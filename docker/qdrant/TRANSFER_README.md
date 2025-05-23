# Qdrant Database Transfer Package

## Contents

This tarball contains the complete Qdrant vector database for Biomapper's PubChem RAG system.

### What's Included

- `qdrant_storage/` - The Qdrant database with 2.2M indexed PubChem embeddings (4GB uncompressed)
- `docker-compose.yml` - Docker configuration file

### Quick Setup on Target System

```bash
# 1. Extract the tarball
tar -xzf qdrant_backup.tar.gz

# 2. Start Qdrant
docker compose up -d

# 3. Verify it's working
curl http://localhost:6333/collections/pubchem_bge_small_v1_5
```

### Expected Output

```json
{
  "result": {
    "status": "green",
    "points_count": 2217373,
    "indexed_vectors_count": 2215982,
    "config": {
      "params": {
        "vectors": {
          "size": 384,
          "distance": "Cosine"
        }
      }
    }
  }
}
```

### Python Verification

```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
info = client.get_collection("pubchem_bge_small_v1_5")
print(f"Points: {info.points_count:,}")  # Should show 2,217,373
```

### Notes

- Ensure port 6333 is available
- Docker must be installed
- The database contains biologically relevant compounds from HMDB, ChEBI, and UniChem
- Created: May 23, 2025
- Biomapper version: Latest from main branch

### Support

See the full documentation at:
- `/roadmap/technical_notes/rag/rag_strategy.md`
- `/roadmap/technical_notes/rag/qdrant_db_overview.md`