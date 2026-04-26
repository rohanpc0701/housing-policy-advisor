"""Structured policy advisor output models."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PolicyRecommendation:
    rank: int
    policy_name: str
    predicted_outcome: str
    confidence_score: float
    evidence_basis: List[str]
    implementation_timeline: str
    resource_requirements: str
    risks: List[str]
    state_of_implementation: Optional[str] = None
    validation_flags: List[str] = field(default_factory=list)


@dataclass
class ValidationSummary:
    grounding_score: float
    avg_confidence: float
    completeness: float
    passed: bool


@dataclass
class PolicyRecommendationsResult:
    locality: str
    generated_date: str
    recommendations: List[PolicyRecommendation]
    validation_summary: ValidationSummary
