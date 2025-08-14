# BioMapper Test Architecture

## Overview

The BioMapper test suite follows Test-Driven Development (TDD) principles with comprehensive coverage of the 37+ self-registering actions. Tests are organized by entity type mirroring the action structure, with a minimum 80% coverage requirement enforced in CI/CD.

## Directory Structure

```
tests/
├── unit/                           # Unit tests
│   └── core/
│       ├── models/                 # Pydantic model tests
│       │   ├── test_action_models.py
│       │   ├── test_action_results.py
│       │   └── test_execution_context.py
│       └── strategy_actions/       # Action tests (37+ files)
│           ├── entities/           # Entity-specific tests
│           │   ├── proteins/       # Protein action tests
│           │   │   ├── test_protein_normalize_accessions.py
│           │   │   └── test_protein_multi_bridge.py
│           │   ├── metabolites/    # Metabolite action tests
│           │   │   ├── test_nightingale_nmr_match.py
│           │   │   └── test_semantic_metabolite_match.py
│           │   └── chemistry/      # Chemistry action tests
│           │       └── test_chemistry_extract_loinc.py
│           ├── io/                 # IO action tests
│           │   ├── test_load_dataset_identifiers.py
│           │   └── test_export_dataset_v2.py
│           ├── algorithms/         # Algorithm tests
│           │   ├── test_calculate_set_overlap.py
│           │   └── test_calculate_three_way_overlap.py
│           └── test_registry.py    # Registry tests
├── integration/                    # Integration tests
│   ├── test_strategy_execution.py # End-to-end strategy tests
│   ├── test_api_endpoints.py      # API endpoint tests
│   └── test_client_integration.py # BiomapperClient tests
├── api/                           # API-specific tests
│   └── test_mapper_service.py    # Job orchestration tests
└── conftest.py                   # Test configuration and fixtures
```

## Test Categories

### Unit Tests

1. **Action Tests (37+ actions)**
   - Parameter validation with Pydantic models
   - `execute_typed()` method implementation
   - Context manipulation (`datasets`, `statistics`, `output_files`)
   - Error handling and edge cases
   - Backward compatibility with dict interface

2. **Registry Tests**
   - Self-registration via `@register_action`
   - ACTION_REGISTRY population
   - Dynamic action lookup
   - Import-time registration

3. **Model Tests**
   - ActionResult validation
   - Parameter model constraints
   - Field validators
   - Type coercion

### Integration Tests

1. **Strategy Execution Tests**
   - Complete YAML strategy workflows
   - Variable substitution (`${parameters.key}`, `${env.VAR}`)
   - Multi-step action sequences
   - Context flow between actions

2. **API Tests**
   - `/api/strategies/v2/` endpoint
   - Job management with SQLite persistence
   - Server-Sent Events streaming
   - Background job processing
   - Checkpoint recovery

3. **Client Tests**
   - BiomapperClient.run() synchronous wrapper
   - Error handling and retries
   - Progress streaming
   - Timeout management

## Test Patterns for Typed Actions

### TDD Approach for New Actions

```python
# Step 1: Write failing test first
class TestProteinNormalizeAction:
    def test_parameter_validation(self):
        """Test Pydantic parameter validation."""
        params = ProteinNormalizeParams(
            input_key="raw_proteins",
            output_key="normalized",
            remove_isoforms=True,
            validate_format=True
        )
        assert params.input_key == "raw_proteins"
        assert params.remove_isoforms is True

    def test_invalid_params(self):
        """Test validation errors."""
        with pytest.raises(ValidationError) as exc:
            ProteinNormalizeParams(
                input_key="",  # Invalid: empty string
                output_key="normalized"
            )
        assert "empty" in str(exc.value)
```

### Typed Action Execution Tests

```python
class TestProteinNormalizeAction:
    @pytest.mark.asyncio
    async def test_execute_typed(self, mock_context):
        """Test typed execution with shared context."""
        # Arrange
        action = ProteinNormalizeAction()
        mock_context["datasets"]["raw_proteins"] = [
            {"identifier": "P12345-1"},
            {"identifier": "Q67890"}
        ]
        params = ProteinNormalizeParams(
            input_key="raw_proteins",
            output_key="normalized",
            remove_isoforms=True
        )
        
        # Act
        result = await action.execute_typed(params, mock_context)
        
        # Assert
        assert result.success
        assert "normalized" in mock_context["datasets"]
        assert len(mock_context["datasets"]["normalized"]) == 2
        assert mock_context["datasets"]["normalized"][0]["identifier"] == "P12345"
```

### Backward Compatibility Tests

```python
class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_dict_interface(self, mock_context):
        """Test legacy dict-based interface still works."""
        action = ProteinNormalizeAction()
        
        # Legacy dict params
        params_dict = {
            "input_key": "raw_proteins",
            "output_key": "normalized",
            "remove_isoforms": True
        }
        
        # Should work via execute() wrapper
        result = await action.execute(params_dict, mock_context)
        
        assert result["success"] is True
        assert "normalized" in result["message"]
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

### Shared Context Pattern

Actions receive and modify a shared `Dict[str, Any]` context:

```python
@pytest.fixture
def mock_context():
    """Standard context structure for action testing."""
    return {
        "datasets": {},           # Named datasets
        "current_identifiers": [], # Active identifiers
        "statistics": {},         # Accumulated metrics
        "output_files": [],       # Generated files
        "metadata": {}            # Strategy metadata
    }
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

### Minimum Standards
- **80% overall coverage** enforced in CI/CD
- **100% coverage** for TypedStrategyAction params
- **95%+ coverage** for execute_typed() methods
- All error paths tested
- Edge cases verified

### Action-Specific Requirements
- Each new action must have comprehensive tests
- Test both typed and dict interfaces
- Verify context manipulation
- Test parameter validation
- Cover error scenarios

### CI/CD Integration
```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    poetry run pytest --cov=biomapper --cov-report=html --cov-fail-under=80
```

## Running Tests

### Essential Commands
```bash
# Full test suite with coverage
poetry run pytest --cov=biomapper --cov-report=html

# Unit tests only
poetry run pytest tests/unit/

# Integration tests
poetry run pytest tests/integration/

# Specific action test with verbose output
poetry run pytest tests/unit/core/strategy_actions/entities/proteins/ -xvs

# Run specific test by name
poetry run pytest -k "test_protein_normalize"

# Debug single test with output
poetry run pytest -xvs tests/unit/core/strategy_actions/test_registry.py::test_action_registration

# Check coverage for specific module
poetry run pytest --cov=biomapper.core.strategy_actions --cov-report=term-missing
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

## Test Organization Best Practices

### Directory Structure Mirrors Code
```
tests/unit/core/strategy_actions/entities/proteins/
  ↓ mirrors ↓
biomapper/core/strategy_actions/entities/proteins/
```

### Test Naming Conventions
- Test files: `test_<action_name>.py`
- Test classes: `Test<ActionName>`
- Test methods: `test_<specific_scenario>`

### Fixture Organization
- Global fixtures in `conftest.py`
- Entity-specific fixtures in subdirectory conftest
- Action-specific fixtures in test file

## Future Enhancements

### In Progress
- Complete migration to TypedStrategyAction tests
- Automated strategy validation tests
- Performance benchmarking suite

### Planned
- Property-based testing with Hypothesis
- Mutation testing for coverage quality
- Load testing for API endpoints
- Integration with external services mocking

---

## Verification Sources
*Last verified: 2025-08-14*

This documentation was verified against the following project resources:

- `/biomapper/tests/unit/core/strategy_actions/` (37+ action test files organized by entity)
- `/biomapper/tests/integration/` (End-to-end strategy execution tests)
- `/biomapper/tests/conftest.py` (Global test fixtures and configuration)
- `/biomapper/.github/workflows/test.yml` (CI/CD test configuration with coverage requirements)
- `/biomapper/pyproject.toml` (pytest and coverage configuration)
- `/biomapper/CLAUDE.md` (TDD approach and testing requirements)