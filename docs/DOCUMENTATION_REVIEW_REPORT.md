# Biomapper Documentation Review Report

## Executive Summary

After reviewing all tutorials and user guides in the biomapper documentation, I've identified several critical issues that need to be addressed:

1. **Outdated API Usage**: The main usage guide references a non-existent synchronous API
2. **Incomplete Tutorials**: Multiple tutorials have placeholder content
3. **Inconsistent Code Examples**: Mix of async and sync patterns without clear guidance
4. **Missing CLI Documentation**: No comprehensive CLI command reference

## Critical Issues

### 1. `/docs/source/usage.rst` - Major API Misalignment

**Problem**: The entire usage guide uses a synchronous API that doesn't exist:
```python
from biomapper.core.mapping_executor import MappingExecutor
executor = MappingExecutor()  # Wrong - requires builder and is async
results = executor.execute_mapping(...)  # Wrong - method is async
```

**Reality**: The actual `MappingExecutor` requires:
- Complex initialization via `MappingExecutorBuilder`
- All methods are async (require `await`)
- Different method signatures than documented

**Recommendation**: Complete rewrite needed to show actual async usage patterns.

### 2. `/docs/source/guides/getting_started.md` - Incorrect Installation and API

**Problems**:
- References non-existent `MetaboliteNameMapper` class
- Shows `pip install biomapper` but project uses Poetry
- Import paths don't match actual codebase structure

**Recommendation**: Update to show Poetry installation and real API usage.

### 3. Placeholder Tutorials

The following tutorials contain only placeholder text:
- `/docs/source/tutorials/protein.md`
- `/docs/source/tutorials/llm_mapper.md`

**Recommendation**: Either complete these tutorials or remove them until ready.

### 4. `/docs/tutorials/yaml_mapping_strategies.md` - Async/Sync Confusion

**Problem**: Shows synchronous code but references async methods:
```python
# Document shows:
executor = MappingExecutor()
result = await executor.execute_yaml_strategy(...)  # Mixing sync/async
```

**Recommendation**: Clarify async patterns and show complete async examples.

## Positive Findings

### Well-Written Documentation:
1. **`/docs/source/tutorials/csv_adapter_usage.md`** - Comprehensive, accurate async examples
2. **`/docs/source/tutorials/name_resolution_clients.md`** - Clear setup instructions and usage patterns
3. **`/docs/source/tutorials/translator_name_resolver_usage.md`** - Good practical examples

## Specific Recommendations

### 1. Update Main Usage Guide (`usage.rst`)

Replace current examples with actual working code:
```python
import asyncio
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder

async def main():
    # Build executor with proper configuration
    builder = MappingExecutorBuilder(config={...})
    executor = builder.build()
    
    # Initialize resources
    await executor.initialize()
    
    # Execute mapping
    results = await executor.execute_mapping(
        identifiers=["BRCA1", "TP53"],
        source_ontology="gene_name",
        target_ontology="uniprot",
        options={}
    )
    
    # Cleanup
    await executor.cleanup()

asyncio.run(main())
```

### 2. Create CLI Reference Documentation

Add comprehensive CLI documentation showing actual commands:
```bash
# Health commands
poetry run biomapper health check-endpoint <endpoint_name>
poetry run biomapper health list-endpoints

# Metadata commands
poetry run biomapper metadata list
poetry run biomapper metadata show <resource_id>

# Metamapper commands
poetry run biomapper metamapper list-strategies
poetry run biomapper metamapper execute <strategy_name>
```

### 3. Fix Installation Instructions

Update all installation references to use Poetry:
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Clone repository
git clone https://github.com/arpanauts/biomapper.git
cd biomapper

# Install dependencies
poetry install --with dev,docs,api

# Activate environment
poetry shell
```

### 4. Add Configuration Examples

Show real configuration patterns from the codebase:
```yaml
# Strategy configuration example
mapping_strategies:
  protein_mapping:
    steps:
      - action: "CONVERT_IDENTIFIERS_LOCAL"
        parameters:
          source_column: "gene_name"
          target_column: "uniprot_ac"
```

### 5. Complete or Remove Placeholder Tutorials

Either:
- Complete the protein.md and llm_mapper.md tutorials with real content
- Remove them from the documentation until they're ready
- Add a "Coming Soon" notice if they're planned

## Testing Recommendations

1. **Add Documentation Tests**: Create pytest fixtures that validate code examples
2. **CI Integration**: Add documentation linting to CI/CD pipeline
3. **Version Pinning**: Ensure examples specify compatible biomapper versions

## Priority Action Items

1. **HIGH**: Fix usage.rst - it's the main entry point and completely wrong
2. **HIGH**: Update getting_started.md with correct installation and imports
3. **MEDIUM**: Complete or remove placeholder tutorials
4. **MEDIUM**: Add comprehensive CLI documentation
5. **LOW**: Add more async/await examples throughout all tutorials

## Conclusion

While some tutorials (CSV adapter, name resolution) are well-written, the core usage documentation is fundamentally incorrect and will frustrate users. The mix of placeholder content and outdated examples significantly impacts the documentation quality. Immediate action is needed on the high-priority items to ensure users can successfully use biomapper.