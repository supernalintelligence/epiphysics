"""Independent, pure oracle for the two proposed raw-source snapshot queries.

Authority: docs/planning/prospective-inputs.md and the pinned proposed declaration.
Only standard-library primitives are shared with other implementations. This module
neither imports their code nor treats their products as evidence. Callers retain
original inputs and returned bytes, including every failed attempt.
"""

import hashlib
import json
import math
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


DECLARATION_SHA256 = "ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65"
MANIFEST_LIMIT = 262_144
OUTPUT_LIMIT = 65_536
COMMON_FIELDS = ("subject_id", "knowledge_cutoff_utc", "outcome_cutoff_utc", "source_observation_ids")
RELEASE_FIELDS = ("seen_id_set", "opening_eligibility")
OBLIGATION_FIELDS = ("promisor_role_id", "beneficiary_role_id", "source_sha256", "quality_rule_hash", "acceptance_event_id", "authorized_submission_channel_id")
FAMILIES = ("software_component", "local_delivery_obligation")
RELEASE_URL = "https://api.github.com/repos/modelcontextprotocol/python-sdk/releases?per_page=5"
REQUEST_HEADERS = (
    ("Accept", "application/vnd.github+json"),
    ("X-GitHub-Api-Version", "2022-11-28"),
    ("Accept-Encoding", "identity"),
    ("User-Agent", "Epiphysics-Prospective-Integrity-Pilot-v1"),
)
RECEIPT_FIELDS = frozenset(("id", "kind", "content_sha256", "retained_byte_length", "observed_byte_length", "complete", "observed_at", "validated_at", "retained_at", "time_basis", "clock"))
CLOCK_FIELDS = frozenset(("start_utc", "start_ns", "observed_ns", "validated_ns", "retained_ns", "start_epoch", "end_epoch"))
HTTP_FIELDS = frozenset(("request_url", "request_method", "request_headers", "status_code", "completion", "headers_sha256", "headers_complete", "headers_observed_byte_length"))
BINDING_FIELDS = ("acceptance_event_id", "promisor_role_id", "beneficiary_role_id", "authorized_submission_channel_id", "quality_rule_hash", "quality_parameters", "source_sha256", "source_byte_length", "source_path", "source_blob_id", "git_object_format", "source_commit_id")
LOCAL_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)\Z")
HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


class OracleUnavailable(ValueError):
    """An operational bound prevented an answer; this is not malformed evidence."""


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, RecursionError, OverflowError, UnicodeError) as exc:
        raise OracleUnavailable("runtime_serialization_unavailable") from exc


def _integer_lexeme(token):
    try:
        return int(token)
    except ValueError as exc:
        raise OracleUnavailable("runtime_integer_unavailable") from exc


def _decimal_lexeme(token):
    try:
        exact = Decimal(token)
        number = float(token)
        if not math.isfinite(number) or Decimal(str(number)) != exact:
            raise OracleUnavailable("runtime_decimal_unavailable")
        return number
    except (InvalidOperation, OverflowError) as exc:
        raise OracleUnavailable("runtime_decimal_unavailable") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _nonfinite(_token):
    raise ValueError("nonfinite_json_literal")


def _json(raw, limit):
    if type(raw) is not bytes:
        raise ValueError("bytes_required")
    if len(raw) > limit:
        raise ValueError("byte_limit_exceeded")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(decoded, object_pairs_hook=_pairs, parse_int=_integer_lexeme,
                           parse_float=_decimal_lexeme, parse_constant=_nonfinite)
        # The raw contract does not permit silently rounded or unserializable JSON,
        # including numbers in unselected API fields. No source bytes are replaced.
        _canonical(value)
        return value
    except OracleUnavailable:
        raise
    except RecursionError as exc:
        raise OracleUnavailable("runtime_nesting_unavailable") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_json") from exc


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("wrong_object_fields")


def _id(value):
    if type(value) is not str or not value or len(value) > 200 or value.strip() != value:
        raise ValueError("invalid_id")
    return value


def _int(value):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_required")
    return value


def _bool(value):
    if type(value) is not bool:
        raise ValueError("boolean_required")


def _string(value):
    if type(value) is not str:
        raise ValueError("string_required")


def _digest(value, length=64):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{%d}" % length, value) is None:
        raise ValueError("invalid_digest")


def _version(value):
    if type(value) is not int or value != 1:
        raise ValueError("unsupported_schema_version")


def _time(value):
    if type(value) is not str or LOCAL_TIME.fullmatch(value) is None:
        raise ValueError("invalid_local_time")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_local_time") from exc


def _stamp(value):
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _micros(interval):
    return (interval.days * 86400 + interval.seconds) * 1_000_000 + interval.microseconds


def _receipt(value):
    if type(value) is not dict:
        raise ValueError("receipt_object_required")
    kind = value.get("kind")
    if kind not in ("question_contract", "release_sample", "acceptance", "source_blob"):
        raise ValueError("unknown_observation_kind")
    _keys(value, RECEIPT_FIELDS | ({"slot_id", "http"} if kind == "release_sample" else set()))
    _id(value["id"])
    _digest(value["content_sha256"])
    _int(value["retained_byte_length"])
    _int(value["observed_byte_length"])
    _bool(value["complete"])
    for key in ("observed_at", "validated_at", "retained_at"):
        _time(value[key])
    _string(value["time_basis"])
    clock = value["clock"]
    _keys(clock, CLOCK_FIELDS)
    _time(clock["start_utc"])
    for key in ("start_ns", "observed_ns", "validated_ns", "retained_ns"):
        _int(clock[key])
    _id(clock["start_epoch"])
    _id(clock["end_epoch"])
    if kind == "release_sample":
        _id(value["slot_id"])
        http = value["http"]
        _keys(http, HTTP_FIELDS)
        for key in ("request_url", "request_method", "completion"):
            _string(http[key])
        _int(http["status_code"])
        _int(http["headers_observed_byte_length"])
        _bool(http["headers_complete"])
        _digest(http["headers_sha256"])
        if type(http["request_headers"]) is not dict or any(type(v) is not str for v in http["request_headers"].values()):
            raise ValueError("invalid_request_headers")


def _clock_reasons(receipt):
    c = receipt["clock"]
    start = _time(c["start_utc"])
    times = [_time(receipt[k]) for k in ("observed_at", "validated_at", "retained_at")]
    ticks = [c[k] for k in ("observed_ns", "validated_ns", "retained_ns")]
    reasons = []
    if receipt["time_basis"] != "local_clock":
        reasons.append("unsupported_time_basis")
    if c["start_epoch"] != c["end_epoch"]:
        reasons.append("clock_epoch_mismatch")
    if [start] + times != sorted([start] + times) or [c["start_ns"]] + ticks != sorted([c["start_ns"]] + ticks):
        reasons.append("clock_order_invalid")
    if any(abs(_micros(t - start) * 1000 - (n - c["start_ns"])) > 1_000_000_000 for t, n in zip(times, ticks)):
        reasons.append("clock_elapsed_mismatch")
    return reasons


def _body_reasons(receipt, bodies, limit, cutoff=None):
    reasons = _clock_reasons(receipt)
    body = bodies.get(receipt["id"])
    if body is None:
        reasons.append("body_missing")
    else:
        if len(body) > limit or receipt["observed_byte_length"] > limit:
            reasons.append("body_over_limit")
        if len(body) != receipt["retained_byte_length"] or len(body) != receipt["observed_byte_length"]:
            reasons.append("body_length_mismatch")
        if _hash(body) != receipt["content_sha256"]:
            reasons.append("body_hash_mismatch")
    if not receipt["complete"]:
        reasons.append("body_incomplete")
    if cutoff is not None and _time(receipt["retained_at"]) > cutoff:
        reasons.append("after_knowledge_cutoff")
    return sorted(set(reasons))


def _question(raw):
    q = _json(raw, 65_536)
    _keys(q, ("schema_version", "family", "question_id", "subject_id", "knowledge_cutoff_utc", "forecast_deadline_utc", "outcome_cutoff_utc", "resolution_rule_id", "evidence"))
    _version(q["schema_version"])
    if q["family"] not in FAMILIES:
        raise ValueError("unsupported_family")
    for key in ("question_id", "subject_id", "resolution_rule_id"):
        _id(q[key])
    times = [_time(q[k]) for k in ("knowledge_cutoff_utc", "forecast_deadline_utc", "outcome_cutoff_utc")]
    if times != sorted(times):
        raise ValueError("question_deadline_order_invalid")
    if q["question_id"] == q["subject_id"]:
        raise ValueError("entity_identity_collision")
    e = q["evidence"]
    if q["family"] == "software_component":
        _keys(e, ("source_id", "request_url", "opening_slot_id", "slots"))
        _id(e["source_id"])
        _id(e["opening_slot_id"])
        if e["request_url"] != RELEASE_URL:
            raise ValueError("undeclared_release_url")
        if type(e["slots"]) is not list or not 1 <= len(e["slots"]) <= 16:
            raise ValueError("slot_count_invalid")
        names, instants = set(), set()
        for slot in e["slots"]:
            _keys(slot, ("id", "nominal_at"))
            name, instant = _id(slot["id"]), _time(slot["nominal_at"])
            if name in names or instant in instants:
                raise ValueError("duplicate_slot")
            names.add(name)
            instants.add(instant)
        opening = [s for s in e["slots"] if s["id"] == e["opening_slot_id"]]
        if not opening or _time(opening[0]["nominal_at"]) > times[0]:
            raise ValueError("opening_slot_invalid")
    else:
        _keys(e, ("acceptance_observation_id", "acceptance_sha256", "source_observation_id") + BINDING_FIELDS)
        _id(e["acceptance_observation_id"])
        _id(e["source_observation_id"])
        _digest(e["acceptance_sha256"])
        _binding(e)
    _entity_kinds(q)
    return q


def _binding(e):
    for key in ("acceptance_event_id", "promisor_role_id", "beneficiary_role_id", "authorized_submission_channel_id"):
        _id(e[key])
    _digest(e["quality_rule_hash"])
    _digest(e["source_sha256"])
    _int(e["source_byte_length"])
    if type(e["quality_parameters"]) is not dict:
        raise ValueError("quality_parameters_object_required")
    if e["git_object_format"] not in ("sha1", "sha256"):
        raise ValueError("unsupported_git_object_format")
    size = 40 if e["git_object_format"] == "sha1" else 64
    _digest(e["source_blob_id"], size)
    _digest(e["source_commit_id"], size)
    path = e["source_path"]
    if type(path) is not str or "\\" in path or "\x00" in path or not path.endswith(".md"):
        raise ValueError("invalid_source_path")
    parts = path.split("/")
    if len(parts) < 3 or parts[:2] not in (["docs", "theory"], ["docs", "research"], ["docs", "applications"]) or any(p in ("", ".", "..") for p in parts):
        raise ValueError("invalid_source_path")


def _entity_kinds(q):
    entities = {}
    pairs = [(q["question_id"], "question"), (q["subject_id"], q["family"])]
    if q["family"] == "local_delivery_obligation":
        e = q["evidence"]
        source_id = "source:" + _hash(_canonical([e["source_commit_id"], e["source_path"], e["source_blob_id"]]))
        pairs.extend(((e["promisor_role_id"], "role"), (e["beneficiary_role_id"], "role"),
                      (e["authorized_submission_channel_id"], "channel"), (source_id, "source")))
    for ident, kind in pairs:
        if ident in entities and entities[ident] != kind:
            raise ValueError("entity_identity_collision")
        entities[ident] = kind
    return entities


def _header_reasons(r, bodies):
    h = r["http"]
    reasons = []
    if h["request_url"] != RELEASE_URL or h["request_method"] != "GET" or h["request_headers"] != dict(REQUEST_HEADERS):
        reasons.append("http_request_binding_invalid")
    if h["status_code"] != 200:
        reasons.append("http_status_invalid")
    if h["completion"] != "completed":
        reasons.append("http_incomplete")
    if not h["headers_complete"]:
        reasons.append("headers_incomplete")
    raw = bodies.get(r["id"] + ":headers")
    if raw is None:
        return reasons + ["headers_missing"]
    if len(raw) > 16_384 or h["headers_observed_byte_length"] > 16_384:
        reasons.append("headers_over_limit")
    if len(raw) != h["headers_observed_byte_length"]:
        reasons.append("headers_length_mismatch")
    if _hash(raw) != h["headers_sha256"]:
        reasons.append("headers_hash_mismatch")
    if reasons:
        return reasons
    pairs = _json(raw, 16_384)
    if type(pairs) is not list:
        return ["headers_shape_invalid"]
    encodings = []
    for pair in pairs:
        if type(pair) is not list or len(pair) != 2 or any(type(v) is not str for v in pair):
            return ["headers_shape_invalid"]
        name, value = pair
        if HEADER_NAME.fullmatch(name) is None or any(c in value for c in "\r\n\x00"):
            return ["headers_field_invalid"]
        if name.lower() == "content-encoding":
            encodings.append(value.strip().lower())
    if encodings not in ([], ["identity"]):
        reasons.append("content_encoding_invalid")
    return reasons


def _release(r, bodies, cutoff, nominal):
    reasons = _body_reasons(r, bodies, 1_048_576, cutoff)
    c = r["clock"]
    start, observed = _time(c["start_utc"]), _time(r["observed_at"])
    if not 0 <= _micros(start - nominal) <= 60_000_000:
        reasons.append("request_start_outside_window")
    if not 0 <= _micros(observed - start) <= 10_000_000 or not 0 <= c["observed_ns"] - c["start_ns"] <= 10_000_000_000:
        reasons.append("request_duration_invalid")
    if any(_micros(_time(r[k]) - nominal) > 120_000_000 for k in ("observed_at", "validated_at", "retained_at")):
        reasons.append("slot_receipt_late")
    # Established body/clock/window ineligibility is conclusive. Unreadable
    # headers cannot turn an excluded attempt into potentially eligible history.
    if reasons:
        return None, sorted(set(reasons))
    reasons = _header_reasons(r, bodies)
    if reasons:
        return None, sorted(set(reasons))
    records = _json(bodies[r["id"]], 1_048_576)
    if type(records) is not list or len(records) > 5:
        raise ValueError("release_array_invalid")
    ids = set()
    for row in records:
        if type(row) is not dict or not {"id", "draft", "prerelease"} <= set(row):
            raise ValueError("release_record_invalid")
        if type(row["id"]) is not int or row["id"] <= 0:
            raise ValueError("release_id_invalid")
        _bool(row["draft"])
        _bool(row["prerelease"])
        if row["id"] in ids:
            raise ValueError("duplicate_release_id")
        ids.add(row["id"])
    return records, []


def _admission(entries, receipt, status, reasons=()):
    entries[receipt["id"]] = {"id": receipt["id"], "kind": receipt["kind"], "status": status, "reasons": sorted(set(reasons))}


def _known(packet, field, value, support):
    packet["answers"][field] = value
    packet["field_status"][field] = "known"
    packet["required_support"][field] = sorted(set(support))
    packet["unknown_reasons"].pop(field, None)


def _initialize_fields(packet, q, qid):
    family = q["family"]
    fields = COMMON_FIELDS + (RELEASE_FIELDS if family == FAMILIES[0] else OBLIGATION_FIELDS)
    packet["family"] = family
    packet["question_id"] = q["question_id"]
    packet["required_fields"] = list(fields)
    packet["inapplicable_fields"] = list(OBLIGATION_FIELDS if family == FAMILIES[0] else RELEASE_FIELDS)
    for field in fields:
        packet["answers"][field] = None
        packet["field_status"][field] = "oracle_unknown"
        packet["required_support"][field] = []
        packet["unknown_reasons"][field] = ["snapshot_unavailable"]
    _known(packet, "subject_id", q["subject_id"], [qid])
    for field in ("knowledge_cutoff_utc", "outcome_cutoff_utc"):
        _known(packet, field, _stamp(_time(q[field])), [qid])


def _release_queries(packet, q, receipts, bodies, entries, qid):
    if any(r["kind"] not in ("release_sample", "question_contract") for r in receipts):
        raise ValueError("observation_kind_not_in_family")
    slots = {s["id"]: _time(s["nominal_at"]) for s in q["evidence"]["slots"]}
    opening = q["evidence"]["opening_slot_id"]
    by_slot = {}
    for r in receipts:
        if r["kind"] == "release_sample":
            if r["slot_id"] not in slots or r["slot_id"] in by_slot:
                raise ValueError("release_slot_binding_invalid")
            by_slot[r["slot_id"]] = r
    missing = sorted(s for s in slots if slots[s] <= slots[opening] and s not in by_slot)
    packet["missing_slots"] = missing
    uncertain = bool(missing)
    samples = {}
    entities = _entity_kinds(q)
    for slot, r in by_slot.items():
        if slots[slot] > slots[opening]:
            _admission(entries, r, "excluded", ["after_opening_slot"])
            continue
        try:
            rows, reasons = _release(r, bodies, _time(q["knowledge_cutoff_utc"]), slots[slot])
            if reasons:
                _admission(entries, r, "excluded", reasons)
            else:
                _admission(entries, r, "admitted")
                samples[slot] = rows
        except OracleUnavailable as exc:
            uncertain = True
            _admission(entries, r, "unavailable", [str(exc)])
        except ValueError as exc:
            _admission(entries, r, "excluded", [str(exc)])
    # A cross-collection entity-kind conflict is an inconsistent snapshot,
    # not permission to discard a valid historical sample and shrink its IDs.
    for rows in samples.values():
        for row in rows:
            ident = "release:" + _hash(_canonical([q["subject_id"], row["id"]]))
            if ident in entities and entities[ident] != "release":
                raise ValueError("entity_identity_collision")
    if missing:
        packet["reasons"].append("declared_slot_receipt_missing")
    if opening not in samples:
        packet["reasons"].append("valid_opening_unavailable")
        return
    opening_id = by_slot[opening]["id"]
    _known(packet, "opening_eligibility", {str(row["id"]): not row["draft"] and not row["prerelease"] for row in samples[opening]}, [qid, opening_id])
    if uncertain:
        packet["reasons"].append("snapshot_membership_unknown")
        return
    support = [by_slot[s]["id"] for s in samples]
    _known(packet, "seen_id_set", sorted({row["id"] for rows in samples.values() for row in rows}), [qid] + support)
    _known(packet, "source_observation_ids", sorted([qid] + support), [qid] + support)


def _obligation_queries(packet, q, receipts, bodies, entries, qid):
    e = q["evidence"]
    aid, sid = e["acceptance_observation_id"], e["source_observation_id"]
    if len({qid, aid, sid}) != 3:
        raise ValueError("observation_identity_collision")
    expected = {qid: "question_contract", aid: "acceptance", sid: "source_blob"}
    if any(r["id"] not in expected or r["kind"] != expected[r["id"]] for r in receipts):
        raise ValueError("obligation_observation_binding_invalid")
    by_id = {r["id"]: r for r in receipts}
    valid = set()
    for ident, cap in ((aid, 65_536), (sid, 8192)):
        if ident not in by_id:
            packet["reasons"].append("required_observation_receipt_missing")
            continue
        r = by_id[ident]
        reasons = _body_reasons(r, bodies, cap, _time(q["knowledge_cutoff_utc"]))
        try:
            if not reasons and ident == aid:
                raw = bodies[aid]
                if _hash(raw) != e["acceptance_sha256"]:
                    reasons.append("acceptance_hash_mismatch")
                a = _json(raw, cap)
                _keys(a, ("schema_version", "obligation_id", "due_utc") + BINDING_FIELDS)
                _version(a["schema_version"])
                _id(a["obligation_id"])
                _binding(a)
                if a["obligation_id"] != q["subject_id"] or _time(a["due_utc"]) != _time(q["outcome_cutoff_utc"]):
                    reasons.append("acceptance_subject_or_due_mismatch")
                if any(_canonical(a[k]) != _canonical(e[k]) for k in BINDING_FIELDS):
                    reasons.append("acceptance_binding_mismatch")
            if not reasons and ident == sid:
                raw = bodies[sid]
                if _hash(raw) != e["source_sha256"] or len(raw) != e["source_byte_length"]:
                    reasons.append("source_hash_or_length_mismatch")
                try:
                    raw.decode("utf-8")
                except UnicodeError:
                    reasons.append("source_invalid_utf8")
                if b"\x00" in raw or not 256 <= len(raw) <= 8192:
                    reasons.append("source_byte_boundary_invalid")
                # Only LF partitions physical lines; CR and other Unicode breaks
                # remain byte content, and a terminal LF adds no empty line.
                if (raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)) > 128:
                    reasons.append("source_line_limit_exceeded")
                blob = hashlib.new(e["git_object_format"], b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
                if blob != e["source_blob_id"]:
                    reasons.append("source_blob_mismatch")
            if reasons:
                _admission(entries, r, "excluded", reasons)
            else:
                valid.add(ident)
                _admission(entries, r, "admitted")
        except OracleUnavailable as exc:
            _admission(entries, r, "unavailable", [str(exc)])
        except ValueError as exc:
            _admission(entries, r, "excluded", reasons + [str(exc)])
    if valid != {aid, sid}:
        packet["reasons"].append("valid_acceptance_and_source_required")
        return
    _known(packet, "source_observation_ids", sorted([qid, aid, sid]), [qid, aid, sid])
    for field in OBLIGATION_FIELDS:
        _known(packet, field, e[field], [qid, aid, sid] if field == "source_sha256" else [qid, aid])


def expected_queries_from_raw_sources(manifest_bytes, bodies):
    """Return bounded canonical expected answers/support, without side effects.

    Malformed manifest/receipt structure raises ValueError; operational inability
    at that boundary raises OracleUnavailable. Raw observation failures appear in
    the returned admissions and field-level oracle_unknown reasons. Receipt times
    and HTTP assertions are checked only for supplied internal consistency.
    """
    m = _json(manifest_bytes, MANIFEST_LIMIT)
    _keys(m, ("raw_input_schema_version", "declaration_sha256", "question_observation_id", "observations"))
    _version(m["raw_input_schema_version"])
    if m["declaration_sha256"] != DECLARATION_SHA256:
        raise ValueError("declaration_pin_mismatch")
    _id(m["question_observation_id"])
    if type(m["observations"]) is not list or not 1 <= len(m["observations"]) <= 18:
        raise ValueError("observation_count_invalid")
    if type(bodies) is not dict or any(type(k) is not str or type(v) is not bytes for k, v in bodies.items()):
        raise ValueError("plain_bytes_dictionary_required")
    receipts = m["observations"]
    ids, expected_keys = set(), set()
    for r in receipts:
        _receipt(r)
        if r["id"] in ids:
            raise ValueError("duplicate_observation_id")
        ids.add(r["id"])
        keys = {r["id"]} | ({r["id"] + ":headers"} if r["kind"] == "release_sample" else set())
        if expected_keys & keys:
            raise ValueError("body_key_identity_collision")
        expected_keys |= keys
    if set(bodies) - expected_keys:
        raise ValueError("undeclared_body_key")
    questions = [r for r in receipts if r["kind"] == "question_contract"]
    if len(questions) != 1 or questions[0]["id"] != m["question_observation_id"]:
        raise ValueError("question_observation_binding_invalid")
    if sum(r["kind"] == "release_sample" for r in receipts) > 16:
        raise ValueError("release_observation_count_invalid")
    p = {
        "oracle_schema_version": 1, "declaration_sha256": DECLARATION_SHA256,
        "manifest_sha256": _hash(manifest_bytes),
        "input_bodies": [{"key": k, "status": "supplied" if k in bodies else "missing", "byte_length": len(bodies[k]) if k in bodies else None, "sha256": _hash(bodies[k]) if k in bodies else None} for k in sorted(expected_keys)],
        "timing_assurance": "caller_claims_only", "independent_collection_verified": False,
        "status": "unavailable", "family": None, "question_id": None,
        "required_fields_by_family": {FAMILIES[0]: list(COMMON_FIELDS + RELEASE_FIELDS), FAMILIES[1]: list(COMMON_FIELDS + OBLIGATION_FIELDS)},
        "required_fields": [], "inapplicable_fields": [], "answers": {}, "field_status": {},
        "required_support": {}, "unknown_reasons": {}, "eligible_observation_ids": [],
        "observations": [], "missing_slots": [], "reasons": [],
    }
    entries = {}
    qr = questions[0]
    qid = qr["id"]
    reasons = _body_reasons(qr, bodies, 65_536)
    q = None
    if not reasons:
        try:
            q = _question(bodies[qid])
            if _time(qr["retained_at"]) > _time(q["knowledge_cutoff_utc"]):
                reasons.append("question_after_knowledge_cutoff")
        except OracleUnavailable as exc:
            _admission(entries, qr, "unavailable", [str(exc)])
            reasons.append(str(exc))
        except ValueError as exc:
            reasons.append(str(exc))
    if reasons:
        if qid not in entries:
            _admission(entries, qr, "excluded", reasons)
        p["reasons"] = ["question_contract_unavailable"] + reasons
        for r in receipts:
            if r["id"] != qid:
                _admission(entries, r, "unavailable", ["question_contract_unavailable"])
    else:
        _admission(entries, qr, "admitted")
        _initialize_fields(p, q, qid)
        if q["family"] == FAMILIES[0]:
            _release_queries(p, q, receipts, bodies, entries, qid)
        else:
            _obligation_queries(p, q, receipts, bodies, entries, qid)
    p["observations"] = [entries[k] for k in sorted(entries)]
    p["eligible_observation_ids"] = sorted(k for k, v in entries.items() if v["status"] == "admitted")
    if p["required_fields"] and all(s == "known" for s in p["field_status"].values()):
        p["status"] = "available"
    p["reasons"] = sorted(set(p["reasons"]))
    for field in p["unknown_reasons"]:
        p["unknown_reasons"][field] = p["reasons"] or ["snapshot_unavailable"]
    encoded = _canonical(p)
    if len(encoded) > OUTPUT_LIMIT:
        raise OracleUnavailable("oracle_output_limit_unavailable")
    return encoded
