"""Unit tests for the PathFinder module."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from biomapper.core.engine_components.path_finder import PathFinder
from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.core.exceptions import BiomapperError, ErrorCode
from biomapper.db.models import (
    MappingPath,
    MappingPathStep,
    MappingResource,
    EndpointRelationship,
    Endpoint
)


class TestPathFinder:
    """Test cases for PathFinder class."""
    
    @pytest.fixture
    def path_finder(self):
        """Create a PathFinder instance for testing."""
        return PathFinder(cache_size=10, cache_expiry_seconds=60)
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_paths(self):
        """Create mock mapping paths."""
        path1 = Mock(spec=MappingPath)
        path1.id = 1
        path1.name = "Path 1"
        path1.priority = 10
        path1.is_active = True
        path1.steps = []
        
        path2 = Mock(spec=MappingPath)
        path2.id = 2
        path2.name = "Path 2"
        path2.priority = 20
        path2.is_active = True
        path2.steps = []
        
        return [path1, path2]
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoints."""
        source = Mock(spec=Endpoint)
        source.id = 100
        source.name = "Source Endpoint"
        
        target = Mock(spec=Endpoint)
        target.id = 200
        target.name = "Target Endpoint"
        
        return source, target
    
    def test_init(self, path_finder):
        """Test PathFinder initialization."""
        assert path_finder._path_cache == {}
        assert path_finder._path_cache_timestamps == {}
        assert path_finder._path_cache_max_size == 10
        assert path_finder._path_cache_expiry_seconds == 60
        assert isinstance(path_finder._path_cache_lock, asyncio.Lock)
    
    @pytest.mark.asyncio
    async def test_find_mapping_paths_simple(
        self, path_finder, mock_session, mock_paths
    ):
        """Test simple forward path finding."""
        # Mock the _find_direct_paths method
        with patch.object(
            path_finder,
            '_find_direct_paths',
            return_value=mock_paths
        ) as mock_find:
            result = await path_finder.find_mapping_paths(
                mock_session,
                "SOURCE_TYPE",
                "TARGET_TYPE"
            )
            
            # Should return reversible paths
            assert len(result) == 2
            assert all(isinstance(p, ReversiblePath) for p in result)
            assert all(not p.is_reverse for p in result)
            
            # Should have called _find_direct_paths once
            mock_find.assert_called_once_with(
                mock_session, "SOURCE_TYPE", "TARGET_TYPE"
            )
    
    @pytest.mark.asyncio
    async def test_find_mapping_paths_bidirectional(
        self, path_finder, mock_session, mock_paths
    ):
        """Test bidirectional path finding."""
        # Create different paths for reverse direction
        reverse_paths = [Mock(spec=MappingPath)]
        reverse_paths[0].id = 3
        reverse_paths[0].name = "Reverse Path"
        reverse_paths[0].priority = 15
        reverse_paths[0].steps = []
        
        # Mock the _find_direct_paths method
        with patch.object(
            path_finder,
            '_find_direct_paths',
            side_effect=[mock_paths, reverse_paths]
        ) as mock_find:
            result = await path_finder.find_mapping_paths(
                mock_session,
                "SOURCE_TYPE",
                "TARGET_TYPE",
                bidirectional=True
            )
            
            # Should return both forward and reverse paths
            assert len(result) == 3
            assert sum(1 for p in result if not p.is_reverse) == 2
            assert sum(1 for p in result if p.is_reverse) == 1
            
            # Should have called _find_direct_paths twice
            assert mock_find.call_count == 2
    
    @pytest.mark.asyncio
    async def test_find_mapping_paths_with_relationship(
        self, path_finder, mock_session, mock_paths, mock_endpoints
    ):
        """Test path finding with relationship-specific paths."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock relationship-specific paths
        with patch.object(
            path_finder,
            '_find_paths_for_relationship',
            return_value=mock_paths
        ) as mock_rel_find:
            result = await path_finder.find_mapping_paths(
                mock_session,
                "SOURCE_TYPE",
                "TARGET_TYPE",
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint
            )
            
            # Should use relationship-specific paths
            assert len(result) == 2
            mock_rel_find.assert_called_once_with(
                mock_session,
                source_endpoint.id,
                target_endpoint.id,
                "SOURCE_TYPE",
                "TARGET_TYPE"
            )
    
    @pytest.mark.asyncio
    async def test_find_mapping_paths_caching(
        self, path_finder, mock_session, mock_paths
    ):
        """Test that paths are cached and retrieved from cache."""
        with patch.object(
            path_finder,
            '_find_direct_paths',
            return_value=mock_paths
        ) as mock_find:
            # First call - should hit database
            result1 = await path_finder.find_mapping_paths(
                mock_session, "SOURCE_TYPE", "TARGET_TYPE"
            )
            
            # Second call - should hit cache
            result2 = await path_finder.find_mapping_paths(
                mock_session, "SOURCE_TYPE", "TARGET_TYPE"
            )
            
            # Should only call database once
            mock_find.assert_called_once()
            
            # Results should be the same
            assert len(result1) == len(result2)
    
    @pytest.mark.asyncio
    async def test_find_mapping_paths_cache_expiry(
        self, path_finder, mock_session, mock_paths
    ):
        """Test that expired cache entries are removed."""
        # Set very short expiry
        path_finder._path_cache_expiry_seconds = 0.1
        
        with patch.object(
            path_finder,
            '_find_direct_paths',
            return_value=mock_paths
        ) as mock_find:
            # First call
            await path_finder.find_mapping_paths(
                mock_session, "SOURCE_TYPE", "TARGET_TYPE"
            )
            
            # Wait for expiry
            await asyncio.sleep(0.2)
            
            # Second call - should hit database again
            await path_finder.find_mapping_paths(
                mock_session, "SOURCE_TYPE", "TARGET_TYPE"
            )
            
            # Should call database twice
            assert mock_find.call_count == 2
    
    @pytest.mark.asyncio
    async def test_find_mapping_paths_preferred_direction(
        self, path_finder, mock_session, mock_paths
    ):
        """Test preferred direction ordering."""
        reverse_paths = [Mock(spec=MappingPath)]
        reverse_paths[0].id = 3
        reverse_paths[0].priority = 5  # Higher priority
        reverse_paths[0].steps = []
        
        with patch.object(
            path_finder,
            '_find_direct_paths',
            side_effect=[mock_paths, reverse_paths]
        ):
            # Test with reverse preferred
            result = await path_finder.find_mapping_paths(
                mock_session,
                "SOURCE_TYPE",
                "TARGET_TYPE",
                bidirectional=True,
                preferred_direction="reverse"
            )
            
            # Reverse paths should come first
            assert result[0].is_reverse is True
    
    @pytest.mark.asyncio
    async def test_find_best_path(
        self, path_finder, mock_session, mock_paths
    ):
        """Test finding the best (highest priority) path."""
        with patch.object(
            path_finder,
            'find_mapping_paths',
            return_value=[
                ReversiblePath(mock_paths[0]),
                ReversiblePath(mock_paths[1])
            ]
        ):
            result = await path_finder.find_best_path(
                mock_session,
                "SOURCE_TYPE",
                "TARGET_TYPE"
            )
            
            assert result is not None
            assert result.id == 1  # First path has highest priority
    
    @pytest.mark.asyncio
    async def test_find_best_path_no_paths(
        self, path_finder, mock_session
    ):
        """Test find_best_path when no paths exist."""
        with patch.object(
            path_finder,
            'find_mapping_paths',
            return_value=[]
        ):
            result = await path_finder.find_best_path(
                mock_session,
                "SOURCE_TYPE",
                "TARGET_TYPE"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_find_paths_for_relationship(
        self, path_finder, mock_session, mock_paths
    ):
        """Test finding relationship-specific paths."""
        # Mock relationship
        mock_relationship = Mock(spec=EndpointRelationship)
        mock_relationship.id = 1
        
        # Mock database queries
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_relationship)
        mock_result.scalars = Mock(return_value=Mock(unique=Mock(return_value=Mock(all=Mock(return_value=mock_paths)))))
        
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await path_finder._find_paths_for_relationship(
            mock_session, 100, 200, "SOURCE_TYPE", "TARGET_TYPE"
        )
        
        assert len(result) == 2
        assert mock_session.execute.call_count == 2  # One for relationship, one for paths
    
    @pytest.mark.asyncio
    async def test_find_paths_for_relationship_no_relationship(
        self, path_finder, mock_session
    ):
        """Test when no relationship exists between endpoints."""
        # Mock no relationship found
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await path_finder._find_paths_for_relationship(
            mock_session, 100, 200, "SOURCE_TYPE", "TARGET_TYPE"
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_find_paths_for_relationship_database_error(
        self, path_finder, mock_session
    ):
        """Test database error handling in relationship path finding."""
        # Mock database error
        mock_session.execute = AsyncMock(
            side_effect=SQLAlchemyError("Database error")
        )
        
        with pytest.raises(BiomapperError) as exc_info:
            await path_finder._find_paths_for_relationship(
                mock_session, 100, 200, "SOURCE_TYPE", "TARGET_TYPE"
            )
        
        assert exc_info.value.error_code == ErrorCode.DATABASE_QUERY_ERROR
    
    @pytest.mark.asyncio
    async def test_find_direct_paths_simple(
        self, path_finder, mock_session, mock_paths
    ):
        """Test direct path finding with simple query."""
        # Mock database result
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(unique=Mock(return_value=Mock(all=Mock(return_value=mock_paths)))))
        
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await path_finder._find_direct_paths(
            mock_session, "SOURCE_TYPE", "TARGET_TYPE"
        )
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(
        self, path_finder, mock_session, mock_paths
    ):
        """Test LRU cache eviction when cache is full."""
        # Set small cache size
        path_finder._path_cache_max_size = 2
        
        with patch.object(
            path_finder,
            '_find_direct_paths',
            return_value=mock_paths
        ):
            # Fill cache
            await path_finder.find_mapping_paths(
                mock_session, "TYPE1", "TYPE2"
            )
            await path_finder.find_mapping_paths(
                mock_session, "TYPE3", "TYPE4"
            )
            
            # This should evict the oldest entry
            await path_finder.find_mapping_paths(
                mock_session, "TYPE5", "TYPE6"
            )
            
            # Cache should still have only 2 entries
            assert len(path_finder._path_cache) == 2
    
    def test_clear_cache(self, path_finder):
        """Test cache clearing."""
        # Add some entries to cache
        path_finder._path_cache["key1"] = []
        path_finder._path_cache["key2"] = []
        path_finder._path_cache_timestamps["key1"] = time.time()
        path_finder._path_cache_timestamps["key2"] = time.time()
        
        # Clear cache
        path_finder.clear_cache()
        
        assert len(path_finder._path_cache) == 0
        assert len(path_finder._path_cache_timestamps) == 0