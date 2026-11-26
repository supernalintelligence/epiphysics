"""Bounded support-probe transport over owned evidence only."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import retrieval_assessment as assessment, retrieval_probe as probe
from epiphysics.store import Ledger, canonical, digest
from test_retrieval_probe import make_probe_fixture


class ProbeAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = Ledger(self.root / "evidence")
        self.addCleanup(self.evidence.close)
        if self._testMethodName == "test_inherited_unrelated_observation_is_preserved_for_complete_prefix_verification":
            self.inherited_raw = b"Owned unrelated historical note outside every selected retrieval source."
            self.inherited_observation = self.evidence.capture("owned:unrelated-history", self.inherited_raw, event_id="unrelated-history")
        self.data = make_probe_fixture(self.root, self.evidence)
        self.path, self.request, self.contract = (self.data[name] for name in ("request_path", "request", "contract"))

    def prepare(self):
        return assessment.prepare_retrieval_study(self.path, declared_contract=self.contract)

    def test_inherited_unrelated_observation_is_preserved_for_complete_prefix_verification(self):
        before = self.evidence.events()
        files_before = {str(path.relative_to(self.evidence.root)): (digest(path.read_bytes()), path.stat().st_mtime_ns)
            for path in self.evidence.root.rglob("*") if path.is_file()}
        accepted = self.data["origin"]["body"]["report"]["support_diagnosis"]["input_bindings"]["prefix_head"]
        inherited = self.data["probe_protocol"]["evidence_preservation"]["inherited_prefix"]
        boundary = before[inherited["events"] - 1]
        self.assertEqual(accepted, {key: boundary[key] for key in ("seq", "id", "hash")})
        self.assertLess(self.inherited_observation["seq"], accepted["seq"])
        corpus = self.evidence.get(self.request["corpus_id"])
        self.assertNotIn(self.inherited_observation["id"], [ref["observation_id"] for ref in corpus["body"]["sources"]])
        prepared = self.prepare()
        # The old capture omitted this blob even though its observation event
        # remained in the immutable prefix. The child then failed integrity.
        measured = assessment.assess_prepared_retrieval_study(prepared)
        self.assertEqual(1, measured["report"]["reproducibility"]["value"])
        content_hash = self.inherited_observation["body"]["content_hash"]
        self.assertEqual(self.inherited_raw, prepared["artifacts"]["blob:" + content_hash])
        bundle = json.loads(prepared["artifacts"]["evidence_bundle"])
        self.assertIn(self.inherited_observation, bundle["events"])
        self.assertEqual(len(self.inherited_raw), bundle["blobs"][content_hash])
        # Model exactly the prior transport omission without changing the
        # original source, accepted origin, event prefix, or checked helper.
        omitted = deepcopy(prepared)
        omitted["artifacts"].pop("blob:" + content_hash)
        bundle["blobs"].pop(content_hash)
        omitted["artifacts"]["evidence_bundle"] = canonical(bundle).encode()
        omitted["manifest"] = {role: digest(raw) for role, raw in omitted["artifacts"].items()}
        with self.assertRaisesRegex(ValueError, "evidence integrity"):
            assessment.assess_prepared_retrieval_study(omitted)
        self.assertEqual(before, self.evidence.events())
        files_after = {str(path.relative_to(self.evidence.root)): (digest(path.read_bytes()), path.stat().st_mtime_ns)
            for path in self.evidence.root.rglob("*") if path.is_file()}
        self.assertEqual(files_before, files_after)

    def test_captured_wrapper_is_read_only_and_does_not_search_or_rescore(self):
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
        self.assertEqual((3, "support_probe", "completed"), (report["schema_version"], report["phase"], report["status"]))
        self.assertEqual(1, report["reproducibility"]["value"])
        self.assertNotIn("quality", report)
        self.assertNotIn("measurement_contract_identity", report)
        self.assertEqual({"assessment_report"}, set(measured["artifacts"]) - set(prepared["artifacts"]))
        self.assertLessEqual(len(measured["artifacts"]["assessment_report"]), 256 * 1024)
        self.assertIn("code:epiphysics.retrieval_probe", prepared["artifacts"])
        for role, (field, _, _) in assessment.PROBE_FILES.items():
            self.assertEqual(Path(self.request[field]).read_bytes(), prepared["artifacts"][role])
        self.assertEqual(before, self.evidence.events())

    def test_captured_execution_works_after_original_paths_disappear(self):
        prepared = self.prepare()
        expected = assessment.assess_prepared_retrieval_study(prepared)
        self.evidence.close()
        shutil.rmtree(self.evidence.root)
        for path in self.root.glob("*.json"):
            path.unlink()
        self.assertEqual(expected, assessment.assess_prepared_retrieval_study(prepared))

    def test_new_artifacts_are_exact_bounded_regular_files(self):
        for role, (field, _, maximum) in assessment.PROBE_FILES.items():
            with self.subTest(role=role):
                path = Path(self.request[field])
                original = path.read_bytes()
                for replacement in (original + b"changed", b"x" * (maximum + 1)):
                    path.write_bytes(replacement)
                    with self.assertRaises(ValueError):
                        self.prepare()
                path.unlink()
                path.symlink_to(path.name)
                with self.assertRaises(ValueError):
                    self.prepare()
                path.unlink()
                path.write_bytes(original)

    def test_missing_captured_roles_and_changed_checker_refuse(self):
        prepared = self.prepare()
        for role in assessment.PROBE_FILES:
            altered = deepcopy(prepared)
            altered["artifacts"].pop(role)
            altered["manifest"].pop(role)
            with self.subTest(role=role), self.assertRaises(ValueError):
                assessment.assess_prepared_retrieval_study(altered)
        with patch.object(probe, "IMPLEMENTATION_SOURCE", probe.IMPLEMENTATION_SOURCE + b"\n"):
            with self.assertRaises(ValueError):
                assessment.check_prepared_retrieval_study(prepared)

    def test_claimed_head_cannot_hide_later_events_and_capture_keeps_existing_snapshot(self):
        prepared = self.prepare()
        expected = assessment.assess_prepared_retrieval_study(prepared)
        self.evidence.capture("owned:later", b"A later event must not be silently truncated.", event_id="later")
        with self.assertRaisesRegex(ValueError, "complete observed ledger tip"):
            self.prepare()
        self.assertEqual(expected, assessment.assess_prepared_retrieval_study(prepared))

    def test_frozen_c4_bytes_and_request_fieldset_remain_exact(self):
        for field, declared in (("cohort_file", None), ("protocol_file", "protocol_hash"), ("review_file", "review_hash")):
            with self.subTest(field=field):
                path = Path(self.request[field])
                original = path.read_bytes()
                contract = deepcopy(self.contract)
                path.write_bytes(original + b"\n")
                if declared is not None:
                    self.contract[declared] = digest(path.read_bytes())
                try:
                    with self.assertRaises(ValueError):
                        assessment.assess_prepared_retrieval_study(self.prepare())
                finally:
                    path.write_bytes(original)
                    self.contract = contract
        self.path.write_text(canonical({**self.request, "run_terminal_ids": []}))
        with self.assertRaises(ValueError):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
