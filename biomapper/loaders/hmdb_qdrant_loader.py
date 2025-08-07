"""HMDB loader for Qdrant vector database using FastEmbed."""

import logging
from typing import Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
from fastembed import TextEmbedding

from ..processors.hmdb import HMDBProcessor

logger = logging.getLogger(__name__)


class HMDBQdrantLoader:
    """Load HMDB metabolites into Qdrant vector database using FastEmbed."""

    def __init__(
        self,
        processor: HMDBProcessor,
        qdrant_url: str = "localhost:6333",
        collection_name: str = "hmdb_metabolites",
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 100,
    ):
        """Initialize the loader.

        Args:
            processor: HMDBProcessor instance for parsing XML data
            qdrant_url: URL for Qdrant instance
            collection_name: Name of collection to store metabolites in
            embedding_model: FastEmbed model name for generating embeddings
            batch_size: Number of metabolites to process at once
        """
        self.processor = processor
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.batch_size = batch_size

        # Initialize Qdrant client only
        self.client = QdrantClient(qdrant_url)

        # Lazy initialization for embedding client
        self.embedding_client = None

        logger.info(
            f"Initialized HMDBQdrantLoader with model: {embedding_model} (lazy loading)"
        )

    def _ensure_embedding_client(self) -> None:
        """Initialize embedding client with memory-efficient settings if not already initialized."""
        if self.embedding_client is None:
            logger.info(f"Initializing FastEmbed model: {self.embedding_model}")

            try:
                # Try with memory-efficient settings
                import gc
                import psutil

                # Log memory before initialization
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024  # MB
                logger.info(f"Memory before FastEmbed init: {memory_before:.1f} MB")

                # Force garbage collection before loading
                gc.collect()

                # Initialize with explicit settings
                self.embedding_client = TextEmbedding(
                    model_name=self.embedding_model,
                    # Add providers parameter to limit ONNX providers if needed
                    # providers=["CPUExecutionProvider"]  # Uncomment if GPU issues
                )

                # Log memory after initialization
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                memory_used = memory_after - memory_before
                logger.info(
                    f"Memory after FastEmbed init: {memory_after:.1f} MB (+{memory_used:.1f} MB)"
                )

            except Exception as e:
                logger.error(
                    f"Failed to initialize FastEmbed model {self.embedding_model}: {e}"
                )
                # Try fallback to a smaller model
                logger.info("Attempting fallback to smaller embedding model...")
                try:
                    self.embedding_client = TextEmbedding(
                        model_name="sentence-transformers/all-MiniLM-L6-v2"
                    )
                    logger.warning(
                        "Using fallback model: sentence-transformers/all-MiniLM-L6-v2"
                    )
                except Exception as fallback_e:
                    logger.error(f"Fallback model also failed: {fallback_e}")
                    raise RuntimeError(
                        f"Could not initialize any embedding model. Original error: {e}"
                    )

    def _create_search_text(self, metabolite: Dict[str, Any]) -> str:
        """Create optimized text for embedding from metabolite data.

        Args:
            metabolite: Dictionary containing metabolite data

        Returns:
            Formatted text for embedding generation
        """
        parts = []

        # Primary name (weight it by repeating)
        if name := metabolite.get("name"):
            parts.extend([name, name])  # Double weight for primary name

        # All synonyms
        if synonyms := metabolite.get("synonyms"):
            parts.extend(synonyms)

        # IUPAC names
        if iupac := metabolite.get("iupac_name"):
            parts.append(iupac)
        if trad_iupac := metabolite.get("traditional_iupac"):
            parts.append(trad_iupac)

        # Chemical formula
        if formula := metabolite.get("chemical_formula"):
            parts.append(f"formula: {formula}")

        return " ".join(filter(None, parts))

    def _create_embedding_text(self, metabolite: Dict[str, Any]) -> str:
        """Create optimized text for embedding generation."""
        return self._create_search_text(metabolite)

    def _prepare_qdrant_payload(self, metabolite: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare payload for Qdrant storage.

        Args:
            metabolite: Dictionary containing metabolite data

        Returns:
            Cleaned payload dictionary for Qdrant
        """
        # Create payload with all non-None values
        payload = {}

        for key, value in metabolite.items():
            if value is not None and value != "":
                payload[key] = value

        return payload

    async def setup_collection(self) -> None:
        """Create Qdrant collection with appropriate configuration."""
        logger.info(f"Setting up collection: {self.collection_name}")

        # Delete existing collection if it exists
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted existing collection: {self.collection_name}")
        except Exception:
            # Collection might not exist
            pass

        # Create collection with BGE model dimensions (384)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=384, distance=models.Distance.COSINE
            ),
        )

        # Create payload index for HMDB ID
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="hmdb_id",
            field_schema=models.PayloadSchemaType.TEXT,
        )

        logger.info(f"Created collection: {self.collection_name}")

    async def load_metabolites(self) -> Dict[str, int]:
        """Load all metabolites into Qdrant.

        Returns:
            Dictionary with loading statistics
        """
        total_processed = 0
        total_errors = 0

        logger.info("Starting metabolite loading process...")

        # Initialize embedding client on first use
        self._ensure_embedding_client()

        try:
            async for batch in self.processor.process_metabolite_batch(self.batch_size):
                try:
                    # Filter out invalid metabolites
                    valid_metabolites = [
                        m for m in batch if m.get("hmdb_id") and m.get("name")
                    ]

                    if not valid_metabolites:
                        logger.warning("No valid metabolites in batch, skipping")
                        total_errors += len(
                            batch
                        )  # Count all as errors if none are valid
                        continue

                    # Process in smaller chunks if batch is large
                    chunk_size = min(
                        25, len(valid_metabolites)
                    )  # Limit embedding batch size
                    all_points = []

                    for chunk_start in range(0, len(valid_metabolites), chunk_size):
                        chunk_end = min(
                            chunk_start + chunk_size, len(valid_metabolites)
                        )
                        chunk_metabolites = valid_metabolites[chunk_start:chunk_end]

                        # Generate embedding texts for this chunk
                        embedding_texts = [
                            self._create_embedding_text(m) for m in chunk_metabolites
                        ]

                        # Generate embeddings (stream to avoid memory issues)
                        embeddings = []
                        for embedding in self.embedding_client.embed(embedding_texts):
                            embeddings.append(embedding)

                        # Prepare points for this chunk
                        for i, metabolite in enumerate(chunk_metabolites):
                            all_points.append(
                                models.PointStruct(
                                    id=hash(metabolite["hmdb_id"]) % (2**63),
                                    vector=embeddings[i],
                                    payload=self._prepare_qdrant_payload(metabolite),
                                )
                            )

                    # Upload to Qdrant
                    self.client.upsert(
                        collection_name=self.collection_name, points=all_points
                    )

                    processed_count = len(valid_metabolites)
                    total_processed += processed_count

                    # Progress logging every 500 metabolites
                    if total_processed % 500 == 0:
                        logger.info(
                            f"Progress: {total_processed:,} metabolites processed"
                        )

                    # Track invalid metabolites as errors
                    invalid_count = len(batch) - processed_count

                    # Clear memory references
                    del all_points, valid_metabolites
                    if invalid_count > 0:
                        total_errors += invalid_count
                        logger.warning(
                            f"Skipped {invalid_count} invalid metabolites in batch"
                        )

                    logger.debug(f"Processed batch of {processed_count} metabolites")

                except Exception as e:
                    total_errors += 1
                    logger.error(f"Error processing batch: {e}")
                    continue

            logger.info(
                f"Completed loading: {total_processed} processed, {total_errors} errors"
            )

        except Exception as e:
            logger.error(f"Fatal error during loading: {e}")
            raise

        return {"total_processed": total_processed, "total_errors": total_errors}
