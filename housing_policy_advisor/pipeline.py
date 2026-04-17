"""End-to-end pipeline orchestration."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from housing_policy_advisor.data.locality_profile import build_full_input
from housing_policy_advisor.llm.policy_advisor import PolicyAdvisor
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
    )


def generate_policy_recommendations(
    *,
    locality: FullLocalityInput,
    retrieval_k: int,
) -> PolicyRecommendationsResult:
    return PolicyAdvisor(retrieval_k=retrieval_k).generate(locality)


def _legacy_report_adapter(result: PolicyRecommendationsResult, locality: FullLocalityInput) -> Dict[str, Any]:
    rec_lines = []
    for rec in result.recommendations:
        rec_lines.append(
            f"Recommendation {rec.rank}: {rec.policy_name}\n"
            f"Outcome: {rec.predicted_outcome}\n"
            f"Timeline: {rec.implementation_timeline}\n"
            f"Resources: {rec.resource_requirements}\n"
            f"Risks: {rec.risks}\n"
            f"Evidence: {', '.join(rec.evidence_basis)}\n"
        )
    return {
        "locality_name": result.locality,
        "state": locality.state_name,
        "generated_date": result.generated_date,
        "housing_challenges": "Derived from structured locality profile and retrieved evidence.",
        "policy_recommendations": "\n\n".join(rec_lines),
        "validation_summary": asdict(result.validation_summary),
    }


def _try_render_legacy_outputs(
    *,
    output_format: str,
    result: PolicyRecommendationsResult,
    locality: FullLocalityInput,
    out_dir: Path,
    base_name: str,
) -> List[Path]:
    paths: List[Path] = []
    if output_format not in ("pdf", "docx", "all"):
        return paths
    try:
        from housing_policy_advisor.past_code.src.output.docx_generator import DOCXGenerator
        from housing_policy_advisor.past_code.src.output.pdf_generator import PDFGenerator
    except Exception:
        return paths

    legacy_payload = _legacy_report_adapter(result, locality)
    if output_format in ("pdf", "all"):
        pdf_path = out_dir / f"{base_name}.pdf"
        PDFGenerator().generate_pdf(legacy_payload, output_path=pdf_path)
        paths.append(pdf_path)
    if output_format in ("docx", "all"):
        docx_path = out_dir / f"{base_name}.docx"
        DOCXGenerator().generate_docx(legacy_payload, output_path=docx_path)
        paths.append(docx_path)
    return paths


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
    retrieval_k: int = 8,
    out_dir: Optional[Path] = None,
    output_format: str = "json",
) -> List[Path]:
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

    json_path = out_dir / f"policy_recommendations_{slug}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    written = [json_path]
    written.extend(
        _try_render_legacy_outputs(
            output_format=output_format,
            result=result,
            locality=locality,
            out_dir=out_dir,
            base_name=f"policy_recommendations_{slug}",
        )
    )
    return written
