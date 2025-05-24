# MVP0 Pipeline Orchestrator

## Overview

The MVP0 Pipeline Orchestrator implements a three-stage RAG (Retrieval-Augmented Generation) approach for mapping biochemical names to PubChem Compound IDs (CIDs). This pipeline is specifically designed for the Arivale BIOCHEMICAL_NAME mapping use case.

### Pipeline Stages

1. **Qdrant Vector Search**: Searches for similar compounds using embeddings in a Qdrant vector database
2. **PubChem Annotation**: Enriches candidate CIDs with detailed chemical information from PubChem API
3. **LLM Selection**: Uses Claude (Anthropic) to intelligently select the best matching CID based on context

## Architecture

```
biochemical_name
    |
    v
[Qdrant Search] --> candidate CIDs with similarity scores
    |
    v
[PubChem Annotator] --> enriched candidates with chemical details
    |
    v
[LLM Mapper] --> best matching CID with confidence and rationale
    |
    v
PipelineMappingResult
```

## Installation

The MVP0 pipeline is part of the biomapper package. Ensure you have the following dependencies:

```bash
pip install qdrant-client httpx anthropic pydantic pydantic-settings
```

## Configuration

The pipeline uses environment variables for configuration. Create a `.env` file or set these variables:

### Required Environment Variables

- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude access (required)

### Optional Environment Variables

- `QDRANT_URL`: URL for Qdrant vector database (default: "http://localhost:6333")
- `QDRANT_COLLECTION_NAME`: Name of the Qdrant collection (default: "pubchem_embeddings")
- `QDRANT_API_KEY`: API key for Qdrant authentication (default: None)
- `PUBCHEM_MAX_CONCURRENT_REQUESTS`: Max concurrent PubChem requests (default: 5)
- `LLM_MODEL_NAME`: Claude model to use (default: "claude-3-sonnet-20240229")
- `PIPELINE_BATCH_SIZE`: Number of names to process in parallel (default: 10)
- `PIPELINE_TIMEOUT_SECONDS`: Timeout per name in seconds (default: 300)

### Example .env file

```env
ANTHROPIC_API_KEY=your-anthropic-api-key-here
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=pubchem_bge_small_v1_5
```

## Usage

### Basic Usage

```python
import asyncio
from biomapper.mvp0_pipeline.pipeline_orchestrator import create_orchestrator

async def main():
    # Create orchestrator (uses environment variables)
    orchestrator = create_orchestrator()
    
    # Map a single biochemical name
    result = await orchestrator.run_single_mapping("glucose")
    
    print(f"Status: {result.status}")
    print(f"Selected CID: {result.selected_cid}")
    print(f"Confidence: {result.confidence}")
    print(f"Rationale: {result.rationale}")

# Run the async function
asyncio.run(main())
```

### Batch Processing

```python
async def batch_example():
    orchestrator = create_orchestrator()
    
    # Process multiple names
    names = ["glucose", "caffeine", "aspirin", "vitamin C"]
    batch_result = await orchestrator.run_pipeline(names)
    
    print(f"Processed: {batch_result.total_processed}")
    print(f"Successful: {batch_result.successful_mappings}")
    print(f"Success rate: {batch_result.get_success_rate():.1f}%")
    
    # Access individual results
    for result in batch_result.results:
        print(f"{result.input_biochemical_name} -> CID: {result.selected_cid}")
```

### Custom Configuration

```python
from biomapper.mvp0_pipeline.pipeline_config import PipelineConfig
from biomapper.mvp0_pipeline.pipeline_orchestrator import PipelineOrchestrator

# Create custom configuration
config = PipelineConfig(
    anthropic_api_key="your-key",
    qdrant_url="http://custom-qdrant:6333",
    qdrant_collection_name="my_collection",
    pipeline_batch_size=20
)

# Initialize orchestrator with custom config
orchestrator = PipelineOrchestrator(config)
```

## Understanding Results

### PipelineMappingResult

Each mapping produces a `PipelineMappingResult` with the following key fields:

- `input_biochemical_name`: The original input name
- `status`: Pipeline execution status (see Status Codes below)
- `selected_cid`: The chosen PubChem CID (if successful)
- `confidence`: Confidence level ("High", "Medium", "Low")
- `rationale`: LLM's explanation for the selection
- `qdrant_results`: Raw Qdrant search results
- `pubchem_annotations`: Retrieved PubChem data
- `llm_choice`: Detailed LLM decision
- `error_message`: Error details (if failed)
- `processing_details`: Timing information

### Pipeline Status Codes

The pipeline uses detailed status codes to indicate outcomes:

**Success States:**
- `SUCCESS`: Full pipeline success with confident mapping
- `PARTIAL_SUCCESS`: Pipeline completed but with caveats

**No Result States:**
- `NO_QDRANT_HITS`: No similar compounds found in vector search
- `INSUFFICIENT_ANNOTATIONS`: Candidates found but couldn't be annotated
- `LLM_NO_MATCH`: LLM evaluated candidates but found no good match

**Error States:**
- `COMPONENT_ERROR_QDRANT`: Error during Qdrant search
- `COMPONENT_ERROR_PUBCHEM`: Error during PubChem annotation
- `COMPONENT_ERROR_LLM`: Error during LLM evaluation
- `CONFIG_ERROR`: Configuration validation error
- `VALIDATION_ERROR`: Input validation error
- `UNKNOWN_ERROR`: Unexpected error

## Error Handling

The pipeline implements a "fail-fast" strategy for individual names:

```python
result = await orchestrator.run_single_mapping("test_compound")

if result.is_successful():
    print(f"Mapped to CID: {result.selected_cid}")
else:
    print(f"Mapping failed: {result.status}")
    print(f"Error: {result.error_message}")
```

## Performance Monitoring

The pipeline tracks processing times for each stage:

```python
result = await orchestrator.run_single_mapping("glucose")

print("Processing times:")
print(f"  Qdrant search: {result.processing_details['qdrant_search_time']:.2f}s")
print(f"  PubChem annotation: {result.processing_details['pubchem_annotation_time']:.2f}s")
print(f"  LLM decision: {result.processing_details['llm_decision_time']:.2f}s")
print(f"  Total: {result.processing_details['total_time']:.2f}s")
```

## Testing

Run the test suite:

```bash
pytest tests/mvp0_pipeline/test_pipeline_orchestrator.py -v
```

The test suite includes:
- Unit tests for all orchestrator methods
- Integration tests for component interactions
- Mock-based testing for external dependencies
- Error handling scenarios

## Troubleshooting

### Common Issues

1. **"ANTHROPIC_API_KEY is required"**
   - Set the `ANTHROPIC_API_KEY` environment variable
   - Or pass it explicitly in PipelineConfig

2. **"Failed to connect to Qdrant"**
   - Ensure Qdrant is running at the configured URL
   - Check if the collection exists
   - Verify network connectivity

3. **"No Qdrant hits"**
   - The biochemical name may not have similar compounds in the database
   - Check if the Qdrant collection is properly populated
   - Try variations of the compound name

4. **"PubChem API rate limit"**
   - Reduce `PUBCHEM_MAX_CONCURRENT_REQUESTS`
   - Add delays between batch processing

### Logging

Enable detailed logging to troubleshoot issues:

```python
import logging

# Set logging level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now run the orchestrator - detailed logs will be shown
```

## Future Enhancements

Currently planned improvements:
- Concurrent batch processing (currently sequential)
- Retry logic for transient failures
- Caching for repeated queries
- Progress callbacks for long-running batches
- Additional LLM providers beyond Anthropic

## Contributing

When contributing to the MVP0 pipeline:

1. Maintain the three-stage architecture
2. Add comprehensive tests for new features
3. Update this README with new functionality
4. Follow the existing code style and patterns
5. Ensure all tests pass before submitting