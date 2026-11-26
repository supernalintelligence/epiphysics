"""One registered six-case execution. No key input, scoring, model or dispatch."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import math
import os
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time
from . import navigation_contracts as c
from . import store, dated_delivery as delivery, decision_diagnosis as history

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE) for module in (c, store, delivery, history))
PREPARATION = 'evidence_navigation_preparation'
CHECK = 'evidence_navigation_check'
CODE_FILES = ('navigation_contracts.py', 'navigation_runner.py', 'navigation_evaluation.py')
TRANSITIONS = {'improvement_completed', 'improvement_failed'}
PUBLIC_ROLES = ('map', 'tasks', 'candidate', 'runtime')
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_require = history._require


def utc(): return datetime.now(timezone.utc).isoformat()


class DeadlineExpired(TimeoutError):
    """Enclosing supervision deadline; never an ordinary candidate failure."""


def within_deadline(function, seconds, *args):
    """Local POSIX main-thread wall bound, including waits and closed-pipe children."""
    c.require(threading.current_thread() is threading.main_thread() and type(seconds) in (int, float)
        and math.isfinite(seconds) and seconds > 0, 'Positive main-thread deadline required')
    prior = signal.getitimer(signal.ITIMER_REAL)
    c.require(prior == (0.0, 0.0), 'An existing process alarm prevents navigation execution')
    previous = signal.getsignal(signal.SIGALRM)
    expired = False
    def expire(_signum, _frame):
        nonlocal expired
        if not expired:
            expired = True
            signal.setitimer(signal.ITIMER_REAL, c.CLOSE_SECONDS)
        raise DeadlineExpired('Navigation wall-clock deadline exceeded')
    signal.signal(signal.SIGALRM, expire)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        return function(*args)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def read(path, cap):
    path = Path(path)
    c.require(not path.is_symlink(), 'Symlink input refused')
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        c.require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, 'Bounded regular input required')
        raw = stream.read(cap + 1); after = os.fstat(stream.fileno())
    c.require(len(raw) <= cap and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Changed input during read')
    return raw


def write_new(path, raw, cap):
    c.require(type(raw) is bytes and len(raw) <= cap, 'Retained output bound')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    descriptor = os.open(Path(path).parent, os.O_RDONLY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def sources():
    path, raw, code = _SELF
    _require(IMPLEMENTATION_SOURCE == raw and IMPLEMENTATION_CODE is code and read(path, 65536) == raw
        and compile(raw, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize) == code, 'Executing runner source changed')
    for name, function, original in _FUNCTION_CODES:
        _require(globals().get(name) is function and function.__code__ is original, 'Runner callable changed')
    for name, value in _CONSTANTS:
        _require(type(globals().get(name)) is type(value) and globals().get(name) == value, 'Runner constant changed')
    _require(read(c.__file__, 65536) == c.IMPLEMENTATION_SOURCE
        and compile(c.IMPLEMENTATION_SOURCE, c.__file__, 'exec', dont_inherit=True, optimize=sys.flags.optimize) == c.IMPLEMENTATION_CODE, 'Executing contract changed')
    for name, function, original in c._FUNCTION_CODES:
        _require(getattr(c, name, None) is function and function.__code__ is original, 'Contract callable changed')
    for name, value in c._CONSTANTS:
        _require(type(getattr(c, name, None)) is type(value) and getattr(c, name) == value, 'Contract constant changed')
    return {name: c.digest(read(path.parent / name, c.MAX_SOURCE_BYTES)) for name in CODE_FILES}


def runtime_identity(value):
    c.keys(value, {'path', 'sha256', 'version'}, 'Python runtime')
    c.text(value['path'], 4096, 'runtime path'); c.sha(value['sha256']); c.text(value['version'], 512, 'runtime version')
    c.require(Path(value['path']).is_absolute() and Path(value['path']).resolve() == Path(sys.executable).resolve(), 'Wrong executing Python runtime')
    c.require(c.digest(read(Path(sys.executable).resolve(), 256 * 1048576)) == value['sha256'] and sys.version == value['version'], 'Python runtime bytes/version changed')
    return value


def scope(registration_hash):
    c.sha(registration_hash)
    return 'improvement-input:evidence-navigation-execution:' + registration_hash + ':'


def retained_size(directory, reserve=0):
    total, count = 0, 0
    for parent, dirs, files in os.walk(directory, followlinks=False):
        c.require(all(not (Path(parent) / name).is_symlink() for name in dirs), 'Symlink evidence directory')
        for name in files:
            info = (Path(parent) / name).lstat(); count += 1
            c.require(stat.S_ISREG(info.st_mode), 'Nonregular retained evidence')
            total += info.st_size
            c.require(count <= 256 and total + reserve <= c.MAX_BUNDLE_BYTES, 'Study retained-evidence bound')
    return total


def _events(ledger):
    bound = ledger.db.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(body AS BLOB))),0),COALESCE(MAX(length(CAST(body AS BLOB))),0) FROM events').fetchone()
    c.require(0 < bound[0] <= history.MAX_PREFIX_EVENTS and bound[1] <= history.MAX_PREFIX_BYTES and bound[2] <= history.MAX_EVENT_BYTES, 'Execution ledger bound')
    events = ledger.events(); history._prefix(events)
    return events


def accepted_registration(events, identity):
    event = history._find({event['id']: event for event in events}, identity)
    report, _ = delivery._accepted(event)
    c.require(report['phase'] == PREPARATION and report['contract_id'] == c.CONTRACT_ID and report['readiness'] == 'registered'
        and report['checks'] and all(value is True for value in report['checks'].values())
        and report['next_step']['action'] == event['body']['next_step']['action'] == 'run_textual_evidence_navigation_baseline', 'No accepted prospective navigation registration')
    registration = report['registration']
    c.keys(registration, {'schema_version', 'study_id', 'input_hashes', 'cohort_hash', 'key_hash', 'map_payload_hash',
        'source_hashes', 'case_ids', 'runtime', 'public_inputs', 'digest'}, 'registration')
    c.require(registration['digest'] == c.digest(c.canonical({key: value for key, value in registration.items() if key != 'digest'})), 'Registration digest differs')
    c.require(set(registration['public_inputs']) == set(PUBLIC_ROLES) and len(registration['case_ids']) == 6
        and len(set(registration['case_ids'])) == 6, 'Registration execution selection')
    return event, registration


def _guard(ledger, identity, expected):
    events = _events(ledger); parent, registration = accepted_registration(events, identity)
    c.require({key: events[-1][key] for key in ('seq', 'hash')} == expected, 'Competing ledger advancement')
    transitions = [event for event in events if event['kind'] in TRANSITIONS]
    c.require(transitions[-1] == parent and parent['body']['next_step']['state'] == 'queued', 'Registration no longer owns queue')
    finished = {event['body']['run_key'] for event in transitions}
    c.require(not any(event['kind'] == 'improvement_started' and event['body']['run_key'] not in finished for event in events), 'Unfinished controller claim prevents execution')
    c.require(sources() == registration['source_hashes'], 'Registered execution source changed')
    runtime_identity(registration['runtime'])
    return events, parent, registration


def _append(ledger, identity, expected, role, raw):
    c.require(len(raw) <= max(c.MAX_MAP_BYTES, c.MAX_RECEIPT_BYTES), 'Execution capture bound')
    digest = c.digest(raw); blob = ledger.root / 'blobs' / digest
    try: write_new(blob, raw, max(c.MAX_MAP_BYTES, c.MAX_RECEIPT_BYTES))
    except FileExistsError: c.require(read(blob, len(raw)) == raw, 'Existing execution blob differs')
    return ledger.append('observation', {'source': scope(identity['event_hash']) + role, 'content_hash': digest,
        'size': len(raw), 'media_type': 'application/octet-stream', 'published_at': None, 'event_at': None,
        'revision_of': None, 'timing_basis': 'collector clock; source times are claims'},
        'navigation:' + identity['event_hash'] + ':' + role, exclusive=True,
        validate=lambda _: _guard(ledger, identity, expected))


def _public_inputs(ledger, events, parent, registration):
    by_id = {event['id']: event for event in events}; result = {}
    caps = {'map': c.MAX_MAP_BYTES, 'tasks': c.MAX_TASK_BYTES, 'candidate': c.MAX_SOURCE_BYTES, 'runtime': c.MAX_RECEIPT_BYTES}
    for role in PUBLIC_ROLES:
        event = by_id[registration['public_inputs'][role]]
        c.require(event['kind'] == 'observation' and event['seq'] < parent['seq'], 'Public input was not prospectively captured')
        raw = read(ledger.root / 'blobs' / event['body']['content_hash'], caps[role])
        c.require(c.digest(raw) == event['body']['content_hash'] == registration['input_hashes'][role]
            and len(raw) == event['body']['size'], 'Registered public input differs')
        result[role] = raw
    c.require(c.decode(result['runtime'], c.MAX_RECEIPT_BYTES) == registration['runtime'], 'Registered runtime input differs')
    return result


def _run_child(directory, input_raw, candidate_raw, seconds, runtime, expected_sources):
    """Fixed child plus bounded, interruption-aware finalization of actual facts."""
    command = [runtime['path'], '-I', str(directory / 'candidate.py')]
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
    process, start, started = None, time.monotonic(), utc()
    streams = {name: {'file': None, 'raw': bytearray(), 'observed': 0, 'eof': False} for name in ('stdout', 'stderr')}
    termination, returncode, error = {'kind': 'completed', 'stream': None}, None, None
    cleanup_errors = []

    def safe(operation, function):
        try: return function()
        except DeadlineExpired: raise
        except (OSError, ValueError, subprocess.SubprocessError) as problem:
            if len(cleanup_errors) < 12:
                cleanup_errors.append(operation + ': ' + type(problem).__name__ + ': ' + str(problem)[:256])
            return None

    def kill_group():
        if process is None: return
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass

    def finalize_process():
        nonlocal returncode, termination
        if process is not None:
            safe('kill_process_group', kill_group)
            # A denied group kill is retained, never interpreted as successful cleanup.
            if process.poll() is None:
                safe('kill_child', process.kill)
            safe('reap_child', lambda: process.wait(timeout=2))
            returncode = process.poll()
            safe('close_child_stdout', process.stdout.close)
            safe('close_child_stderr', process.stderr.close)
        for name, state in streams.items():
            stream = state['file']
            if stream is not None and not stream.closed:
                safe('flush_' + name, stream.flush)
                safe('fsync_' + name, lambda stream=stream: os.fsync(stream.fileno()))
                safe('close_' + name, stream.close)
        if cleanup_errors and termination['kind'] == 'completed':
            termination = {'kind': 'runner_error', 'stream': None}

    def facts():
        receipt = {'schema_version': 1, 'command': command, 'cwd': str(directory), 'runtime': runtime,
            'input_sha256': c.digest(input_raw), 'candidate_sha256': c.digest(candidate_raw), 'seconds_limit': seconds,
            'started_at': started, 'ended_at': utc(), 'elapsed_seconds': time.monotonic() - start,
            'process_started': process is not None, 'returncode': returncode, 'termination': dict(termination),
            'error': error, 'cleanup_errors': list(cleanup_errors), 'sources_before': expected_sources, 'source_unchanged': None}
        for name, state in streams.items():
            raw = bytes(state['raw']); complete = state['eof'] and state['observed'] <= c.MAX_STREAM_BYTES
            receipt[name] = {'bytes': len(raw), 'sha256': c.digest(raw), 'observed_bytes': state['observed'],
                'complete': complete, 'full_sha256': c.digest(raw) if complete else None}
        return receipt

    try:
        directory.mkdir(exist_ok=False)
        write_new(directory / 'input.json', input_raw, c.MAX_INPUT_BYTES)
        write_new(directory / 'candidate.py', candidate_raw, c.MAX_SOURCE_BYTES)
        try:
            for name in streams:
                fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                streams[name]['file'] = os.fdopen(fd, 'wb')
            with open(directory / 'input.json', 'rb') as incoming:
                process = subprocess.Popen(command, cwd=directory, env=env, stdin=incoming, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, start_new_session=True, shell=False)
            deadline, drain = start + seconds, None
            def stop(kind, stream=None):
                nonlocal termination, drain
                if termination['kind'] == 'completed':
                    termination = {'kind': kind, 'stream': stream}; drain = time.monotonic() + 2
                    safe('stop_process_group', kill_group)
            with selectors.DefaultSelector() as selector:
                for name in streams: selector.register(getattr(process, name), selectors.EVENT_READ, name)
                while selector.get_map():
                    now = time.monotonic()
                    if now >= deadline: stop('timeout')
                    if drain is not None and now >= drain: break
                    for key, _ in selector.select(.05):
                        state = streams[key.data]; chunk = os.read(key.fd, 65536)
                        if not chunk:
                            state['eof'] = True; selector.unregister(key.fileobj); continue
                        state['observed'] += len(chunk); prefix = chunk[:max(0, c.MAX_STREAM_BYTES - len(state['raw']))]
                        if prefix:
                            state['raw'].extend(prefix); state['file'].write(prefix); state['file'].flush(); os.fsync(state['file'].fileno())
                        if state['observed'] > c.MAX_STREAM_BYTES: stop('output_limit', key.data)
            if process.poll() is None:
                try: process.wait(timeout=max(.001, deadline - time.monotonic()) if termination['kind'] == 'completed' else 2)
                except subprocess.TimeoutExpired:
                    stop('timeout'); safe('reap_timed_out_child', lambda: process.wait(timeout=2))
            returncode = process.poll()
        except DeadlineExpired: raise
        except (OSError, ValueError, subprocess.SubprocessError) as problem:
            error = type(problem).__name__ + ': ' + str(problem)[:512]
            termination = {'kind': 'spawn_error' if process is None else 'runner_error', 'stream': None}
        finalize_process()
        receipt = facts()
        # This whole persistence/audit boundary is covered by the outer handler.
        write_new(directory / 'runtime.json', c.canonical(receipt), c.MAX_RECEIPT_BYTES)
        try: receipt['source_unchanged'] = sources() == expected_sources and read(directory / 'candidate.py', c.MAX_SOURCE_BYTES) == candidate_raw
        except DeadlineExpired: raise
        except (ValueError, OSError): receipt['source_unchanged'] = False
        write_new(directory / 'receipt.json', c.canonical(receipt), c.MAX_RECEIPT_BYTES)
        return receipt
    except DeadlineExpired as problem:
        # within_deadline arms one closing reserve on the FIRST alarm wherever it
        # lands, including setup, cleanup and writes. A second alarm gets no retry.
        if signal.getitimer(signal.ITIMER_REAL)[0] <= 0:
            raise
        termination = {'kind': 'enclosing_deadline', 'stream': None}
        error = type(problem).__name__ + ': ' + str(problem)[:512]
        finalize_process()
        if directory.is_dir():
            path = directory / 'runtime.json'
            if path.exists(): path = directory / 'runtime-interrupted.json'
            write_new(path, c.canonical(facts()), c.MAX_RECEIPT_BYTES)
        raise


def run_registered(ledger_path, identity):
    """Actual execution entry; callers must obtain accepted preparation first."""
    return within_deadline(_run_registered, c.TOTAL_SECONDS - c.EVALUATE_SECONDS - c.CLOSE_SECONDS,
        ledger_path, identity, time.monotonic(), utc())


def _run_registered(ledger_path, identity, initial_start, initial_started):
    readonly = store.Ledger.open_readonly(ledger_path)
    try:
        events = _events(readonly); parent, registration = accepted_registration(events, identity)
        expected = {key: events[-1][key] for key in ('seq', 'hash')}
        _guard(readonly, identity, expected)
        c.require(not any(event['kind'] == 'observation' and event['body']['source'].startswith(scope(identity['event_hash'])) for event in events), 'Registration already has execution evidence; no retry')
        inputs = _public_inputs(readonly, events, parent, registration)
        root = readonly.root
    finally: readonly.close()
    public_map = c.validate_map(c.decode(inputs['map'], c.MAX_MAP_BYTES))
    cohort = c.validate_cohort(c.decode(inputs['tasks'], c.MAX_TASK_BYTES), public_map)
    c.require(c.digest(c.canonical(cohort)) == registration['cohort_hash']
        and [case['case_id'] for case in cohort['cases']] == registration['case_ids'], 'Registered case selection differs')
    c.require(time.monotonic() - initial_start <= c.PREPARE_SECONDS, 'Execution preflight budget exceeded')
    base = root / 'navigation-runs'; c.require(not base.is_symlink(), 'Symlink run root refused'); base.mkdir(exist_ok=True)
    directory = base / identity['event_hash']; directory.mkdir(exist_ok=False)
    start, started = initial_start, initial_started
    claim = {'schema_version': 1, 'registration': identity, 'registration_digest': registration['digest'],
        'started_at': started, 'started_monotonic': start, 'source_hashes': sources(), 'case_ids': registration['case_ids'],
        'public_input_hashes': {role: c.digest(raw) for role, raw in inputs.items()}, 'total_seconds': c.TOTAL_SECONDS}
    write_new(directory / 'claim.json', c.canonical(claim), c.MAX_RECEIPT_BYTES)
    write_new(directory / 'registration.json', c.canonical(parent), 1048576)
    for role, raw in inputs.items(): write_new(directory / (role + '.bin'), raw, max(c.MAX_MAP_BYTES, c.MAX_SOURCE_BYTES))
    ledger, observed, outcomes = store.Ledger(root), {}, []
    try:
        def capture(role, raw):
            nonlocal expected
            write_new(directory / ('record-' + role + '.bin'), raw, max(c.MAX_MAP_BYTES, c.MAX_RECEIPT_BYTES))
            event = _append(ledger, identity, expected, role, raw)
            expected = {key: event[key] for key in ('seq', 'hash')}; observed[role] = event['id']
            write_new(directory / ('capture-' + str(len(observed)) + '.json'), c.canonical({'role': role, 'event_id': event['id'], 'head': expected, 'event': event}), c.MAX_RECEIPT_BYTES)
            return event
        claim_event = capture('claim', c.canonical(claim))
        halted = None
        for ordinal, case in enumerate(cohort['cases']):
            remaining = c.TOTAL_SECONDS - (time.monotonic() - start)
            if halted is not None or remaining < c.ATTEMPT_SECONDS + c.EVALUATE_SECONDS + c.CLOSE_SECONDS:
                outcomes.append({'case_id': case['case_id'], 'state': 'not_started', 'reason': halted or 'remaining_total_budget'})
                continue
            _guard(ledger, identity, expected)
            input_raw = c.candidate_input(public_map, case)
            retained_size(directory, len(input_raw) + len(inputs['candidate']) + 2 * c.MAX_STREAM_BYTES + 3 * c.MAX_RECEIPT_BYTES)
            attempt_claim = {'schema_version': 1, 'case_id': case['case_id'], 'ordinal': ordinal,
                'execution_claim': {'event_id': claim_event['id'], 'event_hash': claim_event['hash']},
                'input_sha256': c.digest(input_raw), 'candidate_sha256': c.digest(inputs['candidate']), 'seconds_limit': c.ATTEMPT_SECONDS}
            event = capture('attempt-' + str(ordinal) + '-claim', c.canonical(attempt_claim))
            receipt = _run_child(directory / ('attempt-' + str(ordinal)), input_raw, inputs['candidate'],
                c.ATTEMPT_SECONDS, registration['runtime'], registration['source_hashes'])
            for stream in ('stdout', 'stderr'):
                capture('attempt-' + str(ordinal) + '-' + stream, read(directory / ('attempt-' + str(ordinal)) / stream, c.MAX_STREAM_BYTES))
            capture('attempt-' + str(ordinal) + '-receipt', c.canonical(receipt))
            outcomes.append({'case_id': case['case_id'], 'state': 'attempted', 'ordinal': ordinal,
                'claim_event_id': event['id'], 'receipt_sha256': c.digest(c.canonical(receipt))})
            if not receipt['source_unchanged']: halted = 'source_changed'
            elif receipt['cleanup_errors']: halted = 'cleanup_failed'
        seal = {'schema_version': 1, 'registration': identity, 'claim_sha256': c.digest(c.canonical(claim)),
            'ended_at': utc(), 'elapsed_seconds': time.monotonic() - start, 'outcomes': outcomes,
            'observations': deepcopy(observed), 'scope': 'Actual first fixed local attempts only; no key access or scoring', 'retry_allowed': False}
        write_new(directory / 'seal.json', c.canonical(seal), c.MAX_RECEIPT_BYTES)
        capture('seal', c.canonical(seal))
        write_new(directory / 'execution-capture.json', c.canonical({'observations': observed, 'checkpoint': expected}), c.MAX_RECEIPT_BYTES)
        return {'directory': str(directory), 'observations': observed, 'checkpoint': expected}
    except BaseException as error:
        if isinstance(error, DeadlineExpired) and signal.getitimer(signal.ITIMER_REAL)[0] <= 0:
            raise
        write_new(directory / 'execution-error.json', c.canonical({'error': type(error).__name__, 'message': str(error)[:512],
            'observations': observed, 'outcomes': outcomes, 'retry_allowed': False}), c.MAX_RECEIPT_BYTES)
        raise
    finally: ledger.close()


def validate_execution(public_map, cohort, registration, identity, execution, observations):
    """Check retained execution facts without a key, process launch or ledger read."""
    c.require(sum(map(len, execution.values())) <= c.MAX_BUNDLE_BYTES, 'Execution evidence byte bound')
    c.keys(observations, execution, 'execution observation roles')
    for role, event in observations.items():
        history._event(event)
        c.require(event['kind'] == 'observation' and event['body']['source'] == scope(identity['event_hash']) + role
            and event['body']['content_hash'] == c.digest(execution[role]) and event['body']['size'] == len(execution[role]), 'Execution observation binding')
    claim = c.decode(execution['claim'], c.MAX_RECEIPT_BYTES); seal = c.decode(execution['seal'], c.MAX_RECEIPT_BYTES)
    c.keys(claim, {'schema_version', 'registration', 'registration_digest', 'started_at', 'started_monotonic', 'source_hashes', 'case_ids', 'public_input_hashes', 'total_seconds'}, 'execution claim')
    c.require(claim['schema_version'] == 1 and claim['registration'] == identity and claim['registration_digest'] == registration['digest']
        and claim['case_ids'] == registration['case_ids'] and claim['source_hashes'] == registration['source_hashes']
        and claim['public_input_hashes'] == {role: registration['input_hashes'][role] for role in PUBLIC_ROLES}
        and claim['total_seconds'] == c.TOTAL_SECONDS, 'Execution claim differs from registration')
    c.require(type(claim['started_monotonic']) in (int, float) and math.isfinite(claim['started_monotonic']), 'Execution monotonic clock')
    c.keys(seal, {'schema_version', 'registration', 'claim_sha256', 'ended_at', 'elapsed_seconds', 'outcomes', 'observations', 'scope', 'retry_allowed'}, 'execution seal')
    c.require(seal['schema_version'] == 1 and seal['registration'] == identity and seal['claim_sha256'] == c.digest(execution['claim'])
        and seal['retry_allowed'] is False and type(seal['outcomes']) is list and len(seal['outcomes']) == 6, 'Execution seal identity')
    wall = (store.instant(seal['ended_at']) - store.instant(claim['started_at'])).total_seconds()
    c.require(type(seal['elapsed_seconds']) in (int, float) and math.isfinite(seal['elapsed_seconds'])
        and 0 <= seal['elapsed_seconds'] <= wall + .1, 'Execution duration')
    c.require(store.instant(claim['started_at']) <= store.instant(observations['claim']['recorded_at'])
        <= store.instant(seal['ended_at']) <= store.instant(observations['seal']['recorded_at']), 'Execution seal/claim capture times')
    expected, attempts, prior_end = {'claim', 'seal'}, {}, observations['claim']
    for ordinal, (case, outcome) in enumerate(zip(cohort['cases'], seal['outcomes'])):
        c.require(outcome.get('case_id') == case['case_id'], 'Execution case order differs')
        if outcome.get('state') == 'not_started':
            c.keys(outcome, {'case_id', 'state', 'reason'}, 'unstarted case'); c.text(outcome['reason'], 512, 'unstarted reason')
            attempts[case['case_id']] = outcome
            continue
        c.keys(outcome, {'case_id', 'state', 'ordinal', 'claim_event_id', 'receipt_sha256'}, 'attempted case')
        c.require(outcome['state'] == 'attempted' and type(outcome['ordinal']) is int and outcome['ordinal'] == ordinal, 'Attempt ordinal')
        roles = {suffix: 'attempt-' + str(ordinal) + '-' + suffix for suffix in ('claim', 'receipt', 'stdout', 'stderr')}
        expected.update(roles.values())
        beginning, finish = observations[roles['claim']], observations[roles['receipt']]
        c.require(prior_end['seq'] < beginning['seq'] < finish['seq'] < observations['seal']['seq'], 'Attempt chronology')
        attempt_claim = c.decode(execution[roles['claim']], c.MAX_RECEIPT_BYTES)
        c.require(attempt_claim == {'schema_version': 1, 'case_id': case['case_id'], 'ordinal': ordinal,
            'execution_claim': {'event_id': observations['claim']['id'], 'event_hash': observations['claim']['hash']},
            'input_sha256': c.digest(c.candidate_input(public_map, case)), 'candidate_sha256': registration['input_hashes']['candidate'],
            'seconds_limit': c.ATTEMPT_SECONDS}, 'First attempt claim differs')
        receipt = c.decode(execution[roles['receipt']], c.MAX_RECEIPT_BYTES)
        c.keys(receipt, {'schema_version', 'command', 'cwd', 'runtime', 'input_sha256', 'candidate_sha256', 'seconds_limit',
            'started_at', 'ended_at', 'elapsed_seconds', 'process_started', 'returncode', 'termination', 'error',
            'sources_before', 'source_unchanged', 'stdout', 'stderr', 'cleanup_errors'}, 'attempt process receipt')
        c.require(type(receipt['cleanup_errors']) is list and len(receipt['cleanup_errors']) <= 12, 'Cleanup error bound')
        for error in receipt['cleanup_errors']: c.text(error, 512, 'cleanup error')
        c.require(receipt['schema_version'] == 1 and receipt['runtime'] == registration['runtime']
            and receipt['input_sha256'] == attempt_claim['input_sha256'] and receipt['candidate_sha256'] == attempt_claim['candidate_sha256']
            and receipt['sources_before'] == registration['source_hashes'] and type(receipt['source_unchanged']) is bool
            and receipt['seconds_limit'] == c.ATTEMPT_SECONDS, 'Attempt source/runtime/input identity')
        c.require(type(receipt['cwd']) is str and Path(receipt['cwd']).is_absolute()
            and Path(receipt['cwd']).name == 'attempt-' + str(ordinal)
            and Path(receipt['cwd']).parent.name == identity['event_hash']
            and receipt['command'] == [registration['runtime']['path'], '-I', str(Path(receipt['cwd']) / 'candidate.py')], 'Fixed candidate command')
        c.keys(receipt['termination'], {'kind', 'stream'}, 'attempt termination')
        kind, stream = receipt['termination']['kind'], receipt['termination']['stream']
        c.require(kind in {'completed', 'timeout', 'output_limit', 'spawn_error', 'runner_error'} and type(receipt['process_started']) is bool
            and (receipt['returncode'] is None or type(receipt['returncode']) is int), 'Attempt termination schema')
        c.require((kind == 'output_limit' and stream in {'stdout', 'stderr'}) or kind != 'output_limit' and stream is None, 'Attempt termination stream')
        c.require((kind == 'spawn_error') == (receipt['process_started'] is False), 'Spawn outcome differs')
        if kind == 'completed': c.require(type(receipt['returncode']) is int and not receipt['cleanup_errors'], 'Completed process exit absent or cleanup failed')
        duration = (store.instant(receipt['ended_at']) - store.instant(receipt['started_at'])).total_seconds()
        c.require(type(receipt['elapsed_seconds']) in (int, float) and math.isfinite(receipt['elapsed_seconds'])
            and 0 <= receipt['elapsed_seconds'] <= duration + .1
            and store.instant(beginning['recorded_at']) <= store.instant(receipt['started_at'])
            <= store.instant(receipt['ended_at']) <= store.instant(finish['recorded_at']), 'Attempt runtime/capture chronology')
        for name in ('stdout', 'stderr'):
            raw = execution[roles[name]]; meta = receipt[name]
            c.keys(meta, {'bytes', 'sha256', 'observed_bytes', 'complete', 'full_sha256'}, 'attempt output stream')
            c.require(type(meta['bytes']) is int and type(meta['observed_bytes']) is int and type(meta['complete']) is bool
                and meta['bytes'] == len(raw) <= c.MAX_STREAM_BYTES and meta['sha256'] == c.digest(raw)
                and meta['observed_bytes'] >= len(raw), 'Attempt output identity')
            c.require((meta['complete'] and meta['observed_bytes'] == len(raw) and meta['full_sha256'] == c.digest(raw))
                or (not meta['complete'] and meta['full_sha256'] is None), 'Attempt output completeness')
            if kind == 'completed': c.require(meta['complete'], 'Completed process has incomplete output')
            if kind == 'output_limit' and stream == name:
                c.require(not meta['complete'] and len(raw) == c.MAX_STREAM_BYTES and meta['observed_bytes'] > len(raw), 'Overflow prefix is absent')
            c.require(beginning['seq'] < observations[roles[name]]['seq'] < finish['seq'], 'Stream observation order')
        c.require(outcome['claim_event_id'] == beginning['id'] and outcome['receipt_sha256'] == c.digest(execution[roles['receipt']]), 'Sealed first attempt identity')
        attempts[case['case_id']] = {'state': 'attempted', 'receipt': receipt, 'stdout': execution[roles['stdout']], 'stderr': execution[roles['stderr']]}
        prior_end = finish
    c.keys(execution, expected, 'complete execution evidence')
    c.require(seal['observations'] == {role: event['id'] for role, event in observations.items() if role != 'seal'}, 'Seal omitted a scoped capture')
    return attempts, claim, seal


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True)
    parser.add_argument('--registration-id', required=True)
    parser.add_argument('--registration-hash', required=True)
    args = parser.parse_args()
    result = run_registered(args.store, {'event_id': args.registration_id, 'event_hash': args.registration_hash})
    print(c.canonical(result).decode('utf-8'))


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, '__module__', None) == __name__ and hasattr(function, '__code__'))
_CONSTANTS = tuple((name, deepcopy(globals()[name])) for name in ('PREPARATION', 'CHECK', 'CODE_FILES', 'TRANSITIONS', 'PUBLIC_ROLES'))

if __name__ == '__main__': main()
