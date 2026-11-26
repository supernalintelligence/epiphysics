"""Owned synthetic fixtures; these are conformance tests, not retrieval quality."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import retrieval
from epiphysics import retrieval_evaluation as evaluation
from epiphysics.store import Ledger, canonical, digest


def span(observation_id="source-a", start=0, end=10, raw=None):
    return {"observation_id": observation_id, "start": start, "end": end,
            "sha256": digest(raw[start:end]) if raw is not None else "a" * 64}


def case(question_id="q1", query="owned query", gold=None, answerability="answerable"):
    return {"question_id": question_id, "query": query, "answerability": answerability,
            "gold_spans": [span()] if gold is None and answerability == "answerable" else (gold or [])}


def cohort(cases=None, snapshot_id="snapshot"):
    return {"schema_version": 1, "snapshot_id": snapshot_id, "cohort": "development",
            "cases": [case()] if cases is None else cases}


def result(hits):
    return {"query_id": "q1", "query": "owned query", "status": "matched" if hits else "empty",
            "reason": None if hits else "no_lexical_match",
            "hits": [{**hit, "rank": rank, "score": -1.0} for rank, hit in enumerate(hits, 1)]}


class DevelopmentContractTests(unittest.TestCase):
    def test_projection_contains_exactly_id_and_query_and_is_detached(self):
        data = cohort()
        data["cases"][0].update({"topic": "private topic", "rationale": "private gold rationale",
                                 "source_url": "https://example.invalid/owned"})
        projected = evaluation.project_queries(data)
        self.assertEqual(projected, [{"query_id": "q1", "query": "owned query"}])
        projected[0]["query"] = "modified"
        self.assertEqual(data["cases"][0]["query"], "owned query")
        self.assertNotIn("source-a", canonical(projected))

    def test_invalid_cohort_shapes_labels_and_bounds_rejected(self):
        examples = []
        for field, value in (("schema_version", True), ("cohort", "sealed_holdout"),
                             ("cases", []), ("cases", [case(str(i)) for i in range(65)])):
            data = cohort()
            data[field] = value
            examples.append(data)
        for field, value in (("question_id", "q" * 513), ("query", "q" * 2049),
                             ("query", "\ud800"), ("answerability", "unknown"),
                             ("gold_spans", []), ("gold_spans", [span()] * 65)):
            data = cohort()
            data["cases"][0][field] = value
            examples.append(data)
        data = cohort()
        data["cases"].append(deepcopy(data["cases"][0]))
        examples.append(data)
        examples.append(cohort([case(answerability="unanswerable", gold=[span()])]))
        examples.append(cohort([case(gold=[span(), span()])]))
        for field, value in (("start", True), ("start", -1), ("end", 0),
                             ("end", 1024 * 1024 + 1), ("sha256", "not-a-hash")):
            data = cohort()
            data["cases"][0]["gold_spans"][0][field] = value
            examples.append(data)
        data = cohort()
        data["unexpected"] = "unbounded metadata"
        examples.append(data)
        data = cohort()
        data["cases"][0]["expected_answer"] = "not an allowed field"
        examples.append(data)
        data = cohort()
        data["span_convention"] = {"unit": "characters", "start": "inclusive", "end": "exclusive", "sha256": "slice"}
        examples.append(data)
        for index, data in enumerate(examples):
            with self.subTest(index=index), self.assertRaises(ValueError):
                evaluation.project_queries(data)

    def test_cohort_total_byte_bound(self):
        data = cohort([case(str(index)) for index in range(64)])
        for row in data["cases"]:
            row.update({"topic": "t" * 8192, "rationale": "r" * 8192, "source_url": "s" * 8192})
        with self.assertRaisesRegex(ValueError, "canonical byte bound"):
            evaluation.project_queries(data)

    def test_empty_query_is_valid_and_still_projected(self):
        self.assertEqual(evaluation.project_queries(cohort([case(query="")])), [{"query_id": "q1", "query": ""}])


class SpanAndRankScoringTests(unittest.TestCase):
    def test_source_recall_is_distinct_and_mrr_uses_rank(self):
        data = case(gold=[span("a"), span("a", 10, 20), span("b")])
        scored = evaluation._score_case(data, result([span("unrelated"), span("a"), span("a", 10, 20), span("b")]))
        self.assertEqual(scored["source_recall_at_k"]["1"], {"value": 0.0, "numerator": 0, "denominator": 2})
        self.assertEqual(scored["source_recall_at_k"]["3"]["value"], 0.5)
        self.assertEqual(scored["source_recall_at_k"]["5"]["value"], 1.0)
        self.assertEqual(scored["gold_span_recall_at_k"]["3"]["value"], 2 / 3)
        self.assertEqual(scored["source_reciprocal_rank_at_5"], 0.5)
        self.assertEqual(scored["gold_span_reciprocal_rank_at_5"], 0.5)

    def test_span_recall_and_mrr_use_complete_prefix_union(self):
        data = case(gold=[span("a", 0, 10)])
        scored = evaluation._score_case(data, result([span("a", 0, 6), span("a", 4, 10)]))
        self.assertEqual(scored["gold_span_recall_at_k"]["1"]["value"], 0.0)
        self.assertEqual(scored["gold_span_recall_at_k"]["3"]["value"], 1.0)
        self.assertEqual(scored["source_reciprocal_rank_at_5"], 1.0)
        self.assertEqual(scored["gold_span_first_covered_prefix_at_5"], 2)
        self.assertEqual(scored["gold_span_reciprocal_rank_at_5"], 0.5)

    def test_adjoining_intervals_cover_but_one_byte_gap_does_not(self):
        data = case(gold=[span("a", 0, 10)])
        joined = evaluation._score_case(data, result([span("a", 0, 5), span("a", 5, 10)]))
        gapped = evaluation._score_case(data, result([span("a", 0, 5), span("a", 6, 10)]))
        self.assertEqual(joined["gold_span_recall_at_k"]["5"]["value"], 1.0)
        self.assertEqual(gapped["gold_span_recall_at_k"]["5"]["value"], 0.0)
        self.assertEqual(gapped["gold_span_reciprocal_rank_at_5"], 0.0)

    def test_overlap_double_count_and_tiny_overlap_never_fill_missing_bytes(self):
        data = case(gold=[span("a", 0, 10)])
        for hits in ([span("a", 0, 6), span("a", 0, 6)], [span("a", 9, 12)],
                     [span("a", 0, 5), span("b", 5, 10)]):
            with self.subTest(hits=hits):
                scored = evaluation._score_case(data, result(hits))
                self.assertEqual(scored["gold_span_recall_at_k"]["5"]["value"], 0.0)
                self.assertEqual(scored["gold_span_reciprocal_rank_at_5"], 0.0)

    def test_sixth_hit_does_not_count_at_five(self):
        scored = evaluation._score_case(case(), result([span("other", i, i + 1) for i in range(5)] + [span()]))
        self.assertEqual(scored["hit_count_at_5"], 5)
        self.assertEqual(scored["source_reciprocal_rank_at_5"], 0.0)
        self.assertEqual(scored["gold_span_recall_at_k"]["5"]["value"], 0.0)

    def test_empty_positive_is_zero_and_unsupported_is_not_a_perfect_positive(self):
        scored = evaluation._score_case(case(), result([]))
        self.assertEqual(scored["source_reciprocal_rank_at_5"], 0.0)
        self.assertEqual(scored["gold_span_recall_at_k"]["5"]["value"], 0.0)
        unsupported = evaluation._score_case(case(answerability="unanswerable"), result([]))
        self.assertIsNone(unsupported["gold_span_recall_at_k"]["5"]["value"])
        self.assertIsNone(unsupported["source_reciprocal_rank_at_5"])
        self.assertFalse(unsupported["unsupported_retrieval_at_5"])


class EvaluatorImplementationIdentityTests(unittest.TestCase):
    def isolated_check(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(Path(evaluation.__file__).parent, root / "epiphysics",
                            ignore=shutil.ignore_patterns("__pycache__"))
            program = r'''
import importlib,json,os,py_compile,sys
from pathlib import Path
mode=sys.argv[1]
if mode == 'stale_bytecode':
    path=Path('epiphysics/retrieval_evaluation.py').resolve()
    original=path.read_bytes()
    stat=path.stat()
    py_compile.compile(str(path),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
    changed=original.replace(b'MAX_CASES = 64',b'MAX_CASES = 63',1)
    assert changed != original and len(changed) == len(original)
    path.write_bytes(changed)
    os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
if mode == 'dependency_reload_before':
    from epiphysics import retrieval,assertions
    importlib.reload(assertions)
from epiphysics import retrieval_evaluation as evaluation
from epiphysics.store import Ledger
ledger=Ledger(Path('ledger'))
evaluate=evaluation.evaluate_retrieval
if mode == 'dependency_reload_after':
    from epiphysics import assertions
    importlib.reload(assertions)
if mode == 'stale_alias':
    importlib.reload(evaluation)
try:
    try:
        if mode == 'stale_alias':
            evaluate(ledger,{},'unused')
        else:
            evaluation._implementation_identity()
        outcome={'result':'unexpected_success'}
    except ValueError as error:
        outcome={'result':'refused','message':str(error)}
    if mode == 'stale_bytecode':
        outcome.update(loaded_limit=evaluation.MAX_CASES,captured_is_disk=evaluation.IMPLEMENTATION_SOURCE == changed)
    print(json.dumps(outcome))
finally:
    ledger.close()
'''
            environment = {**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
            completed = subprocess.run([sys.executable, "-s", "-c", program, mode], cwd=root,
                                       env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)

    def test_dependency_reload_after_import_is_refused(self):
        outcome = self.isolated_check("dependency_reload_after")
        self.assertEqual(outcome["result"], "refused")
        self.assertIn("Evaluator dependency reloaded", outcome["message"])

    def test_transitive_dependency_reload_before_import_is_refused(self):
        outcome = self.isolated_check("dependency_reload_before")
        self.assertEqual(outcome["result"], "refused")
        self.assertRegex(outcome["message"], "reloaded|dependency callable changed")

    def test_stale_evaluator_callable_after_reload_is_refused(self):
        outcome = self.isolated_check("stale_alias")
        self.assertEqual(outcome["result"], "refused")
        self.assertIn("Stale evaluator callable", outcome["message"])

    def test_timestamp_valid_stale_bytecode_is_refused(self):
        outcome = self.isolated_check("stale_bytecode")
        self.assertEqual(outcome["result"], "refused")
        self.assertEqual(outcome["loaded_limit"], 64)
        self.assertTrue(outcome["captured_is_disk"])
        self.assertIn("does not match retained source", outcome["message"])

    def test_changed_imported_span_resolver_is_refused(self):
        with patch.object(evaluation, "resolve_span", lambda *args: b"unverified"):
            with self.assertRaisesRegex(ValueError, "dependency callable changed"):
                evaluation._implementation_identity()


class CompletedRetrievalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.temp.name) / "ledger", clock=lambda: "2030-01-01T00:00:00Z")
        self.raw_a = b"alpha red kite floats over the owned meadow."
        self.raw_b = b"beta blue boat sails across the owned lake."
        self.a = self.ledger.capture("synthetic:owned-a", self.raw_a, event_id="owned-a")
        self.b = self.ledger.capture("synthetic:owned-b", self.raw_b, event_id="owned-b")
        self.excluded = self.ledger.capture("synthetic:excluded", b"excluded data", event_id="excluded")
        self.snapshot = self.ledger.snapshot()
        self.corpus = retrieval.freeze_retrieval_corpus(
            self.ledger, self.snapshot["id"], [self.a["id"], self.b["id"]], config=deepcopy(retrieval.DEFAULT_CONFIG))
        self.data = cohort([
            case("a", "alpha", [span(self.a["id"], 0, len(self.raw_a), self.raw_a)]),
            case("b", "beta", [span(self.b["id"], 0, len(self.raw_b), self.raw_b)]),
            case("miss", "missingzz", [span(self.a["id"], 0, len(self.raw_a), self.raw_a)]),
            case("unsupported-hit", "alpha", answerability="unanswerable"),
            case("unsupported-empty", "missingzz", answerability="unanswerable"),
        ], self.snapshot["id"])
        self.counter = 0

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def run_queries(self, queries=None):
        self.counter += 1
        return retrieval.run_lexical_retrieval(
            self.ledger, self.corpus["id"], evaluation.project_queries(self.data) if queries is None else queries,
            run_key=f"evaluation-test-{self.counter}")

    def test_real_receipt_scores_all_queries_and_retains_identity_without_writes(self):
        run = self.run_queries()
        before = len(self.ledger.events())
        report = evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])
        self.assertEqual(len(self.ledger.events()), before)
        self.assertEqual(report["counts"], {"queries": 5, "answerable": 3, "unanswerable": 2,
                         "matched": 3, "empty": 2, "empty_reasons": {"no_lexical_match": 2},
                         "execution_failures": 0, "missing_outputs": 0})
        for name in ("source_recall_at_k", "gold_span_recall_at_k"):
            self.assertEqual(report["metrics"][name]["5"]["value"], 2 / 3)
            self.assertEqual(report["metrics"][name]["5"]["numerator"], 2.0)
            self.assertEqual(report["metrics"][name]["5"]["denominator"], 3)
        self.assertEqual(report["metrics"]["source_mrr_at_5"]["value"], 2 / 3)
        self.assertEqual(report["metrics"]["gold_span_mrr_at_5"]["value"], 2 / 3)
        self.assertEqual(report["metrics"]["unsupported_query_retrieval_rate_at_5"], {"value": 0.5, "numerator": 1, "denominator": 2})
        self.assertEqual(report["metrics"]["empty_query_rate"]["value"], 2 / 5)
        identity = report["identity"]
        self.assertEqual(identity["cohort_hash"], digest(canonical(self.data).encode()))
        self.assertEqual(identity["query_hash"], digest(canonical(evaluation.project_queries(self.data)).encode()))
        self.assertEqual(identity["results_hash"], run["body"]["results_hash"])
        self.assertEqual(identity["evaluator"]["source_hash"], digest(evaluation.IMPLEMENTATION_SOURCE))
        self.assertEqual(identity["evaluator"]["contract_hash"], digest(canonical(evaluation.CONTRACT).encode()))
        self.assertEqual(identity["corpus_hash"], self.corpus["hash"])
        self.assertNotIn(self.raw_a.decode(), canonical(report))

    def test_macro_recall_is_not_micro_recall(self):
        self.data["cases"] = [
            case("two-sources", "alpha", [span(self.a["id"], 0, len(self.raw_a), self.raw_a),
                                            span(self.b["id"], 0, len(self.raw_b), self.raw_b)]),
            case("one-source", "beta", [span(self.b["id"], 0, len(self.raw_b), self.raw_b)]),
        ]
        report = evaluation.evaluate_retrieval(self.ledger, self.data, self.run_queries()["id"])
        self.assertEqual(report["metrics"]["source_recall_at_k"]["5"]["value"], 0.75)
        self.assertEqual(report["metrics"]["gold_span_recall_at_k"]["5"]["value"], 0.75)
        self.assertIsNone(report["metrics"]["unsupported_query_retrieval_rate_at_5"]["value"])

    def test_run_truncated_below_five_cannot_claim_metrics_at_five(self):
        self.corpus = retrieval.freeze_retrieval_corpus(
            self.ledger, self.snapshot["id"], [self.a["id"], self.b["id"]],
            config={**retrieval.DEFAULT_CONFIG, "top_k": 3})
        run = self.run_queries()
        with self.assertRaisesRegex(ValueError, "top_k of at least 5"):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])

    def test_all_unsupported_has_null_positive_denominator_and_honest_retrieval_rate(self):
        self.data["cases"] = self.data["cases"][3:]
        report = evaluation.evaluate_retrieval(self.ledger, self.data, self.run_queries()["id"])
        for name in ("source_recall_at_k", "gold_span_recall_at_k"):
            for metric in report["metrics"][name].values():
                self.assertIsNone(metric["value"])
                self.assertEqual(metric["numerator"], 0)
                self.assertEqual(metric["denominator"], 0)
        self.assertIsNone(report["metrics"]["source_mrr_at_5"]["value"])
        self.assertIsNone(report["metrics"]["gold_span_mrr_at_5"]["value"])
        self.assertEqual(report["metrics"]["unsupported_query_retrieval_rate_at_5"]["value"], 0.5)

    def test_no_terms_is_explicit_empty_with_positive_still_counted(self):
        self.data["cases"] = [case("empty", "!!!", [span(self.a["id"], 0, 5, self.raw_a)])]
        report = evaluation.evaluate_retrieval(self.ledger, self.data, self.run_queries()["id"])
        self.assertEqual(report["counts"]["empty_reasons"], {"no_query_terms": 1})
        self.assertEqual(report["metrics"]["source_mrr_at_5"], {"value": 0.0, "numerator": 0.0,
                         "denominator": 1, "aggregation": "macro_query_mean"})

    def test_missing_wrong_or_reordered_query_is_not_silently_dropped(self):
        queries = evaluation.project_queries(self.data)
        changed = deepcopy(queries)
        changed[0]["query"] = "different text"
        wrong_id = deepcopy(queries)
        wrong_id[0]["query_id"] = "different-id"
        for inputs in (queries[:-1], list(reversed(queries)), changed, wrong_id):
            with self.subTest(inputs=inputs):
                run = self.run_queries(inputs)
                with self.assertRaisesRegex(ValueError, "every cohort question"):
                    evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])

    def test_gold_must_be_selected_not_just_snapshot_eligible(self):
        run = self.run_queries()
        self.data["cases"][0]["gold_spans"] = [span(self.excluded["id"], 0, 8, b"excluded data")]
        with self.assertRaisesRegex(ValueError, "selected in the retrieval corpus"):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])

    def test_late_source_cannot_be_gold(self):
        run = self.run_queries()
        late = self.ledger.capture("synthetic:late", b"late source")
        self.data["cases"][0]["gold_spans"] = [span(late["id"], 0, 4, b"late source")]
        with self.assertRaisesRegex(ValueError, "selected in the retrieval corpus"):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])

    def test_gold_hash_bounds_and_snapshot_mismatch_are_rejected(self):
        run = self.run_queries()
        original = deepcopy(self.data)
        self.data["cases"][0]["gold_spans"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Span hash mismatch"):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])
        self.data = deepcopy(original)
        self.data["cases"][0]["gold_spans"][0]["end"] = len(self.raw_a) + 1
        with self.assertRaisesRegex(ValueError, "source byte bounds"):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])
        self.data = deepcopy(original)
        self.data["snapshot_id"] = "different-snapshot"
        with self.assertRaisesRegex(ValueError, "snapshot does not match"):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])

    def test_missing_or_noncompleted_execution_does_not_get_metrics(self):
        for terminal_id in ("missing-run", self.corpus["id"]):
            with self.subTest(terminal_id=terminal_id), self.assertRaises(ValueError):
                evaluation.evaluate_retrieval(self.ledger, self.data, terminal_id)
        rejected = self.ledger.append("retrieval_rejected", {"result": "rejected"})
        with self.assertRaises(ValueError):
            evaluation.evaluate_retrieval(self.ledger, self.data, rejected["id"])

    def test_missing_source_bytes_do_not_get_metrics(self):
        run = self.run_queries()
        (self.ledger.root / "blobs" / self.a["body"]["content_hash"]).unlink()
        with self.assertRaises(ValueError):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])


if __name__ == "__main__":
    unittest.main()
