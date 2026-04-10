"""LLM policy recommendation output."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PolicyRecommendation:
    rank: int
    policy_name: str
    predicted_outcome: str
    confidence_score: float  # 0.0 to 1.0
    evidence_basis: List[str]  # RAG chunk citations
    comparable_communities: List[str]  # Communities with similar profiles
    implementation_timeline: str
    resource_requirements: str  # "Low" | "Medium" | "High"
    risks: List[str]
    validation_flags: List[str] = field(default_factory=list)  # Empty if all checks pass


@dataclass
class PolicyRecommendationsResult:
    """Batch result from the policy advisor pipeline."""

    recommendations: List[PolicyRecommendation]
    grounding_score: Optional[float] = None  # 0.0–1.0 when computed or supplied by LLM
