# Wrapper Script Migration Guide

## Overview

As part of the biomapper v2.0 release, all wrapper scripts have been refactored from complex orchestration scripts to simple API clients. This migration reduces code complexity, improves maintainability, and ensures all execution logic is centralized in the API server.

## What Changed

### Before: Complex Direct Execution (676+ lines)
- Scripts directly imported action classes
- Managed execution context and state
- Implemented prerequisite checking
- Handled Docker/Qdrant setup
- Complex error handling and retry logic

### After: Simple API Clients (<100 lines)
- Scripts only submit strategies to the API
- API handles all orchestration
- Unified CLI interface
- Consistent error handling

## Migration Table

| Old Script | Lines | New Script | Lines | CLI Command |
|------------|-------|------------|-------|-------------|
| `scripts/main_pipelines/run_metabolomics_harmonization.py` | 676 | `scripts/pipelines/run_metabolomics_harmonization.py` | 93 | `biomapper run metabolomics_progressive_enhancement` |
| `scripts/run_metabolomics_fix.py` | 239 | `scripts/pipelines/run_metabolomics_fix.py` | 57 | `biomapper run three_way_metabolomics` |
| `scripts/run_three_way_metabolomics.py` | 97 | `scripts/pipelines/run_three_way_metabolomics.py` | 13 | `biomapper run three_way_metabolomics_complete` |
| `scripts/run_three_way_simple.py` | 365 | `scripts/pipelines/run_three_way_simple.py` | 63 | `biomapper run three_way_metabolomics_simple` |

## How to Migrate Your Workflow

### Option 1: Use the New Unified CLI (Recommended)

```bash
# Install the biomapper client
pip install -e biomapper_client/

# Run strategies using the CLI
biomapper run metabolomics_progressive_enhancement
biomapper run three_way_metabolomics_complete --watch
biomapper run baseline_analysis --output-dir ./results

# Use shortcuts for common pipelines
biomapper metabolomics --skip-setup
biomapper three-way --output-dir ./my_results

# Check available strategies
biomapper list-strategies

# Check API health
biomapper health
```

### Option 2: Use the New Pipeline Scripts

```bash
# Run specific pipeline scripts
python scripts/pipelines/run_metabolomics_harmonization.py
python scripts/pipelines/run_three_way_metabolomics.py
python scripts/pipelines/run_three_way_simple.py --phase data_loading
```

### Option 3: Use Python API Client Directly

```python
from biomapper_client import BiomapperClient, run_strategy

# Simple execution
result = run_strategy("metabolomics_progressive_enhancement")

# With parameters
result = run_strategy(
    "three_way_metabolomics_complete",
    parameters={
        "output_dir": "./results",
        "skip_setup": True,
        "stage": "baseline"
    }
)

# Async execution with client
async def execute_pipeline():
    async with BiomapperClient() as client:
        result = await client.execute_strategy(
            "metabolomics_harmonization",
            context={"output_dir": "./results"}
        )
        return result
```

## Parameter Mapping

### run_metabolomics_harmonization.py

| Old Flag | New Parameter | Example |
|----------|---------------|---------|
| `--skip-setup` | `parameters.skip_setup` | `--parameters '{"skip_setup": true}'` |
| `--skip-qdrant` | `parameters.skip_qdrant` | `--parameters '{"skip_qdrant": true}'` |
| `--stage baseline` | `parameters.stage` | `--parameters '{"stage": "baseline"}'` |
| `--debug` | `--debug` flag | `--debug` |
| `--dry-run` | Not yet supported | Will be added in v2.1 |
| `--report-only` | `parameters.report_only` | `--parameters '{"report_only": true}'` |

### run_three_way_simple.py

| Old Implementation | New Parameter | Example |
|-------------------|---------------|---------|
| Phase-based execution | `parameters.phase` | `--parameters '{"phase": "nightingale"}'` |
| Dataset paths hardcoded | `parameters.datasets` | `--parameters '{"datasets": {...}}'` |
| Direct context management | Handled by API | No action needed |

## Features Temporarily Unavailable

The following features will be re-implemented in future versions:

1. **Real-time Progress Tracking** (v2.1)
   - WebSocket/SSE support for live updates
   - Progress bars with detailed step information

2. **Job Management** (v2.1)
   - `biomapper status <job_id>`
   - `biomapper cancel <job_id>`
   - Background job execution

3. **Dynamic Strategy Listing** (v2.0.1)
   - `biomapper list-strategies` with live API query
   - Strategy documentation retrieval

## Breaking Changes

### Removed Functionality
1. **Direct Action Imports**: Scripts can no longer import action classes directly
2. **Custom Pipeline Classes**: Pipeline orchestration classes have been removed
3. **Local Execution Context**: Context management is now handled by the API

### Changed Behavior
1. **YAML Loading**: Strategies are loaded by the API, not by wrapper scripts
2. **Error Handling**: Unified error handling through API responses
3. **Checkpoint Management**: Checkpointing is managed by the API

## Troubleshooting

### Common Issues

**Issue**: Old scripts show deprecation warnings
```bash
# Solution: Update to use new scripts or CLI
biomapper run metabolomics_progressive_enhancement
```

**Issue**: Custom parameters not working
```bash
# Solution: Pass parameters as JSON
biomapper run my_strategy --parameters '{"key": "value"}'
# Or use a file
biomapper run my_strategy --parameters params.json
```

**Issue**: Output directory not being created
```bash
# Solution: Specify output directory explicitly
biomapper run my_strategy --output-dir ./my_results
```

**Issue**: Strategy not found
```bash
# Solution: Check strategy name or provide full path
biomapper run ./configs/strategies/my_strategy.yaml
```

## Benefits of the New Architecture

1. **Reduced Complexity**: 90% reduction in wrapper script code
2. **Centralized Logic**: All orchestration in the API server
3. **Consistent Interface**: Unified CLI for all operations
4. **Better Testing**: Easier to test simple clients vs complex orchestrators
5. **Improved Maintainability**: Changes only needed in API, not multiple scripts
6. **Enhanced Debugging**: Centralized logging and error handling

## Migration Timeline

- **v1.9** (Current): Deprecation warnings added to old scripts
- **v2.0** (Q1 2025): Old scripts removed, new architecture default
- **v2.1** (Q2 2025): Real-time progress, job management added

## Getting Help

For questions or issues with migration:
1. Check this guide for common patterns
2. Review the example scripts in `scripts/pipelines/`
3. Use `biomapper --help` for CLI documentation
4. Submit issues to the project repository

## Example Migration: Complete Pipeline

### Old Approach (676 lines)
```python
# scripts/main_pipelines/run_metabolomics_harmonization.py
class MetabolomicsHarmonizationPipeline:
    def __init__(self, config_path, skip_setup=False, debug=False):
        # Complex initialization
        self.action_registry = self._build_action_registry()
        self.docker_manager = DockerManager()
        # ... 100+ lines of setup
    
    def run(self):
        # Load YAML
        # Check prerequisites
        # Setup Qdrant
        # Execute actions
        # Handle errors
        # Generate reports
        # ... 500+ lines of logic
```

### New Approach (50 lines)
```python
# scripts/pipelines/run_metabolomics_harmonization.py
from biomapper_client import BiomapperClient

async def main():
    async with BiomapperClient() as client:
        result = await client.execute_strategy(
            "metabolomics_progressive_enhancement",
            context={"skip_setup": args.skip_setup}
        )
        print_result(result)
```

The simplification is dramatic and the functionality is preserved!