---
title: "Executed graph transformations and retained losses"
description: "Fixed identity/projection execution, malformed-input and completion-boundary review fixes, and the next partition/merge packet."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: true
---

B2a followed B1 during the same active supervisor session on **25 November 2026, America/Los_Angeles**. Scoped builders implemented fixed graph operations, an independent capability probe, docs/CI and an evidence-backed catalog update. Two reviewers verified the final changes.

## Executed scope

`execute_graph_transform` computes identity or induced-subgraph projection for the declared directed-graph schema. It accepts no caller-supplied output. The recipe, configuration, fixed implementation source and internal dependency sources must already exist in the parent snapshot. Retained code bytes are checked against the loaded implementation, never evaluated as arbitrary programs.

A completion contains the generated graph, output hash, complete removed entity/relation records, removed evidence references and mappings from parent records. Retained attributes, cycles, self-loops and directed/parallel typed relations are preserved where their endpoints remain. Unit labels and opaque metadata are copied without inferring new meaning. Computation runs during preparation and again under the completion write lock.

Claims are exclusive. Addressable invalid inputs produce a start and rejection; unaddressable requests refuse before claiming; interrupted starts require diagnosis. Exact terminal replay returns historical metadata even after blob loss. Output remains embedded in the completion event: no new representation or forecast manifest is materialized.

## Measured handoff

| Contract | Result |
| --- | --- |
| Representation oracle control | 30/30 across seven families |
| Source spans / assertion history | 8/8 and 6/6 |
| Manifest bindings | 22/22 |
| Fixed graph operations | 26/26 |

The new contract is **`graph-transformation-probes-v2`**, under `offline-contracts-graph-transforms-v4`. These are deterministic synthetic API checks; the representation oracle still copies expected answers. Split/merge preservation remains unmeasured, and no predictive or semantic-equivalence claim follows.

A real worker consumed `representation-manifests-20261126:next` and recorded **`graph-transforms-20261126:next`**, action **`build_split_merge_transformations`**. Changed policy/implementation/probe contracts correctly produce `incomparable_contract_change`, without a gain claim.

Dispatch `b163c180e234451a9999eecfe6a49ccc` started at **2026-11-26T05:20:23.117202+00:00**, ended at **2026-11-26T05:20:25.178508+00:00**, returned 0, and took 2.061 seconds. The assessment recorded 1.899 seconds, zero program model calls and zero external spend. These resource values cover assessment, not builder/review costs. Exact inputs and receipts are retained locally. The reviewed worktree was assessed before local integration; no remote deployment or independent witness is implied.

## Verification and review findings

**192 engine tests passed.** The production site build and both changed CI steps passed locally. Existing build configuration skips TypeScript/lint validation; this packet changed no TypeScript. The generated content index was inspected and kept out of the source patch.

One review finding concerned failure records: an escaped lone surrogate in duplicate JSON keys could make a rejection diagnostic impossible to encode. Diagnostics now escape unencodable characters before truncation, leaving original bytes unchanged. Recipe and configuration cases retain a valid start/rejection pair and exact replay after blob loss.

The other finding was a measurement gap: removing completion validation still passed the original 22 checks. Version two mutates configuration and parent evidence immediately before completion. With the real validator, all 26 checks pass; selectively removing it now gives **24/26**, while identity execution still passes. Both reviewers verified these fixes.

## Knowledge and continuation

The curated map adds the two committed A/B1 run notes and two qualified implementation findings linked to them. Compilation against the committed base produced **86 nodes, 103 edges and 11 embedded documents**. External source rows and historical run notes were unchanged; these counts describe a catalog, not an increase in scientific truth.

B2b will execute graph partition/merge with explicit cross-partition losses, strict collision rules and complete ancestry. It will preserve existing entities rather than invent redistributed quantities or silently reconcile units. Semantic entity fission, broader encodings, output materialization and prospective prediction remain separate work. The supervisor continues into B2b; the 15-minute heartbeat remains a recovery backstop.
