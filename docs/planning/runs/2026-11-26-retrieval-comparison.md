---
title: "HTML extraction changed ranking, but did not improve support"
description: "A reviewed four-run representation comparison, its regressions, and the measured handoff to fresh coverage."
date: 2026-11-25
draft: false
tts:
  enabled: false
feedback:
  enabled: true
---

The fixed HTML extractor did not improve supporting-passage recall on this development set. It reduced first-result source recall from 8/8 to 7/8 and worsened source and support reciprocal rank. Both methods reproduced exactly within their two runs. The raw method also reproduced the historical baseline. The controller retained the raw baseline and selected fresh coverage and answerability work; a builder began that next design while this result was being integrated.

This is a four-source, twelve-question retrospective development result. It does not establish that HTML extraction is generally harmful, that lexical retrieval answers questions correctly, or that a broader representation theory is validated. The [fixed protocol](../../experiments/retrieval-html-comparison.md) was proposed after inspecting baseline errors. No query, gold span, recipe, scoring formula or acceptance floor was changed after these outputs.

## Measured result

Eight questions have required source spans; four are unsupported within the selected evidence. All twelve returned passages in both methods. None were dropped, treated as an execution failure or answered by a model.

| Metric | Raw | HTML text | Change |
| --- | ---: | ---: | ---: |
| Source recall at 1 | 8/8 | 7/8 | −0.125 |
| Source recall at 3 and 5 | 8/8 | 8/8 | 0 |
| Full gold-span recall at 1 | 3/8 | 3/8 | 0 |
| Full gold-span recall at 3 and 5 | 7/8 | 7/8 | 0 |
| Source reciprocal rank through 5 | 1.000000 | 0.937500 | −0.062500 |
| Gold-span reciprocal rank through 5 | 0.625000 | 0.604167 | −0.020833 |
| Unsupported questions returning passages | 4/4 | 4/4 | 0 |
| Empty queries / execution failures / missing outputs | 0 / 0 / 0 | 0 / 0 / 0 | 0 |

The original supporting-window miss, `dev-opentimestamps-01`, remains a support miss through five results. Its first returned source also moves from the gold source to another source. For `dev-anthropic-02`, the earliest prefix covering support moves from two results to three. Ranked raw windows change for seven queries, while the other five remain unchanged. No method is adopted from this comparison.

Only HTML indexing changes; the three Markdown projections remain exact raw slices. All 82 raw windows remain, and none becomes empty in this particular corpus. The changed HTML index also changes corpus-wide search statistics, so unchanged Markdown text does not guarantee unchanged ranking. Cross-method BM25 values are not confidence scores. Raw-window support scoring does not assert that every gold byte survived extraction.

## Reproduction and identity

The experiment extends a verified copy of the original 40-event archive, preserving every inherited event hash and source blob. The original archive remains read-only and unchanged. The new store retains the fixed protocol, reviewed freeze and both supervisor programs before the four search claims. No archived historical implementation is executed.

The raw pair uses keys `control-html-comparison-v1-raw-a` and `control-html-comparison-v1-raw-b`; HTML uses the corresponding `html-a` and `html-b` keys. Each launches a fresh process and index. The raw bridge passes before either HTML execution. New schema-2 receipts retain the recipe, projection maps, source/dependency/runtime identities and costs. Historical schema-1 receipts remain unchanged.

| Binding | SHA-256 |
| --- | --- |
| Pre-execution protocol bytes | `c9ff07509da28349c15a73332a696c3d1e241e3bca0dd3b4693c58858f43c024` |
| Reviewed execution freeze file | `770c2c4dd8fc1c54af44b52b741ef42bbbea48e013f9e1aec24b72991f0ab052` |
| Raw ordered results, both runs and original C1 | `e2b906b69f1dd285fb4968247b624034c542eb045a76a3d845bac6dcf6b1acf4` |
| HTML ordered results, both runs | `4593ae84a723c1f1e7e00ea435d534395cd72151a7c246c26132c9141594c327` |
| Raw projection, both runs | `12be94cbaca10cb218913c2f9b47462699bf4534482b7dd23590ca639acfb4f3` |
| HTML projection, both runs | `eccb0008c62f14cfb135a9085f62eabd03d75debb745ceee62842ec69fcd91aa` |
| New common measurement contract | `d00059031feb4fdb74ed3e5ed46ca5b655927ccdec3ab5ecac377ba8b1df8787` |
| Historical C2 measurement contract | `8d6ee041fbc84cd04ea3c3622546447e75d3dd1d08f8f73b0c80f8559741f083` |

Moving validation into a neutral module creates a new measurement implementation identity. The read-only bridge preserves every original count, metric and per-case value; that numerical agreement does not equate old and new identities. Accordingly, the controller reports the prior C2→C3 action outcome as `incomparable_contract_change`. The raw/HTML delta above compares only the four fresh runs under the same new contract.

The adapter checks exact declarations, fixed arm order, common measurement and repeated outputs. It retains protocol bytes as an opaque binding. The reviewed supervisor separately enforces static protocol agreement, runtime freezing and the historical raw bridge. Neither local receipts nor this procedure provide an independent execution or timestamp witness.

## Costs and limits

The exact C1 runtime is Python 3.14.8, Unicode 16.0.0 and SQLite 3.53.4, with runtime hash `bbd195a3ce3dbe621affa40c3e43147dbb4ed5d62624c67c19e34a7f1ce39c2f`. Each run keeps the 30-second cooperative limit and 60-second fresh-process timeout. The supervisor explicitly invokes the original interpreter.

| Run | Caller seconds through process exit | Inner seconds before locked revalidation | Projection bytes | Indexed bytes | Mapping pieces |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw A | 0.200872 | 0.061738 | 206335 | 164866 | 82 |
| Raw B | 0.194871 | 0.060105 | 206335 | 164866 | 82 |
| HTML A | 0.315142 | 0.117435 | 313428 | 141302 | 1362 |
| HTML B | 0.333310 | 0.111580 | 313428 | 141302 | 1362 |

The four caller durations sum to **1.044195 seconds**. Both arms read the same 144,898 source bytes; indexed bytes count overlapping windows. HTML reduces indexed text but increases retained mapping bytes. These four fixed-order timings are descriptive, not a causal performance estimate. Separate phase times, peak memory and builder/reviewer effort remain unmeasured. The fixed programs make zero model calls and incur zero external spend; that excludes the supervising/building/reviewing agents.

The actual assessment captured 35 artifacts totaling 1,508,406 bytes, within the unchanged 16 MB bundle and other declared bounds. Its dispatcher completed in 9.092802 seconds; the outer assessment caller took 9.328843 seconds. Evidence database, journal/blob inventory and logical history remained unchanged during assessment.

## Verification and a retained preflight failure

The full engine suite passed **487 tests in 349.479 seconds** under the exact C1 runtime. Earlier validation also passed 485 tests plus two later cases under Conda Python 3.12. The changed CI program passed four fresh owned-fixture processes, separate scoring and a real coverage handoff under both runtimes. The pre-execution site build passed; generated content went from 43 to 61 records with no removed slugs and was archived/restored. The final post-result site build also passed, generating 62 records with no removed slugs; its exact artifact was archived and the generated file restored. No browser verification is claimed.

Both independent integrated reviewers found no actionable production-code issue. Six unguided and fifteen guided checks covered raw compatibility, source selection, exact maps, receipt versions, commit-time mutation, limits, decoder incompatibility, execution order, reproduction failures and coverage continuation. The neutral scorer has no runner/indexer dependency; shared decoding remains an explicit measurement dependency.

A separate launcher review found four issues in the local supervisors: assertions could disappear under optimization; physical checks missed live WAL/new-blob changes; static declarations were derived from outputs; and a timeout could skip its caller receipt. All four were fixed and independently verified under both runtimes before real execution. Explicit gates now survive optimization, state checks include logical history and fresh inventory, eleven static input fields come from the frozen protocol, and simulated timeout retains partial output/status/time before refusing continuation.

The first freeze check then correctly refused an environment mismatch: unqualified `python` selected Conda 3.12.9 / SQLite 3.45.3 rather than the original Homebrew interpreter. This happened before an evidence fork or new retrieval attempt. The refused freeze and diagnosis were preserved; the exact original runtime was selected, required checks repeated, and a new freeze linked to the refusal. No protocol or experimental input was relaxed. Local evidence is retained under `.supernal-local/retrieval/control-development-html-comparison-v1/`, including `initial-runtime-refusal/`.

The separate publication dependency repair is integrated at `6f9b5e7`: the unchanged moderate audit gate passes with zero moderate/high/critical findings and documented low findings. That repair does not establish rendered layout or deployment.

## Persistent handoff

The actual assessment `retrieval-comparison-20261126`, dispatch `3df58467e3564a448f82590d3a264f55`, completed and atomically queued `prepare_retrieval_coverage_evaluation` as `retrieval-comparison-20261126:next`. The observed unsupported-query retrieval rate is 1.0; its target and estimated success probability/cost remain null. This selects new evidence and coverage work rather than another recipe change on the same twelve visible questions.

The improvement ledger verifies **193 events, nine completed assessments and no unfinished claims**, with head `2446a79acc1af8aee00ef5325205bdd261116e848a0aeb508effb50ada0b9949`. The experiment ledger verifies **112 events**, with head `fa7c829132b559726f50db2a7c122d02ca152c95b03945c79739678a92f52f61`. Raw remains the operational baseline; no deployment, spending, answer-generation or workload expansion is triggered.

The next scoped builder is preparing a fresh-question protocol with explicit alternative sufficient support, jointly required evidence, matched supported/unsupported requests, denominators and coverage limits. The four current provider/protocol sources cannot establish universal entity-family coverage. The existing supervisor continues that step while the comparison record is integrated; the scheduled heartbeat remains recovery support, not proof of an always-running host.
