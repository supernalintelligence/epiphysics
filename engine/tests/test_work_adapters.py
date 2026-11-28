import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).parent))
from test_work_contracts import bundle, artifact_bundle
from epiphysics import work_adapters, work_contracts as c


class AdapterTests(unittest.TestCase):
    def test_valid_extra_false_evidence_missing_and_abstention_are_distinct(self):
        report = work_adapters.assess(bundle())
        exact, extra, false, missing, abstention = report['cases']
        self.assertTrue(exact['conformance'])
        self.assertTrue(extra['valid_references']); self.assertTrue(extra['required_coverage'])
        self.assertEqual(extra['valid_extra_count'], 1); self.assertFalse(extra['conformance'])
        self.assertEqual(false['invalid_reference_count'], 1)
        self.assertTrue(missing['valid_references']); self.assertEqual(missing['missing_reference_count'], 1)
        self.assertTrue(abstention['abstained']); self.assertIsNone(abstention['valid_references'])
        self.assertEqual(report['conformance'], {'numerator': 1, 'denominator': 5})

    def test_allowed_valid_extras_do_not_permit_false_or_missing_evidence(self):
        value = bundle(extras='allow_valid'); report = work_adapters.assess(value)
        self.assertEqual(report['conformance'], {'numerator': 2, 'denominator': 5})
        self.assertTrue(report['cases'][1]['conformance'])
        self.assertFalse(report['cases'][2]['conformance']); self.assertFalse(report['cases'][3]['conformance'])

    def test_artifact_hash_format_and_abstention_are_separate(self):
        report = work_adapters.assess(artifact_bundle())
        good, wrong_hash, wrong_format, abstained = report['cases']
        self.assertTrue(good['conformance'])
        self.assertTrue(wrong_hash['object_format']); self.assertFalse(wrong_hash['digest_match'])
        self.assertTrue(wrong_format['digest_match']); self.assertFalse(wrong_format['object_format'])
        self.assertTrue(abstained['abstained']); self.assertIsNone(abstained['digest_match'])
        self.assertEqual(report['conformance'], {'numerator': 1, 'denominator': 4})


if __name__ == '__main__':
    unittest.main()
