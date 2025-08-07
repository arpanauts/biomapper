"""
CHUNK_PROCESSOR Action - Performance infrastructure for memory-efficient processing.

This action provides a general-purpose wrapper that automatically chunks large datasets
for memory-efficient processing. It can wrap ANY action to enable processing of datasets
that would otherwise exceed memory limits.

Features:
- Dynamic chunking based on memory constraints or row count
- Parallel and sequential processing modes
- Progress tracking with memory monitoring
- Checkpointing for long-running processes
- Multiple result aggregation methods
- Comprehensive error handling and retry logic
- Memory optimization utilities
"""

import gc
import time
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal, Iterator, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor
import logging

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
import psutil  # type: ignore

from biomapper.core.strategy_actions.registry import register_action, ACTION_REGISTRY

logger = logging.getLogger(__name__)


class ChunkProcessorParams(BaseModel):
    """Parameters for chunk processing wrapper."""

    # Target action configuration
    target_action: str = Field(..., description="Action to wrap with chunking")
    target_params: Dict[str, Any] = Field(
        ..., description="Parameters for target action"
    )

    # Input/Output
    input_key: str = Field(..., description="Input dataset key")
    output_key: str = Field(..., description="Output dataset key")

    # Chunking configuration
    chunk_size: Optional[int] = Field(10000, description="Rows per chunk")
    chunk_by_memory: bool = Field(
        False, description="Chunk by memory usage instead of rows"
    )
    max_memory_mb: Optional[int] = Field(500, description="Max memory per chunk in MB")

    # Processing configuration
    processing_mode: Literal["sequential", "parallel", "adaptive"] = Field(
        "adaptive", description="How to process chunks"
    )
    max_workers: Optional[int] = Field(4, description="Max parallel workers")

    # Chunk overlap (for context-dependent actions)
    overlap_rows: Optional[int] = Field(0, description="Rows to overlap between chunks")
    overlap_strategy: Literal["none", "sliding", "context"] = Field(
        "none", description="Overlap strategy for context preservation"
    )

    # Aggregation configuration
    aggregation_method: Literal["concat", "merge", "custom"] = Field(
        "concat", description="How to combine chunk results"
    )
    merge_columns: Optional[List[str]] = Field(None, description="Columns to merge on")
    dedup_columns: Optional[List[str]] = Field(
        None, description="Columns for deduplication"
    )

    # Progress tracking
    show_progress: bool = Field(True, description="Display progress bar")
    log_chunk_stats: bool = Field(True, description="Log statistics per chunk")
    checkpoint_enabled: bool = Field(False, description="Enable checkpointing")
    checkpoint_dir: Optional[str] = Field(None, description="Directory for checkpoints")

    # Error handling
    error_strategy: Literal["fail", "skip", "retry"] = Field(
        "retry", description="How to handle chunk failures"
    )
    max_retries: int = Field(3, description="Maximum retries per chunk")
    retry_delay: float = Field(1.0, description="Delay between retries (seconds)")

    # Memory optimization
    gc_after_chunk: bool = Field(
        True, description="Force garbage collection after each chunk"
    )
    optimize_dtypes: bool = Field(
        True, description="Optimize DataFrame dtypes for memory"
    )
    use_categories: bool = Field(
        True, description="Convert strings to categories where possible"
    )


class ChunkProcessorResult(BaseModel):
    """Result of chunk processing."""

    success: bool
    total_rows_processed: int
    chunks_processed: int
    chunks_failed: int
    processing_time_seconds: float
    peak_memory_mb: float
    average_chunk_time: float
    chunk_statistics: List[Dict[str, Any]]
    aggregation_method_used: str
    warnings: Optional[List[str]] = None
    error_chunks: Optional[List[int]] = None


class ChunkingStrategy:
    """Dynamic chunking based on size or memory constraints."""

    def calculate_optimal_chunk_size(self, df: pd.DataFrame, max_memory_mb: int) -> int:
        """Calculate chunk size based on memory constraints."""

        if len(df) == 0:
            return 10000  # Default for empty DataFrame

        # Estimate memory usage per row
        memory_usage = df.memory_usage(deep=True).sum()
        rows = len(df)

        bytes_per_row = memory_usage / rows
        mb_per_row = bytes_per_row / (1024 * 1024)

        # Calculate rows that fit in memory limit
        # Leave 20% buffer for processing overhead
        buffer = 0.8
        optimal_rows = int((max_memory_mb * buffer) / mb_per_row)

        # Ensure reasonable bounds
        optimal_rows = max(100, min(optimal_rows, 100000))

        return optimal_rows

    def create_chunks(
        self, df: pd.DataFrame, chunk_size: int, overlap_rows: int = 0
    ) -> Iterator[Tuple[int, pd.DataFrame]]:
        """Create DataFrame chunks with optional overlap."""

        total_rows = len(df)

        if total_rows == 0:
            return  # No chunks for empty DataFrame

        if overlap_rows > 0:
            # Sliding window chunking
            for start_idx in range(0, total_rows, chunk_size - overlap_rows):
                end_idx = min(start_idx + chunk_size, total_rows)
                chunk = df.iloc[start_idx:end_idx].copy()
                yield start_idx, chunk

                if end_idx >= total_rows:
                    break
        else:
            # Simple chunking
            for start_idx in range(0, total_rows, chunk_size):
                end_idx = min(start_idx + chunk_size, total_rows)
                chunk = df.iloc[start_idx:end_idx].copy()
                yield start_idx, chunk

    def optimize_dataframe_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage."""

        if len(df) == 0:
            return df.copy()

        optimized = df.copy()

        for col in optimized.columns:
            col_type = optimized[col].dtype

            # Downcast numeric types
            if col_type != "object":
                c_min = optimized[col].min()
                c_max = optimized[col].max()

                if str(col_type)[:3] == "int":
                    # Integer optimization
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        optimized[col] = optimized[col].astype(np.int8)
                    elif (
                        c_min > np.iinfo(np.int16).min
                        and c_max < np.iinfo(np.int16).max
                    ):
                        optimized[col] = optimized[col].astype(np.int16)
                    elif (
                        c_min > np.iinfo(np.int32).min
                        and c_max < np.iinfo(np.int32).max
                    ):
                        optimized[col] = optimized[col].astype(np.int32)

                elif str(col_type)[:5] == "float":
                    # Float optimization
                    if (
                        c_min > np.finfo(np.float32).min
                        and c_max < np.finfo(np.float32).max
                    ):
                        optimized[col] = optimized[col].astype(np.float32)

            else:
                # Convert repetitive strings to categories
                num_unique = optimized[col].nunique()
                num_total = len(optimized[col])

                if num_unique / num_total < 0.5:  # Less than 50% unique
                    optimized[col] = optimized[col].astype("category")

        return optimized


class ParallelProcessor:
    """Handle parallel chunk processing."""

    def __init__(self, max_workers: int = 4):
        import multiprocessing as mp

        self.max_workers = min(max_workers, mp.cpu_count())

    async def process_chunks_parallel(
        self,
        chunks: List[pd.DataFrame],
        action_func: Callable[..., Any],
        params: Dict[str, Any],
    ) -> List[Optional[pd.DataFrame]]:
        """Process chunks in parallel."""

        results: List[Optional[pd.DataFrame]] = []

        # Use ThreadPoolExecutor for I/O bound actions
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for chunk_idx, chunk in enumerate(chunks):
                future = executor.submit(
                    self._process_single_chunk, chunk, action_func, params, chunk_idx
                )
                futures.append(future)

            # Collect results with progress tracking
            for future in futures:
                try:
                    result = future.result(timeout=300)  # 5 min timeout
                    results.append(result)
                except Exception as e:
                    self._handle_chunk_error(e, len(results))
                    results.append(None)

        return results

    def _process_single_chunk(
        self,
        chunk: pd.DataFrame,
        action_func: Callable[..., Any],
        params: Dict[str, Any],
        chunk_idx: int,
    ) -> pd.DataFrame:
        """Process a single chunk."""

        # Create isolated context for chunk
        chunk_context = {
            "datasets": {params["input_key"]: chunk},
            "statistics": {},
            "chunk_info": {"chunk_index": chunk_idx, "chunk_size": len(chunk)},
        }

        # Execute action on chunk
        action_func(params, chunk_context)

        # Return processed chunk
        datasets = chunk_context.get("datasets", {})
        if (
            isinstance(datasets, dict)
            and params.get("output_key")
            and params["output_key"] in datasets
        ):
            result = datasets[params["output_key"]]
            if isinstance(result, pd.DataFrame):
                return result
        return chunk

    def _handle_chunk_error(self, error: Exception, chunk_idx: int) -> None:
        """Handle chunk processing error."""

        logger.error(f"Chunk {chunk_idx} failed: {str(error)}")


class ProgressMonitor:
    """Monitor and report processing progress."""

    def __init__(self, total_chunks: int, show_progress: bool = True):
        self.total_chunks = total_chunks
        self.show_progress = show_progress
        self.start_time = time.time()
        self.peak_memory = 0.0
        self.log_chunk_stats = True  # Can be configured later

        if show_progress and total_chunks > 0:
            from tqdm import tqdm as tqdm_class

            self.pbar: Optional[Any] = tqdm_class(
                total=total_chunks, desc="Processing chunks"
            )
        else:
            self.pbar = None

        self.chunk_stats: List[Dict[str, Any]] = []

    def update_chunk_complete(
        self, chunk_idx: int, rows_processed: int, chunk_time: float
    ) -> None:
        """Update progress for completed chunk."""

        # Update progress bar
        if self.pbar:
            self.pbar.update(1)

        # Track memory usage
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)

        # Record chunk statistics
        self.chunk_stats.append(
            {
                "chunk_index": chunk_idx,
                "rows_processed": rows_processed,
                "processing_time": chunk_time,
                "memory_mb": current_memory,
            }
        )

        # Log if requested
        if self.log_chunk_stats:
            logger.info(
                f"Chunk {chunk_idx}: {rows_processed} rows in {chunk_time:.2f}s, "
                f"Memory: {current_memory:.1f}MB"
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary."""

        total_time = time.time() - self.start_time

        avg_chunk_time = 0
        if self.chunk_stats:
            avg_chunk_time = np.mean([s["processing_time"] for s in self.chunk_stats])

        return {
            "total_chunks": self.total_chunks,
            "processing_time": total_time,
            "peak_memory_mb": self.peak_memory,
            "average_chunk_time": avg_chunk_time,
            "chunks_per_second": self.total_chunks / total_time
            if total_time > 0
            else 0,
        }


class ResultAggregator:
    """Aggregate chunk results into final output."""

    def aggregate_results(
        self,
        chunk_results: List[pd.DataFrame],
        method: str,
        params: ChunkProcessorParams,
    ) -> pd.DataFrame:
        """Combine chunk results based on aggregation method."""

        # Filter out failed chunks
        valid_results = [r for r in chunk_results if r is not None]

        if not valid_results:
            raise ValueError("All chunks failed processing")

        if method == "concat":
            # Simple concatenation
            result = pd.concat(valid_results, ignore_index=True)

            # Remove duplicates if specified
            if params.dedup_columns:
                result = result.drop_duplicates(subset=params.dedup_columns)

        elif method == "merge":
            # Merge on specified columns
            if not params.merge_columns:
                raise ValueError("merge_columns required for merge aggregation")

            result = valid_results[0]
            for chunk in valid_results[1:]:
                result = pd.merge(result, chunk, on=params.merge_columns, how="outer")

        elif method == "custom":
            # Allow custom aggregation logic
            result = self._custom_aggregation(valid_results, params)

        else:
            raise ValueError(f"Unknown aggregation method: {method}")

        return result

    def _custom_aggregation(
        self, chunks: List[pd.DataFrame], params: ChunkProcessorParams
    ) -> pd.DataFrame:
        """Custom aggregation logic for specific use cases."""

        # Example: Aggregate statistics across chunks
        if "statistics" in params.target_action.lower():
            # Combine statistical summaries
            return self._aggregate_statistics(chunks)

        # Default to concatenation
        return pd.concat(chunks, ignore_index=True)

    def _aggregate_statistics(self, chunks: List[pd.DataFrame]) -> pd.DataFrame:
        """Aggregate statistical results."""
        # Simple concatenation for now - can be enhanced for specific statistics
        return pd.concat(chunks, ignore_index=True)


class CheckpointManager:
    """Handle checkpointing for long-running processes."""

    def __init__(self, checkpoint_dir: Optional[str] = None):
        self.checkpoint_dir: Optional[Path]
        if checkpoint_dir:
            self.checkpoint_dir = Path(checkpoint_dir)
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.checkpoint_dir = None

    def save_checkpoint(
        self, chunk_idx: int, chunk_result: pd.DataFrame, context: Dict[str, Any]
    ) -> None:
        """Save checkpoint after chunk completion."""

        if not self.checkpoint_dir:
            return

        checkpoint_file = self.checkpoint_dir / f"chunk_{chunk_idx:05d}.pkl"

        checkpoint_data = {
            "chunk_index": chunk_idx,
            "chunk_result": chunk_result,
            "context": context,
            "timestamp": time.time(),
        }

        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint_data, f)

    def load_checkpoints(self) -> List[Dict[str, Any]]:
        """Load all saved checkpoints."""

        if not self.checkpoint_dir:
            return []

        checkpoints = []

        for checkpoint_file in sorted(self.checkpoint_dir.glob("chunk_*.pkl")):
            try:
                with open(checkpoint_file, "rb") as f:
                    checkpoint_data = pickle.load(f)
                    checkpoints.append(checkpoint_data)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")

        return checkpoints

    def resume_from_checkpoint(self) -> int:
        """Determine where to resume processing."""

        checkpoints = self.load_checkpoints()

        if not checkpoints:
            return 0

        # Find last completed chunk
        last_chunk_idx: int = max(cp["chunk_index"] for cp in checkpoints)

        logger.info(f"Resuming from chunk {last_chunk_idx + 1}")

        return last_chunk_idx + 1


@register_action("CHUNK_PROCESSOR")
class ChunkProcessorAction:
    """
    Performance infrastructure wrapper for memory-efficient processing.

    This action can wrap ANY other action to enable processing of large datasets
    that would otherwise exceed memory limits through intelligent chunking,
    parallel processing, and result aggregation.
    """

    def __init__(self, db_session: Any = None, *args: Any, **kwargs: Any) -> None:
        """Initialize the chunk processor action."""
        self.db_session = db_session
        self.logger = logging.getLogger(
            self.__class__.__module__ + "." + self.__class__.__name__
        )

    async def execute(
        self, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute chunk processing wrapper."""

        try:
            # Parse and validate parameters
            chunk_params = ChunkProcessorParams(**params)
        except Exception as e:
            error_msg = f"Invalid parameters for CHUNK_PROCESSOR: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "details": {"error": str(e)},
            }

        # Validate target action exists
        if chunk_params.target_action not in ACTION_REGISTRY:
            error_msg = f"Target action '{chunk_params.target_action}' not found"
            self.logger.error(error_msg)
            return {"success": False, "message": error_msg, "details": {}}

        # Get input dataset from context
        datasets = context.get("datasets", {})
        if chunk_params.input_key not in datasets:
            error_msg = (
                f"Input key '{chunk_params.input_key}' not found in context datasets"
            )
            self.logger.error(error_msg)
            return {"success": False, "message": error_msg, "details": {}}

        # Get input data and convert to DataFrame
        input_data = datasets[chunk_params.input_key]
        if isinstance(input_data, list):
            if not input_data:  # Empty list
                df = pd.DataFrame()
            else:
                df = pd.DataFrame(input_data)
        elif isinstance(input_data, pd.DataFrame):
            df = input_data.copy()
        else:
            error_msg = f"Unsupported input data type: {type(input_data)}"
            self.logger.error(error_msg)
            return {"success": False, "message": error_msg, "details": {}}

        # Initialize components
        chunking = ChunkingStrategy()
        aggregator = ResultAggregator()
        checkpoint_mgr = CheckpointManager(chunk_params.checkpoint_dir)

        # Optimize memory if requested
        if chunk_params.optimize_dtypes:
            df = chunking.optimize_dataframe_memory(df)

        # Calculate chunk size
        if chunk_params.chunk_by_memory:
            max_memory = chunk_params.max_memory_mb or 500  # Default fallback
            chunk_size = chunking.calculate_optimal_chunk_size(df, max_memory)
        else:
            chunk_size = chunk_params.chunk_size or 10000  # Default fallback

        # Create chunks
        overlap_rows = chunk_params.overlap_rows or 0  # Default fallback
        chunks = list(chunking.create_chunks(df, chunk_size, overlap_rows))

        if not chunks:  # Empty dataset
            result = ChunkProcessorResult(
                success=True,
                total_rows_processed=0,
                chunks_processed=0,
                chunks_failed=0,
                processing_time_seconds=0.0,
                peak_memory_mb=0.0,
                average_chunk_time=0.0,
                chunk_statistics=[],
                aggregation_method_used=chunk_params.aggregation_method,
            )

            # Store empty result in context
            context["datasets"][chunk_params.output_key] = pd.DataFrame()

            return {
                "success": True,
                "message": "Processing completed (empty dataset)",
                "details": result.model_dump(),
            }

        # Initialize progress monitor
        monitor = ProgressMonitor(len(chunks), chunk_params.show_progress)

        # Check for resumption
        start_chunk = 0
        if chunk_params.checkpoint_enabled:
            start_chunk = checkpoint_mgr.resume_from_checkpoint()

        # Get target action class
        target_action_class = ACTION_REGISTRY[chunk_params.target_action]

        # Process chunks
        chunk_results: List[Optional[pd.DataFrame]] = []
        error_chunks: List[int] = []

        for chunk_idx, (start_idx, chunk_df) in enumerate(
            chunks[start_chunk:], start_chunk
        ):
            chunk_start = time.time()

            try:
                # Process chunk sequentially (parallel can be added later)
                chunk_result = await self._process_chunk_sequential(
                    chunk_df, target_action_class, chunk_params, chunk_idx
                )

                chunk_results.append(chunk_result)

                # Save checkpoint
                if chunk_params.checkpoint_enabled:
                    checkpoint_mgr.save_checkpoint(chunk_idx, chunk_result, {})

                # Update progress
                chunk_time = time.time() - chunk_start
                monitor.update_chunk_complete(chunk_idx, len(chunk_df), chunk_time)

                # Garbage collection
                if chunk_params.gc_after_chunk:
                    gc.collect()

            except Exception as e:
                if chunk_params.error_strategy == "fail":
                    # Close progress bar before raising
                    if monitor.pbar:
                        monitor.pbar.close()
                    raise
                elif chunk_params.error_strategy == "skip":
                    self.logger.warning(f"Skipping failed chunk {chunk_idx}: {str(e)}")
                    chunk_results.append(None)
                    error_chunks.append(chunk_idx)
                elif chunk_params.error_strategy == "retry":
                    # Implement retry logic
                    retry_success = False
                    for retry in range(chunk_params.max_retries):
                        try:
                            time.sleep(chunk_params.retry_delay)
                            retry_result = await self._process_chunk_sequential(
                                chunk_df, target_action_class, chunk_params, chunk_idx
                            )
                            chunk_results.append(retry_result)
                            retry_success = True
                            break
                        except Exception as retry_e:
                            self.logger.warning(
                                f"Retry {retry + 1} failed for chunk {chunk_idx}: {retry_e}"
                            )

                    if not retry_success:
                        self.logger.error(f"All retries failed for chunk {chunk_idx}")
                        chunk_results.append(None)
                        error_chunks.append(chunk_idx)

        # Aggregate results
        try:
            # Filter out None results before aggregation
            valid_chunk_results = [r for r in chunk_results if r is not None]
            final_result = aggregator.aggregate_results(
                valid_chunk_results, chunk_params.aggregation_method, chunk_params
            )

            # Store final result in context
            context["datasets"][chunk_params.output_key] = final_result

        except Exception as e:
            # Close progress bar before handling error
            if monitor.pbar:
                monitor.pbar.close()
            error_msg = f"Failed to aggregate chunk results: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "details": {"aggregation_error": str(e)},
            }

        # Close progress bar
        if monitor.pbar:
            monitor.pbar.close()

        # Get summary statistics
        summary = monitor.get_summary()

        result = ChunkProcessorResult(
            success=True,
            total_rows_processed=len(df),
            chunks_processed=len(chunks),
            chunks_failed=len([r for r in chunk_results if r is None]),
            processing_time_seconds=summary["processing_time"],
            peak_memory_mb=summary["peak_memory_mb"],
            average_chunk_time=summary["average_chunk_time"],
            chunk_statistics=monitor.chunk_stats,
            aggregation_method_used=chunk_params.aggregation_method,
            error_chunks=error_chunks if error_chunks else None,
        )

        return {
            "success": True,
            "message": f"Chunk processing completed: {len(chunks)} chunks processed",
            "details": result.model_dump(),
        }

    async def _process_chunk_sequential(
        self,
        chunk_df: pd.DataFrame,
        target_action_class: type,
        params: ChunkProcessorParams,
        chunk_idx: int,
    ) -> pd.DataFrame:
        """Process a single chunk sequentially."""

        # Create chunk context with datasets
        chunk_context = {
            "datasets": {params.input_key: chunk_df},
            "statistics": {},
            "chunk_info": {"chunk_index": chunk_idx, "chunk_size": len(chunk_df)},
        }

        # Create target action instance
        action = target_action_class()

        # Execute target action on chunk
        await action.execute(params.target_params, chunk_context)

        # Return processed chunk from output key, or original if not found
        datasets = chunk_context.get("datasets", {})
        if isinstance(datasets, dict):
            result = datasets.get(params.output_key, chunk_df)
        else:
            result = chunk_df

        # Ensure result is DataFrame
        if isinstance(result, list):
            result = pd.DataFrame(result)
        elif not isinstance(result, pd.DataFrame):
            result = chunk_df  # Fallback to original chunk

        return result
