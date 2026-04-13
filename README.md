## Housing Policy Advisor

AI-powered housing policy advisor for local governments.

This repo includes:
- **Locality data layer**: Census ACS, HUD FMR/Income Limits, and BLS LAUS clients
- **Unified input model**: `FullLocalityInput`
- **RAG**: ChromaDB retrieval with `sentence-transformers/all-MiniLM-L6-v2` (384-dim), configurable via env
- **LLM**: Groq OpenAI-compatible chat completions + strict JSON parsing for recommendations
- **Validation**: output validator with configurable thresholds
- **Pipeline + CLI**: locality JSON, mock recommendations, or **RAG + Groq** mode

---

## Setup

```bash
python3 -m pip install -r housing_policy_advisor/requirements.txt
```

### API keys

```bash
export CENSUS_API_KEY="..."
export HUD_API_TOKEN="..."
export BLS_API_KEY="..."
export GROQ_API_KEY="..."
```

### Chroma vector store

Point the app at your persisted Chroma directory (must contain a collection whose embeddings match `EMBEDDING_MODEL`):

```bash
export CHROMA_PERSIST_DIR="./chroma_db"
export CHROMA_COLLECTION_NAME="housing_policy_chunks"
```

If the collection is missing, retrieval raises a clear error listing available collection names.

### Building permits

`building_permits_trend` and `building_permits_annual` are **manual / CLI-only** in this version. Census Building Permits Survey (BPS) integration is not implemented; pass values via `--building-permits-trend` and `--building-permits-annual` when you have them.

---

## Run (example)

Montgomery County, Virginia — **mock recommendations** (default):

```bash
python3 -m housing_policy_advisor.main \
  --locality "Montgomery County" --state "Virginia" \
  --state-fips 51 --county-fips 121 \
  --governance-form county \
  --has-housing-dept true \
  --housing-dept-name "Montgomery County Community Development" \
  --state-abbr va
```

Output: `policy_recommendations_montgomery_county_va.json` (includes `llm_mode` only for Groq runs).

### Locality input only

```bash
python3 -m housing_policy_advisor.main \
  --locality "Montgomery County" --state "Virginia" \
  --state-fips 51 --county-fips 121 \
  --governance-form county \
  --state-abbr va \
  --input-only
```

Output: `locality_profile_montgomery_county_va.json`

### RAG + Groq (real recommendations)

Requires `CHROMA_PERSIST_DIR`, a matching collection, and `GROQ_API_KEY`:

```bash
python3 -m housing_policy_advisor.main \
  --locality "Montgomery County" --state "Virginia" \
  --state-fips 51 --county-fips 121 \
  --governance-form county \
  --state-abbr va \
  --use-llm \
  --retrieval-k 8
```

---

## Notes

- **Unemployment rate** is stored as a fraction (e.g. `0.032` for 3.2%).
- **Population/household growth** uses ACS 2017 vs 2022 CAGR: \((V_{2022} / V_{2017})^{1/5} - 1\).
- **HUD income limits** follow the HUD USER API nested shape: `extremely_low` / `very_low` / `low` with `il30_p4`, `il50_p4`, `il80_p4` (30%, 50%, 80% AMI for four-person households).
- **`--use-llm`** is ignored if you also pass **`--input-only`**.

---

## Tests

```bash
python3 -m pytest -q
```

CI runs the same on push/PR via `.github/workflows/ci.yml`.
