import json
import os
from datetime import timedelta
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import manifest_checks, manifests
from epiphysics.store import Ledger, instant


class ManifestCheckTests(unittest.TestCase):
    def test_actual_api_passes_all_declared_checks(self):
        report = manifest_checks.run_manifest_checks()
        self.assertTrue(report["all_passed"], report["checks"])
        self.assertEqual("representation-manifest-probes-v2", report["version"])
        self.assertEqual({"representation_manifest_preservation": {"passed": 22, "checks": 22}}, report["counts"])
        self.assertEqual(22, len({row["id"] for row in report["checks"]}))
        self.assertEqual(1, report["metrics"]["representation_manifest_preservation"])
        self.assertNotIn("transformation_preservation", report["metrics"])

    def test_constant_method_identity_is_detected(self):
        with patch.object(manifests, "method_identity", return_value="representation-method-v1:" + "0" * 64):
            report = manifest_checks.run_manifest_checks()
        semantic = next(row for row in report["checks"] if row["id"] == "semantic_descriptor_fields_change_identity")
        self.assertFalse(semantic["passed"])
        self.assertFalse(report["all_passed"])

    def test_rejecting_every_registration_does_not_pass_positive_controls(self):
        with patch.object(manifests, "register_manifest", side_effect=ValueError("All registration broken")):
            report = manifest_checks.run_manifest_checks()
        retained = next(row for row in report["checks"] if row["id"] == "preserve_inputs_snapshot_units_and_reported_cost")
        self.assertFalse(retained["passed"])
        self.assertIn("All registration broken", retained["diagnostic"])
        self.assertLess(report["metrics"]["representation_manifest_preservation"], 1)

    def test_broken_forecast_api_is_detected_by_positive_binding_control(self):
        with patch.object(manifests, "forecast_manifest", side_effect=ValueError("All forecasts broken")):
            report = manifest_checks.run_manifest_checks()
        binding = next(row for row in report["checks"] if row["id"] == "bind_forecast_to_exact_manifest_and_cost")
        self.assertFalse(binding["passed"])
        self.assertIn("All forecasts broken", binding["diagnostic"])

    def test_permissive_registration_cannot_pass_rejection_controls(self):
        original = manifests.register_manifest
        def unsafe_registration(ledger, *args, **kwargs):
            try:
                return original(ledger, *args, **kwargs)
            except ValueError:
                return ledger.append("representation_manifest", {"unsafe": True})
        with patch.object(manifests, "register_manifest", side_effect=unsafe_registration):
            report = manifest_checks.run_manifest_checks()
        for check_id in ("reject_late_artifact_despite_old_publication", "reject_duplicate_evidence_declaration"):
            with self.subTest(check=check_id):
                self.assertFalse(next(row for row in report["checks"] if row["id"] == check_id)["passed"])

    def test_missing_append_binding_validation_is_detected(self):
        original = Ledger.forecast
        def without_binding_validation(ledger, *args, **kwargs):
            kwargs.pop("validate", None)
            return original(ledger, *args, **kwargs)
        with patch.object(Ledger, "forecast", new=without_binding_validation):
            report = manifest_checks.run_manifest_checks()
        for check_id in ("reject_predictor_changed_at_forecast_append", "reject_inference_receipt_changed_at_forecast_append"):
            with self.subTest(check=check_id):
                self.assertFalse(next(row for row in report["checks"] if row["id"] == check_id)["passed"])
        self.assertLess(report["metrics"]["representation_manifest_preservation"], 1)

    def test_rejecting_successful_replay_is_detected(self):
        original = Ledger.forecast
        def rejecting_replay(ledger, *args, **kwargs):
            if any(event["id"] == kwargs.get("event_id") for event in ledger.events("forecast")):
                raise ValueError("Replay rejected after lost blob")
            return original(ledger, *args, **kwargs)
        with patch.object(Ledger, "forecast", new=rejecting_replay):
            report = manifest_checks.run_manifest_checks()
        replay = next(row for row in report["checks"] if row["id"] == "exact_forecast_replay_survives_blob_loss")
        self.assertFalse(replay["passed"])
        self.assertIn("Replay rejected after lost blob", replay["diagnostic"])

    def test_cli_registers_manifest_and_bound_forecast(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "ledger"
            ledger = Ledger(store)
            try:
                source = ledger.capture("synthetic:cli-manifest", b"Invoice A is for 12 USD.")
                artifacts = {role: ledger.capture(f"synthetic:cli:{role}", raw)["id"]
                             for role, raw in manifest_checks.ARTIFACT_BYTES.items()}
                snapshot = ledger.snapshot()
                representation = ledger.representation(snapshot["id"], {"entities": [{
                    "id": "invoice", "basis": "reported", "evidence_ids": [source["id"]]}]},
                    observer="cli-observer", method="cli-fixture-builder")
                cutoff = instant(snapshot["body"]["cutoff"])
                question = ledger.question("Invoice paid?", (cutoff + timedelta(minutes=5)).isoformat(),
                    (cutoff + timedelta(minutes=10)).isoformat(), "Synthetic receipt", "contract_obligation")
            finally:
                ledger.close()
            payload = {"representation_id": representation["id"], "encoding": "graph", "schema_id": "invoice-v1",
                       "artifacts": artifacts, "task": {"id": "invoice-paid", "family": "contract_obligation", "outcome_type": "binary"},
                       "horizon_seconds": 600, "units": {"invoice_amount": "USD"}, "evidence_ids": [source["id"]],
                       "construction_cost": manifest_checks._unknown_cost(), "event_id": "cli-manifest"}
            request = root / "manifest.json"
            request.write_text(json.dumps(payload))
            environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(store)]
            registered = subprocess.run([*command, "record", "manifest", str(request)], env=environment,
                                        capture_output=True, text=True, timeout=10)
            self.assertEqual(0, registered.returncode, registered.stderr)
            manifest = json.loads(registered.stdout)
            self.assertEqual("representation_manifest", manifest["kind"])
            request.write_text(json.dumps({"manifest_id": manifest["id"], "question_id": question["id"], "probability": 0.6}))
            predicted = subprocess.run([*command, "record", "manifest-forecast", str(request)], env=environment,
                                       capture_output=True, text=True, timeout=10)
            self.assertEqual(0, predicted.returncode, predicted.stderr)
            forecast = json.loads(predicted.stdout)
            self.assertEqual(manifest["body"]["method_id"], forecast["body"]["method"])
            self.assertEqual(manifest["hash"], forecast["body"]["model"]["representation_manifest_hash"])
            ledger = Ledger(store)
            try:
                self.assertTrue(ledger.verify()["valid"])
                self.assertEqual(1, len(ledger.events("forecast")))
            finally:
                ledger.close()

    def test_cli_refuses_oversized_duplicate_and_nonobject_json_before_append(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = root / "request.json"
            store = root / "ledger"
            environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(store), "record", "manifest", str(request)]
            for contents, message in ((b" " * 1_000_001, "exceeds 1 MB"),
                                      (b'{"representation_id":"a","representation_id":"b"}', "Duplicate JSON field"),
                                      (b"[]", "must be a JSON object"),
                                      (b'{"cost": NaN}', "Out of range float")):
                with self.subTest(message=message):
                    request.write_bytes(contents)
                    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
                    self.assertEqual(2, result.returncode, result.stderr)
                    self.assertIn(message, result.stderr)
            ledger = Ledger(store)
            try:
                self.assertEqual([], ledger.events())
            finally:
                ledger.close()


if __name__ == "__main__":
    unittest.main()
