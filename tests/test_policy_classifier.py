"""Tests for limited-scope policy classifier behavior."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from housing_policy_advisor.classifier import (
    AMBIGUOUS_QUERY,
    NO_CLASSIFIER_EVIDENCE,
    UNVALIDATED_CLASS_PREDICTION,
    classify_policy_query,
    disambiguate_policy_class,
)
from housing_policy_advisor.models.policy_class import SUPPORTED_POLICY_CLASSES, validate_policy_class


def test_policy_class_constants_validate_allowed_values():
    assert validate_policy_class("adu") == "adu"
    assert set(SUPPORTED_POLICY_CLASSES) == {"density_bonus", "adu", "affordable_dwelling_unit"}
    with pytest.raises(ValueError, match="Unsupported policy_class"):
        validate_policy_class("rent_assistance")


def test_disambiguate_accessory_dwelling_unit_favors_adu():
    predicted, notes, scores = disambiguate_policy_class("accessory dwelling unit backyard cottage ordinance")
    assert predicted == "adu"
    assert scores["adu"] > scores["affordable_dwelling_unit"]
    assert notes


def test_disambiguate_affordable_dwelling_unit_favors_affordable_class():
    predicted, notes, scores = disambiguate_policy_class(
        "affordable dwelling unit ordinance AMI set-aside developer requirement"
    )
    assert predicted == "affordable_dwelling_unit"
    assert scores["affordable_dwelling_unit"] > scores["adu"]
    assert notes


def test_disambiguate_dwelling_unit_ordinance_is_ambiguous():
    predicted, notes, _ = disambiguate_policy_class("dwelling unit ordinance")
    assert predicted is None
    assert any("ambiguous" in note.lower() for note in notes)


@patch("housing_policy_advisor.classifier.retrieve_classifier_chunks")
def test_classify_policy_query_returns_evidence_backed_result(mock_retrieve):
    mock_retrieve.return_value = [
        {
            "id": "implementation_toolkit_adu_abcd1234_p1_c0",
            "text": "Accessory dwelling units are secondary units on residential lots.",
            "metadata": {"source_file": "ADU Brief.pdf", "policy_class": "adu"},
            "distance": 0.2,
        }
    ]

    result = classify_policy_query("accessory dwelling unit owner occupancy", k=1)

    assert result.predicted_policy_class == "adu"
    assert result.confidence > 0
    assert UNVALIDATED_CLASS_PREDICTION not in result.validation_flags
    assert result.evidence_chunks[0].chunk_id == "implementation_toolkit_adu_abcd1234_p1_c0"
    mock_retrieve.assert_called_once()
    assert mock_retrieve.call_args.kwargs["policy_class"] == "adu"


@patch("housing_policy_advisor.classifier.retrieve_classifier_chunks")
def test_classify_policy_query_marks_ambiguous_query_low_confidence(mock_retrieve):
    mock_retrieve.return_value = []

    result = classify_policy_query("dwelling unit ordinance", k=1)

    assert result.predicted_policy_class is None
    assert AMBIGUOUS_QUERY in result.validation_flags
    assert result.confidence <= 0.45


@patch("housing_policy_advisor.classifier.retrieve_classifier_chunks")
def test_classify_clear_query_without_evidence_is_unvalidated(mock_retrieve):
    mock_retrieve.return_value = []

    result = classify_policy_query("accessory dwelling unit backyard cottage", k=1)

    assert result.predicted_policy_class is None
    assert result.confidence <= 0.40
    assert NO_CLASSIFIER_EVIDENCE in result.validation_flags
    assert UNVALIDATED_CLASS_PREDICTION in result.validation_flags
    assert any("No retrieved classifier evidence" in note for note in result.disambiguation_notes)
