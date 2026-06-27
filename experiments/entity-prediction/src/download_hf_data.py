"""
Download datasets for entity prediction experiments.

Available datasets:
  1. forecast-news (HF: shash42/forecast-news) — daily news articles in parquet, by date
  2. forecastbench (GitHub, already cloned)
  3. fnspid (GitHub, already cloned) — financial news + stock prices
  4. autocast (GitHub, already cloned) — forecasting tournament questions

Usage:
  pip install datasets huggingface_hub pandas pyarrow
  python download_hf_data.py
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"


def download_forecast_news_recent(months=3):
    """
    Download recent months of forecast-news (daily news articles).
    The full dataset is massive; we download only recent data for backtesting.

    Data is organized as: YYYY/MM/DD/articles_b*.parquet
    Each parquet has: id, title, source, date, url, content, authors, description
    """
    from huggingface_hub import hf_hub_download

    out = DATA_DIR / "forecast-news"
    out.mkdir(parents=True, exist_ok=True)

    today = datetime.now()
    start = today - timedelta(days=months * 30)

    print(f"Downloading forecast-news from {start.date()} to {today.date()}...")

    current = start
    downloaded = 0
    while current <= today:
        year = current.strftime("%Y")
        month = current.strftime("%m")
        day = current.strftime("%d")
        date_path = f"{year}/{month}/{day}"
        local_dir = out / year / month / day
        local_dir.mkdir(parents=True, exist_ok=True)

        # Try to download first parquet batch for each day
        try:
            path = hf_hub_download(
                repo_id="shash42/forecast-news",
                filename=f"{date_path}/articles_b0000.parquet",
                repo_type="dataset",
                local_dir=str(out),
            )
            downloaded += 1
            if downloaded % 10 == 0:
                print(f"  Downloaded {downloaded} days...")
        except Exception:
            pass  # Some days may not have data

        current += timedelta(days=1)

    print(f"Downloaded {downloaded} days of news to {out}")


def download_polymarket_sample():
    """Download a small sample of Polymarket data (full is 107GB)."""
    from datasets import load_dataset

    out = DATA_DIR / "polymarket"
    if out.exists() and any(out.iterdir()):
        print(f"polymarket already exists at {out}, skipping")
        return

    print("Downloading Polymarket sample (10K rows, streaming)...")
    ds = load_dataset(
        "SII-WANGZJ/Polymarket_data",
        split="train",
        streaming=True,
    )

    rows = []
    for i, row in enumerate(ds):
        rows.append(row)
        if i >= 9999:
            break

    out.mkdir(parents=True, exist_ok=True)
    with open(out / "sample_10k.jsonl", "w") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")

    print(f"Saved 10K row sample to {out}/sample_10k.jsonl")


def verify_existing():
    """Check what's already available from git clones."""
    repos = {
        "autocast": "Forecasting tournament Qs (need to download news corpus)",
        "fnspid": "Financial news + stock prices (ready to use)",
        "forecastbench": "Binary prediction Qs + baselines (ready to use)",
    }
    print("\nExisting git-cloned datasets:")
    for name, desc in repos.items():
        path = DATA_DIR / name
        if path.exists():
            import subprocess
            size = subprocess.run(
                ["du", "-sh", str(path)],
                capture_output=True, text=True
            ).stdout.split()[0]
            print(f"  ✓ {name} ({size}) — {desc}")
        else:
            print(f"  ✗ {name} — NOT FOUND")


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("Entity Prediction: Dataset Setup")
    print("=" * 60)

    verify_existing()

    print("\n" + "=" * 60)
    print("Downloading HuggingFace datasets...")
    print("=" * 60)

    # Get recent 3 months of daily news
    try:
        download_forecast_news_recent(months=3)
    except Exception as e:
        print(f"forecast-news download failed: {e}")
        print("You can download manually or use fnspid/forecastbench instead.")

    # Optional: Polymarket sample
    try:
        download_polymarket_sample()
    except Exception as e:
        print(f"Polymarket download failed (optional): {e}")

    print("\nSetup complete. Ready datasets:")
    print("  1. fnspid — financial news + prices (backtest-ready)")
    print("  2. forecastbench — prediction Qs with baselines")
    print("  3. forecast-news — daily news corpus for custom prediction tasks")
    print("  4. autocast — forecasting tournament data")
