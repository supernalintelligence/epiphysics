"""Actual navigation adapters/controller on owned ledgers; legacy probes isolated."""
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from epiphysics import improvement, navigation_assessment as navigation, navigation_contracts as c
from epiphysics.store import instant
from test_navigation_assessment import make_study, bind_request, execute_and_bind
from test_decision_diagnosis import calls_named

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples' / 'improvement'


class NavigationControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.study = make_study(self.temp.name); self.ledger = self.study['ledger']; self.addCleanup(self.ledger.close)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name, metrics in (
            ('run_source_span_checks', ('source_span_resolution', 'assertion_history_preservation')),
            ('run_manifest_checks', ('representation_manifest_preservation',)),
            ('run_transformation_checks', ('transformation_preservation',)),
            ('run_graph_view_checks', ('split_merge_preservation',)),
            ('run_materialization_checks', ('output_manifest_materialization',)),
        ):
            self.stack.enter_context(patch.object(improvement, name,
                return_value={'metrics': {metric: 1 for metric in metrics}, 'scope': 'owned unrelated legacy probe stub'}))

    def assess(self, key='owned-navigation', candidate='reference'):
        return improvement.assess(self.ledger, EXAMPLES / 'policy.json', EXAMPLES / 'entities.json', candidate, key,
            after_step=self.study['request']['origin']['step_id'], completed_work='Owned navigation contract control, no actual study',
            decision_study_path=self.study['request_path'])

    def test_registration_and_retained_check_advance_separately_and_exact_replay_does_not_score(self):
        with calls_named({'Popen', 'run_registered', 'score_case', 'evaluate_run'}) as called:
            registered = self.assess()
        self.assertEqual(called, []); self.assertEqual(registered['result'], 'assessed', registered.get('message'))
        self.assertEqual(registered['next_step']['action'], 'run_textual_evidence_navigation_baseline')
        self.assertIsNone(registered['report']['decision_pilot']['scores'])
        self.assertLessEqual(registered['actual_resources']['first_retained_navigation_check_elapsed_seconds'], registered['actual_resources']['elapsed_seconds'])
        before = len(self.ledger.events())
        with calls_named({'assess_prepared_navigation', 'score_case', 'Popen'}) as called:
            self.assertEqual(self.assess(), registered)
        self.assertEqual(called, []); self.assertEqual(len(self.ledger.events()), before)
        self.study['registration'] = self.ledger.get('improvement:owned-navigation:complete')
        execute_and_bind(self.study)
        with calls_named({'Popen', 'run_registered', 'evaluate_run'}) as called:
            checked = self.assess('owned-check')
        self.assertEqual(called, []); self.assertEqual(checked['result'], 'assessed', checked.get('message'))
        self.assertEqual(checked['next_step']['action'], 'prepare_independent_evidence_navigation_comparison')
        self.assertEqual(checked['report']['decision_pilot']['scores']['metrics']['strict_completion']['numerator'], 6)
        count = len(self.ledger.events())
        with calls_named({'assess_prepared_navigation', 'score_case', 'Popen'}) as called:
            self.assertEqual(self.assess('owned-check'), checked)
        self.assertEqual(called, []); self.assertEqual(len(self.ledger.events()), count)
        self.assertTrue(self.ledger.verify()['valid'])

    def test_all_navigation_successors_refuse_generic_or_missing_evidence_before_claim(self):
        for index, action in enumerate(sorted(navigation.SEMANTIC_ACTIONS | navigation.NEXT_ACTIONS)):
            parent = self.ledger.append('improvement_completed', {'run_key': 'owned-' + str(index), 'request': {'manifest': {}},
                'next_step': {'id': 'owned-step-' + str(index), 'state': 'queued', 'action': action}}, 'owned-queue-' + str(index))
            count = len(self.ledger.events())
            for path in (None, self.study['directory'] / 'missing.json'):
                with self.assertRaises(ValueError):
                    improvement.assess(self.ledger, EXAMPLES / 'policy.json', EXAMPLES / 'entities.json', 'reference', 'owned-generic-' + str(index),
                        after_step=parent['body']['next_step']['id'], completed_work='Owned no-evidence refusal', decision_study_path=path)
                self.assertEqual(len(self.ledger.events()), count)

    def test_delayed_evaluation_capture_is_negative_and_preserves_scores(self):
        self.assess(); self.study['registration'] = self.ledger.get('improvement:owned-navigation:complete')
        execute_and_bind(self.study, capture_delay=1200)
        result = self.assess('owned-late-capture')
        self.assertEqual(result['result'], 'assessed', result.get('message'))
        report = result['report']['decision_pilot']
        self.assertFalse(report['checks']['time_bounds']); self.assertEqual(report['readiness'], 'repair_required')
        self.assertEqual(result['next_step']['action'], 'repair_navigation_execution_contract')
        self.assertEqual(report['scores']['metrics']['strict_completion']['numerator'], 6)
        self.assertTrue(self.ledger.verify()['valid'])

    def test_scored_bytes_with_failed_external_process_do_not_queue_comparison(self):
        self.assess(); self.study['registration'] = self.ledger.get('improvement:owned-navigation:complete')
        execute_and_bind(self.study, outcome_mutator=lambda value: value.update(returncode=1))
        self.assertTrue(self.study['scored']['scores']['passed'])
        result = self.assess('owned-failed-evaluator-outcome')
        self.assertEqual(result['result'], 'assessed', result.get('message'))
        self.assertIsNone(result['report']['decision_pilot']['scores'])
        self.assertFalse(result['report']['decision_pilot']['checks']['retained_evaluation'])
        self.assertEqual(result['next_step']['action'], 'repair_navigation_execution_contract')

    def test_closing_reserve_applies_even_before_the_whole_study_limit(self):
        self.assess(); self.study['registration'] = self.ledger.get('improvement:owned-navigation:complete')
        execute_and_bind(self.study, capture_delay=150)
        result = self.assess('owned-late-reserve')
        self.assertEqual(result['result'], 'assessed', result.get('message'))
        self.assertFalse(result['report']['decision_pilot']['checks']['time_bounds'])
        self.assertEqual(result['next_step']['action'], 'repair_navigation_execution_contract')

    def test_on_time_capture_cannot_complete_after_deadline_under_lock(self):
        self.assess(); self.study['registration'] = self.ledger.get('improvement:owned-navigation:complete')
        execute_and_bind(self.study)
        claim = c.decode((Path(self.study['execution']['directory']) / 'claim.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        late = (instant(claim['started_at']) + timedelta(seconds=1200)).isoformat()
        original_append, original_clock = self.ledger.append, self.ledger.clock
        final_clock_checks = []
        def append(kind, body, event_id=None, **kwargs):
            if kind == 'improvement_completed':
                on_time = original_clock()
                def clock():
                    final_clock_checks.append(self.ledger.db.in_transaction)
                    return on_time if len(final_clock_checks) == 1 else late
                self.ledger.clock = clock
            return original_append(kind, body, event_id, **kwargs)
        with patch.object(self.ledger, 'append', side_effect=append):
            result = self.assess('owned-late-completion')
        self.assertEqual(result['result'], 'failed'); self.assertEqual(result['error'], 'ClosureDeadlineExceeded')
        self.assertEqual(result['next_step']['action'], 'repair_navigation_execution_contract')
        self.assertIsNone(result['navigation_closure']['accepted_scores'])
        self.assertTrue(all(final_clock_checks))
        with self.assertRaisesRegex(ValueError, 'Missing event'):
            self.ledger.get('improvement:owned-late-completion:complete')
        retained = self.ledger.get(result['navigation_closure']['retained_report_observation'])
        report = c.decode((self.ledger.root / 'blobs' / retained['body']['content_hash']).read_bytes(), c.MAX_REPORT_BYTES)
        self.assertEqual(report['scores']['metrics']['strict_completion']['numerator'], 6)
        self.assertTrue(self.ledger.verify()['valid'])

    def test_failed_enclosing_probe_preserves_navigation_task_and_real_failure_lineage(self):
        failed = self.assess('owned-degraded', candidate='degraded')
        self.assertEqual(failed['result'], 'failed')
        parent = self.ledger.get('improvement:owned-degraded:failed')
        bind_request(self.study, navigation.PREPARATION, parent, self.study['observations'])
        repaired = self.assess('owned-repaired')
        self.assertEqual(repaired['result'], 'assessed', repaired.get('message'))
        self.assertEqual(repaired['report']['decision_pilot']['ancestry']['mode'], 'failed_attempt_continuation')
        self.assertEqual(repaired['next_step']['action'], 'run_textual_evidence_navigation_baseline')

    def test_completion_refuses_later_scoped_evidence_under_locked_recheck(self):
        original = self.ledger.append; injected = False
        def append(kind, body, event_id=None, **kwargs):
            nonlocal injected
            if kind == 'improvement_completed' and not injected:
                injected = True
                self.ledger.capture(navigation._scope(self.study['study_id']) + 'late', b'owned late bytes', event_id='owned-late')
            return original(kind, body, event_id, **kwargs)
        with patch.object(self.ledger, 'append', side_effect=append):
            result = self.assess('owned-late-check')
        self.assertEqual(result['result'], 'failed')
        with self.assertRaisesRegex(ValueError, 'Missing event'):
            self.ledger.get('improvement:owned-late-check:complete')
        self.assertIn('Later scoped', result['message'])

    def test_checked_unavailable_preparation_cannot_repeat_unchanged(self):
        raw = c.decode(self.study['inputs']['authorship'], c.MAX_RECEIPT_BYTES)
        raw['key_author'] = raw['design_author']
        # Rebuild an owned fixture; there is no correction to a real captured cohort.
        other = make_study(self.study['directory'] / 'negative', mutate=lambda _, authors: authors.update(key_author=authors['design_author']))
        self.addCleanup(other['ledger'].close); self.study = other; self.ledger = other['ledger']
        negative = self.assess('owned-negative')
        self.assertEqual(negative['result'], 'assessed', negative.get('message'))
        self.assertEqual(negative['next_step']['action'], 'repair_evidence_navigation_protocol')
        parent = self.ledger.get('improvement:owned-negative:complete')
        bind_request(self.study, navigation.PREPARATION, parent, self.study['observations'])
        count = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, 'Unchanged'):
            self.assess('owned-blind-repeat')
        self.assertEqual(len(self.ledger.events()), count)
        authorship = c.decode(self.study['inputs']['authorship'], c.MAX_RECEIPT_BYTES)
        authorship['key_author'] = 'owned-task-key-author'
        event = self.ledger.capture(navigation._scope(self.study['study_id']) + 'authorship', c.canonical(authorship), event_id='owned-fixed-authorship')
        observed = {**self.study['observations'], 'authorship': event['id']}
        bind_request(self.study, navigation.PREPARATION, parent, observed)
        repaired = self.assess('owned-changed-prerequisite')
        self.assertEqual(repaired['result'], 'assessed', repaired.get('message'))
        self.assertEqual(repaired['next_step']['action'], 'run_textual_evidence_navigation_baseline')


if __name__ == '__main__': unittest.main()
