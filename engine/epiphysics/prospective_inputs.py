"""Bounded raw evidence -> typed facts. No collection, oracle or outcome logic.

normalize_inputs(manifest_bytes, bodies) returns (packet_bytes_or_None,
diagnostics_bytes). See docs/planning/prospective-inputs.md for raw schema v1.
All receipt/clock assertions are caller claims, never independent witnessing.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from .store import canonical, digest, instant
from .prospective_views import INPUT_LIMIT

DECLARATION_SHA256 = 'ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65'
BODY_LIMIT = 1048576
HEADER_LIMIT = 16384
CONTRACT_LIMIT = 65536
SOURCE_LIMIT = 8192
DIAGNOSTICS_LIMIT = 65536
SOURCE_URL = 'https://api.github.com/repos/modelcontextprotocol/python-sdk/releases?per_page=5'
REQUEST_HEADERS = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                   'Accept-Encoding': 'identity', 'User-Agent': 'Epiphysics-Prospective-Integrity-Pilot-v1'}
COMMON_RECEIPT = {'id', 'kind', 'content_sha256', 'retained_byte_length', 'observed_byte_length', 'complete',
                  'observed_at', 'validated_at', 'retained_at', 'time_basis', 'clock'}
COMMON_QUESTION = {'schema_version', 'family', 'question_id', 'subject_id', 'knowledge_cutoff_utc',
                   'forecast_deadline_utc', 'outcome_cutoff_utc', 'resolution_rule_id', 'evidence'}
ACCEPTANCE_FIELDS = {'acceptance_event_id', 'promisor_role_id', 'beneficiary_role_id',
                     'authorized_submission_channel_id', 'quality_rule_hash', 'quality_parameters',
                     'source_sha256', 'source_byte_length', 'source_path', 'source_blob_id',
                     'git_object_format', 'source_commit_id'}


class InputUnavailable(ValueError):
    """Runtime/resource inability; not evidence that source schema is invalid."""


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, keys, label):
    _require(type(value) is dict and set(value) == set(keys), 'invalid_' + label + '_fields')


def _id(value):
    _require(type(value) is str and 0 < len(value) <= 200 and value.strip() == value, 'invalid_identifier')


def _hash(value):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'invalid_sha256')


def _time(value):
    _require(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)', value),
             'invalid_local_time')
    return instant(value)


def _time_text(value):
    return _time(value).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _bytes(value, limit):
    try:
        result = canonical(value).encode('utf-8')
    except ValueError as exc:
        if 'integer string conversion' in str(exc):
            raise InputUnavailable('runtime_integer_digits_unavailable') from exc
        raise ValueError('unrepresentable_json') from exc
    except RecursionError as exc:
        raise InputUnavailable('runtime_nesting_unavailable') from exc
    except (UnicodeError, OverflowError) as exc:
        raise ValueError('unrepresentable_json') from exc
    _require(len(result) <= limit, 'byte_limit_exceeded')
    return result


def _load(raw, limit):
    _require(type(raw) is bytes and len(raw) <= limit, 'byte_limit_exceeded')
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def integer(text):
        try:
            return int(text)
        except ValueError as exc:
            raise InputUnavailable('runtime_integer_digits_unavailable') from exc
    def decimal(text):
        value = float(text)
        if not math.isfinite(value):
            raise InputUnavailable('runtime_finite_number_range_unavailable')
        try:
            equal = Decimal(text) == Decimal(str(value))
        except InvalidOperation as exc:
            raise InputUnavailable('runtime_decimal_exponent_unavailable') from exc
        if not equal:
            raise InputUnavailable('runtime_number_precision_unavailable')
        return value
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_int=integer, parse_float=decimal,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_number')))
        _bytes(value, max(limit * 6, 1))  # Validate unicode/nonfinite values, never truncate.
        return value
    except json.JSONDecodeError as exc:
        raise ValueError('invalid_json') from exc
    except RecursionError as exc:
        raise InputUnavailable('runtime_nesting_unavailable') from exc
    except (UnicodeError, OverflowError) as exc:
        raise ValueError('invalid_utf8_json') from exc


def _receipt(receipt, body, limit):
    """Validate supplied bytes and internal consistency of local clock claims."""
    _hash(receipt['content_sha256'])
    for key in ('retained_byte_length', 'observed_byte_length'):
        _require(type(receipt[key]) is int and receipt[key] >= 0, 'invalid_byte_count')
    _require(type(receipt['complete']) is bool, 'invalid_complete_type')
    _require(type(body) is bytes, 'missing_body')
    _require(len(body) <= limit, 'body_overflow')
    _require(len(body) == receipt['retained_byte_length'], 'retained_length_mismatch')
    _require(digest(body) == receipt['content_sha256'], 'body_hash_mismatch')
    _require(receipt['complete'] and receipt['observed_byte_length'] == len(body), 'incomplete_body')
    _require(receipt['time_basis'] == 'local_clock', 'unsupported_time_basis')
    observed, validated, retained = (_time(receipt[k]) for k in ('observed_at', 'validated_at', 'retained_at'))
    _require(observed <= validated <= retained, 'receipt_time_order')
    clock = receipt['clock']
    _keys(clock, {'start_utc', 'start_ns', 'observed_ns', 'validated_ns', 'retained_ns', 'start_epoch', 'end_epoch'}, 'clock')
    _id(clock['start_epoch']); _id(clock['end_epoch'])
    _require(clock['start_epoch'] == clock['end_epoch'], 'clock_epoch_changed')
    start = _time(clock['start_utc'])
    counts = [clock[k] for k in ('start_ns', 'observed_ns', 'validated_ns', 'retained_ns')]
    _require(all(type(n) is int and n >= 0 for n in counts) and counts == sorted(counts), 'invalid_monotonic_clock')
    _require(start <= observed, 'receipt_time_order')
    for date, count in zip((observed, validated, retained), counts[1:]):
        elapsed = date - start
        ns = (elapsed.days * 86400 * 1000000 + elapsed.seconds * 1000000 + elapsed.microseconds) * 1000
        _require(abs(ns - (count - counts[0])) <= 1000000000, 'clock_unverified')
    return observed, validated, retained


def _publisher(field, value):
    if value is None:
        return {'raw': None, 'precision': None, 'parse_status': 'unparsed'}
    if field == 'tag_name':
        return {'raw': value, 'precision': 'string' if type(value) is str else None,
                'parse_status': 'valid' if type(value) is str else 'invalid'}
    pattern = r'([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]+))?(Z|[+-][0-9]{2}:[0-9]{2})'
    match = re.fullmatch(pattern, value) if type(value) is str else None
    precision, status = None, 'invalid'
    if match:
        fraction = match[2]
        precision = 'fractional_digits:' + str(len(fraction)) if fraction else 'second'
        try:
            # Validate calendar/offset; no parsed timestamp enters the packet.
            zone = match[3]
            if zone != 'Z':
                _require(int(zone[1:3]) <= 23 and int(zone[4:6]) <= 59, 'invalid_publisher_offset')
            datetime.fromisoformat(match[1] + zone.replace('Z', '+00:00'))
            status = 'valid'
        except ValueError:
            pass
    return {'raw': value, 'precision': precision, 'parse_status': status}


def _link_next(pairs):
    """Diagnostic only: conservatively flag unsupported Link grammar."""
    values = [v for k, v in pairs if k.lower() == 'link']
    uncertain = False
    for value in values:
        for part in re.split(r',(?=\s*<)', value):
            match = re.fullmatch(r'\s*<[^<>\r\n]+>((?:\s*;\s*[A-Za-z0-9_-]+\s*=\s*(?:"[^"\r\n]*"|[^\s;,"]+))*)\s*', part)
            if not match:
                uncertain = True
                continue
            for parameter in re.finditer(r';\s*([A-Za-z0-9_-]+)\s*=\s*(?:"([^"\r\n]*)"|([^\s;,"]+))', match[1]):
                parameter_value = parameter[2] if parameter[2] is not None else parameter[3]
                if parameter[1].lower() == 'rel' and 'next' in parameter_value.split():
                    return 'present'
    return 'unparseable' if uncertain else 'absent'


def _sample(receipt, body, headers, slot):
    observed, validated, retained = _receipt(receipt, body, BODY_LIMIT)
    http = receipt['http']
    _keys(http, {'request_url', 'request_method', 'request_headers', 'status_code', 'completion',
                 'headers_sha256', 'headers_complete', 'headers_observed_byte_length'}, 'http')
    _require(http['request_url'] == SOURCE_URL and http['request_method'] == 'GET'
             and http['request_headers'] == REQUEST_HEADERS, 'request_contract_mismatch')
    _require(type(http['status_code']) is int and http['status_code'] == 200, 'http_status')
    _require(http['completion'] == 'completed', 'request_not_completed')
    _require(type(http['headers_complete']) is bool and http['headers_complete'], 'incomplete_headers')
    _hash(http['headers_sha256'])
    _require(type(headers) is bytes, 'missing_headers')
    _require(len(headers) <= HEADER_LIMIT, 'header_overflow')
    _require(type(http['headers_observed_byte_length']) is int
             and http['headers_observed_byte_length'] == len(headers), 'header_length_mismatch')
    _require(digest(headers) == http['headers_sha256'], 'header_hash_mismatch')
    pairs = _load(headers, HEADER_LIMIT)
    _require(type(pairs) is list and all(type(p) is list and len(p) == 2
             and all(type(x) is str for x in p) for p in pairs), 'invalid_header_pairs')
    _require(all(re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", k)
                 and not any(c in v for c in ('\r', '\n', '\0')) for k, v in pairs), 'invalid_header_field')
    encodings = [v.strip().lower() for k, v in pairs if k.lower() == 'content-encoding']
    _require(not encodings or encodings == ['identity'], 'nonidentity_encoding')
    nominal = _time(slot['nominal_at'])
    start = _time(receipt['clock']['start_utc'])
    _require(timedelta(0) <= start - nominal <= timedelta(seconds=60), 'outside_start_window')
    _require(observed - start <= timedelta(seconds=10)
             and receipt['clock']['observed_ns'] - receipt['clock']['start_ns'] <= 10000000000, 'request_timeout')
    _require(retained - nominal <= timedelta(seconds=120), 'late_slot_receipt')
    records = _load(body, BODY_LIMIT)
    _require(type(records) is list and len(records) <= 5, 'release_record_limit')
    seen = set()
    for record in records:
        _require(type(record) is dict and {'id', 'draft', 'prerelease'} <= set(record), 'missing_release_fields')
        _require(type(record['id']) is int and record['id'] > 0, 'invalid_release_id')
        _require(type(record['draft']) is bool and type(record['prerelease']) is bool, 'invalid_release_boolean')
        _require(record['id'] not in seen, 'duplicate_release_id')
        seen.add(record['id'])
    return records, _link_next(pairs)


def normalize_inputs(manifest_bytes, bodies):
    """Return (canonical packet or None, canonical diagnostics); never mutate inputs.

    Malformed envelope/declaration structure raises ValueError. Evidence failures
    are returned as bounded diagnostics. None means no admissible shared packet.
    """
    manifest = _load(manifest_bytes, INPUT_LIMIT)
    _keys(manifest, {'raw_input_schema_version', 'declaration_sha256', 'question_observation_id', 'observations'}, 'manifest')
    _require(type(manifest['raw_input_schema_version']) is int and manifest['raw_input_schema_version'] == 1, 'raw_schema_version')
    _require(manifest['declaration_sha256'] == DECLARATION_SHA256, 'declaration_pin_mismatch')
    _id(manifest['question_observation_id'])
    receipts = manifest['observations']
    _require(type(receipts) is list and 1 <= len(receipts) <= 18, 'observation_limit')
    _require(type(bodies) is dict and all(type(k) is str and type(v) is bytes for k, v in bodies.items()), 'invalid_bodies')
    by_id, allowed_bodies = {}, set()
    for receipt in receipts:
        _require(type(receipt) is dict, 'invalid_receipt')
        kind = receipt.get('kind')
        _require(kind in ('question_contract', 'release_sample', 'acceptance', 'source_blob'), 'invalid_observation_kind')
        _keys(receipt, COMMON_RECEIPT | ({'slot_id', 'http'} if kind == 'release_sample' else set()), 'receipt')
        _id(receipt['id']); _require(receipt['id'] not in by_id, 'duplicate_observation_id')
        by_id[receipt['id']] = receipt; allowed_bodies.add(receipt['id'])
        if kind == 'release_sample':
            allowed_bodies.add(receipt['id'] + ':headers')
    _require(len(allowed_bodies) == len(receipts) + sum(r['kind'] == 'release_sample' for r in receipts), 'body_key_collision')
    _require(set(bodies) <= allowed_bodies, 'undeclared_body')
    diagnostics = {'raw_input_schema_version': 1, 'status': 'refused', 'timing_assurance': 'caller_claims_only',
                   'independent_collection_verified': False, 'observations': [], 'missing_slots': [], 'reasons': []}
    def result(packet=None):
        diagnostics['observations'].sort(key=lambda x: x['id'])
        return packet, _bytes(diagnostics, DIAGNOSTICS_LIMIT)
    question_id = manifest['question_observation_id']
    qreceipt = by_id.get(question_id)
    if qreceipt is None or qreceipt['kind'] != 'question_contract':
        diagnostics['reasons'].append('missing_question_contract'); return result()
    try:
        _receipt(qreceipt, bodies.get(question_id), CONTRACT_LIMIT)
        question = _load(bodies[question_id], CONTRACT_LIMIT)
        _keys(question, COMMON_QUESTION, 'question')
        _require(type(question['schema_version']) is int and question['schema_version'] == 1, 'question_schema_version')
        _require(question['family'] in ('software_component', 'local_delivery_obligation'), 'invalid_family')
        for key in ('question_id', 'subject_id', 'resolution_rule_id'):
            _id(question[key])
        cutoff, forecast, outcome = (_time(question[k]) for k in ('knowledge_cutoff_utc', 'forecast_deadline_utc', 'outcome_cutoff_utc'))
        _require(_time(qreceipt['retained_at']) <= cutoff <= forecast <= outcome, 'question_deadline_order')
    except ValueError as error:
        diagnostics['reasons'].append('question_contract:' + str(error)); return result()
    packet = {'schema_version': 1, 'family': question['family'], 'entities': [], 'observations': [], 'assertions': []}
    entities = {}
    def entity(identifier, kind):
        _id(identifier)
        _require(identifier not in entities or entities[identifier] == kind, 'entity_identity_collision')
        entities[identifier] = kind
        return identifier
    def add_observation(receipt):
        packet['observations'].append({k: (_time_text(receipt[k]) if k in ('observed_at', 'retained_at') else receipt[k])
            for k in ('id', 'kind', 'content_sha256', 'observed_at', 'retained_at', 'time_basis')})
    def fact(subject, predicate, value_type, value, refs):
        refs = sorted(refs)
        packet['assertions'].append({'id': 'assertion:' + digest(_bytes([subject, predicate, refs], INPUT_LIMIT)),
            'subject': subject, 'predicate': predicate, 'object': {'type': value_type, 'value': value},
            'observation_ids': refs, 'known_at': _time_text(max((by_id[r]['retained_at'] for r in refs), key=_time)),
            'supersedes': None})
    qid = entity(question['question_id'], 'question'); subject = entity(question['subject_id'], question['family'])
    add_observation(qreceipt)
    for key, kind, value in [('subject', 'entity', subject),
            ('knowledge_cutoff', 'string', _time_text(question['knowledge_cutoff_utc'])),
            ('forecast_deadline', 'string', _time_text(question['forecast_deadline_utc'])),
            ('outcome_cutoff', 'string', _time_text(question['outcome_cutoff_utc'])),
            ('resolution_rule', 'string', question['resolution_rule_id'])]:
        fact(qid, 'question.' + key, kind, value, [question_id])
    diagnostics['observations'].append({'id': question_id, 'status': 'admitted', 'reason': None})
    evidence = question['evidence']
    if question['family'] == 'software_component':
        _keys(evidence, {'source_id', 'request_url', 'opening_slot_id', 'slots'}, 'release_declaration')
        _id(evidence['source_id']); _id(evidence['opening_slot_id'])
        _require(evidence['request_url'] == SOURCE_URL, 'source_url_mismatch')
        _require(type(evidence['slots']) is list and 1 <= len(evidence['slots']) <= 16, 'slot_limit')
        slots = {}
        for slot in evidence['slots']:
            _keys(slot, {'id', 'nominal_at'}, 'slot'); _id(slot['id']); _time(slot['nominal_at'])
            _require(slot['id'] not in slots, 'duplicate_slot_id'); slots[slot['id']] = slot
        _require(evidence['opening_slot_id'] in slots, 'undeclared_opening')
        opening_time = _time(slots[evidence['opening_slot_id']]['nominal_at'])
        _require(opening_time <= cutoff, 'opening_after_cutoff')
        _require(len({_time(s['nominal_at']) for s in slots.values()}) == len(slots), 'duplicate_slot_time')
        supplied_slots, opening = set(), None
        for receipt in sorted(receipts, key=lambda r: r['id']):
            if receipt['id'] == question_id:
                continue
            _require(receipt['kind'] == 'release_sample', 'outside_family_observation')
            slot_id = receipt['slot_id']; _id(slot_id)
            _require(slot_id in slots and slot_id not in supplied_slots, 'unknown_or_duplicate_slot')
            supplied_slots.add(slot_id)
            try:
                records, link_next = _sample(receipt, bodies.get(receipt['id']), bodies.get(receipt['id'] + ':headers'), slots[slot_id])
                _require(_time(slots[slot_id]['nominal_at']) <= opening_time, 'after_opening_slot')
                _require(_time(receipt['retained_at']) <= cutoff, 'after_cutoff')
            except ValueError as error:
                diagnostics['observations'].append({'id': receipt['id'],
                    'status': 'unavailable' if isinstance(error, InputUnavailable) else 'excluded', 'reason': str(error)})
                if isinstance(error, InputUnavailable):
                    diagnostics['reasons'].append('input_unavailable:' + str(error))
                continue
            add_observation(receipt)
            diagnostics['observations'].append({'id': receipt['id'], 'status': 'admitted', 'reason': None,
                'release_record_count': len(records), 'link_next': link_next,
                'excluded_field_count': sum(len(set(r) - {'id', 'draft', 'prerelease', 'tag_name', 'created_at', 'published_at'}) for r in records)})
            if slot_id == evidence['opening_slot_id']:
                opening = receipt['id']
            for record in records:
                release = entity('release:' + digest(_bytes([subject, record['id']], INPUT_LIMIT)), 'release')
                for key, kind, value in [('component', 'entity', subject), ('id', 'integer', record['id']),
                        ('draft', 'boolean', record['draft']), ('prerelease', 'boolean', record['prerelease'])]:
                    fact(release, 'release.' + key, kind, value, [receipt['id']])
                for key in ('tag_name', 'created_at', 'published_at'):
                    if key in record:
                        fact(release, 'release.' + key, 'json', _publisher(key, record[key]), [receipt['id']])
        diagnostics['missing_slots'] = sorted(s for s in slots if s not in supplied_slots
            and _time(slots[s]['nominal_at']) <= opening_time)
        # Missing prior receipts could hide eligible history: require explicit
        # invalid/missing evidence records for every scheduled prior slot.
        if diagnostics['missing_slots']:
            diagnostics['reasons'].append('missing_prior_slot_receipts')
        if opening is None:
            diagnostics['reasons'].append('missing_valid_opening')
        if diagnostics['reasons']:
            return result()
        fact(qid, 'question.opening_observation', 'string', opening, [question_id])
    else:
        binding_fields = ACCEPTANCE_FIELDS | {'acceptance_observation_id', 'acceptance_sha256', 'source_observation_id'}
        _keys(evidence, binding_fields, 'obligation_declaration')
        aid, sid = evidence['acceptance_observation_id'], evidence['source_observation_id']
        _id(aid); _id(sid)
        _require(len({aid, sid, question_id}) == 3, 'duplicate_evidence_identity')
        _require(set(by_id) <= {question_id, aid, sid}, 'outside_obligation_observation')
        for identifier, kind, limit in [(aid, 'acceptance', CONTRACT_LIMIT), (sid, 'source_blob', SOURCE_LIMIT)]:
            receipt = by_id.get(identifier)
            try:
                _require(receipt is not None and receipt['kind'] == kind, 'missing_' + kind)
                _receipt(receipt, bodies.get(identifier), limit)
                _require(_time(receipt['retained_at']) <= cutoff, 'after_cutoff')
            except ValueError as error:
                diagnostics['observations'].append({'id': identifier, 'status': 'excluded', 'reason': str(error)})
                diagnostics['reasons'].append('required_evidence_unavailable')
        if diagnostics['reasons']:
            return result()
        try:
            _hash(evidence['acceptance_sha256']); _hash(evidence['source_sha256']); _hash(evidence['quality_rule_hash'])
            _require(digest(bodies[aid]) == evidence['acceptance_sha256'], 'acceptance_binding_mismatch')
            acceptance = _load(bodies[aid], CONTRACT_LIMIT)
            _keys(acceptance, ACCEPTANCE_FIELDS | {'schema_version', 'obligation_id', 'due_utc'}, 'acceptance')
            _require(type(acceptance['schema_version']) is int and acceptance['schema_version'] == 1, 'acceptance_schema_version')
            _require(acceptance['obligation_id'] == subject and _time(acceptance['due_utc']) == outcome, 'acceptance_question_mismatch')
            _require(all(_bytes(acceptance[k], CONTRACT_LIMIT) == _bytes(evidence[k], CONTRACT_LIMIT)
                         for k in ACCEPTANCE_FIELDS), 'acceptance_declaration_mismatch')
            for key in ('acceptance_event_id', 'promisor_role_id', 'beneficiary_role_id', 'authorized_submission_channel_id'):
                _id(evidence[key])
            _require(type(evidence['quality_parameters']) is dict, 'invalid_quality_parameters')
            source = bodies[sid]
            _require(type(evidence['source_byte_length']) is int and len(source) == evidence['source_byte_length']
                     and digest(source) == evidence['source_sha256'], 'source_binding_mismatch')
            _require(evidence['git_object_format'] in ('sha1', 'sha256'), 'git_object_format')
            length = 40 if evidence['git_object_format'] == 'sha1' else 64
            for key in ('source_blob_id', 'source_commit_id'):
                _require(type(evidence[key]) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', evidence[key]), 'invalid_git_identity')
            blob = hashlib.new(evidence['git_object_format'], b'blob ' + str(len(source)).encode('ascii') + b'\0' + source).hexdigest()
            _require(blob == evidence['source_blob_id'], 'git_blob_mismatch')
            path = evidence['source_path']
            _require(type(path) is str and path.startswith(('docs/theory/', 'docs/research/', 'docs/applications/'))
                     and path.endswith('.md') and all(p not in ('', '.', '..') for p in path.split('/'))
                     and '\\' not in path and '\0' not in path, 'invalid_selected_path')
            _require(256 <= len(source) <= SOURCE_LIMIT and b'\0' not in source, 'source_selection_bounds')
            source.decode('utf-8')
            _require(source.count(b'\n') + (not source.endswith(b'\n')) <= 128, 'source_line_limit')
        except (ValueError, UnicodeError) as error:
            diagnostics['reasons'].append(str(error)); return result()
        for identifier in (aid, sid):
            add_observation(by_id[identifier])
            diagnostics['observations'].append({'id': identifier, 'status': 'admitted', 'reason': None})
        source_id = entity('source:' + digest(_bytes([evidence['source_commit_id'], path, blob], CONTRACT_LIMIT)), 'source')
        for name, kind, value in [('promisor', 'entity', entity(evidence['promisor_role_id'], 'role')),
                ('beneficiary', 'entity', entity(evidence['beneficiary_role_id'], 'role')),
                ('channel', 'entity', entity(evidence['authorized_submission_channel_id'], 'channel')),
                ('source', 'entity', source_id), ('acceptance_event', 'string', evidence['acceptance_event_id']),
                ('quality_rule_hash', 'string', evidence['quality_rule_hash']), ('quality_parameters', 'json', evidence['quality_parameters'])]:
            fact(subject, 'obligation.' + name, kind, value, [aid])
        for name, kind, value in [('sha256', 'string', evidence['source_sha256']), ('path', 'string', path),
                ('blob_id', 'string', blob), ('byte_length', 'integer', len(source))]:
            fact(source_id, 'source.' + name, kind, value, [sid])
    packet['entities'] = [{'id': key, 'kind': entities[key]} for key in sorted(entities)]
    packet['observations'].sort(key=lambda o: (_time(o['retained_at']), o['id']))
    packet['assertions'].sort(key=lambda a: (_time(a['known_at']), a['id']))
    try:
        normalized = _bytes(packet, INPUT_LIMIT)
    except ValueError as error:
        diagnostics['reasons'].append('normalized_input:' + str(error)); return result()
    diagnostics['status'] = 'normalized'
    return result(normalized)
