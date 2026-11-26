# Epiphysics — Work Queue

Prioritized list of what needs to be done. Check this file when looking for work.

## Observatory sequence

- [x] Build the local append-only evidence, snapshot, representation, forecast, resolution, and scoring slice.
- [x] Add bounded collection cycles and synthetic demonstration data.
- [x] Clarify the landing page and add a five-step interactive introduction and inspectable example.
- [ ] Validate and land this slice through independent review; record actual checks and deployment state.
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
