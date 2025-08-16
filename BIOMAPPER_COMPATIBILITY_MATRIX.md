# Biomapper Restructure Compatibility Matrix

## Executive Summary

This document provides a detailed compatibility matrix and migration checklist for restructuring the biomapper project with **zero breaking changes**. The analysis identified **154 high-risk files** and **91 YAML-referenced action types** that require careful migration.

## 1. COMPATIBILITY MATRIX

### 1.1 What Changes vs. What Stays the Same

| Component | Current State | After Restructure | Breaking Change Risk |
|-----------|--------------|-------------------|---------------------|
| **Import Paths** | `from biomapper.core.strategy_actions import *` | Same (via compatibility shims) | **None** |
| **Action Names** | 46 registered actions | Same action names | **None** |
| **YAML Strategies** | 91 action types | Same action types | **None** |
| **API Endpoints** | `/api/v2/strategies/*` | Same endpoints | **None** |
| **CLI Commands** | `biomapper health`, etc. | Same commands | **None** |
| **Package Structure** | 3 separate packages | 3 packages (renamed internally) | **Low** |
| **Registry Location** | `biomapper/core/strategy_actions/registry.py` | Same (forwarding) | **None** |
| **Service Layer** | `MinimalStrategyService` | Same interface | **None** |
| **Client Library** | `BiomapperClient` | Same public API | **None** |
| **Test Imports** | 205 biomapper imports | Same imports work | **None** |

### 1.2 Critical Dependencies That Must Be Preserved

| Dependency | Used By | Files Affected | Migration Strategy |
|------------|---------|----------------|-------------------|
| `ACTION_REGISTRY` | All services | 71 files | Keep import path via shim |
| `@register_action` | All actions | 46 files | Forward decorator |
| `MinimalStrategyService` | API, scripts | 12 files | Maintain interface |
| `BiomapperClient` | External users | Unknown | Version carefully |
| `TypedStrategyAction` | Modern actions | 38 files | Keep base class |

## 2. MIGRATION CHECKLIST

### Phase 0: Pre-Migration Setup (Day 1)
- [ ] Create git branch: `restructure-zero-downtime`
- [ ] Tag current state: `git tag pre-restructure-v1.0`
- [ ] Run full test suite and save results
- [ ] Document current action count: 46
- [ ] Document current YAML strategy count: 91
- [ ] Create rollback script

### Phase 1: Compatibility Layer (Days 2-3)

#### Step 1.1: Create New Package Structure
```bash
mkdir -p biomapper_core/actions/{base,entities,io,reports,utils}
mkdir -p biomapper_core/standards
mkdir -p biomapper_core/services
```

#### Step 1.2: Create Import Shims
- [ ] Create `biomapper/core/strategy_actions/__init__.py` shim:
```python
# Backward compatibility shim
from biomapper_core.actions.registry import ACTION_REGISTRY, register_action
from biomapper_core.actions.base import TypedStrategyAction

__all__ = ["ACTION_REGISTRY", "register_action", "TypedStrategyAction"]
```

#### Step 1.3: Move Core Files (Keep Originals as Shims)
- [ ] `registry.py` → `biomapper_core/actions/registry.py`
- [ ] `typed_base.py` → `biomapper_core/actions/base.py`
- [ ] `minimal_strategy_service.py` → `biomapper_core/services/strategy_service.py`

### Phase 2: Action Migration (Days 4-7)

#### Step 2.1: Migrate High-Usage Actions First
Priority order based on YAML usage:
1. [ ] `LOAD_DATASET_IDENTIFIERS` (59 YAML files)
2. [ ] `EXPORT_DATASET` (48 YAML files)
3. [ ] `CALCULATE_SET_OVERLAP` (42 YAML files)
4. [ ] `FILTER_DATASET` (31 YAML files)
5. [ ] `MERGE_DATASETS` (24 YAML files)

#### Step 2.2: Migrate Entity-Specific Actions
- [ ] Move `proteins/*` → `biomapper_core/actions/entities/proteins/`
- [ ] Move `metabolites/*` → `biomapper_core/actions/entities/metabolites/`
- [ ] Move `chemistry/*` → `biomapper_core/actions/entities/chemistry/`

#### Step 2.3: Update Each Action File
For each action file:
```python
# Old location becomes a shim
# biomapper/core/strategy_actions/load_dataset_identifiers.py
from biomapper_core.actions.io.load_dataset_identifiers import *
```

### Phase 3: Service Layer Updates (Days 8-9)

#### Step 3.1: Update API Dependencies
- [ ] Update `biomapper-api/app/services/mapper_service.py`:
```python
# Add fallback imports
try:
    from biomapper_core.services import MinimalStrategyService
except ImportError:
    from biomapper.core.minimal_strategy_service import MinimalStrategyService
```

#### Step 3.2: Update Background Job Executor
- [ ] Update `biomapper-api/app/services/background_executor.py`
- [ ] Ensure job serialization remains compatible

### Phase 4: Package Renaming (Days 10-11)

#### Step 4.1: Rename Directories (Keep Symlinks)
```bash
mv biomapper-api biomapper/api
ln -s biomapper/api biomapper-api  # Temporary symlink

mv biomapper_client biomapper/client  
ln -s biomapper/client biomapper_client  # Temporary symlink
```

#### Step 4.2: Update pyproject.toml Files
- [ ] Update main `pyproject.toml`
- [ ] Update `biomapper/api/pyproject.toml`
- [ ] Update `biomapper/client/pyproject.toml`

### Phase 5: Testing and Validation (Days 12-13)

#### Step 5.1: Run Progressive Test Suite
```bash
# Level 1: Basic imports
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; assert len(ACTION_REGISTRY) == 46"

# Level 2: Strategy loading
poetry run pytest tests/integration/

# Level 3: Full execution
python scripts/run_three_level_tests.py all
```

#### Step 5.2: Validate YAML Strategies
```bash
# Test each critical strategy
for strategy in production/*.yaml; do
    poetry run biomapper run --strategy $strategy --dry-run
done
```

### Phase 6: Cleanup (Day 14)

#### Step 6.1: Remove Deprecated Code
- [ ] Remove duplicate implementations identified
- [ ] Archive old experimental strategies
- [ ] Clean up scattered test files

#### Step 6.2: Update Documentation
- [ ] Update CLAUDE.md with new structure
- [ ] Update README.md
- [ ] Create migration guide for external users

## 3. RISK ASSESSMENT

### 3.1 Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Registry path breaks** | Low (5%) | Critical | Compatibility shims, extensive testing |
| **YAML strategies fail** | Low (10%) | High | No changes to action names |
| **API downtime** | Very Low (2%) | High | Rolling deployment, health checks |
| **Test suite failures** | Medium (30%) | Medium | Fix imports progressively |
| **Client library breaks** | Low (5%) | High | Version carefully, test externally |
| **Performance degradation** | Low (10%) | Medium | Profile before/after |

### 3.2 Highest Risk Files

These files require special attention during migration:

1. **Core Registry Files**
   - `biomapper/core/strategy_actions/registry.py` (71 dependencies)
   - `biomapper/core/minimal_strategy_service.py` (12 dependencies)

2. **High-Usage Actions**
   - `load_dataset_identifiers.py` (59 YAML references)
   - `export_dataset.py` (48 YAML references)
   - `calculate_set_overlap.py` (42 YAML references)

3. **API Integration Points**
   - `biomapper-api/app/services/mapper_service.py`
   - `biomapper-api/app/main.py`

## 4. TESTING STRATEGY

### 4.1 Pre-Migration Baseline
```bash
# Capture current metrics
python << 'EOF'
from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
print(f"Actions registered: {len(ACTION_REGISTRY)}")
print("Action names:", sorted(ACTION_REGISTRY.keys()))
EOF

# Run full test suite
poetry run pytest --json-report --json-report-file=pre-migration-tests.json
```

### 4.2 During Migration Validation
After each phase, run:
```bash
# Quick validation script
./scripts/validate_migration.sh

# Contents:
#!/bin/bash
echo "Checking action registry..."
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; assert len(ACTION_REGISTRY) == 46"

echo "Checking API health..."
curl -s http://localhost:8000/api/health/status | grep "healthy"

echo "Checking critical strategies..."
poetry run biomapper run --strategy test_simple --dry-run
```

### 4.3 Post-Migration Validation
```bash
# Complete test suite
poetry run pytest

# Performance comparison
python scripts/benchmark_strategies.py

# External integration tests
python scripts/test_external_clients.py
```

## 5. ROLLBACK PROCEDURES

### 5.1 Complete Rollback (Emergency)
```bash
# Immediate rollback to pre-migration state
git checkout pre-restructure-v1.0
poetry install
cd biomapper-api && poetry install
systemctl restart biomapper-api
```

### 5.2 Partial Rollback (Specific Component)
```bash
# Rollback just the registry
git checkout HEAD~1 -- biomapper/core/strategy_actions/registry.py

# Rollback just the API
cd biomapper-api
git checkout HEAD~1 -- .
poetry install
```

### 5.3 Forward Recovery (Fix Issues)
```bash
# If specific action fails, restore its original location
cp backup/strategy_actions/failing_action.py biomapper/core/strategy_actions/

# Re-run registration
python -c "import biomapper.core.strategy_actions.failing_action"
```

## 6. SUCCESS METRICS

### 6.1 Quantitative Metrics
- [ ] Action registry maintains 46 registered actions
- [ ] All 91 YAML action types remain functional
- [ ] 100% test suite pass rate maintained
- [ ] API response times within 5% of baseline
- [ ] Zero production errors during migration

### 6.2 Qualitative Metrics
- [ ] No breaking changes reported by users
- [ ] Documentation updated and accurate
- [ ] Team can navigate new structure easily
- [ ] External integrations continue working
- [ ] Performance improvements observed

## 7. TIMELINE SUMMARY

| Day | Phase | Activities | Validation |
|-----|-------|------------|------------|
| 1 | Setup | Create branch, baseline metrics | Run full tests |
| 2-3 | Compatibility | Create shims, new structure | Import tests |
| 4-7 | Actions | Migrate action files | YAML validation |
| 8-9 | Services | Update service layer | API health checks |
| 10-11 | Packages | Rename and restructure | Integration tests |
| 12-13 | Testing | Full validation suite | Performance tests |
| 14 | Cleanup | Remove deprecated code | Final validation |

## 8. COMMAND REFERENCE

### Quick Validation Commands
```bash
# Check action count
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; print(len(ACTION_REGISTRY))"

# Test strategy loading
poetry run biomapper strategies list

# Validate specific YAML
poetry run biomapper validate --strategy configs/strategies/test_simple.yaml

# API health check
curl http://localhost:8000/api/health/status

# Run minimal test
poetry run pytest tests/unit/core/test_registry.py -xvs
```

This compatibility matrix ensures a safe, zero-downtime migration of the biomapper project while maintaining all existing functionality and external interfaces.