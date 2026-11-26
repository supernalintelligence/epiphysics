---
title: "Atomic output records and a verified recursive path"
description: "Graph outputs become usable representations, with corrected time boundaries, independent review and a measured retrieval handoff."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: true
---

B2c completes the consumer bridge for the fixed graph operations. Separate builders implemented transaction ownership, materialization, and capability checks; two independent reviewers inspected the result. Work continued on **25 November 2026, America/Los_Angeles**. The engine performs local, fixed operations; it does not learn a representation or establish predictive advantage.

## What the bridge does

`materialize_graph_outputs` creates every output representation, B1 manifest and full ancestry receipt in one owned SQLite transaction. A failure removes the entire provisional output set before recording rejection. Another reader sees either the complete bundle or none of it. Exact completed/rejected retries preserve their original receipts. Interrupted starts require diagnosis.

The new records preserve model hashes, evidence, semantics, recipe identity, parent multiplicity, and loss/mapping links. Merge ancestry is explicit in the bundle receipt. Derived manifests work in existing forecast consumers and can feed another fixed transformation and materialization; a reviewer independently exercised that recursive path. Supplied-probability forecasting remains separate from inference, and no mathematical or semantic equivalence is inferred from a successful round trip.

New materialization requires the exact current execution implementation and dependencies, then recomputes the fixed operation and compares its outputs, losses and mappings. A changed dependency requires a fresh eligible execution, not a backdated recipe. Historical materialized bundles remain inspectable without re-executing old code. Metadata-only replay does not establish present blob availability.

Resource bounds include 1 MB per graph, 2 MB combined graph outputs, 128-byte view names, 512-byte involved IDs, 16,384-byte parent method descriptors, a conservative 8 MB aggregate output-record estimate before writes, and 10 MB input/terminal records. Repeated descriptors and evidence references count toward the aggregate bound.

## Defects found and fixed

- An append validator could mutate a body after its stored JSON was captured. Appends now reject that mutation and hash the exact stored JSON; a caught error poisons its group.
- A snapshot taken during a grouped write could have a cutoff later than its own timestamp. Its cutoff now uses the group's fixed logical time.
- The same logical time could backdate fresh evidence or admit a late forecast. Groups now reject new observations, questions and forecasts, including generic appends. Capture refuses before writing blobs; forecasts run after commit under normal live deadline checks.
- Malformed completion and parent containers could escape validation and leave an unfinished claim. Explicit container checks produce durable rejection and exact replay.
- A forged-output probe originally rejected inconsistent IDs before reaching recomputation. It now supplies coherent start/terminal IDs and an updated output hash. Removing only the recomputation equality guard makes the probe fail while ordinary materialization still succeeds.
- A final review found the same recovery defect in malformed retained observation containers. Narrow preflight checks now cover recipes, code/configuration/dependencies, parent evidence/artifacts and cost receipts. Declared receipt IDs must match their references. No broad exception swallowing was added.

The capability contract is **`materialization-probes-v1`: 30 checks**. It includes actual four-operation consumers, ancestry, replay, concurrent claims, rollback, reader isolation, source mutation, resource bounds, malformed inputs and grouped-time behavior. Mutation controls target the relevant guard while retaining ordinary positive behavior. These checks establish synthetic conformance, not population-level quality or a universal representation score.

## Verification and successor

The final engine suite passed **308 tests in 244.938 seconds**. This follows a 304-test pass before the final retained-observation fix. The materializer's 28 focused tests and the final safety review's 15 targeted tests passed. Both independent reviewers report no actionable findings. Both changed CI steps executed locally, including a real assessment child. The CI job budget is ten minutes; production assessment acceptance and dispatcher limits remain 30 and 60 seconds respectively.

The persistent worker consumed `graph-views-20261126:next` and recorded **`graph-materialization-20261126:next`**, action **`build_retrieval_baseline`**. Earlier gates remained passing: representation oracle 30/30 across seven families, source spans 8/8, history 6/6, manifests 22/22, identity/projection 26/26 and partition/merge 45/45. Materialization passed 30/30 under `offline-contracts-materialization-v6`.

Dispatch **`1bf743c085854bdc90c0ee22ff84ac5f`** ran from **2026-11-26T06:33:37.631196+00:00** to **2026-11-26T06:33:53.683946+00:00**, returned 0 and took **16.053 seconds**. It recorded zero program model calls and external spend. This excludes builder, reviewer and supervisor effort. Changes to policy, store and materialization contracts correctly produced `incomparable_contract_change`; no improvement delta was awarded. There are fourteen comparison-contract hashes.

The curated catalog compiled against base `e1781d5` with **94 nodes, 109 edges, 13 committed documents and 31 bibliographic sources**. It adds the B2b execution record, qualified implementation/source-capture findings and the maintained SQLite FTS5 reference. Counts describe the map, not research success.

The production site build passed locally. Its existing configuration skips TypeScript/lint checks; this packet changes no TypeScript. The generated content index grew from 43 to 58 entries with no removed slugs; it was inspected, archived outside the patch and restored. No remote CI, deployment, external timestamp witness or real-world predictive improvement is claimed. The persistent improvement store verifies 84 events and seven completed assessments, with no unfinished claim.

## Continuation and coordination

SCI's existing Claude session received a native-session delivery and replied at **2026-11-26T06:28:21.384Z**. File ownership is confirmed and SCI reports no code dependency on B2c/C. Its canonical mathematics note remains under its ownership. Queue acceptance alone was not used as evidence of receipt. The existing audit/promotion restrictions and unrelated shared-checkout files remain intact.

The next work is a real retrieval baseline over the four retained sources described in the [B2b run](2026-11-25-graph-views.md). A curator has prepared eight answerable and four corpus-unsupported development questions with exact evidence spans. SQLite FTS5/BM25 will receive only eligible source passages and queries; scoring will separately use the gold spans. The corpus must be filtered before indexing so future evidence cannot change ranking statistics. The current bridge does not measure `retrieval_baseline_reproducibility`.

This is builder-visible development work, not a sealed final evaluation. Current code run over an older source snapshot is retrospective retrieval, not a predictor proven to have existed at that cutoff. Unsupported-query retrieval is separate from hallucinated answers because this baseline returns passages. Raw third-party source bytes remain local. The supervisor continues the next eligible packet immediately; its 15-minute heartbeat is a recovery backstop.
