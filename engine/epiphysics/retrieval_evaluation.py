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

from . import assertions, retrieval_contracts, store
from .assertions import _read_transaction, resolve_span
from .store import canonical, digest

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions, retrieval_contracts)
)
_DEPENDENCIES = (store, assertions, retrieval_contracts)
_MODULE = sys.modules[__name__]
_PINNED_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_PINNED_DEPENDENCIES = tuple((module, module.IMPLEMENTATION_CODE) for module in _DEPENDENCIES)
_LEDGER_CLASS = store.Ledger
_RETRIEVAL_RUNTIME_SOURCES = retrieval_contracts._runtime_sources
MAX_CASES = 64
MAX_GOLD_PER_CASE = 64
MAX_COHORT_BYTES = 1_000_000
MAX_ID_BYTES = 512
MAX_QUERY_BYTES = 2048
MAX_SOURCE_BYTES = 1_000_000
CUTOFFS = (1, 3, 5)
MAX_BUNDLES_PER_CASE = 4
MAX_SPANS_PER_BUNDLE = 8
MAX_SUPPORT_REFS_PER_CASE = 32
FAMILY_LABELS = ("software_service", "organization", "person_role", "contract_obligation",
                 "physical_asset", "collective", "representation")
RELATION_LABELS = ("identity", "authority", "dependency", "obligation", "ordering",
                   "time_condition", "quantity_unit", "boundary", "representation_assurance")
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
COVERAGE_CONTRACT = {
    "id": "retrieval-coverage-evaluation-v2",
    "cohort": "fresh builder-visible development; not a sealed holdout",
    "source_scope": "selected_corpus_only",
    "support_semantics": "any_complete_bundle_v1",
    "cutoffs": list(CUTOFFS), "minimum_run_top_k": max(CUTOFFS),
    "complete_support": "macro over answerable queries: any bundle with every required span fully covered by raw interval union",
    "complete_support_mrr": "macro over answerable queries: reciprocal earliest prefix through 5 completing a whole bundle; zero for a miss",
    "complete_source_set": "macro over answerable queries: all distinct sources of any one bundle represented; not sufficient support",
    "unsupported_query_retrieval_rate": CONTRACT["unsupported_query_retrieval_rate"],
    "empty_outputs": CONTRACT["empty_outputs"],
    "invalid_execution": CONTRACT["invalid_execution"],
    "empty_denominator": CONTRACT["empty_denominator"],
    "span_unit": CONTRACT["span_unit"],
    "pair_semantics": "one supported and one unsupported case per pair; every case occurs exactly once",
    "pair_bucket_cutoff": 5,
    "group_semantics": "overlapping declared tags; supported rates use all answerable cases in the group; no family macro",
    "family_labels": list(FAMILY_LABELS), "relation_labels": list(RELATION_LABELS),
    "bounds": {"cases": MAX_CASES, "bundles_per_case": MAX_BUNDLES_PER_CASE,
               "spans_per_bundle": MAX_SPANS_PER_BUNDLE, "span_references_per_case": MAX_SUPPORT_REFS_PER_CASE,
               "cohort_bytes": MAX_COHORT_BYTES, "query_bytes": MAX_QUERY_BYTES,
               "id_bytes": MAX_ID_BYTES, "metadata_bytes": 8192, "limitations": 64,
               "tags_per_case": 3, "related_prior_question_ids": MAX_CASES},
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


def _cohort_v1(cohort):
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


def _id_list(value, label, maximum, *, minimum=0):
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} requires a bounded array")
    seen = set()
    for item in value:
        _text(item, label, MAX_ID_BYTES)
        if item in seen:
            raise ValueError(f"Duplicate {label}")
        seen.add(item)
    return seen


def _tags(value, vocabulary, label):
    selected = _id_list(value, label, 3)
    if not selected <= set(vocabulary):
        raise ValueError(f"Unknown {label}")


def _cohort_v2(cohort):
    _fields(cohort, {"schema_version", "snapshot_id", "cohort", "cohort_id", "source_scope",
                    "support_semantics", "cases", "pairs", "limitations"}, set(), "coverage cohort")
    if type(cohort["schema_version"]) is not int or cohort["schema_version"] != 2:
        raise ValueError("Coverage cohort schema_version must be 2")
    if (cohort["cohort"] != "development" or cohort["source_scope"] != "selected_corpus_only"
            or cohort["support_semantics"] != "any_complete_bundle_v1"):
        raise ValueError("Coverage requires selected-corpus builder-visible development and complete-bundle semantics")
    for field in ("snapshot_id", "cohort_id"):
        _text(cohort[field], field, MAX_ID_BYTES)
    cases, pairs = cohort["cases"], cohort["pairs"]
    if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError(f"Coverage requires 1 to {MAX_CASES} cases")
    if type(pairs) is not list or not 1 <= len(pairs) <= MAX_CASES // 2 or len(cases) != 2 * len(pairs):
        raise ValueError("Coverage requires exactly one matched pair for every two cases")
    by_id = {}
    for case in cases:
        _fields(case, {"question_id", "query", "pair_id", "answerability", "support_bundles",
                       "rationale", "family_tags", "relation_tags", "novelty"}, set(), "coverage case")
        for field in ("question_id", "pair_id"):
            _text(case[field], field, MAX_ID_BYTES)
        _text(case["query"], "Query", MAX_QUERY_BYTES, empty=True)
        _text(case["rationale"], "Rationale", 8192)
        if case["question_id"] in by_id:
            raise ValueError("Duplicate question ID")
        by_id[case["question_id"]] = case
        if case["answerability"] not in ("answerable", "unanswerable"):
            raise ValueError("Answerability must be answerable or unanswerable")
        _tags(case["family_tags"], FAMILY_LABELS, "family tags")
        _tags(case["relation_tags"], RELATION_LABELS, "relation tags")
        novelty = case["novelty"]
        _fields(novelty, {"related_prior_question_ids", "distinction"}, set(), "novelty")
        _id_list(novelty["related_prior_question_ids"], "related prior question IDs", MAX_CASES)
        _text(novelty["distinction"], "Novelty distinction", 8192)
        bundles = case["support_bundles"]
        if type(bundles) is not list or len(bundles) > MAX_BUNDLES_PER_CASE:
            raise ValueError("Support bundles must be a bounded array")
        if bool(bundles) != (case["answerability"] == "answerable"):
            raise ValueError("Answerable cases require support bundles; unsupported cases require none")
        bundle_ids, bundle_sets, total = set(), set(), 0
        for bundle in bundles:
            _fields(bundle, {"bundle_id", "spans"}, set(), "support bundle")
            _text(bundle["bundle_id"], "Bundle ID", MAX_ID_BYTES)
            if bundle["bundle_id"] in bundle_ids:
                raise ValueError("Duplicate bundle ID within a case")
            bundle_ids.add(bundle["bundle_id"])
            spans = bundle["spans"]
            if type(spans) is not list or not 1 <= len(spans) <= MAX_SPANS_PER_BUNDLE:
                raise ValueError("Each support bundle requires 1 to 8 nonempty spans")
            total += len(spans)
            if total > MAX_SUPPORT_REFS_PER_CASE:
                raise ValueError("Too many support span references")
            keys = set()
            for span in spans:
                _span(span)
                key = (span["observation_id"], span["start"], span["end"], span["sha256"])
                if key in keys:
                    raise ValueError("Duplicate span within support bundle")
                keys.add(key)
            key = tuple(sorted(keys))
            if key in bundle_sets:
                raise ValueError("Duplicate support bundle span set")
            bundle_sets.add(key)
    used_cases, pair_ids = set(), set()
    for pair in pairs:
        _fields(pair, {"pair_id", "supported_question_id", "unsupported_question_id", "anchor_observation_ids",
                       "changed_requirement", "matching_rationale"}, set(), "matched pair")
        for field in ("pair_id", "supported_question_id", "unsupported_question_id"):
            _text(pair[field], field, MAX_ID_BYTES)
        if pair["pair_id"] in pair_ids:
            raise ValueError("Duplicate pair ID")
        pair_ids.add(pair["pair_id"])
        _id_list(pair["anchor_observation_ids"], "pair anchor IDs", retrieval_contracts.MAX_SOURCES, minimum=1)
        for field in ("changed_requirement", "matching_rationale"):
            _text(pair[field], field, 8192)
        for field, label in (("supported_question_id", "answerable"), ("unsupported_question_id", "unanswerable")):
            question_id = pair[field]
            case = by_id.get(question_id)
            if (case is None or question_id in used_cases or case["answerability"] != label
                    or case["pair_id"] != pair["pair_id"]):
                raise ValueError("Pairs must bijectively match each case and its answerability")
            used_cases.add(question_id)
    if used_cases != set(by_id):
        raise ValueError("Every case must occur in exactly one pair")
    if type(cohort["limitations"]) is not list or len(cohort["limitations"]) > 64:
        raise ValueError("Cohort limitations must be a bounded array")
    for value in cohort["limitations"]:
        _text(value, "Limitation", 8192)
    if len(canonical(cohort).encode("utf-8")) > MAX_COHORT_BYTES:
        raise ValueError("Coverage cohort exceeds the canonical byte bound")
    return deepcopy(cohort)


def _cohort(cohort):
    if type(cohort) is not dict or type(cohort.get("schema_version")) is not int:
        raise ValueError("Cohort requires an integer schema_version")
    if cohort["schema_version"] == 1:
        return _cohort_v1(cohort)
    if cohort["schema_version"] == 2:
        return _cohort_v2(cohort)
    raise ValueError("Cohort schema_version must be 1 or 2")


def cohort_identity(cohort):
    """Hash normalized labels separately from exact candidate-visible queries."""
    checked = _cohort(cohort)
    field = "gold_spans" if checked["schema_version"] == 1 else "support_bundles"
    gold = [{"question_id": case["question_id"], "answerability": case["answerability"], field: case[field]}
            for case in checked["cases"]]
    queries = [{"query_id": case["question_id"], "query": case["query"]} for case in checked["cases"]]
    return {"cohort_hash": _sha(checked), "gold_hash": _sha(gold), "query_hash": _sha(queries)}


def coverage_inventory(cohort, selected_source_ids):
    """Describe annotations and selected sources without scoring any outputs."""
    checked = _cohort(cohort)
    if checked["schema_version"] != 2:
        raise ValueError("Coverage inventory requires cohort schema 2")
    selected = _id_list(selected_source_ids, "selected source IDs", retrieval_contracts.MAX_SOURCES, minimum=1)
    cases = checked["cases"]
    for pair in checked["pairs"]:
        if not set(pair["anchor_observation_ids"]) <= selected:
            raise ValueError("Pair anchor must be selected in the retrieval corpus")
    for case in cases:
        if any(span["observation_id"] not in selected for bundle in case["support_bundles"] for span in bundle["spans"]):
            raise ValueError("Gold observation must be selected in the retrieval corpus")
    groups = {}
    for name, field, labels in (("families", "family_tags", FAMILY_LABELS), ("relations", "relation_tags", RELATION_LABELS)):
        groups[name] = {}
        for label in labels:
            eligible = [case for case in cases if label in case[field]]
            positives = sum(case["answerability"] == "answerable" for case in eligible)
            groups[name][label] = {"queries": len(eligible), "answerable": positives,
                                   "unanswerable": len(eligible) - positives,
                                   "status": "represented" if eligible else "unmeasured"}
    positives = sum(case["answerability"] == "answerable" for case in cases)
    return {"counts": {"queries": len(cases), "answerable": positives, "unanswerable": len(cases) - positives,
                       "pairs": len(checked["pairs"]), "selected_sources": len(selected)},
            "feature_inventory": {
                "alternative_support_cases": sum(len(case["support_bundles"]) > 1 for case in cases),
                "joint_support_cases": sum(any(len(bundle["spans"]) > 1 for bundle in case["support_bundles"]) for case in cases),
                "multisource_support_cases": sum(any(len({span["observation_id"] for span in bundle["spans"]}) > 1
                                                     for bundle in case["support_bundles"]) for case in cases)}, **groups}


def validate_coverage_sources(ledger, cohort, corpus):
    """Validate selected, eligible, byte-exact support and anchors without a run."""
    checked = _cohort(cohort)
    if checked["schema_version"] != 2:
        raise ValueError("Coverage source validation requires cohort schema 2")
    if type(ledger) is not _LEDGER_CLASS or _LEDGER_CLASS is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class; use a fresh reviewed process")
    with _read_transaction(ledger):
        now = retrieval_contracts._time(ledger.clock(), "Ledger clock")
        retained, _ = retrieval_contracts._checked_corpus(ledger, corpus["id"], now, verify_bytes=True)
        if retained != corpus or checked["snapshot_id"] != retained["body"]["snapshot_id"]:
            raise ValueError("Cohort snapshot or corpus does not match retained retrieval corpus")
        sources = retrieval_contracts._projection_sources(ledger, retained, now)
        coverage_inventory(checked, list(sources))
        for case in checked["cases"]:
            for bundle in case["support_bundles"]:
                for span in bundle["spans"]:
                    raw = sources[span["observation_id"]]["raw"]
                    if span["end"] > len(raw):
                        raise ValueError("Gold span exceeds selected source byte bounds")
                    selected = raw[span["start"]:span["end"]]
                    if digest(selected) != span["sha256"]:
                        raise ValueError("Span hash mismatch")
                    try:
                        selected.decode("utf-8", errors="strict")
                    except UnicodeDecodeError as error:
                        raise ValueError("Gold span must have valid UTF-8 boundaries") from error
    return checked


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


def _score_coverage_case(case, result):
    hits = result["hits"][:max(CUTOFFS)]
    answerable = case["answerability"] == "answerable"
    bundles = []
    for bundle in case["support_bundles"]:
        spans = bundle["spans"]
        covered = {str(k): sum(_covered(span, hits[:k]) for span in spans) for k in CUTOFFS}
        first = next((rank for rank in range(1, len(hits) + 1)
                      if all(_covered(span, hits[:rank]) for span in spans)), None)
        bundles.append({"bundle_id": bundle["bundle_id"], "required_spans": len(spans),
                        "covered_spans_at_k": covered,
                        "complete_at_k": {str(k): covered[str(k)] == len(spans) for k in CUTOFFS},
                        "first_complete_prefix_at_5": first})
    completed = [row["first_complete_prefix_at_5"] for row in bundles
                 if row["first_complete_prefix_at_5"] is not None]
    first = min(completed) if completed else None
    source_sets = [{span["observation_id"] for span in bundle["spans"]} for bundle in case["support_bundles"]]
    return {"query_id": case["question_id"], "query": case["query"], "pair_id": case["pair_id"],
            "answerability": case["answerability"], "family_tags": list(case["family_tags"]),
            "relation_tags": list(case["relation_tags"]), "status": result["status"], "reason": result["reason"],
            "hit_count_at_5": len(hits),
            "raw_windows": [{key: hit[key] for key in ("rank", "observation_id", "start", "end", "sha256")} for hit in hits],
            "complete_support_at_k": {str(k): any(row["complete_at_k"][str(k)] for row in bundles)
                                       if answerable else None for k in CUTOFFS},
            "complete_source_set_at_k": {str(k): any(sources <= {hit["observation_id"] for hit in hits[:k]}
                                                     for sources in source_sets) if answerable else None for k in CUTOFFS},
            "complete_support_first_covered_prefix_at_5": first,
            "complete_support_reciprocal_rank_at_5": (1 / first if first else 0.0) if answerable else None,
            "unsupported_retrieval_at_5": bool(hits) if not answerable else None,
            "bundles": bundles}


def _coverage_rates(rows):
    positives = [row for row in rows if row["answerability"] == "answerable"]
    unsupported = [row for row in rows if row["answerability"] == "unanswerable"]
    return {"complete_support_rate_at_k": {
                str(k): _ratio(sum(row["complete_support_at_k"][str(k)] for row in positives),
                               len(positives), "macro_query_mean") for k in CUTOFFS},
            "unsupported_query_retrieval_rate_at_5": _ratio(
                sum(row["unsupported_retrieval_at_5"] for row in unsupported), len(unsupported), "query_fraction")}


def _score_coverage(cohort, results, selected_source_ids):
    inventory = coverage_inventory(cohort, selected_source_ids)
    rows = [_score_coverage_case(case, result) for case, result in zip(cohort["cases"], results)]
    positives = [row for row in rows if row["answerability"] == "answerable"]
    metrics = _coverage_rates(rows)
    metrics["complete_source_set_rate_at_k"] = {
        str(k): _ratio(sum(row["complete_source_set_at_k"][str(k)] for row in positives),
                       len(positives), "macro_query_mean") for k in CUTOFFS}
    metrics["complete_support_mrr_at_5"] = _ratio(
        sum(row["complete_support_reciprocal_rank_at_5"] for row in positives), len(positives), "macro_query_mean")
    metrics["empty_query_rate"] = _ratio(sum(row["status"] == "empty" for row in rows), len(rows), "query_fraction")
    metrics["empty_query_rate_by_answerability"] = {}
    empty_reasons = {}
    for label in ("answerable", "unanswerable"):
        group = [row for row in rows if row["answerability"] == label]
        metrics["empty_query_rate_by_answerability"][label] = _ratio(
            sum(row["status"] == "empty" for row in group), len(group), "query_fraction")
    for row in rows:
        if row["status"] == "empty":
            empty_reasons[row["reason"]] = empty_reasons.get(row["reason"], 0) + 1
    groups = {}
    for name, field in (("families", "family_tags"), ("relations", "relation_tags")):
        groups[name] = {label: {**counts, **_coverage_rates([row for row in rows if label in row[field]])}
                        for label, counts in inventory[name].items()}
    by_id = {row["query_id"]: row for row in rows}
    matched = []
    buckets = {"cutoff": 5, "supported_yes_unsupported_yes": 0, "supported_yes_unsupported_no": 0,
               "supported_no_unsupported_yes": 0, "supported_no_unsupported_no": 0}
    for pair in cohort["pairs"]:
        positive, negative = by_id[pair["supported_question_id"]], by_id[pair["unsupported_question_id"]]
        support = "yes" if positive["complete_support_at_k"]["5"] else "no"
        unsupported = "yes" if negative["unsupported_retrieval_at_5"] else "no"
        buckets[f"supported_{support}_unsupported_{unsupported}"] += 1
        matched.append({"pair_id": pair["pair_id"], "supported_question_id": positive["query_id"],
                        "unsupported_question_id": negative["query_id"],
                        "supported_complete_support_at_k": deepcopy(positive["complete_support_at_k"]),
                        "unsupported_retrieval_at_5": negative["unsupported_retrieval_at_5"],
                        "unsupported_status": negative["status"], "unsupported_reason": negative["reason"],
                        "supported_raw_windows": deepcopy(positive["raw_windows"]),
                        "unsupported_raw_windows": deepcopy(negative["raw_windows"])})
    return {"counts": {**inventory["counts"], "matched": sum(row["status"] == "matched" for row in rows),
                       "empty": sum(row["status"] == "empty" for row in rows), "empty_reasons": empty_reasons,
                       "execution_failures": 0, "missing_outputs": 0},
            "metrics": metrics, "per_case": rows, "matched_pairs": matched, "pair_buckets": buckets,
            "feature_inventory": inventory["feature_inventory"], **groups}


def _implementation_identity(cohort_schema_version=1):
    if type(cohort_schema_version) is not int or cohort_schema_version not in (1, 2):
        raise ValueError("Evaluator identity requires cohort schema 1 or 2")
    contract = CONTRACT if cohort_schema_version == 1 else COVERAGE_CONTRACT
    path, source, code = _PINNED_SELF
    if _MODULE.IMPLEMENTATION_CODE is not code or _MODULE.IMPLEMENTATION_SOURCE != source:
        raise ValueError("Evaluator reloaded after import; use a fresh reviewed process")
    if (len(source) > MAX_SOURCE_BYTES or path.is_symlink() or not path.is_file()
            or path.stat().st_size != len(source)):
        raise ValueError("Evaluator source changed after import; restart before evaluating")
    with path.open("rb") as stream:
        if stream.read(len(source) + 1) != source:
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
            or _RETRIEVAL_RUNTIME_SOURCES is not retrieval_contracts._runtime_sources):
        raise ValueError("Evaluator dependency callable changed; use a fresh reviewed process")
    hashes = {name: digest(raw) for name, raw in _RETRIEVAL_RUNTIME_SOURCES().items()}
    runtime = {"python_implementation": platform.python_implementation(), "python_version": sys.version,
               "python_build": list(platform.python_build()), "optimization": sys.flags.optimize,
               "unicode_version": unicodedata.unidata_version}
    return {"source_hash": digest(source), "dependencies": hashes,
            "dependencies_hash": _sha(hashes), "runtime": runtime, "runtime_hash": _sha(runtime),
            "contract": deepcopy(contract), "contract_hash": _sha(contract)}


def evaluator_identity(cohort_schema_version=1):
    """Return the guarded loaded scorer identity for the selected cohort contract."""
    return _implementation_identity(cohort_schema_version)


def _candidate_identity(body):
    """Historical candidate metadata is data, separate from the scorer closure."""
    artifacts = body["artifacts"]
    def content(ref):
        return {key: ref[key] for key in ("content_hash", "size")}
    if body["schema_version"] == 1:
        algorithm = {"kind": "legacy-coupled-v1", "implementation": content(artifacts["implementation"]),
                     "dependencies": {name: content(ref) for name, ref in artifacts["dependencies"].items()},
                     "config_hash": body["config_hash"], "runtime": deepcopy(body["runtime"])}
        value = {"algorithm": algorithm, "algorithm_hash": _sha(algorithm), "projection": None}
    else:
        algorithm = {"kind": "fixed-indexing-v2", "indexing_recipe": body["indexing_recipe"],
                     "recipe": content(artifacts["recipe"]),
                     "indexing": content(artifacts["dependencies"]["epiphysics.retrieval_indexing"]),
                     "dependencies": {name: content(ref) for name, ref in artifacts["dependencies"].items()
                                      if name != "epiphysics.retrieval_indexing"},
                     "stdlib": {name: content(ref) for name, ref in artifacts["stdlib"].items()},
                     "config_hash": body["config_hash"], "runtime": deepcopy(body["runtime"])}
        value = {"algorithm": algorithm, "algorithm_hash": _sha(algorithm),
                 "projection": {"sha256": body["projection_hash"], "size": artifacts["projection"]["size"]}}
    return {**value, "hash": _sha(value)}


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
    checked = _cohort(cohort)
    version = checked["schema_version"]
    evaluator = _implementation_identity(version)
    queries = project_queries(checked)
    _text(run_terminal_id, "Run terminal ID", MAX_ID_BYTES)
    with _read_transaction(ledger):
        run = retrieval_contracts.get_retrieval_run(ledger, run_terminal_id, verify_bytes=True)
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
        if version == 2:
            validate_coverage_sources(ledger, checked, corpus)
        else:
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
        per_case = ([_score_case(case, result) for case, result in zip(checked["cases"], results)]
                    if version == 1 else [])
    identity = {
        **cohort_identity(checked),
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
        "receipt_schema_version": body["schema_version"], "candidate": _candidate_identity(body),
        "execution": {"schema_version": body["schema_version"], "runner_implementation_hash": body["implementation_hash"],
                      "runner_artifact": deepcopy(body["artifacts"]["implementation"]),
                      "run_terminal_id": run["id"], "run_terminal_hash": run["hash"]},
    }
    if version == 2:
        scored = _score_coverage(checked, results, list(sources))
        if _implementation_identity(version) != evaluator:
            raise ValueError("Evaluator implementation or runtime changed during evaluation")
        return {"schema_version": 2, "evaluation": COVERAGE_CONTRACT["id"], "status": "completed",
                "cohort": "development", "identity": identity, **scored,
                "limitations": [
                    "Fresh builder-visible development over selected sources, not a sealed holdout or generalization estimate.",
                    "Complete raw-span support is not answer correctness or proof that every sufficient alternative was annotated.",
                    "Unsupported-query retrieval measures lexical matches, not hallucination or calibrated abstention.",
                    "Family/relation tags overlap; unrepresented groups remain unmeasured and no family macro is computed.",
                    "Matched pairs are related curated cases, not independent population samples.",
                    "Invalid or incomplete runs receive no metric report; separate executions are required for reproduction.",
                ]}
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
    if _implementation_identity(version) != evaluator:
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
