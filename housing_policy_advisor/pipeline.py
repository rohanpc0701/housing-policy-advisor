"""Orchestrate locality input build, optional mock recommendations, and validation."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, List, Optional

from housing_policy_advisor.data.locality_profile import build_full_input
from housing_policy_advisor.llm import output_validator
from housing_policy_advisor.llm.groq_client import complete_prefer_json
from housing_policy_advisor.llm.policy_response_parser import parse_policy_recommendations_json
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_output import PolicyRecommendation, PolicyRecommendationsResult
from housing_policy_advisor.rag import retriever as rag_retriever
from housing_policy_advisor.rag.prompt_builder import build_policy_prompt, default_retrieval_query


def slugify_locality(locality_name: str, state_abbrev: str) -> str:
    """Normalized filename slug: montgomery_county_va."""
    return f"{re.sub(r'[^a-z0-9]+', '_', locality_name.lower()).strip('_')}_{state_abbrev.lower().strip()}"


def encode_json(obj: Any) -> Any:
    """JSON-serializable dict/list tree from dataclasses."""
    if is_dataclass(obj):
        return {k: encode_json(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: encode_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [encode_json(x) for x in obj]
    return obj


def run_input_only(
    *,
    locality_name: str,
    state_name: str,
    state_fips: str,
    county_fips: str,
    governance_form: str,
    has_housing_dept: Optional[bool] = None,
    housing_dept_name: Optional[str] = None,
    building_permits_trend: Optional[str] = None,
    building_permits_annual: Optional[int] = None,
    out_dir: Optional[Path] = None,
    state_abbr: str = "va",
    full_locality_input: Optional[FullLocalityInput] = None,
) -> Path:
    """Build FullLocalityInput (unless provided) and write locality_profile_{slug}.json."""
    fli = full_locality_input or build_full_input(
        locality_name=locality_name,
        state_name=state_name,
        state_fips=state_fips,
        county_fips=county_fips,
        governance_form=governance_form,
        has_housing_dept=has_housing_dept,
        housing_dept_name=housing_dept_name,
        building_permits_trend=building_permits_trend,
        building_permits_annual=building_permits_annual,
    )
    out_dir = out_dir or Path(".")
    slug = slugify_locality(locality_name, state_abbr)
    path = out_dir / f"locality_profile_{slug}.json"
    path.write_text(json.dumps(encode_json(fli), indent=2), encoding="utf-8")
    return path


def mock_policy_recommendations(locality: FullLocalityInput) -> List[PolicyRecommendation]:
    """Placeholder recommendations to exercise output_validator without Groq."""
    pop = locality.population_estimate or 0
    inc = locality.median_household_income or 0
    evidence = (
        f"Local context: population ~{pop}, median household income ~{inc}. "
        "Evidence chunk: inclusionary zoning case study (comparable mid-size county)."
    )
    return [
        PolicyRecommendation(
            rank=1,
            policy_name="Inclusionary zoning or linkage fee",
            predicted_outcome=(
                "The inclusionary zoning case study (comparable mid-size county) supports moderate "
                f"affordable unit production where population is near {pop} and median household income near {inc}. "
                f"Local context: population ~{pop}, median household income ~{inc}."
            ),
            confidence_score=0.72,
            evidence_basis=[evidence],
            comparable_communities=[
                f"Peer A, population {int(pop * 0.95)}, MHI {int(inc * 1.05)}",
                f"Peer B, population {int(pop * 1.08)}, MHI {int(inc * 0.92)}",
            ],
            implementation_timeline="2–4 years for ordinance adoption and early pipeline",
            resource_requirements="Medium",
            risks=["Political opposition", "Legal review"],
            validation_flags=[],
        )
    ]


def run_recommendations_pipeline(
    locality: FullLocalityInput,
    *,
    recommendations: Optional[List[PolicyRecommendation]] = None,
    rag_chunks: Optional[List[str]] = None,
    out_dir: Optional[Path] = None,
    state_abbr: str = "va",
    locality_name: str = "",
) -> Path:
    """Validate recommendations and write policy_recommendations_{slug}.json."""
    recs = recommendations if recommendations is not None else mock_policy_recommendations(locality)
    name = locality_name or locality.locality_name
    result: PolicyRecommendationsResult = output_validator.validate(recs, locality, rag_chunks=rag_chunks)
    out_dir = out_dir or Path(".")
    slug = slugify_locality(name, state_abbr)
    path = out_dir / f"policy_recommendations_{slug}.json"
    payload = {
        "locality": encode_json(locality),
        "grounding_score": result.grounding_score,
        "recommendations": encode_json(result.recommendations),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def run_llm_recommendations_pipeline(
    locality: FullLocalityInput,
    *,
    out_dir: Optional[Path] = None,
    state_abbr: str = "va",
    locality_name: str = "",
    retrieval_k: int = 8,
) -> Path:
    """Retrieve RAG chunks, call Groq, parse JSON, validate, and write policy JSON."""
    out_dir = out_dir or Path(".")
    name = locality_name or locality.locality_name
    q = default_retrieval_query(locality)
    chunk_rows = rag_retriever.retrieve_chunks(q, k=retrieval_k, locality=locality)
    texts = [str(c.get("text", "")) for c in chunk_rows if c.get("text")]
    ids = [str(c.get("id", f"idx_{i}")) for i, c in enumerate(chunk_rows)]

    prompt = build_policy_prompt(locality, texts, chunk_ids=ids)
    raw = complete_prefer_json([{"role": "user", "content": prompt}])
    parsed = parse_policy_recommendations_json(raw)
    result: PolicyRecommendationsResult = output_validator.validate(
        parsed.recommendations,
        locality,
        rag_chunks=texts,
        batch_grounding_score=parsed.grounding_score,
    )

    slug = slugify_locality(name, state_abbr)
    path = out_dir / f"policy_recommendations_{slug}.json"
    payload = {
        "locality": encode_json(locality),
        "grounding_score": result.grounding_score,
        "recommendations": encode_json(result.recommendations),
        "llm_mode": "groq_rag",
        "rag_chunk_count": len(texts),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def run_full(
    *,
    locality_name: str,
    state_name: str,
    state_fips: str,
    county_fips: str,
    governance_form: str,
    state_abbr: str,
    has_housing_dept: Optional[bool] = None,
    housing_dept_name: Optional[str] = None,
    building_permits_trend: Optional[str] = None,
    building_permits_annual: Optional[int] = None,
    input_only: bool = False,
    use_llm: bool = False,
    retrieval_k: int = 8,
    out_dir: Optional[Path] = None,
) -> List[Path]:
    """Build input; optionally write locality JSON only; else policy JSON (mock or Groq+RAG)."""
    fli = build_full_input(
        locality_name=locality_name,
        state_name=state_name,
        state_fips=state_fips,
        county_fips=county_fips,
        governance_form=governance_form,
        has_housing_dept=has_housing_dept,
        housing_dept_name=housing_dept_name,
        building_permits_trend=building_permits_trend,
        building_permits_annual=building_permits_annual,
    )
    paths: List[Path] = []
    out_dir = out_dir or Path(".")
    if input_only:
        p = run_input_only(
            locality_name=locality_name,
            state_name=state_name,
            state_fips=state_fips,
            county_fips=county_fips,
            governance_form=governance_form,
            has_housing_dept=has_housing_dept,
            housing_dept_name=housing_dept_name,
            building_permits_trend=building_permits_trend,
            building_permits_annual=building_permits_annual,
            out_dir=out_dir,
            state_abbr=state_abbr,
            full_locality_input=fli,
        )
        paths.append(p)
        return paths
    if use_llm:
        p2 = run_llm_recommendations_pipeline(
            fli,
            out_dir=out_dir,
            state_abbr=state_abbr,
            locality_name=locality_name,
            retrieval_k=retrieval_k,
        )
        paths.append(p2)
        return paths
    p2 = run_recommendations_pipeline(
        fli,
        out_dir=out_dir,
        state_abbr=state_abbr,
        locality_name=locality_name,
    )
    paths.append(p2)
    return paths
