"""Read-only interval diagnosis over retained coverage evidence; never searches.

Semantic categories are attributed reviewer claims. This module neither scores
quality nor changes annotations, candidate representations, or the work queue.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, retrieval_contracts as contracts, retrieval_coverage as coverage, retrieval_evaluation as evaluation, store
from .store import Ledger, canonical, digest, instant

IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE)
    for module in (store, assertions, contracts, coverage, evaluation))
CONTRACT_ID = "retrieval-support-diagnosis-v1"
MAX_DIAGNOSIS_BYTES = 256 * 1024
MAX_REVIEW_BYTES = 128 * 1024
MAX_ORIGIN_BYTES = 1_000_000
MAX_REPORT_BYTES = 256 * 1024
REVIEW_FIELDS = {"schema_version", "contract_id", "diagnosis_id", "diagnosis_hash", "origin_transition",
    "origin_step_id", "machine_findings_hash", "investigator_id", "reviewer_id", "focus_question_ids", "cases", "exposure"}
CATEGORIES = ("retrieval_gap", "annotation_gap", "unresolved")
CUTOFFS = (1, 3, 5)
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_MODULE_CODES = tuple((module, module.IMPLEMENTATION_CODE) for module in (store, assertions, contracts, coverage, evaluation))


def _raw(value):
    return coverage._raw(value)


def _same(left, right):
    return _raw(left) == _raw(right)


def _sha(value):
    return digest(_raw(value))


def _bounded(value, maximum, label):
    contracts._bounded_size(value, maximum, label)
    return value


def _keys(value, fields, label):
    coverage._keys(value, fields, label)


def _identity(value):
    return {**value, "hash": _sha(value)}


def runtime_sources():
    """Bind current diagnosis validation code, separate from scoring identity."""
    path, source, code = _SELF
    if IMPLEMENTATION_SOURCE != source or IMPLEMENTATION_CODE is not code:
        raise ValueError("Diagnosis implementation reloaded")
    if path.is_symlink() or not path.is_file() or path.stat().st_size != len(source) or len(source) > contracts.MAX_BYTES:
        raise ValueError("Diagnosis source changed")
    with path.open("rb") as stream:
        if stream.read(len(source) + 1) != source:
            raise ValueError("Diagnosis source changed")
    if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
        raise ValueError("Diagnosis executing code differs from retained source")
    for module, expected in _MODULE_CODES:
        if module.IMPLEMENTATION_CODE is not expected:
            raise ValueError("Diagnosis dependency reloaded: " + module.__name__)
    for name, function, expected in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not expected:
            raise ValueError("Diagnosis callable changed: " + name)
    if Ledger is not store.Ledger or canonical is not store.canonical or digest is not store.digest or instant is not store.instant:
        raise ValueError("Diagnosis store alias changed")
    return {**coverage.runtime_sources(), coverage.__name__: coverage.implementation_source(), __name__: source}


def _deadline(deadline):
    if deadline is not None:
        contracts._check_deadline(deadline)


def _coverage(span, windows):
    """Clipped continuous interval union, retaining every missing byte range."""
    assertions._span_shape(span)
    merged = []
    for start, end in sorted((max(span["start"], row["start"]), min(span["end"], row["end"]))
            for row in windows if row["observation_id"] == span["observation_id"]):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    missing, cursor = [], span["start"]
    for start, end in merged:
        if cursor < start:
            missing.append([cursor, start])
        cursor = end
    if cursor < span["end"]:
        missing.append([cursor, span["end"]])
    return {"covered_intervals": merged, "missing_intervals": missing,
            "covered_bytes": sum(end - start for start, end in merged),
            "total_bytes": span["end"] - span["start"], "complete": not missing}


def _case(case, result, projection_rows, *, detailed, deadline):
    windows = [{key: hit[key] for key in ("rank", "observation_id", "start", "end", "sha256")}
               for hit in result["hits"][:max(CUTOFFS)]]
    spans, indices, bundles, reconciliation = [], {}, [], []
    for bundle in case["support_bundles"]:
        _deadline(deadline)
        required = []
        for span in bundle["spans"]:
            key = _raw(span)
            if key not in indices:
                indices[key] = len(spans)
                entry = {"span": deepcopy(span), "returned_prefixes": {
                    str(k): _coverage(span, windows[:k]) for k in CUTOFFS}}
                if detailed:
                    entry["projection_coverage"] = _coverage(span, projection_rows)
                spans.append(entry)
            required.append(indices[key])
        counts = {str(k): sum(spans[i]["returned_prefixes"][str(k)]["complete"] for i in required) for k in CUTOFFS}
        complete = {str(k): counts[str(k)] == len(required) for k in CUTOFFS}
        first = next((k for k in range(1, len(windows) + 1)
            if all(_coverage(span, windows[:k])["complete"] for span in bundle["spans"])), None)
        bundles.append({"bundle_id": bundle["bundle_id"], "required_span_indices": required, "complete_at_k": complete})
        reconciliation.append({"bundle_id": bundle["bundle_id"], "required_spans": len(required),
            "covered_spans_at_k": counts, "complete_at_k": complete, "first_complete_prefix_at_5": first})
    answerable = case["answerability"] == "answerable"
    complete = {str(k): any(b["complete_at_k"][str(k)] for b in bundles) if answerable else None for k in CUTOFFS}
    detail = {"question_id": case["question_id"], "returned_windows": windows, "returned_windows_hash": _sha(windows),
              "spans": spans, "bundles": bundles, "complete_at_k": complete}
    return detail, reconciliation


def _origin(event, contract):
    _bounded(event, MAX_ORIGIN_BYTES, "Diagnosis origin")
    _keys(event, {"seq", "id", "kind", "recorded_at", "body", "previous_hash", "hash"}, "diagnosis origin event")
    coverage._ref(contract["origin_transition"], "origin transition")
    if type(event["seq"]) is not int or event["seq"] < 1:
        raise ValueError("Invalid diagnosis origin sequence")
    assertions._event_integrity(event)
    if {"id": event["id"], "hash": event["hash"]} != contract["origin_transition"] or event["kind"] != "improvement_completed":
        raise ValueError("Diagnosis origin differs from declared completed transition")
    body = event["body"]
    if type(body) is not dict or body.get("result") != "assessed":
        raise ValueError("Diagnosis origin requires a completed assessment")
    step = body["next_step"]
    if (step["id"] != contract["origin_step_id"] or step["action"] != "inspect_fresh_support_failures"
            or step["state"] != "queued"):
        raise ValueError("Diagnosis origin does not queue the declared support inspection")
    actual = body["report"]["actual_retrieval"]
    if (type(actual) is not dict or type(actual.get("schema_version")) is not int or actual["schema_version"] != 3
            or actual.get("phase") != "evaluation" or actual.get("status") != "completed"
            or actual.get("study_id") != contract["study_id"]):
        raise ValueError("Diagnosis requires original completed coverage evaluation")
    reproduced = actual["reproducibility"]
    if (type(reproduced.get("value")) is not int or reproduced["value"] != 1
            or reproduced.get("required_runs") != 2 or reproduced.get("valid_runs") != 2
            or any(reproduced.get(name) is not True for name in
                   ("ordered_results_equal", "evaluations_equal", "projections_equal"))):
        raise ValueError("Diagnosis origin does not establish repeated coverage")
    reports = actual["quality"]["runs"]
    if type(reports) is not list or len(reports) != 2 or any(type(row) is not dict for row in reports):
        raise ValueError("Diagnosis origin needs exactly two retained reports")
    return actual, reports


def _compute(ledger, cohort, freeze_event_id, run_terminal_ids, origin_transition, contract, deadline):
    _deadline(deadline)
    if type(ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Diagnosis requires the current Ledger")
    if type(contract) is not dict or type(contract.get("schema_version")) is not int or contract["schema_version"] != 3 or contract.get("phase") != "support_diagnosis":
        raise ValueError("Diagnosis declaration requires schema3 support_diagnosis")
    for name in ("diagnosis_id", "study_id", "origin_step_id"):
        contracts._identifier(contract[name], name)
    actual, reports = _origin(origin_transition, contract)
    if instant(origin_transition["recorded_at"]) > instant(ledger.clock()):
        raise ValueError("Diagnosis origin is not yet available")
    checked = evaluation._cohort(cohort)
    if checked["schema_version"] != 2:
        raise ValueError("Diagnosis requires the coverage cohort contract")
    focus = contract["focus_question_ids"]
    if type(focus) is not list or not 1 <= len(focus) <= evaluation.MAX_CASES:
        raise ValueError("Diagnosis requires bounded nonempty focus IDs")
    for identifier in focus:
        contracts._identifier(identifier, "focus question")
    order = [c["question_id"] for c in checked["cases"]]
    if len(set(focus)) != len(focus) or [x for x in order if x in focus] != focus:
        raise ValueError("Focus IDs must be unique existing questions in cohort order")
    found = coverage.get_coverage_freeze(ledger, freeze_event_id)
    freeze, ready = found["event"], found["preparation"]
    if not _same(ready["cohort"], checked):
        raise ValueError("Diagnosis cohort differs from frozen cohort")
    expected = {**ready["lineage"], "study_id": freeze["body"]["study_id"],
        "protocol_hash": ready["file_hashes"]["protocol"], "review_hash": ready["file_hashes"]["review"],
        "freeze_event_hash": freeze["hash"], "reference_terminal": freeze["body"]["reference_terminal"],
        "candidate_algorithm_hash": freeze["body"]["candidate_algorithm_hash"],
        "evaluator_identity_hash": freeze["body"]["evaluator_identity_hash"], "runtime_hash": freeze["body"]["runtime_hash"]}
    if any(not _same(contract[key], value) for key, value in expected.items()):
        raise ValueError("Diagnosis differs from frozen lineage")
    ids = [f"retrieval:{key}:terminal" for key in freeze["body"]["run_keys"]]
    if run_terminal_ids != ids or any(set(contract[field]) != set(ids) for field in ("run_terminal_hashes", "projection_hashes")):
        raise ValueError("Diagnosis execution order differs from freeze")
    if actual["preparation"]["freeze"] != {"id": freeze["id"], "hash": freeze["hash"]}:
        raise ValueError("Origin report belongs to another freeze")
    measurement = _identity({**ready["lineage"], "evaluator": ready["evaluator_identity"],
        "citation_semantics": "complete-raw-source-window-v1", "support_semantics": "any_complete_bundle_v1", "pair_bucket_cutoff": 5})
    if not _same(actual["measurement_contract_identity"], measurement):
        raise ValueError("Origin measurement identity differs from frozen contract")
    runs, projection = [], None
    corpus, _ = contracts._checked_corpus(ledger, contract["corpus_id"], instant(ledger.clock()), verify_bytes=True)
    for index, terminal_id in enumerate(ids):
        _deadline(deadline)
        run = contracts.get_retrieval_run(ledger, terminal_id, verify_bytes=True)
        rb = run["body"]
        if (run["kind"] != "retrieval_completed" or rb["indexing_recipe"] != contracts.RAW_RECIPE
                or run["hash"] != contract["run_terminal_hashes"][terminal_id]
                or rb["projection_hash"] != contract["projection_hashes"][terminal_id]
                or rb["request"]["queries"] != ready["queries"]):
            raise ValueError("Diagnosis receipt/query/projection binding differs")
        if instant(run["recorded_at"]) > instant(origin_transition["recorded_at"]):
            raise ValueError("Origin precedes its retrieval evidence")
        report = reports[index]
        if report.get("schema_version") != 2 or report.get("status") != "completed":
            raise ValueError("Origin contains invalid coverage report")
        identity = report["identity"]
        report_expected = {**ready["lineage"], "run_terminal_id": terminal_id, "run_terminal_hash": run["hash"],
            "results_hash": rb["results_hash"], "evaluator": ready["evaluator_identity"],
            "candidate": evaluation._candidate_identity(rb), "retriever_runtime_hash": rb["runtime_hash"]}
        if any(not _same(identity.get(key), value) for key, value in report_expected.items()):
            raise ValueError("Original evaluation does not bind the diagnosed evidence")
        if not _same(actual["candidate_identity"], report_expected["candidate"]):
            raise ValueError("Original candidate identity differs")
        current_projection = contracts._checked_artifacts_v2(ledger, rb, corpus, instant(run["recorded_at"]), run["seq"], verify_bytes=True)
        if projection is not None and not _same(projection, current_projection):
            raise ValueError("Repeated projections differ")
        projection = current_projection
        runs.append(run)
    if not _same(runs[0]["body"]["results"], runs[1]["body"]["results"]):
        raise ValueError("Repeated results differ")
    for key in ("counts", "metrics", "per_case", "matched_pairs", "pair_buckets", "families", "relations", "feature_inventory"):
        if not _same(reports[0][key], reports[1][key]):
            raise ValueError("Retained repeated evaluations disagree")
    # Neutral projection validation already enforces exact raw copy semantics.
    sources = contracts._projection_sources(ledger, corpus, instant(ledger.clock()), verify_bytes=True)
    for row in projection["rows"]:
        _deadline(deadline)
        raw = sources[row["observation_id"]]["raw"][row["start"]:row["end"]]
        if row["indexed_text"].encode("utf-8") != raw or row["indexed_bytes"] != len(raw) or row["indexed_text_sha256"] != digest(raw):
            raise ValueError("Raw projection does not preserve its source bytes")
    rows = reports[0]["per_case"]
    if type(rows) is not list or len(rows) != len(checked["cases"]):
        raise ValueError("Original report omits cohort cases")
    failed, details = [], []
    for case, result, old in zip(checked["cases"], runs[0]["body"]["results"], rows):
        _deadline(deadline)
        detail, bundles = _case(case, result, projection["rows"], detailed=case["question_id"] in focus, deadline=deadline)
        expected_case = {"query_id": case["question_id"], "query": case["query"], "answerability": case["answerability"],
            "pair_id": case["pair_id"], "status": result["status"], "reason": result["reason"],
            "raw_windows": detail["returned_windows"], "hit_count_at_5": len(detail["returned_windows"]),
            "complete_support_at_k": detail["complete_at_k"], "bundles": bundles}
        if any(not _same(old.get(key), value) for key, value in expected_case.items()):
            raise ValueError("Retained per-case report disagrees with recomputed intervals")
        if case["answerability"] == "answerable" and not detail["complete_at_k"]["5"]:
            failed.append(case["question_id"])
        if case["question_id"] in focus:
            details.append(detail)
            _bounded(details, MAX_REPORT_BYTES, "Diagnosis focused interval details")
    if not set(focus) <= set(failed):
        raise ValueError("Diagnosis focus must be within the original failed supported set")
    bindings = {"transition": deepcopy(contract["origin_transition"]), "step_id": contract["origin_step_id"],
        "freeze": {"id": freeze["id"], "hash": freeze["hash"]},
        **{name + "_file_hash": ready["file_hashes"][name] for name in ("cohort", "protocol", "review")},
        **{name: ready["lineage"][name] for name in ("cohort_hash", "gold_hash", "query_hash")},
        "measurement_contract_hash": measurement["hash"], "candidate_hash": actual["candidate_identity"]["hash"],
        "run_terminals": [{"id": run["id"], "hash": run["hash"]} for run in runs],
        "results_hashes": {run["id"]: run["body"]["results_hash"] for run in runs},
        "projection_hashes": {run["id"]: run["body"]["projection_hash"] for run in runs},
        "evaluation_hashes": [_sha(report) for report in reports]}
    return _bounded(_identity({"schema_version": 1, "contract_id": CONTRACT_ID, "origin_bindings": bindings,
        "failed_question_ids": failed, "focus_question_ids": list(focus),
        "deferred_question_ids": [identifier for identifier in failed if identifier not in focus], "cases": details,
        "projection": {"recipe": projection["recipe"], "sha256": runs[0]["body"]["projection_hash"],
                       "rows_checked": len(projection["rows"]), "all_raw_rows_equal_source": True}}), MAX_REPORT_BYTES, "Diagnosis findings")


def compute_support_findings(evidence_ledger, *, cohort, freeze_event_id, run_terminal_ids,
                             origin_transition, declared_contract, deadline=None):
    """Recompute bounded interval facts without trusting investigator prose."""
    sources = runtime_sources()
    try:
        with assertions._read_transaction(evidence_ledger):
            result = _compute(evidence_ledger, cohort, freeze_event_id, run_terminal_ids,
                              origin_transition, declared_contract, deadline)
        if runtime_sources() != sources:
            raise ValueError("Diagnosis validation code changed")
        return result
    except (KeyError, TypeError, IndexError, UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError("Invalid retained support diagnosis input") from error


def check_support_diagnosis(evidence_ledger, *, cohort, freeze_event_id, run_terminal_ids,
                            origin_transition, declared_contract, diagnosis_raw, review_raw, deadline=None):
    """Bind computed facts to an attributed review; neither chooses nor executes work."""
    sources = runtime_sources()
    try:
        if type(diagnosis_raw) is not bytes or not 1 <= len(diagnosis_raw) <= MAX_DIAGNOSIS_BYTES:
            raise ValueError("Investigation exceeds bounded byte input")
        review = coverage._json(review_raw, MAX_REVIEW_BYTES)
        _keys(review, REVIEW_FIELDS, "support diagnosis review")
        if (type(review["schema_version"]) is not int or review["schema_version"] != 1
                or review["contract_id"] != CONTRACT_ID or review["exposure"] != "post_execution_builder_visible_development"):
            raise ValueError("Unsupported diagnosis review contract or scope")
        for key in ("diagnosis_id", "investigator_id", "reviewer_id", "origin_step_id"):
            contracts._identifier(review[key], key)
        if review["investigator_id"] == review["reviewer_id"]:
            raise ValueError("Diagnosis requires a distinct semantic reviewer")
        if digest(diagnosis_raw) != declared_contract["diagnosis_hash"] or digest(review_raw) != declared_contract["diagnosis_review_hash"]:
            raise ValueError("Diagnosis or semantic review bytes differ from declaration")
        for name in ("diagnosis_id", "origin_transition", "origin_step_id", "focus_question_ids", "diagnosis_hash"):
            if not _same(review[name], declared_contract[name]):
                raise ValueError("Semantic review binding differs: " + name)
        findings = compute_support_findings(evidence_ledger, cohort=cohort, freeze_event_id=freeze_event_id,
            run_terminal_ids=run_terminal_ids, origin_transition=origin_transition, declared_contract=declared_contract, deadline=deadline)
        if review["machine_findings_hash"] != findings["hash"]:
            raise ValueError("Reviewed machine findings differ from recomputed intervals")
        cases = review["cases"]
        if type(cases) is not list or len(cases) != len(findings["cases"]):
            raise ValueError("Semantic review must cover exactly the focused cases")
        for reviewed, computed in zip(cases, findings["cases"]):
            _keys(reviewed, {"question_id", "category", "reviewed_windows_hash", "rationale"}, "focused diagnosis review")
            if (reviewed["question_id"] != computed["question_id"] or reviewed["category"] not in CATEGORIES
                    or reviewed["reviewed_windows_hash"] != computed["returned_windows_hash"]):
                raise ValueError("Semantic review case/window/category differs")
            evaluation._text(reviewed["rationale"], "semantic rationale", 4096)
        binding = findings["origin_bindings"]
        origin = {key: deepcopy(binding[key]) for key in ("transition", "step_id", "measurement_contract_hash", "candidate_hash", "evaluation_hashes")}
        result = {"contract_id": CONTRACT_ID, "origin": origin, "machine_findings": findings,
            "semantic_review": {"artifact_hash": digest(review_raw), "reviewer_id": review["reviewer_id"],
                "investigator_id": review["investigator_id"], "cases": deepcopy(cases),
                "unresolved_question_ids": [row["question_id"] for row in cases if row["category"] == "unresolved"]},
            "diagnosis_contract_identity": _identity({"contract_id": CONTRACT_ID,
                "interval_semantics": "same-source-half-open-continuous-union-v1", "projection_semantics": "retained-raw-source-copy-v1",
                "sources": {name: digest(raw) for name, raw in sorted(sources.items())}})}
        if runtime_sources() != sources:
            raise ValueError("Diagnosis validation code changed")
        return _bounded(result, MAX_REPORT_BYTES, "Checked support diagnosis")
    except (KeyError, TypeError, IndexError, UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError("Invalid support diagnosis review") from error


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
