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
    assert total > 0
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


def _metadata_from_builder_run(tmp_path, extra_metadata):
    from housing_policy_advisor.rag.ingest.builder import IngestBuilder

    pdf_dir = tmp_path / "classifier_docs"
    pdf_dir.mkdir()
    (pdf_dir / "doc.pdf").write_bytes(b"%PDF-1.4")

    captured = {}

    with patch("housing_policy_advisor.rag.ingest.builder.VectorDatabase") as MockDB, \
         patch("housing_policy_advisor.rag.ingest.builder.EmbeddingService") as MockEmb, \
         patch("housing_policy_advisor.rag.ingest.builder.PDFProcessor") as MockProcessor, \
         patch("housing_policy_advisor.rag.ingest.builder.TextChunker") as MockChunker:
        MockProcessor.return_value.extract_text.return_value = [
            {
                "page_number": 1,
                "text": "Classifier policy text.",
                "metadata": {"source_file": "doc.pdf"},
            }
        ]

        def chunk_pages(pages, category=None):
            captured["metadata"] = pages[0]["metadata"].copy()
            captured["category"] = category
            return [
                {
                    "chunk_id": "chunk_1",
                    "text": pages[0]["text"],
                    "metadata": pages[0]["metadata"].copy(),
                }
            ]

        MockChunker.return_value.chunk_pages.side_effect = chunk_pages
        mock_emb_instance = MockEmb.return_value
        mock_db_instance = MockDB.return_value

        builder = IngestBuilder.__new__(IngestBuilder)
        builder.embedder = mock_emb_instance
        builder.db = mock_db_instance

        total = builder.ingest_directories(
            {"implementation_toolkit": pdf_dir},
            dry_run=True,
            extra_metadata=extra_metadata,
        )

    assert total == 1
    mock_db_instance.add_chunks.assert_not_called()
    return captured["metadata"]


def test_classifier_ingest_defaults_doc_type_unknown(tmp_path):
    metadata = _metadata_from_builder_run(tmp_path, {"policy_class": "adu"})

    assert metadata["policy_class"] == "adu"
    assert metadata["doc_type"] == "unknown"


def test_classifier_ingest_preserves_explicit_doc_type(tmp_path):
    metadata = _metadata_from_builder_run(
        tmp_path,
        {"policy_class": "density_bonus", "doc_type": "example_policy"},
    )

    assert metadata["policy_class"] == "density_bonus"
    assert metadata["doc_type"] == "example_policy"


def test_legacy_ingest_does_not_add_classifier_doc_type(tmp_path):
    metadata = _metadata_from_builder_run(tmp_path, {})

    assert "policy_class" not in metadata
    assert "doc_type" not in metadata
