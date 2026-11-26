"""Owned driver controls; never generate or score a registered study cohort."""
import base64
from copy import deepcopy
import json
import os
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


def fresh_cohort():
    # Clone the same exposed positive for wiring only. Mechanism names exercise
    # allocation validation; these clones do not instantiate those mechanisms
    # and are not the separately generated fresh experiment or its seed.
    result = {"cohort_id": "decision-pilot-fresh-v1", "contract_id": views.CONTRACT_ID,
              "trace_count": 24, "final_cohort_generated": True, "status": "fresh_exploratory", "traces": []}
    allocation = {"late_visibility": 6, "visible_authority_changes": 4, "verification_dispute": 4,
                  "duplicate_identity": 4, "retention_pressure": 4, "role_direction": 2}
    for mechanism, count in allocation.items():
        for _ in range(count):
            item = trace()
            item.update(trace_id="owned-fresh-unit-" + str(len(result["traces"])), mechanism=mechanism)
            result["traces"].append(item)
    return result


def fresh_triage_report(delta=2):
    # Summary-shaped predicate controls, not claimed experimental measurements.
    harms = ("unauthorized_release_proposals_all", "duplicate_release_proposals_all",
             "invalid_artifact_release_proposals", "evidence_unjustified_release_proposals")
    report = {"stage": "fresh_exploratory", "checks": {name: True for name in (
        "all_outputs_valid", "lossless_reference_parity", "fixed_policy_conformance",
        "same_input_same_output", "program_deadline_met", "source_unchanged")}, "arms": []}
    for index in range(4):
        metrics = {name: {"numerator": 0} for name in (*harms, "duplicate_effects", "unauthorized_effects")}
        metrics["valid_timely_release"] = {"numerator": 10 + delta if index == 1 else 10}
        report["arms"].append({"summary": {"metrics": metrics, "counts": {"failed_attempts": 0}}})
    return report


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
    def assert_process_stopped(self, pid):
        # A descendant orphan is reaped by the OS, not by this test's waitpid.
        # A zombie is already dead and cannot continue working after the bound.
        until = time.monotonic() + 2
        while time.monotonic() < until:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                                   capture_output=True, text=True, timeout=1).stdout.strip()
            if not state or state.startswith("Z"):
                return
            time.sleep(0.02)
        self.fail("Owned sleeping process survived transport cleanup: " + str(pid))

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
        for owns_group in (True, False):
            with self.subTest(owns_group=owns_group):
                started = time.monotonic()
                receipt = pilot._capture_process([sys.executable, "-c", "import time; time.sleep(10)"],
                                                 b"{}", 0.08, start_new_session=owns_group)
                self.assertEqual(receipt["error"], "worker_timeout")
                self.assertIsNotNone(receipt["returncode"])
                self.assertLess(time.monotonic() - started, 2)

    def test_fixed_worker_keeps_containing_process_group(self):
        failed = {"error": "worker_timeout", "stdout": b"", "stderr": b"", "returncode": -9, "elapsed_seconds": 0.0}
        with patch.object(pilot, "_capture_process", return_value=failed) as transport:
            pilot._run_candidate(bundle(), "flat-recency-v1", 2048, 1)
        self.assertIs(transport.call_args.kwargs["start_new_session"], False)

    def test_outer_timeout_stops_nested_transport_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / (name + ".json") for name in ("parent", "middle", "leaf")]
            def identify(path):
                pending = str(path) + ".pending"
                return ("Path(" + repr(pending) + ").write_text(json.dumps({'pid':os.getpid(),'group':os.getpgrp()}))\n"
                        + "os.replace(" + repr(pending) + "," + repr(str(path)) + ")\n")
            imports = "import os,json,sys,time\nfrom pathlib import Path\n"
            leaf = imports + identify(paths[2]) + "time.sleep(20)\n"
            middle = imports + "from epiphysics import decision_pilot as p\n" + identify(paths[1]) + (
                "p._capture_process([sys.executable,'-c'," + repr(leaf) + "],b'{}',15,start_new_session=False)\n")
            parent = imports + "from epiphysics import decision_pilot as p\n" + identify(paths[0]) + (
                "p._capture_process([sys.executable,'-c'," + repr(middle) + "],b'{}',15,start_new_session=False)\n")
            try:
                receipt = pilot._capture_process([sys.executable, "-c", parent], b"{}", 1)
                self.assertEqual(receipt["error"], "worker_timeout")
                identities = [json.loads(path.read_text()) for path in paths]
                self.assertEqual({entry["group"] for entry in identities}, {identities[0]["pid"]})
                self.assertNotEqual(identities[0]["group"], os.getpgrp())
                for entry in identities:
                    self.assert_process_stopped(entry["pid"])
            finally:
                for path in paths:
                    if path.exists():
                        try:
                            os.kill(json.loads(path.read_text())["pid"], signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_exited_parent_does_not_leave_group_descendant_running(self):
        with tempfile.TemporaryDirectory() as directory:
            child_path = Path(directory) / "child.json"
            pending = str(child_path) + ".pending"
            child = ("import json,os,time\nfrom pathlib import Path\nPath(" + repr(pending)
                     + ").write_text(json.dumps({'pid':os.getpid(),'group':os.getpgrp()}))\n"
                     + "os.replace(" + repr(pending) + "," + repr(str(child_path)) + ")\ntime.sleep(20)\n")
            parent = ("import os,subprocess,sys,time\nfrom pathlib import Path\n"
                      "subprocess.Popen([sys.executable,'-c'," + repr(child)
                      + "],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
                      "until=time.monotonic()+2\n"
                      "while not Path(" + repr(str(child_path)) + ").exists() and time.monotonic()<until: time.sleep(.005)\n"
                      "os.write(1,b'parent-finished')\n")
            try:
                receipt = pilot._capture_process([sys.executable, "-c", parent], b"{}", 3)
                self.assertIsNone(receipt["error"], receipt)
                self.assertEqual(receipt["returncode"], 0)
                self.assertEqual(receipt["stdout"], b"parent-finished")
                identity = json.loads(child_path.read_text())
                self.assertNotEqual(identity["group"], os.getpgrp())
                self.assert_process_stopped(identity["pid"])
            finally:
                if child_path.exists():
                    try:
                        os.kill(json.loads(child_path.read_text())["pid"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass

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


class FreshDecisionPilotTests(unittest.TestCase):
    def test_fresh_cli_retains_96_attempts_and_194_journal_records(self):
        incoming_data = fresh_cohort()
        before = deepcopy(incoming_data)
        declared = json.loads((EXAMPLES / "decision-contract.json").read_text())["future_cohort"]["mechanism_mix_proposal"]
        self.assertEqual(pilot.FRESH_MECHANISMS, declared)
        with tempfile.TemporaryDirectory() as directory:
            incoming, output = Path(directory) / "owned.json", Path(directory) / "result.json"
            incoming.write_bytes(views.canonical(incoming_data))
            with patch.object(pilot, "_run_candidate", side_effect=local_candidate) as worker:
                self.assertEqual(pilot.main(["--phase", "fresh_comparison", "--cohort", str(incoming), "--output", str(output)]), 0)
            result = json.loads(output.read_bytes())
            journal = [json.loads(line) for line in Path(str(output) + ".attempts.jsonl").read_bytes().splitlines()]
            self.assertEqual(len(journal), 194)
            self.assertEqual(worker.call_count, 96)
            self.assertEqual(len(journal[0]["case_ids"]), 24)
            self.assertEqual(journal[0]["scope"], "fresh exploratory comparison; only root may invoke the registered run")
            self.assertEqual(journal[-1], {"kind": "run_terminal", "checks": result["checks"], "next_step": result["next_step"]})
            self.assertEqual(result["stage"], "fresh_exploratory")
            self.assertEqual(result["declared_case_count"], 24)
            self.assertTrue(all(result["checks"].values()), result["checks"])
            self.assertEqual(result["next_step"]["action"], "investigate_decision_information_limits")
            for index, arm in enumerate(result["arms"]):
                self.assertEqual((arm["recipe"], arm["budget_bytes"]), pilot.ARMS[index])
                self.assertEqual(len(arm["rows"]), 24)
                self.assertEqual({key: value["case_count"] for key, value in arm["strata"].items()}, declared)
                self.assertEqual(arm["summary"]["metrics"]["valid_timely_release"]["numerator"], 24)
                self.assertEqual(arm["summary"]["metrics"]["duplicate_effects"]["numerator"], 0)
                self.assertEqual([row["input_hash"] for row in arm["rows"]], [row["input_hash"] for row in result["arms"][0]["rows"]])
            for call in worker.call_args_list:
                self.assertEqual(set(call.args[0]), {"header_bytes", "event_tape_bytes", "input_hash"})
                self.assertNotIn(b"later_outcome", call.args[0]["header_bytes"])
                self.assertNotIn(b"owned-fresh-unit", call.args[0]["event_tape_bytes"])
            self.assertEqual(json.loads(incoming.read_bytes()), before)

    def test_fresh_invalid_identity_allocation_status_or_phase_never_executes(self):
        mutations = (
            lambda value: value.update(trace_count=True),
            lambda value: value.update(trace_count=23),
            lambda value: value["traces"].pop(),
            lambda value: value["traces"][1].update(trace_id=value["traces"][0]["trace_id"]),
            lambda value: value["traces"][0].update(mechanism="unknown"),
            lambda value: value["traces"][0].update(mechanism="role_direction"),
            lambda value: value.update(final_cohort_generated=1),
            lambda value: value.update(final_cohort_generated=False),
            lambda value: value.update(status="exposed_development"),
            lambda value: value.update(cohort_id="decision-pilot-development-v1"),
        )
        for mutate in mutations:
            value = fresh_cohort()
            mutate(value)
            with patch.object(pilot, "_run_candidate") as worker, self.assertRaises(ValueError):
                pilot.run_fresh_comparison(value)
            worker.assert_not_called()
        for runner, value in ((pilot.run_development, fresh_cohort()), (pilot.run_fresh_comparison, cohort())):
            with patch.object(pilot, "_run_candidate") as worker, self.assertRaises(ValueError):
                runner(value)
            worker.assert_not_called()

    def test_fresh_failures_keep_all_cases_and_exact_raw_bytes(self):
        failed = {"error": "worker_exit", "stdout": b"\xff", "stderr": b"owned failure", "returncode": 1,
                  "request_bytes": 1, "elapsed_seconds": 0.0}
        records = []
        with patch.object(pilot, "_run_candidate", return_value=failed):
            result = pilot.run_fresh_comparison(fresh_cohort(), record=records.append)
        self.assertEqual(len(records), 192)
        self.assertEqual(result["next_step"]["action"], "repair_decision_pilot")
        for arm in result["arms"]:
            self.assertEqual(arm["summary"]["counts"]["failed_attempts"], 24)
            self.assertEqual(arm["summary"]["metrics"]["valid_output_completion"]["denominator"], 24)
            self.assertEqual(arm["summary"]["metrics"]["missed_world_opportunities"]["numerator"], 24)
            self.assertTrue(all(base64.b64decode(row["worker_receipt"]["stdout_base64"]) == b"\xff" for row in arm["rows"]))

    def test_fresh_triage_two_release_boundary_and_no_scale_change(self):
        for difference, expected in ((-1, "investigate_decision_information_limits"), (0, "investigate_decision_information_limits"),
                                     (1, "investigate_decision_information_limits"), (2, "prepare_prospective_decision_shadow")):
            result = pilot._next_step(fresh_triage_report(difference))
            self.assertEqual(result["action"], expected)
            self.assertFalse(result["scale_change_allowed"])
            self.assertFalse(result["live_effects_allowed"])
            self.assertEqual(result["metric_status"], "fresh exploratory measurements; research triage only; no adoption claim")

    def test_fresh_triage_each_harm_and_extra_failed_output_blocks_signal(self):
        for harm in ("unauthorized_release_proposals_all", "duplicate_release_proposals_all",
                     "invalid_artifact_release_proposals", "evidence_unjustified_release_proposals"):
            report = fresh_triage_report()
            report["arms"][1]["summary"]["metrics"][harm]["numerator"] = 1
            self.assertEqual(pilot._next_step(report)["action"], "investigate_decision_information_limits")
        report = fresh_triage_report()
        report["arms"][1]["summary"]["counts"]["failed_attempts"] = 1
        self.assertEqual(pilot._next_step(report)["action"], "investigate_decision_information_limits")
        report["checks"]["all_outputs_valid"] = False
        self.assertEqual(pilot._next_step(report)["action"], "repair_decision_pilot")

    def test_fresh_conformance_or_unsafe_effects_override_improvement(self):
        for check in fresh_triage_report()["checks"]:
            report = fresh_triage_report()
            report["checks"][check] = False
            self.assertEqual(pilot._next_step(report)["action"], "repair_decision_pilot")
        for index in range(4):
            for harm in ("duplicate_effects", "unauthorized_effects"):
                report = fresh_triage_report()
                report["arms"][index]["summary"]["metrics"][harm]["numerator"] = 1
                self.assertEqual(pilot._next_step(report)["action"], "repair_decision_pilot")
        report = fresh_triage_report(0)
        report["arms"][3]["summary"]["metrics"]["valid_timely_release"]["numerator"] = 24
        self.assertEqual(pilot._next_step(report)["action"], "investigate_decision_information_limits")

    def test_fresh_parent_failure_keeps_returned_worker_and_null_metrics(self):
        from epiphysics import decision_evaluation as evaluation
        with tempfile.TemporaryDirectory() as directory:
            incoming, output = Path(directory) / "owned.json", Path(directory) / "result.json"
            incoming.write_bytes(views.canonical(fresh_cohort()))
            with patch.object(pilot, "_run_candidate", side_effect=local_candidate), patch.object(
                    evaluation, "evaluate_simulated_proposal", side_effect=ValueError("owned fresh evaluator failure")):
                self.assertEqual(pilot.main(["--phase", "fresh_comparison", "--cohort", str(incoming), "--output", str(output)]), 1)
            result = json.loads(output.read_bytes())
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["metrics"])
            self.assertEqual(result["next_step"]["action"], "repair_decision_pilot")
            journal = [json.loads(line) for line in Path(str(output) + ".attempts.jsonl").read_bytes().splitlines()]
            self.assertEqual([row["kind"] for row in journal], ["declared_run", "worker_returned", "run_terminal"])
            self.assertEqual(len(journal[0]["case_ids"]), 24)
            self.assertGreater(journal[1]["receipt"]["stdout_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
