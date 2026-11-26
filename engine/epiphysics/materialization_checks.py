"""Exercise graph output materialization and its atomic consumers on synthetic data.

These local conformance checks do not measure retrieval, inference quality,
semantic equivalence, business value or independently witnessed execution.
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

from . import assertions, graph_views, manifests, materialization, store, transforms
from .store import Ledger, canonical, digest

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE)
    for module in (store, assertions, manifests, transforms, graph_views, materialization)
)
METRIC = "output_manifest_materialization"


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


def _parent(ledger, snapshot, model, artifacts, units=None):
    representation = ledger.representation(snapshot["id"], model, observer="materialization-probe", method="synthetic-builder")
    manifest = manifests.register_manifest(ledger, representation["id"], encoding="directed-graph", schema_id="epiphysics.graph.v1",
        artifacts={role: event["id"] for role, event in artifacts.items()},
        task={"id": "materialization-probe", "family": "collective", "outcome_type": "binary"},
        horizon_seconds=600, units=units or {"amount": "USD"}, evidence_ids=sorted(_evidence(model)), construction_cost=None)
    return {"representation": representation, "manifest": manifest, "model": model}


@contextmanager
def _fixture(operation="partition_entities", bounds=None):
    clock = ["2026-11-24T10:00:00+00:00"]
    with TemporaryDirectory(prefix="epiphysics-materialization-check-") as directory:
        ledger = Ledger(directory, clock=lambda: clock[0])
        try:
            keys = (("a", "b", "supplies"), ("a", "b", "owes"), ("b", "c", "funds"), ("c", "c", "observes"))
            sources = {name: ledger.capture("synthetic:materialization:" + name, ("Fictional evidence " + name).encode())
                       for name in ("a", "b", "c", *("-".join(row) for row in keys))}
            model = {"entities": [{"id": name, "basis": "reported", "evidence_ids": [sources[name]["id"]],
                                   "amount": {"value": n + 1, "unit": "USD"}} for n, name in enumerate(("a", "b", "c"))],
                     "relations": [{"source": a, "target": b, "type": kind, "basis": "reported",
                                    "evidence_ids": [sources["-".join((a, b, kind))]["id"]]} for a, b, kind in keys],
                     "context": {"label": "Synthetic graph", "unknown": None}}
            if bounds == "aggregate":
                evidence = [ledger.capture(f"synthetic:budget-source:{i}", f"Fictional budget evidence {i}".encode())["id"] for i in range(500)]
                model = {"entities": [{"id": f"entity-{i}", "basis": "reported", "evidence_ids": [evidence[0]]} for i in range(64)],
                         "relations": [], "context": {"evidence_ids": evidence}}
            artifacts = {role: ledger.capture("synthetic:parent:" + role, ("Inert parent " + role).encode())
                         for role in ("construction", "config", "ontology", "predictor")}
            engine = transforms if operation in ("identity", "project_entities") else graph_views
            modules = (store, assertions, manifests) if engine is transforms else (store, assertions, manifests, transforms)
            implementation = ledger.capture("synthetic:implementation", engine.IMPLEMENTATION_SOURCE)
            dependencies = {module.__name__: ledger.capture("synthetic:dependency:" + module.__name__, module.IMPLEMENTATION_SOURCE)
                            for module in modules}
            configurations = {"identity": {}, "project_entities": {"entity_ids": ["a", "b"]},
                              "partition_entities": {"views": {"left": ["a", "b"], "right": ["c"]}},
                              "merge_graphs": {"conflicts": "reject"}}
            if bounds == "aggregate":
                configurations["partition_entities"] = {"views": {row["id"]: [row["id"]] for row in model["entities"]}}
            config = ledger.capture("synthetic:config", canonical(configurations[operation]).encode())
            recipe = ledger.capture("synthetic:recipe", canonical({"schema_version": 1, "operation": operation,
                "config_observation_id": config["id"], "implementation_observation_id": implementation["id"],
                "implementation_sha256": digest(engine.IMPLEMENTATION_SOURCE),
                "dependency_observations": {name: event["id"] for name, event in dependencies.items()},
                "output_schema": "epiphysics.graph.v1"}).encode())
            snapshot = ledger.snapshot()
            clock[0] = "2026-11-24T10:01:00+00:00"
            parent_models = [_subgraph(model, {"a", "b"}), _subgraph(model, {"b", "c"})] if operation == "merge_graphs" else [model]
            parents = [_parent(ledger, snapshot, row, artifacts, units={"amount": "u" * 17_000} if bounds == "descriptor" else None) for row in parent_models]
            if engine is transforms:
                completion = transforms.execute_graph_transform(ledger, parents[0]["manifest"]["id"], recipe["id"], run_key="source")
            else:
                completion = graph_views.execute_graph_views(ledger, [row["manifest"]["id"] for row in parents], recipe["id"], run_key="source")
            if not completion["kind"].endswith("_completed"):
                raise ValueError("Source operation failed: " + str(completion["body"].get("error")))
            yield {"ledger": ledger, "clock": clock, "model": model, "sources": sources, "artifacts": artifacts,
                   "implementation": implementation, "dependencies": dependencies, "config": config, "recipe": recipe,
                   "snapshot": snapshot, "parents": parents, "completion": completion, "operation": operation, "bounds": bounds}
        finally:
            ledger.close()


def _expected(fixture):
    operation, model = fixture["operation"], fixture["model"]
    if operation == "identity":
        return {"output": model}
    if operation == "project_entities":
        return {"output": _subgraph(model, {"a", "b"})}
    if operation == "partition_entities":
        return {"left": _subgraph(model, {"a", "b"}), "right": _subgraph(model, {"c"})}
    model = deepcopy(model)
    model["relations"].sort(key=lambda row: (row["source"], row["target"], row["type"]))
    return {"merged": model}


def _run(fixture, key="probe", completion_id=None):
    return materialization.materialize_graph_outputs(fixture["ledger"], completion_id or fixture["completion"]["id"], run_key=key)


def _completed(fixture, key="probe"):
    result = _run(fixture, key)
    if result["kind"] != "graph_materialization_completed":
        raise ValueError("Expected completed materialization: " + str(result["body"].get("error")))
    return result


def _bundle(fixture, key="probe"):
    return materialization.get_materialized_outputs(fixture["ledger"], _completed(fixture, key)["id"])


def _outputs(fixture):
    bundle, expected = _bundle(fixture), _expected(fixture)
    receipt = bundle["receipt"]["body"]
    return (set(bundle["representations"]) == set(bundle["manifests"]) == set(receipt["outputs"]) == set(expected)
            and all(bundle["representations"][name]["body"]["model"] == model
                    and bundle["manifests"][name]["body"]["model_hash"] == digest(canonical(model).encode())
                    and receipt["outputs"][name]["model_hash"] == digest(canonical(model).encode()) for name, model in expected.items()))


def _bindings(fixture):
    bundle = _bundle(fixture)
    receipt, snapshot = bundle["receipt"]["body"], fixture["snapshot"]
    parent = fixture["parents"][0]["manifest"]["body"]
    for name, manifest in bundle["manifests"].items():
        representation, body = bundle["representations"][name], manifest["body"]
        output = receipt["outputs"][name]
        if not (body["representation_id"] == representation["id"] == output["representation_id"]
                and body["representation_hash"] == representation["hash"] == output["representation_hash"]
                and manifest["id"] == output["manifest_id"] and manifest["hash"] == output["manifest_hash"]
                and body["snapshot_id"] == snapshot["id"] and body["snapshot_hash"] == snapshot["hash"]
                and body["cutoff"] == snapshot["body"]["cutoff"] and body["observer"] == parent["observer"]
                and all(body["descriptor"][key] == parent["descriptor"][key] for key in ("encoding", "schema_id", "task", "horizon_seconds", "units"))
                and body["artifacts"]["construction"]["observation_id"] == fixture["implementation"]["id"]
                and body["artifacts"]["config"]["observation_id"] == fixture["config"]["id"]
                and all(body["artifacts"][key]["content_hash"] == parent["artifacts"][key]["content_hash"] for key in ("ontology", "predictor"))
                and {row["observation_id"] for row in body["evidence"]} == _evidence(representation["body"]["model"])
                and body["construction_cost"]["basis"] == "unknown" and body["construction_cost"]["external_spend"] is None):
            return False
    return True


def _ancestry(fixture):
    bundle = _bundle(fixture)
    body = bundle["receipt"]["body"]
    expected = []
    for parent in fixture["parents"]:
        manifest, representation = parent["manifest"], parent["representation"]
        expected.append({"manifest_id": manifest["id"], "manifest_hash": manifest["hash"],
            "representation_id": representation["id"], "representation_hash": representation["hash"],
            "method_id": manifest["body"]["method_id"], "snapshot_id": fixture["snapshot"]["id"], "snapshot_hash": fixture["snapshot"]["hash"]})
    parent_id = fixture["parents"][0]["representation"]["id"] if len(expected) == 1 else None
    return (sorted(body["parents"], key=canonical) == sorted(expected, key=canonical)
            and all(row["body"]["parent"] == parent_id for row in bundle["representations"].values()))


def _links(fixture):
    body = _completed(fixture)["body"]
    source = fixture["completion"]
    names = {"losses", "source_to_output"} | ({"deduplications"} if fixture["operation"] in ("partition_entities", "merge_graphs") else set())
    return (set(body["links"]) == names and all(body["links"][name] == {"completion_id": source["id"], "field": name,
             "sha256": digest(canonical(source["body"][name]).encode())} for name in names))


def _derivation(fixture):
    bundle = _bundle(fixture)
    body = bundle["receipt"]["body"]
    parent_methods = sorted(parent["manifest"]["body"]["method_id"] for parent in fixture["parents"])
    for name, representation in bundle["representations"].items():
        descriptor = {"schema_version": 1, "recipe_id": fixture["completion"]["body"]["recipe_id"],
                      "parent_method_ids": parent_methods, "output_view": name}
        method = "graph-derived-v1:" + digest(canonical(descriptor).encode())
        if not (body["derivations"][name] == descriptor and representation["body"]["method"] == method
                and body["outputs"][name]["derivation_method"] == method
                and body["outputs"][name]["method_id"] == bundle["manifests"][name]["body"]["method_id"]):
            return False
    return True


def _stable_identity(fixture):
    first = _bundle(fixture)
    with _fixture(fixture["operation"]) as other:
        second = _bundle(other)
        return (fixture["snapshot"]["id"] != other["snapshot"]["id"]
                and {name: row["body"]["method_id"] for name, row in first["manifests"].items()} ==
                    {name: row["body"]["method_id"] for name, row in second["manifests"].items()}
                and len({row["body"]["method_id"] for row in first["manifests"].values()}) == len(first["manifests"]))


def _forecast(fixture):
    bundle = _bundle(fixture)
    ledger = fixture["ledger"]
    question = ledger.question("Will the fictional task finish?", "2026-11-24T10:05:00+00:00", "2026-11-24T10:10:00+00:00",
                               "Synthetic completion reports done", "collective")
    for name, manifest in bundle["manifests"].items():
        forecast = manifests.forecast_manifest(ledger, manifest["id"], question["id"], 0.6)
        if not (forecast["body"]["representation_id"] == bundle["representations"][name]["id"]
                and forecast["body"]["snapshot_id"] == fixture["snapshot"]["id"]
                and forecast["body"]["method"] == manifest["body"]["method_id"]):
            return False
    return len(ledger.events("forecast")) == len(bundle["manifests"])


def _immutable(fixture):
    ledger = fixture["ledger"]
    original = ledger.events()
    _completed(fixture)
    return all(ledger.get(row["id"]) == row for row in original) and ledger.verify()["valid"]


def _replay(fixture):
    terminal = _completed(fixture)
    ledger = fixture["ledger"]
    count = len(ledger.events())
    blob = ledger.root / "blobs" / fixture["implementation"]["body"]["content_hash"]
    blob.unlink()
    return _run(fixture) == terminal and len(ledger.events()) == count


def _lookup_blob_loss(fixture):
    terminal = _completed(fixture)
    ledger = fixture["ledger"]
    blob = ledger.root / "blobs" / fixture["implementation"]["body"]["content_hash"]
    blob.unlink()
    metadata = materialization.get_materialized_outputs(ledger, terminal["id"], verify_bytes=False)
    if metadata["receipt"] != terminal:
        return False
    try:
        materialization.get_materialized_outputs(ledger, terminal["id"])
    except ValueError:
        return True
    return False


def _rejected(fixture, completion_id=None, key="probe"):
    ledger = fixture["ledger"]
    before = len(ledger.events())
    terminal = _run(fixture, key, completion_id)
    return (terminal["kind"] == "graph_materialization_rejected"
            and [row["kind"] for row in ledger.events()[before:]] == ["graph_materialization_started", "graph_materialization_rejected"])


def _tampered(which):
    def check(fixture):
        row = fixture["config"] if which == "config" else fixture["sources"]["a"]
        (fixture["ledger"].root / "blobs" / row["body"]["content_hash"]).write_bytes(b"Changed input before materialization")
        return _rejected(fixture)
    return check


def _synthetic_execution(fixture, body, key):
    source, ledger = fixture["completion"], fixture["ledger"]
    body["run_key"] = key
    prefix, kind = ("graph-transform", "graph_transform_started") if source["kind"] == "graph_transform_completed" else ("graph-views", "graph_views_started")
    ledger.append(kind, {"schema_version": 1, "run_key": key, "request": body["request"]}, f"{prefix}:{key}:started")
    return ledger.append(source["kind"], body, f"{prefix}:{key}:terminal")


def _forged_completion(fixture):
    # Match the run/start/terminal identity and rehash the changed model so the
    # fixed recomputation comparison is the guard actually being exercised.
    body = deepcopy(fixture["completion"]["body"])
    if fixture["completion"]["kind"] == "graph_transform_completed":
        body["output_model"]["entities"][0]["amount"]["value"] = 999
        body["output_model_hash"] = digest(canonical(body["output_model"]).encode())
    else:
        output = body["outputs"]["left"]
        output["model"]["entities"][0]["amount"]["value"] = 999
        output["model_hash"] = digest(canonical(output["model"]).encode())
    event = _synthetic_execution(fixture, body, "forged-output")
    if not _rejected(fixture, event["id"]):
        return False
    terminal = fixture["ledger"].events("graph_materialization_rejected")[-1]
    return "fixed recomputation" in terminal["body"]["error"]["message"]


def _malformed_containers(fixture):
    ledger, pairs = fixture["ledger"], []
    for index, body in enumerate(([], None, "not an object")):
        execution = ledger.append("graph_transform_completed", body, f"graph-transform:malformed-{index}:terminal")
        key = f"malformed-{index}"
        if not _rejected(fixture, execution["id"], key):
            return False
        receipt = ledger.events("graph_materialization_rejected")[-1]
        if receipt["body"]["error"]["type"] != "ValueError" or "body must be an object" not in receipt["body"]["error"]["message"]:
            return False
        pairs.append((execution, receipt, key))
    parent_body = deepcopy(fixture["parents"][0]["manifest"]["body"])
    parent_body["artifacts"] = []
    parent = ledger.append("representation_manifest", parent_body, "malformed-parent")
    body = deepcopy(fixture["completion"]["body"])
    body["request"]["parent_manifest"] = {"id": parent["id"], "hash": parent["hash"]}
    execution = _synthetic_execution(fixture, body, "malformed-artifacts")
    if not _rejected(fixture, execution["id"], "malformed-artifacts"):
        return False
    receipt = ledger.events("graph_materialization_rejected")[-1]
    if "parent manifest artifact roles" not in receipt["body"]["error"]["message"] or not ledger.verify()["valid"]:
        return False
    pairs.append((execution, receipt, "malformed-artifacts"))
    blob = ledger.root / "blobs" / fixture["implementation"]["body"]["content_hash"]
    blob.unlink()
    count = len(ledger.events())
    return all(_run(fixture, key, execution["id"]) == receipt for execution, receipt, key in pairs) and len(ledger.events()) == count


def _incompatible_execution(fixture):
    # Synthetic old-contract control: coherent start/terminal metadata, but a
    # dependency identity differs from the fixed implementation now executing.
    ledger, source = fixture["ledger"], fixture["completion"]
    body = deepcopy(source["body"])
    body["run_key"] = "old-contract"
    body["request"]["implementation"]["dependencies"]["epiphysics.store"] = "0" * 64
    prefix, kind = ("graph-transform", "graph_transform_started") if source["kind"] == "graph_transform_completed" else ("graph-views", "graph_views_started")
    ledger.append(kind, {"schema_version": 1, "run_key": "old-contract", "request": body["request"]}, f"{prefix}:old-contract:started")
    old = ledger.append(source["kind"], body, f"{prefix}:old-contract:terminal")
    return _rejected(fixture, old["id"])


def _noncompletion(fixture):
    _completed(fixture, "positive-control")
    count = len(fixture["ledger"].events())
    try:
        _run(fixture, completion_id=fixture["parents"][0]["representation"]["id"])
    except ValueError:
        return len(fixture["ledger"].events()) == count
    return False


def _rejected_replay(fixture):
    if not _tampered("config")(fixture):
        return False
    ledger = fixture["ledger"]
    terminal = ledger.events("graph_materialization_rejected")[0]
    count = len(ledger.events())
    return _run(fixture) == terminal and len(ledger.events()) == count


def _changed_request(fixture):
    _completed(fixture)
    other = deepcopy(fixture["completion"]["body"])
    event = fixture["ledger"].append(fixture["completion"]["kind"], other)
    before = len(fixture["ledger"].events())
    try:
        _run(fixture, completion_id=event["id"])
    except ValueError:
        return len(fixture["ledger"].events()) == before
    return False


def _atomic_failure(fixture, *, interruption=False):
    class SimulatedInterruption(BaseException):
        pass
    ledger = fixture["ledger"]
    observer = Ledger(ledger.root, clock=lambda: fixture["clock"][0])
    before = {event["id"] for event in ledger.events()}
    original_append, observations = ledger.append, []
    counter = 0
    def fail_append(kind, *args, **kwargs):
        nonlocal counter
        result = original_append(kind, *args, **kwargs)
        if kind == "representation_manifest":
            counter += 1
            observations.append([event["id"] for event in observer.events() if event["id"] not in before and event["kind"] in ("representation", "representation_manifest")])
            if counter == 1:
                raise SimulatedInterruption() if interruption else ValueError("Synthetic failure after first staged output")
        return result
    ledger.append = fail_append
    try:
        try:
            terminal = _run(fixture)
        except SimulatedInterruption:
            terminal = None
        new = [event for event in ledger.events() if event["id"] not in before]
        expected = ["graph_materialization_started"] if interruption else ["graph_materialization_started", "graph_materialization_rejected"]
        if counter != 1 or observations != [[]] or [event["kind"] for event in new] != expected:
            return False
        if interruption:
            count = len(ledger.events())
            try:
                _run(fixture)
            except ValueError:
                return len(ledger.events()) == count
            return False
        return terminal["kind"] == "graph_materialization_rejected" and not ledger.db.in_transaction
    finally:
        ledger.append = original_append
        observer.close()


def _atomic_visibility(fixture):
    ledger = fixture["ledger"]
    observer = Ledger(ledger.root, clock=lambda: fixture["clock"][0])
    before = {event["id"] for event in observer.events()}
    original_append, observed = ledger.append, []
    def watching_append(kind, *args, **kwargs):
        result = original_append(kind, *args, **kwargs)
        if kind in ("representation", "representation_manifest", "graph_materialization_completed"):
            observed.append([event["id"] for event in observer.events() if event["id"] not in before and event["kind"] != "graph_materialization_started"])
        return result
    ledger.append = watching_append
    try:
        terminal = _completed(fixture)
        after = [event for event in observer.events() if event["id"] not in before and event["kind"] != "graph_materialization_started"]
        return len(observed) == 2 * len(_expected(fixture)) + 1 and all(not row for row in observed) and len(after) == len(observed) and after[-1] == terminal
    finally:
        ledger.append = original_append
        observer.close()


def _boundary_mutation(fixture):
    ledger = fixture["ledger"]
    original_append = ledger.append
    path = ledger.root / "blobs" / fixture["config"]["body"]["content_hash"]
    changed = False
    def changing_append(kind, *args, **kwargs):
        nonlocal changed
        if kind == "graph_materialization_completed":
            path.write_bytes(b"Changed before terminal validation")
            changed = True
        return original_append(kind, *args, **kwargs)
    ledger.append = changing_append
    try:
        return _rejected(fixture) and changed
    finally:
        ledger.append = original_append


def _grouped_time_boundary(fixture):
    _completed(fixture, "time-positive-control")
    ledger, clock = fixture["ledger"], fixture["clock"]
    question = ledger.question("Fictional grouped forecast?", "2026-11-24T10:05:00+00:00", "2026-11-24T10:10:00+00:00",
                               "Synthetic outcome", "collective")
    class RestrictionMissing(BaseException):
        pass
    operations = (
        lambda: ledger.capture("synthetic:late-group-evidence", b"Evidence learned after the frozen group time"),
        lambda: ledger.question("New grouped question?", "2026-11-24T10:08:00+00:00", "2026-11-24T10:10:00+00:00", "Synthetic outcome", "collective"),
        lambda: ledger.forecast(question["id"], fixture["snapshot"]["id"], "grouped-probe", 0.5,
                                model={"identifier": "synthetic-supplied-probability", "prompt": "No model was called"}),
        *(lambda kind=kind: ledger.append(kind, {}) for kind in ("observation", "question", "forecast")),
    )
    for operation in operations:
        events = ledger.events()
        blobs = {path.name for path in (ledger.root / "blobs").iterdir()}
        refused = poisoned = False
        try:
            with ledger.atomic_write():
                clock[0] = "2026-11-24T10:06:00+00:00"
                try:
                    operation()
                except ValueError:
                    refused = True
                if not refused:
                    raise RestrictionMissing()
        except RestrictionMissing:
            return False
        except ValueError:
            poisoned = True
        finally:
            clock[0] = "2026-11-24T10:01:00+00:00"
        if not (refused and poisoned and ledger.events() == events and {path.name for path in (ledger.root / "blobs").iterdir()} == blobs):
            return False
    with ledger.atomic_write() as timestamp:
        clock[0] = "2026-11-24T10:02:00+00:00"
        snapshot = ledger.snapshot()
        parent = _parent(ledger, snapshot, fixture["model"], fixture["artifacts"])
        if snapshot["body"]["cutoff"] != timestamp or snapshot["recorded_at"] != timestamp:
            return False
    checked = manifests._checked_manifest(ledger, parent["manifest"]["id"], store.instant(clock[0]))
    if checked["body"]["snapshot_id"] != snapshot["id"]:
        return False
    questions = [ledger.question("Post-group forecast?", "2026-11-24T10:05:00+00:00", "2026-11-24T10:11:00+00:00",
                                 "Synthetic outcome", "collective") for _ in range(2)]
    forecast = manifests.forecast_manifest(ledger, checked["id"], questions[0]["id"], 0.5)
    if forecast["recorded_at"] != clock[0] or forecast["body"]["snapshot_id"] != snapshot["id"]:
        return False
    clock[0] = "2026-11-24T10:06:00+00:00"
    count = len(ledger.events())
    try:
        manifests.forecast_manifest(ledger, checked["id"], questions[1]["id"], 0.5)
    except ValueError as error:
        return "deadline" in str(error) and len(ledger.events()) == count and ledger.verify()["valid"]
    return False


def _resource_bound(fixture):
    # Fixed independent workloads: a >16 KiB parent descriptor, or 64 small
    # output graphs repeating 500 evidence references (graphs remain <2 MB).
    if fixture["bounds"] == "descriptor":
        if len(canonical(fixture["parents"][0]["manifest"]["body"]["descriptor"]).encode()) <= 16_384:
            return False
    elif (len(fixture["completion"]["body"]["outputs"]) != 64
          or sum(len(canonical(output["model"]).encode()) for output in fixture["completion"]["body"]["outputs"].values()) >= 2_000_000):
        return False
    class OutputWriteReached(BaseException):
        pass
    ledger = fixture["ledger"]
    original = ledger.representation
    attempted = []
    def stop_before_output(*args, **kwargs):
        attempted.append(True)
        # A broken cap must fail this probe without performing the amplified write.
        raise OutputWriteReached()
    ledger.representation = stop_before_output
    try:
        try:
            rejected = _rejected(fixture)
        except OutputWriteReached:
            return False
        terminal = ledger.events("graph_materialization_rejected")[-1] if rejected else None
        label = "Parent method descriptor exceeds" if fixture["bounds"] == "descriptor" else "Materialized output records exceeds"
        return rejected and not attempted and label in terminal["body"]["error"]["message"]
    finally:
        ledger.representation = original


def _concurrent(fixture):
    barrier, results = threading.Barrier(2), []
    def worker():
        ledger = Ledger(fixture["ledger"].root, clock=lambda: fixture["clock"][0])
        try:
            barrier.wait(timeout=5)
            results.append(materialization.materialize_graph_outputs(ledger, fixture["completion"]["id"], run_key="race"))
        except ValueError:
            results.append(None)
        except Exception as error:
            results.append({"error": str(error)})
        finally:
            ledger.close()
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=12)
    terminals = fixture["ledger"].events("graph_materialization_completed")
    return (all(not thread.is_alive() for thread in threads) and len(results) == 2 and len(terminals) == 1
            and len(fixture["ledger"].events("graph_materialization_started")) == 1
            and not fixture["ledger"].events("graph_materialization_rejected")
            and any(result == terminals[0] for result in results) and all(result is None or result == terminals[0] for result in results))


CHECKS = (
    *((f"materialize_{operation}_into_exact_output_manifests", _outputs, {"operation": operation})
      for operation in ("identity", "project_entities", "partition_entities", "merge_graphs")),
    ("bind_all_output_manifests_to_snapshot_artifacts_and_semantics", _bindings, {}),
    ("retain_single_parent_representation_ancestry", _ancestry, {}),
    ("retain_every_merge_parent_without_false_singular_parent", _ancestry, {"operation": "merge_graphs"}),
    ("link_retained_losses_mappings_and_deduplications", _links, {}),
    ("derive_methods_from_recipe_parent_methods_and_output_view", _derivation, {"operation": "merge_graphs"}),
    ("stable_methods_across_snapshot_instances_and_distinct_views", _stable_identity, {}),
    ("use_materialized_manifests_with_existing_forecast_consumer", _forecast, {}),
    ("preserve_source_events_and_original_evidence", _immutable, {}),
    ("replay_completed_bundle_after_blob_loss_without_appending", _replay, {}),
    ("separate_metadata_lookup_from_current_byte_integrity", _lookup_blob_loss, {}),
    ("replay_rejected_run_without_partial_outputs", _rejected_replay, {}),
    ("refuse_changed_completion_under_same_run_key", _changed_request, {}),
    *((f"reject_tampered_{kind}_before_materialization", _tampered(kind), {}) for kind in ("config", "parent")),
    ("reject_forged_source_completion_output", _forged_completion, {}),
    ("reject_incompatible_execution_dependency_contract", _incompatible_execution, {}),
    ("record_and_replay_malformed_container_rejections_without_outputs", _malformed_containers, {"operation": "identity"}),
    ("refuse_noncompletion_input_before_claim", _noncompletion, {}),
    ("rollback_every_output_after_first_manifest_failure", _atomic_failure, {}),
    ("hide_partial_outputs_from_second_connection_until_commit", _atomic_visibility, {}),
    ("rollback_interrupted_group_and_refuse_blind_replay", lambda fixture: _atomic_failure(fixture, interruption=True), {}),
    ("reject_changed_input_at_completion_and_rollback_outputs", _boundary_mutation, {}),
    ("concurrent_key_produces_one_materialized_bundle", _concurrent, {}),
    ("preserve_live_evidence_and_forecast_time_boundaries_around_groups", _grouped_time_boundary, {}),
    ("reject_oversized_parent_descriptor_before_output_writes", _resource_bound, {"operation": "identity", "bounds": "descriptor"}),
    ("reject_amplified_output_record_metadata_before_output_writes", _resource_bound, {"bounds": "aggregate"}),
)


def run_materialization_checks():
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
    return {"version": "materialization-probes-v1", "checks": rows, "counts": {METRIC: count},
            "metrics": {METRIC: count["passed"] / count["checks"]}, "all_passed": all(row["passed"] for row in rows),
            "interpretation": "Actual fixed graph outputs materialized into atomic representation/manifest bundles on isolated synthetic ledgers. No retrieval, model inference, semantic equivalence, externally witnessed execution or predictive/business lift measured."}
