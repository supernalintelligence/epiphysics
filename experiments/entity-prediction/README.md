# Entity Prediction Experiments

Prompt-optimized prediction of entity state changes using LLMs. Tests the Epimechanics
claim that high-effective-mass entities provide disproportionate predictive value, and
that prompt optimization (representation optimization) improves prediction accuracy.

## Quick Start

```bash
cd experiments/entity-prediction

# Install dependencies
pip install -r requirements.txt

# Set API key (one of these)
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...

# Dry run (no API calls, verify setup)
python src/run_baseline.py --dataset autocast --prompt baseline_v1 --limit 10 --dry-run

# Run baseline on Trump-related questions (cheapest test: ~$0.02)
python src/run_baseline.py --dataset autocast --keyword trump --prompt baseline_v1 --limit 10

# Run baseline on ForecastBench questions
python src/run_baseline.py --dataset forecastbench --prompt baseline_v1 --limit 20

# Compare all 3 prompts on 50 questions
python src/run_baseline.py --dataset autocast --prompt all --limit 50

# Use OpenAI instead
python src/run_baseline.py --dataset autocast --prompt baseline_v1 --model gpt-4o-mini --limit 10
```

## Directory Structure

```
entity-prediction/
├── data/                              # Datasets (gitignored — large)
│   ├── autocast/                      # 1,364 forecasting tournament Qs
│   ├── fnspid/                        # Financial news + stock prices (sample)
│   ├── forecastbench/                 # ForecastBench code + fetch scripts
│   └── forecastbench-datasets-full/   # 19,684 Qs + 97,800 resolutions
├── src/
│   ├── config.py                      # Paths, model settings, rate limits
│   ├── data_loader.py                 # Load & normalize datasets
│   ├── prompts.py                     # Versioned prompt templates
│   ├── run_baseline.py                # Phase 1: baseline experiment runner
│   └── download_hf_data.py            # Download HuggingFace datasets
├── results/                           # Experiment outputs (JSONL + summary JSON)
├── requirements.txt
└── README.md
```

## Datasets

| Dataset | Questions | Resolved | Domain | Status |
|---------|-----------|----------|--------|--------|
| Autocast | 1,364 | competition set (no resolutions in file) | Geopolitical, business, health | Ready |
| ForecastBench | 19,684 | 97,800 | Multi-domain (ACLED, FRED, markets) | Ready |
| FNSPID | N/A (news articles) | stock prices as outcomes | Financial news | Sample only |

## Experiment Phases

### Phase 1: Baseline (current)
Run three prompt variants against the datasets and measure prediction accuracy.

| Prompt | Strategy | What it tests |
|--------|----------|---------------|
| `baseline_v1` | Direct question answering | Raw LLM prediction ability |
| `entity_aware_v1` | Identify entities + couplings first | Does entity identification improve prediction? |
| `structural_v1` | Basin analysis + regime identification | Does structural reasoning improve prediction? |

### Phase 2: Manual Optimization
Analyze Phase 1 failures, revise prompts by hand based on failure mode taxonomy.

### Phase 3: Automated Optimization
Generate prompt variants, backtest against held-out data, score and select.

### Phase 4: Multi-Entity Expansion
Add entities by effective mass ordering, test whether M-ordering maximizes prediction gain.

## Compute Estimates

| Phase | Questions | Est. Input Tokens | Est. Output Tokens | Cost (Haiku) | Cost (Sonnet) | Runtime |
|-------|-----------|-------------------|--------------------|--------------|--------------:|---------|
| 1a: Autocast baseline | 1,364 | 382K | 273K | $0.05 | $5.24 | ~68 min |
| 1b: ForecastBench baseline | 998 | 196K | 200K | $0.03 | $3.58 | ~50 min |
| 3: Auto optimization (10 variants x 200 Qs x 4 rounds) | 8,000 | 3.4M | 1.6M | $0.26 | $34.32 | ~6.7 hrs |
| **Total** | | | | **$0.34** | **$43.14** | |

Start with Haiku for rapid iteration, upgrade to Sonnet for final comparison.

## Scoring

- **Brier Score**: $(p - a)^2$ where $p$ = predicted probability, $a$ = actual outcome. Lower = better. 0 = perfect.
- **Log Score**: $\log(p)$ if outcome = 1, $\log(1-p)$ if outcome = 0. Higher = better. Penalizes confident wrong answers.
- **Accuracy**: Binary correct/incorrect (predicted > 0.5 matches actual > 0.5).

## Results Format

Each run produces:
- `results/<run_name>/predictions.jsonl` — one record per question with full tracking
- `results/<run_name>/summary.json` — aggregate metrics, token counts, cost estimate

Record schema:
```json
{
  "timestamp": "2026-04-07T...",
  "question_id": "G1411",
  "question": "Before 1 July 2021...",
  "source": "autocast",
  "prompt_name": "baseline_v1",
  "model": "claude-haiku-4-5-20251001",
  "input_tokens": 230,
  "output_tokens": 85,
  "latency_s": 1.4,
  "prediction": 0.75,
  "confidence": 80,
  "reasoning": "...",
  "brier_score": 0.0625,
  "accuracy": 1
}
```

## Connection to Epimechanics

See [docs/experiments/prompt_prediction_experiment.md](../../docs/experiments/prompt_prediction_experiment.md)
for the full experimental design and theory connection.

See [docs/research/predictive_representation_dynamics.md](../../docs/research/predictive_representation_dynamics.md)
for the research note developing prompt-as-Lagrangian, evolving memory, and the gaming problem.

### What This Tests

| Claim | How this experiment tests it |
|-------|------------------------------|
| Prompt optimization improves prediction | Phase 2 vs Phase 1, Phase 3 vs Phase 2 |
| Entity identification improves prediction | `entity_aware_v1` vs `baseline_v1` |
| Structural reasoning improves prediction | `structural_v1` vs `baseline_v1` |
| High-effective-mass entities are disproportionately predictive | Phase 4 multi-entity expansion |
| Compression beats appending | Optimized short prompt vs naive long prompt |
