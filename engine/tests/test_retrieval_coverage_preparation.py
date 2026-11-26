"""Owned coverage fixtures and freeze controls; no development archive access."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from epiphysics import retrieval, retrieval_coverage as coverage, retrieval_evaluation as evaluation
from epiphysics.store import Ledger, canonical, digest


def make_fixture(root, ledger, *, gap=False, freeze=True, top_k=5):
    texts = [b"Amber stores blue receipts. Amber receipt color is blue. Amber verifies two signatures.",
             b"Birch accepts signed requests. Birch records opaque identifiers.",
             b"Cedar lists active workers.", b"Delta records invoice totals."]
    for index, raw in enumerate(texts):
        ledger.capture(f"owned:coverage-{index}", raw, event_id=f"source-{index}")
    snapshot = ledger.snapshot(event_id="snapshot")
    corpus = retrieval.freeze_retrieval_corpus(ledger, snapshot["id"], [f"source-{i}" for i in range(4)], event_id="corpus",
        config={**retrieval.contracts.DEFAULT_CONFIG, "top_k": top_k})
    reference = retrieval.run_lexical_retrieval(ledger, "corpus", [{"query_id": "old", "query": "Amber"}], run_key="reference")
    def span(index, text):
        start = texts[index].index(text)
        return {"observation_id": f"source-{index}", "start": start, "end": start + len(text), "sha256": digest(text)}
    obligations = [
        (0, "Amber receipt color", [[span(0, b"Amber stores blue receipts.")], [span(0, b"Amber receipt color is blue.")]]),
        (0, "Amber receipt and signature requirements", [[span(0, b"Amber stores blue receipts."), span(0, b"Amber verifies two signatures.")]]),
        (1, "Birch request requirements", [[span(1, b"Birch accepts signed requests.")]]),
        (1, "Birch identifier type", [[span(1, b"Birch records opaque identifiers.")]]),
        (2, "Cedar worker state", [[span(2, texts[2])]]),
        (3, "Delta recorded quantity", [[span(3, texts[3])]]),
    ]
    cases, pairs = [], []
    for index, (source, query, alternatives) in enumerate(obligations):
        pid = f"pair-{index}"
        for label in ("answerable", "unanswerable"):
            cases.append({"question_id": f"q-{index}-{label}", "query": ("unmatchedtokenzz" if gap and index == 5 and label == "answerable"
                else query if label == "answerable" else query + " annual adoption rate"),
                "pair_id": pid, "answerability": label, "support_bundles": [
                    {"bundle_id": f"bundle-{i}", "spans": spans} for i, spans in enumerate(alternatives)] if label == "answerable" else [],
                "rationale": "Owned support/absence control.", "family_tags": ["software_service"], "relation_tags": ["obligation"],
                "novelty": {"related_prior_question_ids": [], "distinction": "New owned fixture obligation."}})
        pairs.append({"pair_id": pid, "supported_question_id": f"q-{index}-answerable",
            "unsupported_question_id": f"q-{index}-unanswerable", "anchor_observation_ids": [f"source-{source}"],
            "changed_requirement": "Request a measured adoption rate absent from the corpus.", "matching_rationale": "Same system and stated topic."})
    cohort = {"schema_version": 2, "snapshot_id": "snapshot", "cohort": "development", "cohort_id": "owned-coverage",
        "source_scope": "selected_corpus_only", "support_semantics": "any_complete_bundle_v1",
        "cases": cases, "pairs": pairs, "limitations": ["Owned controls, not population evidence."]}
    cohort_raw = json.dumps(cohort, indent=2).encode()
    protocol = {"schema_version": 1, "study_id": "owned-coverage", "corpus_id": "corpus", "corpus_hash": corpus["hash"],
        "source_snapshot_hash": snapshot["hash"], "cohort_file_sha256": digest(cohort_raw),
        "projected_queries_hash": digest(canonical(evaluation.project_queries(cohort)).encode()),
        "scoring_contract_id": coverage.CONTRACT_ID, "indexing_recipe": "raw-window-text-v1", "executions": 2, "expected_pairs": 6,
        "cutoffs": [1, 3, 5], "adoption": "none", "scope": "fresh_builder_visible_development",
        "exposure": {"prior_results_seen": True, "fresh_results_seen": False},
        "limits": {"model_calls": 0, "external_spend": 0, "assessment_seconds": 30, "dispatch_seconds": 60}, "successor_rule": "coverage-next-v1"}
    review = {"schema_version": 1, "cohort_file_sha256": digest(cohort_raw), "corpus_hash": corpus["hash"],
        "curator_id": "fixture-curator", "reviewer_id": "fixture-reviewer", "reviewed_source_ids": [f"source-{i}" for i in range(4)],
        "unresolved_case_ids": [], "cases": [{"question_id": case["question_id"], "decision": "accept",
            "reviewed_bundle_ids": [bundle["bundle_id"] for bundle in case["support_bundles"]],
            "unsupported_reason": "Full owned corpus has no measured adoption rate." if case["answerability"] == "unanswerable" else None,
            "alternatives_search_note": "Checked complete owned strings.", "pair_match_note": "Same invented system.",
            "novelty_note": "Owned fixture; not a real independent reviewer."} for case in cases]}
    data = {"root": root, "cohort": cohort, "protocol": protocol, "review": review,
        "cohort_raw": cohort_raw, "protocol_raw": canonical(protocol).encode(), "review_raw": canonical(review).encode(),
        "reference_terminal": {"id": reference["id"], "hash": reference["hash"]}, "run_keys": ["fresh-a", "fresh-b"]}
    data["prepared"] = coverage.validate_coverage_preparation(ledger, **validation_args(data))
    if freeze:
        data["freeze"] = coverage.create_coverage_freeze(ledger, **validation_args(data), run_keys=data["run_keys"])
    return data


def validation_args(data):
    return {key: data[key] for key in ("cohort_raw", "protocol_raw", "review_raw", "reference_terminal")}


def execute_pair(data, ledger):
    return [retrieval.run_lexical_retrieval(ledger, "corpus", evaluation.project_queries(data["cohort"]), run_key=key)
            for key in data["run_keys"]]


def study_files(data, ledger, phase="preparation", runs=()):
    root, prepared, freeze = data["root"], data["prepared"], data["freeze"]
    for name in ("cohort", "protocol", "review"):
        (root / (name + ".json")).write_bytes(data[name + "_raw"])
    contract = {"schema_version": 3, "phase": phase, "study_id": "owned-coverage", **prepared["lineage"],
        "protocol_hash": digest(data["protocol_raw"]), "review_hash": digest(data["review_raw"]), "freeze_event_hash": freeze["hash"],
        "reference_terminal": data["reference_terminal"], "candidate_algorithm_hash": prepared["candidate_identity"]["algorithm_hash"],
        "evaluator_identity_hash": prepared["evaluator_identity_hash"], "runtime_hash": prepared["runtime_hash"]}
    request = {"schema_version": 3, "phase": phase, "study_id": "owned-coverage", "evidence_store": str(ledger.root.resolve()),
        **{name + "_file": str(root / (name + ".json")) for name in ("cohort", "protocol", "review")},
        "corpus_id": "corpus", "freeze_event_id": freeze["id"]}
    if phase == "evaluation":
        request["run_terminal_ids"] = [run["id"] for run in runs]
        contract["run_terminal_hashes"] = {run["id"]: run["hash"] for run in runs}
        contract["projection_hashes"] = {run["id"]: run["body"]["projection_hash"] for run in runs}
    path = root / (phase + ".json")
    path.write_text(canonical(request))
    return path, request, contract


class CoveragePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = Ledger(self.root / "evidence")
        self.addCleanup(self.ledger.close)
        self.data = make_fixture(self.root, self.ledger, freeze=False)

    def freeze(self):
        return coverage.create_coverage_freeze(self.ledger, **validation_args(self.data), run_keys=self.data["run_keys"])

    def test_preparation_uses_real_metadata_without_search_or_scores(self):
        calls = []
        def profile(frame, event, arg):
            if event == "call" and frame.f_code.co_name in ("project_index", "lexical_search", "evaluate_retrieval", "run_lexical_retrieval"):
                calls.append(frame.f_code.co_name)
        before = self.ledger.events()
        sys.setprofile(profile)
        try:
            ready = coverage.validate_coverage_preparation(self.ledger, **validation_args(self.data))
        finally:
            sys.setprofile(None)
        self.assertEqual([], calls)
        self.assertEqual(before, self.ledger.events())
        self.assertEqual(6, ready["inventory"]["counts"]["pairs"])
        self.assertNotIn("quality", ready)
        self.assertEqual("unmeasured", ready["inventory"]["families"]["physical_asset"]["status"])
        self.assertEqual(coverage.CONTRACT_ID, ready["evaluator_identity"]["contract"]["id"])

    def test_freeze_replay_before_and_after_two_executions_is_exact(self):
        event = self.freeze()
        self.data["freeze"] = event
        before = len(self.ledger.events())
        self.assertEqual(event, self.freeze())
        self.assertEqual(before, len(self.ledger.events()))
        execute_pair(self.data, self.ledger)
        before = len(self.ledger.events())
        self.assertEqual(event, self.freeze())
        self.assertEqual(event, coverage.get_coverage_freeze(self.ledger, event["id"])["event"])
        self.assertEqual(before, len(self.ledger.events()))

    def test_original_cohort_bytes_reference_hash_and_review_are_required(self):
        args = validation_args(self.data)
        for changed, message in (({**args, "cohort_raw": canonical(self.data["cohort"]).encode()}, "file hash"),
                ({**args, "reference_terminal": {**args["reference_terminal"], "hash": "0" * 64}}, "reference")):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                coverage.validate_coverage_preparation(self.ledger, **changed)
        for edit in (lambda r: r.update(reviewer_id=r["curator_id"]), lambda r: r["cases"].pop(),
                     lambda r: r["reviewed_source_ids"].pop(), lambda r: r["cases"][0].update(reviewed_bundle_ids=[]),
                     lambda r: r.update(unresolved_case_ids=["q-0-answerable"])):
            review = deepcopy(self.data["review"])
            edit(review)
            with self.assertRaises(ValueError):
                coverage.validate_coverage_preparation(self.ledger, **{**args, "review_raw": canonical(review).encode()})

    def test_first_creation_refuses_existing_or_reversed_execution(self):
        retrieval.run_lexical_retrieval(self.ledger, "corpus", evaluation.project_queries(self.data["cohort"]), run_key="fresh-a")
        with self.assertRaisesRegex(ValueError, "precede"):
            self.freeze()
        self.assertEqual([], self.ledger.events("coverage_freeze"))

    def test_later_reversed_start_is_not_valid_historical_readiness(self):
        event = self.freeze()
        retrieval.run_lexical_retrieval(self.ledger, "corpus", evaluation.project_queries(self.data["cohort"]), run_key="fresh-b")
        with self.assertRaisesRegex(ValueError, "sequential order"):
            coverage.get_coverage_freeze(self.ledger, event["id"])

    def test_exclusive_concurrent_creation_has_one_event(self):
        barrier = threading.Barrier(2)
        def create():
            ledger = Ledger(self.ledger.root)
            try:
                barrier.wait(timeout=5)
                return coverage.create_coverage_freeze(ledger, **validation_args(self.data), run_keys=self.data["run_keys"])
            finally:
                ledger.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(1, len(self.ledger.events("coverage_freeze")))

    def test_concurrent_capture_after_prefix_read_uses_one_snapshot(self):
        other = Ledger(self.ledger.root)
        self.addCleanup(other.close)
        observed = {}
        target_code = coverage.preflight_coverage_capture.__code__
        def trace(frame, event, argument):
            if (event == "line" and frame.f_code is target_code
                    and frame.f_locals.get("ledger") is self.ledger
                    and "end" in frame.f_locals and not observed):
                # Force the competing commit after the prefix boundary was read,
                # without replacing a guarded function or relying on timing.
                observed["end"] = frame.f_locals["end"]
                observed["winner"] = coverage.create_coverage_freeze(
                    other, **validation_args(self.data), run_keys=self.data["run_keys"])
                eid = "coverage-input:" + digest(self.data["protocol"]["study_id"].encode()) + ":cohort"
                observed["capture_seq"] = other.get(eid)["seq"]
            return trace
        previous_trace = sys.gettrace()
        sys.settrace(trace)
        try:
            result = self.freeze()
        finally:
            sys.settrace(previous_trace)
        self.assertGreater(observed["capture_seq"], observed["end"])
        self.assertEqual(result, observed["winner"])
        self.assertEqual(1, len(self.ledger.events("coverage_freeze")))
        captures = [event for event in self.ledger.events("observation")
                    if event["id"].startswith("coverage-input:")]
        self.assertEqual(3, len(captures))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_changed_freeze_binding_refuses_and_corrupt_blob_never_replays(self):
        event = self.freeze()
        with self.assertRaisesRegex(ValueError, "different inputs"):
            coverage.create_coverage_freeze(self.ledger, **validation_args(self.data), run_keys=["other-a", "other-b"])
        raw_hash = event["body"]["artifacts"]["review"]["content_hash"]
        (self.ledger.root / "blobs" / raw_hash).write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "hash or size"):
            coverage.get_coverage_freeze(self.ledger, event["id"])

    def test_protocol_bounds_and_exposure_are_not_configurable(self):
        for edit in (lambda p: p["limits"].update(external_spend=1), lambda p: p["exposure"].update(fresh_results_seen=True),
                     lambda p: p.update(executions=True), lambda p: p.update(expected_pairs=5)):
            protocol = deepcopy(self.data["protocol"])
            edit(protocol)
            with self.assertRaisesRegex(ValueError, "fixed scope"):
                coverage.validate_coverage_preparation(self.ledger, **{**validation_args(self.data), "protocol_raw": canonical(protocol).encode()})
        with self.assertRaisesRegex(ValueError, "1 MB"):
            coverage.validate_coverage_preparation(self.ledger, **{**validation_args(self.data), "review_raw": b" " * 1_000_001})

    def test_current_candidate_source_change_refuses_without_searching(self):
        # Fresh-process changed candidate code has internally consistent source
        # guards. The historical reference comparison must still refuse it.
        package = self.root / "isolated"
        shutil.copytree(Path(coverage.__file__).parent, package / "epiphysics", ignore=shutil.ignore_patterns("__pycache__"))
        source = package / "epiphysics" / "retrieval_indexing.py"
        source.write_bytes(source.read_bytes() + b"\n# Owned reviewed-version mismatch control.\n")
        for role in ("cohort", "protocol", "review"):
            (self.root / (role + ".json")).write_bytes(self.data[role + "_raw"])
        args_file = self.root / "reference.json"
        args_file.write_text(canonical(self.data["reference_terminal"]))
        code = '''
import json,sys
from pathlib import Path
from epiphysics import retrieval_coverage as c
from epiphysics.store import Ledger
root=Path(sys.argv[1]); ledger=Ledger.open_readonly(root/'evidence')
try:
    c.validate_coverage_preparation(ledger,**{role+'_raw':(root/(role+'.json')).read_bytes() for role in ('cohort','protocol','review')},reference_terminal=json.loads((root/'reference.json').read_text()))
except ValueError as e:
    assert 'dependency differs from historical reference' in str(e),str(e)
else:
    raise AssertionError('Changed current candidate silently accepted')
finally:
    ledger.close()
'''
        result = subprocess.run([sys.executable, "-c", code, str(self.root)], cwd=package,
            capture_output=True, text=True, timeout=10, env={"PYTHONPATH": str(package), "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(0, result.returncode, result.stderr)

    def test_append_boundary_blob_change_never_produces_ready_freeze(self):
        original = self.ledger.append
        def changed(kind, body, *args, **kwargs):
            if kind == "coverage_freeze":
                raw_hash = body["artifacts"]["review"]["content_hash"]
                (self.ledger.root / "blobs" / raw_hash).write_bytes(b"changed")
            return original(kind, body, *args, **kwargs)
        with patch.object(self.ledger, "append", changed), self.assertRaises(ValueError):
            self.freeze()
        self.assertEqual([], self.ledger.events("coverage_freeze"))

    def test_future_freeze_is_unavailable_to_current_clock(self):
        clock = self.ledger.clock
        self.ledger.clock = lambda: "2099-01-01T00:00:00+00:00"
        event = self.freeze()
        self.ledger.clock = clock
        with self.assertRaisesRegex(ValueError, "not yet available"):
            coverage.get_coverage_freeze(self.ledger, event["id"])

    def test_ready_run_keys_obey_the_actual_runner_grammar(self):
        for key in ("bad key", "é", "", "a" * 101, "line\nbreak", "name:part"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "grammar"):
                coverage.create_coverage_freeze(self.ledger, **validation_args(self.data), run_keys=[key, "valid-b"])
        self.assertEqual([], self.ledger.events("coverage_freeze"))
        self.data["run_keys"] = ["A" * 100, "._-"]
        event = self.freeze()
        runs = execute_pair(self.data, self.ledger)
        self.assertTrue(all(run["kind"] == "retrieval_completed" for run in runs))
        self.assertEqual(event, coverage.get_coverage_freeze(self.ledger, event["id"])["event"])

    def test_top_k_must_cover_all_scoring_cutoffs_before_freeze(self):
        for top_k in (1, 4):
            ledger = Ledger(self.root / ("k-" + str(top_k)))
            try:
                with self.assertRaisesRegex(ValueError, "maximum scoring cutoff"):
                    make_fixture(self.root, ledger, top_k=top_k)
                self.assertEqual([], ledger.events("coverage_freeze"))
            finally:
                ledger.close()
        ledger = Ledger(self.root / "k-20")
        try:
            data = make_fixture(self.root, ledger, top_k=20)
            self.assertEqual(data["freeze"], coverage.get_coverage_freeze(ledger, data["freeze"]["id"])["event"])
        finally:
            ledger.close()

    def test_projected_queries_must_compile_under_actual_runner_limits(self):
        for count in (65, 64):
            cohort = deepcopy(self.data["cohort"])
            cohort["cases"][0]["query"] = " ".join("term" + str(i) for i in range(count))
            raw = canonical(cohort).encode()
            protocol, review = deepcopy(self.data["protocol"]), deepcopy(self.data["review"])
            protocol["cohort_file_sha256"] = review["cohort_file_sha256"] = digest(raw)
            protocol["projected_queries_hash"] = digest(canonical(evaluation.project_queries(cohort)).encode())
            args = {**validation_args(self.data), "cohort_raw": raw, "protocol_raw": canonical(protocol).encode(), "review_raw": canonical(review).encode()}
            if count == 65:
                with self.assertRaisesRegex(ValueError, "terms"):
                    coverage.validate_coverage_preparation(self.ledger, **args)
            else:
                ready = coverage.validate_coverage_preparation(self.ledger, **args)
                self.assertEqual(12, len(ready["queries"]))

    def pad(self, count):
        while len(self.ledger.events()) < count:
            self.ledger.append("owned_padding", {"n": len(self.ledger.events())})

    def capacity(self):
        return coverage.preflight_coverage_capture(self.ledger, self.data["prepared"],
            **{key: self.data[key] for key in ("cohort_raw", "protocol_raw", "review_raw", "run_keys")})

    def test_230_event_reproduction_refuses_before_any_input_capture(self):
        self.pad(230)
        before = self.ledger.events()
        with self.assertRaisesRegex(ValueError, "event capture capacity"):
            self.freeze()
        self.assertEqual(before, self.ledger.events())
        self.assertEqual([], self.ledger.events("coverage_freeze"))

    def test_exact_event_capacity_reuses_capture_and_executes_both_runs(self):
        from epiphysics import retrieval_assessment as assessment
        chunks = len(self.ledger.get(self.data["reference_terminal"]["id"])["body"]["artifacts"]["projection"]["chunks"])
        before_freeze = 256 - 4 - 2 * (16 + chunks)
        self.pad(before_freeze)
        # Interrupted input capture must be counted once, not charged again.
        coverage._capture(self.ledger, "owned-coverage", "cohort", self.data["cohort_raw"])
        estimate = self.capacity()
        self.assertEqual(256, estimate["evaluation_events"])
        self.data["freeze"] = self.freeze()
        runs = execute_pair(self.data, self.ledger)
        self.assertEqual(256, len(self.ledger.events()))
        path, _, declaration = study_files(self.data, self.ledger, "evaluation", runs)
        prepared = assessment.prepare_retrieval_study(path, declared_contract=declaration)
        self.assertLessEqual(sum(len(raw) for raw in prepared["artifacts"].values()), estimate["evaluation_capture_bytes_upper"])
        self.assertLessEqual(len(prepared["artifacts"]) + 3, estimate["artifact_slots_including_reports"])
        evaluated = assessment.assess_prepared_retrieval_study(prepared)
        self.assertEqual(1, evaluated["report"]["reproducibility"]["value"])
        # Historical replay must not reserve another two runs at the tail.
        self.assertEqual(self.data["freeze"], self.freeze())
        self.assertEqual(256, len(self.ledger.events()))

    def test_metadata_capacity_refuses_before_writing_freeze_inputs(self):
        self.ledger.append("owned_padding", {"padding": "x" * 2_100_000})
        before = self.ledger.events()
        with self.assertRaisesRegex(ValueError, "metadata capture capacity"):
            self.freeze()
        self.assertEqual(before, self.ledger.events())

    def test_artifact_and_aggregate_capture_boundary_controls(self):
        estimate = self.capacity()
        before = self.ledger.events()
        for name, value, message in (("MAX_ARTIFACTS", estimate["artifact_slots_including_reports"], "artifact count"),
                ("MAX_BUNDLE_BYTES", estimate["evaluation_capture_bytes_upper"], "aggregate capture")):
            # Tightening test-only limits exercises both sides of each computed
            # upper bound; production128/16MB limits are never increased.
            with self.subTest(bound=name), patch.object(coverage, name, value - 1):
                with self.assertRaisesRegex(ValueError, message):
                    self.freeze()
            self.assertEqual(before, self.ledger.events())
            with patch.object(coverage, name, value):
                self.assertEqual(estimate, self.capacity())

    def test_append_lock_rechecks_capacity_after_competing_writer(self):
        chunks = len(self.ledger.get(self.data["reference_terminal"]["id"])["body"]["artifacts"]["projection"]["chunks"])
        self.pad(256 - 4 - 2 * (16 + chunks))
        original = self.ledger.append
        def competing(kind, body, *args, **kwargs):
            if kind == "coverage_freeze":
                other = Ledger(self.ledger.root)
                try:
                    other.append("owned_competing_write", {"capacity": "consumed after initial preflight"})
                finally:
                    other.close()
            return original(kind, body, *args, **kwargs)
        with patch.object(self.ledger, "append", competing), self.assertRaisesRegex(ValueError, "event capture capacity"):
            self.freeze()
        self.assertEqual([], self.ledger.events("coverage_freeze"))
        # The three bounded input captures may remain from the interrupted
        # attempt. They are not a ready freeze or a reservation.
        self.assertEqual(3, sum(event["body"].get("source", "").startswith("coverage-input:")
                                for event in self.ledger.events("observation")))


if __name__ == "__main__":
    unittest.main()
