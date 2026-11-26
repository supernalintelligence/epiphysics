"""Unrelated tiny owned fixtures; none of the actual navigation cases or answers."""
from copy import deepcopy
import unittest
from epiphysics import navigation_contracts as c


def tiny_map():
    value = {'schemaVersion': 1, 'sourceCommit': '1' * 40, 'catalogHash': '2' * 64,
        'nodes': [
            {'id': 'box', 'kind': 'claim', 'title': 'Owned marble crate', 'statement': 'One painted crate was inspected. This does not establish universal durability.', 'status': 'reported_result', 'basis': 'observed'},
            {'id': 'wheel', 'kind': 'claim', 'title': 'Owned square wheel', 'statement': 'A square wheel may resist rolling.', 'status': 'hypothesis', 'basis': 'inferred'},
            {'id': 'paper', 'kind': 'source', 'title': 'Owned imaginary bibliography', 'href': 'https://example.invalid/paper', 'date': None,
             'dateType': None, 'reviewedOn': None, 'bibliographicOnly': True, 'limitations': ['Invented fixture; no source fetched.']},
            {'id': 'note', 'kind': 'document', 'title': 'Owned workshop note', 'href': '/experiments/owned-note', 'contentHash': '3' * 64, 'commit': '1' * 40},
            {'id': 'trial', 'kind': 'experiment', 'title': 'Owned paint trial', 'status': 'proposed'}],
        'edges': [{'source': 'box', 'target': target, 'type': kind} for target, kind in [('paper', 'cites'), ('note', 'cites'), ('wheel', 'challenges'), ('trial', 'motivates')]],
        'limits': ['Owned synthetic fixture, not actual research evidence.']}
    value['payloadHash'] = c.digest(c.canonical(value))
    return value


def tiny_cases(public_map=None):
    public_map = public_map or tiny_map()
    ops = ['cite_sources', 'outgoing_qualification', 'motivated_followups', 'cite_documents', 'inline_scope', 'motivated_followups']
    return {'schema_version': 1, 'contract_id': c.CONTRACT_ID, 'map_payload_hash': public_map['payloadHash'],
        'cases': [{'case_id': 'owned_' + str(index), 'family': c.OPERATORS[op], 'prompt': 'Owned synthetic ' + op,
            'anchor_title': 'Owned marble crate', 'operator': op, 'requested_fields': list(c.REQUESTED_FIELDS)} for index, op in enumerate(ops)]}


def unresolved(case=None, public_map=None):
    public_map = public_map or tiny_map(); case = case or tiny_cases(public_map)['cases'][0]
    return {'schema_version': 1, 'case_id': case['case_id'], 'map_payload_hash': public_map['payloadHash'],
        'answer_status': 'unresolved', 'references': [], 'relationships': [], 'claim_labels': None, 'target_labels': [],
        'interpretations': ['insufficient_support'], 'unresolved_reason': 'Owned fixture abstention.'}


class NavigationContractTests(unittest.TestCase):
    def test_tiny_public_input_contains_no_key_or_answer_fields(self):
        public_map = tiny_map(); cohort = tiny_cases(public_map)
        c.validate_cohort(cohort, c.validate_map(public_map))
        raw = c.candidate_input(public_map, cohort['cases'][0])
        self.assertEqual(set(c.decode(raw, c.MAX_INPUT_BYTES)), {'schema_version', 'contract_id', 'map', 'case'})
        c.validate_candidate_input(c.decode(raw, c.MAX_INPUT_BYTES))
        cohort['cases'][0]['answer'] = 'hidden'
        with self.assertRaisesRegex(ValueError, 'fields'):
            c.candidate_input(public_map, cohort['cases'][0])

    def test_cohort_freezes_six_cases_families_operators_and_order(self):
        public_map = tiny_map()
        for mutate in [lambda v: v['cases'].pop(), lambda v: v['cases'].reverse(),
                       lambda v: v['cases'][1].update(case_id='owned_0'),
                       lambda v: v['cases'][0].update(anchor_title='Missing crate')]:
            cohort = tiny_cases(public_map); mutate(cohort)
            with self.assertRaises(ValueError): c.validate_cohort(cohort, public_map)

    def test_map_integrity_and_private_field_injection_refused(self):
        value = tiny_map(); value['nodes'][0]['statement'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'hash'): c.validate_map(value)
        value = tiny_map(); value['nodes'][0]['private_body'] = 'unapproved'
        value['payloadHash'] = c.digest(c.canonical({k: v for k, v in value.items() if k != 'payloadHash'}))
        with self.assertRaisesRegex(ValueError, 'fields'): c.validate_map(value)

    def test_duplicate_keys_nonfinite_and_extra_response_fields_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError): c.decode(raw, 100)
        value = unresolved(); value['score'] = 1
        with self.assertRaisesRegex(ValueError, 'fields'): c.validate_response(value, tiny_cases()['cases'][0], tiny_map())

    def test_unresolved_is_explicit_and_semantic_errors_are_not_silently_corrected(self):
        value = unresolved(); c.validate_response(value, tiny_cases()['cases'][0], tiny_map())
        value['unresolved_reason'] = None
        with self.assertRaisesRegex(ValueError, 'reason'): c.validate_response(value, tiny_cases()['cases'][0], tiny_map())
        value = unresolved(); value.update(answer_status='answered', unresolved_reason=None,
            relationships=[{'source': 'paper', 'target': 'box', 'type': 'cites'}])
        self.assertEqual(c.validate_response(value, tiny_cases()['cases'][0], tiny_map())['relationships'][0]['source'], 'paper')

    def test_pointer_must_name_an_exported_scalar(self):
        node = tiny_map()['nodes'][2]
        self.assertIsNone(c.pointer_value(node, '/date'))
        self.assertEqual(c.pointer_value(node, '/limitations/0'), 'Invented fixture; no source fetched.')
        for pointer in ('/limitations', '/limitations/9', '/../key', '/private'):
            with self.assertRaises(ValueError): c.pointer_value(node, pointer)


if __name__ == '__main__': unittest.main()
