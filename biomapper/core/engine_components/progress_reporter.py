"""
Progress reporting functionality for BioMapper.

This module provides the ProgressReporter class which handles
the responsibility of reporting progress updates to registered callbacks.
"""

from typing import Any, Callable, Dict, List, Optional
import logging


class ProgressReporter:
    """
    Handles progress reporting to registered callbacks.

    This class encapsulates the logic for managing and notifying progress
    callbacks, providing a clean separation of concerns from the main
    mapping execution logic.
    """

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize the ProgressReporter.

        Args:
            progress_callback: Optional initial callback function to register
        """
        self._progress_callbacks: List[Callable] = []
        self.logger = logging.getLogger(__name__)

        # Register initial callback if provided
        if progress_callback:
            self.add_callback(progress_callback)

    def add_callback(self, callback: Callable):
        """
        Register a new progress callback.

        Args:
            callback: Function to call with progress updates
        """
        if callback and callback not in self._progress_callbacks:
            self._progress_callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """
        Remove a registered callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def report(self, progress_data: Dict[str, Any]):
        """
        Report progress to all registered callbacks.

        Args:
            progress_data: Dictionary containing progress information
        """
        for callback in self._progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")

    def clear_callbacks(self):
        """Clear all registered callbacks."""
        self._progress_callbacks.clear()

    @property
    def has_callbacks(self) -> bool:
        """Check if any callbacks are registered."""
        return bool(self._progress_callbacks)
