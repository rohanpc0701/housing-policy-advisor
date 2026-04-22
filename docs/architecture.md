# Housing Policy Advisor Architecture

## Purpose

`housing_policy_advisor` generates structured housing policy recommendations for a county or locality. It combines:

- Structured locality data from Census ACS, HUD USER, and BLS LAUS
- Retrieved evidence chunks from a persisted Chroma vector store
- Groq chat completions constrained to a strict JSON schema
- Post-generation validation and JSON export

## Runtime Paths

The repository has two main execution paths.

### 1. Recommendation Generation

Entry points:

- `python -m housing_policy_advisor`
- `python -m housing_policy_advisor.main`

Primary flow:

1. Parse CLI arguments in `housing_policy_advisor/main.py`
2. Build a `FullLocalityInput` in `housing_policy_advisor/pipeline.py`
3. Fetch and merge external data in `housing_policy_advisor/data/locality_profile.py`
4. Retrieve evidence chunks from Chroma in `housing_policy_advisor/rag/retriever.py`
5. Build the LLM prompt in `housing_policy_advisor/llm/prompts.py`
6. Call Groq in `housing_policy_advisor/llm/groq_client.py`
7. Parse JSON into typed models in `housing_policy_advisor/llm/policy_response_parser.py`
8. Compute validation summary in `housing_policy_advisor/llm/output_validator.py`
9. Write the final JSON payload in `housing_policy_advisor/pipeline.py`

Output:

- `policy_recommendations_<locality>_<state>.json`

### 2. Corpus Ingestion

Entry point:

- `python -m housing_policy_advisor.rag.ingest`

Primary flow:

1. Resolve source directories in `housing_policy_advisor/rag/ingest/__main__.py`
2. Extract page text from PDFs in `housing_policy_advisor/rag/ingest/pdf_processor.py`
3. Split page text into overlapping chunks in `housing_policy_advisor/rag/ingest/chunking.py`
4. Generate embeddings in `housing_policy_advisor/rag/ingest/embeddings.py`
5. Persist chunks and embeddings to Chroma in `housing_policy_advisor/rag/ingest/vector_db.py`

Output:

- Persisted Chroma collection under `CHROMA_PERSIST_DIR`

## Core Data Models

### `FullLocalityInput`

Defined in `housing_policy_advisor/models/locality_input.py`.

This is the central structured input contract. It combines:

- Locality identity and governance metadata
- Census-derived population, housing stock, tenure, rent, and growth signals
- HUD-derived FMR and AMI-related fields
- BLS-derived labor market fields
- Manual CLI-supplied administrative fields

### `PolicyRecommendationsResult`

Defined in `housing_policy_advisor/models/policy_output.py`.

This is the structured output contract. It contains:

- Locality name
- Generation date
- Ranked recommendations
- Validation summary

## Component Boundaries

### Data Layer

Located under `housing_policy_advisor/data/`.

- `clients/census_client.py` fetches ACS 5-year county data and maps it into model fields
- `clients/hud_client.py` fetches county FMR and income limit data
- `clients/bls_client.py` fetches LAUS unemployment, labor force, and employment data
- `locality_profile.py` orchestrates the three clients and merges results into `FullLocalityInput`

The data clients intentionally return partial dictionaries. `build_full_input()` is the merge point.

### Retrieval Layer

Located under `housing_policy_advisor/rag/`.

- `retriever.py` opens the configured Chroma collection and returns chunks with metadata and distances
- Retrieval currently uses a generic locality-aware semantic query, not field-aware filtering
- The `locality` parameter is accepted by retrieval but is not used yet

This means retrieval is schema-light and depends heavily on corpus quality and embedding relevance.

### LLM Layer

Located under `housing_policy_advisor/llm/`.

- `prompts.py` assembles locality JSON and evidence chunks into a single instruction block
- `groq_client.py` sends OpenAI-compatible chat requests to Groq
- `policy_response_parser.py` extracts and validates the JSON structure
- `output_validator.py` computes aggregate validation metrics and mutates recommendation flags when needed

This layer assumes the model can reliably return schema-conforming JSON, with a plain-text fallback if Groq rejects JSON mode.

### Pipeline Layer

Located in `housing_policy_advisor/pipeline.py`.

Responsibilities:

- Connect the locality builder and policy advisor
- Normalize dataclasses into JSON-serializable trees
- Write the final JSON artifact
- Attempt optional legacy `pdf` and `docx` rendering

`pipeline.py` is the top-level coordinator for recommendation generation.

## Configuration Surface

Defined in `housing_policy_advisor/config.py`.

Main runtime settings:

- API keys: `CENSUS_API_KEY`, `HUD_API_TOKEN`, `BLS_API_KEY`, `GROQ_API_KEY`
- Groq endpoint/model: `GROQ_API_BASE`, `GROQ_MODEL`
- Retrieval store: `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`
- Embedding config: `EMBEDDING_MODEL`, `EMBEDDING_DIM`
- Ingestion defaults: `CHUNK_SIZE`, `CHUNK_OVERLAP`

Operational note:

- Retrieval requires that the persisted Chroma collection was built with the same embedding model expected by runtime retrieval

## Failure Behavior

The system does not fail uniformly.

- Missing HUD or BLS credentials degrade to partial locality profiles
- Missing Chroma dependencies or missing Chroma collection degrade to no-evidence generation
- Missing Groq credentials are fatal because recommendation generation always calls Groq
- Legacy `pdf` and `docx` rendering failures are swallowed and produce no alternate output artifacts

This makes Groq the only hard dependency in the current recommendation path.

## Current Inconsistencies

These are architectural realities that affect maintenance.

- The README describes CLI flags and flows that are not implemented in the current CLI
- The code no longer has a documented non-LLM recommendation path
- `pipeline.py` still contains a legacy output adapter for modules not present in this repository
- `config.py` exposes validation threshold constants that the current validator does not consume

## Test Coverage Shape

The test suite is concentrated around unit-level behavior:

- Data client payload parsing
- Locality profile assembly
- Retrieval and ingestion behavior
- Groq client behavior
- Parser and validator behavior
- Pipeline behavior

There is good module-level coverage, but no true live integration path through external services in CI.

## Suggested Mental Model

Treat this repository as a small orchestration app with one stable typed boundary on each side:

- Input boundary: `FullLocalityInput`
- Output boundary: `PolicyRecommendationsResult`

Everything else is integration glue around those two contracts.
