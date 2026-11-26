import copy
import json
import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from epiphysics import improvement
from epiphysics.store import Ledger


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "improvement"


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = self.root / "ledger"
        self.policy = self.root / "policy.json"
        self.suite = self.root / "entities.json"
        self.policy.write_bytes((EXAMPLES / "policy.json").read_bytes())
        self.suite.write_bytes((EXAMPLES / "entities.json").read_bytes())
        self.ledger = Ledger(self.store)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def run_assessment(self, candidate="reference", run_key="first", after="initial", work="Run a synthetic control"):
        return improvement.assess(self.ledger, self.policy, self.suite, candidate, run_key,
                                  after_step=after, completed_work=work)

    def test_completion_atomically_queues_successor_and_replay_is_noop(self):
        result = self.run_assessment()
        events = self.ledger.events()
        self.assertEqual("improvement_completed", events[-1]["kind"])
        self.assertEqual(result["next_step"], events[-1]["body"]["next_step"])
        self.assertEqual("build_source_span_assertions", result["next_step"]["action"])
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertEqual(0, result["actual_resources"]["external_spend"])
        self.assertEqual(result, self.run_assessment())
        self.assertEqual(len(events), len(self.ledger.events()))
        self.assertEqual("first:next", improvement.status(self.ledger)["next_step"]["id"])
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.run_assessment(work="A different completion claim")
        with self.assertRaisesRegex(ValueError, "Stale predecessor"):
            self.run_assessment(run_key="second")

    def test_measured_failure_selects_repair_and_next_assessment_records_outcome(self):
        first = self.run_assessment("degraded")
        self.assertLess(first["report"]["metrics"]["accuracy"], 1)
        self.assertNotEqual("build_source_span_assertions", first["next_step"]["action"])
        second = self.run_assessment(run_key="second", after="first:next")
        self.assertEqual("measured", second["prior_action_outcome"]["status"])
        self.assertTrue(second["prior_action_outcome"]["target_met"])
        self.assertIsNone(first["next_step"]["estimated_success_probability"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_changed_inputs_cannot_reuse_run_key(self):
        self.run_assessment()
        policy = json.loads(self.policy.read_text())
        policy["version"] = "different"
        self.policy.write_text(json.dumps(policy))
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.run_assessment()

    def test_removing_a_failed_check_cannot_be_reported_as_improvement(self):
        first = self.run_assessment("degraded")
        failed_case = next(case for case in first["report"]["cases"] if any(not check["correct"] for check in case["checks"]))
        failed_id = next(check["id"] for check in failed_case["checks"] if not check["correct"])
        suite = json.loads(self.suite.read_text())
        case = next(case for case in suite["cases"] if case["id"] == failed_case["id"])
        case["checks"] = [check for check in case["checks"] if check["id"] != failed_id]
        self.suite.write_text(json.dumps(suite))
        second = self.run_assessment(run_key="second", after="first:next")
        outcome = second["prior_action_outcome"]
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertEqual(["suite"], outcome["changed_inputs"])
        self.assertNotIn("change", outcome)
        self.assertNotIn("target_met", outcome)
        self.assertEqual(29, second["report"]["metrics"]["checks"])
        self.assertEqual("second:next", improvement.status(self.ledger)["next_step"]["id"])

    def test_comparison_requires_policy_and_evaluator_but_allows_candidate_and_controller_changes(self):
        previous = {"id": "step", "metric": "accuracy", "observed": 0.5, "target": 1, "direction": "increase"}
        report = {"metrics": {"accuracy": 1}}
        manifest = {"suite": "s", "policy": "p", "evaluator": "e", "candidate": "a", "controller": "c"}
        for key in ("policy", "evaluator"):
            outcome = improvement._forecast_result(previous, report, manifest, {**manifest, key: "changed"})
            self.assertEqual("incomparable_contract_change", outcome["status"])
            self.assertEqual([key], outcome["changed_inputs"])
            self.assertNotIn("change", outcome)
            self.assertNotIn("target_met", outcome)
        outcome = improvement._forecast_result(previous, report, manifest,
                                               {**manifest, "candidate": "b", "controller": "new-controller"})
        self.assertEqual("measured", outcome["status"])
        self.assertEqual(0.5, outcome["change"])

    def test_unauthorized_stage_budget_and_dropped_family_are_refused_before_claim(self):
        original = json.loads(self.policy.read_text())
        variants = [{"stage": "production"}, {"allow_scale_change": True}, {"external_spend": 1},
                    {"max_assessment_seconds": 0}, {"max_assessment_seconds": True}, {"schema_version": True},
                    {"required_families": original["required_families"][:-1]}]
        for change in variants:
            with self.subTest(change=change):
                policy = {**original, **change}
                self.policy.write_text(json.dumps(policy))
                with self.assertRaises(ValueError):
                    self.run_assessment()
                self.assertEqual([], self.ledger.events())

    def test_runtime_failure_preserves_inputs_and_queues_diagnosis(self):
        with patch.object(improvement, "evaluate", side_effect=ValueError("Bad candidate schema")):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertEqual(5, len(self.ledger.events("observation")))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
        self.assertEqual(result, self.run_assessment())

    def test_elapsed_budget_violation_is_failure_not_success(self):
        with patch.object(improvement.time, "monotonic", side_effect=[0, 31]):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertIn("budget", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_interrupted_run_and_mixed_or_corrupt_store_cannot_continue(self):
        self.ledger.append("improvement_started", {"run_key": "crashed"})
        with self.assertRaisesRegex(ValueError, "Interrupted"):
            self.run_assessment()
        self.ledger.append("foreign", {})
        with self.assertRaisesRegex(ValueError, "dedicated"):
            improvement.status(self.ledger)
        self.ledger.db.execute("DROP TRIGGER events_no_update")
        self.ledger.db.execute("UPDATE events SET body='{}' WHERE kind='foreign'")
        self.ledger.db.execute("UPDATE events SET recorded_at='2020-01-01T00:00:00Z' WHERE kind='foreign'")
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError, "integrity"):
            improvement.status(self.ledger)

    def test_concurrent_workers_cannot_claim_same_successor(self):
        self.run_assessment()
        barrier = threading.Barrier(2)
        results = []
        def worker(key):
            ledger = Ledger(self.store)
            try:
                barrier.wait()
                result = improvement.assess(ledger, self.policy, self.suite, "reference", key,
                    after_step="first:next", completed_work="Concurrent fixture assessment")
                results.append(result["result"])
            except ValueError:
                results.append("refused")
            finally:
                ledger.close()
        threads = [threading.Thread(target=worker, args=(key,)) for key in ("second", "third")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertCountEqual(["assessed", "refused"], results)
        self.assertEqual(2, len(self.ledger.events("improvement_completed")))

    def test_locked_claim_rechecks_run_key_after_stale_preflight_read(self):
        self.run_assessment()
        original = improvement._checked_events
        calls = 0
        def stale_once(ledger):
            nonlocal calls
            calls += 1
            return [] if calls == 1 else original(ledger)
        with patch.object(improvement, "_checked_events", side_effect=stale_once):
            with self.assertRaisesRegex(ValueError, "already claimed"):
                self.run_assessment(run_key="first", after="first:next", work="Stale worker reuses key")
        self.assertEqual(1, len(self.ledger.events("improvement_started")))
        self.assertEqual(1, len(self.ledger.events("improvement_completed")))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])

    def test_metric_priority_does_not_hide_weak_family_in_average(self):
        report = {"metrics": {"temporal_violations": 0, "provenance": 1, "coverage": 1,
                              "worst_family_accuracy": 0.5, "accuracy": 0.98},
                  "families": {"organization": {"accuracy": 1}, "collective": {"accuracy": 0.5}}}
        decision = improvement.select_next(report, "case")
        self.assertEqual("repair_weakest_entity_family", decision["action"])
        self.assertEqual("collective", decision["family"])
        report["metrics"]["temporal_violations"] = 1
        self.assertEqual("repair_time_eligibility", improvement.select_next(report, "case")["action"])

    def test_real_dispatch_executes_fixed_program_and_preserves_receipts(self):
        result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "spawned",
                                      completed_work="Execute a synthetic oracle control", timeout_seconds=10)
        self.assertEqual("assessed", result["result"])
        receipt = result["dispatch"]
        directory = Path(receipt["receipt_directory"])
        self.assertEqual("epiphysics.improvement assess", receipt["program"])
        self.assertNotEqual(os.getpid(), receipt["pid"])
        self.assertEqual(0, receipt["returncode"])
        self.assertTrue((directory / "start.json").is_file())
        self.assertTrue((directory / "finish.json").is_file())
        self.assertLessEqual((directory / "output.log").stat().st_size, improvement.MAX_BYTES)
        self.assertEqual("spawned:next", improvement.status(self.ledger)["next_step"]["id"])
        claim = self.ledger.events("improvement_started")[0]["body"]
        self.assertEqual(receipt["dispatch_id"], claim["worker"]["dispatch_id"])
        self.assertEqual(receipt["pid"], claim["worker"]["pid"])
        count = len(self.ledger.events())
        replay = improvement.dispatch(self.store, self.policy, self.suite, "reference", "spawned",
                                      completed_work="Execute a synthetic oracle control", timeout_seconds=10)
        self.assertEqual("assessed", replay["result"])
        self.assertEqual(count, len(self.ledger.events()))

    def test_real_hard_timeout_reaps_child_and_queues_owned_diagnosis(self):
        real_popen = subprocess.Popen
        code = """import os,time
from epiphysics.store import Ledger
ledger=Ledger(os.environ['TEST_STORE'])
ledger.append('improvement_started', {'run_key':'timed','request':{'after_step':'initial'},
 'claimed_step':{'id':'initial'},'worker':{'dispatch_id':os.environ['EPIPHYSICS_DISPATCH_ID'],'pid':os.getpid()}})
ledger.close()
print('owned claim made',flush=True)
time.sleep(30)
"""
        def slow_worker(arguments, **kwargs):
            kwargs["env"]["TEST_STORE"] = str(self.store)
            return real_popen([arguments[0], "-c", code], **kwargs)
        with patch.object(improvement.subprocess, "Popen", side_effect=slow_worker):
            result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "timed",
                                          completed_work="Timeout fixture", timeout_seconds=1)
        self.assertEqual("failed", result["result"])
        self.assertEqual("timeout", result["dispatch"]["termination"])
        self.assertEqual("diagnosis_queued", result["dispatch"]["recovery"])
        self.assertEqual("timed:diagnose", improvement.status(self.ledger)["next_step"]["id"])
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
        with self.assertRaises(ChildProcessError):
            os.waitpid(result["dispatch"]["pid"], os.WNOHANG)

    def test_output_limit_reaps_worker_without_inventing_a_claim(self):
        real_popen = subprocess.Popen
        def noisy_worker(arguments, **kwargs):
            return real_popen([arguments[0], "-c", "import sys,time;sys.stdout.write('x'*1100000);sys.stdout.flush();time.sleep(30)"], **kwargs)
        with patch.object(improvement.subprocess, "Popen", side_effect=noisy_worker):
            result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "noisy",
                                          completed_work="Output-limit fixture", timeout_seconds=10)
        self.assertEqual("failed", result["result"])
        self.assertEqual("output_limit", result["dispatch"]["termination"])
        self.assertEqual(improvement.MAX_BYTES, result["dispatch"]["output_bytes"])
        self.assertEqual("no_owned_claim", result["dispatch"]["recovery"])
        self.assertEqual([], self.ledger.events())

    def test_completed_large_assessment_survives_failed_output_delivery(self):
        original = json.loads(self.suite.read_text())
        suite = {"schema_version": 1, "cases": []}
        for i in range(100):
            case = copy.deepcopy(original["cases"][i % len(original["cases"])] )
            case["id"] = f"large-case-{i}"
            checks = case["checks"]
            case["checks"] = [{**copy.deepcopy(checks[j % len(checks)]), "id": f"check-{j}"} for j in range(30)]
            suite["cases"].append(case)
        self.suite.write_text(json.dumps(suite))
        self.assertLess(self.suite.stat().st_size, improvement.MAX_BYTES)
        result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "large",
                                      completed_work="Exercise bounded delivery after a completed assessment", timeout_seconds=10)
        self.assertEqual("assessment_completed_delivery_failed", result["result"])
        self.assertEqual("output_limit", result["dispatch"]["termination"])
        self.assertEqual("completed", result["dispatch"]["assessment_status"])
        self.assertEqual("failed", result["dispatch"]["delivery_status"])
        self.assertEqual("already_finished", result["dispatch"]["recovery"])
        self.assertEqual("improvement:large:complete", result["dispatch"]["authoritative_transition_id"])
        self.assertIsNone(result["assessment"])
        self.assertEqual("large:next", result["authoritative_transition"]["next_step"]["id"])
        self.assertLess(len(json.dumps(result)), 20000)
        self.assertEqual(1, len(self.ledger.events("improvement_completed")))
        self.assertEqual([], self.ledger.events("improvement_failed"))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
        count = len(self.ledger.events())
        replay = improvement.dispatch(self.store, self.policy, self.suite, "reference", "large",
                                      completed_work="Exercise bounded delivery after a completed assessment", timeout_seconds=10)
        self.assertEqual("assessment_completed_delivery_failed", replay["result"])
        self.assertEqual("improvement:large:complete", replay["dispatch"]["authoritative_transition_id"])
        self.assertEqual(count, len(self.ledger.events()))
        mismatched = improvement.dispatch(self.store, self.policy, self.suite, "degraded", "large",
                                         completed_work="Exercise bounded delivery after a completed assessment", timeout_seconds=10)
        self.assertEqual("failed", mismatched["result"])
        self.assertEqual("not_confirmed", mismatched["dispatch"]["assessment_status"])
        self.assertIsNone(mismatched["dispatch"]["authoritative_transition_id"])
        self.assertEqual(count, len(self.ledger.events()))

    def test_recovery_cannot_close_another_worker_or_overwrite_completion(self):
        result = self.run_assessment()
        count = len(self.ledger.events())
        self.assertEqual("no_owned_claim", improvement._recover_reaped_dispatch(
            self.store, "first", "someone-else", 123, "timeout"))
        self.assertEqual(count, len(self.ledger.events()))
        self.assertEqual(result["next_step"], improvement.status(self.ledger)["next_step"])
        self.ledger.append("improvement_started", {"run_key": "owned", "request": {},
            "worker": {"dispatch_id": "mine", "pid": 456}})
        self.ledger.append("improvement_completed", {"run_key": "owned", "next_step": {"id": "done"}})
        count = len(self.ledger.events())
        self.assertEqual("already_finished", improvement._recover_reaped_dispatch(
            self.store, "owned", "mine", 456, "timeout"))
        self.assertEqual(count, len(self.ledger.events()))

    def test_invalid_dispatch_budget_is_refused(self):
        for timeout in (0, -1, 61, float("inf"), float("nan"), True):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    improvement.dispatch(self.store, self.policy, self.suite, "reference", "bad",
                                         completed_work="Invalid timeout", timeout_seconds=timeout)
        self.assertFalse((self.store / "dispatches").exists())


if __name__ == "__main__":
    unittest.main()
