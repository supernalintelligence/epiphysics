---
title: "The missing evidence was indexed, but not returned"
description: "A checked diagnosis of the joint-question retrieval gap, with the original scores preserved and one bounded follow-up selected."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

The remaining support gap in the [fresh coverage evaluation](2026-11-26-retrieval-coverage.md) concerns a question with two parts: discovering supported payment capabilities and committing payment state. The five returned passages covered the commitment part. They omitted the capability-discovery passage, even though that passage survived intact in the indexed representation.

An independent reviewer examined all five returned windows and the relevant retained source text. The reviewer found no alternative complete answer to both parts in those windows. This supports a retrieval-gap diagnosis for this fixed development case. It does not identify the omitted passage's rank, the cause of the ranking, or a failure in answer generation. No answer component ran.

| Required evidence | Bytes covered in the five returned windows | Retained in the raw representation |
| --- | ---: | --- |
| Capability discovery | 0 / 115 | Complete |
| Direct payment commitment | 218 / 218 | Complete |
| Alternative flow identity | 223 / 223 | Complete |
| Alternative flow durability | 148 / 317 | Complete |

The first evidence bundle requires discovery and direct commitment. The alternative requires discovery plus both flow spans. Neither bundle is complete in the returned windows. The checker keeps alternatives separate and counts overlapping bytes once. All 82 retained raw rows match their source slices. The [diagnosis protocol](../../experiments/retrieval-support-diagnosis.md) distinguishes these mechanical findings from the reviewer's semantic judgment.

The original C4 result remains **5/6 supported questions with complete declared support**. This diagnosis introduces no new retrieval score, quality improvement, source capture or baseline change. Its sole focused case is `coverage-05-supported`; no failed cases remain deferred. The data and outcomes were visible to the investigators, so this is development diagnosis rather than a protected final evaluation.

## What the program completed

The schema-3 `support_diagnosis` path checked the saved receipts, frozen input bytes, original assessment and independently reviewed interval findings. It captured 47 input artifacts and retained 48 artifacts including its report, totaling 1,786,402 bytes. It invoked no search, indexing or retrieval-scoring function. The 152-event source archive remained unchanged.

The fixed worker completed as `support-diagnosis-20261126` and atomically selected **`prepare_focused_support_followup`**. The controller now has 406 verified events, twelve completed assessments and no unfinished claim. The prior quality outcome is `unmeasured`; the successor's metric, target, cost estimate and success probability are null. Scale changes remain disabled.

The next preparation defines one fixed two-clause diagnostic under the same raw representation and corpus. Two top-five outputs permit ten window occurrences, compared with five for the original whole question. Any recovered evidence must therefore be reported as local sensitivity under a changed selection budget, not a C4 score improvement or evidence for adopting decomposition. The diagnostic has not executed at this record's cutoff.

## Validation and resources

All **574 engine tests passed in 563.611 seconds** under the retained Python 3.14.8 / SQLite 3.53.4 runtime. Both implementation reviewers cleared the final code. Tests include real subprocess dispatch and replay, exact frozen-file binding, independent interval controls, attributed unresolved judgments, concurrent claims and refusal of live ledger corruption. The CI job window increased from ten to fifteen minutes because the full suite alone took 9.4 minutes; experiment limits remain unchanged.

Three concrete issues were repaired before actual acceptance: reformatted frozen cohort bytes were being accepted; live-ledger verification could enter the invalid-input handler; and caller output-write failures could skip final state checks. The caller repair passed twelve prelaunch collision controls and ten mocked execution/write-failure controls.

The assessment recorded 8.978124 seconds before completion-time revalidation. The dispatcher took 10.411141 seconds, and the outer caller took 10.885173 seconds through process exit. These nested durations are not additive. Revalidation remained inside the 30-second acceptance budget; the worker limit stayed 60 seconds. The fixed programs report zero model calls and external spend. Builder/reviewer effort and total monetary cost remain unmeasured.

The caller ran from `2026-11-26T10:52:43.973333+00:00` through `10:52:54.859488+00:00`, with exit code zero and delivered output. Dispatch ID: `24ebeeb6eb0b4475a54f54cc171b6ffb`.

Reproduction bindings:

- Deterministic findings: `cd29d5da638b6f1fe50b757aec3b5a9fa2ab3686c2baae1004734dbb07f3016c`.
- Independent semantic-review bytes: `b947c30d5428099489fe1144593115a05448a66f42f75cb9e25aa4ba6b40a0af`.
- Diagnosis contract: `b838727aad436562968a4301f042ca7f340bfb06c2b2dd796eb4ee61fed9aee1`.
- Final controller event: `b6a9f2cbe8962859c0d9330e1cd3687246833d45138c2f3d052070d2667f9565`.

Exact inputs, captured code, reviews and receipts are retained locally under `.supernal-local/retrieval/control-fresh-coverage-diagnosis-v1/`. This public record contains no raw third-party source text. These are local integrity records, without an independent timestamp or execution witness. The filename uses the retained UTC run date; frontmatter follows the client-date convention.
