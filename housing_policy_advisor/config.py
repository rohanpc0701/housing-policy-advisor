"""API keys, model config, and validation thresholds."""

import os
from pathlib import Path

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
HUD_API_TOKEN = os.getenv("HUD_API_TOKEN")
BLS_API_KEY = os.getenv("BLS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "housing_policy_chunks")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def chroma_persist_path() -> Path:
    return Path(CHROMA_PERSIST_DIR).expanduser().resolve()

# ACS dataset year (5-year estimates)
ACS_YEAR = 2022
ACS_BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"

# Validation thresholds
GROUNDING_THRESHOLD = 0.80
CONFIDENCE_THRESHOLD = 0.60
POPULATION_MATCH_TOLERANCE = 0.30
INCOME_MATCH_TOLERANCE = 0.20
