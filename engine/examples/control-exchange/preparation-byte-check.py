#!/usr/bin/env python3
"""Read-only C7 format/provenance check. No policy, resolver, retrieval or I/O effects.

Read two bounded owned JSON files; emit one bounded JSON report to stdout.
This is an executable codec specification, not the comparison implementation.
"""
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

MAX_FILE_BYTES = 131072
MAX_REPORT_BYTES = 262144
BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)
TIME_ORIGIN = '2020-01-01T00:00:00Z'
CONTRACT_ID = 'control-exchange-release-hold-v1'
ARMS = ('flat-recency-v1', 'task-proximity-v1')
POLICY_KINDS = ('grant', 'revoke', 'delivery_claim', 'verification', 'dispute_open', 'dispute_close', 'release_committed')
EVENT_FIELDS = ('event_id', 'kind', 'issuer', 'subject', 'object', 'obligation_id', 'effective_at', 'observed_at', 'reference', 'artifact_sha256', 'verdict', 'authentication')
TASK_FIELDS = ('obligation_id', 'requester', 'delegate', 'provider', 'artifact_id', 'artifact_sha256', 'amount', 'unit', 'deadline')
VIEW_FIELDS = ('v', 'arm', 'input_hash', 'source_hash', 'source_bytes', 'time_origin', 'cutoff_s', 'decision_s', 'task', 'coverage', 'records')
HEADER_FIELDS = ('schema_version', 'contract_id', 'time_origin', 'cutoff', 'decision_at', 'task')
RECORD_FIELDS = ('event_id', 'kind', 'issuer', 'subject', 'object', 'obligation_id', 'effective_seconds_from_time_origin', 'observed_seconds_from_time_origin', 'reference', 'artifact_sha256', 'verdict', 'authentication', 'source_start', 'source_end')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON object key')
        result[key] = value
    return result


def integer(text):
    require(len(text) <= 20, 'Oversized JSON integer')
    return int(text)


def no_float(_):
    raise ValueError('Noninteger JSON number')


def parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_pairs,
                      parse_int=integer, parse_float=no_float, parse_constant=no_float)


def read_bounded(path):
    require(not path.is_symlink() and path.is_file(), 'Input must be a regular nonsymlink file')
    require(path.stat().st_size <= MAX_FILE_BYTES, 'Input exceeds fixed file bound')
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    require(len(raw) <= MAX_FILE_BYTES, 'Input grew beyond file bound')
    return raw


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), 'Invalid ' + label + ' fields')


def identifier(value):
    require(type(value) is str and 1 <= len(value.encode('utf-8')) <= 32
            and not any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value), 'Invalid bounded identifier')


def digest_value(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None, 'Invalid digest')


def seconds(value):
    require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value) is not None, 'Invalid exact UTC timestamp')
    parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    result = int((parsed - BASE).total_seconds())
    require(-86400 <= result <= 86400, 'Timestamp outside owned pilot bound')
    return result


def check_task(task):
    keys(task, TASK_FIELDS, 'task')
    names = [task[key] for key in TASK_FIELDS[:5]]
    for value in names:
        identifier(value)
    require(len(set(names)) == 5, 'Task roles/objects must be distinct')
    digest_value(task['artifact_sha256'])
    require(type(task['amount']) is int and 1 <= task['amount'] <= 1000000000, 'Invalid amount')
    require(task['unit'] == 'simulation_credit', 'Invalid unit')
    seconds(task['deadline'])


def check_event(event):
    keys(event, EVENT_FIELDS, 'event')
    for field in ('event_id', 'issuer', 'subject', 'object', 'obligation_id'):
        identifier(event[field])
    kind = event['kind']
    require(kind in POLICY_KINDS + ('note',), 'Unknown event kind')
    require(event['authentication'] in ('verified', 'unknown', 'invalid'), 'Invalid authentication field')
    seconds(event['effective_at'])
    seconds(event['observed_at'])
    if kind in ('delivery_claim', 'verification', 'release_committed'):
        digest_value(event['artifact_sha256'])
    else:
        require(event['artifact_sha256'] is None, 'Unexpected artifact digest')
    require(event['verdict'] in ('pass', 'fail') if kind == 'verification' else event['verdict'] is None, 'Invalid verdict')
    reference = event['reference']
    if kind == 'release_committed':
        digest_value(reference)
    elif kind == 'dispute_close':
        identifier(reference)
    elif kind in ('revoke', 'note'):
        if reference is not None:
            identifier(reference)
    else:
        require(reference is None, 'Unexpected reference')


def public_input(trace):
    """Only explicit public fields influence the candidate header/tape."""
    check_task(trace['task'])
    cutoff, decision = seconds(trace['cutoff']), seconds(trace['decision_at'])
    require(cutoff == decision, 'Cutoff and decision time differ')
    events = trace['events']
    require(type(events) is list and len(events) + 1 <= 16, 'Domain-event bound exceeded')
    identities = set()
    for event in events:
        check_event(event)
        require(event['event_id'] not in identities, 'Duplicate source event identity')
        identities.add(event['event_id'])
    require(trace['later_outcome']['event_id'] not in identities, 'Outcome duplicates domain event identity')
    eligible = [event for event in events if seconds(event['observed_at']) <= cutoff and event['obligation_id'] == trace['task']['obligation_id']]
    eligible.sort(key=lambda event: (seconds(event['observed_at']), event['event_id']))
    tape = b''
    records = []
    for event in eligible:
        eraw = canonical(event)
        start = len(tape)
        tape += eraw + b'\n'
        row = [event[field] for field in EVENT_FIELDS]
        row[6], row[7] = seconds(row[6]), seconds(row[7])
        records.append(row + [start, start + len(eraw)])
    header = {'schema_version': 1, 'contract_id': CONTRACT_ID, 'time_origin': TIME_ORIGIN,
              'cutoff': trace['cutoff'], 'decision_at': trace['decision_at'], 'task': deepcopy(trace['task'])}
    require(len(canonical(header) + b'\n' + tape) <= 32768, 'Public input exceeds byte bound')
    return header, tape, records


def make_view(header, tape, all_records, selected, arm):
    task = header['task']
    records = sorted(selected, key=lambda row: (row[7], row[0]))
    value = {'v': 1, 'arm': arm, 'input_hash': sha(canonical(header) + b'\n' + tape),
             'source_hash': sha(tape), 'source_bytes': len(tape), 'time_origin': TIME_ORIGIN,
             'cutoff_s': seconds(header['cutoff']), 'decision_s': seconds(header['decision_at']),
             'task': [task[field] for field in TASK_FIELDS[:-1]] + [seconds(task['deadline'])],
             'coverage': [sum(row[1] in POLICY_KINDS for row in all_records), sum(row[1] in POLICY_KINDS for row in records)],
             'records': records}
    if arm == ARMS[1]:
        nodes = sorted({task[field] for field in TASK_FIELDS[:5]} | {row[index] for row in records for index in (2, 3, 4)})
        value['nodes'] = nodes
        value['edges'] = [[nodes.index(row[3]), nodes.index(row[4]), row[1], index] for index, row in enumerate(records)]
    return value


def serialize_view(header, tape, records, arm, *, lossless=False):
    require(arm in ARMS, 'Unknown fixed recipe')
    if arm == ARMS[0]:
        order = sorted(records, key=lambda row: (-row[7], row[0]))
    else:
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
        order = sorted(records, key=lambda row: (distance.get(row[3], 999) + distance.get(row[4], 999), -row[7], row[0]))
    limit = 32768 if lossless else 2048
    selected = []
    require(len(canonical(make_view(header, tape, records, selected, arm))) <= limit, 'Mandatory view metadata exceeds budget')
    for row in order:
        candidate = make_view(header, tape, records, selected + [row], arm)
        if lossless or len(canonical(candidate)) <= limit:
            selected.append(row)
    result = canonical(make_view(header, tape, records, selected, arm))
    require(len(result) <= limit, 'Serialized view exceeds budget')
    return result


def validate_view(header, tape, all_records, view_raw, *, limit=2048):
    require(len(view_raw) <= limit, 'View exceeds byte bound')
    value = parse(view_raw)
    require(type(value) is dict and value.get('arm') in ARMS, 'Invalid view recipe')
    arm = value['arm']
    keys(value, VIEW_FIELDS + (('nodes', 'edges') if arm == ARMS[1] else ()), 'view')
    records = value['records']
    require(type(records) is list and len(records) <= 16, 'Invalid bounded retained records')
    by_id = {row[0]: row for row in all_records}
    require(len(by_id) == len(all_records), 'Duplicate source event identity')
    selected_ids, selected_spans = set(), set()
    for row in records:
        require(type(row) is list and len(row) == 14, 'Invalid record tuple')
        identifier(row[0])
        require(type(row[12]) is int and type(row[13]) is int, 'Invalid span integers')
        span = (row[12], row[13])
        require(row[0] not in selected_ids and span not in selected_spans, 'Duplicate retained source identity or span')
        require(row[0] in by_id and canonical(row) == canonical(by_id[row[0]]), 'Retained row differs from exact source identity')
        expected_event = parse(tape[span[0]:span[1]])
        check_event(expected_event)
        require(expected_event['event_id'] == row[0], 'Source span/event identity mismatch')
        selected_ids.add(row[0])
        selected_spans.add(span)
    expected = make_view(header, tape, all_records, records, arm)
    require(view_raw == canonical(expected), 'View metadata/count/index/order/canonical bytes differ')
    eligible_set = {(row[0], row[12], row[13]) for row in all_records if row[1] in POLICY_KINDS}
    selected_set = {(row[0], row[12], row[13]) for row in records if row[1] in POLICY_KINDS}
    require(selected_set <= eligible_set, 'Retained relevant identity outside source')
    require(value['coverage'] == [len(eligible_set), len(selected_set)], 'Distinct source coverage count differs')
    return {'records': records, 'relevant_source_set_complete': selected_set == eligible_set}


def check_contract(contract):
    require(type(contract['schema_version']) is int and contract['schema_version'] == 1 and contract['contract_id'] == CONTRACT_ID
            and type(contract['preparation_revision']) is int and contract['preparation_revision'] == 1, 'Unexpected corrected contract')
    require(contract['codec']['id'] == 'decision-view-json-v1', 'Unknown codec')
    require(contract['input_schema']['event_fields'] == list(EVENT_FIELDS), 'Event field order differs')
    require(contract['input_schema']['task_fields'] == list(TASK_FIELDS), 'Task field order differs')
    require(contract['codec']['record_tuple'] == list(RECORD_FIELDS), 'Record tuple differs')
    require(contract['codec']['task_tuple'] == list(TASK_FIELDS[:-1]) + ['deadline_seconds_from_time_origin'], 'Task tuple differs')
    require(contract['codec']['header_fields'] == list(HEADER_FIELDS), 'Header fields differ')
    require(contract['codec']['view_flat_exact_keys'] == list(VIEW_FIELDS), 'Flat view shape differs')
    require(contract['codec']['view_relational_exact_keys'] == list(VIEW_FIELDS) + ['nodes', 'edges'], 'Relational view shape differs')
    require(contract['shared_policy']['policy_kinds'] == list(POLICY_KINDS), 'Census kinds differ')
    require(contract['view_contract']['budget_bytes'] == 2048, 'View ceiling differs')
    require((contract['view_contract']['flat_recipe']['id'], contract['view_contract']['relational_recipe']['id']) == ARMS, 'Recipe identities differ')


def main():
    here = Path(__file__).parent
    require(len(sys.argv) in (1, 3), 'Usage: preparation-byte-check.py [contract.json traces.json]')
    contract_path, trace_path = (Path(sys.argv[1]), Path(sys.argv[2])) if len(sys.argv) == 3 else (here / 'decision-contract.json', here / 'development-traces.json')
    source_raw = read_bounded(Path(__file__))
    contract_raw, trace_raw = read_bounded(contract_path), read_bounded(trace_path)
    contract, fixture = parse(contract_raw), parse(trace_raw)
    check_contract(contract)
    require(type(fixture['schema_version']) is int and fixture['schema_version'] == 1
            and type(fixture['preparation_revision']) is int and fixture['preparation_revision'] == 1
            and fixture['contract_id'] == CONTRACT_ID, 'Unexpected fixture contract')
    require(fixture['status'] == 'owned_exposed_development_fixtures' and fixture['final_cohort_generated'] is False, 'Not development-only input')
    traces = fixture['traces']
    require(type(traces) is list and len(traces) == 12 and fixture['trace_count'] == 12, 'Expected twelve development fixtures')
    require(len({trace['trace_id'] for trace in traces}) == 12, 'Duplicate development trace ID')
    rows, feasibility, inputs = [], [], {}
    golden = []
    for trace in traces:
        header, tape, records = public_input(trace)
        inputs[trace['trace_id']] = (header, tape, records)
        item = {'trace_id': trace['trace_id'], 'header_sha256': sha(canonical(header)), 'source_sha256': sha(tape),
                'input_sha256': sha(canonical(header) + b'\n' + tape), 'source_bytes': len(tape), 'input_bytes': len(canonical(header) + b'\n' + tape), 'arms': {}}
        declared_row = {'trace_id': trace['trace_id'], 'eligible_input_bytes': item['input_bytes'], 'arms': {}}
        lossless = []
        for arm in ARMS:
            bounded = serialize_view(header, tape, records, arm)
            decoded = validate_view(header, tape, records, bounded)
            complete = serialize_view(header, tape, records, arm, lossless=True)
            all_decoded = validate_view(header, tape, records, complete, limit=32768)
            require(canonical(all_decoded['records']) == canonical(records), 'Lossless source reconstruction differs')
            lossless.append(all_decoded['records'])
            value = parse(bounded)
            counts = {'bounded_bytes': len(bounded), 'retained_records': len(decoded['records']), 'eligible_records': len(records),
                      'retained_policy_kind_records': value['coverage'][1], 'eligible_policy_kind_records': value['coverage'][0], 'lossless_bytes': len(complete)}
            declared_row['arms'][arm] = counts
            item['arms'][arm] = {**counts, 'view_sha256': sha(bounded), 'lossless_view_sha256': sha(complete),
                                 'retained_source_event_ids': [row[0] for row in decoded['records']], 'relevant_source_set_complete': decoded['relevant_source_set_complete']}
            if trace['trace_id'] in ('dev-01', 'dev-11', 'dev-12'):
                golden.append({'trace_id': trace['trace_id'], 'arm': arm, 'bytes': len(bounded), 'sha256': sha(bounded), 'serialized_view': bounded.decode('utf-8')})
        require(canonical(lossless[0]) == canonical(lossless[1]), 'Lossless arms do not preserve identical facts')
        rows.append(item)
        feasibility.append(declared_row)
    require(canonical(feasibility) == canonical(contract['feasibility']['records']), 'Declared feasibility does not match corrected codec')
    for left, right in (('dev-01', 'dev-02'), ('dev-07', 'dev-08')):
        require(canonical(inputs[left][0]) + b'\n' + inputs[left][1] == canonical(inputs[right][0]) + b'\n' + inputs[right][1], 'Declared identical public input pair differs')
    # Format/provenance controls only; no authority or decision function exists here.
    header, tape, records = inputs['dev-03']
    changed = parse(serialize_view(header, tape, records, ARMS[0]))
    grant = next(row for row in changed['records'] if row[1] == 'grant')
    revoke_index = next(i for i, row in enumerate(changed['records']) if row[1] == 'revoke')
    changed['records'][revoke_index] = deepcopy(grant)
    try:
        validate_view(header, tape, records, canonical(changed))
    except ValueError as error:
        require('Duplicate retained source identity' in str(error), 'Duplicate substitution rejected for unexpected reason')
    else:
        raise ValueError('Duplicate grant replacing revoke was accepted')
    duplicate_trace = deepcopy(traces[0])
    duplicate_trace['events'].append(deepcopy(duplicate_trace['events'][0]))
    try:
        public_input(duplicate_trace)
    except ValueError as error:
        require('Duplicate source event identity' in str(error), 'Duplicate input rejected for unexpected reason')
    else:
        raise ValueError('Duplicate input event identity was accepted')
    report = {'schema_version': 1, 'status': 'format_and_provenance_checks_passed', 'codec_id': contract['codec']['id'],
              'checker_source_sha256': sha(source_raw), 'contract_file_sha256': sha(contract_raw), 'development_file_sha256': sha(trace_raw),
              'trace_count': len(traces), 'max_domain_events_including_private_outcome': max(len(trace['events']) + 1 for trace in traces),
              'declared_feasibility_reproduced': True, 'checks': ['unique input identities', 'distinct exact retained rows/spans', 'lossless fact parity',
              'identical visible input pairs', 'duplicate-grant-for-omitted-revoke rejected', 'duplicate source event rejected', 'bounded canonical views'],
              'rows': rows, 'golden_views': golden, 'policy_executed': False, 'resolver_executed': False, 'quality_scoring_executed': False,
              'final_cases_generated': False, 'network_calls': 0, 'input_writes': 0,
              'scope': 'Owned development format/retention check only; no decision-performance or elapsed-cost measurement.'}
    output = canonical(report)
    require(len(output) <= MAX_REPORT_BYTES, 'Report exceeds fixed output bound')
    sys.stdout.write(output.decode('utf-8') + '\n')


if __name__ == '__main__':
    main()
