## Housing Policy Advisor

AI-powered housing policy advisor for local governments.

Additional repo docs:

- `docs/architecture.md`
- `docs/cleanup-plan.md`

## What This Repo Does

This repository has two main workflows:

- Recommendation generation: build a locality profile, retrieve evidence from Chroma when available, call Groq, and write structured policy recommendations to JSON
- Corpus ingestion: extract text from PDFs, chunk it, embed it, and persist a Chroma collection for retrieval

Main components:

- Locality data layer: Census ACS, HUD USER FMR and income limits, and BLS LAUS clients
- Unified input model: `FullLocalityInput`
- Retrieval: ChromaDB plus `sentence-transformers/all-MiniLM-L6-v2`
- LLM generation: Groq OpenAI-compatible chat completions with strict JSON parsing
- Validation: recommendation completeness, confidence, and grounding summary

## Setup

Install dependencies:

```bash
python3 -m pip install -r housing_policy_advisor/requirements.txt
```

## Environment Variables

### Required for recommendation generation

```bash
export GROQ_API_KEY="..."
```

### Optional external data sources

If these are unset, the app still runs, but locality data will be less complete.

```bash
export CENSUS_API_KEY="..."
export HUD_API_TOKEN="..."
export BLS_API_KEY="..."
```

### Optional retrieval configuration

If a matching Chroma collection is available, the app uses retrieved evidence. If not, generation continues without RAG evidence.

```bash
export CHROMA_PERSIST_DIR="./chroma_db"
export CHROMA_COLLECTION_NAME="housing_policy_chunks"
```

## Generate Recommendations

Entry points:

- `python3 -m housing_policy_advisor`
- `python3 -m housing_policy_advisor.main`

Example:

```bash
python3 -m housing_policy_advisor \
  --locality "Montgomery County" \
  --state "Virginia" \
  --state-fips 51 \
  --county-fips 121 \
  --governance-form county \
  --state-abbr va \
  --housing-dept-present true \
  --retrieval-k 8 \
  --format json \
  --out-dir .
```

Output:

- `policy_recommendations_montgomery_county_va.json`

### Supported CLI Arguments

- `--locality`: locality name
- `--state`: full state name
- `--state-fips`: 2-digit state FIPS
- `--county-fips`: 3-digit county FIPS
- `--hud-fips`: optional 10-digit HUD entity override
- `--governance-form`: locality governance type
- `--state-abbr`: state abbreviation used in output filenames
- `--housing-dept-present`: optional boolean
- `--building-permits-annual`: optional manual input
- `--retrieval-k`: top-k retrieval count, default `8`
- `--format`: `json`, `pdf`, `docx`, or `all`
- `--out-dir`: output directory

### Output Formats

`json` is the only guaranteed output format in the current repository.

The CLI still accepts `pdf`, `docx`, and `all`, but those paths depend on legacy renderer modules that are not part of this checkout. If those modules are unavailable, the app silently writes only the JSON output.

### Retrieval Behavior

Recommendation generation always attempts retrieval. If Chroma is unavailable, misconfigured, or missing the configured collection, the app continues without evidence chunks and the output validation flags reflect that degraded mode.

## Build the Vector Store

Use the ingestion CLI to index your PDF corpus into Chroma:

```bash
python3 -m housing_policy_advisor.rag.ingest \
  --source-dir academic=corpus/academic \
  --source-dir case_studies=corpus/case_studies \
  --source-dir fed_regulatory=corpus/Fed_and_regulatory \
  --source-dir implementation_toolkit=corpus/implementation_toolkit
```

Useful flags:

- `--reset`: reset the collection before indexing
- `--limit N`: ingest only the first `N` PDFs
- `--dry-run`: process PDFs without writing to Chroma
- `--verbose`: enable debug logging

Operational note:

- The runtime retriever and the indexed collection must use the same embedding model
- The default ingest source directories referenced by config may not exist in every checkout, so explicit `--source-dir` arguments are safer

## Notes

- Unemployment rate is stored as a fraction, for example `0.032` for 3.2%
- Population and household growth use ACS 2017 to 2022 CAGR
- HUD income limit parsing targets the nested HUD USER shape for 30%, 50%, 80%, and 100% AMI-related values

## Tests

Run the test suite with:

```bash
python3 -m pytest -q
```

CI runs the same test command on push and pull request.
