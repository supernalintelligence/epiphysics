"""Owned coverage fixtures only; no real cohort or retrieval-quality experiment."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from epiphysics import retrieval
from epiphysics import retrieval_evaluation as evaluation
from epiphysics.store import Ledger, canonical, digest


def span(oid="a", start=0, end=5, raw=None):
    return {"observation_id": oid, "start": start, "end": end,
            "sha256": digest(raw[start:end]) if raw is not None else "a" * 64}


def bundle(name="one", spans=None):
    return {"bundle_id": name, "spans": [span()] if spans is None else spans}


def case(qid="positive", pair_id="pair", bundles=None, *, answerable=True, query="alpha"):
    return {"question_id": qid, "pair_id": pair_id, "query": query,
            "answerability": "answerable" if answerable else "unanswerable",
            "support_bundles": ([bundle()] if bundles is None else bundles) if answerable else [],
            "rationale": "Owned fixture judgment relative to selected sources.",
            "family_tags": ["software_service"], "relation_tags": ["boundary"],
            "novelty": {"related_prior_question_ids": [], "distinction": "Owned new obligation."}}


def pair(pid="pair", positive="positive", negative="negative", anchors=None):
    return {"pair_id": pid, "supported_question_id": positive, "unsupported_question_id": negative,
            "anchor_observation_ids": ["a"] if anchors is None else anchors,
            "changed_requirement": "Change the requested qualifier.",
            "matching_rationale": "Same owned topic and specificity."}


def cohort(positive=None, *, snapshot_id="snapshot"):
    return {"schema_version": 2, "snapshot_id": snapshot_id, "cohort": "development",
            "cohort_id": "owned-coverage", "source_scope": "selected_corpus_only",
            "support_semantics": "any_complete_bundle_v1",
            "cases": [case() if positive is None else positive,
                      case("negative", answerable=False, query="missingzz")],
            "pairs": [pair()], "limitations": ["Owned synthetic cases only."]}


def result(hits, *, qid="positive", query="alpha", reason="no_lexical_match"):
    return {"query_id": qid, "query": query, "status": "matched" if hits else "empty",
            "reason": None if hits else reason,
            "hits": [{**row, "rank": rank, "score": -1.0} for rank, row in enumerate(hits, 1)]}


class CoverageShapeTests(unittest.TestCase):
    def test_projection_is_only_ids_and_text_and_hashes_keep_labels_separate(self):
        data = cohort()
        projected = evaluation.project_queries(data)
        self.assertEqual(projected, [{"query_id": "positive", "query": "alpha"},
                                     {"query_id": "negative", "query": "missingzz"}])
        identity = evaluation.cohort_identity(data)
        gold = [{"question_id": c["question_id"], "answerability": c["answerability"],
                 "support_bundles": c["support_bundles"]} for c in data["cases"]]
        self.assertEqual(identity, {"cohort_hash": digest(canonical(data).encode()),
                                  "gold_hash": digest(canonical(gold).encode()),
                                  "query_hash": digest(canonical(projected).encode())})
        changed = deepcopy(data)
        changed["cases"][0]["rationale"] = "Changed annotation-only rationale."
        self.assertEqual(evaluation.cohort_identity(changed)["query_hash"], identity["query_hash"])
        self.assertEqual(evaluation.cohort_identity(changed)["gold_hash"], identity["gold_hash"])
        self.assertNotEqual(evaluation.cohort_identity(changed)["cohort_hash"], identity["cohort_hash"])
        projected[0]["query"] = "changed"
        self.assertEqual(data["cases"][0]["query"], "alpha")

    def test_duplicate_bundle_ids_and_renamed_reordered_span_sets_refuse(self):
        first = bundle("first", [span("a"), span("b")])
        for second in (bundle("first", [span("c")]), bundle("renamed", list(reversed(first["spans"])))):
            with self.subTest(second=second), self.assertRaisesRegex(ValueError, "Duplicate"):
                evaluation.project_queries(cohort(case(bundles=[first, second])))

    def test_shared_span_between_distinct_alternatives_is_valid(self):
        data = cohort(case(bundles=[bundle("left", [span("a"), span("b")]),
                                    bundle("right", [span("a"), span("c")])]))
        self.assertEqual(evaluation._cohort(data), data)

    def test_bundle_and_span_bounds_and_empty_conjunction_refuse(self):
        values = [[], [bundle(spans=[])], [bundle(spans=[span(), span()])],
                  [bundle(str(i), [span("a", i, i + 1)]) for i in range(5)],
                  [bundle(spans=[span("a", i, i + 1) for i in range(9)])]]
        for bundles in values:
            with self.subTest(bundles=bundles), self.assertRaises(ValueError):
                evaluation._cohort(cohort(case(bundles=bundles)))

    def test_exact_fields_labels_tags_identifiers_and_metadata_bounds(self):
        mutations = [lambda d: d.update(schema_version=True), lambda d: d.update(schema_version=3),
                     lambda d: d.update(cohort="holdout"), lambda d: d.update(source_scope="all_sources"),
                     lambda d: d.update(support_semantics="any_span"), lambda d: d.update(extra=True),
                     lambda d: d["cases"][0].update(question_id="x" * 513),
                     lambda d: d["cases"][0].update(query="é" * 1025),
                     lambda d: d["cases"][0].update(query="\ud800"),
                     lambda d: d["cases"][0].update(rationale="x" * 8193),
                     lambda d: d["cases"][0].update(family_tags=["invented"]),
                     lambda d: d["cases"][0].update(family_tags=["organization"] * 2),
                     lambda d: d["cases"][0].update(relation_tags=list(evaluation.RELATION_LABELS[:4])),
                     lambda d: d["cases"][0].update(answerability="unknown"),
                     lambda d: d["cases"][1].update(support_bundles=[bundle()]),
                     lambda d: d["cases"][0]["novelty"].update(related_prior_question_ids=[str(i) for i in range(65)]),
                     lambda d: d.update(limitations=["x"] * 65)]
        for index, mutate in enumerate(mutations):
            data = cohort(); mutate(data)
            with self.subTest(index=index), self.assertRaises(ValueError):
                evaluation.project_queries(data)

    def test_span_types_hashes_and_half_open_nonempty_offsets(self):
        for field, value in (("start", True), ("start", -1), ("end", 0),
                             ("end", 1_000_001), ("sha256", "A" * 64)):
            data = cohort(); data["cases"][0]["support_bundles"][0]["spans"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                evaluation._cohort(data)

    def test_pair_bijection_labels_agreement_and_anchor_bounds(self):
        mutations = [lambda d: d.update(pairs=[]), lambda d: d["cases"][1].update(pair_id="other"),
                     lambda d: d["pairs"][0].update(supported_question_id="negative"),
                     lambda d: d["pairs"][0].update(unsupported_question_id="missing"),
                     lambda d: d["pairs"][0].update(anchor_observation_ids=[]),
                     lambda d: d["pairs"][0].update(anchor_observation_ids=["a", "a"])]
        for index, mutate in enumerate(mutations):
            data = cohort(); mutate(data)
            with self.subTest(index=index), self.assertRaises(ValueError):
                evaluation._cohort(data)
        data = cohort()
        data["cases"] += [case("p2", "pair2"), case("n2", "pair2", answerable=False)]
        data["pairs"].append(pair("pair2", "positive", "n2"))
        with self.assertRaises(ValueError):
            evaluation._cohort(data)

    def test_full_generic_case_limit_and_canonical_byte_limit(self):
        data = cohort(); data["cases"] = []; data["pairs"] = []
        for index in range(32):
            pid, positive, negative = f"pair{index}", f"p{index}", f"n{index}"
            data["cases"] += [case(positive, pid), case(negative, pid, answerable=False)]
            data["pairs"].append(pair(pid, positive, negative))
        self.assertEqual(len(evaluation.project_queries(data)), 64)
        oversized = deepcopy(data); oversized["cases"].append(case("extra"))
        with self.assertRaises(ValueError):
            evaluation._cohort(oversized)
        for c in data["cases"]:
            c["rationale"] = "r" * 8192
            c["novelty"]["distinction"] = "d" * 8192
        with self.assertRaisesRegex(ValueError, "canonical byte bound"):
            evaluation._cohort(data)

    def test_inventory_counts_annotations_only_and_every_group_slot(self):
        data = cohort(case(bundles=[bundle("one", [span("a"), span("b")]), bundle("two", [span("a", 5, 10)])]))
        inventory = evaluation.coverage_inventory(data, ["a", "b", "unused"])
        self.assertEqual(inventory["counts"], {"queries": 2, "answerable": 1, "unanswerable": 1,
                                             "pairs": 1, "selected_sources": 3})
        self.assertEqual(inventory["feature_inventory"], {"alternative_support_cases": 1,
                                                        "joint_support_cases": 1, "multisource_support_cases": 1})
        self.assertEqual(set(inventory["families"]), set(evaluation.FAMILY_LABELS))
        self.assertEqual(set(inventory["relations"]), set(evaluation.RELATION_LABELS))
        self.assertEqual(inventory["families"]["physical_asset"],
                         {"queries": 0, "answerable": 0, "unanswerable": 0, "status": "unmeasured"})
        self.assertNotIn('"value"', canonical(inventory))
        with self.assertRaisesRegex(ValueError, "selected"):
            evaluation.coverage_inventory(data, ["b"])


class CompleteBundleScoringTests(unittest.TestCase):
    def test_either_sufficient_alternative_passes_without_rewarding_annotation_count(self):
        data = case(bundles=[bundle("many", [span("a"), span("b")]), bundle("single", [span("c")])])
        scored = evaluation._score_coverage_case(data, result([span("c")]))
        self.assertTrue(scored["complete_support_at_k"]["1"])
        self.assertEqual(scored["complete_support_reciprocal_rank_at_5"], 1.0)
        self.assertFalse(scored["bundles"][0]["complete_at_k"]["5"])
        self.assertTrue(scored["bundles"][1]["complete_at_k"]["1"])
        other = evaluation._score_coverage_case(data, result([span("a"), span("b")]))
        self.assertEqual(other["complete_support_first_covered_prefix_at_5"], 2)
        self.assertEqual(other["complete_support_reciprocal_rank_at_5"], 0.5)

    def test_joint_spans_require_every_span_and_cannot_mix_partial_alternatives(self):
        data = case(bundles=[bundle("left", [span("a"), span("b")]),
                             bundle("right", [span("c"), span("d")])])
        for hits in ([span("a")], [span("a"), span("d")]):
            scored = evaluation._score_coverage_case(data, result(hits))
            self.assertFalse(scored["complete_support_at_k"]["5"])
            self.assertEqual(scored["complete_support_reciprocal_rank_at_5"], 0.0)

    def test_union_coverage_uses_earliest_complete_prefix_and_respects_gaps(self):
        data = case(bundles=[bundle(spans=[span("a", 0, 10)])])
        for hits, expected in (([span("a", 0, 5), span("a", 5, 10)], True),
                               ([span("a", 0, 6), span("a", 4, 10)], True),
                               ([span("a", 0, 5), span("a", 6, 10)], False),
                               ([span("a", 0, 6), span("a", 0, 6)], False),
                               ([span("a", 0, 5), span("b", 5, 10)], False)):
            with self.subTest(hits=hits):
                scored = evaluation._score_coverage_case(data, result(hits))
                self.assertFalse(scored["complete_support_at_k"]["1"])
                self.assertEqual(scored["complete_support_at_k"]["3"], expected)
                self.assertEqual(scored["complete_support_first_covered_prefix_at_5"], 2 if expected else None)

    def test_coarse_source_set_diagnostic_does_not_imply_support(self):
        data = case(bundles=[bundle(spans=[span("a"), span("b")])])
        scored = evaluation._score_coverage_case(data, result([span("a", 20, 30), span("b", 20, 30)]))
        self.assertTrue(scored["complete_source_set_at_k"]["3"])
        self.assertFalse(scored["complete_support_at_k"]["3"])

    def test_unsupported_is_not_vacuous_success_and_sixth_hit_is_ignored(self):
        unsupported = evaluation._score_coverage_case(case(answerable=False), result([]))
        self.assertIsNone(unsupported["complete_support_at_k"]["5"])
        self.assertIsNone(unsupported["complete_support_reciprocal_rank_at_5"])
        self.assertFalse(unsupported["unsupported_retrieval_at_5"])
        scored = evaluation._score_coverage_case(case(), result([span("other")] * 5 + [span()]))
        self.assertFalse(scored["complete_support_at_k"]["5"])
        self.assertEqual(len(scored["raw_windows"]), 5)

    def test_query_macro_empty_outputs_group_nulls_and_pair_buckets(self):
        data = cohort(case(bundles=[bundle(spans=[span("a", i, i + 1) for i in range(8)])]))
        data["cases"] += [case("p2", "pair2", [bundle(spans=[span("b")])]),
                          case("n2", "pair2", answerable=False)]
        data["pairs"].append(pair("pair2", "p2", "n2", ["b"]))
        data["cases"][3]["family_tags"] = ["organization"]
        scored = evaluation._score_coverage(data, [result([]), result([span("a")]),
                                                  result([span("b")]), result([])], ["a", "b"])
        self.assertEqual(scored["metrics"]["complete_support_rate_at_k"]["5"],
                         {"numerator": 1, "denominator": 2, "value": 0.5, "aggregation": "macro_query_mean"})
        self.assertEqual(scored["metrics"]["complete_support_mrr_at_5"]["value"], 0.5)
        self.assertEqual(scored["metrics"]["unsupported_query_retrieval_rate_at_5"]["value"], 0.5)
        self.assertEqual(scored["metrics"]["empty_query_rate"]["value"], 0.5)
        for name in ("physical_asset", "organization"):
            metric = scored["families"][name]["complete_support_rate_at_k"]["5"]
            self.assertIsNone(metric["value"])
            self.assertEqual(metric["denominator"], 0)
        self.assertEqual(scored["pair_buckets"], {"cutoff": 5, "supported_yes_unsupported_yes": 0,
                         "supported_yes_unsupported_no": 1, "supported_no_unsupported_yes": 1,
                         "supported_no_unsupported_no": 0})
        self.assertEqual(len(scored["matched_pairs"]), 2)


class CoverageReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.temp.name) / "owned", clock=lambda: "2020-01-01T00:00:00Z")
        self.raw = "alpha café policy does not promise immortality.".encode()
        self.a = self.ledger.capture("synthetic:a", self.raw, event_id="a")
        self.b = self.ledger.capture("synthetic:b", b"beta second supporting fact.", event_id="b")
        self.excluded = self.ledger.capture("synthetic:unselected", b"excluded", event_id="excluded")
        self.snapshot = self.ledger.snapshot(event_id="snapshot")
        self.corpus = retrieval.freeze_retrieval_corpus(self.ledger, self.snapshot["id"], ["a", "b"], event_id="corpus")
        self.data = cohort(case(bundles=[bundle(spans=[span("a", 0, len(self.raw), self.raw)])]))
        self.counter = 0

    def tearDown(self):
        self.ledger.close(); self.temp.cleanup()

    def run_queries(self, queries=None):
        self.counter += 1
        return retrieval.run_lexical_retrieval(self.ledger, self.corpus["id"],
            evaluation.project_queries(self.data) if queries is None else queries, run_key=f"owned-coverage-{self.counter}")

    def test_preparation_source_validation_needs_no_run_and_writes_nothing(self):
        before = self.ledger.events()
        self.assertEqual(evaluation.validate_coverage_sources(self.ledger, self.data, self.corpus), self.data)
        self.assertEqual(self.ledger.events(), before)
        self.assertEqual(self.ledger.events("retrieval_started"), [])

    def test_actual_owned_receipt_reports_v2_and_readonly_scoring_reproduces(self):
        run = self.run_queries()
        before = self.ledger.events()
        report = evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])
        self.assertEqual(report["evaluation"], "retrieval-coverage-evaluation-v2")
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["metrics"]["complete_support_rate_at_k"]["1"]["value"], 1.0)
        self.assertNotIn("gold_span_recall_at_k", report["metrics"])
        self.assertEqual(report["identity"]["evaluator"], evaluation.evaluator_identity(2))
        self.assertEqual(report["identity"]["candidate"], evaluation._candidate_identity(run["body"]))
        self.assertEqual(report["pair_buckets"]["supported_yes_unsupported_no"], 1)
        self.assertEqual(self.ledger.events(), before)
        readonly = Ledger.open_readonly(self.ledger.root)
        try:
            self.assertEqual(evaluation.evaluate_retrieval(readonly, self.data, run["id"]), report)
        finally:
            readonly.close()
        repeat = self.run_queries()
        reproduced = evaluation.evaluate_retrieval(self.ledger, self.data, repeat["id"])
        for key in ("metrics", "per_case", "matched_pairs", "pair_buckets", "families", "relations"):
            self.assertEqual(report[key], reproduced[key])

    def test_explicit_refutation_remains_answerable(self):
        self.data["cases"][0]["query"] = "Does the alpha policy promise immortality?"
        report = evaluation.evaluate_retrieval(self.ledger, self.data, self.run_queries()["id"])
        self.assertEqual(report["counts"]["answerable"], 1)
        self.assertEqual(report["metrics"]["complete_support_rate_at_k"]["5"]["value"], 1.0)

    def test_missing_query_reordered_or_wrong_query_receipts_refuse(self):
        queries = evaluation.project_queries(self.data)
        wrong = deepcopy(queries); wrong[0]["query"] = "different"
        for value in (queries[:-1], list(reversed(queries)), wrong):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "every cohort question"):
                evaluation.evaluate_retrieval(self.ledger, self.data, self.run_queries(value)["id"])

    def test_valid_empty_queries_are_counted_as_misses_with_reasons(self):
        self.data["cases"][0]["query"] = "!!!"
        report = evaluation.evaluate_retrieval(self.ledger, self.data, self.run_queries()["id"])
        self.assertEqual(report["metrics"]["complete_support_rate_at_k"]["5"]["value"], 0.0)
        self.assertEqual(report["metrics"]["empty_query_rate"]["value"], 1.0)
        self.assertEqual(report["counts"]["empty_reasons"], {"no_query_terms": 1, "no_lexical_match": 1})

    def test_gold_and_anchors_must_be_selected_not_merely_snapshot_eligible(self):
        for field in ("gold", "anchor"):
            data = deepcopy(self.data)
            if field == "gold":
                data["cases"][0]["support_bundles"][0]["spans"] = [span("excluded", 0, 8, b"excluded")]
            else:
                data["pairs"][0]["anchor_observation_ids"] = ["excluded"]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "selected"):
                evaluation.validate_coverage_sources(self.ledger, data, self.corpus)

    def test_gold_hash_bounds_and_utf8_boundaries_refuse(self):
        wrong = deepcopy(self.data); wrong["cases"][0]["support_bundles"][0]["spans"][0]["sha256"] = "0" * 64
        beyond = deepcopy(self.data); beyond["cases"][0]["support_bundles"][0]["spans"][0]["end"] = len(self.raw) + 1
        cut = deepcopy(self.data)
        offset = self.raw.index("é".encode())
        cut["cases"][0]["support_bundles"][0]["spans"] = [span("a", offset + 1, offset + 2, self.raw)]
        for data, message in ((wrong, "hash mismatch"), (beyond, "byte bounds"), (cut, "UTF-8 boundaries")):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                evaluation.validate_coverage_sources(self.ledger, data, self.corpus)

    def test_missing_run_blob_or_top_five_budget_refuse(self):
        with self.assertRaises(ValueError):
            evaluation.evaluate_retrieval(self.ledger, self.data, "absent")
        self.corpus = retrieval.freeze_retrieval_corpus(self.ledger, "snapshot", ["a", "b"],
            config={**retrieval.DEFAULT_CONFIG, "top_k": 3}, event_id="short-corpus")
        run = self.run_queries()
        with self.assertRaisesRegex(ValueError, "top_k of at least 5"):
            evaluation.evaluate_retrieval(self.ledger, self.data, run["id"])
        (self.ledger.root / "blobs" / self.a["body"]["content_hash"]).unlink()
        with self.assertRaises(ValueError):
            evaluation.validate_coverage_sources(self.ledger, self.data, self.corpus)


class CoverageIdentityTests(unittest.TestCase):
    def test_selected_contract_identity_and_legacy_default(self):
        legacy, coverage = evaluation.evaluator_identity(), evaluation.evaluator_identity(2)
        self.assertEqual(legacy, evaluation._implementation_identity(1))
        self.assertEqual(legacy["contract"], evaluation.CONTRACT)
        self.assertEqual(coverage["contract"], evaluation.COVERAGE_CONTRACT)
        self.assertNotEqual(legacy["contract_hash"], coverage["contract_hash"])
        for field in ("source_hash", "dependencies", "runtime"):
            self.assertEqual(legacy[field], coverage[field])
        for value in (True, 0, 3, "2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluation.evaluator_identity(value)

    def test_selected_v2_measurement_never_imports_candidate_or_preparation_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(Path(evaluation.__file__).parent, root / "epiphysics", ignore=shutil.ignore_patterns("__pycache__"))
            program = '''
import json,sys
from pathlib import Path
from epiphysics import retrieval_evaluation as evaluation
before=evaluation.evaluator_identity(2)
for name in ('retrieval','retrieval_indexing','retrieval_coverage','retrieval_assessment'):
    assert 'epiphysics.'+name not in sys.modules
    path=Path('epiphysics')/(name+'.py')
    if path.exists(): path.write_bytes(path.read_bytes()+b'\\n# Outside the scoring closure.\\n')
assert evaluation.evaluator_identity(2)==before
print(json.dumps({'contract':before['contract']['id'],'dependencies':list(before['dependencies'])}))
'''
            completed = subprocess.run([sys.executable, "-s", "-c", program], cwd=root,
                env={**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            outcome = json.loads(completed.stdout)
            self.assertEqual(outcome["contract"], "retrieval-coverage-evaluation-v2")
            self.assertNotIn("epiphysics.retrieval_indexing", outcome["dependencies"])


if __name__ == "__main__":
    unittest.main()
