"""
Entity-Persistent Prediction: temporal loop with entity tracking.

Pipeline: news → extract_representation → update_registry → predict → score

Usage:
  # Single tranche test (Phase A)
  python src/run_persistent.py --question-sets 2026-01-18 --n-extractors 1 --n-predictors 1

  # Multi-tranche with accumulation (Phase B)
  python src/run_persistent.py --question-sets 2025-10-26 2025-11-09 2025-12-07 2026-01-04 2026-01-18

  # Full multi-agent (Phase C)
  python src/run_persistent.py --question-sets 2025-10-26 2025-11-09 2025-12-07 2026-01-04 2026-01-18 --n-extractors 3 --n-predictors 3

  # Dry run
  python src/run_persistent.py --question-sets 2026-01-18 --dry-run
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_MODEL, RESULTS_DIR, RATE_LIMIT_DELAY
from data_loader import load_forecastbench_temporal
from entity_registry import EntityRegistry
from representation_extractor import run_extraction, apply_extraction
from prediction_agent import run_prediction_agents
from aggregator import aggregate_predictions
from run_baseline import score_prediction
from news_retriever import get_news_context, get_news_articles_raw, extract_key_terms
from prompts import EXTRACTION_FOCUSES, PREDICTION_FOCUSES


def run_persistent(
    question_sets: list[str],
    n_extractors: int = 3,
    n_predictors: int = 3,
    model: str = DEFAULT_MODEL,
    use_news: bool = True,
    limit_per_tranche: int = None,
    dry_run: bool = False,
    run_name: str = None,
    fresh_registry: bool = True,
):
    """Run the full entity-persistent prediction pipeline."""

    # Load questions by tranche
    print(f"Loading questions for tranches: {question_sets}")
    tranches = load_forecastbench_temporal(question_sets)
    total_qs = sum(len(qs) for qs in tranches.values())
    print(f"Loaded {total_qs} questions across {len(tranches)} tranches")

    # Initialize registry
    registry = EntityRegistry()
    if fresh_registry:
        registry.reset()
        print("Fresh registry initialized")
    else:
        print(f"Loaded existing registry: {registry}")

    # Select focuses based on agent count
    ext_focuses = list(EXTRACTION_FOCUSES.keys())[:n_extractors]
    pred_focuses = list(PREDICTION_FOCUSES.keys())[:n_predictors]

    all_results = []
    tranche_summaries = []

    for tranche_idx, (tranche_date, questions) in enumerate(tranches.items()):
        if limit_per_tranche:
            questions = questions[:limit_per_tranche]

        print(f"\n{'='*70}")
        print(f"TRANCHE {tranche_idx+1}/{len(tranches)}: {tranche_date} ({len(questions)} questions)")
        print(f"Registry: {registry}")
        print(f"{'='*70}")

        # ── Step 1: News Retrieval ──────────────────────────────
        news_articles = []
        if use_news and not dry_run:
            print(f"\n  Retrieving news for {tranche_date}...")
            news_articles = get_news_articles_raw(
                before_date=tranche_date,
                window_days=14,
                max_articles=20,
            )
            print(f"  Retrieved {len(news_articles)} articles")

        # ── Step 2: Representation Extraction ───────────────────
        if not dry_run and news_articles:
            print(f"\n  Extracting representations ({n_extractors} agents)...")
            extraction = run_extraction(
                news_articles=news_articles,
                registry=registry,
                tranche=tranche_date,
                model=model,
                focuses=ext_focuses,
            )
            apply_extraction(registry, extraction, tranche_date)
        elif dry_run:
            print(f"  [DRY RUN] Would extract with {n_extractors} agents")

        # ── Step 3: Predictions ─────────────────────────────────
        print(f"\n  Predicting ({len(questions)} questions, {n_predictors} agents each)...")
        tranche_results = []

        for qi, question in enumerate(questions):
            if dry_run:
                print(f"  [{qi+1}/{len(questions)}] DRY RUN: {question['question'][:70]}...")
                tranche_results.append({"question_id": question["id"], "dry_run": True})
                continue

            # Get question-specific news context
            news_context = ""
            if use_news:
                terms = extract_key_terms(question["question"])
                news_context = get_news_context(
                    question["question"],
                    freeze_date=tranche_date,
                    window_days=7,
                    max_articles=3,
                )

            # Run M prediction agents
            agent_preds = run_prediction_agents(
                question=question,
                registry=registry,
                news_context=news_context,
                model=model,
                focuses=pred_focuses,
            )

            # Aggregate
            aggregated = aggregate_predictions(agent_preds)

            # Score
            score = score_prediction(
                {"prediction": aggregated["prediction"]},
                question,
            )

            # Build result record
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tranche": tranche_date,
                "tranche_idx": tranche_idx,
                "question_id": question["id"],
                "question": question["question"],
                "source": question["source"],
                "prediction": aggregated["prediction"],
                "confidence": aggregated["confidence"],
                "method": aggregated["method"],
                "disagreement": aggregated["disagreement"],
                "reasoning": aggregated.get("reasoning", ""),
                "agent_predictions": aggregated["agent_predictions"],
                "n_entities_in_registry": len(registry.entities),
                "n_couplings_in_registry": len(registry.couplings),
                "model": model,
                "input_tokens": sum(p.get("input_tokens", 0) for p in agent_preds),
                "output_tokens": sum(p.get("output_tokens", 0) for p in agent_preds),
                **score,
            }
            tranche_results.append(result)

            if score.get("score_type") == "scored":
                print(f"  [{qi+1}/{len(questions)}] Pred={score['predicted_prob']:.2f} Actual={score['actual']:.1f} Brier={score['brier_score']:.4f} | {question['question'][:50]}...")
            else:
                print(f"  [{qi+1}/{len(questions)}] {aggregated['prediction']} | {question['question'][:50]}...")

        # ── Step 4: Tranche Summary ─────────────────────────────
        scored = [r for r in tranche_results if r.get("score_type") == "scored" and 0 <= r.get("actual", -1) <= 1]
        tranche_summary = {
            "tranche": tranche_date,
            "questions": len(questions),
            "scored": len(scored),
            "entities": len(registry.entities),
            "couplings": len(registry.couplings),
        }
        if scored:
            briers = [r["brier_score"] for r in scored]
            accs = [r["accuracy"] for r in scored]
            tranche_summary["avg_brier"] = round(sum(briers) / len(briers), 4)
            tranche_summary["avg_accuracy"] = round(sum(accs) / len(accs), 4)
            print(f"\n  Tranche {tranche_date}: Brier={tranche_summary['avg_brier']:.4f}, Acc={tranche_summary['avg_accuracy']:.1%}, Entities={tranche_summary['entities']}, Couplings={tranche_summary['couplings']}")

        tranche_summaries.append(tranche_summary)
        all_results.extend(tranche_results)

        # Snapshot registry
        if not dry_run:
            registry.snapshot(tranche_date)
            registry.save()

    # ── Save Results ────────────────────────────────────────────
    if dry_run:
        print("\n[DRY RUN] No results saved.")
        return

    rname = run_name or f"persistent_{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RESULTS_DIR / rname
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "predictions.jsonl", "w") as f:
        for r in all_results:
            f.write(json.dumps(r, default=str) + "\n")

    with open(run_dir / "tranches.json", "w") as f:
        json.dump(tranche_summaries, f, indent=2)

    # Overall summary
    all_scored = [r for r in all_results if r.get("score_type") == "scored" and 0 <= r.get("actual", -1) <= 1]
    summary = {
        "run_name": rname,
        "model": model,
        "n_extractors": n_extractors,
        "n_predictors": n_predictors,
        "tranches": len(tranches),
        "total_questions": len(all_results),
        "scored": len(all_scored),
        "final_entities": len(registry.entities),
        "final_couplings": len(registry.couplings),
        "total_input_tokens": sum(r.get("input_tokens", 0) for r in all_results),
        "total_output_tokens": sum(r.get("output_tokens", 0) for r in all_results),
    }
    if all_scored:
        briers = [r["brier_score"] for r in all_scored]
        accs = [r["accuracy"] for r in all_scored]
        summary["avg_brier"] = round(sum(briers) / len(briers), 4)
        summary["avg_accuracy"] = round(sum(accs) / len(accs), 4)

    # Cost estimate
    input_cost = summary["total_input_tokens"] / 1e6 * 0.80
    output_cost = summary["total_output_tokens"] / 1e6 * 4.00
    summary["estimated_cost_usd"] = round(input_cost + output_cost, 4)

    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*70}")
    print(f"PERSISTENT PREDICTION COMPLETE: {rname}")
    print(f"{'='*70}")
    print(f"Tranches: {len(tranches)} | Questions: {summary['total_questions']} | Scored: {summary['scored']}")
    if all_scored:
        print(f"Avg Brier: {summary['avg_brier']:.4f} | Avg Accuracy: {summary['avg_accuracy']:.1%}")
    print(f"Final Registry: {len(registry.entities)} entities, {len(registry.couplings)} couplings")
    print(f"Est Cost: ${summary['estimated_cost_usd']:.4f}")
    print(f"Results: {run_dir}/")

    # Print tranche progression
    print(f"\nTranche progression:")
    for ts in tranche_summaries:
        b = ts.get('avg_brier', '?')
        a = ts.get('avg_accuracy', '?')
        b_str = f"{b:.4f}" if isinstance(b, float) else b
        a_str = f"{a:.1%}" if isinstance(a, float) else a
        print(f"  {ts['tranche']}: Brier={b_str}, Acc={a_str}, Entities={ts['entities']}, Couplings={ts['couplings']}")


def main():
    parser = argparse.ArgumentParser(description="Entity-Persistent Prediction")
    parser.add_argument("--question-sets", nargs="+", required=True, help="Tranche dates (e.g., 2026-01-18)")
    parser.add_argument("--n-extractors", type=int, default=3)
    parser.add_argument("--n-predictors", type=int, default=3)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-news", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Max questions per tranche")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--resume", action="store_true", help="Resume with existing registry")
    args = parser.parse_args()

    run_persistent(
        question_sets=args.question_sets,
        n_extractors=args.n_extractors,
        n_predictors=args.n_predictors,
        model=args.model,
        use_news=not args.no_news,
        limit_per_tranche=args.limit,
        dry_run=args.dry_run,
        run_name=args.run_name,
        fresh_registry=not args.resume,
    )


if __name__ == "__main__":
    main()
