"""BLS QCEW county annual average weekly wage."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from housing_policy_advisor import config

logger = logging.getLogger(__name__)

# BLS QCEW area API: annual county data
_QCEW_URL = "https://data.bls.gov/cew/data/api/{year}/a/area/{fips5}.json"

# agglvl_code 70 = county total, all ownerships, all industries
_TARGET_AGGLVL = "70"
_WEEKS_PER_YEAR = 52


def fetch_qcew_county_wages(
    state_fips: str,
    county_fips: str,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """Return ``wage_median`` (annual avg wage) for the county.

    wage_pct25/wage_pct75 are not available at county level from QCEW;
    they remain absent from the returned dict.
    """
    year = year or config.ACS_YEAR
    fips5 = state_fips.zfill(2) + county_fips.zfill(3)
    url = _QCEW_URL.format(year=year, fips5=fips5)

    try:
        with httpx.Client() as client:
            r = client.get(url, timeout=30.0)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("QCEW request failed for %s: %s", fips5, exc)
        return {}

    results = data.get("results") or {}
    area_records = results.get("area") or []
    if not isinstance(area_records, list):
        logger.warning("QCEW unexpected response shape for %s", fips5)
        return {}

    for rec in area_records:
        if not isinstance(rec, dict):
            continue
        if str(rec.get("agglvl_code", "")).strip() != _TARGET_AGGLVL:
            continue
        raw_wage = rec.get("avg_wkly_wage")
        if raw_wage is None:
            continue
        try:
            weekly = float(str(raw_wage).replace(",", ""))
        except (ValueError, TypeError):
            continue
        return {"wage_median": round(weekly * _WEEKS_PER_YEAR, 2)}

    logger.warning("QCEW: no agglvl_code=%s record found for %s", _TARGET_AGGLVL, fips5)
    return {}
