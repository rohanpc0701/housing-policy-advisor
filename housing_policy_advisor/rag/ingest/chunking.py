"""Sentence-boundary aware text chunking with overlap."""
import hashlib
import logging
import re
from typing import List, Dict, Any

from housing_policy_advisor import config

logger = logging.getLogger(__name__)


def make_chunk_id(
    *,
    source_file: str,
    category: str,
    page_num: int,
    chunk_index: int,
    text: str,
) -> str:
    """
    Create a stable, human-readable chunk ID with collision protection.

    TODO: Legacy chunks already persisted in ChromaDB use the old ID format.
    New ingestion uses this collision-resistant format. Do not re-ingest broad
    legacy corpus folders during classifier work unless duplicate chunks are
    intentionally accepted. A future full corpus rebuild should use an explicit
    reset and this ID scheme consistently.
    """
    normalized_name = re.sub(r"\.[Pp][Dd][Ff]$", "", source_file)
    normalized_name = re.sub(r"[^a-zA-Z0-9]+", "_", normalized_name).strip("_")
    safe_filename = (normalized_name or "unknown")[:40]
    safe_category = re.sub(r"[^a-zA-Z0-9]+", "_", category or "unknown").strip("_") or "unknown"
    content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return f"{safe_category}_{safe_filename}_{content_hash}_p{page_num}_c{chunk_index}"


class TextChunker:
    """Splits text into overlapping chunks at sentence boundaries."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None) -> None:
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split *text* into chunks; attach *metadata* to each chunk."""
        if not text or not text.strip():
            return []

        page_num = metadata.get("page_number", 0)
        source_file = str(metadata.get("source_file", "unknown"))
        category = str(metadata.get("category", "unknown"))

        sentences = self._split_sentences(text)
        chunks: List[Dict[str, Any]] = []
        current_chunk = ""
        chunk_index = 0
        start_char = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunk_meta = metadata.copy()
                chunk_meta.update({
                    "chunk_index": chunk_index,
                    "start_char": start_char,
                    "end_char": start_char + len(current_chunk),
                    "chunk_size": len(current_chunk),
                })
                chunk_text = current_chunk.strip()
                # TODO: Existing persisted Chroma chunks use legacy IDs. Do not
                # reset ChromaDB during classifier work; on a future intentional
                # full corpus rebuild, use this ID scheme consistently.
                chunks.append({
                    "chunk_id": make_chunk_id(
                        source_file=source_file,
                        category=category,
                        page_num=int(page_num),
                        chunk_index=chunk_index,
                        text=chunk_text,
                    ),
                    "text": chunk_text,
                    "metadata": chunk_meta,
                })
                overlap = self._get_overlap_text(current_chunk, self.chunk_overlap)
                start_char = chunk_meta["end_char"] - len(overlap)
                current_chunk = overlap + sentence
                chunk_index += 1
            else:
                current_chunk = (current_chunk + " " + sentence) if current_chunk else sentence

        if current_chunk.strip():
            chunk_meta = metadata.copy()
            chunk_meta.update({
                "chunk_index": chunk_index,
                "start_char": start_char,
                "end_char": start_char + len(current_chunk),
                "chunk_size": len(current_chunk),
            })
            chunk_text = current_chunk.strip()
            # TODO: Existing persisted Chroma chunks use legacy IDs. Do not
            # reset ChromaDB during classifier work; on a future intentional
            # full corpus rebuild, use this ID scheme consistently.
            chunks.append({
                "chunk_id": make_chunk_id(
                    source_file=source_file,
                    category=category,
                    page_num=int(page_num),
                    chunk_index=chunk_index,
                    text=chunk_text,
                ),
                "text": chunk_text,
                "metadata": chunk_meta,
            })

        return chunks

    def chunk_pages(self, pages_data: List[Dict[str, Any]], category: str = None) -> List[Dict[str, Any]]:
        """Chunk all pages returned by PDFProcessor."""
        all_chunks: List[Dict[str, Any]] = []
        for page_data in pages_data:
            meta = page_data["metadata"].copy()
            meta["page_number"] = page_data["page_number"]
            if category:
                meta["category"] = category
            all_chunks.extend(self.chunk_text(page_data["text"], meta))
        return all_chunks

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r"[.!?]+\s+", text)
        sentences = [s.strip() for s in parts if s.strip()]
        if len(sentences) <= 1:
            sentences = [p.strip() for p in text.split("\n\n") if p.strip()]
        return sentences

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        if len(text) <= overlap_size:
            return text
        start = len(text) - overlap_size
        for i in range(start, len(text)):
            if text[i] in (" ", "\n"):
                return text[i + 1:]
        return text[-overlap_size:]
