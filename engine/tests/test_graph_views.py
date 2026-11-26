from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from epiphysics import assertions, graph_views, manifests, store, transforms
from epiphysics.store import Ledger, canonical, digest


class GraphViewsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(Path(self.temp.name) / "ledger", clock=lambda: self.now)
        self.evidence = {name: self.capture(name, ("Synthetic evidence " + name).encode()) for name in ("a", "b", "c", "cross", "internal", "meta")}
        self.artifacts = {role: self.capture(role, ("Declared " + role).encode())["id"] for role in manifests.ARTIFACT_ROLES}
        self.code = self.capture("views-code", graph_views.IMPLEMENTATION_SOURCE)
        self.dependencies = {module.__name__: self.capture(module.__name__, module.IMPLEMENTATION_SOURCE)["id"]
                             for module in (store, assertions, manifests, transforms)}
        self.partition = self.recipe("partition_entities", {"views": {"right": ["c"], "left": ["b", "a"]}})
        self.merge = self.recipe("merge_graphs", {"conflicts": "reject"})
        self.model = {"entities": [self.entity("c"), self.entity("b"), self.entity("a")],
            "relations": [self.edge("b", "c", "funds", "cross", id="cross", amount={"value": 7, "unit": "EUR"}),
                          self.edge("a", "b", "supplies", "internal"), self.edge("b", "a", "depends_on", "internal"),
                          self.edge("a", "b", "pays", "internal", amount={"value": 12, "unit": "USD"}),
                          self.edge("c", "c", "monitors", "c")],
            "metadata": {"description": "Fictional context, retained verbatim", "evidence_ids": [self.evidence["meta"]["id"]]}}
        self.snapshot = self.ledger.snapshot()
        self.parent = self.parent_for()

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def capture(self, name, raw):
        return self.ledger.capture("synthetic:" + name, raw)

    def entity(self, eid):
        return {"id": eid, "basis": "reported", "evidence_ids": [self.evidence[eid]["id"]],
                "amount": {"value": {"a": 12, "b": 2, "c": 7}[eid], "unit": "USD"}}

    def edge(self, source, target, kind, evidence, **attrs):
        return {"source": source, "target": target, "type": kind, "basis": "reported",
                "evidence_ids": [self.evidence[evidence]["id"]], **attrs}

    def recipe(self, operation, config, **changes):
        config = self.capture("views-config", canonical(config).encode())
        return self.capture("views-recipe", canonical({"schema_version": 1, "operation": operation,
            "config_observation_id": config["id"], "implementation_observation_id": self.code["id"],
            "implementation_sha256": digest(graph_views.IMPLEMENTATION_SOURCE), "dependency_observations": self.dependencies,
            "output_schema": graph_views.OUTPUT_SCHEMA, **changes}).encode())

    def parent_for(self, model=None, *, snapshot=None, observer="observer", raw=False, **changes):
        model = deepcopy(self.model if model is None else model)
        snap = snapshot or self.snapshot
        if raw:
            rep = self.ledger.append("representation", {"snapshot_id": snap["id"], "observer": observer,
                "method": "declared-constructor", "parent": None, "model": model})
        else:
            rep = self.ledger.representation(snap["id"], model, observer=observer, method="declared-constructor")
        arguments = {"encoding": "directed-graph", "schema_id": graph_views.OUTPUT_SCHEMA, "artifacts": self.artifacts,
                     "task": {"id": "invoice", "family": "contract_obligation", "outcome_type": "binary"},
                     "horizon_seconds": 600, "units": {"amount": "USD"},
                     "evidence_ids": sorted(manifests._model_evidence(model)), "construction_cost": None, **changes}
        return manifests.register_manifest(self.ledger, rep["id"], **arguments)

    def fresh_parent(self, model=None, **changes):
        self.snapshot = self.ledger.snapshot()
        return self.parent_for(model, **changes)

    def execute(self, recipe=None, *, parents=None, key="run"):
        return graph_views.execute_graph_views(self.ledger, [parent["id"] for parent in (parents or [self.parent])],
                                              (recipe or self.partition)["id"], run_key=key)

    def rejected(self, recipe=None, *, parents=None, key="bad", diagnostic=None):
        before = len(self.ledger.events())
        result = self.execute(recipe, parents=parents, key=key)
        self.assertEqual(result["kind"], "graph_views_rejected", result)
        self.assertEqual(result["body"]["result"], "rejected")
        self.assertEqual(len(self.ledger.events()), before + 2)
        result["body"]["error"]["message"].encode("utf-8")
        self.assertLessEqual(len(result["body"]["error"]["message"]), 400)
        if diagnostic:
            self.assertIn(diagnostic, result["body"]["error"]["message"])
        return result

    def completed(self, recipe=None, *, parents=None, key="run"):
        result = self.execute(recipe, parents=parents, key=key)
        self.assertEqual(result["kind"], "graph_views_completed", result)
        return result

    def test_partition_computes_induced_views_without_duplicating_entities_or_quantities(self):
        before = self.ledger.events()
        body = self.completed()["body"]
        left, right = body["outputs"]["left"]["model"], body["outputs"]["right"]["model"]
        self.assertEqual(list(body["outputs"]), ["left", "right"])
        self.assertEqual(left["entities"], self.model["entities"][1:])
        self.assertEqual(left["relations"], self.model["relations"][1:4])
        self.assertEqual(right["entities"], self.model["entities"][:1])
        self.assertEqual(right["relations"], self.model["relations"][4:])
        self.assertEqual(left["metadata"], self.model["metadata"])
        self.assertEqual(right["metadata"], self.model["metadata"])
        self.assertEqual(sum(row["amount"]["value"] for model in (left, right) for row in model["entities"]), 21)
        for output in body["outputs"].values():
            self.assertEqual(output["model_hash"], digest(canonical(output["model"]).encode()))
        self.assertEqual(self.ledger.events()[:len(before)], before)
        self.assertEqual([x["kind"] for x in self.ledger.events()[len(before):]], ["graph_views_started", "graph_views_completed"])
        self.assertEqual(len(self.ledger.events("representation")), 1)
        self.assertEqual(len(self.ledger.events("representation_manifest")), 1)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_partition_cross_edge_losses_and_all_input_ancestry_are_explicit(self):
        body = self.completed()["body"]
        self.assertEqual(body["losses"], {"removed_entities": [],
            "removed_relations": [{"parent_manifest_id": self.parent["id"], "record": self.model["relations"][0]}],
            "removed_evidence_ids": [self.evidence["cross"]["id"]]})
        self.assertEqual(body["deduplications"], {"entities": [], "relations": []})
        mapping = body["source_to_output"][0]
        self.assertEqual(mapping["parent_manifest_id"], self.parent["id"])
        self.assertEqual(mapping["entities"], [
            {"source_id": "c", "output": {"view": "right", "id": "c"}},
            {"source_id": "b", "output": {"view": "left", "id": "b"}},
            {"source_id": "a", "output": {"view": "left", "id": "a"}}])
        self.assertEqual(mapping["relations"][0], {"source_key": {"source": "b", "target": "c", "type": "funds"}, "output": None})
        self.assertEqual(len(mapping["relations"]), len(self.model["relations"]))
        self.assertEqual(mapping["metadata"], {"fields": ["metadata"], "output_views": ["left", "right"]})
        for row in mapping["relations"][1:]:
            self.assertEqual(row["source_key"], row["output"]["key"])

    def test_one_view_retains_cycles_and_self_loops_exactly_and_no_evidence_is_lost(self):
        recipe = self.recipe("partition_entities", {"views": {"all": ["a", "b", "c"]}})
        parent = self.fresh_parent()
        body = self.completed(recipe, parents=[parent])["body"]
        self.assertEqual(body["outputs"]["all"]["model"], self.model)
        self.assertEqual(body["losses"], {"removed_entities": [], "removed_relations": [], "removed_evidence_ids": []})

    def test_partition_rejects_empty_overlapping_incomplete_unknown_duplicate_or_oversized_views(self):
        configs = [{"views": {}}, {"views": {"left": [], "right": ["a", "b", "c"]}},
            {"views": {"left": ["a", "b"], "right": ["b", "c"]}}, {"views": {"left": ["a", "b"]}},
            {"views": {"all": ["a", "b", "c", "ghost"]}}, {"views": {"all": ["a", "a", "b", "c"]}},
            {"views": {"": ["a", "b", "c"]}}, {"views": []},
            {"views": {str(i): [str(i)] for i in range(65)}}]
        for index, config in enumerate(configs):
            with self.subTest(config=config):
                recipe = self.recipe("partition_entities", config)
                self.rejected(recipe, parents=[self.fresh_parent()], key=f"bad-config-{index}")

    def test_view_name_byte_boundary_accepts_ascii_and_multibyte_names(self):
        for index, name in enumerate(("v" * 128, "é" * 64)):
            self.assertEqual(len(name.encode("utf-8")), 128)
            recipe = self.recipe("partition_entities", {"views": {name: ["a", "b", "c"]}})
            body = self.completed(recipe, parents=[self.fresh_parent()], key=f"view-boundary-{index}")["body"]
            self.assertEqual(list(body["outputs"]), [name])
            self.assertEqual(body["outputs"][name]["model"], self.model)
            self.assertTrue(all(row["output"]["view"] == name for row in body["source_to_output"][0]["entities"]))
        self.assertTrue(self.ledger.verify()["valid"])

    def test_oversized_view_names_have_durable_rejections_before_computation(self):
        for index, name in enumerate(("v" * 129, "é" * 64 + "x")):
            self.assertEqual(len(name.encode("utf-8")), 129)
            recipe = self.recipe("partition_entities", {"views": {name: ["a", "b", "c"]}})
            parent = self.fresh_parent()
            # A normally pinned compute function is instrumented only to prove this
            # validation precedes receipt/mapping expansion, not to test identity pins.
            sources = graph_views._runtime_sources()
            with patch.object(graph_views, "_runtime_sources", return_value=sources), \
                    patch.object(graph_views, "_compute_graph_views", side_effect=AssertionError("must not expand oversized name")) as compute:
                result = self.rejected(recipe, parents=[parent], key=f"view-overflow-{index}", diagnostic="View name exceeds 128 UTF-8 bytes")
                compute.assert_not_called()
            self.assertEqual(self.execute(recipe, parents=[parent], key=f"view-overflow-{index}"), result)
            self.assertEqual(result["body"]["error"]["message"], "View name exceeds 128 UTF-8 bytes")
        self.assertEqual(len(self.ledger.events("graph_views_started")), 2)
        self.assertEqual(len(self.ledger.events("graph_views_rejected")), 2)
        self.assertEqual(self.ledger.events("graph_views_completed"), [])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_parent_id_byte_boundary_accepts_ascii_and_multibyte_identifiers(self):
        for index, parent_id in enumerate(("p" * 512, "é" * 256)):
            self.assertEqual(len(parent_id.encode("utf-8")), 512)
            parent = self.parent_for(event_id=parent_id)
            body = self.completed(parents=[parent], key=f"parent-boundary-{index}")["body"]
            self.assertEqual(body["request"]["parents"][0]["manifest"]["id"], parent_id)
            self.assertEqual(body["source_to_output"][0]["parent_manifest_id"], parent_id)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_oversized_genuine_parent_ids_refuse_before_request_expansion_or_claim(self):
        for index, parent_id in enumerate(("p" * 513, "é" * 256 + "x")):
            self.assertEqual(len(parent_id.encode("utf-8")), 513)
            parent = self.parent_for(event_id=parent_id)
            before = self.ledger.events()
            with patch.object(graph_views, "_request_metadata", side_effect=AssertionError("must not expand oversized ID")) as metadata:
                with self.assertRaisesRegex(ValueError, "Parent manifest ID exceeds 512 UTF-8 bytes"):
                    self.execute(parents=[parent], key=f"parent-overflow-{index}")
                metadata.assert_not_called()
            self.assertEqual(self.ledger.events(), before)
        self.assertEqual(self.ledger.events("graph_views_started"), [])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_merge_unions_records_and_deduplicates_only_identical_records_with_all_ancestry(self):
        subset = deepcopy(self.model)
        subset["entities"] = subset["entities"][1:]
        subset["relations"] = subset["relations"][1:4]
        second = self.parent_for(subset)
        body = self.completed(self.merge, parents=[self.parent, second])["body"]
        model = body["outputs"]["merged"]["model"]
        expected = deepcopy(self.model)
        expected["entities"].sort(key=lambda x: x["id"])
        expected["relations"].sort(key=lambda x: (x["source"], x["target"], x["type"]))
        self.assertEqual(model, expected)
        self.assertEqual(body["losses"], {"removed_entities": [], "removed_relations": [], "removed_evidence_ids": []})
        parents = sorted([self.parent["id"], second["id"]])
        self.assertEqual(body["deduplications"]["entities"], [{"output_id": eid, "parent_manifest_ids": parents} for eid in ("a", "b")])
        self.assertEqual(len(body["deduplications"]["relations"]), 3)
        self.assertTrue(all(row["parent_manifest_ids"] == parents for row in body["deduplications"]["relations"]))
        self.assertEqual([x["parent_manifest_id"] for x in body["source_to_output"]], parents)
        self.assertEqual(sum(len(x["entities"]) for x in body["source_to_output"]), 5)
        self.assertEqual(sum(len(x["relations"]) for x in body["source_to_output"]), 8)
        self.assertEqual([x["manifest"]["id"] for x in body["request"]["parents"]], parents)
        self.assertEqual(body["resources"], {"model_calls": 0, "external_spend": 0})

    def test_merge_parent_order_is_normalized_in_request_and_replay(self):
        second = self.parent_for()
        first = self.completed(self.merge, parents=[self.parent, second])
        before = len(self.ledger.events())
        self.assertEqual(self.execute(self.merge, parents=[second, self.parent]), first)
        self.assertEqual(len(self.ledger.events()), before)
        different = self.completed(self.merge, parents=[second, self.parent], key="different")
        for key in ("outputs", "losses", "source_to_output", "deduplications", "recipe_id"):
            self.assertEqual(first["body"][key], different["body"][key])

    def test_merge_rejects_entity_attribute_unit_basis_and_evidence_conflicts(self):
        variants = []
        for field, value in (("amount", {"value": 8, "unit": "USD"}), ("amount", {"value": 7, "unit": "EUR"}),
                             ("basis", "inferred"), ("evidence_ids", [self.evidence["a"]["id"]])):
            model = deepcopy(self.model)
            model["entities"][0][field] = value
            variants.append(model)
        for index, model in enumerate(variants):
            with self.subTest(index=index):
                second = self.parent_for(model)
                self.rejected(self.merge, parents=[self.parent, second], key=f"entity-{index}", diagnostic="Conflicting merge entity")

    def test_merge_rejects_edge_attribute_provenance_and_relation_id_collisions(self):
        variants = []
        for field, value in (("amount", {"value": 99, "unit": "EUR"}), ("evidence_ids", [self.evidence["a"]["id"]]),
                             ("basis", "inferred"), ("id", "different-id")):
            model = deepcopy(self.model)
            model["relations"][0][field] = value
            variants.append((model, "Conflicting merge relation record"))
        model = deepcopy(self.model)
        model["relations"] = [self.edge("a", "a", "owns", "a", id="cross")]
        variants.append((model, "Conflicting merge relation id"))
        for index, (model, diagnostic) in enumerate(variants):
            with self.subTest(index=index):
                self.rejected(self.merge, parents=[self.parent, self.parent_for(model)], key=f"relation-{index}", diagnostic=diagnostic)

    def test_merge_rejects_root_metadata_conflicts_instead_of_dropping_context(self):
        for index, metadata in enumerate(({"description": "different"}, None)):
            model = deepcopy(self.model)
            if metadata is None:
                del model["metadata"]
            else:
                model["metadata"] = metadata
            self.rejected(self.merge, parents=[self.parent, self.parent_for(model)], key=f"metadata-{index}", diagnostic="root metadata")

    def test_merge_requires_same_snapshot_and_declared_semantics(self):
        variants = [{"observer": "other"}, {"horizon_seconds": 601}, {"units": {"amount": "EUR"}},
            {"task": {"id": "other", "family": "contract_obligation", "outcome_type": "binary"}},
            {"encoding": "text"}, {"schema_id": "other"}]
        for index, changes in enumerate(variants):
            with self.subTest(changes=changes):
                self.rejected(self.merge, parents=[self.parent, self.parent_for(**changes)], key=f"semantics-{index}")
        second = self.fresh_parent()
        self.rejected(self.merge, parents=[self.parent, second], key="snapshot", diagnostic="identical snapshot")
        for index, role in enumerate(("ontology", "predictor")):
            alternative = self.capture("alternative-" + role, b"different artifact")["id"]
            first = self.fresh_parent()
            second = self.parent_for(artifacts={**self.artifacts, role: alternative})
            self.rejected(self.merge, parents=[first, second], key=f"artifact-semantics-{index}", diagnostic="compatible declared semantics")

    def test_merge_can_use_different_constructor_config_and_unknown_cost_without_claiming_execution(self):
        alt = self.capture("alt-config", b"other construction configuration")["id"]
        first = self.fresh_parent()
        second = self.parent_for(artifacts={**self.artifacts, "config": alt})
        self.completed(self.merge, parents=[first, second])

    def test_merge_union_must_obey_graph_size_limits(self):
        def model_for(prefix):
            return {"entities": [{"id": f"{prefix}-{i}", "basis": "reported", "evidence_ids": [self.evidence["a"]["id"]]}
                                 for i in range(501)], "relations": []}
        first, second = self.parent_for(model_for("x")), self.parent_for(model_for("y"))
        self.rejected(self.merge, parents=[first, second], diagnostic="at most 1000 entities")

    def test_merge_union_cannot_exceed_edge_or_byte_bounds(self):
        edge_parents = []
        for prefix in ("x", "y"):
            model = {"entities": [self.entity("a")],
                     "relations": [self.edge("a", "a", f"{prefix}-{i}", "a") for i in range(2501)]}
            edge_parents.append(self.parent_for(model))
        self.rejected(self.merge, parents=edge_parents, key="edge-limit", diagnostic="at most 5000 relations")
        byte_parents = []
        for eid in ("a", "b"):
            entity = self.entity(eid)
            entity["description"] = "x" * 510_000
            byte_parents.append(self.parent_for({"entities": [entity], "relations": []}))
        self.rejected(self.merge, parents=byte_parents, key="byte-limit", diagnostic="Graph model exceeds 1 MB")

    def test_aggregate_input_and_replicated_output_metadata_are_bounded(self):
        model = {"entities": [self.entity("a")], "relations": [], "context": "x" * 510_000}
        parents = [self.parent_for(model) for _ in range(4)]
        self.rejected(self.merge, parents=parents, key="input-bound", diagnostic="inputs exceed 2 MB")
        ids = [f"entity-{i}" for i in range(64)]
        model = {"entities": [{**self.entity("a"), "id": eid} for eid in ids], "relations": [], "context": "x" * 32_000}
        recipe = self.recipe("partition_entities", {"views": {eid: [eid] for eid in ids}})
        self.rejected(recipe, parents=[self.fresh_parent(model)], key="output-bound", diagnostic="outputs exceed 2 MB")

    def test_changed_fixed_or_reused_callable_is_rejected_before_execution(self):
        with patch.object(graph_views, "_compute_graph_views", side_effect=AssertionError("must not execute")):
            self.rejected(key="changed-own", diagnostic="Fixed graph views callable changed")
        with patch.object(transforms, "_graph", side_effect=AssertionError("must not execute")):
            self.rejected(key="changed-helper", diagnostic="Fixed transform callable changed")

    def test_recipe_identity_survives_recapture_and_parent_instances(self):
        first = self.completed()
        self.code = self.capture("recaptured-code", graph_views.IMPLEMENTATION_SOURCE)
        self.dependencies = {module.__name__: self.capture("recaptured-" + module.__name__, module.IMPLEMENTATION_SOURCE)["id"]
                             for module in (store, assertions, manifests, transforms)}
        recipe = self.recipe("partition_entities", {"views": {"right": ["c"], "left": ["b", "a"]}})
        second = self.completed(recipe, parents=[self.fresh_parent()], key="second")
        self.assertEqual(first["body"]["recipe_id"], second["body"]["recipe_id"])
        self.assertNotEqual(first["body"]["request"], second["body"]["request"])

    def test_exact_completed_and_rejected_replays_survive_blob_loss_but_changed_requests_refuse(self):
        completed = self.completed(key="completed")
        rejected = self.rejected(self.merge, key="rejected", diagnostic="at least two distinct parents")
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        before = len(self.ledger.events())
        self.assertEqual(self.execute(key="completed"), completed)
        self.assertEqual(self.execute(self.merge, key="rejected"), rejected)
        with self.assertRaisesRegex(ValueError, "different request"):
            self.execute(self.merge, key="completed")
        self.assertEqual(len(self.ledger.events()), before)
        self.assertFalse(self.ledger.verify()["valid"])

    def test_invalid_operation_configs_and_caller_outputs_are_rejected(self):
        cases = [("arbitrary", {}, {}), ("merge_graphs", {"conflicts": "overwrite"}, {}),
                 ("partition_entities", {"views": {"all": ["a", "b", "c"]}}, {"outputs": {}}),
                 ("partition_entities", {"views": {"all": ["a", "b", "c"]}}, {"schema_version": True})]
        for index, (operation, config, changes) in enumerate(cases):
            recipe = self.recipe(operation, config, **changes)
            parent = self.fresh_parent()
            second = self.parent_for()
            parents = [parent, second] if operation == "merge_graphs" else [parent]
            self.rejected(recipe, parents=parents, key=f"shape-{index}")
        self.rejected(parents=[self.parent, self.parent_for(snapshot=self.ledger.get(self.parent['body']['snapshot_id']))],
                      key="too-many-partition", diagnostic="exactly one parent")

    def test_duplicate_surrogate_recipe_and_configuration_rejections_are_durable(self):
        raw = br'{"\ud800":1,"\ud800":2}'
        for index, role in enumerate(("recipe", "config")):
            artifact = self.capture("malformed-" + role, raw)
            recipe = artifact if role == "recipe" else self.recipe("partition_entities", {}, config_observation_id=artifact["id"])
            parent = self.fresh_parent()
            result = self.rejected(recipe, parents=[parent], key=f"surrogate-{index}", diagnostic="Duplicate JSON field")
            self.assertIn("\\ud800", result["body"]["error"]["message"])
            self.assertEqual(self.execute(recipe, parents=[parent], key=f"surrogate-{index}"), result)
            self.assertEqual((self.ledger.root / "blobs" / artifact["body"]["content_hash"]).read_bytes(), raw)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_late_recipe_config_code_and_dependency_are_not_eligible(self):
        late = self.recipe("partition_entities", {"views": {"all": ["a", "b", "c"]}})
        self.rejected(late, key="late-recipe", diagnostic="selected snapshot")
        for index, role in enumerate(("config", "code", "dependency")):
            oid = "future-" + role
            changes = {"config_observation_id": oid} if role == "config" else {"implementation_observation_id": oid} if role == "code" else {
                "dependency_observations": {**self.dependencies, "epiphysics.store": oid}}
            recipe = self.recipe("partition_entities", {"views": {"all": ["a", "b", "c"]}}, **changes)
            parent = self.fresh_parent()
            raw = b'{}' if role == "config" else graph_views.IMPLEMENTATION_SOURCE if role == "code" else store.IMPLEMENTATION_SOURCE
            self.ledger.capture("synthetic:late", raw, published_at="2000-01-01T00:00:00Z", event_id=oid)
            self.rejected(recipe, parents=[parent], key=f"late-{index}", diagnostic="selected snapshot")

    def test_fake_implementation_and_each_wrong_dependency_are_rejected_without_execution(self):
        wrong = self.capture("wrong-code", b"raise RuntimeError('do not execute me')")
        recipe = self.recipe("partition_entities", {"views": {"all": ["a", "b", "c"]}},
                             implementation_observation_id=wrong["id"], implementation_sha256=wrong["body"]["content_hash"])
        self.rejected(recipe, parents=[self.fresh_parent()], diagnostic="fixed executing source")
        for index, name in enumerate(self.dependencies):
            recipe = self.recipe("partition_entities", {"views": {"all": ["a", "b", "c"]}},
                                 dependency_observations={**self.dependencies, name: wrong["id"]})
            self.rejected(recipe, parents=[self.fresh_parent()], key=f"dependency-{index}", diagnostic="Retained dependency")

    def test_each_parent_retained_evidence_and_artifact_must_be_available(self):
        second_model = deepcopy(self.model)
        second_model["relations"] = []
        second = self.parent_for(second_model)
        for index, oid in enumerate((self.evidence["c"]["id"], self.artifacts["predictor"], self.code["id"],
                                    self.dependencies["epiphysics.transforms"], self.merge["id"])):
            observation = self.ledger.get(oid)
            path = self.ledger.root / "blobs" / observation["body"]["content_hash"]
            raw = path.read_bytes()
            path.write_bytes(raw + b"tampered")
            self.rejected(self.merge, parents=[self.parent, second], key=f"tampered-{index}")
            path.write_bytes(raw)

    def test_completion_rechecks_configuration_and_second_parent_evidence_under_lock(self):
        second_model = deepcopy(self.model)
        second_model["entities"] = second_model["entities"][:1]
        second_model["relations"] = second_model["relations"][4:]
        first_model = deepcopy(self.model)
        first_model["entities"] = first_model["entities"][1:]
        first_model["relations"] = first_model["relations"][1:4]
        first, second = self.parent_for(first_model), self.parent_for(second_model)
        merge_recipe = json.loads((self.ledger.root / "blobs" / self.merge["body"]["content_hash"]).read_bytes())
        targets = [merge_recipe["config_observation_id"], self.evidence["c"]["id"]]
        append = self.ledger.append
        for index, oid in enumerate(targets):
            observation = self.ledger.get(oid)
            path = self.ledger.root / "blobs" / observation["body"]["content_hash"]
            raw = path.read_bytes()
            def corrupt(kind, body, event_id=None, **options):
                if kind == "graph_views_completed":
                    path.write_bytes(raw + b"tampered before completion")
                return append(kind, body, event_id, **options)
            with patch.object(self.ledger, "append", side_effect=corrupt):
                self.rejected(self.merge, parents=[first, second], key=f"boundary-{index}", diagnostic="hash or size mismatch")
            path.write_bytes(raw)
        self.assertEqual(self.ledger.events("graph_views_completed"), [])
        self.assertFalse(self.ledger.db.in_transaction)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_malformed_graphs_are_rejected_without_conversion(self):
        duplicate = deepcopy(self.model)
        duplicate["entities"].append(deepcopy(duplicate["entities"][0]))
        dangling = deepcopy(self.model)
        dangling["relations"][0]["target"] = "missing"
        for index, model in enumerate((duplicate, dangling, {"text": "not a graph"})):
            parent = self.parent_for(model, raw=True)
            self.rejected(parents=[parent], key=f"bad-graph-{index}")

    def test_duplicate_invalid_or_unknown_parents_and_bad_keys_refuse_before_claim(self):
        before = len(self.ledger.events())
        for parents in ([], [self.parent["id"], self.parent["id"]], ["missing"], "not-a-list", [str(i) for i in range(17)]):
            with self.subTest(parents=parents), self.assertRaises(ValueError):
                graph_views.execute_graph_views(self.ledger, parents, self.partition["id"], run_key="invalid")
        for key in ("", "with space", "a" * 101, True):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.execute(key=key)
        self.assertEqual(len(self.ledger.events()), before)

    def test_interrupted_run_preserves_start_and_requires_diagnosis(self):
        append = self.ledger.append
        def interrupt(kind, body, event_id=None, **options):
            if kind == "graph_views_completed":
                raise RuntimeError("simulated interruption")
            return append(kind, body, event_id, **options)
        with patch.object(self.ledger, "append", side_effect=interrupt), self.assertRaises(RuntimeError):
            self.execute()
        self.assertEqual(len(self.ledger.events("graph_views_started")), 1)
        self.assertEqual(self.ledger.events("graph_views_completed"), [])
        self.assertEqual(self.ledger.events("graph_views_rejected"), [])
        with self.assertRaisesRegex(ValueError, "requires diagnosis"):
            self.execute()

    def test_concurrent_claims_create_one_start_and_one_terminal(self):
        barrier = threading.Barrier(2)
        outcomes = []
        def worker():
            ledger = Ledger(self.ledger.root, clock=lambda: self.now)
            try:
                barrier.wait(timeout=5)
                outcomes.append(graph_views.execute_graph_views(ledger, [self.parent["id"]], self.partition["id"], run_key="race"))
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
        successes = [x for x in outcomes if isinstance(x, dict)]
        self.assertGreaterEqual(len(successes), 1)
        self.assertTrue(all(x == successes[0] for x in successes))
        self.assertEqual(successes[0]["kind"], "graph_views_completed")
        self.assertEqual(len(self.ledger.events("graph_views_started")), 1)
        self.assertEqual(len(self.ledger.events("graph_views_completed")), 1)
        self.assertEqual(self.ledger.events("graph_views_rejected"), [])
        self.assertTrue(self.ledger.verify()["valid"])


if __name__ == "__main__":
    unittest.main()
