"""
Phase 1: Baseline experiment runner.

Runs prediction prompts against datasets, scores results, and logs everything
to JSONL for analysis and prompt optimization.

Usage:
  # Run baseline on autocast (all questions)
  python run_baseline.py --dataset autocast --prompt baseline_v1

  # Run on Trump-related questions only
  python run_baseline.py --dataset autocast --keyword trump --prompt baseline_v1

  # Run on forecastbench with entity-aware prompt
  python run_baseline.py --dataset forecastbench --prompt entity_aware_v1

  # Compare all prompts on a subset
  python run_baseline.py --dataset autocast --prompt all --limit 50

  # Dry run (no API calls, just show what would be run)
  python run_baseline.py --dataset autocast --prompt baseline_v1 --dry-run
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_MODEL, RESULTS_DIR, RATE_LIMIT_DELAY, MAX_RETRIES, TIMEOUT_SECONDS
from data_loader import load_autocast, load_forecastbench
from prompts import ALL_PROMPTS, format_prompt


def call_llm(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """Call LLM API. Supports Claude (anthropic) and OpenAI (openai) models."""
    t0 = time.time()

    try:
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            return _call_openai(prompt, model, t0)
        else:
            return _call_anthropic(prompt, model, t0)
    except Exception as e:
        return {
            "text": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_s": round(time.time() - t0, 2),
            "model": model,
            "error": str(e),
        }


def _call_anthropic(prompt: str, model: str, t0: float) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=500,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return {
        "text": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_s": round(time.time() - t0, 2),
        "model": model,
        "error": None,
    }


def _call_openai(prompt: str, model: str, t0: float) -> dict:
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        max_tokens=500,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    choice = response.choices[0]
    return {
        "text": choice.message.content,
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
        "latency_s": round(time.time() - t0, 2),
        "model": model,
        "error": None,
    }


def parse_prediction(text: str) -> dict:
    """Extract prediction from LLM response text."""
    if text is None:
        return {"prediction": None, "confidence": None, "reasoning": None, "parse_error": "no response"}

    # Try to find JSON in response — handle nested braces by finding outermost pair
    try:
        start = text.find("{")
        if start >= 0:
            depth = 0
            end = start
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            raw = text[start:end]
            parsed = json.loads(raw)
            return {
                "prediction": parsed.get("prediction"),
                "confidence": parsed.get("confidence"),
                "reasoning": parsed.get("reasoning"),
                "entities": parsed.get("entities"),
                "highest_influence": parsed.get("highest_influence"),
                "regime": parsed.get("regime"),
                "basins": parsed.get("basins"),
                "parse_error": None,
            }
    except json.JSONDecodeError:
        pass

    # Fallback: try to extract a probability from the text
    import re
    prob_match = re.search(r'"prediction"\s*:\s*([\d.]+)', text)
    if prob_match:
        return {
            "prediction": float(prob_match.group(1)),
            "confidence": None,
            "reasoning": text[:200],
            "parse_error": "regex_fallback",
        }

    return {"prediction": None, "confidence": None, "reasoning": text[:200], "parse_error": "json_parse_failed"}


def score_prediction(predicted: dict, question: dict) -> dict:
    """Score a prediction against ground truth (resolution or freeze_value)."""
    pred = predicted.get("prediction")
    actual = question.get("resolution") or question.get("freeze_value")

    if pred is None or actual is None:
        return {"score": None, "score_type": "unscored", "detail": "missing prediction or resolution"}

    # Normalize prediction to float
    if isinstance(pred, str):
        pred = {"yes": 1.0, "no": 0.0}.get(pred.lower(), None)
    if pred is None:
        return {"score": None, "score_type": "unscored", "detail": "unparseable prediction"}

    pred = float(pred)
    actual = float(actual)

    # Brier score (lower is better, 0 = perfect)
    brier = (pred - actual) ** 2

    # Log score (higher is better, penalizes confident wrong answers)
    import math
    eps = 1e-6
    if actual > 0.5:
        log_score = math.log(max(pred, eps))
    else:
        log_score = math.log(max(1 - pred, eps))

    # Binary accuracy (for binary questions)
    pred_binary = 1 if pred > 0.5 else 0
    actual_binary = 1 if actual > 0.5 else 0
    accuracy = 1 if pred_binary == actual_binary else 0

    return {
        "brier_score": round(brier, 4),
        "log_score": round(log_score, 4),
        "accuracy": accuracy,
        "predicted_prob": round(pred, 4),
        "actual": actual,
        "score_type": "scored",
    }


def run_experiment(
    questions: list[dict],
    prompt_config: dict,
    model: str = DEFAULT_MODEL,
    limit: int = None,
    dry_run: bool = False,
    use_news: bool = False,
) -> list[dict]:
    """Run predictions on a set of questions."""
    if limit:
        questions = questions[:limit]

    news_retriever = None
    if use_news:
        from news_retriever import get_news_context
        news_retriever = get_news_context

    results = []
    total = len(questions)

    for i, q in enumerate(questions):
        # Retrieve news context if enabled
        news_context = None
        if news_retriever:
            freeze_date = q.get("publish_time", q.get("close_time", "2026-01-18"))
            if freeze_date:
                freeze_date = freeze_date[:10]
            news_context = news_retriever(q["question"], freeze_date=freeze_date)

        prompt_text = format_prompt(prompt_config, q, news_context=news_context)

        if dry_run:
            print(f"[{i+1}/{total}] DRY RUN: {q['question'][:80]}...")
            print(f"  Prompt length: ~{len(prompt_text)//4} tokens")
            results.append({"question_id": q["id"], "dry_run": True})
            continue

        print(f"[{i+1}/{total}] {q['question'][:80]}...")

        # Call LLM with retries
        response = None
        for attempt in range(MAX_RETRIES):
            response = call_llm(prompt_text, model)
            if response["error"] is None:
                break
            print(f"  Retry {attempt+1}/{MAX_RETRIES}: {response['error'][:80]}")
            time.sleep(2 ** attempt)

        # Parse and score
        predicted = parse_prediction(response["text"])
        scores = score_prediction(predicted, q)

        # Build result record
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question_id": q["id"],
            "question": q["question"],
            "source": q["source"],
            "tags": q.get("tags", []),
            "prompt_name": prompt_config["name"],
            "model": model,
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "latency_s": response["latency_s"],
            "error": response["error"],
            **predicted,
            **scores,
        }
        results.append(result)

        if scores.get("score_type") == "scored":
            print(f"  Pred: {scores['predicted_prob']:.2f} | Actual: {scores['actual']} | Brier: {scores['brier_score']:.4f} | Acc: {scores['accuracy']}")
        else:
            print(f"  Pred: {predicted.get('prediction')} | {scores.get('detail', 'unscored')}")

        time.sleep(RATE_LIMIT_DELAY)

    return results


def save_results(results: list[dict], run_name: str):
    """Save results to JSONL + summary JSON."""
    run_dir = RESULTS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # JSONL (one record per prediction)
    with open(run_dir / "predictions.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")

    # Summary stats
    scored = [r for r in results if r.get("score_type") == "scored"]
    errors = [r for r in results if r.get("error")]

    summary = {
        "run_name": run_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(results),
        "scored": len(scored),
        "errors": len(errors),
        "total_input_tokens": sum(r.get("input_tokens", 0) for r in results),
        "total_output_tokens": sum(r.get("output_tokens", 0) for r in results),
        "total_latency_s": sum(r.get("latency_s", 0) for r in results),
    }

    if scored:
        briers = [r["brier_score"] for r in scored]
        accuracies = [r["accuracy"] for r in scored]
        summary["avg_brier_score"] = round(sum(briers) / len(briers), 4)
        summary["avg_accuracy"] = round(sum(accuracies) / len(accuracies), 4)
        summary["min_brier"] = min(briers)
        summary["max_brier"] = max(briers)

    # Estimate cost (Claude Haiku pricing)
    input_cost = summary["total_input_tokens"] / 1e6 * 0.80
    output_cost = summary["total_output_tokens"] / 1e6 * 4.00
    summary["estimated_cost_usd"] = round(input_cost + output_cost, 4)

    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT RESULTS: {run_name}")
    print(f"{'='*60}")
    print(f"Questions: {summary['total_questions']} | Scored: {summary['scored']} | Errors: {summary['errors']}")
    if scored:
        print(f"Avg Brier Score: {summary['avg_brier_score']:.4f} (lower=better, 0=perfect)")
        print(f"Avg Accuracy:    {summary['avg_accuracy']:.2%}")
    print(f"Tokens: {summary['total_input_tokens']:,} in / {summary['total_output_tokens']:,} out")
    print(f"Est Cost: ${summary['estimated_cost_usd']:.4f}")
    print(f"Results: {run_dir}/")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Entity Prediction Baseline Experiment")
    parser.add_argument("--dataset", choices=["autocast", "forecastbench", "both"], default="forecastbench")
    parser.add_argument("--prompt", default="baseline_v1", help="Prompt name or 'all'")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None, help="Max questions to run")
    parser.add_argument("--keyword", default=None, help="Filter questions by keyword")
    parser.add_argument("--tags", nargs="+", default=None, help="Filter by tags (autocast only)")
    parser.add_argument("--fb-set", default="2024-07-21", help="ForecastBench question set date")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--use-news", action="store_true", help="Include retrieved news articles as context")
    parser.add_argument("--run-name", default=None, help="Custom run name")
    args = parser.parse_args()

    # Load data
    questions = []
    if args.dataset in ("autocast", "both"):
        questions.extend(load_autocast(tags_filter=args.tags, keyword_filter=args.keyword))
    if args.dataset in ("forecastbench", "both"):
        questions.extend(load_forecastbench(question_set=args.fb_set))

    if not questions:
        print("No questions loaded. Check dataset selection and filters.")
        return

    print(f"Loaded {len(questions)} questions from {args.dataset}")

    # Select prompts
    if args.prompt == "all":
        prompts_to_run = list(ALL_PROMPTS.values())
    else:
        if args.prompt not in ALL_PROMPTS:
            print(f"Unknown prompt: {args.prompt}. Available: {list(ALL_PROMPTS.keys())}")
            return
        prompts_to_run = [ALL_PROMPTS[args.prompt]]

    # Run each prompt
    for prompt_config in prompts_to_run:
        run_name = f"{args.run_name}_{prompt_config['name']}" if args.run_name else f"{args.dataset}_{prompt_config['name']}_{args.model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print(f"\n{'='*60}")
        print(f"Running: {prompt_config['name']} on {len(questions)} questions")
        print(f"Model: {args.model} | Limit: {args.limit or 'all'}")
        print(f"{'='*60}\n")

        results = run_experiment(
            questions=questions,
            prompt_config=prompt_config,
            model=args.model,
            limit=args.limit,
            dry_run=args.dry_run,
            use_news=args.use_news,
        )

        if not args.dry_run:
            save_results(results, run_name)


if __name__ == "__main__":
    main()
