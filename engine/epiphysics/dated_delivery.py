"""Bounded, origin-bound local delivery receipts; no producer or network calls.

The queue owner and evidence checkpoint are separate. Original submissions are
selected from captured observations, including malformed and rejected bytes.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
import time

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
from . import decision_diagnosis as historical
from . import store
from . import dated_delivery_verifier as verifier

IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE)
    for module in (historical, store, verifier))
PHASES = {"dated_evidence_quality_preparation": "protocol_preparation",
          "dated_artifact_delivery_registration": "prospective_registration",
          "dated_artifact_delivery_check": "retained_delivery_check",
          "dated_artifact_delivery_review": "retained_delivery_review"}
PREPARATION, REGISTRATION, CHECK, REVIEW = tuple(PHASES)
STAGES = frozenset(PHASES.values())
PHASE_NEXT_ACTIONS = {
    PREPARATION: frozenset({"bind_dated_artifact_delivery", "repair_dated_evidence_quality_protocol"}),
    REGISTRATION: frozenset({"check_dated_artifact_delivery"}),
    CHECK: frozenset({"review_dated_delivery_evidence", "prepare_public_research_map_view"}),
    REVIEW: frozenset({"prepare_public_research_map_view"})}
PHASE_ACTIONS = {PREPARATION: frozenset({"prepare_dated_evidence_quality_protocol", "repair_dated_evidence_quality_protocol"}),
    REGISTRATION: frozenset({"bind_dated_artifact_delivery"}), CHECK: frozenset({"check_dated_artifact_delivery"}),
    REVIEW: frozenset({"review_dated_delivery_evidence"})}
SEMANTIC_ACTIONS = ACTIONS = frozenset().union(*PHASE_ACTIONS.values())
NEXT_ACTIONS = frozenset().union(*PHASE_NEXT_ACTIONS.values())
CONTRACT_ID = "dated-artifact-delivery-v1"
MAX_SECONDS = 10
MAX_REQUEST_BYTES, MAX_CONTRACT_BYTES = 32768, 65536
MAX_EVENT_BYTES = MAX_OUTPUT_BYTES = MAX_INVENTORY_BYTES = 1024 * 1024
MAX_PREFIX_BYTES, MAX_PREFIX_EVENTS = 8 * 1024 * 1024, 4096
MAX_BUNDLE_BYTES, MAX_SOURCE_BYTES = 16 * 1024 * 1024, 131072
MAX_TASK_OBSERVATIONS = 256
SOURCE_NAMES = ("dated_delivery.py", "dated_delivery_verifier.py", "decision_diagnosis.py", "decision_views.py", "store.py")
TRANSITIONS = {"improvement_completed", "improvement_failed"}
INPUT_ROLES = {"source", "tree_manifest", "git_objects", "backlog", "selection", "authority"}
OBSERVATION_KINDS = {"inventory", "oversize", "claim", "verification", "adjudication", "closure", "authority"}
CONTRACT = {"schema_version": 1, "contract_id": CONTRACT_ID, "phases": PHASES,
    "successors": {key: sorted(value) for key, value in PHASE_NEXT_ACTIONS.items()},
    "unit": "First task-scoped captured submission; malformed or over-limit submissions occupy the first slot",
    "time_basis": "Local ledger observation times; no external witness",
    "delivery_hours": 24, "adjudication_hours": 24, "review_limit": 1,
    "limits": {"request_bytes": MAX_REQUEST_BYTES, "contract_bytes": MAX_CONTRACT_BYTES,
        "prefix_bytes": MAX_PREFIX_BYTES, "prefix_events": MAX_PREFIX_EVENTS,
        "event_bytes": MAX_EVENT_BYTES, "output_bytes": MAX_OUTPUT_BYTES,
        "inventory_bytes": MAX_INVENTORY_BYTES, "bundle_bytes": MAX_BUNDLE_BYTES,
        "verification_seconds": MAX_SECONDS, "task_observations": MAX_TASK_OBSERVATIONS, "candidate_executions": 0, "producer_executions": 0,
        "model_calls": 0, "network_calls": 0, "live_effects": False},
    "scope": "One local nonacting maintenance delivery; criterion evidence, attribution, availability, authority and time assurance remain separate"}

_require, _keys = historical._require, historical._keys
_json, _canonical, _hash = historical._json, historical._canonical, historical._hash
_read, _digest, _identity = historical._read, historical._digest, historical._identity
_event, _prefix, _find = historical._event, historical._prefix, historical._find
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)


def _equal(actual, expected, label):
    if type(actual) is bytes or type(expected) is bytes:
        _require(type(actual) is bytes and type(expected) is bytes and actual == expected, label + " differs")
    else:
        historical._equal(actual, expected, label)


def _version(value):
    return type(value) is int and value == 1


def _role_limit(role):
    fixed = {"request": MAX_REQUEST_BYTES, "contract": MAX_CONTRACT_BYTES, "criteria": MAX_CONTRACT_BYTES,
        "packet": MAX_EVENT_BYTES, "validation": MAX_EVENT_BYTES, "validation_stdout": MAX_EVENT_BYTES, "validation_stderr": MAX_EVENT_BYTES, "ledger_prefix": MAX_PREFIX_BYTES,
        "evidence_origin": MAX_EVENT_BYTES, "queue_parent": MAX_EVENT_BYTES,
        "c9_report": MAX_OUTPUT_BYTES, "c9_table": MAX_OUTPUT_BYTES,
        "failure_request": MAX_REQUEST_BYTES, "failure_claim": MAX_EVENT_BYTES, "semantic_parent": MAX_EVENT_BYTES,
        "assessment_report": MAX_OUTPUT_BYTES, "verification_result": MAX_OUTPUT_BYTES}
    if role in fixed:
        return fixed[role]
    if role.startswith("code:epiphysics.") and role[16:] + ".py" in SOURCE_NAMES:
        return MAX_SOURCE_BYTES
    if role.startswith("validation-test:") and role[16:] in {"test_dated_delivery.py", "test_dated_delivery_verifier.py"}:
        return MAX_SOURCE_BYTES
    if role.startswith("observation:"):
        return MAX_EVENT_BYTES
    if role.startswith("blob:") and re.fullmatch(r"blob:[0-9a-f]{64}", role):
        return MAX_INVENTORY_BYTES + 1
    return None


class PreparationError(ValueError):
    def __init__(self, message, artifacts):
        super().__init__(message)
        self.artifacts = {}
        for role, raw in artifacts.items():
            limit = _role_limit(role)
            if limit is not None and type(raw) is bytes and len(raw) <= limit and sum(map(len, self.artifacts.values())) + len(raw) <= MAX_BUNDLE_BYTES:
                self.artifacts[role] = raw


def _put(artifacts, role, raw):
    limit = _role_limit(role)
    _require(limit is not None and type(raw) is bytes and len(raw) <= limit, "Invalid bounded delivery artifact: " + role)
    _require(sum(map(len, artifacts.values())) - len(artifacts.get(role, b"")) + len(raw) <= MAX_BUNDLE_BYTES, "Delivery bundle exceeds bound")
    artifacts[role] = raw


def _current_sources():
    path, raw, code = _SELF
    _require(IMPLEMENTATION_SOURCE == raw and IMPLEMENTATION_CODE is code and _read(path, MAX_SOURCE_BYTES) == raw,
             "Delivery source changed")
    _require(compile(raw, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) == code, "Delivery code changed")
    for name, function, original in _FUNCTION_CODES:
        _require(globals().get(name) is function and function.__code__ is original, "Delivery callable changed: " + name)
    for name, value in _CONSTANTS:
        _require(type(globals().get(name)) is type(value) and globals().get(name) == value, "Delivery constant changed: " + name)
    historical._current_sources()
    # The separately authored verifier exposes a source guard, not a producer.
    verifier.runtime_sources()
    return {"code:epiphysics." + name[:-3]: _read(path.parent / name, MAX_SOURCE_BYTES) for name in SOURCE_NAMES}


def _request(value):
    _keys(value, {"schema_version", "phase", "study_id", "origin", "ledger_path", "evidence_origin", "queue_parent", "evidence_checkpoint", "paths"}, "delivery request")
    _require(_version(value["schema_version"]) and value["phase"] in PHASES, "Invalid delivery phase")
    _require(type(value["study_id"]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value["study_id"]), "Invalid study ID")
    _keys(value["origin"], {"step_id"}, "queued origin")
    _require(type(value["origin"]["step_id"]) is str and 0 < len(value["origin"]["step_id"]) <= 200, "Invalid queued step")
    _identity(value["evidence_origin"])
    _identity(value["queue_parent"])
    checkpoint = value["evidence_checkpoint"]
    _keys(checkpoint, {"seq", "event_id", "event_hash"}, "evidence checkpoint")
    _identity({key: checkpoint[key] for key in ("event_id", "event_hash")})
    _require(type(checkpoint["seq"]) is int and checkpoint["seq"] > 0, "Invalid checkpoint sequence")
    _keys(value["paths"], {"contract", "criteria", "packet", "validation", "validation_stdout", "validation_stderr"} if value["phase"] == PREPARATION else {"contract", "criteria", "packet"}, "delivery paths")
    _require(all(type(path) is str and Path(path).is_absolute() and 0 < len(path.encode()) <= 4096 and "\0" not in path
        for path in [value["ledger_path"], *value["paths"].values()]), "Delivery paths must be bounded absolute locators")


def _accepted(event):
    _require(event["kind"] == "improvement_completed" and event["body"]["result"] == "assessed", "Parent is not a checked completion")
    body = event["body"]
    report = body["report"]["decision_pilot"]
    _require(_version(report["schema_version"]) and report["status"] == "checked", "Missing checked decision report")
    manifest = body["request"]["manifest"]
    declared = {role.removeprefix("decision-input:"): value for role, value in manifest.items() if role.startswith("decision-input:")}
    _equal(body["assessment_identity"]["input_manifest"], manifest, "Accepted manifest")
    _equal(report["assessment_identity"]["hash"], _hash(_canonical(declared)), "Accepted decision identity")
    _equal(body["assessment_identity"]["decision_assessment_hash"], report["assessment_identity"]["hash"], "Accepted report identity")
    _equal(body["assessment_identity"]["hash"], _hash(_canonical({"input_manifest": manifest,
        "decision_assessment_hash": report["assessment_identity"]["hash"]})), "Accepted controller identity")
    _equal(report["input_hashes"], {role: value for role, value in declared.items() if not role.startswith("code:")}, "Accepted input mappings")
    for name, digest in report["source_hashes"].items():
        _equal(declared.get("code:epiphysics." + name[:-3]), digest, "Accepted source mapping")
    return report, declared


def _origin(event, by_id):
    report, declared = _accepted(event)
    _require(report["phase"] == historical.PHASE and report["stage"] == historical.STAGE
        and report["contract_id"] == historical.CONTRACT_ID and report["checks"] and all(value is True for value in report["checks"].values())
        and event["body"]["next_step"]["action"] == report["next_step"]["action"] == "prepare_dated_evidence_quality_protocol", "Origin is not accepted C9 protocol evidence")
    _keys(report["source_hashes"], historical.SOURCE_NAMES, "Original C9 source identities")
    c8 = _find(by_id, {key: report["evidence_origin"][key] for key in ("event_id", "event_hash")})
    immutable = historical._origin_identity(c8)
    _equal(report["evidence_origin"], immutable, "Original C8 identity")
    for role, digest in immutable["input_manifest"].items():
        _equal(declared.get("c8:" + role), digest, "Original C8 role " + role)
    return {"event_id": event["id"], "event_hash": event["hash"],
        "assessment_hash": event["body"]["assessment_identity"]["hash"],
        "decision_assessment_hash": report["assessment_identity"]["hash"],
        "input_manifest": declared, "c8_evidence_origin": immutable}


def _observation(by_id, event_id, source=None):
    observation = by_id.get(event_id)
    _require(observation is not None and observation["kind"] == "observation", "Missing captured observation")
    body = observation["body"]
    _require(type(observation["id"]) is str and len(observation["id"].encode()) <= 256, "Observation identity exceeds bound")
    _digest(body["content_hash"])
    _require(type(body["size"]) is int and 0 <= body["size"] <= MAX_INVENTORY_BYTES + 1, "Captured observation exceeds bound")
    if source is not None:
        _equal(body["source"], source, "Observation scope")
    return observation


def _blob(artifacts, observation):
    raw = artifacts["blob:" + observation["body"]["content_hash"]]
    _require(len(raw) == observation["body"]["size"] and _hash(raw) == observation["body"]["content_hash"], "Captured blob differs")
    return raw


def _semantic_parent(parent, origin, phase):
    step = parent["body"]["next_step"]
    _require(step["state"] == "queued" and step["action"] in PHASE_ACTIONS[phase], "Wrong phase for queued action")
    if step["action"] == "prepare_dated_evidence_quality_protocol":
        _equal({"event_id": parent["id"], "event_hash": parent["hash"]}, {key: origin[key] for key in ("event_id", "event_hash")}, "Initial C9 predecessor")
        return None
    report, declared = _accepted(parent)
    _require(report["phase"] in PHASES and report["stage"] == PHASES[report["phase"]] and report["contract_id"] == CONTRACT_ID
        and report["next_step"]["action"] == step["action"] and step["action"] in PHASE_NEXT_ACTIONS[report["phase"]], "Invalid delivery continuation")
    _equal(report["evidence_origin"], origin, "Continuation immutable C9 ancestry")
    _equal(declared.get("evidence_origin"), origin["capture_sha256"], "Continuation origin manifest binding")
    _equal(declared.get("c9_report"), origin["accepted_report_sha256"], "Continuation C9 report identity")
    _equal(declared.get("c9_table"), origin["accepted_table_sha256"], "Continuation C9 table identity")
    return report


def _lineage(request, artifacts, events):
    by_id = _prefix(events)
    origin_event = _find(by_id, request["evidence_origin"])
    parent = _find(by_id, request["queue_parent"])
    checkpoint = request["evidence_checkpoint"]
    _equal({"seq": events[-1]["seq"], "event_id": events[-1]["id"], "event_hash": events[-1]["hash"]}, checkpoint, "Fixed evidence checkpoint")
    _require(origin_event["seq"] <= parent["seq"] <= checkpoint["seq"], "Invalid origin/parent/checkpoint order")
    _equal(_json(artifacts["evidence_origin"]), origin_event, "Captured C9 origin")
    _equal(_json(artifacts["queue_parent"]), parent, "Captured immediate parent")
    origin = _origin(origin_event, by_id)
    for name, role in (("c9_report", "assessment_report"), ("c9_table", "diagnostic_table")):
        full_role = "decision-result:" + role
        observation = _observation(by_id, origin_event["body"]["input_observations"][full_role], "improvement-input:" + full_role)
        _require(observation["seq"] < origin_event["seq"], "C9 output follows acceptance")
        _equal(artifacts[name], _blob(artifacts, observation), "C9 retained output")
    report = _json(artifacts["c9_report"])
    _equal(report, origin_event["body"]["report"]["decision_pilot"], "Accepted C9 report bytes")
    _equal(_hash(artifacts["c9_table"]), report["diagnosis"]["detail_sha256"], "Accepted C9 detail identity")
    _equal(len(artifacts["c9_table"]), report["diagnosis"]["detail_bytes"], "Accepted C9 detail size")
    origin.update(capture_sha256=_hash(artifacts["evidence_origin"]), accepted_report_sha256=_hash(artifacts["c9_report"]), accepted_table_sha256=_hash(artifacts["c9_table"]))
    step = parent["body"]["next_step"]
    _require(step["state"] == "queued" and step["id"] == request["origin"]["step_id"], "Request does not own queued step")
    semantic = parent
    ancestry = {"mode": "initial" if parent["id"] == origin_event["id"] else "checked_continuation", "failed_event_id": None}
    if parent["kind"] == "improvement_failed":
        _require(step["action"] == "diagnose_failed_assessment", "Invalid failure continuation")
        claim, semantic = _json(artifacts["failure_claim"]), _json(artifacts["semantic_parent"])
        prior = _json(artifacts["failure_request"])
        _request(prior)
        _equal(by_id.get(claim["id"]), claim, "Captured failure claim")
        _equal(by_id.get(semantic["id"]), semantic, "Captured original semantic parent")
        _require(semantic["seq"] < claim["seq"] < parent["seq"] and claim["kind"] == "improvement_started"
            and claim["body"]["run_key"] == parent["body"]["run_key"], "Invalid failure claim order")
        _equal(claim["body"]["request"], parent["body"]["request"], "Failure request identity")
        _equal(claim["body"]["claimed_step"], semantic["body"]["next_step"], "Failure semantic claim")
        _equal(prior["phase"], request["phase"], "Failed semantic phase")
        _equal(prior["evidence_origin"], request["evidence_origin"], "Failure immutable origin")
        _equal(prior["queue_parent"], {"event_id": semantic["id"], "event_hash": semantic["hash"]}, "Failure original parent")
        _equal(prior["origin"]["step_id"], semantic["body"]["next_step"]["id"], "Failure original step")
        _equal(parent["body"]["request"]["after_step"], prior["origin"]["step_id"], "Failed requested step")
        _equal(_hash(artifacts["failure_request"]), parent["body"]["request"]["manifest"]["decision-input:request"], "Failed captured request")
        transitions = [event for event in events if event["kind"] in TRANSITIONS and event["seq"] < claim["seq"]]
        _equal(transitions[-1], semantic, "Failure queue owner")
        observation = _observation(by_id, "improvement:" + parent["body"]["run_key"] + ":input:decision-input:request", "improvement-input:decision-input:request")
        _require(claim["seq"] < observation["seq"] < parent["seq"], "Failure request capture order")
        _equal(_blob(artifacts, observation), artifacts["failure_request"], "Failure request observation")
        ancestry = {"mode": "failed_attempt_continuation", "failed_event_id": parent["id"], "failed_claim_id": claim["id"]}
    previous = _semantic_parent(semantic, origin, request["phase"])
    ancestry["semantic_action"] = semantic["body"]["next_step"]["action"]
    return origin, ancestry, previous


def _git_object(kind, data):
    return hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _git_proof(registration, manifest, proof, source):
    """Verify complete retained tree edges, without invoking Git or a shell."""
    _keys(proof, {"schema_version", "objects"}, "Git object proof")
    _require(_version(proof["schema_version"]) and type(proof["objects"]) is list and 0 < len(proof["objects"]) <= 4096, "Invalid Git proof")
    objects = {}
    for item in proof["objects"]:
        _keys(item, {"object_id", "type", "data_base64"}, "Git object")
        _require(item["type"] in {"commit", "tree", "blob"} and item["object_id"] not in objects, "Invalid Git object kind or duplicate")
        raw = base64.b64decode(item["data_base64"], validate=True)
        _equal(_git_object(item["type"], raw), item["object_id"], "Git object digest")
        objects[item["object_id"]] = (item["type"], raw)
    kind, commit = objects[registration["source_commit"]]
    _require(kind == "commit" and re.match(rb"tree [0-9a-f]{40}\n", commit), "Missing retained commit root")
    entries, visited = [], set()
    def visit(oid, parent, ancestors):
        _require(len(ancestors) < 64 and oid not in ancestors, "Cyclic or overdeep Git tree")
        kind, raw = objects[oid]
        _require(kind == "tree", "Git edge is not a tree")
        visited.add(oid)
        offset, names = 0, set()
        while offset < len(raw):
            space, nul = raw.index(b" ", offset), raw.index(b"\0", offset)
            mode = raw[offset:space].decode("ascii")
            mode = "040000" if mode == "40000" else mode
            name = raw[space + 1:nul].decode("utf-8")
            _require(name not in {"", ".", ".."} and "/" not in name and name not in names and "\0" not in name, "Invalid Git entry name")
            _require(mode in {"040000", "100644", "100755", "120000", "160000"} and nul + 21 <= len(raw), "Invalid Git entry mode/length")
            names.add(name)
            child = raw[nul + 1:nul + 21].hex()
            path = parent + name
            entries.append({"path": path, "mode": mode, "object_id": child})
            if mode == "040000":
                visit(child, path + "/", ancestors | {oid})
            offset = nul + 21
    visit(commit.split(b"\n", 1)[0][5:].decode(), "", set())
    expected = {"schema_version": 1, "source_commit": registration["source_commit"], "entries": sorted(entries, key=lambda item: item["path"])}
    _equal(manifest, expected, "Complete retained Git tree")
    selected = next((entry for entry in entries if entry["path"] == registration["source_path"]), None)
    _require(selected is not None and selected["mode"] in {"100644", "100755"}, "Selected source is not regular")
    _equal(_git_object("blob", source), selected["object_id"], "Selected source Git binding")
    _equal(_hash(source), registration["source_sha256"], "Selected source byte binding")
    return objects


def _source_scope(registration_id, kind):
    return "improvement-input:dated-delivery:" + registration_id + ":" + kind


def _registration(packet, artifacts, by_id, parent):
    _keys(packet, {"schema_version", "phase", "registration"}, "registration packet")
    registration = packet["registration"]
    _keys(registration, {"schema_version", "task_id", "registration_id", "protocol_sha256", "criteria_sha256", "source_commit", "source_path", "source_sha256", "tree_manifest_sha256", "roles", "input_observations", "exposure"}, "task registration")
    _require(_version(registration["schema_version"]), "Invalid registration version")
    for key in ("task_id", "registration_id"):
        _require(type(registration[key]) is str and re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", registration[key]), "Invalid task identity")
    _equal(registration["protocol_sha256"], _hash(artifacts["contract"]), "Frozen protocol binding")
    _equal(registration["criteria_sha256"], _hash(artifacts["criteria"]), "Frozen criteria binding")
    _keys(registration["roles"], {"requester", "producer", "verifier", "adjudicator"}, "task roles")
    _require(all(type(actor) is str and 0 < len(actor) <= 200 for actor in registration["roles"].values()), "Invalid actor")
    _require(registration["roles"]["adjudicator"] != registration["roles"]["producer"], "Adjudicator must be non-producer")
    _keys(registration["exposure"], {"basis", "prior_delivery", "external_witness"}, "exposure declaration")
    _require(type(registration["exposure"]["basis"]) is str and 0 < len(registration["exposure"]["basis"]) <= 2048
        and registration["exposure"]["prior_delivery"] is False and registration["exposure"]["external_witness"] is None,
        "Missing limited prospective exposure declaration")
    _keys(registration["input_observations"], INPUT_ROLES, "registered input observations")
    inputs = {}
    for role, event_id in registration["input_observations"].items():
        observation = _observation(by_id, event_id, _source_scope(registration["registration_id"], "input:" + role))
        _require(observation["seq"] > parent["seq"], "Registration input predates protocol freeze")
        inputs[role] = _blob(artifacts, observation)
    _require(len(inputs["source"]) <= 262144, "Selected source exceeds bound")
    manifest = _json(inputs["tree_manifest"])
    _equal(inputs["tree_manifest"], _canonical(manifest), "Canonical tree manifest")
    _equal(_hash(inputs["tree_manifest"]), registration["tree_manifest_sha256"], "Tree manifest binding")
    verifier._trusted(registration, inputs["source"], manifest)
    objects = _git_proof(registration, manifest, _json(inputs["git_objects"]), inputs["source"])
    selection = _json(inputs["selection"])
    _keys(selection, {"schema_version", "selected_path", "candidate_paths", "exclusions", "eligible_count", "backlog_span"}, "selection receipt")
    _require(_version(selection["schema_version"]), "Invalid selection receipt version")
    candidates = sorted(entry["path"] for entry in manifest["entries"] if entry["mode"] in {"100644", "100755"}
        and entry["path"].startswith("docs/theory/") and entry["path"].endswith(".md"))
    _equal(selection["candidate_paths"], candidates, "Complete theory candidate list")
    _require(type(selection["exclusions"]) is dict and set(selection["exclusions"]) <= set(candidates), "Invalid exclusions")
    for path, reason in selection["exclusions"].items():
        _require(reason in {"generated", "archived", "separate_ownership", "protocol_or_test"}, "Invalid exclusion reason")
        # Exclusions are explicitly attributed operator constraints, not inferred quality.
    chosen, count = None, None
    entries = {entry["path"]: entry for entry in manifest["entries"]}
    for path in candidates:
        if path in selection["exclusions"]:
            continue
        kind, data = objects[entries[path]["object_id"]]
        _require(kind == "blob", "Missing selection candidate bytes")
        parsed = verifier.inspect_source(data)
        if parsed["expected_tokens"]:
            chosen, count = path, len(parsed["expected_tokens"])
            break
    _require(chosen is not None, "No eligible future maintenance source")
    _equal([chosen, count], [selection["selected_path"], selection["eligible_count"]], "First eligible selection")
    _equal(chosen, registration["source_path"], "Registered selected path")
    span = selection["backlog_span"]
    _keys(span, {"start", "end", "sha256"}, "backlog span")
    _require(type(span["start"]) is int and type(span["end"]) is int and 0 <= span["start"] < span["end"] <= len(inputs["backlog"]), "Invalid backlog span")
    backlog = inputs["backlog"][span["start"]:span["end"]]
    _equal(_hash(backlog), span["sha256"], "Backlog evidence span")
    _require(b"Update cross-references in theory docs" in backlog, "Missing independently useful backlog binding")
    _require(not any(event["kind"] == "observation" and event["body"]["source"] in {
        _source_scope(registration["registration_id"], "inventory"), _source_scope(registration["registration_id"], "oversize"),
        _source_scope(registration["registration_id"], "overflow_prefix")}
        for event in by_id.values()), "Task already has a submission before registration")
    return registration


def _registered_event(packet, by_id, origin):
    registration_event = _find(by_id, packet["registration_event"])
    report, _ = _accepted(registration_event)
    _require(report["phase"] == REGISTRATION and report["contract_id"] == CONTRACT_ID
        and report["next_step"]["action"] == "check_dated_artifact_delivery", "Missing accepted task registration")
    _equal(report["evidence_origin"], origin, "Registered C9 ancestry")
    return registration_event, report["registration"]


def _record(raw):
    try:
        value = _json(raw)
        return value if type(value) is dict else None
    except (ValueError, TypeError):
        return None


def _scoped_records(registration, registration_event, by_id, artifacts):
    rows = {kind: [] for kind in OBSERVATION_KINDS}
    for event in by_id.values():
        if event["kind"] != "observation":
            continue
        for kind in OBSERVATION_KINDS:
            if event["body"]["source"] == _source_scope(registration["registration_id"], kind):
                _require(event["seq"] > registration_event["seq"], "Submission record predates accepted registration")
                rows[kind].append((event, _blob(artifacts, event)))
    _require(sum(map(len, rows.values())) <= MAX_TASK_OBSERVATIONS, "Task observation count exceeds bound")
    return rows


def _bound_record(value, registration, artifact_hash, actor=None):
    return (type(value) is dict and _version(value.get("schema_version"))
        and value.get("task_id") == registration["task_id"] and value.get("registration_id") == registration["registration_id"]
        and value.get("artifact_sha256") == artifact_hash and (actor is None or value.get("actor") == actor))


def _when(event):
    return store.instant(event["recorded_at"])


def _closure(rows, packet, registration, registration_event, *, review_parent=None):
    wanted = packet["closure_observation"]
    if wanted is None:
        return None
    found = [pair for pair in rows["closure"] if pair[0]["id"] == wanted]
    _require(len(found) == 1, "Missing captured closure")
    event, raw = found[0]
    value = _record(raw)
    _require(value is not None and _version(value.get("schema_version")) and value.get("task_id") == registration["task_id"]
        and value.get("registration_id") == registration["registration_id"]
        and value.get("actor") == registration["roles"]["adjudicator"]
        and value.get("state") in {"no_delivery", "unresolved", "resolved"}
        and type(value.get("missing")) is list and all(type(x) is str for x in value["missing"]), "Invalid non-producer closure")
    if review_parent is not None:
        _equal(value.get("review_of"), {"event_id": review_parent["id"], "event_hash": review_parent["hash"]}, "Review closure predecessor")
        _require(event["seq"] > review_parent["seq"], "Review requires a new closure receipt")
    return event, value


def _phase_metadata(request, artifacts, events, origin, previous):
    packet = _json(artifacts["packet"])
    _require(type(packet) is dict and _version(packet.get("schema_version")) and packet.get("phase") == request["phase"], "Invalid phase packet")
    by_id = {event["id"]: event for event in events}
    parent = _find(by_id, request["queue_parent"])
    if parent["kind"] == "improvement_failed":
        parent = _json(artifacts["semantic_parent"])
    if request["phase"] == PREPARATION:
        _keys(packet, {"schema_version", "phase", "validation"}, "protocol preparation packet")
        validation = packet["validation"]
        _keys(validation, {"status", "tests", "exit_code", "source_hashes", "receipt_sha256"}, "owned validation receipt")
        _require(type(validation["tests"]) is int and validation["tests"] > 0 and validation["status"] in {"passed", "failed"}
            and type(validation["exit_code"]) is int, "Invalid owned validation evidence")
        _digest(validation["receipt_sha256"])
        _equal(validation["source_hashes"], {name: _hash(artifacts["code:epiphysics." + name[:-3]]) for name in SOURCE_NAMES}, "Owned validation source pins")
        receipt = _json(artifacts["validation"])
        _keys(receipt, {"schema_version", "command", "test_modules", "source_hashes", "test_hashes", "started_at", "ended_at", "elapsed_seconds", "returncode", "tests_run", "stdout_sha256", "stderr_sha256"}, "local execution receipt")
        _require(_version(receipt["schema_version"]) and type(receipt["command"]) is list and 0 < len(receipt["command"]) <= 64
            and all(type(item) is str and 0 < len(item) <= 4096 for item in receipt["command"]), "Missing bounded execution command")
        _require(type(receipt["test_modules"]) is list and {"test_dated_delivery", "test_dated_delivery_verifier"} <= set(receipt["test_modules"])
            and all(module in receipt["command"] for module in receipt["test_modules"]), "Required focused tests are not selected")
        _equal(receipt["source_hashes"], validation["source_hashes"], "Tested production identities")
        _equal(receipt["test_hashes"], {name: _hash(artifacts["validation-test:" + name]) for name in ("test_dated_delivery.py", "test_dated_delivery_verifier.py")}, "Tested control identities")
        _equal([receipt["returncode"], receipt["tests_run"]], [validation["exit_code"], validation["tests"]], "Execution receipt summary")
        for stream in ("stdout", "stderr"):
            _equal(_hash(artifacts["validation_" + stream]), receipt[stream + "_sha256"], "Retained validation output")
        duration = receipt["elapsed_seconds"]
        _require(type(duration) in (int, float) and math.isfinite(duration) and duration >= 0
            and 0 <= duration <= (store.instant(receipt["ended_at"]) - store.instant(receipt["started_at"])).total_seconds() + .01,
            "Invalid validation execution duration")
        output = artifacts["validation_stdout"] + b"\n" + artifacts["validation_stderr"]
        runs = re.findall(rb"(?:^|\n)Ran ([0-9]+) tests? in [0-9.]+s(?:\r?\n)", output)
        _require(len(runs) == 1 and int(runs[0]) == receipt["tests_run"], "Unittest output does not bind test count")
        passed = validation["status"] == "passed" and receipt["returncode"] == 0
        _require(not passed or re.search(rb"(?:^|\n)OK(?: \(skipped=[0-9]+\))?\s*$", output), "Passing receipt lacks terminal test success")
        return {"registration": None, "registration_event": None, "protocol_state": "ready_awaiting_task" if passed else "repair_required"}
    if request["phase"] == REGISTRATION:
        _require(previous is not None, "Missing accepted preparation")
        for role in ("contract", "criteria"):
            _equal(_hash(artifacts[role]), previous["input_hashes"][role], "Accepted preparation " + role + " bytes")
        registration = _registration(packet, artifacts, by_id, parent)
        _require(previous is not None and previous["protocol_state"] == "ready_awaiting_task", "Protocol is not ready")
        _equal(previous["source_hashes"], {name: _hash(artifacts["code:epiphysics." + name[:-3]]) for name in SOURCE_NAMES}, "Frozen protocol implementation")
        return {"registration": registration, "registration_event": None, "protocol_state": "registered"}
    _keys(packet, {"schema_version", "phase", "registration_event", "closure_observation"}, "delivery check packet")
    registration_event, registration = _registered_event(packet, by_id, origin)
    _equal(registration["protocol_sha256"], _hash(artifacts["contract"]), "Registered protocol bytes")
    _equal(registration["criteria_sha256"], _hash(artifacts["criteria"]), "Registered criteria bytes")
    _equal(registration_event["body"]["report"]["decision_pilot"]["source_hashes"],
        {name: _hash(artifacts["code:epiphysics." + name[:-3]]) for name in SOURCE_NAMES}, "Registered implementation freeze")
    if request["phase"] == CHECK:
        _equal(parent, registration_event, "Check must consume its own registration")
    else:
        _require(previous is not None and previous["phase"] == CHECK and previous["next_step"]["action"] == "review_dated_delivery_evidence", "Only one checked review is permitted")
        _equal(previous["registration_event"], packet["registration_event"], "Review registration continuity")
    rows = _scoped_records(registration, registration_event, by_id, artifacts)
    _readiness(request["phase"], packet, registration, registration_event, rows, by_id, artifacts, parent, previous)
    return {"registration": registration, "registration_event": packet["registration_event"], "protocol_state": "reviewing" if request["phase"] == REVIEW else "checking"}


def _needed_observations(request, packet, events):
    by_id = {event["id"]: event for event in events}
    origin = _find(by_id, request["evidence_origin"])
    ids = {origin["body"]["input_observations"]["decision-result:" + role] for role in ("assessment_report", "diagnostic_table")}
    registration = None
    if request["phase"] == REGISTRATION:
        registration = packet["registration"]
    elif request["phase"] in {CHECK, REVIEW}:
        event = _find(by_id, packet["registration_event"])
        registration = event["body"]["report"]["decision_pilot"]["registration"]
    if registration is not None:
        ids.update(registration["input_observations"].values())
        sources = {_source_scope(registration["registration_id"], kind) for kind in OBSERVATION_KINDS}
        ids.update(event["id"] for event in events if event["kind"] == "observation" and event["body"]["source"] in sources)
        ids.update(event["id"] for event in events if event["kind"] == "observation" and event["body"]["source"] == _source_scope(registration["registration_id"], "overflow_prefix"))
    parent = _find(by_id, request["queue_parent"])
    if parent["kind"] == "improvement_failed":
        ids.add("improvement:" + parent["body"]["run_key"] + ":input:decision-input:request")
    return [_observation(by_id, event_id) for event_id in sorted(ids)]


def _metadata(artifacts, manifest):
    request = _json(artifacts["request"])
    _request(request)
    _equal(_json(artifacts["contract"]), CONTRACT, "Fixed delivery contract")
    _equal(_json(artifacts["criteria"]), verifier.CRITERIA, "Fixed delivery criteria")
    events = _json(artifacts["ledger_prefix"])
    origin, ancestry, previous = _lineage(request, artifacts, events)
    packet = _json(artifacts["packet"])
    expected = {"request", "contract", "criteria", "packet", "ledger_prefix", "evidence_origin", "queue_parent", "c9_report", "c9_table"}
    if "validation" in request["paths"]:
        expected.update({"validation", "validation_stdout", "validation_stderr"})
        _equal(_hash(artifacts["validation"]), packet["validation"]["receipt_sha256"], "Retained validation receipt")
        for name in ("test_dated_delivery.py", "test_dated_delivery_verifier.py"):
            expected.add("validation-test:" + name)
            _equal(artifacts["validation-test:" + name], _read(Path(__file__).parent.parent / "tests" / name, MAX_SOURCE_BYTES), "Tested source unchanged")
    for observation in _needed_observations(request, packet, events):
        expected.update({"observation:" + observation["id"], "blob:" + observation["body"]["content_hash"]})
        _equal(_json(artifacts["observation:" + observation["id"]]), observation, "Captured observation identity")
        _blob(artifacts, observation)
    if ancestry["mode"] == "failed_attempt_continuation":
        expected.update({"failure_request", "failure_claim", "semantic_parent"})
    for role, raw in _current_sources().items():
        expected.add(role)
        _equal(artifacts[role], raw, "Current delivery source bytes")
    _keys(artifacts, expected, "Delivery captured roles")
    state = _phase_metadata(request, artifacts, events, origin, previous)
    return {"schema_version": 1, "contract_id": CONTRACT_ID, "study_id": request["study_id"],
        "phase": request["phase"], "stage": PHASES[request["phase"]], "status": "prepared", "origin": deepcopy(request["origin"]),
        "assessment_identity": {"schema_version": 1, "hash": _hash(_canonical(manifest))},
        "input_hashes": {role: value for role, value in sorted(manifest.items()) if not role.startswith("code:")},
        "source_hashes": {name: manifest["code:epiphysics." + name[:-3]] for name in SOURCE_NAMES},
        "evidence_origin": origin, "queue_parent": deepcopy(request["queue_parent"]),
        "evidence_checkpoint": deepcopy(request["evidence_checkpoint"]), "ancestry": ancestry,
        **state, "scope": CONTRACT["scope"]}


def prepare_dated_delivery(path):
    """Capture immutable inputs and source identities, without artifact checking."""
    artifacts, started = {}, time.monotonic()
    try:
        _put(artifacts, "request", _read(path, MAX_REQUEST_BYTES))
        request = _json(artifacts["request"])
        _request(request)
        for role, locator in request["paths"].items():
            _put(artifacts, role, _read(locator, _role_limit(role)))
        packet = _json(artifacts["packet"])
        if request["phase"] == PREPARATION:
            for name in ("test_dated_delivery.py", "test_dated_delivery_verifier.py"):
                _put(artifacts, "validation-test:" + name, _read(Path(__file__).parent.parent / "tests" / name, MAX_SOURCE_BYTES))
        for role, raw in _current_sources().items():
            _put(artifacts, role, raw)
        ledger = store.Ledger.open_readonly(request["ledger_path"])
        try:
            ledger.db.execute("BEGIN")
            end = request["evidence_checkpoint"]["seq"]
            bound = ledger.db.execute("SELECT COUNT(*),COALESCE(SUM(length(CAST(body AS BLOB))),0),COALESCE(MAX(length(CAST(body AS BLOB))),0) FROM events WHERE seq<=?", (end,)).fetchone()
            _require(0 < bound[0] <= MAX_PREFIX_EVENTS and bound[1] <= MAX_PREFIX_BYTES and bound[2] <= MAX_EVENT_BYTES, "Historical prefix exceeds bounds")
            events = [{**dict(row), "body": _json(row["body"])} for row in ledger.db.execute("SELECT * FROM events WHERE seq<=? ORDER BY seq", (end,))]
            _put(artifacts, "ledger_prefix", _canonical(events))
            by_id = _prefix(events)
            origin, parent = _find(by_id, request["evidence_origin"]), _find(by_id, request["queue_parent"])
            _put(artifacts, "evidence_origin", _canonical(origin))
            _put(artifacts, "queue_parent", _canonical(parent))
            for observation in _needed_observations(request, packet, events):
                _put(artifacts, "observation:" + observation["id"], _canonical(observation))
                raw = _read(ledger.root / "blobs" / observation["body"]["content_hash"], MAX_INVENTORY_BYTES + 1)
                _require(len(raw) == observation["body"]["size"] and _hash(raw) == observation["body"]["content_hash"], "Captured historical blob corruption")
                _put(artifacts, "blob:" + observation["body"]["content_hash"], raw)
            for role, original in (("c9_report", "assessment_report"), ("c9_table", "diagnostic_table")):
                observation = by_id[origin["body"]["input_observations"]["decision-result:" + original]]
                _put(artifacts, role, _blob(artifacts, observation))
            if parent["kind"] == "improvement_failed":
                claims = [event for event in events if event["kind"] == "improvement_started" and event["body"]["run_key"] == parent["body"]["run_key"]]
                _require(len(claims) == 1, "Missing unique failure claim")
                claim = claims[0]
                semantic = [event for event in events if event["kind"] in TRANSITIONS and event["seq"] < claim["seq"]][-1]
                observation = by_id["improvement:" + parent["body"]["run_key"] + ":input:decision-input:request"]
                _put(artifacts, "failure_request", _blob(artifacts, observation))
                _put(artifacts, "failure_claim", _canonical(claim))
                _put(artifacts, "semantic_parent", _canonical(semantic))
        finally:
            ledger.close()
        manifest = {role: _hash(raw) for role, raw in artifacts.items()}
        report = _metadata(artifacts, manifest)
        _require(time.monotonic() - started <= MAX_SECONDS, "Delivery preparation exceeds time bound")
        return {"artifacts": artifacts, "manifest": manifest, "report": report}
    except (ValueError, OSError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError, sqlite3.Error) as error:
        raise PreparationError(str(error), artifacts) from error


def check_prepared_dated_delivery(prepared):
    """Validate captured identities; successful replay never invokes the verifier."""
    _keys(prepared, {"artifacts", "manifest", "report"}, "prepared delivery")
    _keys(prepared["manifest"], prepared["artifacts"], "delivery manifest")
    total = 0
    for role, raw in prepared["artifacts"].items():
        limit = _role_limit(role)
        _require(limit is not None and type(raw) is bytes and len(raw) <= limit, "Invalid delivery artifact bound")
        _equal(_hash(raw), prepared["manifest"][role], "Captured delivery digest")
        total += len(raw)
    _require(total <= MAX_BUNDLE_BYTES, "Delivery bundle exceeds bound")
    _equal(prepared["report"], _metadata(prepared["artifacts"], prepared["manifest"]), "Prepared delivery metadata")


def validate_lineage(prepared, actual_events, after_step):
    check_prepared_dated_delivery(prepared)
    request = _json(prepared["artifacts"]["request"])
    _equal(after_step, request["origin"]["step_id"], "Authoritative requested step")
    captured = _json(prepared["artifacts"]["ledger_prefix"])
    _equal([event for event in actual_events if event["seq"] <= request["evidence_checkpoint"]["seq"]], captured, "Authoritative evidence checkpoint")
    transitions = [event for event in actual_events if event["kind"] in TRANSITIONS]
    _require(transitions and transitions[-1]["id"] == request["queue_parent"]["event_id"] and transitions[-1]["hash"] == request["queue_parent"]["event_hash"], "Stale immediate queue owner")
    registration = prepared["report"]["registration"]
    if registration is not None:
        sources = {_source_scope(registration["registration_id"], kind) for kind in OBSERVATION_KINDS | {"overflow_prefix"}}
        # A frozen checkpoint cannot silently omit already-captured scoped evidence.
        # Unrelated observations (including this assessment's own captures) are fine.
        _require(not any(event["seq"] > captured[-1]["seq"] and event["kind"] == "observation"
            and event["body"]["source"] in sources for event in actual_events), "Checkpoint omits later scoped evidence")


def _authority(registration, records, artifacts, by_id, cutoff):
    candidates = list(records["authority"])
    original = _observation(by_id, registration["input_observations"]["authority"])
    candidates.insert(0, (original, _blob(artifacts, original)))
    result = {}
    for role, action in (("producer", "submit"), ("verifier", "verify"), ("adjudicator", "adjudicate")):
        available, effective = [], []
        for event, raw in candidates:
            value = _record(raw)
            if value is None or value.get("task_id") != registration["task_id"] or value.get("registration_id") != registration["registration_id"]:
                continue
            if (value.get("grantor") != registration["roles"]["requester"] or value.get("subject") != registration["roles"][role]
                or type(value.get("actions")) is not list or action not in value["actions"]):
                continue
            if _when(event) <= cutoff:
                available.append(event["id"])
                try:
                    at = store.instant(value["effective_at"])
                    end = store.instant(value["expires_at"]) if value.get("expires_at") is not None else None
                except (ValueError, TypeError, KeyError, AttributeError):
                    continue
                if at <= cutoff and (end is None or cutoff < end) and type(value.get("revoked")) is bool:
                    effective.append((event, value))
        effective.sort(key=lambda pair: pair[0]["seq"])
        result[role] = {"available_observations": available, "effective_permission": None if not effective else not effective[-1][1]["revoked"],
            "basis": "Locally attributed task-scoped authority claims; no authenticated external identity or global authority proof"}
    return result


def _operative(value, at):
    if value.get("effective_at") is None:
        return True  # An observed assertion; no effective-time claim is invented.
    try:
        return store.instant(value["effective_at"]) <= at
    except (ValueError, TypeError, AttributeError):
        return False


def _verification_timing(value, artifact, captured):
    try:
        elapsed = value["elapsed_seconds"]
        start, end = store.instant(value["started_at"]), store.instant(value["ended_at"])
        _digest(value["environment_sha256"])
        return (type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= MAX_SECONDS
            and _when(artifact) <= start <= end <= _when(captured) and elapsed <= (end - start).total_seconds() + .001)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def _dated_records(rows):
    result = []
    for kind in sorted(rows):
        for event, raw in rows[kind]:
            value = _record(raw) or {}
            dates, invalid = {}, []
            for name in ("issued_at", "observed_at", "effective_at"):
                declared = value.get(name)
                try:
                    if declared is not None:
                        _require(type(declared) is str and len(declared) <= 64, "Invalid declared date")
                        store.instant(declared)
                    dates[name] = declared
                except (ValueError, TypeError):
                    dates[name] = None
                    invalid.append(name)
            revision = value.get("revision_of")
            if revision is not None:
                try:
                    _require(type(revision) is str and len(revision) <= 256, "Invalid revision identity")
                    revision.encode("utf-8")
                except (ValueError, TypeError, UnicodeError):
                    revision = None
                    invalid.append("revision_of")
            result.append({"observation_id": event["id"], "kind": kind, "captured_at": event["recorded_at"],
                **dates, "revision_of": revision, "invalid_declared_fields": invalid,
                "basis": "Capture time from local ledger; other dates are retained declarations or null/unmeasured"})
    return result


def _empty_outcome():
    return {"status": None, "first_submission": None, "late_submission": None, "artifact_quality": None, "producer_claim": None,
        "claim_agreement": {"numerator": 0, "denominator": 0, "value": None}, "missing": [],
        "delivery_timely": None, "verification_available_by_cutoff": None, "adjudication_available_by_deadline": None,
        "authority": None, "witness": {"status": "none", "proof": None, "time_bound": None},
        "dated_records": [], "identity_attribution": "Local capture scope and declared actor bindings only; no external authenticity proof"}


def _submissions(rows):
    return sorted([("inventory", *pair) for pair in rows["inventory"]] + [("oversize", *pair) for pair in rows["oversize"]], key=lambda item: item[1]["seq"])


def _submission_identity(submission):
    kind, observation, raw = submission
    return {"observation_id": observation["id"], "capture_hash": observation["hash"],
        "captured_at": observation["recorded_at"], "kind": kind,
        "artifact_sha256": observation["body"]["content_hash"] if kind == "inventory" else None,
        "bytes": len(raw) if kind == "inventory" else None}


def _oversize(raw, observation, registration, registration_event, by_id, artifacts):
    receipt = _record(raw)
    _keys(receipt, {"schema_version", "task_id", "registration_id", "retained_bytes", "prefix_sha256", "prefix_observation", "truncated", "observed_bytes_lower_bound", "complete_sha256"}, "over-limit rejection")
    _require(_version(receipt["schema_version"]) and receipt["task_id"] == registration["task_id"] and receipt["registration_id"] == registration["registration_id"]
        and receipt["truncated"] is True and receipt["complete_sha256"] is None
        and type(receipt["retained_bytes"]) is int and receipt["retained_bytes"] == MAX_INVENTORY_BYTES + 1
        and type(receipt["observed_bytes_lower_bound"]) is int and receipt["observed_bytes_lower_bound"] == receipt["retained_bytes"], "Unsubstantiated over-limit receipt")
    prefix = _observation(by_id, receipt["prefix_observation"], _source_scope(registration["registration_id"], "overflow_prefix"))
    _require(registration_event["seq"] < prefix["seq"] < observation["seq"], "Overflow prefix must follow registration and precede rejection")
    _equal([prefix["body"]["content_hash"], prefix["body"]["size"]], [receipt["prefix_sha256"], receipt["retained_bytes"]], "Retained overflow prefix identity")
    _blob(artifacts, prefix)
    return receipt


def _verification_chain(registration, artifact, rows, verifier_hash, deadline, expected_result=None):
    verification = rows["verification"][0] if rows["verification"] else None
    checked = _record(verification[1]) if verification else None
    supplied = checked.get("result") if checked else None
    matches = type(supplied) is dict and _version(supplied.get("schema_version")) and supplied.get("verdict") in {"pass", "fail"}
    if matches and expected_result is not None:
        try:
            matches = _canonical(supplied) == _canonical(expected_result)
        except (ValueError, TypeError, UnicodeError):
            matches = False
    valid_verification = bool(verification and _bound_record(checked, registration, artifact["body"]["content_hash"], registration["roles"]["verifier"])
        and checked.get("criteria_sha256") == registration["criteria_sha256"] and checked.get("verifier_sha256") == verifier_hash
        and checked.get("error") is None and matches and _verification_timing(checked, artifact, verification[0])
        and _when(verification[0]) <= deadline and _operative(checked, deadline))
    adjudication = rows["adjudication"][0] if rows["adjudication"] else None
    adjudicated = _record(adjudication[1]) if adjudication else None
    valid_adjudication = bool(valid_verification and adjudication
        and _bound_record(adjudicated, registration, artifact["body"]["content_hash"], registration["roles"]["adjudicator"])
        and adjudicated.get("verification_observation") == verification[0]["id"]
        and adjudicated.get("verdict") == supplied["verdict"] and verification[0]["seq"] < adjudication[0]["seq"]
        and _when(adjudication[0]) <= deadline and _operative(checked, _when(adjudication[0]))
        and _operative(adjudicated, _when(adjudication[0])))
    return verification, checked, valid_verification, adjudication, valid_adjudication


def _readiness(phase, packet, registration, registration_event, rows, by_id, artifacts, parent, previous):
    """Refuse known incomplete control evidence before claim; no inventory calls."""
    closure = _closure(rows, packet, registration, registration_event, review_parent=parent if phase == REVIEW else None)
    if phase == REVIEW:
        _require(closure is not None, "Review needs a new independent closure")
        _equal(closure[1]["missing"], previous["outcome"]["missing"], "Review preserves primary missingness")
        _require(closure[1]["state"] in {"unresolved", "no_delivery"}, "Late review cannot rescue primary outcome")
        return
    cutoff = _when(registration_event) + timedelta(hours=24)
    deadline = cutoff + timedelta(hours=24)
    submissions = _submissions(rows)
    if submissions and submissions[0][0] == "oversize":
        _oversize(submissions[0][2], submissions[0][1], registration, registration_event, by_id, artifacts)
    if not submissions or _when(submissions[0][1]) > cutoff:
        _require(closure is not None and _when(closure[0]) >= cutoff and closure[1]["state"] == "no_delivery", "No delivery requires a deadline closure")
        _equal(closure[1]["missing"], ["artifact"], "No-delivery closure gaps")
        return
    if submissions[0][0] == "oversize":
        return
    _, _, valid_verification, _, valid_adjudication = _verification_chain(registration, submissions[0][1], rows,
        _hash(artifacts["code:epiphysics.dated_delivery_verifier"]), deadline)
    if valid_verification and valid_adjudication:
        return
    _require(closure is not None and _when(closure[0]) >= deadline and closure[1]["state"] == "unresolved", "Incomplete delivery needs fixed-deadline closure")
    _equal(closure[1]["missing"], ([] if valid_verification else ["verification"]) + ([] if valid_adjudication else ["adjudication"]), "Unresolved closure gaps")


def _check_delivery(prepared):
    artifacts, metadata = prepared["artifacts"], prepared["report"]
    request, packet = _json(artifacts["request"]), _json(artifacts["packet"])
    events = _json(artifacts["ledger_prefix"])
    by_id = {event["id"]: event for event in events}
    origin, _, previous = _lineage(request, artifacts, events)
    registration_event, registration = _registered_event(packet, by_id, origin)
    rows = _scoped_records(registration, registration_event, by_id, artifacts)
    cutoff = _when(registration_event) + timedelta(hours=24)
    deadline = cutoff + timedelta(hours=24)
    semantic = _json(artifacts["semantic_parent"]) if "semantic_parent" in artifacts else _find(by_id, request["queue_parent"])
    closure = _closure(rows, packet, registration, registration_event, review_parent=semantic if request["phase"] == REVIEW else None)
    if request["phase"] == REVIEW:
        _require(closure is not None, "Review needs a new independent closure")
        outcome = deepcopy(previous["outcome"])
        _equal(closure[1]["missing"], outcome["missing"], "Review preserves primary missingness")
        _require(closure[1]["state"] in {"unresolved", "no_delivery"}, "Late review cannot rescue primary outcome")
        outcome["status"] = "terminal_no_delivery" if outcome["first_submission"] is None else "terminal_unresolved"
        outcome["review_closure"] = closure[0]["id"]
        return outcome, None, None, "prepare_public_research_map_view"
    submissions = _submissions(rows)
    outcome, result, elapsed = _empty_outcome(), None, None
    outcome["cutoff"], outcome["adjudication_deadline"] = cutoff.isoformat(), deadline.isoformat()
    outcome["dated_records"] = _dated_records(rows)
    outcome["authority"] = _authority(registration, rows, artifacts, by_id, cutoff)
    if not submissions or _when(submissions[0][1]) > cutoff:
        _require(closure is not None and _when(closure[0]) >= cutoff and closure[1]["state"] == "no_delivery", "No delivery requires a deadline closure")
        _equal(closure[1]["missing"], ["artifact"], "No-delivery closure gaps")
        outcome.update(status="no_delivery", missing=["artifact"])
        if submissions:
            outcome.update(late_submission=_submission_identity(submissions[0]), delivery_timely=False)
        return outcome, None, None, "prepare_public_research_map_view"
    kind, observation, raw = submissions[0]
    artifact_hash = observation["body"]["content_hash"] if kind == "inventory" else None
    outcome["first_submission"] = _submission_identity(submissions[0])
    outcome["delivery_timely"] = True
    if kind == "oversize":
        _oversize(raw, observation, registration, registration_event, by_id, artifacts)
        outcome.update(status="rejected_over_limit", artifact_quality=False, missing=["complete_artifact"])
        return outcome, None, None, "prepare_public_research_map_view"
    source = _blob(artifacts, _observation(by_id, registration["input_observations"]["source"]))
    manifest = _json(_blob(artifacts, _observation(by_id, registration["input_observations"]["tree_manifest"])))
    start = time.monotonic()
    result = verifier.verify_inventory(registration, source, manifest, raw)
    elapsed = time.monotonic() - start
    _require(elapsed <= MAX_SECONDS and len(_canonical(result)) <= MAX_OUTPUT_BYTES, "Verification exceeds bound")
    claims = rows["claim"]
    claim = _record(claims[0][1]) if claims else None
    if (claims and _when(claims[0][0]) <= cutoff and _bound_record(claim, registration, artifact_hash, registration["roles"]["producer"])
        and claim.get("criteria_sha256") == registration["criteria_sha256"] and claim.get("verdict") in {"pass", "fail", "abstain"} and _operative(claim, cutoff)):
        outcome["producer_claim"] = claim["verdict"]
    verification, checked, valid_verification, adjudication, valid_adjudication = _verification_chain(
        registration, observation, rows, metadata["source_hashes"]["dated_delivery_verifier.py"], deadline, result)
    if verification is not None:
        outcome["verification_available_by_cutoff"] = bool(valid_verification and _when(verification[0]) <= cutoff and _operative(checked, cutoff))
    outcome["adjudication_available_by_deadline"] = bool(valid_adjudication and _when(adjudication[0]) <= deadline)
    if valid_verification and _when(verification[0]) <= deadline and outcome["adjudication_available_by_deadline"]:
        outcome["artifact_quality"] = result["verdict"] == "pass"
        outcome["status"] = "accepted_quality" if outcome["artifact_quality"] else "rejected_quality"
        if outcome["producer_claim"] in {"pass", "fail"}:
            agrees = int(outcome["producer_claim"] == result["verdict"])
            outcome["claim_agreement"] = {"numerator": agrees, "denominator": 1, "value": float(agrees)}
        return outcome, result, elapsed, "prepare_public_research_map_view"
    outcome["missing"] = ([] if valid_verification and _when(verification[0]) <= deadline else ["verification"]) + ([] if outcome["adjudication_available_by_deadline"] else ["adjudication"])
    _require(closure is not None and _when(closure[0]) >= deadline and closure[1]["state"] == "unresolved", "Incomplete delivery needs fixed-deadline closure")
    _equal(closure[1]["missing"], outcome["missing"], "Unresolved closure gaps")
    outcome["status"] = "unresolved"
    return outcome, result, elapsed, "review_dated_delivery_evidence"


def assess_prepared_dated_delivery(prepared):
    started = time.monotonic()
    check_prepared_dated_delivery(prepared)
    report = deepcopy(prepared["report"])
    phase, elapsed, result = report["phase"], None, None
    outcome = _empty_outcome()
    if phase == PREPARATION:
        action = "bind_dated_artifact_delivery" if report["protocol_state"] == "ready_awaiting_task" else "repair_dated_evidence_quality_protocol"
    elif phase == REGISTRATION:
        action = "check_dated_artifact_delivery"
    else:
        outcome, result, elapsed, action = _check_delivery(prepared)
    report.update(status="checked", outcome=outcome,
        counts={"tasks": int(report["registration"] is not None), "deliveries": int(outcome["first_submission"] is not None),
            "late_deliveries": int(outcome["late_submission"] is not None), "decision_candidate_executions": 0, "producer_executions": 0},
        checks={"immutable_ancestry": True, "fixed_checkpoint": True, "bounded_evidence": True,
            "protocol_conformance": report["protocol_state"] != "repair_required", "separate_evidence_axes": True},
        next_step={"action": action, "reason": "Advance the fixed local delivery protocol with retained results and explicit missingness",
            "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "Protocol readiness or one locally attributed delivery; no reliability or predictive lift claim"})
    artifacts = dict(prepared["artifacts"])
    if result is not None:
        report["verification_result_sha256"] = _hash(_canonical(result))
        _put(artifacts, "verification_result", _canonical(result))
    else:
        report["verification_result_sha256"] = None
    _require(action in PHASE_NEXT_ACTIONS[phase], "Invalid declared phase successor")
    _put(artifacts, "assessment_report", _canonical(report))
    _require(time.monotonic() - started <= MAX_SECONDS, "Delivery assessment exceeds time bound")
    return {"report": report, "artifacts": artifacts,
        "actual_resources": {"first_verification_elapsed_seconds": elapsed, "decision_candidate_executions": 0,
            "producer_executions": 0, "model_calls": 0, "external_spend": 0}}


_FUNCTION_CODES = tuple((name, value, value.__code__) for name, value in list(globals().items())
    if callable(value) and getattr(value, "__module__", None) == __name__ and hasattr(value, "__code__"))
_CONSTANTS = tuple((name, deepcopy(value)) for name, value in list(globals().items()) if name.isupper()
    and name not in {"IMPLEMENTATION_SOURCE", "IMPLEMENTATION_CODE", "IMPLEMENTATION_DEPENDENCIES", "_SELF", "_FUNCTION_CODES"})
