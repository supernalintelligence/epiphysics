---
title: "Research Note: Predictive Representation Dynamics"
description: >-
  Prompt-as-Lagrangian, evolving representation enforcers, asymmetric coupling,
  state transitions via energy exchange, timescale-dependent failure modes, and
  self-referential meta-optimization of minimal representations.
date: 2026-04-06T00:00:00.000Z
draft: true
author:
  name: "Ian Derrington"
contentType: article
series: "Epimechanics"
tags:
  - Epimechanics
  - Representation
  - Prediction
  - Coupling
  - State transitions
  - Embedding spaces
  - Self-multiplication
  - Supernal
tts:
  enabled: true
  provider: openai
  voice: onyx
  enableSpeed: true
  enableProgress: true
feedback:
  enabled: true
---

## Overview

This note develops a family of connected ideas arising from the question: **how do you predict the future of a complex system?** The Epimechanics answer is: identify entities, measure their states, estimate their couplings, and find the representation where the mechanical grammar (state, mass, force, energy, Lagrangian) compresses dynamics most efficiently.

We develop this in ten sections:

1. **Prompt as Lagrangian** — the structural constraint that determines prediction
2. **Evolving representations** — prompts that update themselves via prediction error
3. **Timescale-dependent failure modes** — why prediction accuracy varies across timescales
4. **State transitions via coupling** — how entities change state through energy exchange
5. **Asymmetric coupling and power** — when influence is not mutual
6. **Embedding space over graphs** — preserving nuance through continuous representations
7. **Two-stage prompt optimization** — prompts that optimize prompts; entity-outcome frame; multi-scale residuals
8. **The non-triviality of minimal representation** — why compression beats appending; $X_\Gamma$ as Lagrangian of data; summarization vs. compression vs. representation
9. **Evolving memory as the real representation** — beyond prompts to systems; agent teams; scored prediction ensembles
10. **The prediction market gaming problem** — reflexivity, asymmetric coupling as manipulation, detecting and resisting gaming

Each section connects back to the Epimechanics formalism and identifies what is proven, what is conjectured, and what is open.

---

## 1. Prompt as Lagrangian

### The identification

A prompt $P$ given to a language model performs the same structural role as the Lagrangian $L$ in mechanics:

| Component | LLM system | Epimechanics |
|---|---|---|
| Structural constraint | Prompt $P$ | Lagrangian $L = T - V$ |
| Current state | Input $X(t)$ | State $X$ |
| Predicted next state | $\hat{X}(t{+}1) = \text{LLM}(P, X(t))$ | Trajectory under Euler-Lagrange |
| Prediction error | $\|X_{\text{actual}}(t{+}1) - \hat{X}(t{+}1)\|$ | Action $\delta\!\int\! L\,dt \neq 0$ (off-shell) |
| Optimal constraint | $P^* = \arg\min_P\;\text{loss}$ | $L^*$ that minimizes total predictive cost |

The prompt is not data. It is the **coordinate system** — the set of structural assumptions that determines what the model attends to, which entities it tracks, and what couplings it respects. Different prompts induce different representations of the same input, yielding different predictions.

### Why this is more than analogy

The Representational Efficiency Principle (REP) states: the representations of a dynamical system that survive are biased toward Lagrangian structure with quadratic kinetic energy. If this holds, then the optimal prompt $P^*$ — the one that minimizes total predictive cost (description length + integration cost) — will encode Lagrangian structure implicitly. The prompt doesn't need to *contain* equations of motion; it needs to *enforce* the structural constraints that make prediction cheapest.

**Status:** Conjectured. The theorem proves quadratic optimality for time-reversible systems. Extension to prompts as representation enforcers is a new operationalization, not a new claim.

---

## 2. Evolving Representations

### Prompt evolution as structural change

A static prompt assumes fixed domain structure. Real systems have entities that emerge and dissolve, couplings that shift, and regimes that transition. The prompt must evolve:

$$P(t{+}1) = P(t) + \delta P^*$$

where $\delta P^* = \arg\min_{\delta P}\;\text{loss}(X_{\text{actual}}(t{+}1),\;\text{LLM}(P(t) + \delta P,\; X(t)))$.

This is gradient descent on the representation itself — not on model weights, but on the **structural postulate**. In Epimechanics terms, it corresponds to the force equation's cross-term:

$$F = \mathcal{M}\ddot{X} + \dot{\mathcal{M}}\dot{X}$$

The second term $\dot{\mathcal{M}}\dot{X}$ captures what happens when the representation (generalized mass $\mathcal{M}$, encoded in $P$) changes while the system is evolving. The prompt update is $\dot{\mathcal{M}}$.

### The self-multiplication connection

A prompt that updates itself based on its own prediction errors is an instance of $\mathbf{T}(X) \cdot X$ — the self-multiplication mechanism. The representation acts on itself to produce a lower-cost representation:

$$P_{t+1} = f(P_t, X(t), X_{\text{actual}}(t{+}1))$$

When this loop sustains itself — when using $P$ generates evidence that improves $P$ — the prompt has $\rho_{\text{ac}} > 0$. It has become an entity in the Epimechanics sense: a self-sustaining causal loop.

### A prompt is a universal representation enforcer

The prompt enforces structure on arbitrary input. It does not need to know the domain in advance; it needs to encode the *type* of structural constraints that make prediction efficient. This is "universal" in the same sense that the Lagrangian is universal: it provides grammar, not vocabulary. The vocabulary (domain-specific entities, couplings, scales) is learned through the evolution loop.

### The compression constraint

An evolving prompt can overfit — growing to encode every observed fluctuation. At that point it is no longer a representation; it is a recording. The Representational Efficiency Principle constrains this: **$P$ must stay compressible**. The optimal $P^*$ at any time $t$ is the shortest prompt that achieves prediction accuracy within tolerance $\varepsilon$. This is directly the MDL (Minimum Description Length) principle applied to representation enforcers.

**Status:** Framework-level claim. Operationalization via DSPy-like prompt optimization systems is feasible today. Experimental validation requires comparing evolved prompts against static baselines on multi-timescale prediction tasks.

---

## 3. Timescale-Dependent Failure Modes

### Why prediction accuracy varies across timescales

A fixed prompt $P$ coupled with input $X(t)$ will predict with variable accuracy at different timescales. There are six structurally distinct reasons, each with a diagnostic signature and a prescribed fix.

### Mode 1: Wrong-scale dynamics

$P$ encodes a generalized mass $\mathcal{M}$ whose eigenvalues resolve certain frequencies. Modes faster than the fastest eigenvalue appear as noise. Modes slower than the slowest appear as invisible drift.

- **Signature:** Smooth, consistent-sign bias (undershoot or overshoot) at timescales longer than the representation's horizon
- **Fix:** Change $\mathcal{M}$ eigenvalues — attend to different frequencies. In prompt terms: add or remove temporal context, change aggregation windows

### Mode 2: Wrong entities

At hourly scale, "vessel #4721" is an entity. At yearly scale, "global fleet capacity" is the entity. At decade scale, "trade route topology" is the entity. $P$ that names entities at the wrong granularity will predict poorly not because dynamics changed, but because $\rho_{\text{ac}}$ thresholds are scale-dependent.

- **Signature:** Prediction low-error within entity clusters, high-error at entity boundaries or transitions
- **Fix:** Coarse-grain or refine entity ontology. Apply meta-entity emergence criterion: $\text{EI}(\text{macro}) > \text{EI}(\text{micro})$ at the target timescale

### Mode 3: Wrong couplings

Short timescale: price couples to inventory. Medium: price couples to policy. Long: price couples to technology and geology. The coupling tensor $T^i_j$ is a function of timescale. This is Simon's near-decomposability: within-unit couplings dominate at fast timescales, between-unit couplings at slow ones.

- **Signature:** Prediction error correlated with states of entities not in $P$'s coupling model
- **Fix:** Add or remove coupling terms. Estimate transfer entropy at the target timescale to discover which couplings matter

### Mode 4: Wrong dissipation model

Fast timescales are nearly reversible (a price tick can be undone by the next). Medium timescales are dissipative (trends have friction, mean-revert). Long timescales are irreversible (regime changes, entity death, structural transformation).

The quadratic optimality theorem holds for reversible systems. As timescale lengthens and irreversibility increases, the Lagrangian needs correction terms — the linear drift vector $a_i$ from the rate-distortion analysis.

- **Signature:** Asymmetric prediction error (predicts reversals that don't happen, or misses irreversible transitions)
- **Fix:** Add irreversibility correction $a_i$ to the kinetic energy: $K = \frac{1}{2}\mathcal{M}_{ij}\dot{X}^i\dot{X}^j + a_i\dot{X}^i$

### Mode 5: Chaos horizon

Deterministic chaos has finite Lyapunov time $\tau_L$ — prediction error grows exponentially as $\sim e^{\lambda t}$ past it, regardless of representation quality. No $P$ fixes this. But the **basin structure** (which attractor the system is near) may remain predictable even when the trajectory within the basin is not.

- **Signature:** Prediction error grows exponentially with horizon length
- **Fix:** Switch from trajectory prediction to basin prediction at $t > \tau_L$. $P$ should identify basins of attraction and transition probabilities between them, not track trajectories within basins

### Mode 6: Reflexivity (observer coupling)

At short timescales, the model observes passively. At long timescales, the model's predictions feed back into the system (self-fulfilling prophecy, market reflexivity, Soros's reflexivity principle). $P$ alters the thing it predicts. The model is an entity coupled to the system.

- **Signature:** Error correlates with model's own prior outputs; prediction accuracy degrades after the model is deployed, not before
- **Fix:** Add self-coupling term. $P$ must model itself as an entity with coupling $\kappa_{\text{self}}$ to the system state

### The meta-prompt

The meta-prompt $P_{\text{meta}}$ is the prompt that diagnoses **which failure mode is active** and prescribes the minimal structural correction:

$$P_{\text{meta}}:\;(P, X(t), X_{\text{actual}}(t{+}1), \tau) \;\mapsto\; (\text{failure mode},\; \delta P)$$

$P_{\text{meta}}$ does not need domain knowledge. It needs to classify failure signatures and apply the corresponding structural fix from the table above. This is the self-referential loop closed: $\mathbf{T}(P) \cdot P \to P'$.

The **minimal representation of the model** is the smallest $P_{\text{meta}}$ that correctly diagnoses $P$'s failures across timescales. Finding this minimal $P_{\text{meta}}$ is itself a Representational Efficiency problem.

**Status:** Conceptual framework. Each failure mode and its signature are individually testable. The meta-prompt architecture is implementable with current systems.

---

## 4. State Transitions via Coupling

### Quantum-like locality in representation space

Entities occupy states that are locally stable — sitting in potential wells with basin depth $\Delta V$. State transitions occur when energy is supplied (via coupling to other entities) sufficient to overcome the barrier.

This is identical in structure to quantum state transitions and chemical reactions:

$$\text{Entity in state } X \xrightarrow{\Delta E \geq \Delta V} \text{Entity in state } X'$$

The energy $\Delta E$ arrives through coupling mechanisms — interactions with other entities that transfer causal influence. Just as an electron transitions between energy levels via photon absorption, an entity transitions between representational states via coupling to external energy sources.

### Mutual state transitions

State transitions need not be unilateral. Two coupled entities can undergo **mutual transitions** where both change state simultaneously:

$$(X, Y) \xrightarrow{\kappa_{XY}} (X', Y')$$

This is the chemical reaction analogy: reactants $(X, Y)$ become products $(X', Y')$ through coupling $\kappa_{XY}$. The coupling doesn't just transfer energy; it transforms both participants.

Examples:
- **Negotiation:** $(X{=}\text{position}_A, Y{=}\text{position}_B) \to (X'{=}\text{compromise}_A, Y'{=}\text{compromise}_B)$
- **Market transaction:** $(X{=}\text{cash}, Y{=}\text{asset}) \to (X'{=}\text{asset}, Y'{=}\text{cash})$
- **Chemical reaction:** $(X{=}\text{H}_2, Y{=}\text{O}_2) \to (X'{=}\text{H}_2\text{O}, Y'{=}\text{heat})$
- **Diplomatic recognition:** $(X{=}\text{unrecognized state}, Y{=}\text{major power}) \to (X'{=}\text{recognized state}, Y'{=}\text{committed ally})$

### Basin structure determines transition accessibility

Not all transitions are equally accessible. The potential landscape $V(X)$ determines:

1. **Basin depth $\Delta V$:** energy required to leave current state (stability)
2. **Saddle height:** barrier between adjacent basins (transition cost)
3. **Basin topology:** which states are adjacent (transition graph)
4. **Path dependence:** whether the transition path matters (hysteresis)

An entity with deep basin depth (diamond, deeply held belief, constitutional law) requires enormous coupled energy to transition. An entity with shallow basin (fashion trend, provisional policy, weakly held opinion) transitions easily.

### Different entities have different abilities to influence state

This connects directly to the agency formalism:

$$A^{(\mathcal{D})} = C_{\text{coupling}}^{(\mathcal{D})} \times \mu_{\text{meta}} \times C_{\text{consciousness}}^{(\mathcal{D})}$$

The coupling strength $C_{\text{coupling}}$ determines how much energy an entity can deliver to another entity's state. High-agency entities can catalyze transitions in low-basin-depth entities easily. Low-agency entities cannot catalyze transitions in high-basin-depth entities regardless of effort.

**Status:** Structural extension of existing formalism. The chemical reaction analogy is exact for symmetric transitions; asymmetric coupling (next section) extends it.

---

## 5. Asymmetric Coupling and Power

### The asymmetry of influence

Coupling between entities is generically **asymmetric**. The coupling tensor $T^i_j$ has $T^i_j \neq T^j_i$ in general:

$$F_{Y \leftarrow X} = T^Y_X \cdot \nabla_X \Phi \neq F_{X \leftarrow Y} = T^X_Y \cdot \nabla_Y \Phi$$

### Example: President and Country

Let $X = \text{president}$, $Y = \text{country}$.

The coupling is multiplicative and asymmetric:

$$T^Y_X \gg T^X_Y$$

The president's state changes (decisions, directives, rhetoric) produce large forces on the country's state. The country's state changes (public opinion shifts, economic fluctuations) produce smaller forces on the president's state (mediated through polling, elections, institutional feedback).

This asymmetry is not merely quantitative — it is **structural**. The president has:
- High $C_{\text{coupling}}^{(\text{policy})}$ (institutional authority to act)
- High $\mu_{\text{meta}}$ (represents their own decisions as decisions)
- Variable $C_{\text{consciousness}}$ (awareness of country's actual state)

The product $A = C_{\text{coupling}} \times \mu_{\text{meta}} \times C_{\text{consciousness}}$ means a president with high coupling but low consciousness (unaware of actual conditions) has high nominal power but misdirected agency.

### Power as asymmetric coupling ratio

Define **power** of $X$ over $Y$ as:

$$\Pi_{X \to Y} = \frac{T^Y_X}{T^X_Y}$$

- $\Pi > 1$: $X$ influences $Y$ more than reverse (asymmetric power)
- $\Pi = 1$: symmetric coupling (peer relationship)
- $\Pi < 1$: $Y$ dominates $X$

This ratio is:
- **Domain-specific:** A CEO has $\Pi \gg 1$ over employees in operational domain, $\Pi \approx 1$ in personal relationships
- **Time-varying:** Power shifts as coupling structures change (elections, revolutions, market crashes)
- **Not transitive in general:** $\Pi_{A \to B} > 1$ and $\Pi_{B \to C} > 1$ does not imply $\Pi_{A \to C} > 1$

### Mutual transitions under asymmetric coupling

When $(X, Y) \to (X', Y')$ occurs with $T^Y_X \gg T^X_Y$:
- $Y$'s state change is large (country undergoes major policy shift)
- $X$'s state change is small (president's internal state barely changes)
- The transition looks nearly unilateral from the outside
- But $X$ still changes — the act of exerting force alters the agent (commitment effects, political capital spent, precedent set)

### Connection to the Lagrangian

Asymmetric coupling means the kinetic energy tensor $\mathcal{M}_{ij}$ for the joint system $(X, Y)$ has off-diagonal terms:

$$K = \frac{1}{2}\mathcal{M}_{XX}|\dot{X}|^2 + \mathcal{M}_{XY}\dot{X}\dot{Y} + \frac{1}{2}\mathcal{M}_{YY}|\dot{Y}|^2$$

With $\mathcal{M}_{XY} \neq \mathcal{M}_{YX}$ in dissipative systems (where the antisymmetric part of $\mathcal{M}$ is nonzero). In conservative systems, $\mathcal{M}$ is symmetric and power asymmetry must enter through the potential $V(X, Y)$ or the coupling tensor directly.

**Status:** Structural claim. The power ratio $\Pi_{X \to Y}$ is operationally measurable via Granger causality ratios or interventionist experiments. The connection to antisymmetric mass tensors in dissipative systems is conjectured.

---

## 6. Embedding Space over Graphs

### The problem with graph representations

Entity-coupling dynamics naturally suggest a graph: nodes = entities, edges = couplings, edge weights = coupling strengths. This is tempting but loses nuance:

1. **State compression:** Graphs represent entity state as a node label or low-dimensional attribute vector. The actual state $X$ may be high-dimensional and continuous.
2. **Coupling compression:** Graph edges encode coupling existence and strength, but not coupling *type* (symmetric vs. asymmetric, conservative vs. dissipative, frequency-dependent).
3. **Scale collapse:** Graphs flatten the hierarchical entity structure. A node is a node regardless of whether it represents a person, a company, or an industry.
4. **Dynamics as topology change:** In graphs, entity birth/death = node addition/removal; coupling change = edge rewiring. These are discontinuous operations applied to continuous processes.

### Staying in embedding space

The alternative: represent entities as **regions in a continuous embedding space** rather than discrete graph nodes.

- **Entity = cluster in embedding space.** A region of high density with coherent dynamics. Entity boundaries are density gradients, not hard edges. This directly mirrors the Epimechanics definition: entity boundary $\partial E = \{x : \rho_{\text{ac}}(x) = \rho_{\text{threshold}}\}$.

- **Coupling = geometric relationship between regions.** Distance, curvature, and flow fields between clusters encode coupling strength, type, and asymmetry — all without discrete edge structures.

- **Hierarchy = scale of clustering.** Single-word embeddings form fine-grained clusters. Phrase-level concepts form coarser clusters. Domain-level structures form the coarsest. The hierarchy emerges from the geometry, not from an imposed ontology.

- **Dynamics = flow through embedding space.** Entity evolution is continuous trajectory, not discrete state machine. Birth = cluster formation (density exceeds threshold). Death = cluster dissolution (density drops below threshold). Transitions = trajectories between basins.

### Hierarchical embedding spaces

The challenge is maintaining geometric coherence across scales. Fine-grained embeddings (token-level) must compose into coarse-grained embeddings (entity-level) without losing the coupling structure.

Recent work on hierarchical embedding spaces (including methods for learning representations that maintain consistent geometry at multiple resolutions) suggests this is tractable. The key properties needed:

1. **Scale-consistent distance:** If two entities are close at coarse scale, their fine-grained constituents should be close on average (but not necessarily individually)
2. **Coupling preservation:** Coupling strength estimated at fine scale should aggregate consistently to coupling at coarse scale
3. **Compositional structure:** Entity-level embeddings should be reconstructible (approximately) from constituent embeddings
4. **Dynamic consistency:** Trajectories at fine scale should coarse-grain to trajectories at coarse scale (the renormalization group condition)

### Entity identification in embedding space

The core operational challenge: **how do you determine what an entity is, its state, and its coupling to other entities, all within embedding space?**

**Entity identification:**
- Cluster detection in embedding space at multiple scales
- An embedding cluster is an entity when it has coherent internal dynamics (auto-causal structure: the cluster sustains itself)
- Threshold: $\rho_{\text{ac}}(\text{cluster}) > \rho_{\text{threshold}}$ — the cluster's constituents predict each other's evolution better than external points do
- Operationalized: causal emergence criterion $\text{EI}(\text{cluster}) > \text{EI}(\text{constituents})$

**State determination:**
- The entity's state $X(t)$ is the cluster centroid (or higher moments) in embedding space at time $t$
- State change $\dot{X}$ = centroid velocity (how fast the cluster moves through embedding space)
- Internal energy = cluster dispersion (how spread out the constituents are)

**Coupling estimation:**
- Between-cluster: how much does one cluster's trajectory predict another's?
- Operationalized via transfer entropy or Granger causality between cluster centroid time series
- Asymmetry: compare $\text{TE}(X \to Y)$ vs $\text{TE}(Y \to X)$
- The coupling tensor $T^i_j$ is estimable from these directional influence measures

### Token-level to entity-level bridge

For language/text-based systems specifically:

1. **Tokens** = atomic units in embedding space
2. **Named entities** (NER) = first-order clusters (proper nouns, organizations, locations)
3. **Concept clusters** = second-order clusters (topics, themes, arguments)
4. **Domain structures** = third-order clusters (fields, disciplines, worldviews)

At each level, the entity earns its own state variable when $\text{EI}(\text{cluster}) > \text{EI}(\text{tokens})$. The prompt $P$ should track entities at the scale where this criterion is satisfied for the target prediction timescale.

Short prediction horizon $\to$ track fine-grained entities (tokens, named entities).
Long prediction horizon $\to$ track coarse-grained entities (concepts, domains).

This connects to failure mode 2 (wrong entities): prediction fails when $P$ tracks entities at the wrong scale for the target timescale.

**Status:** Architectural proposal. Hierarchical embedding methods exist. Integration with causal emergence criterion and Epimechanics entity framework is novel and untested.

---

## 7. Two-Stage Prompt Optimization

### The problem

A single prompt $P$ both **represents the world** (encodes entities, states, couplings) and **instructs the model** (determines how to use that representation for prediction). These are two distinct functions. Conflating them limits optimization.

### Two stages

**Stage 1: Optimize $P_{\text{rep}}$ (the representation prompt)**

$P_{\text{rep}}$ encodes: who are the players, what are their states, what couplings exist, at what scale. This is $X_\Gamma$ — the compressed state of the world relevant to prediction.

**Stage 2: Optimize $P_{\text{pred}}$ (the prediction prompt)**

$P_{\text{pred}}$ encodes: given this representation, how do you forecast the next state? What model structure to apply? What timescale? What outcome space?

The full system:

$$\hat{Y} = \text{LLM}(P_{\text{pred}},\; P_{\text{rep}}(D),\; X(t))$$

where $D$ is the raw data, $P_{\text{rep}}(D)$ compresses $D$ into a representation, and $P_{\text{pred}}$ operates on that representation.

**The optimization loop:**

1. $P_{\text{pred}}$ optimizes to produce accurate outputs given $P_{\text{rep}}$
2. $P_{\text{rep}}$ optimizes to produce representations that $P_{\text{pred}}$ can use effectively
3. Together they co-optimize: $P_{\text{rep}}$ changes what $P_{\text{pred}}$ sees, $P_{\text{pred}}$'s errors signal what $P_{\text{rep}}$ should change

This is the same co-primitive structure as (Computation, Representation) from Part 0 of Epimechanics: neither is definable without the other. The representation only persists relative to the model that uses it. The model only persists relative to the representation it receives.

### Prompts as representative outcomes of desires

A prompt is not neutral. It encodes what you **want to predict** — which implicitly defines what counts as an entity, what counts as a relevant coupling, and what timescale matters. The prompt is a projection of intent onto the data.

This connects to the decision/trajectory application: the reward function $r$ determines which trajectories are high-reward, and the prompt encodes that reward implicitly. Different desires (predict price vs. predict geopolitical stability vs. predict supply chain disruption) produce different optimal $P_{\text{rep}}$ for the same raw data.

### Training on specific representation levels

Can we train at a single level of the hierarchy (e.g., only entity-level, ignoring token-level)?

Yes, if the causal emergence criterion is satisfied at that level: $\text{EI}(\text{entity level}) > \text{EI}(\text{token level})$. When this holds, entity-level dynamics contain more predictive information than token-level dynamics, and training at entity level is not just cheaper — it's **more accurate**.

The representation levels:

| Level | $P_{\text{rep}}$ content | Prediction target |
|---|---|---|
| Token | Raw text, time series values | Next token / next value |
| Named entity | "These are the players: [list]" | Player state changes |
| Relationship | "Player A influences Player B via [mechanism]" | Coupling-mediated transitions |
| Regime | "The system is in [regime] with [basin structure]" | Regime transitions, basin hopping |
| Structural | "The Lagrangian of this domain is [form]" | Conservation law violations, symmetry breaks |

Training at the right level for your prediction timescale is the same as choosing the right entities (failure mode 2 from Section 3).

### The entity-outcome frame

The concrete prediction structure:

$$X = \{(\text{entity}_i, \text{state}_i, \text{coupling}_{ij})\} \quad \to \quad Y = \{\Delta\text{state}_i\}$$

$P_{\text{rep}}$ says: "These are the players. These are their current states. These are their couplings."

$Y$ is the **change in state** — not the full next state, but the residual $\Delta X_i = X_i(t{+}1) - X_i(t)$. Predicting residuals at each entity level independently is the multi-scale decomposition:

$$\Delta X = \Delta X_{\text{token}} + \Delta X_{\text{entity}} + \Delta X_{\text{regime}}$$

Each level captures dynamics at its own timescale. Token residuals are fast. Entity residuals are medium. Regime residuals are slow. A model trained on entity-level residuals ignores fast noise and slow drift, focusing on the timescale where its representation has purchase.

### Multiple outcomes and meta-prediction

Rather than predicting a single $\hat{Y}$, predict a **distribution** of outcomes $\{Y_1, Y_2, \ldots, Y_k\}$ with probabilities $\{p_1, \ldots, p_k\}$. Then:

1. Compare realized outcome $Y_{\text{actual}}$ against the predicted distribution
2. A meta-model evaluates: which $P_{\text{rep}}$ and $P_{\text{pred}}$ produced distributions closest to $Y_{\text{actual}}$?
3. The meta-model learns which prompt configurations are best for which contexts

This is exactly the perturbative hierarchy from the REP paper: fit multiple model orders, compare BIC, find optimal truncation. Applied to prompts: try multiple $P_{\text{rep}}$ compressions at different levels, evaluate which compresses best for the prediction task at hand.

---

## 8. The Non-Triviality of Minimal Representation

### The question

If $P_{\text{rep}}$ compresses the data $D$ into a representation, why not just pass all of $D$ directly? What makes compression non-trivially better than appending?

### Why appending fails

**Practical:** Context windows are finite. You cannot pass all historical data.

**But the deeper reason is structural:** Even with infinite context, raw data is not a representation. It is a recording. A recording contains everything, which means it highlights nothing. The model must still extract structure from the recording, and doing so costs computation proportional to data size.

The Representational Efficiency Principle gives the precise statement:

$$C_{\text{total}} = \underbrace{\mathcal{K}(P_{\text{rep}})}_{\text{description length}} + \underbrace{C_{\text{predict}}(P_{\text{rep}}, D)}_{\text{prediction cost}}$$

- $\mathcal{K}(P_{\text{rep}})$: bits to specify the representation (complexity of the prompt)
- $C_{\text{predict}}$: computation needed to predict from the representation

Raw data $D$ has $\mathcal{K}(D) \approx |D|$ (incompressible — description length equals data length) and $C_{\text{predict}} \sim O(|D|^2)$ for attention-based models. The total cost grows quadratically.

A good $P_{\text{rep}}$ has $\mathcal{K}(P_{\text{rep}}) \ll |D|$ and $C_{\text{predict}} \sim O(|P_{\text{rep}}|^2) \ll O(|D|^2)$. The compression **pays for itself** by reducing prediction cost more than it costs to specify.

### What makes it non-trivial

The non-trivial content of $P_{\text{rep}}$ is exactly the **structural invariants** extracted from $D$:

1. **Entity identification:** Which clusters in the data are self-sustaining? (Not in the raw data — must be discovered)
2. **Coupling estimation:** Which entities predict each other's evolution? (Requires causal analysis, not just correlation)
3. **Symmetry extraction:** What conservation laws hold? (Noether's theorem applied to discovered Lagrangian)
4. **Basin identification:** What are the stable states and transition barriers? (Requires landscape analysis)
5. **Scale selection:** At what granularity do entities have causal emergence? (Requires multi-scale comparison)

None of these are present in the raw data $D$. They are **computed from** $D$ and then encoded in $P_{\text{rep}}$. The representation is the data *after structural analysis*. That's why it's not trivial — it requires the very computation that Epimechanics formalizes.

### $X_\Gamma$ that predicts $X_{i+1}$

Define $X_\Gamma$ as the minimal sufficient representation: the shortest encoding of the data's structural content that achieves prediction accuracy within tolerance $\varepsilon$.

$$X_\Gamma = \arg\min_{P_{\text{rep}}} \mathcal{K}(P_{\text{rep}}) \quad \text{s.t.} \quad \text{loss}(\text{LLM}(P_{\text{pred}}, P_{\text{rep}}, X(t)),\; X(t{+}1)) < \varepsilon$$

This is the MDL formulation applied to prompt-based prediction. $X_\Gamma$ is not the data, and it's not a summary of the data. It is the **Lagrangian of the data** — the structural constraint that, combined with the current state, generates the dynamics.

### Summarization vs. compression vs. representation

Three distinct operations, often conflated:

| Operation | Input → Output | What's preserved | What's lost |
|---|---|---|---|
| **Summarization** | $D \to S$ | Salient events | Structural relationships, dynamics |
| **Compression** | $D \to C$ | All information (lossless) | Nothing (but not shorter in structural sense) |
| **Representation** | $D \to X_\Gamma$ | Structural invariants (entities, couplings, symmetries) | Noise, irrelevant detail, redundancy |

Summarization loses structure. Lossless compression doesn't reduce prediction cost. Only representation — extraction of structural invariants — achieves both: shorter description AND cheaper prediction.

The challenge: representation requires knowing what's structurally relevant *before* you have the representation. This is the chicken-and-egg of entity identification. The resolution is the two-stage optimization: $P_{\text{rep}}$ and $P_{\text{pred}}$ co-evolve, each providing the signal the other needs.

### The representation and the predictive model of that representation

$X_\Gamma$ and $P_{\text{pred}}$ are inseparable. A representation only persists relative to the model that uses it. A model only persists relative to the representation it receives.

The pair $(X_\Gamma, P_{\text{pred}})$ is the complete predictive system. Optimizing one while holding the other fixed is gradient descent in a saddle landscape. Optimizing both simultaneously — the two-stage loop — is the path to the jointly minimal system.

This is the Epimechanics co-primitive pair (Computation, Representation) made operational: computation produces representations, representations enable computation, neither is prior.

**Status:** This section frames the core optimization problem. The MDL formulation is standard. The connection to Epimechanics co-primitives and the two-stage architecture is novel. Operationalization requires implementing the $(P_{\text{rep}}, P_{\text{pred}})$ co-optimization loop and measuring whether jointly optimized prompts outperform static or single-stage alternatives.

---

## 9. Evolving Memory as the Real Representation

### Beyond prompts to systems

A prompt is a snapshot — a fixed representation applied at one moment. But prediction over long timescales requires **evolving memory**: accumulated structural knowledge that persists, updates, and compresses over time.

The prompt $P$ is the thin edge of a deeper object: the **system** $\mathcal{S}$ that includes:

| Component | Role | Epimechanics analogue |
|---|---|---|
| Memory $\mathcal{M}(t)$ | Accumulated structural knowledge | Generalized mass (resistance to state change; history) |
| Agents $\{A_k\}$ | Specialized predictors with different representations | Entities with different $P_{\text{rep}}$ |
| Scoring function $\sigma$ | Evaluates prediction error | Action principle $\delta\!\int\!L\,dt$ (off-shell = divergent prediction) |
| Selection mechanism | Promotes lower-loss agents/memories, demotes higher-loss | Natural selection; $\rho_{\text{ac}}$ threshold |
| Data streams $\{D_j(t)\}$ | Incoming observations | State updates $X(t)$ |

The prompt $P(t)$ is what the system **emits** at time $t$ — a compressed projection of its memory into a form usable by the prediction engine. The system is the entity; the prompt is its action.

### Memory as evolving representation

What makes memory different from a prompt:

1. **Persistence across prediction episodes.** A prompt lives for one call. Memory lives across calls, accumulating structural knowledge.

2. **Selective forgetting.** Memory must discard what no longer predicts — entities that dissolved, couplings that broke, regimes that ended. This is the compression constraint applied over time: $\mathcal{K}(\mathcal{M}(t))$ must stay bounded even as $t \to \infty$.

3. **Structural consolidation.** Short-term memory holds specific predictions and their outcomes. Long-term memory holds the *patterns* — which entity types tend to couple, what precedes regime transitions, which representation levels work for which timescales. This is the summarization → representation transition: raw prediction logs → structural invariants.

4. **Multi-scale temporal structure.** Fast-changing couplings update in short-term memory. Slowly-changing entity ontology updates in medium-term memory. Structural insights (which failure modes dominate this domain) accumulate in long-term memory.

This maps directly onto the causant hierarchy:
- Short-term memory ≈ bond-level information (specific connections, current states)
- Medium-term memory ≈ loop-level information (which auto-causal structures persist)
- Long-term memory ≈ basin-level information (landscape topology, regime structure)

### Agent teams as multi-entity prediction

Instead of a single predictor, deploy **teams of agents** — each with different:
- $P_{\text{rep}}$ (different entity ontologies, different representation scales)
- $P_{\text{pred}}$ (different prediction strategies, different timescale focus)
- $\mathcal{M}_k$ (different accumulated memory, different structural priors)

This is the super-forecaster model: diverse perspectives aggregate into better predictions than any individual. But formalized:

$$\hat{Y}_{\text{ensemble}} = \sum_k w_k(t) \cdot \hat{Y}_k$$

where $w_k(t)$ are weights updated by scoring function $\sigma$:

$$w_k(t{+}1) \propto w_k(t) \cdot \exp(-\eta \cdot \text{loss}_k(t))$$

Agents that predict well gain weight. Agents that predict poorly lose weight. Over time, the ensemble converges toward the lowest-loss representation — **but only for the timescale and entity level where each agent has purchase**.

The key insight: different agents should dominate at different timescales:
- Token-level agents dominate short-horizon prediction
- Entity-level agents dominate medium-horizon prediction
- Regime-level agents dominate long-horizon prediction

The scoring function must evaluate **per-timescale**, not aggregate, or the fast agents drown out the slow ones (because there are more short-horizon evaluation opportunities).

### Scored agent teams as entities

An agent team that sustains itself — whose predictions generate enough value to justify its compute cost — has $\rho_{\text{ac}} > 0$. It is an entity in the Epimechanics sense. Its internal couplings (how agents share information, how the meta-model allocates weight) are tighter than its external couplings (to other teams, to the data stream). It satisfies the meta-entity criterion.

Agent teams can:
- **Reproduce:** successful configurations spawn variants (mutation + selection)
- **Specialize:** different teams evolve toward different domain/timescale niches
- **Couple:** teams that predict complementary aspects can share memory
- **Die:** teams whose predictions consistently fail lose weight and are deallocated

This is biological evolution applied to prediction systems. The "organism" is the agent team. The "environment" is the data stream. "Fitness" is prediction accuracy. The structural question: does this evolutionary process converge toward Lagrangian representations?

---

## 10. The Prediction Market Gaming Problem

### Reflexivity as the central threat

Prediction markets aggregate information efficiently — **when participants cannot influence outcomes**. When they can, the market becomes a power game:

$$\hat{Y}_{\text{market}} \xrightarrow{\text{influences}} Y_{\text{actual}} \xrightarrow{\text{scores}} \hat{Y}_{\text{market}}$$

This is failure mode 6 (reflexivity) at the system level. Those who can influence outcomes have an advantage: they don't need to predict — they need to **act** and then bet on their own actions.

### The asymmetric coupling problem

Market participants with high $\Pi_{X \to Y}$ (power ratio, Section 5) over the predicted variable can:

1. **Front-run:** Take a position, then act to move the outcome toward that position
2. **Suppress information:** Prevent evidence from reaching the market that would move prices against their position
3. **Manufacture signals:** Create events that shift other participants' beliefs without changing underlying reality

In Epimechanics terms: participants with high coupling $T^Y_X$ to the outcome variable $Y$ have an information advantage that is not epistemic but **causal**. They don't know more about $Y$; they can *change* $Y$.

### What the system must do

To resist gaming, the predictive system must:

**1. Detect reflexivity.**
Measure whether prediction accuracy degrades after the system's predictions become public. If $\text{loss}(t) \sim f(\hat{Y}_{\text{public}}(t{-}1))$, reflexivity is active. This is a testable signature.

**2. Separate prediction from influence.**
Track the coupling tensor $T^i_j$ between participants and outcomes. Participants with $T^Y_k > \theta$ (high influence over outcome $Y$) should be:
- Weighted differently in the ensemble (their "predictions" are partly self-fulfilling)
- Monitored for position-action alignment (betting on outcomes they can influence)
- Used as **signals of intent** rather than signals of belief

**3. Model the game, not just the system.**
The system must include participants as entities with their own $P_{\text{rep}}$, $P_{\text{pred}}$, and $\mathcal{M}$. Their predictions are not independent observations — they are actions by coupled entities. The system models a system that includes itself.

**4. Predict the manipulation, not just the outcome.**
If participant $k$ has high $\Pi_{k \to Y}$ and takes position $Z_k$, the system should predict:
- $Y_{\text{actual}}$ given $k$'s likely actions (strategic prediction)
- $Y_{\text{counterfactual}}$ without $k$'s influence (causal prediction)
- The gap $\Delta Y_k = Y_{\text{actual}} - Y_{\text{counterfactual}}$ (manipulation magnitude)

This is Pearl's counterfactual framework applied to prediction markets: distinguish what would have happened without the intervention from what actually happened because of it.

**5. Value structural prediction over event prediction.**
Individual event predictions are gameable. Structural predictions — conservation laws, coupling topology, basin structure — are harder to game because they describe the *type* of dynamics, not the specific outcome. A system that predicts "this market has three basins of attraction with transition barriers of approximately $\Delta V$" is more robust to gaming than one that predicts "the price will be $X$ tomorrow."

### The deeper point

Prediction marketing is a domain where **the representation is part of the system it represents**. The system $\mathcal{S}$ predicts outcomes that $\mathcal{S}$'s participants can influence. This makes it a test case for the full Epimechanics apparatus:

- The system is an entity with $\rho_{\text{ac}} > 0$ (self-sustaining through prediction → scoring → update)
- Its participants are entities with asymmetric coupling to outcomes
- The system must model itself as coupled to the thing it predicts (self-coupling term)
- The reflexivity problem is the observer-coupling problem from Part 1b applied to markets

Any predictive system deployed in an adversarial environment — markets, politics, strategy — faces this problem. The evolving memory system $\mathcal{M}(t)$ must include memory of **who tried to game it and how**, which means tracking participant entities and their coupling to outcomes over time.

**Status:** Conceptual architecture. The scoring mechanism (exponential weighting of agent teams) is standard (cf. multiplicative weights, hedge algorithm). The reflexivity detection and manipulation separation are novel applications of the Epimechanics coupling tensor framework. Empirical validation requires a prediction market testbed with identifiable participant-outcome coupling.

---

## 11. Synthesis: The Complete Predictive Representation System

All ideas compose into a single architecture:

```
┌──────────────────────────────────────────────────────────────┐
│                    EVOLVING MEMORY  M(t)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │  Long-term   │  │  Medium-term │  │  Short-term          │ │
│  │  structural  │  │  entity      │  │  prediction logs,    │ │
│  │  invariants, │  │  ontology,   │  │  coupling estimates, │ │
│  │  failure     │  │  regime IDs, │  │  recent states       │ │
│  │  patterns    │  │  basin map   │  │                      │ │
│  └──────┬───────┘  └──────┬──────┘  └──────────┬───────────┘ │
└─────────┼─────────────────┼─────────────────────┼────────────┘
          └────────┬────────┘                     │
                   ▼                              │
     ┌─────────────────────────────┐              │
     │       P_meta (meta-prompt)   │              │
     │  diagnoses failure mode,     │              │
     │  prescribes minimal δP,     │              │
     │  detects reflexivity/gaming │              │
     └──────────┬──────────────────┘              │
                │ δP                              │
     ┌──────────▼──────────────────┐              │
     │  P_rep(t)  │  P_pred(t)     │              │
     │  (entities,│  (model        │              │
     │   couplings│   structure,   │              │
     │   scales)  │   timescale)   │              │
     └──────────┬──────────────────┘              │
                │                                 │
     ┌──────────▼──────────────────┐              │
     │    Agent Team {A_k}          │              │
     │  agent 1: token-level pred   │              │
     │  agent 2: entity-level pred  │              │
     │  agent 3: regime-level pred  │              │
     │  weights w_k(t) from scoring │              │
     └──────────┬──────────────────┘              │
                │ Ŷ_ensemble                      │
     ┌──────────▼──────────────────┐              │
     │    Comparison + Scoring      │              │
     │  loss per agent per timescale│──────────────┘
     │  reflexivity detection       │
     │  manipulation separation     │
     └──────────┬──────────────────┘
                │ (loss, failure mode, gaming signal)
                └──────────→ P_meta + Memory update
```

The system is self-referential at three levels:
1. **Agents evolve** via per-timescale scoring (the fastest loop)
2. **$P_{\text{rep}} + P_{\text{pred}}$ co-evolve** via failure mode diagnosis (medium loop)
3. **Memory $\mathcal{M}(t)$ evolves** via structural consolidation (the slowest loop)

The minimal system is the smallest $(\mathcal{M}, P_{\text{meta}}, \{A_k\})$ triple that maintains prediction accuracy within tolerance $\varepsilon$ across target timescales while resisting gaming.

---

## 12. Open Questions

1. **Does prompt evolution converge?** Under what conditions does $P(t)$ reach a fixed point (stable Lagrangian) versus oscillating or diverging?

2. **Is $P_{\text{meta}}$ universal?** Can the same meta-prompt diagnose failures across domains, or must it be domain-specialized?

3. **What is the optimal hierarchy depth?** How many levels of entity clustering (token → named entity → concept → domain → ...) are needed for a given prediction task?

4. **Can the power ratio $\Pi_{X \to Y}$ be estimated from observational data alone?** Or does it require interventionist experiments (and therefore cannot be learned passively)?

5. **Does the compression constraint (P must stay compressible) naturally prevent overfitting?** Or does it need to be enforced as an explicit regularization?

6. **What is the relationship between embedding space geometry and Lagrangian structure?** If the REP conjecture holds, optimal embeddings should have quadratic kinetic energy in the embedding metric. Is this testable?

7. **Can mutual state transitions $(X, Y) \to (X', Y')$ be predicted from coupling tensors alone?** Or do they require modeling the full joint potential $V(X, Y)$?

8. **Does two-stage $(P_{\text{rep}}, P_{\text{pred}})$ co-optimization outperform single-stage prompt optimization?** If so, by how much, and does the gap grow with domain complexity?

9. **What is the minimum viable $X_\Gamma$?** For a given domain and prediction tolerance $\varepsilon$, how small can the representation get before prediction degrades? Is there a phase transition (sharp drop-off) or smooth degradation?

10. **Can entity-level residual prediction $\Delta X_{\text{entity}}$ be trained independently of token-level and regime-level?** Or does cross-scale leakage require joint training?

11. **Is the summarization-compression-representation distinction empirically measurable?** Can you quantify how much predictive lift comes from structural extraction vs. data inclusion?

12. **Does agent team evolution converge toward Lagrangian representations?** If scored agent teams undergo selection, do surviving teams' $P_{\text{rep}}$ develop Lagrangian structure spontaneously?

13. **Can reflexivity be detected before deployment?** Or must the system be deployed and observed to measure self-coupling? Is there a pre-deployment test for reflexivity vulnerability?

14. **What is the optimal memory decay schedule?** How fast should short-term memory consolidate into long-term structural memory? Does the optimal rate depend on the domain's Lyapunov time?

15. **Can the gaming problem be formalized as an adversarial game between the prediction system and coupled participants?** What are the Nash equilibria? Does the system converge to a robust equilibrium or oscillate?

---

## Connection to Existing Epimechanics Work

| This note | Existing formalism | Extension |
|---|---|---|
| Prompt as Lagrangian | REP, Lagrangian as strongest structural postulate | Operationalization via LLM prompt |
| Prompt evolution | $F = \mathcal{M}\ddot{X} + \dot{\mathcal{M}}\dot{X}$ cross-term | $\dot{\mathcal{M}}$ as prompt update rate |
| Self-referential meta-optimization | $\mathbf{T}(X) \cdot X$ self-multiplication | Applied to representation enforcers, not states |
| State transitions via coupling | Potential landscape $V(X)$, basin depth $\Delta V$ | Explicit mutual transition formalism $(X,Y) \to (X',Y')$ |
| Asymmetric coupling | Coupling tensor $T^i_j$ | Power ratio $\Pi_{X \to Y} = T^Y_X / T^X_Y$ |
| Embedding over graphs | Entity boundary $\partial E$, $\rho_{\text{ac}}$ threshold | Continuous embedding operationalization |
| Timescale failure modes | Causants, near-decomposability, chaos | Systematic taxonomy of prompt failure |
| Hierarchical entities | Meta-entity emergence (Part 2) | Token → entity bridge via causal emergence criterion |
| Two-stage optimization | Co-primitive pair (Computation, Representation) | $(P_{\text{rep}}, P_{\text{pred}})$ co-optimization loop |
| Non-trivial compression | MDL, REP, Lagrangian as strongest postulate | $X_\Gamma$ = Lagrangian of data; summarization vs. representation |
| Entity-level residuals | Causants, multi-scale dynamics | $\Delta X = \Delta X_{\text{token}} + \Delta X_{\text{entity}} + \Delta X_{\text{regime}}$ |
| Prompts as desires | Decision/trajectory application, reward function | $P$ encodes intent, not just structure |
| Evolving memory | Generalized mass $\mathcal{M}$, causant hierarchy | Multi-timescale memory as bond/loop/basin knowledge |
| Agent teams | Meta-entity emergence, multiplicative agency | Scored ensemble as entity with $\rho_{\text{ac}} > 0$ |
| Prediction market gaming | Reflexivity (failure mode 6), asymmetric coupling | Coupling tensor $T^i_j$ detects manipulation; Pearl counterfactuals separate prediction from influence |
