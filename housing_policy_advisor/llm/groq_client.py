"""Groq API wrapper for Llama — stub until RAG + policy prompts are wired."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from housing_policy_advisor import config


def get_model_name() -> str:
    return config.GROQ_MODEL


def complete(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """
    Call Groq chat completions. Not used by default pipeline until RAG integration.

    Raises NotImplementedError until implemented with httpx + GROQ_API_KEY.
    """
    raise NotImplementedError(
        "Groq client is a stub; wire GROQ_API_KEY and implement chat completions when RAG is ready."
    )


def health_check() -> Dict[str, Any]:
    """Return whether API key is present (no network call)."""
    return {"groq_api_key_set": bool(config.GROQ_API_KEY), "model": config.GROQ_MODEL}
