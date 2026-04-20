"""Tests for groq_client — auth header, JSON-mode retry on 400/422."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import httpx
import pytest

from housing_policy_advisor import config


def _make_http_error(status_code: int) -> httpx.HTTPStatusError:
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp = httpx.Response(status_code, request=req, text="error")
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=req, response=resp)


def _mock_success_response(content="{}"):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return mock_resp


def test_complete_sends_bearer_token():
    captured_headers = {}

    def fake_post(url, headers, json, timeout):
        captured_headers.update(headers)
        return _mock_success_response('{"result": "ok"}')

    with patch.object(config, "GROQ_API_KEY", "test-key-123"), \
         patch("housing_policy_advisor.llm.groq_client.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = fake_post

        from housing_policy_advisor.llm.groq_client import complete
        complete([{"role": "user", "content": "hello"}])

    assert captured_headers.get("Authorization") == "Bearer test-key-123"


def test_complete_no_api_key_raises():
    with patch.object(config, "GROQ_API_KEY", None):
        from housing_policy_advisor.llm.groq_client import complete
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            complete([{"role": "user", "content": "hello"}])


def test_complete_prefer_json_retries_on_400():
    call_count = 0

    def fake_post(url, headers, json, timeout):
        nonlocal call_count
        call_count += 1
        if json.get("response_format"):
            raise _make_http_error(400)
        return _mock_success_response('{"ok": true}')

    with patch.object(config, "GROQ_API_KEY", "key"), \
         patch("housing_policy_advisor.llm.groq_client.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = fake_post

        from housing_policy_advisor.llm.groq_client import complete_prefer_json
        result = complete_prefer_json([{"role": "user", "content": "hello"}])

    assert call_count == 2
    assert result == '{"ok": true}'


def test_complete_prefer_json_retries_on_422():
    call_count = 0

    def fake_post(url, headers, json, timeout):
        nonlocal call_count
        call_count += 1
        if json.get("response_format"):
            raise _make_http_error(422)
        return _mock_success_response('{"ok": true}')

    with patch.object(config, "GROQ_API_KEY", "key"), \
         patch("housing_policy_advisor.llm.groq_client.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = fake_post

        from housing_policy_advisor.llm.groq_client import complete_prefer_json
        result = complete_prefer_json([{"role": "user", "content": "hello"}])

    assert result == '{"ok": true}'


def test_complete_prefer_json_reraises_non_400():
    def fake_post(url, headers, json, timeout):
        raise _make_http_error(500)

    with patch.object(config, "GROQ_API_KEY", "key"), \
         patch("housing_policy_advisor.llm.groq_client.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = fake_post

        from housing_policy_advisor.llm.groq_client import complete_prefer_json
        with pytest.raises(httpx.HTTPStatusError):
            complete_prefer_json([{"role": "user", "content": "hello"}])


def test_health_check_no_key():
    with patch.object(config, "GROQ_API_KEY", None):
        from housing_policy_advisor.llm.groq_client import health_check
        result = health_check()
    assert result["groq_api_key_set"] is False
