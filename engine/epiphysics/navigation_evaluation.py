"""Separate retained-only scoring. This module never runs a candidate or reads a ledger."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import sys
import time
from . import navigation_contracts as c

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = ((c.__name__, c.IMPLEMENTATION_CODE),)
INTERPRETATION_FIELDS = {'source': 'source_interpretation', 'qualification': 'qualification_interpretation', 'proposal': 'proposal_interpretation'}
_SELF = (Path(__file__), IMPLEMENTATION_SOURCE, IMPLEMENTATION_CODE)


def loaded_source():
    from . import navigation_runner as runner
    path, raw, code = _SELF
    c.require(IMPLEMENTATION_SOURCE == raw and IMPLEMENTATION_CODE is code
        and runner.read(path, c.MAX_SOURCE_BYTES) == raw
        and compile(raw, str(path), 'exec', dont_inherit=True, optimize=sys.flags.optimize) == code, 'Executing evaluator source changed')
    for name, function, original in _FUNCTION_CODES:
        c.require(globals().get(name) is function and function.__code__ is original, 'Evaluator callable changed')
    for name, value in _CONSTANTS:
        c.require(type(globals().get(name)) is type(value) and globals().get(name) == value, 'Evaluator constant changed')


def tokens(items):
    return {c.canonical(item) for item in items}


def ref_tokens(refs):
    return {(ref['node_id'], ref['pointer']) for ref in refs}


def reference_integrity(refs, nodes):
    seen = set()
    for ref in refs:
        c.keys(ref, {'node_id', 'pointer', 'quote'}, 'response reference')
        c.require(ref['node_id'] in nodes and (ref['node_id'], ref['pointer']) not in seen, 'Missing or duplicate referenced field')
        seen.add((ref['node_id'], ref['pointer']))
        field = c.pointer_value(nodes[ref['node_id']], ref['pointer'])
        quote = ref['quote']
        c.require(quote is None or type(field) is str and type(quote) is str and quote and quote in field, 'Quote is not exact source text')
    return True


def expected_claim(case, nodes):
    anchor = next(node for node in nodes.values() if node['kind'] == 'claim' and node['title'] == case['anchor_title'])
    return {'node_id': anchor['id'], 'status': anchor['status'], 'basis': anchor['basis']}


def target_integrity(labels, nodes):
    seen = set()
    for label in labels:
        c.require(label['node_id'] in nodes and label['node_id'] not in seen, 'Missing or duplicate target label')
        seen.add(label['node_id']); node = nodes[label['node_id']]
        c.require(label == {'node_id': node['id'], 'kind': node['kind'], 'status': node.get('status'), 'basis': node.get('basis')}, 'Target label contradicts map')
    return True


def validate_key(key, cohort, public_map):
    c.keys(key, {'schema_version', 'contract_id', 'map_payload_hash', 'cohort_hash', 'cases'}, 'private scoring key')
    c.require(type(key['schema_version']) is int and key['schema_version'] == 1 and key['contract_id'] == c.CONTRACT_ID
        and key['map_payload_hash'] == public_map['payloadHash'] and key['cohort_hash'] == c.digest(c.canonical(cohort)), 'Key/cohort/map identity differs')
    c.keys(key['cases'], {case['case_id'] for case in cohort['cases']}, 'key cases')
    nodes = {node['id']: node for node in public_map['nodes']}; edges = tokens(public_map['edges'])
    for case in cohort['cases']:
        row = key['cases'][case['case_id']]
        c.keys(row, {'direction_required', 'alternatives'}, 'key case')
        c.require(type(row['direction_required']) is bool and row['direction_required'] == (case['operator'] != 'inline_scope'), 'Direction applicability differs')
        c.require(type(row['alternatives']) is list and 1 <= len(row['alternatives']) <= 8, 'Key alternatives bound')
        for answer in row['alternatives']:
            c.keys(answer, {'references', 'relationships', 'claim_labels', 'target_labels', 'interpretations'}, 'key alternative')
            exemplar = {'schema_version': 1, 'case_id': case['case_id'], 'map_payload_hash': public_map['payloadHash'],
                'answer_status': 'answered', 'unresolved_reason': None, **answer}
            c.validate_response(exemplar, case, public_map)
            c.require(bool(answer['references']) and bool(answer['interpretations']), 'Key must require evidence and an interpretation')
            reference_integrity(answer['references'], nodes); target_integrity(answer['target_labels'], nodes)
            c.require(answer['claim_labels'] == expected_claim(case, nodes), 'Key claim labels contradict map')
            c.require(tokens(answer['relationships']) <= edges and bool(answer['relationships']) == row['direction_required'], 'Key relationships contradict map/applicability')
            if case['operator'] != 'inline_scope':
                kind = {'cite_sources': 'cites', 'cite_documents': 'cites', 'outgoing_qualification': 'challenges', 'motivated_followups': 'motivates'}[case['operator']]
                target_kinds = {'cite_sources': {'source'}, 'cite_documents': {'document'}, 'outgoing_qualification': {'claim'},
                    'motivated_followups': {'experiment', 'representation', 'transformation'}}[case['operator']]
                c.require(all(edge['source'] == answer['claim_labels']['node_id'] and edge['type'] == kind
                    and nodes[edge['target']]['kind'] in target_kinds for edge in answer['relationships']), 'Key is outside requested direct operation')
    c.require(len(c.canonical(key)) <= c.MAX_KEY_BYTES, 'Private key byte bound')
    return key


def _failed_row(case, outcome, reason, *, started, parsed=False):
    return {'case_id': case['case_id'], 'family': case['family'], 'outcome': outcome, 'reason': reason,
        'started': started, 'parseable': parsed, 'scorable': False, 'strict_completion': False,
        'references': None, 'direction': None, 'claim_labels': None, 'interpretation': None,
        'target_labels': None, 'reference_integrity': None, 'unpermitted_additions': None}


def score_case(case, public_map, key_case, attempt):
    """attempt envelope is validated independently by runner/checker before scoring."""
    if attempt['state'] == 'not_started':
        return _failed_row(case, 'not_started', attempt['reason'], started=False)
    receipt = attempt['receipt']; kind = receipt['termination']['kind']
    if kind != 'completed' or receipt['returncode'] != 0 or not receipt['source_unchanged']:
        outcome = {'timeout': 'timed_out', 'output_limit': 'output_limit'}.get(kind, 'process_failed')
        return _failed_row(case, outcome, kind if receipt['source_unchanged'] else 'source_changed', started=receipt['process_started'])
    try:
        value = c.decode(attempt['stdout'], c.MAX_STREAM_BYTES)
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        return _failed_row(case, 'malformed', 'Output is not bounded strict JSON', started=True)
    try:
        c.validate_response(value, case, public_map)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return _failed_row(case, 'malformed', 'Output violates public response schema', started=True, parsed=True)
    if value['answer_status'] == 'unresolved':
        return _failed_row(case, 'unresolved', value['unresolved_reason'], started=True, parsed=True)
    nodes = {node['id']: node for node in public_map['nodes']}; map_edges = tokens(public_map['edges'])
    integrity, targets_valid = True, True
    try: reference_integrity(value['references'], nodes)
    except (ValueError, TypeError, KeyError, IndexError): integrity = False
    try: target_integrity(value['target_labels'], nodes)
    except (ValueError, TypeError, KeyError, IndexError): targets_valid = False
    alternatives = key_case['alternatives']
    matches = [{'references': integrity and ref_tokens(value['references']) == ref_tokens(answer['references']),
        'direction': tokens(value['relationships']) == tokens(answer['relationships']),
        'claim_labels': value['claim_labels'] == answer['claim_labels'],
        'target_labels': targets_valid and tokens(value['target_labels']) == tokens(answer['target_labels']),
        'interpretation': tokens(value['interpretations']) == tokens(answer['interpretations'])} for answer in alternatives]
    unsupported = (not integrity or not targets_valid or not tokens(value['relationships']) <= map_edges
        or not any(ref_tokens(value['references']) <= ref_tokens(answer['references'])
            and tokens(value['relationships']) <= tokens(answer['relationships'])
            and tokens(value['target_labels']) <= tokens(answer['target_labels'])
            and tokens(value['interpretations']) <= tokens(answer['interpretations']) for answer in alternatives))
    return {'case_id': case['case_id'], 'family': case['family'], 'outcome': 'answered', 'reason': None,
        'started': True, 'parseable': True, 'scorable': True,
        'strict_completion': not unsupported and any(all(match.values()) for match in matches),
        'references': any(match['references'] for match in matches),
        'direction': any(match['direction'] for match in matches) if key_case['direction_required'] else None,
        'claim_labels': any(match['claim_labels'] for match in matches),
        'interpretation': any(match['interpretation'] for match in matches),
        'target_labels': any(match['target_labels'] for match in matches), 'reference_integrity': integrity,
        'unpermitted_additions': unsupported}


def evaluate(public_map, cohort, key, attempts):
    c.validate_map(public_map); c.validate_cohort(cohort, public_map); validate_key(key, cohort, public_map)
    c.keys(attempts, {case['case_id'] for case in cohort['cases']}, 'retained attempts')
    rows = [score_case(case, public_map, key['cases'][case['case_id']], attempts[case['case_id']]) for case in cohort['cases']]
    metrics = {}
    for metric, denominator in c.DENOMINATORS.items():
        if metric in INTERPRETATION_FIELDS.values():
            family = next(family for family, field in INTERPRETATION_FIELDS.items() if metric == field)
            selected, field = [row for row in rows if row['family'] == family], 'interpretation'
        else:
            selected, field = rows, metric
        numerator = sum(row[field] is True for row in selected)
        metrics[metric] = {'numerator': numerator, 'denominator': denominator, 'value': numerator / denominator,
            'unknown_cases': sum(row[field] is None for row in selected if metric != 'direction' or key['cases'][row['case_id']]['direction_required'])}
    outcomes = {name: sum(row['outcome'] == name for row in rows) for name in
        ('answered', 'unresolved', 'malformed', 'process_failed', 'timed_out', 'output_limit', 'not_started')}
    coverage = {field: {'numerator': sum(row[field] for row in rows), 'denominator': 6} for field in ('started', 'parseable', 'scorable')}
    operational = any(outcomes[name] for name in ('process_failed', 'timed_out', 'output_limit', 'not_started'))
    passed = all(row['strict_completion'] for row in rows)
    action = ('repair_navigation_execution_contract' if operational else 'prepare_independent_evidence_navigation_comparison'
        if passed else 'diagnose_textual_navigation_failure')
    report = {'schema_version': 1, 'contract_id': c.CONTRACT_ID, 'map_payload_hash': public_map['payloadHash'],
        'cohort_hash': c.digest(c.canonical(cohort)), 'key_hash': c.digest(c.canonical(key)), 'metrics': metrics,
        'outcomes': outcomes, 'coverage': coverage, 'cases': rows, 'passed': passed,
        'family_strict_completion': {family: {'numerator': sum(row['strict_completion'] for row in rows if row['family'] == family), 'denominator': 2} for family in c.FAMILIES},
        'next_action': action,
        'addition_scope': 'Unpermitted additions are outside every reviewed answer bundle; valid extra metadata is not thereby false. Reference integrity and target labels are checked separately.',
        'unknowns': {'human_comprehension': None, 'browser_usability': None, 'graph_vs_text_benefit': None,
            'general_accuracy': None, 'external_witness': None}, 'scope': c.CONTRACT['scope']}
    c.require(len(c.canonical(report)) <= c.MAX_REPORT_BYTES, 'Evaluation report byte bound')
    return report


def evaluate_run(directory, key_path):
    """Separate post-seal local evaluator; no process launch and no ledger connection."""
    from . import navigation_runner as runner
    loaded_source()
    return runner.within_deadline(_evaluate_run, c.EVALUATE_SECONDS, directory, key_path)


def _evaluate_run(directory, key_path):
    from . import navigation_runner as runner
    directory = Path(directory).resolve(); started, start = runner.utc(), time.monotonic()
    runner.write_new(directory / 'evaluation-claim.json', c.canonical({'schema_version': 1,
        'started_at': started, 'evaluator_sha256': c.digest(IMPLEMENTATION_SOURCE), 'retry_allowed': False}), c.MAX_RECEIPT_BYTES)
    result = {'schema_version': 1, 'status': 'failed', 'started_at': started, 'ended_at': None, 'elapsed_seconds': None,
        'registration': None, 'seal_sha256': None, 'key_raw_sha256': None, 'key_hash': None,
        'source_hashes': runner.sources(), 'whole_run_seconds': None, 'total_budget_ok': False, 'scores': None, 'error': None}
    try:
        parent = c.decode(runner.read(directory / 'registration.json', 1048576), 1048576)
        identity = {'event_id': parent['id'], 'event_hash': parent['hash']}
        _, registration = runner.accepted_registration([parent], identity)
        result['registration'] = identity
        c.require(result['source_hashes'] == registration['source_hashes'], 'Registered scoring source changed')
        public_map = c.validate_map(c.decode(runner.read(directory / 'map.bin', c.MAX_MAP_BYTES), c.MAX_MAP_BYTES))
        tasks_raw = runner.read(directory / 'tasks.bin', c.MAX_TASK_BYTES)
        cohort = c.validate_cohort(c.decode(tasks_raw, c.MAX_TASK_BYTES), public_map)
        c.require(c.digest(runner.read(directory / 'map.bin', c.MAX_MAP_BYTES)) == registration['input_hashes']['map']
            and c.digest(tasks_raw) == registration['input_hashes']['tasks'], 'Retained evaluation inputs differ')
        captures = list(directory.glob('capture-*.json')); c.require(2 <= len(captures) <= 32, 'Execution capture count')
        execution, observations = {}, {}
        import re
        for path in captures:
            capture = c.decode(runner.read(path, c.MAX_RECEIPT_BYTES), c.MAX_RECEIPT_BYTES)
            role = capture['role']
            c.require(type(role) is str and re.fullmatch(r'claim|seal|attempt-[0-5]-(?:claim|receipt|stdout|stderr)', role)
                and role not in execution, 'Invalid/duplicate execution role')
            execution[role] = runner.read(directory / ('record-' + role + '.bin'), c.MAX_RECEIPT_BYTES)
            observations[role] = capture['event']
        attempts, claim, seal = runner.validate_execution(public_map, cohort, registration, identity, execution, observations)
        result['seal_sha256'] = c.digest(execution['seal'])
        raw_key = runner.read(key_path, c.MAX_KEY_BYTES)
        result['key_raw_sha256'] = c.digest(raw_key)
        key = c.decode(raw_key, c.MAX_KEY_BYTES); result['key_hash'] = c.digest(c.canonical(key))
        c.require(result['key_raw_sha256'] == registration['input_hashes']['key'] and result['key_hash'] == registration['key_hash'], 'Wrong sealed key')
        validate_key(key, cohort, public_map)
        remaining = c.TOTAL_SECONDS - (time.monotonic() - claim['started_monotonic'])
        c.require(remaining > 0, 'Whole study budget exhausted before scoring')
        # Tighten the already installed evaluator alarm to the remaining whole-study budget.
        import signal
        current = signal.getitimer(signal.ITIMER_REAL)[0]
        signal.setitimer(signal.ITIMER_REAL, min(current, remaining))
        provisional_scores = evaluate(public_map, cohort, key, attempts)
        result['whole_run_seconds'] = time.monotonic() - claim['started_monotonic']
        result['total_budget_ok'] = result['whole_run_seconds'] <= c.TOTAL_SECONDS
        c.require(result['total_budget_ok'] and time.monotonic() - start <= c.EVALUATE_SECONDS, 'Scoring time budget exceeded')
        c.require(runner.sources() == registration['source_hashes'], 'Scoring sources changed')
        loaded_source()
        result['scores'] = provisional_scores
        result['status'] = 'scored'
    except (ValueError, OSError, TypeError, KeyError, IndexError, UnicodeError, RecursionError) as error:
        if isinstance(error, runner.DeadlineExpired):
            import signal
            if signal.getitimer(signal.ITIMER_REAL)[0] <= 0: raise
        result.update(status='failed', scores=None, total_budget_ok=False)
        result['error'] = type(error).__name__ + ': ' + str(error)[:512]
    result.update(ended_at=runner.utc(), elapsed_seconds=time.monotonic() - start)
    # These immutable bytes are provisional until an independent supervisor has
    # observed this process exit and bound its outcome to the exact report hash.
    # A write/flush interruption may leave bytes; never rewrite that evidence or
    # mistake an evaluator-written file for proof that its process completed.
    runner.write_new(directory / 'evaluation.json', c.canonical(result), c.MAX_REPORT_BYTES)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', required=True)
    parser.add_argument('--key', required=True)
    args = parser.parse_args()
    result = evaluate_run(args.run_directory, args.key)
    print(c.canonical(result).decode('utf-8'))
    if result['status'] != 'scored': raise SystemExit(1)


_FUNCTION_CODES = tuple((name, function, function.__code__) for name, function in tuple(globals().items())
    if callable(function) and getattr(function, '__module__', None) == __name__ and hasattr(function, '__code__'))
_CONSTANTS = (('INTERPRETATION_FIELDS', deepcopy(INTERPRETATION_FIELDS)),)

if __name__ == '__main__': main()
