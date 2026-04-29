"""Tests for census_client — suppression sentinels, CAGR, zero-2017 edge case."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import httpx
import pytest

from housing_policy_advisor.data.clients.census_client import (
    _clean_int,
    _clean_float,
    _pct,
    _fetch_building_permits_annual,
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


_BPS_SAMPLE_TXT = (
    "Survey,FIPS,FIPS,Region,Division,County,,1-unit,,,2-units,,,3-4 units,,,5+ units\n"
    "Date,State,County,Code,Code,Name,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value,Bldgs,Units,Value\n"
    " \n"
    "2022,51,121,3,5,Montgomery County             ,247,247,66257277,8,16,3081000,0,0,0,4,107,18392029\n"
    "2022,51,059,3,5,Fairfax County                ,980,980,244053741,0,0,0,0,0,0,21,1007,149586961\n"
)


def _bps_mock_client(text: str):
    """Return a context-manager httpx.Client mock that serves `text` for any GET."""
    class _Resp:
        def raise_for_status(self):
            return None
        @property
        def text(self):
            return text

    class _Client:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def get(self, *args, **kwargs): return _Resp()

    return _Client()


def _bps_error_client():
    """Client that raises on GET (simulates network or HTTP error)."""
    class _Client:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def get(self, *args, **kwargs):
            raise httpx.RequestError("connection failed")

    return _Client()


def test_fetch_building_permits_known_county_returns_int():
    """Parses flat-file CSV and sums 1u+2u+3-4u+5+ units for matching FIPS."""
    with patch("housing_policy_advisor.data.clients.census_client.httpx.Client",
               return_value=_bps_mock_client(_BPS_SAMPLE_TXT)):
        out = _fetch_building_permits_annual("51", "121")
    # 247 (1u) + 16 (2u) + 0 (3-4u) + 107 (5+) = 370
    assert isinstance(out, int)
    assert out == 370


def test_fetch_building_permits_unknown_county_returns_none():
    """Returns None when FIPS not present in flat file."""
    with patch("housing_policy_advisor.data.clients.census_client.httpx.Client",
               return_value=_bps_mock_client(_BPS_SAMPLE_TXT)):
        out = _fetch_building_permits_annual("99", "999")
    assert out is None


def test_fetch_building_permits_http_error_returns_none():
    """Returns None on network / HTTP error — never raises."""
    with patch("housing_policy_advisor.data.clients.census_client.httpx.Client",
               return_value=_bps_error_client()):
        out = _fetch_building_permits_annual("51", "121")
    assert out is None
