"""Prompt builder for policy recommendation generation."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from housing_policy_advisor.llm.policy_response_parser import policy_json_schema_instructions


def policy_recommendation_prompt(
    locality_data: Dict[str, Any],
    evidence_chunks: List[Dict[str, Any]],
) -> str:
    locality_json = json.dumps(locality_data, indent=2, default=str)
    evidence_lines: List[str] = []
    for i, chunk in enumerate(evidence_chunks):
        cid = str(chunk.get("id", f"chunk_{i}"))
        text = str(chunk.get("text", "")).strip()
        source = str((chunk.get("metadata") or {}).get("source", "unknown_source"))
        distance = chunk.get("distance")
        evidence_lines.append(
            f"[{cid}] source={source} distance={distance}\n{text}"
        )

    evidence_block = "\n\n---\n\n".join(evidence_lines) if evidence_lines else "(no retrieved evidence)"
    schema = policy_json_schema_instructions()
    return f"""You are a housing policy advisor for local governments.
Use the locality data and retrieved evidence to generate ranked policy recommendations.

Locality data JSON:
{locality_json}

Retrieved evidence chunks with citations:
{evidence_block}

Rules:
1) Use only evidence-grounded claims.
2) Keep evidence_basis entries as citation strings that reference the chunk IDs.
3) Return ONLY valid JSON and no extra prose.
4) Provide at least 3 recommendations ranked 1..N.

Output schema:
{schema}
"""
