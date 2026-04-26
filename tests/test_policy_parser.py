"""Policy JSON parsing."""

import json

from housing_policy_advisor.llm.policy_response_parser import parse_policy_recommendations_json


def test_parse_policy_json_roundtrip():
    raw = json.dumps(
        {
            "locality": "Test County",
            "generated_date": "2026-04-16",
            "recommendations": [
                {
                    "rank": 1,
                    "policy_name": "Test policy",
                    "predicted_outcome": "Outcome.",
                    "confidence_score": 0.7,
                    "evidence_basis": ["[CHUNK_0] quote"],
                    "implementation_timeline": "1 year",
                    "resource_requirements": "Low",
                    "risks": ["Risk"],
                    "validation_flags": [],
                }
            ],
            "validation_summary": {
                "grounding_score": 0.9,
                "avg_confidence": 0.7,
                "completeness": 1.0,
                "passed": True,
            },
        }
    )
    result = parse_policy_recommendations_json(raw)
    assert result.validation_summary.grounding_score == 0.9
    assert len(result.recommendations) == 1
    assert result.recommendations[0].policy_name == "Test policy"
    assert result.recommendations[0].risks == ["Risk"]


def test_parse_fenced_json():
    text = """```json
{"locality": "L", "generated_date": "2026-04-16", "recommendations": [{"rank": 1, "policy_name": "P", "predicted_outcome": "O", "confidence_score": 0.6, "evidence_basis": ["e"], "implementation_timeline": "t", "resource_requirements": "Medium", "risks": ["r"], "validation_flags": []}], "validation_summary": {"grounding_score": 0.8, "avg_confidence": 0.6, "completeness": 1.0, "passed": true}}
```"""
    result = parse_policy_recommendations_json(text)
    assert result.recommendations[0].policy_name == "P"
    assert result.recommendations[0].risks == ["r"]
