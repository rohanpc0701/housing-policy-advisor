# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
python3 -m pip install -r housing_policy_advisor/requirements.txt

# Run all tests (baseline: 67 passed)
python3 -m pytest -q

# Run a single test file
python3 -m pytest tests/test_pipeline.py -q

# Generate recommendations (Montgomery County example)
python3 -m housing_policy_advisor \
  --locality "Montgomery County" --state "Virginia" \
  --state-fips 51 --county-fips 121 \
  --governance-form county --state-abbr va \
  --housing-dept-present true --building-permits-annual 250 \
  --retrieval-k 8 --out-dir .

# Build vector store from PDF corpus
python3 -m housing_policy_advisor.rag.ingest \
  --source-dir academic=corpus/academic \
  --source-dir case_studies=corpus/case_studies \
  --reset --verbose
```

## Tasks Achieved Summary (2026-04-24)

- Stabilized ingestion for a very large case-study PDF by splitting it into smaller PDFs and indexing successfully.
- Indexed additional case-study evidence into Chroma; collection now contains expanded chunk coverage.
- Fixed Chroma runtime retrieval conflict by opening existing collections without passing a conflicting embedding function.
- Wired `output_validator.py` thresholds to `config.py` (`GROUNDING_THRESHOLD`, `CONFIDENCE_THRESHOLD`) and tightened pass logic.
- Updated pipeline wiring to pass configured API credentials into `build_full_input()` explicitly.
- Added backward-compatible HUD env support (`HUD_API_TOKEN` or `HUD_TOKEN`).
- Added regression test coverage for API-key forwarding in pipeline.
- Added and ran Local Housing Solutions policy scraper + ingester:
  - `scrape_lhs_policies.py`
  - `ingest_lhs_to_chroma.py`
  - 102 policies scraped, 480 chunks added to existing Chroma collection.
- Reworked grounding metric from distance proxy to recommendation-level backing:
  - denominator now uses number of recommended policies
  - score reflects chunk support for actual recommended policy names.
- Implemented two-pass retrieval:
  - pass 1 locality/context retrieval
  - pass 2 policy-anchor retrieval
  - merged + deduped chunk set before generation.
- Added profile-based retrieval routing in `rag/retriever.py`:
  - rule-based locality profile assignment
  - universal baseline queries + profile-specific queries
  - profile metadata attached to retrieval results.
- Added locality-metric suffixing for profile-specific pass-2 queries
  - median income, cost burden %, homeownership % appended when available.
- Updated prompt to include locality profile guidance and removed hardcoded anchor examples that caused repeated policy outputs.
- Added extensive experiment chronology in `docs/grounding_experiments_log.md` (entries through Entry 016).
- Verified Groq rate-limit behavior with live probe; generation runs are intermittently blocked by TPD 429 limits.

## Architecture

Two execution paths share one input contract (`FullLocalityInput`) and one output contract (`PolicyRecommendationsResult`). Everything else is integration glue.

### Recommendation Generation Path

`main.py` → `pipeline.py` → `data/locality_profile.py` → `rag/retriever.py` → `llm/prompts.py` → `llm/groq_client.py` (Together default, Groq fallback) → `llm/policy_response_parser.py` → `llm/output_validator.py` → JSON file

- `FullLocalityInput` (models/locality_input.py): central typed input. Merges Census ACS, HUD FMR/income limits, BLS LAUS, and CLI-supplied fields.
- `PolicyRecommendationsResult` (models/policy_output.py): typed output. Contains ranked recommendations + validation summary.
- `pipeline.py`: top-level coordinator — builds input, runs retrieval, calls Groq, normalizes dataclasses to JSON, writes artifact.

### Corpus Ingestion Path

`rag/ingest/__main__.py` → `pdf_processor.py` → `chunking.py` → `embeddings.py` → `vector_db.py` → Chroma

- Embedding model is fixed: `sentence-transformers/all-MiniLM-L6-v2` (384-dim). Do not change.
- Runtime retriever and indexed collection must use the same model.
- Default corpus path `corpus/` does not exist in checkout — always use explicit `--source-dir`.

### Data Layer (`data/`)

Three standalone API clients: `census_client.py` (ACS 5-year, 21 fields), `hud_client.py` (FMR + income limits), `bls_client.py` (LAUS unemployment). Each returns partial dicts. `locality_profile.build_full_input()` merges them into `FullLocalityInput`. Missing credentials degrade to partial profiles; only missing `GROQ_API_KEY` is fatal.

### LLM Layer (`llm/`)

- `groq_client.py`: OpenAI-compatible chat completions with provider routing (Together default, Groq fallback)
- `output_validator.py`: 5-check validation — grounding score, confidence score, comparable communities, completeness, internal consistency. Threshold values read from `config.py`.
- `prompts.py`: now profile-aware; prompt includes locality profile guidance and requires policy naming from retrieved evidence.
- `policy_advisor.py`: grounding score now recommendation-level backing (recommended policy support in retrieved chunks), not average retrieval distance.

## Known Issues (Do Not Fix Without Instruction)

| Issue | Location |
|---|---|
| `pdf`/`docx` output broken | `pipeline.py:83` imports `past_code` not in repo |
| Provider quota/rate limits can interrupt multi-locality runs | Runtime (`llm/groq_client.py` call path) |
| Prompt builder duplicated | `llm/prompts.py` and `rag/prompt_builder.py` overlap |
| Data clients not wired to pipeline | Clients are standalone; `pipeline.py` doesn't call them |

## Priority Tasks (When No Explicit Task Given)

1. Complete full 4-locality validation run in one quota window and refresh Entry 016 results table
2. Tune profile routing thresholds/query sets to reduce recommendation repetition across localities
3. Consolidate `llm/prompts.py` and `rag/prompt_builder.py` into one module
4. Restore or fully remove `pdf`/`docx` output — no half-wired states
5. Add contract tests: CLI smoke, pipeline JSON shape, missing-API-key negative

## Constraints

- LLM: Together default (`meta-llama/Llama-3.3-70B-Instruct-Turbo`) with Groq fallback — do not change without instruction
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim) — do not change
- All data contracts use Pydantic models
- No `print()` in library code — use `logging`
- Tests mirror source under `tests/`; run pytest after every change
- No multi-locality batch runs; no locality comparison features
- Target test locality: Montgomery County, VA (state FIPS: 51, county FIPS: 121, HUD FIPS: 5112199999)

## Environment Variables

```bash
TOGETHER_API_KEY=...      # Preferred default provider key
GROQ_API_KEY=...          # Optional fallback provider key
CENSUS_API_KEY=...        # Optional — degrades to partial profile if unset
HUD_API_TOKEN=...         # Optional — degrades to partial profile if unset
BLS_API_KEY=...           # Optional — degrades to partial profile if unset
LLM_PROVIDER=together     # Default provider
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=housing_policy_chunks
```
