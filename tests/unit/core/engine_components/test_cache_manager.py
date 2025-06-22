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
"""Tests for the CacheManager service."""
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from biomapper.core.engine_components.cache_manager import CacheManager, get_current_utc_time
from biomapper.db.cache_models import EntityMapping, PathExecutionLog, PathExecutionStatus
from biomapper.db.models import MappingPath
from biomapper.core.exceptions import (
    CacheError,
    CacheTransactionError,
    CacheRetrievalError,
    CacheStorageError,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_cache_sessionmaker():
    """Create a mock sessionmaker for cache database."""
    sessionmaker = MagicMock()
    return sessionmaker


@pytest.fixture
def cache_manager(mock_cache_sessionmaker, mock_logger):
    """Create a CacheManager instance with mocked dependencies."""
    return CacheManager(
        cache_sessionmaker=mock_cache_sessionmaker,
        logger=mock_logger
    )


class TestCacheManagerCheckCache:
    """Tests for the check_cache method."""
    
    async def test_check_cache_empty_identifiers(self, cache_manager):
        """Test check_cache with empty identifiers list."""
        result, uncached = await cache_manager.check_cache(
            input_identifiers=[],
            source_ontology="source_type",
            target_ontology="target_type"
        )
        
        assert result == {}
        assert uncached == []
    
    async def test_check_cache_no_results(self, cache_manager, mock_cache_sessionmaker):
        """Test check_cache when no cached results exist."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Mock query execution with no results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        result, uncached = await cache_manager.check_cache(
            input_identifiers=["id1", "id2"],
            source_ontology="source_type",
            target_ontology="target_type"
        )
        
        assert result == {}
        assert uncached == ["id1", "id2"]
    
    async def test_check_cache_with_cached_results(self, cache_manager, mock_cache_sessionmaker):
        """Test check_cache when cached results exist."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Create mock EntityMapping
        mock_mapping = MagicMock(spec=EntityMapping)
        mock_mapping.source_id = "id1"
        mock_mapping.target_id = '["target1", "target2"]'
        mock_mapping.confidence_score = 0.95
        mock_mapping.hop_count = 2
        mock_mapping.mapping_direction = "forward"
        mock_mapping.mapping_path_details = json.dumps({
            "path_id": 123,
            "path_name": "test_path"
        })
        
        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_mapping]
        mock_session.execute.return_value = mock_result
        
        result, uncached = await cache_manager.check_cache(
            input_identifiers=["id1", "id2"],
            source_ontology="source_type",
            target_ontology="target_type"
        )
        
        assert len(result) == 1
        assert "id1" in result
        assert result["id1"]["source_identifier"] == "id1"
        assert result["id1"]["target_identifiers"] == ["target1", "target2"]
        assert result["id1"]["mapped_value"] == "target1"
        assert result["id1"]["confidence_score"] == 0.95
        assert result["id1"]["cached"] is True
        assert uncached == ["id2"]
    
    async def test_check_cache_with_path_id_filter(self, cache_manager, mock_cache_sessionmaker):
        """Test check_cache with mapping_path_id filter."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Create mock EntityMappings with different path IDs
        mock_mapping1 = MagicMock(spec=EntityMapping)
        mock_mapping1.source_id = "id1"
        mock_mapping1.target_id = "target1"
        mock_mapping1.confidence_score = 0.95
        mock_mapping1.hop_count = 1
        mock_mapping1.mapping_direction = "forward"
        mock_mapping1.mapping_path_details = json.dumps({"path_id": 123})
        
        mock_mapping2 = MagicMock(spec=EntityMapping)
        mock_mapping2.source_id = "id2"
        mock_mapping2.target_id = "target2"
        mock_mapping2.confidence_score = 0.85
        mock_mapping2.hop_count = 2
        mock_mapping2.mapping_direction = "forward"
        mock_mapping2.mapping_path_details = json.dumps({"path_id": 456})
        
        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_mapping1, mock_mapping2]
        mock_session.execute.return_value = mock_result
        
        result, uncached = await cache_manager.check_cache(
            input_identifiers=["id1", "id2"],
            source_ontology="source_type",
            target_ontology="target_type",
            mapping_path_id=123
        )
        
        assert len(result) == 1
        assert "id1" in result
        assert "id2" not in result
        assert uncached == ["id2"]
    
    async def test_check_cache_with_expiry_time(self, cache_manager, mock_cache_sessionmaker):
        """Test check_cache with expiry_time filter."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        expiry_time = datetime.now(timezone.utc)
        result, uncached = await cache_manager.check_cache(
            input_identifiers=["id1"],
            source_ontology="source_type",
            target_ontology="target_type",
            expiry_time=expiry_time
        )
        
        # Verify that the query was built with expiry_time filter
        mock_session.execute.assert_called_once()
    
    async def test_check_cache_database_error(self, cache_manager, mock_cache_sessionmaker):
        """Test check_cache when database error occurs."""
        # Setup mock session to raise SQLAlchemyError
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(CacheRetrievalError) as exc_info:
            await cache_manager.check_cache(
                input_identifiers=["id1"],
                source_ontology="source_type",
                target_ontology="target_type"
            )
        
        assert "Failed to check cache" in str(exc_info.value)
    
    async def test_check_cache_single_target_identifier(self, cache_manager, mock_cache_sessionmaker):
        """Test check_cache with single target identifier (not JSON array)."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Create mock EntityMapping with single target
        mock_mapping = MagicMock(spec=EntityMapping)
        mock_mapping.source_id = "id1"
        mock_mapping.target_id = "single_target"  # Not a JSON array
        mock_mapping.confidence_score = 0.9
        mock_mapping.hop_count = 1
        mock_mapping.mapping_direction = "forward"
        mock_mapping.mapping_path_details = None
        
        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_mapping]
        mock_session.execute.return_value = mock_result
        
        result, uncached = await cache_manager.check_cache(
            input_identifiers=["id1"],
            source_ontology="source_type",
            target_ontology="target_type"
        )
        
        assert result["id1"]["target_identifiers"] == ["single_target"]
        assert result["id1"]["mapped_value"] == "single_target"


class TestCacheManagerStoreResults:
    """Tests for the store_mapping_results method."""
    
    async def test_store_mapping_results_empty(self, cache_manager):
        """Test store_mapping_results with empty results."""
        result = await cache_manager.store_mapping_results(
            results_to_cache={},
            path=MagicMock(id=1, name="test_path"),
            source_ontology="source_type",
            target_ontology="target_type"
        )
        
        assert result is None
    
    async def test_store_mapping_results_success(self, cache_manager, mock_cache_sessionmaker):
        """Test successful store_mapping_results."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Mock path
        mock_path = MagicMock()
        mock_path.id = 123
        mock_path.name = "test_path"
        mock_path.steps = ["step1", "step2"]
        
        # Mock path log creation
        with patch.object(cache_manager, 'create_path_execution_log') as mock_create_log:
            mock_log = MagicMock()
            mock_log.id = 999
            mock_create_log.return_value = mock_log
            
            # Test data
            results_to_cache = {
                "id1": {
                    "source_identifier": "id1",
                    "target_identifiers": ["target1", "target2"],
                    "confidence_score": 0.95
                }
            }
            
            result = await cache_manager.store_mapping_results(
                results_to_cache=results_to_cache,
                path=mock_path,
                source_ontology="source_type",
                target_ontology="target_type"
            )
            
            assert result == 999
            mock_session.add_all.assert_called_once()
            mock_session.commit.assert_called()
    
    async def test_store_mapping_results_with_reverse_path(self, cache_manager, mock_cache_sessionmaker):
        """Test store_mapping_results with a reverse path."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Mock reverse path
        mock_path = MagicMock()
        mock_path.id = 123
        mock_path.name = "test_path"
        mock_path.steps = ["step1"]
        mock_path.is_reverse = True  # Reverse path
        
        # Mock path log creation
        with patch.object(cache_manager, 'create_path_execution_log') as mock_create_log:
            mock_log = MagicMock()
            mock_log.id = 999
            mock_create_log.return_value = mock_log
            
            results_to_cache = {
                "id1": {
                    "source_identifier": "id1",
                    "target_identifiers": ["target1"]
                }
            }
            
            result = await cache_manager.store_mapping_results(
                results_to_cache=results_to_cache,
                path=mock_path,
                source_ontology="source_type",
                target_ontology="target_type"
            )
            
            # Verify reverse path handling
            assert result == 999
            # Check that entity mappings were created with correct direction
            mock_session.add_all.assert_called_once()
            entity_mappings = mock_session.add_all.call_args[0][0]
            assert len(entity_mappings) == 1
            assert entity_mappings[0].mapping_direction == "reverse"
    
    async def test_store_mapping_results_no_valid_targets(self, cache_manager, mock_cache_sessionmaker):
        """Test store_mapping_results when no valid target identifiers exist."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Mock path
        mock_path = MagicMock()
        mock_path.id = 123
        mock_path.name = "test_path"
        mock_path.steps = []
        
        # Mock path log creation
        with patch.object(cache_manager, 'create_path_execution_log') as mock_create_log:
            mock_log = MagicMock()
            mock_log.id = 999
            mock_log.status = PathExecutionStatus.SUCCESS
            mock_create_log.return_value = mock_log
            
            # Results with None/empty targets
            results_to_cache = {
                "id1": {
                    "source_identifier": "id1",
                    "target_identifiers": [None]
                },
                "id2": {
                    "source_identifier": "id2",
                    "target_identifiers": []
                }
            }
            
            result = await cache_manager.store_mapping_results(
                results_to_cache=results_to_cache,
                path=mock_path,
                source_ontology="source_type",
                target_ontology="target_type"
            )
            
            # Should still return log ID but status should be NO_MAPPING_FOUND
            assert result == 999
            assert mock_log.status == PathExecutionStatus.NO_MAPPING_FOUND
    
    async def test_store_mapping_results_integrity_error(self, cache_manager, mock_cache_sessionmaker):
        """Test store_mapping_results when IntegrityError occurs."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        mock_session.commit.side_effect = IntegrityError("Duplicate key", None, None)
        
        # Mock path
        mock_path = MagicMock()
        mock_path.id = 123
        mock_path.name = "test_path"
        mock_path.steps = []
        
        with patch.object(cache_manager, 'create_path_execution_log') as mock_create_log:
            mock_log = MagicMock()
            mock_log.id = 999
            mock_create_log.return_value = mock_log
            
            results_to_cache = {
                "id1": {
                    "source_identifier": "id1",
                    "target_identifiers": ["target1"]
                }
            }
            
            # Should not raise exception due to integrity error
            result = await cache_manager.store_mapping_results(
                results_to_cache=results_to_cache,
                path=mock_path,
                source_ontology="source_type",
                target_ontology="target_type"
            )
            
            # Transaction should be rolled back but no exception raised
            mock_session.rollback.assert_called()
    
    async def test_store_mapping_results_database_error(self, cache_manager, mock_cache_sessionmaker):
        """Test store_mapping_results when database error occurs."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        # Mock path
        mock_path = MagicMock()
        mock_path.id = 123
        mock_path.name = "test_path"
        mock_path.steps = []
        
        with patch.object(cache_manager, 'create_path_execution_log') as mock_create_log:
            mock_log = MagicMock()
            mock_log.id = 999
            mock_create_log.return_value = mock_log
            
            results_to_cache = {
                "id1": {
                    "source_identifier": "id1",
                    "target_identifiers": ["target1"]
                }
            }
            
            with pytest.raises(CacheStorageError) as exc_info:
                await cache_manager.store_mapping_results(
                    results_to_cache=results_to_cache,
                    path=mock_path,
                    source_ontology="source_type",
                    target_ontology="target_type"
                )
            
            assert "Failed to store cache results" in str(exc_info.value)
            mock_session.rollback.assert_called()


class TestCacheManagerHelperMethods:
    """Tests for helper methods."""
    
    async def test_create_path_execution_log_success(self, cache_manager, mock_cache_sessionmaker):
        """Test successful path execution log creation."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Call method
        log = await cache_manager.create_path_execution_log(
            path_id=123,
            status=PathExecutionStatus.SUCCESS,
            representative_source_id="id1",
            source_entity_type="source_type"
        )
        
        # Verify log was added and committed
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    async def test_create_path_execution_log_error(self, cache_manager, mock_cache_sessionmaker):
        """Test path execution log creation with database error."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(CacheTransactionError) as exc_info:
            await cache_manager.create_path_execution_log(
                path_id=123,
                status=PathExecutionStatus.SUCCESS,
                representative_source_id="id1",
                source_entity_type="source_type"
            )
        
        assert "Failed to create path execution log" in str(exc_info.value)
        mock_session.rollback.assert_called()
    
    def test_calculate_confidence_score_with_existing_score(self, cache_manager):
        """Test confidence score calculation when result already has a score."""
        result = {"confidence_score": 0.88}
        score = cache_manager.calculate_confidence_score(result, hop_count=3, is_reversed=False, path_step_details={})
        assert score == 0.88
    
    def test_calculate_confidence_score_by_hop_count(self, cache_manager):
        """Test confidence score calculation based on hop count."""
        # Test different hop counts
        assert cache_manager.calculate_confidence_score({}, hop_count=1, is_reversed=False, path_step_details={}) == 0.95
        assert cache_manager.calculate_confidence_score({}, hop_count=2, is_reversed=False, path_step_details={}) == 0.85
        assert cache_manager.calculate_confidence_score({}, hop_count=3, is_reversed=False, path_step_details={}) == 0.75
        assert cache_manager.calculate_confidence_score({}, hop_count=5, is_reversed=False, path_step_details={}) == 0.55
        assert cache_manager.calculate_confidence_score({}, hop_count=None, is_reversed=False, path_step_details={}) == 0.7
    
    def test_calculate_confidence_score_with_reverse_penalty(self, cache_manager):
        """Test confidence score calculation with reverse path penalty."""
        # Forward path
        forward_score = cache_manager.calculate_confidence_score({}, hop_count=2, is_reversed=False, path_step_details={})
        # Reverse path
        reverse_score = cache_manager.calculate_confidence_score({}, hop_count=2, is_reversed=True, path_step_details={})
        
        assert forward_score == 0.85
        assert reverse_score == 0.75  # 0.1 penalty for reverse
    
    def test_calculate_confidence_score_with_resource_penalties(self, cache_manager):
        """Test confidence score calculation with resource type penalties."""
        # RAG resource penalty
        rag_details = {
            "steps": [{"resource_name": "rag_resource"}]
        }
        rag_score = cache_manager.calculate_confidence_score({}, hop_count=1, is_reversed=False, path_step_details=rag_details)
        assert rag_score == 0.9  # 0.95 - 0.05 RAG penalty
        
        # LLM resource penalty
        llm_details = {
            "steps": [{"resource_client": "llm_client"}]
        }
        llm_score = cache_manager.calculate_confidence_score({}, hop_count=1, is_reversed=False, path_step_details=llm_details)
        assert llm_score == 0.85  # 0.95 - 0.1 LLM penalty
    
    def test_determine_mapping_source(self, cache_manager):
        """Test determining mapping source from path details."""
        # No details
        assert cache_manager.determine_mapping_source({}) == "api"
        assert cache_manager.determine_mapping_source({"steps": []}) == "api"
        
        # Spoke resource
        spoke_details = {"steps": [{"resource_name": "spoke_resource"}]}
        assert cache_manager.determine_mapping_source(spoke_details) == "spoke"
        
        # RAG resource
        rag_details = {"steps": [{"resource_client": "rag_client"}]}
        assert cache_manager.determine_mapping_source(rag_details) == "rag"
        
        # LLM resource
        llm_details = {"steps": [{"resource_name": "LLM_Resource"}]}
        assert cache_manager.determine_mapping_source(llm_details) == "llm"
        
        # RAMP resource
        ramp_details = {"steps": [{"resource_client": "ramp_system"}]}
        assert cache_manager.determine_mapping_source(ramp_details) == "ramp"
    
    def test_create_mapping_path_details(self, cache_manager):
        """Test creating mapping path details dictionary."""
        details = cache_manager.create_mapping_path_details(
            path_id=123,
            path_name="test_path",
            hop_count=2,
            mapping_direction="forward",
            path_step_details={"steps": ["step1", "step2"]},
            log_id=999,
            additional_metadata={"key": "value"}
        )
        
        assert details["path_id"] == 123
        assert details["path_name"] == "test_path"
        assert details["hop_count"] == 2
        assert details["direction"] == "forward"
        assert details["log_id"] == 999
        assert details["steps"] == ["step1", "step2"]
        assert details["additional_metadata"] == {"key": "value"}
        assert "execution_timestamp" in details


class TestCacheManagerEdgeCases:
    """Tests for edge cases."""
    
    async def test_check_cache_empty_results(self, cache_manager, mock_cache_sessionmaker):
        """Test check_cache correctly handles empty result lists."""
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        # Create mock EntityMapping with empty target list
        mock_mapping = MagicMock(spec=EntityMapping)
        mock_mapping.source_id = "id1"
        mock_mapping.target_id = "[]"  # Empty JSON array
        mock_mapping.confidence_score = 0.0
        mock_mapping.hop_count = 1
        mock_mapping.mapping_direction = "forward"
        mock_mapping.mapping_path_details = None
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_mapping]
        mock_session.execute.return_value = mock_result
        
        result, uncached = await cache_manager.check_cache(
            input_identifiers=["id1"],
            source_ontology="source_type",
            target_ontology="target_type"
        )
        
        assert result["id1"]["target_identifiers"] == []
        assert result["id1"]["mapped_value"] is None
    
    async def test_store_mapping_results_non_list_targets(self, cache_manager, mock_cache_sessionmaker):
        """Test store_mapping_results with non-list target identifiers."""
        mock_session = AsyncMock()
        mock_cache_sessionmaker.return_value.__aenter__.return_value = mock_session
        
        mock_path = MagicMock()
        mock_path.id = 123
        mock_path.name = "test_path"
        mock_path.steps = []
        
        with patch.object(cache_manager, 'create_path_execution_log') as mock_create_log:
            mock_log = MagicMock()
            mock_log.id = 999
            mock_create_log.return_value = mock_log
            
            # Non-list target identifiers
            results_to_cache = {
                "id1": {
                    "source_identifier": "id1",
                    "target_identifiers": "single_target"  # String instead of list
                }
            }
            
            result = await cache_manager.store_mapping_results(
                results_to_cache=results_to_cache,
                path=mock_path,
                source_ontology="source_type",
                target_ontology="target_type"
            )
            
            # Should handle gracefully and convert to list
            assert result == 999
            # Check that add_all was called with entity mappings
            mock_session.add_all.assert_called_once()
            entity_mappings = mock_session.add_all.call_args[0][0]
            assert len(entity_mappings) == 1
            assert entity_mappings[0].target_id == "single_target"
    
    def test_get_current_utc_time(self):
        """Test get_current_utc_time returns UTC timezone aware datetime."""
        time = get_current_utc_time()
        assert time.tzinfo is not None
        assert time.tzinfo.utcoffset(None).total_seconds() == 0