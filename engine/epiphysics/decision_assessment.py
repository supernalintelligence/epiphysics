"""Check retained fixed development/fresh evidence without executing a candidate.

The journal is a trusted local caller receipt, not proof against a hostile
writer. Its complete fixed slot sequence, raw output bytes, public provenance,
independent evaluation and source identity are checked before controller use.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from types import CodeType

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import decision_evaluation as evaluation
from . import decision_views as views

IMPLEMENTATION_DEPENDENCIES = ((views.__name__, views.IMPLEMENTATION_CODE),)
SOURCE_NAMES = ("decision_views.py", "decision_policy.py", "decision_evaluation.py", "decision_pilot.py")
ARMS = (("flat-recency-v1", 2048), ("task-proximity-v1", 2048),
        ("flat-recency-v1", 32768), ("task-proximity-v1", 32768))
LIMITS = {"request": 16384, "cohort": 262144, "report": 8 * 1024 * 1024,
          "journal": 12 * 1024 * 1024, "decision_contract": 131072, "evaluation_contract": 131072}
MAX_SOURCE_BYTES = 131072
MAX_BUNDLE_BYTES = 24 * 1024 * 1024
FRESH_LIMITS = {**LIMITS, "report": 16 * 1024 * 1024, "journal": 24 * 1024 * 1024,
                "registration": 65536, "custody": 65536, "origin_transition": 262144,
                "generator_source": MAX_SOURCE_BYTES, "caller_source": MAX_SOURCE_BYTES,
                "claim": 16384, "caller_receipt": 65536, "caller_stdout": 65537, "caller_stderr": 65537}
FRESH_MAX_BUNDLE_BYTES = 48 * 1024 * 1024
FRESH_ALLOCATION = {"late_visibility": 6, "visible_authority_changes": 4, "verification_dispute": 4,
                    "duplicate_identity": 4, "retention_pressure": 4, "role_direction": 2}
FRESH_HARMS = ("unauthorized_release_proposals_all", "duplicate_release_proposals_all",
               "invalid_artifact_release_proposals", "evidence_unjustified_release_proposals")
FRESH_REGISTRATION_LIMITS = {"program_seconds": 30, "worker_seconds": 60, "normal_view_bytes": 2048,
    "lossless_view_bytes": 32768, "worker_output_bytes": 65536, "cohort_bytes": 262144,
    "report_bytes": 16777216, "journal_bytes": 25165824, "bundle_bytes": 50331648,
    "model_calls": 0, "external_program_spend": 0, "live_effects": False}
FRESH_TRIAGE = {"minimum_additional_valid_timely_releases": 2, "proposal_harm_metrics": list(FRESH_HARMS),
    "no_extra_failed_attempts": True, "repair_action": "repair_decision_pilot",
    "signal_action": "prepare_prospective_decision_shadow", "otherwise_action": "investigate_decision_information_limits"}
TRUTH_COUNT_FIELDS = {"cases", "world_opportunities", "visible_actionable_opportunities", "forbidden_cases",
                      "duplicate_opportunity_cases", "ordinary_attempts", "not_ready_or_invalid_cases"}
CONTRACT_HASHES = {
    "decision_contract": "751931e3078beb8511c1d1a9eed29a5b324026d078b109fada7d70b47c4a1ee4",
    "evaluation_contract": "1efd3dc61e89e5d1d51a03892255da1ec3cb8b46b2c9c8ba75b0cdb00b1e94d2",
}
EXTRA_ROW_FIELDS = {"arm", "budget_bytes", "input_hash", "source_hash", "source_bytes", "header_bytes",
                    "view_hash", "view_bytes", "view", "provenance_valid", "complete", "worker_receipt", "resources"}
CHECK_FIELDS = {"all_outputs_valid", "lossless_reference_parity", "fixed_policy_conformance",
                "same_input_same_output", "program_deadline_met", "source_unchanged"}
REPORT_FIELDS = {"schema_version", "contract_id", "cohort_id", "cohort_hash", "stage", "declared_case_count",
                 "source_hashes", "arms", "checks", "limits", "scope", "resources", "next_step"}
RECEIPT_FIELDS = {"error", "returncode", "elapsed_seconds", "request_bytes", "stdout_base64", "stderr_base64",
                  "stdout_sha256", "stderr_sha256", "stdout_bytes", "stderr_bytes"}
TRANSPORT_ERRORS = {"program_deadline", "request_limit", "worker_launch_failed", "worker_timeout",
                    "worker_output_limit", "worker_exit"}
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_EVALUATOR_PATH = Path(evaluation.__file__)
_EVALUATOR_SOURCE = _EVALUATOR_PATH.read_bytes()
_EVALUATOR_CODE = compile(_EVALUATOR_SOURCE, str(_EVALUATOR_PATH), "exec", dont_inherit=True, optimize=sys.flags.optimize)
_EVALUATOR_FUNCTIONS = tuple((name, value, value.__code__) for name, value in vars(evaluation).items()
    if callable(value) and getattr(value, "__module__", None) == evaluation.__name__ and hasattr(value, "__code__"))
_EVALUATOR_CONSTANTS = tuple((name, deepcopy(value)) for name, value in vars(evaluation).items() if name.isupper())


class DecisionStudyPreparationError(ValueError):
    """Rejected preparation with its safely read evidence, never a checked report."""

    def __init__(self, message, artifacts):
        super().__init__(message)
        limits, maximum = _artifact_limits(artifacts)
        source_names = SOURCE_NAMES + ("decision_assessment.py",) + (("improvement.py",) if limits is FRESH_LIMITS else ())
        allowed = set(limits) | {_source_role(name) for name in source_names}
        captured, total = {}, 0
        for role, value in artifacts.items():
            if role not in allowed or type(value) is not bytes or len(value) > limits.get(role, MAX_SOURCE_BYTES):
                continue
            if total + len(value) > maximum:
                continue
            captured[role] = value
            total += len(value)
        self.artifacts = captured


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw, *, worker=False):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("Nonfinite JSON number")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, RecursionError) as error:
        # The retained driver's failed evaluator row contains this exact
        # decoder error. Normalizing it would reject honest failed attempts.
        if worker:
            raise
        raise ValueError("Invalid bounded JSON") from error


def _keys(value, expected, label):
    _require(type(value) is dict and set(value) == set(expected), "Invalid " + label + " fields")


def _equal(actual, expected, label):
    # Canonical comparison distinguishes booleans from integers in receipts.
    _require(_canonical(actual) == _canonical(expected), label + " differs")


def _duration(value, label):
    _require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 60, "Invalid " + label)
    return value


def _read_file(path, maximum):
    path = Path(path)
    try:
        _require(not path.is_symlink() and path.is_file() and path.stat().st_size <= maximum,
                 "Input must be a bounded regular file, not a symlink")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Input must remain a regular file")
            raw = stream.read(maximum + 1)
    except OSError as error:
        raise ValueError("Input is missing or unreadable") from error
    _require(len(raw) <= maximum, "Input exceeds byte bound")
    return raw


def _source_role(name):
    return "code:epiphysics." + name.removesuffix(".py")


def _artifact_limits(artifacts):
    # Failure retention selects only a recognized explicit phase, even when
    # later request or evidence validation fails.
    try:
        fresh = _json(artifacts.get("request", b"{}")).get("phase") == "fresh_comparison"
    except (ValueError, TypeError, AttributeError, RecursionError):
        fresh = False
    return (FRESH_LIMITS, FRESH_MAX_BUNDLE_BYTES) if fresh else (LIMITS, MAX_BUNDLE_BYTES)


def _current_sources(*, fresh=False):
    path, source, code = _SELF
    _require(IMPLEMENTATION_SOURCE == source and IMPLEMENTATION_CODE is code, "Assessment implementation reloaded")
    _require(_read_file(path, MAX_SOURCE_BYTES) == source, "Assessment source changed")
    _require(compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) == code,
             "Assessment bytecode differs from source")
    for name, function, expected in _FUNCTION_CODES:
        _require(globals().get(name) is function and function.__code__ is expected, "Assessment callable changed: " + name)
    for name, value in _CONSTANTS:
        _require(type(globals().get(name)) is type(value) and globals()[name] == value, "Assessment constant changed: " + name)
    error_class, initializer, initializer_code = _ERROR_IDENTITY
    _require(DecisionStudyPreparationError is error_class and error_class.__init__ is initializer
             and initializer.__code__ is initializer_code, "Preparation error implementation changed")
    views.runtime_sources()
    _require(_read_file(_EVALUATOR_PATH, MAX_SOURCE_BYTES) == _EVALUATOR_SOURCE, "Evaluator source changed")
    compiled_functions = {item.co_name: item for item in _EVALUATOR_CODE.co_consts if isinstance(item, CodeType)}
    for name, function, expected in _EVALUATOR_FUNCTIONS:
        _require(getattr(evaluation, name, None) is function and function.__code__ is expected
                 and compiled_functions.get(name) == expected, "Evaluator callable/source changed: " + name)
    for name, value in _EVALUATOR_CONSTANTS:
        current = getattr(evaluation, name, None)
        _require(type(current) is type(value) and current == value, "Evaluator constant changed: " + name)
    result = {_source_role(name): _read_file(path.parent / name, MAX_SOURCE_BYTES) for name in SOURCE_NAMES}
    _require(result[_source_role("decision_views.py")] == views.IMPLEMENTATION_SOURCE, "View source changed")
    _require(result[_source_role("decision_evaluation.py")] == _EVALUATOR_SOURCE, "Evaluator source changed")
    result[_source_role("decision_assessment.py")] = source
    if fresh:
        result[_source_role("improvement.py")] = _read_file(path.parent / "improvement.py", MAX_SOURCE_BYTES)
        examples = path.parent.parent / "examples" / "control-exchange"
        for role, name in (("generator_source", "fresh-generator.py"), ("caller_source", "fresh-caller.py")):
            result[role] = _read_file(examples / name, MAX_SOURCE_BYTES)
    return result


def _request(value):
    _keys(value, {"schema_version", "study_id", "phase", "origin", "paths"}, "decision study request")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1
             and value["phase"] in ("development", "fresh_comparison"), "Only fixed schema 1 decision phases are supported")
    _require(type(value["study_id"]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value["study_id"]), "Invalid study identity")
    _keys(value["origin"], {"step_id"}, "origin")
    _require(type(value["origin"]["step_id"]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", value["origin"]["step_id"]), "Invalid origin step")
    limits = FRESH_LIMITS if value["phase"] == "fresh_comparison" else LIMITS
    _keys(value["paths"], set(limits) - {"request"}, "study paths")
    _require(all(type(path) is str and 0 < len(path.encode("utf-8")) <= 4096 and "\0" not in path
                 for path in value["paths"].values()), "Invalid input path")
    if value["phase"] == "fresh_comparison":
        _require(all(Path(path).is_absolute() for path in value["paths"].values()), "Fresh input paths must be absolute")


def _timestamp(value):
    _require(type(value) is str and len(value) <= 40, "Invalid local timestamp")
    parsed = datetime.fromisoformat(value)
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, "Local receipt timestamp must be UTC")
    return parsed


def _origin_transition(raw):
    """Bind a historical completion as recorded; never re-assess old source."""
    event = _json(raw)
    _keys(event, {"seq", "id", "kind", "recorded_at", "body", "previous_hash", "hash"}, "origin transition")
    payload = {key: event[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}
    _require(event["hash"] == _hash(_canonical(payload)), "Origin event hash differs")
    _require(event["kind"] == "improvement_completed" and type(event["seq"]) is int and event["seq"] > 0,
             "Origin must be a completed improvement event")
    body = event["body"]
    study = body["report"]["decision_pilot"]
    _require(body["result"] == "assessed" and body["next_step"]["action"] == "prepare_fresh_decision_comparison"
             and study["phase"] == "development" and study["stage"] == "exposed_development"
             and study["status"] == "checked" and study["next_step"]["action"] == "prepare_fresh_decision_comparison",
             "Origin is not accepted C7 development")
    manifest = body["request"]["manifest"]
    _equal(body["assessment_identity"]["input_manifest"], manifest, "Historical assessment manifest")
    _equal(body["assessment_identity"]["decision_assessment_hash"], study["assessment_identity"]["hash"],
           "Historical decision assessment identity")
    sources = {name: manifest["decision-input:" + _source_role(name)] for name in SOURCE_NAMES + ("decision_assessment.py",)}
    sources["improvement.py"] = manifest["controller"]
    _equal({name: sources[name] for name in SOURCE_NAMES}, study["source_hashes"], "Historical implementation identities")
    _equal(sources["decision_assessment.py"], manifest["decision_assessment"], "Historical helper identity")
    _require(all(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) for value in sources.values()),
             "Invalid historical implementation digest")
    return {"event_id": event["id"], "event_hash": event["hash"], "artifact_sha256": _hash(raw),
            "assessment_hash": body["assessment_identity"]["hash"],
            "decision_assessment_hash": study["assessment_identity"]["hash"], "implementation_hashes": sources}


def _fresh_metadata(artifacts, request, cohort):
    registration, custody = _json(artifacts["registration"]), _json(artifacts["custody"])
    _keys(registration, {"schema_version", "registration_id", "phase", "cohort_id", "allocation", "origin",
        "contract_hashes", "source_hashes", "limits", "triage", "outputs", "execution_id", "frozen_at"}, "fresh registration")
    _equal([registration["schema_version"], registration["phase"], registration["cohort_id"]],
           [1, "fresh_comparison", "decision-pilot-fresh-v1"], "Fresh registration phase")
    for key in ("registration_id", "execution_id"):
        _require(type(registration[key]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", registration[key]), "Invalid registration identity")
    _equal(registration["allocation"], FRESH_ALLOCATION, "Registered allocation")
    _equal(registration["contract_hashes"], CONTRACT_HASHES, "Registered contracts")
    _equal(registration["limits"], FRESH_REGISTRATION_LIMITS, "Registered limits")
    _equal(registration["triage"], FRESH_TRIAGE, "Registered triage")
    origin = _origin_transition(artifacts["origin_transition"])
    _equal(registration["origin"], origin, "Registered origin")
    source_hashes = {name: _hash(artifacts[_source_role(name)]) for name in SOURCE_NAMES + ("decision_assessment.py", "improvement.py")}
    source_hashes.update({"fresh-generator.py": _hash(artifacts["generator_source"]), "fresh-caller.py": _hash(artifacts["caller_source"])})
    _equal(registration["source_hashes"], source_hashes, "Fresh source registration")
    for name in ("decision_views.py", "decision_policy.py", "decision_evaluation.py"):
        _equal(source_hashes[name], origin["implementation_hashes"][name], "Unchanged C7 comparison source")
    outputs = registration["outputs"]
    _keys(outputs, {"cohort", "custody", "report", "journal", "claim", "caller_receipt", "stdout", "stderr"}, "registered outputs")
    for role, output in outputs.items():
        _require(type(output) is str and 0 < len(output.encode()) <= 4096 and "\0" not in output
                 and Path(output).is_absolute(), "Registered output must be an absolute path")
        request_role = {"stdout": "caller_stdout", "stderr": "caller_stderr"}.get(role, role)
        _equal(request["paths"][request_role], output, "Registered output location")
    _require(len(set(outputs.values())) == len(outputs), "Registered outputs alias")
    _equal(outputs["journal"], outputs["report"] + ".attempts.jsonl", "Registered journal location")
    _keys(custody, {"schema_version", "status", "registration_sha256", "generator_sha256", "caller_sha256", "seed_sha256",
        "cohort_sha256", "cohort_canonical_sha256", "cohort_bytes", "case_ids", "allocation", "truth_counts", "generated_at",
        "first_exposure", "execution_id"}, "fresh custody")
    _equal({key: custody[key] for key in ("schema_version", "status", "registration_sha256", "generator_sha256", "caller_sha256",
        "cohort_sha256", "cohort_canonical_sha256", "cohort_bytes", "case_ids", "allocation", "first_exposure", "execution_id")},
        {"schema_version": 1, "status": "complete", "registration_sha256": _hash(artifacts["registration"]),
         "generator_sha256": source_hashes["fresh-generator.py"], "caller_sha256": source_hashes["fresh-caller.py"],
         "cohort_sha256": _hash(artifacts["cohort"]), "cohort_canonical_sha256": _hash(_canonical(cohort)),
         "cohort_bytes": len(artifacts["cohort"]), "case_ids": [trace["trace_id"] for trace in cohort["traces"]],
         "allocation": FRESH_ALLOCATION, "first_exposure": None, "execution_id": registration["execution_id"]}, "Custody bindings")
    _require(type(custody["seed_sha256"]) is str and re.fullmatch("[0-9a-f]{64}", custody["seed_sha256"]), "Invalid seed commitment")
    claim = _json(artifacts["claim"])
    _keys(claim, {"schema_version", "execution_id", "registration_sha256", "custody_sha256", "cohort_sha256", "caller_sha256", "first_exposure_at"}, "caller claim")
    common = {"schema_version": 1, "execution_id": registration["execution_id"], "registration_sha256": _hash(artifacts["registration"]),
              "custody_sha256": _hash(artifacts["custody"]), "cohort_sha256": _hash(artifacts["cohort"]),
              "caller_sha256": source_hashes["fresh-caller.py"]}
    _equal({key: claim[key] for key in common}, common, "Caller claim bindings")
    receipt = _json(artifacts["caller_receipt"])
    _keys(receipt, set(common) | {"status", "claim_sha256", "report_sha256", "journal_sha256", "returncode", "started_at", "ended_at",
        "elapsed_seconds", "stdout_sha256", "stderr_sha256", "stdout_bytes", "stderr_bytes", "original_files_unchanged"}, "caller receipt")
    _equal({key: receipt[key] for key in common}, common, "Caller execution bindings")
    _equal([receipt["status"], receipt["claim_sha256"], receipt["report_sha256"], receipt["journal_sha256"], receipt["original_files_unchanged"]],
           ["completed", _hash(artifacts["claim"]), _hash(artifacts["report"]), _hash(artifacts["journal"]), True], "Caller completion bindings")
    _require(type(receipt["returncode"]) is int and receipt["returncode"] in (0, 1), "Incomplete caller return")
    _duration(receipt["elapsed_seconds"], "outer caller duration")
    _require(_timestamp(registration["frozen_at"]) <= _timestamp(custody["generated_at"]) <= _timestamp(claim["first_exposure_at"])
             <= _timestamp(receipt["ended_at"]) and _timestamp(receipt["started_at"]) <= _timestamp(claim["first_exposure_at"]),
             "Invalid local custody/exposure ordering")
    for label in ("stdout", "stderr"):
        _equal([receipt[label + "_sha256"], receipt[label + "_bytes"]],
               [_hash(artifacts["caller_" + label]), len(artifacts["caller_" + label])], "Outer output receipt")
    _require(len(artifacts["caller_stdout"]) + len(artifacts["caller_stderr"]) <= 65536, "Outer caller output exceeds bound")
    return registration, custody, origin, receipt


def _receipt(value, bundle, recipe, budget):
    _keys(value, RECEIPT_FIELDS, "worker receipt")
    elapsed = _duration(value["elapsed_seconds"], "child duration")
    _require(value["returncode"] is None or type(value["returncode"]) is int and -255 <= value["returncode"] <= 255,
             "Invalid child return code")
    _require(value["error"] is None or type(value["error"]) is str and value["error"] in TRANSPORT_ERRORS,
             "Invalid child failure category")
    _require(value["error"] is not None or value["returncode"] == 0, "Nonzero or missing child cannot be successful")
    if value["error"] == "worker_exit":
        _require(value["returncode"] is not None and value["returncode"] != 0, "Worker-exit receipt lacks nonzero exit")
    request = {"header": bundle["header_bytes"].decode(), "tape": bundle["event_tape_bytes"].decode(),
               "recipe": recipe, "budget_bytes": budget}
    _equal(value["request_bytes"], len(_canonical(request)), "Public request byte count")
    streams = {}
    for label in ("stdout", "stderr"):
        encoded = value[label + "_base64"]
        _require(type(encoded) is str and len(encoded) <= 87384, "Invalid bounded raw output encoding")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, UnicodeError) as error:
            raise ValueError("Invalid raw output encoding") from error
        _require(base64.b64encode(raw).decode() == encoded, "Noncanonical raw output encoding")
        _equal(value[label + "_bytes"], len(raw), "Raw output byte count")
        _require(value[label + "_sha256"] == _hash(raw), "Raw output hash differs")
        streams[label] = raw
    total = sum(map(len, streams.values()))
    _require(total <= 65537 and (total <= 65536 or value["error"] == "worker_output_limit"), "Raw child output exceeds bound")
    if value["error"] == "worker_output_limit":
        _require(total == 65537, "Output-limit receipt lacks retained overflow prefix")
    return streams, elapsed


def _response(raw, bundle, recipe, budget, elapsed):
    """Decode retained output only; never build a view or execute the policy."""
    response = _json(raw, worker=True)
    if type(response) is not dict or set(response) != {"view", "proposal", "input_hash", "source_hash", "complete", "timings"}:
        raise ValueError("Invalid worker response shape")
    if type(response["view"]) is not str:
        raise ValueError("Missing serialized view")
    view = response["view"].encode()
    parsed = _json(view, worker=True)
    if parsed.get("arm") != recipe:
        raise ValueError("Worker used a different recipe")
    verified = views.validate_decode_view(bundle["header_bytes"], bundle["event_tape_bytes"], view, budget_bytes=budget)
    if (response["input_hash"] != verified.input_hash or response["source_hash"] != verified.source_hash
            or type(response["complete"]) is not bool or response["complete"] != verified.complete):
        raise ValueError("Worker input/provenance receipt differs")
    expected_ids = sorted(event["event_id"] for event in verified.events if event["kind"] in views.POLICY_KINDS)
    if type(response["proposal"]) is not dict or response["proposal"].get("support_event_ids") != expected_ids:
        raise ValueError("Proposal evidence IDs differ from retained policy records")
    timings = response["timings"]
    if type(timings) is not dict or set(timings) != {"build_seconds", "validate_decode_seconds", "policy_seconds"}:
        raise ValueError("Missing worker resource accounting")
    for duration in timings.values():
        if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 <= duration <= elapsed:
            raise ValueError("Invalid worker duration")
    if sum(timings.values()) > elapsed:
        raise ValueError("Overlapping or invalid worker durations")
    return response, view, verified


def _row(trace, row, recipe, budget):
    _keys(row, evaluation.ROW_FIELDS | EXTRA_ROW_FIELDS, "retained attempt")
    bundle = views.prepare_decision_input(trace["events"], trace["task"], trace["cutoff"], trace["decision_at"])
    streams, elapsed = _receipt(row["worker_receipt"], bundle, recipe, budget)
    error = row["worker_receipt"]["error"]
    response, view, verified = None, None, None
    if error is None:
        try:
            response, view, verified = _response(streams["stdout"], bundle, recipe, budget, elapsed)
        except (ValueError, TypeError, KeyError, UnicodeError, AttributeError, RecursionError, OverflowError) as invalid:
            error = str(invalid).encode("utf-8", errors="replace")[:400].decode("utf-8", errors="replace")
    proposal = None if error else response["proposal"]
    evaluated = evaluation.evaluate_simulated_proposal(trace, proposal, prior_effect_keys=(), error=error)
    _equal({key: row[key] for key in evaluation.ROW_FIELDS}, evaluated, "Independent evaluated attempt")
    expected = {"arm": recipe, "budget_bytes": budget, "input_hash": bundle["input_hash"],
                "source_hash": _hash(bundle["event_tape_bytes"]), "source_bytes": len(bundle["event_tape_bytes"]),
                "header_bytes": len(bundle["header_bytes"]), "view_hash": _hash(view) if view is not None else None,
                "view_bytes": len(view) if view is not None else None, "view": view.decode() if view is not None else None,
                "provenance_valid": verified is not None, "complete": verified.complete if verified is not None else None}
    _equal({key: row[key] for key in expected}, expected, "Public input/view receipt")
    resources = row["resources"]
    _keys(resources, {"normalization_seconds", "candidate_stages", "child_wall_seconds", "parent_verification_seconds",
                      "model_calls", "external_program_spend", "memory_bytes"}, "attempt resource accounting")
    _duration(resources["normalization_seconds"], "normalization duration")
    _duration(resources["parent_verification_seconds"], "verification duration")
    _equal(resources["child_wall_seconds"], elapsed, "Child wall receipt")
    _equal(resources["candidate_stages"], response["timings"] if response is not None and not error else None, "Candidate stage receipt")
    _equal([resources["model_calls"], resources["external_program_spend"], resources["memory_bytes"]], [0, 0, None], "Local execution accounting")
    return evaluated, (row["view_hash"], proposal, error), bundle, verified


def _next_step(checks, arms, *, fresh=False):
    repair = not all(checks.values()) or any(arm["summary"]["metrics"][name]["numerator"]
        for arm in arms for name in ("duplicate_effects", "unauthorized_effects"))
    if fresh:
        flat, relational = [arm["summary"] for arm in arms[:2]]
        signal = (relational["metrics"]["valid_timely_release"]["numerator"] - flat["metrics"]["valid_timely_release"]["numerator"] >= 2
                  and relational["counts"]["failed_attempts"] <= flat["counts"]["failed_attempts"]
                  and all(relational["metrics"][name]["numerator"] <= flat["metrics"][name]["numerator"] for name in FRESH_HARMS))
        return {"action": "repair_decision_pilot" if repair else
                    "prepare_prospective_decision_shadow" if signal else "investigate_decision_information_limits",
                "reason": "A conformance, execution or separation check failed" if repair else
                    "Fresh exploratory comparison met the registered two-release triage margin; prepare one nonacting prospective shadow task" if signal else
                    "Fresh exploratory comparison did not meet the registered triage margin; retain the flat baseline and investigate information limits",
                "scale_change_allowed": False, "live_effects_allowed": False,
                "metric_status": "fresh exploratory measurements; research triage only; no adoption claim"}
    return {"action": "repair_decision_pilot" if repair else "prepare_fresh_decision_comparison",
            "reason": "A conformance, execution or separation check failed" if repair else
                "Development wiring passed; freeze and review before generating one new 24-case exploratory batch",
            "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "exposed development measurements; no adoption claim"}


def _validate(artifacts):
    request = _json(artifacts["request"])
    _request(request)
    fresh = request["phase"] == "fresh_comparison"
    count, stage = (24, "fresh_exploratory") if fresh else (12, "exposed_development")
    for role, expected in CONTRACT_HASHES.items():
        _require(_hash(artifacts[role]) == expected, "Frozen " + role + " bytes differ")
    cohort, report = _json(artifacts["cohort"]), _json(artifacts["report"])
    _require(type(cohort) is dict and cohort.get("cohort_id") == ("decision-pilot-fresh-v1" if fresh else "decision-pilot-development-v1")
             and cohort.get("contract_id") == views.CONTRACT_ID and type(cohort.get("trace_count")) is int
             and cohort["trace_count"] == count and cohort.get("final_cohort_generated") is fresh
             and type(cohort.get("traces")) is list and len(cohort["traces"]) == count, "Invalid owned fixed cohort")
    traces = cohort["traces"]
    for trace in traces:
        evaluation.resolve_world(trace)
    identities = [trace["trace_id"] for trace in traces]
    _require(len(set(identities)) == count, "Duplicate case identity")
    if fresh:
        _keys(cohort, {"schema_version", "cohort_id", "contract_id", "status", "trace_count", "final_cohort_generated", "allocation", "traces"}, "fresh cohort")
        _equal([cohort["schema_version"], cohort["status"], cohort["allocation"]], [1, stage, FRESH_ALLOCATION], "Fresh cohort declaration")
        _equal({name: sum(trace["mechanism"] == name for trace in traces) for name in {trace["mechanism"] for trace in traces}},
               FRESH_ALLOCATION, "Fresh mechanism allocation")
        registration, custody, origin_transition, caller_receipt = _fresh_metadata(artifacts, request, cohort)
    source_hashes = {name: _hash(artifacts[_source_role(name)]) for name in SOURCE_NAMES}
    cohort_hash = _hash(_canonical(cohort))
    _keys(report, REPORT_FIELDS, "complete fixed report")
    _equal({key: report[key] for key in ("schema_version", "contract_id", "cohort_id", "cohort_hash", "stage", "declared_case_count", "source_hashes")},
           {"schema_version": 1, "contract_id": views.CONTRACT_ID, "cohort_id": cohort["cohort_id"], "cohort_hash": cohort_hash,
            "stage": stage, "declared_case_count": count, "source_hashes": source_hashes}, "Report declaration")
    _equal(report["limits"], {"program_seconds": 30, "normal_view_bytes": 2048, "lossless_view_bytes": 32768,
                              "worker_output_bytes": 65536}, "Fixed program limits")
    _equal(report["scope"], "Owned synthetic fresh exploratory comparison only; retention and view systems compared together; no generalization or live authority claim" if fresh else
           "Owned synthetic development only; retention and view systems compared together; no generalization or live authority claim", "Comparison scope")
    raw_journal = artifacts["journal"]
    _require(raw_journal.endswith(b"\n") and raw_journal.count(b"\n") == count * 8 + 2, "Journal must contain every fixed complete attempt pair")
    journal = [_json(line) for line in raw_journal.splitlines()]
    _require(all(_canonical(item) + b"\n" == line for item, line in zip(journal, raw_journal.splitlines(keepends=True))), "Journal record is not canonical")
    _equal(journal[0], {"kind": "declared_run", "cohort_hash": cohort_hash, "source_hashes": source_hashes,
        "arms": [list(arm) for arm in ARMS], "case_ids": identities,
        "scope": "fresh exploratory comparison; only root may invoke the registered run" if fresh else
            "exposed development; only root may invoke the registered run"}, "Journal declaration")
    _require(type(report["arms"]) is list and len(report["arms"]) == 4, "Report must contain exactly four arms")
    checks = dict.fromkeys(CHECK_FIELDS, True)
    signatures, compact_arms, slot, accounted = {}, [], 0, 0.0
    for arm, (recipe, budget) in zip(report["arms"], ARMS):
        _keys(arm, {"recipe", "budget_bytes", "control", "rows", "summary", "strata"}, "reported arm")
        _equal([arm["recipe"], arm["budget_bytes"], arm["control"]], [recipe, budget, budget == 32768], "Fixed arm order")
        _require(type(arm["rows"]) is list and len(arm["rows"]) == count, "Arm must contain every declared case")
        rows = []
        for trace, row in zip(traces, arm["rows"]):
            evaluated, signature, bundle, verified = _row(trace, row, recipe, budget)
            rows.append(evaluated)
            _equal(journal[1 + slot * 2], {"kind": "worker_returned", "case_id": trace["trace_id"], "recipe": recipe,
                "budget_bytes": budget, "input_hash": bundle["input_hash"], "receipt": row["worker_receipt"]}, "Journal worker slot")
            _equal(journal[2 + slot * 2], {"kind": "attempt_evaluated", "row": row}, "Journal evaluated slot")
            slot += 1
            resources = row["resources"]
            accounted += sum(resources[name] for name in ("normalization_seconds", "child_wall_seconds", "parent_verification_seconds"))
            checks["all_outputs_valid"] &= evaluated["proposal_valid"]
            conformant = evaluated["proposal_valid"] and (evaluated["proposal"] == evaluated["reference_proposal"] if verified and verified.complete else
                evaluated["proposal"]["action"] == "hold" and evaluated["proposal"]["reason"] == "incomplete_evidence")
            checks["fixed_policy_conformance"] &= conformant
            if budget == 32768:
                checks["lossless_reference_parity"] &= evaluated["proposal_valid"] and evaluated["proposal"] == evaluated["reference_proposal"]
            key = (recipe, budget, bundle["input_hash"])
            if key in signatures and signatures[key] != signature:
                checks["same_input_same_output"] = False
            signatures[key] = signature
        summary = evaluation.aggregate_metrics(rows)
        strata = {mechanism: evaluation.aggregate_metrics([row for row in rows if row["mechanism"] == mechanism])
                  for mechanism in sorted({row["mechanism"] for row in rows})}
        _equal(arm["summary"], summary, "Independent arm metrics")
        _equal(arm["strata"], strata, "Independent mechanism metrics")
        compact_arms.append({"recipe": recipe, "budget_bytes": budget, "control": budget == 32768, "summary": summary})
        if fresh:
            compact_arms[-1]["strata"] = strata
    resources = report["resources"]
    _keys(resources, {"parent_wall_seconds", "model_calls", "external_program_spend", "agent_and_review_cost", "memory_bytes", "accounting"}, "Report resources")
    elapsed = _duration(resources["parent_wall_seconds"], "whole program duration")
    _require(accounted <= elapsed + 1e-9, "Attempt resource durations exceed enclosing program wall")
    if fresh:
        _require(elapsed <= caller_receipt["elapsed_seconds"] + 1e-9, "Program duration exceeds enclosing caller wall")
    _equal([resources["model_calls"], resources["external_program_spend"], resources["agent_and_review_cost"], resources["memory_bytes"]], [0, 0, None, None], "Program local accounting")
    _equal(resources["accounting"], "Child wall contains its stage times. Parent wall includes computation and attempt journaling through final source verification, excluding final report serialization/persistence. Do not add nested totals. Lossless arms are separate controls; retain caller wall time separately.", "Resource accounting scope")
    checks["program_deadline_met"] = elapsed <= 30
    _equal(report["checks"], checks, "Recomputed conformance checks")
    next_step = _next_step(checks, compact_arms, fresh=fresh)
    _equal(report["next_step"], next_step, "Comparison successor")
    _equal(journal[-1], {"kind": "run_terminal", "checks": checks, "next_step": next_step}, "Journal terminal")
    manifest = {role: _hash(raw) for role, raw in artifacts.items()}
    result = {"schema_version": 1, "study_id": request["study_id"], "phase": request["phase"], "status": "checked",
            "stage": stage, "origin": deepcopy(request["origin"]),
            "assessment_identity": {"schema_version": 1, "hash": _hash(_canonical(manifest))},
            "input_hashes": {role: manifest[role] for role in (FRESH_LIMITS if fresh else LIMITS)}, "source_hashes": source_hashes,
            "counts": {"cases": count, "arms": 4, "attempts": count * 4, "journal_records": count * 8 + 2},
            "arms": compact_arms, "checks": checks, "next_step": next_step,
            "resources": deepcopy(resources), "scope": report["scope"]}
    if fresh:
        truth = {key: compact_arms[0]["summary"]["counts"][key] for key in TRUTH_COUNT_FIELDS}
        _equal(custody["truth_counts"], truth, "Pre-scoring truth denominators")
        _equal(caller_receipt["returncode"], 0 if all(checks.values()) else 1, "Completed caller exit status")
        pairs = [(left["metric_flags"]["valid_timely_release"], right["metric_flags"]["valid_timely_release"])
                 for left, right in zip(report["arms"][0]["rows"], report["arms"][1]["rows"])]
        result["paired"] = {"flat_only_valid_timely_releases": sum(a and not b for a, b in pairs),
            "relational_only_valid_timely_releases": sum(b and not a for a, b in pairs),
            "both_valid_timely_releases": sum(a and b for a, b in pairs),
            "neither_valid_timely_releases": sum(not a and not b for a, b in pairs),
            "net_valid_timely_releases": sum(b - a for a, b in pairs)}
        result["origin_transition"] = origin_transition
        result["registration"] = {"sha256": manifest["registration"], "registration_id": registration["registration_id"],
            "execution_id": registration["execution_id"], "allocation": deepcopy(FRESH_ALLOCATION), "truth_counts": truth}
    return result


def _check_artifacts(prepared):
    _keys(prepared, {"artifacts", "manifest", "report"}, "prepared decision study")
    request = _json(prepared["artifacts"]["request"])
    _request(request)
    fresh = request["phase"] == "fresh_comparison"
    limits, maximum = _artifact_limits(prepared["artifacts"])
    names = SOURCE_NAMES + ("decision_assessment.py",) + (("improvement.py",) if fresh else ())
    roles = set(limits) | {_source_role(name) for name in names}
    _keys(prepared["artifacts"], roles, "captured artifact")
    _keys(prepared["manifest"], roles, "captured manifest")
    total = 0
    for role, raw in prepared["artifacts"].items():
        _require(type(raw) is bytes and len(raw) <= limits.get(role, MAX_SOURCE_BYTES), "Invalid bounded artifact bytes")
        _require(prepared["manifest"][role] == _hash(raw), "Captured artifact digest differs")
        total += len(raw)
    _require(total <= maximum, "Captured study exceeds aggregate byte bound")
    # The two outer streams may legitimately both be empty. Input and source
    # roles still must have independent identities.
    distinct_roles = roles - ({"caller_stdout", "caller_stderr"} if fresh else set())
    _require(len({prepared["manifest"][role] for role in distinct_roles}) == len(distinct_roles), "Captured artifact roles must contain distinct bytes")
    for role, raw in _current_sources(fresh=fresh).items():
        _require(prepared["artifacts"][role] == raw, "Captured study source changed")


def prepare_decision_study(path):
    """Read one fixed request and capture its bounded retained evidence once."""
    artifacts = {}
    try:
        path = Path(path)
        artifacts["request"] = _read_file(path, LIMITS["request"])
        request = _json(artifacts["request"])
        _request(request)
        limits, _ = _artifact_limits(artifacts)
        paths = [path]
        for role, declared in request["paths"].items():
            source_path = Path(declared)
            if not source_path.is_absolute():
                source_path = path.parent / source_path
            paths.append(source_path)
            artifacts[role] = _read_file(source_path, limits[role])
        _require(len({(item.stat().st_dev, item.stat().st_ino) for item in paths}) == len(paths), "Input roles alias the same file")
        current = _current_sources(fresh=request["phase"] == "fresh_comparison")
        for role in ("generator_source", "caller_source"):
            if role in artifacts:
                _require(artifacts[role] == current[role], "Captured external source changed")
        artifacts.update(current)
        prepared = {"artifacts": artifacts, "manifest": {role: _hash(raw) for role, raw in artifacts.items()}, "report": None}
        _check_artifacts(prepared)
        prepared["report"] = _validate(artifacts)
        return prepared
    except (ValueError, OSError, TypeError, KeyError, AttributeError, RecursionError, OverflowError) as error:
        raise DecisionStudyPreparationError(str(error), artifacts) from error


def check_prepared_decision_study(prepared):
    """Recheck captured bytes and executing code, without original input paths."""
    _check_artifacts(prepared)
    _equal(prepared["report"], _validate(prepared["artifacts"]), "Prepared checked report")


def assess_prepared_decision_study(prepared):
    """Return only a compact checked report and retained input/output artifacts."""
    check_prepared_decision_study(prepared)
    report = deepcopy(prepared["report"])
    artifacts = dict(prepared["artifacts"])
    artifacts["assessment_report"] = _canonical(report)
    _, maximum = _artifact_limits(artifacts)
    _require(sum(map(len, artifacts.values())) <= maximum, "Assessment output exceeds aggregate byte bound")
    return {"report": report, "artifacts": artifacts}


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
_CONSTANTS = tuple((name, deepcopy(globals()[name])) for name in ("SOURCE_NAMES", "ARMS", "LIMITS", "MAX_SOURCE_BYTES",
    "MAX_BUNDLE_BYTES", "FRESH_LIMITS", "FRESH_MAX_BUNDLE_BYTES", "FRESH_ALLOCATION", "FRESH_HARMS",
    "FRESH_REGISTRATION_LIMITS", "FRESH_TRIAGE", "TRUTH_COUNT_FIELDS", "CONTRACT_HASHES", "EXTRA_ROW_FIELDS",
    "CHECK_FIELDS", "REPORT_FIELDS", "RECEIPT_FIELDS", "TRANSPORT_ERRORS"))
_ERROR_IDENTITY = (DecisionStudyPreparationError, DecisionStudyPreparationError.__init__, DecisionStudyPreparationError.__init__.__code__)
