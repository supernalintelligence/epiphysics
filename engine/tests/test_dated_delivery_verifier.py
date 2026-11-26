"""Owned literal-byte fixtures only; no actual source selection or delivery."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from epiphysics import dated_delivery_verifier as verifier


def fixture(source=None, specifications=None, extras=()):
    if source is None:
        source = b'# Example\r\n[x](../target.md#not-a-heading)\n[y](missing.md)\n'
        specifications = [('[x](../target.md#not-a-heading)', '../target.md#not-a-heading', 'docs/target.md', 'regular_file', 'not-a-heading'),
                          ('[y](missing.md)', 'missing.md', 'docs/theory/missing.md', 'missing', None)]
    source_hash = hashlib.sha256(source).hexdigest()
    blob = hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()
    entries = [{'path': 'docs', 'mode': '040000', 'object_id': '1' * 40},
               {'path': 'docs/target.md', 'mode': '100644', 'object_id': '2' * 40},
               {'path': 'docs/theory', 'mode': '040000', 'object_id': '3' * 40},
               {'path': 'docs/theory/example.md', 'mode': '100644', 'object_id': blob}, *extras]
    manifest = {'schema_version': 1, 'source_commit': 'a' * 40, 'entries': sorted(entries, key=lambda row: row['path'])}
    registration = {'schema_version': 1, 'task_id': 'owned-task', 'registration_id': 'owned-registration',
                    'protocol_sha256': 'b' * 64, 'criteria_sha256': 'c' * 64,
                    'source_commit': 'a' * 40, 'source_path': 'docs/theory/example.md',
                    'source_sha256': source_hash, 'tree_manifest_sha256': hashlib.sha256(verifier.canonical(manifest)).hexdigest()}
    links, cursor = [], 0
    for literal, destination, target, status, fragment in specifications or []:
        literal = literal.encode('utf-8')
        start = source.index(literal, cursor)
        end = start + len(literal)
        links.append({'token_id': f'{source_hash}:{start}:{end}', 'start': start, 'end': end,
                      'destination': destination, 'target': target, 'target_status': status, 'fragment': fragment})
        cursor = end
    inventory = {key: registration[key] for key in verifier.BINDINGS[:-1]}
    inventory.update(links=links, unsupported=[], summary={'eligible': len(links), 'unsupported': 0,
        'target_status_counts': {status: sum(row['target_status'] == status for row in links) for status in verifier.STATUSES}})
    return registration, source, manifest, inventory


def expanded_expected(report, source, source_path='docs/theory/example.md'):
    """Decode the declared raw-result layout for owned format controls only."""
    by_span = {(row['start'], row['end']): row for row in verifier.inspect_source(source)['expected_tokens']}
    if hashlib.sha256(source_path.encode()).hexdigest() != report['source_path_sha256']:
        raise ValueError('Retained source path differs from report binding')
    directory = source_path.split('/')[:-1]
    rows = []
    for start, end, shared, suffix, status in report['expected_tokens']:
        target = None if shared is None else '/'.join(directory[:shared] + ([suffix] if suffix else []))
        rows.append({**by_span[start, end], 'target': target, 'target_status': status})
    return rows


class DatedDeliveryVerifierTests(unittest.TestCase):
    def check(self, values, raw=None):
        registration, source, manifest, inventory = values
        return verifier.verify_inventory(registration, source, manifest, verifier.canonical(inventory) if raw is None else raw)

    def test_literal_golden_inventory_and_missing_target_are_correct(self):
        values = fixture()
        report = self.check(values)
        self.assertEqual('pass', report['verdict'])
        self.assertTrue(all(report['criteria'].values()))
        self.assertEqual(list(verifier.RESULT_TOKEN_FIELDS), report['expected_token_fields'])
        self.assertEqual(values[3]['links'], expanded_expected(report, values[1]))
        self.assertEqual(11, report['expected_tokens'][0][0])
        self.assertEqual('not-a-heading', expanded_expected(report, values[1])[0]['fragment'])
        self.assertIsNone(report['limits']['fragment_validity'])
        self.assertEqual(report, self.check(values))
        self.assertLessEqual(len(verifier.canonical(report)), 1048576)

    def test_original_unicode_crlf_offsets_and_empty_fragment(self):
        raw = 'é🙂\r\n[é](../café.md#été)\r\n[x](a.md#)'.encode()
        tokens = verifier.inspect_source(raw)['expected_tokens']
        self.assertEqual(8, tokens[0]['start'])
        self.assertEqual(raw[8:tokens[0]['end']], '[é](../café.md#été)'.encode())
        self.assertEqual('été', tokens[0]['fragment'])
        self.assertEqual('', tokens[1]['fragment'])
        self.assertEqual('../café.md#été', tokens[0]['destination'])

    def test_exclusion_priority_and_nonoverlapping_candidate_spans(self):
        cases = [
            ('![x](a.md)', 'image'), ('[x][ref]', 'reference_style'), ('[ref]', 'reference_style'),
            ('[a[b]](a.md)', 'nested_syntax'), ('[x](a(b).md)', 'nested_syntax'),
            ('\\[x](a.md)', 'escaped_syntax'), ('[x](a\\).md)', 'escaped_syntax'),
            ('[x](${path}.md)', 'template_destination'), ('[x](https://a.md)', 'url_destination'),
            ('[x](//a.md)', 'url_destination'), ('[x](/a.md)', 'absolute_destination'),
            ('[x](a%20b.md)', 'unsupported_destination'), ('[x](a.md?q)', 'unsupported_destination'),
            ('[x](a.MD)', 'unsupported_destination'), ('[x](a b.md)', 'unsupported_destination'),
            ('[x](a.md', 'unterminated_syntax')]
        for raw, reason in cases:
            with self.subTest(raw=raw):
                encoded = raw.encode()
                scan = verifier.inspect_source(encoded)
                self.assertEqual([], scan['expected_tokens'])
                self.assertEqual(1, len(scan['unsupported_tokens']))
                row = scan['unsupported_tokens'][0]
                self.assertEqual(reason, row['reason'])
                self.assertEqual(len(encoded), row['end'])
                self.assertEqual(1 if raw.startswith('\\') else 0, row['start'])
        scan = verifier.inspect_source(b'[a[b](evil.md)](outer.md) [ok](ok.md)')
        self.assertEqual(1, len(scan['unsupported_tokens']))
        self.assertEqual(['ok.md'], [row['destination'] for row in scan['expected_tokens']])

    def test_code_regions_crlf_longer_fence_inline_and_unclosed_fence(self):
        raw = b'  ~~~lang\r\n[a](a.md)\r\n  ~~~~ \t\r\n`[b](b.md)` [c](c.md)\n``x\n[d](d.md)``\n~~~\n[e](e.md)'
        scan = verifier.inspect_source(raw)
        self.assertEqual(['c.md'], [row['destination'] for row in scan['expected_tokens']])
        self.assertEqual(['fenced_code', 'inline_code', 'inline_code', 'fenced_code'],
                         [row['reason'] for row in scan['unsupported_tokens']])
        for row, literal in zip(scan['unsupported_tokens'], (b'[a](a.md)', b'[b](b.md)', b'[d](d.md)', b'[e](e.md)')):
            self.assertEqual(literal, raw[row['start']:row['end']])
        unmatched = verifier.inspect_source(b'` unmatched [x](a.md)')
        self.assertEqual(1, len(unmatched['expected_tokens']))
        unequal = verifier.inspect_source(b'`` [x](a.md) `')
        self.assertEqual(1, len(unequal['expected_tokens']))

    def test_only_cr_lf_define_physical_lines(self):
        source = b'x\x0b```\n[a](a.md)\n```\n'
        self.assertEqual(['a.md'], [row['destination'] for row in verifier.inspect_source(source)['expected_tokens']])

    def test_unsupported_inventory_counts_are_required_and_separate(self):
        source = b'![x](a.md) [y][ref]'
        values = fixture(source)
        values[3]['unsupported'] = [{'start': 0, 'end': 10, 'reason': 'image'},
                                    {'start': 11, 'end': 19, 'reason': 'reference_style'}]
        values[3]['summary']['unsupported'] = 2
        self.assertEqual('pass', self.check(values)['verdict'])
        values[3]['unsupported'].pop()
        values[3]['summary']['unsupported'] = 1
        report = self.check(values)
        self.assertFalse(report['criteria']['complete_scoped_inventory'])
        self.assertTrue(report['criteria']['truthful_summary'])

    def test_direction_normalization_root_escape_and_nonregular_ancestors(self):
        specs = [('[a](./../target.md#)', './../target.md#', 'docs/target.md', 'regular_file', ''),
                 ('[b](../../../x.md)', '../../../x.md', None, 'outside_scope', None),
                 ('[c](link.md)', 'link.md', 'docs/theory/link.md', 'not_regular', None),
                 ('[d](link.md/x.md)', 'link.md/x.md', 'docs/theory/link.md/x.md', 'not_regular', None),
                 ('[e](folder.md)', 'folder.md', 'docs/theory/folder.md', 'not_regular', None),
                 ('[f](submodule.md)', 'submodule.md', 'docs/theory/submodule.md', 'not_regular', None),
                 ('[g](executable.md)', 'executable.md', 'docs/theory/executable.md', 'regular_file', None)]
        extras = [{'path': 'docs/theory/' + name, 'mode': mode, 'object_id': '4' * 40} for name, mode in
                  [('link.md', '120000'), ('folder.md', '040000'), ('submodule.md', '160000'), ('executable.md', '100755')]]
        values = fixture(' '.join(row[0] for row in specs).encode(), specs, extras)
        self.assertEqual('pass', self.check(values)['verdict'])
        values[3]['links'][0]['target'] = 'target.md'
        self.assertFalse(self.check(values)['criteria']['directed_target_resolution'])

    def test_omitted_invented_duplicate_reordered_and_wrong_span_fail(self):
        for mutation in ('omit', 'invent', 'duplicate', 'reverse', 'span'):
            with self.subTest(mutation=mutation):
                values = fixture()
                rows = values[3]['links']
                if mutation == 'omit':
                    rows.pop()
                elif mutation == 'duplicate':
                    rows.append(deepcopy(rows[0]))
                elif mutation == 'reverse':
                    rows.reverse()
                elif mutation == 'span':
                    rows[0]['start'] += 1
                else:
                    rows[0]['token_id'] = 'invented'
                self.assertFalse(self.check(values)['criteria']['complete_scoped_inventory'])

    def test_binding_and_summary_failures_are_results(self):
        for key in verifier.BINDINGS[1:-1]:
            with self.subTest(key=key):
                values = fixture()
                values[3][key] = 'wrong'
                report = self.check(values)
                self.assertEqual('fail', report['verdict'])
                self.assertFalse(report['criteria']['exact_task_binding'])
        values = fixture()
        values[3]['summary']['eligible'] = 500
        self.assertFalse(self.check(values)['criteria']['truthful_summary'])
        values[3]['all_links_valid'] = True
        self.assertFalse(self.check(values)['criteria']['exact_task_binding'])

    def test_malformed_first_bytes_are_negative_and_never_raise(self):
        values = fixture()
        raw = verifier.canonical(values[3])
        invalid = [b'\xff', b'\xef\xbb\xbf{}', b'{', b'null', b'[]', b'{"x":1,"x":2}',
                   b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'{"x":"\\ud800"}',
                   raw.replace(b'"schema_version":1', b'"schema_version":true')]
        for candidate in invalid:
            with self.subTest(raw=candidate[:40]):
                report = self.check(values, candidate)
                self.assertEqual('fail', report['verdict'])
                self.assertFalse(report['criteria']['exact_task_binding'])
                self.assertIsNone(report['criteria']['complete_scoped_inventory'])
                self.assertIsNone(report['reported_summary'])
                self.assertEqual(hashlib.sha256(candidate).hexdigest(), report['artifact_sha256'])
        for row in (1, None, [], 'wrong'):
            bad = deepcopy(values[3])
            bad['links'] = [row]
            self.assertEqual('fail', self.check(values, verifier.canonical(bad))['verdict'])

    def test_trusted_source_and_manifest_corruption_refuse(self):
        values = fixture()
        with self.assertRaisesRegex(ValueError, 'Source digest'):
            verifier.verify_inventory(values[0], values[1] + b'!', values[2], b'{}')
        for mutation in ('manifest_digest', 'blob', 'duplicate', 'parent', 'source_mode', 'unsorted'):
            with self.subTest(mutation=mutation):
                registration, source, manifest, inventory = deepcopy(values)
                if mutation == 'blob':
                    manifest['entries'][-1]['object_id'] = 'f' * 40
                elif mutation == 'duplicate':
                    manifest['entries'].append(deepcopy(manifest['entries'][-1]))
                elif mutation == 'parent':
                    manifest['entries'][0]['mode'] = '120000'
                elif mutation == 'source_mode':
                    manifest['entries'][-1]['mode'] = '120000'
                elif mutation == 'unsorted':
                    manifest['entries'].reverse()
                else:
                    registration['tree_manifest_sha256'] = 'f' * 64
                if mutation != 'manifest_digest':
                    registration['tree_manifest_sha256'] = hashlib.sha256(verifier.canonical(manifest)).hexdigest()
                with self.assertRaises(ValueError):
                    verifier.verify_inventory(registration, source, manifest, verifier.canonical(inventory))

    def test_candidate_and_byte_bounds_do_not_drop_evidence(self):
        with self.assertRaisesRegex(ValueError, 'candidate count'):
            verifier.inspect_source(b'[x](a.md)\n' * 1025)
        with self.assertRaisesRegex(ValueError, 'Source byte'):
            verifier.inspect_source(b'a' * 262145)
        with self.assertRaisesRegex(ValueError, 'strict UTF-8'):
            verifier.inspect_source(b'\xff')
        with self.assertRaisesRegex(ValueError, 'Delivery transport'):
            self.check(fixture(), b'a' * 1048577)
        destination = 'a' * 240000 + '.md'
        literal = '[x](' + destination + ')'
        values = fixture(literal.encode(), [(literal, destination, 'docs/theory/' + destination, 'missing', None)])
        report = self.check(values)
        self.assertEqual('pass', report['verdict'])
        self.assertLessEqual(len(verifier.canonical(report)), 1048576)

    def test_counterexamples_are_bounded_without_changing_failed_verdict(self):
        specs = [('[x](a.md)', 'a.md', 'docs/theory/a.md', 'missing', None)] * 40
        values = fixture((' '.join(row[0] for row in specs)).encode(), specs)
        for row in values[3]['links']:
            row['target'] = 'wrong.md'
        report = self.check(values)
        self.assertEqual('fail', report['verdict'])
        self.assertEqual(32, len(report['counterexamples']))
        self.assertFalse(report['criteria']['directed_target_resolution'])

    def test_near_limit_inventory_and_malformed_bytes_keep_complete_bounded_results(self):
        # Exact independent-review reproduction: legitimate input limits formerly
        # overflowed the expanded result, even for the malformed artifact b'{'.
        directory = 'docs/' + 'a' * 200 + '/' + 'b' * 200
        source_path = directory + '/owned.md'
        destinations = ['c' * 209 + '.md'] * 1023 + ['c' * 714 + '.md']
        source = ''.join('[x](' + destination + ')\n' for destination in destinations).encode()
        source_hash = hashlib.sha256(source).hexdigest()
        manifest = {'schema_version': 1, 'source_commit': 'a' * 40, 'entries': [
            {'path': path, 'mode': '040000', 'object_id': '1' * 40}
            for path in ('docs', 'docs/' + 'a' * 200, directory)] + [
                {'path': source_path, 'mode': '100644', 'object_id': hashlib.sha1(
                    b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()}]}
        registration = {'schema_version': 1, 'task_id': 'owned-task', 'registration_id': 'owned-registration',
            'protocol_sha256': 'b' * 64, 'criteria_sha256': 'c' * 64, 'source_commit': 'a' * 40,
            'source_path': source_path, 'source_sha256': source_hash,
            'tree_manifest_sha256': hashlib.sha256(verifier.canonical(manifest)).hexdigest()}
        links, cursor = [], 0
        for destination in destinations:
            end = cursor + len(('[x](' + destination + ')').encode())
            links.append({'token_id': f'{source_hash}:{cursor}:{end}', 'start': cursor, 'end': end,
                'destination': destination, 'fragment': None, 'target': directory + '/' + destination,
                'target_status': 'missing'})
            cursor = end + 1
        inventory = {key: registration[key] for key in verifier.BINDINGS[:-1]}
        inventory.update(links=links, unsupported=[], summary={'eligible': 1024, 'unsupported': 0,
            'target_status_counts': {'regular_file': 0, 'missing': 1024, 'not_regular': 0, 'outside_scope': 0}})
        raw = verifier.canonical(inventory)
        self.assertEqual((223737, 1453, 1048536), (len(source), len(verifier.canonical(manifest)), len(raw)))
        for delivered, verdict in ((raw, 'pass'), (b'{', 'fail')):
            with self.subTest(verdict=verdict):
                report = verifier.verify_inventory(registration, source, manifest, delivered)
                self.assertEqual(verdict, report['verdict'])
                self.assertLessEqual(len(verifier.canonical(report)), 1048576)
                self.assertEqual(1024, len(report['expected_tokens']))
                self.assertEqual(links, expanded_expected(report, source, source_path))
                if verdict == 'fail':
                    self.assertFalse(report['criteria']['exact_task_binding'])
                    self.assertIsNone(report['criteria']['complete_scoped_inventory'])
                    self.assertIsNone(report['reported_summary'])

    def test_long_registered_path_is_bound_without_unbounded_result_copy(self):
        # A single Git name can be long in retained objects even when it could
        # not be checked out on the host filesystem. No live path is accessed.
        registration, source, manifest, inventory = fixture(b'[x](missing.md)',
            [('[x](missing.md)', 'missing.md', 'missing.md', 'missing', None)])
        long_path = 'a' * 1048000 + '.md'
        manifest['entries'] = [{**manifest['entries'][-1], 'path': long_path}]
        registration['source_path'] = long_path
        registration['tree_manifest_sha256'] = hashlib.sha256(verifier.canonical(manifest)).hexdigest()
        self.assertLessEqual(len(verifier.canonical(manifest)), 1048576)
        report = verifier.verify_inventory(registration, source, manifest, b'{')
        self.assertEqual('fail', report['verdict'])
        self.assertFalse(report['criteria']['exact_task_binding'])
        self.assertIsNone(report['criteria']['complete_scoped_inventory'])
        self.assertNotIn('source_path', report['bindings'])
        self.assertEqual(hashlib.sha256(long_path.encode()).hexdigest(), report['source_path_sha256'])
        self.assertEqual(hashlib.sha256(verifier.canonical({k: registration[k] for k in verifier.BINDINGS})).hexdigest(),
                         report['registration_bindings_sha256'])
        self.assertEqual(inventory['links'], expanded_expected(report, source, long_path))
        self.assertLess(len(verifier.canonical(report)), 5000)

    def test_pure_checks_do_not_read_files_or_mutate_inputs(self):
        values = fixture()
        before = deepcopy(values)
        with patch('builtins.open', side_effect=AssertionError('file I/O')), patch.object(Path, 'open', side_effect=AssertionError('file I/O')):
            self.assertEqual('pass', self.check(values)['verdict'])
            verifier.inspect_source(values[1])
        self.assertEqual(before, values)

    def test_source_receipt_and_callable_constant_guards(self):
        self.assertEqual({verifier.__name__: verifier.IMPLEMENTATION_SOURCE}, verifier.runtime_sources())
        with patch.object(verifier, 'inspect_source', lambda _: None):
            with self.assertRaisesRegex(ValueError, 'callable changed'):
                verifier.runtime_sources()
        with patch.dict(verifier.CRITERIA, {'fragment_validity': 'measured'}):
            with self.assertRaisesRegex(ValueError, 'constant changed'):
                verifier.runtime_sources()


if __name__ == '__main__':
    unittest.main()
