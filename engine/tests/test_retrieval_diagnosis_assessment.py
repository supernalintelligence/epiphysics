"""Captured diagnosis transport on owned receipts and source bytes."""
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import retrieval_assessment as assessment, retrieval_diagnosis as diagnosis
from epiphysics.store import Ledger, canonical, digest
from test_retrieval_diagnosis import make_diagnosis_fixture, bind_diagnosis


class DiagnosisAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = Ledger(self.root / "evidence")
        self.addCleanup(self.evidence.close)
        self.data = make_diagnosis_fixture(self.root, self.evidence)
        self.path, self.request, self.contract, self.review = bind_diagnosis(self.data, self.evidence, self.data["origin"])

    def prepare(self):
        return assessment.prepare_retrieval_study(self.path, declared_contract=self.contract)

    def test_checked_wrapper_captures_originals_without_scoring_or_source_changes(self):
        before = self.evidence.events()
        prepared = self.prepare()
        forbidden = {"evaluate_retrieval", "_score_case", "_score_coverage", "_score_coverage_case",
                     "run_lexical_retrieval", "project_index", "lexical_search"}
        def guard(frame, event, arg):
            if event == "call" and frame.f_code.co_name in forbidden:
                raise AssertionError("Unexpected execution: " + frame.f_code.co_name)
        sys.setprofile(guard)
        try:
            measured = assessment.assess_prepared_retrieval_study(prepared)
        finally:
            sys.setprofile(None)
        report = measured["report"]
        self.assertEqual({"schema_version", "phase", "status", "contract_id", "diagnosis_id", "study_id",
            "origin", "machine_findings", "semantic_review", "diagnosis_contract_identity", "assessment_identity", "input_bindings"}, set(report))
        self.assertEqual((3, "support_diagnosis", "checked"), (report["schema_version"], report["phase"], report["status"]))
        self.assertEqual({"assessment_report"}, set(measured["artifacts"]) - set(prepared["artifacts"]))
        self.assertLessEqual(len(measured["artifacts"]["assessment_report"]), 256 * 1024)
        for role, field in (("support_diagnosis", "diagnosis_file"), ("support_diagnosis_review", "diagnosis_review_file"), ("origin_transition", "origin_file")):
            self.assertEqual(Path(self.request[field]).read_bytes(), prepared["artifacts"][role])
        self.assertIn("code:epiphysics.retrieval_diagnosis", prepared["artifacts"])
        self.assertEqual(before, self.evidence.events())

    def test_captured_diagnosis_works_after_all_original_paths_disappear(self):
        prepared = self.prepare()
        expected = assessment.assess_prepared_retrieval_study(prepared)
        self.evidence.close()
        shutil.rmtree(self.evidence.root)
        for path in self.root.glob("*.json"):
            path.unlink()
        self.assertEqual(expected, assessment.assess_prepared_retrieval_study(prepared))

    def test_changed_or_missing_captured_artifact_and_checker_source_refuse(self):
        prepared = self.prepare()
        for role in ("origin_transition", "support_diagnosis_review", "support_diagnosis"):
            with self.subTest(role=role):
                altered = deepcopy(prepared)
                altered["artifacts"][role] += b"changed"
                altered["manifest"][role] = digest(altered["artifacts"][role])
                with self.assertRaises(ValueError):
                    assessment.assess_prepared_retrieval_study(altered)
                altered["artifacts"].pop(role)
                altered["manifest"].pop(role)
                with self.assertRaises(ValueError):
                    assessment.assess_prepared_retrieval_study(altered)
        with patch.object(diagnosis, "IMPLEMENTATION_SOURCE", diagnosis.IMPLEMENTATION_SOURCE + b"\n"):
            with self.assertRaises(ValueError):
                assessment.check_prepared_retrieval_study(prepared)

    def test_new_files_have_individual_bounds_and_regular_file_defenses(self):
        for role, (field, _, maximum) in assessment.DIAGNOSIS_FILES.items():
            with self.subTest(role=role):
                path = Path(self.request[field])
                original = path.read_bytes()
                path.write_bytes(b"x" * (maximum + 1))
                with self.assertRaises(ValueError):
                    self.prepare()
                path.unlink()
                path.symlink_to(path.name)
                with self.assertRaises(ValueError):
                    self.prepare()
                path.unlink()
                path.write_bytes(original)

    def test_exact_phase_and_focus_declarations_are_required(self):
        for field, value in (("focus_question_ids", []), ("focus_question_ids", ["q-5-answerable", "q-5-answerable"]),
                             ("diagnosis_id", "other"), ("phase", "evaluation")):
            with self.subTest(field=field, value=value):
                self.path.write_text(canonical({**self.request, field: value}))
                with self.assertRaises(ValueError):
                    self.prepare()
        self.path.write_text(canonical(self.request))
        with self.assertRaises(ValueError):
            assessment.prepare_retrieval_study(self.path, declared_contract={**self.contract, "probe": {}})

    def test_frozen_original_file_bytes_cannot_be_reformatted(self):
        report = assessment.assess_prepared_retrieval_study(self.prepare())["report"]
        for field in ("cohort_file_hash", "protocol_file_hash", "review_file_hash"):
            self.assertEqual(report["input_bindings"][field], report["machine_findings"]["origin_bindings"][field])
        for field, declared_hash in (("cohort_file", None), ("protocol_file", "protocol_hash"), ("review_file", "review_hash")):
            with self.subTest(field=field):
                path = Path(self.request[field])
                original = path.read_bytes()
                declaration = dict(self.contract)
                path.write_bytes(original + b"\n")
                if declared_hash is not None:
                    self.contract[declared_hash] = digest(path.read_bytes())
                try:
                    with self.assertRaises(ValueError):
                        assessment.assess_prepared_retrieval_study(self.prepare())
                finally:
                    self.contract = declaration
                    path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
