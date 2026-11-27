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
from epiphysics import prospective_inputs as inputs
from epiphysics import prospective_oracle as oracle
from epiphysics import prospective_query_check as checker


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
            self.assertEqual(result['provenance']['seen_id_set'], ['contract', 'sample-old', 'sample-open'])
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
            self.assertEqual(result['provenance']['source_sha256'], ['acceptance-source', 'blob-source', 'contract'])
            self.assertEqual(result['provenance']['promisor_role_id'], ['acceptance-source', 'contract'])

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


def support_receipt(identifier, kind, body, time):
    """New raw claims, independent of the candidate and the old baseline fixtures."""
    return {'id': identifier, 'kind': kind, 'content_sha256': hashlib.sha256(body).hexdigest(),
            'retained_byte_length': len(body), 'observed_byte_length': len(body), 'complete': True,
            'observed_at': time, 'validated_at': time, 'retained_at': time, 'time_basis': 'local_clock',
            'clock': {'start_utc': time, 'start_ns': 100, 'observed_ns': 100, 'validated_ns': 100,
                      'retained_ns': 100, 'start_epoch': 'cedar-clock', 'end_epoch': 'cedar-clock'}}


def support_fixture(name):
    """C18 inputs and hand-written expected values/support, frozen before execution."""
    declaration = 'ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65'
    question = {'schema_version': 1, 'knowledge_cutoff_utc': '2026-12-03T12:04:00Z',
                'forecast_deadline_utc': '2026-12-03T12:09:00Z', 'resolution_rule_id': 'cedar-rule-v1'}
    if name.startswith('release-'):
        question.update(family='software_component', question_id='question:cedar-releases',
                        subject_id='component:cedar', outcome_cutoff_utc='2026-12-06T12:00:00Z',
                        evidence={'source_id': 'cedar-release-source',
                            'request_url': 'https://api.github.com/repos/modelcontextprotocol/python-sdk/releases?per_page=5',
                            'opening_slot_id': 'cedar-noon', 'slots': [
                                {'id': 'cedar-ten', 'nominal_at': '2026-12-03T10:00:00Z'},
                                {'id': 'cedar-eleven', 'nominal_at': '2026-12-03T11:00:00Z'},
                                {'id': 'cedar-noon', 'nominal_at': '2026-12-03T12:00:00Z'}]})
        bodies = {'q-cedar': raw(question)}
        receipts = [support_receipt('q-cedar', 'question_contract', bodies['q-cedar'], '2026-12-03T09:00:00Z')]
        samples = [
            ('cedar-ten', 'r-history', '2026-12-03T10:00:00Z', [
                {'id': 307, 'draft': True, 'prerelease': False},
                {'id': 118, 'draft': False, 'prerelease': True}]),
            ('cedar-eleven', 'r-empty', '2026-12-03T11:00:00Z', []),
            ('cedar-noon', 'r-opening', '2026-12-03T12:00:00Z', [
                {'id': 307, 'draft': False, 'prerelease': False},
                {'id': 9007199254741777, 'draft': False, 'prerelease': True,
                 'tag_name': None, 'created_at': {'broken': ['tomorrow', 7]},
                 'published_at': '1780-12-01T01:02:03.123456789Z', 'unselected': 'retained raw'}])]
        for slot, identifier, time, records in samples:
            if name == 'release-all-empty' or (name == 'release-empty-opening' and identifier == 'r-opening'):
                records = []
            bodies[identifier] = raw(records)
            bodies[identifier + ':headers'] = raw([['Content-Encoding', 'identity'], ['Link', '<cedar>; rel="next"']])
            receipt = support_receipt(identifier, 'release_sample', bodies[identifier], time)
            receipt.update(slot_id=slot, http={'request_url': question['evidence']['request_url'],
                'request_method': 'GET', 'request_headers': {'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28', 'Accept-Encoding': 'identity',
                    'User-Agent': 'Epiphysics-Prospective-Integrity-Pilot-v1'}, 'status_code': 200,
                'completion': 'completed', 'headers_complete': True,
                'headers_sha256': hashlib.sha256(bodies[identifier + ':headers']).hexdigest(),
                'headers_observed_byte_length': len(bodies[identifier + ':headers'])})
            receipts.append(receipt)
        answers = {'subject_id': 'component:cedar', 'knowledge_cutoff_utc': '2026-12-03T12:04:00.000000Z',
            'outcome_cutoff_utc': '2026-12-06T12:00:00.000000Z',
            'source_observation_ids': ['q-cedar', 'r-empty', 'r-history', 'r-opening'],
            'seen_id_set': [118, 307, 9007199254741777],
            'opening_eligibility': {'307': True, '9007199254741777': False}}
        if name == 'release-empty-opening':
            answers.update(seen_id_set=[118, 307], opening_eligibility={})
        elif name == 'release-all-empty':
            answers.update(seen_id_set=[], opening_eligibility={})
        else:
            assert name == 'release-history'
        support = {'subject_id': ['q-cedar'], 'knowledge_cutoff_utc': ['q-cedar'],
            'outcome_cutoff_utc': ['q-cedar'],
            'source_observation_ids': ['q-cedar', 'r-empty', 'r-history', 'r-opening'],
            'seen_id_set': ['q-cedar', 'r-empty', 'r-history', 'r-opening'],
            'opening_eligibility': ['q-cedar', 'r-opening']}
    else:
        assert name == 'obligation'
        source = ('C18 invented bounded source — cedar.\r\n' +
                  'A measured line with no delivery claim.\n' * 8 + 'Final receipt text.\n').encode()
        acceptance = {'schema_version': 1, 'obligation_id': 'obligation:cedar', 'due_utc': '2026-12-03T12:17:00Z',
            'acceptance_event_id': 'acceptance:cedar-signed', 'promisor_role_id': 'role:cedar-recipient-name',
            'beneficiary_role_id': 'role:cedar-maker-name', 'authorized_submission_channel_id': 'channel:cedar-drop',
            'quality_rule_hash': 'd' * 64, 'quality_parameters': {'line_separator': 'LF', 'retain_final_empty': True},
            'source_sha256': 'b5e7edbcb44b6fe02f901a02ef3f9aa13d9acb4e2fac428598f56d7130459ec7',
            'source_byte_length': 380, 'source_path': 'docs/research/cedar-invented.md',
            'source_blob_id': '44ee50d10df7d1becd270a0b27f1359a6406476f',
            'git_object_format': 'sha1', 'source_commit_id': 'e' * 40}
        evidence = {k: v for k, v in acceptance.items() if k not in ('schema_version', 'obligation_id', 'due_utc')}
        evidence.update(acceptance_observation_id='a-cedar', source_observation_id='s-cedar',
                        acceptance_sha256=hashlib.sha256(raw(acceptance)).hexdigest())
        question.update(family='local_delivery_obligation', question_id='question:cedar-obligation',
                        subject_id='obligation:cedar', outcome_cutoff_utc='2026-12-03T12:17:00Z', evidence=evidence)
        bodies = {'q-cedar': raw(question), 'a-cedar': raw(acceptance), 's-cedar': source}
        receipts = [support_receipt(identifier, kind, bodies[identifier], '2026-12-03T09:00:00Z')
                    for identifier, kind in [('q-cedar', 'question_contract'), ('a-cedar', 'acceptance'),
                                             ('s-cedar', 'source_blob')]]
        answers = {'subject_id': 'obligation:cedar', 'knowledge_cutoff_utc': '2026-12-03T12:04:00.000000Z',
            'outcome_cutoff_utc': '2026-12-03T12:17:00.000000Z',
            'source_observation_ids': ['a-cedar', 'q-cedar', 's-cedar'],
            'promisor_role_id': 'role:cedar-recipient-name', 'beneficiary_role_id': 'role:cedar-maker-name',
            'source_sha256': 'b5e7edbcb44b6fe02f901a02ef3f9aa13d9acb4e2fac428598f56d7130459ec7',
            'quality_rule_hash': 'd' * 64, 'acceptance_event_id': 'acceptance:cedar-signed',
            'authorized_submission_channel_id': 'channel:cedar-drop'}
        support = {'subject_id': ['q-cedar'], 'knowledge_cutoff_utc': ['q-cedar'],
            'outcome_cutoff_utc': ['q-cedar'], 'source_observation_ids': ['a-cedar', 'q-cedar', 's-cedar'],
            'promisor_role_id': ['a-cedar', 'q-cedar'], 'beneficiary_role_id': ['a-cedar', 'q-cedar'],
            'source_sha256': ['a-cedar', 'q-cedar', 's-cedar'], 'quality_rule_hash': ['a-cedar', 'q-cedar'],
            'acceptance_event_id': ['a-cedar', 'q-cedar'], 'authorized_submission_channel_id': ['a-cedar', 'q-cedar']}
    manifest = {'raw_input_schema_version': 1, 'declaration_sha256': declaration,
                'question_observation_id': 'q-cedar', 'observations': receipts}
    return manifest, bodies, {'answers': answers, 'required_support': support}


class SupportDependencyTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-',
                                             dir=os.environ.get('PROSPECTIVE_SUPPORT_EVIDENCE_DIR')))
        self.forms = [('flat', views.encode_flat, views.decode_flat_answers),
                      ('graph', views.encode_graph, views.decode_graph_answers)]

    def saved(self, filename, content):
        path = self.directory / filename
        with path.open('xb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        reread = path.read_bytes()
        self.assertEqual(hashlib.sha256(reread).hexdigest(), hashlib.sha256(content).hexdigest())
        self.assertEqual(reread, content)
        return reread

    def normalized(self, name):
        manifest, bodies, literal = support_fixture(name)
        manifest_bytes = self.saved(name + '-manifest.json', raw(manifest))
        literal_bytes = self.saved(name + '-expected.json', raw(literal))
        for index, body in enumerate(bodies.values()):
            self.saved(name + '-body-%02d.bin' % index, body)
        self.saved(name + '-body-identities.json', raw(list(bodies)))
        frozen = os.environ.get('PROSPECTIVE_SUPPORT_EXPECTED_DIR')
        if frozen:
            directory = Path(frozen) / name
            self.assertEqual(manifest_bytes, (directory / 'manifest.json').read_bytes())
            self.assertEqual(literal_bytes, (directory / 'expected.json').read_bytes())
            for index, body in enumerate(bodies.values()):
                self.assertEqual(body, (directory / ('body-%02d.bin' % index)).read_bytes())
        # This reference sees raw bytes only; no expectation enters normalization or decoding.
        reference = self.saved(name + '-oracle.json', oracle.expected_queries_from_raw_sources(manifest_bytes, bodies))
        expected = json.loads(literal_bytes)
        envelope = json.loads(reference)
        self.assertEqual(envelope['answers'], expected['answers'])
        self.assertEqual(envelope['required_support'], expected['required_support'])
        normalized, diagnostics = inputs.normalize_inputs(manifest_bytes, bodies)
        self.saved(name + '-diagnostics.json', diagnostics)
        self.assertIsNotNone(normalized, diagnostics)
        return self.saved(name + '-normalized.json', normalized), reference, expected

    def test_new_raw_cases_match_frozen_values_and_full_support(self):
        for name in ('release-history', 'release-empty-opening', 'release-all-empty', 'obligation'):
            with self.subTest(case=name):
                packet, reference, expected = self.normalized(name)
                family = 'local_delivery_obligation' if name == 'obligation' else 'software_component'
                for form, encoder, decoder in self.forms:
                    persisted = self.saved(name + '-' + form + '.json', encoder(packet))
                    response = decoder(persisted, views.public_query(family))
                    response_bytes = self.saved(name + '-' + form + '-answers.json', raw(response))
                    self.assertEqual(response['answers'], expected['answers'])
                    result = checker.check_query_content(reference, response_bytes, family)
                    self.saved(name + '-' + form + '-check.json', raw(result))
                    self.assertTrue(result['content_complete'], result)
                    self.assertEqual(result['interface_runtime_assurance'], 'unverified')
                    for field, required in expected['required_support'].items():
                        self.assertLessEqual(set(required), set(response['provenance'][field]))

    def test_question_fact_support_and_receipt_loss_refuse_saved_decoding(self):
        for name in ('release-history', 'obligation'):
            packet, _, _ = self.normalized(name)
            family = json.loads(packet)['family']
            for form, encoder, decoder in self.forms:
                encoded = json.loads(encoder(packet)); rows = 'rows' if form == 'flat' else 'edges'
                for damage in ('fact', 'support', 'receipt', 'unknown-reference'):
                    damaged = deepcopy(encoded)
                    if damage == 'fact':
                        damaged[rows] = [a for a in damaged[rows] if a['predicate'] != 'question.subject']
                    elif damage == 'receipt':
                        damaged['observations'] = [o for o in damaged['observations'] if o['id'] != 'q-cedar']
                    else:
                        binding = next(a for a in damaged[rows] if a['predicate'] == 'question.subject')
                        binding['observation_ids'] = [] if damage == 'support' else ['q-not-encoded']
                    persisted = self.saved(name + '-' + form + '-' + damage + '.json', raw(damaged))
                    with self.assertRaises(ValueError) as caught:
                        decoder(persisted, views.public_query(family))
                    self.saved(name + '-' + form + '-' + damage + '-refusal.txt', str(caught.exception).encode())

    def test_unbound_question_label_cannot_satisfy_fixed_checker(self):
        for name in ('release-history', 'obligation'):
            packet, reference, _ = self.normalized(name)
            family = json.loads(packet)['family']
            substitute = 'r-history' if name == 'release-history' else 'a-cedar'
            derived = ('seen_id_set',) if name == 'release-history' else (
                'promisor_role_id', 'beneficiary_role_id', 'quality_rule_hash', 'acceptance_event_id',
                'authorized_submission_channel_id', 'source_sha256')
            for form, encoder, decoder in self.forms:
                damaged = json.loads(encoder(packet)); rows = 'rows' if form == 'flat' else 'edges'
                binding = next(a for a in damaged[rows] if a['predicate'] == 'question.subject')
                binding['observation_ids'] = [substitute]
                binding['known_at'] = '2026-12-03T12:01:00Z'
                persisted = self.saved(name + '-' + form + '-unbound.json', raw(damaged))
                response = decoder(persisted, views.public_query(family))
                response_bytes = self.saved(name + '-' + form + '-unbound-answers.json', raw(response))
                self.assertIn('q-cedar', response['answers']['source_observation_ids'])
                for field in derived:
                    self.assertNotIn('q-cedar', response['provenance'][field])
                result = checker.check_query_content(reference, response_bytes, family)
                self.saved(name + '-' + form + '-unbound-check.json', raw(result))
                self.assertFalse(result['content_complete'])

    def test_active_question_revision_and_source_path_have_specific_support(self):
        packet, _, expected = self.normalized('obligation')
        p = json.loads(packet)
        p['observations'] += [observation(identifier, kind, '2026-12-03T10:00:00Z') for identifier, kind in [
            ('q-active', 'question_contract'), ('a-path', 'acceptance'), ('s-active', 'source_blob'),
            ('s-unrelated', 'source_blob')]]
        p['entities'].append({'id': 'source:revision', 'kind': 'source'})
        binding = next(a for a in p['assertions'] if a['predicate'] == 'question.subject')
        revised = deepcopy(binding)
        revised.update(id='binding:revision', observation_ids=['q-active'], known_at='2026-12-03T10:00:00Z',
                       supersedes=binding['id'])
        p['assertions'].append(revised)
        source = next(a for a in p['assertions'] if a['predicate'] == 'obligation.source')
        replacement = deepcopy(source)
        replacement.update(id='source-path:revision', observation_ids=['a-path'], known_at='2026-12-03T10:00:00Z',
                           supersedes=source['id'], object={'type': 'entity', 'value': 'source:revision'})
        p['assertions'] += [replacement, fact('source-hash:revision', 'source:revision', 'source.sha256',
            'string', 'f' * 64, ['s-active'], '2026-12-03T10:00:00Z')]
        for form, encoder, decoder in self.forms:
            persisted = self.saved(form + '-revised.json', encoder(raw(p)))
            response = decoder(persisted, views.public_query('local_delivery_obligation'))
            self.saved(form + '-revised-answers.json', raw(response))
            for field in ('promisor_role_id', 'beneficiary_role_id', 'quality_rule_hash',
                          'acceptance_event_id', 'authorized_submission_channel_id'):
                self.assertEqual(response['answers'][field], expected['answers'][field])
                self.assertEqual(response['provenance'][field], ['a-cedar', 'q-active'])
            self.assertEqual(response['answers']['source_sha256'], 'f' * 64)
            self.assertEqual(response['provenance']['source_sha256'], ['a-path', 'q-active', 's-active'])
            self.assertEqual(response['provenance']['subject_id'], ['q-active'])
            restored = views._packet(persisted, form)
            self.assertEqual(restored['assertions'], sorted(p['assertions'], key=lambda a: (a['known_at'], a['id'])))
            for identifier in ('binding:revision', 'source-path:revision', 'source-hash:revision'):
                damaged = json.loads(persisted); rows = 'rows' if form == 'flat' else 'edges'
                next(a for a in damaged[rows] if a['id'] == identifier)['observation_ids'] = []
                lost = self.saved(form + '-' + identifier.replace(':', '-') + '-lost.json', raw(damaged))
                with self.assertRaisesRegex(ValueError, 'provenance') as caught:
                    decoder(lost, views.public_query('local_delivery_obligation'))
                self.saved(form + '-' + identifier.replace(':', '-') + '-refusal.txt', str(caught.exception).encode())

    def test_release_binding_revision_keeps_empty_samples_without_unrelated_support(self):
        packet, _, expected = self.normalized('release-history')
        p = json.loads(packet)
        p['observations'] += [observation('q-active', 'question_contract', '2026-12-03T10:00:00Z'),
                              observation('s-unrelated', 'source_blob', '2026-12-03T10:00:00Z')]
        old = next(a for a in p['assertions'] if a['predicate'] == 'question.subject')
        revised = deepcopy(old)
        revised.update(id='release-binding:revision', observation_ids=['q-active'],
                       known_at='2026-12-03T10:00:00Z', supersedes=old['id'])
        p['assertions'].append(revised)
        for form, encoder, decoder in self.forms:
            persisted = self.saved(form + '-binding-revision.json', encoder(raw(p)))
            response = decoder(persisted, views.public_query('software_component'))
            self.saved(form + '-binding-revision-answers.json', raw(response))
            self.assertEqual(response['answers']['seen_id_set'], expected['answers']['seen_id_set'])
            self.assertEqual(response['answers']['opening_eligibility'], expected['answers']['opening_eligibility'])
            self.assertEqual(response['provenance']['seen_id_set'], ['q-active', 'r-empty', 'r-history', 'r-opening'])
            self.assertEqual(response['provenance']['opening_eligibility'], ['q-active', 'q-cedar', 'r-history', 'r-opening'])
            self.assertIn('s-unrelated', response['answers']['source_observation_ids'])
            restored = views._packet(persisted, form)
            self.assertEqual({a['id']: a for a in restored['assertions']}, {a['id']: a for a in p['assertions']})


if __name__ == '__main__':
    unittest.main()
