from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import transformation_checks, transforms
from epiphysics.store import Ledger


class TransformationCheckTests(unittest.TestCase):
    def test_actual_fixed_operations_pass_each_declared_contract(self):
        report = transformation_checks.run_transformation_checks()
        self.assertTrue(report["all_passed"], report["checks"])
        self.assertEqual("graph-transformation-probes-v2", report["version"])
        self.assertEqual({"transformation_preservation": {"passed": 26, "checks": 26}}, report["counts"])
        self.assertEqual(26, len({row["id"] for row in report["checks"]}))
        self.assertEqual(1, report["metrics"]["transformation_preservation"])
        self.assertNotIn("split_merge_preservation", report["metrics"])

    def test_rejecting_all_execution_cannot_pass_positive_controls(self):
        with patch.object(transforms, "execute_graph_transform", side_effect=ValueError("Execution unavailable")):
            report = transformation_checks.run_transformation_checks()
        self.assertEqual(0, report["metrics"]["transformation_preservation"])
        self.assertFalse(report["all_passed"])
        self.assertIn("Execution unavailable", report["checks"][0]["diagnostic"])

    def test_removing_only_completion_validation_fails_the_capability_report(self):
        original_append = Ledger.append
        def unchecked_completion(ledger, kind, *args, **kwargs):
            if kind == "graph_transform_completed":
                kwargs.pop("validate", None)
            return original_append(ledger, kind, *args, **kwargs)
        with patch.object(Ledger, "append", new=unchecked_completion):
            report = transformation_checks.run_transformation_checks()
        checks = {row["id"]: row for row in report["checks"]}
        self.assertTrue(checks["execute_identity_with_exact_model_and_zero_loss"]["passed"])
        self.assertFalse(checks["reject_config_changed_before_completion_append"]["passed"])
        self.assertFalse(checks["reject_parent_evidence_changed_before_completion_append"]["passed"])
        self.assertFalse(report["all_passed"])
        self.assertLess(report["metrics"]["transformation_preservation"], 1)

    def test_surrogate_rejections_are_durable_utf8_safe_and_replayable(self):
        for which in ("recipe", "config"):
            with self.subTest(which=which), transformation_checks._fixture(malformed=which) as fixture:
                self.assertTrue(transformation_checks._unicode_rejection_replay(which)(fixture))
                ledger = fixture["ledger"]
                self.assertEqual(1, len(ledger.events("graph_transform_started")))
                self.assertEqual(1, len(ledger.events("graph_transform_rejected")))
                self.assertEqual([], ledger.events("graph_transform_completed"))

    def test_projection_check_rejects_copying_the_parent_as_declared_output(self):
        with transformation_checks._fixture() as fixture:
            actual = transformation_checks._completed(fixture)
            self.assertTrue(transformation_checks._projection(fixture))
            copied = deepcopy(actual)
            copied["body"]["output_model"] = deepcopy(fixture["model"])
            # Corrupt the returned completion after a real execution. The check
            # must independently distinguish projection from a copied input.
            with patch.object(transforms, "execute_graph_transform", return_value=copied):
                self.assertFalse(transformation_checks._projection(fixture))

    def test_loss_check_rejects_missing_omission_records(self):
        with transformation_checks._fixture() as fixture:
            actual = transformation_checks._completed(fixture)
            self.assertTrue(transformation_checks._losses(fixture))
            for missing in ("removed_entities", "removed_relations", "removed_evidence_ids"):
                with self.subTest(loss=missing):
                    changed = deepcopy(actual)
                    changed["body"]["losses"][missing] = []
                    with patch.object(transforms, "execute_graph_transform", return_value=changed):
                        self.assertFalse(transformation_checks._losses(fixture))

    def test_projection_check_rejects_dropped_parallel_edge_or_reversed_direction(self):
        with transformation_checks._fixture() as fixture:
            actual = transformation_checks._completed(fixture)
            for mutation in ("parallel", "direction"):
                with self.subTest(mutation=mutation):
                    changed = deepcopy(actual)
                    edges = changed["body"]["output_model"]["relations"]
                    if mutation == "parallel":
                        edges.pop(1)
                    else:
                        edges[2]["source"], edges[2]["target"] = edges[2]["target"], edges[2]["source"]
                    with patch.object(transforms, "execute_graph_transform", return_value=changed):
                        self.assertFalse(transformation_checks._projection(fixture))

    def test_cli_executes_replays_and_reports_rejection(self):
        with transformation_checks._fixture() as fixture:
            ledger = fixture["ledger"]
            request = ledger.root / "request.json"
            payload = {"parent_manifest_id": fixture["manifest"]["id"],
                       "recipe_observation_id": fixture["recipes"]["project"], "run_key": "cli-transform"}
            request.write_text(json.dumps(payload))
            environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(ledger.root), "graph-transform", str(request)]
            executed = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, executed.returncode, executed.stderr)
            terminal = json.loads(executed.stdout)
            self.assertEqual("graph_transform_completed", terminal["kind"])
            self.assertEqual(transformation_checks._projection_expected(fixture), terminal["body"]["output_model"])
            count = len(ledger.events())
            replay = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, replay.returncode, replay.stderr)
            self.assertEqual(terminal, json.loads(replay.stdout))
            self.assertEqual(count, len(ledger.events()))
            request.write_text(json.dumps({**payload, "recipe_observation_id": fixture["recipes"]["unknown"], "run_key": "cli-rejected"}))
            rejected = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(2, rejected.returncode, rejected.stderr)
            self.assertEqual("graph_transform_rejected", json.loads(rejected.stdout)["kind"])
            self.assertEqual(1, len(ledger.events("graph_transform_rejected")))

    def test_cli_rejects_unbounded_or_duplicate_requests_without_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = root / "request.json"
            store = root / "ledger"
            environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(store), "graph-transform", str(request)]
            for raw, message in ((b" " * 1_000_001, "exceeds 1 MB"),
                                 (b'{"run_key":"a","run_key":"b"}', "Duplicate JSON field")):
                request.write_bytes(raw)
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
