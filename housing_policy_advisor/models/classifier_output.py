"""Structured output models for policy-class classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ClassifierEvidenceChunk:
    chunk_id: str
    source_file: str
    policy_class: Optional[str]
    reason: str
    score: Optional[float] = None
    text_excerpt: Optional[str] = None


@dataclass
class PolicyClassificationResult:
    predicted_policy_class: Optional[str]
    confidence: float
    runner_up: Optional[str]
    evidence_chunks: List[ClassifierEvidenceChunk]
    disambiguation_notes: List[str]
    class_scores: Dict[str, float]
    validation_flags: List[str] = field(default_factory=list)
