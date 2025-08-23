# BiomapperClient - Claude Code Instructions

## Overview
This directory contains the Python client for BiOMapper's FastAPI service. The client provides a clean interface for executing strategies without directly importing core libraries.

## Critical Rules
- **NO direct imports from core** - Client must remain independent
- **Always use async/await patterns** - Client is async-first
- **Handle SSE progress events** - Real-time updates are critical
- **Respect timeouts** - Default 3600s, configurable per strategy

## Common Tasks

### Running a Strategy
```python
# Simple synchronous wrapper
client = BiomapperClient()
result = client.run("strategy_name", parameters={"key": "value"})

# Full async with progress tracking
async def execute():
    client = BiomapperClient()
    async for event in client.execute_strategy_stream("strategy_name"):
        if event.type == ProgressEventType.STEP_COMPLETE:
            print(f"Step {event.step_name} completed")
```

### Error Handling Patterns
- `StrategyNotFoundError` - Check strategy exists in src/configs/strategies/
- `ValidationError` - Parameter validation failed, check YAML
- `TimeoutError` - Increase timeout or optimize strategy
- `NetworkError` - Check API server is running on port 8000

## Testing Requirements
- Mock httpx responses using respx (NOT responses library)
- Test both success and failure paths
- Verify SSE event parsing
- Check timeout handling

## Performance Considerations
- File uploads use chunked transfer for large datasets
- Progress events stream via SSE, don't buffer
- Connection pooling enabled by default
- Retry logic for transient failures

## DON'T
- Import from src.core or src.actions
- Use synchronous HTTP libraries
- Ignore progress events
- Hardcode API URLs (use BASE_URL env var)