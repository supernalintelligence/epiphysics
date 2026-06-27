"""
Retrieve relevant news articles for forecasting questions.

Given a question and a date, finds recent articles that are relevant
to the question topic. This provides the NEWS CONTEXT that makes
prediction meaningful — without it, the model is just guessing from
question phrasing.

Strategy:
  1. Extract key terms from the question
  2. Search recent articles (7-day window before freeze date) for matching terms
  3. Return top-K articles by relevance (simple keyword overlap)
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

# Lazy-loaded dataset handle
_dataset = None
_date_index = None


def _load_dataset():
    """Load the forecast-news dataset (lazy, cached)."""
    global _dataset
    if _dataset is None:
        from datasets import load_from_disk
        data_path = Path(__file__).parent.parent / "data" / "forecast-news"
        print(f"Loading news dataset from {data_path}...")
        _dataset = load_from_disk(str(data_path))["train"]
        print(f"Loaded {len(_dataset):,} articles")
    return _dataset


def extract_key_terms(question: str) -> list[str]:
    """Extract searchable key terms from a question."""
    # Remove common question words and stopwords
    stopwords = {
        "will", "the", "a", "an", "of", "in", "to", "for", "by", "on", "at",
        "is", "be", "are", "was", "were", "been", "being", "have", "has", "had",
        "do", "does", "did", "than", "more", "less", "before", "after", "end",
        "any", "this", "that", "these", "those", "from", "with", "about", "between",
        "into", "through", "during", "above", "below", "and", "or", "but", "not",
        "its", "their", "there", "what", "when", "where", "which", "who", "how",
        "all", "each", "every", "both", "few", "most", "other", "some", "such",
    }

    # Clean and tokenize
    text = re.sub(r'[^\w\s]', ' ', question.lower())
    words = text.split()

    # Filter stopwords and short words, keep capitalized proper nouns from original
    terms = []
    orig_words = question.split()
    for w in orig_words:
        clean = re.sub(r'[^\w]', '', w)
        if clean.lower() not in stopwords and len(clean) > 2:
            terms.append(clean)

    # Also extract potential named entities (capitalized sequences)
    entities = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', question)
    terms.extend(entities)

    return list(set(terms))


def search_articles(
    terms: list[str],
    before_date: str,
    window_days: int = 7,
    max_articles: int = 5,
    max_scan: int = 100000,
) -> list[dict]:
    """Search for articles matching terms within a date window.

    Uses simple keyword matching on title + description.
    For a production system, use vector search or BM25.
    """
    ds = _load_dataset()

    # Parse target date
    try:
        target = datetime.strptime(before_date[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return []

    start_dt = target - timedelta(days=window_days)
    end_dt = target

    # Convert terms to lowercase for matching
    lower_terms = [t.lower() for t in terms]

    # Scan articles — for large dataset, sample rather than full scan
    # Use the date column to filter (articles are roughly date-sorted)
    matches = []
    n = len(ds)

    # Binary search for approximate start position by date
    # Articles are roughly chronological, so sample to find date range
    step = max(1, n // 1000)
    start_idx = 0
    for i in range(0, n, step):
        row_date = ds[i]["date"]
        if row_date:
            if isinstance(row_date, str):
                cmp = row_date[:10] >= start_dt.strftime("%Y-%m-%d")
            else:
                rd = row_date.date() if hasattr(row_date, 'date') else row_date
                cmp = rd >= start_dt.date()
            if cmp:
                start_idx = max(0, i - step)
                break

    scanned = 0
    for i in range(start_idx, min(start_idx + max_scan, n)):
        row = ds[i]
        row_date = row.get("date")
        if not row_date:
            continue
        # Normalize to date for comparison
        if isinstance(row_date, str):
            try:
                row_date = datetime.strptime(row_date[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
        elif hasattr(row_date, 'date'):
            row_date = row_date.date()
        # row_date might already be datetime.date

        if row_date < start_dt.date():
            continue
        if row_date > end_dt.date():
            scanned += 1
            if scanned > 10000:
                break
            continue

        # Check relevance
        title = (row.get("title") or "").lower()
        desc = (row.get("description") or "").lower()
        text = title + " " + desc

        score = sum(1 for t in lower_terms if t in text)
        if score >= 2:  # At least 2 term matches
            matches.append({
                "title": row.get("title", ""),
                "date": row_date,
                "source": row.get("source", ""),
                "description": row.get("description", ""),
                "content": (row.get("content") or "")[:500],  # Truncate
                "score": score,
            })

    # Sort by relevance score, take top-K
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:max_articles]


def get_news_context(
    question: str,
    freeze_date: str = None,
    window_days: int = 7,
    max_articles: int = 5,
) -> str:
    """Get formatted news context for a forecasting question.

    Returns a string suitable for insertion into a prompt.
    """
    terms = extract_key_terms(question)

    if not freeze_date:
        freeze_date = "2026-01-18"  # Default to our question set date

    articles = search_articles(
        terms=terms,
        before_date=freeze_date,
        window_days=window_days,
        max_articles=max_articles,
    )

    if not articles:
        return "No relevant recent news articles found."

    lines = [f"Recent news ({len(articles)} articles from the past {window_days} days):"]
    for i, a in enumerate(articles, 1):
        lines.append(f"\n[{i}] {a['title']} ({a['source']}, {a['date']})")
        if a['description']:
            lines.append(f"    {a['description'][:200]}")
        if a['content']:
            lines.append(f"    {a['content'][:300]}")

    return "\n".join(lines)


def get_news_articles_raw(
    terms: list[str] = None,
    before_date: str = None,
    window_days: int = 7,
    max_articles: int = 20,
) -> list[dict]:
    """Get raw article dicts (not formatted string) for extraction agents.

    If terms is None, returns a general sample from the date window.
    """
    if terms:
        return search_articles(terms, before_date, window_days, max_articles)

    # General sample: scan without keyword filter, return diverse articles
    ds = _load_dataset()
    from datetime import datetime, timedelta
    try:
        target = datetime.strptime(before_date[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return []

    start_dt = target - timedelta(days=window_days)
    end_dt = target

    # Binary search for start position
    n = len(ds)
    step = max(1, n // 1000)
    start_idx = 0
    for i in range(0, n, step):
        row_date = ds[i]["date"]
        if row_date:
            rd = row_date.date() if hasattr(row_date, 'date') else row_date
            if rd >= start_dt.date():
                start_idx = max(0, i - step)
                break

    articles = []
    for i in range(start_idx, min(start_idx + 50000, n)):
        row = ds[i]
        row_date = row.get("date")
        if not row_date:
            continue
        if isinstance(row_date, str):
            continue  # Skip string dates for simplicity
        rd = row_date.date() if hasattr(row_date, 'date') else row_date
        if rd < start_dt.date():
            continue
        if rd > end_dt.date():
            break

        title = row.get("title") or ""
        if len(title) < 10:
            continue

        articles.append({
            "title": title,
            "date": str(rd),
            "source": row.get("source", ""),
            "description": row.get("description", ""),
            "content": (row.get("content") or "")[:500],
        })

        if len(articles) >= max_articles:
            break

    return articles


if __name__ == "__main__":
    # Test
    q = "Will the US enter a recession by end of 2025?"
    print(f"Question: {q}")
    terms = extract_key_terms(q)
    print(f"Key terms: {terms}")

    context = get_news_context(q, freeze_date="2026-01-10")
    print(f"\n{context}")
