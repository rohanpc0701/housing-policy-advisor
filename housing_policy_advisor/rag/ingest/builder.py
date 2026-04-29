"""End-to-end ingestion orchestrator: PDF dirs → chunks → embeddings → Chroma."""
import logging
from pathlib import Path
from typing import Dict, List, Any

from tqdm import tqdm

from housing_policy_advisor import config
from .pdf_processor import PDFProcessor
from .chunking import TextChunker
from .embeddings import EmbeddingService
from .vector_db import VectorDatabase

logger = logging.getLogger(__name__)


class IngestBuilder:
    """Builds the Chroma vector store from categorised PDF directories."""

    def __init__(self, reset: bool = False) -> None:
        self.embedder = EmbeddingService()
        self.db = VectorDatabase()
        if reset:
            logger.warning("Resetting vector database collection…")
            self.db.reset_collection()

    def ingest_directories(
        self,
        sources: Dict[str, Path],
        limit: int = None,
        dry_run: bool = False,
    ) -> int:
        """
        Ingest PDFs from *sources* (mapping of category → directory).

        Args:
            sources: e.g. {"academic": Path("corpus/academic"), ...}
            limit: max PDFs to process (useful for quick iteration)
            dry_run: if True, process and report but don't write to Chroma

        Returns:
            Total chunks produced. On dry_run, no chunks are written.
        """
        processor = PDFProcessor()
        chunker = TextChunker()

        all_chunks: List[Dict[str, Any]] = []
        pdf_count = 0

        for category, directory in sources.items():
            directory = Path(directory)
            if not directory.exists():
                logger.warning(f"Source directory not found, skipping: {directory}")
                continue

            pdfs = sorted(directory.glob("*.pdf"))
            if not pdfs:
                logger.warning(f"No PDFs found in {directory}")
                continue

            logger.info(f"Category '{category}': {len(pdfs)} PDFs in {directory}")

            for pdf_path in tqdm(pdfs, desc=f"[{category}]", unit="pdf"):
                if limit is not None and pdf_count >= limit:
                    break
                try:
                    pages = processor.extract_text(pdf_path)
                    chunks = chunker.chunk_pages(pages, category=category)
                    all_chunks.extend(chunks)
                    pdf_count += 1
                    logger.debug(f"{pdf_path.name}: {len(pages)} pages → {len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Failed to process {pdf_path.name}: {e}")

        logger.info(f"Total: {pdf_count} PDFs → {len(all_chunks)} chunks")

        if not all_chunks:
            logger.warning("No chunks produced — nothing to index.")
            return 0

        if dry_run:
            logger.info("Dry run: skipping Chroma write.")
            return len(all_chunks)

        logger.info("Generating embeddings…")
        texts = [c["text"] for c in all_chunks]
        embeddings = self.embedder.embed_batch(texts, batch_size=32)

        logger.info("Writing to Chroma…")
        self.db.add_chunks(all_chunks, embeddings)

        stats = self.db.get_stats()
        logger.info(
            f"Done. Collection '{stats['collection_name']}': "
            f"{stats['total_chunks']} total chunks at {stats['persist_dir']}"
        )
        return len(all_chunks)
