"""Execute small synthetic contracts against the actual assertion implementation.

These are capability checks, not evidence of extraction accuracy or business lift.
Each check uses a new temporary ledger; no production ledger is mutated.
"""
from __future__ import annotations

from contextlib import contextmanager
from tempfile import TemporaryDirectory
from pathlib import Path
import sys

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import assertions, store
from .store import Ledger, digest

IMPLEMENTATION_DEPENDENCIES = tuple(
    (module.__name__, module.IMPLEMENTATION_CODE) for module in (store, assertions)
)


@contextmanager
def _fixture():
    clock = ["2026-11-24T10:00:00+00:00"]
    with TemporaryDirectory(prefix="epiphysics-span-check-") as directory:
        ledger = Ledger(directory, clock=lambda: clock[0])
        try:
            content = "Café owes 12 USD. Revision pending.".encode("utf-8")
            observation = ledger.capture("synthetic:span-check", content, event_id="source-initial")
            snapshot = ledger.snapshot(event_id="snapshot-initial")
            end = content.index(b".") + 1
            span = {"observation_id": observation["id"], "start": 0, "end": end, "sha256": digest(content[:end])}
            yield ledger, clock, observation, snapshot, span, content
        finally:
            ledger.close()


def _record(ledger, snapshot, span, **changes):
    arguments = {"subject": "service-a", "predicate": "invoice-amount",
                 "object": {"kind": "value", "value": 12, "unit": "USD"},
                 "observer": "probe-observer", "method": "synthetic-source-span-probe", "basis": "reported",
                 "spans": [span]}
    arguments.update(changes)
    return assertions.record_assertion(ledger, snapshot["id"], **arguments)


def _rejected_without_append(ledger, operation):
    before = len(ledger.events())
    try:
        operation()
    except ValueError:
        return len(ledger.events()) == before
    return False


def _exact_bytes(ledger, clock, observation, snapshot, span, content):
    return assertions.resolve_span(ledger, snapshot["id"], span) == content[:span["end"]]


def _typed_record(ledger, clock, observation, snapshot, span, content):
    clock[0] = "2026-11-24T10:01:00+00:00"
    record = _record(ledger, snapshot, span, event_id="typed-assertion")
    stored = ledger.get(record["id"], "assertion")
    return (stored["body"]["object"] == {"kind": "value", "value": 12, "unit": "USD"}
            and stored["body"]["spans"] == [span] and stored["body"]["snapshot_id"] == snapshot["id"])


def _bad_span(change):
    def check(ledger, clock, observation, snapshot, span, content):
        changed = {**span, **change(content)}
        return _rejected_without_append(ledger, lambda: _record(ledger, snapshot, changed))
    return check


def _corrupted_blob(ledger, clock, observation, snapshot, span, content):
    # Corrupt bytes outside the requested span: checking only the span is insufficient.
    path = ledger.root / "blobs" / observation["body"]["content_hash"]
    path.write_bytes(content[:-1] + b"!")
    return _rejected_without_append(ledger, lambda: _record(ledger, snapshot, span))


def _late_evidence(ledger, clock, observation, snapshot, span, content):
    clock[0] = "2026-11-24T10:02:00+00:00"
    late = ledger.capture("synthetic:late-report", b"A later report.", published_at="2020-01-01T00:00:00+00:00")
    late_span = {"observation_id": late["id"], "start": 0, "end": 4, "sha256": digest(b"A la")}
    return _rejected_without_append(ledger, lambda: _record(ledger, snapshot, late_span))


def _history(ledger, clock, observation, snapshot, span, content):
    clock[0] = "2026-11-24T10:01:00+00:00"
    original = _record(ledger, snapshot, span, event_id="assertion-original")
    clock[0] = "2026-11-24T10:02:00+00:00"
    contrary_bytes = b"Reporter B says the amount is 20 USD."
    contrary = ledger.capture("synthetic:other-reporter", contrary_bytes)
    contrary_snapshot = ledger.snapshot()
    contrary_span = {"observation_id": contrary["id"], "start": 0, "end": len(contrary_bytes), "sha256": digest(contrary_bytes)}
    opposing = _record(ledger, contrary_snapshot, contrary_span, event_id="assertion-opposing", observer="other-observer",
                       object={"kind": "value", "value": 20, "unit": "USD"}, contradicts=[original["id"]])
    clock[0] = "2026-11-24T10:03:00+00:00"
    revised_bytes = b"Cafeteria owes 14 USD."
    revised = ledger.capture("synthetic:span-check", revised_bytes, revision_of=observation["id"])
    revision_snapshot = ledger.snapshot()
    revision_span = {"observation_id": revised["id"], "start": 0, "end": len(revised_bytes), "sha256": digest(revised_bytes)}
    updated = _record(ledger, revision_snapshot, revision_span, event_id="assertion-updated", supersedes=original["id"],
                      object={"kind": "value", "value": 14, "unit": "USD"})
    clock[0] = "2026-11-24T10:04:00+00:00"
    return original, opposing, updated, revision_snapshot, revision_span


def _old_view(*fixture):
    ledger, clock = fixture[:2]
    original, opposing, updated, _, _ = _history(*fixture)
    rows = assertions.assertions_as_of(ledger, "2026-11-24T10:01:30+00:00")
    return {row["id"] for row in rows} == {original["id"]} and rows[0]["body"]["object"]["value"] == 12


def _new_view(*fixture):
    ledger, clock = fixture[:2]
    original, opposing, updated, _, _ = _history(*fixture)
    rows = assertions.assertions_as_of(ledger, clock[0])
    return {row["id"] for row in rows} == {opposing["id"], updated["id"]} and ledger.get(original["id"])["body"]["object"]["value"] == 12


def _conflicts(*fixture):
    ledger = fixture[0]
    original, opposing, updated, _, _ = _history(*fixture)
    rows = assertions.assertions_as_of(ledger, "2026-11-24T10:02:30+00:00")
    return ({row["id"] for row in rows} == {original["id"], opposing["id"]}
            and ledger.get(opposing["id"])["body"]["contradicts"] == [original["id"]])


def _no_revision_fork(*fixture):
    ledger = fixture[0]
    original, opposing, updated, snapshot, span = _history(*fixture)
    return _rejected_without_append(ledger, lambda: _record(ledger, snapshot, span, supersedes=original["id"]))


def _observer_lineage(*fixture):
    ledger = fixture[0]
    original, opposing, updated, snapshot, span = _history(*fixture)
    return _rejected_without_append(ledger, lambda: _record(ledger, snapshot, span, observer="other-observer", supersedes=updated["id"]))


def _valid_time(ledger, clock, observation, snapshot, span, content):
    clock[0] = "2026-11-24T10:01:00+00:00"
    record = _record(ledger, snapshot, span, valid_from="2026-11-23T00:00:00+00:00", valid_to="2026-11-24T00:00:00+00:00")
    visible = assertions.assertions_as_of(ledger, clock[0], valid_at="2026-11-23T00:00:00+00:00")
    excluded = assertions.assertions_as_of(ledger, clock[0], valid_at="2026-11-24T00:00:00+00:00")
    return {row["id"] for row in visible} == {record["id"]} and excluded == []


CHECKS = (
    ("exact_multibyte_span", "source_span_resolution", _exact_bytes),
    ("record_typed_value_and_source_span", "source_span_resolution", _typed_record),
    ("reject_negative_offset", "source_span_resolution", _bad_span(lambda _: {"start": -1})),
    ("reject_out_of_bounds", "source_span_resolution", _bad_span(lambda content: {"end": len(content) + 1})),
    ("reject_empty_span", "source_span_resolution", _bad_span(lambda _: {"end": 0})),
    ("reject_wrong_span_digest", "source_span_resolution", _bad_span(lambda _: {"sha256": "0" * 64})),
    ("reject_corruption_outside_span", "source_span_resolution", _corrupted_blob),
    ("reject_late_source_despite_old_publication", "source_span_resolution", _late_evidence),
    ("historical_view_preserves_original", "assertion_history_preservation", _old_view),
    ("current_view_applies_revision_without_erasure", "assertion_history_preservation", _new_view),
    ("conflicting_reports_coexist", "assertion_history_preservation", _conflicts),
    ("reject_revision_fork", "assertion_history_preservation", _no_revision_fork),
    ("reject_observer_lineage_change", "assertion_history_preservation", _observer_lineage),
    ("valid_time_is_separate_and_half_open", "assertion_history_preservation", _valid_time),
)


def run_source_span_checks():
    rows = []
    for check_id, metric, operation in CHECKS:
        row = {"id": check_id, "metric": metric, "passed": False}
        try:
            with _fixture() as fixture:
                row["passed"] = bool(operation(*fixture))
            if not row["passed"]:
                row["diagnostic"] = "Implementation did not satisfy the declared check"
        except Exception as error:
            row["diagnostic"] = f"{type(error).__name__}: {error}"[:400]
        rows.append(row)
    counts = {metric: {"passed": sum(row["passed"] for row in rows if row["metric"] == metric),
                       "checks": sum(row["metric"] == metric for row in rows)}
              for metric in ("source_span_resolution", "assertion_history_preservation")}
    return {"version": "source-span-probes-v1", "checks": rows, "counts": counts,
            "metrics": {metric: count["passed"] / count["checks"] for metric, count in counts.items()},
            "all_passed": all(row["passed"] for row in rows),
            "interpretation": "Actual assertion API exercised on isolated synthetic ledgers; not extraction accuracy, source truth, or predictive/business lift."}
