"""
Proper evaluation with:
- ALL resolved questions (not first-50)
- Trivial baselines (always-0.5, always-base-rate, freeze-value)
- Stratified by source and outcome (YES vs NO)
- Normalized Brier: score relative to "always predict base rate"
- Paired comparison on identical questions

Usage:
  python src/run_proper_eval.py --question-set 2026-01-18 --prompt epimech --limit 286
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config  # loads .env
from data_loader import load_forecastbench

import anthropic

PROMPTS = {
    "baseline": """You are a forecasting system. Answer this prediction question.

Question: {question}
Background: {background}

Provide your answer as JSON:
{{"prediction": <probability 0.0-1.0>, "confidence": <0-100>, "reasoning": "<1-2 sentences>"}}""",

    "epimech": """You are a forecasting system. Reason about entities and their couplings.

Question: {question}
Background: {background}

Framework:
1. ENTITIES: What entities are involved?
2. STATES: What is each entity's current state? If unknown, say so.
3. COUPLINGS: How do entities influence each other?
4. UNCERTAINTY: How much do you actually know? Low info = stay near 0.5.

CRITICAL: Do NOT default to low probabilities when you lack information. Unknown = near 0.5.

Respond ONLY JSON:
{{"prediction": <0.0-1.0>, "uncertainty_level": "<high/medium/low>", "reasoning": "<1-2 sentences>"}}""",
}


def run_eval(
    question_set: str = "2026-01-18",
    prompt_name: str = "epimech",
    model: str = "claude-haiku-4-5-20251001",
    limit: int = None,
    run_name: str = None,
):
    questions = load_forecastbench(question_set=question_set)
    if limit:
        questions = questions[:limit]

    n = len(questions)
    print(f"Loaded {n} questions from {question_set}")

    yes = sum(1 for q in questions if q["resolution"] > 0.5)
    no = n - yes
    base_rate = yes / n
    print(f"YES: {yes} ({base_rate:.1%}) | NO: {no} ({1-base_rate:.1%})")

    client = anthropic.Anthropic()
    prompt_template = PROMPTS[prompt_name]

    results = []
    for i, q in enumerate(questions):
        prompt = prompt_template.format(
            question=q["question"][:300],
            background=q.get("background", "")[:300],
        )

        try:
            response = client.messages.create(
                model=model, max_tokens=500, temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
        except Exception as e:
            print(f"[{i+1}] ERROR: {e}")
            continue

        # Parse
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]

        pred = None
        try:
            s = text.find("{")
            if s >= 0:
                d = 0; e = s
                for j in range(s, len(text)):
                    if text[j] == "{": d += 1
                    elif text[j] == "}":
                        d -= 1
                        if d == 0: e = j+1; break
                parsed = json.loads(text[s:e])
                pred = parsed.get("prediction")
        except:
            import re
            m = re.search(r'"prediction"\s*:\s*([\d.]+)', text)
            if m: pred = float(m.group(1))

        actual = q["resolution"]
        if pred is not None and actual is not None:
            brier = (pred - actual) ** 2
            acc = 1 if (pred > 0.5) == (actual > 0.5) else 0
        else:
            brier = acc = None

        src = q["source"].replace("forecastbench:", "")
        outcome = "YES" if actual > 0.5 else "NO"
        freeze = q.get("freeze_value")

        results.append({
            "question_id": q["id"],
            "question": q["question"][:100],
            "source": src,
            "outcome": outcome,
            "actual": actual,
            "prediction": pred,
            "freeze_value": freeze,
            "brier": brier,
            "accuracy": acc,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        })

        if brier is not None:
            print(f"[{i+1:>3}/{n}] P={pred:.2f} A={actual:.0f} B={brier:.3f} | {src:<12} {outcome} | {q['question'][:45]}")

        time.sleep(0.3)

    # ── Analysis ──────────────────────────────────────────────
    scored = [r for r in results if r["brier"] is not None]
    ns = len(scored)

    print(f"\n{'='*75}")
    print(f"PROPER EVALUATION: {prompt_name} on {question_set} (N={ns})")
    print(f"{'='*75}")

    # Overall
    avg_b = sum(r["brier"] for r in scored) / ns
    avg_a = sum(r["accuracy"] for r in scored) / ns
    se_b = (sum((r["brier"]-avg_b)**2 for r in scored)/(ns-1))**0.5 / ns**0.5

    # Trivial baselines
    actuals = [r["actual"] for r in scored]
    base_rate = sum(1 for a in actuals if a > 0.5) / ns
    b_half = sum((0.5 - a)**2 for a in actuals) / ns
    b_base = sum((base_rate - a)**2 for a in actuals) / ns
    b_zero = sum((0.0 - a)**2 for a in actuals) / ns

    # Freeze value baseline (skip non-probability freeze values)
    with_freeze = [r for r in scored if r["freeze_value"] is not None and 0 <= r["freeze_value"] <= 1]
    if with_freeze:
        b_freeze = sum((r["freeze_value"] - r["actual"])**2 for r in with_freeze) / len(with_freeze)
        a_freeze = sum(1 for r in with_freeze if (r["freeze_value"] > 0.5) == (r["actual"] > 0.5)) / len(with_freeze)

    # Normalized Brier: 1 - (model_brier / baseline_brier). >0 = better than baseline
    norm_vs_half = 1 - avg_b / b_half if b_half > 0 else 0
    norm_vs_base = 1 - avg_b / b_base if b_base > 0 else 0

    print(f"\n--- BASELINES ---")
    print(f"{'Method':<35} | {'Brier':>8} | {'Acc':>8} | {'vs base rate':>12}")
    print("-" * 75)
    print(f"{'Always 0.5':<35} | {b_half:>8.4f} | {'50.0%':>8} | {1-b_half/b_base:>+11.1%}")
    print(f"{'Always base rate ({base_rate:.2f})':<35} | {b_base:>8.4f} | {'N/A':>8} | {'(baseline)':>12}")
    print(f"{'Always 0 (always no)':<35} | {b_zero:>8.4f} | {1-base_rate:>7.1%} | {1-b_zero/b_base:>+11.1%}")
    if with_freeze:
        print(f"{'Freeze value (crowd, N={len(with_freeze)})':<35} | {b_freeze:>8.4f} | {a_freeze:>7.1%} | {1-b_freeze/b_base:>+11.1%}")
    print(f"{'OUR MODEL (' + prompt_name + ')':<35} | {avg_b:>8.4f} | {avg_a:>7.1%} | {norm_vs_base:>+11.1%}")

    # Stratified by outcome
    yes_scored = [r for r in scored if r["outcome"] == "YES"]
    no_scored = [r for r in scored if r["outcome"] == "NO"]

    print(f"\n--- STRATIFIED BY OUTCOME ---")
    print(f"{'Subset':<20} | {'N':>4} | {'Model Brier':>11} | {'Base Brier':>10} | {'Norm':>8} | {'Model Acc':>9}")
    print("-" * 75)
    for label, group in [("YES outcomes", yes_scored), ("NO outcomes", no_scored), ("ALL", scored)]:
        if not group: continue
        gb = sum(r["brier"] for r in group) / len(group)
        ga = sum(r["accuracy"] for r in group) / len(group)
        # Base rate Brier for this subset
        g_base = sum((base_rate - r["actual"])**2 for r in group) / len(group)
        gnorm = 1 - gb/g_base if g_base > 0 else 0
        print(f"{label:<20} | {len(group):>4} | {gb:>11.4f} | {g_base:>10.4f} | {gnorm:>+7.1%} | {ga:>8.1%}")

    # By source
    by_src = {}
    for r in scored: by_src.setdefault(r["source"], []).append(r)
    print(f"\n--- BY SOURCE ---")
    print(f"{'Source':<15} | {'N':>4} | {'YES%':>5} | {'Model B':>8} | {'Base B':>8} | {'Norm':>8} | {'Acc':>6}")
    print("-" * 75)
    for src, g in sorted(by_src.items(), key=lambda x: len(x[1]), reverse=True):
        gb = sum(r["brier"] for r in g) / len(g)
        ga = sum(r["accuracy"] for r in g) / len(g)
        g_yes = sum(1 for r in g if r["outcome"] == "YES") / len(g)
        g_base = sum((base_rate - r["actual"])**2 for r in g) / len(g)
        gnorm = 1 - gb/g_base if g_base > 0 else 0
        print(f"{src:<15} | {len(g):>4} | {g_yes:>4.0%} | {gb:>8.4f} | {g_base:>8.4f} | {gnorm:>+7.1%} | {ga:>5.1%}")

    # Save
    rname = run_name or f"eval_{prompt_name}_{question_set}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    from config import RESULTS_DIR
    run_dir = RESULTS_DIR / rname
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "predictions.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")

    with open(run_dir / "summary.json", "w") as f:
        json.dump({
            "run_name": rname, "prompt": prompt_name, "model": model,
            "question_set": question_set, "n": ns,
            "base_rate": round(base_rate, 4),
            "brier": round(avg_b, 4), "accuracy": round(avg_a, 4),
            "brier_se": round(se_b, 4),
            "norm_vs_base_rate": round(norm_vs_base, 4),
            "baseline_always_half": round(b_half, 4),
            "baseline_base_rate": round(b_base, 4),
            "baseline_always_no": round(b_zero, 4),
            "baseline_freeze": round(b_freeze, 4) if with_freeze else None,
        }, f, indent=2)

    print(f"\nSaved to {run_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-set", default="2026-01-18")
    parser.add_argument("--prompt", default="epimech", choices=list(PROMPTS.keys()))
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()
    run_eval(args.question_set, args.prompt, args.model, args.limit, args.run_name)
