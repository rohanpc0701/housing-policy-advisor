"""Policy JSON parsing."""

import json

from housing_policy_advisor.llm.policy_response_parser import parse_policy_recommendations_json


def test_parse_policy_json_roundtrip():
    raw = json.dumps(
        {
            "grounding_score": 0.9,
            "recommendations": [
                {
                    "rank": 1,
                    "policy_name": "Test policy",
                    "predicted_outcome": "Outcome.",
                    "confidence_score": 0.7,
                    "evidence_basis": ["[CHUNK_0] quote"],
                    "comparable_communities": ["Peer, population 100000, MHI 50000"],
                    "implementation_timeline": "1 year",
                    "resource_requirements": "Low",
                    "risks": ["Risk"],
                    "validation_flags": [],
                }
            ],
        }
    )
    result = parse_policy_recommendations_json(raw)
    assert result.grounding_score == 0.9
    assert len(result.recommendations) == 1
    assert result.recommendations[0].policy_name == "Test policy"


def test_parse_fenced_json():
    text = """```json
{"grounding_score": 0.8, "recommendations": [{"rank": 1, "policy_name": "P", "predicted_outcome": "O", "confidence_score": 0.6, "evidence_basis": ["e"], "comparable_communities": ["c"], "implementation_timeline": "t", "resource_requirements": "Medium", "risks": ["r"], "validation_flags": []}]}
```"""
    result = parse_policy_recommendations_json(text)
    assert result.recommendations[0].policy_name == "P"
