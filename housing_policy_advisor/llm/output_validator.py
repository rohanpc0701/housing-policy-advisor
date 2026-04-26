"""Validation helpers for structured policy advisor responses."""

from __future__ import annotations

from typing import List

from housing_policy_advisor import config
from housing_policy_advisor.models.policy_output import PolicyRecommendation, ValidationSummary


def compute_validation_summary(
    recommendations: List[PolicyRecommendation],
    *,
    grounding_score: float,
) -> ValidationSummary:
    if not recommendations:
        return ValidationSummary(
            grounding_score=max(0.0, min(1.0, grounding_score)),
            avg_confidence=0.0,
            completeness=0.0,
            passed=False,
        )

    clipped_grounding = max(0.0, min(1.0, grounding_score))
    avg_confidence = sum(max(0.0, min(1.0, r.confidence_score)) for r in recommendations) / len(recommendations)

    complete_items = 0
    for rec in recommendations:
        required_ok = all(
            [
                str(rec.policy_name).strip(),
                str(rec.predicted_outcome).strip(),
                str(rec.implementation_timeline).strip(),
                str(rec.resource_requirements).strip(),
                isinstance(rec.risks, list) and len(rec.risks) > 0 and all(str(r).strip() for r in rec.risks),
                isinstance(rec.evidence_basis, list) and len(rec.evidence_basis) > 0,
            ]
        )
        if required_ok:
            complete_items += 1
        if not required_ok and "incomplete_fields" not in rec.validation_flags:
            rec.validation_flags.append("incomplete_fields")
        if rec.confidence_score < config.CONFIDENCE_THRESHOLD and "very_low_confidence" not in rec.validation_flags:
            rec.validation_flags.append("very_low_confidence")

    completeness = complete_items / len(recommendations)
    passed = (
        len(recommendations) >= 5
        and clipped_grounding >= config.GROUNDING_THRESHOLD
        and avg_confidence >= config.CONFIDENCE_THRESHOLD
        and completeness >= 1.0
    )
    return ValidationSummary(
        grounding_score=clipped_grounding,
        avg_confidence=avg_confidence,
        completeness=completeness,
        passed=passed,
    )
