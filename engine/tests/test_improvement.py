import copy
import json
import os
import subprocess
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from epiphysics import assertions, graph_views, improvement, manifests, materialization, transforms
from epiphysics.store import Ledger


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "improvement"
# Real assessments may use the policy's full 30 seconds; allow process startup
# and cleanup in the test harness without changing production acceptance bounds.
ASSESSMENT_WAIT_SECONDS = 40


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = self.root / "ledger"
        self.policy = self.root / "policy.json"
        self.suite = self.root / "entities.json"
        self.policy.write_bytes((EXAMPLES / "policy.json").read_bytes())
        self.suite.write_bytes((EXAMPLES / "entities.json").read_bytes())
        self.ledger = Ledger(self.store)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def run_assessment(self, candidate="reference", run_key="first", after="initial", work="Run a synthetic control"):
        return improvement.assess(self.ledger, self.policy, self.suite, candidate, run_key,
                                  after_step=after, completed_work=work)

    def test_completion_atomically_queues_successor_and_replay_is_noop(self):
        result = self.run_assessment()
        events = self.ledger.events()
        self.assertEqual("improvement_completed", events[-1]["kind"])
        self.assertEqual(result["next_step"], events[-1]["body"]["next_step"])
        self.assertEqual("build_retrieval_baseline", result["next_step"]["action"])
        self.assertEqual(1, result["report"]["metrics"]["source_span_resolution"])
        self.assertEqual(1, result["report"]["metrics"]["assertion_history_preservation"])
        self.assertEqual(1, result["report"]["metrics"]["representation_manifest_preservation"])
        self.assertEqual({"source_span_resolution": {"passed": 8, "checks": 8},
                          "assertion_history_preservation": {"passed": 6, "checks": 6}},
                         result["report"]["source_span_checks"]["counts"])
        self.assertEqual("representation-manifest-probes-v2", result["report"]["manifest_checks"]["version"])
        self.assertEqual({"representation_manifest_preservation": {"passed": 22, "checks": 22}},
                         result["report"]["manifest_checks"]["counts"])
        self.assertEqual(1, result["report"]["metrics"]["transformation_preservation"])
        self.assertEqual("graph-transformation-probes-v2", result["report"]["transformation_checks"]["version"])
        self.assertEqual({"transformation_preservation": {"passed": 26, "checks": 26}},
                         result["report"]["transformation_checks"]["counts"])
        self.assertEqual(1, result["report"]["metrics"]["split_merge_preservation"])
        self.assertEqual("graph-view-probes-v1", result["report"]["graph_view_checks"]["version"])
        self.assertEqual({"split_merge_preservation": {"passed": 45, "checks": 45}},
                         result["report"]["graph_view_checks"]["counts"])
        self.assertEqual(1, result["report"]["metrics"]["output_manifest_materialization"])
        self.assertEqual("materialization-probes-v1", result["report"]["materialization_checks"]["version"])
        self.assertEqual({"output_manifest_materialization": {"passed": 30, "checks": 30}},
                         result["report"]["materialization_checks"]["counts"])
        self.assertNotIn("retrieval_baseline_reproducibility", result["report"]["metrics"])
        self.assertIsNone(result["next_step"]["observed"])
        self.assertTrue({"assertions", "source_span_probe", "store", "manifests", "manifest_probe", "transforms", "transformation_probe", "graph_views", "graph_view_probe", "materialization", "materialization_probe"} <= result["request"]["manifest"].keys())
        self.assertFalse(result["next_step"]["scale_change_allowed"])
        self.assertEqual(0, result["actual_resources"]["external_spend"])
        self.assertEqual(result, self.run_assessment())
        self.assertEqual(len(events), len(self.ledger.events()))
        self.assertEqual("first:next", improvement.status(self.ledger)["next_step"]["id"])
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.run_assessment(work="A different completion claim")
        with self.assertRaisesRegex(ValueError, "Stale predecessor"):
            self.run_assessment(run_key="second")

    def test_measured_failure_selects_repair_and_next_assessment_records_outcome(self):
        first = self.run_assessment("degraded")
        self.assertLess(first["report"]["metrics"]["accuracy"], 1)
        self.assertNotEqual("build_retrieval_baseline", first["next_step"]["action"])
        second = self.run_assessment(run_key="second", after="first:next")
        self.assertEqual("measured", second["prior_action_outcome"]["status"])
        self.assertTrue(second["prior_action_outcome"]["target_met"])
        self.assertIsNone(first["next_step"]["estimated_success_probability"])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_changed_inputs_cannot_reuse_run_key(self):
        self.run_assessment()
        policy = json.loads(self.policy.read_text())
        policy["version"] = "different"
        self.policy.write_text(json.dumps(policy))
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.run_assessment()

    def test_removing_a_failed_check_cannot_be_reported_as_improvement(self):
        first = self.run_assessment("degraded")
        failed_case = next(case for case in first["report"]["cases"] if any(not check["correct"] for check in case["checks"]))
        failed_id = next(check["id"] for check in failed_case["checks"] if not check["correct"])
        suite = json.loads(self.suite.read_text())
        case = next(case for case in suite["cases"] if case["id"] == failed_case["id"])
        case["checks"] = [check for check in case["checks"] if check["id"] != failed_id]
        self.suite.write_text(json.dumps(suite))
        second = self.run_assessment(run_key="second", after="first:next")
        outcome = second["prior_action_outcome"]
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertEqual(["suite"], outcome["changed_inputs"])
        self.assertNotIn("change", outcome)
        self.assertNotIn("target_met", outcome)
        self.assertEqual(29, second["report"]["metrics"]["checks"])
        self.assertEqual("second:next", improvement.status(self.ledger)["next_step"]["id"])

    def test_comparison_requires_policy_and_evaluator_but_allows_candidate_and_controller_changes(self):
        previous = {"id": "step", "metric": "accuracy", "observed": 0.5, "target": 1, "direction": "increase"}
        report = {"metrics": {"accuracy": 1}}
        manifest = {"suite": "s", "policy": "p", "evaluator": "e", "candidate": "a", "controller": "c",
                    "assertions": "a-code", "source_span_probe": "probe-code", "store": "store-code",
                    "manifests": "manifest-code", "manifest_probe": "manifest-probe-code",
                    "transforms": "transform-code", "transformation_probe": "transform-probe-code",
                    "graph_views": "view-code", "graph_view_probe": "view-probe-code",
                    "materialization": "materialize-code", "materialization_probe": "materialize-probe-code"}
        for key in ("policy", "evaluator", "assertions", "source_span_probe", "store", "manifests", "manifest_probe", "transforms", "transformation_probe", "graph_views", "graph_view_probe", "materialization", "materialization_probe"):
            outcome = improvement._forecast_result(previous, report, manifest, {**manifest, key: "changed"})
            self.assertEqual("incomparable_contract_change", outcome["status"])
            self.assertEqual([key], outcome["changed_inputs"])
            self.assertNotIn("change", outcome)
            self.assertNotIn("target_met", outcome)
        outcome = improvement._forecast_result(previous, report, manifest,
                                               {**manifest, "candidate": "b", "controller": "new-controller"})
        self.assertEqual("measured", outcome["status"])
        self.assertEqual(0.5, outcome["change"])
        legacy = {key: value for key, value in manifest.items() if key not in {"assertions", "source_span_probe", "store"}}
        outcome = improvement._forecast_result(previous, report, legacy, manifest)
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertEqual(["assertions", "source_span_probe", "store"], outcome["changed_inputs"])
        prior_packet_a = {key: value for key, value in manifest.items() if key not in {"manifests", "manifest_probe"}}
        outcome = improvement._forecast_result(previous, report, prior_packet_a, manifest)
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertEqual(["manifests", "manifest_probe"], outcome["changed_inputs"])
        prior_packet_b1 = {key: value for key, value in manifest.items() if key not in {"transforms", "transformation_probe"}}
        outcome = improvement._forecast_result(previous, report, prior_packet_b1, manifest)
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertEqual(["transforms", "transformation_probe"], outcome["changed_inputs"])
        prior_packet_b2a = {key: value for key, value in manifest.items() if key not in {"graph_views", "graph_view_probe"}}
        outcome = improvement._forecast_result(previous, report, prior_packet_b2a, manifest)
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertEqual(["graph_views", "graph_view_probe"], outcome["changed_inputs"])
        prior_packet_b2b = {key: value for key, value in manifest.items() if key not in {"materialization", "materialization_probe"}}
        outcome = improvement._forecast_result(previous, report, prior_packet_b2b, manifest)
        self.assertEqual("incomparable_contract_change", outcome["status"])
        self.assertEqual(["materialization", "materialization_probe"], outcome["changed_inputs"])

    def test_unauthorized_stage_budget_and_dropped_family_are_refused_before_claim(self):
        original = json.loads(self.policy.read_text())
        variants = [{"stage": "production"}, {"allow_scale_change": True}, {"external_spend": 1},
                    {"max_assessment_seconds": 0}, {"max_assessment_seconds": True}, {"schema_version": True},
                    {"required_families": original["required_families"][:-1]}]
        for change in variants:
            with self.subTest(change=change):
                policy = {**original, **change}
                self.policy.write_text(json.dumps(policy))
                with self.assertRaises(ValueError):
                    self.run_assessment()
                self.assertEqual([], self.ledger.events())

    def test_runtime_failure_preserves_inputs_and_queues_diagnosis(self):
        with patch.object(improvement, "evaluate", side_effect=ValueError("Bad candidate schema")):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertEqual(3 + len(improvement._IMPLEMENTATIONS), len(self.ledger.events("observation")))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
        self.assertEqual(result, self.run_assessment())

    def test_elapsed_budget_violation_is_failure_not_success(self):
        with patch.object(improvement.time, "monotonic", side_effect=[0, 31]):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertIn("budget", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_interrupted_run_and_mixed_or_corrupt_store_cannot_continue(self):
        self.ledger.append("improvement_started", {"run_key": "crashed"})
        with self.assertRaisesRegex(ValueError, "Interrupted"):
            self.run_assessment()
        self.ledger.append("foreign", {})
        with self.assertRaisesRegex(ValueError, "dedicated"):
            improvement.status(self.ledger)
        self.ledger.db.execute("DROP TRIGGER events_no_update")
        self.ledger.db.execute("UPDATE events SET body='{}' WHERE kind='foreign'")
        self.ledger.db.execute("UPDATE events SET recorded_at='2020-01-01T00:00:00Z' WHERE kind='foreign'")
        self.ledger.db.commit()
        with self.assertRaisesRegex(ValueError, "integrity"):
            improvement.status(self.ledger)

    def test_concurrent_workers_cannot_claim_same_successor(self):
        self.run_assessment()
        barrier = threading.Barrier(2)
        results = []
        def worker(key):
            ledger = Ledger(self.store)
            try:
                barrier.wait()
                result = improvement.assess(ledger, self.policy, self.suite, "reference", key,
                    after_step="first:next", completed_work="Concurrent fixture assessment")
                results.append(result["result"])
            except ValueError:
                results.append("refused")
            finally:
                ledger.close()
        threads = [threading.Thread(target=worker, args=(key,)) for key in ("second", "third")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=ASSESSMENT_WAIT_SECONDS)
            self.assertFalse(thread.is_alive(), "Concurrent assessment did not finish within its harness budget")
        self.assertCountEqual(["assessed", "refused"], results)
        self.assertEqual(2, len(self.ledger.events("improvement_completed")))

    def test_locked_claim_rechecks_run_key_after_stale_preflight_read(self):
        self.run_assessment()
        original = improvement._checked_events
        calls = 0
        def stale_once(ledger):
            nonlocal calls
            calls += 1
            return [] if calls == 1 else original(ledger)
        with patch.object(improvement, "_checked_events", side_effect=stale_once):
            with self.assertRaisesRegex(ValueError, "already claimed"):
                self.run_assessment(run_key="first", after="first:next", work="Stale worker reuses key")
        self.assertEqual(1, len(self.ledger.events("improvement_started")))
        self.assertEqual(1, len(self.ledger.events("improvement_completed")))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])

    def test_metric_priority_does_not_hide_weak_family_in_average(self):
        report = {"metrics": {"temporal_violations": 0, "provenance": 1, "coverage": 1,
                              "worst_family_accuracy": 0.5, "accuracy": 0.98},
                  "families": {"organization": {"accuracy": 1}, "collective": {"accuracy": 0.5}}}
        decision = improvement.select_next(report, "case")
        self.assertEqual("repair_weakest_entity_family", decision["action"])
        self.assertEqual("collective", decision["family"])
        report["metrics"]["temporal_violations"] = 1
        self.assertEqual("repair_time_eligibility", improvement.select_next(report, "case")["action"])

    def test_real_probe_failure_blocks_packet_b_despite_perfect_candidate_answers(self):
        with patch.object(assertions, "resolve_span", return_value=b"wrong bytes"):
            result = self.run_assessment()
        self.assertEqual(1, result["report"]["metrics"]["accuracy"])
        self.assertLess(result["report"]["metrics"]["source_span_resolution"], 1)
        self.assertEqual("repair_source_span_assertions", result["next_step"]["action"])
        failures = [row for row in result["report"]["source_span_checks"]["checks"] if not row["passed"]]
        self.assertTrue(failures)
        self.assertTrue(all("diagnostic" in row for row in failures))

    def test_history_probe_failure_blocks_packet_b(self):
        with patch.object(assertions, "assertions_as_of", return_value=[]):
            result = self.run_assessment()
        self.assertEqual(1, result["report"]["metrics"]["source_span_resolution"])
        self.assertLess(result["report"]["metrics"]["assertion_history_preservation"], 1)
        self.assertEqual("repair_source_span_assertions", result["next_step"]["action"])
        self.assertEqual("assertion_history_preservation", result["next_step"]["metric"])

    def test_actual_manifest_failure_blocks_b2_even_with_perfect_candidate_and_assertion_checks(self):
        with patch.object(manifests, "forecast_manifest", side_effect=ValueError("Broken forecast binding")):
            result = self.run_assessment()
        self.assertEqual("assessed", result["result"])
        self.assertEqual(1, result["report"]["metrics"]["accuracy"])
        self.assertEqual(1, result["report"]["metrics"]["source_span_resolution"])
        self.assertEqual(1, result["report"]["metrics"]["assertion_history_preservation"])
        self.assertLess(result["report"]["metrics"]["representation_manifest_preservation"], 1)
        self.assertEqual("repair_representation_manifests", result["next_step"]["action"])
        failures = [row for row in result["report"]["manifest_checks"]["checks"] if not row["passed"]]
        self.assertTrue(failures)
        self.assertTrue(all("diagnostic" in row for row in failures))

    def test_broken_manifest_probe_records_failure_and_never_advances(self):
        with patch.object(improvement, "run_manifest_checks", side_effect=ValueError("Probe interrupted")):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertIn("Probe interrupted", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_selector_requires_all_prior_and_materialization_metrics_before_retrieval(self):
        result = self.run_assessment()
        report = result["report"]
        cases = [("temporal_violations", 1, "repair_time_eligibility"),
                 ("provenance", 0.9, "repair_evidence_mapping"),
                 ("coverage", 0.9, "cover_missing_answers"),
                 ("worst_family_accuracy", 0.9, "repair_weakest_entity_family"),
                 ("source_span_resolution", 0.9, "repair_source_span_assertions"),
                 ("assertion_history_preservation", 0.9, "repair_source_span_assertions"),
                 ("representation_manifest_preservation", 0.9, "repair_representation_manifests"),
                 ("transformation_preservation", 0.9, "repair_graph_transformations"),
                 ("split_merge_preservation", 0.9, "repair_graph_views"),
                 ("output_manifest_materialization", 0.9, "repair_transform_materialization")]
        for metric, value, action in cases:
            with self.subTest(metric=metric):
                changed = copy.deepcopy(report)
                changed["metrics"][metric] = value
                self.assertEqual(action, improvement.select_next(changed, "gate")["action"])
        missing = copy.deepcopy(report)
        del missing["metrics"]["representation_manifest_preservation"]
        self.assertEqual("repair_representation_manifests", improvement.select_next(missing, "legacy")["action"])
        missing_transform = copy.deepcopy(report)
        del missing_transform["metrics"]["transformation_preservation"]
        self.assertEqual("repair_graph_transformations", improvement.select_next(missing_transform, "pre-transform")["action"])
        missing_views = copy.deepcopy(report)
        del missing_views["metrics"]["split_merge_preservation"]
        self.assertEqual("repair_graph_views", improvement.select_next(missing_views, "pre-views")["action"])
        missing_materialization = copy.deepcopy(report)
        del missing_materialization["metrics"]["output_manifest_materialization"]
        self.assertEqual("repair_transform_materialization", improvement.select_next(missing_materialization, "pre-materialization")["action"])

    def test_broken_transformation_probe_records_failure_without_advancing(self):
        with patch.object(improvement, "run_transformation_checks", side_effect=ValueError("Transform probe interrupted")):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertIn("Transform probe interrupted", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_transform_execution_failure_blocks_b2b_with_prior_capabilities_passing(self):
        with patch.object(transforms, "execute_graph_transform", side_effect=ValueError("Transform execution broken")):
            result = self.run_assessment()
        self.assertEqual("assessed", result["result"])
        for metric in ("accuracy", "source_span_resolution", "assertion_history_preservation", "representation_manifest_preservation"):
            self.assertEqual(1, result["report"]["metrics"][metric])
        self.assertEqual(0, result["report"]["metrics"]["transformation_preservation"])
        self.assertEqual("repair_graph_transformations", result["next_step"]["action"])
        self.assertTrue(all("diagnostic" in row for row in result["report"]["transformation_checks"]["checks"]))

    def test_broken_graph_view_probe_records_failure_without_advancing(self):
        with patch.object(improvement, "run_graph_view_checks", side_effect=ValueError("Graph view probe interrupted")):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertIn("Graph view probe interrupted", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_graph_view_execution_failure_blocks_materialization_with_prior_gates_passing(self):
        with patch.object(graph_views, "execute_graph_views", side_effect=ValueError("Graph views unavailable")):
            result = self.run_assessment()
        self.assertEqual("assessed", result["result"])
        for metric in ("accuracy", "source_span_resolution", "assertion_history_preservation", "representation_manifest_preservation", "transformation_preservation"):
            self.assertEqual(1, result["report"]["metrics"][metric])
        self.assertEqual(0, result["report"]["metrics"]["split_merge_preservation"])
        self.assertEqual("repair_graph_views", result["next_step"]["action"])
        self.assertTrue(all("diagnostic" in row for row in result["report"]["graph_view_checks"]["checks"]))

    def test_broken_materialization_probe_records_failure_without_advancing(self):
        with patch.object(improvement, "run_materialization_checks", side_effect=ValueError("Materialization probe interrupted")):
            result = self.run_assessment()
        self.assertEqual("failed", result["result"])
        self.assertEqual("diagnose_failed_assessment", result["next_step"]["action"])
        self.assertIn("Materialization probe interrupted", result["message"])
        self.assertEqual([], self.ledger.events("improvement_completed"))

    def test_materialization_failure_blocks_retrieval_with_prior_gates_passing(self):
        with patch.object(materialization, "materialize_graph_outputs", side_effect=ValueError("Materialization unavailable")):
            result = self.run_assessment()
        self.assertEqual("assessed", result["result"])
        for metric in ("accuracy", "source_span_resolution", "assertion_history_preservation", "representation_manifest_preservation", "transformation_preservation", "split_merge_preservation"):
            self.assertEqual(1, result["report"]["metrics"][metric])
        self.assertEqual(0, result["report"]["metrics"]["output_manifest_materialization"])
        self.assertEqual("repair_transform_materialization", result["next_step"]["action"])
        self.assertTrue(all("diagnostic" in row for row in result["report"]["materialization_checks"]["checks"]))

    def _isolated_drift_check(self, mode, module_name="assertions", dependent_name=""):
        package_root = self.root / f"isolated-{mode}-{module_name}-{dependent_name}"
        shutil.copytree(Path(improvement.__file__).parent, package_root / "epiphysics",
                        ignore=shutil.ignore_patterns("__pycache__"))
        code = r'''
import ast,importlib,json,sys
from pathlib import Path
mode,name,dependent_name,policy,suite,store_path=sys.argv[1:]
def alter(module):
    path=Path(module.__file__)
    if module.__name__.endswith('.store'):
        source=path.read_bytes()
        tree=ast.parse(source)
        ledger=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Ledger')
        snapshot=next(node for node in ledger.body if isinstance(node,ast.FunctionDef) and node.name=='snapshot')
        first=snapshot.body[0]
        lines=source.splitlines(keepends=True)
        lines.insert(first.lineno-1,b' '*first.col_offset+b'raise ValueError("Changed snapshot is broken")\n')
        path.write_bytes(b''.join(lines))
        return
    functions={'assertions':'resolve_span','representation_checks':'evaluate','source_span_checks':'run_source_span_checks',
               'manifests':'register_manifest','manifest_checks':'run_manifest_checks',
               'transforms':'execute_graph_transform','transformation_checks':'run_transformation_checks',
               'graph_views':'execute_graph_views','graph_view_checks':'run_graph_view_checks',
               'materialization':'materialize_graph_outputs','materialization_checks':'run_materialization_checks',
               'retrieval':'run_lexical_retrieval','retrieval_evaluation':'evaluate_retrieval',
               'retrieval_contracts':'get_retrieval_run','retrieval_indexing':'project_index','retrieval_coverage':'get_coverage_freeze',
               'retrieval_assessment':'assess_prepared_retrieval_study'}
    function=functions.get(module.__name__.rsplit('.',1)[-1])
    change=(("\ndef "+function+"(*args, **kwargs):\n    raise ValueError('Changed implementation on disk')\n").encode()
            if function else b"\n# Unreviewed source edit after import\n")
    path.write_bytes(path.read_bytes()+change)
if mode == 'dependency_before_controller':
    dependency=importlib.import_module('epiphysics.'+name)
    alter(dependency)
if mode == 'dependency_reload_before_controller':
    dependent=importlib.import_module('epiphysics.'+dependent_name)
    dependency=importlib.import_module('epiphysics.'+name)
    old_dependency_code=dependency.IMPLEMENTATION_CODE
    alter(dependency)
    importlib.reload(dependency)
    if dependent_name in {'source_span_checks','manifests','manifest_checks'} and name == 'store':
        # Refresh earlier dependencies so the intended dependent retains the first stale edge.
        importlib.reload(importlib.import_module('epiphysics.assertions'))
        if dependent_name == 'manifest_checks':
            importlib.reload(importlib.import_module('epiphysics.manifests'))
    if dependent_name in {'transforms','transformation_checks'}:
        if name == 'store':
            importlib.reload(importlib.import_module('epiphysics.assertions'))
        if name in {'store','assertions'}:
            importlib.reload(importlib.import_module('epiphysics.manifests'))
        if dependent_name == 'transformation_checks' and name in {'store','assertions','manifests'}:
            importlib.reload(importlib.import_module('epiphysics.transforms'))
    if dependent_name in {'graph_views','graph_view_checks'}:
        if name == 'store':
            importlib.reload(importlib.import_module('epiphysics.assertions'))
        if name in {'store','assertions'}:
            importlib.reload(importlib.import_module('epiphysics.manifests'))
        if name in {'store','assertions','manifests'}:
            importlib.reload(importlib.import_module('epiphysics.transforms'))
        if dependent_name == 'graph_view_checks' and name in {'store','assertions','manifests','transforms'}:
            importlib.reload(importlib.import_module('epiphysics.graph_views'))
    if dependent_name in {'materialization','materialization_checks'}:
        if name == 'store':
            importlib.reload(importlib.import_module('epiphysics.assertions'))
        if name in {'store','assertions'}:
            importlib.reload(importlib.import_module('epiphysics.manifests'))
        if name in {'store','assertions','manifests'}:
            importlib.reload(importlib.import_module('epiphysics.transforms'))
        if name in {'store','assertions','manifests','transforms'}:
            importlib.reload(importlib.import_module('epiphysics.graph_views'))
        if dependent_name == 'materialization_checks' and name in {'store','assertions','manifests','transforms','graph_views'}:
            importlib.reload(importlib.import_module('epiphysics.materialization'))
from epiphysics import improvement
from epiphysics.store import Ledger,digest
module=importlib.import_module('epiphysics.'+name)
captured=module.IMPLEMENTATION_SOURCE
assessment_callable=improvement.assess
if mode == 'before_assessment':
    alter(module)
if mode == 'during_probe':
    original=improvement.run_source_span_checks
    def changing_probe():
        report=original()
        alter(module)
        return report
    improvement.run_source_span_checks=changing_probe
if mode == 'reload_after_controller':
    alter(module)
    importlib.reload(module)
if mode == 'reload_controller_stale_alias':
    importlib.reload(improvement)
ledger=Ledger(store_path)
if mode == 'reload_with_stale_ledger':
    importlib.reload(importlib.import_module('epiphysics.store'))
    importlib.reload(improvement)
    assessment_callable=improvement.assess
try:
    try:
        result=assessment_callable(ledger,policy,suite,'reference','drift',completed_work='Isolated drift regression')
        outcome={'result':result['result'],'message':result.get('message'),
                 'next_action':result['next_step']['action'],'manifest':result['request']['manifest']}
    except ValueError as error:
        outcome={'result':'refused','message':str(error)}
    outcome.update(events=[event['kind'] for event in ledger.events()],
                   captured_sha256=digest(captured),disk_sha256=digest(Path(module.__file__).read_bytes()))
    if mode == 'reload_after_controller':
        function={'representation_checks':'evaluate','source_span_checks':'run_source_span_checks','manifest_checks':'run_manifest_checks',
                  'transformation_checks':'run_transformation_checks','graph_view_checks':'run_graph_view_checks','materialization_checks':'run_materialization_checks'}[name]
        outcome['alias_is_current']=getattr(improvement,function) is getattr(module,function)
    if mode == 'dependency_reload_before_controller':
        outcome['dependency_code_changed']=old_dependency_code is not dependency.IMPLEMENTATION_CODE
        outcome['dependency_source_matches_disk']=dependency.IMPLEMENTATION_SOURCE == Path(dependency.__file__).read_bytes()
    print(json.dumps(outcome))
finally:
    ledger.close()
'''
        environment = {**os.environ, "PYTHONPATH": str(package_root), "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, "-s", "-c", code, mode, module_name, dependent_name,
                                 str(self.policy), str(self.suite), str(package_root / "ledger")],
                                cwd=package_root, env=environment, capture_output=True, text=True,
                                timeout=ASSESSMENT_WAIT_SECONDS if mode == "during_probe" else 10)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_preassessment_disk_drift_is_refused_without_claiming_queue(self):
        for module in ("assertions", "source_span_checks", "representation_checks", "store", "improvement", "manifests", "manifest_checks", "transforms", "transformation_checks", "graph_views", "graph_view_checks", "materialization", "materialization_checks", "retrieval", "retrieval_evaluation", "retrieval_assessment", "retrieval_contracts", "retrieval_indexing", "retrieval_coverage"):
            with self.subTest(module=module):
                outcome = self._isolated_drift_check("before_assessment", module)
                self.assertEqual("refused", outcome["result"])
                self.assertIn("changed since import", outcome["message"])
                self.assertEqual([], outcome["events"])
                self.assertNotEqual(outcome["captured_sha256"], outcome["disk_sha256"])

    def test_all_pinned_source_reads_are_bounded_and_oversize_refuses_before_open(self):
        pinned = improvement._IMPLEMENTATIONS
        expected_lengths = {path: len(source) + 1 for _, path, source, _, _ in pinned.values()}
        original_open, original_read = Path.open, Path.read_bytes
        reads = {}
        class LimitedReader:
            def __init__(self, path, stream):
                self.path, self.stream = path, stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def read(self, size=-1):
                if size != expected_lengths[self.path]:
                    raise AssertionError("Pinned source read must be bounded by retained size")
                reads[self.path] = size
                return self.stream.read(size)
        def bounded_open(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            return LimitedReader(path, stream) if path in expected_lengths else stream
        with patch.object(Path, "open", bounded_open):
            self.assertEqual(set(pinned), set(improvement._implementation_inputs()))
        self.assertEqual(expected_lengths, reads)
        oversized = self.root / "changed-module.py"
        with oversized.open("wb") as stream:
            stream.truncate(32_000_000)
        def guarded_open(path, *args, **kwargs):
            if path == oversized:
                raise AssertionError("Oversized source must not be opened")
            return original_open(path, *args, **kwargs)
        def guarded_read(path):
            if path == oversized:
                raise AssertionError("Oversized source must not be read")
            return original_read(path)
        for name, (module, _, source, code, dependencies) in pinned.items():
            changed = {**pinned, name: (module, oversized, source, code, dependencies)}
            with self.subTest(module=name), patch.object(improvement, "_IMPLEMENTATIONS", changed):
                with patch.object(Path, "open", guarded_open), patch.object(Path, "read_bytes", guarded_read):
                    with self.assertRaisesRegex(ValueError, "source changed since import: " + name):
                        improvement._implementation_inputs()

    def test_dependency_imported_before_controller_retains_its_original_source_identity(self):
        outcome = self._isolated_drift_check("dependency_before_controller")
        self.assertEqual("refused", outcome["result"])
        self.assertIn("assertions", outcome["message"])
        self.assertEqual([], outcome["events"])

    def test_source_drift_during_probe_fails_claimed_step_without_promotion(self):
        outcome = self._isolated_drift_check("during_probe")
        self.assertEqual("failed", outcome["result"])
        self.assertEqual("diagnose_failed_assessment", outcome["next_action"])
        self.assertIn("changed since import", outcome["message"])
        self.assertEqual(1, outcome["events"].count("improvement_started"))
        self.assertEqual(1, outcome["events"].count("improvement_failed"))
        self.assertNotIn("improvement_completed", outcome["events"])
        self.assertEqual(outcome["captured_sha256"], outcome["manifest"]["assertions"])
        self.assertNotEqual(outcome["disk_sha256"], outcome["manifest"]["assertions"])

    def test_hot_reload_cannot_pair_new_source_with_old_controller_alias(self):
        outcome = self._isolated_drift_check("reload_after_controller", "representation_checks")
        self.assertFalse(outcome["alias_is_current"])
        self.assertEqual("refused", outcome["result"])
        self.assertIn("reloaded since controller import", outcome["message"])
        self.assertEqual([], outcome["events"])

    def test_transitive_dependency_reload_before_controller_refuses_stale_import_graph(self):
        for dependent, dependency, label in (
            ("assertions", "store", "assertions"),
            ("representation_checks", "store", "evaluator"),
            ("source_span_checks", "store", "source_span_probe"),
            ("source_span_checks", "assertions", "source_span_probe"),
            ("manifests", "store", "manifests"),
            ("manifests", "assertions", "manifests"),
            ("manifest_checks", "store", "manifest_probe"),
            ("manifest_checks", "manifests", "manifest_probe"),
            ("transforms", "store", "transforms"),
            ("transforms", "assertions", "transforms"),
            ("transforms", "manifests", "transforms"),
            ("transformation_checks", "store", "transformation_probe"),
            ("transformation_checks", "assertions", "transformation_probe"),
            ("transformation_checks", "manifests", "transformation_probe"),
            ("transformation_checks", "transforms", "transformation_probe"),
            ("graph_views", "store", "graph_views"),
            ("graph_views", "assertions", "graph_views"),
            ("graph_views", "manifests", "graph_views"),
            ("graph_views", "transforms", "graph_views"),
            ("graph_view_checks", "store", "graph_view_probe"),
            ("graph_view_checks", "assertions", "graph_view_probe"),
            ("graph_view_checks", "manifests", "graph_view_probe"),
            ("graph_view_checks", "transforms", "graph_view_probe"),
            ("graph_view_checks", "graph_views", "graph_view_probe"),
            ("materialization", "store", "materialization"),
            ("materialization", "assertions", "materialization"),
            ("materialization", "manifests", "materialization"),
            ("materialization", "transforms", "materialization"),
            ("materialization", "graph_views", "materialization"),
            ("materialization_checks", "store", "materialization_probe"),
            ("materialization_checks", "assertions", "materialization_probe"),
            ("materialization_checks", "manifests", "materialization_probe"),
            ("materialization_checks", "transforms", "materialization_probe"),
            ("materialization_checks", "graph_views", "materialization_probe"),
            ("materialization_checks", "materialization", "materialization_probe"),
        ):
            with self.subTest(dependent=dependent, dependency=dependency):
                outcome = self._isolated_drift_check("dependency_reload_before_controller", dependency, dependent)
                self.assertTrue(outcome["dependency_code_changed"])
                self.assertTrue(outcome["dependency_source_matches_disk"])
                self.assertEqual("refused", outcome["result"])
                self.assertIn(f"Implementation dependency reloaded: {label} -> epiphysics.{dependency};", outcome["message"])
                self.assertEqual([], outcome["events"])

    def test_probe_reload_after_controller_refuses_stale_probe_alias(self):
        for module in ("source_span_checks", "manifest_checks", "transformation_checks", "graph_view_checks", "materialization_checks"):
            with self.subTest(module=module):
                outcome = self._isolated_drift_check("reload_after_controller", module)
                self.assertFalse(outcome["alias_is_current"])
                self.assertEqual("refused", outcome["result"])
                self.assertIn("reloaded since controller import", outcome["message"])
                self.assertEqual([], outcome["events"])

    def test_stale_assessment_alias_is_refused_after_controller_reload(self):
        outcome = self._isolated_drift_check("reload_controller_stale_alias", "improvement")
        self.assertEqual("refused", outcome["result"])
        self.assertIn("Stale assessment callable", outcome["message"])
        self.assertEqual([], outcome["events"])

    def test_old_ledger_instance_is_refused_after_store_and_controller_reload(self):
        outcome = self._isolated_drift_check("reload_with_stale_ledger", "improvement")
        self.assertEqual("refused", outcome["result"])
        self.assertIn("Stale or unsupported ledger class", outcome["message"])
        self.assertEqual([], outcome["events"])

    def test_timestamp_valid_stale_bytecode_is_rejected(self):
        package_root = self.root / "isolated-stale-bytecode"
        shutil.copytree(Path(improvement.__file__).parent, package_root / "epiphysics",
                        ignore=shutil.ignore_patterns("__pycache__"))
        code = r'''
import json,os,py_compile,sys
from pathlib import Path
policy,suite,store_path=sys.argv[1:]
path=Path('epiphysics/assertions.py').resolve()
stat=path.stat()
original=path.read_bytes()
assert b'MAX_SPANS = 100' in original
py_compile.compile(str(path),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
changed=original.replace(b'MAX_SPANS = 100',b'MAX_SPANS = 101',1)
assert len(changed)==len(original)
path.write_bytes(changed)
os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
from epiphysics import improvement,assertions
from epiphysics.store import Ledger
ledger=Ledger(store_path)
try:
    try:
        improvement.assess(ledger,policy,suite,'reference','stale-cache',completed_work='Test cached bytecode identity')
        outcome={'result':'unexpected_success'}
    except ValueError as error:
        outcome={'result':'refused','message':str(error)}
    outcome.update(loaded_limit=assertions.MAX_SPANS,captured_is_disk=assertions.IMPLEMENTATION_SOURCE==changed,
                   size_unchanged=path.stat().st_size==stat.st_size,mtime_unchanged=path.stat().st_mtime_ns==stat.st_mtime_ns,
                   events=[event['kind'] for event in ledger.events()])
    print(json.dumps(outcome))
finally:
    ledger.close()
'''
        environment = {**os.environ, "PYTHONPATH": str(package_root), "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, "-s", "-c", code, str(self.policy), str(self.suite), str(package_root / "ledger")],
                                cwd=package_root, env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        outcome = json.loads(result.stdout)
        self.assertEqual(100, outcome["loaded_limit"])
        self.assertTrue(outcome["captured_is_disk"])
        self.assertTrue(outcome["size_unchanged"])
        self.assertTrue(outcome["mtime_unchanged"])
        self.assertEqual("refused", outcome["result"])
        self.assertIn("does not match source: assertions", outcome["message"])
        self.assertEqual([], outcome["events"])

    def test_real_dispatch_executes_fixed_program_and_preserves_receipts(self):
        result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "spawned",
                                      completed_work="Execute a synthetic oracle control", timeout_seconds=ASSESSMENT_WAIT_SECONDS)
        self.assertEqual("assessed", result["result"], result["dispatch"])
        receipt = result["dispatch"]
        directory = Path(receipt["receipt_directory"])
        self.assertEqual("epiphysics.improvement assess", receipt["program"])
        self.assertNotEqual(os.getpid(), receipt["pid"])
        self.assertEqual(0, receipt["returncode"])
        self.assertTrue((directory / "start.json").is_file())
        self.assertTrue((directory / "finish.json").is_file())
        self.assertLessEqual((directory / "output.log").stat().st_size, improvement.MAX_BYTES)
        self.assertEqual("spawned:next", improvement.status(self.ledger)["next_step"]["id"])
        claim = self.ledger.events("improvement_started")[0]["body"]
        self.assertEqual(receipt["dispatch_id"], claim["worker"]["dispatch_id"])
        self.assertEqual(receipt["pid"], claim["worker"]["pid"])
        count = len(self.ledger.events())
        replay = improvement.dispatch(self.store, self.policy, self.suite, "reference", "spawned",
                                      completed_work="Execute a synthetic oracle control", timeout_seconds=ASSESSMENT_WAIT_SECONDS)
        self.assertEqual("assessed", replay["result"])
        self.assertEqual(count, len(self.ledger.events()))

    def test_real_hard_timeout_reaps_child_and_queues_owned_diagnosis(self):
        real_popen = subprocess.Popen
        code = """import os,time
from epiphysics.store import Ledger
ledger=Ledger(os.environ['TEST_STORE'])
ledger.append('improvement_started', {'run_key':'timed','request':{'after_step':'initial'},
 'claimed_step':{'id':'initial'},'worker':{'dispatch_id':os.environ['EPIPHYSICS_DISPATCH_ID'],'pid':os.getpid()}})
ledger.close()
print('owned claim made',flush=True)
time.sleep(30)
"""
        def slow_worker(arguments, **kwargs):
            kwargs["env"]["TEST_STORE"] = str(self.store)
            return real_popen([arguments[0], "-c", code], **kwargs)
        with patch.object(improvement.subprocess, "Popen", side_effect=slow_worker):
            result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "timed",
                                          completed_work="Timeout fixture", timeout_seconds=1)
        self.assertEqual("failed", result["result"])
        self.assertEqual("timeout", result["dispatch"]["termination"])
        self.assertEqual("diagnosis_queued", result["dispatch"]["recovery"])
        self.assertEqual("timed:diagnose", improvement.status(self.ledger)["next_step"]["id"])
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
        with self.assertRaises(ChildProcessError):
            os.waitpid(result["dispatch"]["pid"], os.WNOHANG)

    def test_output_limit_reaps_worker_without_inventing_a_claim(self):
        real_popen = subprocess.Popen
        def noisy_worker(arguments, **kwargs):
            return real_popen([arguments[0], "-c", "import sys,time;sys.stdout.write('x'*1100000);sys.stdout.flush();time.sleep(30)"], **kwargs)
        with patch.object(improvement.subprocess, "Popen", side_effect=noisy_worker):
            result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "noisy",
                                          completed_work="Output-limit fixture", timeout_seconds=10)
        self.assertEqual("failed", result["result"])
        self.assertEqual("output_limit", result["dispatch"]["termination"])
        self.assertEqual(improvement.MAX_BYTES, result["dispatch"]["output_bytes"])
        self.assertEqual("no_owned_claim", result["dispatch"]["recovery"])
        self.assertEqual([], self.ledger.events())

    def test_completed_large_assessment_survives_failed_output_delivery(self):
        original = json.loads(self.suite.read_text())
        suite = {"schema_version": 1, "cases": []}
        for i in range(100):
            case = copy.deepcopy(original["cases"][i % len(original["cases"])] )
            case["id"] = f"large-case-{i}"
            checks = case["checks"]
            case["checks"] = [{**copy.deepcopy(checks[j % len(checks)]), "id": f"check-{j}"} for j in range(30)]
            suite["cases"].append(case)
        self.suite.write_text(json.dumps(suite))
        self.assertLess(self.suite.stat().st_size, improvement.MAX_BYTES)
        result = improvement.dispatch(self.store, self.policy, self.suite, "reference", "large",
                                      completed_work="Exercise bounded delivery after a completed assessment", timeout_seconds=ASSESSMENT_WAIT_SECONDS)
        self.assertEqual("assessment_completed_delivery_failed", result["result"])
        self.assertEqual("output_limit", result["dispatch"]["termination"])
        self.assertEqual("completed", result["dispatch"]["assessment_status"])
        self.assertEqual("failed", result["dispatch"]["delivery_status"])
        self.assertEqual("already_finished", result["dispatch"]["recovery"])
        self.assertEqual("improvement:large:complete", result["dispatch"]["authoritative_transition_id"])
        self.assertIsNone(result["assessment"])
        self.assertEqual("large:next", result["authoritative_transition"]["next_step"]["id"])
        self.assertLess(len(json.dumps(result)), 20000)
        self.assertEqual(1, len(self.ledger.events("improvement_completed")))
        self.assertEqual([], self.ledger.events("improvement_failed"))
        self.assertEqual([], improvement.status(self.ledger)["unfinished_runs"])
        count = len(self.ledger.events())
        replay = improvement.dispatch(self.store, self.policy, self.suite, "reference", "large",
                                      completed_work="Exercise bounded delivery after a completed assessment", timeout_seconds=ASSESSMENT_WAIT_SECONDS)
        self.assertEqual("assessment_completed_delivery_failed", replay["result"])
        self.assertEqual("improvement:large:complete", replay["dispatch"]["authoritative_transition_id"])
        self.assertEqual(count, len(self.ledger.events()))
        mismatched = improvement.dispatch(self.store, self.policy, self.suite, "degraded", "large",
                                         completed_work="Exercise bounded delivery after a completed assessment", timeout_seconds=10)
        self.assertEqual("failed", mismatched["result"])
        self.assertEqual("not_confirmed", mismatched["dispatch"]["assessment_status"])
        self.assertIsNone(mismatched["dispatch"]["authoritative_transition_id"])
        self.assertEqual(count, len(self.ledger.events()))

    def test_recovery_cannot_close_another_worker_or_overwrite_completion(self):
        result = self.run_assessment()
        count = len(self.ledger.events())
        self.assertEqual("no_owned_claim", improvement._recover_reaped_dispatch(
            self.store, "first", "someone-else", 123, "timeout"))
        self.assertEqual(count, len(self.ledger.events()))
        self.assertEqual(result["next_step"], improvement.status(self.ledger)["next_step"])
        self.ledger.append("improvement_started", {"run_key": "owned", "request": {},
            "worker": {"dispatch_id": "mine", "pid": 456}})
        self.ledger.append("improvement_completed", {"run_key": "owned", "next_step": {"id": "done"}})
        count = len(self.ledger.events())
        self.assertEqual("already_finished", improvement._recover_reaped_dispatch(
            self.store, "owned", "mine", 456, "timeout"))
        self.assertEqual(count, len(self.ledger.events()))

    def test_invalid_dispatch_budget_is_refused(self):
        for timeout in (0, -1, 61, float("inf"), float("nan"), True):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    improvement.dispatch(self.store, self.policy, self.suite, "reference", "bad",
                                         completed_work="Invalid timeout", timeout_seconds=timeout)
        self.assertFalse((self.store / "dispatches").exists())


if __name__ == "__main__":
    unittest.main()
