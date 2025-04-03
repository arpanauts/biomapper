# Biomapper Embedder Module

The Biomapper Embedder module provides functionality for generating, storing, and retrieving embeddings from various biological text sources.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Vector Storage Implementation](#vector-storage-implementation)
- [Working with Metadata](#working-with-metadata)
- [Usage Examples](#usage-examples)

## Overview

The Embedder module enables semantic search over biological text data by converting text into dense vector embeddings, storing them efficiently, and providing retrieval functionality. It's designed to work with various data sources including PubMed articles, PubChem compounds, and other biological datasets.

## Architecture

The Embedder module consists of several key components:

- **Generators**: Create embeddings from text data
- **Storage**: Store and retrieve embeddings and metadata
- **Search**: Query the vector store for similar items
- **Pipelines**: Process batches of data efficiently
- **Models**: Define standardized data formats

## Data Flow

The flow of data through the Embedder module follows this sequence:

```
Raw Data → Preprocessing → Standardized JSON → Embedding Generation → Vector Storage → Search/Retrieval
```

### 1. Raw Data to Standardized JSON

Before data enters the Embedder module, it must be converted to a standardized JSON format:

```json
{
    "id": "unique_identifier",
    "type": "data_type",
    "primary_text": "main_content_for_embedding",
    "metadata": {
        "field1": "value1",
        "field2": "value2",
        ...
    },
    "source": "data_source_info"
}
```

Example for a PubMed article:

```json
{
    "id": "PMID12345678",
    "type": "pubmed_article",
    "primary_text": "Title: Effects of aspirin... Abstract: This study examines...",
    "metadata": {
        "title": "Effects of aspirin on cardiovascular health",
        "authors": ["Smith, J", "Jones, M"],
        "publication_date": "2023-04-01",
        "journal": "Journal of Medicine",
        "mesh_terms": ["Aspirin", "Cardiovascular Diseases"]
    },
    "source": "pubmed"
}
```

### 2. Embedding Generation

The `TextEmbedder` class processes the `primary_text` field to generate vector embeddings:

1. The text is passed to a transformer model (e.g., `all-MiniLM-L6-v2`)
2. The model encodes the text into a dense vector (typically 384 dimensions)
3. The vector is L2-normalized for cosine similarity calculations

```python
embedder = TextEmbedder(model_name="all-MiniLM-L6-v2")
embedding = embedder.embed_single("Title: Effects of aspirin... Abstract: This study examines...")
# Result: numpy array of shape (384,) containing the embedding
```

### 3. Vector Storage

The generated embeddings and their associated metadata are stored in the vector store:

![Vector Storage Diagram](https://i.imgur.com/tJx0QCD.png)

## Vector Storage Implementation

The Embedder module supports multiple vector storage backends:

1. **FAISSVectorStore**: Local file-based storage using Facebook AI Similarity Search (FAISS)
2. **QdrantVectorStore**: Collection-based storage using Qdrant vector database

### FAISS-Based Storage

The FAISSVectorStore class manages both the vector embeddings and their associated metadata:

### Components

1. **FAISS Index**: Stores and indexes the embedding vectors
   - Type: `faiss.IndexFlatIP` (inner product index for cosine similarity)
   - Handles vector storage and similarity search

2. **Metadata Dictionary**: Stores associated metadata
   - Format: `Dict[str, Dict[str, Any]]`
   - Maps item IDs to their metadata dictionaries

3. **ID-to-Index Mapping**: Links IDs to FAISS index positions
   - Format: `Dict[str, int]`
   - Maps item IDs to their positions in the FAISS index

### Storage Process

When adding embeddings to the store, the following happens:

```python
def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> List[str]:
    """Add embeddings with metadata to the store."""
    # 1. Normalize embeddings if needed
    if self.normalize:
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    
    # 2. Get current index size
    start_idx = self.index.ntotal
    
    # 3. Add embeddings to FAISS index
    self.index.add(embeddings)
    
    # 4. Store metadata and update mappings
    ids = []
    for i, meta in enumerate(metadata):
        id = meta.get('id', f"item_{start_idx + i}")
        self.metadata[id] = meta
        self.id_to_index[id] = start_idx + i
        ids.append(id)
    
    # 5. Save to disk if paths specified
    self._save_index_and_metadata()
        
    return ids
```

### Physical Storage

The FAISS index and metadata are stored in two separate files:

1. **Index File** (`.index`): Binary file containing the FAISS index
   - Format: FAISS binary format
   - Contains all embedding vectors

2. **Metadata File** (`.json`): JSON file containing all metadata
   - Format: JSON dictionary mapping IDs to metadata objects
   - Contains all item metadata and attributes

This separation allows for:
- Efficient vector operations in FAISS
- Easy inspection and manipulation of metadata
- Atomic file operations for data integrity

### Qdrant-Based Storage

The QdrantVectorStore class provides an alternative backend using Qdrant vector database:

#### Components

1. **Qdrant Client**: Interface to the vector database
   - Supports both local storage and remote server modes
   - Manages collections, points, and payload data

2. **Collections**: Organize vectors into logical groupings
   - Each collection has its own schema and configuration
   - Supports multiple collections for different data types

3. **Payload Data**: Stores metadata alongside vectors
   - Format: JSON-compatible fields attached to each vector
   - Fast filtering capabilities on metadata fields

#### Storage Process

When adding embeddings to Qdrant, the following happens:

```python
def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> List[str]:
    """Add embeddings with metadata to the store."""
    # 1. Normalize embeddings if needed
    if self.normalize:
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    
    # 2. Prepare points for batch upload
    points = []
    for embedding, meta in zip(embeddings, metadata):
        # Generate ID or use provided one
        id_value = meta.get('id', f"item_{i}")
        
        # Create Qdrant point
        point = models.PointStruct(
            id=id_value,
            vector=embedding.tolist(),
            payload={"metadata": meta}
        )
        points.append(point)
    
    # 3. Upload points in batch
    self.client.upsert(
        collection_name=self.collection_name,
        points=points
    )
    
    return ids
```

#### Physical Storage

Qdrant provides two deployment modes:

1. **Local Storage**: Embedded database stored on local disk
   - Data is stored in a specified directory
   - Suitable for development or single-node deployments

2. **Remote Server**: Standalone server or cloud deployment
   - Accessed via HTTP API
   - Supports clustering, replication, and high availability
   - Compatible with Qdrant Cloud managed service

#### Advanced Features

Qdrant offers several advanced capabilities:

- **Metadata Filtering**: Filter search results based on metadata fields
- **Payload Indexing**: Create indexes on metadata for faster filtering
- **Collections Management**: Create/delete collections for different data types
- **Versioning**: Built-in support for data versioning and snapshots

## Working with Metadata

### Metadata Structure

When storing items in the vector store, the metadata dictionary includes:

1. **Core Fields**:
   - `id`: Unique identifier
   - `type`: Data type (e.g., "pubmed_article")
   - `source`: Data source (e.g., "pubmed")

2. **Source-Specific Fields**:
   For PubMed articles:
   - `title`: Article title
   - `abstract`: Article abstract
   - `authors`: List of author names
   - `journal`: Journal name
   - `publication_date`: Publication date
   - `mesh_terms`: MeSH terms
   - `keywords`: Article keywords

3. **Additional Fields**: Any other fields included in the input JSON

### Metadata Handling During Search

When searching, the metadata is included in the search results:

```python
# Search results structure
{
    "id": "PMID12345678",
    "similarity": 0.8765,
    "metadata": {
        "id": "PMID12345678",
        "type": "pubmed_article",
        "title": "Effects of aspirin on cardiovascular health",
        "authors": ["Smith, J", "Jones, M"],
        ...
    }
}
```

This allows applications to:
- Display rich information about search results
- Filter or sort results based on metadata
- Provide context for retrieval augmented generation (RAG)

## Usage Examples

### 1. Process Data and Generate Embeddings

```python
from biomapper.embedder.generators.text_embedder import TextEmbedder
from biomapper.embedder.pipelines.batch import BatchEmbeddingPipeline

# Option 1: Using FAISS-based storage
from biomapper.embedder.storage.vector_store import FAISSVectorStore

vector_store_faiss = FAISSVectorStore(
    index_path="/path/to/embeddings.index",
    metadata_path="/path/to/metadata.json"
)

# Option 2: Using Qdrant-based storage
from biomapper.embedder.storage.qdrant_store import QdrantVectorStore

vector_store_qdrant = QdrantVectorStore(
    collection_name="biomapper_compounds",
    dimension=384,  # Matches the embedding model dimension
    local_path="/path/to/qdrant_storage"  # Local storage
    # Or for remote server:
    # url="http://localhost:6333",
    # api_key="your-api-key"  # For Qdrant Cloud
)

# Choose one vector store option
vector_store = vector_store_faiss  # or vector_store_qdrant

# Initialize components
embedder = TextEmbedder(model_name="all-MiniLM-L6-v2")
pipeline = BatchEmbeddingPipeline(
    embedder=embedder,
    vector_store=vector_store
)

# Process data
pipeline.process_from_jsonl("/path/to/data.jsonl")
```

### 2. Search for Similar Items

```python
from biomapper.embedder.generators.text_embedder import TextEmbedder
from biomapper.embedder.search.engine import EmbedderSearchEngine

# Option 1: Using FAISS-based storage
from biomapper.embedder.storage.vector_store import FAISSVectorStore

vector_store = FAISSVectorStore(
    index_path="/path/to/embeddings.index",
    metadata_path="/path/to/metadata.json"
)

# Option 2: Using Qdrant-based storage
# from biomapper.embedder.storage.qdrant_store import QdrantVectorStore
# vector_store = QdrantVectorStore(
#     collection_name="biomapper_compounds",
#     url="http://localhost:6333"
# )

# Initialize components
embedder = TextEmbedder(model_name="all-MiniLM-L6-v2")
search_engine = EmbedderSearchEngine(embedder, vector_store)

# Standard search
results = search_engine.search(
    query="stroke prevention methods", 
    k=5,
    filter_types=["pubmed_article"]
)
```

### 3. Advanced Search with Qdrant

```python
from biomapper.embedder.generators.text_embedder import TextEmbedder
from biomapper.embedder.storage.qdrant_store import QdrantVectorStore

# Initialize components
embedder = TextEmbedder(model_name="all-MiniLM-L6-v2")
vector_store = QdrantVectorStore(
    collection_name="biomapper_compounds",
    url="http://localhost:6333"
)

# Create index for faster filtering (Qdrant-specific feature)
vector_store.create_payload_index("type")
vector_store.create_payload_index("source")

# Filtered search with metadata conditions
query = "glucose metabolism"
query_vector = embedder.embed_single(query)
filtered_results = vector_store.filter_search(
    query_vector=query_vector,
    filter_conditions={
        "type": "compound",
        "source": ["chebi", "pubchem"]  # Match any of these values
    },
    k=10
)

# Get vector count
count = vector_store.get_total_count()
print(f"Total vectors in collection: {count}")
```

### 4. Command-Line Interface

```bash
# Process data with FAISS storage
./scripts/embedder_cli.py process \
  --input-file data.jsonl \
  --index-path embeddings.index \
  --metadata-path metadata.json

# Process data with Qdrant storage
./scripts/embedder_cli.py process \
  --input-file data.jsonl \
  --storage-type qdrant \
  --collection-name biomapper_compounds \
  --qdrant-url http://localhost:6333

# Search
./scripts/embedder_cli.py search \
  --query "stroke prevention methods" \
  --index-path embeddings.index \
  --metadata-path metadata.json \
  --filter-types pubmed_article \
  --k 5
```

## Storage Selection Guide

Choose the appropriate storage backend based on your requirements:

| Feature | FAISSVectorStore | QdrantVectorStore |
|---------|-----------------|-------------------|
| Deployment | Local file-based | Local or server-based |
| Scaling | Single machine | Distributed cluster |
| Metadata filtering | Limited (in-memory) | Advanced (indexed) |
| Collections | Single index | Multiple collections |
| Cloud support | No | Yes (Qdrant Cloud) |
| Update operations | Limited (no vector deletion) | Full CRUD operations |
| Versioning | Manual | Built-in |
| Network access | No | Optional (HTTP API) |

Both implementations conform to the same base interface, making them interchangeable in most use cases. For simple local deployments, FAISSVectorStore offers lower overhead, while QdrantVectorStore provides more advanced features for production environments.
