"""Fixed, bounded development and fresh runners for the owned decision pilot.

The child entry point receives only canonical public header/tape bytes. Private
world resolution is imported by the parent only. Process separation prevents
accidental argument leakage, not hostile access by another process of this user.
No arbitrary candidate commands, network calls, model calls or live effects.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time

from . import decision_views as views
from .decision_policy import decide_release_hold

PROGRAM_SECONDS = 30
MAX_REQUEST_BYTES = 65536
MAX_OUTPUT_BYTES = 65536
MAX_COHORT_BYTES = 262144
ARMS = (("flat-recency-v1", 2048), ("task-proximity-v1", 2048),
        ("flat-recency-v1", 32768), ("task-proximity-v1", 32768))
SOURCE_NAMES = ("decision_views.py", "decision_policy.py", "decision_evaluation.py", "decision_pilot.py")
FRESH_MECHANISMS = {"late_visibility": 6, "visible_authority_changes": 4, "verification_dispute": 4,
                    "duplicate_identity": 4, "retention_pressure": 4, "role_direction": 2}
PROPOSAL_HARMS = ("unauthorized_release_proposals_all", "duplicate_release_proposals_all",
                  "invalid_artifact_release_proposals", "evidence_unjustified_release_proposals")


def _strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("Nonfinite JSON number")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _source_hashes():
    directory = Path(__file__).resolve().parent
    result = {}
    for name in SOURCE_NAMES:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 100000:
            raise ValueError("Invalid fixed implementation source")
        with path.open("rb") as stream:
            raw = stream.read(100001)
        if len(raw) > 100000:
            raise ValueError("Implementation source exceeds bound")
        result[name] = _hash(raw)
    return result


def _candidate(request):
    """Only this fixed public-input function executes in a candidate child."""
    if type(request) is not dict or set(request) != {"header", "tape", "recipe", "budget_bytes"}:
        raise ValueError("Invalid public worker request")
    if type(request["header"]) is not str or type(request["tape"]) is not str:
        raise ValueError("Worker inputs must be UTF-8 text")
    header, tape = request["header"].encode(), request["tape"].encode()
    start = time.monotonic()
    view = views.build_decision_view(header, tape, recipe=request["recipe"], budget_bytes=request["budget_bytes"])
    built = time.monotonic()
    verified = views.validate_decode_view(header, tape, view, budget_bytes=request["budget_bytes"])
    decoded = time.monotonic()
    proposal = decide_release_hold(verified)
    decided = time.monotonic()
    return {"view": view.decode(), "proposal": proposal,
            "input_hash": verified.input_hash, "source_hash": verified.source_hash,
            "complete": verified.complete,
            "timings": {"build_seconds": built - start, "validate_decode_seconds": decoded - built,
                        "policy_seconds": decided - decoded}}


def _capture_process(arguments, request_bytes, timeout, *, output_limit=MAX_OUTPUT_BYTES, start_new_session=True):
    """Drain bounded output, kill/reap on a deadline, and retain failed bytes.

    This private transport accepts arguments for owned timeout/overflow tests;
    the public runner always supplies the single fixed worker command below.
    Anonymous stdin avoids deadlocks when the bounded request exceeds pipe size.
    A session owner always terminates its group, including descendants whose
    direct parent already exited. Nested transports keep that group and own
    cleanup of their direct child only; the outer owner bounds the whole tree.
    """
    if len(request_bytes) > MAX_REQUEST_BYTES or timeout <= 0:
        return {"error": "program_deadline" if timeout <= 0 else "request_limit",
                "stdout": b"", "stderr": b"", "returncode": None, "elapsed_seconds": 0.0}
    start = time.monotonic()
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    error = None
    interrupted = None
    environment = {key: value for key, value in os.environ.items()
                   if key in {"PATH", "SYSTEMROOT", "TMPDIR", "LANG", "LC_ALL"}}
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    environment["PYTHONHASHSEED"] = "0"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryFile() as incoming, tempfile.TemporaryDirectory(prefix="epiphysics-public-worker-") as directory:
        incoming.write(request_bytes)
        incoming.seek(0)
        process = subprocess.Popen(arguments, stdin=incoming, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=directory, env=environment, start_new_session=start_new_session)
        try:
            with selectors.DefaultSelector() as selector:
                for label, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                    selector.register(stream, selectors.EVENT_READ, label)
                while selector.get_map():
                    remaining = timeout - (time.monotonic() - start)
                    if remaining <= 0:
                        error = "worker_timeout"
                        break
                    for key, _ in selector.select(min(remaining, 0.05)):
                        chunk = os.read(key.fileobj.fileno(), min(8192, output_limit + 1))
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        capacity = output_limit + 1 - sum(map(len, streams.values()))
                        streams[key.data].extend(chunk[:capacity])
                        if sum(map(len, streams.values())) > output_limit:
                            error = "worker_output_limit"
                            break
                    if error:
                        break
                if error is None:
                    try:
                        process.wait(timeout=max(0.001, timeout - (time.monotonic() - start)))
                    except subprocess.TimeoutExpired:
                        error = "worker_timeout"
        except ProgramDeadline as expired:
            interrupted = expired
            raise
        finally:
            if start_new_session:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None or error is not None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            process.wait()
            process.stdout.close()
            process.stderr.close()
            if interrupted is not None:
                interrupted.partial_receipt = {"error": "program_deadline", "stdout": bytes(streams["stdout"]),
                    "stderr": bytes(streams["stderr"]), "returncode": process.returncode,
                    "elapsed_seconds": time.monotonic() - start,
                    "output_scope": "Prefix drained before the whole-program deadline; unread child bytes may be absent"}
    if error is None and process.returncode != 0:
        error = "worker_exit"
    return {"error": error, "stdout": bytes(streams["stdout"]), "stderr": bytes(streams["stderr"]),
            "returncode": process.returncode, "elapsed_seconds": time.monotonic() - start}


def _run_candidate(bundle, recipe, budget, remaining):
    request = {"header": bundle["header_bytes"].decode(), "tape": bundle["event_tape_bytes"].decode(),
               "recipe": recipe, "budget_bytes": budget}
    raw = views.canonical(request)
    try:
        receipt = _capture_process([sys.executable, "-s", "-B", "-m", "epiphysics.decision_pilot", "--worker"],
                                   raw, remaining, start_new_session=False)
    except ProgramDeadline as expired:
        if hasattr(expired, "partial_receipt"):
            expired.partial_receipt["request_bytes"] = len(raw)
        raise
    except OSError as error:
        receipt = {"error": "worker_launch_failed", "stdout": b"", "stderr": str(error).encode()[:1024],
                   "returncode": None, "elapsed_seconds": 0.0}
    receipt["request_bytes"] = len(raw)
    return receipt


def _verify_response(receipt, bundle, recipe, budget):
    if receipt["error"]:
        raise ValueError(receipt["error"])
    response = _strict(receipt["stdout"])
    if type(response) is not dict or set(response) != {"view", "proposal", "input_hash", "source_hash", "complete", "timings"}:
        raise ValueError("Invalid worker response shape")
    if type(response["view"]) is not str:
        raise ValueError("Missing serialized view")
    view = response["view"].encode()
    parsed = _strict(view)
    if parsed.get("arm") != recipe:
        raise ValueError("Worker used a different recipe")
    verified = views.validate_decode_view(bundle["header_bytes"], bundle["event_tape_bytes"], view, budget_bytes=budget)
    if (response["input_hash"] != verified.input_hash or response["source_hash"] != verified.source_hash
            or type(response["complete"]) is not bool or response["complete"] != verified.complete):
        raise ValueError("Worker input/provenance receipt differs")
    proposal = response["proposal"]
    expected_ids = sorted(event["event_id"] for event in verified.events if event["kind"] in views.POLICY_KINDS)
    if type(proposal) is not dict or proposal.get("support_event_ids") != expected_ids:
        raise ValueError("Proposal evidence IDs differ from retained policy records")
    timings = response["timings"]
    if type(timings) is not dict or set(timings) != {"build_seconds", "validate_decode_seconds", "policy_seconds"}:
        raise ValueError("Missing worker resource accounting")
    for duration in timings.values():
        if type(duration) not in (int, float) or not 0 <= duration <= receipt["elapsed_seconds"]:
            raise ValueError("Invalid worker duration")
    if sum(timings.values()) > receipt["elapsed_seconds"]:
        raise ValueError("Overlapping or invalid worker durations")
    return response, view, verified


def _next_step(report):
    """Fixed research triage; a fresh result never queues another fresh batch."""
    failures = report["checks"]
    repair = (not all(failures.values()) or any(
        arm["summary"]["metrics"][name]["numerator"]
        for arm in report["arms"] for name in ("duplicate_effects", "unauthorized_effects")))
    if report.get("stage") == "fresh_exploratory":
        flat, relational = (arm["summary"] for arm in report["arms"][:2])
        promising = (relational["metrics"]["valid_timely_release"]["numerator"]
                     - flat["metrics"]["valid_timely_release"]["numerator"] >= 2
                     and relational["counts"]["failed_attempts"] <= flat["counts"]["failed_attempts"]
                     and all(relational["metrics"][name]["numerator"] <= flat["metrics"][name]["numerator"]
                             for name in PROPOSAL_HARMS))
        return {"action": "repair_decision_pilot" if repair else
                    "prepare_prospective_decision_shadow" if promising else "investigate_decision_information_limits",
                "reason": "A conformance, execution or separation check failed" if repair else
                    "Fresh exploratory comparison met the registered two-release triage margin; prepare one nonacting prospective shadow task" if promising else
                    "Fresh exploratory comparison did not meet the registered triage margin; retain the flat baseline and investigate information limits",
                "scale_change_allowed": False, "live_effects_allowed": False,
                "metric_status": "fresh exploratory measurements; research triage only; no adoption claim"}
    return {"action": "repair_decision_pilot" if repair else "prepare_fresh_decision_comparison",
            "reason": "A conformance, execution or separation check failed" if repair else
                "Development wiring passed; freeze and review before generating one new 24-case exploratory batch",
            "scale_change_allowed": False, "live_effects_allowed": False,
            "metric_status": "exposed development measurements; no adoption claim"}


def _receipt_record(receipt):
    return {**{key: value for key, value in receipt.items() if key not in ("stdout", "stderr")},
        **{label + "_base64": base64.b64encode(receipt[label]).decode() for label in ("stdout", "stderr")},
        **{label + "_sha256": _hash(receipt[label]) for label in ("stdout", "stderr")},
        **{label + "_bytes": len(receipt[label]) for label in ("stdout", "stderr")}}


def run_development(cohort, *, record=None):
    """Execute exactly twelve owned development cases, retaining all 48 attempts."""
    return _run_comparison(cohort, fresh=False, record=record)


def run_fresh_comparison(cohort, *, record=None):
    """Execute the fixed 24-case fresh allocation, retaining all 96 attempts.

    Custody, prior source freeze and one-shot execution are bound by the root
    caller and retained assessment. This function does not generate any cases.
    """
    return _run_comparison(cohort, fresh=True, record=record)


def _run_comparison(cohort, *, fresh, record):
    # Deliberately unavailable in the worker path; candidate input never contains
    # a trace, fixture label, private outcome, expected action or evaluator data.
    from . import decision_evaluation as evaluation
    started = time.monotonic()
    source_hashes = _source_hashes()
    count = 24 if fresh else 12
    cohort_id = "decision-pilot-fresh-v1" if fresh else "decision-pilot-development-v1"
    if (type(cohort) is not dict or cohort.get("cohort_id") != cohort_id
            or cohort.get("contract_id") != views.CONTRACT_ID or type(cohort.get("trace_count")) is not int
            or cohort["trace_count"] != count or cohort.get("final_cohort_generated") is not fresh
            or type(cohort.get("traces")) is not list or len(cohort["traces"]) != count
            or fresh and cohort.get("status") != "fresh_exploratory"):
        raise ValueError("Invalid fixed fresh comparison cohort" if fresh else
                         "Only the twelve-case exposed development cohort is supported")
    cohort_bytes = views.canonical(cohort)
    if len(cohort_bytes) > MAX_COHORT_BYTES:
        raise ValueError("Comparison cohort exceeds byte bound")
    traces = deepcopy(cohort["traces"])
    if any(type(trace) is not dict for trace in traces):
        raise ValueError("Invalid declared case")
    identities = [trace.get("trace_id") for trace in traces]
    if any(type(identity) is not str for identity in identities) or len(set(identities)) != count:
        raise ValueError("Duplicate or missing declared case identity")
    for trace in traces:
        evaluation.resolve_world(trace)
    if fresh:
        mechanisms = {}
        for trace in traces:
            mechanisms[trace["mechanism"]] = mechanisms.get(trace["mechanism"], 0) + 1
        if mechanisms != FRESH_MECHANISMS:
            raise ValueError("Fresh comparison must use the exact registered mechanism allocation")
    report = {"schema_version": 1, "contract_id": views.CONTRACT_ID,
              "cohort_id": cohort["cohort_id"], "cohort_hash": _hash(cohort_bytes),
              "stage": "fresh_exploratory" if fresh else "exposed_development", "declared_case_count": count,
              "source_hashes": source_hashes, "arms": [],
              "checks": {"all_outputs_valid": True, "lossless_reference_parity": True,
                         "fixed_policy_conformance": True,
                         "same_input_same_output": True, "program_deadline_met": True,
                         "source_unchanged": True},
              "limits": {"program_seconds": PROGRAM_SECONDS, "normal_view_bytes": 2048,
                         "lossless_view_bytes": 32768, "worker_output_bytes": MAX_OUTPUT_BYTES},
              "scope": "Owned synthetic fresh exploratory comparison only; retention and view systems compared together; no generalization or live authority claim" if fresh else
                  "Owned synthetic development only; retention and view systems compared together; no generalization or live authority claim"}
    identical_inputs = {}
    for recipe, budget in ARMS:
        rows = []
        evaluation_rows = []
        arm = {"recipe": recipe, "budget_bytes": budget, "control": budget == 32768, "rows": rows}
        report["arms"].append(arm)
        for trace in traces:
            normalization_start = time.monotonic()
            bundle = views.prepare_decision_input(trace["events"], trace["task"], trace["cutoff"], trace["decision_at"])
            normalization_seconds = time.monotonic() - normalization_start
            try:
                receipt = _run_candidate(bundle, recipe, budget, PROGRAM_SECONDS - (time.monotonic() - started))
            except ProgramDeadline as expired:
                if record is not None and hasattr(expired, "partial_receipt"):
                    record({"kind": "worker_interrupted", "case_id": trace["trace_id"], "recipe": recipe,
                            "budget_bytes": budget, "input_hash": bundle["input_hash"],
                            "receipt": _receipt_record(expired.partial_receipt)})
                raise
            if record is not None:
                record({"kind": "worker_returned", "case_id": trace["trace_id"], "recipe": recipe,
                        "budget_bytes": budget, "input_hash": bundle["input_hash"], "receipt": _receipt_record(receipt)})
            error, response, view, verified = receipt["error"], None, None, None
            verification_start = time.monotonic()
            try:
                response, view, verified = _verify_response(receipt, bundle, recipe, budget)
            except (ValueError, TypeError, KeyError, UnicodeError, AttributeError, RecursionError, OverflowError) as invalid:
                error = str(invalid).encode("utf-8", errors="replace")[:400].decode("utf-8", errors="replace")
            verification_seconds = time.monotonic() - verification_start
            proposal = None if error else response["proposal"]
            evaluated = evaluation.evaluate_simulated_proposal(trace, proposal, prior_effect_keys=(), error=error)
            evaluation_rows.append(evaluated)
            row = deepcopy(evaluated)
            row.update(arm=recipe, budget_bytes=budget, input_hash=bundle["input_hash"],
                source_hash=_hash(bundle["event_tape_bytes"]),
                source_bytes=len(bundle["event_tape_bytes"]), header_bytes=len(bundle["header_bytes"]),
                view_hash=_hash(view) if view is not None else None, view_bytes=len(view) if view is not None else None,
                view=view.decode() if view is not None else None,
                provenance_valid=verified is not None,
                complete=verified.complete if verified is not None else None,
                worker_receipt=_receipt_record(receipt),
                resources={"normalization_seconds": normalization_seconds,
                    "candidate_stages": response["timings"] if response is not None and not error else None,
                    "child_wall_seconds": receipt["elapsed_seconds"],
                    "parent_verification_seconds": verification_seconds,
                    "model_calls": 0, "external_program_spend": 0, "memory_bytes": None})
            rows.append(row)
            if record is not None:
                record({"kind": "attempt_evaluated", "row": row})
            report["checks"]["all_outputs_valid"] &= row["proposal_valid"]
            if row["proposal_valid"]:
                conformant = (proposal == row["reference_proposal"] if verified.complete else
                    proposal["action"] == "hold" and proposal["reason"] == "incomplete_evidence")
                report["checks"]["fixed_policy_conformance"] &= conformant
            else:
                report["checks"]["fixed_policy_conformance"] = False
            if budget == 32768 and (not row["proposal_valid"] or proposal != row["reference_proposal"]):
                report["checks"]["lossless_reference_parity"] = False
            key = (recipe, budget, bundle["input_hash"])
            signature = (row["view_hash"], proposal, error)
            if key in identical_inputs and identical_inputs[key] != signature:
                report["checks"]["same_input_same_output"] = False
            identical_inputs[key] = signature
        arm["summary"] = evaluation.aggregate_metrics(evaluation_rows)
        arm["strata"] = {mechanism: evaluation.aggregate_metrics([row for row in evaluation_rows if row["mechanism"] == mechanism])
            for mechanism in sorted({row["mechanism"] for row in evaluation_rows})}
    report["checks"]["source_unchanged"] = source_hashes == _source_hashes()
    report["resources"] = {"parent_wall_seconds": time.monotonic() - started,
                           "model_calls": 0, "external_program_spend": 0,
                           "agent_and_review_cost": None, "memory_bytes": None,
                           "accounting": "Child wall contains its stage times. Parent wall includes computation and attempt journaling through final source verification, excluding final report serialization/persistence. Do not add nested totals. Lossless arms are separate controls; retain caller wall time separately."}
    report["checks"]["program_deadline_met"] = report["resources"]["parent_wall_seconds"] <= PROGRAM_SECONDS
    report["next_step"] = _next_step(report)
    return report


class ProgramDeadline(BaseException):
    """Interrupt the whole supervised CLI, including parent-only work."""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--phase", choices=("development", "fresh_comparison"), default="development")
    parser.add_argument("--cohort", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.worker:
        if args.cohort is not None or args.output is not None or args.phase != "development":
            parser.error("Worker accepts public stdin only")
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("Worker request exceeds byte bound")
        result = views.canonical(_candidate(_strict(raw)))
        if len(result) > MAX_OUTPUT_BYTES:
            raise ValueError("Worker output exceeds byte bound")
        sys.stdout.buffer.write(result)
        return 0
    if args.cohort is None or args.output is None:
        parser.error("Specify the owned cohort and a new output file")
    # Reserve the destination before any attempt; existing evidence is never overwritten.
    with args.output.open("xb") as output:
        if args.cohort.is_symlink() or not args.cohort.is_file():
            raise ValueError("Cohort must be a regular file")
        with args.cohort.open("rb") as incoming:
            raw = incoming.read(MAX_COHORT_BYTES + 1)
        if len(raw) > MAX_COHORT_BYTES:
            raise ValueError("Cohort exceeds byte bound")
        cohort = _strict(raw)
        journal_path = args.output.with_name(args.output.name + ".attempts.jsonl")
        with journal_path.open("xb") as journal:
            def record(value):
                journal.write(views.canonical(value) + b"\n")
                journal.flush()
                os.fsync(journal.fileno())
            record({"kind": "declared_run", "cohort_hash": _hash(views.canonical(cohort)),
                    "source_hashes": _source_hashes(), "arms": ARMS,
                    "case_ids": [item.get("trace_id") for item in cohort.get("traces", [])],
                    "scope": "fresh exploratory comparison; only root may invoke the registered run" if args.phase == "fresh_comparison" else
                        "exposed development; only root may invoke the registered run"})
            def deadline(_signum, _frame):
                raise ProgramDeadline("Whole-program deadline exceeded")
            previous = signal.signal(signal.SIGALRM, deadline)
            signal.setitimer(signal.ITIMER_REAL, PROGRAM_SECONDS)
            try:
                runner = run_fresh_comparison if args.phase == "fresh_comparison" else run_development
                result = runner(cohort, record=record)
            except (Exception, ProgramDeadline) as error:
                result = {"status": "failed", "error": type(error).__name__, "message": str(error)[:400],
                    "checks": {"completed": False}, "journal": str(journal_path),
                    "metrics": None, "scope": "Incomplete run; retained attempts must not be presented as complete cohort metrics",
                    "next_step": {"action": "repair_decision_pilot", "scale_change_allowed": False}}
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous)
            record({"kind": "run_terminal", "checks": result["checks"], "next_step": result["next_step"]})
            output.write(views.canonical(result) + b"\n")
            output.flush()
            os.fsync(output.fileno())
    print(json.dumps({"output": str(args.output), "checks": result["checks"], "next_step": result["next_step"]}))
    return 0 if all(result["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
