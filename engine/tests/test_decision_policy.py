"""Owned unit fixtures, not preparation/final-cohort performance execution."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import unittest

from epiphysics.decision_policy import decide_release_hold
from epiphysics.decision_views import (
    VerifiedPolicyInput,
    build_decision_view,
    prepare_decision_input,
    validate_decode_view,
)


CONTRACT = "control-exchange-release-hold-v1"
BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)
TASK = {"obligation_id": "obligation", "requester": "requester", "delegate": "delegate",
        "provider": "provider", "artifact_id": "artifact", "artifact_sha256": "a" * 64,
        "amount": 1, "unit": "simulation_credit", "deadline": "2020-01-01T00:15:00Z"}
POLICY_KINDS = {"grant", "revoke", "delivery_claim", "verification", "dispute_open",
                "dispute_close", "release_committed"}


def at(value):
    return (BASE + timedelta(seconds=value)).strftime("%Y-%m-%dT%H:%M:%SZ")


def independent_key(task):
    raw = json.dumps([CONTRACT, task["obligation_id"], task["artifact_sha256"],
                      task["provider"], task["amount"], task["unit"]],
                     ensure_ascii=False, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()


def event(kind, identity, when, *, task=None, **changes):
    task = TASK if task is None else task
    requester, delegate, provider = task["requester"], task["delegate"], task["provider"]
    artifact, obligation = task["artifact_id"], task["obligation_id"]
    roles = {"grant": (requester, requester, delegate), "revoke": (requester, requester, delegate),
             "delivery_claim": (provider, provider, artifact), "verification": (requester, requester, artifact),
             "dispute_open": (requester, requester, obligation), "dispute_close": (requester, requester, obligation),
             "release_committed": (requester, delegate, provider), "note": (provider, delegate, artifact)}
    issuer, subject, object_id = roles[kind]
    return {"event_id": identity, "kind": kind, "issuer": issuer, "subject": subject, "object": object_id,
            "obligation_id": obligation, "effective_at": at(when), "observed_at": at(min(when, 550)),
            "reference": independent_key(task) if kind == "release_committed" else None,
            "artifact_sha256": task["artifact_sha256"] if kind in ("delivery_claim", "verification", "release_committed") else None,
            "verdict": "pass" if kind == "verification" else None,
            "authentication": "verified", **changes}


def baseline(task=None):
    return [event("grant", "g", 100, task=task), event("delivery_claim", "d", 200, task=task),
            event("verification", "v", 300, task=task)]


def verified(events, *, task=None, complete=True, eligible=None, cutoff=600):
    """Stand in for the already validated decoder result in policy unit tests.

    Provenance corruption belongs to decision_views tests; these inputs contain
    only hand-authored retained events and no annotations or outcome objects.
    """
    task = deepcopy(TASK if task is None else task)
    retained = sum(item["kind"] in POLICY_KINDS for item in events)
    return VerifiedPolicyInput(
        header={"schema_version": 1, "contract_id": CONTRACT, "time_origin": at(0),
                "task": task, "cutoff": at(cutoff), "decision_at": at(cutoff)},
        events=tuple(deepcopy(events)), complete=complete,
        eligible_policy_count=retained if eligible is None else eligible,
        retained_policy_count=retained, input_hash="0" * 64, source_hash="1" * 64)


class DecisionPolicyTests(unittest.TestCase):
    def assert_reason(self, events, reason, **kwargs):
        result = decide_release_hold(verified(events, **kwargs))
        self.assertEqual(result["action"], "release" if reason == "release_requirements_satisfied" else "hold")
        self.assertEqual(result["reason"], reason)
        self.assertEqual(result["release_key"], independent_key(kwargs.get("task") or TASK))
        self.assertEqual(result["support_event_ids"], sorted(item["event_id"] for item in events if item["kind"] in POLICY_KINDS))
        return result

    def test_complete_evidence_is_deterministic_and_does_not_mutate_input(self):
        source = verified(baseline())
        before = deepcopy(source)
        result = decide_release_hold(source)
        self.assertEqual(result, {"action": "release", "reason": "release_requirements_satisfied",
                                  "release_key": independent_key(TASK), "support_event_ids": ["d", "g", "v"]})
        self.assertEqual(result, decide_release_hold(source))
        self.assertEqual(source, before)
        self.assertEqual(result, decide_release_hold(replace(source, events=tuple(reversed(source.events)))))

    def test_real_decoder_handoff_and_late_record_exclusion_for_both_views(self):
        public = prepare_decision_input(baseline(), TASK, at(600), at(600))
        with_late = prepare_decision_input(
            baseline() + [event("revoke", "late-revoke", 500, observed_at=at(700), reference="g")],
            TASK, at(600), at(600))
        self.assertEqual(public, with_late)
        outputs = []
        for recipe in ("flat-recency-v1", "task-proximity-v1"):
            raw = build_decision_view(public["header_bytes"], public["event_tape_bytes"], recipe=recipe)
            decoded = validate_decode_view(public["header_bytes"], public["event_tape_bytes"], raw)
            self.assertTrue(decoded.complete)
            self.assertEqual(decoded.input_hash, public["input_hash"])
            outputs.append(decide_release_hold(decoded))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0]["action"], "release")
        self.assertEqual(outputs[0]["support_event_ids"], ["d", "g", "v"])

    def test_authority_order_uses_effective_time_not_observation_recency(self):
        records = baseline()
        records[0]["observed_at"] = at(500)
        records.append(event("revoke", "r", 200, observed_at=at(300), reference="g"))
        self.assert_reason(records, "authority_absent_or_revoked")

    def test_grants_are_a_set_with_exact_named_null_stale_and_future_scope(self):
        required = baseline()[1:]
        cases = [
            ([event("grant", "g1", 100), event("grant", "g2", 200), event("revoke", "r", 300, reference="g1")], True),
            ([event("grant", "g1", 100), event("grant", "g2", 200), event("revoke", "r", 300, reference="g2")], True),
            ([event("grant", "g1", 100), event("grant", "g2", 200), event("revoke", "r", 300)], False),
            ([event("grant", "g1", 100), event("revoke", "r", 200), event("grant", "g2", 300)], True),
            ([event("grant", "g1", 100), event("revoke", "r1", 200, reference="g1"), event("grant", "g2", 250),
              event("revoke", "r2", 300, reference="g1")], True),
            ([event("revoke", "r", 90, reference="g1"), event("grant", "g1", 100)], True),
            ([event("grant", "g1", 100), event("revoke", "r", 300, reference="missing")], True),
            ([event("grant", "g1", 100), event("revoke", "r", 300, reference="d")], True),
            ([event("grant", "g1", 100), event("revoke", "r", 300, reference="r")], True),
        ]
        for records, release in cases:
            with self.subTest(records=[(item["event_id"], item["reference"]) for item in records]):
                self.assert_reason(required + list(reversed(records)),
                                   "release_requirements_satisfied" if release else "authority_absent_or_revoked")

    def test_revoke_ties_process_grants_first_without_expanding_named_scope(self):
        required = baseline()[1:]
        grants = [event("grant", "z-g1", 100), event("grant", "z-g2", 100)]
        for reference, release in [("z-g1", True), (None, False)]:
            with self.subTest(reference=reference):
                self.assert_reason(required + [event("revoke", "a-revoke", 100, reference=reference)] + grants,
                                   "release_requirements_satisfied" if release else "authority_absent_or_revoked")
        self.assert_reason(required + [grants[0], event("revoke", "a-revoke", 100, reference="z-g1")],
                           "authority_absent_or_revoked")

    def test_references_to_foreign_or_unverified_grants_cannot_remove_valid_grant(self):
        for changes in ({"issuer": "foreign"}, {"subject": "delegate", "object": "requester"},
                        {"authentication": "invalid"}):
            with self.subTest(changes=changes):
                self.assert_reason(baseline() + [event("grant", "foreign-grant", 200, **changes),
                                                event("revoke", "r", 400, reference="foreign-grant")],
                                   "release_requirements_satisfied")

    def test_future_effective_evidence_cannot_satisfy_or_block_current_decision(self):
        cases = [
            ([event("grant", "g", 700)] + baseline()[1:], "authority_absent_or_revoked"),
            ([baseline()[0], event("delivery_claim", "d", 700), baseline()[2]], "missing_delivery"),
            (baseline()[:2] + [event("verification", "v", 700)], "missing_verification"),
            (baseline() + [event("revoke", "r", 700)], "release_requirements_satisfied"),
            (baseline() + [event("verification", "future-fail", 700, verdict="fail")], "release_requirements_satisfied"),
            (baseline() + [event("delivery_claim", "future-wrong", 700, artifact_sha256="b" * 64)], "release_requirements_satisfied"),
            (baseline() + [event("dispute_open", "future-open", 700)], "release_requirements_satisfied"),
            (baseline() + [event("release_committed", "future-paid", 700)], "release_requirements_satisfied"),
            (baseline() + [event("verification", "future-unknown", 700, authentication="unknown")], "release_requirements_satisfied"),
        ]
        for records, reason in cases:
            with self.subTest(reason=reason, last=records[-1]["event_id"]):
                self.assert_reason(records, reason)

    def test_effective_and_observed_cutoffs_are_inclusive(self):
        self.assert_reason(baseline()[:2] + [event("verification", "v", 600, observed_at=at(600))],
                           "release_requirements_satisfied")
        self.assert_reason(baseline() + [event("revoke", "r", 600, observed_at=at(600))],
                           "authority_absent_or_revoked")
        with self.assertRaisesRegex(ValueError, "beyond the evidence cutoff"):
            decide_release_hold(verified(baseline() + [event("revoke", "hidden", 500, observed_at=at(601))]))

    def test_unknown_bound_operative_authentication_always_requires_hold(self):
        for kind in POLICY_KINDS:
            with self.subTest(kind=kind):
                reference = "unresolved" if kind == "dispute_close" else None
                extra = event(kind, "unknown", 400, authentication="unknown")
                if kind == "dispute_close":
                    extra["reference"] = reference
                if kind in ("delivery_claim", "verification", "release_committed"):
                    extra["artifact_sha256"] = "b" * 64
                self.assert_reason(baseline() + [extra], "uncertain_authentication")

    def test_invalid_authentication_is_inert_for_negative_evidence_and_releases(self):
        extras = [event("revoke", "invalid-revoke", 400, authentication="invalid"),
                  event("verification", "invalid-fail", 400, verdict="fail", authentication="invalid"),
                  event("delivery_claim", "invalid-digest", 400, artifact_sha256="b" * 64, authentication="invalid"),
                  event("dispute_open", "invalid-open", 400, authentication="invalid"),
                  event("release_committed", "invalid-paid", 400, authentication="invalid")]
        self.assert_reason(baseline() + extras, "release_requirements_satisfied")
        for index, reason in [(0, "authority_absent_or_revoked"), (1, "missing_delivery"), (2, "missing_verification")]:
            records = baseline()
            records[index]["authentication"] = "invalid"
            with self.subTest(index=index):
                self.assert_reason(records, reason)

    def test_wrong_role_bindings_neither_authorize_nor_create_conflict_or_uncertainty(self):
        for index, reason in [(0, "authority_absent_or_revoked"), (1, "missing_delivery"), (2, "missing_verification")]:
            for field in ("issuer", "subject", "object", "obligation_id"):
                records = baseline()
                records[index][field] = "foreign"
                with self.subTest(index=index, field=field):
                    self.assert_reason(records, reason)
        for kind in ("revoke", "verification", "dispute_open", "release_committed"):
            for authentication in ("verified", "unknown"):
                with self.subTest(kind=kind, authentication=authentication):
                    extra = event(kind, "foreign", 400, issuer="foreign", authentication=authentication)
                    if kind == "verification":
                        extra["verdict"] = "fail"
                    self.assert_reason(baseline() + [extra], "release_requirements_satisfied")
        self.assert_reason([event("grant", "g", 100, subject="delegate", object="requester")] + baseline()[1:],
                           "authority_absent_or_revoked")

    def test_role_renaming_preserves_action_without_special_identifier_values(self):
        task = {**TASK, "requester": "owner-k", "delegate": "worker-z", "provider": "vendor-j",
                "obligation_id": "obligation-m", "artifact_id": "artifact-q"}
        self.assert_reason(baseline(task), "release_requirements_satisfied", task=task)
        records = baseline(task)
        records[0]["subject"], records[0]["object"] = records[0]["object"], records[0]["subject"]
        self.assert_reason(records, "authority_absent_or_revoked", task=task)

    def test_deadline_is_inclusive_and_does_not_override_authority_precedence(self):
        self.assert_reason(baseline(), "release_requirements_satisfied", task={**TASK, "deadline": at(600)})
        self.assert_reason(baseline(), "deadline_expired", task={**TASK, "deadline": at(599)})
        self.assert_reason(baseline()[1:], "authority_absent_or_revoked", task={**TASK, "deadline": at(599)})

    def test_prior_release_requires_exact_key_digest_direction_and_binding(self):
        self.assert_reason(baseline() + [event("release_committed", "paid", 400)], "duplicate_release")
        for changes in ({"reference": "b" * 64}, {"artifact_sha256": "b" * 64}, {"issuer": "provider"},
                        {"subject": "provider", "object": "delegate"}, {"obligation_id": "foreign"}):
            with self.subTest(changes=changes):
                self.assert_reason(baseline() + [event("release_committed", "paid", 400, **changes)],
                                   "release_requirements_satisfied")

    def test_key_binds_amount_provider_digest_obligation_and_survives_hold(self):
        original = decide_release_hold(verified(baseline()))["release_key"]
        for changes in ({"amount": 2}, {"provider": "other-provider"}, {"artifact_sha256": "b" * 64},
                        {"obligation_id": "other-obligation"}):
            task = {**TASK, **changes}
            with self.subTest(changes=changes):
                result = self.assert_reason(baseline(task), "release_requirements_satisfied", task=task)
                self.assertNotEqual(result["release_key"], original)
                held = self.assert_reason(baseline(task)[:2], "missing_verification", task=task)
                self.assertEqual(result["release_key"], held["release_key"])
        renamed_attempt = event("note", "different-attempt", 450, reference="attempt-b")
        self.assertEqual(original, self.assert_reason(baseline() + [renamed_attempt], "release_requirements_satisfied")["release_key"])

    def test_duplicate_proposal_remains_a_hold_with_changed_attempt_note(self):
        records = baseline() + [event("release_committed", "paid", 400)]
        first = self.assert_reason(records + [event("note", "attempt-a", 450)], "duplicate_release")
        second = self.assert_reason(records + [event("note", "attempt-b", 500)], "duplicate_release")
        self.assertEqual(first, second)

    def test_disputes_close_only_the_named_strictly_earlier_valid_open(self):
        opened = event("dispute_open", "open", 350)
        self.assert_reason(baseline() + [opened], "unresolved_dispute")
        self.assert_reason(baseline() + [opened, event("dispute_close", "close", 400, reference="open")],
                           "release_requirements_satisfied")
        for reference, when in [("open", 350), ("open", 300), ("missing", 400), ("g", 400), ("open", 700)]:
            with self.subTest(reference=reference, when=when):
                self.assert_reason(baseline() + [opened, event("dispute_close", "close", when, reference=reference)],
                                   "unresolved_dispute")
        self.assert_reason(baseline() + [opened, event("dispute_open", "other-open", 360),
                                        event("dispute_close", "close", 400, reference="open")], "unresolved_dispute")
        self.assert_reason(baseline() + [opened, event("dispute_close", "close1", 400, reference="open"),
                                        event("dispute_close", "close2", 410, reference="open")], "release_requirements_satisfied")

    def test_foreign_invalid_and_unknown_dispute_closures_do_not_establish_closure(self):
        records = baseline() + [event("dispute_open", "open", 350)]
        for changes, reason in [({"issuer": "foreign"}, "unresolved_dispute"),
                                ({"authentication": "invalid"}, "unresolved_dispute"),
                                ({"authentication": "unknown"}, "uncertain_authentication")]:
            with self.subTest(changes=changes):
                self.assert_reason(records + [event("dispute_close", "close", 400, reference="open", **changes)], reason)

    def test_verified_conflicts_are_not_erased_by_later_pass_or_matching_delivery(self):
        for conflict in [event("verification", "fail", 250, verdict="fail"),
                         event("verification", "wrong-verification", 250, artifact_sha256="b" * 64),
                         event("delivery_claim", "wrong-delivery", 150, artifact_sha256="b" * 64)]:
            with self.subTest(kind=conflict["event_id"]):
                self.assert_reason(baseline() + [conflict], "conflicting_evidence")
                self.assert_reason(list(reversed(baseline() + [conflict])), "conflicting_evidence")

    def test_declared_hold_precedence_when_several_conditions_fail(self):
        open_event = event("dispute_open", "open", 400)
        fail_event = event("verification", "fail", 400, verdict="fail")
        paid = event("release_committed", "paid", 400)
        unknown = event("verification", "unknown", 400, authentication="unknown")
        self.assert_reason(baseline()[1:] + [unknown], "incomplete_evidence", complete=False, eligible=4)
        self.assert_reason(baseline()[1:] + [unknown], "uncertain_authentication")
        self.assert_reason(baseline()[1:] + [paid, open_event], "authority_absent_or_revoked")
        self.assert_reason(baseline() + [paid, open_event], "deadline_expired", task={**TASK, "deadline": at(599)})
        self.assert_reason(baseline() + [paid, open_event, fail_event], "duplicate_release")
        self.assert_reason([baseline()[0], open_event, fail_event], "unresolved_dispute")
        self.assert_reason([baseline()[0], fail_event], "conflicting_evidence")
        self.assert_reason([baseline()[0]], "missing_delivery")
        self.assert_reason(baseline()[:2], "missing_verification")

    def test_support_ids_describe_all_retained_policy_evidence_without_notes(self):
        records = baseline() + [event("verification", "future", 700, verdict="fail"),
                                event("verification", "invalid", 400, verdict="fail", authentication="invalid"),
                                event("note", "unknown-note", 400, authentication="unknown")]
        result = self.assert_reason(records, "release_requirements_satisfied")
        self.assertEqual(result["support_event_ids"], ["d", "future", "g", "invalid", "v"])
        self.assert_reason(records[:2], "incomplete_evidence", complete=False, eligible=5)

    def test_invalid_handoffs_raise_instead_of_becoming_successful_holds(self):
        good = verified(baseline())
        bad = [None, {}, replace(good, complete=1), replace(good, retained_policy_count=True),
               replace(good, eligible_policy_count=True), replace(good, complete=False),
               replace(good, retained_policy_count=2), replace(good, events=good.events + (good.events[0],)),
               replace(good, header={**good.header, "contract_id": "wrong"}),
               replace(good, header={**good.header, "cutoff": at(599)}),
               replace(good, events=list(good.events))]
        for value in bad:
            with self.subTest(value=repr(value)[:90]):
                with self.assertRaises(ValueError):
                    decide_release_hold(value)


if __name__ == "__main__":
    unittest.main()
