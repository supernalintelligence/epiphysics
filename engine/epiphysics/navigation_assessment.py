"""Prospective navigation registration and later retained-only check; never execute."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import math
import re
import sqlite3
import sys
import time
from . import navigation_contracts as c, navigation_runner as runner, navigation_evaluation as evaluation
from . import public_map_assessment as mapping, dated_delivery as delivery, decision_diagnosis as history, store

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE) for module in (c, runner, evaluation, mapping, delivery, history, store))
PREPARATION, CHECK = runner.PREPARATION, runner.CHECK
PHASES = {PREPARATION: 'prospective_textual_navigation', CHECK: 'retained_textual_navigation_check'}
CONTRACT_ID = c.CONTRACT_ID
PHASE_NEXT_ACTIONS = {PREPARATION: frozenset({'run_textual_evidence_navigation_baseline', 'repair_evidence_navigation_protocol'}),
    CHECK: frozenset({'prepare_independent_evidence_navigation_comparison', 'diagnose_textual_navigation_failure', 'repair_navigation_execution_contract'})}
SEMANTIC_ACTIONS = frozenset({'prepare_evidence_navigation_evaluation', 'repair_evidence_navigation_protocol', 'run_textual_evidence_navigation_baseline'})
NEXT_ACTIONS = frozenset().union(*PHASE_NEXT_ACTIONS.values())
SOURCE_NAMES = ('navigation_assessment.py', 'navigation_contracts.py', 'navigation_runner.py', 'navigation_evaluation.py', *mapping.SOURCE_NAMES)
MAX_SECONDS, MAX_PREFIX_EVENTS, MAX_PREFIX_BYTES, MAX_BUNDLE_BYTES = 10, 4096, 8388608, 16777216
MAX_SOURCE_BYTES = 131072
BASE_ROLES = frozenset({'map', 'tasks', 'key', 'candidate', 'runtime', 'authorship'})
AUTHOR_CHECKS = ('generic_candidate_reviewed', 'no_key_to_candidate', 'independent_key_reviewed', 'tasks_answerable_from_map')
CONTRACT = {**deepcopy(c.CONTRACT), 'phases': PHASES, 'successors': {phase: sorted(actions) for phase, actions in PHASE_NEXT_ACTIONS.items()},
    'prospective_registration_required': True, 'author_checks': list(AUTHOR_CHECKS),
    'controller_envelope_limits': {'prefix_bytes': MAX_PREFIX_BYTES, 'prefix_events': MAX_PREFIX_EVENTS,
        'bundle_bytes': MAX_BUNDLE_BYTES, 'retained_check_seconds': MAX_SECONDS},
    'closing_acceptance': {'total_seconds_from_execution_start': c.TOTAL_SECONDS,
        'seconds_after_evaluator_end': c.CLOSE_SECONDS,
        'boundaries': ['evaluation_capture', 'locked_final_completion'],
        'late_result': 'Preserve first attempts and descriptive scores; refuse within-budget success and comparison successor'},
    'evaluator_completion': 'Independent supervising caller outcome required: exact report/stdout, registered runtime/source/key identities, fixed argv, ordered captures, observed elapsed <=60 seconds, exited zero without cleanup errors; evaluator-written bytes alone are provisional',
    'assurance': 'Trusted local process/capture and authorship attribution; no malicious-host or independent witness proof'}
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_json, _read, _canonical, _hash = history._json, history._read, history._canonical, history._hash
_equal, _accepted, _blob, _observation = delivery._equal, delivery._accepted, delivery._blob, delivery._observation
_prefix, _find, _identity = history._prefix, history._find, history._identity
TRANSITIONS = {'improvement_completed', 'improvement_failed'}


def _scope(study): return 'improvement-input:evidence-navigation-preparation:' + study + ':'


def _input_limit(role):
    if role == 'map': return c.MAX_MAP_BYTES
    if role in BASE_ROLES or role in {'evaluation', 'evaluation_execution'} or role.startswith('execution:'): return c.MAX_RECEIPT_BYTES
    return None


def _role_limit(role):
    if role in {'request', 'contract'}: return 65536
    if role == 'ledger_prefix': return MAX_PREFIX_BYTES
    if role in {'packet', 'evidence_origin', 'queue_parent', 'failure_request', 'failure_claim', 'semantic_parent'}: return 1048576
    if role == 'assessment_report': return c.MAX_REPORT_BYTES
    if role.startswith('code:epiphysics.') and role[16:] + '.py' in SOURCE_NAMES: return MAX_SOURCE_BYTES
    if role.startswith(('observation:', 'blob:')): return 1048576
    return None


class PreparationError(ValueError):
    def __init__(self, message, artifacts):
        super().__init__(message)
        self.artifacts = {}
        for role, raw in artifacts.items():
            cap = _role_limit(role)
            if cap is not None and type(raw) is bytes and len(raw) <= cap and sum(map(len, self.artifacts.values())) + len(raw) <= MAX_BUNDLE_BYTES:
                self.artifacts[role] = raw


class ClosureDeadlineExceeded(ValueError):
    """The original study cannot be accepted after its closing deadline."""


def _put(artifacts, role, raw):
    cap = _role_limit(role)
    c.require(cap is not None and type(raw) is bytes and len(raw) <= cap, 'Navigation artifact role/bound')
    c.require(sum(map(len, artifacts.values())) - len(artifacts.get(role, b'')) + len(raw) <= MAX_BUNDLE_BYTES, 'Navigation controller bundle bound')
    artifacts[role] = raw


def _current_sources():
    mapping._current_sources()
    require = history._require
    path, raw, code = _SELF
    require(IMPLEMENTATION_SOURCE == raw and IMPLEMENTATION_CODE is code and _read(path, MAX_SOURCE_BYTES) == raw
        and compile(raw, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize) == code, 'Navigation adapter source changed')
    for name, function, original in _FUNCTION_CODES:
        require(globals().get(name) is function and function.__code__ is original, 'Navigation adapter callable changed')
    for name, value in _CONSTANTS:
        require(type(globals().get(name)) is type(value) and globals().get(name) == value, 'Navigation adapter constant changed')
    for module in (c, evaluation):
        require(_read(module.__file__, MAX_SOURCE_BYTES) == module.IMPLEMENTATION_SOURCE and
            compile(module.IMPLEMENTATION_SOURCE, module.__file__, 'exec', dont_inherit=True, optimize=sys.flags.optimize) == module.IMPLEMENTATION_CODE, 'Navigation dependency loaded source changed')
        for name, function, original in module._FUNCTION_CODES:
            require(getattr(module, name, None) is function and function.__code__ is original, 'Navigation dependency callable changed')
        for name, value in module._CONSTANTS:
            require(type(getattr(module, name, None)) is type(value) and getattr(module, name) == value, 'Navigation dependency constant changed')
    runner.sources(); mapping._current_sources()
    return {'code:epiphysics.' + name[:-3]: _read(path.parent / name, MAX_SOURCE_BYTES) for name in SOURCE_NAMES}


def _request(value):
    c.keys(value, {'schema_version', 'phase', 'study_id', 'origin', 'ledger_path', 'evidence_origin', 'queue_parent', 'evidence_checkpoint', 'paths'}, 'navigation request')
    c.require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['phase'] in PHASES
        and type(value['study_id']) is str and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', value['study_id']), 'Navigation request identity')
    c.keys(value['origin'], {'step_id'}, 'navigation origin'); c.text(value['origin']['step_id'], 200, 'queued step')
    _identity(value['evidence_origin']); _identity(value['queue_parent'])
    c.keys(value['evidence_checkpoint'], {'seq', 'event_id', 'event_hash'}, 'navigation checkpoint')
    _identity({key: value['evidence_checkpoint'][key] for key in ('event_id', 'event_hash')})
    c.require(type(value['evidence_checkpoint']['seq']) is int and value['evidence_checkpoint']['seq'] > 0, 'Navigation sequence')
    c.keys(value['paths'], {'contract', 'packet'}, 'navigation paths')
    c.require(all(type(path) is str and Path(path).is_absolute() and len(path.encode()) <= 4096 and '\0' not in path
        for path in [value['ledger_path'], *value['paths'].values()]), 'Bounded absolute navigation paths')


def _packet(artifacts):
    value = _json(artifacts['packet']); request = _json(artifacts['request'])
    c.keys(value, {'schema_version', 'phase', 'observations'}, 'navigation packet')
    c.require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['phase'] == request['phase']
        and type(value['observations']) is dict and 6 <= len(value['observations']) <= 40, 'Navigation packet shape')
    c.require(all(_input_limit(role) is not None and type(event) is str and 0 < len(event) <= 256 for role, event in value['observations'].items())
        and len(set(value['observations'].values())) == len(value['observations']), 'Navigation packet roles/observations')
    return value


def _lineage(request, artifacts, events):
    by_id = _prefix(events); origin = _find(by_id, request['evidence_origin']); parent = _find(by_id, request['queue_parent'])
    _equal(_json(artifacts['evidence_origin']), origin, 'Captured C11 origin'); _equal(_json(artifacts['queue_parent']), parent, 'Captured navigation parent')
    _equal({'seq': events[-1]['seq'], 'event_id': events[-1]['id'], 'event_hash': events[-1]['hash']}, request['evidence_checkpoint'], 'Navigation checkpoint')
    original, declared = _accepted(origin)
    c.require(original['phase'] == mapping.PHASE and original['stage'] == mapping.STAGE and original['contract_id'] == mapping.CONTRACT_ID
        and original['readiness'] == 'static_view_prepared' and original['checks'] and all(value is True for value in original['checks'].values())
        and origin['body']['next_step']['action'] == original['next_step']['action'] == 'prepare_evidence_navigation_evaluation', 'Origin is not accepted C11 preparation')
    identity = {'event_id': origin['id'], 'event_hash': origin['hash'], 'assessment_hash': origin['body']['assessment_identity']['hash'],
        'decision_assessment_hash': original['assessment_identity']['hash'], 'capture_sha256': _hash(artifacts['evidence_origin'])}
    c.require(parent['body']['next_step']['id'] == request['origin']['step_id'] and parent['body']['next_step']['state'] == 'queued', 'Navigation request does not own queued step')
    semantic, mode = parent, 'initial'
    if parent['kind'] == 'improvement_failed':
        c.require(parent['body']['next_step']['action'] == 'diagnose_failed_assessment', 'Wrong failure successor')
        claim, semantic, previous_request = (_json(artifacts[role]) for role in ('failure_claim', 'semantic_parent', 'failure_request'))
        _request(previous_request)
        _equal(by_id.get(claim['id']), claim, 'Failure claim'); _equal(by_id.get(semantic['id']), semantic, 'Failure semantic parent')
        c.require(semantic['seq'] < claim['seq'] < parent['seq'] and claim['kind'] == 'improvement_started'
            and claim['body']['run_key'] == parent['body']['run_key'], 'Navigation failure chronology')
        _equal(claim['body']['request'], parent['body']['request'], 'Failure request')
        _equal(claim['body']['claimed_step'], semantic['body']['next_step'], 'Failed semantic step')
        _equal(previous_request['evidence_origin'], request['evidence_origin'], 'Failure immutable C11 origin')
        _equal(previous_request['phase'], request['phase'], 'Failure phase')
        _equal(previous_request['queue_parent'], {'event_id': semantic['id'], 'event_hash': semantic['hash']}, 'Failure original parent')
        _equal(previous_request['origin']['step_id'], parent['body']['request']['after_step'], 'Failure original step')
        _equal(_hash(artifacts['failure_request']), parent['body']['request']['manifest']['decision-input:request'], 'Failure request binding')
        _equal([event for event in events if event['kind'] in TRANSITIONS and event['seq'] < claim['seq']][-1], semantic, 'Failure queued owner')
        observation = _observation(by_id, 'improvement:' + parent['body']['run_key'] + ':input:decision-input:request', 'improvement-input:decision-input:request')
        c.require(claim['seq'] < observation['seq'] < parent['seq'], 'Failure input order'); _equal(_blob(artifacts, observation), artifacts['failure_request'], 'Failure captured bytes')
        mode = 'failed_attempt_continuation'
    action = semantic['body']['next_step']['action']; previous, registration = None, None
    if request['phase'] == PREPARATION:
        if action == 'prepare_evidence_navigation_evaluation': _equal(semantic, origin, 'Initial C12 predecessor')
        else:
            c.require(action == 'repair_evidence_navigation_protocol', 'Not a navigation preparation step')
            previous, _ = _accepted(semantic)
            c.require(previous['phase'] == PREPARATION and previous['contract_id'] == CONTRACT_ID
                and previous['next_step']['action'] == action and not all(previous['checks'].values()), 'Not a checked preparation repair')
            _equal(previous['evidence_origin'], identity, 'Preparation repair origin')
    else:
        c.require(action == 'run_textual_evidence_navigation_baseline', 'Not a registered execution/check step')
        _, registration = runner.accepted_registration(events, {'event_id': semantic['id'], 'event_hash': semantic['hash']})
        registered, _ = _accepted(semantic); _equal(registered['evidence_origin'], identity, 'Registration immutable C11 origin')
    return identity, {'mode': mode, 'semantic_action': action, 'failed_event_id': parent['id'] if parent['kind'] == 'improvement_failed' else None}, previous, semantic, original, declared, registration


def _inputs(request, artifacts, events, semantic, registration):
    by_id = {event['id']: event for event in events}; values, observed = {}, {}
    for role, event_id in _packet(artifacts)['observations'].items():
        if role in BASE_ROLES:
            prefix = _scope(request['study_id']); source = prefix + role
        else:
            c.require(registration is not None, 'Execution supplied before accepted registration')
            prefix = runner.scope(semantic['hash']); source = prefix + (role[10:] if role.startswith('execution:') else role)
        event = _observation(by_id, event_id, source); raw = _blob(artifacts, event)
        c.require(len(raw) <= _input_limit(role), 'Navigation input bound')
        if request['phase'] == PREPARATION:
            c.require(event['seq'] > by_id[request['evidence_origin']['event_id']]['seq'], 'Preparation input predates C11 origin')
        elif role in BASE_ROLES:
            c.require(event['seq'] < semantic['seq'] and _hash(raw) == registration['input_hashes'][role], 'Registered base input differs or is late')
        else: c.require(event['seq'] > semantic['seq'], 'Attempt/evaluation predates registration')
        values[role], observed[role] = raw, event
    latest = {}
    for event in events:
        if event['kind'] == 'observation' and event['body']['source'].startswith(_scope(request['study_id'])):
            role = event['body']['source'][len(_scope(request['study_id'])):]
            c.require(role in BASE_ROLES, 'Unknown scoped preparation role')
            latest[role] = event['id']
    c.require(latest == {role: observed[role]['id'] for role in BASE_ROLES}, 'Omitted latest preparation input')
    if registration is not None:
        scoped = {event['id'] for event in events if event['kind'] == 'observation' and event['body']['source'].startswith(runner.scope(semantic['hash']))}
        c.require(scoped == {event['id'] for role, event in observed.items() if role not in BASE_ROLES}, 'Omitted or repeated execution/evaluation evidence')
    c.require(sum(map(len, values.values())) <= c.MAX_BUNDLE_BYTES, 'Study evidence exceeds 4 MiB')
    return values, observed


def _metadata(artifacts, manifest):
    request = _json(artifacts['request']); _request(request); _equal(_json(artifacts['contract']), CONTRACT, 'Navigation contract')
    events = _json(artifacts['ledger_prefix'])
    origin, ancestry, previous, semantic, _, _, registration = _lineage(request, artifacts, events)
    inputs, observed = _inputs(request, artifacts, events, semantic, registration)
    c.require(BASE_ROLES <= set(inputs), 'Missing navigation base input')
    if request['phase'] == PREPARATION: c.keys(inputs, BASE_ROLES, 'preparation inputs')
    else: c.require({'execution:claim', 'execution:seal', 'evaluation', 'evaluation_execution'} <= set(inputs), 'Missing retained execution/evaluation/outcome')
    expected = {'request', 'contract', 'packet', 'ledger_prefix', 'evidence_origin', 'queue_parent'}
    captures = list(observed.values())
    if ancestry['mode'] == 'failed_attempt_continuation':
        expected |= {'failure_request', 'failure_claim', 'semantic_parent'}
        parent = _find({event['id']: event for event in events}, request['queue_parent'])
        captures.append(_observation({event['id']: event for event in events}, 'improvement:' + parent['body']['run_key'] + ':input:decision-input:request'))
    for event in captures:
        expected |= {'observation:' + event['id'], 'blob:' + event['body']['content_hash']}
        _equal(_json(artifacts['observation:' + event['id']]), event, 'Retained navigation observation'); _blob(artifacts, event)
    for role, raw in _current_sources().items():
        expected.add(role); _equal(artifacts[role], raw, 'Navigation frozen source')
    c.keys(artifacts, expected, 'retained navigation artifacts')
    relevant = {}
    for role, raw in inputs.items():
        if role in BASE_ROLES:
            try: relevant[role] = _hash(c.canonical(c.decode(raw, _input_limit(role)))) if role != 'candidate' else _hash(raw)
            except (ValueError, UnicodeError, RecursionError): relevant[role] = _hash(raw)
    relevant.update({role: digest for role, digest in manifest.items() if role.startswith('code:')})
    relevant_hash = _hash(_canonical(relevant))
    if previous is not None: c.require(previous['relevant_input_hash'] != relevant_hash, 'Unchanged failed navigation preparation cannot repeat')
    return {'schema_version': 1, 'contract_id': CONTRACT_ID, 'phase': request['phase'], 'stage': PHASES[request['phase']],
        'study_id': request['study_id'], 'status': 'prepared', 'origin': deepcopy(request['origin']), 'evidence_origin': origin,
        'queue_parent': deepcopy(request['queue_parent']), 'evidence_checkpoint': deepcopy(request['evidence_checkpoint']), 'ancestry': ancestry,
        'assessment_identity': {'schema_version': 1, 'hash': _hash(_canonical(manifest))},
        'input_hashes': {role: value for role, value in manifest.items() if not role.startswith('code:')},
        'source_hashes': {name: manifest['code:epiphysics.' + name[:-3]] for name in SOURCE_NAMES},
        'relevant_input_hash': relevant_hash, 'scope': c.CONTRACT['scope']}


def prepare_navigation(path):
    artifacts, started = {}, time.monotonic()
    try:
        _put(artifacts, 'request', _read(path, 65536)); request = _json(artifacts['request']); _request(request)
        for role, locator in request['paths'].items(): _put(artifacts, role, _read(locator, _role_limit(role)))
        packet = _packet(artifacts)
        for role, raw in _current_sources().items(): _put(artifacts, role, raw)
        ledger = store.Ledger.open_readonly(request['ledger_path'])
        try:
            ledger.db.execute('BEGIN'); end = request['evidence_checkpoint']['seq']
            bounds = ledger.db.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(body AS BLOB))),0),COALESCE(MAX(length(CAST(body AS BLOB))),0) FROM events WHERE seq<=?', (end,)).fetchone()
            c.require(0 < bounds[0] <= MAX_PREFIX_EVENTS and bounds[1] <= MAX_PREFIX_BYTES and bounds[2] <= 1048576, 'Navigation prefix bound')
            events = [{**dict(row), 'body': _json(row['body'])} for row in ledger.db.execute('SELECT * FROM events WHERE seq<=? ORDER BY seq', (end,))]
            _put(artifacts, 'ledger_prefix', _canonical(events)); by_id = _prefix(events)
            for role in ('evidence_origin', 'queue_parent'): _put(artifacts, role, _canonical(_find(by_id, request[role])))
            parent = _find(by_id, request['queue_parent']); ids = list(packet['observations'].values())
            if parent['kind'] == 'improvement_failed': ids.append('improvement:' + parent['body']['run_key'] + ':input:decision-input:request')
            for event_id in ids:
                event = _observation(by_id, event_id); _put(artifacts, 'observation:' + event_id, _canonical(event))
                raw = _read(ledger.root / 'blobs' / event['body']['content_hash'], 1048576)
                c.require(len(raw) == event['body']['size'] and _hash(raw) == event['body']['content_hash'], 'Corrupt navigation blob')
                _put(artifacts, 'blob:' + event['body']['content_hash'], raw)
            if parent['kind'] == 'improvement_failed':
                claims = [event for event in events if event['kind'] == 'improvement_started' and event['body']['run_key'] == parent['body']['run_key']]
                c.require(len(claims) == 1, 'Unique failure claim required'); claim = claims[0]
                semantic = [event for event in events if event['kind'] in TRANSITIONS and event['seq'] < claim['seq']][-1]
                observation = by_id['improvement:' + parent['body']['run_key'] + ':input:decision-input:request']
                _put(artifacts, 'failure_request', _blob(artifacts, observation)); _put(artifacts, 'failure_claim', _canonical(claim)); _put(artifacts, 'semantic_parent', _canonical(semantic))
        finally: ledger.close()
        manifest = {role: _hash(raw) for role, raw in artifacts.items()}
        report = _metadata(artifacts, manifest)
        c.require(time.monotonic() - started <= MAX_SECONDS, 'Navigation preparation time bound')
        return {'artifacts': artifacts, 'manifest': manifest, 'report': report}
    except (ValueError, OSError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError, sqlite3.Error) as error:
        raise PreparationError(str(error), artifacts) from error


def check_prepared_navigation(prepared):
    c.keys(prepared, {'artifacts', 'manifest', 'report'}, 'prepared navigation')
    c.keys(prepared['manifest'], prepared['artifacts'], 'prepared navigation manifest')
    for role, raw in prepared['artifacts'].items():
        cap = _role_limit(role)
        c.require(cap is not None and type(raw) is bytes and len(raw) <= cap and _hash(raw) == prepared['manifest'][role], 'Prepared navigation artifact differs')
    c.require(sum(map(len, prepared['artifacts'].values())) <= MAX_BUNDLE_BYTES, 'Prepared navigation bundle bound')
    _equal(prepared['report'], _metadata(prepared['artifacts'], prepared['manifest']), 'Prepared navigation metadata')


def validate_lineage(prepared, actual_events, after_step):
    check_prepared_navigation(prepared); request = _json(prepared['artifacts']['request'])
    _equal(after_step, request['origin']['step_id'], 'Authoritative navigation step')
    _equal([event for event in actual_events if event['seq'] <= request['evidence_checkpoint']['seq']], _json(prepared['artifacts']['ledger_prefix']), 'Authoritative navigation checkpoint')
    parent = [event for event in actual_events if event['kind'] in TRANSITIONS][-1]
    _equal({'event_id': parent['id'], 'event_hash': parent['hash']}, request['queue_parent'], 'Stale navigation queue parent')
    prefixes = [_scope(request['study_id'])]
    if request['phase'] == CHECK:
        _, _, _, semantic, _, _, _ = _lineage(request, prepared['artifacts'], _json(prepared['artifacts']['ledger_prefix']))
        prefixes.append(runner.scope(semantic['hash']))
    c.require(not any(event['seq'] > request['evidence_checkpoint']['seq'] and event['kind'] == 'observation'
        and any(event['body']['source'].startswith(prefix) for prefix in prefixes) for event in actual_events), 'Later scoped navigation evidence omitted')


def validate_completion(prepared, report, recorded_at, checked_at):
    """Called last under Ledger.append's lock, after source/result revalidation.

    Negative timing findings remain recordable; an apparently within-budget result
    must still satisfy the original deadline at the final acceptance boundary.
    """
    if report['phase'] != CHECK or report['checks'].get('time_bounds') is not True:
        return
    artifacts = prepared['artifacts']; packet = _packet(artifacts)
    def value(role):
        event = _json(artifacts['observation:' + packet['observations'][role]])
        return c.decode(_blob(artifacts, event), c.MAX_RECEIPT_BYTES)
    claim, evaluated = value('execution:claim'), value('evaluation')
    start, end = store.instant(claim['started_at']), store.instant(evaluated['ended_at'])
    recorded, checked = store.instant(recorded_at), store.instant(checked_at)
    elapsed = time.monotonic() - claim['started_monotonic']
    if not (end <= recorded <= checked and 0 <= elapsed <= c.TOTAL_SECONDS
            and 0 <= elapsed - evaluated['whole_run_seconds'] <= c.CLOSE_SECONDS
            and (checked - start).total_seconds() <= c.TOTAL_SECONDS
            and (checked - end).total_seconds() <= c.CLOSE_SECONDS):
        raise ClosureDeadlineExceeded('Navigation final completion exceeded the original study/closing deadline; retained scores are evidence, not an accepted within-budget result')


def _preparation(inputs, observed, original, declared, study_id):
    public_map = c.validate_map(c.decode(inputs['map'], c.MAX_MAP_BYTES))
    _equal(original['dataset_identity'], {key: public_map[key] for key in ('sourceCommit', 'catalogHash', 'payloadHash')}, 'Accepted C11 map identity')
    map_hash = _hash(inputs['map']); _equal(declared.get('blob:' + map_hash), map_hash, 'Accepted C11 raw map bytes')
    cohort = c.validate_cohort(c.decode(inputs['tasks'], c.MAX_TASK_BYTES), public_map)
    key = evaluation.validate_key(c.decode(inputs['key'], c.MAX_KEY_BYTES), cohort, public_map)
    c.require(observed['candidate']['seq'] < observed['tasks']['seq'] and observed['candidate']['seq'] < observed['key']['seq'], 'Candidate was not frozen before tasks/key capture')
    c.require(inputs['candidate'] and len(inputs['candidate']) <= c.MAX_SOURCE_BYTES, 'Candidate source bound')
    compile(inputs['candidate'].decode('utf-8'), 'registered-candidate.py', 'exec', dont_inherit=True)
    runtime = runner.runtime_identity(c.decode(inputs['runtime'], c.MAX_RECEIPT_BYTES))
    authorship = c.decode(inputs['authorship'], c.MAX_RECEIPT_BYTES)
    c.keys(authorship, {'schema_version', 'design_author', 'candidate_author', 'task_author', 'key_author', 'reviewer', 'input_hashes', 'checks', 'exposure'}, 'authorship review')
    c.require(type(authorship['schema_version']) is int and authorship['schema_version'] == 1, 'Authorship version')
    for role in ('design_author', 'candidate_author', 'task_author', 'key_author', 'reviewer'): c.text(authorship[role], 200, 'author attribution')
    c.require(authorship['candidate_author'] not in {authorship['task_author'], authorship['key_author'], authorship['reviewer']}
        and authorship['reviewer'] not in {authorship['task_author'], authorship['key_author']}
        and authorship['design_author'] not in {authorship['task_author'], authorship['key_author']}, 'Independent authorship roles are unavailable')
    c.text(authorship['exposure'], 4096, 'exposure disclosure')
    _equal(authorship['input_hashes'], {role: _hash(raw) for role, raw in inputs.items() if role != 'authorship'}, 'Authorship reviewed inputs')
    c.keys(authorship['checks'], AUTHOR_CHECKS, 'authorship checks')
    c.require(all(value is True for value in authorship['checks'].values()), 'Missing independent authorship/review prerequisite')
    registration = {'schema_version': 1, 'study_id': study_id, 'input_hashes': {role: _hash(raw) for role, raw in inputs.items()},
        'cohort_hash': _hash(c.canonical(cohort)), 'key_hash': _hash(c.canonical(key)), 'map_payload_hash': public_map['payloadHash'],
        'source_hashes': runner.sources(), 'runtime': runtime, 'case_ids': [case['case_id'] for case in cohort['cases']],
        'public_inputs': {role: observed[role]['id'] for role in runner.PUBLIC_ROLES}}
    registration['digest'] = _hash(c.canonical(registration))
    return registration


def _evaluation_outcome(raw, report_raw, received, registration, identity, ledger_path, claim, observed):
    outcome = c.decode(raw, c.MAX_RECEIPT_BYTES)
    c.keys(outcome, {'schema_version', 'registration', 'runtime', 'command', 'source_hashes', 'key_sha256',
        'started_at', 'ended_at', 'started_monotonic', 'ended_monotonic', 'elapsed_seconds', 'returncode',
        'termination', 'error', 'cleanup_errors', 'report_sha256', 'stdout', 'stderr'}, 'external evaluator outcome')
    c.require(type(outcome['schema_version']) is int and outcome['schema_version'] == 1
        and outcome['registration'] == identity and outcome['runtime'] == registration['runtime']
        and outcome['source_hashes'] == registration['source_hashes']
        and outcome['key_sha256'] == registration['input_hashes']['key']
        and outcome['report_sha256'] == _hash(report_raw), 'Evaluator outcome identity differs')
    command = outcome['command']
    engine = str(Path(__file__).resolve().parents[1])
    run_directory = str(Path(ledger_path).resolve() / 'navigation-runs' / identity['event_hash'])
    c.require(type(command) is list and len(command) == 11 and command[:9] ==
        [registration['runtime']['path'], '-I', '-B', '-c', c.EVALUATOR_BOOTSTRAP, engine,
            'epiphysics.navigation_evaluation', '--run-directory', run_directory]
        and command[9] == '--key' and type(command[10]) is str and Path(command[10]).is_absolute(), 'Fixed evaluator command differs')
    c.text(command[10], 4096, 'private key path attribution')
    for field in ('started_monotonic', 'ended_monotonic', 'elapsed_seconds'):
        c.require(type(outcome[field]) in (int, float) and math.isfinite(outcome[field]) and outcome[field] >= 0, 'Evaluator monotonic duration')
    monotonic = outcome['ended_monotonic'] - outcome['started_monotonic']
    wall = (store.instant(outcome['ended_at']) - store.instant(outcome['started_at'])).total_seconds()
    c.require(0 <= monotonic and abs(monotonic - outcome['elapsed_seconds']) <= .01
        and outcome['elapsed_seconds'] <= wall + .1
        and store.instant(outcome['started_at']) <= store.instant(received['started_at'])
        <= store.instant(received['ended_at']) <= store.instant(outcome['ended_at'])
        <= store.instant(observed['evaluation']['recorded_at']) <= store.instant(observed['evaluation_execution']['recorded_at'])
        and observed['evaluation']['seq'] < observed['evaluation_execution']['seq'], 'Evaluator outcome/capture chronology')
    c.require(outcome['termination'] in {'exited', 'deadline', 'output_limit', 'supervisor_error', 'unreaped'}
        and (outcome['returncode'] is None or type(outcome['returncode']) is int), 'Evaluator process outcome')
    if outcome['error'] is not None: c.text(outcome['error'], 1024, 'evaluator supervisor error')
    c.require(type(outcome['cleanup_errors']) is list and len(outcome['cleanup_errors']) <= 12, 'Evaluator cleanup error bound')
    for error in outcome['cleanup_errors']: c.text(error, 1024, 'evaluator cleanup error')
    for name in ('stdout', 'stderr'):
        meta = outcome[name]; c.keys(meta, {'bytes', 'sha256', 'observed_bytes', 'complete'}, 'evaluator stream')
        c.sha(meta['sha256'])
        c.require(type(meta['bytes']) is int and type(meta['observed_bytes']) is int and type(meta['complete']) is bool
            and 0 <= meta['bytes'] <= c.MAX_REPORT_BYTES + 1 and meta['observed_bytes'] >= meta['bytes']
            and (not meta['complete'] or meta['observed_bytes'] == meta['bytes']), 'Evaluator stream bounds/completeness')
    emitted = c.canonical(received) + b'\n'
    successful = (outcome['termination'] == 'exited' and outcome['returncode'] == 0 and outcome['error'] is None
        and not outcome['cleanup_errors'] and all(outcome[name]['complete'] for name in ('stdout', 'stderr'))
        and outcome['stdout']['bytes'] == len(emitted) and outcome['stdout']['sha256'] == _hash(emitted))
    capture = store.instant(observed['evaluation_execution']['recorded_at'])
    within_budget = (monotonic <= c.EVALUATE_SECONDS and wall <= c.EVALUATE_SECONDS
        and (capture - store.instant(claim['started_at'])).total_seconds() <= c.TOTAL_SECONDS
        and (capture - store.instant(received['ended_at'])).total_seconds() <= c.CLOSE_SECONDS)
    return successful, within_budget


def _check(inputs, observed, registration, semantic, ledger_path):
    public_map = c.validate_map(c.decode(inputs['map'], c.MAX_MAP_BYTES)); cohort = c.validate_cohort(c.decode(inputs['tasks'], c.MAX_TASK_BYTES), public_map)
    key = evaluation.validate_key(c.decode(inputs['key'], c.MAX_KEY_BYTES), cohort, public_map)
    identity = {'event_id': semantic['id'], 'event_hash': semantic['hash']}
    execution = {role[10:]: raw for role, raw in inputs.items() if role.startswith('execution:')}
    observations = {role[10:]: event for role, event in observed.items() if role.startswith('execution:')}
    attempts, claim, seal = runner.validate_execution(public_map, cohort, registration, identity, execution, observations)
    received = c.decode(inputs['evaluation'], c.MAX_REPORT_BYTES)
    c.keys(received, {'schema_version', 'status', 'started_at', 'ended_at', 'elapsed_seconds', 'registration', 'seal_sha256',
        'key_raw_sha256', 'key_hash', 'source_hashes', 'whole_run_seconds', 'total_budget_ok', 'scores', 'error'}, 'retained evaluation')
    c.require(received['schema_version'] == 1 and received['status'] in {'scored', 'failed'}
        and received['source_hashes'] == registration['source_hashes'], 'Evaluation source/version')
    duration = (store.instant(received['ended_at']) - store.instant(received['started_at'])).total_seconds()
    c.require(type(received['elapsed_seconds']) in (int, float) and math.isfinite(received['elapsed_seconds'])
        and 0 <= received['elapsed_seconds'] <= duration + .1
        and store.instant(seal['ended_at']) <= store.instant(received['started_at'])
        <= store.instant(received['ended_at']) <= store.instant(observed['evaluation']['recorded_at']), 'Evaluation/capture chronology')
    process_ok, process_budget = _evaluation_outcome(inputs['evaluation_execution'], inputs['evaluation'], received,
        registration, identity, ledger_path, claim, observed)
    checks = {'prospective_execution': True, 'retained_evaluation': received['status'] == 'scored' and process_ok,
        'score_agreement': False, 'time_bounds': False, 'all_six_cases_correct': False}
    scored = None
    if received['status'] == 'scored' and process_ok:
        c.require(received['registration'] == identity and received['seal_sha256'] == _hash(execution['seal'])
            and received['key_raw_sha256'] == _hash(inputs['key']) and received['key_hash'] == _hash(c.canonical(key)), 'Evaluated frozen inputs differ')
        scored = evaluation.evaluate(public_map, cohort, key, attempts)
        checks['score_agreement'] = received['scores'] == scored
        wall = (store.instant(received['ended_at']) - store.instant(claim['started_at'])).total_seconds()
        captured = store.instant(observed['evaluation']['recorded_at'])
        capture_total = (captured - store.instant(claim['started_at'])).total_seconds()
        closing = (captured - store.instant(received['ended_at'])).total_seconds()
        whole = received['whole_run_seconds']
        checks['time_bounds'] = (type(whole) in (int, float) and math.isfinite(whole) and 0 <= whole <= wall + .1
            and wall <= c.TOTAL_SECONDS and whole <= c.TOTAL_SECONDS and received['total_budget_ok'] is True
            and 0 <= capture_total <= c.TOTAL_SECONDS and 0 <= closing <= c.CLOSE_SECONDS
            and process_budget and duration <= c.EVALUATE_SECONDS and all(attempt['state'] == 'not_started' or
                attempt['receipt']['elapsed_seconds'] <= c.ATTEMPT_SECONDS + 3 for attempt in attempts.values()))
        checks['all_six_cases_correct'] = scored['passed']
    elif received['status'] == 'failed':
        c.text(received['error'], 1024, 'failed evaluator reason')
    action = ('repair_navigation_execution_contract' if not checks['retained_evaluation'] or not checks['score_agreement'] or not checks['time_bounds']
        else scored['next_action'])
    return checks, scored, action


def assess_prepared_navigation(prepared):
    started = time.monotonic(); check_prepared_navigation(prepared)
    report = deepcopy(prepared['report']); artifacts = prepared['artifacts']; request = _json(artifacts['request']); events = _json(artifacts['ledger_prefix'])
    _, _, _, semantic, original, declared, registration = _lineage(request, artifacts, events)
    inputs, observed = _inputs(request, artifacts, events, semantic, registration)
    errors, scores = {}, None
    if request['phase'] == PREPARATION:
        try:
            registration = _preparation(inputs, observed, original, declared, request['study_id'])
            checks = {'prospective_protocol': True}; action = 'run_textual_evidence_navigation_baseline'
        except (ValueError, TypeError, KeyError, IndexError, UnicodeError, SyntaxError, RecursionError, OSError) as error:
            registration = None; checks = {'prospective_protocol': False}; errors['prospective_protocol'] = str(error)[:512]
            action = 'repair_evidence_navigation_protocol'
        readiness = 'registered' if all(checks.values()) else 'unavailable_prerequisite'
    else:
        try: checks, scores, action = _check(inputs, observed, registration, semantic, request['ledger_path'])
        except (ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError) as error:
            checks = {'retained_execution_valid': False}; errors['retained_execution_valid'] = str(error)[:512]
            action = 'repair_navigation_execution_contract'
        readiness = 'textual_baseline_checked' if all(checks.values()) else 'repair_required'
    report.update(status='checked', checks=checks, errors=errors, registration=registration, scores=scores, readiness=readiness,
        unknowns={'human_comprehension': None, 'browser_usability': None, 'graph_vs_text_benefit': None, 'population_accuracy': None, 'external_witness': None},
        next_step={'action': action, 'reason': 'Fixed prospective or retained textual-navigation contract outcome',
            'scale_change_allowed': False, 'live_effects_allowed': False, 'metric_status': 'Descriptive six-case baseline only; no human or comparative benefit claim'})
    raw = _canonical(report)
    c.require(len(raw) <= c.MAX_REPORT_BYTES and sum(map(len, artifacts.values())) + len(raw) <= MAX_BUNDLE_BYTES, 'Navigation report bound')
    elapsed = time.monotonic() - started; c.require(elapsed <= MAX_SECONDS, 'Navigation retained check time bound')
    return {'report': report, 'artifacts': {**artifacts, 'assessment_report': raw},
        'actual_resources': {'retained_navigation_elapsed_seconds': elapsed, 'external_program_invocations': 0}}


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, '__module__', None) == __name__ and hasattr(function, '__code__'))
_CONSTANTS = tuple((name, deepcopy(globals()[name])) for name in ('PREPARATION', 'CHECK', 'PHASES', 'CONTRACT_ID', 'PHASE_NEXT_ACTIONS',
    'SEMANTIC_ACTIONS', 'NEXT_ACTIONS', 'SOURCE_NAMES', 'MAX_SECONDS', 'MAX_PREFIX_EVENTS', 'MAX_PREFIX_BYTES', 'MAX_BUNDLE_BYTES',
    'MAX_SOURCE_BYTES', 'BASE_ROLES', 'AUTHOR_CHECKS', 'CONTRACT', 'TRANSITIONS'))
