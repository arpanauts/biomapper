"""Tests for client progress tracking."""

import pytest
import time
from unittest.mock import Mock, patch

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


class TestProgressTrackerTqdm:
    """Test ProgressTracker tqdm integration."""

    @patch('tqdm.tqdm')
    def test_add_tqdm_success(self, mock_tqdm):
        """Test successful tqdm addition."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar
        
        tracker = ProgressTracker(100, "Processing")
        result = tracker.add_tqdm()
        
        assert result is tracker  # Method chaining
        mock_tqdm.assert_called_once_with(total=100, desc="Processing")
        assert len(tracker.backends) == 1
        assert tracker.backends[0][0] == "tqdm"
        assert tracker.backends[0][1] is mock_progress_bar

    def test_add_tqdm_import_error(self):
        """Test tqdm addition when tqdm is not available."""
        with patch('tqdm.tqdm', side_effect=ImportError):
            tracker = ProgressTracker(100)
            result = tracker.add_tqdm()
            
            assert result is tracker
            assert len(tracker.backends) == 0  # No backend added

    @patch('tqdm.tqdm')
    def test_tqdm_update_integration(self, mock_tqdm):
        """Test tqdm update integration."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar
        
        tracker = ProgressTracker(100)
        tracker.add_tqdm()
        
        # Update progress
        tracker.update(step=25, message="Processing...")
        
        # Verify tqdm was updated
        assert mock_progress_bar.n == 25
        mock_progress_bar.refresh.assert_called_once()
        mock_progress_bar.set_postfix_str.assert_called_once_with("Processing...")

    @patch('tqdm.tqdm')
    def test_tqdm_update_without_message(self, mock_tqdm):
        """Test tqdm update without message."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar
        
        tracker = ProgressTracker(100)
        tracker.add_tqdm()
        
        # Update without message
        tracker.update(step=50)
        
        assert mock_progress_bar.n == 50
        mock_progress_bar.refresh.assert_called_once()
        mock_progress_bar.set_postfix_str.assert_not_called()

    @patch('tqdm.tqdm')
    def test_tqdm_close_integration(self, mock_tqdm):
        """Test tqdm close integration."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar
        
        tracker = ProgressTracker(100)
        tracker.add_tqdm()
        tracker.close()
        
        mock_progress_bar.close.assert_called_once()


class TestProgressTrackerRich:
    """Test ProgressTracker rich integration."""

    @patch('rich.progress.Progress')
    def test_add_rich_success(self, mock_progress_class):
        """Test successful rich addition."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = "task-id-123"
        
        tracker = ProgressTracker(100, "Processing")
        result = tracker.add_rich()
        
        assert result is tracker  # Method chaining
        mock_progress_class.assert_called_once()
        mock_progress.start.assert_called_once()
        mock_progress.add_task.assert_called_once_with("Processing", total=100)
        
        assert len(tracker.backends) == 1
        assert tracker.backends[0][0] == "rich"
        assert tracker.backends[0][1] == (mock_progress, "task-id-123")

    def test_add_rich_import_error(self):
        """Test rich addition when rich is not available."""
        with patch('rich.progress.Progress', side_effect=ImportError):
            tracker = ProgressTracker(100)
            result = tracker.add_rich()
            
            assert result is tracker
            assert len(tracker.backends) == 0  # No backend added

    @patch('rich.progress.Progress')
    def test_rich_update_integration(self, mock_progress_class):
        """Test rich update integration."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = "task-id-123"
        
        tracker = ProgressTracker(100, "Processing")
        tracker.add_rich()
        
        # Update progress
        tracker.update(step=30, message="Loading data...")
        
        # Verify rich was updated
        mock_progress.update.assert_called_once_with(
            "task-id-123",
            completed=30,
            description="Processing: Loading data..."
        )

    @patch('rich.progress.Progress')
    def test_rich_update_without_message(self, mock_progress_class):
        """Test rich update without message."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = "task-id-123"
        
        tracker = ProgressTracker(100, "Processing")
        tracker.add_rich()
        
        # Update without message
        tracker.update(step=60)
        
        mock_progress.update.assert_called_once_with(
            "task-id-123",
            completed=60,
            description="Processing"
        )

    @patch('rich.progress.Progress')
    def test_rich_close_integration(self, mock_progress_class):
        """Test rich close integration."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = "task-id-123"
        
        tracker = ProgressTracker(100)
        tracker.add_rich()
        tracker.close()
        
        mock_progress.stop.assert_called_once()


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


class TestProgressTrackerJupyter:
    """Test ProgressTracker Jupyter integration."""

    @patch('IPython.display.display')
    @patch('ipywidgets.HBox')
    @patch('ipywidgets.IntProgress')
    @patch('ipywidgets.Label')
    def test_add_jupyter_success(self, mock_label, mock_int_progress, mock_hbox, mock_display):
        """Test successful Jupyter widget addition."""
        mock_progress = Mock()
        mock_label_progress = Mock()
        mock_label_status = Mock()
        mock_widget = Mock()
        
        mock_int_progress.return_value = mock_progress
        mock_label.side_effect = [mock_label_progress, mock_label_status]
        mock_hbox.return_value = mock_widget
        
        tracker = ProgressTracker(100, "Processing")
        result = tracker.add_jupyter()
        
        assert result is tracker  # Method chaining
        
        # Verify widget creation
        mock_int_progress.assert_called_once_with(
            value=0,
            min=0,
            max=100,
            description="Processing",
            bar_style="info",
            orientation="horizontal"
        )
        
        assert mock_label.call_count == 2
        mock_hbox.assert_called_once_with([mock_progress, mock_label_progress, mock_label_status])
        mock_display.assert_called_once_with(mock_widget)
        
        assert len(tracker.backends) == 1
        assert tracker.backends[0][0] == "jupyter"
        assert tracker.backends[0][1] == (mock_progress, mock_label_progress, mock_label_status)

    def test_add_jupyter_import_error(self):
        """Test Jupyter addition when dependencies are not available."""
        with patch('IPython.display.display', side_effect=ImportError):
            tracker = ProgressTracker(100)
            result = tracker.add_jupyter()
            
            assert result is tracker
            assert len(tracker.backends) == 0  # No backend added

    @patch('IPython.display.display')
    @patch('ipywidgets.HBox')
    @patch('ipywidgets.IntProgress')
    @patch('ipywidgets.Label')
    def test_jupyter_update_integration(self, mock_label, mock_int_progress, mock_hbox, mock_display):
        """Test Jupyter widget update integration."""
        mock_progress = Mock()
        mock_label_progress = Mock()
        mock_label_status = Mock()
        
        mock_int_progress.return_value = mock_progress
        mock_label.side_effect = [mock_label_progress, mock_label_status]
        
        tracker = ProgressTracker(100, "Processing")
        tracker.add_jupyter()
        
        # Update progress
        tracker.update(step=40, message="Loading data...")
        
        # Verify widget updates
        assert mock_progress.value == 40
        assert mock_label_progress.value == "40/100"
        assert mock_label_status.value == "Loading data..."

    @patch('IPython.display.display')
    @patch('ipywidgets.HBox')
    @patch('ipywidgets.IntProgress')
    @patch('ipywidgets.Label')
    def test_jupyter_update_without_message(self, mock_label, mock_int_progress, mock_hbox, mock_display):
        """Test Jupyter widget update without message."""
        mock_progress = Mock()
        mock_label_progress = Mock()
        mock_label_status = Mock()
        
        mock_int_progress.return_value = mock_progress
        mock_label.side_effect = [mock_label_progress, mock_label_status]
        
        tracker = ProgressTracker(100, "Processing")
        tracker.add_jupyter()
        
        # Update without message
        tracker.update(step=60)
        
        # Status should not be updated when no message provided
        assert mock_progress.value == 60
        assert mock_label_progress.value == "60/100"
        # mock_label_status.value should not be set


class TestProgressTrackerMultipleBackends:
    """Test ProgressTracker with multiple backends."""

    def test_multiple_backends_integration(self):
        """Test tracker with multiple backends."""
        tracker = ProgressTracker(100, "Processing")
        
        # Add callback backend
        callback_calls = []
        def test_callback(current, total, message):
            callback_calls.append((current, total, message))
        
        tracker.add_callback(test_callback)
        
        # Add mock tqdm backend
        with patch('tqdm.tqdm') as mock_tqdm:
            mock_progress_bar = Mock()
            mock_tqdm.return_value = mock_progress_bar
            tracker.add_tqdm()
            
            # Update progress
            tracker.update(step=50, message="Halfway")
            
            # Both backends should be updated
            assert len(callback_calls) == 1
            assert callback_calls[0] == (50, 100, "Halfway")
            
            assert mock_progress_bar.n == 50
            mock_progress_bar.refresh.assert_called_once()
            mock_progress_bar.set_postfix_str.assert_called_once_with("Halfway")

    def test_backend_exception_isolation(self):
        """Test that exceptions in one backend don't affect others."""
        tracker = ProgressTracker(100)
        
        # Add failing tqdm backend
        with patch('tqdm.tqdm') as mock_tqdm:
            mock_progress_bar = Mock()
            mock_progress_bar.refresh.side_effect = Exception("tqdm failed")
            mock_tqdm.return_value = mock_progress_bar
            tracker.add_tqdm()
            
            # Add working callback backend
            callback_calls = []
            def test_callback(current, total, message):
                callback_calls.append((current, total, message))
            
            tracker.add_callback(test_callback)
            
            # Update should not raise exception
            tracker.update(step=25)
            
            # Working backend should still function
            assert len(callback_calls) == 1
            assert callback_calls[0] == (25, 100, "Processing")


class TestProgressTrackerDescriptionManagement:
    """Test ProgressTracker description management."""

    def test_set_description(self):
        """Test setting description."""
        tracker = ProgressTracker(100, "Initial description")
        
        tracker.set_description("New description")
        
        assert tracker.description == "New description"

    @patch('tqdm.tqdm')
    def test_set_description_updates_tqdm(self, mock_tqdm):
        """Test that setting description updates tqdm backend."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar
        
        tracker = ProgressTracker(100, "Initial")
        tracker.add_tqdm()
        
        tracker.set_description("Updated description")
        
        mock_progress_bar.set_description.assert_called_once_with("Updated description")

    @patch('rich.progress.Progress')
    def test_set_description_updates_rich(self, mock_progress_class):
        """Test that setting description updates rich backend."""
        mock_progress = Mock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = "task-id"
        
        tracker = ProgressTracker(100, "Initial")
        tracker.add_rich()
        
        tracker.set_description("Updated description")
        
        mock_progress.update.assert_called_once_with("task-id", description="Updated description")

    def test_set_description_with_backend_exceptions(self):
        """Test that backend exceptions in set_description are handled."""
        with patch('tqdm.tqdm') as mock_tqdm:
            mock_progress_bar = Mock()
            mock_progress_bar.set_description.side_effect = Exception("Update failed")
            mock_tqdm.return_value = mock_progress_bar
            
            tracker = ProgressTracker(100, "Initial")
            tracker.add_tqdm()
            
            # Should not raise exception
            tracker.set_description("New description")
            
            # Description should still be updated internally
            assert tracker.description == "New description"


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

    def test_context_manager_with_backends(self):
        """Test context manager with backends."""
        with patch('tqdm.tqdm') as mock_tqdm:
            mock_progress_bar = Mock()
            mock_tqdm.return_value = mock_progress_bar
            
            tracker = ProgressTracker(100)
            tracker.add_tqdm()
            
            with tracker:
                tracker.update(step=50)
                assert mock_progress_bar.n == 50
            
            # Backend should be closed
            mock_progress_bar.close.assert_called_once()

    def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly."""
        with patch('tqdm.tqdm') as mock_tqdm:
            mock_progress_bar = Mock()
            mock_tqdm.return_value = mock_progress_bar
            
            tracker = ProgressTracker(100)
            tracker.add_tqdm()
            
            try:
                with tracker:
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # Backend should still be closed despite exception
            mock_progress_bar.close.assert_called_once()
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

    @patch('tqdm.tqdm')
    @patch('rich.progress.Progress')
    def test_close_all_backends(self, mock_progress_class, mock_tqdm):
        """Test that close properly closes all backends."""
        # Setup tqdm backend
        mock_tqdm_bar = Mock()
        mock_tqdm.return_value = mock_tqdm_bar
        
        # Setup rich backend
        mock_rich_progress = Mock()
        mock_progress_class.return_value = mock_rich_progress
        mock_rich_progress.add_task.return_value = "task-id"
        
        tracker = ProgressTracker(100)
        tracker.add_tqdm()
        tracker.add_rich()
        
        tracker.close()
        
        # Both backends should be closed
        mock_tqdm_bar.close.assert_called_once()
        mock_rich_progress.stop.assert_called_once()

    def test_close_with_backend_exceptions(self):
        """Test that close handles backend exceptions."""
        with patch('tqdm.tqdm') as mock_tqdm:
            mock_progress_bar = Mock()
            mock_progress_bar.close.side_effect = Exception("Close failed")
            mock_tqdm.return_value = mock_progress_bar
            
            tracker = ProgressTracker(100)
            tracker.add_tqdm()
            
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


class TestProgressTrackerEdgeCases:
    """Test ProgressTracker edge cases."""

    def test_zero_total_steps(self):
        """Test tracker with zero total steps."""
        tracker = ProgressTracker(0)
        
        assert tracker.total_steps == 0
        assert tracker.percentage == 100.0
        
        # Updates should not crash, but step is clamped to total_steps (0)
        tracker.update(step=1)
        assert tracker.current_step == 0  # Clamped to total_steps
        assert tracker.percentage == 100.0

    def test_negative_total_steps(self):
        """Test tracker with negative total steps."""
        tracker = ProgressTracker(-10)
        
        assert tracker.total_steps == -10
        
        # Should handle gracefully - step is clamped to min(step, total_steps)
        tracker.update(step=5)
        assert tracker.current_step == -10  # Clamped to total_steps (-10)

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])