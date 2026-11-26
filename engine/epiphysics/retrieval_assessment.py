"""Bounded, read-only assessment of two retained retrieval executions.

Only captured bytes are validated and retained. Archived implementation bytes
are evidence, never executable input. A local receipt pair is not an external
execution witness or a sealed evaluation cohort.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, retrieval_contracts as retrieval, retrieval_coverage, retrieval_evaluation, store
from .store import Ledger, canonical, digest, instant

IMPLEMENTATION_DEPENDENCIES = tuple((m.__name__, m.IMPLEMENTATION_CODE)
    for m in (store, assertions, manifests, retrieval, retrieval_evaluation, retrieval_coverage))
MAX_ARTIFACTS = retrieval_coverage.MAX_ARTIFACTS
MAX_ARTIFACT_BYTES = retrieval_coverage.MAX_ARTIFACT_BYTES
MAX_BUNDLE_BYTES = retrieval_coverage.MAX_BUNDLE_BYTES
MAX_INPUT_BYTES = retrieval_coverage.MAX_BYTES
MAX_PREFIX_EVENTS = retrieval_coverage.MAX_PREFIX_EVENTS
MAX_PREFIX_BYTES = retrieval_coverage.MAX_PREFIX_BYTES
REQUEST_FIELDS = {"schema_version", "study_id", "evidence_store", "cohort_file", "corpus_id", "run_terminal_ids"}
CONTRACT_FIELDS = {"schema_version", "study_id", "snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
    "corpus_id", "corpus_hash", "cohort_hash", "gold_hash", "query_hash", "sources_hash", "passages_hash",
    "config_hash", "implementation_hash", "dependency_hashes", "runtime_hash", "run_terminal_hashes"}
COMMON_CONTRACT_FIELDS = CONTRACT_FIELDS - {"implementation_hash", "dependency_hashes", "runtime_hash", "run_terminal_hashes"}
REQUEST_FIELDS_V2 = (REQUEST_FIELDS - {"run_terminal_ids"}) | {"arms", "protocol_file"}
CONTRACT_FIELDS_V2 = COMMON_CONTRACT_FIELDS | {"arms", "protocol_hash"}
ARM_RECIPES = {"raw": retrieval.RAW_RECIPE, "html": retrieval.HTML_RECIPE}
REQUEST_COMMON_V3 = {"schema_version", "phase", "study_id", "evidence_store", "cohort_file", "protocol_file",
    "review_file", "corpus_id", "freeze_event_id"}
CONTRACT_COMMON_V3 = COMMON_CONTRACT_FIELDS | {"phase", "protocol_hash", "review_hash", "freeze_event_hash",
    "reference_terminal", "candidate_algorithm_hash", "evaluator_identity_hash", "runtime_hash"}
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)


def _raw(value):
    try:
        return canonical(value).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Assessment requires finite UTF-8 JSON") from error


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        _raw(value)
        return value
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Invalid bounded assessment JSON") from error


def _keys(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"Invalid {label} fields")


def _id(value, label):
    if type(value) is not str or not value.strip() or len(value) > 512:
        raise ValueError(f"Invalid {label}")
    try:
        if len(value.encode("utf-8")) > 512:
            raise ValueError(f"Oversized {label}")
    except UnicodeError as error:
        raise ValueError(f"Invalid UTF-8 {label}") from error


def _hash(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Expected SHA-256 digest")


def _request_fields(request):
    if type(request) is not dict or type(request.get("schema_version")) is not int or request["schema_version"] not in (1, 2, 3):
        raise ValueError("Assessment schema_version must be 1, 2 or 3")
    if request["schema_version"] == 3:
        if request.get("phase") not in ("preparation", "evaluation"):
            raise ValueError("Coverage phase must be preparation or evaluation")
        _keys(request, REQUEST_COMMON_V3 | ({"run_terminal_ids"} if request["phase"] == "evaluation" else set()), "coverage request")
        return
    _keys(request, REQUEST_FIELDS if request["schema_version"] == 1 else REQUEST_FIELDS_V2, "study request")


def _run_ids(request):
    if request["schema_version"] == 3:
        return request.get("run_terminal_ids", [])
    return request["run_terminal_ids"] if request["schema_version"] == 1 else [
        terminal_id for arm in ARM_RECIPES for terminal_id in request["arms"][arm]["run_terminal_ids"]]


def _inputs(request, cohort, declared_contract):
    _request_fields(request)
    version = request["schema_version"]
    if version == 3:
        _coverage_inputs(request, cohort, declared_contract)
        return
    _keys(declared_contract, CONTRACT_FIELDS if version == 1 else CONTRACT_FIELDS_V2, "declared retrieval contract")
    for item in (request, declared_contract):
        if type(item["schema_version"]) is not int or item["schema_version"] != version:
            raise ValueError("Request and declaration schema versions must match")
        for key in ("study_id", "corpus_id"):
            _id(item[key], key)
        if len(_raw(item)) > MAX_INPUT_BYTES:
            raise ValueError("Assessment input exceeds 1 MB")
    for key in ("evidence_store", "cohort_file", *(("protocol_file",) if version == 2 else ())):
        _id(request[key], key)
        if not Path(request[key]).is_absolute():
            raise ValueError("Study paths must be absolute")
    if version == 2:
        _keys(request["arms"], ARM_RECIPES, "comparison request arms")
        _keys(declared_contract["arms"], ARM_RECIPES, "declared comparison arms")
        for arm, recipe in ARM_RECIPES.items():
            item, declaration = request["arms"][arm], declared_contract["arms"][arm]
            _keys(item, {"indexing_recipe", "run_terminal_ids"}, "comparison arm")
            _keys(declaration, {"indexing_recipe", "candidate_algorithm_hash", "projection_hashes", "run_terminal_hashes"}, "declared comparison arm")
            if item["indexing_recipe"] != recipe or declaration["indexing_recipe"] != recipe:
                raise ValueError("Comparison requires the fixed raw and HTML recipes in their declared arms")
            ids = item["run_terminal_ids"]
            if type(ids) is not list or len(ids) != 2:
                raise ValueError("Each fixed comparison arm requires two terminal IDs")
            for terminal_id in ids:
                _id(terminal_id, "terminal ID")
            _hash(declaration["candidate_algorithm_hash"])
            for field in ("projection_hashes", "run_terminal_hashes"):
                _keys(declaration[field], set(ids), "declared arm output hashes")
                for value in declaration[field].values():
                    _hash(value)
        _hash(declared_contract["protocol_hash"])
    else:
        if type(request["run_terminal_ids"]) is not list or len(request["run_terminal_ids"]) != 2:
            raise ValueError("Exactly two terminal IDs are required")
        deps = declared_contract["dependency_hashes"]
        if type(deps) is not dict or set(deps) not in (set(retrieval.DEPENDENCY_NAMES), set(retrieval.DEPENDENCY_NAMES_V2)):
            raise ValueError("Invalid declared dependency hashes")
        for value in deps.values():
            _hash(value)
        for field in ("implementation_hash", "runtime_hash"):
            _hash(declared_contract[field])
    runs = _run_ids(request)
    for terminal_id in runs:
        _id(terminal_id, "terminal ID")
    if len(set(runs)) != (2 if version == 1 else 4):
        raise ValueError("Require distinct terminal IDs for every execution")
    if version == 1:
        _keys(declared_contract["run_terminal_hashes"], set(runs), "terminal hashes")
        for value in declared_contract["run_terminal_hashes"].values():
            _hash(value)
    for key in ("study_id", "corpus_id"):
        if request[key] != declared_contract[key]:
            raise ValueError(f"Study differs from declared {key}")
    _id(declared_contract["snapshot_id"], "snapshot ID")
    for key in COMMON_CONTRACT_FIELDS - {"schema_version", "study_id", "snapshot_id", "corpus_id"}:
        _hash(declared_contract[key])
    if len(_raw(cohort)) > MAX_INPUT_BYTES:
        raise ValueError("Cohort exceeds 1 MB")
    retrieval_evaluation.project_queries(cohort)


def _coverage_inputs(request, cohort, contract):
    evaluated = request["phase"] == "evaluation"
    _keys(contract, CONTRACT_COMMON_V3 | ({"run_terminal_hashes", "projection_hashes"} if evaluated else set()), "coverage declaration")
    if type(contract["schema_version"]) is not int or contract["schema_version"] != 3 or contract["phase"] != request["phase"]:
        raise ValueError("Coverage declaration version/phase mismatch")
    for value in (request, contract, cohort):
        if len(_raw(value)) > MAX_INPUT_BYTES:
            raise ValueError("Coverage input exceeds 1 MB")
    for key in ("study_id", "corpus_id"):
        _id(request[key], key)
        if request[key] != contract[key]:
            raise ValueError("Coverage request differs from declared " + key)
    for key in ("evidence_store", "cohort_file", "protocol_file", "review_file"):
        _id(request[key], key)
        if not Path(request[key]).is_absolute():
            raise ValueError("Coverage input paths must be absolute")
    _id(request["freeze_event_id"], "freeze ID")
    if request["freeze_event_id"] != retrieval_coverage.freeze_id(request["study_id"]):
        raise ValueError("Coverage freeze ID must match study")
    _id(contract["snapshot_id"], "snapshot ID")
    retrieval_coverage._ref(contract["reference_terminal"], "declared reference terminal")
    for key in CONTRACT_COMMON_V3 - {"schema_version", "phase", "study_id", "snapshot_id", "corpus_id", "reference_terminal"}:
        _hash(contract[key])
    checked = retrieval_evaluation._cohort(cohort)
    if checked["schema_version"] != 2:
        raise ValueError("Coverage study requires cohort schema 2")
    if evaluated:
        ids = request["run_terminal_ids"]
        if type(ids) is not list or len(ids) != 2:
            raise ValueError("Coverage evaluation requires two terminal IDs")
        for eid in ids:
            _id(eid, "coverage terminal ID")
        if len(set(ids)) != 2:
            raise ValueError("Coverage evaluation requires distinct terminals")
        for key in ("run_terminal_hashes", "projection_hashes"):
            _keys(contract[key], set(ids), "coverage output hashes")
            for value in contract[key].values():
                _hash(value)


def _current_sources(coverage=False):
    path, source, code = _SELF
    if (IMPLEMENTATION_SOURCE != source or IMPLEMENTATION_CODE is not code
            or path.is_symlink() or not path.is_file() or path.stat().st_size != len(source)):
        raise ValueError("Assessment implementation changed; use a fresh reviewed process")
    with path.open("rb") as stream:
        if stream.read(len(source) + 1) != source:
            raise ValueError("Assessment implementation changed; use a fresh reviewed process")
    if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
        raise ValueError("Assessment implementation changed; use a fresh reviewed process")
    for name, function, code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not code:
            raise ValueError("Assessment callable changed; use a fresh reviewed process")
    retrieval_evaluation._implementation_identity()
    sources = retrieval._runtime_sources()
    sources[retrieval_evaluation.__name__] = retrieval_evaluation.IMPLEMENTATION_SOURCE
    # The shared capture caps affect every schema; retain/guard their actual
    # source without importing the candidate into the evaluator's closure.
    sources[retrieval_coverage.__name__] = retrieval_coverage.implementation_source()
    sources[__name__] = source
    if coverage:
        for name, raw in retrieval_coverage.runtime_sources().items():
            if name in sources and sources[name] != raw:
                raise ValueError("Coverage source closure collision")
            sources[name] = raw
    return {("data:" if name == "html.entities.html5" else "code:") + name: raw for name, raw in sources.items()}


def _read_file(path, maximum):
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
            raise ValueError("Input must be a bounded regular file, not a symlink")
        # O_NOFOLLOW also closes a final-component symlink substitution race.
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Input must remain a regular file")
            raw = stream.read(maximum + 1)
    except OSError as error:
        raise ValueError("Input is missing or unreadable") from error
    if len(raw) > maximum:
        raise ValueError("Input exceeds byte bound")
    return raw


def _check_artifacts(prepared):
    _keys(prepared, {"artifacts", "manifest"}, "prepared study")
    artifacts, manifest = prepared["artifacts"], prepared["manifest"]
    if type(artifacts) is not dict or not 1 <= len(artifacts) <= MAX_ARTIFACTS:
        raise ValueError("Too many assessment artifacts")
    _keys(manifest, set(artifacts), "artifact manifest")
    total = 0
    for role, raw in artifacts.items():
        _id(role, "artifact role")
        if type(raw) is not bytes or len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("Invalid bounded artifact bytes")
        total += len(raw)
        if total > MAX_BUNDLE_BYTES:
            raise ValueError("Assessment bundle exceeds aggregate byte bound")
        if digest(raw) != manifest[role]:
            raise ValueError("Prepared artifact digest mismatch")


def check_prepared_retrieval_study(prepared):
    """Check captured bytes and current code at controller claim/commit boundaries."""
    _check_artifacts(prepared)
    request = _json(prepared["artifacts"].get("request", b""))
    _request_fields(request)
    for role, raw in _current_sources(request["schema_version"] == 3).items():
        if prepared["artifacts"].get(role) != raw:
            raise ValueError("Prepared study validation implementation changed")


def _chain(events):
    if type(events) is not list or not 1 <= len(events) <= MAX_PREFIX_EVENTS:
        raise ValueError("Evidence prefix exceeds event bound")
    if len(_raw(events)) > MAX_PREFIX_BYTES:
        raise ValueError("Evidence prefix exceeds metadata bound")
    previous, last_seq, last_time, ids = "0" * 64, 0, None, set()
    for event in events:
        _keys(event, {"seq", "id", "kind", "recorded_at", "body", "previous_hash", "hash"}, "prefix event")
        if type(event["seq"]) is not int or event["seq"] <= last_seq or event["id"] in ids:
            raise ValueError("Invalid evidence prefix ordering or duplicate ID")
        if event["previous_hash"] != previous:
            raise ValueError("Evidence prefix chain mismatch")
        assertions._event_integrity(event)
        now = instant(event["recorded_at"])
        if last_time is not None and now < last_time:
            raise ValueError("Evidence prefix clock regressed")
        previous, last_seq, last_time = event["hash"], event["seq"], now
        ids.add(event["id"])
    return {"seq": events[-1]["seq"], "id": events[-1]["id"], "hash": events[-1]["hash"]}


def _run_artifact_refs(terminal):
    body = terminal["body"]
    if type(body) is not dict or type(body.get("schema_version")) is not int or body["schema_version"] not in (1, 2):
        raise ValueError("Unsupported captured receipt schema")
    version = body["schema_version"]
    artifacts = body["artifacts"]
    fields = {"config", "queries", "implementation", "dependencies"}
    _keys(artifacts, fields if version == 1 else fields | {"recipe", "projection", "stdlib"}, "retained run artifacts")
    _keys(artifacts["dependencies"], retrieval.DEPENDENCY_NAMES if version == 1 else retrieval.DEPENDENCY_NAMES_V2, "retained dependencies")
    refs = [artifacts["config"], artifacts["queries"], artifacts["implementation"], *artifacts["dependencies"].values()]
    if version == 2:
        _keys(artifacts["stdlib"], retrieval.STDLIB_NAMES, "retained stdlib")
        descriptor = artifacts["projection"]
        _keys(descriptor, {"schema_version", "sha256", "size", "chunks"}, "captured projection descriptor")
        if (type(descriptor["schema_version"]) is not int or descriptor["schema_version"] != 1
                or type(descriptor["size"]) is not int or not 1 <= descriptor["size"] <= retrieval.MAX_PROJECTION_BYTES
                or type(descriptor["chunks"]) is not list or not 1 <= len(descriptor["chunks"]) <= retrieval.MAX_PROJECTION_CHUNKS):
            raise ValueError("Invalid bounded captured projection descriptor")
        _hash(descriptor["sha256"])
        total = 0
        for ref in descriptor["chunks"]:
            _keys(ref, retrieval.REF_FIELDS, "captured projection chunk")
            if type(ref["size"]) is not int or not 1 <= ref["size"] <= MAX_INPUT_BYTES:
                raise ValueError("Captured projection chunk exceeds byte bound")
            total += ref["size"]
            if total > descriptor["size"]:
                raise ValueError("Captured projection exceeds aggregate bound")
        if total != descriptor["size"]:
            raise ValueError("Captured projection chunk size mismatch")
        refs.extend([artifacts["recipe"], *artifacts["stdlib"].values(), *descriptor["chunks"]])
    return refs


def _capture(evidence_ledger, request, cohort, declared_contract, *, request_raw=None, cohort_raw=None, protocol_raw=None, review_raw=None):
    _inputs(request, cohort, declared_contract)
    if type(evidence_ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Assessment requires the current Ledger class")
    if evidence_ledger.root.resolve() != Path(request["evidence_store"]).resolve():
        raise ValueError("Evidence ledger differs from requested store")
    if evidence_ledger.root.is_symlink() or (evidence_ledger.root / "blobs").is_symlink():
        raise ValueError("Evidence roots must not be symlinks")
    artifacts = {"request": _raw(request) if request_raw is None else request_raw,
                 "cohort": _raw(cohort) if cohort_raw is None else cohort_raw,
                 "declared_contract": _raw(declared_contract), **_current_sources(request["schema_version"] == 3)}
    if request["schema_version"] == 2:
        protocol_raw = _read_file(request["protocol_file"], MAX_INPUT_BYTES) if protocol_raw is None else protocol_raw
        if type(protocol_raw) is not bytes or len(protocol_raw) > MAX_INPUT_BYTES or digest(protocol_raw) != declared_contract["protocol_hash"]:
            raise ValueError("Comparison protocol differs from declared bytes")
        artifacts["comparison_protocol"] = protocol_raw
    if request["schema_version"] == 3:
        protocol_raw = _read_file(request["protocol_file"], MAX_INPUT_BYTES) if protocol_raw is None else protocol_raw
        review_raw = _read_file(request["review_file"], MAX_INPUT_BYTES) if review_raw is None else review_raw
        for name, raw in (("protocol", protocol_raw), ("review", review_raw)):
            if type(raw) is not bytes or len(raw) > MAX_INPUT_BYTES or digest(raw) != declared_contract[name + "_hash"]:
                raise ValueError("Coverage " + name + " differs from declared original bytes")
            artifacts["coverage_" + name] = raw
    if _json(artifacts["request"]) != request or _json(artifacts["cohort"]) != cohort:
        raise ValueError("Captured file bytes differ from parsed input")
    with assertions._read_transaction(evidence_ledger):
        selected = [request["corpus_id"], *_run_ids(request)]
        if request["schema_version"] == 3:
            selected.extend([request["freeze_event_id"], declared_contract["reference_terminal"]["id"]])
        seqs = []
        for event_id in selected:
            row = evidence_ledger.db.execute("SELECT seq FROM events WHERE id=?", (event_id,)).fetchone()
            if row is None:
                raise ValueError("Missing selected retrieval event")
            seqs.append(row["seq"])
        end = max(seqs)
        if request["schema_version"] == 3 and request["phase"] == "preparation":
            freeze_seq = evidence_ledger.db.execute("SELECT seq FROM events WHERE id=?", (request["freeze_event_id"],)).fetchone()["seq"]
            if end != freeze_seq:
                raise ValueError("Coverage preparation reference and corpus must precede freeze")
        # Inspect lengths in SQLite before deserializing attacker-sized event JSON.
        sizes = evidence_ledger.db.execute("SELECT COUNT(*), COALESCE(SUM(length(CAST(body AS BLOB)) + length(CAST(id AS BLOB)) + length(CAST(kind AS BLOB)) + length(CAST(recorded_at AS BLOB)) + length(CAST(previous_hash AS BLOB)) + length(CAST(hash AS BLOB)) + 256), 0) FROM events WHERE seq<=?", (end,)).fetchone()
        if sizes[0] > MAX_PREFIX_EVENTS or sizes[1] > MAX_PREFIX_BYTES:
            raise ValueError("Evidence prefix exceeds capture bound")
        events = []
        for row in evidence_ledger.db.execute("SELECT * FROM events WHERE seq<=? ORDER BY seq", (end,)):
            event = dict(row)
            event["body"] = _json(event["body"])
            events.append(event)
        head = _chain(events)
        by_id = {event["id"]: event for event in events}
        try:
            corpus = by_id[request["corpus_id"]]
            refs = corpus["body"]["sources"]
            if type(refs) is not list or not 1 <= len(refs) <= retrieval.MAX_SOURCES:
                raise ValueError("Invalid bounded source selection")
            if any(type(ref) is not dict or type(ref.get("size")) is not int or not 0 <= ref["size"] <= MAX_INPUT_BYTES for ref in refs):
                raise ValueError("Invalid bounded source sizes")
            if sum(ref["size"] for ref in refs) > retrieval.MAX_TOTAL_BYTES:
                raise ValueError("Selected source bytes exceed 4 MB")
            refs = list(refs)
            if request["schema_version"] == 3:
                freeze = by_id[request["freeze_event_id"]]
                retrieval_coverage._keys(freeze["body"], retrieval_coverage.FREEZE_FIELDS, "captured coverage freeze")
                retrieval_coverage._keys(freeze["body"]["artifacts"], {"cohort", "protocol", "review"}, "coverage freeze artifacts")
                refs.extend(freeze["body"]["artifacts"].values())
                refs.extend(_run_artifact_refs(by_id[declared_contract["reference_terminal"]["id"]]))
            for terminal_id in _run_ids(request):
                terminal = by_id[terminal_id]
                refs.extend(_run_artifact_refs(terminal))
            blobs = {}
            total = sum(len(raw) for raw in artifacts.values()) + len(_raw(events))
            for ref in refs:
                _keys(ref, {"observation_id", "event_hash", "content_hash", "size"}, "captured observation reference")
                _hash(ref["content_hash"])
                if type(ref["size"]) is not int or not 0 <= ref["size"] <= MAX_INPUT_BYTES:
                    raise ValueError("Source or execution artifact exceeds 1 MB")
                observation = by_id[ref["observation_id"]]
                if (observation["kind"] != "observation" or observation["hash"] != ref["event_hash"]
                        or observation["body"]["content_hash"] != ref["content_hash"]
                        or observation["body"]["size"] != ref["size"]):
                    raise ValueError("Captured observation binding mismatch")
                name = "blob:" + ref["content_hash"]
                if name not in artifacts:
                    if len(artifacts) + 2 > MAX_ARTIFACTS:  # also reserve the evidence-bundle role
                        raise ValueError("Too many captured assessment artifacts")
                    total += ref["size"]
                    if total > MAX_BUNDLE_BYTES:
                        raise ValueError("Assessment bundle exceeds aggregate byte bound")
                    raw = _read_file(evidence_ledger.root / "blobs" / ref["content_hash"], ref["size"])
                    if len(raw) != ref["size"] or digest(raw) != ref["content_hash"]:
                        raise ValueError("Captured blob hash or size mismatch")
                    artifacts[name] = raw
                blobs[ref["content_hash"]] = ref["size"]
        except (KeyError, TypeError, IndexError) as error:
            raise ValueError("Invalid retrieval evidence bundle") from error
    artifacts["evidence_bundle"] = _raw({"schema_version": 1, "events": events, "prefix_head": head, "blobs": blobs})
    prepared = {"artifacts": artifacts, "manifest": {role: digest(raw) for role, raw in artifacts.items()}}
    check_prepared_retrieval_study(prepared)
    return prepared


def prepare_retrieval_study(study_path, *, declared_contract, forbidden_store=None):
    """Capture bounded files and one coherent evidence prefix for later assessment."""
    request_raw = _read_file(study_path, MAX_INPUT_BYTES)
    request = _json(request_raw)
    _request_fields(request)
    _id(request["cohort_file"], "cohort file")
    _id(request["evidence_store"], "evidence store")
    evidence_root = Path(request["evidence_store"])
    if not evidence_root.is_absolute() or not Path(request["cohort_file"]).is_absolute():
        raise ValueError("Study paths must be absolute")
    if evidence_root.is_symlink() or (evidence_root / "ledger.sqlite").is_symlink() or (evidence_root / "blobs").is_symlink():
        raise ValueError("Evidence store must not use substituted symlink roots")
    if forbidden_store is not None:
        forbidden = Path(forbidden_store)
        if evidence_root.resolve() == forbidden.resolve() or ((forbidden / "ledger.sqlite").exists()
                and os.path.samefile(evidence_root / "ledger.sqlite", forbidden / "ledger.sqlite")):
            raise ValueError("Evidence and improvement stores must be distinct")
    cohort_raw = _read_file(request["cohort_file"], MAX_INPUT_BYTES)
    cohort = _json(cohort_raw)
    evidence = Ledger.open_readonly(evidence_root)
    try:
        return _capture(evidence, request, cohort, declared_contract, request_raw=request_raw, cohort_raw=cohort_raw)
    finally:
        evidence.close()


def _identity(value):
    return {**deepcopy(value), "hash": digest(_raw(value))}


def _candidate(report):
    return deepcopy(report["identity"]["candidate"])


def _measurement(report):
    identity = report["identity"]
    if report.get("evaluation") == retrieval_coverage.CONTRACT_ID:
        return _coverage_measurement(identity)
    return _identity({key: identity[key] for key in ("snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
        "corpus_id", "corpus_hash", "sources_hash", "passages_hash", "cohort_hash", "gold_hash", "query_hash", "config_hash", "evaluator")}
        | {"citation_semantics": "complete-raw-source-window-v1",
           "comparison_rule": "Current neutral validation/scoring identity; historical reports retain their original implementation identity."})


def _declared(report, contract, *, arm=None):
    identity = report["identity"]
    for key in ("snapshot_id", "snapshot_hash", "snapshot_manifest_hash", "corpus_id", "corpus_hash",
                "cohort_hash", "gold_hash", "query_hash", "sources_hash", "passages_hash", "config_hash"):
        if identity[key] != contract[key]:
            raise ValueError(f"Retrieval evidence differs from declared {key}")
    if contract["schema_version"] == 1:
        if (identity["retriever_implementation_hash"] != contract["implementation_hash"]
                or identity["retriever_runtime_hash"] != contract["runtime_hash"]
                or {name: ref["content_hash"] for name, ref in identity["retriever_artifacts"]["dependencies"].items()} != contract["dependency_hashes"]):
            raise ValueError("Historical candidate differs from declared implementation, dependencies or runtime")
        terminal_hashes = contract["run_terminal_hashes"]
    else:
        declaration = contract["arms"][arm]
        candidate = identity["candidate"]
        if (identity["receipt_schema_version"] != 2
                or candidate["algorithm"]["indexing_recipe"] != declaration["indexing_recipe"]
                or candidate["algorithm_hash"] != declaration["candidate_algorithm_hash"]):
            raise ValueError("Comparison arm differs from declared v2 candidate algorithm")
        if declaration["projection_hashes"][identity["run_terminal_id"]] != candidate["projection"]["sha256"]:
            raise ValueError("Comparison projection differs from declared observed hash")
        terminal_hashes = declaration["run_terminal_hashes"]
    if terminal_hashes.get(identity["run_terminal_id"]) != identity["run_terminal_hash"]:
        raise ValueError("Run terminal differs from declared hash")


def _pair(runs, reports):
    candidates = [_candidate(report) for report in reports]
    if candidates[0]["algorithm"] != candidates[1]["algorithm"]:
        raise ValueError("Retrieval pair has different candidate identities")
    if _measurement(reports[0]) != _measurement(reports[1]):
        raise ValueError("Retrieval pair has different measurement contracts")
    equal_results = _raw(runs[0]["body"]["results"]) == _raw(runs[1]["body"]["results"])
    equal_evaluations = all(reports[0][key] == reports[1][key] for key in ("counts", "metrics", "per_case"))
    equal_projection = candidates[0]["projection"] == candidates[1]["projection"]
    return {"required_runs": 2, "valid_runs": 2, "ordered_results_equal": equal_results,
            "evaluations_equal": equal_evaluations, "projections_equal": equal_projection,
            "value": int(equal_results and equal_evaluations and equal_projection),
            "assurance": "Two distinct locally retained execution claims; historical receipt validation, not a new search, process isolation proof or independent witness."}


def _quality_delta(raw, html):
    def compare(a, b):
        return {"raw": deepcopy(a), "html": deepcopy(b),
                "change": None if a["value"] is None or b["value"] is None else b["value"] - a["value"]}
    metrics = {}
    for name in ("source_recall_at_k", "gold_span_recall_at_k"):
        metrics[name] = {cutoff: compare(raw["metrics"][name][cutoff], html["metrics"][name][cutoff]) for cutoff in ("1", "3", "5")}
    for name in ("source_mrr_at_5", "gold_span_mrr_at_5", "unsupported_query_retrieval_rate_at_5", "empty_query_rate"):
        metrics[name] = compare(raw["metrics"][name], html["metrics"][name])
    return {"metrics": metrics, "interpretation": "Descriptive builder-visible development changes; unsupported retrieval is not answer hallucination and BM25 magnitudes are not cross-arm confidence."}


def _case_changes(raw_run, html_run, raw_report, html_report):
    rows = []
    for raw, html, raw_score, html_score in zip(raw_run["body"]["results"], html_run["body"]["results"], raw_report["per_case"], html_report["per_case"]):
        def arm(result, score):
            return {"status": result["status"], "reason": result["reason"],
                    "ranked_windows": [{key: hit[key] for key in ("rank", "observation_id", "start", "end", "sha256")} for hit in result["hits"]],
                    "source_recall_at_k": deepcopy(score["source_recall_at_k"]),
                    "gold_span_recall_at_k": deepcopy(score["gold_span_recall_at_k"]),
                    "gold_span_first_covered_prefix_at_5": score["gold_span_first_covered_prefix_at_5"]}
        rows.append({"query_id": raw["query_id"], "answerability": raw_score["answerability"],
                     "raw": arm(raw, raw_score), "html": arm(html, html_score)})
    return rows


def _costs(runs):
    return {"runs": [{"run_terminal_id": run["id"], "resources": deepcopy(run["body"]["resources"])} for run in runs],
            "reported_inner_elapsed_seconds_sum": sum(run["body"]["resources"]["elapsed_seconds"] for run in runs),
            "model_calls": sum(run["body"]["resources"]["model_calls"] for run in runs),
            "external_spend": sum(run["body"]["resources"]["external_spend"] for run in runs),
            "outer_wall_seconds": None, "whole_step_cost": None,
            "scope": "Receipt-reported inner times exclude locked revalidation and commit; outer caller records are separate. Builder/reviewer and whole-step costs are unmeasured."}


def _coverage_measurement(identity):
    return _identity({key: identity[key] for key in ("snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
        "corpus_id", "corpus_hash", "sources_hash", "passages_hash", "cohort_hash", "gold_hash", "query_hash", "config_hash", "evaluator")}
        | {"citation_semantics": "complete-raw-source-window-v1", "support_semantics": "any_complete_bundle_v1", "pair_bucket_cutoff": 5})


def _assess_coverage(ledger, request, contract, prepared, artifacts, bundle):
    found = retrieval_coverage.get_coverage_freeze(ledger, request["freeze_event_id"])
    event, ready = found["event"], found["preparation"]
    body = event["body"]
    expected = {**ready["lineage"], "study_id": body["study_id"], "protocol_hash": ready["file_hashes"]["protocol"],
        "review_hash": ready["file_hashes"]["review"], "freeze_event_hash": event["hash"],
        "reference_terminal": body["reference_terminal"], "candidate_algorithm_hash": body["candidate_algorithm_hash"],
        "evaluator_identity_hash": body["evaluator_identity_hash"], "runtime_hash": body["runtime_hash"]}
    if any(contract[key] != value for key, value in expected.items()):
        raise ValueError("Coverage freeze differs from declared lineage or identity")
    for role, artifact in (("cohort", "cohort"), ("protocol", "coverage_protocol"), ("review", "coverage_review")):
        if digest(artifacts[artifact]) != ready["file_hashes"][role]:
            raise ValueError("Coverage input file differs from frozen original bytes")
    measurement = _coverage_measurement({**ready["lineage"], "evaluator": ready["evaluator_identity"]})
    identity = _identity({"adapter_hash": digest(IMPLEMENTATION_SOURCE), "helper_hash": digest(retrieval_coverage.IMPLEMENTATION_SOURCE),
        "prepared_manifest": prepared["manifest"], "declared_contract_hash": digest(artifacts["declared_contract"]),
        "protocol_hash": contract["protocol_hash"], "review_hash": contract["review_hash"], "freeze_event_hash": event["hash"]})
    report = {"schema_version": 3, "phase": request["phase"], "status": "ready" if request["phase"] == "preparation" else "completed",
        "scope": "fresh_builder_visible_development", "study_id": request["study_id"],
        "preparation": {"freeze": {"id": event["id"], "hash": event["hash"]},
            "reference_terminal": deepcopy(body["reference_terminal"]), "run_keys": list(body["run_keys"]), **deepcopy(ready["inventory"])},
        "candidate_identity": deepcopy(ready["candidate_identity"]), "measurement_contract_identity": measurement,
        "assessment_identity": identity, "input_bindings": {"prefix_head": bundle["prefix_head"],
            "request_hash": digest(artifacts["request"]), "cohort_file_hash": digest(artifacts["cohort"]),
            "protocol_file_hash": digest(artifacts["coverage_protocol"]), "review_file_hash": digest(artifacts["coverage_review"]),
            "declared_contract_hash": digest(artifacts["declared_contract"]), "corpus_id": request["corpus_id"],
            "freeze_event_id": event["id"], "reference_terminal_id": body["reference_terminal"]["id"]}}
    if request["phase"] == "evaluation":
        ids = [f"retrieval:{key}:terminal" for key in body["run_keys"]]
        if request["run_terminal_ids"] != ids:
            raise ValueError("Coverage executions differ from frozen run keys/order")
        runs, reports = [], []
        for terminal_id in ids:
            run = retrieval.get_retrieval_run(ledger, terminal_id, verify_bytes=True)
            scored = retrieval_evaluation.evaluate_retrieval(ledger, ready["cohort"], terminal_id)
            if run["hash"] != contract["run_terminal_hashes"][terminal_id] or run["body"]["projection_hash"] != contract["projection_hashes"][terminal_id]:
                raise ValueError("Coverage output differs from declared observed hash")
            if _measurement(scored) != measurement:
                raise ValueError("Coverage evaluation changed the frozen measurement identity")
            runs.append(run)
            reports.append(scored)
        reproduced = _pair(runs, reports)
        # Pair equality includes every new coverage diagnostic, not just the old
        # metrics/per-case projection. None is selected from a differing repeat.
        reproduced["evaluations_equal"] = reproduced["evaluations_equal"] and all(
            reports[0][key] == reports[1][key] for key in ("matched_pairs", "pair_buckets", "families", "relations", "feature_inventory"))
        reproduced["value"] = int(reproduced["ordered_results_equal"] and reproduced["evaluations_equal"] and reproduced["projections_equal"])
        report.update(reproducibility=reproduced, quality={"runs": reports}, costs=_costs(runs),
            candidate_identity=_candidate(reports[0]), coverage={"contract_id": retrieval_coverage.CONTRACT_ID,
                "candidate_baseline": "raw", "adoption": "none", "matched_pairs": reports[0]["matched_pairs"] if reproduced["value"] else None,
                "pair_buckets": reports[0]["pair_buckets"] if reproduced["value"] else None})
        report["input_bindings"]["run_terminal_ids"] = ids
        for index, scored in enumerate(reports, 1):
            artifacts[f"evaluation:{index}"] = _raw(scored)
    check_prepared_retrieval_study(prepared)
    artifacts["assessment_report"] = _raw(report)
    _check_artifacts({"artifacts": artifacts, "manifest": {role: digest(raw) for role, raw in artifacts.items()}})
    return {"report": report, "artifacts": artifacts}


def assess_prepared_retrieval_study(prepared):
    """Validate captured evidence in a temporary store; never re-read source paths."""
    check_prepared_retrieval_study(prepared)
    artifacts = dict(prepared["artifacts"])
    try:
        request, cohort, contract, bundle = (_json(artifacts[name]) for name in
            ("request", "cohort", "declared_contract", "evidence_bundle"))
    except KeyError as error:
        raise ValueError("Prepared study lacks required artifacts") from error
    _inputs(request, cohort, contract)
    _keys(bundle, {"schema_version", "events", "prefix_head", "blobs"}, "captured evidence bundle")
    if type(bundle["schema_version"]) is not int or bundle["schema_version"] != 1 or _chain(bundle["events"]) != bundle["prefix_head"]:
        raise ValueError("Captured evidence prefix mismatch")
    if type(bundle["blobs"]) is not dict or len(bundle["blobs"]) > MAX_ARTIFACTS:
        raise ValueError("Invalid captured blob manifest")
    expected_roles = {"request", "cohort", "declared_contract", "evidence_bundle", *_current_sources(request["schema_version"] == 3)}
    if request["schema_version"] == 2:
        expected_roles.add("comparison_protocol")
        protocol = artifacts.get("comparison_protocol")
        if type(protocol) is not bytes or len(protocol) > MAX_INPUT_BYTES or digest(protocol) != contract["protocol_hash"]:
            raise ValueError("Captured comparison protocol differs from declared bytes")
    if request["schema_version"] == 3:
        for role in ("protocol", "review"):
            expected_roles.add("coverage_" + role)
            raw = artifacts.get("coverage_" + role)
            if type(raw) is not bytes or len(raw) > MAX_INPUT_BYTES or digest(raw) != contract[role + "_hash"]:
                raise ValueError("Captured coverage file differs from declared bytes")
    expected_roles.update("blob:" + h for h in bundle["blobs"])
    if set(artifacts) != expected_roles:
        raise ValueError("Unexpected or missing captured artifacts")
    reports, runs, starts = [], [], []
    with tempfile.TemporaryDirectory(prefix="epiphysics-retrieval-assessment-") as directory:
        ledger = Ledger(directory)
        try:
            for content_hash, size in bundle["blobs"].items():
                _hash(content_hash)
                raw = artifacts["blob:" + content_hash]
                if type(size) is not int or not 0 <= size <= MAX_INPUT_BYTES or len(raw) != size or digest(raw) != content_hash:
                    raise ValueError("Captured blob size or hash mismatch")
                (ledger.root / "blobs" / content_hash).write_bytes(raw)
            ledger.db.executemany("INSERT INTO events(seq,id,kind,recorded_at,body,previous_hash,hash) VALUES(?,?,?,?,?,?,?)",
                [(e["seq"], e["id"], e["kind"], e["recorded_at"], canonical(e["body"]), e["previous_hash"], e["hash"]) for e in bundle["events"]])
            ledger.db.commit()
            ledger.db.execute("PRAGMA query_only=ON")
            if request["schema_version"] == 3:
                return _assess_coverage(ledger, request, contract, prepared, artifacts, bundle)
            for terminal_id in _run_ids(request):
                run = retrieval.get_retrieval_run(ledger, terminal_id, verify_bytes=True)
                report = retrieval_evaluation.evaluate_retrieval(ledger, cohort, terminal_id)
                arm = None if request["schema_version"] == 1 else next(name for name in ARM_RECIPES if terminal_id in request["arms"][name]["run_terminal_ids"])
                _declared(report, contract, arm=arm)
                runs.append(run)
                starts.append(ledger.get(f"retrieval:{run['body']['run_key']}:started", "retrieval_started"))
                reports.append(report)
        finally:
            ledger.close()
    required = 2 if request["schema_version"] == 1 else 4
    if len({run["body"]["run_key"] for run in runs}) != required:
        raise ValueError("Distinct execution claims are required for every retained run")
    candidates = [_candidate(report) for report in reports]
    measurements = [_measurement(report) for report in reports]
    if any(value != measurements[0] for value in measurements[1:]):
        raise ValueError("All retained runs must share the current measurement contract")
    assessment_identity = {"adapter_hash": digest(IMPLEMENTATION_SOURCE), "prepared_manifest": prepared["manifest"],
                           "declared_contract_hash": digest(artifacts["declared_contract"])}
    if request["schema_version"] == 1:
        reproduction = _pair(runs, reports)
        candidate = candidates[0]
        comparison = None
    else:
        if any(starts[index]["seq"] <= runs[index - 1]["seq"] for index in range(1, 4)):
            raise ValueError("Comparison executions must follow the fixed raw A/B then HTML A/B order")
        # Indexing recipe is the only changed algorithm input. Parser, query,
        # tokenizer/runtime, source-validation closure and runner stay frozen.
        algorithms = [{key: value for key, value in candidates[index]["algorithm"].items()
                       if key not in {"indexing_recipe", "recipe"}} for index in (0, 2)]
        if algorithms[0] != algorithms[1]:
            raise ValueError("Comparison arms changed more than the fixed indexing recipe")
        if len({run["body"]["implementation_hash"] for run in runs}) != 1:
            raise ValueError("Comparison execution runner differs across arms")
        arms = {}
        for index, name in ((0, "raw"), (2, "html")):
            arms[name] = {"indexing_recipe": ARM_RECIPES[name], "run_terminal_ids": _run_ids(request)[index:index+2],
                          "reproducibility": _pair(runs[index:index+2], reports[index:index+2]),
                          "candidate_identities": candidates[index:index+2]}
        passed = all(arm["reproducibility"]["value"] == 1 for arm in arms.values())
        reproduction = {"required_runs": 4, "valid_runs": 4,
            "ordered_results_equal": all(arm["reproducibility"]["ordered_results_equal"] for arm in arms.values()),
            "evaluations_equal": all(arm["reproducibility"]["evaluations_equal"] for arm in arms.values()),
            "projections_equal": all(arm["reproducibility"]["projections_equal"] for arm in arms.values()),
            "value": int(passed), "assurance": "Two distinct local repeats per fixed arm under one current measurement contract; no independent execution witness or holdout claim."}
        candidate = _identity({"raw": candidates[0], "html": candidates[2]})
        comparison = {"kind": "fixed-raw-html-v1", "arms": arms, "status": "reproduced" if passed else "reproduction_failed",
                      "delta": _quality_delta(reports[0], reports[2]) if passed else None,
                      "per_case_changes": _case_changes(runs[0], runs[2], reports[0], reports[2]) if passed else None,
                      "operational_baseline": "raw", "adoption": "not_authorized",
                      "continuation": "fresh_question_coverage_after_valid_comparison"}
        assessment_identity["protocol_hash"] = contract["protocol_hash"]
    report = {"schema_version": request["schema_version"], "status": "completed", "scope": "retrospective_development", "study_id": request["study_id"],
        "reproducibility": reproduction, "quality": {"runs": reports}, "candidate_identity": candidate,
        "measurement_contract_identity": measurements[0], "assessment_identity": _identity(assessment_identity),
        "costs": _costs(runs),
        "input_bindings": {"prefix_head": bundle["prefix_head"], "run_terminal_ids": _run_ids(request),
            "request_hash": digest(artifacts["request"]), "cohort_file_hash": digest(artifacts["cohort"]),
            "declared_contract_hash": digest(artifacts["declared_contract"]), "corpus_id": request["corpus_id"]},
        "limitations": ["Current neutral validation/scoring identity does not replace the original identity of historical reports.",
                        "Builder-visible development data; recipe proposal followed inspection of baseline errors.",
                        "Returned raw-window support does not imply every gold byte survived projection or that an answer was generated."]}
    if comparison is not None:
        report["comparison"] = comparison
    check_prepared_retrieval_study(prepared)
    for index, evaluated in enumerate(reports, 1):
        artifacts[f"evaluation:{index}"] = _raw(evaluated)
    artifacts["assessment_report"] = _raw(report)
    _check_artifacts({"artifacts": artifacts, "manifest": {name: digest(raw) for name, raw in artifacts.items()}})
    return {"report": report, "artifacts": artifacts}


def assess_retrieval_study(evidence_ledger, request, cohort, *, declared_contract):
    """Assess two actual captured receipts without mutating the evidence ledger."""
    return assess_prepared_retrieval_study(_capture(evidence_ledger, request, cohort, declared_contract))


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
