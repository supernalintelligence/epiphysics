"""Execute two fixed graph operations with retained recipes and explicit losses.

Retained code is verified, never evaluated. Outputs are embedded in one terminal
event; this slice does not materialize new representations or forecast manifests.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, store
from .store import canonical, digest
from .assertions import _event_integrity, _hash, _read_transaction, _snapshot, _text, _time
from .manifests import _checked_manifest, _ids, _keys, _model_evidence, _observation

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions, manifests)
)
_LEDGER_CLASS = store.Ledger
_MODULES = (store, assertions, manifests, sys.modules[__name__])
_IMPLEMENTATIONS = tuple((module, Path(module.__file__), module.IMPLEMENTATION_SOURCE,
                        module.IMPLEMENTATION_CODE, module.IMPLEMENTATION_DEPENDENCIES) for module in _MODULES)
DEPENDENCY_NAMES = tuple(module.__name__ for module in (store, assertions, manifests))
OUTPUT_SCHEMA = "epiphysics.graph.v1"
MAX_BYTES = 1_000_000
MAX_TERMINAL_BYTES = 10_000_000
OPERATIONS = {"identity", "project_entities"}
TERMINALS = {"graph_transform_completed", "graph_transform_rejected"}


def _runtime_sources():
    codes = {module.__name__: code for module, _, _, code, _ in _IMPLEMENTATIONS}
    for name, function, code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not code:
            raise ValueError(f"Fixed transform callable changed: {name}; use a fresh reviewed process")
    for module, path, source, code, dependencies in _IMPLEMENTATIONS:
        if module.IMPLEMENTATION_CODE is not code or module.IMPLEMENTATION_SOURCE != source:
            raise ValueError(f"Transform implementation reloaded: {module.__name__}")
        if path.read_bytes() != source:
            raise ValueError(f"Transform implementation source changed: {module.__name__}")
        if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
            raise ValueError(f"Executing code does not match retained source: {module.__name__}")
        for dependency_name, dependency_code in dependencies:
            if codes.get(dependency_name) is not dependency_code:
                raise ValueError(f"Transform dependency reloaded: {module.__name__} -> {dependency_name}")
    return {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS}


def _request_metadata(ledger, parent_manifest_id, recipe_observation_id):
    parent = ledger.get(parent_manifest_id, "representation_manifest")
    _event_integrity(parent)
    _keys(parent["body"], manifests.MANIFEST_FIELDS, "parent manifest")
    representation = ledger.get(parent["body"]["representation_id"], "representation")
    snapshot = ledger.get(parent["body"]["snapshot_id"], "snapshot")
    recipe = ledger.get(recipe_observation_id, "observation")
    for event in (representation, snapshot, recipe):
        _event_integrity(event)
    _hash(recipe["body"].get("content_hash"), "Recipe content_hash")
    sources = {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS}
    return {"parent_manifest": {"id": parent["id"], "hash": parent["hash"]},
        "parent_representation": {"id": representation["id"], "hash": representation["hash"],
                                  "model_hash": digest(canonical(representation["body"]["model"]).encode("utf-8"))},
        "snapshot": {"id": snapshot["id"], "hash": snapshot["hash"],
                     "manifest_hash": snapshot["body"]["manifest_hash"], "cutoff": snapshot["body"]["cutoff"]},
        "recipe": {"observation_id": recipe["id"], "event_hash": recipe["hash"],
                   "content_hash": recipe["body"]["content_hash"]},
        "implementation": {"source_sha256": digest(sources[__name__]),
                           "dependencies": {name: digest(sources[name]) for name in DEPENDENCY_NAMES}}}


def _optional(ledger, event_id):
    if ledger.db.execute("SELECT 1 FROM events WHERE id=?", (event_id,)).fetchone() is None:
        return None
    event = ledger.get(event_id)
    _event_integrity(event)
    return event


def _retained(ledger, observation_id, snapshot, entries, now):
    ref = _observation(ledger, observation_id, now, snapshot=snapshot, entries=entries, verify_bytes=False)
    path = ledger.root / "blobs" / ref["content_hash"]
    if path.is_symlink() or not path.is_file():
        raise ValueError("Transform artifact must be a retained regular blob")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Transform artifact exceeds 1 MB")
    observation = ledger.get(observation_id, "observation")
    if digest(raw) != ref["content_hash"] or len(raw) != observation["body"]["size"]:
        raise ValueError("Transform artifact hash or size mismatch")
    return ref, raw


def _json(raw, label):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON field in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        canonical(value)
        return value
    except (ValueError, UnicodeDecodeError, RecursionError) as error:
        raise ValueError(f"Invalid finite JSON {label}: {error}") from error


def _graph(model, eligible):
    if type(model) is not dict or "entities" not in model or "relations" not in model:
        raise ValueError("Graph model requires explicit entities and relations arrays")
    if len(canonical(model).encode("utf-8")) > MAX_BYTES:
        raise ValueError("Graph model exceeds 1 MB")
    if type(model["entities"]) is not list or len(model["entities"]) > 1000:
        raise ValueError("Graph requires at most 1000 entities")
    if type(model["relations"]) is not list or len(model["relations"]) > 5000:
        raise ValueError("Graph requires at most 5000 relations")
    ids = set()
    triples, relation_ids = set(), set()
    for kind, rows in (("entity", model["entities"]), ("relation", model["relations"])):
        for row in rows:
            if type(row) is not dict:
                raise ValueError(f"Graph {kind} must be an object")
            evidence = _ids(row.get("evidence_ids"), f"{kind} evidence IDs")
            if not evidence or not set(evidence) <= eligible:
                raise ValueError(f"Graph {kind} requires nonempty eligible evidence")
            if row.get("basis") not in ("observed", "reported", "inferred"):
                raise ValueError(f"Graph {kind} requires an epistemic basis")
            if kind == "entity":
                eid = _text(row.get("id"), "Entity id")
                if eid in ids:
                    raise ValueError("Duplicate graph entity id")
                ids.add(eid)
            else:
                key = tuple(_text(row.get(field), f"Relation {field}") for field in ("source", "target", "type"))
                if key[0] not in ids or key[1] not in ids:
                    raise ValueError("Graph relation endpoint does not exist")
                if key in triples:
                    raise ValueError("Duplicate typed directed graph relation")
                triples.add(key)
                if "id" in row:
                    rid = _text(row["id"], "Relation id")
                    if rid in relation_ids:
                        raise ValueError("Duplicate graph relation id")
                    relation_ids.add(rid)


def _edge_key(relation):
    return {field: relation[field] for field in ("source", "target", "type")}


def _compute_graph(model, operation, config):
    """Fixed execution: copy identity, or retain an induced subset in parent order."""
    retained = {entity["id"] for entity in model["entities"]}
    if operation == "project_entities":
        retained = set(config["entity_ids"])
    output = deepcopy(model)
    output["entities"] = [deepcopy(entity) for entity in model["entities"] if entity["id"] in retained]
    output["relations"] = [deepcopy(edge) for edge in model["relations"]
                           if edge["source"] in retained and edge["target"] in retained]
    removed_entities = [deepcopy(entity) for entity in model["entities"] if entity["id"] not in retained]
    removed_relations = [deepcopy(edge) for edge in model["relations"]
                         if edge["source"] not in retained or edge["target"] not in retained]
    return {"output_model": output,
        "losses": {"removed_entities": removed_entities, "removed_relations": removed_relations,
                   "removed_evidence_ids": sorted(_model_evidence(model) - _model_evidence(output))},
        "source_to_output": {
            "entities": {entity["id"]: entity["id"] if entity["id"] in retained else None for entity in model["entities"]},
            "relations": [{"source_key": _edge_key(edge), "output_key": _edge_key(edge)
                           if edge["source"] in retained and edge["target"] in retained else None}
                          for edge in sorted(model["relations"], key=lambda edge: tuple(edge[k] for k in ("source", "target", "type")))]},
        "canonical_exact": canonical(model) == canonical(output)}


def _prepare(ledger, parent_manifest_id, recipe_observation_id, now):
    sources = _runtime_sources()
    parent = _checked_manifest(ledger, parent_manifest_id, now)
    body = parent["body"]
    if body["descriptor"]["encoding"] != "directed-graph" or body["descriptor"]["schema_id"] != OUTPUT_SCHEMA:
        raise ValueError("Unsupported parent encoding/schema; require directed-graph / epiphysics.graph.v1")
    snapshot, entries = _snapshot(ledger, body["snapshot_id"], now)
    recipe_ref, recipe_raw = _retained(ledger, recipe_observation_id, snapshot, entries, now)
    recipe = _json(recipe_raw, "recipe")
    _keys(recipe, {"schema_version", "operation", "config_observation_id", "implementation_observation_id",
                   "implementation_sha256", "dependency_observations", "output_schema"}, "graph recipe")
    if type(recipe["schema_version"]) is not int or recipe["schema_version"] != 1:
        raise ValueError("Recipe schema_version must be 1")
    if type(recipe["operation"]) is not str or recipe["operation"] not in OPERATIONS:
        raise ValueError("Unsupported fixed graph operation")
    if recipe["output_schema"] != OUTPUT_SCHEMA:
        raise ValueError("Unsupported graph output schema")
    _hash(recipe["implementation_sha256"], "Recipe implementation_sha256")
    code_ref, code_raw = _retained(ledger, recipe["implementation_observation_id"], snapshot, entries, now)
    if digest(code_raw) != recipe["implementation_sha256"] or code_raw != sources[__name__]:
        raise ValueError("Retained implementation does not match the fixed executing source")
    _keys(recipe["dependency_observations"], DEPENDENCY_NAMES, "recipe dependencies")
    dependencies = {}
    for name in DEPENDENCY_NAMES:
        ref, raw = _retained(ledger, recipe["dependency_observations"][name], snapshot, entries, now)
        if raw != sources[name]:
            raise ValueError(f"Retained dependency does not match executing source: {name}")
        dependencies[name] = ref
    config_ref, config_raw = _retained(ledger, recipe["config_observation_id"], snapshot, entries, now)
    config = _json(config_raw, "configuration")
    _keys(config, () if recipe["operation"] == "identity" else ("entity_ids",), "graph configuration")
    representation = ledger.get(body["representation_id"], "representation")
    model = representation["body"]["model"]
    eligible = {ref["observation_id"] for ref in body["evidence"]}
    _graph(model, eligible)
    if recipe["operation"] == "project_entities":
        selected = _ids(config["entity_ids"], "projection entity IDs")
        if not set(selected) <= {entity["id"] for entity in model["entities"]}:
            raise ValueError("Projection selects an unknown entity")
    descriptor = {"schema_version": 1, "operation": recipe["operation"], "config_sha256": config_ref["content_hash"],
        "implementation_sha256": code_ref["content_hash"],
        "dependency_hashes": {name: ref["content_hash"] for name, ref in dependencies.items()}, "output_schema": OUTPUT_SCHEMA}
    computed = _compute_graph(model, recipe["operation"], config)
    _graph(computed["output_model"], eligible)
    return {"recipe_id": "graph-recipe-v1:" + digest(canonical(descriptor).encode("utf-8")),
        "recipe_descriptor": descriptor,
        "inputs": {"parent_manifest_id": parent_manifest_id, "parent_representation_id": representation["id"],
                   "snapshot_id": snapshot["id"], "recipe": recipe_ref, "config": config_ref,
                   "implementation": code_ref, "dependencies": dependencies},
        "output_schema": OUTPUT_SCHEMA, **computed,
        "output_model_hash": digest(canonical(computed["output_model"]).encode("utf-8"))}


def _diagnostic(error):
    """Keep malformed-input diagnostics bounded and encodable in the event chain."""
    return str(error).encode("utf-8", errors="backslashreplace").decode("utf-8")[:400]


def execute_graph_transform(ledger, parent_manifest_id, recipe_observation_id, *, run_key):
    """Claim and execute one retained fixed recipe, returning its immutable terminal event.

    Unaddressable requests refuse before claiming. Addressable invalid recipes or
    inputs produce a started/rejected pair. Incomplete starts require diagnosis.
    """
    if sys._getframe().f_code is not execute_graph_transform.__code__:
        raise ValueError("Stale transform callable; use a fresh reviewed process")
    if type(ledger) is not _LEDGER_CLASS or _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class")
    _text(parent_manifest_id, "parent_manifest_id")
    _text(recipe_observation_id, "recipe_observation_id")
    if type(run_key) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key) is None:
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    started_id, terminal_id = f"graph-transform:{run_key}:started", f"graph-transform:{run_key}:terminal"
    with _read_transaction(ledger):
        request = _request_metadata(ledger, parent_manifest_id, recipe_observation_id)
        start, terminal = _optional(ledger, started_id), _optional(ledger, terminal_id)
        if start is not None and (start["kind"] != "graph_transform_started" or start["body"].get("request") != request):
            raise ValueError("Run key already has a different request")
        if terminal is not None:
            if start is None or terminal["kind"] not in TERMINALS or terminal["body"].get("request") != request:
                raise ValueError("Run key has an invalid or different terminal request")
            return terminal
        if start is not None:
            raise ValueError("Incomplete transform run requires diagnosis; do not blindly replay")

    def validate_claim(_):
        if _optional(ledger, terminal_id) is not None:
            raise ValueError("Run already has a terminal record")
        if _request_metadata(ledger, parent_manifest_id, recipe_observation_id) != request:
            raise ValueError("Transform request changed before claim")

    ledger.append("graph_transform_started", {"schema_version": 1, "run_key": run_key, "request": request},
                  started_id, validate=validate_claim, exclusive=True)

    def validate_terminal(_):
        claimed = ledger.get(started_id, "graph_transform_started")
        _event_integrity(claimed)
        if claimed["body"]["request"] != request or _optional(ledger, terminal_id) is not None:
            raise ValueError("Transform terminal does not match its unfinished claim")

    try:
        with _read_transaction(ledger):
            result = _prepare(ledger, parent_manifest_id, recipe_observation_id, _time(ledger.clock(), "Ledger clock"))
        body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "completed", **result,
                "resources": {"model_calls": 0, "external_spend": 0},
                "scope": "Executed fixed graph operation; units remain labels. No semantic equivalence, new manifest, or forecast claim."}
        if len(canonical(body).encode("utf-8")) > MAX_TERMINAL_BYTES:
            raise ValueError("Transform completion exceeds 10 MB")

        def validate_completion(recorded_at):
            validate_terminal(recorded_at)
            if _request_metadata(ledger, parent_manifest_id, recipe_observation_id) != request:
                raise ValueError("Transform request changed before completion")
            checked = _prepare(ledger, parent_manifest_id, recipe_observation_id, _time(recorded_at, "Completion recorded_at"))
            if canonical(checked) != canonical(result):
                raise ValueError("Transform inputs or computed output changed before completion")

        return ledger.append("graph_transform_completed", body, terminal_id, validate=validate_completion, exclusive=True)
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as error:
        body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "rejected",
                "error": {"type": type(error).__name__, "message": _diagnostic(error)}}
        return ledger.append("graph_transform_rejected", body, terminal_id, validate=validate_terminal, exclusive=True)


# Pin this small module's own callable objects as well as the finite module graph.
_FUNCTION_CODES = tuple((name, value, value.__code__) for name, value in list(globals().items())
                        if callable(value) and getattr(value, "__module__", None) == __name__ and hasattr(value, "__code__"))
