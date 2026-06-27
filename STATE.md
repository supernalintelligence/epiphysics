# STATE — Epimechanics / Epiphysics development handoff
 se

**Snapshot date:** 2026-06-18. This is a development and handoff document, not site content. It records where the framework stands, what was done in the recent session, what was tried and killed, the open questions, and the next-step fork. Read it before proposing new work, so the dead ends are not repeated.

The persistent memory under `~/.claude/projects/.../memory/` holds the same conclusions in compressed form; the load-bearing notes are `project_universality_critical_path.md` and `project_representation_economy.md`.

---

## 1. What the framework is, in one paragraph

Epimechanics is a substrate-neutral grammar that treats X as a representation (not reality, per Hoffman's interface view), assigns it mechanical structure (state, tensorial mass M, force, energy, a Lagrangian as the strongest structural postulate, a coupling tensor T), and measures persistence by auto-causal density ρ_ac (a loop-level emergent, equivalently the closeness of the self-application T(X)·X to X). Epiphysics is the empirical program meant to test it. Representational quality is now grounded in existence, not value: a representation is **extant** (survives) in an environment when its basin depth ΔV clears the perturbation ΔE, and efficiency is the independently measurable, selected-for trait. The surviving set 𝒮(ℰ) = {X : ΔV(X) > ΔE} is a viability kernel; the single cost-minimizer is its strong-selection limit.

---

## 2. What the recent session (2026-06) did

**Theory revision (committed):**
- Grounded representation quality in existence, replacing the value-laden "good / well-chosen representation" with **extant / surviving** across the corpus, and fixed the circular definition (good was defined partly as "has simple mechanical structure," then concluded to have it). Commit `c8823fa`.
- Added the **surviving set 𝒮(ℰ)** as a first-class concept with notation, and the relation that argmin is its strong-selection limit (viability-kernel framing). Commit `ce020c3`.
- **Purged value-laden labels** (good, better, interesting, powerful, useful, compelling, and similar) from the live content; kept legitimate terms (good regulator theorem, MDL's best model, empirical comparatives). Commit `903054b`.
- Corrected a self-inflicted error: **lossy is not less extant.** Dropped "lowest-loss" as a quality stand-in; compression funds survival rather than opposing it. Commit `e4944d2`.
- **Accuracy is matched, not maximized.** Over-accuracy is a cost with no survival return, so survival selects for threshold-matched fidelity (the Apollo / Newtonian-mechanics vs general-relativity example). Commit `802c059`.
- Added the **selection mechanism** behind the efficiency conjecture: good regulator theorem (to persist is to model the environment) plus thermodynamics of prediction (modeling it inefficiently wastes the budget).

**Applications (committed):**
- `docs/applications/costly_signaling.md`: the handicap principle derived in the framework's vocabulary (cost sets the fidelity ceiling of an adversarial coupling), with the three families and one novel-tagged prediction (signal cost scales with conflict-of-interest times receiver stake). Commit `b4754f6`.

**Research notes and audits (some uncommitted):**
- `docs/research/gap_analysis_universal_prediction_2026-06-10.md` (committed): the dependency-tower analysis; the Keystone is the critical path.
- `docs/research/self_application_ladder.md` (uncommitted): computation emerges from the mechanical substrate by iterated self-application; the proposed ladder gradient; corrected with the falsifiability verdict.
- `docs/experiments/falsifiability_audit_2026-06-17.md` (uncommitted): the audit that asked what is testable, with the verdicts below.

**Scaffolding proposed but not all written:** a representation economy with four processes (acquire, distort, signal, differentiate) under one currency, and a predictive-solvency epistemology (predictions are calibrated sharp distributions, scored by proper rules on a forward stream, with calibration as the recovered falsifiability test). Captured in memory `project_representation_economy.md`.

---

## 3. Honest current status

The framework is, today, an **integrative lens**, the value class of the free energy principle: real but modest. Across the session, every empirical-validation path that was generated was killed by adversarial review (see section 5). The framework has **no cheap clean empirical test**. The only result that would re-rank it is the **Keystone**, and even that is exposed: in physics it restates Wigner's already-known fact that the world is Lagrangian; outside physics it is untested and the prior is partial, because the framework's own self-application logic predicts mechanical structure should decay up the organizational ladder as computation takes over.

---

## 4. Core claims and their status

| Claim | What it asserts | Status |
|---|---|---|
| Lagrangian postulate (L = T − V) | dynamics derive from a variational principle in any domain | Postulate, not derived. Lens. |
| ρ_ac (auto-causal density) | persistence = self-sustaining loop density; T(X)·X near X | Operationalizable (5 definitions) but persistence is defined via ρ_ac, so dynamical definitions are circular. |
| Generalized mass M (tensorial) | resistance to state change, integral of causal density | Ordinal agreement within a domain; cardinal cross-domain commensurability unsolved. |
| Self-application / Lawvere (T(X)·X) | entities (fixed points) and computation (diagonal obstructions) are two faces of one mechanism | Structural and coherent; near-tautological as a predictor (locates fixed points, does not classify them). |
| Representational Efficiency Conjecture (the **Keystone**) | the cost-minimal representation carries strong mechanical structure (Noether conservation, sparse coupling) | Cost side is MDL/Occam (trivial). Residue: mechanical is a proper subset of compressible (PRNGs and cellular automata are compressible yet non-mechanical). Novel only outside physics, untested, not operationalized. **The one live empirical question.** |
| Costly signaling (application) | cost sets the fidelity ceiling of an adversarial coupling | Relabel of the handicap principle plus one novel-tagged, untested prediction. |
| P (ρ_ac predicts persistence beyond size) | loop structure predicts survival beyond a size baseline | **Killed** (see section 5). |
| Ladder gradient | mechanical structure falls and computational depth rises up the levels of self-application | **Killed** (see section 5). |
| Four "decisive tests" of the Keystone | probe-inside-predictor, cost frontier, transfer, derive-blind | Downgraded to diagnostic; several already answered in the literature (AI Poincare, SINDy, AI-Feynman, Gruver et al. 2022). |

---

## 5. What was tried and killed (do not re-run as validation)

- **The four "decisive tests"** → diagnostic, not decisive; mostly already answered, and the cost-frontier evidence leans against the conjecture for chaotic systems.
- **The costly-signaling demonstration** → a clean pass would reproduce Crawford-Sobel cheap-talk theory, confirming the framework and its relabeling at once. Value would require a second step (a transported fix beating a domain's own experts), not attempted.
- **The ladder gradient** → circular if height is assembly index (also a depth measure); already refuted if height is spatiotemporal scale (galaxies and crystals are large and maximally mechanical; turbulence is small and irreducible); underpowered if height is cosmic emergence time (about five fiat-bounded points). Self-reference, the axis it cares about, is unmeasurable from passive data.
- **P (ρ_ac predicts persistence beyond size)** → (1) relabels autocatalytic-set theory, feedback-vertex-set control, and ecological stability-diversity work on a pass; (2) underpowered (oscillators and flames have fixed topology so ρ_ac is constant; companies have no per-firm loop dataset and a constant hazard rate; cells are telomere-dominated); (3) the five ρ_ac definitions are not one commensurable quantity and two of them anti-correlate (May 1972); (4) circular, since the framework defines active persistence as ρ_ac > 0. Off the critical path regardless.

---

## 6. Open questions and uncertainties

1. **Can the Keystone be stated non-circularly and falsifiably at all?** This is the precondition for any empirical progress. It needs an operational mechanical-minimality criterion that is not just MDL and not circular. Unresolved.
2. **Does cost-minimization actually produce mechanical structure, or do they pull apart?** The converse direction. Risk: symmetry is merely a compression mechanism, in which case the claim collapses to MDL.
3. **Does mechanical structure exist outside physics, or does it decay up the ladder** as the self-application logic predicts? The bold claim, untested, prior is partial.
4. **Cardinal commensurability of ρ_ac and M across domains.** Currently ordinal only; this is rung 3 of the dependency tower and blocks all cross-domain quantitative claims.
5. **Can persistence be defined independently of ρ_ac** so that "ρ_ac predicts persistence" is not true by construction.
6. **Can the self-application generator classify which fixed points form** (the Lawvere note's own open question), or does it stay a near-tautological existence statement.
7. **Is the framework more than a lens?** Current honest answer: probably not, pending a non-circular Keystone.

---

## 7. Next-step fork

The choice is the author's. Three options, with the recommendation that (c) not be taken.

- **(a) Attempt the Keystone.** The only path that could make the framework more than a lens. The first task is not an experiment but a definition: state the mechanical-minimality selection principle precisely enough to be testable and non-circular. If that cannot be written down, the answer to "is anything testable" is settled and the answer is (b).
- **(b) Bank it as an integrative lens and present it as such.** Honest, defensible, nearly ready. The corpus already labels its empirical claims as open conjectures; the framing of the series would be adjusted to foreground the unifying-vocabulary value and stop implying empirical validation is near.
- **(c) A narrow P probe** (single system, single definition, no universality claim). Re-tests the feedback-vertex-set and ecology literature. Low value. Not recommended.

---

## 8. Repository housekeeping (open items)

- **Unpushed commits.** Six session commits sit on local `main` (`c8823fa`, `ce020c3`, `903054b`, `e4944d2`, `802c059`, `b4754f6`) and were not pushed this session. Pushing deploys to epiphysics.xyz via Vercel. Verify position with `git status -sb` before pushing.
- **Uncommitted new docs from this session:** `docs/research/self_application_ladder.md` and `docs/experiments/falsifiability_audit_2026-06-17.md`. Also `docs/theory/self_application_and_lawvere.md` is still untracked (it predates this session and is referenced by the ladder note; commit it).
- **Duplicate gap analysis.** `docs/research/gap_analysis_universal_prediction_2026-06-10.md` (committed) and `docs/research/universality_gap_analysis_2026-06-10.md` (untracked, pre-existing) overlap. Dedupe into one.
- **Dead links in `docs/research/index.md`.** Six linked files do not exist on disk (`paper_representational_efficiency`, `rate_distortion_lagrangian`, `representational_manipulation`, `self_multiplication`, `definitional_structure`, `experimental_protocol`). Create stubs or remove the links.
- **Build.** `npm run build` last passed after the `docs/research/index.md` merge-conflict resolution. The prose edits since are low risk but the build has not been re-run.
- **Out of scope here:** the untracked "Physics of Common Sense" book files and `experiments/entity-prediction/` belong to separate threads.

---

## 9. Working conventions and guardrails

- **No value-laden labels** in content (good, better, interesting, trivial, powerful, useful, elegant, compelling). Use structural, empirical, or existence descriptors (extant, surviving, efficient, accurate, sparse).
- **No em dashes.**
- **Avoid the "not X, it is Y" antithesis cadence**; at most one deliberate beat per section.
- **Any empirical test must follow the predictive-solvency discipline:** pre-register the envelope (horizon, accuracy ε, environment scope, reflexivity), test forward and out-of-sample, compare against a named baseline, score by a proper rule or calibration, and do not retreat to a friendlier exemplar set after a fail.
- **Do not re-propose the killed tests** (the four decisive tests, the signaling demonstration, the ladder gradient, P) as validation. If empirical ambition continues, the only target is a non-circular, pre-registered Keystone.

---

## 10. Key files

- Theory spine: `docs/theory/00_prelude.md` (section 6, the Efficiency Conjecture), `docs/theory/05_ontology_and_open_questions.md` (the Principle and the surviving set), `docs/theory/self_application_and_lawvere.md`, `docs/theory/glossary.md` (Extant Representation, Surviving Set).
- Analysis and audits: `docs/research/gap_analysis_universal_prediction_2026-06-10.md`, `docs/research/self_application_ladder.md`, `docs/experiments/falsifiability_audit_2026-06-17.md`.
- Application: `docs/applications/costly_signaling.md`.
- Memory: `project_universality_critical_path.md`, `project_representation_economy.md` (both carry the kill verdicts and the conventions).
