"""
Logging utilities for biomapper actions.

This module provides consistent logging functionality across all actions
with appropriate formatting and context.

Available Functions (when implemented):
    action_logger: Get configured logger for an action
    log_progress: Progress logging for long operations
    log_statistics: Standardized statistics logging

Logging Features:
    - Action-specific log formatting
    - Progress tracking for batch operations
    - Statistics logging (input/output counts, success rates)
    - Error logging with context

Example Usage:
    from actions.utils.logging import action_logger
    
    logger = action_logger(self.__class__.__name__)
    logger.info(f"Processing {len(data)} records")
    logger.debug(f"First 5 records: {data[:5]}")

Development:
    Provide consistent logging patterns across all actions.
    Include performance metrics and debugging information.
"""

# Import logging utilities
# from .action_logger import action_logger, log_progress, log_statistics  # To be implemented

__all__ = []  # Functions will be exported when implemented
