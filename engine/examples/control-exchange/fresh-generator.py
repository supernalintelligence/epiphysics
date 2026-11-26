#!/usr/bin/env python3
"""Generate the single registered fresh exploratory batch, only after freeze.

Case-level controls may call build_case. Creating the registered 24 cases is a
separate custodian action: never use generate as a test, seed search or preview.
No candidate/view/policy code is imported or executed. The independent evaluator
is used only for schema, world facts and full-evidence opportunity denominators.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

_SOURCE = Path(__file__).read_bytes()
_MODULE_CODE = sys._getframe().f_code
ENGINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ENGINE))

CONTRACT_ID = "control-exchange-release-hold-v1"
COHORT_ID = "decision-pilot-fresh-v1"
GENERATOR_ID = "fresh-exploratory-generator-v1"
ALLOCATION = {"late_visibility": 6, "visible_authority_changes": 4,
              "verification_dispute": 4, "duplicate_identity": 4,
              "retention_pressure": 4, "role_direction": 2}
MAX_COHORT_BYTES = 262144
MAX_REGISTRATION_BYTES = 65536
MAX_SOURCE_BYTES = 131072
BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)
SOURCE_NAMES = ("decision_views.py", "decision_policy.py", "decision_evaluation.py",
                "decision_pilot.py", "decision_assessment.py", "improvement.py",
                "fresh-generator.py", "fresh-caller.py")
TRUTH_FIELDS = ("cases", "world_opportunities", "visible_actionable_opportunities",
                "forbidden_cases", "duplicate_opportunity_cases", "ordinary_attempts",
                "not_ready_or_invalid_cases")
LIMITS = {"program_seconds": 30, "worker_seconds": 60, "normal_view_bytes": 2048,
          "lossless_view_bytes": 32768, "worker_output_bytes": 65536, "cohort_bytes": 262144,
          "report_bytes": 16777216, "journal_bytes": 25165824, "bundle_bytes": 50331648,
          "model_calls": 0, "external_program_spend": 0, "live_effects": False}
TRIAGE = {"minimum_additional_valid_timely_releases": 2,
          "proposal_harm_metrics": ["unauthorized_release_proposals_all", "duplicate_release_proposals_all",
              "invalid_artifact_release_proposals", "evidence_unjustified_release_proposals"],
          "no_extra_failed_attempts": True, "repair_action": "repair_decision_pilot",
          "signal_action": "prepare_prospective_decision_shadow",
          "otherwise_action": "investigate_decision_information_limits"}
OUTPUT_NAMES = {"cohort", "custody", "report", "journal", "claim", "caller_receipt", "stdout", "stderr"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse_seed(raw):
    """An explicit custodian seed; no clocks, defaults, retry or entropy search."""
    require(type(raw) is bytes and re.fullmatch(rb"[0-9a-f]{64}\n?", raw) is not None,
            "Seed file must contain exactly 64 lowercase hex characters and optional LF")
    return bytes.fromhex(raw.decode().rstrip("\n"))


def _seed(seed):
    require(type(seed) is bytes and len(seed) == 32, "Seed must be exactly 32 bytes")


def _number(seed, domain, low, high):
    # Domain-separated SHA-256 avoids dependence on random-module/runtime state.
    value = hashlib.sha256(seed + b"\0" + domain.encode()).digest()
    return low + int.from_bytes(value, "big") % (high - low + 1)


def _time(seconds):
    require(-86400 <= seconds <= 86400, "Generated time exceeds the owned bound")
    return (BASE + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _release_key(task):
    return digest(canonical([CONTRACT_ID, task["obligation_id"], task["artifact_sha256"],
                             task["provider"], task["amount"], task["unit"]]))


def build_case(seed, mechanism, variant):
    """Build one case, suitable for small owned controls before registration.

Variants are preallocated mechanisms, never selected from candidate performance.
The seed changes actual times, intervals, amounts, identifiers, content digests,
and an inert future-record branch. Duplicate variants 0/1 intentionally share
one public history but use different attempt IDs and retain the same release key.
"""
    _seed(seed)
    require(type(mechanism) is str and mechanism in ALLOCATION, "Unknown mechanism")
    require(type(variant) is int and 0 <= variant < ALLOCATION[mechanism], "Invalid mechanism variant")
    shared_variant = 0 if mechanism == "duplicate_identity" and variant == 1 else variant
    domain = GENERATOR_ID + "/" + mechanism + "/" + str(shared_variant)
    number = lambda field, lo, hi: _number(seed, domain + "/" + field, lo, hi)
    tag = digest(seed + domain.encode())[:number("identifier-length", 6, 12)]
    task = {key: prefix + tag for key, prefix in (
        ("obligation_id", "job-"), ("requester", "req-"), ("delegate", "del-"),
        ("provider", "pro-"), ("artifact_id", "art-"))}
    decision, unit = number("decision", 3600, 72000), number("interval", 7, 29)
    task.update(artifact_sha256=digest(seed + (domain + "/artifact").encode()),
                amount=number("amount", 2, 100000), unit="simulation_credit",
                deadline=_time(decision + number("deadline", 0, 9) * unit))
    events = []

    def add(kind, eid, effective, observed=None, **changes):
        roles = {"grant": ("requester", "requester", "delegate"),
                 "revoke": ("requester", "requester", "delegate"),
                 "delivery_claim": ("provider", "provider", "artifact_id"),
                 "verification": ("requester", "requester", "artifact_id"),
                 "dispute_open": ("requester", "requester", "obligation_id"),
                 "dispute_close": ("requester", "requester", "obligation_id"),
                 "release_committed": ("requester", "delegate", "provider"),
                 "note": ("requester", "delegate", "artifact_id")}
        issuer, subject, obj = (task[name] for name in roles[kind])
        event = {"event_id": eid, "kind": kind, "issuer": issuer, "subject": subject,
                 "object": obj, "obligation_id": task["obligation_id"],
                 "effective_at": _time(decision + effective * unit),
                 "observed_at": _time(decision + (effective if observed is None else observed) * unit),
                 "reference": None, "artifact_sha256": task["artifact_sha256"]
                 if kind in ("delivery_claim", "verification", "release_committed") else None,
                 "verdict": "pass" if kind == "verification" else None, "authentication": "verified"}
        event.update(changes)
        events.append(event)
        return event

    grant = add("grant", "grant-a", -24)
    delivery = add("delivery_claim", "delivery", -18)
    verification = add("verification", "verification", -12)
    valid, completed = True, -19

    if mechanism == "late_visibility":
        if variant == 0:
            add("revoke", "hidden-revoke", -3, 2)
        elif variant == 1:
            add("grant", "grant-b", -20)
            add("revoke", "hidden-scoped-revoke", -4, 3, reference="grant-a")
            valid = False
        elif variant == 2:
            add("revoke", "visible-revoke", -8)
            add("grant", "hidden-regrant", -2, 2)
        elif variant == 3:
            verification["observed_at"] = _time(decision + 2 * unit)
            add("verification", "future-verification", 2, -1)
        elif variant == 4:
            add("dispute_open", "hidden-dispute", -4, 2)
            add("dispute_close", "future-close", 3, -1, reference="hidden-dispute")
        else:
            add("release_committed", "hidden-release", -2, 2, reference=_release_key(task))
    elif mechanism == "visible_authority_changes":
        if variant == 0:
            add("grant", "grant-b", -8)
            add("revoke", "scoped-revoke", -8, reference="grant-a")
        elif variant == 1:
            add("revoke", "global-revoke", -7)
            add("grant", "later-grant", -3)
            valid = False
        elif variant == 2:
            # The named revoke cannot create a tombstone for a future grant.
            add("revoke", "old-revoke", -16)
            add("revoke", "premature-revoke", -8, reference="future-target")
            add("grant", "future-target", -4, -10)
        else:
            add("revoke", "tied-revoke", -24)
            add("grant", "not-yet-effective", 1, -2)
            # A future conflicting verification is visible but presently inert.
            add("verification", "future-conflict", 2, -1, verdict="fail")
    elif mechanism == "verification_dispute":
        if variant == 0:
            add("dispute_close", "premature-close", -9, reference="later-open")
            add("dispute_open", "later-open", -6)
        elif variant == 1:
            add("dispute_open", "open-a", -9)
            add("dispute_open", "open-b", -7)
            add("dispute_close", "close-b", -5, reference="open-b")
            add("dispute_close", "close-a", -3, reference="open-a")
            valid = False
        elif variant == 2:
            add("dispute_open", "tied-open", -5)
            add("dispute_close", "tied-close", -5, reference="tied-open")
            verification["verdict"] = "fail"
            task["deadline"] = _time(decision - unit)
        else:
            add("dispute_open", "current-open", -6)
            add("dispute_close", "future-close", 2, -1, reference="current-open")
            verification["authentication"] = "unknown"
            completed = 1
    elif mechanism == "duplicate_identity":
        if variant < 2:
            add("release_committed", "prior-release", -4, reference=_release_key(task))
        else:
            old_task = {**task, "amount": task["amount"] - 1}
            add("release_committed", "old-price-release", -4, reference=_release_key(old_task))
            if variant == 3:
                add("release_committed", "future-release", 2, -1, reference=_release_key(task))
    elif mechanism == "retention_pressure":
        # The two directions are fixed construction hypotheses, not verified
        # candidate losses. No builder, decoder or policy is queried here.
        if variant >= 2:
            for event, offset in ((grant, -3), (delivery, -2), (verification, -1)):
                event["effective_at"] = event["observed_at"] = _time(decision + offset * unit)
        for index in range(12):
            offset = -11 + index // 2 if variant < 2 else -23 + index
            note = add("note", "memo-" + str(index).zfill(2) + "-" + tag, offset)
            note["issuer"] = "n-" + digest((tag + str(index)).encode())[:28]
            if variant < 2:
                note["subject"] = "s-" + digest((tag + "s" + str(index)).encode())[:28]
                note["object"] = "o-" + digest((tag + "o" + str(index)).encode())[:28]
            else:
                note["reference"] = "ref-" + digest((tag + "r" + str(index)).encode())[:28]
    else:
        if variant == 0:
            grant["subject"], grant["object"] = grant["object"], grant["subject"]
            add("grant", "foreign-issuer", -9, issuer=task["provider"])
        else:
            add("revoke", "reversed-revoke", -4,
                subject=task["delegate"], object=task["requester"])
            add("verification", "foreign-fail", -2, issuer=task["provider"], verdict="fail")

    if mechanism not in ("retention_pressure", "duplicate_identity") and number("future-note", 0, 1):
        add("note", "future-note", 2, -1, authentication="unknown")
    # Deliberately do not encode chronological priority in input list order.
    events.sort(key=lambda event: digest(seed + (domain + "/order/" + event["event_id"]).encode()))
    abbreviations = {"late_visibility": "late", "visible_authority_changes": "auth",
                     "verification_dispute": "dispute", "duplicate_identity": "duplicate",
                     "retention_pressure": "pressure", "role_direction": "direction"}
    trace = {"trace_id": "fresh-" + abbreviations[mechanism] + "-" + str(variant + 1).zfill(2),
             "mechanism": mechanism, "task": task, "cutoff": _time(decision), "decision_at": _time(decision),
             "events": events, "attempt_id": "attempt-" + str(variant + 1),
             "later_outcome": {"event_id": "private-outcome", "kind": "artifact_outcome",
                 "artifact_id": task["artifact_id"], "artifact_sha256": task["artifact_sha256"],
                 "completed_at": _time(decision + completed * unit), "artifact_valid": valid,
                 "revealed_at": _time(decision + 6 * unit), "basis": "owned_simulation_stipulation"}}
    require(len(events) <= 15 and len(canonical(trace)) <= 32768, "Generated case exceeds contract bounds")
    return trace


def bounded_json(value, maximum):
    raw = canonical(value) + b"\n"
    require(len(raw) <= maximum, "Serialized generation artifact exceeds byte bound")
    return raw


def _read(path, maximum):
    path = Path(path)
    require(not path.is_symlink(), "Input must not be a symlink")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= maximum, "Input must be a bounded regular file")
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "Input grew beyond byte bound")
    return raw


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("Nonfinite JSON number")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _keys(value, expected, name):
    require(type(value) is dict and set(value) == set(expected), "Invalid " + name + " fields")


def _hash(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "Invalid SHA-256")


def _utc(value):
    require(type(value) is str and len(value) <= 40, "Invalid UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0), "Timestamp must be UTC")
    return parsed


def validate_registration(registration, cohort_path, custody_path):
    """Shape and fixed limits only; the helper separately validates C7 lineage."""
    _keys(registration, {"schema_version", "registration_id", "phase", "cohort_id", "allocation", "origin",
        "contract_hashes", "source_hashes", "limits", "triage", "outputs", "execution_id", "frozen_at"}, "registration")
    require(type(registration["schema_version"]) is int and registration["schema_version"] == 1
            and registration["phase"] == "fresh_comparison" and registration["cohort_id"] == COHORT_ID,
            "Invalid fresh registration identity")
    for name in ("registration_id", "execution_id"):
        require(type(registration[name]) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", registration[name]) is not None,
                "Invalid registration/execution ID")
    require(canonical(registration["allocation"]) == canonical(ALLOCATION), "Mechanism allocation differs")
    require(canonical(registration["limits"]) == canonical(LIMITS), "Registered limits differ")
    require(canonical(registration["triage"]) == canonical(TRIAGE), "Registered triage differs")
    _keys(registration["source_hashes"], SOURCE_NAMES, "source hash")
    _keys(registration["contract_hashes"], {"decision_contract", "evaluation_contract"}, "contract hash")
    for value in (*registration["source_hashes"].values(), *registration["contract_hashes"].values()):
        _hash(value)
    origin = registration["origin"]
    _keys(origin, {"event_id", "event_hash", "artifact_sha256", "assessment_hash", "decision_assessment_hash", "implementation_hashes"}, "origin")
    require(type(origin["event_id"]) is str and 0 < len(origin["event_id"]) <= 200, "Invalid origin event ID")
    for field in ("event_hash", "artifact_sha256", "assessment_hash", "decision_assessment_hash"):
        _hash(origin[field])
    _keys(origin["implementation_hashes"], SOURCE_NAMES[:6], "historical implementation hash")
    for value in origin["implementation_hashes"].values():
        _hash(value)
    for name in SOURCE_NAMES[:3]:
        require(origin["implementation_hashes"][name] == registration["source_hashes"][name],
                "View, policy or evaluator differs from accepted C7 source")
    _keys(registration["outputs"], OUTPUT_NAMES, "output")
    paths = []
    for value in registration["outputs"].values():
        require(type(value) is str and 0 < len(value.encode()) <= 4096 and "\0" not in value,
                "Invalid registered output path")
        path = Path(value)
        require(path.is_absolute() and str(path) == str(path.resolve()), "Output paths must be canonical absolute paths")
        paths.append(value)
    require(len(set(paths)) == len(paths), "Registered output paths must be distinct")
    require(len({Path(path).parent for path in paths}) == 1, "Outputs must share the registration directory")
    require(registration["outputs"]["journal"] == registration["outputs"]["report"] + ".attempts.jsonl",
            "Journal path must match the fixed driver's output")
    for name, path in (("cohort", cohort_path), ("custody", custody_path)):
        require(registration["outputs"][name] == str(Path(path).absolute()), "Output differs from registration")
    require(_utc(registration["frozen_at"]) <= datetime.now(timezone.utc), "Registration freeze is in the future")


def _verify_sources(registration):
    here = Path(__file__).resolve().parent
    for name in SOURCE_NAMES:
        path = here / name if name.startswith("fresh-") else ENGINE / "epiphysics" / name
        raw = _read(path, MAX_SOURCE_BYTES)
        require(digest(raw) == registration["source_hashes"][name], "Frozen source differs: " + name)
        if name == "fresh-generator.py":
            require(raw == _SOURCE and compile(raw, __file__, "exec", dont_inherit=True,
                    optimize=sys.flags.optimize) == _MODULE_CODE, "Executing generator differs from frozen source")
    for role, filename in (("decision_contract", "decision-contract.json"),
                           ("evaluation_contract", "evaluation-contract.json")):
        require(digest(_read(here / filename, 131072)) == registration["contract_hashes"][role],
                "Frozen contract differs: " + role)


def case_truth(trace):
    """Independent schema and opportunity facts, with no candidate scoring."""
    from epiphysics import decision_evaluation as evaluation
    require(Path(evaluation.__file__).resolve() == ENGINE / "epiphysics" / "decision_evaluation.py",
            "Evaluator was imported from a different checkout")
    world = evaluation.resolve_world(trace)
    reference = evaluation.reference_decision(trace)
    return {"cases": 1, "world_opportunities": int(world["world_opportunity"]),
            "visible_actionable_opportunities": int(world["world_opportunity"] and reference["action"] == "release"),
            "forbidden_cases": int(not world["world_authorized"]),
            "duplicate_opportunity_cases": int(world["world_duplicate"]),
            "ordinary_attempts": int(not world["world_duplicate"]),
            "not_ready_or_invalid_cases": int(not world["artifact_ready_valid"])}


def _persist(stream, raw):
    stream.seek(0)
    stream.write(raw)
    stream.truncate()
    stream.flush()
    os.fsync(stream.fileno())


def generate(cohort_path, custody_path, registration_path, seed_file):
    """Custodian-only full generation. A claim or failure cannot be retried.

    The custody file is exclusively reserved first and records started/stopped
    preparation. On success it becomes the immutable generation receipt; the
    separate caller records first exposure without changing this receipt.
    """
    cohort_path, custody_path = Path(cohort_path).absolute(), Path(custody_path).absolute()
    require(cohort_path != custody_path, "Cohort and custody paths must differ")
    started_at = datetime.now(timezone.utc).isoformat()
    partial, cohort_stream, cohort_raw = [], None, b""
    # An existing custody receipt is never overwritten, including failed work.
    with custody_path.open("xb") as custody:
        _persist(custody, bounded_json({"schema_version": 1, "status": "started", "started_at": started_at,
                                      "cohort_path": str(cohort_path)}, MAX_REGISTRATION_BYTES))
        try:
            cohort_stream = cohort_path.open("xb")
            registration_raw = _read(registration_path, MAX_REGISTRATION_BYTES)
            registration = _json(registration_raw)
            validate_registration(registration, cohort_path, custody_path)
            require(Path(registration_path).resolve().parent == cohort_path.parent
                    and str(Path(registration_path).resolve()) not in registration["outputs"].values(),
                    "Registration must be a distinct input beside its outputs")
            require(not any(Path(path).exists() or Path(path).is_symlink() for name, path in registration["outputs"].items()
                            if name not in {"cohort", "custody"}), "An execution output already exists; generation refused")
            _verify_sources(registration)
            seed = parse_seed(_read(seed_file, 65))
            truth_counts = dict.fromkeys(TRUTH_FIELDS, 0)
            for mechanism, count in ALLOCATION.items():
                for variant in range(count):
                    trace = build_case(seed, mechanism, variant)
                    partial.append(trace)
                    for name, value in case_truth(trace).items():
                        truth_counts[name] += value
            require(len(partial) == 24 and len({case["trace_id"] for case in partial}) == 24,
                    "Fresh case identities/count differ")
            require(dict(Counter(case["mechanism"] for case in partial)) == ALLOCATION, "Fresh mechanism counts differ")
            cohort = {"schema_version": 1, "cohort_id": COHORT_ID, "contract_id": CONTRACT_ID,
                      "status": "fresh_exploratory", "trace_count": 24, "final_cohort_generated": True,
                      "allocation": dict(ALLOCATION), "traces": partial}
            cohort_raw = bounded_json(cohort, MAX_COHORT_BYTES)
            _persist(cohort_stream, cohort_raw)
            _verify_sources(registration)
            require(_read(registration_path, MAX_REGISTRATION_BYTES) == registration_raw, "Registration changed during generation")
            receipt = {"schema_version": 1, "status": "complete", "registration_sha256": digest(registration_raw),
                       "generator_sha256": digest(_SOURCE), "caller_sha256": registration["source_hashes"]["fresh-caller.py"],
                       # Commitment is to decoded 32 seed bytes, excluding hex/LF.
                       "seed_sha256": digest(seed), "cohort_sha256": digest(cohort_raw),
                       "cohort_canonical_sha256": digest(canonical(cohort)), "cohort_bytes": len(cohort_raw),
                       "case_ids": [case["trace_id"] for case in partial], "allocation": dict(ALLOCATION),
                       "truth_counts": truth_counts, "generated_at": datetime.now(timezone.utc).isoformat(),
                       "first_exposure": None, "execution_id": registration["execution_id"]}
            _persist(custody, bounded_json(receipt, MAX_REGISTRATION_BYTES))
            return receipt
        except BaseException as error:
            # Preserve constructed cases when validation stops before the final
            # cohort write. A bounded prefix is explicitly labelled in custody.
            truncated = False
            if cohort_stream is not None and not cohort_raw:
                attempted = canonical({"status": "stopped", "constructed_cases": partial}) + b"\n"
                truncated = len(attempted) > MAX_COHORT_BYTES
                cohort_raw = attempted[:MAX_COHORT_BYTES]
                _persist(cohort_stream, cohort_raw)
            retained = None
            if cohort_stream is not None:
                try:
                    cohort_stream.flush()
                    retained = _read(cohort_path, MAX_COHORT_BYTES)
                except (OSError, ValueError):
                    pass  # Never claim a memory-buffer hash proves persistence.
            failed = {"schema_version": 1, "status": "stopped", "started_at": started_at,
                      "stopped_at": datetime.now(timezone.utc).isoformat(), "error": type(error).__name__,
                      "message": str(error)[:400], "constructed_case_count": len(partial),
                      "retained_cohort_owned": cohort_stream is not None,
                      "retained_cohort_bytes": len(retained) if retained is not None else None,
                      "retained_cohort_sha256": digest(retained) if retained is not None else None,
                      "retained_prefix_truncated": truncated,
                      "rule": "Stopped preparation; no replacement seed, batch retry or candidate execution"}
            _persist(custody, bounded_json(failed, MAX_REGISTRATION_BYTES))
            raise
        finally:
            if cohort_stream is not None:
                cohort_stream.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", required=True, type=Path)
    parser.add_argument("--custody", required=True, type=Path)
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--seed-file", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = generate(args.cohort, args.custody, args.registration, args.seed_file)
    except (Exception, KeyboardInterrupt) as error:
        print(json.dumps({"status": "stopped", "error": type(error).__name__, "message": str(error)[:400]}))
        return 1
    print(json.dumps({"status": receipt["status"], "cohort_sha256": receipt["cohort_sha256"],
                      "custody": str(args.custody)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
