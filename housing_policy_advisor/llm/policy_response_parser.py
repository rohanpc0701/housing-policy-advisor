"""Parse LLM JSON responses into policy recommendation models."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, List

from housing_policy_advisor.models.policy_output import (
    PolicyRecommendation,
    PolicyRecommendationsResult,
    ValidationSummary,
)


def _extract_json_text(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
        if m:
            return m.group(1).strip()
    return s


def parse_policy_recommendations_json(text: str) -> PolicyRecommendationsResult:
    payload = json.loads(_extract_json_text(text))
    if not isinstance(payload, dict):
        raise ValueError("Top-level JSON must be an object")

    recs_raw = payload.get("recommendations")
    if not isinstance(recs_raw, list):
        raise ValueError("Missing or invalid 'recommendations' array")

    recommendations: List[PolicyRecommendation] = []
    for i, item in enumerate(recs_raw):
        if not isinstance(item, dict):
            raise ValueError(f"recommendations[{i}] must be an object")
        recommendations.append(_dict_to_recommendation(item))

    locality = str(payload.get("locality", "")).strip() or "Unknown locality"
    generated_date = str(payload.get("generated_date", "")).strip() or date.today().isoformat()
    vs = payload.get("validation_summary") or {}
    validation_summary = ValidationSummary(
        grounding_score=float(vs.get("grounding_score", 0.0)),
        avg_confidence=float(vs.get("avg_confidence", 0.0)),
        completeness=float(vs.get("completeness", 0.0)),
        passed=bool(vs.get("passed", False)),
    )
    return PolicyRecommendationsResult(
        locality=locality,
        generated_date=generated_date,
        recommendations=recommendations,
        validation_summary=validation_summary,
    )


def _dict_to_recommendation(item: Dict[str, Any]) -> PolicyRecommendation:
    required = [
        "rank",
        "policy_name",
        "predicted_outcome",
        "confidence_score",
        "evidence_basis",
        "implementation_timeline",
        "resource_requirements",
        "risks",
    ]
    for k in required:
        if k not in item:
            raise ValueError(f"Missing required field: {k}")

    evidence_basis = item["evidence_basis"]
    if not isinstance(evidence_basis, list):
        raise ValueError("evidence_basis must be a list")

    risks = item["risks"]
    if not isinstance(risks, list):
        raise ValueError("risks must be a list")

    flags = item.get("validation_flags") or []
    if not isinstance(flags, list):
        raise ValueError("validation_flags must be a list")

    state_raw = item.get("state_of_implementation")
    state_of_implementation = str(state_raw).strip() if state_raw not in (None, "null", "") else None

    return PolicyRecommendation(
        rank=int(item["rank"]),
        policy_name=str(item["policy_name"]),
        predicted_outcome=str(item["predicted_outcome"]),
        confidence_score=float(item["confidence_score"]),
        evidence_basis=[str(x) for x in evidence_basis],
        implementation_timeline=str(item["implementation_timeline"]),
        resource_requirements=str(item["resource_requirements"]),
        risks=[str(x) for x in risks],
        state_of_implementation=state_of_implementation,
        validation_flags=[str(x) for x in flags],
    )


def policy_json_schema_instructions() -> str:
    return """Return ONLY valid JSON with this exact schema:
{
  "locality": "<string>",
  "generated_date": "<YYYY-MM-DD>",
  "recommendations": [
    {
      "rank": <integer>,
      "policy_name": "<string>",
      "predicted_outcome": "<string>",
      "confidence_score": <number between 0 and 1>,
      "evidence_basis": ["<RAG citation strings>"],
      "implementation_timeline": "<string>",
      "resource_requirements": "Low" | "Medium" | "High",
      "risks": ["<string>"],
      "state_of_implementation": "<state name or null>",
      "validation_flags": []
    }
  ],
  "validation_summary": {
    "grounding_score": <number 0..1>,
    "avg_confidence": <number 0..1>,
    "completeness": <number 0..1>,
    "passed": <true|false>
  }
}
No markdown, no prose, minimum 3 recommendations."""
