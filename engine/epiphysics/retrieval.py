"""Bounded, retrospective lexical retrieval over explicitly selected evidence.

FTS5 indexes verbatim UTF-8 byte windows, never the whole ledger. Scores are
lower-is-better BM25 values, not confidence or evidence of answerability.
Retained code is hashed and inspected, never evaluated. Receipt lookup is not a
fresh execution or an independent witness of execution.
"""

from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import time
import unicodedata

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, store
from .store import canonical, digest
from .assertions import _event_integrity, _hash, _read_transaction, _snapshot, _time
from .manifests import _keys, _observation

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions, manifests)
)
_LEDGER_CLASS = store.Ledger
_MODULES = (store, assertions, manifests, sys.modules[__name__])
_IMPLEMENTATIONS = tuple((module, Path(module.__file__), module.IMPLEMENTATION_SOURCE,
    module.IMPLEMENTATION_CODE, module.IMPLEMENTATION_DEPENDENCIES) for module in _MODULES)
DEPENDENCY_NAMES = tuple(module.__name__ for module in (store, assertions, manifests))
MAX_BYTES = 1_000_000
MAX_TOTAL_BYTES = 4_000_000
MAX_SOURCES = 64
MAX_PASSAGES = 4096
MAX_QUERIES = 64
MAX_QUERY_BYTES = 2048
MAX_TERMS = 64
DEFAULT_CONFIG = {"schema_version": 1, "passaging": "verbatim-utf8-v1",
    "window_bytes": 2048, "overlap_bytes": 256,
    "tokenizer": "unicode61 remove_diacritics 2",
    "query_scanner": "unicode-alphanumeric-v1", "ranking": "fts5-bm25-v1",
    "top_k": 5, "execution_seconds": 30}
_FIXED_CONFIG = tuple((key, value) for key, value in DEFAULT_CONFIG.items()
                      if key not in ("top_k", "execution_seconds"))
CORPUS_FIELDS = {"schema_version", "snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
    "cutoff", "config", "config_hash", "sources", "sources_hash", "passages", "passages_hash",
    "source_bytes", "passage_count"}
REF_FIELDS = {"observation_id", "event_hash", "content_hash", "size"}
SPAN_FIELDS = {"observation_id", "start", "end", "sha256"}
REQUEST_FIELDS = {"corpus_id", "corpus_hash", "queries", "query_hash"}
RUN_FIELDS = {"schema_version", "run_key", "request", "result", "corpus_id", "corpus_hash",
    "config_hash", "query_hash", "artifacts", "runtime", "runtime_hash", "implementation_hash",
    "results", "results_hash", "resources", "scope"}
ELAPSED_SCOPE = "through initial search and validation; excludes locked revalidation and commit"
SCOPE = ("Retrospective development retrieval; execution artifacts postdate the source snapshot. "
         "Local cooperative limits, no process isolation or independent execution witness. "
         "Lexical matches are not answerability or calibrated confidence.")


def _bounded_size(value, limit, label):
    total = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    try:
        for chunk in encoder.iterencode(value):
            if len(chunk) > limit - total:
                raise ValueError(f"{label} exceeds its byte limit")
            total += len(chunk.encode("utf-8"))
            if total > limit:
                raise ValueError(f"{label} exceeds its byte limit")
    except (TypeError, UnicodeError, RecursionError) as error:
        raise ValueError(f"Invalid bounded JSON {label}") from error
    return total


def _identifier(value, label):
    if type(value) is not str or not value.strip() or len(value) > 512:
        raise ValueError(f"{label} must be a nonempty ID of at most 512 UTF-8 bytes")
    try:
        if len(value.encode("utf-8")) > 512 or "\x00" in value:
            raise ValueError(f"{label} exceeds 512 UTF-8 bytes or contains NUL")
    except UnicodeError as error:
        raise ValueError(f"{label} must be valid UTF-8") from error
    return value


def _config(config):
    value = dict(DEFAULT_CONFIG) if config is None else config
    _keys(value, DEFAULT_CONFIG, "retrieval config")
    for key, expected in _FIXED_CONFIG:
        if type(value[key]) is not type(expected) or value[key] != expected:
            raise ValueError(f"Unsupported retrieval config {key}")
    if type(value["top_k"]) is not int or not 1 <= value["top_k"] <= 20:
        raise ValueError("top_k must be an integer in [1,20]")
    if type(value["execution_seconds"]) not in (int, float) or not math.isfinite(value["execution_seconds"]) or not 0 < value["execution_seconds"] <= 30:
        raise ValueError("execution_seconds must be finite in (0,30]")
    return dict(value)


def _ids(value):
    if type(value) is not list or not 1 <= len(value) <= MAX_SOURCES:
        raise ValueError("Select 1–64 explicit observation IDs")
    for oid in value:
        _identifier(oid, "Observation ID")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate selected observation ID")
    return sorted(value, key=lambda oid: oid.encode("utf-8"))


def _terms(query):
    """Maximal Python Unicode isalnum runs; underscore and combining marks split.

    Preserve spelling and repetition; FTS5 performs its own fixed tokenization.
    Every run becomes a quoted literal OR operand, never caller-supplied syntax.
    """
    terms, start = [], None
    for index, char in enumerate(query + " "):
        if char.isalnum():
            if start is None:
                start = index
        elif start is not None:
            terms.append(query[start:index])
            if len(terms) > MAX_TERMS:
                raise ValueError("Query exceeds 64 compiled terms")
            start = None
    return terms


def _queries(value):
    if type(value) is not list or not 1 <= len(value) <= MAX_QUERIES:
        raise ValueError("Require 1–64 queries")
    seen = set()
    for row in value:
        _keys(row, {"query_id", "query"}, "query")
        _identifier(row["query_id"], "Query ID")
        if row["query_id"] in seen:
            raise ValueError("Duplicate query ID")
        seen.add(row["query_id"])
        query = row["query"]
        if type(query) is not str or len(query) > MAX_QUERY_BYTES:
            raise ValueError("Query must contain at most 2048 UTF-8 bytes")
        try:
            if len(query.encode("utf-8")) > MAX_QUERY_BYTES:
                raise ValueError("Query exceeds 2048 UTF-8 bytes")
        except UnicodeError as error:
            raise ValueError("Query must be valid UTF-8") from error
        _terms(query)
    _bounded_size(value, MAX_BYTES, "Query input")
    return deepcopy(value)


def _standalone(ledger):
    if type(ledger) is not _LEDGER_CLASS or _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class")
    if ledger.db.in_transaction or ledger._atomic_time is not None or ledger._append_active:
        raise ValueError("Retrieval writes require a standalone transaction")


def _get(ledger, event_id, kind=None):
    _identifier(event_id, "Event ID")
    row = ledger.db.execute("SELECT length(CAST(body AS BLOB)) AS size FROM events WHERE id=?", (event_id,)).fetchone()
    if row is not None and row["size"] > MAX_BYTES:
        raise ValueError("Retrieval input record exceeds 1 MB")
    event = ledger.get(event_id, kind)
    _event_integrity(event)
    return event


def _optional(ledger, event_id):
    return _get(ledger, event_id) if ledger.db.execute("SELECT 1 FROM events WHERE id=?", (event_id,)).fetchone() else None


def _retained(ledger, observation_id, now, *, snapshot=None, entries=None, verify_bytes=True):
    observation = _get(ledger, observation_id, "observation")
    body = observation["body"]
    if type(body) is not dict:
        raise ValueError("Observation body must be an object")
    if type(body.get("size")) is not int or not 0 <= body["size"] <= MAX_BYTES:
        raise ValueError("Observation declared size must be in [0,1000000]")
    ref = _observation(ledger, observation_id, now, snapshot=snapshot, entries=entries, verify_bytes=False)
    ref["size"] = body["size"]
    if not verify_bytes:
        return ref, None
    path = ledger.root / "blobs" / ref["content_hash"]
    if path.is_symlink() or not path.is_file():
        raise ValueError("Retained blob must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(body["size"] + 1)
    if len(raw) != body["size"] or digest(raw) != ref["content_hash"]:
        raise ValueError("Retained blob hash or size mismatch")
    return ref, raw


def _source_inputs(ledger, snapshot_id, observation_ids, now, *, verify_bytes):
    _get(ledger, snapshot_id, "snapshot")  # bound the manifest before its helper expands it
    snapshot, entries = _snapshot(ledger, snapshot_id, now)
    sources = [_retained(ledger, oid, now, snapshot=snapshot, entries=entries, verify_bytes=False)[0]
               for oid in observation_ids]
    if sum(ref["size"] for ref in sources) > MAX_TOTAL_BYTES:
        raise ValueError("Selected source bytes exceed 4 MB")
    raw_sources = {}
    if verify_bytes:
        for ref in sources:
            checked, raw = _retained(ledger, ref["observation_id"], now, snapshot=snapshot, entries=entries)
            if checked != ref:
                raise ValueError("Source binding changed before reading")
            raw.decode("utf-8", errors="strict")
            raw_sources[ref["observation_id"]] = raw
    return snapshot, sources, raw_sources


def _passages(raw_sources, config):
    """End=floor_UTF8(start+2048); next start=floor_UTF8(end-256).

    Floor means move backwards over continuation bytes to a codepoint boundary.
    End is capped at source length. Stop immediately at EOF; empty sources emit
    no passages. Thus nominal overlap can grow by at most three bytes.
    """
    rows = []
    for oid in sorted(raw_sources, key=lambda value: value.encode("utf-8")):
        raw = raw_sources[oid]
        start = 0
        while start < len(raw):
            end = min(start + config["window_bytes"], len(raw))
            while end < len(raw) and raw[end] & 0xC0 == 0x80:
                end -= 1
            chunk = raw[start:end]
            rows.append({"observation_id": oid, "start": start, "end": end,
                         "sha256": digest(chunk), "text": chunk.decode("utf-8")})
            if len(rows) > MAX_PASSAGES:
                raise ValueError("Corpus exceeds 4096 passages")
            if end == len(raw):
                break
            next_start = end - config["overlap_bytes"]
            while raw[next_start] & 0xC0 == 0x80:
                next_start -= 1
            if next_start <= start:
                raise ValueError("Passage starts must advance")
            start = next_start
    return rows


def _manifest(rows):
    return [{key: row[key] for key in ("observation_id", "start", "end", "sha256")} for row in rows]


def _build_corpus(ledger, snapshot_id, observation_ids, config, now):
    snapshot, sources, raw = _source_inputs(ledger, snapshot_id, observation_ids, now, verify_bytes=True)
    passages = _passages(raw, config)
    manifest = _manifest(passages)
    body = {"schema_version": 1, "snapshot_id": snapshot["id"], "snapshot_hash": snapshot["hash"],
        "snapshot_manifest_hash": snapshot["body"]["manifest_hash"], "cutoff": snapshot["body"]["cutoff"],
        "config": config, "config_hash": digest(canonical(config).encode()),
        "sources": sources, "sources_hash": digest(canonical(sources).encode()),
        "passages": manifest, "passages_hash": digest(canonical(manifest).encode()),
        "source_bytes": sum(ref["size"] for ref in sources), "passage_count": len(manifest)}
    _bounded_size(body, MAX_BYTES, "Corpus receipt")
    return body, passages


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


def _checked_corpus(ledger, corpus_id, now, *, verify_bytes=True):
    event = _get(ledger, corpus_id, "retrieval_corpus")
    body = event["body"]
    _keys(body, CORPUS_FIELDS, "corpus")
    if type(body["schema_version"]) is not int or body["schema_version"] != 1:
        raise ValueError("Corpus schema_version must be 1")
    if _time(event["recorded_at"], "Corpus recorded_at") > now:
        raise ValueError("Corpus is not yet available")
    config = _config(body["config"])
    if type(body["sources"]) is not list or not 1 <= len(body["sources"]) <= MAX_SOURCES:
        raise ValueError("Invalid corpus sources")
    for ref in body["sources"]:
        _keys(ref, REF_FIELDS, "source reference")
        if type(ref["size"]) is not int or not 0 <= ref["size"] <= MAX_BYTES:
            raise ValueError("Invalid source reference size")
    selected = _ids([ref["observation_id"] for ref in body["sources"]])
    snapshot, sources, _ = _source_inputs(ledger, body["snapshot_id"], selected,
        _time(event["recorded_at"], "Corpus recorded_at"), verify_bytes=False)
    if snapshot["seq"] >= event["seq"]:
        raise ValueError("Corpus must follow snapshot")
    expected = {"snapshot_hash": snapshot["hash"], "snapshot_manifest_hash": snapshot["body"]["manifest_hash"],
        "cutoff": snapshot["body"]["cutoff"], "sources": sources,
        "sources_hash": digest(canonical(sources).encode()), "config_hash": digest(canonical(config).encode()),
        "source_bytes": sum(ref["size"] for ref in sources)}
    if any(body[key] != value for key, value in expected.items()) or type(body["source_bytes"]) is not int:
        raise ValueError("Corpus source/config/snapshot binding mismatch")
    manifest = body["passages"]
    if type(manifest) is not list or len(manifest) > MAX_PASSAGES:
        raise ValueError("Invalid corpus passages")
    sizes = {ref["observation_id"]: ref["size"] for ref in sources}
    previous = None
    for row in manifest:
        _keys(row, SPAN_FIELDS, "passage")
        _span_shape(row, sizes)
        key = _span_key(row)
        if previous is not None and key <= previous:
            raise ValueError("Passages must have distinct canonical ordering")
        previous = key
    if type(body["passage_count"]) is not int or body["passage_count"] != len(manifest) or body["passages_hash"] != digest(canonical(manifest).encode()):
        raise ValueError("Passage manifest hash/count mismatch")
    if verify_bytes:
        rebuilt, passages = _build_corpus(ledger, body["snapshot_id"], selected, config,
            _time(event["recorded_at"], "Corpus recorded_at"))
        if rebuilt != body:
            raise ValueError("Corpus does not match retained source bytes")
        return event, passages
    return event, None


def _span_key(row):
    return (row["observation_id"].encode("utf-8"), row["start"], row["end"], row["sha256"])


def _span_shape(row, sizes):
    _identifier(row["observation_id"], "Passage observation ID")
    _hash(row["sha256"], "Passage SHA-256")
    if row["observation_id"] not in sizes or type(row["start"]) is not int or type(row["end"]) is not int or not 0 <= row["start"] < row["end"] <= sizes[row["observation_id"]] or row["end"] - row["start"] > 2048:
        raise ValueError("Passage must be a selected bounded half-open source span")


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
    results = []
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        connection.execute("CREATE VIRTUAL TABLE passages USING fts5(text, observation_id UNINDEXED, start UNINDEXED, end UNINDEXED, sha256 UNINDEXED, tokenize='unicode61 remove_diacritics 2')")
        for rowid, row in enumerate(corpus_passages, 1):
            _check_deadline(deadline)
            connection.execute("INSERT INTO passages(rowid,text,observation_id,start,end,sha256) VALUES(?,?,?,?,?,?)",
                (rowid, row["text"], row["observation_id"], row["start"], row["end"], row["sha256"]))
        for query in queries:
            _check_deadline(deadline)
            terms = _terms(query["query"])
            hits = []
            if terms:
                expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
                rows = connection.execute("SELECT observation_id,start,end,sha256,bm25(passages) AS score FROM passages WHERE passages MATCH ? ORDER BY score ASC,observation_id COLLATE BINARY ASC,start ASC,end ASC,sha256 ASC LIMIT ?",
                    (expression, config["top_k"]))
                for rank, row in enumerate(rows, 1):
                    if not math.isfinite(row["score"]):
                        raise ValueError("Nonfinite BM25 score")
                    hits.append({"rank": rank, **dict(row)})
            results.append({**query, "status": "matched" if hits else "empty",
                "reason": None if hits else ("no_query_terms" if not terms else "no_lexical_match"), "hits": hits})
        _check_deadline(deadline)
    except sqlite3.OperationalError as error:
        if time.monotonic() >= deadline:
            raise TimeoutError("Retrieval cooperative execution budget exceeded") from error
        raise
    finally:
        connection.close()
    _bounded_size(results, MAX_BYTES, "Retrieval results")
    return results


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
    codes = {module.__name__: code for module, _, _, code, _ in _IMPLEMENTATIONS}
    for name, function, code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not code:
            raise ValueError(f"Fixed retrieval callable changed: {name}; use a fresh reviewed process")
    for owner, name, function, code in _DEPENDENCY_FUNCTION_CODES:
        if getattr(owner, name, None) is not function or function.__code__ is not code:
            raise ValueError(f"Fixed retrieval dependency callable changed: {name}")
    for name, function in _ALIASES:
        if globals().get(name) is not function:
            raise ValueError(f"Fixed retrieval dependency alias changed: {name}")
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
    return {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS}


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


def _request(ledger, corpus_id, queries):
    corpus = _get(ledger, corpus_id, "retrieval_corpus")
    return {"corpus_id": corpus["id"], "corpus_hash": corpus["hash"], "queries": queries,
            "query_hash": digest(canonical(queries).encode())}


def _retain_artifacts(ledger, run_key, config, queries, sources):
    def capture(role, raw):
        if len(raw) > MAX_BYTES:
            raise ValueError("Execution metadata exceeds 1 MB")
        event = ledger.capture(f"retrieval-input:{run_key}:{role}", raw,
            media_type="text/x-python" if role.startswith("code:") else "application/json",
            event_id=f"retrieval:{run_key}:input:{role}")
        return {"observation_id": event["id"], "event_hash": event["hash"],
                "content_hash": event["body"]["content_hash"], "size": len(raw)}
    return {"config": capture("config", canonical(config).encode()),
        "queries": capture("queries", canonical(queries).encode()),
        "implementation": capture("code:" + __name__, sources[__name__]),
        "dependencies": {name: capture("code:" + name, sources[name]) for name in DEPENDENCY_NAMES}}


def _validate_results(results, queries, corpus):
    if type(results) is not list or len(results) != len(queries):
        raise ValueError("Results must cover every query exactly once")
    allowed = {_span_key(row) for row in corpus["passages"]}
    for query, row in zip(queries, results):
        _keys(row, {"query_id", "query", "status", "reason", "hits"}, "query result")
        if row["query_id"] != query["query_id"] or row["query"] != query["query"]:
            raise ValueError("Result queries differ from candidate input")
        hits = row["hits"]
        if type(hits) is not list or len(hits) > corpus["config"]["top_k"]:
            raise ValueError("Invalid bounded result hits")
        expected_reason = "no_lexical_match" if _terms(query["query"]) else "no_query_terms"
        if hits:
            if row["status"] != "matched" or row["reason"] is not None or expected_reason == "no_query_terms":
                raise ValueError("Invalid matched query status")
        elif row["status"] != "empty" or row["reason"] != expected_reason:
            raise ValueError("Invalid empty query status")
        seen, previous = set(), None
        for rank, hit in enumerate(hits, 1):
            _keys(hit, SPAN_FIELDS | {"rank", "score"}, "hit")
            _identifier(hit["observation_id"], "Hit observation ID")
            if type(hit["start"]) is not int or type(hit["end"]) is not int:
                raise ValueError("Hit offsets must be integers")
            _hash(hit["sha256"], "Hit SHA-256")
            key = _span_key(hit)
            if key not in allowed or key in seen:
                raise ValueError("Hit is not a distinct eligible corpus passage")
            seen.add(key)
            if type(hit["rank"]) is not int or hit["rank"] != rank or type(hit["score"]) is not float or not math.isfinite(hit["score"]):
                raise ValueError("Invalid hit rank or finite BM25 score")
            order = (hit["score"], *key)
            if previous is not None and order < previous:
                raise ValueError("Hits violate deterministic BM25 ordering")
            previous = order
    _bounded_size(results, MAX_BYTES, "Retrieval results")


def _checked_artifacts(ledger, body, corpus, now, terminal_seq, *, verify_bytes):
    artifacts = body["artifacts"]
    _keys(artifacts, {"config", "queries", "implementation", "dependencies"}, "retrieval artifacts")
    _keys(artifacts["dependencies"], DEPENDENCY_NAMES, "retrieval dependencies")
    expected = {"config": body["config_hash"], "queries": body["query_hash"],
                "implementation": body["implementation_hash"]}
    refs = {key: artifacts[key] for key in expected}
    refs.update(artifacts["dependencies"])
    for role, ref in refs.items():
        _keys(ref, REF_FIELDS, "artifact reference")
        if type(ref["size"]) is not int or not 0 <= ref["size"] <= MAX_BYTES:
            raise ValueError("Invalid artifact reference size")
        checked, _ = _retained(ledger, ref["observation_id"], now, verify_bytes=verify_bytes)
        event = _get(ledger, ref["observation_id"], "observation")
        source_role = "code:" + (__name__ if role == "implementation" else role) if role == "implementation" or role in DEPENDENCY_NAMES else role
        if checked != ref or not corpus["seq"] < event["seq"] < terminal_seq or event["body"].get("source") != f"retrieval-input:{body['run_key']}:{source_role}":
            raise ValueError("Execution artifact binding/order mismatch")
        if role in expected and ref["content_hash"] != expected[role]:
            raise ValueError("Execution artifact hash mismatch")


def _checked_runtime(runtime):
    _keys(runtime, {"python_version", "python_implementation", "python_cache_tag", "python_optimize",
        "unicode_version", "sqlite_version", "sqlite_source_id", "sqlite_compile_options"}, "runtime")
    for key in ("python_version", "python_implementation", "python_cache_tag", "unicode_version", "sqlite_version", "sqlite_source_id"):
        if type(runtime[key]) is not str or not runtime[key] or len(runtime[key].encode()) > 2048:
            raise ValueError("Invalid runtime text")
    if type(runtime["python_optimize"]) is not int or runtime["python_optimize"] not in (0, 1, 2):
        raise ValueError("Invalid Python optimization")
    options = runtime["sqlite_compile_options"]
    if type(options) is not list or len(options) > 512 or any(type(option) is not str or len(option.encode()) > 512 for option in options) or options != sorted(set(options)):
        raise ValueError("Invalid SQLite compile options")


def _checked_terminal(ledger, terminal, request, *, verify_bytes):
    body = terminal["body"]
    if type(body) is not dict:
        raise ValueError("Retrieval terminal body must be an object")
    run_key = body.get("run_key")
    if type(run_key) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key) is None:
        raise ValueError("Invalid retrieval run key")
    start = _get(ledger, f"retrieval:{run_key}:started", "retrieval_started")
    _keys(start["body"], {"schema_version", "run_key", "request"}, "retrieval claim")
    if start["body"] != {"schema_version": 1, "run_key": run_key, "request": request} or type(start["body"]["schema_version"]) is not int or terminal["id"] != f"retrieval:{run_key}:terminal" or start["seq"] >= terminal["seq"]:
        raise ValueError("Retrieval terminal does not match its earlier claim")
    if body.get("request") != request or type(body.get("schema_version")) is not int or body["schema_version"] != 1:
        raise ValueError("Retrieval terminal request mismatch")
    if terminal["kind"] == "retrieval_rejected":
        _keys(body, {"schema_version", "run_key", "request", "result", "error"}, "retrieval rejection")
        _keys(body["error"], {"type", "message"}, "retrieval error")
        if body["result"] != "rejected" or any(type(value) is not str or len(value.encode()) > 512 for value in body["error"].values()):
            raise ValueError("Invalid bounded retrieval error")
        return terminal
    if terminal["kind"] != "retrieval_completed":
        raise ValueError("Invalid retrieval terminal kind")
    _keys(body, RUN_FIELDS, "retrieval completion")
    now = _time(terminal["recorded_at"], "Retrieval recorded_at")
    corpus, _ = _checked_corpus(ledger, request["corpus_id"], now, verify_bytes=verify_bytes)
    if corpus["seq"] >= start["seq"] or body["result"] != "completed" or body["corpus_id"] != corpus["id"] or body["corpus_hash"] != corpus["hash"] or body["corpus_hash"] != request["corpus_hash"] or body["config_hash"] != corpus["body"]["config_hash"] or body["query_hash"] != request["query_hash"]:
        raise ValueError("Retrieval completion input binding mismatch")
    _validate_results(body["results"], request["queries"], corpus["body"])
    if body["results_hash"] != digest(canonical(body["results"]).encode()):
        raise ValueError("Retrieval result hash mismatch")
    _checked_runtime(body["runtime"])
    if body["runtime_hash"] != digest(canonical(body["runtime"]).encode()):
        raise ValueError("Retrieval runtime hash mismatch")
    _hash(body["implementation_hash"], "Implementation hash")
    _checked_artifacts(ledger, body, corpus, now, terminal["seq"], verify_bytes=verify_bytes)
    resources = body["resources"]
    _keys(resources, {"elapsed_seconds", "elapsed_scope", "execution_budget_seconds", "input_bytes", "passages", "queries",
        "output_bytes", "model_calls", "external_spend"}, "retrieval resources")
    if type(resources["elapsed_seconds"]) not in (int, float) or not math.isfinite(resources["elapsed_seconds"]) or not 0 <= resources["elapsed_seconds"] <= corpus["body"]["config"]["execution_seconds"]:
        raise ValueError("Invalid elapsed retrieval time")
    expected_resources = {"elapsed_scope": ELAPSED_SCOPE, "execution_budget_seconds": corpus["body"]["config"]["execution_seconds"],
        "input_bytes": corpus["body"]["source_bytes"], "passages": corpus["body"]["passage_count"],
        "queries": len(request["queries"]), "output_bytes": len(canonical(body["results"]).encode()),
        "model_calls": 0, "external_spend": 0}
    if any(resources[key] != value or type(resources[key]) is not type(value) for key, value in expected_resources.items()) or body["scope"] != SCOPE:
        raise ValueError("Retrieval resources or scope mismatch")
    return terminal


def get_retrieval_run(ledger, terminal_id, *, verify_bytes=True):
    """Validate a completed historical receipt; never re-execute retained code.

    With verify_bytes=True, also verify available source and metadata blobs.
    False validates historical bindings only and is not an availability claim.
    Reproducibility requires a new run key and a new index.
    """
    if type(verify_bytes) is not bool:
        raise ValueError("verify_bytes must be boolean")
    with _read_transaction(ledger):
        terminal = _get(ledger, terminal_id, "retrieval_completed")
        if type(terminal["body"]) is not dict:
            raise ValueError("Retrieval terminal body must be an object")
        request = terminal["body"].get("request")
        _keys(request, REQUEST_FIELDS, "retrieval request")
        queries = _queries(request["queries"])
        _hash(request["corpus_hash"], "Requested corpus hash")
        if request["query_hash"] != digest(canonical(queries).encode()):
            raise ValueError("Requested query hash mismatch")
        return _checked_terminal(ledger, terminal, request, verify_bytes=verify_bytes)


def run_lexical_retrieval(ledger, corpus_id, queries, *, run_key):
    """Exclusively claim, execute, and retain one completion or bounded rejection.

    An identical run-key retry returns its historical terminal without reading
    blobs or checking current code/runtime. An unfinished claim needs diagnosis.
    """
    if sys._getframe().f_code is not run_lexical_retrieval.__code__:
        raise ValueError("Stale retrieval runner; use a fresh reviewed process")
    _standalone(ledger)
    _identifier(corpus_id, "Corpus ID")
    if type(run_key) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key) is None:
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    queries = _queries(queries)
    started_id, terminal_id = f"retrieval:{run_key}:started", f"retrieval:{run_key}:terminal"
    with _read_transaction(ledger):
        request = _request(ledger, corpus_id, queries)
        _bounded_size(request, MAX_BYTES, "Retrieval request")
        start, terminal = _optional(ledger, started_id), _optional(ledger, terminal_id)
        if start is not None and (start["kind"] != "retrieval_started" or type(start["body"]) is not dict or start["body"].get("request") != request):
            raise ValueError("Run key already has a different request")
        if terminal is not None:
            if start is None:
                raise ValueError("Terminal lacks retrieval claim")
            return _checked_terminal(ledger, terminal, request, verify_bytes=False)
        if start is not None:
            raise ValueError("Incomplete retrieval run requires diagnosis; do not blindly replay")

    def validate_claim(_):
        if _optional(ledger, terminal_id) is not None or _request(ledger, corpus_id, queries) != request:
            raise ValueError("Retrieval request changed before claim")

    ledger.append("retrieval_started", {"schema_version": 1, "run_key": run_key, "request": request},
                  started_id, validate=validate_claim, exclusive=True)

    def validate_terminal(_):
        claimed = _get(ledger, started_id, "retrieval_started")
        if claimed["body"] != {"schema_version": 1, "run_key": run_key, "request": request} or _optional(ledger, terminal_id) is not None:
            raise ValueError("Retrieval terminal does not match its unfinished claim")

    begun = time.monotonic()
    try:
        sources = _runtime_sources()
        with _read_transaction(ledger):
            corpus, passages = _checked_corpus(ledger, corpus_id, _time(ledger.clock(), "Ledger clock"))
        config = corpus["body"]["config"]
        deadline = begun + config["execution_seconds"]
        _check_deadline(deadline)
        artifacts = _retain_artifacts(ledger, run_key, config, queries, sources)
        runtime = _runtime()
        results = _search(passages, queries, config, deadline)
        _validate_results(results, queries, corpus["body"])
        body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "completed",
            "corpus_id": corpus_id, "corpus_hash": corpus["hash"], "config_hash": corpus["body"]["config_hash"],
            "query_hash": request["query_hash"], "artifacts": artifacts, "runtime": runtime,
            "runtime_hash": digest(canonical(runtime).encode()), "implementation_hash": digest(sources[__name__]),
            "results": results, "results_hash": digest(canonical(results).encode()),
            "resources": {"elapsed_seconds": time.monotonic() - begun, "elapsed_scope": ELAPSED_SCOPE, "execution_budget_seconds": config["execution_seconds"],
                "input_bytes": corpus["body"]["source_bytes"], "passages": len(passages), "queries": len(queries),
                "output_bytes": len(canonical(results).encode()), "model_calls": 0, "external_spend": 0}, "scope": SCOPE}
        _bounded_size(body, MAX_BYTES, "Retrieval terminal")
        expected_body = canonical(body)

        def validate_completion(recorded_at):
            validate_terminal(recorded_at)
            _check_deadline(deadline)
            if _request(ledger, corpus_id, queries) != request or _runtime_sources() != sources or _runtime() != runtime:
                raise ValueError("Retrieval inputs or runtime changed before completion")
            checked, checked_passages = _checked_corpus(ledger, corpus_id, _time(recorded_at, "Completion recorded_at"))
            if checked != corpus or _search(checked_passages, queries, config, deadline) != results:
                raise ValueError("Retrieval inputs or recomputed results changed before completion")
            _checked_artifacts(ledger, body, corpus, _time(recorded_at, "Completion recorded_at"),
                ledger.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM events").fetchone()[0], verify_bytes=True)
            _validate_results(body["results"], queries, corpus["body"])
            if canonical(body) != expected_body:
                raise ValueError("Retrieval completion changed before append")
            _check_deadline(deadline)

        return ledger.append("retrieval_completed", body, terminal_id, validate=validate_completion, exclusive=True)
    except Exception as error:
        message = str(error).encode("utf-8", errors="backslashreplace")[:400].decode("utf-8", errors="ignore")
        body = {"schema_version": 1, "run_key": run_key, "request": request, "result": "rejected",
                "error": {"type": type(error).__name__, "message": message}}
        return ledger.append("retrieval_rejected", body, terminal_id, validate=validate_terminal, exclusive=True)


# Same finite, loaded-source pinning pattern as the fixed graph executors.
_FUNCTION_CODES = tuple((name, value, value.__code__) for name, value in list(globals().items())
    if callable(value) and getattr(value, "__module__", None) == __name__ and hasattr(value, "__code__"))

_DEPENDENCY_FUNCTION_CODES = tuple(
    (module, name, value, value.__code__)
    for module in (store, assertions, manifests)
    for name, value in vars(module).items()
    if callable(value) and getattr(value, "__module__", None) == module.__name__ and hasattr(value, "__code__")
) + tuple((_LEDGER_CLASS, name, getattr(_LEDGER_CLASS, name), getattr(_LEDGER_CLASS, name).__code__)
          for name in ("get", "append", "capture", "atomic_write"))
_ALIASES = tuple((name, globals()[name]) for name in ("canonical", "digest", "_event_integrity", "_hash",
    "_read_transaction", "_snapshot", "_time", "_keys", "_observation"))
