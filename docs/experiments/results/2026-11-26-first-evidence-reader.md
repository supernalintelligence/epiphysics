---
title: "The first evidence reader: what failed"
description: "Six retained answers exposed an ambiguous reference rule and an interrupted acceptance process."
date: 2026-11-26
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

The first reader test ran all six questions once. Five answers included the required evidence and one valid title reference excluded by the scoring key. The sixth answer abstained despite citing a statement that explicitly limited the claim's scope.

The separate evaluator recorded zero fully completed answers under the original exact-reference rule. **That score is provisional: final acceptance was interrupted.** The original questions, key, outputs and scores remain unchanged. We did not rerun the reader or rescore edited answers.

This was a small deterministic program reading the [research map](/research-map), with no model calls or network access. It tested explicit relationships and metadata, not general reasoning or human understanding. The [registered protocol](/experiments/evidence-navigation) describes the separation of candidate authorship, questions and evaluation.

## What the answers showed

| Question type | Retained observation |
| --- | --- |
| Two source questions | Both included the required references and supported interpretation, plus an excluded title reference. |
| One directed qualification | Required references, direction and interpretation matched; an excluded title reference remained. |
| One scope statement | The answer cited the scope statement but returned “insufficient support.” |
| Two proposed follow-ups | Both preserved the proposal/result distinction and required references, plus an excluded title reference. |

The five extra references point to real fields. They are not fabricated citations or missing evidence. Independent inspection found that each answered output differed from a complete permitted answer only by its additional anchor title.

The protocol disclosed that valid extra metadata could fail exact completion. But the public interface did not enumerate the rule that excludes titles for these operations. The test therefore measured an incompletely specified reference-selection convention alongside evidence navigation. The pre-run review did not resolve that ambiguity. This finding does not authorize changing the original key after seeing the answers.

## What interrupted acceptance

The runner and evaluator completed. During the final acceptance check, the supervisor's process-inventory command exceeded its half-second limit. The supervisor killed and reaped the acceptance process after 43.182 seconds, before its closing deadline. Why the inventory command stalled is unknown.

Independent reviewers checked the retained process records, source identities and unfinished claim. After a verified backup, the supervisor closed that claim as a recorded failure without repeating any study stage. The original 1,335 ledger events remained unchanged; the failure is event 1,336. No accepted score or comparison result was created.

This separates two findings: the reader's answers exposed a measurement ambiguity, while supervision failed to finish the acceptance workflow. Neither should be hidden by treating the other as the whole explanation.

## The next test

The proposed next comparison uses a new independently authored cohort and explicit public reference-selection rules. It asks whether those rules reduce failures caused only by valid redundant references, while preserving detection of false evidence and appropriate abstention. This comparison has not run.

Before another trial, the caller also needs a checked automatic failure handoff. If a supervised acceptance process fails, the system should preserve its attempts, record the failure and queue diagnosis without requiring a manual rescue. An unresolved recovery must remain visible.

Six selected cases cannot establish general accuracy, an advantage of graphs over text, predictive skill, business value or usability. No external timestamp witness or live deployment was part of this run. Runtime model calls and external spend were zero; that excludes the work of building, reviewing and supervising the system.
