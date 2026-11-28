"""Conditional supplied-byte capture/content evidence, never provenance authority.

The caller must separately establish approved loaded code/runtime and authentic
capture/ledger provenance. Matching caller-supplied anchors cannot establish it.
No filesystem, ledger, clock, capture, producer or publication operation occurs.
"""

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import math
import re

from .prospective_quality import QualityResult, check_line_index


EVALUATION_CONTRACT = "captured-line-index-evidence-v1"
INPUT_CAPS = {"expected": 16384, "claim": 65536, "terminal": 65536,
              "receipt": 65536, "source": 8192, "stdout": 65536}
OUTPUT_CAP = 4096
_MAX_INTEGER = 2**63 - 1
_BINDING = {"instance_id", "question_id", "slot_id", "channel_id", "acceptance_sha256",
            "declaration_sha256", "source_sha256", "schema_sha256", "producer_sha256", "worker_sha256"}
_FIRSTNESS_SCOPE = "this local ledger, instance and channel; no registration authentication"


class _Unavailable(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise _Unavailable(reason)


def _canonical(value):
    # Exact store.canonical semantics, without store's import-time source read.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "metadata_duplicate_key")
        value[key] = item
    return value


def _parse_integer(token):
    _require(len(token) <= 20, "metadata_number")
    value = int(token)
    _require(abs(value) <= _MAX_INTEGER, "metadata_number")
    return value


def _nonfinite(_token):
    raise _Unavailable("metadata_number")


def _load(raw):
    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs,
                       parse_int=_parse_integer, parse_constant=_nonfinite)
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(count <= 4096 and depth <= 32, "metadata_capacity")
        if type(item) is dict:
            pending.extend((part, depth + 1) for pair in item.items() for part in pair)
        elif type(item) is list:
            pending.extend((part, depth + 1) for part in item)
        elif type(item) is str:
            _require(len(item) <= 4096, "metadata_capacity")
        elif type(item) is float:
            _require(math.isfinite(item) and abs(item) <= _MAX_INTEGER, "metadata_number")
    _require(_canonical(value) == raw, "metadata_noncanonical")
    return value


def _keys(value, fields):
    _require(type(value) is dict and set(value) == fields, "metadata_schema")


def _integer(value, minimum=0, maximum=_MAX_INTEGER):
    _require(type(value) is int and minimum <= value <= maximum, "metadata_schema")


def _boolean(value):
    _require(type(value) is bool, "metadata_schema")


def _string(value, maximum=4096):
    _require(type(value) is str and 0 < len(value) <= maximum, "metadata_schema")


def _hash(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "metadata_schema")


def _time(value):
    _string(value, 64)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "metadata_schema")
    return parsed


def _stamp(value, optional=False):
    if optional and value is None:
        return
    _keys(value, {"utc", "monotonic"})
    _time(value["utc"])
    _require(type(value["monotonic"]) in (int, float)
             and math.isfinite(value["monotonic"]), "metadata_schema")


def _binding(value):
    _keys(value, _BINDING)
    for key, item in value.items():
        if key.endswith("_id"):
            _require(type(item) is str and re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", item) is not None,
                     "metadata_schema")
        else:
            _hash(item)


def _runtime(value):
    _keys(value, {"path", "sha256", "version"})
    _string(value["path"])
    _require(value["path"].startswith("/"), "metadata_schema")
    _hash(value["sha256"])
    _string(value["version"], 1024)


def _event(value, kind):
    _keys(value, {"seq", "id", "kind", "recorded_at", "body", "previous_hash", "hash"})
    _integer(value["seq"], 1)
    _string(value["id"], 200)
    _require(value["kind"] == kind, "event_kind")
    _time(value["recorded_at"])
    _hash(value["previous_hash"])
    _hash(value["hash"])
    payload = {key: value[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}
    _require(_digest(_canonical(payload)) == value["hash"], "event_hash")


def _clock(value):
    _keys(value, {"consistent", "observations", "violation_count", "first_violation"})
    _boolean(value["consistent"])
    _integer(value["observations"], 1)
    _integer(value["violation_count"], 0, value["observations"])
    _stamp(value["first_violation"], optional=True)
    _require(value["consistent"] == (value["violation_count"] == 0)
             and (value["first_violation"] is None) == value["consistent"], "metadata_schema")


def _errors(value, close_only=False):
    _require(type(value) is list and len(value) <= 16, "metadata_schema")
    for error in value:
        _require(type(error) is dict, "metadata_schema")
        fields = {"operation", "error_type"}
        if "native_close_uncertain" in error or close_only:
            fields.add("native_close_uncertain")
        _keys(error, fields)
        _string(error["operation"], 120)
        _string(error["error_type"], 120)
        if "native_close_uncertain" in error:
            _require(error["native_close_uncertain"] is True, "metadata_schema")


def _stream(value, cap, path):
    _keys(value, {"observed_prefix_bytes", "observed_prefix_sha256", "retained_bytes", "retained_sha256",
                  "observed_bytes_lower_bound", "eof_observed", "complete_bytes_observed", "full_sha256",
                  "first_byte_observed", "last_byte_observed", "file_durable_observed", "path", "retention_verified"})
    for key in ("eof_observed", "complete_bytes_observed", "retention_verified"):
        _boolean(value[key])
    _integer(value["observed_prefix_bytes"], 0, cap)
    _integer(value["observed_bytes_lower_bound"])
    _hash(value["observed_prefix_sha256"])
    _require(value["path"] == path, "capture_path_binding")
    for key in ("first_byte_observed", "last_byte_observed", "file_durable_observed"):
        _stamp(value[key], optional=True)
    count = value["observed_bytes_lower_bound"]
    complete = value["eof_observed"] and count <= cap
    _require(value["observed_prefix_bytes"] == min(count, cap)
             and value["complete_bytes_observed"] == complete, "stream_consistency")
    _require((value["first_byte_observed"] is None) == (count == 0)
             and (value["last_byte_observed"] is None) == (count == 0), "stream_consistency")
    if complete:
        _require(value["full_sha256"] == value["observed_prefix_sha256"], "stream_consistency")
    else:
        _require(value["full_sha256"] is None, "stream_consistency")
    if value["retained_bytes"] is None:
        _require(value["retained_sha256"] is None and not value["retention_verified"], "stream_consistency")
    else:
        _integer(value["retained_bytes"], 0, cap)
        _hash(value["retained_sha256"])
    if value["retention_verified"]:
        _require(value["file_durable_observed"] is not None
                 and value["retained_bytes"] == value["observed_prefix_bytes"]
                 and value["retained_sha256"] == value["observed_prefix_sha256"], "stream_consistency")


def _metadata(expected, claim, terminal, receipt):
    _keys(expected, {"schema_version", "binding", "source_byte_length", "capture_sha256", "runtime",
                     "claim_bytes_sha256", "terminal_bytes_sha256"})
    _require(type(expected["schema_version"]) is int and expected["schema_version"] == 1, "metadata_schema")
    _binding(expected["binding"])
    _integer(expected["source_byte_length"], 0, 8192)
    _runtime(expected["runtime"])
    for key in ("capture_sha256", "claim_bytes_sha256", "terminal_bytes_sha256"):
        _hash(expected[key])
    _event(claim, "prospective_capture_started")
    _event(terminal, "prospective_capture_finished")
    body = claim["body"]
    _keys(body, {"schema_version", "binding", "timing", "runtime", "capture_sha256", "channel_directory",
                 "epoch", "firstness_scope"})
    _require(type(body["schema_version"]) is int and body["schema_version"] == 1, "metadata_schema")
    _require(body["binding"] == expected["binding"] and body["runtime"] == expected["runtime"]
             and body["capture_sha256"] == expected["capture_sha256"], "capture_contract_binding")
    _require(body["firstness_scope"] == _FIRSTNESS_SCOPE, "metadata_schema")
    _require(type(body["epoch"]) is str and re.fullmatch(r"[0-9a-f]{32}", body["epoch"]) is not None, "metadata_schema")
    directory = body["channel_directory"]
    _string(directory)
    # Lexical validation only; no path resolution, existence check or traversal.
    _require(directory.startswith("/") and not directory.endswith("/")
             and all(part not in ("", ".", "..") for part in directory[1:].split("/"))
             and "\x00" not in directory, "metadata_schema")
    timing = body["timing"]
    _keys(timing, {"not_before", "latest_start", "artifact_due", "wall_seconds", "cleanup_seconds"})
    _require(_time(timing["not_before"]) <= _time(timing["latest_start"]) < _time(timing["artifact_due"]), "metadata_schema")
    for key, maximum in (("wall_seconds", 120), ("cleanup_seconds", 5)):
        _require(type(timing[key]) in (int, float) and math.isfinite(timing[key])
                 and 0 < timing[key] <= maximum, "metadata_schema")
    claim_id = "prospective-capture:" + _digest(_canonical([body["binding"]["instance_id"], body["binding"]["channel_id"]])) + ":first"
    _require(claim["id"] == claim_id and terminal["id"] == claim_id + ":finished"
             and terminal["seq"] > claim["seq"], "event_binding")
    end = terminal["body"]
    _keys(end, {"claim_id", "claim_hash", "receipt_path", "receipt_sha256", "receipt_file_durable_observed"})
    _hash(end["receipt_sha256"])
    _stamp(end["receipt_file_durable_observed"])
    _require(end["claim_id"] == claim_id and end["claim_hash"] == claim["hash"], "event_binding")
    _require(end["receipt_path"] == directory + "/receipt.json", "capture_path_binding")
    _keys(receipt, {"schema_version", "claim_id", "claim_hash", "epoch", "binding", "started", "ended", "pid",
                    "spawn_returned", "launch_requested", "launch_returned", "start_window_observed", "returncode",
                    "child_reaped", "wait_status", "wait_observed", "wait_status_unavailable", "termination", "errors",
                    "close_errors", "close_errors_truncated", "clock_interval_verified", "clock_observations",
                    "descendant_isolation", "quality", "obligation_outcome", "registered", "streams"})
    _require(type(receipt["schema_version"]) is int and receipt["schema_version"] == 1, "metadata_schema")
    _require(receipt["claim_id"] == claim_id and receipt["claim_hash"] == claim["hash"]
             and receipt["epoch"] == body["epoch"] and receipt["binding"] == expected["binding"], "receipt_binding")
    for key in ("spawn_returned", "start_window_observed", "child_reaped", "wait_status_unavailable",
                "close_errors_truncated", "clock_interval_verified"):
        _boolean(receipt[key])
    _require(receipt["descendant_isolation"] is False and receipt["registered"] is False
             and receipt["quality"] is None and receipt["obligation_outcome"] is None, "metadata_schema")
    for key in ("started", "ended"):
        _stamp(receipt[key])
    for key in ("launch_requested", "launch_returned", "wait_observed"):
        _stamp(receipt[key], optional=True)
    for key, low in (("pid", 1), ("returncode", -_MAX_INTEGER), ("wait_status", 0)):
        if receipt[key] is not None:
            _integer(receipt[key], low)
    if receipt["termination"] is not None:
        _require(receipt["termination"] in {"wall_timeout", "stdout_overflow", "stderr_overflow", "parent_deadline",
                                             "capture_error", "wait_status_unavailable"}, "metadata_schema")
    _errors(receipt["errors"])
    _errors(receipt["close_errors"], close_only=True)
    _clock(receipt["clock_observations"])
    _require(receipt["clock_interval_verified"] == receipt["clock_observations"]["consistent"], "metadata_schema")
    _keys(receipt["streams"], {"stdout", "stderr"})
    _stream(receipt["streams"]["stdout"], 65536, directory + "/stdout.bin")
    _stream(receipt["streams"]["stderr"], 16384, directory + "/stderr.bin")


def assess_captured_artifact(*, expected_bytes, claim_bytes, terminal_bytes,
                             receipt_bytes, source_bytes, stdout_bytes) -> bytes:
    """Return <=4096 canonical bytes of conditional consistency/content evidence.

Exactly six supplied bytes-or-None inputs; accepted aggregate <=286720 bytes.
Only complete nonempty, consistently retained stdout enters the unchanged C20
checker. Expected anchors are caller assumptions, not authentication. Python
cancellation propagates. No return/exception establishes obligation outcome,
firstness, rights, time, registration, publication or permission to continue.
    """
    inputs = {"expected": expected_bytes, "claim": claim_bytes, "terminal": terminal_bytes,
              "receipt": receipt_bytes, "source": source_bytes, "stdout": stdout_bytes}
    identities = {}
    first_problem = None
    for name, raw in inputs.items():
        identities[name] = {"sha256": None, "byte_length": len(raw) if type(raw) is bytes else None}
        problem = "missing_" + name if raw is None else "input_type_" + name if type(raw) is not bytes else None
        if type(raw) is bytes:
            if len(raw) > INPUT_CAPS[name]:
                problem = "input_capacity_" + name
            else:
                try:
                    identities[name]["sha256"] = _digest(raw)
                except (MemoryError, RecursionError, OverflowError):
                    problem = "input_identity_unavailable"
        first_problem = first_problem or problem
    result = {"schema_version": 1, "evaluation_contract": EVALUATION_CONTRACT,
              "scope": "conditional_supplied_byte_consistency_and_content",
              "status": "unavailable", "reason": first_problem,
              "input_identities": identities, "quality_result": None,
              "observed_stdout_bytes_lower_bound": None,
              "publication": "not_assessed", "firstness": "not_established",
              "obligation_outcome": None, "continuation_allowed": False}

    def finish():
        raw = _canonical(result)
        # Fixed fields, fixed enums, six bounded identities, one C20 result.
        if len(raw) > OUTPUT_CAP:
            raise RuntimeError("quality evidence output contract exceeded")
        return raw

    if first_problem:
        return finish()
    try:
        expected, claim, terminal, receipt = (_load(inputs[name]) for name in ("expected", "claim", "terminal", "receipt"))
        _metadata(expected, claim, terminal, receipt)
        _require(identities["claim"]["sha256"] == expected["claim_bytes_sha256"]
                 and identities["terminal"]["sha256"] == expected["terminal_bytes_sha256"], "caller_event_anchor")
        _require(identities["receipt"]["sha256"] == terminal["body"]["receipt_sha256"], "receipt_hash")
        _require(identities["source"]["sha256"] == expected["binding"]["source_sha256"]
                 and len(source_bytes) == expected["source_byte_length"], "source_binding")
        stream = receipt["streams"]["stdout"]
        result["observed_stdout_bytes_lower_bound"] = stream["observed_bytes_lower_bound"]
        _require(stream["retention_verified"], "stdout_retention_unverified")
        _require(len(stdout_bytes) == stream["retained_bytes"] == stream["observed_prefix_bytes"]
                 and identities["stdout"]["sha256"] == stream["retained_sha256"] == stream["observed_prefix_sha256"],
                 "stdout_binding")
        if stream["observed_bytes_lower_bound"] > 65536:
            result.update(status="overflow_observed", reason="stdout_overflow_no_content_check")
            return finish()
        _require(stream["complete_bytes_observed"], "stdout_incomplete")
        _require(stream["observed_bytes_lower_bound"] == len(stdout_bytes)
                 and stream["full_sha256"] == identities["stdout"]["sha256"], "stdout_binding")
        if not stdout_bytes:
            result.update(status="closed_empty", reason="zero_bytes_no_content_check")
            return finish()
    except _Unavailable as error:
        result["reason"] = str(error)
        return finish()
    except (MemoryError, RecursionError, OverflowError):
        result["reason"] = "metadata_capacity"
        return finish()
    except (ValueError, TypeError, UnicodeError):
        result["reason"] = "metadata_invalid"
        return finish()

    try:
        quality = check_line_index(source_bytes, stdout_bytes)
    except Exception:
        result["reason"] = "checker_error"
        return finish()
    reasons = {True: {"matches"}, False: {"artifact_utf8", "artifact_json", "artifact_duplicate_key",
                                        "artifact_nonfinite", "artifact_schema", "content_mismatch"},
               None: {"checker_capacity"}}
    if (type(quality) is not QualityResult or type(quality.quality) not in (bool, type(None))
            or type(quality.reason) is not str or quality.reason not in reasons[quality.quality]
            or type(quality.source_sha256) is not str or quality.source_sha256 != identities["source"]["sha256"]
            or type(quality.source_byte_length) is not int or quality.source_byte_length != len(source_bytes)
            or type(quality.artifact_sha256) is not str or quality.artifact_sha256 != identities["stdout"]["sha256"]
            or type(quality.artifact_byte_length) is not int or quality.artifact_byte_length != len(stdout_bytes)):
        result["reason"] = "checker_contract_mismatch"
        return finish()
    result.update(status="checked" if quality.quality is not None else "unavailable",
                  reason="content_checked" if quality.quality is not None else "checker_unavailable",
                  quality_result=asdict(quality))
    return finish()
