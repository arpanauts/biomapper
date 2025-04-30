"""Text embedding generator implementation."""

import os
import gc
import time
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Union

from ..core.base import BaseEmbedder
from ..core.config import default_config

try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    logging.warning(
        "sentence-transformers package not found. TextEmbedder will use mock embeddings."
    )


class TextEmbedder(BaseEmbedder):
    """Text embedding generator using sentence-transformers."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        max_tokens: Optional[int] = None,
        cache_dir: Optional[str] = None,
    ):
        """Initialize the text embedder.

        Args:
            model_name: Name of the sentence transformer model
            device: Device to use (cpu, cuda)
            max_tokens: Maximum number of tokens for the model
            cache_dir: Directory to cache model files
        """
        self.model_name = model_name or default_config.embedding_model
        self.device = device or default_config.device
        self.max_tokens = max_tokens or default_config.max_tokens
        self.cache_dir = cache_dir or default_config.cache_dir

        # Track initialization
        self.initialized = False
        self.model = None
        self.init_attempts = 0
        self.max_init_attempts = 3

        # Memory management
        self.last_gc_time = time.time()
        self.gc_interval = 60  # seconds

    def _initialize(self) -> bool:
        """Lazy initialization of the embedding model.

        Returns:
            True if initialization succeeded, False otherwise
        """
        if self.initialized:
            return True

        self.init_attempts += 1
        if self.init_attempts > self.max_init_attempts:
            logging.error(
                f"Failed to initialize embedding model after {self.max_init_attempts} attempts"
            )
            return False

        try:
            if not HAS_SENTENCE_TRANSFORMERS:
                logging.warning(
                    "Using mock embeddings - install sentence-transformers for real embeddings"
                )
                self.initialized = True
                return True

            # Prepare cache directory
            if self.cache_dir:
                os.makedirs(self.cache_dir, exist_ok=True)

            # Initialize the model
            logging.info(f"Loading embedding model: {self.model_name}")
            kwargs = {"cache_folder": self.cache_dir if self.cache_dir else None}

            if self.device:
                kwargs["device"] = self.device

            self.model = SentenceTransformer(self.model_name, **kwargs)
            logging.info(f"Model loaded successfully")

            self.initialized = True
            return True

        except Exception as e:
            logging.error(f"Error initializing embedding model: {str(e)}")
            self.initialized = False
            return False

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            Array of embeddings with shape (len(texts), embedding_dim)
        """
        # Initialize if needed
        if not self.initialized and not self._initialize():
            # Return mock embeddings if initialization fails
            return self._generate_mock_embeddings(len(texts))

        # Check for empty input
        if not texts:
            logging.warning("Empty text list provided for embedding")
            return np.array([])

        try:
            # Run garbage collection if needed
            self._maybe_run_gc()

            if self.model:
                # Use the sentence transformer model
                return self.model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # L2 normalize for cosine similarity
                )
            else:
                # Use mock embedding
                return self._generate_mock_embeddings(len(texts))

        except Exception as e:
            logging.error(f"Error generating embeddings: {str(e)}")
            return self._generate_mock_embeddings(len(texts))

    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector
        """
        result = self.embed([text])
        if len(result) > 0:
            return result[0]
        else:
            return self._generate_mock_embeddings(1)[0]

    def _generate_mock_embeddings(self, count: int) -> np.ndarray:
        """Generate mock embeddings for testing.

        Args:
            count: Number of embeddings to generate

        Returns:
            Random embeddings with the expected dimensionality
        """
        # Use a fixed dimension of 384 for mock embeddings (matches all-MiniLM-L6-v2)
        dim = default_config.embedding_dimension

        # Generate random embeddings
        embeddings = np.random.randn(count, dim).astype(np.float32)

        # Normalize for cosine similarity
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norm

        return normalized

    def _maybe_run_gc(self):
        """Run garbage collection if needed."""
        current_time = time.time()
        if current_time - self.last_gc_time > self.gc_interval:
            gc.collect()
            self.last_gc_time = current_time
