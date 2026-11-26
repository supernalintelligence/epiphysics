"""Exercise representation identity and forecast binding against the actual API.

Artifacts are inert captured bytes. These synthetic capability checks do not run
constructors or predictors, establish semantic preservation, or measure lift.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import manifests, store
from .store import Ledger, canonical, digest

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, manifests)
)

METRIC = "representation_manifest_preservation"
ARTIFACT_BYTES = {
    "construction": b"raise RuntimeError('Captured construction must never execute')\n",
    "config": b'{"fixture":"manifest-check","seed":7}',
    "ontology": b'{"invoice_amount":{"unit":"USD"}}',
    "predictor": b"raise RuntimeError('Captured predictor must never execute')\n",
}


def _unknown_cost():
    return {"basis": "unknown", "elapsed_seconds": None, "model_calls": None,
            "external_spend": None, "currency": None, "receipt_ids": []}


def _representation(fixture, *, snapshot=None, evidence=None, observer="manifest-probe",
                    method="synthetic-builder-v1", label="Invoice"):
    return fixture["ledger"].representation(
        (snapshot or fixture["snapshot"])["id"],
        {"entities": [{"id": "invoice", "label": label, "basis": "reported",
                       "evidence_ids": evidence or [fixture["source"]["id"]]}], "relations": [],
         "evidence_ids": [fixture["extra"]["id"]]},
        observer=observer, method=method)


@contextmanager
def _fixture():
    clock = ["2026-11-24T10:00:00+00:00"]
    with TemporaryDirectory(prefix="epiphysics-manifest-check-") as directory:
        ledger = Ledger(directory, clock=lambda: clock[0])
        try:
            source = ledger.capture("synthetic:invoice", b"Invoice A is for 12 USD.")
            artifacts = {role: ledger.capture(f"synthetic:artifact:{role}", raw)
                         for role, raw in ARTIFACT_BYTES.items()}
            extra = ledger.capture("synthetic:additional-input", b"Declared contextual input.")
            snapshot = ledger.snapshot()
            clock[0] = "2026-11-24T10:01:00+00:00"
            receipt = ledger.capture("synthetic:construction-receipt", b"Fictional local construction: 0.25 seconds.")
            fixture = {"ledger": ledger, "clock": clock, "source": source, "artifacts": artifacts,
                       "snapshot": snapshot, "extra": extra, "receipt": receipt}
            fixture["representation"] = _representation(fixture)
            fixture["cost"] = {"basis": "reported", "elapsed_seconds": 0.25, "model_calls": 0,
                               "external_spend": 0, "currency": "USD", "receipt_ids": [receipt["id"]]}
            yield fixture
        finally:
            ledger.close()


def _register(fixture, **changes):
    arguments = {"representation_id": fixture["representation"]["id"], "encoding": "graph",
                 "schema_id": "synthetic-invoice-v1", "artifacts": {role: event["id"] for role, event in fixture["artifacts"].items()},
                 "task": {"id": "invoice-paid", "family": "contract_obligation", "outcome_type": "binary"},
                 "horizon_seconds": 600, "units": {"invoice_amount": "USD"},
                 "evidence_ids": [fixture["source"]["id"], fixture["extra"]["id"]],
                 "construction_cost": deepcopy(fixture["cost"])}
    arguments.update(changes)
    return manifests.register_manifest(fixture["ledger"], **arguments)


def _question(fixture, **changes):
    arguments = {"text": "Will invoice A be paid?", "deadline": "2026-11-24T10:05:00+00:00",
                 "resolve_after": "2026-11-24T10:10:00+00:00", "resolution_rule": "Fictional payment receipt",
                 "family": "contract_obligation"}
    arguments.update(changes)
    return fixture["ledger"].question(**arguments)


def _rejects_without_append(fixture, operation):
    before = len(fixture["ledger"].events())
    try:
        operation()
    except ValueError:
        return len(fixture["ledger"].events()) == before
    return False


def _stable_method(fixture):
    first = _register(fixture)
    fixture["clock"][0] = "2026-11-24T10:02:00+00:00"
    ledger = fixture["ledger"]
    source = ledger.capture("synthetic:invoice", b"Invoice A is for 12 USD.")
    artifacts = {role: ledger.capture(f"synthetic:artifact:{role}", raw)["id"]
                 for role, raw in ARTIFACT_BYTES.items()}
    snapshot = ledger.snapshot()
    representation = _representation(fixture, snapshot=snapshot, evidence=[source["id"]], label="New payload, same construction method")
    second = _register(fixture, representation_id=representation["id"], artifacts=artifacts,
                       evidence_ids=[source["id"], fixture["extra"]["id"]], construction_cost=_unknown_cost())
    return (first["body"]["method_id"] == second["body"]["method_id"]
            and first["body"]["snapshot_id"] != second["body"]["snapshot_id"]
            and first["body"]["model_hash"] != second["body"]["model_hash"]
            and all(first["body"]["artifacts"][role]["observation_id"] != second["body"]["artifacts"][role]["observation_id"]
                    for role in ARTIFACT_BYTES))


def _distinct_encodings(fixture):
    graph = _register(fixture)
    text = _register(fixture, encoding="text")
    question = _question(fixture)
    forecasts = [manifests.forecast_manifest(fixture["ledger"], row["id"], question["id"], 0.5)
                 for row in (graph, text)]
    return (graph["body"]["method_id"] != text["body"]["method_id"]
            and len({row["body"]["method"] for row in forecasts}) == 2
            and len({row["body"]["model"]["identifier"] for row in forecasts}) == 1)


def _artifact_identity(role):
    def check(fixture):
        original = _register(fixture)
        fixture["clock"][0] = "2026-11-24T10:02:00+00:00"
        changed = fixture["ledger"].capture(f"synthetic:artifact:{role}", ARTIFACT_BYTES[role] + b"\nchanged artifact bytes")
        snapshot = fixture["ledger"].snapshot()
        representation = _representation(fixture, snapshot=snapshot)
        artifacts = {key: row["id"] for key, row in fixture["artifacts"].items()}
        artifacts[role] = changed["id"]
        updated = _register(fixture, representation_id=representation["id"], artifacts=artifacts)
        return (original["body"]["method_id"] != updated["body"]["method_id"]
                and updated["body"]["descriptor"]["artifact_hashes"][role] == digest(ARTIFACT_BYTES[role] + b"\nchanged artifact bytes"))
    return check


def _semantic_identity(fixture):
    original = _register(fixture)
    variants = [{"schema_id": "synthetic-invoice-v2"}, {"horizon_seconds": 601},
                {"units": {"invoice_amount": "EUR"}},
                {"task": {"id": "different-question", "family": "contract_obligation", "outcome_type": "binary"}},
                {"task": {"id": "invoice-paid", "family": "organization", "outcome_type": "binary"}},
                {"representation_id": _representation(fixture, observer="another-observer")["id"]},
                {"representation_id": _representation(fixture, method="synthetic-builder-v2")["id"]}]
    methods = {original["body"]["method_id"], *(_register(fixture, **change)["body"]["method_id"] for change in variants)}
    return len(methods) == len(variants) + 1


def _preserved_inputs(fixture):
    record = _register(fixture)
    body = fixture["ledger"].get(record["id"], "representation_manifest")["body"]
    representation = fixture["representation"]
    return (body["representation_id"] == representation["id"]
            and body["representation_hash"] == representation["hash"]
            and body["model_hash"] == digest(canonical(representation["body"]["model"]).encode())
            and body["snapshot_id"] == fixture["snapshot"]["id"]
            and body["snapshot_hash"] == fixture["snapshot"]["hash"]
            and body["snapshot_manifest_hash"] == fixture["snapshot"]["body"]["manifest_hash"]
            and body["descriptor"]["units"] == {"invoice_amount": "USD"}
            and {row["observation_id"] for row in body["evidence"]} == {fixture["source"]["id"], fixture["extra"]["id"]}
            and body["construction_cost"] == fixture["cost"]
            and [row["observation_id"] for row in body["cost_receipts"]] == [fixture["receipt"]["id"]]
            and all(body["artifacts"][role]["content_hash"] == digest(raw) for role, raw in ARTIFACT_BYTES.items()))


def _unknown_preserved(fixture):
    record = _register(fixture, construction_cost=_unknown_cost())
    forecast = manifests.forecast_manifest(fixture["ledger"], record["id"], _question(fixture)["id"], 0.5)
    return (record["body"]["construction_cost"] == _unknown_cost()
            and forecast["body"]["cost"]["inference_cost"] == _unknown_cost())


def _late_artifact(fixture):
    late = fixture["ledger"].capture("synthetic:late-artifact", b"late artifact", published_at="2020-01-01T00:00:00+00:00")
    artifacts = {key: row["id"] for key, row in fixture["artifacts"].items()}
    artifacts["config"] = late["id"]
    return _rejects_without_append(fixture, lambda: _register(fixture, artifacts=artifacts))


def _corrupt_artifact(fixture):
    event = fixture["artifacts"]["predictor"]
    (fixture["ledger"].root / "blobs" / event["body"]["content_hash"]).write_bytes(b"corrupt predictor")
    return _rejects_without_append(fixture, lambda: _register(fixture))


def _duplicate_evidence(fixture):
    return _rejects_without_append(fixture, lambda: _register(fixture, evidence_ids=[fixture["source"]["id"]] * 2))


def _missing_evidence(fixture):
    return _rejects_without_append(fixture, lambda: _register(fixture, evidence_ids=[fixture["extra"]["id"]]))


def _forecast_binding(fixture):
    manifest = _register(fixture)
    question = _question(fixture)
    forecast = manifests.forecast_manifest(fixture["ledger"], manifest["id"], question["id"], 0.7,
                                         inference_cost=fixture["cost"])
    body = fixture["ledger"].get(forecast["id"], "forecast")["body"]
    return (body["method"] == manifest["body"]["method_id"]
            and body["snapshot_id"] == fixture["snapshot"]["id"]
            and body["representation_id"] == fixture["representation"]["id"]
            and body["model"] == {"identifier": "sha256:" + fixture["artifacts"]["predictor"]["body"]["content_hash"],
                                  "representation_manifest_id": manifest["id"], "representation_manifest_hash": manifest["hash"],
                                  "method_id": manifest["body"]["method_id"]}
            and body["cost"]["construction_manifest_id"] == manifest["id"]
            and body["cost"]["inference_cost"] == fixture["cost"]
            and [row["observation_id"] for row in body["cost"]["receipt_refs"]] == [fixture["receipt"]["id"]])


def _forecast_rejection(changes):
    def check(fixture):
        manifest = _register(fixture)
        question = _question(fixture, **changes)
        return _rejects_without_append(fixture, lambda: manifests.forecast_manifest(fixture["ledger"], manifest["id"], question["id"], 0.5))
    return check


def _duplicate_forecast(fixture):
    original = _register(fixture)
    same_method = _register(fixture)
    question = _question(fixture)
    manifests.forecast_manifest(fixture["ledger"], original["id"], question["id"], 0.5)
    return _rejects_without_append(fixture, lambda: manifests.forecast_manifest(fixture["ledger"], same_method["id"], question["id"], 0.8))


def _tampered_forecast_input(which):
    def check(fixture):
        manifest = _register(fixture)
        question = _question(fixture)
        ledger = fixture["ledger"]
        if which == "manifest":
            body = deepcopy(manifest["body"])
            body["descriptor"]["units"] = {"invoice_amount": "EUR"}
            ledger.db.execute("DROP TRIGGER events_no_update")
            ledger.db.execute("UPDATE events SET body=? WHERE id=?", (canonical(body), manifest["id"]))
            ledger.db.commit()
        else:
            event = fixture["artifacts"]["construction"]
            (ledger.root / "blobs" / event["body"]["content_hash"]).write_bytes(b"artifact changed after registration")
        return _rejects_without_append(fixture, lambda: manifests.forecast_manifest(ledger, manifest["id"], question["id"], 0.5))
    return check


def _forecast_append_mutation(which):
    def check(fixture):
        manifest = _register(fixture)
        question = _question(fixture)
        ledger = fixture["ledger"]
        inference_receipt = ledger.capture("synthetic:inference-receipt", b"Fictional inference receipt, separate from construction.")
        inference_cost = {**fixture["cost"], "receipt_ids": [inference_receipt["id"]]}
        target = fixture["artifacts"]["predictor"] if which == "predictor" else inference_receipt
        blob = ledger.root / "blobs" / target["body"]["content_hash"]
        original_append = ledger.append
        changed = False
        def changing_append(kind, body, event_id=None, **kwargs):
            nonlocal changed
            if kind == "forecast":
                blob.write_bytes(b"Changed after forecast preparation but before append validation")
                changed = True
            return original_append(kind, body, event_id, **kwargs)
        ledger.append = changing_append
        try:
            rejected = _rejects_without_append(fixture, lambda: manifests.forecast_manifest(
                ledger, manifest["id"], question["id"], 0.5, inference_cost=inference_cost))
            return changed and rejected
        finally:
            ledger.append = original_append
    return check


def _replay_after_blob_loss(fixture):
    ledger = fixture["ledger"]
    manifest = _register(fixture)
    question = _question(fixture)
    inference_receipt = ledger.capture("synthetic:inference-replay-receipt", b"Fictional inference receipt retained in replay metadata.")
    inference_cost = {**fixture["cost"], "receipt_ids": [inference_receipt["id"]]}
    first = manifests.forecast_manifest(ledger, manifest["id"], question["id"], 0.5,
        inference_cost=inference_cost, event_id="forecast-replay")
    count = len(ledger.events())
    for observation in (fixture["artifacts"]["predictor"], inference_receipt):
        (ledger.root / "blobs" / observation["body"]["content_hash"]).unlink()
    fixture["clock"][0] = "2026-11-24T10:11:00+00:00"
    replay = manifests.forecast_manifest(ledger, manifest["id"], question["id"], 0.5,
        inference_cost=inference_cost, event_id="forecast-replay")
    changed_request_rejected = _rejects_without_append(fixture, lambda: manifests.forecast_manifest(
        ledger, manifest["id"], question["id"], 0.8, inference_cost=inference_cost, event_id="forecast-replay"))
    return replay == first and len(ledger.events()) == count and changed_request_rejected


CHECKS = (
    ("stable_method_across_snapshots_and_recapture", _stable_method),
    ("distinct_encodings_same_predictor_do_not_collide", _distinct_encodings),
    *((f"changed_{role}_artifact_changes_identity", _artifact_identity(role)) for role in ARTIFACT_BYTES),
    ("semantic_descriptor_fields_change_identity", _semantic_identity),
    ("preserve_inputs_snapshot_units_and_reported_cost", _preserved_inputs),
    ("unknown_construction_and_inference_cost_remain_unknown", _unknown_preserved),
    ("reject_late_artifact_despite_old_publication", _late_artifact),
    ("reject_corrupt_artifact_at_registration", _corrupt_artifact),
    ("reject_duplicate_evidence_declaration", _duplicate_evidence),
    ("reject_missing_representation_evidence", _missing_evidence),
    ("bind_forecast_to_exact_manifest_and_cost", _forecast_binding),
    ("reject_forecast_horizon_mismatch", _forecast_rejection({"resolve_after": "2026-11-24T10:11:00+00:00"})),
    ("reject_forecast_family_mismatch", _forecast_rejection({"family": "organization"})),
    ("reject_duplicate_method_question_across_manifests", _duplicate_forecast),
    ("reject_tampered_manifest_at_forecast", _tampered_forecast_input("manifest")),
    ("reject_tampered_artifact_at_forecast", _tampered_forecast_input("artifact")),
    ("reject_predictor_changed_at_forecast_append", _forecast_append_mutation("predictor")),
    ("reject_inference_receipt_changed_at_forecast_append", _forecast_append_mutation("receipt")),
    ("exact_forecast_replay_survives_blob_loss", _replay_after_blob_loss),
)


def run_manifest_checks():
    rows = []
    for check_id, operation in CHECKS:
        row = {"id": check_id, "metric": METRIC, "passed": False}
        try:
            with _fixture() as fixture:
                row["passed"] = bool(operation(fixture))
            if not row["passed"]:
                row["diagnostic"] = "Implementation did not satisfy the declared check"
        except Exception as error:
            row["diagnostic"] = f"{type(error).__name__}: {error}"[:400]
        rows.append(row)
    count = {"passed": sum(row["passed"] for row in rows), "checks": len(CHECKS)}
    return {"version": "representation-manifest-probes-v2", "checks": rows,
            "counts": {METRIC: count}, "metrics": {METRIC: count["passed"] / count["checks"]},
            "all_passed": all(row["passed"] for row in rows),
            "interpretation": "Actual manifest API exercised on isolated synthetic ledgers. Identity and input/forecast binding only; no artifact execution, transformation preservation, semantic truth, independent cost verification, or predictive/business lift."}
