"""Diagnosis consumes a real owned controller origin through the fixed handoff."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from epiphysics import improvement
from epiphysics.store import Ledger, canonical
from test_retrieval_coverage_preparation import study_files
from test_retrieval_diagnosis import make_diagnosis_fixture, bind_diagnosis, rehash
from test_retrieval_improvement import fast_contracts

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "improvement"


class DiagnosisImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = Ledger(self.root / "evidence")
        self.addCleanup(self.evidence.close)
        self.data = make_diagnosis_fixture(self.root, self.evidence, multiple="deferred" in self._testMethodName)
        self.ledger = Ledger(self.root / "improvement")
        self.addCleanup(self.ledger.close)
        self.policy = json.loads((EXAMPLES / "policy.json").read_text())
        self.policy_path = self.root / "policy.json"
        path, _, declaration = study_files(self.data, self.evidence, "evaluation", self.data["runs"])
        self.policy["retrieval_study"] = declaration
        self.policy_path.write_text(canonical(self.policy))
        with fast_contracts():
            first = improvement.assess(self.ledger, self.policy_path, EXAMPLES / "entities.json", "reference", "origin",
                completed_work="Owned repeated coverage with failed support", retrieval_study_path=path)
        self.assertEqual("assessed", first["result"], first)
        self.assertEqual("inspect_fresh_support_failures", first["next_step"]["action"])
        self.origin = self.ledger.get("improvement:origin:complete")
        self.after = first["next_step"]["id"]
        self.configure()

    def configure(self, *, origin=None, categories=None):
        self.path, self.request, self.contract, self.review = bind_diagnosis(
            self.data, self.evidence, self.origin if origin is None else origin, categories=categories)
        self.policy["retrieval_study"] = self.contract
        self.policy_path.write_text(canonical(self.policy))

    def assess(self, key="diagnosed", after=None):
        return improvement.assess(self.ledger, self.policy_path, EXAMPLES / "entities.json", "reference", key,
            after_step=self.after if after is None else after, completed_work="Owned checked support diagnosis", retrieval_study_path=self.path)

    def test_checked_diagnosis_has_unmeasured_atomic_successor_and_exact_replay(self):
        before = self.evidence.events()
        with fast_contracts():
            result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("prepare_focused_support_followup", result["next_step"]["action"])
        self.assertEqual("unmeasured", result["prior_action_outcome"]["status"])
        self.assertNotIn("actual_retrieval", result["report"])
        self.assertNotIn("retrieval_baseline_reproducibility", result["report"]["metrics"])
        for field in ("metric", "observed", "target", "estimated_success_probability", "estimated_cost"):
            self.assertIsNone(result["next_step"][field])
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertEqual(result, self.ledger.get("improvement:diagnosed:complete")["body"])
        events = self.ledger.events()
        self.assertEqual(result, self.assess())
        self.assertEqual(events, self.ledger.events())
        self.assertEqual(before, self.evidence.events())
        for metric, action in (("source_span_resolution", "repair_source_span_assertions"),
                ("representation_manifest_preservation", "repair_representation_manifests"),
                ("output_manifest_materialization", "repair_transform_materialization")):
            report = deepcopy(result["report"])
            report["metrics"][metric] = 0
            self.assertEqual(action, improvement.select_next(report, "priority")["action"])
        changed = {**self.request, "diagnosis_id": "different"}
        self.path.write_text(canonical(changed))
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.assess()
        self.assertEqual(events, self.ledger.events())

    def test_annotation_gap_selects_clarification(self):
        self.configure(categories={"q-5-answerable": "annotation_gap"})
        with fast_contracts():
            result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("clarify_support_diagnosis", result["next_step"]["action"])

    def test_unresolved_selects_clarification(self):
        self.configure(categories={"q-5-answerable": "unresolved"})
        with fast_contracts():
            result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("clarify_support_diagnosis", result["next_step"]["action"])

    def test_deferred_failure_selects_clarification(self):
        with fast_contracts():
            result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("clarify_support_diagnosis", result["next_step"]["action"])
        self.assertEqual(["q-4-answerable"], result["next_step"]["evidence"]["deferred_question_ids"])

    def test_self_consistent_forged_origin_fails_durably_and_replays(self):
        forged = deepcopy(self.origin)
        forged["body"]["completed_work"] = "Forged extra claim"
        rehash(forged)
        self.configure(origin=forged)
        result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertIn("actual completed predecessor", result["message"])
        events = self.ledger.events()
        self.assertEqual(result, self.assess())
        self.assertEqual(events, self.ledger.events())
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))
        self.assertEqual(2, len(self.ledger.events("improvement_started")))

    def test_malformed_origin_fails_durably_but_stale_predecessor_never_claims(self):
        Path(self.request["origin_file"]).write_text("malformed")
        before = self.ledger.events()
        with self.assertRaisesRegex(ValueError, "Stale predecessor"):
            self.assess(after="initial")
        self.assertEqual(before, self.ledger.events())
        result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertEqual(result, self.assess())

    def test_live_ledger_corruption_at_claim_never_appends_start_or_failure(self):
        before = self.ledger.events()
        original_append = self.ledger.append
        def append(kind, body, *args, **kwargs):
            if kind == "improvement_started":
                validate = kwargs["validate"]
                def corrupt_then_validate(now):
                    self.ledger.db.execute("DROP TRIGGER events_no_update")
                    self.ledger.db.execute("UPDATE events SET hash=? WHERE id=?", ("0" * 64, self.origin["id"]))
                    validate(now)
                kwargs["validate"] = corrupt_then_validate
            return original_append(kind, body, *args, **kwargs)
        with patch.object(self.ledger, "append", side_effect=append):
            with self.assertRaisesRegex(ValueError, "Ledger integrity failed"):
                self.assess()
        # The rejected append rolls back this owned corruption injection too.
        self.assertEqual(before, self.ledger.events())
        self.assertTrue(self.ledger.verify()["valid"])

    def test_completion_rechecks_deterministic_result(self):
        original_append = self.ledger.append
        def append(kind, body, *args, **kwargs):
            if kind == "improvement_completed":
                body["report"]["support_diagnosis"]["machine_findings"]["hash"] = "0" * 64
            return original_append(kind, body, *args, **kwargs)
        with fast_contracts(), patch.object(self.ledger, "append", side_effect=append):
            result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertIn("changed before completion", result["message"])
        self.assertEqual(1, len(self.ledger.events("improvement_completed")))
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))

    def test_two_workers_cannot_consume_the_same_diagnosis_origin(self):
        barrier = threading.Barrier(2)
        results = []
        def worker(key):
            ledger = Ledger(self.ledger.root)
            try:
                barrier.wait()
                value = improvement.assess(ledger, self.policy_path, EXAMPLES / "entities.json", "reference", key,
                    after_step=self.after, completed_work="Owned competing diagnosis", retrieval_study_path=self.path)
                results.append(value["result"])
            except ValueError:
                results.append("refused")
            finally:
                ledger.close()
        threads = [threading.Thread(target=worker, args=(key,)) for key in ("worker-a", "worker-b")]
        with fast_contracts():
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=45)
                self.assertFalse(thread.is_alive())
        self.assertCountEqual(["assessed", "refused"], results)
        self.assertEqual(2, len(self.ledger.events("improvement_completed")))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])

    def test_real_fixed_dispatch_and_completed_replay_preserve_source_store(self):
        before = self.evidence.events()
        kwargs = dict(after_step=self.after, completed_work="Owned dispatched support diagnosis", retrieval_study_path=self.path, timeout_seconds=60)
        result = improvement.dispatch(self.ledger.root, self.policy_path, EXAMPLES / "entities.json", "reference", "dispatched", **kwargs)
        self.assertEqual("assessed", result["result"], result.get("dispatch"))
        self.assertEqual("prepare_focused_support_followup", result["assessment"]["next_step"]["action"])
        replay = improvement.dispatch(self.ledger.root, self.policy_path, EXAMPLES / "entities.json", "reference", "dispatched", **kwargs)
        self.assertEqual(result["assessment"], replay["assessment"])
        self.assertEqual(before, self.evidence.events())
        self.assertEqual(2, len(self.ledger.events("improvement_completed")))


if __name__ == "__main__":
    unittest.main()
