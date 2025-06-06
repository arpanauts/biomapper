#!/usr/bin/env python3
"""
Filter PubChem embeddings based on the biologically relevant CID allowlist.

This script:
1. Loads the expanded allowlist of CIDs from HMDB, ChEBI, and UniChem sources
2. Processes compressed chunks from PubChem embeddings
3. Extracts only embeddings for allowlisted CIDs
4. Saves filtered embeddings in a format ready for Qdrant indexing

Dataset structure:
- 347 tar.gz files containing JSON files
- Each JSON file has 100 embeddings (CID -> 384-dimensional vector)
- Total: ~89.4 million embeddings
"""

import json
import gzip
import tarfile
from pathlib import Path
import logging
from typing import Set, Dict, Any, List
import numpy as np
from tqdm import tqdm
import pickle
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_allowlist(allowlist_path: Path) -> Set[str]:
    """Load the CID allowlist from file."""
    logger.info(f"Loading CID allowlist from {allowlist_path}")
    
    cids = set()
    with open(allowlist_path, 'r') as f:
        for line in f:
            cid = line.strip()
            if cid:
                cids.add(cid)
    
    logger.info(f"Loaded {len(cids):,} CIDs in allowlist")
    return cids


def process_embedding_chunk(
    chunk_path: Path,
    allowlist: Set[str],
    output_dir: Path,
    chunk_idx: int
) -> Dict[str, Any]:
    """
    Process a single compressed chunk of embeddings.
    
    Each tar.gz contains JSON files with 100 embeddings each.
    Format: {CID: [384 floats], ...}
    
    Returns statistics about the processing.
    """
    stats = {
        'total_embeddings': 0,
        'filtered_embeddings': 0,
        'chunk_name': chunk_path.name,
        'json_files_processed': 0
    }
    
    filtered_embeddings = []
    
    try:
        with tarfile.open(chunk_path, 'r:gz') as tar:
            members = [m for m in tar.getmembers() if m.name.endswith('.json')]
            
            for member in tqdm(members, desc=f"Processing {chunk_path.name}", leave=False):
                if member.isfile():
                    stats['json_files_processed'] += 1
                    
                    # Extract and read the JSON file
                    f = tar.extractfile(member)
                    if f:
                        content = f.read()
                        
                        try:
                            # Parse the JSON containing 100 embeddings
                            embeddings_batch = json.loads(content)
                            
                            # Process each CID in the batch
                            for cid, vector in embeddings_batch.items():
                                stats['total_embeddings'] += 1
                                
                                # Check if CID is in allowlist
                                if cid in allowlist:
                                    embedding = {
                                        'cid': cid,
                                        'vector': vector,  # 384-dimensional list
                                        'metadata': {
                                            'source': 'pubchem',
                                            'model': 'BAAI/bge-small-en-v1.5',
                                            'chunk': chunk_path.name,
                                            'json_file': member.name
                                        }
                                    }
                                    filtered_embeddings.append(embedding)
                                    stats['filtered_embeddings'] += 1
                                    
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON {member.name}: {e}")
                        except Exception as e:
                            logger.warning(f"Error processing {member.name}: {e}")
                                
        # Save filtered embeddings for this chunk
        if filtered_embeddings:
            output_file = output_dir / f"filtered_chunk_{chunk_idx:04d}.pkl"
            with open(output_file, 'wb') as f:
                pickle.dump(filtered_embeddings, f)
            logger.info(f"Saved {len(filtered_embeddings):,} embeddings to {output_file}")
            
    except Exception as e:
        logger.error(f"Error processing chunk {chunk_path}: {e}")
    
    return stats


def filter_all_embeddings(
    embeddings_dir: Path,
    allowlist_path: Path,
    output_dir: Path,
    resume_from: int = 0
) -> None:
    """
    Filter all PubChem embedding chunks based on the allowlist.
    
    Args:
        embeddings_dir: Directory containing tar.gz files
        allowlist_path: Path to bio-relevant CIDs file
        output_dir: Directory to save filtered embeddings
        resume_from: Chunk index to resume from (for resumability)
    """
    # Load allowlist
    allowlist = load_allowlist(allowlist_path)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all chunk files
    chunk_files = sorted(embeddings_dir.glob("Compound_*.tar.gz"))
    logger.info(f"Found {len(chunk_files)} chunk files to process")
    
    # Resume functionality
    if resume_from > 0:
        chunk_files = chunk_files[resume_from:]
        logger.info(f"Resuming from chunk {resume_from}")
    
    # Process statistics
    total_stats = {
        'total_embeddings': 0,
        'filtered_embeddings': 0,
        'chunks_processed': 0,
        'json_files_processed': 0
    }
    
    # Load previous stats if resuming
    stats_file = output_dir / "processing_stats.json"
    if resume_from > 0 and stats_file.exists():
        with open(stats_file, 'r') as f:
            total_stats = json.load(f)
        logger.info(f"Loaded previous stats: {total_stats}")
    
    # Process each chunk
    for idx, chunk_path in enumerate(chunk_files):
        actual_idx = idx + resume_from
        logger.info(f"\nProcessing chunk {actual_idx + 1}/{len(chunk_files) + resume_from}: {chunk_path.name}")
        
        stats = process_embedding_chunk(chunk_path, allowlist, output_dir, actual_idx)
        
        # Update total statistics
        total_stats['total_embeddings'] += stats['total_embeddings']
        total_stats['filtered_embeddings'] += stats['filtered_embeddings']
        total_stats['chunks_processed'] += 1
        total_stats['json_files_processed'] += stats['json_files_processed']
        
        # Save progress periodically
        if (actual_idx + 1) % 10 == 0:
            with open(stats_file, 'w') as f:
                json.dump(total_stats, f, indent=2)
            
            retention_rate = (total_stats['filtered_embeddings'] / 
                            total_stats['total_embeddings'] * 100) if total_stats['total_embeddings'] > 0 else 0
            logger.info(f"\nProgress: {total_stats['chunks_processed']} chunks, "
                       f"{total_stats['filtered_embeddings']:,}/{total_stats['total_embeddings']:,} "
                       f"embeddings retained ({retention_rate:.2f}%)")
    
    # Final statistics
    retention_rate = (total_stats['filtered_embeddings'] / 
                     total_stats['total_embeddings'] * 100) if total_stats['total_embeddings'] > 0 else 0
    
    logger.info("=" * 60)
    logger.info("Filtering Complete!")
    logger.info(f"Total chunks processed: {total_stats['chunks_processed']}")
    logger.info(f"Total JSON files processed: {total_stats['json_files_processed']:,}")
    logger.info(f"Total embeddings scanned: {total_stats['total_embeddings']:,}")
    logger.info(f"Total embeddings retained: {total_stats['filtered_embeddings']:,}")
    logger.info(f"Retention rate: {retention_rate:.2f}%")
    logger.info(f"Expected ~1.4M embeddings based on 51.68% coverage of 2.7M CIDs")
    
    # Save final summary
    summary_path = output_dir / "filtering_summary.json"
    with open(summary_path, 'w') as f:
        json.dump({
            'statistics': total_stats,
            'retention_rate': retention_rate,
            'allowlist_size': len(allowlist),
            'chunks_processed': len(chunk_files) + resume_from,
            'expected_embeddings': int(len(allowlist) * 0.5168),  # Based on 51.68% coverage
            'embeddings_per_chunk': total_stats['filtered_embeddings'] / total_stats['chunks_processed'] if total_stats['chunks_processed'] > 0 else 0
        }, f, indent=2)
    
    logger.info(f"Summary saved to {summary_path}")


def create_qdrant_ready_format(filtered_dir: Path, output_path: Path) -> None:
    """
    Convert filtered embeddings to a format ready for Qdrant indexing.
    Creates a single file with all vectors and metadata.
    """
    logger.info("Creating Qdrant-ready format...")
    
    all_embeddings = []
    
    # Load all filtered chunks
    chunk_files = sorted(filtered_dir.glob("filtered_chunk_*.pkl"))
    
    for chunk_file in tqdm(chunk_files, desc="Loading filtered chunks"):
        with open(chunk_file, 'rb') as f:
            embeddings = pickle.load(f)
            all_embeddings.extend(embeddings)
    
    logger.info(f"Loaded {len(all_embeddings):,} total embeddings")
    
    # Convert to Qdrant format with integer IDs
    qdrant_data = {
        'vectors': [],
        'payloads': [],
        'ids': []
    }
    
    # Create a mapping of CID to index for consistent IDs
    cid_to_idx = {}
    
    for idx, emb in enumerate(all_embeddings):
        cid = emb['cid']
        
        # Use CID as integer ID if possible, otherwise use index
        try:
            point_id = int(cid)
        except ValueError:
            # If CID can't be converted to int, use a hash or index
            point_id = idx + 1000000000  # Offset to avoid collision
            
        cid_to_idx[cid] = point_id
        
        qdrant_data['ids'].append(point_id)
        qdrant_data['vectors'].append(emb['vector'])
        qdrant_data['payloads'].append({
            'cid': cid,
            **emb['metadata']
        })
    
    # Save in a format ready for Qdrant
    with gzip.open(output_path, 'wb') as f:
        pickle.dump(qdrant_data, f)
    
    # Save CID to ID mapping
    mapping_path = output_path.parent / "cid_to_id_mapping.json"
    with open(mapping_path, 'w') as f:
        json.dump(cid_to_idx, f)
    
    logger.info(f"Saved Qdrant-ready data to {output_path}")
    logger.info(f"Saved CID to ID mapping to {mapping_path}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Filter PubChem embeddings for biologically relevant compounds")
    parser.add_argument('--resume-from', type=int, default=0, 
                       help='Chunk index to resume from (0-based)')
    parser.add_argument('--embeddings-dir', type=str, 
                       default="/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks",
                       help='Directory containing PubChem embedding chunks')
    parser.add_argument('--allowlist', type=str,
                       default="/home/ubuntu/biomapper/data/bio_relevant_cids_expanded.txt",
                       help='Path to biologically relevant CIDs file')
    parser.add_argument('--output-dir', type=str,
                       default="/home/ubuntu/biomapper/data/filtered_embeddings",
                       help='Directory to save filtered embeddings')
    parser.add_argument('--skip-qdrant-format', action='store_true',
                       help='Skip creating Qdrant-ready format')
    
    args = parser.parse_args()
    
    # Define paths
    embeddings_dir = Path(args.embeddings_dir)
    allowlist_path = Path(args.allowlist)
    filtered_dir = Path(args.output_dir)
    qdrant_ready_path = filtered_dir.parent / "pubchem_bio_embeddings_qdrant.pkl.gz"
    
    # Check if allowlist exists
    if not allowlist_path.exists():
        logger.error(f"Allowlist not found: {allowlist_path}")
        logger.error("Please ensure the expanded allowlist exists at the specified path")
        return
    
    # Check if embeddings directory exists
    if not embeddings_dir.exists():
        logger.error(f"Embeddings directory not found: {embeddings_dir}")
        return
    
    # Filter embeddings
    logger.info("Starting embedding filtering process...")
    logger.info(f"Using allowlist: {allowlist_path}")
    logger.info(f"Processing embeddings from: {embeddings_dir}")
    logger.info(f"Saving filtered embeddings to: {filtered_dir}")
    
    filter_all_embeddings(embeddings_dir, allowlist_path, filtered_dir, args.resume_from)
    
    # Create Qdrant-ready format
    if not args.skip_qdrant_format:
        logger.info("\nCreating Qdrant-ready format...")
        create_qdrant_ready_format(filtered_dir, qdrant_ready_path)
    
    logger.info("\nAll done! Filtered embeddings are ready for Qdrant indexing.")


if __name__ == "__main__":
    main()
