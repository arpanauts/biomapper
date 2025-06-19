"""
Unit tests for the ProgressReporter class.

Tests cover all public methods and properties to ensure
reliable progress reporting functionality.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to sys.path to import modules directly
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the module directly to avoid loading the full biomapper package
from biomapper.core.engine_components.progress_reporter import ProgressReporter


class TestProgressReporter:
    """Test suite for ProgressReporter class."""
    
    def test_initialization_with_callback(self):
        """Test ProgressReporter initialization with an initial callback."""
        # Create a mock callback
        mock_callback = Mock()
        
        # Initialize with callback
        reporter = ProgressReporter(progress_callback=mock_callback)
        
        # Verify callback was added
        assert reporter.has_callbacks is True
        
        # Test that callback is called when reporting
        test_data = {"status": "test"}
        reporter.report(test_data)
        mock_callback.assert_called_once_with(test_data)
    
    def test_initialization_without_callback(self):
        """Test ProgressReporter initialization without an initial callback."""
        # Initialize without callback
        reporter = ProgressReporter()
        
        # Verify no callbacks are registered
        assert reporter.has_callbacks is False
    
    def test_add_callback(self):
        """Test adding callbacks to ProgressReporter."""
        reporter = ProgressReporter()
        mock_callback = Mock()
        
        # Initially no callbacks
        assert reporter.has_callbacks is False
        
        # Add callback
        reporter.add_callback(mock_callback)
        
        # Verify callback was added
        assert reporter.has_callbacks is True
        
        # Test callback is called
        test_data = {"progress": 50}
        reporter.report(test_data)
        mock_callback.assert_called_once_with(test_data)
    
    def test_add_duplicate_callback(self):
        """Test that adding the same callback twice doesn't create duplicates."""
        reporter = ProgressReporter()
        mock_callback = Mock()
        
        # Add callback twice
        reporter.add_callback(mock_callback)
        reporter.add_callback(mock_callback)
        
        # Report progress
        test_data = {"status": "running"}
        reporter.report(test_data)
        
        # Callback should only be called once
        mock_callback.assert_called_once_with(test_data)
    
    def test_remove_callback(self):
        """Test removing callbacks from ProgressReporter."""
        reporter = ProgressReporter()
        mock_callback = Mock()
        
        # Add callback
        reporter.add_callback(mock_callback)
        assert reporter.has_callbacks is True
        
        # Remove callback
        reporter.remove_callback(mock_callback)
        assert reporter.has_callbacks is False
        
        # Verify callback is not called after removal
        reporter.report({"test": "data"})
        mock_callback.assert_not_called()
    
    def test_remove_nonexistent_callback(self):
        """Test removing a callback that was never added."""
        reporter = ProgressReporter()
        mock_callback1 = Mock()
        mock_callback2 = Mock()
        
        # Add only callback1
        reporter.add_callback(mock_callback1)
        
        # Try to remove callback2 (which was never added)
        # This should not raise an error
        reporter.remove_callback(mock_callback2)
        
        # callback1 should still be registered
        assert reporter.has_callbacks is True
        reporter.report({"test": "data"})
        mock_callback1.assert_called_once()
    
    def test_report_multiple_callbacks(self):
        """Test reporting to multiple registered callbacks."""
        reporter = ProgressReporter()
        
        # Create multiple mock callbacks
        mock_callback1 = Mock()
        mock_callback2 = Mock()
        mock_callback3 = Mock()
        
        # Add all callbacks
        reporter.add_callback(mock_callback1)
        reporter.add_callback(mock_callback2)
        reporter.add_callback(mock_callback3)
        
        # Report progress
        test_data = {
            "current": 10,
            "total": 100,
            "message": "Processing..."
        }
        reporter.report(test_data)
        
        # Verify all callbacks were called with the correct data
        mock_callback1.assert_called_once_with(test_data)
        mock_callback2.assert_called_once_with(test_data)
        mock_callback3.assert_called_once_with(test_data)
    
    def test_report_with_failing_callback(self):
        """Test that a failing callback doesn't prevent others from being called."""
        reporter = ProgressReporter()
        
        # Create callbacks: one that fails, two that work
        failing_callback = Mock(side_effect=RuntimeError("Callback failed!"))
        working_callback1 = Mock()
        working_callback2 = Mock()
        
        # Add all callbacks
        reporter.add_callback(working_callback1)
        reporter.add_callback(failing_callback)
        reporter.add_callback(working_callback2)
        
        # Report progress (with warning logging suppressed)
        test_data = {"status": "testing"}
        with patch.object(reporter.logger, 'warning'):
            reporter.report(test_data)
        
        # Verify working callbacks were still called
        working_callback1.assert_called_once_with(test_data)
        working_callback2.assert_called_once_with(test_data)
        failing_callback.assert_called_once_with(test_data)
    
    def test_clear_callbacks(self):
        """Test clearing all callbacks."""
        reporter = ProgressReporter()
        
        # Add multiple callbacks
        mock_callback1 = Mock()
        mock_callback2 = Mock()
        mock_callback3 = Mock()
        
        reporter.add_callback(mock_callback1)
        reporter.add_callback(mock_callback2)
        reporter.add_callback(mock_callback3)
        
        # Verify callbacks are registered
        assert reporter.has_callbacks is True
        
        # Clear all callbacks
        reporter.clear_callbacks()
        
        # Verify no callbacks remain
        assert reporter.has_callbacks is False
        
        # Verify callbacks are not called after clearing
        reporter.report({"test": "data"})
        mock_callback1.assert_not_called()
        mock_callback2.assert_not_called()
        mock_callback3.assert_not_called()
    
    def test_has_callbacks_property(self):
        """Test the has_callbacks property."""
        reporter = ProgressReporter()
        
        # Initially no callbacks
        assert reporter.has_callbacks is False
        
        # Add a callback
        mock_callback = Mock()
        reporter.add_callback(mock_callback)
        assert reporter.has_callbacks is True
        
        # Remove the callback
        reporter.remove_callback(mock_callback)
        assert reporter.has_callbacks is False
    
    def test_add_none_callback(self):
        """Test that adding None as a callback is handled gracefully."""
        reporter = ProgressReporter()
        
        # Add None - should not be added
        reporter.add_callback(None)
        
        # Verify no callbacks were added
        assert reporter.has_callbacks is False
    
    def test_callback_exception_logging(self):
        """Test that exceptions in callbacks are logged properly."""
        reporter = ProgressReporter()
        
        # Create a failing callback
        error_message = "Test exception"
        failing_callback = Mock(side_effect=Exception(error_message))
        
        # Add the callback
        reporter.add_callback(failing_callback)
        
        # Mock the logger to verify warning is called
        with patch.object(reporter.logger, 'warning') as mock_warning:
            reporter.report({"test": "data"})
            
            # Verify warning was logged with the exception message
            mock_warning.assert_called_once()
            warning_message = mock_warning.call_args[0][0]
            assert "Progress callback failed:" in warning_message
            assert error_message in warning_message