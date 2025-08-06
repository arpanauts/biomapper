# Biomapper Client Library - Enhanced Edition

A comprehensive Python client library for the Biomapper API, providing simple synchronous methods, advanced async support, Jupyter notebook integration, and a powerful CLI.

## 🚀 Quick Start

### Installation

```bash
pip install biomapper-client
```

### Basic Usage

```python
from biomapper_client import BiomapperClient

# Simple one-line execution
client = BiomapperClient()
result = client.run("metabolomics_harmonization")

if result.success:
    print(f"✅ Success! Processed {result.statistics['total_records']} records")
else:
    print(f"❌ Failed: {result.error}")
```

## 📚 Features

### 1. Simple Synchronous Interface

Perfect for scripts and simple use cases:

```python
from biomapper_client import BiomapperClient

client = BiomapperClient()

# Run a named strategy
result = client.run("metabolomics_baseline")

# Run with parameters
result = client.run(
    "metabolomics_harmonization",
    parameters={"threshold": 0.9, "min_confidence": 0.8}
)

# Run from YAML file
result = client.run("path/to/strategy.yaml")

# Watch progress in real-time
result = client.run("long_running_strategy", watch=True)
```

### 2. Advanced Async Support

For high-performance applications:

```python
import asyncio
from biomapper_client import BiomapperClient

async def main():
    async with BiomapperClient() as client:
        # Start multiple jobs concurrently
        jobs = await asyncio.gather(
            client.execute_strategy("strategy1"),
            client.execute_strategy("strategy2"),
            client.execute_strategy("strategy3")
        )
        
        # Stream progress for a job
        async for event in client.stream_progress(jobs[0].id):
            print(f"[{event.percentage:.1f}%] {event.message}")
        
        # Wait for completion
        results = await asyncio.gather(
            *[client.wait_for_job(job.id) for job in jobs]
        )

asyncio.run(main())
```

### 3. Execution Context Builder

Build complex execution contexts fluently:

```python
from biomapper_client import BiomapperClient, ExecutionContext

context = (
    ExecutionContext()
    .add_parameter("threshold", 0.9)
    .add_parameter("min_samples", 100)
    .add_file("input_data", "/path/to/data.csv")
    .add_file("reference", "/path/to/reference.tsv")
    .set_output_dir("/results/output")
    .enable_checkpoints()  # Enable automatic checkpointing
    .enable_debug()        # Enable debug logging
    .set_timeout(3600)     # 1 hour timeout
)

client = BiomapperClient()
result = client.run("complex_strategy", context=context)
```

### 4. Progress Tracking

Multiple progress tracking backends:

```python
from biomapper_client import BiomapperClient

client = BiomapperClient()

# With tqdm progress bar
result = client.run_with_progress("my_strategy", use_tqdm=True)

# With custom callback
def progress_callback(current, total, message):
    print(f"Progress: {current}/{total} - {message}")

result = client.run_with_progress(
    "my_strategy",
    progress_callback=progress_callback
)

# Advanced progress tracker
from biomapper_client.progress import ProgressTracker

tracker = ProgressTracker(100, "Processing")
tracker.add_tqdm()           # Add tqdm backend
tracker.add_rich()           # Add rich backend
tracker.add_callback(my_callback)  # Add custom callback

# Use in your code
for i in range(100):
    tracker.update(f"Processing item {i}")
```

### 5. Jupyter Notebook Integration

Enhanced support for Jupyter notebooks:

```python
from biomapper_client import BiomapperClient
from biomapper_client.jupyter import JupyterExecutor

client = BiomapperClient()
executor = JupyterExecutor(client)

# Run with interactive progress widget
result = executor.run("metabolomics_harmonization", show_logs=True)

# Automatically displays results in notebook-friendly format
executor.display_results(result)

# Compare multiple strategies
results = {
    "baseline": executor.run("metabolomics_baseline"),
    "enhanced": executor.run("metabolomics_enhanced"),
    "ml_powered": executor.run("metabolomics_ml")
}

executor.display_strategy_comparison(
    results,
    metrics=["accuracy", "recall", "f1_score"]
)
```

#### Interactive Strategy Builder

Build strategies interactively in Jupyter:

```python
from biomapper_client.jupyter import InteractiveStrategyBuilder

builder = InteractiveStrategyBuilder()

# Build strategy step by step
(builder
    .add_action("LOAD_DATASET_IDENTIFIERS", "Load Input", 
                params={"file_path": "/data/input.csv"})
    .add_action("MERGE_WITH_UNIPROT_RESOLUTION", "Map to UniProt",
                params={"confidence_threshold": 0.9})
    .add_action("CALCULATE_SET_OVERLAP", "Calculate Overlap",
                params={"method": "jaccard"})
    .add_action("EXPORT_DATASET", "Export Results",
                params={"format": "csv", "output_path": "/results/"})
)

# Visualize the strategy flow
builder.visualize()

# Convert to YAML
yaml_strategy = builder.to_yaml()

# Execute the built strategy
client = BiomapperClient()
result = client.run(builder.build())
```

### 6. Command-Line Interface

Powerful CLI for automation:

```bash
# Run a strategy
biomapper run metabolomics_harmonization

# Run with parameters
biomapper run my_strategy -p '{"threshold": 0.9}'

# Run from YAML file with output directory
biomapper run strategy.yaml -o ./results

# Watch progress
biomapper run my_strategy --watch

# Run without waiting (returns job ID)
biomapper run my_strategy --no-wait

# Check job status
biomapper status job-123-456

# View logs
biomapper logs job-123-456

# Get results
biomapper results job-123-456 -o results.json

# Export as CSV
biomapper results job-123-456 --format csv -o results.csv

# Upload a file
biomapper upload data.csv

# Validate a strategy
biomapper validate strategy.yaml

# Check API health
biomapper health

# List available endpoints
biomapper endpoints
```

### 7. Error Handling

Comprehensive error handling with specific exceptions:

```python
from biomapper_client import BiomapperClient
from biomapper_client.exceptions import (
    StrategyNotFoundError,
    JobNotFoundError,
    TimeoutError,
    ExecutionError,
    ValidationError
)

client = BiomapperClient()

try:
    result = client.run("my_strategy")
except StrategyNotFoundError as e:
    print(f"Strategy not found: {e}")
except ValidationError as e:
    print(f"Invalid parameters: {e}")
except TimeoutError as e:
    print(f"Execution timed out: {e}")
except ExecutionError as e:
    print(f"Execution failed: {e}")
    print(f"Details: {e.details}")
```

### 8. File Operations

Upload and manage files:

```python
import asyncio
from biomapper_client import BiomapperClient

async def process_file():
    async with BiomapperClient() as client:
        # Upload a file
        upload_response = await client.upload_file("/path/to/data.csv")
        session_id = upload_response.session_id
        
        # Get column information
        columns = await client.get_file_columns(session_id)
        print(f"Columns: {columns.columns}")
        
        # Preview the file
        preview = await client.preview_file(session_id, rows=20)
        print(f"Preview: {preview.data[:5]}")
        
        # Use in strategy execution
        result = await client.execute_strategy(
            "process_uploaded_file",
            parameters={"session_id": session_id}
        )

asyncio.run(process_file())
```

### 9. Job Management

Full job lifecycle management:

```python
import asyncio
from biomapper_client import BiomapperClient

async def manage_jobs():
    async with BiomapperClient() as client:
        # Start a job
        job = await client.execute_strategy("long_running_strategy")
        
        # Check status
        status = await client.get_job_status(job.id)
        print(f"Status: {status.status}, Progress: {status.progress}%")
        
        # Get logs (when implemented)
        logs = await client.get_job_logs(job.id, tail=50)
        for entry in logs:
            print(f"[{entry.level}] {entry.message}")
        
        # Cancel if needed (when implemented)
        # await client.cancel_job(job.id)
        
        # Get results
        results = await client.get_job_results(job.id)

asyncio.run(manage_jobs())
```

## 🔧 Configuration

### Environment Variables

```bash
export BIOMAPPER_API_URL=http://localhost:8000
export BIOMAPPER_API_KEY=your-api-key
```

### Client Configuration

```python
client = BiomapperClient(
    base_url="http://api.example.com",
    api_key="your-api-key",
    timeout=600,  # 10 minutes
    auto_retry=True,
    max_retries=3
)
```

## 📖 API Reference

### BiomapperClient

#### Synchronous Methods

- `run(strategy, parameters=None, context=None, wait=True, watch=False)` - Run a strategy
- `run_with_progress(strategy, parameters=None, context=None, progress_callback=None, use_tqdm=True)` - Run with progress tracking

#### Async Methods

- `execute_strategy(strategy, parameters=None, context=None, options=None)` - Execute strategy asynchronously
- `wait_for_job(job_id, timeout=None, poll_interval=2)` - Wait for job completion
- `stream_progress(job_id)` - Stream progress events
- `get_job_status(job_id)` - Get job status
- `get_job_results(job_id)` - Get job results
- `upload_file(file_path, session_id=None)` - Upload a file
- `get_file_columns(session_id)` - Get file columns
- `preview_file(session_id, rows=10)` - Preview file contents
- `health_check()` - Check API health
- `list_endpoints()` - List API endpoints

### ExecutionContext

- `add_parameter(key, value)` - Add a parameter
- `add_file(key, path)` - Add an input file
- `set_output_dir(path)` - Set output directory
- `enable_checkpoints(interval)` - Enable checkpointing
- `enable_debug()` - Enable debug mode
- `set_timeout(seconds)` - Set execution timeout
- `to_request(strategy_name)` - Convert to request

### JupyterExecutor

- `run(strategy, parameters=None, context=None, show_logs=True, auto_display=True)` - Run with Jupyter widgets
- `display_results(result)` - Display results in notebook
- `display_strategy_comparison(results, metrics=None)` - Compare multiple results
- `create_progress_callback()` - Create progress callback

### ProgressTracker

- `add_tqdm(**kwargs)` - Add tqdm progress bar
- `add_rich(**kwargs)` - Add rich progress bar
- `add_callback(callback)` - Add custom callback
- `add_jupyter()` - Add Jupyter widgets
- `update(message=None, step=None, increment=1)` - Update progress
- `set_description(description)` - Update description
- `close()` - Close all backends

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=biomapper_client

# Run specific test file
pytest tests/test_client_v2.py

# Run async tests
pytest -m asyncio
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our repository.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- Documentation: https://biomapper.readthedocs.io
- Issues: https://github.com/your-org/biomapper-client/issues
- Discussions: https://github.com/your-org/biomapper-client/discussions

## 🎯 Roadmap

### Coming Soon

- [ ] WebSocket support for real-time progress streaming
- [ ] Job pause/resume functionality
- [ ] Strategy validation endpoint
- [ ] Batch job execution
- [ ] Result caching
- [ ] Retry policies for failed jobs
- [ ] Strategy templates
- [ ] Data visualization components

### Future Enhancements

- [ ] GraphQL API support
- [ ] gRPC client
- [ ] Kubernetes operator
- [ ] Workflow orchestration
- [ ] Multi-cloud support
- [ ] Federation capabilities