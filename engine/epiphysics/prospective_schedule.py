"""Pure calendar arithmetic for the exact proposed pilot v2; no launch authority.

Only explicitly supplied bytes and a UTC origin are inputs. A returned calendar
is not a registration receipt, a durable binding, or evidence that a window ran.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta

DECLARATION_SHA256 = 'ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65'
DECLARATION_LIMIT = 131072
SCHEDULE_LIMIT = 131072
_OFFSET = '_offset_seconds'


class ScheduleRefusal(ValueError):
    """A bounded reason code; no partial calendar is returned."""


def _require(condition, reason):
    if not condition:
        raise ScheduleRefusal(reason)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ScheduleRefusal('unrepresentable_schedule') from exc


def _load(raw, limit):
    _require(type(raw) is bytes, 'bytes_required')
    _require(len(raw) <= limit, 'byte_limit_exceeded')

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result

    def integer(text):
        _require(len(text) <= 20, 'integer_limit_exceeded')
        return int(text)

    def noninteger(_):
        raise ScheduleRefusal('noninteger_number')

    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_int=integer, parse_float=noninteger,
                          parse_constant=noninteger)
    except ScheduleRefusal:
        raise
    except RecursionError as exc:
        raise ScheduleRefusal('nesting_unavailable') from exc
    except (ValueError, UnicodeError, OverflowError) as exc:
        raise ScheduleRefusal('invalid_utf8_json') from exc


def _origin(value):
    _require(type(value) is str and len(value) <= 32, 'invalid_utc_origin')
    _require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
                          r'(?:\.[0-9]{1,6})?(?:Z|\+00:00)', value) is not None,
             'invalid_utc_origin')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ScheduleRefusal('invalid_utc_origin') from exc


def _utc(value):
    return value.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _at(origin, offset):
    _require(type(offset) is int and 0 <= offset <= 1209600, 'invalid_offset')
    try:
        return _utc(origin + timedelta(seconds=offset))
    except OverflowError as exc:
        raise ScheduleRefusal('datetime_range_unavailable') from exc


def derive_schedule(declaration_bytes, supplied_origin_utc):
    """Return bounded canonical JSON calendar bytes or raise ScheduleRefusal.

    The exact byte pin authenticates which proposed policy is being calculated,
    not its acceptance or registration. UTC origin accepts Z or +00:00 and up
    to six fractional digits; output always uses six fractional digits and Z.
    """
    _require(type(declaration_bytes) is bytes, 'bytes_required')
    _require(len(declaration_bytes) <= DECLARATION_LIMIT, 'byte_limit_exceeded')
    _require(hashlib.sha256(declaration_bytes).hexdigest() == DECLARATION_SHA256,
             'declaration_digest_mismatch')
    declaration = _load(declaration_bytes, DECLARATION_LIMIT)
    origin = _origin(supplied_origin_utc)
    relative = declaration['schedule']
    # The exact digest fixes the schema, array order, types and cross-bindings.
    # Only named offset fields are times; no generic conversion of integers.
    absolute = {
        kind: [{key[:-len(_OFFSET)] + '_utc' if key.endswith(_OFFSET) else key:
                _at(origin, value) if key.endswith(_OFFSET) else value
                for key, value in record.items()} for record in records]
        for kind, records in relative.items()
    }
    membership = []
    for question in relative['questions']:
        if question['family'] != 'software_component':
            continue
        opening = next(slot for slot in relative['http_slots']
                       if slot['slot_id'] == question['opening_poll_id'])
        membership.append({
            'question_id': question['id'],
            'opening_poll_id': opening['slot_id'],
            'slots': [{'id': slot['slot_id'],
                       'nominal_at': _at(origin, slot['scheduled_offset_seconds'])}
                      for slot in relative['http_slots']
                      if slot['scheduled_offset_seconds'] <= opening['scheduled_offset_seconds']],
        })
    result = {
        'schedule_schema_version': 1,
        'declaration_sha256': DECLARATION_SHA256,
        'supplied_origin_utc': _utc(origin),
        'timing_assurance': 'supplied_origin_only',
        'registered': False,
        'launchable': False,
        'execution_authorized': False,
        'relative_schedule': relative,
        'absolute_schedule': absolute,
        'overall_audit_deadline_offset_seconds': declaration['time_policy']['overall_audit_deadline_offset_seconds'],
        'overall_audit_deadline_utc': _at(origin, declaration['time_policy']['overall_audit_deadline_offset_seconds']),
        'release_snapshot_membership': membership,
        'counts': declaration['counts'],
        'source_policy': declaration['sources'],
        'http_policy': declaration['http_policy'],
        'representation_budgets': declaration['representation_policy']['budgets'],
    }
    output = _canonical(result)
    _require(len(output) <= SCHEDULE_LIMIT, 'byte_limit_exceeded')
    return output


def verify_schedule(declaration_bytes, supplied_origin_utc, schedule_bytes):
    """Return None only for an exact typed calendar; never repair or authorize.

    JSON object order/whitespace may differ. Array order, canonical timestamp
    spelling, exact types, fields and all values must match the pinned calendar.
    """
    expected = derive_schedule(declaration_bytes, supplied_origin_utc)
    supplied = _canonical(_load(schedule_bytes, SCHEDULE_LIMIT))
    _require(supplied == expected, 'schedule_mismatch')
