---
title: "Testing the two parts of a missed question"
description: "A fixed local diagnostic over retained evidence, with separate clause results and an explicit retrieval budget."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

The [support diagnosis](../planning/runs/2026-11-26-retrieval-diagnosis.md) located a specific omission: evidence needed to discover payment capabilities was indexed but absent from the five passages returned for a question that also asked about committing payment state. This protocol asks whether separating those clauses changes the evidence returned. The source documents, original questions, annotations and scores stay fixed.

## The fixed diagnostic

Use the original raw-text corpus and candidate. Run these two queries, in order, in each of two fresh local processes:

1. Which x402 facilitator endpoint lists its supported schemes and networks?
2. Which x402 facilitator endpoint durably commits payment state for a request?

Each clause can return five windows. The combined output can therefore contain ten window occurrences, compared with five for the original question. This is a development diagnostic with a larger selection budget. It cannot establish an equal-budget improvement or a general benefit from decomposing questions.

There is no third repeat, alternate wording, new source acquisition, model call or external program spend. If the first execution fails or cannot be verified, preserve its actual evidence and leave the second unstarted. A second failure is retained without a replacement attempt.

## What is measured

For each clause, report whether at least one complete, originally annotated support bundle is covered at the first one, three and five returned windows. Every span within a bundle is required; alternative bundles remain alternatives. Check exact source bytes and merge overlapping intervals only within the same source.

The combined measure, `joint_support_union_of_two_top5`, checks the original question's complete bundles against both clause outputs within one repeat. It has no shared rank. Never combine evidence across repeats to repair a miss.

Report window occurrences, distinct windows, summed window lengths and the union of covered source bytes. Preserve both repeated results. A disagreement makes the aggregate support summaries unavailable and selects reproducibility repair. Caller wall time and inner execution time have different scopes and must not be added together as separate costs. Builder and reviewer costs remain unmeasured.

## How the order is checked

The protocol names the accepted diagnosis and pending step. A separate review binds its exact bytes. An execution envelope binds the protocol, review, supervisor, both request files, candidate and validation code. The working evidence ledger captures that envelope before either retrieval starts. The second start must follow the first valid completion.

The assessment checks each execution against its declared request before comparing the pair. Two matching executions of the wrong query do not pass. It reads a captured evidence prefix and retained bytes; it does not launch retrieval, rebuild the index or rescore the original cohort. The original archive remains unchanged. Local ordering and hashes are not independent timestamps or proof of an externally witnessed execution.

The existing limits remain: 256 events and 4 MB of evidence metadata, 128 captured artifacts and 16 MB in total, with a 256 KiB report. Each retrieval has a 30-second cooperative budget and a 60-second caller timeout. The supervisor checks anticipated capacity before creating the working copy; the adapter checks actual sizes after execution.

## What follows

Every valid reproduced support outcome—recovery, continued omission or a tradeoff—ends this fixed diagnostic and selects `prepare_control_exchange_decision_pilot`. This is preparation for a separate offline decision experiment, not permission to execute payments or change control rights. A failed assessment selects diagnosis; valid repeat disagreement selects repair. Earlier integrity and conformance failures retain priority.

The next application should test one release-or-hold decision for a simulated agent-delivered artifact. Compare bounded views of the same dated events, including authority, verification and prior settlement. Keep rights actually in force, evidence available at decision time and later outcomes separate. Its protocol must define failure denominators, a lossless control over the same eligible information, and separation of candidate inputs from evaluation outcomes. Development retrieval results do not establish predictive or business advantage, recursive adaptation or market concentration.
