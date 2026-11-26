---
title: "C8: fixed fresh exploratory decision comparison"
description: "Preparation, execution custody, independent validation and successor selection."
date: 2026-11-25
draft: true
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

Preparation is active in managed worktree `decision-fresh`, from `2a2427e14cd5b1c55e9db85fe017c805659fa85b`. The accepted predecessor is `improvement:decision-development-20261126:complete`, ledger event hash `7e8eb852b23c2d65d337450b5e8b9d77bbf6129c1d29b2eab3491e746a5f37ba`. Its entire original event is retained in the persistent shared checkout at `.supernal-local/control-exchange/decision-fresh-v1/origin-c7.json`, SHA-256 `c568acda928d2979d184bb3f99e4f3cd803895ba11fc03ce162e72787022563c`. This is a read-only capture of accepted history, not reacceptance through the changed validator.

The [protocol](../../experiments/control-exchange-fresh-comparison.md) fixes one 24-case allocation and 96 attempts. Three builders separately own runner, retained-result validator and generator; root owns the controller and caller. A generator author independently tests the caller, runner author reviews generator/validator, and validator author reviews runner/controller. An additional non-author reviews the whole patch. Root is the only registered experiment runner; a separately assigned custodian generates the actual cohort only after final review and freeze. Individual case and mocked process controls are explicitly development tests, not registered experiments.

The original views, policy, evaluator and two contracts remain byte-identical to C7. Fresh-only retained-artifact ceilings are 16 MiB report, 24 MiB journal and 48 MiB bundle; the larger caps retain all 96 maximum-length failed-output prefixes. C7 ceilings and all production 30/60-second study limits remain unchanged. Research programs make zero model calls, incur zero external spend and produce no live effects. Agent/model coordination and reviewer resources are separate and not represented by these zeros.

Preparation review corrected historical continuity and caller coverage: bind the exact original accepted transition and freeze the outer one-shot caller. Subsequent cross-review found that the caller read a missing report before an existing journal and omitted the journal hash; reads are now independent and transport failure categories retained. Another check found that a claimed caller duration could be shorter than its enclosed program; independent validation now rejects that contradiction. These fixes precede any fresh generation or execution.

Initial focused validation passed 16 controller wiring controls in 4.575 seconds and 20 retained-validator controls in 7.237 seconds. Validator controls include 96 maximal failed-output prefixes, self-consistent false custody claims, no-candidate retained validation and literal historical C7 source identities. All eight production source files remained unchanged during the validator run. Controller controls use real temporary ledgers with explicitly synthetic evidence and stubs for unrelated old probes; they do not manufacture accepted research evidence.

No fresh cohort, actual seed or registered execution existed at this preparation checkpoint. Later sections must distinguish the subsequent real receipts and accepted result from these controls. No push, deployment, browser validation, live transaction or scale promotion is included in this packet.

The complete eight-module decision test collection passed **155 tests in 11.773 seconds** (outer harness 12.090 seconds), with all 79 production-source, test and fresh-script files unchanged. These include 19 caller transport controls after an independent whole-patch review found that the caller pinned implementation but omitted the two contract files. Both contracts are now checked before claim and included in postflight checks; preclaim and during-run mutation controls pass. A public journal-description error was also corrected: each attempt records worker return and evaluated outcome, not a start event.

Five legacy queue, ownership, selector and real dispatcher controls passed in 43.940 seconds with all 79 source/test files unchanged. A read-only check of the actual persistent C7 event confirmed the full captured event and all six historical implementation hashes, with ledger integrity unchanged at 556 events.

Review of the private outer execution envelope found that nested new process groups could escape its timeout. The outer transport now owns one group; the caller, driver and fixed workers inherit it. Nested transports reap their direct children; the outer owner terminates the entire group even when its direct parent exits early. Harmless real process-tree controls confirm there are no running descendants in those cases. Explicit eligibility checks replace optimization-sensitive assertions, and malformed, oversized or absent caller receipts preserve the outer failure record and original launch error. The outer envelope measures through final caller receipt persistence; its own postflight and receipt writes have a separately stated timing scope.

Final production-source validation after the group repair passed **158 tests in 9.708 seconds**, with all 79 source/test/script files unchanged (outer harness 9.932 seconds). The five earlier legacy controls remain evidence for the unchanged controller paths; they were not relabeled as part of this final collection. Validation logs and manifests are retained privately under `decision-fresh-v1/validation`. No actual fresh cohort was used by these checks.
