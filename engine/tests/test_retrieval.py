from copy import deepcopy
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from epiphysics import retrieval
from epiphysics.assertions import resolve_span
from epiphysics.store import Ledger, canonical, digest


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(Path(self.temp.name), clock=lambda: self.now)
        self.a = self.ledger.capture("synthetic:a", b"alpha beta release date", event_id="a")
        self.b = self.ledger.capture("synthetic:b", b"alpha beta release date", event_id="b")
        self.noise = self.ledger.capture("synthetic:noise", b"alpha " * 10_000, event_id="unselected")
        self.snapshot = self.ledger.snapshot(event_id="snapshot")
        self.corpus = self.freeze()
        self.queries = [{"query_id": "hit", "query": "alpha beta"},
                        {"query_id": "missing", "query": "nonexistenttoken"},
                        {"query_id": "punctuation", "query": "?!_\""}]

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def freeze(self, *, config=None, selected=None, snapshot=None, event_id=None):
        return retrieval.freeze_retrieval_corpus(self.ledger, (snapshot or self.snapshot)["id"],
            ["b", "a"] if selected is None else selected, config=config, event_id=event_id)

    def run_search(self, key="run", *, corpus=None, queries=None):
        return retrieval.run_lexical_retrieval(self.ledger, (corpus or self.corpus)["id"],
            self.queries if queries is None else queries, run_key=key)

    def completed(self, key="run", **kwargs):
        event = self.run_search(key, **kwargs)
        self.assertEqual(event["kind"], "retrieval_completed", event)
        return event

    def reject(self, key="run", pattern=None, **kwargs):
        event = self.run_search(key, **kwargs)
        self.assertEqual(event["kind"], "retrieval_rejected", event)
        if pattern:
            self.assertRegex(event["body"]["error"]["message"], pattern)
        self.assertEqual(self.run_search(key, **kwargs), event)
        return event

    def source_path(self, observation=None):
        return self.ledger.root / "blobs" / (observation or self.a)["body"]["content_hash"]

    def test_actual_search_ties_empties_and_exact_provenance(self):
        event = self.completed()
        results = event["body"]["results"]
        self.assertEqual([hit["observation_id"] for hit in results[0]["hits"]], ["a", "b"])
        self.assertEqual(results[0]["status"], "matched")
        self.assertIsNone(results[0]["reason"])
        self.assertEqual(results[0]["hits"][0]["score"], results[0]["hits"][1]["score"])
        self.assertLess(results[0]["hits"][0]["score"], 0)
        for hit in results[0]["hits"]:
            span = {key: hit[key] for key in ("observation_id", "start", "end", "sha256")}
            self.assertEqual(resolve_span(self.ledger, self.snapshot["id"], span), b"alpha beta release date")
            self.assertNotIn("text", hit)
        self.assertEqual([(row["status"], row["reason"]) for row in results[1:]],
            [("empty", "no_lexical_match"), ("empty", "no_query_terms")])
        self.assertEqual(retrieval.get_retrieval_run(self.ledger, event["id"]), event)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_exact_config_manifest_sources_and_retained_execution_metadata(self):
        corpus = self.corpus["body"]
        self.assertEqual(corpus["config"], retrieval.DEFAULT_CONFIG)
        self.assertEqual([row["observation_id"] for row in corpus["sources"]], ["a", "b"])
        self.assertEqual(corpus["source_bytes"], 46)
        for field in ("sources", "passages", "config"):
            self.assertEqual(corpus[field + "_hash"], digest(canonical(corpus[field]).encode()))
        event = self.completed()
        body = event["body"]
        for role, raw in (("config", canonical(corpus["config"]).encode()),
                          ("queries", canonical(self.queries).encode()),
                          ("implementation", Path(retrieval.__file__).read_bytes())):
            ref = body["artifacts"][role]
            self.assertEqual((self.ledger.root / "blobs" / ref["content_hash"]).read_bytes(), raw)
            self.assertGreater(self.ledger.get(ref["observation_id"])["seq"], self.corpus["seq"])
        self.assertEqual(body["runtime_hash"], digest(canonical(body["runtime"]).encode()))
        self.assertIn("sqlite_source_id", body["runtime"])
        self.assertEqual(body["resources"]["model_calls"], 0)
        self.assertEqual(body["resources"]["external_spend"], 0)

    def test_two_fresh_indexes_are_identical_and_late_unselected_docs_cannot_change_scores(self):
        first = self.completed("first")
        self.now = "2030-01-01T00:01:00Z"
        self.ledger.capture("synthetic:late", b"alpha beta " * 50_000, event_id="late")
        second = self.completed("second")
        self.assertEqual(first["body"]["results"], second["body"]["results"])
        self.assertEqual(first["body"]["results_hash"], second["body"]["results_hash"])
        # A different snapshot includes all noise/artifact observations, but the
        # selected corpus remains exactly the same index and BM25 population.
        newer = self.ledger.snapshot()
        selected = self.freeze(snapshot=newer)
        third = self.completed("third", corpus=selected)
        self.assertEqual(first["body"]["results"], third["body"]["results"])
        self.assertEqual(first["body"]["results_hash"], third["body"]["results_hash"])
        with self.assertRaisesRegex(ValueError, "belong"):
            self.freeze(selected=["late"])

    def test_unselected_document_changes_neither_scores_nor_order(self):
        first = self.completed("with-unselected")
        isolated_temp = tempfile.TemporaryDirectory()
        ledger = Ledger(isolated_temp.name, clock=lambda: self.now)
        try:
            for oid in ("a", "b"):
                ledger.capture("synthetic:" + oid, b"alpha beta release date", event_id=oid)
            snap = ledger.snapshot()
            corpus = retrieval.freeze_retrieval_corpus(ledger, snap["id"], ["a", "b"])
            run = retrieval.run_lexical_retrieval(ledger, corpus["id"], self.queries, run_key="without-unselected")
            self.assertEqual(run["kind"], "retrieval_completed", run)
            self.assertEqual(first["body"]["results"], run["body"]["results"])
        finally:
            ledger.close()
            isolated_temp.cleanup()

    def test_multibyte_windows_are_verbatim_contiguous_exact_spans(self):
        raw = ("a" * 2047 + "🦉" + "e\u0301 café 日本語 " * 350).encode()
        self.ledger.capture("synthetic:unicode", raw, event_id="unicode")
        snapshot = self.ledger.snapshot()
        corpus = self.freeze(snapshot=snapshot, selected=["unicode"])
        rows = corpus["body"]["passages"]
        self.assertEqual(rows[0]["end"], 2047)
        self.assertEqual(rows[1]["start"], 1791)
        self.assertEqual(rows[-1]["end"], len(raw))
        previous_end = 0
        for row in rows:
            chunk = raw[row["start"]:row["end"]]
            self.assertEqual(chunk.decode().encode(), chunk)
            self.assertEqual(row["sha256"], digest(chunk))
            self.assertLessEqual(row["end"] - row["start"], 2048)
            self.assertLessEqual(row["start"], previous_end)
            previous_end = row["end"]
            self.assertEqual(resolve_span(self.ledger, snapshot["id"], row), chunk)
        self.assertEqual(corpus["body"]["passages_hash"], digest(canonical(rows).encode()))
        event = self.completed("unicode", corpus=corpus, queries=[{"query_id": "unicode", "query": "cafe 日本語"}])
        self.assertEqual(event["body"]["results"][0]["status"], "matched")

    def test_empty_source_has_zero_passages_and_search_is_empty(self):
        self.ledger.capture("synthetic:empty", b"", event_id="empty")
        snapshot = self.ledger.snapshot()
        corpus = self.freeze(snapshot=snapshot, selected=["empty"])
        self.assertEqual(corpus["body"]["passages"], [])
        event = self.completed("empty", corpus=corpus)
        self.assertEqual(event["body"]["results"][0]["reason"], "no_lexical_match")

    def test_literal_query_compilation_prevents_fts_syntax(self):
        event = self.completed(queries=[{"query_id": "syntax", "query": '"alpha" OR beta NOT NEAR(foo*) : (release)'}])
        self.assertEqual(event["body"]["results"][0]["status"], "matched")
        self.assertEqual(retrieval._terms("café_Δ3 e\u0301"), ["café", "Δ3", "e"])

    def test_invalid_query_shapes_and_bounds_refuse_before_claim(self):
        invalid = [[], [None], [{"query_id": "q", "query": "alpha", "gold": []}],
            [{"query_id": "q", "query": "x" * 2049}], [{"query_id": "q", "query": "é" * 1025}],
            [{"query_id": "q", "query": "a " * 65}], [{"query_id": "é" * 257, "query": "a"}],
            [{"query_id": "q", "query": "\ud800"}], [{"query_id": "q", "query": True}],
            [{"query_id": "q", "query": "a"}] * 2,
            [{"query_id": str(i), "query": "a"} for i in range(65)]]
        before = self.ledger.events()
        for queries in invalid:
            with self.subTest(queries=str(queries)[:100]), self.assertRaises(ValueError):
                self.run_search(queries=queries)
        self.assertEqual(self.ledger.events(), before)

    def test_config_and_selection_are_strictly_bounded(self):
        configs = [{}, {**retrieval.DEFAULT_CONFIG, "top_k": 0}, {**retrieval.DEFAULT_CONFIG, "top_k": 21},
            {**retrieval.DEFAULT_CONFIG, "top_k": True}, {**retrieval.DEFAULT_CONFIG, "execution_seconds": 31},
            {**retrieval.DEFAULT_CONFIG, "execution_seconds": float("nan")},
            {**retrieval.DEFAULT_CONFIG, "window_bytes": 256}, {**retrieval.DEFAULT_CONFIG, "extra": 1},
            {**retrieval.DEFAULT_CONFIG, "schema_version": True}]
        before = self.ledger.events()
        for config in configs:
            with self.subTest(config=config), self.assertRaises(ValueError):
                self.freeze(config=config)
        for ids in ([], ["a", "a"], ["missing"], ["x" * 513], ["a"] * 65, "a"):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.freeze(selected=ids)
        self.assertEqual(self.ledger.events(), before)
        top_one = self.freeze(config={**retrieval.DEFAULT_CONFIG, "top_k": 1})
        self.assertEqual(len(self.completed("one", corpus=top_one)["body"]["results"][0]["hits"]), 1)

    def test_source_bounds_are_checked_before_reading(self):
        huge = self.ledger.capture("synthetic:huge", b"x" * 1_000_001, event_id="huge")
        snapshot = self.ledger.snapshot()
        with patch.object(Path, "open", side_effect=AssertionError("must reject declared size before read")):
            with self.assertRaisesRegex(ValueError, "declared size"):
                self.freeze(snapshot=snapshot, selected=[huge["id"]])
        ids = []
        for index in range(5):
            ids.append(self.ledger.capture("synthetic:many:" + str(index), b"x" * 900_000)["id"])
        snapshot = self.ledger.snapshot()
        with patch.object(Path, "open", side_effect=AssertionError("must reject total before read")):
            with self.assertRaisesRegex(ValueError, "4 MB"):
                self.freeze(snapshot=snapshot, selected=ids)

    def test_invalid_utf8_is_not_normalized_or_silently_dropped(self):
        self.ledger.capture("synthetic:invalid", b"alpha\xffbeta", event_id="invalid")
        snapshot = self.ledger.snapshot()
        with self.assertRaises(UnicodeDecodeError):
            self.freeze(snapshot=snapshot, selected=["invalid"])

    def test_tampered_or_missing_source_is_rejected_and_replay_is_historical(self):
        path = self.source_path()
        path.write_bytes(b"changed")
        event = self.reject(pattern="hash or size mismatch")
        path.unlink()
        self.assertEqual(self.run_search(), event)
        self.assertEqual(len(self.ledger.events("retrieval_rejected")), 1)

    def test_completed_replay_survives_blob_loss_but_verified_lookup_does_not(self):
        event = self.completed()
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        before = self.ledger.events()
        self.assertEqual(self.run_search(), event)
        self.assertEqual(retrieval.get_retrieval_run(self.ledger, event["id"], verify_bytes=False), event)
        with self.assertRaisesRegex(ValueError, "regular file"):
            retrieval.get_retrieval_run(self.ledger, event["id"])
        self.assertEqual(self.ledger.events(), before)
        self.reject("fresh", pattern="regular file")

    def test_replay_does_not_check_changed_live_code_but_fresh_execution_does(self):
        event = self.completed()
        with patch.object(retrieval, "lexical_search", side_effect=AssertionError("changed loaded candidate")):
            self.assertEqual(self.run_search(), event)
            self.reject("new", pattern="callable changed")

    def test_malformed_corpus_and_observation_metadata_get_durable_rejections(self):
        for index, value in enumerate((None, [], "malformed", {})):
            corpus = self.ledger.append("retrieval_corpus", value, f"bad-corpus-{index}")
            self.reject(f"bad-{index}", corpus=corpus, pattern="corpus")
        malformed = self.ledger.append("observation", [], "bad-observation")
        # Build an otherwise valid snapshot that references the malformed body.
        manifest = [{"id": malformed["id"], "event_hash": malformed["hash"], "content_hash": "0" * 64}]
        snap = self.ledger.append("snapshot", {"cutoff": self.now, "observations": manifest,
            "manifest_hash": digest(canonical(manifest).encode()), "watermark": malformed["seq"]})
        with self.assertRaisesRegex(ValueError, "body must be an object"):
            self.freeze(snapshot=snap, selected=[malformed["id"]])

    def test_forged_manifest_hash_or_span_is_rejected(self):
        for index, mutate in enumerate((lambda body: body.update(passages_hash="0" * 64),
            lambda body: body["passages"][0].update(sha256="0" * 64),
            lambda body: body["sources"][0].update(size=True))):
            body = deepcopy(self.corpus["body"])
            mutate(body)
            if index == 1:
                body["passages_hash"] = digest(canonical(body["passages"]).encode())
            corpus = self.ledger.append("retrieval_corpus", body)
            self.reject(f"forged-{index}", corpus=corpus)

    def test_terminal_boundary_source_mutation_rejects_without_completion(self):
        append = self.ledger.append
        path = self.source_path()
        def corrupt(kind, body, event_id=None, **kwargs):
            if kind == "retrieval_completed":
                path.write_bytes(b"mutated immediately before completion")
            return append(kind, body, event_id, **kwargs)
        with patch.object(self.ledger, "append", side_effect=corrupt):
            self.reject(pattern="hash or size mismatch")
        self.assertEqual(self.ledger.events("retrieval_completed"), [])

    def test_terminal_boundary_artifact_and_result_mutation_reject(self):
        append = self.ledger.append
        for role in ("artifact", "result"):
            def corrupt(kind, body, event_id=None, **kwargs):
                if kind == "retrieval_completed":
                    if role == "artifact":
                        ref = body["artifacts"]["config"]
                        (self.ledger.root / "blobs" / ref["content_hash"]).write_bytes(b"changed config")
                    else:
                        body["results"][0]["hits"][0]["score"] -= 10
                        body["results_hash"] = digest(canonical(body["results"]).encode())
                return append(kind, body, event_id, **kwargs)
            with patch.object(self.ledger, "append", side_effect=corrupt):
                self.reject(role)
            if role == "artifact":
                (self.ledger.root / "blobs" / self.corpus["body"]["config_hash"]).write_bytes(canonical(self.corpus["body"]["config"]).encode())
        self.assertEqual(self.ledger.events("retrieval_completed"), [])

    def test_timeout_is_failure_never_empty_success(self):
        corpus = self.freeze(config={**retrieval.DEFAULT_CONFIG, "execution_seconds": 1e-12})
        event = self.reject("timeout", corpus=corpus, pattern="budget exceeded")
        self.assertEqual(event["body"]["error"]["type"], "TimeoutError")
        self.assertNotIn("results", event["body"])

    def test_sqlite_failure_is_failure_never_empty(self):
        connect = sqlite3.connect
        calls = []
        def unavailable(*args, **kwargs):
            calls.append(args)
            if args[0] == ":memory:":
                raise sqlite3.OperationalError("injected missing FTS5")
            return connect(*args, **kwargs)
        with patch.object(sqlite3, "connect", side_effect=unavailable):
            event = self.reject("sqlite", pattern="injected missing FTS5")
        self.assertEqual(event["body"]["error"]["type"], "OperationalError")
        self.assertTrue(calls)

    def test_changed_request_and_invalid_run_key_refuse(self):
        self.completed()
        with self.assertRaisesRegex(ValueError, "different request"):
            self.run_search(queries=[{"query_id": "changed", "query": "alpha"}])
        for key in ("", "bad key", "x" * 101, True):
            with self.assertRaises(ValueError):
                self.run_search(key)

    def test_foreign_transactions_refuse_before_writes(self):
        before = self.ledger.events()
        self.ledger.db.execute("BEGIN")
        try:
            with self.assertRaisesRegex(ValueError, "standalone"):
                self.run_search()
            with self.assertRaisesRegex(ValueError, "standalone"):
                self.freeze()
            self.assertTrue(self.ledger.db.in_transaction)
        finally:
            self.ledger.db.rollback()
        self.assertEqual(self.ledger.events(), before)
        with self.ledger.atomic_write():
            with self.assertRaisesRegex(ValueError, "standalone"):
                self.run_search()
        self.assertEqual(self.ledger.events(), before)

    def test_interruption_leaves_diagnostic_claim_and_replay_refuses(self):
        append = self.ledger.append
        def interrupt(kind, body, event_id=None, **kwargs):
            if kind == "retrieval_completed":
                raise KeyboardInterrupt("simulated interruption")
            return append(kind, body, event_id, **kwargs)
        with patch.object(self.ledger, "append", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
            self.run_search()
        with self.assertRaisesRegex(ValueError, "requires diagnosis"):
            self.run_search()
        self.assertEqual(len(self.ledger.events("retrieval_started")), 1)
        self.assertEqual(self.ledger.events("retrieval_completed"), [])
        self.assertEqual(self.ledger.events("retrieval_rejected"), [])

    def test_concurrent_execution_has_one_claim_and_terminal(self):
        barrier = threading.Barrier(2)
        outcomes = []
        def worker():
            ledger = Ledger(self.ledger.root, clock=lambda: self.now)
            try:
                barrier.wait(timeout=5)
                outcomes.append(retrieval.run_lexical_retrieval(ledger, self.corpus["id"], self.queries, run_key="race"))
            except ValueError:
                outcomes.append("in-flight refusal")
            finally:
                ledger.close()
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
            self.assertFalse(thread.is_alive())
        successes = [row for row in outcomes if isinstance(row, dict)]
        self.assertTrue(successes)
        self.assertTrue(all(row == successes[0] for row in successes))
        self.assertEqual(successes[0]["kind"], "retrieval_completed", successes)
        self.assertEqual(len(self.ledger.events("retrieval_started")), 1)
        self.assertEqual(len(self.ledger.events("retrieval_completed")), 1)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_getter_checks_terminal_result_runtime_and_artifact_integrity(self):
        event = self.completed()
        # Mutate the storage only after deliberately removing append-only protection.
        # A changed event body with its old hash must always fail the integrity check.
        self.ledger.db.execute("DROP TRIGGER events_no_update")
        body = deepcopy(event["body"])
        body["results"][0]["hits"][0]["score"] -= 1
        self.ledger.db.execute("UPDATE events SET body=? WHERE id=?", (canonical(body), event["id"]))
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError, "Event hash mismatch"):
            retrieval.get_retrieval_run(self.ledger, event["id"])

    def test_candidate_bounds_and_passage_integrity(self):
        config = dict(retrieval.DEFAULT_CONFIG)
        passages = retrieval._passages({"a": b"alpha"}, config)
        self.assertEqual(retrieval.lexical_search(passages, self.queries, config)[0]["hits"][0]["observation_id"], "a")
        for mutate in (lambda rows: rows[0].update(text="other"),
                       lambda rows: rows[0].update(start=True),
                       lambda rows: rows[0].update(end=1_000_001),
                       lambda rows: rows.append(deepcopy(rows[0]))):
            rows = deepcopy(passages)
            mutate(rows)
            with self.assertRaises(ValueError):
                retrieval.lexical_search(rows, self.queries, config)
        with self.assertRaisesRegex(ValueError, "4096"):
            retrieval.lexical_search(passages * 4097, self.queries, config)
        with self.assertRaisesRegex(TimeoutError, "budget exceeded"):
            retrieval._search(passages, self.queries, config, 0)


if __name__ == "__main__":
    unittest.main()
