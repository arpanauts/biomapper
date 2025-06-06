#!/usr/bin/env python3
"""
Quick test of filtering logic on a small sample.
"""

import json
import tarfile
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load a small sample of the allowlist
allowlist_path = Path("/home/ubuntu/biomapper/data/bio_relevant_cids_expanded.txt")
logger.info(f"Loading allowlist from {allowlist_path}")

allowlist = set()
with open(allowlist_path, 'r') as f:
    for i, line in enumerate(f):
        if i >= 1000:  # Just load first 1000 CIDs for testing
            break
        cid = line.strip()
        if cid:
            allowlist.add(cid)

logger.info(f"Loaded {len(allowlist)} CIDs for testing")

# Process first few JSON files from first chunk
chunk_path = Path("/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks/Compound_000000001_000500000.tar.gz")
logger.info(f"Opening {chunk_path}")

total_embeddings = 0
filtered_embeddings = 0
files_processed = 0

with tarfile.open(chunk_path, 'r:gz') as tar:
    members = [m for m in tar.getmembers() if m.name.endswith('.json')]
    logger.info(f"Found {len(members)} JSON files in chunk")
    
    # Process only first 5 files
    for member in members[:5]:
        if member.isfile():
            files_processed += 1
            f = tar.extractfile(member)
            if f:
                content = f.read()
                try:
                    embeddings_batch = json.loads(content)
                    logger.info(f"File {member.name}: {len(embeddings_batch)} embeddings")
                    
                    # Check a few embeddings
                    for i, (cid, vector) in enumerate(embeddings_batch.items()):
                        total_embeddings += 1
                        if cid in allowlist:
                            filtered_embeddings += 1
                            if i < 3:  # Show first 3 matches
                                logger.info(f"  Found match: CID {cid}, vector dims: {len(vector)}")
                        
                except Exception as e:
                    logger.error(f"Error parsing {member.name}: {e}")

logger.info(f"\nTest Summary:")
logger.info(f"Files processed: {files_processed}")
logger.info(f"Total embeddings: {total_embeddings}")
logger.info(f"Filtered embeddings: {filtered_embeddings}")
logger.info(f"Filter rate: {filtered_embeddings/total_embeddings*100:.2f}%" if total_embeddings > 0 else "N/A")