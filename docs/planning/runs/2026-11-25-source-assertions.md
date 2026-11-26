---
title: "Source-backed assertions and continuous follow-up"
description: "Implemented evidence-span and historical-view contracts, independent review, and the executed handoff to representation manifests."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: true
draft: true
---

On **25 November 2026, America/Los_Angeles**, scoped builders implemented source-backed assertions and two independent reviewers checked them. A real assessment subprocess then consumed `bootstrap-20261126-positive:next` and recorded `source-assertions-20261126:next`, action `build_representation_manifests`.

## What changed

Assertions bind a typed claim to exact byte spans in a frozen evidence snapshot. The engine checks the entire source blob, span bounds and hashes, and snapshot eligibility. Corrections preserve the original event, observer lineage and earlier views; competing reports remain visible. World validity is separate from when the ledger learned the claim. Logical negation, retraction semantics, extraction accuracy and truth adjudication remain outside this slice.

The assessment calls the actual assertion API on isolated synthetic ledgers. Its two new metrics are executable contract counts, not sampling estimates:

| Contract | Result | Interpretation |
| --- | --- | --- |
| Source-span resolution | 8/8 | Accept valid retained bytes; refuse malformed, altered and ineligible evidence. |
| Assertion-history preservation | 6/6 | Preserve historical views, revisions, conflicts, observer lineage and separate world validity. |
| Representation oracle control | 30/30 across seven families | Copied expected answers; no learned improvement claim. |

The new policy is `offline-contracts-source-spans-v2`; the probe contract is `source-span-probes-v1`. The prior run had a different measurement contract. Its comparison is correctly recorded as **`incomparable_contract_change`**, with no gain or target-achievement claim. All fourteen API checks must pass, alongside the representation gates, before the selector recommends manifests.

## Executed worker

Run key: `source-assertions-20261126`. Dispatch receipt ID: `6cc80d4b38c24fd8bf737764b144976d`. The subprocess started at **2026-11-26T04:29:03.446515+00:00** and finished at **2026-11-26T04:29:03.903972+00:00**, returned 0, and took 0.457 seconds. The assessment recorded 0.184 seconds, zero model calls and zero external spend. Exact input bytes and start/output/finish receipts are retained in the dedicated local improvement store.

The reviewed code was assessed in its managed worktree before local integration. This record does not claim remote deployment, an external timestamp witness, or a future heartbeat execution.

## Review and verification

**115 engine tests passed.** The production site build passed; its existing configuration skips TypeScript and lint validation, and this packet changed no TypeScript source. The edited CI checks were also executed locally, including a real subprocess handoff; no remote CI result is implied.

Independent review found an important evaluation-identity flaw: the process could execute older code while recording newer source bytes. The fix binds retained source to the actual executing module code, pins the internal dependency graph, and rejects ordinary edits, unsupported reloads, stale callable/ledger objects, and valid-looking stale bytecode caches. Regressions use isolated package copies; rejected preflight checks write no ledger events, while drift after a claim records failure and diagnosis. These checks are not a security boundary against an operator controlling the process.

## Continued work

The existing heartbeat is active with a 15-minute recovery cadence. During an active session, 30 minutes or three core steps triggers a checkpoint and the next authorized job, not an automatic stop. Recovery checks the active worker and worktree before starting anything, to avoid duplicate work. Per-worker limits and zero external spending remain unchanged.

The next implementation is **B1: representation manifests**—stable method identity across snapshots, distinct candidate instances, retained construction/configuration/ontology/predictor artifacts, evidence bindings, declared cost provenance and a bound forecast adapter. B2 will separately add transformations and loss checks. A queued recommendation does not implement either component; the supervisor must dispatch, review and measure the builder's work.
