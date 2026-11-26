"""Owned driver controls; these are not the registered twelve-case study."""
import base64
from copy import deepcopy
import json
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics import decision_pilot as pilot
from epiphysics import decision_views as views


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "control-exchange"


def trace():
    # A single already-exposed owned positive, cloned for wiring controls. The
    # actual twelve different development traces are not scored by these tests.
    return deepcopy(json.loads((EXAMPLES / "development-traces.json").read_text())["traces"][0])


def cohort():
    result = {"cohort_id": "decision-pilot-development-v1", "contract_id": views.CONTRACT_ID,
              "trace_count": 12, "final_cohort_generated": False, "traces": []}
    for index in range(12):
        item = trace()
        item["trace_id"] = "owned-unit-" + str(index)
        item["mechanism"] = "owned driver control"
        result["traces"].append(item)
    return result


def bundle(item=None):
    item = item or trace()
    return views.prepare_decision_input(item["events"], item["task"], item["cutoff"], item["decision_at"])


def local_candidate(public, recipe, budget, remaining):
    started = time.monotonic()
    request = {"header": public["header_bytes"].decode(), "tape": public["event_tape_bytes"].decode(),
               "recipe": recipe, "budget_bytes": budget}
    response = pilot._candidate(request)
    return {"error": None, "stdout": views.canonical(response), "stderr": b"", "returncode": 0,
            "request_bytes": len(views.canonical(request)), "elapsed_seconds": time.monotonic() - started}


class DecisionPilotTests(unittest.TestCase):
    def test_fixed_child_receives_only_public_input(self):
        public = bundle()
        receipt = pilot._run_candidate(public, "flat-recency-v1", 2048, 5)
        response, view, verified = pilot._verify_response(receipt, public, "flat-recency-v1", 2048)
        self.assertEqual(response["proposal"]["action"], "release")
        self.assertTrue(verified.complete)
        self.assertLessEqual(len(view), 2048)
        self.assertNotIn("trace_id", receipt["stdout"].decode())
        self.assertNotIn("later_outcome", receipt["stdout"].decode())

    def test_private_or_extra_fields_are_not_worker_arguments(self):
        public = bundle()
        request = {"header": public["header_bytes"].decode(), "tape": public["event_tape_bytes"].decode(),
                   "recipe": "flat-recency-v1", "budget_bytes": 2048, "later_outcome": {}}
        with self.assertRaises(ValueError):
            pilot._candidate(request)

    def test_wrong_support_ids_or_recipe_or_receipt_are_failed(self):
        public = bundle()
        receipt = local_candidate(public, "flat-recency-v1", 2048, 5)
        baseline = json.loads(receipt["stdout"])
        for change in (lambda value: value["proposal"].update(support_event_ids=[]),
                       lambda value: value.update(input_hash="0" * 64),
                       lambda value: value.update(complete=1),
                       lambda value: value["timings"].update(build_seconds=float("inf")),
                       lambda value: value.update(view="[]")):
            value = deepcopy(baseline)
            change(value)
            altered = {**receipt, "stdout": json.dumps(value).encode()}
            with self.assertRaises((ValueError, AttributeError)):
                pilot._verify_response(altered, public, "flat-recency-v1", 2048)
        with self.assertRaises(ValueError):
            pilot._verify_response(receipt, public, "task-proximity-v1", 2048)

    def test_timeout_kills_and_reaps_worker(self):
        started = time.monotonic()
        receipt = pilot._capture_process([sys.executable, "-c", "import time; time.sleep(10)"], b"{}", 0.08)
        self.assertEqual(receipt["error"], "worker_timeout")
        self.assertIsNotNone(receipt["returncode"])
        self.assertLess(time.monotonic() - started, 2)

    def test_combined_output_cap_and_exit_failure(self):
        receipt = pilot._capture_process([sys.executable, "-c", "import os; os.write(2,b'x'*10000)"], b"{}", 2, output_limit=512)
        self.assertEqual(receipt["error"], "worker_output_limit")
        self.assertEqual(len(receipt["stdout"]) + len(receipt["stderr"]), 513)
        receipt = pilot._capture_process([sys.executable, "-c", "raise SystemExit(7)"], b"{}", 2)
        self.assertEqual(receipt["error"], "worker_exit")
        self.assertEqual(receipt["returncode"], 7)

    def test_deadline_before_launch_and_large_request(self):
        self.assertEqual(pilot._capture_process([], b"", 0)["error"], "program_deadline")
        self.assertEqual(pilot._capture_process([], b"x" * (pilot.MAX_REQUEST_BYTES + 1), 1)["error"], "request_limit")

    def test_launch_failure_retained(self):
        with patch.object(pilot.subprocess, "Popen", side_effect=OSError("owned launch failure")):
            result = pilot._run_candidate(bundle(), "flat-recency-v1", 2048, 5)
        self.assertEqual(result["error"], "worker_launch_failed")
        self.assertIn(b"owned launch failure", result["stderr"])

    def test_all_rows_and_independent_arm_state(self):
        with patch.object(pilot, "_run_candidate", side_effect=local_candidate):
            result = pilot.run_development(cohort())
        self.assertTrue(all(result["checks"].values()), result["checks"])
        self.assertEqual(result["next_step"]["action"], "prepare_fresh_decision_comparison")
        self.assertEqual(len(result["arms"]), 4)
        for arm in result["arms"]:
            self.assertEqual(len(arm["rows"]), 12)
            self.assertEqual(arm["summary"]["metrics"]["valid_timely_release"]["numerator"], 12)
            self.assertEqual(arm["summary"]["metrics"]["duplicate_effects"]["numerator"], 0)

    def test_all_failures_remain_in_denominators(self):
        failed = {"error": "owned_worker_failure", "stdout": b"\xff", "stderr": b"reason", "returncode": 1,
                  "request_bytes": 1, "elapsed_seconds": 0.01}
        with patch.object(pilot, "_run_candidate", return_value=failed):
            result = pilot.run_development(cohort())
        self.assertEqual(result["next_step"]["action"], "repair_decision_pilot")
        self.assertFalse(result["checks"]["all_outputs_valid"])
        for arm in result["arms"]:
            self.assertEqual(arm["summary"]["metrics"]["valid_output_completion"]["denominator"], 12)
            self.assertEqual(arm["summary"]["metrics"]["missed_world_opportunities"]["numerator"], 12)
            self.assertEqual(base64.b64decode(arm["rows"][0]["worker_receipt"]["stdout_base64"]), b"\xff")

    def test_complete_bounded_policy_divergence_selects_repair(self):
        def changed(*args):
            receipt = local_candidate(*args)
            if args[2] == 2048:
                response = json.loads(receipt["stdout"])
                response["proposal"].update(action="hold", reason="incomplete_evidence")
                receipt["stdout"] = views.canonical(response)
            return receipt
        with patch.object(pilot, "_run_candidate", side_effect=changed):
            result = pilot.run_development(cohort())
        self.assertTrue(result["checks"]["all_outputs_valid"])
        self.assertTrue(result["checks"]["lossless_reference_parity"])
        self.assertFalse(result["checks"]["fixed_policy_conformance"])
        self.assertEqual(result["next_step"]["action"], "repair_decision_pilot")

    def test_parent_failure_preserves_returned_worker_before_evaluation(self):
        from epiphysics import decision_evaluation as evaluation
        with tempfile.TemporaryDirectory() as directory:
            incoming, output = Path(directory) / "owned.json", Path(directory) / "result.json"
            incoming.write_bytes(views.canonical(cohort()))
            with patch.object(pilot, "_run_candidate", side_effect=local_candidate), patch.object(
                    evaluation, "evaluate_simulated_proposal", side_effect=ValueError("owned evaluator failure")):
                self.assertEqual(pilot.main(["--cohort", str(incoming), "--output", str(output)]), 1)
            result = json.loads(output.read_text())
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["metrics"])
            journal = [json.loads(line) for line in Path(str(output) + ".attempts.jsonl").read_text().splitlines()]
            self.assertEqual([row["kind"] for row in journal], ["declared_run", "worker_returned", "run_terminal"])
            self.assertGreater(journal[1]["receipt"]["stdout_bytes"], 0)
            self.assertEqual(len(journal[0]["case_ids"]), 12)

    def test_whole_program_deadline_covers_parent_work(self):
        from epiphysics import decision_evaluation as evaluation
        with tempfile.TemporaryDirectory() as directory:
            incoming, output = Path(directory) / "owned.json", Path(directory) / "result.json"
            incoming.write_bytes(views.canonical(cohort()))
            started = time.monotonic()
            with patch.object(pilot, "PROGRAM_SECONDS", 0.05), patch.object(
                    evaluation, "resolve_world", side_effect=lambda *_: time.sleep(10)):
                self.assertEqual(pilot.main(["--cohort", str(incoming), "--output", str(output)]), 1)
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(json.loads(output.read_text())["error"], "ProgramDeadline")

    def test_outer_deadline_keeps_drained_child_output(self):
        def expired(*_):
            raise pilot.ProgramDeadline("owned outer deadline")
        previous = signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, 0.15)
        try:
            with self.assertRaises(pilot.ProgramDeadline) as raised:
                pilot._capture_process([sys.executable, "-c", "import os,time; os.write(1,b'partial'); time.sleep(10)"], b"{}", 5)
            receipt = raised.exception.partial_receipt
            self.assertEqual(receipt["stdout"], b"partial")
            self.assertEqual(receipt["error"], "program_deadline")
            self.assertIsNotNone(receipt["returncode"])
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)

    def test_hidden_outcome_and_attempt_id_do_not_change_candidate(self):
        first = trace()
        second = deepcopy(first)
        second["attempt_id"] = "different-private-attempt"
        second["later_outcome"]["artifact_valid"] = False
        self.assertEqual(bundle(first), bundle(second))
        for recipe, budget in pilot.ARMS:
            a = json.loads(local_candidate(bundle(first), recipe, budget, 5)["stdout"])
            b = json.loads(local_candidate(bundle(second), recipe, budget, 5)["stdout"])
            self.assertEqual(a["proposal"], b["proposal"])
            self.assertEqual(a["view"], b["view"])

    def test_invalid_cohort_rejected_before_execution(self):
        for change in (lambda value: value.update(trace_count=True),
                       lambda value: value["traces"][1].update(trace_id=value["traces"][0]["trace_id"]),
                       lambda value: value.update(final_cohort_generated=True)):
            value = cohort()
            change(value)
            with patch.object(pilot, "_run_candidate") as execute:
                with self.assertRaises(ValueError):
                    pilot.run_development(value)
                execute.assert_not_called()

    def test_output_destination_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            output.write_bytes(b"original")
            with patch.object(pilot, "run_development") as execute:
                with self.assertRaises(FileExistsError):
                    pilot.main(["--cohort", str(EXAMPLES / "development-traces.json"), "--output", str(output)])
                execute.assert_not_called()
            self.assertEqual(output.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
