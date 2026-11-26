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

from . import assertions, manifests, retrieval, retrieval_evaluation, store
from .store import Ledger, canonical, digest, instant

IMPLEMENTATION_DEPENDENCIES = tuple((m.__name__, m.IMPLEMENTATION_CODE)
    for m in (store, assertions, manifests, retrieval, retrieval_evaluation))
MAX_ARTIFACTS = 128
MAX_ARTIFACT_BYTES = 4_000_000
MAX_BUNDLE_BYTES = 16_000_000
MAX_INPUT_BYTES = 1_000_000
MAX_PREFIX_EVENTS = 256
MAX_PREFIX_BYTES = 4_000_000
REQUEST_FIELDS = {"schema_version", "study_id", "evidence_store", "cohort_file", "corpus_id", "run_terminal_ids"}
CONTRACT_FIELDS = {"schema_version", "study_id", "snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
    "corpus_id", "corpus_hash", "cohort_hash", "gold_hash", "query_hash", "sources_hash", "passages_hash",
    "config_hash", "implementation_hash", "dependency_hashes", "runtime_hash", "run_terminal_hashes"}
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
    if type(value) is not dict or set(value) != fields:
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


def _inputs(request, cohort, declared_contract):
    _keys(request, REQUEST_FIELDS, "study request")
    _keys(declared_contract, CONTRACT_FIELDS, "declared retrieval contract")
    for item in (request, declared_contract):
        if type(item["schema_version"]) is not int or item["schema_version"] != 1:
            raise ValueError("Assessment schema_version must be 1")
        for key in ("study_id", "corpus_id"):
            _id(item[key], key)
        if len(_raw(item)) > MAX_INPUT_BYTES:
            raise ValueError("Assessment input exceeds 1 MB")
    for key in ("evidence_store", "cohort_file"):
        _id(request[key], key)
        if not Path(request[key]).is_absolute():
            raise ValueError("Study paths must be absolute")
    runs = request["run_terminal_ids"]
    if type(runs) is not list or len(runs) != 2:
        raise ValueError("Exactly two terminal IDs are required")
    for terminal_id in runs:
        _id(terminal_id, "terminal ID")
    if len(set(runs)) != 2:
        raise ValueError("Two distinct terminal IDs are required")
    for key in ("study_id", "corpus_id"):
        if request[key] != declared_contract[key]:
            raise ValueError(f"Study differs from declared {key}")
    _id(declared_contract["snapshot_id"], "snapshot ID")
    for key in CONTRACT_FIELDS - {"schema_version", "study_id", "snapshot_id", "corpus_id", "dependency_hashes", "run_terminal_hashes"}:
        _hash(declared_contract[key])
    _keys(declared_contract["dependency_hashes"], set(retrieval.DEPENDENCY_NAMES), "dependency hashes")
    _keys(declared_contract["run_terminal_hashes"], set(runs), "terminal hashes")
    for value in [*declared_contract["dependency_hashes"].values(), *declared_contract["run_terminal_hashes"].values()]:
        _hash(value)
    if len(_raw(cohort)) > MAX_INPUT_BYTES:
        raise ValueError("Cohort exceeds 1 MB")
    retrieval_evaluation.project_queries(cohort)


def _current_sources():
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
    sources[__name__] = source
    return {"code:" + name: raw for name, raw in sources.items()}


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
    for role, raw in _current_sources().items():
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


def _capture(evidence_ledger, request, cohort, declared_contract, *, request_raw=None, cohort_raw=None):
    _inputs(request, cohort, declared_contract)
    if type(evidence_ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Assessment requires the current Ledger class")
    if evidence_ledger.root.resolve() != Path(request["evidence_store"]).resolve():
        raise ValueError("Evidence ledger differs from requested store")
    if evidence_ledger.root.is_symlink() or (evidence_ledger.root / "blobs").is_symlink():
        raise ValueError("Evidence roots must not be symlinks")
    artifacts = {"request": _raw(request) if request_raw is None else request_raw,
                 "cohort": _raw(cohort) if cohort_raw is None else cohort_raw,
                 "declared_contract": _raw(declared_contract), **_current_sources()}
    if _json(artifacts["request"]) != request or _json(artifacts["cohort"]) != cohort:
        raise ValueError("Captured file bytes differ from parsed input")
    with assertions._read_transaction(evidence_ledger):
        selected = [request["corpus_id"], *request["run_terminal_ids"]]
        seqs = []
        for event_id in selected:
            row = evidence_ledger.db.execute("SELECT seq FROM events WHERE id=?", (event_id,)).fetchone()
            if row is None:
                raise ValueError("Missing selected retrieval event")
            seqs.append(row["seq"])
        end = max(seqs)
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
            for terminal_id in request["run_terminal_ids"]:
                terminal = by_id[terminal_id]
                retained = terminal["body"]["artifacts"]
                _keys(retained, {"config", "queries", "implementation", "dependencies"}, "retained run artifacts")
                _keys(retained["dependencies"], set(retrieval.DEPENDENCY_NAMES), "retained dependencies")
                refs.extend([retained["config"], retained["queries"], retained["implementation"], *retained["dependencies"].values()])
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
    _keys(request, REQUEST_FIELDS, "study request")
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
    identity = report["identity"]
    artifacts = identity["retriever_artifacts"]
    def normalized(ref):
        return {key: ref[key] for key in ("content_hash", "size")}
    return _identity({"implementation": normalized(artifacts["implementation"]),
        "dependencies": {name: normalized(ref) for name, ref in artifacts["dependencies"].items()},
        "config": normalized(artifacts["config"]), "runtime": identity["retriever_runtime"],
        "runtime_hash": identity["retriever_runtime_hash"]})


def _declared(report, contract):
    identity = report["identity"]
    for key in ("snapshot_id", "snapshot_hash", "snapshot_manifest_hash", "corpus_id", "corpus_hash",
                "cohort_hash", "gold_hash", "query_hash", "sources_hash", "passages_hash", "config_hash"):
        if identity[key] != contract[key]:
            raise ValueError(f"Retrieval evidence differs from declared {key}")
    if (identity["retriever_implementation_hash"] != contract["implementation_hash"]
            or identity["retriever_runtime_hash"] != contract["runtime_hash"]
            or {name: ref["content_hash"] for name, ref in identity["retriever_artifacts"]["dependencies"].items()} != contract["dependency_hashes"]):
        raise ValueError("Historical candidate differs from declared implementation, dependencies or runtime")
    if contract["run_terminal_hashes"].get(identity["run_terminal_id"]) != identity["run_terminal_hash"]:
        raise ValueError("Run terminal differs from declared hash")


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
    expected_roles = {"request", "cohort", "declared_contract", "evidence_bundle", *_current_sources()}
    expected_roles.update("blob:" + h for h in bundle["blobs"])
    if set(artifacts) != expected_roles:
        raise ValueError("Unexpected or missing captured artifacts")
    reports, runs = [], []
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
            for terminal_id in request["run_terminal_ids"]:
                run = retrieval.get_retrieval_run(ledger, terminal_id, verify_bytes=True)
                report = retrieval_evaluation.evaluate_retrieval(ledger, cohort, terminal_id)
                _declared(report, contract)
                runs.append(run)
                reports.append(report)
        finally:
            ledger.close()
    if len({run["body"]["run_key"] for run in runs}) != 2:
        raise ValueError("Two distinct execution claims are required")
    candidates = [_candidate(report) for report in reports]
    if candidates[0] != candidates[1]:
        raise ValueError("Retrieval pair has different candidate identities")
    identity = reports[0]["identity"]
    measurement = _identity({key: identity[key] for key in ("snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
        "corpus_id", "corpus_hash", "sources_hash", "passages_hash", "cohort_hash", "gold_hash", "query_hash", "config_hash", "evaluator")}
        | {"coupled_candidate_hash": candidates[0]["hash"], "comparison_rule": "Current retrieval code/config couples candidate and measurement; changes are conservatively incomparable."})
    equal_results = _raw(runs[0]["body"]["results"]) == _raw(runs[1]["body"]["results"])
    equal_evaluations = all(reports[0][key] == reports[1][key] for key in ("counts", "metrics", "per_case"))
    report = {"schema_version": 1, "status": "completed", "scope": "retrospective_development", "study_id": request["study_id"],
        "reproducibility": {"required_runs": 2, "valid_runs": 2, "ordered_results_equal": equal_results,
            "evaluations_equal": equal_evaluations, "value": int(equal_results and equal_evaluations),
            "assurance": "Two distinct locally retained execution claims; historical receipt validation, not a new search, process isolation proof or independent witness."},
        "quality": {"runs": reports}, "candidate_identity": candidates[0], "measurement_contract_identity": measurement,
        "assessment_identity": _identity({"adapter_hash": digest(IMPLEMENTATION_SOURCE), "prepared_manifest": prepared["manifest"],
            "declared_contract_hash": digest(artifacts["declared_contract"])}),
        "input_bindings": {"prefix_head": bundle["prefix_head"], "run_terminal_ids": request["run_terminal_ids"],
            "request_hash": digest(artifacts["request"]), "cohort_file_hash": digest(artifacts["cohort"]),
            "declared_contract_hash": digest(artifacts["declared_contract"]), "corpus_id": request["corpus_id"]}}
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
