---
title: "C9 retained decision information diagnosis"
description: "Implementation, historical-input continuity, validation and the next measured handoff."
date: 2026-11-25
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

Work began in managed worktree `decision-information`, based on `0e940daab1293437172327881ba5bbd9c0d1ae79`. The worktree then fast-forwarded to `6e23501513b40839ec09decbc72f5465e245ee54` after the separate site-loading fix landed; no research source or input changed in that update. The accepted evidence origin is `improvement:decision-fresh-20261126:complete`, hash `4d89e0f7672afd881ea0a9a8b95a3b31bc66f3c4d1e9934978b4392f4f7cc17a`. It queues `decision-fresh-20261126:next / investigate_decision_information_limits`. The persistent store has 606 events, 15 completed assessments and no unfinished claim at this starting point.

The original event was captured read-only in `.supernal-local/control-exchange/decision-information-v1/origin-c8.json`, SHA-256 `8ce1a0772b24775c44f7b65ffc7af22bd9d68cab2c0b0c61f6f2d3c4307bdc5d`, at `2026-11-26T15:52:04.621762+00:00`. That capture ran no diagnostic. All private research evidence remains in the persistent shared checkout, outside disposable worktrees.

The cleared third plan revision has SHA-256 `a717feb2b38b69e264bc7a1bb746089a85a9a24ae013fb956016522617bad276`. Independent review found no remaining continuity issue. Earlier revisions remain retained; the correction removes an unusable recovery/requeue step in favor of a directly checked full diagnostic after a verified operational failure.

One builder owns the new diagnostic module, explicit decision-assessment bridge, contract and focused tests. Root owns controller routing, queue/claim/completion checks and their controls. A separate worker measures the site bundling repair in `site-chunks`; it does not edit research inputs or dependencies. Non-author review precedes either landing. SCI retains its existing scientific-note and publication ownership.

The [public protocol](../../experiments/control-exchange-information-limits.md) separates dated availability, bounded retention and verification quality. Historical bytes resolve through accepted observations and blobs, never deleted worktree paths. Current diagnostic sources have identities separate from the accepted C8 implementations. Preparation captures and validates inputs without computing the diagnostic; this allows exact successful replay to return its recorded result without recomputation. The source and contract must be frozen before the reported diagnostic pass.

Status at this checkpoint: implementation in progress. No C9 diagnostic, accepted transition, new cases or candidate execution has occurred. The queued C8 successor remains authoritative until a checked C9 completion. Checkpoints trigger continued work; the existing 15-minute recovery wake is a fallback for interrupted sessions, not the execution pace.

An early independent controller review found a preclaim gap: malformed or wrong-phase evidence could replace the protocol-preparation successor with a generic failure task. The protocol action now receives the same preclaim protection as diagnosis and review tasks; a regression control covers both malformed and wrong-phase input while requiring the original queue and event count to remain unchanged. This fix has been written; execution of its test awaits the stable-source window. The early review covers controller wiring only, not the new diagnostic implementation or historical-proof validation.

Initial controller/assessment validation passed 46 tests in 9.308 seconds with production sources unchanged. The first complete nine-module decision run executed 186 tests in 20.252 seconds: 185 passed and one test fixture failed because it assigned a revision reference to a verification event, which C8 does not support. The fixture was corrected to retain two distinct claims with unestablished revision semantics; all 16 diagnosis controls then passed in 4.247 seconds, with source and test bytes unchanged. A subsequent pure timing-boundary control passed independently. Both real-controller tests passed in the broad run: initial diagnosis plus zero-computation replay, and a durable postclaim failure followed directly by a corrected 96-attempt diagnosis and normal successor. These are owned synthetic transport controls, not execution on the retained research cohort.
