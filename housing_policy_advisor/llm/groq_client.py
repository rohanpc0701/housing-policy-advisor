"""Groq OpenAI-compatible chat completions."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from housing_policy_advisor import config

logger = logging.getLogger(__name__)


def get_model_name() -> str:
    return config.GROQ_MODEL


def complete(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """
    Call Groq ``/chat/completions`` and return assistant message content.

    When ``json_mode`` is True, requests ``response_format`` JSON object (supported on compatible models).
    """
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    model = model or config.GROQ_MODEL
    url = f"{config.GROQ_API_BASE.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client() as client:
            r = client.post(url, headers=headers, json=body, timeout=120.0)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        logger.error("Groq HTTP error: %s %s", e.response.status_code, e.response.text[:500])
        raise
    except Exception as e:
        logger.error("Groq request failed: %s", e)
        raise

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Groq response missing choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if content is None:
        raise RuntimeError("Groq response missing message content")
    return str(content)


def health_check() -> Dict[str, Any]:
    """Return whether API key is present (no network call)."""
    return {"groq_api_key_set": bool(config.GROQ_API_KEY), "model": config.GROQ_MODEL}


def complete_prefer_json(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """
    Try JSON-object mode first; fall back to plain completion if the API rejects ``json_mode``.
    """
    try:
        return complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (400, 422):
            logger.warning("Groq json_mode rejected (%s); retrying without json_mode", code)
            return complete(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=False,
            )
        raise
