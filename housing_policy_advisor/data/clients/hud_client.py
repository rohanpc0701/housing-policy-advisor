"""
HUD USER API: Fair Market Rents and Income Limits for a county entity.

Entity ID: {state_fips}{county_fips}99999 (10 digits), e.g. 5112199999 for Montgomery County, VA.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from housing_policy_advisor import config

logger = logging.getLogger(__name__)

HUD_BASE = "https://www.huduser.gov/hudapi/public"


def hud_entity_id(state_fips: str, county_fips: str) -> str:
    s = state_fips.zfill(2)
    c = county_fips.zfill(3)
    return f"{s}{c}99999"


def _pick_county_fmr_basicdata(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the aggregate row for FMR (non-zip or MSA-level row)."""
    basic = payload.get("basicdata")
    if not basic or not isinstance(basic, list):
        return None
    for row in basic:
        if not isinstance(row, dict):
            continue
        zc = str(row.get("zip_code", "")).strip().upper()
        if "MSA" in zc or zc in ("", "MSA LEVEL"):
            return row
    return basic[0] if basic else None


def _parse_fmr_row(row: Dict[str, Any], out: Dict[str, Any]) -> None:
    def _to_int(key: str) -> Optional[int]:
        v = row.get(key)
        if v is None or v == "":
            return None
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    out["fmr_1br"] = _to_int("One-Bedroom")
    out["fmr_2br"] = _to_int("Two-Bedroom")
    out["fmr_3br"] = _to_int("Three-Bedroom")


def _parse_il_response(data: Dict[str, Any], out: Dict[str, Any]) -> None:
    """Map HUD IL JSON to area_median_income and 4-person limits at 30/50/80% AMI."""
    mi = data.get("median_income") or data.get("medianIncome") or data.get("median")
    if mi is not None:
        try:
            out["area_median_income"] = int(float(str(mi).replace(",", "")))
        except (TypeError, ValueError):
            pass

    candidates: List[Any] = []
    for key in ("il_data", "income_limits", "data", "results", "il"):
        v = data.get(key)
        if isinstance(v, list):
            candidates.extend(v)
        elif isinstance(v, dict):
            candidates.append(v)

    four_person: Optional[Dict[str, Any]] = None
    for item in candidates:
        if not isinstance(item, dict):
            continue
        bp = item.get("bedrooms") or item.get("Bedrooms")
        ps = item.get("persons") or item.get("Persons") or item.get("person") or item.get("person_num")
        if str(bp) == "4" or str(ps) == "4":
            four_person = item
            break
    if four_person is None:
        for item in candidates:
            if isinstance(item, dict) and (
                "il30p" in item
                or "il50p" in item
                or "il80p" in item
                or "limit_30" in item
                or "very_low" in item
            ):
                four_person = item
                break

    def _get_limit(d: Dict[str, Any], *keys: str) -> Optional[int]:
        for k in keys:
            v = d.get(k)
            if v is not None and v != "":
                try:
                    return int(float(str(v).replace(",", "")))
                except (TypeError, ValueError):
                    continue
        return None

    if four_person:
        out["il_30pct_ami_4person"] = _get_limit(
            four_person,
            "il30p",
            "il30",
            "limit30",
            "limit_30pct",
            "very_low",
            "extremely_low",
            "il_very_low_income_4_person",
        )
        out["il_50pct_ami_4person"] = _get_limit(
            four_person,
            "il50p",
            "il50",
            "limit50",
            "limit_50pct",
            "low",
            "il_low_income_4_person",
        )
        out["il_80pct_ami_4person"] = _get_limit(
            four_person,
            "il80p",
            "il80",
            "limit80",
            "limit_80pct",
            "moderate",
            "il_moderate_income_4_person",
        )

    if out.get("il_30pct_ami_4person") is None:
        out["il_30pct_ami_4person"] = _get_limit(data, "il30p", "il30", "limit30_4")
    if out.get("il_50pct_ami_4person") is None:
        out["il_50pct_ami_4person"] = _get_limit(data, "il50p", "il50", "limit50_4")
    if out.get("il_80pct_ami_4person") is None:
        out["il_80pct_ami_4person"] = _get_limit(data, "il80p", "il80", "limit80_4")


def fetch_hud_county_data(
    state_fips: str,
    county_fips: str,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch FMR and Income Limits for a county entity.

    Returns dict keys aligned with FullLocalityInput HUD fields.
    """
    token = token or config.HUD_API_TOKEN
    out: Dict[str, Any] = {}
    if not token:
        logger.warning("HUD_API_TOKEN not set; skipping HUD requests")
        return out

    entity = hud_entity_id(state_fips, county_fips)
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client() as client:
        # FMR
        try:
            r = client.get(
                f"{HUD_BASE}/fmr/data/{entity}",
                headers=headers,
                params={"year": config.ACS_YEAR},
                timeout=60.0,
            )
            r.raise_for_status()
            fmr_json = r.json()
        except Exception as e:
            logger.warning("HUD FMR request failed: %s", e)
            fmr_json = {}

        if isinstance(fmr_json, dict) and isinstance(fmr_json.get("data"), dict):
            fmr_json = fmr_json["data"]
        row = _pick_county_fmr_basicdata(fmr_json) if isinstance(fmr_json, dict) else None
        if isinstance(row, dict):
            _parse_fmr_row(row, out)

        # Income Limits
        try:
            r2 = client.get(
                f"{HUD_BASE}/il/data/{entity}",
                headers=headers,
                params={"year": config.ACS_YEAR},
                timeout=60.0,
            )
            r2.raise_for_status()
            il_json = r2.json()
        except Exception as e:
            logger.warning("HUD IL request failed: %s", e)
            il_json = {}

    if isinstance(il_json, dict) and isinstance(il_json.get("data"), dict):
        il_json = il_json["data"]
    if isinstance(il_json, dict):
        _parse_il_response(il_json, out)

    return out
