"""Bounded offline assessment with an append-only completion-to-next-step handoff.

The desktop automation supervises scoped builders. The dispatcher executes only
the offline assessment program; it never grants deployment or scale rights.
Fixture success is not predictive or business lift.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import selectors
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, decision_assessment, decision_diagnosis, decision_views, dated_delivery, dated_delivery_verifier, public_map_assessment, navigation_assessment, navigation_contracts, navigation_runner, navigation_evaluation, graph_view_checks, graph_views, manifest_checks, manifests, materialization, materialization_checks, representation_checks, retrieval, retrieval_assessment, retrieval_contracts, retrieval_coverage, retrieval_diagnosis, retrieval_evaluation, retrieval_indexing, retrieval_probe, source_span_checks, store, transformation_checks, transforms
from .store import Ledger, canonical, digest, utc_now
from .representation_checks import FAMILIES, evaluate, reference_candidate, degraded_candidate, validate_suite
from .source_span_checks import run_source_span_checks
from .manifest_checks import run_manifest_checks
from .transformation_checks import run_transformation_checks
from .graph_view_checks import run_graph_view_checks
from .materialization_checks import run_materialization_checks

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE)
    for module in (assertions, decision_assessment, decision_diagnosis, decision_views, dated_delivery, dated_delivery_verifier, public_map_assessment, navigation_assessment, navigation_contracts, navigation_runner, navigation_evaluation, manifests, manifest_checks, representation_checks, source_span_checks, store, transforms, transformation_checks, graph_views, graph_view_checks, materialization, materialization_checks, retrieval, retrieval_evaluation, retrieval_assessment, retrieval_contracts, retrieval_indexing, retrieval_coverage, retrieval_diagnosis, retrieval_probe)
)

# Pin dependency identities after imports. Reloading a module can otherwise pair
# its new source snapshot with our old from-import callable aliases.
_IMPLEMENTATIONS = {
    name: (module, Path(module.__file__), module.IMPLEMENTATION_SOURCE,
           module.IMPLEMENTATION_CODE, module.IMPLEMENTATION_DEPENDENCIES)
    for name, module in {"evaluator": representation_checks, "assertions": assertions,
                         "manifests": manifests, "manifest_probe": manifest_checks,
                         "transforms": transforms, "transformation_probe": transformation_checks,
                         "graph_views": graph_views, "graph_view_probe": graph_view_checks,
                         "materialization": materialization, "materialization_probe": materialization_checks,
                         "retrieval": retrieval, "retrieval_evaluator": retrieval_evaluation,
                         "retrieval_assessment": retrieval_assessment,
                         "retrieval_contracts": retrieval_contracts, "retrieval_indexing": retrieval_indexing,
                         "retrieval_coverage": retrieval_coverage,
                         "retrieval_diagnosis": retrieval_diagnosis,
                         "retrieval_probe": retrieval_probe,
                         "decision_assessment": decision_assessment,
                         "decision_diagnosis": decision_diagnosis,
                         "dated_delivery": dated_delivery,
                         "public_map_assessment": public_map_assessment,
                         "navigation_assessment": navigation_assessment,
                         "navigation_contracts": navigation_contracts,
                         "navigation_runner": navigation_runner,
                         "navigation_evaluation": navigation_evaluation,
                         "dated_delivery_verifier": dated_delivery_verifier,
                         "decision_views": decision_views,
                         "source_span_probe": source_span_checks, "store": store,
                         "controller": sys.modules[__name__]}.items()
}

MAX_BYTES = 1_000_000
TRANSITIONS = {"improvement_completed", "improvement_failed"}
ALLOWED_EVENTS = TRANSITIONS | {"improvement_started", "observation"}


def _load(path, limit=MAX_BYTES):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"Input exceeds {limit} bytes")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    canonical(value)  # Reject NaN/Infinity, including in unused metadata.
    return value, raw


def _prepare_retrieval(study_path, policy, improvement_store):
    """Capture once; malformed supplied studies remain an explicit failed input."""
    if study_path is None:
        return None
    try:
        prepared = retrieval_assessment.prepare_retrieval_study(
            study_path, declared_contract=policy.get("retrieval_study"), forbidden_store=improvement_store)
        return {"prepared": prepared, "error": None}
    except (ValueError, OSError, TypeError, KeyError, RuntimeError, sqlite3.Error) as error:
        return _failed_retrieval_preparation(study_path, error)


def _prepare_decision(study_path):
    if study_path is None:
        return None
    try:
        return {"prepared": decision_assessment.prepare_decision_study(study_path), "error": None}
    except (ValueError, OSError, TypeError, KeyError, RuntimeError, sqlite3.Error) as error:
        failed = _failed_retrieval_preparation(study_path, error)
        if isinstance(error, (decision_assessment.DecisionStudyPreparationError, decision_diagnosis.PreparationError,
                              dated_delivery.PreparationError, public_map_assessment.PreparationError, navigation_assessment.PreparationError)):
            artifacts = failed["prepared"]["artifacts"]
            artifacts.update({"invalid-captured:" + role: raw for role, raw in error.artifacts.items()})
            failed["prepared"]["manifest"] = {role: digest(raw) for role, raw in artifacts.items()}
        return failed


def _decision_inputs(preparation):
    if preparation is None:
        return {}
    return {"decision-input:" + role: raw for role, raw in preparation["prepared"]["artifacts"].items()}


def _failed_decision_parent(event):
    """A failed decision claim cannot be cleared by an unrelated fixture run."""
    return (event is not None and event["kind"] == "improvement_failed"
            and any(name.startswith("decision-input:")
                    for name in event["body"].get("request", {}).get("manifest", {})))


def _information_context(preparation, events):
    transitions = [event for event in events if event["kind"] in TRANSITIONS]
    current = transitions[-1] if transitions else None
    if current is not None and (current["body"]["next_step"]["action"] in {
            "investigate_decision_information_limits", "repair_decision_information_diagnosis",
            "review_unresolved_decision_evidence", "prepare_dated_evidence_quality_protocol"}
            | dated_delivery.SEMANTIC_ACTIONS | public_map_assessment.SEMANTIC_ACTIONS | public_map_assessment.NEXT_ACTIONS
            | navigation_assessment.SEMANTIC_ACTIONS | navigation_assessment.NEXT_ACTIONS
            or _failed_decision_parent(current)):
        return True
    if preparation is None:
        return False
    if preparation["error"] is None:
        return preparation["prepared"]["report"].get("phase") in {decision_diagnosis.PHASE, *dated_delivery.PHASES, public_map_assessment.PHASE, *navigation_assessment.PHASES}
    # A failed explicit diagnosis still has diagnosis preclaim semantics even
    # when aimed at an unrelated queued step. Use only captured bounded bytes;
    # a file name or an incomplete/ambiguous JSON prefix cannot declare a phase.
    artifacts = preparation["prepared"]["artifacts"]
    for role in ("invalid-captured:request", "invalid-request-prefix"):
        raw = artifacts.get(role)
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            continue
        try:
            request = decision_assessment._json(raw)
        except (ValueError, TypeError, RecursionError):
            continue
        if type(request) is dict and request.get("phase") in {decision_diagnosis.PHASE, *dated_delivery.PHASES, public_map_assessment.PHASE, *navigation_assessment.PHASES}:
            return True
    return False


def _check_decision_origin(preparation, events, after_step):
    transitions = [event for event in events if event["kind"] in TRANSITIONS]
    previous = transitions[-1]["body"]["next_step"] if transitions else None
    if preparation is None:
        if (previous is not None and previous["id"] == after_step and previous["action"] in {
                "prepare_control_exchange_decision_pilot", "repair_decision_pilot", "prepare_fresh_decision_comparison",
                "prepare_prospective_decision_shadow", "investigate_decision_information_limits",
                "repair_decision_information_diagnosis", "review_unresolved_decision_evidence",
                "prepare_dated_evidence_quality_protocol"}
                | dated_delivery.SEMANTIC_ACTIONS | public_map_assessment.SEMANTIC_ACTIONS | public_map_assessment.NEXT_ACTIONS
            | navigation_assessment.SEMANTIC_ACTIONS | navigation_assessment.NEXT_ACTIONS):
            raise ValueError("This queued decision step requires its decision evidence; a generic assessment cannot complete it")
        if transitions and _failed_decision_parent(transitions[-1]):
            raise ValueError("A failed decision assessment requires its retained decision evidence; a generic assessment cannot complete it")
        return
    if preparation["error"] is not None:
        if _information_context(preparation, events):
            raise ValueError("Invalid supplied decision diagnosis: " + preparation["error"]["message"])
        return
    report = preparation["prepared"]["report"]
    if (report["origin"]["step_id"] != after_step or previous is None or previous["id"] != after_step
            or previous.get("state") != "queued"):
        raise ValueError("Decision study must bind the currently queued decision-pilot step")
    if report.get("phase") == decision_diagnosis.PHASE:
        decision_diagnosis.validate_lineage(preparation["prepared"], events, after_step)
        return
    if report.get("phase") in dated_delivery.PHASES:
        dated_delivery.validate_lineage(preparation["prepared"], events, after_step)
        return
    if report.get("phase") == public_map_assessment.PHASE:
        public_map_assessment.validate_lineage(preparation["prepared"], events, after_step)
        return
    if report.get("phase") in navigation_assessment.PHASES:
        navigation_assessment.validate_lineage(preparation["prepared"], events, after_step)
        return
    if report.get("phase") == "development":
        if previous["action"] not in {"prepare_control_exchange_decision_pilot", "repair_decision_pilot"}:
            raise ValueError("Development evidence cannot consume a fresh comparison or its successor")
        if previous["action"] == "repair_decision_pilot" and transitions[-1]["body"].get(
                "report", {}).get("decision_pilot", {}).get("phase") != "development":
            raise ValueError("Development repair requires a development predecessor")
        return
    if report.get("phase") != "fresh_comparison":
        raise ValueError("Unsupported checked decision phase")
    try:
        current = transitions[-1]
        supplied = decision_assessment._json(preparation["prepared"]["artifacts"]["origin_transition"])
        prior_pilot = current["body"]["report"]["decision_pilot"]
        binding = report["origin_transition"]
        if (current["kind"] != "improvement_completed" or canonical(current) != canonical(supplied)
                or previous["action"] != "prepare_fresh_decision_comparison"
                or prior_pilot.get("phase") != "development" or prior_pilot.get("status") != "checked"
                or prior_pilot.get("stage") != "exposed_development"
                or not prior_pilot.get("checks") or not all(prior_pilot["checks"].values())
                or binding["event_id"] != current["id"] or binding["event_hash"] != current["hash"]
                or binding["assessment_hash"] != current["body"]["assessment_identity"]["hash"]
                or binding["decision_assessment_hash"] != prior_pilot["assessment_identity"]["hash"]):
            raise ValueError("Fresh comparison must bind the actual accepted development predecessor")
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("Invalid historical decision origin binding") from error


def _failed_retrieval_preparation(path, error):
    # Preserve the rejected locator without traversing symlinks: even a broken
    # or looping link must be recordable as an explicit failed study.
    locator = {"study_path": os.path.abspath(path),
               "error": {"type": type(error).__name__, "message": str(error)[:400]}}
    artifacts = {"invalid-request": canonical(locator).encode()}
    try:
        candidate = Path(path)
        if not candidate.is_symlink() and candidate.is_file():
            descriptor = os.open(candidate, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
            with os.fdopen(descriptor, "rb") as stream:
                if stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    artifacts["invalid-request-prefix"] = stream.read(MAX_BYTES)
    except (OSError, RuntimeError):
        pass
    prepared = {"artifacts": artifacts, "manifest": {name: digest(raw) for name, raw in artifacts.items()}}
    return {"prepared": prepared, "error": locator["error"]}


def _retrieval_inputs(preparation):
    if preparation is None:
        return {}
    prepared = preparation["prepared"]
    return {"retrieval_preparation": canonical({"manifest": prepared["manifest"],
                                                "error": preparation["error"]}).encode(),
            **{f"retrieval-study:{role}": raw for role, raw in prepared["artifacts"].items()}}


def _check_diagnosis_origin(preparation, events, after_step):
    """A captured event is evidence only when it is the actual queued predecessor."""
    if preparation is None or preparation["error"] is not None:
        return
    artifacts = preparation["prepared"]["artifacts"]
    request = retrieval_assessment._json(artifacts["request"])
    phase = request.get("phase")
    if phase not in ("support_diagnosis", "support_probe"):
        return
    try:
        contract = retrieval_assessment._json(artifacts["declared_contract"])
        supplied = (retrieval_assessment._probe_artifacts(artifacts, contract) if phase == "support_probe"
                    else retrieval_assessment._diagnosis_artifacts(artifacts, contract))
        transitions = [event for event in events if event["kind"] in TRANSITIONS]
        current = transitions[-1] if transitions else None
        if (current is None or current["kind"] != "improvement_completed"
                or canonical(current) != canonical(supplied)
                or contract["origin_transition"] != {"id": current["id"], "hash": current["hash"]}):
            raise ValueError("Diagnosis origin must equal the actual completed predecessor")
        step = current["body"]["next_step"]
        if step["id"] != after_step or contract["origin_step_id"] != after_step or step.get("state") != "queued":
            raise ValueError("Diagnosis origin must be the current queued predecessor")
        if phase == "support_probe":
            actual = current["body"]["report"]["support_diagnosis"]
            if (step.get("action") != "prepare_focused_support_followup"
                    or actual.get("schema_version") != 3 or actual.get("phase") != "support_diagnosis"
                    or actual.get("status") != "checked" or actual.get("contract_id") != retrieval_diagnosis.CONTRACT_ID
                    or actual["machine_findings"]["deferred_question_ids"]
                    or not actual["semantic_review"]["cases"]
                    or any(case["category"] != "retrieval_gap" for case in actual["semantic_review"]["cases"])):
                raise ValueError("Support probe origin must queue follow-up from checked retrieval gaps")
        else:
            actual = current["body"]["report"]["actual_retrieval"]
            if (step.get("action") != "inspect_fresh_support_failures"
                    or actual.get("schema_version") != 3 or actual.get("phase") != "evaluation"
                    or actual.get("status") != "completed" or actual["reproducibility"]["value"] != 1):
                raise ValueError("Diagnosis origin must be the queued reproduced coverage failure inspection")
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("Invalid diagnosis origin binding") from error


def _write_retrieval_preparation(directory, preparation):
    """The fixed child receives captured bytes, never a second read of evidence."""
    directory.mkdir()
    prepared = preparation["prepared"]
    entries = {}
    for index, (role, raw) in enumerate(sorted(prepared["artifacts"].items())):
        filename = f"{index:03d}.bin"
        (directory / filename).write_bytes(raw)
        entries[role] = {"file": filename, "size": len(raw), "sha256": digest(raw)}
    manifest = {"schema_version": 1, "artifacts": entries,
                "manifest": prepared["manifest"], "error": preparation["error"]}
    raw = canonical(manifest).encode()
    path = directory / "manifest.json"
    path.write_bytes(raw)
    return path, digest(raw)


def _read_retrieval_preparation(path):
    manifest, raw = _load(path)
    expected = os.environ.get("EPIPHYSICS_RETRIEVAL_PREPARATION_SHA256")
    if expected is not None and digest(raw) != expected:
        raise ValueError("Prepared retrieval transport manifest changed")
    if (type(manifest) is not dict or set(manifest) != {"schema_version", "artifacts", "manifest", "error"}
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or type(manifest["artifacts"]) is not dict
            or not 1 <= len(manifest["artifacts"]) <= retrieval_assessment.MAX_ARTIFACTS
            or type(manifest["manifest"]) is not dict
            or set(manifest["manifest"]) != set(manifest["artifacts"])):
        raise ValueError("Invalid prepared retrieval transport")
    artifacts, total = {}, 0
    for index, (role, entry) in enumerate(sorted(manifest["artifacts"].items())):
        if (type(role) is not str or not role or len(role.encode()) > 512 or type(entry) is not dict
                or set(entry) != {"file", "size", "sha256"} or entry["file"] != f"{index:03d}.bin"
                or type(entry["size"]) is not int or not 0 <= entry["size"] <= retrieval_assessment.MAX_ARTIFACT_BYTES):
            raise ValueError("Invalid prepared retrieval artifact")
        total += entry["size"]
        if total > retrieval_assessment.MAX_BUNDLE_BYTES:
            raise ValueError("Prepared retrieval bundle exceeds byte limit")
        artifact = Path(path).parent / entry["file"]
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError("Prepared retrieval artifact must be a regular file")
        with artifact.open("rb") as stream:
            data = stream.read(entry["size"] + 1)
        if len(data) != entry["size"] or digest(data) != entry["sha256"] or entry["sha256"] != manifest["manifest"][role]:
            raise ValueError("Prepared retrieval artifact changed")
        artifacts[role] = data
    error = manifest["error"]
    if error is not None and (type(error) is not dict or set(error) != {"type", "message"}
                              or any(type(value) is not str or len(value) > 400 for value in error.values())):
        raise ValueError("Invalid prepared retrieval error")
    return {"prepared": {"artifacts": artifacts, "manifest": manifest["manifest"]}, "error": error}


def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get("schema_version") != 1 or type(policy.get("schema_version")) is not int:
        raise ValueError("Policy requires schema_version 1")
    if policy.get("stage") != "offline_fixture" or policy.get("allow_scale_change") is not False:
        raise ValueError("Only offline fixture work is enabled; scale changes are disabled")
    if type(policy.get("max_assessment_seconds")) is not int or not 1 <= policy["max_assessment_seconds"] <= 60:
        raise ValueError("Assessment time limit must be an integer from 1 to 60 seconds")
    if type(policy.get("external_spend")) is not int or policy["external_spend"] != 0:
        raise ValueError("External spend must be zero")
    required = policy.get("required_families")
    if not isinstance(required, list) or any(not isinstance(f, str) for f in required) or set(required) != FAMILIES or len(required) != len(FAMILIES):
        raise ValueError("Policy must retain all seven entity families")
    if not isinstance(policy.get("version"), str) or not policy["version"].strip():
        raise ValueError("Policy version is required")


def _checked_events(ledger):
    integrity = ledger.verify()
    if not integrity["valid"]:
        raise ValueError("Ledger integrity failed; preserve the store for diagnosis")
    events = ledger.events()
    if any(e["kind"] not in ALLOWED_EVENTS for e in events):
        raise ValueError("Use a dedicated improvement store; another workflow is present")
    if any(e["kind"] == "observation" and not e["body"]["source"].startswith("improvement-input:") for e in events):
        raise ValueError("Use a dedicated improvement store; unrelated observations are present")
    return events


def status(ledger):
    events = _checked_events(ledger)
    starts = [e for e in events if e["kind"] == "improvement_started"]
    finished = [e for e in events if e["kind"] in TRANSITIONS]
    completed_keys = {e["body"]["run_key"] for e in finished}
    unfinished = [e["body"]["run_key"] for e in starts if e["body"]["run_key"] not in completed_keys]
    return {"stage": "offline_fixture", "unfinished_runs": unfinished,
            "next_step": finished[-1]["body"]["next_step"] if finished else {
                "id": "initial", "action": "assess_representation_contracts", "state": "queued"},
            "last_transition": finished[-1]["id"] if finished else None,
            "completed_assessments": sum(e["kind"] == "improvement_completed" for e in finished),
            "worker": "Desktop research automation; this queue does not execute itself"}


def select_next(report, run_key):
    """Version-one transparent priority rule, not a calibrated utility predictor."""
    m = report["metrics"]
    pilot = report.get("decision_pilot")
    if pilot is not None:
        phases = {"development": ("exposed_development", {"repair_decision_pilot", "prepare_fresh_decision_comparison"}),
                  "fresh_comparison": ("fresh_exploratory", {"repair_decision_pilot",
                      "prepare_prospective_decision_shadow", "investigate_decision_information_limits"}),
                  decision_diagnosis.PHASE: (decision_diagnosis.STAGE, {
                      "repair_decision_information_diagnosis", "review_unresolved_decision_evidence",
                      "prepare_dated_evidence_quality_protocol"})}
        phases.update({phase: (stage, dated_delivery.PHASE_NEXT_ACTIONS[phase])
                       for phase, stage in dated_delivery.PHASES.items()})
        phases[public_map_assessment.PHASE] = (public_map_assessment.STAGE, public_map_assessment.NEXT_ACTIONS)
        phases.update({phase: (stage, navigation_assessment.PHASE_NEXT_ACTIONS[phase])
                       for phase, stage in navigation_assessment.PHASES.items()})
        expected = phases.get(pilot.get("phase"))
        if (pilot.get("schema_version") != 1 or pilot.get("status") != "checked" or expected is None
                or pilot.get("stage") != expected[0] or pilot.get("next_step", {}).get("action") not in expected[1]):
            raise ValueError("Decision pilot must be independently checked before selecting its successor")
        if (pilot["phase"] == decision_diagnosis.PHASE
                and pilot.get("contract_id") != decision_diagnosis.CONTRACT_ID):
            raise ValueError("Decision diagnosis must use its checked diagnostic contract")
        if (pilot["phase"] in dated_delivery.PHASES
                and pilot.get("contract_id") != dated_delivery.CONTRACT_ID):
            raise ValueError("Dated delivery must use its checked protocol contract")
        if pilot["phase"] == public_map_assessment.PHASE and pilot.get("contract_id") != public_map_assessment.CONTRACT_ID:
            raise ValueError("Public map must use its checked preparation contract")
        if pilot["phase"] in navigation_assessment.PHASES and pilot.get("contract_id") != navigation_assessment.CONTRACT_ID:
            raise ValueError("Navigation must use its checked contract")
    ready = report.get("coverage_preparation")
    if ready is not None and (ready.get("schema_version") != 3 or ready.get("phase") != "preparation" or ready.get("status") != "ready"):
        raise ValueError("Coverage readiness must be validated before choosing a successor")
    diagnosis = report.get("support_diagnosis")
    if diagnosis is not None and (diagnosis.get("schema_version") != 3 or diagnosis.get("phase") != "support_diagnosis"
            or diagnosis.get("status") != "checked" or diagnosis.get("contract_id") != retrieval_diagnosis.CONTRACT_ID):
        raise ValueError("Support diagnosis must be checked before choosing a successor")
    followup = diagnosis is not None and not diagnosis["machine_findings"]["deferred_question_ids"] and all(
        case["category"] == "retrieval_gap" for case in diagnosis["semantic_review"]["cases"])
    support_probe = report.get("support_probe")
    if support_probe is not None and (support_probe.get("schema_version") != 3
            or support_probe.get("phase") != "support_probe" or support_probe.get("status") != "completed"
            or support_probe.get("contract_id") != retrieval_probe.CONTRACT_ID
            or type(support_probe.get("reproducibility", {}).get("value")) is not int
            or support_probe["reproducibility"]["value"] not in (0, 1)):
        raise ValueError("Support probe must be checked before choosing a successor")
    worst = min(report["families"], key=lambda f: (report["families"][f]["accuracy"], f))
    choices = [
        ("repair_time_eligibility", "temporal_violations", 0, "decrease", m["temporal_violations"] > 0,
         "Later evidence entered a fixture answer; fix eligibility before optimizing quality."),
        ("repair_evidence_mapping", "provenance", 1, "increase", m["provenance"] < 1,
         "Some answers lost or changed their required source ancestry."),
        ("cover_missing_answers", "coverage", 1, "increase", m["coverage"] < 1,
         "Missing answers remain in the denominator and require explicit treatment."),
        ("repair_weakest_entity_family", "worst_family_accuracy", 1, "increase", m["worst_family_accuracy"] < 1,
         f"The weakest family is {worst}; inspect its failed contracts before aggregate optimization."),
        ("repair_source_span_assertions", "source_span_resolution", 1, "increase", m.get("source_span_resolution") != 1,
         "The actual assertion implementation failed or lacks a required source-span probe; inspect source_span_checks diagnostics."),
        ("repair_source_span_assertions", "assertion_history_preservation", 1, "increase", m.get("assertion_history_preservation") != 1,
         "The actual assertion implementation failed or lacks a required history/conflict probe; inspect source_span_checks diagnostics."),
        ("repair_representation_manifests", "representation_manifest_preservation", 1, "increase", m.get("representation_manifest_preservation") != 1,
         "The actual manifest implementation failed or lacks a required identity, artifact, or forecast-binding probe; inspect manifest_checks diagnostics."),
        ("repair_graph_transformations", "transformation_preservation", 1, "increase", m.get("transformation_preservation") != 1,
         "The actual fixed graph operations failed or lack an execution, preservation, loss, or receipt probe; inspect transformation_checks diagnostics."),
        ("repair_graph_views", "split_merge_preservation", 1, "increase", m.get("split_merge_preservation") != 1,
         "Actual graph partition/merge operations failed or lack a preservation, conflict, ancestry, loss, or receipt check; inspect graph_view_checks diagnostics."),
        ("repair_transform_materialization", "output_manifest_materialization", 1, "increase", m.get("output_manifest_materialization") != 1,
         "Actual output materialization failed or lacks a binding, ancestry, forecast-consumer, atomicity or replay check; inspect materialization_checks diagnostics."),
        ("repair_decision_pilot", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "repair_decision_pilot",
         "Retained decision attempts failed a conformance or execution check. Preserve the evidence and diagnose before another separately reviewed protocol; no automatic rerun."),
        ("prepare_fresh_decision_comparison", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "prepare_fresh_decision_comparison",
         "The exposed development comparison is validated. Freeze and independently review the next protocol before one new exploratory cohort; no live effects or scale change."),
        ("prepare_prospective_decision_shadow", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "prepare_prospective_decision_shadow",
         "The one fresh scripted comparison met its descriptive triage rule. Prepare one nonacting prospective question with new dated receipts; this authorizes no live action, spending or scale change."),
        ("investigate_decision_information_limits", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "investigate_decision_information_limits",
         "Retain the simpler baseline. Explain the paired losses and information limits, then specify a new informative question; do not tune or rerun these exposed cases."),
        ("repair_decision_information_diagnosis", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "repair_decision_information_diagnosis",
         "The retained diagnostic has a checked conformance failure. Repair that diagnosis using the same accepted evidence; no candidate rerun or changed baseline."),
        ("review_unresolved_decision_evidence", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "review_unresolved_decision_evidence",
         "The retained diagnostic is structurally valid but leaves an evidence attribution unresolved. Review the gap before preparing a new protocol."),
        ("prepare_dated_evidence_quality_protocol", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "prepare_dated_evidence_quality_protocol",
         "The retained diagnosis identifies the next evidence-quality question. Prepare a dated, independently checkable, nonacting artifact-delivery protocol; no new capture, experiment, spending or authority follows from this step."),
        ("repair_dated_evidence_quality_protocol", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "repair_dated_evidence_quality_protocol",
         "The dated delivery preparation failed a declared check. Repair the protocol while preserving its accepted origin; no substitute delivery or live authority."),
        ("bind_dated_artifact_delivery", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "bind_dated_artifact_delivery",
         "The protocol is checked. Register one eligible backlog delivery before producing its first artifact; quality and outcomes remain unmeasured."),
        ("check_dated_artifact_delivery", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "check_dated_artifact_delivery",
         "One future delivery is registered. Preserve its first bytes and claim, then check retained evidence or close honestly at the declared deadline."),
        ("review_dated_delivery_evidence", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "review_dated_delivery_evidence",
         "Review the exact unresolved delivery evidence once; preserve missing or failed outcomes and never replace the first submission."),
        ("prepare_public_research_map_view", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "prepare_public_research_map_view",
         "The first delivery has a checked closure, including negative or missing outcomes. Prepare a public view of the curated research graph; do not infer predictive gain."),
        ("repair_public_research_map_preparation", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "repair_public_research_map_preparation",
         "Repair the retained static public-map failure with changed relevant evidence; no unchanged retry or user-performance inference."),
        ("prepare_evidence_navigation_evaluation", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "prepare_evidence_navigation_evaluation",
         "Prepare six fixed textual evidence-navigation cases with separate answer keys and one attempt per case; browser and human usability remain unmeasured."),
        ("run_textual_evidence_navigation_baseline", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "run_textual_evidence_navigation_baseline",
         "One prospective six-case baseline is registered; retain exactly one first attempt per case without exposing its key."),
        ("repair_evidence_navigation_protocol", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "repair_evidence_navigation_protocol",
         "Repair the unavailable navigation preparation prerequisite; no unchanged retry or candidate execution."),
        ("prepare_independent_evidence_navigation_comparison", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "prepare_independent_evidence_navigation_comparison",
         "Prepare new cases and a stronger comparison; six selected baseline cases establish no human or graph benefit."),
        ("diagnose_textual_navigation_failure", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "diagnose_textual_navigation_failure",
         "Diagnose retained reference, direction or interpretation failures without replacing first attempts."),
        ("repair_navigation_execution_contract", None, None, "increase", pilot is not None and pilot["next_step"]["action"] == "repair_navigation_execution_contract",
         "Repair the bounded execution or evaluation failure while preserving first attempts; no automatic repeat."),
        ("execute_fresh_coverage_baseline", None, None, "increase", ready is not None,
         "Reviewed fresh coverage inputs are frozen. Execute the two declared raw-baseline runs; retrieval quality remains unmeasured."),
        ("prepare_focused_support_followup", None, None, "increase", followup,
         "All failed support cases have reviewed retrieval gaps. Prepare a bounded follow-up declaration; no execution or quality improvement is authorized by this diagnosis."),
        ("clarify_support_diagnosis", None, None, "increase", diagnosis is not None and not followup,
         "Resolve deferred cases, annotation gaps or unresolved review before preparing a retrieval intervention."),
        ("repair_retrieval_reproducibility", None, None, "increase", support_probe is not None and support_probe["reproducibility"]["value"] == 0,
         "The fixed diagnostic repeats disagree. Inspect their retained receipts; do not infer a support comparison or prepare a decision pilot."),
        ("prepare_control_exchange_decision_pilot", None, None, "increase", support_probe is not None and support_probe["reproducibility"]["value"] == 1,
         "The fixed two-clause diagnostic is complete. Prepare one separately bounded control/value-exchange decision pilot regardless of support recovery; no payment, control action or quality improvement follows from this result."),
        ("build_retrieval_baseline", "retrieval_baseline_reproducibility", 1, "increase", report.get("actual_retrieval") is None and ready is None and diagnosis is None and support_probe is None and pilot is None,
         "Representation, assertion, manifest, graph-operation and output materialization probes pass. Build a source-backed reproducible retrieval baseline (Packet C); retrieval_baseline_reproducibility remains unmeasured."),
    ]
    actual = report.get("actual_retrieval")
    if actual is not None:
        if actual.get("status") != "completed":
            raise ValueError("Actual retrieval must be validated before choosing a successor")
        quality = actual["quality"]["runs"][0]
        coverage = actual.get("schema_version") == 3 and actual.get("phase") == "evaluation"
        coverage_metric = "complete_support_rate_at_k" if coverage else "gold_span_recall_at_k"
        at_one = quality["metrics"][coverage_metric]["1"]["value"]
        at_five = quality["metrics"][coverage_metric]["5"]["value"]
        gap = at_one is not None and at_five is not None and (at_one < 1 or at_five < 1)
        comparison = actual.get("comparison")
        completed_comparison = actual.get("schema_version") == 2 and comparison is not None and comparison.get("kind") == "fixed-raw-html-v1"
        metric = "retrieval_gold_span_recall_at_5" if at_five is not None and at_five < 1 else "retrieval_gold_span_recall_at_1"
        choices.extend([
            ("repair_retrieval_reproducibility", "retrieval_baseline_reproducibility", 1, "increase",
             actual["reproducibility"]["value"] != 1,
             "Valid repeated retrieval runs disagree within an arm; inspect projections, ordered results and per-query evaluation before reporting a comparison delta."),
            ("inspect_fresh_support_failures", "retrieval_complete_support_rate_at_5", None, "increase", coverage and at_five is not None and at_five < 1,
             "Fresh reproduced coverage lacks a complete support bundle for some questions. Inspect retained evidence and returned windows; do not tune recipes or rewrite frozen labels."),
            ("prepare_answerability_evidence_gaps", "retrieval_unsupported_query_retrieval_rate_at_5", None, "decrease", coverage,
             "Fresh reproduced support is covered. Document unsupported hit patterns and unmeasured entity families before any separately scoped answerability method or new evidence acquisition."),
            ("prepare_retrieval_representation_comparison", metric, None, "increase", not coverage and gap and not completed_comparison,
             "Actual development retrieval misses required support or ranks it below first place. Separate indexing recipe from source/gold/scoring identity, then predeclare a bounded source-span-preserving representation comparator. No quality floor is inferred."),
            ("prepare_retrieval_coverage_evaluation", "retrieval_unsupported_query_retrieval_rate_at_5", None, "decrease", True,
             "The fixed representation comparison is complete; retain the raw baseline and predeclare fresh-question coverage/answerability evaluation regardless of gain, tie or regression. Do not repeat recipe tuning on visible gold." if completed_comparison else
             "The reproduced development baseline has no measured support-ranking gap. Predeclare unseen-query coverage and answerability evaluation; unsupported lexical matches are not generated-answer hallucinations."),
        ])
    ranked = [{"action": a, "metric": metric, "observed": _metric_value(report, metric), "target": target,
               "direction": direction, "eligible": eligible, "reason": reason,
               "estimated_success_probability": None, "estimated_cost": None}
              for a, metric, target, direction, eligible, reason in choices]
    chosen = next(c for c in ranked if c["eligible"])
    if (pilot is not None and pilot["phase"] in {decision_diagnosis.PHASE, *dated_delivery.PHASES, public_map_assessment.PHASE, *navigation_assessment.PHASES}
            and chosen["action"] != pilot["next_step"]["action"]):
        # Preserve the semantic task when an enclosing fixture/probe fails.
        # assess retains the actual request/claim and queues operational
        # diagnosis, allowing the verified full-diagnostic continuation.
        raise ValueError("Decision diagnosis cannot complete while an enclosing conformance check requires "
                         + chosen["action"])
    decision = {"id": f"{run_key}:next", "state": "queued", **chosen,
            "family": worst if chosen["action"] == "repair_weakest_entity_family" else None,
            "selection_rule": "existing integrity and conformance priorities, then missing or unreproduced actual retrieval, then measured support-ranking and coverage gaps",
            "forecast_kind": "target and directional hypothesis; probability and cost unestimated",
            "candidate_actions": ranked, "scale_change_allowed": False}
    if ready is not None and chosen["action"] == "execute_fresh_coverage_baseline":
        decision.update(measurement_contract_hash=ready["measurement_contract_identity"]["hash"],
            candidate_algorithm_hash=ready["candidate_identity"]["algorithm_hash"],
            evidence={"study_id": ready["study_id"], "freeze": ready["preparation"]["freeze"],
                "reference_terminal": ready["preparation"]["reference_terminal"],
                "run_keys": ready["preparation"]["run_keys"], "indexing_recipe": retrieval_contracts.RAW_RECIPE,
                "counts": ready["preparation"]["counts"], "quality": "unmeasured"})
    if diagnosis is not None and chosen["action"] in {"prepare_focused_support_followup", "clarify_support_diagnosis"}:
        decision["evidence"] = {"diagnosis_id": diagnosis["diagnosis_id"], "study_id": diagnosis["study_id"],
            "origin": diagnosis["origin"], "machine_findings_hash": diagnosis["machine_findings"]["hash"],
            "semantic_review_hash": diagnosis["semantic_review"]["artifact_hash"],
            "focus_question_ids": diagnosis["machine_findings"]["focus_question_ids"],
            "deferred_question_ids": diagnosis["machine_findings"]["deferred_question_ids"],
            "cases": [{"question_id": case["question_id"], "category": case["category"]}
                for case in diagnosis["semantic_review"]["cases"]], "quality": "unmeasured"}
    if support_probe is not None and chosen["action"] in {"prepare_control_exchange_decision_pilot", "repair_retrieval_reproducibility"}:
        decision["evidence"] = {"study_id": support_probe["study_id"], "origin": support_probe["origin"],
            "bindings": support_probe["bindings"], "reproducibility": support_probe["reproducibility"],
            "assessment_identity": support_probe["assessment_identity"],
            "scope": "Fixed visible-case diagnostic with two top-five selections; no cohort quality or adoption claim"}
    if pilot is not None and chosen["action"] in {"repair_decision_pilot", "prepare_fresh_decision_comparison",
                                                "prepare_prospective_decision_shadow", "investigate_decision_information_limits",
                                                "repair_decision_information_diagnosis", "review_unresolved_decision_evidence",
                                                "prepare_dated_evidence_quality_protocol"}:
        decision["evidence"] = {"study_id": pilot["study_id"], "origin": pilot["origin"],
            "assessment_identity": pilot["assessment_identity"], "checks": pilot["checks"],
            "phase": pilot["phase"],
            "scope": ("Retained-evidence diagnosis of the original 96 attempts; no new candidate execution, quality improvement or live authority"
                      if pilot["phase"] == decision_diagnosis.PHASE else
                      "One fixed24-case exploratory batch; descriptive research triage only, no adoption, live authority or automatic repeat"
                      if pilot["phase"] == "fresh_comparison" else
                      "Twelve exposed synthetic cases; useful development evidence, not representative capability or live authority")}
        if pilot["phase"] == decision_diagnosis.PHASE:
            decision["evidence"].update(evidence_origin=pilot["evidence_origin"],
                                        queue_parent=pilot["queue_parent"], ancestry=pilot["ancestry"])
    if pilot is not None and pilot["phase"] in dated_delivery.PHASES:
        decision["evidence"] = {"study_id": pilot["study_id"], "origin": pilot["origin"],
            "assessment_identity": pilot["assessment_identity"], "checks": pilot["checks"],
            "phase": pilot["phase"], "evidence_origin": pilot["evidence_origin"],
            "queue_parent": pilot["queue_parent"], "ancestry": pilot["ancestry"],
            "scope": "Versioned local delivery preparation, registration or retained check; no predictive lift, external witness or live authority"}
    if pilot is not None and (pilot["phase"] == public_map_assessment.PHASE or pilot["phase"] in navigation_assessment.PHASES):
        decision["evidence"] = {key: pilot[key] for key in ("study_id", "origin", "assessment_identity", "checks", "phase", "evidence_origin", "queue_parent", "ancestry", "scope")}
    if actual is not None and chosen["metric"] is not None and chosen["metric"].startswith("retrieval_"):
        decision["measurement_contract_hash"] = actual["measurement_contract_identity"]["hash"]
        decision["candidate_hash"] = actual["candidate_identity"]["hash"]
        decision["evidence"] = {
            "study_id": actual["study_id"],
            coverage_metric: quality["metrics"][coverage_metric],
            "unsupported_query_retrieval_rate_at_5": quality["metrics"]["unsupported_query_retrieval_rate_at_5"],
            "support_gap_query_ids": [row["query_id"] for row in quality["per_case"]
                if row["answerability"] == "answerable" and (not row["complete_support_at_k"]["5"] if coverage else row["gold_span_recall_at_k"]["1"]["value"] < 1)],
        }
        if coverage:
            decision["evidence"].update(coverage=actual["coverage"], families=actual["preparation"]["families"])
        if actual.get("comparison") is not None:
            decision["evidence"]["comparison"] = {key: actual["comparison"][key] for key in
                ("kind", "status", "delta", "operational_baseline", "adoption", "continuation")}
    return decision


def _metric_value(report, metric):
    actual = report.get("actual_retrieval")
    if actual is not None:
        if metric == "retrieval_baseline_reproducibility":
            return actual["reproducibility"]["value"]
        if actual["reproducibility"]["value"] != 1 and metric and metric.startswith("retrieval_"):
            return None
        metrics = actual["quality"]["runs"][0]["metrics"]
        if metric in {"retrieval_gold_span_recall_at_1", "retrieval_gold_span_recall_at_5"}:
            values = metrics.get("gold_span_recall_at_k")
            return None if values is None else values[metric[-1]]["value"]
        if metric == "retrieval_complete_support_rate_at_5":
            values = metrics.get("complete_support_rate_at_k")
            return None if values is None else values["5"]["value"]
        if metric == "retrieval_unsupported_query_retrieval_rate_at_5":
            return metrics["unsupported_query_retrieval_rate_at_5"]["value"]
    return report["metrics"].get(metric)


def _forecast_result(previous, report, previous_manifest, current_manifest):
    metric = previous.get("metric")
    if metric is None:
        return {"status": "unmeasured", "step_id": previous["id"], "metric": None}
    actual_metric = metric is not None and metric.startswith("retrieval_")
    if previous_manifest is not None and not actual_metric:
        changed = [name for name in ("suite", "evaluator", "policy", "assertions", "source_span_probe", "store", "manifests", "manifest_probe", "transforms", "transformation_probe", "graph_views", "graph_view_probe", "materialization", "materialization_probe")
                   if previous_manifest.get(name) != current_manifest.get(name)]
        if changed:
            return {"status": "incomparable_contract_change", "changed_inputs": changed,
                    "step_id": previous["id"], "metric": metric}
    if actual_metric:
        actual = report.get("actual_retrieval")
        previous_contract = previous.get("measurement_contract_hash")
        current_contract = None if actual is None else actual["measurement_contract_identity"]["hash"]
        if previous_contract is None or current_contract is None:
            return {"status": "unmeasured", "step_id": previous["id"], "metric": metric}
        if previous_contract != current_contract:
            return {"status": "incomparable_contract_change", "changed_inputs": ["retrieval_measurement_contract"],
                    "step_id": previous["id"], "metric": metric}
    observed = _metric_value(report, metric)
    if previous_manifest is None or metric is None or observed is None:
        return {"status": "unmeasured", "step_id": previous["id"], "metric": metric}
    baseline = previous.get("observed")
    return {"status": "measured", "step_id": previous["id"], "metric": metric,
            "baseline": baseline, "observed": observed,
            "change": None if baseline is None else observed - baseline,
            "target_met": (None if previous.get("target") is None else
                           observed <= previous["target"] if previous["direction"] == "decrease" else observed >= previous["target"]),
            "interpretation": "Descriptive change; no causal attribution to the queued action"}


def _implementation_inputs():
    pinned_codes = {module.__name__: code for module, _, _, code, _ in _IMPLEMENTATIONS.values()}
    for name, (module, path, captured, executing_code, dependencies) in _IMPLEMENTATIONS.items():
        if module.IMPLEMENTATION_CODE is not executing_code or module.IMPLEMENTATION_SOURCE != captured:
            raise ValueError(f"Implementation reloaded since controller import: {name}; use a fresh process after review")
        if (len(captured) > MAX_BYTES or path.is_symlink() or not path.is_file()
                or path.stat().st_size != len(captured)):
            raise ValueError(f"Implementation source changed since import: {name}; use a fresh process after review")
        with path.open("rb") as stream:
            if stream.read(len(captured) + 1) != captured:
                raise ValueError(f"Implementation source changed since import: {name}; use a fresh process after review")
        try:
            compiled_code = compile(captured, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize)
        except (SyntaxError, ValueError) as error:
            raise ValueError(f"Captured implementation cannot be compiled: {name}; use a fresh reviewed process") from error
        if executing_code != compiled_code:
            raise ValueError(f"Executing implementation does not match source: {name}; discard stale bytecode and use a fresh process")
        # A dependency may have reloaded before the controller was imported,
        # leaving this module's older from-import bindings in use.
        for dependency_name, dependency_code in dependencies:
            if pinned_codes.get(dependency_name) is not dependency_code:
                raise ValueError(f"Implementation dependency reloaded: {name} -> {dependency_name}; use a fresh process")
    return {name: captured for name, (_, _, captured, _, _) in _IMPLEMENTATIONS.items()}


def _assessment_inputs(policy_path, suite_path, candidate):
    implementation = _implementation_inputs()
    policy, policy_bytes = _load(policy_path)
    suite, suite_bytes = _load(suite_path)
    validate_policy(policy)
    validate_suite(suite)
    if {c["family"] for c in suite["cases"]} != FAMILIES:
        raise ValueError("Suite must include exactly the seven declared entity families")
    if candidate in {"reference", "degraded"}:
        output = reference_candidate(suite) if candidate == "reference" else degraded_candidate(suite)
        candidate_bytes = canonical(output).encode()
    else:
        output, candidate_bytes = _load(candidate)
    inputs = {"policy": policy_bytes, "suite": suite_bytes, "candidate": candidate_bytes, **implementation}
    return policy, suite, output, inputs


def assess(ledger, policy_path, suite_path, candidate, run_key, *, after_step="initial", completed_work="",
           retrieval_study_path=None, _prepared_retrieval_path=None, decision_study_path=None):
    if sys._getframe().f_code is not assess.__code__:
        raise ValueError("Stale assessment callable after reload; use a fresh process")
    if type(ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class; use a fresh process")
    if not isinstance(run_key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key):
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    if not isinstance(completed_work, str) or not completed_work.strip() or len(completed_work) > 8000:
        raise ValueError("Describe the work actually completed; assessment is not proof of task completion")
    if decision_study_path is not None and (retrieval_study_path is not None or _prepared_retrieval_path is not None):
        raise ValueError("Assess one decision or retrieval study per transition")
    policy, suite, output, inputs = _assessment_inputs(policy_path, suite_path, candidate)
    preparation_started = time.monotonic() if retrieval_study_path is not None or _prepared_retrieval_path is not None or decision_study_path is not None else None
    if _prepared_retrieval_path is not None:
        try:
            preparation = _read_retrieval_preparation(_prepared_retrieval_path)
        except (ValueError, OSError, TypeError, KeyError, RuntimeError) as error:
            preparation = _failed_retrieval_preparation(_prepared_retrieval_path, error)
    else:
        preparation = _prepare_retrieval(retrieval_study_path, policy, ledger.root)
    inputs.update(_retrieval_inputs(preparation))
    decision_preparation = _prepare_decision(decision_study_path)
    inputs.update(_decision_inputs(decision_preparation))
    manifest = {name: digest(raw) for name, raw in inputs.items()}
    request = {"manifest": manifest, "after_step": after_step, "completed_work": completed_work}
    events = _checked_events(ledger)
    prior = [e for e in events if e["kind"] in TRANSITIONS and e["body"]["run_key"] == run_key]
    if prior:
        expected_request_hash = os.environ.get("EPIPHYSICS_EXPECTED_REQUEST_SHA256")
        if expected_request_hash is not None and digest(canonical(request).encode()) != expected_request_hash:
            raise ValueError("Assessment inputs changed from the dispatcher's prepared request")
        if prior[0]["body"]["request"] != request:
            raise ValueError("Run key already used with different inputs or completion description")
        return prior[0]["body"]
    current = status(ledger)
    if current["unfinished_runs"]:
        raise ValueError("Interrupted run exists; inspect it before continuing (no blind replay)")
    if current["next_step"]["id"] != after_step:
        raise ValueError("Stale predecessor; read status and use the currently queued step")
    previous = current["next_step"]
    if decision_preparation is None:
        _check_decision_origin(None, events, after_step)
    previous_manifest = (ledger.get(current["last_transition"])["body"]["request"]["manifest"]
                         if current["last_transition"] else None)
    origin_error = None
    try:
        _check_diagnosis_origin(preparation, events, after_step)
        _check_decision_origin(decision_preparation, events, after_step)
    except ValueError as error:
        if _information_context(decision_preparation, events):
            raise
        origin_error = str(error)
    def validate_claim(_):
        nonlocal origin_error
        _implementation_inputs()
        if preparation is not None and preparation["error"] is None:
            retrieval_assessment.check_prepared_retrieval_study(preparation["prepared"])
        if decision_preparation is not None and decision_preparation["error"] is None:
            decision_assessment.check_prepared_decision_study(decision_preparation["prepared"])
        locked_events = _checked_events(ledger)
        if any(e["kind"] in TRANSITIONS | {"improvement_started"} and e["body"].get("run_key") == run_key
               for e in locked_events):
            raise ValueError("Run key was already claimed; read its recorded result before continuing")
        transitions = [e for e in locked_events if e["kind"] in TRANSITIONS]
        actual = transitions[-1]["body"]["next_step"]["id"] if transitions else "initial"
        if actual != after_step:
            raise ValueError("Another worker advanced the queue")
        # Invalid current-step evidence follows the usual durable failure path;
        # stale ownership above still refuses before claiming any work.
        try:
            _check_diagnosis_origin(preparation, locked_events, after_step)
            _check_decision_origin(decision_preparation, locked_events, after_step)
        except ValueError as error:
            if _information_context(decision_preparation, locked_events):
                raise
            origin_error = str(error)
    ledger.append("improvement_started", {"run_key": run_key, "request": request,
        "claimed_step": previous, "worker": {"dispatch_id": os.environ.get("EPIPHYSICS_DISPATCH_ID"),
                                             "pid": os.getpid()}},
        f"improvement:claim:{digest(after_step.encode())}",
        exclusive=True, validate=validate_claim)
    started = preparation_started if preparation_started is not None else time.monotonic()
    try:
        captures = {}
        for name, raw in inputs.items():
            event = ledger.capture(f"improvement-input:{name}", raw, media_type="text/plain",
                                   event_id=f"improvement:{run_key}:input:{name}")
            captures[name] = event["id"]
        actual = None
        decision_actual = None
        decision_diagnostic_seconds = None
        delivery_verification_seconds = None
        map_check_seconds = None
        navigation_check_seconds = None
        if origin_error is not None:
            raise ValueError(origin_error)
        expected_request_hash = os.environ.get("EPIPHYSICS_EXPECTED_REQUEST_SHA256")
        if expected_request_hash is not None and digest(canonical(request).encode()) != expected_request_hash:
            raise ValueError("Assessment inputs changed from the dispatcher's prepared request")
        if decision_preparation is not None:
            if decision_preparation["error"] is not None:
                raise ValueError("Invalid supplied decision study: " + decision_preparation["error"]["message"])
            if origin_error is not None:
                raise ValueError(origin_error)
            _check_decision_origin(decision_preparation, _checked_events(ledger), after_step)
            decision_measured = decision_assessment.assess_prepared_decision_study(decision_preparation["prepared"])
            decision_actual = decision_measured["report"]
            if decision_actual.get("phase") == decision_diagnosis.PHASE:
                decision_diagnostic_seconds = decision_measured.get("actual_resources", {}).get("diagnostic_elapsed_seconds")
                if decision_diagnostic_seconds is not None and (
                        type(decision_diagnostic_seconds) not in (int, float)
                        or not math.isfinite(decision_diagnostic_seconds)
                        or not 0 <= decision_diagnostic_seconds <= decision_diagnosis.MAX_SECONDS):
                    raise ValueError("Invalid diagnostic elapsed-time receipt")
            if decision_actual.get("phase") in dated_delivery.PHASES:
                delivery_verification_seconds = decision_measured.get("actual_resources", {}).get("first_verification_elapsed_seconds")
                if delivery_verification_seconds is not None and (
                        type(delivery_verification_seconds) not in (int, float)
                        or not math.isfinite(delivery_verification_seconds)
                        or not 0 <= delivery_verification_seconds <= dated_delivery.MAX_SECONDS):
                    raise ValueError("Invalid delivery verification elapsed-time receipt")
            if decision_actual.get("phase") == public_map_assessment.PHASE:
                map_check_seconds = decision_measured.get("actual_resources", {}).get("retained_check_elapsed_seconds")
                if (type(map_check_seconds) not in (int, float) or not math.isfinite(map_check_seconds)
                        or not 0 <= map_check_seconds <= public_map_assessment.MAX_SECONDS):
                    raise ValueError("Invalid public-map retained-check elapsed-time receipt")
            if decision_actual.get("phase") in navigation_assessment.PHASES:
                navigation_check_seconds = decision_measured.get("actual_resources", {}).get("retained_navigation_elapsed_seconds")
                if (type(navigation_check_seconds) not in (int, float) or not math.isfinite(navigation_check_seconds)
                        or not 0 <= navigation_check_seconds <= navigation_assessment.MAX_SECONDS):
                    raise ValueError("Invalid retained navigation elapsed-time receipt")
            for role, raw in decision_measured["artifacts"].items():
                if role in decision_preparation["prepared"]["artifacts"]:
                    if raw != decision_preparation["prepared"]["artifacts"][role]:
                        raise ValueError("Decision validation changed a captured input artifact")
                    continue
                name = "decision-result:" + role
                event = ledger.capture("improvement-input:" + name, raw, media_type="application/octet-stream",
                                       event_id=f"improvement:{run_key}:input:{name}")
                captures[name] = event["id"]
        if preparation is not None:
            if preparation["error"] is not None:
                raise ValueError("Invalid supplied retrieval study: " + preparation["error"]["message"])
            if origin_error is not None:
                raise ValueError(origin_error)
            _check_diagnosis_origin(preparation, _checked_events(ledger), after_step)
            retrieval_assessment.check_prepared_retrieval_study(preparation["prepared"])
            if preparation["prepared"]["artifacts"].get("declared_contract") != canonical(policy.get("retrieval_study")).encode():
                raise ValueError("Prepared retrieval contract does not match the assessment policy")
            measured = retrieval_assessment.assess_prepared_retrieval_study(preparation["prepared"])
            actual = measured["report"]
            for role, raw in measured["artifacts"].items():
                if role in preparation["prepared"]["artifacts"]:
                    if raw != preparation["prepared"]["artifacts"][role]:
                        raise ValueError("Retrieval evaluation changed a captured input artifact")
                    continue
                name = f"retrieval-result:{role}"
                event = ledger.capture(f"improvement-input:{name}", raw, media_type="application/octet-stream",
                                       event_id=f"improvement:{run_key}:input:{name}")
                captures[name] = event["id"]
        report = evaluate(suite, output)
        probe = run_source_span_checks()
        report["source_span_checks"] = probe
        report["metrics"].update(probe["metrics"])
        manifest_probe = run_manifest_checks()
        report["manifest_checks"] = manifest_probe
        report["metrics"].update(manifest_probe["metrics"])
        transformation_probe = run_transformation_checks()
        report["transformation_checks"] = transformation_probe
        report["metrics"].update(transformation_probe["metrics"])
        graph_view_probe = run_graph_view_checks()
        report["graph_view_checks"] = graph_view_probe
        report["metrics"].update(graph_view_probe["metrics"])
        materialization_probe = run_materialization_checks()
        report["materialization_checks"] = materialization_probe
        report["metrics"].update(materialization_probe["metrics"])
        if actual is not None:
            if actual.get("schema_version") == 3 and actual.get("phase") == "support_probe":
                report["support_probe"] = actual
            elif actual.get("schema_version") == 3 and actual.get("phase") == "support_diagnosis":
                report["support_diagnosis"] = actual
            elif actual.get("schema_version") == 3 and actual.get("phase") == "preparation":
                report["coverage_preparation"] = actual
            else:
                report["actual_retrieval"] = actual
                report["metrics"]["retrieval_baseline_reproducibility"] = actual["reproducibility"]["value"]
            retrieval_assessment.check_prepared_retrieval_study(preparation["prepared"])
        if decision_actual is not None:
            report["decision_pilot"] = decision_actual
        if {name: digest(raw) for name, raw in inputs.items()} != manifest:
            raise ValueError("Assessment input bytes changed after claim")
        _implementation_inputs()
        elapsed = time.monotonic() - started
        if elapsed > policy["max_assessment_seconds"]:
            raise ValueError("Assessment exceeded its elapsed-time acceptance budget")
        if decision_diagnostic_seconds is not None and decision_diagnostic_seconds > elapsed:
            raise ValueError("Diagnostic elapsed time exceeds its enclosing assessment duration")
        if delivery_verification_seconds is not None and delivery_verification_seconds > elapsed:
            raise ValueError("Delivery verification elapsed time exceeds its enclosing assessment duration")
        if map_check_seconds is not None and map_check_seconds > elapsed:
            raise ValueError("Public-map retained-check elapsed time exceeds its enclosing assessment duration")
        if navigation_check_seconds is not None and navigation_check_seconds > elapsed:
            raise ValueError("Navigation check exceeds enclosing assessment duration")
        result = {"run_key": run_key, "request": request, "input_observations": captures,
                  "stage": "offline_fixture", "result": "assessed", "report": report,
                  "prior_action_outcome": _forecast_result(previous, report, previous_manifest, manifest),
                  "next_step": select_next(report, run_key),
                  "actual_resources": {"elapsed_seconds": elapsed, "model_calls": 0, "external_spend": 0},
                  "scope": ("Synthetic conformance plus prospective or retained six-case textual navigation; no candidate execution by assessor, human-use or comparative benefit claim. "
                            if decision_actual is not None and decision_actual.get("phase") in navigation_assessment.PHASES else
                            "Synthetic conformance checks plus retained static public-map preparation; no external process execution by the assessor, browser, human-use, deployment or predictive improvement result. "
                            if decision_actual is not None and decision_actual.get("phase") == public_map_assessment.PHASE else
                            "Synthetic conformance checks plus a checked dated artifact-delivery phase; preparation and registration have no delivery-quality result, and retained checks imply no general predictive gain or live control. "
                            if decision_actual is not None and decision_actual.get("phase") in dated_delivery.PHASES else
                            "Synthetic conformance checks plus checked diagnosis of the 96 retained decision attempts; no new candidate execution, predictive improvement or live control claim. "
                            if decision_actual is not None and decision_actual.get("phase") == decision_diagnosis.PHASE else
                            "Synthetic conformance checks plus one validated fixed24-case fresh exploratory comparison; no automatic repeat, representative capability or live control claim. "
                            if decision_actual is not None and decision_actual.get("phase") == "fresh_comparison" else
                            "Synthetic conformance checks plus one validated exposed decision-development comparison; no representative capability or live control claim. "
                            if decision_actual is not None else
                            "Synthetic conformance checks plus one checked two-clause development diagnostic; no new cohort quality, adoption or control-action claim. "
                            if actual is not None and actual.get("phase") == "support_probe" else
                            "Synthetic conformance checks plus checked retained support diagnosis; retrieval quality and improvement remain unmeasured. "
                            if actual is not None and actual.get("phase") == "support_diagnosis" else
                            "Synthetic conformance checks plus verified fresh-cohort preparation; retrieval quality remains unmeasured. "
                            if actual is not None and actual.get("phase") == "preparation" else
                            "Synthetic conformance checks plus separately reported validated retrospective development retrieval; no quality improvement or independent execution witness is inferred. "
                            if actual is not None else "Synthetic conformance assessment with fixed local checks; ") + "queued builds, deployment and scale promotion remain supervised"}
        if decision_actual is not None and decision_actual.get("phase") == decision_diagnosis.PHASE:
            result["actual_resources"].update(
                first_diagnostic_elapsed_seconds=decision_diagnostic_seconds,
                diagnostic_timing_scope="First checked diagnosis only, nested within assessment elapsed time; completion revalidation excluded")
        if decision_actual is not None and decision_actual.get("phase") in dated_delivery.PHASES:
            result["actual_resources"].update(
                first_verification_elapsed_seconds=delivery_verification_seconds,
                verification_timing_scope="First retained-inventory verification only, nested in assessment; completion revalidation excluded; null when no verifier ran")
        if decision_actual is not None and decision_actual.get("phase") == public_map_assessment.PHASE:
            result["actual_resources"].update(first_retained_map_check_elapsed_seconds=map_check_seconds,
                public_map_timing_scope="First retained-only map check, nested in assessment; completion revalidation excluded; no external program invocation")
        if decision_actual is not None and decision_actual.get("phase") in navigation_assessment.PHASES:
            result["actual_resources"].update(first_retained_navigation_check_elapsed_seconds=navigation_check_seconds,
                navigation_timing_scope="First retained check nested in assessment; excludes completion revalidation; no external program invocation")
        if actual is not None:
            identity = {"input_manifest": dict(manifest),
                        "retrieval_assessment_hash": actual["assessment_identity"]["hash"]}
            result["assessment_identity"] = {**identity, "hash": digest(canonical(identity).encode())}
        if decision_actual is not None:
            identity = {"input_manifest": dict(manifest), "decision_assessment_hash": decision_actual["assessment_identity"]["hash"]}
            result["assessment_identity"] = {**identity, "hash": digest(canonical(identity).encode())}
        # Completion and successor are one atomic ledger event, never two separate writes.
        expected_result = canonical(result)
        def validate_completion(recorded_at):
            _implementation_inputs()
            if {name: digest(raw) for name, raw in inputs.items()} != manifest:
                raise ValueError("Assessment inputs changed before completion")
            if preparation is not None:
                retrieval_assessment.check_prepared_retrieval_study(preparation["prepared"])
            if decision_actual is not None:
                _check_decision_origin(decision_preparation, _checked_events(ledger), after_step)
                checked_decision = decision_assessment.assess_prepared_decision_study(decision_preparation["prepared"])["report"]
                if canonical(checked_decision) != canonical(decision_actual):
                    raise ValueError("Decision evidence changed before completion")
                if time.monotonic() - started > policy["max_assessment_seconds"]:
                    raise ValueError("Decision revalidation exceeded the assessment elapsed-time budget")
            if actual is not None and actual.get("phase") in ("support_diagnosis", "support_probe"):
                _check_diagnosis_origin(preparation, _checked_events(ledger), after_step)
                checked_again = retrieval_assessment.assess_prepared_retrieval_study(preparation["prepared"])["report"]
                if canonical(checked_again) != canonical(actual):
                    raise ValueError("Support diagnosis or probe changed before completion")
                if time.monotonic() - started > policy["max_assessment_seconds"]:
                    raise ValueError("Diagnosis or probe revalidation exceeded the assessment elapsed-time budget")
            if canonical(result) != expected_result:
                raise ValueError("Assessment result changed before completion")
            if decision_actual is not None and decision_actual.get("phase") == navigation_assessment.CHECK:
                navigation_assessment.validate_completion(decision_preparation["prepared"], decision_actual,
                    recorded_at, ledger.clock())
        ledger.append("improvement_completed", result, f"improvement:{run_key}:complete",
                      exclusive=True, validate=validate_completion)
        return result
    except Exception as error:
        failed = {"run_key": run_key, "request": request, "result": "failed", "error": type(error).__name__,
                  "message": str(error)[:400], "next_step": {"id": f"{run_key}:diagnose", "state": "queued",
                  "action": "diagnose_failed_assessment", "reason": str(error)[:400], "scale_change_allowed": False}}
        if isinstance(error, navigation_assessment.ClosureDeadlineExceeded):
            failed["next_step"]["action"] = "repair_navigation_execution_contract"
            failed["navigation_closure"] = {"status": "outside_original_budget", "accepted_scores": None,
                "retained_report_observation": captures.get("decision-result:assessment_report"), "retry_allowed": False}
        ledger.append("improvement_failed", failed, f"improvement:{run_key}:failed", exclusive=True)
        return failed


def _recover_reaped_dispatch(store, run_key, dispatch_id, pid, reason):
    """Close only this already-reaped child's unfinished claim, under the ledger lock."""
    ledger = Ledger(store)
    try:
        events = _checked_events(ledger)
        owned = [e for e in events if e["kind"] == "improvement_started"
                 and e["body"].get("run_key") == run_key
                 and e["body"].get("worker") == {"dispatch_id": dispatch_id, "pid": pid}]
        if not owned:
            return "no_owned_claim"
        if any(e["kind"] in TRANSITIONS and e["body"]["run_key"] == run_key for e in events):
            return "already_finished"
        start = owned[0]["body"]
        result = {"run_key": run_key, "request": start["request"], "result": "failed",
                  "error": "WorkerFailure", "message": reason,
                  "worker": {"dispatch_id": dispatch_id, "pid": pid},
                  "next_step": {"id": f"{run_key}:diagnose", "state": "queued",
                                "action": "diagnose_failed_assessment", "reason": reason,
                                "scale_change_allowed": False}}
        def validate_recovery(_):
            if any(e["kind"] in TRANSITIONS and e["body"]["run_key"] == run_key for e in ledger.events()):
                raise ValueError("Run already finished; recovery refused")
        ledger.append("improvement_failed", result, f"improvement:{run_key}:failed",
                      exclusive=True, validate=validate_recovery)
        return "diagnosis_queued"
    finally:
        ledger.close()


def _dispatch_transition(store, run_key, dispatch_id, pid, delivered_result, expected_request):
    """Return a small authoritative receipt for this worker or a verified replay."""
    ledger = Ledger(store)
    try:
        events = _checked_events(ledger)
        owned = any(e["kind"] == "improvement_started" and e["body"].get("run_key") == run_key
                    and e["body"].get("worker") == {"dispatch_id": dispatch_id, "pid": pid} for e in events)
        records = [e for e in events if e["kind"] in TRANSITIONS and e["body"]["run_key"] == run_key]
        if not records:
            return None
        event = records[-1]
        body = event["body"]
        replay_matches = (isinstance(delivered_result, dict)
                          and delivered_result.get("request") == body.get("request")
                          and delivered_result.get("result") == body.get("result"))
        expected_matches = expected_request is not None and expected_request == body.get("request")
        if not owned and not replay_matches and not expected_matches:
            return None
        return {"event_id": event["id"], "event_hash": event["hash"], "kind": event["kind"],
                "run_key": run_key, "result": body["result"],
                "next_step": {key: body["next_step"].get(key) for key in ("id", "action", "state", "scale_change_allowed")}}
    finally:
        ledger.close()


def dispatch(store, policy_path, suite_path, candidate, run_key, *, after_step="initial",
             completed_work="", timeout_seconds=60, retrieval_study_path=None, decision_study_path=None):
    """Spawn one fixed assessment program and persist a bounded process receipt.

    This is process supervision for a trusted local checkout, not a security
    sandbox. Builder agents remain separate workers supervised by the desktop.
    """
    if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60:
        raise ValueError("Worker timeout must be positive and at most 60 seconds")
    if not isinstance(run_key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key):
        raise ValueError("Invalid run key")
    if not isinstance(completed_work, str) or not completed_work.strip() or len(completed_work) > 8000:
        raise ValueError("A nonempty completion description of at most 8000 characters is required")
    if decision_study_path is not None and retrieval_study_path is not None:
        raise ValueError("Dispatch one decision or retrieval study per transition")
    store = Path(store).resolve()
    policy_path, suite_path = str(Path(policy_path).resolve()), str(Path(suite_path).resolve())
    candidate = candidate if candidate in {"reference", "degraded"} else str(Path(candidate).resolve())
    if retrieval_study_path is not None:
        retrieval_study_path = os.path.abspath(retrieval_study_path)
    if decision_study_path is not None:
        decision_study_path = os.path.abspath(decision_study_path)
    # Validate store ownership before launching, and close this connection first.
    ledger = Ledger(store)
    try:
        _checked_events(ledger)
    finally:
        ledger.close()
    expected_request = None
    preparation = None
    try:
        policy, _, _, input_bytes = _assessment_inputs(policy_path, suite_path, candidate)
        preparation = _prepare_retrieval(retrieval_study_path, policy, store)
        input_bytes.update(_retrieval_inputs(preparation))
        input_bytes.update(_decision_inputs(_prepare_decision(decision_study_path)))
        expected_request = {"manifest": {name: digest(raw) for name, raw in input_bytes.items()},
                            "after_step": after_step, "completed_work": completed_work}
    except (ValueError, OSError, TypeError, KeyError):
        # The child reports invalid input through its ordinary exit/output path.
        # Without a manifest, a prior completion cannot be attributed to this request.
        pass
    dispatch_id = uuid.uuid4().hex
    directory = store / "dispatches" / dispatch_id
    directory.mkdir(parents=True, exist_ok=False)
    engine = Path(__file__).resolve().parents[1]
    arguments = [sys.executable, "-s", "-m", "epiphysics.improvement", "--store", str(store), "assess",
                 "--policy", policy_path, "--suite", suite_path, "--candidate", candidate,
                 "--run-key", run_key, "--after-step", after_step, "--completed-work", completed_work]
    environment = {"PATH": os.defpath, "PYTHONPATH": str(engine), "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
                   "PYTHONUTF8": "1", "EPIPHYSICS_DISPATCH_ID": dispatch_id}
    if preparation is not None:
        prepared_path, prepared_hash = _write_retrieval_preparation(directory / "retrieval-input", preparation)
        arguments.extend(["--prepared-retrieval-study", str(prepared_path)])
        environment["EPIPHYSICS_RETRIEVAL_PREPARATION_SHA256"] = prepared_hash
        environment["EPIPHYSICS_EXPECTED_REQUEST_SHA256"] = digest(canonical(expected_request).encode())
    elif retrieval_study_path is not None:
        arguments.extend(["--retrieval-study", retrieval_study_path])
    if decision_study_path is not None:
        arguments.extend(["--decision-study", decision_study_path])
        if expected_request is not None:
            environment["EPIPHYSICS_EXPECTED_REQUEST_SHA256"] = digest(canonical(expected_request).encode())
    receipt = {"schema_version": 1, "dispatch_id": dispatch_id, "run_key": run_key,
               "program": "epiphysics.improvement assess", "started_at": utc_now(), "pid": None,
               "timeout_seconds": timeout_seconds, "output_limit_bytes": MAX_BYTES,
               "cwd": str(engine), "arguments": arguments, "model_calls": 0, "external_spend": 0,
               "assurance": "Local process supervision; timeout enforcement requires the dispatcher to remain alive"}
    output_path = directory / "output.log"
    process = None
    termination = None
    output_bytes = 0
    started = time.monotonic()
    try:
        process = subprocess.Popen(arguments, cwd=engine, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
        receipt["pid"] = process.pid
        (directory / "start.json").write_text(json.dumps(receipt, indent=2) + "\n")
        with output_path.open("xb") as output, selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = timeout_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    termination = "timeout"
                    break
                for key, _ in selector.select(timeout=remaining):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        break
                    allowed = MAX_BYTES - output_bytes
                    output.write(chunk[:allowed])
                    output_bytes += min(len(chunk), allowed)
                    if len(chunk) > allowed:
                        termination = "output_limit"
                        break
                if termination:
                    break
            if termination:
                process.kill()
                process.wait()
            else:
                try:
                    process.wait(timeout=max(0.001, timeout_seconds - (time.monotonic() - started)))
                except subprocess.TimeoutExpired:
                    termination = "timeout"
                    process.kill()
                    process.wait()
    except OSError as error:
        termination = f"dispatch_error: {type(error).__name__}: {error}"
    finally:
        if process:
            if process.poll() is None:
                process.kill()
                process.wait()
            if process.stdout:
                process.stdout.close()
    if not (directory / "start.json").exists():
        (directory / "start.json").write_text(json.dumps(receipt, indent=2) + "\n")
    raw_output = output_path.read_bytes() if output_path.exists() else b""
    result = None
    if process and process.returncode == 0 and termination is None:
        try:
            result = json.loads(raw_output)
            if not isinstance(result, dict) or result.get("run_key") != run_key or result.get("result") != "assessed":
                raise ValueError("Unexpected worker result")
        except (ValueError, UnicodeDecodeError):
            termination = "invalid_worker_output"
    failed = termination is not None or process is None or process.returncode != 0
    recovery = "not_needed"
    if failed and process:
        try:
            recovery = _recover_reaped_dispatch(store, run_key, dispatch_id, process.pid,
                termination or f"Worker exited with code {process.returncode}")
        except (ValueError, OSError) as error:
            recovery = f"recovery_refused: {error}"
    authoritative = None
    if process:
        try:
            authoritative = _dispatch_transition(store, run_key, dispatch_id, process.pid, result, expected_request)
        except (ValueError, OSError) as error:
            recovery = f"authoritative_read_refused: {error}"
            failed = True
            termination = termination or "authoritative_read_failed"
    if not failed and (authoritative is None or authoritative["kind"] != "improvement_completed"):
        failed = True
        termination = "missing_authoritative_completion"
    assessment_status = ("completed" if authoritative and authoritative["kind"] == "improvement_completed"
                         else "failed" if authoritative else "not_confirmed")
    dispatch_result = ("assessment_completed_delivery_failed" if failed and assessment_status == "completed"
                       else "failed" if failed else "assessed")
    receipt.update(ended_at=utc_now(), elapsed_seconds=time.monotonic() - started,
        returncode=None if process is None else process.returncode, termination=termination,
        output_bytes=len(raw_output), output_sha256=digest(raw_output), recovery=recovery,
        result=dispatch_result, delivery_status="failed" if failed else "delivered",
        assessment_status=assessment_status,
        authoritative_transition_id=authoritative["event_id"] if authoritative else None,
        receipt_directory=str(directory))
    (directory / "finish.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return {"result": receipt["result"], "dispatch": receipt, "assessment": result,
            "authoritative_transition": authoritative}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    for command in ("assess", "dispatch"):
        run = commands.add_parser(command)
        run.add_argument("--policy", required=True)
        run.add_argument("--suite", required=True)
        run.add_argument("--candidate", required=True, help="reference, degraded, or a local JSON candidate output")
        run.add_argument("--run-key", required=True)
        run.add_argument("--after-step", default="initial")
        run.add_argument("--completed-work", required=True)
        run.add_argument("--retrieval-study", help="Local bounded retrieval study request; independently validates two completed runs")
        run.add_argument("--decision-study", help="Validate retained owned decision-development results without rerunning candidates")
        if command == "dispatch":
            run.add_argument("--timeout-seconds", type=float, default=60)
        else:
            run.add_argument("--prepared-retrieval-study", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    ledger = None
    try:
        if args.command == "dispatch":
            result = dispatch(args.store, args.policy, args.suite, args.candidate, args.run_key,
                after_step=args.after_step, completed_work=args.completed_work, timeout_seconds=args.timeout_seconds,
                retrieval_study_path=args.retrieval_study, decision_study_path=args.decision_study)
        else:
            ledger = Ledger(args.store)
            result = status(ledger) if args.command == "status" else assess(ledger, args.policy, args.suite, args.candidate,
                args.run_key, after_step=args.after_step, completed_work=args.completed_work,
                retrieval_study_path=args.retrieval_study, _prepared_retrieval_path=args.prepared_retrieval_study,
                decision_study_path=args.decision_study)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 2 if result.get("result") in {"failed", "assessment_completed_delivery_failed"} else 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    finally:
        if ledger:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
