from copy import deepcopy
import tempfile
import threading
import unittest
from pathlib import Path

from epiphysics.assertions import assertions_as_of, record_assertion, resolve_span
from epiphysics.store import Ledger, canonical, digest


class AssertionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(self.root / "ledger", clock=lambda: self.now)
        self.raw = "A café owes B 125 EUR.\nSecond claim.".encode("utf-8")
        self.observation = self.ledger.capture("synthetic:invoice", self.raw, event_id="observation-one")
        self.snapshot = self.ledger.snapshot(event_id="snapshot-one")
        self.span = self.span_for(self.observation, 0, self.raw.index(b"\n"))

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def span_for(self, observation, start=0, end=None):
        raw = (self.ledger.root / "blobs" / observation["body"]["content_hash"]).read_bytes()
        end = len(raw) if end is None else end
        return {"observation_id": observation["id"], "start": start, "end": end, "sha256": digest(raw[start:end])}

    def record(self, **changes):
        fields = {"subject": "org:aster", "predicate": "owes", "object": {"kind": "entity", "id": "org:cedar"},
                  "observer": "observer:one", "method": "manual-span-v1", "spans": [deepcopy(self.span)], "basis": "reported"}
        fields.update(changes)
        return record_assertion(self.ledger, self.snapshot["id"], **fields)

    def ids(self, **kwargs):
        return [event["id"] for event in assertions_as_of(self.ledger, self.now, **kwargs)]

    def test_multibyte_spans_use_bytes_not_character_offsets(self):
        start = self.raw.index("é".encode())
        span = self.span_for(self.observation, start, start + 2)
        self.assertEqual(resolve_span(self.ledger, self.snapshot["id"], span), "é".encode())
        wrong_character_end = {**span, "end": start + 1}
        with self.assertRaisesRegex(ValueError, "Span hash"):
            resolve_span(self.ledger, self.snapshot["id"], wrong_character_end)
        # Binary addressing may deliberately select part of a UTF-8 sequence.
        byte = self.span_for(self.observation, start, start + 1)
        self.assertEqual(resolve_span(self.ledger, self.snapshot["id"], byte), b"\xc3")

    def test_full_blob_hash_detects_corruption_outside_selected_span(self):
        path = self.ledger.root / "blobs" / self.observation["body"]["content_hash"]
        path.write_bytes(self.raw[:-1] + b"!")
        before = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, "Source blob hash"):
            resolve_span(self.ledger, self.snapshot["id"], self.span)
        with self.assertRaisesRegex(ValueError, "Source blob hash"):
            self.record()
        self.assertEqual(len(self.ledger.events()), before)

    def test_missing_and_symlinked_blobs_are_rejected(self):
        path = self.ledger.root / "blobs" / self.observation["body"]["content_hash"]
        path.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            resolve_span(self.ledger, self.snapshot["id"], self.span)
        external = self.root / "matching-bytes"
        external.write_bytes(self.raw)
        path.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "symlink"):
            resolve_span(self.ledger, self.snapshot["id"], self.span)

    def test_invalid_byte_bounds_types_and_hashes_are_rejected(self):
        changes = [{"start": -1}, {"start": True}, {"end": True}, {"start": 0.0},
                   {"end": 0}, {"end": len(self.raw) + 1}, {"sha256": "0" * 64},
                   {"sha256": "not-a-hash"}, {"unexpected": "field"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolve_span(self.ledger, self.snapshot["id"], {**self.span, **change})

    def test_snapshot_manifest_hash_and_observation_identifiers_are_verified(self):
        for variant in ("manifest_hash", "event_hash", "content_hash", "duplicate", "unknown_id", "watermark"):
            with self.subTest(variant=variant):
                body = deepcopy(self.snapshot["body"])
                if variant == "manifest_hash":
                    body["manifest_hash"] = "0" * 64
                else:
                    if variant in ("event_hash", "content_hash"):
                        body["observations"][0][variant] = "0" * 64
                    elif variant == "duplicate":
                        body["observations"] *= 2
                    elif variant == "unknown_id":
                        body["observations"][0]["id"] = "unknown-observation"
                    else:
                        body["watermark"] = 0
                    body["manifest_hash"] = digest(canonical(body["observations"]).encode())
                snapshot = self.ledger.append("snapshot", body)
                with self.assertRaises(ValueError):
                    resolve_span(self.ledger, snapshot["id"], self.span)

    def test_modified_snapshot_or_observation_event_hash_is_detected(self):
        self.ledger.db.execute("DROP TRIGGER events_no_update")
        self.ledger.db.execute("UPDATE events SET recorded_at=? WHERE id=?", ("2029-12-31T00:00:00Z", self.observation["id"]))
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError, "Event hash mismatch"):
            resolve_span(self.ledger, self.snapshot["id"], self.span)

    def test_future_observation_cannot_be_smuggled_into_forged_snapshot(self):
        self.now = "2030-01-02T00:00:00Z"
        later = self.ledger.capture("synthetic:late", b"late observation")
        manifest = [{"id": later["id"], "event_hash": later["hash"], "content_hash": later["body"]["content_hash"]}]
        snapshot = self.ledger.append("snapshot", {"cutoff": "2030-01-01T00:00:00Z", "observations": manifest,
            "manifest_hash": digest(canonical(manifest).encode()), "watermark": later["seq"]})
        with self.assertRaisesRegex(ValueError, "not eligible"):
            resolve_span(self.ledger, snapshot["id"], self.span_for(later))

    def test_publication_claim_cannot_backdate_evidence_or_assertion_knowledge(self):
        self.now = "2030-01-02T00:00:00Z"
        later = self.ledger.capture("synthetic:late-publication", b"old publication, new knowledge", published_at="2000-01-01T00:00:00Z")
        old_view = self.ledger.snapshot(cutoff="2030-01-01T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "belong"):
            resolve_span(self.ledger, old_view["id"], self.span_for(later))
        self.snapshot = self.ledger.snapshot()
        claim = self.record(spans=[self.span_for(later)], valid_from="2000-01-01T00:00:00Z")
        self.assertEqual(claim["recorded_at"], self.now)
        self.assertEqual(assertions_as_of(self.ledger, "2030-01-01T00:00:00Z", valid_at="2001-01-01T00:00:00Z"), [])
        self.assertEqual(self.ids(valid_at="2001-01-01T00:00:00Z"), [claim["id"]])

    def test_same_time_observation_after_snapshot_is_not_in_snapshot(self):
        later = self.ledger.capture("synthetic:same-clock", b"arrived after the snapshot")
        with self.assertRaisesRegex(ValueError, "belong"):
            resolve_span(self.ledger, self.snapshot["id"], self.span_for(later))

    def test_unit_qualifiers_and_relation_direction_survive(self):
        amount = self.record(predicate="invoice_amount", object={"kind": "value", "value": 125, "unit": "EUR"}, event_id="amount")
        forward = self.record(event_id="forward")
        backward = self.record(subject="org:cedar", object={"kind": "entity", "id": "org:aster"}, event_id="backward")
        self.assertEqual(amount["body"]["object"], {"kind": "value", "value": 125, "unit": "EUR"})
        self.assertNotEqual(forward["body"]["subject"], backward["body"]["subject"])
        self.assertEqual(self.ids(), ["amount", "forward", "backward"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_object_is_typed_and_scalar_values_are_finite(self):
        invalid = [{"kind": "entity", "id": ""}, {"kind": "unknown", "id": "x"},
                   {"kind": "value", "value": 1}, {"kind": "value", "value": 1, "unit": " "},
                   *[{"kind": "value", "value": value, "unit": None} for value in (float("nan"), float("inf"), {}, [])]]
        for obj in invalid:
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                self.record(object=obj)
        for value in (None, True, False, 0, 1.5, ""):
            with self.subTest(value=value):
                assertion = self.record(object={"kind": "value", "value": value, "unit": None})
                self.assertEqual(type(assertion["body"]["object"]["value"]), type(value))

    def test_independent_contradictory_claims_are_retained_without_winner(self):
        first = self.record(object={"kind": "value", "value": 125, "unit": "EUR"}, event_id="first")
        second = self.record(object={"kind": "value", "value": 150, "unit": "EUR"},
            observer="observer:two", contradicts=[first["id"]], event_id="second")
        third = self.record(object={"kind": "value", "value": 160, "unit": "EUR"}, event_id="third")
        self.assertEqual(self.ids(), ["first", "second", "third"])
        self.assertEqual(second["body"]["contradicts"], [first["id"]])
        self.assertEqual(self.ids(observer="observer:two"), [second["id"]])
        self.assertEqual(third["body"]["contradicts"], [])

    def test_late_correction_changes_current_view_but_not_historical_view(self):
        original = self.record(event_id="original", valid_from="2029-01-01T00:00:00Z")
        self.now = "2030-01-03T00:00:00Z"
        self.snapshot = self.ledger.snapshot()
        corrected = self.record(supersedes=original["id"], object={"kind": "value", "value": 100, "unit": "EUR"},
                                event_id="corrected", valid_from="2029-01-01T00:00:00Z")
        old = assertions_as_of(self.ledger, "2030-01-02T00:00:00Z")
        self.assertEqual([event["id"] for event in old], [original["id"]])
        self.assertEqual(self.ids(), [corrected["id"]])
        self.assertEqual(len(self.ledger.events("assertion")), 2)
        self.assertEqual(self.ledger.get(original["id"]), original)

    def test_supersession_precedes_valid_interval_filter_without_resurrection(self):
        original = self.record(event_id="original", valid_from="2029-01-01T00:00:00Z")
        self.now = "2030-01-02T00:00:00Z"
        corrected = self.record(supersedes=original["id"], event_id="corrected",
            valid_from="2030-01-02T00:00:00Z", valid_to="2030-02-01T00:00:00Z")
        self.assertEqual(self.ids(valid_at="2029-06-01T00:00:00Z"), [])
        self.assertEqual(self.ids(valid_at="2030-01-02T00:00:00Z"), [corrected["id"]])
        self.assertEqual(self.ids(valid_at="2030-02-01T00:00:00Z"), [])
        past = assertions_as_of(self.ledger, "2030-01-01T00:00:00Z", valid_at="2029-06-01T00:00:00Z")
        self.assertEqual([event["id"] for event in past], [original["id"]])

    def test_open_valid_intervals_and_future_world_time_are_independent_of_knowledge(self):
        until = self.record(event_id="until", valid_to="2030-02-01T00:00:00Z")
        future = self.record(event_id="future", valid_from="2031-01-01T00:00:00Z")
        self.assertEqual(self.ids(valid_at="2029-01-01T00:00:00Z"), [until["id"]])
        self.assertEqual(self.ids(valid_at="2031-01-01T00:00:00Z"), [future["id"]])
        self.assertEqual(self.ids(), [until["id"], future["id"]])

    def test_invalid_intervals_and_future_knowledge_queries_are_refused(self):
        for start, end in [(self.now, self.now), ("2030-01-02T00:00:00Z", self.now),
                           ("2030-01-01", None), (None, "invalid")]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                self.record(valid_from=start, valid_to=end)
        with self.assertRaisesRegex(ValueError, "future knowledge"):
            assertions_as_of(self.ledger, "2030-01-02T00:00:00Z")
        with self.assertRaises(ValueError):
            assertions_as_of(self.ledger, "2030-01-01")
        with self.assertRaises(ValueError):
            assertions_as_of(self.ledger, self.now, valid_at="invalid")

    def test_supersession_preserves_observer_and_latest_revision(self):
        original = self.record(event_id="original")
        with self.assertRaisesRegex(ValueError, "observer"):
            self.record(supersedes=original["id"], observer="observer:other")
        corrected = self.record(supersedes=original["id"], event_id="corrected")
        with self.assertRaisesRegex(ValueError, "latest assertion"):
            self.record(supersedes=original["id"])
        latest = self.record(supersedes=corrected["id"], event_id="latest")
        self.assertEqual(self.ids(), [latest["id"]])

    def test_supersession_cannot_regress_snapshot_cutoff(self):
        old_snapshot = self.snapshot
        self.now = "2030-01-02T00:00:00Z"
        self.snapshot = self.ledger.snapshot()
        original = self.record()
        self.snapshot = old_snapshot
        with self.assertRaisesRegex(ValueError, "earlier snapshot cutoff"):
            self.record(supersedes=original["id"])

    def test_identical_retries_replay_even_after_later_revisions(self):
        original = self.record(event_id="original")
        corrected = self.record(event_id="corrected", supersedes=original["id"])
        latest = self.record(event_id="latest", supersedes=corrected["id"])
        before = len(self.ledger.events())
        self.assertEqual(self.record(event_id="original"), original)
        self.assertEqual(self.record(event_id="corrected", supersedes=original["id"]), corrected)
        self.assertEqual(len(self.ledger.events()), before)
        self.assertEqual(self.ids(), [latest["id"]])
        with self.assertRaisesRegex(ValueError, "different content"):
            self.record(event_id="original", method="changed-method")

    def test_unknown_and_wrong_kind_links_cannot_be_appended(self):
        for target in ("missing", self.observation["id"], self.snapshot["id"]):
            for field in ("supersedes", "contradicts"):
                with self.subTest(target=target, field=field), self.assertRaises(ValueError):
                    self.record(**{field: target if field == "supersedes" else [target]})
        self.assertEqual(self.ledger.events("assertion"), [])

    def test_required_fields_and_span_limits_are_enforced(self):
        for changes in ({"subject": ""}, {"predicate": " "}, {"observer": ""}, {"method": ""},
                        {"basis": "certain"}, {"spans": []}, {"spans": [self.span] * 101},
                        {"spans": [self.span] * 2}, {"contradicts": "one"}, {"contradicts": ["one", "one"]},
                        {"event_id": ""}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.record(**changes)

    def test_caller_mutations_do_not_change_recorded_body(self):
        spans = [deepcopy(self.span)]
        obj = {"kind": "value", "value": 125, "unit": "EUR"}
        claim = self.record(object=obj, spans=spans)
        obj["unit"] = "USD"
        spans[0]["end"] = 1
        self.assertEqual(self.ledger.get(claim["id"])["body"]["object"]["unit"], "EUR")
        self.assertEqual(self.ledger.get(claim["id"])["body"]["spans"], [self.span])

    def test_concurrent_corrections_cannot_fork_the_same_revision(self):
        original = self.record(event_id="original")
        barrier = threading.Barrier(2)
        outcomes = []

        def revise(index):
            ledger = Ledger(self.ledger.root, clock=lambda: self.now)
            try:
                barrier.wait(timeout=5)
                claim = record_assertion(ledger, self.snapshot["id"], subject="org:aster", predicate="owes",
                    object={"kind": "value", "value": index, "unit": "EUR"}, observer="observer:one",
                    method="manual-span-v1", spans=[self.span], basis="reported", supersedes=original["id"],
                    event_id=f"correction-{index}")
                outcomes.append(claim["id"])
            except ValueError as error:
                outcomes.append(str(error))
            finally:
                ledger.close()

        threads = [threading.Thread(target=revise, args=(index,)) for index in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(sum(value.startswith("correction-") for value in outcomes), 1)
        self.assertEqual(sum("latest assertion" in value for value in outcomes), 1)
        self.assertEqual(len(self.ledger.events("assertion")), 2)
        self.assertEqual(len(self.ids()), 1)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_append_validator_uses_the_locked_recorded_time_once(self):
        times = []

        def clock():
            times.append(self.now)
            return self.now

        self.ledger.clock = clock
        claim = self.record()
        self.assertEqual(times, [self.now])
        self.assertEqual(claim["recorded_at"], self.now)


if __name__ == "__main__":
    unittest.main()
