"""Independent, pure evaluator for the owned release/hold decision pilot.

No candidate view or policy implementation is imported. World rights and the
full-visible reference are resolved from records, not candidate conclusions.
Effect keys are explicit case-local simulation state, not a payment service.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import re

CONTRACT_ID = "control-exchange-release-hold-v1"
EVALUATION_CONTRACT_ID = "release-hold-evaluation-v1"
MAX_CASES = 24
MAX_EVENTS = 15  # One additional private outcome is the sixteenth domain event.
MAX_EFFECT_KEYS = 32
MAX_INPUT_BYTES = 32768
MAX_OUTPUT_BYTES = 131072
BASE = datetime(2020, 1, 1, tzinfo=timezone.utc)
POLICY_KINDS = ("grant", "revoke", "delivery_claim", "verification", "dispute_open", "dispute_close", "release_committed")
HOLD_REASONS = ("incomplete_evidence", "uncertain_authentication", "authority_absent_or_revoked", "deadline_expired",
                "duplicate_release", "unresolved_dispute", "conflicting_evidence", "missing_delivery", "missing_verification")
TASK_FIELDS = {"obligation_id", "requester", "delegate", "provider", "artifact_id", "artifact_sha256", "amount", "unit", "deadline"}
EVENT_FIELDS = {"event_id", "kind", "issuer", "subject", "object", "obligation_id", "effective_at", "observed_at", "reference", "artifact_sha256", "verdict", "authentication"}
OUTCOME_FIELDS = {"event_id", "kind", "artifact_id", "artifact_sha256", "completed_at", "artifact_valid", "revealed_at", "basis"}
TRACE_REQUIRED = {"trace_id", "mechanism", "task", "cutoff", "decision_at", "events", "later_outcome"}
TRACE_OPTIONAL = {"pair_id", "fixture_label", "attempt_id", "development_only_annotation"}
PROPOSAL_FIELDS = {"action", "reason", "release_key", "support_event_ids"}
FACT_FIELDS = {"active_grant_ids", "open_dispute_ids", "decision_within_deadline", "world_authorized", "world_duplicate",
               "artifact_ready_valid", "world_opportunity", "visible_actionable_opportunity"}
ROW_FIELDS = {"schema_version", "evaluation_contract_id", "case_id", "mechanism", "release_key", "facts", "artifact_outcome",
              "reference_proposal", "proposal", "proposal_valid", "proposal_error", "attempt_class", "prior_effect_keys",
              "effect_receipt", "resulting_effect_keys", "metric_flags"}
METRIC_IDS = ("valid_timely_release", "observable_opportunity_completion", "unauthorized_release_proposals_all",
              "unauthorized_release_proposals_forbidden", "duplicate_release_proposals_all", "duplicate_release_proposals_attempts",
              "invalid_artifact_release_proposals", "evidence_unjustified_release_proposals", "hold_rate",
              "missed_world_opportunities", "missed_observable_opportunities", "valid_output_completion", "duplicate_effects", "unauthorized_effects")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _raw(value, limit=MAX_INPUT_BYTES):
    # Bound traversal before serialization, including ignored fixture metadata.
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        _require(count <= 8192 and depth <= 16, "JSON structure exceeds evaluator bound")
        if type(item) is dict:
            _require(len(item) <= 128 and all(type(key) is str and len(key) <= 128 for key in item), "Invalid bounded JSON object")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list or type(item) is tuple:
            _require(len(item) <= 128, "JSON array exceeds evaluator bound")
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            _require(len(item) <= limit, "JSON string exceeds evaluator bound")
        elif type(item) is int:
            _require(item.bit_length() <= 64, "JSON integer exceeds evaluator bound")
        elif type(item) is float:
            _require(math.isfinite(item), "Nonfinite JSON number")
        else:
            _require(item is None or type(item) is bool, "Expected JSON data")
    try:
        result = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Invalid finite UTF-8 JSON") from error
    _require(len(result) <= limit, "JSON bytes exceed evaluator bound")
    return result


def _keys(value, fields, label):
    _require(type(value) is dict and set(value) == fields, "Invalid " + label + " fields")


def _identifier(value):
    _require(type(value) is str and 1 <= len(value) <= 32, "Invalid identifier")
    try:
        _require(len(value.encode("utf-8")) <= 32 and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value), "Invalid identifier")
    except UnicodeError as error:
        raise ValueError("Invalid identifier encoding") from error


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "Invalid digest")


def _seconds(value):
    _require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value) is not None, "Invalid exact UTC time")
    try:
        result = int((datetime.fromisoformat(value[:-1] + "+00:00") - BASE).total_seconds())
    except ValueError as error:
        raise ValueError("Invalid UTC calendar time") from error
    _require(-86400 <= result <= 86400, "Time exceeds owned pilot range")
    return result


def _task(task):
    _keys(task, TASK_FIELDS, "task")
    names = [task[key] for key in ("obligation_id", "requester", "delegate", "provider", "artifact_id")]
    for name in names:
        _identifier(name)
    _require(len(set(names)) == 5, "Task roles and objects must be distinct")
    _digest(task["artifact_sha256"])
    _require(type(task["amount"]) is int and 1 <= task["amount"] <= 1000000000 and task["unit"] == "simulation_credit", "Invalid amount/unit")
    _seconds(task["deadline"])


def compute_release_key(task):
    """The reviewed task key, independent of attempt IDs and outcome labels."""
    _task(task)
    return hashlib.sha256(_raw([CONTRACT_ID, task["obligation_id"], task["artifact_sha256"], task["provider"], task["amount"], task["unit"]])).hexdigest()


def _event(event):
    _keys(event, EVENT_FIELDS, "domain event")
    for field in ("event_id", "issuer", "subject", "object", "obligation_id"):
        _identifier(event[field])
    kind = event["kind"]
    _require(type(kind) is str and kind in POLICY_KINDS + ("note",), "Invalid event kind")
    _require(event["authentication"] in ("verified", "unknown", "invalid"), "Invalid authentication")
    _seconds(event["effective_at"])
    _seconds(event["observed_at"])
    if kind in ("delivery_claim", "verification", "release_committed"):
        _digest(event["artifact_sha256"])
    else:
        _require(event["artifact_sha256"] is None, "Unexpected event artifact")
    _require(event["verdict"] in ("pass", "fail") if kind == "verification" else event["verdict"] is None, "Invalid verdict")
    ref = event["reference"]
    if kind == "release_committed":
        _digest(ref)
    elif kind == "dispute_close":
        _identifier(ref)
    elif kind in ("revoke", "note"):
        if ref is not None:
            _identifier(ref)
    else:
        _require(ref is None, "Unexpected reference")


def _outcome(outcome):
    _keys(outcome, OUTCOME_FIELDS, "private outcome")
    _identifier(outcome["event_id"])
    _identifier(outcome["artifact_id"])
    _digest(outcome["artifact_sha256"])
    _seconds(outcome["completed_at"])
    _seconds(outcome["revealed_at"])
    _require(outcome["kind"] == "artifact_outcome" and type(outcome["artifact_valid"]) is bool
             and outcome["basis"] == "owned_simulation_stipulation", "Invalid private outcome")


def _trace(trace):
    _raw(trace)
    _require(type(trace) is dict and TRACE_REQUIRED <= set(trace) <= TRACE_REQUIRED | TRACE_OPTIONAL, "Invalid private trace fields")
    _identifier(trace["trace_id"])
    _require(type(trace["mechanism"]) is str and 1 <= len(trace["mechanism"].encode("utf-8")) <= 256, "Invalid mechanism")
    _task(trace["task"])
    _require(_seconds(trace["cutoff"]) == _seconds(trace["decision_at"]), "Cutoff must equal decision time")
    _require(type(trace["events"]) is list and len(trace["events"]) <= MAX_EVENTS, "Invalid bounded event history")
    ids = set()
    for event in trace["events"]:
        _event(event)
        _require(event["event_id"] not in ids, "Duplicate domain event ID")
        ids.add(event["event_id"])
    outcome = trace["later_outcome"]
    _outcome(outcome)
    _require(outcome["event_id"] not in ids, "Outcome duplicates domain event ID")
    return trace["task"]


def _bound(event, task):
    """Base roles/scope only: uncertain content cannot cure unknown auth."""
    if event["obligation_id"] != task["obligation_id"]:
        return False
    roles = {"grant": ("requester", "requester", "delegate"), "revoke": ("requester", "requester", "delegate"),
             "delivery_claim": ("provider", "provider", "artifact_id"), "verification": ("requester", "requester", "artifact_id"),
             "dispute_open": ("requester", "requester", "obligation_id"), "dispute_close": ("requester", "requester", "obligation_id"),
             "release_committed": ("requester", "delegate", "provider")}
    binding = roles.get(event["kind"])
    return binding is not None and tuple(event[k] for k in ("issuer", "subject", "object")) == tuple(task[k] for k in binding)


def _state(events, task, decision, key):
    operative = [e for e in events if _seconds(e["effective_at"]) <= decision and _bound(e, task)]
    verified = [e for e in operative if e["authentication"] == "verified"]
    grants = [e for e in verified if e["kind"] == "grant"]
    revokes = [e for e in verified if e["kind"] == "revoke"]
    # Independent per-grant predicate, not the candidate's ordered set reducer.
    active = sorted(g["event_id"] for g in grants if not any(
        _seconds(r["effective_at"]) >= _seconds(g["effective_at"])
        and r["reference"] in (None, g["event_id"]) for r in revokes))
    opens = [e for e in verified if e["kind"] == "dispute_open"]
    closes = [e for e in verified if e["kind"] == "dispute_close"]
    unresolved = sorted(o["event_id"] for o in opens if not any(c["reference"] == o["event_id"]
        and _seconds(o["effective_at"]) < _seconds(c["effective_at"]) for c in closes))
    used = any(e["kind"] == "release_committed" and e["reference"] == key
               and e["artifact_sha256"] == task["artifact_sha256"] for e in verified)
    return active, unresolved, used, operative, verified


def _reference(trace, task):
    eligible = [e for e in trace["events"] if _seconds(e["observed_at"]) <= _seconds(trace["cutoff"])
                and e["obligation_id"] == task["obligation_id"]]
    key, decision = compute_release_key(task), _seconds(trace["decision_at"])
    active, disputes, used, operative, verified = _state(eligible, task, decision, key)
    content = [e for e in verified if e["kind"] in ("delivery_claim", "verification")]
    conflict = any(e["artifact_sha256"] != task["artifact_sha256"] or e["verdict"] == "fail" for e in content)
    delivery = any(e["kind"] == "delivery_claim" and e["artifact_sha256"] == task["artifact_sha256"] for e in content)
    passed = any(e["kind"] == "verification" and e["verdict"] == "pass" and e["artifact_sha256"] == task["artifact_sha256"] for e in content)
    conditions = (("uncertain_authentication", any(e["authentication"] == "unknown" for e in operative)),
                  ("authority_absent_or_revoked", not active), ("deadline_expired", decision > _seconds(task["deadline"])),
                  ("duplicate_release", used), ("unresolved_dispute", bool(disputes)), ("conflicting_evidence", conflict),
                  ("missing_delivery", not delivery), ("missing_verification", not passed))
    reason = next((name for name, holds in conditions if holds), "release_requirements_satisfied")
    return {"action": "release" if reason == "release_requirements_satisfied" else "hold", "reason": reason, "release_key": key,
            "support_event_ids": sorted(e["event_id"] for e in eligible if e["kind"] in POLICY_KINDS)}


def reference_decision(world_trace_private):
    """Independent full-cutoff-input reference; never consults private truth."""
    task = _trace(world_trace_private)
    return _reference(world_trace_private, task)


def _effect_keys(values):
    _require(type(values) in (list, tuple) and len(values) <= MAX_EFFECT_KEYS, "Invalid bounded effect-key state")
    for key in values:
        _digest(key)
    _require(len(set(values)) == len(values), "Duplicate state key")
    return set(values)


def _world(trace, task, prior_effect_keys):
    key, decision = compute_release_key(task), _seconds(trace["decision_at"])
    active, disputes, used, _, _ = _state(trace["events"], task, decision, key)
    state = _effect_keys(prior_effect_keys)
    if used:
        state.add(key)
    _require(len(state | {key}) <= MAX_EFFECT_KEYS, "Effect-key state lacks bounded capacity")
    within = decision <= _seconds(task["deadline"])
    outcome = trace["later_outcome"]
    ready = (outcome["artifact_id"] == task["artifact_id"] and outcome["artifact_sha256"] == task["artifact_sha256"]
             and outcome["artifact_valid"] and _seconds(outcome["completed_at"]) <= decision)
    authorized = bool(active) and within and not disputes
    facts = {"active_grant_ids": active, "open_dispute_ids": disputes, "decision_within_deadline": within,
             "world_authorized": bool(authorized), "world_duplicate": key in state, "artifact_ready_valid": bool(ready),
             "world_opportunity": bool(authorized and key not in state and ready)}
    return key, facts, sorted(state)


def resolve_world(world_trace_private, *, prior_effect_keys=()):
    """Return bounded stipulated world facts, independent of observer evidence."""
    task = _trace(world_trace_private)
    key, facts, state = _world(world_trace_private, task, prior_effect_keys)
    return {"release_key": key, **facts, "prior_effect_keys": state}


def _proposal(proposal, expected_key, eligible_ids):
    _raw(proposal, 1024)
    _keys(proposal, PROPOSAL_FIELDS, "proposal")
    _require(proposal["action"] in ("release", "hold"), "Invalid proposal action")
    _require(proposal["reason"] == "release_requirements_satisfied" if proposal["action"] == "release"
             else proposal["reason"] in HOLD_REASONS, "Invalid action/reason pairing")
    _require(proposal["release_key"] == expected_key, "Proposal release key differs from task")
    ids = proposal["support_event_ids"]
    _require(type(ids) is list and len(ids) <= MAX_EVENTS, "Invalid support ID list")
    for eid in ids:
        _identifier(eid)
    _require(ids == sorted(set(ids)) and set(ids) <= set(eligible_ids), "Support IDs must be sorted unique eligible policy-kind IDs")


def _metric_flags(row):
    f, effect = row["facts"], row["effect_receipt"]
    release = row["proposal_valid"] and row["proposal"]["action"] == "release"
    hold = row["proposal_valid"] and row["proposal"]["action"] == "hold"
    successful = bool(release and f["world_opportunity"] and effect["status"] == "accepted")
    unauthorized, duplicate = bool(release and not f["world_authorized"]), bool(release and f["world_duplicate"])
    return {"valid_timely_release": int(successful), "observable_opportunity_completion": int(successful and f["visible_actionable_opportunity"]),
            "unauthorized_release_proposals_all": int(unauthorized), "unauthorized_release_proposals_forbidden": int(unauthorized),
            "duplicate_release_proposals_all": int(duplicate), "duplicate_release_proposals_attempts": int(duplicate),
            "invalid_artifact_release_proposals": int(release and not f["artifact_ready_valid"]),
            "evidence_unjustified_release_proposals": int(release and row["reference_proposal"]["action"] == "hold"),
            "hold_rate": int(hold), "missed_world_opportunities": int(f["world_opportunity"] and not successful),
            "missed_observable_opportunities": int(f["visible_actionable_opportunity"] and not successful),
            "valid_output_completion": int(row["proposal_valid"]),
            "duplicate_effects": max(0, effect["new_effects"] - int(not f["world_duplicate"])),
            "unauthorized_effects": int(effect["new_effects"] > 0 and not f["world_authorized"])}


def evaluate_simulated_proposal(world_trace_private, proposal, *, release_key=None, prior_effect_keys=(), error=None):
    """Evaluate one attempt; callers retain raw failed worker output separately.

    A bad candidate output is a failed row. Invalid private fixture/state is an
    evaluator contract error. Each arm/case starts independently; carry returned
    keys only for an explicit replay test. No caller-owned input is mutated.
    """
    task = _trace(world_trace_private)
    key, facts, state = _world(world_trace_private, task, prior_effect_keys)
    _require(release_key is None or release_key == key, "Supplied evaluator key differs from task")
    _require(error is None or type(error) is str and 1 <= len(error.encode("utf-8")) <= 512, "Invalid worker error")
    reference = _reference(world_trace_private, task)
    facts["visible_actionable_opportunity"] = facts["world_opportunity"] and reference["action"] == "release"
    retained, problem = None, error
    try:
        _raw(proposal, 1024)
        retained = deepcopy(proposal)
        _proposal(proposal, key, reference["support_event_ids"])
    except ValueError as failure:
        if problem is None:
            problem = str(failure)
    valid = problem is None
    status, effect_reason, new_effects = "not_attempted", "candidate_failure", 0
    resulting = set(state)
    if valid and proposal["action"] == "hold":
        status, effect_reason = "held", "hold_proposal"
    elif valid:
        if facts["world_duplicate"]:
            status, effect_reason = "reused", "duplicate_release"
        elif not facts["world_authorized"]:
            status, effect_reason = "refused", "world_authority_or_deadline_or_dispute"
        else:
            status, effect_reason, new_effects = "accepted", "first_simulated_release", 1
            resulting.add(key)
    effect_id = hashlib.sha256(_raw(["case-local-simulated-effect-v1", key])).hexdigest() if key in resulting else None
    row = {"schema_version": 1, "evaluation_contract_id": EVALUATION_CONTRACT_ID,
           "case_id": world_trace_private["trace_id"], "mechanism": world_trace_private["mechanism"], "release_key": key,
           "facts": facts, "artifact_outcome": deepcopy(world_trace_private["later_outcome"]), "reference_proposal": reference,
           "proposal": retained, "proposal_valid": valid, "proposal_error": problem,
           "attempt_class": proposal["action"] if valid else "failed", "prior_effect_keys": state,
           "effect_receipt": {"status": status, "reason": effect_reason, "release_key": key, "effect_id": effect_id, "new_effects": new_effects},
           "resulting_effect_keys": sorted(resulting)}
    row["metric_flags"] = _metric_flags(row)
    _raw(row)
    return row


def _checked_row(row):
    _raw(row)
    _keys(row, ROW_FIELDS, "evaluation row")
    _require(type(row["schema_version"]) is int and row["schema_version"] == 1 and row["evaluation_contract_id"] == EVALUATION_CONTRACT_ID, "Invalid evaluation identity")
    _identifier(row["case_id"])
    _require(type(row["mechanism"]) is str and 1 <= len(row["mechanism"].encode("utf-8")) <= 256, "Invalid mechanism")
    _digest(row["release_key"])
    _outcome(row["artifact_outcome"])
    facts = row["facts"]
    _keys(facts, FACT_FIELDS, "truth facts")
    for field in FACT_FIELDS - {"active_grant_ids", "open_dispute_ids"}:
        _require(type(facts[field]) is bool, "Truth flag must be boolean")
    for field in ("active_grant_ids", "open_dispute_ids"):
        ids = facts[field]
        _require(type(ids) is list and len(ids) <= MAX_EVENTS, "Invalid truth identity set")
        for eid in ids:
            _identifier(eid)
        _require(ids == sorted(set(ids)), "Truth IDs must be sorted unique")
    _require(facts["world_authorized"] == bool(facts["active_grant_ids"] and facts["decision_within_deadline"] and not facts["open_dispute_ids"]), "Inconsistent authorization facts")
    _require(facts["world_opportunity"] == (facts["world_authorized"] and not facts["world_duplicate"] and facts["artifact_ready_valid"]), "Inconsistent world opportunity")
    reference = row["reference_proposal"]
    _proposal(reference, row["release_key"], reference.get("support_event_ids", []) if type(reference) is dict else [])
    _require(facts["visible_actionable_opportunity"] == (facts["world_opportunity"] and reference["action"] == "release"), "Inconsistent visible opportunity")
    _require(type(row["proposal_valid"]) is bool, "Invalid proposal-valid flag")
    if row["proposal_valid"]:
        _proposal(row["proposal"], row["release_key"], reference["support_event_ids"])
        _require(row["proposal_error"] is None and row["attempt_class"] == row["proposal"]["action"], "Inconsistent valid attempt")
    else:
        _require(type(row["proposal_error"]) is str and 1 <= len(row["proposal_error"].encode("utf-8")) <= 512 and row["attempt_class"] == "failed", "Missing failed-attempt error")
    prior, resulting = _effect_keys(row["prior_effect_keys"]), _effect_keys(row["resulting_effect_keys"])
    _require(row["prior_effect_keys"] == sorted(prior) and row["resulting_effect_keys"] == sorted(resulting), "State must be sorted")
    _require(facts["world_duplicate"] == (row["release_key"] in prior), "Inconsistent duplicate fact")
    effect = row["effect_receipt"]
    _keys(effect, {"status", "reason", "release_key", "effect_id", "new_effects"}, "effect receipt")
    reasons = {"not_attempted": "candidate_failure", "held": "hold_proposal", "refused": "world_authority_or_deadline_or_dispute", "reused": "duplicate_release", "accepted": "first_simulated_release"}
    _require(type(effect["status"]) is str and effect["status"] in reasons and effect["reason"] == reasons[effect["status"]], "Invalid effect status")
    _require(type(effect["new_effects"]) is int and effect["new_effects"] == int(effect["status"] == "accepted") and effect["release_key"] == row["release_key"], "Invalid effect count/key")
    _require(resulting == prior | ({row["release_key"]} if effect["new_effects"] else set()), "Inconsistent resulting effect state")
    expected_id = hashlib.sha256(_raw(["case-local-simulated-effect-v1", row["release_key"]])).hexdigest() if row["release_key"] in resulting else None
    _require(effect["effect_id"] == expected_id, "Invalid simulated effect identity")
    _require((row["attempt_class"] == "failed") == (effect["status"] == "not_attempted"), "Failure cannot create an effect")
    _require((row["attempt_class"] == "hold") == (effect["status"] == "held"), "Hold cannot create an effect")
    _keys(row["metric_flags"], set(METRIC_IDS), "metric flags")
    _require(all(type(value) is int and 0 <= value <= 1 for value in row["metric_flags"].values()) and row["metric_flags"] == _metric_flags(row), "Inconsistent metric flags")


def aggregate_metrics(rows):
    """Fixed denominators over every supplied case; call separately per arm.

    The driver binds this case set to its complete declared cohort. This function
    rejects duplicate/malformed rows rather than silently dropping any attempt.
    """
    _require(type(rows) is list and len(rows) <= MAX_CASES, "Invalid bounded evaluation rows")
    for row in rows:
        _checked_row(row)
    _require(len({row["case_id"] for row in rows}) == len(rows), "Duplicate case ID")
    counts = {"cases": len(rows), "world_opportunities": sum(r["facts"]["world_opportunity"] for r in rows),
              "visible_actionable_opportunities": sum(r["facts"]["visible_actionable_opportunity"] for r in rows),
              "forbidden_cases": sum(not r["facts"]["world_authorized"] for r in rows),
              "duplicate_opportunity_cases": sum(r["facts"]["world_duplicate"] for r in rows),
              "ordinary_attempts": sum(not r["facts"]["world_duplicate"] for r in rows),
              "not_ready_or_invalid_cases": sum(not r["facts"]["artifact_ready_valid"] for r in rows),
              "failed_attempts": sum(not r["proposal_valid"] for r in rows),
              "release_proposals": sum(r["proposal_valid"] and r["proposal"]["action"] == "release" for r in rows),
              "hold_outputs": sum(r["proposal_valid"] and r["proposal"]["action"] == "hold" for r in rows)}
    denominators = {name: counts["cases"] for name in METRIC_IDS}
    for name in ("valid_timely_release", "missed_world_opportunities"):
        denominators[name] = counts["world_opportunities"]
    for name in ("observable_opportunity_completion", "missed_observable_opportunities"):
        denominators[name] = counts["visible_actionable_opportunities"]
    denominators["unauthorized_release_proposals_forbidden"] = counts["forbidden_cases"]
    denominators["duplicate_release_proposals_attempts"] = counts["duplicate_opportunity_cases"]
    metrics = {}
    for name in METRIC_IDS:
        numerator, denominator = sum(row["metric_flags"][name] for row in rows), denominators[name]
        metrics[name] = {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None}
    by_key = {}
    for row in rows:
        key_counts = by_key.setdefault(row["release_key"], {"attempts": 0, "new_effects": 0, "duplicate_effects": 0})
        key_counts["attempts"] += 1
        key_counts["new_effects"] += row["effect_receipt"]["new_effects"]
        key_counts["duplicate_effects"] += row["metric_flags"]["duplicate_effects"]
    result = {"schema_version": 1, "evaluation_contract_id": EVALUATION_CONTRACT_ID, "case_count": len(rows),
              "counts": counts, "metrics": metrics, "effects_by_release_key": by_key,
              "effect_scope": "Each case starts from its independent stipulated state; equal keys across cases do not share effects."}
    _raw(result, MAX_OUTPUT_BYTES)
    return result
