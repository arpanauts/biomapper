"""
Test the EnhancedMappingExecutor robust features.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path

import pytest

from biomapper.core.mapping_executor_enhanced import EnhancedMappingExecutor


@pytest.mark.asyncio
async def test_checkpoint_save_load():
    """Test checkpoint saving and loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create executor with checkpointing enabled
        executor = EnhancedMappingExecutor(
            checkpoint_enabled=True,
            checkpoint_dir=tmpdir
        )
        
        # Test data
        execution_id = "test_execution"
        test_state = {
            'processed_count': 100,
            'total_count': 200,
            'results': ['a', 'b', 'c'],
            'custom_data': {'key': 'value'}
        }
        
        # Save checkpoint
        await executor.save_checkpoint(execution_id, test_state)
        
        # Verify checkpoint file exists
        checkpoint_file = Path(tmpdir) / f"{execution_id}.checkpoint"
        assert checkpoint_file.exists()
        
        # Load checkpoint
        loaded_state = await executor.load_checkpoint(execution_id)
        
        # Verify loaded data matches
        assert loaded_state is not None
        assert loaded_state['processed_count'] == 100
        assert loaded_state['total_count'] == 200
        assert loaded_state['results'] == ['a', 'b', 'c']
        assert loaded_state['custom_data']['key'] == 'value'
        assert 'checkpoint_time' in loaded_state
        
        # Clear checkpoint
        await executor.clear_checkpoint(execution_id)
        assert not checkpoint_file.exists()


@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry logic with failing operations."""
    executor = EnhancedMappingExecutor(
        max_retries=3,
        retry_delay=0.1  # Short delay for testing
    )
    
    # Create a failing operation
    attempt_count = 0
    
    async def failing_operation(**kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("Simulated failure")
        return "success"
    
    # Execute with retry
    result = await executor.execute_with_retry(
        operation=failing_operation,
        operation_args={},
        operation_name="test_operation",
        retry_exceptions=(ValueError,)
    )
    
    assert result == "success"
    assert attempt_count == 3


@pytest.mark.asyncio
async def test_batch_processing():
    """Test batch processing with checkpointing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        executor = EnhancedMappingExecutor(
            checkpoint_enabled=True,
            checkpoint_dir=tmpdir,
            batch_size=3
        )
        
        # Test data
        items = list(range(10))
        processed_batches = []
        
        async def process_batch(batch):
            processed_batches.append(batch)
            return [x * 2 for x in batch]
        
        # Process in batches
        results = await executor.process_in_batches(
            items=items,
            processor=process_batch,
            processor_name="test_processor",
            checkpoint_key="test_results",
            execution_id="test_batch_execution"
        )
        
        
        # Verify results
        assert len(processed_batches) == 4  # 10 items / 3 batch_size = 4 batches
        # The process_in_batches method returns a list where each batch result is appended
        assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        
        # Verify checkpoint was saved
        checkpoint = await executor.load_checkpoint("test_batch_execution")
        assert checkpoint is not None
        assert checkpoint['processed_count'] == 10
        assert checkpoint['total_count'] == 10


@pytest.mark.asyncio
async def test_progress_reporting():
    """Test progress reporting callbacks."""
    executor = EnhancedMappingExecutor()
    
    # Track progress reports
    progress_reports = []
    
    def progress_callback(data):
        progress_reports.append(data)
    
    executor.add_progress_callback(progress_callback)
    
    # Trigger some progress reports
    executor._report_progress({
        'type': 'test_progress',
        'value': 50
    })
    
    executor._report_progress({
        'type': 'test_complete',
        'value': 100
    })
    
    # Verify callbacks were called
    assert len(progress_reports) == 2
    assert progress_reports[0]['type'] == 'test_progress'
    assert progress_reports[0]['value'] == 50
    assert progress_reports[1]['type'] == 'test_complete'
    assert progress_reports[1]['value'] == 100


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_checkpoint_save_load())
    asyncio.run(test_retry_logic())
    asyncio.run(test_batch_processing())
    asyncio.run(test_progress_reporting())
    print("All tests passed!")