"""Bounded, pure content comparison; this is not preservation certification."""
import json
import math
import re
from datetime import datetime
from decimal import Decimal, DecimalException

BYTE_LIMIT = 65_536
DECLARATION_SHA256 = 'ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65'
COMMON = ('subject_id', 'knowledge_cutoff_utc', 'outcome_cutoff_utc', 'source_observation_ids')
RELEASE = ('seen_id_set', 'opening_eligibility')
OBLIGATION = ('promisor_role_id', 'beneficiary_role_id', 'source_sha256', 'quality_rule_hash',
              'acceptance_event_id', 'authorized_submission_channel_id')
FAMILIES = ('software_component', 'local_delivery_obligation')


class CheckerRefusal(ValueError):
    """Expected evidence or public family is invalid/unusable; no candidate score."""


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, keys):
    _require(type(value) is dict and set(value) == set(keys), 'wrong_object_fields')


def _id(value):
    _require(type(value) is str and 0 < len(value) <= 200 and value.strip() == value, 'invalid_id')


def _hash(value):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid_hash')


def _ids(value, limit=18):
    _require(type(value) is list and len(value) <= limit, 'invalid_id_list')
    for item in value:
        _id(item)
    _require(value == sorted(set(value)), 'id_list_not_sorted_unique')


def _strings(value, nonempty=False):
    _require(type(value) is list and (not nonempty or bool(value)), 'invalid_reasons')
    _require(all(type(v) is str and bool(v) for v in value), 'invalid_reason')
    _require(value == sorted(set(value)), 'reasons_not_sorted_unique')


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def _decimal(token):
    value = float(token)
    try:
        _require(math.isfinite(value) and Decimal(str(value)) == Decimal(token), 'numeric_limit')
    except DecimalException as exc:
        raise ValueError('numeric_limit') from exc
    return value


def _nonfinite(token):
    raise ValueError('nonfinite_json_literal')


def _load(raw):
    _require(type(raw) is bytes, 'bytes_required')
    _require(len(raw) <= BYTE_LIMIT, 'byte_limit')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_float=_decimal, parse_constant=_nonfinite)
        # Also reject lone surrogates and runtime serialization limits, without
        # changing digit or recursion globals or replacing the supplied bytes.
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        return value
    except (UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError('json_runtime_or_unicode_limit') from exc


def _value(field, value):
    if field in ('knowledge_cutoff_utc', 'outcome_cutoff_utc'):
        _require(type(value) is str and re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)', value), 'invalid_time')
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    elif field in ('source_sha256', 'quality_rule_hash'):
        _hash(value)
    elif field == 'source_observation_ids':
        _ids(value)
    elif field == 'seen_id_set':
        _require(type(value) is list and len(value) <= 80, 'invalid_seen_ids')
        _require(all(type(v) is int and v > 0 for v in value), 'positive_integer_required')
        _require(value == sorted(set(value)), 'seen_ids_not_sorted_unique')
    elif field == 'opening_eligibility':
        _require(type(value) is dict and len(value) <= 5, 'invalid_opening_map')
        for key, flag in value.items():
            _require(re.fullmatch('[1-9][0-9]*', key) is not None, 'invalid_release_key')
            int(key)  # Honor the unchanged runtime integer limit for decimal keys.
            _require(type(flag) is bool, 'boolean_required')
    else:
        _id(value)


def _fields(family):
    _require(type(family) is str and family in FAMILIES, 'invalid_planned_family')
    return COMMON + (RELEASE if family == FAMILIES[0] else OBLIGATION)


def _oracle(raw, family, fields):
    p = _load(raw)
    _keys(p, ('oracle_schema_version', 'declaration_sha256', 'manifest_sha256', 'input_bodies',
              'timing_assurance', 'independent_collection_verified', 'status', 'family', 'question_id',
              'required_fields_by_family', 'required_fields', 'inapplicable_fields', 'answers',
              'field_status', 'required_support', 'unknown_reasons', 'eligible_observation_ids',
              'observations', 'missing_slots', 'reasons'))
    _require(type(p['oracle_schema_version']) is int and p['oracle_schema_version'] == 1, 'oracle_version')
    _require(p['declaration_sha256'] == DECLARATION_SHA256, 'declaration_pin')
    _hash(p['manifest_sha256'])
    _require(p['timing_assurance'] == 'caller_claims_only' and p['independent_collection_verified'] is False, 'oracle_assurance')
    _require(p['required_fields_by_family'] == {f: list(_fields(f)) for f in FAMILIES}, 'family_grammar')
    _ids(p['eligible_observation_ids']); _ids(p['missing_slots'], 16); _strings(p['reasons'])
    observations = p['observations']
    _require(type(observations) is list and 1 <= len(observations) <= 18, 'observation_count')
    by_id = {}
    for o in observations:
        _keys(o, ('id', 'kind', 'status', 'reasons')); _id(o['id'])
        _require(o['id'] not in by_id, 'duplicate_observation')
        _require(o['kind'] in ('question_contract', 'release_sample', 'acceptance', 'source_blob'), 'observation_kind')
        _require(o['status'] in ('admitted', 'excluded', 'unavailable'), 'observation_status')
        _strings(o['reasons'], o['status'] != 'admitted')
        _require(o['status'] != 'admitted' or o['reasons'] == [], 'admitted_reasons')
        by_id[o['id']] = o
    _require(list(by_id) == sorted(by_id), 'observation_order')
    eligible = sorted(k for k, o in by_id.items() if o['status'] == 'admitted')
    _require(p['eligible_observation_ids'] == eligible, 'eligible_observations_differ')
    questions = [k for k, o in by_id.items() if o['kind'] == 'question_contract']
    _require(len(questions) == 1, 'question_count')
    q = questions[0]
    _require(sum(o['kind'] == 'release_sample' for o in observations) <= 16, 'release_count')
    expected_body_keys = sorted(k for o in observations for k in
                                ([o['id'], o['id'] + ':headers'] if o['kind'] == 'release_sample' else [o['id']]))
    _require(len(set(expected_body_keys)) == len(expected_body_keys), 'body_key_collision')
    _require(type(p['input_bodies']) is list, 'input_bodies_list')
    body_keys, supplied = [], set()
    for b in p['input_bodies']:
        _keys(b, ('key', 'status', 'byte_length', 'sha256'))
        body_keys.append(b['key'])
        if b['status'] == 'supplied':
            supplied.add(b['key'])
            _require(type(b['byte_length']) is int and b['byte_length'] >= 0, 'body_length')
            _hash(b['sha256'])
        else:
            _require(b['status'] == 'missing' and b['byte_length'] is None and b['sha256'] is None, 'body_status')
    _require(body_keys == expected_body_keys, 'body_inventory')
    _require(all(k in supplied and (by_id[k]['kind'] != 'release_sample' or k + ':headers' in supplied)
                 for k in eligible), 'admitted_body_missing')
    if p['family'] is None:
        _require(p['question_id'] is None and p['required_fields'] == [] and p['inapplicable_fields'] == []
                 and all(p[k] == {} for k in ('answers', 'field_status', 'required_support', 'unknown_reasons'))
                 and p['status'] == 'unavailable' and eligible == [] and bool(p['reasons'])
                 and by_id[q]['status'] != 'admitted', 'unbound_oracle_inconsistent')
        return p
    _require(p['family'] == family, 'oracle_family_differs'); _id(p['question_id'])
    _require(p['required_fields'] == list(fields), 'required_fields')
    _require(p['inapplicable_fields'] == list(OBLIGATION if family == FAMILIES[0] else RELEASE), 'inapplicable_fields')
    for name in ('answers', 'field_status', 'required_support'):
        _keys(p[name], fields)
    _require(type(p['unknown_reasons']) is dict, 'unknown_reasons_object')
    unknown = {f for f in fields if p['field_status'][f] == 'oracle_unknown'}
    _require(set(p['unknown_reasons']) == unknown, 'unknown_reason_fields')
    _require(q in eligible, 'question_not_eligible')
    allowed = ('question_contract', 'release_sample') if family == FAMILIES[0] else ('question_contract', 'acceptance', 'source_blob')
    _require(all(o['kind'] in allowed for o in observations), 'family_observation_kind')
    if family == FAMILIES[1]:
        _require(all(sum(o['kind'] == kind for o in observations) <= 1 for kind in allowed), 'obligation_kind_count')
        _require(p['missing_slots'] == [], 'obligation_missing_slots')
    for f in fields:
        refs = p['required_support'][f]; _ids(refs)
        if f in unknown:
            _require(p['answers'][f] is None and refs == [], 'unknown_value_or_support')
            _strings(p['unknown_reasons'][f], True)
        else:
            _require(p['field_status'][f] == 'known', 'field_status')
            _value(f, p['answers'][f])
            _require(bool(refs) and set(refs) <= set(eligible), 'required_support_not_eligible')
            if f in COMMON[:3]:
                wanted = [q]
            elif f in ('source_observation_ids', 'seen_id_set', 'source_sha256'):
                wanted = eligible
            elif f == 'opening_eligibility':
                _require(q in refs and len(refs) == 2 and all(by_id[r]['kind'] == 'release_sample' for r in refs if r != q), 'opening_support')
                wanted = refs
            else:
                wanted = sorted([q] + [k for k in eligible if by_id[k]['kind'] == 'acceptance'])
                _require(len(wanted) == 2, 'acceptance_support')
            _require(refs == wanted, 'support_convention')
    _require(not (set(COMMON[:3]) & unknown), 'question_fields_unknown')
    _require(datetime.fromisoformat(p['answers']['knowledge_cutoff_utc'].replace('Z', '+00:00')) <=
             datetime.fromisoformat(p['answers']['outcome_cutoff_utc'].replace('Z', '+00:00')), 'cutoff_order')
    _require(p['status'] == ('unavailable' if unknown else 'available'), 'availability_differs')
    _require(not unknown or bool(p['reasons']), 'unavailable_reasons_missing')
    if 'source_observation_ids' not in unknown:
        _require(p['answers']['source_observation_ids'] == eligible, 'source_membership_differs')
    if family == FAMILIES[0]:
        _require(('source_observation_ids' in unknown) == ('seen_id_set' in unknown), 'release_membership_status')
        _require('opening_eligibility' not in unknown or 'seen_id_set' in unknown, 'opening_unavailable_membership')
        _require(not p['missing_slots'] or 'seen_id_set' in unknown, 'missing_slots_known_membership')
        if 'seen_id_set' not in unknown:
            _require(all(int(k) in p['answers']['seen_id_set'] for k in p['answers']['opening_eligibility']), 'opening_not_seen')
            _require(not any(o['status'] == 'unavailable' for o in observations), 'unavailable_history_known')
    else:
        dependent = ('source_observation_ids',) + OBLIGATION
        _require(all(f in unknown for f in dependent) or all(f not in unknown for f in dependent), 'obligation_availability')
        if not unknown:
            _require(len(eligible) == 3, 'obligation_support_incomplete')
    return p


def check_query_content(oracle_bytes, response_bytes, family):
    """Compare oracle bytes with decoded {answers, provenance} bytes or None.

    Family is the public planned family, retaining its denominator even if the
    oracle could not bind a question. Schema defects are explicit diagnostics.
    No result certifies interface isolation, preservation or forecast eligibility.
    """
    try:
        fields = _fields(family)
        p = _oracle(oracle_bytes, family, fields)
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise CheckerRefusal('oracle_or_plan_invalid: ' + str(exc)) from exc
    errors, answers, provenance = [], {}, {}
    response_status = 'missing' if response_bytes is None else 'parsed'
    if response_bytes is not None:
        try:
            candidate = _load(response_bytes)
        except (ValueError, RecursionError, OverflowError) as exc:
            response_status = 'unparseable'
            errors.append('response: ' + str(exc))
        else:
            if type(candidate) is not dict:
                errors.append('response: object_required')
            else:
                if set(candidate) != {'answers', 'provenance'}:
                    errors.append('response: wrong_object_fields')
                for key in ('answers', 'provenance'):
                    value = candidate.get(key)
                    if type(value) is not dict:
                        errors.append(key + ': object_required')
                    else:
                        if set(value) != set(fields):
                            errors.append(key + ': wrong_field_set')
                        if key == 'answers':
                            answers = value
                        else:
                            provenance = value
    eligible = set(p['eligible_observation_ids'])
    results = {}
    for f in fields:
        known = p['family'] is not None and p['field_status'][f] == 'known'
        present = f in answers
        valid_value = False
        if present:
            try:
                _value(f, answers[f]); valid_value = True
            except (ValueError, TypeError, OverflowError) as exc:
                errors.append(f + ': ' + str(exc))
        if not known:
            value_status = 'oracle_unknown'
        elif not present:
            value_status = 'missing'
        elif not valid_value:
            value_status = 'invalid'
        else:
            value_status = 'correct' if answers[f] == p['answers'][f] else 'wrong'
        refs = provenance.get(f)
        valid_refs, invalid_refs, duplicates = set(), [], []
        refs_valid = type(refs) is list
        if not refs_valid:
            if f in provenance:
                errors.append(f + ': provenance_array_required')
        else:
            for ref in refs:
                try:
                    _id(ref)
                    _require(ref in eligible, 'ineligible_reference')
                except (ValueError, TypeError):
                    invalid_refs.append(ref)
                else:
                    if ref in valid_refs:
                        duplicates.append(ref)
                    valid_refs.add(ref)
        required = set(p['required_support'][f]) if known else set()
        missing_support = sorted(required - valid_refs) if known else None
        additional = sorted(valid_refs - required) if known else None
        support_complete = (refs_valid and not missing_support and not invalid_refs) if known else None
        results[f] = {'oracle_status': 'known' if known else 'oracle_unknown',
                      'candidate_value_present': present, 'candidate_value_valid': valid_value,
                      'value_status': value_status, 'missing_support': missing_support,
                      'valid_reference_ids': sorted(valid_refs),
                      'invalid_references': invalid_refs, 'additional_valid_references': additional,
                      'duplicate_valid_references': duplicates, 'support_complete': support_complete,
                      'supported_content_match': value_status == 'correct' and support_complete is True}
    values = list(results.values())
    count = lambda key: sum(v['value_status'] == key for v in values)
    matches = sum(v['supported_content_match'] for v in values)
    return {'checker_schema_version': 1, 'family': family, 'planned_fields': len(fields),
            'evaluable_fields': sum(v['oracle_status'] == 'known' for v in values),
            'oracle_unknown': count('oracle_unknown'), 'response_status': response_status,
            'schema_errors': errors, 'value_matches': count('correct'),
            'missing_values': sum(not v['candidate_value_present'] for v in values),
            'wrong_values': count('wrong'), 'invalid_values': sum(v['candidate_value_present'] and not v['candidate_value_valid'] for v in values),
            'supported_content_matches': matches,
            'missing_support_fields': sum(bool(v['missing_support']) for v in values),
            'invalid_references': sum(len(v['invalid_references']) for v in values),
            'additional_valid_references': sum(len(v['additional_valid_references'] or []) for v in values),
            'duplicate_valid_references': sum(len(v['duplicate_valid_references']) for v in values),
            'content_complete': matches == len(fields) and not errors,
            'interface_runtime_assurance': 'unverified', 'fields': results}
