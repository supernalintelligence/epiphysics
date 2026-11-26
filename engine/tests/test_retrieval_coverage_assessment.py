"""Captured preparation/evaluation integration on owned source bytes."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from epiphysics import retrieval_assessment as assessment, retrieval_coverage as coverage, retrieval_contracts
from epiphysics.store import Ledger, canonical, digest
from test_retrieval_coverage_preparation import make_fixture, execute_pair, study_files


def diverge_repeat(ledger, run):
    changed = deepcopy(run)
    body = changed["body"]
    body["results"][0].update(hits=[], status="empty", reason="no_lexical_match")
    body["results_hash"] = digest(canonical(body["results"]).encode())
    body["resources"]["output_bytes"] = len(canonical(body["results"]).encode())
    changed["hash"] = digest(canonical({key: changed[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}).encode())
    ledger.db.execute("DROP TRIGGER events_no_update")
    ledger.db.execute("UPDATE events SET body=?,hash=? WHERE id=?", (canonical(body), changed["hash"], changed["id"]))
    ledger.db.commit()
    return changed


class CoverageAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = Ledger(self.root / "evidence")
        self.addCleanup(self.ledger.close)
        self.data = make_fixture(self.root, self.ledger)

    def prepare(self, phase="preparation", runs=()):
        path, _, declaration = study_files(self.data, self.ledger, phase, runs)
        return assessment.prepare_retrieval_study(path, declared_contract=declaration)

    def test_preparation_has_no_future_outputs_or_quality_and_captures_full_freeze(self):
        before = self.ledger.events()
        prepared = self.prepare()
        value = assessment.assess_prepared_retrieval_study(prepared)
        report = value["report"]
        self.assertEqual("ready", report["status"])
        self.assertEqual("preparation", report["phase"])
        for name in ("quality", "reproducibility", "metrics", "costs", "runs"):
            self.assertNotIn(name, report)
        self.assertEqual(6, report["preparation"]["counts"]["pairs"])
        self.assertEqual(self.data["freeze"]["hash"], report["input_bindings"]["prefix_head"]["hash"])
        for role in ("cohort", "protocol", "review"):
            ref = self.data["freeze"]["body"]["artifacts"][role]
            self.assertEqual(self.data[role + "_raw"], prepared["artifacts"]["blob:" + ref["content_hash"]])
        self.assertEqual(before, self.ledger.events())

    def test_preparation_replays_after_original_files_and_store_disappear(self):
        prepared = self.prepare()
        expected = assessment.assess_prepared_retrieval_study(prepared)
        self.ledger.close()
        shutil.rmtree(self.ledger.root)
        for file in self.root.glob("*.json"):
            file.unlink()
        self.assertEqual(expected, assessment.assess_prepared_retrieval_study(prepared))

    def test_two_real_repeats_keep_preparation_measurement_identity(self):
        prepared = self.prepare()
        first = assessment.assess_prepared_retrieval_study(prepared)["report"]
        runs = execute_pair(self.data, self.ledger)
        before = self.ledger.events()
        evaluated = assessment.assess_prepared_retrieval_study(self.prepare("evaluation", runs))["report"]
        self.assertEqual(1, evaluated["reproducibility"]["value"])
        self.assertEqual(first["measurement_contract_identity"], evaluated["measurement_contract_identity"])
        self.assertNotEqual(first["assessment_identity"], evaluated["assessment_identity"])
        self.assertEqual(1, evaluated["quality"]["runs"][0]["metrics"]["complete_support_rate_at_k"]["5"]["value"])
        self.assertEqual(6, sum(v for key, v in evaluated["coverage"]["pair_buckets"].items() if key != "cutoff"))
        self.assertEqual("none", evaluated["coverage"]["adoption"])
        self.assertEqual(before, self.ledger.events())
        # Capturing preparation after later growth still ends at the freeze.
        self.assertEqual(first, assessment.assess_prepared_retrieval_study(self.prepare())["report"])
        self.assertEqual(first, assessment.assess_prepared_retrieval_study(prepared)["report"])

    def test_valid_coherent_repeat_difference_retains_both_without_pair_summary(self):
        runs = execute_pair(self.data, self.ledger)
        runs[1] = diverge_repeat(self.ledger, runs[1])
        self.assertEqual(runs[1], retrieval_contracts.get_retrieval_run(self.ledger, runs[1]["id"]))
        report = assessment.assess_prepared_retrieval_study(self.prepare("evaluation", runs))["report"]
        self.assertEqual(0, report["reproducibility"]["value"])
        self.assertEqual(2, len(report["quality"]["runs"]))
        self.assertIsNone(report["coverage"]["matched_pairs"])
        self.assertIsNone(report["coverage"]["pair_buckets"])

    def test_phase_specific_fieldsets_and_declared_freeze_are_enforced(self):
        path, request, contract = study_files(self.data, self.ledger)
        for field, value in (("run_terminal_ids", []), ("phase", "evaluation")):
            changed = {**request, field: value}
            path.write_text(canonical(changed))
            with self.assertRaises(ValueError):
                assessment.prepare_retrieval_study(path, declared_contract=contract)
        path.write_text(canonical(request))
        for field in ("freeze_event_hash", "evaluator_identity_hash", "candidate_algorithm_hash", "review_hash"):
            changed = {**contract, field: "0" * 64}
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepared = assessment.prepare_retrieval_study(path, declared_contract=changed)
                assessment.assess_prepared_retrieval_study(prepared)
        with self.assertRaises(ValueError):
            assessment.prepare_retrieval_study(path, declared_contract={**contract, "projection_hashes": {}})

    def test_changed_original_review_or_missing_captured_blob_refuses(self):
        prepared = self.prepare()
        role = "blob:" + self.data["freeze"]["body"]["artifacts"]["review"]["content_hash"]
        prepared["artifacts"].pop(role)
        prepared["manifest"].pop(role)
        with self.assertRaises(ValueError):
            assessment.assess_prepared_retrieval_study(prepared)
        path, _, declaration = study_files(self.data, self.ledger)
        review = deepcopy(self.data["review"])
        review["cases"][0]["novelty_note"] = "Changed after the freeze"
        raw = canonical(review).encode()
        (self.root / "review.json").write_bytes(raw)
        declaration["review_hash"] = digest(raw)
        prepared = assessment.prepare_retrieval_study(path, declared_contract=declaration)
        with self.assertRaisesRegex(ValueError, "declared lineage|frozen original"):
            assessment.assess_prepared_retrieval_study(prepared)

    def test_evaluation_requires_frozen_order_and_all_completed_claims(self):
        runs = execute_pair(self.data, self.ledger)
        prepared = self.prepare("evaluation", list(reversed(runs)))
        with self.assertRaisesRegex(ValueError, "frozen run keys"):
            assessment.assess_prepared_retrieval_study(prepared)


if __name__ == "__main__":
    unittest.main()
