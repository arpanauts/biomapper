# Biomapper Generalized Action Types Roadmap

This directory contains detailed specifications for each proposed generalized action type. Each action is designed following the principles outlined in [00_OVERARCHING_PRINCIPLES.md](./00_OVERARCHING_PRINCIPLES.md).

## Document Structure

Each action type document follows this template:
1. **Overview**: Purpose and use cases
2. **Design Decisions**: Key architectural choices
3. **Implementation Details**: Pydantic models, algorithms
4. **Performance Characteristics**: Benchmarks, limitations
5. **Error Scenarios**: Common failures and recovery
6. **Testing Strategy**: TDD approach, test cases
7. **Examples**: Real-world usage with sample data
8. **Integration Notes**: How it fits with other actions

## Action Type Categories

### Foundation Components (Phase 0)
Infrastructure patterns and utilities that all actions incorporate:

- [01_STREAMING_DATA_PROCESSOR.md](./01_STREAMING_DATA_PROCESSOR.md) - Base class for memory-efficient data processing
- [02_ERROR_HANDLING_PATTERNS.md](./02_ERROR_HANDLING_PATTERNS.md) - Error handling patterns all actions must implement
- [03_PARSER_PLUGIN_ARCHITECTURE.md](./03_PARSER_PLUGIN_ARCHITECTURE.md) - Extensible biological identifier parsing system
- [04_CONFIGURATION_DRIVEN_NORMALIZATION.md](./04_CONFIGURATION_DRIVEN_NORMALIZATION.md) - Declarative data transformation rules
- [05_GRAPH_CROSS_REFERENCE_RESOLVER.md](./05_GRAPH_CROSS_REFERENCE_RESOLVER.md) - Neo4j-based relationship discovery
- [06_STREAMING_INFRASTRUCTURE.md](./06_STREAMING_INFRASTRUCTURE.md) - Core streaming pipeline components

### Data Loading Actions
Actions for ingesting and parsing various data formats:

- [10_LOAD_DATASET_IDENTIFIERS.md](./10_LOAD_DATASET_IDENTIFIERS.md) - Generic CSV/TSV loader
- [11_PARSE_COMPOSITE_IDENTIFIERS.md](./11_PARSE_COMPOSITE_IDENTIFIERS.md) - Split composite IDs
- [12_EXTRACT_CROSS_REFERENCES.md](./12_EXTRACT_CROSS_REFERENCES.md) - Parse xref columns

### Mapping & Resolution Actions
Core mapping operations across entity types:

- [20_RESOLVE_HISTORICAL_IDENTIFIERS.md](./20_RESOLVE_HISTORICAL_IDENTIFIERS.md) - Generic historical resolution
- [21_MAP_VIA_CROSS_REFERENCE.md](./21_MAP_VIA_CROSS_REFERENCE.md) - Indirect mapping through common references
- [22_FUZZY_NAME_MATCH.md](./22_FUZZY_NAME_MATCH.md) - String similarity matching

### Analysis Actions
Set operations and statistical analysis:

- [30_CALCULATE_SET_OVERLAP.md](./30_CALCULATE_SET_OVERLAP.md) - Comprehensive set analysis
- [31_AGGREGATE_ONE_TO_MANY.md](./31_AGGREGATE_ONE_TO_MANY.md) - Handle one-to-many mappings
- [32_RANK_MAPPING_CANDIDATES.md](./32_RANK_MAPPING_CANDIDATES.md) - Score and rank options

### Reporting Actions
Output generation and metrics:

- [40_GENERATE_MAPPING_REPORT.md](./40_GENERATE_MAPPING_REPORT.md) - Standardized CSV outputs
- [41_CALCULATE_MAPPING_METRICS.md](./41_CALCULATE_MAPPING_METRICS.md) - Performance metrics
- [42_CREATE_PROVENANCE_TRACE.md](./42_CREATE_PROVENANCE_TRACE.md) - Audit trails

### Validation Actions
Quality checks and verification:

- [50_VALIDATE_IDENTIFIER_FORMAT.md](./50_VALIDATE_IDENTIFIER_FORMAT.md) - ID pattern validation
- [51_DETECT_MAPPING_CONFLICTS.md](./51_DETECT_MAPPING_CONFLICTS.md) - Find inconsistencies
- [52_ASSESS_DATA_QUALITY.md](./52_ASSESS_DATA_QUALITY.md) - Data quality metrics

### Advanced Actions (Future)
Complex operations building on foundation:

- [60_PARALLEL_PROCESS.md](./60_PARALLEL_PROCESS.md) - Concurrent execution
- [61_CONDITIONAL_BRANCH.md](./61_CONDITIONAL_BRANCH.md) - Dynamic routing
- [62_EXTERNAL_API_CALL.md](./62_EXTERNAL_API_CALL.md) - Generic API wrapper

## Implementation Timeline

### Week 1-2: Foundation (Phase 0)
- Streaming infrastructure
- Error handling framework
- Caching layer
- Entity registry

### Week 3-4: Core Actions
- Essential data loaders
- Basic mapping actions
- Simple analysis actions

### Week 5-6: Advanced Actions
- Complex mapping operations
- Comprehensive reporting
- Validation suite

### Week 7-8: Integration & Polish
- Performance optimization
- Documentation completion
- LIH demo preparation

## Usage Guidelines

1. **For Developers**: Start with the overarching principles, then review specific actions you need to implement
2. **For LLM Agents**: Use these specifications as authoritative references when implementing or modifying actions
3. **For Testing**: Each action spec includes comprehensive test scenarios
4. **For Integration**: Check integration notes to understand action dependencies

## Quick Reference

### Most Used Actions
1. `LOAD_DATASET_IDENTIFIERS` - Starting point for most pipelines
2. `CALCULATE_SET_OVERLAP` - Core analysis operation
3. `GENERATE_MAPPING_REPORT` - Standard output format

### Performance Critical Actions
1. `STREAMING_DATA_PROCESSOR` - For large datasets
2. `CACHE_MANAGER` - For expensive operations
3. `PARALLEL_PROCESS` - For computational bottlenecks

### Entity-Agnostic Actions
All actions in this roadmap are designed to work across entity types through the Entity Behavior Registry pattern.

## Contributing

When adding new action specifications:
1. Follow the document template
2. Include comprehensive examples
3. Define clear performance targets
4. Specify all error scenarios
5. Add to appropriate category in this index