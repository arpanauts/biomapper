# STREAMING_DATA_PROCESSOR Action Type

## Overview

The `STREAMING_DATA_PROCESSOR` is a foundational action that provides memory-efficient processing of large datasets. This action implements the core streaming pipeline described in [06_STREAMING_INFRASTRUCTURE.md](./06_STREAMING_INFRASTRUCTURE.md), including async generators, backpressure handling, and pluggable processors.

### Purpose
- Process files larger than available memory
- Provide consistent streaming interface for all data operations
- Enable progress tracking for long-running operations
- Support various file formats (CSV, TSV, JSON Lines)

### Use Cases
- Loading 100M+ identifier datasets
- Processing large cross-reference tables
- Streaming ETL operations
- Real-time data processing pipelines

## Design Decisions

### Why Streaming?
Based on analysis of real datasets (UKBB, metabolomics), files can contain millions of rows. Loading these entirely into memory is impractical and limits scalability.

### Key Design Choices
1. **Async Generators**: Use Python's async generators for memory-efficient iteration
2. **Configurable Chunks**: Allow users to tune chunk size based on their needs
3. **Format Agnostic**: Support multiple file formats through plugins
4. **Progress Tracking**: Built-in progress reporting with ETA
5. **Error Boundaries**: Each chunk processes independently for fault tolerance

## Implementation Details

### Parameter Model
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path

class StreamingDataProcessorParams(BaseModel):
    """Parameters for streaming data processing."""
    
    # Input configuration
    file_path: Path = Field(..., description="Path to input file")
    file_format: Literal['csv', 'tsv', 'jsonl', 'auto'] = Field(
        default='auto',
        description="File format (auto-detected if not specified)"
    )
    encoding: str = Field(default='utf-8', description="File encoding")
    
    # Streaming configuration
    chunk_size: int = Field(
        default=1000,
        ge=1,
        le=100000,
        description="Number of rows per chunk"
    )
    memory_limit_mb: int = Field(
        default=500,
        ge=50,
        le=8000,
        description="Maximum memory usage in MB"
    )
    
    # Processing configuration
    columns: Optional[List[str]] = Field(
        default=None,
        description="Specific columns to load (None = all)"
    )
    skip_rows: int = Field(
        default=0,
        ge=0,
        description="Number of rows to skip at start"
    )
    max_rows: Optional[int] = Field(
        default=None,
        description="Maximum rows to process (None = all)"
    )
    
    # Data cleaning
    skip_empty: bool = Field(
        default=True,
        description="Skip rows with empty values in key columns"
    )
    strip_whitespace: bool = Field(
        default=True,
        description="Strip whitespace from values"
    )
    
    # Error handling
    continue_on_error: bool = Field(
        default=True,
        description="Continue processing on errors"
    )
    error_threshold: float = Field(
        default=0.1,
        ge=0,
        le=1,
        description="Maximum error rate before stopping"
    )
    
    # Progress tracking
    report_progress: bool = Field(
        default=True,
        description="Enable progress reporting"
    )
    progress_interval: int = Field(
        default=10000,
        description="Rows between progress updates"
    )
```

### Result Models
```python
class ChunkResult(BaseModel):
    """Result from processing a single chunk."""
    chunk_id: int
    rows_processed: int
    data: List[Dict[str, Any]]
    errors: List[ErrorDetail]
    memory_usage_mb: float
    processing_time_ms: float

class StreamingDataProcessorResult(ActionResult):
    """Final result after processing all chunks."""
    total_chunks: int
    total_rows: int
    total_errors: int
    chunks_with_errors: List[int]
    average_chunk_time_ms: float
    peak_memory_mb: float
    file_metadata: Dict[str, Any]
```

### Core Algorithm
```python
class StreamingDataProcessor(GeneralizedAction[StreamingDataProcessorParams, StreamingDataProcessorResult]):
    """Memory-efficient data processing for large files."""
    
    async def stream_execute(
        self,
        params: StreamingDataProcessorParams,
        context: ExecutionContext
    ) -> AsyncIterator[ChunkResult]:
        """Stream process file in chunks."""
        
        # Detect file format
        file_format = self._detect_format(params.file_path, params.file_format)
        
        # Initialize reader
        reader = self._get_reader(file_format, params)
        
        # Track state
        chunk_id = 0
        total_rows = 0
        total_errors = 0
        
        async with reader as r:
            # Skip initial rows if requested
            await r.skip_rows(params.skip_rows)
            
            # Process chunks
            while True:
                # Check memory before loading chunk
                if self._memory_usage_mb() > params.memory_limit_mb:
                    await self._wait_for_memory()
                
                # Read chunk
                chunk_data = await r.read_chunk(params.chunk_size)
                if not chunk_data:
                    break
                
                # Process chunk
                chunk_result = await self._process_chunk(
                    chunk_id=chunk_id,
                    data=chunk_data,
                    params=params
                )
                
                # Update counters
                chunk_id += 1
                total_rows += chunk_result.rows_processed
                total_errors += len(chunk_result.errors)
                
                # Check error threshold
                error_rate = total_errors / total_rows if total_rows > 0 else 0
                if error_rate > params.error_threshold:
                    raise ValueError(f"Error rate {error_rate:.2%} exceeds threshold")
                
                # Report progress
                if params.report_progress and total_rows % params.progress_interval == 0:
                    await self._report_progress(total_rows, context)
                
                yield chunk_result
                
                # Check max rows
                if params.max_rows and total_rows >= params.max_rows:
                    break
    
    async def _process_chunk(
        self,
        chunk_id: int,
        data: List[Dict],
        params: StreamingDataProcessorParams
    ) -> ChunkResult:
        """Process a single chunk of data."""
        start_time = time.time()
        start_memory = self._memory_usage_mb()
        errors = []
        processed_data = []
        
        for row in data:
            try:
                # Clean data
                if params.strip_whitespace:
                    row = {k: v.strip() if isinstance(v, str) else v 
                           for k, v in row.items()}
                
                # Skip empty rows
                if params.skip_empty and all(not v for v in row.values()):
                    continue
                
                # Filter columns
                if params.columns:
                    row = {k: v for k, v in row.items() if k in params.columns}
                
                processed_data.append(row)
                
            except Exception as e:
                if params.continue_on_error:
                    errors.append(ErrorDetail(
                        row_number=chunk_id * params.chunk_size + len(processed_data),
                        error=str(e),
                        data=row
                    ))
                else:
                    raise
        
        return ChunkResult(
            chunk_id=chunk_id,
            rows_processed=len(processed_data),
            data=processed_data,
            errors=errors,
            memory_usage_mb=self._memory_usage_mb() - start_memory,
            processing_time_ms=(time.time() - start_time) * 1000
        )
```

## Performance Characteristics

### Benchmarks
| Dataset Size | Chunk Size | Memory Usage | Processing Time |
|--------------|------------|--------------|-----------------|
| 1M rows      | 1,000      | ~50MB        | ~10 seconds     |
| 10M rows     | 5,000      | ~100MB       | ~100 seconds    |
| 100M rows    | 10,000     | ~200MB       | ~1000 seconds   |

### Memory Profile
- Base overhead: ~20MB
- Per chunk: ~(chunk_size * avg_row_size * 2) bytes
- Peak usage: base + max(chunk_memory)

### Optimization Strategies
1. **Chunk Size Tuning**: Larger chunks = better throughput but more memory
2. **Column Selection**: Only load needed columns
3. **Parallel Processing**: Process chunks concurrently (future enhancement)
4. **Compression**: Support reading compressed files directly

## Error Scenarios

### Common Errors
1. **File Not Found**: Clear error with path
2. **Invalid Format**: Auto-detection fallback
3. **Encoding Issues**: Try common encodings
4. **Memory Exceeded**: Automatic backpressure
5. **Corrupt Data**: Row-level error isolation

### Recovery Strategies
```python
# Automatic retry with smaller chunks
if memory_error:
    new_chunk_size = params.chunk_size // 2
    await retry_with_params(chunk_size=new_chunk_size)

# Skip corrupted sections
if parse_error and params.continue_on_error:
    log_error(error)
    continue_to_next_row()
```

## Testing Strategy

### Unit Tests
```python
class TestStreamingDataProcessor:
    """TDD tests for streaming data processor."""
    
    @pytest.mark.asyncio
    async def test_stream_large_file(self, tmp_path):
        """Test streaming a large CSV file."""
        # Create test file
        test_file = tmp_path / "large_dataset.csv"
        with open(test_file, 'w') as f:
            f.write("id,name,value\n")
            for i in range(10000):
                f.write(f"ID{i},Name{i},{i*10}\n")
        
        # Process with streaming
        processor = StreamingDataProcessor()
        chunks_processed = 0
        total_rows = 0
        
        async for chunk in processor.stream_execute(
            params=StreamingDataProcessorParams(
                file_path=test_file,
                chunk_size=1000
            ),
            context={}
        ):
            chunks_processed += 1
            total_rows += chunk.rows_processed
            assert chunk.memory_usage_mb < 50  # Memory constraint
            assert len(chunk.errors) == 0
        
        assert chunks_processed == 10
        assert total_rows == 10000
    
    @pytest.mark.asyncio
    async def test_memory_limit_enforcement(self):
        """Test that memory limits are respected."""
        # Test with very low memory limit
        processor = StreamingDataProcessor()
        
        with pytest.raises(MemoryError):
            async for chunk in processor.stream_execute(
                params=StreamingDataProcessorParams(
                    file_path="huge_file.csv",
                    chunk_size=100000,
                    memory_limit_mb=10  # Very low limit
                ),
                context={}
            ):
                pass
    
    @pytest.mark.asyncio
    async def test_error_threshold(self):
        """Test error threshold handling."""
        # Create file with some bad data
        # Assert processing stops when threshold exceeded
        pass
```

### Integration Tests
- Test with real UKBB protein files
- Test with Arivale metabolomics data
- Test with cross-reference tables
- Benchmark against current non-streaming loaders

## Examples

### Basic Usage
```yaml
- action:
    type: STREAMING_DATA_PROCESSOR
    params:
      file_path: "/data/ukbb_proteins.csv"
      chunk_size: 5000
      columns: ["Assay", "UniProt", "Panel"]
      output_context_key: "ukbb_proteins"
```

### Advanced Usage with Error Handling
```yaml
- action:
    type: STREAMING_DATA_PROCESSOR
    params:
      file_path: "/data/metabolomics_full.tsv"
      file_format: "tsv"
      chunk_size: 10000
      memory_limit_mb: 1000
      skip_rows: 13  # Skip Arivale headers
      columns: ["name", "hmdb_id", "kegg_id"]
      continue_on_error: true
      error_threshold: 0.05  # Allow 5% errors
      output_context_key: "metabolite_ids"
```

### Processing Composite IDs
```python
# Custom processor using streaming base
async for chunk in stream_processor.stream_execute(params, context):
    # Process composite IDs in each chunk
    for row in chunk.data:
        if ',' in row['uniprot']:
            ids = row['uniprot'].split(',')
            # Handle multiple IDs
```

## Integration Notes

### Dependencies
- No external dependencies for core functionality
- Optional: `aiofiles` for async file I/O
- Optional: `psutil` for memory monitoring

### Used By
- `LOAD_DATASET_IDENTIFIERS` - Built on top of streaming
- `PARSE_COMPOSITE_IDENTIFIERS` - Processes streamed chunks
- All data loading actions use this as foundation

### Combines With
- `CACHE_MANAGER` - Cache processed chunks
- `ERROR_HANDLER` - Standardized error handling
- `PARALLEL_PROCESS` - Process chunks concurrently

## Future Enhancements

1. **Parallel Chunk Processing**: Process multiple chunks concurrently
2. **Compressed File Support**: Read .gz, .zip directly
3. **Remote File Streaming**: S3, HTTP sources
4. **Schema Evolution**: Handle changing schemas
5. **Checkpoint/Resume**: Save progress for interruption recovery

## Performance Tips

1. **Optimal Chunk Size**: Start with 1000-5000 rows, adjust based on row size
2. **Column Selection**: Always specify needed columns to reduce memory
3. **Memory Monitoring**: Use monitoring to find optimal memory_limit_mb
4. **Error Threshold**: Set based on data quality expectations
5. **Progress Reporting**: Disable for maximum throughput