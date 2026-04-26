"""Tests for PolicyAdvisor.generate — mocks retrieval and Groq."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from housing_policy_advisor.llm.policy_advisor import PolicyAdvisor


_MINIMAL_RESPONSE = json.dumps({
    "locality": "Test County",
    "generated_date": "2026-01-01",
    "recommendations": [
        {
            "rank": 1,
            "policy_name": "Inclusionary Zoning",
            "predicted_outcome": "More affordable units.",
            "confidence_score": 0.8,
            "evidence_basis": ["Study A"],
            "implementation_timeline": "2 years",
            "resource_requirements": "Moderate",
            "risks": ["Developer resistance"],
            "validation_flags": [],
        },
        {
            "rank": 2,
            "policy_name": "Density Bonuses",
            "predicted_outcome": "Increased density near transit.",
            "confidence_score": 0.7,
            "evidence_basis": ["Study B"],
            "implementation_timeline": "1 year",
            "resource_requirements": "Low",
            "risks": ["Neighborhood opposition"],
            "validation_flags": [],
        },
        {
            "rank": 3,
            "policy_name": "Fee Waivers",
            "predicted_outcome": "Reduced development cost.",
            "confidence_score": 0.65,
            "evidence_basis": ["Report C"],
            "implementation_timeline": "6 months",
            "resource_requirements": "Low",
            "risks": ["Revenue loss"],
            "validation_flags": [],
        },
    ],
    "validation_summary": None,
})


def test_generate_success(mock_locality):
    chunks = [{"id": "c1", "text": "Evidence text", "metadata": {}, "distance": 0.2}]
    with patch("housing_policy_advisor.llm.policy_advisor.retrieve_chunks", return_value=chunks), \
         patch("housing_policy_advisor.llm.policy_advisor.complete_prefer_json", return_value=_MINIMAL_RESPONSE):
        result = PolicyAdvisor().generate(mock_locality)

    assert result.locality == "Test County"
    assert len(result.recommendations) == 3
    assert result.validation_summary is not None


def test_generate_rag_unavailable_flags(mock_locality):
    """When retriever raises, rag_unavailable flag added to each rec."""
    with patch("housing_policy_advisor.llm.policy_advisor.retrieve_chunks", side_effect=RuntimeError("no db")), \
         patch("housing_policy_advisor.llm.policy_advisor.complete_prefer_json", return_value=_MINIMAL_RESPONSE):
        result = PolicyAdvisor().generate(mock_locality)

    for rec in result.recommendations:
        assert "rag_unavailable" in rec.validation_flags


def test_generate_confidence_blended(mock_locality):
    """confidence_score should be avg of llm_conf and retrieval_confidence."""
    chunks = [{"id": "c1", "text": "t", "metadata": {}, "distance": 0.0}]
    with patch("housing_policy_advisor.llm.policy_advisor.retrieve_chunks", return_value=chunks), \
         patch("housing_policy_advisor.llm.policy_advisor.complete_prefer_json", return_value=_MINIMAL_RESPONSE):
        result = PolicyAdvisor().generate(mock_locality)

    # distance=0 → confidence=1.0; llm confidence for rec1=0.8 → blended=(0.8+1.0)/2=0.9
    assert result.recommendations[0].confidence_score == pytest.approx(0.9, abs=0.01)


def test_distance_to_confidence():
    adv = PolicyAdvisor()
    assert adv._distance_to_confidence(None) == 0.5
    assert adv._distance_to_confidence(0.0) == pytest.approx(1.0)
    assert adv._distance_to_confidence(1.0) == pytest.approx(0.5)
    assert adv._distance_to_confidence(9.0) == pytest.approx(0.1)
