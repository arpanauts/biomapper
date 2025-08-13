# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

```bash
# Setup and environment
poetry install --with dev,docs,api
poetry shell

# Run tests
poetry run pytest                           # All tests with coverage
poetry run pytest tests/unit/               # Unit tests only
poetry run pytest tests/integration/        # Integration tests only
poetry run pytest -k "test_name"            # Run specific test by name
poetry run pytest -xvs tests/path/test.py   # Debug single test with output

# Code quality (run before committing)
poetry run ruff format .                    # Format code
poetry run ruff check . --fix               # Fix auto-fixable linting issues
poetry run mypy biomapper biomapper-api biomapper_client  # Type checking

# Development server
cd biomapper-api && poetry run uvicorn app.main:app --reload --port 8000

# Database operations
poetry run alembic upgrade head             # Apply migrations
poetry run alembic revision -m "description"  # Create new migration

# Makefile shortcuts
make test                                   # Run tests with coverage
make format                                 # Format code with ruff
make lint-fix                              # Auto-fix linting issues
make typecheck                             # Run mypy type checking
make check                                 # Run all checks (format, lint, typecheck, test, docs)
make docs                                  # Build documentation
make clean                                 # Clean cache files

# CLI usage
poetry run biomapper --help
poetry run biomapper health
poetry run biomapper metadata list

# CI diagnostics
python scripts/ci_diagnostics.py           # Check for common CI issues
make ci-test-local                         # Test in Docker CI environment
```

## Architecture Overview

```
Client Request → BiomapperClient → FastAPI Server → MapperService → MinimalStrategyService
                                                                     ↓
                                                    ACTION_REGISTRY (Global Dict)
                                                                     ↓
                                              Self-Registering Action Classes
                                                                     ↓
                                                 Execution Context (shared state)
```

### Core Components

**biomapper/** - Core library with mapping logic
- Actions self-register via `@register_action("ACTION_NAME")` decorator
- `MinimalStrategyService` provides lightweight strategy execution
- Execution context flows as `Dict[str, Any]` with keys: `current_identifiers`, `datasets`, `statistics`, `output_files`

**biomapper-api/** - FastAPI service exposing REST endpoints
- Direct YAML loading from `configs/` directory at runtime
- SQLite job persistence (`biomapper.db`) with checkpointing
- Background job execution with real-time SSE progress updates

**biomapper_client/** - Python client for the API
- Primary interface via `BiomapperClient` in `client_v2.py`
- Synchronous wrapper: `client.run("strategy_name")`
- No direct imports from core library

## Creating New Strategy Actions

Follow TDD approach - write tests first:

```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from pydantic import BaseModel, Field

class MyActionParams(BaseModel):
    input_key: str = Field(..., description="Input dataset key")
    threshold: float = Field(0.8, description="Processing threshold")
    output_key: str = Field(..., description="Output dataset key")

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, context: Dict) -> ActionResult:
        # Access input data
        input_data = context["datasets"].get(params.input_key)
        
        # Process data
        processed = process_data(input_data, params.threshold)
        
        # Store output
        context["datasets"][params.output_key] = processed
        
        return ActionResult(
            success=True,
            message=f"Processed {len(processed)} items"
        )
```

Action will auto-register - no executor modifications needed.

## Enhanced Action Organization

Actions are organized by biological entity and function:

```
strategy_actions/
├── entities/                    # Entity-specific actions
│   ├── proteins/                # UniProt, Ensembl, gene symbols
│   │   ├── annotation/          # ID extraction & normalization
│   │   └── matching/            # Cross-dataset resolution
│   ├── metabolites/             # HMDB, InChIKey, CHEBI, KEGG
│   │   ├── identification/      # ID extraction & normalization
│   │   ├── matching/            # CTS, semantic, vector matching
│   │   └── enrichment/          # External API integration
│   └── chemistry/               # LOINC, clinical tests
│       ├── identification/      # LOINC extraction
│       └── matching/            # Fuzzy test matching
├── algorithms/                  # Reusable algorithms
├── utils/                       # General utilities
├── workflows/                   # High-level orchestration
├── io/                         # Data input/output
└── reports/                    # Analysis & reporting
```

## Creating YAML Strategies

Place strategies in `configs/strategies/`:

```yaml
name: MY_STRATEGY
description: Clear description of purpose
parameters:
  data_file: "/path/to/data.tsv"
  output_dir: "${OUTPUT_DIR:-/tmp/results}"
  
steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.data_file}"
        identifier_column: id
        output_key: loaded_data
        
  - name: process
    action:
      type: MY_ACTION
      params:
        input_key: loaded_data
        threshold: 0.85
        output_key: processed_data
```

Variable substitution supports:
- `${parameters.key}` - Strategy parameters
- `${metadata.field}` - Metadata fields
- `${env.VAR}` or `${VAR}` - Environment variables

## Available Actions

**Data Operations:**
- `LOAD_DATASET_IDENTIFIERS` - Load biological identifiers from TSV/CSV
- `MERGE_DATASETS` - Combine datasets with deduplication
- `FILTER_DATASET` - Apply filtering criteria
- `EXPORT_DATASET` - Export to various formats
- `CUSTOM_TRANSFORM` - Apply Python expressions to columns

**Mapping Operations:**
- `MERGE_WITH_UNIPROT_RESOLUTION` - Map to UniProt accessions
- `CALCULATE_SET_OVERLAP` - Jaccard similarity analysis
- `CALCULATE_THREE_WAY_OVERLAP` - Three-dataset comparison

**Metabolomics:**
- `NIGHTINGALE_NMR_MATCH` - Nightingale NMR reference matching
- `CTS_ENRICHED_MATCH` - Chemical Translation Service matching
- `METABOLITE_API_ENRICHMENT` - External API enrichment
- `SEMANTIC_METABOLITE_MATCH` - AI-powered semantic matching
- `VECTOR_ENHANCED_MATCH` - Vector similarity matching
- `COMBINE_METABOLITE_MATCHES` - Merge multiple approaches
- `GENERATE_METABOLOMICS_REPORT` - Comprehensive reports

**IO Operations:**
- `SYNC_TO_GOOGLE_DRIVE` - Upload results to Google Drive with chunked transfer

**Protein Operations:**
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Extract UniProt IDs from compound fields
- `PROTEIN_NORMALIZE_ACCESSIONS` - Standardize protein identifiers

**Chemistry Operations:**
- `CHEMISTRY_EXTRACT_LOINC` - Extract LOINC codes from clinical data

## Testing Strategy

Follow Test-Driven Development (TDD):

1. Write failing tests first
2. Implement minimal code to pass
3. Refactor while keeping tests green

```bash
# Test specific action
poetry run pytest -xvs tests/unit/core/strategy_actions/test_my_action.py

# Test with coverage
poetry run pytest --cov=biomapper --cov-report=html

# Debug test failures
poetry run pytest -xvs --pdb tests/unit/
```

## Type Safety Migration

Project is migrating to full type safety using TypedStrategyAction pattern:
- Business logic actions use TypedStrategyAction with Pydantic models
- Infrastructure actions (like chunk_processor) remain flexible
- Backward compatibility maintained with `extra="allow"` in Pydantic models
- All new actions must use typed pattern

## Key Implementation Patterns

### Context Flow
Actions receive and modify shared `context` dictionary:
- `context["datasets"][key]` - Access datasets from previous actions
- `context["statistics"]` - Accumulate statistics
- `context["output_files"]` - Track generated files
- `context["current_identifiers"]` - Active identifier set

### Error Handling
```python
from biomapper.core.exceptions import ValidationError, ProcessingError

try:
    result = process_data(input_data)
except ValidationError as e:
    return ActionResult(success=False, message=str(e))
```

### Parameter Validation
```python
from pydantic import BaseModel, Field, validator

class MyParams(BaseModel):
    file_path: str = Field(..., description="Input file path")
    threshold: float = Field(0.8, ge=0.0, le=1.0)
    
    @validator("file_path")
    def validate_path(cls, v):
        if not Path(v).exists():
            raise ValueError(f"File not found: {v}")
        return v
```

## API Development

When working on biomapper-api:
- Use dependency injection for database sessions
- Implement proper error handling with HTTPException
- Add OpenAPI documentation to endpoints
- Follow RESTful conventions
- Use Pydantic models for request/response validation

## Important Notes

- **ALWAYS USE POETRY** - Never use pip directly
- **Type Safety** - Resolve all mypy errors before committing
- **Action Registration** - Actions self-register via decorator
- **Direct YAML Loading** - No database intermediary for strategies
- **Test Coverage** - Minimum 80% required
- **ChromaDB** - May require specific system dependencies
- **Environment Variables** - Use `.env` files (not committed)
- **Backward Compatibility** - Maintain during type safety migration

## Current Focus Areas

1. **Type Safety Migration** - Converting final 2-3 actions to TypedStrategyAction
2. **Enhanced Organization** - Entity-based action structure
3. **Performance Optimization** - Chunking for large datasets
4. **External Integrations** - Google Drive sync, API enrichments