"""Policy advisor that combines RAG retrieval and Groq generation."""

from __future__ import annotations

import logging
import json
import re
from dataclasses import asdict
from datetime import date
from typing import Any, Dict, List

from housing_policy_advisor.llm.groq_client import complete_prefer_json
from housing_policy_advisor.llm.output_validator import compute_validation_summary
from housing_policy_advisor.llm.policy_response_parser import parse_policy_recommendations_json
from housing_policy_advisor.llm.prompts import policy_recommendation_prompt
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_output import PolicyRecommendationsResult
from housing_policy_advisor.rag.retriever import _assign_locality_profile, retrieve_chunks

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "with",
    "will",
    "which",
    "where",
    "when",
    "what",
    "while",
    "have",
    "has",
    "had",
    "can",
    "could",
    "should",
    "would",
    "than",
    "then",
    "there",
    "these",
    "those",
    "about",
    "also",
    "within",
    "across",
    "through",
    "using",
    "used",
    "use",
}

HOUSING_POLICY_CONCEPTS = [
    "accessory dwelling unit",
    "adu",
    "inclusionary zoning",
    "density bonus",
    "community land trust",
    "housing trust fund",
    "land bank",
    "rent regulation",
    "rent control",
    "missing middle housing",
    "affordable housing",
    "workforce housing",
    "low income housing tax credit",
    "lihtc",
    "section 8",
    "housing choice voucher",
    "down payment assistance",
    "home repair",
    "homeowner rehabilitation",
    "eviction prevention",
    "foreclosure prevention",
    "code enforcement",
    "manufactured housing",
    "tax increment financing",
    "tif",
    "opportunity zone",
    "mixed income",
    "mixed use",
    "transit oriented development",
    "cost burden",
    "severe cost burden",
    "homeownership rate",
    "vacancy rate",
    "fair market rent",
    "fmr",
    "area median income",
    "ami",
    "housing supply",
    "zoning reform",
    "building permit",
    "rental assistance",
    "housing voucher",
    "public housing",
    "supportive housing",
    "permanent supportive housing",
    "emergency rental assistance",
    "housing counseling",
]


class PolicyAdvisor:
    def __init__(self, retrieval_k: int = 15) -> None:
        self.retrieval_k = retrieval_k

    @staticmethod
    def _retrieval_query(locality: FullLocalityInput) -> str:
        parts = [
            (
                f"What housing policies and programs are recommended for "
                f"{locality.locality_name}, {locality.state_name}?"
            ),
            (
                "Include strategies for affordable housing, rental burden reduction, "
                "housing supply expansion, and zoning reform."
            ),
        ]
        if locality.population_estimate is not None:
            parts.append(f"The population is {locality.population_estimate:,}.")
        if locality.median_household_income is not None:
            parts.append(f"The median household income is ${locality.median_household_income:,.0f}.")
        if locality.cost_burden_rate is not None:
            parts.append(f"The housing cost burden rate is {locality.cost_burden_rate:.1%}.")
        if locality.homeownership_rate is not None:
            parts.append(f"The homeownership rate is {locality.homeownership_rate:.1%}.")
        if locality.vacancy_rate is not None:
            parts.append(f"The housing vacancy rate is {locality.vacancy_rate:.1%}.")
        if locality.building_permits_annual is not None:
            parts.append(f"Recent annual building permits are {locality.building_permits_annual:,}.")
        return " ".join(parts)

    @staticmethod
    def _distance_to_confidence(distance: float | None) -> float:
        if distance is None:
            return 0.5
        # Chroma distances are lower-is-better; map to [0, 1].
        return max(0.0, min(1.0, 1.0 / (1.0 + max(0.0, float(distance)))))

    @staticmethod
    def _normalize_token(token: str) -> str:
        t = token.lower().strip("-")
        if len(t) < 4:
            return ""
        # Lightweight stemming without external dependencies.
        for suffix in ("ingly", "edly", "ments", "ment", "ations", "ation", "ingly", "edly", "ies", "ing", "ers", "er", "ed", "ly", "s"):
            if t.endswith(suffix) and len(t) - len(suffix) >= 3:
                t = t[: -len(suffix)]
                break
        return t

    @staticmethod
    def _extract_grounding_terms(chunks: List[Dict[str, Any]]) -> set[str]:
        _ = chunks
        return set(HOUSING_POLICY_CONCEPTS)

    @staticmethod
    def _extract_recommended_policy_names(llm_output: str) -> List[str]:
        try:
            payload = json.loads(llm_output)
        except Exception:
            return []

        if isinstance(payload, dict):
            recs = payload.get("recommendations", [])
        elif isinstance(payload, list):
            recs = payload
        else:
            recs = []

        names: List[str] = []
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            policy_name = str(rec.get("policy_name", "")).strip()
            if policy_name:
                names.append(policy_name)
        return names

    @staticmethod
    def _canonical_concept_for_policy(policy_name: str) -> str:
        name = policy_name.lower().strip()
        if not name:
            return ""

        for concept in HOUSING_POLICY_CONCEPTS:
            if concept in name or name in concept:
                return concept
        return name

    @classmethod
    def _policy_key_terms(cls, text: str) -> List[str]:
        terms: List[str] = []
        for token in re.findall(r"[a-z][a-z0-9]{2,}", text.lower()):
            if token in _STOPWORDS:
                continue
            terms.append(token)
        return terms

    @staticmethod
    def _get_locality_profile(locality: FullLocalityInput) -> str:
        try:
            return _assign_locality_profile(locality)
        except Exception:
            return "UNKNOWN"

    def _compute_grounding_score(self, chunks: List[Dict[str, Any]], llm_output: str) -> float:
        if not chunks or not llm_output.strip():
            return 0.0

        try:
            payload = json.loads(llm_output)
        except Exception:
            return 0.0

        recs = payload.get("recommendations", []) if isinstance(payload, dict) else []
        if not recs:
            return 0.0

        # Primary: evidence_basis entries reference a real retrieved chunk ID.
        chunk_ids = {
            str(c.get("id", "")).strip().lower().strip("[]")
            for c in chunks
            if c.get("id")
        }
        chunk_text = " ".join(str(c.get("text", "")) for c in chunks).lower()
        chunk_terms = set(self._policy_key_terms(chunk_text))

        backed = 0
        for rec in recs:
            if not isinstance(rec, dict):
                continue

            cited = {
                str(e).strip().lower().strip("[]")
                for e in (rec.get("evidence_basis") or [])
                if e
            }
            if cited & chunk_ids:
                backed += 1
                continue

            # Fallback: policy name keyword overlap with retrieved chunk text.
            policy_name = str(rec.get("policy_name", "")).strip()
            canonical = self._canonical_concept_for_policy(policy_name)
            if canonical and canonical in chunk_text:
                backed += 1
                continue
            key_terms = self._policy_key_terms(canonical if canonical else policy_name)
            if not key_terms:
                key_terms = self._policy_key_terms(policy_name)
            overlap = sum(1 for term in key_terms if term in chunk_terms)
            if key_terms and (overlap >= 2 or (len(key_terms) >= 3 and overlap / len(key_terms) >= 0.5)):
                backed += 1

        return backed / len(recs)

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
        profile = self._get_locality_profile(locality_input)
        prompt = policy_recommendation_prompt(
            locality_data=locality_json,
            evidence_chunks=chunks,
            locality_profile=profile,
        )
        raw = complete_prefer_json([{"role": "user", "content": prompt}])
        parsed = parse_policy_recommendations_json(raw)

        retrieval_confidence = (
            sum(self._distance_to_confidence(c.get("distance")) for c in chunks) / len(chunks)
            if chunks
            else 0.0
        )
        grounding_score = self._compute_grounding_score(chunks, raw)
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
            grounding_score=grounding_score,
        )
        return parsed
