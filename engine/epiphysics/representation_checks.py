"""Offline conformance checks for explicitly curated, synthetic query contracts.

Adapters may normalize different representations to answers. This module does not
extract knowledge, predict outcomes, or require the same internal ontology.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import store
from .store import canonical, instant

IMPLEMENTATION_DEPENDENCIES = ((store.__name__, store.IMPLEMENTATION_CODE),)


DIMENSIONS = {"identity", "relation_direction", "relation_type", "time", "units",
    "contradiction", "hierarchy", "boundary", "workflow"}
FAMILIES = {"software_service", "organization", "person_role", "contract_obligation",
    "physical_asset", "collective", "representation"}
MAX_CASES = 100
MAX_CHECKS = 100
MAX_OBSERVATIONS = 100
INTERPRETATION = (
    "Synthetic query-contract conformance only; not calibration, prediction, learned-model quality, "
    "business value, or empirical validation. Accuracy requires both the expected JSON value and "
    "the exact curated eligible evidence set. Coverage counts supplied answers, including wrong ones. "
    "All metric denominators are the declared checks. Temporal violations count checks citing at least "
    "one observation recorded after the cutoff. The reference candidate deliberately copies expected "
    "answers and is an oracle positive control, not a learned model."
)


def _object(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f"{label} must contain exactly: {', '.join(fields)}")


def _text(value, label):
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _array(value, label, maximum, *, nonempty=False):
    if type(value) is not list or len(value) > maximum or (nonempty and not value):
        raise ValueError(f"{label} must be an array with {'1' if nonempty else '0'}–{maximum} entries")
    return value


def _timestamp(value, label):
    _text(value, label)
    try:
        return instant(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"Invalid timezone-aware timestamp for {label}") from error


def _json(value):
    def validate(item):
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError("JSON object keys must be strings")
            for child in item.values():
                validate(child)
        elif type(item) is list:
            for child in item:
                validate(child)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise ValueError("Expected a JSON value")

    try:
        validate(value)
        return canonical(value)
    except (TypeError, ValueError, RecursionError, OverflowError) as error:
        raise ValueError("Expected a finite JSON value with string object keys") from error


def _evidence(value, label, *, nonempty=False):
    _array(value, label, MAX_OBSERVATIONS, nonempty=nonempty)
    for item in value:
        _text(item, label)
    if len(value) != len(set(value)):
        raise ValueError(f"Duplicate evidence IDs in {label}")
    return set(value)


def validate_suite(suite) -> None:
    """Reject malformed or temporally ineligible reference obligations."""
    _object(suite, ("schema_version", "cases"), "Suite")
    if type(suite["schema_version"]) is not int or suite["schema_version"] != 1:
        raise ValueError("Suite schema_version must be 1")
    _array(suite["cases"], "Suite cases", MAX_CASES, nonempty=True)
    case_ids = set()
    for case in suite["cases"]:
        _object(case, ("id", "family", "description", "cutoff", "observations", "checks"), "Case")
        case_id = _text(case["id"], "Case id")
        if case_id in case_ids:
            raise ValueError(f"Duplicate case: {case_id}")
        case_ids.add(case_id)
        if _text(case["family"], "Case family") not in FAMILIES:
            raise ValueError(f"Unknown family: {case['family']}")
        _text(case["description"], "Case description")
        cutoff = _timestamp(case["cutoff"], "Case cutoff")
        _array(case["observations"], "Case observations", MAX_OBSERVATIONS, nonempty=True)
        observations = {}
        for observation in case["observations"]:
            _object(observation, ("id", "recorded_at"), "Observation")
            oid = _text(observation["id"], "Observation id")
            if oid in observations:
                raise ValueError(f"Duplicate observation: {oid}")
            observations[oid] = _timestamp(observation["recorded_at"], "Observation recorded_at")
        _array(case["checks"], "Case checks", MAX_CHECKS, nonempty=True)
        check_ids = set()
        for check in case["checks"]:
            _object(check, ("id", "dimension", "expected", "evidence_ids"), "Check")
            check_id = _text(check["id"], "Check id")
            if check_id in check_ids:
                raise ValueError(f"Duplicate check: {check_id}")
            check_ids.add(check_id)
            if _text(check["dimension"], "Check dimension") not in DIMENSIONS:
                raise ValueError(f"Unknown dimension: {check['dimension']}")
            _json(check["expected"])
            evidence = _evidence(check["evidence_ids"], "Reference evidence", nonempty=True)
            if not evidence <= observations.keys():
                raise ValueError(f"Unknown reference evidence for {check_id}")
            if any(observations[oid] > cutoff for oid in evidence):
                raise ValueError(f"Reference evidence after cutoff for {check_id}")


def reference_candidate(suite) -> dict:
    """Oracle positive control: deliberately copy answers, without learning or inference."""
    validate_suite(suite)
    return {"schema_version": 1, "cases": [{"id": case["id"], "answers": [
        {"check_id": check["id"], "value": deepcopy(check["expected"]), "evidence_ids": list(check["evidence_ids"])}
        for check in case["checks"]]} for case in suite["cases"]]}


def degraded_candidate(suite) -> dict:
    """Negative control: lose provenance plus direction and unit qualifiers where present."""
    candidate = reference_candidate(suite)
    for case, answers in zip(suite["cases"], candidate["cases"]):
        # A lossy provenance projection in every family, including identity-only suites.
        answers["answers"][0]["evidence_ids"] = []
        for check, answer in zip(case["checks"], answers["answers"]):
            value = answer["value"]
            if check["dimension"] == "relation_direction" and type(value) is dict and {"source", "target"} <= value.keys():
                answer["value"] = {"participants": [value["source"], value["target"]]}
            elif check["dimension"] == "units" and type(value) is dict:
                answer["value"] = {key: item for key, item in value.items() if key not in {"unit", "currency"}}
    return candidate


def _summary(checks):
    count = len(checks)
    correct = sum(check["correct"] for check in checks)
    answered = sum(check["answered"] for check in checks)
    provenance = sum(check["provenance_correct"] for check in checks)
    return {"checks": count, "correct": correct, "answered": answered, "provenance_correct": provenance,
        "temporal_violations": sum(check["temporal_violation"] for check in checks),
        "accuracy": correct / count, "coverage": answered / count, "provenance": provenance / count}


def evaluate(suite, candidate) -> dict:
    """Score wrong/missing answers; reject malformed schemas and unknown or duplicate IDs."""
    validate_suite(suite)
    _object(candidate, ("schema_version", "cases"), "Candidate")
    if type(candidate["schema_version"]) is not int or candidate["schema_version"] != 1:
        raise ValueError("Candidate schema_version must be 1")
    _array(candidate["cases"], "Candidate cases", MAX_CASES)
    declared = {case["id"]: case for case in suite["cases"]}
    supplied = {}
    for case in candidate["cases"]:
        _object(case, ("id", "answers"), "Candidate case")
        case_id = _text(case["id"], "Candidate case id")
        if case_id not in declared:
            raise ValueError(f"Unknown candidate case: {case_id}")
        if case_id in supplied:
            raise ValueError(f"Duplicate candidate case: {case_id}")
        _array(case["answers"], "Candidate answers", MAX_CHECKS)
        check_ids = {check["id"] for check in declared[case_id]["checks"]}
        observation_ids = {observation["id"] for observation in declared[case_id]["observations"]}
        answers = {}
        for answer in case["answers"]:
            _object(answer, ("check_id", "value", "evidence_ids"), "Answer")
            check_id = _text(answer["check_id"], "Answer check_id")
            if check_id not in check_ids:
                raise ValueError(f"Unknown answer check: {check_id}")
            if check_id in answers:
                raise ValueError(f"Duplicate answer: {check_id}")
            _json(answer["value"])
            evidence = _evidence(answer["evidence_ids"], "Answer evidence")
            if not evidence <= observation_ids:
                raise ValueError(f"Unknown answer evidence for {check_id}")
            answers[check_id] = answer
        supplied[case_id] = answers
    cases, all_checks = [], []
    by_family, by_dimension = {}, {}
    for case in suite["cases"]:
        cutoff = _timestamp(case["cutoff"], "Case cutoff")
        observed = {observation["id"]: _timestamp(observation["recorded_at"], "Observation recorded_at")
            for observation in case["observations"]}
        checks = []
        for check in case["checks"]:
            answer = supplied.get(case["id"], {}).get(check["id"])
            expected_evidence = set(check["evidence_ids"])
            evidence = set(answer["evidence_ids"]) if answer is not None else set()
            late = sorted(oid for oid in evidence if observed[oid] > cutoff)
            value_correct = answer is not None and _json(answer["value"]) == _json(check["expected"])
            provenance_correct = answer is not None and evidence == expected_evidence and not late
            result = {"id": check["id"], "dimension": check["dimension"], "answered": answer is not None,
                "value_correct": value_correct, "provenance_correct": bool(provenance_correct),
                "correct": bool(value_correct and provenance_correct), "temporal_violation": bool(late),
                "missing_evidence_ids": sorted(expected_evidence - evidence),
                "unexpected_evidence_ids": sorted(evidence - expected_evidence), "late_evidence_ids": late}
            checks.append(result)
            by_family.setdefault(case["family"], []).append(result)
            by_dimension.setdefault(check["dimension"], []).append(result)
        cases.append({"id": case["id"], "family": case["family"], "checks": checks, "metrics": _summary(checks)})
        all_checks.extend(checks)
    families = {}
    for family, checks in sorted(by_family.items()):
        summary = _summary(checks)
        families[family] = {key: summary[key] for key in ("checks", "correct", "accuracy")}
    metrics = _summary(all_checks)
    metrics["worst_family_accuracy"] = min(family["accuracy"] for family in families.values())
    metrics["macro_family_accuracy"] = sum(family["accuracy"] for family in families.values()) / len(families)
    return {"cases": cases, "metrics": metrics, "families": families,
        "dimensions": {dimension: _summary(checks) for dimension, checks in sorted(by_dimension.items())},
        "interpretation": INTERPRETATION}
