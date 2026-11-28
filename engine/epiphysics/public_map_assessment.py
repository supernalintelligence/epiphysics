"""Retained static-publication evidence. Never launch a build, verifier or candidate."""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.parse import urlsplit

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
from . import dated_delivery as delivery
from . import decision_diagnosis as historical
from . import store
IMPLEMENTATION_DEPENDENCIES = tuple((module.__name__, module.IMPLEMENTATION_CODE) for module in (delivery, historical, store))

PHASE = 'public_research_map_preparation'
STAGE = 'retained_public_map_preparation'
CONTRACT_ID = 'public-research-map-preparation-v1'
SEMANTIC_ACTIONS = frozenset({'prepare_public_research_map_view', 'repair_public_research_map_preparation'})
NEXT_ACTIONS = frozenset({'repair_public_research_map_preparation', 'prepare_evidence_navigation_evaluation'})
MAX_SECONDS = 10
MAX_REQUEST_BYTES, MAX_CONTRACT_BYTES, MAX_RECEIPT_BYTES = 32768, 65536, 65536
MAX_DATASET_BYTES, MAX_REPORT_BYTES = 262144, 16384
MAX_EVENT_BYTES = MAX_LOG_BYTES = MAX_MANIFEST_BYTES = MAX_OUTPUT_BYTES = 1048576
MAX_PREFIX_BYTES, MAX_PREFIX_EVENTS, MAX_BUNDLE_BYTES, MAX_SOURCE_BYTES = 8388608, 4096, 16777216, 131072
SOURCE_NAMES = ('public_map_assessment.py', 'dated_delivery.py', 'dated_delivery_verifier.py', 'decision_diagnosis.py', 'decision_views.py', 'store.py')
TRANSITIONS = {'improvement_completed', 'improvement_failed'}
CATALOGS = ('registry.json', 'sources-control.json', 'sources-representation.json', 'sources-retrieval.json')
CATEGORIES = ('verifier', 'exporter_tests', 'ui_tests', 'typecheck', 'lint', 'build')
TYPE_ENTRIES = ('src/app/research-map/page.tsx', 'src/data/public-research-map.json',
    'src/components/research-map/ResearchMap.tsx', 'src/components/research-map/Neighborhood.tsx',
    'src/components/research-map/model.ts', 'src/components/research-map/model.test.ts',
    'src/components/research-map/focus.test.tsx', 'src/components/home/ResearchHome.tsx')
LINT_FILES = (*TYPE_ENTRIES[:1], *TYPE_ENTRIES[2:], 'scripts/check-public-research-map-types.mjs')
COMMANDS = {
    'verifier': ['node', 'scripts/verify-public-research-map.mjs', '--json'],
    'exporter_tests': ['node', '--test', '--test-reporter=tap', 'test/public-research-map.test.mjs'],
    'ui_tests': ['node', 'node_modules/jest/bin/jest.js', 'src/components/research-map', '--runInBand', '--json'],
    'typecheck': ['node', 'scripts/check-public-research-map-types.mjs', '--json'],
    'lint': ['node', 'node_modules/eslint/bin/eslint.js', *LINT_FILES],
    'build': ['npm', 'run', 'build'],
}
REQUIRED_FILES = (*TYPE_ENTRIES[:1], *TYPE_ENTRIES[2:], 'src/components/research-map/ResearchMap.module.css',
    'src/components/home/RepresentationLattice.tsx', 'src/components/home/ResearchExperience.module.css',
    'src/components/home/research-stages.ts', 'src/components/home/research-progress.json',
    'scripts/export-public-research-map.mjs', 'scripts/verify-public-research-map.mjs', 'scripts/public-research-map.mjs',
    'scripts/check-public-research-map-types.mjs', 'test/public-research-map.test.mjs',
    'scripts/preprocess-content-simple.js', 'scripts/verify-research-progress.mjs',
    'package.json', 'package-lock.json', 'tsconfig.json', 'next.config.js', 'mdx.config.js', 'jest.config.js', 'jest.setup.js', '.eslintrc.json')
REPORT_CHECKS = ('explicitNodeAndFieldAllowlists', 'committedAndCurrentInputIdentity', 'publishedDocumentRoutes',
    'safeBibliographicURLs', 'publicClaimCitations', 'typedDirectedRelationships', 'savedSnapshotMatchesDeterministicProjection')
PUBLIC_LIMITS = (
    'This is a reviewed public selection, not the complete research catalog. A citation does not certify that a claim is true.',
    'External sources are bibliographic references; article bytes were not archived by this map. Publication and review dates are not collection receipts.',
    'Claim status and basis are curator attributions. Observed local implementation or synthetic results do not establish predictive advantage or independent execution assurance.',
    'Proposed experiment and representation nodes describe catalog concepts, not the completion status of associated runs. Challenges may describe qualifications or competing mechanisms.',
    'The source commit and document digests identify retained local bytes. They are not independent timestamps or evidence of historical availability.',
)
REPORT_LIMIT = 'This report checks the public data boundary and saved snapshot. It does not establish browser accessibility, visual quality, user behavior, scientific truth, deployment or controller acceptance.'
KINDS = ('claim', 'source', 'document', 'representation', 'transformation', 'experiment')
EDGE_KINDS = {'cites': (('claim',), ('source', 'document')), 'challenges': (('claim',), ('claim',)),
    'motivates': (('claim',), ('representation', 'transformation', 'experiment')), 'compares': (('experiment',), ('representation',)),
    'transforms': (('transformation',), ('representation',)), 'depends_on': (KINDS, KINDS), 'implements': (('document',), ('representation', 'transformation'))}
REQUIRED_TEST_NAMES = {'test/public-research-map.test.mjs': ['deterministic public projection preserves direction, qualifications and limits without private/text fields', 'publication verification never silently adds an approved or unapproved new node', 'current catalog edits require a new reviewed committed pin', 'current public document edits do not inherit an older digest', 'private, code, traversal and route-mismatched document bindings are refused', 'committed draft/private documents and missing public routes are refused', 'selected unknown fields fail closed while excluded private nodes stay excluded', 'unsafe bibliographic URLs cannot become clickable public links', 'source date precision and bibliographic-only labels are checked', 'duplicate identifiers, duplicate edges and dangling or mistyped relationships fail', 'claims must retain a real public citation rather than a private-only or missing edge', 'snapshot field injection or payload tampering is rejected without rewriting', 'symlink documents cannot bypass committed-file or local-path validation', 'a missing promisor object cannot execute a configured remote helper', 'complete serialized artifact size is checked before any write, including hash and pretty formatting', 'export refuses leaf and parent symlinks without changing their targets', 'export is exclusive unless an exact previous raw digest authorizes reviewed replacement'], 'src/components/research-map/model.test.ts': ['searches all words across title, statement, status, and basis, without changing source order', 'combines the status filter with search and preserves honest zero matches', 'browses claims only, never interpreting proposal status as a result', 'defaults only absent parameters and leaves invalid, empty, or non-claim IDs unresolved', 'writes a stable encoded selection URL while preserving other query parameters and fragments', 'resolves a restored URL independently of the currently filtered list', 'includes both directed endpoints without adding a second-hop connection', 'uses precisely the same edges for all text groups and the optional graph', 'represents every supported edge type once without replacing its direction or type', 'keeps an isolated claim and empty edge groups honest'], 'src/components/research-map/focus.test.tsx': ['moves focus to the selected heading after following a related claim', 'preserves browse-list focus when selecting a claim from the list', 'moves focus to the selected heading when recovering from an unknown claim link']}
SELECTION = {'schema_version': 1, 'commands': COMMANDS, 'test_names': REQUIRED_TEST_NAMES, 'typecheck_entries': list(TYPE_ENTRIES)}
CONTRACT = {'schema_version': 1, 'contract_id': CONTRACT_ID, 'phase': PHASE, 'stage': STAGE,
    'commands': COMMANDS, 'selection': SELECTION, 'required_files': list(REQUIRED_FILES), 'typecheck_entries': list(TYPE_ENTRIES),
    'report_checks': list(REPORT_CHECKS), 'next_actions': sorted(NEXT_ACTIONS),
    'limits': {'request_bytes': MAX_REQUEST_BYTES, 'contract_receipt_bytes': MAX_RECEIPT_BYTES, 'dataset_bytes': MAX_DATASET_BYTES,
        'verifier_report_bytes': MAX_REPORT_BYTES, 'log_bytes': MAX_LOG_BYTES, 'manifest_bytes': MAX_MANIFEST_BYTES,
        'prefix_bytes': MAX_PREFIX_BYTES, 'prefix_events': MAX_PREFIX_EVENTS, 'bundle_bytes': MAX_BUNDLE_BYTES, 'assessment_seconds': MAX_SECONDS},
    'scope': 'Trusted local retained static-publication checks; no external execution witness, browser, human-use, deployment or predictive gain claim',
    'unchanged_failed_retry': False,
    'publication_metadata': 'UTF-8 YAML frontmatter with unambiguous scalar publication fields; unsupported tags, aliases, merges, duplicate keys or complex publication values are failed artifact checks',
    'repair_identity': 'Direct source/catalog/document/selection bytes and policy/dataset content excluding commit labels and derived digests'}
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)
_require, _keys, _json, _read, _hash, _canonical = (historical._require, historical._keys, historical._json, historical._read, historical._hash, historical._canonical)
_equal, _version, _accepted, _observation, _blob = delivery._equal, delivery._version, delivery._accepted, delivery._observation, delivery._blob
_prefix, _find, _identity, _digest = historical._prefix, historical._find, historical._identity, historical._digest
REPO = Path(__file__).resolve().parents[2]


def _role_limit(role):
    fixed = {'request': MAX_REQUEST_BYTES, 'contract': MAX_CONTRACT_BYTES, 'packet': MAX_EVENT_BYTES,
        'ledger_prefix': MAX_PREFIX_BYTES, 'evidence_origin': MAX_EVENT_BYTES, 'queue_parent': MAX_EVENT_BYTES,
        'failure_request': MAX_REQUEST_BYTES, 'failure_claim': MAX_EVENT_BYTES, 'semantic_parent': MAX_EVENT_BYTES,
        'assessment_report': MAX_OUTPUT_BYTES}
    if role in fixed: return fixed[role]
    if role.startswith('code:epiphysics.') and role[16:] + '.py' in SOURCE_NAMES: return MAX_SOURCE_BYTES
    if role.startswith('observation:') or role.startswith('blob:'): return MAX_EVENT_BYTES
    return None


def _input_limit(role):
    if role == 'dataset': return MAX_DATASET_BYTES
    if role in {'policy', 'selection'} or role.startswith('receipt:'): return MAX_RECEIPT_BYTES
    if role in {'manifest'} or role.startswith(('catalog:', 'file:', 'stdout:', 'stderr:')): return MAX_EVENT_BYTES
    return None


class PreparationError(ValueError):
    def __init__(self, message, artifacts):
        super().__init__(message)
        self.artifacts = {}
        for role, raw in artifacts.items():
            cap = _role_limit(role)
            if cap is not None and type(raw) is bytes and len(raw) <= cap and sum(map(len, self.artifacts.values())) + len(raw) <= MAX_BUNDLE_BYTES:
                self.artifacts[role] = raw


def _put(artifacts, role, raw):
    cap = _role_limit(role)
    _require(cap is not None and type(raw) is bytes and len(raw) <= cap, 'Invalid bounded public-map role: ' + role)
    _require(sum(map(len, artifacts.values())) - len(artifacts.get(role, b'')) + len(raw) <= MAX_BUNDLE_BYTES, 'Public-map bundle exceeds bound')
    artifacts[role] = raw


def _current_sources():
    path, raw, code = _SELF
    _require(IMPLEMENTATION_SOURCE == raw and IMPLEMENTATION_CODE is code and _read(path, MAX_SOURCE_BYTES) == raw, 'Public-map source changed')
    _require(compile(raw, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize) == code, 'Public-map loaded code changed')
    for name, function, original in _FUNCTION_CODES:
        _require(globals().get(name) is function and function.__code__ is original, 'Public-map callable changed: ' + name)
    for name, value in _CONSTANTS:
        _require(type(globals().get(name)) is type(value) and globals().get(name) == value, 'Public-map constant changed: ' + name)
    delivery._current_sources()
    return {'code:epiphysics.' + name[:-3]: _read(path.parent / name, MAX_SOURCE_BYTES) for name in SOURCE_NAMES}


def _request(value):
    _keys(value, {'schema_version', 'phase', 'study_id', 'origin', 'ledger_path', 'evidence_origin', 'queue_parent', 'evidence_checkpoint', 'paths'}, 'map request')
    _require(_version(value['schema_version']) and value['phase'] == PHASE and type(value['study_id']) is str
        and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', value['study_id']), 'Invalid map request identity')
    _keys(value['origin'], {'step_id'}, 'map step')
    _require(type(value['origin']['step_id']) is str and 0 < len(value['origin']['step_id']) <= 200, 'Invalid map step ID')
    _identity(value['evidence_origin']); _identity(value['queue_parent'])
    _keys(value['evidence_checkpoint'], {'seq', 'event_id', 'event_hash'}, 'map checkpoint')
    _identity({key: value['evidence_checkpoint'][key] for key in ('event_id', 'event_hash')})
    _require(type(value['evidence_checkpoint']['seq']) is int and value['evidence_checkpoint']['seq'] > 0, 'Invalid checkpoint sequence')
    _keys(value['paths'], {'contract', 'packet'}, 'map paths')
    _require(all(type(path) is str and Path(path).is_absolute() and 0 < len(path.encode()) <= 4096 and '\0' not in path
        for path in [value['ledger_path'], *value['paths'].values()]), 'Map paths must be bounded absolute locators')


def _scope(study_id): return 'improvement-input:public-research-map:' + study_id + ':'


def _packet(artifacts):
    packet = _json(artifacts['packet'])
    _keys(packet, {'schema_version', 'phase', 'observations'}, 'map packet')
    _require(_version(packet['schema_version']) and packet['phase'] == PHASE and type(packet['observations']) is dict
        and 0 < len(packet['observations']) <= 200, 'Invalid map input observations')
    _require(all(_input_limit(role) is not None and type(event_id) is str and 0 < len(event_id) <= 256
        for role, event_id in packet['observations'].items()), 'Invalid map observation role/ID')
    _require(len(set(packet['observations'].values())) == len(packet['observations']), 'Reused map input observation')
    return packet


def _lineage(request, artifacts, events):
    by_id = _prefix(events)
    origin, parent = _find(by_id, request['evidence_origin']), _find(by_id, request['queue_parent'])
    _equal(_json(artifacts['evidence_origin']), origin, 'Captured C10 event')
    _equal(_json(artifacts['queue_parent']), parent, 'Captured map parent')
    _equal({'seq': events[-1]['seq'], 'event_id': events[-1]['id'], 'event_hash': events[-1]['hash']}, request['evidence_checkpoint'], 'Fixed map checkpoint')
    _require(origin['seq'] <= parent['seq'] <= events[-1]['seq'], 'Map ancestry order')
    original, declared = _accepted(origin)
    _require(original['phase'] in {delivery.CHECK, delivery.REVIEW} and original['stage'] == delivery.PHASES[original['phase']]
        and original['contract_id'] == delivery.CONTRACT_ID and original['checks'] and all(value is True for value in original['checks'].values())
        and origin['body']['next_step']['action'] == original['next_step']['action'] == 'prepare_public_research_map_view', 'Origin is not accepted C10 map preparation evidence')
    identity = {'event_id': origin['id'], 'event_hash': origin['hash'], 'assessment_hash': origin['body']['assessment_identity']['hash'],
        'decision_assessment_hash': original['assessment_identity']['hash'], 'capture_sha256': _hash(artifacts['evidence_origin'])}
    step = parent['body']['next_step']
    _require(step['id'] == request['origin']['step_id'] and step['state'] == 'queued', 'Map request does not own queued step')
    semantic, mode = parent, 'initial'
    if parent['kind'] == 'improvement_failed':
        _require(step['action'] == 'diagnose_failed_assessment', 'Invalid operational failure successor')
        claim, semantic, prior = (_json(artifacts[role]) for role in ('failure_claim', 'semantic_parent', 'failure_request'))
        _request(prior)
        _equal(by_id.get(claim['id']), claim, 'Failure claim'); _equal(by_id.get(semantic['id']), semantic, 'Failure semantic parent')
        _require(semantic['seq'] < claim['seq'] < parent['seq'] and claim['kind'] == 'improvement_started'
            and claim['body']['run_key'] == parent['body']['run_key'], 'Failure claim order')
        _equal(claim['body']['request'], parent['body']['request'], 'Failure request identity')
        _equal(claim['body']['claimed_step'], semantic['body']['next_step'], 'Failure semantic claim')
        _equal(prior['evidence_origin'], request['evidence_origin'], 'Failure immutable C10 origin')
        _equal(prior['queue_parent'], {'event_id': semantic['id'], 'event_hash': semantic['hash']}, 'Failure original parent')
        _equal(prior['origin']['step_id'], semantic['body']['next_step']['id'], 'Failure original step')
        _equal(parent['body']['request']['after_step'], prior['origin']['step_id'], 'Failure controller origin')
        _equal(_hash(artifacts['failure_request']), parent['body']['request']['manifest']['decision-input:request'], 'Failure request digest')
        _equal([event for event in events if event['kind'] in TRANSITIONS and event['seq'] < claim['seq']][-1], semantic, 'Failure queue owner')
        observation = _observation(by_id, 'improvement:' + parent['body']['run_key'] + ':input:decision-input:request', 'improvement-input:decision-input:request')
        _require(claim['seq'] < observation['seq'] < parent['seq'], 'Failure request capture order')
        _equal(_blob(artifacts, observation), artifacts['failure_request'], 'Failure captured request')
        mode = 'failed_attempt_continuation'
    previous = None
    action = semantic['body']['next_step']['action']
    _require(action in SEMANTIC_ACTIONS, 'Wrong semantic action for public-map preparation')
    if action == 'prepare_public_research_map_view':
        _equal(semantic, origin, 'Initial map predecessor')
    else:
        previous, inputs = _accepted(semantic)
        _require(previous['phase'] == PHASE and previous['stage'] == STAGE and previous['contract_id'] == CONTRACT_ID
            and previous['next_step']['action'] == action and not all(previous['checks'].values()), 'Not a checked map repair predecessor')
        _equal(previous['evidence_origin'], identity, 'Repair immutable C10 identity')
        _equal(inputs.get('evidence_origin'), identity['capture_sha256'], 'Repair captured C10 digest')
        mode = 'checked_repair' if mode == 'initial' else mode
    return identity, {'mode': mode, 'failed_event_id': parent['id'] if parent['kind'] == 'improvement_failed' else None, 'semantic_action': action}, previous


def _required_inputs(inputs):
    manifest = _json(inputs['manifest'])
    _keys(manifest, {'schema_version', 'source_commit', 'ui_commit', 'files', 'executables'}, 'source/input manifest')
    _require(_version(manifest['schema_version']), 'Manifest version')
    for name in ('source_commit', 'ui_commit'):
        _require(type(manifest[name]) is str and re.fullmatch('[a-f0-9]{40}', manifest[name]), 'Manifest commit identity')
    _keys(manifest['executables'], {'node', 'npm'}, 'fixed process executables')
    for value in manifest['executables'].values():
        _keys(value, {'path', 'sha256', 'version'}, 'executable identity')
        _require(type(value['path']) is str and Path(value['path']).is_absolute() and 0 < len(value['path']) <= 4096
            and type(value['version']) is str and 0 < len(value['version']) <= 512, 'Invalid executable identity')
        _digest(value['sha256'])
    files = manifest['files']
    _require(type(files) is dict and set(REQUIRED_FILES) <= set(files) and len(files) <= 150, 'Missing fixed source/input files')
    for path, identity in files.items():
        _require(path in REQUIRED_FILES or (type(path) is str and re.fullmatch(r'docs/(research|theory|experiments)/[A-Za-z0-9_/-]+\.md', path)
            and all(part not in {'.', '..', 'private', 'planning', 'internal', 'draft', 'drafts'} for part in path.split('/'))), 'Unapproved retained file path')
        _keys(identity, {'sha256', 'bytes'}, 'file identity'); _digest(identity['sha256'])
        _require(type(identity['bytes']) is int and 0 <= identity['bytes'] <= MAX_EVENT_BYTES, 'File identity bound')
        raw = inputs['file:' + path]
        _equal({'sha256': _hash(raw), 'bytes': len(raw)}, identity, 'Retained file identity')
        if path in REQUIRED_FILES:
            _equal(raw, _read(REPO / path, MAX_EVENT_BYTES), 'Current fixed source/input ' + path)
    _equal(_json(inputs['selection']), SELECTION, 'Fixed validation selections')
    expected = {'dataset', 'policy', 'manifest', 'selection'} | {'catalog:' + name for name in CATALOGS}
    expected |= {'file:' + path for path in files}
    expected |= {prefix + ':' + category for prefix in ('receipt', 'stdout', 'stderr') for category in CATEGORIES}
    _keys(inputs, expected, 'exact map evidence roles')
    package = _json(inputs['file:package.json'])
    _require(package['scripts']['build'] == 'next build' and 'preprocess-content-simple.js' in package['scripts']['prebuild']
        and 'verify-research-progress.mjs' in package['scripts']['prebuild'], 'Production build hooks differ')
    return manifest


def _stream(value, raw, *, overflow=False):
    _keys(value, {'bytes', 'sha256', 'complete', 'observed_bytes', 'full_sha256'}, 'retained process stream')
    _require(type(value['bytes']) is int and type(value['observed_bytes']) is int and type(value['complete']) is bool
        and value['bytes'] == len(raw) <= MAX_LOG_BYTES and value['observed_bytes'] >= len(raw), 'Invalid stream byte counts')
    _equal(value['sha256'], _hash(raw), 'Process stream prefix digest')
    if value['complete']:
        _require(value['observed_bytes'] == len(raw) and value['full_sha256'] == _hash(raw), 'Complete stream identity differs')
    else:
        _require(value['full_sha256'] is None, 'Incomplete output cannot claim a full hash')
    if overflow:
        _require(not value['complete'] and len(raw) == MAX_LOG_BYTES and value['observed_bytes'] > MAX_LOG_BYTES,
            'Output-limit failure lacks actual bounded overflow prefix')


def _receipts(inputs, manifest):
    result = {}
    identities = {role: _hash(raw) for role, raw in inputs.items() if not role.startswith(('receipt:', 'stdout:', 'stderr:'))}
    for category in CATEGORIES:
        value = _json(inputs['receipt:' + category])
        _keys(value, {'schema_version', 'category', 'command', 'cwd', 'executable', 'started_at', 'ended_at', 'elapsed_seconds',
            'returncode', 'termination', 'inputs_before', 'inputs_after', 'stdout', 'stderr', 'outputs', 'generated_inputs'}, 'fixed local process receipt')
        _require(_version(value['schema_version']) and value['category'] == category, 'Receipt category differs')
        executable = manifest['executables'][COMMANDS[category][0]]
        _equal(value['executable'], executable, 'Actual executable identity')
        _equal(value['command'], [executable['path'], *COMMANDS[category][1:]], 'Required fixed command')
        _equal(value['cwd'], str(REPO), 'Receipt working directory')
        _equal(value['inputs_before'], identities, 'Process inputs before execution')
        _equal(value['inputs_after'], identities, 'Process inputs after execution')
        seconds = value['elapsed_seconds']
        wall = (store.instant(value['ended_at']) - store.instant(value['started_at'])).total_seconds()
        _require(type(seconds) in (int, float) and math.isfinite(seconds) and 0 <= seconds <= wall + .1 and wall >= 0, 'Process duration')
        _keys(value['termination'], {'kind', 'stream'}, 'termination receipt')
        kind, stream = value['termination']['kind'], value['termination']['stream']
        _require(kind in {'completed', 'timeout', 'output_limit'} and (type(value['returncode']) is int or value['returncode'] is None), 'Invalid process termination')
        _require((kind == 'completed' and type(value['returncode']) is int and stream is None)
            or (kind == 'timeout' and value['returncode'] != 0 and stream is None)
            or (kind == 'output_limit' and stream in {'stdout', 'stderr'}), 'Inconsistent process termination')
        for name in ('stdout', 'stderr'):
            _stream(value[name], inputs[name + ':' + category], overflow=kind == 'output_limit' and stream == name)
        if kind == 'completed':
            _require(value['stdout']['complete'] and value['stderr']['complete'], 'Completed process requires complete streams')
        _keys(value['outputs'], {'public_content'} if category == 'build' else set(), 'Attributed process outputs')
        if category == 'build':
            output = value['outputs']['public_content']
            if output is not None:
                _keys(output, {'sha256', 'bytes'}, 'Attributed built-content identity'); _digest(output['sha256'])
                _require(type(output['bytes']) is int and 0 <= output['bytes'] <= 64 * 1024 * 1024, 'Built-content identity bound')
            _require(output is not None or kind != 'completed' or value['returncode'] != 0, 'Successful build lacks attributed content identity')
        _keys(value['generated_inputs'], {'public_content'} if category == 'verifier' else set(), 'Generated process inputs')
        result[category] = value
    _equal(result['verifier']['generated_inputs']['public_content'], result['build']['outputs']['public_content'], 'Verifier used exact generated build content')
    _require(result['verifier']['generated_inputs']['public_content'] is not None or result['verifier']['returncode'] != 0, 'Verifier cannot pass without generated content')
    _require(store.instant(result['build']['ended_at']) <= store.instant(result['verifier']['started_at']), 'Final verifier must follow build')
    return result


def _inputs(request, artifacts, events):
    packet, by_id = _packet(artifacts), {event['id']: event for event in events}
    values = {}
    for role, event_id in packet['observations'].items():
        observation = _observation(by_id, event_id, _scope(request['study_id']) + role)
        _require(request['queue_parent']['event_id'] != event_id and observation['seq'] > _find(by_id, request['queue_parent'])['seq'], 'Map input predates current queue parent')
        raw = _blob(artifacts, observation)
        _require(len(raw) <= _input_limit(role), 'Map input exceeds its role cap')
        values[role] = raw
    scoped = {event['id'] for event in events if event['kind'] == 'observation' and event['body']['source'].startswith(_scope(request['study_id']))}
    _equal(sorted(scoped), sorted(packet['observations'].values()), 'Checkpoint omitted or duplicated scoped input')
    return values


def _metadata(artifacts, manifest):
    request = _json(artifacts['request']); _request(request)
    _equal(_json(artifacts['contract']), CONTRACT, 'Fixed public-map contract')
    events = _json(artifacts['ledger_prefix'])
    origin, ancestry, previous = _lineage(request, artifacts, events)
    inputs = _inputs(request, artifacts, events)
    source_manifest = _required_inputs(inputs)
    receipts = _receipts(inputs, source_manifest)
    expected = {'request', 'contract', 'packet', 'ledger_prefix', 'evidence_origin', 'queue_parent'}
    by_id = {event['id']: event for event in events}
    observation_roles = _packet(artifacts)['observations']
    observations = list(observation_roles.values())
    for category, receipt in receipts.items():
        captured = by_id[observation_roles['receipt:' + category]]
        _require(store.instant(receipt['ended_at']) <= store.instant(captured['recorded_at']), 'Receipt captured before process ended')
    if ancestry['mode'] == 'failed_attempt_continuation':
        expected |= {'failure_request', 'failure_claim', 'semantic_parent'}
        parent = _find(by_id, request['queue_parent'])
        observations.append('improvement:' + parent['body']['run_key'] + ':input:decision-input:request')
    for event_id in observations:
        event = _observation(by_id, event_id)
        expected |= {'observation:' + event_id, 'blob:' + event['body']['content_hash']}
        _equal(_json(artifacts['observation:' + event_id]), event, 'Captured input observation')
        _blob(artifacts, event)
    for role, raw in _current_sources().items():
        expected.add(role); _equal(artifacts[role], raw, 'Frozen adapter dependency')
    _keys(artifacts, expected, 'Captured public-map artifacts')
    relevant = {role: _hash(raw) for role, raw in inputs.items() if role.startswith(('file:', 'catalog:')) or role == 'selection'}
    relevant['policy_content'] = _content_fingerprint(inputs['policy'], policy=True)
    relevant['dataset_content'] = _content_fingerprint(inputs['dataset'], policy=False, inputs=inputs)
    # Commit labels/times/execution IDs alone do not constitute a repaired input.
    relevant.update({role: digest for role, digest in manifest.items() if role.startswith('code:')})
    relevant_hash = _hash(_canonical(relevant))
    if previous is not None:
        _require(previous['relevant_input_hash'] != relevant_hash, 'Unchanged failed public-map preparation may not be repeated')
    return {'schema_version': 1, 'contract_id': CONTRACT_ID, 'study_id': request['study_id'], 'phase': PHASE, 'stage': STAGE,
        'status': 'prepared', 'origin': deepcopy(request['origin']), 'evidence_origin': origin,
        'queue_parent': deepcopy(request['queue_parent']), 'evidence_checkpoint': deepcopy(request['evidence_checkpoint']), 'ancestry': ancestry,
        'assessment_identity': {'schema_version': 1, 'hash': _hash(_canonical(manifest))},
        'input_hashes': {role: value for role, value in manifest.items() if not role.startswith('code:')},
        'source_hashes': {name: manifest['code:epiphysics.' + name[:-3]] for name in SOURCE_NAMES},
        'relevant_input_hash': relevant_hash, 'source_commit': source_manifest['source_commit'], 'ui_commit': source_manifest['ui_commit'],
        'scope': CONTRACT['scope']}


def prepare_public_map(path):
    artifacts, started = {}, time.monotonic()
    try:
        _put(artifacts, 'request', _read(path, MAX_REQUEST_BYTES))
        request = _json(artifacts['request']); _request(request)
        for role, locator in request['paths'].items(): _put(artifacts, role, _read(locator, _role_limit(role)))
        packet = _packet(artifacts)
        for role, raw in _current_sources().items(): _put(artifacts, role, raw)
        ledger = store.Ledger.open_readonly(request['ledger_path'])
        try:
            ledger.db.execute('BEGIN')
            end = request['evidence_checkpoint']['seq']
            bound = ledger.db.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(body AS BLOB))),0),COALESCE(MAX(length(CAST(body AS BLOB))),0) FROM events WHERE seq<=?', (end,)).fetchone()
            _require(0 < bound[0] <= MAX_PREFIX_EVENTS and bound[1] <= MAX_PREFIX_BYTES and bound[2] <= MAX_EVENT_BYTES, 'Map prefix exceeds bound')
            events = [{**dict(row), 'body': _json(row['body'])} for row in ledger.db.execute('SELECT * FROM events WHERE seq<=? ORDER BY seq', (end,))]
            _put(artifacts, 'ledger_prefix', _canonical(events)); by_id = _prefix(events)
            for role in ('evidence_origin', 'queue_parent'): _put(artifacts, role, _canonical(_find(by_id, request[role])))
            parent = _find(by_id, request['queue_parent'])
            ids = list(packet['observations'].values())
            if parent['kind'] == 'improvement_failed': ids.append('improvement:' + parent['body']['run_key'] + ':input:decision-input:request')
            for event_id in ids:
                observation = _observation(by_id, event_id)
                _put(artifacts, 'observation:' + event_id, _canonical(observation))
                raw = _read(ledger.root / 'blobs' / observation['body']['content_hash'], MAX_EVENT_BYTES)
                _require(len(raw) == observation['body']['size'] and _hash(raw) == observation['body']['content_hash'], 'Corrupt retained input')
                _put(artifacts, 'blob:' + observation['body']['content_hash'], raw)
            if parent['kind'] == 'improvement_failed':
                claims = [event for event in events if event['kind'] == 'improvement_started' and event['body']['run_key'] == parent['body']['run_key']]
                _require(len(claims) == 1, 'Missing unique failure claim')
                claim = claims[0]
                semantic = [event for event in events if event['kind'] in TRANSITIONS and event['seq'] < claim['seq']][-1]
                observation = by_id['improvement:' + parent['body']['run_key'] + ':input:decision-input:request']
                _put(artifacts, 'failure_request', _blob(artifacts, observation))
                _put(artifacts, 'failure_claim', _canonical(claim)); _put(artifacts, 'semantic_parent', _canonical(semantic))
        finally: ledger.close()
        manifest = {role: _hash(raw) for role, raw in artifacts.items()}
        report = _metadata(artifacts, manifest)
        _require(time.monotonic() - started <= MAX_SECONDS, 'Map preparation exceeded budget')
        return {'artifacts': artifacts, 'manifest': manifest, 'report': report}
    except (ValueError, OSError, TypeError, KeyError, AttributeError, IndexError, RecursionError, OverflowError, sqlite3.Error) as error:
        raise PreparationError(str(error), artifacts) from error


def check_prepared_public_map(prepared):
    _keys(prepared, {'artifacts', 'manifest', 'report'}, 'prepared map')
    _keys(prepared['manifest'], prepared['artifacts'], 'prepared manifest')
    total = 0
    for role, raw in prepared['artifacts'].items():
        cap = _role_limit(role)
        _require(cap is not None and type(raw) is bytes and len(raw) <= cap, 'Prepared map role exceeds bound')
        _equal(_hash(raw), prepared['manifest'][role], 'Prepared map digest'); total += len(raw)
    _require(total <= MAX_BUNDLE_BYTES, 'Prepared map bundle exceeds bound')
    _equal(prepared['report'], _metadata(prepared['artifacts'], prepared['manifest']), 'Prepared map metadata')


def validate_lineage(prepared, actual_events, after_step):
    check_prepared_public_map(prepared)
    request = _json(prepared['artifacts']['request'])
    _equal(after_step, request['origin']['step_id'], 'Authoritative map step')
    _equal([event for event in actual_events if event['seq'] <= request['evidence_checkpoint']['seq']], _json(prepared['artifacts']['ledger_prefix']), 'Authoritative map checkpoint')
    parent = [event for event in actual_events if event['kind'] in TRANSITIONS][-1]
    _equal({'event_id': parent['id'], 'event_hash': parent['hash']}, request['queue_parent'], 'Stale map queue parent')
    _require(not any(event['seq'] > request['evidence_checkpoint']['seq'] and event['kind'] == 'observation'
        and event['body']['source'].startswith(_scope(request['study_id'])) for event in actual_events), 'Later scoped map capture omitted')


def _text(value, label, cap=4096):
    _require(type(value) is str and value.strip() and len(value.encode('utf-8')) <= cap
        and not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value), 'Invalid public ' + label)
    return value


def _public_json(raw):
    value = _json(raw.decode('utf-8'))
    _canonical(value)  # Invalid Unicode/nonfinite values are failed artifacts, not executable input.
    return value


def _derived_identity_checks(value, inputs):
    """Keep repairable identity validity while discarding equivalent hash labels."""
    checks = {'payload_hash': False, 'catalog_hash': None, 'source_commit': None, 'documents': None}
    if type(value) is not dict: return checks
    checks['payload_hash'] = value.get('payloadHash') == _hash(_canonical({key: item for key, item in value.items() if key != 'payloadHash'}))
    try:
        policy = _public_json(inputs['policy'])
        manifest = _json(inputs['manifest'])
        checks['source_commit'] = value.get('sourceCommit') == policy['sourceCommit'] == manifest['source_commit']
        checks['catalog_hash'] = value.get('catalogHash') == _hash(_canonical({'policy': policy,
            'files': [{'name': name, 'hash': _hash(inputs['catalog:' + name])} for name in CATALOGS]}))
        if type(value.get('nodes')) is list:
            documents = []
            for node in value['nodes']:
                if type(node) is dict and node.get('kind') == 'document':
                    path = policy['documents'][node['id']]['repoPath']
                    documents.append({'commit': node.get('commit') == policy['sourceCommit'],
                        'content_hash': node.get('contentHash') == _hash(inputs['file:' + path])})
            checks['documents'] = documents
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        pass  # Unavailable validity stays explicit; full artifact checks run later.
    return checks


def _content_fingerprint(raw, *, policy, inputs=None):
    """Identity labels cannot reopen a checked failure; content repairs can."""
    try:
        value = _public_json(raw)
        identity_checks = _derived_identity_checks(value, inputs) if not policy else None
        if type(value) is dict:
            value.pop('sourceCommit', None)
            if not policy:
                value.pop('catalogHash', None); value.pop('payloadHash', None)
                if type(value.get('nodes')) is list:
                    for node in value['nodes']:
                        if type(node) is dict and node.get('kind') == 'document':
                            node.pop('commit', None); node.pop('contentHash', None)
        return _hash(_canonical({'content': value, 'identity_checks': identity_checks}))
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        return _hash(raw)  # Unparseable artifact bytes remain an explicit repair input.


def _publication_scalar(value):
    value = value.strip()
    if value.startswith('#'): return None
    if value.startswith('"'):
        match = re.fullmatch(r'("(?:[^"\\]|\\.)*")(?:[ \t]+#.*)?', value)
        _require(match is not None, 'Ambiguous quoted publication metadata')
        return _json(match[1])
    if value.startswith("'"):
        match = re.fullmatch(r"('(?:[^']|'')*')(?:[ \t]+#.*)?", value)
        _require(match is not None, 'Ambiguous quoted publication metadata')
        return match[1][1:-1].replace("''", "'")
    value = re.split(r'[ \t]+#', value, maxsplit=1)[0].strip()
    _require(not any(char in value for char in '&*!{}[]|>') and ': ' not in value, 'Unsupported publication metadata scalar')
    if value in {'false', 'False', 'FALSE'}: return False
    if value in {'true', 'True', 'TRUE'}: return True
    if value in {'', '~', 'null', 'Null', 'NULL'} or re.match(r'^[+-]?(?:[0-9]|\.[0-9])', value): return None
    return value


def _published_document(raw):
    """Independently check the publication boundary, without a YAML execution engine.

    The fixed public documents use ordinary scalar YAML publication metadata.
    Ambiguous/unsupported YAML fails this artifact criterion rather than being
    interpreted as public or raising from request preparation.
    """
    text = raw.decode('utf-8')
    lines = text.splitlines()
    _require(lines and lines[0] == '---', 'Public document lacks YAML frontmatter')
    end = next((index for index in range(1, len(lines)) if lines[index] == '---'), None)
    _require(end is not None, 'Unterminated publication frontmatter')
    fields, last = {}, None
    publication = {'title', 'draft', 'private', 'published', 'visibility', 'status'}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith('#'): continue
        if line[0].isspace():
            _require(last not in publication, 'Complex publication metadata value')
            continue
        match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*))?', line)
        _require(match is not None and match[1] not in fields, 'Ambiguous or duplicate frontmatter key')
        last = match[1]
        fields[last] = _publication_scalar(match[2] or '') if last in publication else None
    _text(fields.get('title'), 'document title')
    _require(('draft' not in fields or fields['draft'] is False)
        and ('private' not in fields or fields['private'] is False)
        and ('published' not in fields or fields['published'] is True)
        and ('visibility' not in fields or fields['visibility'] == 'public')
        and fields.get('status') not in {'draft', 'private', 'internal'}, 'Document is not published')


def _date(value, partial=False):
    _require(type(value) is str and re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?' if partial else r'\d{4}-\d{2}-\d{2}', value), 'Invalid source date')
    date.fromisoformat(value + ('-01-01' if len(value) == 4 else '-01' if len(value) == 7 else ''))


def _dataset(inputs, manifest):
    data, policy = _public_json(inputs['dataset']), _public_json(inputs['policy'])
    _keys(data, {'schemaVersion', 'sourceCommit', 'catalogHash', 'nodes', 'edges', 'limits', 'payloadHash'}, 'public dataset fields')
    _keys(policy, {'schemaVersion', 'sourceCommit', 'catalogFiles', 'nodeIds', 'documents'}, 'publication policy')
    _require(_version(data['schemaVersion']) and _version(policy['schemaVersion']), 'Public schema version')
    _equal(policy['catalogFiles'], list(CATALOGS), 'Fixed catalog list')
    _equal(data['sourceCommit'], policy['sourceCommit'], 'Dataset/policy commit')
    _equal(data['sourceCommit'], manifest['source_commit'], 'Declared catalog/document commit')
    approved = policy['nodeIds']
    _require(type(approved) is list and 0 < len(approved) <= 100 and all(type(node) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', node) for node in approved)
        and len(set(approved)) == len(approved) and type(policy['documents']) is dict, 'Public node allowlist')
    catalogs = [_public_json(inputs['catalog:' + name]) for name in CATALOGS]
    registry = catalogs[0]
    _keys(registry, {'schema_version', 'nodes', 'edges'}, 'registry')
    _require(_version(registry['schema_version']) and type(registry['nodes']) is list and type(registry['edges']) is list, 'Registry shape')
    all_nodes = list(registry['nodes'])
    for catalog in catalogs[1:]:
        _require(type(catalog) is list and all(type(node) is dict and node.get('kind') == 'source' for node in catalog), 'Source catalog shape')
        all_nodes.extend(catalog)
    _require(len(all_nodes) <= 5000 and len(registry['edges']) <= 20000, 'Catalog bound')
    by_id = {}
    for node in all_nodes:
        _require(type(node) is dict and type(node.get('id')) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', node['id'])
            and node['id'] not in by_id and node.get('kind') in KINDS, 'Catalog identity/kind')
        by_id[node['id']] = node
    projected, docs = [], set()
    for key in approved:
        node = by_id[key]
        common = {name: node[name] for name in ('id', 'kind', 'title')}
        _text(node['title'], 'title', 512)
        if node['kind'] == 'claim':
            _keys(node, {'id', 'kind', 'title', 'statement', 'status', 'basis'}, 'catalog claim')
            _require(node['status'] in {'definition', 'hypothesis', 'reported_result', 'implementation_finding', 'contested'}
                and node['basis'] in {'reported', 'inferred', 'observed'}, 'Claim status/basis')
            projected.append({**common, 'statement': _text(node['statement'], 'statement'), 'status': node['status'], 'basis': node['basis']})
        elif node['kind'] == 'source':
            required = {'id', 'kind', 'title', 'url', 'date', 'date_type', 'reviewed_on', 'bibliographic_only', 'claim_supported', 'limitation'}
            _require(required <= set(node) <= required | {'first_submitted', 'reprint_date', 'revision', 'version_reviewed'}, 'Public source fields')
            _require(node['bibliographic_only'] is True, 'Source must remain bibliographic')
            href = _text(node['url'], 'source URL', 2048)
            url = urlsplit(href)
            _require(href.startswith('https://') and url.scheme == 'https' and url.hostname and not url.username and not url.password
                and not re.search(r'\s|\\', href) and url.port != 443, 'Unsafe/noncanonical source URL')
            _text(node['claim_supported'], 'support description')
            if node['date'] is None:
                _require(node['date_type'] in {'undated_live_documentation', 'mutable_main_revision_unverified'}, 'Undated source reason')
            else: _date(node['date'], True)
            _date(node['reviewed_on'])
            projected.append({**common, 'href': href, 'date': node['date'], 'dateType': _text(node['date_type'], 'date type', 128),
                'reviewedOn': node['reviewed_on'], 'bibliographicOnly': True, 'limitations': [_text(node['limitation'], 'source limitation')]})
        elif node['kind'] == 'document':
            _keys(node, {'id', 'kind', 'title', 'repo_path'}, 'catalog document')
            binding = policy['documents'][key]
            _keys(binding, {'repoPath', 'href'}, 'public document binding')
            path = node['repo_path']
            _require(type(path) is str and re.fullmatch(r'docs/(research|theory|experiments)/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\.md', path)
                and not any(part.lower() in {'planning', 'private', 'internal', 'draft', 'drafts'} for part in path.split('/')), 'Unsafe public document path')
            href = '/' + re.sub(r'/index$', '', path[5:-3])
            _equal(binding, {'repoPath': path, 'href': href}, 'Explicit public route')
            _published_document(inputs['file:' + path])
            projected.append({**common, 'href': href, 'contentHash': _hash(inputs['file:' + path]), 'commit': policy['sourceCommit']})
            docs.add(key)
        else:
            _keys(node, {'id', 'kind', 'title', 'status'}, 'proposal fields')
            _require(node['status'] == 'proposed', 'Proposal must remain proposed')
            projected.append({**common, 'status': 'proposed'})
    _equal(sorted(policy['documents']), sorted(docs), 'Exact document allowlist')
    expected_edges, seen = [], set()
    for edge in registry['edges']:
        _keys(edge, {'source', 'target', 'type'}, 'typed directed relationship')
        kinds = EDGE_KINDS[edge['type']]
        _require(by_id[edge['source']]['kind'] in kinds[0] and by_id[edge['target']]['kind'] in kinds[1], 'Relationship direction/kinds')
        key = (edge['source'], edge['target'], edge['type'])
        _require(key not in seen, 'Duplicate relationship'); seen.add(key)
        if edge['source'] in approved and edge['target'] in approved: expected_edges.append(edge)
    expected_edges.sort(key=lambda edge: (edge['source'], edge['target'], edge['type']))
    projected.sort(key=lambda node: node['id'])
    for node in projected:
        _require(any(node['id'] in (edge['source'], edge['target']) for edge in expected_edges), 'Unconnected public node')
        if node['kind'] == 'claim': _require(any(edge['source'] == node['id'] and edge['type'] == 'cites' for edge in expected_edges), 'Claim lacks public citation')
    catalog_hash = _hash(_canonical({'policy': policy, 'files': [{'name': name, 'hash': _hash(inputs['catalog:' + name])} for name in CATALOGS]}))
    payload = {'schemaVersion': 1, 'sourceCommit': policy['sourceCommit'], 'catalogHash': catalog_hash,
        'nodes': projected, 'edges': expected_edges, 'limits': list(PUBLIC_LIMITS)}
    _equal(data, {**payload, 'payloadHash': _hash(_canonical(payload))}, 'Independent public projection and identities')
    return {'sourceCommit': data['sourceCommit'], 'payloadHash': data['payloadHash'], 'catalogHash': catalog_hash,
        'counts': {'nodes': len(projected), 'edges': len(expected_edges), 'claims': sum(node['kind'] == 'claim' for node in projected),
            'publicDocuments': len(docs), 'sources': sum(node['kind'] == 'source' for node in projected)}}


def _test_output(category, raw):
    if category == 'exporter_tests':
        output = raw.decode('utf-8')
        names = re.findall(r'^ok [0-9]+ - (.+)$', output, re.M)
        _equal(names, REQUIRED_TEST_NAMES['test/public-research-map.test.mjs'], 'Required exporter test names')
        for key, count in {'tests': len(names), 'pass': len(names), 'fail': 0, 'cancelled': 0, 'skipped': 0, 'todo': 0}.items():
            _equal(re.findall(r'^# ' + key + r' ([0-9]+)$', output, re.M), [str(count)], 'Exporter test totals: ' + key)
    else:
        report = _public_json(raw)
        names = {str(REPO / path): required for path, required in REQUIRED_TEST_NAMES.items() if path.startswith('src/')}
        _require(all(type(report[key]) is int for key in ('numFailedTests', 'numPendingTests', 'numTotalTests', 'numPassedTests')), 'UI test integer totals')
        _require(report['success'] is True and report['numFailedTests'] == 0 and report['numPendingTests'] == 0
            and report['numTotalTests'] == report['numPassedTests'] == sum(map(len, names.values())), 'UI test result totals')
        _equal(sorted(item['name'] for item in report['testResults']), sorted(names), 'Required UI test files')
        for item in report['testResults']:
            _require(item['status'] == 'passed' and all(row['status'] == 'passed' for row in item['assertionResults']), 'Skipped or failed UI test')
            _equal([row['title'] for row in item['assertionResults']], names[item['name']], 'Required named UI controls')


def _successful_output(category, raw, inputs, dataset):
    if category == 'verifier':
        _require(len(raw) <= MAX_REPORT_BYTES, 'Verifier report exceeds bound')
        report = _public_json(raw)
        _keys(report, {'schemaVersion', 'payloadHash', 'sourceCommit', 'counts', 'checks', 'limits'}, 'verifier success report')
        _require(_version(report['schemaVersion']), 'Verifier report version')
        _equal(report['checks'], {key: 'passed' for key in REPORT_CHECKS}, 'All fixed verifier checks')
        _equal(report['limits'], [*PUBLIC_LIMITS, REPORT_LIMIT], 'Verifier limits')
        _require(dataset is not None, 'Verifier success contradicts failed independent public data check')
        for key in ('payloadHash', 'sourceCommit', 'counts'): _equal(report[key], dataset[key], 'Verifier independent ' + key)
        return report['counts']
    if category in {'exporter_tests', 'ui_tests'}: _test_output(category, raw)
    elif category == 'typecheck':
        report = _public_json(raw)
        _keys(report, {'schema_version', 'status', 'entries', 'files', 'next_css_declaration_sha256', 'diagnostics'}, 'focused typecheck output')
        _require(_version(report['schema_version']) and report['status'] == 'passed' and report['diagnostics'] == [], 'Typecheck diagnostics')
        _equal(report['entries'], list(TYPE_ENTRIES), 'Typecheck actual route/data/UI/test entries')
        _require(type(report['files']) is dict and set(TYPE_ENTRIES) <= set(report['files']), 'Typecheck omitted actual inputs')
        _digest(report['next_css_declaration_sha256'])
        for path, digest in report['files'].items():
            _equal(digest, _hash(inputs['dataset'] if path == 'src/data/public-research-map.json' else inputs['file:' + path]), 'Typechecked source/input')
    elif category == 'lint':
        _require(not raw.strip(), 'Passing lint emitted diagnostics')
    elif category == 'build':
        _require(b'/research-map' in raw and (b'Generating static pages' in raw or b'Route (app)' in raw), 'Build output lacks actual map route')
    return None


def assess_prepared_public_map(prepared):
    started = time.monotonic()
    check_prepared_public_map(prepared)
    report = deepcopy(prepared['report'])
    inputs = _inputs(_json(prepared['artifacts']['request']), prepared['artifacts'], _json(prepared['artifacts']['ledger_prefix']))
    manifest = _required_inputs(inputs)
    receipts = _receipts(inputs, manifest)
    checks, errors, dataset, verifier_counts = {}, {}, None, None
    try:
        dataset = _dataset(inputs, manifest)
        checks['independent_public_data'] = True
    except (ValueError, TypeError, KeyError, AttributeError, IndexError, UnicodeError, RecursionError, OverflowError) as error:
        checks['independent_public_data'] = False; errors['independent_public_data'] = str(error)[:500]
    for category, receipt in receipts.items():
        completed = receipt['termination']['kind'] == 'completed' and receipt['returncode'] == 0
        checks[category] = completed
        if completed:
            try:
                counts = _successful_output(category, inputs['stdout:' + category], inputs, dataset)
                if category == 'verifier': verifier_counts = counts
            except (ValueError, TypeError, KeyError, AttributeError, IndexError, UnicodeError, RecursionError, OverflowError) as error:
                checks[category] = False; errors[category] = str(error)[:500]
        else:
            errors[category] = 'Retained process ' + receipt['termination']['kind'] + '; returncode=' + str(receipt['returncode'])
    passed = all(checks.values())
    report.update(status='checked', checks=checks, errors=errors,
        counts=None if dataset is None else dataset['counts'], verifier_counts=verifier_counts,
        dataset_identity=None if dataset is None else {key: dataset[key] for key in ('sourceCommit', 'catalogHash', 'payloadHash')},
        readiness='static_view_prepared' if passed else 'repair_required',
        unknowns={'browser_accessibility': None, 'visual_quality': None, 'human_navigation': None, 'deployment': None,
            'predictive_improvement': None, 'external_execution_witness': None, 'installed_dependency_byte_identity': None},
        processes={category: {'termination': receipt['termination'], 'returncode': receipt['returncode'], 'elapsed_seconds': receipt['elapsed_seconds']} for category, receipt in receipts.items()},
        next_step={'action': 'prepare_evidence_navigation_evaluation' if passed else 'repair_public_research_map_preparation',
            'reason': 'Prepare six fixed textual evidence-navigation cases' if passed else 'Repair the retained static-view failure with changed relevant evidence',
            'scale_change_allowed': False, 'live_effects_allowed': False, 'metric_status': 'Static preparation evidence only; no browser or user-performance result'})
    raw = _canonical(report)
    _require(len(raw) <= MAX_OUTPUT_BYTES and sum(map(len, prepared['artifacts'].values())) + len(raw) <= MAX_BUNDLE_BYTES, 'Map output bound')
    elapsed = time.monotonic() - started
    _require(elapsed <= MAX_SECONDS, 'Map assessment exceeded budget')
    return {'report': report, 'artifacts': {**prepared['artifacts'], 'assessment_report': raw},
        'actual_resources': {'retained_check_elapsed_seconds': elapsed, 'external_program_invocations': 0}}


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, '__module__', None) == __name__ and hasattr(function, '__code__'))
_CONSTANTS = tuple((name, deepcopy(globals()[name])) for name in ('PHASE', 'STAGE', 'CONTRACT_ID', 'SEMANTIC_ACTIONS', 'NEXT_ACTIONS',
    'MAX_SECONDS', 'MAX_REQUEST_BYTES', 'MAX_CONTRACT_BYTES', 'MAX_RECEIPT_BYTES', 'MAX_DATASET_BYTES', 'MAX_REPORT_BYTES', 'MAX_EVENT_BYTES',
    'MAX_LOG_BYTES', 'MAX_MANIFEST_BYTES', 'MAX_OUTPUT_BYTES', 'MAX_PREFIX_BYTES', 'MAX_PREFIX_EVENTS', 'MAX_BUNDLE_BYTES', 'MAX_SOURCE_BYTES',
    'SOURCE_NAMES', 'TRANSITIONS', 'CATALOGS', 'CATEGORIES', 'TYPE_ENTRIES', 'LINT_FILES', 'COMMANDS', 'REQUIRED_FILES', 'REPORT_CHECKS',
    'PUBLIC_LIMITS', 'REPORT_LIMIT', 'KINDS', 'EDGE_KINDS', 'REQUIRED_TEST_NAMES', 'SELECTION', 'CONTRACT', 'REPO'))
