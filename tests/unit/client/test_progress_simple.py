"""Simplified tests for client progress tracking."""

import pytest
import time

from src.client.progress import ProgressTracker, NoOpProgressTracker


class TestProgressTracker:
    """Test ProgressTracker functionality."""

    def test_progress_tracker_initialization(self):
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker(100, "Processing data")
        
        assert tracker.total_steps == 100
        assert tracker.current_step == 0
        assert tracker.description == "Processing data"
        assert tracker.backends == []
        assert tracker._is_closed is False

    def test_progress_tracker_default_description(self):
        """Test ProgressTracker with default description."""
        tracker = ProgressTracker(50)
        
        assert tracker.total_steps == 50
        assert tracker.description == "Processing"

    def test_progress_tracker_percentage_calculation(self):
        """Test progress percentage calculation."""
        tracker = ProgressTracker(100)
        
        # Initial state
        assert tracker.percentage == 0.0
        
        # Update progress
        tracker.current_step = 25
        assert tracker.percentage == 25.0
        
        tracker.current_step = 50
        assert tracker.percentage == 50.0
        
        tracker.current_step = 100
        assert tracker.percentage == 100.0

    def test_progress_tracker_percentage_edge_cases(self):
        """Test progress percentage calculation edge cases."""
        # Zero total steps
        tracker = ProgressTracker(0)
        assert tracker.percentage == 100.0
        
        # Steps exceed total
        tracker = ProgressTracker(100)
        tracker.current_step = 150
        assert tracker.percentage == 150.0


class TestProgressTrackerUpdate:
    """Test ProgressTracker update functionality."""

    def test_update_with_increment(self):
        """Test update with increment."""
        tracker = ProgressTracker(100)
        
        # Default increment of 1
        tracker.update()
        assert tracker.current_step == 1
        
        # Custom increment
        tracker.update(increment=5)
        assert tracker.current_step == 6

    def test_update_with_absolute_step(self):
        """Test update with absolute step number."""
        tracker = ProgressTracker(100)
        
        tracker.update(step=25)
        assert tracker.current_step == 25
        
        tracker.update(step=75)
        assert tracker.current_step == 75

    def test_update_step_clamping(self):
        """Test that step updates are clamped to total_steps."""
        tracker = ProgressTracker(100)
        
        # Step set higher than total should be clamped
        tracker.update(step=150)
        assert tracker.current_step == 100
        
        # Increment beyond total should be clamped
        tracker.current_step = 95
        tracker.update(increment=10)
        assert tracker.current_step == 100

    def test_update_after_closed(self):
        """Test that updates are ignored after tracker is closed."""
        tracker = ProgressTracker(100)
        
        tracker.close()
        tracker.update(step=50)
        
        # Should remain at 0 since tracker is closed
        assert tracker.current_step == 0

    def test_update_with_message(self):
        """Test update with message (verified through backend calls)."""
        tracker = ProgressTracker(100)
        
        # Add mock callback to verify message passing
        callback_calls = []
        def mock_callback(current, total, message):
            callback_calls.append((current, total, message))
        
        tracker.add_callback(mock_callback)
        tracker.update(step=25, message="Processing data...")
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == (25, 100, "Processing data...")


class TestProgressTrackerCallback:
    """Test ProgressTracker callback functionality."""

    def test_add_callback(self):
        """Test adding callback."""
        tracker = ProgressTracker(100)
        
        def test_callback(current, total, message):
            pass
        
        result = tracker.add_callback(test_callback)
        
        assert result is tracker  # Method chaining
        assert len(tracker.backends) == 1
        assert tracker.backends[0][0] == "callback"
        assert tracker.backends[0][1] is test_callback

    def test_callback_invocation(self):
        """Test callback invocation."""
        tracker = ProgressTracker(100, "Processing")
        
        callback_calls = []
        def test_callback(current, total, message):
            callback_calls.append((current, total, message))
        
        tracker.add_callback(test_callback)
        
        # Test updates
        tracker.update(step=25, message="Step 1")
        tracker.update(step=50, message="Step 2")
        tracker.update(step=100)  # No message
        
        assert len(callback_calls) == 3
        assert callback_calls[0] == (25, 100, "Step 1")
        assert callback_calls[1] == (50, 100, "Step 2")
        assert callback_calls[2] == (100, 100, "Processing")  # Default description

    def test_multiple_callbacks(self):
        """Test multiple callbacks."""
        tracker = ProgressTracker(100)
        
        calls_1 = []
        calls_2 = []
        
        def callback_1(current, total, message):
            calls_1.append((current, total, message))
        
        def callback_2(current, total, message):
            calls_2.append((current, total, message))
        
        tracker.add_callback(callback_1)
        tracker.add_callback(callback_2)
        
        tracker.update(step=50, message="Test")
        
        # Both callbacks should be called
        assert len(calls_1) == 1
        assert len(calls_2) == 1
        assert calls_1[0] == (50, 100, "Test")
        assert calls_2[0] == (50, 100, "Test")

    def test_callback_exception_handling(self):
        """Test that callback exceptions don't break progress tracking."""
        tracker = ProgressTracker(100)
        
        def failing_callback(current, total, message):
            raise Exception("Callback failed")
        
        def working_callback(current, total, message):
            working_callback.called = True
        
        working_callback.called = False
        
        tracker.add_callback(failing_callback)
        tracker.add_callback(working_callback)
        
        # Update should not raise exception
        tracker.update(step=50)
        
        # Working callback should still be called
        assert working_callback.called is True


class TestProgressTrackerDescriptionManagement:
    """Test ProgressTracker description management."""

    def test_set_description(self):
        """Test setting description."""
        tracker = ProgressTracker(100, "Initial description")
        
        tracker.set_description("New description")
        
        assert tracker.description == "New description"

    def test_set_description_with_callback(self):
        """Test that setting description works with callbacks."""
        tracker = ProgressTracker(100, "Initial")
        
        callback_calls = []
        def test_callback(current, total, message):
            callback_calls.append(message)
        
        tracker.add_callback(test_callback)
        tracker.set_description("Updated description")
        
        # Update to trigger callback with new description
        tracker.update(step=25)
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == "Updated description"


class TestProgressTrackerContextManager:
    """Test ProgressTracker context manager functionality."""

    def test_context_manager_enter_exit(self):
        """Test context manager enter and exit."""
        tracker = ProgressTracker(100, "Processing")
        
        with tracker as ctx_tracker:
            assert ctx_tracker is tracker
            assert tracker._is_closed is False
        
        # Should be closed after exiting context
        assert tracker._is_closed is True

    def test_context_manager_with_callbacks(self):
        """Test context manager with callback backends."""
        tracker = ProgressTracker(100)
        
        callback_calls = []
        def test_callback(current, total, message):
            callback_calls.append((current, total, message))
        
        tracker.add_callback(test_callback)
        
        with tracker:
            tracker.update(step=50, message="Processing")
            assert len(callback_calls) == 1
        
        # Tracker should be closed
        assert tracker._is_closed is True

    def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly."""
        tracker = ProgressTracker(100)
        
        try:
            with tracker:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Tracker should still be closed despite exception
        assert tracker._is_closed is True


class TestProgressTrackerCloseBehavior:
    """Test ProgressTracker close behavior."""

    def test_close_single_call(self):
        """Test that close can be called safely multiple times."""
        tracker = ProgressTracker(100)
        
        tracker.close()
        assert tracker._is_closed is True
        
        # Multiple close calls should be safe
        tracker.close()
        tracker.close()

    def test_close_with_callbacks(self):
        """Test that close works with callback backends."""
        tracker = ProgressTracker(100)
        
        def test_callback(current, total, message):
            pass
        
        tracker.add_callback(test_callback)
        
        # Should not raise exception
        tracker.close()
        
        assert tracker._is_closed is True


class TestNoOpProgressTracker:
    """Test NoOpProgressTracker functionality."""

    def test_noop_tracker_initialization(self):
        """Test NoOpProgressTracker initialization."""
        tracker = NoOpProgressTracker(100, "Processing")
        
        # Should not raise any exceptions
        assert tracker is not None

    def test_noop_tracker_methods(self):
        """Test NoOpProgressTracker methods are no-ops."""
        tracker = NoOpProgressTracker()
        
        # All methods should return self for chaining or None
        assert tracker.add_tqdm() is tracker
        assert tracker.add_rich() is tracker
        assert tracker.add_callback(lambda x, y, z: None) is tracker
        assert tracker.add_jupyter() is tracker
        
        # These should not raise exceptions
        tracker.update(step=50, message="Test")
        tracker.set_description("New description")
        tracker.close()

    def test_noop_tracker_percentage(self):
        """Test NoOpProgressTracker percentage property."""
        tracker = NoOpProgressTracker()
        
        assert tracker.percentage == 0.0

    def test_noop_tracker_context_manager(self):
        """Test NoOpProgressTracker context manager."""
        tracker = NoOpProgressTracker()
        
        with tracker as ctx_tracker:
            assert ctx_tracker is tracker
            
            # These should not raise exceptions
            tracker.update(step=50)
            tracker.set_description("Test")
        
        # No exceptions should be raised


class TestProgressTrackerEdgeCases:
    """Test ProgressTracker edge cases."""

    def test_zero_total_steps(self):
        """Test tracker with zero total steps."""
        tracker = ProgressTracker(0)
        
        assert tracker.total_steps == 0
        assert tracker.percentage == 100.0
        
        # Updates should not crash
        tracker.update(step=1)
        assert tracker.current_step == 0  # Clamped to total_steps
        assert tracker.percentage == 100.0

    def test_negative_total_steps(self):
        """Test tracker with negative total steps."""
        tracker = ProgressTracker(-10)
        
        assert tracker.total_steps == -10
        
        # Should handle gracefully
        tracker.update(step=5)
        assert tracker.current_step == -10  # Clamped to total_steps

    def test_very_large_total_steps(self):
        """Test tracker with very large total steps."""
        large_total = 10**9  # 1 billion steps
        tracker = ProgressTracker(large_total)
        
        assert tracker.total_steps == large_total
        
        tracker.update(step=large_total // 2)
        assert tracker.percentage == 50.0

    def test_unicode_description_and_messages(self):
        """Test handling of Unicode in descriptions and messages."""
        unicode_description = "Processing 你好 🌟 café"
        tracker = ProgressTracker(100, unicode_description)
        
        assert tracker.description == unicode_description
        
        callback_calls = []
        def unicode_callback(current, total, message):
            callback_calls.append(message)
        
        tracker.add_callback(unicode_callback)
        
        unicode_message = "Step with unicode: 🚀 ñoño"
        tracker.update(step=50, message=unicode_message)
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == unicode_message

    def test_empty_string_description(self):
        """Test handling of empty string description."""
        tracker = ProgressTracker(100, "")
        
        assert tracker.description == ""
        
        # Should not cause issues with backends
        callback_calls = []
        def test_callback(current, total, message):
            callback_calls.append(message)
        
        tracker.add_callback(test_callback)
        tracker.update(step=25)
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == ""  # Empty description


class TestProgressTrackerPerformance:
    """Test ProgressTracker performance characteristics."""

    def test_update_performance_without_backends(self):
        """Test update performance without backends."""
        tracker = ProgressTracker(10000)
        
        start_time = time.time()
        
        for i in range(1000):
            tracker.update(step=i)
        
        end_time = time.time()
        
        # Should complete quickly (under 100ms for 1000 updates)
        assert end_time - start_time < 0.1

    def test_update_performance_with_callback(self):
        """Test update performance with callback backend."""
        tracker = ProgressTracker(10000)
        
        call_count = 0
        def fast_callback(current, total, message):
            nonlocal call_count
            call_count += 1
        
        tracker.add_callback(fast_callback)
        
        start_time = time.time()
        
        for i in range(100):
            tracker.update(step=i)
        
        end_time = time.time()
        
        # Should complete quickly and call callback for each update
        assert end_time - start_time < 0.1
        assert call_count == 100

    def test_large_message_handling(self):
        """Test handling of large messages."""
        tracker = ProgressTracker(100)
        
        large_message = "A" * 10000  # 10k character message
        
        callback_calls = []
        def test_callback(current, total, message):
            callback_calls.append(message)
        
        tracker.add_callback(test_callback)
        
        # Should handle large message without issues
        tracker.update(step=50, message=large_message)
        
        assert len(callback_calls) == 1
        assert len(callback_calls[0]) == 10000

    def test_many_backends_performance(self):
        """Test performance with many backends."""
        tracker = ProgressTracker(100)
        
        # Add many callback backends
        for i in range(50):
            def callback(current, total, message):
                pass
            tracker.add_callback(callback)
        
        start_time = time.time()
        
        # Update progress multiple times
        for i in range(50):
            tracker.update(step=i)
        
        end_time = time.time()
        
        # Should complete in reasonable time even with many backends
        assert end_time - start_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])