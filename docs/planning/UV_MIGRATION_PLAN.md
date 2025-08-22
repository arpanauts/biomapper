# BioMapper Poetry → UV Migration Plan

> **Status**: Planning Phase  
> **Created**: 2025-08-18  
> **Last Updated**: 2025-08-18 (Added Package Cleanup Phase)  
> **Reviewed By**: ActivePieces Gemini AI

## Executive Summary

This document outlines a comprehensive migration strategy for converting the BioMapper project from Poetry to UV (Ultra-fast Python package manager). The migration addresses a complex bioinformatics project with 75+ dependencies, 1,297 tests, and a modern src-layout structure.

**Key Benefits of Migration:**
- 10-100x faster dependency resolution and installation
- Improved CI/CD performance with better caching
- Modern PEP 621 project configuration
- Single binary tool with built-in Python management
- Better compatibility with modern Python tooling

**Migration Complexity Level**: High → Medium (with cleanup)
- Complex dependency tree with ML packages (torch, transformers)
- **NEW: 54% of packages potentially unused - cleanup opportunity**
- Private git dependencies
- Src-layout package structure
- Self-registering action system
- FastAPI service with background jobs
- Comprehensive test suite requiring validation

**Package Cleanup Opportunity**: 
Analysis reveals 42 of 78 packages (54%) are potentially unused. Removing these before migration will significantly reduce complexity and improve success likelihood.

## Current Project State

### Dependencies & Structure
- **Python Version**: 3.11+
- **Package Manager**: Poetry 2.1.3
- **Dependencies**: 78 packages (42 potentially unused - 54%)
- **Structure**: Modern src-layout with packages in `src/`
- **Test Coverage**: 1,297 tests with 79.69% coverage
- **Build System**: `poetry-core` masonry API
- **Package Analysis**: 29 confirmed used, 4 test-only, 3 type stubs, 42 potentially unused

### Key Components
- **CLI Entry Point**: `cli.minimal:cli`
- **API Server**: FastAPI with uvicorn
- **Dependency Groups**: main, dev, docs, api
- **Private Dependencies**: `phenome-arivale` from git
- **CI/CD**: GitHub Actions with Poetry

### Critical Dependencies to Validate
```toml
# ML & Science Stack
torch = "^2.2.0"
transformers = "^4.38.2"
sentence-transformers = "^2.2.2"
faiss-cpu = "^1.10.0"
chromadb = "^0.6.2"

# Private Repository
phenome-arivale = {git = "https://git.phenome.health/trent.leslie/phenome-arivale"}

# Web Framework
fastapi = {version = ">=0.104.1", optional = true}
uvicorn = {version = ">=0.24.0", optional = true}
```

## Phase 0: Pre-Migration Analysis & Preparation

### Step 0: Package Cleanup (NEW - Highly Recommended)

**Removing unused packages before migration will:**
- Simplify dependency resolution (54% fewer packages)
- Reduce potential compatibility issues
- Speed up installation times (both Poetry and UV)
- Make troubleshooting easier
- Reduce migration complexity

**Package Usage Analysis Results:**
```
Total Packages: 78
Confirmed Used: 29 (37%)
Test-Only: 4 (5%)
Type Stubs: 3 (4%)
Potentially Unused: 42 (54%)
```

**Safe to Remove (Low Risk):**
1. **Duplicate Libraries:**
   - `venn` + `upsetplot` + `matplotlib-venn` (keep only one)
   - `pyarango` + `python-arango` (keep only one)
   - `thefuzz` + `fuzzywuzzy` (keep only one)

2. **Unused ML/AI Libraries:**
   - `dspy-ai` (^2.1.8) - DSPy framework
   - `sentence-transformers` (^2.2.2) - If embeddings not used
   - `faiss-cpu` (^1.10.0) - If vector search not used
   - `fastembed` (^0.5.1) - If fast embeddings not used

3. **Unused Visualization:**
   - `adjusttext` (^1.3.0) - Plot text adjustment
   - `plotly` (^6.3.0) - If interactive plots not used
   - `statsmodels` (^0.14.4) - If statistical models not used

4. **Unused Chemistry/Bio Libraries:**
   - `rdkit` (^2023.9.1) - Chemistry toolkit
   - `libchebipy` (1.0.10) - ChEBI database

**Verification Process:**
```bash
# Check if package is actually used
grep -r "import torch\|from torch" src/ tests/
grep -r "import matplotlib\|from matplotlib" src/ tests/

# Check dependency tree
poetry show --tree package-name

# Run package usage analysis
python scripts/analyze_package_usage.py
```

**Cleanup Steps:**
1. Remove 5-10 packages at a time from pyproject.toml
2. Run `poetry lock --no-update`
3. Run `poetry install`
4. Run full test suite: `poetry run pytest`
5. If tests pass, commit changes
6. Repeat until all unused packages removed

**Packages Requiring Manual Verification:**
- `pyyaml` - Used as `import yaml` (keep)
- `sqlalchemy` - Database layer (verify usage)
- `alembic` - Database migrations (verify usage)
- `torch`/`transformers` - ML models (check integrations)
- `chromadb`/`qdrant-client` - Vector databases (check usage)
- `anthropic` - Claude API (check if used)
- `langfuse` - Monitoring (check if used)

### Step 1: Dependency Compatibility Assessment

**Create compatibility matrix for all dependencies:**

1. **Core Dependencies Validation**
   ```bash
   # Test each major dependency group
   uv add torch transformers sentence-transformers faiss-cpu
   uv add fastapi uvicorn
   uv add chromadb qdrant-client
   uv add pandas numpy matplotlib seaborn
   ```

2. **Private Repository Testing**
   ```bash
   # Test private git dependency
   uv add "phenome-arivale @ git+https://git.phenome.health/trent.leslie/phenome-arivale"
   ```

3. **Build Dependencies**
   ```bash
   # Test build-related packages
   uv add pydantic sqlalchemy alembic
   ```

**Compatibility Checklist:**
- [ ] All main dependencies install without errors
- [ ] Private git repository accessible
- [ ] ML dependencies with proper CUDA support (if needed)
- [ ] No conflicting version constraints
- [ ] Build dependencies function correctly

### Step 2: Create Comprehensive Rollback Plan

**Backup Critical Files:**
```bash
# Create backup directory
mkdir -p migration_backup/$(date +%Y%m%d_%H%M%S)

# Backup current working state
cp poetry.lock migration_backup/$(date +%Y%m%d_%H%M%S)/
cp poetry.toml migration_backup/$(date +%Y%m%d_%H%M%S)/
cp pyproject.toml migration_backup/$(date +%Y%m%d_%H%M%S)/
cp -r .venv migration_backup/$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || echo "No .venv to backup"
```

**Rollback Script:**
```bash
#!/bin/bash
# rollback_to_poetry.sh
echo "Rolling back to Poetry configuration..."
BACKUP_DIR="migration_backup/$(ls migration_backup/ | tail -1)"
cp $BACKUP_DIR/poetry.lock .
cp $BACKUP_DIR/poetry.toml .
cp $BACKUP_DIR/pyproject.toml .
poetry install --with dev,docs --extras api
echo "Rollback complete. Test with: poetry run pytest"
```

### Step 3: Dependency Mapping Documentation

**Poetry → UV Mapping:**
```toml
# Poetry Format (Current)
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.25.1"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
mypy = "^1.14.1"

[tool.poetry.extras]
api = ["fastapi", "uvicorn"]

# UV/PEP 621 Format (Target)
[project]
name = "biomapper"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.25.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "mypy>=1.14.1",
]
api = [
    "fastapi>=0.104.1",
    "uvicorn>=0.24.0",
]
```

## Phase 1: Pilot Migration

### Step 4: Isolated Module Testing

**Choose pilot module:** `src/core/standards/`
- Self-contained with minimal external dependencies
- Used by other modules (good test of import resolution)
- Has comprehensive tests

**Create test environment:**
```bash
# Create isolated test directory
mkdir -p uv_pilot_test
cd uv_pilot_test

# Copy pilot module and tests
cp -r ../src/core/standards/ ./
cp -r ../tests/unit/core/standards/ ./tests/

# Create minimal pyproject.toml for testing
cat > pyproject.toml << EOF
[project]
name = "biomapper-pilot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.11.4",
    "pandas>=2.0.0",
    "pyyaml>=6.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-cov>=4.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF
```

**Test pilot migration:**
```bash
uv sync --all-extras
uv run pytest tests/ -v
```

### Step 5: UV Installation and Basic Testing

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version

# Test basic functionality
uv python list
uv python install 3.11
```

## Phase 2: Incremental Conversion

### Step 6: Convert pyproject.toml (Stage 1)

**Create new PEP 621 compliant pyproject.toml:**

```toml
[project]
name = "biomapper"
version = "0.5.2"
description = "A unified Python toolkit for biological data harmonization and ontology mapping"
authors = [
    {name = "Trent Leslie", email = "trent.leslie@phenomehealth.org"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.11"
keywords = [
    "bioinformatics",
    "ontology",
    "data mapping",
    "biological data",
    "standardization",
    "harmonization"
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Programming Language :: Python :: 3.11",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Natural Language :: English"
]

# Core dependencies (converted from Poetry format)
dependencies = [
    "requests>=2.25.1",
    "numpy>=2.1.0",
    "pandas>=2.0.0",
    "sqlalchemy[asyncio]>=2.0.40",
    "pyyaml>=6.0.1",
    "tqdm>=4.66.1",
    "libChEBIpy==1.0.10",
    "matplotlib>=3.8.0",
    "seaborn>=0.13.0",
    "upsetplot>=0.8.0",
    "venn>=0.1.3",
    "langfuse>=2.57.1",
    "openai>=1.14.0",
    "python-dotenv>=1.0.1",
    "structlog>=24.1.0",
    "dspy-ai>=2.1.8",
    "cloudpickle>=3.0.0",
    "python-multipart>=0.0.18",
    "cryptography>=43.0.1",
    "rdkit>=2023.9.1",
    "chromadb>=0.6.2",
    "torch>=2.2.0",
    "transformers>=4.38.2",
    "sentence-transformers>=2.2.2",
    "aiohttp>=3.11.11",
    "pyarango>=2.1.1",
    "fastembed>=0.5.1",
    "faiss-cpu>=1.10.0",
    "lxml>=5.3.1",
    "aiosqlite>=0.21.0",
    "python-arango>=8.1.6",
    "psutil>=7.0.0",
    "pydantic>=2.11.4",
    "alembic>=1.15.2",
    "pydantic-settings>=2.9.1",
    "qdrant-client>=1.14.2",
    "anthropic>=0.52.0",
    "cachetools>=5.0.0,<6.0.0",
    "thefuzz>=0.22.1",
    "matplotlib-venn>=1.1.2",
    "statsmodels>=0.14.4",
    "adjusttext>=1.3.0",
    "scikit-learn>=1.3.0",
    "markdown>=3.4",
    "jinja2>=3.1",
    "python-levenshtein>=0.27.1",
    "fuzzywuzzy>=0.18.0",
    "plotly>=6.3.0",
    "google-api-python-client>=2.0.0,<3.0.0",
    "google-auth-httplib2>=0.1.0",
    "google-auth-oauthlib>=1.2.2",
    "odfpy>=1.4.1",
    "openpyxl>=3.1.5",
]

[project.optional-dependencies]
# Development dependencies
dev = [
    "pytest>=7.4.3",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.14.0",
    "mypy>=1.14.1",
    "ruff>=0.1.6",
    "jupyter>=1.1.1",
    "ipykernel>=6.29.5",
    "types-requests>=2.31.0.20240311",
    "pandas-stubs>=2.2.3.241126",
    "types-tqdm>=4.67.0.20241119",
    "requests-mock>=1.11.0",
    "pytest-asyncio>=0.21.1",
    "phenome-arivale @ git+https://git.phenome.health/trent.leslie/phenome-arivale",
    "autoflake>=2.3.1",
    "vulture>=2.14",
    "chardet>=5.2.0",
    "responses>=0.25.8",
    "respx>=0.22.0",
]

# Documentation dependencies
docs = [
    "sphinx>=8.1.3",
    "sphinx-rtd-theme>=3.0.2",
    "sphinx-autodoc-typehints>=3.0.0",
    "myst-parser>=4.0.0",
    "sphinxcontrib-mermaid>=1.0.0",
    "matplotlib>=3.10.3",
]

# API dependencies
api = [
    "fastapi>=0.104.1",
    "uvicorn>=0.24.0",
]

# Full feature set
full = [
    "fastapi>=0.104.1",
    "uvicorn>=0.24.0",
]

[project.scripts]
biomapper = "cli.minimal:cli"

[project.urls]
Repository = "https://github.com/arpanauts/biomapper"
Documentation = "https://biomapper.readthedocs.io/"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# Hatchling configuration for src-layout
[tool.hatchling.packages]
src = "src"

# Keep all existing tool configurations
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = ["examples", ".venv", ".git", "docs", "build", "dist"]
python_files = ["test_*.py"]
addopts = "-ra --cov=src --cov-report=term-missing"
markers = [
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.ruff]
select = ["E", "F", "B", "I", "C4", "DTZ", "RUF", "N", "D", "UP", "S"]
ignore = ["D203", "D213", "F401"]
line-length = 88

[tool.ruff.per-file-ignores]
"tests/**/*.py" = []
"**/__init__.py" = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.ruff.pydocstyle]
convention = "google"

[tool.ruff.isort]
known-first-party = ["biomapper"]
combine-as-imports = true

[tool.coverage.run]
source = ["src"]
omit = [
    "tests/*",
    "**/__init__.py",
    "**/cli.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "pass",
    "raise ImportError",
    "raise NotImplementedError"
]
show_missing = true
fail_under = 75

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
check_untyped_defs = true
strict_optional = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
show_error_codes = true
pretty = true
sqlite_cache = true
plugins = ["numpy.typing.mypy_plugin"]

[[tool.mypy.overrides]]
module = [
    "libchebipy.*",
    "torch.*",
    "chromadb.*",
    "dspy.*",
    "langfuse.*"
]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
```

### Step 7: Test Critical Dependencies

**Validate core functionality:**
```bash
# Test dependency installation
uv sync --all-extras

# Verify imports work
uv run python -c "import torch; print('Torch:', torch.__version__)"
uv run python -c "import transformers; print('Transformers:', transformers.__version__)"
uv run python -c "import fastapi; print('FastAPI:', fastapi.__version__)"

# Test private dependency
uv run python -c "import phenome_arivale; print('Private repo working')"
```

### Step 8: Generate and Validate Lock File

```bash
# Generate UV lock file
uv lock

# Sync all dependencies
uv sync --all-extras

# Verify environment
uv run python --version
uv run pip list
```

## Phase 3: Comprehensive Testing Strategy

### Step 9: Multi-Level Testing Approach

**Level 1: Unit Tests (Fast)**
```bash
# Run core unit tests
uv run pytest tests/unit/ -v --maxfail=5

# Test specific modules
uv run pytest tests/unit/core/ -v
uv run pytest tests/unit/actions/ -v
uv run pytest tests/unit/client/ -v
```

**Level 2: Integration Tests**
```bash
# Test API integration
uv run pytest tests/integration/ -v

# Test CLI functionality
uv run biomapper --help
uv run biomapper health
uv run biomapper test-import
```

**Level 3: Full Test Suite**
```bash
# Run all 1,297 tests
uv run pytest -c pytest-ci.ini --cov=src --cov-report=html

# Verify coverage targets
# Target: 79.69% (current level with Poetry)
```

**Level 4: Build and Installation Tests**
```bash
# Test package building
uv build

# Test wheel installation
pip install dist/*.whl

# Test CLI from installed package
biomapper --help
```

### Step 10: CI Pipeline Testing

**Create test branch with UV configuration:**
```yaml
# .github/workflows/ci-uv-test.yml
name: Biomapper CI (UV Test)

on:
  push:
    branches: [ uv-migration-test ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
    
    - name: Install UV
      uses: astral-sh/setup-uv@v4
      with:
        enable-cache: true
        cache-dependency-glob: "uv.lock"
    
    - name: Set up Python 3.11
      run: uv python install 3.11
    
    - name: Install dependencies
      run: uv sync --all-extras
    
    - name: Run linting
      run: |
        uv run ruff check src/ tests/ --exit-zero
        uv run ruff format --check src/ tests/ --quiet || echo "Format check completed with warnings"
    
    - name: Run type checking
      run: |
        uv run mypy src/ --ignore-missing-imports --no-error-summary || echo "Type checking completed with warnings"
    
    - name: Run tests
      env:
        DATABASE_URL: "sqlite+aiosqlite:///./test.db"
        LANGFUSE_ENABLED: "false"
        PYTHONPATH: "${{ github.workspace }}/src:$PYTHONPATH"
      run: |
        uv run pytest -c pytest-ci.ini --cov=src --cov-report=xml --cov-report=term-missing
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      if: success()
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: false
```

**Performance Comparison:**
- Measure total CI runtime with Poetry vs UV
- Compare dependency installation time
- Monitor cache effectiveness

## Phase 4: Documentation & Source Updates

### Step 11: Update Source Code References

**Update `src/cli/minimal.py`:**
```python
# Before (Poetry):
subprocess.run(['poetry', 'run', 'uvicorn', ...])
click.echo("❌ Poetry not found. Make sure you're in the poetry environment.")
click.echo("   • poetry run biomapper health")

# After (UV):
subprocess.run(['uv', 'run', 'uvicorn', ...])
click.echo("❌ UV not found. Make sure you have UV installed.")
click.echo("   • uv run biomapper health")
```

### Step 12: Update Documentation

**CLAUDE.md Updates:**
```markdown
# Before:
poetry install --with dev,docs,api
poetry shell
poetry run pytest

# After:
uv sync --all-extras
source .venv/bin/activate  # UV auto-creates venv
uv run pytest
```

**README.md Updates:**
```markdown
# Before:
from biomapper.client.client_v2 import BiomapperClient
poetry run uvicorn biomapper.api.main:app

# After:
from src.client.client_v2 import BiomapperClient
uv run uvicorn api.main:app
```

**Makefile Updates:**
```makefile
# Before:
test:
	poetry run pytest --cov=src --cov-report=term-missing tests/

# After:
test:
	uv run pytest --cov=src --cov-report=term-missing tests/
```

### Step 13: Update CI/CD Configurations

**GitHub Actions (replace existing):**
- Install UV instead of Poetry
- Use UV caching instead of Poetry cache
- Update all `poetry run` commands to `uv run`

**Dockerfile.ci Updates:**
```dockerfile
# Before:
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"
RUN poetry install --with dev,docs,api --no-interaction

# After:
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv sync --all-extras --frozen
```

## Phase 5: Validation & Deployment

### Step 14: Comprehensive End-to-End Testing

**Functional Validation:**
```bash
# 1. Full test suite must pass
uv run pytest -c pytest-ci.ini --cov=src
# Expected: All 1,297 tests pass with 79.69%+ coverage

# 2. API server functionality
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 &
curl http://localhost:8000/health
curl http://localhost:8000/api/docs

# 3. CLI functionality
uv run biomapper --help
uv run biomapper health
uv run biomapper metadata list

# 4. Client library
uv run python -c "
from src.client.client_v2 import BiomapperClient
client = BiomapperClient('http://localhost:8000')
print('Client created successfully')
"

# 5. Strategy execution (if test data available)
# uv run python -c "
# from src.client.client_v2 import BiomapperClient
# client = BiomapperClient()
# result = client.run('test_strategy')
# print(f'Strategy result: {result.success}')
# "
```

**Performance Benchmarking:**
```bash
# Compare installation times
time poetry install --with dev,docs,api  # Baseline
time uv sync --all-extras                # New

# Compare test execution
time poetry run pytest tests/unit/
time uv run pytest tests/unit/

# Compare CI pipeline duration
# Monitor GitHub Actions runtime
```

### Step 15: Staging Environment Testing

**Deploy to staging:**
1. Use UV-based deployment
2. Run production-like workloads
3. Monitor performance metrics
4. Test all external integrations:
   - Google Drive sync
   - External APIs (UniProt, ChEMBL, etc.)
   - Database connections

**Monitoring checklist:**
- [ ] Memory usage comparable to Poetry
- [ ] Startup times acceptable
- [ ] All external integrations working
- [ ] No dependency conflicts
- [ ] Error rates within normal range

## Phase 6: Final Migration & Cleanup

### Step 16: Production Deployment

**Pre-deployment checklist:**
- [ ] All tests pass (1,297/1,297)
- [ ] Performance is equal or better than Poetry
- [ ] Documentation is updated and accurate
- [ ] CI pipeline is stable
- [ ] Rollback plan is tested and ready
- [ ] Team is trained on UV commands

**Deployment steps:**
1. Merge UV migration branch to main
2. Deploy to production with UV
3. Monitor for 24-48 hours
4. Validate all functionality
5. Remove Poetry backup files if stable

### Step 17: Cleanup and Finalization

**Remove Poetry artifacts:**
```bash
# Remove Poetry files
rm poetry.lock poetry.toml

# Remove Poetry from system (optional)
curl -sSL https://install.python-poetry.org | python3 - --uninstall

# Update .gitignore if needed
echo "uv.lock" >> .gitignore  # Typically tracked, but document decision
```

**Final documentation updates:**
- Remove all Poetry references
- Add UV installation instructions
- Update troubleshooting guides
- Document new development workflow

## Risk Mitigation & Rollback Procedures

### High-Risk Dependencies

**Torch & ML Stack:**
- Risk: CUDA dependencies, complex build requirements
- Mitigation: Test in isolated environment first
- Fallback: Use conda for ML dependencies if UV fails

**Private Repository (`phenome-arivale`):**
- Risk: Authentication, network access changes
- Mitigation: Verify git credentials work with UV
- Fallback: Local development without private repo

**FastAPI/Uvicorn:**
- Risk: Async functionality changes
- Mitigation: Comprehensive API testing
- Fallback: Pin exact versions during migration

### Rollback Triggers

**Immediate rollback if:**
- More than 5% of tests fail after migration
- CI pipeline becomes unstable (>3 consecutive failures)
- Performance degradation >20%
- Critical dependency incompatibilities discovered
- Production issues that can't be quickly resolved

**Rollback procedure:**
1. Execute rollback script
2. Restore Poetry environment
3. Verify all tests pass
4. Deploy Poetry version to production
5. Document issues for future migration attempt

### Success Metrics

**Technical Metrics:**
- All 1,297 tests pass with UV
- Test coverage remains ≥79.69%
- CI pipeline is ≥20% faster
- Dependency resolution is ≥10x faster
- Zero functional regressions

**Team Metrics:**
- Development workflow unchanged or improved
- Documentation is accurate and complete
- Team can operate effectively with UV
- New developers can onboard with UV

## Timeline & Resources

### Estimated Timeline

**Phase 0 (Pre-Migration)**: 2-4 days
- Package cleanup: 1-2 days (NEW)
- Dependency analysis: 1 day
- Pilot migration: 1 day

**Phase 1-3 (Core Migration)**: 3-5 days
- pyproject.toml conversion: 1 day
- Comprehensive testing: 2-4 days

**Phase 4-5 (Documentation & Validation)**: 2-3 days
- Documentation updates: 1-2 days
- End-to-end validation: 1 day

**Phase 6 (Deployment & Cleanup)**: 1-2 days
- Production deployment: 1 day
- Cleanup and finalization: 1 day

**Total Estimated Time**: 8-14 days (including package cleanup)

### Required Resources

**Technical Requirements:**
- Development environment with UV installed
- Access to private git repository
- CI/CD pipeline access
- Staging environment for testing

**Team Requirements:**
- Developer familiar with Poetry and UV
- Access to production deployment process
- Ability to rollback if issues occur

## Conclusion

This migration plan provides a comprehensive, risk-aware approach to converting BioMapper from Poetry to UV. The addition of a package cleanup phase significantly reduces migration complexity by potentially eliminating 54% of dependencies before the conversion begins.

**Key Success Factors:**
1. **Package cleanup before migration (NEW)** - Reduce complexity by 54%
2. Thorough dependency compatibility testing
3. Incremental migration approach
4. Comprehensive testing at each phase
5. Well-documented rollback procedures
6. Performance validation throughout process

**Cleanup Impact:**
- From 78 packages → potentially 36-40 packages
- Faster dependency resolution for both Poetry and UV
- Easier troubleshooting during migration
- Cleaner, more maintainable project

The migration will result in a more modern, faster development environment while maintaining all existing functionality and reliability standards.

---

**Document Version**: 1.0  
**Next Review**: After Phase 1 completion  
**Contact**: Development Team Lead