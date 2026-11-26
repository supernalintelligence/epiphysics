"""Check retained local development evidence without executing a candidate.

The journal is a trusted local caller receipt, not proof against a hostile
writer. Its complete fixed slot sequence, raw output bytes, public provenance,
independent evaluation and source identity are checked before controller use.
"""
from __future__ import annotations

import base64
from copy import deepcopy
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
        allowed = set(LIMITS) | {_source_role(name) for name in SOURCE_NAMES + ("decision_assessment.py",)}
        captured, total = {}, 0
        for role, value in artifacts.items():
            if role not in allowed or type(value) is not bytes or len(value) > LIMITS.get(role, MAX_SOURCE_BYTES):
                continue
            if total + len(value) > MAX_BUNDLE_BYTES:
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


def _current_sources():
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
    return result


def _request(value):
    _keys(value, {"schema_version", "study_id", "phase", "origin", "paths"}, "decision study request")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1
             and value["phase"] == "development", "Only schema 1 development studies are supported")
    _require(type(value["study_id"]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value["study_id"]), "Invalid study identity")
    _keys(value["origin"], {"step_id"}, "origin")
    _require(type(value["origin"]["step_id"]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", value["origin"]["step_id"]), "Invalid origin step")
    _keys(value["paths"], set(LIMITS) - {"request"}, "study paths")
    _require(all(type(path) is str and 0 < len(path.encode("utf-8")) <= 4096 and "\0" not in path
                 for path in value["paths"].values()), "Invalid input path")


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


def _next_step(checks, arms):
    repair = not all(checks.values()) or any(arm["summary"]["metrics"][name]["numerator"]
        for arm in arms for name in ("duplicate_effects", "unauthorized_effects"))
    return {"action": "repair_decision_pilot" if repair else "prepare_fresh_decision_comparison",
            "reason": "A conformance, execution or separation check failed" if repair else
                "Development wiring passed; freeze and review before generating one new 24-case exploratory batch",
            "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "exposed development measurements; no adoption claim"}


def _validate(artifacts):
    request = _json(artifacts["request"])
    _request(request)
    for role, expected in CONTRACT_HASHES.items():
        _require(_hash(artifacts[role]) == expected, "Frozen " + role + " bytes differ")
    cohort, report = _json(artifacts["cohort"]), _json(artifacts["report"])
    _require(type(cohort) is dict and cohort.get("cohort_id") == "decision-pilot-development-v1"
             and cohort.get("contract_id") == views.CONTRACT_ID and type(cohort.get("trace_count")) is int
             and cohort["trace_count"] == 12 and cohort.get("final_cohort_generated") is False
             and type(cohort.get("traces")) is list and len(cohort["traces"]) == 12, "Invalid owned development cohort")
    traces = cohort["traces"]
    for trace in traces:
        evaluation.resolve_world(trace)
    identities = [trace["trace_id"] for trace in traces]
    _require(len(set(identities)) == 12, "Duplicate case identity")
    source_hashes = {name: _hash(artifacts[_source_role(name)]) for name in SOURCE_NAMES}
    cohort_hash = _hash(_canonical(cohort))
    _keys(report, REPORT_FIELDS, "complete development report")
    _equal({key: report[key] for key in ("schema_version", "contract_id", "cohort_id", "cohort_hash", "stage", "declared_case_count", "source_hashes")},
           {"schema_version": 1, "contract_id": views.CONTRACT_ID, "cohort_id": cohort["cohort_id"], "cohort_hash": cohort_hash,
            "stage": "exposed_development", "declared_case_count": 12, "source_hashes": source_hashes}, "Report declaration")
    _equal(report["limits"], {"program_seconds": 30, "normal_view_bytes": 2048, "lossless_view_bytes": 32768,
                              "worker_output_bytes": 65536}, "Fixed program limits")
    _equal(report["scope"], "Owned synthetic development only; retention and view systems compared together; no generalization or live authority claim", "Development scope")
    raw_journal = artifacts["journal"]
    _require(raw_journal.endswith(b"\n") and raw_journal.count(b"\n") == 98, "Journal must contain exactly 48 complete attempt pairs")
    journal = [_json(line) for line in raw_journal.splitlines()]
    _require(all(_canonical(item) + b"\n" == line for item, line in zip(journal, raw_journal.splitlines(keepends=True))), "Journal record is not canonical")
    _equal(journal[0], {"kind": "declared_run", "cohort_hash": cohort_hash, "source_hashes": source_hashes,
        "arms": [list(arm) for arm in ARMS], "case_ids": identities,
        "scope": "exposed development; only root may invoke the registered run"}, "Journal declaration")
    _require(type(report["arms"]) is list and len(report["arms"]) == 4, "Report must contain exactly four arms")
    checks = dict.fromkeys(CHECK_FIELDS, True)
    signatures, compact_arms, slot, accounted = {}, [], 0, 0.0
    for arm, (recipe, budget) in zip(report["arms"], ARMS):
        _keys(arm, {"recipe", "budget_bytes", "control", "rows", "summary", "strata"}, "reported arm")
        _equal([arm["recipe"], arm["budget_bytes"], arm["control"]], [recipe, budget, budget == 32768], "Fixed arm order")
        _require(type(arm["rows"]) is list and len(arm["rows"]) == 12, "Arm must contain every declared case")
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
    resources = report["resources"]
    _keys(resources, {"parent_wall_seconds", "model_calls", "external_program_spend", "agent_and_review_cost", "memory_bytes", "accounting"}, "Report resources")
    elapsed = _duration(resources["parent_wall_seconds"], "whole program duration")
    _require(accounted <= elapsed + 1e-9, "Attempt resource durations exceed enclosing program wall")
    _equal([resources["model_calls"], resources["external_program_spend"], resources["agent_and_review_cost"], resources["memory_bytes"]], [0, 0, None, None], "Program local accounting")
    _equal(resources["accounting"], "Child wall contains its stage times. Parent wall includes computation and attempt journaling through final source verification, excluding final report serialization/persistence. Do not add nested totals. Lossless arms are separate controls; retain caller wall time separately.", "Resource accounting scope")
    checks["program_deadline_met"] = elapsed <= 30
    _equal(report["checks"], checks, "Recomputed conformance checks")
    next_step = _next_step(checks, compact_arms)
    _equal(report["next_step"], next_step, "Development successor")
    _equal(journal[-1], {"kind": "run_terminal", "checks": checks, "next_step": next_step}, "Journal terminal")
    manifest = {role: _hash(raw) for role, raw in artifacts.items()}
    return {"schema_version": 1, "study_id": request["study_id"], "phase": "development", "status": "checked",
            "stage": "exposed_development", "origin": deepcopy(request["origin"]),
            "assessment_identity": {"schema_version": 1, "hash": _hash(_canonical(manifest))},
            "input_hashes": {role: manifest[role] for role in LIMITS}, "source_hashes": source_hashes,
            "counts": {"cases": 12, "arms": 4, "attempts": 48, "journal_records": 98},
            "arms": compact_arms, "checks": checks, "next_step": next_step,
            "resources": deepcopy(resources), "scope": report["scope"]}


def _check_artifacts(prepared):
    _keys(prepared, {"artifacts", "manifest", "report"}, "prepared decision study")
    roles = set(LIMITS) | {_source_role(name) for name in SOURCE_NAMES + ("decision_assessment.py",)}
    _keys(prepared["artifacts"], roles, "captured artifact")
    _keys(prepared["manifest"], roles, "captured manifest")
    total = 0
    for role, raw in prepared["artifacts"].items():
        _require(type(raw) is bytes and len(raw) <= LIMITS.get(role, MAX_SOURCE_BYTES), "Invalid bounded artifact bytes")
        _require(prepared["manifest"][role] == _hash(raw), "Captured artifact digest differs")
        total += len(raw)
    _require(total <= MAX_BUNDLE_BYTES, "Captured study exceeds aggregate byte bound")
    _require(len(set(prepared["manifest"].values())) == len(roles), "Captured artifact roles must contain distinct bytes")
    for role, raw in _current_sources().items():
        _require(prepared["artifacts"][role] == raw, "Captured study source changed")


def prepare_decision_study(path):
    """Read one fixed request and capture its bounded retained evidence once."""
    artifacts = {}
    try:
        path = Path(path)
        artifacts["request"] = _read_file(path, LIMITS["request"])
        request = _json(artifacts["request"])
        _request(request)
        paths = [path]
        for role, declared in request["paths"].items():
            source_path = Path(declared)
            if not source_path.is_absolute():
                source_path = path.parent / source_path
            paths.append(source_path)
            artifacts[role] = _read_file(source_path, LIMITS[role])
        _require(len({(item.stat().st_dev, item.stat().st_ino) for item in paths}) == len(paths), "Input roles alias the same file")
        artifacts.update(_current_sources())
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
    _require(sum(map(len, artifacts.values())) <= MAX_BUNDLE_BYTES, "Assessment output exceeds aggregate byte bound")
    return {"report": report, "artifacts": artifacts}


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
_CONSTANTS = tuple((name, deepcopy(globals()[name])) for name in ("SOURCE_NAMES", "ARMS", "LIMITS", "MAX_SOURCE_BYTES",
    "MAX_BUNDLE_BYTES", "CONTRACT_HASHES", "EXTRA_ROW_FIELDS", "CHECK_FIELDS", "REPORT_FIELDS", "RECEIPT_FIELDS", "TRANSPORT_ERRORS"))
_ERROR_IDENTITY = (DecisionStudyPreparationError, DecisionStudyPreparationError.__init__, DecisionStudyPreparationError.__init__.__code__)
