"""One local first-attempt claim and fixed leaf-process capture, not an outcome.

Trusted POSIX main-thread supervision. A surviving parent is required; filesystem
and kernel failures can leave the exclusive claim without a terminal receipt.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import math
import os
import re
import selectors
import signal
import stat
import sys
import threading
import time
import uuid

from .store import Ledger, canonical, digest, instant


PRODUCER_SHA256 = 'b75e28b42c0dab8b90275da511848ea49e865c11891414d3c180a51b25fecf4a'
SCHEMA_SHA256 = '7fca7514f1012274e51583cad46b6b0d66ee1f813cb6b760fab4cf78f8441413'
STREAM_CAPS = {'stdout': 65536, 'stderr': 16384}
_DIRECTORY = Path(__file__).parent
_SOURCE = Path(__file__).read_bytes()
_WORKER = (_DIRECTORY / 'prospective_producer_worker.py').read_bytes()
_CANCEL_SIGNALS = {signal.SIGALRM, signal.SIGINT}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _stamp():
    return {'utc': datetime.now(timezone.utc).isoformat(), 'monotonic': time.monotonic()}


def _clock_consistent(origin, observations):
    for observed in observations:
        if observed is None:
            continue
        elapsed = observed['monotonic'] - origin['monotonic']
        if elapsed < 0 or abs((instant(observed['utc']) - instant(origin['utc'])).total_seconds() - elapsed) > 1:
            return False
    return True


def _descriptor_preflight():
    """Bounded inventory of this process only; never close foreign descriptors."""
    _require(threading.active_count() == 1, 'single-threaded capture process required')
    for descriptor in (0, 1, 2):
        os.fstat(descriptor)
    with os.scandir('/dev/fd') as entries:
        for count, entry in enumerate(entries, 1):
            _require(count <= 256, 'parent descriptor inventory exceeds bound')
            _require(entry.name.isdecimal(), 'unexpected descriptor inventory entry')
            descriptor = int(entry.name)
            try:
                inheritable = os.get_inheritable(descriptor)
            except OSError as error:
                if error.errno == 9:  # The inventory's own transient descriptor.
                    continue
                raise
            _require(descriptor <= 2 or not inheritable, 'unexpected inheritable parent descriptor')


def _signal_preflight():
    _require(threading.current_thread() is threading.main_thread(), 'main thread required')
    _require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'existing process alarm')
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    _require(not ((_CANCEL_SIGNALS | {signal.SIGCHLD}) & mask), 'blocked supported signal')
    _require(not (_CANCEL_SIGNALS & signal.sigpending()), 'pending supported cancellation')
    _require(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL, 'default child status disposition required')
    _require(signal.getsignal(signal.SIGINT) is signal.default_int_handler, 'default keyboard interrupt handler required')


@contextmanager
def _handoff():
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, _CANCEL_SIGNALS)
    try:
        yield previous
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def _cancellation_record():
    return {'interrupt': None, 'deadline': None, 'pending_alarm_observed': False, 'pending_alarm_observation': None,
            'close_errors': [], 'close_errors_truncated': False}


def _close_evidence(cancellation, errors):
    # Records originate in this adapter. Retain a set of distinct descriptions,
    # not an event count; repeated propagation does not consume the bound.
    for error in errors[:16]:
        if error in cancellation['close_errors']:
            continue
        if len(cancellation['close_errors']) < 16:
            cancellation['close_errors'].append(error)
        else:
            cancellation['close_errors_truncated'] = True
    if len(errors) > 16:
        cancellation['close_errors_truncated'] = True


def _annotate(error, cancellation):
    metadata = BaseException.__dict__['__dict__'].__get__(error)
    if cancellation['close_errors']:
        metadata['capture_close_errors'] = cancellation['close_errors'][:16]
    if cancellation['close_errors_truncated']:
        metadata['capture_close_errors_truncated'] = True
    deadline = cancellation['deadline']
    if isinstance(error, KeyboardInterrupt) and deadline is not None:
        metadata['capture_deadline'] = {'phase': deadline.phase,
                                  'final': deadline.final, 'pending_alarm_observed': cancellation['pending_alarm_observed']}
        if cancellation['pending_alarm_observation'] is not None:
            metadata['capture_deadline']['pending_alarm_observation'] = dict(cancellation['pending_alarm_observation'])
    if isinstance(error, CaptureDeadline) and cancellation['pending_alarm_observed']:
        metadata['pending_alarm_observed'] = True
        metadata['pending_alarm_observation'] = dict(cancellation['pending_alarm_observation'])


def _live_interrupt(cancellation, frame, error):
    """Only a caught exception with this live call's exact owner-frame trace."""
    for _ in range(16):
        if frame is None:
            break
        if frame.f_code is _owned.__code__:
            scope = frame.f_locals.get('scope')
            if type(scope) is dict and scope.get('cancellation') is cancellation:
                candidate = error
                for _context in range(4):
                    if candidate is None:
                        break
                    trace = candidate.__traceback__
                    for _depth in range(16):
                        if trace is None or trace.tb_frame is frame:
                            break
                        trace = trace.tb_next
                    if trace is None or trace.tb_frame is not frame:
                        break
                    if isinstance(candidate, KeyboardInterrupt):
                        _remember(scope, candidate)
                        return
                    following = candidate.__context__
                    if following is candidate:
                        break
                    candidate = following
        frame = frame.f_back


class _OwnedFDs:
    """Fixed local resources; publish and retire ownership before cancellation."""
    def __init__(self, cancellation=None):
        self.cancellation = cancellation if cancellation is not None else _cancellation_record()
        self.values = {}
        self.close_errors = []

    def open(self, key, path, flags, mode=0o600):
        _require(key not in self.values, 'descriptor ownership key reused')
        with _handoff():
            self.values[key] = os.open(path, flags, mode)
        return self.values[key]

    def pipe(self, reading, writing):
        _require(reading not in self.values and writing not in self.values and reading != writing,
                 'pipe ownership key reused')
        with _handoff():
            self.values[reading], self.values[writing] = os.pipe()

    def close(self, key):
        with _handoff():
            descriptor = self.values.get(key)
            if descriptor is None:
                return
            try:
                os.close(descriptor)
            except OSError as error:
                # The kernel's close outcome can be uncertain. Never blindly
                # retry this numeric FD, which could already have been reused.
                if len(self.close_errors) < 16:
                    self.close_errors.append({'operation': 'close_' + key,
                                              'error_type': type(error).__name__, 'native_close_uncertain': True})
                else:
                    self.cancellation['close_errors_truncated'] = True
                _close_evidence(self.cancellation, self.close_errors)
                raise
            finally:
                self.values[key] = None

    def close_all(self):
        interruption = failure = None
        for key in tuple(self.values):
            for _attempt in range(2):
                try:
                    self.close(key)
                except (CaptureDeadline, KeyboardInterrupt) as error:
                    # One cancellation can arrive before the mask is installed.
                    # A still-owned key means native close was not attempted;
                    # completed/uncertain close always retires the key first.
                    if isinstance(error, KeyboardInterrupt) or not isinstance(interruption, KeyboardInterrupt):
                        interruption = error
                except OSError as error:
                    failure = error
                if self.values.get(key) is None:
                    break
        if interruption is not None:
            interruption.capture_close_errors = self.close_errors[:16]
            raise interruption
        if failure is not None:
            raise failure


def _write_all(descriptor, raw):
    position = 0
    while position < len(raw):
        count = os.write(descriptor, raw[position:])
        if count <= 0:
            raise OSError('zero-progress retained write')
        position += count


def _read(path, limit, *, cancellation=None):
    owned = _OwnedFDs(cancellation)
    def body():
        descriptor = owned.open('input', path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'bounded regular file required')
        chunks = []; size = 0
        while size <= limit:
            chunk = os.read(descriptor, min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk); size += len(chunk)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
        _require(len(raw) <= limit and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                 == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'file changed during read')
        return raw
    return _owned(body, lambda _scope: owned.close_all(), close_errors=owned.close_errors, cancellation=owned.cancellation)


def _sync_directory(directory, *, cancellation=None):
    owned = _OwnedFDs(cancellation)
    def body():
        descriptor = owned.open('directory', directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        os.fsync(descriptor)
    _owned(body, lambda _scope: owned.close_all(), close_errors=owned.close_errors, cancellation=owned.cancellation)


def _write_new(path, raw, *, cancellation=None):
    owned = _OwnedFDs(cancellation)
    def body():
        descriptor = owned.open('output', path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW)
        _write_all(descriptor, raw)
        os.fsync(descriptor)
    _owned(body, lambda _scope: owned.close_all(), close_errors=owned.close_errors, cancellation=owned.cancellation)
    _sync_directory(Path(path).parent, cancellation=owned.cancellation)
    return _stamp()


class CaptureDeadline(BaseException):
    """Parent budget exhausted; inspect retained claim, never replay it."""

    def __init__(self, *, final, phase='owned_alarm'):
        super().__init__('capture wall budget expired')
        self.final = final
        self.phase = phase


def _remember(scope, error):
    """Only caught errors, plus contexts that escaped this exact owner frame."""
    candidate = error
    owned = []
    for _ in range(4):
        if candidate is None:
            break
        if candidate is not error:
            trace = candidate.__traceback__
            for _depth in range(16):
                if trace is None or trace.tb_frame is scope['frame']:
                    break
                trace = trace.tb_next
            if trace is None or trace.tb_frame is not scope['frame']:
                break
        owned.append(candidate)
        following = candidate.__context__
        if following is candidate:
            break
        candidate = following
    # A new delivery can interrupt this bookkeeping. Earlier escaped errors
    # appear in the later error's context; never replace the first interruption.
    for candidate in reversed(owned):
        if isinstance(candidate, KeyboardInterrupt):
            scope['interrupt'] = scope['interrupt'] or candidate
            cancellation = scope['cancellation']
            cancellation['interrupt'] = cancellation['interrupt'] or candidate
            if cancellation['deadline'] is not None and cancellation['deadline'].final:
                scope['deadline'] = cancellation['deadline']
        elif isinstance(candidate, CaptureDeadline):
            if scope['deadline'] is None or candidate.final:
                scope['deadline'] = candidate
            cancellation = scope['cancellation']
            if cancellation['deadline'] is None or candidate.final:
                cancellation['deadline'] = candidate
        elif candidate is error:
            scope['other'] = candidate


def _owned(body, retire, *, close_errors=None, cancellation=None):
    """Fixed capture ownership: four guards precede every acquisition.

    First SIGINT and two owned timer deliveries can each interrupt one cleanup
    admission. Outer guards are already installed when an inner finalizer starts.
    Retirement must be idempotent; this is not exhaustive asynchronous safety.
    No body/callback is executed under a blanket cancellation mask.
    """
    cancellation = cancellation if cancellation is not None else _cancellation_record()
    scope = {'frame': sys._getframe(), 'cancellation': cancellation, 'interrupt': None, 'deadline': None,
             'other': None, 'consume_nonfinal': False, 'pending_alarm_observed': False}
    result = None
    try:
        try:
            try:
                try:
                    try:
                        result = body()
                    except BaseException as error:
                        _remember(scope, error)
                        raise
                    finally:
                        retire(scope)
                except BaseException as error:
                    _remember(scope, error)
                    raise
                finally:
                    retire(scope)
            except BaseException as error:
                _remember(scope, error)
                raise
            finally:
                retire(scope)
        except BaseException as error:
            _remember(scope, error)
            raise
        finally:
            retire(scope)
    except BaseException as error:
        _remember(scope, error)
    # Only locally pending exceptions select failure here. Shared evidence is
    # not itself a request for a normally completing cleanup helper to throw.
    try:
        return _finish_owned(scope, result, close_errors)
    except (KeyboardInterrupt, CaptureDeadline) as error:
        _remember(scope, error)
        return _finish_owned(scope, result, close_errors)


def _finish_owned(scope, result, close_errors):
    with _handoff():
        cancellation = scope['cancellation']
        if close_errors:
            _close_evidence(cancellation, close_errors)
        selected = scope['interrupt']
        deadline = scope['deadline']
        if selected is None and deadline is not None and (deadline.final or not scope['consume_nonfinal']):
            selected = deadline
        if selected is None:
            selected = scope['other']
        if selected is not None:
            _annotate(selected, cancellation)
    if selected is not None:
        raise selected
    return result


def _wall_bound(seconds, cleanup_seconds, body, *, cancellation=None):
    cancellation = cancellation if cancellation is not None else _cancellation_record()
    _signal_preflight()
    previous = signal.getsignal(signal.SIGALRM)
    expired = exhausted = restored = retiring = False
    def alarm(_signum, frame):
        nonlocal expired, exhausted
        final = expired
        if not expired:
            expired = True
            signal.setitimer(signal.ITIMER_REAL, cleanup_seconds)
        else:
            exhausted = True
        error = CaptureDeadline(final=final)
        cancellation['deadline'] = error
        if cancellation['interrupt'] is None:
            _live_interrupt(cancellation, frame, sys.exc_info()[1])
        with _handoff():
            selected = cancellation['interrupt'] or error
            _annotate(selected, cancellation)
        raise selected
    def enter_cleanup():
        nonlocal expired, exhausted
        with _handoff():
            if expired:
                if exhausted or signal.getitimer(signal.ITIMER_REAL)[0] <= 0:
                    exhausted = True
                    raise CaptureDeadline(final=True)
                return False
            signal.setitimer(signal.ITIMER_REAL, 0)
            pending = signal.SIGALRM in signal.sigpending()
            if pending:
                signal.sigwait({signal.SIGALRM})
                cancellation['deadline'] = CaptureDeadline(final=False, phase='cleanup_admission')
                cancellation['pending_alarm_observed'] = True
                cancellation['pending_alarm_observation'] = {'phase': 'cleanup_admission', 'final': False}
            expired = True
            signal.setitimer(signal.ITIMER_REAL, cleanup_seconds)
            return pending
    def execute():
        with _handoff():
            signal.signal(signal.SIGALRM, alarm)
            signal.setitimer(signal.ITIMER_REAL, seconds)
        return body(enter_cleanup)
    def retire(scope):
        nonlocal restored, retiring
        if restored:
            return
        retiring = True
        with _handoff():
            signal.setitimer(signal.ITIMER_REAL, 0)
            if signal.SIGALRM in signal.sigpending():
                signal.sigwait({signal.SIGALRM})
                scope['pending_alarm_observed'] = True
                cancellation['pending_alarm_observed'] = True
                if cancellation['pending_alarm_observation'] is None:
                    cancellation['pending_alarm_observation'] = {'phase': 'signal_retirement', 'final': expired}
                _remember(scope, CaptureDeadline(final=expired, phase='signal_retirement'))
            signal.signal(signal.SIGALRM, previous)
            restored = True
    return _owned(execute, retire, cancellation=cancellation)


def _preflight(ledger, binding, source, runtime, directory, timing, cancellation):
    _signal_preflight()
    _descriptor_preflight()
    _require(type(ledger) is Ledger and not ledger._read_only and not ledger.db.in_transaction
             and ledger._append_active is False and ledger._atomic_time is None and ledger._atomic_failed is False,
             'independent writable Ledger connection required')
    _require(type(source) is bytes and len(source) <= 8192, 'bounded built-in source bytes required')
    fields = {'instance_id', 'question_id', 'slot_id', 'channel_id', 'acceptance_sha256',
              'declaration_sha256', 'source_sha256', 'schema_sha256', 'producer_sha256', 'worker_sha256'}
    _require(type(binding) is dict and set(binding) == fields, 'exact binding fields required')
    for key, value in binding.items():
        pattern = r'[A-Za-z0-9_.:-]{1,120}' if key.endswith('_id') else r'[0-9a-f]{64}'
        _require(type(value) is str and re.fullmatch(pattern, value), 'invalid binding value')
    _require(binding['source_sha256'] == digest(source) and binding['schema_sha256'] == SCHEMA_SHA256
             and binding['producer_sha256'] == PRODUCER_SHA256 and binding['worker_sha256'] == digest(_WORKER),
             'source, schema or fixed program binding differs')
    _require(_read(Path(__file__), 65536, cancellation=cancellation) == _SOURCE
             and _read(_DIRECTORY / 'prospective_producer_worker.py', 16384, cancellation=cancellation) == _WORKER,
             'capture or worker source changed')
    producer = _read(_DIRECTORY / 'prospective_producer.py', 16384, cancellation=cancellation)
    _require(digest(producer) == PRODUCER_SHA256, 'fixed producer source changed')
    _require(type(runtime) is dict and set(runtime) == {'path', 'sha256', 'version'}, 'exact runtime fields required')
    _require(runtime['path'] == str(Path(sys.executable).resolve()) and runtime['version'] == sys.version,
             'runtime must be the current pinned interpreter')
    _require(digest(_read(runtime['path'], 256 * 1048576, cancellation=cancellation)) == runtime['sha256'], 'runtime bytes differ')
    _require(type(timing) is dict and set(timing) == {'not_before', 'latest_start', 'artifact_due', 'wall_seconds', 'cleanup_seconds'},
             'exact timing fields required')
    for name, maximum in [('wall_seconds', 120), ('cleanup_seconds', 5)]:
        value = timing[name]
        _require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= maximum, 'invalid process budget')
    beginning, latest, due = (instant(timing[key]) for key in ('not_before', 'latest_start', 'artifact_due'))
    _require(beginning <= latest < due, 'invalid timing order')
    now = instant(_stamp()['utc'])
    _require(beginning <= now <= latest, 'outside supplied start window')
    _require(directory.is_absolute() and directory.parent.resolve(strict=True) == directory.parent
             and not directory.exists() and not directory.is_symlink(), 'new channel directory under real parent required')
    _require(ledger.db.execute('PRAGMA synchronous').fetchone()[0] >= 2, 'SQLite FULL durability required')
    return producer


def _spawn_owned(owner, command, input_fd, streams):
    """Publish the native spawn's PID before unmasking pending cancellation.

    This critical section contains one native spawn, not Python constructor or
    exec-pipe waits. A kernel spawn that never returns is not a proven bound.
    """
    actions = [(os.POSIX_SPAWN_DUP2, input_fd, 0)]
    for name, target in [('stdout', 1), ('stderr', 2)]:
        actions.append((os.POSIX_SPAWN_DUP2, streams[name]['write_fd'], target))
    for descriptor in [input_fd] + [state[key] for state in streams.values() for key in ('read_fd', 'write_fd')]:
        actions.append((os.POSIX_SPAWN_CLOSE, descriptor))
    with _handoff() as previous:
        owner['pid'] = os.posix_spawn(command[0], command,
            {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'},
            file_actions=actions, setsigmask=previous, setsigdef={signal.SIGPIPE, signal.SIGCHLD})
        owner['spawn_returned'] = True


def _wait_owned(owner, observe):
    """Collect actual status for this PID; never synthesize an ECHILD exit."""
    if owner['pid'] is None or owner['reaped'] or owner['status_unavailable']:
        return
    with _handoff():
        try:
            waited, status = os.waitpid(owner['pid'], os.WNOHANG)
        except ChildProcessError:
            owner['status_unavailable'] = True
            return
        if waited == owner['pid']:
            owner['wait_status'] = status
            owner['returncode'] = os.waitstatus_to_exitcode(status)
            owner['reaped'] = True
            owner['wait_observed'] = observe()
        elif waited != 0:
            owner['status_unavailable'] = True


def _nonblocking_ledger(ledger, body, *, cancellation=None):
    """Own only this connection's temporary busy timeout, not a new ledger."""
    connection = ledger.db
    busy = connection.execute('PRAGMA busy_timeout').fetchone()[0]
    restored = retiring = False
    attempts = 0
    def execute():
        with _handoff():
            connection.execute('PRAGMA busy_timeout=0')
        return body()
    def retire(_scope):
        nonlocal restored, retiring, attempts
        if restored:
            return
        retiring = True
        attempts += 1
        with _handoff():
            connection.execute('PRAGMA busy_timeout=' + str(busy))
            restored = True
    return _owned(execute, retire, cancellation=cancellation)


def _append_once(ledger, kind, body, event_id, *, cancellation=None):
    """Recover only this independent append's uncommitted connection state.

    Trusted single-threaded caller: no concurrent/reentrant connection operation
    or callback mutation of Ledger internals. A committed event is never undone.
    """
    connection = ledger.db
    _require(not connection.in_transaction and ledger._append_active is False
             and ledger._atomic_time is None and ledger._atomic_failed is False,
             'independent inactive append required')
    retired = False
    def execute():
        return ledger.append(kind, body, event_id, exclusive=True)
    def retire(_scope):
        nonlocal retired
        if retired:
            return
        _require(ledger.db is connection, 'caller changed capture connection')
        with _handoff():
            if connection.in_transaction:
                connection.rollback()
            _require(not connection.in_transaction, 'append transaction retirement uncertain')
            ledger._append_active = False
            retired = True
    return _owned(execute, retire, cancellation=cancellation)


def capture_first_delivery(ledger, binding, source: bytes, *, runtime, channel_directory, timing):
    """Capture once in this ledger/instance/channel authority; never score it.

    Binding references and supplied times are not verified registration. The
    returned post-publication observation is required by any future consumer;
    ledger event timestamps alone do not prove when their commits completed.
    """
    cancellation = _cancellation_record()
    directory = Path(channel_directory)
    producer = _preflight(ledger, binding, source, runtime, directory, timing, cancellation)
    binding = dict(binding); timing = dict(timing); runtime = dict(runtime)
    key = digest(canonical([binding['instance_id'], binding['channel_id']]).encode())
    claim_id = 'prospective-capture:' + key + ':first'
    epoch = uuid.uuid4().hex
    claim_body = {'schema_version': 1, 'binding': binding, 'timing': timing, 'runtime': runtime,
                  'capture_sha256': digest(_SOURCE), 'channel_directory': str(directory), 'epoch': epoch,
                  'firstness_scope': 'this local ledger, instance and channel; no registration authentication'}
    def execute(enter_cleanup):
        claim = _append_once(ledger, 'prospective_capture_started', claim_body, claim_id, cancellation=cancellation)
        return _capture(ledger, claim, source, producer, directory, enter_cleanup, cancellation=cancellation)
    return _nonblocking_ledger(ledger, lambda: _wall_bound(timing['wall_seconds'], timing['cleanup_seconds'], execute,
        cancellation=cancellation), cancellation=cancellation)


def _capture(ledger, claim, source, producer, directory, enter_cleanup, *, cancellation):
    body = claim['body']; timing = body['timing']; binding = body['binding']
    began = _stamp(); errors = []; termination = None
    clock = {'consistent': True, 'observations': 1, 'violation_count': 0, 'first_violation': None}
    def record(value):
        clock['observations'] += 1
        if not _clock_consistent(began, [value]):
            clock['consistent'] = False; clock['violation_count'] += 1
            clock['first_violation'] = clock['first_violation'] or value
        return value
    def observe():
        return record(_stamp())
    def write(path, raw):
        return record(_write_new(path, raw, cancellation=cancellation))
    owner = {'pid': None, 'spawn_returned': False, 'reaped': False, 'returncode': None,
             'wait_status': None, 'wait_observed': None, 'status_unavailable': False}
    descriptors = _OwnedFDs(cancellation)
    launch = launched = None
    streams = {name: {'raw': bytearray(), 'observed': 0, 'eof': False, 'first_byte': None,
                     'last_byte': None, 'durable': None,
                     'read_fd': None, 'write_fd': None} for name in STREAM_CAPS}
    deadline = began['monotonic'] + timing['wall_seconds']
    cleanup_deadline = None
    command = [body['runtime']['path'], '-I', '-B', str(directory / 'worker.py'), binding['question_id'], SCHEMA_SHA256]

    def problem(operation, error):
        if len(errors) < 16:
            errors.append({'operation': operation, 'error_type': type(error).__name__})

    def cleanup():
        nonlocal cleanup_deadline
        if cleanup_deadline is None:
            cleanup_deadline = time.monotonic() + timing['cleanup_seconds']
        if owner['pid'] is not None:
            try:
                _wait_owned(owner, observe)
                if not owner['reaped'] and not owner['status_unavailable']:
                    try:
                        os.kill(owner['pid'], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    while not owner['reaped'] and not owner['status_unavailable']:
                        if time.monotonic() >= cleanup_deadline:
                            raise TimeoutError('owned child cleanup deadline')
                        _wait_owned(owner, observe)
                        if not owner['reaped'] and not owner['status_unavailable']:
                            time.sleep(min(.005, max(0, cleanup_deadline - time.monotonic())))
            except OSError as error:
                problem('reap_owned_child', error)
        for name, state in streams.items():
            target = descriptors.values.get(name + '_file')
            if target is not None:
                try:
                    os.fsync(target)
                    _sync_directory(directory, cancellation=cancellation)
                    stamp = observe()
                    state['durable'] = state['durable'] or stamp
                except (OSError, ValueError) as error:
                    problem('retain_' + name, error)

    def execute():
        nonlocal launch, launched, termination
        try:
            directory.mkdir(mode=0o700, exist_ok=False)
            _sync_directory(directory.parent, cancellation=cancellation)
            for name, raw in [('source.bin', source), ('producer.py', producer), ('worker.py', _WORKER)]:
                write(directory / name, raw)
            write(directory / 'claim.json', canonical(claim).encode())
            for name, state in streams.items():
                descriptors.open(name + '_file', directory / (name + '.bin'),
                                 os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW)
                descriptors.pipe(name + '_read', name + '_write')
                state['read_fd'] = descriptors.values[name + '_read']
                state['write_fd'] = descriptors.values[name + '_write']
            launch = observe()
            _require(instant(timing['not_before']) <= instant(launch['utc']) <= instant(timing['latest_start']),
                     'start window elapsed during setup')
            source_fd = descriptors.open('source', directory / 'source.bin', os.O_RDONLY | os.O_NOFOLLOW)
            _spawn_owned(owner, command, source_fd, streams)
            descriptors.close('source')
            launched = observe()
            for name in streams:
                descriptors.close(name + '_write')
            write(directory / 'start.json', canonical({'epoch': body['epoch'], 'pid': owner['pid'],
                       'command': command, 'launch_requested': launch, 'launch_returned': launched}).encode())
            with selectors.SelectSelector() as selector:
                for name in streams:
                    selector.register(streams[name]['read_fd'], selectors.EVENT_READ, name)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        termination = 'wall_timeout'; break
                    for ready, _ in selector.select(min(.05, remaining)):
                        name = ready.data; state = streams[name]
                        chunk = os.read(ready.fd, min(8192, STREAM_CAPS[name] + 1))
                        observed_at = observe()
                        if not chunk:
                            state['eof'] = True
                            selector.unregister(ready.fileobj)
                            # Artifact arrival is measured after actual EOF and fsync,
                            # independently of a later process exit or stderr error.
                            os.fsync(descriptors.values[name + '_file'])
                            _sync_directory(directory, cancellation=cancellation); state['durable'] = observe()
                            continue
                        state['first_byte'] = state['first_byte'] or observed_at
                        state['last_byte'] = observed_at
                        state['observed'] += len(chunk)
                        prefix = chunk[:max(0, STREAM_CAPS[name] - len(state['raw']))]
                        state['raw'].extend(prefix); _write_all(descriptors.values[name + '_file'], prefix)
                        if state['observed'] > STREAM_CAPS[name]:
                            termination = name + '_overflow'; break
                    if termination:
                        break
            if termination is None:
                while not owner['reaped'] and not owner['status_unavailable']:
                    _wait_owned(owner, observe)
                    if time.monotonic() >= deadline:
                        termination = 'wall_timeout'; break
                    if not owner['reaped'] and not owner['status_unavailable']:
                        time.sleep(min(.005, max(0, deadline - time.monotonic())))
        except CaptureDeadline as error:
            errors.extend(getattr(error, 'capture_close_errors', [])[:max(0, 16 - len(errors))])
            if error.final:
                raise
            termination = 'parent_deadline'
        except (OSError, ValueError) as error:
            termination = 'capture_error'; problem('capture', error)
    cleanup_complete = retired = False
    def retire(scope):
        nonlocal cleanup_complete, retired, termination
        if retired:
            return
        deadline_error = scope['deadline']
        final = deadline_error is not None and deadline_error.final
        if deadline_error is not None and not final:
            termination = 'parent_deadline'
            scope['consume_nonfinal'] = True
        if not cleanup_complete and not final:
            if enter_cleanup():
                termination = 'parent_deadline'
            cleanup()
            cleanup_complete = True
        descriptors.close_all()
        errors.extend(descriptors.close_errors[:max(0, 16 - len(errors))])
        retired = True
    _owned(execute, retire, close_errors=descriptors.close_errors, cancellation=cancellation)

    ended = observe()
    if owner['status_unavailable'] and termination is None:
        termination = 'wait_status_unavailable'
    clock_verified = clock['consistent']
    receipt = {'schema_version': 1, 'claim_id': claim['id'], 'claim_hash': claim['hash'], 'epoch': body['epoch'],
               'binding': binding, 'started': began, 'ended': ended, 'pid': owner['pid'], 'spawn_returned': owner['spawn_returned'],
               'launch_requested': launch, 'launch_returned': launched,
               'start_window_observed': launched is not None and instant(launched['utc']) <= instant(timing['latest_start']),
               'returncode': owner['returncode'], 'child_reaped': owner['reaped'],
               'wait_status': owner['wait_status'], 'wait_observed': owner['wait_observed'],
               'wait_status_unavailable': owner['status_unavailable'], 'termination': termination, 'errors': errors,
               'close_errors': cancellation['close_errors'][:16],
               'close_errors_truncated': cancellation['close_errors_truncated'],
               'clock_interval_verified': clock_verified, 'clock_observations': dict(clock), 'descendant_isolation': False,
               'quality': None, 'obligation_outcome': None, 'registered': False, 'streams': {}}
    for name, state in streams.items():
        complete = state['eof'] and state['observed'] <= STREAM_CAPS[name]
        receipt['streams'][name] = {'observed_prefix_bytes': len(state['raw']), 'observed_prefix_sha256': digest(bytes(state['raw'])),
            'retained_bytes': None, 'retained_sha256': None,
            'observed_bytes_lower_bound': state['observed'], 'eof_observed': state['eof'],
            'complete_bytes_observed': complete, 'full_sha256': digest(bytes(state['raw'])) if complete else None,
            'first_byte_observed': state['first_byte'], 'last_byte_observed': state['last_byte'],
            'file_durable_observed': state['durable'], 'path': str(directory / (name + '.bin')),
            'retention_verified': False}
        try:
            retained = _read(directory / (name + '.bin'), STREAM_CAPS[name], cancellation=cancellation)
            receipt['streams'][name]['retained_bytes'] = len(retained)
            receipt['streams'][name]['retained_sha256'] = digest(retained)
            receipt['streams'][name]['retention_verified'] = state['durable'] is not None and retained == bytes(state['raw'])
        except (OSError, ValueError) as error:
            problem('verify_' + name, error)
    for close_error in cancellation['close_errors']:
        if close_error not in errors and len(errors) < 16:
            errors.append(close_error)
    receipt['close_errors'] = cancellation['close_errors'][:16]
    receipt['close_errors_truncated'] = cancellation['close_errors_truncated']
    raw = canonical(receipt).encode()
    _require(len(raw) <= 65536, 'capture receipt exceeded bound')
    receipt_durable = write(directory / 'receipt.json', raw)
    terminal = _append_once(ledger, 'prospective_capture_finished', {'claim_id': claim['id'], 'claim_hash': claim['hash'],
        'receipt_path': str(directory / 'receipt.json'), 'receipt_sha256': digest(raw),
        'receipt_file_durable_observed': receipt_durable}, claim['id'] + ':finished', cancellation=cancellation)
    published = observe()
    clock_verified = clock['consistent']
    return {'receipt': receipt, 'terminal_event': terminal, 'publication_observed': published,
            'publication_clock_verified': clock_verified,
            'publication_clock_observations': dict(clock),
            'publication_by_artifact_due': clock_verified and instant(published['utc']) <= instant(timing['artifact_due']),
            'continuation_allowed': False,
            'scope': 'local unregistered capture evidence; no quality, firstness outside this authority, or obligation outcome'}
