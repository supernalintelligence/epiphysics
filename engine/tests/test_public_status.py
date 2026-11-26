import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from epiphysics.cli import main
from epiphysics.cycle import run_cycle
from epiphysics.public_status import project_status
from epiphysics.store import Ledger


class PublicStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "README.md"
        self.source.write_text("Public project source")
        self.config = self.root / "project.json"
        self.config.write_text(json.dumps({
            "sources": [{"id": "epiphysics-readme", "kind": "file", "path": "README.md"}],
            "horizon_seconds": 120,
        }))
        self.now = "2026-11-25T10:00:00Z"
        self.ledger = Ledger(self.root / "store", clock=lambda: self.now)
        self.first_cycle = run_cycle(self.ledger, self.config, "first")

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def publish(self, output):
        stdout, stderr = io.StringIO(), io.StringIO()
        arguments = ["epiphysics", "--store", str(self.ledger.root), "publish-status",
            "--source", str(self.source), "--output", str(output)]
        with patch("sys.argv", arguments), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main()
        return result, stderr.getvalue()

    def test_publish_rejects_store_source_aliases_and_non_json_output(self):
        store_alias = self.root / "store-link"
        store_alias.symlink_to(self.ledger.root, target_is_directory=True)
        source_symlink = self.root / "source-link.json"
        source_symlink.symlink_to(self.source)
        source_hardlink = self.root / "source-hardlink.json"
        source_hardlink.hardlink_to(self.source)
        plain_output = self.root / "status.txt"
        plain_output.write_text("Keep this file")
        observation = self.ledger.events("observation")[0]
        blob = self.ledger.root / "blobs" / observation["body"]["content_hash"]
        head = self.ledger.verify()["head"]
        cases = [
            (self.ledger.root / "ledger.sqlite", "outside the evidence store"),
            (blob, "outside the evidence store"),
            (self.ledger.root / "status.json", "outside the evidence store"),
            (store_alias / "status.json", "outside the evidence store"),
            (self.source, "must not alias"),
            (source_symlink, "must not alias"),
            (source_hardlink, "must not alias"),
            (plain_output, ".json artifact"),
        ]
        for output, message in cases:
            with self.subTest(output=output.name, message=message):
                result, error = self.publish(output)
                self.assertEqual(2, result)
                self.assertIn(message, error)
                self.assertEqual("Public project source", self.source.read_text())
                integrity = self.ledger.verify()
                self.assertTrue(integrity["valid"])
                self.assertEqual(head, integrity["head"])
        self.assertEqual("Keep this file", plain_output.read_text())
        self.assertFalse((self.ledger.root / "status.json").exists())

    def test_publish_replaces_json_and_preserves_completed_run(self):
        output = self.root / "site" / "status.json"
        output.parent.mkdir()
        output.write_text('{"old": true}\n')
        before = self.ledger.events()
        self.assertEqual((0, ""), self.publish(output))
        published = output.read_text()
        self.assertEqual(project_status(self.ledger, str(self.source)), json.loads(published))
        self.assertEqual(self.first_cycle, run_cycle(self.ledger, self.config, "first"))
        self.assertEqual((0, ""), self.publish(output))
        self.assertEqual(published, output.read_text())
        self.assertEqual(before, self.ledger.events())
        self.assertEqual([output], list(output.parent.iterdir()))

    def test_public_status_rejects_other_methods_probabilities_and_attempt_statuses(self):
        cases = [
            {"method": "learned-model", "probability": 0.5, "status": "predicted"},
            {"method": "constant-0.5-v1", "probability": 0.9, "status": "predicted"},
            {"method": "constant-0.5-v1", "probability": None, "status": "failed"},
            {"method": "constant-0.5-v1", "probability": None, "status": "abstained"},
        ]
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                ledger = Ledger(root, clock=lambda: self.now)
                try:
                    ledger.capture(str(self.source.resolve()), self.source.read_bytes())
                    snapshot = ledger.snapshot()
                    question = ledger.question("Will bytes change?", "2026-11-25T10:01:00Z",
                        "2026-11-25T10:02:00Z", "Compare bytes", "source:epiphysics-readme")
                    ledger.forecast(question["id"], snapshot["id"], **case,
                        model={"identifier": case["method"]}, reason="test")
                    with self.assertRaisesRegex(ValueError, "constant-0.5-v1 predicted forecasts"):
                        project_status(ledger, str(self.source))
                    self.assertFalse(ledger.db.in_transaction)
                finally:
                    ledger.close()

    def test_public_status_uses_one_snapshot_during_concurrent_collection(self):
        initial = project_status(self.ledger, str(self.source))
        verify = self.ledger.verify
        other = Ledger(self.ledger.root, clock=lambda: self.now)

        def collect_before_verification():
            self.now = "2026-11-25T10:03:00Z"
            run_cycle(other, self.config, "concurrent")
            return verify()

        try:
            with patch.object(self.ledger, "verify", side_effect=collect_before_verification):
                concurrent_status = project_status(self.ledger, str(self.source))
        finally:
            other.close()
        self.assertEqual(initial, concurrent_status)
        self.assertFalse(self.ledger.db.in_transaction)
        current = project_status(self.ledger, str(self.source))
        self.assertEqual((2, 2, 1, 1),
            (current["observations"], current["forecasts"], current["resolved"], current["pending"]))
        self.assertEqual(self.now, current["last_capture_at"])


if __name__ == "__main__":
    unittest.main()
