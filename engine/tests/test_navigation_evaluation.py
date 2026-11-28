"""Scoring controls over invented marble-crate records only; no actual key."""
from copy import deepcopy
import unittest
from epiphysics import navigation_contracts as c, navigation_evaluation as evaluation
from test_navigation_contracts import tiny_map, tiny_cases, unresolved


def tiny_key(public_map=None, cohort=None):
    public_map = public_map or tiny_map(); cohort = cohort or tiny_cases(public_map)
    nodes = {node['id']: node for node in public_map['nodes']}; rows = {}
    for case in cohort['cases']:
        op = case['operator']
        target = {'cite_sources': 'paper', 'cite_documents': 'note', 'outgoing_qualification': 'wheel', 'motivated_followups': 'trial'}.get(op)
        edge_type = {'cite_sources': 'cites', 'cite_documents': 'cites', 'outgoing_qualification': 'challenges', 'motivated_followups': 'motivates'}.get(op)
        ref_node = target or 'box'; fields = ['/title'] if target else ['/statement']
        if target in {'paper', 'note'}: fields.append('/href')
        if target == 'paper': fields += ['/date', '/dateType', '/bibliographicOnly', '/limitations/0']
        labels = [] if target is None else [{'node_id': target, 'kind': nodes[target]['kind'], 'status': nodes[target].get('status'), 'basis': nodes[target].get('basis')}]
        interpretation = {'cite_sources': 'bibliographic_reference_only', 'cite_documents': 'document_metadata_only',
            'outgoing_qualification': 'qualification_not_refutation', 'inline_scope': 'explicit_scope_not_generalization', 'motivated_followups': 'proposed_not_completed'}[op]
        answer = {'references': [{'node_id': ref_node, 'pointer': field, 'quote': None} for field in fields],
            'relationships': [] if target is None else [{'source': 'box', 'target': target, 'type': edge_type}],
            'claim_labels': {'node_id': 'box', 'status': 'reported_result', 'basis': 'observed'},
            'target_labels': labels, 'interpretations': [interpretation]}
        rows[case['case_id']] = {'direction_required': op != 'inline_scope', 'alternatives': [answer]}
    return {'schema_version': 1, 'contract_id': c.CONTRACT_ID, 'map_payload_hash': public_map['payloadHash'],
        'cohort_hash': c.digest(c.canonical(cohort)), 'cases': rows}


def answer_for(case, public_map, key):
    return {'schema_version': 1, 'case_id': case['case_id'], 'map_payload_hash': public_map['payloadHash'],
        'answer_status': 'answered', 'unresolved_reason': None, **deepcopy(key['cases'][case['case_id']]['alternatives'][0])}


def tiny_attempts(public_map=None, cohort=None, key=None):
    public_map = public_map or tiny_map(); cohort = cohort or tiny_cases(public_map); key = key or tiny_key(public_map, cohort)
    return {case['case_id']: {'state': 'attempted', 'stdout': c.canonical(answer_for(case, public_map, key)), 'stderr': b'',
        'receipt': {'termination': {'kind': 'completed', 'stream': None}, 'returncode': 0, 'source_unchanged': True, 'process_started': True}}
        for case in cohort['cases']}


class NavigationEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.public_map = tiny_map(); self.cohort = tiny_cases(self.public_map); self.key = tiny_key(self.public_map, self.cohort)
        self.attempts = tiny_attempts(self.public_map, self.cohort, self.key)

    def score(self): return evaluation.evaluate(self.public_map, self.cohort, self.key, self.attempts)

    def alter(self, ordinal, mutate):
        identifier = self.cohort['cases'][ordinal]['case_id']; value = c.decode(self.attempts[identifier]['stdout'], c.MAX_STREAM_BYTES)
        mutate(value); self.attempts[identifier]['stdout'] = c.canonical(value)

    def test_positive_tiny_fixture_has_fixed_denominators_and_no_human_claim(self):
        result = self.score(); self.assertTrue(result['passed'])
        self.assertEqual({name: metric['denominator'] for name, metric in result['metrics'].items()}, c.DENOMINATORS)
        self.assertEqual(result['next_action'], 'prepare_independent_evidence_navigation_comparison')
        self.assertTrue(all(value is None for value in result['unknowns'].values()))

    def test_reversed_arrow_wrong_basis_and_proposal_as_result_are_separate_failures(self):
        self.alter(0, lambda v: v['relationships'][0].update(source='paper', target='box'))
        self.alter(1, lambda v: v['claim_labels'].update(basis='inferred'))
        self.alter(2, lambda v: v['target_labels'][0].update(status='completed'))
        result = self.score()
        self.assertEqual(result['metrics']['strict_completion']['numerator'], 3)
        self.assertFalse(result['cases'][0]['direction']); self.assertFalse(result['cases'][1]['claim_labels'])
        self.assertFalse(result['cases'][2]['target_labels']); self.assertEqual(result['next_action'], 'diagnose_textual_navigation_failure')

    def test_reference_existence_does_not_excuse_wrong_quote_or_reference_dump(self):
        self.alter(0, lambda v: v['references'][0].update(quote='Invented absent quotation'))
        self.alter(1, lambda v: v['references'].append({'node_id': 'trial', 'pointer': '/title', 'quote': None}))
        result = self.score()
        self.assertFalse(result['cases'][0]['reference_integrity']); self.assertFalse(result['cases'][1]['references'])
        self.assertTrue(result['cases'][1]['unpermitted_additions'])

    def test_valid_extra_metadata_is_unpermitted_but_not_invalid_evidence(self):
        self.alter(0, lambda v: v['references'].append({'node_id': 'paper', 'pointer': '/reviewedOn', 'quote': None}))
        row = self.score()['cases'][0]
        self.assertTrue(row['reference_integrity'])
        self.assertTrue(row['unpermitted_additions']); self.assertFalse(row['strict_completion'])
        self.assertFalse(row['references'])

    def test_unresolved_malformed_failure_and_unstarted_never_shrink_denominators(self):
        ids = [case['case_id'] for case in self.cohort['cases']]
        self.attempts[ids[0]]['stdout'] = c.canonical(unresolved(self.cohort['cases'][0], self.public_map))
        self.attempts[ids[1]]['stdout'] = b'{bad'
        self.attempts[ids[2]]['receipt']['returncode'] = 7
        self.attempts[ids[3]] = {'state': 'not_started', 'reason': 'owned exhausted budget'}
        result = self.score()
        self.assertEqual(result['metrics']['strict_completion']['numerator'], 2)
        self.assertEqual(result['metrics']['strict_completion']['denominator'], 6)
        self.assertEqual(result['metrics']['direction']['denominator'], 5)
        self.assertIsNone(result['cases'][0]['references'])
        self.assertEqual(result['outcomes']['not_started'], 1)
        self.assertEqual(result['next_action'], 'repair_navigation_execution_contract')

    def test_alternative_fragments_cannot_be_combined_into_a_new_correct_answer(self):
        row = self.key['cases'][self.cohort['cases'][0]['case_id']]
        other = deepcopy(row['alternatives'][0]); other['references'] = other['references'][1:]
        other['interpretations'].append('insufficient_support'); row['alternatives'].append(other)
        self.alter(0, lambda v: v['interpretations'].append('insufficient_support'))
        result = self.score()
        self.assertTrue(result['cases'][0]['references']); self.assertTrue(result['cases'][0]['interpretation'])
        self.assertFalse(result['cases'][0]['strict_completion'])

    def test_key_contradiction_and_key_cohort_drift_refused(self):
        self.key['cases']['owned_0']['alternatives'][0]['claim_labels']['basis'] = 'reported'
        with self.assertRaisesRegex(ValueError, 'contradict'): self.score()
        self.key = tiny_key(self.public_map, self.cohort); self.key['cohort_hash'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'identity'): self.score()

    def test_inline_qualification_needs_no_invented_challenge_edge(self):
        result = self.score(); row = result['cases'][4]
        self.assertTrue(row['strict_completion']); self.assertIsNone(row['direction'])


if __name__ == '__main__': unittest.main()
