---
name: test-ci-local
description: Run pytest in a Docker container that replicates the GitHub Actions CI environment
---

# Test CI Locally

You should run tests in a Docker container that replicates the GitHub Actions CI environment to catch issues before pushing to the repository.

## Setup Steps

1. **Check for existing Docker files**:
   - Look for `Dockerfile.ci` and `docker-compose.ci.yml` in the project root
   - If they don't exist, create them

2. **Create/Update Dockerfile.ci** if needed:
```dockerfile
# CI Testing Environment - Replicates GitHub Actions
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY README.md ./
COPY biomapper ./biomapper
COPY biomapper-api ./biomapper-api
COPY biomapper_client ./biomapper_client
COPY tests ./tests
COPY configs ./configs
COPY conftest.py ./
COPY CLAUDE.md ./

# Install dependencies for main project
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-root

# Install dependencies for biomapper-api
WORKDIR /app/biomapper-api
RUN poetry install --no-interaction --no-root

# Back to main directory
WORKDIR /app

# Set environment variables to match CI
ENV LANGFUSE_ENABLED=false
ENV PYTHONPATH=/app:/app/biomapper-api:$PYTHONPATH

# Default command - run tests
CMD ["poetry", "run", "pytest", "-v"]
```

3. **Create/Update docker-compose.ci.yml** if needed:
```yaml
services:
  ci-test:
    build:
      context: .
      dockerfile: Dockerfile.ci
    volumes:
      # Mount source for live changes
      - ./biomapper:/app/biomapper
      - ./biomapper-api:/app/biomapper-api
      - ./biomapper_client:/app/biomapper_client
      - ./tests:/app/tests
      - ./configs:/app/configs
    environment:
      - LANGFUSE_ENABLED=false
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
    command: >
      bash -c "
        echo '=== CI Environment Test Runner ===' &&
        echo 'Running pytest with CI configuration...' &&
        poetry run pytest -v --tb=short
      "
```

## Execution Steps

1. **Build the Docker image**:
```bash
sudo docker compose -f docker-compose.ci.yml build
```

2. **Run all tests**:
```bash
sudo docker compose -f docker-compose.ci.yml run --rm ci-test
```

3. **Run specific test files**:
```bash
sudo docker compose -f docker-compose.ci.yml run --rm ci-test poetry run pytest tests/services/test_persistent_execution_engine.py -v
```

4. **Run with coverage**:
```bash
sudo docker compose -f docker-compose.ci.yml run --rm ci-test poetry run pytest --cov=biomapper --cov-report=term-missing
```

5. **Debug a specific failing test**:
```bash
sudo docker compose -f docker-compose.ci.yml run --rm ci-test poetry run pytest tests/path/to/test.py::TestClass::test_method -xvs
```

6. **Clean database and re-run** (for database-related issues):
```bash
sudo docker compose -f docker-compose.ci.yml run --rm ci-test bash -c "rm -f biomapper.db && poetry run pytest"
```

## Common Issues and Fixes

### SQLite Autoincrement Issues
- **Problem**: `NOT NULL constraint failed: execution_logs.id`
- **Solution**: Ensure models use `Integer` (not `BigInteger`) for autoincrement columns in SQLite:
  ```python
  id = Column(Integer, primary_key=True, autoincrement=True)
  ```

### Langfuse Connection Errors
- **Problem**: Tests try to connect to Langfuse
- **Solution**: Ensure `LANGFUSE_ENABLED=false` is set in environment and `conftest.py` disables it

### Import Path Issues
- **Problem**: `ModuleNotFoundError` for app imports
- **Solution**: Check `PYTHONPATH` includes both `/app` and `/app/biomapper-api`

### Missing Dependencies
- **Problem**: Module import errors
- **Solution**: Rebuild the Docker image after updating dependencies:
  ```bash
  sudo docker compose -f docker-compose.ci.yml build --no-cache
  ```

## Workflow Recommendation

1. **Before pushing any code**, run:
   ```bash
   sudo docker compose -f docker-compose.ci.yml run --rm ci-test
   ```

2. **If tests fail**, debug locally in Docker:
   ```bash
   # Run specific failing test with verbose output
   sudo docker compose -f docker-compose.ci.yml run --rm ci-test poetry run pytest path/to/failing/test.py -xvs
   ```

3. **Fix issues and re-test** in Docker before committing

4. **Only push to GitHub** after all tests pass locally in the CI environment

This approach will significantly reduce CI failures on GitHub Actions!