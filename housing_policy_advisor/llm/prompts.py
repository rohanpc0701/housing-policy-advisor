"""Prompt builder for policy recommendation generation."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from housing_policy_advisor.llm.policy_response_parser import policy_json_schema_instructions

MAX_EVIDENCE_CHARS_PER_CHUNK = 800


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
    return f"""You are a housing policy advisor for local governments.
Use the locality data and retrieved evidence to generate ranked policy recommendations.

This locality has been classified as: {locality_profile}

Profile guidance:
- RURAL_LOW_INCOME: prioritize home repair assistance, manufactured housing, USDA programs, down payment assistance, eviction prevention
- RURAL_MODERATE: prioritize ADUs, housing trust funds, homeowner rehabilitation, employer assisted housing
- URBAN_MODERATE: prioritize missing middle housing, land banks, workforce housing, rental registry, housing choice vouchers
- URBAN_HIGH_COST: prioritize community land trusts, inclusionary zoning, anti-displacement, tax increment financing, opportunity to purchase
- COLLEGE_TOWN: prioritize missing middle housing, rental regulation, density bonus, landlord recruitment, short term rental regulation
- UNKNOWN: use your best judgment based on locality data

Recommend policies appropriate for this profile. Do not default to the same policies for every locality.

Do not give generic advice like "increase affordable housing supply."
Name the specific program or policy tool from the retrieved evidence documents and explain why it fits this locality's profile.

Locality data JSON:
{locality_json}

Retrieved evidence chunks with citations:
{evidence_block}

Base your recommendations strictly on the policy documents provided.
Use the exact policy names from those documents.

Rules:
1) Use only evidence-grounded claims.
2) Keep evidence_basis entries as citation strings that reference the chunk IDs.
3) Return ONLY valid JSON and no extra prose.
4) Provide at least 3 recommendations ranked 1..N.
5) For state_of_implementation: name a real U.S. state where this policy is actively used — this proves legal feasibility. Use null if unknown.

Output schema:
{schema}
"""
