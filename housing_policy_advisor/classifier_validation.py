"""Lightweight qualitative validation report for classifier demos."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from housing_policy_advisor.models.classifier_output import PolicyClassificationResult
from housing_policy_advisor.models.policy_class import SUPPORTED_POLICY_CLASSES, validate_policy_class


@dataclass
class ClassifierValidationRow:
    policy_class: str
    example_document: str
    ground_truth_components: List[str]
    ai_generated_components: List[str]
    alignment: str
    evidence: List[str]


def load_expected_components(path: Path) -> Dict[str, Dict[str, object]]:
    """
    Load classifier validation expectations from JSON.

    The repo does not currently include hand-labeled ground-truth components.
    This loader fails clearly instead of inventing validation labels.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Classifier validation expectations not found: {path}. "
            "Create a JSON file keyed by policy_class with example_document and components fields."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Classifier validation expectations must be a JSON object keyed by policy_class")
    return payload


def build_validation_report(
    results: Dict[str, PolicyClassificationResult],
    expected_components: Dict[str, Dict[str, object]],
) -> List[ClassifierValidationRow]:
    """Compare classifier outputs with manually supplied example-document expectations."""
    rows: List[ClassifierValidationRow] = []
    for policy_class in SUPPORTED_POLICY_CLASSES:
        validate_policy_class(policy_class)
        expected = expected_components.get(policy_class)
        if not expected:
            continue

        components_raw = expected.get("components", [])
        if not isinstance(components_raw, list):
            raise ValueError(f"{policy_class}.components must be a list")
        ground_truth = [str(item) for item in components_raw]

        result = results.get(policy_class)
        ai_components = result.disambiguation_notes if result else []
        evidence = [chunk.chunk_id for chunk in result.evidence_chunks] if result else []
        overlap = sum(
            1
            for component in ground_truth
            if any(component.lower() in note.lower() for note in ai_components)
        )
        ratio = overlap / len(ground_truth) if ground_truth else 0.0
        alignment = "High" if ratio >= 0.67 else "Medium" if ratio >= 0.34 else "Low"

        rows.append(
            ClassifierValidationRow(
                policy_class=policy_class,
                example_document=str(expected.get("example_document", "unknown")),
                ground_truth_components=ground_truth,
                ai_generated_components=ai_components,
                alignment=alignment,
                evidence=evidence,
            )
        )
    return rows
