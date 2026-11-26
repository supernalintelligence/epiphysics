"""Controller wiring controls, separate from retained-result validation tests."""
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import improvement
from epiphysics.store import Ledger, canonical, digest


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "improvement"
REAL_PREPARE = improvement._prepare_decision


class DecisionControllerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ledger = Ledger(self.root / "ledger")
        self.policy = EXAMPLES / "policy.json"
        self.suite = EXAMPLES / "entities.json"
        self.origin = "owned-predecessor:next"
        # Explicit local queue fixture; never part of a research evidence store.
        self.ledger.append("improvement_completed", {"run_key": "owned-predecessor", "request": {"manifest": {}},
            "next_step": {"id": self.origin, "state": "queued", "action": "prepare_control_exchange_decision_pilot"}}, "owned-predecessor")
        self.compact = {"schema_version": 1, "study_id": "owned-wiring-control", "phase": "development",
            "status": "checked", "stage": "exposed_development", "origin": {"step_id": self.origin},
            "checks": {"owned_control": True}, "next_step": {"action": "prepare_fresh_decision_comparison"},
            "assessment_identity": {"hash": "a" * 64}}
        self.prepared = {"artifacts": {"owned-input": b"owned control"}, "report": self.compact}
        self.patches = ExitStack()
        self.patches.enter_context(patch.object(improvement, "_prepare_decision",
            side_effect=lambda _: {"prepared": self.prepared, "error": None}))
        self.checked = self.patches.enter_context(patch.object(improvement.decision_assessment,
            "check_prepared_decision_study"))
        self.measured = self.patches.enter_context(patch.object(improvement.decision_assessment,
            "assess_prepared_decision_study", side_effect=lambda prepared: {
                "report": deepcopy(prepared["report"]), "artifacts": {**prepared["artifacts"],
                    "assessment_report": canonical(prepared["report"]).encode()}}))
        # Existing probe implementations have their own integration suite. These
        # tests isolate queue/capture/replay wiring and do not spend each test's
        # real 30-second assessment ceiling rerunning unrelated graph probes.
        for name, metrics in (
            ("run_source_span_checks", ("source_span_resolution", "assertion_history_preservation")),
            ("run_manifest_checks", ("representation_manifest_preservation",)),
            ("run_transformation_checks", ("transformation_preservation",)),
            ("run_graph_view_checks", ("split_merge_preservation",)),
            ("run_materialization_checks", ("output_manifest_materialization",)),
        ):
            self.patches.enter_context(patch.object(improvement, name,
                return_value={"metrics": {metric: 1 for metric in metrics}, "scope": "owned wiring stub"}))

    def tearDown(self):
        self.patches.close()
        self.ledger.close()
        self.temporary.cleanup()

    def run_assessment(self, **kwargs):
        return improvement.assess(self.ledger, self.policy, self.suite, "reference", "owned-decision-run",
            after_step=self.origin, completed_work="Owned controller wiring control; not research evidence",
            decision_study_path=self.root / "owned-request.json", **kwargs)

    def test_validated_decision_result_atomically_advances_and_captures(self):
        result = self.run_assessment()
        self.assertEqual(result["result"], "assessed")
        self.assertEqual(result["next_step"]["action"], "prepare_fresh_decision_comparison")
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertIsNone(result["next_step"]["metric"])
        self.assertEqual(result["report"]["decision_pilot"], self.compact)
        self.assertEqual(result["prior_action_outcome"]["status"], "unmeasured")
        self.assertEqual(result["request"]["manifest"]["decision-input:owned-input"], digest(b"owned control"))
        self.assertIn("decision-result:assessment_report", result["input_observations"])
        self.assertGreaterEqual(self.measured.call_count, 2)
        before = len(self.ledger.events())
        self.assertEqual(self.run_assessment(), result)
        self.assertEqual(len(self.ledger.events()), before)
        with patch.dict(os.environ, {"EPIPHYSICS_EXPECTED_REQUEST_SHA256": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "dispatcher's prepared request"):
                self.run_assessment()
        self.assertEqual(len(self.ledger.events()), before)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_failed_conformance_selects_repair(self):
        self.compact["checks"]["owned_control"] = False
        self.compact["next_step"]["action"] = "repair_decision_pilot"
        result = self.run_assessment()
        self.assertEqual(result["result"], "assessed")
        self.assertEqual(result["next_step"]["action"], "repair_decision_pilot")

    def test_wrong_origin_becomes_durable_failure(self):
        self.compact["origin"]["step_id"] = "wrong-origin"
        result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertEqual(result["next_step"]["action"], "diagnose_failed_assessment")
        self.measured.assert_not_called()
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])

    def test_completed_or_cancelled_step_cannot_be_consumed(self):
        for state in ("completed", "cancelled", None):
            events = deepcopy(self.ledger.events())
            events[-1]["body"]["next_step"]["state"] = state
            with self.assertRaisesRegex(ValueError, "currently queued"):
                improvement._check_decision_origin({"prepared": self.prepared, "error": None}, events, self.origin)

    def test_missing_decision_evidence_cannot_consume_decision_steps(self):
        for action in ("prepare_control_exchange_decision_pilot", "repair_decision_pilot", "prepare_fresh_decision_comparison"):
            self.ledger.append("improvement_completed", {"run_key": "owned-" + action, "request": {"manifest": {}},
                "next_step": {"id": self.origin, "state": "queued", "action": action}}, "owned-" + action)
            before = len(self.ledger.events())
            with patch.object(improvement, "_prepare_decision", side_effect=REAL_PREPARE):
                with self.assertRaisesRegex(ValueError, "generic assessment cannot complete"):
                    improvement.assess(self.ledger, self.policy, self.suite, "reference", "missing-" + action,
                        after_step=self.origin, completed_work="Owned omission control; no decision evidence")
            self.assertEqual(len(self.ledger.events()), before)
            self.assertEqual(improvement.status(self.ledger)["next_step"]["action"], action)

    def test_result_change_at_completion_is_not_accepted(self):
        altered = deepcopy(self.compact)
        altered["checks"]["owned_control"] = False
        self.measured.side_effect = [
            {"report": self.compact, "artifacts": self.prepared["artifacts"]},
            {"report": altered, "artifacts": self.prepared["artifacts"]},
        ]
        result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertIn("changed before completion", result["message"])

    def test_mixed_studies_refused_before_claim(self):
        before = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, "one decision or retrieval"):
            self.run_assessment(retrieval_study_path="unused")
        self.assertEqual(len(self.ledger.events()), before)
        with self.assertRaisesRegex(ValueError, "one decision or retrieval"):
            improvement.dispatch(self.root / "ledger", self.policy, self.suite, "reference", "unused",
                completed_work="Owned control", retrieval_study_path="unused", decision_study_path="unused")

    def test_cli_forwards_decision_study(self):
        with patch.object(improvement, "dispatch", return_value={"result": "assessed"}) as called:
            result = improvement.main(["--store", str(self.root / "ledger"), "dispatch", "--policy", str(self.policy),
                "--suite", str(self.suite), "--candidate", "reference", "--run-key", "owned-cli", "--after-step", self.origin,
                "--completed-work", "Owned control", "--decision-study", "owned-study.json"])
        self.assertEqual(result, 0)
        self.assertEqual(called.call_args.kwargs["decision_study_path"], "owned-study.json")

    def test_incomplete_evidence_is_captured_before_durable_failure(self):
        # Exercise the real preparation error transport, without a candidate run.
        failure = improvement.decision_assessment.DecisionStudyPreparationError(
            "Owned incomplete report", {"report": b'{"status":"failed"}', "journal": b'{"kind":"worker_interrupted"}\n'})
        # The setUp adapter is a wiring stub; call its unpatched implementation
        # directly through the original function captured before patching.
        with patch.object(improvement.decision_assessment, "prepare_decision_study", side_effect=failure):
            preparation = REAL_PREPARE(self.root / "missing-owned-request.json")
        self.assertIsNotNone(preparation["error"])
        self.assertEqual(preparation["prepared"]["artifacts"]["invalid-captured:report"], b'{"status":"failed"}')
        with patch.object(improvement, "_prepare_decision", return_value=preparation):
            result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        events = [event for event in self.ledger.events() if event["kind"] == "observation"]
        sources = {event["body"]["source"] for event in events}
        self.assertIn("improvement-input:decision-input:invalid-captured:report", sources)
        self.assertIn("improvement-input:decision-input:invalid-captured:journal", sources)
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])


if __name__ == "__main__":
    unittest.main()
