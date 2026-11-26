---
title: "Find where required evidence was lost"
description: "A retained-evidence diagnosis that separates missing retrieval support, annotation gaps and unresolved interpretation."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

The [fresh coverage evaluation](../planning/runs/2026-11-26-retrieval-coverage.md) retrieved a complete declared evidence bundle for five of six supported questions. The remaining question asks for two related capabilities. Before changing the retriever, check whether it omitted required evidence, the annotations missed another sufficient answer, or the evidence remains ambiguous.

This protocol uses the saved source bytes, questions, annotations, projection and returned windows. It introduces no new retrieval or answer generation. The original scores and raw baseline remain unchanged. The cohort and its results are already visible to the investigators.

## Check the recorded result

The mechanical check intersects each required source span with the windows actually returned at cutoffs one, three and five. It preserves source identity, merges overlapping coverage without counting bytes twice, and retains every gap. A bundle succeeds only when all its required spans are covered; separate alternatives cannot supply interchangeable fragments.

Inspect the retained projection separately. A required span may survive in indexed windows that never appeared in the results. That observation distinguishes representation preservation from retrieval selection. It does not establish why the ranking omitted those windows. Retained rows never become extra retrieval results in this check.

The machine check cannot decide whether the returned text contains a differently worded sufficient answer. A separate reviewer examines that question, records uncertainty and binds the judgment to the exact returned windows and mechanical findings. Reviewer labels are local attestations; they do not authenticate a person's identity. An unresolved judgment must remain unresolved.

The executable report will retain the originating assessment and its frozen measurement identity. Its own diagnosis identity is separate. Successful verification records a diagnosis and a successor together through the existing controller. It does not count as a fresh quality measurement, repaired support, or a prediction of the next action's success.

## Bound the follow-up

For the exposed joint question, the proposed follow-up asks each of its two clauses separately under the same raw representation and corpus. Exact clauses, run count, retrieval depth, source-byte accounting and stopping rule must be fixed before any new output. The proposal is not an executed experiment.

Two clause queries can return more windows than one whole query. Report that change explicitly. Recovering evidence with a larger selection budget would show local sensitivity, not a fair-budget quality gain. Any later comparative claim requires a separately fixed equal-budget control and fresh questions. Do not reformulate this exposed case repeatedly until it succeeds.

Stop after the declared diagnostic comparison, regardless of the outcome. Preserve failures and missing outputs. Use its result to choose a new question, rather than changing the old labels or promoting a new baseline.

## Acceptance and limits

Accept the diagnosis only when source and receipt identities match, interval findings reconcile with the original per-case report, and the persistent transition consumes the correct predecessor exactly once. Retain annotation gaps and unresolved judgments as valid attributed findings. They select clarification work; only reviewed retrieval gaps with no deferred failures select follow-up preparation. Neither outcome executes the proposed follow-up experiment. Changed inputs under a reused run key must refuse; interruption must preserve the original result and require inspection.

Owned controls must exercise intact omitted evidence, partial and overlapping spans, alternative bundles, cross-source mismatches, changed bytes, stale predecessors and replay. The diagnosis must not invoke search, indexing or the aggregate scorer. Source archives remain read-only; the controller stores the new report separately.

This checks a development failure in evidence retrieval. It does not measure generated answers, calibrated abstention, broad entity coverage, general query decomposition benefit or an independent historical timestamp. Implementation and actual acceptance status belong in the execution record, not in this protocol.
