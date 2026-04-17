"""Build FullLocalityInput from Census, HUD, BLS, and CLI/manual fields."""

from __future__ import annotations

from dataclasses import asdict, fields
from typing import Any, Dict, Optional

from housing_policy_advisor.data.clients.bls_client import fetch_laus_county_data
from housing_policy_advisor.data.clients.census_client import fetch_acs_county_data
from housing_policy_advisor.data.clients.hud_client import fetch_hud_county_data
from housing_policy_advisor.models.locality_input import FullLocalityInput


def _merge_dataclass(base: FullLocalityInput, updates: Dict[str, Any]) -> FullLocalityInput:
    """Apply non-None keys from updates onto a copy of base."""
    d = asdict(base)
    for k, v in updates.items():
        if k in d and v is not None:
            d[k] = v
    return FullLocalityInput(**d)


def build_full_input(
    locality_name: str,
    state_name: str,
    state_fips: str,
    county_fips: str,
    governance_form: str,
    hud_fips: Optional[str] = None,
    housing_dept_present: Optional[bool] = None,
    building_permits_annual: Optional[int] = None,
    census_api_key: Optional[str] = None,
    hud_token: Optional[str] = None,
    bls_api_key: Optional[str] = None,
) -> FullLocalityInput:
    """
    Call Census, HUD, and BLS clients and merge into FullLocalityInput.

    Manual fields override/fill gaps from APIs.
    """
    census = fetch_acs_county_data(state_fips, county_fips, census_api_key)
    hud = fetch_hud_county_data(state_fips, county_fips, hud_fips=hud_fips, token=hud_token)
    bls = fetch_laus_county_data(state_fips, county_fips, bls_api_key)

    merged: Dict[str, Any] = {}
    merged.update(census)
    merged.update(hud)
    merged.update(bls)

    base = FullLocalityInput(
        locality_name=locality_name,
        state_name=state_name,
        state_fips=state_fips,
        county_fips=county_fips,
        governance_form=governance_form,
        hud_fips=hud_fips,
        housing_dept_present=housing_dept_present,
        building_permits_annual=building_permits_annual,
    )

    # Only set keys that exist on FullLocalityInput
    allowed = {f.name for f in fields(FullLocalityInput)}
    filtered = {k: v for k, v in merged.items() if k in allowed and v is not None}
    result = _merge_dataclass(base, filtered)

    # Manual overrides (explicit non-None wins)
    if housing_dept_present is not None:
        result.housing_dept_present = housing_dept_present
    if building_permits_annual is not None:
        result.building_permits_annual = building_permits_annual

    return result
