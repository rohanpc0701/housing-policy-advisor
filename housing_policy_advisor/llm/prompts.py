"""Prompt builder for policy recommendation generation."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from housing_policy_advisor import config
from housing_policy_advisor.llm.policy_response_parser import policy_json_schema_instructions

MAX_EVIDENCE_CHARS_PER_CHUNK = 800


def _format_comparable_guidance(locality_data: Dict[str, Any]) -> str:
    population = locality_data.get("population_estimate")
    income = locality_data.get("median_household_income")
    if not population or not income:
        return (
            "Comparable-community constraint: use the closest available real localities by "
            "population and median household income. Do not use large metro examples unless "
            "the target locality is also a large metro."
        )

    pop_low = int(round(float(population) * (1 - config.POPULATION_MATCH_TOLERANCE)))
    pop_high = int(round(float(population) * (1 + config.POPULATION_MATCH_TOLERANCE)))
    income_low = int(round(float(income) * (1 - config.INCOME_MATCH_TOLERANCE)))
    income_high = int(round(float(income) * (1 + config.INCOME_MATCH_TOLERANCE)))
    return (
        "Comparable-community constraint: every comparable_communities entry MUST have "
        f"population between {pop_low:,} and {pop_high:,}, and median_household_income "
        f"between {income_low:,} and {income_high:,}. Do not use large metro examples "
        "unless they fall inside both ranges."
    )


def policy_recommendation_prompt(
    locality_data: Dict[str, Any],
    evidence_chunks: List[Dict[str, Any]],
    locality_profile: str = "UNKNOWN",
) -> str:
    locality_json = json.dumps(locality_data, indent=2, default=str)
    evidence_lines: List[str] = []
    for i, chunk in enumerate(evidence_chunks):
        cid = str(chunk.get("id", f"chunk_{i}"))
        text = str(chunk.get("text", "")).strip()
        if len(text) > MAX_EVIDENCE_CHARS_PER_CHUNK:
            text = text[:MAX_EVIDENCE_CHARS_PER_CHUNK].rstrip() + " ...[truncated]"
        source = str((chunk.get("metadata") or {}).get("source", "unknown_source"))
        distance = chunk.get("distance")
        evidence_lines.append(
            f"[{cid}] source={source} distance={distance}\n{text}"
        )

    evidence_block = "\n\n---\n\n".join(evidence_lines) if evidence_lines else "(no retrieved evidence)"
    schema = policy_json_schema_instructions()
    comparable_guidance = _format_comparable_guidance(locality_data)
    return f"""You are a housing policy advisor for local governments.
Use ONLY the retrieved evidence chunks below to generate ranked policy recommendations.
Do not draw on training knowledge for policy names — every recommended policy must appear in the chunks.

This locality has been classified as: {locality_profile}

Profile guidance:
- RURAL_LOW_INCOME: prioritize home repair assistance, manufactured housing, USDA programs, down payment assistance, eviction prevention
- RURAL_MODERATE: prioritize ADUs, housing trust funds, homeowner rehabilitation, employer assisted housing
- URBAN_MODERATE: prioritize missing middle housing, land banks, workforce housing, rental registry, housing choice vouchers
- URBAN_HIGH_COST: prioritize community land trusts, inclusionary zoning, anti-displacement, tax increment financing, opportunity to purchase
- COLLEGE_TOWN: prioritize missing middle housing, rental regulation, density bonus, landlord recruitment, short term rental regulation
- SUBURBAN_GROWING: prioritize transit-oriented development, ADUs in single-family zones, workforce housing, infrastructure-linked growth management
- UNKNOWN: use your best judgment based on locality data

Locality data JSON:
{locality_json}

Retrieved evidence chunks (each labeled with its ID):
{evidence_block}

Rules (strictly enforced):
1) policy_name MUST be the exact name of a specific program or policy tool as written in one of the retrieved chunks above. Do not use generic category names like "Rental Assistance Programs" or "Homeownership Programs" — use the specific program name from the evidence.
2) evidence_basis MUST contain the exact chunk ID labels shown in brackets above (e.g., "gap_report_2024_p1_c0"). Cite at least one ID per recommendation whose chunk text supports the policy.
3) Do not recommend any policy that is not supported by at least one retrieved chunk.
4) Return ONLY valid JSON — no prose, no markdown, no commentary.
5) Provide at least 5 recommendations ranked 1..N. More is better if evidence supports it.
6) state_of_implementation: name a real U.S. state where this policy is actively implemented — proves legal feasibility. Use null if unknown.
7) comparable_communities: include real locality names with population and median_household_income close to the target locality.
8) {comparable_guidance}

Output schema:
{schema}
"""
