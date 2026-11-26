"""Owned retained-evidence diagnosis; no private archives or network calls."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics import retrieval_assessment as assessment, retrieval_coverage as coverage, retrieval_diagnosis as diagnosis, retrieval_evaluation as evaluation
from epiphysics.store import Ledger, canonical, digest
from test_retrieval_coverage_preparation import make_fixture, validation_args, execute_pair, study_files


def rehash(event):
    event["hash"] = digest(canonical({key: event[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}).encode())
    return event


def make_diagnosis_fixture(root, evidence, *, multiple=False):
    data = make_fixture(root, evidence, gap=True, freeze=False)
    if multiple:
        data["cohort"]["cases"][8]["query"] = "anotherunmatchedzz"
        data["cohort_raw"] = json.dumps(data["cohort"], indent=2).encode()
        data["protocol"]["cohort_file_sha256"] = digest(data["cohort_raw"])
        data["protocol"]["projected_queries_hash"] = digest(canonical(evaluation.project_queries(data["cohort"])).encode())
        data["protocol_raw"] = canonical(data["protocol"]).encode()
        data["review"]["cohort_file_sha256"] = digest(data["cohort_raw"])
        data["review_raw"] = canonical(data["review"]).encode()
    data["prepared"] = coverage.validate_coverage_preparation(evidence, **validation_args(data))
    data["freeze"] = coverage.create_coverage_freeze(evidence, **validation_args(data), run_keys=data["run_keys"])
    data["runs"] = execute_pair(data, evidence)
    path, _, declaration = study_files(data, evidence, "evaluation", data["runs"])
    prepared = assessment.prepare_retrieval_study(path, declared_contract=declaration)
    data["original_actual_report"] = assessment.assess_prepared_retrieval_study(prepared)["report"]
    origin_ledger = Ledger(root / "owned-origin")
    try:
        data["origin"] = origin_ledger.append("improvement_completed", {"run_key": "owned-origin", "result": "assessed",
            "report": {"actual_retrieval": data["original_actual_report"]},
            "next_step": {"id": "owned-origin:next", "action": "inspect_fresh_support_failures", "state": "queued", "scale_change_allowed": False}},
            "improvement:owned-origin:complete")
    finally:
        origin_ledger.close()
    return data


def bind_diagnosis(data, evidence, origin, *, focus=None, categories=None):
    root = data["root"]
    _, request, declaration = study_files(data, evidence, "evaluation", data["runs"])
    focus = ["q-5-answerable"] if focus is None else focus
    investigation = canonical({"investigation": "Owned visible-development interval diagnosis."}).encode()
    declaration.update(phase="support_diagnosis", diagnosis_id="owned-diagnosis", origin_transition={"id": origin["id"], "hash": origin["hash"]},
        origin_step_id=origin["body"]["next_step"]["id"], diagnosis_hash=digest(investigation), diagnosis_review_hash="0" * 64, focus_question_ids=focus)
    request.update(phase="support_diagnosis", diagnosis_id="owned-diagnosis", focus_question_ids=focus,
        diagnosis_file=str(root / "diagnosis.json"), diagnosis_review_file=str(root / "diagnosis-review.json"), origin_file=str(root / "origin.json"))
    findings = diagnosis.compute_support_findings(evidence, cohort=data["cohort"], freeze_event_id=data["freeze"]["id"],
        run_terminal_ids=request["run_terminal_ids"], origin_transition=origin, declared_contract=declaration)
    review = {"schema_version": 1, "contract_id": diagnosis.CONTRACT_ID, "diagnosis_id": declaration["diagnosis_id"],
        "diagnosis_hash": digest(investigation), "origin_transition": declaration["origin_transition"],
        "origin_step_id": declaration["origin_step_id"], "machine_findings_hash": findings["hash"],
        "investigator_id": "owned-investigator", "reviewer_id": "owned-independent-reviewer", "focus_question_ids": focus,
        "cases": [{"question_id": row["question_id"], "category": (categories or {}).get(row["question_id"], "retrieval_gap"),
                   "reviewed_windows_hash": row["returned_windows_hash"], "rationale": "Owned review claim, not semantic proof."} for row in findings["cases"]],
        "exposure": "post_execution_builder_visible_development"}
    review_raw = canonical(review).encode()
    declaration["diagnosis_review_hash"] = digest(review_raw)
    Path(request["diagnosis_file"]).write_bytes(investigation)
    Path(request["diagnosis_review_file"]).write_bytes(review_raw)
    Path(request["origin_file"]).write_text(canonical(origin))
    path = root / "support-diagnosis.json"
    path.write_text(canonical(request))
    return path, request, declaration, review


class RetrievalDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = Ledger(self.root / "evidence")
        self.addCleanup(self.evidence.close)
        self.data = make_diagnosis_fixture(self.root, self.evidence)
        self.path, self.request, self.contract, self.review = bind_diagnosis(self.data, self.evidence, self.data["origin"])

    def args(self):
        return {"cohort": self.data["cohort"], "freeze_event_id": self.data["freeze"]["id"],
            "run_terminal_ids": self.request["run_terminal_ids"], "origin_transition": self.data["origin"], "declared_contract": self.contract,
            "diagnosis_raw": Path(self.request["diagnosis_file"]).read_bytes(), "review_raw": Path(self.request["diagnosis_review_file"]).read_bytes()}

    def test_actual_retained_diagnosis_is_deterministic_read_only_and_not_a_new_score(self):
        before = self.evidence.events()
        result = diagnosis.check_support_diagnosis(self.evidence, **self.args())
        self.assertEqual(result, diagnosis.check_support_diagnosis(self.evidence, **self.args()))
        self.assertEqual(before, self.evidence.events())
        facts = result["machine_findings"]
        self.assertEqual(["q-5-answerable"], facts["failed_question_ids"])
        self.assertEqual([], facts["deferred_question_ids"])
        span = facts["cases"][0]["spans"][0]
        self.assertFalse(span["returned_prefixes"]["5"]["complete"])
        self.assertTrue(span["projection_coverage"]["complete"])
        self.assertNotIn("quality", result)
        self.assertNotIn("next_probe", result)

    def test_no_search_projection_or_scoring_entry_point_is_executed(self):
        forbidden = {"evaluate_retrieval", "_score_case", "_score_coverage", "_score_coverage_case", "run_lexical_retrieval", "project_index", "lexical_search"}
        def guard(frame, event, arg):
            if event == "call" and frame.f_code.co_name in forbidden:
                raise AssertionError("Unexpected execution: " + frame.f_code.co_name)
        sys.setprofile(guard)
        try:
            diagnosis.check_support_diagnosis(self.evidence, **self.args())
        finally:
            sys.setprofile(None)

    def test_valid_unresolved_and_annotation_gap_remain_attributed(self):
        for category in ("unresolved", "annotation_gap"):
            _, _, contract, review = bind_diagnosis(self.data, self.evidence, self.data["origin"], categories={"q-5-answerable": category})
            value = diagnosis.check_support_diagnosis(self.evidence, **{**self.args(), "declared_contract": contract})
            self.assertEqual(category, value["semantic_review"]["cases"][0]["category"])
            self.assertEqual(["q-5-answerable"] if category == "unresolved" else [], value["semantic_review"]["unresolved_question_ids"])

    def test_interval_union_preserves_partial_coverage_and_gaps(self):
        span = {"observation_id": "a", "start": 10, "end": 30, "sha256": "0" * 64}
        def row(a, b, source="a"):
            return {"observation_id": source, "start": a, "end": b}
        value = diagnosis._coverage(span, [row(8, 15), row(14, 20), row(21, 24), row(24, 35), row(10, 30, "b")])
        self.assertEqual([[10, 20], [21, 30]], value["covered_intervals"])
        self.assertEqual([[20, 21]], value["missing_intervals"])
        self.assertEqual(19, value["covered_bytes"])
        self.assertFalse(value["complete"])
        self.assertTrue(diagnosis._coverage(span, [row(0, 20), row(20, 40)])["complete"])

    def compute(self, **changes):
        args = self.args()
        args.pop("diagnosis_raw")
        args.pop("review_raw")
        return diagnosis.compute_support_findings(self.evidence, **{**args, **changes})

    def forged_report(self, edit):
        origin = deepcopy(self.data["origin"])
        for report in origin["body"]["report"]["actual_retrieval"]["quality"]["runs"]:
            edit(report)
        rehash(origin)
        contract = {**self.contract, "origin_transition": {"id": origin["id"], "hash": origin["hash"]}}
        return origin, contract

    def test_coherent_original_report_changes_are_reconciled_against_actual_intervals(self):
        edits = [lambda r: r["per_case"][-2]["complete_support_at_k"].update({"5": True}),
                 lambda r: r["per_case"][-2].update(raw_windows=[{"rank": 1, "observation_id": "source-3", "start": 0, "end": 28, "sha256": "0" * 64}]),
                 lambda r: r["per_case"].pop(),
                 lambda r: r["per_case"][0]["bundles"][0]["covered_spans_at_k"].update({"1": 0})]
        for edit in edits:
            origin, contract = self.forged_report(edit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.compute(origin_transition=origin, declared_contract=contract)

    def test_declared_origin_freeze_and_receipt_hashes_are_required(self):
        for name in ("freeze_event_hash", "candidate_algorithm_hash", "cohort_hash", "protocol_hash", "review_hash"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.compute(declared_contract={**self.contract, name: "0" * 64})
        for name in ("run_terminal_hashes", "projection_hashes"):
            contract = deepcopy(self.contract)
            contract[name][self.data["runs"][0]["id"]] = "0" * 64
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.compute(declared_contract=contract)
        with self.assertRaisesRegex(ValueError, "origin differs"):
            self.compute(declared_contract={**self.contract, "origin_transition": {**self.contract["origin_transition"], "hash": "0" * 64}})

    def test_unknown_duplicate_and_successful_focus_cannot_create_a_failure(self):
        for focus in ([], ["missing"], ["q-5-answerable", "q-5-answerable"], ["q-0-answerable"], ["q-5-unanswerable"]):
            with self.subTest(focus=focus), self.assertRaises(ValueError):
                self.compute(declared_contract={**self.contract, "focus_question_ids": focus})

    def test_review_requires_exact_bindings_but_never_infers_semantics(self):
        edits = [lambda r: r.update(machine_findings_hash="0" * 64),
                 lambda r: r.update(reviewer_id=r["investigator_id"]),
                 lambda r: r.update(cases=[]),
                 lambda r: r["cases"][0].update(reviewed_windows_hash="0" * 64),
                 lambda r: r["cases"][0].update(category="guaranteed_truth"),
                 lambda r: r.update(origin_step_id="another-step"),
                 lambda r: r.update(focus_question_ids=["q-0-answerable"])]
        for edit in edits:
            review = deepcopy(self.review)
            edit(review)
            raw = canonical(review).encode()
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                diagnosis.check_support_diagnosis(self.evidence, **{**self.args(), "review_raw": raw,
                    "declared_contract": {**self.contract, "diagnosis_review_hash": digest(raw)}})
        with self.assertRaises(ValueError):
            diagnosis.check_support_diagnosis(self.evidence, **{**self.args(), "diagnosis_raw": b"Changed investigation"})

    def test_source_and_projection_corruption_cannot_be_diagnosed_as_intact(self):
        for content_hash in (self.data["runs"][0]["body"]["projection_hash"], self.evidence.get("source-3")["body"]["content_hash"]):
            path = self.evidence.root / "blobs" / content_hash
            original = path.read_bytes()
            try:
                path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                with self.subTest(content_hash=content_hash), self.assertRaises(ValueError):
                    self.compute()
            finally:
                path.write_bytes(original)

    def test_multiple_failures_leave_unfocused_inventory_explicit(self):
        root = self.root / "multiple"
        root.mkdir()
        ledger = Ledger(root / "evidence")
        try:
            data = make_diagnosis_fixture(root, ledger, multiple=True)
            _, request, contract, _ = bind_diagnosis(data, ledger, data["origin"])
            value = diagnosis.compute_support_findings(ledger, cohort=data["cohort"], freeze_event_id=data["freeze"]["id"],
                run_terminal_ids=request["run_terminal_ids"], origin_transition=data["origin"], declared_contract=contract)
            self.assertEqual(["q-4-answerable", "q-5-answerable"], value["failed_question_ids"])
            self.assertEqual(["q-4-answerable"], value["deferred_question_ids"])
            self.assertEqual(["q-5-answerable"], [row["question_id"] for row in value["cases"]])
        finally:
            ledger.close()

    def test_generic_interval_core_does_not_pool_incomplete_alternatives(self):
        def span(start, end):
            return {"observation_id": "a", "start": start, "end": end, "sha256": "0" * 64}
        case = {"question_id": "generic", "answerability": "answerable", "support_bundles": [
            {"bundle_id": "first", "spans": [span(0, 5), span(10, 15)]},
            {"bundle_id": "alternative", "spans": [span(0, 5), span(20, 25)]}]}
        result = {"hits": [{"rank": 1, **span(0, 5)}, {"rank": 2, **span(10, 13)}, {"rank": 3, **span(22, 25)}]}
        value, _ = diagnosis._case(case, result, [span(0, 25)], detailed=True, deadline=None)
        self.assertEqual(3, len(value["spans"]))
        self.assertFalse(value["complete_at_k"]["5"])
        self.assertTrue(all(row["projection_coverage"]["complete"] for row in value["spans"]))

    def test_malformed_bounded_and_expired_inputs_refuse(self):
        for origin in (None, [], "bad", {**self.data["origin"], "body": []}):
            with self.subTest(origin=type(origin)), self.assertRaises(ValueError):
                self.compute(origin_transition=origin)
        with self.assertRaises(TimeoutError):
            self.compute(deadline=time.monotonic() - 1)
        with patch.object(diagnosis, "MAX_REPORT_BYTES", 128), self.assertRaises(ValueError):
            self.compute()
        for raw in (b"null", b"[]", b'{"schema_version":1,"schema_version":1}', b" " * (diagnosis.MAX_REVIEW_BYTES + 1)):
            with self.subTest(rawlen=len(raw)), self.assertRaises(ValueError):
                diagnosis.check_support_diagnosis(self.evidence, **{**self.args(), "review_raw": raw})
        with patch.object(diagnosis, "IMPLEMENTATION_SOURCE", diagnosis.IMPLEMENTATION_SOURCE + b"changed"), self.assertRaises(ValueError):
            self.compute()

    def test_guard_controls_detect_removed_reconciliation_without_rejecting_all(self):
        origin, contract = self.forged_report(lambda r: r["per_case"][-2]["complete_support_at_k"].update({"5": True}))
        with self.assertRaisesRegex(ValueError, "recomputed intervals"):
            self.compute(origin_transition=origin, declared_contract=contract)
        ordinary_same = diagnosis._same
        def removed_case_equality(left, right):
            if type(right) is dict and set(right) == {"1", "3", "5"} and right == {"1": False, "3": False, "5": False}:
                return True
            return ordinary_same(left, right)
        # Deliberately release only this callable guard to test the semantic
        # equality gate itself. Normal execution refuses such monkeypatching.
        with patch.object(diagnosis, "_same", removed_case_equality):
            codes = tuple((name, getattr(diagnosis, name), getattr(diagnosis, name).__code__) for name, _, _ in diagnosis._FUNCTION_CODES)
            with patch.object(diagnosis, "_FUNCTION_CODES", codes):
                self.assertEqual(["q-5-answerable"], self.compute()["failed_question_ids"])
                accepted = self.compute(origin_transition=origin, declared_contract=contract)
                self.assertEqual(["q-5-answerable"], accepted["failed_question_ids"])
        # The negative detector above rejects the mutant, even though the same
        # mutant retains ordinary positive behavior instead of rejecting all.

    def test_guard_control_exposes_removed_origin_comparison(self):
        changed = {**self.contract, "origin_transition": {**self.contract["origin_transition"], "hash": "0" * 64}}
        with self.assertRaisesRegex(ValueError, "origin differs"):
            self.compute(declared_contract=changed)
        original = diagnosis._origin
        def removed_origin_comparison(event, contract):
            return original(event, {**contract, "origin_transition": {"id": event["id"], "hash": event["hash"]}})
        with patch.object(diagnosis, "_origin", removed_origin_comparison):
            codes = tuple((name, getattr(diagnosis, name), getattr(diagnosis, name).__code__) for name, _, _ in diagnosis._FUNCTION_CODES)
            with patch.object(diagnosis, "_FUNCTION_CODES", codes):
                self.assertEqual(["q-5-answerable"], self.compute()["failed_question_ids"])
                self.assertEqual("0" * 64, self.compute(declared_contract=changed)["origin_bindings"]["transition"]["hash"])


if __name__ == "__main__":
    unittest.main()
