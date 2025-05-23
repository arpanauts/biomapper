#!/usr/bin/env python3
"""
Test semantic search with actual text embeddings.
"""

import json
import time
from qdrant_client import QdrantClient
from fastembed import TextEmbedding
import numpy as np

# Initialize clients
client = QdrantClient(host="localhost", port=6333)
embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

print("Testing semantic search with metabolite names...")
print("="*60)

# Test metabolite names
test_queries = [
    "glucose",
    "adenosine triphosphate",
    "cholesterol",
    "vitamin D3",
    "aspirin",
    "caffeine",
    "dopamine",
    "serotonin"
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    
    # Generate embedding for the query
    query_embedding = list(embedder.embed([query]))[0].tolist()
    
    # Search in Qdrant
    start_time = time.time()
    results = client.query_points(
        collection_name="pubchem_bge_small_v1_5",
        query=query_embedding,
        limit=5
    )
    search_time = (time.time() - start_time) * 1000
    
    print(f"Search time: {search_time:.2f}ms")
    print(f"Top 5 similar compounds:")
    
    for i, result in enumerate(results.points):
        cid = result.payload.get('cid', 'N/A')
        score = result.score
        print(f"  {i+1}. CID: {cid}, Score: {score:.4f}")
        
        # For the top result, we could fetch more info from PubChem API
        # if we had it implemented

print("\n" + "="*60)
print("\nTesting with IUPAC-like names...")

technical_queries = [
    "2-acetoxybenzoic acid",  # aspirin
    "1,3,7-trimethylxanthine",  # caffeine
    "(2S,3S,4R,5R)-2,3,4,5,6-pentahydroxyhexanal",  # glucose (open form)
]

for query in technical_queries:
    print(f"\nQuery: '{query}'")
    
    # Generate embedding
    query_embedding = list(embedder.embed([query]))[0].tolist()
    
    # Search
    results = client.query_points(
        collection_name="pubchem_bge_small_v1_5",
        query=query_embedding,
        limit=3
    )
    
    print(f"Top 3 similar compounds:")
    for i, result in enumerate(results.points):
        cid = result.payload.get('cid', 'N/A')
        score = result.score
        print(f"  {i+1}. CID: {cid}, Score: {score:.4f}")

# Let's also check which CIDs are actually in our filtered dataset
print("\n" + "="*60)
print("\nChecking specific biologically relevant CIDs:")

# These are known metabolite CIDs we might expect to find
known_metabolite_cids = {
    "5793": "glucose",
    "5957": "adenosine triphosphate (ATP)",
    "5997": "cholesterol", 
    "5280795": "vitamin D3",
    "2244": "aspirin",
    "2519": "caffeine",
    "681": "dopamine",
    "5202": "serotonin"
}

found_count = 0
for cid, name in known_metabolite_cids.items():
    results, _ = client.scroll(
        collection_name="pubchem_bge_small_v1_5",
        scroll_filter={
            "must": [{"key": "cid", "match": {"value": cid}}]
        },
        limit=1
    )
    if results:
        print(f"✓ CID {cid} ({name}) is in the collection")
        found_count += 1
    else:
        print(f"✗ CID {cid} ({name}) not found")

print(f"\nFound {found_count}/{len(known_metabolite_cids)} known metabolites")

# Get some statistics about the CID distribution
print("\n" + "="*60)
print("\nCID distribution sample:")
sample_cids = []
for offset in [0, 100000, 500000, 1000000, 1500000, 2000000]:
    results, _ = client.scroll(
        collection_name="pubchem_bge_small_v1_5",
        limit=5,
        offset=offset,
        with_payload=True,
        with_vectors=False
    )
    if results:
        cids = [int(p.payload.get('cid', 0)) for p in results]
        sample_cids.extend(cids)

if sample_cids:
    print(f"Sample CID range: {min(sample_cids):,} to {max(sample_cids):,}")
    print(f"Sample CIDs: {sorted(sample_cids[:10])}")

print("\nSemantic search testing complete!")