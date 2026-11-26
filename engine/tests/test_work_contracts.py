import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from epiphysics import work_contracts as c, work_runner, work_adapters
from epiphysics.store import Ledger, canonical


def bind(value):
    declaration = value['declaration']
    declaration['public_policy_hash'] = c.hash_value(value['public_policy'])
    declaration['cohort_hash'] = c.hash_value(value['cases'])
    value['outcome_manifest']['cohort_hash'] = declaration['cohort_hash']
    declaration['outcome_manifest_hash'] = c.hash_value(value['outcome_manifest'])
    return value


def bundle(*, extras='forbid', run='fixture-1', after='initial', predecessor=None):
    cases = [
        {'id': 'required', 'family': 'software_service', 'available': ['statement', 'title'], 'required': ['statement'], 'submitted': ['statement']},
        {'id': 'valid-extra', 'family': 'software_service', 'available': ['statement', 'title'], 'required': ['statement'], 'submitted': ['statement', 'title']},
        {'id': 'false-reference', 'family': 'collective', 'available': ['statement'], 'required': ['statement'], 'submitted': ['statement', 'absent']},
        {'id': 'missing', 'family': 'collective', 'available': ['statement', 'title'], 'required': ['statement'], 'submitted': ['title']},
        {'id': 'abstention', 'family': 'collective', 'available': ['statement'], 'required': ['statement'], 'submitted': None},
    ]
    policy = {'version': 1, 'adapter': 'reference-policy-v1', 'denominator': 5,
              'family_denominators': {'software_service': 2, 'collective': 3},
              'outcome_definition': 'declared-reference-conformance-v1', 'rules': {'extras': extras}}
    declaration = {'id': run, 'stage': 'invented_fixture', 'adapter': policy['adapter'], 'after_step': after,
                   'predecessor': predecessor, 'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat(),
                   'max_seconds': 10, 'public_policy_hash': c.hash_value(policy), 'cohort_hash': c.hash_value(cases),
                   'source_hashes': work_runner.source_hashes(), 'roles': {'author': 'invented-author', 'reviewer': 'invented-reviewer'},
                   'method_descriptor': None, 'method_id': None}
    outcomes = [{'id': case['id'], 'submitted': case.pop('submitted')} for case in cases]
    return bind({'schema_version': 1, 'declaration': declaration, 'public_policy': policy, 'cases': cases,
                 'outcome_manifest': {'version': 1, 'cohort_hash': None, 'records': outcomes}})


def artifact_bundle(run='artifact-fixture-1'):
    value = bundle(run=run)
    good = '{"value":1}'
    cases = [{'id': 'valid', 'family': 'information', 'artifact': good, 'expected_sha256': c.store.digest(good.encode())},
             {'id': 'wrong-digest', 'family': 'software_service', 'artifact': good, 'expected_sha256': '0' * 64},
             {'id': 'invalid-object', 'family': 'information', 'artifact': '[]', 'expected_sha256': c.store.digest(b'[]')},
             {'id': 'abstention', 'family': 'software_service', 'artifact': None, 'expected_sha256': c.store.digest(good.encode())}]
    policy = {'version': 1, 'adapter': 'artifact-quality-v1', 'denominator': 4,
              'family_denominators': {'information': 2, 'software_service': 2},
              'outcome_definition': 'declared-artifact-quality-v1',
              'rules': {'max_bytes': 128, 'required_keys': ['value'], 'extra_keys': 'forbid'}}
    outcomes = [{'id': case['id'], 'artifact': case.pop('artifact')} for case in cases]
    value.update(public_policy=policy, cases=cases, outcome_manifest={'version': 1, 'cohort_hash': None, 'records': outcomes})
    value['declaration']['adapter'] = policy['adapter']
    return bind(value)


class FixtureCase(unittest.TestCase):
    def setUp(self):
        location = os.environ.get('EPIPHYSICS_WORK_TEST_EVIDENCE')
        if location:
            Path(location).mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-', dir=location)).resolve()
        self.retained = bool(location)
        self.store = self.root / 'owned-ledger'
        Ledger(self.store).close()

    def tearDown(self):
        if not self.retained:
            shutil.rmtree(self.root)

    def write(self, value, name='bundle.json'):
        path = self.root / name
        path.write_text(canonical(value))
        return path

    def events(self):
        ledger = Ledger.open_readonly(self.store)
        try:
            self.assertTrue(ledger.verify()['valid'])
            return ledger.events()
        finally:
            ledger.close()


class ContractTests(FixtureCase):
    def test_public_instructions_are_same_policy_without_gold(self):
        value = bundle()
        shown = c.public_instructions(value)
        self.assertEqual(shown['policy'], value['public_policy'])
        self.assertEqual(shown['policy_hash'], c.hash_value(shown['policy']))
        self.assertNotIn('cases', shown)

    def test_policy_hash_and_denominator_mismatch_refuse_before_claim(self):
        for change in ('rules', 'denominator', 'cohort', 'family'):
            value = bundle()
            if change == 'rules': value['public_policy']['rules']['extras'] = 'allow_valid'
            if change == 'denominator': value['public_policy']['denominator'] = 4
            if change == 'cohort': value['cases'][0]['available'] = ['statement']
            if change == 'family': value['public_policy']['family_denominators']['collective'] = 2
            with self.assertRaises(ValueError): work_runner.prepare(self.write(value), self.store)
        self.assertEqual(self.events(), [])

    def test_source_pin_and_unlisted_adapter_refuse(self):
        value = bundle(); value['declaration']['source_hashes']['work_runner'] = '0' * 64
        with self.assertRaises(ValueError): work_runner.prepare(self.write(value), self.store)
        value = bundle(); value['declaration']['adapter'] = value['public_policy']['adapter'] = 'os.system'
        value['declaration']['public_policy_hash'] = c.hash_value(value['public_policy'])
        with self.assertRaisesRegex(ValueError, 'allowlisted'): work_runner.prepare(self.write(value), self.store)
        self.assertEqual(self.events(), [])

    def test_contract_changes_are_incomparable_not_accuracy_deltas(self):
        original = bundle(); first = c.measurement_identity(original)
        for name in ('policy', 'cohort', 'scorer', 'outcome', 'denominator'):
            value = copy.deepcopy(original)
            if name == 'policy': value['public_policy']['rules']['extras'] = 'allow_valid'
            if name == 'cohort': value['cases'][0]['available'] = ['statement']
            if name == 'scorer': value['declaration']['source_hashes']['work_adapters'] = '1' * 64
            if name == 'outcome': value['public_policy']['outcome_definition'] = 'new-outcome-v2'
            if name == 'denominator':
                value['cases'].pop(); value['public_policy']['denominator'] -= 1
                value['public_policy']['family_denominators']['collective'] -= 1
                value['outcome_manifest']['records'].pop()
            bind(value)
            comparison = c.compare(first, c.measurement_identity(value))
            self.assertEqual(comparison['status'], 'incomparable_contract_change')
            self.assertIsNone(comparison['delta'])

    def test_duplicate_json_and_unknown_authority_are_rejected(self):
        with self.assertRaises(ValueError): c.decode(b'{"x":1,"x":2}')
        value = bundle(); value['declaration']['command'] = 'arbitrary'
        with self.assertRaises(ValueError): c.validate(value)

    def test_distinct_candidate_methods_do_not_change_measurement_contract(self):
        first = bundle()
        descriptor = {'schema_version': 1, 'encoding': 'json', 'schema_id': 'fixture-v1',
                      'construction_method': 'method-one', 'observer': 'fixture-author',
                      'artifact_hashes': {key: 'a' * 64 for key in c.manifests.ARTIFACT_ROLES},
                      'task': {'id': 'fixture', 'family': 'software_service', 'outcome_type': 'binary'},
                      'horizon_seconds': 1, 'units': {}}
        first['declaration']['method_descriptor'] = descriptor
        first['declaration']['method_id'] = c.manifests.method_identity(descriptor)
        second = copy.deepcopy(first)
        second['declaration']['method_descriptor']['construction_method'] = 'method-two'
        second['declaration']['method_id'] = c.manifests.method_identity(second['declaration']['method_descriptor'])
        self.assertNotEqual(first['declaration']['method_id'], second['declaration']['method_id'])
        self.assertEqual(c.measurement_identity(first), c.measurement_identity(second))
        self.assertEqual(c.compare(c.measurement_identity(first), c.measurement_identity(second))['status'],
                         'same_measurement_contract')
        second['declaration']['source_hashes']['improvement'] = 'b' * 64
        second['declaration']['source_hashes']['work_runner'] = 'c' * 64
        self.assertEqual(c.compare(c.measurement_identity(first), c.measurement_identity(second))['status'],
                         'incomparable_contract_change')
        # Compatibility is descriptive eligibility; this helper invents no
        # measured gain or causal effect from candidate identity changes.
        self.assertIsNone(c.compare(c.measurement_identity(first), c.measurement_identity(second))['delta'])

    def test_distinct_outcomes_share_fixed_measurement_obligations_in_both_domains(self):
        for factory, output_field, changed in ((bundle, 'submitted', None), (artifact_bundle, 'artifact', None)):
            first = factory(); second = copy.deepcopy(first)
            second['outcome_manifest']['records'][0][output_field] = changed
            bind(second)
            self.assertEqual(c.measurement_identity(first), c.measurement_identity(second))
            self.assertNotEqual(first['declaration']['outcome_manifest_hash'], second['declaration']['outcome_manifest_hash'])
            self.assertEqual(work_adapters.assess(first)['conformance']['numerator'], 1)
            self.assertEqual(work_adapters.assess(second)['conformance']['numerator'], 0)
            self.assertEqual(c.compare(c.measurement_identity(first), c.measurement_identity(second))['status'],
                             'same_measurement_contract')

    def test_outcome_manifest_hash_order_and_cohort_binding_are_enforced(self):
        for field in ('digest', 'order', 'cohort'):
            value = bundle()
            if field == 'digest': value['outcome_manifest']['records'][0]['submitted'] = None
            if field == 'order':
                value['outcome_manifest']['records'].reverse()
                value['declaration']['outcome_manifest_hash'] = c.hash_value(value['outcome_manifest'])
            if field == 'cohort':
                value['outcome_manifest']['cohort_hash'] = 'a' * 64
                value['declaration']['outcome_manifest_hash'] = c.hash_value(value['outcome_manifest'])
            with self.assertRaises(ValueError): work_runner.prepare(self.write(value), self.store)
        self.assertEqual(self.events(), [])

    def test_symlink_and_fifo_inputs_refuse_without_blocking(self):
        real = self.write(bundle()); alias = self.root / 'alias.json'; alias.symlink_to(real)
        with self.assertRaises(OSError): c.read(alias)
        fifo = self.root / 'pipe'; os.mkfifo(fifo)
        with self.assertRaises(ValueError): c.read(fifo)


if __name__ == '__main__':
    unittest.main()
