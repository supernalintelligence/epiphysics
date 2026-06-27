"""
Knowledge Graph Prediction: question-guided entity extraction → prediction.

Pipeline:
1. Analyze questions → extract visible + hidden entities + base rates
2. Populate knowledge graph (with Wikidata hierarchy)
3. Get news context targeted at identified entities
4. Predict using entity graph state + base rates + news

Usage:
  python src/run_kg_predict.py --question-set 2026-01-18 --limit 20
  python src/run_kg_predict.py --question-set 2026-01-18 --limit 5 --dry-run
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_MODEL, RESULTS_DIR, RATE_LIMIT_DELAY
from data_loader import load_forecastbench
from knowledge_graph import KnowledgeGraph
from question_analyzer import analyze_question, populate_kg_from_analysis
from news_retriever import get_news_context, extract_key_terms
from run_baseline import call_llm, score_prediction

KG_PREDICT_PROMPT = """You are a calibrated forecasting system with access to a structured entity analysis and recent news.

Question: {question}

=== ENTITY ANALYSIS ===
Question type: {question_type}

Visible entities and their graph context:
{entity_context}

Hidden factors:
{hidden_factors}

Base rate estimate: {base_rate} — {base_rate_reasoning}

Key couplings:
{couplings}

Temporal data needed (not all may be available):
{temporal_needs}

=== RECENT NEWS ===
{news_context}

=== INSTRUCTIONS ===
1. Start from the BASE RATE ({base_rate}) as your prior
2. Adjust up or down based on entity states, couplings, and news
3. For questions about rare events in stable regions: check if the baseline count is near zero — if 10x of near-zero, any occurrence resolves YES
4. Do NOT default to low probabilities — calibrate carefully against the base rate
5. If the question involves competition (sports division, election), consider ALL competitors, not just the named one

Respond with ONLY JSON:
{{
  "prediction": <number 0.0-1.0>,
  "confidence": <0-100>,
  "base_rate_used": <the base rate you started from>,
  "adjustment": "<what moved you away from base rate and why>",
  "reasoning": "<1-2 sentence final reasoning>"
}}"""


def predict_with_kg(
    question: dict,
    analysis: dict,
    kg: KnowledgeGraph,
    model: str = DEFAULT_MODEL,
    use_news: bool = True,
) -> dict:
    """Make a prediction using the full entity graph analysis."""
    if "error" in analysis:
        # Fallback to simple prediction
        return {"prediction": 0.5, "confidence": 20, "reasoning": "Analysis failed", "parse_error": analysis.get("error")}

    # Build entity context from graph
    visible = analysis.get("visible_entities", [])
    entity_ids = []
    import re
    for ve in visible:
        eid = re.sub(r"[^a-z0-9]+", "_", ve["name"].lower()).strip("_")
        # Find closest match in graph
        for nid in kg.G.nodes:
            if eid in nid or nid in eid:
                entity_ids.append(nid)
                break

    entity_context = kg.get_entity_context(entity_ids[:8]) if entity_ids else "No entities matched in graph."

    # Format hidden factors
    hidden = analysis.get("hidden_entities", [])
    hidden_text = "\n".join(f"- [{h.get('type', '?')}] {h['name']}: {h.get('description', '')}" for h in hidden) or "None identified."

    # Format couplings
    couplings = analysis.get("key_couplings", [])
    coupling_text = "\n".join(f"- {c['source']} → {c['target']} ({c['type']}): {c.get('description', '')}" for c in couplings) or "None identified."

    # Base rate
    br = analysis.get("base_rate_estimate", {})
    base_rate = br.get("estimate", "unknown")
    base_rate_reasoning = br.get("reasoning", "No estimate available.")[:200]

    # Temporal needs
    temporal = analysis.get("temporal_data_needed", [])
    temporal_text = "\n".join(f"- {t}" for t in temporal) or "None specified."

    # News
    news_context = "No news retrieved."
    if use_news:
        news_context = get_news_context(question["question"], freeze_date=question.get("close_time", "2026-01-18")[:10])

    prompt = KG_PREDICT_PROMPT.format(
        question=question["question"],
        question_type=analysis.get("question_type", "unknown"),
        entity_context=entity_context,
        hidden_factors=hidden_text,
        base_rate=base_rate,
        base_rate_reasoning=base_rate_reasoning,
        couplings=coupling_text,
        temporal_needs=temporal_text,
        news_context=news_context,
    )

    import anthropic
    client = anthropic.Anthropic()
    t0 = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
    except Exception as e:
        return {"prediction": None, "parse_error": str(e), "input_tokens": 0, "output_tokens": 0}

    time.sleep(RATE_LIMIT_DELAY)

    # Parse
    if "```" in text:
        text = text.split("```json", 1)[-1].split("```", 1)[0] if "```json" in text else text.split("```", 1)[1].split("```", 1)[0]

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
            parsed = json.loads(text[start:end])
            parsed["input_tokens"] = input_tokens
            parsed["output_tokens"] = output_tokens
            parsed["latency_s"] = round(time.time() - t0, 2)
            parsed["parse_error"] = None
            return parsed
    except json.JSONDecodeError:
        pass

    # Regex fallback
    import re
    m = re.search(r'"prediction"\s*:\s*([\d.]+)', text)
    if m:
        return {"prediction": float(m.group(1)), "confidence": None, "reasoning": text[:200],
                "parse_error": "regex_fallback", "input_tokens": input_tokens, "output_tokens": output_tokens}

    return {"prediction": None, "parse_error": "json_parse_failed", "input_tokens": input_tokens, "output_tokens": output_tokens}


def run_kg_experiment(
    question_set: str = "2026-01-18",
    model: str = DEFAULT_MODEL,
    limit: int = None,
    use_news: bool = True,
    dry_run: bool = False,
    run_name: str = None,
):
    """Run the full knowledge-graph-based prediction pipeline."""
    questions = load_forecastbench(question_set=question_set)
    if limit:
        questions = questions[:limit]
    print(f"Loaded {len(questions)} questions from {question_set}")

    kg = KnowledgeGraph()
    kg.reset()

    results = []

    # Phase 1: Analyze all questions and build KG
    print(f"\n{'='*70}")
    print(f"PHASE 1: Question Analysis + KG Construction")
    print(f"{'='*70}")

    analyses = {}
    for i, q in enumerate(questions):
        if dry_run:
            print(f"  [{i+1}/{len(questions)}] DRY RUN: {q['question'][:60]}...")
            analyses[q["id"]] = {"dry_run": True}
            continue

        print(f"  [{i+1}/{len(questions)}] {q['question'][:60]}...")
        analysis = analyze_question(q, kg, model)
        if "error" not in analysis:
            populate_kg_from_analysis(kg, analysis)
            analyses[q["id"]] = analysis
            n_vis = len(analysis.get("visible_entities", []))
            n_hid = len(analysis.get("hidden_entities", []))
            br = analysis.get("base_rate_estimate", {}).get("estimate")
            print(f"           → {n_vis}v + {n_hid}h entities, base_rate={br}")
        else:
            analyses[q["id"]] = analysis
            print(f"           → ERROR")

    kg.save()
    print(f"\nKG built: {kg}")

    if dry_run:
        print("[DRY RUN] Stopping before predictions.")
        return

    # Phase 2: Predict using KG
    print(f"\n{'='*70}")
    print(f"PHASE 2: KG-Based Prediction")
    print(f"{'='*70}")

    for i, q in enumerate(questions):
        analysis = analyses.get(q["id"], {})
        prediction = predict_with_kg(q, analysis, kg, model, use_news)

        score = score_prediction(
            {"prediction": prediction.get("prediction")},
            q,
        )

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question_id": q["id"],
            "question": q["question"],
            "source": q["source"],
            "question_type": analysis.get("question_type"),
            "prediction": prediction.get("prediction"),
            "confidence": prediction.get("confidence"),
            "base_rate_used": prediction.get("base_rate_used"),
            "adjustment": prediction.get("adjustment"),
            "reasoning": prediction.get("reasoning"),
            "parse_error": prediction.get("parse_error"),
            "model": model,
            "input_tokens": prediction.get("input_tokens", 0),
            "output_tokens": prediction.get("output_tokens", 0),
            "n_visible": len(analysis.get("visible_entities", [])),
            "n_hidden": len(analysis.get("hidden_entities", [])),
            "kg_nodes": kg.G.number_of_nodes(),
            "kg_edges": kg.G.number_of_edges(),
            **score,
        }
        results.append(result)

        if score.get("score_type") == "scored":
            br = prediction.get("base_rate_used", "?")
            print(f"  [{i+1}/{len(questions)}] Pred={score['predicted_prob']:.2f} (base={br}) Actual={score['actual']:.1f} Brier={score['brier_score']:.4f} | {q['question'][:45]}...")
        else:
            print(f"  [{i+1}/{len(questions)}] {prediction.get('prediction')} | {q['question'][:45]}...")

    # Save results
    rname = run_name or f"kg_predict_{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RESULTS_DIR / rname
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "predictions.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")

    all_scored = [r for r in results if r.get("score_type") == "scored" and 0 <= r.get("actual", -1) <= 1]
    summary = {
        "run_name": rname,
        "model": model,
        "questions": len(results),
        "scored": len(all_scored),
        "kg_nodes": kg.G.number_of_nodes(),
        "kg_edges": kg.G.number_of_edges(),
        "total_input_tokens": sum(r.get("input_tokens", 0) for r in results),
        "total_output_tokens": sum(r.get("output_tokens", 0) for r in results),
    }
    if all_scored:
        briers = [r["brier_score"] for r in all_scored]
        accs = [r["accuracy"] for r in all_scored]
        summary["avg_brier"] = round(sum(briers) / len(briers), 4)
        summary["avg_accuracy"] = round(sum(accs) / len(accs), 4)

    input_cost = summary["total_input_tokens"] / 1e6 * 0.80
    output_cost = summary["total_output_tokens"] / 1e6 * 4.00
    summary["estimated_cost_usd"] = round(input_cost + output_cost, 4)

    with open(run_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*70}")
    print(f"RESULTS: {rname}")
    print(f"{'='*70}")
    print(f"Questions: {summary['questions']} | Scored: {summary['scored']}")
    if all_scored:
        print(f"Avg Brier: {summary['avg_brier']:.4f} | Avg Accuracy: {summary['avg_accuracy']:.1%}")
    print(f"KG: {summary['kg_nodes']} entities, {summary['kg_edges']} edges")
    print(f"Cost: ${summary['estimated_cost_usd']:.4f}")
    print(f"Results: {run_dir}/")


def main():
    parser = argparse.ArgumentParser(description="KG-based Prediction")
    parser.add_argument("--question-set", default="2026-01-18")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-news", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    run_kg_experiment(
        question_set=args.question_set,
        model=args.model,
        limit=args.limit,
        use_news=not args.no_news,
        dry_run=args.dry_run,
        run_name=args.run_name,
    )


if __name__ == "__main__":
    main()
