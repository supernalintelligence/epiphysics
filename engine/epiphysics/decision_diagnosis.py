"""Bounded diagnosis of accepted decision artifacts; never execute a candidate.

Preparation resolves immutable historical observations, not historical paths.
Only assessment computes the case table. Replay preparation and lineage checks
therefore do not repeat a successful diagnostic.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import decision_views as views
from . import store

IMPLEMENTATION_DEPENDENCIES = ((views.__name__, views.IMPLEMENTATION_CODE),
                               (store.__name__, store.IMPLEMENTATION_CODE))
PHASE = "information_limits_diagnosis"
STAGE = "retained_diagnostic"
CONTRACT_ID = "decision-information-diagnosis-v1"
MAX_REQUEST_BYTES = 32768
MAX_CONTRACT_BYTES = 65536
MAX_EVENT_BYTES = 1024 * 1024
MAX_PREFIX_BYTES = 8 * 1024 * 1024
MAX_PREFIX_EVENTS = 4096
MAX_SOURCE_BYTES = 131072
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 48 * 1024 * 1024
MAX_SECONDS = 10
ARMS = (("flat-recency-v1", 2048), ("task-proximity-v1", 2048),
        ("flat-recency-v1", 32768), ("task-proximity-v1", 32768))
ALLOCATION = {"late_visibility": 6, "visible_authority_changes": 4, "verification_dispute": 4,
              "duplicate_identity": 4, "retention_pressure": 4, "role_direction": 2}
SEMANTIC_ACTIONS = {"investigate_decision_information_limits", "repair_decision_information_diagnosis",
                    "review_unresolved_decision_evidence"}
NEXT_ACTIONS = {"repair_decision_information_diagnosis", "review_unresolved_decision_evidence",
                "prepare_dated_evidence_quality_protocol"}
TRANSITIONS = {"improvement_completed", "improvement_failed"}
SOURCE_NAMES = ("decision_diagnosis.py", "decision_views.py", "store.py")
C8_SOURCE_NAMES = ("decision_views.py", "decision_policy.py", "decision_evaluation.py", "decision_pilot.py",
                   "decision_assessment.py", "improvement.py")
C8_LIMITS = {"request": 16384, "cohort": 262144, "report": 16 * 1024 * 1024,
    "journal": 24 * 1024 * 1024, "decision_contract": 131072, "evaluation_contract": 131072,
    "registration": 65536, "custody": 65536, "origin_transition": 262144,
    "generator_source": MAX_SOURCE_BYTES, "caller_source": MAX_SOURCE_BYTES,
    "claim": 16384, "caller_receipt": 65536, "caller_stdout": 65537, "caller_stderr": 65537,
    **{"code:epiphysics." + name[:-3]: MAX_SOURCE_BYTES for name in C8_SOURCE_NAMES}}
SUPPLEMENTS = {"outer_execution", "custodian_process"}
CONTRACT = {"schema_version": 1, "contract_id": CONTRACT_ID, "phase": PHASE, "stage": STAGE,
    "cases": 24, "arms": 4, "attempts": 96, "journal_records": 194,
    "evidence_unit": "Accepted C8 case/arm rows; verification claims counted once per cohort/case/event identity",
    "axes": ["dated_availability", "bounded_retention", "verification_quality"],
    "accepted_effect_metric": "new accepted effects with NOT artifact_ready_valid; denominators: all cases, not-ready/invalid cases, all accepted effects",
    "verification_denominator": "distinct eligible operative exactly-bound verified verification claims with a bound retained outcome; separate case count",
    "unknown_rule": "Missing or insufficient evidence remains explicit; harms overlap and are never summed",
    "review_rule": "An accepted review continuation may prepare a protocol only with the identical verified nonempty unresolved identity/reason set; unknowns remain unresolved",
    "limits": {"request_bytes": MAX_REQUEST_BYTES, "prefix_bytes": MAX_PREFIX_BYTES, "prefix_events": MAX_PREFIX_EVENTS,
        "event_bytes": MAX_EVENT_BYTES, "output_bytes": MAX_OUTPUT_BYTES, "bundle_bytes": MAX_BUNDLE_BYTES,
        "diagnostic_seconds": MAX_SECONDS, "candidate_executions": 0, "new_cases": 0, "model_calls": 0,
        "external_spend": 0, "live_effects": False},
    "successors": sorted(NEXT_ACTIONS),
    "scope": "Retained synthetic engineering diagnosis; no new experiment, predictive lift, adoption or live authority"}
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_STORE_SOURCE = store.IMPLEMENTATION_SOURCE
_STORE_CLASS = store.Ledger
_STORE_METHODS = tuple((name, function, function.__code__) for name in ("open_readonly", "events", "get", "close")
    for function in (getattr(getattr(store.Ledger, name), "__func__", getattr(store.Ledger, name)),))
_STORE_INSTANT = (store.instant, store.instant.__code__)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("Nonfinite JSON number")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, RecursionError) as error:
        raise ValueError("Invalid bounded diagnosis JSON") from error


def _keys(value, expected, label):
    _require(type(value) is dict and set(value) == set(expected), "Invalid " + label + " fields")


def _equal(actual, expected, label):
    _require(_canonical(actual) == _canonical(expected), label + " differs")


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "Invalid digest")


def _identity(value):
    _keys(value, {"event_id", "event_hash"}, "event identity")
    _require(type(value["event_id"]) is str and 0 < len(value["event_id"]) <= 256, "Invalid event ID")
    _digest(value["event_hash"])


def _read(path, maximum):
    path = Path(path)
    _require(not path.is_symlink() and path.is_file() and path.stat().st_size <= maximum, "Input must be a bounded regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Input ceased to be a regular file")
        raw = stream.read(maximum + 1)
    _require(len(raw) <= maximum, "Input exceeds byte limit")
    return raw


def _role_limit(role):
    fixed = {"request": MAX_REQUEST_BYTES, "contract": MAX_CONTRACT_BYTES, "ledger_prefix": MAX_PREFIX_BYTES,
             "evidence_origin": MAX_EVENT_BYTES, "queue_parent": MAX_EVENT_BYTES,
             "failure_request": MAX_EVENT_BYTES, "failure_claim": MAX_EVENT_BYTES,
             "semantic_parent": MAX_EVENT_BYTES, "assessment_report": MAX_OUTPUT_BYTES, "diagnostic_table": MAX_OUTPUT_BYTES}
    if role in fixed:
        return fixed[role]
    if role.startswith("c8:") and role[3:] in C8_LIMITS:
        return C8_LIMITS[role[3:]]
    if role.startswith("observation:") and role[12:] in C8_LIMITS:
        return MAX_EVENT_BYTES
    if role in {"code:epiphysics." + name[:-3] for name in SOURCE_NAMES}:
        return MAX_SOURCE_BYTES
    if role.startswith("supplement:") and role[11:] in SUPPLEMENTS:
        return 65536
    return None


class PreparationError(ValueError):
    """Safely captured bounded evidence, without a checked diagnosis."""

    def __init__(self, message, artifacts):
        super().__init__(message)
        self.artifacts = {}
        total = 0
        for role, raw in artifacts.items():
            maximum = _role_limit(role)
            if maximum is not None and type(raw) is bytes and len(raw) <= maximum and total + len(raw) <= MAX_BUNDLE_BYTES:
                self.artifacts[role] = raw
                total += len(raw)


def _put(artifacts, role, raw):
    maximum = _role_limit(role)
    _require(maximum is not None and type(raw) is bytes and len(raw) <= maximum, "Invalid bounded artifact role")
    _require(sum(map(len, artifacts.values())) - len(artifacts.get(role, b"")) + len(raw) <= MAX_BUNDLE_BYTES,
             "Diagnosis bundle exceeds aggregate bound")
    artifacts[role] = raw


def _current_sources():
    path, raw, code = _SELF
    _require(IMPLEMENTATION_SOURCE == raw and IMPLEMENTATION_CODE is code and _read(path, MAX_SOURCE_BYTES) == raw,
             "Diagnosis source changed")
    _require(compile(raw, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) == code, "Diagnosis code differs")
    for name, function, original in _FUNCTION_CODES:
        _require(globals().get(name) is function and function.__code__ is original, "Diagnosis callable changed: " + name)
    for name, value in _CONSTANTS:
        _require(type(globals().get(name)) is type(value) and globals().get(name) == value, "Diagnosis constant changed: " + name)
    _require(PreparationError is _ERROR_IDENTITY[0] and PreparationError.__init__ is _ERROR_IDENTITY[1]
             and PreparationError.__init__.__code__ is _ERROR_IDENTITY[2], "Diagnosis error class changed")
    views.runtime_sources()
    _require(store.Ledger is _STORE_CLASS and store.IMPLEMENTATION_SOURCE == _STORE_SOURCE
             and _read(Path(store.__file__), MAX_SOURCE_BYTES) == _STORE_SOURCE, "Ledger implementation changed")
    _require(store.instant is _STORE_INSTANT[0] and store.instant.__code__ is _STORE_INSTANT[1], "Ledger clock parser changed")
    for name, function, code in _STORE_METHODS:
        current = getattr(store.Ledger, name)
        current = getattr(current, "__func__", current)
        _require(current is function and current.__code__ is code, "Ledger callable changed: " + name)
    return {"code:epiphysics." + name[:-3]: _read(path.parent / name, MAX_SOURCE_BYTES) for name in SOURCE_NAMES}


def _request(value):
    _keys(value, {"schema_version", "study_id", "phase", "origin", "ledger_path", "evidence_origin", "queue_parent", "paths", "supplemental_evidence"}, "diagnosis request")
    _equal([value["schema_version"], value["phase"]], [1, PHASE], "Diagnosis request phase")
    _require(type(value["study_id"]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value["study_id"]), "Invalid study ID")
    _keys(value["origin"], {"step_id"}, "origin")
    _require(type(value["origin"]["step_id"]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", value["origin"]["step_id"]), "Invalid queued step")
    _identity(value["evidence_origin"])
    _identity(value["queue_parent"])
    _keys(value["paths"], {"contract"}, "diagnosis paths")
    _require(type(value["supplemental_evidence"]) is dict and set(value["supplemental_evidence"]) <= SUPPLEMENTS, "Invalid supplemental roles")
    paths = [value["ledger_path"], value["paths"]["contract"]]
    for item in value["supplemental_evidence"].values():
        _keys(item, {"path", "sha256", "source"}, "supplement")
        _digest(item["sha256"])
        _require(type(item["source"]) is str and 0 < len(item["source"].encode()) <= 512, "Missing supplemental attribution")
        paths.append(item["path"])
    _require(all(type(path) is str and 0 < len(path.encode()) <= 4096 and "\0" not in path and Path(path).is_absolute() for path in paths),
             "Diagnosis locators must be bounded absolute paths")


def _event(event):
    _keys(event, {"seq", "id", "kind", "recorded_at", "body", "previous_hash", "hash"}, "ledger event")
    _require(type(event["seq"]) is int and event["seq"] > 0 and len(_canonical(event)) <= MAX_EVENT_BYTES, "Invalid bounded event")
    _digest(event["hash"])
    _digest(event["previous_hash"])
    payload = {key: event[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}
    _equal(event["hash"], _hash(_canonical(payload)), "Historical event digest")


def _prefix(events):
    _require(type(events) is list and 0 < len(events) <= MAX_PREFIX_EVENTS and len(_canonical(events)) <= MAX_PREFIX_BYTES,
             "Historical prefix exceeds bound")
    previous, seq, ids, latest_time = "0" * 64, 0, set(), None
    for event in events:
        _event(event)
        _require(event["seq"] > seq and event["id"] not in ids and event["previous_hash"] == previous, "Broken historical prefix")
        instant = store.instant(event["recorded_at"])
        _require(latest_time is None or instant >= latest_time, "Historical clock order differs")
        previous, seq, latest_time = event["hash"], event["seq"], instant
        ids.add(event["id"])
    return {event["id"]: event for event in events}


def _find(by_id, identity):
    _identity(identity)
    event = by_id.get(identity["event_id"])
    _require(event is not None and event["hash"] == identity["event_hash"], "Historical event identity is absent or changed")
    return event


def _origin_identity(event):
    body = event["body"]
    pilot = body["report"]["decision_pilot"]
    _require(event["kind"] == "improvement_completed" and body["result"] == "assessed"
             and pilot["phase"] == "fresh_comparison" and pilot["stage"] == "fresh_exploratory"
             and pilot["status"] == "checked" and body["next_step"]["action"] == "investigate_decision_information_limits"
             and pilot["next_step"]["action"] == "investigate_decision_information_limits"
             and pilot["checks"] and all(type(value) is bool and value for value in pilot["checks"].values()),
             "Evidence origin is not accepted C8 information-limits evidence")
    _equal(pilot["counts"], {"cases": 24, "arms": 4, "attempts": 96, "journal_records": 194}, "Accepted C8 counts")
    manifest = body["request"]["manifest"]
    _equal(body["assessment_identity"]["input_manifest"], manifest, "Accepted input manifest")
    identity = {"input_manifest": manifest, "decision_assessment_hash": pilot["assessment_identity"]["hash"]}
    _equal(body["assessment_identity"]["hash"], _hash(_canonical(identity)), "Accepted assessment identity")
    _equal(body["assessment_identity"]["decision_assessment_hash"], pilot["assessment_identity"]["hash"], "Accepted decision identity")
    declared = {key.removeprefix("decision-input:"): value for key, value in manifest.items() if key.startswith("decision-input:")}
    _keys(declared, C8_LIMITS, "accepted decision input manifest")
    for value in declared.values():
        _digest(value)
    _equal(pilot["assessment_identity"]["hash"], _hash(_canonical(declared)), "Accepted study artifact identity")
    for name in ("decision_views.py", "decision_policy.py", "decision_evaluation.py", "decision_pilot.py"):
        _equal(pilot["source_hashes"][name], declared["code:epiphysics." + name[:-3]], "Historical comparison implementation")
    return {"event_id": event["id"], "event_hash": event["hash"], "assessment_hash": body["assessment_identity"]["hash"],
            "decision_assessment_hash": pilot["assessment_identity"]["hash"], "input_manifest": declared}


def _observation(origin, by_id, role):
    full_role = "decision-input:" + role
    event = by_id.get(origin["body"]["input_observations"].get(full_role))
    _require(event is not None and event["kind"] == "observation" and event["seq"] < origin["seq"], "Accepted observation is absent or outside prefix")
    body = event["body"]
    _equal(body["source"], "improvement-input:" + full_role, "Accepted observation role")
    _equal(body["content_hash"], origin["body"]["request"]["manifest"][full_role], "Accepted observation content identity")
    _require(type(body["size"]) is int and 0 <= body["size"] <= C8_LIMITS[role], "Accepted observation size exceeds bound")
    return event


def _semantic_parent(parent, origin_identity):
    step = parent["body"]["next_step"]
    _require(step["state"] == "queued" and step["action"] in SEMANTIC_ACTIONS, "Parent does not own a semantic diagnosis step")
    if step["action"] == "investigate_decision_information_limits":
        _equal(_origin_identity(parent), origin_identity, "Initial C8 ownership")
        return None
    report = parent["body"]["report"]["decision_pilot"]
    _require(parent["kind"] == "improvement_completed" and parent["body"]["result"] == "assessed"
             and report["schema_version"] == 1 and report["contract_id"] == CONTRACT_ID
             and report["phase"] == PHASE and report["stage"] == STAGE and report["status"] == "checked"
             and report["next_step"]["action"] == step["action"], "Invalid checked diagnostic continuation parent")
    _equal(report["evidence_origin"], origin_identity, "Continuation C8 ancestry")
    identity = parent["body"]["assessment_identity"]
    manifest = parent["body"]["request"]["manifest"]
    _equal(identity["input_manifest"], manifest, "Prior diagnostic input manifest")
    _equal(identity["decision_assessment_hash"], report["assessment_identity"]["hash"], "Prior diagnostic identity")
    _equal(identity["hash"], _hash(_canonical({"input_manifest": manifest,
        "decision_assessment_hash": report["assessment_identity"]["hash"]})), "Prior assessment identity")
    declared = {key.removeprefix("decision-input:"): value for key, value in manifest.items() if key.startswith("decision-input:")}
    _equal(report["assessment_identity"]["hash"], _hash(_canonical(declared)), "Prior diagnostic artifact identity")
    _equal(report["input_hashes"], {role: value for role, value in declared.items() if not role.startswith("code:")},
           "Prior diagnostic report/input mapping")
    _equal(report["source_hashes"], {name: declared["code:epiphysics." + name[:-3]] for name in SOURCE_NAMES},
           "Prior diagnostic source mapping")
    for role, expected in origin_identity["input_manifest"].items():
        _equal(declared.get("c8:" + role), expected, "Prior diagnostic accepted C8 ancestry: " + role)
        _equal(report["input_hashes"].get("c8:" + role), expected, "Prior diagnostic reported C8 ancestry: " + role)
    return report["assessment_identity"]


def _lineage(request, artifacts, events):
    by_id = _prefix(events)
    origin = _find(by_id, request["evidence_origin"])
    parent = _find(by_id, request["queue_parent"])
    _equal(events[-1], parent, "Stable prefix endpoint")
    _equal(_json(artifacts["evidence_origin"]), origin, "Captured evidence origin")
    _equal(_json(artifacts["queue_parent"]), parent, "Captured queue parent")
    origin_identity = _origin_identity(origin)
    _require(origin["seq"] <= parent["seq"], "Evidence origin follows parent")
    step = parent["body"]["next_step"]
    _require(step["id"] == request["origin"]["step_id"] and step["state"] == "queued", "Request does not own captured queued step")
    if step["action"] in SEMANTIC_ACTIONS:
        previous = _semantic_parent(parent, origin_identity)
        return origin_identity, {"mode": "initial" if previous is None else "checked_continuation",
            "semantic_action": step["action"], "prior_diagnostic_identity": previous, "failed_event_id": None}
    _require(parent["kind"] == "improvement_failed" and step["action"] == "diagnose_failed_assessment", "Unsupported diagnosis queue action")
    claim = _json(artifacts["failure_claim"])
    semantic = _json(artifacts["semantic_parent"])
    prior = _json(artifacts["failure_request"])
    _request(prior)
    _equal(by_id.get(claim["id"]), claim, "Captured failed claim")
    _equal(by_id.get(semantic["id"]), semantic, "Captured semantic predecessor")
    _require(semantic["seq"] < claim["seq"] < parent["seq"] and claim["kind"] == "improvement_started"
             and claim["body"]["run_key"] == parent["body"]["run_key"], "Failed claim does not bind parent")
    _equal(claim["body"]["request"], parent["body"]["request"], "Failed request/claim identity")
    _equal(claim["body"]["claimed_step"], semantic["body"]["next_step"], "Original claimed semantic step")
    prior_transitions = [item for item in events if item["kind"] in TRANSITIONS and item["seq"] < claim["seq"]]
    _equal(prior_transitions[-1], semantic, "Original semantic queue owner")
    _equal(prior["queue_parent"], {"event_id": semantic["id"], "event_hash": semantic["hash"]}, "Failed request semantic parent")
    _equal(prior["evidence_origin"], request["evidence_origin"], "Failed request C8 origin")
    _equal(prior["origin"]["step_id"], semantic["body"]["next_step"]["id"], "Failed original step")
    _equal(parent["body"]["request"]["after_step"], prior["origin"]["step_id"], "Failed dispatcher step")
    expected_hash = parent["body"]["request"]["manifest"]["decision-input:request"]
    _equal(_hash(artifacts["failure_request"]), expected_hash, "Captured failed request bytes")
    matches = [item for item in events if item["kind"] == "observation" and claim["seq"] < item["seq"] < parent["seq"]
        and item["id"] == "improvement:" + parent["body"]["run_key"] + ":input:decision-input:request"
        and item["body"]["source"] == "improvement-input:decision-input:request" and item["body"]["content_hash"] == expected_hash]
    _require(len(matches) == 1 and matches[0]["body"]["size"] == len(artifacts["failure_request"]), "Failed request observation is not bound")
    previous = _semantic_parent(semantic, origin_identity)
    return origin_identity, {"mode": "failed_attempt_continuation", "semantic_action": semantic["body"]["next_step"]["action"],
        "prior_diagnostic_identity": previous, "failed_event_id": parent["id"], "failed_claim_id": claim["id"],
        "failed_request_sha256": expected_hash, "semantic_parent_id": semantic["id"]}


def _metadata(artifacts, manifest):
    request = _json(artifacts["request"])
    _request(request)
    _equal(_json(artifacts["contract"]), CONTRACT, "Fixed diagnosis contract")
    events = _json(artifacts["ledger_prefix"])
    origin_identity, ancestry = _lineage(request, artifacts, events)
    by_id = {event["id"]: event for event in events}
    origin = _find(by_id, request["evidence_origin"])
    expected_roles = {"request", "contract", "ledger_prefix", "evidence_origin", "queue_parent"}
    for role in C8_LIMITS:
        observation = _observation(origin, by_id, role)
        expected_roles.update({"c8:" + role, "observation:" + role})
        _equal(_json(artifacts["observation:" + role]), observation, "Captured historical observation")
        _require(_hash(artifacts["c8:" + role]) == observation["body"]["content_hash"]
                 and len(artifacts["c8:" + role]) == observation["body"]["size"], "Captured historical blob differs")
    if ancestry["mode"] == "failed_attempt_continuation":
        expected_roles.update({"failure_request", "failure_claim", "semantic_parent"})
    for name, declared in request["supplemental_evidence"].items():
        role = "supplement:" + name
        expected_roles.add(role)
        _equal(_hash(artifacts[role]), declared["sha256"], "Supplemental receipt identity")
    sources = _current_sources()
    for role, raw in sources.items():
        expected_roles.add(role)
        _require(artifacts[role] == raw, "Current diagnosis source differs")
    _keys(artifacts, expected_roles, "diagnosis artifacts")
    # The decoder's source must retain the accepted meaning of C8 view bytes.
    # No equality is required between current and historical helper/controller.
    _require(artifacts["c8:code:epiphysics.decision_views"] == sources["code:epiphysics.decision_views"], "Historical decoder version differs")
    return {"schema_version": 1, "contract_id": CONTRACT_ID, "study_id": request["study_id"], "phase": PHASE, "stage": STAGE,
        "status": "prepared", "origin": deepcopy(request["origin"]),
        "assessment_identity": {"schema_version": 1, "hash": _hash(_canonical(manifest))},
        "input_hashes": {key: manifest[key] for key in sorted(manifest) if not key.startswith("code:")},
        "source_hashes": {name: manifest["code:epiphysics." + name[:-3]] for name in SOURCE_NAMES},
        "counts": {"cases": 24, "arms": 4, "attempts": 96, "journal_records": 194},
        "evidence_origin": origin_identity, "queue_parent": deepcopy(request["queue_parent"]), "ancestry": ancestry,
        "supplemental_evidence": {name: {"sha256": value["sha256"], "source": value["source"],
            "scope": "Separately attributed local receipt; not an accepted C8 input"} for name, value in request["supplemental_evidence"].items()},
        "scope": CONTRACT["scope"]}


def _capture_failure(request, artifacts, events, ledger):
    parent = events[-1]
    if parent["body"]["next_step"]["action"] != "diagnose_failed_assessment":
        return
    _require(parent["kind"] == "improvement_failed", "Failure continuation requires an actual failed transition")
    run_key = parent["body"]["run_key"]
    claims = [event for event in events if event["kind"] == "improvement_started" and event["body"].get("run_key") == run_key]
    _require(len(claims) == 1, "Missing unique failed C9 claim")
    claim = claims[0]
    prior_transitions = [event for event in events if event["kind"] in TRANSITIONS and event["seq"] < claim["seq"]]
    _require(prior_transitions, "Missing original semantic queue parent")
    expected = parent["body"]["request"]["manifest"]["decision-input:request"]
    _digest(expected)
    observations = [event for event in events if event["kind"] == "observation"
        and event["id"] == "improvement:" + run_key + ":input:decision-input:request"]
    _require(len(observations) == 1 and observations[0]["body"]["content_hash"] == expected,
             "Missing captured failed C9 request; cannot invent one")
    _put(artifacts, "failure_request", _read(ledger.root / "blobs" / expected, MAX_EVENT_BYTES))
    _put(artifacts, "failure_claim", _canonical(claim))
    _put(artifacts, "semantic_parent", _canonical(prior_transitions[-1]))


def prepare_diagnosis(path):
    """Capture a fixed historical prefix and its accepted inputs, without diagnosis."""
    artifacts = {}
    started = time.monotonic()
    try:
        _put(artifacts, "request", _read(path, MAX_REQUEST_BYTES))
        request = _json(artifacts["request"])
        _request(request)
        _put(artifacts, "contract", _read(request["paths"]["contract"], MAX_CONTRACT_BYTES))
        _equal(_json(artifacts["contract"]), CONTRACT, "Fixed diagnosis contract")
        for role, raw in _current_sources().items():
            _put(artifacts, role, raw)
        ledger = store.Ledger.open_readonly(request["ledger_path"])
        try:
            ledger.db.execute("BEGIN")
            end = ledger.db.execute("SELECT seq FROM events WHERE id=?", (request["queue_parent"]["event_id"],)).fetchone()
            _require(end is not None, "Missing historical queue parent")
            bound = ledger.db.execute("SELECT COUNT(*),COALESCE(SUM(length(CAST(body AS BLOB))),0),COALESCE(MAX(length(CAST(body AS BLOB))),0) FROM events WHERE seq<=?", (end[0],)).fetchone()
            _require(0 < bound[0] <= MAX_PREFIX_EVENTS and bound[1] <= MAX_PREFIX_BYTES and bound[2] <= MAX_EVENT_BYTES,
                     "Historical prefix exceeds input bounds")
            events = []
            for row in ledger.db.execute("SELECT * FROM events WHERE seq<=? ORDER BY seq", (end[0],)):
                events.append({**dict(row), "body": _json(row["body"])})
            _put(artifacts, "ledger_prefix", _canonical(events))
            by_id = _prefix(events)
            origin = _find(by_id, request["evidence_origin"])
            parent = _find(by_id, request["queue_parent"])
            _origin_identity(origin)
            _put(artifacts, "evidence_origin", _canonical(origin))
            _put(artifacts, "queue_parent", _canonical(parent))
            for role in C8_LIMITS:
                observation = _observation(origin, by_id, role)
                _put(artifacts, "observation:" + role, _canonical(observation))
                blob = _read(ledger.root / "blobs" / observation["body"]["content_hash"], C8_LIMITS[role])
                _require(len(blob) == observation["body"]["size"] and _hash(blob) == observation["body"]["content_hash"], "Historical blob corruption")
                _put(artifacts, "c8:" + role, blob)
            _capture_failure(request, artifacts, events, ledger)
        finally:
            ledger.close()
        for name, item in request["supplemental_evidence"].items():
            _put(artifacts, "supplement:" + name, _read(item["path"], 65536))
        manifest = {role: _hash(raw) for role, raw in artifacts.items()}
        report = _metadata(artifacts, manifest)
        _require(time.monotonic() - started <= MAX_SECONDS, "Diagnosis preparation exceeded time budget")
        return {"artifacts": artifacts, "manifest": manifest, "report": report}
    except (ValueError, OSError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError, sqlite3.Error) as error:
        raise PreparationError(str(error), artifacts) from error


def check_prepared_diagnosis(prepared):
    """Verify captured identities and metadata; never recompute the case diagnosis."""
    _keys(prepared, {"artifacts", "manifest", "report"}, "prepared diagnosis")
    _keys(prepared["manifest"], prepared["artifacts"], "diagnosis manifest")
    total = 0
    for role, raw in prepared["artifacts"].items():
        maximum = _role_limit(role)
        _require(maximum is not None and type(raw) is bytes and len(raw) <= maximum, "Invalid captured diagnosis artifact")
        _equal(_hash(raw), prepared["manifest"][role], "Captured diagnosis digest")
        total += len(raw)
    _require(total <= MAX_BUNDLE_BYTES, "Captured diagnosis exceeds bundle bound")
    _equal(prepared["report"], _metadata(prepared["artifacts"], prepared["manifest"]), "Prepared diagnosis metadata")


def validate_lineage(prepared, actual_events, after_step):
    """Compare captured ancestry with the caller's authoritative locked event view."""
    check_prepared_diagnosis(prepared)
    request = _json(prepared["artifacts"]["request"])
    _equal(after_step, request["origin"]["step_id"], "Current requested step")
    captured = _json(prepared["artifacts"]["ledger_prefix"])
    actual_prefix = [event for event in actual_events if event["seq"] <= captured[-1]["seq"]]
    _equal(actual_prefix, captured, "Authoritative historical prefix")
    transitions = [event for event in actual_events if event["kind"] in TRANSITIONS]
    _require(transitions and transitions[-1]["id"] == request["queue_parent"]["event_id"]
             and transitions[-1]["hash"] == request["queue_parent"]["event_hash"], "Stale or unrelated immediate queue predecessor")
    _equal(transitions[-1]["body"]["next_step"]["id"], after_step, "Authoritative queued step")


def _ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None}


def _flags(row):
    facts, effect = row["facts"], row["effect_receipt"]
    _require(type(row["proposal_valid"]) is bool, "Invalid accepted proposal-valid flag")
    for name in ("world_authorized", "world_duplicate", "artifact_ready_valid", "world_opportunity", "visible_actionable_opportunity", "decision_within_deadline"):
        _require(type(facts[name]) is bool, "Invalid accepted world flag")
    _equal(facts["world_opportunity"], facts["world_authorized"] and not facts["world_duplicate"] and facts["artifact_ready_valid"], "Accepted opportunity definition")
    _equal(facts["visible_actionable_opportunity"], facts["world_opportunity"] and row["reference_proposal"]["action"] == "release", "Accepted visible opportunity")
    release = row["proposal_valid"] and row["proposal"]["action"] == "release"
    hold = row["proposal_valid"] and row["proposal"]["action"] == "hold"
    success = bool(release and facts["world_opportunity"] and effect["status"] == "accepted")
    _require(type(effect["new_effects"]) is int and effect["new_effects"] in (0, 1), "Invalid accepted effect count")
    _equal(effect["new_effects"], int(effect["status"] == "accepted"), "Accepted effect status/count")
    unauthorized = bool(release and not facts["world_authorized"])
    duplicate = bool(release and facts["world_duplicate"])
    flags = {"valid_timely_release": int(success), "observable_opportunity_completion": int(success and facts["visible_actionable_opportunity"]),
        "unauthorized_release_proposals_all": int(unauthorized), "unauthorized_release_proposals_forbidden": int(unauthorized),
        "duplicate_release_proposals_all": int(duplicate), "duplicate_release_proposals_attempts": int(duplicate),
        "invalid_artifact_release_proposals": int(release and not facts["artifact_ready_valid"]),
        "evidence_unjustified_release_proposals": int(release and row["reference_proposal"]["action"] == "hold"),
        "hold_rate": int(hold), "missed_world_opportunities": int(facts["world_opportunity"] and not success),
        "missed_observable_opportunities": int(facts["visible_actionable_opportunity"] and not success),
        "valid_output_completion": int(row["proposal_valid"]),
        "duplicate_effects": max(0, effect["new_effects"] - int(not facts["world_duplicate"])),
        "unauthorized_effects": int(effect["new_effects"] > 0 and not facts["world_authorized"])}
    _equal(row["metric_flags"], flags, "Retained metric flags")
    return flags


def _summary(rows):
    counts = {"cases": len(rows), "world_opportunities": sum(row["facts"]["world_opportunity"] for row in rows),
        "visible_actionable_opportunities": sum(row["facts"]["visible_actionable_opportunity"] for row in rows),
        "forbidden_cases": sum(not row["facts"]["world_authorized"] for row in rows),
        "duplicate_opportunity_cases": sum(row["facts"]["world_duplicate"] for row in rows),
        "ordinary_attempts": sum(not row["facts"]["world_duplicate"] for row in rows),
        "not_ready_or_invalid_cases": sum(not row["facts"]["artifact_ready_valid"] for row in rows),
        "failed_attempts": sum(not row["proposal_valid"] for row in rows),
        "release_proposals": sum(row["proposal_valid"] and row["proposal"]["action"] == "release" for row in rows),
        "hold_outputs": sum(row["proposal_valid"] and row["proposal"]["action"] == "hold" for row in rows)}
    metric_names = set(rows[0]["metric_flags"]) if rows else {
        "valid_timely_release", "observable_opportunity_completion", "unauthorized_release_proposals_all",
        "unauthorized_release_proposals_forbidden", "duplicate_release_proposals_all", "duplicate_release_proposals_attempts",
        "invalid_artifact_release_proposals", "evidence_unjustified_release_proposals", "hold_rate", "missed_world_opportunities",
        "missed_observable_opportunities", "valid_output_completion", "duplicate_effects", "unauthorized_effects"}
    denominators = dict.fromkeys(metric_names, len(rows))
    for name in ("valid_timely_release", "missed_world_opportunities"):
        denominators[name] = counts["world_opportunities"]
    for name in ("observable_opportunity_completion", "missed_observable_opportunities"):
        denominators[name] = counts["visible_actionable_opportunities"]
    denominators["unauthorized_release_proposals_forbidden"] = counts["forbidden_cases"]
    denominators["duplicate_release_proposals_attempts"] = counts["duplicate_opportunity_cases"]
    effects = {}
    for row in rows:
        entry = effects.setdefault(row["release_key"], {"attempts": 0, "new_effects": 0, "duplicate_effects": 0})
        entry["attempts"] += 1
        entry["new_effects"] += row["effect_receipt"]["new_effects"]
        entry["duplicate_effects"] += row["metric_flags"]["duplicate_effects"]
    return {"schema_version": 1, "evaluation_contract_id": "release-hold-evaluation-v1", "case_count": len(rows), "counts": counts,
        "metrics": {name: _ratio(sum(row["metric_flags"][name] for row in rows), denominators[name]) for name in sorted(metric_names)},
        "effects_by_release_key": effects,
        "effect_scope": "Each case starts from its independent stipulated state; equal keys across cases do not share effects."}


def _bound(event, task):
    roles = {"grant": ("requester", "requester", "delegate"), "revoke": ("requester", "requester", "delegate"),
        "delivery_claim": ("provider", "provider", "artifact_id"), "verification": ("requester", "requester", "artifact_id"),
        "dispute_open": ("requester", "requester", "obligation_id"), "dispute_close": ("requester", "requester", "obligation_id"),
        "release_committed": ("requester", "delegate", "provider")}
    role = roles.get(event["kind"])
    return role is not None and event["obligation_id"] == task["obligation_id"] and all(event[key] == task[name] for key, name in zip(("issuer", "subject", "object"), role))


def _case_evidence(trace, cohort_hash):
    task = trace["task"]
    outcome = trace["later_outcome"]
    _require(type(outcome["artifact_valid"]) is bool, "Invalid stipulated artifact validity")
    binding = outcome["artifact_id"] == task["artifact_id"] and outcome["artifact_sha256"] == task["artifact_sha256"]
    completed = views.seconds(outcome["completed_at"]) <= views.seconds(trace["decision_at"])
    dated, claims = [], []
    for event in trace["events"]:
        visible = event["obligation_id"] == task["obligation_id"] and views.seconds(event["observed_at"]) <= views.seconds(trace["cutoff"])
        effective = views.seconds(event["effective_at"]) <= views.seconds(trace["decision_at"])
        bound = _bound(event, task)
        identity = [cohort_hash, trace["trace_id"], event["event_id"]]
        item = {"identity": identity, "kind": event["kind"], "issuer": event["issuer"], "subject": event["subject"], "object": event["object"],
            "obligation_id": event["obligation_id"], "reference": event["reference"], "artifact_sha256": event["artifact_sha256"],
            "authentication": event["authentication"], "verdict": event["verdict"], "observed_at": event["observed_at"],
            "effective_at": event["effective_at"], "captured_at": None, "visible_at_cutoff": visible,
            "effective_at_decision": effective, "observer_operative": visible and effective, "role_binding_matches": bound,
            "artifact_digest_matches": event["artifact_sha256"] == task["artifact_sha256"],
            "timing_basis": "Synthetic source declarations; no external domain-event capture witness"}
        dated.append(item)
        if (event["kind"] == "verification" and visible and effective and bound and event["authentication"] == "verified"
                and event["artifact_sha256"] == task["artifact_sha256"]):
            claims.append({"identity": identity, "case_id": trace["trace_id"], "verdict": event["verdict"],
                "reference": event["reference"], "revision_semantics": "Not established by the C8 contract; preserve distinct records",
                "outcome_bound": binding, "stipulated_artifact_valid": outcome["artifact_valid"] if binding else None,
                "completed_by_decision": completed if binding else None,
                "disagrees_with_stipulated_validity": (event["verdict"] == "pass") != outcome["artifact_valid"] if binding else None,
                "positive_claim_invalid_artifact": event["verdict"] == "pass" and not outcome["artifact_valid"] if binding else None})
    return dated, claims, {"artifact_binding_matches": binding, "stipulated_artifact_valid": outcome["artifact_valid"],
        "completed_by_decision": completed, "outcome_revealed_at": outcome["revealed_at"],
        "outcome_available_at_decision": views.seconds(outcome["revealed_at"]) <= views.seconds(trace["cutoff"]),
        "truth_basis": outcome["basis"]}


def _retention(trace, row, recipe, budget):
    bundle = views.prepare_decision_input(trace["events"], trace["task"], trace["cutoff"], trace["decision_at"])
    _equal(row["input_hash"], bundle["input_hash"], "Retained public input identity")
    _equal([row["source_hash"], row["source_bytes"], row["header_bytes"]],
           [_hash(bundle["event_tape_bytes"]), len(bundle["event_tape_bytes"]), len(bundle["header_bytes"])], "Retained public provenance")
    _require(row["proposal_valid"] is True and type(row["view"]) is str, "Accepted all-valid C8 row lacks its view/proposal")
    view = row["view"].encode()
    verified = views.validate_decode_view(bundle["header_bytes"], bundle["event_tape_bytes"], view, budget_bytes=budget)
    _equal(_json(view)["arm"], recipe, "Retained view recipe")
    _equal([row["view_hash"], row["view_bytes"], row["complete"], row["provenance_valid"]],
           [_hash(view), len(view), verified.complete, True], "Retained view receipt")
    eligible = {event["event_id"] for event in trace["events"] if event["kind"] in views.POLICY_KINDS
        and event["obligation_id"] == trace["task"]["obligation_id"] and views.seconds(event["observed_at"]) <= views.seconds(trace["cutoff"])}
    retained = {event["event_id"] for event in verified.events if event["kind"] in views.POLICY_KINDS}
    _equal(row["proposal"]["support_event_ids"], sorted(retained), "Retained proposal support identities")
    _equal(row["reference_proposal"]["support_event_ids"], sorted(eligible), "Accepted full-visible reference identities")
    return {"eligible_policy_event_ids": sorted(eligible), "retained_policy_event_ids": sorted(retained),
        "omitted_policy_event_ids": sorted(eligible - retained), "complete": verified.complete,
        "view_bytes": len(view), "view_hash": row["view_hash"], "input_hash": bundle["input_hash"]}


def _attribution(row, retention, dated, claims, lossless_success):
    facts, flags = row["facts"], row["metric_flags"]
    labels, unresolved = [], []
    hidden = [event for event in dated if not event["visible_at_cutoff"] and event["effective_at_decision"]
              and event["role_binding_matches"] and event["authentication"] == "verified"]
    if flags["missed_observable_opportunities"]:
        demonstrated = (row["reference_proposal"]["action"] == "release" and lossless_success
            and row["proposal"]["action"] == "hold" and row["proposal"]["reason"] == "incomplete_evidence"
            and not retention["complete"] and bool(retention["omitted_policy_event_ids"]))
        (labels if demonstrated else unresolved).append("bounded_retention_loss" if demonstrated else "observable_miss_without_supported_retention_attribution")
    elif flags["missed_world_opportunities"]:
        reason = row["reference_proposal"]["reason"]
        if reason == "authority_absent_or_revoked" and any(event["kind"] == "grant" and event["identity"][2] in facts["active_grant_ids"] for event in hidden):
            labels.append("world_authority_unavailable_at_cutoff")
        elif reason == "missing_verification" and any(event["kind"] == "verification" and event["verdict"] == "pass"
                and event["artifact_digest_matches"] for event in hidden):
            labels.append("verification_unavailable_at_cutoff")
        else:
            unresolved.append("world_opportunity_without_full_visible_release:" + reason)
    if flags["unauthorized_release_proposals_all"]:
        active_visible = [event for event in dated if event["kind"] == "grant" and event["observer_operative"]
            and event["role_binding_matches"] and event["authentication"] == "verified"]
        conflict = any((event["kind"] == "dispute_open" and event["identity"][2] in facts["open_dispute_ids"])
            or (event["kind"] == "revoke" and any(event["reference"] in (None, grant["identity"][2])
                and views.seconds(event["effective_at"]) >= views.seconds(grant["effective_at"])
                and grant["identity"][2] not in facts["active_grant_ids"] for grant in active_visible)) for event in hidden)
        (labels if conflict else unresolved).append("authority_evidence_differs_across_cutoff")
    if flags["duplicate_release_proposals_all"]:
        (labels if any(event["kind"] == "release_committed" and event["reference"] == row["release_key"]
            and event["artifact_digest_matches"] for event in hidden) else unresolved).append("prior_release_unavailable_at_cutoff")
    if flags["invalid_artifact_release_proposals"]:
        if any(claim["positive_claim_invalid_artifact"] is True for claim in claims):
            labels.append("positive_verification_disagrees_with_stipulated_quality")
        else:
            unresolved.append("artifact_not_ready_without_supported_verification_validity_attribution")
    if flags["evidence_unjustified_release_proposals"]:
        unresolved.append("release_lacks_full_visible_reference_justification")
    return {"supported_labels": labels, "unresolved": unresolved,
            "causal_scope": "Nonexclusive retained-evidence attribution; no single-record necessity or representation superiority claim"}


def _next_step(checks, unresolved, gap_review=None):
    if not all(checks.values()):
        action, reason = "repair_decision_information_diagnosis", "Checked diagnostic conformance failed; retain its evidence before repair"
    elif unresolved and not (gap_review and gap_review["unchanged_verified_gap_set"]):
        action, reason = "review_unresolved_decision_evidence", "Retained evidence leaves explicit attribution gaps; review those identities without rerunning candidates"
    elif unresolved:
        action, reason = "prepare_dated_evidence_quality_protocol", "Verified retained gaps remain unchanged and unresolved; prepare a dated evidence-quality protocol to address the missing evidence"
    else:
        action, reason = "prepare_dated_evidence_quality_protocol", "Retained diagnosis reconciles the cases; prepare one dated evidence-quality protocol without capture or execution"
    return {"action": action, "reason": reason, "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "engineering diagnostic completeness; no empirical or predictive lift"}


def _gap_review(prepared, unresolved):
    """A repeated verified gap prepares evidence collection; it does not resolve it."""
    if prepared["report"]["ancestry"]["semantic_action"] != "review_unresolved_decision_evidence":
        return None
    artifacts = prepared["artifacts"]
    parent = _json(artifacts["semantic_parent"] if prepared["report"]["ancestry"]["mode"] == "failed_attempt_continuation"
                   else artifacts["queue_parent"])
    previous = parent["body"]["report"]["decision_pilot"]
    old = previous["diagnosis"]["unresolved"]
    _require(type(old) is list and old, "Prior accepted review lacks explicit unresolved evidence")
    old_ids = []
    for item in old:
        _keys(item, {"case_id", "arm", "budget_bytes", "reasons"}, "prior unresolved record")
        _require(type(item["reasons"]) is list and item["reasons"] and all(type(reason) is str for reason in item["reasons"]),
                 "Prior unresolved record lacks reasons")
        old_ids.append((item["case_id"], item["arm"], item["budget_bytes"]))
    _require(len(set(old_ids)) == len(old_ids), "Prior review repeats an attempt identity")
    same = _canonical(old) == _canonical(unresolved)
    return {"prior_diagnostic_identity": deepcopy(previous["assessment_identity"]),
        "prior_unresolved_sha256": _hash(_canonical(old)), "current_unresolved_sha256": _hash(_canonical(unresolved)),
        "unchanged_verified_gap_set": same,
        "resolution": "Unknowns remain unknown; no retained record supplies the missing evidence" if same else
            "The unresolved identity/reason set changed; review the changed evidence before protocol preparation",
        "required_evidence": "A dated, independently checkable artifact acceptance result bound to exact content, actor roles and cutoff",
        "permission": "Protocol preparation only; no capture, comparison, spending or live effect"}


def _output_checks(table, dated_cases, arms, baseline, cohort):
    """Check assembled diagnostic outputs separately from accepted-input integrity."""
    source_rows = [row for arm in baseline["arms"] for row in arm["rows"]]
    identities = [(row["case_id"], row["arm"], row["budget_bytes"]) for row in table]
    expected = [(trace["trace_id"], recipe, budget) for recipe, budget in ARMS for trace in cohort["traces"]]
    cohort_hash = _hash(_canonical(cohort))
    scoped = (len(table) == 96 and identities == expected and len(set(identities)) == 96
        and all(row["independent_effect_scope"] == [cohort_hash, row["case_id"], row["release_key"]] for row in table))
    preserved = len(table) == len(source_rows) and all(
        all(_canonical(row[name]) == _canonical(original[name]) for name in
            ("facts", "proposal", "reference_proposal", "effect_receipt", "metric_flags", "release_key"))
        and row["retention"]["input_hash"] == original["input_hash"]
        and row["retention"]["view_hash"] == original["view_hash"]
        for row, original in zip(table, source_rows))
    dates = len(dated_cases) == len(cohort["traces"]) and all(
        case["case_id"] == trace["trace_id"] and case["cutoff"] == trace["cutoff"]
        and case["decision_at"] == trace["decision_at"] and _canonical(case["task"]) == _canonical(trace["task"])
        and len(case["events"]) == len(trace["events"])
        and all(event["identity"] == [cohort_hash, trace["trace_id"], original["event_id"]]
            and event["observed_at"] == original["observed_at"] and event["effective_at"] == original["effective_at"]
            and event["captured_at"] is None for event, original in zip(case["events"], trace["events"]))
        for case, trace in zip(dated_cases, cohort["traces"]))
    metrics = len(arms) == 4 and all(
        (arm["recipe"], arm["budget_bytes"], arm["control"]) == (recipe, budget, budget == 32768)
        and _canonical(arm["summary"]) == _canonical(original["summary"])
        and all(sum(row["metric_flags"][name] for row in table if (row["arm"], row["budget_bytes"]) == (recipe, budget))
            == arm["summary"]["metrics"][name]["numerator"] for name in arm["summary"]["metrics"])
        for (recipe, budget), arm, original in zip(ARMS, arms, baseline["arms"]))
    return {"accepted_attempts_reconciled": scoped, "historical_metrics_preserved": metrics,
            "public_provenance_and_references_preserved": preserved, "dated_evidence_separated": dates}


def _diagnose(prepared):
    """The only case-table computation; not used by preparation or replay checks."""
    artifacts = prepared["artifacts"]
    cohort, baseline = _json(artifacts["c8:cohort"]), _json(artifacts["c8:report"])
    accepted = _json(artifacts["evidence_origin"])["body"]["report"]["decision_pilot"]
    _equal([cohort["cohort_id"], cohort["trace_count"], cohort["status"], cohort["final_cohort_generated"]],
           ["decision-pilot-fresh-v1", 24, "fresh_exploratory", True], "Accepted fixed cohort")
    traces = cohort["traces"]
    _require(type(traces) is list and len(traces) == 24 and len({trace["trace_id"] for trace in traces}) == 24, "Invalid complete cohort identities")
    _equal({name: sum(trace["mechanism"] == name for trace in traces) for name in {trace["mechanism"] for trace in traces}}, ALLOCATION, "Fixed case allocation")
    cohort_hash = _hash(_canonical(cohort))
    _equal([baseline["cohort_hash"], baseline["cohort_id"], baseline["stage"], baseline["declared_case_count"]],
           [cohort_hash, cohort["cohort_id"], "fresh_exploratory", 24], "Historical report declaration")
    _equal(baseline["checks"], accepted["checks"], "Accepted historical conformance")
    _equal(baseline["source_hashes"], accepted["source_hashes"], "Accepted historical source identities")
    _equal(baseline["next_step"], accepted["next_step"], "Accepted historical successor")
    _require(type(baseline["arms"]) is list and len(baseline["arms"]) == 4, "Missing fixed arms")
    journal_raw = artifacts["c8:journal"]
    _require(journal_raw.endswith(b"\n") and journal_raw.count(b"\n") == 194, "Incomplete retained journal")
    journal = [_json(line) for line in journal_raw.splitlines()]
    _require(all(_canonical(item) + b"\n" == line for item, line in zip(journal, journal_raw.splitlines(keepends=True))), "Noncanonical retained journal")
    _equal(journal[0], {"kind": "declared_run", "cohort_hash": cohort_hash, "source_hashes": baseline["source_hashes"],
        "arms": [list(arm) for arm in ARMS], "case_ids": [trace["trace_id"] for trace in traces],
        "scope": "fresh exploratory comparison; only root may invoke the registered run"}, "Historical journal declaration")
    _equal(journal[-1], {"kind": "run_terminal", "checks": baseline["checks"], "next_step": baseline["next_step"]}, "Historical terminal")
    table, dated_cases, verification_claims, arms, slot = [], [], [], [], 0
    case_evidence = []
    for trace in traces:
        dated, claims, quality = _case_evidence(trace, cohort_hash)
        case_evidence.append((dated, claims, quality))
        dated_cases.append({"case_id": trace["trace_id"], "mechanism": trace["mechanism"], "cutoff": trace["cutoff"],
            "decision_at": trace["decision_at"], "deadline": trace["task"]["deadline"], "task": deepcopy(trace["task"]),
            "events": dated, "artifact_quality": quality})
        verification_claims.extend(claims)
    for arm_index, ((recipe, budget), arm) in enumerate(zip(ARMS, baseline["arms"])):
        _equal([arm["recipe"], arm["budget_bytes"], arm["control"]], [recipe, budget, budget == 32768], "Retained arm identity")
        _require(type(arm["rows"]) is list and len(arm["rows"]) == 24, "Every arm must retain24 rows")
        arm_table = []
        for case_index, (trace, row) in enumerate(zip(traces, arm["rows"])):
            _equal([row["case_id"], row["mechanism"], row["arm"], row["budget_bytes"]],
                   [trace["trace_id"], trace["mechanism"], recipe, budget], "Retained case/arm order")
            flags = _flags(row)
            retention = _retention(trace, row, recipe, budget)
            _equal(journal[1 + slot * 2], {"kind": "worker_returned", "case_id": trace["trace_id"], "recipe": recipe,
                "budget_bytes": budget, "input_hash": row["input_hash"], "receipt": row["worker_receipt"]}, "Historical worker slot")
            _equal(journal[2 + slot * 2], {"kind": "attempt_evaluated", "row": row}, "Historical evaluated slot")
            slot += 1
            dated, claims, quality = case_evidence[case_index]
            _equal(row["artifact_outcome"], trace["later_outcome"], "Retained artifact adjudication")
            _equal(row["facts"]["artifact_ready_valid"], quality["artifact_binding_matches"] and quality["stipulated_artifact_valid"] and quality["completed_by_decision"], "Retained artifact readiness components")
            lossless_success = all(baseline["arms"][index]["rows"][case_index]["metric_flags"]["valid_timely_release"] == 1 for index in (2, 3))
            attribution = _attribution(row, retention, dated, claims, lossless_success)
            item = {"case_id": row["case_id"], "mechanism": row["mechanism"], "arm": recipe, "budget_bytes": budget,
                "release_key": row["release_key"], "independent_effect_scope": [cohort_hash, row["case_id"], row["release_key"]],
                "facts": deepcopy(row["facts"]), "proposal": deepcopy(row["proposal"]), "reference_proposal": deepcopy(row["reference_proposal"]),
                "effect_receipt": deepcopy(row["effect_receipt"]), "metric_flags": flags, "retention": retention,
                "artifact_quality": quality, "attribution": attribution}
            table.append(item)
            arm_table.append(item)
        summary = _summary(arm["rows"])
        _equal(arm["summary"], summary, "Historical arm totals")
        strata = {name: _summary([row for row in arm["rows"] if row["mechanism"] == name]) for name in sorted(ALLOCATION)}
        _equal(arm["strata"], strata, "Historical mechanism totals")
        _equal(accepted["arms"][arm_index], {"recipe": recipe, "budget_bytes": budget, "control": budget == 32768,
            "summary": summary, "strata": strata}, "Accepted checked arm totals")
        bad_effects = sum(row["effect_receipt"]["new_effects"] for row in arm["rows"] if not row["facts"]["artifact_ready_valid"])
        effects = sum(row["effect_receipt"]["new_effects"] for row in arm["rows"])
        supplement = {"accepted_not_ready_or_invalid_effects": {"all_cases": _ratio(bad_effects, 24),
            "not_ready_or_invalid_cases": _ratio(bad_effects, summary["counts"]["not_ready_or_invalid_cases"]), "accepted_effects": _ratio(bad_effects, effects)},
            "demonstrated_bounded_retention_losses": sum("bounded_retention_loss" in row["attribution"]["supported_labels"] for row in arm_table),
            "world_opportunities_without_visible_release": sum(row["facts"]["world_opportunity"] and not row["facts"]["visible_actionable_opportunity"] for row in arm_table),
            "unresolved_attribution_rows": sum(bool(row["attribution"]["unresolved"]) for row in arm_table)}
        arms.append({"recipe": recipe, "budget_bytes": budget, "control": budget == 32768, "summary": summary, "diagnosis": supplement})
    pairing = {"both": [], "flat_only": [], "relational_only": [], "neither": []}
    for left, right in zip(table[:24], table[24:48]):
        a, b = left["metric_flags"]["valid_timely_release"], right["metric_flags"]["valid_timely_release"]
        pairing["both" if a and b else "flat_only" if a else "relational_only" if b else "neither"].append(left["case_id"])
    paired = {"case_ids": pairing, "counts": {name: len(ids) for name, ids in pairing.items()},
        "net_relational_valid_releases": len(pairing["relational_only"]) - len(pairing["flat_only"])}
    _equal(paired["net_relational_valid_releases"], arms[1]["summary"]["metrics"]["valid_timely_release"]["numerator"] - arms[0]["summary"]["metrics"]["valid_timely_release"]["numerator"], "Paired release reconciliation")
    adjudicated = [claim for claim in verification_claims if claim["outcome_bound"]]
    positive = [claim for claim in adjudicated if claim["verdict"] == "pass"]
    verification = {"eligible_operative_bound_verified_claims": len(verification_claims), "adjudicated_claims": len(adjudicated),
        "cases_with_adjudicated_claims": len({claim["case_id"] for claim in adjudicated}), "unknown_outcome_claims": len(verification_claims) - len(adjudicated),
        "verdict_vs_stipulated_validity_disagreement": _ratio(sum(claim["disagrees_with_stipulated_validity"] for claim in adjudicated), len(adjudicated)),
        "positive_claim_invalid_artifact": _ratio(sum(claim["positive_claim_invalid_artifact"] for claim in positive), len(positive)),
        "unit": "Distinct cohort/case/event identities counted once, not once per arm; source authenticity is not truth"}
    unresolved = [{"case_id": row["case_id"], "arm": row["arm"], "budget_bytes": row["budget_bytes"],
        "reasons": row["attribution"]["unresolved"]} for row in table if row["attribution"]["unresolved"]]
    checks = _output_checks(table, dated_cases, arms, baseline, cohort)
    gap_review = _gap_review(prepared, unresolved)
    detail = {"schema_version": 1, "contract_id": CONTRACT_ID, "cases": dated_cases, "attempts": table,
              "verification_claims": verification_claims, "paired": paired, "unresolved": unresolved}
    report = deepcopy(prepared["report"])
    report.update(status="checked", arms=arms, checks=checks, next_step=_next_step(checks, unresolved, gap_review),
        diagnosis={"paired": paired, "verification": verification, "unresolved_attribution_rows": len(unresolved),
            "unresolved": unresolved, "gap_review": gap_review,
            "conformance_failures": [name for name, passed in checks.items() if not passed],
            "attribution_coverage": _ratio(96 - len(unresolved), 96),
            "detail_sha256": _hash(_canonical(detail)), "detail_bytes": len(_canonical(detail)),
            "interpretation": "Engineering reconciliation of exposed synthetic evidence; no new performance or predictive measurement"},
        resources={"diagnostic_seconds_limit": MAX_SECONDS, "diagnostic_wall_seconds": None, "decision_candidate_executions": 0,
            "new_cases": 0, "model_calls": 0, "external_program_spend": 0, "memory_bytes": None,
            "accounting": "Decision comparison execution only; other controller conformance probes and reviewer resources are not measured here; caller retains assessment wall separately"})
    return report, detail


def assess_prepared_diagnosis(prepared):
    """Compute a separate checked report and bounded detail artifact, never mutate inputs."""
    started = time.monotonic()
    check_prepared_diagnosis(prepared)
    try:
        report, detail = _diagnose(prepared)
        artifacts = dict(prepared["artifacts"])
        # Both output artifacts together are bounded to one MiB.
        report_raw, detail_raw = _canonical(report), _canonical(detail)
        _require(len(report_raw) + len(detail_raw) <= MAX_OUTPUT_BYTES, "Diagnostic output exceeds bound")
        _require(sum(map(len, artifacts.values())) + len(report_raw) + len(detail_raw) <= MAX_BUNDLE_BYTES, "Diagnostic output exceeds bundle bound")
        _current_sources()
        elapsed = time.monotonic() - started
        _require(elapsed <= MAX_SECONDS, "Diagnostic exceeded time budget")
        artifacts["assessment_report"] = report_raw
        artifacts["diagnostic_table"] = detail_raw
        return {"report": report, "artifacts": artifacts, "actual_resources": {"diagnostic_elapsed_seconds": elapsed}}
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError) as error:
        raise PreparationError(str(error), prepared["artifacts"]) from error


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
_CONSTANTS = tuple((name, deepcopy(globals()[name])) for name in ("PHASE", "STAGE", "CONTRACT_ID", "MAX_REQUEST_BYTES",
    "MAX_CONTRACT_BYTES", "MAX_EVENT_BYTES", "MAX_PREFIX_BYTES", "MAX_PREFIX_EVENTS", "MAX_SOURCE_BYTES", "MAX_OUTPUT_BYTES",
    "MAX_BUNDLE_BYTES", "MAX_SECONDS", "ARMS", "ALLOCATION", "SEMANTIC_ACTIONS", "NEXT_ACTIONS", "TRANSITIONS",
    "SOURCE_NAMES", "C8_SOURCE_NAMES", "C8_LIMITS", "SUPPLEMENTS", "CONTRACT"))
_ERROR_IDENTITY = (PreparationError, PreparationError.__init__, PreparationError.__init__.__code__)
