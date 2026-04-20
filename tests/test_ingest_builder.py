"""Integration test: IngestBuilder on a minimal PDF fixture."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture()
def pdf_dir(tmp_path, minimal_pdf_bytes):
    d = tmp_path / "academic"
    d.mkdir()
    (d / "test_doc.pdf").write_bytes(minimal_pdf_bytes)
    return d


def test_ingest_dry_run(pdf_dir, tmp_path):
    from housing_policy_advisor.rag.ingest.builder import IngestBuilder

    with patch("housing_policy_advisor.rag.ingest.builder.VectorDatabase") as MockDB, \
         patch("housing_policy_advisor.rag.ingest.builder.EmbeddingService") as MockEmb:
        mock_emb_instance = MockEmb.return_value
        mock_emb_instance.embed_batch.return_value = [[0.1] * 4]
        mock_db_instance = MockDB.return_value

        builder = IngestBuilder.__new__(IngestBuilder)
        builder.embedder = mock_emb_instance
        builder.db = mock_db_instance

        total = builder.ingest_directories(
            {"academic": pdf_dir},
            dry_run=True,
        )
    assert total == 0
    mock_db_instance.add_chunks.assert_not_called()


def test_ingest_missing_dir_skipped(tmp_path):
    from housing_policy_advisor.rag.ingest.builder import IngestBuilder

    with patch("housing_policy_advisor.rag.ingest.builder.VectorDatabase"), \
         patch("housing_policy_advisor.rag.ingest.builder.EmbeddingService") as MockEmb:
        mock_emb_instance = MockEmb.return_value
        mock_emb_instance.embed_batch.return_value = []

        builder = IngestBuilder.__new__(IngestBuilder)
        builder.embedder = mock_emb_instance
        builder.db = MagicMock()

        total = builder.ingest_directories(
            {"academic": tmp_path / "nonexistent"},
        )
    assert total == 0


def test_ingest_limit(pdf_dir, tmp_path):
    from housing_policy_advisor.rag.ingest.builder import IngestBuilder

    with patch("housing_policy_advisor.rag.ingest.builder.VectorDatabase") as MockDB, \
         patch("housing_policy_advisor.rag.ingest.builder.EmbeddingService") as MockEmb:
        mock_emb_instance = MockEmb.return_value
        mock_db_instance = MockDB.return_value

        builder = IngestBuilder.__new__(IngestBuilder)
        builder.embedder = mock_emb_instance
        builder.db = mock_db_instance

        # Limit 0 means process 0 PDFs
        total = builder.ingest_directories(
            {"academic": pdf_dir},
            limit=0,
        )
    assert total == 0
