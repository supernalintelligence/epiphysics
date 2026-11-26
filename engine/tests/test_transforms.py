from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from epiphysics import assertions, manifests, store, transforms
from epiphysics.store import Ledger, canonical, digest


class GraphTransformTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(Path(self.temp.name) / "ledger", clock=lambda: self.now)
        self.evidence = {name: self.capture(f"evidence-{name}", f"Synthetic evidence {name}".encode()) for name in ("a", "b", "c", "shared")}
        self.artifacts = {role: self.capture(role, f"Declared parent {role}".encode())["id"] for role in manifests.ARTIFACT_ROLES}
        self.code = self.capture("transform-code", transforms.IMPLEMENTATION_SOURCE)
        self.dependencies = {module.__name__: self.capture(module.__name__, module.IMPLEMENTATION_SOURCE)["id"]
                             for module in (store, assertions, manifests)}
        self.identity = self.recipe("identity", {})
        self.projection = self.recipe("project_entities", {"entity_ids": ["a", "b"]})
        self.model = {"entities": [
            self.entity("c", "c", {"unit": "EUR", "value": 7}),
            self.entity("a", "a", {"unit": "USD", "value": 12}),
            self.entity("b", "b", {"unit": "hour", "value": 2})],
            "relations": [
                self.edge("a", "c", "owes", "c", id="removed-edge", amount={"value": 7, "unit": "EUR"}),
                self.edge("a", "b", "depends_on", "shared", qualifiers={"scope": "invoices"}),
                self.edge("b", "a", "depends_on", "shared"),
                self.edge("a", "b", "pays", "shared", amount={"value": 12, "unit": "USD"}),
                self.edge("a", "a", "monitors", "a")],
            "metadata": {"synthetic": True, "description": "Preserve this context verbatim", "evidence_ids": [self.evidence["shared"]["id"]]}}
        self.parent = self.parent_for()

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def capture(self, name, raw):
        return self.ledger.capture(f"synthetic:{name}", raw)

    def entity(self, eid, evidence, attributes):
        return {"id": eid, "basis": "reported", "evidence_ids": [self.evidence[evidence]["id"]], "attributes": attributes}

    def edge(self, source, target, kind, evidence, **attributes):
        return {"source": source, "target": target, "type": kind, "basis": "reported",
                "evidence_ids": [self.evidence[evidence]["id"]], **attributes}

    def recipe(self, operation, config, **changes):
        config_observation = self.capture("transform-config", canonical(config).encode())
        body = {"schema_version": 1, "operation": operation, "config_observation_id": config_observation["id"],
                "implementation_observation_id": self.code["id"], "implementation_sha256": digest(transforms.IMPLEMENTATION_SOURCE),
                "dependency_observations": deepcopy(self.dependencies), "output_schema": transforms.OUTPUT_SCHEMA, **changes}
        return self.capture("transform-recipe", canonical(body).encode())

    def parent_for(self, model=None, *, encoding="directed-graph", schema_id=transforms.OUTPUT_SCHEMA, raw=False):
        model = deepcopy(self.model if model is None else model)
        snapshot = self.ledger.snapshot()
        if raw:
            representation = self.ledger.append("representation", {"snapshot_id": snapshot["id"], "observer": "synthetic-observer",
                "method": "declared-parent-constructor", "parent": None, "model": model})
        else:
            representation = self.ledger.representation(snapshot["id"], model, observer="synthetic-observer", method="declared-parent-constructor")
        return manifests.register_manifest(self.ledger, representation["id"], encoding=encoding, schema_id=schema_id,
            artifacts=self.artifacts, task={"id": "synthetic-invoice", "family": "contract_obligation", "outcome_type": "binary"},
            horizon_seconds=600, units={"invoice": "USD"}, evidence_ids=sorted(manifests._model_evidence(model)), construction_cost=None)

    def execute(self, recipe=None, *, parent=None, key="run"):
        return transforms.execute_graph_transform(self.ledger, (parent or self.parent)["id"],
                                                 (recipe or self.identity)["id"], run_key=key)

    def assert_rejected(self, recipe=None, *, parent=None, key="rejected", diagnostic=None):
        before = len(self.ledger.events())
        result = self.execute(recipe, parent=parent, key=key)
        self.assertEqual(result["kind"], "graph_transform_rejected", result)
        self.assertEqual(result["body"]["result"], "rejected")
        self.assertEqual(len(self.ledger.events()), before + 2)
        self.assertLessEqual(len(result["body"]["error"]["message"]), 400)
        if diagnostic:
            self.assertIn(diagnostic, result["body"]["error"]["message"])
        return result

    def test_identity_executes_canonical_exact_copy_and_no_losses(self):
        before = self.ledger.events()
        result = self.execute()
        body = result["body"]
        self.assertEqual(result["kind"], "graph_transform_completed", result)
        self.assertEqual(canonical(body["output_model"]), canonical(self.model))
        self.assertTrue(body["canonical_exact"])
        self.assertEqual(body["losses"], {"removed_entities": [], "removed_relations": [], "removed_evidence_ids": []})
        self.assertEqual(body["output_model_hash"], digest(canonical(self.model).encode()))
        self.assertEqual(body["source_to_output"]["entities"], {"c": "c", "a": "a", "b": "b"})
        self.assertTrue(all(row["source_key"] == row["output_key"] for row in body["source_to_output"]["relations"]))
        self.assertEqual(body["resources"], {"model_calls": 0, "external_spend": 0})
        self.assertEqual(self.ledger.events()[:len(before)], before)
        self.assertEqual([event["kind"] for event in self.ledger.events()[len(before):]],
                         ["graph_transform_started", "graph_transform_completed"])
        self.assertEqual(len(self.ledger.events("representation")), 1)
        self.assertEqual(len(self.ledger.events("representation_manifest")), 1)

    def test_projection_retains_induced_cycles_self_loops_parallel_types_and_attributes(self):
        result = self.execute(self.projection)
        self.assertEqual(result["kind"], "graph_transform_completed", result)
        output = result["body"]["output_model"]
        self.assertEqual(output["entities"], self.model["entities"][1:])
        self.assertEqual(output["relations"], self.model["relations"][1:])
        self.assertEqual(output["metadata"], self.model["metadata"])
        triples = {(edge["source"], edge["target"], edge["type"]) for edge in output["relations"]}
        self.assertEqual(triples, {("a", "b", "depends_on"), ("b", "a", "depends_on"), ("a", "b", "pays"), ("a", "a", "monitors")})
        self.assertFalse(result["body"]["canonical_exact"])

    def test_projection_loss_records_are_complete_and_maps_do_not_use_list_indices(self):
        result = self.execute(self.projection)
        body = result["body"]
        self.assertEqual(body["losses"]["removed_entities"], self.model["entities"][:1])
        self.assertEqual(body["losses"]["removed_relations"], self.model["relations"][:1])
        self.assertEqual(body["losses"]["removed_evidence_ids"], [self.evidence["c"]["id"]])
        self.assertEqual(body["source_to_output"]["entities"], {"c": None, "a": "a", "b": "b"})
        maps = body["source_to_output"]["relations"]
        removed = [row for row in maps if row["output_key"] is None]
        self.assertEqual(removed, [{"source_key": {"source": "a", "target": "c", "type": "owes"}, "output_key": None}])
        self.assertEqual(len(maps), len(self.model["relations"]))

    def test_empty_projection_retains_metadata_and_reports_actual_evidence_set_difference(self):
        recipe = self.recipe("project_entities", {"entity_ids": []})
        parent = self.parent_for()
        result = self.execute(recipe, parent=parent)
        self.assertEqual(result["kind"], "graph_transform_completed", result)
        body = result["body"]
        self.assertEqual(body["output_model"], {"entities": [], "relations": [], "metadata": self.model["metadata"]})
        self.assertEqual(body["losses"]["removed_entities"], self.model["entities"])
        self.assertEqual(body["losses"]["removed_relations"], self.model["relations"])
        self.assertEqual(set(body["losses"]["removed_evidence_ids"]), {self.evidence[name]["id"] for name in ("a", "b", "c")})

    def test_recipe_identity_survives_parent_instances_and_artifact_recapture(self):
        first = self.execute(self.projection, key="first")
        self.now = "2030-01-01T00:01:00Z"
        self.code = self.capture("recaptured-code", transforms.IMPLEMENTATION_SOURCE)
        self.dependencies = {module.__name__: self.capture("recaptured-" + module.__name__, module.IMPLEMENTATION_SOURCE)["id"]
                             for module in (store, assertions, manifests)}
        recipe = self.recipe("project_entities", {"entity_ids": ["a", "b"]})
        parent = self.parent_for()
        second = self.execute(recipe, parent=parent, key="second")
        self.assertEqual(second["kind"], "graph_transform_completed", second)
        self.assertNotEqual(first["body"]["request"], second["body"]["request"])
        self.assertEqual(first["body"]["recipe_id"], second["body"]["recipe_id"])
        self.assertEqual(first["body"]["output_model"], second["body"]["output_model"])
        self.assertEqual(first["body"]["losses"], second["body"]["losses"])

    def test_exact_terminal_replay_survives_blob_loss_but_changed_request_fails(self):
        result = self.execute(self.projection)
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        before = len(self.ledger.events())
        self.assertEqual(self.execute(self.projection), result)
        self.assertEqual(len(self.ledger.events()), before)
        with self.assertRaisesRegex(ValueError, "different request"):
            self.execute(self.identity)
        self.assertEqual(len(self.ledger.events()), before)

    def test_rejected_attempt_replays_without_new_records(self):
        recipe = self.recipe("unsupported", {})
        parent = self.parent_for()
        result = self.assert_rejected(recipe, parent=parent, key="bad", diagnostic="Unsupported fixed")
        before = len(self.ledger.events())
        self.assertEqual(self.execute(recipe, parent=parent, key="bad"), result)
        self.assertEqual(len(self.ledger.events()), before)

    def test_unknown_ops_false_claims_and_bad_config_are_recorded_rejections(self):
        cases = [("merge", {}, {}), ("identity", {"entity_ids": ["a"]}, {}),
                 ("project_entities", {"entity_ids": ["unknown"]}, {}),
                 ("project_entities", {"entity_ids": ["a", "a"]}, {}),
                 ("identity", {}, {"canonical_exact": True}),
                 ("identity", {}, {"output_model": self.model}),
                 ("identity", {}, {"schema_version": True}),
                 ("identity", {}, {"output_schema": "other"})]
        for index, (operation, config, changes) in enumerate(cases):
            with self.subTest(index=index):
                recipe = self.recipe(operation, config, **changes)
                self.assert_rejected(recipe, parent=self.parent_for(), key=f"bad-{index}")

    def test_duplicate_json_keys_nonfinite_values_and_invalid_json_are_rejected(self):
        for index, raw in enumerate((b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}', b'not JSON', b'\xff')):
            with self.subTest(raw=raw):
                recipe = self.capture("bad-json", raw)
                self.assert_rejected(recipe, parent=self.parent_for(), key=f"json-{index}", diagnostic="Invalid finite JSON")

    def assert_surrogate_rejection(self, artifact_kind, key_repeats=1):
        key = b"\\ud800" * key_repeats
        raw = b'{"' + key + b'":1,"' + key + b'":2}'
        artifact = self.capture("malformed-surrogate-" + artifact_kind, raw)
        recipe = artifact if artifact_kind == "recipe" else self.recipe(
            "identity", {}, config_observation_id=artifact["id"])
        parent = self.parent_for()
        result = self.assert_rejected(recipe, parent=parent, key="surrogate-" + artifact_kind,
                                      diagnostic="Duplicate JSON field")
        self.assertEqual(len(self.ledger.events("graph_transform_started")), 1)
        self.assertEqual(len(self.ledger.events("graph_transform_rejected")), 1)
        self.assertEqual(self.ledger.events("graph_transform_completed"), [])
        message = result["body"]["error"]["message"]
        self.assertIn("\\ud800", message)
        message.encode("utf-8")
        canonical(result).encode("utf-8")
        self.assertLessEqual(len(message), 400)
        self.assertEqual((self.ledger.root / "blobs" / artifact["body"]["content_hash"]).read_bytes(), raw)
        self.assertTrue(self.ledger.verify()["valid"])
        before = len(self.ledger.events())
        self.assertEqual(self.execute(recipe, parent=parent, key="surrogate-" + artifact_kind), result)
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        self.assertEqual(self.execute(recipe, parent=parent, key="surrogate-" + artifact_kind), result)
        self.assertEqual(len(self.ledger.events()), before)
        # Blob loss affects availability; it must not break the event hash chain.
        previous = "0" * 64
        for event in self.ledger.events():
            payload = {field: event[field] for field in ("id", "kind", "recorded_at", "body", "previous_hash")}
            self.assertEqual(event["previous_hash"], previous)
            self.assertEqual(event["hash"], digest(canonical(payload).encode("utf-8")))
            previous = event["hash"]

    def test_duplicate_surrogate_recipe_key_has_replayable_utf8_safe_rejection(self):
        self.assert_surrogate_rejection("recipe")

    def test_duplicate_surrogate_config_key_has_replayable_utf8_safe_rejection(self):
        self.assert_surrogate_rejection("config")

    def test_surrogate_diagnostic_is_truncated_after_escaping(self):
        self.assert_surrogate_rejection("recipe", key_repeats=100)

    def test_late_recipe_config_code_and_dependency_cannot_enter_snapshot(self):
        self.now = "2030-01-01T00:01:00Z"
        late_recipe = self.recipe("identity", {})
        self.assert_rejected(late_recipe, key="late-recipe", diagnostic="selected snapshot")
        # A pre-cutoff recipe can refer to predictable IDs that are captured only later.
        for field, name in (("config_observation_id", "config"), ("implementation_observation_id", "code"),
                            ("dependency_observations", "dependency")):
            with self.subTest(field=field):
                future_id = f"future-{name}"
                changes = {field: future_id} if field != "dependency_observations" else {
                    field: {**self.dependencies, "epiphysics.store": future_id}}
                recipe = self.recipe("identity", {}, **changes)
                parent = self.parent_for()
                self.now = "2030-01-01T00:02:00Z"
                raw = b"{}" if name == "config" else transforms.IMPLEMENTATION_SOURCE if name == "code" else store.IMPLEMENTATION_SOURCE
                self.ledger.capture("synthetic:future", raw, published_at="2000-01-01T00:00:00Z", event_id=future_id)
                self.assert_rejected(recipe, parent=parent, key=f"late-{name}", diagnostic="selected snapshot")

    def test_retained_code_must_match_executing_code_and_is_never_executed(self):
        fake = self.capture("fake-code", b"raise RuntimeError('retained bytes executed')")
        recipe = self.recipe("identity", {}, implementation_observation_id=fake["id"], implementation_sha256=fake["body"]["content_hash"])
        result = self.assert_rejected(recipe, parent=self.parent_for(), diagnostic="fixed executing source")
        self.assertEqual(result["body"]["error"]["type"], "ValueError")

    def test_expected_source_hash_and_every_retained_dependency_are_bound(self):
        recipe = self.recipe("identity", {}, implementation_sha256="0" * 64)
        self.assert_rejected(recipe, parent=self.parent_for(), key="bad-hash", diagnostic="fixed executing source")
        for index, name in enumerate(self.dependencies):
            with self.subTest(name=name):
                wrong = self.capture("wrong-dependency", b"wrong implementation dependency")
                recipe = self.recipe("identity", {}, dependency_observations={**self.dependencies, name: wrong["id"]})
                self.assert_rejected(recipe, parent=self.parent_for(), key=f"bad-dep-{index}", diagnostic="Retained dependency")

    def test_missing_or_tampered_recipe_and_parent_artifacts_are_rejected(self):
        targets = [self.identity["id"], self.code["id"], self.dependencies["epiphysics.store"],
                   self.artifacts["predictor"], self.evidence["a"]["id"]]
        for index, oid in enumerate(targets):
            with self.subTest(oid=oid):
                observation = self.ledger.get(oid)
                path = self.ledger.root / "blobs" / observation["body"]["content_hash"]
                raw = path.read_bytes()
                path.write_bytes(raw + b"tampered")
                self.assert_rejected(key=f"tampered-{index}")
                path.write_bytes(raw)
        path = self.ledger.root / "blobs" / self.identity["body"]["content_hash"]
        path.unlink()
        self.assert_rejected(key="missing-recipe", diagnostic="regular blob")

    def test_unsupported_encoding_schema_or_non_graph_model_is_not_converted(self):
        variants = [(self.model, "text", transforms.OUTPUT_SCHEMA), (self.model, "directed-graph", "other-schema"),
                    ({"text": "not a graph", "evidence_ids": [self.evidence["a"]["id"]]}, "directed-graph", transforms.OUTPUT_SCHEMA)]
        for index, (model, encoding, schema_id) in enumerate(variants):
            parent = self.parent_for(model, encoding=encoding, schema_id=schema_id)
            self.assert_rejected(parent=parent, key=f"shape-{index}")

    def test_graph_identifier_endpoint_triple_and_evidence_validation(self):
        variants = []
        duplicate_node = deepcopy(self.model)
        duplicate_node["entities"].append(deepcopy(duplicate_node["entities"][0]))
        variants.append(duplicate_node)
        dangling = deepcopy(self.model)
        dangling["relations"][0]["target"] = "unknown"
        variants.append(dangling)
        duplicate_edge = deepcopy(self.model)
        duplicate_edge["relations"].append(deepcopy(duplicate_edge["relations"][0]))
        variants.append(duplicate_edge)
        bad_type = deepcopy(self.model)
        bad_type["relations"][0]["type"] = ""
        variants.append(bad_type)
        duplicate_edge_id = deepcopy(self.model)
        duplicate_edge_id["relations"][1]["id"] = "removed-edge"
        variants.append(duplicate_edge_id)
        missing_evidence = deepcopy(self.model)
        missing_evidence["entities"][0]["evidence_ids"] = []
        variants.append(missing_evidence)
        for index, model in enumerate(variants):
            with self.subTest(index=index):
                self.assert_rejected(parent=self.parent_for(model, raw=True), key=f"graph-{index}")

    def test_mutation_after_compute_is_rechecked_before_atomic_completion(self):
        append = self.ledger.append
        path = self.ledger.root / "blobs" / self.code["body"]["content_hash"]

        def mutate_before_completion(kind, body, event_id=None, **options):
            if kind == "graph_transform_completed":
                path.write_bytes(b"changed after initial execution")
            return append(kind, body, event_id, **options)

        with patch.object(self.ledger, "append", side_effect=mutate_before_completion):
            self.assert_rejected(diagnostic="hash or size")
        self.assertEqual(self.ledger.events("graph_transform_completed"), [])

    def test_loaded_source_and_fixed_callable_changes_refuse_completion(self):
        with patch.object(manifests, "IMPLEMENTATION_SOURCE", b"different source"):
            self.assert_rejected(key="source-drift", diagnostic="implementation reloaded")
        with patch.object(transforms, "_compute_graph", return_value={}):
            self.assert_rejected(key="compute-drift", diagnostic="callable changed")

    def test_invalid_keys_or_unaddressable_inputs_refuse_without_claim(self):
        before = len(self.ledger.events())
        for key in ("", "space key", "a" * 101, True):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.execute(key=key)
        with self.assertRaises(ValueError):
            transforms.execute_graph_transform(self.ledger, "missing", self.identity["id"], run_key="missing-parent")
        with self.assertRaises(ValueError):
            transforms.execute_graph_transform(self.ledger, self.parent["id"], "missing", run_key="missing-recipe")
        self.assertEqual(len(self.ledger.events()), before)

    def test_interruption_leaves_one_start_and_requires_diagnosis(self):
        append = self.ledger.append

        def interrupt_completion(kind, body, event_id=None, **options):
            if kind == "graph_transform_completed":
                raise RuntimeError("Simulated interrupted process")
            return append(kind, body, event_id, **options)

        with patch.object(self.ledger, "append", side_effect=interrupt_completion), self.assertRaisesRegex(RuntimeError, "interrupted"):
            self.execute()
        self.assertEqual(len(self.ledger.events("graph_transform_started")), 1)
        self.assertEqual(self.ledger.events("graph_transform_completed"), [])
        self.assertEqual(self.ledger.events("graph_transform_rejected"), [])
        before = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, "requires diagnosis"):
            self.execute()
        self.assertEqual(len(self.ledger.events()), before)

    def test_concurrent_claims_produce_only_one_start_and_one_terminal(self):
        barrier = threading.Barrier(2)
        outcomes = []

        def worker():
            ledger = Ledger(self.ledger.root, clock=lambda: self.now)
            try:
                barrier.wait(timeout=5)
                outcomes.append(transforms.execute_graph_transform(ledger, self.parent["id"], self.projection["id"], run_key="race"))
            except ValueError:
                outcomes.append("in-flight refusal")
            finally:
                ledger.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 2)
        successes = [outcome for outcome in outcomes if isinstance(outcome, dict)]
        self.assertGreaterEqual(len(successes), 1)
        self.assertTrue(all(result == successes[0] for result in successes))
        self.assertEqual(successes[0]["kind"], "graph_transform_completed")
        self.assertEqual(len(self.ledger.events("graph_transform_started")), 1)
        self.assertEqual(len(self.ledger.events("graph_transform_completed")), 1)
        self.assertEqual(self.ledger.events("graph_transform_rejected"), [])
        self.assertTrue(self.ledger.verify()["valid"])


if __name__ == "__main__":
    unittest.main()
