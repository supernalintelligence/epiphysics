---
title: "Fresh coverage reproduced, with one incomplete declared support bundle"
description: "Two frozen raw-retrieval runs, six matched question pairs, and a measured handoff to support diagnosis."
date: 2026-11-25
draft: false
tts:
  enabled: false
feedback:
  enabled: true
---

The raw retrieval baseline reproduced exactly on twelve fresh development questions. Five of the six supported questions had a complete declared support bundle in the first result; one question lacked a complete declared support bundle through five results. All six unsupported questions also returned passages. The controller queued a read-only diagnosis of the remaining support gap. That diagnosis has been dispatched and is not complete at this record's cutoff.

The [coverage protocol](../../experiments/retrieval-coverage.md) uses six matched supported/unsupported pairs over the same four retained sources. Questions, annotations, review bytes and run keys were frozen before fresh retrieval. The cohort was visible to builders and reviewers; it is not a sealed holdout or a population sample. The raw method remains the operational baseline. No recipe, answer generator or adoption rule was introduced.

| Measure | Both runs |
| --- | ---: |
| Complete declared support at 1, 3 and 5 | 5/6 at each cutoff |
| Complete source set at 1, 3 and 5 | 6/6 at each cutoff |
| Complete-support reciprocal rank through 5 | 0.833333 |
| Unsupported questions returning passages through 5 | 6/6 |
| Empty queries | 0/12 |
| Execution failures / missing outputs | 0 / 0 |

A question succeeds when the returned raw windows cover every required span in at least one declared support bundle. Alternative bundles are independently sufficient; spans within a bundle are jointly required. Source-set coverage checks source identity rather than sufficient content. Unsupported passage matches measure retrieval behavior, not hallucinated answers or successful answerability detection. No answers were generated and no abstention threshold was calibrated.

Only `coverage-05-supported` lacks a complete declared bundle. At five results, one of two required spans is covered in its first bundle and one of three in its alternative. The next diagnosis will check for unannotated sufficient evidence as well as the declared spans; this score alone does not establish a causal retrieval failure or that returned text cannot answer the question. The frozen scores remain the reported result. They are not a C4-versus-C1 gain: the questions and complete-bundle scoring contract differ from C1's flat span-recall measure.

The cohort contains **two alternative-support cases, one joint-support case and zero multisource cases**. Family tags overlap: software/service covers twelve questions, organization two, contract/obligation two and representation six. Person/role, physical asset and collective are unmeasured. Ordering, quantity/unit and representation-assurance relations are also unmeasured. At cutoff five, five pairs combine complete declared support with an unsupported passage match; one combines incomplete declared support with an unsupported match. These four provider/protocol documents do not establish coverage of all seven entity families.

The inherited archive contains 112 events. The new store retains supervisor material and the exact cohort/protocol/review inputs before the freeze at event **118**, recorded at `2026-11-26T09:58:31.730517+00:00`. Preparation then reports `ready`, without future outputs or quality values, and queues `execute_fresh_coverage_baseline`. Run A starts at event **119** and completes at **135**; run B starts at **136** and completes at **152**. Each uses a fresh process. Ordered results, projections and evaluations match exactly. Evaluation reports `completed`; both dispatches report `assessed`, assessment `completed`, delivery `delivered`, and exit code zero.

The original archive, inherited event hashes and source bytes are preserved. Saved postflight checks confirm unchanged reviewed code/artifacts and historical-store state, and unchanged input evidence across both assessments. Preparation captures through the freeze; evaluation captures through the second terminal. These are local retained receipts, not an independent timestamp or execution witness.

An independent read-only audit matched both saved evaluations exactly, checked the original 112-event prefix and physical source-store state, and verified the authoritative controller transitions without executing search. The controller has 332 events with head `0c5dc1a00b2c6a9c90cbe7438e19540e40fcba30e2349156006ca727a8ccbd7b`. Preparation retains 43 input/output artifacts totaling 1,426,756 bytes; evaluation retains 46 totaling 1,746,014 bytes. Both remain within the unchanged 128-artifact/16 MB limits; captured prefixes also fit 256 events/4 MB. All three audited stores stayed physically unchanged during the audit.

The study is `control-fresh-coverage-v1`, using `raw-window-text-v1` and scoring contract `retrieval-coverage-evaluation-v2`. Preparation and evaluation share the exact measurement hash below; their assessment identities differ because their inputs and phases differ. Candidate identity remains separate from scoring and controller identity.

| Binding | SHA-256 |
| --- | --- |
| Exact cohort file | `f85a843b068d59f2eca09697dffb1ae64fcd988a142cda46c91e941520e39855` |
| Normalized cohort | `3259c1e5a972cfb05490f08d210c6b2193844c7d510d285b9d0656a091f9a84f` |
| Gold bundles | `c23cf480efd5d97bc28c2699ad2f7b066cbcbf82c2a9f8cf83fdbc9f7b051d67` |
| Queries | `34cca47db4a8c33d37328efd42f583afcb1f379b5a175aaeae098eb10505f103` |
| Protocol file | `301eb07f60a66b987364e534565d20b5334071ac77e00d3dc59456523269c3e1` |
| Review file | `9a97f4b12c0c8abd37eca13f5fe2e0fe27fa2713a66ba90f698acc9d23293272` |
| Freeze event | `facbf1048689076799569ee472544b4b8dcfbf45376998b409c4c7f63539b82e` |
| Corpus | `8506a15404d9377abe3f05744be815711da9030e94a54ab9e5175cfa365fa3d5` |
| Common measurement contract | `b1e5cb28327a490fa2454f3fcb446c906ef43de6c3b2456de069669ecfc0556e` |
| Candidate, including projection | `fececd63368da1b34f339cfcf4668a79abc18acf4fa756ef6cb0975e7d9fb7ed` |
| Ordered results, both runs | `e8cbb1eb54d1729e896aeb1f73970b8b5fce0727c1a219548122454648305f18` |
| Projection, both runs | `12be94cbaca10cb218913c2f9b47462699bf4534482b7dd23590ca639acfb4f3` |
| Run A terminal | `da0b0d98d9dce4f515ef1220c106dd1c191ac17d72e34be1f9208549cf4d9c16` |
| Run B terminal / final evidence head | `292648c3d0c61932d90b44e48c42f1e16b3e689d5664d79f5b48231b3d1557df` |
| Preparation controller assessment | `294409b808308b4b674525dbde03ec1b48391b7da2db357b4e718eb64ace89d8` |
| Evaluation controller assessment | `eabab2d3ad4d16219fa96a178310d998dd11305b10b24d407107553c11f6fb05` |

The exact retained runtime is Python 3.14.8, Unicode 16.0.0 and SQLite 3.53.4, hash `bbd195a3ce3dbe621affa40c3e43147dbb4ed5d62624c67c19e34a7f1ce39c2f`. Each retrieval reads 144,898 source bytes, indexes 164,866 bytes across 82 overlapping windows, retains a 206,335-byte projection with 82 mapping pieces, and returns 14,522 result bytes. There are no empty windows. The 30-second execution/assessment budgets and 60-second dispatcher cap remain unchanged.

| Operation | Inner recorded seconds | Dispatcher seconds | Outer caller seconds through process exit |
| --- | ---: | ---: | ---: |
| Raw A | 0.058824167 | — | 0.204462417 |
| Raw B | 0.057499917 | — | 0.189623541 |
| Preparation assessment | 8.677852959 | 8.966236208 | 9.306005250 |
| Evaluation assessment | 8.872798959 | 9.261825667 | 9.612589375 |

The two retrieval caller durations sum to **0.394085958 seconds**. Retrieval inner timing ends after initial search and validation, excluding locked revalidation and commit. Assessment, dispatcher and outer timings are nested measurements, not additive phase costs. The observed supervision interval is **2618.528959 seconds**, from `2026-11-26T09:16:05.674643+00:00` through `09:59:44.203602+00:00`; it includes parallel work and waits and excludes earlier design. It is neither CPU time nor monetary cost. Whole-step builder/reviewer cost remains unmeasured. The fixed local programs record zero model calls and zero external spend; this does not describe the cost of supervising agents.

Final validation passed **544 tests in 378.622 seconds** under the exact interpreter, plus the owned-source preparation→two-process retrieval→evaluation CI smoke. Both independent implementation reviewers closed their findings. Accepted readiness fixes align run-key grammar, query-token limits and result depth with the actual runner/scorer, and preflight both capture phases within unchanged event/byte/artifact caps before writes and again under the append lock. Boundary and concurrency controls cover refusal before writes and a successful exact-capacity run. This check does not reserve capacity against later unrelated writes; report-size checks still apply at completion.

The supervisor now retains postflight evidence and authoritative state even after child failure or timeout; seven independent mocked failure controls passed. Separate semantic review approved all twelve cases after an omitted sufficient alternative was added before the freeze. Earlier drafts and review findings remain retained. No fresh output informed that correction.

Preparation dispatch `b4d8fed81c4145d182b9623feebd9bba` and evaluation dispatch `5886e7bef1714d45a8242e0e8bc852d5` complete the measured handoff. The persistent queue now holds **`coverage-evaluation-20261126:next` / `inspect_fresh_support_failures`**, with observed complete-support rate 5/6, null target, unestimated success probability/cost and no scale increase. At the saved cutoff there are eleven completed assessments and no unfinished assessment claims. The watcher has dispatched the narrow read-only diagnosis; it has not yet produced a conclusion or changed annotations, recipes or baseline adoption.

Evidence files, exact receipts, reviews and logs are retained locally under `.supernal-local/retrieval/control-fresh-coverage-v1/`. This public record contains no private source text. Its filename follows the retained UTC run date; frontmatter follows the client-date convention.
