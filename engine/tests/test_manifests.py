from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from epiphysics import manifests
from epiphysics.store import Ledger, canonical, digest, instant


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = "2030-01-01T00:00:00Z"
        self.ledger = Ledger(Path(self.temp.name) / "ledger", clock=lambda: self.now)
        self.data = self.ledger.capture("synthetic:invoice", b"A owes 12 USD.")
        self.context = self.ledger.capture("synthetic:context", b"A is a service.")
        self.artifact_bytes = {"construction": b"# declared constructor v1\n", "config": b'{"threshold":3}',
                               "ontology": b'{"relation":"owes"}', "predictor": b"# declared constant predictor v1\n"}
        self.artifacts = {role: self.ledger.capture(f"synthetic:{role}", raw)["id"]
                          for role, raw in self.artifact_bytes.items()}
        self.snapshot = self.ledger.snapshot()
        self.model = {"entities": [{"id": "A", "basis": "reported", "evidence_ids": [self.data["id"]]}], "relations": []}
        self.representation = self.represent()
        self.task = {"id": "invoice-paid-v1", "family": "contract_obligation", "outcome_type": "binary"}

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def represent(self, *, snapshot=None, model=None, observer="fixture-observer", method="fixture-constructor-v1"):
        return self.ledger.representation((snapshot or self.snapshot)["id"], deepcopy(self.model if model is None else model),
                                          observer=observer, method=method)

    def register(self, **changes):
        representation = changes.pop("representation", self.representation)
        arguments = {"encoding": "directed-graph", "schema_id": "synthetic-graph-v1", "artifacts": deepcopy(self.artifacts),
                     "task": deepcopy(self.task), "horizon_seconds": 600, "units": {"invoice": "USD"},
                     "evidence_ids": [self.data["id"]], "construction_cost": None}
        arguments.update(changes)
        return manifests.register_manifest(self.ledger, representation["id"], **arguments)

    def question(self, *, snapshot=None, horizon=600, family="contract_obligation"):
        cutoff = instant((snapshot or self.snapshot)["body"]["cutoff"])
        return self.ledger.question("Will the fictional invoice be paid?", (cutoff + timedelta(seconds=300)).isoformat(),
            (cutoff + timedelta(seconds=horizon)).isoformat(), "Synthetic payment record.", family)

    def reported_cost(self, **changes):
        return {"basis": "reported", "elapsed_seconds": 1.25, "model_calls": 0, "external_spend": 0,
                "currency": "USD", "receipt_ids": [], **changes}

    def rejected_without_append(self, operation, pattern=None):
        before = len(self.ledger.events())
        with self.assertRaisesRegex(ValueError, pattern) if pattern else self.assertRaises(ValueError):
            operation()
        self.assertEqual(before, len(self.ledger.events()))

    def test_manifest_binds_exact_representation_snapshot_artifacts_and_units(self):
        event = self.register()
        body = event["body"]
        self.assertEqual(event["kind"], "representation_manifest")
        self.assertEqual(body["representation_id"], self.representation["id"])
        self.assertEqual(body["representation_hash"], self.representation["hash"])
        self.assertEqual(body["model_hash"], digest(canonical(self.model).encode()))
        self.assertEqual(body["snapshot_id"], self.snapshot["id"])
        self.assertEqual(body["snapshot_hash"], self.snapshot["hash"])
        self.assertEqual(body["snapshot_manifest_hash"], self.snapshot["body"]["manifest_hash"])
        self.assertEqual(body["descriptor"]["units"], {"invoice": "USD"})
        self.assertEqual(body["observer"], "fixture-observer")
        self.assertEqual(body["method_id"], manifests.method_identity(body["descriptor"]))
        for role, ref in body["artifacts"].items():
            self.assertEqual(ref["observation_id"], self.artifacts[role])
            self.assertEqual(ref["content_hash"], digest(self.artifact_bytes[role]))
        self.assertEqual([ref["observation_id"] for ref in body["evidence"]], [self.data["id"]])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_method_identity_survives_new_snapshot_model_payload_recapture_and_cost(self):
        first = self.register()
        self.now = "2030-01-01T00:01:00Z"
        self.data = self.ledger.capture("synthetic:invoice", b"A now owes 13 USD.")
        self.artifacts = {role: self.ledger.capture(f"synthetic:recaptured:{role}", raw)["id"]
                          for role, raw in self.artifact_bytes.items()}
        self.snapshot = self.ledger.snapshot()
        model = {"text": "Different representation payload", "evidence_ids": [self.data["id"]]}
        self.representation = self.represent(model=model)
        second = self.register(construction_cost=self.reported_cost())
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(first["body"]["snapshot_id"], second["body"]["snapshot_id"])
        self.assertNotEqual(first["body"]["model_hash"], second["body"]["model_hash"])
        self.assertNotEqual(first["body"]["artifacts"], second["body"]["artifacts"])
        self.assertEqual(first["body"]["method_id"], second["body"]["method_id"])

    def test_different_encodings_sharing_predictor_have_distinct_methods(self):
        graph = self.register()
        text = self.register(encoding="text")
        self.assertEqual(graph["body"]["artifacts"]["predictor"], text["body"]["artifacts"]["predictor"])
        self.assertNotEqual(graph["body"]["method_id"], text["body"]["method_id"])

    def test_each_artifact_content_change_changes_method_identity(self):
        baseline = self.register()["body"]["method_id"]
        for role in manifests.ARTIFACT_ROLES:
            with self.subTest(role=role):
                changed = self.ledger.capture(f"synthetic:changed:{role}", self.artifact_bytes[role] + b" changed")
                snapshot = self.ledger.snapshot()
                representation = self.represent(snapshot=snapshot)
                result = self.register(representation=representation, artifacts={**self.artifacts, role: changed["id"]})
                self.assertNotEqual(result["body"]["method_id"], baseline)

    def test_semantic_descriptor_changes_change_identity_and_key_order_does_not(self):
        body = self.register()["body"]
        descriptor = body["descriptor"]
        variants = [{"schema_id": "v2"}, {"construction_method": "constructor-v2"}, {"observer": "other"},
                    {"task": {**self.task, "id": "task-v2"}}, {"task": {**self.task, "family": "other"}},
                    {"horizon_seconds": 601}, {"units": {"invoice": "EUR"}}]
        for change in variants:
            with self.subTest(change=change):
                self.assertNotEqual(manifests.method_identity({**descriptor, **change}), body["method_id"])
        reordered = dict(reversed(list(descriptor.items())))
        reordered["artifact_hashes"] = dict(reversed(list(descriptor["artifact_hashes"].items())))
        self.assertEqual(manifests.method_identity(reordered), body["method_id"])
        with self.assertRaises(ValueError):
            manifests.method_identity({**descriptor, "snapshot_id": self.snapshot["id"]})

    def test_declared_evidence_matches_all_explicit_model_references_exactly(self):
        self.rejected_without_append(lambda: self.register(evidence_ids=[]), "exactly equal")
        self.rejected_without_append(lambda: self.register(evidence_ids=[self.data["id"], self.context["id"]]), "exactly equal")
        self.rejected_without_append(lambda: self.register(evidence_ids=[self.data["id"]] * 2), "Duplicate")
        model = deepcopy(self.model)
        model["metadata"] = {"text_context": {"evidence_ids": [self.context["id"]]}}
        representation = self.represent(model=model)
        self.rejected_without_append(lambda: self.register(representation=representation), "exactly equal")
        event = self.register(representation=representation, evidence_ids=[self.context["id"], self.data["id"]])
        self.assertEqual({ref["observation_id"] for ref in event["body"]["evidence"]}, {self.data["id"], self.context["id"]})

    def test_missing_unknown_and_wrong_kind_artifacts_are_rejected(self):
        self.rejected_without_append(lambda: self.register(artifacts={"construction": self.artifacts["construction"]}))
        for oid in ("missing", self.snapshot["id"], self.representation["id"]):
            with self.subTest(oid=oid):
                self.rejected_without_append(lambda: self.register(artifacts={**self.artifacts, "config": oid}))

    def test_late_artifacts_cannot_use_publication_dates_to_enter_earlier_snapshot(self):
        self.now = "2030-01-01T00:01:00Z"
        late = self.ledger.capture("synthetic:late-config", b"new config", published_at="2000-01-01T00:00:00Z")
        self.rejected_without_append(lambda: self.register(artifacts={**self.artifacts, "config": late["id"]}), "selected snapshot")

    def test_ineligible_evidence_in_raw_representation_event_is_rejected(self):
        self.now = "2030-01-01T00:01:00Z"
        late = self.ledger.capture("synthetic:late-evidence", b"late source")
        body = deepcopy(self.representation["body"])
        body["model"]["entities"][0]["evidence_ids"] = [late["id"]]
        forged = self.ledger.append("representation", body)
        self.rejected_without_append(lambda: self.register(representation=forged, evidence_ids=[late["id"]]), "selected snapshot")

    def test_corrupted_artifact_and_evidence_bytes_are_rejected_without_manifest(self):
        for oid in (self.artifacts["construction"], self.data["id"]):
            with self.subTest(oid=oid):
                observation = self.ledger.get(oid)
                path = self.ledger.root / "blobs" / observation["body"]["content_hash"]
                original = path.read_bytes()
                path.write_bytes(original + b"corruption")
                self.rejected_without_append(lambda: self.register(), "hash or size")
                path.write_bytes(original)

    def test_missing_and_symlinked_artifact_bytes_are_rejected(self):
        observation = self.ledger.get(self.artifacts["ontology"])
        path = self.ledger.root / "blobs" / observation["body"]["content_hash"]
        raw = path.read_bytes()
        path.unlink()
        self.rejected_without_append(lambda: self.register(), "missing")
        target = Path(self.temp.name) / "same-content"
        target.write_bytes(raw)
        path.symlink_to(target)
        self.rejected_without_append(lambda: self.register(), "symlink")

    def test_snapshot_manifest_event_and_content_hash_binding_are_verified(self):
        original = deepcopy(self.snapshot["body"])
        for field in ("manifest_hash", "event_hash", "content_hash"):
            with self.subTest(field=field):
                body = deepcopy(original)
                if field == "manifest_hash":
                    body[field] = "0" * 64
                else:
                    entry = next(entry for entry in body["observations"] if entry["id"] == self.data["id"])
                    entry[field] = "0" * 64
                    body["manifest_hash"] = digest(canonical(body["observations"]).encode())
                forged = self.ledger.append("snapshot", body)
                representation = self.represent(snapshot=forged)
                self.rejected_without_append(lambda: self.register(representation=representation))

    def test_blob_change_between_preparation_and_write_is_checked_under_lock(self):
        append = self.ledger.append
        path = self.ledger.root / "blobs" / digest(self.artifact_bytes["predictor"])

        def changed_before_append(kind, body, event_id=None, **options):
            path.write_bytes(b"changed after manifest preparation")
            return append(kind, body, event_id, **options)

        with patch.object(self.ledger, "append", side_effect=changed_before_append):
            self.rejected_without_append(lambda: self.register(), "hash or size")

    def test_unknown_cost_is_not_fabricated_as_zero(self):
        event = self.register()
        cost = event["body"]["construction_cost"]
        self.assertEqual(cost, {"basis": "unknown", "elapsed_seconds": None, "model_calls": None,
                                "external_spend": None, "currency": None, "receipt_ids": []})
        q = self.question()
        forecast = manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.5)
        self.assertEqual(forecast["body"]["cost"]["inference_cost"], cost)

    def test_reported_cost_receipts_can_postdate_cutoff_and_remain_bound(self):
        baseline = self.register()
        self.now = "2030-01-01T00:01:00Z"
        receipt = self.ledger.capture("synthetic:construction-receipt", b"reported 1.25 seconds; zero calls")
        cost = self.reported_cost(receipt_ids=[receipt["id"]])
        event = self.register(construction_cost=cost)
        self.assertEqual(event["body"]["construction_cost"], cost)
        self.assertEqual(event["body"]["cost_receipts"][0]["event_hash"], receipt["hash"])
        self.assertEqual(event["body"]["method_id"], baseline["body"]["method_id"])
        self.assertNotIn(receipt["id"], [ref["observation_id"] for ref in event["body"]["evidence"]])
        q = self.question()
        forecast = manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.5, inference_cost=cost)
        self.assertEqual(forecast["body"]["cost"]["construction_manifest_id"], event["id"])
        self.assertEqual(forecast["body"]["cost"]["receipt_refs"][0]["content_hash"], receipt["body"]["content_hash"])

    def test_cost_schema_rejects_nonfinite_negative_bool_and_unbacked_unknown_labels(self):
        variants = [{"elapsed_seconds": float("nan")}, {"elapsed_seconds": -1}, {"elapsed_seconds": True},
                    {"model_calls": 1.5}, {"model_calls": True}, {"model_calls": -1},
                    {"external_spend": float("inf")}, {"external_spend": -1}, {"currency": None},
                    {"external_spend": None}, {"basis": "unknown"}, {"basis": "verified-execution"},
                    {"receipt_ids": ["missing"]}]
        for variant in variants:
            with self.subTest(variant=variant):
                self.rejected_without_append(lambda: self.register(construction_cost=self.reported_cost(**variant)))

    def test_semantic_schema_types_and_descriptor_versions_are_strict(self):
        variants = [{"encoding": ""}, {"schema_id": ""}, {"horizon_seconds": True}, {"horizon_seconds": 0},
                    {"horizon_seconds": 1.0}, {"units": {"invoice": 1}}, {"units": {1: "USD"}},
                    {"task": {**self.task, "outcome_type": "continuous"}}, {"task": {**self.task, "extra": "ignored"}}]
        for variant in variants:
            with self.subTest(variant=variant):
                self.rejected_without_append(lambda: self.register(**variant))
        descriptor = self.register()["body"]["descriptor"]
        with self.assertRaises(ValueError):
            manifests.method_identity({**descriptor, "schema_version": True})

    def test_bound_forecast_uses_stable_method_and_instance_metadata(self):
        event = self.register()
        q = self.question()
        forecast = manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.7)
        body = forecast["body"]
        self.assertEqual(body["method"], event["body"]["method_id"])
        self.assertEqual(body["snapshot_id"], self.snapshot["id"])
        self.assertEqual(body["representation_id"], self.representation["id"])
        self.assertEqual(body["model"]["representation_manifest_id"], event["id"])
        self.assertEqual(body["model"]["representation_manifest_hash"], event["hash"])
        self.assertEqual(body["model"]["identifier"], "sha256:" + digest(self.artifact_bytes["predictor"]))

    def test_question_family_horizon_and_invalid_probability_cannot_be_bypassed(self):
        event = self.register()
        for q in (self.question(family="other"), self.question(horizon=601)):
            self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.5))
        q = self.question()
        for probability in (True, -0.1, 1.1, float("nan")):
            self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, event["id"], q["id"], probability))
        self.now = "2030-01-01T00:05:00Z"
        self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.5), "deadline")

    def test_failed_and_abstained_attempts_keep_reason_and_unknown_cost(self):
        event = self.register()
        for status in ("failed", "abstained"):
            q = self.question()
            forecast = manifests.forecast_manifest(self.ledger, event["id"], q["id"], None, status=status, reason="synthetic unavailable result")
            self.assertEqual(forecast["body"]["status"], status)
            self.assertIsNone(forecast["body"]["probability"])
            self.assertEqual(forecast["body"]["cost"]["inference_cost"]["basis"], "unknown")
        summary = self.ledger.scores()["methods"][event["body"]["method_id"]]
        self.assertEqual((summary["failed"], summary["abstained"], summary["coverage"]), (1, 1, 0))

    def test_forged_manifest_binding_and_later_artifact_corruption_reject_forecast(self):
        event = self.register()
        q = self.question()
        for key in ("method_id", "representation_hash", "model_hash", "snapshot_manifest_hash"):
            body = deepcopy(event["body"])
            body[key] = "0" * 64
            forged = self.ledger.append("representation_manifest", body)
            self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, forged["id"], q["id"], 0.5))
        path = self.ledger.root / "blobs" / digest(self.artifact_bytes["predictor"])
        path.write_bytes(b"different predictor bytes")
        self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.5), "hash or size")

    def test_manifest_and_forecast_idempotent_retries_survive_deadline_and_resolution(self):
        event = self.register(event_id="manifest-retry")
        q = self.question()
        forecast = manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.7, event_id="forecast-retry")
        self.now = "2030-01-01T00:11:00Z"
        outcome = self.ledger.capture("synthetic:outcome", b"paid")
        self.ledger.resolve(q["id"], 1, [outcome["id"]], explanation="Synthetic outcome")
        before = len(self.ledger.events())
        self.assertEqual(self.register(event_id="manifest-retry"), event)
        self.assertEqual(manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.7, event_id="forecast-retry"), forecast)
        self.assertEqual(before, len(self.ledger.events()))
        self.rejected_without_append(lambda: self.register(event_id="manifest-retry", encoding="changed"), "different content")
        self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.6, event_id="forecast-retry"), "different content")

    def test_all_mutable_inputs_are_revalidated_at_forecast_append(self):
        construction_receipt = self.ledger.capture("synthetic:construction-cost", b"construction cost report")
        inference_receipt = self.ledger.capture("synthetic:inference-cost", b"inference cost report")
        event = self.register(construction_cost=self.reported_cost(receipt_ids=[construction_receipt["id"]]))
        inference_cost = self.reported_cost(receipt_ids=[inference_receipt["id"]])
        q = self.question()
        original_forecast = self.ledger.forecast
        targets = [*self.artifacts.values(), self.data["id"], construction_receipt["id"], inference_receipt["id"]]
        for oid in targets:
            with self.subTest(observation=oid):
                observation = self.ledger.get(oid, "observation")
                path = self.ledger.root / "blobs" / observation["body"]["content_hash"]
                original_bytes = path.read_bytes()

                def changed_before_forecast(*arguments, **keywords):
                    path.write_bytes(original_bytes + b"changed after preflight")
                    return original_forecast(*arguments, **keywords)

                with patch.object(self.ledger, "forecast", side_effect=changed_before_forecast):
                    self.rejected_without_append(lambda: manifests.forecast_manifest(
                        self.ledger, event["id"], q["id"], 0.7, inference_cost=inference_cost), "hash or size")
                path.write_bytes(original_bytes)
        self.assertEqual(self.ledger.events("forecast"), [])

    def test_exact_forecast_replay_survives_all_blob_loss_but_changed_replay_does_not(self):
        construction_receipt = self.ledger.capture("synthetic:construction-cost", b"construction receipt")
        inference_receipt = self.ledger.capture("synthetic:inference-cost", b"inference receipt")
        cost = self.reported_cost(receipt_ids=[inference_receipt["id"]])
        event = self.register(construction_cost=self.reported_cost(receipt_ids=[construction_receipt["id"]]))
        alternate = self.register(encoding="text")
        q, fresh_question = self.question(), self.question()
        forecast = manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.7,
            inference_cost=cost, event_id="surviving-replay")
        for path in (self.ledger.root / "blobs").iterdir():
            path.unlink()
        before = len(self.ledger.events())
        replay = manifests.forecast_manifest(self.ledger, event["id"], q["id"], 0.7,
            inference_cost=cost, event_id="surviving-replay")
        self.assertEqual(replay, forecast)
        self.assertEqual(len(self.ledger.events()), before)
        for manifest_id, probability, replay_cost in (
            (event["id"], 0.6, cost),
            (event["id"], 0.7, {**cost, "elapsed_seconds": 2}),
            (alternate["id"], 0.7, cost),
        ):
            with self.subTest(manifest=manifest_id, probability=probability, cost=replay_cost):
                self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, manifest_id,
                    q["id"], probability, inference_cost=replay_cost, event_id="surviving-replay"), "different content")
        self.rejected_without_append(lambda: manifests.forecast_manifest(self.ledger, event["id"],
            fresh_question["id"], 0.7, inference_cost=cost, event_id="new-attempt"), "missing")

    def test_same_methods_compare_across_two_matched_snapshot_question_pairs(self):
        method_pairs = []
        questions = []
        for round_number in range(2):
            if round_number:
                self.now = "2030-01-01T00:01:00Z"
                self.snapshot = self.ledger.snapshot()
                self.representation = self.represent()
            graph, text = self.register(), self.register(encoding="text")
            q = self.question()
            questions.append(q)
            for event, probability in ((graph, 0.7), (text, 0.5)):
                manifests.forecast_manifest(self.ledger, event["id"], q["id"], probability)
            method_pairs.append((graph["body"]["method_id"], text["body"]["method_id"]))
        self.assertEqual(method_pairs[0], method_pairs[1])
        self.now = "2030-01-01T00:12:00Z"
        outcome = self.ledger.capture("synthetic:outcome", b"both fictional invoices paid")
        for q in questions:
            self.ledger.resolve(q["id"], 1, [outcome["id"]], explanation="Synthetic matched outcome")
        comparison = self.ledger.compare(*method_pairs[0])
        self.assertEqual(comparison["matched"], 2)
        self.assertAlmostEqual(comparison["right_minus_left_brier"], 0.16)
        self.assertEqual(len(self.ledger.scores()["methods"]), 2)

    def test_concurrent_instances_of_same_method_cannot_duplicate_question_attempt(self):
        first, second = self.register(), self.register()
        self.assertEqual(first["body"]["method_id"], second["body"]["method_id"])
        q = self.question()
        barrier = threading.Barrier(2)
        outcomes = []

        def worker(event, probability):
            ledger = Ledger(self.ledger.root, clock=lambda: self.now)
            try:
                barrier.wait(timeout=5)
                manifests.forecast_manifest(ledger, event["id"], q["id"], probability)
                outcomes.append("recorded")
            except ValueError as error:
                outcomes.append(str(error))
            finally:
                ledger.close()

        threads = [threading.Thread(target=worker, args=(event, probability)) for event, probability in ((first, 0.5), (second, 0.7))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(outcomes.count("recorded"), 1)
        self.assertEqual(sum("already attempted" in outcome for outcome in outcomes), 1)
        self.assertEqual(len(self.ledger.events("forecast")), 1)

    def test_caller_mutations_do_not_rewrite_manifest(self):
        units = {"invoice": "USD"}
        task = deepcopy(self.task)
        cost = self.reported_cost()
        event = self.register(units=units, task=task, construction_cost=cost)
        units["invoice"] = "EUR"
        task["family"] = "other"
        cost["external_spend"] = 100
        self.assertEqual(self.ledger.get(event["id"]), event)


if __name__ == "__main__":
    unittest.main()
