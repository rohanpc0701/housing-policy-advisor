"""Tests for digestible output formatting."""

from __future__ import annotations

from housing_policy_advisor.formatting import (
    format_classifier_narrative,
    format_classifier_table,
    format_recommendations_narrative,
    format_recommendations_table,
)
from housing_policy_advisor.models.classifier_output import ClassifierEvidenceChunk, PolicyClassificationResult


def test_recommendations_table_contains_expected_columns(sample_policy_result):
    output = format_recommendations_table(sample_policy_result)
    assert "Rank" in output
    assert "Policy" in output
    assert "Confidence" in output
    assert "Evidence" in output


def test_recommendations_narrative_is_non_empty(sample_policy_result):
    output = format_recommendations_narrative(sample_policy_result)
    assert "Top recommendation" in output
    assert sample_policy_result.recommendations[0].policy_name in output


def test_classifier_table_contains_expected_columns():
    result = PolicyClassificationResult(
        predicted_policy_class="adu",
        confidence=0.82,
        runner_up="affordable_dwelling_unit",
        evidence_chunks=[],
        disambiguation_notes=["Query uses accessory dwelling unit terminology."],
        class_scores={"adu": 3.0},
    )
    output = format_classifier_table(result)
    assert "Predicted class" in output
    assert "Confidence" in output
    assert "Runner-up" in output
    assert "Evidence" in output


def test_classifier_narrative_includes_top_class():
    result = PolicyClassificationResult(
        predicted_policy_class="affordable_dwelling_unit",
        confidence=0.75,
        runner_up="density_bonus",
        evidence_chunks=[
            ClassifierEvidenceChunk(
                chunk_id="implementation_toolkit_wdu_abcd1234_p1_c0",
                source_file="wdu.pdf",
                policy_class="affordable_dwelling_unit",
                reason="metadata filter",
            )
        ],
        disambiguation_notes=["Query refers to affordability requirements."],
        class_scores={"affordable_dwelling_unit": 4.0},
    )
    output = format_classifier_narrative(result)
    assert "affordable_dwelling_unit" in output
    assert "implementation_toolkit_wdu_abcd1234_p1_c0" in output
