# Directory Structure Recommendations for Biomapper

## Terminology Clarification

When discussing "architecture" in software projects, it's important to distinguish between:

- **File/Directory Architecture** (or "Project Structure"): Physical organization of files and folders
- **System Architecture**: How components interact, data flows, dependencies  
- **Software Architecture**: Higher-level patterns (microservices, monolithic, event-driven)

This document focuses on **directory architecture/project structure** - how files are organized - which directly impacts developer experience and productivity.

## Current Directory Structure Pain Points

### 1. Strategies are Orphaned from Their Actions

```
configs/strategies/experimental/*.yaml    ← Strategies here
    ↕ (4+ directories apart!)
biomapper/core/strategy_actions/         ← Actions here
```

**Problem**: This separation makes it hard to understand what actions a strategy needs or what strategies use an action. Developers must navigate between distant directories to understand a single feature.

### 2. Three Separate Packages Feel Unnecessary

```
biomapper/          ← Core logic
biomapper-api/      ← Thin FastAPI wrapper
biomapper_client/   ← Thin client wrapper
```

**Problem**: The API and client are so thin they could just be modules within biomapper. This creates:
- Complex import paths
- Separate dependency management
- Unclear boundaries between packages

### 3. Inconsistent Depth and Organization

```
biomapper/core/strategy_actions/entities/proteins/identification/
                                ↑        ↑         ↑
                            (too deep for what it does)

vs.

configs/strategies/experimental/
        ↑          ↑
    (too shallow - no organization by entity type)
```

**Problem**: Some paths are 6+ levels deep while others are too shallow, making navigation inconsistent and confusing.

### 4. Test Data Scattered

```
/data/test_data/
/data/isb_osp/
/data/function_health/
/tmp/ (during testing)
```

**Problem**: No clear convention for where test data lives, leading to duplication and confusion.

## Proposed Improvements (Without Breaking Changes)

### Option 1: Simple Reorganization (Minimal Risk)

```
biomapper/
├── strategies/                    # Move strategies INTO biomapper
│   ├── proteins/
│   │   ├── arivale_to_kg2c.yaml
│   │   ├── ukbb_to_kg2c.yaml
│   │   └── actions/              # Co-locate related actions
│   │       ├── extract_uniprot.py
│   │       └── normalize_accessions.py
│   ├── metabolites/
│   │   ├── nightingale_nmr.yaml
│   │   ├── cts_bridge.yaml
│   │   └── actions/
│   │       ├── nmr_match.py
│   │       └── hmdb_normalize.py
│   └── chemistry/
│       ├── fuzzy_match.yaml
│       ├── vendor_harmonization.yaml
│       └── actions/
│           ├── loinc_extract.py
│           └── fuzzy_test_match.py
├── api/                          # Merge biomapper-api here
│   ├── main.py
│   ├── routes/
│   └── models/
├── client/                       # Merge biomapper_client here
│   └── client.py
├── core/                         # Shared core functionality
│   ├── registry.py
│   ├── executor.py
│   └── utils/
└── test_data/                    # Centralize test data
    ├── proteins/
    │   └── test_proteins.csv
    ├── metabolites/
    │   └── test_metabolites.csv
    └── chemistry/
        └── test_chemistry.csv
```

### Option 2: Domain-Driven Structure (Medium Risk)

```
biomapper/
├── domains/                      # Organize by domain
│   ├── proteins/
│   │   ├── __init__.py
│   │   ├── strategies/          # Strategies for this domain
│   │   │   ├── arivale_to_kg2c.yaml
│   │   │   └── ukbb_to_kg2c.yaml
│   │   ├── actions/             # Actions for this domain
│   │   │   ├── extract_uniprot.py
│   │   │   └── normalize_accessions.py
│   │   ├── models/              # Domain-specific models
│   │   │   └── protein.py
│   │   └── tests/               # Domain-specific tests
│   │       └── test_protein_actions.py
│   ├── metabolites/
│   │   └── (similar structure)
│   └── chemistry/
│       └── (similar structure)
├── infrastructure/              # Cross-cutting concerns
│   ├── api/                    # API layer
│   ├── client/                 # Client library
│   ├── database/               # Database access
│   └── cache/                  # Caching layer
└── shared/                      # Shared utilities
    ├── registry.py
    └── executor.py
```

## Benefits of Reorganization

### 1. Strategies with Their Actions
- **Current**: Need to navigate 4+ directories to find related code
- **Proposed**: Actions and strategies in same domain folder
- **Benefit**: Easy to see relationships and dependencies

### 2. Single Package
- **Current**: Three separate packages with complex imports
- **Proposed**: Single package with clear modules
- **Benefit**: Simpler imports: `from biomapper.strategies.proteins import ...`

### 3. Organized by Domain
- **Current**: Mixed organization (by type in some places, flat in others)
- **Proposed**: Consistent organization by entity type/domain
- **Benefit**: Clear where to add new entity types

### 4. Flatter Hierarchy
- **Current**: Some paths 6+ levels deep
- **Proposed**: Maximum 4 levels for most files
- **Benefit**: Easier navigation and cleaner imports

## Why This Matters

The current structure creates real friction:

### 1. Finding Related Code
**Scenario**: "I need to modify a protein strategy... where are the protein actions again?"
- **Current**: Navigate from `/configs/strategies/experimental/` to `/biomapper/core/strategy_actions/entities/proteins/`
- **Proposed**: Everything in `/biomapper/domains/proteins/`

### 2. Adding Features
**Scenario**: "I want to add a new entity type (e.g., genomics)..."
- **Current**: Create directories in 3+ different places
- **Proposed**: Create one domain folder with standard subfolders

### 3. Understanding Flow
**Scenario**: "This strategy uses CUSTOM_TRANSFORM... where is that implemented?"
- **Current**: Hunt through deep directory structure
- **Proposed**: Look in same domain or shared utilities

### 4. Testing
**Scenario**: "I need test data for proteins..."
- **Current**: Check data/, test_data/, isb_osp/, or create in /tmp/
- **Proposed**: Always in `/biomapper/test_data/proteins/`

## Quick Wins (No Code Changes Required)

Even without refactoring, you could improve navigation:

### 1. Add a STRUCTURE.md File
Create a map of where everything lives:
```markdown
# Biomapper Structure Guide

## Finding Things
- Strategies: configs/strategies/experimental/
- Actions: biomapper/core/strategy_actions/
- API routes: biomapper-api/app/api/
- Test data: data/test_data/

## Adding New Features
- New action: biomapper/core/strategy_actions/entities/{type}/
- New strategy: configs/strategies/experimental/{type}_*.yaml
- New test: tests/unit/core/strategy_actions/
```

### 2. Create Convenience Symlinks
```bash
# Make actions accessible from strategies directory
ln -s ../../../biomapper/core/strategy_actions configs/strategies/actions

# Make strategies accessible from biomapper
ln -s ../../configs/strategies biomapper/strategies_configs
```

### 3. Add Navigation Comments
In key files, add comments pointing to related components:
```python
# biomapper/core/strategy_actions/registry.py
"""
Action Registry

Related files:
- Strategies using these actions: configs/strategies/experimental/
- Action implementations: biomapper/core/strategy_actions/entities/
- API endpoints: biomapper-api/app/api/v2/strategies.py
"""
```

## The Fundamental Question

Should strategies be treated as:

### Option A: Configuration (Current Approach)
- Live in `configs/` directory
- Treated as external YAML files
- Versioned with the repo but conceptually separate

### Option B: Code (Recommended)
- Live in `biomapper/` package
- Treated as part of the application
- Co-located with their implementations

**Recommendation**: Strategies are code - they define behavior, have versions, need testing, and are tightly coupled to action implementations. Treating them as external configs creates unnecessary distance from their implementations.

## Migration Path

If you decide to reorganize:

### Phase 1: Plan and Communicate (Week 1)
1. Create detailed migration plan
2. Get team buy-in
3. Set up new structure in parallel
4. Create migration scripts

### Phase 2: Move Core Components (Week 2)
1. Move strategies to new location
2. Update strategy loader to check both locations
3. Move actions to co-located structure
4. Update imports incrementally

### Phase 3: Consolidate Packages (Week 3)
1. Merge biomapper-api into biomapper/api
2. Merge biomapper_client into biomapper/client
3. Update deployment configurations
4. Update documentation

### Phase 4: Clean Up (Week 4)
1. Remove old structure
2. Update all documentation
3. Update CI/CD pipelines
4. Team training on new structure

## Metrics for Success

| Metric | Current | Target | 
|--------|---------|--------|
| Average directory depth | 6+ levels | ≤4 levels |
| Directories to visit for one feature | 3-4 | 1-2 |
| Import statement length | 50+ chars | <30 chars |
| Time to find related code | Minutes | Seconds |
| Packages to maintain | 3 | 1 |

## Conclusion

The current directory structure works but creates unnecessary friction. The proposed reorganization would:

1. **Reduce cognitive load** by co-locating related code
2. **Simplify navigation** with consistent, shallow structure  
3. **Improve maintainability** with clear domain boundaries
4. **Accelerate development** by making code easier to find

The sweet spot would be strategies and actions co-located by domain, with a single package structure that makes the codebase much more navigable and maintainable.