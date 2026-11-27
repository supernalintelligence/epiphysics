"""Pure, bounded table/graph round trips for two prospective-pilot families.

These functions neither collect evidence nor register, forecast, score or schedule
work. Decoding has no source access: only saved encoding bytes and public grammar.
"""
from __future__ import annotations

import json
import re
from .store import canonical, digest, instant

INPUT_LIMIT = 262144
ENCODING_LIMIT = 524288
ANSWER_LIMIT = 65536
COMMON = ('subject_id', 'knowledge_cutoff_utc', 'outcome_cutoff_utc', 'source_observation_ids')
FIELDS = {
    'software_component': COMMON + ('seen_id_set', 'opening_eligibility'),
    'local_delivery_obligation': COMMON + ('promisor_role_id', 'beneficiary_role_id', 'source_sha256',
                                        'quality_rule_hash', 'acceptance_event_id', 'authorized_submission_channel_id'),
}
KINDS = {'question', 'software_component', 'release', 'local_delivery_obligation', 'role', 'source', 'channel'}
# subject kind, object type, entity target kind (None for a scalar)
PREDICATES = {
    'question.subject': ('question', 'entity', None),
    'question.knowledge_cutoff': ('question', 'string', None),
    'question.outcome_cutoff': ('question', 'string', None),
    'question.forecast_deadline': ('question', 'string', None),
    'question.resolution_rule': ('question', 'string', None),
    'question.opening_observation': ('question', 'string', None),
    'release.component': ('release', 'entity', 'software_component'),
    'release.id': ('release', 'integer', None),
    'release.draft': ('release', 'boolean', None),
    'release.prerelease': ('release', 'boolean', None),
    **{'release.' + k: ('release', 'json', None) for k in ('tag_name', 'created_at', 'published_at')},
    'obligation.promisor': ('local_delivery_obligation', 'entity', 'role'),
    'obligation.beneficiary': ('local_delivery_obligation', 'entity', 'role'),
    'obligation.channel': ('local_delivery_obligation', 'entity', 'channel'),
    'obligation.source': ('local_delivery_obligation', 'entity', 'source'),
    'obligation.acceptance_event': ('local_delivery_obligation', 'string', None),
    'obligation.quality_rule_hash': ('local_delivery_obligation', 'string', None),
    'obligation.quality_parameters': ('local_delivery_obligation', 'json', None),
    'source.sha256': ('source', 'string', None),
    'source.path': ('source', 'string', None),
    'source.blob_id': ('source', 'string', None),
    'source.byte_length': ('source', 'integer', None),
}
ASSERTION_KEYS = {'id', 'subject', 'predicate', 'object', 'observation_ids', 'known_at', 'supersedes'}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, names, label):
    _require(type(value) is dict and set(value) == set(names), 'Invalid ' + label + ' fields')


def _id(value):
    _require(type(value) is str and 0 < len(value) <= 200 and value.strip() == value, 'Invalid identifier')


def _hash(value):
    _require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value), 'Invalid SHA256')


def _time(value):
    _require(type(value) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)', value),
             'Time must be a UTC RFC3339 instant with at most microsecond precision')
    return instant(value)


def _load(raw, limit):
    _require(type(raw) is bytes and len(raw) <= limit, 'JSON byte limit exceeded')
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
        canonical(value)
        return value
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError('Invalid bounded UTF-8 JSON') from error


def _bytes(value, limit):
    try:
        raw = canonical(value).encode('utf-8')
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError('Invalid JSON value') from error
    _require(len(raw) <= limit, 'Encoded byte limit exceeded')
    return raw


def public_query(family):
    _require(type(family) is str and family in FIELDS, 'Unknown family')
    return {'query_schema_version': 1, 'family': family, 'required_fields': list(FIELDS[family])}


def _current(packet, subject, predicate, observation=None):
    rows = [a for a in packet['assertions'] if a['subject'] == subject and a['predicate'] == predicate
            and (observation is None or observation in a['observation_ids'])]
    replaced = {a['supersedes'] for a in rows}
    return [a for a in rows if a['id'] not in replaced]


def _support(rows):
    _require(rows and all(a['observation_ids'] for a in rows), 'Missing fact or supporting provenance')
    return sorted({ref for a in rows for ref in a['observation_ids']})


def _one(packet, subject, predicate, observation=None):
    rows = _current(packet, subject, predicate, observation)
    support = _support(rows)
    _require(len({canonical(a['object']) for a in rows}) == 1, 'Conflicting active fact: ' + predicate)
    return rows[0]['object']['value'], support


def _validate(packet):
    _keys(packet, {'schema_version', 'family', 'entities', 'observations', 'assertions'}, 'snapshot')
    _require(type(packet['schema_version']) is int and packet['schema_version'] == 1, 'Snapshot version')
    _require(type(packet['family']) is str and packet['family'] in FIELDS, 'Snapshot family')
    for field in ('entities', 'observations', 'assertions'):
        _require(type(packet[field]) is list, 'Snapshot collections must be arrays')
    entities, observations, assertions = {}, {}, {}
    for entity in packet['entities']:
        _keys(entity, {'id', 'kind'}, 'entity'); _id(entity['id'])
        _require(type(entity['kind']) is str and entity['kind'] in KINDS and entity['id'] not in entities,
                 'Unknown entity kind or duplicate identity')
        entities[entity['id']] = entity['kind']
    questions = [key for key, kind in entities.items() if kind == 'question']
    _require(len(questions) == 1, 'Exactly one question entity required')
    for observation in packet['observations']:
        _keys(observation, {'id', 'kind', 'content_sha256', 'observed_at', 'retained_at', 'time_basis'}, 'observation')
        _id(observation['id']); _hash(observation['content_sha256'])
        _require(observation['id'] not in observations, 'Duplicate observation identity')
        _require(observation['kind'] in ('question_contract', 'release_sample', 'acceptance', 'source_blob'), 'Observation kind')
        _require(observation['time_basis'] == 'local_clock', 'Unsupported knowledge-time basis')
        _require(_time(observation['observed_at']) <= _time(observation['retained_at']), 'Retention precedes observation')
        observations[observation['id']] = observation
    for assertion in packet['assertions']:
        _keys(assertion, ASSERTION_KEYS, 'assertion'); _id(assertion['id'])
        _require(assertion['id'] not in assertions, 'Duplicate assertion identity')
        _id(assertion['subject']); predicate = assertion['predicate']
        _require(type(predicate) is str and predicate in PREDICATES, 'Unknown predicate')
        subject_kind, value_type, target_kind = PREDICATES[predicate]
        _require(entities.get(assertion['subject']) == subject_kind, 'Predicate direction/subject kind differs')
        obj = assertion['object']; _keys(obj, {'type', 'value'}, 'typed object')
        _require(obj['type'] == value_type, 'Wrong object type')
        value = obj['value']
        if value_type == 'entity':
            _id(value)
            wanted = packet['family'] if predicate == 'question.subject' else target_kind
            _require(entities.get(value) == wanted, 'Predicate target kind differs')
        elif value_type == 'string':
            _require(type(value) is str and bool(value), 'String fact required')
            if predicate.endswith(('sha256', 'quality_rule_hash')):
                _hash(value)
        elif value_type == 'integer':
            _require(type(value) is int and value >= (1 if predicate == 'release.id' else 0), 'Integer fact required')
        elif value_type == 'boolean':
            _require(type(value) is bool, 'Boolean fact required')
        else:
            canonical(value)
            if predicate.startswith('release.'):
                _keys(value, {'raw', 'precision', 'parse_status'}, 'publisher metadata')
                _require(value['precision'] is None or type(value['precision']) is str, 'Publisher precision')
                _require(value['parse_status'] in ('valid', 'invalid', 'unparsed', 'missing'), 'Publisher parse status')
        refs = assertion['observation_ids']
        _require(type(refs) is list, 'Provenance must be an array')
        for ref in refs:
            _id(ref); _require(ref in observations, 'Unknown supporting observation')
        _require(len(refs) == len(set(refs)), 'Duplicate support in normalized assertion')
        known = _time(assertion['known_at'])
        _require(all(_time(observations[ref]['retained_at']) <= known for ref in refs), 'Fact predates retained support')
        if assertion['supersedes'] is not None:
            _id(assertion['supersedes'])
        if predicate.startswith('release.'):
            samples = [ref for ref in refs if observations[ref]['kind'] == 'release_sample']
            _require(len(samples) == 1, 'A release assertion requires exactly one sample provenance')
        assertions[assertion['id']] = assertion
    replaced = set()
    for assertion in packet['assertions']:
        previous = assertion['supersedes']
        if previous is not None:
            _require(previous in assertions and previous not in replaced, 'Missing revision or revision fork')
            parent = assertions[previous]
            _require(parent['subject'] == assertion['subject'] and parent['predicate'] == assertion['predicate']
                     and _time(parent['known_at']) <= _time(assertion['known_at']), 'Revision subject/predicate/time differs')
            if assertion['predicate'].startswith('release.'):
                parent_sample = {ref for ref in parent['observation_ids'] if observations[ref]['kind'] == 'release_sample'}
                current_sample = {ref for ref in assertion['observation_ids'] if observations[ref]['kind'] == 'release_sample'}
                _require(parent_sample == current_sample, 'Release revision must stay within its source sample')
            replaced.add(previous)
        visited = {assertion['id']}
        while previous is not None:
            _require(previous not in visited, 'Revision cycle')
            visited.add(previous); previous = assertions[previous]['supersedes']
            _require(previous is None or previous in assertions, 'Missing revision ancestor')
    question = questions[0]
    cutoff, _ = _one(packet, question, 'question.knowledge_cutoff')
    cutoff_time = _time(cutoff)
    _require(all(_time(o['retained_at']) <= cutoff_time for o in packet['observations']), 'After-cutoff observation')
    _require(all(_time(a['known_at']) <= cutoff_time for a in packet['assertions']), 'After-cutoff assertion')
    forecast, _ = _one(packet, question, 'question.forecast_deadline')
    outcome, _ = _one(packet, question, 'question.outcome_cutoff')
    _require(cutoff_time <= _time(forecast) <= _time(outcome), 'Question deadline order')
    _one(packet, question, 'question.resolution_rule')
    _one(packet, question, 'question.subject')
    return question


def encode_flat(snapshot_bytes):
    packet = _load(snapshot_bytes, INPUT_LIMIT); _validate(packet)
    return _bytes({'schema_version': 1, 'format': 'flat', 'family': packet['family'],
                   'input_sha256': digest(snapshot_bytes), 'entities': sorted(packet['entities'], key=lambda x: x['id']),
                   'observations': sorted(packet['observations'], key=lambda x: (_time(x['retained_at']), x['id'])),
                   'rows': sorted(packet['assertions'], key=lambda x: (_time(x['known_at']), x['id']))}, ENCODING_LIMIT)


def encode_graph(snapshot_bytes):
    packet = _load(snapshot_bytes, INPUT_LIMIT); _validate(packet)
    edges = []
    for assertion in packet['assertions']:
        entity = assertion['object']['type'] == 'entity'
        edges.append({'id': assertion['id'], 'source': assertion['subject'], 'predicate': assertion['predicate'],
                      'target': assertion['object']['value'] if entity else None,
                      'literal': None if entity else assertion['object'],
                      **{k: assertion[k] for k in ('observation_ids', 'known_at', 'supersedes')}})
    return _bytes({'schema_version': 1, 'format': 'graph', 'family': packet['family'],
                   'input_sha256': digest(snapshot_bytes), 'nodes': sorted(packet['entities'], key=lambda x: x['id']),
                   'observations': sorted(packet['observations'], key=lambda x: (_time(x['retained_at']), x['id'])),
                   'edges': sorted(edges, key=lambda x: (_time(x['known_at']), x['id']))}, ENCODING_LIMIT)


def _packet(raw, form):
    encoded = _load(raw, ENCODING_LIMIT)
    names = {'schema_version', 'format', 'family', 'input_sha256', 'observations'}
    _keys(encoded, names | ({'entities', 'rows'} if form == 'flat' else {'nodes', 'edges'}), 'encoding')
    _require(encoded['format'] == form, 'Encoding format differs'); _hash(encoded['input_sha256'])
    if form == 'flat':
        entities, assertions = encoded['entities'], encoded['rows']
    else:
        entities, assertions = encoded['nodes'], []
        _require(type(encoded['edges']) is list, 'Graph edges must be an array')
        for edge in encoded['edges']:
            _keys(edge, {'id', 'source', 'predicate', 'target', 'literal', 'observation_ids', 'known_at', 'supersedes'}, 'edge')
            _require((edge['target'] is None) != (edge['literal'] is None), 'Graph edge needs one target or typed literal')
            if edge['literal'] is not None:
                _keys(edge['literal'], {'type', 'value'}, 'edge literal')
                _require(edge['literal']['type'] != 'entity', 'Entity graph relations require a target')
            obj = {'type': 'entity', 'value': edge['target']} if edge['target'] is not None else edge['literal']
            assertions.append({'id': edge['id'], 'subject': edge['source'], 'predicate': edge['predicate'],
                               'object': obj, **{k: edge[k] for k in ('observation_ids', 'known_at', 'supersedes')}})
    packet = {'schema_version': encoded['schema_version'], 'family': encoded['family'], 'entities': entities,
              'observations': encoded['observations'], 'assertions': assertions}
    _validate(packet)
    return packet


def _answers(packet, query):
    _keys(query, {'query_schema_version', 'family', 'required_fields'}, 'public query')
    _require(type(query['query_schema_version']) is int and query == public_query(packet['family']), 'Public query differs')
    question = next(e['id'] for e in packet['entities'] if e['kind'] == 'question')
    answers, provenance = {}, {}
    def put(name, subject, predicate, dependencies=()):
        answers[name], provenance[name] = _one(packet, subject, predicate)
        provenance[name] = sorted(set(provenance[name]) | set(dependencies))
    put('subject_id', question, 'question.subject')
    put('knowledge_cutoff_utc', question, 'question.knowledge_cutoff')
    put('outcome_cutoff_utc', question, 'question.outcome_cutoff')
    answers['source_observation_ids'] = sorted(o['id'] for o in packet['observations'])
    provenance['source_observation_ids'] = answers['source_observation_ids'][:]
    subject = answers['subject_id']
    # Derived queries traverse this active binding, so retain its encoded support.
    subject_support = set(provenance['subject_id'])
    if packet['family'] == 'software_component':
        opening, opening_support = _one(packet, question, 'question.opening_observation')
        samples = {o['id'] for o in packet['observations'] if o['kind'] == 'release_sample'}
        _require(opening in samples, 'Missing opening sample')
        seen, opening_values, support = set(), {}, set()
        release_ids = {}
        for entity in packet['entities']:
            if entity['kind'] != 'release':
                continue
            touched = {ref for a in packet['assertions'] if a['subject'] == entity['id'] for ref in a['observation_ids'] if ref in samples}
            _require(touched, 'Release without sampled evidence')
            for sample in sorted(touched):
                values = {}
                for predicate in ('id', 'draft', 'prerelease', 'component'):
                    values[predicate], refs = _one(packet, entity['id'], 'release.' + predicate, sample)
                    support.update(refs)
                _require(values['component'] == subject, 'Release belongs to a different component')
                _require(entity['id'] not in release_ids or release_ids[entity['id']] == values['id'], 'Release identity changed')
                release_ids[entity['id']] = values['id']; seen.add(values['id'])
                if sample == opening:
                    key = str(values['id']); _require(key not in opening_values, 'Duplicate opening release ID')
                    opening_values[key] = not values['draft'] and not values['prerelease']
        _require(len(set(release_ids.values())) == len(release_ids), 'One release ID has multiple entities')
        answers['seen_id_set'] = sorted(seen)
        provenance['seen_id_set'] = sorted(subject_support | support | samples)
        answers['opening_eligibility'] = opening_values
        provenance['opening_eligibility'] = sorted(subject_support | set(opening_support) | {opening} | support)
    else:
        for name, predicate in [('promisor_role_id', 'promisor'), ('beneficiary_role_id', 'beneficiary'),
                                ('quality_rule_hash', 'quality_rule_hash'), ('acceptance_event_id', 'acceptance_event'),
                                ('authorized_submission_channel_id', 'channel')]:
            put(name, subject, 'obligation.' + predicate, subject_support)
        source, source_support = _one(packet, subject, 'obligation.source')
        put('source_sha256', source, 'source.sha256', subject_support | set(source_support))
    _require(set(answers) == set(FIELDS[packet['family']]), 'Answer field set differs')
    result = {'answers': answers, 'provenance': provenance}
    _bytes(result, ANSWER_LIMIT)
    return result


def decode_flat_answers(persisted_encoding_bytes, public_query):
    return _answers(_packet(persisted_encoding_bytes, 'flat'), public_query)


def decode_graph_answers(persisted_encoding_bytes, public_query):
    return _answers(_packet(persisted_encoding_bytes, 'graph'), public_query)
