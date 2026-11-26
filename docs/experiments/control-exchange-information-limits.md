---
title: "Why a delivery can pass a check and still be wrong"
description: "A retained-evidence diagnosis of missing information, compact records and authenticated verification claims."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

In the [fresh decision comparison](results/2026-11-26-fresh-decision-comparison.md), every method accepted three simulated releases for invalid deliveries. The authority and duplicate checks passed. The delivery-quality assumption did not. A positive verification record was enough for the decision rule even when the later stipulated outcome said the artifact was invalid.

The next investigation explains the original 96 attempts using their saved evidence. It creates no new cases and runs no decision candidate. Its question is: **Was the needed information unavailable, lost from the compact record, or present as a claim that disagreed with the outcome?** These explanations can overlap.

## Three different information limits

| Axis | Evidence to inspect | What the diagnosis can establish |
| --- | --- | --- |
| Availability and effective time | When an event was observed, when it took effect, the cutoff, decision and deadline | Whether the event could support the original decision; later outcomes remain separate |
| Retention | Original event identities, exact source spans, serialized view, completeness and lossless controls | Whether a compact record dropped relevant evidence in a case where the full record supported release |
| Verification quality | Issuer and subject, artifact ID and digest, claimed verdict, later validity and completion | Whether an authenticated and correctly bound claim disagreed with the stipulated outcome |

Observation time is not capture time. These synthetic domain events have no independent per-event capture witness. A local timestamp on the experiment cannot supply one. A visible verification that becomes effective after the decision is also different from one that arrived after the cutoff.

Identity must survive every comparison. An event is identified by cohort hash, case ID and event ID together. Actor identity, role and the direction of a grant stay distinct. Artifact identity includes its content digest. Two cases sharing a release key do not acquire a shared effect history: the experiment gave them separate local states.

A bounded-retention explanation needs joint evidence: the accepted full-input reference supports release; both lossless controls release; the compact attempt holds for incomplete evidence; and the saved source/view mapping shows omission. This explains the retention-and-view system in that case. It does not identify one omitted event as independently necessary or establish a general advantage of graph structure.

## Preserve the original result

The original counts remain fixed. Each compact method released 7 of 9 observable opportunities and 7 of 11 world opportunities. Each lossless control released 9 of 9 and 9 of 11. The compact pairing was five successes in common, two chronological-only, two relational-only and fifteen successes in neither: a net difference of zero.

The diagnostic adds denominators the original score did not foreground. Each arm accepted three effects involving not-ready or invalid artifacts: 3/24 cases and 3/4 such cases. Those are 3/10 accepted effects in either compact arm, and 3/12 in either lossless arm. These are supplemental descriptions of the saved experiment, not revised registered performance metrics. Validity, completion by the decision, and artifact binding are reported separately.

Verification disagreement uses all eligible, operative, exactly bound claims with a retained adjudication as its denominator. A separate count reports how many cases contain those claims. Multiple claims in one case are not independent cases. The C8 format does not establish revision relationships between verification claims; their distinct records remain visible without assuming that a later one supersedes an earlier one. Missing adjudication remains unknown. Overlapping harm categories are not added together as though mutually exclusive.

The case table also retains omitted records, unresolved explanations, exact byte counts and diagnostic time. These measure the quality of the explanation and its reproducibility. They do not measure predictive lift, business value or improved decision capability.

## Read the accepted evidence

The diagnostic starts from the actual accepted comparison event. Each input is resolved through that event's observation mapping to its content-addressed bytes. The loader verifies the historical event chain, observation role, source, membership before completion, byte limit and digest. It does not follow file paths from the old temporary checkout, execute archived code or require an old implementation to match the current source.

The accepted comparison binds its inner caller receipt, claim, custody and registration. Optional outer-process receipts are separately attributed supplements. Capturing one now does not make it part of the earlier acceptance or an external witness.

The immutable evidence origin and the immediate queue parent have separate identities. At the first handoff they name the same accepted comparison. A checked repair or unresolved-evidence review names its immediate diagnostic predecessor while retaining the original comparison ancestry. The controller checks those bindings before claiming work and again under its claim and completion locks.

A preclaim refusal leaves the queue unchanged. A durable operational failure can be consumed only by a corrected full diagnostic with the original captured request, matching claim and valid semantic predecessor. It then records the checked diagnosis and its normal successor together. A failure note alone cannot advance research. Exact replay returns a successful recorded result without running the diagnosis or appending another event.

## Bounds and acceptance

The versioned contract is `decision-information-diagnosis-v1`, phase `information_limits_diagnosis`, stage `retained_diagnostic`. The standalone diagnostic has a ten-second ceiling. Controller acceptance keeps its existing 30-second limit and 60-second outer worker ceiling. There are no new candidate executions, model calls, paid calls or live effects in the diagnostic program. Builder and reviewer resources are accounted separately.

| Captured item | Maximum |
| --- | ---: |
| Original report / journal / cohort | 16 MiB / 24 MiB / 256 KiB |
| Each bound origin, parent, failed request or claim | 1 MiB |
| Each code artifact | 128 KiB |
| Each optional supplemental receipt | 64 KiB |
| Current request / diagnostic contract | 32 KiB / 64 KiB |
| Verified historical prefix | 8 MiB and 4,096 events |
| Diagnostic output | 1 MiB |
| Entire capture, including output | 48 MiB |

Controls cover historical input resolution after a worktree is removed; wrong observations, roles, digests and source versions; cutoff equality and future-effective events; identity collisions; positive verification with an invalid accepted effect; valid but late completion; multiple claims with unestablished revision semantics and unknowns; all 96 attempt slots; bounded failures; unchanged replay; and atomic handoff. Failed-diagnostic continuation must execute the full corrected diagnosis and select its normal successor without an intermediate recovery/requeue event.

## The next question follows from the diagnosis

Checked conformance failure selects repair of the diagnosis. Valid structure with insufficient evidence selects a bounded review of the unresolved attribution. Sufficiently complete diagnosis selects **preparation** of a dated evidence-quality protocol. None of these branches repeats the exposed comparison.

An unchanged evidence gap must not create an endless review loop. A checked review can carry its exact unresolved identities and reasons into protocol preparation as missing-evidence requirements. Those records stay unresolved; identifying what must be observed next does not retroactively answer the old question.

The proposed next question is concrete: for one naturally occurring artifact delivery, can a versioned, independently checkable acceptance result be retained before a declared cutoff and distinguished from an authenticated but unsupported pass claim? Preparation would define artifact digests, actor and role bindings, criteria versions, verifier method and raw result, issue/observe/capture/effective times, revisions and outcome adjudication.

That is a prerequisite for useful distributed value exchange: an identity and a promise must connect to delivery evidence. Recursive systems additionally need versioned interventions that change resources, authority or later observations. Forecast evaluation needs predictions registered before their outcomes. Those are subsequent measurement problems; this diagnosis explains one saved synthetic experiment.
