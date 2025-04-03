"""Batch processing pipeline for embeddings."""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Union
import numpy as np

from ..core.base import BaseEmbedder, BaseVectorStore
from ..core.config import default_config
from ..models.schemas import EmbedderItem


class BatchEmbeddingPipeline:
    """Pipeline for batch embedding generation and storage."""
    
    def __init__(
        self, 
        embedder: BaseEmbedder, 
        vector_store: BaseVectorStore,
        batch_size: int = 32, 
        progress_tracking: bool = True
    ):
        """Initialize the batch embedding pipeline.
        
        Args:
            embedder: Embedder implementation
            vector_store: Vector storage implementation
            batch_size: Number of items per batch
            progress_tracking: Whether to track and save progress
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.batch_size = batch_size
        self.progress_tracking = progress_tracking
        
        # Stats tracking
        self.stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "batches": 0,
            "start_time": time.time(),
            "last_update_time": time.time()
        }
    
    def process_items(self, items: List[EmbedderItem]) -> Dict[str, Any]:
        """Process a list of items.
        
        Args:
            items: List of items to embed
            
        Returns:
            Processing statistics
        """
        # Process in batches
        batches = [items[i:i+self.batch_size] for i in range(0, len(items), self.batch_size)]
        
        for batch in batches:
            self._process_batch(batch)
            
        # Update final stats
        self.stats["end_time"] = time.time()
        self.stats["duration"] = self.stats["end_time"] - self.stats["start_time"]
        
        # Show processing rate
        if self.stats["duration"] > 0:
            self.stats["items_per_second"] = self.stats["processed"] / self.stats["duration"]
            logging.info(f"Processing rate: {self.stats['items_per_second']:.2f} items/second")
            
        return self.stats
    
    def process_from_jsonl(self, jsonl_path: str, max_items: Optional[int] = None) -> Dict[str, Any]:
        """Process items from a JSONL file.
        
        Args:
            jsonl_path: Path to JSONL file
            max_items: Maximum number of items to process
            
        Returns:
            Processing statistics
        """
        items = []
        processed_count = 0
        
        logging.info(f"Processing items from {jsonl_path}")
        
        # Read items in batches to avoid loading everything into memory
        batch = []
        
        with open(jsonl_path, 'r') as f:
            for line in f:
                try:
                    # Parse JSON and validate with Pydantic model
                    data = json.loads(line)
                    item = EmbedderItem(**data)
                    batch.append(item)
                    
                    # Process a batch when it reaches batch_size
                    if len(batch) >= self.batch_size:
                        self._process_batch(batch)
                        batch = []
                        
                        # Check if we've reached the maximum
                        processed_count += self.batch_size
                        if max_items and processed_count >= max_items:
                            logging.info(f"Reached maximum of {max_items} items")
                            break
                        
                except Exception as e:
                    logging.error(f"Error parsing item: {e}")
                    self.stats["failed"] += 1
        
        # Process any remaining items in the last batch
        if batch:
            self._process_batch(batch)
        
        # Update final stats
        self.stats["end_time"] = time.time()
        self.stats["duration"] = self.stats["end_time"] - self.stats["start_time"]
        
        # Show processing rate
        if self.stats["duration"] > 0:
            self.stats["items_per_second"] = self.stats["processed"] / self.stats["duration"]
            logging.info(f"Processing rate: {self.stats['items_per_second']:.2f} items/second")
            
        return self.stats
    
    def _process_batch(self, batch: List[EmbedderItem]) -> None:
        """Process a single batch of items."""
        try:
            # Log progress
            if self.stats["batches"] % 10 == 0:
                current_time = time.time()
                elapsed = current_time - self.stats["last_update_time"]
                if elapsed > 0:
                    rate = (self.batch_size * 10) / elapsed
                    logging.info(f"Processing batch {self.stats['batches']} - {rate:.2f} items/sec")
                self.stats["last_update_time"] = current_time
            
            # Extract text for embedding
            texts = [item.primary_text for item in batch]
            
            # Generate embeddings
            embeddings = self.embedder.embed(texts)
            
            # Prepare metadata
            metadata = [
                {
                    "id": item.id,
                    "type": item.type,
                    "source": item.source,
                    **item.metadata
                }
                for item in batch
            ]
            
            # Add to vector store
            self.vector_store.add(embeddings, metadata)
            
            # Update stats
            self.stats["processed"] += len(batch)
            self.stats["successful"] += len(batch)
            self.stats["batches"] += 1
            
        except Exception as e:
            logging.error(f"Error processing batch: {e}")
            self.stats["processed"] += len(batch)
            self.stats["failed"] += len(batch)
            self.stats["batches"] += 1
