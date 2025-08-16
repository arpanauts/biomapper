# CLAUDE.md - Strategy Configuration Guide (2025 Standards)

This file provides guidance to Claude Code (claude.ai/code) when working with biomapper strategy configurations.

**🎯 CRITICAL**: All strategy configurations MUST follow the 2025 parameter naming standards and best practices.

## Essential Commands

```bash
# Strategy validation and testing
python scripts/validate_strategy.py my_strategy_name    # Validate strategy configuration
python scripts/run_three_level_tests.py strategies --strategy my_strategy  # Test strategy

# Parameter naming validation (NEW)
python -c "from biomapper.core.standards.parameter_validator import ParameterValidator; ParameterValidator.audit_strategy_file('configs/strategies/my_strategy.yaml')"

# Environment setup for strategies (NEW)
python scripts/setup_environment.py            # Interactive environment setup
poetry run python -c "from biomapper.core.standards.env_manager import EnvironmentManager; EnvironmentManager().validate_requirements(['google_drive'])"

# Run tests
poetry run pytest                              # All tests
poetry run pytest tests/unit/                  # Unit tests only
poetry run pytest tests/integration/           # Integration tests only
poetry run pytest -k "test_name"              # Specific test
poetry run pytest -xvs tests/path/to/test.py::TestClass::test_method  # Single test with output

# Code quality checks - ALWAYS RUN BEFORE COMMITTING
poetry run ruff check .                        # Check linting
poetry run ruff check . --fix                  # Auto-fix issues  
poetry run ruff format .                       # Format code
poetry run mypy biomapper biomapper-api biomapper_client  # Type checking

# Makefile shortcuts (preferred)
make test                                       # Run all tests with coverage
make lint-fix                                   # Fix linting issues
make format                                     # Format code
make typecheck                                  # Run mypy
make check                                      # Run ALL checks (format, lint, typecheck, test, docs)

# API development
cd ../biomapper-api && poetry run uvicorn app.main:app --reload  # Start API server
poetry run alembic upgrade head                 # Apply database migrations
poetry run alembic revision -m "description"   # Create new migration

# Client usage
poetry run biomapper health                    # Check system health
poetry run biomapper metadata list             # List available resources
```

## Architecture Overview

Biomapper is a bioinformatics workflow platform built around self-registering actions and YAML-based strategies. The system follows a strict API-first architecture where all scripts use BiomapperClient to execute strategies.

### System Flow
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

1. **biomapper/** - Core library with mapping logic
   - Actions self-register via `@register_action` decorator
   - `MinimalStrategyService` executes strategies from YAML
   - Located at `/home/ubuntu/biomapper/biomapper/`

2. **biomapper-api/** - FastAPI service 
   - Loads strategies from `configs/` at runtime
   - SQLite persistence (`biomapper.db`)
   - Located at `/home/ubuntu/biomapper/biomapper-api/`

3. **biomapper_client/** - Python client
   - Clean API interface, no core imports
   - Used by all wrapper scripts
   - Located at `/home/ubuntu/biomapper/biomapper_client/`

## Creating New Strategy Actions (TDD Approach)

1. **Write failing tests first**:
   ```python
   # tests/unit/core/strategy_actions/test_my_action.py
   def test_my_action_executes():
       action = MyAction()
       result = await action.execute(params, context)
       assert result.success
   ```

2. **Create action class**:
   ```python
   # biomapper/core/strategy_actions/my_action.py
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
           # Implementation
           pass
   ```

3. **Action auto-registers** - No executor modifications needed

## 🎯 STANDARDIZED Parameter Naming (2025 Framework)

**CRITICAL**: All strategy configurations MUST use standardized parameter names. This prevents the 376+ parameter inconsistencies that caused pipeline failures.

### Required Parameter Names

| Purpose | STANDARD NAME | ❌ AVOID | Example |
|---------|---------------|----------|---------|
| Input dataset | `input_key` | `dataset_key`, `source_dataset` | `input_key: "loaded_data"` |
| Output dataset | `output_key` | `result_key`, `output_dataset` | `output_key: "processed_data"` |
| File path | `file_path` | `filepath`, `csv_path`, `filename` | `file_path: "/data/file.tsv"` |
| Output path | `output_path` | `output_file`, `result_path` | `output_path: "/results/output.tsv"` |
| Column names | `identifier_column` | `id_column`, `identifier_col` | `identifier_column: "uniprot_id"` |
| Thresholds | `threshold` | `threshold_value`, `cutoff` | `threshold: 0.8` |

### Creating YAML Strategies (2025 Standards)

Create file in `configs/strategies/` following naming standards:

```yaml
name: MY_STRATEGY_2025
description: Clear description of strategy purpose
parameters:
  # STANDARD NAMES REQUIRED
  data_file: "/path/to/data.tsv"
  output_dir: "${OUTPUT_DIR:-/tmp/results}"  # Environment variable support
  
steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.data_file}"        # STANDARD: file_path
        identifier_column: "uniprot_id"             # STANDARD: identifier_column  
        output_key: "loaded_data"                   # STANDARD: output_key
        
  - name: normalize_identifiers
    action:
      type: PROTEIN_NORMALIZE_ACCESSIONS
      params:
        input_key: "loaded_data"                    # STANDARD: input_key
        output_key: "normalized_data"               # STANDARD: output_key
        
  - name: export_results
    action:
      type: EXPORT_DATASET
      params:
        input_key: "normalized_data"                # STANDARD: input_key
        output_path: "${parameters.output_dir}/results.tsv"  # STANDARD: output_path
        format: "tsv"                               # STANDARD: format (not file_format)
```

### Parameter Validation Commands

```bash
# Validate strategy parameter names
python -c "from biomapper.core.standards.parameter_validator import ParameterValidator; ParameterValidator.audit_strategy_file('configs/strategies/my_strategy.yaml')"

# Test strategy with three-level framework
python scripts/run_three_level_tests.py strategies --strategy my_strategy

# Validate environment requirements
python scripts/setup_environment.py --validate-for-strategy my_strategy
```

## Available Action Types

**Data Operations:**
- `LOAD_DATASET_IDENTIFIERS` - Load biological identifiers from TSV/CSV
- `MERGE_DATASETS` - Combine multiple datasets with deduplication
- `FILTER_DATASET` - Apply filtering criteria to datasets
- `EXPORT_DATASET` - Export results to various formats

**Mapping Operations:**
- `MERGE_WITH_UNIPROT_RESOLUTION` - Map identifiers to UniProt
- `EXECUTE_MAPPING_PATH` - Run predefined mapping workflows
- `CALCULATE_SET_OVERLAP` - Calculate Jaccard similarity
- `CALCULATE_THREE_WAY_OVERLAP` - Specialized 3-way analysis

**Metabolomics Actions:**
- `NIGHTINGALE_NMR_MATCH` - Nightingale NMR reference matching
- `CTS_ENRICHED_MATCH` - Chemical Translation Service
- `METABOLITE_API_ENRICHMENT` - External metabolite APIs
- `SEMANTIC_METABOLITE_MATCH` - AI-powered matching
- `VECTOR_ENHANCED_MATCH` - Vector similarity matching
- `COMBINE_METABOLITE_MATCHES` - Merge matching approaches
- `GENERATE_METABOLOMICS_REPORT` - Analysis reports

## Key Files and Directories

```
/home/ubuntu/biomapper/
├── biomapper/                      # Core library
│   ├── core/
│   │   ├── strategy_actions/       # Action implementations  
│   │   ├── minimal_strategy_service.py
│   │   └── exceptions.py
│   └── mapping/
│       └── clients/                # External API clients
├── biomapper-api/                  # FastAPI service
│   ├── app/
│   │   ├── main.py
│   │   ├── services/
│   │   └── api/routes/
│   ├── alembic/                    # Database migrations
│   └── biomapper.db                # SQLite persistence
├── biomapper_client/               # Python client library
├── configs/                        # YAML configurations
│   ├── strategies/                 # Strategy definitions
│   └── schemas/                    # Validation schemas
├── tests/
│   ├── unit/                       # Unit tests
│   └── integration/                # Integration tests
├── scripts/
│   └── main_pipelines/            # Example client scripts
└── pyproject.toml                  # Poetry dependencies
```

## 🛡️ Strategy Configuration Best Practices (2025 Standards)

### MANDATORY: Standards Compliance Checklist

Before creating or modifying any strategy:

- [ ] **Parameter Naming**: All parameters use standard names (`input_key`, `output_key`, `file_path`)
- [ ] **Environment Integration**: Uses `EnvironmentManager` for configuration validation
- [ ] **File Loading**: Actions use `BiologicalFileLoader` for robust data ingestion
- [ ] **Identifier Normalization**: Biological IDs normalized for matching accuracy
- [ ] **Performance Optimization**: Large datasets handled with efficient algorithms
- [ ] **Edge Case Documentation**: Known issues like Q6EMK4 documented
- [ ] **Three-Level Testing**: Strategy tested at unit, integration, and production levels

### Strategy Development Workflow

```bash
# 1. Validate environment setup
python scripts/setup_environment.py

# 2. Create strategy with standard parameters
# (Use standard naming as shown above)

# 3. Validate parameter naming
python -c "from biomapper.core.standards.parameter_validator import ParameterValidator; ParameterValidator.audit_strategy_file('configs/strategies/my_strategy.yaml')"

# 4. Test with three-level framework
python scripts/run_three_level_tests.py strategies --strategy my_strategy

# 5. Run complexity audit if strategy includes custom logic
python audits/complexity_audit.py --strategy my_strategy

# 6. Document any edge cases found
python scripts/investigate_identifier.py PROBLEMATIC_ID --strategy my_strategy
```

### Environment Variable Integration

Strategies should use environment variables through the standardized manager:

```yaml
parameters:
  # Environment variables with fallbacks
  output_dir: "${BIOMAPPER_OUTPUT_DIR:-/tmp/results}"
  data_path: "${BIOMAPPER_DATA_DIR}/input.tsv"
  google_drive_folder: "${GOOGLE_DRIVE_FOLDER_ID}"
  
steps:
  - name: validate_environment
    action:
      type: VALIDATE_ENVIRONMENT_REQUIREMENTS
      params:
        required_features: ["google_drive", "data_paths"]
```

## Critical Notes

- **ALWAYS USE POETRY** - Never use pip directly: `poetry install --with dev,docs,api`
- **🎯 FOLLOW PARAMETER NAMING STANDARDS** - Use validator before committing
- **Run checks before committing**: `make check` or individual commands
- **Actions self-register** - Just use `@register_action` decorator
- **Strategies load from YAML** - No database, direct file loading
- **API-first architecture** - All scripts use BiomapperClient
- **Follow TDD** - Write failing tests first, then implement
- **Type safety migration** - Moving to Pydantic models throughout
- **Environment variables** - Use `EnvironmentManager` and setup wizard
- **Performance first** - Audit for O(n^2)+ complexity before production
- **Document edge cases** - Use debugging framework for issues like Q6EMK4