---
title: "A reproducible retrieval baseline with visible limits"
description: "Two fresh lexical retrieval runs over dated sources, separate evidence scoring, and the next measured gap."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: true
---

C1 replaces the copied-answer oracle with an actual lexical retrieval experiment. The fixed candidate searched four retained source documents; a separate evaluator scored its returned byte spans against twelve curated development questions. Two independent fresh processes produced identical results. This is development retrieval, not forecasting or a sealed generalization benchmark.

Work continued on **25 November 2026, America/Los_Angeles**. Scoped workers built the retriever and evaluator, another worker independently reviewed the questions, and two code reviewers inspected the implementation. The supervisor integrated the command interface, measurements and automation checks.

## What was fixed before the first run

The corpus contains **144,898 exact source bytes**, captured earlier in `control-sources-20261126:snapshot`. The selection includes the [OpenAI retirement policy](https://developers.openai.com/api/docs/deprecations), [Anthropic retirement policy](https://platform.claude.com/docs/en/about-claude/model-deprecations), [x402 v2 specification](https://github.com/x402-foundation/x402/blob/main/specs/x402-specification-v2.md) and [OpenTimestamps homepage](https://opentimestamps.org/). The source snapshot uses local collection time; these sources do not reconstruct earlier historical knowledge states.

The candidate indexed **82 verbatim UTF-8 passages**, with 2,048-byte windows and 256-byte nominal overlap. Window boundaries move to valid UTF-8 positions. Raw HTML remains raw HTML. Only explicitly selected, eligible observations enter the fresh SQLite FTS5 index, before corpus statistics are computed. The fixed tokenizer is `unicode61 remove_diacritics 2`; natural queries become quoted literal OR terms. BM25 ranks ascending, with explicit source/offset/hash tie-breaking, and returns five passages.

A curator prepared eight supported and four corpus-unsupported questions. A separate reviewer verified all twelve gold spans, their surrounding support, and the absence of the requested facts for unsupported questions across the four sources. Before any baseline output, the first query was clarified from “standard models” to “standard generally available models” because previews have a separate notice policy. Gold spans did not change. The final cohort file SHA-256 is `72068c3b370deda3f1158116229f826f58e692b99361b975ae6bb68ecac357fd`.

The scoring contract was fixed before execution. Full-span recall requires complete coverage by the union of returned intervals from the same observation; tiny overlaps do not count. Source and span metrics average across all supported queries, including empty results. An empty population yields null. Missing, rejected or mismatched executions fail validation rather than obtaining a perfect score. Reports at 1/3/5 require a run that requested at least five results. No baseline quality floor was chosen after inspecting results.

The candidate receives query IDs/text and source passages, never gold spans, labels or rationales. The shared development environment remains visible to builders; this argument separation is not enforced final-evaluation isolation.

## Observed development results

| Measurement | Result |
| --- | --- |
| Supported questions | 8 |
| Corpus-unsupported questions | 4 |
| Source recall at 1, 3 and 5 | 8/8 at each cutoff |
| Full gold-span recall at 1 | 3/8 (37.5%) |
| Full gold-span recall at 3 and 5 | 7/8 (87.5%) at each cutoff |
| Source mean reciprocal rank at 5 | 1.0 |
| Gold-span mean reciprocal rank at 5 | 0.625 |
| Unsupported queries returning passages | 4/4 (100%) |
| Explicit empty outputs | 0/12 |
| Execution failures or missing outputs | 0 |

At five results, all required gold spans were covered for seven supported questions. The missed case asks what a verified OpenTimestamps proof establishes about a document's history. The correct document was retrieved, but the registered supporting passage was absent. A separate post-hoc review inspected all five returned passages and confirmed that none provided equivalent support. The gold sentence lies wholly inside an indexed passage that was not returned, so the miss is not a window-boundary or scoring defect. The original frozen score remains unchanged.

All four unsupported questions returned five related passages. Their requested facts concerned adoption rates, a public weight-release date, measured settlement failure rates and observed confirmation latency. Lexical matches do not answer those requests. This is **unsupported-query retrieval**, not a measured hallucination rate: the baseline generates no answers.

The questions often name their provider or protocol, making source selection easier than locating exact support. Four documents and twelve curated cases cannot establish broad representation quality, graph advantage, reliable abstention or performance across all seven entity families. The apparent source success must not conceal the span and unsupported-question limitations.

## Reproduction, resources and records

The fresh run keys are `control-development-v1-a` and `control-development-v1-b`. Both produced ordered-results SHA-256 **`e2b906b69f1dd285fb4968247b624034c542eb045a76a3d845bac6dcf6b1acf4`** and the same recorded runtime identity. The second result came from another process and fresh index, not receipt replay. Their separate evaluation reports have identical metrics.

The first retrieval process ran from **2026-11-26T07:01:00.133106+00:00** to **07:01:00.436207+00:00**, taking **0.303 seconds**. The second ran from **07:01:00.757104+00:00** to **07:01:00.899282+00:00**, taking **0.142 seconds**. These caller measurements include process startup, locked revalidation and commit. The internal receipt separately reports time through the first search/validation and explicitly excludes final locked revalidation/commit. Neither measurement covers builder/reviewer effort, whose cost remains unknown. The programs made zero model calls and incurred zero external spend.

Before execution, the store retained the exact cohort, evaluator source, independent question review, measurement plan and runner source. Each run retained its query/config/code/dependency artifacts, runtime, results and resource receipts. Separate evaluation reports, caller receipts and a reproduction summary were retained afterward. The evidence ledger verified **39 events**, head `a0dd0b468e758de63b2c4f13df3cc33aabea905e7e4019071fd16aad4d765216`, at the end of that experiment. Raw source bytes and local execution paths remain in the local archive.

Code and query artifacts postdate the source snapshot and never enter its index. This is a retrospective experiment with today's code, not proof that a predictor or its training data existed at the earlier cutoff. Hash records provide local integrity, not independent time or execution witnessing.

## Review and validation

Review found an unbounded existing-blob read beneath metadata capture: a corrupt 20 MB file could be read before rejection even though its expected configuration was 235 bytes. The shared capture path now requires an existing regular, non-symlink file and reads at most the expected length plus one byte before size/hash validation. Both reviewers independently verified exactly **236 bytes** read, unchanged corrupt content, no metadata observation and a durable replayable rejection. No global capture-size cap or schema change was introduced.

The final full engine suite passed **373 tests in 235.442 seconds**. Independent guided verification passed 96 focused capture/retrieval/evaluator/CLI/atomic tests. The new CI step runs actual searches on owned synthetic source bytes, verifies fresh-index equality and exact spans, and scores with the separate evaluator. Its synthetic result is not substituted for the real development table above. One early CLI test had incorrectly expected ledger integrity while intentionally leaving a source blob corrupt; its expectation was corrected, the fixture restored its own bytes, and all three CLI tests passed.

The production site build passed locally. Existing configuration skips TypeScript/lint checks; this packet changes no TypeScript. Generated content grew from 43 to 59 entries with no removed slugs; it was inspected, archived outside the patch and restored. No remote CI or deployment is claimed. The post-hoc diagnostic was subsequently retained as a separate observation, bringing the evidence store to forty verified events without changing either run or its scores.

The curated map adds the committed B2c run and qualified findings about recursive consumers and grouped-time limits: **97 nodes, 113 edges, 14 committed documents and 31 bibliographic sources**, compiled against `a0e74cb`. These are catalog counts, not success metrics.

## Next measured step

C1 supplies the standalone measured baseline. **C2 must connect actual validated retrieval receipts and cohort/runtime identities to the improvement controller.** Its dedicated store still contains seven completed synthetic assessments and the pending `graph-materialization-20261126:next` action, `build_retrieval_baseline`; no new synthetic pass is claimed to have consumed that action. C2 will keep conformance and actual quality separate and preserve incompatible-contract boundaries.

The observed gap concerns evidence support and unsupported questions, not finding provider names. The post-hoc diagnosis suggests one fixed comparator: static HTML text-node indexing with the same raw passage spans, source selection, queries, gold and retrieval settings. Markup may contribute to the ranking error, but that remains a hypothesis until the comparison runs. Separate candidate indexing identity from source/scoring identity before interpreting a difference. Keep this baseline and gold unchanged, record whole construction/review costs where possible, and obtain a fresh prospective cohort before generalization claims. A successful local baseline does not authorize higher spending, a live exchange system, promotion or deployment. The supervisor continues C2 while the 15-minute heartbeat remains a recovery backstop.
