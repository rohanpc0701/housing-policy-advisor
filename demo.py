"""
Demo: Montgomery County, VA — hardcoded locality profile through full pipeline.

Requires: GROQ_API_KEY env var.
Census/HUD/BLS API keys not needed — locality data is hardcoded below.

Usage:
    python demo.py
"""

import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY is not set. Export it before running:")
    print("  export GROQ_API_KEY=your_key_here")
    sys.exit(1)

from housing_policy_advisor.llm.policy_advisor import PolicyAdvisor
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.pipeline import to_json_tree

MONTGOMERY_COUNTY_VA = FullLocalityInput(
    locality_name="Montgomery County",
    state_name="Virginia",
    state_fips="51",
    county_fips="121",
    governance_form="county",
    hud_fips="5112199999",

    # Population & households (ACS 2022 estimates)
    population_estimate=99_000,
    household_estimate=37_500,
    avg_annual_population_rate_of_change=0.008,
    avg_annual_household_rate_of_change=0.007,

    # Income & housing cost
    median_household_income=62_000,
    median_gross_rent=925,
    cost_burden_rate=0.31,

    # Housing stock
    total_housing_units=41_200,
    vacancy_rate=0.072,
    homeownership_rate=0.54,
    pct_single_family_detached=0.58,
    pct_single_family_attached=0.07,
    pct_multifamily_2_4=0.06,
    pct_multifamily_5plus=0.22,
    pct_mobile_home=0.07,

    # Age of stock
    pct_built_post_2000=0.22,
    pct_built_1980_1999=0.31,
    pct_built_pre_1980=0.47,

    # HUD FMR (FY2023, Montgomery County VA)
    fmr_0br=725,
    fmr_1br=830,
    fmr_2br=1_010,
    fmr_3br=1_340,
    fmr_4br=1_580,

    # AMI income limits (4-person household)
    ami_30pct=19_850,
    ami_50pct=33_100,
    ami_80pct=52_950,
    ami_100pct=66_200,

    # BLS LAUS (2023 annual average)
    unemployment_rate=0.032,
    employment_level=42_800,
    labor_force=44_200,

    # Administrative
    housing_dept_present=True,
    building_permits_annual=250,
)


def print_recommendations(result) -> None:
    top3 = sorted(result.recommendations, key=lambda r: r.rank)[:3]
    width = 72

    print()
    print("=" * width)
    print(f"  Housing Policy Recommendations — {result.locality}")
    print(f"  Generated: {result.generated_date}")
    print("=" * width)

    vs = result.validation_summary
    status = "PASSED" if vs.passed else "DEGRADED"
    print(f"\n  Validation: {status}  |  Grounding: {vs.grounding_score:.0%}"
          f"  |  Avg confidence: {vs.avg_confidence:.0%}"
          f"  |  Completeness: {vs.completeness:.0%}")
    print()

    for rec in top3:
        print("-" * width)
        print(f"  #{rec.rank}  {rec.policy_name}")
        print(f"  Confidence: {rec.confidence_score:.0%}  |  Resources: {rec.resource_requirements}"
              f"  |  Timeline: {rec.implementation_timeline}")
        print()
        print(f"  Outcome:  {rec.predicted_outcome}")
        print(f"  Risks:    {rec.risks}")
        if rec.evidence_basis:
            print(f"  Evidence: {', '.join(rec.evidence_basis[:3])}")
        if rec.validation_flags:
            print(f"  Flags:    {', '.join(rec.validation_flags)}")
        print()

    print("=" * width)
    print()


def main() -> None:
    locality = MONTGOMERY_COUNTY_VA
    print(f"Running pipeline for {locality.locality_name}, {locality.state_name}...")
    print("  RAG retrieval (Chroma) — continues without evidence if unavailable")
    print("  Groq LLM call — llama-3.3-70b-versatile")
    print()

    advisor = PolicyAdvisor(retrieval_k=8)
    result = advisor.generate(locality)

    print_recommendations(result)

    payload = to_json_tree(result)
    payload["locality_profile"] = to_json_tree(locality)
    out_path = Path("policy_recommendations_montgomery_county_va.json")
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  Full JSON written to: {out_path}")
    print()


if __name__ == "__main__":
    main()
