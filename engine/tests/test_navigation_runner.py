"""Real bounded owned child processes, never the study candidate or real ledger."""
from pathlib import Path
import signal
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from epiphysics import navigation_runner as runner, navigation_contracts as c
from test_navigation_assessment import make_study, register, identity


class NavigationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = {'path': sys.executable, 'sha256': c.digest(runner.read(Path(sys.executable).resolve(), 256 * 1048576)), 'version': sys.version}
        self.sources = runner.sources()

    def child(self, source, seconds=2, runtime=None):
        directory = self.root / ('attempt-' + str(len(list(self.root.iterdir()))))
        receipt = runner._run_child(directory, b'{"owned":true}', source, seconds, runtime or self.runtime, self.sources)
        return directory, receipt

    def test_real_nonzero_exit_preserves_raw_outputs_and_first_runtime_receipt(self):
        directory, receipt = self.child(b'import sys\nsys.stdout.write("owned output")\nsys.stderr.write("owned error")\nsys.exit(7)\n')
        self.assertEqual(receipt['returncode'], 7); self.assertEqual(receipt['termination']['kind'], 'completed')
        self.assertEqual((directory / 'stdout').read_bytes(), b'owned output')
        self.assertTrue(receipt['stdout']['complete']); self.assertTrue(receipt['source_unchanged'])
        runtime = c.decode((directory / 'runtime.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        self.assertIsNone(runtime['source_unchanged']); self.assertEqual(runtime['returncode'], 7)
        with self.assertRaises(FileExistsError):
            runner._run_child(directory, b'{}', b'print(1)', 1, self.runtime, self.sources)

    def test_output_overflow_preserves_only_complete_bounded_prefix(self):
        directory, receipt = self.child(b'import os\nos.write(1,b"x"*65536)\n')
        self.assertEqual(receipt['termination'], {'kind': 'output_limit', 'stream': 'stdout'})
        self.assertEqual((directory / 'stdout').read_bytes(), b'x' * c.MAX_STREAM_BYTES)
        self.assertFalse(receipt['stdout']['complete']); self.assertIsNone(receipt['stdout']['full_sha256'])
        self.assertGreater(receipt['stdout']['observed_bytes'], c.MAX_STREAM_BYTES)

    def test_child_with_closed_pipes_still_obeys_process_deadline(self):
        started = time.monotonic()
        _, receipt = self.child(b'import os,time\nos.close(1);os.close(2);time.sleep(5)\n', .15)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(receipt['termination']['kind'], 'timeout'); self.assertNotEqual(receipt['returncode'], 0)

    def test_spawn_failure_is_real_failure_without_a_fabricated_returncode(self):
        _, receipt = self.child(b'pass', runtime={**self.runtime, 'path': str(self.root / 'missing-python')})
        self.assertFalse(receipt['process_started']); self.assertIsNone(receipt['returncode'])
        self.assertEqual(receipt['termination']['kind'], 'spawn_error')

    def test_runtime_is_durable_before_postprocess_source_audit_failure(self):
        with patch.object(runner, 'sources', side_effect=ValueError('owned source audit failure')):
            directory, receipt = self.child(b'print("retained")')
        self.assertEqual(receipt['returncode'], 0); self.assertFalse(receipt['source_unchanged'])
        self.assertEqual(c.decode((directory / 'runtime.json').read_bytes(), c.MAX_RECEIPT_BYTES)['returncode'], 0)
        self.assertEqual((directory / 'stdout').read_bytes(), b'retained\n')

    def test_wall_deadline_interrupts_wait_and_restores_signal_state(self):
        previous = signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(TimeoutError, 'wall-clock'):
            runner.within_deadline(time.sleep, .05, 5)
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))

    def test_enclosing_deadline_retains_child_facts_and_prevents_later_work(self):
        directory = self.root / 'outer-deadline'; continued = []
        def work():
            runner._run_child(directory, b'{}', b'import time\ntime.sleep(5)\n', 5, self.runtime, self.sources)
            continued.append('must not happen')
        previous = signal.getsignal(signal.SIGALRM)
        # Synchronize to an actual process before shortening the existing alarm.
        real_popen = subprocess.Popen
        def launch(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            signal.setitimer(signal.ITIMER_REAL, .05)
            return process
        with patch.object(subprocess, 'Popen', side_effect=launch), self.assertRaises(runner.DeadlineExpired):
            runner.within_deadline(work, 5)
        self.assertEqual(continued, [])
        receipt = c.decode((directory / 'runtime.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        self.assertEqual(receipt['termination']['kind'], 'enclosing_deadline')
        self.assertTrue(receipt['process_started']); self.assertIsInstance(receipt['returncode'], int)
        self.assertIsNone(receipt['source_unchanged'])
        self.assertFalse((directory / 'receipt.json').exists())
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))

    def test_registered_outer_deadline_leaves_first_claim_and_raw_facts_without_seal(self):
        study = make_study(self.root / 'study', mutate=lambda inputs, _: inputs.update(candidate=b'import time\ntime.sleep(5)\n'))
        self.addCleanup(study['ledger'].close); parent = register(study); injected = []
        original = subprocess.Popen
        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            injected.append(True); signal.setitimer(signal.ITIMER_REAL, .05)
            return process
        with patch.object(subprocess, 'Popen', side_effect=launch):
            with self.assertRaises(runner.DeadlineExpired):
                runner.run_registered(study['ledger'].root, identity(parent))
        self.assertEqual(injected, [True])
        directory = study['ledger'].root / 'navigation-runs' / parent['hash']
        self.assertTrue((directory / 'attempt-0' / 'runtime.json').exists())
        self.assertTrue((directory / 'execution-error.json').exists())
        self.assertFalse((directory / 'attempt-1').exists()); self.assertFalse((directory / 'seal.json').exists())
        scoped = [event['body']['source'] for event in study['ledger'].events() if event['kind'] == 'observation'
            and event['body']['source'].startswith(runner.scope(parent['hash']))]
        self.assertEqual(scoped, [runner.scope(parent['hash']) + 'claim', runner.scope(parent['hash']) + 'attempt-0-claim'])
        with self.assertRaisesRegex(ValueError, 'no retry'):
            runner.run_registered(study['ledger'].root, identity(parent))

    def test_alarm_during_cleanup_preserves_facts_under_live_finalization_reserve(self):
        study = make_study(self.root / 'study'); self.addCleanup(study['ledger'].close); parent = register(study)
        original_fsync, original_write = os.fsync, runner.write_new
        fired, alarm_states = [], []
        def observe_write(path, raw, cap):
            if Path(path).name in {'runtime.json', 'execution-error.json'}:
                alarm_states.append(signal.getitimer(signal.ITIMER_REAL)[0])
            return original_write(path, raw, cap)
        def fsync(fd):
            frame = sys._getframe(1); cleanup = False
            while frame is not None:
                cleanup |= frame.f_code.co_name == 'finalize_process'
                frame = frame.f_back
            if cleanup and not fired:
                fired.append(True); runner.write_new = observe_write
                signal.setitimer(signal.ITIMER_REAL, .002); time.sleep(.05)
            return original_fsync(fd)
        try:
            with patch.object(os, 'fsync', side_effect=fsync), self.assertRaises(runner.DeadlineExpired):
                runner.run_registered(study['ledger'].root, identity(parent))
        finally: runner.write_new = original_write
        directory = study['ledger'].root / 'navigation-runs' / parent['hash']
        receipt = c.decode((directory / 'attempt-0' / 'runtime.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        self.assertEqual(fired, [True]); self.assertTrue(alarm_states and all(value > 0 for value in alarm_states))
        self.assertEqual(receipt['returncode'], 0); self.assertEqual(receipt['termination']['kind'], 'enclosing_deadline')
        self.assertFalse((directory / 'seal.json').exists()); self.assertFalse((directory / 'attempt-1').exists())

    def test_denied_cleanup_kill_is_retained_without_claiming_success(self):
        def denied(_pid, _signal): raise PermissionError('owned denied group kill')
        with patch.object(os, 'killpg', side_effect=denied):
            directory, receipt = self.child(b'print("owned completed child")')
        self.assertEqual(receipt['returncode'], 0)
        self.assertEqual(receipt['termination']['kind'], 'runner_error')
        self.assertTrue(any('PermissionError' in item for item in receipt['cleanup_errors']))
        raw = c.decode((directory / 'runtime.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        self.assertEqual(raw['returncode'], 0); self.assertEqual(raw['cleanup_errors'], receipt['cleanup_errors'])

    def test_registered_cleanup_failure_retains_first_receipt_and_halts_later_cases(self):
        study = make_study(self.root / 'study'); self.addCleanup(study['ledger'].close); parent = register(study)
        def denied(_pid, _signal): raise PermissionError('owned denied cleanup')
        with patch.object(os, 'killpg', side_effect=denied):
            executed = runner.run_registered(study['ledger'].root, identity(parent))
        directory = Path(executed['directory'])
        seal = c.decode((directory / 'seal.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        self.assertEqual(seal['outcomes'][0]['state'], 'attempted')
        self.assertTrue(all(row['state'] == 'not_started' and row['reason'] == 'cleanup_failed' for row in seal['outcomes'][1:]))
        receipt = c.decode((directory / 'attempt-0' / 'receipt.json').read_bytes(), c.MAX_RECEIPT_BYTES)
        self.assertEqual(receipt['returncode'], 0); self.assertEqual(receipt['termination']['kind'], 'runner_error')
        self.assertFalse((directory / 'attempt-1').exists())

    def test_executing_source_mutation_refused_before_registered_attempt(self):
        study = make_study(self.root / 'study'); self.addCleanup(study['ledger'].close); parent = register(study)
        with patch.object(c, 'ATTEMPT_SECONDS', 999):
            with self.assertRaisesRegex(ValueError, 'constant changed'):
                runner.run_registered(study['ledger'].root, identity(parent))
        self.assertFalse((study['ledger'].root / 'navigation-runs').exists())

    def test_runner_projection_never_reads_sealed_key_or_authorship_blobs(self):
        study = make_study(self.root / 'study'); self.addCleanup(study['ledger'].close); parent = register(study)
        events = study['ledger'].events(); _, registration = runner.accepted_registration(events, identity(parent))
        original = runner.read; paths = []
        def tracked(path, cap):
            paths.append(Path(path)); return original(path, cap)
        with patch.object(runner, 'read', side_effect=tracked):
            inputs = runner._public_inputs(study['ledger'], events, parent, registration)
        self.assertEqual(set(inputs), {'map', 'tasks', 'candidate', 'runtime'})
        self.assertNotIn(study['ledger'].root / 'blobs' / registration['input_hashes']['key'], paths)
        self.assertNotIn(study['ledger'].root / 'blobs' / registration['input_hashes']['authorship'], paths)

    def test_fixed_runner_and_separate_evaluator_cli_on_owned_registration(self):
        study = make_study(self.root / 'study'); self.addCleanup(study['ledger'].close); parent = register(study)
        environment = {'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(Path(runner.__file__).resolve().parents[1]),
            'PYTHONDONTWRITEBYTECODE': '1'}
        command = [sys.executable, '-m', 'epiphysics.navigation_runner', '--store', str(study['ledger'].root),
            '--registration-id', parent['id'], '--registration-hash', parent['hash']]
        executed = subprocess.run(command, env=environment, capture_output=True, timeout=20)
        self.assertEqual(executed.returncode, 0, executed.stderr)
        result = c.decode(executed.stdout, c.MAX_REPORT_BYTES)
        key_path = self.root / 'PRIVATE-owned-key'; key_path.write_bytes(study['inputs']['key'])
        evaluated = subprocess.run([sys.executable, '-m', 'epiphysics.navigation_evaluation', '--run-directory', result['directory'],
            '--key', str(key_path)], env=environment, capture_output=True, timeout=20)
        self.assertEqual(evaluated.returncode, 0, evaluated.stderr)
        score = c.decode(evaluated.stdout, c.MAX_REPORT_BYTES)
        self.assertEqual(score['status'], 'scored'); self.assertEqual(score['scores']['metrics']['strict_completion']['numerator'], 6)


if __name__ == '__main__': unittest.main()
