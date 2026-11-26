---
title: "A second set of decisions, with the methods held fixed"
description: "One exploratory comparison of compact chronological and relational records, including late evidence, invalid deliveries and disputed authority."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

The [development comparison](results/2026-11-26-decision-pilot.md) found a tie: each compact record supported four valid releases and missed a different opportunity under storage pressure. A lossless record recovered both opportunities. Neither record could reveal a revocation that had not yet been observed.

The next question is whether those methods behave differently on a new, deliberately varied set of cases. We keep the two record builders, shared decision rule and independent evaluator unchanged. A separate custodian generates one batch after the implementation and this decision rule are frozen. There is no search for a favorable seed or replacement batch.

| Situation | Cases | What it probes |
| --- | ---: | --- |
| Evidence arrives late | 6 | The difference between available evidence and rights actually in force |
| Authority changes visibly | 4 | Scoped revocation, regrant and effective time |
| Verification and disputes | 4 | Conflicts, premature closure and invalid or incomplete artifacts |
| Repeated identity | 4 | Earlier releases and what makes two attempts the same exchange |
| Storage pressure | 4 | Which relevant records each compact method loses |
| Direction of roles | 2 | Who granted authority to whom |

Each case runs through the chronological and relational records at 2,048 bytes, and both lossless controls at 32,768 bytes. This produces 96 attempts. The journal retains the declared sequence, each worker return and independently evaluated outcome, and a terminal record: 194 records in a completed run. Missing, malformed, timed-out and overlong outputs count as failures; they do not disappear from the denominator.

The generator varies identifiers, amounts, event intervals and other stated features. Its mechanisms and allocation are hand-designed. These are **fresh exploratory cases**, not a sealed holdout, a representative sample of businesses, or a test of a learning system. The entire retention-and-decision pipeline is compared; a difference cannot be assigned to graph notation alone.

We count valid timely releases, missed opportunities, unsafe and duplicate proposals, invalid-artifact proposals, effects and failures separately. The evaluator sees stipulated world facts and later artifact outcomes. The decision process sees only evidence available by its cutoff. A protective guard refusing an unsafe proposal does not erase the proposal from the score. An unrepresented category remains unmeasured.

The following rule is fixed before generation:

1. Failed conformance, execution failure, or an unauthorized or duplicate effect selects repair and investigation of the retained evidence.
2. At least two additional valid timely releases from the relational method, with no increase in **each** of four proposal-harm counts and no additional failed outputs, selects preparation of a prospective, nonacting test.
3. Otherwise, keep the chronological baseline and investigate the observed information limits.

Two additional releases is a descriptive threshold for choosing research work. It is not a significance test, proof of superiority, or permission to change live authority. The comparison never automatically repeats itself. All branches retain the result and require a new, explicit research question before another experiment.

Generation custody, the caller's first read and execution are separate receipts. Hashes bind the exact sources, contracts and files to the accepted development result. They establish local consistency, not an independent witness of when something first existed. An external timestamp could strengthen that narrow claim; it could not establish that a dataset is complete or that its contents are true.

This step concerns one simulated exchange contract. Recursive adaptation, real businesses, AI-company concentration and prospective forecast accuracy remain distinct research tracks. The purpose of the loop is to make those transitions depend on inspected evidence rather than an increasingly confident description of the same fixtures.
