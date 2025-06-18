# Enhanced Mapping Executor

The `EnhancedMappingExecutor` extends the base `MappingExecutor` with robust execution features including checkpointing, retry logic, and progress tracking. These features are essential for large-scale mapping operations that may take hours to complete or involve unreliable external services.

## Features

### 1. Checkpointing
- Save execution state to disk for resumable operations
- Automatic recovery from interruptions
- Configurable checkpoint directory
- Atomic checkpoint writes to prevent corruption

### 2. Retry Logic
- Configurable retry attempts for failed operations
- Exponential backoff between retries
- Customizable exception types to retry
- Per-operation retry configuration

### 3. Progress Tracking
- Real-time progress reporting via callbacks
- Batch processing statistics
- Detailed execution metrics
- Integration with logging framework

### 4. Batch Processing
- Process large datasets in configurable batches
- Memory-efficient operation
- Progress checkpointing per batch
- Parallel batch execution support

## Usage

### Basic Usage

```python
from biomapper.core.mapping_executor_enhanced import EnhancedMappingExecutor

# Create executor with robust features enabled
executor = await EnhancedMappingExecutor.create(
    checkpoint_enabled=True,
    checkpoint_dir="/path/to/checkpoints",
    batch_size=250,
    max_retries=3,
    retry_delay=5
)

# Execute mapping with automatic checkpointing
result = await executor.execute_yaml_strategy_robust(
    strategy_name="UKBB_TO_HPA_MAPPING",
    input_identifiers=identifiers,
    execution_id="unique_execution_id"
)
```

### Progress Monitoring

```python
# Add progress callback
def progress_handler(progress_data):
    if progress_data['type'] == 'batch_complete':
        print(f"Progress: {progress_data['progress_percent']:.1f}%")
        
executor.add_progress_callback(progress_handler)
```

### Batch Processing External APIs

```python
async def process_api_batch(batch):
    # Your API processing logic
    return await api_client.process(batch)

# Process with checkpointing and retry
results = await executor.process_in_batches(
    items=large_identifier_list,
    processor=process_api_batch,
    processor_name="api_resolution",
    checkpoint_key="api_results",
    execution_id="api_job_123"
)
```

## Configuration Parameters

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| checkpoint_enabled | bool | False | Enable checkpoint saving |
| checkpoint_dir | str | ~/.biomapper/checkpoints | Directory for checkpoint files |
| batch_size | int | 100 | Number of items per batch |
| max_retries | int | 3 | Maximum retry attempts |
| retry_delay | int | 5 | Seconds between retries |

### Standard MappingExecutor Parameters

All standard `MappingExecutor` parameters are also supported:
- metamapper_db_url
- mapping_cache_db_url
- echo_sql
- path_cache_size
- path_cache_expiry_seconds
- max_concurrent_batches
- enable_metrics

## Checkpoint Structure

Checkpoints are saved as pickled dictionaries containing:
- Current execution state
- Processed item count
- Intermediate results
- Timestamp information
- Custom application data

Example checkpoint structure:
```python
{
    'checkpoint_time': '2025-06-15T10:30:45',
    'processed_count': 1500,
    'total_count': 3000,
    'processor': 'uniprot_resolution',
    'results': [...],
    'custom_data': {...}
}
```

## Error Handling

The enhanced executor provides multiple levels of error handling:

1. **Operation-level retry**: Individual operations can be retried
2. **Batch-level recovery**: Failed batches are retried as a unit
3. **Checkpoint recovery**: Resume from last successful state
4. **Graceful degradation**: Continue processing despite partial failures

## Performance Considerations

### Memory Usage
- Batch processing limits memory usage
- Checkpoints are written incrementally
- Results can be streamed rather than accumulated

### I/O Optimization
- Atomic checkpoint writes
- Configurable checkpoint frequency
- Async I/O throughout

### Concurrency
- Maintains MappingExecutor's concurrent batch support
- Thread-safe checkpoint operations
- Progress callbacks executed asynchronously

## Migration from Standard MappingExecutor

The `EnhancedMappingExecutor` is a drop-in replacement for `MappingExecutor`:

```python
# Before
executor = await MappingExecutor.create()

# After
executor = await EnhancedMappingExecutor.create(
    checkpoint_enabled=True  # Opt-in to robust features
)
```

## Example: Large-Scale Mapping with Recovery

```python
import asyncio
from biomapper.core.mapping_executor_enhanced import EnhancedMappingExecutor

async def robust_mapping_pipeline():
    # Create executor with all robust features
    executor = await EnhancedMappingExecutor.create(
        checkpoint_enabled=True,
        batch_size=500,
        max_retries=5,
        retry_delay=10
    )
    
    # Add comprehensive progress tracking
    def track_progress(data):
        logger.info(f"Progress: {data}")
        # Could also update UI, send notifications, etc.
        
    executor.add_progress_callback(track_progress)
    
    try:
        # Load large dataset
        identifiers = await load_million_identifiers()
        
        # Execute with unique ID for resumability
        execution_id = f"large_mapping_{datetime.now().isoformat()}"
        
        # This can be interrupted and resumed
        result = await executor.execute_yaml_strategy_robust(
            strategy_name="COMPLEX_MAPPING",
            input_identifiers=identifiers,
            execution_id=execution_id
        )
        
        # Process results
        await save_results(result)
        
    finally:
        await executor.async_dispose()

# Run with automatic recovery on failure
if __name__ == "__main__":
    asyncio.run(robust_mapping_pipeline())
```

## Best Practices

1. **Always use unique execution IDs** for different runs
2. **Configure appropriate batch sizes** based on API limits
3. **Monitor checkpoint directory size** and clean old checkpoints
4. **Test checkpoint recovery** in development
5. **Use progress callbacks** for long-running operations
6. **Set reasonable retry limits** to avoid infinite loops

## Future Enhancements

Planned improvements include:
- Distributed checkpointing for cluster deployments
- Checkpoint compression and encryption
- Web UI for progress monitoring
- Automatic checkpoint cleanup policies
- Integration with job scheduling systems