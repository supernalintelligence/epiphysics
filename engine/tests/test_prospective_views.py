"""Invented inputs only; retained files exercise the actual byte-only decoder API."""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from epiphysics import prospective_views as views


def raw(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def observation(name, kind, time):
    return {'id': name, 'kind': kind, 'content_sha256': hashlib.sha256(name.encode()).hexdigest(),
            'observed_at': time, 'retained_at': time, 'time_basis': 'local_clock'}


def fact(name, subject, predicate, kind, value, refs, time='2026-11-26T09:00:00Z', supersedes=None):
    return {'id': name, 'subject': subject, 'predicate': predicate, 'object': {'type': kind, 'value': value},
            'observation_ids': refs, 'known_at': time, 'supersedes': supersedes}


def base(family, subject):
    packet = {'schema_version': 1, 'family': family, 'entities': [{'id': 'question', 'kind': 'question'},
              {'id': subject, 'kind': family}], 'observations': [observation('contract', 'question_contract', '2026-11-26T09:00:00Z')],
              'assertions': []}
    for name, kind, value in [('subject', 'entity', subject), ('knowledge_cutoff', 'string', '2026-11-26T10:05:00Z'),
                               ('forecast_deadline', 'string', '2026-11-26T10:10:00Z'),
                               ('outcome_cutoff', 'string', '2026-11-26T11:00:00Z'), ('resolution_rule', 'string', 'invented-rule-v1')]:
        packet['assertions'].append(fact('q:' + name, 'question', 'question.' + name, kind, value, ['contract']))
    return packet


def release_packet():
    p = base('software_component', 'component:demo')
    p['entities'] += [{'id': 'release:small', 'kind': 'release'}, {'id': 'release:large', 'kind': 'release'}]
    p['observations'] += [observation('sample-old', 'release_sample', '2026-11-26T09:30:00Z'),
                          observation('sample-open', 'release_sample', '2026-11-26T10:00:00Z')]
    p['assertions'].append(fact('opening', 'question', 'question.opening_observation', 'string', 'sample-open', ['contract']))
    for prefix, entity, number, sample, time, prerelease in [
        ('old', 'release:small', 91, 'sample-old', '2026-11-26T09:30:00Z', True),
        ('new', 'release:small', 91, 'sample-open', '2026-11-26T10:00:00Z', False),
        ('big', 'release:large', 9007199254740993123, 'sample-open', '2026-11-26T10:00:00Z', False),
    ]:
        for predicate, kind, value in [('id', 'integer', number), ('draft', 'boolean', False),
                                       ('prerelease', 'boolean', prerelease), ('component', 'entity', 'component:demo')]:
            p['assertions'].append(fact(prefix + ':' + predicate, entity, 'release.' + predicate, kind, value, [sample], time))
    p['assertions'].append(fact('publisher:invalid', 'release:large', 'release.published_at', 'json',
        {'raw': {'unexpected': ['yesterday?', None, 9007199254740993123]}, 'precision': None, 'parse_status': 'invalid'},
        ['sample-open'], '2026-11-26T10:00:00Z'))
    return p


def obligation_packet(maker='role:maker', beneficiary='role:recipient'):
    p = base('local_delivery_obligation', 'obligation:demo')
    p['entities'] += [{'id': maker, 'kind': 'role'}, {'id': beneficiary, 'kind': 'role'},
                      {'id': 'channel:one', 'kind': 'channel'}, {'id': 'source:one', 'kind': 'source'}]
    p['observations'] += [observation('acceptance-source', 'acceptance', '2026-11-26T09:20:00Z'),
                          observation('blob-source', 'source_blob', '2026-11-26T09:15:00Z')]
    for predicate, kind, value in [('promisor', 'entity', maker), ('beneficiary', 'entity', beneficiary),
        ('channel', 'entity', 'channel:one'), ('source', 'entity', 'source:one'),
        ('acceptance_event', 'string', 'acceptance:invented'), ('quality_rule_hash', 'string', 'b' * 64),
        ('quality_parameters', 'json', {'line_separator': 'LF', 'retain_final_empty': False})]:
        p['assertions'].append(fact('obligation:' + predicate, 'obligation:demo', 'obligation.' + predicate, kind, value,
                                    ['acceptance-source'], '2026-11-26T09:20:00Z'))
    for predicate, kind, value in [('sha256', 'string', 'a' * 64), ('path', 'string', 'docs/example.md'),
                                  ('blob_id', 'string', 'blob:invented'), ('byte_length', 'integer', 47)]:
        p['assertions'].append(fact('source:' + predicate, 'source:one', 'source.' + predicate, kind, value,
                                    ['blob-source'], '2026-11-26T09:15:00Z'))
    return p


class ViewTests(unittest.TestCase):
    def setUp(self):
        root = os.environ.get('PROSPECTIVE_VIEWS_EVIDENCE_DIR')
        self.directory = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-', dir=root))
        self.forms = [('flat', views.encode_flat, views.decode_flat_answers),
                      ('graph', views.encode_graph, views.decode_graph_answers)]

    def roundtrip(self, p, form, encoder, decoder, suffix='complete'):
        source = raw(p); (self.directory / 'snapshot.json').write_bytes(source)
        encoding = encoder(source); path = self.directory / (form + '-' + suffix + '.json')
        path.write_bytes(encoding); reread = path.read_bytes()
        self.assertEqual(hashlib.sha256(encoding).hexdigest(), hashlib.sha256(reread).hexdigest())
        result = decoder(reread, views.public_query(p['family']))
        (self.directory / (form + '-' + suffix + '-answers.json')).write_bytes(raw(result))
        return encoding, result

    def test_release_round_trip_matches_independent_values_and_support(self):
        p = release_packet()
        expected = {'subject_id': 'component:demo', 'knowledge_cutoff_utc': '2026-11-26T10:05:00Z',
                    'outcome_cutoff_utc': '2026-11-26T11:00:00Z', 'source_observation_ids': ['contract', 'sample-old', 'sample-open'],
                    'seen_id_set': [91, 9007199254740993123], 'opening_eligibility': {'91': True, '9007199254740993123': True}}
        results = []
        for form, encoder, decoder in self.forms:
            encoding, result = self.roundtrip(p, form, encoder, decoder)
            self.assertEqual(result['answers'], expected)
            self.assertEqual(result['provenance']['seen_id_set'], ['sample-old', 'sample-open'])
            self.assertEqual(result['provenance']['opening_eligibility'], ['contract', 'sample-old', 'sample-open'])
            self.assertEqual(json.loads(encoding)['input_sha256'], hashlib.sha256(raw(p)).hexdigest())
            results.append(result)
        self.assertEqual(*results)

    def test_obligation_round_trip_preserves_direction_and_provenance(self):
        maker, beneficiary = 'role:maker-' + uuid.uuid4().hex, 'role:recipient-' + uuid.uuid4().hex
        p = obligation_packet(maker, beneficiary)
        expected = {'subject_id': 'obligation:demo', 'knowledge_cutoff_utc': '2026-11-26T10:05:00Z',
                    'outcome_cutoff_utc': '2026-11-26T11:00:00Z', 'source_observation_ids': ['acceptance-source', 'blob-source', 'contract'],
                    'promisor_role_id': maker, 'beneficiary_role_id': beneficiary, 'source_sha256': 'a' * 64,
                    'quality_rule_hash': 'b' * 64, 'acceptance_event_id': 'acceptance:invented',
                    'authorized_submission_channel_id': 'channel:one'}
        for form, encoder, decoder in self.forms:
            _, result = self.roundtrip(p, form, encoder, decoder)
            self.assertEqual(result['answers'], expected)
            self.assertEqual(result['provenance']['source_sha256'], ['acceptance-source', 'blob-source'])
            self.assertEqual(result['provenance']['promisor_role_id'], ['acceptance-source'])

    def test_valid_format_fact_loss_cannot_be_repaired_from_original_input(self):
        maker = 'role:unique-' + uuid.uuid4().hex
        p = obligation_packet(maker)
        for form, encoder, decoder in self.forms:
            encoding, _ = self.roundtrip(p, form, encoder, decoder)
            damaged = json.loads(encoding); field = 'rows' if form == 'flat' else 'edges'
            damaged[field] = [a for a in damaged[field] if a['predicate'] != 'obligation.promisor']
            # Remove even the now-unrelated entity identity, so no copy of the answer survives.
            nodes = 'entities' if form == 'flat' else 'nodes'
            damaged[nodes] = [e for e in damaged[nodes] if e['id'] != maker]
            path = self.directory / (form + '-lost-fact.json'); path.write_bytes(raw(damaged))
            self.assertNotIn(maker.encode(), path.read_bytes())
            with self.assertRaisesRegex(ValueError, 'Missing fact'):
                decoder(path.read_bytes(), views.public_query(p['family']))

    def test_valid_format_provenance_loss_cannot_be_repaired(self):
        p = obligation_packet()
        for form, encoder, decoder in self.forms:
            encoding, _ = self.roundtrip(p, form, encoder, decoder)
            damaged = json.loads(encoding); field = 'rows' if form == 'flat' else 'edges'
            for a in damaged[field]:
                if a['predicate'] == 'obligation.promisor': a['observation_ids'] = []
            path = self.directory / (form + '-lost-support.json'); path.write_bytes(raw(damaged))
            with self.assertRaisesRegex(ValueError, 'provenance'):
                decoder(path.read_bytes(), views.public_query(p['family']))

    def test_graph_contains_directed_relations_not_answer_cache(self):
        graph = json.loads(views.encode_graph(raw(obligation_packet())))
        edge = next(e for e in graph['edges'] if e['predicate'] == 'obligation.promisor')
        self.assertEqual((edge['source'], edge['target'], edge['literal']), ('obligation:demo', 'role:maker', None))
        self.assertNotIn('answers', graph)
        edge['source'], edge['target'] = edge['target'], edge['source']
        with self.assertRaisesRegex(ValueError, 'direction'):
            views.decode_graph_answers(raw(graph), views.public_query('local_delivery_obligation'))

    def test_swapped_roles_are_observable_not_silently_corrected(self):
        p = obligation_packet(); rows = {a['predicate']: a for a in p['assertions']}
        rows['obligation.promisor']['object']['value'] = 'role:recipient'
        rows['obligation.beneficiary']['object']['value'] = 'role:maker'
        for form, encoder, decoder in self.forms:
            _, result = self.roundtrip(p, form, encoder, decoder)
            self.assertEqual(result['answers']['promisor_role_id'], 'role:recipient')
            self.assertEqual(result['answers']['beneficiary_role_id'], 'role:maker')

    def test_raw_optional_metadata_and_sample_history_survive_both_views(self):
        p = release_packet()
        for form, encoder, _ in self.forms:
            encoded = encoder(raw(p)); restored = views._packet(encoded, form)
            self.assertEqual({a['id']: a for a in restored['assertions']}, {a['id']: a for a in p['assertions']})
            self.assertEqual(restored['observations'], sorted(p['observations'], key=lambda x: (x['retained_at'], x['id'])))
        self.assertTrue(views.decode_flat_answers(views.encode_flat(raw(p)), views.public_query(p['family']))['answers']['opening_eligibility']['9007199254740993123'])

    def test_flat_rows_are_chronological_and_tie_sorted(self):
        p = release_packet(); p['assertions'].reverse()
        flat = json.loads(views.encode_flat(raw(p)))
        self.assertEqual([(a['known_at'], a['id']) for a in flat['rows']], sorted((a['known_at'], a['id']) for a in p['assertions']))

    def test_absent_optional_publisher_field_differs_from_explicit_null(self):
        p = release_packet(); optional = next(a for a in p['assertions'] if a['id'] == 'publisher:invalid')
        optional['object']['value']['raw'] = None
        for form, encoder, _ in self.forms:
            restored = views._packet(encoder(raw(p)), form)
            self.assertIn(optional, restored['assertions'])
            self.assertFalse(any(a['predicate'] == 'release.created_at' for a in restored['assertions']))

    def test_after_cutoff_observation_and_assertion_refuse_not_filter(self):
        for field in ('observation', 'assertion'):
            p = release_packet()
            if field == 'observation':
                p['observations'].append(observation('late', 'release_sample', '2026-11-26T10:05:00.000001Z'))
            else: p['assertions'][-1]['known_at'] = '2026-11-26T10:05:00.000001Z'
            for _, encoder, _ in self.forms:
                with self.assertRaisesRegex(ValueError, 'After-cutoff'): encoder(raw(p))

    def test_exact_cutoff_is_eligible_and_publisher_date_has_no_time_authority(self):
        p = release_packet(); p['assertions'][-1]['known_at'] = '2026-11-26T10:05:00Z'
        p['assertions'][-1]['object']['value']['raw'] = '1900-01-01'
        for form, encoder, decoder in self.forms: self.roundtrip(p, form, encoder, decoder)
        p['observations'][-1]['retained_at'] = '2026-11-26T12:00:00Z'
        for _, encoder, _ in self.forms:
            with self.assertRaises(ValueError): encoder(raw(p))

    def test_local_time_basis_and_retention_order_are_required(self):
        for edit in ('basis', 'retention', 'known'):
            p = release_packet()
            if edit == 'basis': p['observations'][-1]['time_basis'] = 'publisher_date'
            elif edit == 'retention': p['observations'][-1]['retained_at'] = '2026-11-26T09:00:00Z'
            else: p['assertions'][-1]['known_at'] = '2026-11-26T09:00:00Z'
            with self.assertRaises(ValueError): views.encode_flat(raw(p))

    def test_public_query_rejects_answer_context_and_wrong_field_grammar(self):
        p = obligation_packet()
        for _, encoder, decoder in self.forms:
            encoded = encoder(raw(p))
            for mutation in ('extra', 'wrong_fields', 'wrong_family', 'boolean_version'):
                query = views.public_query(p['family'])
                if mutation == 'extra': query['promisor_role_id'] = 'role:maker'
                elif mutation == 'wrong_fields': query['required_fields'] = []
                elif mutation == 'wrong_family': query['family'] = 'software_component'
                else: query['query_schema_version'] = True
                with self.assertRaises(ValueError): decoder(encoded, query)

    def test_conflicting_active_facts_refuse_but_explicit_revision_is_retained(self):
        p = obligation_packet(); old = next(a for a in p['assertions'] if a['predicate'] == 'obligation.promisor')
        new = deepcopy(old); new['id'] = 'promisor:revision'; new['object']['value'] = 'role:recipient'; p['assertions'].append(new)
        for _, encoder, decoder in self.forms:
            with self.assertRaisesRegex(ValueError, 'Conflicting'): decoder(encoder(raw(p)), views.public_query(p['family']))
        new['supersedes'] = old['id']
        for form, encoder, decoder in self.forms:
            encoded, result = self.roundtrip(p, form, encoder, decoder)
            self.assertEqual(result['answers']['promisor_role_id'], 'role:recipient')
            self.assertEqual(len(views._packet(encoded, form)['assertions']), len(p['assertions']))

    def test_revision_fork_cycle_and_cross_subject_refuse(self):
        for mutation in ('fork', 'cycle', 'subject'):
            p = obligation_packet(); old = next(a for a in p['assertions'] if a['predicate'] == 'obligation.promisor')
            new = deepcopy(old); new['id'] = 'new'; new['supersedes'] = old['id']; p['assertions'].append(new)
            if mutation == 'fork':
                another = deepcopy(new); another['id'] = 'fork'; p['assertions'].append(another)
            elif mutation == 'cycle': old['supersedes'] = new['id']
            else: new['supersedes'] = 'obligation:beneficiary'
            with self.assertRaises(ValueError): views.encode_flat(raw(p))

    def test_missing_release_boolean_does_not_default_to_stable(self):
        p = release_packet(); p['assertions'] = [a for a in p['assertions'] if a['id'] != 'big:prerelease']
        for _, encoder, decoder in self.forms:
            with self.assertRaisesRegex(ValueError, 'Missing fact'): decoder(encoder(raw(p)), views.public_query(p['family']))

    def test_empty_complete_opening_is_distinct_from_missing_opening(self):
        p = release_packet(); p['entities'] = [e for e in p['entities'] if e['kind'] != 'release']
        p['assertions'] = [a for a in p['assertions'] if not a['predicate'].startswith('release.')]
        for form, encoder, decoder in self.forms:
            _, result = self.roundtrip(p, form, encoder, decoder)
            self.assertEqual(result['answers']['seen_id_set'], [])
            self.assertEqual(result['answers']['opening_eligibility'], {})
        p['observations'] = [o for o in p['observations'] if o['id'] != 'sample-open']
        with self.assertRaisesRegex(ValueError, 'Missing opening'):
            views.decode_flat_answers(views.encode_flat(raw(p)), views.public_query(p['family']))

    def test_duplicate_identity_unsupported_predicate_and_invalid_types_refuse(self):
        for mutation in ('duplicate', 'predicate', 'bool_id', 'unknown_provenance', 'dangling_entity'):
            p = release_packet()
            if mutation == 'duplicate': p['entities'].append(deepcopy(p['entities'][-1]))
            elif mutation == 'predicate': p['assertions'][-1]['predicate'] = 'release.unknown'
            elif mutation == 'bool_id': next(a for a in p['assertions'] if a['id'] == 'big:id')['object']['value'] = True
            elif mutation == 'unknown_provenance': p['assertions'][-1]['observation_ids'] = ['unknown']
            else: p['entities'].pop()
            with self.assertRaises(ValueError): views.encode_graph(raw(p))

    def test_strict_utf8_json_duplicate_keys_and_nonfinite_numbers(self):
        for invalid in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'{} trailing', b'\xff', '{}'.encode('utf-16')):
            with self.assertRaises(ValueError): views.encode_flat(invalid)
        with self.assertRaises(ValueError): views.encode_flat(raw(release_packet()) + b' ' * views.INPUT_LIMIT)
        with self.assertRaises(ValueError): views.decode_graph_answers(b' ' * (views.ENCODING_LIMIT + 1), views.public_query('software_component'))

    def test_output_limit_is_enforced_without_truncation(self):
        p = release_packet()
        # Enough eligible observations to exceed the answer bound but stay below input/encoding bounds.
        p['observations'] = [p['observations'][0]] + [observation('source-' + str(i) + '-' + 'x' * 180, 'release_sample',
                                      '2026-11-26T09:30:00Z') for i in range(180)] + [p['observations'][-1]]
        p['entities'] = [e for e in p['entities'] if e['kind'] != 'release']
        p['assertions'] = [a for a in p['assertions'] if not a['predicate'].startswith('release.')]
        self.assertLess(len(raw(p)), views.INPUT_LIMIT)
        for _, encoder, decoder in self.forms:
            with self.assertRaisesRegex(ValueError, 'Encoded byte limit'):
                decoder(encoder(raw(p)), views.public_query(p['family']))

    def test_decoder_module_has_no_io_or_construction_state_channels(self):
        tree = ast.parse(Path(views.__file__).read_text())
        forbidden = {'open', 'eval', 'exec', 'compile', '__import__', 'globals', 'locals', 'getattr', 'setattr'}
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertFalse([n for n in calls if isinstance(n.func, ast.Name) and n.func.id in forbidden])
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual({n.module for n in imports if isinstance(n, ast.ImportFrom)}, {'__future__', 'store'})
        self.assertEqual({alias.name for n in imports if isinstance(n, ast.Import) for alias in n.names}, {'json', 're'})
        self.assertFalse(any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree)))
        p = obligation_packet(); encoded = views.encode_flat(raw(p)); p.clear()
        self.assertEqual(views.decode_flat_answers(encoded, views.public_query('local_delivery_obligation'))['answers']['promisor_role_id'], 'role:maker')

    def test_release_correction_support_loss_never_revives_superseded_value(self):
        p = release_packet()
        old = next(a for a in p['assertions'] if a['id'] == 'new:draft')
        corrected = deepcopy(old); corrected.update(id='draft:correction', known_at='2026-11-26T10:01:00Z', supersedes=old['id'])
        corrected['object']['value'] = True; p['assertions'].append(corrected)
        for form, encoder, decoder in self.forms:
            encoded, result = self.roundtrip(p, form, encoder, decoder)
            self.assertFalse(result['answers']['opening_eligibility']['91'])
            restored = views._packet(encoded, form)
            self.assertIn(old, restored['assertions']); self.assertIn(corrected, restored['assertions'])
            self.assertIn('sample-old', result['answers']['source_observation_ids'])
            damaged = json.loads(encoded); field = 'rows' if form == 'flat' else 'edges'
            next(a for a in damaged[field] if a['id'] == corrected['id'])['observation_ids'] = []
            path = self.directory / (form + '-lost-correction-support.json'); path.write_bytes(raw(damaged))
            with self.assertRaisesRegex(ValueError, 'exactly one sample provenance'):
                decoder(path.read_bytes(), views.public_query(p['family']))

    def test_release_revisions_cannot_cross_sample_identity(self):
        p = release_packet()
        next(a for a in p['assertions'] if a['id'] == 'new:prerelease')['supersedes'] = 'old:prerelease'
        for _, encoder, _ in self.forms:
            with self.assertRaisesRegex(ValueError, 'within its source sample'): encoder(raw(p))

    def test_graph_cannot_hide_entity_relations_inside_literals(self):
        p = obligation_packet(); encoded = views.encode_graph(raw(p)); graph = json.loads(encoded)
        for edge in graph['edges']:
            if edge['target'] is not None:
                edge['literal'] = {'type': 'entity', 'value': edge['target']}; edge['target'] = None
        self.assertFalse(any(e['target'] is not None for e in graph['edges']))
        path = self.directory / 'entity-relations-as-literals.json'; path.write_bytes(raw(graph))
        with self.assertRaisesRegex(ValueError, 'Entity graph relations require a target'):
            views.decode_graph_answers(path.read_bytes(), views.public_query(p['family']))


if __name__ == '__main__':
    unittest.main()
