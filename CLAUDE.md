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
cd biomapper-api && poetry run uvicorn main:app --reload

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

Biomapper is a modular biological data harmonization toolkit with three main components:

1. **biomapper/** - Core library with mapping logic and orchestration
2. **biomapper-api/** - FastAPI service exposing REST endpoints
3. **biomapper_client/** - Python client for the API

### Core Components

- **core/**: Main executor, handlers, and strategy actions
  - `Executor`: Orchestrates mapping strategies
  - `ActionHandler`: Processes individual mapping actions
  - `ExecutionSet`: Manages execution state and checkpointing

- **mapping/**: Various biological database clients
  - Each client inherits from `BaseMappingClient`
  - Implements entity-specific mapping logic (proteins, genes, metabolites)
  - Examples: UniProtClient, OBOTermClient, EnsemblClient

- **rag/**: Retrieval Augmented Generation components
  - `QueryEngine`: Semantic search over biological data
  - Vector store implementations (ChromaDB, Qdrant, FAISS)
  - Document preprocessing and chunking

- **llm/**: LLM integration for intelligent mapping
  - OpenAI and Anthropic client wrappers
  - Prompt templates for biological entity mapping
  - Response parsing and validation

- **db/**: Database models and session management
  - SQLAlchemy async models
  - Alembic migrations in `alembic/`
  - Session management patterns

## Development Guidelines

### Code Standards

1. **Type Hints**: All functions must have complete type annotations
2. **Docstrings**: Use Google-style docstrings for all public methods
3. **Error Handling**: Use custom exceptions from `biomapper.core.exceptions`
4. **Async/Await**: Use async patterns for I/O operations
5. **Configuration**: Use Pydantic models for all configuration

### Testing Patterns

- Minimum 80% test coverage required
- Use pytest fixtures for common test data
- Mock external services in unit tests
- Integration tests should use test databases/APIs
- Follow Test-Driven Development (TDD) for new features and refactoring
- Write failing tests first, then implement minimal code to pass

### Test-Driven Development (TDD) Workflow

When adding new features or refactoring (especially for type safety):

1. **Red Phase**: Write failing tests that define the desired behavior
2. **Green Phase**: Implement minimal code to make tests pass
3. **Refactor Phase**: Improve code quality while keeping tests green

Example TDD cycle for adding Pydantic models:
```python
# 1. RED: Write failing test
def test_action_params_validation():
    params = ExecuteMappingPathParams(path_name="test")
    assert params.path_name == "test"
    
    with pytest.raises(ValidationError):
        ExecuteMappingPathParams()  # Missing required field

# 2. GREEN: Implement model
class ExecuteMappingPathParams(BaseModel):
    path_name: str = Field(..., min_length=1)

# 3. REFACTOR: Add more validation, docs, etc.
```

### Common Development Tasks

**Adding a New Mapping Client:**
1. Create new file in `biomapper/mapping/clients/`
2. Inherit from `BaseMappingClient`
3. Implement required methods: `map_entity()`, `validate_input()`
4. Add unit tests in `tests/unit/mapping/clients/`
5. Update strategy configuration schema if needed

**Creating a New Strategy Action:**
1. Write failing tests for the new action (TDD approach)
2. Add action class in `biomapper/core/strategy_actions/`
3. Inherit from `BaseStrategyAction` (or `TypedStrategyAction` for new actions)
4. Define Pydantic models for parameters and results
5. Implement `execute()` method with type safety
6. Use `@register_action("ACTION_NAME")` decorator for auto-registration
7. Add action to strategy validation registry
8. Update documentation

**Working with Configurations:**
- Strategy configs go in `configs/strategies/`
- Client configs go in `configs/clients/`
- All configs use YAML format with Pydantic validation

### API Development

When working on biomapper-api:
- Use dependency injection for database sessions
- Implement proper error handling with HTTPException
- Add OpenAPI documentation to endpoints
- Use Pydantic models for request/response validation
- Follow RESTful conventions

### Database Guidelines

- Always use async SQLAlchemy sessions
- Create Alembic migrations for schema changes
- Use proper transaction management
- Index frequently queried fields
- Follow naming conventions: snake_case for tables/columns

## Type Safety and Pydantic Integration

### Current Type Safety Initiative

Biomapper is transitioning to full type safety using Pydantic models:

1. **Strategy Actions**: Moving from `Dict[str, Any]` to typed Pydantic models
2. **Execution Context**: Replacing untyped context dictionaries with `StrategyExecutionContext`
3. **YAML Validation**: Strategy configurations validated at load time
4. **Backward Compatibility**: Maintaining dict interfaces during migration

### Implementing Type-Safe Actions

**For new actions:**
```python
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.models import ActionParams, ActionResult

class MyActionParams(BaseModel):
    required_field: str
    optional_field: int = 100

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, ...) -> ActionResult:
        # Type-safe implementation
        pass
```

**For migrating existing actions:**
1. Create Pydantic models for params and results
2. Add `execute_typed()` method alongside existing `execute()`
3. Implement compatibility wrapper in base class
4. Gradually deprecate dict-based interface

## Important Notes

- ALWAYS USE POETRY ENVIRONMENT - Never use pip directly
- Configuration files in `configs/` are version-controlled examples
- Environment-specific settings use `.env` files (not committed)
- The project uses strict MyPy settings - resolve all type errors
- ChromaDB requires specific system dependencies on some platforms
- Integration tests may require external services (document in PR)
- Follow TDD approach for all new features and refactoring
- Maintain backward compatibility during type safety migration

## Key Action Types

The biomapper orchestration system supports these core actions:

- **LOAD_DATASET_IDENTIFIERS**: Load biological identifiers from TSV/CSV files
- **MERGE_WITH_UNIPROT_RESOLUTION**: Map identifiers to UniProt accessions
- **CALCULATE_SET_OVERLAP**: Calculate Jaccard similarity between datasets
- **MERGE_DATASETS**: Combine multiple datasets with deduplication
- **EXECUTE_MAPPING_PATH**: Run predefined mapping workflows
- **FILTER_DATASET**: Apply filtering criteria to datasets
- **EXPORT_DATASET**: Export results to various formats

See strategy configuration examples in `configs/strategies/` for usage patterns.