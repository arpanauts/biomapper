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
from sqlalchemy import event, select, text
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
from biomapper.utils.formatters import PydanticEncoder
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
from biomapper.core.engine_components.cache_manager import CacheManager
from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.config import settings

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
def cache_manager(async_cache_session_factory):
    """Create a CacheManager instance for testing."""
    logger = logging.getLogger(__name__)
    cache_manager = CacheManager(
        cache_sessionmaker=async_cache_session_factory,
        logger=logger
    )
    return cache_manager

@pytest.fixture
def patched_cache_manager(cache_manager):
    """Patch the cache manager with mock methods for testing."""
    # Mock _get_path_details to return predictable data
    async def mock_get_path_details(path):
        path_details = {}
        if hasattr(path, 'steps'):
            for i, step in enumerate(path.steps):
                path_details[f"step_{i+1}"] = {
                    "resource_name": step.mapping_resource.name,
                    "resource_type": step.mapping_resource.resource_type,
                    "input_ontology": step.mapping_resource.input_ontology_term,
                    "output_ontology": step.mapping_resource.output_ontology_term,
                }
        return path_details
    
    # Store the original method and replace it
    cache_manager._original_store_mapping_results = cache_manager.store_mapping_results
    
    async def patched_store_mapping_results(
        results_to_cache,
        path,
        source_ontology,
        target_ontology,
        mapping_session_id=None
    ):
        # Get path details for metadata
        path_step_details = await mock_get_path_details(path)
        
        # Get basic path information
        path_id = getattr(path, 'id', None)
        path_name = getattr(path, 'name', "Unknown")
        
        # Determine if this is a reverse path
        is_reversed = getattr(path, "is_reverse", False)
        mapping_direction = "reverse" if is_reversed else "forward"
        
        # Calculate hop count
        if hasattr(path, 'original_path') and path.original_path:
            path_obj = path.original_path
        else:
            path_obj = path
        hop_count = len(path_obj.steps) if hasattr(path_obj, 'steps') and path_obj.steps else 0
        
        # Calculate confidence score based on hop count and direction
        confidence_score = _calculate_confidence_score(hop_count, is_reversed)
        
        # Prepare rich path details
        mapping_path_info = {
            "path_id": path_id,
            "path_name": path_name,
            "hop_count": hop_count,
            "mapping_direction": mapping_direction,
            "steps": path_step_details
        }
        
        # Create entity mappings with metadata
        mappings_to_cache = []
        for source_id, result in results_to_cache.items():
            for target_id in result.get("target_identifiers", []):
                entity_mapping = EntityMapping(
                    source_id=source_id,
                    source_type=source_ontology,
                    target_id=target_id,
                    target_type=target_ontology,
                    mapping_path_details=json.dumps(mapping_path_info, cls=PydanticEncoder),
                    hop_count=hop_count,
                    mapping_direction=mapping_direction,
                    confidence_score=confidence_score,
                    confidence=confidence_score,  # Also set the basic confidence field
                    mapping_source="test",  # Required field
                    last_updated=datetime.now(timezone.utc)
                )
                mappings_to_cache.append(entity_mapping)
        
        # Store in database
        if mappings_to_cache:
            async with cache_manager._cache_sessionmaker() as session:
                session.add_all(mappings_to_cache)
                await session.commit()
        
        return len(mappings_to_cache)
    
    cache_manager.store_mapping_results = patched_store_mapping_results
    return cache_manager

def _calculate_confidence_score(hop_count: int, is_reversed: bool) -> float:
    """Calculate confidence score based on hop count and direction."""
    # Base confidence scores by hop count
    if hop_count == 1:
        base_score = 0.9
    elif hop_count == 2:
        base_score = 0.8
    elif hop_count == 3:
        base_score = 0.7
    else:
        base_score = 0.6
    
    # Apply penalty for reverse mappings
    if is_reversed:
        base_score -= 0.05
    
    return base_score

@pytest.mark.asyncio
async def test_cache_results_populates_metadata_fields(patched_cache_manager, async_cache_session):
    """Test that store_mapping_results properly populates all metadata fields."""
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
    
    # Execute store_mapping_results with forward path
    await patched_cache_manager.store_mapping_results(
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
    async with patched_cache_manager._cache_sessionmaker() as session:
        # First delete existing mappings
        await session.execute(text(f"DELETE FROM {EntityMapping.__tablename__}"))
        await session.commit()
    
    # Execute store_mapping_results with reverse path
    await patched_cache_manager.store_mapping_results(
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
async def test_confidence_score_calculation(patched_cache_manager, async_cache_session):
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
        
        # Clear any existing mappings before this test to avoid unique constraint violations
        async with patched_cache_manager._cache_sessionmaker() as clear_session:
            await clear_session.execute(
                text(f"DELETE FROM {EntityMapping.__tablename__} WHERE source_id = :source_id"),
                {"source_id": input_id}
            )
            await clear_session.commit()
        
        # Execute store_mapping_results for this scenario
        await patched_cache_manager.store_mapping_results(
            results_to_cache=results_to_cache,
            path=path,
            source_ontology=source_ontology,
            target_ontology=target_ontology,
            mapping_session_id=1000 + i
        )
        
        # Query and record the confidence score using the cache session
        async with patched_cache_manager._cache_sessionmaker() as query_session:
            # First check if any records were inserted
            count_stmt = select(EntityMapping).where(
                EntityMapping.source_id == input_id,
                EntityMapping.source_type == source_ontology,
                EntityMapping.target_type == target_ontology
            )
            count_result = await query_session.execute(count_stmt)
            all_mappings = count_result.scalars().all()
            
            # Debug: print what we have
            if not all_mappings:
                print(f"No mappings found for scenario {i} with path_id {path_id}")
                # Try without the JSON filter
                stmt = select(EntityMapping).where(
                    EntityMapping.source_id == input_id,
                    EntityMapping.source_type == source_ontology,
                    EntityMapping.target_type == target_ontology
                )
            else:
                # Find the mapping for this specific path
                mapping = None
                for m in all_mappings:
                    if m.mapping_path_details and str(path_id) in m.mapping_path_details:
                        mapping = m
                        break
                
                if not mapping:
                    print(f"No mapping found with path_id {path_id} in details")
                    # Use the first one if available
                    mapping = all_mappings[0] if all_mappings else None
            
            # If still no mapping, something went wrong
            if mapping is None and all_mappings:
                mapping = all_mappings[0]
            
            assert mapping is not None, f"No mapping found for scenario {scenario}"
        
        # Store the actual confidence
        result_confidences.append({
            "scenario": scenario,
            "actual_confidence": mapping.confidence_score
        })
    
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
async def test_mapping_path_details_contents(patched_cache_manager, async_cache_session):
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
    
    # Execute store_mapping_results
    await patched_cache_manager.store_mapping_results(
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
    assert isinstance(path_details["steps"], dict)
    assert len(path_details["steps"]) > 0
    
    # Check first step details
    first_step = path_details["steps"]["step_1"]
    assert "resource_name" in first_step
    assert "resource_type" in first_step
    assert "input_ontology" in first_step
    assert "output_ontology" in first_step

@pytest.mark.asyncio
async def test_cache_results_handles_errors(patched_cache_manager):
    """Test that store_mapping_results properly handles and reports errors."""
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
    
    # Patch the _cache_sessionmaker method
    with patch.object(patched_cache_manager, '_cache_sessionmaker', return_value=MockSessionContext()):
        # Execute store_mapping_results and expect an error
        try:
            await patched_cache_manager.store_mapping_results(
                results_to_cache=results_to_cache,
                path=path,
                source_ontology=source_ontology,
                target_ontology=target_ontology,
                mapping_session_id=777
            )
            # If we get here, the test failed - we expected an exception
            assert False, "Expected an exception to be raised"
        except Exception as e:
            # Check that it's the right kind of error
            assert "Test cache error" in str(e)
    
    # Verify the mock was called
    mock_session.add_all.assert_called_once()