"""Build FullLocalityInput from Census, HUD, BLS, and CLI/manual fields."""

from __future__ import annotations

from dataclasses import asdict, fields
from typing import Any, Dict, Optional

from housing_policy_advisor.data.clients.bls_client import fetch_laus_county_data
from housing_policy_advisor.data.clients.census_client import fetch_acs_county_data
from housing_policy_advisor.data.clients.hud_client import fetch_hud_county_data
from housing_policy_advisor.models.locality_input import FullLocalityInput


def _mel_building_age_profile(inp: FullLocalityInput) -> Optional[Dict[str, float]]:
    """
    Four summary buckets: pre-1940; 1940-1960; 1970s-1980s; 1990+.
    ACS only gives 1980-1999 as one share; 1980-1984 is approximated as 5/20 of
    that bucket, combined with 1960-1979. Remainder of 1980-1999 plus 2000+ → 1990s_plus.
    """
    pre_40 = inp.pct_built_pre_1940
    d40_60 = inp.pct_built_1940_1959
    d60_79 = inp.pct_built_1960_1979
    d80_99 = inp.pct_built_1980_1999
    post_2000 = inp.pct_built_post_2000
    if any(x is None for x in (pre_40, d40_60, d60_79, d80_99, post_2000)):
        return None
    early_80s_share = 0.25 * d80_99
    return {
        "pre_1940": pre_40,
        "1940_1960": d40_60,
        "1970s_1980s": d60_79 + early_80s_share,
        "1990s_plus": 0.75 * d80_99 + post_2000,
    }


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

    result.building_age_profile = _mel_building_age_profile(result)
    return result
