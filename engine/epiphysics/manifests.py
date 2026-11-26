"""Retained representation manifests with stable, content-defined method identity.

Artifacts and receipts are declared provenance, not proof that code executed.
Unit names are labels, not conversions. This module never executes artifacts.
"""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, store
from .store import canonical, digest
from .assertions import _event_integrity, _hash, _read_transaction, _snapshot, _text, _time

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions)
)

ARTIFACT_ROLES = ("construction", "config", "ontology", "predictor")
DESCRIPTOR_FIELDS = {"schema_version", "encoding", "schema_id", "construction_method", "artifact_hashes",
                     "observer", "task", "horizon_seconds", "units"}
COST_FIELDS = {"basis", "elapsed_seconds", "model_calls", "external_spend", "currency", "receipt_ids"}
MANIFEST_FIELDS = {"schema_version", "method_id", "descriptor", "representation_id", "representation_hash",
                   "model_hash", "snapshot_id", "snapshot_hash", "snapshot_manifest_hash", "cutoff", "observer",
                   "artifacts", "evidence", "construction_cost", "cost_receipts"}


def _keys(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"Invalid {label} fields; require {', '.join(sorted(fields))}")


def _ids(value, label, maximum=1000):
    if type(value) is not list or len(value) > maximum:
        raise ValueError(f"{label} must be an array of at most {maximum} IDs")
    for item in value:
        _text(item, label)
    if len(set(value)) != len(value):
        raise ValueError(f"Duplicate {label}")
    return sorted(value)


def _semantics(encoding, schema_id, task, horizon_seconds, units):
    _text(encoding, "encoding")
    _text(schema_id, "schema_id")
    _keys(task, {"id", "family", "outcome_type"}, "task")
    _text(task["id"], "task id")
    _text(task["family"], "task family")
    if task["outcome_type"] != "binary":
        raise ValueError("B1 forecast tasks require binary outcome_type")
    if type(horizon_seconds) is not int or horizon_seconds <= 0:
        raise ValueError("horizon_seconds must be a positive integer")
    if type(units) is not dict or len(units) > 1000:
        raise ValueError("units must map at most 1000 field names to unit labels")
    for field, unit in units.items():
        _text(field, "unit field")
        _text(unit, "unit label")


def method_identity(descriptor) -> str:
    """Hash method semantics and artifact contents, excluding instance/run metadata."""
    _keys(descriptor, DESCRIPTOR_FIELDS, "method descriptor")
    if type(descriptor["schema_version"]) is not int or descriptor["schema_version"] != 1:
        raise ValueError("Method descriptor schema_version must be 1")
    _semantics(descriptor["encoding"], descriptor["schema_id"], descriptor["task"],
               descriptor["horizon_seconds"], descriptor["units"])
    _text(descriptor["construction_method"], "construction_method")
    _text(descriptor["observer"], "observer")
    _keys(descriptor["artifact_hashes"], ARTIFACT_ROLES, "artifact hashes")
    for role, sha256 in descriptor["artifact_hashes"].items():
        _hash(sha256, f"{role} content hash")
    return "representation-method-v1:" + digest(canonical(descriptor).encode("utf-8"))


def _cost(value):
    if value is None:
        value = {"basis": "unknown", "elapsed_seconds": None, "model_calls": None,
                 "external_spend": None, "currency": None, "receipt_ids": []}
    _keys(value, COST_FIELDS, "cost")
    value = deepcopy(value)
    if value["basis"] not in ("reported", "unknown"):
        raise ValueError("Cost basis must be reported or unknown")
    for field in ("elapsed_seconds", "external_spend"):
        amount = value[field]
        if amount is not None and (type(amount) not in (int, float) or (type(amount) is float and not math.isfinite(amount)) or amount < 0):
            raise ValueError(f"Cost {field} must be finite and nonnegative, or null")
    calls = value["model_calls"]
    if calls is not None and (type(calls) is not int or calls < 0):
        raise ValueError("Cost model_calls must be a nonnegative integer, or null")
    if value["external_spend"] is None:
        if value["currency"] is not None:
            raise ValueError("Unknown external_spend requires null currency")
    else:
        _text(value["currency"], "cost currency")
    value["receipt_ids"] = _ids(value["receipt_ids"], "receipt IDs", maximum=100)
    if value["basis"] == "unknown" and (any(value[key] is not None for key in ("elapsed_seconds", "model_calls", "external_spend", "currency")) or value["receipt_ids"]):
        raise ValueError("Unknown cost must retain null quantities and no receipts")
    if value["basis"] == "reported" and not any(value[key] is not None for key in ("elapsed_seconds", "model_calls", "external_spend")):
        raise ValueError("Reported cost must report at least one quantity")
    return value


def _observation(ledger, observation_id, now, *, snapshot=None, entries=None, verify_bytes=True):
    """Bind a full retained blob; unlike assertion spans, empty blobs are allowed."""
    _text(observation_id, "observation id")
    observation = ledger.get(observation_id, "observation")
    _event_integrity(observation)
    body = observation["body"]
    _hash(body.get("content_hash"), "Observation content_hash")
    if type(body.get("size")) is not int or body["size"] < 0:
        raise ValueError("Observation size must be a nonnegative integer")
    if _time(observation["recorded_at"], "Observation recorded_at") > now:
        raise ValueError("Observation is not yet available")
    if snapshot is not None:
        entry = entries.get(observation_id)
        if entry is None:
            raise ValueError("Observation must belong to the selected snapshot")
        if entry["event_hash"] != observation["hash"] or entry["content_hash"] != body["content_hash"]:
            raise ValueError("Snapshot manifest does not match the observation record")
        if (observation["seq"] >= snapshot["seq"] or observation["seq"] > snapshot["body"]["watermark"]
                or _time(observation["recorded_at"], "Observation recorded_at") > _time(snapshot["body"]["cutoff"], "Snapshot cutoff")):
            raise ValueError("Observation is not eligible at the snapshot cutoff")
    if verify_bytes:
        path = ledger.root / "blobs" / body["content_hash"]
        if path.is_symlink():
            raise ValueError("Retained blob must not be a symlink")
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise ValueError("Retained blob is missing or unreadable") from error
        if len(raw) != body["size"] or digest(raw) != body["content_hash"]:
            raise ValueError("Retained blob hash or size mismatch")
    return {"observation_id": observation_id, "event_hash": observation["hash"], "content_hash": body["content_hash"]}


def _model_evidence(model):
    if type(model) is not dict:
        raise ValueError("Representation model must be a JSON object")
    found = set()

    def visit(value):
        if type(value) is dict:
            for key, child in value.items():
                if key == "evidence_ids":
                    found.update(_ids(child, "model evidence IDs"))
                else:
                    visit(child)
        elif type(value) is list:
            for child in value:
                visit(child)

    visit(model)
    return found


def _build(ledger, representation_id, arguments, now, *, verify_bytes=True):
    representation = ledger.get(representation_id, "representation")
    _event_integrity(representation)
    rep = representation["body"]
    _keys(rep, {"snapshot_id", "observer", "method", "parent", "model"}, "representation")
    if _time(representation["recorded_at"], "Representation recorded_at") > now:
        raise ValueError("Representation is not yet available")
    _text(rep.get("observer"), "Representation observer")
    _text(rep.get("method"), "Representation method")
    snapshot, entries = _snapshot(ledger, rep.get("snapshot_id"), now)
    if snapshot["seq"] >= representation["seq"]:
        raise ValueError("Representation must follow its snapshot")
    expected_evidence = _model_evidence(rep.get("model"))
    if set(arguments["evidence_ids"]) != expected_evidence:
        raise ValueError("Declared evidence must exactly equal the representation model evidence references")
    artifacts = {role: _observation(ledger, arguments["artifacts"][role], now, snapshot=snapshot,
        entries=entries, verify_bytes=verify_bytes) for role in ARTIFACT_ROLES}
    evidence = [_observation(ledger, oid, now, snapshot=snapshot, entries=entries, verify_bytes=verify_bytes)
                for oid in arguments["evidence_ids"]]
    receipts = [_observation(ledger, oid, now, verify_bytes=verify_bytes)
                for oid in arguments["construction_cost"]["receipt_ids"]]
    descriptor = {"schema_version": 1, "encoding": arguments["encoding"], "schema_id": arguments["schema_id"],
        "construction_method": rep["method"], "artifact_hashes": {role: ref["content_hash"] for role, ref in artifacts.items()},
        "observer": rep["observer"], "task": arguments["task"], "horizon_seconds": arguments["horizon_seconds"],
        "units": arguments["units"]}
    return {"schema_version": 1, "method_id": method_identity(descriptor), "descriptor": descriptor,
        "representation_id": representation_id, "representation_hash": representation["hash"],
        "model_hash": digest(canonical(rep["model"]).encode("utf-8")), "snapshot_id": snapshot["id"],
        "snapshot_hash": snapshot["hash"], "snapshot_manifest_hash": snapshot["body"]["manifest_hash"],
        "cutoff": snapshot["body"]["cutoff"], "observer": rep["observer"], "artifacts": artifacts,
        "evidence": evidence, "construction_cost": arguments["construction_cost"], "cost_receipts": receipts}


def _arguments(*, encoding, schema_id, artifacts, task, horizon_seconds, units, evidence_ids, construction_cost):
    _semantics(encoding, schema_id, task, horizon_seconds, units)
    _keys(artifacts, ARTIFACT_ROLES, "artifact roles")
    for role, oid in artifacts.items():
        _text(oid, f"{role} observation id")
    return deepcopy({"encoding": encoding, "schema_id": schema_id, "artifacts": artifacts, "task": task,
        "horizon_seconds": horizon_seconds, "units": units, "evidence_ids": _ids(evidence_ids, "evidence IDs"),
        "construction_cost": _cost(construction_cost)})


def register_manifest(ledger, representation_id, *, encoding, schema_id, artifacts, task, horizon_seconds,
                      units, evidence_ids, construction_cost, event_id=None):
    """Bind an existing representation to retained artifacts and declared semantics."""
    _text(representation_id, "representation_id")
    if event_id is not None:
        _text(event_id, "event_id")
    arguments = _arguments(encoding=encoding, schema_id=schema_id, artifacts=artifacts, task=task,
        horizon_seconds=horizon_seconds, units=units, evidence_ids=evidence_ids, construction_cost=construction_cost)
    with _read_transaction(ledger):
        body = _build(ledger, representation_id, arguments, _time(ledger.clock(), "Ledger clock"), verify_bytes=False)

    def validate(recorded_at):
        checked = _build(ledger, representation_id, arguments, _time(recorded_at, "Manifest recorded_at"))
        if canonical(checked) != canonical(body):
            raise ValueError("Manifest bindings changed before append")

    return ledger.append("representation_manifest", body, event_id, validate=validate)


def _checked_manifest(ledger, manifest_id, now, *, verify_bytes=True):
    manifest = ledger.get(manifest_id, "representation_manifest")
    _event_integrity(manifest)
    body = manifest["body"]
    _keys(body, MANIFEST_FIELDS, "representation manifest")
    if type(body["schema_version"]) is not int or body["schema_version"] != 1:
        raise ValueError("Manifest schema_version must be 1")
    if _time(manifest["recorded_at"], "Manifest recorded_at") > now:
        raise ValueError("Manifest is not yet available")
    descriptor = body["descriptor"]
    if method_identity(descriptor) != body["method_id"]:
        raise ValueError("Manifest method identity mismatch")
    _keys(body["artifacts"], ARTIFACT_ROLES, "manifest artifacts")
    if type(body["evidence"]) is not list or type(body["cost_receipts"]) is not list:
        raise ValueError("Manifest evidence and cost_receipts must be arrays")
    refs = list(body["artifacts"].values()) + body["evidence"] + body["cost_receipts"]
    for ref in refs:
        _keys(ref, {"observation_id", "event_hash", "content_hash"}, "manifest observation reference")
    arguments = _arguments(encoding=descriptor["encoding"], schema_id=descriptor["schema_id"],
        artifacts={role: ref["observation_id"] for role, ref in body["artifacts"].items()}, task=descriptor["task"],
        horizon_seconds=descriptor["horizon_seconds"], units=descriptor["units"],
        evidence_ids=[ref["observation_id"] for ref in body["evidence"]], construction_cost=body["construction_cost"])
    # Receipts must have existed when this manifest was recorded, not merely now.
    rebuilt = _build(ledger, body["representation_id"], arguments,
        _time(manifest["recorded_at"], "Manifest recorded_at"), verify_bytes=verify_bytes)
    if canonical(rebuilt) != canonical(body):
        raise ValueError("Manifest does not match its bound representation, snapshot, or artifacts")
    return manifest


def forecast_manifest(ledger, manifest_id, question_id, probability, *, status="predicted", reason=None,
                      inference_cost=None, event_id=None):
    """Record a forecast bound to a manifest, using the existing forecast safeguards.

    This adapter records a supplied probability; it does not run the predictor.
    Construction cost is referenced once by manifest, not charged again here.
    """
    _text(manifest_id, "manifest_id")
    _text(question_id, "question_id")
    if event_id is not None:
        _text(event_id, "event_id")
    cost = _cost(inference_cost)
    def bindings(now, *, verify_bytes):
        manifest = _checked_manifest(ledger, manifest_id, now, verify_bytes=verify_bytes)
        body = manifest["body"]
        question = ledger.get(question_id, "question")
        _event_integrity(question)
        q = question["body"]
        task = body["descriptor"]["task"]
        if q["family"] != task["family"] or q["outcome_type"] != task["outcome_type"]:
            raise ValueError("Question family and outcome_type must match the manifest task")
        horizon = (_time(q["resolve_after"], "Question resolve_after") - _time(body["cutoff"], "Manifest cutoff")).total_seconds()
        if horizon != body["descriptor"]["horizon_seconds"]:
            raise ValueError("Question resolution horizon must match the manifest snapshot cutoff")
        receipts = [_observation(ledger, oid, now, verify_bytes=verify_bytes) for oid in cost["receipt_ids"]]
        model = {"identifier": "sha256:" + body["descriptor"]["artifact_hashes"]["predictor"],
                 "representation_manifest_id": manifest_id, "representation_manifest_hash": manifest["hash"],
                 "method_id": body["method_id"]}
        return {"snapshot_id": body["snapshot_id"], "method": body["method_id"],
                "representation_id": body["representation_id"], "model": model, "question_hash": question["hash"],
                "cost": {"construction_manifest_id": manifest_id, "inference_cost": cost, "receipt_refs": receipts}}

    # Build only immutable metadata before append so exact retries survive blob loss.
    with _read_transaction(ledger):
        prepared = bindings(_time(ledger.clock(), "Ledger clock"), verify_bytes=False)

    def validate(recorded_at):
        checked = bindings(_time(recorded_at, "Forecast recorded_at"), verify_bytes=True)
        if canonical(checked) != canonical(prepared):
            raise ValueError("Forecast manifest bindings changed before append")

    return ledger.forecast(question_id, prepared["snapshot_id"], prepared["method"], probability,
        model=prepared["model"], representation_id=prepared["representation_id"], status=status, reason=reason,
        cost=prepared["cost"], event_id=event_id, validate=validate)
