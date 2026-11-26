---
title: "Stepwise improvement loop bootstrap"
description: "Verified program workers, review fixes, metric controls, and the queued next implementation step."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: true
draft: true
---

The first two real assessment workers ran on **25 November 2026, America/Los_Angeles**, with ledger completions at **26 November 2026 03:27:13 UTC**. This is an execution record of synthetic controls, not a predictive experiment or evidence of learned improvement.

## Programs and handoff

A supervisor program dispatched the deliberately degraded candidate through a fresh Python process, read its recorded successor ID, then dispatched the copied-answer reference control using that predecessor. Both processes exited successfully. The shared persistent improvement store is separate from the observatory and from disposable worktrees. Start/output/finish receipts and exact input bytes are retained locally; they are not published here.

| Control | Correct checks | Provenance | Coverage | Worst-family accuracy | Successor |
| --- | --- | --- | --- | --- | --- |
| Degraded | 18/30 | 23/30 | 30/30 | 0.5 | Repair evidence mapping |
| Reference oracle | 30/30 | 30/30 | 30/30 | 1.0 | Build source-span assertions |

Both controls cover seven entity families and nine dimensions. Both have zero temporal violations. The reference deliberately copies expected answers. Changing from the degraded control to the oracle tests the handoff and reporting machinery; it does **not** establish that an agent repaired a representation or learned anything.

The ledger verifies 14 events, two completed assessments, and no unfinished run. Its queued successor is `bootstrap-20261126-positive:next`, action `build_source_span_assertions`. Scale changes remain disabled. The recorded comparison is descriptive and uses identical suite/evaluator/policy hashes.

## Validation and independent review

- **75 engine tests passed**, including the 20 evaluator and 18 controller/dispatch tests.
- The production site build passed. Its existing configuration skips TypeScript/lint validation; no TypeScript source changed in this work.
- Existing CI was extended with positive/negative control assertions and a real subprocess/status smoke check. The workflow steps were exercised locally; no remote CI result is claimed.
- Independent reviewers reproduced and verified fixes for changed-contract comparisons, oversized output after durable completion, and concurrent run-key reuse.

A changed suite, evaluator, or policy now yields `incomparable_contract_change` without a gain or target-achievement claim. A completed assessment with failed delivery remains discoverable by its authoritative event reference, including matching oversized retries. A concurrent stale worker cannot reuse a run key under the claim lock.

## Recurring supervisor

The existing `epiphysics-research-and-evidence-loop` heartbeat was updated through the app tool and its stored configuration verified: active, hourly, attached to this chat. The prompt delegates construction to scoped builder agents and assessment to fixed programs, with immediate follow-up during each bounded wake. Each wake permits at most three core steps and 30 minutes of active work, preserving the queued successor afterward. Future execution still depends on the host/session being available.

The supervisor also retains the daily observatory capture key and the separate publication workflow. No new scheduler, paid external API, deployment, or business transaction was introduced.

## Next work

Packet A must add assertions tied to exact captured source spans, units, world/knowledge time, revisions and unresolved conflicts. Its acceptance needs new independent fixtures, a versioned `source_span_resolution` metric and a reviewed selector update. The current evaluator cannot measure that capability and would otherwise keep recommending it. The next worker should implement a bounded part of Packet A, not repeat the oracle controls.
