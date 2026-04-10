"""Assemble locality JSON + RAG chunks into LLM prompts — stub for later integration."""

from __future__ import annotations

from typing import List

from housing_policy_advisor.models.locality_input import FullLocalityInput


def build_policy_prompt(locality: FullLocalityInput, chunks: List[str]) -> str:
    """
    Build the main policy recommendation prompt from structured input and evidence chunks.

    Stub returns an empty string until prompt text is finalized with the report template.
    """
    if chunks:
        return ""
    return ""
