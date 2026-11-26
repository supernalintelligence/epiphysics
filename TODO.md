---
title: "Epiphysics work queue"
description: "Prioritized implementation and research work, selected against current measured gaps."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: false
---

# Epiphysics — Work Queue

Prioritized list of what needs to be done. Check this file when looking for work.

## Active measured improvement loop — first priority

Read the durable improvement status before choosing a packet. The [loop protocol](docs/planning/stepwise-improvement-loop.md) and [metric contracts](docs/experiments/representation-metrics.md) govern this queue. The supervisor dispatches ready, authorized successors immediately throughout its active session. Every 30 minutes or three core steps is a checkpoint to record and review progress, not a stop condition. A 15-minute heartbeat recovers unattended work; inspect or join an existing active job instead of duplicating it. The queue alone does not execute tasks.

- [x] Implement offline conformance evaluation: seven entity families, thirty checks, per-case/dimension results, macro and worst-family accuracy, provenance, coverage and time eligibility.
- [x] Implement dedicated improvement status, hashed inputs, atomic assessment-completion/successor events, stale-claim protection, and explicit failure diagnosis.
- [x] Add fixed subprocess assessment dispatch with time/output limits and retained process receipts. It does not execute arbitrary build actions.
- [x] Independently review the controller/evaluator and verify a real two-process assessment continuation. See [the bootstrap record](docs/planning/runs/2026-11-25-improvement-bootstrap.md) for the original hourly configuration; current operation uses continuous active follow-up with a 15-minute backstop. Configuration does not prove a future autonomous run or learned improvement.
- [ ] Follow the current measured gap in order: diagnose failed/interrupted runs, repair time eligibility, repair evidence ancestry, cover missing answers, then repair the weakest family. Keep all seven families and existing preservation checks.
- [x] **Packet A — reviewed source-backed assertion slice:** source-backed assertions, typed values/units, world/knowledge time, immutable revisions and unresolved conflicts now have fourteen actual-API probes (`source-span-probes-v1`: eight span, six history). Independent review and 115 engine tests passed; the recorded worker advanced to Packet B. See [the execution record](docs/planning/runs/2026-11-25-source-assertions.md). The selector advances to Packet B only after both metrics and all representation gates pass; failures route to assertion repair.
- [x] **Packet B1 — independently reviewed manifest metadata:** retained construction/configuration/ontology/predictor artifacts, stable method identity distinct from snapshot instances, explicit cost claims and a forecast-binding adapter now have twenty-two actual-API probes (`representation-manifest-probes-v2`). Independent review, 158 engine tests and the recorded B2 handoff passed; see [the execution record](docs/planning/runs/2026-11-25-representation-manifests.md). Passing B1 plus all prior gates selects B2; metadata alone does not prove construction or inference executed.
- [ ] **Packet B2 — transformation preservation:** add transformation runs, parent sets, evidence mappings and declared loss with split/merge/coarse-grain fixtures. Add a measured preservation contract and selector gate; B1 completion does not complete this packet.
- [ ] **Packet C:** freeze a permitted corpus and source-grounded questions; implement an offline lexical baseline with explicit missing-answer treatment and separate development/final evaluation ownership.
- [ ] Add measured action costs and outcome windows before estimating success probabilities or learning a next-action policy. Current cost/probability estimates are null, and observed changes are descriptive.
- [ ] Implement protected final evaluation and new prospective cohorts before predictive-advantage claims; add shadow/canary gates before changing workload or action scope. Increase one axis at a time, with per-family floors, side-effect limits and exercised rollback.

Preserve observatory collection when due, but do not let the older publication backlog displace an actionable integrity or representation gap. A completed assessment is not proof that an implementation packet passed its tests and review.

## Observatory sequence

- [x] Build the local append-only evidence, snapshot, representation, forecast, resolution, and scoring slice.
- [x] Add bounded collection cycles and synthetic demonstration data.
- [x] Clarify the landing page and add a five-step interactive introduction and inspectable example.
- [x] Validate and integrate this slice on `ian-dev` through independent review; see the 26 November run record.
- [ ] Promote through the required `ian-dev` → `main` → `production` pull requests after the separate site-loading fix is integrated; verify deployment and rendered layout.
- [ ] Add an independent witness adapter and verification fixtures; distinguish receipt time from source time.
- [ ] Add isolated model runners with explicit model/prompt/input manifests and enforced per-run budgets.
- [ ] Compare a simple baseline, a direct language-model forecast, a fixed entity graph, and a learned representation on the same prospective questions.
- [ ] Implement evaluator holdout separation, family-aware uncertainty, calibration, and abstention policies before promoting advantage claims.
- [ ] Study recursive AI control with declared measurable proxies and competing hypotheses; avoid assuming dominance.
- [ ] Design typed value-exchange events for services, data, compute, money, commitments, reputation, and governance rights; pilot in simulation before settlement adapters.
- [ ] Add privacy-conscious measurement of example inspection, record downloads, reproductions, corrections, and repeat contributions; report retention and reproduction, not raw page views alone.
- [ ] Prepare the knowledge-snapshots persona post for Ian's review. Keep it unpublished until reviewed.

The detailed dependencies and acceptance gates are in `docs/planning/2026-11-24-recursive-observatory.md`. SCI's reply on the mathematics-note handoff is verified there; observatory review remains pending.

## Existing research queue

### Representation and knowledge layer

The [research assessment](docs/research/meta-representational-systems.md), [component plan](docs/planning/meta-representation-build.md), and [six proposed protocols](docs/experiments/representation-comparison.md) define the dependency sequence. The active queue above owns Packets A–C; the existing supervisor automation continues them without a second scheduler.

- [x] Investigate primary literature and audit existing representation/graph implementations; seed a curated research map with source limitations and conflicting claims.
- [x] Add an offline validator/compiler that embeds selected committed source documents and emits a reproducible graph artifact.
- [ ] Compare hybrid retrieval and graph challengers at matched reading and total construction costs; preserve shuffled/removed-edge controls.
- [ ] Coordinate scientific revisions of prompt/Lagrangian and Lawvere claims; preserve hypothesis status until explicit constructions and discriminating tests exist.
- [ ] Register a prospective representation tournament only after model budgets, evaluator separation and numerical acceptance rules are implemented.
- [ ] Test bounded ontology revision and control/exchange mechanisms in simulation; keep real settlement adapters downstream of delivery verification.

Prior items below need their status reconciled against dated experiment records before rerunning.

### High Priority

- [ ] **Run Experiment 2** — quadratic vs quartic on low-dimensional time-series data. Simplest test. See `docs/experiments/index.md` and `docs/research/rate_distortion_lagrangian.md` (Empirical Testing section).
- [ ] **Add missing citations to paper** — Caticha (2012, Entropic Dynamics), Balasubramanian (1997, Occam factors), Transtrum/Sethna (sloppy models), Cranmer et al. (2020, Lagrangian NNs), Greydanus et al. (2019, Hamiltonian NNs), Galley (2013, non-conservative Lagrangians). File: `docs/research/paper_representational_efficiency.md`
- [ ] **Update cross-references in theory docs** — file paths changed during migration from blog. Internal links between theory parts may point to old `epimechanics_*` filenames.

## Medium Priority

- [ ] **Write AI Scaling Laws application** — neural scaling as thermodynamic signatures. See `docs/applications/index.md` for outline.
- [ ] **Address circularity concern in paper** — the conditions (non-negativity, zero-at-rest, time-reversibility) are physical desiderata, so the conclusion that physics is optimal is less deep than it appears. Needs honest engagement.
- [ ] **Refine MDL analysis with Fisher information** — the crude bound $\mathcal{K} \approx p \cdot \log(1/\delta)$ ignores Fisher information geometry. Balasubramanian (1997) and Myung/Pitt provide the tools.
- [ ] **Write Belief Dynamics application** — decomposition of $\mathcal{M}$ predicts force-matching effects in persuasion. See applications plan.
- [ ] **Write Power Structure Dynamics application** — forces, fields, coupling in governance. Connects to the governance series on ian.ceo.

## Lower Priority

- [ ] **Add P/D/C tags to equations in Parts 1-4** — index.md and Part 5 have definition/postulate/consequence tags. Parts 1-4 body text does not.
- [ ] **Generate proper cover images** for research and experiments sections (currently using default fallback).
- [ ] **Write remaining Physics of Common Sense posts** — on ian.ceo, not this repo. 11 of 15 planned posts not yet written.

## Open Research Problems

- [ ] **Step 4b: Irreversible case** — does quadratic KE minimize cost without time-reversibility? Three possibilities identified. See `docs/research/rate_distortion_lagrangian.md`.
- [ ] **Step 5: Lagrangian class optimality** — structural argument but not formal proof. Can a non-Lagrangian representation beat Lagrangian at matched complexity for systems with zero symmetries?
- [ ] **Derive the Lagrangian from bond network structure** — if $\mathcal{M}$ is composed of bonds with known strengths and $V(X)$ is determined by basin structure, can $L$ be derived rather than postulated? See `docs/theory/01_5_causants.md`, Open Question Q5.
- [ ] **Prove or disprove: rate-distortion optimality implies Lagrangian symmetry** — the central open problem. See `docs/research/rate_distortion_lagrangian.md`.
