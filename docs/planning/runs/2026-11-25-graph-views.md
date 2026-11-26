---
title: "Graph partition and merge with explicit losses"
description: "Bounded graph views, a repaired resource limit, and fresh source snapshots for control and exchange research."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: true
draft: true
---

B2b follows the reviewed identity/projection operations with executable graph partition and merge. The supervisor assigned separate workers to the API, capability checks, and documentation/CI, followed by two independent reviews. Work continued during the same active session on **25 November 2026, America/Los_Angeles**.

## Operations and preserved information

`execute_graph_views` partitions one parent into nonempty, disjoint groups covering every entity, or merges compatible parents sharing an exact snapshot. Partition outputs are induced graphs; cross-partition edges become explicit removed records. Merge collisions require canonical equality of complete records, including provenance and attributes. Opposite directions and parallel typed edges remain distinct. Conflicting units, declared semantics, relation IDs or root metadata cause rejection.

The completion embeds named graph outputs, hashes, full parent mappings and identical-record deduplication ancestry. It does not redistribute quantities, split physical entities or establish semantic equivalence. The limits are 16 parents, 64 views, 1 MB per graph, 1,000 entities and 5,000 relations per graph, 2 MB combined input/output graph bytes, and 10 MB per completion. Outputs are still embedded; B2c must create usable representation/manifest records before this path feeds corpus comparisons.

## Review changes and measurement

Review found that a long view name or parent manifest ID could repeat throughout the receipt before the terminal-size check. A small valid input produced about 41 MB of measured allocations in the review reproduction; permitted graph sizes could amplify it further. View names now have a **128 UTF-8 byte** limit before computation; parent manifest IDs have a **512 UTF-8 byte** limit before request expansion or claim. View-name failures retain a start/rejection pair. Unaddressable parent identifiers refuse before writing.

`graph-view-probes-v1` now runs **45 actual API checks**. Disabling both identifier limits gives **43/45**, while ordinary partition and merge still pass. Removing completion validation gives **42/45**. The probe also detects dropped parallel edges, overwritten conflicts, fabricated outputs and missing losses/ancestry. These are synthetic operation-conformance measurements, not predictive accuracy.

The additional checks exposed outdated ten-second test waits. An instrumented assessment took 14.707 seconds under load; concurrent claim ownership remained correct. Full-assessment test waits now allow 40 seconds for the existing 30-second acceptance budget plus startup/cleanup. Production assessment and dispatcher limits remain 30 and 60 seconds respectively; intentional timeout/output-limit checks retain their original behavior.

## Verified handoff

The final full suite passed **236 tests in 134.184 seconds**. The production site build and both changed CI steps passed locally. Existing build configuration skips TypeScript/lint checks; this packet changes no TypeScript. Generated content was inspected (43 to 57 entries, no removed slugs), archived outside the patch, and restored. Both reviewers verified the resource fix; their original reproductions now peak around 1.5 MB and 0.2 MB.

A real worker consumed `graph-transforms-20261126:next` and recorded **`graph-views-20261126:next`**, action **`build_transform_materialization`**. All preceding controls remain required: representation oracle 30/30 across seven families, source spans 8/8, history 6/6, manifests 22/22, and identity/projection 26/26. Graph views passed 45/45 under `offline-contracts-graph-views-v5`.

Dispatch **`076cc552abca4cfc8305c6e4181e1b7b`** started at **2026-11-26T05:51:21.735246+00:00**, ended at **2026-11-26T05:51:25.665277+00:00**, returned 0 and took 3.930 seconds. It recorded zero program model calls and external spend. This covers assessment, not total builder/reviewer effort. Changed policy and graph-view contracts correctly yield `incomparable_contract_change`; no improvement delta is claimed. The reviewed worktree was assessed before local integration, with no remote deployment implied.

The curated map now includes the committed B2a run and two qualified implementation findings: **89 nodes, 105 edges and 12 embedded committed documents**, compiled against the B2b base. These catalog counts are descriptive, not scientific success measures.

## Fresh evidence for control and exchange

Four public sources were captured at **2026-11-26 05:34:11 UTC**, preserving exact bytes and hashes in a separate local research store. Four current reported claims cite exact byte spans. Independent semantic review prompted two clarifications, saved as superseding assertions; earlier knowledge-time views still return the original claims. The store retains six assertion events and thirteen events in total.

- Provider retirement policies offer an observable control relationship: access can change on a provider's schedule. The [OpenAI policy](https://developers.openai.com/api/docs/deprecations) distinguishes general, specialized/image and preview categories; treating all models as having the same notice period would lose that distinction.
- The [Anthropic policy](https://platform.claude.com/docs/en/about-claude/model-deprecations) identifies loss of research access as a retirement consequence while also describing preservation efforts. This supports studying reproducibility and migration, without establishing permanent loss or inevitable market dominance.
- The [x402 v2 specification](https://github.com/x402-foundation/x402/blob/main/specs/x402-specification-v2.md) places client-side budget management outside its core scope. A business-system adapter must account for budgets separately; the protocol does not forbid implementations from doing so.
- [OpenTimestamps](https://opentimestamps.org/) concerns verifiable evidence of prior data existence. A valid proof is distinct from our local collection timestamp and from proof that a source's statements are true. No external timestamp proof was created in this capture.

This is fresh development evidence. Historical dates within these sources remain source claims: today's capture cannot reconstruct what a forecaster actually knew on those dates. Collection made no program model calls or payments; assistant curation has no separately measured cost. Source snapshots and private ledger contents are not published by this run note.

## Next measured step

B2c will materialize completed outputs into B1 representations/manifests with exact output hashes, full ancestry, atomic writes and replay checks. Its `output_manifest_materialization` metric remains unmeasured. After that bridge, the next comparison should use a frozen local corpus and a genuine retrieval baseline rather than the reference oracle that copies expected answers. The 15-minute heartbeat remains a recovery backstop; an active supervisor dispatches the next ready step without waiting for that heartbeat.
