"""Small owned retained-publication fixtures; never execute frontend programs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import public_map_assessment as mapping
from epiphysics import dated_delivery as delivery
from epiphysics.store import Ledger


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value): return hashlib.sha256(value).hexdigest()
def identity(event): return {'event_id': event['id'], 'event_hash': event['hash']}
def checkpoint(event): return {'seq': event['seq'], **identity(event)}


def accepted_origin(ledger):
    """Historical C10-shaped metadata; no C10 checker or original task is run."""
    declared = {'request': digest(b'owned historical request')}
    declared.update({'code:epiphysics.' + name[:-3]: digest(('owned older ' + name).encode()) for name in delivery.SOURCE_NAMES})
    manifest = {'decision-input:' + key: value for key, value in declared.items()}
    report = {'schema_version': 1, 'status': 'checked', 'phase': delivery.CHECK,
        'stage': delivery.PHASES[delivery.CHECK], 'contract_id': delivery.CONTRACT_ID,
        'assessment_identity': {'schema_version': 1, 'hash': digest(raw(declared))},
        'input_hashes': {'request': declared['request']},
        'source_hashes': {name: declared['code:epiphysics.' + name[:-3]] for name in delivery.SOURCE_NAMES},
        'checks': {'owned_historical_control': True}, 'next_step': {'action': 'prepare_public_research_map_view'}}
    assessment = {'input_manifest': manifest, 'decision_assessment_hash': report['assessment_identity']['hash']}
    assessment['hash'] = digest(raw(assessment))
    return ledger.append('improvement_completed', {'run_key': 'owned-c10', 'result': 'assessed',
        'request': {'manifest': manifest}, 'assessment_identity': assessment, 'report': {'decision_pilot': report},
        'next_step': {'id': 'owned-c10:next', 'state': 'queued', 'action': 'prepare_public_research_map_view'}}, 'improvement:owned-c10:complete')


def fixture_inputs(statement='An owned claim with a retained public citation.'):
    source = {'id': 'source', 'kind': 'source', 'title': 'Owned source', 'url': 'https://example.org/paper',
        'date': '2020', 'date_type': 'publication', 'reviewed_on': '2026-11-26', 'bibliographic_only': True,
        'claim_supported': 'Owned fixture support only', 'limitation': 'Not external execution evidence'}
    claim = {'id': 'claim', 'kind': 'claim', 'title': 'Owned claim', 'statement': statement, 'status': 'hypothesis', 'basis': 'inferred'}
    doc = {'id': 'document', 'kind': 'document', 'title': 'Owned document', 'repo_path': 'docs/research/owned-map.md'}
    edges = [{'source': 'claim', 'target': 'document', 'type': 'cites'}, {'source': 'claim', 'target': 'source', 'type': 'cites'}]
    policy = {'schemaVersion': 1, 'sourceCommit': '1' * 40, 'catalogFiles': list(mapping.CATALOGS),
        'nodeIds': ['claim', 'document', 'source'], 'documents': {'document': {'repoPath': doc['repo_path'], 'href': '/research/owned-map'}}}
    inputs = {'policy': raw(policy), 'selection': raw(mapping.SELECTION),
        'catalog:registry.json': raw({'schema_version': 1, 'nodes': [claim, doc], 'edges': edges}),
        'catalog:sources-control.json': raw([source]), 'catalog:sources-representation.json': b'[]', 'catalog:sources-retrieval.json': b'[]',
        'file:' + doc['repo_path']: b'---\ntitle: Owned document\ndraft: false\n---\nOwned content.\n'}
    inputs.update({'file:' + path: (mapping.REPO / path).read_bytes() for path in mapping.REQUIRED_FILES})
    nodes = [claim, {'id': 'document', 'kind': 'document', 'title': doc['title'], 'href': '/research/owned-map',
        'contentHash': digest(inputs['file:' + doc['repo_path']]), 'commit': policy['sourceCommit']},
        {'id': 'source', 'kind': 'source', 'title': source['title'], 'href': source['url'], 'date': source['date'],
         'dateType': source['date_type'], 'reviewedOn': source['reviewed_on'], 'bibliographicOnly': True, 'limitations': [source['limitation']]}]
    payload = {'schemaVersion': 1, 'sourceCommit': policy['sourceCommit'],
        'catalogHash': digest(raw({'policy': policy, 'files': [{'name': name, 'hash': digest(inputs['catalog:' + name])} for name in mapping.CATALOGS]})),
        'nodes': nodes, 'edges': edges, 'limits': list(mapping.PUBLIC_LIMITS)}
    inputs['dataset'] = raw({**payload, 'payloadHash': digest(raw(payload))})
    manifest = {'schema_version': 1, 'source_commit': policy['sourceCommit'], 'ui_commit': '2' * 40,
        'files': {role[5:]: {'sha256': digest(content), 'bytes': len(content)} for role, content in inputs.items() if role.startswith('file:')},
        'executables': {name: {'path': '/owned/bin/' + name, 'sha256': digest(name.encode()), 'version': 'owned-fixture'} for name in ('node', 'npm')}}
    inputs['manifest'] = raw(manifest)
    counts = {'nodes': 3, 'edges': 2, 'claims': 1, 'publicDocuments': 1, 'sources': 1}
    inputs['stdout:verifier'] = raw({'schemaVersion': 1, 'payloadHash': digest(raw(payload)), 'sourceCommit': policy['sourceCommit'], 'counts': counts,
        'checks': {name: 'passed' for name in mapping.REPORT_CHECKS}, 'limits': [*mapping.PUBLIC_LIMITS, mapping.REPORT_LIMIT]})
    names = mapping.REQUIRED_TEST_NAMES['test/public-research-map.test.mjs']
    inputs['stdout:exporter_tests'] = ('TAP version 13\n' + '\n'.join('ok ' + str(index) + ' - ' + name for index, name in enumerate(names, 1))
        + '\n' + '\n'.join('# ' + name + ' ' + str(value) for name, value in {'tests': 17, 'pass': 17, 'fail': 0, 'cancelled': 0, 'skipped': 0, 'todo': 0}.items()) + '\n').encode()
    inputs['stdout:ui_tests'] = raw({'success': True, 'numFailedTests': 0, 'numPendingTests': 0, 'numTotalTests': 13, 'numPassedTests': 13,
        'testResults': [{'name': str(mapping.REPO / path), 'status': 'passed',
            'assertionResults': [{'title': name, 'status': 'passed'} for name in names]} for path, names in mapping.REQUIRED_TEST_NAMES.items() if path.startswith('src/')]})
    inputs['stdout:typecheck'] = raw({'schema_version': 1, 'status': 'passed', 'entries': list(mapping.TYPE_ENTRIES),
        'files': {path: digest(inputs['dataset'] if path == 'src/data/public-research-map.json' else inputs['file:' + path]) for path in mapping.TYPE_ENTRIES},
        'next_css_declaration_sha256': digest(b'owned installed declaration'), 'diagnostics': []})
    inputs['stdout:lint'] = b''
    inputs['stdout:build'] = b'Generating static pages\nRoute (app)\n /research-map\n'
    inputs.update({'stderr:' + category: b'' for category in mapping.CATEGORIES})
    return refresh_receipts(inputs)


def refresh_receipts(inputs, changes=None):
    manifest = json.loads(inputs['manifest'])
    identities = {role: digest(content) for role, content in inputs.items() if not role.startswith(('receipt:', 'stdout:', 'stderr:'))}
    generated = {'sha256': digest(b'owned generated content'), 'bytes': 23}
    for category in mapping.CATEGORIES:
        executable = manifest['executables'][mapping.COMMANDS[category][0]]
        value = {'schema_version': 1, 'category': category, 'command': [executable['path'], *mapping.COMMANDS[category][1:]],
            'cwd': str(mapping.REPO), 'executable': executable, 'started_at': '2000-01-01T00:00:02Z' if category == 'verifier' else '2000-01-01T00:00:00Z',
            'ended_at': '2000-01-01T00:00:03Z' if category == 'verifier' else '2000-01-01T00:00:01Z', 'elapsed_seconds': .01,
            'returncode': 0, 'termination': {'kind': 'completed', 'stream': None}, 'inputs_before': identities, 'inputs_after': identities,
            'outputs': {'public_content': generated} if category == 'build' else {},
            'generated_inputs': {'public_content': generated} if category == 'verifier' else {}}
        for name in ('stdout', 'stderr'):
            content = inputs[name + ':' + category]
            value[name] = {'bytes': len(content), 'sha256': digest(content), 'complete': True, 'observed_bytes': len(content), 'full_sha256': digest(content)}
        if changes and category in changes: value.update(changes[category])
        inputs['receipt:' + category] = raw(value)
    return inputs


def rebind_public_identities(inputs):
    """Recompute all declared identities, so controls target semantic checks."""
    manifest, policy, data = (json.loads(inputs[name]) for name in ('manifest', 'policy', 'dataset'))
    manifest['source_commit'] = policy['sourceCommit']
    for path in manifest['files']:
        manifest['files'][path] = {'sha256': digest(inputs['file:' + path]), 'bytes': len(inputs['file:' + path])}
    data['sourceCommit'] = policy['sourceCommit']
    for node in data['nodes']:
        if node['kind'] == 'document':
            node['commit'] = policy['sourceCommit']
            node['contentHash'] = digest(inputs['file:' + policy['documents'][node['id']]['repoPath']])
    data['catalogHash'] = digest(raw({'policy': policy, 'files': [{'name': name, 'hash': digest(inputs['catalog:' + name])} for name in mapping.CATALOGS]}))
    data['payloadHash'] = digest(raw({key: value for key, value in data.items() if key != 'payloadHash'}))
    inputs['dataset'], inputs['manifest'] = raw(data), raw(manifest)
    report = json.loads(inputs['stdout:verifier']); report.update(payloadHash=data['payloadHash'], sourceCommit=data['sourceCommit'])
    inputs['stdout:verifier'] = raw(report)
    report = json.loads(inputs['stdout:typecheck']); report['files']['src/data/public-research-map.json'] = digest(inputs['dataset'])
    inputs['stdout:typecheck'] = raw(report)
    return refresh_receipts(inputs)


def bind_inputs(study, inputs=None, parent=None, name=None):
    parent = parent or study['origin']
    inputs = inputs or study['inputs']
    name = name or 'owned-map-' + str(len(study['ledger'].events()))
    observations = {}
    for index, (role, content) in enumerate(inputs.items()):
        event = study['ledger'].capture(mapping._scope(name) + role, content, event_id=name + ':input:' + str(index))
        observations[role] = event['id']
    packet = {'schema_version': 1, 'phase': mapping.PHASE, 'observations': observations}
    request = {'schema_version': 1, 'phase': mapping.PHASE, 'study_id': name,
        'origin': {'step_id': parent['body']['next_step']['id']}, 'ledger_path': str(study['ledger'].root),
        'evidence_origin': identity(study['origin']), 'queue_parent': identity(parent), 'evidence_checkpoint': checkpoint(event),
        'paths': {'contract': str(study['directory'] / 'contract.json'), 'packet': str(study['directory'] / 'packet.json')}}
    Path(request['paths']['contract']).write_bytes(raw(mapping.CONTRACT))
    Path(request['paths']['packet']).write_bytes(raw(packet))
    study['request_path'].write_bytes(raw(request))
    study.update(inputs=inputs, request=request, packet=packet, parent=parent)
    return study


def make_study(directory, inputs=None):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(directory / 'ledger')
    study = {'directory': directory, 'ledger': ledger, 'origin': accepted_origin(ledger), 'request_path': directory / 'request.json',
        'inputs': inputs or fixture_inputs()}
    return bind_inputs(study)


class PublicMapAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.study = make_study(self.temp.name); self.addCleanup(self.study['ledger'].close)

    def assess(self): return mapping.assess_prepared_public_map(mapping.prepare_public_map(self.study['request_path']))

    def rebind(self, inputs): return bind_inputs(self.study, inputs)

    def test_valid_retained_only_comparison_and_deterministic_output(self):
        from test_decision_diagnosis import calls_named, FORBIDDEN_CALLS
        with calls_named(FORBIDDEN_CALLS | {'verify_inventory', '_diagnose', 'Popen', 'run', 'system'}) as called:
            prepared = mapping.prepare_public_map(self.study['request_path'])
            first = mapping.assess_prepared_public_map(prepared)
            second = mapping.assess_prepared_public_map(prepared)
        self.assertEqual(called, [])
        self.assertEqual(first['report'], second['report'])
        self.assertTrue(all(first['report']['checks'].values()))
        self.assertEqual(first['report']['counts']['claims'], 1)
        self.assertEqual(first['report']['next_step']['action'], 'prepare_evidence_navigation_evaluation')
        self.assertTrue(all(value is None for value in first['report']['unknowns'].values()))
        self.assertLess(sum(map(len, first['artifacts'].values())), mapping.MAX_BUNDLE_BYTES)

    def test_malformed_dataset_is_checked_negative_with_null_counts(self):
        inputs = fixture_inputs(); inputs['dataset'] = b'{"a":1,"a":2}'
        inputs['stdout:verifier'] = b''; inputs['stderr:verifier'] = b'Invalid dataset\n'
        refresh_receipts(inputs, {'verifier': {'returncode': 1}}); self.rebind(inputs)
        report = self.assess()['report']
        self.assertIsNone(report['counts']); self.assertIsNone(report['verifier_counts'])
        self.assertFalse(report['checks']['independent_public_data']); self.assertFalse(report['checks']['verifier'])
        self.assertEqual(report['next_step']['action'], 'repair_public_research_map_preparation')

    def test_valid_process_failure_needs_no_success_json(self):
        for termination in ({'kind': 'completed', 'stream': None}, {'kind': 'timeout', 'stream': None}):
            with self.subTest(termination=termination):
                inputs = fixture_inputs(); inputs['stdout:verifier'] = b''
                refresh_receipts(inputs, {'verifier': {'returncode': 1, 'termination': termination}}); self.rebind(inputs)
                report = self.assess()['report']
                self.assertFalse(report['checks']['verifier']); self.assertIsNone(report['verifier_counts'])
                self.assertTrue(report['checks']['independent_public_data'])

    def test_failed_build_without_generated_file_retains_real_verifier_failure(self):
        inputs = fixture_inputs(); inputs['stdout:build'] = b''; inputs['stderr:build'] = b'Owned build failed\n'
        inputs['stdout:verifier'] = b''; inputs['stderr:verifier'] = b'Missing generated content\n'
        refresh_receipts(inputs, {'build': {'returncode': 1, 'outputs': {'public_content': None}},
            'verifier': {'returncode': 1, 'generated_inputs': {'public_content': None}}})
        self.rebind(inputs); report = self.assess()['report']
        self.assertFalse(report['checks']['build']); self.assertFalse(report['checks']['verifier'])
        self.assertIsNone(report['verifier_counts'])
        self.assertEqual(report['next_step']['action'], 'repair_public_research_map_preparation')
        receipt = json.loads(inputs['receipt:verifier']); receipt['returncode'] = 0
        inputs['receipt:verifier'] = raw(receipt); self.rebind(inputs)
        with self.assertRaisesRegex(mapping.PreparationError, 'without generated content'): mapping.prepare_public_map(self.study['request_path'])

    def test_real_overflow_prefix_is_negative_but_empty_assertion_refused(self):
        inputs = fixture_inputs(); inputs['stdout:verifier'] = b'x' * mapping.MAX_LOG_BYTES
        refresh_receipts(inputs)
        receipt = json.loads(inputs['receipt:verifier'])
        receipt.update(returncode=-15, termination={'kind': 'output_limit', 'stream': 'stdout'})
        receipt['stdout'].update(complete=False, observed_bytes=mapping.MAX_LOG_BYTES + 1, full_sha256=None)
        inputs['receipt:verifier'] = raw(receipt); self.rebind(inputs)
        self.assertFalse(self.assess()['report']['checks']['verifier'])
        inputs['stdout:verifier'] = b''; receipt['stdout'].update(bytes=0, sha256=digest(b''))
        inputs['receipt:verifier'] = raw(receipt); self.rebind(inputs)
        with self.assertRaisesRegex(mapping.PreparationError, 'actual bounded overflow prefix'): mapping.prepare_public_map(self.study['request_path'])

    def test_false_report_counts_and_validation_subsets_are_failed_checks(self):
        for category in ('verifier', 'exporter_tests', 'ui_tests', 'typecheck'):
            with self.subTest(category=category):
                inputs = fixture_inputs()
                if category == 'exporter_tests': inputs['stdout:' + category] = b'ok 1 - unrelated test\n'
                else:
                    report = json.loads(inputs['stdout:' + category])
                    if category == 'verifier': report['counts']['claims'] = 999
                    elif category == 'ui_tests': report['numPendingTests'] = 1
                    else: report['entries'] = ['src/components/research-map/model.ts']
                    inputs['stdout:' + category] = raw(report)
                refresh_receipts(inputs); self.rebind(inputs)
                self.assertFalse(self.assess()['report']['checks'][category])

    def test_independent_dataset_rejects_extra_fields_membership_routes_direction_and_hash(self):
        def extra(data): data['nodes'][0]['private_note'] = 'hidden'
        def member(data): data['nodes'][0]['id'] = 'unapproved'
        def route(data): data['nodes'][1]['href'] = '/private/file'
        def reverse(data): data['edges'][0]['source'], data['edges'][0]['target'] = data['edges'][0]['target'], data['edges'][0]['source']
        def catalog(data): data['catalogHash'] = '0' * 64
        for mutate in (extra, member, route, reverse, catalog):
            with self.subTest(mutate=mutate.__name__):
                inputs = fixture_inputs(); data = json.loads(inputs['dataset']); mutate(data)
                data['payloadHash'] = digest(raw({key: value for key, value in data.items() if key != 'payloadHash'}))
                inputs['dataset'] = raw(data); refresh_receipts(inputs); self.rebind(inputs)
                self.assertFalse(self.assess()['report']['checks']['independent_public_data'])

    def test_receipt_tampering_or_unregistered_command_refuses_preparation(self):
        for field, value in (('schema_version', True), ('command', ['/owned/bin/node', 'unregistered.mjs']), ('inputs_after', {})):
            inputs = fixture_inputs(); receipt = json.loads(inputs['receipt:verifier']); receipt[field] = value
            inputs['receipt:verifier'] = raw(receipt); self.rebind(inputs)
            with self.subTest(field=field), self.assertRaises(mapping.PreparationError): mapping.prepare_public_map(self.study['request_path'])

    def test_build_output_and_final_verifier_order_are_bound(self):
        for mutation in ('identity', 'time'):
            inputs = fixture_inputs(); receipt = json.loads(inputs['receipt:verifier'])
            if mutation == 'identity': receipt['generated_inputs']['public_content']['sha256'] = '0' * 64
            else: receipt['started_at'] = '1999-01-01T00:00:00Z'
            inputs['receipt:verifier'] = raw(receipt); self.rebind(inputs)
            with self.subTest(mutation=mutation), self.assertRaises(mapping.PreparationError): mapping.prepare_public_map(self.study['request_path'])

    def test_prepared_inputs_survive_deleted_request_but_reject_mutation(self):
        prepared = mapping.prepare_public_map(self.study['request_path'])
        self.study['request_path'].unlink()
        mapping.check_prepared_public_map(prepared)
        changed = deepcopy(prepared); changed['artifacts']['packet'] += b' '
        with self.assertRaisesRegex(ValueError, 'digest'): mapping.check_prepared_public_map(changed)

    def test_authoritative_checkpoint_parent_and_omitted_later_capture(self):
        prepared = mapping.prepare_public_map(self.study['request_path'])
        ledger = self.study['ledger']; step = self.study['request']['origin']['step_id']
        mapping.validate_lineage(prepared, ledger.events(), step)
        ledger.capture(mapping._scope(self.study['request']['study_id']) + 'stderr:later', b'later', event_id='owned-later')
        with self.assertRaisesRegex(ValueError, 'Later scoped'): mapping.validate_lineage(prepared, ledger.events(), step)
        wrong = deepcopy(prepared); wrong['report']['evidence_origin']['event_hash'] = '0' * 64
        with self.assertRaises(ValueError): mapping.check_prepared_public_map(wrong)

    def test_source_and_selection_mismatch_refuse_before_computation(self):
        inputs = fixture_inputs(); selection = json.loads(inputs['selection']); selection['commands']['lint'] = ['node', 'other.js']
        inputs['selection'] = raw(selection); refresh_receipts(inputs); self.rebind(inputs)
        with self.assertRaisesRegex(mapping.PreparationError, 'validation selections'): mapping.prepare_public_map(self.study['request_path'])
        inputs = fixture_inputs(); key = 'file:src/components/research-map/model.ts'; inputs[key] += b'\n'
        manifest = json.loads(inputs['manifest']); manifest['files'][key[5:]] = {'sha256': digest(inputs[key]), 'bytes': len(inputs[key])}
        inputs['manifest'] = raw(manifest); refresh_receipts(inputs); self.rebind(inputs)
        with self.assertRaisesRegex(mapping.PreparationError, 'Current fixed'): mapping.prepare_public_map(self.study['request_path'])

    def test_rebound_private_document_is_an_artifact_failure(self):
        inputs = fixture_inputs(); inputs['file:docs/research/owned-map.md'] = b'---\ntitle: Owned draft\ndraft: true\nprivate: true\n---\nPrivate fixture.\n'
        rebind_public_identities(inputs); self.rebind(inputs)
        report = self.assess()['report']
        self.assertFalse(report['checks']['independent_public_data']); self.assertFalse(report['checks']['verifier'])
        self.assertIsNone(report['counts'])
        self.assertEqual(report['next_step']['action'], 'repair_public_research_map_preparation')

    def test_publication_metadata_scalar_and_frontmatter_boundaries(self):
        mapping._published_document(b'---\ntitle: "# A literal title"\ndraft: false\n---\nBody')
        mapping._published_document(b'---\ntitle: "Owned public title"\ndraft: false # allowed\nprivate: false\npublished: true\nvisibility: public\nauthor:\n  name: Owned\n---\nBody')
        for metadata in ('draft: true', 'private: true', 'published: false', 'visibility: private', 'status: internal',
                         'status: draft', 'status: private', 'draft: "false"', "private: 'false'", 'published: "true"',
                         'draft: null', 'private:', 'title: false', 'title: 123', 'title: ""', 'title: # no title value', 'title:   # comment', 'title: "   "',
                         'draft: false\ndraft: true', '"private": true', '<<: *private', 'title: *hidden',
                         'draft: false\n  other: value'):
            text = ('---\n' + ('' if metadata.startswith('title:') else 'title: Owned\n') + metadata + '\n---\nBody').encode()
            with self.subTest(metadata=metadata), self.assertRaises((ValueError, UnicodeError)): mapping._published_document(text)
        for content in (b'No frontmatter', b'---\ndraft: false\n---\nBody', b'---\ntitle: Missing close', b'---json\n{"title":"Owned","private":true}\n---'):
            with self.subTest(content=content), self.assertRaises(ValueError): mapping._published_document(content)

    def test_provenance_labels_and_derived_hashes_do_not_reopen_failed_check(self):
        from test_dated_delivery import append_completion
        inputs = fixture_inputs(); refresh_receipts(inputs, {'build': {'returncode': 1}}); self.rebind(inputs)
        prepared = mapping.prepare_public_map(self.study['request_path']); measured = mapping.assess_prepared_public_map(prepared)
        parent = append_completion(self.study['ledger'], prepared, measured, 'owned-map-failed')
        changed = fixture_inputs(); policy = json.loads(changed['policy']); policy['sourceCommit'] = '3' * 40
        changed['policy'] = raw(policy); rebind_public_identities(changed)
        manifest = json.loads(changed['manifest']); manifest['ui_commit'] = '4' * 40; changed['manifest'] = raw(manifest)
        refresh_receipts(changed, {'build': {'returncode': 1}}); bind_inputs(self.study, changed, parent)
        self.assertNotEqual(changed['dataset'], inputs['dataset']); self.assertNotEqual(changed['policy'], inputs['policy'])
        self.assertTrue(all(changed[name] == value for name, value in inputs.items() if name.startswith(('file:', 'catalog:')) or name == 'selection'))
        before = len(self.study['ledger'].events())
        with self.assertRaisesRegex(mapping.PreparationError, 'Unchanged failed'): mapping.prepare_public_map(self.study['request_path'])
        self.assertEqual(len(self.study['ledger'].events()), before)
        bind_inputs(self.study, fixture_inputs('Owned direct content repair.'), parent)
        repaired = self.assess()['report']
        self.assertEqual(repaired['next_step']['action'], 'prepare_evidence_navigation_evaluation')

    def test_invalid_derived_hash_can_be_repaired_without_changing_content(self):
        from test_dated_delivery import append_completion
        inputs = fixture_inputs(); data = json.loads(inputs['dataset']); data['payloadHash'] = '0' * 64
        inputs['dataset'] = raw(data)
        typecheck = json.loads(inputs['stdout:typecheck']); typecheck['files']['src/data/public-research-map.json'] = digest(inputs['dataset'])
        inputs['stdout:typecheck'] = raw(typecheck); refresh_receipts(inputs); self.rebind(inputs)
        prepared = mapping.prepare_public_map(self.study['request_path']); measured = mapping.assess_prepared_public_map(prepared)
        self.assertFalse(measured['report']['checks']['independent_public_data'])
        parent = append_completion(self.study['ledger'], prepared, measured, 'owned-map-bad-hash')
        fixed = fixture_inputs(); bind_inputs(self.study, fixed, parent)
        report = self.assess()['report']
        self.assertTrue(all(report['checks'].values()))
        self.assertEqual(report['next_step']['action'], 'prepare_evidence_navigation_evaluation')
        self.assertNotEqual(report['relevant_input_hash'], measured['report']['relevant_input_hash'])
        self.assertTrue(all(inputs[name] == fixed[name] for name in inputs if name.startswith(('file:', 'catalog:')) or name in {'selection', 'policy'}))

    def test_request_symlink_and_role_bound_refuse(self):
        linked = self.study['directory'] / 'linked.json'; linked.symlink_to(self.study['request_path'])
        with self.assertRaises(mapping.PreparationError): mapping.prepare_public_map(linked)
        inputs = fixture_inputs(); inputs['dataset'] = b' ' * (mapping.MAX_DATASET_BYTES + 1); refresh_receipts(inputs); self.rebind(inputs)
        with self.assertRaisesRegex(mapping.PreparationError, 'role cap'): mapping.prepare_public_map(self.study['request_path'])


if __name__ == '__main__': unittest.main()
