---
title: "Shared work contracts"
description: "A bounded, two-domain fixture assessment interface using the existing improvement journal."
date: 2026-11-26
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

This implementation lets two invented assessment domains share one lifecycle: declare the work, claim its exact predecessor, preserve inputs, obtain a provisional child report, and let the supervising parent accept or reject it. It reuses `Ledger`, existing improvement events, the existing bounded dispatcher and its failure handoff. It does not run a new predictor, collect evidence, schedule itself or replace the research controller.

The two adapters are reference selection and artifact quality. Their registry is fixed in source. A declaration selects a registered identifier; it cannot supply a command, executable, import, new permission or spending authority. Adding artifact quality required no changes to `improvement.py`, `decision_assessment.py`, `work_contracts.py` or `work_runner.py` after the real first-domain checkpoint. This demonstrates reuse for these two fixtures, not universal extensibility or measured development efficiency.

## Three distinct records

| Record | What it commits to |
| --- | --- |
| Work declaration | Schema version, work ID, exact predecessor and queued step, original expiry and elapsed-time budget, source identities, distinct declared author/reviewer names, optional existing B1 method descriptor/identity, separate policy/cohort/outcome-manifest hashes |
| Public measurement obligations | Adapter/version, outcome definition, total and family denominators, explicit answer-selection or artifact rules, policy hash and fixed task/evidence/expected-obligation identity |
| Observed evidence and accepted outcome | Original input bytes, provisional child output, independently observed child exit/output digest, and an atomic parent-authored terminal event with its successor |

The declarations are bounded to 256 KiB, 32 unique cases and 1–20 seconds. The earlier of the original elapsed-time budget and the declared UTC expiry applies. A fresh child process receives a frozen input capsule and the parent's exact request/checkpoint digest. The claim is checked under the existing write lock. A changed head, reused identity, unfinished claim, changed source or mismatched policy refuses execution or closure.

The child records its claim and input, then returns `provisional` with no accepted measurements. The parent must reap it, observe exit zero without termination, bind its output bytes to the receipt, independently recompute the fixture assessment, and check ownership, input identity, original deadlines and current head again under the completion lock. One transaction records acceptance and its queued successor. Child output alone never advances the queue.

On an ordinary observed process or closure failure, the existing recovery helper may close only the matching reaped claim, under the additional work-contract guards. Expired or uncertain ownership remains unresolved with its evidence; recovery does not refresh the deadline or rerun work. Lost delivery after a committed terminal event preserves that authoritative event. Successors are fixed review/diagnosis actions, not an optimizer or an estimate of the most valuable next research task.

## Deadline observation and continuation

The parent checks the original deadline before commit, after commit, after recovery, after reading authoritative state and after persisting its receipt. A slow operating-system or database write can cross the deadline after the last reversible check. The implementation cannot guarantee publication before that deadline, undo a committed event, or erase accepted measurements already recorded in that event.

A detected crossing returns `work_deadline_exceeded`, `deadline_status: exceeded`, `publication_status: timely_delivery_not_established`, `automatic_continuation_allowed: false` and `continuation_status: requires_inspection`. The CLI exits unsuccessfully. Any already durable completion or failure remains authoritative historical evidence, and its original successor remains recorded; the dispatcher does not replay it or issue another terminal event. A durable administrative completion is not proof of timely publication. Failure-recovery publication has the same limit.

Callers must require the returned successful parent delivery, `deadline_status: observed_within_deadline` and `automatic_continuation_allowed: true` before dispatching a successor. Ledger status alone is insufficient. This fixture entry does not itself execute successors or enforce that caller rule through receipt-gated ownership. A future automatic consumer must implement that gate and independently define its timing evidence. Even a saved receipt is an observation under a surviving trusted parent, not a guarantee against later output I/O stalls or host failure; failed receipt correction requires inspection.

## Public policy and comparison

Reference assessment reports valid references, required coverage, valid extra fields, invalid references, missing references and abstention separately. The public `extras` rule explicitly permits valid extras or forbids them. A valid title reference can therefore fail exact conformance without being false evidence. Missing evidence and abstention are different rows of evidence. The artifact adapter separately reports byte limits, digest match, JSON-object format, required keys and permitted extra keys. A matching digest does not establish useful content.

Both reports retain counts and fixed family denominators. Their measures are declared-policy conformance; `general_accuracy` and `predictive_advantage` remain null. The public policy accessor returns the actual policy and its digest without case/gold content. It is an interface helper, not evidence that an independent candidate received or understood it.

Measurement identity includes the adapter, public policy, retained cohort and eight source identities: `work_contracts`, `work_adapters`, `work_runner`, `decision_assessment`, `improvement`, `store`, `manifests`, and `assertions`. The conservative set includes operational sources because they may affect evidence eligibility. No dependency-granular semantic compatibility is claimed. All identities remain retained for provenance.

Candidate method identity and the retained outcome manifest are separate from measurement identity. Fixed cases contain task/evidence/expected obligations; the versioned outcome manifest binds an ordered set of supplied answers/artifacts to that cohort. Different answers can produce different measurements under the same measurement identity. The original complete bundle and separate outcome-manifest hash remain retained, and post-preparation mutation refuses even if its declared hashes are recomputed.

Different existing B1 method descriptors may be descriptively comparable when the measurement components are unchanged. Changing the cohort, policy, outcome definition, denominator or a pinned source is explicitly incomparable; it cannot be presented as improvement. Comparison supplies no invented delta or causal estimate. Supplied outcomes are not newly generated predictions, independent first attempts or prospective seals. A future prospective consumer must validate that production and timing evidence separately.

The existing manifest method-identity function is reused; this does not register a new live representation manifest or prove snapshot eligibility. Distinct author/reviewer names are declared local metadata, not authentication or independent review by themselves.

## Historical boundary and next dependency

The actual C12 failed queue, original answers, scoring key and strict score remain unchanged. Work fixtures refuse a legacy/C12 predecessor, and the legacy entry refuses a work-contract predecessor. This entry neither migrates nor consumes the actual queue. A compatible continuation from that historical failure remains an unresolved, separately reviewed dependency; fixture completion is not automatic research progress.

The next intended consumer is a prospective diverse-entity representation experiment. Its task/output binding, independently authored public obligations, reference baselines, evidence eligibility and metric choice require their own protocol. No collector, candidate runner, model call, network call, new scheduler or authority increase is part of this slice. The [validation record](runs/2026-11-26-work-contracts.md) and [fixture protocol](../experiments/work-contracts.md) state the measured limits.
