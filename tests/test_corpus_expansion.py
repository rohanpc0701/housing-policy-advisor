"""Integration checks for newly ingested corpus_additions retrieval."""

from __future__ import annotations

import os

import pytest

from housing_policy_advisor.rag.retriever import retrieve_chunks


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_CORPUS_EXPANSION_TESTS") != "1",
    reason="requires locally ingested data/corpus_additions Chroma collection",
)


NEW_CORPUS_FILES = {
    "Chapter 21 Rental assistance and eviction prevention _ HB854 Statewide Housing Study.pdf",
    "Executive summary _ HB854 Statewide Housing Study.pdf",
    "RADResidentFactSheet_13_RADandLow-IncomeTaxCredits.pdf",
    "dbhds-srap.pdf",
    "dbhds-srap (1).pdf",
    "dhcd-asnh.pdf",
    "dpa-program-guidelines.pdf",
    "home-arp-tbra-program-guidelines.pdf",
}


def _source_file(chunk: dict) -> str:
    md = chunk.get("metadata") or {}
    return str(md.get("source_file") or md.get("source") or "")


def _count_matches(query: str, expected_files: set[str], k: int = 50) -> int:
    chunks = retrieve_chunks(query=query, k=k, locality=None)
    return sum(1 for c in chunks if _source_file(c) in expected_files)


def test_rental_assistance_returns_new_docs() -> None:
    count = _count_matches("rental assistance Virginia", NEW_CORPUS_FILES, k=60)
    assert count >= 5, f"Expected >=5 matches from new corpus files, got {count}"


def test_lihtc_tax_credit_returns_results() -> None:
    count = _count_matches(
        "LIHTC tax credit affordable housing",
        {
            "RADResidentFactSheet_13_RADandLow-IncomeTaxCredits.pdf",
            "Executive summary _ HB854 Statewide Housing Study.pdf",
            "Chapter 21 Rental assistance and eviction prevention _ HB854 Statewide Housing Study.pdf",
        },
        k=50,
    )
    assert count >= 3, f"Expected >=3 LIHTC/tax-credit matches, got {count}"


def test_down_payment_assistance_returns_results() -> None:
    count = _count_matches(
        "down payment assistance homeownership",
        {"dpa-program-guidelines.pdf", "dhcd-asnh.pdf"},
        k=50,
    )
    assert count >= 3, f"Expected >=3 down-payment-assistance matches, got {count}"
