"""Tests for metadata field population in MappingExecutor._cache_results."""

import json
import pytest
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.future import select

from biomapper.db.cache_models import (
    Base as CacheBase,
    EntityMapping,
    PathExecutionStatus,
)
from biomapper.db.models import (
    MappingPath,
    MappingPathStep,
    MappingResource,
)
from biomapper.core.exceptions import (
    CacheError,
)
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.reversible_path import ReversiblePath

logger = logging.getLogger(__name__)

# In-memory database URL for testing
ASYNC_DB_URL = "sqlite+aiosqlite:///:memory:"

# Helper function to create mock mapping results
def create_mock_results(input_ids, target_prefix="TARGET_"):
    """Create mock mapping results for testing."""
    results = {}
    for i, input_id in enumerate(input_ids):
        results[input_id] = {
            "source_identifier": input_id,
            "target_identifiers": [f"{target_prefix}{input_id}"],
            "status": PathExecutionStatus.SUCCESS.value,
            "message": "Test mapping successful",
        }
    return results

# Helper for creating a mock path
def create_mock_path(path_id, path_name, steps_count=2, is_reverse=False):
    """Create a mock path with specified number of steps."""
    # Create mock resources
    resources = []
    for i in range(steps_count):
        resource = MagicMock(spec=MappingResource)
        resource.id = i + 100
        resource.name = f"Resource_{i}"
        resource.resource_type = "api" if i % 2 == 0 else "database"
        resource.input_ontology_term = f"ONTOLOGY_{i}" 
        resource.output_ontology_term = f"ONTOLOGY_{i+1}"
        resources.append(resource)
    
    # Create mock steps
    steps = []
    for i in range(steps_count):
        step = MagicMock(spec=MappingPathStep)
        step.id = i + 200
        step.step_order = i + 1
        step.mapping_resource_id = resources[i].id
        step.mapping_resource = resources[i]
        steps.append(step)
    
    # Create mock path
    path = MagicMock(spec=MappingPath)
    path.id = path_id
    path.name = path_name
    path.steps = steps
    
    # If requested, wrap in a ReversiblePath
    if is_reverse:
        return ReversiblePath(path, is_reverse=True)
    return path

# Ensure foreign key support for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if hasattr(dbapi_connection, "execute"):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

# Fixtures for test database setup
@pytest.fixture(scope="function")
async def async_cache_engine():
    """Create an async SQLAlchemy engine for cache database."""
    # Create engine
    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(CacheBase.metadata.create_all)
    
    # Return engine for use
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(CacheBase.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def async_cache_session_factory(async_cache_engine):
    """Create an async session factory for the cache database."""
    factory = async_sessionmaker(
        bind=async_cache_engine, 
        expire_on_commit=False,
        class_=AsyncSession
    )
    return factory

@pytest.fixture
async def async_cache_session(async_cache_session_factory):
    """Create and yield an async session for the cache database."""
    async with async_cache_session_factory() as session:
        yield session

@pytest.fixture
def mapping_executor():
    """Create a MappingExecutor instance for testing."""
    executor = MappingExecutor(
        metamapper_db_url=ASYNC_DB_URL,
        mapping_cache_db_url=ASYNC_DB_URL,
    )
    # Mock the logger to avoid actual logging during tests
    executor.logger = MagicMock()
    return executor

@pytest.fixture
def patched_executor(mapping_executor, async_cache_session_factory):
    """Patch the executor to use the test session factory."""
    mapping_executor.get_cache_session = lambda: async_cache_session_factory()
    
    # Mock _get_path_details to return predictable data
    async def mock_get_path_details(path_id):
        return {
            "step_1": {
                "resource_name": "TestResource1",
                "resource_type": "api",
                "input_ontology": "SOURCE_ONTOLOGY",
                "output_ontology": "INTERMEDIATE_ONTOLOGY",
            },
            "step_2": {
                "resource_name": "TestResource2",
                "resource_type": "database",
                "input_ontology": "INTERMEDIATE_ONTOLOGY",
                "output_ontology": "TARGET_ONTOLOGY",
            }
        }
    
    mapping_executor._get_path_details = mock_get_path_details
    mapping_executor.get_current_utc_time = lambda: datetime.now(timezone.utc)
    
    return mapping_executor

@pytest.mark.asyncio
async def test_cache_results_populates_metadata_fields(patched_executor, async_cache_session):
    """Test that _cache_results properly populates all metadata fields."""
    # Setup
    source_ontology = "SOURCE_ONTOLOGY"
    target_ontology = "TARGET_ONTOLOGY"
    input_ids = ["TEST_ID1", "TEST_ID2"]
    path_id = 999
    path_name = "Test Metadata Path"
    
    # Create test data
    results_to_cache = create_mock_results(input_ids)
    
    # Create a mock path (normal and reverse versions to test both directions)
    forward_path = create_mock_path(path_id, path_name, steps_count=2, is_reverse=False)
    reverse_path = create_mock_path(path_id, path_name, steps_count=2, is_reverse=True)
    
    # Execute _cache_results with forward path
    await patched_executor._cache_results(
        results_to_cache=results_to_cache,
        path=forward_path,
        source_ontology=source_ontology,
        target_ontology=target_ontology,
        mapping_session_id=123  # Mock session ID
    )
    
    # Query the database to verify forward path results
    stmt = select(EntityMapping).where(
        EntityMapping.source_type == source_ontology,
        EntityMapping.target_type == target_ontology
    )
    
    result = await async_cache_session.execute(stmt)
    forward_mappings = result.scalars().all()
    
    # Assert forward mappings
    assert len(forward_mappings) == len(input_ids)
    
    for mapping in forward_mappings:
        # Verify basic fields
        assert mapping.source_id in input_ids
        assert mapping.target_id == f"TARGET_{mapping.source_id}"
        
        # Verify metadata fields
        assert mapping.hop_count == 2  # Number of steps in the path
        assert mapping.mapping_direction == "forward"
        assert mapping.confidence_score is not None
        
        # Path details should be non-empty JSON
        assert mapping.mapping_path_details is not None
        path_details = json.loads(mapping.mapping_path_details)
        assert path_details["path_id"] == path_id
        assert path_details["path_name"] == path_name
        assert path_details["hop_count"] == 2
        assert path_details["mapping_direction"] == "forward"
        assert "steps" in path_details
    
    # Clear the session
    await async_cache_session.commit()  # Save changes
    await async_cache_session.close()   # Close session
    
    # Now test with reverse path to ensure direction is properly recorded
    async with patched_executor.get_cache_session() as session:
        # First delete existing mappings
        await session.execute(f"DELETE FROM {EntityMapping.__tablename__}")
        await session.commit()
    
    # Execute _cache_results with reverse path
    await patched_executor._cache_results(
        results_to_cache=results_to_cache,
        path=reverse_path,  # Use reverse path
        source_ontology=source_ontology,
        target_ontology=target_ontology,
        mapping_session_id=124  # Different session ID
    )
    
    # Query again to verify reverse path results
    result = await async_cache_session.execute(stmt)
    reverse_mappings = result.scalars().all()
    
    # Assert reverse mappings
    assert len(reverse_mappings) == len(input_ids)
    
    for mapping in reverse_mappings:
        # Verify metadata fields
        assert mapping.hop_count == 2
        assert mapping.mapping_direction == "reverse"
        
        # Confidence should be lower for reverse paths
        assert mapping.confidence_score is not None
        # Should be approximately 0.05 less than for forward path
        assert mapping.confidence_score < 0.9
        
        # Path details should include reverse flag
        path_details = json.loads(mapping.mapping_path_details)
        assert path_details["mapping_direction"] == "reverse"

@pytest.mark.asyncio
async def test_confidence_score_calculation(patched_executor, async_cache_session):
    """Test the confidence score calculation for different path lengths and directions."""
    source_ontology = "SOURCE_ONTOLOGY"
    target_ontology = "TARGET_ONTOLOGY"
    input_id = "TEST_ID_CONF"
    
    # Create test data with a single ID to focus on confidence score
    results_to_cache = create_mock_results([input_id])
    
    # Create test scenarios:
    # 1. Direct (1-hop) forward path
    # 2. 2-hop forward path
    # 3. Multi-hop (3+) forward path
    # 4. Direct (1-hop) reverse path
    # 5. 2-hop reverse path
    # 6. Multi-hop (3+) reverse path
    
    test_scenarios = [
        {"hop_count": 1, "is_reverse": False, "expected_confidence": 0.9},
        {"hop_count": 2, "is_reverse": False, "expected_confidence": 0.8},
        {"hop_count": 4, "is_reverse": False, "expected_confidence": 0.6},
        {"hop_count": 1, "is_reverse": True, "expected_confidence": 0.85},
        {"hop_count": 2, "is_reverse": True, "expected_confidence": 0.75},
        {"hop_count": 4, "is_reverse": True, "expected_confidence": 0.55},
    ]
    
    result_confidences = []
    
    # Run each scenario
    for i, scenario in enumerate(test_scenarios):
        path_id = 1000 + i
        path = create_mock_path(
            path_id=path_id,
            path_name=f"Test Path {i}",
            steps_count=scenario["hop_count"],
            is_reverse=scenario["is_reverse"]
        )
        
        # Execute _cache_results for this scenario
        await patched_executor._cache_results(
            results_to_cache=results_to_cache,
            path=path,
            source_ontology=source_ontology,
            target_ontology=target_ontology,
            mapping_session_id=1000 + i
        )
        
        # Query and record the confidence score
        stmt = select(EntityMapping).where(
            EntityMapping.source_id == input_id,
            EntityMapping.source_type == source_ontology,
            EntityMapping.target_type == target_ontology,
            EntityMapping.mapping_path_details.like(f'%"path_id": {path_id}%')
        )
        
        result = await async_cache_session.execute(stmt)
        mapping = result.scalar_one()
        
        # Store the actual confidence
        result_confidences.append({
            "scenario": scenario,
            "actual_confidence": mapping.confidence_score
        })
        
        # Clear the session
        await async_cache_session.commit()
    
    # Verify all confidence scores
    for result in result_confidences:
        scenario = result["scenario"]
        actual = result["actual_confidence"]
        expected = scenario["expected_confidence"]
        
        # Use approximate comparison with small epsilon
        assert abs(actual - expected) < 0.02, f"Expected ~{expected} but got {actual} for {scenario}"
        
        # Verify the pattern: reverse paths have lower confidence
        if scenario["is_reverse"]:
            # Find matching forward scenario with same hop count
            forward_scenario = next(
                r for r in result_confidences 
                if r["scenario"]["hop_count"] == scenario["hop_count"] and 
                not r["scenario"]["is_reverse"]
            )
            # Reverse should be lower by approximately 0.05
            assert actual < forward_scenario["actual_confidence"]
            assert abs(actual - (forward_scenario["actual_confidence"] - 0.05)) < 0.02

@pytest.mark.asyncio
async def test_mapping_path_details_contents(patched_executor, async_cache_session):
    """Test that mapping_path_details contains complete and correctly structured information."""
    # Setup
    source_ontology = "SOURCE_ONTOLOGY"
    target_ontology = "TARGET_ONTOLOGY"
    input_id = "TEST_ID_DETAILS"
    path_id = 888
    path_name = "Path Details Test"
    
    # Create test data
    results_to_cache = create_mock_results([input_id])
    path = create_mock_path(path_id, path_name, steps_count=3, is_reverse=False)
    
    # Execute _cache_results
    await patched_executor._cache_results(
        results_to_cache=results_to_cache,
        path=path,
        source_ontology=source_ontology,
        target_ontology=target_ontology,
        mapping_session_id=888
    )
    
    # Query for the mapping
    stmt = select(EntityMapping).where(
        EntityMapping.source_id == input_id,
        EntityMapping.source_type == source_ontology,
        EntityMapping.target_type == target_ontology
    )
    
    result = await async_cache_session.execute(stmt)
    mapping = result.scalar_one()
    
    # Parse the mapping_path_details
    path_details = json.loads(mapping.mapping_path_details)
    
    # Verify the structure and contents
    assert path_details["path_id"] == path_id
    assert path_details["path_name"] == path_name
    assert path_details["hop_count"] == 3
    assert path_details["mapping_direction"] == "forward"
    
    # Verify steps information
    assert "steps" in path_details
    assert isinstance(path_details["steps"], list)
    assert len(path_details["steps"]) > 0
    
    # Check first step details
    first_step = path_details["steps"][0]
    assert "step_order" in first_step
    assert "resource_name" in first_step
    assert "resource_type" in first_step
    assert "input_ontology" in first_step
    assert "output_ontology" in first_step

@pytest.mark.asyncio
async def test_cache_results_handles_errors(patched_executor):
    """Test that _cache_results properly handles and reports errors."""
    # Setup
    source_ontology = "SOURCE_ONTOLOGY"
    target_ontology = "TARGET_ONTOLOGY"
    input_ids = ["TEST_ID1", "TEST_ID2"]
    path = create_mock_path(777, "Error Test Path", steps_count=2, is_reverse=False)
    results_to_cache = create_mock_results(input_ids)
    
    # Create mock session that raises an error during add_all
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add_all.side_effect = Exception("Test cache error")
    
    # Create mock context manager
    class MockSessionContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False  # Don't suppress exceptions
    
    # Patch the get_cache_session method
    with patch.object(patched_executor, 'get_cache_session', return_value=MockSessionContext()):
        # Execute _cache_results and expect an error
        with pytest.raises(CacheError):
            await patched_executor._cache_results(
                results_to_cache=results_to_cache,
                path=path,
                source_ontology=source_ontology,
                target_ontology=target_ontology,
                mapping_session_id=777
            )
    
    # Verify the mock was called
    mock_session.add_all.assert_called_once()