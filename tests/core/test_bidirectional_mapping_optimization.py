"""Tests for the optimized bidirectional mapping implementation."""

import asyncio
import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.mapping_executor import MappingExecutor


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
        # Create a MappingExecutor with small cache size and expiry time
        executor = MappingExecutor(
            path_cache_size=2,  # Small cache size to test LRU behavior
            path_cache_expiry_seconds=1  # Short expiry to test expiration
        )
        
        # Mock _find_direct_paths method to avoid DB calls
        mock_find_direct = mocker.patch.object(
            executor, 
            '_find_direct_paths',
            side_effect=[
                asyncio.Future(),  # For path1
                asyncio.Future(),  # For path2
                asyncio.Future(),  # For path3
            ]
        )
        
        # Set mock return values
        mock_find_direct.side_effect[0].set_result([mocker.Mock(id=1, name="Path1")])
        mock_find_direct.side_effect[1].set_result([mocker.Mock(id=2, name="Path2")])
        mock_find_direct.side_effect[2].set_result([mocker.Mock(id=3, name="Path3")])
        
        # Call _find_mapping_paths multiple times with different keys
        await executor._find_mapping_paths(mocker.Mock(), "source1", "target1")
        assert len(executor._path_cache) == 1
        
        await executor._find_mapping_paths(mocker.Mock(), "source2", "target2")
        assert len(executor._path_cache) == 2
        
        # This should evict the oldest entry due to cache size limit
        await executor._find_mapping_paths(mocker.Mock(), "source3", "target3")
        assert len(executor._path_cache) == 2
        assert "source1_target1_False_forward" not in executor._path_cache
        
        # Test cache expiration
        await asyncio.sleep(1.1)  # Wait for expiration
        
        # This should trigger a new lookup due to expiration
        mock_find_direct.side_effect = [asyncio.Future()]
        mock_find_direct.side_effect[0].set_result([mocker.Mock(id=2, name="Path2")])
        
        await executor._find_mapping_paths(mocker.Mock(), "source2", "target2")
        assert mock_find_direct.call_count == 4

    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, mocker):
        """Test concurrent batch processing implementation."""
        # Create a MappingExecutor with test settings
        executor = MappingExecutor(max_concurrent_batches=3)
        
        # Mock _run_path_steps to track concurrent execution
        concurrent_executions = 0
        max_concurrent = 0
        
        # Define a mock path
        mock_path = mocker.Mock()
        mock_path.id = 1
        mock_path.name = "Test Path"
        mock_path.steps = [mocker.Mock()]
        
        # Define test data - large number of identifiers
        test_identifiers = [f"id_{i}" for i in range(100)]
        
        # Define execution tracker
        execution_times = {}
        completion_order = []
        
        async def mock_run_path_steps(path, initial_input_ids, meta_session, mapping_session_id):
            nonlocal concurrent_executions, max_concurrent
            
            # Track concurrency
            concurrent_executions += 1
            max_concurrent = max(max_concurrent, concurrent_executions)
            
            # Record start time
            batch_id = len(initial_input_ids)
            execution_times[batch_id] = {"start": time.time()}
            
            # Simulate different processing times
            await asyncio.sleep(0.1 if batch_id % 3 == 0 else 0.05)
            
            # Record completion
            execution_times[batch_id]["end"] = time.time()
            completion_order.append(batch_id)
            
            # Decrement concurrency counter
            concurrent_executions -= 1
            
            # Return mock results
            return {
                input_id: {
                    "final_ids": [f"target_{input_id}"],
                    "provenance": [{
                        "path_id": 1,
                        "path_name": "Test Path",
                        "steps_details": [{"client_name": "TestClient", "resource_id": 1}]
                    }]
                }
                for input_id in initial_input_ids
            }
        
        # Mock the _run_path_steps method
        mocker.patch.object(executor, '_run_path_steps', side_effect=mock_run_path_steps)
        
        # Execute the path with our test data
        result = await executor._execute_path(
            mocker.Mock(),  # session
            mock_path,
            test_identifiers,
            "TestSource",
            "TestTarget",
            batch_size=10  # Split into 10 batches of 10 identifiers each
        )
        
        # Verify the maximum concurrency matches our setting
        assert max_concurrent == 3, "Maximum concurrency should match the setting"
        
        # Verify all identifiers were processed
        assert len(result) == 100
        
        # Check some batches completed concurrently
        batch_completions = sorted([(batch_id, data["end"]) for batch_id, data in execution_times.items()], 
                                 key=lambda x: x[1])
        
        # Get time differences between batch completions
        time_diffs = [batch_completions[i+1][1] - batch_completions[i][1] for i in range(len(batch_completions) - 1)]
        
        # Some batches should complete very close to each other (< 0.01s)
        assert any(diff < 0.01 for diff in time_diffs), "No batches completed concurrently"
        
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, mocker):
        """Test metrics tracking implementation."""
        # Create a MappingExecutor with metrics enabled
        executor = MappingExecutor(enable_metrics=True)
        
        # Mock track_mapping_metrics to capture calls
        mock_track_metrics = mocker.patch.object(executor, 'track_mapping_metrics')
        
        # Mock _run_path_steps to return successful results
        async def mock_run_path_steps(path, initial_input_ids, meta_session, mapping_session_id):
            return {
                input_id: {
                    "final_ids": [f"target_{input_id}"],
                    "provenance": [{
                        "path_id": 1,
                        "path_name": "Test Path",
                        "steps_details": [{"client_name": "TestClient", "resource_id": 1}]
                    }]
                }
                for input_id in initial_input_ids
            }
        
        # Mock the necessary methods
        mocker.patch.object(executor, '_run_path_steps', side_effect=mock_run_path_steps)
        mocker.patch.object(executor, '_calculate_confidence_score', return_value=0.9)
        mocker.patch.object(executor, '_create_mapping_path_details', return_value={})
        mocker.patch.object(executor, '_determine_mapping_source', return_value="api")
        
        # Define a mock path
        mock_path = mocker.Mock()
        mock_path.id = 1
        mock_path.name = "Test Path"
        mock_path.steps = [mocker.Mock()]
        
        # Execute the path
        await executor._execute_path(
            mocker.Mock(),  # session
            mock_path,
            ["id_1", "id_2", "id_3"],
            "TestSource",
            "TestTarget",
            batch_size=2  # Should create 2 batches
        )
        
        # Verify metrics were tracked
        assert mock_track_metrics.called
        
        # Check metrics content
        metrics_call = mock_track_metrics.call_args[0]
        assert metrics_call[0] == "path_execution"
        
        metrics_data = metrics_call[1]
        assert metrics_data["path_id"] == 1
        assert metrics_data["input_count"] == 3
        assert metrics_data["success_count"] == 3
        assert "processing_times" in metrics_data
        assert len(metrics_data["processing_times"]) == 2  # 2 batches
    

# Integration test with mock DB session    
class TestIntegrationOptimizedBidirectionalMapping:
    """Integration test for the optimized bidirectional mapping implementation."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_mapping(self, mocker):
        """Test the full end-to-end mapping process with optimization."""
        # Create a MappingExecutor with default settings
        executor = MappingExecutor()
        
        # Mock database methods to avoid real DB calls
        # This would be a more complex setup in a real implementation
        
        # Mock session and path execution
        mock_session = mocker.Mock(spec=AsyncSession)
        
        # For a real integration test, set up mock models, query responses, etc.
        
        # TODO: Implement a more comprehensive integration test
        # This test should validate:
        # 1. End-to-end mapping with bidirectional=True works correctly
        # 2. Performance is better than non-optimized version
        # 3. All metadata fields are correctly populated
        # 4. Metrics are properly tracked
        
        # Placeholder for full implementation
        assert True