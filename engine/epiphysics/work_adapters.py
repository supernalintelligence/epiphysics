"""Static pure fixture assessors. Input data cannot select executable code."""
from __future__ import annotations

import sys
from pathlib import Path
from . import work_contracts as c

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = ((c.__name__, c.IMPLEMENTATION_CODE),)


def reference_policy(policy, cases, outcomes):
    c.keys(policy['rules'], {'extras'}, 'reference rule')
    c.require(policy['rules']['extras'] in {'allow_valid', 'forbid'}, 'Unknown extra-reference policy')
    rows = []
    for case, outcome in zip(cases, outcomes, strict=True):
        c.keys(case, {'id', 'family', 'available', 'required'}, 'reference case')
        c.keys(outcome, {'id', 'submitted'}, 'reference outcome')
        c.strings(case['available'], 'available references'); c.strings(case['required'], 'required references')
        c.require(set(case['required']) <= set(case['available']), 'Required reference is absent')
        row = {'case_id': case['id'], 'family': case['family'], 'abstained': outcome['submitted'] is None}
        if row['abstained']:
            row.update(valid_references=None, required_coverage=None, valid_extra_count=None,
                       invalid_reference_count=None, missing_reference_count=None, conformance=False)
        else:
            c.strings(outcome['submitted'], 'submitted references', empty=True)
            submitted, required, available = map(set, (outcome['submitted'], case['required'], case['available']))
            invalid, missing, extras = submitted - available, required - submitted, submitted - required
            row.update(valid_references=not invalid, required_coverage=not missing,
                       valid_extra_count=len(extras & available), invalid_reference_count=len(invalid),
                       missing_reference_count=len(missing),
                       conformance=not invalid and not missing and (not extras or policy['rules']['extras'] == 'allow_valid'))
        rows.append(row)
    return rows


def artifact_quality(policy, cases, outcomes):
    c.keys(policy['rules'], {'max_bytes', 'required_keys', 'extra_keys'}, 'artifact rules')
    rules = policy['rules']
    c.require(type(rules['max_bytes']) is int and 1 <= rules['max_bytes'] <= 65536, 'Artifact byte bound')
    c.strings(rules['required_keys'], 'required artifact keys')
    c.require(rules['extra_keys'] in {'allow', 'forbid'}, 'Artifact extra-key rule')
    rows = []
    for case, outcome in zip(cases, outcomes, strict=True):
        c.keys(case, {'id', 'family', 'expected_sha256'}, 'artifact case')
        c.keys(outcome, {'id', 'artifact'}, 'artifact outcome')
        c.hash_text(case['expected_sha256'], 'expected artifact digest')
        row = {'case_id': case['id'], 'family': case['family'], 'abstained': outcome['artifact'] is None}
        if row['abstained']:
            row.update(within_byte_limit=None, digest_match=None, object_format=None,
                       required_keys_present=None, extra_keys_permitted=None, conformance=False)
        else:
            c.require(type(outcome['artifact']) is str, 'Artifact must be retained text or abstention')
            raw = outcome['artifact'].encode('utf-8')
            within, matches = len(raw) <= rules['max_bytes'], c.store.digest(raw) == case['expected_sha256']
            try:
                value = c.decode(raw)
            except (ValueError, TypeError, RecursionError):
                value = None
            is_object = type(value) is dict
            present = set(rules['required_keys']) <= set(value) if is_object else None
            permitted = (rules['extra_keys'] == 'allow' or set(value) <= set(rules['required_keys'])) if is_object else None
            row.update(within_byte_limit=within, digest_match=matches, object_format=is_object,
                       required_keys_present=present, extra_keys_permitted=permitted,
                       conformance=bool(within and matches and is_object and present and permitted))
        rows.append(row)
    return rows


REGISTRY = {'reference-policy-v1': reference_policy, 'artifact-quality-v1': artifact_quality}


def assess(bundle):
    c.validate(bundle)
    adapter = REGISTRY.get(bundle['declaration']['adapter'])
    c.require(adapter is not None, 'Adapter is not allowlisted')
    rows = adapter(bundle['public_policy'], bundle['cases'], bundle['outcome_manifest']['records'])
    families = {}
    for family, denominator in bundle['public_policy']['family_denominators'].items():
        families[family] = {'numerator': sum(row['conformance'] for row in rows if row['family'] == family),
                            'denominator': denominator}
    return {'scope': 'invented_retained_input_fixture', 'cases': rows,
            'conformance': {'numerator': sum(row['conformance'] for row in rows), 'denominator': len(rows)},
            'families': families, 'abstentions': sum(row['abstained'] for row in rows),
            'passed': all(row['conformance'] for row in rows),
            'measurement_identity': c.measurement_identity(bundle),
            'general_accuracy': None, 'predictive_advantage': None}
