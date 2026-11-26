"""Owned v1/v2 receipt and runner boundary fixtures; no real study execution."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from epiphysics import assertions, manifests, retrieval, retrieval_contracts as contracts, retrieval_indexing as indexing, store
from epiphysics.store import Ledger, canonical, digest


class ComparisonRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.ledger = Ledger(self.temporary.name, clock=lambda: "2030-01-01T00:00:00Z")
        self.raw = {
            "body": b'<p>cobalt archive</p>',
            "markup": b'<p data-key="cobalt cobalt cobalt cobalt">unrelated</p>',
            "empty": b'<head>cobalt hidden</head>',
            "markdown": b'# cobalt <b>verbatim</b> &amp;',
        }
        self.observations = {}
        for oid, raw in self.raw.items():
            self.observations[oid] = self.ledger.capture("synthetic:" + oid, raw,
                media_type="text/markdown" if oid == "markdown" else "text/html", event_id=oid)
        self.ledger.capture("synthetic:unselected", b"cobalt " * 50_000, event_id="unselected")
        self.snapshot = self.ledger.snapshot(event_id="snapshot")
        self.corpus = retrieval.freeze_retrieval_corpus(self.ledger, "snapshot", list(self.raw))
        self.queries = [{"query_id": "match", "query": "cobalt"},
                        {"query_id": "empty", "query": "?!_"},
                        {"query_id": "miss", "query": "zygomaticnebula"}]

    def tearDown(self):
        self.ledger.close()
        self.temporary.cleanup()

    def run_recipe(self, key, recipe=contracts.RAW_RECIPE):
        return retrieval.run_lexical_retrieval(self.ledger, self.corpus["id"], self.queries,
                                               run_key=key, indexing_recipe=recipe)

    def complete(self, key, recipe=contracts.RAW_RECIPE):
        result = self.run_recipe(key, recipe)
        self.assertEqual("retrieval_completed", result["kind"], result)
        self.assertEqual(result, retrieval.get_retrieval_run(self.ledger, result["id"]))
        return result

    def projection(self, run):
        descriptor = run["body"]["artifacts"]["projection"]
        raw = b"".join((self.ledger.root / "blobs" / ref["content_hash"]).read_bytes()
                       for ref in descriptor["chunks"])
        self.assertEqual(descriptor["size"], len(raw))
        self.assertEqual(descriptor["sha256"], digest(raw))
        return json.loads(raw)

    def legacy_fixture(self, key, *, rejected=False, incomplete=False):
        """Construct owned v1 receipt data, never execute retained historical code.

        These records test the frozen v1 schema/bindings. They are not claims of
        a historical C1 execution or empirical retrieval quality.
        """
        request = {"corpus_id": self.corpus["id"], "corpus_hash": self.corpus["hash"],
                   "queries": deepcopy(self.queries), "query_hash": digest(canonical(self.queries).encode())}
        self.ledger.append("retrieval_started", {"schema_version": 1, "run_key": key, "request": request},
                           f"retrieval:{key}:started")
        if incomplete:
            return request
        if rejected:
            return self.ledger.append("retrieval_rejected", {"schema_version": 1, "run_key": key,
                "request": request, "result": "rejected", "error": {"type": "ValueError", "message": "Owned fixture rejection"}},
                f"retrieval:{key}:terminal")

        def capture(role, raw):
            event = self.ledger.capture(f"retrieval-input:{key}:{role}", raw,
                                       event_id=f"retrieval:{key}:input:{role}")
            return {"observation_id": event["id"], "event_hash": event["hash"],
                    "content_hash": event["body"]["content_hash"], "size": len(raw)}

        implementation = b"# Owned schema-v1 receipt fixture; retained data is never executed.\n"
        config = self.corpus["body"]["config"]
        artifacts = {"config": capture("config", canonical(config).encode()),
            "queries": capture("queries", canonical(self.queries).encode()),
            "implementation": capture("code:epiphysics.retrieval", implementation),
            "dependencies": {module.__name__: capture("code:" + module.__name__, module.IMPLEMENTATION_SOURCE)
                             for module in (store, assertions, manifests)}}
        results = retrieval.lexical_search(contracts._passages(self.raw, config), self.queries, config)
        runtime = retrieval._runtime()
        body = {"schema_version": 1, "run_key": key, "request": request, "result": "completed",
            "corpus_id": self.corpus["id"], "corpus_hash": self.corpus["hash"],
            "config_hash": self.corpus["body"]["config_hash"], "query_hash": request["query_hash"],
            "artifacts": artifacts, "runtime": runtime, "runtime_hash": digest(canonical(runtime).encode()),
            "implementation_hash": digest(implementation), "results": results,
            "results_hash": digest(canonical(results).encode()), "scope": contracts.SCOPE,
            "resources": {"elapsed_seconds": 0.0, "elapsed_scope": contracts.ELAPSED_SCOPE,
                "execution_budget_seconds": config["execution_seconds"],
                "input_bytes": self.corpus["body"]["source_bytes"], "passages": self.corpus["body"]["passage_count"],
                "queries": len(self.queries), "output_bytes": len(canonical(results).encode()),
                "model_calls": 0, "external_spend": 0}}
        return self.ledger.append("retrieval_completed", body, f"retrieval:{key}:terminal")

    def test_both_v2_recipes_reproduce_with_unchanged_raw_citations(self):
        runs = {recipe: [self.complete(recipe + suffix, recipe) for suffix in ("-a", "-b")]
                for recipe in contracts.RECIPE_IDS}
        for recipe, (first, second) in runs.items():
            self.assertEqual(first["body"]["results"], second["body"]["results"])
            self.assertEqual(first["body"]["results_hash"], second["body"]["results_hash"])
            self.assertEqual(first["body"]["projection_hash"], second["body"]["projection_hash"])
            self.assertEqual(2, first["body"]["schema_version"])
            projection = self.projection(first)
            self.assertEqual(recipe, projection["recipe"])
            self.assertEqual(self.corpus["body"]["passages"], [
                {key: row[key] for key in contracts.SPAN_FIELDS} for row in projection["rows"]])
            for result in first["body"]["results"]:
                for hit in result["hits"]:
                    selected = assertions.resolve_span(self.ledger, "snapshot", {key: hit[key] for key in contracts.SPAN_FIELDS})
                    self.assertEqual(self.raw[hit["observation_id"]][hit["start"]:hit["end"]], selected)
        raw_run, html_run = runs[contracts.RAW_RECIPE][0], runs[contracts.HTML_RECIPE][0]
        self.assertNotEqual(raw_run["body"]["results_hash"], html_run["body"]["results_hash"])
        self.assertEqual(1, html_run["body"]["resources"]["empty_windows"])
        self.assertNotIn("markup", [hit["observation_id"] for hit in html_run["body"]["results"][0]["hits"]])
        raw_markdown = next(row for row in self.projection(raw_run)["rows"] if row["observation_id"] == "markdown")
        html_markdown = next(row for row in self.projection(html_run)["rows"] if row["observation_id"] == "markdown")
        self.assertEqual(raw_markdown, html_markdown)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_html_late_and_unselected_sources_cannot_change_scores_or_projection(self):
        first = self.complete("html-before", contracts.HTML_RECIPE)
        self.ledger.capture("synthetic:late", b'<p>cobalt</p>' * 50_000, media_type="text/html", event_id="late")
        second = self.complete("html-after", contracts.HTML_RECIPE)
        self.assertEqual(first["body"]["results"], second["body"]["results"])
        self.assertEqual(first["body"]["projection_hash"], second["body"]["projection_hash"])

    def test_projection_artifacts_split_at_one_megabyte_and_reassemble_exactly(self):
        large = self.ledger.capture("synthetic:large", b"alpha " * 150_000, event_id="large")
        snapshot = self.ledger.snapshot()
        self.corpus = retrieval.freeze_retrieval_corpus(self.ledger, snapshot["id"], [large["id"]])
        run = self.complete("chunked")
        descriptor = run["body"]["artifacts"]["projection"]
        self.assertGreater(descriptor["size"], contracts.MAX_BYTES)
        self.assertGreater(len(descriptor["chunks"]), 1)
        self.assertLessEqual(len(descriptor["chunks"]), contracts.MAX_PROJECTION_CHUNKS)
        self.assertTrue(all(ref["size"] == contracts.MAX_BYTES for ref in descriptor["chunks"][:-1]))
        self.assertLessEqual(descriptor["chunks"][-1]["size"], contracts.MAX_BYTES)
        projection = self.projection(run)
        self.assertEqual(len(self.corpus["body"]["passages"]), len(projection["rows"]))
        self.assertEqual(descriptor["sha256"], digest(canonical(projection).encode()))

    def test_changed_candidate_method_records_a_replayable_claimed_failure(self):
        before = len(self.ledger.events("observation"))
        with patch.object(Ledger, "capture", lambda *args, **kwargs: None):
            rejected = self.run_recipe("changed-capture")
        self.assertEqual("retrieval_rejected", rejected["kind"])
        self.assertIn("ledger method changed: capture", rejected["body"]["error"]["message"])
        self.assertEqual(before, len(self.ledger.events("observation")))
        self.assertEqual(rejected, self.run_recipe("changed-capture"))

    def test_recipe_is_bound_to_claim_and_unknown_recipe_refuses_before_claim(self):
        first = self.complete("fixed")
        before = self.ledger.events()
        with self.assertRaisesRegex(ValueError, "different request"):
            self.run_recipe("fixed", contracts.HTML_RECIPE)
        for recipe in ("custom", True, {"callback": "arbitrary"}):
            with self.subTest(recipe=recipe), self.assertRaises(ValueError):
                self.run_recipe("unknown", recipe)
        self.assertEqual(before, self.ledger.events())
        self.assertEqual(first, self.run_recipe("fixed"))

    def test_v1_completion_validates_and_replays_exactly_without_upgrade_or_execution(self):
        legacy = self.legacy_fixture("legacy")
        self.assertEqual(legacy, retrieval.get_retrieval_run(self.ledger, legacy["id"]))
        before = self.ledger.events()
        with patch.object(indexing, "project_index", side_effect=AssertionError("Historical receipt was executed")), \
                patch.object(indexing, "runtime_sources", side_effect=AssertionError("Historical receipt checked live code")):
            replay = self.run_recipe("legacy")
        self.assertEqual(legacy, replay)
        self.assertEqual(1, replay["body"]["schema_version"])
        self.assertNotIn("indexing_recipe", replay["body"])
        self.assertEqual(before, self.ledger.events())
        with self.assertRaisesRegex(ValueError, "different recipe"):
            self.run_recipe("legacy", contracts.HTML_RECIPE)

    def test_v1_blob_loss_allows_historical_replay_but_not_verified_lookup(self):
        legacy = self.legacy_fixture("legacy-loss")
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        self.assertEqual(legacy, self.run_recipe("legacy-loss"))
        self.assertEqual(legacy, retrieval.get_retrieval_run(self.ledger, legacy["id"], verify_bytes=False))
        with self.assertRaises(ValueError):
            retrieval.get_retrieval_run(self.ledger, legacy["id"])

    def test_v1_rejection_and_interrupted_claim_keep_legacy_behavior(self):
        rejection = self.legacy_fixture("legacy-rejected", rejected=True)
        self.assertEqual(rejection, self.run_recipe("legacy-rejected"))
        self.legacy_fixture("legacy-incomplete", incomplete=True)
        with self.assertRaisesRegex(ValueError, "requires diagnosis"):
            self.run_recipe("legacy-incomplete")

    def test_corrupt_projection_refuses_verified_lookup_and_fresh_reuse(self):
        completed = self.complete("projection-corrupt", contracts.HTML_RECIPE)
        ref = completed["body"]["artifacts"]["projection"]["chunks"][0]
        path = self.ledger.root / "blobs" / ref["content_hash"]
        path.write_bytes(b"corrupt projection")
        with self.assertRaisesRegex(ValueError, "hash or size mismatch"):
            retrieval.get_retrieval_run(self.ledger, completed["id"])
        self.assertEqual(completed, self.run_recipe("projection-corrupt", contracts.HTML_RECIPE))
        rejected = self.run_recipe("projection-fresh", contracts.HTML_RECIPE)
        self.assertEqual("retrieval_rejected", rejected["kind"])
        self.assertIn("corrupted", rejected["body"]["error"]["message"])

    def test_terminal_boundary_projection_corruption_has_one_rejection(self):
        append = self.ledger.append

        def corrupt(kind, body, event_id=None, **options):
            if kind == "retrieval_completed":
                ref = body["artifacts"]["projection"]["chunks"][0]
                (self.ledger.root / "blobs" / ref["content_hash"]).write_bytes(b"terminal corruption")
            return append(kind, body, event_id, **options)

        with patch.object(self.ledger, "append", corrupt):
            rejected = self.run_recipe("terminal-map", contracts.HTML_RECIPE)
        self.assertEqual("retrieval_rejected", rejected["kind"])
        self.assertEqual([], self.ledger.events("retrieval_completed"))
        self.assertEqual(1, len(self.ledger.events("retrieval_rejected")))

    def test_completion_recomputes_a_fresh_index_and_deadline_covers_revalidation(self):
        connect, creates = sqlite3.connect, []

        class CountedConnection(sqlite3.Connection):
            def execute(self, sql, parameters=(), /):
                if sql.startswith("CREATE VIRTUAL TABLE passages"):
                    creates.append(sql)
                return super().execute(sql, parameters)

        with patch.object(sqlite3, "connect", lambda *args, **kwargs: connect(*args, **kwargs, factory=CountedConnection)):
            self.complete("two-indexes", contracts.HTML_RECIPE)
        self.assertEqual(2, len(creates))
        append = self.ledger.append

        def expire(kind, body, event_id=None, **options):
            if kind == "retrieval_completed":
                future = time.monotonic() + 100
                with patch.object(retrieval.time, "monotonic", lambda: future):
                    return append(kind, body, event_id, **options)
            return append(kind, body, event_id, **options)

        with patch.object(self.ledger, "append", expire):
            rejected = self.run_recipe("expired-revalidation", contracts.HTML_RECIPE)
        self.assertEqual("retrieval_rejected", rejected["kind"])
        self.assertEqual("TimeoutError", rejected["body"]["error"]["type"])

    def test_projection_semantics_changing_at_commit_cannot_record_completion(self):
        append = self.ledger.append

        def mutate(kind, body, event_id=None, **options):
            if kind == "retrieval_completed":
                with patch.object(indexing, "_EXCLUDED", frozenset()):
                    return append(kind, body, event_id, **options)
            return append(kind, body, event_id, **options)

        with patch.object(self.ledger, "append", mutate):
            rejected = self.run_recipe("changed-projection", contracts.HTML_RECIPE)
        self.assertEqual("retrieval_rejected", rejected["kind"])
        self.assertRegex(rejected["body"]["error"]["message"], "projection changed|source|constant|configuration")
        self.assertEqual([], self.ledger.events("retrieval_completed"))

    def test_different_recipe_race_has_one_exclusive_owner(self):
        barrier, outcomes = threading.Barrier(2), []

        def worker(recipe):
            ledger = Ledger(self.ledger.root, clock=lambda: "2030-01-01T00:00:00Z")
            try:
                barrier.wait(timeout=5)
                outcomes.append(retrieval.run_lexical_retrieval(ledger, self.corpus["id"], self.queries,
                                                              run_key="recipe-race", indexing_recipe=recipe))
            except ValueError:
                outcomes.append("refused")
            finally:
                ledger.close()

        threads = [threading.Thread(target=worker, args=(recipe,)) for recipe in contracts.RECIPE_IDS]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
            self.assertFalse(thread.is_alive())
        completed = [event for event in outcomes if isinstance(event, dict)]
        self.assertEqual(1, len(completed), outcomes)
        self.assertEqual("retrieval_completed", completed[0]["kind"])
        self.assertEqual(1, len(self.ledger.events("retrieval_started")))
        self.assertEqual(1, len(self.ledger.events("retrieval_completed")))


class RunnerIdentityTests(unittest.TestCase):
    def test_source_closures_refuse_collisions_before_overwrite(self):
        self.assertEqual({"same": b"a", "other": b"b"}, retrieval._merge_runtime_sources(
            {"same": b"a"}, {"same": b"a", "other": b"b"}))
        with self.assertRaisesRegex(ValueError, "closure conflict: shared"):
            retrieval._merge_runtime_sources({"runner": b"r"}, {"shared": b"contract"}, {"shared": b"candidate"})

    def test_imported_aliases_runtime_helpers_and_ledger_methods_are_pinned(self):
        for name in ("canonical", "digest", "_read_transaction", "_time", "_keys", "_checked_corpus"):
            with self.subTest(alias=name), patch.object(retrieval, name, lambda *args: None):
                with self.assertRaisesRegex(ValueError, "alias changed"):
                    retrieval._runtime_sources()
        for owner, name in ((contracts, "_runtime_sources"), (contracts, "validate_projection"),
                            (indexing, "runtime_sources"), (indexing, "project_index"), (indexing, "lexical_search")):
            with self.subTest(helper=name), patch.object(owner, name, lambda *args: None):
                with self.assertRaisesRegex(ValueError, "runtime helper changed"):
                    retrieval._runtime_sources()
        for name in ("get", "append", "capture", "atomic_write", "_decode", "_require_writable", "open_readonly"):
            with self.subTest(method=name), patch.object(Ledger, name, lambda *args: None):
                with self.assertRaisesRegex(ValueError, "ledger method changed"):
                    retrieval._runtime_sources()

    def test_fresh_source_identity_lists_candidate_and_neutral_closures(self):
        sources = retrieval._runtime_sources()
        self.assertEqual(set(contracts.DEPENDENCY_NAMES_V2) | set(contracts.STDLIB_NAMES) | {"epiphysics.retrieval"}, set(sources))
        self.assertEqual(contracts.IMPLEMENTATION_SOURCE, sources[contracts.__name__])
        self.assertEqual(indexing.IMPLEMENTATION_SOURCE, sources[indexing.__name__])

    def test_dependency_reload_stale_runner_alias_and_stale_bytecode_refuse(self):
        program = r'''
import importlib, json, os, py_compile, sys
from pathlib import Path
mode=sys.argv[1]
if mode=='bytecode':
    path=Path('epiphysics/retrieval.py').resolve()
    source=path.read_bytes(); stat=path.stat()
    py_compile.compile(str(path),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
    changed=source.replace(b'"unicode_version": unicodedata.unidata_version',b'"unicode_versioN": unicodedata.unidata_version',1)
    assert changed != source and len(changed)==len(source)
    path.write_bytes(changed); os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
from epiphysics import retrieval, retrieval_indexing, retrieval_contracts
if mode=='alias':
    old=retrieval.run_lexical_retrieval
    importlib.reload(retrieval)
elif mode=='indexing_reload':
    importlib.reload(retrieval_indexing)
elif mode=='contracts_reload':
    importlib.reload(retrieval_contracts)
try:
    if mode=='alias':
        old(None,'unused',[],run_key='unused')
    else:
        retrieval._runtime_sources()
    result={'status':'unexpected_success'}
except ValueError as error:
    result={'status':'refused','message':str(error)}
print(json.dumps(result))
'''
        for mode in ("bytecode", "alias", "indexing_reload", "contracts_reload"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(Path(retrieval.__file__).parent, root / "epiphysics", ignore=shutil.ignore_patterns("__pycache__"))
                completed = subprocess.run([sys.executable, "-s", "-c", program, mode], cwd=root,
                    env={**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(0, completed.returncode, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual("refused", result["status"])
                self.assertRegex(result["message"], "[Ss]tale|reloaded|code does not match|alias changed|helper changed")


if __name__ == "__main__":
    unittest.main()
