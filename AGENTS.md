# AGENTS.md — AI Housing Policy Advisor

## Project Overview

RAG-based AI Housing Policy Advisor for local government planners in Virginia.
Funded by HousingForward Virginia and VCHR (Virginia Center for Housing Research) at Virginia Tech.
The system predicts which housing policies will work for a given locality.
It is a prediction system, NOT a report generator.

**PI:** Dr. Ruichuan Zhang (VT)
**Developer:** Rohan Chavan

---

## Repo Structure

```
housing_policy_advisor/
  main.py                  # CLI entry point
  pipeline.py              # Recommendation orchestration
  config.py                # Threshold constants (partially wired)
  data/
    locality_profile.py    # FullLocalityInput builder
    census_client.py       # Census ACS 5-year (21 fields)
    hud_client.py          # HUD FMR + Income Limits
    bls_client.py          # BLS LAUS unemployment
  llm/
    policy_advisor.py      # LLM policy advisor (Together default, Groq fallback)
    output_validator.py    # 5-check validation (thresholds not wired)
    prompts.py             # Prompt templates (duplicate -- see below)
  rag/
    retriever.py           # ChromaDB semantic search
    prompt_builder.py      # Prompt construction (duplicate of llm/prompts.py)
    ingest/__main__.py     # Ingestion CLI
docs/
  architecture.md
  cleanup-plan.md
```

---

## Environment

```bash
# Required (at least one)
TOGETHER_API_KEY=<your key>
# Optional fallback
GROQ_API_KEY=<your key>

# Optional (needed for live data integration)
CENSUS_API_KEY=<register free at api.census.gov>
HUD_TOKEN=<register free at huduser.gov>
# BLS uses free registration at bls.gov, no token in header
```

Python 3.10+. Install deps:
```bash
pip install -r requirements.txt
```

Run recommendations:
```bash
python -m housing_policy_advisor.main --locality-json data/sample_locality.json --output-format json
```

Run ingestion (requires explicit source dir):
```bash
python -m housing_policy_advisor.rag.ingest --source-dir /path/to/corpus
```

---

## Known Issues (Ground Truth -- Do Not Assume Otherwise)

| Issue | Location | Status |
|---|---|---|
| `pdf`/`docx` output broken | `pipeline.py:83` imports `past_code` not in repo | Do not fix without instruction |
| Provider token/rate caps can interrupt full-batch locality validation | `llm/groq_client.py` runtime path | Operational blocker |
| Prompt builder duplication | `llm/prompts.py` and `rag/prompt_builder.py` overlap | Needs consolidation |
| Data clients not wired to pipeline | `census_client.py`, `hud_client.py`, `bls_client.py` are standalone | Integration is priority task |
| Ingestion corpus path | Defaults to `corpus/` which is not in checkout | Always use `--source-dir` |

Test baseline before any changes: `67 passed`

---

## Target Locality for Testing

Montgomery County, VA
- State FIPS: `51`
- County FIPS: `121`
- HUD FIPS: `5112199999`

---

## Output Schema

The pipeline must produce a JSON array of `PolicyRecommendation` objects:

```json
{
  "rank": 1,
  "policy_name": "string",
  "predicted_outcome": "string",
  "confidence_score": 0.75,
  "evidence_basis": ["chunk_id_1", "chunk_id_2"],
  "comparable_communities": ["locality_a", "locality_b"],
  "implementation_timeline": "string",
  "resource_requirements": "Low | Medium | High",
  "risks": ["string"],
  "validation_flags": []
}
```

---

## Validation Logic (5 Checks in output_validator.py)

| Check | Rule | On Fail |
|---|---|---|
| Grounding Score | >= 80% of claims trace to RAG chunk or input field | Flag: LOW_GROUNDING, send to human review |
| Confidence Score | >= 0.60 per recommendation | Flag: LOW_CONFIDENCE, display warning |
| Comparable Communities | Cited localities within +-30% population, +-20% income of target | Flag: BAD_COMPARABLE, exclude community |
| Completeness | All required output fields populated (100%) | Flag: INCOMPLETE, reject + re-prompt |
| Internal Consistency | No recommendation contradicts input conditions | Flag: CONTRADICTION, suppress + flag |

Threshold values must be read from `config.py`, not hardcoded in `output_validator.py`.

---

## Task Priority

When no explicit task is given, work in this order:

1. Complete full 4-locality validation run in one Groq quota window and refresh final comparison table
2. Tune profile assignment/query routing to reduce cross-locality recommendation repetition
3. Consolidate `llm/prompts.py` and `rag/prompt_builder.py` into one module
4. Restore or fully remove `pdf`/`docx` output -- no half-wired states
5. Add contract tests: CLI smoke test, pipeline JSON shape test, missing-API-key negative test

---

## Constraints

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim) -- do not change
- LLM: Together default (`meta-llama/Llama-3.3-70B-Instruct-Turbo`) with Groq fallback -- do not change without instruction
- No locality comparison features (out of scope)
- No multi-locality batch runs
- No new PDFs added to corpus without explicit instruction
- All data contracts use Pydantic models
- No print() in library code -- use logging module
- Tests mirror source structure under `tests/`
- Never commit API keys or .env files

---

## Verification Steps After Any Change

1. Run `pytest` -- must stay at >= 67 passed, zero regressions
2. Run pipeline on Montgomery County sample JSON with `--output-format json`
3. Confirm output is valid against the PolicyRecommendation schema above
4. If you touched `output_validator.py`, manually verify all 5 checks fire correctly on a known bad input

---

## Tasks Achieved Summary (2026-04-24)

- Completed large-corpus ingestion workflow for case studies by splitting the problematic 1256-page Minneapolis PDF and ingesting split artifacts.
- Resolved Chroma retrieval embedding-function conflict in runtime retrieval path.
- Wired `output_validator.py` threshold checks to `config.py` and validated behavior with tests and real output.
- Wired explicit API-key forwarding from pipeline to `build_full_input()` for Census/HUD/BLS integration path.
- Added `HUD_TOKEN` fallback support via config while keeping `HUD_API_TOKEN` as primary.
- Added test coverage for API-key forwarding in `tests/test_pipeline.py`.
- Added Local Housing Solutions ingestion pipeline:
  - `scrape_lhs_policies.py` (policy-page scrape/chunk)
  - `ingest_lhs_to_chroma.py` (upsert to existing Chroma collection)
  - 480 LHS chunks added.
- Implemented two-pass retrieval with merge/dedupe:
  - locality context pass
  - policy-anchor pass.
- Added profile-based retrieval routing in `rag/retriever.py`:
  - rule-based profile assignment
  - universal + profile-specific query sets
  - profile metadata attached to retrieved chunks.
- Added locality-metric suffix injection to profile-specific pass-2 queries.
- Reworked grounding score to recommendation-level backing:
  - score is based on whether recommended policies are supported by retrieved chunks.
- Updated generation prompt to include locality profile guidance and removed hardcoded policy anchor examples.
- Added detailed experiment record in `docs/grounding_experiments_log.md` (entries through Entry 016).
- Current blocker for final multi-locality validation: provider quota/rate windows (historically Groq TPD 429).
- Together provider integration shipped:
  - `LLM_PROVIDER` default set to `together`
  - provider/model metadata added to output JSON (`metadata.llm_provider`, `metadata.llm_model`)
