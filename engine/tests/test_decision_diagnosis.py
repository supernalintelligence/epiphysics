"""Owned C8-shaped ledger controls; no private cohort, generator or worker runs.

The 24 repeated exposed cases exercise artifact/ledger transport, not research.
Fixture construction may normalize/decode synthetic data and use the independent
reference evaluator; preparation/replay/diagnosis must never execute a candidate.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import decision_assessment as assessment
from epiphysics import decision_diagnosis as diagnosis
from epiphysics import decision_evaluation as evaluation
from epiphysics.store import Ledger
import test_decision_assessment as fixtures
from test_decision_assessment import digest, raw, synthetic_evidence, write_fresh_study


FORBIDDEN_CALLS = {"build_decision_view", "decide_release_hold", "_candidate", "_run_candidate",
                   "run_development", "run_fresh_comparison", "generate", "build_case"}


@contextmanager
def calls_named(names):
    """Observe execution without replacing source-guarded functions."""
    seen = []
    previous = sys.getprofile()
    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_name in names:
            seen.append(frame.f_code.co_name)
    sys.setprofile(profile)
    try:
        yield seen
    finally:
        sys.setprofile(previous)


def identity(event):
    return {"event_id": event["id"], "event_hash": event["hash"]}


def make_study(directory, *, cohort=None, report=None, historical_transport=False):
    """Return an open temporary ledger, accepted C8 evidence and a C9 request.

    Caller owns closing result['ledger']. All input files are under directory,
    except read-only checked-in code/contracts used by the existing C8 fixture.
    No registered comparison, caller, generator or candidate is invoked.
    """
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    historical = directory / "historical-c8"
    historical.mkdir()
    if cohort is None and report is None:
        cohort, report = synthetic_evidence(fresh=True)
    elif cohort is None or report is None:
        raise ValueError("Provide both owned cohort and report")
    cohort, report = deepcopy(cohort), deepcopy(report)
    c8_path = write_fresh_study(historical, cohort, report)
    accepted = assessment.prepare_decision_study(c8_path)
    if historical_transport:
        historical_transport_copy(accepted)
    if set(accepted["artifacts"]) != set(diagnosis.C8_LIMITS) or len(accepted["artifacts"]) != 21:
        raise ValueError("Fixture must retain the exact original 21 C8 inputs")
    ledger = Ledger(directory / "ledger")
    try:
        observations = {}
        for role, content in accepted["artifacts"].items():
            full_role = "decision-input:" + role
            event = ledger.capture("improvement-input:" + full_role, content,
                event_id="improvement:owned-c8:input:" + full_role)
            observations[full_role] = event["id"]
        manifest = {"decision-input:" + role: value for role, value in accepted["manifest"].items()}
        assessment_identity = {"input_manifest": manifest,
            "decision_assessment_hash": accepted["report"]["assessment_identity"]["hash"]}
        assessment_identity["hash"] = digest(raw(assessment_identity))
        step = {"id": "owned-c8:next", "action": "investigate_decision_information_limits",
                "state": "queued", "scale_change_allowed": False, "live_effects_allowed": False}
        origin = ledger.append("improvement_completed", {"run_key": "owned-c8", "result": "assessed",
            "request": {"manifest": manifest, "after_step": "owned-c7:next"},
            "input_observations": observations, "assessment_identity": assessment_identity,
            "report": {"decision_pilot": deepcopy(accepted["report"])}, "next_step": step},
            "improvement:owned-c8:complete")
        contract_path = directory / "information-contract.json"
        contract_path.write_bytes(raw(diagnosis.CONTRACT))
        request = {"schema_version": 1, "study_id": "owned-information-diagnosis", "phase": diagnosis.PHASE,
            "origin": {"step_id": step["id"]}, "ledger_path": str(ledger.root),
            "evidence_origin": identity(origin), "queue_parent": identity(origin),
            "paths": {"contract": str(contract_path)}, "supplemental_evidence": {}}
        request_path = directory / "diagnosis-request.json"
        request_path.write_bytes(raw(request))
        return {"ledger": ledger, "request_path": request_path, "request": request,
            "origin": origin, "queue_parent": origin, "cohort": cohort, "report": report,
            "accepted_report": accepted["report"], "artifacts": accepted["artifacts"],
            "observations": observations, "c8_directory": historical, "contract_path": contract_path}
    except BaseException:
        ledger.close()
        raise


def historical_transport_copy(accepted):
    """Simulate a prior helper/controller revision; rebind the entire receipt chain.

    These two historical sources differ only by an inert comment. Candidate,
    decoder, policy and evaluator bytes and all measured outputs stay fixed.
    """
    artifacts = accepted["artifacts"]
    registration = json.loads(artifacts["registration"])
    for name in ("decision_assessment.py", "improvement.py"):
        role = "code:epiphysics." + name.removesuffix(".py")
        artifacts[role] += b"\n# owned historical transport revision\n"
        registration["source_hashes"][name] = digest(artifacts[role])
    artifacts["registration"] = raw(registration)
    custody = json.loads(artifacts["custody"])
    custody["registration_sha256"] = digest(artifacts["registration"])
    artifacts["custody"] = raw(custody)
    claim = json.loads(artifacts["claim"])
    claim.update(registration_sha256=digest(artifacts["registration"]), custody_sha256=digest(artifacts["custody"]))
    artifacts["claim"] = raw(claim)
    receipt = json.loads(artifacts["caller_receipt"])
    receipt.update(registration_sha256=digest(artifacts["registration"]), custody_sha256=digest(artifacts["custody"]),
                   claim_sha256=digest(artifacts["claim"]))
    artifacts["caller_receipt"] = raw(receipt)
    accepted["manifest"] = {role: digest(content) for role, content in artifacts.items()}
    accepted["report"]["assessment_identity"]["hash"] = digest(raw(accepted["manifest"]))
    for role in accepted["report"]["input_hashes"]:
        accepted["report"]["input_hashes"][role] = accepted["manifest"][role]
    accepted["report"]["registration"]["sha256"] = accepted["manifest"]["registration"]


def append_failed_attempt(study, *, capture_request=True, claimed_step=None):
    """Append an owned claim/failure chain; preserve immutable C8 origin.

    This is ledger-fixture construction, not controller execution. Root's
    integration test separately exercises the real controller failure path.
    """
    ledger = study["ledger"]
    previous = deepcopy(study["request"])
    previous_raw = raw(previous)
    run_key = "owned-c9-failure"
    dispatch_request = {"manifest": {"decision-input:request": digest(previous_raw)},
                        "after_step": previous["origin"]["step_id"]}
    claim = ledger.append("improvement_started", {"run_key": run_key, "request": dispatch_request,
        "claimed_step": deepcopy(claimed_step if claimed_step is not None else study["queue_parent"]["body"]["next_step"])},
        "improvement:" + run_key + ":started")
    if capture_request:
        ledger.capture("improvement-input:decision-input:request", previous_raw,
            event_id="improvement:" + run_key + ":input:decision-input:request")
    failure = ledger.append("improvement_failed", {"run_key": run_key, "result": "failed",
        "request": dispatch_request, "error": {"type": "OwnedFailure", "message": "Owned failure transport control"},
        "next_step": {"id": run_key + ":next", "state": "queued", "action": "diagnose_failed_assessment",
                      "scale_change_allowed": False, "live_effects_allowed": False}},
        "improvement:" + run_key + ":failed")
    current = deepcopy(previous)
    current.update(origin={"step_id": failure["body"]["next_step"]["id"]}, queue_parent=identity(failure))
    study.update(request=current, queue_parent=failure, failure_claim=claim, failure_request=previous)
    study["request_path"].write_bytes(raw(current))
    return failure


def quality_evidence():
    """Three outcome-only variations, keeping all public candidate inputs fixed."""
    cohort, report = synthetic_evidence(fresh=True)
    cohort["traces"][0]["later_outcome"]["artifact_valid"] = False
    cohort["traces"][1]["later_outcome"]["completed_at"] = "2020-01-01T00:11:00Z"
    cohort["traces"][2]["later_outcome"]["artifact_sha256"] = "0" * 64
    return reconcile_owned_outcomes(cohort, report)


def reconcile_owned_outcomes(cohort, report):
    """Refresh only owned evaluator evidence after changing private outcomes."""
    report["cohort_hash"] = digest(raw(cohort))
    for arm in report["arms"]:
        evaluated = []
        for trace, row in zip(cohort["traces"], arm["rows"]):
            outcome = evaluation.evaluate_simulated_proposal(trace, row["proposal"])
            row.update(deepcopy(outcome))
            evaluated.append(outcome)
        arm["summary"] = evaluation.aggregate_metrics(evaluated)
        arm["strata"] = {name: evaluation.aggregate_metrics([row for row in evaluated if row["mechanism"] == name])
                         for name in sorted(diagnosis.ALLOCATION)}
    return cohort, report


class DecisionDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def study(self, **kwargs):
        study = make_study(self.directory, **kwargs)
        self.addCleanup(study["ledger"].close)
        return study

    def test_preparation_checks_metadata_without_diagnosing_or_candidate_execution(self):
        study = self.study()
        before = len(study["ledger"].events())
        with calls_named(FORBIDDEN_CALLS | {"_diagnose"}) as seen:
            prepared = diagnosis.prepare_diagnosis(study["request_path"])
            diagnosis.check_prepared_diagnosis(prepared)
        self.assertEqual(seen, [])
        self.assertEqual(prepared["report"]["status"], "prepared")
        self.assertNotIn("next_step", prepared["report"])
        self.assertNotIn("diagnosis", prepared["report"])
        self.assertEqual(len(study["ledger"].events()), before)
        self.assertEqual({role.removeprefix("c8:") for role in prepared["artifacts"] if role.startswith("c8:")},
                         set(diagnosis.C8_LIMITS))
        self.assertEqual(prepared["artifacts"]["c8:journal"].count(b"\n"), 194)

    def test_full_owned96_row_reconciliation_uses_case_scoped_verification_identity(self):
        study = self.study()
        prepared = diagnosis.prepare_diagnosis(study["request_path"])
        untouched = deepcopy(prepared)
        with calls_named(FORBIDDEN_CALLS) as seen:
            result = diagnosis.assess_prepared_diagnosis(prepared)
        self.assertEqual(seen, [])
        self.assertEqual(prepared, untouched)
        repeat = diagnosis.assess_prepared_diagnosis(prepared)
        self.assertEqual(result["report"], repeat["report"])
        self.assertEqual(result["artifacts"]["diagnostic_table"], repeat["artifacts"]["diagnostic_table"])
        self.assertLessEqual(len(result["artifacts"]["assessment_report"]) + len(result["artifacts"]["diagnostic_table"]),
                             1024 * 1024)
        checked = result["report"]
        table = json.loads(result["artifacts"]["diagnostic_table"])
        self.assertEqual(len(table["attempts"]), 96)
        self.assertEqual(len({(row["case_id"], row["arm"], row["budget_bytes"]) for row in table["attempts"]}), 96)
        self.assertEqual(checked["counts"], {"cases": 24, "arms": 4, "attempts": 96, "journal_records": 194})
        self.assertTrue(all(checked["checks"].values()))
        self.assertEqual(checked["next_step"]["action"], "prepare_dated_evidence_quality_protocol")
        self.assertEqual(checked["resources"]["decision_candidate_executions"], 0)
        self.assertEqual(checked["diagnosis"]["paired"]["counts"], {"both": 24, "flat_only": 0, "relational_only": 0, "neither": 0})
        verification = checked["diagnosis"]["verification"]
        self.assertEqual(verification["adjudicated_claims"], 24)
        self.assertEqual(verification["cases_with_adjudicated_claims"], 24)
        self.assertEqual(len({tuple(row["identity"]) for row in table["verification_claims"]}), 24)
        # Repeated event IDs/release keys belong to independent case scopes.
        self.assertEqual(len({row["identity"][2] for row in table["verification_claims"]}), 1)
        self.assertEqual(len({tuple(row["independent_effect_scope"]) for row in table["attempts"]}), 24)
        for arm in checked["arms"]:
            quality = arm["diagnosis"]["accepted_not_ready_or_invalid_effects"]
            self.assertEqual(quality["all_cases"], {"numerator": 0, "denominator": 24, "value": 0})
            self.assertEqual(quality["not_ready_or_invalid_cases"], {"numerator": 0, "denominator": 0, "value": None})
            self.assertEqual(quality["accepted_effects"]["denominator"], 24)

    def test_quality_denominators_separate_invalid_late_and_unbound_outcomes(self):
        cohort, report = quality_evidence()
        study = self.study(cohort=cohort, report=report)
        result = diagnosis.assess_prepared_diagnosis(diagnosis.prepare_diagnosis(study["request_path"]))
        checked = result["report"]
        verification = checked["diagnosis"]["verification"]
        self.assertEqual(verification["eligible_operative_bound_verified_claims"], 24)
        self.assertEqual(verification["adjudicated_claims"], 23)
        self.assertEqual(verification["unknown_outcome_claims"], 1)
        self.assertEqual(verification["verdict_vs_stipulated_validity_disagreement"],
                         {"numerator": 1, "denominator": 23, "value": 1 / 23})
        self.assertEqual(verification["positive_claim_invalid_artifact"]["numerator"], 1)
        for arm in checked["arms"]:
            quality = arm["diagnosis"]["accepted_not_ready_or_invalid_effects"]
            self.assertEqual(quality["all_cases"], {"numerator": 3, "denominator": 24, "value": 3 / 24})
            self.assertEqual(quality["not_ready_or_invalid_cases"], {"numerator": 3, "denominator": 3, "value": 1})
            self.assertEqual(quality["accepted_effects"], {"numerator": 3, "denominator": 24, "value": 3 / 24})
        self.assertEqual(checked["next_step"]["action"], "review_unresolved_decision_evidence")
        self.assertGreater(checked["diagnosis"]["unresolved_attribution_rows"], 0)

    def test_multiple_claims_and_repeated_unknowns_have_distinct_claim_and_case_denominators(self):
        original = json.loads((fixtures.EXAMPLES / "development-traces.json").read_bytes())["traces"][0]
        additional = deepcopy(next(event for event in original["events"] if event["kind"] == "verification"))
        additional["event_id"] = "owned-additional-verification"
        # Verification v1 forbids reference values; distinct records do not
        # establish that either supersedes/revises the other.
        original["events"].append(additional)
        exposed = self.directory / "owned-exposed-source"
        exposed.mkdir()
        (exposed / "development-traces.json").write_bytes(raw({"traces": [original]}))
        # Patch only the test fixture's input location. No implementation or
        # registered cohort changes; repeat one exposed scenario for transport.
        with patch.object(fixtures, "EXAMPLES", exposed):
            cohort, report = synthetic_evidence(fresh=True)
        for trace in cohort["traces"][:2]:
            trace["later_outcome"]["artifact_sha256"] = "0" * 64
        cohort["traces"][2]["later_outcome"]["artifact_valid"] = False
        reconcile_owned_outcomes(cohort, report)
        study = self.study(cohort=cohort, report=report)
        result = diagnosis.assess_prepared_diagnosis(diagnosis.prepare_diagnosis(study["request_path"]))
        verification = result["report"]["diagnosis"]["verification"]
        self.assertEqual(verification["eligible_operative_bound_verified_claims"], 48)
        self.assertEqual(verification["adjudicated_claims"], 44)
        self.assertEqual(verification["cases_with_adjudicated_claims"], 22)
        self.assertEqual(verification["unknown_outcome_claims"], 4)
        self.assertEqual(verification["verdict_vs_stipulated_validity_disagreement"],
                         {"numerator": 2, "denominator": 44, "value": 2 / 44})
        detail = json.loads(result["artifacts"]["diagnostic_table"])
        self.assertEqual(len({tuple(claim["identity"]) for claim in detail["verification_claims"]}), 48)
        claims = detail["verification_claims"]
        self.assertEqual(len({claim["identity"][2] for claim in claims}), 2)
        self.assertTrue(all(claim["reference"] is None for claim in claims))
        self.assertTrue(all("Not established" in claim["revision_semantics"] for claim in claims))
        self.assertEqual(result["report"]["diagnosis"]["unresolved_attribution_rows"], 8)
        self.assertEqual(result["report"]["next_step"]["action"], "review_unresolved_decision_evidence")
        self.assertFalse(result["report"]["next_step"]["scale_change_allowed"])

    def test_checked_continuation_keeps_original_c8_and_binds_current_c9_identity(self):
        cohort, report = quality_evidence()
        study = self.study(cohort=cohort, report=report)
        first = diagnosis.prepare_diagnosis(study["request_path"])
        checked = diagnosis.assess_prepared_diagnosis(first)["report"]
        manifest = {"decision-input:" + role: value for role, value in first["manifest"].items()}
        accepted_identity = {"input_manifest": manifest, "decision_assessment_hash": checked["assessment_identity"]["hash"]}
        accepted_identity["hash"] = digest(raw(accepted_identity))
        parent = study["ledger"].append("improvement_completed", {"run_key": "owned-first-diagnosis", "result": "assessed",
            "request": {"manifest": manifest}, "assessment_identity": accepted_identity,
            "report": {"decision_pilot": checked}, "next_step": {**checked["next_step"],
                "id": "owned-first-diagnosis:next", "state": "queued"}}, "owned-first-diagnosis:complete")
        study["request"].update(origin={"step_id": parent["body"]["next_step"]["id"]}, queue_parent=identity(parent))
        study["request_path"].write_bytes(raw(study["request"]))
        prepared = diagnosis.prepare_diagnosis(study["request_path"])
        self.assertEqual(prepared["report"]["ancestry"]["mode"], "checked_continuation")
        self.assertEqual(prepared["report"]["ancestry"]["prior_diagnostic_identity"], checked["assessment_identity"])
        self.assertEqual(prepared["report"]["evidence_origin"]["event_id"], study["origin"]["id"])
        self.assertEqual(prepared["report"]["queue_parent"], identity(parent))
        diagnosis.validate_lineage(prepared, study["ledger"].events(), parent["body"]["next_step"]["id"])

        second = diagnosis.assess_prepared_diagnosis(prepared)["report"]
        self.assertEqual(second["next_step"]["action"], "prepare_dated_evidence_quality_protocol")
        self.assertEqual(second["diagnosis"]["unresolved"], checked["diagnosis"]["unresolved"])
        self.assertEqual(second["diagnosis"]["attribution_coverage"], checked["diagnosis"]["attribution_coverage"])
        self.assertTrue(second["diagnosis"]["gap_review"]["unchanged_verified_gap_set"])
        self.assertIn("Unknowns remain unknown", second["diagnosis"]["gap_review"]["resolution"])
        self.assertFalse(second["next_step"]["live_effects_allowed"])
        # Predicate controls use the real prepared ancestry and identity/reason
        # rows. They do not pretend altered artifacts passed metadata binding.
        changed = deepcopy(prepared)
        prior = json.loads(changed["artifacts"]["queue_parent"])
        prior["body"]["report"]["decision_pilot"]["diagnosis"]["unresolved"][0]["reasons"] = ["different owned gap"]
        changed["artifacts"]["queue_parent"] = raw(prior)
        gap = diagnosis._gap_review(changed, second["diagnosis"]["unresolved"])
        self.assertFalse(gap["unchanged_verified_gap_set"])
        self.assertEqual(diagnosis._next_step(second["checks"], second["diagnosis"]["unresolved"], gap)["action"],
                         "review_unresolved_decision_evidence")
        prior["body"]["report"]["decision_pilot"]["diagnosis"]["unresolved"] = []
        changed["artifacts"]["queue_parent"] = raw(prior)
        with self.assertRaisesRegex(ValueError, "lacks explicit unresolved evidence"):
            diagnosis._gap_review(changed, second["diagnosis"]["unresolved"])

    def test_prior_checked_completion_cannot_substitute_or_omit_immutable_c8_roles(self):
        cohort, report = quality_evidence()
        study = self.study(cohort=cohort, report=report)
        first = diagnosis.prepare_diagnosis(study["request_path"])
        checked = diagnosis.assess_prepared_diagnosis(first)["report"]
        original_roles = {role.removeprefix("c8:"): value for role, value in first["manifest"].items()
                          if role.startswith("c8:")}
        self.assertEqual(set(original_roles), set(diagnosis.C8_LIMITS))
        self.assertEqual(len(original_roles), 21)
        self.assertEqual(original_roles, checked["evidence_origin"]["input_manifest"])

        def append_parent(label, declared, prior_report):
            # All ordinary input, study and controller identities are genuine
            # hashes of the altered declarations. Ledger.append supplies a
            # valid event hash/chain, avoiding an earlier checksum rejection.
            manifest = {"decision-input:" + role: value for role, value in declared.items()}
            prior_report["assessment_identity"]["hash"] = digest(raw(declared))
            accepted_identity = {"input_manifest": manifest,
                "decision_assessment_hash": prior_report["assessment_identity"]["hash"]}
            accepted_identity["hash"] = digest(raw(accepted_identity))
            parent = study["ledger"].append("improvement_completed", {
                "run_key": label, "result": "assessed", "request": {"manifest": manifest},
                "assessment_identity": accepted_identity, "report": {"decision_pilot": prior_report},
                "next_step": {**prior_report["next_step"], "id": label + ":next", "state": "queued"}},
                label + ":complete")
            study["request"].update(origin={"step_id": label + ":next"}, queue_parent=identity(parent))
            study["request_path"].write_bytes(raw(study["request"]))
            self.assertTrue(study["ledger"].verify()["valid"])
            return parent

        # An unaltered accepted review remains a valid continuation.
        append_parent("owned-valid-prior", deepcopy(first["manifest"]), deepcopy(checked))
        valid = diagnosis.prepare_diagnosis(study["request_path"])
        self.assertEqual(valid["report"]["ancestry"]["mode"], "checked_continuation")
        for mode, original_role in (("substituted", "cohort"), ("omitted", "cohort"),
                                    ("substituted", "code:epiphysics.decision_policy"),
                                    ("omitted", "code:epiphysics.decision_policy")):
            with self.subTest(mode=mode, role=original_role):
                declared, prior_report = deepcopy(first["manifest"]), deepcopy(checked)
                role = "c8:" + original_role
                if mode == "substituted":
                    declared[role] = digest(b"owned alternate historical role")
                else:
                    del declared[role]
                # Align report metadata with the altered input manifest. Only
                # immutable C8 ancestry should reject this coherent forgery.
                prior_report["input_hashes"] = {key: value for key, value in declared.items()
                                                if not key.startswith("code:")}
                label = "owned-prior-" + mode + "-" + ("code" if original_role.startswith("code:") else "data")
                parent = append_parent(label, declared, prior_report)
                before = len(study["ledger"].events())
                with self.assertRaisesRegex(diagnosis.PreparationError,
                        "Prior diagnostic accepted C8 ancestry") as failure:
                    diagnosis.prepare_diagnosis(study["request_path"])
                self.assertEqual(json.loads(failure.exception.artifacts["queue_parent"]), parent)
                self.assertEqual(len(study["ledger"].events()), before)

        # A report-only mapping alteration must also be rejected, even though
        # the original input/study/controller/event identities all remain valid.
        for field, role, message in (("input_hashes", "c8:cohort", "Prior diagnostic report/input mapping"),
                                    ("source_hashes", "decision_diagnosis.py", "Prior diagnostic source mapping")):
            with self.subTest(report_field=field):
                prior_report = deepcopy(checked)
                prior_report[field][role] = digest(b"owned altered report-only mapping")
                append_parent("owned-prior-" + field, deepcopy(first["manifest"]), prior_report)
                with self.assertRaisesRegex(diagnosis.PreparationError, message):
                    diagnosis.prepare_diagnosis(study["request_path"])

    def test_assembled_output_checks_refuse_identity_reference_date_and_metric_mutations(self):
        study = self.study()
        result = diagnosis.assess_prepared_diagnosis(diagnosis.prepare_diagnosis(study["request_path"]))
        detail = json.loads(result["artifacts"]["diagnostic_table"])
        original = (detail["attempts"], detail["cases"], result["report"]["arms"])
        baseline_checks = diagnosis._output_checks(*original, study["report"], study["cohort"])
        self.assertTrue(all(baseline_checks.values()))
        mutations = {
            "repeated_case_identity": lambda table, cases, arms: table[1].update(case_id=table[0]["case_id"]),
            "changed_reference": lambda table, cases, arms: table[0]["reference_proposal"].update(reason="unbound reason"),
            "invented_capture_time": lambda table, cases, arms: cases[0]["events"][0].update(captured_at="2020-01-01T00:10:00Z"),
            "changed_numerator": lambda table, cases, arms: arms[0]["summary"]["metrics"]["valid_timely_release"].update(numerator=23),
            "changed_denominator": lambda table, cases, arms: arms[0]["summary"]["metrics"]["valid_timely_release"].update(denominator=999),
            "changed_value": lambda table, cases, arms: arms[0]["summary"]["metrics"]["valid_timely_release"].update(value=0.5),
            "changed_arm_identity": lambda table, cases, arms: arms[0].update(recipe="unregistered-arm"),
        }
        for label, mutate in mutations.items():
            with self.subTest(mutation=label):
                table, cases, arms = deepcopy(original)
                mutate(table, cases, arms)
                checks = diagnosis._output_checks(table, cases, arms, study["report"], study["cohort"])
                self.assertFalse(all(checks.values()), label)
                next_step = diagnosis._next_step(checks, [])
                self.assertEqual(next_step["action"], "repair_decision_information_diagnosis")
                self.assertFalse(next_step["scale_change_allowed"])
                self.assertFalse(next_step["live_effects_allowed"])

    def test_replay_uses_frozen_prefix_after_later_events_without_recomputation(self):
        study = self.study()
        prepared = diagnosis.prepare_diagnosis(study["request_path"])
        study["ledger"].capture("owned-later-source", b"new unrelated evidence")
        with calls_named(FORBIDDEN_CALLS | {"_diagnose"}) as seen:
            replay = diagnosis.prepare_diagnosis(study["request_path"])
            diagnosis.check_prepared_diagnosis(replay)
            diagnosis.validate_lineage(replay, study["ledger"].events(), study["request"]["origin"]["step_id"])
        self.assertEqual(seen, [])
        self.assertEqual(replay, prepared)
        study["ledger"].append("improvement_completed", {"run_key": "later-transition", "next_step": {
            "id": "later-transition:next", "state": "queued", "action": "prepare_dated_evidence_quality_protocol"}}, "later-transition")
        with calls_named({"_diagnose"}) as seen:
            self.assertEqual(diagnosis.prepare_diagnosis(study["request_path"]), prepared)
            with self.assertRaisesRegex(ValueError, "Stale or unrelated"):
                diagnosis.validate_lineage(prepared, study["ledger"].events(), study["request"]["origin"]["step_id"])
        self.assertEqual(seen, [])

    def test_original_c8_paths_can_be_deleted_before_preparation_and_assessment(self):
        study = self.study()
        shutil.rmtree(study["c8_directory"])
        with calls_named(FORBIDDEN_CALLS) as seen:
            prepared = diagnosis.prepare_diagnosis(study["request_path"])
            result = diagnosis.assess_prepared_diagnosis(prepared)
        self.assertEqual(seen, [])
        self.assertEqual(result["report"]["status"], "checked")
        self.assertEqual(len(json.loads(result["artifacts"]["diagnostic_table"])["attempts"]), 96)

    def test_historical_helper_and_controller_bytes_need_not_equal_current_code(self):
        study = self.study(historical_transport=True)
        shutil.rmtree(study["c8_directory"])
        prepared = diagnosis.prepare_diagnosis(study["request_path"])
        for name in ("decision_assessment.py", "improvement.py"):
            retained = prepared["artifacts"]["c8:code:epiphysics." + name.removesuffix(".py")]
            current = (Path(assessment.__file__).parent / name).read_bytes()
            self.assertNotEqual(retained, current)
            self.assertEqual(retained, current + b"\n# owned historical transport revision\n")
        checked = diagnosis.assess_prepared_diagnosis(prepared)["report"]
        self.assertEqual(checked["status"], "checked")
        self.assertEqual(checked["next_step"]["action"], "prepare_dated_evidence_quality_protocol")

    def test_failed_claim_ancestry_preserves_c8_origin_and_advances_only_parent(self):
        study = self.study()
        original_identity = identity(study["origin"])
        failure = append_failed_attempt(study)
        with calls_named(FORBIDDEN_CALLS) as seen:
            prepared = diagnosis.prepare_diagnosis(study["request_path"])
            diagnosis.validate_lineage(prepared, study["ledger"].events(), study["request"]["origin"]["step_id"])
            checked = diagnosis.assess_prepared_diagnosis(prepared)["report"]
        self.assertEqual(seen, [])
        self.assertEqual(study["request"]["evidence_origin"], original_identity)
        self.assertEqual(prepared["report"]["queue_parent"], identity(failure))
        self.assertNotEqual(prepared["report"]["evidence_origin"]["event_id"], failure["id"])
        self.assertEqual(prepared["report"]["ancestry"]["mode"], "failed_attempt_continuation")
        self.assertEqual(prepared["report"]["ancestry"]["semantic_parent_id"], study["origin"]["id"])
        self.assertEqual(checked["next_step"]["action"], "prepare_dated_evidence_quality_protocol")
        self.assertTrue(study["ledger"].verify()["valid"])

    def test_failure_without_captured_request_refuses_without_fabricating_ancestry(self):
        study = self.study()
        append_failed_attempt(study, capture_request=False)
        before = len(study["ledger"].events())
        with self.assertRaisesRegex(diagnosis.PreparationError, "Missing captured failed C9 request") as error:
            diagnosis.prepare_diagnosis(study["request_path"])
        self.assertIn("queue_parent", error.exception.artifacts)
        self.assertNotIn("failure_request", error.exception.artifacts)
        self.assertEqual(len(study["ledger"].events()), before)

    def test_failure_claim_must_name_the_actual_semantic_step(self):
        study = self.study()
        wrong_step = deepcopy(study["origin"]["body"]["next_step"])
        wrong_step["id"] = "unrelated:next"
        append_failed_attempt(study, claimed_step=wrong_step)
        with self.assertRaisesRegex(diagnosis.PreparationError, "Original claimed semantic step"):
            diagnosis.prepare_diagnosis(study["request_path"])

    def test_forged_origin_hash_is_refused_without_a_new_event(self):
        study = self.study()
        study["request"]["evidence_origin"]["event_hash"] = "0" * 64
        study["request_path"].write_bytes(raw(study["request"]))
        before = len(study["ledger"].events())
        with self.assertRaisesRegex(diagnosis.PreparationError, "Historical event identity"):
            diagnosis.prepare_diagnosis(study["request_path"])
        self.assertEqual(len(study["ledger"].events()), before)

    def test_changed_owned_source_copy_is_refused_before_preparation(self):
        study = self.study()
        original_path, source, code = diagnosis._SELF
        copied = self.directory / "owned-diagnosis-source.py"
        copied.write_bytes(source + b"\n# owned changed source control\n")
        # Redirect only the source guard's path to an owned copy; never edit a
        # shared implementation file while another worker may import it.
        with patch.object(diagnosis, "_SELF", (copied, source, code)):
            with self.assertRaisesRegex(diagnosis.PreparationError, "Diagnosis source changed"):
                diagnosis.prepare_diagnosis(study["request_path"])
        self.assertEqual(Path(original_path).read_bytes(), source)


class DiagnosisAttributionTests(unittest.TestCase):
    """Wrong evidence must not turn an explicit attribution gap into a fact."""
    def test_case_timing_separates_cutoff_equality_future_effect_and_later_outcome(self):
        trace = json.loads((fixtures.EXAMPLES / "development-traces.json").read_bytes())["traces"][0]
        untouched_task = deepcopy(trace["task"])
        verification = next(event for event in trace["events"] if event["kind"] == "verification")
        verification.update(observed_at=trace["cutoff"], effective_at=trace["decision_at"])
        future = deepcopy(verification)
        future.update(event_id="owned-future-verification", effective_at="2020-01-01T00:10:01Z")
        trace["events"].append(future)
        dated, claims, quality = diagnosis._case_evidence(trace, "a" * 64)
        by_id = {event["identity"][2]: event for event in dated}
        at_cutoff, future_effective = by_id[verification["event_id"]], by_id[future["event_id"]]
        self.assertTrue(at_cutoff["visible_at_cutoff"])
        self.assertTrue(at_cutoff["effective_at_decision"])
        self.assertTrue(at_cutoff["observer_operative"])
        self.assertTrue(future_effective["visible_at_cutoff"])
        self.assertFalse(future_effective["effective_at_decision"])
        self.assertFalse(future_effective["observer_operative"])
        for event in (at_cutoff, future_effective):
            self.assertTrue(event["role_binding_matches"])
            self.assertTrue(event["artifact_digest_matches"])
            self.assertEqual(event["artifact_sha256"], untouched_task["artifact_sha256"])
            self.assertEqual((event["issuer"], event["subject"], event["object"]),
                             (untouched_task["requester"], untouched_task["requester"], untouched_task["artifact_id"]))
            self.assertIsNone(event["captured_at"])
        self.assertEqual([claim["identity"][2] for claim in claims], [verification["event_id"]])
        self.assertTrue(quality["artifact_binding_matches"])
        self.assertTrue(quality["completed_by_decision"])
        self.assertTrue(quality["stipulated_artifact_valid"])
        self.assertEqual(quality["outcome_revealed_at"], trace["later_outcome"]["revealed_at"])
        self.assertFalse(quality["outcome_available_at_decision"])
        self.assertEqual(trace["task"], untouched_task)

    def test_hidden_wrong_digest_verification_does_not_explain_visible_miss(self):
        row = {"facts": {}, "metric_flags": {"missed_observable_opportunities": 0, "missed_world_opportunities": 1,
            "unauthorized_release_proposals_all": 0, "duplicate_release_proposals_all": 0,
            "invalid_artifact_release_proposals": 0, "evidence_unjustified_release_proposals": 0},
            "reference_proposal": {"reason": "missing_verification"}}
        hidden = {"kind": "verification", "visible_at_cutoff": False, "effective_at_decision": True,
                  "role_binding_matches": True, "authentication": "verified", "verdict": "pass",
                  "artifact_digest_matches": False}
        result = diagnosis._attribution(row, {}, [hidden], [], True)
        self.assertEqual(result["supported_labels"], [])
        self.assertEqual(result["unresolved"], ["world_opportunity_without_full_visible_release:missing_verification"])
        hidden["artifact_digest_matches"] = True
        self.assertEqual(diagnosis._attribution(row, {}, [hidden], [], True)["supported_labels"],
                         ["verification_unavailable_at_cutoff"])

    def test_irrelevant_hidden_authority_event_does_not_explain_unsafe_proposal(self):
        row = {"facts": {"open_dispute_ids": [], "active_grant_ids": []},
            "metric_flags": {"missed_observable_opportunities": 0, "missed_world_opportunities": 0,
            "unauthorized_release_proposals_all": 1, "duplicate_release_proposals_all": 0,
            "invalid_artifact_release_proposals": 0, "evidence_unjustified_release_proposals": 0}}
        visible_grant = {"kind": "grant", "identity": ["cohort", "case", "actual-grant"],
            "visible_at_cutoff": True, "effective_at_decision": True, "observer_operative": True,
            "role_binding_matches": True, "authentication": "verified", "effective_at": "2020-01-01T00:01:00Z"}
        hidden = {"kind": "revoke", "identity": ["cohort", "case", "hidden-revoke"],
            "reference": "unrelated-grant", "visible_at_cutoff": False, "effective_at_decision": True,
            "observer_operative": False, "role_binding_matches": True, "authentication": "verified",
            "effective_at": "2020-01-01T00:02:00Z"}
        result = diagnosis._attribution(row, {}, [visible_grant, hidden], [], True)
        self.assertEqual(result["supported_labels"], [])
        self.assertEqual(result["unresolved"], ["authority_evidence_differs_across_cutoff"])
        hidden["reference"] = "actual-grant"
        self.assertEqual(diagnosis._attribution(row, {}, [visible_grant, hidden], [], True)["supported_labels"],
                         ["authority_evidence_differs_across_cutoff"])
        hidden["reference"] = None
        self.assertEqual(diagnosis._attribution(row, {}, [visible_grant, hidden], [], True)["supported_labels"],
                         ["authority_evidence_differs_across_cutoff"])
        hidden["effective_at"] = "2020-01-01T00:00:30Z"
        self.assertEqual(diagnosis._attribution(row, {}, [visible_grant, hidden], [], True)["supported_labels"], [])
        hidden["effective_at"] = "2020-01-01T00:02:00Z"
        row["facts"]["active_grant_ids"] = ["actual-grant"]
        self.assertEqual(diagnosis._attribution(row, {}, [visible_grant, hidden], [], True)["supported_labels"], [])


if __name__ == "__main__":
    unittest.main()
