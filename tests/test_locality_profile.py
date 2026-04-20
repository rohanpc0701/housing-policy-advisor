"""Tests for locality_profile.build_full_input — mocks API clients."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from housing_policy_advisor.data.locality_profile import build_full_input, _merge_dataclass
from housing_policy_advisor.models.locality_input import FullLocalityInput


def test_build_full_input_merges_census(mock_locality):
    census_data = {"population_estimate": 99999, "median_household_income": 70000}
    with patch("housing_policy_advisor.data.locality_profile.fetch_acs_county_data", return_value=census_data), \
         patch("housing_policy_advisor.data.locality_profile.fetch_hud_county_data", return_value={}), \
         patch("housing_policy_advisor.data.locality_profile.fetch_laus_county_data", return_value={}):
        result = build_full_input(
            locality_name="Test County",
            state_name="Virginia",
            state_fips="51",
            county_fips="001",
            governance_form="county",
        )

    assert result.population_estimate == 99999
    assert result.median_household_income == 70000


def test_manual_overrides_api(mock_locality):
    census_data = {"building_permits_annual": 500, "housing_dept_present": False}
    with patch("housing_policy_advisor.data.locality_profile.fetch_acs_county_data", return_value=census_data), \
         patch("housing_policy_advisor.data.locality_profile.fetch_hud_county_data", return_value={}), \
         patch("housing_policy_advisor.data.locality_profile.fetch_laus_county_data", return_value={}):
        result = build_full_input(
            locality_name="Test County",
            state_name="Virginia",
            state_fips="51",
            county_fips="001",
            governance_form="county",
            housing_dept_present=True,
            building_permits_annual=1200,
        )

    assert result.housing_dept_present is True
    assert result.building_permits_annual == 1200


def test_none_values_ignored_in_merge():
    census_data = {"population_estimate": None, "median_household_income": 60000}
    with patch("housing_policy_advisor.data.locality_profile.fetch_acs_county_data", return_value=census_data), \
         patch("housing_policy_advisor.data.locality_profile.fetch_hud_county_data", return_value={}), \
         patch("housing_policy_advisor.data.locality_profile.fetch_laus_county_data", return_value={}):
        result = build_full_input(
            locality_name="Test",
            state_name="VA",
            state_fips="51",
            county_fips="001",
            governance_form="county",
        )

    assert result.population_estimate is None
    assert result.median_household_income == 60000


def test_merge_dataclass_applies_non_none():
    base = FullLocalityInput(
        locality_name="A",
        state_name="VA",
        state_fips="51",
        county_fips="001",
        governance_form="county",
        population_estimate=50000,
    )
    updated = _merge_dataclass(base, {"population_estimate": 99000, "median_gross_rent": None})
    assert updated.population_estimate == 99000
    assert updated.median_gross_rent is None


def test_api_failure_returns_partial():
    """If all clients return empty dicts, base fields preserved."""
    with patch("housing_policy_advisor.data.locality_profile.fetch_acs_county_data", return_value={}), \
         patch("housing_policy_advisor.data.locality_profile.fetch_hud_county_data", return_value={}), \
         patch("housing_policy_advisor.data.locality_profile.fetch_laus_county_data", return_value={}):
        result = build_full_input(
            locality_name="Fallback Town",
            state_name="Virginia",
            state_fips="51",
            county_fips="999",
            governance_form="city",
        )

    assert result.locality_name == "Fallback Town"
    assert result.population_estimate is None
