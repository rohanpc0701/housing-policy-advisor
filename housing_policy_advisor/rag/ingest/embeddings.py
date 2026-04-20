"""Local sentence-transformers embedding service."""
import logging
from typing import List

from housing_policy_advisor import config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates text embeddings using a local sentence-transformers model."""

    def __init__(self) -> None:
        self.model = None
        self.model_name = config.EMBEDDING_MODEL
        self._init_model()

    def _init_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded")
        except ImportError:
            raise ImportError("sentence-transformers not installed. pip install sentence-transformers")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """Return embedding vector for a single text."""
        if not text or not text.strip():
            return [0.0] * config.EMBEDDING_DIM
        try:
            return self.model.encode(text, convert_to_numpy=True, show_progress_bar=False).tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Return embedding vectors for a list of texts."""
        if not texts:
            return []
        try:
            all_embeddings: List[List[float]] = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embeddings = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    batch_size=batch_size,
                )
                all_embeddings.extend(embeddings.tolist())
                logger.debug(f"Embedded {min(i + batch_size, len(texts))}/{len(texts)} texts")
            return all_embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        return config.EMBEDDING_DIM
