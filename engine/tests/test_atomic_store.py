from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from epiphysics.assertions import record_assertion, resolve_span
from epiphysics.manifests import forecast_manifest, register_manifest
from epiphysics.store import Ledger, digest, instant


class Interrupted(BaseException):
    pass


class AtomicStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(self.root, clock=lambda: self.now)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def assert_reusable(self):
        self.assertFalse(self.ledger.db.in_transaction)
        self.ledger.append("after", {"usable": True})
        self.assertTrue(self.ledger.verify()["valid"])

    def test_group_is_visible_to_its_writer_and_invisible_to_other_connection_until_commit(self):
        seed = self.ledger.append("seed", {}, "seed")
        other = Ledger(self.root, clock=lambda: self.now)
        try:
            self.now = "2030-01-01T00:01:00Z"
            seen = []
            with self.ledger.atomic_write() as recorded_at:
                first = self.ledger.append("first", {"x": 1}, "first")
                self.assertEqual(first, self.ledger.get("first"))
                self.assertEqual([seed], other.events())
                second = self.ledger.append("second", {"first": first["id"]}, "second",
                    validate=lambda now: seen.append((now, self.ledger.get("first")["hash"])))
                self.assertEqual(first["hash"], second["previous_hash"])
                self.assertEqual(recorded_at, first["recorded_at"])
                self.assertEqual(recorded_at, second["recorded_at"])
                self.assertEqual([(recorded_at, first["hash"])], seen)
                self.assertEqual([seed], other.events())
            self.assertEqual([seed, first, second], other.events())
            self.assertTrue(other.verify()["valid"])
        finally:
            other.close()

    def test_exception_after_staged_records_rolls_back_the_entire_group(self):
        with self.assertRaisesRegex(RuntimeError, "bundle interrupted"):
            with self.ledger.atomic_write():
                self.ledger.append("first", {}, "first")
                self.ledger.append("second", {}, "second")
                raise RuntimeError("bundle interrupted")
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_baseexception_rolls_back_group_and_resets_ownership(self):
        with self.assertRaises(Interrupted):
            with self.ledger.atomic_write():
                self.ledger.append("first", {}, "first")
                raise Interrupted()
        self.assertEqual([], self.ledger.events())
        with self.ledger.atomic_write():
            self.ledger.append("later", {}, "later")
        self.assertTrue(self.ledger.verify()["valid"])
        self.assertFalse(self.ledger.db.in_transaction)

    def test_caught_serialization_or_validator_errors_poison_the_group(self):
        def reject(_):
            raise ValueError("validation refused")

        cases = [({"x": float("nan")}, None), ({"x": {1}}, None), ({}, reject)]
        for body, validator in cases:
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, "complete group"):
                with self.ledger.atomic_write():
                    self.ledger.append("provisional", {}, "first")
                    try:
                        self.ledger.append("invalid", body, "second", validate=validator)
                    except (ValueError, TypeError):
                        pass
            self.assertEqual([], self.ledger.events())
            self.assertFalse(self.ledger.db.in_transaction)
        self.assert_reusable()

    def test_poisoned_group_refuses_further_appends_even_if_original_error_was_caught(self):
        with self.assertRaisesRegex(ValueError, "complete group"):
            with self.ledger.atomic_write():
                self.ledger.append("first", {}, "same")
                with self.assertRaisesRegex(ValueError, "different content"):
                    self.ledger.append("different", {}, "same")
                with self.assertRaisesRegex(ValueError, "no longer available"):
                    self.ledger.append("later", {}, "later")
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_standalone_validator_reentrancy_refuses_nested_write_and_rolls_back(self):
        def reenter(_):
            self.ledger.append("nested", {}, "nested")

        with self.assertRaisesRegex(ValueError, "Reentrant append"):
            self.ledger.append("outer", {}, "outer", validate=reenter)
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_caught_validator_reentrancy_poisoning_cannot_commit_partial_group(self):
        def reenter(_):
            with self.assertRaisesRegex(ValueError, "Reentrant append"):
                self.ledger.append("nested", {}, "nested")

        with self.assertRaisesRegex(ValueError, "failed during append validation"):
            with self.ledger.atomic_write():
                self.ledger.append("first", {}, "first")
                self.ledger.append("outer", {}, "outer", validate=reenter)
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_standalone_validator_baseexception_also_releases_write_transaction(self):
        def interrupt(_):
            raise Interrupted()

        with self.assertRaises(Interrupted):
            self.ledger.append("outer", {}, "outer", validate=interrupt)
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_standalone_validator_body_mutation_refuses_without_corrupting_chain(self):
        seed = self.ledger.append("seed", {}, "seed")
        body = {"value": 1, "nested": {"items": ["original"]}}

        def mutate(_):
            body["value"] = 2
            body["nested"]["items"].append("changed")

        with self.assertRaisesRegex(ValueError, "body changed during append validation"):
            self.ledger.append("mutated", body, "mutated", validate=mutate)
        self.assertEqual([seed], self.ledger.events())
        self.assert_reusable()

    def test_validator_body_mutation_rolls_back_the_entire_atomic_group(self):
        body = {"value": 1}

        def mutate(_):
            body["value"] = 2

        with self.assertRaisesRegex(ValueError, "body changed during append validation"):
            with self.ledger.atomic_write():
                self.ledger.append("first", {}, "first")
                self.ledger.append("mutated", body, "mutated", validate=mutate)
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_caught_validator_body_mutation_still_poisons_the_atomic_group(self):
        body = {"nested": [1]}

        def mutate(_):
            body["nested"].append(2)

        with self.assertRaisesRegex(ValueError, "complete group"):
            with self.ledger.atomic_write():
                self.ledger.append("first", {}, "first")
                with self.assertRaisesRegex(ValueError, "body changed during append validation"):
                    self.ledger.append("mutated", body, "mutated", validate=mutate)
                with self.assertRaisesRegex(ValueError, "no longer available"):
                    self.ledger.append("later", {}, "later")
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_successful_append_is_independent_of_later_caller_body_mutation(self):
        body = {"nested": [1]}
        event = self.ledger.append("original", body, "original")
        body["nested"].append(2)
        self.assertEqual({"nested": [1]}, event["body"])
        self.assertEqual(event, self.ledger.get("original"))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_nested_atomic_context_refuses_and_poisoning_survives_caught_error(self):
        with self.assertRaisesRegex(ValueError, "complete group"):
            with self.ledger.atomic_write():
                self.ledger.append("first", {}, "first")
                with self.assertRaisesRegex(ValueError, "Nested atomic"):
                    with self.ledger.atomic_write():
                        self.fail("Nested context entered")
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_validator_cannot_open_an_atomic_context(self):
        def reenter(_):
            with self.ledger.atomic_write():
                self.fail("Validator acquired a nested transaction")

        with self.assertRaisesRegex(ValueError, "during append validation"):
            self.ledger.append("outer", {}, "outer", validate=reenter)
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_external_sqlite_transaction_is_not_adopted_committed_or_rolled_back(self):
        self.ledger.db.execute("CREATE TABLE caller_state(value TEXT)")
        other = sqlite3.connect(self.root / "ledger.sqlite")
        try:
            self.ledger.db.execute("BEGIN IMMEDIATE")
            self.ledger.db.execute("INSERT INTO caller_state VALUES('provisional')")
            with self.assertRaisesRegex(ValueError, "owned by this context"):
                with self.ledger.atomic_write():
                    self.fail("Foreign transaction was adopted")
            with self.assertRaisesRegex(ValueError, "without atomic_write"):
                self.ledger.append("unexpected", {}, "unexpected")
            self.assertTrue(self.ledger.db.in_transaction)
            self.assertEqual(1, self.ledger.db.execute("SELECT COUNT(*) FROM caller_state").fetchone()[0])
            self.assertEqual(0, other.execute("SELECT COUNT(*) FROM caller_state").fetchone()[0])
            self.ledger.db.rollback()
        finally:
            other.close()
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_group_uses_one_clock_read_and_shared_validator_timestamp(self):
        calls, validated = [], []

        def clock():
            calls.append(self.now)
            return self.now

        self.ledger.clock = clock
        with self.ledger.atomic_write() as recorded_at:
            first = self.ledger.append("first", {}, "first", validate=validated.append)
            self.now = "2030-01-01T00:01:00Z"
            second = self.ledger.append("second", {}, "second", validate=validated.append)
        self.assertEqual([recorded_at], calls)
        self.assertEqual([recorded_at, recorded_at], validated)
        self.assertEqual(recorded_at, first["recorded_at"])
        self.assertEqual(recorded_at, second["recorded_at"])
        third = self.ledger.append("third", {}, "third")
        self.assertEqual(self.now, third["recorded_at"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_invalid_or_backwards_group_clock_refuses_before_entry_and_releases_lock(self):
        seed = self.ledger.append("seed", {}, "seed")
        for value, diagnostic in [("2029-12-31T00:00:00Z", "Clock moved backwards"),
                                  ("2030-01-01T00:00:00", "timezone"), ("not-a-date", "Invalid isoformat")]:
            self.now = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, diagnostic):
                with self.ledger.atomic_write():
                    self.fail("Invalid clock entered the group")
            self.assertFalse(self.ledger.db.in_transaction)
            self.assertEqual([seed], self.ledger.events())
        self.now = "2030-01-01T00:01:00Z"
        self.assert_reusable()

    def test_idempotent_replay_skips_validation_without_committing_other_staged_events(self):
        existing = self.ledger.append("existing", {"value": 1}, "existing")
        other = Ledger(self.root, clock=lambda: self.now)

        def reject(_):
            self.fail("Replay ran its validator")

        try:
            self.now = "2030-01-01T00:01:00Z"
            with self.ledger.atomic_write():
                staged = self.ledger.append("new", {}, "new")
                self.assertEqual(existing, self.ledger.append("existing", {"value": 1}, "existing", validate=reject))
                self.assertEqual(staged, self.ledger.append("new", {}, "new", validate=reject))
                self.assertEqual([existing], other.events())
            self.assertEqual([existing, staged], other.events())
        finally:
            other.close()

    def test_exclusive_existing_id_refusal_rolls_back_only_new_group_events(self):
        existing = self.ledger.append("existing", {}, "existing")
        with self.assertRaisesRegex(ValueError, "exclusive claim"):
            with self.ledger.atomic_write():
                self.ledger.append("new", {}, "new")
                self.ledger.append("existing", {}, "existing", exclusive=True)
        self.assertEqual([existing], self.ledger.events())
        self.assert_reusable()

    def test_existing_representation_and_assertion_callers_can_consume_staged_events(self):
        observation = self.ledger.capture("test:source", b"A exists.", event_id="source")
        other = Ledger(self.root, clock=lambda: self.now)
        try:
            with self.ledger.atomic_write():
                snapshot = self.ledger.snapshot(event_id="snapshot")
                model = {"entities": [{"id": "a", "basis": "reported", "evidence_ids": [observation["id"]]}],
                         "relations": []}
                self.ledger.representation(snapshot["id"], model, observer="test", method="manual", event_id="representation")
                record_assertion(self.ledger, snapshot["id"], subject="a", predicate="exists",
                    object={"kind": "value", "value": True, "unit": None}, observer="test", method="manual",
                    spans=[{"observation_id": observation["id"], "start": 0, "end": 9, "sha256": digest(b"A exists.")}],
                    basis="reported", event_id="assertion")
                self.assertEqual([observation], other.events())
            self.assertEqual(["source", "snapshot", "representation", "assertion"], [e["id"] for e in other.events()])
            self.assertTrue(other.verify()["valid"])
        finally:
            other.close()

    def exercise_grouped_snapshot_consumers(self, ledger):
        observation = ledger.capture("test:source", b"A exists.", event_id="source")
        artifacts = {role: ledger.capture(f"test:{role}", f"declared {role}".encode())["id"]
                     for role in ("construction", "config", "ontology", "predictor")}
        span = {"observation_id": observation["id"], "start": 0, "end": 9, "sha256": digest(b"A exists.")}
        with ledger.atomic_write() as recorded_at:
            snapshot = ledger.snapshot(event_id="snapshot")
            self.assertEqual(recorded_at, snapshot["body"]["cutoff"])
            self.assertEqual(recorded_at, snapshot["recorded_at"])
            self.assertEqual(b"A exists.", resolve_span(ledger, snapshot["id"], span))
            assertion = record_assertion(ledger, snapshot["id"], subject="a", predicate="exists",
                object={"kind": "value", "value": True, "unit": None}, observer="test", method="manual",
                spans=[span], basis="reported", event_id="assertion")
            representation = ledger.representation(snapshot["id"],
                {"entities": [{"id": "a", "basis": "reported", "evidence_ids": [observation["id"]]}], "relations": []},
                observer="test", method="manual", event_id="representation")
            manifest = register_manifest(ledger, representation["id"], encoding="directed-graph",
                schema_id="epiphysics.graph.v1", artifacts=artifacts,
                task={"id": "snapshot-consumer", "family": "snapshot-test", "outcome_type": "binary"},
                horizon_seconds=600, units={}, evidence_ids=[observation["id"]], construction_cost=None,
                event_id="manifest")
            self.assertEqual(recorded_at, assertion["recorded_at"])
            self.assertEqual(recorded_at, manifest["recorded_at"])
        self.assertEqual(b"A exists.", resolve_span(ledger, snapshot["id"], span))
        cutoff = instant(snapshot["body"]["cutoff"])
        question = ledger.question("Will A persist?", (cutoff + timedelta(seconds=300)).isoformat(),
            (cutoff + timedelta(seconds=600)).isoformat(), "Synthetic completion evidence", "snapshot-test")
        forecast = forecast_manifest(ledger, manifest["id"], question["id"], 0.5, event_id="forecast")
        self.assertEqual(snapshot["id"], forecast["body"]["snapshot_id"])
        self.assertTrue(ledger.verify()["valid"])

    def test_grouped_snapshot_with_advancing_clock_is_usable_by_span_assertion_and_manifest_consumers(self):
        tick = instant("2030-01-01T00:00:00Z")

        def advancing_clock():
            nonlocal tick
            tick += timedelta(microseconds=17)
            return tick.isoformat()

        self.ledger.clock = advancing_clock
        self.exercise_grouped_snapshot_consumers(self.ledger)

    def test_grouped_snapshot_with_default_real_clock_is_usable_by_all_consumers(self):
        ledger = Ledger(self.root / "real-clock")
        try:
            self.exercise_grouped_snapshot_consumers(ledger)
        finally:
            ledger.close()

    def test_explicit_snapshot_cutoff_after_group_time_refuses_even_after_live_clock_advances(self):
        tick = instant("2030-01-01T00:00:00Z")

        def advancing_clock():
            nonlocal tick
            tick += timedelta(seconds=1)
            return tick.isoformat()

        self.ledger.clock = advancing_clock
        with self.assertRaisesRegex(ValueError, "future information state"):
            with self.ledger.atomic_write() as recorded_at:
                self.ledger.append("first", {}, "first")
                future_cutoff = (instant(recorded_at) + timedelta(microseconds=1)).isoformat()
                self.assertGreater(instant(self.ledger.clock()), instant(future_cutoff))
                self.ledger.snapshot(cutoff=future_cutoff)
        self.assertEqual([], self.ledger.events())
        self.assert_reusable()

    def test_standalone_snapshot_keeps_live_clock_cutoff_and_recording_semantics(self):
        tick = instant("2030-01-01T00:00:00Z")

        def advancing_clock():
            nonlocal tick
            tick += timedelta(seconds=1)
            return tick.isoformat()

        self.ledger.clock = advancing_clock
        observation = self.ledger.capture("test:source", b"A exists.", event_id="source")
        snapshot = self.ledger.snapshot()
        self.assertLess(instant(snapshot["body"]["cutoff"]), instant(snapshot["recorded_at"]))
        span = {"observation_id": observation["id"], "start": 0, "end": 9, "sha256": digest(b"A exists.")}
        self.assertEqual(b"A exists.", resolve_span(self.ledger, snapshot["id"], span))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_group_cannot_backdate_forecast_when_live_time_passes_its_deadline(self):
        snapshot = self.ledger.snapshot()
        question = self.ledger.question("Will A persist?", "2030-01-01T00:01:00Z",
            "2030-01-01T00:02:00Z", "Synthetic completion", "test")
        before = self.ledger.events()
        self.now = "2030-01-01T00:00:59Z"
        with self.assertRaisesRegex(ValueError, "forecast writes are not allowed"):
            with self.ledger.atomic_write():
                self.ledger.append("derived", {}, "derived")
                self.now = "2030-01-01T00:01:01Z"
                self.ledger.forecast(question["id"], snapshot["id"], "late", 0.5,
                    model={"identifier": "test"})
        self.assertEqual(before, self.ledger.events())
        with self.assertRaisesRegex(ValueError, "deadline has passed"):
            self.ledger.forecast(question["id"], snapshot["id"], "late", 0.5,
                model={"identifier": "test"})
        self.assertEqual(before, self.ledger.events())
        self.assert_reusable()

    def test_group_cannot_backdate_new_evidence_or_write_its_blob(self):
        self.ledger.capture("test:prior", b"prior evidence", event_id="prior")
        before, blobs = self.ledger.events(), set((self.root / "blobs").iterdir())
        self.now = "2030-01-01T00:00:59Z"
        with self.assertRaisesRegex(ValueError, "observation writes are not allowed"):
            with self.ledger.atomic_write():
                self.ledger.snapshot(event_id="group-snapshot")
                self.ledger.append("derived", {}, "derived")
                self.now = "2030-01-01T00:02:59Z"
                self.ledger.capture("test:late", b"new late evidence", event_id="late")
        self.assertEqual(before, self.ledger.events())
        self.assertEqual(blobs, set((self.root / "blobs").iterdir()))
        self.assertFalse((self.root / "blobs" / digest(b"new late evidence")).exists())
        captured = self.ledger.capture("test:late", b"new late evidence", event_id="late")
        self.assertEqual(self.now, captured["recorded_at"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_caught_live_write_refusals_poison_every_convenience_api_group(self):
        observation = self.ledger.capture("test:prior", b"prior evidence", event_id="prior")
        snapshot = self.ledger.snapshot()
        question = self.ledger.question("Will A persist?", "2030-01-01T00:10:00Z",
            "2030-01-01T00:20:00Z", "Synthetic completion", "test")
        before, blobs = self.ledger.events(), set((self.root / "blobs").iterdir())
        operations = [
            ("observation", lambda: self.ledger.capture("test:late", b"late evidence", event_id="late")),
            ("question", lambda: self.ledger.question("New question", "2030-01-01T00:10:00Z",
                "2030-01-01T00:20:00Z", "New rule", "test", event_id="new-question")),
            ("forecast", lambda: self.ledger.forecast(question["id"], snapshot["id"], "grouped", 0.5,
                model={"identifier": "test"}, event_id="new-forecast")),
        ]
        for index, (kind, operation) in enumerate(operations):
            self.now = (instant("2030-01-01T00:01:00Z") + timedelta(minutes=index)).isoformat()
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "complete group"):
                with self.ledger.atomic_write():
                    self.ledger.append("derived", {}, "derived")
                    self.now = (instant(self.now) + timedelta(seconds=10)).isoformat()
                    with self.assertRaisesRegex(ValueError, f"{kind} writes are not allowed"):
                        operation()
                    with self.assertRaisesRegex(ValueError, "no longer available"):
                        self.ledger.append("later", {}, "later")
            self.assertEqual(before, self.ledger.events())
            self.assertEqual(blobs, set((self.root / "blobs").iterdir()))
            self.assertTrue(self.ledger.verify()["valid"])
        self.assertEqual(observation, self.ledger.get("prior"))

    def test_generic_append_cannot_bypass_live_kind_refusal_or_poisoning(self):
        for index, kind in enumerate(("observation", "question", "forecast")):
            self.now = (instant("2030-01-01T00:01:00Z") + timedelta(minutes=index)).isoformat()
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "complete group"):
                with self.ledger.atomic_write():
                    self.ledger.append("derived", {}, "derived")
                    self.now = (instant(self.now) + timedelta(seconds=10)).isoformat()
                    with self.assertRaisesRegex(ValueError, f"{kind} writes are not allowed"):
                        self.ledger.append(kind, {}, "bypass")
            self.assertEqual([], self.ledger.events())
            self.assertEqual([], list((self.root / "blobs").iterdir()))
            self.assertTrue(self.ledger.verify()["valid"])

    def test_live_kind_retries_outside_groups_still_return_original_events(self):
        observation = self.ledger.capture("test:source", b"original", event_id="observation")
        snapshot = self.ledger.snapshot()
        arguments = ("Will A persist?", "2030-01-01T00:01:00Z", "2030-01-01T00:02:00Z", "Synthetic completion", "test")
        question = self.ledger.question(*arguments, event_id="question")
        forecast = self.ledger.forecast(question["id"], snapshot["id"], "method", 0.5,
            model={"identifier": "test"}, event_id="forecast")
        before = self.ledger.events()
        self.now = "2030-01-01T00:03:00Z"
        self.assertEqual(observation, self.ledger.capture("test:source", b"original", event_id="observation"))
        self.assertEqual(question, self.ledger.question(*arguments, event_id="question"))
        self.assertEqual(forecast, self.ledger.forecast(question["id"], snapshot["id"], "method", 0.5,
            model={"identifier": "test"}, event_id="forecast"))
        self.assertEqual(before, self.ledger.events())
        self.assertTrue(self.ledger.verify()["valid"])

    def test_concurrent_groups_have_one_exclusive_owner_and_no_partial_loser_records(self):
        barrier = threading.Barrier(2)

        def worker(index):
            ledger = Ledger(self.root, clock=lambda: self.now)
            try:
                barrier.wait(timeout=5)
                with ledger.atomic_write():
                    ledger.append("claim", {}, "shared", exclusive=True)
                    ledger.append("output", {"owner": index}, f"output-{index}")
                return "completed"
            except ValueError:
                return "refused"
            finally:
                ledger.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertCountEqual(["completed", "refused"], results)
        self.assertEqual(2, len(self.ledger.events()))
        self.assertEqual(1, len(self.ledger.events("output")))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_group_waiting_for_lock_takes_its_timestamp_after_acquiring_it(self):
        ready, start, attempting_write = threading.Event(), threading.Event(), threading.Event()

        def worker():
            ledger = Ledger(self.root, clock=lambda: self.now)
            ledger.db.set_trace_callback(lambda sql: attempting_write.set() if sql == "BEGIN IMMEDIATE" else None)
            ready.set()
            try:
                if not start.wait(timeout=5):
                    raise TimeoutError("Writer was not started")
                with ledger.atomic_write() as now:
                    record = ledger.append("after-lock", {}, "after-lock")
                    self.assertEqual(now, record["recorded_at"])
                return record
            finally:
                ledger.close()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker)
            self.assertTrue(ready.wait(timeout=5))
            self.ledger.db.execute("BEGIN IMMEDIATE")
            try:
                start.set()
                self.assertTrue(attempting_write.wait(timeout=5))
                self.now = "2030-01-01T00:01:00Z"
            finally:
                self.ledger.db.rollback()
            record = future.result(timeout=5)
        self.assertEqual(self.now, record["recorded_at"])
        self.assertTrue(self.ledger.verify()["valid"])


if __name__ == "__main__":
    unittest.main()
