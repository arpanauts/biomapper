# PubChemRAGMappingClient - Specification

## Overview

The PubChemRAGMappingClient is a semantic search-based mapping client that queries a Qdrant vector database containing 2.3 million biologically relevant PubChem compound embeddings. It provides an alternative to traditional exact-match mapping approaches by leveraging vector similarity search to find PubChem CIDs for metabolite names and synonyms.

## Functionality

### Core Mapping Operations

#### 1. Single Metabolite Mapping
```python
async def map_identifier(
    self,
    identifier: str,
    source_type: str = "name",
    target_type: str = "pubchem_cid",
    **kwargs
) -> MappingResult:
    """
    Map a single metabolite identifier to PubChem CID using semantic search.
    
    Args:
        identifier: The metabolite name or synonym to map
        source_type: Type of source identifier (default: "name")
        target_type: Type of target identifier (default: "pubchem_cid")
        **kwargs: Additional parameters (similarity_threshold, top_k, etc.)
    
    Returns:
        MappingResult containing PubChem CIDs with confidence scores
    """
```

#### 2. Batch Mapping
```python
async def map_identifiers_batch(
    self,
    identifiers: List[str],
    source_type: str = "name",
    target_type: str = "pubchem_cid",
    **kwargs
) -> List[MappingResult]:
    """
    Map multiple metabolite identifiers in a single batch operation.
    
    Args:
        identifiers: List of metabolite names or synonyms
        source_type: Type of source identifiers
        target_type: Type of target identifiers
        **kwargs: Additional parameters
    
    Returns:
        List of MappingResults corresponding to input identifiers
    """
```

### Embedding Generation

#### 3. Text to Vector Conversion
```python
async def generate_embedding(
    self,
    text: str
) -> np.ndarray:
    """
    Generate embedding vector for input text using BAAI/bge-small-en-v1.5 model.
    
    Args:
        text: Metabolite name or synonym
    
    Returns:
        384-dimensional embedding vector
    """
```

### Vector Search Operations

#### 4. Similarity Search
```python
async def search_similar(
    self,
    embedding: np.ndarray,
    top_k: int = 10,
    similarity_threshold: float = 0.8
) -> List[SearchResult]:
    """
    Search for similar compounds in Qdrant based on embedding similarity.
    
    Args:
        embedding: Query embedding vector
        top_k: Maximum number of results to return
        similarity_threshold: Minimum similarity score
    
    Returns:
        List of SearchResults with CIDs and scores
    """
```

### Configuration Management

#### 5. Client Configuration
```python
class PubChemRAGConfig:
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    collection_name: str = "pubchem_bge_small_v1_5"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    default_top_k: int = 10
    default_similarity_threshold: float = 0.8
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds
    batch_size: int = 100
    timeout: float = 30.0
```

## Scope

### In Scope

1. **Vector Search Integration**
   - Qdrant client initialization and connection management
   - Query execution with configurable parameters
   - Result retrieval and ranking

2. **Embedding Generation**
   - Integration with sentence-transformers library
   - Model loading and caching
   - Text preprocessing for optimal embedding quality

3. **Caching Layer**
   - In-memory LRU cache for frequent queries
   - Configurable TTL and size limits
   - Cache statistics and monitoring

4. **Error Handling**
   - Connection failure recovery
   - Graceful degradation when services unavailable
   - Comprehensive exception handling

5. **Metrics and Logging**
   - Query latency tracking
   - Success/failure rate monitoring
   - Detailed debug logging

### Out of Scope

1. **Embedding Model Training**
   - Uses pre-trained BAAI/bge-small-en-v1.5 model
   - No custom model fine-tuning

2. **PubChem Data Updates**
   - Relies on pre-computed embeddings in Qdrant
   - No direct PubChem API integration for compound data

3. **Complex Query Logic**
   - No support for boolean queries or filters beyond similarity
   - No chemical structure-based search

4. **Database Administration**
   - Qdrant deployment and maintenance
   - Embedding generation pipeline for PubChem data

## User Interface Treatments

### Configuration Interface

```yaml
# biomapper_config.yaml
mapping:
  clients:
    pubchem_rag:
      enabled: true
      class: "biomapper.mapping.clients.pubchem_rag_client.PubChemRAGMappingClient"
      config:
        qdrant_host: "localhost"
        qdrant_port: 6333
        collection_name: "pubchem_bge_small_v1_5"
        embedding_model: "BAAI/bge-small-en-v1.5"
        default_similarity_threshold: 0.8
        default_top_k: 10
        cache_enabled: true
        cache_ttl: 3600
```

### Programmatic Usage

```python
from biomapper.mapping.clients import PubChemRAGMappingClient
from biomapper.mapping.orchestrators import FallbackOrchestrator

# Initialize client
rag_client = PubChemRAGMappingClient(
    qdrant_host="localhost",
    qdrant_port=6333,
    similarity_threshold=0.85
)

# Use directly
result = await rag_client.map_identifier("aspirin")
print(f"Found PubChem CID: {result.target_id} (confidence: {result.confidence})")

# Use with orchestrator
orchestrator = FallbackOrchestrator(
    clients=[
        exact_match_client,  # Try exact match first
        rag_client,          # Fall back to semantic search
        fuzzy_match_client   # Final fallback
    ]
)
```

### Response Format

```python
@dataclass
class MappingResult:
    source_id: str
    source_type: str
    target_id: Optional[str]
    target_type: str
    confidence: float
    metadata: Dict[str, Any]
    
# Example response
MappingResult(
    source_id="aspirin",
    source_type="name",
    target_id="2244",
    target_type="pubchem_cid",
    confidence=0.92,
    metadata={
        "similarity_score": 0.92,
        "rank": 1,
        "alternative_cids": ["2343", "2453"],
        "alternative_scores": [0.85, 0.81],
        "query_time_ms": 45
    }
)
```

### Error Responses

```python
# Connection failure
MappingResult(
    source_id="aspirin",
    source_type="name",
    target_id=None,
    target_type="pubchem_cid",
    confidence=0.0,
    metadata={
        "error": "Qdrant connection failed",
        "error_type": "ConnectionError",
        "retry_after": 5
    }
)

# No results above threshold
MappingResult(
    source_id="unknown_compound_xyz",
    source_type="name",
    target_id=None,
    target_type="pubchem_cid",
    confidence=0.0,
    metadata={
        "error": "No matches above similarity threshold",
        "best_score": 0.65,
        "threshold": 0.8
    }
)
```

## Success Criteria

1. **Functional Success**
   - Client successfully connects to Qdrant and executes queries
   - Correct embedding generation for input metabolites
   - Accurate similarity search results with proper ranking

2. **Performance Metrics**
   - Single query latency < 100ms (excluding embedding generation)
   - Batch processing of 100 metabolites < 5 seconds
   - Cache hit rate > 30% for typical workloads

3. **Integration Success**
   - Seamless integration with FallbackOrchestrator
   - Proper error propagation and handling
   - Compatible with existing logging and monitoring

4. **Quality Metrics**
   - Unit test coverage > 80%
   - Integration tests with mock Qdrant instance
   - Demonstrated improvement in mapping success rate vs baseline

5. **Operational Readiness**
   - Comprehensive documentation
   - Configuration examples and best practices
   - Deployment guide for Qdrant setup