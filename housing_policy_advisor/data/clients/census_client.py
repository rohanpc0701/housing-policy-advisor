"""
Census ACS 5-year API client for county-level housing and demographic fields.

Trend fields use 2017 vs 2022 ACS5 estimates: CAGR = (V_2022 / V_2017)^(1/5) - 1.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from housing_policy_advisor import config

logger = logging.getLogger(__name__)

# Census suppression / missing value sentinels
_SUPPRESSED = {-666666666, -666666666.0, -888888888, -999999999}


def _clean_int(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        v = int(float(raw))
    except (TypeError, ValueError):
        return None
    if v in _SUPPRESSED or v < 0:
        return None
    return v


def _clean_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v in _SUPPRESSED:
        return None
    return v


def _pct(numer: Optional[int], denom: Optional[int]) -> Optional[float]:
    if numer is None or denom is None or denom <= 0:
        return None
    return numer / denom


def _acs_url(year: int) -> str:
    return f"https://api.census.gov/data/{year}/acs/acs5"


def _get_row(
    client: httpx.Client,
    year: int,
    variables: List[str],
    state_fips: str,
    county_fips: str,
    api_key: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Fetch one county row; returns dict of var -> value string."""
    params: Dict[str, Any] = {
        "get": ",".join(variables),
        "for": f"county:{county_fips}",
        "in": f"state:{state_fips}",
    }
    if api_key:
        params["key"] = api_key
    url = _acs_url(year)
    try:
        r = client.get(url, params=params, timeout=60.0)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("ACS request failed for %s: %s", year, e)
        return None
    if not data or len(data) < 2:
        return None
    headers = data[0]
    row = data[1]
    return dict(zip(headers, row))


def fetch_acs_county_data(
    state_fips: str,
    county_fips: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pull ACS 5-year county estimates into keys matching FullLocalityInput fields.

    Returns a dict with only populated keys (merge into FullLocalityInput in locality_profile).
    """
    api_key = api_key or config.CENSUS_API_KEY
    out: Dict[str, Any] = {}

    # One request for current year: demographics, units, tenure, structure, year built, rent, burden
    vars_2022 = [
        "NAME",
        "B01003_001E",
        "B11001_001E",
        "B19013_001E",
        "B25001_001E",
        "B25002_001E",
        "B25002_002E",
        "B25002_003E",
        "B25003_001E",
        "B25003_002E",
        "B25003_003E",
        # B25024 units in structure
        "B25024_001E",
        "B25024_002E",
        "B25024_003E",
        "B25024_004E",
        "B25024_005E",
        "B25024_006E",
        "B25024_007E",
        "B25024_008E",
        "B25024_009E",
        "B25024_010E",
        # B25034 year structure built (2022 ACS layout)
        "B25034_001E",
        "B25034_002E",
        "B25034_003E",
        "B25034_004E",
        "B25034_005E",
        "B25034_006E",
        "B25034_007E",
        "B25034_008E",
        "B25034_009E",
        "B25034_010E",
        "B25034_011E",
        # B25064 median gross rent
        "B25064_001E",
        # B25070 gross rent as % of household income
        "B25070_001E",
        "B25070_007E",
        "B25070_008E",
        "B25070_009E",
        "B25070_010E",
    ]

    with httpx.Client() as client:
        row = _get_row(client, config.ACS_YEAR, vars_2022, state_fips, county_fips, api_key)
        row_2017 = _get_row(
            client,
            2017,
            ["B01003_001E", "B11001_001E"],
            state_fips,
            county_fips,
            api_key,
        )

    if not row:
        logger.warning("No ACS data for county state=%s county=%s", state_fips, county_fips)
        return out

    pop = _clean_int(row.get("B01003_001E"))
    hh = _clean_int(row.get("B11001_001E"))
    mhi = _clean_int(row.get("B19013_001E"))
    total_units = _clean_int(row.get("B25001_001E"))
    # B25002: 001E total units, 002E occupied, 003E vacant
    occ_total = _clean_int(row.get("B25002_001E"))
    _occupied = _clean_int(row.get("B25002_002E"))
    vacant = _clean_int(row.get("B25002_003E"))
    ten_total = _clean_int(row.get("B25003_001E"))
    owner = _clean_int(row.get("B25003_002E"))
    renter = _clean_int(row.get("B25003_003E"))

    out["population_estimate"] = pop
    out["household_estimate"] = hh
    out["median_household_income"] = mhi
    out["total_housing_units"] = total_units

    out["vacancy_rate"] = _pct(vacant, occ_total)  # vacant / total housing units
    out["homeownership_rate"] = _pct(owner, ten_total)

    # Structure types (B25024)
    b24_tot = _clean_int(row.get("B25024_001E"))
    detached = _clean_int(row.get("B25024_002E"))
    attached = _clean_int(row.get("B25024_003E"))
    u2 = _clean_int(row.get("B25024_004E"))
    u34 = _clean_int(row.get("B25024_005E"))
    u5_9 = _clean_int(row.get("B25024_006E"))
    u10_19 = _clean_int(row.get("B25024_007E"))
    u20_49 = _clean_int(row.get("B25024_008E"))
    u50p = _clean_int(row.get("B25024_009E"))
    mobile = _clean_int(row.get("B25024_010E"))

    if b24_tot and b24_tot > 0:
        out["pct_single_family_detached"] = detached / b24_tot if detached is not None else None
        out["pct_single_family_attached"] = attached / b24_tot if attached is not None else None
        mf_24 = (u2 or 0) + (u34 or 0)
        mf_5p = (u5_9 or 0) + (u10_19 or 0) + (u20_49 or 0) + (u50p or 0)
        out["pct_multifamily_2_4"] = mf_24 / b24_tot
        out["pct_multifamily_5plus"] = mf_5p / b24_tot
        out["pct_mobile_home"] = (mobile or 0) / b24_tot

    # Year built (B25034) — 2022 ACS5: 002=2020+, 003=2010–2019, 004=2000–2009, 005=1990–1999,
    # 006=1980–1989, 007=1970–1979, … 011=1939 or earlier
    y_tot = _clean_int(row.get("B25034_001E"))
    y_2020p = _clean_int(row.get("B25034_002E"))
    y_2010_2019 = _clean_int(row.get("B25034_003E"))
    y_2000_2009 = _clean_int(row.get("B25034_004E"))
    y_1990_1999 = _clean_int(row.get("B25034_005E"))
    y_1980_1989 = _clean_int(row.get("B25034_006E"))
    y_pre_1980 = sum(
        x or 0
        for x in (
            _clean_int(row.get("B25034_007E")),
            _clean_int(row.get("B25034_008E")),
            _clean_int(row.get("B25034_009E")),
            _clean_int(row.get("B25034_010E")),
            _clean_int(row.get("B25034_011E")),
        )
    )

    if y_tot and y_tot > 0:
        post_2000 = (y_2020p or 0) + (y_2010_2019 or 0) + (y_2000_2009 or 0)
        y80_99 = (y_1990_1999 or 0) + (y_1980_1989 or 0)
        out["pct_built_post_2000"] = post_2000 / y_tot
        out["pct_built_1980_1999"] = y80_99 / y_tot
        out["pct_built_pre_1980"] = y_pre_1980 / y_tot

    out["median_gross_rent"] = _clean_int(row.get("B25064_001E"))

    # Cost burden: renter-occupied paying cash rent with gross rent %; share with rent >= 30%
    b70_tot = _clean_int(row.get("B25070_001E"))
    b70_30_35 = _clean_int(row.get("B25070_007E"))
    b70_35_40 = _clean_int(row.get("B25070_008E"))
    b70_40_50 = _clean_int(row.get("B25070_009E"))
    b70_50p = _clean_int(row.get("B25070_010E"))
    if b70_tot and b70_tot > 0:
        burden_n = (b70_30_35 or 0) + (b70_35_40 or 0) + (b70_40_50 or 0) + (b70_50p or 0)
        out["cost_burden_rate"] = burden_n / b70_tot

    # CAGR 2017→2022 (5 years) for population and households
    if row_2017:
        pop17 = _clean_int(row_2017.get("B01003_001E"))
        hh17 = _clean_int(row_2017.get("B11001_001E"))
        if pop and pop17 and pop17 > 0 and pop > 0:
            out["avg_annual_population_rate_of_change"] = (pop / pop17) ** (1.0 / 5.0) - 1.0
        if hh and hh17 and hh17 > 0 and hh > 0:
            out["avg_annual_household_rate_of_change"] = (hh / hh17) ** (1.0 / 5.0) - 1.0

    return out
