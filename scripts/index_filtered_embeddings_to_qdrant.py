#!/usr/bin/env python3
"""
Index filtered PubChem embeddings to Qdrant vector database.

This script:
1. Loads the filtered embeddings from pickle files
2. Creates a Qdrant collection with proper configuration
3. Batch uploads embeddings with progress tracking
4. Supports resumability for interrupted uploads
"""

import json
import gzip
import pickle
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, 
    Distance, 
    PointStruct,
    OptimizersConfigDiff,
    HnswConfigDiff,
)
import argparse
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QdrantIndexer:
    """Handles indexing of PubChem embeddings to Qdrant."""
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        """Initialize Qdrant client."""
        self.client = QdrantClient(host=host, port=port)
        logger.info(f"Connected to Qdrant at {host}:{port}")
        
    def create_collection(self, collection_name: str, vector_size: int = 384) -> None:
        """Create Qdrant collection with optimal settings for semantic search."""
        
        # Check if collection already exists
        collections = self.client.get_collections().collections
        if any(col.name == collection_name for col in collections):
            logger.warning(f"Collection '{collection_name}' already exists")
            
            # Get collection info
            info = self.client.get_collection(collection_name)
            logger.info(f"Existing collection has {info.points_count} points")
            
            # In non-interactive mode, use the existing collection
            logger.info("Using existing collection (non-interactive mode)")
            return
        
        # Create collection with optimized settings
        logger.info(f"Creating collection '{collection_name}' with vector size {vector_size}")
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE  # Cosine similarity for semantic search
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=20000,  # Start indexing after 20k vectors
                flush_interval_sec=5,  # Flush to disk every 5 seconds
                max_segment_size=200000  # Max vectors per segment
            ),
            hnsw_config=HnswConfigDiff(
                m=16,  # Number of connections per node
                ef_construct=100,  # Beam size during construction
                full_scan_threshold=10000  # Use HNSW after 10k vectors
            )
        )
        
        logger.info(f"Collection '{collection_name}' created successfully")
        
    def load_embeddings_batch(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load embeddings from a filtered pickle file."""
        logger.info(f"Loading embeddings from {file_path}")
        
        if file_path.suffix == '.gz':
            with gzip.open(file_path, 'rb') as f:
                data = pickle.load(f)
        else:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
        
        return data
        
    def prepare_points(self, embeddings: List[Dict[str, Any]], 
                      offset: int = 0) -> List[PointStruct]:
        """Convert embeddings to Qdrant points format."""
        points = []
        
        for idx, emb in enumerate(embeddings):
            # Try to use CID as ID, fallback to offset index
            try:
                point_id = int(emb['cid'])
            except (ValueError, KeyError):
                point_id = offset + idx + 1000000000  # Large offset to avoid collisions
            
            # Prepare payload
            payload = {
                'cid': emb['cid'],
                **emb.get('metadata', {})
            }
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=emb['vector'],
                payload=payload
            )
            points.append(point)
        
        return points
    
    def upload_batch(self, collection_name: str, points: List[PointStruct], 
                    batch_size: int = 1000) -> None:
        """Upload points to Qdrant in batches."""
        total_points = len(points)
        
        for i in tqdm(range(0, total_points, batch_size), 
                     desc="Uploading to Qdrant"):
            batch = points[i:i + batch_size]
            
            # Upload with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.client.upsert(
                        collection_name=collection_name,
                        points=batch
                    )
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Upload failed (attempt {attempt + 1}): {e}")
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        logger.error(f"Failed to upload batch after {max_retries} attempts")
                        raise
        
    def index_filtered_embeddings(self, input_path: Path, collection_name: str,
                                 batch_size: int = 5000, resume_from: int = 0) -> None:
        """Main indexing function for filtered embeddings."""
        
        # Handle different input types
        if input_path.is_file():
            # Single file containing all embeddings
            if 'qdrant' in input_path.name:
                logger.info("Loading Qdrant-ready format")
                with gzip.open(input_path, 'rb') as f:
                    data = pickle.load(f)
                
                # Convert to points
                points = []
                for idx, (point_id, vector, payload) in enumerate(
                    zip(data['ids'], data['vectors'], data['payloads'])
                ):
                    point = PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                    points.append(point)
                
                # Upload all points
                logger.info(f"Uploading {len(points):,} points to Qdrant")
                self.upload_batch(collection_name, points, batch_size)
                
            else:
                # Regular filtered embeddings file
                embeddings = self.load_embeddings_batch(input_path)
                points = self.prepare_points(embeddings)
                self.upload_batch(collection_name, points, batch_size)
                
        else:
            # Directory containing multiple filtered chunks
            chunk_files = sorted(input_path.glob("filtered_chunk_*.pkl"))
            logger.info(f"Found {len(chunk_files)} chunk files to index")
            
            # Resume functionality
            if resume_from > 0:
                chunk_files = chunk_files[resume_from:]
                logger.info(f"Resuming from chunk {resume_from}")
            
            # Process each chunk
            total_indexed = 0
            for idx, chunk_file in enumerate(chunk_files):
                actual_idx = idx + resume_from
                logger.info(f"\nProcessing chunk {actual_idx + 1}/{len(chunk_files) + resume_from}")
                
                try:
                    embeddings = self.load_embeddings_batch(chunk_file)
                    points = self.prepare_points(embeddings, offset=total_indexed)
                    self.upload_batch(collection_name, points, batch_size)
                    
                    total_indexed += len(embeddings)
                    logger.info(f"Total indexed so far: {total_indexed:,}")
                    
                    # Save progress
                    if (actual_idx + 1) % 10 == 0:
                        progress_file = input_path / "indexing_progress.json"
                        with open(progress_file, 'w') as f:
                            json.dump({
                                'last_chunk_idx': actual_idx,
                                'total_indexed': total_indexed,
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                            }, f, indent=2)
                        
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_file}: {e}")
                    raise
        
        # Final statistics
        info = self.client.get_collection(collection_name)
        logger.info("=" * 60)
        logger.info("Indexing Complete!")
        logger.info(f"Collection: {collection_name}")
        logger.info(f"Total points indexed: {info.points_count:,}")
        logger.info(f"Vector dimension: {info.config.params.vectors.size}")
        logger.info(f"Distance metric: {info.config.params.vectors.distance}")
    
    def test_search(self, collection_name: str, test_cids: List[str]) -> None:
        """Test the indexed collection with sample searches."""
        logger.info("\nTesting search functionality...")
        
        # Get collection info
        info = self.client.get_collection(collection_name)
        
        for cid in test_cids:
            try:
                # Search by CID in payload
                results = self.client.scroll(
                    collection_name=collection_name,
                    scroll_filter={
                        "must": [
                            {"key": "cid", "match": {"value": cid}}
                        ]
                    },
                    limit=1
                )
                
                if results[0]:
                    point = results[0][0]
                    logger.info(f"Found CID {cid}: ID={point.id}, payload={point.payload}")
                else:
                    logger.warning(f"CID {cid} not found in collection")
                    
            except Exception as e:
                logger.error(f"Error searching for CID {cid}: {e}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Index filtered PubChem embeddings to Qdrant"
    )
    parser.add_argument('--input-path', type=str, required=True,
                       help='Path to filtered embeddings (file or directory)')
    parser.add_argument('--qdrant-host', type=str, default='localhost',
                       help='Qdrant server host')
    parser.add_argument('--qdrant-port', type=int, default=6333,
                       help='Qdrant server port')
    parser.add_argument('--collection-name', type=str, 
                       default='pubchem_bge_small_v1_5',
                       help='Name of Qdrant collection')
    parser.add_argument('--batch-size', type=int, default=5000,
                       help='Batch size for uploading')
    parser.add_argument('--resume-from', type=int, default=0,
                       help='Resume from chunk index (for directory input)')
    parser.add_argument('--test-cids', type=str, nargs='+',
                       help='Test CIDs to verify indexing')
    
    args = parser.parse_args()
    
    # Initialize indexer
    indexer = QdrantIndexer(host=args.qdrant_host, port=args.qdrant_port)
    
    # Create collection
    indexer.create_collection(args.collection_name)
    
    # Index embeddings
    input_path = Path(args.input_path)
    if not input_path.exists():
        logger.error(f"Input path not found: {input_path}")
        return
    
    logger.info(f"Starting indexing from: {input_path}")
    indexer.index_filtered_embeddings(
        input_path=input_path,
        collection_name=args.collection_name,
        batch_size=args.batch_size,
        resume_from=args.resume_from
    )
    
    # Test search if requested
    if args.test_cids:
        indexer.test_search(args.collection_name, args.test_cids)
    
    logger.info("\nIndexing pipeline complete!")


if __name__ == "__main__":
    main()
