from copy import deepcopy
import json
from pathlib import Path
import unittest

from epiphysics.representation_checks import (
    DIMENSIONS,
    FAMILIES,
    degraded_candidate,
    evaluate,
    reference_candidate,
    validate_suite,
)
from epiphysics.store import canonical


FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "improvement" / "entities.json"


def small_suite():
    return {"schema_version": 1, "cases": [{
        "id": "one", "family": "software_service", "description": "Synthetic contract.",
        "cutoff": "2030-01-07T12:00:00Z",
        "observations": [
            {"id": "first", "recorded_at": "2030-01-06T00:00:00Z"},
            {"id": "second", "recorded_at": "2030-01-07T12:00:00Z"},
            {"id": "other", "recorded_at": "2030-01-07T11:00:00Z"},
            {"id": "late", "recorded_at": "2030-01-07T12:00:01Z"},
        ],
        "checks": [{"id": "query", "dimension": "identity", "expected": {"count": 1},
                    "evidence_ids": ["first", "second"]}],
    }]}


class RepresentationChecksTests(unittest.TestCase):
    def setUp(self):
        self.suite = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_diversity_and_oracle_conformance(self):
        validate_suite(self.suite)
        self.assertEqual({case["family"] for case in self.suite["cases"]}, FAMILIES)
        self.assertEqual({check["dimension"] for case in self.suite["cases"] for check in case["checks"]}, DIMENSIONS)
        for case in self.suite["cases"]:
            self.assertGreaterEqual(len(case["checks"]), 3)
            self.assertIn("Synthetic fictional", case["description"])
        report = evaluate(self.suite, reference_candidate(self.suite))
        self.assertEqual(report["metrics"], {
            "checks": 30, "correct": 30, "answered": 30, "provenance_correct": 30,
            "temporal_violations": 0, "accuracy": 1, "coverage": 1, "provenance": 1,
            "worst_family_accuracy": 1, "macro_family_accuracy": 1,
        })
        for case in report["cases"]:
            self.assertEqual(case["metrics"]["correct"], case["metrics"]["checks"])
            self.assertEqual(case["metrics"]["answered"], case["metrics"]["checks"])
            self.assertEqual(case["metrics"]["provenance_correct"], case["metrics"]["checks"])
        self.assertIn("oracle positive control, not a learned model", report["interpretation"])

    def test_degraded_control_loses_direction_units_and_provenance(self):
        before = canonical(self.suite)
        candidate = degraded_candidate(self.suite)
        report = evaluate(self.suite, candidate)
        self.assertEqual(report["metrics"]["coverage"], 1)
        self.assertLess(report["metrics"]["accuracy"], 1)
        self.assertLess(report["metrics"]["provenance"], 1)
        self.assertLess(report["metrics"]["worst_family_accuracy"], 1)
        self.assertLess(report["metrics"]["macro_family_accuracy"], 1)
        self.assertEqual(report["dimensions"]["relation_direction"]["correct"], 0)
        self.assertEqual(report["dimensions"]["units"]["correct"], 0)
        self.assertEqual(canonical(candidate), canonical(degraded_candidate(self.suite)))
        self.assertEqual(canonical(self.suite), before)

    def test_controls_are_independent_deep_copies(self):
        before = canonical(self.suite)
        first = reference_candidate(self.suite)
        second = reference_candidate(self.suite)
        first["cases"][0]["answers"][0]["value"]["entity_ids"].append("pollution")
        first["cases"][0]["answers"][0]["evidence_ids"].clear()
        degraded = degraded_candidate(self.suite)
        degraded["cases"][0]["answers"][0]["value"]["entity_ids"].clear()
        self.assertEqual(canonical(self.suite), before)
        self.assertEqual(second, reference_candidate(self.suite))

    def test_wrong_answer_is_scored_without_losing_coverage_or_evidence_credit(self):
        suite = small_suite()
        candidate = reference_candidate(suite)
        candidate["cases"][0]["answers"][0]["value"] = {"count": 7}
        metrics = evaluate(suite, candidate)["metrics"]
        self.assertEqual(metrics["correct"], 0)
        self.assertEqual(metrics["answered"], 1)
        self.assertEqual(metrics["provenance_correct"], 1)

    def test_fixture_detects_specific_semantic_losses(self):
        losses = [
            ("relay-services", "dependency-direction", lambda v: dict(v, source=v["target"], target=v["source"])),
            ("relay-services", "parallel-service-relations", lambda v: v[:1]),
            ("relay-services", "scope-homonymous-services", lambda v: dict(v, same_entity=True)),
            ("aster-boundaries", "preserve-owner-dispute", lambda v: dict(v, alternatives=v["alternatives"][:1], resolution="resolved")),
            ("mira-roles", "expired-approval-role", lambda v: dict(v, authorized_at_cutoff=True)),
            ("invoice-obligation", "currency-and-scale", lambda v: dict(v, currency="USD")),
            ("invoice-obligation", "settlement-idempotency-authority", lambda v: dict(v, settlement_count=2, authorized_role="any-employee")),
            ("harbor-collective", "membership-over-time", lambda v: dict(v, known_person_members=["person:jun", "person:mira-a"])),
            ("competing-representations", "representation-versus-referent", lambda v: dict(v, same_entity=True)),
        ]
        for case_id, query_id, lose in losses:
            with self.subTest(case=case_id, query=query_id):
                candidate = reference_candidate(self.suite)
                case = next(case for case in candidate["cases"] if case["id"] == case_id)
                answer = next(answer for answer in case["answers"] if answer["check_id"] == query_id)
                answer["value"] = lose(answer["value"])
                report = evaluate(self.suite, candidate)
                self.assertEqual(report["metrics"]["correct"], 29)
                self.assertEqual(report["metrics"]["answered"], 30)
                self.assertEqual(report["metrics"]["provenance_correct"], 30)

    def test_canonical_json_equality_is_strict_and_object_order_independent(self):
        suite = small_suite()
        suite["cases"][0]["checks"][0]["expected"] = {"count": 1, "active": True}
        for value in ({"active": 1, "count": 1}, {"active": True, "count": True}, {"active": True, "count": 1.0}):
            with self.subTest(value=value):
                candidate = reference_candidate(suite)
                candidate["cases"][0]["answers"][0]["value"] = value
                self.assertEqual(evaluate(suite, candidate)["metrics"]["correct"], 0)
        candidate["cases"][0]["answers"][0]["value"] = {"active": True, "count": 1}
        self.assertEqual(evaluate(suite, candidate)["metrics"]["correct"], 1)

    def test_nonfinite_and_non_json_values_are_malformed(self):
        for value in (float("nan"), float("inf"), float("-inf"), (1, 2), {1: "numeric-key"}):
            with self.subTest(value=value):
                suite = small_suite()
                candidate = reference_candidate(suite)
                candidate["cases"][0]["answers"][0]["value"] = {"nested": value}
                with self.assertRaises(ValueError):
                    evaluate(suite, candidate)
                suite["cases"][0]["checks"][0]["expected"] = {"nested": value}
                with self.assertRaises(ValueError):
                    validate_suite(suite)

    def test_missing_answers_and_cases_keep_the_declared_denominator(self):
        candidate = reference_candidate(self.suite)
        del candidate["cases"][0]["answers"][0]
        metrics = evaluate(self.suite, candidate)["metrics"]
        self.assertEqual((metrics["checks"], metrics["answered"], metrics["correct"]), (30, 29, 29))
        self.assertEqual(metrics["coverage"], 29 / 30)
        candidate["cases"].pop(0)
        metrics = evaluate(self.suite, candidate)["metrics"]
        self.assertEqual((metrics["checks"], metrics["answered"]), (30, 25))
        report = evaluate(self.suite, {"schema_version": 1, "cases": []})
        for field in ("correct", "answered", "provenance_correct", "temporal_violations", "accuracy", "coverage", "provenance", "macro_family_accuracy", "worst_family_accuracy"):
            self.assertEqual(report["metrics"][field], 0)
        self.assertEqual(set(report["families"]), FAMILIES)

    def test_exact_provenance_sets_ignore_order_but_not_missing_or_extra_evidence(self):
        suite = small_suite()
        candidate = reference_candidate(suite)
        candidate["cases"][0]["answers"][0]["evidence_ids"].reverse()
        self.assertEqual(evaluate(suite, candidate)["metrics"]["correct"], 1)
        for evidence in ([], ["first"], ["first", "second", "other"], ["other"]):
            with self.subTest(evidence=evidence):
                candidate["cases"][0]["answers"][0]["evidence_ids"] = evidence
                report = evaluate(suite, candidate)
                result = report["cases"][0]["checks"][0]
                self.assertTrue(result["value_correct"])
                self.assertFalse(result["provenance_correct"])
                self.assertFalse(result["correct"])
                self.assertEqual(result["missing_evidence_ids"], sorted({"first", "second"} - set(evidence)))
                self.assertEqual(result["unexpected_evidence_ids"], sorted(set(evidence) - {"first", "second"}))

    def test_late_evidence_contamination_fails_even_when_answer_is_correct(self):
        suite = small_suite()
        suite["cases"][0]["observations"].append({"id": "later", "recorded_at": "2030-01-08T00:00:00Z"})
        candidate = reference_candidate(suite)
        candidate["cases"][0]["answers"][0]["evidence_ids"] += ["late", "later"]
        report = evaluate(suite, candidate)
        self.assertEqual(report["metrics"]["temporal_violations"], 1)  # Checks, not evidence rows.
        self.assertEqual(report["metrics"]["correct"], 0)
        result = report["cases"][0]["checks"][0]
        self.assertTrue(result["value_correct"])
        self.assertEqual(result["late_evidence_ids"], ["late", "later"])

    def test_cutoff_is_inclusive_and_compares_instants(self):
        suite = small_suite()
        suite["cases"][0]["cutoff"] = "2030-01-07T04:00:00-08:00"
        suite["cases"][0]["observations"][1]["recorded_at"] = "2030-01-07T13:00:00+01:00"
        self.assertEqual(evaluate(suite, reference_candidate(suite))["metrics"]["correct"], 1)

    def test_unknown_cases_queries_and_evidence_reject_extra_work(self):
        for target in ("case", "check", "evidence"):
            with self.subTest(target=target):
                suite = small_suite()
                candidate = reference_candidate(suite)
                if target == "case":
                    candidate["cases"].append({"id": "invented", "answers": []})
                elif target == "check":
                    candidate["cases"][0]["answers"].append({"check_id": "invented", "value": 1, "evidence_ids": ["first"]})
                else:
                    candidate["cases"][0]["answers"][0]["evidence_ids"].append("invented")
                with self.assertRaisesRegex(ValueError, "Unknown"):
                    evaluate(suite, candidate)

    def test_case_local_evidence_cannot_be_borrowed_from_another_case(self):
        candidate = reference_candidate(self.suite)
        candidate["cases"][0]["answers"][0]["evidence_ids"] = ["charter"]
        with self.assertRaisesRegex(ValueError, "Unknown answer evidence"):
            evaluate(self.suite, candidate)

    def test_duplicate_candidate_cases_answers_or_evidence_are_rejected(self):
        for target in ("case", "answer", "evidence"):
            with self.subTest(target=target):
                suite = small_suite()
                candidate = reference_candidate(suite)
                if target == "case":
                    candidate["cases"].append(deepcopy(candidate["cases"][0]))
                elif target == "answer":
                    candidate["cases"][0]["answers"] *= 2
                else:
                    candidate["cases"][0]["answers"][0]["evidence_ids"].append("first")
                with self.assertRaisesRegex(ValueError, "Duplicate"):
                    evaluate(suite, candidate)

    def test_invalid_reference_obligations_fail_before_scoring(self):
        for evidence in ([], ["unknown"], ["late"], ["first", "first"]):
            with self.subTest(evidence=evidence):
                suite = small_suite()
                suite["cases"][0]["checks"][0]["evidence_ids"] = evidence
                with self.assertRaises(ValueError):
                    validate_suite(suite)
                with self.assertRaises(ValueError):
                    evaluate(suite, {"schema_version": 1, "cases": []})

    def test_duplicate_reference_identifiers_are_rejected(self):
        for target in ("cases", "checks", "observations"):
            with self.subTest(target=target):
                suite = small_suite()
                rows = suite["cases"] if target == "cases" else suite["cases"][0][target]
                rows.append(deepcopy(rows[0]))
                with self.assertRaisesRegex(ValueError, "Duplicate"):
                    validate_suite(suite)

    def test_malformed_schema_and_timestamps_are_rejected(self):
        mutations = [
            lambda s: s.update(schema_version=True),
            lambda s: s.update(extra="unsupported"),
            lambda s: s.update(cases=[]),
            lambda s: s["cases"][0].update(family="unknown"),
            lambda s: s["cases"][0].update(description=" "),
            lambda s: s["cases"][0].update(checks=[]),
            lambda s: s["cases"][0].update(observations=[]),
            lambda s: s["cases"][0]["checks"][0].update(dimension="unknown"),
            lambda s: s["cases"][0].update(cutoff="2030-01-07T12:00:00"),
            lambda s: s["cases"][0].update(cutoff="not-a-timestamp"),
            lambda s: s["cases"][0]["observations"][0].update(recorded_at="2030-01-06"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                suite = small_suite()
                mutate(suite)
                with self.assertRaises(ValueError):
                    validate_suite(suite)
        suite = small_suite()
        for mutation in ("version", "missing_evidence", "extra_field", "bad_value"):
            with self.subTest(mutation=mutation):
                candidate = reference_candidate(suite)
                if mutation == "version":
                    candidate["schema_version"] = True
                elif mutation == "missing_evidence":
                    del candidate["cases"][0]["answers"][0]["evidence_ids"]
                elif mutation == "extra_field":
                    candidate["cases"][0]["answers"][0]["confidence"] = 0.5
                else:
                    candidate["cases"][0]["answers"][0]["value"] = object()
                with self.assertRaises(ValueError):
                    evaluate(suite, candidate)

    def test_hard_collection_bounds(self):
        for target in ("cases", "checks", "observations"):
            with self.subTest(target=target):
                suite = small_suite()
                if target == "cases":
                    suite["cases"] *= 101
                else:
                    suite["cases"][0][target] = [suite["cases"][0][target][0]] * 101
                with self.assertRaises(ValueError):
                    validate_suite(suite)
        suite = small_suite()
        candidate = reference_candidate(suite)
        candidate["cases"][0]["answers"] *= 101
        with self.assertRaises(ValueError):
            evaluate(suite, candidate)

    def test_macro_accuracy_weights_families_and_family_accuracy_weights_checks(self):
        suite = small_suite()
        larger_case = deepcopy(suite["cases"][0])
        larger_case.update(id="two", family="organization")
        larger_case["checks"] = [dict(deepcopy(larger_case["checks"][0]), id=f"query-{i}") for i in range(3)]
        suite["cases"].append(larger_case)
        candidate = reference_candidate(suite)
        candidate["cases"][0]["answers"][0]["value"] = "wrong"
        report = evaluate(suite, candidate)
        self.assertEqual(report["metrics"]["accuracy"], 0.75)
        self.assertEqual(report["metrics"]["macro_family_accuracy"], 0.5)
        self.assertEqual(report["metrics"]["worst_family_accuracy"], 0)
        suite["cases"][1]["family"] = "software_service"
        report = evaluate(suite, candidate)
        self.assertEqual(report["families"], {"software_service": {"checks": 4, "correct": 3, "accuracy": 0.75}})
        self.assertEqual(report["metrics"]["macro_family_accuracy"], 0.75)

    def test_candidate_order_does_not_change_report_or_inputs(self):
        candidate = reference_candidate(self.suite)
        expected = evaluate(self.suite, candidate)
        candidate["cases"].reverse()
        for case in candidate["cases"]:
            case["answers"].reverse()
            for answer in case["answers"]:
                answer["evidence_ids"].reverse()
        suite_before, candidate_before = canonical(self.suite), canonical(candidate)
        self.assertEqual(evaluate(self.suite, candidate), expected)
        self.assertEqual(canonical(self.suite), suite_before)
        self.assertEqual(canonical(candidate), candidate_before)


if __name__ == "__main__":
    unittest.main()
