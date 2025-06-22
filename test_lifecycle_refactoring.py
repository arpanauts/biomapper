"""
Integration test to verify the lifecycle manager refactoring works correctly.
"""

import asyncio
import tempfile
from pathlib import Path

from biomapper.core.mapping_executor import MappingExecutor


async def test_lifecycle_refactoring():
    """Test that the refactored lifecycle components work together."""
    
    print("Creating MappingExecutor with refactored lifecycle components...")
    
    # Create a temporary checkpoint directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create executor with checkpoint enabled
        executor = await MappingExecutor.create(
            metamapper_db_url="sqlite+aiosqlite:///:memory:",
            mapping_cache_db_url="sqlite+aiosqlite:///:memory:",
            checkpoint_enabled=True,
            checkpoint_dir=temp_dir
        )
        
        print("✓ MappingExecutor created successfully")
        
        # Test 1: Verify lifecycle coordinator is properly initialized
        assert hasattr(executor, 'lifecycle_manager'), "Missing lifecycle_manager"
        assert hasattr(executor, 'execution_session_service'), "Missing execution_session_service"
        assert hasattr(executor, 'checkpoint_service'), "Missing checkpoint_service"
        assert hasattr(executor, 'resource_disposal_service'), "Missing resource_disposal_service"
        print("✓ All lifecycle services initialized")
        
        # Test 2: Verify checkpoint service is enabled
        assert executor.lifecycle_manager.checkpoint_enabled, "Checkpointing should be enabled"
        assert executor.checkpoint_service.is_enabled, "Checkpoint service should be enabled"
        assert executor.checkpoint_service.checkpoint_directory == Path(temp_dir)
        print("✓ Checkpoint service configured correctly")
        
        # Test 3: Test session management
        execution_id = "test-execution-123"
        await executor.lifecycle_manager.start_execution(
            execution_id=execution_id,
            execution_type="test",
            metadata={"test": True}
        )
        
        # Verify session is tracked
        assert executor.execution_session_service.is_session_active(execution_id)
        print("✓ Session management working")
        
        # Test 4: Test checkpoint operations
        checkpoint_data = {"state": "processing", "progress": 50}
        await executor.lifecycle_manager.save_checkpoint(execution_id, checkpoint_data)
        
        loaded_data = await executor.lifecycle_manager.load_checkpoint(execution_id)
        assert loaded_data == checkpoint_data
        print("✓ Checkpoint save/load working")
        
        # Test 5: Complete the session
        await executor.lifecycle_manager.complete_execution(
            execution_id=execution_id,
            execution_type="test",
            result_summary={"status": "success"}
        )
        
        assert not executor.execution_session_service.is_session_active(execution_id)
        print("✓ Session completion working")
        
        # Test 6: Test progress callbacks
        callback_called = False
        progress_data = None
        
        def progress_callback(data):
            nonlocal callback_called, progress_data
            callback_called = True
            progress_data = data
        
        executor.lifecycle_manager.add_progress_callback(progress_callback)
        
        await executor.lifecycle_manager.report_progress({
            "event": "test_progress",
            "message": "Testing progress"
        })
        
        # Give async callback time to execute
        await asyncio.sleep(0.1)
        
        assert callback_called, "Progress callback should have been called"
        assert progress_data["event"] == "test_progress"
        print("✓ Progress reporting working")
        
        # Test 7: Test resource disposal
        await executor.lifecycle_manager.async_dispose()
        assert executor.resource_disposal_service.is_disposed
        print("✓ Resource disposal working")
        
        print("\n✅ All tests passed! The lifecycle refactoring is working correctly.")


if __name__ == "__main__":
    asyncio.run(test_lifecycle_refactoring())