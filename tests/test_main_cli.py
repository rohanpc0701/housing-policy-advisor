"""Tests for CLI mode-specific behavior."""

from __future__ import annotations

from unittest.mock import patch

from housing_policy_advisor.models.classifier_output import PolicyClassificationResult


def test_classifier_mode_skips_optional_api_key_warnings(capsys):
    from housing_policy_advisor.main import main

    result = PolicyClassificationResult(
        predicted_policy_class=None,
        confidence=0.0,
        runner_up=None,
        evidence_chunks=[],
        disambiguation_notes=["No retrieved classifier evidence was found."],
        class_scores={},
        validation_flags=["NO_CLASSIFIER_EVIDENCE"],
    )

    with patch("housing_policy_advisor.main.config.validate_optional_api_keys") as mock_validate, \
         patch("housing_policy_advisor.main.classify_policy_query", return_value=result):
        exit_code = main(["--classify-query", "accessory dwelling unit", "--format", "json"])

    assert exit_code == 0
    mock_validate.assert_not_called()
    assert "NO_CLASSIFIER_EVIDENCE" in capsys.readouterr().out
