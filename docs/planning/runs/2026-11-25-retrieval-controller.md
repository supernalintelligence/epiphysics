---
title: "Connecting real retrieval evidence to the next build"
description: "A bounded bridge from retained retrieval executions to measured work selection."
date: 2026-11-25
draft: false
tts:
  enabled: false
feedback:
  enabled: true
---

C2 connects the [C1 baseline](2026-11-25-retrieval-baseline.md) to the measured work queue. The reviewed controller validated the two retained executions, recomputed their original scores and selected the next task from the observed support gap. All 417 tests passed. C1 remains preserved at `6773193`; no new search or source rewrite occurred during this assessment.

Work continues on 25 November 2026, America/Los_Angeles. Three scoped builders implemented the read-only ledger, bounded evidence adapter and controller integration. Two separate reviewers inspected the changes and independently checked repairs. The supervisor integrated the evidence, documentation and measured successor. The 15-minute heartbeat is an interruption recovery mechanism; ready work continues immediately during the active session.

## What this step must establish

The controller must validate the two retained C1 executions and recompute their scores from captured evidence. It must not trust a supplied summary, run a new search under the old receipt, mutate the original evidence store or mistake another read of one receipt for a second execution. Both run identities, corpus, queries, gold, configuration, implementation content and runtime must match their declared contract.

The evidence adapter captures a bounded, coherent event prefix and required blobs. The improvement store retains the captured evidence as observations, separate from its own workflow events. Candidate, measurement and assessment identities remain explicit. Current retrieval code couples search with validation; a later representation comparison must resolve that boundary before claiming a comparable improvement.

All existing integrity and representation repair priorities stay ahead of retrieval work. A valid, reproduced baseline with support gaps selects a bounded representation-comparison packet. An invalid study selects diagnosis; a valid but differing pair selects reproducibility repair. No missing input receives a fabricated success score. The current 3/8 support at rank one and 7/8 at rank five are measured baselines, not thresholds selected after seeing results.

## Current evidence and limits

The four-source development corpus has twelve builder-visible queries, including four unsupported questions. Both actual searches produced the same ordered results. All four unsupported queries returned related passages; this measures lexical matching without requested support, not hallucinated answers. No model generated answers, and no new population or sealed-holdout result is claimed.

Before this step, the dedicated improvement store contained seven completed assessments and the pending `graph-materialization-20261126:next` action. C1's separate experiment did not consume that action. The reviewed C2 assessment has now consumed it using validated actual evidence.

The curated research map now includes the committed C1 record and qualified reproduction/support-gap claims. Catalog size is bookkeeping, not a quality metric. Third-party source bytes, local paths and process receipts remain local; public documentation contains owned questions, citations, hashes and summaries.

## Validation and successor

The read-only ledger passed 109 focused store/capture/atomic/retrieval/evaluator/CLI tests. Its nine new cases cover live WAL visibility, coherent read transactions, missing-store refusal without creation, mutation refusal before blob access, direct SQL write rejection and evaluator compatibility.

The adapter passed sixteen focused tests. Root inspection tightened three preflight limits: count actual chain-hash field lengths before deserializing records, reject selected source totals above 4 MB before copying blobs, and bound changed adapter-source reads to the expected length plus one. Valid-but-different result pairs explicitly produce reproduction 0; malformed evidence produces a failure. Retained captures can be evaluated after the original paths disappear.

A read-only preflight on the actual C1 archive reproduced both original reports in 0.209 seconds. Its 23 artifacts totalled 558,887 bytes. Every original database/blob byte and modification time remained unchanged. Current validation uses store hash `fda268dfa48beb28ee34a3bef714979f85e2e46db28bd7dc4cb1bc0395d6b0d1`; historical executions retain their original store hash. This preflight did not consume the persistent queue.

The real CI program also passed: it generated two searches on owned synthetic evidence, invoked the controller in a separate process and verified the resulting coverage-evaluation task. The site build passed before and after the completed run record was included. Its final generated index grew from 43 to 60 entries with no removed slugs; the generated file was inspected, archived and restored. No deployment or visual verification is claimed.

Independent review found three failure-path defects: corrupt SQLite input could escape before a diagnosis was recorded, a changed evaluator source file could be read without an expected-length bound, and rejected symlink-loop paths could fail while constructing their own diagnosis. Both reviewers independently verified the repairs. The original 32 MB changed-evaluator reproduction now rejects without opening the file; measured peak allocation in that reproduction was 1,856,321 bytes. Self/ancestor link loops produce one started event, one failed event and no completion, including through the real dispatcher. Corrupt database bytes remain unchanged. Expected-length source checks also cover every controller-pinned module. Prefix reads refuse nonregular files so a rejected FIFO cannot block the dispatcher.

The initial full suite passed 411 tests in 266.276 seconds. The final full suite passed **417 tests in 342.801 seconds**, including six additional regression controls. Final changed-CI handoff checks passed. The supervised persistent assessment completed successfully as recorded below. The selected successor is a fixed HTML text-node comparator with mappings to original source bytes, after separating indexing identity from the measurement contract. This hypothesis arose from development error inspection; a later comparison on these questions remains development evidence. A fresh cohort is required before generalization claims.

No deployment or expansion of workload, action scope or spending is part of this step. Assessment process time excludes builder and reviewer effort, whose cost remains unknown.


## Actual persistent handoff

Run `retrieval-assessment-20261126` completed through the fixed dispatcher, receipt `2f8700b4c7af42049002e527b640bd43`. The worker ran from **2026-11-26T07:52:29.101018+00:00** to **07:52:41.806509+00:00**, taking **12.705 seconds**; the outer caller measured **12.906 seconds**. Exit code was zero, output was delivered, and no recovery was needed. The 30-second assessment and 60-second dispatcher limits were unchanged.

Both historical executions validated and reproduced the original evaluation: source recall@1 **8/8**, full gold-span recall@1 **3/8**, @3/@5 **7/8**, gold-span MRR@5 **0.625**, and unsupported-query retrieval **4/4**. All twelve queries remain counted. This is rescoring preserved executions, not a third retrieval run. Original database/blob bytes and modification times stayed unchanged.

The improvement ledger now verifies **129 events and eight completed assessments**, with no unfinished claims. Its head is `db227fa3b727a3c8d186907d539871079648fd32e6783983b785398954b0ae4b`. Completion and successor are one durable event. The new step is `retrieval-assessment-20261126:next`, action **`prepare_retrieval_representation_comparison`**, based on observed full-span recall@5 **0.875**. Its target remains null. Five rank-one support gaps are retained by query ID, alongside all four unsupported matches.

Actual measurement identity is `8d6ee041fbc84cd04ea3c3622546447e75d3dd1d08f8f73b0c80f8559741f083`; controller assessment identity is `a2a63c00efd6a02e5abecc6f3b00c93b7672a048d3e9aad485622d5856c8d2f5`. The current evaluator source is `fc521539c94c6e4347e00d1f55ab9960236c9c65e261bb211da952ac15cb79fc`; its bounded source-check repair changes validation identity while preserving the historical candidate artifacts. The prior retrieval outcome is **unmeasured**, because the preceding synthetic assessment had no actual retrieval measurement contract. No before/after improvement or target success is fabricated.

The supervisor continues the selected comparison immediately after local integration. Its preparation specifies a fresh raw-reference reproduction bridge before a single fixed HTML-text arm, unchanged raw citation windows and scoring, and complete byte mappings. Once a valid comparison is recorded, the next task must obtain new coverage/answerability evidence instead of repeatedly tuning against these same visible questions. A gain, tie or regression is a legitimate experimental result. Program model calls and external spending remain zero; builder/reviewer effort is outside those receipts.
