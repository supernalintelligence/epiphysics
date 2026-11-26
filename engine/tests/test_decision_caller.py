"""Owned caller transport controls: no generated cases, seeds or subprocesses.

All executions below use an opaque small input and an explicitly mocked child.
The shallow report/journal stubs are not research evidence or helper-valid runs.
Source files are temporary byte fixtures except the copied caller source needed
for its executing-code binding. These tests never invoke the fresh generator.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "control-exchange" / "fresh-caller.py"
SPEC = importlib.util.spec_from_file_location("owned_decision_caller_control", SCRIPT)
caller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(caller)
REPORT = {"stage": "fresh_exploratory", "declared_case_count": 24,
          "checks": {"owned_transport_control_only": True}}
JOURNAL = b'{"kind":"owned_mock_transport_journal"}\n'
TRANSPORT = {"returncode": 0, "error": None, "stdout": b"owned child stdout\n", "stderr": b""}


class OwnedCallerFiles:
    def __init__(self, root):
        self.root = root
        self.registration_path = root / "registration.json"
        self.outputs = {key: root / key for key in caller.OUTPUT_KEYS}
        self.outputs["journal"] = root / "report.attempts.jsonl"
        sources = root / "sources"
        sources.mkdir()
        self.source_paths = {name: sources / name for name in caller.SOURCE_PATHS}
        for name, path in self.source_paths.items():
            path.write_bytes(caller._SOURCE if name == "fresh-caller.py" else b"owned nonexecuted source: " + name.encode())
        hashes = {name: caller.digest(path.read_bytes()) for name, path in self.source_paths.items()}
        self.contract_paths = {role: sources / (role + ".json") for role in caller.CONTRACT_PATHS}
        for role, path in self.contract_paths.items():
            path.write_bytes(caller.canonical({"owned_transport_contract": role}))
        self.registration = {"schema_version": 1, "phase": "fresh_comparison", "cohort_id": "decision-pilot-fresh-v1",
                             "execution_id": "owned-caller-control", "source_hashes": hashes,
                             "contract_hashes": {role: caller.digest(path.read_bytes())
                                                 for role, path in self.contract_paths.items()},
                             "outputs": {name: str(path) for name, path in self.outputs.items()}}
        self.cohort_raw = b'{"owned_transport_fixture":true,"no_cases_generated":true}\n'
        self.outputs["cohort"].write_bytes(self.cohort_raw)
        self.custody = {"status": "complete", "execution_id": self.registration["execution_id"],
                        "generator_sha256": hashes["fresh-generator.py"], "caller_sha256": hashes["fresh-caller.py"],
                        "cohort_sha256": caller.digest(self.cohort_raw), "first_exposure": None}
        self.save_registration()

    def save_registration(self):
        raw = caller.canonical(self.registration)
        self.registration_path.write_bytes(raw)
        self.custody["registration_sha256"] = caller.digest(raw)
        self.save_custody()

    def save_custody(self):
        self.outputs["custody"].write_bytes(caller.canonical(self.custody))


class DecisionCallerTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix="epiphysics-owned-caller-")
        self.addCleanup(temporary.cleanup)
        return OwnedCallerFiles(Path(temporary.name).resolve())

    def mocked(self, fixture, *, transport=None, report=REPORT, journal=JOURNAL, mutate=None, launch_error=None):
        """Return an owned patch scope; caller's file/claim code remains real."""
        transport = deepcopy(TRANSPORT if transport is None else transport)
        stack = ExitStack()
        stack.enter_context(patch.object(caller, "SOURCE_PATHS", fixture.source_paths))
        stack.enter_context(patch.object(caller, "CONTRACT_PATHS", fixture.contract_paths))

        def worker(arguments, request, timeout, *, output_limit, start_new_session):
            self.assertTrue(fixture.outputs["claim"].is_file(), "Claim must precede the mocked child")
            self.assertEqual(request, b"")
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 60)
            self.assertEqual(output_limit, 65536)
            self.assertIs(start_new_session, False)
            self.assertEqual(arguments[1:7], ["-s", "-m", "epiphysics.decision_pilot", "--phase", "fresh_comparison", "--cohort"])
            self.assertEqual(arguments[7:], [str(fixture.outputs["cohort"]), "--output", str(fixture.outputs["report"])])
            if launch_error is not None:
                raise launch_error
            if report is not None:
                fixture.outputs["report"].write_bytes(report if type(report) is bytes else caller.canonical(report))
            if journal is not None:
                fixture.outputs["journal"].write_bytes(journal)
            if mutate is not None:
                mutate()
            return transport

        mocked = stack.enter_context(patch.object(caller.pilot, "_capture_process", side_effect=worker))
        return stack, mocked

    def test_complete_receipt_binds_claim_inputs_outputs_and_refuses_replay(self):
        fixture = self.fixture()
        custody_before = fixture.outputs["custody"].read_bytes()
        scope, worker = self.mocked(fixture)
        with scope:
            receipt = caller.run(fixture.registration_path)
            self.assertEqual(receipt["status"], "completed")
            self.assertTrue(receipt["original_files_unchanged"])
            for role in ("claim", "report", "journal", "stdout", "stderr", "cohort", "custody"):
                self.assertEqual(receipt[role + "_sha256"], caller.digest(fixture.outputs[role].read_bytes()))
            claim = json.loads(fixture.outputs["claim"].read_bytes())
            self.assertEqual(claim["registration_sha256"], caller.digest(fixture.registration_path.read_bytes()))
            self.assertLessEqual(receipt["started_at"], claim["first_exposure_at"])
            self.assertLessEqual(claim["first_exposure_at"], receipt["ended_at"])
            self.assertEqual(fixture.outputs["custody"].read_bytes(), custody_before)
            before = {name: path.read_bytes() for name, path in fixture.outputs.items()}
            with self.assertRaisesRegex(ValueError, "never replay"):
                caller.run(fixture.registration_path)
            self.assertEqual(before, {name: path.read_bytes() for name, path in fixture.outputs.items()})
            self.assertEqual(worker.call_count, 1)

    def test_exclusive_claim_handles_race_after_preflight(self):
        fixture = self.fixture()
        original = caller.persist_new

        def racing_claim(path, raw):
            if path == fixture.outputs["claim"]:
                path.write_bytes(b"owned competing claim")
            return original(path, raw)

        scope, worker = self.mocked(fixture)
        with scope, patch.object(caller, "persist_new", side_effect=racing_claim):
            with self.assertRaises(FileExistsError):
                caller.run(fixture.registration_path)
        worker.assert_not_called()
        self.assertEqual(fixture.outputs["claim"].read_bytes(), b"owned competing claim")
        self.assertFalse(fixture.outputs["caller_receipt"].exists())

    def test_source_change_before_claim_is_refused(self):
        fixture = self.fixture()
        fixture.source_paths["decision_policy.py"].write_bytes(b"changed owned source")
        scope, worker = self.mocked(fixture)
        with scope, self.assertRaisesRegex(ValueError, "Frozen implementation changed"):
            caller.run(fixture.registration_path)
        worker.assert_not_called()
        self.assertFalse(fixture.outputs["claim"].exists())

    def test_contract_change_before_claim_refuses_without_child_execution(self):
        for role in caller.CONTRACT_PATHS:
            with self.subTest(role=role):
                fixture = self.fixture()
                fixture.contract_paths[role].write_bytes(b'{"owned_contract_changed":true}')
                scope, worker = self.mocked(fixture)
                with scope, self.assertRaisesRegex(ValueError, "Frozen contract changed"):
                    caller.run(fixture.registration_path)
                worker.assert_not_called()
                self.assertFalse(fixture.outputs["claim"].exists())
                self.assertFalse(fixture.outputs["caller_receipt"].exists())

    def test_contract_change_during_child_retains_failed_receipt(self):
        for role in caller.CONTRACT_PATHS:
            with self.subTest(role=role):
                fixture = self.fixture()
                path = fixture.contract_paths[role]
                scope, worker = self.mocked(fixture, mutate=lambda: path.write_bytes(b'{"owned_contract_changed":true}'))
                with scope:
                    receipt = caller.run(fixture.registration_path)
                worker.assert_called_once()
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["failure"]["type"], "InputChanged")
                self.assertFalse(receipt["original_files_unchanged"])
                self.assertEqual(receipt["report_sha256"], caller.digest(fixture.outputs["report"].read_bytes()))
                self.assertEqual(receipt["journal_sha256"], caller.digest(fixture.outputs["journal"].read_bytes()))
                self.assertEqual(json.loads(fixture.outputs["caller_receipt"].read_bytes()), receipt)

    def test_caller_bytes_cannot_be_rebound_to_different_loaded_code(self):
        fixture = self.fixture()
        changed = caller._SOURCE + b"\n# owned replacement bytes\n"
        fixture.source_paths["fresh-caller.py"].write_bytes(changed)
        fixture.registration["source_hashes"]["fresh-caller.py"] = caller.digest(changed)
        fixture.custody["caller_sha256"] = caller.digest(changed)
        fixture.save_registration()
        scope, worker = self.mocked(fixture)
        with scope, self.assertRaisesRegex(ValueError, "Executing caller"):
            caller.run(fixture.registration_path)
        worker.assert_not_called()

    def test_source_and_each_input_mutation_in_child_downgrade_completion(self):
        for role in ("source", "registration", "custody", "cohort"):
            with self.subTest(role=role):
                fixture = self.fixture()
                path = (fixture.source_paths["decision_views.py"] if role == "source" else
                        fixture.registration_path if role == "registration" else fixture.outputs[role])
                scope, worker = self.mocked(fixture, mutate=lambda: path.write_bytes(b"owned changed bytes"))
                with scope:
                    receipt = caller.run(fixture.registration_path)
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["failure"]["type"], "InputChanged")
                self.assertFalse(receipt["original_files_unchanged"])
                self.assertEqual(receipt["report_sha256"], caller.digest(fixture.outputs["report"].read_bytes()))
                worker.assert_called_once()

    def test_custody_binding_errors_refuse_before_claim(self):
        changes = ({"status": "stopped"}, {"execution_id": "other"}, {"registration_sha256": "0" * 64},
                   {"generator_sha256": "0" * 64}, {"caller_sha256": "0" * 64},
                   {"first_exposure": "2020-01-01T00:00:00Z"}, {"cohort_sha256": None})
        for change in changes:
            with self.subTest(change=change):
                fixture = self.fixture()
                fixture.custody.update(change)
                fixture.save_custody()
                scope, worker = self.mocked(fixture)
                with scope, self.assertRaisesRegex(ValueError, "Custody"):
                    caller.run(fixture.registration_path)
                worker.assert_not_called()
                self.assertFalse(fixture.outputs["claim"].exists())

    def test_wrong_cohort_hash_retains_claim_and_failure_without_launch(self):
        fixture = self.fixture()
        fixture.outputs["cohort"].write_bytes(b"changed opaque owned input")
        scope, worker = self.mocked(fixture)
        with scope:
            receipt = caller.run(fixture.registration_path)
        worker.assert_not_called()
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("immutable custody", receipt["failure"]["message"])
        self.assertTrue(fixture.outputs["claim"].is_file())
        self.assertTrue(fixture.outputs["caller_receipt"].is_file())

    def test_complete_failed_conformance_rc1_is_completed_transport(self):
        fixture = self.fixture()
        report = {**REPORT, "checks": {"owned_transport_control_only": False}}
        scope, worker = self.mocked(fixture, report=report,
                                    transport={**TRANSPORT, "returncode": 1, "error": "worker_exit"})
        with scope:
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["returncode"], 1)
        self.assertNotIn("failure", receipt)
        worker.assert_called_once()

    def test_report_returncode_disagreement_is_failed(self):
        fixture = self.fixture()
        report = {**REPORT, "checks": {"owned_transport_control_only": False}}
        scope, _ = self.mocked(fixture, report=report)
        with scope:
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "failed")
        self.assertIn("complete-shaped", receipt["failure"]["message"])

    def test_missing_report_retains_partial_journal_and_timeout_reason(self):
        fixture = self.fixture()
        partial = b'{"kind":"owned_interrupted_attempt","prefix":"unclosed'
        scope, _ = self.mocked(fixture, report=None, journal=partial,
                              transport={**TRANSPORT, "returncode": -9, "error": "worker_timeout"})
        with scope:
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["report_sha256"])
        self.assertEqual(receipt["journal_sha256"], caller.digest(partial))
        self.assertEqual(fixture.outputs["journal"].read_bytes(), partial)
        self.assertEqual(receipt["failure"]["transport_error"], "worker_timeout")
        self.assertEqual([item["role"] for item in receipt["failure"]["capture_errors"]], ["report"])

    def test_missing_journal_still_binds_available_report(self):
        fixture = self.fixture()
        scope, _ = self.mocked(fixture, journal=None)
        with scope:
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["report_sha256"], caller.digest(caller.canonical(REPORT)))
        self.assertIsNone(receipt["journal_sha256"])
        self.assertEqual([item["role"] for item in receipt["failure"]["capture_errors"]], ["journal"])

    def test_malformed_report_keeps_exact_artifact_hashes(self):
        fixture = self.fixture()
        malformed = b'{"incomplete":'
        scope, _ = self.mocked(fixture, report=malformed)
        with scope:
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["report_sha256"], caller.digest(malformed))
        self.assertEqual(receipt["journal_sha256"], caller.digest(JOURNAL))

    def test_timeout_overflow_and_exit_failures_preserve_raw_streams(self):
        for error, returncode, stdout, stderr in (
            ("worker_timeout", -9, b"owned partial stdout", b"owned timeout stderr"),
            ("worker_output_limit", -9, b"x" * 65530, b"y" * 7),
            ("worker_exit", 7, b"owned failing stdout", b"owned failure detail"),
        ):
            with self.subTest(error=error):
                fixture = self.fixture()
                scope, _ = self.mocked(fixture, transport={"error": error, "returncode": returncode,
                                                           "stdout": stdout, "stderr": stderr})
                with scope:
                    receipt = caller.run(fixture.registration_path)
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["failure"]["transport_error"], error)
                for label, raw in (("stdout", stdout), ("stderr", stderr)):
                    self.assertEqual(fixture.outputs[label].read_bytes(), raw)
                    self.assertEqual(receipt[label + "_sha256"], caller.digest(raw))
                    self.assertEqual(receipt[label + "_bytes"], len(raw))

    def test_launch_error_leaves_terminal_failure_and_claim(self):
        fixture = self.fixture()
        scope, _ = self.mocked(fixture, launch_error=OSError("owned launch failure"))
        with scope:
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["failure"]["type"], "OSError")
        self.assertIn("owned launch failure", receipt["failure"]["message"])
        self.assertIsNone(receipt["returncode"])
        self.assertTrue(fixture.outputs["claim"].exists())

    def test_stream_persistence_failure_cannot_be_completed(self):
        fixture = self.fixture()
        original = caller.persist_new

        def broken_stdout(path, raw):
            if path == fixture.outputs["stdout"]:
                raise OSError("owned stdout persistence failure")
            return original(path, raw)

        scope, _ = self.mocked(fixture)
        with scope, patch.object(caller, "persist_new", side_effect=broken_stdout):
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["persistence_errors"][0]["stage"], "stdout")
        self.assertTrue(fixture.outputs["stderr"].exists())
        self.assertTrue(fixture.outputs["caller_receipt"].exists())

    def test_caller_budget_includes_preflight_and_stream_persistence(self):
        fixture = self.fixture()
        scope, _ = self.mocked(fixture)
        with scope, patch.object(caller.time, "monotonic", side_effect=[100.0, 130.0, 161.0]):
            receipt = caller.run(fixture.registration_path)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["elapsed_seconds"], 61.0)
        self.assertEqual(receipt["failure"]["type"], "CallerDeadline")

    def test_output_aliases_relative_paths_and_wrong_journal_are_refused(self):
        for kind in ("alias", "registration", "relative", "outside", "journal", "symlink_alias"):
            with self.subTest(kind=kind):
                fixture = self.fixture()
                outputs = fixture.registration["outputs"]
                if kind == "alias":
                    outputs["stdout"] = outputs["stderr"]
                elif kind == "registration":
                    outputs["stdout"] = str(fixture.registration_path)
                elif kind == "relative":
                    outputs["stdout"] = "owned-relative-output"
                elif kind == "outside":
                    outputs["stdout"] = str(fixture.root.parent / "owned-outside-output")
                elif kind == "journal":
                    outputs["journal"] = str(fixture.root / "wrong-journal")
                else:
                    fixture.outputs["stdout"].symlink_to(fixture.outputs["stderr"])
                fixture.save_registration()
                scope, worker = self.mocked(fixture)
                with scope, self.assertRaisesRegex(ValueError, "distinct absolute paths"):
                    caller.run(fixture.registration_path)
                worker.assert_not_called()
                self.assertFalse(fixture.outputs["claim"].exists())


if __name__ == "__main__":
    unittest.main()
