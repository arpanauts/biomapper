"""Tests for the CacheManager component."""
import pytest
import json
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.engine_components.cache_manager import CacheManager
from biomapper.db.cache_models import EntityMapping, PathExecutionLog, PathExecutionStatus

logger = logging.getLogger(__name__)


def create_mock_results(input_ids, target_prefix, offset=1):
    """Helper function to create mock mapping results for caching tests."""
    results = {}
    for i, input_id in enumerate(input_ids):
        target_id = f"{target_prefix}{i + offset}"
        results[input_id] = {
            "target_identifiers": [target_id],
            "confidence_score": 0.95 - (i * 0.01),
            "mapping_path_details": {},
            "hop_count": 2,
            "mapping_direction": "forward",
        }
    return results


class MockAsyncContextManager:
    """Helper for mocking async context managers."""
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
            raise self.raise_exception_on_exit
        return False


@pytest.fixture
def mock_cache_session():
    """Create a mock cache session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_cache_sessionmaker(mock_cache_session):
    """Create a mock sessionmaker that returns the mock session."""
    sessionmaker_mock = MagicMock()
    sessionmaker_mock.return_value = MockAsyncContextManager(mock_cache_session)
    return sessionmaker_mock


@pytest.fixture
def cache_manager(mock_cache_sessionmaker):
    """Create a CacheManager instance with mocked dependencies."""
    logger = logging.getLogger(__name__)
    return CacheManager(
        cache_sessionmaker=mock_cache_sessionmaker,
        logger=logger
    )


@pytest.mark.asyncio
async def test_store_mapping_results_with_metadata(cache_manager, mock_cache_session):
    """Test that store_mapping_results properly populates all metadata fields."""
    # Test values
    source_ontology = "SOURCE_ONT"
    target_ontology = "TARGET_ONT"
    mock_path_id = 42
    mock_path_name = "TestPath"
    mock_session_id = 123
    input_ids = ["ID1", "ID2"]
    
    # Create mock results with test data
    results = create_mock_results(input_ids, "TGT_")
    
    # Create a simple mock path
    mock_path = MagicMock()
    mock_path.id = mock_path_id
    mock_path.name = mock_path_name
    
    # Add steps to calculate hop_count
    step1 = MagicMock()
    step2 = MagicMock()
    mock_path.steps = [step1, step2]
    
    # Add is_reverse attribute for direction check
    mock_path.is_reverse = False
    
    # Mock the path execution log creation
    mock_log = MagicMock()
    mock_log.id = 999
    
    # Setup mock behavior for session operations
    async def mock_commit():
        pass
    
    async def mock_refresh(obj):
        if hasattr(obj, 'relationship_mapping_path_id'):
            obj.id = 999
    
    mock_cache_session.commit = AsyncMock(side_effect=mock_commit)
    mock_cache_session.refresh = AsyncMock(side_effect=mock_refresh)
    
    # Call the method under test
    log_id = await cache_manager.store_mapping_results(
        results, mock_path, source_ontology, target_ontology, mock_session_id
    )
    
    # Verify add was called for log entry
    assert mock_cache_session.add.called
    
    # Verify add_all was called for entity mappings
    mock_cache_session.add_all.assert_called_once()
    mock_cache_session.commit.assert_awaited()
    
    # Get the entity mappings passed to add_all
    entity_mappings = mock_cache_session.add_all.call_args[0][0]
    assert len(entity_mappings) == len(input_ids)
    
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
        assert path_details["hop_count"] == len(mock_path.steps)
        assert path_details["direction"] == "forward"
        assert "execution_timestamp" in path_details


@pytest.mark.asyncio
async def test_calculate_confidence_score():
    """Test confidence score calculation logic."""
    cache_manager = CacheManager(MagicMock(), logging.getLogger())
    
    # Test with existing confidence score in result
    result_with_score = {"confidence_score": 0.99}
    score = cache_manager.calculate_confidence_score(result_with_score, 2, False, {})
    assert score == 0.99
    
    # Test hop count based scoring
    result_no_score = {}
    
    # 1 hop - highest confidence
    score = cache_manager.calculate_confidence_score(result_no_score, 1, False, {})
    assert score == 0.95
    
    # 2 hops
    score = cache_manager.calculate_confidence_score(result_no_score, 2, False, {})
    assert score == 0.85
    
    # 3 hops
    score = cache_manager.calculate_confidence_score(result_no_score, 3, False, {})
    assert score == 0.75
    
    # 4+ hops
    score = cache_manager.calculate_confidence_score(result_no_score, 5, False, {})
    assert score == 0.55
    
    # Test reverse penalty
    score = cache_manager.calculate_confidence_score(result_no_score, 2, True, {})
    assert score == 0.75  # 0.85 - 0.1
    
    # Test resource type penalties
    path_details_with_rag = {
        "steps": [{"resource_name": "rag_client"}]
    }
    score = cache_manager.calculate_confidence_score(result_no_score, 2, False, path_details_with_rag)
    assert score == 0.80  # 0.85 - 0.05
    
    path_details_with_llm = {
        "steps": [{"resource_client": "llm_service"}]
    }
    score = cache_manager.calculate_confidence_score(result_no_score, 2, False, path_details_with_llm)
    assert score == 0.75  # 0.85 - 0.1


@pytest.mark.asyncio
async def test_determine_mapping_source():
    """Test mapping source determination logic."""
    cache_manager = CacheManager(MagicMock(), logging.getLogger())
    
    # Test default
    assert cache_manager.determine_mapping_source({}) == 'api'
    assert cache_manager.determine_mapping_source(None) == 'api'
    
    # Test spoke detection
    path_details_spoke = {
        "steps": [{"resource_name": "spoke_resource"}]
    }
    assert cache_manager.determine_mapping_source(path_details_spoke) == 'spoke'
    
    # Test rag detection
    path_details_rag = {
        "steps": [{"resource_client": "rag_client"}]
    }
    assert cache_manager.determine_mapping_source(path_details_rag) == 'rag'
    
    # Test llm detection
    path_details_llm = {
        "steps": [{"resource_name": "llm_model"}]
    }
    assert cache_manager.determine_mapping_source(path_details_llm) == 'llm'
    
    # Test ramp detection
    path_details_ramp = {
        "steps": [{"resource_client": "ramp_service"}]
    }
    assert cache_manager.determine_mapping_source(path_details_ramp) == 'ramp'


@pytest.mark.asyncio
async def test_check_cache_with_results(cache_manager, mock_cache_session):
    """Test cache checking with existing results."""
    source_ontology = "SOURCE_ONT"
    target_ontology = "TARGET_ONT"
    input_ids = ["ID1", "ID2", "ID3"]
    
    # Create mock cached entities
    cached_entity1 = MagicMock(spec=EntityMapping)
    cached_entity1.source_id = "ID1"
    cached_entity1.target_id = "TGT_1"
    cached_entity1.confidence_score = 0.95
    cached_entity1.hop_count = 2
    cached_entity1.mapping_direction = "forward"
    cached_entity1.mapping_path_details = json.dumps({
        "path_id": 42,
        "path_name": "TestPath"
    })
    
    cached_entity2 = MagicMock(spec=EntityMapping)
    cached_entity2.source_id = "ID2"
    cached_entity2.target_id = json.dumps(["TGT_2A", "TGT_2B"])  # Multiple targets
    cached_entity2.confidence_score = 0.90
    cached_entity2.hop_count = 3
    cached_entity2.mapping_direction = "reverse"
    cached_entity2.mapping_path_details = json.dumps({
        "path_id": 43,
        "path_name": "AnotherPath"
    })
    
    # Setup mock query results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [cached_entity1, cached_entity2]
    mock_cache_session.execute = AsyncMock(return_value=mock_result)
    
    # Call check_cache
    cached_results, uncached_ids = await cache_manager.check_cache(
        input_ids, source_ontology, target_ontology
    )
    
    # Verify results
    assert len(cached_results) == 2
    assert "ID1" in cached_results
    assert "ID2" in cached_results
    assert len(uncached_ids) == 1
    assert "ID3" in uncached_ids
    
    # Verify ID1 result structure
    id1_result = cached_results["ID1"]
    assert id1_result["source_identifier"] == "ID1"
    assert id1_result["target_identifiers"] == ["TGT_1"]
    assert id1_result["mapped_value"] == "TGT_1"
    assert id1_result["confidence_score"] == 0.95
    assert id1_result["hop_count"] == 2
    assert id1_result["mapping_direction"] == "forward"
    assert id1_result["cached"] is True
    
    # Verify ID2 result structure (multiple targets)
    id2_result = cached_results["ID2"]
    assert id2_result["source_identifier"] == "ID2"
    assert id2_result["target_identifiers"] == ["TGT_2A", "TGT_2B"]
    assert id2_result["mapped_value"] == "TGT_2A"  # First target
    assert id2_result["confidence_score"] == 0.90
    assert id2_result["hop_count"] == 3
    assert id2_result["mapping_direction"] == "reverse"


@pytest.mark.asyncio
async def test_check_cache_with_path_id_filter(cache_manager, mock_cache_session):
    """Test cache checking with path ID filtering."""
    source_ontology = "SOURCE_ONT"
    target_ontology = "TARGET_ONT"
    input_ids = ["ID1"]
    path_id_filter = 42
    
    # Create two entities - one matching path ID, one not
    matching_entity = MagicMock(spec=EntityMapping)
    matching_entity.source_id = "ID1"
    matching_entity.target_id = "TGT_1"
    matching_entity.confidence_score = 0.95
    matching_entity.hop_count = 2
    matching_entity.mapping_direction = "forward"
    matching_entity.mapping_path_details = json.dumps({"path_id": 42})
    
    non_matching_entity = MagicMock(spec=EntityMapping)
    non_matching_entity.source_id = "ID1"
    non_matching_entity.target_id = "TGT_2"
    non_matching_entity.confidence_score = 0.90
    non_matching_entity.hop_count = 3
    non_matching_entity.mapping_direction = "forward"
    non_matching_entity.mapping_path_details = json.dumps({"path_id": 99})
    
    # Setup mock query results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [matching_entity, non_matching_entity]
    mock_cache_session.execute = AsyncMock(return_value=mock_result)
    
    # Call check_cache with path ID filter
    cached_results, uncached_ids = await cache_manager.check_cache(
        input_ids, source_ontology, target_ontology, mapping_path_id=path_id_filter
    )
    
    # Verify only the matching entity is returned
    assert len(cached_results) == 1
    assert "ID1" in cached_results
    assert cached_results["ID1"]["target_identifiers"] == ["TGT_1"]
    assert len(uncached_ids) == 0