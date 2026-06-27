"""
Question Analyzer: parse questions into structured entity graphs.

For each question, identifies:
- Visible entities (named in the question)
- Container entities (define rules/constraints)
- Hidden entities (base rates, momentum, question mechanics)
- Question type and structural couplings
- What temporal data would be needed

This is the question-guided approach: start from what we're predicting,
work backward to what entities and data we need.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_MODEL, RATE_LIMIT_DELAY
from knowledge_graph import KnowledgeGraph
from run_baseline import call_llm


QUESTION_ANALYSIS_PROMPT = """Analyze this prediction question to identify the full entity structure needed for forecasting.

Question: {question}
Background: {background}
Resolution criteria: {resolution_criteria}

Provide a JSON analysis:
{{
  "question_type": "<sports|politics|conflict|economic|scientific|meta>",

  "visible_entities": [
    {{"name": "<entity name>", "type": "<person|org|country|market|indicator|event_class>", "role": "<subject|competitor|institution>"}}
  ],

  "container_entities": [
    {{"name": "<container>", "relationship": "<league|alliance|market|jurisdiction|region>", "constraint": "<zero_sum_winner|threshold|continuous>"}}
  ],

  "hidden_entities": [
    {{"name": "<hidden factor>", "type": "<base_rate|momentum|structural_rule|sentiment|external_force>", "description": "<why this matters>", "estimated_value": "<if estimable, otherwise null>"}}
  ],

  "key_couplings": [
    {{"source": "<entity>", "target": "<entity>", "type": "<competitive|causal|temporal|structural>", "description": "<how they couple>"}}
  ],

  "temporal_data_needed": [
    "<what specific data would help predict this (e.g., current W-L record, recent event counts, polling data)>"
  ],

  "base_rate_estimate": {{
    "description": "<what base rate applies here>",
    "estimate": <0.0-1.0 or null if unknown>,
    "reasoning": "<how you estimated this>"
  }}
}}"""


def analyze_question(
    question: dict,
    kg: KnowledgeGraph,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Analyze a question to extract full entity structure.

    Returns structured analysis dict.
    """
    prompt = QUESTION_ANALYSIS_PROMPT.format(
        question=question["question"],
        background=question.get("background", "No additional background.")[:500],
        resolution_criteria=question.get("resolution_criteria", "Standard resolution.")[:300],
    )

    import anthropic
    client = anthropic.Anthropic()
    t0 = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
    except Exception as e:
        return {"error": str(e)}

    time.sleep(RATE_LIMIT_DELAY)

    # Strip markdown fences
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

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
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    return {"error": "parse_failed", "raw": text[:300]}


def populate_kg_from_analysis(kg: KnowledgeGraph, analysis: dict, tranche: str = None):
    """Add entities and couplings from question analysis into the knowledge graph."""
    if "error" in analysis:
        return

    # Add visible entities (with Wikidata lookup)
    for ve in analysis.get("visible_entities", []):
        name = ve.get("name", "")
        if name:
            eid = kg.add_entity_from_wikidata(name, entity_type=ve.get("type"), domain=analysis.get("question_type"))

    # Add container entities
    for ce in analysis.get("container_entities", []):
        name = ce.get("name", "")
        if name:
            eid = kg.add_entity_from_wikidata(name, entity_type="container")
            if eid:
                kg.update_entity_state(eid, constraint=ce.get("constraint", ""))

    # Add hidden entities (these don't go to Wikidata — they're latent)
    for he in analysis.get("hidden_entities", []):
        name = he.get("name", "")
        if name:
            import re
            eid = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            kg.add_entity(
                eid, name,
                entity_type="hidden",
                domain=analysis.get("question_type", "general"),
                summary=he.get("description", ""),
                base_rate=he.get("estimated_value"),
                hidden_type=he.get("type", "unknown"),
            )

    # Add couplings
    for kc in analysis.get("key_couplings", []):
        import re
        src = re.sub(r"[^a-z0-9]+", "_", kc.get("source", "").lower()).strip("_")
        tgt = re.sub(r"[^a-z0-9]+", "_", kc.get("target", "").lower()).strip("_")
        if src and tgt and src in kg.G and tgt in kg.G:
            kg.add_edge(
                src, tgt,
                relation=kc.get("description", "couples"),
                edge_type=kc.get("type", "direct"),
                strength=0.5,
            )

    # Store base rate estimate
    br = analysis.get("base_rate_estimate", {})
    if br and br.get("estimate") is not None:
        # Attach base rate to the question's primary visible entity
        vis = analysis.get("visible_entities", [])
        if vis:
            import re
            primary = re.sub(r"[^a-z0-9]+", "_", vis[0]["name"].lower()).strip("_")
            # Find closest match in graph
            for nid in kg.G.nodes:
                if primary in nid or nid in primary:
                    kg.update_entity_state(nid, base_rate=br["estimate"])
                    break


def analyze_and_populate(
    questions: list[dict],
    kg: KnowledgeGraph,
    model: str = DEFAULT_MODEL,
    limit: int = None,
) -> list[dict]:
    """Analyze multiple questions and populate the knowledge graph.

    Returns list of analysis dicts.
    """
    analyses = []
    qs = questions[:limit] if limit else questions

    for i, q in enumerate(qs):
        print(f"  [{i+1}/{len(qs)}] Analyzing: {q['question'][:60]}...")
        analysis = analyze_question(q, kg, model)

        if "error" not in analysis:
            populate_kg_from_analysis(kg, analysis)
            n_vis = len(analysis.get("visible_entities", []))
            n_hid = len(analysis.get("hidden_entities", []))
            n_coup = len(analysis.get("key_couplings", []))
            br = analysis.get("base_rate_estimate", {}).get("estimate")
            print(f"           → {n_vis} visible, {n_hid} hidden, {n_coup} couplings, base_rate={br}")
        else:
            print(f"           → ERROR: {analysis.get('error', '?')[:60]}")

        analyses.append(analysis)

    return analyses


if __name__ == "__main__":
    from data_loader import load_forecastbench

    kg = KnowledgeGraph(Path("/tmp/qa_test_kg.json"))
    kg.reset()

    questions = load_forecastbench(question_set="2026-01-18")[:5]
    analyses = analyze_and_populate(questions, kg, limit=5)

    kg.save()
    print(f"\n{kg}")

    # Show a sample analysis
    for a in analyses[:2]:
        if "error" not in a:
            print(f"\nQuestion type: {a.get('question_type')}")
            print(f"Visible: {[e['name'] for e in a.get('visible_entities', [])]}")
            print(f"Hidden: {[e['name'] for e in a.get('hidden_entities', [])]}")
            print(f"Base rate: {a.get('base_rate_estimate', {})}")
