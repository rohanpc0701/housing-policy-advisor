"""ChromaDB wrapper for storing and searching document embeddings."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from housing_policy_advisor import config

logger = logging.getLogger(__name__)


class VectorDatabase:
    """Manages a persistent ChromaDB collection."""

    def __init__(self, collection_name: str = None, persist_dir: Path = None) -> None:
        self.collection_name = collection_name or config.CHROMA_COLLECTION_NAME
        self.persist_dir = persist_dir or config.chroma_persist_path()
        self.client: Optional[chromadb.PersistentClient] = None
        self.collection = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        try:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Loaded existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Housing policy documents and evidence"},
                )
                logger.info(f"Created new collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error initializing vector database: {e}")
            raise

    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        batch_size: int = 5000,
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")

        total = len(chunks)
        logger.info(f"Adding {total} chunks in batches of {batch_size}…")

        for i in range(0, total, batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_embs = embeddings[i : i + batch_size]

            ids = [c["chunk_id"] for c in batch_chunks]
            texts = [c["text"] for c in batch_chunks]
            metadatas = []
            for c in batch_chunks:
                md = {}
                for k, v in c["metadata"].items():
                    md[k] = v if isinstance(v, (str, int, float, bool)) else str(v)
                metadatas.append(md)

            self.collection.add(
                ids=ids,
                embeddings=batch_embs,
                documents=texts,
                metadatas=metadatas,
            )
            logger.info(f"Batch {i // batch_size + 1}: {len(batch_chunks)} chunks (total {min(i + batch_size, total)}/{total})")

        logger.info(f"Added {total} chunks to {self.collection_name}")

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata or None,
        )
        formatted: List[Dict[str, Any]] = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None,
                })
        return formatted

    def get_stats(self) -> Dict[str, Any]:
        count = self.collection.count()
        sample = self.collection.peek(limit=1)
        stats: Dict[str, Any] = {
            "collection_name": self.collection_name,
            "total_chunks": count,
            "persist_dir": str(self.persist_dir),
        }
        if sample and sample["ids"]:
            stats["sample_metadata_keys"] = list(sample["metadatas"][0].keys()) if sample["metadatas"] else []
        return stats

    def reset_collection(self) -> None:
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "Housing policy documents and evidence"},
        )
        logger.warning(f"Collection {self.collection_name} reset")
