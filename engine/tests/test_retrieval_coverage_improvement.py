"""Actual coverage phases drive the existing fixed controller on owned fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from epiphysics import improvement
from epiphysics.store import Ledger, canonical
from test_retrieval_coverage_preparation import make_fixture, execute_pair, study_files
from test_retrieval_coverage_assessment import diverge_repeat
from test_retrieval_improvement import fast_contracts

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "improvement"


class CoverageImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = Ledger(self.root / "evidence")
        self.addCleanup(self.evidence.close)
        self.data = make_fixture(self.root, self.evidence, gap="support_gap" in self._testMethodName)
        self.ledger = Ledger(self.root / "improvement")
        self.addCleanup(self.ledger.close)
        self.policy = json.loads((EXAMPLES / "policy.json").read_text())
        self.policy_path = self.root / "policy.json"
        self.configure()

    def configure(self, phase="preparation", runs=()):
        self.study_path, self.request, contract = study_files(self.data, self.evidence, phase, runs)
        self.policy["retrieval_study"] = contract
        self.policy_path.write_text(canonical(self.policy))

    def assess(self, key="ready", after="initial"):
        return improvement.assess(self.ledger, self.policy_path, EXAMPLES / "entities.json", "reference", key,
            after_step=after, completed_work="Owned fresh coverage " + self.request["phase"], retrieval_study_path=self.study_path)

    def test_readiness_beats_missing_baseline_without_invented_quality(self):
        with fast_contracts():
            result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        report = result["report"]
        self.assertNotIn("actual_retrieval", report)
        self.assertNotIn("retrieval_baseline_reproducibility", report["metrics"])
        self.assertNotIn("quality", report["coverage_preparation"])
        self.assertEqual("execute_fresh_coverage_baseline", result["next_step"]["action"])
        for name in ("metric", "observed", "target"):
            self.assertIsNone(result["next_step"][name])
        self.assertEqual(["fresh-a", "fresh-b"], result["next_step"]["evidence"]["run_keys"])
        self.assertFalse(next(row for row in result["next_step"]["candidate_actions"] if row["action"] == "build_retrieval_baseline")["eligible"])
        before = self.ledger.events()
        self.assertEqual(result, self.assess())
        self.assertEqual(before, self.ledger.events())
        for metric, action in (("source_span_resolution", "repair_source_span_assertions"),
                ("representation_manifest_preservation", "repair_representation_manifests"),
                ("output_manifest_materialization", "repair_transform_materialization")):
            altered = deepcopy(report)
            altered["metrics"][metric] = 0
            self.assertEqual(action, improvement.select_next(altered, "priority")["action"])

    def test_ready_then_complete_support_advances_answerability_gap_evidence(self):
        with fast_contracts():
            first = self.assess()
        runs = execute_pair(self.data, self.evidence)
        self.configure("evaluation", runs)
        with fast_contracts():
            second = self.assess("evaluated", first["next_step"]["id"])
        self.assertEqual("assessed", second["result"], second)
        self.assertEqual("prepare_answerability_evidence_gaps", second["next_step"]["action"])
        actual = second["report"]["actual_retrieval"]
        self.assertEqual(1, actual["reproducibility"]["value"])
        self.assertEqual(first["report"]["coverage_preparation"]["measurement_contract_identity"], actual["measurement_contract_identity"])
        self.assertEqual("unmeasured", second["prior_action_outcome"]["status"])
        self.assertIsNone(second["next_step"]["target"])
        self.assertEqual("none", second["next_step"]["evidence"]["coverage"]["adoption"])

    def test_measured_support_gap_advances_diagnosis_without_recipe_tuning(self):
        self.configure("evaluation", execute_pair(self.data, self.evidence))
        with fast_contracts():
            result = self.assess("evaluated")
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("inspect_fresh_support_failures", result["next_step"]["action"])
        self.assertEqual(["q-5-answerable"], result["next_step"]["evidence"]["support_gap_query_ids"])
        self.assertEqual(5 / 6, result["next_step"]["observed"])
        self.assertIsNone(result["next_step"]["target"])
        self.assertFalse(next(row for row in result["next_step"]["candidate_actions"] if row["action"] == "prepare_retrieval_representation_comparison")["eligible"])

    def test_valid_differing_repeats_queue_repair_and_omit_pair_claims(self):
        runs = execute_pair(self.data, self.evidence)
        runs[1] = diverge_repeat(self.evidence, runs[1])
        self.configure("evaluation", runs)
        with fast_contracts():
            result = self.assess("differing")
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("repair_retrieval_reproducibility", result["next_step"]["action"])
        self.assertEqual(0, result["report"]["metrics"]["retrieval_baseline_reproducibility"])
        self.assertIsNone(result["report"]["actual_retrieval"]["coverage"]["matched_pairs"])

    def test_invalid_preparation_has_one_durable_failure_and_no_quality(self):
        (self.root / "review.json").write_text("changed")
        result = self.assess()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertNotIn("report", result)
        self.assertEqual(1, len(self.ledger.events("improvement_started")))
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))
        self.assertEqual([], self.ledger.events("improvement_completed"))
        self.assertEqual(result, self.assess())

    def test_real_preparation_dispatch_preserves_inputs_and_exact_replay(self):
        before = self.evidence.events()
        result = improvement.dispatch(self.ledger.root, self.policy_path, EXAMPLES / "entities.json", "reference", "dispatched",
            completed_work="Owned preparation dispatch", retrieval_study_path=self.study_path, timeout_seconds=40)
        self.assertEqual("assessed", result["result"], result["dispatch"])
        ready = result["assessment"]["report"]["coverage_preparation"]
        self.assertEqual("ready", ready["status"])
        self.assertNotIn("quality", ready)
        self.assertEqual("execute_fresh_coverage_baseline", result["assessment"]["next_step"]["action"])
        self.assertEqual(before, self.evidence.events())
        replay = improvement.dispatch(self.ledger.root, self.policy_path, EXAMPLES / "entities.json", "reference", "dispatched",
            completed_work="Owned preparation dispatch", retrieval_study_path=self.study_path, timeout_seconds=40)
        self.assertEqual(result["assessment"], replay["assessment"])
        self.assertEqual(1, len(self.ledger.events("improvement_completed")))


if __name__ == "__main__":
    unittest.main()
