---
title: "Does removing HTML markup improve supporting-passage retrieval?"
description: "A fixed raw-text versus HTML-text comparison with unchanged questions, source windows and scoring."
date: 2026-11-25
draft: false
tts:
  enabled: false
feedback:
  enabled: true
---

The first retrieval baseline found the right document for all eight supported questions, but the required evidence appeared in the first result for only three. One question still lacked its supporting passage after five results. This experiment tests one possible explanation: HTML markup changes which passages lexical search ranks highly. The explanation is a hypothesis, identified after inspecting development errors.

The comparison changes only the text indexed for HTML sources. It keeps the four source documents, 82 raw source windows, twelve questions, gold byte spans, query compiler, tokenizer, ranking and five-result budget fixed. Three Markdown sources remain verbatim. The raw reference remains the operational baseline after this experiment; a favorable descriptive result alone does not authorize adoption or a broader advantage claim.

The machine-readable protocol at `engine/examples/retrieval/html-comparison-protocol.json` fixes input identities, order, limits and reporting before execution. A separately retained execution freeze binds the final reviewed code and runtime. The later declaration of actual terminal and projection hashes is an output binding, not a claim that those outputs were known beforehand. Completed results belong in the execution record.

## What remains fixed

| Item | Contract |
| --- | --- |
| Evidence | The same four observations eligible at the original snapshot cutoff. Later code and protocol captures are execution metadata and cannot enter retrieval. |
| Source windows | Exact UTF-8 slices, 2,048 bytes with 256-byte overlap; all 82 rows retained, including windows that become empty after extraction. |
| Questions | The original eight supported and four unsupported development questions; no edits after inspecting comparator output. |
| Search | The same literal query compiler, Unicode tokenizer, FTS5 BM25 ranking, deterministic tie order and top five results. |
| Scoring | Source recall and full raw-span coverage at 1, 3 and 5; source and span reciprocal rank through 5; unsupported-query retrieval; all cases and valid empty results counted. |
| Execution | Exactly four fresh processes in order: raw A, raw B, HTML A, HTML B. Each has a fresh index and distinct exclusive claim. |
| Interpretation | Builder-visible retrospective development. No generated answers, calibrated abstention, forecast, sealed holdout or representative entity-family coverage. |

The candidate receives only selected bytes, their media types, raw windows, questions and fixed search settings. It receives no gold labels. Gold remains visible to the developers, so this separation is an execution boundary rather than a claim of blinded development.

## Two fixed indexing methods

`raw-window-text-v1` indexes the exact raw window text. `static-html-text-nodes-v1` parses each complete selected HTML document before projecting text back into the same raw windows. It does not fetch resources, execute JavaScript or interpret CSS or visibility attributes. Ordinary `noscript`, `template` and navigation text remain eligible under this explicitly static policy.

The HTML method excludes tag syntax, attributes, comments, declarations, processing instructions and text inside `head`, `script` or `style`. It tracks only those excluded tags: a matching end tag closes its most recent matching opener and excluded descendants; unmatched ends do nothing; self-closing tags create no lasting state; an unclosed excluded region continues to end of input. This explicit rule is necessary because the standard parser does not perform matching-tag or browser-tree validation. [Python HTMLParser documentation](https://docs.python.org/3.14/library/html.parser.html)

Every accepted parser callback must match the original bytes at its reported line and character position. The implementation checks the UTF-8 translation, including repeated text and CRLF. It refuses unverifiable offsets instead of silently returning empty text or switching to another extractor.

Copy text and whitespace remain unchanged. Complete semicolon-terminated named references use the pinned HTML5 entity table; bounded numeric references decode once. Unknown, semicolonless and oversized references remain literal. A synthetic ASCII space separates retained text across removed bytes. It is not evidence, and does not appear at the beginning or end of a projected window. Entities crossing a raw-window boundary are excluded from that window; copied text is clipped only on valid UTF-8 boundaries.

Every projected row retains its raw span and adds a text hash plus ordered mappings. A mapping is an exact source copy, a source-bound decoded entity, or a synthetic separator with no source. Disjoint pieces never become a fabricated contiguous quote. Zero-output decoded references retain their source mapping. Maps and indexed text are retained in bounded chunks separately from ranked hits.

All raw windows keep their original row positions, even when extraction leaves no indexed text. Removing empty rows would change corpus statistics. BM25 uses document and corpus statistics, so cross-method BM25 magnitudes are not probabilities or comparable confidence scores. [SQLite FTS5 documentation](https://www.sqlite.org/fts5.html#the_bm25_function)

## Measurement, candidate and execution identities

The neutral contract validates source eligibility, raw windows, maps and receipts. The evaluator imports that contract, not the runner or indexing implementation. It continues to score the raw source intervals returned by search. Finding a gold raw interval does not establish that every gold byte survived text extraction; projected-text coverage would be a different metric requiring a new contract.

Three identities have different purposes:

1. The **measurement identity** binds source/snapshot lineage, raw windows, queries, gold, scoring definitions, common search constraints and the actual neutral/evaluator dependency closure. The shared entity decoder belongs here because it determines map validity.
2. The **candidate identity** binds the fixed recipe, indexing/search implementation, dependencies, parser and runtime. The constructed projection hash is identified separately from the algorithm. Per-run observation IDs are lineage, not algorithm changes.
3. The **execution identity** binds runner, claims, terminal records, retained inputs, budgets and the comparison protocol. Assessment code and its captured inputs remain separately identifiable.

Moving validation out of the old runner creates a new measurement implementation identity even where every numerical score agrees. The bridge records both identities; it never rewrites the original records or declares old and new measurement contracts identical. Historical schema-1 receipts remain schema 1. New executions use schema 2, and a reused key with a changed recipe is refused.

Byte-verified schema-2 maps must match the current pinned shared decoder source and entity table. Metadata-only historical inspection remains explicit; incompatible decoder semantics require a reviewed migration. Archived implementation bytes are never executed to validate a receipt.

## Gates and costs

The fixed controller validates receipt order, exact declared inputs, shared measurement and repeated outputs. It retains the protocol as opaque hash-bound bytes; it does not interpret that document or establish when it was chosen. The supervisor separately freezes static input identities before new searches, checks the historical raw bridge before allowing HTML, and records the launcher and caller identities. A standalone four-receipt adapter report does not by itself prove those additional procedural gates or an independent execution witness.

Before real execution, owned tests and independent review must cover the neutral boundary, original receipt compatibility, raw ranking equality, maps, parser edge cases, bounds, stale-code refusal, exclusive claims and locked final recomputation. The original two C1 runs are validated and rescored read-only under the new measurement implementation, preserving their original bytes and reports.

Raw A and B must reproduce each other, the original ordered-results hash and all original numerical evaluation fields under the recorded C1 runtime. A mismatch stops before either HTML run. It is retained as a migration diagnosis; the questions, gold and equality rule are not adjusted to make it pass.

Only a passing raw bridge permits HTML A and B. Their maps and ordered results must reproduce, every map must validate, non-HTML windows must remain exact raw text, and both arms must share the frozen new measurement identity. A valid differing pair is a reproduction failure. Invalid or incomplete receipts produce no quality summary. Neither case permits choosing a favorable repeat.

Bounds include 1 MB per source and 4 MB selected total, 64 sources, 4,096 windows, 64 queries, 256 excluded nesting levels, 65,536 mapping pieces, 8,192 indexed bytes per window, 8 MB indexed text, 8 MB mapping metadata and 12 MB combined projection. Projection chunks are at most 1 MB each, with at most sixteen chunks. The captured assessment bundle remains limited to 128 artifacts, 16 MB total, 256 prefix events and 4 MB prefix metadata. Exceeding a bound is a recorded refusal, not truncation.

Each run has the existing 30-second cooperative budget, including final locked validation, and a 60-second supervisor process timeout. These are local process controls, not OS memory isolation. The receipt's elapsed field preserves its original scope: it ends before final locked revalidation and commit. A separate caller record measures wall time through process completion. Report both, each run's retained/input/output bytes and map/window counts, and the sum of four caller durations. Separate phase timings, peak memory and builder/reviewer effort remain unmeasured; they are not inferred from a zero-spend field. The four fixed programs make no model calls or purchases.

## What happens next

The report preserves both repeats for both methods, per-question raw-span rank changes, all metric components, valid empties and costs. A paired delta is available only after shared measurement and within-arm reproduction pass. Gains, ties and regressions are all valid findings; no quality floor is selected from these twelve examples.

A valid completed comparison consumes the preparation step and selects `prepare_retrieval_coverage_evaluation`, regardless of the direction of the result. Higher-priority integrity or conformance failures still require repair, and a reproduction failure selects its own repair step. The next coverage work must freeze fresh questions, alternative supporting passages and matched supported/unsupported cases before comparator output is inspected. Repeated recipe tuning on this development set is outside this protocol.
