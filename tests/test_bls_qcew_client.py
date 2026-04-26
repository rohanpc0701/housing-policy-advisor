"""Tests for BLS QCEW county wage client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from housing_policy_advisor.data.clients.bls_qcew_client import fetch_qcew_county_wages


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=r
        )
    return r


_GOOD_RESPONSE = {
    "results": {
        "area": [
            {"agglvl_code": "75", "avg_wkly_wage": "900", "own_code": "5"},
            {"agglvl_code": "70", "avg_wkly_wage": "1200", "own_code": "0"},
        ]
    }
}


def test_extracts_wage_from_agglvl_70():
    with patch("housing_policy_advisor.data.clients.bls_qcew_client.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = _mock_response(_GOOD_RESPONSE)
        result = fetch_qcew_county_wages("51", "121")

    assert "wage_median" in result
    assert result["wage_median"] == pytest.approx(1200 * 52)


def test_ignores_non_agglvl_70():
    response = {"results": {"area": [{"agglvl_code": "75", "avg_wkly_wage": "900"}]}}
    with patch("housing_policy_advisor.data.clients.bls_qcew_client.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = _mock_response(response)
        result = fetch_qcew_county_wages("51", "121")

    assert result == {}


def test_http_error_returns_empty():
    with patch("housing_policy_advisor.data.clients.bls_qcew_client.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.side_effect = Exception("connection error")
        result = fetch_qcew_county_wages("51", "121")

    assert result == {}


def test_missing_avg_wkly_wage_returns_empty():
    response = {"results": {"area": [{"agglvl_code": "70", "own_code": "0"}]}}
    with patch("housing_policy_advisor.data.clients.bls_qcew_client.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = _mock_response(response)
        result = fetch_qcew_county_wages("51", "121")

    assert result == {}


def test_fips_padding():
    """state_fips and county_fips are zero-padded to 2+3 digits."""
    with patch("housing_policy_advisor.data.clients.bls_qcew_client.httpx.Client") as MockClient:
        mock_get = MockClient.return_value.__enter__.return_value.get
        mock_get.return_value = _mock_response({"results": {"area": []}})
        fetch_qcew_county_wages("1", "1")

    url_called = mock_get.call_args[0][0]
    assert "/01001" in url_called
