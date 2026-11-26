from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from epiphysics import graph_views, manifests, materialization, store, transforms
from epiphysics.store import Ledger, canonical, digest, instant
import test_graph_views


class MaterializationTests(unittest.TestCase):
    def setUp(self):
        # Reuse only the fixture helpers, not the graph-operation test suite.
        self.fixture = test_graph_views.GraphViewsTests()
        self.fixture.setUp()
        self.ledger = self.fixture.ledger
        fx = self.fixture
        self.transform_code = fx.capture("transform-code", transforms.IMPLEMENTATION_SOURCE)
        self.transform_recipes = {}
        for operation, config in (("identity", {}), ("project_entities", {"entity_ids": ["a", "b"]})):
            configuration = fx.capture(operation + "-configuration", canonical(config).encode())
            recipe = {"schema_version": 1, "operation": operation, "config_observation_id": configuration["id"],
                "implementation_observation_id": self.transform_code["id"], "implementation_sha256": digest(transforms.IMPLEMENTATION_SOURCE),
                "dependency_observations": {name: oid for name, oid in fx.dependencies.items() if name != "epiphysics.transforms"},
                "output_schema": transforms.OUTPUT_SCHEMA}
            self.transform_recipes[operation] = fx.capture(operation + "-recipe", canonical(recipe).encode())
        fx.parent = fx.fresh_parent()
        self.parent = fx.parent

    def tearDown(self):
        self.fixture.tearDown()

    def execute(self, operation="partition", *, parents=None, key="execute"):
        parents = parents or [self.parent]
        if operation in ("identity", "project_entities"):
            result = transforms.execute_graph_transform(self.ledger, parents[0]["id"], self.transform_recipes[operation]["id"], run_key=key)
        else:
            if operation == "merge" and len(parents) == 1:
                parents = parents + [self.fixture.parent_for()]
            recipe = self.fixture.partition if operation == "partition" else self.fixture.merge
            result = graph_views.execute_graph_views(self.ledger, [parent["id"] for parent in parents], recipe["id"], run_key=key)
        self.assertIn(result["kind"], materialization.COMPLETIONS, result)
        return result

    def materialize(self, execution, *, key="materialize"):
        return materialization.materialize_graph_outputs(self.ledger, execution["id"], run_key=key)

    def completed(self, execution, *, key="materialize"):
        result = self.materialize(execution, key=key)
        self.assertEqual(result["kind"], "graph_materialization_completed", result)
        return result

    def rejected(self, execution, *, key="materialize", diagnostic=None):
        representations, manifest_rows = self.ledger.events("representation"), self.ledger.events("representation_manifest")
        before = len(self.ledger.events())
        result = self.materialize(execution, key=key)
        self.assertEqual(result["kind"], "graph_materialization_rejected", result)
        self.assertEqual(self.ledger.events("representation"), representations)
        self.assertEqual(self.ledger.events("representation_manifest"), manifest_rows)
        self.assertEqual(len(self.ledger.events()), before + 2)
        if diagnostic:
            self.assertIn(diagnostic, result["body"]["error"]["message"])
        self.assertFalse(self.ledger.db.in_transaction)
        return result

    def synthetic_execution(self, original, *, key, change):
        body = deepcopy(original["body"])
        body["run_key"] = key
        change(body)
        prefix, kind = ("graph-transform", "graph_transform_started") if original["kind"] == "graph_transform_completed" else ("graph-views", "graph_views_started")
        self.ledger.append(kind, {"schema_version": 1, "run_key": key, "request": body["request"]}, f"{prefix}:{key}:started")
        return self.ledger.append(original["kind"], body, f"{prefix}:{key}:terminal")

    def test_all_four_operations_materialize_exact_outputs_into_valid_complete_bundles(self):
        for index, operation in enumerate(("identity", "project_entities", "partition", "merge")):
            with self.subTest(operation=operation):
                execution = self.execute(operation, key=f"execute-{index}")
                originals = self.ledger.events()
                completed = self.completed(execution, key=f"materialize-{index}")
                bundle = materialization.get_materialized_outputs(self.ledger, completed["id"])
                self.assertEqual(bundle["receipt"], completed)
                expected = execution["body"].get("outputs", {"output": {"model": execution["body"].get("output_model"),
                    "model_hash": execution["body"].get("output_model_hash")}})
                self.assertEqual(set(bundle["manifests"]), set(expected))
                for name, representation in bundle["representations"].items():
                    manifest = bundle["manifests"][name]
                    self.assertEqual(representation["body"]["model"], expected[name]["model"])
                    self.assertEqual(manifest["body"]["model_hash"], expected[name]["model_hash"])
                    self.assertEqual(manifest["body"]["snapshot_id"], self.parent["body"]["snapshot_id"])
                    self.assertEqual(representation["recorded_at"], completed["recorded_at"])
                    self.assertEqual(manifest["recorded_at"], completed["recorded_at"])
                    self.assertEqual(manifest["body"]["construction_cost"], manifests._cost(None))
                    self.assertEqual(manifest["body"]["descriptor"]["construction_method"], representation["body"]["method"])
                self.assertEqual(self.ledger.events()[:len(originals)], originals)
        self.assertEqual(self.ledger.events("forecast"), [])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_parent_instances_multiplicity_losses_and_mapping_links_are_preserved(self):
        parents = [self.parent, self.fixture.parent_for(), self.fixture.parent_for()]
        execution = self.execute("merge", parents=parents)
        body = self.completed(execution)["body"]
        expected_ids = sorted(parent["id"] for parent in parents)
        self.assertEqual([parent["manifest_id"] for parent in body["parents"]], expected_ids)
        self.assertEqual(body["derivations"]["merged"]["parent_method_ids"], [self.parent["body"]["method_id"]] * 3)
        self.assertEqual(body["execution"]["completion_hash"], execution["hash"])
        self.assertEqual(body["execution"]["recipe_id"], execution["body"]["recipe_id"])
        for field in ("losses", "source_to_output", "deduplications"):
            self.assertEqual(body["links"][field], {"completion_id": execution["id"], "field": field,
                "sha256": digest(canonical(execution["body"][field]).encode())})
        representation = self.ledger.get(body["outputs"]["merged"]["representation_id"])
        self.assertIsNone(representation["body"]["parent"])
        for parent in body["parents"]:
            self.assertEqual(self.ledger.get(parent["manifest_id"])["hash"], parent["manifest_hash"])

    def test_partition_preserves_single_parent_lineage_and_hashed_view_ids(self):
        execution = self.execute()
        body = self.completed(execution)["body"]
        for view, output in body["outputs"].items():
            suffix = digest(view.encode())
            self.assertEqual(output["representation_id"], f"graph-materialization:materialize:representation:{suffix}")
            self.assertEqual(output["manifest_id"], f"graph-materialization:materialize:manifest:{suffix}")
            representation = self.ledger.get(output["representation_id"])
            self.assertEqual(representation["body"]["parent"], self.parent["body"]["representation_id"])
            self.assertEqual(output["derivation_method"], "graph-derived-v1:" + digest(canonical(body["derivations"][view]).encode()))
        self.assertNotEqual(body["outputs"]["left"]["method_id"], body["outputs"]["right"]["method_id"])

    def test_derived_identity_is_stable_across_instances_but_tracks_recipe_and_parent_multiplicity(self):
        first = self.completed(self.execute("identity", key="first"), key="first")
        clone = self.fixture.parent_for()
        second = self.completed(self.execute("identity", parents=[clone], key="second"), key="second")
        self.assertEqual(first["body"]["outputs"]["output"]["method_id"], second["body"]["outputs"]["output"]["method_id"])
        projected = self.completed(self.execute("project_entities", key="projection"), key="projection")
        self.assertNotEqual(first["body"]["outputs"]["output"]["method_id"], projected["body"]["outputs"]["output"]["method_id"])
        two = self.completed(self.execute("merge", parents=[self.parent, clone], key="two"), key="two")
        three = self.completed(self.execute("merge", parents=[self.parent, clone, self.fixture.parent_for()], key="three"), key="three")
        self.assertEqual(self.ledger.get(two["body"]["outputs"]["merged"]["representation_id"])["body"]["model"],
                         self.ledger.get(three["body"]["outputs"]["merged"]["representation_id"])["body"]["model"])
        self.assertNotEqual(two["body"]["outputs"]["merged"]["method_id"], three["body"]["outputs"]["merged"]["method_id"])

    def test_derived_identity_changes_with_parent_method_even_for_same_graph(self):
        first = self.completed(self.execute("identity", key="first"), key="first")
        other = self.fixture.capture("other-parent-config", b"other parent configuration")["id"]
        self.fixture.snapshot = self.ledger.snapshot()
        parent = self.fixture.parent_for(artifacts={**self.fixture.artifacts, "config": other})
        second = self.completed(self.execute("identity", parents=[parent], key="second"), key="second")
        self.assertNotEqual(first["body"]["outputs"]["output"]["method_id"], second["body"]["outputs"]["output"]["method_id"])

    def test_existing_manifest_forecast_consumer_accepts_derived_records_and_enforces_deadline(self):
        execution = self.execute("project_entities")
        receipt = self.completed(execution)
        mid = receipt["body"]["outputs"]["output"]["manifest_id"]
        cutoff = instant(self.parent["body"]["cutoff"])
        question = self.ledger.question("Will the fictional invoice be paid?", (cutoff + timedelta(seconds=300)).isoformat(),
            (cutoff + timedelta(seconds=600)).isoformat(), "Fictional payment record", "contract_obligation")
        forecast = manifests.forecast_manifest(self.ledger, mid, question["id"], 0.6)
        self.assertEqual(forecast["body"]["representation_id"], receipt["body"]["outputs"]["output"]["representation_id"])
        self.assertEqual(forecast["body"]["method"], receipt["body"]["outputs"]["output"]["method_id"])
        other = self.ledger.question("Another fictional invoice?", (cutoff + timedelta(seconds=300)).isoformat(),
            (cutoff + timedelta(seconds=600)).isoformat(), "Fictional payment record", "contract_obligation")
        self.fixture.now = (cutoff + timedelta(seconds=301)).isoformat()
        with self.assertRaisesRegex(ValueError, "deadline"):
            manifests.forecast_manifest(self.ledger, mid, other["id"], 0.6)

    def test_completion_replay_after_blob_loss_returns_original_but_integrity_and_byte_lookup_fail(self):
        execution = self.execute()
        receipt = self.completed(execution)
        before = self.ledger.events()
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        self.assertEqual(self.materialize(execution), receipt)
        metadata = materialization.get_materialized_outputs(self.ledger, receipt["id"], verify_bytes=False)
        self.assertEqual(metadata["receipt"], receipt)
        with self.assertRaises(ValueError):
            materialization.get_materialized_outputs(self.ledger, receipt["id"])
        self.assertFalse(self.ledger.verify()["valid"])
        self.assertEqual(self.ledger.events(), before)

    def test_changed_request_under_completed_key_refuses_without_events(self):
        first, second = self.execute("identity", key="first"), self.execute("project_entities", key="second")
        self.completed(first)
        before = self.ledger.events()
        with self.assertRaisesRegex(ValueError, "different request"):
            self.materialize(second)
        self.assertEqual(self.ledger.events(), before)

    def test_nonobject_completion_bodies_leave_durable_rejections_and_exact_replay(self):
        pairs = []
        for index, body in enumerate(([], None, "not a completion object")):
            execution = self.ledger.append("graph_transform_completed", body, f"graph-transform:malformed-{index}:terminal")
            receipt = self.rejected(execution, key=f"malformed-{index}", diagnostic="Execution completion body must be an object")
            self.assertEqual(receipt["body"]["error"]["type"], "ValueError")
            self.assertTrue(self.ledger.verify()["valid"])
            pairs.append((execution, receipt, f"malformed-{index}"))
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        before = self.ledger.events()
        for execution, receipt, key in pairs:
            self.assertEqual(self.materialize(execution, key=key), receipt)
        self.assertEqual(self.ledger.events(), before)
        self.assertEqual(len(self.ledger.events("graph_materialization_started")), 3)
        self.assertEqual(len(self.ledger.events("graph_materialization_rejected")), 3)
        self.assertEqual(self.ledger.events("graph_materialization_completed"), [])

    def test_malformed_parent_artifact_container_is_rejected_before_mapping_use(self):
        original = self.execute("identity")
        parent_body = deepcopy(self.parent["body"])
        parent_body["artifacts"] = []
        malformed = self.ledger.append("representation_manifest", parent_body, "malformed-parent")
        def replace_parent(body):
            body["request"]["parent_manifest"] = {"id": malformed["id"], "hash": malformed["hash"]}
        execution = self.synthetic_execution(original, key="bad-parent-artifacts", change=replace_parent)
        receipt = self.rejected(execution, diagnostic="parent manifest artifact roles")
        before = self.ledger.events()
        self.assertEqual(self.materialize(execution), receipt)
        self.assertEqual(self.ledger.events(), before)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_nonobject_recipe_observations_are_durably_rejected_and_replay_after_blob_loss(self):
        original = self.execute("identity")
        pairs = []
        for index, bad_body in enumerate(([], None, "not an observation object")):
            malformed = self.ledger.append("observation", bad_body, f"malformed-recipe-{index}")
            def replace_recipe(body):
                body["request"]["recipe"] = {"observation_id": malformed["id"], "event_hash": malformed["hash"], "content_hash": "0" * 64}
            execution = self.synthetic_execution(original, key=f"malformed-recipe-{index}", change=replace_recipe)
            receipt = self.rejected(execution, key=f"recipe-{index}", diagnostic="Recipe observation body must be an object")
            self.assertEqual(receipt["body"]["error"]["type"], "ValueError")
            pairs.append((execution, receipt, f"recipe-{index}"))
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        before = self.ledger.events()
        for execution, receipt, key in pairs:
            self.assertEqual(self.materialize(execution, key=key), receipt)
        self.assertEqual(self.ledger.events(), before)
        self.assertEqual(len(self.ledger.events("graph_materialization_started")), 3)
        self.assertEqual(len(self.ledger.events("graph_materialization_rejected")), 3)
        self.assertEqual(self.ledger.events("graph_materialization_completed"), [])
        self.assertFalse(self.ledger.db.in_transaction)

    def test_nonobject_parent_artifact_evidence_and_cost_observations_have_replayable_rejections(self):
        original = self.execute("identity")
        for field in ("artifacts", "evidence", "cost_receipts"):
            for index, bad_body in enumerate(([], None, "not an observation object")):
                key = f"parent-{field}-{index}"
                malformed = self.ledger.append("observation", bad_body, key + "-observation")
                reference = {"observation_id": malformed["id"], "event_hash": malformed["hash"], "content_hash": "0" * 64}
                parent_body = deepcopy(self.parent["body"])
                if field == "artifacts":
                    parent_body[field]["construction"] = reference
                else:
                    parent_body[field] = [reference]
                parent = self.ledger.append("representation_manifest", parent_body, key + "-manifest")
                def replace_parent(body):
                    body["request"]["parent_manifest"] = {"id": parent["id"], "hash": parent["hash"]}
                execution = self.synthetic_execution(original, key=key, change=replace_parent)
                receipt = self.rejected(execution, key=key, diagnostic="Parent observation body must be an object")
                before = self.ledger.events()
                self.assertEqual(self.materialize(execution, key=key), receipt)
                self.assertEqual(self.ledger.events(), before)
        self.assertEqual(len(self.ledger.events("graph_materialization_rejected")), 9)
        self.assertFalse(self.ledger.db.in_transaction)

    def test_parent_cost_cannot_hide_an_unchecked_observation_outside_receipt_refs(self):
        original = self.execute("identity")
        malformed = self.ledger.append("observation", [], "hidden-cost-observation")
        parent_body = deepcopy(self.parent["body"])
        parent_body["construction_cost"] = {"basis": "reported", "elapsed_seconds": 1, "model_calls": None,
            "external_spend": None, "currency": None, "receipt_ids": [malformed["id"]]}
        self.assertEqual(parent_body["cost_receipts"], [])
        parent = self.ledger.append("representation_manifest", parent_body, "hidden-cost-parent")
        def replace_parent(body):
            body["request"]["parent_manifest"] = {"id": parent["id"], "hash": parent["hash"]}
        execution = self.synthetic_execution(original, key="hidden-cost", change=replace_parent)
        receipt = self.rejected(execution, diagnostic="Parent cost receipt references do not match declared IDs")
        before = self.ledger.events()
        self.assertEqual(self.materialize(execution), receipt)
        self.assertEqual(self.ledger.events(), before)

    def test_nonobject_recipe_config_code_and_dependency_observations_have_replayable_rejections(self):
        original = self.execute("identity")
        recipe_blob = self.ledger.root / "blobs" / self.transform_recipes["identity"]["body"]["content_hash"]
        recipe_body = json.loads(recipe_blob.read_bytes())
        cases = []
        # Capture valid recipes/snapshots before appending intentionally malformed
        # observation events; no legitimate collector ever creates those bodies.
        for role in ("config", "implementation", "dependency"):
            for index, bad_body in enumerate(([], None, "not an observation object")):
                key = f"recipe-{role}-{index}"
                observation_id = key + "-observation"
                recipe = deepcopy(recipe_body)
                if role == "dependency":
                    recipe["dependency_observations"]["epiphysics.store"] = observation_id
                else:
                    recipe[role + "_observation_id"] = observation_id
                retained = self.fixture.capture(key, canonical(recipe).encode())
                parent = self.fixture.fresh_parent()
                cases.append((key, observation_id, bad_body, retained, parent))
        for key, observation_id, bad_body, recipe, parent in cases:
            self.ledger.append("observation", bad_body, observation_id)
            def replace_request(body):
                body["request"] = transforms._request_metadata(self.ledger, parent["id"], recipe["id"])
            execution = self.synthetic_execution(original, key=key, change=replace_request)
            receipt = self.rejected(execution, key=key, diagnostic="Recipe artifact observation body must be an object")
            before = self.ledger.events()
            self.assertEqual(self.materialize(execution, key=key), receipt)
            self.assertEqual(self.ledger.events(), before)
        self.assertEqual(len(self.ledger.events("graph_materialization_rejected")), 9)
        self.assertFalse(self.ledger.db.in_transaction)

    def test_rejected_replay_survives_blob_loss_without_retrying_failed_execution(self):
        source = self.execute("identity")
        fake = self.synthetic_execution(source, key="old-contract", change=lambda body: body["request"]["implementation"]["dependencies"].update({"epiphysics.store": "0" * 64}))
        rejected = self.rejected(fake, diagnostic="Execution contract differs")
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        before = self.ledger.events()
        self.assertEqual(self.materialize(fake), rejected)
        self.assertEqual(self.ledger.events(), before)

    def test_recomputation_rejects_tampered_output_loss_or_ancestry_even_with_valid_event_hash(self):
        source = self.execute("project_entities")
        def output_change(body):
            body["output_model"]["entities"][0]["amount"]["value"] += 1
            body["output_model_hash"] = digest(canonical(body["output_model"]).encode())
        for index, change in enumerate((output_change, lambda body: body["losses"].update(removed_relations=[]),
                                        lambda body: body["source_to_output"].update(entities={}))):
            fake = self.synthetic_execution(source, key=f"forged-{index}", change=change)
            self.rejected(fake, key=f"reject-{index}", diagnostic="fixed recomputation")

    def test_missing_output_view_is_rejected_instead_of_materializing_partial_set(self):
        source = self.execute()
        fake = self.synthetic_execution(source, key="missing-view", change=lambda body: body["outputs"].pop("right"))
        self.rejected(fake, diagnostic="fixed recomputation")

    def test_failure_after_first_manifest_rolls_back_all_outputs_and_other_reader_sees_none(self):
        execution = self.execute()
        reader = Ledger(self.ledger.root, clock=lambda: self.fixture.now)
        original_reps, original_manifests = reader.events("representation"), reader.events("representation_manifest")
        append = self.ledger.append
        staged_manifests = []
        def fail_second_representation(kind, body, event_id=None, **options):
            if kind == "representation" and staged_manifests:
                self.assertEqual(reader.events("representation"), original_reps)
                self.assertEqual(reader.events("representation_manifest"), original_manifests)
                raise ValueError("injected failure after first manifest")
            result = append(kind, body, event_id, **options)
            if kind == "representation_manifest":
                staged_manifests.append(result)
            return result
        try:
            with patch.object(self.ledger, "append", side_effect=fail_second_representation):
                self.rejected(execution, diagnostic="injected failure")
            self.assertEqual(len(staged_manifests), 1)
            self.assertEqual(reader.events("representation"), original_reps)
            self.assertEqual(reader.events("representation_manifest"), original_manifests)
            self.assertTrue(self.ledger.verify()["valid"])
        finally:
            reader.close()

    def test_second_reader_observes_whole_bundle_only_after_completion_commit(self):
        execution = self.execute()
        reader = Ledger(self.ledger.root, clock=lambda: self.fixture.now)
        original_reps = len(reader.events("representation"))
        original_manifests = len(reader.events("representation_manifest"))
        append = self.ledger.append
        observed = []
        def observe(kind, body, event_id=None, **options):
            result = append(kind, body, event_id, **options)
            if kind in ("representation", "representation_manifest", "graph_materialization_completed"):
                observed.append(kind)
                self.assertEqual(len(reader.events("representation")), original_reps)
                self.assertEqual(len(reader.events("representation_manifest")), original_manifests)
                self.assertEqual(reader.events("graph_materialization_completed"), [])
            return result
        try:
            with patch.object(self.ledger, "append", side_effect=observe):
                receipt = self.completed(execution)
            self.assertEqual(len(observed), 5)
            self.assertEqual(len(reader.events("representation")), original_reps + 2)
            self.assertEqual(len(reader.events("representation_manifest")), original_manifests + 2)
            self.assertEqual(reader.get(receipt["id"]), receipt)
        finally:
            reader.close()

    def test_completion_boundary_evidence_and_config_mutation_roll_back_all_rows(self):
        execution = self.execute()
        targets = [execution["body"]["inputs"]["config"]["observation_id"], self.fixture.evidence["c"]["id"]]
        append = self.ledger.append
        for index, oid in enumerate(targets):
            observation = self.ledger.get(oid)
            path = self.ledger.root / "blobs" / observation["body"]["content_hash"]
            raw = path.read_bytes()
            def corrupt(kind, body, event_id=None, **options):
                if kind == "graph_materialization_completed":
                    path.write_bytes(raw + b"changed before completion")
                return append(kind, body, event_id, **options)
            with patch.object(self.ledger, "append", side_effect=corrupt):
                self.rejected(execution, key=f"boundary-{index}", diagnostic="hash or size mismatch")
            path.write_bytes(raw)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_corrupt_terminal_output_binding_is_rejected_and_entire_group_rolls_back(self):
        execution = self.execute()
        append = self.ledger.append
        def corrupt(kind, body, event_id=None, **options):
            if kind == "graph_materialization_completed":
                body["outputs"]["left"]["model_hash"] = "0" * 64
            return append(kind, body, event_id, **options)
        with patch.object(self.ledger, "append", side_effect=corrupt):
            self.rejected(execution, diagnostic="hash binding mismatch")
        self.assertTrue(self.ledger.verify()["valid"])

    def test_orphan_output_id_refuses_without_adopting_or_overwriting_it(self):
        execution = self.execute()
        rid, _ = materialization._output_ids("materialize", "left")
        orphan = self.ledger.append("orphan-test", {"synthetic": True}, rid)
        self.rejected(execution, diagnostic="already exist without a completed bundle")
        self.assertEqual(self.ledger.get(rid), orphan)

    def test_interruption_rolls_back_output_rows_and_leaves_diagnostic_start(self):
        execution = self.execute()
        reps, manifest_rows = self.ledger.events("representation"), self.ledger.events("representation_manifest")
        append = self.ledger.append
        def interrupt(kind, body, event_id=None, **options):
            if kind == "graph_materialization_completed":
                raise KeyboardInterrupt("simulated interrupted process")
            return append(kind, body, event_id, **options)
        with patch.object(self.ledger, "append", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
            self.materialize(execution)
        self.assertEqual(self.ledger.events("representation"), reps)
        self.assertEqual(self.ledger.events("representation_manifest"), manifest_rows)
        self.assertEqual(len(self.ledger.events("graph_materialization_started")), 1)
        self.assertEqual(self.ledger.events("graph_materialization_completed"), [])
        self.assertEqual(self.ledger.events("graph_materialization_rejected"), [])
        self.assertFalse(self.ledger.db.in_transaction)
        with self.assertRaisesRegex(ValueError, "requires diagnosis"):
            self.materialize(execution)

    def test_concurrent_materializations_claim_once_and_return_one_bundle(self):
        execution = self.execute()
        barrier = threading.Barrier(2)
        outcomes = []
        def worker():
            ledger = Ledger(self.ledger.root, clock=lambda: self.fixture.now)
            try:
                barrier.wait(timeout=5)
                outcomes.append(materialization.materialize_graph_outputs(ledger, execution["id"], run_key="race"))
            except ValueError:
                outcomes.append("in-flight refusal")
            finally:
                ledger.close()
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 2)
        successes = [x for x in outcomes if isinstance(x, dict)]
        self.assertGreaterEqual(len(successes), 1)
        self.assertTrue(all(x == successes[0] for x in successes))
        self.assertEqual(successes[0]["kind"], "graph_materialization_completed")
        self.assertEqual(len(self.ledger.events("graph_materialization_started")), 1)
        self.assertEqual(len(self.ledger.events("graph_materialization_completed")), 1)
        self.assertTrue(self.ledger.verify()["valid"])

    def test_invalid_inputs_and_existing_transaction_refuse_before_claim(self):
        execution = self.execute()
        before = self.ledger.events()
        for key in ("", "bad key", "x" * 101, True):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.materialize(execution, key=key)
        for completion_id in ("x" * 513, "é" * 257, self.parent["id"], "missing"):
            with self.subTest(completion_id=completion_id), self.assertRaises(ValueError):
                materialization.materialize_graph_outputs(self.ledger, completion_id, run_key="invalid")
        self.ledger.db.execute("BEGIN")
        try:
            with self.assertRaisesRegex(ValueError, "standalone"):
                self.materialize(execution)
            self.assertTrue(self.ledger.db.in_transaction)
        finally:
            self.ledger.db.rollback()
        self.assertEqual(self.ledger.events(), before)

    def test_large_parent_descriptor_is_rejected_before_output_expansion(self):
        parent = self.fixture.parent_for(units={"amount": "u" * 17_000})
        execution = self.execute("identity", parents=[parent])
        self.rejected(execution, diagnostic="Parent method descriptor exceeds")

    def test_repeated_evidence_metadata_budget_refuses_before_any_output_rows(self):
        evidence = [self.fixture.capture(f"budget-source-{i}", f"Synthetic source {i}".encode())["id"] for i in range(500)]
        entity_ids = [f"entity-{i}" for i in range(64)]
        model = {"entities": [{"id": eid, "basis": "reported", "evidence_ids": [evidence[0]]} for eid in entity_ids],
                 "relations": [], "context": {"evidence_ids": evidence}}
        recipe = self.fixture.recipe("partition_entities", {"views": {eid: [eid] for eid in entity_ids}})
        parent = self.fixture.fresh_parent(model)
        execution = graph_views.execute_graph_views(self.ledger, [parent["id"]], recipe["id"], run_key="many-views")
        self.assertEqual(execution["kind"], "graph_views_completed", execution)
        self.assertLess(sum(len(canonical(row["model"]).encode()) for row in execution["body"]["outputs"].values()), 2_000_000)
        with patch.object(self.ledger, "representation", side_effect=AssertionError("must reject before output writes")) as represent:
            self.rejected(execution, diagnostic="Materialized output records exceeds")
            represent.assert_not_called()
        self.assertTrue(self.ledger.verify()["valid"])

    def test_incremental_metadata_budget_counts_multibyte_bytes_and_stops_without_joining(self):
        self.assertEqual(materialization._bounded_size({"x": "é"}, 10, "fixture"), 10)
        with self.assertRaisesRegex(ValueError, "fixture exceeds"):
            materialization._bounded_size({"x": "é"}, 9, "fixture")
        with self.assertRaisesRegex(ValueError, "fixture exceeds"):
            materialization._bounded_size({"x": "a" * 100_000}, 1000, "fixture")


if __name__ == "__main__":
    unittest.main()
