"""Prompt construction tests."""

from __future__ import annotations

from housing_policy_advisor import config
from housing_policy_advisor.llm.prompts import policy_recommendation_prompt


def test_prompt_states_comparable_community_tolerance_ranges() -> None:
    locality_data = {
        "locality_name": "Montgomery County",
        "population_estimate": 99_373,
        "median_household_income": 65_270,
    }

    prompt = policy_recommendation_prompt(
        locality_data=locality_data,
        evidence_chunks=[],
        locality_profile="COLLEGE_TOWN",
    )

    pop_low = int(round(locality_data["population_estimate"] * (1 - config.POPULATION_MATCH_TOLERANCE)))
    pop_high = int(round(locality_data["population_estimate"] * (1 + config.POPULATION_MATCH_TOLERANCE)))
    income_low = int(
        round(locality_data["median_household_income"] * (1 - config.INCOME_MATCH_TOLERANCE))
    )
    income_high = int(
        round(locality_data["median_household_income"] * (1 + config.INCOME_MATCH_TOLERANCE))
    )

    assert "comparable_communities" in prompt
    assert f"{pop_low:,}" in prompt
    assert f"{pop_high:,}" in prompt
    assert f"{income_low:,}" in prompt
    assert f"{income_high:,}" in prompt
    assert "Do not use large metro examples" in prompt
