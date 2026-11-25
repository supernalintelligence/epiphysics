---
title: "Build plan: the recursive observatory"
description: "Temporal evidence, competing representations, prospective evaluation, and distributed control and exchange research."
date: 2026-11-24T00:00:00.000Z
draft: false
author:
  name: "Epiphysics"
contentType: article
tts:
  enabled: true
  provider: openai
  voice: onyx
  enableSpeed: true
  enableProgress: true
feedback:
  enabled: true
---

> **Implementation plan, 24 November 2026.** Local implementation and proposed research are distinguished below. This is not evidence that Epimechanics improves prediction. The Epiphysics SCI Claude session has been located. On 25 November, this Codex chat received its mathematics-note handoff and sent a consolidation reply; the separate observatory brief still awaits acknowledgment.

## Intended outcome

Build a system that preserves what it could know, proposes different representations of a changing system, predicts before outcomes, and improves through comparisons others can inspect. Apply it first to its own software and agent work, then to public AI organizations, dependencies, and distributed exchange.

The ambition is generality of method. Transfer between domains is an empirical question. An entity is anything representable; its boundary is a modeling choice. A representation X is not reality. Auto-causal density concerns persistence, not entityhood. The Lagrangian remains a strong structural postulate, not an established universal law.

Public entry points are [the five-step overview](/overview), [the observatory](/observatory), and [the research program](/research/recursive-research-program). The [prospective protocol](/experiments/prospective-observatory) defines the evidence needed for stronger claims.

## What exists in this implementation

The Python standard-library engine stores exact bytes and a SQLite event chain. It supports file capture, revisions, snapshot manifests, evidence-linked entity/relation representations, binary questions, forecasts and failed/abstained attempts, outcome corrections, descriptive Brier scores, matched question/snapshot comparisons, export, and local integrity verification.

The declarative `cycle` command collects configured files or credential-free HTTPS sources. It permits 1–10 sources, limits each capture to 1 MB, uses a 10-second HTTP request timeout, and refuses redirects. Each successful capture creates a byte-change question with a constant 0.5 forecast. A later invocation resolves an earlier question within its declared window. Failures and expired windows remain visible. Completed run keys are idempotent; interrupted runs require inspection and a new key.

This is collection and evaluation plumbing. It does not discover entities autonomously, make learned forecasts, resolve semantic events, run an LLM optimizer, schedule itself, or independently witness commitments. The synthetic demo has fictional evidence, outcomes, and time. Local integrity checks cannot detect a complete rewrite or truncation without an external checkpoint. Neither a demo score nor a byte-change score validates the scientific program.

Implementation references: `engine/epiphysics/store.py`, `engine/epiphysics/cycle.py`, `engine/epiphysics/cli.py`, and `engine/tests/test_ledger.py`.

## Six components

| Component | Responsibility | Coverage and next gate |
| --- | --- | --- |
| Temporal evidence store | Exact observations, provenance, revisions, failures, and eligible evidence at each cutoff | Local SQLite/blob ledger exists. Add source metadata, restore checks, independent checkpoint adapter. |
| Representation engine | Alternative boundaries, entities, states, relationships, and beliefs | Evidence-linked graph records exist. Add candidate generation and other encodings. |
| Prediction and action runner | Frozen methods/evidence, costs, interventions, execution receipts | Binary forecasts and constant baseline exist. Add model adapter, full runtime receipt, controlled action contract. |
| Independent evaluator | Outcomes, matched comparisons, failures, corrections, uncertainty | Descriptive scores and matched pairs exist. Add preregistered cohorts, calibration, family-aware uncertainty, independent resolution. |
| Research controller | Bounded investigations, candidate changes, promotion and rollback | No autonomous optimizer exists. Add budgets, sandboxed candidates, immutable evaluators. |
| Inspection and contribution interface | Trace results to evidence; reproduce, challenge, and contribute | Landing/overview/observatory presentation is implemented. Add real ledger imports, result bundles, contribution tracking. |

The evaluator must remain separate from the optimizer. A candidate can propose a new protocol; it cannot retrospectively change the protocol judging its result.

## Eight contracts

These target interchange contracts exceed the present implementation. A field declared here is not necessarily validated by the engine.

| Contract | Required meaning | Coverage now |
| --- | --- | --- |
| Observation | Source, exact bytes/hash, event time, claimed publication time, collection time, revisions, failures | Core capture/revisions implemented; source times explicitly treated as claims. |
| Evidence snapshot | Immutable eligible observation manifest, cutoff, hash, coverage and exclusions | Manifest/hash/cutoff implemented; coverage policy planned. |
| Representation | Snapshot, observer, method/version, encoding, evidence, parent, uncertainty, construction cost | Graph records/lineage implemented; cost and uncertainty semantics planned. |
| Entity model | Hypothesized boundary/membership, resources, capabilities, beliefs, observation basis | Entity/relation payloads supported; richer entity semantics planned. |
| Prediction | Target/rule/horizon, probability or failure/abstention, snapshot, representation, model/configuration, cost, commitment | Binary records and local receipt implemented; full runtime fingerprint and witness planned. |
| Action | Actor, authority, intended intervention, resources consumed/transferred, receipt, consequences | Planned; separate prediction from intervention effects. |
| Resolution | Outcome evidence, rule application, resolver, time, disagreement, correction lineage | Binary outcomes/evidence/corrections implemented; independent workflow planned. |
| Experiment | Hypothesis, candidates, eligibility, budgets, scoring/stop rules, immutable protocol, all attempts/report | Documented protocol; machine-enforced experiment registry planned. |

Distinguish **observed**, **reported**, and **inferred** claims. A model of another actor's beliefs is an inference owned by an observer, not access to that actor's internal state. Preserve alternatives rather than silently collapsing uncertainty into a single graph.

## Two environments

**A. Our own research and software work.** Instrument tasks, tool calls, dependencies, failures, computation, and outputs. Predict completion, latency, cost, and failure. In controlled trials, test interventions such as adding a worker or changing a dependency. Dense feedback makes the observatory itself a modeled entity.

**B. Public AI organizations and dependencies.** Capture selected official releases, repositories, service notices, and filings. Begin with precise publicly resolvable events. Represent compute, distribution, data, capital, and infrastructure separately; record missing information. Do not infer secret strategy from an attractive diagram.

Success in A does not establish success in B. Transfer means freezing a method, applying it to a new environment, and measuring whether its benefit survives. More domains can use the same contracts without assuming the same useful representation.

## Recursive models, control, and exchange

Study **model → decision → resource/dependency change → capability change → observation → revised model**. Candidates may split/merge entities, change boundaries, introduce latent variables, revise directed relationships, compress memory, and retire unsupported hypotheses. Compare text, graphs, learned states, and executable models under common evidence and cost constraints.

The concern that AI companies accumulate control becomes competing hypotheses: capabilities and distribution may compound concentration; portability and open interfaces may spread capability; hardware, energy, regulation, and coordination may constrain either path. Measure control through decision rights, access rules, dependency substitution, and switching costs. Revenue, predictive accuracy, reputation, and control are different quantities.

Begin distributed value exchange in a simulator. Agents offer evidence capture, forecasts, compute, or verification; another accepts; delivery is evaluated; credits and disputes are recorded. Measure contribution, service quality, transfers, and concentration separately. A payment receipt cannot establish inference quality. Real identity, payment, reputation, and settlement systems are later adapters.

Modern AI connects through evidence-bound retrieval, structured model generation, reflective prompt/program optimization, agent task/artifact interfaces, and hypotheses from causal representation research. None substitutes for independent evaluation. Predictions may also change the systems they describe, so record actions and exposure separately; see [Performative Prediction](https://proceedings.mlr.press/v119/perdomo20a.html).

## AI methods and exchange adapters to investigate

These are design references, not implemented integrations or evidence of benefit here.

| Reference | What it contributes | Our next experiment |
| --- | --- | --- |
| [AlphaEvolve](https://arxiv.org/abs/2506.13131) | LLM-generated program changes selected through evaluator feedback | Let a candidate propose a representation/forecast program; test it against a frozen evaluator with a small search budget. |
| [GEPA](https://arxiv.org/abs/2507.19457) | Reflective prompt evolution from execution traces | Compare a fixed prompt with a development-cohort-optimized prompt, then evaluate both on new future questions. |
| [Causal representation learning](https://arxiv.org/abs/2102.11107) | Learning high-level variables rather than assuming them given | Propose entity boundaries and state variables; distinguish predictive usefulness from causal identifiability and test interventions where possible. |
| [OpenTimestamps](https://opentimestamps.org/) | Independently verifiable prior-existence proofs | Batch manifest/forecast digests, preserve pending receipts, upgrade proofs, and verify deadline bounds against an independent verifier. |

For exchange, keep an internal neutral event contract before choosing a protocol: offer, acceptance, delivery, evaluation, transfer, dispute, and resolution. Track actors, units, obligations, authority, provenance, and time separately. Services, information, computation, money, access rights, reputation, and governance participation need distinct units; no single scalar measures all value. Compare centralized, federated, and permissionless arrangements with the same simulated work and failure conditions. Candidate interoperability and settlement adapters belong behind that contract, and should be selected through a current protocol review before implementation.

## Phases and acceptance gates

| Phase | Deliverable | Gate to advance |
| --- | --- | --- |
| 0. Honest foundation | Status inventory, original visual, overview, ledger, synthetic example, limitations | Build/focused checks pass; demo and unwitnessed status visible; no universal-validation claim. |
| 1. Preserve the present | Three selected source adapters, revision/failure coverage, restore, witnessed manifest batches | Fresh environment reconstructs exact bytes/snapshots; publication dates cannot backdate eligibility; proofs verify or remain explicitly pending/failed. |
| 2. Prospective cohort | Frozen questions, calendar, baselines, deadlines, resolution rules, all-attempt report | Forecasts precede outcomes under declared assurance; missed windows/failures retained; independent reproduction of scores. |
| 3. Representation comparison | Statistical/base-rate, raw-evidence LLM, fixed entity, evolving entity candidates | Same questions/evidence and declared budgets; construction costs included; new future cohort and family-aware analysis; null results retained. |
| 4. Recursive improvement | Generator, sandbox, work queue, promotion and rollback records | Optimizer cannot edit held-out outcomes/evaluator; candidate passes fixed prospective gate; budget exhaustion halts cleanly. |
| 5. Exchange and transfer | Simulated delivery/transfers/disputes; second-environment replication | Delivery and incentives independently measured; portability tested; benefit survives transfer or is explicitly limited. |

Phases are dependencies, not promised discovery dates. Preserve observations immediately; clean prospective history takes elapsed time. Retrospective runs are diagnostics where timing or model exposure is uncertain. Retired persistence and ladder tests are not revived; any new test needs a distinct discriminating prediction and a check against the existing experiment record.

## Bounded autonomous operation

The current cycle makes **zero model calls** and runs only when invoked. A Codex heartbeat is active daily at 9 a.m. America/Los_Angeles for this chat. It checks integrity, runs one collection cycle, and advances at most one unblocked task with a 30-minute active-work limit. The host must be available. Learned candidate evaluation remains a later gate. A failed check creates a bounded diagnosis task, not unlimited retries.

Before enabling model work, record per-run and rolling limits for currency, tokens, calls, wall time, bytes, concurrency, candidates, and retries. Defaults for paid model calls and external spend stay zero until configured. Reserve evaluation capacity before exploration; stop rather than exceed the budget. Retain usage, errors, rejected changes, and remaining budget in receipts. Run candidates in isolation with explicit tool/source access. Promotion requires a fixed gate; deployment, external transactions, and public messages follow the authority granted for each action.

The planned controller selects work by expected information gain and cost. “Insufficient evidence,” “unresolved,” and “no improvement” are normal results. The app scheduler wakes the work described in `DAILY_LOOP.md`; it does not turn the engine into an autonomous scientific optimizer. The persistent store belongs in the shared checkout’s `.supernal-local/observatory`, outside temporary worktrees.

## Temporal integrity

Separate event time, claimed publication time, collection time, and independent witness time. Eligibility uses collection records; a new import with an old date cannot enter an old snapshot. Retain raw bytes, extracts, and corrections.

Historical input snapshots do not remove future knowledge from a model's weights. Record provider/model/version information available, prompts, tools, retrieval, and execution time. Unknown training exposure limits historical claims. Freeze new future cohorts, retain every attempt, and separate optimization from final evaluation. [ForecastBench](https://www.forecastbench.org/about/) is a reference for repeated future-event evaluation.

Plan a witness adapter that commits snapshot/forecast batch roots, retains proofs and raw artifacts, verifies independently, and distinguishes pending from verified. [OpenTimestamps](https://opentimestamps.org/) and [RFC 3161](https://www.rfc-editor.org/info/rfc3161/) are candidates. Existence proofs do not establish truth, completeness, exact event time, or continued availability. Register all attempts to limit selective revelation. A first-person essay is retained for review at `docs/research/knowledge-snapshots.md`; its `draft: true` status keeps it out of the public content loader.

## Landing and presentation audit

These are exact pre-change statements inspected on 24 November. They are an audit trail, not approved copy. Verify their replacement in the assigned implementation; secondary pages need a separate claim audit.

| Location and old statement | Problem | Updated message/destination |
| --- | --- | --- |
| `src/components/home/WhatsThis.tsx`: “One Equation, Any Domain”; “Epimechanics shows it works for anything that changes: beliefs, institutions, ecosystems. Same math, different substrate.” | Unestablished universality presented as a result | Landing introduces comparisons against future outcomes; `/overview` explains the test. |
| Same file: “Spacetime and quantum mechanics — including why amplitudes use complex numbers — derived from causal structure alone. No assumed physics.” | Hides assumptions/open gaps | Theory motivates hypotheses; `/research/recursive-research-program` separates conjecture and evidence. |
| Same file: “Humans conceive the theory. AIs audit every proof, check every assumption, maintain consistency across papers. Faster iteration, fewer errors.” | Implies exhaustive, reliable AI verification | Bounded assistance, explicit checks, reviewable records. |
| Same file: “Run first experiment, publish U(1) derivation” | Stale roadmap/promised scientific result | Current implementation and acceptance gates at `/observatory`. |
| `docs/home/content.yaml`: “The mathematical grammar of change — derived from first principles, experiments designed, built collaboratively with AI.” | Claimed derivation precedes practical purpose | Preserve, predict, compare, revise in plain language. |
| Same file: “The Full Derivation”; “Causal event → spacetime → quantum mechanics → life”; “Why quantum mechanics uses complex numbers — derived, not postulated” | Incomplete research chain sounds settled | A research route with assumptions and status. |
| Same file: “Theory developed. Experiments ready to run. Join us.” | Blanket status flattens mixed research history | Inspect an example, reproduce a result, propose a resolvable question. |
| `src/app/page.tsx`: “Empirical tests being designed — protocols ready, experiments not yet run” | Omits existing experiments/new infrastructure | Status per artifact; `/observatory` separates demo and measured results. |
| `docs/ELEVATOR_PITCH.md`: “Physics structure is literal (in abstract form)”; “High ρ_ac = entity-like.”; “Soul, consciousness, agency as computable quantities (not mystical)” | Proposal confused with validation; persistence confused with entityhood | Revised pitch gives the empirical question and removes unsupported measurement claims. |

Keep the theory map after a concrete example and contribution path. Use readable type, space, consistent status labels, one primary action, and source/date beside results. Do not decorate invented metrics as live data.

The `/overview` presentation has five scenes: **Observe** (what was knowable), **Represent** (alternative entities/dependencies), **Predict** (committed alternatives), **Evaluate** (outcome/cost/failures), **Revise** (learn and reproduce). `/observatory` carries the worked example and evidence status. The landing gives the promise, loop, current limits, and next action.

## Visual inspiration and rights

Inspected SI42 sources under `/Users/ianderrington/git/supernal-nova/families/supernal-coding/apps/si42-landing/`: `components/signal-lattice-hero.tsx`, `components/si42-lattice-story.tsx`, `lib/signal-lattice-morph-order.ts`, `lib/signal-lattice-scroll.ts`, and `lib/signal-lattice-knowledge.ts`. Persistent points morph while narrative panels explain a common progression. No earlier simplex implementation was verified in the bounded `public/v2` inspection.

The repository license at `/Users/ianderrington/git/supernal-nova/families/supernal-coding/LICENSE` is proprietary/all rights reserved. `lib/signal-lattice-data.ts` references downloaded mesh assets whose complete attribution was not established. Use the visual idea with original procedural geometry; copy neither proprietary implementation nor mesh arrays into Epiphysics.

Use a small deterministic Canvas2D point field with persistent identities and original simplex-like clusters. Provide stage selection, pause, reduced motion, and an accessible text equivalent. Cap pixel density, stop background/offscreen animation, and label it “illustration.” The visual explains changing representations; it does not demonstrate causal inference.

## Sharing through useful reproduction

The intended loop is **useful question → inspectable forecast → outcome → reusable result → reproduction or challenge → better question**. Each eventual result bundle needs a stable link, status, evidence cutoff, forecast/resolution IDs, method/configuration, cost, limitations, and reproduction artifact. Let readers contribute without adopting the theory.

Measure successful reproductions, accepted corrections, eligible questions, retained contributors, and time to understand an example. Track shares alongside these outcomes. Test whether clear result cards and contribution actions improve participation. “Self-viral” is an ambition to test, not a guarantee. Automated social posting and invented endorsements are outside this implementation.

## SCI handoff

**Two-way messages located; observatory review pending.** The user confirmed that Epiphysics is the SCI agent's project. The exact Claude session is `d1fe9b44-383f-4c3e-bc81-8f37a1ff0e4b`, with title/agent name `SCI`. Handoff `CPFFbfpWw4uaoewmvOrK_` was persisted to `claude-code:sci`. That initial message has no confirmed delivery. SCI subsequently addressed this Codex session directly about consolidating mathematics notes; the message was read and a reply sent on 25 November. Its scientific review of the observatory remains pending.

Exchange contracts, experiments, ownership, and limitations when SCI responds. Proposed boundary: SCI supplies candidate generation or agent-runtime interfaces where implemented; Epiphysics owns temporal evidence, prospective evaluation, and public claim status. Confirm with that agent before duplicating work. First integration gate: one SCI candidate evaluated against a frozen Epiphysics snapshot/protocol with an explicit cost receipt.

## Completion evidence for this slice

Deliver the engine/focused checks, landing/overview/observatory, this plan, public research program, draft snapshot essay, prospective protocol, and revised pitch. Report checks actually passed and remaining build issues. Completing the slice implies neither deployment nor scientific validation, witnessed timestamps, SCI agreement, paid automation, or real exchange.

## Presentation revision on 25 November

Ian rejected the first visual pass as generic and supplied a screenshot of overlapping content. The article used a `header` element that inherited the global navigation height, causing the text to spill over later sections. It now uses a normal content container. The revision removes slogan headings, colored status cards, and the dashboard-style before/after boxes. The landing uses a research introduction and a simple work index; the example uses a chronological record with source text, commitments, outcome, and calculation. The browser tool reports a saved permission or managed-policy block for the local preview origin, despite Ian confirming access. Post-revision visual verification is outstanding; no alternate browser route was used to bypass the block. Source review, the production build, and 20 engine tests pass. Repository-wide type checking still reports 42 existing errors outside changed files.
