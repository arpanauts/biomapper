#!/usr/bin/env python3
"""
Memory-efficient setup script to load HMDB data into Qdrant with lightweight models.

Usage:
    python scripts/setup_hmdb_qdrant_lightweight.py --xml-path /path/to/hmdb_metabolites.xml
"""

import asyncio
import logging
import argparse
import sys
import time
import gc
import psutil
import numpy as np
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biomapper.processors.hmdb import HMDBProcessor
from biomapper.rag.metabolite_search import MetaboliteSearcher


class LightweightHMDBQdrantLoader:
    """Memory-efficient HMDB loader with alternative embedding approaches."""
    
    def __init__(
        self,
        processor: HMDBProcessor,
        qdrant_url: str = "localhost:6333",
        collection_name: str = "hmdb_metabolites",
        embedding_approach: str = "fastembed-mini",  # or "sentence-transformers", "tfidf"
        batch_size: int = 50,  # Smaller default batch size
    ):
        """Initialize with memory-efficient settings."""
        self.processor = processor
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.embedding_approach = embedding_approach
        self.batch_size = batch_size
        
        # Import here to avoid loading unnecessary dependencies
        from qdrant_client import QdrantClient
        self.client = QdrantClient(qdrant_url)
        
        # Lazy initialization for embedding model
        self.embedding_model = None
        self.vector_size = None
        
        # Log memory at initialization
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logging.info(f"Initial memory usage: {memory_mb:.1f} MB")

    def _get_embedding_model(self):
        """Initialize embedding model based on approach with memory monitoring."""
        if self.embedding_model is not None:
            return self.embedding_model
            
        logging.info(f"Initializing embedding model: {self.embedding_approach}")
        
        # Memory monitoring
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024
        logging.info(f"Memory before model init: {memory_before:.1f} MB")
        
        try:
            gc.collect()  # Clean up before loading
            
            if self.embedding_approach == "fastembed-mini":
                # Try smallest FastEmbed model first
                from fastembed import TextEmbedding
                model_options = [
                    "sentence-transformers/all-MiniLM-L6-v2",  # 384D, smallest
                    "BAAI/bge-small-en-v1.5",  # 384D, small
                ]
                
                for model_name in model_options:
                    try:
                        logging.info(f"Trying FastEmbed model: {model_name}")
                        self.embedding_model = TextEmbedding(model_name=model_name)
                        self.vector_size = 384
                        logging.info(f"Successfully loaded: {model_name}")
                        break
                    except Exception as e:
                        logging.warning(f"Failed to load {model_name}: {e}")
                        continue
                        
                if self.embedding_model is None:
                    raise RuntimeError("All FastEmbed models failed to load")
                    
            elif self.embedding_approach == "sentence-transformers":
                # Use sentence-transformers directly with CPU optimization
                from sentence_transformers import SentenceTransformer
                import torch
                
                # Force CPU usage to avoid GPU memory issues
                device = "cpu"
                model_name = "all-MiniLM-L6-v2"  # Small and efficient
                
                logging.info(f"Loading SentenceTransformer: {model_name} on {device}")
                self.embedding_model = SentenceTransformer(model_name, device=device)
                self.vector_size = 384
                
            elif self.embedding_approach == "tfidf":
                # Fallback to TF-IDF for extremely low memory scenarios
                from sklearn.feature_extraction.text import TfidfVectorizer
                
                logging.info("Using TF-IDF vectorizer (no pre-trained model)")
                self.embedding_model = TfidfVectorizer(
                    max_features=384,  # Match vector size
                    stop_words='english',
                    ngram_range=(1, 2),
                    max_df=0.95,
                    min_df=2
                )
                self.vector_size = 384
                
            else:
                raise ValueError(f"Unknown embedding approach: {self.embedding_approach}")
                
            # Log memory usage after loading
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_used = memory_after - memory_before
            logging.info(f"Memory after model init: {memory_after:.1f} MB (+{memory_used:.1f} MB)")
            
            return self.embedding_model
            
        except Exception as e:
            logging.error(f"Failed to initialize embedding model: {e}")
            raise

    def _generate_embeddings(self, texts):
        """Generate embeddings with the selected approach."""
        model = self._get_embedding_model()
        
        if self.embedding_approach in ["fastembed-mini"]:
            # FastEmbed approach
            return list(model.embed(texts))
            
        elif self.embedding_approach == "sentence-transformers":
            # SentenceTransformers approach
            return model.encode(texts, convert_to_numpy=True)
            
        elif self.embedding_approach == "tfidf":
            # TF-IDF approach - needs to be fit first
            if not hasattr(model, 'vocabulary_'):
                # For TF-IDF, we need to fit on all texts first
                # This is a simplified approach - in practice you'd fit on a larger corpus
                logging.info("Fitting TF-IDF model on sample texts...")
                model.fit(texts)
            
            vectors = model.transform(texts).toarray()
            
            # Pad or truncate to exact vector size
            if vectors.shape[1] != self.vector_size:
                if vectors.shape[1] < self.vector_size:
                    # Pad with zeros
                    padding = self.vector_size - vectors.shape[1]
                    vectors = np.pad(vectors, ((0, 0), (0, padding)), mode='constant')
                else:
                    # Truncate
                    vectors = vectors[:, :self.vector_size]
                    
            return vectors
            
        else:
            raise ValueError(f"Unknown embedding approach: {self.embedding_approach}")

    async def setup_collection(self) -> None:
        """Create Qdrant collection with appropriate configuration."""
        from qdrant_client.http import models
        
        logging.info(f"Setting up collection: {self.collection_name}")
        
        # Ensure we know the vector size
        if self.vector_size is None:
            self._get_embedding_model()  # This will set vector_size
        
        # Delete existing collection if it exists
        try:
            self.client.delete_collection(self.collection_name)
            logging.info(f"Deleted existing collection: {self.collection_name}")
        except Exception:
            pass  # Collection might not exist
        
        # Create collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size, 
                distance=models.Distance.COSINE
            ),
        )
        
        # Create payload index for HMDB ID
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="hmdb_id",
            field_schema=models.PayloadSchemaType.TEXT,
        )
        
        logging.info(f"Created collection: {self.collection_name}")

    async def load_metabolites(self):
        """Load metabolites with memory monitoring."""
        from qdrant_client.http import models
        import numpy as np
        
        total_processed = 0
        total_errors = 0
        
        logging.info("Starting memory-efficient metabolite loading...")
        
        try:
            async for batch in self.processor.process_metabolite_batch(self.batch_size):
                try:
                    # Filter valid metabolites
                    valid_metabolites = [
                        m for m in batch if m.get("hmdb_id") and m.get("name")
                    ]
                    
                    if not valid_metabolites:
                        total_errors += len(batch)
                        continue
                    
                    # Create embedding texts
                    embedding_texts = []
                    for metabolite in valid_metabolites:
                        parts = []
                        
                        # Primary name (weighted)
                        if name := metabolite.get("name"):
                            parts.extend([name, name])
                        
                        # Synonyms
                        if synonyms := metabolite.get("synonyms"):
                            parts.extend(synonyms[:3])  # Limit synonyms to save memory
                        
                        # Formula
                        if formula := metabolite.get("chemical_formula"):
                            parts.append(f"formula: {formula}")
                        
                        embedding_texts.append(" ".join(filter(None, parts)))
                    
                    # Generate embeddings with memory monitoring
                    process = psutil.Process()
                    memory_before = process.memory_info().rss / 1024 / 1024
                    
                    embeddings = self._generate_embeddings(embedding_texts)
                    
                    memory_after = process.memory_info().rss / 1024 / 1024
                    logging.debug(f"Embedding generation used {memory_after - memory_before:.1f} MB")
                    
                    # Prepare points for Qdrant
                    points = []
                    for i, metabolite in enumerate(valid_metabolites):
                        # Clean payload
                        payload = {k: v for k, v in metabolite.items() 
                                 if v is not None and v != ""}
                        
                        points.append(
                            models.PointStruct(
                                id=hash(metabolite["hmdb_id"]) % (2**63),
                                vector=embeddings[i].tolist() if hasattr(embeddings[i], 'tolist') else embeddings[i],
                                payload=payload,
                            )
                        )
                    
                    # Upload to Qdrant
                    self.client.upsert(
                        collection_name=self.collection_name, 
                        points=points
                    )
                    
                    processed_count = len(valid_metabolites)
                    total_processed += processed_count
                    
                    # Progress logging
                    if total_processed % 250 == 0:  # More frequent logging for smaller batches
                        memory_current = process.memory_info().rss / 1024 / 1024
                        logging.info(f"Progress: {total_processed:,} metabolites processed, Memory: {memory_current:.1f} MB")
                    
                    # Cleanup
                    del points, embeddings, embedding_texts, valid_metabolites
                    gc.collect()
                    
                    invalid_count = len(batch) - processed_count
                    if invalid_count > 0:
                        total_errors += invalid_count
                        
                except Exception as e:
                    total_errors += len(batch) if batch else 1
                    logging.error(f"Error processing batch: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Fatal error during loading: {e}")
            raise
            
        return {"total_processed": total_processed, "total_errors": total_errors}


async def main():
    parser = argparse.ArgumentParser(description="Memory-efficient HMDB metabolite loading")
    parser.add_argument("--xml-path", type=Path, required=True, help="Path to HMDB XML file")
    parser.add_argument("--qdrant-url", type=str, default="localhost:6333", help="Qdrant URL")
    parser.add_argument("--collection-name", type=str, default="hmdb_metabolites_lite", help="Collection name")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size (smaller = less memory)")
    parser.add_argument("--embedding-approach", type=str, default="fastembed-mini",
                       choices=["fastembed-mini", "sentence-transformers", "tfidf"],
                       help="Embedding approach to use")
    parser.add_argument("--log-level", type=str, default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"hmdb_qdrant_lightweight_{args.embedding_approach}.log")
        ]
    )
    
    if not args.xml_path.exists():
        logging.error(f"XML file not found: {args.xml_path}")
        return 1
    
    logging.info(f"Starting lightweight HMDB loading with {args.embedding_approach}")
    logging.info(f"Batch size: {args.batch_size} (smaller batches = less memory usage)")
    
    try:
        # Initialize components
        processor = HMDBProcessor(args.xml_path)
        loader = LightweightHMDBQdrantLoader(
            processor=processor,
            qdrant_url=args.qdrant_url,
            collection_name=args.collection_name,
            embedding_approach=args.embedding_approach,
            batch_size=args.batch_size
        )
        
        # Setup and load
        await loader.setup_collection()
        
        start_time = time.time()
        stats = await loader.load_metabolites()
        elapsed_time = time.time() - start_time
        
        # Report results
        logging.info("=" * 50)
        logging.info("LIGHTWEIGHT LOADING COMPLETED")
        logging.info("=" * 50)
        logging.info(f"Embedding approach: {args.embedding_approach}")
        logging.info(f"Total processed: {stats['total_processed']:,}")
        logging.info(f"Total errors: {stats['total_errors']:,}")
        logging.info(f"Elapsed time: {elapsed_time:.1f} seconds")
        
        if stats['total_processed'] > 0:
            rate = stats['total_processed'] / elapsed_time
            logging.info(f"Processing rate: {rate:.1f} metabolites/second")
        
        # Final memory check
        process = psutil.Process()
        final_memory = process.memory_info().rss / 1024 / 1024
        logging.info(f"Final memory usage: {final_memory:.1f} MB")
        
        return 0
        
    except Exception as e:
        logging.error(f"Setup failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)