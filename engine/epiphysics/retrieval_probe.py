"""Fixed read-only two-clause probe acceptance over retained raw receipts.

This is a development diagnostic, not a scoring contract or a retrieval runner.
The original cohort and scores remain unchanged; callers own live queue checks.
"""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
import re
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, retrieval_contracts as contracts, retrieval_coverage as coverage, retrieval_diagnosis as diagnosis, retrieval_evaluation as evaluation, store
from .store import Ledger, canonical, digest, instant

IMPLEMENTATION_DEPENDENCIES = tuple((m.__name__, m.IMPLEMENTATION_CODE) for m in (store, assertions, contracts, coverage, diagnosis, evaluation))
CONTRACT_ID = "fixed-clause-support-probe-v1"
MAX_BYTES = 1_000_000
MAX_REPORT_BYTES = 256 * 1024
ENVELOPE_FIELDS = {"schema_version", "protocol", "review", "supervisor", "requests", "origin_transition", "candidate_algorithm_hash", "runtime_hash", "validation_sources"}
EXECUTION_FIELDS = {"schema_version", "envelope_hash", "envelope_capture", "evidence_head", "slots"}
SLOT_FIELDS = {"run_key", "request_hash", "status", "caller_artifact", "stdout_artifact", "stderr_artifact", "start", "terminal"}
CALLER_FIELDS = {"schema_version", "run_key", "request_hash", "started_at", "ended_at", "elapsed_seconds", "elapsed_scope", "returncode", "stdout_hash", "stdout_bytes", "stderr_hash", "stderr_bytes", "model_calls", "external_spend"}
STATUSES = ("completed", "rejected", "launch_error", "timeout", "not_started")
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_MODULE_CODES = tuple((m, m.IMPLEMENTATION_CODE) for m in (store, assertions, contracts, coverage, diagnosis, evaluation))


def _raw(value):
    return coverage._raw(value)


def _same(a, b):
    return _raw(a) == _raw(b)


def _sha(value):
    return digest(_raw(value))


def _keys(value, fields, label):
    coverage._keys(value, fields, label)


def _bounded(value, limit=MAX_BYTES):
    contracts._bounded_size(value, limit, "Support probe")
    return value


def _version(value):
    if type(value) is not dict or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("Support probe artifacts require schema_version1")


def _ref(value):
    _keys(value, contracts.REF_FIELDS, "probe observation reference")
    contracts._identifier(value["observation_id"], "observation ID")
    for key in ("event_hash", "content_hash"):
        contracts._hash(value[key], key)
    if type(value["size"]) is not int or not 0 <= value["size"] <= MAX_BYTES:
        raise ValueError("Probe observation exceeds byte bound")


def _event_ref(value):
    coverage._ref(value, "probe event")


def _run_key(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value) is None:
        raise ValueError("Invalid fixed probe run key")


def _execution_shape(executions):
    _bounded(executions)
    _keys(executions, EXECUTION_FIELDS, "probe executions")
    _version(executions)
    contracts._hash(executions["envelope_hash"], "envelope hash")
    _event_ref(executions["envelope_capture"])
    head = executions["evidence_head"]
    _keys(head, {"seq", "id", "hash"}, "probe evidence head")
    _event_ref({"id": head["id"], "hash": head["hash"]})
    if type(head["seq"]) is not int or not 1 <= head["seq"] <= coverage.MAX_PREFIX_EVENTS:
        raise ValueError("Invalid bounded probe evidence sequence")
    slots = executions["slots"]
    if type(slots) is not list or len(slots) != 2:
        raise ValueError("Exactly two ordered probe slots are required")
    for slot in slots:
        _keys(slot, SLOT_FIELDS, "probe execution slot")
        _run_key(slot["run_key"])
        contracts._hash(slot["request_hash"], "request hash")
        if slot["status"] not in STATUSES:
            raise ValueError("Unknown probe slot status")
        for name in ("caller_artifact", "stdout_artifact", "stderr_artifact"):
            if slot[name] is not None:
                _ref(slot[name])
        for name in ("start", "terminal"):
            if slot[name] is not None:
                _event_ref(slot[name])
        refs = ("caller_artifact", "stdout_artifact", "stderr_artifact", "start", "terminal")
        if slot["status"] == "not_started":
            if any(slot[name] is not None for name in refs):
                raise ValueError("Unstarted slot cannot invent artifacts or events")
        elif any(slot[name] is None for name in ("caller_artifact", "stdout_artifact", "stderr_artifact")):
            raise ValueError("Attempted slot lacks caller/output evidence")
        if slot["status"] == "completed" and any(slot[name] is None for name in ("start", "terminal")):
            raise ValueError("Terminal slot lacks actual start/terminal references")
        if slot["status"] == "launch_error" and any(slot[name] is not None for name in ("start", "terminal")):
            raise ValueError("Launch error cannot claim retrieval events")
        if slot["terminal"] is not None and slot["start"] is None:
            raise ValueError("Terminal requires its actual start")
    if slots[0]["run_key"] == slots[1]["run_key"]:
        raise ValueError("Probe repetitions require distinct run keys")
    if slots[0]["status"] != "completed" and slots[1]["status"] != "not_started":
        raise ValueError("A failed first probe must leave the second unstarted")
    return slots


def capture_references(envelope, executions):
    """Return only bounded existing observation refs; never invent absent output."""
    _bounded(envelope)
    _keys(envelope, ENVELOPE_FIELDS, "probe envelope")
    _version(envelope)
    _event_ref(envelope["origin_transition"])
    for key in ("candidate_algorithm_hash", "runtime_hash"):
        contracts._hash(envelope[key], key)
    pins = envelope["validation_sources"]
    if type(pins) is not dict or not 1 <= len(pins) <= 32:
        raise ValueError("Invalid bounded probe validation source map")
    for name, content_hash in pins.items():
        contracts._identifier(name, "validation module")
        contracts._hash(content_hash, "validation source hash")
    requests = envelope["requests"]
    if type(requests) is not list or len(requests) != 2:
        raise ValueError("Envelope requires two exact requests")
    refs = [envelope[name] for name in ("protocol", "review", "supervisor")]
    for request in requests:
        _keys(request, {"run_key", "artifact"}, "envelope request")
        _run_key(request["run_key"])
        refs.append(request["artifact"])
    slots = _execution_shape(executions)
    if [row["run_key"] for row in requests] != [row["run_key"] for row in slots]:
        raise ValueError("Execution slots differ from envelope request order")
    for slot in slots:
        refs.extend(slot[key] for key in ("caller_artifact", "stdout_artifact", "stderr_artifact") if slot[key] is not None)
    for ref in refs:
        _ref(ref)
    return deepcopy(refs)


def terminal_ids(executions):
    return [slot["terminal"]["id"] for slot in _execution_shape(executions) if slot["terminal"] is not None]


def runtime_sources():
    path, source, code = _SELF
    if IMPLEMENTATION_SOURCE != source or IMPLEMENTATION_CODE is not code:
        raise ValueError("Probe implementation reloaded")
    if path.is_symlink() or not path.is_file() or path.stat().st_size != len(source) or len(source) > MAX_BYTES:
        raise ValueError("Probe source changed")
    with path.open("rb") as stream:
        if stream.read(len(source) + 1) != source:
            raise ValueError("Probe source changed")
    if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
        raise ValueError("Probe execution differs from retained source")
    for module, expected in _MODULE_CODES:
        if module.IMPLEMENTATION_CODE is not expected:
            raise ValueError("Probe validation dependency reloaded")
    for name, function, expected in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not expected:
            raise ValueError("Probe callable changed: " + name)
    if Ledger is not store.Ledger or canonical is not store.canonical or digest is not store.digest or instant is not store.instant:
        raise ValueError("Probe store alias changed")
    return {**diagnosis.runtime_sources(), __name__: source}


def _retained(ledger, ref):
    _ref(ref)
    actual, raw = contracts._retained(ledger, ref["observation_id"], instant(ledger.clock()), verify_bytes=True)
    if actual != ref:
        raise ValueError("Probe observation reference differs from retained bytes")
    return contracts._get(ledger, ref["observation_id"], "observation"), raw


def _event(ledger, ref, expected_id, kind=None):
    if ref is None:
        if contracts._optional(ledger, expected_id) is not None:
            raise ValueError("Probe omits an existing declared execution event")
        return None
    _event_ref(ref)
    if ref["id"] != expected_id:
        raise ValueError("Probe event ID differs from fixed run key")
    value = contracts._get(ledger, expected_id, kind)
    if value["hash"] != ref["hash"]:
        raise ValueError("Probe event hash differs")
    return value


def _window_stats(windows):
    groups = {}
    for row in windows:
        groups.setdefault(row["observation_id"], []).append((row["start"], row["end"]))
    union = {}
    for source, spans in sorted(groups.items()):
        merged = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        union[source] = sum(end - start for start, end in merged)
    return {"window_occurrences": len(windows), "distinct_windows": len({(r["observation_id"], r["start"], r["end"], r["sha256"]) for r in windows}),
        "summed_window_bytes": sum(r["end"] - r["start"] for r in windows),
        "union_source_bytes": sum(union.values()), "union_source_bytes_by_observation": union}


def _diagnostic(protocol, results, old_results):
    clauses = []
    for support, result in zip(protocol["clause_support"], results):
        windows = [{key: row[key] for key in ("rank", "observation_id", "start", "end", "sha256")} for row in result["hits"][:5]]
        bundles = [{"bundle_id": bundle["bundle_id"], "spans": [{"span": deepcopy(span),
            "coverage_at_k": {str(k): diagnosis._coverage(span, windows[:k]) for k in (1, 3, 5)}} for span in bundle["spans"]]}
            for bundle in support["support_bundles"]]
        clauses.append({"query_id": result["query_id"], "raw_windows": windows,
            "complete_at_k": {str(k): any(all(s["coverage_at_k"][str(k)]["complete"] for s in b["spans"]) for b in bundles) for k in (1, 3, 5)},
            "bundles": bundles, "windows_at_k": {str(k): _window_stats(windows[:k]) for k in (1, 3, 5)}})
    combined = [window for clause in clauses for window in clause["raw_windows"]]
    joint = {"metric": "joint_support_union_of_two_top5", "shared_rank": None, "maximum_window_occurrences": 10,
        "bundles": [{"bundle_id": bundle["bundle_id"], "spans": [{"span": deepcopy(span), "coverage": diagnosis._coverage(span, combined)}
            for span in bundle["spans"]]} for bundle in protocol["origin"]["joint_bundles"]],
        "windows": _window_stats(combined), "original_joint_top5_windows": _window_stats(old_results["hits"][:5])}
    joint["complete"] = any(all(span["coverage"]["complete"] for span in bundle["spans"]) for bundle in joint["bundles"])
    return {"clause_support": clauses, "joint_support_union_of_two_top5": joint}


def _check_protocol(ledger, cohort, origin, protocol, contract):
    _bounded(protocol)
    _version(protocol)
    if protocol.get("status") != "pre_execution_protocol" or protocol.get("scope") != "post_execution_builder_visible_development_diagnosis":
        raise ValueError("Probe protocol is not fixed pre-execution development work")
    contracts._identifier(protocol["protocol_id"], "protocol ID")
    if len(protocol["protocol_id"].encode()) > 128:
        raise ValueError("Probe protocol ID exceeds128 bytes")
    _bounded(origin)
    assertions._event_integrity(origin)
    ref = {"id": origin["id"], "hash": origin["hash"]}
    prerequisite = protocol["prerequisites"]
    if (origin["kind"] != "improvement_completed" or ref != contract["origin_transition"] or ref != prerequisite["checked_c5_transition"]
            or prerequisite["queued_preparation_step"] != contract["origin_step_id"]
            or prerequisite["required_action"] != "prepare_focused_support_followup" or prerequisite["no_deferred_or_unresolved_failures"] is not True):
        raise ValueError("Probe origin differs from accepted diagnosis")
    step = origin["body"]["next_step"]
    if origin["body"].get("result") != "assessed" or step["id"] != contract["origin_step_id"] or step["action"] != "prepare_focused_support_followup" or step["state"] != "queued":
        raise ValueError("Probe origin does not queue this preparation")
    checked = origin["body"]["report"]["support_diagnosis"]
    if (checked.get("schema_version") != 3 or checked.get("phase") != "support_diagnosis" or checked.get("status") != "checked"
            or checked["machine_findings"]["deferred_question_ids"] or checked["semantic_review"]["unresolved_question_ids"]
            or any(row["category"] != "retrieval_gap" for row in checked["semantic_review"]["cases"])):
        raise ValueError("Probe requires reviewed diagnosis without deferred/unresolved cases")
    findings = checked["machine_findings"]
    if findings["hash"] != _sha({key: value for key, value in findings.items() if key != "hash"}):
        raise ValueError("Origin diagnosis findings hash differs")
    c4 = findings["origin_bindings"]
    found = coverage.get_coverage_freeze(ledger, c4["freeze"]["id"])
    freeze, ready = found["event"], found["preparation"]
    if c4["freeze"]["hash"] != freeze["hash"] or not _same(ready["cohort"], evaluation._cohort(cohort)):
        raise ValueError("Probe ancestral cohort/freeze differs")
    expected = {**ready["lineage"], "protocol_hash": ready["file_hashes"]["protocol"], "review_hash": ready["file_hashes"]["review"],
        "freeze_event_hash": freeze["hash"], "reference_terminal": ready["reference_terminal"], "candidate_algorithm_hash": ready["candidate_identity"]["algorithm_hash"],
        "evaluator_identity_hash": ready["evaluator_identity_hash"], "runtime_hash": ready["runtime_hash"]}
    if any(not _same(contract[key], value) for key, value in expected.items()):
        raise ValueError("Probe declaration changed frozen lineage")
    original = protocol["origin"]
    target = next((case for case in ready["cohort"]["cases"] if case["question_id"] == original["question_id"]), None)
    if (target is None or target["question_id"] not in findings["focus_question_ids"] or target["answerability"] != "answerable"
            or original["joint_query"] != target["query"] or not _same(original["joint_bundles"], target["support_bundles"])
            or original["cohort_file_sha256"] != c4["cohort_file_hash"] or original["measurement_contract_hash"] != c4["measurement_contract_hash"]
            or not _same(original["c4_terminal_refs"], c4["run_terminals"])):
        raise ValueError("Probe target differs from original diagnosed case")
    limits = {"fresh_processes": 2, "ordered_repeats": True, "queries_per_process": 2, "top_k_per_query": 5,
        "cooperative_seconds_per_process": 30, "outer_seconds_per_process": 60, "model_calls": 0, "external_spend": 0,
        "additional_repeats_or_queries": 0, "config_or_recipe_changes": False, "network_fetches": False}
    if not _same(protocol["execution_limits"], limits):
        raise ValueError("Probe exceeds fixed local two-run scope")
    queries = contracts._queries(protocol["queries"])
    if len(queries) != 2 or type(protocol["executions"]) is not list or len(protocol["executions"]) != 2:
        raise ValueError("Probe requires exactly two fixed clauses and executions")
    candidate = protocol["fixed_candidate"]
    corpus, _ = contracts._checked_corpus(ledger, candidate["corpus_id"], instant(ledger.clock()), verify_bytes=True)
    if (candidate["corpus_id"] != ready["lineage"]["corpus_id"] or candidate["corpus_hash"] != ready["lineage"]["corpus_hash"]
            or candidate["corpus_hash"] != corpus["hash"] or candidate["config_hash"] != corpus["body"]["config_hash"]
            or candidate["indexing_recipe"] != contracts.RAW_RECIPE or candidate["candidate_algorithm_hash"] != ready["candidate_identity"]["algorithm_hash"]
            or candidate["runtime_hash"] != ready["runtime_hash"] or corpus["body"]["config"]["top_k"] != 5
            or corpus["body"]["config"]["execution_seconds"] != 30):
        raise ValueError("Probe candidate/runtime/configuration differs")
    for request in protocol["executions"]:
        _keys(request, {"corpus_id", "queries", "run_key", "indexing_recipe"}, "fixed probe request")
        _run_key(request["run_key"])
        if request["corpus_id"] != corpus["id"] or request["indexing_recipe"] != contracts.RAW_RECIPE or not _same(request["queries"], queries):
            raise ValueError("Declared probe request differs from fixed clauses")
    if protocol["executions"][0]["run_key"] == protocol["executions"][1]["run_key"]:
        raise ValueError("Probe run keys must be distinct")
    support = protocol["clause_support"]
    if type(support) is not list or len(support) != 2:
        raise ValueError("Both probe clauses need reviewed support intervals")
    allowed = {_raw(span) for bundle in target["support_bundles"] for span in bundle["spans"]}
    for entry, query in zip(support, queries):
        _keys(entry, {"query_id", "support_bundles"}, "clause support")
        if entry["query_id"] != query["query_id"] or type(entry["support_bundles"]) is not list or not 1 <= len(entry["support_bundles"]) <= 4:
            raise ValueError("Invalid clause support declaration")
        seen = set()
        for bundle in entry["support_bundles"]:
            _keys(bundle, {"bundle_id", "spans"}, "clause support bundle")
            contracts._identifier(bundle["bundle_id"], "bundle ID")
            if bundle["bundle_id"] in seen or type(bundle["spans"]) is not list or not 1 <= len(bundle["spans"]) <= 8:
                raise ValueError("Invalid bounded clause support bundle")
            seen.add(bundle["bundle_id"])
            if len({_raw(span) for span in bundle["spans"]}) != len(bundle["spans"]) or any(_raw(span) not in allowed for span in bundle["spans"]):
                raise ValueError("Probe support must preserve original source intervals")
    old_runs = [contracts.get_retrieval_run(ledger, ref["id"], verify_bytes=True) for ref in original["c4_terminal_refs"]]
    if any(run["hash"] != ref["hash"] or run["body"]["results_hash"] != original["c4_results_hash"]
           or run["body"]["projection_hash"] != candidate["projection_hash"] for run, ref in zip(old_runs, original["c4_terminal_refs"])):
        raise ValueError("Original joint retrieval binding differs")
    old_result = next(row for row in old_runs[0]["body"]["results"] if row["query_id"] == target["question_id"])
    return c4, corpus, old_result


def _check(ledger, cohort, origin, protocol, review, envelope, executions, contract, sources, deadline):
    if type(ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Probe requires current Ledger")
    refs = capture_references(envelope, executions)
    _bounded(review)
    _keys(review, {"schema_version", "protocol_hash", "reviewer_id", "decision", "unresolved_findings", "scope"}, "probe review")
    _version(review)
    contracts._identifier(review["reviewer_id"], "reviewer")
    if review["decision"] != "approved" or review["unresolved_findings"] != [] or review["scope"] != "post_execution_builder_visible_development_diagnosis":
        raise ValueError("Probe lacks resolved protocol review")
    c4, corpus, old_result = _check_protocol(ledger, cohort, origin, protocol, contract)
    size = ledger.db.execute("SELECT COUNT(*),COALESCE(SUM(length(CAST(body AS BLOB))+length(CAST(id AS BLOB))+256),0) FROM events").fetchone()
    if size[0] > coverage.MAX_PREFIX_EVENTS or size[1] > coverage.MAX_PREFIX_BYTES:
        raise ValueError("Probe evidence prefix exceeds bounds")
    if not ledger.verify()["valid"]:
        raise ValueError("Probe evidence integrity failed")
    events = ledger.events()
    if not events or {key: events[-1][key] for key in ("seq", "id", "hash")} != executions["evidence_head"]:
        raise ValueError("Probe evidence head is not the complete captured prefix")
    inherited = protocol["evidence_preservation"]["inherited_prefix"]
    _keys(inherited, {"events", "head"}, "inherited probe prefix")
    if type(inherited["events"]) is not int or not 1 <= inherited["events"] < len(events) or events[inherited["events"] - 1]["hash"] != inherited["head"]:
        raise ValueError("Probe changed its inherited evidence prefix")
    accepted_prefix = origin["body"]["report"]["support_diagnosis"]["input_bindings"]["prefix_head"]
    _keys(accepted_prefix, {"seq", "id", "hash"}, "accepted diagnosis prefix")
    if not _same({key: events[inherited["events"] - 1][key] for key in ("seq", "id", "hash")}, accepted_prefix):
        raise ValueError("Probe inherited boundary differs from accepted diagnosis prefix")
    anchor_id = f"support-probe:{protocol['protocol_id']}:envelope"
    anchor = _event(ledger, executions["envelope_capture"], anchor_id, "observation")
    anchor_ref, anchor_raw = contracts._retained(ledger, anchor_id, instant(ledger.clock()))
    if (anchor["body"]["source"] != f"support-probe-envelope:{protocol['protocol_id']}" or anchor["seq"] <= events[inherited["events"] - 1]["seq"]
            or digest(anchor_raw) != contract["probe_envelope_hash"] or digest(anchor_raw) != executions["envelope_hash"]
            or not _same(coverage._json(anchor_raw), envelope)):
        raise ValueError("Probe envelope lacks exact pre-execution order anchor")
    for name, parsed in (("protocol", protocol), ("review", review)):
        event, raw = _retained(ledger, envelope[name])
        if event["seq"] >= anchor["seq"] or digest(raw) != contract[f"probe_{name}_hash"] or not _same(coverage._json(raw), parsed):
            raise ValueError("Envelope does not bind exact reviewed pre-execution bytes")
    if review["protocol_hash"] != envelope["protocol"]["content_hash"] or envelope["origin_transition"] != contract["origin_transition"]:
        raise ValueError("Protocol review/origin envelope binding differs")
    supervisor, _ = _retained(ledger, envelope["supervisor"])
    if supervisor["seq"] >= anchor["seq"]:
        raise ValueError("Supervisor source must precede envelope")
    if (envelope["candidate_algorithm_hash"] != protocol["fixed_candidate"]["candidate_algorithm_hash"]
            or envelope["runtime_hash"] != protocol["fixed_candidate"]["runtime_hash"]
            or envelope["validation_sources"] != {name: digest(raw) for name, raw in sources.items()}):
        raise ValueError("Envelope validation/candidate/runtime identity differs")
    known_ids = {f"retrieval:{request['run_key']}:{suffix}" for request in protocol["executions"] for suffix in ("started", "terminal")}
    if any(e["kind"] != "observation" and e["id"] not in known_ids for e in events[inherited["events"]:]):
        raise ValueError("Unplanned execution after inherited probe prefix")
    runs, diagnostics, caller_rows, reports = [], [], [], []
    for index, (slot, request, request_ref) in enumerate(zip(executions["slots"], protocol["executions"], envelope["requests"])):
        diagnosis._deadline(deadline)
        if slot["run_key"] != request["run_key"]:
            raise ValueError("Probe slot differs from declared exact run key")
        event, raw_request = _retained(ledger, request_ref["artifact"])
        if event["seq"] >= anchor["seq"] or not _same(coverage._json(raw_request), request) or slot["request_hash"] != digest(raw_request):
            raise ValueError("Probe request differs from envelope declaration")
        key = request["run_key"]
        start = _event(ledger, slot["start"], f"retrieval:{key}:started", "retrieval_started")
        terminal = _event(ledger, slot["terminal"], f"retrieval:{key}:terminal")
        expected_request = {"corpus_id": corpus["id"], "corpus_hash": corpus["hash"], "queries": request["queries"],
            "query_hash": _sha(request["queries"]), "indexing_recipe": contracts.RAW_RECIPE}
        if start is not None:
            if start["seq"] <= anchor["seq"] or not _same(start["body"], {"schema_version": 2, "run_key": key, "request": expected_request}):
                raise ValueError("Probe start precedes envelope or differs from exact request")
            if index and (not runs or runs[0]["seq"] >= start["seq"]):
                raise ValueError("Second probe must follow first valid completion")
        if terminal is not None:
            terminal = contracts._checked_terminal(ledger, terminal, expected_request, verify_bytes=True)
            if terminal["body"]["run_key"] != key or not _same(terminal["body"]["request"], expected_request):
                raise ValueError("Probe terminal differs from declared request")
        if slot["status"] == "not_started":
            continue
        caller_event, caller_raw = _retained(ledger, slot["caller_artifact"])
        caller = coverage._json(caller_raw)
        _keys(caller, CALLER_FIELDS, "probe caller receipt")
        _version(caller)
        outputs = {}
        for name in ("stdout", "stderr"):
            output_event, raw_output = _retained(ledger, slot[name + "_artifact"])
            if output_event["seq"] <= (terminal or start or anchor)["seq"]:
                raise ValueError("Caller output must follow its actual execution evidence")
            if type(caller[name + "_bytes"]) is not int or caller[name + "_bytes"] != len(raw_output) or caller[name + "_hash"] != digest(raw_output):
                raise ValueError("Caller output bytes/hash differ")
            outputs[name] = raw_output
        if caller_event["seq"] <= (terminal or start or anchor)["seq"]:
            raise ValueError("Caller receipt must follow execution")
        if (caller["run_key"] != key or caller["request_hash"] != slot["request_hash"]
                or caller["elapsed_scope"] != "fresh process wall time through exit"
                or type(caller["elapsed_seconds"]) not in (int, float) or not math.isfinite(caller["elapsed_seconds"]) or caller["elapsed_seconds"] < 0
                or type(caller["model_calls"]) is not int or caller["model_calls"] != 0
                or type(caller["external_spend"]) is not int or caller["external_spend"] != 0
                or instant(caller["started_at"]) > instant(caller["ended_at"])):
            raise ValueError("Caller identity/time/resource fields differ")
        if slot["status"] == "completed":
            if (type(caller["returncode"]) is not int or caller["returncode"] != 0 or caller["elapsed_seconds"] > 60
                    or terminal["kind"] != "retrieval_completed" or not _same(coverage._json(outputs["stdout"]), terminal)):
                raise ValueError("Completed caller does not bind a successful exact terminal")
        elif slot["status"] == "rejected":
            if type(caller["returncode"]) is not int or caller["returncode"] == 0:
                raise ValueError("Rejected caller requires its actual nonzero exit")
            if terminal is not None and (terminal["kind"] != "retrieval_rejected" or not _same(coverage._json(outputs["stdout"]), terminal)):
                raise ValueError("Rejected caller differs from actual rejected terminal")
        elif caller["returncode"] != slot["status"]:
            raise ValueError("Failed caller status differs from execution slot")
        if slot["status"] != "completed":
            continue
        candidate = evaluation._candidate_identity(terminal["body"])
        fixed = protocol["fixed_candidate"]
        if (candidate["algorithm_hash"] != fixed["candidate_algorithm_hash"] or terminal["body"]["runtime_hash"] != fixed["runtime_hash"]
                or terminal["body"]["projection_hash"] != fixed["projection_hash"] or terminal["body"]["config_hash"] != fixed["config_hash"]):
            raise ValueError("Probe completion changed candidate/runtime/projection/config")
        runs.append(terminal)
        diagnostic = _diagnostic(protocol, terminal["body"]["results"], old_result)
        diagnostics.append(diagnostic)
        caller_rows.append({"run_key": key, "caller": caller, "retrieval": deepcopy(terminal["body"]["resources"])})
        reports.append({"run_key": key, "request_hash": slot["request_hash"], "start": deepcopy(slot["start"]), "terminal": deepcopy(slot["terminal"]),
            "results_hash": terminal["body"]["results_hash"], "projection_hash": terminal["body"]["projection_hash"], "result_rows": deepcopy(terminal["body"]["results"])})
    if len(runs) != 2:
        raise ValueError("Probe execution incomplete; preserve actual failure and unstarted slots")
    equal_results = _same(runs[0]["body"]["results"], runs[1]["body"]["results"])
    equal_projections = runs[0]["body"]["projection_hash"] == runs[1]["body"]["projection_hash"]
    equal_diagnostics = _same(diagnostics[0], diagnostics[1])
    reproduced = equal_results and equal_projections and equal_diagnostics
    identity = {"contract_id": CONTRACT_ID, "sources": {name: digest(raw) for name, raw in sorted(sources.items())}}
    return _bounded({"contract_id": CONTRACT_ID,
        "origin": {"transition": deepcopy(contract["origin_transition"]), "step_id": contract["origin_step_id"],
            "measurement_contract_hash": c4["measurement_contract_hash"], "candidate_hash": c4["candidate_hash"]},
        "bindings": {"c4_origin_bindings": deepcopy(c4), "protocol_hash": contract["probe_protocol_hash"], "review_hash": contract["probe_review_hash"],
            "envelope_hash": contract["probe_envelope_hash"], "envelope_capture": deepcopy(executions["envelope_capture"]), "evidence_head": deepcopy(executions["evidence_head"]),
            "request_hashes": [slot["request_hash"] for slot in executions["slots"]], "terminal_refs": [row["terminal"] for row in reports]},
        "executions": reports, "reproducibility": {"required_runs": 2, "valid_runs": 2, "ordered_results_equal": equal_results,
            "projections_equal": equal_projections, "diagnostics_equal": equal_diagnostics, "value": int(reproduced),
            "assurance": "Local retained claims and caller attestations; not an independent execution or timestamp witness."},
        "clause_support": diagnostics[0]["clause_support"] if reproduced else None,
        "joint_support_union_of_two_top5": diagnostics[0]["joint_support_union_of_two_top5"] if reproduced else None,
        "resources": {"runs": caller_rows, "caller_seconds_sum": sum(row["caller"]["elapsed_seconds"] for row in caller_rows),
            "model_calls": 0, "external_spend": 0, "whole_step_builder_reviewer_cost": None},
        "limitations": ["Exposed development clause diagnostic; not a held-out or same-budget quality comparison.",
            "Two separate top-five sets have no shared rank; no original cohort score, annotation, or adoption changes.",
            "Inner and outer timings are nested scopes; caller wall time is not CPU or engineering cost."],
        "probe_contract_identity": {**identity, "hash": _sha(identity)}}, MAX_REPORT_BYTES)


def check_support_probe(ledger, *, cohort, origin_transition, protocol, review, envelope, executions, declared_contract, deadline=None):
    """Accept only two bound completed receipts; never execute a probe or score."""
    sources = runtime_sources()
    try:
        diagnosis._deadline(deadline)
        with assertions._read_transaction(ledger):
            result = _check(ledger, cohort, origin_transition, protocol, review, envelope, executions, declared_contract, sources, deadline)
        if runtime_sources() != sources:
            raise ValueError("Probe validation code changed")
        return result
    except (KeyError, TypeError, IndexError, UnicodeError, OverflowError, RecursionError, StopIteration) as error:
        raise ValueError("Invalid retained support probe input") from error


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
