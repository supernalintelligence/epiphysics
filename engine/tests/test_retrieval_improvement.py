"""Actual local retrieval/controller integration; fixtures contain owned text only."""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import improvement, retrieval, retrieval_assessment, retrieval_evaluation
from epiphysics.store import Ledger, canonical, digest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "improvement"


@contextmanager
def fast_contracts():
    """Only orchestration unit tests replace already independently tested probes."""
    with ExitStack() as stack:
        for function, metrics in (
            ("run_source_span_checks", {"source_span_resolution": 1, "assertion_history_preservation": 1}),
            ("run_manifest_checks", {"representation_manifest_preservation": 1}),
            ("run_transformation_checks", {"transformation_preservation": 1}),
            ("run_graph_view_checks", {"split_merge_preservation": 1}),
            ("run_materialization_checks", {"output_manifest_materialization": 1}),
        ):
            stack.enter_context(patch.object(improvement, function, return_value={"metrics": metrics}))
        yield


class RetrievalImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence_path = self.root / "evidence"
        evidence = Ledger(self.evidence_path)
        try:
            # Repeated lexical noise outranks the final support passage. This
            # deliberately demonstrates valid reproduction with poor support.
            raw = b"billing " * 2000 + b"Required support sentinel."
            source = evidence.capture("owned:billing", raw, event_id="source")
            snapshot = evidence.snapshot()
            corpus = retrieval.freeze_retrieval_corpus(evidence, snapshot["id"], [source["id"]], event_id="corpus")
            gold = {"observation_id": source["id"], "start": len(raw) - 26, "end": len(raw), "sha256": digest(raw[-26:])}
            self.cohort = {"schema_version": 1, "snapshot_id": snapshot["id"], "cohort": "development", "cases": [
                {"question_id": "support", "query": "billing", "answerability": "answerable", "gold_spans": [gold]},
                {"question_id": "unsupported", "query": "billing nonexistent detail", "answerability": "unanswerable", "gold_spans": []},
            ]}
            queries = retrieval_evaluation.project_queries(self.cohort)
            self.runs = [retrieval.run_lexical_retrieval(evidence, corpus["id"], queries, run_key=key) for key in ("a", "b")]
            self.assertTrue(all(run["kind"] == "retrieval_completed" for run in self.runs))
            evaluated = retrieval_evaluation.evaluate_retrieval(evidence, self.cohort, self.runs[0]["id"])
            identity = evaluated["identity"]
            self.contract = {"schema_version": 1, "study_id": "owned-study", **{key: identity[key] for key in (
                "snapshot_id", "snapshot_hash", "snapshot_manifest_hash", "corpus_id", "corpus_hash", "cohort_hash",
                "gold_hash", "query_hash", "sources_hash", "passages_hash", "config_hash")},
                "implementation_hash": identity["retriever_implementation_hash"],
                "dependency_hashes": {name: ref["content_hash"] for name, ref in identity["retriever_artifacts"]["dependencies"].items()},
                "runtime_hash": identity["retriever_runtime_hash"],
                "run_terminal_hashes": {run["id"]: run["hash"] for run in self.runs}}
            self.original_events = evidence.events()
        finally:
            evidence.close()
        self.cohort_path = self.root / "cohort.json"
        self.cohort_path.write_text(canonical(self.cohort))
        self.study = {"schema_version": 1, "study_id": "owned-study", "evidence_store": str(self.evidence_path),
                      "cohort_file": str(self.cohort_path), "corpus_id": "corpus", "run_terminal_ids": [run["id"] for run in self.runs]}
        self.study_path = self.root / "study.json"
        self.study_path.write_text(canonical(self.study))
        self.policy = json.loads((EXAMPLES / "policy.json").read_text())
        self.policy["retrieval_study"] = self.contract
        self.policy_path = self.root / "policy.json"
        self.policy_path.write_text(canonical(self.policy))
        self.suite_path = EXAMPLES / "entities.json"
        self.ledger = Ledger(self.root / "improvement")

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def assess(self, key="first", after="initial", **kwargs):
        return improvement.assess(self.ledger, self.policy_path, self.suite_path, "reference", key,
            after_step=after, completed_work="Evaluate the owned actual retrieval study", retrieval_study_path=self.study_path, **kwargs)

    def test_real_assessment_preserves_base_gates_and_retains_reproducible_measurement(self):
        result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        actual = result["report"]["actual_retrieval"]
        self.assertEqual(1, actual["reproducibility"]["value"])
        self.assertEqual(0, actual["quality"]["runs"][0]["metrics"]["gold_span_recall_at_k"]["5"]["value"])
        self.assertEqual(1, actual["quality"]["runs"][0]["metrics"]["unsupported_query_retrieval_rate_at_5"]["value"])
        self.assertEqual("prepare_retrieval_representation_comparison", result["next_step"]["action"])
        self.assertIsNone(result["next_step"]["target"])
        self.assertEqual(["support"], result["next_step"]["evidence"]["support_gap_query_ids"])
        self.assertEqual(30, result["report"]["metrics"]["checks"])
        self.assertEqual(1, result["report"]["metrics"]["output_manifest_materialization"])
        self.assertNotIn("retrieval_gold_span_recall_at_5", result["report"]["metrics"])
        identity = result["assessment_identity"]
        self.assertEqual(result["request"]["manifest"], identity["input_manifest"])
        self.assertEqual(actual["assessment_identity"]["hash"], identity["retrieval_assessment_hash"])
        self.assertEqual(identity["hash"], digest(canonical({key: value for key, value in identity.items() if key != "hash"}).encode()))
        count = len(self.ledger.events())
        self.assertEqual(result, self.assess())
        self.assertEqual(count, len(self.ledger.events()))
        evidence = Ledger.open_readonly(self.evidence_path)
        try:
            self.assertEqual(self.original_events, evidence.events())
        finally:
            evidence.close()
        self.assertTrue(all(event["kind"] in improvement.ALLOWED_EVENTS for event in self.ledger.events()))
        artifacts = {}
        for name, event_id in result["input_observations"].items():
            if name.startswith("retrieval-study:"):
                event = self.ledger.get(event_id)
                artifacts[name[len("retrieval-study:"):]] = (self.ledger.root / "blobs" / event["body"]["content_hash"]).read_bytes()
        shutil.rmtree(self.evidence_path)
        retained = {"artifacts": artifacts, "manifest": {role: digest(raw) for role, raw in artifacts.items()}}
        reproduced = retrieval_assessment.assess_prepared_retrieval_study(retained)
        self.assertEqual(actual, reproduced["report"])

    def test_nullable_targets_and_contract_changes_are_not_claimed_as_lift(self):
        with fast_contracts():
            first = self.assess()
            second = self.assess("second", "first:next")
        self.assertEqual("measured", second["prior_action_outcome"]["status"])
        self.assertEqual(0, second["prior_action_outcome"]["change"])
        self.assertIsNone(second["prior_action_outcome"]["target_met"])
        changed = deepcopy(second["report"])
        changed["actual_retrieval"]["measurement_contract_identity"]["hash"] = "0" * 64
        outcome = improvement._forecast_result(first["next_step"], changed, first["request"]["manifest"], second["request"]["manifest"])
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertNotIn("change", outcome)

    def test_fresh_execution_ids_change_policy_but_not_actual_measurement_contract(self):
        with fast_contracts():
            first = self.assess()
        evidence = Ledger(self.evidence_path)
        try:
            queries = retrieval_evaluation.project_queries(self.cohort)
            runs = [retrieval.run_lexical_retrieval(evidence, "corpus", queries, run_key=key) for key in ("c", "d")]
        finally:
            evidence.close()
        self.study["run_terminal_ids"] = [run["id"] for run in runs]
        self.contract["run_terminal_hashes"] = {run["id"]: run["hash"] for run in runs}
        self.study_path.write_text(canonical(self.study))
        self.policy_path.write_text(canonical(self.policy))
        with fast_contracts():
            second = self.assess("fresh-pair", "first:next")
        self.assertEqual("assessed", second["result"], second)
        self.assertNotEqual(first["request"]["manifest"]["policy"], second["request"]["manifest"]["policy"])
        old, new = (result["report"]["actual_retrieval"] for result in (first, second))
        self.assertEqual(old["candidate_identity"], new["candidate_identity"])
        self.assertEqual(old["measurement_contract_identity"], new["measurement_contract_identity"])
        self.assertNotEqual(first["assessment_identity"], second["assessment_identity"])
        self.assertEqual("measured", second["prior_action_outcome"]["status"])
        self.assertIsNone(second["prior_action_outcome"]["target_met"])

    def test_malformed_or_missing_study_is_durable_failure_and_exact_replay(self):
        self.study_path.write_text('{"schema_version":1,"schema_version":1}')
        first = self.assess()
        self.assertEqual("failed", first["result"])
        self.assertEqual("diagnose_failed_assessment", first["next_step"]["action"])
        self.assertNotIn("report", first)
        count = len(self.ledger.events())
        self.assertEqual(first, self.assess())
        self.assertEqual(count, len(self.ledger.events()))
        self.study_path.unlink()
        second = self.assess("missing", "first:diagnose")
        self.assertEqual("failed", second["result"])
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO fixture")
    def test_invalid_fifo_study_does_not_open_or_read_prefix(self):
        self.study_path.unlink()
        os.mkfifo(self.study_path)
        original_open = os.open
        def guard(path, *args, **kwargs):
            if Path(path) == self.study_path:
                raise AssertionError("Rejected FIFO must not be opened for a prefix")
            return original_open(path, *args, **kwargs)
        with patch.object(os, "open", side_effect=guard):
            prepared = improvement._prepare_retrieval(self.study_path, self.policy, self.ledger.root)
        self.assertIsNotNone(prepared["error"])
        self.assertNotIn("invalid-request-prefix", prepared["prepared"]["artifacts"])

    def test_cohort_and_declared_contract_mismatch_never_succeed_base_only(self):
        self.contract["gold_hash"] = "0" * 64
        self.policy_path.write_text(canonical(self.policy))
        result = self.assess()
        self.assertEqual("failed", result["result"])
        self.assertIn("gold_hash", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_corrupt_sqlite_study_is_durable_diagnosis_without_evidence_writes(self):
        database = self.evidence_path / "ledger.sqlite"
        database.write_bytes(b"not sqlite")
        before = {path.relative_to(self.evidence_path): path.read_bytes()
                  for path in self.evidence_path.rglob("*") if path.is_file()}
        result = self.assess()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertIn("database", result["message"].lower())
        self.assertNotIn("report", result)
        self.assertEqual(1, len(self.ledger.events("improvement_started")))
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))
        self.assertEqual([], self.ledger.events("improvement_completed"))
        after = {path.relative_to(self.evidence_path): path.read_bytes()
                 for path in self.evidence_path.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def _loop_requests(self):
        direct = self.root / "self-loop.json"
        direct.symlink_to(direct.name)
        ancestor = self.root / "ancestor-loop"
        ancestor.symlink_to(ancestor.name, target_is_directory=True)
        return (direct, ancestor / "study.json")

    def test_self_and_ancestor_symlink_loops_become_durable_assessment_diagnoses(self):
        after = "initial"
        for index, path in enumerate(self._loop_requests()):
            key = f"loop-{index}"
            result = improvement.assess(self.ledger, self.policy_path, self.suite_path, "reference", key,
                after_step=after, completed_work="Diagnose rejected study locator", retrieval_study_path=path)
            self.assertEqual("failed", result["result"])
            self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
            self.assertNotIn("report", result)
            self.assertEqual(index + 1, len(self.ledger.events("improvement_started")))
            self.assertEqual(index + 1, len(self.ledger.events("improvement_failed")))
            self.assertEqual([], self.ledger.events("improvement_completed"))
            self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
            event = self.ledger.get(f"improvement:{key}:input:retrieval-study:invalid-request")
            locator = json.loads((self.ledger.root / "blobs" / event["body"]["content_hash"]).read_bytes())
            self.assertEqual(os.path.abspath(path), locator["study_path"])
            after = result["next_step"]["id"]

    def test_self_and_ancestor_symlink_loops_become_durable_dispatch_diagnoses(self):
        after = "initial"
        for index, path in enumerate(self._loop_requests()):
            key = f"dispatched-loop-{index}"
            result = improvement.dispatch(self.ledger.root, self.policy_path, self.suite_path, "reference", key,
                after_step=after, completed_work="Dispatch rejected study locator", retrieval_study_path=path,
                timeout_seconds=10)
            self.assertEqual("failed", result["result"])
            self.assertEqual("failed", result["dispatch"]["assessment_status"])
            self.assertEqual(f"improvement:{key}:failed", result["dispatch"]["authoritative_transition_id"])
            failure = self.ledger.get(f"improvement:{key}:failed")["body"]
            self.assertEqual("diagnose_failed_assessment", failure["next_step"]["action"])
            self.assertNotIn("report", failure)
            self.assertEqual(index + 1, len(self.ledger.events("improvement_started")))
            self.assertEqual(index + 1, len(self.ledger.events("improvement_failed")))
            self.assertEqual([], self.ledger.events("improvement_completed"))
            self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
            after = failure["next_step"]["id"]

    def test_embedded_evidence_locator_resolution_error_is_also_durable(self):
        ancestor = self.root / "evidence-loop"
        ancestor.symlink_to(ancestor.name, target_is_directory=True)
        locator = ancestor / "store"
        self.study["evidence_store"] = str(locator)
        self.study_path.write_text(canonical(self.study))
        original_resolve = Path.resolve
        def resolve(path, *args, **kwargs):
            if path == locator:
                # Older supported Python versions raise RuntimeError here;
                # newer versions may surface the loop as an OSError instead.
                raise RuntimeError("Symlink loop in evidence locator")
            return original_resolve(path, *args, **kwargs)
        with patch.object(Path, "resolve", resolve):
            result = self.assess()
        self.assertEqual("failed", result["result"])
        self.assertIn("Symlink loop", result["message"])
        self.assertEqual(1, len(self.ledger.events("improvement_started")))
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_captured_transport_uses_original_bytes_and_checks_policy_binding(self):
        prepared = improvement._prepare_retrieval(self.study_path, self.policy, self.ledger.root)
        path, _ = improvement._write_retrieval_preparation(self.root / "transport", prepared)
        shutil.rmtree(self.evidence_path)
        self.cohort_path.write_text("corrupt after capture")
        with fast_contracts():
            result = self.assess(_prepared_retrieval_path=path)
        self.assertEqual("assessed", result["result"], result)
        self.policy["retrieval_study"] = {**self.contract, "gold_hash": "0" * 64}
        self.policy_path.write_text(canonical(self.policy))
        result = self.assess("changed-policy", "first:next", _prepared_retrieval_path=path)
        self.assertEqual("failed", result["result"])
        self.assertIn("does not match", result["message"])

    def test_changed_transport_and_same_store_are_diagnosed(self):
        prepared = improvement._prepare_retrieval(self.study_path, self.policy, self.ledger.root)
        path, _ = improvement._write_retrieval_preparation(self.root / "transport", prepared)
        artifact = path.parent / "000.bin"
        artifact.write_bytes(artifact.read_bytes() + b"changed")
        result = self.assess(_prepared_retrieval_path=path)
        self.assertEqual("failed", result["result"])
        self.assertIn("changed", result["message"])
        self.study["evidence_store"] = str(self.ledger.root)
        self.study_path.write_text(canonical(self.study))
        result = self.assess("same-store", "first:diagnose")
        self.assertEqual("failed", result["result"])
        self.assertIn("distinct", result["message"])

    def test_all_existing_repairs_take_priority_over_actual_quality(self):
        with fast_contracts():
            report = self.assess()["report"]
        for metric, value, action in (
            ("temporal_violations", 1, "repair_time_eligibility"), ("provenance", 0, "repair_evidence_mapping"),
            ("coverage", 0, "cover_missing_answers"), ("worst_family_accuracy", 0, "repair_weakest_entity_family"),
            ("source_span_resolution", 0, "repair_source_span_assertions"), ("assertion_history_preservation", 0, "repair_source_span_assertions"),
            ("representation_manifest_preservation", 0, "repair_representation_manifests"),
            ("transformation_preservation", 0, "repair_graph_transformations"), ("split_merge_preservation", 0, "repair_graph_views"),
            ("output_manifest_materialization", 0, "repair_transform_materialization"),
        ):
            changed = deepcopy(report)
            changed["metrics"][metric] = value
            self.assertEqual(action, improvement.select_next(changed, "priority")["action"])
        changed = deepcopy(report)
        changed["actual_retrieval"]["reproducibility"]["value"] = 0
        self.assertEqual("repair_retrieval_reproducibility", improvement.select_next(changed, "mismatch")["action"])
        for cutoff in ("1", "3", "5"):
            report["actual_retrieval"]["quality"]["runs"][0]["metrics"]["gold_span_recall_at_k"][cutoff]["value"] = 1
        self.assertEqual("prepare_retrieval_coverage_evaluation", improvement.select_next(report, "no-gap")["action"])

    def test_boundary_mutation_refuses_completed_assessment(self):
        append = self.ledger.append
        def mutate(kind, body, *args, **kwargs):
            if kind == "improvement_completed":
                body["report"]["actual_retrieval"]["reproducibility"]["value"] = 0
            return append(kind, body, *args, **kwargs)
        with fast_contracts(), patch.object(self.ledger, "append", side_effect=mutate):
            result = self.assess()
        self.assertEqual("failed", result["result"])
        self.assertIn("result changed", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_real_dispatch_uses_captured_inputs_and_replay_remains_exact(self):
        real_popen = subprocess.Popen
        def remove_sources(arguments, **kwargs):
            self.assertIn("--prepared-retrieval-study", arguments)
            shutil.rmtree(self.evidence_path)
            self.cohort_path.unlink()
            return real_popen(arguments, **kwargs)
        with patch.object(improvement.subprocess, "Popen", side_effect=remove_sources):
            result = improvement.dispatch(self.ledger.root, self.policy_path, self.suite_path, "reference", "spawned",
                completed_work="Actual retrieval dispatch", retrieval_study_path=self.study_path, timeout_seconds=40)
        self.assertEqual("assessed", result["result"], result["dispatch"])
        self.assertEqual("prepare_retrieval_representation_comparison", result["assessment"]["next_step"]["action"])
        directory = Path(result["dispatch"]["receipt_directory"])
        path = directory / "retrieval-input" / "manifest.json"
        count = len(self.ledger.events())
        replay = improvement.assess(self.ledger, self.policy_path, self.suite_path, "reference", "spawned",
            completed_work="Actual retrieval dispatch", _prepared_retrieval_path=path)
        self.assertEqual(result["assessment"], replay)
        self.assertEqual(count, len(self.ledger.events()))

    def test_dispatch_parent_child_manifest_change_is_durable_diagnosis(self):
        real_popen = subprocess.Popen
        def change_policy(arguments, **kwargs):
            self.policy["version"] = "changed-after-parent-preparation"
            self.policy_path.write_text(canonical(self.policy))
            return real_popen(arguments, **kwargs)
        with patch.object(improvement.subprocess, "Popen", side_effect=change_policy):
            result = improvement.dispatch(self.ledger.root, self.policy_path, self.suite_path, "reference", "changed-input",
                completed_work="Check parent-child byte identity", retrieval_study_path=self.study_path, timeout_seconds=10)
        self.assertEqual("failed", result["result"])
        self.assertEqual("failed", result["dispatch"]["assessment_status"])
        self.assertEqual("improvement:changed-input:failed", result["dispatch"]["authoritative_transition_id"])
        failure = self.ledger.events("improvement_failed")[0]["body"]
        self.assertIn("dispatcher's prepared request", failure["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])


if __name__ == "__main__":
    unittest.main()
