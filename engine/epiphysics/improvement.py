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

from . import assertions, graph_view_checks, graph_views, manifest_checks, manifests, materialization, materialization_checks, representation_checks, retrieval, retrieval_assessment, retrieval_contracts, retrieval_coverage, retrieval_evaluation, retrieval_indexing, source_span_checks, store, transformation_checks, transforms
from .store import Ledger, canonical, digest, utc_now
from .representation_checks import FAMILIES, evaluate, reference_candidate, degraded_candidate, validate_suite
from .source_span_checks import run_source_span_checks
from .manifest_checks import run_manifest_checks
from .transformation_checks import run_transformation_checks
from .graph_view_checks import run_graph_view_checks
from .materialization_checks import run_materialization_checks

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE)
    for module in (assertions, manifests, manifest_checks, representation_checks, source_span_checks, store, transforms, transformation_checks, graph_views, graph_view_checks, materialization, materialization_checks, retrieval, retrieval_evaluation, retrieval_assessment, retrieval_contracts, retrieval_indexing, retrieval_coverage)
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
    ready = report.get("coverage_preparation")
    if ready is not None and (ready.get("schema_version") != 3 or ready.get("phase") != "preparation" or ready.get("status") != "ready"):
        raise ValueError("Coverage readiness must be validated before choosing a successor")
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
        ("execute_fresh_coverage_baseline", None, None, "increase", ready is not None,
         "Reviewed fresh coverage inputs are frozen. Execute the two declared raw-baseline runs; retrieval quality remains unmeasured."),
        ("build_retrieval_baseline", "retrieval_baseline_reproducibility", 1, "increase", report.get("actual_retrieval") is None and ready is None,
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
           retrieval_study_path=None, _prepared_retrieval_path=None):
    if sys._getframe().f_code is not assess.__code__:
        raise ValueError("Stale assessment callable after reload; use a fresh process")
    if type(ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class; use a fresh process")
    if not isinstance(run_key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key):
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    if not isinstance(completed_work, str) or not completed_work.strip() or len(completed_work) > 8000:
        raise ValueError("Describe the work actually completed; assessment is not proof of task completion")
    policy, suite, output, inputs = _assessment_inputs(policy_path, suite_path, candidate)
    preparation_started = time.monotonic() if retrieval_study_path is not None or _prepared_retrieval_path is not None else None
    if _prepared_retrieval_path is not None:
        try:
            preparation = _read_retrieval_preparation(_prepared_retrieval_path)
        except (ValueError, OSError, TypeError, KeyError, RuntimeError) as error:
            preparation = _failed_retrieval_preparation(_prepared_retrieval_path, error)
    else:
        preparation = _prepare_retrieval(retrieval_study_path, policy, ledger.root)
    inputs.update(_retrieval_inputs(preparation))
    manifest = {name: digest(raw) for name, raw in inputs.items()}
    request = {"manifest": manifest, "after_step": after_step, "completed_work": completed_work}
    events = _checked_events(ledger)
    prior = [e for e in events if e["kind"] in TRANSITIONS and e["body"]["run_key"] == run_key]
    if prior:
        if prior[0]["body"]["request"] != request:
            raise ValueError("Run key already used with different inputs or completion description")
        return prior[0]["body"]
    current = status(ledger)
    if current["unfinished_runs"]:
        raise ValueError("Interrupted run exists; inspect it before continuing (no blind replay)")
    if current["next_step"]["id"] != after_step:
        raise ValueError("Stale predecessor; read status and use the currently queued step")
    previous = current["next_step"]
    previous_manifest = (ledger.get(current["last_transition"])["body"]["request"]["manifest"]
                         if current["last_transition"] else None)
    def validate_claim(_):
        _implementation_inputs()
        if preparation is not None and preparation["error"] is None:
            retrieval_assessment.check_prepared_retrieval_study(preparation["prepared"])
        locked_events = ledger.events()
        if any(e["kind"] in TRANSITIONS | {"improvement_started"} and e["body"].get("run_key") == run_key
               for e in locked_events):
            raise ValueError("Run key was already claimed; read its recorded result before continuing")
        transitions = [e for e in locked_events if e["kind"] in TRANSITIONS]
        actual = transitions[-1]["body"]["next_step"]["id"] if transitions else "initial"
        if actual != after_step:
            raise ValueError("Another worker advanced the queue")
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
        expected_request_hash = os.environ.get("EPIPHYSICS_EXPECTED_REQUEST_SHA256")
        if expected_request_hash is not None and digest(canonical(request).encode()) != expected_request_hash:
            raise ValueError("Assessment inputs changed from the dispatcher's prepared request")
        if preparation is not None:
            if preparation["error"] is not None:
                raise ValueError("Invalid supplied retrieval study: " + preparation["error"]["message"])
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
            if actual.get("schema_version") == 3 and actual.get("phase") == "preparation":
                report["coverage_preparation"] = actual
            else:
                report["actual_retrieval"] = actual
                report["metrics"]["retrieval_baseline_reproducibility"] = actual["reproducibility"]["value"]
            retrieval_assessment.check_prepared_retrieval_study(preparation["prepared"])
        if {name: digest(raw) for name, raw in inputs.items()} != manifest:
            raise ValueError("Assessment input bytes changed after claim")
        _implementation_inputs()
        elapsed = time.monotonic() - started
        if elapsed > policy["max_assessment_seconds"]:
            raise ValueError("Assessment exceeded its elapsed-time acceptance budget")
        result = {"run_key": run_key, "request": request, "input_observations": captures,
                  "stage": "offline_fixture", "result": "assessed", "report": report,
                  "prior_action_outcome": _forecast_result(previous, report, previous_manifest, manifest),
                  "next_step": select_next(report, run_key),
                  "actual_resources": {"elapsed_seconds": elapsed, "model_calls": 0, "external_spend": 0},
                  "scope": ("Synthetic conformance checks plus verified fresh-cohort preparation; retrieval quality remains unmeasured. "
                            if actual is not None and actual.get("phase") == "preparation" else
                            "Synthetic conformance checks plus separately reported validated retrospective development retrieval; no quality improvement or independent execution witness is inferred. "
                            if actual is not None else "Synthetic conformance assessment with fixed local checks; ") + "queued builds, deployment and scale promotion remain supervised"}
        if actual is not None:
            identity = {"input_manifest": dict(manifest),
                        "retrieval_assessment_hash": actual["assessment_identity"]["hash"]}
            result["assessment_identity"] = {**identity, "hash": digest(canonical(identity).encode())}
        # Completion and successor are one atomic ledger event, never two separate writes.
        expected_result = canonical(result)
        def validate_completion(_):
            _implementation_inputs()
            if {name: digest(raw) for name, raw in inputs.items()} != manifest:
                raise ValueError("Assessment inputs changed before completion")
            if preparation is not None:
                retrieval_assessment.check_prepared_retrieval_study(preparation["prepared"])
            if canonical(result) != expected_result:
                raise ValueError("Assessment result changed before completion")
        ledger.append("improvement_completed", result, f"improvement:{run_key}:complete",
                      exclusive=True, validate=validate_completion)
        return result
    except Exception as error:
        failed = {"run_key": run_key, "request": request, "result": "failed", "error": type(error).__name__,
                  "message": str(error)[:400], "next_step": {"id": f"{run_key}:diagnose", "state": "queued",
                  "action": "diagnose_failed_assessment", "reason": str(error)[:400], "scale_change_allowed": False}}
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
             completed_work="", timeout_seconds=60, retrieval_study_path=None):
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
    store = Path(store).resolve()
    policy_path, suite_path = str(Path(policy_path).resolve()), str(Path(suite_path).resolve())
    candidate = candidate if candidate in {"reference", "degraded"} else str(Path(candidate).resolve())
    if retrieval_study_path is not None:
        retrieval_study_path = os.path.abspath(retrieval_study_path)
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
                retrieval_study_path=args.retrieval_study)
        else:
            ledger = Ledger(args.store)
            result = status(ledger) if args.command == "status" else assess(ledger, args.policy, args.suite, args.candidate,
                args.run_key, after_step=args.after_step, completed_work=args.completed_work,
                retrieval_study_path=args.retrieval_study, _prepared_retrieval_path=args.prepared_retrieval_study)
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
