"""
Load and normalize datasets for entity prediction experiments.

Each loader returns a list of dicts with standardized schema:
  {
    "id": str,
    "question": str,
    "background": str,
    "choices": list[str] | None,
    "resolution": float | str | None,  # ground truth answer
    "source": str,  # dataset name
    "tags": list[str],
    "publish_time": str | None,
    "close_time": str | None,
  }
"""

import json
from pathlib import Path
from typing import Optional

from config import AUTOCAST_QUESTIONS, FORECASTBENCH_DIR


def load_autocast(
    tags_filter: Optional[list[str]] = None,
    keyword_filter: Optional[str] = None,
) -> list[dict]:
    """Load autocast competition questions.

    Args:
        tags_filter: Only include questions with at least one matching tag
        keyword_filter: Only include questions containing this keyword (case-insensitive)
    """
    with open(AUTOCAST_QUESTIONS) as f:
        raw = json.load(f)

    questions = []
    for q in raw:
        if tags_filter:
            if not any(t in q.get("tags", []) for t in tags_filter):
                continue
        if keyword_filter:
            text = (q.get("question", "") + q.get("background", "")).lower()
            if keyword_filter.lower() not in text:
                continue

        questions.append({
            "id": q["id"],
            "question": q["question"],
            "background": q.get("background", ""),
            "choices": q.get("choices"),
            "resolution": None,  # autocast competition set doesn't include resolutions
            "source": "autocast",
            "tags": q.get("tags", []),
            "publish_time": q.get("publish_time"),
            "close_time": q.get("close_time"),
        })

    return questions


def load_forecastbench(
    question_set: str = "latest",
    resolved_only: bool = True,
) -> list[dict]:
    """Load ForecastBench questions with resolved outcomes.

    Args:
        question_set: Which question set to load ("latest", or a date like "2026-03-15")
        resolved_only: Only include questions with known resolutions
    """
    qsets = sorted(FORECASTBENCH_DIR.glob("question_sets/*.json"))
    rsets = sorted(FORECASTBENCH_DIR.glob("resolution_sets/*.json"))

    if not qsets:
        raise FileNotFoundError(f"No question sets in {FORECASTBENCH_DIR}")

    # Select question set
    if question_set == "latest":
        qfile = qsets[-1]
    else:
        matches = [f for f in qsets if question_set in f.name]
        qfile = matches[0] if matches else qsets[-1]

    with open(qfile) as f:
        qdata = json.load(f)

    # Build resolution lookup — match by ID across all resolution sets
    resolutions = {}
    for rf in rsets:
        with open(rf) as f:
            rdata = json.load(f)
            for r in rdata.get("resolutions", []):
                if r.get("resolved"):
                    rid = r["id"]
                    if isinstance(rid, str):
                        resolutions[rid] = r["resolved_to"]

    questions = []
    for q in qdata.get("questions", []):
        qid = q["id"]
        if not isinstance(qid, str):
            continue
        resolution = resolutions.get(qid)

        freeze_val = q.get("freeze_datetime_value")
        if freeze_val is not None:
            try:
                freeze_val = float(freeze_val)
            except (ValueError, TypeError):
                freeze_val = None

        if resolved_only and resolution is None:
            continue

        # Skip non-probability resolutions (ACLED event counts etc.)
        if resolution is not None and not (0 <= resolution <= 1):
            continue

        questions.append({
            "id": qid,
            "question": q.get("question", ""),
            "background": q.get("background", ""),
            "choices": None,
            "resolution": resolution,
            "source": f"forecastbench:{q.get('source', 'unknown')}",
            "tags": [],
            "publish_time": q.get("market_info_open_datetime"),
            "close_time": q.get("market_info_close_datetime"),
            "freeze_value": freeze_val,
            "resolution_criteria": q.get("resolution_criteria", ""),
            "url": q.get("url", ""),
        })

    return questions


def load_forecastbench_temporal(question_sets: list[str]) -> dict:
    """Load multiple ForecastBench question sets, ordered chronologically.

    Returns dict of {tranche_date: [questions]} sorted by date.
    """
    result = {}
    for qs in sorted(question_sets):
        questions = load_forecastbench(question_set=qs, resolved_only=True)
        if questions:
            result[qs] = questions
    return result


def load_all(
    autocast_tags: Optional[list[str]] = None,
    autocast_keyword: Optional[str] = None,
    forecastbench_set: str = "latest",
) -> list[dict]:
    """Load from all available datasets."""
    questions = []
    questions.extend(load_autocast(autocast_tags, autocast_keyword))
    try:
        questions.extend(load_forecastbench(forecastbench_set))
    except FileNotFoundError:
        pass
    return questions


if __name__ == "__main__":
    # Quick test
    ac = load_autocast()
    print(f"Autocast: {len(ac)} questions")
    ac_trump = load_autocast(keyword_filter="trump")
    print(f"Autocast (Trump): {len(ac_trump)} questions")
    ac_policy = load_autocast(tags_filter=["US Policy"])
    print(f"Autocast (US Policy): {len(ac_policy)} questions")

    try:
        fb = load_forecastbench(question_set="2024-07-21")
        print(f"ForecastBench (2024-07-21): {len(fb)} resolved questions")
        if fb:
            print(f"  Sample: {fb[0]['question'][:100]}")
            print(f"  Resolution: {fb[0]['resolution']}")
    except Exception as e:
        print(f"ForecastBench: {e}")
