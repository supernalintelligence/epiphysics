"""Fixed observer policy for the owned control-exchange decision pilot.

Only ``VerifiedPolicyInput`` from the public view decoder is accepted. There are
no source-store reads, private outcomes, world-state reducers or effects here.
The type denotes the trusted local pipeline, not a security capability.

``support_event_ids`` names all inspected retained policy-kind records, including
inert, future-effective and partial evidence. It is not a positive-proof-only
list. Notes are omitted. Every output, including a hold, has the same task key.
"""

from hashlib import sha256

from .decision_views import (
    CONTRACT_ID,
    EVENT_FIELDS,
    POLICY_KINDS,
    VerifiedPolicyInput,
    canonical,
    seconds,
)


RELEASE_REASON = "release_requirements_satisfied"
HOLD_REASONS = (
    "incomplete_evidence",
    "uncertain_authentication",
    "authority_absent_or_revoked",
    "deadline_expired",
    "duplicate_release",
    "unresolved_dispute",
    "conflicting_evidence",
    "missing_delivery",
    "missing_verification",
)


def _bound(event, task):
    """Base role/scope binding, before authentication, digest and reference."""
    requester, delegate = task["requester"], task["delegate"]
    provider, artifact = task["provider"], task["artifact_id"]
    obligation = task["obligation_id"]
    bindings = {
        "grant": (requester, requester, delegate),
        "revoke": (requester, requester, delegate),
        "delivery_claim": (provider, provider, artifact),
        "verification": (requester, requester, artifact),
        "dispute_open": (requester, requester, obligation),
        "dispute_close": (requester, requester, obligation),
        "release_committed": (requester, delegate, provider),
    }
    return (event["obligation_id"] == obligation
            and bindings.get(event["kind"]) ==
            (event["issuer"], event["subject"], event["object"]))


def _active_grants(events):
    """Reduce only verified, operative, base-bound records from this view."""
    authority = [event for event in events if event["kind"] in ("grant", "revoke")]
    authority.sort(key=lambda event: (seconds(event["effective_at"]),
                                     event["kind"] == "revoke", event["event_id"]))
    active = set()
    for event in authority:
        if event["kind"] == "grant":
            active.add(event["event_id"])
        elif event["reference"] is None:
            active.clear()
        else:
            # Only applicable verified grants can already be in this set.
            # Missing/foreign/future/stale references cannot remove another ID.
            active.discard(event["reference"])
    return active


def _open_disputes(events):
    disputes = [event for event in events
                if event["kind"] in ("dispute_open", "dispute_close")]
    disputes.sort(key=lambda event: (seconds(event["effective_at"]),
                                    event["kind"] == "dispute_close", event["event_id"]))
    opened_at, active = {}, set()
    for event in disputes:
        when = seconds(event["effective_at"])
        if event["kind"] == "dispute_open":
            opened_at[event["event_id"]] = when
            active.add(event["event_id"])
        elif event["reference"] in opened_at and opened_at[event["reference"]] < when:
            active.discard(event["reference"])
    return active


def decide_release_hold(verified_input):
    """Return one deterministic proposal; invalid pipeline inputs raise.

    Source schema, byte limits and provenance belong to ``validate_decode_view``.
    These inexpensive structural checks detect malformed handoffs without
    turning a failed attempt into a successful hold. This function never obtains
    omitted facts or verifies a private artifact outcome.
    """
    if not isinstance(verified_input, VerifiedPolicyInput):
        raise ValueError("Policy requires VerifiedPolicyInput from the view decoder")
    header, events = verified_input.header, verified_input.events
    if (type(header) is not dict or header.get("contract_id") != CONTRACT_ID
            or type(events) is not tuple or len(events) > 16):
        raise ValueError("Invalid verified policy handoff")
    if (type(verified_input.complete) is not bool
            or type(verified_input.eligible_policy_count) is not int
            or type(verified_input.retained_policy_count) is not int
            or not 0 <= verified_input.retained_policy_count <= verified_input.eligible_policy_count <= 16
            or verified_input.complete != (verified_input.eligible_policy_count == verified_input.retained_policy_count)):
        raise ValueError("Invalid verified completeness metadata")
    for event in events:
        if (type(event) is not dict or set(event) != set(EVENT_FIELDS)
                or event["kind"] not in (*POLICY_KINDS, "note")
                or event["authentication"] not in ("verified", "unknown", "invalid")):
            raise ValueError("Invalid retained event handoff")
    identifiers = [event["event_id"] for event in events]
    if (any(type(value) is not str for value in identifiers)
            or len(set(identifiers)) != len(identifiers)
            or sum(event["kind"] in POLICY_KINDS for event in events) != verified_input.retained_policy_count):
        raise ValueError("Invalid retained identities or policy count")
    task = header["task"]
    decision = seconds(header["decision_at"])
    if decision != seconds(header["cutoff"]):
        raise ValueError("Decision and evidence cutoff must match")
    if any(seconds(event["observed_at"]) > decision for event in events):
        raise ValueError("Retained event is beyond the evidence cutoff")
    release_key = sha256(canonical([CONTRACT_ID, task["obligation_id"],
                                   task["artifact_sha256"], task["provider"],
                                   task["amount"], task["unit"]])).hexdigest()
    support_ids = sorted(event["event_id"] for event in events if event["kind"] in POLICY_KINDS)

    def output(reason):
        result = {"action": "release" if reason == RELEASE_REASON else "hold",
                  "reason": reason, "release_key": release_key, "support_event_ids": support_ids}
        if len(canonical(result)) > 1024:
            raise ValueError("Policy output exceeds the fixed byte bound")
        return result

    if not verified_input.complete:
        return output("incomplete_evidence")
    operative = [event for event in events
                 if seconds(event["effective_at"]) <= decision and _bound(event, task)]
    if any(event["authentication"] == "unknown" for event in operative):
        return output("uncertain_authentication")
    trusted = [event for event in operative if event["authentication"] == "verified"]
    if not _active_grants(trusted):
        return output("authority_absent_or_revoked")
    if decision > seconds(task["deadline"]):
        return output("deadline_expired")
    expected_digest = task["artifact_sha256"]
    if any(event["kind"] == "release_committed" and event["artifact_sha256"] == expected_digest
           and event["reference"] == release_key for event in trusted):
        return output("duplicate_release")
    if _open_disputes(trusted):
        return output("unresolved_dispute")
    claims = [event for event in trusted if event["kind"] in ("delivery_claim", "verification")]
    if any(event["artifact_sha256"] != expected_digest
           or (event["kind"] == "verification" and event["verdict"] == "fail") for event in claims):
        return output("conflicting_evidence")
    if not any(event["kind"] == "delivery_claim" for event in claims):
        return output("missing_delivery")
    if not any(event["kind"] == "verification" and event["verdict"] == "pass" for event in claims):
        return output("missing_verification")
    return output(RELEASE_REASON)
