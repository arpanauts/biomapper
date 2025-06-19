"""Tests for the metadata features of MappingExecutor."""
import pytest
import json
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)
from biomapper.core.mapping_executor import MappingExecutor

logger = logging.getLogger(__name__)

# SQLite in-memory URL for testing
asyncdb_url = "sqlite+aiosqlite:///:memory:"

# Helper function to create mock results for caching tests
def create_mock_results(input_ids, target_prefix, offset=1):
    """Helper function to create mock mapping results for caching tests."""
    results = {}
    for i, input_id in enumerate(input_ids):
        target_id = f"{target_prefix}{i + offset}"
        results[input_id] = {
            "target_identifiers": [target_id],
            "confidence_score": 0.95 - (i * 0.01),  # Example confidence
            # Simulate details being generated later in _cache_results
            "mapping_path_details": {},
            "hop_count": 2,  # Example hop count
            "mapping_direction": "forward",  # Example direction
        }
    return results

# Helper for mocking async context managers
class MockAsyncContextManager:
    def __init__(self, mock_obj, raise_exception_on_exit=None, raise_exception_on_enter=None):
        self.mock_obj = mock_obj
        self.raise_exception_on_exit = raise_exception_on_exit
        self.raise_exception_on_enter = raise_exception_on_enter

    async def __aenter__(self):
        if self.raise_exception_on_enter:
            raise self.raise_exception_on_enter
        return self.mock_obj

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.raise_exception_on_exit:
            # Simulate error during commit/close
            raise self.raise_exception_on_exit
        # Return False to allow exceptions raised *within* the block to propagate
        return False

@pytest.fixture
def mapping_executor():
    """Fixture for a properly initialized MappingExecutor with mock sessions."""
    executor = MappingExecutor(
        metamapper_db_url="sqlite+aiosqlite:///:memory:",
        mapping_cache_db_url="sqlite+aiosqlite:///:memory:",
    )
    return executor

@pytest.fixture
def mock_async_cache_session_factory():
    """Provides a mock async session factory for the cache database."""
    mock_factory = MagicMock(spec=async_sessionmaker)
    # Configure the factory to return a mock session when called
    mock_cache_session = AsyncMock(spec=AsyncSession)
    # Setup mock to allow property access for mock_obj
    mock_factory.return_value = MockAsyncContextManager(mock_cache_session)
    return mock_factory, mock_cache_session

@pytest.fixture
def patched_mapping_executor(
    mapping_executor,  # Get the base executor instance
    mock_async_cache_session_factory,  # Get the mock cache session factory
):
    """Provides a MappingExecutor with mocked sessions."""
    # Unpack the factory and session from the fixture
    mock_factory, mock_cache_session = mock_async_cache_session_factory
    
    # Create a mock metamapper session factory and session
    mock_metamapper_session = AsyncMock(spec=AsyncSession)
    mock_metamapper_factory = MagicMock(spec=async_sessionmaker)
    mock_metamapper_factory.return_value = MockAsyncContextManager(mock_metamapper_session)
    
    # Replace both session factories with mocks
    mapping_executor.async_session = mock_metamapper_factory
    mapping_executor.async_cache_session = mock_factory
    
    # Also mock the engines
    mapping_executor.engine = AsyncMock(spec=AsyncEngine)
    mapping_executor.cache_engine = AsyncMock(spec=AsyncEngine)
    
    return mapping_executor, mock_cache_session, mock_metamapper_session

# Test for _cache_results method focusing on metadata fields
@pytest.mark.asyncio
async def test_metadata_in_cache_results(patched_mapping_executor):
    """Test that _cache_results properly populates all metadata fields."""
    # Unpack the executor and mocked sessions
    executor, mock_cache_session, mock_metamapper_session = patched_mapping_executor
    
    # Test values
    source_ontology = "SOURCE_ONT"
    target_ontology = "TARGET_ONT"
    mock_path_id = 42
    mock_path_name = "TestPath"
    mock_session_id = 123
    input_ids = ["ID1", "ID2"]
    
    # Create mock results with test data
    results = create_mock_results(input_ids, "TGT_")
    
    # Create a simple mock path without using ReversiblePath
    mock_path = MagicMock()
    mock_path.id = mock_path_id
    mock_path.name = mock_path_name
    mock_path.source_ontology_type = source_ontology
    mock_path.target_ontology_type = target_ontology
    
    # Add steps to calculate hop_count
    step1 = MagicMock()
    step2 = MagicMock()
    mock_path.steps = [step1, step2]
    
    # Add is_reverse attribute for direction check
    mock_path.is_reverse = False
    
    # Mock the flush to simulate ID generation for log entry
    async def mock_flush():
        # Find the log entry in added objects and assign an ID
        for call in mock_cache_session.method_calls:
            if call[0] == 'add':
                obj = call[1][0]
                if hasattr(obj, 'relationship_mapping_path_id') and obj.relationship_mapping_path_id == mock_path_id:
                    obj.id = 999  # Assign a test ID
    
    mock_cache_session.flush = AsyncMock(side_effect=mock_flush)
    
    # Set up mock for _get_path_details to return test data
    patch_get_details = patch.object(
        executor, '_get_path_details', new_callable=AsyncMock
    )
    
    with patch_get_details as mock_get_details:
        # Return mock path details
        mock_get_details.return_value = {
            "step_1": {
                "resource_name": "TestResource",
                "resource_type": "TestClass",
                "input_ontology": source_ontology,
                "output_ontology": target_ontology,
            }
        }
        
        # Call the method under test
        await executor._cache_results(
            results, mock_path, source_ontology, target_ontology, mock_session_id
        )
    
    # Verify add_all was called
    mock_cache_session.add_all.assert_called_once()
    mock_cache_session.commit.assert_awaited_once()
    
    # Get the entity mappings passed to add_all
    entity_mappings = mock_cache_session.add_all.call_args[0][0]
    assert len(entity_mappings) == len(input_ids)  # One mapping per input ID
    
    # Verify entity mapping fields are correctly populated
    for mapping in entity_mappings:
        # Verify source/target are set correctly
        assert mapping.source_type == source_ontology
        assert mapping.target_type == target_ontology
        assert mapping.source_id in input_ids
        assert mapping.target_id.startswith("TGT_")
        
        # Verify metadata fields
        assert mapping.confidence_score is not None
        assert mapping.hop_count == len(mock_path.steps)
        assert mapping.mapping_direction == "forward"  # since is_reverse = False
        
        # Verify path_details JSON
        path_details = json.loads(mapping.mapping_path_details)
        assert path_details["path_id"] == mock_path_id
        assert path_details["path_name"] == mock_path_name
        assert path_details["is_reversed"] == mock_path.is_reverse
        assert "details" in path_details
        assert "step_1" in path_details["details"]