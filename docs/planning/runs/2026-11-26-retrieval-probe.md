---
title: "Separate questions recovered the missing evidence, at a larger reading budget"
description: "Two fixed repetitions recovered both required clauses; the changed retrieval budget prevents an improvement claim."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

Asking the two parts separately recovered the evidence missing from the original joint question. Both fixed executions returned identical ordered results. Discovery support was complete within five passages; direct payment-commitment support was already complete in the first passage.

| Declared clause | Complete at 1 | Complete at 3 | Complete at 5 |
| --- | --- | --- | --- |
| Discover supported capabilities | No | No | Yes |
| Commit payment state | Yes | Yes | Yes |

The union of both top-five lists contains complete support for the original joint question. It uses **ten distinct passages**, totaling 20,480 window bytes and 18,688 unique source bytes. The original whole question returned five passages, totaling 10,240 window bytes and 9,728 unique source bytes. This result demonstrates sensitivity to asking separate questions under a larger selection budget. It does not establish an equal-budget gain or justify adopting decomposition generally.

The [fixed protocol](../../experiments/retrieval-fixed-clause-probe.md) permitted exactly two repetitions, with the same saved corpus, raw-text representation, queries and runtime. No alternate wording or third execution ran. Original annotations and the [C4 score of 5/6](2026-11-26-retrieval-coverage.md) remain unchanged. These questions and outcomes are development data visible to the builders. No answers were generated, and no predictive or business advantage was measured.

## A verification failure, retained and repaired

Both retrieval processes completed successfully. The first attempt to assess their captured evidence failed: the transport copied selected run artifacts but omitted some older observation blobs from the inherited ledger. The checker correctly rejected that incomplete copy because it verifies the whole retained prefix. The original archive and working evidence were intact.

The repair copies every observation blob in the bounded prefix through the existing size, hash, file-type and total-capacity checks. It changes only the assessment adapter. The original execution gate, old adapter bytes, failed preparation record, queries, retrieval outputs and measurement helper are retained. Before changing the adapter, the unchanged helper evaluated the original working evidence and saved its result as the comparison reference. The repaired captured assessment equals that same measurement core exactly. It retains 82 input artifacts and 83 artifacts including its report, totaling 2,376,567 bytes; source hashes and modification times remain unchanged. This is a post-execution transport repair, not a new experiment or a retrospective rewrite of its protocol.

The original failure receipt reports `input_evidence_unchanged: false` because that early utility conflated any preparation error with mutation. Its separate checks found no mutation. The repaired receipt records the evidence comparison separately from preparation success.

## Validation and resources

The complete pre-execution suite passed **607 tests in 951.108 seconds**. Those tests ran before the transport repair; they are not a full-suite result for the repaired source. After the repair, all seven affected assessment tests passed in 52.247 seconds, and four historical controls passed in 11.673 seconds. The new inherited-history test reproduced the original failure using the retained old adapter in an isolated copy, then passed with the repair. Two independent reviewers cleared the repair, and six mocked preparation controls covered success, changed results, forbidden retrieval, changed evidence and persistence failures. The CI job window increased from fifteen to twenty minutes because this full suite exceeded fifteen minutes; experimental time limits did not change.

The two retrieval processes took 0.382335 and 0.323651 seconds through exit, totaling 0.705986 seconds. Their inner retrieval measurements were 0.137841 and 0.096924 seconds and exclude locked revalidation and commit; they are contained within, not additional to, the caller times. Fixed programs recorded zero model calls and zero external spend. Total builder/reviewer effort and monetary cost remain unmeasured.

The original archive remains 152 events. The working copy contains 198 events, with two new retrieval starts and two completions. Exact inputs, original and repaired code, local ordering receipts and both outputs are retained under `.supernal-local/retrieval/control-fixed-clause-probe-v1/`. Public content contains authored questions and aggregate results, not raw third-party snapshots. Local hashes and timestamps are not an independent execution or timestamp witness.

## Acceptance and next work

The fixed worker completed as `support-probe-20261126` and atomically selected **`prepare_control_exchange_decision_pilot`**. The controller contains 516 verified events, thirteen completed assessments and no unfinished claim. The prior quality outcome is `unmeasured`; the next metric, target, estimated cost and success probability remain null. Scale changes remain disabled.

The assessment recorded 18.364754 seconds before completion-time revalidation; the dispatcher took 20.833990 seconds and the outer caller 21.714997 seconds through exit. All completed within the existing limits. The dispatch ran from `2026-11-26T12:08:43.126805+00:00` through `12:09:03.960934+00:00`, returned zero and delivered its output. Dispatch ID: `9b01109eb03e47bd8343d4314ceb9a9d`.

Reproduction bindings:

- Unchanged measurement core: `f8b99a3dd11497c883b9840e08896654d512381211b8eb0914a1e4ee0f2ba4be`.
- Probe contract: `2daf8ed99910bec98fe7cd0b3fa33ea5a7af0bea9013f859f6930def6674c6ba`.
- Repaired captured assessment: `6682f712f02b5bd2fa9ea3ee135e86e04d4081fce2a5a4c4afbea491563effc5`.
- Final controller event: `591be146303bb407e78f0b6256405db0ca91987857d50f189d4bb57de0e2b124`.

The filename retains the UTC run date; frontmatter follows the client-date convention.

The declared successor is preparation for one simulated release-or-hold decision for an agent-delivered artifact. Compare flat and relational views of the same eligible dated evidence, with a lossless control, shared decision rule and explicit construction/reading costs. Keep rights in force, what was known at the decision time and later outcomes separate. This diagnostic ends the visible-query follow-up; it does not authorize live settlement or further tuning of this case.
