---
title: "Does the evidence answer the whole question?"
description: "Fresh paired questions distinguish complete support from topical retrieval, with explicit alternatives and jointly required evidence."
date: 2026-11-25
draft: false
tts:
  enabled: false
feedback:
  enabled: true
---

Finding the right document is not enough. In the completed retrieval comparison, the original search found all eight relevant documents first, but only three questions had their required evidence in that first result. Four questions unsupported by the selected sources also returned passages. Those matches establish neither a supported answer nor an incorrect generated answer: this system has not generated answers.

The next experiment asks whether search retrieves **all the evidence needed to answer a question**. It uses twelve fresh questions arranged in six matched pairs over the same four retained sources. Each pair keeps a similar topic but changes one requirement: one question has sufficient support in the sources; the other does not. The existing raw-text search remains fixed. This protocol defines preparation and evaluation separately; implementation tests or a prepared question set do not count as completed retrieval results.

## What counts as sufficient support

A question may have more than one sufficient source passage. It may also require several passages together. The new cohort records these possibilities as support bundles:

- Within a bundle, **every span is required**. A question about both a rule and its exception needs evidence for both.
- Between bundles, **any complete bundle is sufficient**. Retrieving one complete explanation should not be penalized because another equivalent explanation exists.
- Partial evidence from different alternatives cannot be combined into an undeclared sufficient bundle.

Spans retain their exact source observation, half-open UTF-8 byte offsets and slice hash. Coverage requires the returned raw intervals to cover every byte without a gap. A bundle may cross documents. The semantic judgment that its text answers the question remains a reviewed annotation; matching bytes alone cannot prove that judgment.

An unsupported question has no bundle. Its label means that the answer is not supported by these four selected sources. It says nothing about all possible sources. A proposition explicitly refuted by a source is answerable: a supported “no” is different from missing information.

## Prepare before searching

The curator reads the selected sources and earlier questions, creates six fresh pairs and records how each differs from earlier obligations. A separate reviewer checks every sufficient bundle, unsupported label, pair and novelty claim against the complete selected source set. At least one pair must be anchored to each source. Genuine alternative or conjunctive support is included where available; its absence is reported rather than filled with invented examples.

The cohort, machine-readable protocol and review record are retained as exact immutable byte artifacts before either new retrieval starts. Their freeze also binds the source corpus, projected question IDs/text, selected scoring contract, candidate algorithm, runtime and two intended run keys. The selected candidate is checked against the retained C3 raw reference; obtaining its identity requires no trial search. The review and gold labels are evaluator inputs and do not enter the candidate index.

Preparation is itself a bounded read-only assessment. It reconstructs the retained inputs, validates the freeze and reports actual case counts, evidence structures and represented entity families. It reports no retrieval quality and invents no future result hashes. Only validated preparation selects the two-run execution step. A later evaluation reconstructs the same frozen inputs and both completed executions.

Before creating the freeze, preparation also checks that the fixed runner can accept the intended run keys and compiled queries, that its result depth supports scoring through five, and that both phases fit the existing capture limits. The capacity calculation uses the verified unchanged raw projection, known artifact bytes and conservative event-size bounds; it runs before input captures and again while appending the freeze. This checks the planned input capture, not unknown report sizes or a reservation against unrelated later writes. Final report-size checks remain in force.

Creation and historical validation have different rules. First creation refuses existing intended starts. Exact replay after correctly ordered later executions returns the original freeze without adding another event. Changed bytes, changed bindings, a late freeze or reversed execution order are errors. A local event chain records local ordering; it is not an independently witnessed timestamp.

This is a prospectively frozen **development cohort**, visible to the builders. The team has seen earlier results. Separate curator and reviewer roles improve the review process but do not make shared files a sealed holdout. Any correction after new results are inspected requires an explicitly amended version, preserving the original evidence and exposure record.

## Measurements

Every ratio retains its numerator and denominator. Empty valid results remain in the denominator; missing or invalid executions produce diagnosis instead of quality scores. A zero denominator is unmeasured.

| Measurement | Meaning |
| --- | --- |
| Complete support at 1, 3 and 5 | Supported questions with at least one complete bundle in the first k results, divided by all supported questions. Each question has one vote. |
| Complete-support reciprocal rank through 5 | Mean reciprocal earliest result prefix that completes an entire bundle; a miss contributes zero. |
| Complete source set at 1, 3 and 5 | Supported questions for which all source IDs of at least one bundle appear. This is a coarse provenance diagnostic, not sufficient support. |
| Unsupported-query retrieval through 5 | Unsupported questions returning any passage, divided by all unsupported questions. This is not an answer error rate or calibrated abstention. |
| Empty results | Valid empty queries divided by all queries, with supported/unsupported breakdowns and reasons. |
| Matched-pair outcomes | Complete support for the supported member and any hit for the unsupported member, both at five. Four descriptive buckets account for every pair; they are not an answerability classifier. |

Per-case records retain each bundle's covered and required spans, earliest complete prefix and returned raw window IDs. Per-family and per-relation reports retain their eligible counts. Families may overlap, so their counts are not additive. All seven established entity families appear in the inventory, including unmeasured families. These four documents cannot establish universal entity coverage; a seven-family macro score would conceal the missing evidence.

Schema-1 scoring keeps its original meaning. The new scoring contract, `retrieval-coverage-evaluation-v2`, changes both questions and support semantics. Comparing its aggregate against the earlier gold-span score would not establish an improvement. Within this experiment, both raw runs must reproduce their ordered results, projection and complete evaluation under the same frozen measurement identity.

## Limits and continuation

The actual experiment has twelve questions, six pairs, four sources and exactly two fresh raw executions. Generic validation permits at most 64 questions, four bundles per question and eight spans per bundle, with duplicate and empty bundles refused. Each cohort, protocol and review artifact is limited to 1 MB. Existing capture limits remain 128 artifacts, 16 MB total, 256 prefix events and 4 MB prefix metadata. Each fixed program has a 30-second cooperative budget and a 60-second outer process limit. No model calls, new source collection or external spending are part of this experiment.

The next action follows the recorded result:

1. Invalid evidence, review or execution selects diagnosis; valid differing repeats select reproduction repair.
2. Reproduced results with any incomplete supported question select a bounded inspection of the missed bundles and returned passages.
3. Reproduced complete support selects a bounded design of the additional evidence needed to study answerability, including unsupported matches and unmeasured families.

Both valid branches preserve the complete report and retain the raw baseline. Neither authorizes tuning repeatedly against these newly visible questions, silently changing gold, generating answers, increasing budgets or acquiring more sources. Each subsequent change needs its own explicit inputs, measurement contract and bounded worker. This makes completion trigger an informative next step without treating activity itself as progress.
