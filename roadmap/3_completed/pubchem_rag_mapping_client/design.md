# PubChemRAGMappingClient - Design Document

## Architecture Overview

The PubChemRAGMappingClient implements a semantic search-based approach to metabolite mapping using vector embeddings and similarity search. The architecture consists of several key components working together to provide efficient and accurate mapping capabilities.

```
┌─────────────────────────────────────────────────────────────┐
│                    FallbackOrchestrator                      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                  PubChemRAGMappingClient                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Config    │  │ Cache Layer  │  │ Metrics/Logging  │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              EmbeddingGenerator                      │   │
│  │         (BAAI/bge-small-en-v1.5)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              QdrantSearchEngine                      │   │
│  │         (Vector Similarity Search)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ResultProcessor                         │   │
│  │      (Ranking, Filtering, Formatting)              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Qdrant Vector Database                    │
│                  (pubchem_bge_small_v1_5)                   │
│                    2.3M PubChem Embeddings                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. PubChemRAGMappingClient (Main Class)

**Responsibilities:**
- Implements the `MappingClient` interface
- Orchestrates the mapping workflow
- Manages component lifecycle and dependencies
- Handles configuration and initialization

**Key Methods:**
```python
class PubChemRAGMappingClient(MappingClient):
    def __init__(self, config: PubChemRAGConfig):
        self.config = config
        self.embedding_generator = EmbeddingGenerator(config.embedding_model)
        self.search_engine = QdrantSearchEngine(config)
        self.result_processor = ResultProcessor(config)
        self.cache = LRUCache(maxsize=config.cache_size) if config.cache_enabled else None
        
    async def map_identifier(self, identifier: str, **kwargs) -> MappingResult:
        # Check cache
        if self.cache and identifier in self.cache:
            return self.cache[identifier]
            
        # Generate embedding
        embedding = await self.embedding_generator.generate(identifier)
        
        # Search similar vectors
        search_results = await self.search_engine.search(embedding, **kwargs)
        
        # Process results
        mapping_result = self.result_processor.process(identifier, search_results)
        
        # Update cache
        if self.cache:
            self.cache[identifier] = mapping_result
            
        return mapping_result
```

### 2. EmbeddingGenerator

**Responsibilities:**
- Load and manage the sentence-transformer model
- Generate embeddings for input text
- Handle text preprocessing and normalization
- Implement model caching for performance

**Design Decisions:**
- Use sentence-transformers library for consistency
- Lazy load model to reduce startup time
- Implement singleton pattern for model instance
- Support GPU acceleration if available

```python
class EmbeddingGenerator:
    _model_instance = None
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        
    @property
    def model(self):
        if EmbeddingGenerator._model_instance is None:
            from sentence_transformers import SentenceTransformer
            EmbeddingGenerator._model_instance = SentenceTransformer(self.model_name)
        return EmbeddingGenerator._model_instance
        
    async def generate(self, text: str) -> np.ndarray:
        # Preprocess text
        processed_text = self._preprocess(text)
        
        # Generate embedding
        embedding = self.model.encode(processed_text)
        
        return embedding
        
    def _preprocess(self, text: str) -> str:
        # Normalize text: lowercase, remove special chars, etc.
        return text.lower().strip()
```

### 3. QdrantSearchEngine

**Responsibilities:**
- Manage Qdrant client connection
- Execute vector similarity searches
- Handle connection pooling and retries
- Implement search parameter optimization

**Design Decisions:**
- Use async Qdrant client for better performance
- Implement connection pooling for concurrent requests
- Add retry logic with exponential backoff
- Support both REST and gRPC interfaces

```python
class QdrantSearchEngine:
    def __init__(self, config: PubChemRAGConfig):
        self.config = config
        self.client = self._create_client()
        
    def _create_client(self):
        from qdrant_client import QdrantClient
        return QdrantClient(
            host=self.config.qdrant_host,
            port=self.config.qdrant_port,
            timeout=self.config.timeout
        )
        
    async def search(
        self, 
        embedding: np.ndarray, 
        top_k: int = None,
        threshold: float = None
    ) -> List[SearchResult]:
        top_k = top_k or self.config.default_top_k
        threshold = threshold or self.config.default_similarity_threshold
        
        # Execute search
        results = await self.client.search(
            collection_name=self.config.collection_name,
            query_vector=embedding.tolist(),
            limit=top_k,
            score_threshold=threshold
        )
        
        # Convert to internal format
        return [
            SearchResult(
                cid=str(hit.payload['cid']),
                score=hit.score,
                metadata=hit.payload
            )
            for hit in results
        ]
```

### 4. ResultProcessor

**Responsibilities:**
- Convert search results to MappingResult format
- Apply ranking and filtering logic
- Enrich results with metadata
- Handle edge cases and error conditions

**Design Decisions:**
- Implement configurable ranking strategies
- Support multiple result formats
- Add metadata enrichment hooks
- Provide detailed error information

```python
class ResultProcessor:
    def __init__(self, config: PubChemRAGConfig):
        self.config = config
        
    def process(
        self, 
        source_id: str, 
        search_results: List[SearchResult]
    ) -> MappingResult:
        if not search_results:
            return self._create_no_match_result(source_id)
            
        # Select best result
        best_result = search_results[0]
        
        # Create mapping result
        return MappingResult(
            source_id=source_id,
            source_type="name",
            target_id=best_result.cid,
            target_type="pubchem_cid",
            confidence=best_result.score,
            metadata={
                "similarity_score": best_result.score,
                "rank": 1,
                "alternative_cids": [r.cid for r in search_results[1:self.config.max_alternatives]],
                "alternative_scores": [r.score for r in search_results[1:self.config.max_alternatives]],
                "search_params": {
                    "top_k": len(search_results),
                    "threshold": self.config.default_similarity_threshold
                }
            }
        )
```

### 5. Cache Layer

**Responsibilities:**
- Cache frequently requested mappings
- Implement TTL-based expiration
- Provide cache statistics
- Support cache warming strategies

**Design Decisions:**
- Use Python's functools.lru_cache with TTL wrapper
- Make caching optional via configuration
- Implement cache statistics for monitoring
- Support both in-memory and Redis backends

## Integration Points

### 1. MappingClient Interface

The client implements the standard MappingClient interface:

```python
from biomapper.mapping.base_client import MappingClient

class PubChemRAGMappingClient(MappingClient):
    async def map_identifier(self, identifier: str, **kwargs) -> MappingResult:
        # Implementation
        
    async def map_identifiers_batch(self, identifiers: List[str], **kwargs) -> List[MappingResult]:
        # Batch implementation with optimizations
        
    @property
    def supported_types(self) -> Dict[str, List[str]]:
        return {
            "source": ["name", "synonym"],
            "target": ["pubchem_cid"]
        }
```

### 2. FallbackOrchestrator Integration

```python
# In FallbackOrchestrator configuration
orchestrator = FallbackOrchestrator(
    clients=[
        ExactMatchClient(priority=1),
        PubChemRAGMappingClient(priority=2),  # Our client
        FuzzyMatchClient(priority=3)
    ],
    strategy="sequential"  # Try clients in priority order
)
```

### 3. Configuration System

```python
# Integration with Biomapper config
from biomapper.core.config import get_config

config = get_config()
rag_config = PubChemRAGConfig(**config.mapping.clients.pubchem_rag)
client = PubChemRAGMappingClient(rag_config)
```

## Data Flow

1. **Input Processing**
   ```
   Metabolite Name → Text Preprocessing → Embedding Generation
   ```

2. **Vector Search**
   ```
   Query Embedding → Qdrant Search → Top-K Similar Vectors
   ```

3. **Result Processing**
   ```
   Search Results → Ranking/Filtering → MappingResult Format
   ```

4. **Caching Flow**
   ```
   Check Cache → Cache Miss → Execute Search → Update Cache → Return Result
   Cache Hit → Return Cached Result
   ```

## Error Handling Strategy

### 1. Connection Errors
- Retry with exponential backoff
- Fall back to next client in orchestrator
- Log detailed error information

### 2. Model Loading Errors
- Fail fast with clear error message
- Suggest model download instructions
- Check model compatibility

### 3. Search Errors
- Return empty result with error metadata
- Log query parameters for debugging
- Monitor error rates

### 4. Timeout Handling
- Configurable timeout per operation
- Graceful cancellation of pending requests
- Return partial results if available

## Performance Considerations

### 1. Embedding Generation
- Cache model in memory after first load
- Batch encode multiple texts when possible
- Use GPU acceleration if available
- Implement text preprocessing cache

### 2. Vector Search
- Use HNSW index in Qdrant for fast search
- Optimize search parameters (ef, m)
- Implement connection pooling
- Consider search result caching

### 3. Batch Processing
- Group queries by similarity for better cache hits
- Use Qdrant batch search API
- Parallelize embedding generation
- Implement progress reporting

### 4. Memory Management
- Limit cache size to prevent memory issues
- Use weak references for large objects
- Implement cache eviction policies
- Monitor memory usage

## Testing Strategy

### 1. Unit Tests
```python
# Test embedding generation
def test_embedding_generation():
    generator = EmbeddingGenerator("BAAI/bge-small-en-v1.5")
    embedding = generator.generate("aspirin")
    assert embedding.shape == (384,)
    assert -1 <= embedding.min() <= embedding.max() <= 1

# Test result processing
def test_result_processing():
    processor = ResultProcessor(config)
    result = processor.process("aspirin", search_results)
    assert result.target_id == "2244"
    assert result.confidence > 0.8
```

### 2. Integration Tests
```python
# Test with mock Qdrant
@pytest.mark.asyncio
async def test_mapping_with_mock_qdrant(mock_qdrant):
    client = PubChemRAGMappingClient(test_config)
    result = await client.map_identifier("aspirin")
    assert result.target_id is not None
    mock_qdrant.search.assert_called_once()
```

### 3. Performance Tests
```python
# Test batch performance
@pytest.mark.benchmark
async def test_batch_mapping_performance():
    client = PubChemRAGMappingClient(config)
    metabolites = ["aspirin", "glucose", "caffeine"] * 100
    
    start = time.time()
    results = await client.map_identifiers_batch(metabolites)
    duration = time.time() - start
    
    assert duration < 5.0  # Should complete in under 5 seconds
    assert len(results) == 300
```

## Future Enhancements

1. **Advanced Search Features**
   - Support for chemical structure similarity
   - Multi-modal search (name + structure)
   - Filtered search by compound properties

2. **Model Improvements**
   - Fine-tune embeddings on biochemical data
   - Support multiple embedding models
   - Implement ensemble approaches

3. **Operational Features**
   - Real-time embedding updates
   - A/B testing framework
   - Advanced caching strategies
   - Search result explanation