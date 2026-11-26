"""Read-only connections use owned temporary stores, never real evidence."""

from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from epiphysics.assertions import _read_transaction, resolve_span
from epiphysics.retrieval import freeze_retrieval_corpus, get_retrieval_run, run_lexical_retrieval
from epiphysics.retrieval_evaluation import evaluate_retrieval, project_queries
from epiphysics.store import Ledger, digest


class ReadonlyLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # URI punctuation must remain part of the path, not SQLite options.
        self.root = Path(self.temporary.name) / "owned store #?%"
        self.writer = Ledger(self.root)
        self.raw = b"The fictional cobalt archive holds the receipts."
        self.source = self.writer.capture("synthetic:archive", self.raw, event_id="source")
        self.snapshot = self.writer.snapshot(event_id="snapshot")
        self.readers = []

    def tearDown(self):
        for reader in self.readers:
            reader.close()
        if self.writer is not None:
            self.writer.close()
        self.temporary.cleanup()

    def reader(self):
        reader = Ledger.open_readonly(self.root)
        self.readers.append(reader)
        return reader

    def data_state(self):
        # SQLite coordination sidecars are deliberately distinct from evidence
        # data. Main database and every retained blob must remain byte-identical.
        paths = [self.root / "ledger.sqlite", *(self.root / "blobs").iterdir()]
        return {str(path.relative_to(self.root)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in paths}

    def test_existing_reads_exact_class_and_read_transactions_work(self):
        before = self.data_state()
        reader = self.reader()
        self.assertIs(type(reader), Ledger)
        self.assertIs(reader.db.row_factory, sqlite3.Row)
        self.assertEqual(1, reader.db.execute("PRAGMA query_only").fetchone()[0])
        self.assertIsNone(reader._atomic_time)
        self.assertFalse(reader._atomic_failed)
        self.assertFalse(reader._append_active)
        self.assertEqual(self.source, reader.get(self.source["id"], "observation"))
        self.assertEqual(self.writer.events(), reader.events())
        with _read_transaction(reader):
            self.assertTrue(reader.db.in_transaction)
            self.assertEqual(self.writer.events("observation"), reader.events("observation"))
        self.assertFalse(reader.db.in_transaction)
        self.assertTrue(reader.verify()["valid"])
        self.assertEqual(before, self.data_state())

    def test_open_never_initializes_schema_directories_or_journal_mode(self):
        original_connect = sqlite3.connect
        calls, statements = [], []

        def connect(database, **options):
            calls.append((database, options))
            connection = original_connect(database, **options)
            connection.set_trace_callback(statements.append)
            return connection

        with patch.object(Ledger, "__init__", side_effect=AssertionError("Writable initializer called")), \
                patch.object(Path, "mkdir", side_effect=AssertionError("Read-only opener created a directory")), \
                patch.object(sqlite3, "connect", connect):
            reader = self.reader()
        self.assertEqual(1, len(calls))
        uri, options = calls[0]
        self.assertEqual((self.root.resolve() / "ledger.sqlite").as_uri() + "?mode=ro", uri)
        self.assertEqual({"uri": True, "timeout": 10}, options)
        self.assertNotIn("immutable", uri)
        self.assertEqual(["PRAGMA query_only=ON"], statements)
        self.assertEqual(self.source, reader.get("source"))

    def test_missing_database_or_parent_creates_nothing(self):
        absent_root = Path(self.temporary.name) / "absent" / "nested"
        with self.assertRaisesRegex(ValueError, "existing database"):
            Ledger.open_readonly(absent_root)
        self.assertFalse(absent_root.parent.exists())
        empty_root = Path(self.temporary.name) / "empty"
        empty_root.mkdir()
        with self.assertRaisesRegex(ValueError, "existing database"):
            Ledger.open_readonly(empty_root)
        self.assertEqual([], list(empty_root.iterdir()))
        (empty_root / "ledger.sqlite").mkdir()
        with self.assertRaisesRegex(ValueError, "existing database"):
            Ledger.open_readonly(empty_root)
        self.assertEqual([empty_root / "ledger.sqlite"], list(empty_root.iterdir()))

    def test_open_does_not_create_a_missing_blob_directory(self):
        empty_root = Path(self.temporary.name) / "database-only"
        writer = Ledger(empty_root)
        writer.close()
        (empty_root / "blobs").rmdir()
        reader = Ledger.open_readonly(empty_root)
        self.readers.append(reader)
        self.assertEqual([], reader.events())
        self.assertFalse((empty_root / "blobs").exists())

    def test_all_mutation_entry_points_refuse_before_database_or_blob_access(self):
        reader = self.reader()
        before = self.data_state()
        events = self.writer.events()
        statements = []
        reader.db.set_trace_callback(statements.append)

        def atomic():
            with reader.atomic_write():
                self.fail("Entered a read-only atomic write")

        operations = {
            "append": lambda: reader.append("new", {"value": 1}),
            "append replay": lambda: reader.append("observation", self.source["body"], "source"),
            "capture": lambda: reader.capture("synthetic:new", b"new bytes"),
            "capture replay": lambda: reader.capture("synthetic:archive", self.raw, event_id="source"),
            "atomic_write": atomic,
            "snapshot": reader.snapshot,
            "representation": lambda: reader.representation("missing", {}, observer="test", method="test"),
            "question": lambda: reader.question("Question?", "invalid", "invalid", "rule", "family"),
            "forecast": lambda: reader.forecast("missing", "missing", "test", 0.5, model={}),
            "resolve": lambda: reader.resolve("missing", 1, ["missing"], explanation="test"),
        }
        with patch.object(Path, "open", side_effect=AssertionError("Read-only mutation touched a blob")):
            for name, operation in operations.items():
                with self.subTest(operation=name), self.assertRaisesRegex(ValueError, "Read-only ledger"):
                    operation()
        self.assertEqual([], statements)
        self.assertFalse(reader.db.in_transaction)
        self.assertEqual(events, self.writer.events())
        self.assertEqual(before, self.data_state())

    def test_uri_readonly_blocks_direct_writes_even_if_query_only_is_disabled(self):
        reader = self.reader()
        before = self.data_state()
        for query_only in (True, False):
            with self.subTest(query_only=query_only):
                reader.db.execute("PRAGMA query_only=" + ("ON" if query_only else "OFF"))
                with self.assertRaisesRegex(sqlite3.OperationalError, "readonly"):
                    reader.db.execute("CREATE TABLE forbidden(value TEXT)")
                with self.assertRaisesRegex(ValueError, "Read-only ledger"):
                    reader.capture("synthetic:new", b"must not write")
        self.assertEqual(before, self.data_state())
        self.assertEqual([], reader.db.execute("SELECT name FROM sqlite_master WHERE name='forbidden'").fetchall())

    def test_live_wal_remains_visible_and_read_transaction_has_a_coherent_snapshot(self):
        reader = self.reader()
        wal = self.root / "ledger.sqlite-wal"
        before_wal = wal.read_bytes()
        self.assertEqual(self.source, reader.get("source"))
        self.assertEqual(before_wal, wal.read_bytes())
        with _read_transaction(reader):
            before = reader.events()
            added = self.writer.append("owned-marker", {"new": True}, "live-marker")
            self.assertEqual(before, reader.events())
        self.assertEqual(added, reader.get("live-marker"))
        self.assertEqual(self.writer.events(), reader.events())

    def test_retrieval_receipt_and_evaluator_accept_exact_readonly_ledger(self):
        corpus = freeze_retrieval_corpus(self.writer, "snapshot", ["source"])
        start = self.raw.index(b"cobalt archive")
        span = {"observation_id": "source", "start": start, "end": start + len(b"cobalt archive"),
                "sha256": digest(b"cobalt archive")}
        cohort = {"schema_version": 1, "snapshot_id": "snapshot", "cohort": "development", "cases": [
            {"question_id": "supported", "query": "cobalt archive", "answerability": "answerable", "gold_spans": [span]},
            {"question_id": "unsupported", "query": "zygomaticnebula", "answerability": "unanswerable", "gold_spans": []},
        ]}
        run = run_lexical_retrieval(self.writer, corpus["id"], project_queries(cohort), run_key="owned")
        self.assertEqual("retrieval_completed", run["kind"], run)
        expected = evaluate_retrieval(self.writer, cohort, run["id"])
        self.writer.close()
        self.writer = None
        before = self.data_state()
        before_files = {path.relative_to(self.root) for path in self.root.rglob("*")}
        reader = self.reader()
        with _read_transaction(reader):
            self.assertEqual(run, get_retrieval_run(reader, run["id"], verify_bytes=True))
            self.assertEqual(b"cobalt archive", resolve_span(reader, "snapshot", span))
            report = evaluate_retrieval(reader, cohort, run["id"])
        self.assertEqual(expected, report)
        self.assertEqual(1, report["metrics"]["gold_span_recall_at_k"]["5"]["value"])
        self.assertEqual(before, self.data_state())
        after_files = {path.relative_to(self.root) for path in self.root.rglob("*")}
        self.assertLessEqual(after_files - before_files, {Path("ledger.sqlite-wal"), Path("ledger.sqlite-shm")})

    def test_subclasses_cannot_change_the_exact_class_contract(self):
        class AlternateLedger(Ledger):
            pass

        with self.assertRaisesRegex(ValueError, "exact Ledger class"):
            AlternateLedger.open_readonly(self.root)


if __name__ == "__main__":
    unittest.main()
