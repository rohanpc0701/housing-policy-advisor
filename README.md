## Housing Policy Advisor

AI-powered housing policy advisor for local governments.

This repo currently includes:
- **Locality data layer**: Census ACS, HUD FMR/Income Limits, and BLS LAUS clients
- **Unified input model**: `FullLocalityInput`
- **Validation layer**: output validator with configurable thresholds
- **Pipeline + CLI**: runs the locality build and writes JSON outputs

RAG/Chroma and Groq LLM calls are present as **stubs** and are not executed by default.

---

## Setup

```bash
python3 -m pip install -r housing_policy_advisor/requirements.txt
```

### API keys

Set these environment variables as needed:

```bash
export CENSUS_API_KEY="..."
export HUD_API_TOKEN="..."
export BLS_API_KEY="..."
export GROQ_API_KEY="..."  # not used yet by default pipeline
```

---

## Run (example)

Montgomery County, Virginia:

```bash
python3 -m housing_policy_advisor.main \
  --locality "Montgomery County" --state "Virginia" \
  --state-fips 51 --county-fips 121 \
  --governance-form county \
  --has-housing-dept true \
  --housing-dept-name "Montgomery County Community Development" \
  --state-abbr va
```

Outputs (written to the current directory by default):
- `policy_recommendations_montgomery_county_va.json`

To generate only the locality input JSON (no mock recommendations):

```bash
python3 -m housing_policy_advisor.main \
  --locality "Montgomery County" --state "Virginia" \
  --state-fips 51 --county-fips 121 \
  --governance-form county \
  --state-abbr va \
  --input-only
```

Output:
- `locality_profile_montgomery_county_va.json`

---

## Notes

- **Unemployment rate** is stored as a fraction (e.g. `0.032` for 3.2%).
- **Population/household growth** uses ACS 2017 vs 2022 CAGR \((V_{2022} / V_{2017})^{1/5} - 1\).
- **RAG/LLM integration** is intentionally deferred until the input layer is verified.

