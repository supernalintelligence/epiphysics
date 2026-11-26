"""Actual bounded partition/merge checks on isolated synthetic graph ledgers.

This measures fixed record operations, not semantic entity fission, learned
representations, output materialization or predictive/business advantage.
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

from . import assertions, graph_views, manifests, store, transforms
from .store import Ledger, canonical, digest

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE)
    for module in (store, assertions, manifests, transforms, graph_views)
)
METRIC = "split_merge_preservation"


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


def _subgraph(model, ids):
    output = deepcopy(model)
    output["entities"] = [row for row in output["entities"] if row["id"] in ids]
    output["relations"] = [row for row in output["relations"] if row["source"] in ids and row["target"] in ids]
    return output


def _register(fixture, model, *, semantics=None, event_id=None):
    semantics = semantics or {}
    ledger = fixture["ledger"]
    snapshot = semantics.get("snapshot", fixture["snapshot"])
    representation = ledger.representation(snapshot["id"], model,
        observer=semantics.get("observer", "graph-view-probe"), method="synthetic-graph-builder")
    artifacts = {role: event["id"] for role, event in fixture["artifacts"].items()}
    for role in ("ontology", "predictor"):
        if role in semantics:
            artifacts[role] = fixture["alternatives"][role]["id"]
    manifest = manifests.register_manifest(ledger, representation["id"],
        encoding="directed-graph", schema_id="epiphysics.graph.v1", artifacts=artifacts,
        task=semantics.get("task", {"id": "view-probe", "family": "collective", "outcome_type": "binary"}),
        horizon_seconds=semantics.get("horizon_seconds", 600), units=semantics.get("units", {"money": "USD", "mass": "kg"}),
        evidence_ids=sorted(_evidence(model)), construction_cost={"basis": "unknown", "elapsed_seconds": None,
            "model_calls": None, "external_spend": None, "currency": None, "receipt_ids": []}, event_id=event_id)
    return representation, manifest


@contextmanager
def _fixture(*, late=None, malformed=None, conflict=None, mismatch=None, bounds=None):
    clock = ["2026-11-24T10:00:00+00:00"]
    with TemporaryDirectory(prefix="epiphysics-view-check-") as directory:
        ledger = Ledger(directory, clock=lambda: clock[0])
        try:
            edge_keys = (("a", "b", "supplies"), ("a", "b", "owes"), ("b", "a", "reports"),
                         ("b", "c", "funds"), ("c", "b", "reports"), ("c", "c", "observes"),
                         ("c", "d", "supplies"), ("d", "c", "reports"))
            sources = {name: ledger.capture("synthetic:view:" + name, ("Fictional evidence " + name).encode())
                       for name in ("a", "b", "c", "d", "alternative", *("-".join(key) for key in edge_keys))}
            model = {"entities": [{"id": name, "basis": "reported", "evidence_ids": [sources[name]["id"]],
                                   "amount": {"value": index + 1, "unit": "USD"}}
                                  for index, name in enumerate(("a", "b", "c", "d"))],
                     "relations": [{"id": "edge-" + str(index), "source": a, "target": b, "type": kind,
                                    "basis": "reported", "evidence_ids": [sources["-".join((a, b, kind))]["id"]], "weight": 1}
                                   for index, (a, b, kind) in enumerate(edge_keys)],
                     "units": {"money": "USD", "mass": "kg"}, "context": {"label": "Synthetic graph", "unknown": None}}
            artifacts = {role: ledger.capture("synthetic:parent:" + role, ("Inert parent " + role).encode())
                         for role in ("construction", "config", "ontology", "predictor")}
            alternatives = {role: ledger.capture("synthetic:alternative:" + role, ("Different " + role).encode())
                            for role in ("ontology", "predictor")}
            deferred = []
            def capture(name, raw, defer=False):
                event_id = "view-input-" + name
                if defer:
                    deferred.append((name, raw, event_id))
                    return event_id
                return ledger.capture("synthetic:view-input:" + name, raw, event_id=event_id)["id"]
            implementation = capture("implementation", graph_views.IMPLEMENTATION_SOURCE, late == "implementation")
            dependencies = {module.__name__: capture(module.__name__, module.IMPLEMENTATION_SOURCE,
                            late == "dependency" and module is transforms)
                            for module in (store, assertions, manifests, transforms)}
            malformed_json = br'{"\ud800":1,"\ud800":2}'
            config_data = {"partition": {"views": {"right": ["d", "c"], "left": ["b", "a"]}},
                           "merge": {"conflicts": "reject"},
                           "missing": {"views": {"left": ["a", "b"], "right": ["c"]}},
                           "overlap": {"views": {"left": ["a", "b"], "right": ["b", "c", "d"]}},
                           "empty": {"views": {"left": ["a", "b", "c", "d"], "right": []}},
                           "unknown": {"views": {"left": ["a", "b"], "right": ["c", "d", "unknown"]}}}
            if bounds == "view_name":
                # 129 UTF-8 bytes despite only 43 characters; independent of implementation constants.
                config_data["partition"] = {"views": {"界" * 43: ["a", "b", "c", "d"]}}
            configs = {name: capture(name + "-config", malformed_json if malformed == "config" and name == "partition"
                                    else canonical(value).encode(), late == "config" and name == "partition")
                       for name, value in config_data.items()}
            recipes = {}
            for name in (*configs, "declared"):
                recipe = {"schema_version": 1, "operation": "merge_graphs" if name == "merge" else "partition_entities",
                          "config_observation_id": configs["partition" if name == "declared" else name],
                          "implementation_observation_id": implementation, "implementation_sha256": digest(graph_views.IMPLEMENTATION_SOURCE),
                          "dependency_observations": dependencies, "output_schema": "epiphysics.graph.v1"}
                if name == "declared":
                    recipe["outputs"] = {}
                recipes[name] = capture(name + "-recipe", malformed_json if malformed == "recipe" and name == "partition"
                                        else canonical(recipe).encode(), late == "recipe" and name == "partition")
            snapshot = ledger.snapshot()
            clock[0] = "2026-11-24T10:01:00+00:00"
            for name, raw, event_id in deferred:
                ledger.capture("synthetic:view-input:" + name, raw, published_at="2020-01-01T00:00:00+00:00", event_id=event_id)
            fixture = {"ledger": ledger, "clock": clock, "model": model, "sources": sources, "artifacts": artifacts,
                       "alternatives": alternatives, "implementation": implementation, "dependencies": dependencies,
                       "configs": configs, "recipes": recipes, "snapshot": snapshot}
            fixture["representation"], fixture["manifest"] = _register(fixture, model,
                event_id="界" * 171 if bounds == "parent_id" else None)  # 513 UTF-8 bytes
            left, right = _subgraph(model, {"a", "b", "c"}), _subgraph(model, {"b", "c", "d"})
            if conflict == "entity":
                right["entities"][0]["amount"]["value"] = 99
            elif conflict == "relation":
                right["relations"][0]["weight"] = 99
            elif conflict == "evidence":
                right["entities"][0]["evidence_ids"] = [sources["alternative"]["id"]]
            elif conflict == "relation_id":
                right["relations"][-1]["id"] = model["relations"][0]["id"]
            elif conflict == "metadata":
                right["context"]["label"] = "Different root metadata"
            semantics = {}
            if mismatch == "snapshot":
                semantics["snapshot"] = ledger.snapshot()
            elif mismatch == "observer":
                semantics["observer"] = "another-observer"
            elif mismatch == "task":
                semantics["task"] = {"id": "another-task", "family": "collective", "outcome_type": "binary"}
            elif mismatch == "horizon":
                semantics["horizon_seconds"] = 601
            elif mismatch == "units":
                semantics["units"] = {"money": "EUR", "mass": "kg"}
            elif mismatch in ("ontology", "predictor"):
                semantics[mismatch] = True
            fixture["left_model"], fixture["right_model"] = left, right
            fixture["left_representation"], fixture["left_manifest"] = _register(fixture, left)
            fixture["right_representation"], fixture["right_manifest"] = _register(fixture, right, semantics=semantics)
            yield fixture
        finally:
            ledger.close()


def _parents(fixture, recipe):
    return [fixture[name]["id"] for name in ("left_manifest", "right_manifest")] if recipe == "merge" else [fixture["manifest"]["id"]]


def _run(fixture, recipe="partition", key="probe", parents=None):
    return graph_views.execute_graph_views(fixture["ledger"], _parents(fixture, recipe) if parents is None else parents,
                                          fixture["recipes"][recipe], run_key=key)


def _completed(fixture, recipe="partition", key="probe"):
    result = _run(fixture, recipe, key)
    if result["kind"] != "graph_views_completed":
        raise ValueError("Expected completed graph views: " + str(result["body"].get("error")))
    return result


def _partition_expected(fixture):
    return {name: _subgraph(fixture["model"], ids) for name, ids in (("left", {"a", "b"}), ("right", {"c", "d"}))}


def _output_rows(models):
    return {name: {"model": model, "model_hash": digest(canonical(model).encode())} for name, model in models.items()}


def _partition(fixture):
    return _completed(fixture)["body"]["outputs"] == _output_rows(_partition_expected(fixture))


def _merge_expected(fixture):
    expected = deepcopy(fixture["model"])
    expected["entities"].sort(key=lambda row: row["id"])
    expected["relations"].sort(key=lambda row: (row["source"], row["target"], row["type"]))
    return expected


def _merge(fixture):
    body = _completed(fixture, "merge")["body"]
    return body["outputs"] == _output_rows({"merged": _merge_expected(fixture)}) and body["losses"] == {
        "removed_entities": [], "removed_relations": [], "removed_evidence_ids": []}


def _losses(fixture):
    expected = _partition_expected(fixture)
    removed = fixture["model"]["relations"][3:5]
    body = _completed(fixture)["body"]
    return (body["losses"]["removed_entities"] == []
            and body["losses"]["removed_relations"] == [{"parent_manifest_id": fixture["manifest"]["id"], "record": row} for row in removed]
            and body["losses"]["removed_evidence_ids"] == sorted(_evidence(fixture["model"]) - set().union(*(_evidence(x) for x in expected.values()))))


def _edge_key(row):
    return {key: row[key] for key in ("source", "target", "type")}


def _mapping(fixture, merge=False):
    recipe = "merge" if merge else "partition"
    body = _completed(fixture, recipe)["body"]
    models = {fixture["left_manifest"]["id"]: fixture["left_model"], fixture["right_manifest"]["id"]: fixture["right_model"]} if merge else {fixture["manifest"]["id"]: fixture["model"]}
    expected = []
    for parent, model in sorted(models.items()):
        def view(eid):
            return "merged" if merge else "left" if eid in ("a", "b") else "right"
        expected.append({"parent_manifest_id": parent,
            "entities": [{"source_id": row["id"], "output": {"view": view(row["id"]), "id": row["id"]}} for row in model["entities"]],
            "relations": [{"source_key": _edge_key(row), "output": {"view": view(row["source"]), "key": _edge_key(row)}
                           if view(row["source"]) == view(row["target"]) else None} for row in model["relations"]],
            "metadata": {"fields": sorted(set(model) - {"entities", "relations"}), "output_views": ["merged"] if merge else ["left", "right"]}})
    # Ancestry record ordering is presentation; require all exact records once.
    actual = deepcopy(body["source_to_output"])
    for rows in (actual, expected):
        rows.sort(key=lambda row: row["parent_manifest_id"])
        for row in rows:
            row["entities"].sort(key=canonical)
            row["relations"].sort(key=canonical)
    return actual == expected


def _deduplication(fixture):
    body = _completed(fixture, "merge")["body"]
    parents = sorted(_parents(fixture, "merge"))
    expected = {"entities": [{"output_id": eid, "parent_manifest_ids": parents} for eid in ("b", "c")],
                "relations": [{"output_key": _edge_key(row), "parent_manifest_ids": parents} for row in fixture["model"]["relations"][3:6]]}
    return {key: sorted(rows, key=canonical) for key, rows in body["deduplications"].items()} == {
            key: sorted(rows, key=canonical) for key, rows in expected.items()}


def _order(fixture):
    first = _completed(fixture, "merge")
    parents = list(reversed(_parents(fixture, "merge")))
    count = len(fixture["ledger"].events())
    replay = _run(fixture, "merge", parents=parents)
    if replay != first or len(fixture["ledger"].events()) != count:
        return False
    second = _run(fixture, "merge", "another-order", parents)
    return second["body"]["outputs"] == first["body"]["outputs"] and second["body"]["source_to_output"] == first["body"]["source_to_output"]


def _immutable(fixture):
    ledger = fixture["ledger"]
    events = ledger.events()
    blobs = {row["body"]["content_hash"]: (ledger.root / "blobs" / row["body"]["content_hash"]).read_bytes() for row in ledger.events("observation")}
    _completed(fixture)
    _completed(fixture, "merge", "merge")
    return all(ledger.get(row["id"]) == row for row in events) and all((ledger.root / "blobs" / sha).read_bytes() == raw for sha, raw in blobs.items())


def _receipts(fixture):
    event = _completed(fixture, "merge")
    body, ledger = event["body"], fixture["ledger"]
    starts = ledger.events("graph_views_started")
    parents = {row["manifest"]["id"]: row for row in body["request"]["parents"]}
    return (len(starts) == 1 and starts[0]["body"]["request"] == body["request"] and starts[0]["seq"] < event["seq"]
            and set(parents) == set(_parents(fixture, "merge"))
            and all(parents[fixture[key + "_manifest"]["id"]]["manifest"]["hash"] == fixture[key + "_manifest"]["hash"]
                    and parents[fixture[key + "_manifest"]["id"]]["representation"]["model_hash"] == fixture[key + "_manifest"]["body"]["model_hash"]
                    and parents[fixture[key + "_manifest"]["id"]]["snapshot"]["hash"] == fixture["snapshot"]["hash"] for key in ("left", "right"))
            and body["request"]["recipe"]["observation_id"] == fixture["recipes"]["merge"]
            and body["request"]["implementation"]["source_sha256"] == digest(graph_views.IMPLEMENTATION_SOURCE)
            and body["recipe_descriptor"]["operation"] == "merge_graphs"
            and body["resources"] == {"model_calls": 0, "external_spend": 0})


def _rejected(fixture, recipe="partition", key="probe"):
    ledger = fixture["ledger"]
    before = len(ledger.events())
    original = [ledger.get(parent) for parent in _parents(fixture, recipe)]
    event = _run(fixture, recipe, key)
    return (event["kind"] == "graph_views_rejected" and event["body"]["result"] == "rejected"
            and [row["kind"] for row in ledger.events()[before:]] == ["graph_views_started", "graph_views_rejected"]
            and all(ledger.get(row["id"]) == row for row in original))


def _replay(fixture, rejected=False):
    recipe = "missing" if rejected else "merge"
    if rejected and not _rejected(fixture, recipe):
        return False
    event = fixture["ledger"].events("graph_views_rejected")[0] if rejected else _completed(fixture, recipe)
    ledger = fixture["ledger"]
    count = len(ledger.events())
    observation = ledger.get(fixture["implementation"])
    (ledger.root / "blobs" / observation["body"]["content_hash"]).unlink()
    return _run(fixture, recipe) == event and len(ledger.events()) == count


def _view_name_bound(fixture):
    # Observe calls without replacing the fixed function or disabling its guards.
    original_profile = sys.getprofile()
    compute_code = graph_views._compute_graph_views.__code__
    calls = []
    def profile(frame, event, argument):
        if event == "call" and frame.f_code is compute_code:
            calls.append(True)
        if original_profile is not None:
            original_profile(frame, event, argument)
    sys.setprofile(profile)
    try:
        return _rejected(fixture) and not calls
    finally:
        sys.setprofile(original_profile)


def _parent_id_bound(fixture):
    # A real, otherwise valid 513-byte manifest ID prevents a missing-ID lookup
    # from masquerading as resource validation. Keep a positive execution control.
    _completed(fixture, "merge", "bound-positive-control")
    ledger = fixture["ledger"]
    original, count = ledger.get(fixture["manifest"]["id"]), len(ledger.events())
    original_get, lookups = ledger.get, []
    def tracking_get(*args, **kwargs):
        lookups.append(args)
        return original_get(*args, **kwargs)
    ledger.get = tracking_get
    try:
        try:
            _run(fixture)
        except ValueError:
            return not lookups and len(ledger.events()) == count and original_get(original["id"]) == original
        return False
    finally:
        ledger.get = original_get


def _changed_request(fixture):
    _completed(fixture)
    count = len(fixture["ledger"].events())
    try:
        _run(fixture, "missing")
    except ValueError:
        return len(fixture["ledger"].events()) == count
    return False


def _tampered(which, *, boundary=False):
    def check(fixture):
        ledger = fixture["ledger"]
        observation_id = {"implementation": fixture["implementation"], "config": fixture["configs"]["partition"],
                          "parent": fixture["sources"]["a"]["id"], "dependency": fixture["dependencies"]["epiphysics.transforms"]}[which]
        path = ledger.root / "blobs" / ledger.get(observation_id)["body"]["content_hash"]
        original_append, changed = ledger.append, False
        def changing_append(kind, *args, **kwargs):
            nonlocal changed
            if kind == "graph_views_completed":
                path.write_bytes(b"Changed immediately before completion validation")
                changed = True
            return original_append(kind, *args, **kwargs)
        if boundary:
            ledger.append = changing_append
        else:
            path.write_bytes(b"Changed retained bytes")
        try:
            return _rejected(fixture) and (not boundary or changed) and ledger.events("graph_views_completed") == []
        finally:
            ledger.append = original_append
    return check


def _unicode_replay(fixture):
    if not _rejected(fixture):
        return False
    ledger = fixture["ledger"]
    terminal = ledger.events("graph_views_rejected")[0]
    canonical(terminal).encode("utf-8")
    if len(terminal["body"]["error"]["message"]) > 400 or not ledger.verify()["valid"]:
        return False
    observation = ledger.get(fixture["implementation"])
    (ledger.root / "blobs" / observation["body"]["content_hash"]).unlink()
    count = len(ledger.events())
    return _run(fixture) == terminal and len(ledger.events()) == count


def _concurrent(fixture):
    barrier, results = threading.Barrier(2), []
    def worker():
        ledger = Ledger(fixture["ledger"].root, clock=lambda: fixture["clock"][0])
        try:
            barrier.wait(timeout=5)
            results.append(graph_views.execute_graph_views(ledger, _parents(fixture, "merge"), fixture["recipes"]["merge"], run_key="race"))
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
    completed = fixture["ledger"].events("graph_views_completed")
    return (all(not worker.is_alive() for worker in workers) and len(results) == 2 and len(completed) == 1
            and len(fixture["ledger"].events("graph_views_started")) == 1 and not fixture["ledger"].events("graph_views_rejected")
            and any(result == completed[0] for result in results) and all(result is None or result == completed[0] for result in results))


def _interrupted(fixture):
    class SimulatedInterruption(BaseException):
        pass
    ledger, original_append = fixture["ledger"], fixture["ledger"].append
    def interrupted_append(kind, *args, **kwargs):
        if kind == "graph_views_completed":
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
        return len(ledger.events()) == count and len(ledger.events("graph_views_started")) == 1 and not ledger.events("graph_views_completed") and not ledger.events("graph_views_rejected")
    return False


CHECKS = (
    ("execute_exhaustive_partition_with_directed_parallel_edges_and_self_loops", _partition, {}),
    ("account_for_every_cross_partition_edge_and_removed_evidence", _losses, {}),
    ("map_every_partition_source_record_and_metadata", _mapping, {}),
    ("execute_strict_merge_preserving_units_attributes_and_provenance", _merge, {}),
    ("map_every_record_from_every_merge_parent", lambda fixture: _mapping(fixture, True), {}),
    ("record_identical_entity_and_relation_deduplication", _deduplication, {}),
    ("normalize_parent_order_for_deterministic_outputs_and_replay", _order, {}),
    ("preserve_all_parent_events_and_retained_artifacts", _immutable, {}),
    ("bind_receipts_to_all_parents_snapshot_and_executing_source", _receipts, {}),
    ("replay_completed_merge_after_blob_loss_without_append", _replay, {}),
    ("replay_rejected_partition_after_blob_loss_without_append", lambda fixture: _replay(fixture, True), {}),
    ("reject_changed_recipe_under_same_run_key", _changed_request, {}),
    *((f"reject_{kind}_partition", lambda fixture, kind=kind: _rejected(fixture, kind), {}) for kind in ("missing", "overlap", "empty", "unknown")),
    *((f"reject_conflicting_merge_{kind}", lambda fixture: _rejected(fixture, "merge"), {"conflict": kind}) for kind in ("entity", "relation", "evidence", "relation_id", "metadata")),
    *((f"reject_mismatched_merge_{kind}", lambda fixture: _rejected(fixture, "merge"), {"mismatch": kind}) for kind in ("snapshot", "observer", "task", "horizon", "units", "ontology", "predictor")),
    ("reject_caller_fabricated_outputs", lambda fixture: _rejected(fixture, "declared"), {}),
    ("reject_oversized_utf8_view_name_before_expansion", _view_name_bound, {"bounds": "view_name"}),
    ("reject_oversized_utf8_parent_id_before_claim", _parent_id_bound, {"bounds": "parent_id"}),
    *((f"reject_late_{kind}_despite_old_publication", _rejected, {"late": kind}) for kind in ("recipe", "config", "implementation", "dependency")),
    *((f"reject_tampered_{kind}_bytes", _tampered(kind), {}) for kind in ("implementation", "config", "parent")),
    *((f"reject_{kind}_changed_before_completion_append", _tampered(kind, boundary=True), {}) for kind in ("config", "parent", "dependency")),
    ("concurrent_merge_key_produces_one_start_and_terminal", _concurrent, {}),
    ("refuse_blind_replay_of_interrupted_started_run", _interrupted, {}),
    *((f"record_and_replay_surrogate_{kind}_rejection", _unicode_replay, {"malformed": kind}) for kind in ("recipe", "config")),
)


def run_graph_view_checks():
    rows = []
    for check_id, operation, options in CHECKS:
        row = {"id": check_id, "metric": METRIC, "passed": False}
        try:
            with _fixture(**options) as fixture:
                row["passed"] = bool(operation(fixture))
            if not row["passed"]:
                row["diagnostic"] = "Implementation did not satisfy the declared check"
        except Exception as error:
            row["diagnostic"] = (f"{type(error).__name__}: {error}").encode("utf-8", errors="backslashreplace").decode("utf-8")[:400]
        rows.append(row)
    count = {"passed": sum(row["passed"] for row in rows), "checks": len(CHECKS)}
    return {"version": "graph-view-probes-v1", "checks": rows, "counts": {METRIC: count},
            "metrics": {METRIC: count["passed"] / count["checks"]}, "all_passed": all(row["passed"] for row in rows),
            "interpretation": "Actual fixed graph partition/merge on isolated synthetic ledgers. Record preservation, explicit losses and rejection rules only; no semantic entity fission, learned representation, output materialization or predictive/business lift measured."}
