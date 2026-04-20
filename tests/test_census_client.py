"""Tests for census_client — suppression sentinels, CAGR, zero-2017 edge case."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from housing_policy_advisor.data.clients.census_client import (
    _clean_int,
    _clean_float,
    _pct,
    fetch_acs_county_data,
)


# --- Unit tests for helper functions ---

def test_clean_int_normal():
    assert _clean_int("42000") == 42000
    assert _clean_int(42000) == 42000


def test_clean_int_none():
    assert _clean_int(None) is None
    assert _clean_int("") is None


def test_clean_int_suppressed_sentinels():
    assert _clean_int("-666666666") is None
    assert _clean_int(-666666666) is None
    assert _clean_int(-888888888) is None
    assert _clean_int(-999999999) is None


def test_clean_int_negative():
    assert _clean_int(-5) is None


def test_clean_float_normal():
    assert _clean_float("3.14") == pytest.approx(3.14)


def test_clean_float_suppressed():
    assert _clean_float(-666666666.0) is None


def test_pct_normal():
    result = _pct(30, 100)
    assert result == pytest.approx(0.30)


def test_pct_zero_denom():
    assert _pct(30, 0) is None


def test_pct_none_inputs():
    assert _pct(None, 100) is None
    assert _pct(30, None) is None


# --- Integration tests for fetch_acs_county_data ---

def _mock_get_row(row_2022, row_2017=None):
    call_count = 0

    def side_effect(client, year, variables, state_fips, county_fips, api_key):
        nonlocal call_count
        call_count += 1
        if year == 2017:
            return row_2017
        return row_2022

    return side_effect


def test_fetch_acs_returns_population(fake_acs_response):
    with patch("housing_policy_advisor.data.clients.census_client._get_row") as mock_row, \
         patch("housing_policy_advisor.data.clients.census_client.httpx.Client"):
        mock_row.side_effect = _mock_get_row(
            row_2022=fake_acs_response,
            row_2017={"B01003_001E": "95000", "B11001_001E": "38000"},
        )
        result = fetch_acs_county_data("51", "001")

    assert result["population_estimate"] == 100000
    assert result["median_household_income"] == 65000


def test_fetch_acs_cagr_computed(fake_acs_response):
    with patch("housing_policy_advisor.data.clients.census_client._get_row") as mock_row, \
         patch("housing_policy_advisor.data.clients.census_client.httpx.Client"):
        mock_row.side_effect = _mock_get_row(
            row_2022=fake_acs_response,
            row_2017={"B01003_001E": "95000", "B11001_001E": "38000"},
        )
        result = fetch_acs_county_data("51", "001")

    # CAGR = (100000/95000)^(1/5) - 1 ≈ 0.0103
    assert "avg_annual_population_rate_of_change" in result
    assert result["avg_annual_population_rate_of_change"] == pytest.approx((100000 / 95000) ** 0.2 - 1, abs=1e-6)


def test_fetch_acs_cagr_zero_2017_skipped(fake_acs_response):
    """CAGR skipped when 2017 pop is zero (div-by-zero guard)."""
    with patch("housing_policy_advisor.data.clients.census_client._get_row") as mock_row, \
         patch("housing_policy_advisor.data.clients.census_client.httpx.Client"):
        mock_row.side_effect = _mock_get_row(
            row_2022=fake_acs_response,
            row_2017={"B01003_001E": "0", "B11001_001E": "0"},
        )
        result = fetch_acs_county_data("51", "001")

    assert "avg_annual_population_rate_of_change" not in result


def test_fetch_acs_cagr_none_2017_skipped(fake_acs_response):
    """CAGR skipped when 2017 row missing."""
    with patch("housing_policy_advisor.data.clients.census_client._get_row") as mock_row, \
         patch("housing_policy_advisor.data.clients.census_client.httpx.Client"):
        mock_row.side_effect = _mock_get_row(
            row_2022=fake_acs_response,
            row_2017=None,
        )
        result = fetch_acs_county_data("51", "001")

    assert "avg_annual_population_rate_of_change" not in result


def test_fetch_acs_no_row_returns_empty():
    with patch("housing_policy_advisor.data.clients.census_client._get_row", return_value=None), \
         patch("housing_policy_advisor.data.clients.census_client.httpx.Client"):
        result = fetch_acs_county_data("51", "001")

    assert result == {}


def test_fetch_acs_suppressed_income(fake_acs_response):
    modified = dict(fake_acs_response)
    modified["B19013_001E"] = "-666666666"
    with patch("housing_policy_advisor.data.clients.census_client._get_row") as mock_row, \
         patch("housing_policy_advisor.data.clients.census_client.httpx.Client"):
        mock_row.side_effect = _mock_get_row(row_2022=modified)
        result = fetch_acs_county_data("51", "001")

    assert result.get("median_household_income") is None
