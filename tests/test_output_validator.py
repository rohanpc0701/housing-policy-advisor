"""Output validator behavior."""

from housing_policy_advisor.llm import output_validator
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_output import PolicyRecommendation


def _locality():
    return FullLocalityInput(
        locality_name="Test",
        state_name="VA",
        state_fips="51",
        county_fips="121",
        governance_form="county",
        population_estimate=100000,
        median_household_income=50000,
        vacancy_rate=0.20,
    )


def test_low_confidence_flag():
    rec = PolicyRecommendation(
        rank=1,
        policy_name="P",
        predicted_outcome="Outcome text here.",
        confidence_score=0.4,
        evidence_basis=["evidence"],
        comparable_communities=["Peer, population 95000, MHI 51000"],
        implementation_timeline="1y",
        resource_requirements="Low",
        risks=["r"],
    )
    result = output_validator.validate([rec], _locality())
    assert any("low_confidence" in f for f in result.recommendations[0].validation_flags)


def test_vacancy_consistency_flag():
    rec = PolicyRecommendation(
        rank=1,
        policy_name="P",
        predicted_outcome="We face a housing shortage and tight supply.",
        confidence_score=0.8,
        evidence_basis=["evidence"],
        comparable_communities=["Peer, population 95000, MHI 51000"],
        implementation_timeline="1y",
        resource_requirements="Low",
        risks=["r"],
    )
    result = output_validator.validate([rec], _locality())
    assert any("consistency_vacancy" in f for f in result.recommendations[0].validation_flags)
