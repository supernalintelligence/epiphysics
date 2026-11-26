"""Fixed fresh-coverage preparation; never searches or executes retained code.

This helper is outside the scoring dependency closure. It may verify the loaded
candidate against a historical raw receipt, but cannot supply scores or answers.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifests, retrieval, retrieval_contracts as contracts, retrieval_evaluation as evaluation, retrieval_indexing, store
from .store import Ledger, canonical, digest, instant

IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE)
    for module in (store, assertions, manifests, contracts, evaluation, retrieval_indexing, retrieval))
MAX_BYTES = 1_000_000
MAX_ARTIFACTS = 128
MAX_ARTIFACT_BYTES = 4_000_000
MAX_BUNDLE_BYTES = 16_000_000
MAX_PREFIX_EVENTS = 256
MAX_PREFIX_BYTES = 4_000_000
CONTRACT_ID = "retrieval-coverage-evaluation-v2"
PROTOCOL_FIELDS = {"schema_version", "study_id", "corpus_id", "corpus_hash", "source_snapshot_hash",
    "cohort_file_sha256", "projected_queries_hash", "scoring_contract_id", "indexing_recipe", "executions",
    "expected_pairs", "cutoffs", "adoption", "scope", "exposure", "limits", "successor_rule"}
REVIEW_FIELDS = {"schema_version", "cohort_file_sha256", "corpus_hash", "curator_id", "reviewer_id",
    "reviewed_source_ids", "cases", "unresolved_case_ids"}
FREEZE_FIELDS = {"schema_version", "study_id", "corpus", "reference_terminal", "artifacts", "cohort_hash",
    "gold_hash", "query_hash", "scoring_contract_id", "evaluator_identity_hash", "candidate_algorithm_hash",
    "runtime_hash", "run_keys"}
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_MODULE_CODES = tuple((module, module.IMPLEMENTATION_CODE) for module in
    (store, assertions, manifests, contracts, evaluation, retrieval_indexing, retrieval))


def _raw(value):
    try:
        return canonical(value).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Coverage requires finite UTF-8 JSON") from error


def _json(raw, maximum=MAX_BYTES):
    if type(raw) is not bytes or len(raw) > maximum:
        raise ValueError("Coverage input must be at most 1 MB of exact bytes" if maximum == MAX_BYTES else "Coverage prefix JSON exceeds byte bound")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate coverage JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
        _raw(value)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ValueError("Invalid coverage JSON") from error


def _keys(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"Invalid {label} fields")


def _id(value, label):
    contracts._identifier(value, label)


def _text(value, label):
    evaluation._text(value, label, 8192)


def _ref(value, label):
    _keys(value, {"id", "hash"}, label)
    _id(value["id"], label + " ID")
    contracts._hash(value["hash"], label + " hash")


def implementation_source():
    """Bound and guard the helper, also used by the adapter's shared caps."""
    path, source, code = _SELF
    if IMPLEMENTATION_SOURCE != source or IMPLEMENTATION_CODE is not code:
        raise ValueError("Coverage helper reloaded; use a fresh reviewed process")
    if path.is_symlink() or not path.is_file() or path.stat().st_size != len(source) or len(source) > MAX_BYTES:
        raise ValueError("Coverage helper source changed")
    with path.open("rb") as stream:
        if stream.read(len(source) + 1) != source:
            raise ValueError("Coverage helper source changed")
    if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
        raise ValueError("Coverage executing code differs from retained bytes")
    for module, expected in _MODULE_CODES:
        if module.IMPLEMENTATION_CODE is not expected:
            raise ValueError("Coverage dependency reloaded: " + module.__name__)
    for name, function, expected in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not expected:
            raise ValueError("Coverage callable changed: " + name)
    if Ledger is not store.Ledger or canonical is not store.canonical or digest is not store.digest or instant is not store.instant:
        raise ValueError("Coverage store alias changed")
    return source


def runtime_sources():
    """Guard current helper/candidate/scorer bytes without running retrieval."""
    source = implementation_source()
    evaluation.evaluator_identity(2)
    return retrieval._merge_runtime_sources(retrieval._runtime_sources(),
        {evaluation.__name__: evaluation.IMPLEMENTATION_SOURCE, __name__: source})


def _reference(ledger, reference_terminal, corpus_id, corpus_hash):
    _ref(reference_terminal, "reference terminal")
    run = contracts.get_retrieval_run(ledger, reference_terminal["id"], verify_bytes=True)
    body = run["body"]
    if (run["hash"] != reference_terminal["hash"] or run["kind"] != "retrieval_completed"
            or body["schema_version"] != 2 or body["indexing_recipe"] != contracts.RAW_RECIPE
            or body["corpus_id"] != corpus_id or body["corpus_hash"] != corpus_hash):
        raise ValueError("Coverage reference must be the declared completed raw candidate on this corpus")
    sources = runtime_sources()
    for name, ref in {**body["artifacts"]["dependencies"], **body["artifacts"]["stdlib"]}.items():
        if name not in sources or ref["content_hash"] != digest(sources[name]) or ref["size"] != len(sources[name]):
            raise ValueError("Coverage candidate dependency differs from historical reference: " + name)
    if body["runtime"] != retrieval._runtime():
        raise ValueError("Coverage candidate runtime differs from historical reference")
    candidate = evaluation._candidate_identity(body)
    return run, {key: candidate[key] for key in ("algorithm", "algorithm_hash")}


def validate_coverage_preparation(ledger, *, cohort_raw, protocol_raw, review_raw, reference_terminal):
    """Validate original files and a fixed reference without searching or writing."""
    if type(ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Coverage requires the current Ledger class")
    sources = runtime_sources()
    cohort, protocol, review = map(_json, (cohort_raw, protocol_raw, review_raw))
    cohort = evaluation._cohort(cohort)
    if cohort["schema_version"] != 2:
        raise ValueError("Coverage preparation requires cohort schema 2")
    _keys(protocol, PROTOCOL_FIELDS, "coverage protocol")
    _keys(review, REVIEW_FIELDS, "coverage review")
    fixed = {"schema_version": 1, "scoring_contract_id": CONTRACT_ID, "indexing_recipe": contracts.RAW_RECIPE,
        "executions": 2, "expected_pairs": 6, "cutoffs": [1, 3, 5], "adoption": "none",
        "scope": "fresh_builder_visible_development", "exposure": {"prior_results_seen": True, "fresh_results_seen": False},
        "limits": {"model_calls": 0, "external_spend": 0, "assessment_seconds": 30, "dispatch_seconds": 60},
        "successor_rule": "coverage-next-v1"}
    if any(_raw(protocol[key]) != _raw(value) for key, value in fixed.items()):
        raise ValueError("Coverage protocol differs from fixed scope or limits")
    for key in ("study_id", "corpus_id"):
        _id(protocol[key], key)
    if cohort["cohort_id"] != protocol["study_id"]:
        raise ValueError("Coverage study and cohort IDs differ")
    for key in ("corpus_hash", "source_snapshot_hash", "cohort_file_sha256", "projected_queries_hash"):
        contracts._hash(protocol[key], key)
    if type(review["schema_version"]) is not int or review["schema_version"] != 1:
        raise ValueError("Coverage review schema_version must be 1")
    if protocol["cohort_file_sha256"] != digest(cohort_raw) or review["cohort_file_sha256"] != digest(cohort_raw):
        raise ValueError("Coverage original cohort file hash differs")
    if review["corpus_hash"] != protocol["corpus_hash"]:
        raise ValueError("Coverage review corpus differs")
    for key in ("curator_id", "reviewer_id"):
        _id(review[key], key)
    if review["curator_id"] == review["reviewer_id"] or review["unresolved_case_ids"] != []:
        raise ValueError("Coverage requires distinct curator/reviewer and no unresolved cases")
    identities = evaluation.cohort_identity(cohort)
    queries = evaluation.project_queries(cohort)
    contracts._queries(queries)
    if identities["query_hash"] != protocol["projected_queries_hash"]:
        raise ValueError("Coverage protocol queries differ")
    with assertions._read_transaction(ledger):
        run, candidate = _reference(ledger, reference_terminal, protocol["corpus_id"], protocol["corpus_hash"])
        corpus, _ = contracts._checked_corpus(ledger, protocol["corpus_id"], instant(ledger.clock()), verify_bytes=True)
        cb = corpus["body"]
        if cb["config"]["top_k"] < max(evaluation.CUTOFFS):
            raise ValueError("Coverage readiness requires top_k at least the maximum scoring cutoff")
        if (corpus["hash"] != protocol["corpus_hash"] or cb["snapshot_hash"] != protocol["source_snapshot_hash"]
                or cb["snapshot_id"] != cohort["snapshot_id"]):
            raise ValueError("Coverage source snapshot or corpus differs")
        evaluation.validate_coverage_sources(ledger, cohort, corpus)
        selected = [ref["observation_id"] for ref in cb["sources"]]
        inventory = evaluation.coverage_inventory(cohort, selected)
        if inventory["counts"] != {"queries": 12, "answerable": 6, "unanswerable": 6, "pairs": 6, "selected_sources": 4}:
            raise ValueError("Coverage protocol requires exactly four sources and six matched pairs")
        if set(oid for pair in cohort["pairs"] for oid in pair["anchor_observation_ids"]) != set(selected):
            raise ValueError("Coverage pairs must anchor every selected source")
        reviewed = review["reviewed_source_ids"]
        if type(reviewed) is not list or len(reviewed) != len(selected) or any(type(x) is not str for x in reviewed) or set(reviewed) != set(selected):
            raise ValueError("Coverage review must inspect every selected source")
        rows = review["cases"]
        if type(rows) is not list or len(rows) != len(cohort["cases"]):
            raise ValueError("Coverage review must include every case")
        cases = {case["question_id"]: case for case in cohort["cases"]}
        seen = set()
        for row in rows:
            _keys(row, {"question_id", "decision", "reviewed_bundle_ids", "unsupported_reason",
                       "alternatives_search_note", "pair_match_note", "novelty_note"}, "coverage case review")
            _id(row["question_id"], "review question ID")
            if row["question_id"] not in cases or row["question_id"] in seen or row["decision"] != "accept":
                raise ValueError("Invalid or duplicate coverage review decision")
            seen.add(row["question_id"])
            case = cases[row["question_id"]]
            bundle_ids = [bundle["bundle_id"] for bundle in case["support_bundles"]]
            actual_ids = row["reviewed_bundle_ids"]
            if (type(actual_ids) is not list or len(actual_ids) != len(bundle_ids)
                    or any(type(x) is not str for x in actual_ids) or set(actual_ids) != set(bundle_ids)):
                raise ValueError("Coverage review omits or repeats a support bundle")
            for key in ("alternatives_search_note", "pair_match_note", "novelty_note"):
                _text(row[key], key)
            if case["answerability"] == "answerable":
                if row["unsupported_reason"] is not None:
                    raise ValueError("Supported case cannot have an unsupported rationale")
            else:
                _text(row["unsupported_reason"], "Corpus-relative unsupported reason")
        evaluator = evaluation.evaluator_identity(2)
        lineage = {key: cb[key] for key in ("snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
                    "sources_hash", "passages_hash", "config_hash")}
        lineage.update(corpus_id=corpus["id"], corpus_hash=corpus["hash"], **identities)
    if runtime_sources() != sources:
        raise ValueError("Coverage validation implementation changed")
    return {"cohort": cohort, "queries": queries, "protocol": protocol, "review": review,
        "file_hashes": {"cohort": digest(cohort_raw), "protocol": digest(protocol_raw), "review": digest(review_raw)},
        "reference_terminal": deepcopy(reference_terminal), "candidate_identity": candidate,
        "evaluator_identity": evaluator, "evaluator_identity_hash": digest(_raw(evaluator)),
        "runtime_hash": run["body"]["runtime_hash"], "lineage": lineage, "inventory": inventory}


def freeze_id(study_id):
    _id(study_id, "Study ID")
    return "coverage-freeze:" + digest(study_id.encode("utf-8"))


def _run_keys(run_keys):
    if type(run_keys) is not list or len(run_keys) != 2:
        raise ValueError("Coverage requires two distinct intended run keys")
    for key in run_keys:
        if type(key) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", key) is None:
            raise ValueError("Coverage run keys require the runner's 1–100 character alphanumeric grammar with . _ or -")
    if run_keys[0] == run_keys[1]:
        raise ValueError("Coverage run keys must be distinct")


def _body(preparation, refs, run_keys):
    return {"schema_version": 1, "study_id": preparation["protocol"]["study_id"],
        "corpus": {"id": preparation["lineage"]["corpus_id"], "hash": preparation["lineage"]["corpus_hash"]},
        "reference_terminal": preparation["reference_terminal"], "artifacts": refs,
        **{key: preparation["lineage"][key] for key in ("cohort_hash", "gold_hash", "query_hash")},
        "scoring_contract_id": CONTRACT_ID, "evaluator_identity_hash": preparation["evaluator_identity_hash"],
        "candidate_algorithm_hash": preparation["candidate_identity"]["algorithm_hash"],
        "runtime_hash": preparation["runtime_hash"], "run_keys": deepcopy(run_keys)}


def _observation_body(source, content_hash, size, media_type="application/json"):
    return {"source": source, "content_hash": content_hash, "size": size, "media_type": media_type,
        "published_at": None, "event_at": None, "revision_of": None, "timing_basis": "collector clock; source times are claims"}


def _event_bytes(kind, event_id, body_bytes):
    # Fixed collector UTC timestamps are shorter than this generous envelope.
    # This is a capture forecast under unchanged code/clock, not a reservation
    # against unrelated later writes or arbitrary replacement of the clock.
    shell = {"seq": 2**63 - 1, "id": event_id, "kind": kind, "recorded_at": "0" * 256,
             "body": None, "previous_hash": "0" * 64, "hash": "0" * 64}
    return len(_raw(shell)) - 4 + body_bytes


def _prefix_capacity(ledger, end):
    sized = ledger.db.execute("SELECT COUNT(*) AS n, COALESCE(SUM(length(CAST(body AS BLOB))+length(CAST(id AS BLOB))+length(CAST(kind AS BLOB))+length(CAST(recorded_at AS BLOB))+length(CAST(previous_hash AS BLOB))+length(CAST(hash AS BLOB))),0) AS bytes FROM events WHERE seq<=?", (end,)).fetchone()
    if sized["n"] > MAX_PREFIX_EVENTS or sized["bytes"] > MAX_PREFIX_BYTES:
        raise ValueError("Coverage prefix already exceeds capture capacity")
    total, previous, last_time = 2, "0" * 64, None
    for row in ledger.db.execute("SELECT * FROM events WHERE seq<=? ORDER BY seq", (end,)):
        event = dict(row)
        event["body"] = _json(event["body"].encode("utf-8"), MAX_PREFIX_BYTES)
        assertions._event_integrity(event)
        now = instant(event["recorded_at"])
        if event["previous_hash"] != previous or (last_time is not None and now < last_time):
            raise ValueError("Coverage prefix chain or time ordering differs")
        previous, last_time = event["hash"], now
        total += len(_raw(event)) + 1
        if total > MAX_PREFIX_BYTES:
            raise ValueError("Coverage prefix already exceeds metadata capture capacity")
    return sized["n"], max(2, total - (1 if sized["n"] else 0))


def preflight_coverage_capture(ledger, preparation, *, cohort_raw, protocol_raw, review_raw, run_keys, freeze_event=None):
    """Bound both input captures without indexing, searching or making scores.

    Current raw projection and source bytes come from the verified reference.
    Future result bodies reserve the runner's existing 1 MB ceiling. This checks
    input capture capacity; actual report outputs retain their final size gate.
    A historical lookup budgets from its original freeze, never the newer tail.
    """
    _run_keys(run_keys)
    sources = runtime_sources()
    study_id = preparation["protocol"]["study_id"]
    stem = digest(study_id.encode("utf-8"))
    end = freeze_event["seq"] if freeze_event is not None else ledger.db.execute("SELECT COALESCE(MAX(seq),0) AS n FROM events").fetchone()["n"]
    count, prefix_bytes = _prefix_capacity(ledger, end)
    raw_files = {"cohort": cohort_raw, "protocol": protocol_raw, "review": review_raw}
    blobs = {}
    def blob(h, size):
        if type(size) is not int or not 0 <= size <= MAX_BYTES or (h in blobs and blobs[h] != size):
            raise ValueError("Invalid bounded coverage blob size")
        blobs[h] = size
    refs = {}
    for role, raw in raw_files.items():
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            raise ValueError("Coverage file exceeds capture capacity")
        h, eid = digest(raw), f"coverage-input:{stem}:{role}"
        blob(h, len(raw))
        observation = contracts._optional(ledger, eid)
        expected_body = _observation_body(eid, h, len(raw))
        if observation is not None and (observation["seq"] > end or observation["kind"] != "observation" or observation["body"] != expected_body):
            raise ValueError("Coverage deterministic input capture differs")
        if observation is None:
            if freeze_event is not None:
                raise ValueError("Historical coverage freeze lacks input capture")
            count += 1
            prefix_bytes += _event_bytes("observation", eid, len(_raw(expected_body))) + 1
        refs[role] = {"observation_id": eid, "event_hash": observation["hash"] if observation else "0" * 64,
                      "content_hash": h, "size": len(raw)}
    if freeze_event is None:
        count += 1
        prefix_bytes += _event_bytes("coverage_freeze", freeze_id(study_id), len(_raw(_body(preparation, refs, run_keys)))) + 1
    preparation_count, preparation_prefix = count, prefix_bytes
    reference = contracts._get(ledger, preparation["reference_terminal"]["id"], "retrieval_completed")
    corpus = contracts._get(ledger, preparation["lineage"]["corpus_id"], "retrieval_corpus")
    artifacts = reference["body"]["artifacts"]
    reference_refs = [artifacts["config"], artifacts["queries"], artifacts["implementation"], artifacts["recipe"],
        *artifacts["dependencies"].values(), *artifacts["stdlib"].values(), *artifacts["projection"]["chunks"]]
    for ref in [*corpus["body"]["sources"], *reference_refs]:
        blob(ref["content_hash"], ref["size"])
    roles = {"config": _raw(corpus["body"]["config"]), "queries": _raw(preparation["queries"]),
        "code:epiphysics.retrieval": sources[retrieval.__name__],
        "recipe": _raw({"schema_version": 1, "indexing_recipe": contracts.RAW_RECIPE})}
    roles.update({"code:" + name: sources[name] for name in contracts.DEPENDENCY_NAMES_V2})
    roles.update({("data:" if name == "html.entities.html5" else "code:") + name: sources[name] for name in contracts.STDLIB_NAMES})
    role_refs = {role: {"content_hash": digest(raw), "size": len(raw)} for role, raw in roles.items()}
    role_refs.update({f"projection:{index:04d}": {"content_hash": ref["content_hash"], "size": ref["size"]}
                     for index, ref in enumerate(artifacts["projection"]["chunks"])})
    for ref in role_refs.values():
        blob(ref["content_hash"], ref["size"])
    request = {"corpus_id": corpus["id"], "corpus_hash": corpus["hash"], "queries": preparation["queries"],
        "query_hash": preparation["lineage"]["query_hash"], "indexing_recipe": contracts.RAW_RECIPE}
    for key in run_keys:
        count += len(role_refs) + 2  # exactly16+number of unchanged projection chunks
        prefix_bytes += _event_bytes("retrieval_started", f"retrieval:{key}:started",
            len(_raw({"schema_version": 2, "run_key": key, "request": request}))) + 1
        for role, ref in role_refs.items():
            body = _observation_body(f"retrieval-input:{key}:{role}", ref["content_hash"], ref["size"],
                "text/x-python" if role.startswith("code:") else "application/json")
            prefix_bytes += _event_bytes("observation", f"retrieval:{key}:input:{role}", len(_raw(body))) + 1
        prefix_bytes += _event_bytes("retrieval_completed", f"retrieval:{key}:terminal", MAX_BYTES) + 1
    if count > MAX_PREFIX_EVENTS:
        raise ValueError("Coverage future executions exceed event capture capacity")
    if prefix_bytes > MAX_PREFIX_BYTES:
        raise ValueError("Coverage future executions exceed metadata capture capacity")
    # Adapter code is a bounded input artifact, read as bytes only. Keeping it
    # outside the neutral/evaluator imports preserves the measurement boundary.
    adapter_path = Path(__file__).with_name("retrieval_assessment.py")
    if adapter_path.is_symlink() or not adapter_path.is_file() or adapter_path.stat().st_size > MAX_BYTES:
        raise ValueError("Coverage adapter source exceeds capture capacity")
    with adapter_path.open("rb") as stream:
        adapter_raw = stream.read(MAX_BYTES + 1)
    if len(adapter_raw) > MAX_BYTES:
        raise ValueError("Coverage adapter source exceeds capture capacity")
    code_bytes = sum(len(raw) for raw in sources.values()) + len(adapter_raw)
    code_count = len(sources) + 1
    # Fixed original request may contain whitespace up to the existing1MB cap;
    # the policy declaration is always captured as bounded canonical JSON.
    terminals = [f"retrieval:{key}:terminal" for key in run_keys]
    declaration = {"schema_version": 3, "phase": "evaluation", "study_id": study_id, **preparation["lineage"],
        "protocol_hash": digest(protocol_raw), "review_hash": digest(review_raw), "freeze_event_hash": "0" * 64,
        "reference_terminal": preparation["reference_terminal"], "candidate_algorithm_hash": preparation["candidate_identity"]["algorithm_hash"],
        "evaluator_identity_hash": preparation["evaluator_identity_hash"], "runtime_hash": preparation["runtime_hash"],
        "run_terminal_hashes": {eid: "0" * 64 for eid in terminals}, "projection_hashes": {eid: "0" * 64 for eid in terminals}}
    wrapper = {"schema_version": 1, "events": [], "prefix_head": {"seq": 2**63-1, "id": terminals[-1], "hash": "0" * 64}, "blobs": blobs}
    bundle_artifact_bytes = prefix_bytes + len(_raw(wrapper)) - 2
    if bundle_artifact_bytes > MAX_ARTIFACT_BYTES:
        raise ValueError("Coverage evidence bundle exceeds per-artifact capture capacity")
    artifact_count = code_count + 6 + len(blobs) + 3  # reserve two scores and final report slots
    capture_bytes = code_bytes + sum(len(raw) for raw in raw_files.values()) + MAX_BYTES + len(_raw(declaration)) + bundle_artifact_bytes + sum(blobs.values())
    if artifact_count > MAX_ARTIFACTS:
        raise ValueError("Coverage future inputs exceed artifact count capacity")
    if capture_bytes > MAX_BUNDLE_BYTES:
        raise ValueError("Coverage future inputs exceed aggregate capture capacity")
    return {"preparation_events": preparation_count, "evaluation_events": count,
        "preparation_prefix_bytes_upper": preparation_prefix, "evaluation_prefix_bytes_upper": prefix_bytes,
        "evaluation_capture_bytes_upper": capture_bytes, "artifact_slots_including_reports": artifact_count,
        "result_report_bytes": "checked at completion, not forecast", "scope": "unchanged raw projection/code/collector clock; later growth is not reserved"}


def _capture(ledger, study_id, role, raw):
    identity = digest(study_id.encode("utf-8"))
    eid, source = f"coverage-input:{identity}:{role}", f"coverage-input:{identity}:{role}"
    event = ledger.capture(source, raw, media_type="application/json", event_id=eid)
    ref, actual = contracts._retained(ledger, eid, instant(ledger.clock()))
    if actual != raw or event["body"]["source"] != source:
        raise ValueError("Coverage captured bytes differ")
    return ref


def _ordered_runs(ledger, event, prepared):
    body = event["body"]
    request = {"corpus_id": body["corpus"]["id"], "corpus_hash": body["corpus"]["hash"],
        "queries": prepared["queries"], "query_hash": body["query_hash"], "indexing_recipe": contracts.RAW_RECIPE}
    previous = event
    missing = False
    for key in body["run_keys"]:
        for suffix, kind in (("started", "retrieval_started"), ("terminal", None)):
            current = contracts._optional(ledger, f"retrieval:{key}:{suffix}")
            if current is None:
                missing = True
                continue
            if missing or current["seq"] <= previous["seq"] or instant(current["recorded_at"]) < instant(previous["recorded_at"]):
                raise ValueError("Coverage executions violate frozen sequential order")
            if suffix == "started":
                if current["kind"] != kind or current["body"] != {"schema_version": 2, "run_key": key, "request": request}:
                    raise ValueError("Coverage started request differs from freeze")
            else:
                checked = contracts.get_retrieval_run(ledger, current["id"], verify_bytes=True)
                if checked["body"]["request"] != request:
                    raise ValueError("Coverage terminal request differs from freeze")
                if checked["kind"] == "retrieval_completed":
                    candidate = evaluation._candidate_identity(checked["body"])
                    if (candidate["algorithm_hash"] != body["candidate_algorithm_hash"]
                            or checked["body"]["runtime_hash"] != body["runtime_hash"]):
                        raise ValueError("Coverage execution candidate differs from freeze")
            previous = current


def get_coverage_freeze(ledger, event_id):
    """Verify historical preparation, allowing correctly later execution events."""
    if type(ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Coverage requires the current Ledger class")
    with assertions._read_transaction(ledger):
        event = contracts._get(ledger, event_id, "coverage_freeze")
        if instant(event["recorded_at"]) > instant(ledger.clock()):
            raise ValueError("Coverage freeze is not yet available")
        body = event["body"]
        _keys(body, FREEZE_FIELDS, "coverage freeze")
        if type(body["schema_version"]) is not int or body["schema_version"] != 1 or event["id"] != freeze_id(body["study_id"]):
            raise ValueError("Coverage freeze identity mismatch")
        _run_keys(body["run_keys"])
        _ref(body["corpus"], "freeze corpus")
        _ref(body["reference_terminal"], "freeze reference")
        _keys(body["artifacts"], {"cohort", "protocol", "review"}, "freeze artifacts")
        raws = {}
        for role, ref in body["artifacts"].items():
            _keys(ref, contracts.REF_FIELDS, "freeze artifact reference")
            observation = contracts._get(ledger, ref["observation_id"], "observation")
            if type(observation["body"]) is not dict:
                raise ValueError("Coverage artifact observation body must be an object")
            if observation["seq"] >= event["seq"]:
                raise ValueError("Coverage artifact must precede freeze")
            expected_id = f"coverage-input:{digest(body['study_id'].encode('utf-8'))}:{role}"
            if observation["id"] != expected_id or observation["body"].get("source") != expected_id:
                raise ValueError("Coverage artifact role differs")
            actual_ref, raw = contracts._retained(ledger, observation["id"], instant(event["recorded_at"]))
            if actual_ref != ref:
                raise ValueError("Coverage artifact reference differs")
            raws[role] = raw
        prepared = validate_coverage_preparation(ledger, cohort_raw=raws["cohort"], protocol_raw=raws["protocol"],
            review_raw=raws["review"], reference_terminal=body["reference_terminal"])
        if _body(prepared, body["artifacts"], body["run_keys"]) != body:
            raise ValueError("Coverage freeze bindings differ from retained inputs")
        reference = contracts._get(ledger, body["reference_terminal"]["id"])
        if reference["seq"] >= event["seq"] or instant(reference["recorded_at"]) > instant(event["recorded_at"]):
            raise ValueError("Coverage reference must precede freeze")
        preflight_coverage_capture(ledger, prepared, cohort_raw=raws["cohort"], protocol_raw=raws["protocol"],
            review_raw=raws["review"], run_keys=body["run_keys"], freeze_event=event)
        _ordered_runs(ledger, event, prepared)
        return {"event": event, "preparation": prepared}


def create_coverage_freeze(ledger, *, cohort_raw, protocol_raw, review_raw, reference_terminal, run_keys):
    """Create one reviewed freeze; exact retry never creates another event."""
    contracts._standalone(ledger)
    _run_keys(run_keys)
    prepared = validate_coverage_preparation(ledger, cohort_raw=cohort_raw, protocol_raw=protocol_raw,
        review_raw=review_raw, reference_terminal=reference_terminal)
    study_id = prepared["protocol"]["study_id"]
    eid = freeze_id(study_id)
    existing = contracts._optional(ledger, eid)
    if existing is not None:
        found = get_coverage_freeze(ledger, eid)
        if _body(prepared, found["event"]["body"]["artifacts"], run_keys) != found["event"]["body"] or found["preparation"]["file_hashes"] != prepared["file_hashes"]:
            raise ValueError("Coverage study already frozen with different inputs")
        return found["event"]
    # Keep the selected prefix and capture lookups in the same read snapshot.
    # Release it before captures; append validation still rechecks under its lock.
    with assertions._read_transaction(ledger):
        preflight_coverage_capture(ledger, prepared, cohort_raw=cohort_raw, protocol_raw=protocol_raw,
            review_raw=review_raw, run_keys=run_keys)
    refs = {role: _capture(ledger, study_id, role, raw) for role, raw in
        (("cohort", cohort_raw), ("protocol", protocol_raw), ("review", review_raw))}
    body = _body(prepared, refs, run_keys)
    def validate(now):
        checked = validate_coverage_preparation(ledger, cohort_raw=cohort_raw, protocol_raw=protocol_raw,
            review_raw=review_raw, reference_terminal=reference_terminal)
        if _body(checked, refs, run_keys) != body:
            raise ValueError("Coverage inputs changed before freeze")
        preflight_coverage_capture(ledger, checked, cohort_raw=cohort_raw, protocol_raw=protocol_raw,
            review_raw=review_raw, run_keys=run_keys)
        for ref in refs.values():
            actual, _ = contracts._retained(ledger, ref["observation_id"], instant(now))
            if actual != ref:
                raise ValueError("Coverage artifact changed before freeze")
        if any(contracts._optional(ledger, f"retrieval:{key}:{suffix}") is not None
               for key in run_keys for suffix in ("started", "terminal")):
            raise ValueError("Coverage freeze must precede both intended execution claims")
    try:
        event = ledger.append("coverage_freeze", body, eid, validate=validate, exclusive=True)
    except ValueError:
        existing = contracts._optional(ledger, eid)
        if existing is None or existing["body"] != body:
            raise
        return get_coverage_freeze(ledger, eid)["event"]
    return get_coverage_freeze(ledger, eid)["event"]


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
