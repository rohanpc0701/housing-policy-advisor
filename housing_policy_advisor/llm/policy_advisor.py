"""Policy advisor that combines RAG retrieval and Groq generation."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date
from typing import Any, Dict, List

from housing_policy_advisor.llm.groq_client import complete_prefer_json
from housing_policy_advisor.llm.output_validator import compute_validation_summary
from housing_policy_advisor.llm.policy_response_parser import parse_policy_recommendations_json
from housing_policy_advisor.llm.prompts import policy_recommendation_prompt
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_output import PolicyRecommendationsResult
from housing_policy_advisor.rag.retriever import retrieve_chunks

logger = logging.getLogger(__name__)


class PolicyAdvisor:
    def __init__(self, retrieval_k: int = 8) -> None:
        self.retrieval_k = retrieval_k

    @staticmethod
    def _retrieval_query(locality: FullLocalityInput) -> str:
        return (
            f"{locality.locality_name} {locality.state_name} housing policy affordability "
            "zoning supply rental burden homelessness prevention"
        )

    @staticmethod
    def _distance_to_confidence(distance: float | None) -> float:
        if distance is None:
            return 0.5
        # Chroma distances are lower-is-better; map to [0, 1].
        return max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, float(distance)))))

    def _compute_grounding_score(self, chunks: List[Dict[str, Any]]) -> float:
        if not chunks:
            return 0.0
        confs = [self._distance_to_confidence(c.get("distance")) for c in chunks]
        return sum(confs) / len(confs)

    def generate(self, locality_input: FullLocalityInput) -> PolicyRecommendationsResult:
        locality_json = asdict(locality_input)
        try:
            chunks = retrieve_chunks(
                query=self._retrieval_query(locality_input),
                k=self.retrieval_k,
                locality=locality_input,
            )
        except (RuntimeError, OSError, ImportError) as e:
            logger.warning("RAG retrieval unavailable; continuing without evidence chunks: %s", e)
            chunks = []
        prompt = policy_recommendation_prompt(locality_json, chunks)
        raw = complete_prefer_json([{"role": "user", "content": prompt}])
        parsed = parse_policy_recommendations_json(raw)

        retrieval_confidence = self._compute_grounding_score(chunks)
        for rec in parsed.recommendations:
            llm_conf = max(0.0, min(1.0, float(rec.confidence_score)))
            rec.confidence_score = round((llm_conf + retrieval_confidence) / 2.0, 4)
            if not chunks and "rag_unavailable" not in rec.validation_flags:
                rec.validation_flags.append("rag_unavailable")
            if not rec.evidence_basis:
                rec.validation_flags.append("missing_evidence_basis")

        parsed.locality = locality_input.locality_name
        parsed.generated_date = date.today().isoformat()
        parsed.validation_summary = compute_validation_summary(
            parsed.recommendations,
            grounding_score=retrieval_confidence,
        )
        return parsed
