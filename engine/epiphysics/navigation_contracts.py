"""Public wire contract for a fixed textual reader; no cohort, key or execution."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = ()
CONTRACT_ID = 'textual-evidence-navigation-v1'
EVALUATOR_BOOTSTRAP = "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module(sys.argv.pop(1),run_name='__main__',alter_sys=True)"
MAX_MAP_BYTES = 262144
MAX_TASK_BYTES = MAX_KEY_BYTES = MAX_SOURCE_BYTES = MAX_RECEIPT_BYTES = MAX_REPORT_BYTES = 65536
MAX_INPUT_BYTES = 327680
MAX_STREAM_BYTES = 16384
MAX_BUNDLE_BYTES = 4194304
TOTAL_SECONDS, ATTEMPT_SECONDS, PREPARE_SECONDS, EVALUATE_SECONDS, CLOSE_SECONDS = 900, 120, 30, 60, 90
FAMILIES = ('source', 'qualification', 'proposal')
OPERATORS = {'cite_sources': 'source', 'cite_documents': 'source', 'outgoing_qualification': 'qualification',
    'inline_scope': 'qualification', 'motivated_followups': 'proposal'}
OPERATOR_COUNTS = {'cite_sources': 1, 'cite_documents': 1, 'outgoing_qualification': 1, 'inline_scope': 1, 'motivated_followups': 2}
REQUESTED_FIELDS = ['references', 'relationships', 'claim_labels', 'target_labels', 'interpretations']
INTERPRETATIONS = ('bibliographic_reference_only', 'document_metadata_only', 'qualification_not_refutation',
    'explicit_scope_not_generalization', 'proposed_not_completed', 'insufficient_support')
KINDS = ('claim', 'source', 'document', 'representation', 'transformation', 'experiment')
STATUSES = ('definition', 'hypothesis', 'reported_result', 'implementation_finding', 'contested')
BASES = ('reported', 'inferred', 'observed')
EDGE_TYPES = ('cites', 'challenges', 'motivates', 'compares', 'transforms', 'depends_on', 'implements')
DENOMINATORS = {'strict_completion': 6, 'references': 6, 'direction': 5, 'claim_labels': 6,
    'source_interpretation': 2, 'qualification_interpretation': 2, 'proposal_interpretation': 2}
CONTRACT = {'schema_version': 1, 'contract_id': CONTRACT_ID, 'families': list(FAMILIES), 'operators': OPERATORS,
    'operator_counts': OPERATOR_COUNTS, 'requested_fields': REQUESTED_FIELDS, 'interpretations': list(INTERPRETATIONS),
    'denominators': DENOMINATORS, 'cases': 6, 'attempts_per_case': 1, 'arms': 1,
    'limits': {'map_bytes': MAX_MAP_BYTES, 'tasks_bytes': MAX_TASK_BYTES, 'key_bytes': MAX_KEY_BYTES,
        'source_receipt_report_bytes': MAX_SOURCE_BYTES, 'candidate_input_bytes': MAX_INPUT_BYTES,
        'stream_bytes': MAX_STREAM_BYTES, 'bundle_bytes': MAX_BUNDLE_BYTES, 'total_seconds': TOTAL_SECONDS,
        'attempt_seconds': ATTEMPT_SECONDS, 'preparation_seconds': PREPARE_SECONDS,
        'evaluation_seconds': EVALUATE_SECONDS, 'closing_seconds': CLOSE_SECONDS},
    'scope': 'One deterministic textual baseline on six selected tasks; no model calls, browser, human-use or comparative benefit claim',
    'retry': 'No second attempt on any case; malformed and failed first attempts remain evidence'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw, cap):
    require(type(raw) is bytes and len(raw) <= cap, 'JSON byte bound')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('Nonfinite JSON number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), 'Unexpected ' + label + ' fields')


def text(value, cap, label):
    require(type(value) is str and bool(value.strip()) and len(value.encode('utf-8')) <= cap
        and not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value), 'Invalid ' + label)


def identifier(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value), 'Invalid identifier')


def sha(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{64}', value), 'Invalid SHA-256')


def validate_case(case):
    keys(case, {'case_id', 'family', 'prompt', 'anchor_title', 'operator', 'requested_fields'}, 'public case')
    identifier(case['case_id']); text(case['prompt'], 4096, 'prompt'); text(case['anchor_title'], 512, 'anchor title')
    require(type(case['operator']) is str and case['operator'] in OPERATORS
        and case['family'] == OPERATORS[case['operator']], 'Public operator/family mismatch')
    require(case['requested_fields'] == REQUESTED_FIELDS, 'Public response field selection differs')
    return case


def validate_cohort(value, public_map):
    keys(value, {'schema_version', 'contract_id', 'map_payload_hash', 'cases'}, 'public cohort')
    require(type(value['schema_version']) is int and value['schema_version'] == 1
        and value['contract_id'] == CONTRACT_ID and value['map_payload_hash'] == public_map['payloadHash'], 'Cohort identity differs')
    require(type(value['cases']) is list and len(value['cases']) == 6, 'Exactly six cases required')
    seen, counts = set(), dict.fromkeys(OPERATORS, 0)
    titles = [node['title'] for node in public_map['nodes'] if node['kind'] == 'claim']
    for case in value['cases']:
        validate_case(case)
        require(case['case_id'] not in seen and titles.count(case['anchor_title']) == 1, 'Duplicate case or ambiguous claim anchor')
        seen.add(case['case_id']); counts[case['operator']] += 1
    require(counts == OPERATOR_COUNTS, 'Two source, two qualification and two proposal slots required')
    require([case['family'] for case in value['cases']] == list(FAMILIES) * 2, 'Frozen family-interleaved order required')
    return value


def validate_map(value):
    keys(value, {'schemaVersion', 'sourceCommit', 'catalogHash', 'nodes', 'edges', 'limits', 'payloadHash'}, 'public map')
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1, 'Map version')
    require(type(value['sourceCommit']) is str and re.fullmatch('[a-f0-9]{40}', value['sourceCommit']), 'Map commit label')
    sha(value['catalogHash']); sha(value['payloadHash'])
    require(digest(canonical({key: item for key, item in value.items() if key != 'payloadHash'})) == value['payloadHash'], 'Map payload hash differs')
    require(type(value['nodes']) is list and 1 <= len(value['nodes']) <= 128 and type(value['edges']) is list
        and len(value['edges']) <= 512, 'Map node/edge bounds')
    require(type(value['limits']) is list and 1 <= len(value['limits']) <= 8, 'Map limitations')
    for limit in value['limits']: text(limit, 4096, 'map limitation')
    by_id = {}
    for node in value['nodes']:
        require(type(node) is dict and node.get('kind') in KINDS, 'Map node kind')
        common = {'id', 'kind', 'title'}
        extra = ({'statement', 'status', 'basis'} if node['kind'] == 'claim' else
            {'href', 'date', 'dateType', 'reviewedOn', 'bibliographicOnly', 'limitations'} if node['kind'] == 'source' else
            {'href', 'contentHash', 'commit'} if node['kind'] == 'document' else {'status'})
        keys(node, common | extra, 'public node'); identifier(node['id']); text(node['title'], 512, 'node title')
        require(node['id'] not in by_id, 'Duplicate node ID'); by_id[node['id']] = node
        if node['kind'] == 'claim':
            text(node['statement'], 4096, 'claim statement')
            require(node['status'] in STATUSES and node['basis'] in BASES, 'Claim labels')
        elif node['kind'] == 'source':
            text(node['href'], 2048, 'source URL'); href = urlsplit(node['href'])
            require(href.scheme == 'https' and href.hostname and not href.username and not href.password
                and not re.search(r'[\s\\]', node['href']), 'Unsafe source URL')
            require(node['bibliographicOnly'] is True and type(node['limitations']) is list and len(node['limitations']) <= 8, 'Bibliographic source fields')
            for name in ('date', 'dateType', 'reviewedOn'):
                if node[name] is not None: text(node[name], 100, 'bibliographic date attribution')
            for limitation in node['limitations']: text(limitation, 4096, 'source limitation')
        elif node['kind'] == 'document':
            require(type(node['href']) is str and re.fullmatch(r'/(research|theory|experiments)/[A-Za-z0-9_/-]+', node['href'])
                and '..' not in node['href'], 'Unsafe public document route')
            sha(node['contentHash']); require(node['commit'] == value['sourceCommit'], 'Document commit differs')
        else:
            require(node['status'] == 'proposed', 'Proposal label')
    seen = set()
    for edge in value['edges']:
        keys(edge, {'source', 'target', 'type'}, 'directed edge')
        identifier(edge['source']); identifier(edge['target'])
        require(edge['source'] in by_id and edge['target'] in by_id and edge['type'] in EDGE_TYPES, 'Dangling or invalid edge')
        token = (edge['source'], edge['target'], edge['type'])
        require(token not in seen, 'Duplicate edge'); seen.add(token)
    require(len(canonical(value)) <= MAX_MAP_BYTES, 'Map byte bound')
    return value


def pointer_value(node, pointer):
    require(type(pointer) is str and re.fullmatch(r'/[A-Za-z][A-Za-z0-9]*(?:/(?:0|[1-9][0-9]*))?', pointer), 'Unsupported node field pointer')
    parts = pointer[1:].split('/')
    require(parts[0] in node, 'Missing referenced field')
    value = node[parts[0]]
    if len(parts) == 2:
        require(type(value) is list and int(parts[1]) < len(value), 'Missing referenced list element')
        value = value[int(parts[1])]
    require(value is None or type(value) in (str, bool, int), 'Reference must identify a scalar field')
    return value


def validate_response(value, case, public_map):
    keys(value, {'schema_version', 'case_id', 'map_payload_hash', 'answer_status', 'references', 'relationships',
        'claim_labels', 'target_labels', 'interpretations', 'unresolved_reason'}, 'candidate response')
    require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['case_id'] == case['case_id']
        and value['map_payload_hash'] == public_map['payloadHash'], 'Response identity differs')
    require(value['answer_status'] in {'answered', 'unresolved'}, 'Answer status')
    for field in ('references', 'relationships', 'target_labels', 'interpretations'):
        require(type(value[field]) is list and len(value[field]) <= 32, 'Response list bound')
        require(len({canonical(item) for item in value[field]}) == len(value[field]), 'Duplicate response item')
    for ref in value['references']:
        keys(ref, {'node_id', 'pointer', 'quote'}, 'reference'); identifier(ref['node_id'])
        text(ref['pointer'], 128, 'field pointer')
        if ref['quote'] is not None: text(ref['quote'], 4096, 'quotation')
    for edge in value['relationships']:
        keys(edge, {'source', 'target', 'type'}, 'answer relationship')
        identifier(edge['source']); identifier(edge['target']); text(edge['type'], 100, 'relationship type')
    labels = value['claim_labels']
    if labels is not None:
        keys(labels, {'node_id', 'status', 'basis'}, 'claim labels'); identifier(labels['node_id'])
        for field in ('status', 'basis'):
            if labels[field] is not None: text(labels[field], 100, 'claim label')
    for labels in value['target_labels']:
        keys(labels, {'node_id', 'kind', 'status', 'basis'}, 'target labels'); identifier(labels['node_id'])
        for field in ('kind', 'status', 'basis'):
            if labels[field] is not None: text(labels[field], 100, 'target label')
    require(all(type(code) is str and code in INTERPRETATIONS for code in value['interpretations']), 'Interpretation vocabulary')
    if value['answer_status'] == 'answered':
        require(value['unresolved_reason'] is None, 'Answered response has unresolved reason')
    else:
        text(value['unresolved_reason'], 512, 'unresolved reason')
    require(len(canonical(value)) <= MAX_STREAM_BYTES, 'Response byte bound')
    return value


def candidate_input(public_map, case):
    validate_map(public_map); validate_case(case)
    raw = canonical({'schema_version': 1, 'contract_id': CONTRACT_ID, 'map': public_map, 'case': case})
    require(len(raw) <= MAX_INPUT_BYTES, 'Candidate input byte bound')
    return raw


def validate_candidate_input(value):
    keys(value, {'schema_version', 'contract_id', 'map', 'case'}, 'candidate input')
    require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['contract_id'] == CONTRACT_ID, 'Candidate contract')
    validate_map(value['map']); validate_case(value['case'])
    return value


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, '__module__', None) == __name__ and hasattr(function, '__code__'))
_CONSTANTS = tuple((name, deepcopy(value)) for name, value in tuple(globals().items())
    if name.isupper() and not name.startswith('_') and not name.startswith('IMPLEMENTATION_'))
