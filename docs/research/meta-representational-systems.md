---
title: "Representations we can inspect, compare, and change"
description: "A research assessment of temporal knowledge graphs, representation learning, recursive research, and distributed exchange."
date: 2026-11-25T17:00:00-08:00
draft: false
author:
  name: "Epiphysics"
contentType: article
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

Epiphysics should build a system that can **compare and revise the way it describes a problem while retaining the evidence needed to judge the revision**. A larger knowledge graph is useful only if its distinctions help answer questions, explain failures, or make better decisions. The main research object is therefore a family of competing representations, together with explicit transformations and evaluations.

This assessment combines a repository audit with primary-source research reviewed on **25 November 2026, America/Los_Angeles**. It is a research synthesis and engineering proposal, not a systematic literature review or a demonstration of predictive advantage. External benchmark results are author-reported. The companion build plan identifies implemented and proposed components; the [experiment protocols](../experiments/representation-comparison.md) specify how to test the proposal. Machine-readable references and a first curated research map live in `research/meta-representation/`.

## What the project already has

The local engine, documented in `engine/README.md`, is the strongest starting point. It captures exact bytes, records when they entered the local ledger, freezes evidence snapshots, and preserves representations, forecasts, resolutions, and corrections. Its representation records already distinguish observed, reported, and inferred material. They retain directed, typed relationships and require evidence from the selected snapshot.

The missing layer is a contract for comparing representations themselves: schema versions, entity boundaries, state variables, units, scales, transformations, construction costs, and preserved meanings. A free-form payload can contain those fields today, but the engine does not validate them. A forecast comparison matches question and snapshot; it does not enforce equal budgets or protect a final evaluation cohort from repeated optimization.

Other implementations provide ideas, but should not become the canonical evidence store without repairs:

| Existing work | Reusable part | Gap found in the audit |
| --- | --- | --- |
| `src/types/story-graph.ts` and the story graph interface | Scenes, relationships, timelines, inspection views | The parser uses names as relationship endpoints, time-dependent IDs, and fixed confidence. Repeated mentions mutate the same object. |
| `experiments/entity-prediction/src/entity_registry.py` | Entity history and neighborhood lookup | Sorting endpoints collapses direction; one coupling key cannot preserve multiple relationship types. |
| `experiments/entity-prediction/src/knowledge_graph.py` | Hierarchies, queries, export | A `DiGraph` merges different relationships for the same ordered pair. |
| `representation_extractor.py` in that experiment | Candidate entity extraction | Averaging and overwriting erase disagreement; errors can resemble empty results. |
| `run_auto_opt.py` in that experiment | Candidate prompt generation | Selection subsets are reused without a separate untouched final evaluation; the shuffle is not reproducibly seeded. |

The `experiments/entity-prediction/` directory was **untracked in the shared checkout during this audit**. These are exploratory artifacts, not reviewed components of the integrated engine. Its reported graph Brier score of 0.136 uses a different question cohort, question-dependent construction, and additional calls. Another stored summary contains a binary Brier score above 24,000, which is invalid for probabilities in [0,1]. These results must be reconciled from per-question records before reuse. They do not establish a representation advantage.

The [representation derivation note](representation_derivation_problem.md) already identifies the core scientific gap: the useful variables and couplings are usually supplied by the investigator. The next step is to make their construction, revision, and evaluation observable.

## What a meta-representation means here

For a particular task, describe a representation as

$$
R = (\Sigma, Z, E, Q, F; S, O, H, C).
$$

Here, $\Sigma$ specifies entities, relations, units, and identity rules; $Z$ is the state space; $E$ encodes observations; $Q$ defines queries or decoding; and $F$ predicts or evolves states. The remaining fields specify the evidence snapshot $S$, observer $O$, task and horizon $H$, and cost accounting $C$. These are proposed engineering fields, not a claim that reality has this decomposition.

A **meta-representation** describes families of these objects, the transformations permitted between them, and the evidence used to select among them. A transformation must say what changes and what should be preserved. Renaming an entity, merging two institutions, averaging daily observations into weeks, replacing a graph with an embedding, and changing the revision algorithm are different operations.

Four levels of adaptation should be reported separately:

1. **Parameter fitting:** change coefficients inside an unchanged representation.
2. **Coordinate change:** encode the same modeled state differently.
3. **Ontology revision:** change entity boundaries, relations, variables, or primitives.
4. **Method revision:** change how candidate representations are proposed and selected.

A system may improve at one level and fail at another. Self-description alone establishes none of them. Each needs an immutable before/after record, an executable or inspectable mapping, and an evaluation outside the proposal process.

The goal is a common interface across domains, not a single ontology that makes every domain use the same entities. An organization may be a legal entity for ownership questions, a dependency network for reliability, and a collection of decision rights for control. All three views can coexist.

## Evidence, claims, and graph views

Separate evidence from interpretations. A source document is an observation; “company A controls service B” is an attributed assertion; a forecast about service B is another object. A source's claim about itself is not independently observed control. An agent's summary of that source is not another independent witness.

Assertions need stable IDs, subject/predicate/object or a typed value, units, scope, supporting source spans, observer and extraction version, and a basis such as reported or inferred. Confidence in extraction, trust in a source, and probability of a future outcome must remain separate quantities.

Use at least two time axes: **when a claim concerns the world** and **when the system learned it**. Publication dates and independent witness receipts are additional fields. A correction learned on Friday about Monday cannot enter Wednesday's knowledge snapshot. A later source may describe a changed world, correct an earlier report, or simply disagree. Preserve those cases instead of applying “newer wins.”

Standards can reduce unnecessary invention. [RDF 1.1](https://www.w3.org/TR/2014/REC-rdf11-concepts-20140225/) supplies an interchange model, but its graph model is atemporal. [PROV-O](https://www.w3.org/TR/2013/REC-prov-o-20130430/) describes attribution and derivation; [SHACL](https://www.w3.org/TR/2017/REC-shacl-20170720/) checks declared graph constraints. [Nanopublications](https://arxiv.org/abs/1809.06532v1) package individual assertions with provenance. These solve representation and exchange problems, not factual verification. The cited RDF/SHACL releases are compatibility baselines, not claims about the newest standards.

Keep the append-only ledger as the record of evidence and decisions. Build replaceable graph, lexical, vector, tabular, and program views over it. Each projection must identify its snapshot and construction method. A refreshed summary or changed embedding model must not silently change an earlier experiment's input.

## What modern retrieval research changes

[Microsoft GraphRAG](https://arxiv.org/abs/2404.16130v2) supports community summaries for global questions about a corpus. Its evaluated comprehensiveness and diversity do not establish universal factual accuracy. This is a candidate retrieval mode, especially for “what themes connect these findings?”, rather than a replacement for exact evidence retrieval.

The November 2026 revision of [RAG vs. GraphRAG](https://arxiv.org/html/2502.11371v4) makes budget matching particularly relevant: one MultiHop-RAG comparison reports 65.77 for the smaller-context baseline, 71.01 after matching retrieved-token budget, and 71.17 for GraphRAG. That configuration is near parity, not proof of equivalence. It motivates a cost-controlled comparison here. [BEIR](https://arxiv.org/abs/2104.08663v4) also provides a reason to retain lexical retrieval as a serious baseline, although its evaluated models are historical.

[Graphiti](https://github.com/getzep/graphiti) offers temporal edges and hybrid retrieval. Evaluate a pinned implementation as an adapter; do not replace independent assertion history with its mutable interpretation layer. The [Zep paper](https://arxiv.org/html/2501.13956v1) reports memory improvements against specified baselines and describes an invalidation policy favoring newer information. That policy is unsuitable as Epiphysics' automatic rule for scientific truth.

Evaluation must separate finding evidence, answering a question, and predicting a future outcome. [LongMemEval](https://arxiv.org/abs/2410.10813v2) tests temporal reasoning, updates, and abstention. [LongMemEval-V2](https://arxiv.org/html/2605.12493v1) adds environment-specific experience but uses prerecorded trajectories. [WildGraphBench](https://arxiv.org/html/2602.02053v2) tests heterogeneous sources and exposes limitations in detailed summarization. None substitutes for a prospective Epiphysics cohort. Model judges require order controls and human adjudication of important disagreements.

The initial retrieval comparison should use a fixed reader with four challengers: lexical/vector hybrid, that same retriever with graph expansion, pinned Graphiti, and community-summary GraphRAG. Compare by question family. Charge ingestion, updates, retrieval, and reading; preserve original passages alongside summaries.

## Learning better representations

[Minimum description length](https://www.sciencedirect.com/science/article/pii/0005109878900055) is a useful selection principle: account for model and data description together. A short prompt is not necessarily a short system. Its interpreter, encoder, decoder, residual model, and external memory can hide complexity. Define a coding convention and report actual computation alongside description length.

[DreamCoder](https://arxiv.org/abs/2006.08381) demonstrates library growth and improved search over specified program-learning tasks. This suggests a concrete route to reusable representational primitives. It does not establish that a discovered program denotes the uniquely correct entity. [Refinement-type synthesis](https://arxiv.org/abs/1510.08419) suggests checking transformations against obligations such as retaining provenance or units. Satisfaction of a formal specification remains different from whether that specification captures scientific intent.

[Functorial data migration](https://arxiv.org/abs/1009.1166) gives precise semantics for mappings between schemas. Use it to reason about joins, projections, and migrations. A canonical migration may still lose information; an adjunction is not a certificate of scientific equivalence.

Causal variables require more than a pleasing latent space. [Locatello et al.](https://proceedings.mlr.press/v97/locatello19a.html) establish limits to unsupervised disentanglement without assumptions. [Ahuja et al.](https://proceedings.mlr.press/v202/ahuja23a.html) obtain identification with interventions under explicit decoder, support, reconstruction, and intervention conditions. These results motivate controlled simulators where those conditions can be inspected.

For causal abstraction, test whether the mapped models agree about interventions, not just whether their graphs look similar. [Rubenstein et al.](https://arxiv.org/abs/1707.00819) formalize this through exact transformations between structural equation models. Our implementation should start with finite fixtures and approximate errors; a successful empirical check must not be called a general proof.

Use a Pareto comparison across prediction loss, calibration, coverage, construction cost, latency, transfer, and intervention fidelity. A domain-specific decision rule may combine these, but the weights must be visible. There is no justified universal scalar that makes money, truth, compute, reputation, and control interchangeable.

## Recursive improvement and its limits

[GEPA](https://arxiv.org/html/2507.19457v2) shows how execution feedback can guide prompt evolution, with training, validation, and test roles separated. [AlphaEvolve](https://arxiv.org/html/2506.13131v1) couples code proposals to automated evaluators. Their results motivate bounded search with useful evaluators. Mathematical constructions that can be checked exactly and industrial performance reports have different evidence requirements; neither establishes unrestricted recursive improvement.

The practical loop is: propose a revision, check its contract, evaluate on development material, freeze it, then test on new material. If a final cohort informs another revision, it becomes development data. Repeatedly exposing exact holdout scores leaks information even when examples remain hidden; [adaptive-data-analysis results](https://arxiv.org/abs/1506.02629) require specific mechanisms and assumptions, not merely a file called “holdout.”

[Gödel machines](https://arxiv.org/abs/cs/0309048) describe proof-based self-rewrites relative to encoded axioms, utility, and costs. They clarify conditions for a formal guarantee; they do not guarantee practical discovery of useful proofs. [Lawvere's theorem](https://tac.mta.ca/tac/reprints/articles/15/tr15.pdf) gives fixed points under a specified categorical hypothesis. It does not imply attraction, dynamical stability, conservation, or a Lagrangian. [Gödel's incompleteness result](https://doi.org/10.1007/BF01700692) likewise does not prevent useful bounded verification.

Three local claims need explicit qualification in the research map:

| Local claim | Treatment in this program |
| --- | --- |
| A prompt acts as a Lagrangian | A modeling analogy or hypothesis until variables, objective, dynamics, and an independently testable correspondence are supplied. |
| Self-application categorically justifies mechanical structure | An open construction problem. Specify the category, morphisms, required witnesses, and derivation before asserting a consequence. |
| Only persistent fixed points are entities | Conflicts with the repository convention: an entity is anything representable; persistence is a separate property. Retain both attributed statements and the conflict. |

This preserves ambitious ideas while making their evidential status inspectable. The [Lawvere note](../theory/self_application_and_lawvere.md) and [predictive representation note](predictive_representation_dynamics.md) should receive coordinated revisions; this investigation does not silently rewrite another agent's research.

## AI concentration, control, and value exchange

Study competing mechanisms rather than assuming AI-company dominance. One hypothesis is that better capability increases revenue, infrastructure access, distribution, and further capability. A competing hypothesis is that portability and substitutable providers distribute those benefits. Another is that energy, coordination, regulation, or integration costs limit both processes. These are scenarios to test, not current empirical conclusions.

For each actor, record observable capabilities and rights: who can change prices, allocate compute, revoke access, alter an interface, export data, move a workload, or choose a settlement route? Represent ownership, technical dependence, contractual rights, and actual usage as different relationships. Attach evidence and missingness to each. Treat concentration indices as descriptive summaries; define the market and denominator before computing them.

Forecast narrow, resolvable events: a declared service becomes portable across two providers; an interface is withdrawn; a specified workload can be migrated within a measured cost; a published access rule changes. Avoid attempting to forecast “dominance” as an undefined binary outcome. Observational correlations do not identify which mechanism caused concentration.

The observer also changes the system. Recommendations can move demand, funding, and visibility, altering the outcomes being predicted. [Performative prediction](https://proceedings.mlr.press/v119/perdomo20a.html) formalizes such feedback under stated assumptions. Simulations should compare prediction-only and prediction-with-action settings, and report the intervention policy.

For distributed exchange, begin with a simulator containing offers, acceptance, delivery, independent evaluation, settlement, disputes, and changes of governance. Track service quality, price, compute, credit, reputation, and access rights separately. Test false identities, collusion, selective reporting, copied reviews, latency advantages, and refusal to serve. [Magentic Marketplace](https://www.microsoft.com/en-us/research/publication/magentic-marketplace-an-open-source-environment-for-studying-agentic-markets/) is a useful existing environment: its authors report substantial sensitivity to search conditions and first-offer bias. Those simulated findings do not establish real-market outcomes.

Protocol choices come after a measurable exchange task. [ERC-8004](https://eips.ethereum.org/EIPS/eip-8004) is currently marked Draft and proposes identity, reputation, and validation registries; payments are separate. [x402](https://github.com/x402-foundation/x402/blob/main/docs/introduction.md) supplies an HTTP payment flow. These can be adapters after simulation. Identity registration and successful payment do not establish that useful work was delivered, that reviews are independent, or that access is decentralized.

## Historical knowledge and public verification

Start clean prospective archives now. Backfill is still useful, but label its assurance: independently archived historical bytes, signed releases, current reconstructions, or unverified publication claims. Present access to an old-looking page does not show what an agent could have known then. A current model may already contain later outcomes in its weights, even if retrieval is time-filtered.

[OpenTimestamps](https://opentimestamps.org/) can provide a proof that committed bytes existed before an anchoring point. A witness adapter should distinguish pending submissions from verified receipts and preserve original manifests. It cannot prove truth, complete collection, exact original publication time, or what was inside a model. Anchoring a digest is also insufficient if the corresponding data disappears.

Use a local append-only record, independent witness receipts, and separately retained public bundles as distinct assurance layers. Do not put private source contents or personal data on a public chain. No blockchain or payment integration was performed for this investigation.

## What would count as progress

The first meaningful result is a reproducible map of our own claims, evidence, implementations, and disagreements. The second is a transformation that preserves declared queries and provenance. The third is a matched-cost prospective experiment where changing the representation improves a specified task. Only after these should the system autonomously choose larger representation revisions.

Public communication should follow that sequence. The landing page should lead with the research question and a visible working example; the research page should distinguish implemented machinery, open hypotheses, and evaluated results. The animated graph can show a real split, merge, correction, or change of scale over a frozen example. Its labels and downloadable record should explain what changed. Motion is useful when it exposes a transformation, not when it substitutes for evidence.

For participation, publish small inspectable claim bundles, reproducible comparisons, unresolved questions, and correction paths. Measure successful reproductions, useful corrections, and returning contributors. Sharing should result from useful artifacts; no architecture guarantees virality.
