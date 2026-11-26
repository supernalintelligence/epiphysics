"""One shared retained-fixture lifecycle through the existing dispatcher.

The child produces only a provisional report. The reaping parent owns closure.
This module does not implement a process supervisor or execute candidate code.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from . import work_contracts as c, work_adapters, store

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = ((c.__name__, c.IMPLEMENTATION_CODE),
                              (work_adapters.__name__, work_adapters.IMPLEMENTATION_CODE),
                              (store.__name__, store.IMPLEMENTATION_CODE))


def source_hashes():
    from . import decision_assessment, improvement, manifests, assertions
    modules = (c, work_adapters, sys.modules[__name__], decision_assessment, improvement, store, manifests, assertions)
    result = {}
    codes = {module.__name__: module.IMPLEMENTATION_CODE for module in modules}
    for module in modules:
        path = Path(module.__file__)
        raw = module.IMPLEMENTATION_SOURCE
        c.require(not path.is_symlink() and path.read_bytes() == raw, 'Executing work source changed')
        c.require(compile(raw, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize) == module.IMPLEMENTATION_CODE,
                  'Work source/bytecode differs')
        for name, code in module.IMPLEMENTATION_DEPENDENCIES:
            if name in codes:
                c.require(codes[name] is code, 'Work dependency reloaded after consumer import')
        result[path.stem] = store.digest(raw)
    c.require(set(result) == set(c.SOURCE_NAMES), 'Work source registry differs')
    return result


def check_sources(prepared):
    c.require(store.canonical(c.decode(prepared['raw'])) == store.canonical(prepared['bundle']), 'Captured work bundle changed')
    if 'request' in prepared:
        c.require(prepared['request'] == request_for(prepared['bundle'], prepared['raw'], prepared['checkpoint']),
                  'Prepared work request changed')
    c.require(source_hashes() == prepared['bundle']['declaration']['source_hashes'], 'Declared work source pins differ')


def identity(event):
    return None if event is None else {'event_id': event['id'], 'event_hash': event['hash']}


def _events(ledger):
    from . import improvement
    return improvement._checked_events(ledger)


def _owner(events, declaration):
    from . import improvement
    starts = [e for e in events if e['kind'] == 'improvement_started']
    ends = [e for e in events if e['kind'] in improvement.TRANSITIONS]
    finished = {e['body']['run_key'] for e in ends}
    c.require(not any(e['body']['run_key'] not in finished for e in starts), 'Interrupted work exists; no replay')
    previous = ends[-1] if ends else None
    c.require(previous is None or c.MARKER in previous['body']['request']['manifest'],
              'Work fixtures cannot consume a legacy or C12 queue')
    c.require(identity(previous) == declaration['predecessor'], 'Work predecessor differs')
    step = previous['body']['next_step'] if previous else {'id': 'initial', 'state': 'queued',
                                                        'action': 'assess_representation_contracts'}
    c.require(step['id'] == declaration['after_step'] and step['state'] == 'queued', 'Stale work predecessor')
    c.require(not any(e['body'].get('run_key') == declaration['id'] for e in starts + ends),
              'Work identity already used; read retained result without replay')
    return step, previous


def request_for(bundle, raw, checkpoint):
    return {'after_step': bundle['declaration']['after_step'],
            'completed_work': 'Assess retained invented inputs under their declared public measurement policy',
            'manifest': {c.MARKER: c.hash_value(bundle['declaration']),
                         'work:public_policy': c.hash_value(bundle['public_policy']),
                         'work:cohort': c.hash_value(bundle['cases']), 'work:bundle': store.digest(raw),
                         'work:outcomes': c.hash_value(bundle['outcome_manifest']),
                         'work:checkpoint': c.hash_value(checkpoint),
                         **{'work:source:' + k: v for k, v in bundle['declaration']['source_hashes'].items()}}}


def prepare(path, ledger_root):
    from . import decision_assessment
    bundle, raw = c.read(path)
    c.validate(bundle)
    prepared = {'bundle': bundle, 'raw': raw}
    check_sources(prepared)
    c.require(store.instant(bundle['declaration']['expires_at']) > store.instant(store.utc_now()), 'Work declaration expired')
    decision_assessment.prepare_work_contract(bundle)
    ledger = store.Ledger.open_readonly(ledger_root)
    try:
        events = _events(ledger)
        step, previous = _owner(events, bundle['declaration'])
        prepared.update(checkpoint=identity(events[-1] if events else None), step=step,
                        previous_measurement=(previous['body'].get('work_contract', {}).get('measurement_identity')
                                              if previous else None))
        prepared['request'] = request_for(bundle, raw, prepared['checkpoint'])
    finally:
        ledger.close()
    return prepared


def alive(prepared, deadline):
    c.require(time.monotonic() < deadline and
              store.instant(store.utc_now()) < store.instant(prepared['bundle']['declaration']['expires_at']),
              'Original work deadline expired')


def child(ledger_root, path):
    from . import decision_assessment
    prepared = prepare(path, ledger_root)
    declaration = prepared['bundle']['declaration']; request = prepared['request']
    dispatch_id = os.environ.get('EPIPHYSICS_DISPATCH_ID')
    c.require(type(dispatch_id) is str and len(dispatch_id) == 32 and all(ch in '0123456789abcdef' for ch in dispatch_id),
              'Work child requires its supervising dispatcher')
    c.require(os.environ.get('EPIPHYSICS_EXPECTED_REQUEST_SHA256') == c.hash_value(request), 'Parent work request differs')
    ledger = store.Ledger(ledger_root)
    try:
        def validate(_):
            check_sources(prepared)
            c.require(store.instant(store.utc_now()) < store.instant(declaration['expires_at']), 'Work declaration expired')
            events = _events(ledger)
            _owner(events, declaration)
            c.require(identity(events[-1] if events else None) == prepared['checkpoint'], 'Work head changed before claim')
        ledger.append('improvement_started', {'run_key': declaration['id'], 'request': request,
                      'claimed_step': prepared['step'], 'worker': {'dispatch_id': dispatch_id, 'pid': os.getpid()}},
                      'improvement:claim:' + store.digest(declaration['after_step'].encode()), exclusive=True, validate=validate)
        ledger.capture('improvement-input:work:bundle', prepared['raw'], media_type='application/json',
                       event_id='improvement:' + declaration['id'] + ':input:work:bundle')
        assessed = decision_assessment.assess_work_contract(prepared['bundle'])
        check_sources(prepared)
        return {'schema_version': 1, 'result': 'provisional', 'run_key': declaration['id'],
                'request': request, 'measurements': assessed, 'accepted_measurements': None}
    finally:
        ledger.close()


def _claim(ledger, prepared, dispatch_id, pid):
    from . import improvement
    events = _events(ledger); run = prepared['bundle']['declaration']['id']
    claims = [e for e in events if e['kind'] == 'improvement_started' and e['body']['run_key'] == run]
    c.require(len(claims) == 1, 'Missing or ambiguous owned work claim')
    claim = claims[0]
    c.require(claim['body']['worker'] == {'dispatch_id': dispatch_id, 'pid': pid} and
              claim['body']['request'] == prepared['request'] and claim['body']['claimed_step'] == prepared['step'],
              'Work claim ownership/request differs')
    before = [e for e in events if e['seq'] < claim['seq']]
    c.require(identity(before[-1] if before else None) == prepared['checkpoint'], 'Work preclaim checkpoint differs')
    c.require(not any(e['kind'] in improvement.TRANSITIONS and e['body']['run_key'] == run for e in events),
              'Work already finished')
    suffix = [e for e in events if e['seq'] > claim['seq']]
    c.require(all(e['kind'] == 'observation' and e['id'].startswith('improvement:' + run + ':input:work:') for e in suffix),
              'Unrelated write after work claim')
    return events, claim


def recovery_guard(prepared, deadline, ledger_root, dispatch_id, pid):
    """Extra locked guards for the existing already-reaped-worker recovery helper."""
    check_sources(prepared); alive(prepared, deadline)
    reader = store.Ledger.open_readonly(ledger_root)
    try:
        events, _ = _claim(reader, prepared, dispatch_id, pid)
        expected = identity(events[-1])
    finally:
        reader.close()
    def validate(ledger):
        check_sources(prepared); alive(prepared, deadline)
        current, _ = _claim(ledger, prepared, dispatch_id, pid)
        c.require(identity(current[-1]) == expected, 'Work recovery head changed')
    return validate


def finish(ledger_root, prepared, dispatch_id, process_receipt, raw_output, deadline):
    """Parent-only acceptance after observed exit, with one locked transition."""
    from . import decision_assessment
    alive(prepared, deadline); check_sources(prepared)
    c.require(process_receipt['dispatch_id'] == dispatch_id and process_receipt['returncode'] == 0
              and process_receipt['termination'] is None and process_receipt['output_sha256'] == store.digest(raw_output),
              'No successful independently observed work process')
    report = c.decode(raw_output)
    expected = {'schema_version': 1, 'result': 'provisional', 'run_key': prepared['bundle']['declaration']['id'],
                'request': prepared['request'], 'measurements': decision_assessment.assess_work_contract(prepared['bundle']),
                'accepted_measurements': None}
    c.require(store.canonical(report) == store.canonical(expected), 'Provisional work report differs from retained inputs')
    ledger = store.Ledger(ledger_root)
    try:
        events, claim = _claim(ledger, prepared, dispatch_id, process_receipt['pid'])
        c.require(store.instant(process_receipt['started_at']) <= store.instant(claim['recorded_at'])
                  <= store.instant(process_receipt['ended_at']), 'Claim outside supervised work interval')
        run = report['run_key']
        original = ledger.get('improvement:' + run + ':input:work:bundle', 'observation')
        blob = ledger.root / 'blobs' / original['body']['content_hash']
        with blob.open('rb') as stream:
            retained = stream.read(len(prepared['raw']) + 1)
        c.require(not blob.is_symlink() and original['body']['content_hash'] == store.digest(prepared['raw'])
                  and retained == prepared['raw'], 'Original work input changed')
        captures = {}
        for role, raw in [('report', raw_output), ('process', store.canonical(process_receipt).encode())]:
            alive(prepared, deadline)
            event = ledger.capture('improvement-input:work:' + role, raw, media_type='application/json',
                                   event_id='improvement:' + run + ':input:work:' + role)
            captures[role] = identity(event)
        checkpoint = identity(ledger.events()[-1])
        measurements = report['measurements']; measured = measurements['measurement_identity']
        result = {'run_key': run, 'request': prepared['request'], 'result': 'assessed',
                  'work_contract': {'version': 1, 'adapter': prepared['bundle']['declaration']['adapter'],
                                    'measurement_identity': measured, 'stage': 'invented_fixture',
                                    'method_id': prepared['bundle']['declaration']['method_id'],
                                    'outcome_manifest_hash': prepared['bundle']['declaration']['outcome_manifest_hash'],
                                    'source_hashes': prepared['bundle']['declaration']['source_hashes']},
                  'accepted_measurements': measurements, 'process_evidence': captures,
                  'comparison': c.compare(prepared['previous_measurement'], measured),
                  'next_step': {'id': run + ':next', 'state': 'queued',
                                'action': 'review_work_measurements' if measurements['passed'] else 'diagnose_work_conformance',
                                'scale_change_allowed': False, 'estimated_cost': None, 'estimated_success_probability': None}}
        frozen = store.canonical(result)
        def validate(_):
            alive(prepared, deadline); check_sources(prepared)
            current, _ = _claim(ledger, prepared, dispatch_id, process_receipt['pid'])
            c.require(identity(current[-1]) == checkpoint and store.canonical(result) == frozen, 'Work closure head/report changed')
            c.require(decision_assessment.assess_work_contract(prepared['bundle']) == measurements, 'Work measurement changed')
            alive(prepared, deadline)
        ledger.db.execute('PRAGMA busy_timeout=0')
        with ledger.atomic_write():
            event = ledger.append('improvement_completed', result, 'improvement:' + run + ':complete',
                                  exclusive=True, validate=validate)
            alive(prepared, deadline)
        # Commit I/O can outlast the precommit check. A durable record cannot
        # be rolled back here; the parent must report late publication honestly.
        alive(prepared, deadline)
        return result
    finally:
        ledger.close()
