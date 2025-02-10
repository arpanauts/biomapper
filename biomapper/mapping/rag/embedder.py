"""Text embedders for RAG."""

from typing import List
import numpy as np
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from .base_rag import BaseEmbedder, EmbeddingError


class ChromaEmbedder(BaseEmbedder):
    """Embedder using ChromaDB's SentenceTransformer."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize ChromaEmbedder.
        
        Args:
            model_name: Name of the model to use
        """
        try:
            self.embedder = SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )
        except Exception as e:
            raise EmbeddingError(f"Failed to initialize embedder: {e}") from e

    async def embed_text(self, text: str) -> np.ndarray:
        """Embed text into a vector.
        
        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding fails
        """
        try:
            # ChromaDB returns a list of embeddings, we take the first one
            embedding = self.embedder([text])[0]
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            raise EmbeddingError(f"Failed to embed text: {e}") from e

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts.
        
        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding fails
        """
        try:
            embeddings = self.embedder(texts)
            return [np.array(emb, dtype=np.float32) for emb in embeddings]
        except Exception as e:
            raise EmbeddingError(f"Failed to embed texts: {e}") from e
