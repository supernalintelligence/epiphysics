"""Literal invented content controls; never import candidate/oracle helpers."""
import ast
import copy
import inspect
import json
import sys
import unittest
from unittest.mock import patch

from epiphysics import prospective_query_check as checker

FAMILY = 'software_component'
FIELDS = ['subject_id', 'knowledge_cutoff_utc', 'outcome_cutoff_utc', 'source_observation_ids',
          'seen_id_set', 'opening_eligibility']
OTHER = ['promisor_role_id', 'beneficiary_role_id', 'source_sha256', 'quality_rule_hash',
         'acceptance_event_id', 'authorized_submission_channel_id']
ANSWERS = {'subject_id': 'component:literal', 'knowledge_cutoff_utc': '2026-12-01T00:00:00.000000Z',
           'outcome_cutoff_utc': '2026-12-01T00:10:00.000000Z',
           'source_observation_ids': ['o', 'p', 'q'], 'seen_id_set': [7, 11],
           'opening_eligibility': {'11': True}}
SUPPORT = {'subject_id': ['q'], 'knowledge_cutoff_utc': ['q'], 'outcome_cutoff_utc': ['q'],
           'source_observation_ids': ['o', 'p', 'q'], 'seen_id_set': ['o', 'p', 'q'],
           'opening_eligibility': ['o', 'q']}
ORACLE = {'oracle_schema_version': 1,
          'declaration_sha256': 'ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65',
          'manifest_sha256': 'a' * 64,
          'input_bodies': [{'key': k, 'status': 'supplied', 'byte_length': 2, 'sha256': 'b' * 64}
                           for k in ['o', 'o:headers', 'p', 'p:headers', 'q']],
          'timing_assurance': 'caller_claims_only', 'independent_collection_verified': False,
          'status': 'available', 'family': FAMILY, 'question_id': 'question:literal',
          'required_fields_by_family': {'software_component': FIELDS, 'local_delivery_obligation': FIELDS[:4] + OTHER},
          'required_fields': FIELDS, 'inapplicable_fields': OTHER,
          'answers': ANSWERS, 'field_status': {f: 'known' for f in FIELDS},
          'required_support': SUPPORT, 'unknown_reasons': {}, 'eligible_observation_ids': ['o', 'p', 'q'],
          'observations': [{'id': k, 'kind': kind, 'status': 'admitted', 'reasons': []}
                           for k, kind in [('o', 'release_sample'), ('p', 'release_sample'), ('q', 'question_contract')]],
          'missing_slots': [], 'reasons': []}
RESPONSE = {'answers': ANSWERS, 'provenance': SUPPORT}
# This complete literal result is frozen before the first checker execution.
EXPECTED = {'checker_schema_version': 1, 'family': FAMILY, 'planned_fields': 6,
            'evaluable_fields': 6, 'oracle_unknown': 0, 'response_status': 'parsed',
            'schema_errors': [], 'value_matches': 6, 'missing_values': 0, 'wrong_values': 0,
            'invalid_values': 0, 'supported_content_matches': 6, 'missing_support_fields': 0,
            'invalid_references': 0, 'additional_valid_references': 0, 'duplicate_valid_references': 0,
            'content_complete': True, 'interface_runtime_assurance': 'unverified',
            'fields': {f: {'oracle_status': 'known', 'candidate_value_present': True,
                           'candidate_value_valid': True, 'value_status': 'correct',
                           'missing_support': [], 'invalid_references': [], 'additional_valid_references': [],
                           'valid_reference_ids': SUPPORT[f],
                           'duplicate_valid_references': [], 'support_complete': True,
                           'supported_content_match': True} for f in FIELDS}}


def raw(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class ContentChecks(unittest.TestCase):
    def check(self, response=None, oracle=None, family=FAMILY):
        return checker.check_query_content(raw(ORACLE if oracle is None else oracle),
                                           raw(RESPONSE if response is None else response), family)

    def test_complete_literal(self):
        self.assertEqual(self.check(), EXPECTED)

    def test_obligation_ten_literal_fields(self):
        p = copy.deepcopy(ORACLE)
        p.update(family='local_delivery_obligation', required_fields=FIELDS[:4] + OTHER,
                 inapplicable_fields=['seen_id_set', 'opening_eligibility'])
        p['observations'][0]['kind'] = 'acceptance'
        p['observations'][1]['kind'] = 'source_blob'
        p['input_bodies'] = [b for b in p['input_bodies'] if ':headers' not in b['key']]
        p['answers'] = {k: copy.deepcopy(v) for k, v in ANSWERS.items() if k in FIELDS[:4]}
        p['answers'].update(promisor_role_id='role:b', beneficiary_role_id='role:a',
                            source_sha256='c'*64, quality_rule_hash='d'*64,
                            acceptance_event_id='event:e', authorized_submission_channel_id='channel:x')
        p['required_support'] = {k: copy.deepcopy(v) for k, v in SUPPORT.items() if k in FIELDS[:4]}
        p['required_support'].update({f: ['o', 'q'] for f in OTHER})
        p['required_support']['source_sha256'] = ['o', 'p', 'q']
        p['field_status'] = {f: 'known' for f in FIELDS[:4] + OTHER}
        r = {'answers': copy.deepcopy(p['answers']), 'provenance': copy.deepcopy(p['required_support'])}
        result = self.check(r, p, 'local_delivery_obligation')
        self.assertEqual((result['planned_fields'], result['evaluable_fields'], result['supported_content_matches'], result['content_complete']), (10, 10, 10, True))
        r['answers']['promisor_role_id'], r['answers']['beneficiary_role_id'] = 'role:a', 'role:b'
        result = self.check(r, p, 'local_delivery_obligation')
        self.assertEqual((result['wrong_values'], result['supported_content_matches']), (2, 8))

    def test_wrong_and_missing_values(self):
        r = copy.deepcopy(RESPONSE)
        r['answers']['subject_id'] = 'component:wrong'
        del r['answers']['seen_id_set']
        result = self.check(r)
        self.assertEqual((result['wrong_values'], result['missing_values'], result['supported_content_matches']), (1, 1, 4))
        self.assertFalse(result['content_complete'])

    def test_missing_response_is_missing(self):
        r = checker.check_query_content(raw(ORACLE), None, FAMILY)
        self.assertEqual((r['planned_fields'], r['missing_values'], r['missing_support_fields'], r['supported_content_matches'], r['response_status']), (6, 6, 6, 0, 'missing'))
        self.assertFalse(r['content_complete'])

    def test_unknowns_not_wrong_or_removed(self):
        p = copy.deepcopy(ORACLE)
        for f in ['source_observation_ids', 'seen_id_set']:
            p['answers'][f] = None
            p['field_status'][f] = 'oracle_unknown'
            p['required_support'][f] = []
            p['unknown_reasons'][f] = ['snapshot_membership_unknown']
        p['status'], p['reasons'], p['missing_slots'] = 'unavailable', ['snapshot_membership_unknown'], ['unreceived-slot']
        r = self.check(oracle=p)
        self.assertEqual((r['planned_fields'], r['evaluable_fields'], r['oracle_unknown'], r['wrong_values'], r['supported_content_matches']), (6, 4, 2, 0, 4))
        self.assertIsNone(r['fields']['seen_id_set']['support_complete'])
        self.assertFalse(r['content_complete'])
        r = checker.check_query_content(raw(p), None, FAMILY)
        self.assertEqual((r['missing_values'], r['oracle_unknown'], r['wrong_values']), (6, 2, 0))

    def test_unbound_oracle_retains_planned_family(self):
        p = copy.deepcopy(ORACLE)
        p.update(family=None, question_id=None, required_fields=[], inapplicable_fields=[],
                 answers={}, field_status={}, required_support={}, unknown_reasons={},
                 eligible_observation_ids=[], status='unavailable', reasons=['question_contract_unavailable'])
        for o in p['observations']:
            o.update(status='excluded' if o['id'] == 'q' else 'unavailable', reasons=['question_contract_unavailable'])
        for family, denominator in [('software_component', 6), ('local_delivery_obligation', 10)]:
            r = checker.check_query_content(raw(p), None, family)
            self.assertEqual((r['planned_fields'], r['oracle_unknown'], r['evaluable_fields'], r['wrong_values']), (denominator, denominator, 0, 0))

    def test_required_extra_and_duplicate_support(self):
        r = copy.deepcopy(RESPONSE)
        r['provenance']['subject_id'] = ['q', 'p', 'q', 'p']
        result = self.check(r)
        self.assertEqual((result['supported_content_matches'], result['additional_valid_references'], result['duplicate_valid_references'], result['content_complete']), (6, 1, 2, True))
        self.assertEqual(result['fields']['subject_id']['additional_valid_references'], ['p'])
        self.assertEqual(result['fields']['subject_id']['duplicate_valid_references'], ['q', 'p'])
        r['provenance']['seen_id_set'] = ['o', 'p', 'o']
        result = self.check(r)
        self.assertEqual(result['fields']['seen_id_set']['missing_support'], ['q'])
        self.assertEqual((result['value_matches'], result['supported_content_matches'], result['missing_support_fields']), (6, 5, 1))

    def test_invalid_references_do_not_hide_full_required_set(self):
        r = copy.deepcopy(RESPONSE)
        r['provenance']['subject_id'] += ['future', ' q', 1, True, [], {'x': 1}]
        result = self.check(r)
        self.assertEqual((result['value_matches'], result['supported_content_matches'], result['invalid_references']), (6, 5, 6))
        self.assertEqual(result['fields']['subject_id']['missing_support'], [])
        self.assertFalse(result['fields']['subject_id']['support_complete'])

    def test_excluded_reference_invalid(self):
        p = copy.deepcopy(ORACLE)
        p['observations'][1].update(status='excluded', reasons=['late'])
        p['eligible_observation_ids'] = ['o', 'q']
        p['answers']['source_observation_ids'] = ['o', 'q']
        p['required_support']['source_observation_ids'] = ['o', 'q']
        p['required_support']['seen_id_set'] = ['o', 'q']
        r = {'answers': p['answers'], 'provenance': copy.deepcopy(p['required_support'])}
        r['provenance']['subject_id'] += ['p']
        result = self.check(r, p)
        self.assertEqual((result['supported_content_matches'], result['invalid_references']), (5, 1))

    def test_unknown_extra_keys_are_schema_failures(self):
        for target in ['root', 'answers', 'provenance']:
            r = copy.deepcopy(RESPONSE)
            (r if target == 'root' else r[target])['extra'] = 'opaque'
            result = self.check(r)
            self.assertEqual(result['supported_content_matches'], 6)
            self.assertTrue(result['schema_errors'])
            self.assertFalse(result['content_complete'])

    def test_global_shapes_and_parse_failure_have_no_matches(self):
        for r in [[], True, None, 1, 'text', {'answers': [], 'provenance': []}]:
            result = checker.check_query_content(raw(ORACLE), raw(r), FAMILY)
            self.assertEqual(result['supported_content_matches'], 0)
            self.assertTrue(result['schema_errors'])
        for r in [b'{', b'\xff', b'\xef\xbb\xbf{}', b'{"answers":{},"answers":{}}', b'{"x":{"a":1,"a":2}}', b'{} trailing']:
            result = checker.check_query_content(raw(ORACLE), r, FAMILY)
            self.assertEqual((result['supported_content_matches'], result['response_status']), (0, 'unparseable'))

    def test_wrong_types_and_no_trim(self):
        for field, value in [('subject_id', ' component:literal'), ('subject_id', 42),
                             ('seen_id_set', [True, 11]), ('seen_id_set', [7.0, 11]),
                             ('opening_eligibility', {'11': 1}), ('opening_eligibility', {'011': True}),
                             ('source_observation_ids', ['q', 'p', 'o']), ('seen_id_set', [11, 7]),
                             ('seen_id_set', [7, 7, 11]), ('knowledge_cutoff_utc', '2026-02-30T00:00:00Z')]:
            with self.subTest(field=field, value=value):
                r = copy.deepcopy(RESPONSE); r['answers'][field] = value
                result = self.check(r)
                self.assertEqual((result['invalid_values'], result['supported_content_matches']), (1, 5))
                self.assertTrue(result['schema_errors'])

    def test_time_strings_exact_not_coerced(self):
        r = copy.deepcopy(RESPONSE); r['answers']['knowledge_cutoff_utc'] = '2026-12-01T00:00:00Z'
        result = self.check(r)
        self.assertEqual((result['wrong_values'], result['supported_content_matches']), (1, 5))

    def test_map_order_is_irrelevant(self):
        p = copy.deepcopy(ORACLE); p['answers']['opening_eligibility'] = {'7': False, '11': True}
        r = copy.deepcopy(RESPONSE); r['answers']['opening_eligibility'] = {'11': True, '7': False}
        self.assertTrue(self.check(r, p)['content_complete'])

    def test_missing_bad_provenance_unaffected_fields_survive(self):
        for refs in [None, 'q', True, {}]:
            r = copy.deepcopy(RESPONSE); r['provenance']['subject_id'] = refs
            result = self.check(r)
            self.assertEqual((result['supported_content_matches'], result['missing_support_fields']), (5, 1))
            self.assertTrue(result['schema_errors'])
        r = copy.deepcopy(RESPONSE); del r['provenance']['subject_id']
        self.assertEqual(self.check(r)['supported_content_matches'], 5)

    def test_oracle_malformed_is_refusal(self):
        cases = []
        for key, value in [('oracle_schema_version', True), ('status', 'unavailable'), ('family', 'other'),
                           ('eligible_observation_ids', ['o', 'q']), ('required_fields', FIELDS[:-1]),
                           ('independent_collection_verified', 0), ('question_id', ' q')]:
            p = copy.deepcopy(ORACLE); p[key] = value; cases.append(p)
        p = copy.deepcopy(ORACLE); p['required_support']['seen_id_set'] = ['o', 'p']; cases.append(p)
        p = copy.deepcopy(ORACLE); p['required_support']['subject_id'] = ['p', 'q']; cases.append(p)
        p = copy.deepcopy(ORACLE); p['required_support']['subject_id'] = ['q', 'q']; cases.append(p)
        p = copy.deepcopy(ORACLE); p['answers']['opening_eligibility']['11'] = 1; cases.append(p)
        p = copy.deepcopy(ORACLE); p['answers']['source_observation_ids'] = ['o', 'q']; cases.append(p)
        p = copy.deepcopy(ORACLE); p['answers']['seen_id_set'] = [7]; cases.append(p)
        p = copy.deepcopy(ORACLE); p['missing_slots'] = ['absent']; cases.append(p)
        p = copy.deepcopy(ORACLE); p['observations'][0]['status'] = 'excluded'; cases.append(p)
        p = copy.deepcopy(ORACLE); p['input_bodies'][0].update(status='missing', byte_length=None, sha256=None); cases.append(p)
        p = copy.deepcopy(ORACLE); p['answers']['outcome_cutoff_utc'] = '2020-01-01T00:00:00Z'; cases.append(p)
        p = copy.deepcopy(ORACLE); p['unknown_reasons']['subject_id'] = ['x']; cases.append(p)
        p = copy.deepcopy(ORACLE); p['answers']['seen_id_set'] = None; p['field_status']['seen_id_set'] = 'oracle_unknown'; cases.append(p)
        for p in cases:
            with self.subTest(case=p):
                with self.assertRaises(checker.CheckerRefusal):
                    self.check(oracle=p)
        for malformed in [b'{}', b'[]', b'{"x":1,"x":2}', b'\xff']:
            with self.assertRaises(checker.CheckerRefusal):
                checker.check_query_content(malformed, raw(RESPONSE), FAMILY)

    def test_caps(self):
        for response in [b' ' * 65537, bytearray(raw(RESPONSE))]:
            self.assertEqual(checker.check_query_content(raw(ORACLE), response, FAMILY)['response_status'], 'unparseable')
        with self.assertRaises(checker.CheckerRefusal):
            checker.check_query_content(b' ' * 65537, None, FAMILY)
        for field, value in [('seen_id_set', list(range(1, 82))), ('opening_eligibility', {str(i): True for i in range(1, 7)})]:
            r = copy.deepcopy(RESPONSE); r['answers'][field] = value
            self.assertEqual(self.check(r)['invalid_values'], 1)
        # Exact cap is allowed; whitespace is retained, not trimmed from byte accounting.
        r = raw(RESPONSE)
        self.assertTrue(checker.check_query_content(raw(ORACLE), r + b' ' * (65536-len(r)), FAMILY)['content_complete'])

    def test_exact_large_integers(self):
        for ident in [9007199254740993, int('9' * 4300)]:
            p = copy.deepcopy(ORACLE); p['answers']['seen_id_set'] = [7, ident]
            p['answers']['opening_eligibility'] = {str(ident): True}
            r = {'answers': p['answers'], 'provenance': SUPPORT}
            self.assertTrue(self.check(r, p)['content_complete'])

    def test_numeric_limits_explicit(self):
        for token in [b'NaN', b'Infinity', b'1e400', b'1e-400', b'0.123456789012345678901234567890', b'9' * 4301]:
            response = b'{"x":' + token + b'}'
            self.assertEqual(checker.check_query_content(raw(ORACLE), response, FAMILY)['response_status'], 'unparseable')
            with self.assertRaises(checker.CheckerRefusal):
                checker.check_query_content(response, None, FAMILY)
        p = copy.deepcopy(RESPONSE); p['answers']['opening_eligibility'] = {'9' * 4301: True}
        self.assertEqual(self.check(p)['invalid_values'], 1)

    def test_decimal_operational_limits_on_both_public_inputs(self):
        # Frozen literals: valid JSON syntax whose exact decimal conversion or
        # finite float representation exceeds this unchanged runtime's bounds.
        for token in [b'0e999999999999999999999', b'0e-999999999999999999999',
                      b'-0e999999999999999999999', b'-0e-999999999999999999999',
                      b'0.0e999999999999999999999', b'0.0e-999999999999999999999',
                      b'1e999999999999999999999', b'1e-999999999999999999999']:
            with self.subTest(token=token):
                response = raw(RESPONSE)[:-1] + b',"probe":' + token + b'}'
                result = checker.check_query_content(raw(ORACLE), response, FAMILY)
                self.assertEqual((result['response_status'], result['schema_errors'],
                                  result['planned_fields'], result['supported_content_matches']),
                                 ('unparseable', ['response: numeric_limit'], 6, 0))
                oracle = raw(ORACLE)[:-1] + b',"probe":' + token + b'}'
                with self.assertRaisesRegex(checker.CheckerRefusal,
                                            '^oracle_or_plan_invalid: numeric_limit$'):
                    checker.check_query_content(oracle, raw(RESPONSE), FAMILY)

    def test_adjacent_finite_decimals_reach_schema_checks(self):
        # Finite exact decimal lexemes remain parseable; the deliberately extra
        # key then triggers only the ordinary public-schema error on each side.
        for token in [b'0e0', b'-0e0', b'0.0e308', b'0e-324',
                      b'0e999999999999999999', b'0e-999999999999999999',
                      b'1e0', b'1.25e2', b'1e308', b'1e-308']:
            with self.subTest(token=token):
                response = raw(RESPONSE)[:-1] + b',"probe":' + token + b'}'
                result = checker.check_query_content(raw(ORACLE), response, FAMILY)
                self.assertEqual((result['response_status'], result['schema_errors'],
                                  result['value_matches'], result['supported_content_matches'],
                                  result['content_complete']),
                                 ('parsed', ['response: wrong_object_fields'], 6, 6, False))
                oracle = raw(ORACLE)[:-1] + b',"probe":' + token + b'}'
                with self.assertRaisesRegex(checker.CheckerRefusal,
                                            '^oracle_or_plan_invalid: wrong_object_fields$'):
                    checker.check_query_content(oracle, raw(RESPONSE), FAMILY)

    def test_no_effects_mutation_or_hidden_imports(self):
        before = copy.deepcopy((ORACLE, RESPONSE, EXPECTED))
        ob, rb = raw(ORACLE), raw(RESPONSE)
        recursion, digits = sys.getrecursionlimit(), sys.get_int_max_str_digits()
        tree = ast.parse(inspect.getsource(checker))
        imports = [n.module if isinstance(n, ast.ImportFrom) else n.names[0].name
                   for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual(imports, ['json', 'math', 're', 'datetime', 'decimal'])
        with patch('builtins.open', side_effect=AssertionError('filesystem effect')), \
             patch('socket.socket', side_effect=AssertionError('network effect')), \
             patch('subprocess.Popen', side_effect=AssertionError('process effect')):
            self.assertEqual(checker.check_query_content(ob, rb, FAMILY), EXPECTED)
        self.assertEqual((ORACLE, RESPONSE, EXPECTED), before)
        self.assertEqual((ob, rb), (raw(ORACLE), raw(RESPONSE)))
        self.assertEqual((sys.getrecursionlimit(), sys.get_int_max_str_digits()), (recursion, digits))
        self.assertEqual(checker.check_query_content(ob, rb, FAMILY), EXPECTED)


if __name__ == '__main__':
    unittest.main()
