"""Настройки проекта (читаются из .env, есть значения по умолчанию)."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INDEX_DIR = DATA_DIR / "index"
RUNS_DIR = ROOT / "runs"
RESULTS_DIR = ROOT / "results"
SCENARIO_DIR = ROOT / "scenarios"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("RA_MODEL", "qwen2.5:7b")
AVAILABLE_MODELS = ["qwen2.5:7b", "qwen2.5:3b"]
TEMPERATURE = 0.2
SEED = 42

MAX_STEPS = int(os.getenv("RA_MAX_STEPS", "150"))
MAX_SECONDS = float(os.getenv("RA_MAX_SECONDS", "1200"))
MAX_REVISIONS = int(os.getenv("RA_MAX_REVISIONS", "1"))
LLM_RETRIES = 2

CHUNK_SIZE = 2500
DENSE_WEIGHT = 0.8  # вес плотной части гибридного скора (из статьи автора)
CANDIDATES_K = 30
MIN_DOC_CHARS = 200
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CORPUS_URLS = {
    "arxiv_may2026.jsonl": "https://raw.githubusercontent.com/Armani7777/arxiv-similar-paper-retrieval/main/data/arxiv_may2026.jsonl",
    "arxiv_2020_2024.jsonl": "https://raw.githubusercontent.com/Armani7777/arxiv-similar-paper-retrieval/main/data/arxiv_2020_2024.jsonl",
}
