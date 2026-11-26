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
import subprocess
import sys
import time
import uuid
from pathlib import Path

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, manifest_checks, manifests, representation_checks, source_span_checks, store, transformation_checks, transforms
from .store import Ledger, canonical, digest, utc_now
from .representation_checks import FAMILIES, evaluate, reference_candidate, degraded_candidate, validate_suite
from .source_span_checks import run_source_span_checks
from .manifest_checks import run_manifest_checks
from .transformation_checks import run_transformation_checks

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE)
    for module in (assertions, manifests, manifest_checks, representation_checks, source_span_checks, store, transforms, transformation_checks)
)

# Pin dependency identities after imports. Reloading a module can otherwise pair
# its new source snapshot with our old from-import callable aliases.
_IMPLEMENTATIONS = {
    name: (module, Path(module.__file__), module.IMPLEMENTATION_SOURCE,
           module.IMPLEMENTATION_CODE, module.IMPLEMENTATION_DEPENDENCIES)
    for name, module in {"evaluator": representation_checks, "assertions": assertions,
                         "manifests": manifests, "manifest_probe": manifest_checks,
                         "transforms": transforms, "transformation_probe": transformation_checks,
                         "source_span_probe": source_span_checks, "store": store,
                         "controller": sys.modules[__name__]}.items()
}

MAX_BYTES = 1_000_000
TRANSITIONS = {"improvement_completed", "improvement_failed"}
ALLOWED_EVENTS = TRANSITIONS | {"improvement_started", "observation"}


def _load(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Input exceeds 1 MB")
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
        ("build_split_merge_transformations", "split_merge_preservation", 1, "increase", True,
         "Representation contracts and actual assertion, manifest, and fixed graph-operation probes pass. Implement and test split/merge transformations (Packet B2b); split/merge preservation remains unmeasured."),
    ]
    ranked = [{"action": a, "metric": metric, "observed": m.get(metric), "target": target,
               "direction": direction, "eligible": eligible, "reason": reason,
               "estimated_success_probability": None, "estimated_cost": None}
              for a, metric, target, direction, eligible, reason in choices]
    chosen = next(c for c in ranked if c["eligible"])
    return {"id": f"{run_key}:next", "state": "queued", **chosen,
            "family": worst if chosen["action"] == "repair_weakest_entity_family" else None,
            "selection_rule": "integrity, evidence, coverage, weakest family, actual assertion, manifest and fixed graph probes, then missing capability",
            "forecast_kind": "target and directional hypothesis; probability and cost unestimated",
            "candidate_actions": ranked, "scale_change_allowed": False}


def _forecast_result(previous, report, previous_manifest, current_manifest):
    metric = previous.get("metric")
    if previous_manifest is not None:
        changed = [name for name in ("suite", "evaluator", "policy", "assertions", "source_span_probe", "store", "manifests", "manifest_probe", "transforms", "transformation_probe")
                   if previous_manifest.get(name) != current_manifest.get(name)]
        if changed:
            return {"status": "incomparable_contract_change", "changed_inputs": changed,
                    "step_id": previous["id"], "metric": metric}
    observed = report["metrics"].get(metric)
    if previous_manifest is None or metric is None or observed is None:
        return {"status": "unmeasured", "step_id": previous["id"], "metric": metric}
    baseline = previous.get("observed")
    return {"status": "measured", "step_id": previous["id"], "metric": metric,
            "baseline": baseline, "observed": observed,
            "change": None if baseline is None else observed - baseline,
            "target_met": observed <= previous["target"] if previous["direction"] == "decrease" else observed >= previous["target"],
            "interpretation": "Descriptive change; no causal attribution to the queued action"}


def _implementation_inputs():
    pinned_codes = {module.__name__: code for module, _, _, code, _ in _IMPLEMENTATIONS.values()}
    for name, (module, path, captured, executing_code, dependencies) in _IMPLEMENTATIONS.items():
        if module.IMPLEMENTATION_CODE is not executing_code or module.IMPLEMENTATION_SOURCE != captured:
            raise ValueError(f"Implementation reloaded since controller import: {name}; use a fresh process after review")
        if path.read_bytes() != captured:
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


def assess(ledger, policy_path, suite_path, candidate, run_key, *, after_step="initial", completed_work=""):
    if sys._getframe().f_code is not assess.__code__:
        raise ValueError("Stale assessment callable after reload; use a fresh process")
    if type(ledger) is not Ledger or Ledger is not store.Ledger:
        raise ValueError("Stale or unsupported ledger class; use a fresh process")
    if not isinstance(run_key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_key):
        raise ValueError("Use a 1–100 character alphanumeric run key with . _ or -")
    if not isinstance(completed_work, str) or not completed_work.strip() or len(completed_work) > 8000:
        raise ValueError("Describe the work actually completed; assessment is not proof of task completion")
    policy, suite, output, inputs = _assessment_inputs(policy_path, suite_path, candidate)
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
    started = time.monotonic()
    try:
        captures = {}
        for name, raw in inputs.items():
            event = ledger.capture(f"improvement-input:{name}", raw, media_type="text/plain",
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
        _implementation_inputs()
        elapsed = time.monotonic() - started
        if elapsed > policy["max_assessment_seconds"]:
            raise ValueError("Assessment exceeded its elapsed-time acceptance budget")
        result = {"run_key": run_key, "request": request, "input_observations": captures,
                  "stage": "offline_fixture", "result": "assessed", "report": report,
                  "prior_action_outcome": _forecast_result(previous, report, previous_manifest, manifest),
                  "next_step": select_next(report, run_key),
                  "actual_resources": {"elapsed_seconds": elapsed, "model_calls": 0, "external_spend": 0},
                  "scope": "Synthetic conformance assessment with fixed local checks; queued builds, deployment and scale promotion remain supervised"}
        # Completion and successor are one atomic ledger event, never two separate writes.
        ledger.append("improvement_completed", result, f"improvement:{run_key}:complete", exclusive=True)
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
             completed_work="", timeout_seconds=60):
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
    # Validate store ownership before launching, and close this connection first.
    ledger = Ledger(store)
    try:
        _checked_events(ledger)
    finally:
        ledger.close()
    expected_request = None
    try:
        _, _, _, input_bytes = _assessment_inputs(policy_path, suite_path, candidate)
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
        if command == "dispatch":
            run.add_argument("--timeout-seconds", type=float, default=60)
    args = parser.parse_args(argv)
    ledger = None
    try:
        if args.command == "dispatch":
            result = dispatch(args.store, args.policy, args.suite, args.candidate, args.run_key,
                after_step=args.after_step, completed_work=args.completed_work, timeout_seconds=args.timeout_seconds)
        else:
            ledger = Ledger(args.store)
            result = status(ledger) if args.command == "status" else assess(ledger, args.policy, args.suite, args.candidate,
                args.run_key, after_step=args.after_step, completed_work=args.completed_work)
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
