import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from epiphysics import assertions, source_span_checks
from epiphysics.store import Ledger, digest, utc_now


class SourceSpanCheckTests(unittest.TestCase):
    def test_actual_api_passes_each_declared_probe(self):
        report = source_span_checks.run_source_span_checks()
        self.assertTrue(report["all_passed"], report["checks"])
        self.assertEqual({"source_span_resolution": {"passed": 8, "checks": 8},
                          "assertion_history_preservation": {"passed": 6, "checks": 6}}, report["counts"])
        self.assertEqual(14, len({row["id"] for row in report["checks"]}))
        self.assertEqual(1, report["metrics"]["source_span_resolution"])
        self.assertEqual(1, report["metrics"]["assertion_history_preservation"])

    def test_broken_resolver_is_detected_in_actual_implementation(self):
        with patch.object(assertions, "resolve_span", return_value=b"wrong bytes"):
            report = source_span_checks.run_source_span_checks()
        exact = next(row for row in report["checks"] if row["id"] == "exact_multibyte_span")
        self.assertFalse(exact["passed"])
        self.assertLess(report["metrics"]["source_span_resolution"], 1)
        self.assertFalse(report["all_passed"])

    def test_rejecting_every_write_does_not_pass_positive_controls(self):
        with patch.object(assertions, "record_assertion", side_effect=ValueError("All writes broken")):
            report = source_span_checks.run_source_span_checks()
        typed = next(row for row in report["checks"] if row["id"] == "record_typed_value_and_source_span")
        self.assertFalse(typed["passed"])
        self.assertEqual(0, report["metrics"]["assertion_history_preservation"])
        self.assertIn("All writes broken", typed["diagnostic"])

    def test_erasing_historical_queries_is_detected(self):
        with patch.object(assertions, "assertions_as_of", return_value=[]):
            report = source_span_checks.run_source_span_checks()
        self.assertLess(report["metrics"]["assertion_history_preservation"], 1)
        old = next(row for row in report["checks"] if row["id"] == "historical_view_preserves_original")
        self.assertFalse(old["passed"])

    def test_assertion_cli_records_and_queries_real_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "ledger"
            ledger = Ledger(store)
            try:
                raw = b"Service A owes 12 USD."
                observation = ledger.capture("synthetic:cli-probe", raw)
                snapshot = ledger.snapshot()
            finally:
                ledger.close()
            payload = {"snapshot_id": snapshot["id"], "subject": "service-a", "predicate": "owes",
                       "object": {"kind": "value", "value": 12, "unit": "USD"}, "observer": "cli-observer",
                       "method": "synthetic-cli-test", "basis": "reported", "event_id": "cli-assertion",
                       "spans": [{"observation_id": observation["id"], "start": 0, "end": len(raw), "sha256": digest(raw)}]}
            request = Path(directory) / "assertion.json"
            request.write_text(json.dumps(payload))
            environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-m", "epiphysics", "--store", str(store)]
            recorded = subprocess.run([*command, "record", "assertion", str(request)], env=environment,
                                      capture_output=True, text=True, timeout=10)
            self.assertEqual(0, recorded.returncode, recorded.stderr)
            self.assertEqual("assertion", json.loads(recorded.stdout)["kind"])
            queried = subprocess.run([*command, "assertions", "--known-at", utc_now(), "--observer", "cli-observer"],
                                     env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, queried.returncode, queried.stderr)
            self.assertEqual(["cli-assertion"], [row["id"] for row in json.loads(queried.stdout)])


if __name__ == "__main__":
    unittest.main()
