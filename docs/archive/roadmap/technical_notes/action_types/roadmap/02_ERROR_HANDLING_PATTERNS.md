# ERROR_HANDLING_PATTERNS - Foundation Pattern

## Overview

This document defines error handling patterns that MUST be implemented within each action type. These are not separate actions but built-in capabilities that make each action robust and fault-tolerant.

### Purpose
- Standardize error handling across all actions
- Enable partial success scenarios
- Implement retry strategies with exponential backoff
- Provide circuit breaker protection for external services
- Capture detailed error context for debugging

### Use Cases
- API call failures and retries
- Partial dataset processing
- Graceful degradation strategies
- Error aggregation and reporting

## Design Decisions

### Key Patterns
1. **Error Boundaries**: Isolate failures to prevent cascade
2. **Retry Strategies**: Configurable retry with backoff
3. **Circuit Breakers**: Protect external dependencies
4. **Error Context**: Rich error information for debugging
5. **Partial Success**: Continue processing valid data

## Implementation Details

### Parameter Model
```python
class ErrorHandlerParams(BaseModel):
    """Parameters for error handling configuration."""
    
    # Error tolerance
    continue_on_error: bool = Field(default=True)
    error_threshold: float = Field(default=0.1, ge=0, le=1)
    fail_fast: bool = Field(default=False)
    
    # Retry configuration
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_ms: int = Field(default=1000)
    retry_backoff_factor: float = Field(default=2.0)
    retry_on_errors: List[str] = Field(
        default=["timeout", "connection", "rate_limit"]
    )
    
    # Circuit breaker
    circuit_breaker_enabled: bool = Field(default=True)
    circuit_breaker_threshold: int = Field(default=5)
    circuit_breaker_timeout_s: int = Field(default=60)
    
    # Error reporting
    capture_stack_trace: bool = Field(default=True)
    aggregate_similar_errors: bool = Field(default=True)
    max_error_details: int = Field(default=100)
```

### Error Models
```python
class ErrorDetail(BaseModel):
    """Detailed error information."""
    error_type: str
    error_message: str
    error_code: Optional[str]
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str]
    retry_count: int = 0
    
class ErrorSummary(BaseModel):
    """Aggregated error summary."""
    total_errors: int
    error_types: Dict[str, int]
    error_rate: float
    first_error_time: datetime
    last_error_time: datetime
    sample_errors: List[ErrorDetail]
```

### Core Implementation
```python
# This is NOT a separate action - it's a mixin/pattern for all actions
class ErrorHandlingMixin:
    """Mixin that all actions should incorporate."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        params: ErrorHandlerParams
    ) -> ErrorHandlingResult:
        """Handle an error with retry and circuit breaker logic."""
        
        error_detail = self._create_error_detail(error, context, params)
        
        # Check if retriable
        if self._is_retriable(error, params):
            retry_result = await self._retry_with_backoff(
                error, context, params
            )
            if retry_result.success:
                return retry_result
        
        # Check circuit breaker
        service = context.get('service_name', 'default')
        if params.circuit_breaker_enabled:
            breaker = self._get_circuit_breaker(service, params)
            if breaker.is_open:
                raise CircuitBreakerOpen(f"Circuit breaker open for {service}")
            breaker.record_failure()
        
        # Handle based on configuration
        if params.fail_fast:
            raise error
        elif params.continue_on_error:
            return ErrorHandlingResult(
                handled=True,
                error_detail=error_detail,
                should_continue=True
            )
        else:
            return ErrorHandlingResult(
                handled=False,
                error_detail=error_detail,
                should_continue=False
            )
    
    async def _retry_with_backoff(
        self,
        error: Exception,
        context: Dict[str, Any],
        params: ErrorHandlerParams
    ) -> RetryResult:
        """Implement exponential backoff retry."""
        
        for attempt in range(params.max_retries):
            delay = params.retry_delay_ms * (params.retry_backoff_factor ** attempt)
            await asyncio.sleep(delay / 1000)
            
            try:
                # Retry the operation
                result = await context['retry_function']()
                return RetryResult(success=True, result=result, attempts=attempt + 1)
            except Exception as e:
                if attempt == params.max_retries - 1:
                    return RetryResult(success=False, error=e, attempts=attempt + 1)
                continue
```

## Error Scenarios

### Supported Error Types
1. **Network Errors**: Timeout, connection refused
2. **API Errors**: Rate limits, authentication, 5xx errors
3. **Data Errors**: Parsing, validation, format issues
4. **Resource Errors**: Memory, disk space, permissions
5. **Logic Errors**: Business rule violations

### Recovery Examples
```python
# API rate limit with backoff
@with_error_handler(
    retry_on_errors=["RateLimitError"],
    max_retries=5,
    retry_backoff_factor=3.0
)
async def call_external_api(identifier):
    # API call implementation
    pass

# Partial success processing
async def process_batch(items, error_handler):
    successful = []
    failed = []
    
    for item in items:
        try:
            result = await process_item(item)
            successful.append(result)
        except Exception as e:
            handling_result = await error_handler.handle_error(e, {'item': item})
            if handling_result.should_continue:
                failed.append((item, handling_result.error_detail))
            else:
                raise
    
    return BatchResult(successful=successful, failed=failed)
```

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_retry_with_exponential_backoff():
    """Test retry logic with exponential backoff."""
    handler = ErrorHandler()
    attempt_times = []
    
    async def failing_operation():
        attempt_times.append(time.time())
        if len(attempt_times) < 3:
            raise TimeoutError("Service unavailable")
        return "success"
    
    result = await handler.handle_error(
        TimeoutError("Initial error"),
        {'retry_function': failing_operation},
        ErrorHandlerParams(max_retries=3, retry_delay_ms=100)
    )
    
    # Verify exponential backoff timing
    assert len(attempt_times) == 3
    assert attempt_times[1] - attempt_times[0] >= 0.1  # 100ms
    assert attempt_times[2] - attempt_times[1] >= 0.2  # 200ms

@pytest.mark.asyncio
async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    handler = ErrorHandler()
    params = ErrorHandlerParams(
        circuit_breaker_threshold=3,
        circuit_breaker_timeout_s=1
    )
    
    # Trigger circuit breaker
    for i in range(3):
        await handler.handle_error(
            ConnectionError("Service down"),
            {'service_name': 'test_api'},
            params
        )
    
    # Fourth call should fail immediately
    with pytest.raises(CircuitBreakerOpen):
        await handler.handle_error(
            ConnectionError("Service down"),
            {'service_name': 'test_api'},
            params
        )
```

## Examples

### YAML Configuration
```yaml
- action:
    type: MAP_VIA_API
    error_handler:
      continue_on_error: true
      error_threshold: 0.2
      max_retries: 5
      retry_delay_ms: 2000
      circuit_breaker_enabled: true
```

### Python Integration
```python
# Wrap any action with error handling
class MyAction(GeneralizedAction):
    async def execute_typed(self, params, context):
        error_handler = ErrorHandler()
        
        try:
            # Main logic
            result = await self.process_data(params.data)
        except Exception as e:
            handling_result = await error_handler.handle_error(
                e, context, params.error_handling
            )
            if not handling_result.should_continue:
                raise
            result = handling_result.partial_result
        
        return result
```

## Integration Notes

- All actions should integrate with ERROR_HANDLER
- Provides consistent error reporting across pipeline
- Enables graceful degradation strategies
- Circuit breakers prevent cascade failures

## Future Enhancements

1. **Error Classification ML**: Auto-classify error types
2. **Adaptive Retry**: Learn optimal retry strategies
3. **Distributed Circuit Breakers**: Share state across instances
4. **Error Correlation**: Identify related errors across pipeline
5. **Predictive Failure Detection**: Anticipate failures before they occur