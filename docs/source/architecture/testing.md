# BioMapper Test Architecture

## Overview
The test suite follows a domain-driven structure that mirrors the main codebase organization. Each domain has its own test directory with comprehensive unit tests for mappers, pipelines, and domain-specific logic.

## Directory Structure
```
tests/
├── core/                      # Tests for core abstractions
│   ├── test_base_client.py   # API client tests
│   ├── test_base_mapper.py   # Mapper interface tests
│   ├── test_base_pipeline.py # Pipeline interface tests
│   ├── test_base_rag.py     # RAG component tests
│   └── test_base_store.py   # Store interface tests
│
├── pipelines/                # Domain-specific tests
│   ├── compounds/           # Compound mapping tests
│   │   ├── test_compound_mapper.py
│   │   └── test_compound_pipeline.py
│   ├── proteins/            # Protein mapping tests
│   │   ├── test_protein_mapper.py
│   │   └── test_protein_pipeline.py
│   └── labs/                # Lab test mapping tests
│
├── monitoring/              # Monitoring tests
├── schemas/                # Schema validation tests
└── conftest.py            # Shared test fixtures
```

## Test Categories

### Unit Tests
1. Base Class Tests
   - Interface contract validation
   - Abstract method behavior
   - Error handling
   - Type checking

2. Domain Implementation Tests
   - Mapper functionality
   - Pipeline workflow
   - Domain-specific logic
   - Error cases

3. Integration Tests
   - API client integration
   - RAG system integration
   - Pipeline end-to-end flow

### Test Fixtures
1. Common Fixtures (`conftest.py`)
   ```python
   @pytest.fixture
   def mock_api_client():
       """Mock API client for testing."""
       return Mock(spec=BaseAPIClient)

   @pytest.fixture
   def mock_vector_store():
       """Mock vector store for testing."""
       return Mock(spec=BaseVectorStore)
   ```

2. Domain-Specific Fixtures
   ```python
   @pytest.fixture
   def sample_compound_doc():
       """Sample compound document for testing."""
       return CompoundDocument(...)

   @pytest.fixture
   def sample_protein_doc():
       """Sample protein document for testing."""
       return ProteinDocument(...)
   ```

## Testing Patterns

### Mapper Tests
```python
def test_map_entity(mock_api_client):
    """Test basic entity mapping."""
    mapper = DomainMapper(mock_api_client)
    result = await mapper.map_entity("test")
    assert result.confidence > 0

def test_map_entity_error(mock_api_client):
    """Test error handling in mapping."""
    mock_api_client.search.side_effect = Exception()
    mapper = DomainMapper(mock_api_client)
    result = await mapper.map_entity("test")
    assert result.mapped_entity is None
```

### Pipeline Tests
```python
def test_process_names(mock_pipeline):
    """Test full pipeline processing."""
    result = await mock_pipeline.process_names(["test1", "test2"])
    assert len(result.mappings) == 2
    assert result.unmatched_count == 0

def test_rag_fallback(mock_pipeline):
    """Test RAG fallback for unmatched entities."""
    result = await mock_pipeline.process_names(["unknown"])
    assert result.rag_mapped_count == 1
```

## Mocking Strategy

### API Mocking
```python
@pytest.fixture
def mock_api_responses(requests_mock):
    """Mock API responses for testing."""
    requests_mock.get(
        "http://api.example.com/search",
        json={"results": [...]}
    )
```

### RAG Mocking
```python
@pytest.fixture
def mock_rag_system():
    """Mock RAG system components."""
    return {
        "embedder": Mock(spec=BaseEmbedder),
        "store": Mock(spec=BaseVectorStore),
        "llm": Mock(spec=BaseLLM)
    }
```

## Test Coverage Requirements

### Core Components
- 100% coverage for base classes
- All abstract methods tested
- Error handling paths verified

### Domain Implementation
- 90%+ coverage for domain logic
- Edge cases tested
- Error handling verified

### Integration Points
- API client integration tested
- RAG system integration verified
- Pipeline workflows validated

## Migration Guide

### From Legacy Tests
1. Identify domain-specific tests
2. Create new test directory in appropriate domain
3. Update imports to use new structure
4. Add missing test cases
5. Verify coverage
6. Remove legacy tests

### Best Practices
1. Use descriptive test names
2. Follow AAA pattern (Arrange, Act, Assert)
3. Mock external dependencies
4. Test error cases
5. Use appropriate fixtures
6. Maintain test isolation

## Future Considerations

### Planned Improvements
1. Property-based testing for edge cases
2. Performance testing suite
3. Integration test automation
4. Coverage reporting improvements
5. Test data generation tools

### CI/CD Integration
1. Automated test runs
2. Coverage reports
3. Performance benchmarks
4. Integration test gates
