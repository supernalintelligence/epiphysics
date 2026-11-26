"""Neutral bounded retrieval contracts and historical receipt validation.

This module never imports a candidate, runner or evaluator and never searches.
Returned citations remain raw source windows; projection maps are derived data.
"""
from __future__ import annotations

from copy import deepcopy
import html
import html.entities
import json
import math
from pathlib import Path
import re
import sys
import time

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, store
from .store import canonical, digest
from .assertions import _event_integrity, _hash, _read_transaction, _snapshot, _time
from .manifests import _keys, _observation

IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE)
    for module in (store, assertions, manifests))
_LEDGER_CLASS = store.Ledger
_MODULES = (store, assertions, manifests, sys.modules[__name__])
_IMPLEMENTATIONS = tuple((module, Path(module.__file__), module.IMPLEMENTATION_SOURCE,
    module.IMPLEMENTATION_CODE, module.IMPLEMENTATION_DEPENDENCIES) for module in _MODULES)
LEGACY_IMPLEMENTATION_NAME = 'epiphysics.retrieval'
DEPENDENCY_NAMES = ('epiphysics.store', 'epiphysics.assertions', 'epiphysics.manifests')
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
RAW_RECIPE = "raw-window-text-v1"
HTML_RECIPE = "static-html-text-nodes-v1"
RECIPE_IDS = (RAW_RECIPE, HTML_RECIPE)
RECIPES = RECIPE_IDS
INDEXING_RECIPES = RECIPE_IDS
REQUEST_FIELDS_V2 = REQUEST_FIELDS | {"indexing_recipe"}
RUN_FIELDS_V2 = RUN_FIELDS | {"indexing_recipe", "projection_hash"}
DEPENDENCY_NAMES_V2 = (*DEPENDENCY_NAMES, "epiphysics.retrieval_contracts", "epiphysics.retrieval_indexing")
STDLIB_NAMES = ("html", "html.parser", "html.entities", "_markupbase", "html.entities.html5")
MAX_MAPPING_PIECES = 65_536
MAX_INDEXED_WINDOW_BYTES = 8192
MAX_INDEXED_TOTAL_BYTES = 8_000_000
MAX_MAPPING_BYTES = 8_000_000
MAX_PROJECTION_BYTES = 12_000_000
MAX_PROJECTION_CHUNKS = 16
MAX_REFERENCE_BYTES = 64
_DECODER_MODULES = tuple((module, Path(module.__file__), Path(module.__file__).read_bytes())
                         for module in (html, html.entities))
_UNESCAPE = html.unescape
_UNESCAPE_CODE = html.unescape.__code__
_REPLACE_CHARREF = html._replace_charref
_REPLACE_CHARREF_CODE = html._replace_charref.__code__
_HTML_TABLE = dict(html.entities.html5)
_HTML_TABLE_BYTES = canonical(_HTML_TABLE).encode()



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


def _indexing_recipe(value):
    if type(value) is not str or value not in RECIPE_IDS:
        raise ValueError("Indexing recipe must be one of the two fixed recipes")
    return value


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


def _request(ledger, corpus_id, queries):
    corpus = _get(ledger, corpus_id, "retrieval_corpus")
    return {"corpus_id": corpus["id"], "corpus_hash": corpus["hash"], "queries": queries,
            "query_hash": digest(canonical(queries).encode())}


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
        source_role = "code:" + (LEGACY_IMPLEMENTATION_NAME if role == "implementation" else role) if role == "implementation" or role in DEPENDENCY_NAMES else role
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


def _checked_terminal_v1(ledger, terminal, request, *, verify_bytes):
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
        version = terminal["body"].get("schema_version")
        if type(version) is not int or version not in (1, 2):
            raise ValueError("Unsupported retrieval receipt schema")
        request = terminal["body"].get("request")
        _keys(request, REQUEST_FIELDS if version == 1 else REQUEST_FIELDS_V2, "retrieval request")
        queries = _queries(request["queries"])
        _hash(request["corpus_hash"], "Requested corpus hash")
        if request["query_hash"] != digest(canonical(queries).encode()):
            raise ValueError("Requested query hash mismatch")
        return _checked_terminal(ledger, terminal, request, verify_bytes=verify_bytes)


def _decoder_guard():
    if (html.unescape is not _UNESCAPE or html.unescape.__code__ is not _UNESCAPE_CODE
            or html._replace_charref is not _REPLACE_CHARREF or html._replace_charref.__code__ is not _REPLACE_CHARREF_CODE
            or html.entities.html5 != _HTML_TABLE or html._html5 != _HTML_TABLE):
        raise ValueError("Entity decoder implementation changed")


def _decoder_sources():
    _decoder_guard()
    sources = {}
    for module, path, source in _DECODER_MODULES:
        if len(source) > MAX_BYTES or path.is_symlink() or not path.is_file() or path.stat().st_size != len(source):
            raise ValueError("Entity decoder source changed")
        with path.open("rb") as stream:
            if stream.read(len(source) + 1) != source:
                raise ValueError("Entity decoder source changed")
        if module is html:
            compiled = compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize)
            functions = {item.co_name: item for item in compiled.co_consts if type(item) is type(_UNESCAPE_CODE)}
            if functions.get("unescape") != _UNESCAPE_CODE or functions.get("_replace_charref") != _REPLACE_CHARREF_CODE:
                raise ValueError("Loaded entity decoder differs from retained source")
        sources[module.__name__] = source
    sources["html.entities.html5"] = _HTML_TABLE_BYTES
    return sources


def decode_entity(raw):
    """Decode one complete bounded lexeme; None means keep the source literal."""
    if type(raw) is not bytes:
        raise ValueError("Entity lexeme must be bytes")
    if not 3 <= len(raw) <= MAX_REFERENCE_BYTES or not raw.startswith(b"&") or not raw.endswith(b";"):
        return None
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    if re.fullmatch(r"&#(?:[0-9]+|[xX][0-9a-fA-F]+);", text):
        if (html.unescape is not _UNESCAPE or html.unescape.__code__ is not _UNESCAPE_CODE
                or html._replace_charref is not _REPLACE_CHARREF or html._replace_charref.__code__ is not _REPLACE_CHARREF_CODE):
            raise ValueError("Entity decoder callable changed")
        return _UNESCAPE(text).encode("utf-8")
    named = _HTML_TABLE.get(text[1:])
    return None if named is None else named.encode("utf-8")


def normalize_media_type(value):
    if type(value) is not str or len(value) > 512:
        raise ValueError("Source media type must be bounded text")
    try:
        if len(value.encode("utf-8")) > 512:
            raise ValueError("Source media type exceeds byte bound")
    except UnicodeError as error:
        raise ValueError("Invalid source media type") from error
    return value.split(";", 1)[0].strip().translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))


def validate_projection(source_inputs, raw_manifest, projection, *, deadline=None):
    """Verify source-bound map assembly, never regenerate candidate selection.

    HTML maps may select source text, but only source-preserving copy/entity
    operations and unsupported synthetic spaces can construct indexed bytes.
    Returned citations remain the complete original raw windows.
    """
    _decoder_guard()
    if type(source_inputs) is not dict or not 1 <= len(source_inputs) <= MAX_SOURCES:
        raise ValueError("Projection requires bounded selected source inputs")
    source_total = 0
    for oid, source in source_inputs.items():
        _identifier(oid, "Projection source ID")
        _keys(source, {"raw", "media_type"}, "projection source")
        raw = source["raw"]
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            raise ValueError("Projection source exceeds byte bound")
        source_total += len(raw)
        if source_total > MAX_TOTAL_BYTES:
            raise ValueError("Projection selected sources exceed aggregate bound")
        raw.decode("utf-8", errors="strict")
        normalize_media_type(source["media_type"])
    if type(raw_manifest) is not list or len(raw_manifest) > MAX_PASSAGES:
        raise ValueError("Invalid projection raw manifest")
    _keys(projection, {"schema_version", "recipe", "rows"}, "projection")
    if type(projection["schema_version"]) is not int or projection["schema_version"] != 1 or projection["recipe"] not in RECIPES:
        raise ValueError("Unsupported projection schema or recipe")
    rows = projection["rows"]
    if type(rows) is not list or len(rows) != len(raw_manifest):
        raise ValueError("Projection must preserve every raw window")
    sizes = {oid: len(value["raw"]) for oid, value in source_inputs.items()}
    pieces_total = indexed_total = mapping_total = 0
    previous_key = None
    for manifest, row in zip(raw_manifest, rows):
        if deadline is not None:
            _check_deadline(deadline)
        _keys(manifest, SPAN_FIELDS, "raw manifest span")
        _span_shape(manifest, sizes)
        key = _span_key(manifest)
        if previous_key is not None and key <= previous_key:
            raise ValueError("Projection raw windows must retain canonical ordering")
        previous_key = key
        _keys(row, SPAN_FIELDS | {"indexed_text", "indexed_text_sha256", "indexed_bytes", "mapping"}, "projected row")
        if {name: row[name] for name in SPAN_FIELDS} != manifest:
            raise ValueError("Projection changed a raw source window")
        source = source_inputs[row["observation_id"]]
        raw = source["raw"]
        raw_slice = raw[row["start"]:row["end"]]
        raw_slice.decode("utf-8", errors="strict")
        if digest(raw_slice) != row["sha256"]:
            raise ValueError("Projection raw window digest mismatch")
        text = row["indexed_text"]
        if type(text) is not str or len(text) > MAX_INDEXED_WINDOW_BYTES:
            raise ValueError("Indexed text exceeds window byte bound")
        try:
            indexed = text.encode("utf-8")
        except UnicodeError as error:
            raise ValueError("Indexed text must be valid UTF-8") from error
        if len(indexed) > MAX_INDEXED_WINDOW_BYTES or type(row["indexed_bytes"]) is not int or row["indexed_bytes"] != len(indexed):
            raise ValueError("Indexed window byte length mismatch")
        indexed_total += len(indexed)
        if indexed_total > MAX_INDEXED_TOTAL_BYTES:
            raise ValueError("Indexed text exceeds aggregate byte bound")
        _hash(row["indexed_text_sha256"], "Indexed text hash")
        if digest(indexed) != row["indexed_text_sha256"]:
            raise ValueError("Indexed text digest mismatch")
        mapping = row["mapping"]
        if type(mapping) is not list:
            raise ValueError("Projection mapping must be a list")
        pieces_total += len(mapping)
        if pieces_total > MAX_MAPPING_PIECES:
            raise ValueError("Projection mapping exceeds piece bound")
        offset, source_end = 0, None
        gap_since_output = False
        separator_since_output = False
        has_output = False
        assembled = []
        for piece_index, piece in enumerate(mapping):
            if deadline is not None:
                _check_deadline(deadline)
            _keys(piece, {"kind", "start", "end", "source"}, "projection mapping piece")
            if (type(piece["start"]) is not int or type(piece["end"]) is not int
                    or not 0 <= piece["start"] == offset <= piece["end"] <= len(indexed)):
                raise ValueError("Projection offsets must exactly cover indexed text in order")
            kind = piece["kind"]
            if kind == "separator":
                if (piece["source"] is not None or piece["end"] - offset != 1 or not has_output
                        or piece["end"] == len(indexed) or separator_since_output):
                    raise ValueError("Synthetic separator cannot carry source support or be leading/trailing")
                data = b" "
                separator_since_output = True
            elif kind in ("copy", "entity"):
                span = piece["source"]
                _keys(span, {"start", "end", "sha256"}, "mapping source interval")
                if (type(span["start"]) is not int or type(span["end"]) is not int
                        or not row["start"] <= span["start"] < span["end"] <= row["end"]
                        or source_end is not None and span["start"] < source_end):
                    raise ValueError("Mapping source intervals must be inside the window and ordered without overlap")
                lexeme = raw[span["start"]:span["end"]]
                lexeme.decode("utf-8", errors="strict")
                _hash(span["sha256"], "Mapping source hash")
                if digest(lexeme) != span["sha256"]:
                    raise ValueError("Mapping source digest mismatch")
                if source_end is not None and span["start"] > source_end:
                    gap_since_output = True
                if kind == "copy":
                    data = lexeme
                else:
                    data = decode_entity(lexeme)
                    if data is None:
                        raise ValueError("Entity map requires a complete recognized reference")
                source_end = span["end"]
                if data:
                    if has_output and gap_since_output != separator_since_output:
                        raise ValueError("Only omitted source bytes between emitted pieces require a separator")
                    has_output = True
                    gap_since_output = separator_since_output = False
            else:
                raise ValueError("Unknown projection mapping operation")
            if piece["end"] - offset != len(data) or indexed[offset:piece["end"]] != data:
                raise ValueError("Projection map does not reconstruct indexed bytes")
            assembled.append(data)
            offset = piece["end"]
        if offset != len(indexed) or b"".join(assembled) != indexed:
            raise ValueError("Projection map does not cover all indexed bytes")
        mapping_total += _bounded_size(mapping, MAX_MAPPING_BYTES, "Projection mapping")
        if mapping_total > MAX_MAPPING_BYTES:
            raise ValueError("Projection mapping exceeds aggregate byte bound")
        if projection["recipe"] == "raw-window-text-v1" or normalize_media_type(source["media_type"]) != "text/html":
            expected = [{"kind": "copy", "start": 0, "end": len(raw_slice),
                         "source": {"start": row["start"], "end": row["end"], "sha256": digest(raw_slice)}}]
            if indexed != raw_slice or mapping != expected:
                raise ValueError("Raw and non-HTML windows must preserve exact source bytes and copy mapping")
    _bounded_size(projection, MAX_PROJECTION_BYTES, "Projection")
    _decoder_guard()
    return projection


def _projection_sources(ledger, corpus, now, *, verify_bytes=True):
    selected = [ref["observation_id"] for ref in corpus["body"]["sources"]]
    _, refs, raw = _source_inputs(ledger, corpus["body"]["snapshot_id"], selected, now, verify_bytes=verify_bytes)
    if refs != corpus["body"]["sources"]:
        raise ValueError("Projection selected source bindings changed")
    sources = {}
    for oid in selected:
        observation = _get(ledger, oid, "observation")
        media_type = observation["body"].get("media_type")
        normalize_media_type(media_type)
        if verify_bytes:
            sources[oid] = {"raw": raw[oid], "media_type": media_type}
    return sources


def _artifact_reference(ledger, ref, role, body, corpus, now, terminal_seq, *, verify_bytes):
    _keys(ref, REF_FIELDS, "artifact reference")
    if type(ref["size"]) is not int or not 0 <= ref["size"] <= MAX_BYTES:
        raise ValueError("Invalid bounded artifact reference size")
    checked, raw = _retained(ledger, ref["observation_id"], now, verify_bytes=verify_bytes)
    event = _get(ledger, ref["observation_id"], "observation")
    if (checked != ref or not corpus["seq"] < event["seq"] < terminal_seq
            or event["body"].get("source") != f"retrieval-input:{body['run_key']}:{role}"):
        raise ValueError("Execution artifact binding/order mismatch")
    return raw


def _strict_json(raw, label):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"Duplicate field in {label}")
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        canonical(value)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ValueError(f"Invalid {label} JSON") from error


def _checked_artifacts_v2(ledger, body, corpus, now, terminal_seq, *, verify_bytes):
    artifacts = body["artifacts"]
    _keys(artifacts, {"config", "queries", "implementation", "dependencies", "recipe", "projection", "stdlib"}, "v2 retrieval artifacts")
    _keys(artifacts["dependencies"], DEPENDENCY_NAMES_V2, "v2 retrieval dependencies")
    _keys(artifacts["stdlib"], STDLIB_NAMES, "v2 retrieval stdlib")
    recipe = {"schema_version": 1, "indexing_recipe": _indexing_recipe(body["indexing_recipe"])}
    expected = {"config": body["config_hash"], "queries": body["query_hash"],
                "implementation": body["implementation_hash"], "recipe": digest(canonical(recipe).encode())}
    payloads = {"config": canonical(corpus["body"]["config"]).encode(),
                "queries": canonical(body["request"]["queries"]).encode(), "recipe": canonical(recipe).encode()}
    for role, expected_hash in expected.items():
        ref = artifacts[role]
        raw = _artifact_reference(ledger, ref, "code:" + LEGACY_IMPLEMENTATION_NAME if role == "implementation" else role,
                                  body, corpus, now, terminal_seq, verify_bytes=verify_bytes)
        if ref["content_hash"] != expected_hash or verify_bytes and role in payloads and raw != payloads[role]:
            raise ValueError("V2 execution artifact hash/content mismatch")
    for name, ref in artifacts["dependencies"].items():
        _artifact_reference(ledger, ref, "code:" + name, body, corpus, now, terminal_seq, verify_bytes=verify_bytes)
    decoder_sources = _decoder_sources() if verify_bytes else {}
    for name, ref in artifacts["stdlib"].items():
        role = "data:" + name if name == "html.entities.html5" else "code:" + name
        raw = _artifact_reference(ledger, ref, role, body, corpus, now, terminal_seq, verify_bytes=verify_bytes)
        if name in decoder_sources and raw != decoder_sources[name]:
            raise ValueError("Retained projection decoder differs from the current measurement contract")
    descriptor = artifacts["projection"]
    _keys(descriptor, {"schema_version", "sha256", "size", "chunks"}, "projection descriptor")
    if (type(descriptor["schema_version"]) is not int or descriptor["schema_version"] != 1
            or type(descriptor["size"]) is not int or not 1 <= descriptor["size"] <= MAX_PROJECTION_BYTES
            or type(descriptor["chunks"]) is not list or not 1 <= len(descriptor["chunks"]) <= MAX_PROJECTION_CHUNKS):
        raise ValueError("Invalid bounded projection descriptor")
    _hash(descriptor["sha256"], "Projection descriptor hash")
    _hash(body["projection_hash"], "Projection hash")
    if descriptor["sha256"] != body["projection_hash"]:
        raise ValueError("Projection descriptor hash mismatch")
    total, chunks, observation_ids = 0, [], set()
    for index, ref in enumerate(descriptor["chunks"]):
        _keys(ref, REF_FIELDS, "projection chunk reference")
        if type(ref["size"]) is not int or not 1 <= ref["size"] <= MAX_BYTES:
            raise ValueError("Projection chunk exceeds byte bound")
        total += ref["size"]
        if total > descriptor["size"] or total > MAX_PROJECTION_BYTES:
            raise ValueError("Projection chunks exceed aggregate byte bound")
        _identifier(ref["observation_id"], "Projection chunk observation")
        if ref["observation_id"] in observation_ids:
            raise ValueError("Projection chunks must have distinct observation references")
        observation_ids.add(ref["observation_id"])
        raw = _artifact_reference(ledger, ref, f"projection:{index:04d}", body, corpus, now, terminal_seq, verify_bytes=verify_bytes)
        if verify_bytes:
            chunks.append(raw)
    if total != descriptor["size"]:
        raise ValueError("Projection chunk sizes do not match descriptor")
    sources = _projection_sources(ledger, corpus, now, verify_bytes=verify_bytes)
    if not verify_bytes:
        return None
    raw = b"".join(chunks)
    if digest(raw) != descriptor["sha256"]:
        raise ValueError("Projection content hash mismatch")
    projection = _strict_json(raw, "projection")
    if canonical(projection).encode() != raw:
        raise ValueError("Projection artifact must use canonical JSON bytes")
    if type(projection) is not dict or projection.get("recipe") != body["indexing_recipe"]:
        raise ValueError("Projection recipe does not match execution")
    validate_projection(sources, corpus["body"]["passages"], projection)
    return projection


def _checked_terminal_v2(ledger, terminal, request, *, verify_bytes):
    body = terminal["body"]
    if type(body) is not dict:
        raise ValueError("Retrieval terminal body must be an object")
    _keys(request, REQUEST_FIELDS_V2, "v2 retrieval request")
    _indexing_recipe(request["indexing_recipe"])
    queries = _queries(request["queries"])
    _hash(request["corpus_hash"], "Requested corpus hash")
    if request["query_hash"] != digest(canonical(queries).encode()):
        raise ValueError("Requested query hash mismatch")
    run_key = body.get("run_key")
    if type(run_key) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key) is None:
        raise ValueError("Invalid retrieval run key")
    start = _get(ledger, f"retrieval:{run_key}:started", "retrieval_started")
    _keys(start["body"], {"schema_version", "run_key", "request"}, "v2 retrieval claim")
    if (start["body"] != {"schema_version": 2, "run_key": run_key, "request": request}
            or type(start["body"]["schema_version"]) is not int
            or terminal["id"] != f"retrieval:{run_key}:terminal" or start["seq"] >= terminal["seq"]):
        raise ValueError("Retrieval terminal does not match its earlier v2 claim")
    if body.get("request") != request or type(body.get("schema_version")) is not int or body["schema_version"] != 2:
        raise ValueError("V2 retrieval terminal request mismatch")
    if terminal["kind"] == "retrieval_rejected":
        _keys(body, {"schema_version", "run_key", "request", "result", "error"}, "retrieval rejection")
        _keys(body["error"], {"type", "message"}, "retrieval error")
        if body["result"] != "rejected" or any(type(value) is not str or len(value.encode()) > 512 for value in body["error"].values()):
            raise ValueError("Invalid bounded retrieval error")
        return terminal
    if terminal["kind"] != "retrieval_completed":
        raise ValueError("Invalid retrieval terminal kind")
    _keys(body, RUN_FIELDS_V2, "v2 retrieval completion")
    if body["indexing_recipe"] != request["indexing_recipe"]:
        raise ValueError("V2 recipe does not match claim")
    now = _time(terminal["recorded_at"], "Retrieval recorded_at")
    corpus, _ = _checked_corpus(ledger, request["corpus_id"], now, verify_bytes=verify_bytes)
    if (corpus["seq"] >= start["seq"] or body["result"] != "completed" or body["corpus_id"] != corpus["id"]
            or body["corpus_hash"] != corpus["hash"] or body["corpus_hash"] != request["corpus_hash"]
            or body["config_hash"] != corpus["body"]["config_hash"] or body["query_hash"] != request["query_hash"]):
        raise ValueError("Retrieval completion input binding mismatch")
    _validate_results(body["results"], request["queries"], corpus["body"])
    if body["results_hash"] != digest(canonical(body["results"]).encode()):
        raise ValueError("Retrieval result hash mismatch")
    _checked_runtime(body["runtime"])
    if body["runtime_hash"] != digest(canonical(body["runtime"]).encode()):
        raise ValueError("Retrieval runtime hash mismatch")
    _hash(body["implementation_hash"], "Implementation hash")
    projection = _checked_artifacts_v2(ledger, body, corpus, now, terminal["seq"], verify_bytes=verify_bytes)
    resources = body["resources"]
    _keys(resources, {"elapsed_seconds", "elapsed_scope", "execution_budget_seconds", "input_bytes", "passages", "queries",
        "output_bytes", "model_calls", "external_spend", "projection_bytes", "indexed_bytes", "mapping_pieces", "empty_windows"}, "v2 retrieval resources")
    if (type(resources["elapsed_seconds"]) not in (int, float) or not math.isfinite(resources["elapsed_seconds"])
            or not 0 <= resources["elapsed_seconds"] <= corpus["body"]["config"]["execution_seconds"]):
        raise ValueError("Invalid elapsed retrieval time")
    expected = {"elapsed_scope": ELAPSED_SCOPE, "execution_budget_seconds": corpus["body"]["config"]["execution_seconds"],
        "input_bytes": corpus["body"]["source_bytes"], "passages": corpus["body"]["passage_count"],
        "queries": len(request["queries"]), "output_bytes": len(canonical(body["results"]).encode()),
        "model_calls": 0, "external_spend": 0, "projection_bytes": body["artifacts"]["projection"]["size"]}
    if any(resources[key] != value or type(resources[key]) is not type(value) for key, value in expected.items()) or body["scope"] != SCOPE:
        raise ValueError("Retrieval resources or scope mismatch")
    for key, maximum in (("indexed_bytes", MAX_INDEXED_TOTAL_BYTES), ("mapping_pieces", MAX_MAPPING_PIECES),
                         ("empty_windows", corpus["body"]["passage_count"])):
        if type(resources[key]) is not int or not 0 <= resources[key] <= maximum:
            raise ValueError("Invalid bounded projection resource count")
    if projection is not None:
        expected_projection = {"indexed_bytes": sum(row["indexed_bytes"] for row in projection["rows"]),
            "mapping_pieces": sum(len(row["mapping"]) for row in projection["rows"]),
            "empty_windows": sum(row["indexed_bytes"] == 0 for row in projection["rows"])}
        if any(resources[key] != value for key, value in expected_projection.items()):
            raise ValueError("Projection resource counts differ from retained artifact")
    return terminal


def _checked_terminal(ledger, terminal, request, *, verify_bytes):
    if type(terminal.get("body")) is not dict:
        raise ValueError("Retrieval terminal body must be an object")
    version = terminal["body"].get("schema_version")
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported retrieval receipt schema")
    if version == 1:
        return _checked_terminal_v1(ledger, terminal, request, verify_bytes=verify_bytes)
    return _checked_terminal_v2(ledger, terminal, request, verify_bytes=verify_bytes)


def _runtime_sources():
    """The actual measurement dependency closure excludes search and execution."""
    codes = {module.__name__: code for module, _, _, code, _ in _IMPLEMENTATIONS}
    if _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Neutral retrieval ledger class changed")
    for name, function, code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not code:
            raise ValueError(f"Neutral retrieval contract callable changed: {name}")
    for owner, name, function, code in _DEPENDENCY_FUNCTION_CODES:
        if getattr(owner, name, None) is not function or function.__code__ is not code:
            raise ValueError(f"Neutral retrieval dependency callable changed: {name}")
    for name, function in _ALIASES:
        if globals().get(name) is not function:
            raise ValueError(f"Neutral retrieval dependency alias changed: {name}")
    for name, descriptor, function, code, wrapped, wrapped_code in _LEDGER_METHOD_CODES:
        if (vars(_LEDGER_CLASS).get(name) is not descriptor or function.__code__ is not code
                or getattr(function, "__wrapped__", None) is not wrapped
                or wrapped is not None and wrapped.__code__ is not wrapped_code):
            raise ValueError(f"Neutral retrieval ledger method changed: {name}")
    for module, path, source, code, dependencies in _IMPLEMENTATIONS:
        if module.IMPLEMENTATION_CODE is not code or module.IMPLEMENTATION_SOURCE != source:
            raise ValueError(f"Neutral retrieval implementation reloaded: {module.__name__}")
        if len(source) > MAX_BYTES or path.is_symlink() or not path.is_file() or path.stat().st_size != len(source):
            raise ValueError(f"Neutral retrieval implementation source changed: {module.__name__}")
        with path.open("rb") as stream:
            if stream.read(len(source) + 1) != source:
                raise ValueError(f"Neutral retrieval implementation source changed: {module.__name__}")
        if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
            raise ValueError(f"Neutral retrieval code differs from source: {module.__name__}")
        for name, dependency_code in dependencies:
            if codes.get(name) is not dependency_code:
                raise ValueError(f"Neutral retrieval dependency reloaded: {module.__name__} -> {name}")
    return {module.__name__: source for module, _, source, _, _ in _IMPLEMENTATIONS} | _decoder_sources()


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
_DEPENDENCY_FUNCTION_CODES = tuple((module, name, function, function.__code__)
    for module in (store, assertions, manifests) for name, function in vars(module).items()
    if callable(function) and getattr(function, "__module__", None) == module.__name__ and hasattr(function, "__code__"))
_ALIASES = tuple((name, globals()[name]) for name in ("canonical", "digest", "_event_integrity", "_hash",
    "_read_transaction", "_snapshot", "_time", "_keys", "_observation"))
_LEDGER_METHOD_CODES = tuple(
    (name, descriptor, function, function.__code__, getattr(function, "__wrapped__", None),
     getattr(getattr(function, "__wrapped__", None), "__code__", None))
    for name, descriptor in vars(_LEDGER_CLASS).items()
    for function in (descriptor.__func__ if isinstance(descriptor, (classmethod, staticmethod)) else descriptor,)
    if callable(function) and hasattr(function, "__code__")
)
