"""Parse Groq/LLM responses into PolicyRecommendationsResult (strict JSON contract)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from housing_policy_advisor.models.policy_output import PolicyRecommendation, PolicyRecommendationsResult


def _extract_json_text(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s)
        if m:
            return m.group(1).strip()
    return s


def parse_policy_recommendations_json(text: str) -> PolicyRecommendationsResult:
    """
    Parse JSON object with:
    - ``grounding_score`` (optional float 0–1)
    - ``recommendations`` (array of recommendation objects)

    Each recommendation must include:
    rank, policy_name, predicted_outcome, confidence_score,
    evidence_basis, comparable_communities, implementation_timeline,
    resource_requirements, risks
    """
    payload = json.loads(_extract_json_text(text))
    if not isinstance(payload, dict):
        raise ValueError("Top-level JSON must be an object")

    g = payload.get("grounding_score")
    grounding_score = float(g) if g is not None else None

    recs_raw = payload.get("recommendations")
    if not isinstance(recs_raw, list):
        raise ValueError("Missing or invalid 'recommendations' array")

    out: List[PolicyRecommendation] = []
    for i, item in enumerate(recs_raw):
        if not isinstance(item, dict):
            raise ValueError(f"recommendations[{i}] must be an object")
        rec = _dict_to_recommendation(item)
        out.append(rec)

    return PolicyRecommendationsResult(recommendations=out, grounding_score=grounding_score)


def _dict_to_recommendation(item: Dict[str, Any]) -> PolicyRecommendation:
    required = [
        "rank",
        "policy_name",
        "predicted_outcome",
        "confidence_score",
        "evidence_basis",
        "comparable_communities",
        "implementation_timeline",
        "resource_requirements",
        "risks",
    ]
    for k in required:
        if k not in item:
            raise ValueError(f"Missing required field: {k}")

    flags = item.get("validation_flags")
    if flags is None:
        flags = []
    if not isinstance(flags, list):
        raise ValueError("validation_flags must be a list")

    eb = item["evidence_basis"]
    cc = item["comparable_communities"]
    risks = item["risks"]
    if not isinstance(eb, list) or not isinstance(cc, list) or not isinstance(risks, list):
        raise ValueError("evidence_basis, comparable_communities, and risks must be arrays")

    return PolicyRecommendation(
        rank=int(item["rank"]),
        policy_name=str(item["policy_name"]),
        predicted_outcome=str(item["predicted_outcome"]),
        confidence_score=float(item["confidence_score"]),
        evidence_basis=[str(x) for x in eb],
        comparable_communities=[str(x) for x in cc],
        implementation_timeline=str(item["implementation_timeline"]),
        resource_requirements=str(item["resource_requirements"]),
        risks=[str(x) for x in risks],
        validation_flags=[str(x) for x in flags],
    )


def policy_json_schema_instructions() -> str:
    """Prompt text describing the required JSON shape for the LLM."""
    return """Return a single JSON object (no markdown) with this exact structure:
{
  "grounding_score": <number between 0 and 1, your estimate of how well claims are supported by evidence>,
  "recommendations": [
    {
      "rank": <integer>,
      "policy_name": "<string>",
      "predicted_outcome": "<string>",
      "confidence_score": <number between 0 and 1>,
      "evidence_basis": ["<cite evidence using chunk ids or short quotes from the evidence blocks>"],
      "comparable_communities": ["<name or 'Name, population N pop, MHI M' format>"],
      "implementation_timeline": "<string>",
      "resource_requirements": "Low" | "Medium" | "High",
      "risks": ["<string>"],
      "validation_flags": []
    }
  ]
}
Use empty array for validation_flags unless you need to note issues."""

