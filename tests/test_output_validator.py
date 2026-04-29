"""Output validator behavior for new structured schema."""

from housing_policy_advisor.llm.output_validator import (
    BAD_COMPARABLE,
    INCOMPLETE,
    LOW_CONFIDENCE,
    LOW_GROUNDING,
    compute_validation_summary,
)
from housing_policy_advisor.models.policy_output import ComparableCommunity, PolicyRecommendation


def _rec(**overrides):
    values = {
        "rank": 1,
        "policy_name": "P",
        "predicted_outcome": "Outcome text here.",
        "confidence_score": 0.8,
        "evidence_basis": ["evidence"],
        "implementation_timeline": "1y",
        "resource_requirements": "Low",
        "risks": ["Risk"],
        "comparable_communities": [
            ComparableCommunity(
                name="Comparable City, VA",
                population=95_000,
                median_household_income=63_000,
            )
        ],
    }
    values.update(overrides)
    return PolicyRecommendation(**values)


def test_summary_flags_low_confidence():
    rec = _rec(confidence_score=0.2)
    summary = compute_validation_summary([rec], grounding_score=0.8)
    assert LOW_CONFIDENCE in rec.validation_flags
    assert summary.avg_confidence == 0.2


def test_summary_requires_minimum_five_recommendations():
    recs = [
        _rec(
            rank=i + 1,
            policy_name=f"P{i}",
            predicted_outcome="Outcome",
            confidence_score=0.8,
            evidence_basis=["evidence"],
            implementation_timeline="1y",
            resource_requirements="Low",
            risks=["Risk"],
        )
        for i in range(2)
    ]
    summary = compute_validation_summary(recs, grounding_score=0.9)
    assert summary.passed is False


def test_summary_flags_low_grounding_on_each_recommendation():
    recs = [_rec(rank=i + 1) for i in range(5)]
    summary = compute_validation_summary(recs, grounding_score=0.2)

    assert summary.grounding_score == 0.2
    assert summary.passed is False
    assert all(LOW_GROUNDING in rec.validation_flags for rec in recs)


def test_summary_flags_incomplete_fields():
    rec = _rec(evidence_basis=[])
    summary = compute_validation_summary([rec], grounding_score=0.9)

    assert INCOMPLETE in rec.validation_flags
    assert summary.completeness == 0.0


def test_summary_does_not_duplicate_flags():
    rec = _rec(confidence_score=0.2, validation_flags=[LOW_CONFIDENCE])
    compute_validation_summary([rec], grounding_score=0.2)
    compute_validation_summary([rec], grounding_score=0.2)

    assert rec.validation_flags.count(LOW_CONFIDENCE) == 1
    assert rec.validation_flags.count(LOW_GROUNDING) == 1


def test_summary_accepts_comparable_within_population_and_income_tolerance():
    recs = [_rec(rank=i + 1) for i in range(5)]
    summary = compute_validation_summary(
        recs,
        grounding_score=0.9,
        target_population=100_000,
        target_median_household_income=65_000,
    )

    assert summary.passed is True
    assert all(BAD_COMPARABLE not in rec.validation_flags for rec in recs)


def test_summary_flags_bad_comparable_population_outlier():
    rec = _rec(
        comparable_communities=[
            ComparableCommunity(
                name="Too Large, VA",
                population=150_000,
                median_household_income=65_000,
            )
        ]
    )
    summary = compute_validation_summary(
        [rec],
        grounding_score=0.9,
        target_population=100_000,
        target_median_household_income=65_000,
    )

    assert BAD_COMPARABLE in rec.validation_flags
    assert summary.passed is False


def test_summary_flags_bad_comparable_income_outlier():
    rec = _rec(
        comparable_communities=[
            ComparableCommunity(
                name="Too Wealthy, VA",
                population=100_000,
                median_household_income=90_000,
            )
        ]
    )
    compute_validation_summary(
        [rec],
        grounding_score=0.9,
        target_population=100_000,
        target_median_household_income=65_000,
    )

    assert BAD_COMPARABLE in rec.validation_flags


def test_summary_flags_bad_comparable_invalid_metrics():
    rec = _rec(
        comparable_communities=[
            ComparableCommunity(
                name="",
                population=0,
                median_household_income=0,
            )
        ]
    )
    compute_validation_summary(
        [rec],
        grounding_score=0.9,
        target_population=100_000,
        target_median_household_income=65_000,
    )

    assert BAD_COMPARABLE in rec.validation_flags


def test_summary_skips_comparable_check_when_target_metrics_missing():
    rec = _rec(
        comparable_communities=[
            ComparableCommunity(
                name="Far Away, VA",
                population=1_000_000,
                median_household_income=200_000,
            )
        ]
    )
    compute_validation_summary([rec], grounding_score=0.9)

    assert BAD_COMPARABLE not in rec.validation_flags
