# Entity Prediction Experiment Log

## Experiment 1: 3-Prompt Comparison (2026-04-07)

### Design
- **Dataset:** ForecastBench (2024-07-21 question set)
- **N:** 15 questions (same 15 for all prompts)
- **Model:** Claude Haiku 4.5
- **Scoring:** Brier score against market freeze value (crowd prediction at freeze time). Note: freeze_value is the prediction market probability, not binary ground truth. Brier here measures distance from crowd consensus, not from resolved outcome.
- **Ground truth caveat:** We're scoring against market consensus, not final resolution. A model that disagrees with the market and is right would score poorly here. This is a limitation — proper scoring needs resolved outcomes.

### Prompts

**baseline_v1**: Direct question answering
```
You are a forecasting system. Answer the following prediction question.
[question + background]
Provide your answer as JSON: {prediction, confidence, reasoning}
```

**entity_aware_v1**: Identify entities and couplings first
```
Before answering, identify:
1. KEY ENTITIES: Who are the main actors/forces?
2. EFFECTIVE MASS: Which entity has the most influence?
3. CURRENT STATE: What is each entity's trajectory?
4. COUPLINGS: How do they influence each other?
Then predict.
```

**structural_v1**: Basin analysis and regime identification
```
Analyze this as a dynamical system:
1. REGIME: stable/transitioning/chaotic?
2. BASINS: What are the likely stable outcomes?
3. BARRIERS: What would cause transitions?
4. TIMESCALE: Question timescale vs system timescale?
5. KEY FORCES: What pushes toward each basin?
Then predict.
```

### Results

| Prompt | N | Avg Brier | SE | 95% CI | Accuracy | Acc SE | Cost |
|--------|---|-----------|------|--------|----------|--------|------|
| baseline_v1 | 15 | 0.0733 | 0.0286 | [0.017, 0.129] | 66.7% | 12.2% | $0.010 |
| entity_aware_v1 | 15 | 0.0853 | 0.0335 | [0.020, 0.151] | 66.7% | 12.2% | $0.014 |
| structural_v1 | 15 | **0.0504** | 0.0164 | [0.018, 0.083] | 66.7% | 12.2% | $0.014 |

### Statistical tests

**Paired t-test (baseline vs structural):**
- Mean diff: 0.0229 (baseline worse by this much)
- t = 1.56, N = 15
- **NOT significant at p<0.05** (need t > 2.14 for df=14)

**Power analysis:**
- To detect a Brier difference of 0.02 at 80% power, α=0.05: **need N ≥ 62 per prompt**
- At N=15, we can only detect differences > ~0.06 with 80% power

### Interpretation

1. **Accuracy is identical (10/15) across all three prompts.** All three get the same questions right/wrong in terms of direction (>0.5 vs <0.5). This means the extra reasoning doesn't change WHICH questions are answerable, at least at this N.

2. **Brier score differs because of calibration, not direction.** Structural prompt produces probabilities closer to the crowd consensus. Example: US basketball gold medal — baseline says 0.68, structural says 0.78, crowd says 0.88. Both "correct" on direction, but structural is better calibrated.

3. **N=15 is too small for significance.** The Brier SE ranges overlap substantially. We cannot distinguish the prompts with confidence at this sample size. Need N≥100 for a meaningful test (power analysis: to detect a Brier difference of 0.02 at 80% power with α=0.05, need ~100 questions per prompt).

4. **Entity-aware slightly worse than baseline** — possibly because the extra entity identification step introduces noise at Haiku quality, or the entities identified aren't the right ones for these questions.

### Next steps from Experiment 1
- [x] Run at N=100+ — done, see Experiment 2
- [x] Score against actual resolutions — done, see Experiment 3
- [ ] Run on Sonnet to test if entity-aware improves with smarter model
- [ ] Add per-question-type analysis (sports vs politics vs economics)

---

## Experiment 2: N=100 on Contaminated Data (2026-04-07)

Ran all 3 prompts on 100 ForecastBench questions from the 2024-07-21 set.

**INVALIDATED** — see Experiment 3. The 2024-07-21 question set closes within Haiku's training window. Results reflect memorization, not prediction.

| Prompt | N | Brier (clean) | Accuracy |
|---|---|---|---|
| baseline_v1 | 96 | 0.115 | 71.9% |
| entity_aware_v1 | 96 | 0.117 | 70.8% |
| structural_v1 | 96 | 0.105 | 74.0% |

---

## Experiment 3: Clean Post-Training Data (2026-04-07)

### Design change
**Critical issue identified:** All prior experiments used questions from 2024, well within model training data (Haiku cutoff ~early 2025). Results were contaminated by memorization.

**Fix:** Switched to 2026-01-18 question set. Questions close Jan-Feb 2026 — definitively outside any model's training window. Scored against **actual resolved outcomes** (binary 0/1), not market freeze values.

### Setup
- **Dataset:** ForecastBench 2026-01-18 question set
- **N:** 76 common questions with valid 0-1 resolutions
- **Model:** Claude Haiku 4.5
- **Scoring:** Brier score against resolved binary outcome

### Results

| Prompt | N | Avg Brier | SE | 95% CI | Accuracy | Acc SE |
|--------|---|-----------|------|--------|----------|--------|
| entity_aware_v1 | 76 | **0.2468** | 0.0376 | [0.173, 0.321] | 61.8% | 5.6% |
| structural_v1 | 76 | 0.2537 | 0.0378 | [0.180, 0.328] | **63.2%** | 5.5% |
| baseline_v1 | 76 | 0.2584 | 0.0398 | [0.180, 0.337] | 60.5% | 5.6% |

### Statistical tests
- baseline vs entity_aware: diff=+0.012, t=1.68, p=0.094 — trending but **not significant**
- baseline vs structural: diff=+0.005, t=0.59, p=0.553 — **not significant**
- entity_aware vs structural: diff=-0.007, t=-1.15, p=0.251 — **not significant**

### Contamination effect measured

| Metric | Contaminated (2024) | Clean (2026) | Change |
|--------|--------------------:|-------------:|-------:|
| Accuracy | 71.9% | 60.5% | **-11.4 pp** |
| Brier | 0.115 | 0.258 | **+0.143 (2.2x worse)** |

### Interpretation

1. **Contamination inflated accuracy by ~11 percentage points.** On genuinely unseen questions, Haiku baseline is 60.5% — only 10.5pp above random chance.

2. **On clean data, entity-aware and structural prompts show slight advantages** (reversed from contaminated results where entity-aware was worst). Entity-aware has the best Brier; structural has the best accuracy. Neither is statistically significant at N=76.

3. **The signal-to-noise ratio is low.** Haiku on bare question text (no current news context) may not have enough information or reasoning capacity to differentiate between prompt strategies. The real test requires either:
   - A more capable model (Sonnet/Opus)
   - Providing current news context with the questions
   - Larger N for statistical power (~300+ per prompt based on observed effect sizes)

### Key lesson
**Always verify that evaluation data postdates model training.** LLM prediction benchmarks on historical data measure recall, not forecasting ability.

---

## Experiment 4: With News Context + Systematic Failure Analysis (2026-04-07)

### Design
- **Dataset:** ForecastBench 2026-01-18 (clean, post-training)
- **N:** 67 resolved questions with valid 0-1 outcomes
- **Model:** Claude Haiku 4.5
- **News context:** 5 keyword-retrieved articles from 7-day window before freeze date (53.8M article corpus)

### Results

| Prompt | Brier | Accuracy | Tokens in |
|--------|-------|----------|-----------|
| **entity_aware + news** | **0.243** | **68.7%** | 73K |
| baseline + news | 0.254 | 67.2% | 64K |
| structural + news | 0.258 | 65.7% | ~73K |

Significant: entity_aware vs structural, p=0.035.

News vs no-news (baseline): not significant (p=0.55), only +0.5pp accuracy.

### Systematic failure analysis

#### The ACLED problem dominates everything

| Source | N | Accuracy | Brier |
|--------|---|----------|-------|
| Polymarket | 36 | **86%** | **0.068** |
| ACLED | 29 | 45% | 0.476 |
| Metaculus | 1 | 100% | 0.040 |

**ACLED questions account for 43% of our dataset but drive nearly all the error.** These are "Will there be more than ten times as many [event type] in [country]?" questions about conflict events. The model systematically predicts low probability for these (stable countries won't have violence spikes), but the actual resolution is 1.0 — because the baseline periods often have zero events, so even 1 event = "more than ten times."

The model is correct on the *reasoning* (stable countries don't suddenly have mass violence) but wrong on the *question mechanics* (10x of zero is still zero, so any events at all resolve YES).

On **Polymarket questions only**, the model achieves **86% accuracy and 0.068 Brier** — genuinely strong performance.

#### Base rate exploitation

| Strategy | Brier | Accuracy |
|----------|-------|----------|
| Always predict base rate (0.36) | **0.215** | N/A |
| Always predict "no" | 0.353 | 64.2% |
| Our entity_aware model | 0.243 | 68.7% |

**The model's 0.243 Brier is WORSE than always predicting the base rate (0.215).** This means the model is adding noise relative to a trivial strategy on this question mix. However, this is driven by ACLED — on Polymarket questions, the model substantially outperforms base rate.

#### What the entity identification actually produced

- 100% of questions got entities identified (good parse rate)
- Top entities: OpenAI, Anthropic, Google, xAI, Meta (AI questions), economic conditions, civilian populations (ACLED)
- Entities are generic category labels, NOT specific actors with tracked states and couplings
- No coupling estimation between entities
- No temporal tracking — each question is independent

#### Confidence calibration is inverted

| Confidence | N | Accuracy | Brier |
|------------|---|----------|-------|
| Low (<50) | 42 | 69.0% | 0.233 |
| Mid (50-79) | 17 | 64.7% | 0.272 |
| High (>=80) | 8 | 75.0% | 0.234 |

The model is *most accurate when least confident*. This suggests the model's confidence signal is uncorrelated with actual difficulty — it's not measuring uncertainty well.

#### Model prediction bias

- Actual outcomes: 36% yes, 64% no
- Model predictions: 10% yes, 90% no
- **The model is massively biased toward predicting "no"** — only 10% of predictions are >0.5. It's too conservative.

### What this experiment does NOT do (but should)

1. **No entity persistence.** Each question is independent. The system does not track entities across questions or over time.
2. **No coupling estimation.** The prompt asks "how do entities influence each other?" but the answer is discarded — never used for the next prediction.
3. **No prompt evolution.** Same static prompt for all 67 questions. No learning from errors.
4. **No temporal state tracking.** Entities identified in Q1 are not carried to Q2.
5. **No representation compression.** The news context is keyword-matched, not structurally compressed.

These are exactly the features described in the research note (Sections 7-10) that have NOT been implemented yet. The current experiment tests only the simplest version: does asking for entities in a single-shot prompt help? Answer: slightly, on appropriate question types.

### Why only ~67% accuracy

Three factors compound:

1. **ACLED question mechanics** (biggest factor): 43% of questions have a trick base rate (10x of zero = any nonzero). Model reasons correctly but gets the question wrong. Removing ACLED → 86% accuracy.

2. **No actual news retrieval**: Keyword matching pulls mostly irrelevant articles. The model is still mostly reasoning from the question text alone, which is ~60% (question phrasing bias).

3. **Conservative prediction bias**: Model predicts <0.5 for 90% of questions but actual rate is 64% no. It's directionally right but too extreme, adding Brier cost.

---

## Experiment 5: KG-Guided Prediction with Base Rates (2026-04-07)

### Design
- **Dataset:** ForecastBench 2026-01-18 (clean, post-training)
- **N:** 48 scored (of 50 attempted)
- **Model:** Claude Haiku 4.5
- **Method:** Two-phase pipeline:
  - Phase 1: Analyze each question → extract visible + hidden entities + base rates → populate knowledge graph (networkx + Wikidata hierarchy)
  - Phase 2: Predict using KG entity context + base rate anchoring + news

### KG Statistics
- 432 entities (visible + container + hidden)
- 95 edges (hierarchical containment + couplings)
- Wikidata-backed hierarchy (e.g., Pistons → Central Division → NBA → US)
- Hidden entities include: base rates, momentum, structural rules, question mechanics

### Results

| Method | N | Brier | Accuracy |
|--------|---|-------|----------|
| baseline (no news) | 76 | 0.258 | 60.5% |
| baseline + news | 67 | 0.254 | 67.2% |
| entity_aware + news | 67 | 0.243 | 68.7% |
| structural + news | 67 | 0.258 | 65.7% |
| **KG-guided + base rates** | **48** | **0.136** | **81.2%** |

By source:

| Source | N | Brier | Accuracy |
|--------|---|-------|----------|
| Polymarket | 36 | 0.083 | 88.9% |
| ACLED | 10 | 0.349 | 50.0% |

Base rate impact:

| Condition | N | Brier | Accuracy |
|-----------|---|-------|----------|
| With base rate | 43 | 0.125 | 81.4% |
| Without base rate | 5 | 0.228 | 80.0% |

### What drove the improvement

1. **Base rate anchoring** — predictions start from estimated base rates instead of LLM vibes. Questions with base rates got 0.125 Brier vs 0.228 without.
2. **Hidden entity surfacing** — structural rules, momentum, question mechanics identified before prediction.
3. **Entity hierarchy** — Wikidata containment (team ⊂ division ⊂ league) provides competitive context automatically.

### Caveats

1. **Not directly comparable** — N=48 vs N=67 for prior experiments, not same question subset, can't do paired test.
2. **Temporal integrity** — KG was built from question analysis (not news-first). Questions guide CONSTRUCTION, not just LOOKUP. See FRAMEWORK.md for the correct architecture.
3. **ACLED still near chance** — 50% accuracy (up from 45%) but base rate surfacing alone doesn't solve the missing temporal data problem (actual event counts needed).
4. **Cost** — 2 LLM calls per question (analysis + prediction) = 2x cost of single-shot.

### Next steps
- [ ] Refactor to build KG from news first (temporal integrity)
- [ ] Run on same N=67 questions as prior experiments for paired comparison
- [ ] Add temporal data APIs (sports standings, event counts) for entity state
- [ ] Run on Sonnet for quality comparison
- [ ] Multi-tranche test with proper temporal walls
