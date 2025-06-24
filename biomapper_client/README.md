# Biomapper Python Client SDK

A simple, asynchronous Python client SDK for interacting with the Biomapper API.

## Installation

### From Source

To install the client from source:

```bash
# Clone the repository or navigate to the biomapper_client directory
cd biomapper_client

# Install using pip
pip install .

# Or install in development mode
pip install -e .

# If using Poetry
poetry install
```

### Dependencies

The client requires:
- Python 3.8+
- httpx
- pydantic

## Usage

### Basic Example

```python
import asyncio
from biomapper_client import BiomapperClient

async def main():
    # Create a client instance
    async with BiomapperClient(base_url="http://localhost:8000") as client:
        # Execute a strategy
        context = {
            "data": {
                "composite_ids": ["ABC123_XYZ", "DEF456_UVW"],
                "separator": "_"
            }
        }
        
        result = await client.execute_strategy(
            strategy_name="composite_id_splitter",
            context=context
        )
        
        print(f"Strategy result: {result}")

# Run the async function
asyncio.run(main())
```

### Error Handling

The client provides specific exception types for different error scenarios:

```python
import asyncio
from biomapper_client import BiomapperClient, ApiError, NetworkError

async def main():
    async with BiomapperClient() as client:
        try:
            result = await client.execute_strategy(
                strategy_name="my_strategy",
                context={"key": "value"}
            )
            print(f"Success: {result}")
            
        except ApiError as e:
            print(f"API Error (status {e.status_code}): {e}")
            print(f"Response body: {e.response_body}")
            
        except NetworkError as e:
            print(f"Network Error: {e}")
            
        except Exception as e:
            print(f"Unexpected error: {e}")

asyncio.run(main())
```

### Custom Base URL

You can specify a custom base URL when creating the client:

```python
# Connect to a remote Biomapper API
async with BiomapperClient(base_url="https://api.biomapper.example.com") as client:
    result = await client.execute_strategy("my_strategy", {"data": "value"})
```

### Manual Client Management

If you need more control over the client lifecycle:

```python
client = BiomapperClient()
await client.__aenter__()  # Initialize the client

try:
    result = await client.execute_strategy("my_strategy", {})
finally:
    await client.__aexit__(None, None, None)  # Clean up
```

## API Reference

### BiomapperClient

#### Constructor

```python
BiomapperClient(base_url: str = "http://localhost:8000")
```

- `base_url`: The base URL of the Biomapper API server

#### Methods

##### execute_strategy

```python
async def execute_strategy(strategy_name: str, context: Dict[str, Any]) -> Dict[str, Any]
```

Execute a strategy on the Biomapper API.

**Parameters:**
- `strategy_name`: The name of the strategy to execute
- `context`: The context dictionary to pass to the strategy

**Returns:**
- The response from the API as a dictionary

**Raises:**
- `ApiError`: If the API returns a non-200 status code
- `NetworkError`: If there are network-related issues
- `BiomapperClientError`: For other client-related errors

## Development

### Running Tests

```bash
# Install development dependencies
poetry install

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=biomapper_client
```

### Code Quality

```bash
# Format code
poetry run black biomapper_client

# Lint code
poetry run ruff check biomapper_client

# Type checking
poetry run mypy biomapper_client
```

## License

This project is part of the Biomapper ecosystem.