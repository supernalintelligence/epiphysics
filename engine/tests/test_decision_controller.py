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
        for action in ("prepare_control_exchange_decision_pilot", "repair_decision_pilot", "prepare_fresh_decision_comparison",
                       "prepare_prospective_decision_shadow", "investigate_decision_information_limits"):
            self.ledger.append("improvement_completed", {"run_key": "owned-" + action, "request": {"manifest": {}},
                "next_step": {"id": self.origin, "state": "queued", "action": action}}, "owned-" + action)
            before = len(self.ledger.events())
            with patch.object(improvement, "_prepare_decision", side_effect=REAL_PREPARE):
                with self.assertRaisesRegex(ValueError, "generic assessment cannot complete"):
                    improvement.assess(self.ledger, self.policy, self.suite, "reference", "missing-" + action,
                        after_step=self.origin, completed_work="Owned omission control; no decision evidence")
            self.assertEqual(len(self.ledger.events()), before)
            self.assertEqual(improvement.status(self.ledger)["next_step"]["action"], action)

    def fresh_origin(self, action="investigate_decision_information_limits"):
        # A real local ledger envelope with synthetic study contents. These are
        # wiring controls, not a reproduction or replacement of the C7 receipt.
        prior = deepcopy(self.compact)
        self.ledger.append("improvement_completed", {"run_key": "owned-development", "request": {"manifest": {}},
            "report": {"decision_pilot": prior}, "assessment_identity": {"hash": "b" * 64},
            "next_step": {"id": self.origin, "state": "queued", "action": "prepare_fresh_decision_comparison"}},
            "owned-development-complete")
        event = self.ledger.events()[-1]
        self.compact.update(phase="fresh_comparison", stage="fresh_exploratory",
            next_step={"action": action}, origin_transition={"event_id": event["id"], "event_hash": event["hash"],
                "assessment_hash": "b" * 64, "decision_assessment_hash": "a" * 64})
        self.prepared["artifacts"]["origin_transition"] = canonical(event).encode()
        return event

    def test_fresh_comparison_advances_from_exact_retained_predecessor(self):
        self.fresh_origin()
        with patch.object(improvement, "_check_decision_origin", wraps=improvement._check_decision_origin) as origins:
            result = self.run_assessment()
        self.assertEqual(result["result"], "assessed")
        self.assertGreaterEqual(origins.call_count, 4)
        self.assertEqual(result["next_step"]["action"], "investigate_decision_information_limits")
        self.assertIn("fresh exploratory", result["scope"])
        self.assertNotIn("exposed decision-development", result["scope"])
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        before = len(self.ledger.events())
        self.assertEqual(self.run_assessment(), result)
        self.assertEqual(len(self.ledger.events()), before)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_fresh_signal_only_prepares_prospective_shadow(self):
        self.fresh_origin("prepare_prospective_decision_shadow")
        result = self.run_assessment()
        self.assertEqual(result["result"], "assessed")
        self.assertEqual(result["next_step"]["action"], "prepare_prospective_decision_shadow")
        self.assertFalse(result["next_step"]["scale_change_allowed"])

    def test_fresh_origin_compares_full_event_not_only_identifiers(self):
        event = self.fresh_origin()
        event["body"]["request"]["manifest"]["forged-historical-source"] = "c" * 64
        self.prepared["artifacts"]["origin_transition"] = canonical(event).encode()
        result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertIn("actual accepted development predecessor", result["message"])
        self.measured.assert_not_called()

    def test_fresh_origin_refuses_forged_identity_fields(self):
        self.fresh_origin()
        for field in ("event_id", "event_hash", "assessment_hash", "decision_assessment_hash"):
            with self.subTest(field=field):
                altered = deepcopy(self.prepared)
                altered["report"]["origin_transition"][field] = "forged"
                with self.assertRaisesRegex(ValueError, "actual accepted development predecessor"):
                    improvement._check_decision_origin({"prepared": altered, "error": None}, self.ledger.events(), self.origin)

    def test_fresh_origin_refuses_nonaccepted_or_failed_predecessor(self):
        self.fresh_origin()
        for change in ("failed-kind", "failed-check", "fresh-phase", "wrong-action"):
            events = deepcopy(self.ledger.events())
            event = events[-1]
            if change == "failed-kind":
                event["kind"] = "improvement_failed"
            elif change == "failed-check":
                event["body"]["report"]["decision_pilot"]["checks"]["owned_control"] = False
            elif change == "fresh-phase":
                event["body"]["report"]["decision_pilot"]["phase"] = "fresh_comparison"
            else:
                event["body"]["next_step"]["action"] = "investigate_decision_information_limits"
            prepared = deepcopy(self.prepared)
            prepared["artifacts"]["origin_transition"] = canonical(event).encode()
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "actual accepted development predecessor"):
                improvement._check_decision_origin({"prepared": prepared, "error": None}, events, self.origin)

    def test_fresh_historical_bytes_changed_before_completion_fail_durably(self):
        event = self.fresh_origin()
        def measure(prepared):
            result = {"report": deepcopy(prepared["report"]), "artifacts": dict(prepared["artifacts"])}
            changed = deepcopy(event)
            changed["body"]["request"]["manifest"]["late-forgery"] = "e" * 64
            prepared["artifacts"]["origin_transition"] = canonical(changed).encode()
            return result
        self.measured.side_effect = measure
        result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertNotEqual(result["next_step"]["action"], "investigate_decision_information_limits")
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])

    def test_development_cannot_consume_fresh_or_fresh_repair(self):
        self.fresh_origin()
        self.compact.update(phase="development", stage="exposed_development")
        for action in ("prepare_fresh_decision_comparison", "repair_decision_pilot",
                       "prepare_prospective_decision_shadow", "investigate_decision_information_limits"):
            events = deepcopy(self.ledger.events())
            events[-1]["body"]["next_step"]["action"] = action
            events[-1]["body"]["report"]["decision_pilot"]["phase"] = "fresh_comparison"
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "Development"):
                improvement._check_decision_origin({"prepared": self.prepared, "error": None}, events, self.origin)

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


class DecisionDiagnosisControllerTests(unittest.TestCase):
    """Real queue/claim controls; core ancestry has separate non-stub tests."""

    def setUp(self):
        DecisionControllerTests.setUp(self)
        self.parent = self.ledger.append("improvement_completed", {
            "run_key": "owned-fresh", "request": {"manifest": {}},
            "next_step": {"id": self.origin, "state": "queued",
                          "action": "investigate_decision_information_limits"}}, "owned-fresh-complete")
        self.compact.update(phase=improvement.decision_diagnosis.PHASE,
            stage=improvement.decision_diagnosis.STAGE,
            contract_id=improvement.decision_diagnosis.CONTRACT_ID,
            evidence_origin={"event_id": self.parent["id"], "event_hash": self.parent["hash"]},
            queue_parent={"event_id": self.parent["id"], "event_hash": self.parent["hash"]},
            ancestry={"scope": "synthetic controller wiring only"},
            next_step={"action": "prepare_dated_evidence_quality_protocol"})
        self.prepared["artifacts"]["queue_parent"] = canonical(self.parent).encode()

        def lineage(prepared, events, after_step):
            # Simulate the core's exact-parent verdict. This stub does not
            # stand in for historical blob or failed-request proof validation.
            current = [e for e in events if e["kind"] in improvement.TRANSITIONS][-1]
            if (prepared["artifacts"]["queue_parent"] != canonical(current).encode()
                    or current["body"]["next_step"]["id"] != after_step):
                raise ValueError("Owned lineage control refuses changed parent")

        self.lineage = self.patches.enter_context(patch.object(
            improvement.decision_diagnosis, "validate_lineage", side_effect=lineage))

    tearDown = DecisionControllerTests.tearDown
    run_assessment = DecisionControllerTests.run_assessment

    def test_checked_diagnosis_is_atomic_and_exact_replay_does_not_assess(self):
        result = self.run_assessment()
        self.assertEqual(result["result"], "assessed")
        self.assertEqual(result["next_step"]["action"], "prepare_dated_evidence_quality_protocol")
        self.assertEqual(result["next_step"]["evidence"]["evidence_origin"], self.compact["evidence_origin"])
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertIn("96 retained", result["scope"])
        self.assertGreaterEqual(self.lineage.call_count, 4)
        transitions = [e for e in self.ledger.events() if e["kind"] in improvement.TRANSITIONS
                       and e["body"]["run_key"] == "owned-decision-run"]
        self.assertEqual(len(transitions), 1)
        self.measured.reset_mock()
        before = len(self.ledger.events())
        self.assertEqual(self.run_assessment(), result)
        self.measured.assert_not_called()
        self.assertEqual(len(self.ledger.events()), before)

    def test_checked_diagnosis_routes_each_declared_successor(self):
        for action in ("repair_decision_information_diagnosis", "review_unresolved_decision_evidence",
                       "prepare_dated_evidence_quality_protocol"):
            report = improvement.evaluate(improvement._load(self.suite)[0],
                improvement.reference_candidate(improvement._load(self.suite)[0]))
            for metric in ("source_span_resolution", "assertion_history_preservation",
                           "representation_manifest_preservation", "transformation_preservation",
                           "split_merge_preservation", "output_manifest_materialization"):
                report["metrics"][metric] = 1
            report["decision_pilot"] = deepcopy(self.compact)
            report["decision_pilot"]["next_step"]["action"] = action
            with self.subTest(action=action):
                self.assertEqual(improvement.select_next(report, "owned")["action"], action)
        report["decision_pilot"]["contract_id"] = "unreviewed-contract"
        with self.assertRaisesRegex(ValueError, "diagnostic contract"):
            improvement.select_next(report, "owned")

    def test_bad_diagnosis_origin_is_refused_before_claim(self):
        self.compact["origin"]["step_id"] = "unrelated"
        before = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, "currently queued"):
            self.run_assessment()
        self.assertEqual(len(self.ledger.events()), before)
        self.measured.assert_not_called()

    def test_preparation_failure_does_not_consume_diagnostic_queue(self):
        failed = {"prepared": {"artifacts": {"invalid-request": b"owned failure"}},
                  "error": {"message": "owned missing historical blob"}}
        before = len(self.ledger.events())
        with patch.object(improvement, "_prepare_decision", return_value=failed):
            with self.assertRaisesRegex(ValueError, "missing historical blob"):
                self.run_assessment()
        self.assertEqual(len(self.ledger.events()), before)
        self.assertEqual(improvement.status(self.ledger)["next_step"]["action"],
                         "investigate_decision_information_limits")

    def test_parent_changed_at_claim_is_refused_without_a_claim(self):
        real = self.lineage.side_effect
        calls = 0
        def check(prepared, events, after_step):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("Owned parent changed under claim lock")
            return real(prepared, events, after_step)
        self.lineage.side_effect = check
        before = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, "claim lock"):
            self.run_assessment()
        self.assertEqual(len(self.ledger.events()), before)
        self.measured.assert_not_called()

    def test_parent_changed_after_measurement_does_not_publish_diagnostic(self):
        def measure(prepared):
            result = {"report": deepcopy(prepared["report"]), "artifacts": dict(prepared["artifacts"])}
            prepared["artifacts"]["queue_parent"] = b"changed parent bytes"
            return result
        self.measured.side_effect = measure
        result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertEqual(result["next_step"]["action"], "diagnose_failed_assessment")
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])

    def test_generic_assessment_cannot_consume_diagnosis_or_its_failure(self):
        for action in ("investigate_decision_information_limits", "repair_decision_information_diagnosis",
                       "review_unresolved_decision_evidence", "prepare_dated_evidence_quality_protocol"):
            self.ledger.append("improvement_completed", {"run_key": "owned-" + action,
                "request": {"manifest": {}}, "next_step": {"id": self.origin, "state": "queued", "action": action}},
                "owned-" + action)
            before = len(self.ledger.events())
            with self.subTest(action=action), patch.object(improvement, "_prepare_decision", side_effect=REAL_PREPARE):
                with self.assertRaisesRegex(ValueError, "generic assessment cannot complete"):
                    improvement.assess(self.ledger, self.policy, self.suite, "reference", "missing-" + action,
                        after_step=self.origin, completed_work="Owned missing evidence control")
            self.assertEqual(len(self.ledger.events()), before)
        self.ledger.append("improvement_failed", {"run_key": "owned-failure",
            "request": {"manifest": {"decision-input:request": "a" * 64}},
            "next_step": {"id": self.origin, "state": "queued", "action": "diagnose_failed_assessment"}},
            "owned-failure")
        before = len(self.ledger.events())
        with patch.object(improvement, "_prepare_decision", side_effect=REAL_PREPARE):
            with self.assertRaisesRegex(ValueError, "failed decision assessment requires"):
                improvement.assess(self.ledger, self.policy, self.suite, "reference", "clear-failure",
                    after_step=self.origin, completed_work="Owned unrelated generic assessment")
        self.assertEqual(len(self.ledger.events()), before)


    def test_protocol_successor_refuses_malformed_and_wrong_phase_before_claim(self):
        self.ledger.append("improvement_completed", {"run_key": "owned-protocol-preparation",
            "request": {"manifest": {}}, "next_step": {"id": self.origin, "state": "queued",
            "action": "prepare_dated_evidence_quality_protocol"}}, "owned-protocol-preparation")
        before = len(self.ledger.events())
        failed = {"prepared": {"artifacts": {"invalid-request": b"owned malformed request"}},
                  "error": {"message": "owned unreadable protocol evidence"}}
        with patch.object(improvement, "_prepare_decision", return_value=failed):
            with self.assertRaisesRegex(ValueError, "unreadable protocol evidence"):
                self.run_assessment()
        self.assertEqual(len(self.ledger.events()), before)
        for phase in ("development", "fresh_comparison"):
            self.compact["phase"] = phase
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                self.run_assessment()
            self.assertEqual(len(self.ledger.events()), before)
        self.assertEqual(improvement.status(self.ledger)["next_step"]["action"],
                         "prepare_dated_evidence_quality_protocol")
        self.measured.assert_not_called()


    def test_explicit_invalid_diagnosis_cannot_consume_an_unrelated_queue(self):
        self.ledger.append("improvement_completed", {"run_key": "owned-generic",
            "request": {"manifest": {}}, "next_step": {"id": self.origin, "state": "queued",
            "action": "build_retrieval_baseline"}}, "owned-generic")
        path = self.root / "owned-request.json"
        path.write_text(canonical({"phase": improvement.decision_diagnosis.PHASE,
                                   "schema_version": 999, "invalid": "owned malformed diagnosis"}))
        before = len(self.ledger.events())
        with patch.object(improvement, "_prepare_decision", side_effect=REAL_PREPARE):
            with self.assertRaisesRegex(ValueError, "Invalid supplied decision diagnosis"):
                self.run_assessment()
        self.assertEqual(len(self.ledger.events()), before)
        self.assertEqual(improvement.status(self.ledger)["next_step"]["action"], "build_retrieval_baseline")
        self.measured.assert_not_called()

    def test_impossible_nested_diagnostic_time_fails_with_receipt(self):
        self.measured.side_effect = lambda prepared: {
            "report": deepcopy(prepared["report"]), "artifacts": dict(prepared["artifacts"]),
            "actual_resources": {"diagnostic_elapsed_seconds": 9.0}}
        tick = [0.0]
        def clock():
            tick[0] += 0.001
            return tick[0]
        with patch.object(improvement.time, "monotonic", side_effect=clock):
            result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertIn("exceeds its enclosing assessment duration", result["message"])
        self.assertEqual(result["next_step"]["action"], "diagnose_failed_assessment")


class DecisionDiagnosisIntegrationTests(unittest.TestCase):
    """Actual diagnostic, historical blobs and controller; no research data."""

    def setUp(self):
        from test_decision_diagnosis import make_study
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.study = make_study(Path(self.temporary.name))
        self.ledger = self.study["ledger"]
        self.addCleanup(self.ledger.close)
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        # These old fixture probes have separate integration coverage. The
        # diagnostic, ancestry validator, captures and atomic locks stay real.
        for name, metrics in (
            ("run_source_span_checks", ("source_span_resolution", "assertion_history_preservation")),
            ("run_manifest_checks", ("representation_manifest_preservation",)),
            ("run_transformation_checks", ("transformation_preservation",)),
            ("run_graph_view_checks", ("split_merge_preservation",)),
            ("run_materialization_checks", ("output_manifest_materialization",)),
        ):
            self.patches.enter_context(patch.object(improvement, name,
                return_value={"metrics": {metric: 1 for metric in metrics}, "scope": "owned legacy probe stub"}))

    def assess(self, run_key, *, candidate="reference"):
        return improvement.assess(self.ledger, EXAMPLES / "policy.json", EXAMPLES / "entities.json",
            candidate, run_key, after_step=self.study["request"]["origin"]["step_id"],
            completed_work="Owned real-diagnostic integration control; not a research execution",
            decision_study_path=self.study["request_path"])

    def assert_full_completion(self, result):
        self.assertEqual(result["result"], "assessed", result.get("message"))
        pilot = result["report"]["decision_pilot"]
        self.assertEqual(pilot["phase"], improvement.decision_diagnosis.PHASE)
        self.assertEqual(pilot["counts"]["attempts"], 96)
        self.assertEqual(pilot["status"], "checked")
        self.assertGreaterEqual(result["actual_resources"]["first_diagnostic_elapsed_seconds"], 0)
        self.assertLessEqual(result["actual_resources"]["first_diagnostic_elapsed_seconds"], 10)
        observation = self.ledger.get(result["input_observations"]["decision-result:diagnostic_table"], "observation")
        raw = (self.ledger.root / "blobs" / observation["body"]["content_hash"]).read_bytes()
        self.assertEqual(digest(raw), pilot["diagnosis"]["detail_sha256"])
        self.assertEqual(len(json.loads(raw)["attempts"]), 96)
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_real_initial_diagnosis_and_zero_computation_replay(self):
        from test_decision_diagnosis import calls_named, FORBIDDEN_CALLS
        with calls_named(FORBIDDEN_CALLS) as forbidden:
            result = self.assess("owned-information-initial")
        self.assertEqual(forbidden, [])
        self.assert_full_completion(result)
        before = len(self.ledger.events())
        with calls_named(FORBIDDEN_CALLS | {"_diagnose"}) as replayed:
            self.assertEqual(self.assess("owned-information-initial"), result)
        self.assertEqual(replayed, [])
        self.assertEqual(len(self.ledger.events()), before)
        changed = deepcopy(self.study["request"])
        changed["study_id"] = "owned-altered-replay"
        self.study["request_path"].write_text(canonical(changed))
        with self.assertRaisesRegex(ValueError, "Run key already used with different"):
            self.assess("owned-information-initial")
        self.assertEqual(len(self.ledger.events()), before)

    def test_real_failed_diagnosis_directly_completes_full_corrected_diagnosis(self):
        from test_decision_diagnosis import calls_named, FORBIDDEN_CALLS
        with patch.object(improvement.decision_assessment, "assess_prepared_decision_study",
                          side_effect=ValueError("Owned postclaim diagnostic interruption")):
            failed = self.assess("owned-information-failed")
        self.assertEqual(failed["result"], "failed")
        self.assertEqual(failed["next_step"]["action"], "diagnose_failed_assessment")
        failure_event = self.ledger.get("improvement:owned-information-failed:failed")
        request = self.study["request"]
        request["origin"] = {"step_id": failed["next_step"]["id"]}
        request["queue_parent"] = {"event_id": failure_event["id"], "event_hash": failure_event["hash"]}
        self.study["request_path"].write_text(canonical(request))
        with calls_named(FORBIDDEN_CALLS) as forbidden:
            completed = self.assess("owned-information-corrected")
        self.assertEqual(forbidden, [])
        self.assert_full_completion(completed)
        self.assertEqual(completed["report"]["decision_pilot"]["ancestry"]["mode"], "failed_attempt_continuation")
        self.assertEqual(completed["report"]["decision_pilot"]["evidence_origin"]["event_hash"],
                         self.study["origin"]["hash"])
        transitions = [e for e in self.ledger.events() if e["kind"] in improvement.TRANSITIONS]
        self.assertEqual([e["body"]["run_key"] for e in transitions],
                         ["owned-c8", "owned-information-failed", "owned-information-corrected"])
        self.assertEqual(completed["next_step"]["action"], "prepare_dated_evidence_quality_protocol")
        before = len(self.ledger.events())
        with calls_named(FORBIDDEN_CALLS | {"_diagnose"}) as replayed:
            self.assertEqual(self.assess("owned-information-corrected"), completed)
        self.assertEqual(replayed, [])
        with self.assertRaisesRegex(ValueError, "Stale predecessor"):
            self.assess("owned-information-stale")
        self.assertEqual(len(self.ledger.events()), before)


    def test_failed_enclosing_fixture_cannot_replace_the_diagnostic_successor(self):
        result = self.assess("owned-information-degraded", candidate="degraded")
        self.assertEqual(result["result"], "failed")
        self.assertIn("enclosing conformance check", result["message"])
        self.assertEqual(result["next_step"]["action"], "diagnose_failed_assessment")
        self.assertIn("decision-input:request", result["request"]["manifest"])
        observations = [e for e in self.ledger.events() if e["kind"] == "observation"]
        self.assertTrue(any(e["body"]["source"] == "improvement-input:decision-result:diagnostic_table"
                            for e in observations))
        self.assertFalse(any(e["kind"] == "improvement_completed"
                             and e["body"]["run_key"] == "owned-information-degraded" for e in self.ledger.events()))
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])


class DatedDeliveryControllerTests(unittest.TestCase):
    """Queue/timing wiring only; actual historical capture is tested separately."""

    def setUp(self):
        DecisionControllerTests.setUp(self)
        self.parent = self.ledger.append("improvement_completed", {
            "run_key": "owned-information", "request": {"manifest": {}},
            "next_step": {"id": self.origin, "state": "queued",
                          "action": "prepare_dated_evidence_quality_protocol"}}, "owned-information-complete")
        self.compact.update(phase="dated_evidence_quality_preparation", stage="protocol_preparation",
            contract_id=improvement.dated_delivery.CONTRACT_ID,
            evidence_origin={"event_id": self.parent["id"], "event_hash": self.parent["hash"]},
            queue_parent={"event_id": self.parent["id"], "event_hash": self.parent["hash"]},
            ancestry={"scope": "owned wiring fixture only"},
            next_step={"action": "bind_dated_artifact_delivery"})
        self.prepared["artifacts"]["queue_parent"] = canonical(self.parent).encode()
        self.seconds = None
        self.measured.side_effect = lambda prepared: {
            "report": deepcopy(prepared["report"]),
            "artifacts": {**prepared["artifacts"], "assessment_report": canonical(prepared["report"]).encode()},
            "actual_resources": {"first_verification_elapsed_seconds": self.seconds}}

        def lineage(prepared, events, after_step):
            current = [e for e in events if e["kind"] in improvement.TRANSITIONS][-1]
            if (canonical(current).encode() != prepared["artifacts"]["queue_parent"]
                    or current["body"]["next_step"]["id"] != after_step):
                raise ValueError("Owned delivery lineage rejects a changed parent")
        self.lineage = self.patches.enter_context(patch.object(
            improvement.dated_delivery, "validate_lineage", side_effect=lineage))

    tearDown = DecisionControllerTests.tearDown
    run_assessment = DecisionControllerTests.run_assessment

    def selector_report(self):
        suite = improvement._load(self.suite)[0]
        report = improvement.evaluate(suite, improvement.reference_candidate(suite))
        report["metrics"].update({name: 1 for name in (
            "source_span_resolution", "assertion_history_preservation", "representation_manifest_preservation",
            "transformation_preservation", "split_merge_preservation", "output_manifest_materialization")})
        report["decision_pilot"] = deepcopy(self.compact)
        return report

    def test_preparation_completion_and_successor_are_atomic_and_replay_is_readonly(self):
        result = self.run_assessment()
        self.assertEqual(result["result"], "assessed")
        self.assertEqual(result["next_step"]["action"], "bind_dated_artifact_delivery")
        self.assertIsNone(result["next_step"]["metric"])
        self.assertIsNone(result["actual_resources"]["first_verification_elapsed_seconds"])
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertEqual(result["next_step"]["evidence"]["evidence_origin"], self.compact["evidence_origin"])
        self.assertGreaterEqual(self.lineage.call_count, 4)
        self.assertIn("dated artifact-delivery phase", result["scope"])
        self.assertNotIn("decision-development comparison", result["scope"])
        count = len(self.ledger.events())
        self.measured.reset_mock()
        self.assertEqual(self.run_assessment(), result)
        self.measured.assert_not_called()
        self.assertEqual(len(self.ledger.events()), count)
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])

    def test_phase_specific_successors_and_no_invented_quality(self):
        for phase, stage in improvement.dated_delivery.PHASES.items():
            for action in improvement.dated_delivery.PHASE_NEXT_ACTIONS[phase]:
                with self.subTest(phase=phase, action=action):
                    report = self.selector_report()
                    report["decision_pilot"].update(phase=phase, stage=stage, next_step={"action": action})
                    chosen = improvement.select_next(report, "owned")
                    self.assertEqual(chosen["action"], action)
                    self.assertIsNone(chosen["metric"])
                    self.assertIsNone(chosen["observed"])
                    self.assertIsNone(chosen["estimated_success_probability"])
        for changes in ({"stage": "exposed_development"}, {"contract_id": "unreviewed"},
                        {"next_step": {"action": "prepare_public_research_map_view"}}):
            report = self.selector_report()
            report["decision_pilot"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                improvement.select_next(report, "owned-invalid")

    def test_no_generic_assessment_can_consume_any_delivery_successor(self):
        for action in improvement.dated_delivery.SEMANTIC_ACTIONS | {"prepare_public_research_map_view"}:
            self.ledger.append("improvement_completed", {"run_key": "owned-" + action, "request": {"manifest": {}},
                "next_step": {"id": self.origin, "state": "queued", "action": action}}, "owned-" + action)
            count = len(self.ledger.events())
            with self.subTest(action=action), patch.object(improvement, "_prepare_decision", side_effect=REAL_PREPARE):
                with self.assertRaisesRegex(ValueError, "generic assessment"):
                    improvement.assess(self.ledger, self.policy, self.suite, "reference", "missing-" + action,
                        after_step=self.origin, completed_work="Owned missing delivery evidence; not research")
            self.assertEqual(len(self.ledger.events()), count)

    def test_malformed_explicit_delivery_cannot_consume_an_unrelated_queue(self):
        self.ledger.append("improvement_completed", {"run_key": "owned-generic", "request": {"manifest": {}},
            "next_step": {"id": self.origin, "state": "queued", "action": "repair_time_eligibility"}}, "owned-generic")
        for phase in improvement.dated_delivery.PHASES:
            failed = {"prepared": {"artifacts": {"invalid-request-prefix": canonical({"phase": phase}).encode()}},
                      "error": {"message": "Owned missing delivery protocol"}}
            count = len(self.ledger.events())
            with self.subTest(phase=phase), patch.object(improvement, "_prepare_decision", return_value=failed):
                with self.assertRaisesRegex(ValueError, "missing delivery protocol"):
                    self.run_assessment()
            self.assertEqual(len(self.ledger.events()), count)
        self.measured.assert_not_called()

    def test_bad_origin_refuses_before_claim(self):
        self.compact["origin"]["step_id"] = "unrelated"
        count = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, "currently queued"):
            self.run_assessment()
        self.assertEqual(len(self.ledger.events()), count)
        self.measured.assert_not_called()

    def use_owned_delivery_check(self):
        parent = self.ledger.append("improvement_completed", {
            "run_key": "owned-registration", "request": {"manifest": {}},
            "next_step": {"id": self.origin, "state": "queued", "action": "check_dated_artifact_delivery"}},
            "owned-registration-complete")
        self.compact.update(phase="dated_artifact_delivery_check", stage="retained_delivery_check",
            queue_parent={"event_id": parent["id"], "event_hash": parent["hash"]},
            next_step={"action": "prepare_public_research_map_view"})
        self.prepared["artifacts"]["queue_parent"] = canonical(parent).encode()

    def test_first_verification_timing_is_retained_separately(self):
        self.use_owned_delivery_check()
        self.seconds = 0.001
        result = self.run_assessment()
        self.assertEqual(result["result"], "assessed")
        self.assertEqual(result["actual_resources"]["first_verification_elapsed_seconds"], 0.001)
        self.assertGreaterEqual(result["actual_resources"]["elapsed_seconds"], 0.001)
        self.assertIn("completion revalidation excluded", result["actual_resources"]["verification_timing_scope"])

    def test_invalid_verification_timing_is_a_durable_failure(self):
        self.use_owned_delivery_check()
        self.seconds = True
        result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertIn("Invalid delivery verification elapsed-time", result["message"])
        self.assertEqual(result["next_step"]["action"], "diagnose_failed_assessment")

    def test_nested_verification_cannot_exceed_assessment_time(self):
        self.use_owned_delivery_check()
        self.seconds = 1
        with patch.object(improvement.time, "monotonic", return_value=1):
            result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertIn("exceeds its enclosing assessment", result["message"])

    def test_failed_enclosing_probe_preserves_semantic_task_as_failure(self):
        with patch.object(improvement, "run_source_span_checks", return_value={"metrics": {
                "source_span_resolution": 0, "assertion_history_preservation": 1}}):
            result = self.run_assessment()
        self.assertEqual(result["result"], "failed")
        self.assertEqual(result["next_step"]["action"], "diagnose_failed_assessment")
        self.assertIn("enclosing conformance check", result["message"])
        self.assertIn("decision-input:owned-input", result["request"]["manifest"])


class DatedDeliveryIntegrationTests(unittest.TestCase):
    """Real delivery phase/ledger/controller paths over owned synthetic receipts."""

    def setUp(self):
        from test_dated_delivery import make_study
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.study = make_study(Path(self.temporary.name))
        self.ledger = self.study["ledger"]
        self.addCleanup(self.ledger.close)
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        for name, metrics in (
            ("run_source_span_checks", ("source_span_resolution", "assertion_history_preservation")),
            ("run_manifest_checks", ("representation_manifest_preservation",)),
            ("run_transformation_checks", ("transformation_preservation",)),
            ("run_graph_view_checks", ("split_merge_preservation",)),
            ("run_materialization_checks", ("output_manifest_materialization",)),
        ):
            self.patches.enter_context(patch.object(improvement, name,
                return_value={"metrics": {metric: 1 for metric in metrics}, "scope": "owned legacy probe stub"}))

    def assess(self, key):
        return improvement.assess(self.ledger, EXAMPLES / "policy.json", EXAMPLES / "entities.json", "reference", key,
            after_step=self.study["request"]["origin"]["step_id"],
            completed_work="Owned real delivery lifecycle control; not an actual backlog task",
            decision_study_path=self.study["request_path"])

    def assert_completed(self, result, successor):
        self.assertEqual(result["result"], "assessed", result.get("message"))
        self.assertEqual(result["next_step"]["action"], successor)
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertEqual(improvement.status(self.ledger)["unfinished_runs"], [])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_real_preparation_registration_delivery_and_zero_verification_replay(self):
        from test_dated_delivery import register_study, deliver
        from test_decision_diagnosis import calls_named, FORBIDDEN_CALLS
        with calls_named(FORBIDDEN_CALLS | {"_diagnose", "verify_inventory"}) as called:
            prepared = self.assess("owned-delivery-protocol")
        self.assertEqual(called, [])
        self.assert_completed(prepared, "bind_dated_artifact_delivery")
        self.assertIsNone(prepared["actual_resources"]["first_verification_elapsed_seconds"])
        count = len(self.ledger.events())
        with calls_named({"_diagnose", "verify_inventory"}) as called:
            self.assertEqual(self.assess("owned-delivery-protocol"), prepared)
        self.assertEqual(called, [])
        self.assertEqual(len(self.ledger.events()), count)
        protocol = self.ledger.get("improvement:owned-delivery-protocol:complete")
        register_study(self.study, protocol_event=protocol, accept_registration=False)
        registered = self.assess("owned-delivery-registration")
        self.assert_completed(registered, "check_dated_artifact_delivery")
        self.study["registration_event"] = self.ledger.get("improvement:owned-delivery-registration:complete")
        first = deliver(self.study)
        checked = self.assess("owned-delivery-check")
        self.assert_completed(checked, "prepare_public_research_map_view")
        outcome = checked["report"]["decision_pilot"]["outcome"]
        self.assertTrue(outcome["artifact_quality"])
        self.assertEqual(outcome["first_submission"]["observation_id"], first["id"])
        self.assertIsNotNone(checked["actual_resources"]["first_verification_elapsed_seconds"])
        self.ledger.capture("improvement-input:owned-unrelated", b"later unrelated bytes", event_id="owned:unrelated")
        count = len(self.ledger.events())
        with calls_named(FORBIDDEN_CALLS | {"_diagnose", "verify_inventory"}) as called:
            self.assertEqual(self.assess("owned-delivery-check"), checked)
        self.assertEqual(called, [])
        self.assertEqual(len(self.ledger.events()), count)
        self.assertEqual([event["body"]["run_key"] for event in self.ledger.events()
                          if event["kind"] == "improvement_completed"][-3:],
                         ["owned-delivery-protocol", "owned-delivery-registration", "owned-delivery-check"])

    def test_real_failed_preparation_continues_with_actual_claim_proof(self):
        from test_dated_delivery import write_request
        delivery = improvement.dated_delivery
        with patch.object(improvement.decision_assessment, "assess_prepared_decision_study",
                          side_effect=ValueError("Owned interruption after claim")):
            failed = self.assess("owned-delivery-failed")
        self.assertEqual(failed["result"], "failed")
        self.assertEqual(failed["next_step"]["action"], "diagnose_failed_assessment")
        failure = self.ledger.get("improvement:owned-delivery-failed:failed")
        write_request(self.study, delivery.PREPARATION, failure, self.study["packet"], checkpoint_event=failure)
        completed = self.assess("owned-delivery-corrected")
        self.assert_completed(completed, "bind_dated_artifact_delivery")
        self.assertEqual(completed["report"]["decision_pilot"]["ancestry"]["mode"], "failed_attempt_continuation")
        self.assertEqual(completed["report"]["decision_pilot"]["evidence_origin"]["event_hash"], self.study["origin"]["hash"])
        count = len(self.ledger.events())
        self.assertEqual(self.assess("owned-delivery-corrected"), completed)
        self.assertEqual(len(self.ledger.events()), count)

    def test_real_malformed_first_delivery_remains_negative_after_correction(self):
        from test_dated_delivery import register_study, deliver, capture, inventory_bytes, write_request
        delivery = improvement.dated_delivery
        register_study(self.study)
        first = deliver(self.study, b'{"schema_version":1,"schema_version":1}')
        capture(self.study, "inventory", inventory_bytes(self.study), "later-correction")
        write_request(self.study, delivery.CHECK, self.study["registration_event"], self.study["packet"])
        result = self.assess("owned-malformed-first")
        self.assert_completed(result, "prepare_public_research_map_view")
        outcome = result["report"]["decision_pilot"]["outcome"]
        self.assertFalse(outcome["artifact_quality"])
        self.assertEqual(outcome["first_submission"]["observation_id"], first["id"])
        self.assertEqual(outcome["claim_agreement"], {"numerator": 0, "denominator": 1, "value": 0.0})

    def test_real_unresolved_check_and_one_review_have_finite_closure(self):
        from datetime import datetime, timedelta
        from test_dated_delivery import register_study, capture, inventory_bytes, write_request, identity
        delivery = improvement.dated_delivery
        register_study(self.study)
        registration = self.study["registration_event"]
        capture(self.study, "inventory", inventory_bytes(self.study))
        at = datetime.fromisoformat(registration["recorded_at"]) + timedelta(hours=48)
        closure_value = {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
            "actor": "reviewer", "state": "unresolved", "missing": ["verification", "adjudication"]}
        closure = capture(self.study, "closure", closure_value, at=at)
        packet = {"schema_version": 1, "phase": delivery.CHECK,
            "registration_event": identity(registration), "closure_observation": closure["id"]}
        write_request(self.study, delivery.CHECK, registration, packet)
        with patch.object(self.ledger, "clock", return_value=(at + timedelta(seconds=1)).isoformat()):
            result = self.assess("owned-delivery-unresolved")
        self.assert_completed(result, "review_dated_delivery_evidence")
        parent = self.ledger.get("improvement:owned-delivery-unresolved:complete")
        closure_value["review_of"] = identity(parent)
        review = capture(self.study, "closure", closure_value, "review-closure", at + timedelta(seconds=2))
        packet.update(phase=delivery.REVIEW, closure_observation=review["id"])
        write_request(self.study, delivery.REVIEW, parent, packet)
        with patch.object(self.ledger, "clock", return_value=(at + timedelta(seconds=3)).isoformat()):
            result = self.assess("owned-delivery-closed")
        self.assert_completed(result, "prepare_public_research_map_view")
        outcome = result["report"]["decision_pilot"]["outcome"]
        self.assertEqual(outcome["status"], "terminal_unresolved")
        self.assertIsNone(outcome["artifact_quality"])
        self.assertEqual(outcome["claim_agreement"]["denominator"], 0)
        count = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, "Stale predecessor"):
            self.assess("owned-second-review")
        self.assertEqual(len(self.ledger.events()), count)

    def assert_pending_check_preserves_queue(self, key):
        from test_decision_diagnosis import calls_named
        before_events = self.ledger.events()
        before_status = improvement.status(self.ledger)
        with calls_named({"verify_inventory", "_diagnose"}) as called:
            with self.assertRaises(ValueError):
                self.assess(key)
        self.assertEqual(called, [])
        self.assertEqual(self.ledger.events(), before_events)
        self.assertEqual(improvement.status(self.ledger), before_status)
        self.assertEqual(before_status["next_step"]["action"], "check_dated_artifact_delivery")
        self.assertEqual(before_status["unfinished_runs"], [])

    def test_real_missing_delivery_waits_without_claim_or_verification(self):
        from test_dated_delivery import register_study, write_request, identity
        delivery = improvement.dated_delivery
        register_study(self.study)
        registration = self.study["registration_event"]
        packet = {"schema_version": 1, "phase": delivery.CHECK,
            "registration_event": identity(registration), "closure_observation": None}
        write_request(self.study, delivery.CHECK, registration, packet)
        self.assert_pending_check_preserves_queue("owned-pending-delivery")

    def test_real_incomplete_delivery_waits_without_claim_or_verification(self):
        from test_dated_delivery import register_study, capture, inventory_bytes, write_request, identity
        delivery = improvement.dated_delivery
        register_study(self.study)
        registration = self.study["registration_event"]
        capture(self.study, "inventory", inventory_bytes(self.study))
        packet = {"schema_version": 1, "phase": delivery.CHECK,
            "registration_event": identity(registration), "closure_observation": None}
        write_request(self.study, delivery.CHECK, registration, packet)
        self.assert_pending_check_preserves_queue("owned-pending-evidence")

    def test_real_premature_closure_preserves_pending_check(self):
        from datetime import datetime, timedelta
        from test_dated_delivery import register_study, capture, write_request, identity
        delivery = improvement.dated_delivery
        register_study(self.study)
        registration = self.study["registration_event"]
        at = datetime.fromisoformat(registration["recorded_at"]) + timedelta(hours=23)
        closure = capture(self.study, "closure", {
            "schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
            "actor": "reviewer", "state": "no_delivery", "missing": ["artifact"]}, at=at)
        packet = {"schema_version": 1, "phase": delivery.CHECK,
            "registration_event": identity(registration), "closure_observation": closure["id"]}
        write_request(self.study, delivery.CHECK, registration, packet)
        self.assert_pending_check_preserves_queue("owned-premature-closure")


if __name__ == "__main__":
    unittest.main()
