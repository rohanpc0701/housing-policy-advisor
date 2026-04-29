"""Validation helpers for structured policy advisor responses."""

from __future__ import annotations

from typing import List

from housing_policy_advisor import config
from housing_policy_advisor.models.policy_output import PolicyRecommendation, ValidationSummary

LOW_GROUNDING = "LOW_GROUNDING"
LOW_CONFIDENCE = "LOW_CONFIDENCE"
INCOMPLETE = "INCOMPLETE"
BAD_COMPARABLE = "BAD_COMPARABLE"


def _append_flag(flags: List[str], flag: str) -> None:
    if flag not in flags:
        flags.append(flag)


def _relative_difference(value: int | float, target: int | float) -> float:
    if target <= 0:
        return float("inf")
    return abs(float(value) - float(target)) / float(target)


def _has_bad_comparable(
    rec: PolicyRecommendation,
    *,
    target_population: int | None,
    target_median_household_income: int | None,
) -> bool:
    if target_population is None or target_median_household_income is None:
        return False

    for community in rec.comparable_communities:
        if not str(community.name).strip():
            return True
        if community.population <= 0 or community.median_household_income <= 0:
            return True
        if _relative_difference(community.population, target_population) > config.POPULATION_MATCH_TOLERANCE:
            return True
        if (
            _relative_difference(community.median_household_income, target_median_household_income)
            > config.INCOME_MATCH_TOLERANCE
        ):
            return True
    return False


def compute_validation_summary(
    recommendations: List[PolicyRecommendation],
    *,
    grounding_score: float,
    target_population: int | None = None,
    target_median_household_income: int | None = None,
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
    has_low_grounding = clipped_grounding < config.GROUNDING_THRESHOLD

    complete_items = 0
    has_bad_comparable = False
    for rec in recommendations:
        required_ok = all(
            [
                str(rec.policy_name).strip(),
                str(rec.predicted_outcome).strip(),
                str(rec.implementation_timeline).strip(),
                str(rec.resource_requirements).strip(),
                isinstance(rec.risks, list) and len(rec.risks) > 0 and all(str(r).strip() for r in rec.risks),
                isinstance(rec.comparable_communities, list) and len(rec.comparable_communities) > 0,
                isinstance(rec.evidence_basis, list) and len(rec.evidence_basis) > 0,
            ]
        )
        if required_ok:
            complete_items += 1
        if has_low_grounding:
            _append_flag(rec.validation_flags, LOW_GROUNDING)
        if not required_ok:
            _append_flag(rec.validation_flags, INCOMPLETE)
        if rec.confidence_score < config.CONFIDENCE_THRESHOLD:
            _append_flag(rec.validation_flags, LOW_CONFIDENCE)
        if _has_bad_comparable(
            rec,
            target_population=target_population,
            target_median_household_income=target_median_household_income,
        ):
            has_bad_comparable = True
            _append_flag(rec.validation_flags, BAD_COMPARABLE)

    completeness = complete_items / len(recommendations)
    passed = (
        len(recommendations) >= 5
        and clipped_grounding >= config.GROUNDING_THRESHOLD
        and avg_confidence >= config.CONFIDENCE_THRESHOLD
        and completeness >= 1.0
        and not has_bad_comparable
    )
    return ValidationSummary(
        grounding_score=clipped_grounding,
        avg_confidence=avg_confidence,
        completeness=completeness,
        passed=passed,
    )
