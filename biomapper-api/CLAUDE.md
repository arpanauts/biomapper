# CLAUDE.md - Biomapper API Development Guide (2025 Standards)

This file provides guidance to Claude Code (claude.ai/code) when working with the biomapper API service.

**🎯 CRITICAL**: API development MUST follow the 2025 standardizations, especially environment configuration and API method alignment.

## Essential Commands

```bash
# Setup and environment (NEW - 2025 standards)
poetry install --with dev,docs,api
poetry shell

# Environment validation (REQUIRED before API development)
python scripts/setup_environment.py        # Interactive environment setup wizard
python -c "from biomapper.core.standards.env_manager import EnvironmentManager; EnvironmentManager().validate_requirements(['google_drive', 'database'])"

# Run tests (Enhanced with three-level framework)
poetry run pytest                           # All tests
poetry run pytest tests/unit/               # Unit tests only (Level 1)
poetry run pytest tests/integration/        # Integration tests only (Level 2)
poetry run pytest -k "test_name"            # Specific test
poetry run pytest -xvs tests/path/test.py   # Debug single test with output
python scripts/run_three_level_tests.py api # Three-level API tests

# API method validation (NEW - prevent silent failures)
python -c "from biomapper.core.standards.api_validator import APIMethodValidator; APIMethodValidator.validate_all_registered_clients()"

# Code quality checks (run these before committing)
poetry run ruff format .                    # Format code
poetry run ruff check . --fix               # Fix linting issues
poetry run mypy biomapper biomapper-api biomapper_client  # Type checking

# Development server (with environment validation)
python -c "from biomapper.core.standards.env_manager import EnvironmentManager; EnvironmentManager().validate_requirements(['database'])" # Validate first
cd biomapper-api && poetry run uvicorn app.main:app --reload --port 8000

# Database operations
poetry run alembic upgrade head             # Apply migrations
poetry run alembic revision -m "description"  # Create migration

# Performance and complexity analysis (NEW)
python audits/complexity_audit.py --api     # Check API endpoint complexity
python scripts/investigate_identifier.py Q6EMK4 --via-api  # Debug via API

# Makefile shortcuts
make test                                   # Tests with coverage
make format                                 # Format code
make lint-fix                              # Auto-fix linting
make typecheck                             # Run mypy
make check                                 # Run all checks + docs

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

**biomapper/** - Core library
- Actions self-register via `@register_action("ACTION_NAME")` decorator in `biomapper/core/strategy_actions/registry.py`
- `MinimalStrategyService` loads YAML strategies from `configs/` at runtime
- Execution context flows through actions as `Dict[str, Any]` containing `current_identifiers`, `datasets`, `statistics`, `output_files`

**biomapper-api/** - FastAPI service  
- Routes in `app/api/routes/` - main endpoints: `strategies_v2_simple.py`, `jobs.py`, `mapping.py`
- `MapperService` orchestrates background jobs with SQLite persistence (`biomapper.db`)
- Direct YAML loading - no database intermediary for strategies

**biomapper_client/** - Python client
- `BiomapperClient` in `client_v2.py` - primary interface for all scripts
- Synchronous wrapper: `client.run("strategy_name")` for simple usage
- Progress tracking with real-time SSE events

## 🛡️ API Development Standards (2025 Framework)

### MANDATORY: Environment Configuration Integration

All API endpoints MUST validate environment requirements:

```python
# app/api/routes/my_endpoint.py
from fastapi import APIRouter, HTTPException
from biomapper.core.standards.env_manager import EnvironmentManager
from biomapper.core.standards.api_validator import APIMethodValidator

router = APIRouter()

@router.post("/my-endpoint")
async def my_endpoint_handler(request: MyRequest):
    # 1. ENVIRONMENT VALIDATION (Required for all endpoints)
    env_manager = EnvironmentManager()
    try:
        env_manager.validate_requirements(['google_drive', 'database'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Environment configuration error: {e}")
    
    # 2. API CLIENT VALIDATION (Required for external API calls)
    if hasattr(self, '_external_client'):
        APIMethodValidator.validate_client_interface(
            self._external_client, 
            required_methods=['search', 'get_data']
        )
    
    # 3. Use standardized context handling
    from biomapper.core.standards.context_handler import UniversalContext
    ctx = UniversalContext.wrap(execution_context)
    
    # Implementation logic here
    return {"status": "success"}
```

### Creating New Strategy Actions (2025 Standards)

Actions self-register and require standardized base classes:

```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.standards.base_models import ActionParamsBase  # NEW: Flexible base
from biomapper.core.standards.context_handler import UniversalContext  # NEW: Context handling

class MyActionParams(ActionParamsBase):  # NEW: Inherits debug/trace/timeout
    input_key: str = Field(..., description="Input dataset key")  # STANDARD NAME
    output_key: str = Field(..., description="Output dataset key")  # STANDARD NAME
    threshold: float = Field(0.8, description="Processing threshold")

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, context: Dict) -> ActionResult:
        # NEW: Use standardized context handling
        ctx = UniversalContext.wrap(context)
        
        # NEW: Environment validation for external dependencies
        if params.requires_external_api:
            env_manager = EnvironmentManager()
            env_manager.validate_requirements(['api_access'])
        
        # Implementation - use standardized patterns
        input_data = ctx.get_dataset(params.input_key)
        processed_data = self._process_with_standards(input_data)
        ctx.set_dataset(params.output_key, processed_data)
        
        return ActionResult(success=True, message=f"Processed {len(processed_data)} items")
```

### API Testing with Three-Level Framework

```python
# tests/integration/api/test_my_endpoint.py
from biomapper.testing.base import APITestBase
from biomapper.testing.data_generator import BiologicalDataGenerator

class TestMyEndpoint(APITestBase):
    
    def test_level_1_minimal_request(self):
        """Level 1: Fast API test with minimal data (<1s)"""
        minimal_request = {"input_data": BiologicalDataGenerator.generate_uniprot_dataset(3)}
        response = self.client.post("/my-endpoint", json=minimal_request)
        assert response.status_code == 200
        
    def test_level_2_sample_request(self):
        """Level 2: Integration test with sample data (<10s)"""
        sample_request = {"input_data": BiologicalDataGenerator.generate_uniprot_dataset(100)}
        response = self.client.post("/my-endpoint", json=sample_request)
        assert response.status_code == 200
        # Validate performance
        assert response.elapsed.total_seconds() < 5.0
        
    def test_level_3_production_load(self):
        """Level 3: Production-like load test (<60s)"""
        large_request = {"input_data": BiologicalDataGenerator.generate_uniprot_dataset(1000)}
        response = self.client.post("/my-endpoint", json=sample_request)
        assert response.status_code == 200
        # Validate scalability
        self.assert_linear_scaling(response.elapsed, len(large_request["input_data"]))
```

## Creating YAML Strategies

Create in `configs/strategies/`:

```yaml
name: MY_STRATEGY
description: Clear purpose description
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
```

Test via: `BiomapperClient().run("MY_STRATEGY")`

## Available Actions

**Data Operations:**
- `LOAD_DATASET_IDENTIFIERS` - Load TSV/CSV biological identifiers
- `MERGE_DATASETS` - Combine with deduplication
- `FILTER_DATASET` - Apply filtering criteria

**Mapping Operations:**
- `MERGE_WITH_UNIPROT_RESOLUTION` - Map to UniProt accessions
- `CALCULATE_SET_OVERLAP` - Jaccard similarity analysis
- `CALCULATE_THREE_WAY_OVERLAP` - Three-dataset analysis

**Metabolomics:**
- `NIGHTINGALE_NMR_MATCH` - NMR reference matching
- `CTS_ENRICHED_MATCH` - Chemical Translation Service
- `SEMANTIC_METABOLITE_MATCH` - AI-powered matching
- `VECTOR_ENHANCED_MATCH` - Vector similarity
- `COMBINE_METABOLITE_MATCHES` - Merge approaches
- `GENERATE_METABOLOMICS_REPORT` - Analysis reports

## Key Implementation Patterns

### Action Context Flow
- Actions receive and modify shared `context` dictionary
- Previous action outputs available via `context["datasets"][key]`
- Statistics accumulate in `context["statistics"]`

### Error Handling
- Use custom exceptions from `biomapper.core.exceptions`
- Actions should handle and log errors gracefully
- Failed actions set `success=False` in ActionResult

### Testing Strategy
- Write failing tests first (TDD)
- Mock external services in unit tests
- Integration tests use test data in `data/test_data/`
- Minimum 80% coverage required

## Important Notes (2025 Standards)

- **Poetry only** - Never use pip directly
- **🎯 FOLLOW ALL 10 STANDARDIZATIONS** - Critical for API reliability
- **Environment validation FIRST** - Use `EnvironmentManager` before any API operations
- **API method validation** - Use `APIMethodValidator` to prevent silent failures
- **Type safety** - Project uses strict mypy, resolve all type errors
- **No database loading** - Strategies load from YAML at runtime
- **API-first** - All scripts use BiomapperClient, no direct core imports
- **Backwards compatibility** - Maintained through flexible base models
- **Job persistence** - SQLite (`biomapper.db`) for execution state
- **Performance first** - Use complexity checker to prevent O(n^2)+ endpoints
- **Three-level testing** - All API endpoints must have Level 1, 2, 3 tests
- **Edge case debugging** - Document Q6EMK4-style issues in registry

## API Development Checklist (2025 Standards)

Before deploying any API changes:

- [ ] **Environment Integration**: Endpoints validate required environment features
- [ ] **API Method Validation**: External clients validated with `APIMethodValidator`
- [ ] **Parameter Naming**: Request/response models use standard parameter names
- [ ] **Context Handling**: Uses `UniversalContext.wrap()` for execution contexts
- [ ] **Performance Audited**: Endpoints checked for algorithmic complexity
- [ ] **Three-Level Testing**: Fast unit, integration, and production-load tests
- [ ] **Error Handling**: Comprehensive error responses with actionable messages
- [ ] **Documentation**: OpenAPI schemas updated with examples

## Pre-Deployment Commands

```bash
# 1. Validate environment setup
python scripts/setup_environment.py --validate-for-api

# 2. Check API method alignment
python -c "from biomapper.core.standards.api_validator import APIMethodValidator; APIMethodValidator.validate_all_registered_clients()"

# 3. Run three-level API tests
python scripts/run_three_level_tests.py api --performance

# 4. Audit endpoint complexity
python audits/complexity_audit.py --api

# 5. Validate all checks pass
make check
```