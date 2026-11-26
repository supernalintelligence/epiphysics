"""Owned, exposed pilot controls; no registered/private execution or final cases."""
import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from epiphysics import decision_evaluation as evaluation

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "control-exchange"


def at(seconds):
    return (datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(kind, eid, effective, *, observed=None, reference=None, auth="verified", issuer="R", subject="R", object=None):
    return {"event_id": eid, "kind": kind, "issuer": issuer, "subject": subject,
            "object": object or ("O" if kind.startswith("dispute_") else "A"), "obligation_id": "O",
            "effective_at": at(effective), "observed_at": at(effective if observed is None else observed),
            "reference": reference, "artifact_sha256": None, "verdict": None, "authentication": auth}


class DecisionEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traces = json.loads((EXAMPLES / "development-traces.json").read_bytes())["traces"]

    def base(self, case_id=None):
        result = deepcopy(self.traces[0])
        if case_id is not None:
            result["trace_id"] = case_id
        return result

    def release(self, trace):
        result = evaluation.reference_decision(trace)
        result.update(action="release", reason="release_requirements_satisfied")
        return result

    def hold(self, trace, *, ids=None):
        return {"action": "hold", "reason": "incomplete_evidence", "release_key": evaluation.compute_release_key(trace["task"]),
                "support_event_ids": [] if ids is None else ids}

    def test_twelve_exposed_hand_actions_and_all_declared_metric_categories(self):
        rows = []
        for trace in self.traces:
            with self.subTest(trace=trace["trace_id"]):
                reference = evaluation.reference_decision(trace)
                self.assertEqual(trace["development_only_annotation"]["hand_expected_visible_action"], reference["action"])
                row = evaluation.evaluate_simulated_proposal(trace, reference)
                self.assertTrue(row["proposal_valid"])
                self.assertEqual(trace["trace_id"], row["case_id"])
                self.assertEqual(trace["mechanism"], row["mechanism"])
                rows.append(row)
        summary = evaluation.aggregate_metrics(rows)
        contract = json.loads((EXAMPLES / "evaluation-contract.json").read_bytes())
        self.assertEqual({m["id"] for m in contract["metrics"]}, set(summary["metrics"]))
        self.assertEqual(12, summary["case_count"])
        self.assertEqual(0, summary["counts"]["failed_attempts"])

    def test_hidden_revocation_preserves_reference_but_refuses_unsafe_effect(self):
        first, hidden = self.traces[:2]
        visible = evaluation.reference_decision(first)
        self.assertEqual(visible, evaluation.reference_decision(hidden))
        good = evaluation.evaluate_simulated_proposal(first, visible)
        bad = evaluation.evaluate_simulated_proposal(hidden, visible)
        self.assertTrue(good["facts"]["world_opportunity"])
        self.assertFalse(bad["facts"]["world_authorized"])
        self.assertEqual("refused", bad["effect_receipt"]["status"])
        self.assertEqual(1, bad["metric_flags"]["unauthorized_release_proposals_all"])
        self.assertEqual(0, bad["metric_flags"]["evidence_unjustified_release_proposals"])
        self.assertEqual(0, bad["metric_flags"]["unauthorized_effects"])

    def test_private_truth_attempt_and_annotation_do_not_choose_reference_action(self):
        trace = self.base()
        before = evaluation.reference_decision(trace)
        trace["later_outcome"].update(artifact_valid=False, completed_at=at(800), artifact_sha256="0" * 64)
        trace["attempt_id"] = "another-attempt"
        trace["development_only_annotation"] = {"wrong_expected_action": "hold"}
        self.assertEqual(before, evaluation.reference_decision(trace))
        self.assertFalse(evaluation.resolve_world(trace)["artifact_ready_valid"])

    def test_named_revoke_preserves_another_grant_and_null_clears_all(self):
        trace = self.base()
        trace["events"] += [event("grant", "g2", 200), event("revoke", "r", 400, reference="g")]
        self.assertEqual(["g2"], evaluation.resolve_world(trace)["active_grant_ids"])
        self.assertEqual("release", evaluation.reference_decision(trace)["action"])
        trace["events"][-1]["reference"] = None
        self.assertEqual([], evaluation.resolve_world(trace)["active_grant_ids"])
        trace["events"].append(event("grant", "g3", 500))
        self.assertEqual(["g3"], evaluation.resolve_world(trace)["active_grant_ids"])

    def test_same_time_scope_and_input_order_do_not_change_authority(self):
        trace = self.base()
        trace["events"] += [event("grant", "g2", 100), event("revoke", "r", 100, reference="g")]
        expected = evaluation.reference_decision(trace)
        self.assertEqual(["g2"], evaluation.resolve_world(trace)["active_grant_ids"])
        trace["events"].reverse()
        self.assertEqual(expected, evaluation.reference_decision(trace))
        trace["events"][0]["reference"] = None
        self.assertEqual([], evaluation.resolve_world(trace)["active_grant_ids"])

    def test_missing_foreign_stale_and_future_named_references_are_inert(self):
        trace = self.base()
        trace["events"] += [event("grant", "g2", 250), event("revoke", "r1", 200, reference="g"),
                            event("revoke", "r2", 300, reference="g"), event("revoke", "missing", 400, reference="absent"),
                            event("grant", "foreign", 200, issuer="P"), event("revoke", "wrong", 400, reference="foreign"),
                            event("revoke", "early", 50, reference="g2")]
        self.assertEqual(["g2"], evaluation.resolve_world(trace)["active_grant_ids"])
        self.assertEqual("release", evaluation.reference_decision(trace)["action"])

    def test_dispute_closures_require_bound_strictly_earlier_named_open(self):
        for close in (event("dispute_close", "c", 700, observed=550, reference="o"),
                      event("dispute_close", "c", 300, reference="o"),
                      event("dispute_close", "c", 400, reference="missing"),
                      event("dispute_close", "c", 400, reference="o", issuer="P"),
                      event("dispute_close", "c", 400, reference="o", auth="invalid")):
            with self.subTest(close=close):
                trace = self.base()
                trace["events"] += [event("dispute_open", "o", 300), close]
                self.assertEqual(["o"], evaluation.resolve_world(trace)["open_dispute_ids"])
                self.assertEqual("unresolved_dispute", evaluation.reference_decision(trace)["reason"])
        trace = self.base()
        trace["events"] += [event("dispute_open", "o", 300), event("dispute_open", "o2", 310),
                            event("dispute_close", "c", 400, reference="o"), event("dispute_close", "c2", 450, reference="o")]
        self.assertEqual(["o2"], evaluation.resolve_world(trace)["open_dispute_ids"])

    def test_future_verification_conflict_grant_and_release_are_not_operative(self):
        trace = self.base()
        trace["events"][2]["effective_at"] = at(700)
        self.assertEqual("missing_verification", evaluation.reference_decision(trace)["reason"])
        trace = self.base()
        failure = deepcopy(trace["events"][2])
        failure.update(event_id="future-fail", verdict="fail", effective_at=at(700), observed_at=at(500))
        trace["events"].append(failure)
        self.assertEqual("release", evaluation.reference_decision(trace)["action"])
        self.assertIn("future-fail", evaluation.reference_decision(trace)["support_event_ids"])
        trace["events"][0]["effective_at"] = at(700)
        self.assertFalse(evaluation.resolve_world(trace)["world_authorized"])
        trace = deepcopy(self.traces[6])
        trace["events"][-1]["effective_at"] = at(700)
        self.assertFalse(evaluation.resolve_world(trace)["world_duplicate"])
        self.assertEqual("release", evaluation.reference_decision(trace)["action"])

    def test_authentication_binding_and_conflict_remain_distinct(self):
        trace = self.base()
        failure = deepcopy(trace["events"][2])
        failure.update(event_id="fail", verdict="fail", authentication="invalid")
        trace["events"].append(failure)
        self.assertEqual("release", evaluation.reference_decision(trace)["action"])
        failure["authentication"] = "unknown"
        self.assertEqual("uncertain_authentication", evaluation.reference_decision(trace)["reason"])
        failure["issuer"] = "P"
        self.assertEqual("release", evaluation.reference_decision(trace)["action"])
        failure.update(issuer="R", authentication="verified")
        self.assertEqual("conflicting_evidence", evaluation.reference_decision(trace)["reason"])
        failure.update(verdict="pass", artifact_sha256="0" * 64)
        self.assertEqual("conflicting_evidence", evaluation.reference_decision(trace)["reason"])
        self.assertTrue(evaluation.resolve_world(trace)["world_authorized"])
        unknown_close = event("dispute_close", "c", 500, reference="missing", auth="unknown")
        trace["events"].append(unknown_close)
        self.assertEqual("uncertain_authentication", evaluation.reference_decision(trace)["reason"])

    def test_reversed_authority_and_unknown_revoke_do_not_change_world_rights(self):
        reverse = self.traces[9]
        self.assertFalse(evaluation.resolve_world(reverse)["world_authorized"])
        self.assertEqual("authority_absent_or_revoked", evaluation.reference_decision(reverse)["reason"])
        trace = self.base()
        trace["events"].append(event("revoke", "r", 500, reference="g", auth="unknown"))
        self.assertTrue(evaluation.resolve_world(trace)["world_authorized"])
        self.assertEqual("uncertain_authentication", evaluation.reference_decision(trace)["reason"])

    def test_expiry_is_not_invalid_artifact(self):
        trace = self.base()
        trace["task"]["deadline"] = at(500)
        row = evaluation.evaluate_simulated_proposal(trace, self.release(trace))
        self.assertTrue(row["facts"]["artifact_ready_valid"])
        self.assertFalse(row["facts"]["world_authorized"])
        self.assertEqual(1, row["metric_flags"]["unauthorized_release_proposals_all"])
        self.assertEqual(0, row["metric_flags"]["invalid_artifact_release_proposals"])
        self.assertEqual("deadline_expired", row["reference_proposal"]["reason"])

    def test_invalid_or_unready_artifact_does_not_become_an_authority_guard(self):
        for changes in ({"artifact_valid": False}, {"completed_at": at(700)}, {"artifact_sha256": "0" * 64}, {"artifact_id": "other"}):
            with self.subTest(changes=changes):
                trace = self.base()
                trace["later_outcome"].update(changes)
                row = evaluation.evaluate_simulated_proposal(trace, self.release(trace))
                self.assertTrue(row["facts"]["world_authorized"])
                self.assertFalse(row["facts"]["artifact_ready_valid"])
                self.assertEqual("accepted", row["effect_receipt"]["status"])
                self.assertEqual(1, row["metric_flags"]["invalid_artifact_release_proposals"])
                self.assertEqual(0, row["metric_flags"]["valid_timely_release"])

    def test_duplicate_proposal_remains_counted_while_effect_is_reused(self):
        trace = deepcopy(self.traces[6])
        row = evaluation.evaluate_simulated_proposal(trace, self.release(trace))
        self.assertTrue(row["facts"]["world_duplicate"])
        self.assertEqual("reused", row["effect_receipt"]["status"])
        self.assertEqual(0, row["effect_receipt"]["new_effects"])
        self.assertEqual(1, row["metric_flags"]["duplicate_release_proposals_all"])
        self.assertEqual(0, row["metric_flags"]["duplicate_effects"])

    def test_replay_state_is_explicit_case_local_and_attempt_id_independent(self):
        trace = self.base()
        original = deepcopy(trace)
        proposal = self.release(trace)
        first = evaluation.evaluate_simulated_proposal(trace, proposal)
        trace["attempt_id"] = "different-attempt"
        replay = evaluation.evaluate_simulated_proposal(trace, proposal, prior_effect_keys=first["resulting_effect_keys"])
        self.assertEqual("reused", replay["effect_receipt"]["status"])
        self.assertEqual(first["effect_receipt"]["effect_id"], replay["effect_receipt"]["effect_id"])
        self.assertEqual(first["resulting_effect_keys"], replay["resulting_effect_keys"])
        independent = evaluation.evaluate_simulated_proposal(trace, proposal)
        self.assertEqual("accepted", independent["effect_receipt"]["status"])
        self.assertEqual(original, {**trace, "attempt_id": original["attempt_id"]})
        second_case = deepcopy(trace)
        second_case["trace_id"] = "another-case"
        summary = evaluation.aggregate_metrics([first, evaluation.evaluate_simulated_proposal(second_case, proposal)])
        self.assertEqual(2, summary["effects_by_release_key"][proposal["release_key"]]["new_effects"])
        self.assertEqual(0, summary["metrics"]["duplicate_effects"]["numerator"])

    def test_partial_hold_is_valid_without_agreeing_with_lossless_reference(self):
        trace = self.base()
        row = evaluation.evaluate_simulated_proposal(trace, self.hold(trace))
        self.assertTrue(row["proposal_valid"])
        self.assertEqual("release", row["reference_proposal"]["action"])
        self.assertEqual(1, row["metric_flags"]["missed_observable_opportunities"])
        self.assertEqual(1, row["metric_flags"]["valid_output_completion"])

    def test_malformed_missing_worker_failure_and_support_ids_are_failed_rows(self):
        trace = self.base()
        good = self.release(trace)
        bad = [None, "x" * 1025, {**good, "action": "pay"}, {**good, "reason": "missing_delivery"},
               {**good, "release_key": "0" * 64}, {**good, "support_event_ids": ["hidden-revoke"]},
               {**good, "support_event_ids": ["g", "g"]}, {**good, "support_event_ids": ["v", "g"]},
               {**good, "support_event_ids": [True]}, {**good, "extra": 1}]
        for proposal in bad:
            with self.subTest(proposal=proposal):
                row = evaluation.evaluate_simulated_proposal(trace, proposal)
                self.assertFalse(row["proposal_valid"])
                self.assertTrue(row["proposal_error"])
                self.assertEqual("not_attempted", row["effect_receipt"]["status"])
                self.assertEqual(1, evaluation.aggregate_metrics([row])["counts"]["failed_attempts"])
        row = evaluation.evaluate_simulated_proposal(trace, good, error="worker_timeout")
        self.assertEqual(good, row["proposal"])
        self.assertFalse(row["proposal_valid"])
        self.assertEqual("worker_timeout", row["proposal_error"])

    def test_eligible_support_is_sorted_policy_kind_basis_including_inert_rows(self):
        trace = self.base()
        trace["events"].append(event("note", "n", 200, auth="unknown", object="X"))
        trace["events"].append(event("revoke", "inert", 700, observed=550, reference="g", auth="invalid"))
        trace["events"].append(event("revoke", "hidden", 500, observed=700, reference="g"))
        reference = evaluation.reference_decision(trace)
        self.assertEqual(["d", "g", "inert", "v"], reference["support_event_ids"])
        self.assertEqual("release", reference["action"])
        bad = {**reference, "support_event_ids": sorted(reference["support_event_ids"] + ["n"])}
        self.assertFalse(evaluation.evaluate_simulated_proposal(trace, bad)["proposal_valid"])

    def test_failure_inclusive_denominators_and_null_empty_categories(self):
        release = self.base("success")
        hold = self.base("hold")
        missing = self.base("missing")
        hidden = deepcopy(self.traces[1])
        duplicate = deepcopy(self.traces[6])
        rows = [evaluation.evaluate_simulated_proposal(release, self.release(release)),
                evaluation.evaluate_simulated_proposal(hold, self.hold(hold)),
                evaluation.evaluate_simulated_proposal(missing, None),
                evaluation.evaluate_simulated_proposal(hidden, self.release(hidden)),
                evaluation.evaluate_simulated_proposal(duplicate, self.release(duplicate))]
        summary = evaluation.aggregate_metrics(rows)
        self.assertEqual({"numerator": 1, "denominator": 3, "value": 1 / 3}, summary["metrics"]["valid_timely_release"])
        self.assertEqual(2, summary["metrics"]["missed_world_opportunities"]["numerator"])
        self.assertEqual(1, summary["counts"]["failed_attempts"])
        self.assertEqual(5, summary["metrics"]["valid_output_completion"]["denominator"])
        self.assertEqual(4, summary["metrics"]["valid_output_completion"]["numerator"])
        self.assertEqual(1, summary["metrics"]["unauthorized_release_proposals_forbidden"]["denominator"])
        self.assertEqual(1, summary["metrics"]["duplicate_release_proposals_attempts"]["denominator"])
        self.assertEqual(4, summary["counts"]["ordinary_attempts"])
        empty = evaluation.aggregate_metrics([])
        self.assertTrue(all(metric == {"numerator": 0, "denominator": 0, "value": None} for metric in empty["metrics"].values()))

    def test_aggregate_refuses_duplicate_cases_and_malformed_or_inconsistent_rows(self):
        trace = self.base()
        row = evaluation.evaluate_simulated_proposal(trace, self.release(trace))
        with self.assertRaisesRegex(ValueError, "Duplicate case"):
            evaluation.aggregate_metrics([row, deepcopy(row)])
        mutations = []
        item = deepcopy(row); item.pop("proposal_error"); mutations.append(item)
        item = deepcopy(row); item["facts"]["world_opportunity"] = 1; mutations.append(item)
        item = deepcopy(row); item["metric_flags"]["valid_timely_release"] = 0; mutations.append(item)
        item = deepcopy(row); item["effect_receipt"]["new_effects"] = True; mutations.append(item)
        item = deepcopy(row); item["artifact_outcome"] = {}; mutations.append(item)
        for item in mutations:
            with self.assertRaises(ValueError):
                evaluation.aggregate_metrics([item])

    def test_bounds_invalid_fixtures_and_no_api_io_or_candidate_import(self):
        tree = ast.parse(Path(evaluation.__file__).read_bytes())
        imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imported += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        self.assertFalse(any("decision_views" in name or "decision_policy" in name for name in imported))
        trace = self.base()
        proposal = self.release(trace)
        before = deepcopy(trace)
        with patch("builtins.open", side_effect=AssertionError("API attempted file access")):
            row = evaluation.evaluate_simulated_proposal(trace, proposal)
            evaluation.aggregate_metrics([row])
        self.assertEqual(before, trace)
        duplicate = self.base(); duplicate["events"].append(deepcopy(duplicate["events"][0]))
        invalid_time = self.base(); invalid_time["cutoff"] = "2020-01-01T00:10:00+00:00"
        huge = self.base(); huge["events"] *= 6
        boolean_amount = self.base(); boolean_amount["task"]["amount"] = True
        for invalid in (duplicate, invalid_time, huge, boolean_amount):
            with self.assertRaises(ValueError):
                evaluation.evaluate_simulated_proposal(invalid, proposal)
        with self.assertRaises(ValueError):
            evaluation.evaluate_simulated_proposal(trace, proposal, release_key="0" * 64)
        with self.assertRaises(ValueError):
            evaluation.evaluate_simulated_proposal(trace, proposal, prior_effect_keys=["0" * 64] * 33)


if __name__ == "__main__":
    unittest.main()
