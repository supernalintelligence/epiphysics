"""
Representation Extractor: news → structured entity state updates.

The core innovation: instead of X → summarize → predict,
we do X → summarize+extract_representation → predict.

Multiple independent agents process news with different focus areas
(political, economic, conflict), then their extractions merge into
the entity registry.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_MODEL, RATE_LIMIT_DELAY
from entity_registry import EntityRegistry, _slugify
from prompts import EXTRACTION_PROMPT, EXTRACTION_FOCUSES
from run_baseline import call_llm


def extract_representations(
    news_articles: list[dict],
    registry: EntityRegistry,
    tranche: str,
    model: str = DEFAULT_MODEL,
    focus: str = "political",
) -> dict:
    """Extract structured entity updates from news articles.

    Args:
        news_articles: list of {title, date, source, description, content}
        registry: current entity registry (for context)
        tranche: date string for this extraction
        model: LLM model to use
        focus: one of EXTRACTION_FOCUSES keys

    Returns:
        dict with entity_updates, new_entities, coupling_evidence
    """
    # Format news for the prompt
    news_text = ""
    for i, a in enumerate(news_articles[:10], 1):  # Limit to 10 articles
        news_text += f"\n[{i}] {a.get('title', 'Untitled')} ({a.get('source', '?')}, {a.get('date', '?')})\n"
        if a.get("description"):
            news_text += f"    {a['description'][:200]}\n"
        if a.get("content"):
            news_text += f"    {a['content'][:300]}\n"

    if not news_text.strip():
        return {"entity_updates": [], "new_entities": [], "coupling_evidence": []}

    # Get current entity context for the prompt
    entity_ids = list(registry.entities.keys())[:20]  # Top 20 entities
    entity_context = registry.get_entity_context(entity_ids) if entity_ids else "No entities tracked yet."

    focus_text = EXTRACTION_FOCUSES.get(focus, EXTRACTION_FOCUSES["political"])

    prompt = EXTRACTION_PROMPT.format(
        entity_context=entity_context,
        news_articles=news_text,
        focus=focus_text,
    )

    # Use higher max_tokens for extraction (structured output is longer)
    import anthropic
    client = anthropic.Anthropic()
    t0 = time.time()
    try:
        api_response = client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        response = {
            "text": api_response.content[0].text,
            "input_tokens": api_response.usage.input_tokens,
            "output_tokens": api_response.usage.output_tokens,
            "latency_s": round(time.time() - t0, 2),
            "model": model,
            "error": None,
        }
    except Exception as e:
        response = {"text": None, "error": str(e), "input_tokens": 0, "output_tokens": 0, "latency_s": 0}
    time.sleep(RATE_LIMIT_DELAY)

    if response["error"]:
        print(f"  Extraction error ({focus}): {response['error'][:80]}")
        return {"entity_updates": [], "new_entities": [], "coupling_evidence": []}

    # Parse JSON response — strip markdown fences if present
    text = response["text"] or ""
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
            parsed = json.loads(text[start:end])
            return {
                "entity_updates": parsed.get("entity_updates", []),
                "new_entities": parsed.get("new_entities", []),
                "coupling_evidence": parsed.get("coupling_evidence", []),
            }
    except json.JSONDecodeError:
        pass

    print(f"  Extraction parse failed ({focus})")
    return {"entity_updates": [], "new_entities": [], "coupling_evidence": []}


def run_extraction(
    news_articles: list[dict],
    registry: EntityRegistry,
    tranche: str,
    model: str = DEFAULT_MODEL,
    focuses: list[str] = None,
) -> dict:
    """Run N independent extraction agents and merge results.

    Args:
        news_articles: all articles for this tranche
        registry: current entity registry
        tranche: date string
        model: LLM model
        focuses: list of focus areas (default: all three)

    Returns:
        merged extraction result
    """
    if focuses is None:
        focuses = list(EXTRACTION_FOCUSES.keys())

    all_updates = []
    all_new = []
    all_couplings = []

    for focus in focuses:
        print(f"  Extracting ({focus})...")
        result = extract_representations(news_articles, registry, tranche, model, focus)
        all_updates.extend(result["entity_updates"])
        all_new.extend(result["new_entities"])
        all_couplings.extend(result["coupling_evidence"])

    return {
        "entity_updates": all_updates,
        "new_entities": all_new,
        "coupling_evidence": all_couplings,
    }


def apply_extraction(registry: EntityRegistry, extraction: dict, tranche: str):
    """Apply extraction results to the entity registry.

    Merges entity updates, adds new entities, updates couplings.
    Handles duplicates from multiple agents by averaging.
    """
    # 1. Add new entities
    for ne in extraction["new_entities"]:
        name = ne.get("canonical_name", "")
        if not name:
            continue
        registry.add_entity(
            canonical_name=name,
            entity_type=ne.get("type", "concept"),
            domain=ne.get("domain", "general"),
            aliases=ne.get("aliases", []),
            state=ne.get("initial_state", {}),
            tranche=tranche,
        )

    # 2. Apply entity updates (aggregate by entity ID)
    updates_by_id = {}
    for eu in extraction["entity_updates"]:
        eid = eu.get("id") or _slugify(eu.get("canonical_name", ""))
        if not eid:
            continue
        if eid not in updates_by_id:
            updates_by_id[eid] = []
        updates_by_id[eid].append(eu)

    for eid, updates in updates_by_id.items():
        # If entity doesn't exist, create it from the update
        if not registry.get_entity(eid):
            u = updates[0]
            registry.add_entity(
                canonical_name=u.get("canonical_name", eid),
                entity_type="concept",
                domain="general",
                state={
                    "trajectory": u.get("trajectory", "unknown"),
                    "activity_level": u.get("activity_level", 0.5),
                    "key_attributes": u.get("key_attributes", {}),
                    "summary": u.get("summary", ""),
                },
                tranche=tranche,
            )
        else:
            # Average activity levels from multiple agents
            avg_activity = sum(u.get("activity_level", 0.5) for u in updates) / len(updates)
            # Take the most recent/detailed summary
            best_summary = max(updates, key=lambda u: len(u.get("summary", "")))

            merged_attrs = {}
            for u in updates:
                merged_attrs.update(u.get("key_attributes", {}))

            registry.update_entity(eid, {
                "trajectory": best_summary.get("trajectory", "unknown"),
                "activity_level": round(avg_activity, 2),
                "key_attributes": merged_attrs,
                "summary": best_summary.get("summary", ""),
            }, tranche=tranche)

    # 3. Apply coupling evidence
    for ce in extraction["coupling_evidence"]:
        src = ce.get("source", "")
        tgt = ce.get("target", "")
        if not src or not tgt:
            continue
        registry.update_coupling(
            source=src,
            target=tgt,
            strength=ce.get("strength", 0.5),
            asymmetry=ce.get("asymmetry", 0.0),
            coupling_type=ce.get("type", "influence"),
            domains=ce.get("domains", []),
            evidence=ce.get("evidence", ""),
            tranche=tranche,
        )

    n_updates = len(updates_by_id)
    n_new = len(extraction["new_entities"])
    n_couplings = len(extraction["coupling_evidence"])
    print(f"  Applied: {n_updates} entity updates, {n_new} new entities, {n_couplings} couplings")
