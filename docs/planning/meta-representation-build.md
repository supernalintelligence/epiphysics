---
title: "Building a system that can revise its representations"
description: "Components, ownership, dependencies, and acceptance gates for the next Epiphysics research layer."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

This plan extends the [observatory implementation plan](2026-11-24-recursive-observatory.md). It translates the [research assessment](../research/meta-representational-systems.md) into small components with independently checkable outputs. Phase estimates below are planning estimates, not scheduled delivery promises; one focused implementation cycle includes review and tests.

## Current delivery and boundaries

The existing engine implements local capture, snapshots, representation records, prospective forecasts, resolution, and scoring. This investigation adds a curated source/claim/representation catalog and an offline graph compiler. The compiler validates references and selected field/type rules, embeds explicitly selected **committed** repository documents, and emits a reproducible graph payload. It does not infer truth, browse, extract entities, call models, revise an ontology, or make forecasts.

The [stepwise improvement controller](stepwise-improvement-loop.md) provides a dedicated development queue, seven-family/thirty-check representation evaluator, hashed inputs, atomic assessment-completion/successor transitions and fixed subprocess assessment. Reviewed A/B1/B2a slices retain fourteen assertion, twenty-two manifest and twenty-six identity/projection checks. B2b now adds executed graph partition/merge, strict conflicts, losses and ancestry with forty-five actual-API probes; both reviewers verified its identifier-bound fix and the real assessment selected B2c. These synthetic contracts establish neither semantic truth nor predictive advantage. Selection remains heuristic and whole-step builder/reviewer cost is not measured. B2c adds atomic output representations/manifests and thirty consumer checks. Learned selection, protected final cohorts and live scale promotion remain future work. See the [metric contracts](../experiments/representation-metrics.md).

External source rows contain bibliographic metadata and research notes. They are **not archived article bytes** and must not be admitted as historical evidence snapshots. A compiled graph records its generation time; its Git commit and content hashes identify local inputs, not independently verified times of existence. The full evidence layer remains the existing ledger.

```mermaid
flowchart LR
  A[Source bytes and collection receipts] --> B[Immutable evidence snapshots]
  B --> C[Attributed claims and conflicts]
  C --> D[Text, graph, program and latent views]
  D --> E[Versioned candidates and transformations]
  E --> F[Development evaluation]
  F --> G[Freeze candidate]
  G --> H[New prospective cohort]
  H --> I[Recorded comparison and review]
  I --> C
  I --> J[Public reproducible artifacts]
```

The return arrow proposes a new version. It does not edit earlier evidence, change outcomes, or grant the proposer control over its final evaluator.

## Component contracts

| Component | Minimum contract | Implementation boundary |
| --- | --- | --- |
| Evidence bundle | Observation IDs, bytes/hashes, collection time, source time claims, source spans, coverage and failures | Existing capture plus verified byte-span resolution; no graph database required. |
| Assertion store | Stable assertion ID; subject/predicate and typed entity or scalar/unit object; observer; valid interval; evidence spans; basis; contradiction and correction links | Immutable `assertion` events and knowledge/world-time projection implemented; corrections use `supersedes`, not a separate event kind. Claims remain separate from edges drawn on screen. |
| Representation registry | Schema/version, encoding, snapshot, representation/model hashes, units, observer/task/horizon, retained artifact/evidence references and construction-cost claim | B1 stores source-bound metadata and stable method identity distinct from snapshot instances. Multiple candidates can describe the same snapshot; semantic identity equivalence remains a claim. |
| Transformation registry | Parent instances, stable recipe and eligible code/configuration; generated output hashes; computed losses; source-to-output and deduplication ancestry | B2a/B2b execute fixed identity/projection and graph partition/merge with embedded outputs. B2c materializes checked representations/manifests atomically; semantic aggregation and broader encodings remain separate work. |
| Run manifest | Candidate ID binds encoder, retrieval, memory, predictor, versions, environment, seeds, allowed inputs and resource ceiling | B1 records declared artifact/input bindings and supplied forecast provenance. Verified execution, hidden-context isolation and enforced cost ceilings remain separate runner work. |
| Evaluator | Frozen task/cohort; scoring; failure treatment; resolution policy; family labels; cost metrics; permitted development feedback | Read-only to candidate runner. Final cohort access logged and irreversible. |
| Revision controller | Allowed changes, proposal budget, development feedback, rejected candidates, stopping rule | Bounded search; no self-issued promotion or evaluator rewrites. |
| Query and presentation adapters | Snapshot, observer, view version, source links, disagreement and missingness | Reuse story graph views after endpoint/identity fixes; export standards at boundaries. |
| Witness adapter | Submitted digest, pending/verified/failed receipt, verification method and retained bundle | Independent existence assurance, not a truth flag. |
| Exchange simulator | Offers, commitments, delivery, independent quality checks, settlement, disputes and rights | Simulated balances first. Real payment and identity protocols remain optional adapters. |

Do not pack all contracts into one unvalidated JSON object. Add one validated event type at a time with fixtures for its invariants. The initial catalog is a research planning format, not a second implementation of the complete production schema.

## Delivery sequence

| Phase and planning effort | Responsible component / caller | Concrete output and acceptance gate |
| --- | --- | --- |
| **0. Research map — implemented** | Research investigator; offline catalog compiler | Dated primary-source catalog, attributed claims and challenges, candidate/experiment map; deterministic payload; duplicate/dangling/type checks; committed-source isolation; no paid calls. |
| **1. Claims and time — implemented and reviewed** | Engine builder and independent reviewer | Byte-backed assertion events, corrections and contradictions; world/knowledge-time queries; fourteen capability probes. Preserve prior views, source hashes, observer lineage and rejected-write integrity. |
| **2. Representations and transformations — reviewed** | Engine maintainer plus independent reviewer | B1 metadata, B2a identity/projection, B2b graph partition/merge and forty-five view probes. Rejected runs retain records and leave inputs intact. B2c output materialization adds thirty consumer checks; independent review, 308 tests and a real assessment passed. |
| **3. Retrieval comparison — 2–4 cycles plus bounded model runs** | Retrieval adapter runner; evaluator owns tasks | Frozen local corpus and questions; lexical baseline first, then hybrid and graph challengers. Report citation precision, recall, abstention, cost and stale-result rate by task. Add tools only after a measured baseline. |
| **4. Prospective representation experiment — 2–3 setup cycles, then outcomes** | Candidate runner; independently controlled evaluator | Same future questions, snapshot and predictor; structure and budget controls; fresh final cohort. Record failures and all attempts. No advantage claim from pilot selection. |
| **5. Bounded revision — 2–4 cycles after phase 4 machinery** | Revision controller | Static, fixed-update and reflective-search arms; limited revisions; frozen evaluation; costs and churn. Stop on budget exhaustion, invalid contracts or contaminated evaluation. |
| **6. Control and exchange — separate domain pilots** | Domain adapter and simulator maintainer | Measurable access/control relationships, competing mechanisms and intervention policies; simulated quality/price/latency outcomes. No live settlement required. |

Phases 1 and witness design can proceed independently. Phases 4–5 require enforceable runner/evaluator separation, not just different prompts. Phase 6 can begin with deterministic scripted agents while learned candidate evaluation is still being built. Scaling follows measurement, not a fixed calendar date.

## First three work packets

**Packet A: source-backed assertions — implemented and independently reviewed.** `record_assertion` validates exact byte spans against captured blobs and preserves typed values/units, observer/method identity, epistemic basis and optional world-valid intervals. Corrections are new `assertion` events naming `supersedes`; contradiction links retain incompatible reports. `assertions_as_of` projects what was known at a recorded time without erasing earlier views. Explicit logical negation, retraction semantics, automatic extraction and semantic truth adjudication are not implemented by this slice.

Contract `source-span-probes-v1` measures `source_span_resolution` as passed checks / 8 and `assertion_history_preservation` as passed checks / 6. All fourteen actual-API probes pass in the current synthetic validation. The A slice used policy `offline-contracts-source-spans-v2`, with zero external spend and disabled scale changes. Those capability gates remain required before later work advances; failures select assertion repair. They replaced the earlier unconditional Packet A fallback. Two independent reviewers verified the fixes, and a real assessment worker recorded the Packet B1 successor. See [the execution record](runs/2026-11-25-source-assertions.md). Local integration and successful conformance checks do not imply deployment or scientific advantage.

**Packet B1: source-bound manifest metadata — implemented and independently reviewed.** `register_manifest` binds a representation instance to its snapshot, retained construction/configuration/ontology/predictor artifacts, task/horizon, units, evidence and declared construction cost. `method_identity` uses declared method semantics and artifact content hashes, excluding snapshot-instance IDs, evidence payload and actual cost. `forecast_manifest` binds a supplied probability to that manifest and the existing forecast safeguards; it does not execute construction or inference. Contract `representation-manifest-probes-v2` measures passed API checks / 22; all twenty-two passed in the recorded assessment. Retained bytes and reported/unknown cost metadata are not proof that a program ran or an expense occurred. See [the execution record](runs/2026-11-25-representation-manifests.md) for the reviewed fixes and real B2 handoff.

The B1 slice used policy `offline-contracts-manifests-v3` with zero external spend and disabled scale changes. Its thirty representation checks, eight source-span checks, six history checks and twenty-two manifest checks remain gates for later work. The recorded B1 worker selected B2a; it did not implement transformations by queuing them.

**Packet B2a: executed graph identity and projection — implemented and independently reviewed.** `execute_graph_transform` runs fixed operations against a validated `directed-graph` / `epiphysics.graph.v1` parent, accepts no caller-supplied output and executes no arbitrary retained code. Recipe/configuration/implementation/dependency artifacts must already be eligible in the parent snapshot. The completion embeds generated output, hash, computed removed records/evidence and all-parent mappings; inputs remain unchanged and addressable invalid runs retain rejection records. Stable recipe identity is separate from the parent instance. B2a itself embeds outputs; B2c supplies the separate representation/manifest consumer.

Contract `graph-transformation-probes-v2` measures `transformation_preservation` as passed API checks / 26, limited to these operations. The B2a slice used `offline-contracts-graph-transforms-v4` with offline scope and zero external spending. Its gates remain required; failures select `repair_graph_transformations`. See [the execution record](runs/2026-11-25-graph-transforms.md) for reviewed fixes and the real B2b handoff. B2a alone does not validate graph merge or semantic/causal equivalence.

**Packet B2b: graph partition/merge — implemented and independently reviewed.** `execute_graph_views` partitions one graph into named exhaustive disjoint induced views or merges 2–16 compatible parents sharing the exact snapshot and declared semantics. It computes cross-partition losses, strict record conflicts, full ancestry and identical-record deduplication. Quantities, identities, attributes, evidence and units are not silently reconciled. Recipe/configuration/code dependencies must be snapshot-eligible; output remains embedded and inputs unchanged. View names are capped at 128 UTF-8 bytes before output expansion, with recorded rejection above the bound. Parent manifest IDs are capped at 512 UTF-8 bytes before lookup/claim, with no new events on refusal. This is graph-record manipulation, not physical entity fission or semantic equivalence.

Contract `graph-view-probes-v1` measures `split_merge_preservation` as passed API checks / 45, limited to these operations. All forty-five checks passed in the real assessment after both reviewers verified the resource fix; see [the execution record](runs/2026-11-25-graph-views.md). Policy `offline-contracts-graph-views-v5` preserves zero external spending and disabled scale changes. All prior gates plus B2b must pass before `build_transform_materialization` is selected; failures select `repair_graph_views`.

**Packet B2c: output materialization — implemented and independently reviewed.** `materialize_graph_outputs` converts complete B2a/B2b outputs into actual representations, B1 manifests and a full lineage receipt in one owned transaction. Failure rolls back every output; exact retries preserve historical receipts. New materialization requires the current execution contract, eligible source artifacts and verified output/parent/evidence bindings. Its actual consumer probes include a supplied-probability forecast through the existing manifest adapter; the bridge itself generates no forecasts. Both reviewers cleared the fixes, 308 tests passed, and the real worker selected Packet C. See [the execution record](runs/2026-11-25-graph-materialization.md). Metadata-only historical lookup does not re-execute old recipes or certify current blob availability. No stage here establishes arbitrary encodings or semantic/causal equivalence.

**Packet C: a small comparison corpus.** Freeze a reviewed local corpus from committed repository documents and permitted external snapshots. Publish reusable owned fixtures, hashes and summaries; keep raw third-party snapshots in the local evidence store unless redistribution is separately permitted. Prepare questions for exact facts, relationships, global synthesis, temporal eligibility, contradiction and false premises. A curator writes evidence-based answers; a separate evaluator locks the final portion. Start with an offline lexical baseline using the existing [SQLite FTS5/BM25 implementation](https://www.sqlite.org/fts5.html), deterministic tie-breaking, recorded runtime/tokenizer settings and explicit source-byte spans. Index only the eligible corpus before ranking; later evidence must not influence document statistics. Acceptance: reproducible baseline, explicit unanswered cases, and no future passages entering an earlier snapshot. The four-source development capture in the [B2b run](runs/2026-11-25-graph-views.md) supplies initial real material, not a sealed final benchmark.

**C1: bounded lexical baseline — measured and independently reviewed.** Separate builders implemented the fixed retriever and evaluator. Two fresh processes over four sources and twelve reviewed queries reproduced exactly. Source recall@1 was 8/8, gold-span recall@5 was 7/8, and all four unsupported queries returned passages. The final 373 tests passed; see [the baseline record](runs/2026-11-25-retrieval-baseline.md). Do not tune a quality floor or query wording after seeing the first baseline. A generated answer, model call, general vector database and B1 binary forecast task are unnecessary for this first measurement.

**C2: evidence-driven controller handoff.** A fixed read-only adapter captures a bounded coherent bundle, validates the declared pair of historical retrieval executions and recomputes their scores. The dedicated improvement store retains the captured inputs and separate actual-quality reports. Existing repair priorities remain ahead of retrieval; malformed evidence queues diagnosis, a valid differing pair queues reproducibility repair, and a reproduced support gap selects a bounded representation-comparison packet. See [the execution record](runs/2026-11-25-retrieval-controller.md) for current validation and persistent handoff status. Candidate, measurement and assessment identities remain separate; currently coupled retrieval/validation changes stay incomparable. The rule does not learn success probabilities or whole-step costs.

## Adoption decisions

Keep SQLite and the current blob store until a measured query or concurrency problem requires something else. Adopt maintained retrieval libraries instead of writing a search engine. Trial Graphiti for temporal retrieval and GraphRAG for global summaries behind adapters with pinned revisions; neither owns the source of truth. Export PROV/RDF and validate SHACL at interchange boundaries after the internal contracts stabilize. Investigate refinement types or functorial migrations only where concrete transformations need stronger guarantees.

Defer a general vector database, autonomous ontology discovery, a universal causal simulator, a token, public payments, and a new multi-agent orchestration framework. Each would add infrastructure before the essential question is tested. Existing tools can supply implementations; the distinctive work is evidence eligibility, competing interpretations, preserved transformations, and credible evaluation.

## Automation and knowledge growth

The existing supervisor automation reads `TODO.md`, the durable improvement queue, and current plans. It continues ready, authorized work throughout an active session, reviewing and recording a checkpoint every 30 minutes or three core steps rather than stopping. A 15-minute heartbeat is a recovery backstop and inspects any active job before dispatching to avoid duplicate work. The primary supervises scoped builder subagents and fixed program workers; a queue does not execute itself. Per-worker time/output limits, zero paid model calls and zero external spend remain unchanged. A configured schedule is not proof of a future wake or an always-online agent.

For each eligible step, freeze relevant inputs, dispatch scoped work, review its checks, assess the actual candidate, and record a result plus successor. Dispatch that successor immediately while the session and authorized resources permit; checkpoints preserve continuity, and the next wake recovers work after an actual interruption. The installed controller handles assessment completion and next-action records. These additional event-driven capabilities remain proposed:

| Trigger | Action | Boundary and output |
| --- | --- | --- |
| New approved source or source revision | Capture exact content, record failure if unavailable, propose claim changes | Source allowlist, size/time limits, no source-instruction execution. Extraction remains a proposal. |
| Curated catalog or relevant code changes | Validate catalog and rebuild a new graph artifact | No overwrite of historical exports; compiler reads committed document bytes. |
| Conflict or ungrounded claim detected | Add a research question with evidence requirements | Never silently choose the newer source or count a self-citation as confirmation. |
| Sufficient new resolved cases | Run the registered comparison | Cohort minimum and stopping rule fixed before outcomes; no repeated significance hunting. |
| Candidate passes development gate | Freeze candidate and queue prospective evaluation | Evaluator and final cohort inaccessible to optimizer. |
| Final evaluation and independent review complete | Draft a reproducible result page and updated research status | Publication follows repository review/deployment policy; no invented success claims. |

The source-change, conflict, cohort and promotion triggers in this table are **planned**; the assessment-completion controller and fixed child dispatcher are implemented. No generic autonomous code builder, learned optimizer, sealed final evaluator, or live deployment controller is implied. Use no paid model calls until a concrete provider/model and per-run ceiling are configured under the user's standing authorization and applicable controls. Stop work at the resource ceiling while preserving partial records; do not treat failure as an empty successful extraction.

Knowledge growth should prioritize uncertainty reduction: an unresolved high-impact claim, a broken evidence link, a failed transform, or a missing control is more valuable than another thousand loosely connected entities. Each proposed research task should state what result would change a decision. Cap source expansion and candidate branching; preserve rejected proposals so the system does not repeatedly rediscover them.

## Scaling gates

Measure a local workload at roughly 100, 1,000 and 10,000 documents before selecting distributed storage. At each scale, hold question families fixed and record input bytes, assertion count, ingest/update time, memory, storage, p50/p95 query latency, retrieval recall, citation precision, temporal violations and rebuild reproducibility. These are planned checkpoints, not capacities already demonstrated.

Increase only one axis per trial: corpus size, model capability, concurrency, traffic, action scope, or spend. Freeze per-family quality floors, a practical improvement margin, side-effect ceilings, observation window and rollback before changing it. Shadow and canary evaluation precede wider service use; they remain planned stages with explicit authorization and implementation requirements. A passing fixture score cannot award new permissions or spending. The [stepwise loop](stepwise-improvement-loop.md) defines the stage gates.

Partition by access scope and snapshot eligibility before retrieval; post-filtering an answer is insufficient if hidden material influenced candidate selection. Use incremental projections only after a full rebuild is correct. Cache keys include snapshot, schema, extractor and embedding versions. Backups must preserve source bytes as well as database references. Retention and deletion policies need explicit treatment before ingesting personal or restricted material.

## Site and presentation integration

| Surface | Clarification to build after the data contracts |
| --- | --- |
| Landing page | One plain research question, one real example, visible current status, and a clear path to participate. Link this research map from the research program. |
| Five-step overview | Show the same evidence represented as a company, dependency graph and decision-rights graph; name the question each helps answer. |
| Animated lattice | Use controlled morphs to demonstrate split, merge and change of scale. Label transformation and information loss; pause/reduced-motion behavior; no meaningless confidence animation. |
| Observatory | Select snapshot and candidate; inspect evidence, disagreement, transformation and score together. Keep synthetic examples visibly separate. |
| Research pages | Display hypothesis/result/implementation status, limitations, supporting and challenging records, next experiment and last review date. |
| Shared artifacts | Stable URLs for claim bundles and frozen comparisons; downloadable inputs and scoring instructions; an attributable correction path. |

The existing site-loading and publication work is tracked separately. This investigation does not certify a rendered layout or deploy changes. For growth, instrument completed reproductions and useful corrections before optimizing presentation metrics. Public artifacts should earn sharing by being understandable and reusable.
