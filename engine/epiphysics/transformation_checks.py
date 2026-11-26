"""Execute fixed graph operations on isolated ledgers and check their receipts.

This measures identity/projection conformance, not split/merge preservation,
semantic equivalence, learned transformations, or predictive/business advantage.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, store, transforms
from .store import Ledger, canonical, digest

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions, manifests, transforms)
)

METRIC = "transformation_preservation"


def _unknown_cost():
    return {"basis": "unknown", "elapsed_seconds": None, "model_calls": None,
            "external_spend": None, "currency": None, "receipt_ids": []}


def _evidence(model):
    result = set()
    def visit(value):
        if isinstance(value, dict):
            result.update(value.get("evidence_ids", []))
            for key, child in value.items():
                if key != "evidence_ids":
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(model)
    return result


def _register_parent(fixture, model):
    representation = fixture["ledger"].representation(fixture["snapshot"]["id"], model,
        observer="graph-transform-probe", method="synthetic-graph-builder")
    manifest = manifests.register_manifest(fixture["ledger"], representation["id"],
        encoding="directed-graph", schema_id="epiphysics.graph.v1",
        artifacts={role: event["id"] for role, event in fixture["artifacts"].items()},
        task={"id": "graph-probe", "family": "collective", "outcome_type": "binary"},
        horizon_seconds=600, units={"money": "USD", "mass": "kg"},
        evidence_ids=sorted(_evidence(model)), construction_cost=_unknown_cost())
    return representation, manifest


@contextmanager
def _fixture(*, late=None, malformed=None):
    clock = ["2026-11-24T10:00:00+00:00"]
    with TemporaryDirectory(prefix="epiphysics-transform-check-") as directory:
        ledger = Ledger(directory, clock=lambda: clock[0])
        try:
            sources = {name: ledger.capture("synthetic:graph:" + name, ("Fictional graph evidence " + name).encode())
                       for name in ("a", "b", "c", "ab-supplies", "ab-owes", "ba-reports", "bc-funds", "cc-observes")}
            model = {"entities": [
                {"id": "a", "basis": "reported", "evidence_ids": [sources["a"]["id"]], "amount": {"value": 12, "unit": "USD"}},
                {"id": "b", "basis": "reported", "evidence_ids": [sources["b"]["id"]], "mass": {"value": 4, "unit": "kg"}},
                {"id": "c", "basis": "reported", "evidence_ids": [sources["c"]["id"]], "amount": {"value": 7, "unit": "USD"}}],
                "relations": [
                    {"source": a, "target": b, "type": kind, "basis": "reported", "evidence_ids": [sources[source]["id"]], "weight": 1}
                    for a, b, kind, source in (("a", "b", "supplies", "ab-supplies"), ("a", "b", "owes", "ab-owes"),
                                              ("b", "a", "reports", "ba-reports"), ("b", "c", "funds", "bc-funds"),
                                              ("c", "c", "observes", "cc-observes"))],
                "units": {"money": "USD", "mass": "kg"}, "context": {"label": "Synthetic graph", "missingness": None}}
            artifacts = {role: ledger.capture("synthetic:parent-artifact:" + role, ("Inert parent artifact " + role).encode())
                         for role in ("construction", "config", "ontology", "predictor")}
            deferred = []
            def capture_input(name, raw, defer=False):
                event_id = "input-" + name
                if defer:
                    deferred.append((name, raw, event_id))
                    return event_id
                return ledger.capture("synthetic:transform:" + name, raw, event_id=event_id)["id"]
            implementation = capture_input("implementation", transforms.IMPLEMENTATION_SOURCE, late == "implementation")
            dependencies = {module.__name__: capture_input(module.__name__, module.IMPLEMENTATION_SOURCE,
                            late == "dependency" and module is store) for module in (store, assertions, manifests)}
            malformed_json = br'{"\ud800": 1, "\ud800": 2}'
            project_config = malformed_json if malformed == "config" else canonical({"entity_ids": ["b", "a"]}).encode()
            configs = {"identity": capture_input("identity-config", b"{}"),
                       "project": capture_input("project-config", project_config, late == "config"),
                       "unknown": capture_input("unknown-config", canonical({"entity_ids": ["missing"]}).encode())}
            recipes = {}
            for name, operation in (("identity", "identity"), ("project", "project_entities"), ("unknown", "project_entities"), ("declared", "project_entities")):
                recipe = {"schema_version": 1, "operation": operation, "config_observation_id": configs["project" if name == "declared" else name],
                          "implementation_observation_id": implementation, "implementation_sha256": digest(transforms.IMPLEMENTATION_SOURCE),
                          "dependency_observations": dependencies, "output_schema": "epiphysics.graph.v1"}
                if name == "declared":
                    recipe["output_model"] = {"entities": [], "relations": []}
                raw_recipe = malformed_json if malformed == "recipe" and name == "project" else canonical(recipe).encode()
                recipes[name] = capture_input(name + "-recipe", raw_recipe, late == "recipe" and name == "project")
            snapshot = ledger.snapshot()
            clock[0] = "2026-11-24T10:01:00+00:00"
            for name, raw, event_id in deferred:
                ledger.capture("synthetic:transform:" + name, raw, published_at="2020-01-01T00:00:00+00:00", event_id=event_id)
            fixture = {"ledger": ledger, "clock": clock, "model": model, "sources": sources, "artifacts": artifacts,
                       "implementation": implementation, "dependencies": dependencies, "configs": configs,
                       "recipes": recipes, "snapshot": snapshot}
            fixture["representation"], fixture["manifest"] = _register_parent(fixture, model)
            yield fixture
        finally:
            ledger.close()


def _run(fixture, recipe="project", key="probe"):
    return transforms.execute_graph_transform(fixture["ledger"], fixture["manifest"]["id"], fixture["recipes"][recipe], run_key=key)


def _completed(fixture, recipe="project", key="probe"):
    result = _run(fixture, recipe, key)
    if result["kind"] != "graph_transform_completed":
        raise ValueError("Expected completed graph operation: " + str(result["body"].get("error")))
    return result


def _projection_expected(fixture):
    expected = deepcopy(fixture["model"])
    expected["entities"] = expected["entities"][:2]
    expected["relations"] = expected["relations"][:3]
    return expected


def _identity(fixture):
    body = _completed(fixture, "identity")["body"]
    return (body["output_model"] == fixture["model"] and body["canonical_exact"] is True
            and body["losses"] == {"removed_entities": [], "removed_relations": [], "removed_evidence_ids": []}
            and body["output_model_hash"] == digest(canonical(fixture["model"]).encode()))


def _projection(fixture):
    body = _completed(fixture)["body"]
    expected = _projection_expected(fixture)
    return (body["output_model"] == expected and body["output_model"] != fixture["model"]
            and body["canonical_exact"] is False and body["output_model_hash"] == digest(canonical(expected).encode()))


def _attributes(fixture):
    output = _completed(fixture)["body"]["output_model"]
    return (output["units"] == fixture["model"]["units"] and output["context"] == fixture["model"]["context"]
            and output["entities"] == fixture["model"]["entities"][:2]
            and output["relations"] == fixture["model"]["relations"][:3])


def _losses(fixture):
    body = _completed(fixture)["body"]
    expected = _projection_expected(fixture)
    return (body["losses"]["removed_entities"] == fixture["model"]["entities"][2:]
            and body["losses"]["removed_relations"] == fixture["model"]["relations"][3:]
            and set(body["losses"]["removed_evidence_ids"]) == _evidence(fixture["model"]) - _evidence(expected)
            and len(body["losses"]["removed_evidence_ids"]) == len(set(body["losses"]["removed_evidence_ids"])))


def _mapping(fixture):
    body = _completed(fixture)["body"]
    expected = []
    for index, relation in enumerate(fixture["model"]["relations"]):
        key = {field: relation[field] for field in ("source", "target", "type")}
        expected.append({"source_key": key, "output_key": key if index < 3 else None})
    return (body["source_to_output"]["entities"] == {"a": "a", "b": "b", "c": None}
            and sorted(body["source_to_output"]["relations"], key=canonical) == sorted(expected, key=canonical))


def _immutable(fixture):
    ledger = fixture["ledger"]
    original = ledger.events()
    blobs = {row["body"]["content_hash"]: (ledger.root / "blobs" / row["body"]["content_hash"]).read_bytes()
             for row in ledger.events("observation")}
    _completed(fixture)
    return (all(ledger.get(row["id"]) == row for row in original)
            and all((ledger.root / "blobs" / sha).read_bytes() == raw for sha, raw in blobs.items())
            and ledger.get(fixture["representation"]["id"])["body"]["model"] == fixture["model"])


def _receipts(fixture):
    completed = _completed(fixture)
    body = completed["body"]
    starts = fixture["ledger"].events("graph_transform_started")
    request = body["request"]
    inputs = body["inputs"]
    return (len(starts) == 1 and starts[0]["body"]["request"] == request and starts[0]["seq"] < completed["seq"]
            and request["parent_manifest"] == {"id": fixture["manifest"]["id"], "hash": fixture["manifest"]["hash"]}
            and request["parent_representation"]["model_hash"] == fixture["manifest"]["body"]["model_hash"]
            and inputs["parent_manifest_id"] == fixture["manifest"]["id"]
            and inputs["parent_representation_id"] == fixture["representation"]["id"]
            and inputs["recipe"]["observation_id"] == fixture["recipes"]["project"]
            and inputs["implementation"]["content_hash"] == digest(transforms.IMPLEMENTATION_SOURCE)
            and body["recipe_descriptor"]["operation"] == "project_entities"
            and body["resources"]["model_calls"] == 0 and body["resources"]["external_spend"] == 0)


def _replay(fixture):
    original = _completed(fixture)
    ledger = fixture["ledger"]
    count = len(ledger.events())
    implementation = ledger.get(fixture["implementation"])
    (ledger.root / "blobs" / implementation["body"]["content_hash"]).unlink()
    return _run(fixture) == original and len(ledger.events()) == count


def _rejected(fixture, recipe="project", key="probe"):
    before = len(fixture["ledger"].events())
    original = deepcopy(fixture["representation"])
    terminal = _run(fixture, recipe, key)
    events = fixture["ledger"].events()[before:]
    return (terminal["kind"] == "graph_transform_rejected" and terminal["body"]["result"] == "rejected"
            and [row["kind"] for row in events] == ["graph_transform_started", "graph_transform_rejected"]
            and fixture["ledger"].get(original["id"]) == original)


def _rejected_replay(fixture):
    if not _rejected(fixture, "unknown"):
        return False
    terminal = fixture["ledger"].events("graph_transform_rejected")[0]
    count = len(fixture["ledger"].events())
    config = fixture["ledger"].get(fixture["configs"]["unknown"])
    (fixture["ledger"].root / "blobs" / config["body"]["content_hash"]).unlink()
    return _run(fixture, "unknown") == terminal and len(fixture["ledger"].events()) == count


def _changed_request(fixture):
    _completed(fixture)
    count = len(fixture["ledger"].events())
    try:
        _run(fixture, "identity")
    except ValueError:
        return len(fixture["ledger"].events()) == count
    return False


def _tampered(which):
    def check(fixture):
        ledger = fixture["ledger"]
        observation_id = (fixture["implementation"] if which == "implementation" else fixture["configs"]["project"]
                          if which == "config" else fixture["sources"]["a"]["id"])
        observation = ledger.get(observation_id)
        (ledger.root / "blobs" / observation["body"]["content_hash"]).write_bytes(b"Changed bytes after snapshot")
        return _rejected(fixture)
    return check


def _invalid_graph(fixture):
    model = deepcopy(fixture["model"])
    model["relations"][0]["target"] = "missing"
    # A legacy/raw representation may exist; transformation must validate its shape.
    representation = fixture["ledger"].append("representation", {"snapshot_id": fixture["snapshot"]["id"],
        "observer": "graph-transform-probe", "method": "legacy-fixture", "parent": None, "model": model})
    fixture["representation"] = representation
    fixture["manifest"] = manifests.register_manifest(fixture["ledger"], representation["id"],
        encoding="directed-graph", schema_id="epiphysics.graph.v1",
        artifacts={role: event["id"] for role, event in fixture["artifacts"].items()},
        task={"id": "graph-probe", "family": "collective", "outcome_type": "binary"},
        horizon_seconds=600, units={"money": "USD", "mass": "kg"}, evidence_ids=sorted(_evidence(model)), construction_cost=_unknown_cost())
    return _rejected(fixture)


def _concurrent(fixture):
    barrier = threading.Barrier(2)
    results = []
    def worker():
        ledger = Ledger(fixture["ledger"].root, clock=lambda: fixture["clock"][0])
        try:
            barrier.wait(timeout=5)
            results.append(transforms.execute_graph_transform(ledger, fixture["manifest"]["id"],
                fixture["recipes"]["project"], run_key="race"))
        except ValueError:
            results.append(None)
        except Exception as error:
            results.append({"error": str(error)})
        finally:
            ledger.close()
    workers = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=12)
    completed = fixture["ledger"].events("graph_transform_completed")
    return (all(not worker.is_alive() for worker in workers) and len(results) == 2 and len(completed) == 1
            and len(fixture["ledger"].events("graph_transform_started")) == 1
            and fixture["ledger"].events("graph_transform_rejected") == []
            and any(result == completed[0] for result in results)
            and all(result is None or result == completed[0] for result in results))


def _interrupted(fixture):
    class SimulatedInterruption(BaseException):
        pass
    ledger = fixture["ledger"]
    original_append = ledger.append
    def interrupted_append(kind, *args, **kwargs):
        if kind == "graph_transform_completed":
            raise SimulatedInterruption()
        return original_append(kind, *args, **kwargs)
    ledger.append = interrupted_append
    try:
        try:
            _run(fixture)
        except SimulatedInterruption:
            pass
    finally:
        ledger.append = original_append
    count = len(ledger.events())
    try:
        _run(fixture)
    except ValueError:
        return (len(ledger.events()) == count and len(ledger.events("graph_transform_started")) == 1
                and ledger.events("graph_transform_completed") == [] and ledger.events("graph_transform_rejected") == [])
    return False


def _completion_mutation(which):
    def check(fixture):
        ledger = fixture["ledger"]
        observation_id = fixture["configs"]["project"] if which == "config" else fixture["sources"]["a"]["id"]
        observation = ledger.get(observation_id)
        path = ledger.root / "blobs" / observation["body"]["content_hash"]
        original_append = ledger.append
        changed = False
        def changing_append(kind, *args, **kwargs):
            nonlocal changed
            if kind == "graph_transform_completed":
                path.write_bytes(b"Changed after preparation and before completion validation")
                changed = True
            return original_append(kind, *args, **kwargs)
        ledger.append = changing_append
        try:
            rejected = _rejected(fixture)
            return changed and rejected and ledger.events("graph_transform_completed") == []
        finally:
            ledger.append = original_append
    return check


def _unicode_rejection_replay(which):
    def check(fixture):
        ledger = fixture["ledger"]
        observation_id = fixture["recipes"]["project"] if which == "recipe" else fixture["configs"]["project"]
        observation = ledger.get(observation_id)
        path = ledger.root / "blobs" / observation["body"]["content_hash"]
        raw = path.read_bytes()
        if not _rejected(fixture):
            return False
        terminal = ledger.events("graph_transform_rejected")[0]
        canonical(terminal).encode("utf-8")
        if len(terminal["body"]["error"]["message"]) > 400 or path.read_bytes() != raw or not ledger.verify()["valid"]:
            return False
        count = len(ledger.events())
        path.unlink()
        return _run(fixture) == terminal and len(ledger.events()) == count
    return check


CHECKS = (
    ("execute_identity_with_exact_model_and_zero_loss", _identity, {}),
    ("execute_induced_projection_with_directed_parallel_edges", _projection, {}),
    ("preserve_units_evidence_and_metadata", _attributes, {}),
    ("account_for_all_removed_entities_relations_and_evidence", _losses, {}),
    ("map_each_parent_entity_and_typed_relation", _mapping, {}),
    ("leave_parent_events_and_retained_bytes_unchanged", _immutable, {}),
    ("bind_started_and_completed_receipts_to_exact_inputs", _receipts, {}),
    ("replay_completed_run_after_blob_loss_without_append", _replay, {}),
    ("replay_rejected_run_after_blob_loss_without_append", _rejected_replay, {}),
    ("reject_changed_request_under_same_run_key", _changed_request, {}),
    ("record_rejection_for_unknown_selected_entity", lambda fixture: _rejected(fixture, "unknown"), {}),
    ("reject_caller_declared_output", lambda fixture: _rejected(fixture, "declared"), {}),
    *((f"reject_late_{kind}_despite_old_publication", _rejected, {"late": kind})
      for kind in ("recipe", "config", "implementation", "dependency")),
    ("reject_tampered_implementation_bytes", _tampered("implementation"), {}),
    ("reject_tampered_configuration_bytes", _tampered("config"), {}),
    ("reject_tampered_parent_evidence_bytes", _tampered("parent"), {}),
    ("reject_dangling_graph_endpoint", _invalid_graph, {}),
    ("concurrent_same_key_produces_one_start_and_terminal", _concurrent, {}),
    ("refuse_blind_replay_of_interrupted_started_run", _interrupted, {}),
    ("reject_config_changed_before_completion_append", _completion_mutation("config"), {}),
    ("reject_parent_evidence_changed_before_completion_append", _completion_mutation("evidence"), {}),
    ("record_and_replay_surrogate_recipe_rejection", _unicode_rejection_replay("recipe"), {"malformed": "recipe"}),
    ("record_and_replay_surrogate_config_rejection", _unicode_rejection_replay("config"), {"malformed": "config"}),
)


def run_transformation_checks():
    rows = []
    for check_id, operation, options in CHECKS:
        row = {"id": check_id, "metric": METRIC, "passed": False}
        try:
            with _fixture(**options) as fixture:
                row["passed"] = bool(operation(fixture))
            if not row["passed"]:
                row["diagnostic"] = "Implementation did not satisfy the declared check"
        except Exception as error:
            row["diagnostic"] = f"{type(error).__name__}: {error}"[:400]
        rows.append(row)
    count = {"passed": sum(row["passed"] for row in rows), "checks": len(CHECKS)}
    return {"version": "graph-transformation-probes-v2", "checks": rows, "counts": {METRIC: count},
            "metrics": {METRIC: count["passed"] / count["checks"]}, "all_passed": all(row["passed"] for row in rows),
            "interpretation": "Actual fixed identity and induced-subgraph operations on isolated synthetic ledgers. Retained artifact bytes are not executed. No split/merge, learned or arbitrary transformations, semantic equivalence, or predictive/business lift measured."}
