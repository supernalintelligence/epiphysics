"""Owned retained-output controls; never run the registered development study."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import decision_assessment as assessment
from epiphysics import decision_evaluation as evaluation
from epiphysics import decision_views as views


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "control-exchange"
ACCOUNTING = "Child wall contains its stage times. Parent wall includes computation and attempt journaling through final source verification, excluding final report serialization/persistence. Do not add nested totals. Lossless arms are separate controls; retain caller wall time separately."


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def successor(checks):
    repair = not all(checks.values())
    return {"action": "repair_decision_pilot" if repair else "prepare_fresh_decision_comparison",
            "reason": "A conformance, execution or separation check failed" if repair else
                "Development wiring passed; freeze and review before generating one new 24-case exploratory batch",
            "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "exposed development measurements; no adoption claim"}


def synthetic_evidence(*, overflow=False, invalid_utf8=False, fresh=False):
    # Clone one exposed positive for transport checks. This is not a comparison
    # of the twelve registered mechanisms, and launches no worker or policy.
    original = json.loads((EXAMPLES / "development-traces.json").read_bytes())["traces"][0]
    traces = []
    mechanisms = [name for name, count in assessment.FRESH_ALLOCATION.items() for _ in range(count)] if fresh else ["retained transport control"] * 12
    for index, mechanism in enumerate(mechanisms):
        trace = deepcopy(original)
        trace["trace_id"] = "assessment-owned-" + str(index)
        trace["mechanism"] = mechanism
        traces.append(trace)
    cohort = {"cohort_id": "decision-pilot-fresh-v1" if fresh else "decision-pilot-development-v1", "contract_id": views.CONTRACT_ID,
              "trace_count": len(traces), "final_cohort_generated": fresh, "traces": traces}
    if fresh:
        cohort.update(schema_version=1, status="fresh_exploratory", allocation=deepcopy(assessment.FRESH_ALLOCATION))
    sources = {name: digest((Path(assessment.__file__).parent / name).read_bytes()) for name in assessment.SOURCE_NAMES}
    checks = {name: True for name in assessment.CHECK_FIELDS}
    failed = overflow or invalid_utf8
    if failed:
        checks.update(all_outputs_valid=False, fixed_policy_conformance=False, lossless_reference_parity=False)
    report = {"schema_version": 1, "contract_id": views.CONTRACT_ID, "cohort_id": cohort["cohort_id"],
        "cohort_hash": digest(raw(cohort)), "stage": "fresh_exploratory" if fresh else "exposed_development", "declared_case_count": len(traces),
        "source_hashes": sources, "checks": checks, "arms": [],
        "limits": {"program_seconds": 30, "normal_view_bytes": 2048, "lossless_view_bytes": 32768, "worker_output_bytes": 65536},
        "scope": "Owned synthetic fresh exploratory comparison only; retention and view systems compared together; no generalization or live authority claim" if fresh else
            "Owned synthetic development only; retention and view systems compared together; no generalization or live authority claim",
        "resources": {"parent_wall_seconds": 2.0 if fresh else 1.0, "model_calls": 0, "external_program_spend": 0,
            "agent_and_review_cost": None, "memory_bytes": None, "accounting": ACCOUNTING},
        "next_step": successor(checks)}
    if fresh:
        report["next_step"] = {"action": "repair_decision_pilot" if failed else "investigate_decision_information_limits",
            "reason": "A conformance, execution or separation check failed" if failed else
                "Fresh exploratory comparison did not meet the registered triage margin; retain the flat baseline and investigate information limits",
            "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "fresh exploratory measurements; research triage only; no adoption claim"}
    for recipe, budget in assessment.ARMS:
        rows, evaluated_rows = [], []
        for trace in traces:
            bundle = views.prepare_decision_input(trace["events"], trace["task"], trace["cutoff"], trace["decision_at"])
            view = None if failed else views.build_decision_view(bundle["header_bytes"], bundle["event_tape_bytes"], recipe=recipe, budget_bytes=budget)
            proposal = None if failed else evaluation.reference_decision(trace)
            stages = {"build_seconds": 0.001, "validate_decode_seconds": 0.001, "policy_seconds": 0.001}
            response = None if failed else {"view": view.decode(), "proposal": proposal, "input_hash": bundle["input_hash"],
                "source_hash": digest(bundle["event_tape_bytes"]), "complete": True, "timings": stages}
            stdout, stderr = (b"x" * 65537 if overflow else b"\xff" if invalid_utf8 else raw(response)), b""
            error = "worker_output_limit" if overflow else None
            receipt = {"error": error, "returncode": -9 if overflow else 0, "elapsed_seconds": 0.01,
                "request_bytes": len(raw({"header": bundle["header_bytes"].decode(), "tape": bundle["event_tape_bytes"].decode(), "recipe": recipe, "budget_bytes": budget}))}
            for label, value in (("stdout", stdout), ("stderr", stderr)):
                receipt.update({label + "_base64": base64.b64encode(value).decode(), label + "_sha256": digest(value), label + "_bytes": len(value)})
            evaluation_error = error
            if invalid_utf8:
                try:
                    json.loads(stdout)
                except UnicodeDecodeError as invalid:
                    evaluation_error = str(invalid).encode("utf-8", errors="replace")[:400].decode("utf-8", errors="replace")
            evaluated = evaluation.evaluate_simulated_proposal(trace, proposal, error=evaluation_error)
            evaluated_rows.append(evaluated)
            row = deepcopy(evaluated)
            row.update(arm=recipe, budget_bytes=budget, input_hash=bundle["input_hash"],
                source_hash=digest(bundle["event_tape_bytes"]), source_bytes=len(bundle["event_tape_bytes"]), header_bytes=len(bundle["header_bytes"]),
                view_hash=digest(view) if view else None, view_bytes=len(view) if view else None, view=view.decode() if view else None,
                provenance_valid=not failed, complete=True if not failed else None, worker_receipt=receipt,
                resources={"normalization_seconds": 0.001, "candidate_stages": stages if not failed else None,
                    "child_wall_seconds": 0.01, "parent_verification_seconds": 0.001, "model_calls": 0,
                    "external_program_spend": 0, "memory_bytes": None})
            rows.append(row)
        summary = evaluation.aggregate_metrics(evaluated_rows)
        report["arms"].append({"recipe": recipe, "budget_bytes": budget, "control": budget == 32768,
            "rows": rows, "summary": summary, "strata": {name: evaluation.aggregate_metrics([row for row in evaluated_rows if row["mechanism"] == name])
                for name in sorted(set(mechanisms))}})
    return cohort, report


def journal_for(cohort, report):
    entries = [{"kind": "declared_run", "cohort_hash": report["cohort_hash"], "source_hashes": report["source_hashes"],
        "arms": [list(arm) for arm in assessment.ARMS], "case_ids": [trace["trace_id"] for trace in cohort["traces"]],
        "scope": "fresh exploratory comparison; only root may invoke the registered run" if report["stage"] == "fresh_exploratory" else
            "exposed development; only root may invoke the registered run"}]
    for arm in report["arms"]:
        for row in arm["rows"]:
            entries.extend([{"kind": "worker_returned", "case_id": row["case_id"], "recipe": arm["recipe"],
                "budget_bytes": arm["budget_bytes"], "input_hash": row["input_hash"], "receipt": row["worker_receipt"]},
                {"kind": "attempt_evaluated", "row": row}])
    entries.append({"kind": "run_terminal", "checks": report["checks"], "next_step": report["next_step"]})
    return b"".join(raw(entry) + b"\n" for entry in entries)


def write_study(directory, cohort, report):
    directory = Path(directory)
    for role in ("decision_contract", "evaluation_contract"):
        (directory / (role + ".json")).write_bytes((EXAMPLES / (role.replace("_", "-") + ".json")).read_bytes())
    (directory / "cohort.json").write_bytes(raw(cohort))
    (directory / "report.json").write_bytes(raw(report))
    (directory / "journal.jsonl").write_bytes(journal_for(cohort, report))
    request = {"schema_version": 1, "study_id": "owned-assessment-control", "phase": "development",
        "origin": {"step_id": "owned-preparation:next"}, "paths": {role: role + ".json" for role in
            ("cohort", "report", "decision_contract", "evaluation_contract")}}
    request["paths"]["journal"] = "journal.jsonl"
    (directory / "request.json").write_bytes(raw(request))
    return directory / "request.json"


def write_fresh_study(directory, cohort, report):
    """Compose exposed owned receipts; never generate a cohort or run a worker."""
    directory = Path(directory)
    path = write_study(directory, cohort, report)
    request = json.loads(path.read_bytes())
    (directory / "journal.jsonl").rename(directory / "report.json.attempts.jsonl")
    request["paths"]["journal"] = "report.json.attempts.jsonl"
    request.update(phase="fresh_comparison", origin={"step_id": "owned-c7:next"})
    request["paths"] = {role: str(directory / name) for role, name in request["paths"].items()}
    source_dir = Path(assessment.__file__).parent
    sources = {name: digest((source_dir / name).read_bytes()) for name in assessment.SOURCE_NAMES + ("decision_assessment.py", "improvement.py")}
    for role, name in (("generator_source", "fresh-generator.py"), ("caller_source", "fresh-caller.py")):
        request["paths"][role] = str(EXAMPLES / name)
        sources[name] = digest((EXAMPLES / name).read_bytes())
    # Historical C7 implementation identities deliberately remain old. This
    # owned event envelope is synthetic; it is not a replacement C7 acceptance.
    old = {name: sources[name] for name in assessment.SOURCE_NAMES}
    old["decision_pilot.py"] = "fa066457406e999b7aec146e50fcb4ed7b18b8d96c78e923869133ef290de090"
    manifest = {"decision-input:code:epiphysics." + name.removesuffix(".py"): value for name, value in old.items()}
    manifest.update({"decision-input:code:epiphysics.decision_assessment": "3698f72d0718ed7f20f6975d2e9f9ad02987342fc8cffd0df1f928236d7b58da",
        "decision_assessment": "3698f72d0718ed7f20f6975d2e9f9ad02987342fc8cffd0df1f928236d7b58da",
        "controller": "4bc7b1fb53959061d2ef9414baf8745152db282bb6717b9b3c4b4ca20037ffba"})
    historical_identity = {"hash": "3cf4c36eff77965167e879ffa43134828b27459e64f6cd146389f67d550e46f6", "schema_version": 1}
    event = {"seq": 1, "id": "improvement:owned-c7:complete", "kind": "improvement_completed", "recorded_at": "2026-01-01T00:00:00+00:00",
        "previous_hash": "0" * 64, "body": {"result": "assessed", "run_key": "owned-c7", "next_step": {"action": "prepare_fresh_decision_comparison"},
        "assessment_identity": {"hash": "63982ce107f875a65dd9ad0bdde748182eb8d5cc5ef9457b66db8717111fd2cb",
            "decision_assessment_hash": historical_identity["hash"], "input_manifest": manifest}, "request": {"manifest": manifest},
        "report": {"decision_pilot": {"phase": "development", "stage": "exposed_development", "status": "checked",
            "next_step": {"action": "prepare_fresh_decision_comparison"}, "assessment_identity": historical_identity, "source_hashes": old}}}}
    event["hash"] = digest(raw({key: event[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}))
    event_raw = raw(event)
    historical_sources = {**old, "decision_assessment.py": manifest["decision_assessment"], "improvement.py": manifest["controller"]}
    origin = {"event_id": event["id"], "event_hash": event["hash"], "artifact_sha256": digest(event_raw),
        "assessment_hash": event["body"]["assessment_identity"]["hash"], "decision_assessment_hash": historical_identity["hash"],
        "implementation_hashes": historical_sources}
    for role in ("registration", "custody", "origin_transition", "claim", "caller_receipt"):
        request["paths"][role] = str(directory / (role + ".json"))
    for role in ("caller_stdout", "caller_stderr"):
        request["paths"][role] = str(directory / (role + ".bin"))
    outputs = {role: request["paths"][role] for role in ("cohort", "custody", "report", "journal", "claim", "caller_receipt")}
    outputs.update(stdout=request["paths"]["caller_stdout"], stderr=request["paths"]["caller_stderr"])
    registration = {"schema_version": 1, "registration_id": "owned-fresh-registration", "execution_id": "owned-fresh-execution",
        "phase": "fresh_comparison", "cohort_id": cohort["cohort_id"], "allocation": deepcopy(assessment.FRESH_ALLOCATION), "origin": origin,
        "contract_hashes": deepcopy(assessment.CONTRACT_HASHES), "source_hashes": sources,
        "limits": deepcopy(assessment.FRESH_REGISTRATION_LIMITS), "triage": deepcopy(assessment.FRESH_TRIAGE), "outputs": outputs,
        "frozen_at": "2026-01-01T00:00:01+00:00"}
    custody = {"schema_version": 1, "status": "complete", "registration_sha256": digest(raw(registration)),
        "generator_sha256": sources["fresh-generator.py"], "caller_sha256": sources["fresh-caller.py"], "seed_sha256": digest(b"owned seed control"),
        "cohort_sha256": digest(raw(cohort)), "cohort_canonical_sha256": digest(raw(cohort)), "cohort_bytes": len(raw(cohort)),
        "case_ids": [trace["trace_id"] for trace in cohort["traces"]], "allocation": deepcopy(assessment.FRESH_ALLOCATION),
        "truth_counts": {key: report["arms"][0]["summary"]["counts"][key] for key in assessment.TRUTH_COUNT_FIELDS},
        "generated_at": "2026-01-01T00:00:02+00:00", "first_exposure": None, "execution_id": registration["execution_id"]}
    common = {"schema_version": 1, "execution_id": registration["execution_id"], "registration_sha256": digest(raw(registration)),
        "custody_sha256": digest(raw(custody)), "cohort_sha256": digest(raw(cohort)), "caller_sha256": sources["fresh-caller.py"]}
    claim = {**common, "first_exposure_at": "2026-01-01T00:00:03+00:00"}
    stdout, stderr = b"owned caller completion\n", b""
    receipt = {**common, "status": "completed", "claim_sha256": digest(raw(claim)), "report_sha256": digest(raw(report)),
        "journal_sha256": digest(journal_for(cohort, report)), "returncode": 0 if all(report["checks"].values()) else 1,
        "started_at": "2026-01-01T00:00:02+00:00", "ended_at": "2026-01-01T00:00:06+00:00", "elapsed_seconds": 4.0,
        "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr), "stdout_bytes": len(stdout), "stderr_bytes": 0,
        "original_files_unchanged": True}
    for role, value in (("registration", registration), ("custody", custody), ("origin_transition", event), ("claim", claim), ("caller_receipt", receipt)):
        Path(request["paths"][role]).write_bytes(raw(value))
    Path(request["paths"]["caller_stdout"]).write_bytes(stdout)
    Path(request["paths"]["caller_stderr"]).write_bytes(stderr)
    path.write_bytes(raw(request))
    return path


class DecisionAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cohort, cls.report = synthetic_evidence()

    def _prepare(self, report=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = write_study(temporary.name, deepcopy(self.cohort), deepcopy(report or self.report))
        return path, assessment.prepare_decision_study(path)

    def _reject_report(self, mutate, message=None):
        report = deepcopy(self.report)
        mutate(report)
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, report)
            with self.assertRaisesRegex(ValueError, message or ".*"):
                assessment.prepare_decision_study(path)

    def test_complete_captured_replay_without_original_paths_or_candidates(self):
        path, prepared = self._prepare()
        before = deepcopy(prepared)
        for child in path.parent.iterdir():
            child.unlink()
        forbidden = []
        def profile(frame, event, arg):
            if event == "call" and frame.f_code.co_name in {"build_decision_view", "decide_release_hold", "_candidate", "run_development", "_run_candidate"}:
                forbidden.append(frame.f_code.co_name)
        sys.setprofile(profile)
        try:
            checked = assessment.assess_prepared_decision_study(prepared)
        finally:
            sys.setprofile(None)
        self.assertEqual(forbidden, [])
        self.assertEqual(prepared, before)
        self.assertEqual(checked["report"]["counts"]["attempts"], 48)
        self.assertEqual(checked["report"]["status"], "checked")
        self.assertEqual(checked["report"]["next_step"]["action"], "prepare_fresh_decision_comparison")
        self.assertNotIn("rows", checked["report"]["arms"][0])
        self.assertNotIn("strata", checked["report"]["arms"][0])
        self.assertEqual(checked["artifacts"]["assessment_report"], raw(checked["report"]))
        self.assertEqual(len(prepared["artifacts"]), 11)

    def test_large_bounded_failed_outputs_remain_failures(self):
        cohort, report = synthetic_evidence(overflow=True)
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, cohort, report)
            self.assertGreater((path.parent / "journal.jsonl").stat().st_size, 8 * 1024 * 1024)
            prepared = assessment.prepare_decision_study(path)
            checked = assessment.assess_prepared_decision_study(prepared)["report"]
        self.assertEqual(checked["next_step"]["action"], "repair_decision_pilot")
        for arm in checked["arms"]:
            self.assertEqual(arm["summary"]["counts"]["failed_attempts"], 12)
            self.assertEqual(arm["summary"]["metrics"]["missed_world_opportunities"]["denominator"], 12)
            self.assertEqual(arm["summary"]["metrics"]["valid_output_completion"]["numerator"], 0)

    def test_invalid_utf8_failure_preserves_exact_driver_error(self):
        cohort, report = synthetic_evidence(invalid_utf8=True)
        self.assertIn("'utf-8' codec can't decode byte", report["arms"][0]["rows"][0]["proposal_error"])
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, cohort, report)
            prepared = assessment.prepare_decision_study(path)
            self.assertEqual(prepared["report"]["next_step"]["action"], "repair_decision_pilot")
            self.assertEqual(prepared["report"]["arms"][0]["summary"]["counts"]["failed_attempts"], 12)
            report["arms"][0]["rows"][0]["proposal_error"] = "Invalid bounded JSON"
            write_study(directory, cohort, report)
            with self.assertRaisesRegex(ValueError, "Independent evaluated attempt"):
                assessment.prepare_decision_study(path)

    def test_incomplete_deadline_retains_exact_captured_failure_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, self.report)
            journal_path = path.parent / "journal.jsonl"
            declaration = json.loads(journal_path.read_bytes().splitlines()[0])
            first = self.report["arms"][0]["rows"][0]
            partial_receipt = deepcopy(first["worker_receipt"])
            prefix = b'{"view":"partial'
            partial_receipt.update(error="program_deadline", returncode=-9, stdout_base64=base64.b64encode(prefix).decode(),
                stdout_sha256=digest(prefix), stdout_bytes=len(prefix),
                output_scope="Prefix drained before the whole-program deadline; unread child bytes may be absent")
            failed = {"status": "failed", "error": "ProgramDeadline", "message": "Whole-program deadline exceeded",
                "checks": {"completed": False}, "journal": str(journal_path), "metrics": None,
                "scope": "Incomplete run; retained attempts must not be presented as complete cohort metrics",
                "next_step": {"action": "repair_decision_pilot", "scale_change_allowed": False}}
            partial = [declaration, {"kind": "worker_interrupted", "case_id": first["case_id"],
                "recipe": first["arm"], "budget_bytes": first["budget_bytes"], "input_hash": first["input_hash"],
                "receipt": partial_receipt}, {"kind": "run_terminal", "checks": failed["checks"], "next_step": failed["next_step"]}]
            (path.parent / "report.json").write_bytes(raw(failed) + b"\n")
            journal_path.write_bytes(b"".join(raw(item) + b"\n" for item in partial))
            expected = {role: (path.parent / name).read_bytes() for role, name in json.loads(path.read_bytes())["paths"].items()}
            expected["request"] = path.read_bytes()
            with self.assertRaises(assessment.DecisionStudyPreparationError) as refused:
                assessment.prepare_decision_study(path)
            error = refused.exception
            self.assertIsInstance(error, ValueError)
            self.assertFalse(hasattr(error, "report"))
            self.assertFalse(hasattr(error, "metrics"))
            for role, value in expected.items():
                self.assertEqual(error.artifacts[role], value)
            self.assertEqual(len(error.artifacts), 11)
            self.assertNotIn("assessment_report", error.artifacts)
            self.assertLessEqual(sum(map(len, error.artifacts.values())), assessment.MAX_BUNDLE_BYTES)

    def test_capture_error_retains_only_safely_read_bounded_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, self.report)
            # Canonical request order reads cohort before the missing contract.
            (path.parent / "decision_contract.json").unlink()
            with self.assertRaises(assessment.DecisionStudyPreparationError) as refused:
                assessment.prepare_decision_study(path)
            self.assertEqual(set(refused.exception.artifacts), {"request", "cohort"})
        error = assessment.DecisionStudyPreparationError("owned bound control", {
            "request": b"retained", "extra": b"unrecognized", "report": "not bytes",
            "cohort": b"x" * (assessment.LIMITS["cohort"] + 1)})
        self.assertEqual(error.artifacts, {"request": b"retained"})

    def test_recomputed_world_rows_aggregates_strata_and_checks(self):
        mutations = [
            lambda report: report["arms"][0]["rows"][0]["facts"].update(world_authorized=False),
            lambda report: report["arms"][0]["rows"][0]["metric_flags"].update(valid_timely_release=0),
            lambda report: report["arms"][0]["summary"]["metrics"]["valid_timely_release"].update(numerator=0),
            lambda report: report["arms"][0]["strata"]["retained transport control"]["counts"].update(failed_attempts=1),
            lambda report: report["checks"].update(fixed_policy_conformance=False),
            lambda report: report["next_step"].update(action="adopt_relational"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self._reject_report(mutate)

    def test_raw_receipts_hash_size_nonzero_and_failed_relabel(self):
        for change in ({"stdout_sha256": "0" * 64}, {"stdout_bytes": 0}, {"returncode": 1},
                       {"returncode": None}, {"error": "worker_exit", "returncode": 1}, {"request_bytes": 1}):
            with self.subTest(change=change):
                self._reject_report(lambda report: report["arms"][0]["rows"][0]["worker_receipt"].update(change))

    def test_public_bundle_view_and_source_bindings(self):
        for change in ({"input_hash": "0" * 64}, {"view_bytes": 0}, {"view_hash": "0" * 64},
                       {"complete": False}, {"header_bytes": 0}, {"provenance_valid": False}):
            with self.subTest(change=change):
                self._reject_report(lambda report: report["arms"][0]["rows"][0].update(change))
        self._reject_report(lambda report: report["source_hashes"].update({"decision_pilot.py": "0" * 64}))
        self._reject_report(lambda report: report.update(cohort_hash="0" * 64))

    def test_independent_output_support_and_timings(self):
        def mutate_response(report, field, value):
            receipt = report["arms"][0]["rows"][0]["worker_receipt"]
            response = json.loads(base64.b64decode(receipt["stdout_base64"]))
            if field == "support_event_ids":
                response["proposal"][field] = value
            else:
                response["timings"][field] = value
            encoded = raw(response)
            receipt.update(stdout_base64=base64.b64encode(encoded).decode(), stdout_bytes=len(encoded), stdout_sha256=digest(encoded))
        for field, value in (("support_event_ids", []), ("policy_seconds", 2.0), ("policy_seconds", -0.1), ("policy_seconds", True)):
            with self.subTest(field=field, value=value):
                self._reject_report(lambda report: mutate_response(report, field, value))
        self._reject_report(lambda report: report["arms"][0]["rows"][0]["resources"].update(normalization_seconds=True))
        self._reject_report(lambda report: report["resources"].update(parent_wall_seconds=0.1))

    def test_extra_missing_reordered_and_unmatched_journal_records(self):
        for mutation in (lambda lines: lines[:-1], lambda lines: lines + [lines[1]],
                         lambda lines: lines[:1] + [lines[2], lines[1]] + lines[3:],
                         lambda lines: lines[:1] + [lines[3]] + lines[2:]):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                path = write_study(directory, self.cohort, self.report)
                journal_path = path.parent / "journal.jsonl"
                lines = journal_path.read_bytes().splitlines(keepends=True)
                journal_path.write_bytes(b"".join(mutation(lines)))
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)
        self._reject_report(lambda report: report["arms"][0]["rows"].pop())
        self._reject_report(lambda report: report["arms"].reverse())

    def test_contract_and_original_input_shape_refusals(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_study(directory, self.cohort, self.report)
            contract = path.parent / "decision_contract.json"
            contract.write_bytes(contract.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Frozen"):
                assessment.prepare_decision_study(path)
        for change in ({"schema_version": True}, {"phase": "final"}, {"origin": {"step_id": ""}}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                path = write_study(directory, self.cohort, self.report)
                request = json.loads(path.read_bytes())
                request.update(change)
                path.write_bytes(raw(request))
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)

    def test_symlink_oversized_and_duplicate_json_refusals(self):
        for kind in ("symlink", "oversized", "duplicate"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                path = write_study(directory, self.cohort, self.report)
                cohort = path.parent / "cohort.json"
                if kind == "symlink":
                    alternate = path.parent / "other.json"
                    cohort.rename(alternate)
                    cohort.symlink_to(alternate)
                elif kind == "oversized":
                    cohort.write_bytes(b" " * (262144 + 1))
                else:
                    cohort.write_bytes(b'{"trace_count":12,"trace_count":12}')
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)

    def test_prepared_mutation_role_manifest_and_live_callables(self):
        _, prepared = self._prepare()
        for mutation in (lambda item: item["artifacts"].update(extra=b"unexpected"),
                         lambda item: item["manifest"].update(report="0" * 64),
                         lambda item: item["report"]["counts"].update(attempts=47)):
            changed = deepcopy(prepared)
            mutation(changed)
            with self.assertRaises(ValueError):
                assessment.check_prepared_decision_study(changed)
        with patch.object(evaluation, "reference_decision", lambda trace: {}):
            with self.assertRaisesRegex(ValueError, "Evaluator callable"):
                assessment.check_prepared_decision_study(prepared)
        with patch.object(views, "build_decision_view", lambda *args, **kwargs: b"{}"):
            with self.assertRaisesRegex(ValueError, "callable"):
                assessment.check_prepared_decision_study(prepared)


class FreshDecisionAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cohort, cls.report = synthetic_evidence(fresh=True)

    def test_fresh_retained_replay_preserves_historical_c7_and_never_executes_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fresh_study(directory, self.cohort, self.report)
            forbidden = []
            def profile(frame, event, arg):
                if event == "call" and frame.f_code.co_name in {"build_decision_view", "decide_release_hold", "_candidate", "run_development",
                        "run_fresh_comparison", "_run_candidate", "generate", "build_case"}:
                    forbidden.append(frame.f_code.co_name)
            sys.setprofile(profile)
            try:
                prepared = assessment.prepare_decision_study(path)
                for item in path.parent.iterdir():
                    item.unlink()
                checked = assessment.assess_prepared_decision_study(prepared)["report"]
            finally:
                sys.setprofile(None)
        self.assertEqual(forbidden, [])
        self.assertEqual(checked["counts"], {"cases": 24, "arms": 4, "attempts": 96, "journal_records": 194})
        self.assertEqual(checked["phase"], "fresh_comparison")
        self.assertEqual(checked["stage"], "fresh_exploratory")
        self.assertEqual(checked["next_step"]["action"], "investigate_decision_information_limits")
        self.assertEqual(checked["paired"]["both_valid_timely_releases"], 24)
        self.assertEqual(checked["paired"]["net_valid_timely_releases"], 0)
        self.assertEqual(set(checked["arms"][0]["strata"]), set(assessment.FRESH_ALLOCATION))
        historic = checked["origin_transition"]["implementation_hashes"]
        self.assertEqual(historic["decision_assessment.py"], "3698f72d0718ed7f20f6975d2e9f9ad02987342fc8cffd0df1f928236d7b58da")
        self.assertNotEqual(historic["decision_assessment.py"], digest(Path(assessment.__file__).read_bytes()))
        self.assertNotEqual(historic["decision_pilot.py"], checked["source_hashes"]["decision_pilot.py"])

    def test_fresh_maximal_failed_prefixes_fit_and_survive_preparation_failure(self):
        cohort, report = synthetic_evidence(fresh=True, overflow=True)
        with tempfile.TemporaryDirectory() as directory:
            path = write_fresh_study(directory, cohort, report)
            paths = json.loads(path.read_bytes())["paths"]
            self.assertGreater(Path(paths["report"]).stat().st_size, assessment.LIMITS["report"])
            self.assertGreater(Path(paths["journal"]).stat().st_size, assessment.LIMITS["journal"])
            prepared = assessment.prepare_decision_study(path)
            checked = assessment.assess_prepared_decision_study(prepared)
            self.assertLessEqual(sum(map(len, checked["artifacts"].values())), 48 * 1024 * 1024)
            self.assertEqual(checked["report"]["next_step"]["action"], "repair_decision_pilot")
            for arm in checked["report"]["arms"]:
                self.assertEqual(arm["summary"]["counts"]["failed_attempts"], 24)
                self.assertEqual(arm["summary"]["metrics"]["valid_output_completion"]["numerator"], 0)
            # Incomplete evidence must retain the same large raw prefixes,
            # without turning any partial metrics into checked cohort results.
            journal = Path(paths["journal"]).read_bytes()
            Path(paths["journal"]).write_bytes(b"\n".join(journal.splitlines()[:-1]) + b"\n")
            expected = {role: Path(location).read_bytes() for role, location in paths.items()}
            with self.assertRaises(assessment.DecisionStudyPreparationError) as refused:
                assessment.prepare_decision_study(path)
            self.assertFalse(hasattr(refused.exception, "report"))
            for role in ("report", "journal", "caller_receipt", "custody", "claim"):
                self.assertEqual(refused.exception.artifacts[role], expected[role])

    def test_fresh_fixed_count_allocation_identity_and_phase_refusals(self):
        for mutate in (lambda cohort: cohort["traces"].pop(),
                       lambda cohort: cohort["traces"][0].update(mechanism="role_direction"),
                       lambda cohort: cohort["traces"][1].update(trace_id=cohort["traces"][0]["trace_id"]),
                       lambda cohort: cohort.update(final_cohort_generated=False),
                       lambda cohort: cohort.update(status="exposed_development")):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                cohort = deepcopy(self.cohort)
                mutate(cohort)
                path = write_fresh_study(directory, cohort, self.report)
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)
        with tempfile.TemporaryDirectory() as directory:
            path = write_fresh_study(directory, self.cohort, self.report)
            request = json.loads(path.read_bytes())
            request["phase"] = "development"
            path.write_bytes(raw(request))
            with self.assertRaisesRegex(ValueError, "study paths"):
                assessment.prepare_decision_study(path)

    def test_fresh_registration_custody_origin_and_caller_binding_refusals(self):
        cases = [("registration", lambda item: item["limits"].update(program_seconds=31)),
                 ("registration", lambda item: item["triage"].update(minimum_additional_valid_timely_releases=1)),
                 ("registration", lambda item: item["source_hashes"].update({"decision_policy.py": "0" * 64})),
                 ("registration", lambda item: item["outputs"].update(report="/different/report.json")),
                 ("custody", lambda item: item.update(status="stopped")),
                 ("custody", lambda item: item.update(first_exposure="2026-01-01T00:00:03+00:00")),
                 ("custody", lambda item: item["truth_counts"].update(world_opportunities=0)),
                 ("origin_transition", lambda item: item["body"]["request"]["manifest"].update(controller="0" * 64)),
                 ("claim", lambda item: item.update(cohort_sha256="0" * 64)),
                 ("caller_receipt", lambda item: item.update(returncode=1)),
                 ("caller_receipt", lambda item: item.update(status="failed")),
                 ("caller_receipt", lambda item: item.update(elapsed_seconds=0)),
                 ("caller_receipt", lambda item: item.update(elapsed_seconds=60.001)),
                 ("caller_receipt", lambda item: item.update(ended_at="2025-01-01T00:00:00+00:00")),
                 ("caller_receipt", lambda item: item.update(stdout_sha256="0" * 64))]
        for role, mutate in cases:
            with self.subTest(role=role, mutate=mutate), tempfile.TemporaryDirectory() as directory:
                path = write_fresh_study(directory, self.cohort, self.report)
                artifact = Path(json.loads(path.read_bytes())["paths"][role])
                value = json.loads(artifact.read_bytes())
                mutate(value)
                artifact.write_bytes(raw(value))
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)

    def test_fresh_missing_extra_reordered_attempts_and_altered_successor_refused(self):
        for mutate in (lambda report: report["arms"][0]["rows"].pop(),
                       lambda report: report["arms"][0]["rows"].append(deepcopy(report["arms"][0]["rows"][0])),
                       lambda report: report["arms"][0]["rows"].reverse(),
                       lambda report: report["next_step"].update(action="prepare_fresh_decision_comparison")):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                report = deepcopy(self.report)
                mutate(report)
                path = write_fresh_study(directory, self.cohort, report)
                with self.assertRaises(ValueError):
                    assessment.prepare_decision_study(path)

    def test_self_consistent_custody_hashes_cannot_forge_denominators_or_ordering(self):
        for target in ("denominators", "ordering"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                path = write_fresh_study(directory, self.cohort, self.report)
                paths = json.loads(path.read_bytes())["paths"]
                custody = json.loads(Path(paths["custody"]).read_bytes())
                claim = json.loads(Path(paths["claim"]).read_bytes())
                receipt = json.loads(Path(paths["caller_receipt"]).read_bytes())
                if target == "denominators":
                    custody["truth_counts"]["world_opportunities"] = 0
                else:
                    custody["generated_at"] = "2026-01-01T00:00:04+00:00"
                custody_raw = raw(custody)
                claim["custody_sha256"] = digest(custody_raw)
                receipt["custody_sha256"] = digest(custody_raw)
                receipt["claim_sha256"] = digest(raw(claim))
                Path(paths["custody"]).write_bytes(custody_raw)
                Path(paths["claim"]).write_bytes(raw(claim))
                Path(paths["caller_receipt"]).write_bytes(raw(receipt))
                with self.assertRaisesRegex(ValueError, "Pre-scoring truth denominators" if target == "denominators" else "ordering"):
                    assessment.prepare_decision_study(path)

    def test_fresh_two_release_rule_each_harm_and_hard_repair(self):
        checks = dict.fromkeys(assessment.CHECK_FIELDS, True)
        arms = [{"summary": deepcopy(arm["summary"])} for arm in self.report["arms"]]
        arms[0]["summary"]["metrics"]["valid_timely_release"]["numerator"] = 20
        arms[1]["summary"]["metrics"]["valid_timely_release"]["numerator"] = 21
        self.assertEqual(assessment._next_step(checks, arms, fresh=True)["action"], "investigate_decision_information_limits")
        arms[1]["summary"]["metrics"]["valid_timely_release"]["numerator"] = 22
        self.assertEqual(assessment._next_step(checks, arms, fresh=True)["action"], "prepare_prospective_decision_shadow")
        for harm in assessment.FRESH_HARMS:
            changed = deepcopy(arms)
            changed[1]["summary"]["metrics"][harm]["numerator"] += 1
            self.assertEqual(assessment._next_step(checks, changed, fresh=True)["action"], "investigate_decision_information_limits")
        changed = deepcopy(arms)
        changed[1]["summary"]["counts"]["failed_attempts"] = 1
        self.assertEqual(assessment._next_step(checks, changed, fresh=True)["action"], "investigate_decision_information_limits")
        for check in checks:
            failed = {**checks, check: False}
            self.assertEqual(assessment._next_step(failed, arms, fresh=True)["action"], "repair_decision_pilot")
        for effect in ("unauthorized_effects", "duplicate_effects"):
            changed = deepcopy(arms)
            changed[2]["summary"]["metrics"][effect]["numerator"] = 1
            self.assertEqual(assessment._next_step(checks, changed, fresh=True)["action"], "repair_decision_pilot")


if __name__ == "__main__":
    unittest.main()
