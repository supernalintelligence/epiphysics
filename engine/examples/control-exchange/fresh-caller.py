"""One exclusive, bounded invocation of the frozen exploratory comparison.

The caller records its own first read, not a globally witnessed first exposure.
Custody remains immutable. A completed receipt means the process returned a
complete-shaped report; the independent retained validator must check its claims.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

_SOURCE = Path(__file__).read_bytes()
_MODULE_CODE = sys._getframe().f_code
ENGINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ENGINE))
from epiphysics import decision_pilot as pilot

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
SOURCE_PATHS = {name: ENGINE / "epiphysics" / name for name in (
    "decision_views.py", "decision_policy.py", "decision_evaluation.py",
    "decision_pilot.py", "decision_assessment.py", "improvement.py")}
SOURCE_PATHS.update({name: SCRIPT_DIRECTORY / name for name in ("fresh-generator.py", "fresh-caller.py")})
CONTRACT_PATHS = {role: SCRIPT_DIRECTORY / filename for role, filename in (
    ("decision_contract", "decision-contract.json"), ("evaluation_contract", "evaluation-contract.json"))}
OUTPUT_KEYS = {"cohort", "custody", "report", "journal", "claim", "caller_receipt", "stdout", "stderr"}
PROGRAM_SECONDS = 60
MAX_METADATA = 131072
MAX_COHORT = 262144
MAX_REPORT = 16 * 1024 * 1024
MAX_JOURNAL = 24 * 1024 * 1024
MAX_OUTPUT = 65536


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def read_bounded(path, maximum):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("Input must be a bounded regular file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Input changed to a nonregular file")
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("Input exceeds its byte bound")
    return raw


def persist_new(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def now():
    return datetime.now(timezone.utc).isoformat()


def run(registration_path):
    started_at, started = now(), time.monotonic()
    registration_path = Path(registration_path)
    if not registration_path.is_absolute():
        raise ValueError("Registration path must be absolute")
    registration_raw = read_bounded(registration_path, MAX_METADATA)
    registration = pilot._strict(registration_raw)
    if (type(registration) is not dict or registration.get("schema_version") != 1
            or registration.get("phase") != "fresh_comparison"
            or registration.get("cohort_id") != "decision-pilot-fresh-v1"
            or type(registration.get("execution_id")) is not str
            or not 1 <= len(registration["execution_id"]) <= 100):
        raise ValueError("Invalid fixed fresh registration")
    declared = registration.get("outputs")
    if type(declared) is not dict or set(declared) != OUTPUT_KEYS:
        raise ValueError("Invalid registered output paths")
    outputs = {key: Path(value) for key, value in declared.items() if type(value) is str}
    if (len(outputs) != len(OUTPUT_KEYS) or any(not p.is_absolute() for p in outputs.values())
            or len({str(p.resolve()) for p in outputs.values()}) != len(OUTPUT_KEYS)
            or any(p.parent.resolve() != registration_path.parent.resolve() for p in outputs.values())
            or registration_path.resolve() in {p.resolve() for p in outputs.values()}
            or outputs["journal"] != outputs["report"].with_name(outputs["report"].name + ".attempts.jsonl")):
        raise ValueError("Outputs require distinct absolute paths beside registration")
    for key in OUTPUT_KEYS - {"cohort", "custody"}:
        if outputs[key].exists() or outputs[key].is_symlink():
            raise ValueError("Existing execution evidence; inspect it, never replay")
    expected_sources = registration.get("source_hashes")
    if type(expected_sources) is not dict or set(expected_sources) != set(SOURCE_PATHS):
        raise ValueError("Invalid frozen source set")
    pinned = {str(registration_path): registration_raw}
    for name, path in SOURCE_PATHS.items():
        raw = read_bounded(path, MAX_METADATA)
        if digest(raw) != expected_sources[name]:
            raise ValueError("Frozen implementation changed")
        if name == "fresh-caller.py" and (raw != _SOURCE or compile(raw, __file__, "exec",
                dont_inherit=True, optimize=sys.flags.optimize) != _MODULE_CODE):
            raise ValueError("Executing caller differs from frozen source")
        pinned[str(path)] = raw
    expected_contracts = registration.get("contract_hashes")
    if type(expected_contracts) is not dict or set(expected_contracts) != set(CONTRACT_PATHS):
        raise ValueError("Invalid frozen contract set")
    for role, path in CONTRACT_PATHS.items():
        raw = read_bounded(path, MAX_METADATA)
        if digest(raw) != expected_contracts[role]:
            raise ValueError("Frozen contract changed")
        pinned[str(path)] = raw
    custody_raw = read_bounded(outputs["custody"], MAX_METADATA)
    custody = pilot._strict(custody_raw)
    if (type(custody) is not dict or custody.get("status") != "complete"
            or custody.get("registration_sha256") != digest(registration_raw)
            or custody.get("execution_id") != registration["execution_id"]
            or custody.get("generator_sha256") != expected_sources["fresh-generator.py"]
            or custody.get("caller_sha256") != expected_sources["fresh-caller.py"]
            or custody.get("first_exposure") is not None
            or type(custody.get("cohort_sha256")) is not str):
        raise ValueError("Custody does not bind this frozen execution")
    pinned[str(outputs["custody"])] = custody_raw
    # These timestamps concern this caller only. No cohort bytes are read above.
    claim = {"schema_version": 1, "execution_id": registration["execution_id"],
             "registration_sha256": digest(registration_raw), "custody_sha256": digest(custody_raw),
             "cohort_sha256": custody["cohort_sha256"],
             "caller_sha256": expected_sources["fresh-caller.py"], "first_exposure_at": now()}
    claim_raw = canonical(claim)
    persist_new(outputs["claim"], claim_raw)
    status, failure, report_raw, journal_raw = "failed", None, None, None
    transport = {"stdout": b"", "stderr": b"", "returncode": None, "error": "not_started"}
    try:
        cohort_raw = read_bounded(outputs["cohort"], MAX_COHORT)
        if digest(cohort_raw) != custody["cohort_sha256"]:
            raise ValueError("Cohort differs from immutable custody")
        pinned[str(outputs["cohort"])] = cohort_raw
        remaining = PROGRAM_SECONDS - (time.monotonic() - started)
        transport = pilot._capture_process(
            [sys.executable, "-s", "-m", "epiphysics.decision_pilot", "--phase", "fresh_comparison",
             "--cohort", str(outputs["cohort"]), "--output", str(outputs["report"])],
            b"", remaining, output_limit=MAX_OUTPUT, start_new_session=False)
        # A complete failed-check run legitimately exits 1. An interrupted run
        # lacks the complete report shape and remains failed preparation.
        retained, capture_errors = {}, []
        for role, maximum in (("report", MAX_REPORT), ("journal", MAX_JOURNAL)):
            try:
                retained[role] = read_bounded(outputs[role], maximum)
            except (OSError, ValueError) as error:
                capture_errors.append({"role": role, "type": type(error).__name__, "message": str(error)[:400]})
        report_raw, journal_raw = retained.get("report"), retained.get("journal")
        if capture_errors or transport["error"] not in (None, "worker_exit"):
            failure = {"type": "IncompleteExecution", "transport_error": transport["error"],
                       "capture_errors": capture_errors}
            raise ValueError("Incomplete execution; available report and journal bytes retained independently")
        report = pilot._strict(report_raw)
        if (transport["returncode"] not in (0, 1)
                or transport["error"] not in (None, "worker_exit")
                or type(report) is not dict or report.get("stage") != "fresh_exploratory"
                or report.get("declared_case_count") != 24
                or type(report.get("checks")) is not dict or not report["checks"]
                or any(type(value) is not bool for value in report["checks"].values())
                or transport["returncode"] != (0 if all(report["checks"].values()) else 1)):
            raise ValueError("Worker did not return a complete-shaped fixed comparison")
        status = "completed"
    except Exception as error:
        if failure is None:
            failure = {"type": type(error).__name__, "message": str(error)[:400],
                       "transport_error": transport["error"]}
    unchanged = True
    for path, original in pinned.items():
        try:
            unchanged &= read_bounded(path, max(len(original), 1)) == original
        except (OSError, ValueError):
            unchanged = False
    if not unchanged:
        status = "failed"
        failure = {"type": "InputChanged", "message": "Frozen source or input changed during execution"}
    persistence_errors = []
    for label in ("stdout", "stderr"):
        try:
            persist_new(outputs[label], transport[label])
        except OSError as error:
            persistence_errors.append({"stage": label, "type": type(error).__name__, "message": str(error)[:400]})
    elapsed = time.monotonic() - started
    if elapsed > PROGRAM_SECONDS:
        status = "failed"
        failure = {"type": "CallerDeadline", "message": "Whole caller exceeded its 60-second budget"}
    if persistence_errors:
        status = "failed"
    receipt = {"schema_version": 1, "status": status, "execution_id": registration["execution_id"],
               "claim_sha256": digest(claim_raw), "registration_sha256": digest(registration_raw),
               "custody_sha256": digest(custody_raw), "cohort_sha256": custody["cohort_sha256"],
               "caller_sha256": expected_sources["fresh-caller.py"],
               "report_sha256": digest(report_raw) if report_raw is not None else None,
               "journal_sha256": digest(journal_raw) if journal_raw is not None else None,
               "returncode": transport["returncode"], "started_at": started_at, "ended_at": now(),
               "elapsed_seconds": elapsed, "stdout_sha256": digest(transport["stdout"]),
               "stderr_sha256": digest(transport["stderr"]), "stdout_bytes": len(transport["stdout"]),
               "stderr_bytes": len(transport["stderr"]), "original_files_unchanged": unchanged}
    if status != "completed":
        receipt["failure"] = failure
        receipt["persistence_errors"] = persistence_errors
    persist_new(outputs["caller_receipt"], canonical(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registration", type=Path)
    args = parser.parse_args(argv)
    receipt = run(args.registration)
    print(json.dumps({"status": receipt["status"], "execution_id": receipt["execution_id"],
                      "returncode": receipt["returncode"], "elapsed_seconds": receipt["elapsed_seconds"]}))
    return 0 if receipt["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
