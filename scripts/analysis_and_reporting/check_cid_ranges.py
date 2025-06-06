#!/usr/bin/env python3
"""
Check CID ranges in embeddings vs allowlist.
"""

import json
import tarfile
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check first few CIDs in allowlist
allowlist_path = Path("/home/ubuntu/biomapper/data/bio_relevant_cids_expanded.txt")
logger.info("First 10 CIDs in allowlist:")
with open(allowlist_path, 'r') as f:
    for i, line in enumerate(f):
        if i >= 10:
            break
        print(f"  {line.strip()}")

# Check CID range in first embedding file
chunk_path = Path("/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks/Compound_000000001_000500000.tar.gz")
with tarfile.open(chunk_path, 'r:gz') as tar:
    members = [m for m in tar.getmembers() if m.name.endswith('.json')]
    
    # Get first JSON file
    member = members[0]
    f = tar.extractfile(member)
    if f:
        content = f.read()
        embeddings_batch = json.loads(content)
        cids = list(embeddings_batch.keys())
        logger.info(f"\nFirst file {member.name} has {len(cids)} CIDs")
        logger.info(f"CID range: {min(cids)} to {max(cids)}")
        logger.info("First 10 CIDs in embeddings:")
        for cid in sorted(cids)[:10]:
            print(f"  {cid}")