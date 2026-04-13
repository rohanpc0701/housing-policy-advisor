"""
ChromaDB retrieval using the same embedding model as the indexed corpus.

Requires ``chromadb`` and ``sentence-transformers``. Set ``CHROMA_PERSIST_DIR`` and
``CHROMA_COLLECTION_NAME`` to match your persisted vector store.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from housing_policy_advisor import config
from housing_policy_advisor.models.locality_input import FullLocalityInput

logger = logging.getLogger(__name__)


def _embedding_function():
    try:
        from chromadb.utils import embedding_functions
    except ImportError as e:
        raise RuntimeError(
            "chromadb is required for RAG. Install dependencies: pip install chromadb sentence-transformers"
        ) from e

    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)


def _persistent_client():
    try:
        import chromadb
    except ImportError as e:
        raise RuntimeError(
            "chromadb is required for RAG. Install dependencies: pip install chromadb sentence-transformers"
        ) from e

    path = str(config.chroma_persist_path())
    return chromadb.PersistentClient(path=path)


def _get_collection():
    client = _persistent_client()
    ef = _embedding_function()
    name = config.CHROMA_COLLECTION_NAME
    names = {c.name for c in client.list_collections()}
    if name not in names:
        raise RuntimeError(
            f"Chroma collection {name!r} not found under {config.chroma_persist_path()}. "
            f"Available collections: {sorted(names) or '(none)'}. "
            "Build or copy the vector DB, or set CHROMA_COLLECTION_NAME."
        )
    return client.get_collection(name=name, embedding_function=ef)


def retrieve_chunks(
    query: str,
    k: int = 8,
    locality: Optional[FullLocalityInput] = None,
) -> List[Dict[str, Any]]:
    """
    Return top-k chunks as dicts: ``id``, ``text``, ``metadata``, ``distance`` (if present).

    ``locality`` is reserved for future query expansion; currently unused.
    """
    _ = locality
    if not query.strip():
        return []
    collection = _get_collection()
    res = collection.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0] if res.get("distances") is not None else [None] * len(ids)
    out: List[Dict[str, Any]] = []
    for i, cid in enumerate(ids):
        text = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None
        out.append(
            {
                "id": cid,
                "text": text or "",
                "metadata": meta or {},
                "distance": dist,
            }
        )
    return out


def retrieve(query: str, k: int = 8, locality: Optional[FullLocalityInput] = None) -> List[str]:
    """Return top-k chunk texts for the query."""
    return [c["text"] for c in retrieve_chunks(query, k=k, locality=locality) if c.get("text")]


def retrieve_chunks_with_metadata(query: str, k: int = 8) -> List[dict]:
    """Alias for :func:`retrieve_chunks` (includes metadata)."""
    return retrieve_chunks(query, k=k)
