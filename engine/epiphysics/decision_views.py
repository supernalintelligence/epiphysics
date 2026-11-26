"""Two fixed, bounded public decision views with exact source provenance.

Preparation filters dated public event records. Builders and decoders receive
only the resulting header/tape bytes; no policy, resolver, outcomes or stores.
Filesystem reads are confined to source capture and runtime_sources().
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

IMPLEMENTATION_CODE = sys._getframe().f_code
_SOURCE_PATH = Path(__file__)
with _SOURCE_PATH.open('rb') as _source_stream:
    IMPLEMENTATION_SOURCE = _source_stream.read(100001)
if len(IMPLEMENTATION_SOURCE) > 100000:
    raise ValueError('Decision view implementation exceeds source bound')
IMPLEMENTATION_DEPENDENCIES = ()

CONTRACT_ID = 'control-exchange-release-hold-v1'
CODEC_ID = 'decision-view-json-v1'
TIME_ORIGIN = '2020-01-01T00:00:00Z'
MAX_PUBLIC_EVENTS = 15  # The sixteen-domain-event contract reserves one private outcome.
MAX_INPUT_BYTES = 32768
VIEW_BUDGETS = (2048, 32768)  # Fixed bounded arm and declared lossless control only.
RECIPE_IDS = ('flat-recency-v1', 'task-proximity-v1')
POLICY_KINDS = ('grant', 'revoke', 'delivery_claim', 'verification', 'dispute_open', 'dispute_close', 'release_committed')
EVENT_FIELDS = ('event_id', 'kind', 'issuer', 'subject', 'object', 'obligation_id', 'effective_at', 'observed_at', 'reference', 'artifact_sha256', 'verdict', 'authentication')
TASK_FIELDS = ('obligation_id', 'requester', 'delegate', 'provider', 'artifact_id', 'artifact_sha256', 'amount', 'unit', 'deadline')
HEADER_FIELDS = ('schema_version', 'contract_id', 'time_origin', 'cutoff', 'decision_at', 'task')
VIEW_FIELDS = ('v', 'arm', 'input_hash', 'source_hash', 'source_bytes', 'time_origin', 'cutoff_s', 'decision_s', 'task', 'coverage', 'records')
_BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class VerifiedPolicyInput:
    """Independent values for a trusted pipeline, not a same-process sandbox."""
    header: dict
    events: tuple[dict, ...]
    complete: bool
    eligible_policy_count: int
    retained_policy_count: int
    input_hash: str
    source_hash: str


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    """Exact UTF-8 JSON codec; encoded views never receive a trailing newline."""
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError('Invalid decision JSON value') from error


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'Duplicate JSON object key')
        result[key] = value
    return result


def _integer(text):
    _require(len(text) <= 20, 'Oversized JSON integer')
    return int(text)


def _noninteger(_):
    raise ValueError('Noninteger JSON number')


def _parse(raw):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_int=_integer, parse_float=_noninteger, parse_constant=_noninteger)
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError('Invalid bounded decision JSON') from error


def _keys(value, fields, label):
    _require(type(value) is dict and len(value) == len(fields) and set(value) == set(fields), 'Invalid ' + label + ' fields')


def _identifier(value):
    _require(type(value) is str and 1 <= len(value) <= 32, 'Invalid bounded identifier')
    try:
        encoded = value.encode('utf-8')
    except UnicodeError as error:
        raise ValueError('Invalid UTF-8 identifier') from error
    _require(len(encoded) <= 32 and not any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value), 'Invalid bounded identifier')


def _hash(value):
    _require(type(value) is str and len(value) == 64 and re.fullmatch(r'[0-9a-f]{64}', value) is not None, 'Invalid digest')


def seconds(value):
    """Parse the exact whole-second UTC spelling and bounded owned time range."""
    _require(type(value) is str and len(value) == 20 and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value) is not None, 'Invalid exact UTC timestamp')
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    except (ValueError, OverflowError) as error:
        raise ValueError('Invalid exact UTC timestamp') from error
    result = int((parsed - _BASE).total_seconds())
    _require(-86400 <= result <= 86400, 'Timestamp outside owned pilot bound')
    return result


def validate_task(task):
    """Validate public task shape; this does not establish authority."""
    _keys(task, TASK_FIELDS, 'task')
    names = [task[field] for field in TASK_FIELDS[:5]]
    for value in names:
        _identifier(value)
    _require(len(set(names)) == 5, 'Task roles/objects must be distinct')
    _hash(task['artifact_sha256'])
    _require(type(task['amount']) is int and 1 <= task['amount'] <= 1000000000, 'Invalid amount')
    _require(task['unit'] == 'simulation_credit', 'Invalid unit')
    seconds(task['deadline'])


def validate_event(event):
    """Validate only public record structure; no role/state/policy reduction."""
    _keys(event, EVENT_FIELDS, 'event')
    for field in ('event_id', 'issuer', 'subject', 'object', 'obligation_id'):
        _identifier(event[field])
    kind = event['kind']
    _require(type(kind) is str and kind in POLICY_KINDS + ('note',), 'Unknown event kind')
    _require(type(event['authentication']) is str and event['authentication'] in ('verified', 'unknown', 'invalid'), 'Invalid authentication field')
    seconds(event['effective_at'])
    seconds(event['observed_at'])
    if kind in ('delivery_claim', 'verification', 'release_committed'):
        _hash(event['artifact_sha256'])
    else:
        _require(event['artifact_sha256'] is None, 'Unexpected artifact digest')
    _require(event['verdict'] in ('pass', 'fail') if kind == 'verification' else event['verdict'] is None, 'Invalid verdict')
    reference = event['reference']
    if kind == 'release_committed':
        _hash(reference)
    elif kind == 'dispute_close':
        _identifier(reference)
    elif kind in ('revoke', 'note'):
        if reference is not None:
            _identifier(reference)
    else:
        _require(reference is None, 'Unexpected reference')


def _header(task, cutoff, decision_at):
    validate_task(task)
    _require(seconds(cutoff) == seconds(decision_at), 'Cutoff and decision time differ')
    return {'schema_version': 1, 'contract_id': CONTRACT_ID, 'time_origin': TIME_ORIGIN,
            'cutoff': cutoff, 'decision_at': decision_at, 'task': deepcopy(task)}


def _check_header(header):
    _keys(header, HEADER_FIELDS, 'public header')
    _require(type(header['schema_version']) is int and header['schema_version'] == 1 and header['contract_id'] == CONTRACT_ID
             and header['time_origin'] == TIME_ORIGIN, 'Invalid public header identity')
    _header(header['task'], header['cutoff'], header['decision_at'])


def prepare_decision_input(events, task, cutoff, decision_at):
    """Prepare only dated public records; never accepts a whole fixture/trace."""
    header = _header(task, cutoff, decision_at)
    _require(type(events) is list and len(events) <= MAX_PUBLIC_EVENTS, 'Invalid bounded public event list')
    identities = set()
    eligible = []
    for event in events:
        validate_event(event)
        _require(event['event_id'] not in identities, 'Duplicate source event identity')
        identities.add(event['event_id'])
        if seconds(event['observed_at']) <= seconds(cutoff) and event['obligation_id'] == task['obligation_id']:
            eligible.append(event)
    eligible.sort(key=lambda event: (seconds(event['observed_at']), event['event_id']))
    header_bytes = canonical(header)
    tape = b''.join(canonical(event) + b'\n' for event in eligible)
    _require(len(header_bytes) + 1 + len(tape) <= MAX_INPUT_BYTES, 'Public input exceeds byte bound')
    return {'header_bytes': header_bytes, 'event_tape_bytes': tape, 'input_hash': digest(header_bytes + b'\n' + tape)}


def _read_input(header_bytes, event_tape_bytes):
    _require(type(header_bytes) is bytes and type(event_tape_bytes) is bytes, 'Public input requires exact bytes')
    _require(len(header_bytes) + 1 + len(event_tape_bytes) <= MAX_INPUT_BYTES, 'Public input exceeds byte bound')
    header = _parse(header_bytes)
    _check_header(header)
    _require(canonical(header) == header_bytes, 'Header is not canonical JSON bytes')
    tape = event_tape_bytes
    _require(not tape or tape.endswith(b'\n'), 'Event tape must end in exactly one record LF')
    _require(tape.count(b'\n') <= MAX_PUBLIC_EVENTS, 'Event tape exceeds record bound')
    events, records, identities = [], [], set()
    start = 0
    for line in tape.split(b'\n')[:-1] if tape else ():
        event = _parse(line)
        validate_event(event)
        _require(canonical(event) == line, 'Event tape contains noncanonical record bytes')
        _require(event['event_id'] not in identities, 'Duplicate source event identity')
        _require(event['obligation_id'] == header['task']['obligation_id'] and seconds(event['observed_at']) <= seconds(header['cutoff']), 'Source record is outside task or cutoff')
        identities.add(event['event_id'])
        row = [event[field] for field in EVENT_FIELDS]
        row[6], row[7] = seconds(row[6]), seconds(row[7])
        records.append(row + [start, start + len(line)])
        events.append(event)
        start += len(line) + 1
    _require(events == sorted(events, key=lambda event: (seconds(event['observed_at']), event['event_id'])), 'Event tape order differs from canonical source order')
    return header, events, records


def _make_view(header, tape, all_records, selected, recipe):
    task = header['task']
    records = sorted(selected, key=lambda row: (row[7], row[0]))
    value = {'v': 1, 'arm': recipe, 'input_hash': digest(canonical(header) + b'\n' + tape),
             'source_hash': digest(tape), 'source_bytes': len(tape), 'time_origin': TIME_ORIGIN,
             'cutoff_s': seconds(header['cutoff']), 'decision_s': seconds(header['decision_at']),
             'task': [task[field] for field in TASK_FIELDS[:-1]] + [seconds(task['deadline'])],
             'coverage': [sum(row[1] in POLICY_KINDS for row in all_records), sum(row[1] in POLICY_KINDS for row in records)],
             'records': records}
    if recipe == RECIPE_IDS[1]:
        nodes = sorted({task[field] for field in TASK_FIELDS[:5]} | {row[index] for row in records for index in (2, 3, 4)})
        value['nodes'] = nodes
        value['edges'] = [[nodes.index(row[3]), nodes.index(row[4]), row[1], index] for index, row in enumerate(records)]
    return value


def _priority(header, records, recipe):
    if recipe == RECIPE_IDS[0]:
        return sorted(records, key=lambda row: (-row[7], row[0]))
    neighbors = {}
    for row in records:
        neighbors.setdefault(row[3], set()).add(row[4])
        neighbors.setdefault(row[4], set()).add(row[3])
    seeds = (header['task']['delegate'], header['task']['artifact_id'])
    distance = {node: 0 for node in seeds}
    queue = deque(seeds)
    while queue:
        node = queue.popleft()
        for other in sorted(neighbors.get(node, ())):
            if other not in distance:
                distance[other] = distance[node] + 1
                queue.append(other)
    return sorted(records, key=lambda row: (distance.get(row[3], 999) + distance.get(row[4], 999), -row[7], row[0]))


def _budget(value):
    _require(type(value) is int and value in VIEW_BUDGETS, 'Only fixed 2048-byte or 32768-byte lossless budget is supported')


def build_decision_view(header_bytes, event_tape_bytes, *, recipe, budget_bytes=2048):
    _require(type(recipe) is str and recipe in RECIPE_IDS, 'Unknown fixed view recipe')
    _budget(budget_bytes)
    header, _, records = _read_input(header_bytes, event_tape_bytes)
    selected = []
    _require(len(canonical(_make_view(header, event_tape_bytes, records, selected, recipe))) <= budget_bytes, 'Mandatory view metadata exceeds budget')
    for row in _priority(header, records, recipe):
        candidate = _make_view(header, event_tape_bytes, records, selected + [row], recipe)
        if len(canonical(candidate)) <= budget_bytes:
            selected.append(row)
    result = canonical(_make_view(header, event_tape_bytes, records, selected, recipe))
    _require(len(result) <= budget_bytes, 'Serialized view exceeds byte budget')
    if budget_bytes == VIEW_BUDGETS[1]:
        _require(len(selected) == len(records), 'Lossless control cannot omit a source record')
    return result


def validate_decode_view(header_bytes, event_tape_bytes, view_bytes, *, budget_bytes=2048):
    """Verify distinct source rows/metadata/index before releasing copied facts."""
    _budget(budget_bytes)
    _require(type(view_bytes) is bytes and len(view_bytes) <= budget_bytes, 'View exceeds byte bound or is not exact bytes')
    header, source_events, all_records = _read_input(header_bytes, event_tape_bytes)
    value = _parse(view_bytes)
    _require(type(value) is dict and type(value.get('arm')) is str and value['arm'] in RECIPE_IDS, 'Invalid view recipe')
    recipe = value['arm']
    _keys(value, VIEW_FIELDS + (('nodes', 'edges') if recipe == RECIPE_IDS[1] else ()), 'view')
    records = value['records']
    _require(type(records) is list and len(records) <= MAX_PUBLIC_EVENTS, 'Invalid bounded retained records')
    by_id = {row[0]: row for row in all_records}
    event_by_id = {event['event_id']: event for event in source_events}
    selected_ids, selected_spans = set(), set()
    for row in records:
        _require(type(row) is list and len(row) == 14, 'Invalid source record tuple')
        _identifier(row[0])
        _require(type(row[12]) is int and type(row[13]) is int, 'Invalid source span integers')
        span = (row[12], row[13])
        _require(row[0] not in selected_ids and span not in selected_spans, 'Duplicate retained source identity or span')
        _require(row[0] in by_id and canonical(row) == canonical(by_id[row[0]]), 'Retained record differs from exact source row')
        selected_ids.add(row[0])
        selected_spans.add(span)
    expected = _make_view(header, event_tape_bytes, all_records, records, recipe)
    _require(view_bytes == canonical(expected), 'View count/index/header/order/canonical bytes differ')
    eligible = {(row[0], row[12], row[13]) for row in all_records if row[1] in POLICY_KINDS}
    retained = {(row[0], row[12], row[13]) for row in records if row[1] in POLICY_KINDS}
    _require(retained <= eligible and value['coverage'] == [len(eligible), len(retained)], 'Distinct source coverage differs')
    if budget_bytes == VIEW_BUDGETS[1]:
        _require(selected_ids == set(by_id), 'Lossless control must preserve every source row')
    return VerifiedPolicyInput(header=deepcopy(header), events=tuple(deepcopy(event_by_id[row[0]]) for row in records),
        complete=retained == eligible, eligible_policy_count=len(eligible), retained_policy_count=len(retained),
        input_hash=expected['input_hash'], source_hash=expected['source_hash'])


def runtime_sources():
    """Bounded separate receipt helper; pure view APIs perform no filesystem I/O."""
    path, source, code = _SOURCE_IDENTITY
    _require(IMPLEMENTATION_SOURCE == source and IMPLEMENTATION_CODE is code, 'Decision view implementation reloaded')
    _require(not path.is_symlink() and path.is_file() and path.stat().st_size == len(source), 'Decision view source changed')
    with path.open('rb') as stream:
        _require(stream.read(len(source) + 1) == source, 'Decision view source changed')
    _require(compile(source, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize) == code, 'Decision view code differs from source')
    for name, function, expected in _FUNCTION_CODES:
        _require(globals().get(name) is function and function.__code__ is expected, 'Decision view callable changed: ' + name)
    for name, value in _CONSTANTS:
        _require(type(globals().get(name)) is type(value) and globals().get(name) == value, 'Decision view contract value changed: ' + name)
    _require(VerifiedPolicyInput is _VERIFIED_CLASS and VerifiedPolicyInput.__init__ is _VERIFIED_INIT, 'VerifiedPolicyInput class changed')
    return {__name__: source}


_SOURCE_IDENTITY = (_SOURCE_PATH, IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, '__module__', None) == __name__ and hasattr(function, '__code__'))
_CONSTANTS = tuple((name, globals()[name]) for name in ('CONTRACT_ID', 'CODEC_ID', 'TIME_ORIGIN', 'MAX_PUBLIC_EVENTS', 'MAX_INPUT_BYTES', 'VIEW_BUDGETS', 'RECIPE_IDS', 'POLICY_KINDS', 'EVENT_FIELDS', 'TASK_FIELDS', 'HEADER_FIELDS', 'VIEW_FIELDS', '_BASE'))
_VERIFIED_CLASS, _VERIFIED_INIT = VerifiedPolicyInput, VerifiedPolicyInput.__init__
