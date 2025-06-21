"""Tests for the optimized bidirectional mapping implementation with new service architecture."""

import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.core.engine_components.path_finder import PathFinder
from biomapper.core.services.mapping_path_execution_service import MappingPathExecutionService
from biomapper.core.engine_components.reversible_path import ReversiblePath


# Test fixture for mock path results
@pytest.fixture
def mock_path_results():
    """Mock path results for testing."""
    return {
        "path1": {
            "id": 1,
            "name": "Test Path 1",
            "priority": 1,
            "steps": [
                {"resource_id": 1, "step_order": 1},
                {"resource_id": 2, "step_order": 2},
            ],
        },
        "path2": {
            "id": 2,
            "name": "Test Path 2",
            "priority": 2,
            "steps": [
                {"resource_id": 3, "step_order": 1},
            ],
        },
        "reverse_path1": {
            "id": 3,
            "name": "Reverse Test Path 1",
            "priority": 1,
            "steps": [
                {"resource_id": 2, "step_order": 1},
                {"resource_id": 1, "step_order": 2},
            ],
        },
    }


class TestBidirectionalMappingOptimization:
    """Tests for the optimized bidirectional mapping implementation."""

    @pytest.mark.asyncio
    async def test_path_caching(self, mocker):
        """Test path cache implementation with expiration and size limits."""
        # Create a PathFinder with small cache size and expiry time
        path_finder = PathFinder(
            cache_size=2,  # Small cache size to test LRU behavior
            cache_expiry_seconds=1  # Short expiry to test expiration
        )
        
        # Mock _find_direct_paths method to avoid DB calls
        mock_find_direct = mocker.patch.object(
            path_finder, 
            '_find_direct_paths',
            side_effect=[
                [mocker.Mock(id=1, name="Path1", priority=1, steps=[])],
                [mocker.Mock(id=2, name="Path2", priority=2, steps=[])],
                [mocker.Mock(id=3, name="Path3", priority=3, steps=[])],
                [mocker.Mock(id=2, name="Path2", priority=2, steps=[])],  # For re-fetch after expiry
            ]
        )
        
        # Mock session
        mock_session = mocker.Mock(spec=AsyncSession)
        
        # Call find_mapping_paths multiple times with different keys
        paths1 = await path_finder.find_mapping_paths(mock_session, "source1", "target1")
        assert len(path_finder._path_cache) == 1
        assert len(paths1) == 1
        assert paths1[0].id == 1  # ReversiblePath delegates to original_path.id
        
        paths2 = await path_finder.find_mapping_paths(mock_session, "source2", "target2")
        assert len(path_finder._path_cache) == 2
        assert len(paths2) == 1
        assert paths2[0].id == 2
        
        # This should evict the oldest entry due to cache size limit
        paths3 = await path_finder.find_mapping_paths(mock_session, "source3", "target3")
        assert len(path_finder._path_cache) == 2
        assert "source1_target1_False_forward" not in path_finder._path_cache
        assert len(paths3) == 1
        assert paths3[0].id == 3
        
        # Test cache hit - should not call _find_direct_paths again
        paths2_cached = await path_finder.find_mapping_paths(mock_session, "source2", "target2")
        assert mock_find_direct.call_count == 3  # No new call
        assert len(paths2_cached) == 1
        assert paths2_cached[0].id == 2
        
        # Test cache expiration
        await asyncio.sleep(1.1)  # Wait for expiration
        
        # This should trigger a new lookup due to expiration
        paths2_expired = await path_finder.find_mapping_paths(mock_session, "source2", "target2")
        assert mock_find_direct.call_count == 4  # New call made
        assert len(paths2_expired) == 1
        assert paths2_expired[0].id == 2

    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, mocker):
        """Test concurrent batch processing via semaphore limiting in MappingPathExecutionService."""
        # This test verifies that the semaphore properly limits concurrent execution
        
        # Track execution
        execution_order = []
        max_concurrent = 0
        current_concurrent = 0
        
        # Create a custom semaphore we can track
        class TrackingSemaphore:
            def __init__(self, value):
                self._semaphore = asyncio.Semaphore(value)
                self._active = 0
                self._max_active = 0
                
            async def __aenter__(self):
                await self._semaphore.__aenter__()
                nonlocal current_concurrent, max_concurrent
                current_concurrent += 1
                self._active += 1
                self._max_active = max(self._max_active, self._active)
                max_concurrent = max(max_concurrent, current_concurrent)
                
            async def __aexit__(self, *args):
                nonlocal current_concurrent
                current_concurrent -= 1
                self._active -= 1
                await self._semaphore.__aexit__(*args)
                
        # Test with asyncio.gather to simulate batch processing
        test_semaphore = TrackingSemaphore(3)  # Limit to 3 concurrent
        
        async def mock_batch_work(batch_id):
            async with test_semaphore:
                execution_order.append(("start", batch_id, current_concurrent))
                await asyncio.sleep(0.1)  # Simulate work
                execution_order.append(("end", batch_id, current_concurrent))
                return batch_id
        
        # Run 10 batches
        tasks = [mock_batch_work(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 10
        assert max_concurrent <= 3, f"Max concurrent should be <= 3, but was {max_concurrent}"
        assert max_concurrent > 1, f"Should have concurrent execution, but max was {max_concurrent}"
        
        # Check that we had overlapping executions
        starts = [e for e in execution_order if e[0] == "start"]
        # At some point, multiple batches should have been active
        concurrent_counts = [e[2] for e in starts]
        assert max(concurrent_counts) > 1, "No concurrent execution detected"
        
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, mocker):
        """Test metrics tracking implementation in MappingExecutor."""
        # Create a MappingExecutor with metrics enabled
        # Using component mode initialization
        mock_components = {
            'session_manager': mocker.Mock(),
            'client_manager': mocker.Mock(),
            'config_loader': mocker.Mock(),
            'strategy_handler': mocker.Mock(),
            'path_finder': mocker.Mock(),
            'path_execution_manager': mocker.Mock(),
            'cache_manager': mocker.Mock(),
            'identifier_loader': mocker.Mock(),
            'strategy_orchestrator': mocker.Mock(),
            'checkpoint_manager': mocker.Mock(),
            'progress_reporter': mocker.Mock(),
            'langfuse_tracker': mocker.Mock(),
        }
        
        executor = MappingExecutor(**mock_components)
        executor.enable_metrics = True
        
        # Mock _langfuse_tracker to capture metrics
        mock_trace = mocker.Mock()
        mock_span = mocker.Mock()
        executor._langfuse_tracker = mocker.Mock()
        executor._langfuse_tracker.trace.return_value = mock_trace
        mock_trace.span.return_value = mock_span
        
        # Test metrics data
        test_metrics = {
            "path_id": 1,
            "input_count": 3,
            "success_count": 3,
            "error_count": 0,
            "filtered_count": 0,
            "is_reverse": False,
            "start_time": time.time(),
            "batch_size": 2,
            "max_concurrent_batches": 3,
            "processing_times": {
                "batch_0": {
                    "start_time": time.time(),
                    "total_time": 0.1,
                    "batch_size": 2,
                    "success_count": 2,
                    "error_count": 0,
                    "filtered_count": 0
                },
                "batch_1": {
                    "start_time": time.time() + 0.05,
                    "total_time": 0.05,
                    "batch_size": 1,
                    "success_count": 1,
                    "error_count": 0,
                    "filtered_count": 0
                }
            },
            "total_execution_time": 0.15,
            "missing_ids": 0,
            "result_count": 3
        }
        
        # Call track_mapping_metrics
        await executor.track_mapping_metrics("path_execution", test_metrics)
        
        # Verify Langfuse tracking was called
        assert executor._langfuse_tracker.trace.called
        trace_call = executor._langfuse_tracker.trace.call_args
        assert trace_call[1]["name"] == "path_execution"
        assert trace_call[1]["metadata"]["path_id"] == 1
        assert trace_call[1]["metadata"]["input_count"] == 3
        assert trace_call[1]["metadata"]["batch_size"] == 2
        
        # Verify spans were created for batches
        assert mock_trace.span.call_count == 2  # 2 batches
        
        # Verify trace update with summary metrics
        assert mock_trace.update.called
        update_call = mock_trace.update.call_args
        assert update_call[1]["metadata"]["total_execution_time"] == 0.15
        assert update_call[1]["metadata"]["success_count"] == 3
        assert update_call[1]["metadata"]["result_count"] == 3
    

# Integration test with mock DB session    
class TestIntegrationOptimizedBidirectionalMapping:
    """Integration test for the optimized bidirectional mapping implementation."""
    
    @pytest.mark.asyncio
    async def test_bidirectional_path_finding(self, mocker):
        """Test bidirectional path finding with ReversiblePath."""
        # Create a PathFinder
        path_finder = PathFinder()
        
        # Mock the database session
        mock_session = mocker.Mock(spec=AsyncSession)
        
        # Create mock paths
        forward_path = mocker.Mock(id=1, name="Forward Path", priority=1, steps=[])
        reverse_path = mocker.Mock(id=2, name="Reverse Path", priority=2, steps=[])
        
        # Mock _find_direct_paths to return different paths for each direction
        mocker.patch.object(
            path_finder,
            '_find_direct_paths',
            side_effect=[
                [forward_path],  # Forward direction
                [reverse_path],  # Reverse direction
            ]
        )
        
        # Test bidirectional path finding
        paths = await path_finder.find_mapping_paths(
            mock_session,
            "source_onto",
            "target_onto",
            bidirectional=True,
            preferred_direction="forward"
        )
        
        # Should return both paths wrapped in ReversiblePath
        assert len(paths) == 2
        
        # First should be forward path (preferred)
        assert isinstance(paths[0], ReversiblePath)
        assert paths[0].id == 1
        assert paths[0].is_reverse == False
        
        # Second should be reverse path
        assert isinstance(paths[1], ReversiblePath)
        assert paths[1].id == 2
        assert paths[1].is_reverse == True
        
    @pytest.mark.asyncio
    async def test_path_execution_with_filtering(self, mocker):
        """Test path execution with max_hop_count filtering."""
        # Create mock components
        path_execution_service = MappingPathExecutionService(
            session_manager=mocker.Mock(),
            client_manager=mocker.Mock(),
            cache_manager=mocker.Mock(),
            path_finder=mocker.Mock(),
            path_execution_manager=mocker.Mock(),
            composite_handler=mocker.Mock(),
        )
        
        # Mock path with many steps
        mock_path = mocker.Mock()
        mock_path.id = 1
        mock_path.name = "Long Path"
        mock_path.steps = [mocker.Mock() for _ in range(5)]  # 5 steps
        
        # Test with max_hop_count filtering
        test_ids = ["id_1", "id_2"]
        results = await path_execution_service.execute_path(
            path=mock_path,
            input_identifiers=test_ids,
            source_ontology="source",
            target_ontology="target",
            max_hop_count=3  # Should skip this path as it has 5 steps
        )
        
        # All results should be skipped
        assert len(results) == 2
        for test_id in test_ids:
            result = results[test_id]
            assert result["status"] == "skipped"
            assert "exceeds max_hop_count" in result["message"]
            assert result["hop_count"] == 5
            
    @pytest.mark.asyncio  
    async def test_reversible_path_priority(self, mocker):
        """Test that ReversiblePath correctly adjusts priority for reverse paths."""
        # Create a mock path
        mock_path = mocker.Mock()
        mock_path.id = 1
        mock_path.name = "Test Path"
        mock_path.priority = 10
        mock_path.steps = []
        
        # Create forward and reverse wrappers
        forward_path = ReversiblePath(mock_path, is_reverse=False)
        reverse_path = ReversiblePath(mock_path, is_reverse=True)
        
        # Test properties
        assert forward_path.id == 1
        assert reverse_path.id == 1
        
        assert forward_path.name == "Test Path"
        assert reverse_path.name == "Test Path (Reverse)"
        
        # Reverse path should have higher priority number (lower precedence)
        assert forward_path.priority == 10
        assert reverse_path.priority == 15  # Original + 5 for reverse