# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
python3 -m pip install -r housing_policy_advisor/requirements.txt

# Run all tests (baseline: 82 passed)
python3 -m pytest -q

# Run a single test file
python3 -m pytest tests/test_pipeline.py -q

# Generate recommendations (Montgomery County example)
python3 -m housing_policy_advisor \
  --locality "Montgomery County" --state "Virginia" \
  --state-fips 51 --county-fips 121 \
  --governance-form county --state-abbr va \
  --housing-dept-present true \
  --retrieval-k 20 --out-dir .

# Build vector store from PDF corpus
python3 -m housing_policy_advisor.rag.ingest \
  --source-dir academic=corpus/academic \
  --source-dir case_studies=corpus/case_studies \
  --verbose
```

## Tasks Achieved Summary (2026-04-26)

- Fixed `risks` field type: was `str`, LLM returns array — changed to `List[str]` across parser, validator, pipeline, tests.
- Removed dead `rag/prompt_builder.py`; `llm/prompts.py` is the sole active prompt builder.
- Fixed `retrieve_chunks` to honor the `k` argument in two-pass retrieval (was hardcoded 10/2).
- Fixed COLLEGE_TOWN profile assignment: added upper pop bound `< 120k` to prevent large-city misclassification.
- Added SUBURBAN_GROWING profile queries (TOD, APFO, suburban infill) and wired profile assignment logic.
- Removed dead pdf/docx output path and `output_format` parameter from pipeline + CLI.
- `wage_median` is populated from ACS `B20002_001E` (median worker earnings, full-time year-round).
- Added contract tests: CLI smoke, pipeline JSON shape, missing-API-key negative.
- Changed `VectorDatabase.add_chunks` from `add()` to `upsert()` — safe re-ingestion of same filenames.
- Corpus expanded: 28 PDFs ingested (academic, case studies, fed/regulatory, implementation toolkit, Minneapolis 2040 splits); collection = 6,604 chunks.
- Grounding metric reworked: primary signal = `evidence_basis` entries matched against real retrieved chunk IDs. Keyword fallback tightened (≥2 term overlap required, not single-word).
- Prompt tightened: `policy_name` must be exact name from chunk, `evidence_basis` must contain real chunk ID labels. Generic category names rejected.
- Minimum recommendations raised from 3 → 5; validator `passed` threshold updated to match.
- `CONFIDENCE_THRESHOLD` lowered 0.60 → 0.55 based on live run calibration.
- **Grounding score: 56% → 100% on Montgomery County VA live run.**
- 82 tests passing.

### Addendum (later 2026-04-26 session)

- Ingestion CLI updated with `--input-dir` and before/after collection count reporting.
- Created `data/corpus_additions/` and ingested new files:
  - 8 PDFs processed
  - +205 chunks
  - collection size 6604 -> 6809
- Added retrieval-only integration tests for corpus expansion:
  - `tests/test_corpus_expansion.py` (3 tests, no LLM calls)
- Added `.env.example` and startup warnings for missing optional HUD/BLS keys:
  - config supports `HUD_API_TOKEN` or `HUD_API_KEY` (plus legacy `HUD_TOKEN`)
  - tests added in `tests/test_config_warnings.py`
- Verified QCEW references removed from active code/docs; LAUS path retained.
- Replaced hardcoded `building_permits_annual` fallback with Census BPS-derived data (`timeseries/eits/bps`):
  - known county -> integer
  - unknown/no data -> `None`
  - tests added in `tests/test_census_client.py`
- Removed `--building-permits-annual 250` from docs examples (README + CLAUDE command snippets).
- Ran `security_agent.py`:
  - dependency audit PASS
  - `.env` reported as present but ignored (INFO).

### Previous session (2026-04-24)

- Stabilized ingestion for a very large case-study PDF by splitting it into smaller PDFs.
- Wired `output_validator.py` thresholds to `config.py`.
- Added backward-compatible HUD env support (`HUD_API_TOKEN` or `HUD_TOKEN`).
- Added Local Housing Solutions policy scraper + ingester (102 policies, 480 chunks).
- Reworked grounding metric to recommendation-level backing.
- Implemented two-pass retrieval (locality + policy-anchor passes).
- Added profile-based retrieval routing with locality-metric suffixing.

## Architecture

Two execution paths share one input contract (`FullLocalityInput`) and one output contract (`PolicyRecommendationsResult`). Everything else is integration glue.

### Recommendation Generation Path

`main.py` → `pipeline.py` → `data/locality_profile.py` → `rag/retriever.py` → `llm/prompts.py` → `llm/groq_client.py` (Together default, Groq fallback) → `llm/policy_response_parser.py` → `llm/output_validator.py` → JSON file

- `FullLocalityInput` (models/locality_input.py): central typed input. Merges Census ACS, HUD FMR/income limits, BLS LAUS, and CLI-supplied fields.
- `PolicyRecommendationsResult` (models/policy_output.py): typed output. Contains ranked recommendations + validation summary.
- `pipeline.py`: top-level coordinator — builds input, runs retrieval, calls LLM, normalizes dataclasses to JSON, writes artifact.

### Corpus Ingestion Path

`rag/ingest/__main__.py` → `pdf_processor.py` → `chunking.py` → `embeddings.py` → `vector_db.py` → Chroma

- Embedding model is fixed: `sentence-transformers/all-MiniLM-L6-v2` (384-dim). Do not change.
- Runtime retriever and indexed collection must use the same model.
- Default corpus path `corpus/` does not exist in checkout — always use explicit `--source-dir`.
- `vector_db.add_chunks` uses `upsert` — safe to re-ingest without `--reset`.

### Data Layer (`data/`)

Four standalone API clients: `census_client.py` (ACS 5-year, 22+ fields including `wage_median` from B20002), `hud_client.py` (FMR + income limits), `bls_client.py` (LAUS unemployment). Each returns partial dicts. `locality_profile.build_full_input()` merges them into `FullLocalityInput`. Missing credentials degrade to partial profiles; only missing `TOGETHER_API_KEY` (or `GROQ_API_KEY` when provider=groq) is fatal.

### LLM Layer (`llm/`)

- `groq_client.py`: OpenAI-compatible chat completions with provider routing (Together default, Groq fallback)
- `output_validator.py`: validation — grounding score, confidence score, completeness. Threshold values read from `config.py`. Requires ≥5 recommendations for `passed=True`.
- `prompts.py`: profile-aware; requires exact chunk-cited policy names and real chunk ID labels in `evidence_basis`.
- `policy_advisor.py`: grounding = fraction of recs whose `evidence_basis` contains a real retrieved chunk ID (keyword fallback if no ID match).

### Profile Routing (`rag/retriever.py`)

Six profiles assigned by `_assign_locality_profile()` in priority order:
1. `COLLEGE_TOWN`: 15k < pop < 120k AND homeownership < 0.45
2. `URBAN_HIGH_COST`: pop > 50k, city governance, income > 65k, burden > 0.35
3. `URBAN_MODERATE`: pop > 50k, city governance, income ≥ 45k
4. `SUBURBAN_GROWING`: pop > 50k, non-city governance, income ≥ 55k
5. `RURAL_LOW_INCOME`: income < 45k OR pop < 50k
6. `RURAL_MODERATE`: default

## Known Issues (Do Not Fix Without Instruction)

| Issue | Location |
|---|---|
| Provider quota/rate limits can interrupt multi-locality runs | Runtime (`llm/groq_client.py` call path) |
| `wage_pct25` / `wage_pct75` fields always None | No county-level percentile wage source available |

## Priority Tasks (When No Explicit Task Given)

### Done
- [x] Full 4-locality validation run — all 4 profiles pass, grounding 1.00 (Entry 021)
- [x] BPS `building_permits_annual` fix — flat-file `co{year}a.txt` replaces broken REST endpoint

### Active
1. **Tune profile routing** — same-profile localities share identical pass-2 query sets → similar recs; add per-locality Census-metric differentiation or expand profile-specific query variety
2. **Corpus: program-level docs** — add LIHTC allocation guides, rental assistance toolkits; recs 4-5 confidence ~0.49-0.54 due to sparse program-level evidence
3. **URBAN_HIGH_COST profile unvalidated** — no VA locality in current test set meets all 4 thresholds; identify a suitable locality and run

### Backlog
- `wage_pct25` / `wage_pct75` always None — no county-level ACS percentile source available (known, do not fix without instruction)
- AGENTS.md has stale entries (e.g. references deleted `rag/prompt_builder.py`) — sync with CLAUDE.md

## Constraints

- LLM: Together default (`meta-llama/Llama-3.3-70B-Instruct-Turbo`) with Groq fallback — do not change without instruction
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim) — do not change
- All data contracts use Pydantic/dataclass models
- No `print()` in library code — use `logging`
- Tests mirror source under `tests/`; run pytest after every change
- No multi-locality batch runs; no locality comparison features
- Target test locality: Montgomery County, VA (state FIPS: 51, county FIPS: 121, HUD FIPS: 5112199999)

## Environment Variables

```bash
TOGETHER_API_KEY=...      # Required default provider key
GROQ_API_KEY=...          # Optional fallback provider key
CENSUS_API_KEY=...        # Optional — degrades to partial profile if unset
HUD_API_TOKEN=...         # Optional — degrades to partial profile if unset
BLS_API_KEY=...           # Optional — degrades to partial profile if unset
LLM_PROVIDER=together     # Default provider
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=housing_policy_chunks
```
