"""Tests for progress tracking utilities."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from biomapper_client.progress import NoOpProgressTracker, ProgressTracker


class TestProgressTracker:
    """Test ProgressTracker class."""

    def test_init(self):
        """Test initialization."""
        tracker = ProgressTracker(100, "Testing")

        assert tracker.total_steps == 100
        assert tracker.current_step == 0
        assert tracker.description == "Testing"
        assert tracker.backends == []
        assert tracker._is_closed is False

    def test_add_callback(self):
        """Test adding callback backend."""
        tracker = ProgressTracker(100)
        callback = Mock()

        tracker.add_callback(callback)

        assert len(tracker.backends) == 1
        assert tracker.backends[0] == ("callback", callback)

    def test_update_with_callback(self):
        """Test update with callback."""
        tracker = ProgressTracker(100, "Testing")
        callback = Mock()
        tracker.add_callback(callback)

        tracker.update("Step 1")

        callback.assert_called_once_with(1, 100, "Step 1")

    def test_update_with_step(self):
        """Test update with absolute step."""
        tracker = ProgressTracker(100)

        tracker.update(step=50)
        assert tracker.current_step == 50

        tracker.update(step=75)
        assert tracker.current_step == 75

    def test_update_with_increment(self):
        """Test update with increment."""
        tracker = ProgressTracker(100)

        tracker.update(increment=5)
        assert tracker.current_step == 5

        tracker.update(increment=10)
        assert tracker.current_step == 15

    def test_update_caps_at_total(self):
        """Test that updates don't exceed total steps."""
        tracker = ProgressTracker(100)

        tracker.update(step=150)
        assert tracker.current_step == 100

        tracker.current_step = 95
        tracker.update(increment=10)
        assert tracker.current_step == 100

    def test_percentage(self):
        """Test percentage calculation."""
        tracker = ProgressTracker(100)

        assert tracker.percentage == 0.0

        tracker.update(step=25)
        assert tracker.percentage == 25.0

        tracker.update(step=100)
        assert tracker.percentage == 100.0

    def test_percentage_zero_total(self):
        """Test percentage with zero total steps."""
        tracker = ProgressTracker(0)
        assert tracker.percentage == 100.0

    def test_set_description(self):
        """Test setting description."""
        tracker = ProgressTracker(100, "Initial")

        tracker.set_description("Updated")
        assert tracker.description == "Updated"

    def test_context_manager(self):
        """Test context manager usage."""
        tracker = ProgressTracker(100)

        with tracker as t:
            assert t == tracker
            assert not tracker._is_closed

        assert tracker._is_closed

    def test_close_idempotent(self):
        """Test that close is idempotent."""
        tracker = ProgressTracker(100)

        tracker.close()
        assert tracker._is_closed

        # Should not raise error
        tracker.close()
        assert tracker._is_closed

    def test_update_after_close(self):
        """Test that updates are ignored after close."""
        tracker = ProgressTracker(100)
        callback = Mock()
        tracker.add_callback(callback)

        tracker.close()
        tracker.update("Should be ignored")

        # Callback should not be called
        callback.assert_not_called()

    @patch("tqdm.tqdm")
    def test_add_tqdm(self, mock_tqdm_class):
        """Test adding tqdm backend."""
        mock_tqdm = Mock()
        mock_tqdm_class.return_value = mock_tqdm

        tracker = ProgressTracker(100, "Testing")
        tracker.add_tqdm(ncols=80)

        mock_tqdm_class.assert_called_once_with(
            total=100,
            desc="Testing",
            ncols=80,
        )
        assert len(tracker.backends) == 1
        assert tracker.backends[0][0] == "tqdm"

    @patch("tqdm.tqdm")
    def test_update_with_tqdm(self, mock_tqdm_class):
        """Test update with tqdm backend."""
        mock_pbar = Mock()
        mock_tqdm_class.return_value = mock_pbar

        tracker = ProgressTracker(100)
        tracker.add_tqdm()

        tracker.update("Processing", step=50)

        assert mock_pbar.n == 50
        mock_pbar.refresh.assert_called_once()
        mock_pbar.set_postfix_str.assert_called_once_with("Processing")

    @patch("tqdm.tqdm")
    def test_close_with_tqdm(self, mock_tqdm_class):
        """Test closing with tqdm backend."""
        mock_pbar = Mock()
        mock_tqdm_class.return_value = mock_pbar

        tracker = ProgressTracker(100)
        tracker.add_tqdm()

        tracker.close()

        mock_pbar.close.assert_called_once()

    @patch("rich.progress.Progress")
    def test_add_rich(self, mock_progress_class):
        """Test adding rich backend."""
        mock_progress = Mock()
        mock_task_id = "task-123"
        mock_progress.add_task.return_value = mock_task_id
        mock_progress_class.return_value = mock_progress

        tracker = ProgressTracker(100, "Testing")
        tracker.add_rich()

        mock_progress.start.assert_called_once()
        mock_progress.add_task.assert_called_once_with("Testing", total=100)
        assert len(tracker.backends) == 1
        assert tracker.backends[0][0] == "rich"

    @patch("rich.progress.Progress")
    def test_update_with_rich(self, mock_progress_class):
        """Test update with rich backend."""
        mock_progress = Mock()
        mock_task_id = "task-123"
        mock_progress.add_task.return_value = mock_task_id
        mock_progress_class.return_value = mock_progress

        tracker = ProgressTracker(100, "Testing")
        tracker.add_rich()

        tracker.update("Processing", step=50)

        mock_progress.update.assert_called_once_with(
            mock_task_id,
            completed=50,
            description="Testing: Processing",
        )

    @patch("IPython.display.display")
    @patch("ipywidgets.HBox")
    @patch("ipywidgets.IntProgress")
    @patch("ipywidgets.Label")
    def test_add_jupyter(self, mock_label, mock_progress, mock_hbox, mock_display):
        """Test adding Jupyter backend."""
        mock_progress_widget = Mock()
        mock_label_widget = Mock()
        mock_status_widget = Mock()
        mock_box = Mock()

        mock_progress.return_value = mock_progress_widget
        mock_label.side_effect = [mock_label_widget, mock_status_widget]
        mock_hbox.return_value = mock_box

        tracker = ProgressTracker(100, "Testing")
        tracker.add_jupyter()

        mock_progress.assert_called_once()
        assert mock_label.call_count == 2
        mock_hbox.assert_called_once()
        mock_display.assert_called_once_with(mock_box)

        assert len(tracker.backends) == 1
        assert tracker.backends[0][0] == "jupyter"

    def test_add_tqdm_import_error(self):
        """Test adding tqdm when not installed."""
        # Patch the import inside the method
        with patch("builtins.__import__", side_effect=ImportError):
            tracker = ProgressTracker(100)
            result = tracker.add_tqdm()

            # Should not raise error, just skip
            assert result == tracker
            assert len(tracker.backends) == 0

    def test_backend_error_handling(self):
        """Test that backend errors are silently ignored."""
        tracker = ProgressTracker(100)

        # Add callback that raises error
        def bad_callback(*args):
            raise RuntimeError("Callback error")

        tracker.add_callback(bad_callback)

        # Should not raise error
        tracker.update("Step 1")
        assert tracker.current_step == 1


class TestNoOpProgressTracker:
    """Test NoOpProgressTracker class."""

    def test_all_methods(self):
        """Test that all methods work and do nothing."""
        tracker = NoOpProgressTracker(100, "Testing")

        # All methods should work without error
        tracker.add_tqdm()
        tracker.add_rich()
        tracker.add_callback(Mock())
        tracker.add_jupyter()
        tracker.update("Step 1", step=50, increment=10)
        tracker.set_description("New description")
        tracker.close()

        # Percentage should always be 0
        assert tracker.percentage == 0.0

    def test_context_manager(self):
        """Test context manager usage."""
        tracker = NoOpProgressTracker()

        with tracker as t:
            assert t == tracker
            # Should work without error

    def test_chaining(self):
        """Test method chaining."""
        tracker = NoOpProgressTracker()

        result = tracker.add_tqdm().add_rich().add_callback(Mock())
        assert result == tracker