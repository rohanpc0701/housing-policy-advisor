"""Assemble locality JSON + RAG chunks into LLM prompts."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import List, Optional

from housing_policy_advisor.llm.policy_response_parser import policy_json_schema_instructions
from housing_policy_advisor.models.locality_input import FullLocalityInput


def build_policy_prompt(
    locality: FullLocalityInput,
    chunks: List[str],
    *,
    chunk_ids: Optional[List[str]] = None,
) -> str:
    """
    Build the policy recommendation prompt from structured input and evidence chunks.

    Chunks should be labeled so the model can cite them (by index or id).
    """
    loc_json = json.dumps(asdict(locality), indent=2, default=str)
    blocks: List[str] = []
    for i, text in enumerate(chunks):
        label = chunk_ids[i] if chunk_ids and i < len(chunk_ids) else f"CHUNK_{i}"
        blocks.append(f"[{label}]\n{text.strip()}")

    evidence = "\n\n---\n\n".join(blocks) if blocks else "(no retrieved evidence)"

    schema = policy_json_schema_instructions()

    return f"""You are a housing policy advisor for local governments.
Use the locality profile and the evidence blocks below. Prefer policies supported by the evidence.
If evidence is insufficient, say so in predicted_outcome and lower confidence_score.

## Locality profile (JSON)
{loc_json}

## Evidence (cite using bracket labels like [CHUNK_0] in evidence_basis)
{evidence}

## Output format
{schema}
"""


def default_retrieval_query(locality: FullLocalityInput) -> str:
    """Default semantic search query from locality identity."""
    return (
        f"{locality.locality_name} {locality.state_name} housing affordability "
        f"zoning land use rental assistance homeless prevention policy"
    )
