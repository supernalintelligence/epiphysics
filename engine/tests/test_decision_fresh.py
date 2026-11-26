"""Small owned generator controls; never instantiate a registered 24-case batch.

No test calls generate, runs a candidate, writes a seed file or reads fresh private
evidence. Distinct public unit seeds below are test constants, not custody seeds.
Full generation, output reservation and failure receipt integration need review
before the separate custodian's single post-freeze generation.
"""
import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

from epiphysics import decision_evaluation as evaluation


PATH = Path(__file__).resolve().parents[1] / "examples" / "control-exchange" / "fresh-generator.py"
SPEC = importlib.util.spec_from_file_location("owned_fresh_generator_control", PATH)
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


def owned_case(mechanism, variant, seed_byte):
    case = generator.build_case(bytes([seed_byte]) * 32, mechanism, variant)
    evaluation.resolve_world(case)  # Schema and private facts only, no scoring.
    return case


class DecisionFreshGeneratorTests(unittest.TestCase):
    def test_static_allocation_and_no_candidate_import(self):
        self.assertEqual(generator.ALLOCATION, {"late_visibility": 6, "visible_authority_changes": 4,
            "verification_dispute": 4, "duplicate_identity": 4, "retention_pressure": 4, "role_direction": 2})
        self.assertEqual(sum(generator.ALLOCATION.values()), 24)
        tree = ast.parse(PATH.read_text())
        engine_imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                          and node.module and node.module.startswith("epiphysics")]
        self.assertEqual([(node.module, [name.name for name in node.names]) for node in engine_imports],
                         [("epiphysics", ["decision_evaluation"])])

    def test_seed_format_exact_and_no_implicit_seed(self):
        self.assertEqual(generator.parse_seed(b"ab" * 32), bytes.fromhex("ab" * 32))
        self.assertEqual(generator.parse_seed(b"ab" * 32 + b"\n"), bytes.fromhex("ab" * 32))
        for invalid in (b"", b"ab" * 31, b"AB" * 32, b"ab" * 32 + b"\n\n", b" " + b"ab" * 32,
                        b"ab" * 32 + b"\r\n", "ab" * 32):
            with self.subTest(invalid=repr(invalid)), self.assertRaises(ValueError):
                generator.parse_seed(invalid)
        for seed in (None, b"", b"a" * 31, "a" * 32):
            with self.assertRaises(ValueError):
                generator.build_case(seed, "late_visibility", 0)

    def test_individual_case_determinism_and_actual_task_variation(self):
        first = owned_case("late_visibility", 1, 11)
        same = owned_case("late_visibility", 1, 11)
        other = owned_case("late_visibility", 1, 12)
        self.assertEqual(first, same)
        self.assertNotEqual(first["task"]["amount"], other["task"]["amount"])
        self.assertNotEqual(first["decision_at"], other["decision_at"])
        self.assertFalse(first["later_outcome"]["artifact_valid"])
        world = evaluation.resolve_world(first)
        self.assertTrue(world["world_authorized"])
        self.assertFalse(world["artifact_ready_valid"])
        self.assertEqual(generator.case_truth(first)["not_ready_or_invalid_cases"], 1)

    def test_invalid_mechanism_variant_and_boolean_refused(self):
        for mechanism, variant in (("other", 0), ("late_visibility", -1), ("late_visibility", 6),
                                   ("role_direction", 2), ("role_direction", True)):
            with self.assertRaises(ValueError):
                generator.build_case(b"z" * 32, mechanism, variant)

    def test_hidden_regrant_restores_world_but_not_available_opportunity(self):
        case = owned_case("late_visibility", 2, 21)
        self.assertTrue(evaluation.resolve_world(case)["world_opportunity"])
        self.assertEqual(generator.case_truth(case)["visible_actionable_opportunities"], 0)
        hidden = next(event for event in case["events"] if event["event_id"] == "hidden-regrant")
        self.assertLess(hidden["effective_at"], case["decision_at"])
        self.assertGreater(hidden["observed_at"], case["cutoff"])

    def test_scoped_tie_keeps_second_grant_and_future_reference_is_inert(self):
        tied = owned_case("visible_authority_changes", 0, 31)
        future_target = owned_case("visible_authority_changes", 2, 32)
        self.assertEqual(evaluation.resolve_world(tied)["active_grant_ids"], ["grant-b"])
        self.assertEqual(evaluation.resolve_world(future_target)["active_grant_ids"], ["future-target"])

    def test_dispute_close_before_open_is_not_authority(self):
        case = owned_case("verification_dispute", 0, 41)
        self.assertEqual(evaluation.resolve_world(case)["open_dispute_ids"], ["later-open"])
        self.assertFalse(evaluation.resolve_world(case)["world_authorized"])

    def test_two_independent_disputes_close_but_artifact_can_be_invalid(self):
        case = owned_case("verification_dispute", 1, 42)
        world = evaluation.resolve_world(case)
        self.assertEqual(world["open_dispute_ids"], [])
        self.assertTrue(world["world_authorized"])
        self.assertFalse(world["artifact_ready_valid"])

    def test_tied_and_future_closes_leave_current_disputes_open(self):
        tied = owned_case("verification_dispute", 2, 43)
        future = owned_case("verification_dispute", 3, 44)
        self.assertEqual(evaluation.resolve_world(tied)["open_dispute_ids"], ["tied-open"])
        self.assertEqual(evaluation.resolve_world(future)["open_dispute_ids"], ["current-open"])
        self.assertFalse(evaluation.resolve_world(tied)["decision_within_deadline"])
        self.assertFalse(evaluation.resolve_world(future)["artifact_ready_valid"])

    def test_new_attempt_id_does_not_change_existing_release_key(self):
        first = owned_case("duplicate_identity", 0, 51)
        retry = owned_case("duplicate_identity", 1, 51)
        self.assertNotEqual(first["attempt_id"], retry["attempt_id"])
        self.assertEqual(first["task"], retry["task"])
        self.assertEqual(first["events"], retry["events"])
        self.assertTrue(evaluation.resolve_world(first)["world_duplicate"])
        self.assertEqual(evaluation.compute_release_key(first["task"]), evaluation.compute_release_key(retry["task"]))

    def test_old_amount_and_future_release_do_not_mark_current_key_duplicate(self):
        case = owned_case("duplicate_identity", 3, 52)
        self.assertFalse(evaluation.resolve_world(case)["world_duplicate"])
        self.assertTrue(evaluation.resolve_world(case)["world_opportunity"])

    def test_pressure_structures_remain_bounded_without_running_views(self):
        distant = owned_case("retention_pressure", 0, 61)
        nearby = owned_case("retention_pressure", 2, 62)
        for case in (distant, nearby):
            self.assertEqual(len(case["events"]), 15)
            self.assertEqual(len({event["event_id"] for event in case["events"]}), 15)
            self.assertTrue(evaluation.resolve_world(case)["world_opportunity"])
            self.assertLess(len(generator.canonical(case)), 32768)
        seeds = {distant["task"]["delegate"], distant["task"]["artifact_id"]}
        self.assertTrue(all({event["subject"], event["object"]}.isdisjoint(seeds)
                            for event in distant["events"] if event["kind"] == "note"))
        self.assertTrue(all({event["subject"], event["object"]} == {nearby["task"]["delegate"], nearby["task"]["artifact_id"]}
                            for event in nearby["events"] if event["kind"] == "note"))

    def test_reversed_grants_do_not_authorize(self):
        case = owned_case("role_direction", 0, 71)
        self.assertFalse(evaluation.resolve_world(case)["world_authorized"])

    def test_serialized_byte_limit_includes_lf_and_utf8(self):
        value = {"owned": "é"}
        raw = generator.canonical(value) + b"\n"
        self.assertEqual(generator.bounded_json(value, len(raw)), raw)
        with self.assertRaises(ValueError):
            generator.bounded_json(value, len(raw) - 1)
        with self.assertRaises(ValueError):
            generator.bounded_json({"owned": "x" * generator.MAX_COHORT_BYTES}, generator.MAX_COHORT_BYTES)

    def test_registration_shape_limits_and_exact_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory).resolve()
            outputs = {name: str(directory / name) for name in generator.OUTPUT_NAMES}
            outputs["journal"] = outputs["report"] + ".attempts.jsonl"
            hashes = dict.fromkeys(generator.SOURCE_NAMES, "a" * 64)
            registration = {"schema_version": 1, "registration_id": "owned-schema-control", "phase": "fresh_comparison",
                "cohort_id": generator.COHORT_ID, "allocation": dict(generator.ALLOCATION),
                "origin": {"event_id": "owned-predecessor", "event_hash": "b" * 64, "artifact_sha256": "c" * 64,
                    "assessment_hash": "d" * 64, "decision_assessment_hash": "e" * 64,
                    "implementation_hashes": {name: hashes[name] for name in generator.SOURCE_NAMES[:6]}},
                "source_hashes": hashes, "contract_hashes": {"decision_contract": "f" * 64, "evaluation_contract": "0" * 64},
                "limits": deepcopy(generator.LIMITS), "triage": deepcopy(generator.TRIAGE), "outputs": outputs,
                "execution_id": "owned-schema-only", "frozen_at": "2020-01-01T00:00:00Z"}
            generator.validate_registration(registration, outputs["cohort"], outputs["custody"])
            for mutate in (lambda item: item["limits"].update(program_seconds=31),
                           lambda item: item["allocation"].update(late_visibility=7),
                           lambda item: item.update(schema_version=True),
                           lambda item: item["outputs"].update(report=outputs["cohort"]),
                           lambda item: item["source_hashes"].update({"decision_policy.py": "1" * 64}),
                           lambda item: item.update(extra="not allowed")):
                invalid = deepcopy(registration)
                mutate(invalid)
                with self.assertRaises(ValueError):
                    generator.validate_registration(invalid, outputs["cohort"], outputs["custody"])


if __name__ == "__main__":
    unittest.main()
