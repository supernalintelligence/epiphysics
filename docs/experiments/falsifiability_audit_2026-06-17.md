---
title: "Falsifiability Audit: What in Epimechanics Can Actually Be Killed"
description: >-
  An adversarial audit of which Epimechanics claims are cleanly falsifiable. Verdict: the
  ladder gradient is not (circular, already refuted, or underpowered depending on the height
  coordinate); the Keystone is only partially operationalizable; the one cleanly falsifiable
  claim is P, that auto-causal density predicts persistence beyond a size baseline. Includes
  the cheap experiment that buries the ladder and the pre-registered protocol for P.
date: 2026-06-17T00:00:00.000Z
draft: true
author:
  name: "Ian Derrington"
  role: "Framework Author"
authors:
  - name: "Ian Derrington"
  - name: "Parnian Barekatain"
contentType: article
mediaTypes:
  - text
series: "Epimechanics"
categories:
  - Systems thinking
  - Mathematics
tags:
  - Falsifiability
  - Auto-causal density
  - Conserved quantities
  - Persistence
  - Pre-registration
tts:
  enabled: true
  provider: openai
  voice: onyx
  enableSpeed: true
  enableProgress: true
feedback:
  enabled: true
---

## Purpose

Settle one question for the whole framework: is anything in it cleanly falsifiable? This audit was produced by an adversarial planning pass against the [self-application ladder](../research/self_application_ladder.md) and the framework's [gap analysis](../research/gap_analysis_universal_prediction_2026-06-10.md).

## Verdict

- **The ladder gradient: not cleanly falsifiable as stated.** Its nominated height coordinate (assembly index) is also one of its computational-depth measures, so the headline test compares a quantity to itself (circular). Under the one independent coordinate with abundant data (spatiotemporal scale) the claim is already refuted by standard counterexamples (galaxies and crystals are large and maximally mechanical; Lotka-Volterra ecologies carry conserved quantities; turbulence is small-scale yet irreducible). Under the one independent, not-already-false coordinate (cosmic emergence time) it yields about five ordinal points with fiat boundaries and within-level variance that swamps the signal. The self-reference axis it most cares about is not measurable from passive data at any level.
- **The Keystone (K): only partially operationalizable.** That cost-minimal representations carry strong mechanical structure (Noether conservation, sparse coupling) beyond what information theory entails is the framework's central bet, but it is not yet operationally defined and is likely false for chaotic systems where neural surrogates are the cheapest predictors (the Gruver et al. 2022 rebuttal already cuts against it). At best partially falsifiable pending a precise definition.
- **P: the most operationalizable candidate, but circular-or-relabeling on inspection.** Auto-causal density predicts persistence beyond a size baseline. ρ_ac has computable definitions, persistence is observable, and "beyond size" looks like a non-tautological control. It was nominated here as the experiment worth running, but a second adversarial pass (below) found it does not survive either.

## Second adversarial pass (2026-06-18): P does not survive either

A hostile review of the recommendation "run P next" found P fails four independent ways, so that recommendation is withdrawn:

1. **Relabeling on pass.** "Loop structure predicts persistence beyond size" is the established result of autocatalytic-set and RAF theory, feedback-vertex-set control (Mochizuki and Fiedler; Zanudo, Yang and Albert), and fifty years of ecological complexity-stability work, all of which already control for a size or diversity baseline. A clean pass relabels known results; it does not validate Epimechanics.
2. **Underpowered everywhere.** No proposed system supplies enough independent instances with varying, measurable loop structure and a confound-free outcome. Chemical oscillators and candle flames have a fixed topology, so ρ_ac is nearly constant and there is nothing to regress. Company lifespan has no per-firm loop-topology dataset and an approximately constant, age-independent hazard rate (Daepp et al. 2015). Cell-line lifespan is dominated by telomere length.
3. **Not one commensurable quantity.** The five ρ_ac definitions are not the same measurand (several are neural-network-only), the two that apply broadly can anti-correlate (more cycles can destabilize, per May 1972), and cross-domain pooling needs the cardinal commensurability the gap analysis says the framework lacks.
4. **Circular under its natural definitions.** The framework defines active persistence as ρ_ac > 0 (see persistence_reversal.md), so for the eigenvalue-near-unit-circle and information-retention definitions, P is the stability spectrum predicting stability, true by construction. The one genuinely independent definition (cycle-flow fraction) carries a sign the framework does not predict.

Above all, P is off the framework's own critical path. The [gap analysis](../research/gap_analysis_universal_prediction_2026-06-10.md) names pre-registering the Keystone as the number-one move and notes a pass or fail on a persistence experiment would not re-rank the framework. Falsifiable is not the same as worth running.

**Revised recommendation.** Do not run P as posed. The two honest options are: (a) specify and pre-register the Keystone (representation-derivation and the mechanical-minimality selection principle), the only result that would re-rank the framework, or (b) bank the framework as an integrative lens and present it as such. A narrow single-system, single-definition probe of cycle-flow fraction is possible but it re-tests the feedback-vertex-set and ecology literature and carries no universality claim.

## Experiment 1: the cheap kill for the ladder (about 1 to 2 days)

Goal: formally falsify the ladder's mechanical-decrease claim on already-public data.

Method: count conserved quantities with AI-Poincare-style intrinsic-dimension estimation (Liu and Tegmark, PRL 126.180604, 2021) on three systems spanning the proposed ordering:
- double pendulum (physics, chaotic, one conserved quantity),
- Lotka-Volterra lynx-hare series (biology, which has a known conserved quantity),
- Belousov-Zhabotinsky reaction (chemistry).

Pass/fail: the ladder predicts conserved-quantity density falls from physics to chemistry to biology. If the biology rung shows more conserved structure than the physics rung, which Lotka-Volterra's conserved quantity makes likely, the monotone decrease is dead on three points. Symmetrically, compute statistical complexity (ε-machine, CSSR) on turbulence versus an opinion-dynamics series; if physics is at least as computationally deep as society, the computational-increase claim is dead too.

## Experiment 2: the real test (P), pre-registered

Claim: ρ_ac measured at time t adds out-of-sample predictive power for whether an entity persists after t, beyond what its size or component count predicts.

Pre-register before touching data:
- **Systems with observable lifespans:** chemical oscillators (time to damping), cultured cell lines (generations to senescence), companies (years to failure), flames (time to extinction under perturbation). Lock the set and the data sources by a fixed rule, not by inspection.
- **ρ_ac measured structure-first**, from loop topology, using one pre-chosen definition from [measures of causality](../research/measures_of_causality_autocausality.md) (for example loop flow in a thresholded causal graph, or the recurrence ratio). Compute it from the state at time t only, with no access to the later fate.
- **Baseline:** fit survival on size or component count (generalized mass proxy) alone.
- **Test:** does adding ρ_ac to the baseline improve out-of-sample survival prediction (nested-model Δ in AUC or log-loss), with a temporal separation between the ρ_ac measurement and the survival outcome to block circularity.
- **Fail line:** ρ_ac adds nothing beyond the size baseline. **Pass line:** a pre-registered, significant out-of-sample improvement.
- **No retreat:** a fail is reported as a fail for the locked system set, with no swap to a friendlier exemplar set.

The circularity guard is the whole point: ρ_ac is loop density and persistence is loop survival, so the claim has content only if ρ_ac is computed structure-first and tested on a temporally separated outcome against a size control.

## To-do

- [ ] Phase 0 (half day): decide whether to run Experiment 1 at all, given that its only purpose is to formally bury a claim already judged non-falsifiable. Optional.
- [ ] Phase 1 (1 to 2 days): run Experiment 1, the killer trio, if a written falsification is wanted.
- [ ] Phase 2: superseded by the second adversarial pass above. Do not run P as posed. Either pre-register the Keystone (representation-derivation and mechanical-minimality), or bank the framework as a lens and present it as such.

## Status

Designed, not run. Produced 2026-06-17 by an adversarial planning pass.
