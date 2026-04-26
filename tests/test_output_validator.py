"""Output validator behavior for new structured schema."""

from housing_policy_advisor.llm.output_validator import compute_validation_summary
from housing_policy_advisor.models.policy_output import PolicyRecommendation


def test_summary_flags_low_confidence():
    rec = PolicyRecommendation(
        rank=1,
        policy_name="P",
        predicted_outcome="Outcome text here.",
        confidence_score=0.2,
        evidence_basis=["evidence"],
        implementation_timeline="1y",
        resource_requirements="Low",
        risks=["Risk"],
    )
    summary = compute_validation_summary([rec], grounding_score=0.8)
    assert any("very_low_confidence" in f for f in rec.validation_flags)
    assert summary.avg_confidence == 0.2


def test_summary_requires_minimum_five_recommendations():
    recs = [
        PolicyRecommendation(
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
