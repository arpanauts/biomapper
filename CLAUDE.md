# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

### Setup
```bash
# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --with dev,docs,api

# Activate virtual environment
poetry shell
```

### Essential Commands
```bash
# Run tests
poetry run pytest
poetry run pytest tests/unit/  # Unit tests only
poetry run pytest tests/integration/  # Integration tests only
poetry run pytest -k "test_name"  # Run specific test

# Linting and formatting
poetry run ruff check .  # Check for linting issues
poetry run ruff check . --fix  # Fix auto-fixable issues
poetry run ruff format .  # Format code

# Type checking
poetry run mypy biomapper biomapper-api biomapper_client

# Run API server
cd biomapper-api && poetry run uvicorn app.main:app --reload

# Database migrations
poetry run alembic upgrade head  # Apply migrations
poetry run alembic revision -m "description"  # Create new migration

# Build documentation
cd docs && poetry run make html

# CLI usage
poetry run biomapper --help
poetry run biomapper health
poetry run biomapper metadata list

# Makefile shortcuts (alternative to poetry run)
make test           # Run all tests with coverage
make lint           # Check for linting issues
make lint-fix       # Auto-fix linting issues
make format         # Format code with ruff
make typecheck      # Run mypy type checking
make check          # Run all checks (format, lint, typecheck, test, docs)
make docs           # Build documentation
make clean          # Clean all cache files
```

## Architecture Overview

Biomapper is a modular biological data harmonization toolkit built around an extensible action system and YAML-based strategy configuration.

### System Architecture Flow
```
Client Request → FastAPI Server → MapperService → MinimalStrategyService
                                                   ↓
                                  ACTION_REGISTRY (Global Dict)
                                                   ↓
                            Individual Action Classes (self-registered)
                                                   ↓
                                  Execution Context (Dict[str, Any])
```

### Three Main Components

1. **biomapper/** - Core library with mapping logic and orchestration
   - Self-registering action system using `@register_action` decorator
   - `MinimalStrategyService` for lightweight strategy execution
   - Pydantic models for type safety and validation

2. **biomapper-api/** - FastAPI service exposing REST endpoints
   - Direct YAML loading from `configs/` directory at runtime
   - Job persistence in SQLite (`biomapper.db`)
   - Background job execution with checkpointing

3. **biomapper_client/** - Python client for the API
   - Clean interface for strategy execution
   - No direct imports from core library
   - Used by all wrapper scripts

### Core Architecture Components

- **ACTION_REGISTRY**: Global dictionary mapping action names to classes
  - Actions self-register via `@register_action("ACTION_NAME")` decorator
  - Located in `biomapper/core/strategy_actions/registry.py`
  - Loaded dynamically by `MinimalStrategyService`

- **Execution Context**: Simple dictionary flowing through action pipeline
  - Contains: `current_identifiers`, `datasets`, `statistics`, `output_files`
  - Each action reads from and modifies this shared state
  - Enables actions to build upon previous results

- **Strategy Actions**: Self-contained processing units in `biomapper/core/strategy_actions/`
  - Inherit from `TypedStrategyAction` for type safety
  - Use Pydantic models for parameters and results
  - Register themselves automatically when imported

- **YAML Strategies**: Configuration files in `configs/strategies/`
  - Define workflows as sequences of actions
  - Support variable substitution for both parameters and metadata:
    - `${parameters.key}` - Access strategy parameters
    - `${metadata.source_files[0].path}` - Access metadata fields
    - `${env.VAR_NAME}` or `${VAR_NAME}` - Environment variables
  - Loaded directly by API at runtime without database intermediary

## Development Guidelines

### Code Standards

1. **Type Hints**: All functions must have complete type annotations
2. **Docstrings**: Use Google-style docstrings for all public methods
3. **Error Handling**: Use custom exceptions from `biomapper.core.exceptions`
4. **Async/Await**: Use async patterns for I/O operations
5. **Configuration**: Use Pydantic models for all configuration

### Testing Requirements

- Minimum 80% test coverage required
- Use pytest fixtures for common test data
- Mock external services in unit tests
- Integration tests should use test databases/APIs
- Follow Test-Driven Development (TDD) for new features
- Write failing tests first, then implement minimal code to pass

### Creating a New Strategy Action

1. **Write failing tests first** (TDD approach)
2. Create action class in `biomapper/core/strategy_actions/`
3. Inherit from `TypedStrategyAction` for type safety
4. Define Pydantic models for parameters and results:
   ```python
   from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
   from biomapper.core.strategy_actions.registry import register_action
   from pydantic import BaseModel
   
   class MyActionParams(BaseModel):
       required_field: str
       optional_field: int = 100
   
   @register_action("MY_ACTION")
   class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
       def get_params_model(self) -> type[MyActionParams]:
           return MyActionParams
       
       async def execute_typed(self, params: MyActionParams, context: Dict) -> ActionResult:
           # Type-safe implementation
           pass
   ```
5. Action will auto-register via decorator - no need to modify executor
6. Add comprehensive unit tests in `tests/unit/core/strategy_actions/`
7. Update documentation if needed

### Creating a New YAML Strategy

1. Create YAML file in `configs/strategies/`:
   ```yaml
   name: MY_NEW_STRATEGY
   description: Clear description of what this strategy accomplishes
   parameters:
     data_file: "/path/to/data.tsv"
     output_dir: "/path/to/output"
   steps:
     - name: load_data
       action:
         type: LOAD_DATASET_IDENTIFIERS
         params:
           file_path: "${parameters.data_file}"
           identifier_column: id_column
           output_key: loaded_data
   ```
2. API will auto-load on next request (no restart needed)
3. Test via BiomapperClient: `client.execute_strategy("MY_NEW_STRATEGY")`

### API Development

When working on biomapper-api:
- Use dependency injection for database sessions
- Implement proper error handling with HTTPException
- Add OpenAPI documentation to endpoints
- Use Pydantic models for request/response validation
- Follow RESTful conventions

## Key Action Types

The biomapper orchestration system supports these core actions (auto-registered):

**Data Operations:**
- `LOAD_DATASET_IDENTIFIERS`: Load biological identifiers from TSV/CSV files
- `MERGE_DATASETS`: Combine multiple datasets with deduplication
- `FILTER_DATASET`: Apply filtering criteria to datasets
- `EXPORT_DATASET`: Export results to various formats
- `CUSTOM_TRANSFORM`: Apply Python expressions to transform dataset columns

**IO Operations:**
- `SYNC_TO_GOOGLE_DRIVE`: Upload analysis results to Google Drive

**Mapping Operations:**
- `MERGE_WITH_UNIPROT_RESOLUTION`: Map identifiers to UniProt accessions
- `EXECUTE_MAPPING_PATH`: Run predefined mapping workflows
- `CALCULATE_SET_OVERLAP`: Calculate Jaccard similarity between datasets
- `CALCULATE_THREE_WAY_OVERLAP`: Specialized 3-way dataset analysis

**Metabolomics-Specific:**
- `NIGHTINGALE_NMR_MATCH`: Match using Nightingale NMR reference
- `CTS_ENRICHED_MATCH`: Enhanced matching via Chemical Translation Service
- `METABOLITE_API_ENRICHMENT`: Enrich using external metabolite APIs
- `SEMANTIC_METABOLITE_MATCH`: AI-powered semantic matching
- `VECTOR_ENHANCED_MATCH`: Vector similarity-based matching
- `COMBINE_METABOLITE_MATCHES`: Merge multiple matching approaches
- `GENERATE_METABOLOMICS_REPORT`: Create comprehensive analysis reports

See strategy configuration examples in `configs/strategies/` for usage patterns.

### SYNC_TO_GOOGLE_DRIVE Action

The `SYNC_TO_GOOGLE_DRIVE` action provides seamless integration with Google Drive for uploading analysis results:

**Features:**
- Automatic upload of all pipeline output files
- Support for custom file selection and filtering
- Timestamped subfolder creation
- Conflict resolution strategies (rename, overwrite, skip)
- Chunked upload for large files
- Exponential backoff retry logic
- Soft failure mode to prevent pipeline interruption

**Setup:**
1. Create a Google Cloud service account
2. Download the JSON credentials file
3. Set environment variable: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json`

**Example Usage:**
```yaml
- name: sync_results_to_drive
  action:
    type: SYNC_TO_GOOGLE_DRIVE
    params:
      drive_folder_id: "1A2B3C4D5E6F"  # Target folder ID from Google Drive
      sync_context_outputs: true        # Auto-sync all output files
      create_subfolder: true            # Create timestamped subfolder
      subfolder_name: "run_${env.RUN_ID}"  # Optional custom name
      file_patterns: ["*.csv", "*.json"]   # Include only these patterns
      exclude_patterns: ["*temp*"]         # Exclude these patterns
      conflict_resolution: "rename"        # rename, overwrite, or skip
      chunk_size: 10485760               # 10MB chunks for large files
      max_retries: 3                     # Retry failed uploads
      hard_failure: false                # Don't fail pipeline on error
      verbose: true                      # Enable progress logging
```

### CUSTOM_TRANSFORM Action

The `CUSTOM_TRANSFORM` action provides flexible data transformation using Python expressions:

**Features:**
- Apply arbitrary Python expressions to dataset columns
- Support for conditional logic and complex transformations
- Create new columns while preserving originals
- Configurable error handling (keep_original, null, raise)
- Safe evaluation with restricted namespace

**Example Usage:**
```yaml
- name: transform_protein_data
  action:
    type: CUSTOM_TRANSFORM
    params:
      input_key: protein_data
      output_key: transformed_proteins
      transformations:
        # Simple string transformation
        - column: uniprot_id
          expression: "value.upper().strip()"
        
        # Conditional splitting
        - column: gene_symbol
          expression: "value.split('|')[0] if '|' in value else value"
          new_column: primary_gene
        
        # Type conversion with null handling
        - column: concentration
          expression: "float(value) if value else 0.0"
          on_error: null
        
        # Complex expression with numpy
        - column: values
          expression: "np.log10(float(value)) if value else np.nan"
          new_column: log_values
```

## Important Notes

- **ALWAYS USE POETRY ENVIRONMENT** - Never use pip directly
- **Action Registration** - Actions self-register via `@register_action` decorator
- **No Database Loading** - Strategies load directly from YAML files at runtime
- **Configuration files** in `configs/` are version-controlled examples
- **Environment-specific settings** use `.env` files (not committed)
- **The project uses strict MyPy settings** - resolve all type errors
- **ChromaDB** requires specific system dependencies on some platforms
- **Integration tests** may require external services (document in PR)
- **Follow TDD approach** for all new features and refactoring
- **Maintain backward compatibility** during type safety migration

## Current Architecture State (August 2025)

- **Simplified Execution**: `MinimalStrategyService` provides lightweight strategy execution
- **Direct YAML Loading**: No database intermediary, strategies loaded from `configs/` at runtime
- **Self-Registering Actions**: Actions register themselves via decorator pattern
- **API-First Architecture**: All scripts use `BiomapperClient`, no direct core imports
- **Type Safety Migration**: Moving from `Dict[str, Any]` to typed Pydantic models
- **Job Persistence**: SQLite database (`biomapper.db`) for execution state and checkpoints