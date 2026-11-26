"""Evidence-bound assertions and historical projections over the existing ledger.

Spans address bytes, not characters. Source validity is a claimed world interval;
recorded_at is local knowledge time. Neither matching bytes nor a retained claim
establishes truth or an independently witnessed collection time.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import math
import re
import sys
from pathlib import Path

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import store
from .store import canonical, digest, instant

IMPLEMENTATION_DEPENDENCIES = ((store.__name__, store.IMPLEMENTATION_CODE),)


MAX_SPANS = 100
BASES = {"observed", "reported", "inferred"}
BODY_FIELDS = {"schema_version", "snapshot_id", "subject", "predicate", "object", "observer", "method",
               "spans", "basis", "valid_from", "valid_to", "supersedes", "contradicts"}


def _text(value, label):
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _time(value, label):
    _text(value, label)
    try:
        return instant(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{label} must be a timezone-aware timestamp") from error


def _hash(value, label):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _span_shape(span):
    if type(span) is not dict or set(span) != {"observation_id", "start", "end", "sha256"}:
        raise ValueError("Span requires observation_id, start, end, and sha256")
    _text(span["observation_id"], "Span observation_id")
    if type(span["start"]) is not int or type(span["end"]) is not int or not 0 <= span["start"] < span["end"]:
        raise ValueError("Span bounds must be integer byte offsets with 0 <= start < end")
    _hash(span["sha256"], "Span sha256")


def _body_shape(body):
    if type(body) is not dict or set(body) != BODY_FIELDS or type(body["schema_version"]) is not int or body["schema_version"] != 1:
        raise ValueError("Invalid assertion schema_version 1 body")
    for field in ("snapshot_id", "subject", "predicate", "observer", "method"):
        _text(body[field], field)
    if type(body["basis"]) is not str or body["basis"] not in BASES:
        raise ValueError("Assertion basis must be observed, reported, or inferred")
    obj = body["object"]
    if type(obj) is not dict:
        raise ValueError("Assertion object must be typed")
    if obj.get("kind") == "entity" and set(obj) == {"kind", "id"}:
        _text(obj["id"], "Object entity id")
    elif obj.get("kind") == "value" and set(obj) == {"kind", "value", "unit"}:
        value = obj["value"]
        if type(value) not in (str, int, float, bool, type(None)) or (type(value) is float and not math.isfinite(value)):
            raise ValueError("Object value must be a finite JSON scalar")
        if obj["unit"] is not None:
            _text(obj["unit"], "Object unit")
    else:
        raise ValueError("Object requires either entity kind/id or value kind/value/unit")
    spans = body["spans"]
    if type(spans) is not list or not 1 <= len(spans) <= MAX_SPANS:
        raise ValueError(f"Assertion requires 1–{MAX_SPANS} spans")
    for span in spans:
        _span_shape(span)
    if len({canonical(span) for span in spans}) != len(spans):
        raise ValueError("Duplicate assertion span")
    start = _time(body["valid_from"], "valid_from") if body["valid_from"] is not None else None
    end = _time(body["valid_to"], "valid_to") if body["valid_to"] is not None else None
    if start is not None and end is not None and end <= start:
        raise ValueError("valid_to must follow valid_from")
    if body["supersedes"] is not None:
        _text(body["supersedes"], "supersedes")
    links = body["contradicts"]
    if type(links) is not list or len(links) > 100:
        raise ValueError("contradicts must be an array of at most 100 assertion IDs")
    for target in links:
        _text(target, "contradicts target")
    if len(links) != len(set(links)):
        raise ValueError("Duplicate contradicts target")
    try:
        canonical(body)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError("Assertion must contain finite JSON values") from error


def _event_integrity(event):
    payload = {key: event[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}
    if digest(canonical(payload).encode("utf-8")) != event["hash"]:
        raise ValueError(f"Event hash mismatch: {event['id']}")


@contextmanager
def _read_transaction(ledger):
    own = not ledger.db.in_transaction
    if own:
        ledger.db.execute("BEGIN")
    try:
        yield
    except Exception:
        if own:
            ledger.db.rollback()
        raise
    else:
        if own:
            ledger.db.commit()


def _snapshot(ledger, snapshot_id, now):
    _text(snapshot_id, "snapshot_id")
    snapshot = ledger.get(snapshot_id, "snapshot")
    _event_integrity(snapshot)
    body = snapshot["body"]
    if type(body) is not dict or set(body) != {"cutoff", "observations", "manifest_hash", "watermark"}:
        raise ValueError("Invalid snapshot manifest")
    cutoff = _time(body["cutoff"], "Snapshot cutoff")
    created = _time(snapshot["recorded_at"], "Snapshot recorded_at")
    if cutoff > created or created > now:
        raise ValueError("Snapshot is not available at this knowledge time")
    manifest = body["observations"]
    if type(manifest) is not list or type(body["watermark"]) is not int or not 0 <= body["watermark"] < snapshot["seq"]:
        raise ValueError("Invalid snapshot manifest or watermark")
    _hash(body["manifest_hash"], "Snapshot manifest_hash")
    if digest(canonical(manifest).encode("utf-8")) != body["manifest_hash"]:
        raise ValueError("Snapshot manifest hash mismatch")
    entries = {}
    for entry in manifest:
        if type(entry) is not dict or set(entry) != {"id", "event_hash", "content_hash"}:
            raise ValueError("Invalid snapshot manifest entry")
        oid = _text(entry["id"], "Manifest observation id")
        if oid in entries:
            raise ValueError("Duplicate snapshot observation")
        _hash(entry["event_hash"], "Manifest event_hash")
        _hash(entry["content_hash"], "Manifest content_hash")
        entries[oid] = entry
    return snapshot, entries


def _resolve(ledger, snapshot, entries, span):
    _span_shape(span)
    oid = span["observation_id"]
    if oid not in entries:
        raise ValueError("Span observation must belong to the selected snapshot")
    observation = ledger.get(oid, "observation")
    _event_integrity(observation)
    entry = entries[oid]
    body = observation["body"]
    if entry["event_hash"] != observation["hash"] or entry["content_hash"] != body.get("content_hash"):
        raise ValueError("Snapshot manifest does not match the observation record")
    if (observation["seq"] >= snapshot["seq"] or observation["seq"] > snapshot["body"]["watermark"]
            or _time(observation["recorded_at"], "Observation recorded_at") > _time(snapshot["body"]["cutoff"], "Snapshot cutoff")):
        raise ValueError("Observation is not eligible at the snapshot cutoff")
    path = ledger.root / "blobs" / entry["content_hash"]
    if path.is_symlink():
        raise ValueError("Source blob must be a regular file, not a symlink")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError("Source blob is missing or unreadable") from error
    if digest(raw) != entry["content_hash"] or type(body.get("size")) is not int or len(raw) != body["size"]:
        raise ValueError("Source blob hash or size mismatch")
    if span["end"] > len(raw):
        raise ValueError("Span exceeds source byte bounds")
    selected = raw[span["start"]:span["end"]]
    if digest(selected) != span["sha256"]:
        raise ValueError("Span hash mismatch")
    return selected


def resolve_span(ledger, snapshot_id, span) -> bytes:
    """Resolve a nonempty byte range, verifying its snapshot, source, and span hashes."""
    with _read_transaction(ledger):
        snapshot, entries = _snapshot(ledger, snapshot_id, _time(ledger.clock(), "Ledger clock"))
        return _resolve(ledger, snapshot, entries, span)


def record_assertion(ledger, snapshot_id, *, subject, predicate, object, observer, method, spans, basis,
                     valid_from=None, valid_to=None, supersedes=None, contradicts=None, event_id=None):
    """Append a source-bound claim; corrections retain history and cannot fork a lineage."""
    if event_id is not None:
        _text(event_id, "event_id")
    body = deepcopy({"schema_version": 1, "snapshot_id": snapshot_id, "subject": subject,
        "predicate": predicate, "object": object, "observer": observer, "method": method,
        "spans": spans, "basis": basis, "valid_from": valid_from, "valid_to": valid_to,
        "supersedes": supersedes, "contradicts": [] if contradicts is None else contradicts})
    _body_shape(body)

    def validate(recorded_at):
        now = _time(recorded_at, "Assertion recorded_at")
        snapshot, entries = _snapshot(ledger, snapshot_id, now)
        for span in body["spans"]:
            _resolve(ledger, snapshot, entries, span)
        for target in body["contradicts"]:
            previous = ledger.get(target, "assertion")
            _event_integrity(previous)
            _body_shape(previous["body"])
        if supersedes is not None:
            previous = ledger.get(supersedes, "assertion")
            _event_integrity(previous)
            _body_shape(previous["body"])
            if previous["body"]["observer"] != body["observer"]:
                raise ValueError("A supersession lineage must preserve its observer")
            old_snapshot, _ = _snapshot(ledger, previous["body"]["snapshot_id"], now)
            if _time(old_snapshot["body"]["cutoff"], "Previous cutoff") > _time(snapshot["body"]["cutoff"], "Snapshot cutoff"):
                raise ValueError("Cannot regress a supersession lineage to an earlier snapshot cutoff")
            if any(event["body"].get("supersedes") == supersedes for event in ledger.events("assertion")):
                raise ValueError("A correction must supersede the latest assertion revision")

    # Ledger.append returns identical event IDs before this mutable validation runs.
    return ledger.append("assertion", body, event_id, validate=validate)


def assertions_as_of(ledger, known_at, valid_at=None, observer=None) -> list[dict]:
    """Project visible unsuperseded claims, then filter their half-open world intervals.

    known_at cannot exceed the local ledger clock. Contradictions remain separate
    claims; this function neither ranks them nor infers a winning truth value.
    """
    known = _time(known_at, "known_at")
    valid = _time(valid_at, "valid_at") if valid_at is not None else None
    if observer is not None:
        _text(observer, "observer")
    with _read_transaction(ledger):
        if known > _time(ledger.clock(), "Ledger clock"):
            raise ValueError("Cannot query a future knowledge time")
        visible = [event for event in ledger.events("assertion") if _time(event["recorded_at"], "Assertion recorded_at") <= known]
        for event in visible:
            _event_integrity(event)
            _body_shape(event["body"])
        retired = {event["body"]["supersedes"] for event in visible if event["body"]["supersedes"] is not None}
        result = []
        for event in visible:
            body = event["body"]
            if event["id"] in retired or (observer is not None and body["observer"] != observer):
                continue
            if valid is not None:
                if body["valid_from"] is not None and valid < _time(body["valid_from"], "valid_from"):
                    continue
                if body["valid_to"] is not None and valid >= _time(body["valid_to"], "valid_to"):
                    continue
            result.append(event)
        return result
