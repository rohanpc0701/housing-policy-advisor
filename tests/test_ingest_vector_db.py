"""Round-trip tests for VectorDatabase using a tmp_path Chroma store."""

from __future__ import annotations

import pytest

from housing_policy_advisor.rag.ingest.vector_db import VectorDatabase


@pytest.fixture()
def db(tmp_path):
    return VectorDatabase(collection_name="test_collection", persist_dir=tmp_path)


def _fake_chunks(n=3):
    return [
        {
            "chunk_id": f"doc_p1_c{i}",
            "text": f"Chunk text number {i} about housing policy.",
            "metadata": {"source": f"doc{i}.pdf", "category": "academic", "page_num": 1},
        }
        for i in range(n)
    ]


def _fake_embeddings(n=3, dim=4):
    return [[float(i + j) / 10 for j in range(dim)] for i in range(n)]


def test_add_and_count(db):
    chunks = _fake_chunks(3)
    embs = _fake_embeddings(3)
    db.add_chunks(chunks, embs)
    stats = db.get_stats()
    assert stats["total_chunks"] == 3


def test_get_stats_fields(db):
    stats = db.get_stats()
    assert "collection_name" in stats
    assert "total_chunks" in stats
    assert "persist_dir" in stats


def test_search_returns_results(db):
    chunks = _fake_chunks(5)
    embs = _fake_embeddings(5)
    db.add_chunks(chunks, embs)
    results = db.search(query_embedding=[0.0, 0.1, 0.2, 0.3], n_results=3)
    assert len(results) <= 3
    for r in results:
        assert "chunk_id" in r
        assert "text" in r
        assert "metadata" in r


def test_mismatch_raises(db):
    chunks = _fake_chunks(3)
    embs = _fake_embeddings(2)
    with pytest.raises(ValueError, match="Mismatch"):
        db.add_chunks(chunks, embs)


def test_reset_clears_collection(db):
    chunks = _fake_chunks(3)
    embs = _fake_embeddings(3)
    db.add_chunks(chunks, embs)
    assert db.get_stats()["total_chunks"] == 3
    db.reset_collection()
    assert db.get_stats()["total_chunks"] == 0


def test_collection_name_default():
    from housing_policy_advisor import config
    from unittest.mock import patch
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        with patch.object(config, "chroma_persist_path", return_value=pathlib.Path(td)):
            db = VectorDatabase()
            assert db.collection_name == config.CHROMA_COLLECTION_NAME
