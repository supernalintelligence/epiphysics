"""Owned codec/provenance tests only; no policy, resolver or experiment run."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import decision_views as views

EXAMPLES = Path(__file__).parents[1] / 'examples' / 'control-exchange'


class DecisionViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((EXAMPLES / 'development-traces.json').read_bytes())
        cls.report = json.loads((EXAMPLES / 'preparation-byte-check.json').read_bytes())
        cls.contract = json.loads((EXAMPLES / 'decision-contract.json').read_bytes())
        cls.traces = {trace['trace_id']: trace for trace in cls.fixture['traces']}

    def prepare(self, trace_id='dev-01'):
        trace = self.traces[trace_id]
        return views.prepare_decision_input(deepcopy(trace['events']), deepcopy(trace['task']), trace['cutoff'], trace['decision_at'])

    def build(self, trace_id='dev-01', recipe='flat-recency-v1', budget=2048):
        prepared = self.prepare(trace_id)
        wire = views.build_decision_view(prepared['header_bytes'], prepared['event_tape_bytes'], recipe=recipe, budget_bytes=budget)
        return prepared, wire

    def decode(self, prepared, wire, budget=2048):
        return views.validate_decode_view(prepared['header_bytes'], prepared['event_tape_bytes'], wire, budget_bytes=budget)

    def test_all_six_reviewed_golden_views_match_exact_bytes_and_hashes(self):
        self.assertEqual(6, len(self.report['golden_views']))
        for golden in self.report['golden_views']:
            with self.subTest(trace=golden['trace_id'], arm=golden['arm']):
                prepared, wire = self.build(golden['trace_id'], golden['arm'])
                self.assertEqual(golden['serialized_view'].encode('utf-8'), wire)
                self.assertEqual(golden['bytes'], len(wire))
                self.assertEqual(golden['sha256'], hashlib.sha256(wire).hexdigest())
                self.assertEqual(prepared['input_hash'], self.decode(prepared, wire).input_hash)
                self.assertFalse(wire.endswith(b'\n'))

    def test_development_serialization_reproduces_all_reviewed_feasibility_rows(self):
        for row in self.contract['feasibility']['records']:
            prepared = self.prepare(row['trace_id'])
            self.assertEqual(row['eligible_input_bytes'], len(prepared['header_bytes']) + 1 + len(prepared['event_tape_bytes']))
            for recipe, expected in row['arms'].items():
                with self.subTest(trace=row['trace_id'], recipe=recipe):
                    wire = views.build_decision_view(prepared['header_bytes'], prepared['event_tape_bytes'], recipe=recipe)
                    decoded = self.decode(prepared, wire)
                    self.assertEqual(expected['bounded_bytes'], len(wire))
                    self.assertEqual(expected['retained_records'], len(decoded.events))
                    self.assertEqual(expected['retained_policy_kind_records'], decoded.retained_policy_count)
                    self.assertEqual(expected['eligible_policy_kind_records'], decoded.eligible_policy_count)
                    self.assertLessEqual(len(wire), 2048)

    def test_lossless_controls_reconstruct_identical_original_event_dictionaries(self):
        for trace_id in self.traces:
            decoded = []
            prepared = self.prepare(trace_id)
            expected = tuple(json.loads(line) for line in prepared['event_tape_bytes'].splitlines())
            for recipe in views.RECIPE_IDS:
                wire = views.build_decision_view(prepared['header_bytes'], prepared['event_tape_bytes'], recipe=recipe, budget_bytes=32768)
                value = self.decode(prepared, wire, 32768)
                self.assertEqual(expected, value.events)
                self.assertTrue(value.complete)
                decoded.append(value.events)
            self.assertEqual(decoded[0], decoded[1])

    def test_late_observation_and_attempt_identity_pairs_have_identical_public_bytes(self):
        for left, right in (('dev-01', 'dev-02'), ('dev-07', 'dev-08')):
            self.assertEqual(self.prepare(left), self.prepare(right))
        late = self.prepare('dev-02')['event_tape_bytes']
        self.assertNotIn(b'hidden-revoke', late)
        self.assertNotIn(b'hand_expected_visible_action', late)
        self.assertNotIn(b'artifact_outcome', late)

    def test_visible_future_effective_record_is_preserved_without_policy_interpretation(self):
        trace = deepcopy(self.traces['dev-01'])
        future = deepcopy(trace['events'][2])
        future.update(event_id='future-fail', observed_at='2020-01-01T00:08:00Z', effective_at='2020-01-01T00:11:40Z', verdict='fail')
        trace['events'].append(future)
        prepared = views.prepare_decision_input(trace['events'], trace['task'], trace['cutoff'], trace['decision_at'])
        wire = views.build_decision_view(prepared['header_bytes'], prepared['event_tape_bytes'], recipe=views.RECIPE_IDS[0])
        value = self.decode(prepared, wire)
        self.assertIn(future, value.events)
        self.assertTrue(value.complete)
        self.assertEqual(4, value.eligible_policy_count)
        self.assertFalse(hasattr(value, 'action'))

    def test_task_scope_is_identical_and_foreign_obligation_records_are_filtered(self):
        trace = deepcopy(self.traces['dev-01'])
        foreign = deepcopy(trace['events'][0])
        foreign.update(event_id='foreign', obligation_id='elsewhere')
        changed = views.prepare_decision_input(trace['events'] + [foreign], trace['task'], trace['cutoff'], trace['decision_at'])
        self.assertEqual(self.prepare(), changed)

    def test_duplicate_source_identity_rejected_even_if_duplicate_is_late_or_foreign(self):
        trace = deepcopy(self.traces['dev-01'])
        for changes in ({}, {'observed_at': '2020-01-01T00:11:40Z'}, {'obligation_id': 'other'}):
            duplicate = {**trace['events'][0], **changes}
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'Duplicate source event'):
                views.prepare_decision_input(trace['events'] + [duplicate], trace['task'], trace['cutoff'], trace['decision_at'])

    def test_duplicate_grant_cannot_replace_omitted_revoke_with_equal_counts(self):
        prepared, wire = self.build('dev-03')
        changed = json.loads(wire)
        grant = next(row for row in changed['records'] if row[1] == 'grant')
        revoke = next(index for index, row in enumerate(changed['records']) if row[1] == 'revoke')
        changed['records'][revoke] = deepcopy(grant)
        self.assertEqual([4, 4], changed['coverage'])
        with self.assertRaisesRegex(ValueError, 'Duplicate retained source'):
            self.decode(prepared, views.canonical(changed))

    def test_valid_partial_view_is_distinct_from_invalid_duplicate_substitution(self):
        flat_prepared, flat_wire = self.build('dev-11', views.RECIPE_IDS[0])
        flat = self.decode(flat_prepared, flat_wire)
        self.assertFalse(flat.complete)
        self.assertEqual((3, 1), (flat.eligible_policy_count, flat.retained_policy_count))
        graph_prepared, graph_wire = self.build('dev-11', views.RECIPE_IDS[1])
        graph = self.decode(graph_prepared, graph_wire)
        self.assertTrue(graph.complete)
        self.assertLess(len(graph.events), len(graph_prepared['event_tape_bytes'].splitlines()))
        opposite_prepared, opposite_wire = self.build('dev-12', views.RECIPE_IDS[1])
        self.assertFalse(self.decode(opposite_prepared, opposite_wire).complete)
        with self.assertRaisesRegex(ValueError, 'Lossless control must preserve'):
            self.decode(flat_prepared, flat_wire, 32768)

    def test_rows_spans_direction_and_source_values_are_exact_not_reconstructed_guesses(self):
        prepared, wire = self.build()
        operations = [
            lambda value: value['records'][0].__setitem__(12, value['records'][0][12] + 1),
            lambda value: value['records'][0].__setitem__(13, value['records'][0][13] - 1),
            lambda value: value['records'][0].__setitem__(6, value['records'][0][6] + 1),
            lambda value: value['records'][0].__setitem__(12, False),
            lambda value: value['records'][0].__setitem__(3, value['records'][0][4]),
            lambda value: value['records'][0].__setitem__(0, 'invented'),
            lambda value: value['records'].reverse(),
        ]
        for operation in operations:
            changed = json.loads(wire)
            operation(changed)
            with self.subTest(operation=operations.index(operation)), self.assertRaises(ValueError):
                self.decode(prepared, views.canonical(changed))

    def test_graph_nodes_edges_record_indices_and_counts_must_equal_source_reconstruction(self):
        prepared, wire = self.build(recipe=views.RECIPE_IDS[1])
        operations = [
            lambda value: value['edges'][0].__setitem__(0, value['edges'][0][1]),
            lambda value: value['edges'][0].__setitem__(3, 999),
            lambda value: value['edges'].append(deepcopy(value['edges'][0])),
            lambda value: value['nodes'].reverse(),
            lambda value: value['coverage'].__setitem__(0, 999),
            lambda value: value['coverage'].__setitem__(1, True),
        ]
        for operation in operations:
            changed = json.loads(wire)
            operation(changed)
            with self.subTest(operation=operations.index(operation)), self.assertRaises(ValueError):
                self.decode(prepared, views.canonical(changed))

    def test_view_source_hash_header_values_and_canonical_byte_boundary_are_bound(self):
        prepared, wire = self.build()
        for field, replacement in (('source_hash', '0' * 64), ('input_hash', '0' * 64), ('cutoff_s', 599), ('source_bytes', 0), ('v', True)):
            changed = json.loads(wire)
            changed[field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.decode(prepared, views.canonical(changed))
        for changed in (wire + b'\n', b' ' + wire, json.dumps(json.loads(wire), indent=2).encode()):
            with self.assertRaises(ValueError):
                self.decode(prepared, changed)

    def test_source_tape_must_be_canonical_ordered_eligible_whole_rows(self):
        prepared, wire = self.build()
        original = prepared['event_tape_bytes']
        rows = original.splitlines(keepends=True)
        foreign = json.loads(rows[0]); foreign['obligation_id'] = 'other'
        late = json.loads(rows[0]); late['observed_at'] = '2020-01-01T00:11:40Z'
        malformed = [original[:-1], original + b'\n', b''.join(reversed(rows)), rows[0] + original,
                     views.canonical(foreign) + b'\n', views.canonical(late) + b'\n', b' ' + original]
        for tape in malformed:
            with self.subTest(tape=tape[:20]), self.assertRaises(ValueError):
                views.build_decision_view(prepared['header_bytes'], tape, recipe=views.RECIPE_IDS[0])
        changed_header = json.loads(prepared['header_bytes'])
        changed_header['later_outcome'] = {'artifact_valid': True}
        with self.assertRaisesRegex(ValueError, 'header fields'):
            views.build_decision_view(views.canonical(changed_header), original, recipe=views.RECIPE_IDS[0])
        with self.assertRaises(ValueError):
            self.decode({**prepared, 'event_tape_bytes': original.replace(b'"pass"', b'"fail"')}, wire)

    def test_private_trace_labels_unknown_fields_and_outcome_events_are_not_accepted(self):
        trace = deepcopy(self.traces['dev-01'])
        with self.assertRaises(ValueError):
            views.prepare_decision_input(trace, trace['task'], trace['cutoff'], trace['decision_at'])
        for field in ('expected_action', 'later_outcome', 'trace_id'):
            event = {**trace['events'][0], field: 'private'}
            with self.subTest(field=field), self.assertRaises(ValueError):
                views.prepare_decision_input([event], trace['task'], trace['cutoff'], trace['decision_at'])
        event = {**trace['events'][0], 'kind': 'artifact_outcome'}
        with self.assertRaises(ValueError):
            views.prepare_decision_input([event], trace['task'], trace['cutoff'], trace['decision_at'])
        with self.assertRaises(ValueError):
            views.prepare_decision_input(trace['events'], {**trace['task'], 'expected_action': 'release'}, trace['cutoff'], trace['decision_at'])

    def test_precise_field_specific_utf8_digest_reference_and_time_bounds(self):
        task = deepcopy(self.traces['dev-01']['task'])
        task['requester'] = 'é' * 16
        views.validate_task(task)
        for bad in ('é' * 17, 'x' * 33, 'a b', '\ud800', ''):
            with self.subTest(bad=repr(bad)), self.assertRaises(ValueError):
                views.validate_task({**task, 'requester': bad})
        release = deepcopy(self.traces['dev-07']['events'][-1])
        self.assertEqual(64, len(release['reference']))
        views.validate_event(release)
        for bad in ('x' * 64, '0' * 63, None):
            with self.assertRaises(ValueError):
                views.validate_event({**release, 'reference': bad})
        for bad in ('2020-01-01T00:00:00+00:00', '2020-01-01T00:00:00.000Z', '2020-02-30T00:00:00Z', '2020-01-03T00:00:00Z'):
            with self.assertRaises(ValueError):
                views.seconds(bad)
        with self.assertRaises(ValueError):
            views.validate_task({**task, 'amount': True})

    def test_malformed_duplicate_json_numbers_depth_and_byte_bounds_refuse(self):
        prepared, wire = self.build()
        for raw in (b'null', b'[]', b'"bad"', b'{"v":1,"v":1}', b'{"v":NaN}', b'{"v":1.0}', b'\xff', b'[' * 2000 + b']' * 2000):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                self.decode(prepared, raw)
        with self.assertRaisesRegex(ValueError, 'byte bound'):
            self.decode(prepared, b'x' * 2049)
        with self.assertRaisesRegex(ValueError, 'byte bound'):
            views.build_decision_view(b'x' * 32769, b'', recipe=views.RECIPE_IDS[0])
        for bad in (True, 0, 2047, 2049, 32769):
            with self.assertRaises(ValueError):
                views.build_decision_view(prepared['header_bytes'], prepared['event_tape_bytes'], recipe=views.RECIPE_IDS[0], budget_bytes=bad)
        for wrong in (bytearray(wire), wire.decode(), None):
            with self.assertRaises(ValueError):
                self.decode(prepared, wrong)

    def test_event_limit_and_empty_source_are_explicit(self):
        trace = self.traces['dev-01']
        too_many = [{**trace['events'][0], 'event_id': 'g' + str(i)} for i in range(16)]
        with self.assertRaisesRegex(ValueError, 'bounded public event'):
            views.prepare_decision_input(too_many, trace['task'], trace['cutoff'], trace['decision_at'])
        empty = views.prepare_decision_input([], trace['task'], trace['cutoff'], trace['decision_at'])
        for recipe in views.RECIPE_IDS:
            wire = views.build_decision_view(empty['header_bytes'], empty['event_tape_bytes'], recipe=recipe)
            value = self.decode(empty, wire)
            self.assertEqual((), value.events)
            self.assertTrue(value.complete)
            self.assertEqual((0, 0), (value.eligible_policy_count, value.retained_policy_count))

    def test_verified_values_are_independent_and_class_fields_are_frozen(self):
        prepared, wire = self.build()
        first = self.decode(prepared, wire)
        self.assertIsInstance(first, views.VerifiedPolicyInput)
        first.header['task']['delegate'] = 'changed'
        first.events[0]['event_id'] = 'changed'
        again = self.decode(prepared, wire)
        self.assertEqual('A', again.header['task']['delegate'])
        self.assertEqual('g', again.events[0]['event_id'])
        self.assertEqual('A', self.traces['dev-01']['task']['delegate'])
        with self.assertRaises(FrozenInstanceError):
            again.complete = False

    def test_pure_preparation_build_decode_do_not_open_files_or_import_policy(self):
        trace = deepcopy(self.traces['dev-01'])
        with patch.object(Path, 'open', side_effect=AssertionError('Unexpected file access')), patch.object(Path, 'read_bytes', side_effect=AssertionError('Unexpected file access')):
            prepared = views.prepare_decision_input(trace['events'], trace['task'], trace['cutoff'], trace['decision_at'])
            wire = views.build_decision_view(prepared['header_bytes'], prepared['event_tape_bytes'], recipe=views.RECIPE_IDS[1])
            self.assertTrue(self.decode(prepared, wire).complete)
        self.assertNotIn('decision_policy', views.__dict__)
        self.assertNotIn('decision_resolver', views.__dict__)

    def test_separate_source_guard_detects_changed_source_functions_and_contract_constants(self):
        self.assertEqual({'epiphysics.decision_views': views.IMPLEMENTATION_SOURCE}, views.runtime_sources())
        with patch.object(views, 'IMPLEMENTATION_SOURCE', b'changed'):
            with self.assertRaises(ValueError):
                views.runtime_sources()
        with patch.object(views, '_priority', lambda *args: []):
            with self.assertRaisesRegex(ValueError, 'callable changed'):
                views.runtime_sources()
        with patch.object(views, 'VIEW_BUDGETS', (2048, 65536)):
            with self.assertRaisesRegex(ValueError, 'contract value changed'):
                views.runtime_sources()


if __name__ == '__main__':
    unittest.main()
