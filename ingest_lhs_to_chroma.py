"""
Ingest Local Housing Solutions chunks JSON into existing Chroma collection.

Usage:
    python ingest_lhs_to_chroma.py

Optional env:
    LHS_CHUNKS_FILE=lhs_policies_chunks.json
    LHS_BATCH_SIZE=256
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from housing_policy_advisor import config
from housing_policy_advisor.rag.ingest.embeddings import EmbeddingService

CHUNKS_FILE = Path(os.getenv("LHS_CHUNKS_FILE", "lhs_policies_chunks.json"))
CHROMA_PATH = config.chroma_persist_path()
COLLECTION_NAME = config.CHROMA_COLLECTION_NAME
BATCH_SIZE = int(os.getenv("LHS_BATCH_SIZE", "256"))


def _to_chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    out: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
        else:
            out[key] = str(value)
    return out


def main() -> None:
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(f"Chunks file not found: {CHUNKS_FILE}")

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    print(f"Using CHROMA_PATH={CHROMA_PATH}")
    print(f"Using COLLECTION_NAME={COLLECTION_NAME}")
    print(f"Reading chunks from: {CHUNKS_FILE}")

    with CHUNKS_FILE.open("r", encoding="utf-8") as file:
        chunks: list[dict[str, Any]] = json.load(file)

    if not chunks:
        print("No chunks found in JSON. Nothing to ingest.")
        return

    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
    )

    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' not found at {CHROMA_PATH}. "
            "Refusing to create a new collection."
        ) from exc

    embedder = EmbeddingService()

    total = len(chunks)
    print(f"Loaded {total} chunks. Upserting in batches of {BATCH_SIZE}...")

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        ids = [item["id"] for item in batch]
        texts = [item["text"] for item in batch]
        metadatas = [_to_chroma_metadata(item.get("metadata", {})) for item in batch]
        embeddings = embedder.embed_batch(texts, batch_size=32)

        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        print(f"Upserted {min(i + BATCH_SIZE, total)}/{total}")

    print(f"Done. Collection '{COLLECTION_NAME}' now has {collection.count()} chunks.")


if __name__ == "__main__":
    main()
