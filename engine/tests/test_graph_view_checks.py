from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import graph_view_checks, graph_views
from epiphysics.store import Ledger, canonical, digest


class GraphViewCheckTests(unittest.TestCase):
    def test_actual_partition_merge_passes_each_declared_contract(self):
        report = graph_view_checks.run_graph_view_checks()
        self.assertTrue(report["all_passed"], report["checks"])
        self.assertEqual("graph-view-probes-v1", report["version"])
        self.assertEqual({"split_merge_preservation": {"passed": 45, "checks": 45}}, report["counts"])
        self.assertEqual(45, len({row["id"] for row in report["checks"]}))
        self.assertEqual(1, report["metrics"]["split_merge_preservation"])
        self.assertNotIn("output_manifest_materialization", report["metrics"])

    def test_reject_all_cannot_pass_positive_or_durable_rejection_controls(self):
        with patch.object(graph_views, "execute_graph_views", side_effect=ValueError("Unavailable graph views")):
            report = graph_view_checks.run_graph_view_checks()
        self.assertEqual(0, report["metrics"]["split_merge_preservation"])
        self.assertFalse(report["all_passed"])
        self.assertIn("Unavailable graph views", report["checks"][0]["diagnostic"])

    def test_dropped_parallel_edge_is_detected_even_when_output_is_valid_and_rehashed(self):
        original = graph_views._compute_graph_views
        sources = graph_views._runtime_sources()
        def drop_edge(*args):
            computed = original(*args)
            for output in computed["outputs"].values():
                output["model"]["relations"] = [row for row in output["model"]["relations"] if row["type"] != "owes"]
                output["model_hash"] = digest(canonical(output["model"]).encode())
            return computed
        with patch.object(graph_views, "_runtime_sources", return_value=sources), patch.object(graph_views, "_compute_graph_views", side_effect=drop_edge):
            with graph_view_checks._fixture() as fixture:
                result = graph_view_checks._completed(fixture)
                self.assertEqual("graph_views_completed", result["kind"])
                self.assertFalse(graph_view_checks._partition(fixture))
            with graph_view_checks._fixture() as fixture:
                self.assertFalse(graph_view_checks._merge(fixture))

    def test_overwriting_conflicts_is_detected_without_reject_all_shortcut(self):
        original = graph_views._compute_graph_views
        sources = graph_views._runtime_sources()
        def overwrite_conflicts(parent_models, operation, config):
            parent_models = deepcopy(parent_models)
            if operation == "merge_graphs":
                winners = {row["id"]: row for _, model in parent_models for row in model["entities"]}
                for _, model in parent_models:
                    model["entities"] = [deepcopy(winners[row["id"]]) for row in model["entities"]]
            return original(parent_models, operation, config)
        with patch.object(graph_views, "_runtime_sources", return_value=sources), patch.object(graph_views, "_compute_graph_views", side_effect=overwrite_conflicts):
            with graph_view_checks._fixture() as fixture:
                self.assertTrue(graph_view_checks._merge(fixture))
            for kind in ("entity", "evidence"):
                with self.subTest(conflict=kind), graph_view_checks._fixture(conflict=kind) as fixture:
                    self.assertFalse(graph_view_checks._rejected(fixture, "merge"))
                    self.assertEqual(1, len(fixture["ledger"].events("graph_views_completed")))

    def test_fabricated_parent_copy_is_detected_despite_valid_model_hash(self):
        original = graph_views._compute_graph_views
        sources = graph_views._runtime_sources()
        def fake_partition(parent_models, operation, config):
            computed = original(parent_models, operation, config)
            if operation == "partition_entities":
                model = deepcopy(parent_models[0][1])
                computed["outputs"] = {"left": {"model": model, "model_hash": digest(canonical(model).encode())}}
            return computed
        with patch.object(graph_views, "_runtime_sources", return_value=sources), patch.object(graph_views, "_compute_graph_views", side_effect=fake_partition):
            with graph_view_checks._fixture() as fixture:
                self.assertFalse(graph_view_checks._partition(fixture))
                self.assertEqual(1, len(fixture["ledger"].events("graph_views_completed")))
            with graph_view_checks._fixture() as fixture:
                self.assertTrue(graph_view_checks._merge(fixture))

    def test_omitted_losses_and_ancestry_are_detected_independently(self):
        for recipe, field, check in (("partition", "losses", graph_view_checks._losses),
                                     ("partition", "source_to_output", graph_view_checks._mapping),
                                     ("merge", "deduplications", graph_view_checks._deduplication)):
            with self.subTest(field=field), graph_view_checks._fixture() as fixture:
                actual = graph_view_checks._completed(fixture, recipe)
                changed = deepcopy(actual)
                if field == "source_to_output":
                    changed["body"][field] = []
                else:
                    changed["body"][field] = {key: [] for key in changed["body"][field]}
                with patch.object(graph_views, "execute_graph_views", return_value=changed):
                    self.assertFalse(check(fixture))

    def test_removing_completion_validation_fails_exact_boundary_controls(self):
        original_append = Ledger.append
        def unchecked(ledger, kind, *args, **kwargs):
            if kind == "graph_views_completed":
                kwargs.pop("validate", None)
            return original_append(ledger, kind, *args, **kwargs)
        with patch.object(Ledger, "append", new=unchecked):
            report = graph_view_checks.run_graph_view_checks()
        checks = {row["id"]: row for row in report["checks"]}
        self.assertTrue(checks["execute_exhaustive_partition_with_directed_parallel_edges_and_self_loops"]["passed"])
        self.assertTrue(checks["execute_strict_merge_preserving_units_attributes_and_provenance"]["passed"])
        for kind in ("config", "parent", "dependency"):
            self.assertFalse(checks[f"reject_{kind}_changed_before_completion_append"]["passed"])
        self.assertEqual(42, report["counts"]["split_merge_preservation"]["passed"])
        self.assertFalse(report["all_passed"])

    def test_disabling_identifier_caps_is_detected_with_ordinary_operations_still_passing(self):
        # Small fixed 129/513-byte probes: do not allocate the original large receipt.
        with patch.object(graph_views, "MAX_VIEW_NAME_BYTES", 2048), patch.object(graph_views, "MAX_PARENT_ID_BYTES", 2048):
            report = graph_view_checks.run_graph_view_checks()
        checks = {row["id"]: row for row in report["checks"]}
        self.assertTrue(checks["execute_exhaustive_partition_with_directed_parallel_edges_and_self_loops"]["passed"])
        self.assertTrue(checks["execute_strict_merge_preserving_units_attributes_and_provenance"]["passed"])
        self.assertFalse(checks["reject_oversized_utf8_view_name_before_expansion"]["passed"])
        self.assertFalse(checks["reject_oversized_utf8_parent_id_before_claim"]["passed"])
        self.assertEqual({"split_merge_preservation": {"passed": 43, "checks": 45}}, report["counts"])
        self.assertFalse(report["all_passed"])

    def test_malformed_surrogates_leave_durable_replayable_rejections(self):
        for kind in ("recipe", "config"):
            with self.subTest(kind=kind), graph_view_checks._fixture(malformed=kind) as fixture:
                self.assertTrue(graph_view_checks._unicode_replay(fixture))
                self.assertEqual(1, len(fixture["ledger"].events("graph_views_started")))
                self.assertEqual(1, len(fixture["ledger"].events("graph_views_rejected")))

    def test_cli_executes_replays_and_reports_partition_rejection(self):
        with graph_view_checks._fixture() as fixture:
            ledger = fixture["ledger"]
            request = ledger.root / "request.json"
            payload = {"parent_manifest_ids": graph_view_checks._parents(fixture, "merge"),
                       "recipe_observation_id": fixture["recipes"]["merge"], "run_key": "cli-merge"}
            request.write_text(json.dumps(payload))
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(ledger.root), "graph-views", str(request)]
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            terminal = json.loads(result.stdout)
            self.assertEqual("graph_views_completed", terminal["kind"])
            self.assertEqual(graph_view_checks._output_rows({"merged": graph_view_checks._merge_expected(fixture)}), terminal["body"]["outputs"])
            count = len(ledger.events())
            replay = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(0, replay.returncode, replay.stderr)
            self.assertEqual(terminal, json.loads(replay.stdout))
            self.assertEqual(count, len(ledger.events()))
            payload.update(parent_manifest_ids=[fixture["manifest"]["id"]], recipe_observation_id=fixture["recipes"]["missing"], run_key="cli-rejected")
            request.write_text(json.dumps(payload))
            rejected = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(2, rejected.returncode, rejected.stderr)
            self.assertEqual("graph_views_rejected", json.loads(rejected.stdout)["kind"])

    def test_cli_rejects_unbounded_or_duplicate_input_without_claiming(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, store = root / "request.json", root / "ledger"
            env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, "-s", "-m", "epiphysics", "--store", str(store), "graph-views", str(request)]
            for raw, message in ((b" " * 1_000_001, "exceeds 1 MB"), (b'{"run_key":"a","run_key":"b"}', "Duplicate JSON field")):
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
