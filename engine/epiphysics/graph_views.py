"""Execute bounded graph partition/merge recipes without reconciling semantics.

A partition creates induced views of existing records, not new real-world
entities. Retained code is matched to fixed loaded functions, never evaluated.
Outputs remain embedded in terminal events; no new manifest is materialized.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, store, transforms
from .store import canonical, digest
from .assertions import _event_integrity, _hash, _read_transaction, _snapshot, _text, _time
from .manifests import _checked_manifest, _ids, _keys, _model_evidence

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions, manifests, transforms)
)
_LEDGER_CLASS = store.Ledger
_MODULES = (store, assertions, manifests, transforms, sys.modules[__name__])
_IMPLEMENTATIONS = tuple((module, Path(module.__file__), module.IMPLEMENTATION_SOURCE,
                        module.IMPLEMENTATION_CODE, module.IMPLEMENTATION_DEPENDENCIES) for module in _MODULES)
DEPENDENCY_NAMES = tuple(module.__name__ for module in (store, assertions, manifests, transforms))
OUTPUT_SCHEMA = "epiphysics.graph.v1"
MAX_PARENTS = 16
MAX_VIEWS = 64
MAX_PARENT_ID_BYTES = 512
MAX_VIEW_NAME_BYTES = 128
MAX_TOTAL_MODEL_BYTES = 2_000_000
MAX_TERMINAL_BYTES = 10_000_000
OPERATIONS = {"partition_entities", "merge_graphs"}
TERMINALS = {"graph_views_completed", "graph_views_rejected"}


def _runtime_sources():
    codes = {module.__name__: code for module, _, _, code, _ in _IMPLEMENTATIONS}
    for name, function, code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not code:
            raise ValueError(f"Fixed graph views callable changed: {name}; use a fresh reviewed process")
    for module, path, source, code, dependencies in _IMPLEMENTATIONS:
        if module.IMPLEMENTATION_CODE is not code or module.IMPLEMENTATION_SOURCE != source:
            raise ValueError(f"Graph views implementation reloaded: {module.__name__}")
        if path.read_bytes() != source:
            raise ValueError(f"Graph views implementation source changed: {module.__name__}")
        if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
            raise ValueError(f"Executing code does not match retained source: {module.__name__}")
        for dependency_name, dependency_code in dependencies:
            if codes.get(dependency_name) is not dependency_code:
                raise ValueError(f"Graph views dependency reloaded: {module.__name__} -> {dependency_name}")
    transforms._runtime_sources()  # Also pin the reused graph and retained-artifact helper functions.
    return {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS}


def _request_metadata(ledger, parent_manifest_ids, recipe_observation_id):
    parents = []
    for parent_id in parent_manifest_ids:
        parent = ledger.get(parent_id, "representation_manifest")
        _event_integrity(parent)
        _keys(parent["body"], manifests.MANIFEST_FIELDS, "parent manifest")
        representation = ledger.get(parent["body"]["representation_id"], "representation")
        snapshot = ledger.get(parent["body"]["snapshot_id"], "snapshot")
        for event in (representation, snapshot):
            _event_integrity(event)
        parents.append({"manifest": {"id": parent_id, "hash": parent["hash"]},
            "representation": {"id": representation["id"], "hash": representation["hash"],
                               "model_hash": digest(canonical(representation["body"]["model"]).encode("utf-8"))},
            "snapshot": {"id": snapshot["id"], "hash": snapshot["hash"],
                         "manifest_hash": snapshot["body"]["manifest_hash"], "cutoff": snapshot["body"]["cutoff"]}})
    recipe = ledger.get(recipe_observation_id, "observation")
    _event_integrity(recipe)
    _hash(recipe["body"].get("content_hash"), "Recipe content_hash")
    sources = {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS}
    return {"parents": parents,
        "recipe": {"observation_id": recipe["id"], "event_hash": recipe["hash"], "content_hash": recipe["body"]["content_hash"]},
        "implementation": {"source_sha256": digest(sources[__name__]),
                           "dependencies": {name: digest(sources[name]) for name in DEPENDENCY_NAMES}}}


def _semantics(parent):
    body = parent["body"]
    descriptor = body["descriptor"]
    return {"snapshot_id": body["snapshot_id"], "snapshot_hash": body["snapshot_hash"],
        **{key: descriptor[key] for key in ("encoding", "schema_id", "observer", "task", "horizon_seconds", "units")},
        "ontology": descriptor["artifact_hashes"]["ontology"], "predictor": descriptor["artifact_hashes"]["predictor"]}


def _metadata(model):
    return {key: value for key, value in model.items() if key not in ("entities", "relations")}


def _edge_tuple(edge):
    return tuple(edge[key] for key in ("source", "target", "type"))


def _compute_graph_views(parent_models, operation, config):
    """Compute fixed record operations with explicit losses and ancestry."""
    outputs, mappings, removed = {}, [], []
    deduplications = {"entities": [], "relations": []}
    if operation == "partition_entities":
        parent_id, model = parent_models[0]
        assignment = {eid: name for name, ids in config["views"].items() for eid in ids}
        for name in sorted(config["views"]):
            output = deepcopy(_metadata(model))
            output["entities"] = [deepcopy(row) for row in model["entities"] if assignment[row["id"]] == name]
            output["relations"] = [deepcopy(row) for row in model["relations"]
                                   if assignment[row["source"]] == name == assignment[row["target"]]]
            outputs[name] = output
        entities = [{"source_id": row["id"], "output": {"view": assignment[row["id"]], "id": row["id"]}}
                    for row in model["entities"]]
        relations = []
        for row in model["relations"]:
            name = assignment[row["source"]]
            destination = {"view": name, "key": transforms._edge_key(row)} if name == assignment[row["target"]] else None
            relations.append({"source_key": transforms._edge_key(row), "output": destination})
            if destination is None:
                removed.append({"parent_manifest_id": parent_id, "record": deepcopy(row)})
        mappings.append({"parent_manifest_id": parent_id, "entities": entities, "relations": relations,
                         "metadata": {"fields": sorted(_metadata(model)), "output_views": sorted(outputs)}})
    else:
        metadata = _metadata(parent_models[0][1])
        entities, relations, relation_ids = {}, {}, {}
        entity_parents, relation_parents = {}, {}
        for parent_id, model in parent_models:
            if canonical(_metadata(model)) != canonical(metadata):
                raise ValueError("Merge parent root metadata must match exactly")
            for row in model["entities"]:
                eid = row["id"]
                if eid in entities and canonical(entities[eid]) != canonical(row):
                    raise ValueError(f"Conflicting merge entity record: {eid}")
                entities[eid] = deepcopy(row)
                entity_parents.setdefault(eid, []).append(parent_id)
            for row in model["relations"]:
                key = _edge_tuple(row)
                if key in relations and canonical(relations[key]) != canonical(row):
                    raise ValueError("Conflicting merge relation record")
                if "id" in row:
                    rid = row["id"]
                    if rid in relation_ids and relation_ids[rid] != key:
                        raise ValueError(f"Conflicting merge relation id: {rid}")
                    relation_ids[rid] = key
                relations[key] = deepcopy(row)
                relation_parents.setdefault(key, []).append(parent_id)
            mappings.append({"parent_manifest_id": parent_id,
                "entities": [{"source_id": row["id"], "output": {"view": "merged", "id": row["id"]}}
                             for row in model["entities"]],
                "relations": [{"source_key": transforms._edge_key(row),
                               "output": {"view": "merged", "key": transforms._edge_key(row)}} for row in model["relations"]],
                "metadata": {"fields": sorted(metadata), "output_views": ["merged"]}})
        output = deepcopy(metadata)
        output["entities"] = [entities[eid] for eid in sorted(entities)]
        output["relations"] = [relations[key] for key in sorted(relations)]
        outputs["merged"] = output
        deduplications = {
            "entities": [{"output_id": eid, "parent_manifest_ids": sorted(entity_parents[eid])}
                         for eid in sorted(entities) if len(entity_parents[eid]) > 1],
            "relations": [{"output_key": transforms._edge_key(relations[key]), "parent_manifest_ids": sorted(relation_parents[key])}
                          for key in sorted(relations) if len(relation_parents[key]) > 1]}
    input_evidence = set().union(*(_model_evidence(model) for _, model in parent_models))
    output_evidence = set().union(*(_model_evidence(model) for model in outputs.values()))
    if sum(len(canonical(model).encode("utf-8")) for model in outputs.values()) > MAX_TOTAL_MODEL_BYTES:
        raise ValueError("Combined graph view outputs exceed 2 MB")
    return {"outputs": {name: {"model": model, "model_hash": digest(canonical(model).encode("utf-8"))}
                        for name, model in outputs.items()},
            "losses": {"removed_entities": [], "removed_relations": removed,
                       "removed_evidence_ids": sorted(input_evidence - output_evidence)},
            "source_to_output": mappings, "deduplications": deduplications}


def _prepare(ledger, parent_manifest_ids, recipe_observation_id, now):
    sources = _runtime_sources()
    parents = [_checked_manifest(ledger, parent_id, now) for parent_id in parent_manifest_ids]
    for parent in parents:
        descriptor = parent["body"]["descriptor"]
        if descriptor["encoding"] != "directed-graph" or descriptor["schema_id"] != OUTPUT_SCHEMA:
            raise ValueError("Unsupported parent encoding/schema; require directed-graph / epiphysics.graph.v1")
    if any(canonical(_semantics(parent)) != canonical(_semantics(parents[0])) for parent in parents[1:]):
        raise ValueError("Merge parents require an identical snapshot and compatible declared semantics")
    snapshot, entries = _snapshot(ledger, parents[0]["body"]["snapshot_id"], now)
    recipe_ref, recipe_raw = transforms._retained(ledger, recipe_observation_id, snapshot, entries, now)
    recipe = transforms._json(recipe_raw, "recipe")
    _keys(recipe, {"schema_version", "operation", "config_observation_id", "implementation_observation_id",
                   "implementation_sha256", "dependency_observations", "output_schema"}, "graph views recipe")
    if type(recipe["schema_version"]) is not int or recipe["schema_version"] != 1:
        raise ValueError("Recipe schema_version must be 1")
    if type(recipe["operation"]) is not str or recipe["operation"] not in OPERATIONS:
        raise ValueError("Unsupported fixed graph views operation")
    if recipe["output_schema"] != OUTPUT_SCHEMA:
        raise ValueError("Unsupported graph output schema")
    if recipe["operation"] == "partition_entities" and len(parents) != 1:
        raise ValueError("Partition requires exactly one parent")
    if recipe["operation"] == "merge_graphs" and len(parents) < 2:
        raise ValueError("Merge requires at least two distinct parents")
    _hash(recipe["implementation_sha256"], "Recipe implementation_sha256")
    code_ref, code_raw = transforms._retained(ledger, recipe["implementation_observation_id"], snapshot, entries, now)
    if digest(code_raw) != recipe["implementation_sha256"] or code_raw != sources[__name__]:
        raise ValueError("Retained implementation does not match the fixed executing source")
    _keys(recipe["dependency_observations"], DEPENDENCY_NAMES, "recipe dependencies")
    dependencies = {}
    for name in DEPENDENCY_NAMES:
        ref, raw = transforms._retained(ledger, recipe["dependency_observations"][name], snapshot, entries, now)
        if raw != sources[name]:
            raise ValueError(f"Retained dependency does not match executing source: {name}")
        dependencies[name] = ref
    config_ref, config_raw = transforms._retained(ledger, recipe["config_observation_id"], snapshot, entries, now)
    config = transforms._json(config_raw, "configuration")
    _keys(config, ("views",) if recipe["operation"] == "partition_entities" else ("conflicts",), "graph views configuration")
    parent_models = []
    eligible = set()
    for parent in parents:
        body = parent["body"]
        model = ledger.get(body["representation_id"], "representation")["body"]["model"]
        parent_evidence = {ref["observation_id"] for ref in body["evidence"]}
        transforms._graph(model, parent_evidence)
        eligible.update(parent_evidence)
        parent_models.append((parent["id"], model))
    if sum(len(canonical(model).encode("utf-8")) for _, model in parent_models) > MAX_TOTAL_MODEL_BYTES:
        raise ValueError("Combined graph view inputs exceed 2 MB")
    if recipe["operation"] == "partition_entities":
        views = config["views"]
        if type(views) is not dict or not 1 <= len(views) <= MAX_VIEWS:
            raise ValueError("Partition requires 1–64 named views")
        assigned = set()
        for name, ids in views.items():
            _text(name, "View name")
            if len(name.encode("utf-8")) > MAX_VIEW_NAME_BYTES:
                raise ValueError("View name exceeds 128 UTF-8 bytes")
            selected = _ids(ids, "view entity IDs")
            if not selected or assigned.intersection(selected):
                raise ValueError("Partition views must be nonempty and disjoint")
            assigned.update(selected)
        if assigned != {row["id"] for row in parent_models[0][1]["entities"]}:
            raise ValueError("Partition must cover every parent entity exactly")
    elif config["conflicts"] != "reject":
        raise ValueError("Merge conflicts policy must be reject")
    descriptor = {"schema_version": 1, "operation": recipe["operation"], "config_sha256": config_ref["content_hash"],
        "implementation_sha256": code_ref["content_hash"],
        "dependency_hashes": {name: ref["content_hash"] for name, ref in dependencies.items()}, "output_schema": OUTPUT_SCHEMA}
    computed = _compute_graph_views(parent_models, recipe["operation"], config)
    for output in computed["outputs"].values():
        transforms._graph(output["model"], eligible)
    return {"recipe_id": "graph-views-recipe-v1:" + digest(canonical(descriptor).encode("utf-8")),
        "recipe_descriptor": descriptor,
        "inputs": {"parents": [{"manifest_id": parent["id"], "representation_id": parent["body"]["representation_id"],
                                "snapshot_id": parent["body"]["snapshot_id"]} for parent in parents],
                   "recipe": recipe_ref, "config": config_ref, "implementation": code_ref, "dependencies": dependencies},
        "output_schema": OUTPUT_SCHEMA, **computed}


def execute_graph_views(ledger, parent_manifest_ids, recipe_observation_id, *, run_key):
    """Run a fixed partition or merge and retain a replayable completion/rejection.

    Parent input is a set: caller ordering is normalized. Unaddressable requests
    refuse before claim; interrupted starts require diagnosis, not blind replay.
    """
    if sys._getframe().f_code is not execute_graph_views.__code__:
        raise ValueError("Stale graph views callable; use a fresh reviewed process")
    if type(ledger) is not _LEDGER_CLASS or _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class")
    parent_manifest_ids = _ids(parent_manifest_ids, "parent_manifest_ids", maximum=MAX_PARENTS)
    if not parent_manifest_ids:
        raise ValueError("At least one parent manifest is required")
    for parent_id in parent_manifest_ids:
        if len(parent_id.encode("utf-8")) > MAX_PARENT_ID_BYTES:
            raise ValueError("Parent manifest ID exceeds 512 UTF-8 bytes")
    _text(recipe_observation_id, "recipe_observation_id")
    if type(run_key) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key) is None:
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    started_id, terminal_id = f"graph-views:{run_key}:started", f"graph-views:{run_key}:terminal"
    with _read_transaction(ledger):
        request = _request_metadata(ledger, parent_manifest_ids, recipe_observation_id)
        start, terminal = transforms._optional(ledger, started_id), transforms._optional(ledger, terminal_id)
        if start is not None and (start["kind"] != "graph_views_started" or start["body"].get("request") != request):
            raise ValueError("Run key already has a different request")
        if terminal is not None:
            if start is None or terminal["kind"] not in TERMINALS or terminal["body"].get("request") != request:
                raise ValueError("Run key has an invalid or different terminal request")
            return terminal
        if start is not None:
            raise ValueError("Incomplete graph views run requires diagnosis; do not blindly replay")

    def validate_claim(_):
        if transforms._optional(ledger, terminal_id) is not None:
            raise ValueError("Run already has a terminal record")
        if _request_metadata(ledger, parent_manifest_ids, recipe_observation_id) != request:
            raise ValueError("Graph views request changed before claim")

    ledger.append("graph_views_started", {"schema_version": 1, "run_key": run_key, "request": request},
                  started_id, validate=validate_claim, exclusive=True)

    def validate_terminal(_):
        claimed = ledger.get(started_id, "graph_views_started")
        _event_integrity(claimed)
        if claimed["body"]["request"] != request or transforms._optional(ledger, terminal_id) is not None:
            raise ValueError("Graph views terminal does not match its unfinished claim")

    try:
        with _read_transaction(ledger):
            result = _prepare(ledger, parent_manifest_ids, recipe_observation_id, _time(ledger.clock(), "Ledger clock"))
        body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "completed", **result,
                "resources": {"model_calls": 0, "external_spend": 0},
                "scope": "Executed fixed graph views; units remain labels. No semantic equivalence, entity fission, new manifest or forecast claim."}
        if len(canonical(body).encode("utf-8")) > MAX_TERMINAL_BYTES:
            raise ValueError("Graph views completion exceeds 10 MB")

        def validate_completion(recorded_at):
            validate_terminal(recorded_at)
            if _request_metadata(ledger, parent_manifest_ids, recipe_observation_id) != request:
                raise ValueError("Graph views request changed before completion")
            checked = _prepare(ledger, parent_manifest_ids, recipe_observation_id, _time(recorded_at, "Completion recorded_at"))
            if canonical(checked) != canonical(result):
                raise ValueError("Graph views inputs or computed output changed before completion")

        return ledger.append("graph_views_completed", body, terminal_id, validate=validate_completion, exclusive=True)
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as error:
        body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "rejected",
                "error": {"type": type(error).__name__, "message": transforms._diagnostic(error)}}
        return ledger.append("graph_views_rejected", body, terminal_id, validate=validate_terminal, exclusive=True)


_FUNCTION_CODES = tuple((name, value, value.__code__) for name, value in list(globals().items())
                        if callable(value) and getattr(value, "__module__", None) == __name__ and hasattr(value, "__code__"))
