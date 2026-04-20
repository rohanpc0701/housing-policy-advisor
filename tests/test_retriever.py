"""Tests for rag/retriever.py — patches chromadb client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_query_result(ids, docs, metas, dists):
    return {
        "ids": [ids],
        "documents": [docs],
        "metadatas": [metas],
        "distances": [dists],
    }


def _named(name: str):
    """Return a simple object with .name attribute (avoids MagicMock name= conflict)."""
    obj = MagicMock()
    obj.name = name
    return obj


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_chunks_returns_flat_list(mock_ef, mock_client):
    collection = MagicMock()
    collection.query.return_value = _make_query_result(
        ids=["id1", "id2"],
        docs=["text one", "text two"],
        metas=[{"source": "a.pdf"}, {"source": "b.pdf"}],
        dists=[0.1, 0.3],
    )
    mock_client.return_value.list_collections.return_value = [_named("housing_policy_chunks")]
    mock_client.return_value.get_collection.return_value = collection
    mock_ef.return_value = MagicMock()

    from housing_policy_advisor.rag.retriever import retrieve_chunks
    results = retrieve_chunks("affordable housing zoning")

    assert len(results) == 2
    assert results[0]["id"] == "id1"
    assert results[0]["text"] == "text one"
    assert results[0]["distance"] == pytest.approx(0.1)


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_chunks_missing_collection_raises(mock_ef, mock_client):
    mock_client.return_value.list_collections.return_value = []  # no collections
    mock_ef.return_value = MagicMock()

    from housing_policy_advisor.rag.retriever import retrieve_chunks
    with pytest.raises(RuntimeError, match="not found"):
        retrieve_chunks("some query")


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_empty_query_returns_empty(mock_ef, mock_client):
    from housing_policy_advisor.rag.retriever import retrieve_chunks
    results = retrieve_chunks("   ")
    assert results == []
    mock_client.assert_not_called()


@patch("housing_policy_advisor.rag.retriever._persistent_client")
@patch("housing_policy_advisor.rag.retriever._embedding_function")
def test_retrieve_texts_only(mock_ef, mock_client):
    collection = MagicMock()
    collection.query.return_value = _make_query_result(
        ids=["id1"],
        docs=["policy text"],
        metas=[{}],
        dists=[0.2],
    )
    mock_client.return_value.list_collections.return_value = [_named("housing_policy_chunks")]
    mock_client.return_value.get_collection.return_value = collection

    from housing_policy_advisor.rag.retriever import retrieve
    texts = retrieve("housing policy")
    assert texts == ["policy text"]
