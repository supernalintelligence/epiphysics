"""Versioned declarations for retained-input fixture assessments, not predictions."""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from copy import deepcopy
from pathlib import Path

from . import manifests, store

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = ((store.__name__, store.IMPLEMENTATION_CODE),
                              (manifests.__name__, manifests.IMPLEMENTATION_CODE))
MAX_BYTES = 262144
MAX_CASES = 32
SOURCE_NAMES = ('work_contracts', 'work_adapters', 'work_runner', 'decision_assessment',
                'improvement', 'store', 'manifests', 'assertions')
MARKER = 'work:declaration'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, label):
    require(type(value) is dict and set(value) == set(expected), 'Invalid ' + label + ' fields')


def text(value, label, maximum=200):
    require(type(value) is str and 0 < len(value) <= maximum and value.strip() == value,
            'Invalid ' + label)


def hash_value(value):
    return store.digest(store.canonical(value).encode())


def hash_text(value, label):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'Invalid ' + label)


def decode(raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'Work input exceeds byte bound')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate work JSON field')
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs)
    store.canonical(result)
    return result


def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'Work input must be a regular file')
        raw = stream.read(MAX_BYTES + 1)
    return decode(raw), raw


def strings(value, label, *, empty=False):
    require(type(value) is list and (empty or value) and len(value) <= 128, 'Invalid ' + label)
    for item in value:
        text(item, label)
    require(len(value) == len(set(value)), 'Duplicate ' + label)


def validate(bundle):
    keys(bundle, {'schema_version', 'declaration', 'public_policy', 'cases', 'outcome_manifest'}, 'work bundle')
    require(type(bundle['schema_version']) is int and bundle['schema_version'] == 1, 'Work schema version')
    d, policy, cases = bundle['declaration'], bundle['public_policy'], bundle['cases']
    keys(d, {'id', 'stage', 'adapter', 'after_step', 'predecessor', 'expires_at', 'max_seconds',
             'public_policy_hash', 'cohort_hash', 'outcome_manifest_hash', 'source_hashes', 'roles', 'method_descriptor', 'method_id'},
         'work declaration')
    require(type(d['id']) is str and re.fullmatch('[A-Za-z0-9_.-]{1,80}', d['id']), 'Invalid work id')
    require(d['stage'] == 'invented_fixture', 'Only invented retained-input fixtures are enabled')
    for field in ('adapter', 'after_step'):
        text(d[field], field)
    require(type(d['max_seconds']) is int and 1 <= d['max_seconds'] <= 20, 'Work budget must be 1–20 seconds')
    store.instant(d['expires_at'])
    if d['predecessor'] is not None:
        keys(d['predecessor'], {'event_id', 'event_hash'}, 'predecessor')
        text(d['predecessor']['event_id'], 'predecessor id')
        hash_text(d['predecessor']['event_hash'], 'predecessor hash')
    keys(d['roles'], {'author', 'reviewer'}, 'work roles')
    for role in d['roles'].values():
        text(role, 'role')
    require(d['roles']['author'] != d['roles']['reviewer'], 'Declared author and reviewer must differ')
    keys(d['source_hashes'], SOURCE_NAMES, 'source pins')
    for h in d['source_hashes'].values():
        hash_text(h, 'source hash')
    keys(policy, {'version', 'adapter', 'denominator', 'family_denominators', 'outcome_definition', 'rules'},
         'public measurement policy')
    require(type(policy['version']) is int and policy['version'] == 1 and policy['adapter'] == d['adapter'],
            'Public policy version/adapter differs')
    text(policy['outcome_definition'], 'outcome definition')
    require(type(cases) is list and 1 <= len(cases) <= MAX_CASES, 'Work case count bound')
    require(type(policy['denominator']) is int and policy['denominator'] == len(cases), 'Fixed denominator differs')
    ids, counts = [], {}
    for case in cases:
        require(type(case) is dict, 'Case must be an object')
        text(case.get('id'), 'case id'); text(case.get('family'), 'case family')
        ids.append(case['id']); counts[case['family']] = counts.get(case['family'], 0) + 1
    require(len(ids) == len(set(ids)), 'Duplicate attempt identity')
    require(type(policy['family_denominators']) is dict and policy['family_denominators'] == counts
            and all(type(n) is int for n in policy['family_denominators'].values()), 'Family denominators differ')
    require(d['public_policy_hash'] == hash_value(policy), 'Public policy hash differs')
    require(d['cohort_hash'] == hash_value(cases), 'Cohort hash differs')
    outcome = bundle['outcome_manifest']
    keys(outcome, {'version', 'cohort_hash', 'records'}, 'outcome manifest')
    require(type(outcome['version']) is int and outcome['version'] == 1, 'Outcome manifest version')
    require(outcome['cohort_hash'] == d['cohort_hash'], 'Outcome cohort binding differs')
    require(type(outcome['records']) is list and len(outcome['records']) == len(cases), 'Outcome count differs')
    require(all(type(row) is dict for row in outcome['records']) and
            [row.get('id') for row in outcome['records']] == ids, 'Outcome case binding differs')
    require(d['outcome_manifest_hash'] == hash_value(outcome), 'Outcome manifest hash differs')
    if d['method_descriptor'] is None:
        require(d['method_id'] is None, 'Unbound method identity')
    else:
        require(manifests.method_identity(d['method_descriptor']) == d['method_id'], 'Method descriptor identity differs')
    return bundle


def measurement_identity(bundle):
    validate(bundle)
    d = bundle['declaration']
    value = {key: d[key] for key in ('adapter', 'public_policy_hash', 'cohort_hash', 'source_hashes')}
    return {'components': value, 'hash': hash_value(value)}


def compare(previous, current):
    if previous is None:
        return {'status': 'unmeasured', 'changed_components': [], 'delta': None}
    changed = [name for name in current['components']
               if previous['components'].get(name) != current['components'][name]]
    return {'status': 'incomparable_contract_change' if changed else 'same_measurement_contract',
            'changed_components': changed, 'delta': None}


def public_instructions(bundle):
    """Expose the exact policy scored by the adapter; never expose fixture gold."""
    validate(bundle)
    return {'policy': deepcopy(bundle['public_policy']), 'policy_hash': bundle['declaration']['public_policy_hash'],
            'scope': 'Declared fixture conformance; not universal correctness or predictive accuracy'}
