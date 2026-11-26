---
title: "Can a reader follow the evidence?"
description: "A fixed six-question test of source links, qualifications and proposed work in the research map."
date: 2026-11-25
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

The [research map](/research-map) links claims to sources, qualifications and proposed experiments. This test asks whether one small program can follow those explicit links and report their meaning without confusing a proposal with a result or a citation with verified evidence.

**Status: first attempt retained; acceptance failed.** All six questions ran once. The provisional evaluator result and independent answer diagnosis are described in [the first-reader report](/experiments/results/2026-11-26-first-evidence-reader). The original attempts and scoring rules are preserved. Building the page and passing software checks did not establish that the map helps people understand the research. This test measures a narrower prerequisite: whether its exported information supports six precise queries.

## What the reader receives

One fixed map and one question are supplied to a fresh process. The question names an anchor claim and an operation. The reader returns source-field references, directed relationships, attributed labels and one of a few declared interpretations. It can explicitly report that the supplied information is insufficient.

The map contains public metadata and claim statements. It does not contain external article archives or the bodies of linked project documents. Following a source link in this test means identifying its recorded metadata; the program does not visit the link. The [map preparation protocol](/experiments/public-research-map) describes how these public records were selected.

| Questions | Requested distinction |
| --- | --- |
| Two source questions | Which source or project document is cited, and what evidence is actually present in the export? |
| Two qualification questions | Which claim is qualified, in which direction, and what explicit limit is stated? |
| Two follow-up questions | Which work is proposed, and how does its status differ from the starting claim? |

Five questions require directed links. One asks about an explicit restriction within a claim statement. The latter does not require a challenge edge. Structured operations make this a literal information-access baseline, not an open-ended comprehension test.

## Freeze before asking

The reader is written and reviewed using unrelated invented examples. Its source is frozen before a different author prepares the final questions and scoring key. A separate reviewer checks that key against the fixed map. The candidate author and candidate process do not receive it; the runner does not read it. Preparation validates the key without running the candidate. Final scoring uses it only after all outputs and termination records are sealed.

The registration identifies the map, ordered questions, key digest, program sources, runtime and budgets before the first attempt. Each of the six questions has exactly one attempt. A failed or missing answer remains in the record. Neither the questions nor the key may be revised to improve a score after seeing the answers. A discovered key defect requires a disclosed adjudication preserving the original evidence.

This separation is a local procedure with retained records. It is not protection against a hostile operator with access to every local file, nor an independently witnessed timestamp.

## What counts

Every answer must cite actual fields and preserve the distinction between an attributed claim, bibliographic information and completed work. The scorer checks an entire permitted answer bundle. Returning fields outside the permitted answer bundles, reversing an arrow or mixing pieces of different permitted answers cannot earn full credit. A valid extra metadata reference can fail this exact-answer rule without being false: the report distinguishes additions not permitted by the key from invalid evidence.

| Metric | Fixed denominator |
| --- | --- |
| Fully supported answers | All 6 questions |
| Correct evidence references | All 6 questions |
| Correct starting-claim status and basis | All 6 questions |
| Correct relationship direction | The 5 questions that require links |
| Source interpretation | The 2 source questions |
| Qualification interpretation | The 2 qualification questions |
| Proposal/result distinction | The 2 follow-up questions |

Results will include counts as well as fractions, individual cases and separate two-case family summaries. Started, parseable and scorable answers are reported separately from correctness. Unresolved answers receive no full-completion credit; unavailable semantic component scores remain unknown. Process errors, malformed output, timeouts, overflow and unstarted cases stay visible. An always-abstaining analytical reference has zero fully supported answers; it is not presented as a separately executed competitor.

The local preparation target is all six fully supported answers, with no additions outside the permitted bundles or unsupported interpretations. Even a perfect result would describe these six selected questions and this literal reader. It would not estimate general accuracy, establish an advantage over plain text, show human usability or measure predictive skill.

## Resources and the next step

The whole registered run has a 15-minute ceiling. Each candidate process is limited to 120 seconds and 16 KiB each of standard output and diagnostics. The map is capped at 256 KiB; questions and key at 64 KiB each; retained study evidence at 4 MiB. Runtime programs make no model or network calls. Their zero metered external spend excludes the separate effort of writing, reviewing and supervising them.

A report alone cannot certify that its evaluation finished. The supervising program separately records the evaluator's exit, elapsed time and exact output. The retained check requires that completion record before accepting scores. Interrupted output remains evidence of an attempt, and does not become a successful result merely because it contains a score.

The recorded result selects the next bounded task:

- Fully supported completion: prepare a new independent comparison, with unseen questions and a stronger reader or a separately designed human study.
- Valid answers with information or interpretation errors: diagnose each failure and choose one specific repair to the reader or public information.
- An incomplete or operationally invalid run: repair execution or retention while preserving every first attempt. Do not repeat an unchanged failed run automatically.

The supervisor carries out that next task while active; recording its name alone does not execute it. This is one step toward a system that can test and revise its representations. The larger research questions about prediction, organizational control and distributed exchange remain separate experiments.
