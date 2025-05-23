#!/usr/bin/env python3
"""Check sizes of filtered chunks."""
import pickle
from pathlib import Path

chunk_dir = Path("/home/ubuntu/biomapper/data/filtered_embeddings")
chunks = sorted(chunk_dir.glob("filtered_chunk_*.pkl"))

print("Checking first 5 chunks:")
for i, chunk_file in enumerate(chunks[:5]):
    with open(chunk_file, 'rb') as f:
        data = pickle.load(f)
    print(f"{chunk_file.name}: {len(data):,} embeddings")