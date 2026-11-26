---
title: "Experiments for revisable representations"
description: "Proposed tests of provenance, retrieval, causal abstraction, and bounded representation revision."
date: 2026-11-25T17:00:00-08:00
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

These are **proposed protocols**, not registered experiments or completed results. They extend the [prospective observatory protocol](prospective-observatory.md). Before a confirmatory run, the evaluator must fill the model/version, corpus hash, cohort dates, resource ceilings, sample-size calculation, primary endpoint, numerical promotion margin and stopping rule, then freeze that record before outcomes. Until then, runs are development pilots.

The research question is whether explicit representation choices and controlled revisions improve a specified task at a declared cost. A successful result supports that task and procedure; it does not prove that the representation is uniquely real or universally optimal.

## Shared controls

Use the same eligible evidence snapshot and prediction reader within each comparison. Charge extraction, indexing, memory construction, candidate search, retrieval and inference; report first-use and amortized costs separately. Equal retrieved tokens alone do not make total costs equal. Preserve failure, abstention, invalid outputs and unsuccessful candidates.

Register question families before selection; related events are not independent samples. Estimate sample size from a separate development pilot using family dependence and a practically meaningful effect. Use paired comparisons and family-aware intervals. Do not stop when a promising score appears. Report primary endpoint first, then secondary metrics and exploratory breakdowns.

For binary prediction, Brier score must lie in [0,1]. Report coverage and a prespecified policy for failures alongside conditional scores; an arm cannot improve by dropping hard cases. Freeze how corrected or disputed outcomes are handled. Preserve resolution IDs so scores remain reproducible after corrections.

The evaluator owns final source bundles and acceptance rules. The optimizer can receive only declared development feedback. Any final examples or scores used to choose another candidate retire that cohort to development. Provider versions, training contamination and undisclosed memory remain assurance limits even with timestamp-filtered retrieval.

## E1. Provenance and transformation fidelity

**Question:** Can a representation change preserve the information it claims to preserve?

Start with about twenty small generated schemas and hidden instances: homonymous entities, A→B and B→A, two predicates for the same pair, negation, unit conversion, missing values, conflicting reports, source corrections and late captures with old publication dates. Include the repository's competing definitions of entityhood as attributed claims.

Compare unrestricted edits, schema/type-checked edits, and edits checked against explicit semantic obligations. Test renaming, split, merge, aggregation and projection. A lossless adapter must preserve all registered queries and evidence references. A lossy adapter must declare the affected fields and queries; it is not expected to reconstruct deliberately discarded information.

Primary measures: false acceptance of a violating transform and preservation of declared queries. Secondary measures: provenance recovery, migration cost, failure clarity and deterministic replay. Passing fixtures establishes those tested properties only. Reserve proof language for discharged formal obligations with stated assumptions.

Gate before model use: zero accepted future-evidence violations; zero silent loss of source ancestry; no merged opposite directions or parallel predicates; no automatic resolution of contradictions. This is an engineering gate, not a statistical claim of universal correctness.

## E2. Retrieval and synthesis ablation

**Question:** When do graph relationships contribute beyond extra retrieved context?

Use one frozen permitted corpus. Include exact facts, multi-hop relationships, global themes, quantities, time-sensitive corrections, contradictory sources and questions with false premises. The curator marks supporting and challenging source spans. Keep the answer generator fixed.

Arms: lexical baseline; lexical/vector hybrid; the same hybrid with explicit graph expansion; pinned Graphiti; community-summary GraphRAG. Add shuffled-edge and removed-edge controls for the graph-expansion arm. Compare equal reading budgets and report total construction/update costs. Tune only on development questions.

Measure retrieval recall at the evidence-span level, citation precision, unsupported-claim rate, answer quality by family, abstention, ingestion lag, storage and tail latency. Evaluate exact-count questions with executable answers. For model-judged prose, counterbalance answer order and independently adjudicate consequential disagreements. Do not combine retrieval quality and forecasting skill into one score.

Choose a method per workload only after meeting evidence and temporal-integrity gates. Public benchmarks are useful development evidence, not uncontaminated prospective evaluation. No external benchmark has been run by this investigation.

## E3. Prospective representation tournament

**Question:** Does a chosen representation improve future predictions at matched cost?

Begin with directly observable software tasks or a small simulated workflow before public institutional forecasting. Register completion/failure questions with exact deadlines and resolution rules. Do not let the representation builder inspect outcomes or build a different evidence graph after reading each final question unless every arm receives that same declared opportunity.

Arms: raw eligible evidence; fixed entity/dependency graph; hierarchy-and-state graph; hybrid text/graph; a structure-shuffled control. Fix the predictor family and cap total construction plus inference budget. Give every arm a registered candidate identity binding encoder, memory, retrieval and predictor versions.

Primary endpoint: paired Brier difference against raw evidence on the fresh cohort. Secondary endpoints: coverage, calibration, cost, transfer to withheld task families and error severity. Freeze a practical improvement margin and allowed coverage/cost changes before outcomes. Report uncertainty and all arms, not just the best selected one.

A development win permits freezing a candidate for final evaluation. A final win supports this representation on these tasks. A null or negative result should preserve the candidate and identify whether structure failed, evidence was insufficient, or costs erased the benefit; it must not be relabeled a theoretical success.

## E4. Causal coordinates and mechanical hypotheses

**Question:** Does recovering useful causal coordinates specifically help a mechanical model, beyond helping a general predictor?

Use two stages. First, generate small latent systems through known injective observation maps with explicit interventions; check identification assumptions. Compare observational learning, intervention-assisted learning and oracle coordinates. Measure recovery modulo declared equivalences and held-out intervention error.

Second, compare conservative, damped, switching and deliberately nonmechanical synthetic processes. Freeze allowed coordinate transformations, normalization and dynamics libraries. Compare mechanically constrained models with generic regularized models of matched capacity and tuning budget. Include degenerate or trivial fits that must fail the validity check.

Measure predictive error on new initial conditions and interventions, model/encoder description costs, computation and structural residuals separately. A win on pendulums alone cannot establish universality. If causal coordinates help both model families equally, that supports causal representation learning without supporting the stronger mechanical hypothesis.

## E5. Bounded recursive revision

**Question:** Does feedback improve the representation-update method on material it has not selected against?

Compare a static representation, a fixed update rule, score-only candidate search, and trace-based reflective search. Use equal proposal and computation budgets. Permit one logged ontology revision per development tranche in the initial pilot; record attempted splits, merges and rejected changes. Include a random-revision control if the candidate count allows it without reducing other arms' budget parity.

Freeze the selected method before each new prospective tranche. Prespecify regime changes in a simulator; later use newly collected real workflow data. The controller cannot modify scoring, final cohorts, source history or promotion rules. Candidate runs are isolated with explicit permitted inputs and outputs.

Measure forward loss, adaptation delay, revision churn, provenance violations, unsupported claims and total cost. Success requires improvement over fixed and equally expensive search controls, with integrity gates satisfied. If gains appear only in selection data, the result is overfitting evidence rather than successful recursive improvement.

## E6. Control and exchange mechanisms

**Question:** Which observed mechanisms concentrate or distribute decision power in an agent-mediated exchange system?

Adapt an existing marketplace simulator before constructing a new one. Script a deterministic baseline with offers, search, acceptance, service delivery, quality verification, settlement and disputes. Vary provider substitutability, switching costs, access revocation, search ordering, response latency, identity costs and reputation visibility independently where possible. Then introduce bounded model-based agents as separate arms.

Compare concentration and portability hypotheses using explicit measures: share of transactions, dependence on a single provider, cost/time to switch, distribution of veto rights, delivered utility, fraud losses and unresolved disputes. Define the simulated population and market denominator. Report quality, money, reputation and control separately.

Add adversarial fixtures for multiple identities, collusive reviews, copied evidence, fast low-quality offers and prompt injection in service descriptions. Compare prediction-only policies with policies that act on predictions. Simulation interventions can identify effects within the simulator; external institutional claims require separately collected evidence.

There are no real payments, token launches or financial return claims in this protocol. Payment and identity adapters become relevant only after we can independently verify delivery and account for disputes.

## Required run record

Every actual run must retain its protocol and candidate hashes, code revision, source manifest, collection receipts, seeds/environment, budget ceiling and actual use, attempted/failed/abstained outputs, per-case scores, resolution references, final-cohort access log, deviations and review. Store raw evidence separately from shareable summaries. Publish negative results and limitations with the same status discipline as positive findings.

The immediate executable work is E1 and the baseline preparation for E2. E3–E6 remain queued protocols until their prerequisites and numerical registration fields are complete.
