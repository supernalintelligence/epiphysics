"""
Phase 3: Automated prompt optimization.

Generates prompt variants, backtests against held-out data, scores and selects.
This is the two-stage (P_rep, P_pred) co-optimization from the research note.

Usage:
  # Run optimization on autocast questions (10 variants, 4 rounds)
  python run_auto_opt.py --dataset autocast --base-prompt entity_aware_v1 --rounds 4

  # Quick test with fewer variants
  python run_auto_opt.py --dataset autocast --base-prompt baseline_v1 --rounds 2 --variants 5 --limit 20
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_MODEL, SONNET_MODEL, RESULTS_DIR, RATE_LIMIT_DELAY
from data_loader import load_autocast, load_forecastbench
from prompts import ALL_PROMPTS, format_prompt
from run_baseline import call_llm, parse_prediction, score_prediction, save_results


MUTATE_PROMPT = """You are an expert at prompt engineering for prediction tasks.

Below is a prompt template used to predict outcomes of forecasting questions.
Your job: generate a VARIANT of this prompt that might predict more accurately.

Current prompt:
---
{current_prompt}
---

Performance so far:
- Average Brier score: {avg_brier} (lower = better, 0 = perfect)
- Accuracy: {accuracy}%
- Common failure pattern: {failure_pattern}

Generate a new prompt variant that addresses the failure pattern.
Keep the same output JSON format. Change the REASONING STRUCTURE — what you ask
the model to think about before predicting.

Return ONLY the new prompt template (no explanation). Use {{question}}, {{background}},
and {{choices_section}} as placeholders."""


def analyze_failures(results: list[dict]) -> str:
    """Identify the most common failure pattern from results."""
    if not results:
        return "No results yet"

    scored = [r for r in results if r.get("score_type") == "scored"]
    if not scored:
        return "No scored results"

    # Find worst predictions
    worst = sorted(scored, key=lambda r: r.get("brier_score", 0), reverse=True)[:5]

    # Categorize failures
    overconfident = sum(1 for r in worst if r.get("confidence", 50) > 80)
    wrong_direction = sum(1 for r in worst if r.get("accuracy", 1) == 0)

    if overconfident > 3:
        return "Overconfident wrong predictions — model is too certain on questions it gets wrong"
    elif wrong_direction > 3:
        return "Systematic direction errors — model predicts opposite of actual outcome"
    else:
        return "Mixed failures — some overconfidence, some direction errors"


def generate_variants(
    base_prompt: dict,
    n_variants: int,
    results: list[dict],
    model: str,
) -> list[dict]:
    """Generate prompt variants using an LLM to mutate the base prompt."""
    failure_pattern = analyze_failures(results)

    scored = [r for r in results if r.get("score_type") == "scored"]
    avg_brier = sum(r.get("brier_score", 0.25) for r in scored) / max(len(scored), 1)
    accuracy = sum(r.get("accuracy", 0) for r in scored) / max(len(scored), 1) * 100

    variants = []
    for i in range(n_variants):
        mutate_request = MUTATE_PROMPT.format(
            current_prompt=base_prompt["template"],
            avg_brier=f"{avg_brier:.4f}",
            accuracy=f"{accuracy:.1f}",
            failure_pattern=failure_pattern,
        )

        response = call_llm(mutate_request, model)
        time.sleep(RATE_LIMIT_DELAY)

        if response["error"]:
            print(f"  Variant {i+1} generation failed: {response['error'][:60]}")
            continue

        variant_template = response["text"]
        if not variant_template or "{question}" not in variant_template:
            print(f"  Variant {i+1}: invalid template (missing placeholders)")
            continue

        variants.append({
            "name": f"{base_prompt['name']}_mut{len(variants)+1}_r{len(results)//max(len(scored),1) if scored else 0}",
            "description": f"Auto-generated variant of {base_prompt['name']}",
            "template": variant_template,
        })
        print(f"  Generated variant {len(variants)}: {variants[-1]['name']}")

    return variants


def evaluate_variant(
    variant: dict,
    questions: list[dict],
    model: str,
) -> tuple[list[dict], dict]:
    """Evaluate a prompt variant on a set of questions."""
    results = []
    for q in questions:
        prompt_text = format_prompt(variant, q)
        response = call_llm(prompt_text, model)
        predicted = parse_prediction(response["text"])
        scores = score_prediction(predicted, q)

        results.append({
            "question_id": q["id"],
            "prompt_name": variant["name"],
            "model": model,
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            **predicted,
            **scores,
        })
        time.sleep(RATE_LIMIT_DELAY)

    scored = [r for r in results if r.get("score_type") == "scored"]
    summary = {
        "prompt_name": variant["name"],
        "total": len(results),
        "scored": len(scored),
        "avg_brier": sum(r["brier_score"] for r in scored) / max(len(scored), 1) if scored else None,
        "accuracy": sum(r["accuracy"] for r in scored) / max(len(scored), 1) if scored else None,
    }
    return results, summary


def run_optimization(
    questions: list[dict],
    base_prompt_name: str,
    n_rounds: int = 4,
    n_variants: int = 10,
    eval_size: int = 50,
    model: str = DEFAULT_MODEL,
    mutate_model: str = SONNET_MODEL,
):
    """Run the full optimization loop."""
    base_prompt = ALL_PROMPTS[base_prompt_name]
    best_prompt = base_prompt
    all_results = []
    round_summaries = []

    # Split questions into eval sets
    random.shuffle(questions)

    for round_num in range(n_rounds):
        print(f"\n{'='*60}")
        print(f"OPTIMIZATION ROUND {round_num + 1}/{n_rounds}")
        print(f"{'='*60}")

        # Select eval subset for this round
        eval_qs = questions[(round_num * eval_size) % len(questions):][:eval_size]
        print(f"Evaluating on {len(eval_qs)} questions")

        # Evaluate current best
        print(f"\nEvaluating current best: {best_prompt['name']}")
        best_results, best_summary = evaluate_variant(best_prompt, eval_qs, model)
        all_results.extend(best_results)
        print(f"  Brier: {best_summary['avg_brier']:.4f} | Acc: {best_summary['accuracy']:.2%}")

        # Generate variants
        print(f"\nGenerating {n_variants} variants...")
        variants = generate_variants(best_prompt, n_variants, all_results, mutate_model)

        # Evaluate each variant
        variant_summaries = [best_summary]
        for v in variants:
            print(f"\nEvaluating: {v['name']}")
            v_results, v_summary = evaluate_variant(v, eval_qs, model)
            all_results.extend(v_results)
            variant_summaries.append(v_summary)
            if v_summary["avg_brier"] is not None:
                print(f"  Brier: {v_summary['avg_brier']:.4f} | Acc: {v_summary['accuracy']:.2%}")

        # Select best
        scored_summaries = [s for s in variant_summaries if s["avg_brier"] is not None]
        if scored_summaries:
            winner = min(scored_summaries, key=lambda s: s["avg_brier"])
            if winner["prompt_name"] != best_prompt["name"]:
                # Find the winning variant
                for v in variants:
                    if v["name"] == winner["prompt_name"]:
                        best_prompt = v
                        break
                print(f"\n>>> New best: {winner['prompt_name']} (Brier: {winner['avg_brier']:.4f})")
            else:
                print(f"\n>>> Keeping: {best_prompt['name']} (Brier: {winner['avg_brier']:.4f})")

        round_summaries.append({
            "round": round_num + 1,
            "best_prompt": best_prompt["name"],
            "best_brier": winner["avg_brier"] if scored_summaries else None,
            "variants_tested": len(variants),
            "variants_scored": len(scored_summaries),
        })

    # Save final results
    run_name = f"optimization_{base_prompt_name}_{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RESULTS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "predictions.jsonl", "w") as f:
        for r in all_results:
            f.write(json.dumps(r, default=str) + "\n")

    with open(run_dir / "rounds.json", "w") as f:
        json.dump(round_summaries, f, indent=2)

    with open(run_dir / "best_prompt.txt", "w") as f:
        f.write(best_prompt["template"])

    opt_summary = {
        "run_name": run_name,
        "base_prompt": base_prompt_name,
        "rounds": n_rounds,
        "variants_per_round": n_variants,
        "eval_size": eval_size,
        "model": model,
        "mutate_model": mutate_model,
        "final_best": best_prompt["name"],
        "round_summaries": round_summaries,
        "total_predictions": len(all_results),
    }
    with open(run_dir / "summary.json", "w") as f:
        json.dump(opt_summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"OPTIMIZATION COMPLETE")
    print(f"{'='*60}")
    print(f"Best prompt: {best_prompt['name']}")
    print(f"Rounds: {json.dumps(round_summaries, indent=2)}")
    print(f"Results: {run_dir}/")

    return best_prompt, opt_summary


def main():
    parser = argparse.ArgumentParser(description="Automated Prompt Optimization")
    parser.add_argument("--dataset", choices=["autocast", "forecastbench"], default="autocast")
    parser.add_argument("--base-prompt", default="entity_aware_v1")
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--variants", type=int, default=10)
    parser.add_argument("--eval-size", type=int, default=50)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model for prediction")
    parser.add_argument("--mutate-model", default=SONNET_MODEL, help="Model for generating variants")
    parser.add_argument("--limit", type=int, default=None, help="Max total questions to use")
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--tags", nargs="+", default=None)
    args = parser.parse_args()

    if args.dataset == "autocast":
        questions = load_autocast(args.tags, args.keyword)
    else:
        questions = load_forecastbench()

    if args.limit:
        questions = questions[:args.limit]

    print(f"Loaded {len(questions)} questions")

    run_optimization(
        questions=questions,
        base_prompt_name=args.base_prompt,
        n_rounds=args.rounds,
        n_variants=args.variants,
        eval_size=args.eval_size,
        model=args.model,
        mutate_model=args.mutate_model,
    )


if __name__ == "__main__":
    main()
