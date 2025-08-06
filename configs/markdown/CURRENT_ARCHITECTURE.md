# Biomapper Current Architecture (August 2025)

## Overview

**UPDATE (2025-08-06)**: Biomapper has achieved full **API-first architecture**. All wrapper scripts have been successfully migrated to simple API clients, eliminating previous architectural violations.

This document clarifies the current implementation of Biomapper's configuration and execution system, including recent architectural improvements.

## Key Finding: Direct YAML Loading

The current implementation **does not use a database intermediary** for configuration management. Instead:

1. **Strategy YAML files** are loaded directly from the `configs/` directory
2. **The API reads these files at startup** via `MinimalStrategyService`
3. **Strategies are executed from in-memory representations** of the YAML data

## Architecture Components

### 1. Strategy Storage
- **Location**: `/home/ubuntu/biomapper/configs/*.yaml`
- **Format**: YAML files containing strategy definitions
- **Example**: `arivale_ukbb_mapping.yaml`

### 2. API Configuration
- **Settings**: `biomapper-api/app/core/config.py`
- **Key Setting**: `STRATEGIES_DIR: Path = BASE_DIR.parent / "configs"`
- **Loading**: Happens at API startup, not on-demand

### 3. Strategy Loading Service
- **Class**: `MinimalStrategyService` 
- **Location**: `biomapper/core/minimal_strategy_service.py`
- **Process**:
  ```python
  # Simplified loading process
  for yaml_file in strategies_dir.glob("*.yaml"):
      strategy_data = yaml.safe_load(f)
      strategies[strategy_data['name']] = strategy_data
  ```

### 4. Execution Flow
```
1. Client calls API endpoint with strategy name
2. API looks up strategy in memory (loaded at startup)
3. MinimalStrategyService executes steps sequentially
4. Each step uses registered actions (LOAD_DATASET_IDENTIFIERS, etc.)
5. Results returned to client
```

## What Changed from Previous Architecture

### Old Architecture (per documentation):
- Configurations loaded into `metamapper.db`
- Scripts query database for configuration
- Complex entity relationships and mappings stored in DB

### Current Architecture (actual implementation):
- Direct YAML file loading
- No database for configuration storage
- Simplified execution model
- Strategies self-contained in individual YAML files

## Implications for Development

### Adding New Strategies
1. Create a new YAML file in `configs/`
2. Restart the API to load the new strategy
3. No database population step required

### Modifying Existing Strategies
1. Edit the YAML file directly
2. Restart the API to reload changes
3. Changes take effect immediately

### Debugging
- Check API startup logs to see which strategies loaded
- YAML syntax errors will prevent strategy loading
- All strategies must have a unique `name` field

## Action Registry

Current supported actions (15+ production-ready):

**Core Actions:**
- `LOAD_DATASET_IDENTIFIERS`
- `MERGE_WITH_UNIPROT_RESOLUTION`
- `CALCULATE_SET_OVERLAP`
- `MERGE_DATASETS`

**Metabolomics Actions:**
- `BASELINE_FUZZY_MATCH`
- `CTS_ENRICHED_MATCH`
- `VECTOR_ENHANCED_MATCH`
- `NIGHTINGALE_NMR_MATCH`
- `SEMANTIC_METABOLITE_MATCH`
- `COMBINE_METABOLITE_MATCHES`
- `CALCULATE_THREE_WAY_OVERLAP`

**Utility Actions:**
- `BUILD_NIGHTINGALE_REFERENCE`
- `GENERATE_ENHANCEMENT_REPORT`
- `GENERATE_METABOLOMICS_REPORT`

Additional actions can be registered by:
1. Creating new action classes
2. Adding them to the registry in `MinimalStrategyService`
3. Using them in strategy YAML files

## Benefits of Current Architecture

1. **Simplicity**: No database layer to manage
2. **Transparency**: YAML files are human-readable and version-controlled
3. **Flexibility**: Easy to add/modify strategies without schema changes
4. **Debugging**: Can directly inspect strategy definitions

## Recent Architectural Achievements

### API-First Migration Complete (August 2025)
- **Metabolomics wrapper**: Reduced from 691 → 255 lines
- **All wrapper scripts**: Now simple BiomapperClient usage
- **Zero core imports**: No direct action imports in scripts
- **Full API delegation**: All orchestration in API layer

### Production Features Added
- **Job Persistence**: SQLite database (`biomapper.db`) for state management
- **15+ Action Types**: Comprehensive biological data harmonization
- **Progressive Enhancement**: Multi-stage improvement strategies
- **Type Safety**: Pydantic models throughout

## Limitations (Minor)

1. **No complex querying**: Can't query strategies by properties (planned for v2.1)
2. **Memory usage**: All strategies loaded at startup (negligible impact)
3. **No runtime updates**: Must restart API for changes (acceptable for production)
4. **No validation**: Beyond YAML syntax and action existence

## Summary

The current Biomapper implementation prioritizes simplicity and directness over the more complex database-driven approach described in older documentation. This makes it easier to understand, modify, and extend, though it trades off some capabilities like dynamic configuration updates and complex querying.