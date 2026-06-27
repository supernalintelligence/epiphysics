"""
Aggregator: combine multiple independent predictions into one.

Implements confidence-weighted averaging with optional extremization
to address the systematic "predict no" bias observed in experiments.
"""


def aggregate_predictions(predictions: list[dict]) -> dict:
    """Combine M independent predictions into a final prediction.

    Strategy:
    1. Filter to valid predictions
    2. Confidence-weighted mean
    3. If agents agree (low variance), extremize away from 0.5
    4. Log disagreement as uncertainty signal

    Returns:
        dict with prediction, confidence, method, agent_details
    """
    valid = [p for p in predictions if p.get("prediction") is not None]

    if not valid:
        return {
            "prediction": 0.5,
            "confidence": 0,
            "method": "fallback_no_valid",
            "agent_predictions": [],
            "disagreement": None,
        }

    if len(valid) == 1:
        p = valid[0]
        return {
            "prediction": p["prediction"],
            "confidence": p.get("confidence") or 50,
            "method": "single_agent",
            "agent_predictions": [{"focus": p.get("focus"), "prediction": p["prediction"]}],
            "disagreement": 0.0,
        }

    # Confidence-weighted mean
    preds = [p["prediction"] for p in valid]
    confs = [max(p.get("confidence") or 50, 1) for p in valid]
    total_conf = sum(confs)

    weighted_mean = sum(p * c for p, c in zip(preds, confs)) / total_conf
    simple_mean = sum(preds) / len(preds)

    # Measure disagreement (std dev of predictions)
    variance = sum((p - simple_mean) ** 2 for p in preds) / len(preds)
    disagreement = variance ** 0.5

    # Extremization: if agents agree (low disagreement), push away from 0.5
    # This combats the "always predict no" bias
    if disagreement < 0.10:  # Strong agreement
        extremized = 0.5 + 1.3 * (weighted_mean - 0.5)
        extremized = max(0.02, min(0.98, extremized))
        method = "extremized_agreement"
        final = extremized
        confidence = min(90, int(max(confs)))
    elif disagreement < 0.20:  # Moderate agreement
        extremized = 0.5 + 1.1 * (weighted_mean - 0.5)
        extremized = max(0.02, min(0.98, extremized))
        method = "mild_extremized"
        final = extremized
        confidence = int(sum(confs) / len(confs))
    else:  # High disagreement — hedge toward base rate
        method = "hedged_disagreement"
        final = weighted_mean
        confidence = max(20, int(min(confs)))

    return {
        "prediction": round(final, 4),
        "confidence": confidence,
        "method": method,
        "disagreement": round(disagreement, 4),
        "agent_predictions": [
            {"focus": p.get("focus"), "prediction": p["prediction"], "confidence": p.get("confidence")}
            for p in valid
        ],
        "reasoning": _merge_reasoning(valid),
    }


def _merge_reasoning(predictions: list[dict]) -> str:
    """Combine reasoning from multiple agents."""
    parts = []
    for p in predictions:
        focus = p.get("focus", "?")
        reasoning = p.get("reasoning", "")
        if reasoning:
            parts.append(f"[{focus}] {reasoning}")
    return " | ".join(parts) if parts else ""
