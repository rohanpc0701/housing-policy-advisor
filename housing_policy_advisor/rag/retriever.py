"""
ChromaDB retrieval interface — stub until vector DB is connected.

Implement with sentence-transformers + Chroma using config.CHROMA_PERSIST_DIR.
"""

from __future__ import annotations

from typing import List, Optional

from housing_policy_advisor.models.locality_input import FullLocalityInput


def retrieve(query: str, k: int = 8, locality: Optional[FullLocalityInput] = None) -> List[str]:
    """
    Return top-k RAG chunk texts for the query.

    Currently raises NotImplementedError; replace with Chroma query + embedding.
    """
    raise NotImplementedError(
        "RAG retriever not connected; implement ChromaDB query when embeddings are available."
    )


def retrieve_chunks_with_metadata(
    query: str, k: int = 8
) -> List[dict]:
    """Optional: chunks with source metadata for citations."""
    raise NotImplementedError("RAG retriever not connected.")
