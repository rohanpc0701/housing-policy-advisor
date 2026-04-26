"""LLM chat completions with Together default and Groq fallback."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

import httpx

from housing_policy_advisor import config

logger = logging.getLogger(__name__)

# Groq 429 body often includes: "Please try again in 42.59s"
_GROQ_RETRY_SECS = re.compile(r"try again in ([\d.]+)s", re.IGNORECASE)


def _parse_groq_429_wait_seconds(response: httpx.Response) -> float:
    """Return seconds to wait from Retry-After or error JSON text."""
    ra = response.headers.get("Retry-After")
    if ra:
        try:
            return float(ra)
        except ValueError:
            pass
    try:
        payload = response.json()
        msg = (payload.get("error") or {}).get("message") or ""
    except (json.JSONDecodeError, TypeError, ValueError):
        msg = response.text or ""
    m = _GROQ_RETRY_SECS.search(msg)
    if m:
        return float(m.group(1)) + 0.5
    return 60.0


def get_model_name() -> str:
    if get_provider_name() == "together":
        return config.TOGETHER_MODEL
    return config.GROQ_MODEL


def get_provider_name() -> str:
    provider = (config.LLM_PROVIDER or "").strip().lower()
    if provider in {"together", "groq"}:
        return provider
    return "together"


def _complete_with_openai_compatible_api(
    messages: List[Dict[str, str]],
    *,
    api_key: str,
    api_base: str,
    model_name: str,
    provider_label: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """
    Call Groq ``/chat/completions`` and return assistant message content.

    When ``json_mode`` is True, requests ``response_format`` JSON object (supported on compatible models).
    """
    model = model or model_name
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
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

    max_429_attempts = 6
    data: Optional[Dict[str, Any]] = None
    try:
        with httpx.Client() as client:
            for attempt in range(max_429_attempts):
                r = client.post(url, headers=headers, json=body, timeout=120.0)
                if r.status_code == 429 and attempt < max_429_attempts - 1:
                    wait = _parse_groq_429_wait_seconds(r)
                    logger.warning(
                        "%s 429; sleeping %.1fs then retrying (%s/%s)",
                        provider_label.capitalize(),
                        wait,
                        attempt + 1,
                        max_429_attempts,
                    )
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                break
            if data is None:
                raise RuntimeError("Groq: no response after 429 retries")
    except httpx.HTTPStatusError as e:
        logger.error("%s HTTP error: %s %s", provider_label.capitalize(), e.response.status_code, e.response.text[:500])
        raise
    except Exception as e:
        logger.error("%s request failed: %s", provider_label.capitalize(), e)
        raise

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Groq response missing choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if content is None:
        raise RuntimeError(f"{provider_label.capitalize()} response missing message content")
    return str(content)


def complete(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    provider = get_provider_name()
    if provider == "together":
        if config.TOGETHER_API_KEY:
            return _complete_with_openai_compatible_api(
                messages,
                api_key=config.TOGETHER_API_KEY,
                api_base=config.TOGETHER_API_BASE,
                model_name=config.TOGETHER_MODEL,
                provider_label="together",
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        if config.GROQ_API_KEY:
            logger.warning("LLM_PROVIDER=together but TOGETHER_API_KEY not set; falling back to Groq")
            return _complete_with_openai_compatible_api(
                messages,
                api_key=config.GROQ_API_KEY,
                api_base=config.GROQ_API_BASE,
                model_name=config.GROQ_MODEL,
                provider_label="groq",
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        raise RuntimeError("TOGETHER_API_KEY is not set (and GROQ_API_KEY unavailable for fallback)")

    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")
    return _complete_with_openai_compatible_api(
        messages,
        api_key=config.GROQ_API_KEY,
        api_base=config.GROQ_API_BASE,
        model_name=config.GROQ_MODEL,
        provider_label="groq",
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode,
    )


def health_check() -> Dict[str, Any]:
    """Return whether API key is present (no network call)."""
    return {
        "provider": get_provider_name(),
        "groq_api_key_set": bool(config.GROQ_API_KEY),
        "together_api_key_set": bool(config.TOGETHER_API_KEY),
        "model": get_model_name(),
    }


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
