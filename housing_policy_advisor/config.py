"""API keys, model config, and validation thresholds."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
# Support both names; HUD_TOKEN appears in project docs and older setups.
HUD_API_TOKEN = os.getenv("HUD_API_TOKEN") or os.getenv("HUD_TOKEN")
BLS_API_KEY = os.getenv("BLS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
TOGETHER_API_BASE = os.getenv("TOGETHER_API_BASE", "https://api.together.xyz/v1")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "together").strip().lower()
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "housing_policy_chunks")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Ingestion defaults
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

_REPO_ROOT = Path(__file__).parent.parent
DEFAULT_PDF_SOURCES: dict = {
    "academic": _REPO_ROOT / "corpus" / "academic",
    "case_studies": _REPO_ROOT / "corpus" / "case_studies",
    "fed_regulatory": _REPO_ROOT / "corpus" / "Fed_and_regulatory",
    "implementation_toolkit": _REPO_ROOT / "corpus" / "implementation_toolkit",
}


def chroma_persist_path() -> Path:
    return Path(CHROMA_PERSIST_DIR).expanduser().resolve()


# ACS dataset year (5-year estimates)
ACS_YEAR = 2022
ACS_BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"

# Validation thresholds
GROUNDING_THRESHOLD = 0.80
CONFIDENCE_THRESHOLD = 0.55
POPULATION_MATCH_TOLERANCE = 0.30
INCOME_MATCH_TOLERANCE = 0.20
