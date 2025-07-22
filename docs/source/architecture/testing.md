# Biomapper Test Architecture

## Overview

The test suite for Biomapper follows a focused approach that mirrors the simplified architecture. Tests are primarily concentrated on the core action system and API functionality, with comprehensive unit tests for the three core actions.

## Directory Structure

```
tests/
├── unit/                           # Unit tests
│   └── core/
│       ├── models/                 # Pydantic model tests
│       │   ├── test_action_models.py
│       │   ├── test_action_results.py
│       │   └── test_execution_context.py
│       └── strategy_actions/       # Core action tests
│           ├── test_load_dataset_identifiers.py
│           ├── test_merge_with_uniprot_resolution.py
│           └── test_calculate_set_overlap.py
├── manual/                         # Manual integration tests
│   ├── test_data_loading.py       # Test data loading scenarios
│   ├── test_simple_ukbb_hpa.py    # Simple strategy test
│   └── test_timing.py             # Timing metrics test
├── monitoring/                     # System monitoring tests
├── utils/                         # Utility function tests
└── conftest.py                    # Test configuration and fixtures
```

## Test Categories

### Unit Tests

1. **Core Action Tests**
   - Parameter validation (Pydantic models)
   - Execution logic
   - Error handling
   - Data processing
   - Context management

2. **Model Tests**
   - Pydantic model validation
   - Type checking
   - Serialization/deserialization
   - Field requirements

3. **Service Tests**
   - Strategy loading
   - Action registry
   - Context handling

### Integration Tests

1. **Manual Tests**
   - Strategy execution via API
   - Client-server interaction
   - End-to-end workflows

2. **API Tests** 
   - HTTP endpoint functionality
   - Request/response handling
   - Error scenarios

## Core Action Test Patterns

### Parameter Validation Tests

```python
class TestLoadDatasetIdentifiersParams:
    def test_valid_params(self):
        """Test valid parameter combinations."""
        params = LoadDatasetIdentifiersParams(
            file_path="/path/to/file.csv",
            identifier_column="id",
            output_key="dataset"
        )
        assert params.file_path == "/path/to/file.csv"
        assert params.identifier_column == "id"

    def test_missing_required_params(self):
        """Test validation of required parameters."""
        with pytest.raises(ValidationError):
            LoadDatasetIdentifiersParams()
```

### Action Execution Tests

```python
class TestLoadDatasetIdentifiersAction:
    async def test_load_simple_csv(self, temp_csv_file, mock_context):
        """Test loading a simple CSV file."""
        action = LoadDatasetIdentifiersAction()
        params = LoadDatasetIdentifiersParams(
            file_path=str(temp_csv_file),
            identifier_column="id",
            output_key="test_data"
        )
        
        result = await action.execute(params, mock_context)
        
        assert result.success
        assert "test_data" in mock_context.get_action_data("datasets", {})
```

### Error Handling Tests

```python
async def test_file_not_found(self, mock_context):
    """Test handling of missing files."""
    action = LoadDatasetIdentifiersAction()
    params = LoadDatasetIdentifiersParams(
        file_path="/nonexistent/file.csv",
        identifier_column="id", 
        output_key="test"
    )
    
    with pytest.raises(FileNotFoundError):
        await action.execute(params, mock_context)
```

## Test Fixtures

### Common Fixtures (conftest.py)

```python
@pytest.fixture
def mock_context():
    """Mock context for action testing."""
    class MockContext:
        def __init__(self):
            self._data = {'custom_action_data': {}}
        
        def set_action_data(self, key: str, value):
            self._data['custom_action_data'][key] = value
        
        def get_action_data(self, key: str, default=None):
            return self._data.get('custom_action_data', {}).get(key, default)
    
    return MockContext()

@pytest.fixture
def temp_csv_file(tmp_path):
    """Create temporary CSV file for testing."""
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text("id,name\nP12345,Protein1\nQ67890,Protein2\n")
    return csv_file
```

### Action-Specific Fixtures

```python
@pytest.fixture
def sample_merged_data():
    """Sample merged data for overlap calculations."""
    return [
        {
            "source_id": "P12345",
            "target_id": "ENSP000123",
            "match_type": "direct",
            "match_confidence": 1.0
        }
    ]
```

## Testing Strategy

### MockContext Pattern

Since the current architecture uses a simple dictionary-like context instead of the full StrategyExecutionContext, tests use a MockContext class that simulates the required interface:

```python
class MockContext:
    """Mock context that simulates StrategyExecutionContext for actions."""
    def __init__(self):
        self._data = {'custom_action_data': {}}
    
    def set_action_data(self, key: str, value) -> None:
        self._data['custom_action_data'][key] = value
    
    def get_action_data(self, key: str, default=None):
        return self._data.get('custom_action_data', {}).get(key, default)
```

### CI/CD Integration

Tests are configured to work in CI environments:

- Manual tests skip automatically when `CI=true` or `GITHUB_ACTIONS=true`
- Integration tests that require the API server are marked and skipped appropriately
- Unit tests run independently without external dependencies

### Test Configuration

The `pytest.ini` file includes:

```ini
[pytest]
asyncio_mode = auto
markers =
    requires_api: marks tests that require the API server to be running
```

## Coverage Requirements

### Core Actions
- **100% coverage** for action parameter models
- **95%+ coverage** for action execution logic
- All error paths tested
- Edge cases verified

### Models
- **100% coverage** for Pydantic model validation
- All field combinations tested
- Type checking verified

### Integration Points
- API endpoint functionality verified
- Client-server communication tested
- Strategy execution validated

## Running Tests

### Full Test Suite
```bash
poetry run pytest
```

### Unit Tests Only  
```bash
poetry run pytest tests/unit/
```

### Specific Action Tests
```bash
poetry run pytest tests/unit/core/strategy_actions/test_load_dataset_identifiers.py -v
```

### Skip Manual Tests (CI Mode)
```bash
CI=true poetry run pytest
```

## Performance Testing

The test suite includes performance considerations:

- Large dataset tests with timing validation
- Memory usage monitoring for data processing
- CSV parsing performance benchmarks
- Venn diagram generation performance

Example:
```python
def test_large_dataset_performance(self):
    """Test performance with large datasets."""
    # Test with 10,000 rows
    large_data = generate_test_data(10000)
    start_time = time.time()
    
    # Execute action
    result = await action.execute(params, context)
    
    execution_time = time.time() - start_time
    assert execution_time < 30.0  # Should complete within 30 seconds
```

## Future Enhancements

### Planned Improvements
- Property-based testing for edge cases
- Performance regression testing
- Automated integration test environment
- Test data generation improvements
- API load testing

### Monitoring Integration
- Test execution metrics
- Coverage trending
- Performance benchmarks
- Failure analysis