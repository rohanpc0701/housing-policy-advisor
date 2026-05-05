"""End-to-end pipeline orchestration."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, List, Optional

from housing_policy_advisor import config
from housing_policy_advisor.data.locality_profile import build_full_input
from housing_policy_advisor.llm.groq_client import get_model_name, get_provider_name
from housing_policy_advisor.llm.policy_advisor import PolicyAdvisor
from housing_policy_advisor.formatting import format_recommendations_narrative, format_recommendations_table
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_output import PolicyRecommendationsResult


def slugify_locality(locality_name: str, state_abbrev: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in locality_name).strip("_")
    return f"{cleaned}_{state_abbrev.lower().strip()}"


def to_json_tree(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: to_json_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_json_tree(v) for v in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return to_json_tree(asdict(obj))
    return obj


def build_locality_profile(
    *,
    locality_name: str,
    state_name: str,
    state_fips: str,
    county_fips: str,
    governance_form: str,
    hud_fips: Optional[str],
    housing_dept_present: Optional[bool],
    building_permits_annual: Optional[int],
) -> FullLocalityInput:
    return build_full_input(
        locality_name=locality_name,
        state_name=state_name,
        state_fips=state_fips,
        county_fips=county_fips,
        governance_form=governance_form,
        hud_fips=hud_fips,
        housing_dept_present=housing_dept_present,
        building_permits_annual=building_permits_annual,
        census_api_key=config.CENSUS_API_KEY,
        hud_token=config.HUD_API_TOKEN,
        bls_api_key=config.BLS_API_KEY,
    )


def generate_policy_recommendations(
    *,
    locality: FullLocalityInput,
    retrieval_k: int,
) -> PolicyRecommendationsResult:
    return PolicyAdvisor(retrieval_k=retrieval_k).generate(locality)


def run_full(
    *,
    locality_name: str,
    state_name: str,
    state_fips: str,
    county_fips: str,
    governance_form: str,
    state_abbr: str,
    hud_fips: Optional[str] = None,
    housing_dept_present: Optional[bool] = None,
    building_permits_annual: Optional[int] = None,
    retrieval_k: int = 15,
    output_format: str = "json",
    out_dir: Optional[Path] = None,
) -> List[Path]:
    if output_format not in {"json", "table", "narrative"}:
        raise ValueError("output_format must be one of: json, table, narrative")
    out_dir = out_dir or Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify_locality(locality_name, state_abbr)

    locality = build_locality_profile(
        locality_name=locality_name,
        state_name=state_name,
        state_fips=state_fips,
        county_fips=county_fips,
        governance_form=governance_form,
        hud_fips=hud_fips,
        housing_dept_present=housing_dept_present,
        building_permits_annual=building_permits_annual,
    )
    result = generate_policy_recommendations(locality=locality, retrieval_k=retrieval_k)
    payload = to_json_tree(result)
    payload["locality_profile"] = to_json_tree(locality)
    payload["metadata"] = {
        "llm_provider": get_provider_name(),
        "llm_model": get_model_name(),
    }

    json_path = out_dir / f"policy_recommendations_{slug}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    paths = [json_path]
    if output_format == "table":
        table_path = out_dir / f"policy_recommendations_{slug}.txt"
        table_path.write_text(format_recommendations_table(result), encoding="utf-8")
        paths.append(table_path)
    elif output_format == "narrative":
        narrative_path = out_dir / f"policy_recommendations_{slug}.txt"
        narrative_path.write_text(format_recommendations_narrative(result), encoding="utf-8")
        paths.append(narrative_path)
    return paths
