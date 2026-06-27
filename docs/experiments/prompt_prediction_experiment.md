---
title: "Experiment: Prompt-Optimized News Prediction"
description: >-
  Can we optimize an LLM prompt to predict next-day/hour/week news more accurately?
  Starting with high-effective-mass entities (Trump, world leaders) where individual
  actions disproportionately move outcomes.
date: 2026-04-07T00:00:00.000Z
draft: true
author:
  name: "Ian Derrington"
authors:
  - name: "Ian Derrington"
  - name: "Parnian Barekatain"
contentType: article
series: "Epimechanics"
tags:
  - Epimechanics
  - Prediction
  - Experiment
  - Prompt optimization
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

## The Question

Given an LLM, an input prompt, and a news dataset: **can we optimize the prompt to produce more accurate predictions of the next day's / hour's / week's news?**

## Why High-Effective-Mass Entities First

Not all entities are equally predictive. A high-effective-mass entity — one whose actions disproportionately move the state of other entities — gives you more predictive signal per entity tracked.

Trump is the obvious first test case:
- Highest $\Pi_{X \to Y}$ (power ratio) of any single actor over US policy, markets, and media
- Actions are public and timestamped (tweets/posts, executive orders, speeches, rallies)
- Outcomes are measurable (market moves, policy changes, media response, polling)
- High coupling asymmetry: Trump moves markets more than markets move Trump

Other high-effective-mass entities to add in later rounds: Fed chair, major central banks, Xi Jinping, key tech CEOs, OPEC decisions.

The Epimechanics reasoning: focus compute on entities where $\mathcal{M} \cdot |\dot{X}|$ is largest — those with the most momentum. Tracking 5 high-mass entities should outpredict tracking 500 low-mass entities for the same compute budget.

## Experimental Design

### Phase 1: Baseline (no optimization)

**Setup:**
- Model: Claude Sonnet or GPT-4o (cheapest capable model)
- Dataset: RSS/API news feed (Reuters, AP, Bloomberg) — timestamped articles
- Scope: Trump-related news only (filter by entity mention)
- Prediction targets: next-day headlines, market direction (up/down/flat), policy action (yes/no/type)

**Baseline prompt (P_0):**
```
You are a news prediction system. Given the following news articles
from the past 24 hours about Donald Trump, predict:

1. The most likely headline topic tomorrow
2. S&P 500 direction (up/down/flat) 
3. Whether a new executive action will be announced (yes/no)

Rate your confidence (0-100) for each prediction.

Today's articles:
{articles}
```

**Scoring:**
- Headline topic: semantic similarity (embedding cosine) between predicted and actual top headline
- Market direction: accuracy (correct/incorrect)
- Executive action: accuracy + calibration (are 80% confidence predictions right 80% of the time?)

Run for 14 days. Log all predictions, actuals, and scores.

### Phase 2: Manual Prompt Optimization

After 14 days of baseline data, analyze failures:

- Which predictions were worst? Why?
- What information was in the articles that the prompt didn't extract?
- What entities besides Trump drove the outcomes? (Coupling structure)

Manually revise the prompt based on failure analysis. This is the human-in-the-loop version of $P_{\text{meta}}$ diagnosing failure modes.

**Example revisions:**
- Add entity tracking: "Also note actions by: [key cabinet members, congressional leaders, Fed]"
- Add state tracking: "Current market regime: [bull/bear/volatile]. Current political context: [specific]"
- Add coupling: "How might Trump's actions interact with [upcoming Fed decision / earnings season / foreign policy event]?"
- Change timescale: maybe hour-level predictions are more accurate than day-level for some targets

Run revised prompt for 14 days. Compare to baseline.

### Phase 3: Automated Prompt Optimization

Use the prediction logs from Phases 1-2 as training signal for automated prompt evolution.

**Method:**
1. Generate N prompt variants (mutate the current best prompt)
2. Score each variant against held-out historical data (backtesting)
3. Select top-K variants
4. Run top-K in parallel on live data for 3 days
5. Score against actuals
6. Best variant becomes new base; repeat

This is the agent-team approach from Section 9 of the research note, but minimal: instead of diverse agent architectures, we're just evolving the prompt while holding the model fixed.

**What to measure:**
- Does prediction accuracy improve over optimization rounds?
- Does the optimized prompt converge to stable structure or keep drifting?
- Does the optimized prompt develop entity-tracking and coupling language spontaneously?
- Does the optimal prompt differ by timescale (hour vs. day vs. week)?

### Phase 4: Multi-Entity Expansion

Once single-entity (Trump) optimization stabilizes, add entities by effective mass:

1. Trump (baseline, already optimized)
2. Trump + Fed chair
3. Trump + Fed + top 3 tech CEOs
4. Trump + Fed + tech + Xi Jinping / key foreign leaders

**The test:** Does adding each entity improve prediction proportionally to their estimated effective mass? Or is there a point of diminishing returns (too many entities, prompt too complex, representation collapses)?

This tests the core claim: high-effective-mass entities provide disproportionate predictive value.

## Data: Available Datasets for Backtesting

All datasets are cloned/downloaded to `experiments/entity-prediction/data/` (gitignored).

### Tier 1: Input + outcome already paired (backtest-ready)

**OpenForesight / forecast-news** (HuggingFace: `shash42/forecast-news`)
- 52K forecasting questions auto-generated from daily news (CCNews)
- Each has: source articles at time T, prediction question, verified answer
- Time range: 2021-2025. Ideal for backtesting prompt optimization.
- Location: `experiments/entity-prediction/data/forecast-news/`

**FNSPID** (GitHub: `Zdong104/FNSPID_Financial_News_Dataset`)
- 15.7M financial news records + 29.7M stock prices for 4,775 S&P 500 companies
- News from NASDAQ, Bloomberg, Reuters, Benzinga — already paired with next-day prices
- Time range: 1999-2023. Includes GPT-generated sentiment scores.
- Location: `experiments/entity-prediction/data/fnspid/`

**ForecastBench** (GitHub + HuggingFace: `forecastingresearch/forecastbench-datasets`)
- Binary prediction questions from real-world time series (ACLED, FRED, Yahoo Finance)
- 250 new questions biweekly. Includes superforecaster + public forecasts as baselines.
- Time range: 2024-present. Continuously updated.
- Location: `experiments/entity-prediction/data/forecastbench/` + `forecastbench-hf/`

**Autocast** (GitHub: `andyzoujm/autocast`)
- Thousands of resolved forecasting tournament questions (Metaculus, GJOpen, Polymarket)
- Comes with news corpus download scripts for context retrieval
- Time range: 2018-2023
- Location: `experiments/entity-prediction/data/autocast/`

### Tier 2: Assemble-your-own (more flexibility)

**Polymarket historical** (HuggingFace: `SII-WANGZJ/Polymarket_data`)
- 1.1B trades across 268K+ prediction markets. Heavy Trump/politics 2023-2026.
- 107GB full; 10K sample downloadable. Pair with news corpus for inputs.

**GDELT** (Google BigQuery, free tier)
- Billions of timestamped political events, 15-minute updates since 1979
- Structured: who did what to whom (CAMEO codes). No full articles.

### For live prediction (Phase 1-3)

| Data | Source | Access |
|---|---|---|
| News articles (timestamped) | NewsAPI or CC-NEWS | API key (free tier) |
| Market data (S&P 500 daily) | Yahoo Finance API | Free |
| Trump actions (posts, orders) | Truth Social RSS, Federal Register API | Free/scrape |
| Executive orders | Federal Register API | Free |

## Cost Estimate

| Component | Cost/day | 14-day phase |
|---|---|---|
| LLM calls (baseline) | ~$0.50 (1 call/day, ~4K tokens in, ~500 out) | $7 |
| LLM calls (N=10 variants, Phase 3) | ~$5/day | $70 |
| News API | Free tier or ~$0 | $0 |
| Total Phase 1-2 | | ~$14 |
| Total Phase 3 (14 days) | | ~$70 |

This is cheap enough to run immediately.

## Success Criteria

| Metric | Baseline (Phase 1) | Target (Phase 3) |
|---|---|---|
| Headline topic similarity | >0.3 cosine | >0.5 cosine |
| Market direction accuracy | >50% (better than coin flip) | >55% |
| Executive action accuracy | >60% | >70% |
| Calibration | within 20% | within 10% |

**Kill criterion:** If Phase 3 (automated optimization) does not improve over Phase 2 (manual optimization) after 4 rounds, the automated approach adds no value beyond human analysis. Stop and diagnose why.

**Strong positive signal:** If optimized prompts spontaneously develop entity-coupling language ("Trump's tariff announcement will interact with Fed's rate decision to produce...") without being explicitly told to track couplings. This would suggest the representation is discovering mechanical structure.

## What This Tests from the Theory

| Claim | How this experiment tests it |
|---|---|
| Prompt optimization improves prediction | Direct: Phase 2 vs Phase 1, Phase 3 vs Phase 2 |
| High-effective-mass entities are disproportionately predictive | Phase 4: does adding entities by $\mathcal{M}$ ordering maximize accuracy gain per entity? |
| Optimal prompts develop structural features | Observe: do optimized prompts converge toward entity-coupling-timescale structure? |
| Different timescales need different prompts | Compare hour/day/week prediction accuracy per prompt variant |
| Prompt evolution converges | Track prompt structure over optimization rounds — stable or drifting? |
| Compression beats appending | Compare: optimized short prompt vs. naive "append all articles" long prompt |

## Immediate Next Steps

1. Set up news ingestion pipeline (NewsAPI + Federal Register + Yahoo Finance)
2. Write baseline prompt and scoring functions
3. Run Phase 1 for 14 days
4. Analyze and start Phase 2

This can start today with ~2 hours of setup.
