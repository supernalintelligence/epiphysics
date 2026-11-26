"""Owned fixtures for actual receipt assessment, not retrieval-quality claims."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import retrieval, retrieval_evaluation as evaluation
from epiphysics import retrieval_assessment as assessment
from epiphysics.store import Ledger, canonical, digest


def declared(report, second, study_id="owned-study"):
    identity = report["identity"]
    return {"schema_version": 1, "study_id": study_id,
        **{key: identity[key] for key in ("snapshot_id", "snapshot_hash", "snapshot_manifest_hash",
            "corpus_id", "corpus_hash", "cohort_hash", "gold_hash", "query_hash", "sources_hash", "passages_hash", "config_hash")},
        "implementation_hash": identity["retriever_implementation_hash"],
        "dependency_hashes": {name: ref["content_hash"] for name, ref in identity["retriever_artifacts"]["dependencies"].items()},
        "runtime_hash": identity["retriever_runtime_hash"],
        "run_terminal_hashes": {identity["run_terminal_id"]: identity["run_terminal_hash"], second["id"]: second["hash"]}}


class RetrievalAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ledger = Ledger(self.root / "evidence")
        self.addCleanup(self.ledger.close)
        self.source = b"alpha history: the document existed before a time boundary."
        self.ledger.capture("owned:source", self.source, event_id="source-a")
        self.ledger.capture("owned:other", b"beta details", event_id="source-b")
        snapshot = self.ledger.snapshot(event_id="snapshot")
        self.corpus = retrieval.freeze_retrieval_corpus(self.ledger, snapshot["id"], ["source-a", "source-b"], event_id="corpus")
        self.cohort = {"schema_version": 1, "snapshot_id": "snapshot", "cohort": "development", "cases": [
            {"question_id": "positive", "query": "alpha history", "answerability": "answerable",
             "gold_spans": [{"observation_id": "source-a", "start": 0, "end": 5, "sha256": digest(self.source[:5])}]},
            {"question_id": "unsupported", "query": "alpha median wait", "answerability": "unanswerable", "gold_spans": []}]}
        queries = evaluation.project_queries(self.cohort)
        self.a = retrieval.run_lexical_retrieval(self.ledger, "corpus", queries, run_key="owned-a")
        self.b = retrieval.run_lexical_retrieval(self.ledger, "corpus", queries, run_key="owned-b")
        self.expected = evaluation.evaluate_retrieval(self.ledger, self.cohort, self.a["id"])
        self.contract = declared(self.expected, self.b)
        self.cohort_path = self.root / "cohort.json"
        self.cohort_path.write_text(json.dumps(self.cohort, indent=2))
        self.request = {"schema_version": 1, "study_id": "owned-study", "evidence_store": str(self.ledger.root),
            "cohort_file": str(self.cohort_path), "corpus_id": "corpus", "run_terminal_ids": [self.a["id"], self.b["id"]]}
        self.request_path = self.root / "study.json"
        self.request_path.write_text(json.dumps(self.request, indent=2))

    def prepare(self):
        return assessment.prepare_retrieval_study(self.request_path, declared_contract=self.contract)

    def assess(self, request=None, cohort=None, contract=None):
        return assessment.assess_retrieval_study(self.ledger, request or self.request, cohort or self.cohort,
            declared_contract=contract or self.contract)

    def test_valid_pair_scores_actual_data_and_preserves_foreign_store(self):
        before_events = self.ledger.events()
        before_blobs = {p.name: p.read_bytes() for p in (self.ledger.root / "blobs").iterdir()}
        value = self.assess()
        report = value["report"]
        self.assertEqual(report["reproducibility"]["value"], 1)
        self.assertEqual(report["quality"]["runs"][0], self.expected)
        self.assertEqual(report["quality"]["runs"][1]["metrics"], self.expected["metrics"])
        self.assertEqual(report["quality"]["runs"][0]["metrics"]["unsupported_query_retrieval_rate_at_5"]["numerator"], 1)
        self.assertNotEqual(report["quality"]["runs"][0]["identity"]["retriever_artifacts"], report["quality"]["runs"][1]["identity"]["retriever_artifacts"])
        self.assertEqual(self.ledger.events(), before_events)
        self.assertEqual({p.name: p.read_bytes() for p in (self.ledger.root / "blobs").iterdir()}, before_blobs)
        self.assertIn("assessment_report", value["artifacts"])

    def test_retained_bytes_reproduce_without_original_paths(self):
        prepared = self.prepare()
        self.assertEqual(prepared["artifacts"]["request"], self.request_path.read_bytes())
        self.assertEqual(prepared["artifacts"]["cohort"], self.cohort_path.read_bytes())
        first = assessment.assess_prepared_retrieval_study(prepared)
        self.ledger.close()
        shutil.rmtree(self.ledger.root)
        self.request_path.unlink()
        self.cohort_path.unlink()
        self.assertEqual(assessment.assess_prepared_retrieval_study(prepared), first)

    def test_mutation_after_capture_does_not_mix_versions(self):
        prepared = self.prepare()
        source_path = self.ledger.root / "blobs" / digest(self.source)
        source_path.write_bytes(b"mutated after coherent capture")
        self.assertEqual(assessment.assess_prepared_retrieval_study(prepared)["report"]["reproducibility"]["value"], 1)
        with self.assertRaisesRegex(ValueError, "hash or size"):
            self.assess()

    def test_distinct_terminal_and_claim_required(self):
        request = deepcopy(self.request)
        request["run_terminal_ids"] = [self.a["id"], self.a["id"]]
        # A replay is still exactly the same terminal, not an independent run.
        self.assertEqual(retrieval.run_lexical_retrieval(self.ledger, "corpus", evaluation.project_queries(self.cohort), run_key="owned-a"), self.a)
        with self.assertRaisesRegex(ValueError, "distinct terminal"):
            self.assess(request=request)

    def test_coherent_different_results_measure_zero_not_rejection(self):
        # Model a second valid historical receipt with different returned hits.
        # Rehash its terminal and declare that true hash; nothing is hidden by a
        # stale expected hash. Both public receipt validators must accept it.
        changed = deepcopy(self.b)
        body = changed["body"]
        body["results"][0].update(hits=[], status="empty", reason="no_lexical_match")
        body["results_hash"] = digest(canonical(body["results"]).encode())
        body["resources"]["output_bytes"] = len(canonical(body["results"]).encode())
        changed["hash"] = digest(canonical({k: changed[k] for k in ("id", "kind", "recorded_at", "body", "previous_hash")}).encode())
        self.ledger.db.execute("DROP TRIGGER events_no_update")
        self.ledger.db.execute("UPDATE events SET body=?,hash=? WHERE id=?", (canonical(body), changed["hash"], changed["id"]))
        self.ledger.db.commit()
        self.assertEqual(retrieval.get_retrieval_run(self.ledger, changed["id"]), changed)
        other_report = evaluation.evaluate_retrieval(self.ledger, self.cohort, changed["id"])
        contract = declared(self.expected, changed)
        report = self.assess(contract=contract)["report"]
        self.assertEqual(report["reproducibility"]["value"], 0)
        self.assertFalse(report["reproducibility"]["ordered_results_equal"])
        self.assertFalse(report["reproducibility"]["evaluations_equal"])
        self.assertEqual(report["quality"]["runs"][1], other_report)

    def test_full_query_order_and_gold_identity_are_checked(self):
        reordered = deepcopy(self.cohort)
        reordered["cases"].reverse()
        with self.assertRaisesRegex(ValueError, "every cohort question"):
            self.assess(cohort=reordered)
        changed_gold = deepcopy(self.cohort)
        changed_gold["cases"][0]["gold_spans"][0].update(end=4, sha256=digest(self.source[:4]))
        with self.assertRaisesRegex(ValueError, "declared cohort_hash"):
            self.assess(cohort=changed_gold)

    def test_declared_source_candidate_runtime_and_terminal_bindings(self):
        for key in ("snapshot_hash", "corpus_hash", "sources_hash", "passages_hash", "config_hash", "implementation_hash", "runtime_hash"):
            contract = deepcopy(self.contract)
            contract[key] = "0" * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.assess(contract=contract)
        for key in ("dependency_hashes", "run_terminal_hashes"):
            contract = deepcopy(self.contract)
            contract[key][next(iter(contract[key]))] = "0" * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.assess(contract=contract)

    def test_captured_blob_tamper_and_external_summary_refused(self):
        prepared = self.prepare()
        role = "blob:" + digest(self.source)
        prepared["artifacts"][role] = b"changed"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            assessment.check_prepared_retrieval_study(prepared)
        prepared["manifest"][role] = digest(b"changed")
        with self.assertRaisesRegex(ValueError, "blob size or hash"):
            assessment.assess_prepared_retrieval_study(prepared)
        prepared = self.prepare()
        prepared["artifacts"]["supplied_summary"] = b'{"accuracy":1}'
        prepared["manifest"]["supplied_summary"] = digest(prepared["artifacts"]["supplied_summary"])
        with self.assertRaisesRegex(ValueError, "Unexpected or missing"):
            assessment.assess_prepared_retrieval_study(prepared)

    def test_future_ledger_growth_does_not_expand_frozen_prefix(self):
        first = self.prepare()
        for index in range(260):
            self.ledger.append("unrelated_later", {"index": index})
        self.assertEqual(self.prepare(), first)

    def test_prefix_and_aggregate_bounds_refuse(self):
        for key, value in (("MAX_PREFIX_EVENTS", 1), ("MAX_PREFIX_BYTES", 100), ("MAX_BUNDLE_BYTES", 100)):
            with self.subTest(key=key), patch.object(assessment, key, value), self.assertRaisesRegex(ValueError, "bound"):
                self.prepare()

    def test_malformed_oversized_chain_hash_refuses_before_deserialization(self):
        self.ledger.db.execute("DROP TRIGGER events_no_update")
        self.ledger.db.execute("UPDATE events SET previous_hash=? WHERE id=?", ("x" * (assessment.MAX_PREFIX_BYTES + 1), "source-a"))
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError, "prefix exceeds capture bound"):
            self.prepare()

    def test_selected_source_aggregate_refuses_at_capture(self):
        # Every source independently fits; only their sum exceeds this test cap.
        with patch.object(retrieval, "MAX_TOTAL_BYTES", len(self.source)), self.assertRaisesRegex(ValueError, "Selected source bytes"):
            self.prepare()

    def test_oversized_adapter_source_refuses_without_reading_file(self):
        oversized = self.root / "changed-adapter.py"
        oversized.write_bytes(b"x" * (len(assessment.IMPLEMENTATION_SOURCE) + 1))
        with patch.object(assessment, "_SELF", (oversized, assessment.IMPLEMENTATION_SOURCE, assessment.IMPLEMENTATION_CODE)):
            with patch.object(Path, "open", side_effect=AssertionError("Oversized source must not be opened")):
                with self.assertRaisesRegex(ValueError, "implementation changed"):
                    assessment._current_sources()

    def test_prepare_refuses_oversized_evaluator_source_before_reading_it(self):
        oversized = self.root / "changed-evaluator.py"
        with oversized.open("wb") as stream:
            stream.truncate(32_000_000)
        original_open, original_read = Path.open, Path.read_bytes
        def guarded_open(path, *args, **kwargs):
            if path == oversized:
                raise AssertionError("Oversized evaluator source must not be opened")
            return original_open(path, *args, **kwargs)
        def guarded_read(path):
            if path == oversized:
                raise AssertionError("Oversized evaluator source must not be read")
            return original_read(path)
        with patch.object(evaluation, "_PINNED_SELF", (oversized, evaluation.IMPLEMENTATION_SOURCE, evaluation.IMPLEMENTATION_CODE)):
            with patch.object(Path, "open", guarded_open), patch.object(Path, "read_bytes", guarded_read):
                with self.assertRaisesRegex(ValueError, "Evaluator source changed"):
                    self.prepare()

    def test_evaluator_source_identity_reads_only_expected_length_plus_one(self):
        source_path, source, _ = evaluation._PINNED_SELF
        original_open = Path.open
        reads = []
        class LimitedReader:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def read(self, size=-1):
                reads.append(size)
                if size != len(source) + 1:
                    raise AssertionError("Evaluator source read must be bounded by retained size")
                return self.stream.read(size)
        def guarded_open(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return LimitedReader(stream) if path == source_path else stream
        with patch.object(Path, "open", guarded_open):
            prepared = self.prepare()
        self.assertTrue(prepared["artifacts"])
        self.assertTrue(reads)
        self.assertEqual({len(source) + 1}, set(reads))

    def test_same_store_symlink_and_hardlink_aliases_refused(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            assessment.prepare_retrieval_study(self.request_path, declared_contract=self.contract, forbidden_store=self.ledger.root)
        alias = self.root / "alias"
        alias.symlink_to(self.ledger.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "distinct"):
            assessment.prepare_retrieval_study(self.request_path, declared_contract=self.contract, forbidden_store=alias)
        alias.unlink()
        alias.mkdir()
        os.link(self.ledger.root / "ledger.sqlite", alias / "ledger.sqlite")
        with self.assertRaisesRegex(ValueError, "distinct"):
            assessment.prepare_retrieval_study(self.request_path, declared_contract=self.contract, forbidden_store=alias)

    def test_duplicate_json_and_unknown_contract_fields_refused(self):
        self.request_path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, "JSON"):
            self.prepare()
        contract = deepcopy(self.contract)
        contract["expected_accuracy"] = 1
        with self.assertRaisesRegex(ValueError, "contract"):
            self.assess(contract=contract)

    def test_readonly_evidence_connection_is_supported(self):
        with_readonly = Ledger.open_readonly(self.ledger.root)
        try:
            actual = assessment.assess_retrieval_study(with_readonly, self.request, self.cohort, declared_contract=self.contract)
            self.assertEqual(actual["report"]["reproducibility"]["value"], 1)
            self.assertEqual(with_readonly.db.execute("PRAGMA query_only").fetchone()[0], 1)
        finally:
            with_readonly.close()


if __name__ == "__main__":
    unittest.main()
