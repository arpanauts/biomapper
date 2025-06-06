# CSV Adapter Usage Guide

The `CSVAdapter` is a powerful component for extracting identifiers from CSV endpoint values and loading CSV data with advanced caching and selective column loading capabilities.

## Overview

The `CSVAdapter` provides two main functionalities:
1. **ID Extraction**: Extract specific ontology identifiers from string values (e.g., HMDB IDs, ChEBI IDs)
2. **CSV Data Loading**: Load CSV files with optional column selection and intelligent caching

## Basic Usage

### Initialization

```python
from biomapper.mapping.adapters.csv_adapter import CSVAdapter

# Basic initialization (uses default settings)
adapter = CSVAdapter()

# Initialize with custom cache size
adapter = CSVAdapter(cache_max_size=20)

# Initialize with configuration and endpoint
adapter = CSVAdapter(
    config={'custom_setting': 'value'},
    resource_name='my_adapter',
    endpoint=my_endpoint
)
```

### ID Extraction

```python
import asyncio

async def extract_example():
    adapter = CSVAdapter()
    
    # Extract HMDB ID from a string
    result = await adapter.extract_ids(
        value="HMDB0000001",
        endpoint_id=1,
        ontology_type="hmdb"
    )
    print(result)
    # Output: [{'id': 'HMDB0000001', 'ontology_type': 'hmdb', 'confidence': 1.0}]
    
    # Get supported extraction types
    supported = adapter.get_supported_extractions(endpoint_id=1)
    print(f"Supported types: {supported}")

# Run the example
asyncio.run(extract_example())
```

## CSV Data Loading

### Loading All Columns

```python
import asyncio

async def load_all_columns():
    adapter = CSVAdapter()
    
    # Load all columns from a CSV file
    data = await adapter.load_data(file_path='data/metabolites.csv')
    print(f"Loaded {len(data)} rows with {len(data.columns)} columns")
    print(f"Columns: {list(data.columns)}")

asyncio.run(load_all_columns())
```

### Selective Column Loading

One of the key features of `CSVAdapter` is its ability to load only specific columns, which can significantly improve memory usage and performance for large files.

```python
import asyncio

async def selective_loading_example():
    adapter = CSVAdapter()
    
    # Load only specific columns
    data = await adapter.load_data(
        file_path='data/metabolites.csv',
        columns_to_load=['compound_id', 'hmdb_id', 'name']
    )
    print(f"Loaded {len(data)} rows with only {len(data.columns)} columns")
    print(data.head())
    
    # The adapter handles missing columns gracefully
    data_with_missing = await adapter.load_data(
        file_path='data/metabolites.csv',
        columns_to_load=['compound_id', 'nonexistent_column', 'name']
    )
    # Only existing columns will be loaded, warning logged for missing ones

asyncio.run(selective_loading_example())
```

### Using with Endpoints

```python
import asyncio
from unittest.mock import Mock

async def endpoint_example():
    # Mock endpoint with file path
    mock_endpoint = Mock()
    mock_endpoint.file_path = 'data/metabolites.csv'
    
    adapter = CSVAdapter(endpoint=mock_endpoint)
    
    # Load data using endpoint's file path
    data = await adapter.load_data(columns_to_load=['compound_id', 'name'])
    print(f"Loaded from endpoint: {len(data)} rows")

asyncio.run(endpoint_example())
```

## Caching Benefits

The `CSVAdapter` uses an LRU (Least Recently Used) cache to improve performance on repeated data loads.

```python
import asyncio
import time

async def caching_example():
    adapter = CSVAdapter(cache_max_size=5)
    
    # First load - reads from file
    start_time = time.time()
    data1 = await adapter.load_data(
        file_path='data/metabolites.csv',
        columns_to_load=['compound_id', 'name']
    )
    first_load_time = time.time() - start_time
    print(f"First load took: {first_load_time:.4f} seconds")
    
    # Second load - comes from cache
    start_time = time.time()
    data2 = await adapter.load_data(
        file_path='data/metabolites.csv',
        columns_to_load=['compound_id', 'name']
    )
    second_load_time = time.time() - start_time
    print(f"Second load took: {second_load_time:.4f} seconds")
    
    # Verify data is identical
    assert data1.equals(data2)
    print("Data from cache is identical to original")

asyncio.run(caching_example())
```

## Performance Monitoring

The `CSVAdapter` includes built-in performance monitoring to track cache effectiveness.

```python
import asyncio

async def monitoring_example():
    adapter = CSVAdapter()
    
    # Perform some operations
    await adapter.load_data('data/file1.csv', columns_to_load=['col1', 'col2'])
    await adapter.load_data('data/file1.csv', columns_to_load=['col1', 'col2'])  # Cache hit
    await adapter.load_data('data/file2.csv', columns_to_load=['col1', 'col2'])  # Cache miss
    
    # Get performance statistics
    stats = adapter.get_cache_stats()
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Cache misses: {stats['cache_misses']}")
    print(f"Hit rate: {stats['hit_rate']:.2%}")
    print(f"Total requests: {stats['total_requests']}")
    
    # Get cache information
    info = adapter.get_cache_info()
    print(f"Current cache size: {info['cache_size']}/{info['max_size']}")
    print(f"Cached files: {len(info['cached_files'])}")

asyncio.run(monitoring_example())
```

## Configuration

### Using Application Settings

The cache size can be configured through the application settings:

```python
# In your .env file or environment variables
CSV_ADAPTER_CACHE_SIZE=25

# Or modify the settings programmatically
from biomapper.config import get_settings

settings = get_settings()
print(f"Default cache size: {settings.csv_adapter_cache_size}")
```

### Cache Management

```python
async def cache_management():
    adapter = CSVAdapter(cache_max_size=3)
    
    # Load multiple files to demonstrate cache eviction
    await adapter.load_data('file1.csv', columns_to_load=['col1'])
    await adapter.load_data('file2.csv', columns_to_load=['col1'])
    await adapter.load_data('file3.csv', columns_to_load=['col1'])
    print(f"Cache size: {adapter.get_cache_info()['cache_size']}")  # Should be 3
    
    # Add another file - will evict least recently used
    await adapter.load_data('file4.csv', columns_to_load=['col1'])
    print(f"Cache size: {adapter.get_cache_info()['cache_size']}")  # Still 3
    
    # Clear cache manually
    adapter.clear_cache()
    print(f"Cache size after clear: {adapter.get_cache_info()['cache_size']}")  # 0
    
    # Performance counters are also reset
    stats = adapter.get_cache_stats()
    print(f"Stats after clear: {stats}")

asyncio.run(cache_management())
```

## Error Handling

The `CSVAdapter` provides robust error handling for common scenarios:

```python
import asyncio

async def error_handling_example():
    adapter = CSVAdapter()
    
    try:
        # File not found
        await adapter.load_data(file_path='nonexistent.csv')
    except FileNotFoundError:
        print("Handled file not found error")
    
    try:
        # No file path and no endpoint
        await adapter.load_data()
    except ValueError as e:
        print(f"Handled missing file path: {e}")
    
    try:
        # All requested columns don't exist
        await adapter.load_data(
            file_path='data/metabolites.csv',
            columns_to_load=['nonexistent1', 'nonexistent2']
        )
    except ValueError as e:
        print(f"Handled missing columns: {e}")

asyncio.run(error_handling_example())
```

## Best Practices

1. **Use Selective Loading**: When working with large CSV files, always specify `columns_to_load` to reduce memory usage.

2. **Monitor Cache Performance**: Use `get_cache_stats()` to monitor cache effectiveness and adjust cache size if needed.

3. **Configure Cache Size**: Set an appropriate cache size based on your application's memory constraints and usage patterns.

4. **Handle Errors Gracefully**: Always wrap CSV loading operations in try-catch blocks to handle file not found and parsing errors.

5. **Clear Cache When Needed**: Clear the cache when you know the underlying data has changed or when memory usage becomes a concern.

## Complete Example

Here's a complete example that demonstrates all major features:

```python
import asyncio
import pandas as pd
from biomapper.mapping.adapters.csv_adapter import CSVAdapter

async def complete_example():
    # Initialize with custom cache size
    adapter = CSVAdapter(cache_max_size=10)
    
    try:
        # Load data with selective columns
        metabolites = await adapter.load_data(
            file_path='data/metabolites.csv',
            columns_to_load=['compound_id', 'hmdb_id', 'name', 'molecular_weight']
        )
        print(f"Loaded {len(metabolites)} metabolites")
        
        # Extract IDs from compound names
        for _, row in metabolites.head().iterrows():
            hmdb_result = await adapter.extract_ids(
                value=row['hmdb_id'],
                endpoint_id=1,
                ontology_type='hmdb'
            )
            if hmdb_result:
                print(f"Extracted HMDB ID: {hmdb_result[0]['id']}")
        
        # Load same data again (should be cached)
        metabolites_cached = await adapter.load_data(
            file_path='data/metabolites.csv',
            columns_to_load=['compound_id', 'hmdb_id', 'name', 'molecular_weight']
        )
        
        # Check performance
        stats = adapter.get_cache_stats()
        print(f"Cache performance: {stats['hit_rate']:.1%} hit rate")
        print(f"Total requests: {stats['total_requests']}")
        
    except Exception as e:
        print(f"Error: {e}")

# Run the complete example
asyncio.run(complete_example())
```

This guide covers all the major features and use cases of the `CSVAdapter`. For more advanced usage or integration with specific mapping workflows, refer to the other mapping tutorials in this documentation.