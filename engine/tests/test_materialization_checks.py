from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import materialization, materialization_checks
from epiphysics.store import Ledger


class MaterializationCheckTests(unittest.TestCase):
    def test_actual_materialization_passes_all_contracts(self):
        report = materialization_checks.run_materialization_checks()
        self.assertTrue(report["all_passed"], report["checks"])
        self.assertEqual("materialization-probes-v1", report["version"])
        self.assertEqual({"output_manifest_materialization": {"passed": 30, "checks": 30}}, report["counts"])
        self.assertEqual(30, len({row["id"] for row in report["checks"]}))
        self.assertNotIn("retrieval_baseline_reproducibility", report["metrics"])

    def test_reject_all_cannot_pass_positive_or_durable_rejection_controls(self):
        with patch.object(materialization, "materialize_graph_outputs", side_effect=ValueError("Materialization unavailable")):
            report = materialization_checks.run_materialization_checks()
        self.assertEqual(0, report["metrics"]["output_manifest_materialization"])
        self.assertFalse(report["all_passed"])

    def test_removed_atomic_group_exposes_partial_outputs_and_is_detected(self):
        @contextmanager
        def non_atomic(ledger):
            yield ledger.clock()
        with patch.object(Ledger, "atomic_write", new=non_atomic):
            with materialization_checks._fixture() as fixture:
                self.assertTrue(materialization_checks._outputs(fixture))
            with materialization_checks._fixture() as fixture:
                self.assertFalse(materialization_checks._atomic_visibility(fixture))
            with materialization_checks._fixture() as fixture:
                self.assertFalse(materialization_checks._atomic_failure(fixture))
                self.assertTrue(any(event["id"].startswith("graph-materialization:")
                                    for event in fixture["ledger"].events("representation_manifest")))
            with materialization_checks._fixture() as fixture:
                self.assertFalse(materialization_checks._atomic_failure(fixture, interruption=True))

    def test_wrong_output_and_manifest_bindings_are_independently_detected(self):
        with materialization_checks._fixture() as fixture:
            bundle = materialization_checks._bundle(fixture)
            changed = deepcopy(bundle)
            changed["representations"]["left"]["body"]["model"]["entities"][0]["amount"]["value"] = 999
            with patch.object(materialization, "get_materialized_outputs", return_value=changed):
                self.assertFalse(materialization_checks._outputs(fixture))
            changed = deepcopy(bundle)
            changed["manifests"]["left"]["body"]["snapshot_id"] = "wrong-snapshot"
            with patch.object(materialization, "get_materialized_outputs", return_value=changed):
                self.assertFalse(materialization_checks._bindings(fixture))

    def test_lost_merge_parent_and_lost_loss_link_are_detected(self):
        with materialization_checks._fixture("merge_graphs") as fixture:
            bundle = materialization_checks._bundle(fixture)
            self.assertTrue(materialization_checks._ancestry(fixture))
            changed = deepcopy(bundle)
            changed["receipt"]["body"]["parents"].pop()
            with patch.object(materialization, "get_materialized_outputs", return_value=changed):
                self.assertFalse(materialization_checks._ancestry(fixture))
        with materialization_checks._fixture() as fixture:
            receipt = materialization_checks._completed(fixture)
            changed = deepcopy(receipt)
            changed["body"]["links"].pop("losses")
            with patch.object(materialization, "materialize_graph_outputs", return_value=changed):
                self.assertFalse(materialization_checks._links(fixture))

    def test_removed_completion_validator_is_detected_while_normal_outputs_pass(self):
        original = Ledger.append
        def unchecked(ledger, kind, *args, **kwargs):
            if kind == "graph_materialization_completed":
                kwargs.pop("validate", None)
            return original(ledger, kind, *args, **kwargs)
        with patch.object(Ledger, "append", new=unchecked):
            with materialization_checks._fixture() as fixture:
                self.assertTrue(materialization_checks._outputs(fixture))
            with materialization_checks._fixture() as fixture:
                self.assertFalse(materialization_checks._boundary_mutation(fixture))
                self.assertEqual(1, len(fixture["ledger"].events("graph_materialization_completed")))

    def test_disabled_metadata_caps_fail_resource_controls_without_large_writes(self):
        with patch.object(materialization, "MAX_DESCRIPTOR_BYTES", 32_768), patch.object(materialization, "MAX_OUTPUT_RECORD_BYTES", 16_000_000):
            for operation in ("partition_entities", "merge_graphs"):
                with materialization_checks._fixture(operation) as fixture:
                    self.assertTrue(materialization_checks._outputs(fixture))
            for operation, bound in (("identity", "descriptor"), ("partition_entities", "aggregate")):
                with self.subTest(bound=bound), materialization_checks._fixture(operation, bounds=bound) as fixture:
                    before = len(fixture["ledger"].events("representation"))
                    self.assertFalse(materialization_checks._resource_bound(fixture))
                    self.assertEqual(before, len(fixture["ledger"].events("representation")))

    def test_disabled_group_kind_restrictions_fail_time_boundary_control(self):
        with patch.object(Ledger, "_check_atomic_kind", new=lambda ledger, kind: None):
            with materialization_checks._fixture() as fixture:
                self.assertTrue(materialization_checks._outputs(fixture))
            with materialization_checks._fixture() as fixture:
                self.assertFalse(materialization_checks._grouped_time_boundary(fixture))

    def test_removing_only_recomputation_equality_is_detected_by_coherent_forgery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "epiphysics"
            shutil.copytree(Path(materialization.__file__).parent, package, ignore=shutil.ignore_patterns("__pycache__"))
            path = package / "materialization.py"
            source = path.read_text()
            guard = '    if canonical({key: body[key] for key in prepared}) != canonical(prepared):\n        raise ValueError("Execution output, losses or ancestry do not match fixed recomputation")\n'
            self.assertEqual(1, source.count(guard))
            path.write_text(source.replace(guard, "", 1))
            code = """import json
from epiphysics import materialization_checks as checks
with checks._fixture() as fixture:
    positive = checks._outputs(fixture)
with checks._fixture() as fixture:
    detected = not checks._forged_completion(fixture)
    rows = fixture['ledger'].events('graph_materialization_completed')
    accepted = len(rows) == 1
    bundle = checks.materialization.get_materialized_outputs(fixture['ledger'], rows[0]['id'])
    value = bundle['representations']['left']['body']['model']['entities'][0]['amount']['value']
print(json.dumps({'positive':positive,'detected':detected,'accepted':accepted,'value':value}))
"""
            env = {**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
            result = subprocess.run([sys.executable, "-s", "-c", code], cwd=root, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual({"positive": True, "detected": True, "accepted": True, "value": 999}, json.loads(result.stdout))

    def test_cli_materializes_replays_and_records_rejection(self):
        with materialization_checks._fixture() as fixture:
            ledger = fixture["ledger"]
            path = ledger.root / "request.json"
            request = {"completion_id": fixture["completion"]["id"], "run_key": "cli-materialization"}
            path.write_text(json.dumps(request))
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(ledger.root), "materialize-graphs", str(path)]
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            terminal = json.loads(result.stdout)
            self.assertEqual("graph_materialization_completed", terminal["kind"])
            self.assertEqual({"left", "right"}, set(terminal["body"]["outputs"]))
            count = len(ledger.events())
            replay = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, replay.returncode, replay.stderr)
            self.assertEqual(terminal, json.loads(replay.stdout))
            self.assertEqual(count, len(ledger.events()))
            blob = ledger.root / "blobs" / fixture["config"]["body"]["content_hash"]
            blob.write_bytes(b"Changed config")
            path.write_text(json.dumps({**request, "run_key": "cli-rejected"}))
            rejected = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(2, rejected.returncode, rejected.stderr)
            self.assertEqual("graph_materialization_rejected", json.loads(rejected.stdout)["kind"])

    def test_cli_rejects_oversize_duplicate_and_unknown_fields_before_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, store = root / "request.json", root / "ledger"
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(store), "materialize-graphs", str(request)]
            for raw, message in ((b" " * 1_000_001, "exceeds 1 MB"), (b'{"run_key":"a","run_key":"b"}', "Duplicate JSON field"),
                                 (b'{"completion_id":"x","run_key":"a","outputs":{}}', "unexpected keyword")):
                request.write_bytes(raw)
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertIn(message, result.stderr)
            ledger = Ledger(store)
            try:
                self.assertEqual([], ledger.events())
            finally:
                ledger.close()


if __name__ == "__main__":
    unittest.main()
