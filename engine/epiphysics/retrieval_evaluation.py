"""Read-only scoring of builder-visible retrieval development data.

Gold is evaluator input only. The candidate receives ``project_queries`` and its
frozen corpus, never this cohort. Invalid or incomplete executions raise rather
than returning apparent zero loss; genuine empty outputs score as misses.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import platform
import re
import sys
import unicodedata

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, retrieval, store
from .assertions import _read_transaction, resolve_span
from .store import canonical, digest

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions, retrieval)
)
_DEPENDENCIES = (store, assertions, retrieval)
_MODULE = sys.modules[__name__]
_PINNED_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_PINNED_DEPENDENCIES = tuple((module, module.IMPLEMENTATION_CODE) for module in _DEPENDENCIES)
_LEDGER_CLASS = store.Ledger
_RETRIEVAL_RUNTIME_SOURCES = retrieval._runtime_sources
MAX_CASES = 64
MAX_GOLD_PER_CASE = 64
MAX_COHORT_BYTES = 1_000_000
MAX_ID_BYTES = 512
MAX_QUERY_BYTES = 2048
MAX_SOURCE_BYTES = 1_000_000
CUTOFFS = (1, 3, 5)
CONTRACT = {
    "id": "retrieval-development-evaluation-v1",
    "cohort": "builder-visible development; not a sealed holdout",
    "cutoffs": list(CUTOFFS),
    "minimum_run_top_k": max(CUTOFFS),
    "source_recall": "macro mean over answerable queries of distinct gold sources found / distinct gold sources",
    "source_mrr": "macro mean over answerable queries of reciprocal earliest gold-source rank through 5",
    "gold_span_recall": "macro mean over answerable queries of fully covered gold spans / gold spans; union intervals per observation",
    "gold_span_mrr": "macro mean over answerable queries of reciprocal earliest prefix through 5 fully covering at least one gold span by interval union",
    "unsupported_query_retrieval_rate": "unsupported queries with any hit through 5 / all unsupported queries; not hallucination or calibrated abstention",
    "empty_outputs": "valid empty outputs contribute zero to answerable-query metrics",
    "invalid_execution": "missing, rejected, malformed or incomplete execution raises ValueError and produces no metric report",
    "empty_denominator": "null, never a perfect score",
    "span_unit": "half-open UTF-8 byte offsets with exact slice SHA-256",
    "bounds": {"cases": MAX_CASES, "gold_spans_per_case": MAX_GOLD_PER_CASE,
               "cohort_bytes": MAX_COHORT_BYTES, "query_bytes": MAX_QUERY_BYTES,
               "id_bytes": MAX_ID_BYTES},
}


def _sha(value):
    return digest(canonical(value).encode("utf-8"))


def _text(value, label, maximum, *, empty=False):
    if type(value) is not str or (not empty and not value.strip()):
        raise ValueError(f"{label} must be a {'possibly empty' if empty else 'nonempty'} string")
    if len(value) > maximum:
        raise ValueError(f"{label} exceeds {maximum} UTF-8 bytes")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ValueError(f"{label} must contain valid UTF-8 text") from error
    if size > maximum:
        raise ValueError(f"{label} exceeds {maximum} UTF-8 bytes")


def _fields(value, required, optional, label):
    if type(value) is not dict or not required <= set(value) or set(value) - required - optional:
        raise ValueError(f"Invalid {label} fields")


def _span(span):
    _fields(span, {"observation_id", "start", "end", "sha256"}, set(), "gold span")
    _text(span["observation_id"], "Gold observation ID", MAX_ID_BYTES)
    if (type(span["start"]) is not int or type(span["end"]) is not int
            or not 0 <= span["start"] < span["end"] <= MAX_SOURCE_BYTES):
        raise ValueError("Gold span requires bounded nonempty integer byte offsets")
    if type(span["sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", span["sha256"]) is None:
        raise ValueError("Gold span requires a lowercase SHA-256")


def _cohort(cohort):
    _fields(cohort, {"schema_version", "snapshot_id", "cohort", "cases"},
            {"span_convention", "answerability_definition", "limitations"}, "development cohort")
    if type(cohort["schema_version"]) is not int or cohort["schema_version"] != 1:
        raise ValueError("Cohort schema_version must be 1")
    if cohort["cohort"] != "development":
        raise ValueError("This evaluator requires builder-visible development data")
    _text(cohort["snapshot_id"], "Cohort snapshot ID", MAX_ID_BYTES)
    cases = cohort["cases"]
    if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError(f"Cohort requires 1 to {MAX_CASES} cases")
    seen = set()
    for case in cases:
        _fields(case, {"question_id", "query", "answerability", "gold_spans"},
                {"topic", "rationale", "source_url"}, "development case")
        _text(case["question_id"], "Question ID", MAX_ID_BYTES)
        _text(case["query"], "Query", MAX_QUERY_BYTES, empty=True)
        if case["question_id"] in seen:
            raise ValueError("Duplicate question ID")
        seen.add(case["question_id"])
        if case["answerability"] not in ("answerable", "unanswerable"):
            raise ValueError("Answerability must be answerable or unanswerable")
        spans = case["gold_spans"]
        if type(spans) is not list or len(spans) > MAX_GOLD_PER_CASE:
            raise ValueError("Gold spans must be a bounded array")
        if bool(spans) != (case["answerability"] == "answerable"):
            raise ValueError("Answerable cases require gold spans; unanswerable cases require no gold spans")
        seen_spans = set()
        for span in spans:
            _span(span)
            key = (span["observation_id"], span["start"], span["end"], span["sha256"])
            if key in seen_spans:
                raise ValueError("Duplicate gold span")
            seen_spans.add(key)
        for field in ("topic", "rationale", "source_url"):
            if field in case:
                _text(case[field], field, 8192, empty=True)
    for field, keys in (("span_convention", {"unit", "start", "end", "sha256"}),
                        ("answerability_definition", {"answerable", "unanswerable"})):
        if field in cohort:
            _fields(cohort[field], keys, set(), field)
            for value in cohort[field].values():
                _text(value, field, 8192)
    if "span_convention" in cohort:
        convention = cohort["span_convention"]
        if (convention["unit"], convention["start"], convention["end"]) != ("UTF-8 bytes", "inclusive", "exclusive"):
            raise ValueError("Gold spans must use inclusive/exclusive UTF-8 byte offsets")
    if "limitations" in cohort:
        if type(cohort["limitations"]) is not list or len(cohort["limitations"]) > 64:
            raise ValueError("Cohort limitations must be a bounded array")
        for value in cohort["limitations"]:
            _text(value, "Limitation", 8192)
    if len(canonical(cohort).encode("utf-8")) > MAX_COHORT_BYTES:
        raise ValueError("Development cohort exceeds the canonical byte bound")
    return deepcopy(cohort)


def project_queries(cohort) -> list[dict]:
    """Return only candidate-visible IDs and query text, after cohort validation."""
    checked = _cohort(cohort)
    return [{"query_id": case["question_id"], "query": case["query"]} for case in checked["cases"]]


def _covered(span, hits):
    """Require continuous union coverage; overlaps cannot compensate for a gap."""
    cursor = span["start"]
    intervals = sorted((hit["start"], hit["end"]) for hit in hits
                       if hit["observation_id"] == span["observation_id"])
    for start, end in intervals:
        if end <= cursor:
            continue
        if start > cursor:
            return False
        cursor = end
        if cursor >= span["end"]:
            return True
    return False


def _ratio(numerator, denominator, aggregation=None):
    value = {"value": numerator / denominator if denominator else None,
             "numerator": numerator, "denominator": denominator}
    if aggregation:
        value["aggregation"] = aggregation
    return value


def _score_case(case, result):
    hits = result["hits"][:5]
    gold = case["gold_spans"]
    gold_sources = {span["observation_id"] for span in gold}
    answerable = case["answerability"] == "answerable"
    source_recall, span_recall = {}, {}
    for cutoff in CUTOFFS:
        prefix = hits[:cutoff]
        found_sources = {hit["observation_id"] for hit in prefix} & gold_sources
        source_recall[str(cutoff)] = _ratio(len(found_sources), len(gold_sources))
        span_recall[str(cutoff)] = _ratio(sum(_covered(span, prefix) for span in gold), len(gold))
    source_rank = next((index for index, hit in enumerate(hits, 1)
                        if hit["observation_id"] in gold_sources), None)
    span_rank = next((index for index in range(1, len(hits) + 1)
                      if any(_covered(span, hits[:index]) for span in gold)), None)
    return {
        "query_id": case["question_id"], "query": case["query"],
        "answerability": case["answerability"], "status": result["status"], "reason": result["reason"],
        "hit_count_at_5": len(hits), "gold_source_count": len(gold_sources), "gold_span_count": len(gold),
        "source_recall_at_k": source_recall, "gold_span_recall_at_k": span_recall,
        "source_first_relevant_rank_at_5": source_rank,
        "gold_span_first_covered_prefix_at_5": span_rank,
        "source_reciprocal_rank_at_5": (1 / source_rank if source_rank else 0.0) if answerable else None,
        "gold_span_reciprocal_rank_at_5": (1 / span_rank if span_rank else 0.0) if answerable else None,
        "unsupported_retrieval_at_5": bool(hits) if not answerable else None,
    }


def _implementation_identity():
    path, source, code = _PINNED_SELF
    if _MODULE.IMPLEMENTATION_CODE is not code or _MODULE.IMPLEMENTATION_SOURCE != source:
        raise ValueError("Evaluator reloaded after import; use a fresh reviewed process")
    if path.read_bytes() != source:
        raise ValueError("Evaluator source changed after import; restart before evaluating")
    if compile(source, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize) != code:
        raise ValueError("Executing evaluator code does not match retained source; discard stale bytecode")
    for module, dependency_code in _PINNED_DEPENDENCIES:
        if module.IMPLEMENTATION_CODE is not dependency_code:
            raise ValueError(f"Evaluator dependency reloaded: {module.__name__}; use a fresh reviewed process")
    for name, function, function_code in _FUNCTION_CODES:
        if globals().get(name) is not function or function.__code__ is not function_code:
            raise ValueError(f"Fixed evaluator callable changed: {name}; use a fresh reviewed process")
    if (resolve_span is not assertions.resolve_span or _read_transaction is not assertions._read_transaction
            or canonical is not store.canonical or digest is not store.digest
            or _RETRIEVAL_RUNTIME_SOURCES is not retrieval._runtime_sources):
        raise ValueError("Evaluator dependency callable changed; use a fresh reviewed process")
    hashes = {name: digest(raw) for name, raw in _RETRIEVAL_RUNTIME_SOURCES().items()}
    runtime = {"python_implementation": platform.python_implementation(), "python_version": sys.version,
               "python_build": list(platform.python_build()), "optimization": sys.flags.optimize,
               "unicode_version": unicodedata.unidata_version}
    return {"source_hash": digest(source), "dependencies": hashes,
            "dependencies_hash": _sha(hashes), "runtime": runtime, "runtime_hash": _sha(runtime),
            "contract": deepcopy(CONTRACT), "contract_hash": _sha(CONTRACT)}


def evaluate_retrieval(ledger, cohort, run_terminal_id) -> dict:
    """Score a validated completed receipt against a separate development cohort.

    This function is read-only. It rejects missing, failed, invalid and partial
    execution instead of presenting them as successful retrieval. All queries in
    a valid execution remain in the appropriate denominator, including empties.
    It validates retained bytes, not a fresh reproduction of the search.
    """
    if sys._getframe().f_code is not evaluate_retrieval.__code__:
        raise ValueError("Stale evaluator callable after reload; use a fresh reviewed process")
    if type(ledger) is not _LEDGER_CLASS or _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class; use a fresh reviewed process")
    evaluator = _implementation_identity()
    checked = _cohort(cohort)
    queries = project_queries(checked)
    _text(run_terminal_id, "Run terminal ID", MAX_ID_BYTES)
    with _read_transaction(ledger):
        run = retrieval.get_retrieval_run(ledger, run_terminal_id, verify_bytes=True)
        body = run["body"]
        if run["kind"] != "retrieval_completed" or body.get("result") != "completed":
            raise ValueError("Evaluation requires a completed retrieval execution")
        corpus = ledger.get(body["corpus_id"], "retrieval_corpus")
        cb = corpus["body"]
        if cb["config"]["top_k"] < max(CUTOFFS):
            raise ValueError("Evaluation at rank 5 requires corpus top_k of at least 5")
        if checked["snapshot_id"] != cb["snapshot_id"]:
            raise ValueError("Cohort snapshot does not match retrieval corpus")
        if body["request"]["queries"] != queries or body["query_hash"] != _sha(queries):
            raise ValueError("Run queries must match every cohort question ID and text in order")
        results = body["results"]
        if (type(results) is not list or len(results) != len(queries) or any(type(row) is not dict for row in results)
                or [{"query_id": row.get("query_id"), "query": row.get("query")} for row in results] != queries):
            raise ValueError("Run outputs must match all cohort queries; missing outputs are not successful empties")
        sources = {source["observation_id"]: source for source in cb["sources"]}
        # get_retrieval_run has already bounded and verified selected full blobs.
        # Only then may the public span resolver read those bounded sources.
        for case in checked["cases"]:
            for span in case["gold_spans"]:
                source = sources.get(span["observation_id"])
                if source is None:
                    raise ValueError("Gold observation must be selected in the retrieval corpus")
                if span["end"] > source["size"]:
                    raise ValueError("Gold span exceeds selected source byte bounds")
                resolve_span(ledger, checked["snapshot_id"], span)
        for result in results:
            if (result["status"] not in ("matched", "empty")
                    or (result["status"] == "matched") != bool(result["hits"])):
                raise ValueError("Invalid execution status; failures are not successful empty retrieval")
        per_case = [_score_case(case, result) for case, result in zip(checked["cases"], results)]
    positives = [row for row in per_case if row["answerability"] == "answerable"]
    unsupported = [row for row in per_case if row["answerability"] == "unanswerable"]
    metrics = {}
    for name in ("source_recall_at_k", "gold_span_recall_at_k"):
        metrics[name] = {str(k): _ratio(sum(row[name][str(k)]["value"] for row in positives),
                                       len(positives), "macro_query_mean") for k in CUTOFFS}
    for name in ("source", "gold_span"):
        metrics[name + "_mrr_at_5"] = _ratio(sum(row[name + "_reciprocal_rank_at_5"] for row in positives),
                                               len(positives), "macro_query_mean")
    metrics["unsupported_query_retrieval_rate_at_5"] = _ratio(
        sum(row["unsupported_retrieval_at_5"] for row in unsupported), len(unsupported))
    metrics["empty_query_rate"] = _ratio(sum(row["status"] == "empty" for row in per_case), len(per_case))
    empty_reasons = {}
    for row in per_case:
        if row["status"] == "empty":
            empty_reasons[row["reason"]] = empty_reasons.get(row["reason"], 0) + 1
    gold = [{"question_id": case["question_id"], "answerability": case["answerability"],
             "gold_spans": case["gold_spans"]} for case in checked["cases"]]
    identity = {
        "cohort_hash": _sha(checked), "gold_hash": _sha(gold), "query_hash": body["query_hash"],
        "snapshot_id": cb["snapshot_id"], "snapshot_hash": cb["snapshot_hash"],
        "snapshot_manifest_hash": cb["snapshot_manifest_hash"],
        "corpus_id": corpus["id"], "corpus_hash": corpus["hash"],
        "sources_hash": cb["sources_hash"], "sources": deepcopy(cb["sources"]),
        "passages_hash": cb["passages_hash"], "config_hash": cb["config_hash"],
        "retriever_implementation_hash": body["implementation_hash"],
        "retriever_artifacts": deepcopy(body["artifacts"]),
        "retriever_runtime": deepcopy(body["runtime"]), "retriever_runtime_hash": body["runtime_hash"],
        "evaluator": evaluator, "run_terminal_id": run["id"], "run_terminal_hash": run["hash"],
        "results_hash": body["results_hash"],
    }
    if _implementation_identity() != evaluator:
        raise ValueError("Evaluator implementation or runtime changed during evaluation")
    return {
        "schema_version": 1, "evaluation": CONTRACT["id"], "status": "completed", "cohort": "development",
        "identity": identity,
        "counts": {"queries": len(per_case), "answerable": len(positives), "unanswerable": len(unsupported),
                   "matched": sum(row["status"] == "matched" for row in per_case),
                   "empty": sum(row["status"] == "empty" for row in per_case),
                   "empty_reasons": empty_reasons, "execution_failures": 0, "missing_outputs": 0},
        "metrics": metrics, "per_case": per_case,
        "limitations": [
            "Builder-visible development data, not a sealed holdout or an unbiased generalization estimate.",
            "Only supplied gold spans count; alternative supporting evidence has not been adjudicated.",
            "Unsupported-query retrieval rate measures lexical retrieval, not answer hallucination or calibrated abstention.",
            "Invalid, rejected, missing or incomplete executions raise ValueError; they do not receive a metric report.",
            "Receipt validation verifies retained bytes and bindings; independent fresh runs are required to test reproducibility.",
            "No quality floor, improvement claim, confidence estimate or controller completion is inferred from this report.",
        ],
    }


# Finite guards for the local trusted-process implementation, not a security
# boundary against arbitrary Python mutation or an independent execution proof.
_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
                        if getattr(function, "__module__", None) == __name__ and hasattr(function, "__code__"))
