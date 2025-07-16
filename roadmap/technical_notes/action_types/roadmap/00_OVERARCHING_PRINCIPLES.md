# Biomapper Generalized Action Types: Overarching Principles

## Purpose
This document serves as the authoritative reference for LLM agents and developers implementing generalized action types for Biomapper. It defines core principles, patterns, and requirements that ALL action types must follow.

## Core Design Principles

### 1. True Generalization Over Entity-Specific Implementation
- **Principle**: Actions must work across ALL entity types (proteins, metabolites, genes, clinical labs, etc.)
- **Implementation**: Use entity behavior registries and plugins rather than hardcoding entity logic
- **Foundation**: Leverage Parser Plugin Architecture ([03_PARSER_PLUGIN_ARCHITECTURE.md](./03_PARSER_PLUGIN_ARCHITECTURE.md)) and Configuration-Driven Normalization ([04_CONFIGURATION_DRIVEN_NORMALIZATION.md](./04_CONFIGURATION_DRIVEN_NORMALIZATION.md))
- **Anti-pattern**: `if entity_type == 'protein': do_protein_specific_thing()`
- **Correct pattern**: `handler = registry.get_handler(entity_type, behavior)`

### 2. Performance-First Design
- **Streaming by Default**: All data loading actions must support streaming for large datasets using Streaming Infrastructure ([06_STREAMING_INFRASTRUCTURE.md](./06_STREAMING_INFRASTRUCTURE.md))
- **Batch Processing**: Configurable batch sizes for all operations
- **Memory Management**: Explicit memory limits and monitoring
- **Graph Resolution**: Leverage Graph Cross-Reference Resolver ([05_GRAPH_CROSS_REFERENCE_RESOLVER.md](./05_GRAPH_CROSS_REFERENCE_RESOLVER.md)) for complex relationship discovery
- **Caching Strategy**: Built-in caching for expensive operations with TTL management
- **Async Operations**: Leverage async/await for I/O-bound operations

### 3. Robust Error Handling
- **Partial Success**: Actions must support partial success scenarios
- **Error Thresholds**: Configurable error tolerance (e.g., allow up to 20% failures)
- **Recovery Patterns**: Built-in retry logic with exponential backoff
- **Circuit Breakers**: Protect against cascading failures from external services
- **Detailed Error Reporting**: Capture error context, not just error messages

### 4. Type Safety & Validation
- **Pydantic Models**: All action parameters and results as typed models
- **Runtime Validation**: Validate inputs before processing
- **Clear Contracts**: Well-defined input/output schemas
- **Backward Compatibility**: Maintain dict interfaces during migration

### 5. Comprehensive Observability
- **Structured Logging**: Use structured logging with correlation IDs
- **Metrics Collection**: Built-in performance metrics (latency, throughput, error rates)
- **Provenance Tracking**: Detailed audit trail for every transformation
- **Progress Reporting**: Real-time progress for long-running operations

## Implementation Patterns

### Action Base Class Structure
```python
from typing import Generic, TypeVar, AsyncIterator
from pydantic import BaseModel
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction

TParams = TypeVar('TParams', bound=BaseModel)
TResult = TypeVar('TResult', bound=BaseModel)
TChunk = TypeVar('TChunk', bound=BaseModel)

class GeneralizedAction(TypedStrategyAction[TParams, TResult], Generic[TParams, TResult]):
    """Base for all generalized actions."""
    
    async def execute_typed(self, params: TParams, context: ExecutionContext) -> TResult:
        """Standard execution for complete processing."""
        pass
    
    async def stream_execute(self, params: TParams, context: ExecutionContext) -> AsyncIterator[TChunk]:
        """Streaming execution for large datasets."""
        pass
    
    def validate_params(self, params: TParams) -> None:
        """Additional validation beyond Pydantic."""
        pass
```

### Entity Behavior Registry Pattern
```python
class EntityBehaviorRegistry:
    """Registry for entity-specific behaviors."""
    
    def register(self, entity_type: str, behavior: str, handler: Callable):
        """Register a behavior handler for an entity type."""
    
    def get_handler(self, entity_type: str, behavior: str) -> Callable:
        """Get the appropriate handler, with fallback to default."""
```

### Error Handling Pattern
```python
class ActionResult(BaseModel):
    status: Literal['success', 'partial_success', 'failure']
    processed_count: int
    error_count: int
    errors: List[ErrorDetail]
    warnings: List[str]
    data: Dict[str, Any]
    metrics: PerformanceMetrics
```

## Required Components for Each Action

### 1. Parameter Model
```python
class MyActionParams(BaseModel):
    # Required parameters
    input_source: str
    
    # Performance parameters
    batch_size: int = Field(default=1000, ge=1, le=10000)
    memory_limit_mb: int = Field(default=500, ge=100)
    
    # Error handling parameters
    continue_on_error: bool = True
    error_threshold: float = Field(default=0.1, ge=0, le=1)
    
    # Caching parameters
    use_cache: bool = True
    cache_ttl: int = Field(default=3600, ge=0)
```

### 2. Result Model
```python
class MyActionResult(ActionResult):
    # Action-specific results
    specific_data: Dict[str, Any]
    
    # Always include these
    provenance: List[ProvenanceRecord]
    performance_metrics: PerformanceMetrics
```

### 3. Comprehensive Tests
- Unit tests for happy path
- Error condition tests
- Performance/memory tests
- Integration tests with real data
- Streaming functionality tests

### 4. Documentation
- Dedicated markdown file in roadmap/
- Clear examples with real data
- Performance characteristics
- Error scenarios and recovery

## Development Workflow

### Phase 0: Foundation (Before Any Action Implementation)
1. Implement base infrastructure
   - Error handling framework
   - Streaming support utilities
   - Entity behavior registry
   - Caching layer
   - Performance monitoring

2. Create test utilities
   - Mock data generators
   - Performance benchmarking tools
   - Memory usage monitors

### For Each New Action Type
1. **Design Phase**
   - Write failing tests first (TDD)
   - Define Pydantic models
   - Document in roadmap/

2. **Implementation Phase**
   - Implement minimal code to pass tests
   - Add streaming support if applicable
   - Integrate error handling
   - Add caching where appropriate

3. **Optimization Phase**
   - Performance benchmarking
   - Memory profiling
   - Query optimization

4. **Integration Phase**
   - Update action registry
   - Create example strategies
   - Update documentation

## Performance Requirements

### Minimum Performance Standards
- **Throughput**: ≥10,000 identifiers/second for simple operations
- **Memory**: ≤500MB for 1M identifiers (streaming mode)
- **Latency**: ≤100ms startup overhead
- **Cache Hit Rate**: ≥80% for repeated operations
- **Error Recovery**: ≤3 retry attempts with exponential backoff

### Scalability Requirements
- Support datasets up to 100M identifiers
- Parallel processing capability
- Distributed execution ready (future)
- Cloud storage compatibility

## Security Considerations

### Input Validation
- Sanitize all file paths
- Validate file formats before processing
- Size limits on uploads
- Rate limiting for API calls

### Data Protection
- No sensitive data in logs
- Secure credential management
- Audit trail encryption
- GDPR compliance considerations

## Testing Requirements

### Test Coverage Targets
- Unit tests: ≥95% coverage
- Integration tests: All happy paths
- Performance tests: Memory and throughput
- Error scenario tests: All failure modes

### Test Data Requirements
- Use test data from `/home/trentleslie/Mapping Ontologies/test_data/`
- Create minimal reproducible examples
- Include edge cases in test data
- Document test data structure

## Migration Strategy

### Supporting Legacy Actions
1. Maintain backward compatibility during transition
2. Provide migration utilities
3. Deprecation warnings for old patterns
4. Phased rollout with feature flags

### Success Metrics
- 80% of strategies using new actions within 3 months
- Zero regression in performance
- 50% reduction in code duplication
- 90% test coverage maintained

## Common Pitfalls to Avoid

1. **Over-generalization**: Don't sacrifice clarity for reusability
2. **Premature Optimization**: Profile before optimizing
3. **Ignoring Memory**: Always consider memory usage
4. **Poor Error Messages**: Be specific and actionable
5. **Missing Streaming**: Large data requires streaming
6. **Coupling Actions**: Keep actions independent
7. **Skipping Tests**: TDD is mandatory

## References

- [Biomapper Architecture Guide](/docs/architecture/BIOMAPPER_ARCHITECTURE_GUIDE.md)
- [Strategy Actions CLAUDE.md](../CLAUDE.md)
- [Test Data README](/home/trentleslie/Mapping Ontologies/test_data/README.md)
- [Typed Strategy Actions Documentation](/docs/typed_strategy_actions.md)

## Revision History

- 2024-01-16: Initial version incorporating review feedback
- Focus on performance, error handling, and true generalization
- Added streaming and caching requirements
- Enhanced testing and documentation standards