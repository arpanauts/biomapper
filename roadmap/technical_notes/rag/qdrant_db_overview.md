# Qdrant Database Overview for Biomapper

## Introduction

This document provides a comprehensive overview of the Qdrant vector database implementation for Biomapper's RAG-based metabolite mapping system. It includes setup instructions, usage tutorials, and performance benchmarks based on our production deployment.

## System Overview

### What is Qdrant?

Qdrant is a high-performance vector similarity search engine designed for storing, searching, and managing vector embeddings with additional payload data. In Biomapper, we use it to enable semantic search across 2.2 million biologically relevant PubChem compounds.

### Our Implementation Stats

- **Total vectors indexed**: 2,217,373 biologically relevant compounds
- **Vector dimensions**: 384 (from BAAI/bge-small-en-v1.5 model)
- **Distance metric**: Cosine similarity
- **Average search latency**: 4.85ms
- **Storage requirement**: ~3.5GB on disk
- **Status**: Production-ready as of May 23, 2025

## Setup Instructions

### 1. Starting Qdrant

Qdrant runs as a Docker container. To start it:

```bash
cd /home/ubuntu/biomapper/docker/qdrant
docker compose up -d
```

To check if it's running:
```bash
docker ps | grep qdrant
```

### 2. Accessing Qdrant

- **HTTP API**: http://localhost:6333
- **gRPC API**: localhost:6334
- **Web Dashboard**: http://localhost:6333/dashboard

### 3. Verifying Health

```bash
curl http://localhost:6333/health
```

## Collection Details

### Collection Name: `pubchem_bge_small_v1_5`

This collection contains embeddings for biologically relevant PubChem compounds filtered from:
- HMDB (Human Metabolome Database)
- ChEBI (Chemical Entities of Biological Interest)
- UniChem cross-references (including ChEMBL, DrugBank, KEGG, etc.)

### Configuration

```json
{
  "vectors": {
    "size": 384,
    "distance": "Cosine"
  },
  "optimizers": {
    "indexing_threshold": 20000,
    "max_segment_size": 200000
  },
  "hnsw_config": {
    "m": 16,
    "ef_construct": 100,
    "full_scan_threshold": 10000
  }
}
```

## Usage Tutorial

### 1. Basic Search with Python

```python
from qdrant_client import QdrantClient
import numpy as np

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

# Example: Search with a random vector
random_vector = np.random.randn(384).tolist()
results = client.query_points(
    collection_name="pubchem_bge_small_v1_5",
    query=random_vector,
    limit=5
)

# Process results
for result in results.points:
    cid = result.payload.get('cid')
    score = result.score
    print(f"CID: {cid}, Score: {score:.4f}")
```

### 2. Semantic Search with Text

To search using metabolite names, you need to first embed the text:

```python
from qdrant_client import QdrantClient
from fastembed import TextEmbedding

# Initialize clients
client = QdrantClient(host="localhost", port=6333)
embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Search for a metabolite
metabolite_name = "glucose"
query_embedding = list(embedder.embed([metabolite_name]))[0].tolist()

# Perform semantic search
results = client.query_points(
    collection_name="pubchem_bge_small_v1_5",
    query=query_embedding,
    limit=10
)

# Display results
print(f"Top matches for '{metabolite_name}':")
for i, result in enumerate(results.points, 1):
    print(f"{i}. CID: {result.payload['cid']}, Score: {result.score:.4f}")
```

### 3. Filtering by Payload

Search for specific CIDs:

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Search for a specific CID
cid_to_find = "5280795"  # Vitamin D3
results, _ = client.scroll(
    collection_name="pubchem_bge_small_v1_5",
    scroll_filter=Filter(
        must=[
            FieldCondition(
                key="cid",
                match=MatchValue(value=cid_to_find)
            )
        ]
    ),
    limit=1
)

if results:
    print(f"Found CID {cid_to_find}")
else:
    print(f"CID {cid_to_find} not in collection")
```

### 4. Batch Search

For processing multiple queries efficiently:

```python
# Multiple metabolite queries
metabolites = ["aspirin", "caffeine", "dopamine", "serotonin"]

# Embed all queries
query_embeddings = list(embedder.embed(metabolites))

# Search for each
for metabolite, embedding in zip(metabolites, query_embeddings):
    results = client.query_points(
        collection_name="pubchem_bge_small_v1_5",
        query=embedding.tolist(),
        limit=5
    )
    
    print(f"\n{metabolite}:")
    for result in results.points[:3]:
        print(f"  CID: {result.payload['cid']}, Score: {result.score:.4f}")
```

## Performance Benchmarks

Based on our testing (May 23, 2025):

### Search Latency
- **Average**: 4.85ms
- **Minimum**: 3.73ms
- **Maximum**: 16.58ms
- **95th percentile**: ~7.5ms

### Throughput
- **Single-threaded**: ~200 queries/second
- **Expected with parallelism**: 1000+ queries/second

### Accuracy
- **Self-similarity check**:  Passed (score = 1.0)
- **Semantic relevance**: Good (scores 0.62-0.70 for exact matches)

## Common Use Cases

### 1. Metabolite Name Resolution

When traditional identifier mapping fails:

```python
def find_metabolite_candidates(metabolite_name, top_k=5):
    """Find potential PubChem CIDs for a metabolite name."""
    
    # Embed the query
    embedding = list(embedder.embed([metabolite_name]))[0].tolist()
    
    # Search
    results = client.query_points(
        collection_name="pubchem_bge_small_v1_5",
        query=embedding,
        limit=top_k
    )
    
    # Return candidates with scores
    candidates = []
    for result in results.points:
        candidates.append({
            'cid': result.payload['cid'],
            'score': result.score,
            'confidence': 'high' if result.score > 0.7 else 'medium'
        })
    
    return candidates
```

### 2. Similarity Search

Find compounds similar to a known CID:

```python
def find_similar_compounds(cid, limit=10):
    """Find compounds similar to a given CID."""
    
    # First, get the vector for this CID
    results, _ = client.scroll(
        collection_name="pubchem_bge_small_v1_5",
        scroll_filter=Filter(
            must=[FieldCondition(key="cid", match=MatchValue(value=str(cid)))]
        ),
        limit=1,
        with_vectors=True
    )
    
    if not results:
        return []
    
    # Use its vector to find similar compounds
    vector = results[0].vector
    similar = client.query_points(
        collection_name="pubchem_bge_small_v1_5",
        query=vector,
        limit=limit + 1  # +1 because it will include itself
    )
    
    # Filter out the query CID itself
    return [r for r in similar.points if r.payload['cid'] != str(cid)]
```

### 3. Batch Processing for Mapping Pipeline

```python
def batch_metabolite_search(metabolite_names, batch_size=100):
    """Process multiple metabolite names efficiently."""
    
    results = {}
    
    # Process in batches
    for i in range(0, len(metabolite_names), batch_size):
        batch = metabolite_names[i:i + batch_size]
        
        # Embed batch
        embeddings = list(embedder.embed(batch))
        
        # Search for each
        for name, embedding in zip(batch, embeddings):
            search_results = client.query_points(
                collection_name="pubchem_bge_small_v1_5",
                query=embedding.tolist(),
                limit=5
            )
            
            results[name] = [
                {
                    'cid': r.payload['cid'],
                    'score': r.score
                }
                for r in search_results.points
            ]
    
    return results
```

## Maintenance and Operations

### 1. Check Collection Status

```python
# Get collection info
info = client.get_collection("pubchem_bge_small_v1_5")
print(f"Status: {info.status}")
print(f"Points: {info.points_count:,}")
print(f"Indexed: {info.indexed_vectors_count:,}")
print(f"Segments: {info.segments_count}")
```

### 2. Monitor Performance

```python
# Check if indexing is complete
if info.indexed_vectors_count < info.points_count:
    print(f"Still indexing: {info.points_count - info.indexed_vectors_count} vectors remaining")
```

### 3. Backup Collection

```bash
# Create snapshot
curl -X POST 'http://localhost:6333/collections/pubchem_bge_small_v1_5/snapshots'

# List snapshots
curl 'http://localhost:6333/collections/pubchem_bge_small_v1_5/snapshots'
```

### 4. Optimize Collection

```python
# Trigger optimization
client.update_collection(
    collection_name="pubchem_bge_small_v1_5",
    optimizer_config={
        "max_optimization_threads": 2
    }
)
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if Docker container is running: `docker ps | grep qdrant`
   - Restart if needed: `cd /home/ubuntu/biomapper/docker/qdrant && docker compose restart`

2. **Slow Searches**
   - Check if indexing is complete
   - Monitor segment count (too many segments = slower search)
   - Consider optimizing the collection

3. **Memory Issues**
   - Default configuration uses on-disk storage for payloads
   - For better performance, increase Docker memory limits

### Useful Commands

```bash
# View logs
docker logs qdrant-qdrant-1

# Check resource usage
docker stats qdrant-qdrant-1

# Access Qdrant shell
docker exec -it qdrant-qdrant-1 /bin/bash
```

## Integration with Biomapper

The Qdrant database is designed to integrate with the `PubChemRAGMappingClient` (pending implementation). The workflow will be:

1. Receive metabolite name from mapping pipeline
2. Generate embedding using FastEmbed
3. Search Qdrant for top-k similar compounds
4. Enrich results with PubChem API data
5. Use LLM to select best match
6. Return mapped PubChem CID

## Future Enhancements

1. **Additional Collections**: Index other databases (ChEMBL, DrugBank)
2. **Multi-vector Support**: Store multiple representations per compound
3. **Filtering by Properties**: Add molecular weight, LogP, etc. to payloads
4. **Incremental Updates**: Add new compounds as they're discovered
5. **Distributed Deployment**: Scale across multiple nodes for larger datasets

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Biomapper RAG Strategy](/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md)
- [PubChem Filtering Implementation](/home/ubuntu/biomapper/roadmap/2_inprogress/qdrant_pubchem_indexing/)