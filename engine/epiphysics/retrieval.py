"""One bounded retrieval runner with fixed raw and static HTML indexing recipes.

Source-window validation and scoring use neutral contracts. The candidate indexes
only selected eligible inputs; its derived text never replaces raw citations.
Retained implementation bytes are evidence, never executable input.
"""
from __future__ import annotations

from pathlib import Path
import re
import sqlite3
import sys
import time
import unicodedata

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, retrieval_contracts as contracts, retrieval_indexing as indexing, store
from .store import canonical, digest
from .assertions import _read_transaction, _time
from .manifests import _keys

IMPLEMENTATION_DEPENDENCIES = tuple((m.__name__, m.IMPLEMENTATION_CODE)
    for m in (store, assertions, manifests, contracts, indexing))
_LEDGER_CLASS = store.Ledger
_MODULES = (store, assertions, manifests, contracts, indexing, sys.modules[__name__])
_IMPLEMENTATIONS = tuple((m, Path(m.__file__), m.IMPLEMENTATION_SOURCE,
    m.IMPLEMENTATION_CODE, m.IMPLEMENTATION_DEPENDENCIES) for m in _MODULES)

# Public and previously used raw-input helpers remain aliases to the single
# neutral implementation. Historical artifact roles keep their original names.
DEPENDENCY_NAMES = contracts.DEPENDENCY_NAMES
DEFAULT_CONFIG = contracts.DEFAULT_CONFIG
MAX_BYTES = contracts.MAX_BYTES
MAX_TOTAL_BYTES = contracts.MAX_TOTAL_BYTES
MAX_SOURCES = contracts.MAX_SOURCES
MAX_PASSAGES = contracts.MAX_PASSAGES
SPAN_FIELDS = contracts.SPAN_FIELDS
REF_FIELDS = contracts.REF_FIELDS
ELAPSED_SCOPE = contracts.ELAPSED_SCOPE
SCOPE = contracts.SCOPE
RAW_RECIPE = contracts.RAW_RECIPE
HTML_RECIPE = contracts.HTML_RECIPE

_ALIAS_NAMES = ("_bounded_size", "_identifier", "_config", "_ids", "_terms", "_queries",
    "_get", "_optional", "_retained", "_source_inputs", "_passages", "_manifest",
    "_build_corpus", "_checked_corpus", "_span_key", "_span_shape", "_validate_results",
    "_checked_runtime", "_checked_artifacts", "_checked_terminal", "_indexing_recipe")
for _name in _ALIAS_NAMES:
    globals()[_name] = getattr(contracts, _name)
_CONTRACT_ALIASES = tuple((name, globals()[name]) for name in _ALIAS_NAMES)


def _standalone(ledger):
    if type(ledger) is not _LEDGER_CLASS or _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class")
    if ledger.db.in_transaction or ledger._atomic_time is not None or ledger._append_active:
        raise ValueError("Retrieval writes require a standalone transaction")


def freeze_retrieval_corpus(ledger, snapshot_id, observation_ids, *, config=None, event_id=None):
    """Freeze selected eligible bytes, config, and exact passage manifest."""
    _standalone(ledger)
    _identifier(snapshot_id, "Snapshot ID")
    if event_id is not None:
        _identifier(event_id, "Corpus event ID")
    selected, config = _ids(observation_ids), _config(config)
    with _read_transaction(ledger):
        body, _ = _build_corpus(ledger, snapshot_id, selected, config, _time(ledger.clock(), "Ledger clock"))

    def validate(recorded_at):
        checked, _ = _build_corpus(ledger, snapshot_id, selected, config, _time(recorded_at, "Corpus recorded_at"))
        if checked != body:
            raise ValueError("Corpus bindings changed before append")

    return ledger.append("retrieval_corpus", body, event_id, validate=validate)


def _check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("Retrieval cooperative execution budget exceeded")


def _search(corpus_passages, queries, config, deadline):
    config, queries = _config(config), _queries(queries)
    if type(corpus_passages) is not list or len(corpus_passages) > MAX_PASSAGES:
        raise ValueError("Candidate requires at most 4096 passages")
    sizes, previous = {}, None
    for row in corpus_passages:
        _check_deadline(deadline)
        _keys(row, SPAN_FIELDS | {"text"}, "candidate passage")
        _identifier(row["observation_id"], "Passage observation ID")
        if type(row["text"]) is not str or len(row["text"]) > 2048:
            raise ValueError("Passage text exceeds its byte window")
        raw = row["text"].encode("utf-8")
        _span_shape(row, {row["observation_id"]: MAX_BYTES})
        if len(raw) != row["end"] - row["start"] or digest(raw) != row["sha256"]:
            raise ValueError("Candidate passage text/span hash mismatch")
        sizes[row["observation_id"]] = max(sizes.get(row["observation_id"], 0), row["end"])
        if len(sizes) > MAX_SOURCES or sum(sizes.values()) > MAX_TOTAL_BYTES:
            raise ValueError("Candidate source bounds exceeded")
        key = _span_key(row)
        if previous is not None and key <= previous:
            raise ValueError("Candidate passages require distinct canonical ordering")
        previous = key
    rows = [{**{key: row[key] for key in SPAN_FIELDS},
             "indexed_text": row["text"], "indexed_text_sha256": row["sha256"],
             "indexed_bytes": row["end"] - row["start"],
             "mapping": [{"kind": "copy", "start": 0, "end": row["end"] - row["start"],
                          "source": {key: row[key] for key in ("start", "end", "sha256")}}]}
            for row in corpus_passages]
    return indexing.lexical_search(rows, queries, config, deadline=deadline)

def lexical_search(corpus_passages, queries, config):
    """Pure fixed candidate: no ledger, gold, network, model, or callbacks.

    Passages are ordered manifest rows plus the exact decoded source-slice `text`.
    A fresh disposable FTS5 index is created on every call.
    """
    if sys._getframe().f_code is not lexical_search.__code__:
        raise ValueError("Stale lexical candidate; use a fresh reviewed process")
    config = _config(config)
    return _search(corpus_passages, queries, config, time.monotonic() + config["execution_seconds"])


def _runtime_sources():
    codes = {m.__name__: code for m, _, _, code, _ in _IMPLEMENTATIONS}
    for name, function, code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not code:
            raise ValueError(f"Fixed retrieval callable changed: {name}; use a fresh reviewed process")
    for name, function in _CONTRACT_ALIASES:
        if globals().get(name) is not function or getattr(contracts, name) is not function:
            raise ValueError(f"Fixed retrieval contract alias changed: {name}")
    for name, owner, function, code in _IMPORTED_ALIASES:
        if (globals().get(name) is not function or getattr(owner, name) is not function
                or function.__code__ is not code):
            raise ValueError(f"Fixed retrieval dependency alias changed: {name}")
    for name, function, code in _LEDGER_METHODS:
        current = vars(_LEDGER_CLASS).get(name)
        if isinstance(current, (staticmethod, classmethod)):
            current = current.__func__
        if current is not function or getattr(current, "__code__", None) is not code:
            raise ValueError(f"Fixed retrieval ledger method changed: {name}")
    for owner, name, function, code in _RUNTIME_HELPERS:
        if getattr(owner, name) is not function or function.__code__ is not code:
            raise ValueError(f"Fixed retrieval runtime helper changed: {owner.__name__}.{name}")
    for module, path, source, code, dependencies in _IMPLEMENTATIONS:
        if module.IMPLEMENTATION_CODE is not code or module.IMPLEMENTATION_SOURCE != source:
            raise ValueError(f"Retrieval implementation reloaded: {module.__name__}")
        if len(source) > MAX_BYTES or path.is_symlink() or not path.is_file() or path.stat().st_size != len(source):
            raise ValueError(f"Retrieval implementation source changed: {module.__name__}")
        with path.open("rb") as stream:
            if stream.read(len(source) + 1) != source:
                raise ValueError(f"Retrieval implementation source changed: {module.__name__}")
        if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
            raise ValueError(f"Executing code does not match retained source: {module.__name__}")
        for name, dependency_code in dependencies:
            if codes.get(name) is not dependency_code:
                raise ValueError(f"Retrieval dependency reloaded: {module.__name__} -> {name}")
    return _merge_runtime_sources(
        {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS},
        contracts._runtime_sources(), indexing.runtime_sources())


def _merge_runtime_sources(*closures):
    """Refuse conflicting shared dependencies before any value can overwrite one."""
    sources = {}
    for closure in closures:
        for name, raw in closure.items():
            if name in sources and sources[name] != raw:
                raise ValueError(f"Runtime source closure conflict: {name}")
            sources[name] = raw
    return sources


def _runtime():
    connection = sqlite3.connect(":memory:")
    try:
        return {"python_version": sys.version, "python_implementation": sys.implementation.name,
            "python_cache_tag": sys.implementation.cache_tag, "python_optimize": sys.flags.optimize,
            "unicode_version": unicodedata.unidata_version, "sqlite_version": sqlite3.sqlite_version,
            "sqlite_source_id": connection.execute("SELECT sqlite_source_id()").fetchone()[0],
            "sqlite_compile_options": sorted(row[0] for row in connection.execute("PRAGMA compile_options"))}
    finally:
        connection.close()



def _request(ledger, corpus_id, queries, indexing_recipe):
    corpus = _get(ledger, corpus_id, "retrieval_corpus")
    return {"corpus_id": corpus["id"], "corpus_hash": corpus["hash"], "queries": queries,
            "query_hash": digest(canonical(queries).encode()), "indexing_recipe": indexing_recipe}


def _projection_inputs(ledger, corpus, now):
    body = corpus["body"]
    _, refs, raw = _source_inputs(ledger, body["snapshot_id"],
        [ref["observation_id"] for ref in body["sources"]], now, verify_bytes=True)
    if refs != body["sources"]:
        raise ValueError("Projection source binding changed")
    return {oid: {"raw": content, "media_type": _get(ledger, oid, "observation")["body"]["media_type"]}
            for oid, content in raw.items()}


def _retain_artifacts(ledger, run_key, config, queries, sources, recipe, projection_raw):
    if len(projection_raw) > contracts.MAX_PROJECTION_BYTES:
        raise ValueError("Projection exceeds retained byte bound")
    def capture(role, raw):
        if len(raw) > MAX_BYTES:
            raise ValueError("Execution metadata exceeds 1 MB")
        event = ledger.capture(f"retrieval-input:{run_key}:{role}", raw,
            media_type="text/x-python" if role.startswith("code:") else "application/json",
            event_id=f"retrieval:{run_key}:input:{role}")
        return {"observation_id": event["id"], "event_hash": event["hash"],
                "content_hash": event["body"]["content_hash"], "size": len(raw)}
    chunks = [projection_raw[start:start + MAX_BYTES] for start in range(0, len(projection_raw), MAX_BYTES)]
    if not 1 <= len(chunks) <= 16:
        raise ValueError("Projection requires one to sixteen bounded chunks")
    return {"config": capture("config", canonical(config).encode()),
        "queries": capture("queries", canonical(queries).encode()),
        "implementation": capture("code:epiphysics.retrieval", sources[__name__]),
        "dependencies": {name: capture("code:" + name, sources[name]) for name in contracts.DEPENDENCY_NAMES_V2},
        "stdlib": {name: capture(("data:" if name == "html.entities.html5" else "code:") + name, sources[name])
                   for name in contracts.STDLIB_NAMES},
        "recipe": capture("recipe", canonical({"schema_version": 1, "indexing_recipe": recipe}).encode()),
        "projection": {"schema_version": 1, "sha256": digest(projection_raw), "size": len(projection_raw),
                       "chunks": [capture(f"projection:{index:04d}", raw) for index, raw in enumerate(chunks)]}}


def get_retrieval_run(ledger, terminal_id, *, verify_bytes=True):
    """Read a historical v1/v2 receipt without executing retained candidate code."""
    return contracts.get_retrieval_run(ledger, terminal_id, verify_bytes=verify_bytes)


def run_lexical_retrieval(ledger, corpus_id, queries, *, run_key, indexing_recipe=RAW_RECIPE):
    """Execute one of two fixed recipes; preserve exact historical v1/v2 replay."""
    if sys._getframe().f_code is not run_lexical_retrieval.__code__:
        raise ValueError("Stale retrieval runner; use a fresh reviewed process")
    _standalone(ledger)
    _identifier(corpus_id, "Corpus ID")
    recipe = _indexing_recipe(indexing_recipe)
    if type(run_key) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key) is None:
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    queries = _queries(queries)
    started_id, terminal_id = f"retrieval:{run_key}:started", f"retrieval:{run_key}:terminal"
    with _read_transaction(ledger):
        request = _request(ledger, corpus_id, queries, recipe)
        _bounded_size(request, MAX_BYTES, "Retrieval request")
        start, terminal = _optional(ledger, started_id), _optional(ledger, terminal_id)
        if start is not None:
            if start["kind"] != "retrieval_started" or type(start["body"]) is not dict:
                raise ValueError("Run key already has a different request")
            version = start["body"].get("schema_version")
            if type(version) is not int or version not in (1, 2):
                raise ValueError("Unsupported historical retrieval claim")
            if version == 1:
                if recipe != RAW_RECIPE:
                    raise ValueError("Historical raw run cannot replay with a different recipe")
                request = {key: value for key, value in request.items() if key != "indexing_recipe"}
            if start["body"].get("request") != request:
                raise ValueError("Run key already has a different request")
        if terminal is not None:
            if start is None:
                raise ValueError("Terminal lacks retrieval claim")
            return _checked_terminal(ledger, terminal, request, verify_bytes=False)
        if start is not None:
            raise ValueError("Incomplete retrieval run requires diagnosis; do not blindly replay")

    def validate_claim(_):
        if _optional(ledger, terminal_id) is not None or _request(ledger, corpus_id, queries, recipe) != request:
            raise ValueError("Retrieval request changed before claim")

    claim = {"schema_version": 2, "run_key": run_key, "request": request}
    ledger.append("retrieval_started", claim, started_id, validate=validate_claim, exclusive=True)

    def validate_terminal(_):
        if _get(ledger, started_id, "retrieval_started")["body"] != claim or _optional(ledger, terminal_id) is not None:
            raise ValueError("Retrieval terminal does not match its unfinished claim")

    begun = time.monotonic()
    try:
        sources = _runtime_sources()
        with _read_transaction(ledger):
            now = _time(ledger.clock(), "Ledger clock")
            corpus, _ = _checked_corpus(ledger, corpus_id, now)
            inputs = _projection_inputs(ledger, corpus, now)
        config = corpus["body"]["config"]
        deadline = begun + config["execution_seconds"]
        _check_deadline(deadline)
        runtime = _runtime()
        projection = indexing.project_index(inputs, corpus["body"]["passages"], recipe, deadline=deadline)
        contracts.validate_projection(inputs, corpus["body"]["passages"], projection, deadline=deadline)
        projection_raw = canonical(projection).encode()
        artifacts = _retain_artifacts(ledger, run_key, config, queries, sources, recipe, projection_raw)
        results = indexing.lexical_search(projection["rows"], queries, config, deadline=deadline)
        _validate_results(results, queries, corpus["body"])
        body = {"schema_version": 2, "run_key": run_key, "request": request, "result": "completed",
            "corpus_id": corpus_id, "corpus_hash": corpus["hash"], "config_hash": corpus["body"]["config_hash"],
            "query_hash": request["query_hash"], "indexing_recipe": recipe, "projection_hash": digest(projection_raw),
            "artifacts": artifacts, "runtime": runtime, "runtime_hash": digest(canonical(runtime).encode()),
            "implementation_hash": digest(sources[__name__]), "results": results,
            "results_hash": digest(canonical(results).encode()),
            "resources": {"elapsed_seconds": time.monotonic() - begun, "elapsed_scope": ELAPSED_SCOPE,
                "execution_budget_seconds": config["execution_seconds"], "input_bytes": corpus["body"]["source_bytes"],
                "passages": len(corpus["body"]["passages"]), "queries": len(queries),
                "output_bytes": len(canonical(results).encode()), "model_calls": 0, "external_spend": 0,
                "projection_bytes": len(projection_raw), "indexed_bytes": sum(row["indexed_bytes"] for row in projection["rows"]),
                "mapping_pieces": sum(len(row["mapping"]) for row in projection["rows"]),
                "empty_windows": sum(row["indexed_bytes"] == 0 for row in projection["rows"])}, "scope": SCOPE}
        _bounded_size(body, MAX_BYTES, "Retrieval terminal")
        expected_body = canonical(body)

        def validate_completion(recorded_at):
            validate_terminal(recorded_at)
            _check_deadline(deadline)
            if _request(ledger, corpus_id, queries, recipe) != request or _runtime_sources() != sources or _runtime() != runtime:
                raise ValueError("Retrieval inputs or runtime changed before completion")
            checked, _ = _checked_corpus(ledger, corpus_id, _time(recorded_at, "Completion recorded_at"))
            checked_inputs = _projection_inputs(ledger, checked, _time(recorded_at, "Completion recorded_at"))
            recomputed = indexing.project_index(checked_inputs, checked["body"]["passages"], recipe, deadline=deadline)
            contracts.validate_projection(checked_inputs, checked["body"]["passages"], recomputed, deadline=deadline)
            if checked != corpus or canonical(recomputed).encode() != projection_raw:
                raise ValueError("Retrieval inputs or recomputed projection changed before completion")
            if indexing.lexical_search(recomputed["rows"], queries, config, deadline=deadline) != results:
                raise ValueError("Recomputed retrieval results changed before completion")
            contracts._checked_artifacts_v2(ledger, body, corpus, _time(recorded_at, "Completion recorded_at"),
                ledger.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM events").fetchone()[0], verify_bytes=True)
            _validate_results(body["results"], queries, corpus["body"])
            if canonical(body) != expected_body:
                raise ValueError("Retrieval completion changed before append")
            _check_deadline(deadline)

        return ledger.append("retrieval_completed", body, terminal_id, validate=validate_completion, exclusive=True)
    except Exception as error:
        message = str(error).encode("utf-8", errors="backslashreplace")[:400].decode("utf-8", errors="ignore")
        body = {"schema_version": 2, "run_key": run_key, "request": request, "result": "rejected",
                "error": {"type": type(error).__name__, "message": message}}
        return ledger.append("retrieval_rejected", body, terminal_id, validate=validate_terminal, exclusive=True)


_FUNCTION_CODES = tuple((name, value, value.__code__) for name, value in list(globals().items())
    if callable(value) and getattr(value, "__module__", None) == __name__ and hasattr(value, "__code__"))
_IMPORTED_ALIASES = tuple((name, owner, globals()[name], globals()[name].__code__)
    for owner, names in ((store, ("canonical", "digest")),
                         (assertions, ("_read_transaction", "_time")), (manifests, ("_keys",)))
    for name in names)
_LEDGER_METHODS = tuple((name, function.__func__ if isinstance(function, (staticmethod, classmethod)) else function,
                        (function.__func__ if isinstance(function, (staticmethod, classmethod)) else function).__code__)
    for name, function in vars(_LEDGER_CLASS).items()
    if hasattr(function.__func__ if isinstance(function, (staticmethod, classmethod)) else function, "__code__"))
_RUNTIME_HELPERS = tuple((owner, name, getattr(owner, name), getattr(owner, name).__code__)
    for owner, names in ((contracts, ("_runtime_sources", "validate_projection", "_checked_artifacts_v2", "get_retrieval_run")),
                         (indexing, ("runtime_sources", "project_index", "lexical_search")))
    for name in names)
