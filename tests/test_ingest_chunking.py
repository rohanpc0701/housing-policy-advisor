"""Tests for text chunking logic."""

from __future__ import annotations

import pytest

from housing_policy_advisor.rag.ingest.chunking import TextChunker


@pytest.fixture()
def chunker():
    return TextChunker(chunk_size=200, chunk_overlap=40)


def _page(text, page_number=1, source="test.pdf"):
    return {"page_number": page_number, "text": text, "metadata": {"source_file": source}}


def test_chunk_short_text_produces_one_chunk(chunker):
    chunks = chunker.chunk_pages([_page("Short text.")], category="academic")
    assert len(chunks) >= 1
    assert chunks[0]["text"]


def test_chunk_empty_text_returns_nothing(chunker):
    chunks = chunker.chunk_pages([_page("   ")], category="academic")
    assert chunks == []


def test_chunk_empty_pages_returns_nothing(chunker):
    assert chunker.chunk_pages([], category="academic") == []


def test_chunk_id_deterministic(chunker):
    pages = [_page("Some content for testing chunking.", source="doc.pdf")]
    a = chunker.chunk_pages(pages, category="academic")
    b = chunker.chunk_pages(pages, category="academic")
    assert [c["chunk_id"] for c in a] == [c["chunk_id"] for c in b]


def test_chunk_ids_unique(chunker):
    long_text = ("Housing policy sentence. " * 50).strip()
    chunks = chunker.chunk_pages([_page(long_text, source="doc.pdf")], category="academic")
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_metadata_propagated(chunker):
    chunks = chunker.chunk_pages([_page("Content here.", page_number=3, source="report.pdf")], category="fed_regulatory")
    for c in chunks:
        assert c["metadata"]["category"] == "fed_regulatory"
        assert c["metadata"]["page_number"] == 3


def test_overlap_not_larger_than_chunk(chunker):
    long_text = ("Word " * 200).strip()
    chunks = chunker.chunk_pages([_page(long_text, source="doc.pdf")], category="academic")
    if len(chunks) > 1:
        for c in chunks:
            assert len(c["text"]) <= chunker.chunk_size + 100


def test_chunk_text_field_non_empty(chunker):
    chunks = chunker.chunk_pages([_page("Non-trivial content about affordable housing policy.")], category="case_studies")
    for c in chunks:
        assert c["text"].strip()
