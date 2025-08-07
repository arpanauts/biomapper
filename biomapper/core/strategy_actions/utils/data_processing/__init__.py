"""
Data processing utilities for biomapper actions.

This module contains utilities for DataFrame operations, filtering,
chunking, and other common data processing tasks.

Available Functions (when implemented):
    chunk_processor: Process DataFrames in memory-efficient chunks
    filter_dataset: Generic dataset filtering (implements FILTER_DATASET action)
    validate_dataframe: DataFrame validation utilities

Memory Management:
    - Chunking for datasets > 50k rows
    - Progress tracking for long operations
    - Memory usage monitoring

Example Usage:
    from biomapper.core.strategy_actions.utils.data_processing import ChunkProcessor
    
    processor = ChunkProcessor(chunk_size=10000)
    for chunk in processor.process_dataframe(large_df):
        # Process chunk efficiently

Development:
    Implement memory-efficient processing for large biological datasets.
    Provide progress tracking and error recovery.
"""

# Import data processing utilities
from .chunk_processor import (
    ChunkProcessorAction,
    ChunkProcessorParams,
    ChunkProcessorResult,
    ChunkingStrategy,
    ParallelProcessor,
    ProgressMonitor,
    ResultAggregator,
    CheckpointManager,
)
from .filter_dataset import FilterDatasetAction
# from .data_validators import validate_dataframe # To be implemented

__all__ = [
    "ChunkProcessorAction",
    "ChunkProcessorParams",
    "ChunkProcessorResult",
    "ChunkingStrategy",
    "ParallelProcessor",
    "ProgressMonitor",
    "ResultAggregator",
    "CheckpointManager",
    "FilterDatasetAction",
]
