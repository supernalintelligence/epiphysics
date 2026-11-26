import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from epiphysics.store import Ledger
from epiphysics.cycle import run_cycle
from epiphysics.cli import demo
from epiphysics.public_status import project_status


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = "2026-11-24T10:00:00+00:00"
        self.ledger = Ledger(self.temp.name, clock=lambda: self.now)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def question(self):
        return self.ledger.question("Will the task finish?", "2026-11-24T10:05:00Z",
            "2026-11-24T10:10:00Z", "Completion log says done", "task")

    def setup_forecast(self, probability=0.7, method="candidate"):
        obs = self.ledger.capture("test", b"pending")
        snapshot = self.ledger.snapshot()
        question = self.question()
        forecast = self.ledger.forecast(question["id"], snapshot["id"], method, probability, model={"identifier": "test"})
        return obs, snapshot, question, forecast

    def concurrent_writes(self, kind, operation):
        """Make both callers reach the write boundary before either can append."""
        barrier = threading.Barrier(2)

        def worker(index):
            ledger = Ledger(self.temp.name, clock=lambda: self.now)
            append = ledger.append

            def synchronized_append(event_kind, *args, **kwargs):
                if event_kind == kind:
                    barrier.wait(timeout=5)
                return append(event_kind, *args, **kwargs)

            ledger.append = synchronized_append
            try:
                return operation(ledger, index)
            except ValueError as error:
                return error
            finally:
                ledger.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertEqual(1, sum(isinstance(result, dict) for result in results))
        self.assertEqual(1, sum(isinstance(result, ValueError) for result in results))
        return results

    def test_publication_date_cannot_backdate_observation(self):
        old = self.ledger.capture("test", b"old")
        self.now = "2026-11-24T11:00:00Z"
        self.ledger.capture("test", b"new", published_at="2020-01-01T00:00:00Z", revision_of=old["id"])
        snapshot = self.ledger.snapshot("2026-11-24T10:30:00Z")
        self.assertEqual([old["id"]], [r["id"] for r in snapshot["body"]["observations"]])

    def test_events_cannot_be_edited_or_deleted(self):
        self.ledger.capture("test", b"a")
        for sql in ["UPDATE events SET kind='fake'", "DELETE FROM events"]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.ledger.db.execute(sql)
            self.ledger.db.rollback()

    def test_blob_tampering_is_detected(self):
        obs = self.ledger.capture("test", b"a")
        (Path(self.temp.name) / "blobs" / obs["body"]["content_hash"]).write_bytes(b"b")
        self.assertFalse(self.ledger.verify()["valid"])
        with self.assertRaises(ValueError):
            self.ledger.capture("test", b"a")

    def test_idempotent_writes_reject_content_change(self):
        a = self.ledger.capture("test", b"a", event_id="same")
        self.assertEqual(a, self.ledger.capture("test", b"a", event_id="same"))
        with self.assertRaises(ValueError):
            self.ledger.capture("test", b"b", event_id="same")

    def test_direction_and_multiple_relationship_types_survive(self):
        obs = self.ledger.capture("test", b"A supplies B; B pays A")
        snap = self.ledger.snapshot()
        entities = [{"id": i, "basis": "reported", "evidence_ids": [obs["id"]]} for i in ["a", "b"]]
        relations = [{"source": a, "target": b, "type": t, "basis": "reported", "evidence_ids": [obs["id"]]}
                     for a,b,t in [("a","b","supplies"),("b","a","pays"),("a","b","depends")]]
        rep = self.ledger.representation(snap["id"], {"entities": entities, "relations": relations}, observer="test", method="manual")
        self.assertEqual(3, len(rep["body"]["model"]["relations"]))

    def test_future_evidence_and_memory_are_rejected(self):
        early = self.ledger.snapshot()
        self.now = "2026-11-24T11:00:00Z"
        obs = self.ledger.capture("test", b"future")
        model = {"entities": [{"id": "a", "basis": "inferred", "evidence_ids": [obs["id"]]}]}
        with self.assertRaises(ValueError):
            self.ledger.representation(early["id"], model, observer="test", method="manual")
        late = self.ledger.snapshot()
        rep = self.ledger.representation(late["id"], model, observer="test", method="manual")
        with self.assertRaises(ValueError):
            self.ledger.representation(early["id"], {"entities": []}, observer="test", method="manual", parent=rep["id"])

    def test_invalid_probabilities_fail(self):
        snap = self.ledger.snapshot()
        q = self.question()
        for p in [float("nan"), float("inf"), -0.1, 1.1, True, "0.7", None]:
            with self.assertRaises(ValueError):
                self.ledger.forecast(q["id"], snap["id"], "test", p, model={"identifier": "test"})

    def test_deadlines_and_resolution_time(self):
        obs,snap,q,_ = self.setup_forecast()
        with self.assertRaises(ValueError):
            self.ledger.resolve(q["id"], 1, [obs["id"]], explanation="too early")
        self.now = "2026-11-24T10:05:00Z"
        with self.assertRaises(ValueError):
            self.ledger.forecast(q["id"], snap["id"], "late", .5, model={"identifier": "test"})

    def test_concurrent_forecasts_cannot_duplicate_method_question(self):
        snap = self.ledger.snapshot()
        question = self.question()
        results = self.concurrent_writes("forecast", lambda ledger, index: ledger.forecast(
            question["id"], snap["id"], "same-method", (index + 1) / 10, model={"identifier": "test"}))
        self.assertIn("already attempted", str(next(r for r in results if isinstance(r, ValueError))))
        self.assertEqual(1, len(self.ledger.events("forecast")))
        self.assertEqual(1, self.ledger.scores()["methods"]["same-method"]["attempts"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_concurrent_resolutions_and_corrections_cannot_fork(self):
        observation, _, question, _ = self.setup_forecast()
        self.now = "2026-11-24T10:11:00Z"
        self.concurrent_writes("resolution", lambda ledger, index: ledger.resolve(
            question["id"], index, [observation["id"]], explanation="initial"))
        first = self.ledger.events("resolution")
        self.assertEqual(1, len(first))
        self.concurrent_writes("resolution", lambda ledger, index: ledger.resolve(
            question["id"], index, [observation["id"]], explanation="correction", supersedes=first[0]["id"]))
        resolutions = self.ledger.events("resolution")
        self.assertEqual(2, len(resolutions))
        self.assertEqual(first[0]["id"], resolutions[1]["body"]["supersedes"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_forecast_waiting_for_write_lock_uses_time_after_lock(self):
        snap = self.ledger.snapshot()
        question = self.question()
        ready, start, attempting_write = threading.Event(), threading.Event(), threading.Event()

        def worker():
            ledger = Ledger(self.temp.name, clock=lambda: self.now)
            ledger.db.set_trace_callback(lambda statement: attempting_write.set() if statement == "BEGIN IMMEDIATE" else None)
            ready.set()
            try:
                if not start.wait(timeout=5):
                    raise TimeoutError("Writer was not started")
                try:
                    return ledger.forecast(question["id"], snap["id"], "delayed", .5, model={"identifier": "test"})
                except ValueError as error:
                    return error
            finally:
                ledger.close()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker)
            self.assertTrue(ready.wait(timeout=5))
            self.ledger.db.execute("BEGIN IMMEDIATE")
            try:
                start.set()
                self.assertTrue(attempting_write.wait(timeout=5))
                self.now = "2026-11-24T10:05:00Z"
            finally:
                self.ledger.db.rollback()
            result = future.result(timeout=5)
        self.assertIsInstance(result, ValueError)
        self.assertIn("deadline has passed", str(result))
        self.assertEqual([], self.ledger.events("forecast"))

    def test_identical_question_forecast_and_resolution_retries_are_safe(self):
        observation = self.ledger.capture("test", b"pending")
        snap = self.ledger.snapshot()
        question_args = ("Will this finish?", "2026-11-24T10:05:00Z", "2026-11-24T10:10:00Z", "Completion record", "test")
        question = self.ledger.question(*question_args, event_id="question-retry")
        forecast_args = (question["id"], snap["id"], "test", .7)
        forecast = self.ledger.forecast(*forecast_args, model={"identifier": "test"}, event_id="forecast-retry")
        self.now = "2026-11-24T10:11:00Z"
        first = self.ledger.resolve(question["id"], 1, [observation["id"]], explanation="first", event_id="resolution-retry")
        correction = self.ledger.resolve(question["id"], 0, [observation["id"]], explanation="correction",
            supersedes=first["id"], event_id="correction-retry")
        count = len(self.ledger.events())
        self.assertEqual(question, self.ledger.question(*question_args, event_id="question-retry"))
        self.assertEqual(forecast, self.ledger.forecast(*forecast_args, model={"identifier": "test"}, event_id="forecast-retry"))
        self.assertEqual(first, self.ledger.resolve(question["id"], 1, [observation["id"]], explanation="first", event_id="resolution-retry"))
        self.assertEqual(correction, self.ledger.resolve(question["id"], 0, [observation["id"]], explanation="correction",
            supersedes=first["id"], event_id="correction-retry"))
        self.assertEqual(count, len(self.ledger.events()))
        with self.assertRaisesRegex(ValueError, "different content"):
            self.ledger.forecast(question["id"], snap["id"], "test", .9, model={"identifier": "test"}, event_id="forecast-retry")
        with self.assertRaisesRegex(ValueError, "different content"):
            self.ledger.resolve(question["id"], 0, [observation["id"]], explanation="first", event_id="resolution-retry")

    def test_failure_coverage_pending_and_correction(self):
        obs,snap,q,_ = self.setup_forecast()
        self.ledger.forecast(q["id"], snap["id"], "failed-method", None, model={"identifier": "test"}, status="failed", reason="timeout")
        self.assertEqual(1, self.ledger.scores()["methods"]["candidate"]["pending"])
        self.assertEqual(0, self.ledger.scores()["methods"]["failed-method"]["coverage"])
        self.now = "2026-11-24T10:11:00Z"
        outcome = self.ledger.capture("outcome", b"done")
        first = self.ledger.resolve(q["id"], 1, [outcome["id"]], explanation="done")
        self.assertAlmostEqual(.09, self.ledger.scores()["methods"]["candidate"]["brier"])
        with self.assertRaises(ValueError):
            self.ledger.resolve(q["id"], 0, [outcome["id"]], explanation="correction")
        correction = self.ledger.resolve(q["id"], 0, [outcome["id"]], explanation="correction", supersedes=first["id"])
        self.assertAlmostEqual(.49, self.ledger.scores()["methods"]["candidate"]["brier"])
        self.assertEqual(correction["id"], self.ledger.scores()["rows"][0]["resolution_id"])
        self.assertEqual(2, len(self.ledger.events("resolution")))

    def test_pairs_require_same_snapshot(self):
        obs,snap,q,_ = self.setup_forecast()
        other = self.ledger.snapshot()
        self.ledger.forecast(q["id"], other["id"], "other", .5, model={"identifier": "test"})
        self.now = "2026-11-24T10:11:00Z"
        self.ledger.resolve(q["id"], 1, [obs["id"]], explanation="test")
        self.assertEqual(0, self.ledger.compare("candidate", "other")["matched"])

    def test_cycle_is_bounded_deduplicated_and_scores_later_capture(self):
        root = Path(self.temp.name)
        source = root / "signal.txt"
        source.write_text("before")
        config = root / "cycle.json"
        config.write_text(json.dumps({"sources": [{"id":"signal","kind":"file","path":"signal.txt"}], "horizon_seconds":120}))
        first = run_cycle(self.ledger, config, "first")
        count = len(self.ledger.events())
        self.assertEqual(first, run_cycle(self.ledger, config, "first"))
        self.assertEqual(count, len(self.ledger.events()))
        source.write_text("after")
        self.now = "2026-11-24T10:03:00Z"
        second = run_cycle(self.ledger, config, "second")
        self.assertEqual(1, len(second["resolved"]))
        self.assertEqual(.25, self.ledger.scores()["methods"]["constant-0.5-v1"]["brier"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_collection_failure_is_preserved(self):
        config = Path(self.temp.name) / "config.json"
        config.write_text(json.dumps({"sources": [{"id":"missing","kind":"file","path":"missing"}]}))
        result = run_cycle(self.ledger, config, "failed")
        self.assertEqual(1, len(result["collection_failures"]))
        self.assertEqual([], self.ledger.events("forecast"))

    def test_concurrent_cycles_exclusively_claim_run_key(self):
        root = Path(self.temp.name)
        (root / "signal.txt").write_text("before")
        config = root / "cycle.json"
        config.write_text(json.dumps({"sources": [{"id": "signal", "kind": "file", "path": "signal.txt"}]}))
        results = self.concurrent_writes("cycle_started", lambda ledger, _: run_cycle(ledger, config, "same-key"))
        self.assertIn("exclusive claim", str(next(r for r in results if isinstance(r, ValueError))))
        for kind in ("cycle_started", "cycle_completed", "observation", "question", "forecast"):
            self.assertEqual(1, len(self.ledger.events(kind)), kind)
        completed = next(r for r in results if isinstance(r, dict))
        self.assertEqual(completed, run_cycle(self.ledger, config, "same-key"))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_failed_collection_expires_monitor_and_removes_pending_status(self):
        root = Path(self.temp.name)
        source = root / "signal.txt"
        source.write_text("before")
        config = root / "cycle.json"
        config.write_text(json.dumps({"sources": [{"id": "signal", "kind": "file", "path": "signal.txt"}],
            "horizon_seconds": 120, "max_lateness_seconds": 60}))
        run_cycle(self.ledger, config, "first")
        source.unlink()
        self.now = "2026-11-24T10:03:00Z"
        boundary = run_cycle(self.ledger, config, "at-window-end")
        self.assertEqual([], boundary["expired"])
        self.assertEqual(1, boundary["scores"]["methods"]["constant-0.5-v1"]["pending"])
        self.now = "2026-11-24T10:04:00Z"
        expired = run_cycle(self.ledger, config, "past-window")
        self.assertEqual(1, len(expired["collection_failures"]))
        self.assertEqual(1, len(expired["expired"]))
        summary = expired["scores"]["methods"]["constant-0.5-v1"]
        self.assertEqual((1, 0, 0), (summary["expired"], summary["pending"], summary["resolved"]))
        run_cycle(self.ledger, config, "still-missing")
        self.assertEqual(1, len(self.ledger.events("monitor_expired")))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_removed_source_monitor_still_expires(self):
        root = Path(self.temp.name)
        (root / "signal.txt").write_text("before")
        config = root / "cycle.json"
        config.write_text(json.dumps({"sources": [{"id": "signal", "kind": "file", "path": "signal.txt"}],
            "horizon_seconds": 120, "max_lateness_seconds": 0}))
        run_cycle(self.ledger, config, "first")
        config.write_text(json.dumps({"sources": [{"id": "other", "kind": "file", "path": "missing.txt"}]}))
        self.now = "2026-11-24T10:03:00Z"
        result = run_cycle(self.ledger, config, "other-source")
        self.assertEqual(1, len(result["expired"]))
        self.assertEqual(0, result["scores"]["methods"]["constant-0.5-v1"]["pending"])

    def test_synthetic_demo_cannot_overwrite_store(self):
        with tempfile.TemporaryDirectory() as root:
            result = demo(root)
            self.assertTrue(result["synthetic"])
            self.assertTrue(result["integrity"]["valid"])
            with self.assertRaises(ValueError):
                demo(root)

    def test_public_status_excludes_source_bytes_paths_and_rejects_mixed_store(self):
        root = Path(self.temp.name)
        source = root / "README.md"
        source.write_text("Public project source")
        config = root / "project.json"
        config.write_text(json.dumps({"sources": [{"id": "epiphysics-readme", "kind": "file", "path": "README.md"}]}))
        run_cycle(self.ledger, config, "public")
        status = project_status(self.ledger, str(source))
        self.assertEqual((1, 1, 1, 0), (status["observations"], status["forecasts"], status["pending"], status["resolved"]))
        self.assertNotIn(str(root), json.dumps(status))
        self.assertNotIn("Public project source", json.dumps(status))
        self.ledger.capture("private-source", b"private text")
        with self.assertRaisesRegex(ValueError, "dedicated store"):
            project_status(self.ledger, str(source))

    def test_public_status_refuses_corrupted_source(self):
        source = Path(self.temp.name) / "README.md"
        observation = self.ledger.capture(str(source.resolve()), b"public")
        (Path(self.temp.name) / "blobs" / observation["body"]["content_hash"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "integrity"):
            project_status(self.ledger, str(source))


if __name__ == "__main__":
    unittest.main()
