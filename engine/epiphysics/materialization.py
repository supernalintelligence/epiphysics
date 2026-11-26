"""Atomically materialize fixed graph execution outputs into B1 records.

The whole output set and its lineage receipt commit together. New writes require
the current execution contract; historical replay never re-executes archived code.
These are local hash-checked records, not signatures or external witnesses.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, graph_views, manifests, store, transforms
from .store import canonical, digest
from .assertions import _event_integrity, _read_transaction, _text, _time
from .manifests import _checked_manifest, _ids, _keys, _model_evidence

IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE)
    for module in (store, assertions, manifests, transforms, graph_views))
_LEDGER_CLASS = store.Ledger
_MODULES = (store, assertions, manifests, transforms, graph_views, sys.modules[__name__])
_IMPLEMENTATIONS = tuple((module, Path(module.__file__), module.IMPLEMENTATION_SOURCE,
    module.IMPLEMENTATION_CODE, module.IMPLEMENTATION_DEPENDENCIES) for module in _MODULES)
DEPENDENCY_NAMES = tuple(module.__name__ for module in (store, assertions, manifests, transforms, graph_views))
MAX_RECORD_BYTES = 10_000_000
MAX_DESCRIPTOR_BYTES = 16_384
MAX_OUTPUT_RECORD_BYTES = 8_000_000
MAX_ID_BYTES = 512
MAX_VIEW_NAME_BYTES = 128
COMPLETIONS = {"graph_transform_completed", "graph_views_completed"}
TERMINALS = {"graph_materialization_completed", "graph_materialization_rejected"}


def _runtime_sources():
    codes = {module.__name__: code for module, _, _, code, _ in _IMPLEMENTATIONS}
    for name, function, code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not code:
            raise ValueError(f"Fixed materialization callable changed: {name}; use a fresh reviewed process")
    for module, path, source, code, dependencies in _IMPLEMENTATIONS:
        if module.IMPLEMENTATION_CODE is not code or module.IMPLEMENTATION_SOURCE != source:
            raise ValueError(f"Materialization implementation reloaded: {module.__name__}")
        if path.read_bytes() != source:
            raise ValueError(f"Materialization implementation source changed: {module.__name__}")
        if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
            raise ValueError(f"Executing code does not match retained source: {module.__name__}")
        for name, dependency_code in dependencies:
            if codes.get(name) is not dependency_code:
                raise ValueError(f"Materialization dependency reloaded: {module.__name__} -> {name}")
    graph_views._runtime_sources()
    return {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS}


def _identifier(value, label):
    _text(value, label)
    if len(value.encode("utf-8")) > MAX_ID_BYTES:
        raise ValueError(f"{label} exceeds 512 UTF-8 bytes")
    return value


def _run_key(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value) is None:
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    return value


def _get(ledger, event_id, kind=None):
    _identifier(event_id, "Event ID")
    row = ledger.db.execute("SELECT length(CAST(body AS BLOB)) AS size FROM events WHERE id=?", (event_id,)).fetchone()
    if row is not None and row["size"] > MAX_RECORD_BYTES:
        raise ValueError("Materialization input record exceeds 10 MB")
    event = ledger.get(event_id, kind)
    _event_integrity(event)
    return event


def _bounded_size(value, limit, label):
    """Count canonical UTF-8 incrementally, refusing before joining a large string."""
    total = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        if len(chunk) > limit - total:
            raise ValueError(f"{label} exceeds its byte limit")
        total += len(chunk.encode("utf-8"))
        if total > limit:
            raise ValueError(f"{label} exceeds its byte limit")
    return total


def _observation_body(ledger, observation_id, label):
    observation = _get(ledger, observation_id, "observation")
    if type(observation["body"]) is not dict:
        raise ValueError(f"{label} body must be an object")
    return observation


def _recipe_observation_shapes(ledger, recipe_id, parent, producer, now):
    """Check referenced containers before helpers that expect observation objects."""
    snapshot, entries = assertions._snapshot(ledger, parent["body"]["snapshot_id"], now)
    _, raw = transforms._retained(ledger, recipe_id, snapshot, entries, now)
    recipe = transforms._json(raw, "recipe")
    _keys(recipe, {"schema_version", "operation", "config_observation_id", "implementation_observation_id",
                   "implementation_sha256", "dependency_observations", "output_schema"}, "execution recipe")
    _keys(recipe["dependency_observations"], producer.DEPENDENCY_NAMES, "recipe dependencies")
    for observation_id in (recipe["config_observation_id"], recipe["implementation_observation_id"],
                           *recipe["dependency_observations"].values()):
        _identifier(observation_id, "Recipe artifact observation ID")
        _observation_body(ledger, observation_id, "Recipe artifact observation")


def _request_metadata(ledger, completion_id):
    completion = _get(ledger, completion_id)
    if completion["kind"] not in COMPLETIONS:
        raise ValueError("Materialization requires a completed fixed graph execution")
    return {"schema_version": 1, "completion": {"id": completion["id"], "kind": completion["kind"], "hash": completion["hash"]}}


def _execution(ledger, completion_id, now):
    """Read immutable execution metadata, without reading retained blob bytes."""
    completion = _get(ledger, completion_id)
    if completion["kind"] not in COMPLETIONS:
        raise ValueError("Materialization requires a completed fixed graph execution")
    body = completion["body"]
    if type(body) is not dict:
        raise ValueError("Execution completion body must be an object")
    if type(body.get("schema_version")) is not int or body["schema_version"] != 1 or body.get("result") != "completed":
        raise ValueError("Invalid execution completion schema or result")
    run_key = _run_key(body.get("run_key"))
    prefix, started_kind = ("graph-transform", "graph_transform_started") if completion["kind"] == "graph_transform_completed" else ("graph-views", "graph_views_started")
    if completion_id != f"{prefix}:{run_key}:terminal":
        raise ValueError("Execution completion ID does not match its run key")
    started = _get(ledger, f"{prefix}:{run_key}:started", started_kind)
    _keys(started["body"], {"schema_version", "run_key", "request"}, "execution start")
    if (type(started["body"]["schema_version"]) is not int or started["body"]["schema_version"] != 1
            or started["body"]["run_key"] != run_key or started["body"]["request"] != body.get("request")):
        raise ValueError("Execution start and completion request differ")
    if not started["seq"] < completion["seq"] or not _time(started["recorded_at"], "Execution start") <= _time(completion["recorded_at"], "Execution completion") <= now:
        raise ValueError("Execution completion must follow its start and be available now")
    if completion["kind"] == "graph_transform_completed":
        parent_ids = [body["request"]["parent_manifest"]["id"]]
        outputs = {"output": {"model": body["output_model"], "model_hash": body["output_model_hash"]}}
    else:
        refs = body["request"]["parents"]
        if type(refs) is not list or not 1 <= len(refs) <= graph_views.MAX_PARENTS:
            raise ValueError("Execution requires 1–16 parents")
        parent_ids = [ref["manifest"]["id"] for ref in refs]
        outputs = body["outputs"]
    for parent_id in parent_ids:
        _identifier(parent_id, "Parent manifest ID")
    if parent_ids != _ids(parent_ids, "parent manifest IDs", maximum=graph_views.MAX_PARENTS):
        raise ValueError("Execution parent IDs must be normalized")
    if type(outputs) is not dict or not 1 <= len(outputs) <= graph_views.MAX_VIEWS:
        raise ValueError("Execution requires 1–64 output views")
    total_bytes = 0
    for name, output in outputs.items():
        _text(name, "View name")
        if len(name.encode("utf-8")) > MAX_VIEW_NAME_BYTES:
            raise ValueError("View name exceeds 128 UTF-8 bytes")
        _keys(output, {"model", "model_hash"}, "execution output")
        raw = canonical(output["model"]).encode("utf-8")
        if len(raw) > transforms.MAX_BYTES or digest(raw) != output["model_hash"]:
            raise ValueError("Execution output size or hash mismatch")
        total_bytes += len(raw)
    if total_bytes > graph_views.MAX_TOTAL_MODEL_BYTES:
        raise ValueError("Combined execution outputs exceed 2 MB")
    return completion, started, parent_ids, outputs


def _derivation(recipe_id, parents, view):
    return {"schema_version": 1, "recipe_id": recipe_id,
            "parent_method_ids": sorted(parent["body"]["method_id"] for parent in parents), "output_view": view}


def _method(derivation):
    return "graph-derived-v1:" + digest(canonical(derivation).encode("utf-8"))


def _output_ids(run_key, view):
    suffix = digest(view.encode("utf-8"))
    return (f"graph-materialization:{run_key}:representation:{suffix}",
            f"graph-materialization:{run_key}:manifest:{suffix}")


def _bindings(ledger, completion_id, now, *, verify_bytes):
    completion, started, parent_ids, outputs = _execution(ledger, completion_id, now)
    body = completion["body"]
    parents = []
    for parent_id in parent_ids:
        raw_parent = _get(ledger, parent_id, "representation_manifest")
        _bounded_size(raw_parent["body"]["descriptor"], MAX_DESCRIPTOR_BYTES, "Parent method descriptor")
        for field in ("representation_id", "snapshot_id"):
            _identifier(raw_parent["body"][field], field)
        _keys(raw_parent["body"]["artifacts"], manifests.ARTIFACT_ROLES, "parent manifest artifact roles")
        for field, limit in (("evidence", 1000), ("cost_receipts", 100)):
            if type(raw_parent["body"][field]) is not list or len(raw_parent["body"][field]) > limit:
                raise ValueError(f"Parent manifest {field} must be a bounded array")
        refs = list(raw_parent["body"]["artifacts"].values()) + raw_parent["body"]["evidence"] + raw_parent["body"]["cost_receipts"]
        for reference in refs:
            _keys(reference, {"observation_id", "event_hash", "content_hash"}, "parent observation reference")
            _identifier(reference["observation_id"], "Observation ID")
            _observation_body(ledger, reference["observation_id"], "Parent observation")
        cost = manifests._cost(raw_parent["body"]["construction_cost"])
        if cost["receipt_ids"] != [ref["observation_id"] for ref in raw_parent["body"]["cost_receipts"]]:
            raise ValueError("Parent cost receipt references do not match declared IDs")
        parents.append(_checked_manifest(ledger, parent_id, now, verify_bytes=verify_bytes))
    for parent in parents:
        if parent["seq"] >= started["seq"] or _time(parent["recorded_at"], "Parent manifest") > _time(started["recorded_at"], "Execution start"):
            raise ValueError("Every parent manifest must precede execution")
    common = graph_views._semantics(parents[0])
    if any(canonical(graph_views._semantics(parent)) != canonical(common) for parent in parents[1:]):
        raise ValueError("Execution parents must share snapshot and declared semantics")
    if common["encoding"] != "directed-graph" or common["schema_id"] != transforms.OUTPUT_SCHEMA:
        raise ValueError("Unsupported execution graph schema")
    evidence = set().union(*({ref["observation_id"] for ref in parent["body"]["evidence"]} for parent in parents))
    for output in outputs.values():
        transforms._graph(output["model"], evidence)
    parent_refs = [{"manifest_id": parent["id"], "manifest_hash": parent["hash"],
        "representation_id": parent["body"]["representation_id"], "representation_hash": parent["body"]["representation_hash"],
        "method_id": parent["body"]["method_id"], "snapshot_id": parent["body"]["snapshot_id"],
        "snapshot_hash": parent["body"]["snapshot_hash"]} for parent in parents]
    fields = ("losses", "source_to_output", "deduplications") if completion["kind"] == "graph_views_completed" else ("losses", "source_to_output")
    links = {field: {"completion_id": completion_id, "field": field, "sha256": digest(canonical(body[field]).encode("utf-8"))}
             for field in fields}
    execution = {"completion_id": completion_id, "completion_hash": completion["hash"], "completion_kind": completion["kind"],
        "started_id": started["id"], "started_hash": started["hash"], "recipe_id": body["recipe_id"],
        "recipe_descriptor": body["recipe_descriptor"], "output_schema": body["output_schema"]}
    return {"execution": execution, "parents": parent_refs,
            "derivations": {view: _derivation(body["recipe_id"], parents, view) for view in sorted(outputs)}, "links": links}, parents, outputs


def _prepare(ledger, completion_id, now):
    sources = _runtime_sources()
    completion, _, parent_ids, _ = _execution(ledger, completion_id, now)
    body = completion["body"]
    producer = transforms if completion["kind"] == "graph_transform_completed" else graph_views
    parent_argument = parent_ids[0] if producer is transforms else parent_ids
    recipe_id = body["request"]["recipe"]["observation_id"]
    _identifier(recipe_id, "Recipe observation ID")
    _observation_body(ledger, recipe_id, "Recipe observation")
    request = producer._request_metadata(ledger, parent_argument, recipe_id)
    if canonical(request["implementation"]) != canonical(body["request"]["implementation"]):
        raise ValueError("Execution contract differs from current verified implementation; execute a fresh eligible snapshot")
    if canonical(request) != canonical(body["request"]):
        raise ValueError("Execution request no longer matches its parent, recipe or snapshot bindings")
    bindings, parents, outputs = _bindings(ledger, completion_id, now, verify_bytes=False)
    _recipe_observation_shapes(ledger, recipe_id, parents[0], producer, _time(completion["recorded_at"], "Execution completion"))
    prepared = producer._prepare(ledger, parent_argument, recipe_id, _time(completion["recorded_at"], "Execution completion"))
    _keys(body, set(prepared) | {"schema_version", "run_key", "request", "result", "resources", "scope"}, "execution completion")
    if canonical({key: body[key] for key in prepared}) != canonical(prepared):
        raise ValueError("Execution output, losses or ancestry do not match fixed recomputation")
    if canonical(body["resources"]) != canonical({"model_calls": 0, "external_spend": 0}):
        raise ValueError("Unexpected fixed execution resources")
    bindings, parents, outputs = _bindings(ledger, completion_id, now, verify_bytes=True)
    descriptor = parents[0]["body"]["descriptor"]
    artifacts = {"construction": prepared["inputs"]["implementation"]["observation_id"],
                 "config": prepared["inputs"]["config"]["observation_id"],
                 **{role: parents[0]["body"]["artifacts"][role]["observation_id"] for role in ("ontology", "predictor")}}
    plans = {}
    output_bytes = 0
    evidence_refs = {ref["observation_id"]: ref for parent in parents for ref in parent["body"]["evidence"]}
    for view in sorted(outputs):
        output = outputs[view]
        plans[view] = {"snapshot_id": parents[0]["body"]["snapshot_id"], "model": deepcopy(output["model"]),
            "model_hash": output["model_hash"], "observer": descriptor["observer"], "method": _method(bindings["derivations"][view]),
            "parent": parents[0]["body"]["representation_id"] if len(parents) == 1 else None,
            "manifest_arguments": {"encoding": descriptor["encoding"], "schema_id": descriptor["schema_id"],
                "artifacts": artifacts, "task": descriptor["task"], "horizon_seconds": descriptor["horizon_seconds"],
                "units": descriptor["units"], "evidence_ids": sorted(_model_evidence(output["model"])), "construction_cost": None}}
        for observation_id in artifacts.values():
            _identifier(observation_id, "Execution artifact observation ID")
        # Overestimate every generated representation/manifest before writes. IDs
        # use their allowed upper bound, and padding covers fixed hashes/fields.
        # This includes repeated semantics and evidence refs across all views.
        template = {"representation": {key: plans[view][key] for key in ("snapshot_id", "model", "observer", "method", "parent")},
            "manifest": {"descriptor": {**descriptor, "construction_method": plans[view]["method"]},
                "artifacts": prepared["inputs"], "evidence": [evidence_refs[oid] for oid in plans[view]["manifest_arguments"]["evidence_ids"]],
                "representation_id": "x" * MAX_ID_BYTES, "snapshot_id": plans[view]["snapshot_id"],
                "cutoff": parents[0]["body"]["cutoff"], "observer": descriptor["observer"], "fixed_field_allowance": "x" * 2048}}
        output_bytes += _bounded_size(template, MAX_OUTPUT_RECORD_BYTES - output_bytes, "Materialized output records")
    return {**bindings, "plans": plans, "materializer": {"source_sha256": digest(sources[__name__]),
        "dependencies": {name: digest(sources[name]) for name in DEPENDENCY_NAMES}}}


def _checked_outputs(ledger, body, now, *, verify_bytes):
    expected, parents, source_outputs = _bindings(ledger, body["request"]["completion"]["id"], now, verify_bytes=verify_bytes)
    for field in ("execution", "parents", "derivations", "links"):
        if canonical(body[field]) != canonical(expected[field]):
            raise ValueError(f"Materialization {field} binding mismatch")
    if type(body["outputs"]) is not dict or set(body["outputs"]) != set(source_outputs):
        raise ValueError("Materialization must contain the complete execution output set")
    representations, result_manifests = {}, {}
    source = _get(ledger, expected["execution"]["completion_id"])
    common = parents[0]["body"]["descriptor"]
    for view, output in body["outputs"].items():
        _keys(output, {"representation_id", "representation_hash", "manifest_id", "manifest_hash", "model_hash", "method_id", "derivation_method"}, "materialized output")
        rid, mid = _output_ids(body["run_key"], view)
        if output["representation_id"] != rid or output["manifest_id"] != mid:
            raise ValueError("Materialization output IDs do not match the run and view")
        representation = _get(ledger, rid, "representation")
        manifest = _checked_manifest(ledger, mid, now, verify_bytes=verify_bytes)
        rep, mb = representation["body"], manifest["body"]
        if not source["seq"] < representation["seq"] < manifest["seq"]:
            raise ValueError("Materialized records must follow their source execution")
        expected_method = _method(expected["derivations"][view])
        if (representation["hash"] != output["representation_hash"] or manifest["hash"] != output["manifest_hash"]
                or mb["representation_id"] != rid or mb["model_hash"] != source_outputs[view]["model_hash"]
                or output["model_hash"] != mb["model_hash"] or output["method_id"] != mb["method_id"]
                or output["derivation_method"] != expected_method or rep["method"] != expected_method
                or canonical(rep["model"]) != canonical(source_outputs[view]["model"])):
            raise ValueError("Materialization output, method or hash binding mismatch")
        if rep["parent"] != (parents[0]["body"]["representation_id"] if len(parents) == 1 else None):
            raise ValueError("Materialization single-parent field does not match lineage")
        for key in ("encoding", "schema_id", "observer", "task", "horizon_seconds", "units"):
            if canonical(mb["descriptor"][key]) != canonical(common[key]):
                raise ValueError("Materialized manifest changed inherited semantics")
        expected_artifacts = {"construction": source["body"]["inputs"]["implementation"], "config": source["body"]["inputs"]["config"],
                              **{role: parents[0]["body"]["artifacts"][role] for role in ("ontology", "predictor")}}
        if canonical(mb["artifacts"]) != canonical(expected_artifacts) or mb["snapshot_id"] != parents[0]["body"]["snapshot_id"]:
            raise ValueError("Materialized manifest changed execution artifacts or snapshot")
        if mb["construction_cost"] != manifests._cost(None):
            raise ValueError("Materialization must preserve unknown construction cost")
        representations[view], result_manifests[view] = representation, manifest
    return representations, result_manifests


def get_materialized_outputs(ledger, terminal_id, *, verify_bytes=True):
    """Verify a committed bundle; byte checking can be disabled for historical metadata.

    Lookup does not re-execute a historical recipe or require its old dependency
    bytes to equal current code. Disabled byte checks do not certify availability.
    """
    if type(verify_bytes) is not bool:
        raise ValueError("verify_bytes must be boolean")
    with _read_transaction(ledger):
        receipt = _get(ledger, terminal_id, "graph_materialization_completed")
        body = receipt["body"]
        _keys(body, {"schema_version", "run_key", "request", "result", "execution", "parents", "derivations", "links",
                     "outputs", "materializer", "resources", "scope"}, "materialization completion")
        key = _run_key(body["run_key"])
        if (type(body["schema_version"]) is not int or body["schema_version"] != 1 or body["result"] != "completed"
                or terminal_id != f"graph-materialization:{key}:terminal"):
            raise ValueError("Invalid materialization completion")
        now = _time(ledger.clock(), "Ledger clock")
        started = _get(ledger, f"graph-materialization:{key}:started", "graph_materialization_started")
        if (started["body"].get("request") != body["request"] or body["request"] != _request_metadata(ledger, body["request"]["completion"]["id"])
                or not started["seq"] < receipt["seq"] or not _time(started["recorded_at"], "Materialization start") <= _time(receipt["recorded_at"], "Materialization completion") <= now):
            raise ValueError("Materialization receipt does not match its started request")
        representations, result_manifests = _checked_outputs(ledger, body, now, verify_bytes=verify_bytes)
        if any(not started["seq"] < representation["seq"] < result_manifests[view]["seq"] < receipt["seq"]
               or representation["recorded_at"] != receipt["recorded_at"] or result_manifests[view]["recorded_at"] != receipt["recorded_at"]
               for view, representation in representations.items()):
            raise ValueError("Materialized output set does not share its completion transaction ordering/time")
        return {"receipt": receipt, "representations": representations, "manifests": result_manifests}


def materialize_graph_outputs(ledger, completion_id, *, run_key):
    """Claim one output set, then atomically append representations/manifests/receipt."""
    if sys._getframe().f_code is not materialize_graph_outputs.__code__:
        raise ValueError("Stale materialization callable; use a fresh reviewed process")
    if type(ledger) is not _LEDGER_CLASS or _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class")
    if ledger.db.in_transaction:
        raise ValueError("Materialization requires a standalone ledger transaction")
    _identifier(completion_id, "Completion ID")
    _run_key(run_key)
    started_id, terminal_id = f"graph-materialization:{run_key}:started", f"graph-materialization:{run_key}:terminal"
    with _read_transaction(ledger):
        request = _request_metadata(ledger, completion_id)
        start, terminal = transforms._optional(ledger, started_id), transforms._optional(ledger, terminal_id)
        if start is not None and (start["kind"] != "graph_materialization_started" or start["body"].get("request") != request):
            raise ValueError("Run key already has a different request")
        if terminal is not None:
            if start is None or terminal["kind"] not in TERMINALS or terminal["body"].get("request") != request:
                raise ValueError("Run key has an invalid or different terminal request")
            if terminal["kind"] == "graph_materialization_completed":
                return get_materialized_outputs(ledger, terminal_id, verify_bytes=False)["receipt"]
            return terminal
        if start is not None:
            raise ValueError("Incomplete materialization run requires diagnosis; do not blindly replay")

    def validate_claim(_):
        if transforms._optional(ledger, terminal_id) is not None or _request_metadata(ledger, completion_id) != request:
            raise ValueError("Materialization request changed before claim")

    ledger.append("graph_materialization_started", {"schema_version": 1, "run_key": run_key, "request": request},
                  started_id, validate=validate_claim, exclusive=True)

    def validate_terminal(_):
        claimed = _get(ledger, started_id, "graph_materialization_started")
        if claimed["body"]["request"] != request or transforms._optional(ledger, terminal_id) is not None:
            raise ValueError("Materialization terminal does not match its unfinished claim")

    try:
        with ledger.atomic_write() as recorded_at:
            validate_terminal(recorded_at)
            if _request_metadata(ledger, completion_id) != request:
                raise ValueError("Materialization execution changed before group write")
            now = _time(recorded_at, "Materialization recorded_at")
            prepared = _prepare(ledger, completion_id, now)
            for view in prepared["plans"]:
                if any(transforms._optional(ledger, event_id) is not None for event_id in _output_ids(run_key, view)):
                    raise ValueError("Materialization output IDs already exist without a completed bundle")
            outputs = {}
            for view, plan in prepared["plans"].items():
                rid, mid = _output_ids(run_key, view)
                representation = ledger.representation(plan["snapshot_id"], plan["model"], observer=plan["observer"],
                    method=plan["method"], parent=plan["parent"], event_id=rid)
                manifest = manifests.register_manifest(ledger, rid, event_id=mid, **plan["manifest_arguments"])
                outputs[view] = {"representation_id": rid, "representation_hash": representation["hash"], "manifest_id": mid,
                    "manifest_hash": manifest["hash"], "model_hash": plan["model_hash"], "method_id": manifest["body"]["method_id"],
                    "derivation_method": plan["method"]}
            body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "completed",
                **{key: value for key, value in prepared.items() if key != "plans"}, "outputs": outputs,
                "resources": {"model_calls": 0, "external_spend": 0},
                "scope": "Atomic materialization of current fixed graph execution; construction cost unknown. No forecast, semantic truth or external witness claim."}
            if len(canonical(body).encode("utf-8")) > MAX_RECORD_BYTES:
                raise ValueError("Materialization completion exceeds 10 MB")

            def validate_completion(stamp):
                validate_terminal(stamp)
                if _request_metadata(ledger, completion_id) != request or canonical(_prepare(ledger, completion_id, _time(stamp, "Completion recorded_at"))) != canonical(prepared):
                    raise ValueError("Materialization inputs changed before completion")
                _checked_outputs(ledger, body, _time(stamp, "Completion recorded_at"), verify_bytes=True)

            result = ledger.append("graph_materialization_completed", body, terminal_id, validate=validate_completion, exclusive=True)
        return result
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as error:
        body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "rejected",
                "error": {"type": type(error).__name__, "message": transforms._diagnostic(error)}}
        return ledger.append("graph_materialization_rejected", body, terminal_id, validate=validate_terminal, exclusive=True)


_FUNCTION_CODES = tuple((name, value, value.__code__) for name, value in list(globals().items())
                        if callable(value) and getattr(value, "__module__", None) == __name__ and hasattr(value, "__code__"))
