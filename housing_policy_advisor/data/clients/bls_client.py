"""
BLS LAUS county series: unemployment rate and employment level.

Series: LAUCN{SS}{CCC}00000000{measure}
  SS = state FIPS 2 digits, CCC = county FIPS 3 digits
  measure 3 = unemployment rate (percent, e.g. 3.2)
  measure 5 = employment
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from housing_policy_advisor import config

logger = logging.getLogger(__name__)

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def _laus_series_id(state_fips: str, county_fips: str, measure: int) -> str:
    s = state_fips.zfill(2)
    c = county_fips.zfill(3)
    return f"LAUCN{s}{c}00000000{measure}"


def _pick_latest(data: list) -> Optional[Dict[str, Any]]:
    if not data:
        return None
    for row in data:
        if row.get("latest") == "true":
            return row
    return data[0]


def fetch_laus_county_data(
    state_fips: str,
    county_fips: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Latest unemployment rate (0.0–1.0 fraction) and employment count for the county.
    """
    api_key = api_key or config.BLS_API_KEY
    out: Dict[str, Any] = {}
    if not api_key:
        logger.warning("BLS_API_KEY not set; skipping BLS requests")
        return out

    s3 = _laus_series_id(state_fips, county_fips, 3)
    s5 = _laus_series_id(state_fips, county_fips, 5)

    body = {
        "seriesid": [s3, s5],
        "registrationKey": api_key,
        "calculations": False,
        "annualaverage": False,
    }

    try:
        with httpx.Client() as client:
            r = client.post(BLS_URL, json=body, timeout=60.0)
            r.raise_for_status()
            payload = r.json()
    except Exception as e:
        logger.warning("BLS request failed: %s", e)
        return out

    if payload.get("status") != "REQUEST_SUCCEEDED":
        logger.warning("BLS API status: %s", payload.get("message"))
        return out

    results_list = payload.get("Results") or {}
    series_list = results_list.get("series") or []

    for ser in series_list:
        sid = ser.get("seriesID") or ser.get("seriesId")
        data = ser.get("data") or []
        obs = _pick_latest(data)
        if not obs:
            continue
        val = obs.get("value")
        try:
            fval = float(val)
        except (TypeError, ValueError):
            continue
        if sid == s3:
            # BLS publishes unemployment as a percent (e.g. 3.2); store as fraction
            out["unemployment_rate"] = fval / 100.0
        elif sid == s5:
            out["regional_employment_estimate"] = int(round(fval))

    return out
