"""Invented byte evidence only, independently stated answers, real disk round trips."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from epiphysics import prospective_inputs as inputs
from epiphysics import prospective_views as views


def raw(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def clock_ns(value):
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    delta = date - datetime(2026, 11, 27, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1000000000 + delta.microseconds * 1000


def receipt(identifier, kind, body, time='2026-11-27T08:00:00Z'):
    ns = clock_ns(time)
    return {'id': identifier, 'kind': kind, 'content_sha256': sha(body), 'retained_byte_length': len(body),
            'observed_byte_length': len(body), 'complete': True, 'observed_at': time, 'validated_at': time,
            'retained_at': time, 'time_basis': 'local_clock',
            'clock': {'start_utc': time, 'start_ns': ns, 'observed_ns': ns, 'validated_ns': ns,
                      'retained_ns': ns, 'start_epoch': 'invented-process-epoch', 'end_epoch': 'invented-process-epoch'}}


def release_fixture():
    question = {'schema_version': 1, 'family': 'software_component', 'question_id': 'q:invented-release',
        'subject_id': 'component:invented', 'knowledge_cutoff_utc': '2026-11-27T10:05:00Z',
        'forecast_deadline_utc': '2026-11-27T10:10:00Z', 'outcome_cutoff_utc': '2026-11-30T10:00:00Z',
        'resolution_rule_id': 'bounded-release-observation-v1', 'evidence': {'source_id': 'invented-source',
            'request_url': 'https://api.github.com/repos/modelcontextprotocol/python-sdk/releases?per_page=5',
            'opening_slot_id': 'open', 'slots': [{'id': 'prior', 'nominal_at': '2026-11-27T09:00:00Z'},
                                               {'id': 'open', 'nominal_at': '2026-11-27T10:00:00Z'}]}}
    manifest = {'raw_input_schema_version': 1,
        'declaration_sha256': 'ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65',
        'question_observation_id': 'q-source', 'observations': []}
    bodies = {'q-source': raw(question)}
    manifest['observations'].append(receipt('q-source', 'question_contract', bodies['q-source']))
    records = {'prior': [{'id': 91, 'draft': True, 'prerelease': True},
                         {'id': 19, 'draft': False, 'prerelease': False}],
               'open': [{'id': 91, 'draft': False, 'prerelease': False},
                        {'id': 9007199254740993123, 'draft': False, 'prerelease': True,
                         'tag_name': None, 'created_at': {'bad': ['date', None]},
                         'published_at': '1820-01-01T01:02:03.123456789123Z', 'ignored': 'raw-only'}]}
    for slot, time in [('prior', '2026-11-27T09:00:00Z'), ('open', '2026-11-27T10:00:00Z')]:
        identifier = 'sample-' + slot
        bodies[identifier] = raw(records[slot])
        bodies[identifier + ':headers'] = raw([['Content-Encoding', 'identity'], ['Link', '<ignored>; rel="next"']])
        r = receipt(identifier, 'release_sample', bodies[identifier], time)
        r.update(slot_id=slot, http={'request_url': question['evidence']['request_url'], 'request_method': 'GET',
            'request_headers': {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                'Accept-Encoding': 'identity', 'User-Agent': 'Epiphysics-Prospective-Integrity-Pilot-v1'},
            'status_code': 200, 'completion': 'completed', 'headers_complete': True,
            'headers_sha256': sha(bodies[identifier + ':headers']),
            'headers_observed_byte_length': len(bodies[identifier + ':headers'])})
        manifest['observations'].append(r)
    return manifest, bodies


def obligation_fixture(source=None):
    source = source if source is not None else ('A public invented document.\r\n' + 'é' * 120 + '\n').encode()
    body_hash = sha(source)
    blob = hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()
    acceptance = {'schema_version': 1, 'obligation_id': 'obligation:invented', 'due_utc': '2026-11-27T10:16:00Z',
        'acceptance_event_id': 'acceptance:explicit', 'promisor_role_id': 'role:recipient-named-but-promisor',
        'beneficiary_role_id': 'role:maker-named-but-beneficiary', 'authorized_submission_channel_id': 'channel:exclusive',
        'quality_rule_hash': 'b' * 64, 'quality_parameters': {'line_separator': 'LF', 'retain_final_empty': False},
        'source_sha256': body_hash, 'source_byte_length': len(source), 'source_path': 'docs/theory/invented.md',
        'source_blob_id': blob, 'git_object_format': 'sha1', 'source_commit_id': 'c' * 40}
    binding = {k: v for k, v in acceptance.items() if k not in ('schema_version', 'obligation_id', 'due_utc')}
    binding.update(acceptance_observation_id='acceptance-source', acceptance_sha256=sha(raw(acceptance)),
                   source_observation_id='blob-source')
    question = {'schema_version': 1, 'family': 'local_delivery_obligation', 'question_id': 'q:invented-obligation',
        'subject_id': 'obligation:invented', 'knowledge_cutoff_utc': '2026-11-27T10:05:00Z',
        'forecast_deadline_utc': '2026-11-27T10:10:00Z', 'outcome_cutoff_utc': '2026-11-27T10:16:00Z',
        'resolution_rule_id': 'first-artifact-quality-v1', 'evidence': binding}
    bodies = {'q-source': raw(question), 'acceptance-source': raw(acceptance), 'blob-source': source}
    manifest = {'raw_input_schema_version': 1,
        'declaration_sha256': 'ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65',
        'question_observation_id': 'q-source', 'observations': [receipt(identifier, kind, bodies[identifier])
            for identifier, kind in [('q-source', 'question_contract'), ('acceptance-source', 'acceptance'), ('blob-source', 'source_blob')]]}
    return manifest, bodies


def replace_body(fixture, identifier, body):
    manifest, bodies = fixture
    bodies[identifier] = body
    r = next(r for r in manifest['observations'] if r['id'] == identifier)
    r.update(content_sha256=sha(body), retained_byte_length=len(body), observed_byte_length=len(body))


def replace_question(fixture, question):
    replace_body(fixture, 'q-source', raw(question))


class InputTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-', dir=os.environ.get('PROSPECTIVE_INPUTS_EVIDENCE_DIR')))
        self.count = 0

    def normalize(self, fixture):
        self.count += 1
        directory = self.directory / str(self.count); directory.mkdir()
        manifest, bodies = fixture
        (directory / 'manifest.json').write_bytes(raw(manifest))
        for index, (identifier, body) in enumerate(bodies.items()):
            (directory / ('body-%02d.bin' % index)).write_bytes(body)
        (directory / 'body-identities.json').write_bytes(raw(list(bodies)))
        try:
            packet, diagnostics = inputs.normalize_inputs(raw(manifest), bodies)
        except ValueError as error:
            (directory / 'exception.txt').write_text(str(error))
            raise
        (directory / 'diagnostics.json').write_bytes(diagnostics)
        if packet is not None:
            (directory / 'normalized.json').write_bytes(packet)
        return packet, json.loads(diagnostics)

    def roundtrip(self, fixture, expected):
        before = deepcopy(fixture)
        packet, diagnostics = self.normalize(fixture)
        self.assertIsNotNone(packet, diagnostics)
        self.assertEqual(fixture, before)
        self.assertEqual(diagnostics['timing_assurance'], 'caller_claims_only')
        self.assertFalse(diagnostics['independent_collection_verified'])
        for name, encode, decode in [('flat', views.encode_flat, views.decode_flat_answers),
                                     ('graph', views.encode_graph, views.decode_graph_answers)]:
            encoded = encode(packet); path = self.directory / (name + '.json'); path.write_bytes(encoded)
            reread = path.read_bytes(); self.assertEqual(sha(reread), sha(encoded))
            answers = decode(reread, views.public_query(json.loads(packet)['family']))
            (self.directory / (name + '-answers.json')).write_bytes(raw(answers))
            self.assertEqual(answers['answers'], expected)
            support = answers['provenance']
            for field in ('subject_id', 'knowledge_cutoff_utc', 'outcome_cutoff_utc'):
                self.assertEqual(support[field], ['q-source'])
            self.assertEqual(support['source_observation_ids'], expected['source_observation_ids'])
            if 'seen_id_set' in expected:
                self.assertEqual(support['seen_id_set'], ['q-source', 'sample-open', 'sample-prior'])
                self.assertEqual(support['opening_eligibility'], ['q-source', 'sample-open', 'sample-prior'])
            else:
                self.assertEqual(support['source_sha256'], ['acceptance-source', 'blob-source', 'q-source'])
                for field in ('promisor_role_id', 'beneficiary_role_id', 'quality_rule_hash',
                              'acceptance_event_id', 'authorized_submission_channel_id'):
                    self.assertEqual(support[field], ['acceptance-source', 'q-source'])
        return json.loads(packet)

    def test_release_raw_saved_roundtrip_history_and_independent_answers(self):
        p = self.roundtrip(release_fixture(), {'subject_id': 'component:invented',
            'knowledge_cutoff_utc': '2026-11-27T10:05:00.000000Z', 'outcome_cutoff_utc': '2026-11-30T10:00:00.000000Z',
            'source_observation_ids': ['q-source', 'sample-open', 'sample-prior'],
            'seen_id_set': [19, 91, 9007199254740993123], 'opening_eligibility': {'91': True, '9007199254740993123': False}})
        self.assertEqual(len([a for a in p['assertions'] if a['predicate'] == 'release.id']), 4)
        self.assertTrue(all(a['supersedes'] is None for a in p['assertions']))
        optional = {a['predicate']: a['object']['value'] for a in p['assertions'] if a['predicate'] in ('release.tag_name', 'release.created_at', 'release.published_at')}
        self.assertEqual(optional['release.tag_name'], {'raw': None, 'precision': None, 'parse_status': 'unparsed'})
        self.assertEqual(optional['release.created_at'], {'raw': {'bad': ['date', None]}, 'precision': None, 'parse_status': 'invalid'})
        self.assertEqual(optional['release.published_at'], {'raw': '1820-01-01T01:02:03.123456789123Z', 'precision': 'fractional_digits:12', 'parse_status': 'valid'})
        self.assertFalse(any(a['predicate'] == 'release.ignored' for a in p['assertions']))

    def test_obligation_bytes_direction_and_independent_answers(self):
        fixture = obligation_fixture()
        p = self.roundtrip(fixture, {'subject_id': 'obligation:invented',
            'knowledge_cutoff_utc': '2026-11-27T10:05:00.000000Z', 'outcome_cutoff_utc': '2026-11-27T10:16:00.000000Z',
            'source_observation_ids': ['acceptance-source', 'blob-source', 'q-source'],
            'promisor_role_id': 'role:recipient-named-but-promisor', 'beneficiary_role_id': 'role:maker-named-but-beneficiary',
            'source_sha256': sha(fixture[1]['blob-source']), 'quality_rule_hash': 'b' * 64,
            'acceptance_event_id': 'acceptance:explicit', 'authorized_submission_channel_id': 'channel:exclusive'})
        source = {a['predicate']: a['object']['value'] for a in p['assertions'] if a['predicate'].startswith('source.')}
        self.assertEqual(source['source.byte_length'], len(fixture[1]['blob-source']))
        self.assertEqual(source['source.path'], 'docs/theory/invented.md')

    def test_record_and_receipt_order_do_not_change_packet_or_ids(self):
        fixture = release_fixture(); first, _ = self.normalize(fixture)
        fixture[0]['observations'].reverse()
        records = json.loads(fixture[1]['sample-open']); records.reverse()
        replace_body(fixture, 'sample-open', raw(records))
        second, _ = self.normalize(fixture)
        a, b = json.loads(first), json.loads(second)
        self.assertEqual(a['assertions'], b['assertions'])
        self.assertEqual(a['entities'], b['entities'])
        # Byte reordering changes source hash even though derived facts agree.
        self.assertNotEqual(a['observations'], b['observations'])

    def test_time_spellings_normalize_by_instant(self):
        fixture = release_fixture(); first, _ = self.normalize(fixture)
        r = fixture[0]['observations'][1]
        for key in ('observed_at', 'validated_at', 'retained_at'):
            r[key] = r[key].replace('Z', '.000000+00:00')
        r['clock']['start_utc'] = r['clock']['start_utc'].replace('Z', '.000000+00:00')
        second, _ = self.normalize(fixture)
        self.assertEqual(first, second)

    def test_empty_valid_opening_keeps_prior_ids(self):
        fixture = release_fixture(); replace_body(fixture, 'sample-open', b'[]')
        self.roundtrip(fixture, {'subject_id': 'component:invented',
            'knowledge_cutoff_utc': '2026-11-27T10:05:00.000000Z', 'outcome_cutoff_utc': '2026-11-30T10:00:00.000000Z',
            'source_observation_ids': ['q-source', 'sample-open', 'sample-prior'], 'seen_id_set': [19, 91], 'opening_eligibility': {}})

    def test_missing_opening_and_missing_prior_receipt_refuse(self):
        for identifier in ('sample-open', 'sample-prior'):
            with self.subTest(identifier=identifier):
                fixture = release_fixture()
                fixture[0]['observations'] = [r for r in fixture[0]['observations'] if r['id'] != identifier]
                del fixture[1][identifier]; del fixture[1][identifier + ':headers']
                packet, diagnostics = self.normalize(fixture)
                self.assertIsNone(packet); self.assertIn('missing_prior_slot_receipts', diagnostics['reasons'])

    def test_explicit_missing_prior_body_excluded_without_inventing_empty_source(self):
        fixture = release_fixture(); del fixture[1]['sample-prior']
        packet, diagnostics = self.normalize(fixture)
        self.assertIsNotNone(packet)
        self.assertNotIn('sample-prior', [o['id'] for o in json.loads(packet)['observations']])
        self.assertIn({'id': 'sample-prior', 'status': 'excluded', 'reason': 'missing_body'}, diagnostics['observations'])

    def test_invalid_opening_bodies_never_become_valid_empty_sample(self):
        cases = [b'{}', b'null', b'[', b'\xff', b'\xef\xbb\xbf[]', b'[] false', b'[NaN]',
                 b'[{"id":1,"id":2,"draft":false,"prerelease":false}]',
                 raw([{'id': 1, 'draft': False, 'prerelease': False}] * 2),
                 raw([{'id': n, 'draft': False, 'prerelease': False} for n in range(1, 7)])]
        for body in cases:
            with self.subTest(body=body[:60]):
                fixture = release_fixture(); replace_body(fixture, 'sample-open', body)
                packet, diagnostics = self.normalize(fixture)
                self.assertIsNone(packet); self.assertIn('missing_valid_opening', diagnostics['reasons'])

    def test_exact_required_primitive_types(self):
        for field, value in [('id', 0), ('id', -1), ('id', True), ('id', 1.5), ('id', '1'),
                             ('draft', 0), ('prerelease', 'false'), ('draft', None)]:
            fixture = release_fixture(); record = {'id': 1, 'draft': False, 'prerelease': False}; record[field] = value
            replace_body(fixture, 'sample-open', raw([record]))
            self.assertIsNone(self.normalize(fixture)[0])

    def test_optional_absence_null_and_malformed_values_remain_distinct(self):
        fixture = release_fixture()
        records = [{'id': 1, 'draft': False, 'prerelease': False},
                   {'id': 2, 'draft': False, 'prerelease': False, 'published_at': None},
                   {'id': 3, 'draft': False, 'prerelease': False, 'published_at': '2026-02-30T01:02:03Z'},
                   {'id': 4, 'draft': False, 'prerelease': False, 'tag_name': {'malformed': 'tag'}}]
        replace_body(fixture, 'sample-open', raw(records)); packet, _ = self.normalize(fixture)
        rows = json.loads(packet)['assertions']
        values = [a['object']['value'] for a in rows if a['predicate'] == 'release.published_at']
        self.assertCountEqual(values, [{'raw': None, 'precision': None, 'parse_status': 'unparsed'},
            {'raw': '2026-02-30T01:02:03Z', 'precision': 'second', 'parse_status': 'invalid'}])

    def test_clock_start_timeout_retention_and_hash_failures(self):
        changes = [('complete', False), ('content_sha256', '0' * 64), ('retained_byte_length', 0),
                   ('observed_byte_length', 1000001), ('retained_at', '2026-11-27T10:02:00.000001Z'),
                   ('observed_at', '2026-11-27T10:00:11Z'), ('time_basis', 'publisher_clock')]
        for key, value in changes:
            fixture = release_fixture(); r = fixture[0]['observations'][2]; r[key] = value
            self.assertIsNone(self.normalize(fixture)[0])
        for key, value in [('end_epoch', 'another'), ('retained_ns', 0), ('observed_ns', True),
                           ('start_utc', '2026-11-27T09:59:59Z')]:
            fixture = release_fixture(); fixture[0]['observations'][2]['clock'][key] = value
            self.assertIsNone(self.normalize(fixture)[0])

    def test_deadlines_inclusive_and_late_cutoff_excluded(self):
        fixture = release_fixture(); r = fixture[0]['observations'][2]
        r.update(validated_at='2026-11-27T10:02:00Z', retained_at='2026-11-27T10:02:00Z')
        r['clock'].update(validated_ns=clock_ns(r['validated_at']), retained_ns=clock_ns(r['retained_at']))
        question = json.loads(fixture[1]['q-source']); question['knowledge_cutoff_utc'] = r['retained_at']; replace_question(fixture, question)
        self.assertIsNotNone(self.normalize(fixture)[0])
        question['knowledge_cutoff_utc'] = '2026-11-27T10:01:59.999999Z'; replace_question(fixture, question)
        packet, diagnostics = self.normalize(fixture); self.assertIsNone(packet)
        self.assertIn('after_cutoff', [d['reason'] for d in diagnostics['observations']])

    def test_future_slot_not_admitted_even_before_knowledge_cutoff(self):
        fixture = release_fixture(); question = json.loads(fixture[1]['q-source'])
        question['evidence']['slots'].append({'id': 'future', 'nominal_at': '2026-11-27T10:01:00Z'})
        replace_question(fixture, question)
        r = deepcopy(fixture[0]['observations'][2]); r['id'] = 'sample-future'; r['slot_id'] = 'future'
        r.update(receipt('sample-future', 'release_sample', b'[]', '2026-11-27T10:01:00Z'))
        fixture[0]['observations'].append(r); fixture[1]['sample-future'] = b'[]'
        fixture[1]['sample-future:headers'] = fixture[1]['sample-open:headers']
        packet, diagnostics = self.normalize(fixture); self.assertIsNotNone(packet)
        self.assertIn({'id': 'sample-future', 'status': 'excluded', 'reason': 'after_opening_slot'}, diagnostics['observations'])

    def test_http_metadata_and_header_integrity(self):
        for key, value in [('status_code', 304), ('status_code', True), ('completion', 'timeout'),
                           ('headers_complete', False), ('headers_sha256', '0' * 64),
                           ('request_url', 'https://example.invalid'), ('request_method', 'POST')]:
            fixture = release_fixture(); fixture[0]['observations'][2]['http'][key] = value
            self.assertIsNone(self.normalize(fixture)[0])
        fixture = release_fixture(); headers = raw([['Content-Encoding', 'gzip']]); fixture[1]['sample-open:headers'] = headers
        fixture[0]['observations'][2]['http'].update(headers_sha256=sha(headers), headers_observed_byte_length=len(headers))
        self.assertIsNone(self.normalize(fixture)[0])

    def test_five_records_and_body_cap_are_inclusive(self):
        fixture = release_fixture(); records = [{'id': n, 'draft': False, 'prerelease': False} for n in range(1, 6)]
        body = raw(records); body += b' ' * (1048576 - len(body)); replace_body(fixture, 'sample-open', body)
        self.assertIsNotNone(self.normalize(fixture)[0])
        replace_body(fixture, 'sample-open', body + b' ')
        self.assertIsNone(self.normalize(fixture)[0])

    def test_optional_normalized_overflow_refuses_without_pruning(self):
        fixture = release_fixture(); replace_body(fixture, 'sample-open', raw([{'id': 1, 'draft': False,
            'prerelease': False, 'tag_name': 'x' * 262144}]))
        packet, diagnostics = self.normalize(fixture)
        self.assertIsNone(packet); self.assertIn('normalized_input:byte_limit_exceeded', diagnostics['reasons'])
        self.assertIn(b'x' * 262144, fixture[1]['sample-open'])

    def test_runtime_integer_and_finite_float_limits_are_unavailable_not_schema_invalid(self):
        limit = sys.get_int_max_str_digits() if hasattr(sys, 'get_int_max_str_digits') else 0
        bodies = [b'[{"id":1,"draft":false,"prerelease":false,"tag_name":1e400}]',
                  b'[{"id":1,"draft":false,"prerelease":false,"tag_name":0.123456789012345678901}]']
        if limit:
            bodies.append(b'[{"id":' + b'9' * (limit + 1) + b',"draft":false,"prerelease":false}]')
        for body in bodies:
            fixture = release_fixture(); replace_body(fixture, 'sample-prior', body)
            packet, diagnostics = self.normalize(fixture)
            self.assertIsNone(packet)
            self.assertTrue(any(reason.startswith('input_unavailable:runtime_') for reason in diagnostics['reasons']))
            self.assertNotIn('invalid_json', raw(diagnostics).decode())
        if limit:
            self.assertEqual(sys.get_int_max_str_digits(), limit)

    def test_runtime_integer_limit_boundary_remains_exact_in_both_saved_views(self):
        limit = sys.get_int_max_str_digits() if hasattr(sys, 'get_int_max_str_digits') else 0
        if not limit:
            limit = 4300
        fixture = release_fixture(); number = int('9' * limit)
        replace_body(fixture, 'sample-open', b'[{"id":' + b'9' * limit + b',"draft":false,"prerelease":false}]')
        self.roundtrip(fixture, {'subject_id': 'component:invented',
            'knowledge_cutoff_utc': '2026-11-27T10:05:00.000000Z', 'outcome_cutoff_utc': '2026-11-30T10:00:00.000000Z',
            'source_observation_ids': ['q-source', 'sample-open', 'sample-prior'],
            'seen_id_set': [19, 91, number], 'opening_eligibility': {'9' * limit: True}})

    def test_header_cap_and_link_flag_are_bounded_not_pagination(self):
        fixture = release_fixture(); _, diagnostics = self.normalize(fixture)
        opening = next(o for o in diagnostics['observations'] if o['id'] == 'sample-open')
        self.assertEqual(opening['link_next'], 'present'); self.assertEqual(opening['excluded_field_count'], 1)
        for value, expected in [('malformed Link', 'unparseable'), ('<ignored>; rel="prev"', 'absent')]:
            headers = raw([['Link', value]])
            fixture[1]['sample-open:headers'] = headers
            fixture[0]['observations'][2]['http'].update(headers_sha256=sha(headers), headers_observed_byte_length=len(headers))
            _, diagnostics = self.normalize(fixture)
            self.assertEqual(next(o for o in diagnostics['observations'] if o['id'] == 'sample-open')['link_next'], expected)
        headers = b'[]' + b' ' * (16384 - 2)
        fixture[1]['sample-open:headers'] = headers
        fixture[0]['observations'][2]['http'].update(headers_sha256=sha(headers), headers_observed_byte_length=len(headers))
        self.assertIsNotNone(self.normalize(fixture)[0])
        headers += b' '; fixture[1]['sample-open:headers'] = headers
        fixture[0]['observations'][2]['http'].update(headers_sha256=sha(headers), headers_observed_byte_length=len(headers))
        self.assertIsNone(self.normalize(fixture)[0])

    def test_duplicate_slot_or_evidence_identity_refuses(self):
        fixture = release_fixture(); fixture[0]['observations'].append(deepcopy(fixture[0]['observations'][2]))
        with self.assertRaisesRegex(ValueError, 'duplicate_observation_id'):
            self.normalize(fixture)
        fixture = release_fixture(); fixture[0]['observations'][1]['slot_id'] = 'open'
        with self.assertRaisesRegex(ValueError, 'unknown_or_duplicate_slot'):
            self.normalize(fixture)

    def test_link_rel_is_a_parameter_not_text_inside_a_quoted_title(self):
        cases = [('<https://invented.invalid/p>; title="see; rel=next here"; rel=prev', 'absent'),
                 ('<https://invented.invalid/p>; title="see; rel=prev here"; rel="next prev"', 'present'),
                 ('<https://invented.invalid/p>; rel=""; title="rel=next"', 'absent')]
        for value, expected in cases:
            fixture = release_fixture(); headers = raw([['Link', value]])
            fixture[1]['sample-open:headers'] = headers
            fixture[0]['observations'][2]['http'].update(headers_sha256=sha(headers), headers_observed_byte_length=len(headers))
            packet, diagnostics = self.normalize(fixture)
            self.assertIsNotNone(packet)
            self.assertEqual(next(o for o in diagnostics['observations'] if o['id'] == 'sample-open')['link_next'], expected)

    def test_publisher_non_ascii_digits_remain_raw_invalid_optional_metadata(self):
        fixture = release_fixture(); value = '2026-11-26T12:00:00.١٢Z'
        replace_body(fixture, 'sample-open', raw([{'id': 1, 'draft': False, 'prerelease': False, 'published_at': value}]))
        packet, diagnostics = self.normalize(fixture); self.assertIsNotNone(packet)
        for name, encode in [('flat', views.encode_flat), ('graph', views.encode_graph)]:
            path = self.directory / (name + '-unicode-fraction.json'); path.write_bytes(encode(packet))
            reconstructed = views._packet(path.read_bytes(), name)
            metadata = next(a['object']['value'] for a in reconstructed['assertions'] if a['predicate'] == 'release.published_at')
            self.assertEqual(metadata, {'raw': value, 'precision': None, 'parse_status': 'invalid'})

    def test_maximum_utc_year_windows_use_elapsed_duration(self):
        fixture = release_fixture(); boundary = '9999-12-31T23:59:59Z'
        question = json.loads(fixture[1]['q-source'])
        for key in ('knowledge_cutoff_utc', 'forecast_deadline_utc', 'outcome_cutoff_utc'):
            question[key] = boundary
        question['evidence']['slots'][1]['nominal_at'] = boundary; replace_question(fixture, question)
        r = fixture[0]['observations'][2]
        for key in ('observed_at', 'validated_at', 'retained_at'):
            r[key] = boundary
        r['clock'].update(start_utc=boundary, start_ns=0, observed_ns=0, validated_ns=0, retained_ns=0)
        self.roundtrip(fixture, {'subject_id': 'component:invented',
            'knowledge_cutoff_utc': '9999-12-31T23:59:59.000000Z', 'outcome_cutoff_utc': '9999-12-31T23:59:59.000000Z',
            'source_observation_ids': ['q-source', 'sample-open', 'sample-prior'],
            'seen_id_set': [19, 91, 9007199254740993123], 'opening_eligibility': {'91': True, '9007199254740993123': False}})

    def test_obligation_tamper_hash_blob_roles_channel_and_quality_bindings(self):
        for field, value in [('promisor_role_id', 'role:changed'), ('beneficiary_role_id', 'role:changed'),
            ('authorized_submission_channel_id', 'channel:changed'), ('quality_rule_hash', 'a' * 64),
            ('quality_parameters', {'line_separator': 'CRLF'}), ('source_sha256', 'a' * 64),
            ('source_path', 'docs/theory/other.md'), ('source_blob_id', 'a' * 40), ('source_byte_length', 256)]:
            fixture = obligation_fixture(); question = json.loads(fixture[1]['q-source']); question['evidence'][field] = value
            replace_question(fixture, question); self.assertIsNone(self.normalize(fixture)[0])
        fixture = obligation_fixture(); replace_body(fixture, 'blob-source', b'x' * len(fixture[1]['blob-source']))
        self.assertIsNone(self.normalize(fixture)[0])

    def test_obligation_source_size_line_unicode_and_empty_boundaries(self):
        for source in [b'x' * 256, b'x' * 8192, b'a\n' * 128, b'a\r\n' * 128]:
            self.assertIsNotNone(self.normalize(obligation_fixture(source))[0])
        for source in [b'', b'x' * 255, b'x' * 8193, b'a\n' * 129, b'x' * 255 + b'\xff', b'x' * 255 + b'\0']:
            self.assertIsNone(self.normalize(obligation_fixture(source))[0])

    def test_obligation_missing_late_and_unbound_outcomes_refuse(self):
        for identifier in ('acceptance-source', 'blob-source'):
            fixture = obligation_fixture(); del fixture[1][identifier]
            self.assertIsNone(self.normalize(fixture)[0])
            fixture = obligation_fixture(); r = next(r for r in fixture[0]['observations'] if r['id'] == identifier)
            r.update(receipt(identifier, r['kind'], fixture[1][identifier], '2026-11-27T10:05:00.000001Z'))
            self.assertIsNone(self.normalize(fixture)[0])
        fixture = obligation_fixture(); fixture[1]['delivery-result'] = b'{"quality":"pass"}'
        with self.assertRaisesRegex(ValueError, 'undeclared_body'):
            self.normalize(fixture)

    def test_supplied_answer_and_valid_labels_do_not_bypass_bytes(self):
        fixture = release_fixture(); fixture[0]['answers'] = {'seen_id_set': []}
        with self.assertRaisesRegex(ValueError, 'manifest_fields'):
            self.normalize(fixture)
        fixture = release_fixture(); fixture[0]['observations'][2]['valid'] = True
        with self.assertRaisesRegex(ValueError, 'receipt_fields'):
            self.normalize(fixture)

    def test_source_has_no_research_io_or_execution_paths(self):
        tree = ast.parse(Path(inputs.__file__).read_text())
        forbidden = {'open', 'read_bytes', 'read_text', 'write_bytes', 'write_text', 'Ledger', 'eval', 'exec', 'run', 'Popen', 'urlopen'}
        calls = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr
                 for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
        self.assertFalse(calls & forbidden)


if __name__ == '__main__':
    unittest.main()
