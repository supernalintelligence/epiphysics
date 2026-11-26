"""Owned retained-output controls; never run the registered development study."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import decision_assessment as assessment
from epiphysics import decision_evaluation as evaluation
from epiphysics import decision_views as views


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "control-exchange"
ACCOUNTING = "Child wall contains its stage times. Parent wall includes computation and attempt journaling through final source verification, excluding final report serialization/persistence. Do not add nested totals. Lossless arms are separate controls; retain caller wall time separately."


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def successor(checks):
    repair = not all(checks.values())
    return {"action": "repair_decision_pilot" if repair else "prepare_fresh_decision_comparison",
            "reason": "A conformance, execution or separation check failed" if repair else
                "Development wiring passed; freeze and review before generating one new 24-case exploratory batch",
            "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "exposed development measurements; no adoption claim"}


def synthetic_evidence(*, overflow=False, invalid_utf8=False):
    # Clone one exposed positive for transport checks. This is not a comparison
    # of the twelve registered mechanisms, and launches no worker or policy.
    original = json.loads((EXAMPLES / "development-traces.json").read_bytes())["traces"][0]
    traces = []
    for index in range(12):
        trace = deepcopy(original)
        trace["trace_id"] = "assessment-owned-" + str(index)
        trace["mechanism"] = "retained transport control"
        traces.append(trace)
    cohort = {"cohort_id": "decision-pilot-development-v1", "contract_id": views.CONTRACT_ID,
              "trace_count": 12, "final_cohort_generated": False, "traces": traces}
    sources = {name: digest((Path(assessment.__file__).parent / name).read_bytes()) for name in assessment.SOURCE_NAMES}
    checks = {name: True for name in assessment.CHECK_FIELDS}
    failed = overflow or invalid_utf8
    if failed:
        checks.update(all_outputs_valid=False, fixed_policy_conformance=False, lossless_reference_parity=False)
    report = {"schema_version": 1, "contract_id": views.CONTRACT_ID, "cohort_id": cohort["cohort_id"],
        "cohort_hash": digest(raw(cohort)), "stage": "exposed_development", "declared_case_count": 12,
        "source_hashes": sources, "checks": checks, "arms": [],
        "limits": {"program_seconds": 30, "normal_view_bytes": 2048, "lossless_view_bytes": 32768, "worker_output_bytes": 65536},
        "scope": "Owned synthetic development only; retention and view systems compared together; no generalization or live authority claim",
        "resources": {"parent_wall_seconds": 1.0, "model_calls": 0, "external_program_spend": 0,
            "agent_and_review_cost": None, "memory_bytes": None, "accounting": ACCOUNTING},
        "next_step": successor(checks)}
    for recipe, budget in assessment.ARMS:
        rows, evaluated_rows = [], []
        for trace in traces:
            bundle = views.prepare_decision_input(trace["events"], trace["task"], trace["cutoff"], trace["decision_at"])
            view = None if failed else views.build_decision_view(bundle["header_bytes"], bundle["event_tape_bytes"], recipe=recipe, budget_bytes=budget)
            proposal = None if failed else evaluation.reference_decision(trace)
            stages = {"build_seconds": 0.001, "validate_decode_seconds": 0.001, "policy_seconds": 0.001}
            response = None if failed else {"view": view.decode(), "proposal": proposal, "input_hash": bundle["input_hash"],
                "source_hash": digest(bundle["event_tape_bytes"]), "complete": True, "timings": stages}
            stdout, stderr = (b"x" * 65537 if overflow else b"\xff" if invalid_utf8 else raw(response)), b""
            error = "worker_output_limit" if overflow else None
            receipt = {"error": error, "returncode": -9 if overflow else 0, "elapsed_seconds": 0.01,
                "request_bytes": len(raw({"header": bundle["header_bytes"].decode(), "tape": bundle["event_tape_bytes"].decode(), "recipe": recipe, "budget_bytes": budget}))}
            for label, value in (("stdout", stdout), ("stderr", stderr)):
                receipt.update({label + "_base64": base64.b64encode(value).decode(), label + "_sha256": digest(value), label + "_bytes": len(value)})
            evaluation_error = error
            if invalid_utf8:
                try:
                    json.loads(stdout)
                except UnicodeDecodeError as invalid:
                    evaluation_error = str(invalid).encode("utf-8", errors="replace")[:400].decode("utf-8", errors="replace")
            evaluated = evaluation.evaluate_simulated_proposal(trace, proposal, error=evaluation_error)
            evaluated_rows.append(evaluated)
            row = deepcopy(evaluated)
            row.update(arm=recipe, budget_bytes=budget, input_hash=bundle["input_hash"],
                source_hash=digest(bundle["event_tape_bytes"]), source_bytes=len(bundle["event_tape_bytes"]), header_bytes=len(bundle["header_bytes"]),
                view_hash=digest(view) if view else None, view_bytes=len(view) if view else None, view=view.decode() if view else None,
                provenance_valid=not failed, complete=True if not failed else None, worker_receipt=receipt,
                resources={"normalization_seconds": 0.001, "candidate_stages": stages if not failed else None,
                    "child_wall_seconds": 0.01, "parent_verification_seconds": 0.001, "model_calls": 0,
                    "external_program_spend": 0, "memory_bytes": None})
            rows.append(row)
        summary = evaluation.aggregate_metrics(evaluated_rows)
        report["arms"].append({"recipe": recipe, "budget_bytes": budget, "control": budget == 32768,
            "rows": rows, "summary": summary, "strata": {"retained transport control": deepcopy(summary)}})
    return cohort, report


def journal_for(cohort, report):
    entries = [{"kind": "declared_run", "cohort_hash": report["cohort_hash"], "source_hashes": report["source_hashes"],
        "arms": [list(arm) for arm in assessment.ARMS], "case_ids": [trace["trace_id"] for trace in cohort["traces"]],
        "scope": "exposed development; only root may invoke the registered run"}]
    for arm in report["arms"]:
        for row in arm["rows"]:
            entries.extend([{"kind": "worker_returned", "case_id": row["case_id"], "recipe": arm["recipe"],
                "budget_bytes": arm["budget_bytes"], "input_hash": row["input_hash"], "receipt": row["worker_receipt"]},
                {"kind": "attempt_evaluated", "row": row}])
    entries.append({"kind": "run_terminal", "checks": report["checks"], "next_step": report["next_step"]})
    return b"".join(raw(entry) + b"\n" for entry in entries)


def write_study(directory, cohort, report):
    directory = Path(directory)
    for role in ("decision_contract", "evaluation_contract"):
        (directory / (role + ".json")).write_bytes((EXAMPLES / (role.replace("_", "-") + ".json")).read_bytes())
    (directory / "cohort.json").write_bytes(raw(cohort))
    (directory / "report.json").write_bytes(raw(report))
    (directory / "journal.jsonl").write_bytes(journal_for(cohort, report))
    request = {"schema_version": 1, "study_id": "owned-assessment-control", "phase": "development",
        "origin": {"step_id": "owned-preparation:next"}, "paths": {role: role + ".json" for role in
            ("cohort", "report", "decision_contract", "evaluation_contract")}}
    request["paths"]["journal"] = "journal.jsonl"
    (directory / "request.json").write_bytes(raw(request))
    return directory / "request.json"


class DecisionAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cohort, cls.report = synthetic_evidence()

    def _prepare(self, report=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = write_study(temporary.name, deepcopy(self.cohort), deepcopy(report or self.report))
        return path, assessment.prepare_decision_study(path)

    def _reject_report(self, mutate, message=None):
        report = deepcopy(self.report)
        mutate(report)
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, report)
            with self.assertRaisesRegex(ValueError, message or ".*"):
                assessment.prepare_decision_study(path)

    def test_complete_captured_replay_without_original_paths_or_candidates(self):
        path, prepared = self._prepare()
        before = deepcopy(prepared)
        for child in path.parent.iterdir():
            child.unlink()
        forbidden = []
        def profile(frame, event, arg):
            if event == "call" and frame.f_code.co_name in {"build_decision_view", "decide_release_hold", "_candidate", "run_development", "_run_candidate"}:
                forbidden.append(frame.f_code.co_name)
        sys.setprofile(profile)
        try:
            checked = assessment.assess_prepared_decision_study(prepared)
        finally:
            sys.setprofile(None)
        self.assertEqual(forbidden, [])
        self.assertEqual(prepared, before)
        self.assertEqual(checked["report"]["counts"]["attempts"], 48)
        self.assertEqual(checked["report"]["status"], "checked")
        self.assertEqual(checked["report"]["next_step"]["action"], "prepare_fresh_decision_comparison")
        self.assertNotIn("rows", checked["report"]["arms"][0])
        self.assertNotIn("strata", checked["report"]["arms"][0])
        self.assertEqual(checked["artifacts"]["assessment_report"], raw(checked["report"]))
        self.assertEqual(len(prepared["artifacts"]), 11)

    def test_large_bounded_failed_outputs_remain_failures(self):
        cohort, report = synthetic_evidence(overflow=True)
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, cohort, report)
            self.assertGreater((path.parent / "journal.jsonl").stat().st_size, 8 * 1024 * 1024)
            prepared = assessment.prepare_decision_study(path)
            checked = assessment.assess_prepared_decision_study(prepared)["report"]
        self.assertEqual(checked["next_step"]["action"], "repair_decision_pilot")
        for arm in checked["arms"]:
            self.assertEqual(arm["summary"]["counts"]["failed_attempts"], 12)
            self.assertEqual(arm["summary"]["metrics"]["missed_world_opportunities"]["denominator"], 12)
            self.assertEqual(arm["summary"]["metrics"]["valid_output_completion"]["numerator"], 0)

    def test_invalid_utf8_failure_preserves_exact_driver_error(self):
        cohort, report = synthetic_evidence(invalid_utf8=True)
        self.assertIn("'utf-8' codec can't decode byte", report["arms"][0]["rows"][0]["proposal_error"])
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, cohort, report)
            prepared = assessment.prepare_decision_study(path)
            self.assertEqual(prepared["report"]["next_step"]["action"], "repair_decision_pilot")
            self.assertEqual(prepared["report"]["arms"][0]["summary"]["counts"]["failed_attempts"], 12)
            report["arms"][0]["rows"][0]["proposal_error"] = "Invalid bounded JSON"
            write_study(directory, cohort, report)
            with self.assertRaisesRegex(ValueError, "Independent evaluated attempt"):
                assessment.prepare_decision_study(path)

    def test_incomplete_deadline_retains_exact_captured_failure_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, self.report)
            journal_path = path.parent / "journal.jsonl"
            declaration = json.loads(journal_path.read_bytes().splitlines()[0])
            first = self.report["arms"][0]["rows"][0]
            partial_receipt = deepcopy(first["worker_receipt"])
            prefix = b'{"view":"partial'
            partial_receipt.update(error="program_deadline", returncode=-9, stdout_base64=base64.b64encode(prefix).decode(),
                stdout_sha256=digest(prefix), stdout_bytes=len(prefix),
                output_scope="Prefix drained before the whole-program deadline; unread child bytes may be absent")
            failed = {"status": "failed", "error": "ProgramDeadline", "message": "Whole-program deadline exceeded",
                "checks": {"completed": False}, "journal": str(journal_path), "metrics": None,
                "scope": "Incomplete run; retained attempts must not be presented as complete cohort metrics",
                "next_step": {"action": "repair_decision_pilot", "scale_change_allowed": False}}
            partial = [declaration, {"kind": "worker_interrupted", "case_id": first["case_id"],
                "recipe": first["arm"], "budget_bytes": first["budget_bytes"], "input_hash": first["input_hash"],
                "receipt": partial_receipt}, {"kind": "run_terminal", "checks": failed["checks"], "next_step": failed["next_step"]}]
            (path.parent / "report.json").write_bytes(raw(failed) + b"\n")
            journal_path.write_bytes(b"".join(raw(item) + b"\n" for item in partial))
            expected = {role: (path.parent / name).read_bytes() for role, name in json.loads(path.read_bytes())["paths"].items()}
            expected["request"] = path.read_bytes()
            with self.assertRaises(assessment.DecisionStudyPreparationError) as refused:
                assessment.prepare_decision_study(path)
            error = refused.exception
            self.assertIsInstance(error, ValueError)
            self.assertFalse(hasattr(error, "report"))
            self.assertFalse(hasattr(error, "metrics"))
            for role, value in expected.items():
                self.assertEqual(error.artifacts[role], value)
            self.assertEqual(len(error.artifacts), 11)
            self.assertNotIn("assessment_report", error.artifacts)
            self.assertLessEqual(sum(map(len, error.artifacts.values())), assessment.MAX_BUNDLE_BYTES)

    def test_capture_error_retains_only_safely_read_bounded_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, self.report)
            # Canonical request order reads cohort before the missing contract.
            (path.parent / "decision_contract.json").unlink()
            with self.assertRaises(assessment.DecisionStudyPreparationError) as refused:
                assessment.prepare_decision_study(path)
            self.assertEqual(set(refused.exception.artifacts), {"request", "cohort"})
        error = assessment.DecisionStudyPreparationError("owned bound control", {
            "request": b"retained", "extra": b"unrecognized", "report": "not bytes",
            "cohort": b"x" * (assessment.LIMITS["cohort"] + 1)})
        self.assertEqual(error.artifacts, {"request": b"retained"})

    def test_recomputed_world_rows_aggregates_strata_and_checks(self):
        mutations = [
            lambda report: report["arms"][0]["rows"][0]["facts"].update(world_authorized=False),
            lambda report: report["arms"][0]["rows"][0]["metric_flags"].update(valid_timely_release=0),
            lambda report: report["arms"][0]["summary"]["metrics"]["valid_timely_release"].update(numerator=0),
            lambda report: report["arms"][0]["strata"]["retained transport control"]["counts"].update(failed_attempts=1),
            lambda report: report["checks"].update(fixed_policy_conformance=False),
            lambda report: report["next_step"].update(action="adopt_relational"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self._reject_report(mutate)

    def test_raw_receipts_hash_size_nonzero_and_failed_relabel(self):
        for change in ({"stdout_sha256": "0" * 64}, {"stdout_bytes": 0}, {"returncode": 1},
                       {"returncode": None}, {"error": "worker_exit", "returncode": 1}, {"request_bytes": 1}):
            with self.subTest(change=change):
                self._reject_report(lambda report: report["arms"][0]["rows"][0]["worker_receipt"].update(change))

    def test_public_bundle_view_and_source_bindings(self):
        for change in ({"input_hash": "0" * 64}, {"view_bytes": 0}, {"view_hash": "0" * 64},
                       {"complete": False}, {"header_bytes": 0}, {"provenance_valid": False}):
            with self.subTest(change=change):
                self._reject_report(lambda report: report["arms"][0]["rows"][0].update(change))
        self._reject_report(lambda report: report["source_hashes"].update({"decision_pilot.py": "0" * 64}))
        self._reject_report(lambda report: report.update(cohort_hash="0" * 64))

    def test_independent_output_support_and_timings(self):
        def mutate_response(report, field, value):
            receipt = report["arms"][0]["rows"][0]["worker_receipt"]
            response = json.loads(base64.b64decode(receipt["stdout_base64"]))
            if field == "support_event_ids":
                response["proposal"][field] = value
            else:
                response["timings"][field] = value
            encoded = raw(response)
            receipt.update(stdout_base64=base64.b64encode(encoded).decode(), stdout_bytes=len(encoded), stdout_sha256=digest(encoded))
        for field, value in (("support_event_ids", []), ("policy_seconds", 2.0), ("policy_seconds", -0.1), ("policy_seconds", True)):
            with self.subTest(field=field, value=value):
                self._reject_report(lambda report: mutate_response(report, field, value))
        self._reject_report(lambda report: report["arms"][0]["rows"][0]["resources"].update(normalization_seconds=True))
        self._reject_report(lambda report: report["resources"].update(parent_wall_seconds=0.1))

    def test_extra_missing_reordered_and_unmatched_journal_records(self):
        for mutation in (lambda lines: lines[:-1], lambda lines: lines + [lines[1]],
                         lambda lines: lines[:1] + [lines[2], lines[1]] + lines[3:],
                         lambda lines: lines[:1] + [lines[3]] + lines[2:]):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                path = write_study(directory, self.cohort, self.report)
                journal_path = path.parent / "journal.jsonl"
                lines = journal_path.read_bytes().splitlines(keepends=True)
                journal_path.write_bytes(b"".join(mutation(lines)))
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)
        self._reject_report(lambda report: report["arms"][0]["rows"].pop())
        self._reject_report(lambda report: report["arms"].reverse())

    def test_contract_and_original_input_shape_refusals(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, self.report)
            contract = path.parent / "decision_contract.json"
            contract.write_bytes(contract.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Frozen"):
                assessment.prepare_decision_study(path)
        for change in ({"schema_version": True}, {"phase": "final"}, {"origin": {"step_id": ""}}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                path = write_study(directory, self.cohort, self.report)
                request = json.loads(path.read_bytes())
                request.update(change)
                path.write_bytes(raw(request))
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)

    def test_symlink_oversized_and_duplicate_json_refusals(self):
        for kind in ("symlink", "oversized", "duplicate"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                path = write_study(directory, self.cohort, self.report)
                cohort = path.parent / "cohort.json"
                if kind == "symlink":
                    alternate = path.parent / "other.json"
                    cohort.rename(alternate)
                    cohort.symlink_to(alternate)
                elif kind == "oversized":
                    cohort.write_bytes(b" " * (262144 + 1))
                else:
                    cohort.write_bytes(b'{"trace_count":12,"trace_count":12}')
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)

    def test_prepared_mutation_role_manifest_and_live_callables(self):
        _, prepared = self._prepare()
        for mutation in (lambda item: item["artifacts"].update(extra=b"unexpected"),
                         lambda item: item["manifest"].update(report="0" * 64),
                         lambda item: item["report"]["counts"].update(attempts=47)):
            changed = deepcopy(prepared)
            mutation(changed)
            with self.assertRaises(ValueError):
                assessment.check_prepared_decision_study(changed)
        with patch.object(evaluation, "reference_decision", lambda trace: {}):
            with self.assertRaisesRegex(ValueError, "Evaluator callable"):
                assessment.check_prepared_decision_study(prepared)
        with patch.object(views, "build_decision_view", lambda *args, **kwargs: b"{}"):
            with self.assertRaisesRegex(ValueError, "callable"):
                assessment.check_prepared_decision_study(prepared)


if __name__ == "__main__":
    unittest.main()
