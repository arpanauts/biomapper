# Biomapper Architecture Investigation Prompt

## Objective
Perform a comprehensive code trace to map the actual current architecture of the Biomapper project, identifying what components are actively used versus legacy/dead code that can be removed.

## Investigation Tasks

### 1. API Entry Points Analysis
Trace all FastAPI endpoints to understand the actual execution flow:

```bash
# Find all API routes
grep -r "@router\." biomapper-api/app/api/routes/
grep -r "@app\." biomapper-api/app/main.py

# For each endpoint, trace:
# - What service methods it calls
# - What core library components those services use
# - What database models/tables are accessed
# - What YAML strategies are invoked
```

Key questions:
- Which endpoints are actually defined and accessible?
- What services do they use (MapperService, PersistenceService, etc.)?
- Do they use MinimalStrategyService or legacy components?
- What's the flow from endpoint → service → core library?

### 2. Strategy Action Registry Analysis
Map which actions are registered and actually used:

```bash
# Find all @register_action decorators
grep -r "@register_action" biomapper/core/strategy_actions/

# Find all action type references in YAML strategies
grep -r "type:" configs/strategies/ | grep -v "#"

# Cross-reference to find:
# - Registered but never used actions
# - Actions referenced in YAML but not registered
# - Actions imported but never registered
```

Key questions:
- Which actions are registered in ACTION_REGISTRY?
- Which actions are referenced in active YAML strategies?
- Are there orphaned action implementations?
- Which actions have tests vs those that don't?

### 3. Client Usage Pattern Analysis
Understand how the system is actually used:

```bash
# Analyze biomapper_client usage
grep -r "BiomapperClient" scripts/
grep -r "execute_strategy" scripts/
grep -r "from biomapper_client" scripts/

# Find direct biomapper core imports (should be minimal/none in scripts)
grep -r "from biomapper\." scripts/ --exclude-dir=__pycache__

# Analyze CLI commands
grep -r "@click\." biomapper_client/
grep -r "@app\.command" biomapper_client/
```

Key questions:
- Which client methods are actually used?
- Are scripts properly using BiomapperClient or importing core directly?
- Which CLI commands exist and are they documented?
- What strategies do the example scripts execute?

### 4. Database and Persistence Layer Analysis
Map the actual persistence architecture:

```bash
# Find SQLAlchemy models
grep -r "class.*Base):" biomapper-api/
grep -r "declarative_base" biomapper-api/

# Find Alembic migrations
ls -la biomapper-api/alembic/versions/

# Find actual database operations
grep -r "session\." biomapper-api/
grep -r "\.query(" biomapper-api/
```

Key questions:
- What tables actually exist in biomapper.db?
- Which models are actively used vs orphaned?
- Are there unused migrations or models?
- Is job persistence/checkpointing actually working?

### 5. Import Dependency Analysis
Create a dependency graph to identify isolated components:

```bash
# Find all imports in core library
find biomapper/ -name "*.py" -exec grep -l "from biomapper" {} \; | while read f; do
    echo "=== $f ==="
    grep "from biomapper" "$f" | grep -v "^#"
done

# Find external dependencies actually used
grep -r "import " biomapper/ | grep -v "from biomapper" | grep -v "^#" | sort -u

# Find circular dependencies
# Look for files that import each other
```

Key questions:
- Which modules have no incoming imports (dead code candidates)?
- Are there circular dependencies?
- Which external libraries are actually used vs just installed?
- Can we identify self-contained modules that can be extracted/removed?

### 6. Legacy vs Active Components Identification

Components to investigate:
```
POTENTIALLY LEGACY:
- biomapper/core/engine_components/* (except CheckpointManager, ProgressReporter)
- biomapper/core/base_*.py files
- biomapper/mapping/clients/* (check which are actually used)
- *_old.py files
- biomapper/core/services/* (check if replaced by MinimalStrategyService)

CONFIRMED ACTIVE (per CLAUDE.md):
- MinimalStrategyService
- ACTION_REGISTRY and @register_action pattern
- biomapper-api/app/*
- biomapper_client/*
- configs/strategies/*.yaml
```

### 7. Test Coverage Analysis
Understand what's actually tested:

```bash
# Find test files
find tests/ -name "test_*.py" | wc -l

# Map test files to implementation files
# For each test file, identify what it's testing

# Find untested modules
# Compare biomapper/**/*.py with tests/**/*.py

# Run coverage report
poetry run pytest --cov=biomapper --cov=biomapper-api --cov=biomapper_client --cov-report=term-missing
```

### 8. Configuration and Environment Analysis

```bash
# Find all environment variable usage
grep -r "os\.environ" biomapper/ biomapper-api/ biomapper_client/
grep -r "getenv" biomapper/ biomapper-api/ biomapper_client/

# Find all config files
find . -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.toml" | grep -v __pycache__

# Check what's in .env.example vs actual usage
```

## Output Report Structure

### Executive Summary
- Current architecture diagram (text-based)
- Key findings about active vs legacy code
- Recommended removal candidates with risk assessment

### Detailed Findings

#### Active Components
List of components confirmed in use with evidence:
- File path
- How it's used
- Dependencies
- Test coverage

#### Dead Code Candidates
Components that appear unused:
- File path
- Last meaningful commit
- Risk of removal (low/medium/high)
- Dependencies that would break

#### Ambiguous Components
Components needing further investigation:
- File path
- Why it's ambiguous
- Questions to answer

### Dependency Graph
```
API Endpoints
    ↓
Services (MapperService, PersistenceService)
    ↓
MinimalStrategyService
    ↓
ACTION_REGISTRY ← Strategy Actions (self-registered)
    ↓
External Clients (CTS, UniProt, etc.)
```

### Recommendations
1. Safe to remove immediately (no dependencies)
2. Requires refactoring before removal
3. Keep but refactor/modernize
4. Core components (do not touch)

## Execution Instructions

1. Run this investigation systematically, section by section
2. Document findings in a new file: `/home/ubuntu/biomapper/configs/prompts/investigation_results.md`
3. Create a visualization of the actual architecture
4. Generate a prioritized list of cleanup tasks
5. Estimate effort and risk for each cleanup task

## Safety Checks
Before recommending any removal:
- Verify no imports from other modules
- Check no YAML strategies reference it
- Confirm no tests depend on it
- Search for string references (dynamic imports)
- Check if mentioned in documentation

## Notes
- Focus on evidence-based findings (grep results, import traces)
- Distinguish between "unused" and "legacy but still imported"
- Consider that some code might be used dynamically or via reflection
- Check for imports in test files too - they might be the only users