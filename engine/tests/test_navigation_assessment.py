"""Owned prospective/retained lifecycle fixtures. Never open the actual evidence store."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import sys
import subprocess
import time
import os
import signal
import tempfile
import unittest
from unittest.mock import patch
from epiphysics import navigation_contracts as c, navigation_runner as runner, navigation_evaluation as evaluation
from epiphysics import navigation_assessment as navigation, public_map_assessment as mapping
from epiphysics.store import Ledger, instant
from test_navigation_contracts import tiny_map, tiny_cases
from test_navigation_evaluation import tiny_key, answer_for
from test_dated_delivery import append_completion


def identity(event): return {'event_id': event['id'], 'event_hash': event['hash']}
def checkpoint(event): return {'seq': event['seq'], **identity(event)}


def fixture_program(public_map, cohort, key, *, fail=False):
    """Explicit test stub with invented answers, never the actual independent candidate."""
    if fail: return b'import sys\nsys.stderr.write("owned synthetic child failure\\n")\nsys.exit(7)\n'
    answers = {case['case_id']: answer_for(case, public_map, key) for case in cohort['cases']}
    return ('import json,sys\nanswers=' + repr(answers) + '\nrequest=json.load(sys.stdin)\n'
        'print(json.dumps(answers[request["case"]["case_id"]],separators=(",",":")))\n').encode()


def accepted_c11(ledger, public_map):
    """Synthetic historical C11-shaped metadata; no C11 checker/build is invoked."""
    map_hash = c.digest(c.canonical(public_map))
    declared = {'request': c.digest(b'owned C11 request'), 'blob:' + map_hash: map_hash}
    declared.update({'code:epiphysics.' + name[:-3]: c.digest(('owned old ' + name).encode()) for name in mapping.SOURCE_NAMES})
    manifest = {'decision-input:' + role: value for role, value in declared.items()}
    report = {'schema_version': 1, 'status': 'checked', 'phase': mapping.PHASE, 'stage': mapping.STAGE,
        'contract_id': mapping.CONTRACT_ID, 'readiness': 'static_view_prepared',
        'dataset_identity': {name: public_map[name] for name in ('sourceCommit', 'catalogHash', 'payloadHash')},
        'assessment_identity': {'schema_version': 1, 'hash': c.digest(c.canonical(declared))},
        'input_hashes': {role: value for role, value in declared.items() if not role.startswith('code:')},
        'source_hashes': {name: declared['code:epiphysics.' + name[:-3]] for name in mapping.SOURCE_NAMES},
        'checks': {'owned_historical_control': True}, 'next_step': {'action': 'prepare_evidence_navigation_evaluation'}}
    assessment = {'input_manifest': manifest, 'decision_assessment_hash': report['assessment_identity']['hash']}
    assessment['hash'] = c.digest(c.canonical(assessment))
    return ledger.append('improvement_completed', {'run_key': 'owned-c11', 'result': 'assessed', 'request': {'manifest': manifest},
        'assessment_identity': assessment, 'report': {'decision_pilot': report},
        'next_step': {'id': 'owned-c11:next', 'state': 'queued', 'action': 'prepare_evidence_navigation_evaluation'}}, 'improvement:owned-c11:complete')


def make_study(directory, *, fail=False, mutate=None):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(directory / 'OWNED-ledger'); public_map = tiny_map(); cohort = tiny_cases(public_map); key = tiny_key(public_map, cohort)
    runtime = {'path': sys.executable, 'sha256': c.digest(runner.read(Path(sys.executable).resolve(), 256 * 1048576)), 'version': sys.version}
    inputs = {'candidate': fixture_program(public_map, cohort, key, fail=fail), 'map': c.canonical(public_map),
        'tasks': c.canonical(cohort), 'key': c.canonical(key), 'runtime': c.canonical(runtime)}
    authorship = {'schema_version': 1, 'design_author': 'owned-design-author', 'candidate_author': 'owned-candidate-author',
        'task_author': 'owned-task-key-author', 'key_author': 'owned-task-key-author', 'reviewer': 'owned-independent-reviewer',
        'checks': dict.fromkeys(navigation.AUTHOR_CHECKS, True), 'exposure': 'Explicit invented test stub and tiny fixtures; not actual independent study authorship.'}
    if mutate is not None: mutate(inputs, authorship)
    authorship['input_hashes'] = {role: c.digest(raw) for role, raw in inputs.items()}
    inputs['authorship'] = c.canonical(authorship)
    origin = accepted_c11(ledger, public_map); observed = {}; study_id = 'owned-navigation'
    for index, (role, raw) in enumerate(inputs.items()):
        observed[role] = ledger.capture(navigation._scope(study_id) + role, raw, event_id='owned-base-' + str(index))['id']
    study = {'directory': directory, 'ledger': ledger, 'origin': origin, 'study_id': study_id, 'inputs': inputs,
        'observations': observed, 'request_path': directory / 'request.json'}
    bind_request(study, navigation.PREPARATION, origin, observed)
    return study


def bind_request(study, phase, parent, observations):
    packet = {'schema_version': 1, 'phase': phase, 'observations': observations}
    request = {'schema_version': 1, 'phase': phase, 'study_id': study['study_id'], 'origin': {'step_id': parent['body']['next_step']['id']},
        'ledger_path': str(study['ledger'].root), 'evidence_origin': identity(study['origin']), 'queue_parent': identity(parent),
        'evidence_checkpoint': checkpoint(study['ledger'].events()[-1]),
        'paths': {'contract': str(study['directory'] / 'contract.json'), 'packet': str(study['directory'] / 'packet.json')}}
    (study['directory'] / 'contract.json').write_bytes(c.canonical(navigation.CONTRACT))
    (study['directory'] / 'packet.json').write_bytes(c.canonical(packet))
    study['request_path'].write_bytes(c.canonical(request)); study.update(request=request, packet=packet)
    return request


def register(study):
    prepared = navigation.prepare_navigation(study['request_path']); measured = navigation.assess_prepared_navigation(prepared)
    assert measured['report']['readiness'] == 'registered', measured['report']['errors']
    parent = append_completion(study['ledger'], prepared, measured, 'owned-navigation-registration')
    study['registration'] = parent
    return parent


def supervised_evaluation(study, directory, key_path):
    """Actual separate evaluator process; only unrelated owned fixture inputs."""
    registration = study['registration']['body']['report']['decision_pilot']['registration']
    command = [registration['runtime']['path'], '-I', '-B', '-c', c.EVALUATOR_BOOTSTRAP,
        str(Path(runner.__file__).resolve().parents[1]), 'epiphysics.navigation_evaluation', '--run-directory', str(directory), '--key', str(key_path)]
    start, started = time.monotonic(), runner.utc()
    process = subprocess.run(command, capture_output=True, timeout=65, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    end, ended = time.monotonic(), runner.utc()
    raw = (Path(directory) / 'evaluation.json').read_bytes(); report = c.decode(raw, c.MAX_REPORT_BYTES)
    outcome = {'schema_version': 1, 'registration': identity(study['registration']), 'runtime': registration['runtime'],
        'command': command, 'source_hashes': registration['source_hashes'], 'key_sha256': registration['input_hashes']['key'],
        'started_at': started, 'ended_at': ended, 'started_monotonic': start, 'ended_monotonic': end,
        'elapsed_seconds': end - start, 'returncode': process.returncode, 'termination': 'exited', 'error': None,
        'cleanup_errors': [], 'report_sha256': c.digest(raw)}
    for name, data in [('stdout', process.stdout), ('stderr', process.stderr)]:
        assert len(data) <= c.MAX_REPORT_BYTES + 1
        (Path(directory) / ('evaluator-supervised-' + name)).write_bytes(data)
        outcome[name] = {'bytes': len(data), 'sha256': c.digest(data), 'observed_bytes': len(data), 'complete': True}
    (Path(directory) / 'evaluator-supervised-outcome.json').write_bytes(c.canonical(outcome))
    return report, outcome


def execute_and_bind(study, *, capture_delay=None, outcome_mutator=None):
    parent = study['registration']; result = runner.run_registered(study['ledger'].root, identity(parent))
    key_path = study['directory'] / 'PRIVATE-owned-key.json'; key_path.write_bytes(study['inputs']['key'])
    scored, outcome = supervised_evaluation(study, result['directory'], key_path)
    if outcome_mutator is not None: outcome_mutator(outcome)
    if capture_delay is not None:
        claim = c.decode((Path(result['directory']) / 'claim.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        delayed = (instant(claim['started_at']) + timedelta(seconds=capture_delay)).isoformat()
        study['ledger'].clock = lambda: delayed
    observed = dict(study['observations']); observed.update({'execution:' + role: event for role, event in result['observations'].items()})
    event = study['ledger'].capture(runner.scope(parent['hash']) + 'evaluation', c.canonical(scored), event_id='owned-evaluation')
    observed['evaluation'] = event['id']
    event = study['ledger'].capture(runner.scope(parent['hash']) + 'evaluation_execution', c.canonical(outcome), event_id='owned-evaluation-execution')
    observed['evaluation_execution'] = event['id']; bind_request(study, navigation.CHECK, parent, observed)
    study.update(execution=result, scored=scored, evaluation_execution=outcome)
    return result


class NavigationAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)

    def study(self, **kwargs):
        value = make_study(Path(self.temp.name) / str(len(list(Path(self.temp.name).iterdir()))), **kwargs)
        self.addCleanup(value['ledger'].close); return value

    def test_preparation_is_prospective_and_never_executes(self):
        study = self.study()
        with patch('subprocess.Popen', side_effect=AssertionError('no candidate during preparation')):
            prepared = navigation.prepare_navigation(study['request_path'])
            measured = navigation.assess_prepared_navigation(prepared)
        self.assertEqual(measured['report']['readiness'], 'registered')
        self.assertIsNone(measured['report']['scores'])
        self.assertFalse((study['ledger'].root / 'navigation-runs').exists())

    def test_design_candidate_and_reviewer_role_reuse_are_unavailable_prerequisites(self):
        for target, reused in [('key_author', 'design_author'), ('task_author', 'design_author'), ('key_author', 'candidate_author'), ('reviewer', 'task_author')]:
            study = self.study(mutate=lambda _, authors, target=target, reused=reused: authors.update({target: authors[reused]}))
            result = navigation.assess_prepared_navigation(navigation.prepare_navigation(study['request_path']))['report']
            self.assertEqual(result['readiness'], 'unavailable_prerequisite')
            self.assertIsNone(result['registration']); self.assertEqual(result['next_step']['action'], 'repair_evidence_navigation_protocol')

    def test_actual_owned_children_follow_registration_and_check_is_retained_only(self):
        study = self.study(); parent = register(study); execute_and_bind(study)
        self.assertEqual(study['scored']['status'], 'scored', study['scored'])
        with patch('subprocess.Popen', side_effect=AssertionError('checker must not execute')):
            measured = navigation.assess_prepared_navigation(navigation.prepare_navigation(study['request_path']))
        self.assertTrue(all(measured['report']['checks'].values()), measured['report']['errors'])
        self.assertEqual(measured['report']['scores']['metrics']['strict_completion']['numerator'], 6)
        self.assertEqual(measured['report']['next_step']['action'], 'prepare_independent_evidence_navigation_comparison')
        with self.assertRaisesRegex(ValueError, 'no retry'):
            runner.run_registered(study['ledger'].root, identity(parent))

    def test_first_owned_nonzero_attempts_remain_negative_without_invented_answers(self):
        study = self.study(fail=True); register(study); execute_and_bind(study)
        measured = navigation.assess_prepared_navigation(navigation.prepare_navigation(study['request_path']))
        report = measured['report']; self.assertEqual(report['scores']['outcomes']['process_failed'], 6)
        self.assertEqual(report['scores']['metrics']['strict_completion']['numerator'], 0)
        self.assertEqual(report['next_step']['action'], 'repair_navigation_execution_contract')
        for ordinal in range(6):
            self.assertEqual((Path(study['execution']['directory']) / ('attempt-' + str(ordinal)) / 'stdout').read_bytes(), b'')

    def test_unregistered_origin_cannot_execute_and_no_claim_is_created(self):
        study = self.study(); count = len(study['ledger'].events())
        with self.assertRaisesRegex(ValueError, 'registration'):
            runner.run_registered(study['ledger'].root, identity(study['origin']))
        self.assertEqual(len(study['ledger'].events()), count)

    def test_tampered_retained_source_and_changed_key_cannot_score_as_original(self):
        study = self.study(); prepared = navigation.prepare_navigation(study['request_path'])
        role = 'code:epiphysics.navigation_evaluation'; prepared['artifacts'][role] += b'\n'
        prepared['manifest'][role] = c.digest(prepared['artifacts'][role])
        with self.assertRaisesRegex(ValueError, 'source'): navigation.check_prepared_navigation(prepared)
        register(study); result = runner.run_registered(study['ledger'].root, identity(study['registration']))
        key_path = study['directory'] / 'wrong-key'; key_path.write_bytes(b'{}')
        scored = evaluation.evaluate_run(result['directory'], key_path)
        self.assertEqual(scored['status'], 'failed'); self.assertIsNone(scored['scores'])
        with self.assertRaises(FileExistsError): evaluation.evaluate_run(result['directory'], key_path)

    def test_post_score_source_and_timeout_failures_have_no_accepted_scores(self):
        for fault in (ValueError('owned final source audit'), TimeoutError('owned final deadline fault')):
            study = self.study(); register(study)
            result = runner.run_registered(study['ledger'].root, identity(study['registration']))
            key_path = study['directory'] / 'PRIVATE-owned-key'; key_path.write_bytes(study['inputs']['key'])
            registered_sources = runner.sources(); calls = []
            def final_fault():
                calls.append(True)
                if len(calls) == 2: raise fault
                return registered_sources
            with patch.object(runner, 'sources', side_effect=final_fault):
                failed = evaluation.evaluate_run(result['directory'], key_path)
            self.assertEqual(len(calls), 2); self.assertEqual(failed['status'], 'failed')
            self.assertIsNone(failed['scores']); self.assertFalse(failed['total_budget_ok'])
            self.assertIsNotNone(failed['whole_run_seconds'])
            self.assertEqual(c.decode((Path(result['directory']) / 'evaluation.json').read_bytes(), c.MAX_REPORT_BYTES), failed)

    def test_interrupted_final_report_bytes_remain_provisional_without_process_outcome(self):
        study = self.study(); register(study)
        executed = runner.run_registered(study['ledger'].root, identity(study['registration']))
        key_path = study['directory'] / 'PRIVATE-owned-key'; key_path.write_bytes(study['inputs']['key'])
        real_fsync = os.fsync; fired = []
        def fsync(fd):
            frame = sys._getframe(1)
            if frame.f_code is runner.write_new.__code__ and Path(frame.f_locals['path']).name == 'evaluation.json' and not fired:
                fired.append(True); signal.setitimer(signal.ITIMER_REAL, .002); time.sleep(.05)
            return real_fsync(fd)
        with patch.object(os, 'fsync', new=fsync), self.assertRaises(runner.DeadlineExpired):
            evaluation.evaluate_run(executed['directory'], key_path)
        raw = (Path(executed['directory']) / 'evaluation.json').read_bytes()
        self.assertEqual(fired, [True]); self.assertEqual(c.decode(raw, c.MAX_REPORT_BYTES)['status'], 'scored')
        observed = dict(study['observations']); observed.update({'execution:' + role: event for role, event in executed['observations'].items()})
        observed['evaluation'] = study['ledger'].capture(runner.scope(study['registration']['hash']) + 'evaluation', raw, event_id='owned-interrupted-evaluation')['id']
        bind_request(study, navigation.CHECK, study['registration'], observed)
        with self.assertRaisesRegex(navigation.PreparationError, 'outcome'):
            navigation.prepare_navigation(study['request_path'])
        self.assertEqual((Path(executed['directory']) / 'evaluation.json').read_bytes(), raw)

    def test_nonzero_or_interrupted_external_outcome_never_accepts_scored_report(self):
        changes = [lambda value: value.update(returncode=1),
            lambda value: value.update(termination='deadline', returncode=-9, error='owned supervisor deadline'),
            lambda value: value['cleanup_errors'].append('owned cleanup failure'),
            lambda value: value['stdout'].update(sha256='0' * 64)]
        for change in changes:
            study = self.study(); register(study)
            execute_and_bind(study, outcome_mutator=change)
            # Outcome variants are explicit fixture mutations; the raw original
            # external process receipt remains in the owned run directory.
            self.assertEqual(study['scored']['status'], 'scored')
            report = navigation.assess_prepared_navigation(navigation.prepare_navigation(study['request_path']))['report']
            self.assertFalse(report['checks']['retained_evaluation']); self.assertIsNone(report['scores'])
            self.assertEqual(report['next_step']['action'], 'repair_navigation_execution_contract')


if __name__ == '__main__': unittest.main()
