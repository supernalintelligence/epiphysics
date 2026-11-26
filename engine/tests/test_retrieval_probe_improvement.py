"""Fixed diagnostic consumes a real owned C5 completion exactly once."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from epiphysics import improvement, retrieval_assessment as assessment
from epiphysics.store import Ledger, canonical, digest
from test_retrieval_coverage_preparation import study_files
from test_retrieval_diagnosis import make_diagnosis_fixture, bind_diagnosis, rehash
from test_retrieval_improvement import fast_contracts
from test_retrieval_probe import make_probe_fixture

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "improvement"


class ProbeImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = Ledger(self.root / "evidence")
        self.addCleanup(self.evidence.close)
        self.ledger = Ledger(self.root / "improvement")
        self.addCleanup(self.ledger.close)
        data = make_diagnosis_fixture(self.root, self.evidence)
        self.policy = json.loads((EXAMPLES / "policy.json").read_text())
        self.policy_path = self.root / "policy.json"
        coverage_path, _, contract = study_files(data, self.evidence, "evaluation", data["runs"])
        self.set_contract(contract)
        with fast_contracts():
            result = improvement.assess(self.ledger, self.policy_path, EXAMPLES / "entities.json", "reference", "coverage",
                completed_work="Owned repeated support coverage", retrieval_study_path=coverage_path)
        self.assertEqual("assessed", result["result"], result)
        origin = self.ledger.get("improvement:coverage:complete")
        diagnosis_path, _, contract, _ = bind_diagnosis(data, self.evidence, origin)
        self.set_contract(contract)
        with fast_contracts():
            result = improvement.assess(self.ledger, self.policy_path, EXAMPLES / "entities.json", "reference", "diagnosis",
                after_step=result["next_step"]["id"], completed_work="Owned checked support gap", retrieval_study_path=diagnosis_path)
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("prepare_focused_support_followup", result["next_step"]["action"])
        self.origin = self.ledger.get("improvement:diagnosis:complete")
        self.after = result["next_step"]["id"]
        options = {"failure": "launch_error"} if "incomplete" in self._testMethodName else {}
        if "rejected_second" in self._testMethodName:
            options = {"failure": "second_rejected"}
        self.data = make_probe_fixture(self.root, self.evidence, origin=self.origin, data=data, **options)
        self.path, self.request, self.contract = (self.data[name] for name in ("request_path", "request", "contract"))
        self.set_contract(self.contract)

    def set_contract(self, contract):
        self.policy["retrieval_study"] = contract
        self.policy_path.write_text(canonical(self.policy))

    def assess(self, key="probed", after=None):
        return improvement.assess(self.ledger, self.policy_path, EXAMPLES / "entities.json", "reference", key,
            after_step=self.after if after is None else after, completed_work="Owned fixed two-clause diagnostic",
            retrieval_study_path=self.path)

    def test_checked_probe_has_atomic_unmeasured_successor_and_exact_replay(self):
        before = self.evidence.events()
        with fast_contracts():
            result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        self.assertEqual("prepare_control_exchange_decision_pilot", result["next_step"]["action"])
        self.assertEqual("unmeasured", result["prior_action_outcome"]["status"])
        self.assertNotIn("actual_retrieval", result["report"])
        self.assertNotIn("support_diagnosis", result["report"])
        self.assertNotIn("retrieval_baseline_reproducibility", result["report"]["metrics"])
        self.assertEqual("support_probe", result["report"]["support_probe"]["phase"])
        for field in ("metric", "observed", "target", "estimated_success_probability", "estimated_cost"):
            self.assertIsNone(result["next_step"][field])
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertEqual(result, self.ledger.get("improvement:probed:complete")["body"])
        events = self.ledger.events()
        def forbid_assessment(frame, event, arg):
            if event == "call" and frame.f_code.co_name == "assess_prepared_retrieval_study":
                raise AssertionError("Replay must not assess")
        sys.setprofile(forbid_assessment)
        try:
            self.assertEqual(result, self.assess())
        finally:
            sys.setprofile(None)
        self.assertEqual(events, self.ledger.events())
        self.assertEqual(before, self.evidence.events())
        self.path.write_text(canonical({**self.request, "study_id": "different"}))
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.assess()
        self.assertEqual(events, self.ledger.events())

    def test_support_outcome_never_selects_another_tuning_run_and_integrity_still_wins(self):
        with fast_contracts():
            result = self.assess()
        self.assertEqual("assessed", result["result"], result)
        for clauses, joint in ((None, None), ({"complete": False}, {"complete": False}),
                               ({"complete": True}, {"complete": True})):
            report = deepcopy(result["report"])
            report["support_probe"].update(clause_support=clauses, joint_support_union_of_two_top5=joint)
            self.assertEqual("prepare_control_exchange_decision_pilot", improvement.select_next(report, "decision")["action"])
        report = deepcopy(result["report"])
        report["support_probe"]["reproducibility"]["value"] = 0
        report["support_probe"]["clause_support"] = None
        report["support_probe"]["joint_support_union_of_two_top5"] = None
        selected = improvement.select_next(report, "disagreement")
        self.assertEqual("repair_retrieval_reproducibility", selected["action"])
        self.assertIsNone(selected["metric"])
        self.assertIsNone(selected["observed"])
        for metric, action in (("source_span_resolution", "repair_source_span_assertions"),
                ("representation_manifest_preservation", "repair_representation_manifests"),
                ("output_manifest_materialization", "repair_transform_materialization")):
            damaged = deepcopy(report)
            damaged["metrics"][metric] = 0
            self.assertEqual(action, improvement.select_next(damaged, "priority")["action"])

    def test_self_consistent_origin_forgery_is_not_the_live_predecessor(self):
        forged = deepcopy(self.origin)
        forged["body"]["completed_work"] = "A self-consistent invented history"
        rehash(forged)
        # The strict adapter independently rejects the protocol/envelope
        # mismatch. Also exercise the live predecessor check with otherwise
        # accepted input to prove that event self-integrity is insufficient.
        prepared = assessment.prepare_retrieval_study(self.path, declared_contract=self.contract)
        supplied = {"prepared": prepared, "error": None}
        with patch.object(assessment, "_probe_artifacts", return_value=forged):
            with self.assertRaisesRegex(ValueError, "actual completed predecessor"):
                improvement._check_diagnosis_origin(supplied, improvement._checked_events(self.ledger), self.after)
        Path(self.request["origin_file"]).write_text(canonical(forged))
        result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertEqual(result, self.assess())

    def test_malformed_input_fails_durably_but_stale_step_never_claims(self):
        Path(self.request["probe_execution_file"]).write_text("malformed")
        before = self.ledger.events()
        with self.assertRaisesRegex(ValueError, "Stale predecessor"):
            self.assess(after="initial")
        self.assertEqual(before, self.ledger.events())
        result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertEqual(result, self.assess())
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))

    def test_incomplete_execution_is_captured_before_durable_failure(self):
        execution_raw = Path(self.request["probe_execution_file"]).read_bytes()
        execution = json.loads(execution_raw)
        self.assertEqual(["launch_error", "not_started"], [slot["status"] for slot in execution["slots"]])
        with fast_contracts():
            result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        capture = self.ledger.get("improvement:probed:input:retrieval-study:probe_execution", "observation")
        self.assertEqual(execution_raw, (self.ledger.root / "blobs" / capture["body"]["content_hash"]).read_bytes())
        for slot in execution["slots"]:
            self.assertFalse(any(event["id"] == "retrieval:" + slot["run_key"] + ":started" for event in self.evidence.events()))
        self.assertEqual(2, len(self.ledger.events("improvement_completed")))
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))

    def test_rejected_second_retains_first_completed_and_real_rejected_receipt(self):
        execution_raw = Path(self.request["probe_execution_file"]).read_bytes()
        execution = json.loads(execution_raw)
        self.assertEqual(["completed", "rejected"], [slot["status"] for slot in execution["slots"]])
        with fast_contracts():
            result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        capture = self.ledger.get("improvement:probed:input:retrieval-study:probe_execution", "observation")
        self.assertEqual(execution_raw, (self.ledger.root / "blobs" / capture["body"]["content_hash"]).read_bytes())
        bundle = self.ledger.get("improvement:probed:input:retrieval-study:evidence_bundle", "observation")
        retained = json.loads((self.ledger.root / "blobs" / bundle["body"]["content_hash"]).read_bytes())
        for slot, kind in zip(execution["slots"], ("retrieval_completed", "retrieval_rejected")):
            event = next(event for event in retained["events"] if event["id"] == slot["terminal"]["id"])
            self.assertEqual(kind, event["kind"])
            self.assertEqual(slot["terminal"]["hash"], event["hash"])
        self.assertEqual(2, len(self.ledger.events("improvement_completed")))

    def test_live_integrity_failure_at_claim_rolls_back_without_failure_append(self):
        before = self.ledger.events()
        append = self.ledger.append
        def corrupt(kind, body, *args, **kwargs):
            if kind == "improvement_started":
                validate = kwargs["validate"]
                def validate_corruption(now):
                    self.ledger.db.execute("DROP TRIGGER events_no_update")
                    self.ledger.db.execute("UPDATE events SET hash=? WHERE id=?", ("0" * 64, self.origin["id"]))
                    validate(now)
                kwargs["validate"] = validate_corruption
            return append(kind, body, *args, **kwargs)
        with patch.object(self.ledger, "append", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "Ledger integrity failed"):
                self.assess()
        self.assertEqual(before, self.ledger.events())
        self.assertTrue(self.ledger.verify()["valid"])

    def test_completion_revalidates_probe_result(self):
        append = self.ledger.append
        def changed(kind, body, *args, **kwargs):
            if kind == "improvement_completed":
                body["report"]["support_probe"]["bindings"] = {"changed": True}
            return append(kind, body, *args, **kwargs)
        with fast_contracts(), patch.object(self.ledger, "append", side_effect=changed):
            result = self.assess()
        self.assertEqual("failed", result["result"], result)
        self.assertIn("changed before completion", result["message"])
        self.assertEqual(2, len(self.ledger.events("improvement_completed")))
        self.assertEqual(1, len(self.ledger.events("improvement_failed")))

    def test_competing_workers_cannot_consume_one_diagnosis_twice(self):
        barrier, results = threading.Barrier(2), []
        def worker(key):
            ledger = Ledger(self.ledger.root)
            try:
                barrier.wait(timeout=5)
                result = improvement.assess(ledger, self.policy_path, EXAMPLES / "entities.json", "reference", key,
                    after_step=self.after, completed_work="Owned competing probe acceptance", retrieval_study_path=self.path)
                results.append(result["result"])
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
        self.assertEqual(3, len(self.ledger.events("improvement_completed")))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])

    def test_real_dispatch_and_replay_leave_authoritative_completion_after_delivery_loss(self):
        before = self.evidence.events()
        kwargs = dict(after_step=self.after, completed_work="Owned dispatched fixed diagnostic", retrieval_study_path=self.path, timeout_seconds=60)
        result = improvement.dispatch(self.ledger.root, self.policy_path, EXAMPLES / "entities.json", "reference", "dispatched", **kwargs)
        self.assertEqual("assessed", result["result"], result.get("dispatch"))
        self.assertEqual("prepare_control_exchange_decision_pilot", result["assessment"]["next_step"]["action"])
        replay = improvement.dispatch(self.ledger.root, self.policy_path, EXAMPLES / "entities.json", "reference", "dispatched", **kwargs)
        self.assertEqual(result["assessment"], replay["assessment"])
        receipt = result["dispatch"]
        authority = improvement._dispatch_transition(self.ledger.root, "dispatched", receipt["dispatch_id"], receipt["pid"],
            None, result["assessment"]["request"])
        self.assertEqual("improvement:dispatched:complete", authority["event_id"])
        self.assertEqual("prepare_control_exchange_decision_pilot", authority["next_step"]["action"])
        self.assertEqual(before, self.evidence.events())
        self.assertEqual(3, len(self.ledger.events("improvement_completed")))


if __name__ == "__main__":
    unittest.main()
