"""Limited-scope policy classifier prototype."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from housing_policy_advisor.models.classifier_output import (
    ClassifierEvidenceChunk,
    PolicyClassificationResult,
)
from housing_policy_advisor.models.policy_class import SUPPORTED_POLICY_CLASSES, validate_policy_class
from housing_policy_advisor.rag.retriever import retrieve_classifier_chunks

AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"
NO_CLASSIFIER_EVIDENCE = "NO_CLASSIFIER_EVIDENCE"
UNVALIDATED_CLASS_PREDICTION = "UNVALIDATED_CLASS_PREDICTION"

_CLASS_TERMS: Dict[str, tuple[str, ...]] = {
    "adu": (
        "accessory",
        "secondary unit",
        "garage conversion",
        "backyard cottage",
        "detached accessory",
        "owner occupancy",
    ),
    "affordable_dwelling_unit": (
        "affordable dwelling unit",
        "ami",
        "set-aside",
        "set aside",
        "developer requirement",
        "income-restricted",
        "below market",
        "ordinance",
    ),
    "density_bonus": (
        "density bonus",
        "floor area",
        "height bonus",
        "zoning bonus",
        "increased density",
    ),
}


def disambiguate_policy_class(query: str) -> tuple[Optional[str], List[str], Dict[str, float]]:
    """Classify clear class terminology and flag ambiguous dwelling-unit queries."""
    q = query.lower()
    scores = {klass: 0.0 for klass in SUPPORTED_POLICY_CLASSES}
    notes: List[str] = []

    for klass, terms in _CLASS_TERMS.items():
        scores[klass] += sum(1.0 for term in terms if term in q)

    if "accessory dwelling unit" in q or "adu" in q:
        scores["adu"] += 3.0
        notes.append("Query uses accessory dwelling unit terminology.")
    if "affordable dwelling unit" in q:
        scores["affordable_dwelling_unit"] += 3.0
        notes.append("Query uses affordable dwelling unit terminology.")
    if any(term in q for term in ("ami", "set-aside", "set aside", "developer requirement", "income-restricted")):
        scores["affordable_dwelling_unit"] += 2.0
        notes.append("Query refers to affordability requirements or income restrictions.")

    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_class, top_score = sorted_scores[0]
    runner_score = sorted_scores[1][1]

    if "dwelling unit ordinance" in q and top_score <= runner_score + 1.0:
        notes.append("Dwelling unit ordinance is ambiguous without accessory or affordability terms.")
        return None, notes, scores
    if top_score <= 0:
        notes.append("Query does not contain class-specific policy terms.")
        return None, notes, scores
    if runner_score > 0 and top_score <= runner_score + 1.0:
        notes.append("Top policy classes are too close to classify confidently.")
        return None, notes, scores

    return top_class, notes, scores


def _distance_to_score(distance: Any) -> float:
    if distance is None:
        return 0.5
    return max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, float(distance)))))


def _excerpt(text: str, max_chars: int = 240) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _evidence_reason(chunk: Dict[str, Any]) -> str:
    metadata = chunk.get("metadata") or {}
    policy_class = metadata.get("policy_class")
    return f"Retrieved by classifier metadata filter for {policy_class or 'unknown class'}."


def classify_policy_query(
    query: str,
    *,
    policy_class: Optional[str] = None,
    k: int = 5,
) -> PolicyClassificationResult:
    """Classify a policy query and return evidence-backed prototype output."""
    if not query.strip():
        raise ValueError("query must not be empty")
    requested_class = validate_policy_class(policy_class) if policy_class else None

    disambiguated_class, notes, term_scores = disambiguate_policy_class(query)
    retrieval_class = requested_class or disambiguated_class
    chunks = retrieve_classifier_chunks(query, policy_class=retrieval_class, k=k)

    evidence: List[ClassifierEvidenceChunk] = []
    metadata_counts: Counter[str] = Counter()
    retrieval_scores = {klass: 0.0 for klass in SUPPORTED_POLICY_CLASSES}

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        chunk_class = metadata.get("policy_class")
        if chunk_class in SUPPORTED_POLICY_CLASSES:
            metadata_counts[str(chunk_class)] += 1
            retrieval_scores[str(chunk_class)] += _distance_to_score(chunk.get("distance"))
        evidence.append(
            ClassifierEvidenceChunk(
                chunk_id=str(chunk.get("id", "")),
                source_file=str(metadata.get("source_file") or metadata.get("source") or "unknown"),
                policy_class=str(chunk_class) if chunk_class else None,
                reason=_evidence_reason(chunk),
                score=_distance_to_score(chunk.get("distance")),
                text_excerpt=_excerpt(str(chunk.get("text", ""))),
            )
        )

    combined_scores: Dict[str, float] = {}
    for klass in SUPPORTED_POLICY_CLASSES:
        combined_scores[klass] = round(term_scores.get(klass, 0.0) + retrieval_scores.get(klass, 0.0), 4)

    ranked = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
    predicted = requested_class or (ranked[0][0] if ranked and ranked[0][1] > 0 else disambiguated_class)
    runner_up = ranked[1][0] if len(ranked) > 1 else None

    flags: List[str] = []
    if not evidence:
        flags.append(NO_CLASSIFIER_EVIDENCE)
        flags.append(UNVALIDATED_CLASS_PREDICTION)
    if requested_class is None and disambiguated_class is None:
        flags.append(AMBIGUOUS_QUERY)
        predicted = None
    if not evidence:
        notes.append("No retrieved classifier evidence was found; any class signal is inferred from query terms only.")
        predicted = None

    total_score = sum(max(0.0, score) for score in combined_scores.values())
    top_score = combined_scores.get(predicted or "", 0.0)
    confidence = round(top_score / total_score, 4) if total_score > 0 and predicted else 0.0
    if NO_CLASSIFIER_EVIDENCE in flags:
        confidence = min(confidence, 0.4)
    if flags and AMBIGUOUS_QUERY in flags:
        confidence = min(confidence, 0.45)

    if requested_class:
        notes.append(f"Caller supplied policy_class={requested_class}; retrieval was metadata-filtered to that class.")
    elif disambiguated_class:
        notes.append(f"Query terminology favors {disambiguated_class}.")
    if metadata_counts:
        notes.append(f"Retrieved classifier evidence counts: {dict(metadata_counts)}.")

    return PolicyClassificationResult(
        predicted_policy_class=predicted,
        confidence=confidence,
        runner_up=runner_up,
        evidence_chunks=evidence,
        disambiguation_notes=notes,
        class_scores=combined_scores,
        validation_flags=flags,
    )
