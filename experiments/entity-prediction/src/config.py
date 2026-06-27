"""
Configuration for entity prediction experiments.
"""

import os
from pathlib import Path

# Load .env from experiment root
ROOT = Path(__file__).parent.parent
_env_file = ROOT / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Datasets
AUTOCAST_QUESTIONS = DATA_DIR / "autocast" / "competition" / "autocast_competition_test_set.json"
FORECASTBENCH_DIR = DATA_DIR / "forecastbench-datasets-full" / "datasets"

# LLM settings
DEFAULT_MODEL = "claude-haiku-4-5-20251001"  # Cheapest for baseline; upgrade for quality
SONNET_MODEL = "claude-sonnet-4-6-20250514"
OPUS_MODEL = "claude-opus-4-6-20250414"

# Experiment settings
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
RATE_LIMIT_DELAY = 0.5  # seconds between calls
