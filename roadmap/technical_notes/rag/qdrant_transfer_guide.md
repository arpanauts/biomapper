# Qdrant Database Transfer Guide

## Overview

This guide explains how to transfer the Qdrant vector database between systems. The Qdrant database contains 2.2 million pre-indexed PubChem embeddings and is essential for the RAG-based metabolite mapping functionality.

## What Needs to be Transferred

### 1. Qdrant Storage Data (Required)
- **Location**: `/home/ubuntu/biomapper/docker/qdrant/qdrant_storage/`
- **Size**: ~4.0GB
- **Contains**: The actual indexed vectors, collection metadata, and WAL files
- **Critical**: This is the primary data that must be transferred

### 2. Docker Compose Configuration (Required)
- **File**: `/home/ubuntu/biomapper/docker/qdrant/docker-compose.yml`
- **Size**: <1KB
- **Purpose**: Defines how to run the Qdrant container

### 3. Filtered Embeddings (Optional - for re-indexing)
- **Location**: `/home/ubuntu/biomapper/data/filtered_embeddings/`
- **Size**: ~750MB (337 pickle files)
- **Purpose**: Source data used to create the Qdrant index
- **Note**: Only needed if you want to re-index from scratch

## Transfer Methods

### Method 1: Direct Storage Transfer (Recommended)

This is the fastest method - transfer the pre-indexed Qdrant storage directly.

**On Source System:**
```bash
# Stop Qdrant to ensure data consistency
cd /home/ubuntu/biomapper/docker/qdrant
docker compose down

# Create archive of Qdrant storage
cd /home/ubuntu/biomapper/docker/qdrant
tar -czf qdrant_storage_backup.tar.gz qdrant_storage/

# The archive will be ~3.5GB
```

**On Target System:**
```bash
# Create directory structure
mkdir -p /path/to/biomapper/docker/qdrant

# Copy docker-compose.yml
cat > /path/to/biomapper/docker/qdrant/docker-compose.yml << 'EOF'
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO
EOF

# Extract the storage archive
cd /path/to/biomapper/docker/qdrant
tar -xzf qdrant_storage_backup.tar.gz

# Start Qdrant
docker compose up -d

# Verify it's working
curl http://localhost:6333/collections/pubchem_bge_small_v1_5
```

### Method 2: Using Qdrant Snapshots (Alternative)

Qdrant provides a built-in snapshot mechanism for backup/restore.

**On Source System:**
```bash
# Create snapshot (with Qdrant running)
curl -X POST 'http://localhost:6333/collections/pubchem_bge_small_v1_5/snapshots'

# List snapshots to get snapshot name
curl 'http://localhost:6333/collections/pubchem_bge_small_v1_5/snapshots'

# Download snapshot
curl -o pubchem_snapshot.tar 'http://localhost:6333/collections/pubchem_bge_small_v1_5/snapshots/{snapshot_name}'
```

**On Target System:**
```bash
# Start fresh Qdrant instance
cd /path/to/biomapper/docker/qdrant
docker compose up -d

# Upload and restore snapshot
curl -X POST 'http://localhost:6333/collections/pubchem_bge_small_v1_5/snapshots/upload' \
  -H 'Content-Type: multipart/form-data' \
  -F 'snapshot=@pubchem_snapshot.tar'
```

### Method 3: Re-index from Filtered Embeddings

If you prefer to rebuild the index from scratch:

**Transfer these files:**
1. `/home/ubuntu/biomapper/data/filtered_embeddings/` directory (750MB)
2. `/home/ubuntu/biomapper/scripts/index_filtered_embeddings_to_qdrant.py`

**On Target System:**
```bash
# Start Qdrant
cd /path/to/biomapper/docker/qdrant
docker compose up -d

# Re-index (will take ~30 minutes)
poetry run python scripts/index_filtered_embeddings_to_qdrant.py \
  --input-path data/filtered_embeddings \
  --collection-name pubchem_bge_small_v1_5 \
  --batch-size 1000
```

## Directory Structure Recommendations

### Current Structure (Should Update)
```
biomapper/
├── docker/
│   └── qdrant/
│       ├── docker-compose.yml
│       └── qdrant_storage/      # 4GB - should be in .gitignore
└── data/
    └── filtered_embeddings/     # 750MB - already in .gitignore (*.pkl)
```

### Recommended Structure
```
biomapper/
├── docker/
│   └── qdrant/
│       └── docker-compose.yml   # Keep in git
└── data/
    ├── filtered_embeddings/     # Already gitignored
    └── qdrant_storage/         # Move here and gitignore
```

Or keep Qdrant storage completely outside the project:
```
/var/lib/qdrant/storage/        # System location
~/qdrant_data/                  # User home directory
```

## .gitignore Updates

Add these entries to `.gitignore`:

```gitignore
# Qdrant storage
docker/qdrant/qdrant_storage/
data/qdrant_storage/

# Filtered embeddings (already covered by *.pkl)
# data/filtered_embeddings/

# Qdrant backups
*.qdrant.tar.gz
*_snapshot.tar
```

## Docker Compose Update for External Storage

To use storage outside the project directory:

```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ${QDRANT_STORAGE_PATH:-./qdrant_storage}:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO
```

Then set environment variable:
```bash
export QDRANT_STORAGE_PATH=/var/lib/qdrant/storage
docker compose up -d
```

## Size Considerations

- **Qdrant Storage**: ~4GB (compressed to ~3.5GB)
- **Filtered Embeddings**: ~750MB (compressed to ~600MB)
- **Transfer Time**: 
  - LAN: 5-10 minutes
  - Internet: 30-60 minutes depending on connection

## Verification After Transfer

```python
from qdrant_client import QdrantClient

# Connect and verify
client = QdrantClient(host="localhost", port=6333)
info = client.get_collection("pubchem_bge_small_v1_5")

print(f"Collection status: {info.status}")
print(f"Points count: {info.points_count:,}")
print(f"Indexed vectors: {info.indexed_vectors_count:,}")

# Expected output:
# Collection status: green
# Points count: 2,217,373
# Indexed vectors: 2,215,982
```

## Best Practices

1. **Always stop Qdrant** before copying storage files to ensure consistency
2. **Verify checksums** after transfer for data integrity
3. **Test searches** after transfer to ensure functionality
4. **Keep the filtered embeddings** as a backup source for re-indexing
5. **Document the Qdrant version** used (currently `latest`)

## Summary

- **Minimum transfer**: `docker-compose.yml` + `qdrant_storage/` directory
- **Total size**: ~4GB
- **Recommended method**: Direct storage transfer (Method 1)
- **Git strategy**: Keep docker-compose.yml in git, exclude storage data