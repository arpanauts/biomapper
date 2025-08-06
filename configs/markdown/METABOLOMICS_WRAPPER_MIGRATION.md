# Metabolomics Wrapper Migration Guide

## Overview
The metabolomics harmonization wrapper has been simplified from 691 lines of complex orchestration to a clean API client (255 lines).

## Before vs After

### Before (Complex Orchestration)
```bash
# 691 lines with many options
python scripts/main_pipelines/run_metabolomics_harmonization.py \
    --config configs/strategies/metabolomics_progressive_enhancement.yaml \
    --skip-setup \
    --skip-qdrant \
    --stage all \
    --debug
```

### After (Simple API Client)  
```bash
# Clean, simple interface
python scripts/main_pipelines/run_metabolomics_harmonization.py \
    --three-way \
    --watch \
    --debug
```

## Parameter Mapping

| Old Flag | New Equivalent | Notes |
|----------|----------------|--------|
| `--config PATH` | `--strategy NAME` | Now uses strategy names, not file paths |
| `--skip-setup` | Removed | API handles all setup |
| `--skip-qdrant` | Removed | API manages resources |
| `--stage STAGE` | Removed | Strategies define their own flow |
| `--debug` | `--debug` | Same functionality |
| `--dry-run` | `--dry-run` | Same functionality |
| `--report-only` | Removed | Use separate reporting tools |
| `--three-way` | `--three-way` | Same functionality |

## Migration Steps

1. **Update Your Scripts**: Replace calls to the old wrapper with the new API client version
2. **Check Parameters**: Review any custom parameters and move them to JSON files
3. **Verify Output**: Ensure output paths and formats meet your needs
4. **Test Execution**: Run the new version to verify it works as expected

## Benefits of New Approach

- **Simpler**: 255 lines instead of 691
- **Reliable**: All orchestration handled by robust API
- **Maintainable**: Changes only needed in one place (API)
- **Monitorable**: Future support for real-time progress tracking
- **Scalable**: Can run distributed with job persistence

## Available Strategies

The new script supports these pre-configured strategies:

1. **METABOLOMICS_PROGRESSIVE_ENHANCEMENT** (default)
   - 3-stage progressive enhancement
   - Baseline fuzzy matching → CTS API enrichment → Vector search enhancement
   
2. **THREE_WAY_METABOLOMICS_COMPLETE**  
   - Complete three-way analysis
   - Advanced matching techniques with comprehensive reporting

## Usage Examples

### Basic Progressive Enhancement
```bash
python scripts/main_pipelines/run_metabolomics_harmonization.py
```

### Three-Way Analysis
```bash
python scripts/main_pipelines/run_metabolomics_harmonization.py --three-way
```

### Custom Parameters
```bash
# Create params.json with custom settings
echo '{"threshold": 0.9, "output_format": "tsv"}' > params.json
python scripts/main_pipelines/run_metabolomics_harmonization.py --parameters params.json
```

### Development Mode
```bash
python scripts/main_pipelines/run_metabolomics_harmonization.py --debug --dry-run
```

### Custom API Endpoint
```bash
python scripts/main_pipelines/run_metabolomics_harmonization.py --api-url http://remote-server:8000
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   ```bash
   # Start the API server first
   cd biomapper-api
   poetry run uvicorn main:app --reload
   ```

2. **Strategy Not Found**
   ```bash
   # List available strategies
   ls configs/strategies/
   # Use exact strategy name from YAML filename
   ```

3. **Parameter File Not Found**
   ```bash
   # Check file path and format
   python -c "import json; print(json.load(open('params.json')))"
   ```

### Migration Checklist

- [ ] Identified all scripts using the old wrapper
- [ ] Tested new wrapper with existing workflows
- [ ] Updated any automation/CI scripts
- [ ] Verified output files are generated correctly
- [ ] Confirmed parameter files work as expected
- [ ] Updated documentation for your specific use cases

## API Requirements

The new wrapper requires:
- Biomapper API server running (default: `http://localhost:8000`)
- Valid strategy configurations in `configs/strategies/`
- `biomapper_client` package installed

## Future Enhancements

The new architecture enables:
- Real-time progress monitoring (via WebSocket/SSE)
- Distributed execution
- Job persistence and resumption
- Better error reporting
- Centralized logging and metrics