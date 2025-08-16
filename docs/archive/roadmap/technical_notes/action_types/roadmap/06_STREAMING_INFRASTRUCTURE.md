# Streaming Infrastructure

## Overview

The Streaming Infrastructure provides memory-efficient processing of large biological datasets through async generators, backpressure handling, and chunk-based processing. This architecture enables Biomapper to handle datasets that exceed available memory while maintaining performance.

## Core Components

### Streaming Pipeline

```python
from typing import AsyncIterator, TypeVar, Generic, Protocol, Optional, Any, Dict, List
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import asyncio
from dataclasses import dataclass
import aiofiles
import json
from pathlib import Path

T = TypeVar('T')
U = TypeVar('U')

class StreamChunk(BaseModel, Generic[T]):
    """Container for a chunk of streaming data."""
    data: List[T]
    chunk_id: int
    total_chunks: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class StreamProcessor(Protocol, Generic[T, U]):
    """Protocol for stream processors."""
    
    async def process_chunk(self, chunk: StreamChunk[T]) -> StreamChunk[U]:
        """Process a single chunk."""
        ...
    
    async def initialize(self) -> None:
        """Initialize processor."""
        ...
    
    async def finalize(self) -> Dict[str, Any]:
        """Finalize processing and return summary."""
        ...

class StreamPipeline(Generic[T]):
    """Core streaming pipeline for biological data."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        max_concurrent_chunks: int = 5,
        backpressure_threshold: int = 10
    ):
        self.chunk_size = chunk_size
        self.max_concurrent_chunks = max_concurrent_chunks
        self.backpressure_threshold = backpressure_threshold
        self._processors: List[StreamProcessor] = []
        self._semaphore = asyncio.Semaphore(max_concurrent_chunks)
        self._stats = {
            "chunks_processed": 0,
            "items_processed": 0,
            "errors": 0
        }
    
    def add_processor(self, processor: StreamProcessor) -> 'StreamPipeline':
        """Add processor to pipeline."""
        self._processors.append(processor)
        return self
    
    async def process_stream(
        self,
        data_stream: AsyncIterator[T]
    ) -> AsyncIterator[StreamChunk[Any]]:
        """Process data through the pipeline."""
        
        # Initialize all processors
        for processor in self._processors:
            await processor.initialize()
        
        try:
            # Create chunks from input stream
            chunk_stream = self._create_chunks(data_stream)
            
            # Process through pipeline
            async for result_chunk in self._process_pipeline(chunk_stream):
                yield result_chunk
                
        finally:
            # Finalize all processors
            for processor in self._processors:
                await processor.finalize()
    
    async def _create_chunks(
        self,
        data_stream: AsyncIterator[T]
    ) -> AsyncIterator[StreamChunk[T]]:
        """Create chunks from input stream."""
        chunk_data = []
        chunk_id = 0
        
        async for item in data_stream:
            chunk_data.append(item)
            
            if len(chunk_data) >= self.chunk_size:
                yield StreamChunk(
                    data=chunk_data,
                    chunk_id=chunk_id,
                    metadata={"source": "input_stream"}
                )
                chunk_data = []
                chunk_id += 1
        
        # Yield remaining data
        if chunk_data:
            yield StreamChunk(
                data=chunk_data,
                chunk_id=chunk_id,
                metadata={"source": "input_stream", "final_chunk": True}
            )
    
    async def _process_pipeline(
        self,
        chunk_stream: AsyncIterator[StreamChunk[T]]
    ) -> AsyncIterator[StreamChunk[Any]]:
        """Process chunks through the pipeline."""
        
        async def process_single_chunk(chunk: StreamChunk[Any]) -> StreamChunk[Any]:
            """Process chunk through all processors."""
            async with self._semaphore:  # Limit concurrent processing
                current_chunk = chunk
                
                for processor in self._processors:
                    try:
                        current_chunk = await processor.process_chunk(current_chunk)
                    except Exception as e:
                        self._stats["errors"] += 1
                        # Add error info to chunk
                        current_chunk.metadata["error"] = str(e)
                        current_chunk.metadata["failed_processor"] = type(processor).__name__
                
                self._stats["chunks_processed"] += 1
                self._stats["items_processed"] += len(current_chunk.data)
                
                return current_chunk
        
        # Process chunks with backpressure control
        pending_tasks = set()
        
        async for chunk in chunk_stream:
            # Wait if too many chunks are pending
            if len(pending_tasks) >= self.backpressure_threshold:
                done, pending_tasks = await asyncio.wait(
                    pending_tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    yield await task
            
            # Start processing new chunk
            task = asyncio.create_task(process_single_chunk(chunk))
            pending_tasks.add(task)
        
        # Wait for remaining tasks
        while pending_tasks:
            done, pending_tasks = await asyncio.wait(
                pending_tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                yield await task
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self._stats.copy()
```

### File Stream Readers

```python
class BiologicalFileStreamer:
    """Streaming readers for biological file formats."""
    
    @staticmethod
    async def stream_csv(
        file_path: str,
        chunk_size: int = 1000,
        skip_header: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream CSV file."""
        async with aiofiles.open(file_path, 'r') as file:
            header = None
            if skip_header:
                header_line = await file.readline()
                header = [col.strip() for col in header_line.strip().split(',')]
            
            buffer = []
            async for line in file:
                if line.strip():
                    values = [val.strip() for val in line.strip().split(',')]
                    
                    if header:
                        record = dict(zip(header, values))
                    else:
                        record = {f"col_{i}": val for i, val in enumerate(values)}
                    
                    buffer.append(record)
                    
                    if len(buffer) >= chunk_size:
                        for record in buffer:
                            yield record
                        buffer = []
            
            # Yield remaining records
            for record in buffer:
                yield record
    
    @staticmethod
    async def stream_jsonl(
        file_path: str,
        chunk_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream JSONL file."""
        async with aiofiles.open(file_path, 'r') as file:
            buffer = []
            async for line in file:
                if line.strip():
                    try:
                        record = json.loads(line.strip())
                        buffer.append(record)
                        
                        if len(buffer) >= chunk_size:
                            for record in buffer:
                                yield record
                            buffer = []
                    except json.JSONDecodeError:
                        continue  # Skip malformed lines
            
            # Yield remaining records
            for record in buffer:
                yield record
    
    @staticmethod
    async def stream_tsv(
        file_path: str,
        chunk_size: int = 1000,
        skip_header: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream TSV file."""
        async with aiofiles.open(file_path, 'r') as file:
            header = None
            if skip_header:
                header_line = await file.readline()
                header = [col.strip() for col in header_line.strip().split('\t')]
            
            buffer = []
            async for line in file:
                if line.strip():
                    values = [val.strip() for val in line.strip().split('\t')]
                    
                    if header:
                        record = dict(zip(header, values))
                    else:
                        record = {f"col_{i}": val for i, val in enumerate(values)}
                    
                    buffer.append(record)
                    
                    if len(buffer) >= chunk_size:
                        for record in buffer:
                            yield record
                        buffer = []
            
            # Yield remaining records
            for record in buffer:
                yield record
```

### Specialized Biological Processors

```python
class BiologicalParserProcessor(StreamProcessor[Dict[str, Any], Dict[str, Any]]):
    """Stream processor for biological identifier parsing."""
    
    def __init__(self, parser_registry, column_mappings: List[Dict[str, str]]):
        self.parser_registry = parser_registry
        self.column_mappings = column_mappings
        self.stats = {
            "parsed_records": 0,
            "parse_errors": 0,
            "parser_usage": {}
        }
    
    async def initialize(self) -> None:
        """Initialize parser."""
        pass
    
    async def process_chunk(
        self,
        chunk: StreamChunk[Dict[str, Any]]
    ) -> StreamChunk[Dict[str, Any]]:
        """Parse identifiers in chunk."""
        parsed_records = []
        
        for record in chunk.data:
            parsed_record = record.copy()
            
            for mapping in self.column_mappings:
                source_col = mapping["source_column"]
                identifier_type = mapping["identifier_type"]
                
                if source_col in record:
                    value = record[source_col]
                    
                    try:
                        parse_results = await self.parser_registry.parse(
                            value,
                            identifier_type
                        )
                        
                        if parse_results:
                            best_result = parse_results[0]
                            parsed_record[f"{identifier_type}_parsed"] = {
                                "raw": value,
                                "parsed": best_result.parsed_value,
                                "confidence": best_result.confidence,
                                "parser": best_result.parser_name
                            }
                            
                            # Update stats
                            parser_name = best_result.parser_name
                            self.stats["parser_usage"][parser_name] = \
                                self.stats["parser_usage"].get(parser_name, 0) + 1
                        
                        self.stats["parsed_records"] += 1
                        
                    except Exception as e:
                        self.stats["parse_errors"] += 1
                        parsed_record[f"{identifier_type}_error"] = str(e)
            
            parsed_records.append(parsed_record)
        
        return StreamChunk(
            data=parsed_records,
            chunk_id=chunk.chunk_id,
            total_chunks=chunk.total_chunks,
            metadata={
                **chunk.metadata,
                "processor": "biological_parser",
                "parsed_count": len(parsed_records)
            }
        )
    
    async def finalize(self) -> Dict[str, Any]:
        """Return processing summary."""
        return self.stats

class NormalizationProcessor(StreamProcessor[Dict[str, Any], Dict[str, Any]]):
    """Stream processor for data normalization."""
    
    def __init__(self, normalization_engine):
        self.normalization_engine = normalization_engine
        self.stats = {
            "normalized_records": 0,
            "normalization_errors": 0
        }
    
    async def initialize(self) -> None:
        """Initialize normalizer."""
        pass
    
    async def process_chunk(
        self,
        chunk: StreamChunk[Dict[str, Any]]
    ) -> StreamChunk[Dict[str, Any]]:
        """Normalize records in chunk."""
        normalized_records = []
        
        for record in chunk.data:
            try:
                normalized = await self.normalization_engine.normalize_record(record)
                normalized_records.append(normalized)
                self.stats["normalized_records"] += 1
            except Exception as e:
                self.stats["normalization_errors"] += 1
                # Include original record with error info
                record["normalization_error"] = str(e)
                normalized_records.append(record)
        
        return StreamChunk(
            data=normalized_records,
            chunk_id=chunk.chunk_id,
            total_chunks=chunk.total_chunks,
            metadata={
                **chunk.metadata,
                "processor": "normalization",
                "normalized_count": len(normalized_records)
            }
        )
    
    async def finalize(self) -> Dict[str, Any]:
        """Return processing summary."""
        return self.stats

class CrossReferenceProcessor(StreamProcessor[Dict[str, Any], Dict[str, Any]]):
    """Stream processor for cross-reference resolution."""
    
    def __init__(self, graph_resolver, identifier_fields: List[str]):
        self.graph_resolver = graph_resolver
        self.identifier_fields = identifier_fields
        self.stats = {
            "resolved_records": 0,
            "resolution_errors": 0,
            "total_mappings": 0
        }
    
    async def initialize(self) -> None:
        """Initialize resolver."""
        pass
    
    async def process_chunk(
        self,
        chunk: StreamChunk[Dict[str, Any]]
    ) -> StreamChunk[Dict[str, Any]]:
        """Resolve cross-references in chunk."""
        resolved_records = []
        
        for record in chunk.data:
            enriched_record = record.copy()
            
            for field in self.identifier_fields:
                if field in record:
                    identifier = record[field]
                    
                    try:
                        result = await self.graph_resolver.resolve_cross_reference(
                            identifier,
                            max_hops=2
                        )
                        
                        if result.mappings:
                            enriched_record[f"{field}_mappings"] = result.mappings
                            enriched_record[f"{field}_paths"] = result.paths
                            self.stats["total_mappings"] += len(result.mappings)
                        
                        self.stats["resolved_records"] += 1
                        
                    except Exception as e:
                        self.stats["resolution_errors"] += 1
                        enriched_record[f"{field}_resolution_error"] = str(e)
            
            resolved_records.append(enriched_record)
        
        return StreamChunk(
            data=resolved_records,
            chunk_id=chunk.chunk_id,
            total_chunks=chunk.total_chunks,
            metadata={
                **chunk.metadata,
                "processor": "cross_reference",
                "resolved_count": len(resolved_records)
            }
        )
    
    async def finalize(self) -> Dict[str, Any]:
        """Return processing summary."""
        return self.stats
```

### Stream Sinks

```python
class StreamSink(ABC, Generic[T]):
    """Abstract base for stream output sinks."""
    
    @abstractmethod
    async def write_chunk(self, chunk: StreamChunk[T]) -> None:
        """Write chunk to sink."""
        pass
    
    @abstractmethod
    async def finalize(self) -> Dict[str, Any]:
        """Finalize sink and return summary."""
        pass

class FileStreamSink(StreamSink[Dict[str, Any]]):
    """Write stream to file."""
    
    def __init__(self, output_path: str, format: str = "jsonl"):
        self.output_path = Path(output_path)
        self.format = format
        self.file_handle = None
        self.records_written = 0
    
    async def initialize(self):
        """Initialize file handle."""
        self.file_handle = await aiofiles.open(self.output_path, 'w')
    
    async def write_chunk(self, chunk: StreamChunk[Dict[str, Any]]) -> None:
        """Write chunk to file."""
        if not self.file_handle:
            await self.initialize()
        
        for record in chunk.data:
            if self.format == "jsonl":
                await self.file_handle.write(json.dumps(record) + '\n')
            elif self.format == "csv":
                # Handle CSV writing
                pass
            
            self.records_written += 1
    
    async def finalize(self) -> Dict[str, Any]:
        """Close file and return summary."""
        if self.file_handle:
            await self.file_handle.close()
        
        return {
            "output_file": str(self.output_path),
            "records_written": self.records_written,
            "format": self.format
        }

class DatabaseStreamSink(StreamSink[Dict[str, Any]]):
    """Write stream to database."""
    
    def __init__(self, session_factory, table_name: str, batch_size: int = 1000):
        self.session_factory = session_factory
        self.table_name = table_name
        self.batch_size = batch_size
        self.records_written = 0
        self.batch_buffer = []
    
    async def write_chunk(self, chunk: StreamChunk[Dict[str, Any]]) -> None:
        """Write chunk to database."""
        self.batch_buffer.extend(chunk.data)
        
        while len(self.batch_buffer) >= self.batch_size:
            batch = self.batch_buffer[:self.batch_size]
            self.batch_buffer = self.batch_buffer[self.batch_size:]
            
            await self._write_batch(batch)
    
    async def _write_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Write batch to database."""
        async with self.session_factory() as session:
            # Implementation depends on database and ORM
            pass
    
    async def finalize(self) -> Dict[str, Any]:
        """Write remaining records."""
        if self.batch_buffer:
            await self._write_batch(self.batch_buffer)
        
        return {
            "table": self.table_name,
            "records_written": self.records_written
        }
```

## Integration with Actions

```python
@register_action("STREAMING_DATA_PROCESSOR")
class StreamingDataProcessorAction(TypedStrategyAction[StreamingParams, StreamingResult]):
    
    async def execute_typed(
        self,
        params: StreamingParams,
        context: StrategyExecutionContext
    ) -> StreamingResult:
        """Process data using streaming pipeline."""
        
        # Create data stream
        if params.input_format == "csv":
            data_stream = BiologicalFileStreamer.stream_csv(
                params.input_path,
                chunk_size=params.chunk_size
            )
        elif params.input_format == "jsonl":
            data_stream = BiologicalFileStreamer.stream_jsonl(
                params.input_path,
                chunk_size=params.chunk_size
            )
        else:
            raise ValueError(f"Unsupported format: {params.input_format}")
        
        # Create pipeline
        pipeline = StreamPipeline(
            chunk_size=params.chunk_size,
            max_concurrent_chunks=params.max_concurrent_chunks
        )
        
        # Add processors based on configuration
        if params.enable_parsing:
            parser_processor = BiologicalParserProcessor(
                context.parser_registry,
                params.column_mappings
            )
            pipeline.add_processor(parser_processor)
        
        if params.enable_normalization:
            norm_processor = NormalizationProcessor(
                context.normalization_engine
            )
            pipeline.add_processor(norm_processor)
        
        if params.enable_cross_reference:
            xref_processor = CrossReferenceProcessor(
                context.graph_resolver,
                params.identifier_fields
            )
            pipeline.add_processor(xref_processor)
        
        # Create output sink
        output_sink = FileStreamSink(
            params.output_path,
            params.output_format
        )
        
        # Process stream
        total_chunks = 0
        async for result_chunk in pipeline.process_stream(data_stream):
            await output_sink.write_chunk(result_chunk)
            total_chunks += 1
            
            # Progress reporting
            if total_chunks % 10 == 0:
                context.logger.info(f"Processed {total_chunks} chunks")
        
        # Finalize
        sink_summary = await output_sink.finalize()
        pipeline_stats = pipeline.get_stats()
        
        return StreamingResult(
            total_chunks_processed=total_chunks,
            total_items_processed=pipeline_stats["items_processed"],
            processing_errors=pipeline_stats["errors"],
            output_summary=sink_summary,
            pipeline_stats=pipeline_stats
        )
```

## Configuration

```yaml
streaming:
  chunk_size: 1000
  max_concurrent_chunks: 5
  backpressure_threshold: 10
  
  file_readers:
    csv:
      encoding: "utf-8"
      delimiter: ","
      quote_char: '"'
    jsonl:
      encoding: "utf-8"
    tsv:
      encoding: "utf-8"
      delimiter: "\t"
  
  memory_management:
    max_memory_mb: 2048
    gc_frequency: 1000  # chunks
    
  error_handling:
    max_errors_per_chunk: 10
    continue_on_error: true
    error_output_path: "errors.jsonl"
```

## Performance Monitoring

```python
class StreamingMetrics:
    """Metrics collection for streaming pipeline."""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {
            "throughput": [],
            "memory_usage": [],
            "error_rates": []
        }
    
    async def collect_metrics(self, pipeline: StreamPipeline):
        """Collect real-time metrics."""
        while True:
            stats = pipeline.get_stats()
            
            # Calculate throughput
            if self.start_time:
                elapsed = time.time() - self.start_time
                throughput = stats["items_processed"] / elapsed
                self.metrics["throughput"].append(throughput)
            
            # Memory usage
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            self.metrics["memory_usage"].append(memory_mb)
            
            # Error rate
            if stats["chunks_processed"] > 0:
                error_rate = stats["errors"] / stats["chunks_processed"]
                self.metrics["error_rates"].append(error_rate)
            
            await asyncio.sleep(5)  # Collect every 5 seconds
```

## Benefits

1. **Memory Efficiency**: Process datasets larger than available memory
2. **Scalability**: Handle millions of records with constant memory usage
3. **Parallelism**: Concurrent chunk processing with backpressure control
4. **Fault Tolerance**: Continue processing despite individual record errors
5. **Modularity**: Pluggable processors for different transformation steps
6. **Monitoring**: Real-time metrics and progress tracking

## Next Steps

- Implement distributed streaming across multiple workers
- Add support for streaming from cloud storage (S3, GCS)
- Create streaming validation and quality control
- Build real-time streaming dashboard
- Optimize for specific biological file formats (FASTA, VCF, etc.)