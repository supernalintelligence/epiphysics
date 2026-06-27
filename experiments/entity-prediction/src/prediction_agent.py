"""
Prediction Agent: makes forecasts using pre-loaded entity state.

Key difference from the single-shot entity_aware prompt: entity states
are loaded from the persistent registry, not identified from scratch.
Multiple agents with different focuses evaluate independently.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_MODEL, RATE_LIMIT_DELAY
from entity_registry import EntityRegistry
from prompts import PERSISTENT_PREDICTION_PROMPT, PREDICTION_FOCUSES
from run_baseline import call_llm, parse_prediction


def make_prediction(
    question: dict,
    registry: EntityRegistry,
    news_context: str = "",
    model: str = DEFAULT_MODEL,
    focus: str = "entity_dynamics",
) -> dict:
    """Make a prediction using entity registry state.

    Args:
        question: normalized question dict
        registry: entity registry with current state
        news_context: formatted news string
        model: LLM model
        focus: one of PREDICTION_FOCUSES keys

    Returns:
        parsed prediction dict
    """
    # Find relevant entities from registry
    relevant = registry.get_relevant_entities(question["question"])
    entity_ids = [e["id"] for e in relevant]

    # Also check background for entity mentions
    bg_relevant = registry.get_relevant_entities(question.get("background", ""))
    for e in bg_relevant:
        if e["id"] not in entity_ids:
            entity_ids.append(e["id"])

    entity_context = registry.get_entity_context(entity_ids[:10]) if entity_ids else "No tracked entities match this question."

    focus_text = PREDICTION_FOCUSES.get(focus, PREDICTION_FOCUSES["entity_dynamics"])

    prompt = PERSISTENT_PREDICTION_PROMPT.format(
        question=question["question"],
        background=question.get("background", "No additional background."),
        entity_context=entity_context,
        news_context=news_context or "No recent news available.",
        focus=focus_text,
    )

    response = call_llm(prompt, model)
    time.sleep(RATE_LIMIT_DELAY)

    if response["error"]:
        return {
            "prediction": None,
            "confidence": None,
            "reasoning": None,
            "parse_error": response["error"],
            "focus": focus,
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "latency_s": response["latency_s"],
        }

    parsed = parse_prediction(response["text"])
    parsed["focus"] = focus
    parsed["input_tokens"] = response["input_tokens"]
    parsed["output_tokens"] = response["output_tokens"]
    parsed["latency_s"] = response["latency_s"]
    parsed["n_entities_matched"] = len(entity_ids)
    return parsed


def run_prediction_agents(
    question: dict,
    registry: EntityRegistry,
    news_context: str = "",
    model: str = DEFAULT_MODEL,
    focuses: list[str] = None,
) -> list[dict]:
    """Run M independent prediction agents on a question.

    Returns list of prediction dicts, one per agent.
    """
    if focuses is None:
        focuses = list(PREDICTION_FOCUSES.keys())

    predictions = []
    for focus in focuses:
        pred = make_prediction(question, registry, news_context, model, focus)
        predictions.append(pred)

    return predictions
