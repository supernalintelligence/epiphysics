"""Invented calendars with literal expectations frozen before first execution.

Supply EPIPHYSICS_SCHEDULE_DECLARATION with the retained exact proposed v2
bytes. Missing private declaration evidence is an explicit skipped class, never
schedule conformance. EPIPHYSICS_SCHEDULE_EVIDENCE optionally retains controls.
"""
import ast
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from epiphysics import prospective_schedule as schedule

ORIGIN = '2032-02-28T23:00:00.125Z'
# Independent complete inventories: IDs and relative endpoint seconds are
# transcribed from the frozen declaration, without calling candidate helpers.
QUESTION_ROWS = [
    ('R1', 3600, 3900, 4200, 262800, 266400, '2032-02-29', '2032-03-03'),
    ('O1', 3600, 3900, 4200, 4560, 6360, '2032-02-29', '2032-02-29'),
    ('R2', 262800, 263100, 263400, 522000, 525600, '2032-03-03', '2032-03-06'),
    ('O2', 262800, 263100, 263400, 263760, 265560, '2032-03-03', '2032-03-03'),
    ('R3', 522000, 522300, 522600, 781200, 784800, '2032-03-06', '2032-03-09'),
    ('O3', 522000, 522300, 522600, 522960, 524760, '2032-03-06', '2032-03-06'),
    ('R4', 781200, 781500, 781800, 1040400, 1044000, '2032-03-09', '2032-03-12'),
    ('O4', 781200, 781500, 781800, 782160, 783960, '2032-03-09', '2032-03-09'),
]
HTTP_ROWS = [
    ('P1.0', 'R1', 3600, 3660, 3720, '2032-02-29', '00:00:00', '00:01:00', '00:02:00'),
    ('P1.1', 'R1', 90000, 90060, 90120, '2032-03-01', '00:00:00', '00:01:00', '00:02:00'),
    ('P1.2', 'R1', 176400, 176460, 176520, '2032-03-02', '00:00:00', '00:01:00', '00:02:00'),
    ('P1.3', 'R1', 262500, 262560, 262620, '2032-03-02', '23:55:00', '23:56:00', '23:57:00'),
    ('P2.0', 'R2', 262800, 262860, 262920, '2032-03-03', '00:00:00', '00:01:00', '00:02:00'),
    ('P2.1', 'R2', 349200, 349260, 349320, '2032-03-04', '00:00:00', '00:01:00', '00:02:00'),
    ('P2.2', 'R2', 435600, 435660, 435720, '2032-03-05', '00:00:00', '00:01:00', '00:02:00'),
    ('P2.3', 'R2', 521700, 521760, 521820, '2032-03-05', '23:55:00', '23:56:00', '23:57:00'),
    ('P3.0', 'R3', 522000, 522060, 522120, '2032-03-06', '00:00:00', '00:01:00', '00:02:00'),
    ('P3.1', 'R3', 608400, 608460, 608520, '2032-03-07', '00:00:00', '00:01:00', '00:02:00'),
    ('P3.2', 'R3', 694800, 694860, 694920, '2032-03-08', '00:00:00', '00:01:00', '00:02:00'),
    ('P3.3', 'R3', 780900, 780960, 781020, '2032-03-08', '23:55:00', '23:56:00', '23:57:00'),
    ('P4.0', 'R4', 781200, 781260, 781320, '2032-03-09', '00:00:00', '00:01:00', '00:02:00'),
    ('P4.1', 'R4', 867600, 867660, 867720, '2032-03-10', '00:00:00', '00:01:00', '00:02:00'),
    ('P4.2', 'R4', 954000, 954060, 954120, '2032-03-11', '00:00:00', '00:01:00', '00:02:00'),
    ('P4.3', 'R4', 1040100, 1040160, 1040220, '2032-03-11', '23:55:00', '23:56:00', '23:57:00'),
]
METHOD_ROWS = [
    ('R1:flat-constant-v1:first', 'R1', 'flat-constant-v1', 3900, 3910, 3950, 4200, '2032-02-29', '00:05:00', '00:05:10', '00:05:50'),
    ('R1:graph-constant-v1:first', 'R1', 'graph-constant-v1', 3950, 3960, 4000, 4200, '2032-02-29', '00:05:50', '00:06:00', '00:06:40'),
    ('O1:flat-constant-v1:first', 'O1', 'flat-constant-v1', 4000, 4010, 4050, 4200, '2032-02-29', '00:06:40', '00:06:50', '00:07:30'),
    ('O1:graph-constant-v1:first', 'O1', 'graph-constant-v1', 4050, 4060, 4100, 4200, '2032-02-29', '00:07:30', '00:07:40', '00:08:20'),
    ('R2:flat-constant-v1:first', 'R2', 'flat-constant-v1', 263100, 263110, 263150, 263400, '2032-03-03', '00:05:00', '00:05:10', '00:05:50'),
    ('R2:graph-constant-v1:first', 'R2', 'graph-constant-v1', 263150, 263160, 263200, 263400, '2032-03-03', '00:05:50', '00:06:00', '00:06:40'),
    ('O2:flat-constant-v1:first', 'O2', 'flat-constant-v1', 263200, 263210, 263250, 263400, '2032-03-03', '00:06:40', '00:06:50', '00:07:30'),
    ('O2:graph-constant-v1:first', 'O2', 'graph-constant-v1', 263250, 263260, 263300, 263400, '2032-03-03', '00:07:30', '00:07:40', '00:08:20'),
    ('R3:flat-constant-v1:first', 'R3', 'flat-constant-v1', 522300, 522310, 522350, 522600, '2032-03-06', '00:05:00', '00:05:10', '00:05:50'),
    ('R3:graph-constant-v1:first', 'R3', 'graph-constant-v1', 522350, 522360, 522400, 522600, '2032-03-06', '00:05:50', '00:06:00', '00:06:40'),
    ('O3:flat-constant-v1:first', 'O3', 'flat-constant-v1', 522400, 522410, 522450, 522600, '2032-03-06', '00:06:40', '00:06:50', '00:07:30'),
    ('O3:graph-constant-v1:first', 'O3', 'graph-constant-v1', 522450, 522460, 522500, 522600, '2032-03-06', '00:07:30', '00:07:40', '00:08:20'),
    ('R4:flat-constant-v1:first', 'R4', 'flat-constant-v1', 781500, 781510, 781550, 781800, '2032-03-09', '00:05:00', '00:05:10', '00:05:50'),
    ('R4:graph-constant-v1:first', 'R4', 'graph-constant-v1', 781550, 781560, 781600, 781800, '2032-03-09', '00:05:50', '00:06:00', '00:06:40'),
    ('O4:flat-constant-v1:first', 'O4', 'flat-constant-v1', 781600, 781610, 781650, 781800, '2032-03-09', '00:06:40', '00:06:50', '00:07:30'),
    ('O4:graph-constant-v1:first', 'O4', 'graph-constant-v1', 781650, 781660, 781700, 781800, '2032-03-09', '00:07:30', '00:07:40', '00:08:20'),
]
PRODUCER_ROWS = [
    ('producer:O1', 'O1', 4260, 4320, 4560, '2032-02-29'),
    ('producer:O2', 'O2', 263460, 263520, 263760, '2032-03-03'),
    ('producer:O3', 'O3', 522660, 522720, 522960, '2032-03-06'),
    ('producer:O4', 'O4', 781860, 781920, 782160, '2032-03-09'),
]
MEMBERSHIP_IDS = [
    ['P1.0'],
    ['P1.0', 'P1.1', 'P1.2', 'P1.3', 'P2.0'],
    ['P1.0', 'P1.1', 'P1.2', 'P1.3', 'P2.0', 'P2.1', 'P2.2', 'P2.3', 'P3.0'],
    ['P1.0', 'P1.1', 'P1.2', 'P1.3', 'P2.0', 'P2.1', 'P2.2', 'P2.3', 'P3.0', 'P3.1', 'P3.2', 'P3.3', 'P4.0'],
]
CALENDAR_BOUNDARIES = [
    ('2031-04-30T23:59:59.999999Z', '2031-05-01T00:59:59.999999Z', '2031-05-14T23:59:59.999999Z'),
    ('2031-12-31T23:59:59.000001Z', '2032-01-01T00:59:59.000001Z', '2032-01-14T23:59:59.000001Z'),
    ('2000-02-28T23:00:00Z', '2000-02-29T00:00:00.000000Z', '2000-03-13T23:00:00.000000Z'),
    ('1900-02-28T23:00:00Z', '1900-03-01T00:00:00.000000Z', '1900-03-14T23:00:00.000000Z'),
    ('0001-01-01T00:00:00Z', '0001-01-01T01:00:00.000000Z', '0001-01-15T00:00:00.000000Z'),
    ('9999-12-17T23:59:59.999999Z', '9999-12-18T00:59:59.999999Z', '9999-12-31T23:59:59.999999Z'),
]
INVALID_ORIGINS = [None, False, 1, 1.0, b'2032-02-28T23:00:00Z', '', 'Z',
    '2031-02-29T00:00:00Z', '2032-02-30T00:00:00Z', '0000-01-01T00:00:00Z',
    '10000-01-01T00:00:00Z', '2032-01-01T24:00:00Z', '2032-01-01T00:00:60Z',
    '2032-01-01T00:00:00', '2032-01-01T00:00:00-00:00', '2032-01-01T00:00:00+01:00',
    '2032-01-01 00:00:00Z', '2032-01-01T00:00:00z', '2032-01-01T00:00:00.1234567Z',
    '２０３２-01-01T00:00:00Z', ' 2032-01-01T00:00:00Z', '2032-01-01T00:00:00Z\n']


def raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def literal_inventory():
    """Expected calendar data assembled solely from prewritten literal tables."""
    def stamp(day, time):
        return day + 'T' + time + '.125000Z'
    kinds = {'questions': [], 'http_slots': [], 'method_attempt_slots': [], 'producer_attempt_slots': []}
    for ident, b, c, f, e, r, day, end in QUESTION_ROWS:
        kinds['questions'].append({'id': ident, 'offsets': [b, c, f, e, r],
            'times': [stamp(day, '00:00:00'), stamp(day, '00:05:00'), stamp(day, '00:10:00'),
                      stamp(end, '00:00:00' if ident.startswith('R') else '00:16:00'),
                      stamp(end, '01:00:00' if ident.startswith('R') else '00:46:00')]})
    for ident, q, b, s, d, day, t1, t2, t3 in HTTP_ROWS:
        kinds['http_slots'].append({'id': ident, 'question_id': q, 'offsets': [b, s, d],
                                   'times': [stamp(day, t) for t in (t1, t2, t3)]})
    for ident, q, m, b, s, d, f, day, t1, t2, t3 in METHOD_ROWS:
        kinds['method_attempt_slots'].append({'id': ident, 'question_id': q, 'method_id': m,
            'offsets': [b, s, d, f], 'times': [stamp(day, t) for t in (t1, t2, t3, '00:10:00')]})
    for ident, q, b, s, d, day in PRODUCER_ROWS:
        kinds['producer_attempt_slots'].append({'id': ident, 'question_id': q, 'offsets': [b, s, d],
            'times': [stamp(day, t) for t in ('00:11:00', '00:12:00', '00:16:00')]})
    return {'origin': ORIGIN, 'inventory': kinds, 'membership_ids': MEMBERSHIP_IDS,
            'overall_audit_deadline_offset_seconds': 1209600,
            'overall_audit_deadline_utc': '2032-03-13T23:00:00.125000Z',
            'calendar_boundaries': CALENDAR_BOUNDARIES}


class ScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get('EPIPHYSICS_SCHEDULE_DECLARATION')
        if not path:
            raise unittest.SkipTest('Exact private declaration not supplied; no schedule conformance measured')
        cls.declaration = Path(path).read_bytes()
        if hashlib.sha256(cls.declaration).hexdigest() != schedule.DECLARATION_SHA256:
            raise AssertionError('Wrong normative declaration fixture')
        cls.literal = literal_inventory()
        cls.counter = 0

    def retain(self, label, value):
        target = os.environ.get('EPIPHYSICS_SCHEDULE_EVIDENCE')
        if target:
            type(self).counter += 1
            path = Path(target)
            path.mkdir(parents=True, exist_ok=True)
            (path / f'{self.counter:04d}-{label}').write_bytes(value)

    def derive(self, origin=ORIGIN):
        result = schedule.derive_schedule(self.declaration, origin)
        self.retain('calendar.json', result)
        return json.loads(result)

    def refusal(self, callback, label, evidence=b'', reason=None):
        self.retain(label + '.input', evidence)
        with self.assertRaises(schedule.ScheduleRefusal) as caught:
            callback()
        self.assertLessEqual(len(str(caught.exception)), 80)
        if reason:
            self.assertEqual(str(caught.exception), reason)
        self.retain(label + '.refusal', str(caught.exception).encode())

    def reject_plan(self, value, label='mutated'):
        encoded = raw(value)
        self.refusal(lambda: schedule.verify_schedule(self.declaration, ORIGIN, encoded), label, encoded)

    def test_complete_literal_calendar_and_unchanged_values(self):
        plan = self.derive()
        declaration = json.loads(self.declaration)
        self.assertEqual(plan['relative_schedule'], declaration['schedule'])
        fields = {'questions': ['window_start', 'knowledge_cutoff', 'forecast_deadline', 'outcome_cutoff', 'resolution_deadline'],
                  'http_slots': ['scheduled', 'latest_start', 'durable_receipt_deadline'],
                  'method_attempt_slots': ['scheduled', 'latest_start', 'durable_receipt_deadline', 'forecast_deadline'],
                  'producer_attempt_slots': ['scheduled', 'latest_start', 'artifact_deadline']}
        for kind, rows in self.literal['inventory'].items():
            actual = plan['absolute_schedule'][kind]
            relative = plan['relative_schedule'][kind]
            self.assertEqual(len(actual), len(rows))
            for want, got, rel in zip(rows, actual, relative):
                ident = 'id' if kind == 'questions' else 'slot_id'
                self.assertEqual(got[ident], want['id'])
                self.assertEqual(rel[ident], want['id'])
                self.assertEqual([rel[f + '_offset_seconds'] for f in fields[kind]], want['offsets'])
                self.assertEqual([got[f + '_utc'] for f in fields[kind]], want['times'])
                expected_keys = {k.removesuffix('_offset_seconds') + '_utc' if k.endswith('_offset_seconds') else k for k in rel}
                self.assertEqual(set(got), expected_keys)
                for key in rel:
                    if not key.endswith('_offset_seconds'):
                        self.assertEqual(type(got[key]), type(rel[key]))
                        self.assertEqual(got[key], rel[key])
                for key in ('question_id', 'method_id'):
                    if key in want:
                        self.assertEqual(got[key], want[key])
        self.assertEqual(plan['overall_audit_deadline_utc'], self.literal['overall_audit_deadline_utc'])
        self.assertEqual(plan['overall_audit_deadline_offset_seconds'], 1209600)
        self.assertEqual(plan['representation_budgets'], {'normalized_input_bytes_max': 262144,
            'representation_bytes_max': 524288, 'answer_stdout_bytes_max': 65536, 'stderr_bytes_max': 16384,
            'method_total_wall_seconds_max': 30, 'cleanup_seconds_max': 5,
            'concurrent_method_processes_max': 1, 'attempts_per_method_question': 1})
        for output, original in [('counts', 'counts'), ('source_policy', 'sources'), ('http_policy', 'http_policy')]:
            self.assertEqual(plan[output], declaration[original])
        for slot in plan['absolute_schedule']['producer_attempt_slots']:
            self.assertEqual([slot[k] for k in ['ordinal', 'process_wall_seconds_max', 'cleanup_seconds_max',
                                              'artifact_bytes_max', 'stderr_bytes_max']], [1, 120, 5, 65536, 16384])
        self.assertTrue(all(x['ordinal'] == 1 for x in plan['absolute_schedule']['method_attempt_slots']))
        self.assertTrue(all(x['request_count_max'] == 1 for x in plan['absolute_schedule']['http_slots']))

    def test_complete_prior_opening_membership(self):
        plan = self.derive()
        times = {x['id']: x['times'][0] for x in self.literal['inventory']['http_slots']}
        expected = [{'question_id': f'R{i}', 'opening_poll_id': ids[-1],
                     'slots': [{'id': ident, 'nominal_at': times[ident]} for ident in ids]}
                    for i, ids in enumerate(MEMBERSHIP_IDS, 1)]
        self.assertEqual(plan['release_snapshot_membership'], expected)
        self.assertEqual([len(x['slots']) for x in expected], [1, 5, 9, 13])
        for i in range(1, 4):
            self.assertIn(f'P{i}.3', MEMBERSHIP_IDS[i])

    def test_canonical_equivalent_origins_and_serialization(self):
        first = schedule.derive_schedule(self.declaration, ORIGIN)
        for origin in ['2032-02-28T23:00:00.125000Z', '2032-02-28T23:00:00.125000+00:00']:
            self.assertEqual(schedule.derive_schedule(self.declaration, origin), first)
            self.assertIsNone(schedule.verify_schedule(self.declaration, origin, first))
        pretty = json.dumps(json.loads(first), indent=2).encode()
        self.assertIsNone(schedule.verify_schedule(self.declaration, ORIGIN, pretty))
        self.assertEqual(raw(json.loads(first)), first)
        self.assertLess(len(first), schedule.SCHEDULE_LIMIT)

    def test_calendar_boundaries(self):
        for origin, first, audit in CALENDAR_BOUNDARIES:
            with self.subTest(origin=origin):
                plan = self.derive(origin)
                self.assertEqual(plan['absolute_schedule']['http_slots'][0]['scheduled_utc'], first)
                self.assertEqual(plan['overall_audit_deadline_utc'], audit)

    def test_invalid_origins(self):
        for i, origin in enumerate(INVALID_ORIGINS):
            self.refusal(lambda: schedule.derive_schedule(self.declaration, origin),
                         f'origin-{i}', repr(origin).encode(), 'invalid_utc_origin')

    def test_upper_range_refuses_whole_plan(self):
        for origin in ['9999-12-18T00:00:00Z', '9999-12-31T23:59:59.999999Z']:
            self.refusal(lambda: schedule.derive_schedule(self.declaration, origin),
                         'upper-overflow', origin.encode(), 'datetime_range_unavailable')

    def test_exact_declaration_byte_identity(self):
        for value in [self.declaration + b'\n', self.declaration.replace(b'3600', b'3601', 1), b'{}', b'{', b'\xff']:
            self.refusal(lambda: schedule.derive_schedule(value, ORIGIN), 'wrong-declaration', value,
                         'declaration_digest_mismatch')
        for field, value in [('scheduled_offset_seconds', False), ('scheduled_offset_seconds', 3600.0),
                             ('slot_id', 'substituted'), ('extra_field', 1)]:
            declaration = json.loads(self.declaration)
            declaration['schedule']['http_slots'][0][field] = value
            encoded = raw(declaration)
            self.refusal(lambda: schedule.derive_schedule(encoded, ORIGIN), 'changed-declaration', encoded,
                         'declaration_digest_mismatch')

    def test_declaration_type_and_cap(self):
        for value in [None, {}, bytearray(self.declaration), self.declaration.decode(), b'x' * 131073]:
            self.refusal(lambda: schedule.derive_schedule(value, ORIGIN), 'declaration-type-cap', repr(value)[:90].encode())

    def test_missing_extra_duplicate_substituted_and_reordered_records(self):
        base = self.derive()
        for branch in ['relative_schedule', 'absolute_schedule']:
            for kind in base[branch]:
                for mutation in ['drop', 'extra', 'duplicate', 'substitute', 'reorder']:
                    plan = copy.deepcopy(base)
                    rows = plan[branch][kind]
                    if mutation == 'drop': rows.pop()
                    elif mutation == 'extra': rows.append(copy.deepcopy(rows[-1]))
                    elif mutation == 'duplicate': rows[-1] = copy.deepcopy(rows[0])
                    elif mutation == 'substitute': rows[0]['id' if kind == 'questions' else 'slot_id'] = 'unknown'
                    else: rows.reverse()
                    self.reject_plan(plan, branch + '-' + kind + '-' + mutation)

    def test_every_endpoint_and_budget_is_verified(self):
        base = self.derive()
        for branch in ['relative_schedule', 'absolute_schedule']:
            for kind, rows in base[branch].items():
                for index, row in enumerate(rows):
                    for field, value in row.items():
                        if field.endswith('_offset_seconds') or field.endswith('_utc') or type(value) is int:
                            plan = copy.deepcopy(base)
                            plan[branch][kind][index][field] = value + 1 if type(value) is int else '2032-02-29T00:00:01.125000Z'
                            self.reject_plan(plan, f'changed-{branch}-{kind}-{index}-{field}')
        for section in ['counts', 'http_policy', 'representation_budgets']:
            for field, value in base[section].items():
                if type(value) is int:
                    plan = copy.deepcopy(base)
                    plan[section][field] = value + 1
                    self.reject_plan(plan, 'changed-budget-' + section + '-' + field)
        for field in ['overall_audit_deadline_utc', 'overall_audit_deadline_offset_seconds']:
            plan = copy.deepcopy(base)
            plan[field] = '2032-03-14T23:00:00.125000Z' if field.endswith('_utc') else 1209601
            self.reject_plan(plan, 'changed-' + field)

    def test_cross_bindings_types_and_fields_are_verified(self):
        base = self.derive()
        for branch in ['relative_schedule', 'absolute_schedule']:
            for kind, field, value in [('questions', 'opening_poll_id', 'P2.0'), ('questions', 'subject_id', 'different'),
                ('http_slots', 'question_id', 'R4'), ('http_slots', 'purpose', 'outcome'),
                ('method_attempt_slots', 'method_id', 'graph-constant-v1'),
                ('method_attempt_slots', 'ordinal', True), ('producer_attempt_slots', 'ordinal', 1.0),
                ('producer_attempt_slots', 'question_id', 'O4')]:
                plan = copy.deepcopy(base)
                plan[branch][kind][0][field] = value
                self.reject_plan(plan, 'cross-binding-' + field)
            for kind in base[branch]:
                for mode in ['missing', 'extra']:
                    plan = copy.deepcopy(base)
                    if mode == 'missing': plan[branch][kind][0].pop(next(iter(plan[branch][kind][0])))
                    else: plan[branch][kind][0]['invented'] = None
                    self.reject_plan(plan, mode + '-field')
        for field, value in [('schedule_schema_version', True), ('registered', 0), ('launchable', True),
                             ('execution_authorized', True), ('timing_assurance', 'witnessed'),
                             ('declaration_sha256', '0' * 64), ('supplied_origin_utc', '2032-02-28T23:00:01.125000Z')]:
            plan = copy.deepcopy(base)
            plan[field] = value
            self.reject_plan(plan, 'changed-envelope-' + field)
        for field in base:
            plan = copy.deepcopy(base)
            plan.pop(field)
            self.reject_plan(plan, 'missing-envelope-' + field)
        plan = copy.deepcopy(base)
        plan['receipt'] = 'invented'
        self.reject_plan(plan, 'extra-envelope')

    def test_membership_cannot_be_pruned_retimed_or_substituted(self):
        base = self.derive()
        for index in range(4):
            for mutation in ['drop', 'duplicate', 'future', 'time', 'opening', 'question', 'reorder']:
                plan = copy.deepcopy(base)
                member = plan['release_snapshot_membership'][index]
                if mutation == 'drop': member['slots'].pop(0)
                elif mutation == 'duplicate': member['slots'].append(copy.deepcopy(member['slots'][0]))
                elif mutation == 'future': member['slots'][0]['id'] = 'P4.3'
                elif mutation == 'time': member['slots'][0]['nominal_at'] = '2032-02-29T00:01:00.125000Z'
                elif mutation == 'opening': member['opening_poll_id'] = 'P4.3'
                elif mutation == 'question': member['question_id'] = 'O1'
                elif index: member['slots'].reverse()
                else: continue
                self.reject_plan(plan, f'membership-{index}-{mutation}')

    def test_malformed_bounded_schedule(self):
        cases = [b'', b'[]', b'null', b'false', b'{}{}', b'\xef\xbb\xbf{}', b'\xff',
                 b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e400}',
                 b'{"x":1.0}', b'{"x":' + b'9' * 4301 + b'}', b'{"x":"\\ud800"}',
                 b'[' * 1500 + b'0' + b']' * 1500, b' ' * 131073, None, bytearray(b'{}')]
        for index, encoded in enumerate(cases):
            self.refusal(lambda: schedule.verify_schedule(self.declaration, ORIGIN, encoded),
                         f'malformed-{index}', encoded if type(encoded) is bytes else repr(encoded).encode())

    def test_authority_no_effects_and_runtime_settings(self):
        baseline = (sys.get_int_max_str_digits(), sys.getrecursionlimit())
        source = inspect.getsource(schedule)
        parsed = ast.parse(source)
        imports = {node.names[0].name for node in ast.walk(parsed) if isinstance(node, ast.Import)}
        from_imports = {node.module for node in ast.walk(parsed) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(imports, {'hashlib', 'json', 're'})
        self.assertEqual(from_imports, {'__future__', 'datetime'})
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr in {'now', 'utcnow', 'timestamp', 'fromtimestamp', 'total_seconds'}
                             for node in ast.walk(parsed)))
        before = bytes(self.declaration)
        with patch('builtins.open', side_effect=AssertionError('unexpected open')),\
             patch('time.time', side_effect=AssertionError('unexpected wall clock')),\
             patch('time.sleep', side_effect=AssertionError('unexpected sleep')):
            result = schedule.derive_schedule(self.declaration, ORIGIN)
            self.assertIsNone(schedule.verify_schedule(self.declaration, ORIGIN, result))
        plan = json.loads(result)
        self.assertIs(plan['registered'], False)
        self.assertIs(plan['launchable'], False)
        self.assertIs(plan['execution_authorized'], False)
        self.assertEqual(plan['timing_assurance'], 'supplied_origin_only')
        self.assertEqual(self.declaration, before)
        self.assertEqual((sys.get_int_max_str_digits(), sys.getrecursionlimit()), baseline)


if __name__ == '__main__':
    unittest.main()
