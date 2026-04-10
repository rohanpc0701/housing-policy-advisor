"""
Validates LLM policy recommendations against locality input and optional RAG text.

Five checks:
1. Grounding score >= threshold (batch or per-outcome heuristic)
2. Confidence score >= CONFIDENCE_THRESHOLD else flag
3. Comparable communities vs population/income tolerances (when structured data missing, flag unverified)
4. Completeness of required fields
5. Internal consistency heuristics vs locality metrics
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import List, Optional, Tuple

from housing_policy_advisor import config
from housing_policy_advisor.models.locality_input import FullLocalityInput
from housing_policy_advisor.models.policy_output import PolicyRecommendation, PolicyRecommendationsResult


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _sentence_grounded(
    sentence: str,
    evidence_basis: List[str],
    rag_chunks: Optional[List[str]],
    input_facts: List[str],
) -> bool:
    s_low = sentence.lower()
    pool = list(evidence_basis) + list(input_facts)
    if rag_chunks:
        pool.extend(rag_chunks)
    for chunk in pool:
        if not chunk:
            continue
        c = chunk.strip()
        if len(c) < 12:
            continue
        snippet = c[:120].lower()
        if snippet and snippet in s_low:
            return True
        # Substring match either direction for short factual overlap
        words = [w for w in re.findall(r"[a-z0-9%]+", s_low) if len(w) > 4]
        hits = sum(1 for w in words[:8] if w in c.lower())
        if hits >= 2:
            return True
    return False


def _compute_grounding_score(
    recommendations: List[PolicyRecommendation],
    locality: FullLocalityInput,
    rag_chunks: Optional[List[str]],
) -> float:
    """Fraction of sentences in predicted_outcome with trace to evidence, RAG, or input."""
    input_facts: List[str] = []
    if locality.population_estimate is not None:
        input_facts.append(str(locality.population_estimate))
    if locality.median_household_income is not None:
        input_facts.append(str(locality.median_household_income))
    if locality.vacancy_rate is not None:
        input_facts.append(f"{locality.vacancy_rate:.2f}")

    total_sents = 0
    grounded = 0
    for rec in recommendations:
        for sent in _split_sentences(rec.predicted_outcome):
            total_sents += 1
            if _sentence_grounded(sent, rec.evidence_basis, rag_chunks, input_facts):
                grounded += 1
    if total_sents == 0:
        return 1.0
    return grounded / total_sents


def _pop_income_window(
    locality: FullLocalityInput,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    pop = float(locality.population_estimate) if locality.population_estimate else None
    inc = float(locality.median_household_income) if locality.median_household_income else None
    if pop is None or inc is None:
        return None, None, None, None
    pt = config.POPULATION_MATCH_TOLERANCE
    it = config.INCOME_MATCH_TOLERANCE
    return pop * (1 - pt), pop * (1 + pt), inc * (1 - it), inc * (1 + it)


def _parse_comparable_numbers(name: str) -> Optional[Tuple[float, float]]:
    """If string embeds pop/income like 'Foo, pop 100000, MHI 55000', extract."""
    m_pop = re.search(r"pop(?:ulation)?\s*[:=]?\s*([\d,]+)", name, re.I)
    m_inc = re.search(r"(?:mhi|income|ami)\s*[:=]?\s*([\d,]+)", name, re.I)
    if not m_pop or not m_inc:
        return None
    try:
        p = float(m_pop.group(1).replace(",", ""))
        i = float(m_inc.group(1).replace(",", ""))
        return p, i
    except ValueError:
        return None


def validate(
    recommendations: List[PolicyRecommendation],
    locality: FullLocalityInput,
    rag_chunks: Optional[List[str]] = None,
    batch_grounding_score: Optional[float] = None,
) -> PolicyRecommendationsResult:
    """
    Run all validation checks; append flags to each recommendation's validation_flags.

    Returns PolicyRecommendationsResult with updated recommendations and computed grounding_score.
    """
    out_recs: List[PolicyRecommendation] = [deepcopy(r) for r in recommendations]

    g_score = batch_grounding_score
    if g_score is None:
        g_score = _compute_grounding_score(out_recs, locality, rag_chunks)
    if g_score < config.GROUNDING_THRESHOLD:
        flag = f"low_grounding:{g_score:.2f}"
        for r in out_recs:
            if flag not in r.validation_flags:
                r.validation_flags.append(flag)

    pop_lo, pop_hi, inc_lo, inc_hi = _pop_income_window(locality)

    for rec in out_recs:
        if rec.confidence_score < config.CONFIDENCE_THRESHOLD:
            rec.validation_flags.append("low_confidence")

        for comm in rec.comparable_communities:
            parsed = _parse_comparable_numbers(comm)
            if parsed is None:
                rec.validation_flags.append(f"unverified_comparable:{comm[:40]}")
                continue
            cp, ci = parsed
            if pop_lo is not None and not (pop_lo <= cp <= pop_hi):
                rec.validation_flags.append(f"comparable_pop_out_of_range:{comm[:40]}")
            if inc_lo is not None and not (inc_lo <= ci <= inc_hi):
                rec.validation_flags.append(f"comparable_income_out_of_range:{comm[:40]}")

        # Completeness
        req = [
            rec.policy_name,
            rec.predicted_outcome,
            rec.implementation_timeline,
            rec.resource_requirements,
        ]
        if not all(str(x).strip() for x in req):
            rec.validation_flags.append("incomplete_fields")
        if rec.risks is None:
            rec.validation_flags.append("incomplete_fields")
        if rec.evidence_basis is None or len(rec.evidence_basis) == 0:
            rec.validation_flags.append("incomplete_fields")

        # Internal consistency heuristics
        text = (rec.policy_name + " " + rec.predicted_outcome).lower()
        vr = locality.vacancy_rate
        if vr is not None and vr > 0.15:
            tight_phrases = ("tight supply", "housing shortage", "severe shortage", "nowhere to build")
            if any(p in text for p in tight_phrases):
                rec.validation_flags.append("consistency_vacancy_vs_tight_supply")

    return PolicyRecommendationsResult(recommendations=out_recs, grounding_score=g_score)


def validate_completeness_raises(recommendations: List[PolicyRecommendation]) -> None:
    """Strict check: every recommendation must have all required fields populated."""
    for rec in recommendations:
        if not str(rec.policy_name).strip():
            raise ValueError("Missing policy_name")
        if not str(rec.predicted_outcome).strip():
            raise ValueError("Missing predicted_outcome")
        if rec.confidence_score is None:
            raise ValueError("Missing confidence_score")
        if rec.evidence_basis is None:
            raise ValueError("Missing evidence_basis")
        if rec.comparable_communities is None:
            raise ValueError("Missing comparable_communities")
        if not str(rec.implementation_timeline).strip():
            raise ValueError("Missing implementation_timeline")
        if not str(rec.resource_requirements).strip():
            raise ValueError("Missing resource_requirements")
        if rec.risks is None:
            raise ValueError("Missing risks")
