"""CLI integration with owned synthetic source bytes, never the development gold."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from epiphysics.store import Ledger, digest


class RetrievalCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ledger = Ledger(self.root / "evidence")
        self.raw = b"The fictional Harbor collective stores receipts in the cobalt archive."
        self.observation = self.ledger.capture("https://example.invalid/receipts", self.raw, event_id="owned-source")
        self.snapshot = self.ledger.snapshot(event_id="owned-snapshot")
        start = self.raw.index(b"cobalt archive")
        template = Path(__file__).resolve().parents[1] / "examples/retrieval/control-development.json"
        self.cohort = json.loads(template.read_text())
        self.cohort["snapshot_id"] = self.snapshot["id"]
        self.cohort["cases"] = [
            {"question_id": "positive", "topic": "fictional_storage", "query": "cobalt archive",
             "answerability": "answerable", "gold_spans": [{"observation_id": self.observation["id"],
                "start": start, "end": start + len(b"cobalt archive"), "sha256": digest(b"cobalt archive")}],
             "rationale": "Owned synthetic fixture names its archive.", "source_url": "https://example.invalid/receipts"},
            {"question_id": "unsupported", "topic": "fictional_storage", "query": "zygomaticnebula",
             "answerability": "unanswerable", "gold_spans": [], "rationale": "No matching word in the owned fixture.",
             "source_url": "https://example.invalid/receipts"},
        ]
        self.cohort["limitations"] = ["Owned synthetic CLI fixture, not real retrieval quality."]
        self.queries = [{"query_id": case["question_id"], "query": case["query"]} for case in self.cohort["cases"]]
        self.env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}

    def tearDown(self):
        self.ledger.close()
        self.temporary.cleanup()

    def cli(self, command, value, *extra):
        path = self.root / "request.json"
        path.write_text(json.dumps(value)) if not isinstance(value, bytes) else path.write_bytes(value)
        return subprocess.run([sys.executable, "-s", "-m", "epiphysics", "--store", str(self.ledger.root),
                               command, str(path), *map(str, extra)], env=self.env,
                              capture_output=True, text=True, timeout=45)

    def freeze(self):
        result = self.cli("freeze-retrieval", {"snapshot_id": self.snapshot["id"],
            "observation_ids": [self.observation["id"]], "event_id": "owned-corpus"})
        self.assertEqual(0, result.returncode, result.stderr)
        corpus = json.loads(result.stdout)
        self.assertEqual("retrieval_corpus", corpus["kind"])
        return corpus

    def test_fresh_runs_reproduce_replay_is_noop_and_evaluation_exports_exclusively(self):
        corpus = self.freeze()
        request = {"corpus_id": corpus["id"], "queries": self.queries, "run_key": "cli-a"}
        first = self.cli("run-retrieval", request)
        self.assertEqual(0, first.returncode, first.stderr)
        terminal = json.loads(first.stdout)
        self.assertEqual("retrieval_completed", terminal["kind"])
        self.assertEqual(["matched", "empty"], [row["status"] for row in terminal["body"]["results"]])
        count = len(self.ledger.events())
        replay = self.cli("run-retrieval", request)
        self.assertEqual(0, replay.returncode, replay.stderr)
        self.assertEqual(terminal, json.loads(replay.stdout))
        self.assertEqual(count, len(self.ledger.events()))
        second = self.cli("run-retrieval", {**request, "run_key": "cli-b"})
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(terminal["body"]["results_hash"], json.loads(second.stdout)["body"]["results_hash"])
        evaluation = {"cohort": self.cohort, "run_terminal_id": terminal["id"]}
        before = len(self.ledger.events())
        scored = self.cli("evaluate-retrieval", evaluation)
        self.assertEqual(0, scored.returncode, scored.stderr)
        report = json.loads(scored.stdout)
        self.assertTrue(report)
        self.assertEqual(before, len(self.ledger.events()), "Evaluation must remain read-only")
        output = self.root / "score.json"
        saved = self.cli("evaluate-retrieval", evaluation, "--output", output)
        self.assertEqual(0, saved.returncode, saved.stderr)
        original = output.read_bytes()
        self.assertEqual(report, json.loads(original))
        refused = self.cli("evaluate-retrieval", evaluation, "--output", output)
        self.assertEqual(2, refused.returncode)
        self.assertEqual(original, output.read_bytes())
        self.assertTrue(self.ledger.verify()["valid"])

    def test_invalid_json_or_candidate_gold_field_refuses_without_events(self):
        before = len(self.ledger.events())
        for command in ("freeze-retrieval", "run-retrieval", "evaluate-retrieval"):
            for raw in (b" " * 1_000_001, b'{"x":1,"x":2}', b"[]"):
                with self.subTest(command=command, raw=raw[:20]):
                    result = self.cli(command, raw)
                    self.assertEqual(2, result.returncode, result.stdout)
                    self.assertEqual(before, len(self.ledger.events()))
        result = self.cli("run-retrieval", {"corpus_id": "absent", "queries": self.queries,
            "run_key": "no-gold", "cohort": self.cohort})
        self.assertEqual(2, result.returncode)
        self.assertIn("unexpected keyword", result.stderr)
        self.assertEqual(before, len(self.ledger.events()))

    def test_explicit_html_recipe_retains_raw_citations_and_refuses_changed_replay(self):
        raw = b'<head>hiddenreceipt</head><main title="attributeonly">cobalt &amp; archive</main>'
        source = self.ledger.capture("https://example.invalid/owned-html", raw,
            media_type="text/html; charset=UTF-8", event_id="owned-html")
        snapshot = self.ledger.snapshot(event_id="owned-html-snapshot")
        frozen = self.cli("freeze-retrieval", {"snapshot_id": snapshot["id"],
            "observation_ids": [source["id"]], "event_id": "owned-html-corpus"})
        self.assertEqual(0, frozen.returncode, frozen.stderr)
        request = {"corpus_id": "owned-html-corpus", "run_key": "html-cli",
            "indexing_recipe": "static-html-text-nodes-v1", "queries": [
                {"query_id": "body", "query": "cobalt archive"},
                {"query_id": "attribute", "query": "attributeonly"},
                {"query_id": "head", "query": "hiddenreceipt"}]}
        executed = self.cli("run-retrieval", request)
        self.assertEqual(0, executed.returncode, executed.stderr)
        terminal = json.loads(executed.stdout)
        body = terminal["body"]
        self.assertEqual(2, body["schema_version"])
        self.assertEqual(request["indexing_recipe"], body["indexing_recipe"])
        self.assertEqual(["matched", "empty", "empty"], [row["status"] for row in body["results"]])
        hit = body["results"][0]["hits"][0]
        self.assertEqual(raw, raw[hit["start"]:hit["end"]])
        self.assertEqual(digest(raw), hit["sha256"])
        self.assertGreater(body["resources"]["projection_bytes"], 0)
        self.assertLess(body["resources"]["indexed_bytes"], len(raw))
        count = len(self.ledger.events())
        replay = self.cli("run-retrieval", request)
        self.assertEqual(terminal, json.loads(replay.stdout))
        changed = self.cli("run-retrieval", {**request, "indexing_recipe": "raw-window-text-v1"})
        self.assertEqual(2, changed.returncode)
        unknown = self.cli("run-retrieval", {**request, "run_key": "unknown", "indexing_recipe": "dynamic"})
        self.assertEqual(2, unknown.returncode)
        self.assertEqual(count, len(self.ledger.events()))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_tampered_source_records_rejection_and_replays_it(self):
        corpus = self.freeze()
        (self.ledger.root / "blobs" / self.observation["body"]["content_hash"]).write_bytes(b"changed")
        request = {"corpus_id": corpus["id"], "queries": self.queries, "run_key": "tampered"}
        failed = self.cli("run-retrieval", request)
        self.assertEqual(2, failed.returncode)
        terminal = json.loads(failed.stdout)
        self.assertEqual("retrieval_rejected", terminal["kind"])
        before = len(self.ledger.events())
        replay = self.cli("run-retrieval", request)
        self.assertEqual(2, replay.returncode)
        self.assertEqual(terminal, json.loads(replay.stdout))
        self.assertEqual(before, len(self.ledger.events()))
        self.assertFalse(self.ledger.verify()["valid"], "The deliberately changed source must remain detectable")
        (self.ledger.root / "blobs" / self.observation["body"]["content_hash"]).write_bytes(self.raw)
        self.assertTrue(self.ledger.verify()["valid"])


if __name__ == "__main__":
    unittest.main()
