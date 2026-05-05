"""Plain-text output formatting for demos and advisor review."""

from __future__ import annotations

from typing import Iterable, List

from housing_policy_advisor.models.classifier_output import PolicyClassificationResult
from housing_policy_advisor.models.policy_output import PolicyRecommendationsResult


def _clip(value: str, width: int) -> str:
    value = " ".join(str(value).split())
    if len(value) <= width:
        return value
    return value[: max(0, width - 3)].rstrip() + "..."


def _table(headers: List[str], rows: Iterable[List[str]]) -> str:
    materialized = list(rows)
    widths = [
        max(len(header), *(len(row[i]) for row in materialized)) if materialized else len(header)
        for i, header in enumerate(headers)
    ]
    header_line = " | ".join(header.ljust(widths[i]) for i, header in enumerate(headers))
    separator = " | ".join("-" * widths[i] for i in range(len(headers)))
    body = [" | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) for row in materialized]
    return "\n".join([header_line, separator, *body])


def format_recommendations_table(result: PolicyRecommendationsResult) -> str:
    """Format policy recommendations as a compact table."""
    rows: List[List[str]] = []
    for rec in result.recommendations:
        rows.append(
            [
                str(rec.rank),
                _clip(rec.policy_name, 30),
                _clip(rec.predicted_outcome, 42),
                _clip(rec.implementation_timeline, 18),
                f"{rec.confidence_score:.2f}",
                str(len(rec.evidence_basis)),
                _clip(rec.risks[0] if rec.risks else "", 28),
            ]
        )
    return _table(
        ["Rank", "Policy", "Expected outcome", "Timeline", "Confidence", "Evidence", "Key risk"],
        rows,
    )


def format_recommendations_narrative(result: PolicyRecommendationsResult) -> str:
    """Format the top recommendation as short narrative output."""
    if not result.recommendations:
        return "No policy recommendations were generated."
    top = sorted(result.recommendations, key=lambda rec: rec.rank)[0]
    evidence = ", ".join(top.evidence_basis[:3]) if top.evidence_basis else "no cited evidence"
    risk = top.risks[0] if top.risks else "No specific risk cited."
    return (
        f"Top recommendation for {result.locality}: {top.policy_name} "
        f"(confidence {top.confidence_score:.2f}). {top.predicted_outcome} "
        f"Evidence: {evidence}. Timeline: {top.implementation_timeline}. Key caveat: {risk}"
    )


def format_classifier_table(result: PolicyClassificationResult) -> str:
    """Format classifier output as a compact table."""
    note = result.disambiguation_notes[0] if result.disambiguation_notes else ""
    return _table(
        ["Predicted class", "Confidence", "Runner-up", "Evidence", "Disambiguation note"],
        [
            [
                result.predicted_policy_class or "ambiguous",
                f"{result.confidence:.2f}",
                result.runner_up or "",
                str(len(result.evidence_chunks)),
                _clip(note, 60),
            ]
        ],
    )


def format_classifier_narrative(result: PolicyClassificationResult) -> str:
    """Format classifier output as short narrative output."""
    predicted = result.predicted_policy_class or "ambiguous"
    evidence = result.evidence_chunks[0].chunk_id if result.evidence_chunks else "no classifier evidence"
    note = result.disambiguation_notes[0] if result.disambiguation_notes else "No disambiguation note."
    return (
        f"Classifier result: {predicted} with confidence {result.confidence:.2f}. "
        f"Primary evidence: {evidence}. {note}"
    )
