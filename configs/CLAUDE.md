# Biomapper Configs - AI Assistant Instructions

## Overview

This directory contains YAML configuration files that define all data sources, mappings, and strategies for the Biomapper system. These YAML files are loaded directly by the API at runtime and drive all mapping operations.

## Key Concepts

### 1. Configuration-Driven Architecture
- **No hardcoded paths or columns** - Everything is defined in YAML
- The API loads YAML files directly from the `configs/` directory at runtime via `MinimalStrategyService`
- Changes to data sources require only YAML updates, not code changes
- **Note**: Previous documentation mentioned `metamapper.db`, but the current implementation reads YAML files directly without any database intermediary

### 2. Core Components
- **Ontologies**: Define identifier types (e.g., UniProt ACs, Gene names)
- **Databases**: Define data sources with file paths and column mappings
- **Mapping Paths**: Multi-step conversion sequences
- **Mapping Strategies**: Complex pipelines using action types
- **Action Types**: Building blocks that correspond to MappingExecutor methods

### 3. Action Types
See `/home/ubuntu/biomapper/docs/ACTION_TYPES_REFERENCE.md` for full documentation.

Current action types include:

**Core Actions:**
- `LOAD_DATASET_IDENTIFIERS` - Load biological identifiers from TSV/CSV files
- `MERGE_WITH_UNIPROT_RESOLUTION` - Map identifiers to UniProt with historical resolution
- `CALCULATE_SET_OVERLAP` - Calculate Jaccard similarity and generate overlap analysis
- `MERGE_DATASETS` - Combine multiple datasets with deduplication
- `EXECUTE_MAPPING_PATH` - Run predefined mapping workflows

**Metabolomics-Specific Actions:**
- `NIGHTINGALE_NMR_MATCH` - Match metabolites using Nightingale NMR reference
- `CTS_ENRICHED_MATCH` - Enhanced matching via Chemical Translation Service
- `METABOLITE_API_ENRICHMENT` - Enrich using external metabolite APIs
- `SEMANTIC_METABOLITE_MATCH` - AI-powered semantic matching
- `VECTOR_ENHANCED_MATCH` - Vector similarity-based matching
- `COMBINE_METABOLITE_MATCHES` - Merge multiple matching approaches
- `CALCULATE_THREE_WAY_OVERLAP` - Specialized 3-way dataset overlap analysis

**Utility Actions:**
- `FILTER_DATASET` - Apply filtering criteria to datasets
- `EXPORT_DATASET` - Export results to various formats
- `GENERATE_METABOLOMICS_REPORT` - Create comprehensive analysis reports

## Important Files

### Strategy Configurations
- **`strategies/metabolomics_progressive_enhancement.yaml`** - Main metabolomics pipeline (313 lines)
- **`strategies/three_way_metabolomics_complete.yaml`** - Complete 3-way analysis
- **`arivale_ukbb_mapping.yaml`** - Protein mapping reference implementation
- **`three_way_metabolomics_mapping_strategy.yaml`** - Additional 3-way strategy variant

### Schema and Validation
- **`schemas/metabolomics_strategy_schema.json`** - Metabolomics strategy validation
- **`schemas/mapping_concepts_explained.md`** - Conceptual documentation
- **`schemas/protein_config_schema.json`** - Legacy protein configuration schema

### Documentation and Guidance
- **`BIOMAPPER_STRATEGY_AGENT_SPEC.md`** - Strategy development specification
- **`BIOMAPPER_STRATEGY_QUICK_REFERENCE.md`** - Quick reference guide
- **`CLAUDE_STRATEGY_DEVELOPMENT.md`** - AI assistant strategy development guide
- **`prompts/08_metabolomics_wrapper_migration.md`** - Wrapper migration implementation guide

## Current Work Context

### Recent Major Achievements (August 2025)
1. **✅ API-First Architecture Complete** - All wrapper scripts migrated to BiomapperClient
2. **✅ Metabolomics Pipeline Comprehensive** - Full 3-way analysis with progressive enhancement
3. **✅ Architectural Violations Eliminated** - No more direct core imports in scripts
4. **✅ Configuration-Driven Execution** - All pipelines use YAML strategies exclusively

### Active Configuration Files
- **`strategies/metabolomics_progressive_enhancement.yaml`** - 3-stage metabolomics harmonization (313 lines)
- **`strategies/three_way_metabolomics_complete.yaml`** - Complete 3-way analysis pipeline
- **`arivale_ukbb_mapping.yaml`** - Protein mapping strategy (38 lines)
- **`schemas/metabolomics_strategy_schema.json`** - Validation schema for metabolomics strategies

### Recent Strategy Development
1. **Enhanced Metabolomics Actions** - 11+ new action types for metabolomics workflows
2. **Progressive Enhancement Pattern** - Baseline → API → Vector search methodology
3. **Three-Way Analysis Support** - Israeli10K, UKBB, Arivale dataset harmonization
4. **Type-Safe Actions** - All new actions use Pydantic models and TypedStrategyAction

### Future Priorities
1. **Strategy Schema Evolution** - Expand validation for new action types
2. **Cross-Entity Reuse** - Generic actions for proteins, metabolites, genes
3. **Performance Optimization** - Vector search and large dataset handling
4. **Real-Time Progress** - WebSocket/SSE integration for long-running strategies

## Common Tasks

### Adding a New Data Source
1. Add endpoint definition under `databases` section in the appropriate entity config file
2. Define property mappings (column to ontology type)
3. Add any mapping clients needed
4. **Note**: No database loading required - changes take effect on API restart

### Creating a New Strategy
1. **Review available action types** - See action lists above or ACTION_TYPES_REFERENCE.md
2. **Design the pipeline steps** - Use progressive enhancement or multi-stage patterns
3. **Create YAML strategy file** in `configs/strategies/` directory:
   ```yaml
   name: MY_NEW_STRATEGY
   description: Clear description of what this strategy accomplishes
   steps:
     - name: load_data
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: /path/to/data.tsv
           identifier_column: id_column
           output_key: loaded_data
   ```
4. **Validate against schema** - Use `configs/schemas/metabolomics_strategy_schema.json` as reference
5. **Test via API client** - Use BiomapperClient.execute_strategy() with your strategy name
6. **API auto-loads** - No restart needed, strategies loaded dynamically

### Debugging Configuration Issues
1. Check YAML syntax errors (the API logs will show loading failures)
2. Verify action types match those in the action registry (`MinimalStrategyService._build_action_registry()`)
3. Ensure file paths in action params are absolute and exist
4. Check column names match actual data files
5. Review API logs during startup to see which strategies were successfully loaded

## Best Practices

1. **Test configurations** - Always validate YAML against schema before loading
2. **Document strategies** - Include clear descriptions of what each strategy does
3. **Keep actions atomic** - Each action type should do one thing well
4. **Consider reusability** - Design for use across different datasets

## Notes on Architecture Evolution

The system has evolved to:
- **Direct YAML loading**: Strategies are loaded directly from YAML files at API startup, no database intermediary
- **Simplified execution**: `MinimalStrategyService` provides lightweight strategy execution
- **Action-based architecture**: Small, composable actions (LOAD_DATASET_IDENTIFIERS, MERGE_WITH_UNIPROT_RESOLUTION, etc.)
- **Runtime flexibility**: Add new strategies by simply creating new YAML files in `configs/`

### Current Implementation Details
Based on recent architectural completion (August 2025):

**API Service Architecture:**
- **Main Service**: `biomapper-api/app/services/mapper_service.py` using `MapperServiceForStrategies`
- **Strategy Loading**: `biomapper/core/minimal_strategy_service.py` loads all `*.yaml` files from `STRATEGIES_DIR` 
- **Configuration Path**: `STRATEGIES_DIR` points to `/home/ubuntu/biomapper/configs/`
- **Job Persistence**: `biomapper-api/biomapper.db` (SQLite) handles execution state and checkpoints

**Wrapper Scripts (Now API Clients):**
- **`scripts/main_pipelines/run_metabolomics_harmonization.py`** - 255 lines, BiomapperClient only
- **`scripts/main_pipelines/run_arivale_ukbb_mapping.py`** - 81 lines, clean API client pattern
- **All orchestration** delegated to API layer, no direct core imports

**Strategy Execution Flow:**
1. Client calls BiomapperClient.execute_strategy()
2. API loads YAML strategy from configs/strategies/
3. MinimalStrategyService orchestrates action sequence
4. Results and checkpoints stored in biomapper.db
5. Final results returned to client

## Action Type Design Principles

When developing new action types for Biomapper, follow these key principles:

### 1. **Composability**
- Each action should do one thing well
- Actions should be combinable in different sequences
- Avoid actions that try to do too much

### 2. **Reusability**
- Design actions to work across entity types (proteins, metabolites, genes)
- Use generic parameter names when possible
- Avoid entity-specific assumptions

### 3. **Type Safety**
- Use Pydantic models for all parameters and results
- Inherit from `TypedStrategyAction` for new actions
- Define clear input/output contracts

### 4. **Error Handling**
- Implement graceful degradation
- Provide clear, actionable error messages
- Use `is_required: false` for optional steps
- Log warnings for non-critical failures

### 5. **Performance**
- Batch operations where possible
- Implement efficient data structures
- Consider memory usage for large datasets
- Add progress tracking for long operations

### 6. **Extensibility**
- Use the `@register_action` decorator
- Follow existing naming conventions
- Document parameters thoroughly
- Design for future enhancement

### 7. **Provenance Tracking**
- Each action should record what it did
- Track success/failure rates
- Maintain mapping source information
- Enable audit trails

### Example Action Structure:
```python
@register_action("ACTION_NAME")
class MyAction(TypedStrategyAction[MyParams, MyResult]):
    """Clear description of what this action does."""
    
    def get_params_model(self) -> type[MyParams]:
        return MyParams
    
    async def execute_typed(self, params: MyParams, context: Dict) -> MyResult:
        # Implementation following the principles above
        pass
```