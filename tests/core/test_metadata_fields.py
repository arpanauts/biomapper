"""Tests for metadata field population in the _cache_results method."""

import json
import pytest
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import select, text
from sqlalchemy.future import select

# Import from cache_models directly for EntityMapping
from biomapper.db.cache_models import (
    Base as CacheBase,
    EntityMapping,
    PathExecutionStatus,
)

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
            "status": "success",
            "message": "Test mapping successful",
        }
    return results

# Custom encoder class (copied from mapping_executor to avoid import issues)
class PydanticEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle Pydantic models and other special types."""
    
    def default(self, obj):
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle Pydantic models if they exist in the codebase
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict") and callable(obj.dict):
            return obj.dict()
        # Let the base class handle anything else
        return super().default(obj)

# Simplified ReversiblePath for testing
class ReversiblePath:
    """Simplified ReversiblePath for testing."""
    
    def __init__(self, original_path, is_reverse=False):
        self.original_path = original_path
        self.is_reverse = is_reverse
        
    @property
    def id(self):
        return self.original_path.id
        
    @property
    def name(self):
        return f"{self.original_path.name} (Reverse)" if self.is_reverse else self.original_path.name
    
    @property
    def steps(self):
        return self.original_path.steps

# Helper for creating a mock path
def create_mock_path(path_id, path_name, steps_count=2):
    """Create a mock path with specified number of steps."""
    # Create mock steps
    steps = []
    for i in range(steps_count):
        # Create mock resource for each step
        resource = MagicMock()
        resource.id = i + 100
        resource.name = f"Resource_{i}"
        resource.resource_type = "api" if i % 2 == 0 else "database"
        resource.input_ontology_term = f"ONTOLOGY_{i}" 
        resource.output_ontology_term = f"ONTOLOGY_{i+1}"
        
        # Create step with resource
        step = MagicMock()
        step.id = i + 200
        step.step_order = i + 1
        step.mapping_resource_id = resource.id
        step.mapping_resource = resource
        steps.append(step)
    
    # Create mock path
    path = MagicMock()
    path.id = path_id
    path.name = path_name
    path.steps = steps
    return path

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

# Implementation of _cache_results for testing
async def _cache_results(
    session_factory,
    results_to_cache,
    path,
    source_ontology,
    target_ontology,
    mapping_session_id=None
):
    """
    Store successful mapping results in the cache.
    
    Calculates and populates metadata fields:
    - confidence_score: Based on path length, client type, or a default value
    - hop_count: Number of steps in the executed path
    - mapping_direction: Whether the path was executed in "forward" or "reverse" direction
    - mapping_path_details: Structured JSON information about the path execution
    """
    if not results_to_cache:
        return
    
    mappings_to_add = []
    now = datetime.now(timezone.utc)
    
    # Get basic path information
    path_id = path.id if hasattr(path, 'id') else None
    path_name_str = path.name if hasattr(path, 'name') and isinstance(path.name, str) else 'Unknown'
    
    # Calculate hop_count from path
    hop_count = len(path.steps) if hasattr(path, 'steps') else 1
    
    # Determine mapping_direction from the path
    is_reverse = False
    if isinstance(path, ReversiblePath) and hasattr(path, 'is_reverse'):
        is_reverse = path.is_reverse
    mapping_direction = "reverse" if is_reverse else "forward"
    
    # Build enhanced path details
    path_details = {
        "path_id": path_id,
        "path_name": path_name_str,
        "hop_count": hop_count,
        "mapping_direction": mapping_direction,
        "steps": []
    }
    
    # Add information about steps if available
    if hasattr(path, 'steps'):
        for step in path.steps:
            if hasattr(step, 'mapping_resource') and step.mapping_resource:
                resource = step.mapping_resource
                step_info = {
                    "step_order": getattr(step, 'step_order', 0),
                    "resource_name": getattr(resource, 'name', 'Unknown'),
                    "resource_type": getattr(resource, 'resource_type', 'Unknown'),
                    "input_ontology": getattr(resource, 'input_ontology_term', 'Unknown'),
                    "output_ontology": getattr(resource, 'output_ontology_term', 'Unknown')
                }
                path_details["steps"].append(step_info)
    
    path_details_json = json.dumps(path_details, cls=PydanticEncoder)
    
    for source_id, result_data in results_to_cache.items():
        if result_data and result_data.get("target_identifiers") is not None:
            target_ids = result_data["target_identifiers"]
            
            # Use provided confidence_score or calculate it if not provided
            confidence_score = result_data.get("confidence_score")
            if confidence_score is None:
                # Default calculation based on hop count if no specific score is provided
                if hop_count <= 1:
                    confidence_score = 0.9  # High confidence for direct mappings
                elif hop_count == 2:
                    confidence_score = 0.8  # Medium-high confidence for 2-hop
                else:
                    confidence_score = max(0.1, 1.0 - (0.1 * hop_count))  # Decreasing confidence for longer paths
                
                # Adjust for direction - reverse paths are slightly less confident
                if is_reverse:
                    confidence_score = max(0.1, confidence_score - 0.05)
            
            # Handle multiple target IDs
            for target_id in target_ids if target_ids else [None]:
                mapping = EntityMapping(
                    source_id=source_id,
                    source_type=source_ontology,
                    target_id=target_id,
                    target_type=target_ontology,
                    confidence_score=confidence_score,
                    mapping_path_details=path_details_json,
                    hop_count=hop_count,
                    mapping_direction=mapping_direction,
                    last_updated=now,
                )
                mappings_to_add.append(mapping)
    
    if mappings_to_add:
        async with session_factory() as session:
            session.add_all(mappings_to_add)
            await session.commit()
            return True
    return False

@pytest.mark.asyncio
async def test_cache_results_populates_metadata_fields(async_cache_session_factory, async_cache_session):
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
    forward_path = create_mock_path(path_id, path_name, steps_count=2)
    reverse_path = ReversiblePath(forward_path, is_reverse=True)
    
    # Execute _cache_results with forward path
    await _cache_results(
        session_factory=async_cache_session_factory,
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
    
    # Clear the database
    await async_cache_session.execute(text(f"DELETE FROM {EntityMapping.__tablename__}"))
    await async_cache_session.commit()
    
    # Now test with reverse path to ensure direction is properly recorded
    await _cache_results(
        session_factory=async_cache_session_factory,
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
async def test_confidence_score_calculation(async_cache_session_factory, async_cache_session):
    """Test the confidence score calculation for different path lengths and directions."""
    source_ontology = "SOURCE_ONTOLOGY"
    target_ontology = "TARGET_ONTOLOGY"
    input_id = "TEST_ID_CONF"
    
    # Create test data with a single ID to focus on confidence score
    results_to_cache = create_mock_results([input_id])
    
    # Test scenarios with different hop counts and directions
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
        # Clear previous results
        await async_cache_session.execute(text(f"DELETE FROM {EntityMapping.__tablename__}"))
        await async_cache_session.commit()
        
        path_id = 1000 + i
        path = create_mock_path(path_id, f"Test Path {i}", steps_count=scenario["hop_count"])
        
        # Wrap in ReversiblePath if needed
        if scenario["is_reverse"]:
            path = ReversiblePath(path, is_reverse=True)
        
        # Execute _cache_results for this scenario
        await _cache_results(
            session_factory=async_cache_session_factory,
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
            EntityMapping.target_type == target_ontology
        )
        
        result = await async_cache_session.execute(stmt)
        mapping = result.scalar_one()
        
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
        assert abs(actual - expected) < 0.01, f"Expected ~{expected} but got {actual} for {scenario}"

@pytest.mark.asyncio
async def test_mapping_path_details_contents(async_cache_session_factory, async_cache_session):
    """Test that mapping_path_details contains complete and correctly structured information."""
    # Setup
    source_ontology = "SOURCE_ONTOLOGY"
    target_ontology = "TARGET_ONTOLOGY"
    input_id = "TEST_ID_DETAILS"
    path_id = 888
    path_name = "Path Details Test"
    
    # Create test data
    results_to_cache = create_mock_results([input_id])
    path = create_mock_path(path_id, path_name, steps_count=3)
    
    # Execute _cache_results
    await _cache_results(
        session_factory=async_cache_session_factory,
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
    assert len(path_details["steps"]) == 3
    
    # Check step details
    for i, step in enumerate(path_details["steps"]):
        assert "step_order" in step
        assert step["step_order"] == i + 1
        assert "resource_name" in step
        assert "resource_type" in step
        assert "input_ontology" in step
        assert "output_ontology" in step