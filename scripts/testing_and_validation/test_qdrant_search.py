#!/usr/bin/env python3
"""
Test Qdrant search functionality with sample metabolite queries.
"""

import json
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import numpy as np

# Initialize Qdrant client
client = QdrantClient(host="localhost", port=6333)

# Get collection info
collection_info = client.get_collection("pubchem_bge_small_v1_5")
print(f"Collection status: {collection_info.status}")
print(f"Total points: {collection_info.points_count:,}")
print(f"Indexed vectors: {collection_info.indexed_vectors_count:,}")
print(f"Vector dimensions: {collection_info.config.params.vectors.size}")
print("\n" + "="*60 + "\n")

# Test 1: Search with a random vector
print("Test 1: Random vector search")
random_vector = np.random.randn(384).tolist()
start_time = time.time()
results = client.search(
    collection_name="pubchem_bge_small_v1_5",
    query_vector=random_vector,
    limit=5
)
search_time = (time.time() - start_time) * 1000
print(f"Search time: {search_time:.2f}ms")
print(f"Found {len(results)} results")
for i, result in enumerate(results):
    print(f"  {i+1}. CID: {result.payload.get('cid', 'N/A')}, Score: {result.score:.4f}")
print("\n" + "="*60 + "\n")

# Test 2: Retrieve specific CIDs by payload filter
print("Test 2: Search by CID in payload")
test_cids = ["2", "5", "10", "100", "1000", "5090", "52222", "2724399"]
found_cids = []

for cid in test_cids:
    try:
        results, _ = client.scroll(
            collection_name="pubchem_bge_small_v1_5",
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="cid",
                        match=MatchValue(value=cid)
                    )
                ]
            ),
            limit=1
        )
        if results:
            found_cids.append(cid)
            print(f"✓ Found CID {cid}")
        else:
            print(f"✗ CID {cid} not found")
    except Exception as e:
        print(f"✗ Error searching for CID {cid}: {e}")

print(f"\nFound {len(found_cids)} out of {len(test_cids)} test CIDs")
print("\n" + "="*60 + "\n")

# Test 3: Get a sample of points to see what's actually indexed
print("Test 3: Sample of indexed points")
sample_results, _ = client.scroll(
    collection_name="pubchem_bge_small_v1_5",
    limit=10,
    with_payload=True,
    with_vectors=False
)

print(f"Sample of {len(sample_results)} indexed compounds:")
for i, point in enumerate(sample_results):
    cid = point.payload.get('cid', 'N/A')
    source = point.payload.get('source', 'N/A')
    chunk = point.payload.get('chunk', 'N/A')
    print(f"  {i+1}. ID: {point.id}, CID: {cid}, Source: {source}")
print("\n" + "="*60 + "\n")

# Test 4: Performance test with multiple searches
print("Test 4: Performance benchmark (10 searches)")
search_times = []
for i in range(10):
    random_vector = np.random.randn(384).tolist()
    start_time = time.time()
    results = client.search(
        collection_name="pubchem_bge_small_v1_5",
        query_vector=random_vector,
        limit=10
    )
    search_time = (time.time() - start_time) * 1000
    search_times.append(search_time)

avg_time = np.mean(search_times)
min_time = np.min(search_times)
max_time = np.max(search_times)

print(f"Average search time: {avg_time:.2f}ms")
print(f"Min search time: {min_time:.2f}ms")
print(f"Max search time: {max_time:.2f}ms")
print(f"All times: {[f'{t:.2f}ms' for t in search_times]}")

# Test 5: Check vector similarity between close points
print("\n" + "="*60 + "\n")
print("Test 5: Vector similarity check")
# Get one point with its vector
sample_point, _ = client.scroll(
    collection_name="pubchem_bge_small_v1_5",
    limit=1,
    with_payload=True,
    with_vectors=True
)

if sample_point:
    point = sample_point[0]
    print(f"Using CID {point.payload.get('cid')} as reference")
    
    # Search using its own vector
    results = client.search(
        collection_name="pubchem_bge_small_v1_5",
        query_vector=point.vector,
        limit=5
    )
    
    print("Nearest neighbors:")
    for i, result in enumerate(results):
        print(f"  {i+1}. CID: {result.payload.get('cid')}, Score: {result.score:.6f}")
    
    # The first result should be itself with score ~1.0 (cosine similarity)
    if results and results[0].score > 0.999:
        print("✓ Self-similarity check passed")
    else:
        print("✗ Self-similarity check failed")

print("\n" + "="*60)
print("All tests completed!")