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

### Common Development Tasks

**Adding a New Mapping Client:**
1. Create new file in `biomapper/mapping/clients/`
2. Inherit from `BaseMappingClient`
3. Implement required methods: `map_entity()`, `validate_input()`
4. Add unit tests in `tests/unit/mapping/clients/`
5. Update strategy configuration schema if needed

**Creating a New Strategy Action:**
1. Add action class in `biomapper/core/actions/`
2. Inherit from `BaseAction`
3. Implement `execute()` method
4. Register in `ActionType` enum
5. Add tests and update documentation

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

## Important Notes

- ALWAYS USE POETRY ENVIRONMENT - Never use pip directly
- Configuration files in `configs/` are version-controlled examples
- Environment-specific settings use `.env` files (not committed)
- The project uses strict MyPy settings - resolve all type errors
- ChromaDB requires specific system dependencies on some platforms
- Integration tests may require external services (document in PR)