"""Invented first-attempt controls; real fixed workers and labelled fake faults.

C23_RETAIN_DIRECTORY must name a new directory when first evidence is retained.
No prospective source selection, registered slot, or historical queue is used.
"""
from datetime import datetime, timedelta, timezone
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics import prospective_capture as capture
from epiphysics.store import Ledger, canonical, digest


SOURCE = b'leaf\ncapture\n'
EXPECTED = canonical({'schema_version': 1, 'source_sha256': digest(SOURCE), 'source_byte_length': 13,
    'lines': [{'start': 0, 'end': 5, 'sha256': digest(b'leaf\n')},
              {'start': 5, 'end': 13, 'sha256': digest(b'capture\n')}]}).encode()


class FakeSelector:
    """Ready regular files emulate pipes; this does not test OS readiness."""
    def __init__(self): self.rows = {}
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def register(self, file, _events, data):
        fd = file if type(file) is int else file.fileno()
        self.rows[fd] = SimpleNamespace(fd=fd, fileobj=file, data=data)
    def unregister(self, file): self.rows.pop(file if type(file) is int else file.fileno())
    def get_map(self): return self.rows
    def select(self, _timeout): return [(key, None) for key in list(self.rows.values())]


class FakeProcess:
    """No subprocess or signal; explicit faults exercise parent classification."""
    def __init__(self, stdout=b'', stderr=b'', code=0, waits=False, denied=False):
        self.pid = 900000001; self.returncode = None
        self.code = code; self.waits = waits; self.denied = denied; self.killed = False
        for name, raw in [('stdout', stdout), ('stderr', stderr)]:
            stream = tempfile.TemporaryFile(); stream.write(raw); stream.seek(0); setattr(self, name, stream)
    def poll(self): return self.returncode
    def kill(self):
        if self.denied: raise PermissionError('invented denied kill')
        self.killed = True; self.returncode = -9
    def wait(self, timeout=None):
        if self.waits and not self.killed:
            raise subprocess.TimeoutExpired('invented fake process', timeout)
        self.returncode = self.code if not self.killed else -9
        return self.returncode


class CaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        retained = os.environ.get('C23_RETAIN_DIRECTORY')
        cls.temporary = None
        if retained:
            cls.root = Path(retained); cls.root.mkdir(parents=False, exist_ok=False)
        else:
            cls.temporary = tempfile.TemporaryDirectory(prefix='epiphysics-c23-')
            cls.root = Path(cls.temporary.name)
        runtime_path = Path(sys.executable).resolve()
        cls.runtime = {'path': str(runtime_path), 'sha256': digest(runtime_path.read_bytes()), 'version': sys.version}

    @classmethod
    def tearDownClass(cls):
        if cls.temporary is not None: cls.temporary.cleanup()

    def setUp(self):
        self.directory = self.root / self._testMethodName
        self.directory.mkdir(exist_ok=False)
        self.ledger = Ledger(self.directory / 'ledger')
        self.calls = []; self.results = []; self.extra = {}; self.started = time.monotonic()
        now = datetime.now(timezone.utc)
        self.timing = {'not_before': (now - timedelta(seconds=10)).isoformat(),
            'latest_start': (now + timedelta(seconds=20)).isoformat(),
            'artifact_due': (now + timedelta(seconds=25)).isoformat(), 'wall_seconds': 3, 'cleanup_seconds': .5}
        self.binding = {'instance_id': 'invented-c23', 'question_id': self._testMethodName, 'slot_id': 'producer:invented',
            'channel_id': 'one', 'acceptance_sha256': 'a' * 64, 'declaration_sha256': 'd' * 64,
            'source_sha256': digest(SOURCE), 'schema_sha256': capture.SCHEMA_SHA256,
            'producer_sha256': capture.PRODUCER_SHA256, 'worker_sha256': digest(capture._WORKER)}

    def tearDown(self):
        self.ledger.close()
        raw = canonical({'test': self._testMethodName, 'calls': self.calls, 'returned': self.results, 'extra': self.extra,
                         'elapsed_seconds': time.monotonic() - self.started}).encode()
        with (self.directory / 'control-facts.json').open('xb') as output: output.write(raw)

    def invoke(self, *, source=SOURCE, binding=None, timing=None, directory=None, factory=None, native_wait=False):
        original = os.posix_spawn
        fakes = []
        def launch(path, args, env, **kwargs):
            row = {'kind': 'real_fixed_worker', 'arguments': args, 'started_monotonic': time.monotonic()}
            self.calls.append(row)
            pid = original(path, args, env, **kwargs); row['pid'] = pid
            return pid
        def fake_launch(owner, command, _input_fd, streams):
            row = {'kind': 'fake_process_fault', 'arguments': command, 'started_monotonic': time.monotonic()}
            self.calls.append(row)
            process = factory(); fakes.append(process); row['pid'] = process.pid
            owner['pid'] = process.pid; owner['spawn_returned'] = True
            for name, state in streams.items():
                os.dup2(getattr(process, name).fileno(), state['read_fd'], inheritable=False)
        def fake_wait(owner, observe):
            if owner['reaped'] or owner['status_unavailable'] or owner['pid'] is None: return
            try: code = fakes[-1].wait(timeout=0)
            except subprocess.TimeoutExpired: return
            owner.update(returncode=code, wait_status=(code << 8) if code >= 0 else -code,
                         reaped=True, wait_observed=observe())
        def fake_kill(pid, _signal):
            if pid != fakes[-1].pid: raise AssertionError('unowned fake signal')
            self.calls[-1]['kill_calls'] = self.calls[-1].get('kill_calls', 0) + 1
            fakes[-1].kill()
        try:
            with ExitStack() as stack:
                if factory is None:
                    stack.enter_context(patch.object(capture.os, 'posix_spawn', side_effect=launch))
                else:
                    stack.enter_context(patch.object(capture, '_spawn_owned', side_effect=fake_launch))
                    stack.enter_context(patch.object(capture.selectors, 'SelectSelector', FakeSelector))
                    if not native_wait:
                        stack.enter_context(patch.object(capture, '_wait_owned', side_effect=fake_wait))
                    stack.enter_context(patch.object(capture.os, 'kill', side_effect=fake_kill))
                result = capture.capture_first_delivery(self.ledger, binding or self.binding, source,
                    runtime=self.runtime, channel_directory=directory or self.directory / 'channel', timing=timing or self.timing)
        finally:
            for process in fakes:
                process.stdout.close(); process.stderr.close()
        self.results.append(result)
        return result

    def fake(self, **values): return lambda *_args, **_kwargs: FakeProcess(**values)

    def test_real_fixed_worker_retains_exact_artifact_and_local_claim(self):
        result = self.invoke(); receipt = result['receipt']; stream = receipt['streams']['stdout']
        self.assertEqual(Path(stream['path']).read_bytes(), EXPECTED)
        self.assertEqual(receipt['returncode'], 0); self.assertTrue(receipt['child_reaped'])
        self.assertTrue(stream['complete_bytes_observed']); self.assertTrue(stream['retention_verified'])
        self.assertTrue(result['publication_by_artifact_due']); self.assertFalse(result['continuation_allowed'])
        self.assertIsNone(receipt['quality']); self.assertIsNone(receipt['obligation_outcome'])
        self.assertEqual(len(self.ledger.events()), 2)
        self.assertLessEqual(stream['first_byte_observed']['monotonic'], stream['last_byte_observed']['monotonic'])
        self.assertLessEqual(stream['last_byte_observed']['monotonic'], stream['file_durable_observed']['monotonic'])

    def test_real_empty_boundary_is_artifact_not_empty_stream(self):
        binding = {**self.binding, 'source_sha256': digest(b'')}
        result = self.invoke(source=b'', binding=binding)
        raw = Path(result['receipt']['streams']['stdout']['path']).read_bytes()
        self.assertEqual(raw, canonical({'lines': [], 'schema_version': 1, 'source_byte_length': 0,
                                        'source_sha256': digest(b'')}).encode())
        self.assertEqual(result['receipt']['returncode'], 0)

    def test_real_capacity_refusal_has_no_artifact_quality_verdict(self):
        source = b'\n' * 700
        result = self.invoke(source=source, binding={**self.binding, 'source_sha256': digest(source)})
        receipt = result['receipt']
        self.assertEqual(receipt['returncode'], 2)
        self.assertEqual(receipt['streams']['stdout']['retained_bytes'], 0)
        self.assertTrue(receipt['streams']['stdout']['complete_bytes_observed'])
        self.assertIsNone(receipt['quality']); self.assertIsNone(receipt['obligation_outcome'])

    def test_duplicate_binding_or_directory_cannot_replace_first_attempt(self):
        first = self.invoke()
        original = (self.directory / 'channel' / 'stdout.bin').read_bytes()
        with self.assertRaises(ValueError):
            self.invoke(binding={**self.binding, 'acceptance_sha256': 'b' * 64}, directory=self.directory / 'elsewhere')
        self.assertEqual(len(self.calls), 1); self.assertEqual(len(self.ledger.events()), 2)
        self.assertFalse((self.directory / 'elsewhere').exists())
        self.assertEqual((self.directory / 'channel' / 'stdout.bin').read_bytes(), original)
        self.assertEqual(first['receipt']['streams']['stdout']['retained_sha256'], digest(original))

    def test_preflight_refusals_do_not_claim_or_launch(self):
        for changed in [{'source_sha256': '0' * 64}, {'schema_sha256': '0' * 64}, {'producer_sha256': '0' * 64}]:
            with self.assertRaises(ValueError): self.invoke(binding={**self.binding, **changed})
        with self.assertRaises(ValueError): self.invoke(source=b'x' * 8193)
        with self.assertRaises(ValueError): self.invoke(timing={**self.timing, 'wall_seconds': 121})
        self.assertEqual(self.calls, []); self.assertEqual(self.ledger.events(), [])

    def test_existing_path_and_symlink_refused_without_claim(self):
        target = self.directory / 'existing'; target.mkdir()
        link = self.directory / 'link'; link.symlink_to(target, target_is_directory=True)
        for path in [target, link]:
            with self.assertRaises(ValueError): self.invoke(directory=path)
        self.assertEqual(self.ledger.events(), []); self.assertEqual(self.calls, [])

    def test_locked_ledger_refuses_before_launch_without_waiting(self):
        other = Ledger(self.ledger.root)
        try:
            other.db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(Exception) as error: self.invoke()
            self.assertEqual(type(error.exception).__name__, 'OperationalError')
            self.assertEqual(self.calls, []); self.assertFalse((self.directory / 'channel').exists())
        finally:
            other.db.rollback(); other.close()

    def test_fake_nonzero_exit_keeps_complete_artifact_separate(self):
        result = self.invoke(factory=self.fake(stdout=b'{broken', stderr=b'reason', code=7))
        receipt = result['receipt']
        self.assertEqual(receipt['returncode'], 7)
        self.assertTrue(receipt['streams']['stdout']['complete_bytes_observed'])
        self.assertEqual(Path(receipt['streams']['stderr']['path']).read_bytes(), b'reason')
        self.assertIsNone(receipt['quality'])

    def test_fake_independent_exact_stream_caps_are_complete(self):
        result = self.invoke(factory=self.fake(stdout=b'o' * 65536, stderr=b'e' * 16384))
        for name, cap in [('stdout', 65536), ('stderr', 16384)]:
            stream = result['receipt']['streams'][name]
            self.assertEqual(stream['retained_bytes'], cap); self.assertTrue(stream['complete_bytes_observed'])

    def test_fake_stdout_overflow_retains_prefix_and_lower_bound(self):
        result = self.invoke(factory=self.fake(stdout=b'o' * 65537))
        stream = result['receipt']['streams']['stdout']
        self.assertEqual(stream['retained_bytes'], 65536); self.assertEqual(stream['observed_bytes_lower_bound'], 65537)
        self.assertFalse(stream['complete_bytes_observed']); self.assertIsNone(stream['full_sha256'])
        self.assertEqual(result['receipt']['termination'], 'stdout_overflow')

    def test_fake_stderr_overflow_does_not_merge_into_artifact(self):
        result = self.invoke(factory=self.fake(stdout=b'first', stderr=b'e' * 16385))
        self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), b'first')
        self.assertEqual(result['receipt']['termination'], 'stderr_overflow')
        self.assertEqual(result['receipt']['streams']['stderr']['retained_bytes'], 16384)

    def test_fake_closed_pipes_do_not_hide_living_child_timeout(self):
        result = self.invoke(factory=self.fake(waits=True))
        receipt = result['receipt']
        self.assertIn(receipt['termination'], {'wall_timeout', 'parent_deadline'}); self.assertEqual(receipt['returncode'], -9)
        self.assertTrue(receipt['child_reaped']); self.assertTrue(receipt['streams']['stdout']['eof_observed'])

    def test_fake_denied_cleanup_is_unreaped_not_successful_absence(self):
        result = self.invoke(factory=self.fake(waits=True, denied=True))
        self.assertFalse(result['receipt']['child_reaped']); self.assertIsNone(result['receipt']['returncode'])
        self.assertTrue(result['receipt']['errors']); self.assertIsNone(result['receipt']['obligation_outcome'])

    def test_fake_spawn_failure_keeps_first_claim_and_no_pid(self):
        def failed(*_args, **_kwargs): raise OSError('invented spawn failure')
        result = self.invoke(factory=failed)
        self.assertIsNone(result['receipt']['pid']); self.assertFalse(result['receipt']['child_reaped'])
        self.assertEqual(len(self.ledger.events()), 2)
        with self.assertRaises(ValueError): self.invoke(directory=self.directory / 'retry', factory=failed)
        self.assertEqual(len(self.calls), 1)

    def test_fake_retention_corruption_does_not_become_verified(self):
        original = capture._read
        def altered(path, cap, **kwargs):
            raw = original(path, cap, **kwargs)
            return b'altered' if Path(path).name == 'stdout.bin' else raw
        with patch.object(capture, '_read', side_effect=altered):
            result = self.invoke(factory=self.fake(stdout=b'original'))
        self.assertFalse(result['receipt']['streams']['stdout']['retention_verified'])
        self.assertEqual(result['receipt']['streams']['stdout']['retained_sha256'], digest(b'altered'))
        self.assertEqual(result['receipt']['streams']['stdout']['observed_prefix_sha256'], digest(b'original'))

    def test_fake_failed_stdout_fsync_does_not_certify_saved_memory(self):
        original = capture.os.fsync
        def failed(fd):
            target = self.directory / 'channel' / 'stdout.bin'
            if target.exists() and os.fstat(fd).st_ino == target.stat().st_ino:
                raise OSError('invented stdout fsync failure')
            return original(fd)
        with patch.object(capture.os, 'fsync', side_effect=failed):
            result = self.invoke(factory=self.fake(stdout=b'observed'))
        stream = result['receipt']['streams']['stdout']
        self.assertEqual(stream['observed_prefix_sha256'], digest(b'observed'))
        self.assertFalse(stream['retention_verified']); self.assertIsNone(stream['file_durable_observed'])
        self.assertIsNone(result['receipt']['quality'])

    def test_fake_eof_durable_time_not_replaced_by_later_cleanup(self):
        result = self.invoke(factory=self.fake(stdout=b'done', code=9))
        receipt = result['receipt']; stream = receipt['streams']['stdout']
        self.assertLess(stream['file_durable_observed']['monotonic'], receipt['ended']['monotonic'])
        self.assertEqual(receipt['returncode'], 9)

    def test_fake_clock_jump_and_late_receipt_are_reported(self):
        original = capture._stamp; calls = []
        def shifted():
            value = original(); calls.append(1)
            if len(calls) > 9:
                value['utc'] = (datetime.fromisoformat(value['utc']) + timedelta(seconds=40)).isoformat()
            return value
        with patch.object(capture, '_stamp', side_effect=shifted):
            result = self.invoke(factory=self.fake(stdout=b'done'))
        self.assertFalse(result['publication_clock_verified']); self.assertFalse(result['publication_by_artifact_due'])

    def test_fake_receipt_failure_leaves_claim_and_refuses_retry(self):
        original = capture._write_new
        def failed(path, raw, **kwargs):
            if Path(path).name == 'receipt.json': raise OSError('invented receipt disk error')
            return original(path, raw, **kwargs)
        with patch.object(capture, '_write_new', side_effect=failed), self.assertRaises(OSError):
            self.invoke(factory=self.fake(stdout=b'done'))
        self.assertEqual(len(self.ledger.events()), 1)
        with self.assertRaises(ValueError): self.invoke(directory=self.directory / 'retry', factory=self.fake())
        self.assertEqual(len(self.calls), 1)

    def test_fake_publication_exact_deadline_and_late_boundary(self):
        original_stamp = capture._stamp; original_append = self.ledger.append
        for ordinal, seconds_after, expected in [(1, 0, True), (2, .001, False)]:
            observations = []; after_commit = []
            def stamp():
                value = original_stamp()
                if after_commit:
                    due = datetime.fromisoformat(self.timing['artifact_due']) + timedelta(seconds=seconds_after)
                    origin = observations[1]
                    value = {'utc': due.isoformat(), 'monotonic': origin['monotonic'] +
                             (due - datetime.fromisoformat(origin['utc'])).total_seconds()}
                observations.append(value)
                return value
            def append(kind, *args, **kwargs):
                value = original_append(kind, *args, **kwargs)
                if kind == 'prospective_capture_finished': after_commit.append(True)
                return value
            with patch.object(capture, '_stamp', side_effect=stamp), patch.object(self.ledger, 'append', side_effect=append):
                result = self.invoke(binding={**self.binding, 'channel_id': 'boundary-' + str(ordinal)},
                    directory=self.directory / ('channel-' + str(ordinal)), factory=self.fake(stdout=b'complete'))
            self.assertTrue(result['publication_clock_verified'])
            self.assertIs(result['publication_by_artifact_due'], expected)

    def test_fake_intermediate_clock_jump_remains_visible_after_return(self):
        original = capture._stamp; calls = []
        def stamp():
            value = original(); calls.append(1)
            if len(calls) == 10:
                value['utc'] = (datetime.fromisoformat(value['utc']) + timedelta(seconds=4)).isoformat()
            return value
        with patch.object(capture, '_stamp', side_effect=stamp):
            result = self.invoke(factory=self.fake(stdout=b'one'))
        self.assertFalse(result['publication_clock_verified'])

    def test_fake_receipt_durable_clock_jump_not_hidden_by_aligned_end(self):
        original = capture._write_new
        def write(path, raw, **kwargs):
            stamp = original(path, raw, **kwargs)
            if Path(path).name == 'receipt.json':
                stamp['utc'] = (datetime.fromisoformat(stamp['utc']) + timedelta(seconds=4)).isoformat()
            return stamp
        with patch.object(capture, '_write_new', side_effect=write):
            result = self.invoke(factory=self.fake(stdout=b'one'))
        self.assertTrue(result['receipt']['clock_interval_verified'])
        self.assertFalse(result['publication_clock_verified'])

    def test_r8b_real_parent_alarm_verifies_receipt_or_final_deadline_cleanup(self):
        source = b'R8b alarm\nfirst retained attempt\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r8b', 'source_sha256': digest(source)}
        native_kill = os.kill; result = caught = None
        handler = signal.getsignal(signal.SIGALRM); mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        timeout = self.ledger.db.execute('PRAGMA busy_timeout').fetchone()[0]
        facts = {'hook': []}; self.extra['r8b_regression'] = facts
        with self.native_trace() as (native, hooks), self.r3_resource_trace() as (resources, _):
            def alarm_after_spawn(pid):
                facts['hook'].append({'owned_pid': pid, 'self_pid': os.getpid(),
                    'mask': sorted(int(x) for x in signal.pthread_sigmask(signal.SIG_BLOCK, set()))})
                native_kill(os.getpid(), signal.SIGALRM)
            hooks['spawn'] = alarm_after_spawn
            try:
                result = self.invoke(source=source, binding=binding,
                                     timing={**self.timing, 'wall_seconds': .15, 'cleanup_seconds': .5})
            except capture.CaptureDeadline as error:
                caught = error
        events = self.ledger.events(); terminals = [event for event in events if event['kind'] == 'prospective_capture_finished']
        receipt_path = self.directory / 'channel/receipt.json'
        raw = receipt_path.read_bytes() if receipt_path.exists() else None
        saved = None
        if raw:
            try: saved = json.loads(raw)
            except (UnicodeDecodeError, ValueError): pass
        facts.update(branch='returned_receipt' if result is not None else 'final_deadline',
                     final=getattr(caught, 'final', None), terminal_events=len(terminals),
                     receipt_file={'present': raw is not None, 'bytes': len(raw) if raw is not None else None,
                                   'sha256': digest(raw) if raw is not None else None, 'json_valid': saved is not None},
                     caller_handler_restored=signal.getsignal(signal.SIGALRM) is handler,
                     caller_mask_restored=signal.pthread_sigmask(signal.SIG_BLOCK, set()) == mask,
                     timer_disabled=signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
                     caller_timeout=self.ledger.db.execute('PRAGMA busy_timeout').fetchone()[0],
                     caller_transaction=self.ledger.db.in_transaction, caller_append_active=self.ledger._append_active,
                     returned_publication=result['publication_observed'] if result is not None else None)
        self.assertEqual(len(facts['hook']), 1); self.assertEqual(len(native['pids']), 1)
        self.assertEqual(len(native['wait_statuses']), 1); self.assertEqual(native['wait_statuses'][0][0], native['pids'][0])
        status = native['wait_statuses'][0][1]
        self.assertTrue(os.WIFEXITED(status) or os.WIFSIGNALED(status))
        self.assertEqual(native['harness_recovery'], []); self.assertEqual(resources['remaining'], [])
        self.assertTrue(facts['caller_handler_restored']); self.assertTrue(facts['caller_mask_restored']); self.assertTrue(facts['timer_disabled'])
        self.assertEqual(facts['caller_timeout'], timeout); self.assertFalse(facts['caller_transaction']); self.assertFalse(facts['caller_append_active'])
        self.assertEqual(events[0]['kind'], 'prospective_capture_started'); self.assertLessEqual(len(terminals), 1)
        self.assertEqual(len(events), 1 + len(terminals))
        if result is not None:
            self.assertIsNone(caught); self.assertEqual(result['receipt']['termination'], 'parent_deadline')
            self.assertTrue(result['receipt']['child_reaped']); self.assertEqual(result['receipt']['wait_status'], status)
            self.assertFalse(result['receipt']['streams']['stdout']['eof_observed']); self.assertFalse(result['receipt']['streams']['stderr']['eof_observed'])
            self.assertFalse(result['continuation_allowed']); self.assertEqual(len(terminals), 1)
        else:
            self.assertIsInstance(caught, capture.CaptureDeadline); self.assertTrue(caught.final)
            self.assertEqual(self.results, []); self.assertIsNone(facts['returned_publication'])
        if saved is not None:
            self.assertEqual(saved['claim_id'], events[0]['id']); self.assertEqual(saved['claim_hash'], events[0]['hash'])
            self.assertTrue(saved['child_reaped']); self.assertEqual(saved['wait_status'], status)
            self.assertFalse(saved['streams']['stdout']['eof_observed']); self.assertFalse(saved['streams']['stderr']['eof_observed'])
            self.assertIsNone(saved['quality']); self.assertIsNone(saved['obligation_outcome'])
            if result is not None: self.assertEqual(saved, result['receipt'])
        if terminals:
            self.assertIsNotNone(saved); self.assertEqual(terminals[0]['body']['receipt_sha256'], digest(raw))
            self.assertEqual(terminals[0]['body']['claim_id'], events[0]['id']); self.assertEqual(terminals[0]['body']['claim_hash'], events[0]['hash'])


    def test_fake_second_alarm_ends_cleanup_without_retry_or_terminal(self):
        def blocked(*_args, **_kwargs):
            process = FakeProcess()
            def wait(timeout=None): time.sleep(5)
            process.wait = wait
            return process
        with self.assertRaises(capture.CaptureDeadline) as error:
            self.invoke(factory=blocked, timing={**self.timing, 'wall_seconds': .05, 'cleanup_seconds': .05})
        self.assertTrue(error.exception.final)
        self.assertEqual(len(self.ledger.events()), 1)
        self.assertFalse((self.directory / 'channel' / 'receipt.json').exists())
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))

    def test_existing_alarm_refuses_before_claim_and_is_untouched(self):
        previous = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, lambda *_: None); signal.setitimer(signal.ITIMER_REAL, 10)
        try:
            with self.assertRaises(ValueError): self.invoke(factory=self.fake())
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
            self.assertEqual(self.ledger.events(), []); self.assertEqual(self.calls, [])
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, previous)

    def invoke_r1(self, **kwargs):
        source = b'R1 leaf\nnew capture\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r1', 'source_sha256': digest(source)}
        binding.update(kwargs.pop('binding_changes', {}))
        return self.invoke(source=source, binding=binding, **kwargs)

    def test_r1_real_exact_output_and_firstness(self):
        result = self.invoke_r1(); stream = result['receipt']['streams']['stdout']
        expected = canonical({'lines': [{'start': 0, 'end': 8, 'sha256': digest(b'R1 leaf\n')},
                                       {'start': 8, 'end': 20, 'sha256': digest(b'new capture\n')}],
            'schema_version': 1, 'source_byte_length': 20, 'source_sha256': digest(b'R1 leaf\nnew capture\n')}).encode()
        self.assertEqual(Path(stream['path']).read_bytes(), expected)
        self.assertEqual(result['receipt']['wait_status'], 0); self.assertTrue(result['receipt']['child_reaped'])
        self.assertEqual(result['receipt']['returncode'], 0)
        with self.assertRaises(ValueError):
            self.invoke_r1(binding_changes={'acceptance_sha256': 'b' * 64}, directory=self.directory / 'second')
        self.assertEqual(len(self.calls), 1); self.assertEqual(len(self.ledger.events()), 2)

    def test_r1_real_pending_alarm_after_native_spawn_retains_owned_pid(self):
        native = os.posix_spawn; launched = []
        def spawn(*args, **kwargs):
            pid = native(*args, **kwargs); launched.append(pid)
            self.assertIn(signal.SIGALRM, signal.pthread_sigmask(signal.SIG_BLOCK, set()))
            os.kill(os.getpid(), signal.SIGALRM)
            self.assertIn(signal.SIGALRM, signal.sigpending())
            return pid
        previous = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        with patch.object(capture.os, 'posix_spawn', side_effect=spawn):
            result = self.invoke_r1()
        self.assertEqual(result['receipt']['pid'], launched[0]); self.assertTrue(result['receipt']['spawn_returned'])
        self.assertTrue(result['receipt']['child_reaped']); self.assertIsNotNone(result['receipt']['wait_status'])
        self.assertIn(result['receipt']['returncode'], {0, -signal.SIGKILL})
        self.assertEqual(result['receipt']['termination'], 'parent_deadline')
        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, set()), previous)

    def test_r1_real_pending_alarm_after_wait_preserves_actual_status(self):
        native = os.waitpid; statuses = []
        def wait(pid, options):
            answer = native(pid, options)
            if answer[0] == pid:
                statuses.append(answer)
                self.assertIn(signal.SIGALRM, signal.pthread_sigmask(signal.SIG_BLOCK, set()))
                os.kill(os.getpid(), signal.SIGALRM)
            return answer
        with patch.object(capture.os, 'waitpid', side_effect=wait):
            result = self.invoke_r1()
        self.assertEqual(len(statuses), 1)
        self.assertEqual(result['receipt']['wait_status'], statuses[0][1])
        self.assertEqual(result['receipt']['returncode'], 0); self.assertTrue(result['receipt']['child_reaped'])
        self.assertEqual(result['receipt']['termination'], 'parent_deadline')

    def test_r1_fake_middle_read_clock_violation_is_sticky(self):
        self._r1_clock_read_control(eof=False)

    def test_r1_fake_eof_read_clock_violation_is_sticky(self):
        self._r1_clock_read_control(eof=True)

    def _r1_clock_read_control(self, *, eof):
        native_read = os.read; native_stamp = capture._stamp
        reads = []; target = []; inject = []
        def read(fd, amount):
            raw = native_read(fd, amount)
            if raw.startswith(b'M') and not target: target.append(fd)
            if target and fd == target[0]:
                reads.append(len(raw))
                if (eof and not raw) or (not eof and len(reads) == 2): inject.append(True)
            return raw
        def stamp():
            value = native_stamp()
            if inject:
                inject.pop()
                value['utc'] = (datetime.fromisoformat(value['utc']) + timedelta(seconds=4)).isoformat()
            return value
        with patch.object(capture.os, 'read', side_effect=read), patch.object(capture, '_stamp', side_effect=stamp):
            result = self.invoke_r1(factory=self.fake(stdout=b'M' * (17 if eof else 20000)))
        self.assertFalse(result['publication_clock_verified'])
        self.assertGreaterEqual(result['publication_clock_observations']['violation_count'], 1)
        self.assertIsNotNone(result['publication_clock_observations']['first_violation'])
        self.assertTrue(result['receipt']['streams']['stdout']['retention_verified'])

    def test_r1_fake_unavailable_wait_never_synthesizes_exit_or_signal(self):
        waits = []
        def wait(pid, options):
            self.assertEqual(pid, 900000001); self.assertEqual(options, os.WNOHANG)
            waits.append(pid); raise ChildProcessError('invented unavailable owned status')
        with patch.object(capture.os, 'waitpid', side_effect=wait):
            result = self.invoke_r1(factory=self.fake(stdout=b'available bytes'), native_wait=True)
        receipt = result['receipt']
        self.assertEqual(waits, [900000001]); self.assertFalse(receipt['child_reaped'])
        self.assertIsNone(receipt['returncode']); self.assertIsNone(receipt['wait_status'])
        self.assertTrue(receipt['wait_status_unavailable'])
        self.assertEqual(receipt['termination'], 'wait_status_unavailable')
        self.assertEqual(self.calls[-1].get('kill_calls', 0), 0)

    def test_r1_fake_receipt_clock_violation_is_sticky(self):
        original = capture._write_new
        def write(path, raw, **kwargs):
            value = original(path, raw, **kwargs)
            if Path(path).name == 'receipt.json':
                value['utc'] = (datetime.fromisoformat(value['utc']) + timedelta(seconds=4)).isoformat()
            return value
        with patch.object(capture, '_write_new', side_effect=write):
            result = self.invoke_r1(factory=self.fake(stdout=b'R1 receipt'))
        self.assertFalse(result['publication_clock_verified'])
        self.assertEqual(result['publication_clock_observations']['violation_count'], 1)

    def test_r1_preflight_rejects_signal_and_descriptor_conflicts(self):
        previous_handler = signal.getsignal(signal.SIGCHLD)
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        try:
            with self.assertRaises(ValueError): self.invoke_r1()
        finally: signal.signal(signal.SIGCHLD, previous_handler)
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        try:
            with self.assertRaises(ValueError): self.invoke_r1()
        finally: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        with patch.object(capture.signal, 'sigpending', return_value={signal.SIGALRM}):
            with self.assertRaises(ValueError): self.invoke_r1()
        original_stat = os.fstat
        def missing_stdin(fd):
            if fd == 0: raise OSError(9, 'invented missing standard descriptor')
            return original_stat(fd)
        with patch.object(capture.os, 'fstat', side_effect=missing_stdin):
            with self.assertRaises(OSError): self.invoke_r1()
        reading, writing = os.pipe()
        try:
            os.set_inheritable(reading, True)
            with self.assertRaises(ValueError): self.invoke_r1()
            self.assertTrue(os.get_inheritable(reading))
        finally: os.close(reading); os.close(writing)
        self.assertEqual(self.calls, []); self.assertEqual(self.ledger.events(), [])

    def test_r1_fake_spawn_failure_retains_claim_and_closes_owned_fds(self):
        before = set(os.listdir('/dev/fd'))
        def failed(): raise OSError('invented R1 native spawn refusal')
        result = self.invoke_r1(factory=failed)
        self.assertEqual(set(os.listdir('/dev/fd')), before)
        self.assertIsNone(result['receipt']['pid']); self.assertFalse(result['receipt']['spawn_returned'])
        self.assertFalse(result['receipt']['child_reaped']); self.assertIsNone(result['receipt']['wait_status'])
        self.assertEqual(len(self.ledger.events()), 2)

    def test_r1_fake_stderr_overflow_remains_separate(self):
        result = self.invoke_r1(factory=self.fake(stdout=b'R1 complete', stderr=b'E' * 16385))
        self.assertEqual(result['receipt']['termination'], 'stderr_overflow')
        self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), b'R1 complete')
        self.assertEqual(result['receipt']['streams']['stderr']['retained_bytes'], 16384)
        self.assertIsNone(result['receipt']['quality']); self.assertFalse(result['continuation_allowed'])

    def invoke_r2(self, **kwargs):
        source = b'R2 owned\nnew evidence\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r2', 'source_sha256': digest(source)}
        binding.update(kwargs.pop('binding_changes', {}))
        return self.invoke(source=source, binding=binding, **kwargs)

    @contextmanager
    def native_trace(self):
        spawn, wait, kill = os.posix_spawn, os.waitpid, os.kill
        data = {'pids': [], 'wait_statuses': [], 'signals': [], 'harness_recovery': []}; hooks = {}
        self.extra['native'] = data
        def tracked_spawn(*args, **kwargs):
            pid = spawn(*args, **kwargs); data['pids'].append(pid)
            if 'spawn' in hooks: hooks['spawn'](pid)
            return pid
        def tracked_wait(pid, flags):
            result = wait(pid, flags)
            if result[0] == pid:
                data['wait_statuses'].append(list(result))
                if 'wait' in hooks: hooks['wait'](pid, result[1])
            return result
        def tracked_kill(pid, number):
            if pid != os.getpid() and pid not in data['pids']: raise AssertionError('unowned signal target')
            data['signals'].append({'pid': pid, 'signal': number})
            return kill(pid, number)
        try:
            with patch.object(capture.os, 'posix_spawn', side_effect=tracked_spawn), \
                 patch.object(capture.os, 'waitpid', side_effect=tracked_wait), \
                 patch.object(capture.os, 'kill', side_effect=tracked_kill):
                yield data, hooks
        finally:
            for pid in data['pids']:
                try: result = wait(pid, os.WNOHANG)
                except ChildProcessError: continue
                data['harness_recovery'].append({'pid': pid, 'initial_wait': list(result)})
                if result[0] == 0:
                    kill(pid, signal.SIGKILL)
                    end = time.monotonic() + 1
                    while time.monotonic() < end:
                        result = wait(pid, os.WNOHANG)
                        if result[0] == pid: break
                        time.sleep(.005)
                    self.assertEqual(result[0], pid)

    def fd_identity(self, fd):
        try:
            value = os.fstat(fd)
            return [value.st_dev, value.st_ino, value.st_mode]
        except OSError: return None

    def check_retired(self, owned):
        leaks = []
        for fd, identity in owned:
            if self.fd_identity(fd) == identity:
                leaks.append(fd); os.close(fd)
        self.extra['owned_fd_leaks_before_harness_close'] = leaks
        self.assertEqual(leaks, [])

    def test_r2_real_literal_transport_and_firstness(self):
        with self.native_trace() as (data, _hooks):
            result = self.invoke_r2()
        raw = canonical({'lines': [{'start': 0, 'end': 9, 'sha256': digest(b'R2 owned\n')},
                                  {'start': 9, 'end': 22, 'sha256': digest(b'new evidence\n')}],
                         'schema_version': 1, 'source_byte_length': 22,
                         'source_sha256': digest(b'R2 owned\nnew evidence\n')}).encode()
        self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), raw)
        self.assertEqual(result['receipt']['wait_status'], 0); self.assertEqual(data['harness_recovery'], [])
        with self.assertRaises(ValueError):
            self.invoke_r2(binding_changes={'question_id': 'changed'}, directory=self.directory / 'second')
        self.assertEqual(len(self.calls), 1); self.assertFalse(result['continuation_allowed'])

    def test_r2_real_sigint_spawn_handoff_propagates_after_owned_cleanup(self):
        with self.native_trace() as (data, hooks):
            def interrupt(_pid):
                self.assertTrue({signal.SIGALRM, signal.SIGINT}.issubset(signal.pthread_sigmask(signal.SIG_BLOCK, set())))
                os.kill(os.getpid(), signal.SIGINT)
            hooks['spawn'] = interrupt
            with self.assertRaises(KeyboardInterrupt): self.invoke_r2()
        self.assertEqual(len(data['wait_statuses']), 1); self.assertEqual(data['harness_recovery'], [])
        self.assertEqual(data['wait_statuses'][0][0], data['pids'][0]); self.assertEqual(len(self.ledger.events()), 1)

    def test_r2_real_sigint_wait_handoff_keeps_actual_status(self):
        with self.native_trace() as (data, hooks):
            hooks['wait'] = lambda _pid, _status: os.kill(os.getpid(), signal.SIGINT)
            with self.assertRaises(KeyboardInterrupt): self.invoke_r2()
        self.assertEqual(data['wait_statuses'], [[data['pids'][0], 0]])
        self.assertEqual(data['harness_recovery'], [])
        self.assertFalse(any(row['pid'] != os.getpid() for row in data['signals']))

    def test_r2_real_pipe_acquisition_alarm_retires_both_fds(self):
        native = os.pipe; owned = []
        def pipe():
            pair = native()
            if not owned:
                owned.extend((fd, self.fd_identity(fd)) for fd in pair)
                os.kill(os.getpid(), signal.SIGALRM)
            return pair
        with patch.object(capture.os, 'pipe', side_effect=pipe): result = self.invoke_r2()
        self.check_retired(owned)
        self.assertEqual(self.calls, []); self.assertEqual(result['receipt']['termination'], 'parent_deadline')

    def test_r2_real_pipe_close_alarm_does_not_lose_owner(self):
        native = os.close; target = []; owned = []; fired = []
        with self.native_trace() as (data, hooks):
            native_spawn = os.posix_spawn
            def spawn(path, args, env, **kwargs):
                writes = [row[1] for row in kwargs['file_actions'] if row[0] == os.POSIX_SPAWN_DUP2 and row[2] == 1]
                target.extend(writes); owned.extend((fd, self.fd_identity(fd)) for fd in writes)
                return native_spawn(path, args, env, **kwargs)
            def close(fd):
                if fd in target and not fired:
                    fired.append(fd); os.kill(os.getpid(), signal.SIGALRM)
                return native(fd)
            with patch.object(capture.os, 'posix_spawn', side_effect=spawn), patch.object(capture.os, 'close', side_effect=close):
                result = self.invoke_r2()
        self.check_retired(owned); self.assertEqual(data['harness_recovery'], [])
        self.assertTrue(result['receipt']['child_reaped']); self.assertEqual(result['receipt']['errors'], [])

    def test_r2_real_file_and_directory_acquisition_alarm_closes_owners(self):
        native = os.open
        for ordinal, kind in enumerate(['source', 'directory'], 1):
            owned = []
            def opening(path, flags, *args, **kwargs):
                fd = native(path, flags, *args, **kwargs)
                match = (Path(path).name == 'source.bin' and flags & os.O_WRONLY) if kind == 'source' else flags & os.O_DIRECTORY
                if match and not owned:
                    owned.append((fd, self.fd_identity(fd))); os.kill(os.getpid(), signal.SIGALRM)
                return fd
            with patch.object(capture.os, 'open', side_effect=opening):
                result = self.invoke_r2(binding_changes={'channel_id': 'acquire-' + kind}, directory=self.directory / ('channel-' + str(ordinal)))
            self.check_retired(owned); self.assertEqual(result['receipt']['termination'], 'parent_deadline')
        self.assertEqual(self.calls, [])

    def test_r2_uncertain_close_never_retries_reused_numeric_fd(self):
        native_close, native_open = os.close, os.open
        target = []; sentinel = []; fired = []
        marker = self.directory / 'caller-marker'; marker.write_bytes(b'caller-owned')
        with self.native_trace() as (data, _hooks):
            native_spawn = os.posix_spawn
            def spawn(path, args, env, **kwargs):
                target.extend(row[1] for row in kwargs['file_actions'] if row[0] == os.POSIX_SPAWN_DUP2 and row[2] == 1)
                return native_spawn(path, args, env, **kwargs)
            def close(fd):
                if fd in target and not fired:
                    fired.append(fd); native_close(fd)
                    replacement = native_open(marker, os.O_RDONLY); sentinel.append(replacement)
                    self.assertEqual(replacement, fd)
                    raise OSError(5, 'invented uncertain close result')
                return native_close(fd)
            try:
                with patch.object(capture.os, 'posix_spawn', side_effect=spawn), patch.object(capture.os, 'close', side_effect=close):
                    result = self.invoke_r2()
                self.assertIsNotNone(self.fd_identity(sentinel[0]))
                self.assertTrue(any(row.get('native_close_uncertain') for row in result['receipt']['errors']))
            finally:
                for fd in sentinel:
                    if self.fd_identity(fd) is not None: native_close(fd)
        self.assertEqual(data['harness_recovery'], [])

    def test_r2_final_receipt_alarm_closes_fd_without_later_writes(self):
        native_open, native_write = os.open, os.write
        owned = []; fired = []; later_writes = []
        def opening(path, flags, *args, **kwargs):
            fd = native_open(path, flags, *args, **kwargs)
            if Path(path).name == 'receipt.json' and not fired:
                owned.append((fd, self.fd_identity(fd))); fired.append(True); os.kill(os.getpid(), signal.SIGALRM)
            return fd
        def write(fd, raw):
            if fired: later_writes.append(len(raw))
            return native_write(fd, raw)
        with self.native_trace() as (data, _hooks):
            with patch.object(capture.os, 'open', side_effect=opening), patch.object(capture.os, 'write', side_effect=write):
                with self.assertRaises(capture.CaptureDeadline) as error: self.invoke_r2()
        self.assertTrue(error.exception.final); self.check_retired(owned)
        self.assertEqual(later_writes, []); self.assertEqual(data['harness_recovery'], [])
        self.assertEqual(len(self.ledger.events()), 1)

    def test_r2_normal_cleanup_has_only_one_short_reserve(self):
        original = capture._sync_directory
        def slow(path, **kwargs):
            if self.in_capture_cleanup(): time.sleep(2)
            return original(path, **kwargs)
        began = time.monotonic()
        with self.native_trace() as (data, _hooks), patch.object(capture, '_sync_directory', side_effect=slow):
            with self.assertRaises(capture.CaptureDeadline) as error:
                self.invoke_r2(timing={**self.timing, 'cleanup_seconds': .05})
        elapsed = time.monotonic() - began; self.extra['reserve_elapsed'] = elapsed
        self.assertTrue(error.exception.final); self.assertLess(elapsed, .8)
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(len(self.ledger.events()), 1)

    def test_r2_keyboard_interrupt_keeps_short_cleanup_reserve_and_propagates(self):
        original = capture._sync_directory
        def slow(path, **kwargs):
            if self.in_capture_cleanup(): time.sleep(2)
            return original(path, **kwargs)
        began = time.monotonic()
        with self.native_trace() as (data, hooks), patch.object(capture, '_sync_directory', side_effect=slow):
            hooks['spawn'] = lambda _pid: os.kill(os.getpid(), signal.SIGINT)
            with self.assertRaises(KeyboardInterrupt):
                self.invoke_r2(timing={**self.timing, 'cleanup_seconds': .05})
        elapsed = time.monotonic() - began; self.extra['reserve_elapsed'] = elapsed
        self.assertLess(elapsed, .8); self.assertEqual(data['harness_recovery'], [])
        self.assertEqual(len(self.ledger.events()), 1)

    def test_r2_fake_nonzero_binary_and_overflow_are_separate_facts(self):
        result = self.invoke_r2(factory=self.fake(stdout=b'R2\x00binary', stderr=b'diagnostic', code=7))
        self.assertEqual(result['receipt']['returncode'], 7)
        self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), b'R2\x00binary')
        self.assertTrue(result['receipt']['streams']['stdout']['retention_verified'])
        self.assertIsNone(result['receipt']['quality'])
        overflow = self.invoke_r2(binding_changes={'channel_id': 'overflow'}, directory=self.directory / 'overflow',
                                  factory=self.fake(stdout=b'Q' * 65537, stderr=b'R2'))
        self.assertEqual(overflow['receipt']['streams']['stdout']['retained_bytes'], 65536)
        self.assertIsNone(overflow['receipt']['streams']['stdout']['full_sha256'])
        self.assertFalse(overflow['receipt']['streams']['stdout']['complete_bytes_observed'])

    def test_r2_fake_unknown_status_and_transient_clock_stay_uncertain(self):
        def missing(pid, flags):
            self.assertEqual(pid, 900000001); raise ChildProcessError('R2 unavailable status')
        with patch.object(capture.os, 'waitpid', side_effect=missing):
            result = self.invoke_r2(factory=self.fake(stdout=b'R2 unknown'), native_wait=True)
        self.assertFalse(result['receipt']['child_reaped']); self.assertIsNone(result['receipt']['returncode'])
        self.assertEqual(self.calls[-1].get('kill_calls', 0), 0)
        original_read, original_stamp = os.read, capture._stamp
        reads = []; inject = []; used = []
        def read(fd, size):
            raw = original_read(fd, size)
            if raw.startswith(b'Z'):
                reads.append(len(raw))
                if len(reads) == 2 and not used: inject.append(True); used.append(True)
            return raw
        def stamp():
            value = original_stamp()
            if inject:
                inject.pop(); value['utc'] = (datetime.fromisoformat(value['utc']) + timedelta(seconds=3)).isoformat()
            return value
        with patch.object(capture.os, 'read', side_effect=read), patch.object(capture, '_stamp', side_effect=stamp):
            clock = self.invoke_r2(binding_changes={'channel_id': 'clock'}, directory=self.directory / 'clock',
                                   factory=self.fake(stdout=b'Z' * 20000))
        self.assertFalse(clock['publication_clock_verified'])
        self.assertEqual(clock['publication_clock_observations']['violation_count'], 1)

    def test_r2_preflight_refuses_unsupported_sigint_state(self):
        previous = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            with self.assertRaises(ValueError): self.invoke_r2()
        finally: signal.signal(signal.SIGINT, previous)
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
        try:
            with self.assertRaises(ValueError): self.invoke_r2()
        finally: signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        self.assertEqual(self.calls, []); self.assertEqual(self.ledger.events(), [])

    def in_capture_cleanup(self):
        frame = sys._getframe(1)
        for _ in range(16):
            if frame is None: return False
            if frame.f_code.co_name == 'cleanup' and frame.f_code.co_filename == capture.__file__: return True
            frame = frame.f_back
        return False

    def test_r2b_fresh_normal_cleanup_delay_is_bounded_once(self):
        self._fresh_reserve_control(interrupt=False)

    def test_r2b_fresh_sigint_cleanup_delay_propagates_keyboard_interrupt(self):
        self._fresh_reserve_control(interrupt=True)

    def _fresh_reserve_control(self, *, interrupt):
        source = b'Reserve follow-up\nfresh bytes\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r2b', 'source_sha256': digest(source)}
        original_sync = capture._sync_directory
        native_open, native_pipe, native_close = os.open, os.pipe, os.close
        active = {}; retired = []; fired = []
        def opened(path, flags, *args, **kwargs):
            fd = native_open(path, flags, *args, **kwargs)
            active[fd] = self.fd_identity(fd)
            return fd
        def piped():
            pair = native_pipe()
            for fd in pair: active[fd] = self.fd_identity(fd)
            return pair
        def closed(fd):
            identity = active.get(fd)
            result = native_close(fd)
            if identity is not None:
                retired.append({'fd': fd, 'identity': identity})
                del active[fd]
            return result
        def slow(path, **kwargs):
            if self.in_capture_cleanup():
                fired.append({'monotonic': time.monotonic(), 'remaining_alarm': signal.getitimer(signal.ITIMER_REAL)[0]})
                time.sleep(2)
            return original_sync(path, **kwargs)
        began = time.monotonic()
        with self.native_trace() as (data, hooks):
            if interrupt: hooks['spawn'] = lambda _pid: os.kill(os.getpid(), signal.SIGINT)
            with patch.object(capture.os, 'open', side_effect=opened), \
                 patch.object(capture.os, 'pipe', side_effect=piped), \
                 patch.object(capture.os, 'close', side_effect=closed), \
                 patch.object(capture, '_sync_directory', side_effect=slow):
                expected = KeyboardInterrupt if interrupt else capture.CaptureDeadline
                with self.assertRaises(expected) as error:
                    self.invoke(source=source, binding=binding, timing={**self.timing, 'cleanup_seconds': .05})
        elapsed = time.monotonic() - began
        self.extra.update(delay_hook=fired, reserve_elapsed=elapsed, retired_owned_descriptors=retired,
                          remaining_owned_descriptors=active, interrupt_type=type(error.exception).__name__)
        self.assertEqual(len(fired), 1); self.assertGreater(fired[0]['remaining_alarm'], 0)
        self.assertLessEqual(fired[0]['remaining_alarm'], .05)
        self.assertLess(elapsed, .8); self.assertEqual(active, {})
        self.assertTrue(retired); self.assertEqual(data['harness_recovery'], [])
        self.assertEqual(len(self.ledger.events()), 1)
        if not interrupt: self.assertTrue(error.exception.final)

    def invoke_r3(self, **kwargs):
        source = b'R3 cleanup\nremaining work\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r3', 'source_sha256': digest(source)}
        return self.invoke(source=source, binding=binding, **kwargs)

    @contextmanager
    def r3_resource_trace(self):
        native_open, native_pipe, native_close, native_write = os.open, os.pipe, os.close, os.write
        data = {'active': {}, 'retired': [], 'remaining': [], 'after_final_writes': [], 'hooks': []}
        hooks = {}; self.extra['resources'] = data
        def opened(path, flags, *args, **kwargs):
            fd = native_open(path, flags, *args, **kwargs)
            data['active'][fd] = {'identity': self.fd_identity(fd), 'path': str(path)}
            return fd
        def piped():
            pair = native_pipe()
            for fd in pair: data['active'][fd] = {'identity': self.fd_identity(fd), 'path': 'owned-pipe'}
            return pair
        def closed(fd):
            owned = data['active'].get(fd)
            result = native_close(fd)
            if owned is not None:
                data['retired'].append({'fd': fd, **owned}); del data['active'][fd]
                if 'close' in hooks: hooks['close'](owned)
            return result
        def written(fd, raw):
            if data.get('final_pending'): data['after_final_writes'].append({'fd': fd, 'bytes': len(raw)})
            return native_write(fd, raw)
        try:
            with patch.object(capture.os, 'open', side_effect=opened), \
                 patch.object(capture.os, 'pipe', side_effect=piped), \
                 patch.object(capture.os, 'close', side_effect=closed), \
                 patch.object(capture.os, 'write', side_effect=written):
                yield data, hooks
        finally:
            for fd, owned in data['active'].items():
                if self.fd_identity(fd) == owned['identity']:
                    data['remaining'].append({'fd': fd, **owned}); native_close(fd)

    def r3_stop_owned_child(self, hooks, native_wait):
        def stopped(pid):
            os.kill(pid, signal.SIGSTOP)
            end = time.monotonic() + .5
            while time.monotonic() < end:
                waited, status = native_wait(pid, os.WNOHANG | os.WUNTRACED)
                if waited:
                    self.extra['owned_stop_status'] = [waited, status]
                    self.assertTrue(os.WIFSTOPPED(status)); return
                time.sleep(.002)
            self.fail('exact owned child did not report stopped state')
        hooks['spawn'] = stopped

    def test_r3_real_first_sigint_during_child_cleanup_resumes_within_reserve(self):
        original_write, original_wait = capture._write_new, os.waitpid; fired = []
        def failed_start(path, raw, **kwargs):
            if Path(path).name == 'start.json': raise OSError('R3 invented start retention refusal')
            return original_write(path, raw, **kwargs)
        with self.native_trace() as (data, hooks), self.r3_resource_trace() as (resources, _):
            self.r3_stop_owned_child(hooks, original_wait)
            native_wait = os.waitpid
            def waited(pid, flags):
                result = native_wait(pid, flags)
                if self.in_capture_cleanup() and result == (0, 0) and not fired:
                    fired.append({'pid': pid, 'remaining_alarm': signal.getitimer(signal.ITIMER_REAL)[0]})
                    os.kill(os.getpid(), signal.SIGINT)
                return result
            with patch.object(capture, '_write_new', side_effect=failed_start), \
                 patch.object(capture.os, 'waitpid', side_effect=waited):
                with self.assertRaises(KeyboardInterrupt): self.invoke_r3()
        self.extra['cleanup_wait_hook'] = fired
        self.assertEqual(len(fired), 1); self.assertGreater(fired[0]['remaining_alarm'], 0)
        self.assertLessEqual(fired[0]['remaining_alarm'], self.timing['cleanup_seconds'])
        self.assertEqual(data['wait_statuses'], [[data['pids'][0], signal.SIGKILL]])
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(resources['remaining'], [])
        self.assertEqual(len(self.ledger.events()), 1)

    def test_r3_real_first_deadline_at_cleanup_admission_retires_child(self):
        original_capture, original_write, original_wait = capture._capture, capture._write_new, os.waitpid; fired = []
        def wrapped(ledger, claim, source, producer, directory, enter_cleanup, **kwargs):
            def admission():
                if not fired:
                    fired.append({'remaining_execution_alarm': signal.getitimer(signal.ITIMER_REAL)[0]})
                    time.sleep(.4)
                return enter_cleanup()
            return original_capture(ledger, claim, source, producer, directory, admission, **kwargs)
        def failed_start(path, raw, **kwargs):
            if Path(path).name == 'start.json': raise OSError('R3 distinct admission retention refusal')
            return original_write(path, raw, **kwargs)
        with self.native_trace() as (data, hooks), self.r3_resource_trace() as (resources, _):
            self.r3_stop_owned_child(hooks, original_wait)
            with patch.object(capture, '_capture', side_effect=wrapped), \
                 patch.object(capture, '_write_new', side_effect=failed_start):
                result = self.invoke_r3(timing={**self.timing, 'wall_seconds': .15})
        self.extra['cleanup_admission_hook'] = fired
        self.assertEqual(len(fired), 1); self.assertGreater(fired[0]['remaining_execution_alarm'], 0)
        self.assertEqual(result['receipt']['termination'], 'parent_deadline')
        self.assertEqual(result['receipt']['wait_status'], signal.SIGKILL)
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(resources['remaining'], [])
        self.assertEqual(len(self.ledger.events()), 2)

    def test_r3_fake_cleanup_sigint_survives_final_close_deadline(self):
        self._close_priority_control(b'R3 cleanup\nremaining work\n', 'invented-c23-r3', b'R3 fake retained bytes')

    def test_r3b_fresh_cleanup_sigint_keeps_priority_after_final_close(self):
        self._close_priority_control(b'Priority follow-up\nkept interruption\n',
                                     'invented-c23-r3b', b'R3b kept interruption')

    def _close_priority_control(self, source, instance, output):
        original_sync, native_kill = capture._sync_directory, os.kill; fired = []
        binding = {**self.binding, 'instance_id': instance, 'source_sha256': digest(source)}
        with self.r3_resource_trace() as (resources, hooks):
            def interrupted_sync(path, **kwargs):
                if self.in_capture_cleanup() and not fired:
                    fired.append({'remaining_alarm': signal.getitimer(signal.ITIMER_REAL)[0],
                                  'target_pid': os.getpid(), 'signal': signal.SIGINT})
                    native_kill(os.getpid(), signal.SIGINT)
                return original_sync(path, **kwargs)
            def closing(owned):
                if fired and Path(owned['path']).name == 'stdout.bin' and not resources['hooks']:
                    resources['hooks'].append({'remaining_alarm': signal.getitimer(signal.ITIMER_REAL)[0]})
                    time.sleep(.12)
                    resources['final_pending'] = signal.SIGALRM in signal.sigpending()
            hooks['close'] = closing
            with patch.object(capture, '_sync_directory', side_effect=interrupted_sync):
                with self.assertRaises(KeyboardInterrupt) as error:
                    self.invoke(source=source, binding=binding, factory=self.fake(stdout=output),
                                timing={**self.timing, 'cleanup_seconds': .06})
        self.extra['cleanup_sync_hook'] = fired
        self.extra['propagated_interrupt'] = type(error.exception).__name__
        self.assertEqual(len(fired), 1); self.assertGreater(fired[0]['remaining_alarm'], 0)
        self.assertEqual(len(resources['hooks']), 1); self.assertGreater(resources['hooks'][0]['remaining_alarm'], 0)
        self.assertTrue(resources['final_pending']); self.assertEqual(resources['after_final_writes'], [])
        self.assertEqual(resources['remaining'], []); self.assertEqual(len(self.ledger.events()), 1)

    def invoke_r4(self):
        source = b'R4 signal\nretirement\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r4', 'source_sha256': digest(source)}
        return self.invoke(source=source, binding=binding)

    def in_wall_retirement(self):
        frame = sys._getframe(1)
        for _ in range(16):
            if frame is None: return False
            if frame.f_code.co_name == '_wall_bound' and frame.f_code.co_filename == capture.__file__ and frame.f_locals.get('retiring') is True: return True
            frame = frame.f_back
        return False

    def test_r4_real_installation_sigint_restores_caller_handler(self):
        self._r4_signal_boundary('install')

    def test_r4_real_retirement_sigint_restores_caller_handler(self):
        self._r4_signal_boundary('retire_int')

    def test_r4_real_pending_owned_alarm_survives_retirement(self):
        self._r4_signal_boundary('retire_alarm')

    def test_r4_real_pending_alarm_keeps_sigint_priority_at_retirement(self):
        self._r4_signal_boundary('retire_both')

    def _r4_signal_boundary(self, mode):
        native_signal, native_timer, native_kill = signal.signal, signal.setitimer, os.kill
        original_handler = signal.getsignal(signal.SIGALRM)
        original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        facts = {'hooks': [], 'caller_handler_calls': [], 'harness_handler_recovery': False}
        self.extra['signal_boundary'] = facts
        def caller_handler(number, _frame): facts['caller_handler_calls'].append(number)
        def send_hook():
            row = {'target_pid': os.getpid(), 'mask': sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, set())),
                   'signals': []}; facts['hooks'].append(row)
            if mode != 'retire_alarm':
                row['signals'].append(int(signal.SIGINT)); native_kill(os.getpid(), signal.SIGINT)
            if mode in {'retire_alarm', 'retire_both'}:
                row['signals'].append(int(signal.SIGALRM)); native_kill(os.getpid(), signal.SIGALRM)
                row['owned_alarm_pending'] = signal.SIGALRM in signal.sigpending()
        def installed(number, handler):
            result = native_signal(number, handler)
            if mode == 'install' and number == signal.SIGALRM and getattr(handler, '__name__', None) == 'alarm' and not facts['hooks']:
                send_hook()
            return result
        def timed(which, seconds, *args):
            result = native_timer(which, seconds, *args)
            if mode != 'install' and seconds == 0 and self.in_wall_retirement() and not facts['hooks']:
                send_hook()
            return result
        native_signal(signal.SIGALRM, caller_handler)
        try:
            with self.native_trace() as (data, _), self.r3_resource_trace() as (resources, _):
                with patch.object(capture.signal, 'signal', side_effect=installed), \
                     patch.object(capture.signal, 'setitimer', side_effect=timed):
                    expected = capture.CaptureDeadline if mode == 'retire_alarm' else KeyboardInterrupt
                    with self.assertRaises(expected) as error: self.invoke_r4()
            facts.update(propagated=type(error.exception).__name__, final=getattr(error.exception, 'final', None),
                         deadline_evidence=getattr(error.exception, 'capture_deadline', None),
                         pending_alarm_observed=getattr(error.exception, 'pending_alarm_observed', None),
                         handler_restored=signal.getsignal(signal.SIGALRM) is caller_handler,
                         timer_disabled=signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
                         mask_restored=signal.pthread_sigmask(signal.SIG_BLOCK, set()) == original_mask)
        finally:
            facts['harness_handler_recovery'] = signal.getsignal(signal.SIGALRM) is not caller_handler
            native_timer(signal.ITIMER_REAL, 0); native_signal(signal.SIGALRM, original_handler)
        self.assertEqual(len(facts['hooks']), 1)
        self.assertEqual(facts['hooks'][0]['mask'], sorted(int(s) for s in original_mask | {signal.SIGALRM, signal.SIGINT}))
        self.assertTrue(facts['handler_restored']); self.assertTrue(facts['timer_disabled']); self.assertTrue(facts['mask_restored'])
        self.assertFalse(facts['harness_handler_recovery']); self.assertEqual(facts['caller_handler_calls'], [])
        self.assertEqual(resources['remaining'], []); self.assertEqual(data['harness_recovery'], [])
        self.assertEqual(len(self.ledger.events()), 0 if mode == 'install' else 2)
        if mode == 'install': self.assertEqual(data['pids'], [])
        else: self.assertEqual(data['wait_statuses'], [[data['pids'][0], 0]])
        if mode in {'retire_alarm', 'retire_both'}: self.assertTrue(facts['hooks'][0]['owned_alarm_pending'])
        if mode == 'retire_alarm':
            self.assertTrue(facts['final']); self.assertTrue(facts['pending_alarm_observed'])
        if mode == 'retire_both':
            self.assertEqual(facts['deadline_evidence'], {'phase': 'signal_retirement', 'final': True, 'pending_alarm_observed': True,
                            'pending_alarm_observation': {'phase': 'signal_retirement', 'final': True}})

    def test_r4_real_literal_worker_preserves_output_and_signal_state(self):
        self._r4_literal_worker(missing_api=False)

    def test_r4_real_worker_with_labelled_missing_exception_api_simulation(self):
        self._r4_literal_worker(missing_api=True)

    def _r4_literal_worker(self, *, missing_api):
        original_api = getattr(sys, 'exception', None)
        handler = signal.getsignal(signal.SIGALRM)
        self.extra['compatibility'] = {'missing_sys_exception_simulated': missing_api,
                                       'actual_runtime': sys.version, 'python_310_executed': False}
        try:
            if missing_api and hasattr(sys, 'exception'): del sys.exception
            with self.native_trace() as (data, _), self.r3_resource_trace() as (resources, _):
                result = self.invoke_r4()
        finally:
            if original_api is not None: sys.exception = original_api
        expected = canonical({'lines': [{'start': 0, 'end': 10, 'sha256': digest(b'R4 signal\n')},
                                       {'start': 10, 'end': 21, 'sha256': digest(b'retirement\n')}],
                              'schema_version': 1, 'source_byte_length': 21,
                              'source_sha256': digest(b'R4 signal\nretirement\n')}).encode()
        self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), expected)
        self.assertEqual(result['receipt']['wait_status'], 0); self.assertEqual(data['harness_recovery'], [])
        self.assertEqual(resources['remaining'], []); self.assertEqual(signal.getsignal(signal.SIGALRM), handler)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0)); self.assertFalse(result['continuation_allowed'])

    def invoke_r5(self):
        source = b'R5 caller\nowned attempt\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r5', 'source_sha256': digest(source)}
        return self.invoke(source=source, binding=binding)

    def test_r5_real_prior_handled_deadline_does_not_cancel_or_mutate(self):
        self._r5_ambient_control(capture.CaptureDeadline(final=True))

    def test_r5_real_prior_handled_interrupt_does_not_cancel_or_mutate(self):
        self._r5_ambient_control(KeyboardInterrupt('earlier caller work'))

    def test_r5_real_prior_handled_value_error_stays_unrelated(self):
        self._r5_ambient_control(ValueError('earlier distinct input'))

    def test_r5_real_current_interrupt_inside_prior_handler_still_propagates(self):
        self._r5_ambient_control(ValueError('prior caller input'), interrupt=True)

    def _r5_ambient_control(self, prior, *, interrupt=False):
        prior.caller_marker = 'unchanged R5 caller object'
        before = dict(vars(prior)); unexpected = None; result = None
        try:
            raise prior
        except BaseException:
            handled_state = (prior.__traceback__, prior.__context__, prior.__cause__, prior.args)
            with self.native_trace() as (data, hooks), self.r3_resource_trace() as (resources, _):
                if interrupt: hooks['spawn'] = lambda _pid: os.kill(os.getpid(), signal.SIGINT)
                try: result = self.invoke_r5()
                except BaseException as error: unexpected = error
        self.extra['ambient'] = {'prior_type': type(prior).__name__, 'prior_unchanged': vars(prior) == before,
                                 'handled_state_unchanged': handled_state == (prior.__traceback__, prior.__context__, prior.__cause__, prior.args),
                                 'rethrown_prior': unexpected is prior,
                                 'propagated': type(unexpected).__name__ if unexpected else None,
                                 'current_sigint_sent': interrupt}
        self.assertEqual(vars(prior), before); self.assertIsNot(unexpected, prior)
        self.assertEqual(handled_state, (prior.__traceback__, prior.__context__, prior.__cause__, prior.args))
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(resources['remaining'], [])
        self.assertEqual(self.ledger.db.execute('PRAGMA busy_timeout').fetchone()[0], 10000)
        if interrupt:
            self.assertIsInstance(unexpected, KeyboardInterrupt); self.assertEqual(len(self.ledger.events()), 1)
            self.assertEqual(len(data['wait_statuses']), 1)
        else:
            self.assertIsNone(unexpected)
            expected = canonical({'lines': [{'start': 0, 'end': 10, 'sha256': digest(b'R5 caller\n')},
                                           {'start': 10, 'end': 24, 'sha256': digest(b'owned attempt\n')}],
                                  'schema_version': 1, 'source_byte_length': 24,
                                  'source_sha256': digest(b'R5 caller\nowned attempt\n')}).encode()
            self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), expected)
            self.assertEqual(result['receipt']['wait_status'], 0); self.assertEqual(len(self.ledger.events()), 2)

    def test_r5_real_sqlite_timeout_installation_sigint_restores_caller(self):
        self._r5_timeout_control('install')

    def test_r5_real_sqlite_timeout_retirement_sigint_restores_caller(self):
        self._r5_timeout_control('retire')

    def test_r5_real_sqlite_timeout_retirement_admission_sigint_retries(self):
        self._r5_timeout_control('admission')

    def _r5_timeout_control(self, mode):
        connection = self.ledger.db; original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        native_mask, native_kill = signal.pthread_sigmask, os.kill
        original_handler = signal.getsignal(signal.SIGALRM)
        connection.execute('PRAGMA busy_timeout=5371')
        facts = {'hooks': [], 'restore_attempts': [], 'harness_timeout_recovery': False}
        self.extra['timeout_boundary'] = facts
        def retirement_frame():
            frame = sys._getframe(1)
            for _ in range(16):
                if frame is None: return None
                if frame.f_code.co_name == '_nonblocking_ledger' and frame.f_code.co_filename == capture.__file__ and frame.f_locals.get('retiring') is True:
                    return frame
                frame = frame.f_back
            return None
        def send_hook(label):
            facts['hooks'].append({'at': label, 'target_pid': os.getpid(),
                'mask': sorted(int(s) for s in native_mask(signal.SIG_BLOCK, set())),
                'timeout': connection.execute('PRAGMA busy_timeout').fetchone()[0]})
            native_kill(os.getpid(), signal.SIGINT)
        class ConnectionProxy:
            def __getattr__(self, name): return getattr(connection, name)
            def execute(self, statement, *args):
                result = connection.execute(statement, *args)
                if statement == 'PRAGMA busy_timeout=5371':
                    frame = retirement_frame()
                    facts['restore_attempts'].append(frame.f_locals['attempts'] if frame else None)
                target = 'PRAGMA busy_timeout=0' if mode == 'install' else 'PRAGMA busy_timeout=5371'
                if mode != 'admission' and statement == target and not facts['hooks']: send_hook(mode)
                return result
        def masked(how, signals):
            if mode == 'admission' and how == signal.SIG_BLOCK and set(signals) == {signal.SIGALRM, signal.SIGINT} and retirement_frame() is not None and not facts['hooks']:
                send_hook('before_retirement_mask')
            return native_mask(how, signals)
        self.ledger.db = ConnectionProxy()
        try:
            with self.native_trace() as (data, _), self.r3_resource_trace() as (resources, _):
                with patch.object(capture.signal, 'pthread_sigmask', side_effect=masked):
                    with self.assertRaises(KeyboardInterrupt): self.invoke_r5()
            facts.update(restored_timeout=connection.execute('PRAGMA busy_timeout').fetchone()[0],
                         mask_restored=native_mask(signal.SIG_BLOCK, set()) == original_mask,
                         handler_restored=signal.getsignal(signal.SIGALRM) == original_handler,
                         timer_disabled=signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0))
        finally:
            self.ledger.db = connection
            if connection.execute('PRAGMA busy_timeout').fetchone()[0] != 5371:
                facts['harness_timeout_recovery'] = True; connection.execute('PRAGMA busy_timeout=5371')
        self.assertEqual(len(facts['hooks']), 1); self.assertEqual(facts['restored_timeout'], 5371)
        self.assertFalse(facts['harness_timeout_recovery']); self.assertTrue(facts['mask_restored'])
        self.assertTrue(facts['handler_restored']); self.assertTrue(facts['timer_disabled'])
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(resources['remaining'], [])
        self.assertEqual(len(self.ledger.events()), 0 if mode == 'install' else 2)
        if mode == 'admission':
            self.assertEqual(facts['restore_attempts'], [2]); self.assertEqual(facts['hooks'][0]['timeout'], 0)
        else:
            self.assertEqual(facts['restore_attempts'], [1])
            self.assertTrue({int(signal.SIGALRM), int(signal.SIGINT)}.issubset(facts['hooks'][0]['mask']))


    def invoke_r6(self):
        source = b'R6 ownership\nlocal first claim\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r6', 'source_sha256': digest(source)}
        return self.invoke(source=source, binding=binding)

    @contextmanager
    def r6_first_line(self, predicate, facts):
        previous = sys.gettrace(); native_kill = os.kill
        self.assertIsNone(previous)
        def trace(frame, event, _arg):
            if event == 'line' and not facts['hooks'] and predicate(frame):
                facts['hooks'].append({'function': frame.f_code.co_qualname, 'line': frame.f_lineno,
                                       'self_pid': os.getpid(), 'mask': sorted(int(x) for x in signal.pthread_sigmask(signal.SIG_BLOCK, set()))})
                native_kill(os.getpid(), signal.SIGINT)
            return trace
        sys.settrace(trace)
        try: yield
        finally: sys.settrace(previous)

    def test_r6_real_wall_first_retirement_instruction_restores(self):
        self._r6_finalizer_control('_wall_bound')

    def test_r6_real_timeout_first_retirement_instruction_restores(self):
        self._r6_finalizer_control('_nonblocking_ledger')

    def test_r6_real_capture_first_retirement_instruction_reaps(self):
        self._r6_finalizer_control('_capture')

    def _r6_finalizer_control(self, owner):
        connection = self.ledger.db; connection.execute('PRAGMA busy_timeout=6833')
        handler = signal.getsignal(signal.SIGALRM)
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        original_write, original_wait = capture._write_new, os.waitpid
        facts = {'owner': owner, 'hooks': [], 'fixture_recovery': []}; self.extra['r6_finalizer'] = facts
        def predicate(frame):
            return frame.f_code.co_filename == capture.__file__ and frame.f_code.co_qualname == owner + '.<locals>.retire'
        def failed_start(path, raw, **kwargs):
            if owner == '_capture' and Path(path).name == 'start.json':
                raise OSError('R6 distinct retained-start refusal')
            return original_write(path, raw, **kwargs)
        try:
            with self.native_trace() as (data, hooks), self.r3_resource_trace() as (resources, _):
                if owner == '_capture': self.r3_stop_owned_child(hooks, original_wait)
                with patch.object(capture, '_write_new', side_effect=failed_start), self.r6_first_line(predicate, facts):
                    with self.assertRaises(KeyboardInterrupt): self.invoke_r6()
            facts.update(timeout=connection.execute('PRAGMA busy_timeout').fetchone()[0],
                         handler_restored=signal.getsignal(signal.SIGALRM) is handler,
                         timer=signal.getitimer(signal.ITIMER_REAL),
                         mask_restored=signal.pthread_sigmask(signal.SIG_BLOCK, set()) == mask)
        finally:
            if connection.execute('PRAGMA busy_timeout').fetchone()[0] != 6833:
                facts['fixture_recovery'].append('timeout'); connection.execute('PRAGMA busy_timeout=6833')
            if signal.getsignal(signal.SIGALRM) is not handler or signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
                facts['fixture_recovery'].append('alarm'); signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, handler)
        self.assertEqual(len(facts['hooks']), 1); self.assertEqual(facts['hooks'][0]['mask'], sorted(int(x) for x in mask))
        self.assertEqual(facts['fixture_recovery'], []); self.assertEqual(facts['timeout'], 6833)
        self.assertTrue(facts['handler_restored']); self.assertEqual(facts['timer'], (0.0, 0.0)); self.assertTrue(facts['mask_restored'])
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(resources['remaining'], [])
        self.assertEqual(data['wait_statuses'], [[data['pids'][0], signal.SIGKILL if owner == '_capture' else 0]])
        self.assertEqual(len(self.ledger.events()), 1 if owner == '_capture' else 2)

    def test_r6_real_initial_append_flag_before_try_is_restored(self):
        self._r6_append_control('initial', 'flag')

    def test_r6_real_initial_native_begin_is_rolled_back(self):
        self._r6_append_control('initial', 'begin')

    def test_r6_real_initial_commit_with_lost_return_stays_claimed(self):
        self._r6_append_control('initial', 'commit')

    def test_r6_real_terminal_append_flag_before_try_is_restored(self):
        self._r6_append_control('terminal', 'flag')

    def test_r6_real_terminal_native_begin_is_rolled_back(self):
        self._r6_append_control('terminal', 'begin')

    def test_r6_real_terminal_commit_with_lost_return_stays_committed(self):
        self._r6_append_control('terminal', 'commit')

    def _r6_append_control(self, phase, boundary):
        connection = self.ledger.db; native_kill = os.kill; target = 1 if phase == 'initial' else 2
        connection.execute('PRAGMA busy_timeout=6947')
        facts = {'phase': phase, 'boundary': boundary, 'hooks': [], 'begins': 0, 'commits': 0,
                 'rollbacks': [], 'fixture_recovery': []}; self.extra['r6_append'] = facts
        append_file = Ledger.append.__code__.co_filename
        append_lines = Path(append_file).read_text().splitlines()
        flag_boundary = next(index for index, line in enumerate(append_lines, 1) if line.strip() == 'owns_transaction = False')
        wanted_kind = 'prospective_capture_started' if phase == 'initial' else 'prospective_capture_finished'
        def predicate(frame):
            return boundary == 'flag' and frame.f_code is Ledger.append.__code__ and frame.f_lineno == flag_boundary and frame.f_locals.get('kind') == wanted_kind
        def interrupt(label):
            facts['hooks'].append({'at': label, 'transaction': connection.in_transaction,
                                   'append_active': self.ledger._append_active, 'self_pid': os.getpid(),
                                   'committed_events': connection.execute('SELECT count(*) FROM events').fetchone()[0]})
            native_kill(os.getpid(), signal.SIGINT)
        class ConnectionProxy:
            def __getattr__(self, name): return getattr(connection, name)
            def execute(self, statement, *args):
                result = connection.execute(statement, *args)
                if statement == 'BEGIN IMMEDIATE':
                    facts['begins'] += 1
                    if boundary == 'begin' and facts['begins'] == target: interrupt('after_native_begin')
                return result
            def commit(self):
                result = connection.commit(); facts['commits'] += 1
                if boundary == 'commit' and facts['commits'] == target: interrupt('after_native_commit')
                return result
            def rollback(self):
                facts['rollbacks'].append({'was_active': connection.in_transaction})
                return connection.rollback()
        self.ledger.db = ConnectionProxy()
        try:
            with self.native_trace() as (data, _), self.r3_resource_trace() as (resources, _):
                with self.r6_first_line(predicate, facts):
                    with self.assertRaises(KeyboardInterrupt): self.invoke_r6()
            facts.update(transaction_after=connection.in_transaction, append_active_after=self.ledger._append_active,
                         timeout_after=connection.execute('PRAGMA busy_timeout').fetchone()[0],
                         event_count=len(self.ledger.events()))
        finally:
            self.ledger.db = connection
            if connection.in_transaction:
                facts['fixture_recovery'].append('transaction'); connection.rollback()
            if self.ledger._append_active:
                facts['fixture_recovery'].append('flag'); self.ledger._append_active = False
        self.assertEqual(len(facts['hooks']), 1); self.assertEqual(facts['fixture_recovery'], [])
        self.assertFalse(facts['transaction_after']); self.assertFalse(facts['append_active_after'])
        self.assertEqual(facts['timeout_after'], 6947)
        self.assertEqual(facts['event_count'], (target if boundary == 'commit' else target - 1))
        if boundary == 'begin': self.assertEqual(facts['rollbacks'], [{'was_active': True}])
        if boundary == 'commit': self.assertTrue(all(not row['was_active'] for row in facts['rollbacks']))
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(resources['remaining'], [])
        self.assertEqual(len(self.calls), 0 if phase == 'initial' else 1)
        self.assertEqual(len(data['wait_statuses']), 0 if phase == 'initial' else 1)
        self.assertEqual(self.results, [])

    def test_r6_real_fixed_worker_retains_literal_and_caller_state(self):
        with self.native_trace() as (data, _), self.r3_resource_trace() as (resources, _):
            result = self.invoke_r6()
        expected = canonical({'lines': [{'start': 0, 'end': 13, 'sha256': digest(b'R6 ownership\n')},
                                       {'start': 13, 'end': 31, 'sha256': digest(b'local first claim\n')}],
                              'schema_version': 1, 'source_byte_length': 31,
                              'source_sha256': digest(b'R6 ownership\nlocal first claim\n')}).encode()
        self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), expected)
        self.assertEqual(result['receipt']['wait_status'], 0); self.assertTrue(result['publication_clock_verified'])
        self.assertFalse(result['continuation_allowed']); self.assertEqual(len(self.ledger.events()), 2)
        self.assertFalse(self.ledger.db.in_transaction); self.assertFalse(self.ledger._append_active)
        self.assertEqual(data['harness_recovery'], []); self.assertEqual(resources['remaining'], [])

    def test_r6_real_three_supported_deliveries_resume_known_fd_retirement(self):
        native_kill = os.kill; owned = capture._OwnedFDs()
        facts = {'deliveries': [], 'retire_calls': 0}; self.extra['r6_guards'] = facts
        def body():
            owned.open('guard_fixture', self.directory / 'guard-fixture.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        def retire(_scope):
            facts['retire_calls'] += 1
            delivery = {1: signal.SIGALRM, 2: signal.SIGINT, 3: signal.SIGALRM}.get(facts['retire_calls'])
            if delivery is not None:
                facts['deliveries'].append({'signal': int(delivery), 'self_pid': os.getpid(),
                                            'remaining_timer': signal.getitimer(signal.ITIMER_REAL)[0]})
                native_kill(os.getpid(), delivery)
            owned.close_all()
        handler = signal.getsignal(signal.SIGALRM)
        with self.r3_resource_trace() as (resources, _):
            with self.assertRaises(KeyboardInterrupt):
                capture._wall_bound(3, .5, lambda _enter: capture._owned(body, retire, cancellation=owned.cancellation), cancellation=owned.cancellation)
        self.assertEqual(facts['retire_calls'], 4)
        self.assertEqual([row['signal'] for row in facts['deliveries']], [signal.SIGALRM, signal.SIGINT, signal.SIGALRM])
        self.assertEqual(resources['remaining'], []); self.assertIsNone(owned.values['guard_fixture'])
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0)); self.assertIs(signal.getsignal(signal.SIGALRM), handler)
        self.assertEqual(self.calls, []); self.assertEqual(self.ledger.events(), [])

    def test_r6_real_interrupted_exception_bookkeeping_keeps_owned_interrupt(self):
        native_kill, original_remember = os.kill, capture._remember
        owned = capture._OwnedFDs(); facts = {'hook': [], 'body_interrupt': None}; self.extra['r6_context'] = facts
        def body():
            owned.open('context_fixture', self.directory / 'context-fixture.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            try: native_kill(os.getpid(), signal.SIGINT)
            except KeyboardInterrupt as error:
                facts['body_interrupt'] = id(error)
                raise
        def interrupted(scope, error):
            if isinstance(error, KeyboardInterrupt) and not facts['hook']:
                facts['hook'].append({'self_pid': os.getpid(), 'interrupt_identity': id(error)})
                native_kill(os.getpid(), signal.SIGALRM)
            return original_remember(scope, error)
        with self.r3_resource_trace() as (resources, _), patch.object(capture, '_remember', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt) as caught:
                capture._wall_bound(3, .5, lambda _enter: capture._owned(body, lambda _scope: owned.close_all(), cancellation=owned.cancellation), cancellation=owned.cancellation)
        facts['returned_interrupt'] = id(caught.exception)
        self.assertEqual(len(facts['hook']), 1); self.assertEqual(facts['body_interrupt'], facts['returned_interrupt'])
        self.assertEqual(resources['remaining'], []); self.assertIsNone(owned.values['context_fixture'])
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0)); self.assertEqual(self.calls, [])


    def invoke_r7(self):
        source = b'R7 propagation\nretained uncertainty\n'
        binding = {**self.binding, 'instance_id': 'invented-c23-r7', 'source_sha256': digest(source)}
        return self.invoke(source=source, binding=binding)

    def test_r7_real_first_deadline_keeps_injected_close_uncertainty(self):
        original_sync, native_kill = os.fsync, os.kill
        facts = {'deadline_hook': [], 'injected_after_actual_close': []}; self.extra['r7_close'] = facts
        with self.r3_resource_trace() as (resources, hooks):
            def synced(fd):
                result = original_sync(fd)
                tracked = resources['active'].get(fd)
                if tracked and Path(tracked['path']).name == 'source.bin' and not facts['deadline_hook']:
                    facts['deadline_hook'].append({'self_pid': os.getpid(), 'remaining_timer': signal.getitimer(signal.ITIMER_REAL)[0]})
                    native_kill(os.getpid(), signal.SIGALRM)
                return result
            def uncertain(owned):
                if Path(owned['path']).name == 'source.bin' and facts['deadline_hook']:
                    facts['injected_after_actual_close'].append(owned)
                    raise OSError('R7 labelled uncertainty after successful native close')
            hooks['close'] = uncertain
            with patch.object(capture.os, 'fsync', side_effect=synced): result = self.invoke_r7()
        self.assertEqual(len(facts['deadline_hook']), 1); self.assertEqual(len(facts['injected_after_actual_close']), 1)
        expected = {'operation': 'close_output', 'error_type': 'OSError', 'native_close_uncertain': True}
        self.assertIn(expected, result['receipt']['errors']); self.assertEqual(result['receipt']['close_errors'], [expected])
        self.assertFalse(result['receipt']['close_errors_truncated']); self.assertEqual(result['receipt']['termination'], 'parent_deadline')
        self.assertEqual(self.calls, []); self.assertEqual(resources['remaining'], []); self.assertEqual(len(self.ledger.events()), 2)

    def test_r7_real_recorded_interrupt_survives_final_dispatch_alarm(self):
        self._r7_dispatch_control('recorded')

    def test_r7_real_first_dispatch_interrupt_then_alarm_before_bookkeeping(self):
        self._r7_dispatch_control('before_record')

    def test_r7_real_composed_close_uncertainty_interrupt_and_final_alarm(self):
        self._r7_dispatch_control('close')

    def _r7_dispatch_control(self, mode):
        original_finish, original_remember = capture._finish_owned, capture._remember
        original_write, original_sync, native_kill = capture._write_new, os.fsync, os.kill
        facts = {'mode': mode, 'interrupt_hook': [], 'final_hook': [], 'injected_close': []}; self.extra['r7_dispatch'] = facts
        original_handler = signal.getsignal(signal.SIGALRM)
        def send_interrupt():
            facts['interrupt_hook'].append({'self_pid': os.getpid()})
            try: native_kill(os.getpid(), signal.SIGINT)
            except KeyboardInterrupt as error:
                facts['first_interrupt_id'] = id(error)
                raise
        def is_capture(scope):
            retire = scope['frame'].f_locals.get('retire')
            return getattr(retire, '__qualname__', None) == '_capture.<locals>.retire'
        with self.native_trace() as (native, _), self.r3_resource_trace() as (resources, hooks):
            def final(scope):
                facts['final_hook'].append({'self_pid': os.getpid(), 'scope_interrupt': id(scope['interrupt']) if scope['interrupt'] is not None else None,
                    'record_interrupt': id(scope['cancellation']['interrupt']) if scope['cancellation']['interrupt'] is not None else None,
                    'remaining_timer': signal.getitimer(signal.ITIMER_REAL)[0]})
                resources['final_pending'] = True
                native_kill(os.getpid(), signal.SIGALRM)
            def finish(scope, result, close_errors):
                if is_capture(scope):
                    if mode == 'before_record' and not facts['interrupt_hook']: send_interrupt()
                    if mode != 'before_record' and scope['interrupt'] is not None and not facts['final_hook']: final(scope)
                return original_finish(scope, result, close_errors)
            def remember(scope, error):
                if mode == 'before_record' and is_capture(scope) and isinstance(error, KeyboardInterrupt) and not facts['final_hook']:
                    self.assertIsNone(scope['cancellation']['interrupt'])
                    final(scope)
                return original_remember(scope, error)
            def written(path, raw, **kwargs):
                if mode == 'recorded' and Path(path).name == 'start.json' and not facts['interrupt_hook']: send_interrupt()
                return original_write(path, raw, **kwargs)
            def synced(fd):
                result = original_sync(fd); tracked = resources['active'].get(fd)
                if mode == 'close' and tracked and Path(tracked['path']).name == 'source.bin' and not facts['interrupt_hook']: send_interrupt()
                return result
            def uncertain(owned):
                if mode == 'close' and Path(owned['path']).name == 'source.bin' and facts['interrupt_hook']:
                    facts['injected_close'].append(owned)
                    raise OSError('R7 composed labelled close uncertainty after actual close')
            hooks['close'] = uncertain
            with patch.object(capture, '_finish_owned', side_effect=finish), patch.object(capture, '_remember', side_effect=remember), \
                 patch.object(capture, '_write_new', side_effect=written), patch.object(capture.os, 'fsync', side_effect=synced):
                with self.assertRaises(KeyboardInterrupt) as caught: self.invoke_r7()
        facts.update(returned_interrupt_id=id(caught.exception), deadline=getattr(caught.exception, 'capture_deadline', None),
                     close_errors=getattr(caught.exception, 'capture_close_errors', []))
        self.assertEqual(len(facts['interrupt_hook']), 1); self.assertEqual(len(facts['final_hook']), 1)
        self.assertEqual(facts['first_interrupt_id'], facts['returned_interrupt_id'])
        self.assertTrue(facts['deadline']['final']); self.assertLessEqual(facts['final_hook'][0]['remaining_timer'], .5)
        self.assertGreater(facts['final_hook'][0]['remaining_timer'], 0)
        self.assertEqual(resources['after_final_writes'], []); self.assertEqual(resources['remaining'], [])
        self.assertEqual(native['harness_recovery'], []); self.assertEqual(len(self.ledger.events()), 1)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0)); self.assertIs(signal.getsignal(signal.SIGALRM), original_handler)
        if mode == 'close':
            self.assertEqual(len(facts['injected_close']), 1); self.assertEqual(len(facts['close_errors']), 1)
            self.assertTrue(facts['close_errors'][0]['native_close_uncertain']); self.assertEqual(self.calls, [])
        else:
            self.assertEqual(len(self.calls), 1); self.assertEqual(len(native['wait_statuses']), 1)

    def test_r7_real_normal_literal_does_not_adopt_nested_ambient_exceptions(self):
        prior = KeyboardInterrupt('R7 ambient caller interrupt'); prior.marker = 'unchanged'
        later = capture.CaptureDeadline(final=True); later.marker = 'also unchanged'
        try: raise prior
        except KeyboardInterrupt:
            try: raise later
            except capture.CaptureDeadline:
                before = [(dict(vars(x)), x.__traceback__, x.__context__, x.__cause__, x.args) for x in [prior, later]]
                with self.native_trace() as (native, _), self.r3_resource_trace() as (resources, _): result = self.invoke_r7()
        after = [(dict(vars(x)), x.__traceback__, x.__context__, x.__cause__, x.args) for x in [prior, later]]
        self.extra['r7_ambient'] = {'objects_unchanged': before == after}
        self.assertEqual(before, after)
        expected = canonical({'lines': [{'start': 0, 'end': 15, 'sha256': digest(b'R7 propagation\n')},
                                       {'start': 15, 'end': 36, 'sha256': digest(b'retained uncertainty\n')}],
                              'schema_version': 1, 'source_byte_length': 36,
                              'source_sha256': digest(b'R7 propagation\nretained uncertainty\n')}).encode()
        self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), expected)
        self.assertEqual(result['receipt']['wait_status'], 0); self.assertEqual(len(self.ledger.events()), 2)
        self.assertEqual(native['harness_recovery'], []); self.assertEqual(resources['remaining'], [])

    def test_r7_real_callback_only_handled_interrupt_not_adopted_by_alarm(self):
        native_kill = os.kill; prior = KeyboardInterrupt('R7 callback-only handled interrupt'); prior.marker = 'untouched'
        facts = {'hook': []}; self.extra['r7_callback'] = facts
        def clock():
            try: raise prior
            except KeyboardInterrupt:
                before = (dict(vars(prior)), prior.__traceback__, prior.__context__, prior.__cause__, prior.args)
                facts['hook'].append({'self_pid': os.getpid()})
                try: native_kill(os.getpid(), signal.SIGALRM)
                finally:
                    facts['prior_unchanged'] = before == (dict(vars(prior)), prior.__traceback__, prior.__context__, prior.__cause__, prior.args)
        self.ledger.clock = clock
        with self.assertRaises(capture.CaptureDeadline) as caught: self.invoke_r7()
        self.assertFalse(caught.exception.final); self.assertTrue(facts['prior_unchanged'])
        self.assertEqual(len(facts['hook']), 1); self.assertEqual(self.calls, []); self.assertEqual(self.ledger.events(), [])
        self.assertFalse(self.ledger.db.in_transaction); self.assertFalse(self.ledger._append_active)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))

    def test_r7_real_owned_close_faults_are_deduplicated_bounded_and_flagged(self):
        owned = capture._OwnedFDs(); facts = {'injected': []}; self.extra['r7_bound'] = facts
        def body():
            for index in range(17): owned.open('distinct_' + str(index), self.directory / ('fault-' + str(index)), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with self.r3_resource_trace() as (resources, hooks):
            def uncertain(value):
                facts['injected'].append(value)
                raise OSError('R7 labelled uncertainty after actual native close')
            hooks['close'] = uncertain
            with self.assertRaises(OSError) as caught:
                capture._owned(body, lambda _scope: owned.close_all(), close_errors=owned.close_errors, cancellation=owned.cancellation)
        errors = caught.exception.capture_close_errors
        facts.update(retained_count=len(errors), truncated=caught.exception.capture_close_errors_truncated)
        self.assertEqual(len(facts['injected']), 17); self.assertEqual(len(errors), 16); self.assertTrue(facts['truncated'])
        self.assertEqual(len({row['operation'] for row in errors}), 16); self.assertEqual(resources['remaining'], [])
        self.assertEqual(self.calls, []); self.assertEqual(self.ledger.events(), [])

    def test_r7_real_nonfinal_alarm_does_not_rethrow_from_normal_cleanup_helpers(self):
        original_write, native_timer, native_kill = capture._write_new, signal.setitimer, os.kill
        facts = {'hook': [], 'timer_arms': []}; self.extra['r7_consumed'] = facts
        def timed(which, seconds, *args):
            if seconds: facts['timer_arms'].append(seconds)
            return native_timer(which, seconds, *args)
        def written(path, raw, **kwargs):
            if Path(path).name == 'start.json' and not facts['hook']:
                facts['hook'].append({'self_pid': os.getpid()}); native_kill(os.getpid(), signal.SIGALRM)
            return original_write(path, raw, **kwargs)
        with self.native_trace() as (native, _), self.r3_resource_trace() as (resources, _):
            with patch.object(capture, '_write_new', side_effect=written), patch.object(capture.signal, 'setitimer', side_effect=timed): result = self.invoke_r7()
        self.assertEqual(len(facts['hook']), 1); self.assertEqual(facts['timer_arms'], [3, .5])
        self.assertEqual(result['receipt']['termination'], 'parent_deadline'); self.assertTrue(result['receipt']['child_reaped'])
        self.assertEqual(len(self.ledger.events()), 2); self.assertEqual(native['harness_recovery'], []); self.assertEqual(resources['remaining'], [])

    def test_r7_real_retention_reread_close_uncertainty_reaches_receipt(self):
        facts = {'hook': []}; self.extra['r7_reread'] = facts
        with self.native_trace() as (native, _), self.r3_resource_trace() as (resources, hooks):
            def uncertain(owned):
                if Path(owned['path']).name != 'stdout.bin' or facts['hook']: return
                frame = sys._getframe(1)
                for _ in range(16):
                    if frame is None: return
                    if frame.f_code is capture._read.__code__:
                        facts['hook'].append(owned)
                        raise OSError('R7 labelled post-reread close uncertainty')
                    frame = frame.f_back
            hooks['close'] = uncertain
            result = self.invoke_r7()
        expected = {'operation': 'close_input', 'error_type': 'OSError', 'native_close_uncertain': True}
        self.assertEqual(len(facts['hook']), 1); self.assertEqual(result['receipt']['close_errors'], [expected])
        self.assertIn(expected, result['receipt']['errors']); self.assertFalse(result['receipt']['streams']['stdout']['retention_verified'])
        self.assertTrue(result['receipt']['streams']['stdout']['complete_bytes_observed']); self.assertEqual(result['receipt']['wait_status'], 0)
        self.assertEqual(native['harness_recovery'], []); self.assertEqual(resources['remaining'], []); self.assertEqual(len(self.ledger.events()), 2)


    def test_r8_real_pending_cleanup_normal_completion_preserves_observation(self):
        self._r8_pending_control('normal')

    def test_r8_real_pending_cleanup_then_interrupt_preserves_nonfinal_evidence(self):
        self._r8_pending_control('interrupt')

    def test_r8_real_pending_cleanup_interrupt_then_final_alarm_keeps_both_phases(self):
        self._r8_pending_control('final')

    def _r8_pending_control(self, mode):
        original_capture, original_sync, original_finish = capture._capture, capture._sync_directory, capture._finish_owned
        native_timer, native_pending, native_wait = signal.setitimer, signal.sigpending, signal.sigwait
        native_kill, native_fsync = os.kill, os.fsync
        original_handler = signal.getsignal(signal.SIGALRM); original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        record = []; admission_code = []; result = caught = None
        facts = {'mode': mode, 'pending_sent': [], 'pending_observed': [], 'consumed': [], 'interrupt_sent': [],
                 'final_sent': [], 'timer_arms': [], 'after_final_fsync': []}; self.extra['r8_pending'] = facts
        def in_admission():
            frame = sys._getframe(1)
            for _ in range(16):
                if frame is None: return False
                if admission_code and frame.f_code is admission_code[0]: return True
                frame = frame.f_back
            return False
        def captured(ledger, claim, source, producer, directory, enter_cleanup, **kwargs):
            record.append(kwargs['cancellation']); admission_code.append(enter_cleanup.__code__)
            return original_capture(ledger, claim, source, producer, directory, enter_cleanup, **kwargs)
        def timed(which, seconds, *args):
            value = native_timer(which, seconds, *args)
            if seconds: facts['timer_arms'].append(seconds)
            if seconds == 0 and in_admission() and not facts['pending_sent']:
                facts['pending_sent'].append({'self_pid': os.getpid(), 'mask': sorted(int(x) for x in signal.pthread_sigmask(signal.SIG_BLOCK, set()))})
                native_kill(os.getpid(), signal.SIGALRM)
            return value
        def pending():
            value = native_pending()
            if in_admission() and signal.SIGALRM in value: facts['pending_observed'].append(int(signal.SIGALRM))
            return value
        def waited(signals):
            value = native_wait(signals)
            if in_admission(): facts['consumed'].append(int(value))
            return value
        def synced(path, **kwargs):
            value = original_sync(path, **kwargs)
            if mode != 'normal' and self.in_capture_cleanup() and not facts['interrupt_sent']:
                facts['interrupt_sent'].append({'self_pid': os.getpid(), 'remaining_timer': signal.getitimer(signal.ITIMER_REAL)[0]})
                try: native_kill(os.getpid(), signal.SIGINT)
                except KeyboardInterrupt as error:
                    facts['first_interrupt_id'] = id(error)
                    raise
            return value
        with self.native_trace() as (native, _), self.r3_resource_trace() as (resources, _):
            def fsynced(fd):
                if resources.get('final_pending'): facts['after_final_fsync'].append(fd)
                return native_fsync(fd)
            def finished(scope, value, close_errors):
                retire = scope['frame'].f_locals.get('retire')
                if mode == 'final' and getattr(retire, '__qualname__', None) == '_capture.<locals>.retire' and scope['interrupt'] is not None and not facts['final_sent']:
                    facts['final_sent'].append({'self_pid': os.getpid(), 'remaining_timer': signal.getitimer(signal.ITIMER_REAL)[0]})
                    resources['final_pending'] = True; native_kill(os.getpid(), signal.SIGALRM)
                return original_finish(scope, value, close_errors)
            prior = KeyboardInterrupt('R8 earlier caller interruption'); prior.marker = 'unchanged'
            try: raise prior
            except KeyboardInterrupt:
                before = (dict(vars(prior)), prior.__traceback__, prior.__context__, prior.__cause__, prior.args)
                with patch.object(capture, '_capture', side_effect=captured), patch.object(capture, '_sync_directory', side_effect=synced), \
                     patch.object(capture, '_finish_owned', side_effect=finished), patch.object(capture.signal, 'setitimer', side_effect=timed), \
                     patch.object(capture.signal, 'sigpending', side_effect=pending), patch.object(capture.signal, 'sigwait', side_effect=waited), \
                     patch.object(capture.os, 'fsync', side_effect=fsynced):
                    source = b'R8 pending\none reserve\n'
                    binding = {**self.binding, 'instance_id': 'invented-c23-r8', 'source_sha256': digest(source)}
                    try: result = self.invoke(source=source, binding=binding)
                    except KeyboardInterrupt as error: caught = error
                facts['ambient_unchanged'] = before == (dict(vars(prior)), prior.__traceback__, prior.__context__, prior.__cause__, prior.args)
        state = record[0]
        facts.update(record_deadline={'phase': state['deadline'].phase, 'final': state['deadline'].final},
                     record_pending=state['pending_alarm_observed'], pending_observation=state['pending_alarm_observation'],
                     returned_interrupt_id=id(caught) if caught is not None else None,
                     exception_deadline=getattr(caught, 'capture_deadline', None),
                     caller_handler_restored=signal.getsignal(signal.SIGALRM) is original_handler,
                     caller_mask_restored=signal.pthread_sigmask(signal.SIG_BLOCK, set()) == original_mask,
                     final_timer=signal.getitimer(signal.ITIMER_REAL))
        self.assertEqual(len(facts['pending_sent']), 1); self.assertEqual(facts['pending_observed'], [signal.SIGALRM])
        self.assertEqual(facts['consumed'], [signal.SIGALRM]); self.assertEqual(facts['timer_arms'], [3, .5])
        self.assertTrue({int(signal.SIGINT), int(signal.SIGALRM)}.issubset(facts['pending_sent'][0]['mask']))
        self.assertTrue(facts['record_pending']); self.assertEqual(facts['pending_observation'], {'phase': 'cleanup_admission', 'final': False})
        self.assertTrue(facts['ambient_unchanged']); self.assertTrue(facts['caller_handler_restored']); self.assertTrue(facts['caller_mask_restored'])
        self.assertEqual(facts['final_timer'], (0.0, 0.0)); self.assertEqual(resources['remaining'], []); self.assertEqual(native['harness_recovery'], [])
        self.assertEqual(native['wait_statuses'], [[native['pids'][0], 0]])
        self.assertEqual(len(self.calls), 1); self.assertEqual(resources['after_final_writes'], []); self.assertEqual(facts['after_final_fsync'], [])
        if mode == 'normal':
            self.assertIsNone(caught); self.assertEqual(result['receipt']['termination'], 'parent_deadline'); self.assertEqual(len(self.ledger.events()), 2)
            expected = canonical({'lines': [{'start': 0, 'end': 11, 'sha256': digest(b'R8 pending\n')},
                                           {'start': 11, 'end': 23, 'sha256': digest(b'one reserve\n')}],
                                  'schema_version': 1, 'source_byte_length': 23,
                                  'source_sha256': digest(b'R8 pending\none reserve\n')}).encode()
            self.assertEqual(Path(result['receipt']['streams']['stdout']['path']).read_bytes(), expected)
        else:
            self.assertIsInstance(caught, KeyboardInterrupt); self.assertEqual(facts['first_interrupt_id'], facts['returned_interrupt_id'])
            expected = {'phase': 'owned_alarm' if mode == 'final' else 'cleanup_admission', 'final': mode == 'final',
                        'pending_alarm_observed': True, 'pending_alarm_observation': {'phase': 'cleanup_admission', 'final': False}}
            self.assertEqual(facts['exception_deadline'], expected); self.assertEqual(len(self.ledger.events()), 1)
            self.assertEqual(len(facts['interrupt_sent']), 1)
        self.assertEqual(len(facts['final_sent']), 1 if mode == 'final' else 0)


if __name__ == '__main__':
    unittest.main()
