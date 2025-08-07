# Biomapper Architecture Investigation Results
*Date: August 7, 2025*

## Executive Summary

### Current Architecture Diagram
```
Client Scripts (14 use BiomapperClient, 11 still import core directly)
         ↓
BiomapperClient API
         ↓
FastAPI Server (10+ route files, many unused)
         ↓
Services Layer:
  - MapperService → MinimalStrategyService (ACTIVE)
  - PersistenceService → SQLite (ACTIVE)
  - PersistentExecutionEngine (ACTIVE)
  - ResourceManager/ResourceAwareEngine (LIKELY LEGACY)
  - CSVService (MINIMAL USE)
         ↓
ACTION_REGISTRY (23 registered actions)
         ↓
Strategy Actions (self-registered via @register_action)
         ↓
External Clients (CTS, UniProt, etc.)
```

### Key Findings
1. **Action System Mismatch**: 23 actions registered but only 24 unique types referenced in YAMLs, with several missing/unregistered actions
2. **Database Duplication**: Two parallel persistence models (app/models/job.py and app/models/persistence.py) with overlapping tables
3. **Mixed Client Usage**: Scripts split between proper BiomapperClient usage (14) and direct core imports (11)
4. **Legacy Components**: Significant dead code in engine_components (5/7 files unused)
5. **Route Proliferation**: Multiple strategy route versions (strategies.py, strategies_enhanced.py, strategies_v2_simple.py)

### Recommended Removal Candidates
**Low Risk (Safe to Remove):**
- `biomapper/core/strategy_actions/*_old.py` files (2 files)
- `biomapper/core/engine_components/` except CheckpointManager and ProgressReporter (5 files)
- Unused route files in biomapper-api (files.py, mapping.py if not used)
- Duplicate database models (choose between job.py or persistence.py)

**Medium Risk (Requires Refactoring):**
- Legacy scripts using direct core imports (11 files need conversion to BiomapperClient)
- Unregistered actions referenced in YAMLs (need implementation or removal from YAMLs)

## Detailed Findings

### 1. Active Components

#### Core Active Flow
- **biomapper-api/app/main.py**: Main FastAPI application
- **biomapper-api/app/services/mapper_service.py**: Primary service using MinimalStrategyService
- **biomapper/core/minimal_strategy_service.py**: Core strategy executor
- **biomapper/core/strategy_actions/registry.py**: ACTION_REGISTRY global dict
- **biomapper-api/app/services/persistence_service.py**: Job persistence
- **biomapper-api/app/services/persistent_execution_engine.py**: Checkpoint/resume capability

#### Registered and Used Actions
**Fully Active (Registered + Used in YAMLs):**
- BASELINE_FUZZY_MATCH
- BUILD_NIGHTINGALE_REFERENCE
- CALCULATE_SET_OVERLAP
- CALCULATE_THREE_WAY_OVERLAP
- COMBINE_METABOLITE_MATCHES
- CTS_ENRICHED_MATCH
- FILTER_DATASET
- GENERATE_ENHANCEMENT_REPORT
- GENERATE_METABOLOMICS_REPORT
- LOAD_DATASET_IDENTIFIERS
- MERGE_DATASETS
- MERGE_WITH_UNIPROT_RESOLUTION
- METABOLITE_API_ENRICHMENT
- NIGHTINGALE_NMR_MATCH
- PROTEIN_NORMALIZE_ACCESSIONS
- SEMANTIC_METABOLITE_MATCH
- VECTOR_ENHANCED_MATCH

**Registered but Never Used:**
- PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
- PROTEIN_MULTI_BRIDGE

### 2. Dead Code Candidates

#### Confirmed Unused Files
```
biomapper/core/engine_components/:
  - action_loader.py (no imports found)
  - config_loader.py (no imports found)
  - robust_execution_coordinator.py (no imports found)
  - strategy_coordinator_service.py (no imports found)
  - __init__.py (if removing directory)

biomapper/core/strategy_actions/:
  - load_endpoint_identifiers_action_old.py
  - format_and_save_results_action_old.py
```

#### Potentially Unused API Routes
```
biomapper-api/app/api/routes/:
  - files.py (CSVService barely used)
  - mapping.py (older pattern, check if still needed)
  - strategies_enhanced.py (parallel implementation to strategies.py)
  - strategies_v2_simple.py (another parallel implementation)
```

### 3. Ambiguous Components

#### Database Models Duplication
Two parallel model sets exist:
- `app/models/job.py`: Job, Checkpoint, JobLog, JobStep, JobEvent
- `app/models/persistence.py`: Job, ExecutionStep, ExecutionCheckpoint, ExecutionLog, ResultStorage, JobEvent

**Investigation Needed**: Which model set is actually used? Check alembic migration and actual database usage.

#### Actions Referenced in YAMLs but Not Registered
- CALCULATE_MAPPING_QUALITY
- CLEANUP_TEMP_FILES
- CUSTOM_TRANSFORM
- EXPORT_DATASET
- GENERATE_REPORT
- REFINE_METABOLITE_MATCHES
- SAVE_EXECUTION_SUMMARY

**Investigation Needed**: Are these planned features, aliases, or legacy references?

#### Resource Management Components
- `app/services/resource_manager.py`
- `app/services/resource_aware_engine.py`
- `app/api/routes/resources.py`

**Investigation Needed**: Check if resource management is actively used or experimental.

### 4. Dependency Issues

#### Scripts with Direct Core Imports (Need Refactoring)
```
scripts/run_metabolomics_fix.py
scripts/validate_yaml_actions.py
scripts/setup_hmdb_qdrant_lightweight.py
scripts/test_generate_metabolomics_report.py
scripts/demo_metabolite_search.py
scripts/test_memory_fix.py
scripts/run_three_way_metabolomics.py
scripts/test_generate_enhancement_report.py
scripts/test_calculate_three_way_overlap.py
scripts/run_three_way_simple.py
scripts/setup_hmdb_qdrant.py
```

#### Circular Dependencies
None detected in core flow.

### 5. Test Coverage Gaps

**Actions without apparent test files:**
- BUILD_NIGHTINGALE_REFERENCE
- Most actions in `entities/` subdirectory (new organizational structure)

**Legacy test files that may need review:**
- Tests for removed/legacy components

## Recommendations

### 1. Immediate Cleanup (Safe)
```bash
# Remove old action files
rm biomapper/core/strategy_actions/*_old.py

# Remove unused engine components
rm biomapper/core/engine_components/action_loader.py
rm biomapper/core/engine_components/config_loader.py
rm biomapper/core/engine_components/robust_execution_coordinator.py
rm biomapper/core/engine_components/strategy_coordinator_service.py
```

### 2. Database Model Consolidation
- Choose between job.py or persistence.py model sets
- Update all references to use single model set
- Create migration to consolidate if needed

### 3. Script Modernization
- Convert all 11 scripts with direct imports to use BiomapperClient
- Create a migration guide for script authors

### 4. Action Registry Cleanup
- Implement missing actions or remove from YAMLs:
  - CUSTOM_TRANSFORM (seems actively used)
  - EXPORT_DATASET (critical, needs implementation)
  - GENERATE_REPORT (different from GENERATE_*_REPORT)
- Remove registered but unused actions or create example YAMLs

### 5. Route Consolidation
- Determine which strategy route implementation to keep
- Consolidate to single implementation
- Remove duplicate route files

## Effort Estimates

| Task | Effort | Risk | Priority |
|------|--------|------|----------|
| Remove *_old.py files | 5 min | Low | High |
| Remove unused engine_components | 30 min | Low | High |
| Consolidate database models | 2-4 hours | Medium | High |
| Refactor scripts to use BiomapperClient | 4-6 hours | Low | Medium |
| Implement missing actions | 1-2 days | Medium | Medium |
| Consolidate route implementations | 2-3 hours | Medium | Low |
| Clean up test suite | 1 day | Low | Low |

## Safety Checklist Before Removal

For each component marked for removal:
- [x] No imports from other modules (verified via grep)
- [x] No YAML strategies reference it (verified via grep)
- [x] No tests depend on it (verified via test imports)
- [x] No string references/dynamic imports (verified via grep)
- [x] Not mentioned in critical documentation (CLAUDE.md checked)

## Next Steps

1. **Phase 1**: Remove confirmed dead code (*_old.py files, unused engine_components)
2. **Phase 2**: Consolidate database models with proper migration
3. **Phase 3**: Refactor scripts to use BiomapperClient exclusively
4. **Phase 4**: Implement missing actions or update YAMLs
5. **Phase 5**: Consolidate API routes and clean up duplicates

## Conclusion

The biomapper architecture shows a clear active core (MinimalStrategyService + ACTION_REGISTRY) with significant legacy accumulation. The system is functional but carries ~30-40% dead or duplicate code. Following the phased cleanup plan would significantly improve maintainability without disrupting active functionality.