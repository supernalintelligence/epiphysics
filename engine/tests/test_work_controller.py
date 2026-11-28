import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
from test_work_contracts import FixtureCase, bundle, artifact_bundle, bind
from epiphysics import improvement, work_runner, work_contracts as c
from epiphysics.store import Ledger, canonical, utc_now

ENGINE = Path(__file__).resolve().parents[1]


class ControllerTests(FixtureCase):
    def dispatch(self, value):
        path = self.write(value)
        d = value['declaration']
        return improvement.dispatch(self.store, None, None, None, d['id'], after_step=d['after_step'],
                                    completed_work='Invented fixture assessment', work_contract_path=path)

    def cli(self, value):
        path = self.write(value)
        result = subprocess.run([sys.executable, '-s', '-m', 'epiphysics.improvement', '--store', str(self.store),
                                 'work', '--work-contract', str(path)], cwd=ENGINE,
                                env={'PATH': os.defpath, 'PYTHONPATH': str(ENGINE), 'PYTHONDONTWRITEBYTECODE': '1'},
                                capture_output=True, timeout=20)
        (self.root / 'cli.stdout').write_bytes(result.stdout); (self.root / 'cli.stderr').write_bytes(result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return json.loads(result.stdout)

    def test_reference_domain_real_cli_then_duplicate_refuses_without_replay(self):
        value = bundle(); result = self.cli(value)
        self.assertEqual(result['result'], 'assessed')
        self.assertEqual(result['dispatch']['deadline_status'], 'observed_within_deadline')
        self.assertTrue(result['dispatch']['automatic_continuation_allowed'])
        self.assertEqual(result['assessment']['accepted_measurements']['conformance'], {'numerator': 1, 'denominator': 5})
        self.assertEqual(result['assessment']['next_step']['action'], 'diagnose_work_conformance')
        events = self.events()
        with self.assertRaises(ValueError): self.dispatch(value)
        self.assertEqual(self.events(), events)

    def test_artifact_domain_real_cli_uses_identical_lifecycle(self):
        result = self.cli(artifact_bundle())
        self.assertEqual(result['result'], 'assessed')
        self.assertEqual(result['assessment']['accepted_measurements']['conformance'], {'numerator': 1, 'denominator': 4})
        self.assertEqual(result['assessment']['work_contract']['adapter'], 'artifact-quality-v1')
        self.assertEqual([e['kind'] for e in self.events()],
                         ['improvement_started', 'observation', 'observation', 'observation', 'improvement_completed'])
        self.assertEqual(result['dispatch']['program'], 'epiphysics.improvement work-assess')

    def test_child_report_alone_never_advances_queue(self):
        value = bundle(); path = self.write(value); prepared = work_runner.prepare(path, self.store)
        with patch.dict(os.environ, {'EPIPHYSICS_DISPATCH_ID': 'a' * 32,
                                     'EPIPHYSICS_EXPECTED_REQUEST_SHA256': c.hash_value(prepared['request'])}):
            report = work_runner.child(self.store, path)
        self.assertEqual(report['result'], 'provisional'); self.assertIsNone(report['accepted_measurements'])
        self.assertFalse(any(e['kind'] in improvement.TRANSITIONS for e in self.events()))
        ledger = Ledger.open_readonly(self.store)
        try: self.assertEqual(improvement.status(ledger)['unfinished_runs'], [value['declaration']['id']])
        finally: ledger.close()

    def test_legacy_queue_and_work_queue_cannot_consume_each_other(self):
        legacy = {'run_key': 'legacy', 'request': {'manifest': {'decision-input:request': '0' * 64}},
                  'next_step': {'id': 'legacy:diagnose', 'state': 'queued', 'action': 'diagnose_failed_assessment'}}
        ledger = Ledger(self.store)
        try: event = ledger.append('improvement_failed', legacy, 'legacy-failure')
        finally: ledger.close()
        value = bundle(after='legacy:diagnose', predecessor=work_runner.identity(event))
        with self.assertRaisesRegex(ValueError, 'legacy or C12'): self.dispatch(value)
        self.assertEqual(len(self.events()), 1)
        event = {'kind': 'improvement_completed', 'body': {'request': {'manifest': {c.MARKER: 'x'}},
                                                        'next_step': {'id': 'work:next'}}}
        with self.assertRaisesRegex(ValueError, 'work-contract'):
            improvement._check_decision_origin(None, [event], 'work:next')

    def test_malformed_legacy_decision_cannot_claim_work_successor(self):
        self.dispatch(bundle())
        before = self.events()
        policy = {'schema_version': 1, 'stage': 'offline_fixture', 'allow_scale_change': False,
                  'max_assessment_seconds': 5, 'external_spend': 0,
                  'required_families': sorted(improvement.FAMILIES), 'version': 'boundary-fixture'}
        cases = [{'id': 'case-' + str(n), 'family': family, 'description': 'Invented boundary fixture',
                  'cutoff': '2026-01-01T00:00:00Z',
                  'observations': [{'id': 'fact', 'recorded_at': '2025-12-31T00:00:00Z'}],
                  'checks': [{'id': 'check', 'dimension': 'identity', 'expected': 'fixture', 'evidence_ids': ['fact']}]}
                 for n, family in enumerate(sorted(improvement.FAMILIES))]
        supplied = {'schema_version': 1, 'cases': [{'id': case['id'], 'answers': []} for case in cases]}
        paths = (self.write(policy, 'policy.json'), self.write({'schema_version': 1, 'cases': cases}, 'suite.json'),
                 self.write(supplied, 'supplied-output.json'))
        malformed = self.write({}, 'malformed-decision.json')
        ledger = Ledger(self.store)
        try:
            for decision in (None, malformed):
                with self.subTest(decision=decision):
                    with self.assertRaisesRegex(ValueError, 'work-contract'):
                        improvement.assess(ledger, *paths, 'legacy-boundary',
                            after_step=before[-1]['body']['next_step']['id'], completed_work='Invented boundary check',
                            decision_study_path=decision)
                    self.assertEqual(ledger.events(), before)
                    self.assertEqual(improvement.status(ledger)['next_step'], before[-1]['body']['next_step'])
        finally:
            ledger.close()

    def test_lost_delivery_after_commit_preserves_one_authoritative_completion(self):
        original = work_runner.finish
        def lose(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('injected post-commit delivery loss')
        with patch.object(work_runner, 'finish', side_effect=lose): result = self.dispatch(bundle())
        self.assertEqual(result['result'], 'assessment_completed_delivery_failed')
        self.assertEqual(result['authoritative_transition']['kind'], 'improvement_completed')
        self.assertEqual(sum(e['kind'] in improvement.TRANSITIONS for e in self.events()), 1)

    def test_supervisor_error_after_claim_retains_input_and_queues_owned_failure(self):
        selector_type = selectors.DefaultSelector
        test = self
        class FaultSelector:
            def __init__(self): self.inner = selector_type()
            def __enter__(self): return self
            def __exit__(self, *args): self.inner.close()
            def register(self, *args): return self.inner.register(*args)
            def unregister(self, *args): return self.inner.unregister(*args)
            def get_map(self): return self.inner.get_map()
            def select(self, timeout):
                ready = self.inner.select(timeout)
                if any(e['kind'] == 'improvement_started' for e in test.events()):
                    raise OSError('injected process-inventory failure after observed claim')
                return ready
        value = bundle(); raw = canonical(value).encode()
        with patch.object(selectors, 'DefaultSelector', FaultSelector): result = self.dispatch(value)
        self.assertEqual(result['result'], 'failed')
        self.assertEqual(result['dispatch']['recovery'], 'diagnosis_queued')
        events = self.events(); self.assertEqual(events[-1]['kind'], 'improvement_failed')
        captured = next(e for e in events if e['id'].endswith(':input:work:bundle'))
        self.assertEqual((self.store / 'blobs' / captured['body']['content_hash']).read_bytes(), raw)
        self.assertNotIn('accepted_measurements', events[-1]['body'])

    def test_original_deadline_expiration_leaves_claim_pending_not_new_budget(self):
        value = bundle(); value['declaration']['max_seconds'] = 1
        original = work_runner.finish
        def late(*args, **kwargs):
            time.sleep(1.05)
            return original(*args, **kwargs)
        with patch.object(work_runner, 'finish', side_effect=late): result = self.dispatch(value)
        self.assertEqual(result['result'], 'work_deadline_exceeded')
        self.assertFalse(any(e['kind'] in improvement.TRANSITIONS for e in self.events()))
        self.assertIn('deadline', result['dispatch']['recovery'])

    def assert_late_delivery(self, result, kind):
        self.assertEqual(result['result'], 'work_deadline_exceeded')
        self.assertEqual(result['dispatch']['deadline_status'], 'exceeded')
        self.assertEqual(result['dispatch']['publication_status'], 'timely_delivery_not_established')
        self.assertEqual(result['dispatch']['continuation_status'], 'requires_inspection')
        self.assertFalse(result['dispatch']['automatic_continuation_allowed'])
        self.assertEqual(result['dispatch']['delivery_status'], 'failed')
        transitions = [event for event in self.events() if event['kind'] in improvement.TRANSITIONS]
        self.assertEqual([event['kind'] for event in transitions], [kind])
        self.assertEqual(result['authoritative_transition']['event_id'], transitions[0]['id'])
        retained = json.loads((Path(result['dispatch']['receipt_directory']) / 'finish.json').read_text())
        self.assertEqual(retained['result'], 'work_deadline_exceeded')
        self.assertFalse(retained['automatic_continuation_allowed'])

    def delayed_terminal_commit(self, kind):
        original_init = Ledger.__init__
        class DelayedCommit:
            def __init__(self, db): self.db = db
            def __getattr__(self, name): return getattr(self.db, name)
            def commit(self):
                row = self.db.execute('SELECT kind FROM events ORDER BY seq DESC LIMIT 1').fetchone()
                if row and row['kind'] == kind and self.db.in_transaction:
                    time.sleep(2.05)
                self.db.commit()
        def delayed_init(ledger, *args, **kwargs):
            original_init(ledger, *args, **kwargs)
            ledger.db = DelayedCommit(ledger.db)
        return patch.object(Ledger, '__init__', new=delayed_init)

    def test_slow_terminal_commit_preserves_event_but_disallows_continuation(self):
        value = bundle(); value['declaration']['max_seconds'] = 2
        with self.delayed_terminal_commit('improvement_completed'):
            result = self.dispatch(value)
        self.assert_late_delivery(result, 'improvement_completed')
        self.assertEqual(result['dispatch']['assessment_status'], 'completed')
        self.assertIn('work_closure_failed', result['dispatch']['termination'])

    def test_slow_failure_recovery_commit_is_not_timely_handoff(self):
        value = bundle(); value['declaration']['max_seconds'] = 2
        with self.delayed_terminal_commit('improvement_failed'), \
             patch.object(work_runner, 'finish', side_effect=OSError('invented closure failure')):
            result = self.dispatch(value)
        self.assert_late_delivery(result, 'improvement_failed')
        self.assertEqual(result['dispatch']['recovery'], 'recovery_publication_deadline_exceeded')

    def test_slow_authoritative_read_cannot_restore_ordinary_success(self):
        value = bundle(); value['declaration']['max_seconds'] = 2
        original = improvement._dispatch_transition
        def delayed(*args, **kwargs):
            answer = original(*args, **kwargs)
            time.sleep(2.05)
            return answer
        with patch.object(improvement, '_dispatch_transition', side_effect=delayed):
            result = self.dispatch(value)
        self.assert_late_delivery(result, 'improvement_completed')

    def test_slow_receipt_persistence_cannot_return_ordinary_success(self):
        value = bundle(); value['declaration']['max_seconds'] = 2
        original = Path.write_text
        writes = []
        def delayed(path, data, *args, **kwargs):
            if path.name == 'finish.json':
                writes.append(json.loads(data)['result'])
                if len(writes) == 1:
                    time.sleep(2.05)
            return original(path, data, *args, **kwargs)
        with patch.object(Path, 'write_text', new=delayed):
            result = self.dispatch(value)
        self.assert_late_delivery(result, 'improvement_completed')
        self.assertEqual(writes, ['assessed', 'work_deadline_exceeded'])

    def test_foreign_owner_refuses_parent_acceptance(self):
        value = bundle(); path = self.write(value); prepared = work_runner.prepare(path, self.store)
        began = utc_now()
        with patch.dict(os.environ, {'EPIPHYSICS_DISPATCH_ID': 'a' * 32,
                                     'EPIPHYSICS_EXPECTED_REQUEST_SHA256': c.hash_value(prepared['request'])}):
            report = work_runner.child(self.store, path)
        raw = canonical(report).encode()
        receipt = {'dispatch_id': 'b' * 32, 'pid': os.getpid(), 'returncode': 0, 'termination': None,
                   'output_sha256': c.store.digest(raw), 'started_at': began, 'ended_at': utc_now()}
        with self.assertRaisesRegex(ValueError, 'ownership'):
            work_runner.finish(self.store, prepared, 'b' * 32, receipt, raw, time.monotonic() + 5)
        self.assertFalse(any(e['kind'] in improvement.TRANSITIONS for e in self.events()))

    def test_source_drift_after_provisional_report_refuses_closure_and_recovery(self):
        original = work_runner.finish
        def drift(*args, **kwargs):
            with patch.object(work_runner, 'source_hashes', return_value={}):
                return original(*args, **kwargs)
        with patch.object(work_runner, 'finish', side_effect=drift): result = self.dispatch(bundle())
        self.assertEqual(result['result'], 'failed')
        # The source check was restored before recovery; the independently
        # reaped claim is therefore closed as failure, never accepted.
        self.assertEqual(self.events()[-1]['kind'], 'improvement_failed')

    def test_deadline_failure_inside_locked_closure_rolls_back_terminal_only(self):
        original_append = Ledger.append
        def interrupt(ledger, kind, *args, **kwargs):
            if kind == 'improvement_completed':
                validate = kwargs['validate']
                def expired(recorded_at):
                    validate(recorded_at)
                    raise ValueError('injected original deadline expiry under lock')
                kwargs['validate'] = expired
            return original_append(ledger, kind, *args, **kwargs)
        with patch.object(Ledger, 'append', new=interrupt): result = self.dispatch(bundle())
        self.assertEqual(result['result'], 'failed')
        events = self.events()
        self.assertFalse(any(e['kind'] == 'improvement_completed' for e in events))
        self.assertEqual(events[-1]['kind'], 'improvement_failed')
        self.assertTrue(any(e['id'].endswith(':input:work:report') for e in events))

    def test_post_report_publication_error_cannot_accept_score(self):
        original_capture = Ledger.capture
        def fail_publication(ledger, source, *args, **kwargs):
            event = original_capture(ledger, source, *args, **kwargs)
            if source == 'improvement-input:work:report':
                raise OSError('injected error after report capture')
            return event
        with patch.object(Ledger, 'capture', new=fail_publication): result = self.dispatch(bundle())
        self.assertEqual(result['result'], 'failed')
        events = self.events(); self.assertEqual(events[-1]['kind'], 'improvement_failed')
        self.assertFalse(any(e['kind'] == 'improvement_completed' for e in events))
        self.assertTrue(any(e['id'].endswith(':input:work:report') for e in events))

    def test_stale_predecessor_refuses_without_claim(self):
        value = bundle(after='someone-elses-step')
        with self.assertRaisesRegex(ValueError, 'Stale'): self.dispatch(value)
        self.assertEqual(self.events(), [])

    def test_parent_checkpoint_change_refuses_in_child_before_claim(self):
        popen = subprocess.Popen
        def intervening_write(*args, **kwargs):
            ledger = Ledger(self.store)
            try: ledger.capture('improvement-input:unrelated', b'an intervening observation', event_id='intervening')
            finally: ledger.close()
            return popen(*args, **kwargs)
        with patch.object(improvement.subprocess, 'Popen', side_effect=intervening_write):
            result = self.dispatch(bundle())
        self.assertEqual(result['result'], 'failed')
        self.assertEqual([e['id'] for e in self.events()], ['intervening'])

    def test_prepared_bundle_mutation_refuses_without_writes(self):
        prepared = work_runner.prepare(self.write(bundle()), self.store)
        prepared['bundle']['declaration']['roles']['reviewer'] = 'new-unregistered-reviewer'
        with self.assertRaisesRegex(ValueError, 'Captured work bundle changed'): work_runner.check_sources(prepared)
        self.assertEqual(self.events(), [])

    def test_prepared_outcome_mutation_refuses_even_with_rebound_manifest(self):
        prepared = work_runner.prepare(self.write(bundle()), self.store)
        prepared['bundle']['outcome_manifest']['records'][0]['submitted'] = None
        bind(prepared['bundle'])
        with self.assertRaisesRegex(ValueError, 'Captured work bundle changed'): work_runner.check_sources(prepared)
        self.assertEqual(self.events(), [])


if __name__ == '__main__':
    unittest.main()
