# Biomapper Cleanup Tracker
*Last Updated: August 7, 2025*

## Overall Progress: 0% Complete

### Phase 1: Safe Immediate Removals ✅
- [✅] Remove `load_endpoint_identifiers_action_old.py`
- [✅] Remove `format_and_save_results_action_old.py`
- [✅] Remove unused engine_components files:
  - [✅] `action_loader.py`
  - [✅] `config_loader.py`
  - [✅] `robust_execution_coordinator.py`
  - [✅] `strategy_coordinator_service.py`
- [✅] Update engine_components `__init__.py`
- [✅] Remove duplicate API route files (`strategies.py`, `strategies_enhanced.py`)

### Phase 2: Database Model Consolidation ⏳
- [ ] Analyze job.py vs persistence.py usage
- [ ] Choose primary model
- [ ] Migrate features to single model
- [ ] Update all imports
- [ ] Create Alembic migration if needed
- [ ] Test persistence functionality

### Phase 3: Fix Missing Actions ⏳
**Critical:**
- [ ] Implement or remove EXPORT_DATASET (used in 6 strategies)
- [ ] Implement or remove CUSTOM_TRANSFORM (used in 1 strategy)
- [ ] Implement or remove EXECUTE_MAPPING_PATH (used in multiple strategies)

**Lower Priority:**
- [ ] Handle AGGREGATE_RESULTS
- [ ] Handle CONDITIONAL_EXECUTE
- [ ] Handle VALIDATE_IDENTIFIERS
- [ ] Handle PARAMETER_SWEEP

### Phase 4: Script Modernization ⏳
Convert these 11 scripts from direct imports to BiomapperClient:
- [ ] `scripts/analysis/dataset_comparison.py`
- [ ] `scripts/analysis/identifier_analysis.py`
- [ ] `scripts/converters/arivale_name_mapper.py`
- [ ] `scripts/data_processing/filter_mapping_results.py`
- [ ] `scripts/data_processing/generate_test_data.py`
- [ ] `scripts/entity_analysis/entity_set_analyzer.py`
- [ ] `scripts/main_pipelines/run_metabolomics_workflow.py`
- [ ] `scripts/mapping_execution/identifier_mapper.py`
- [ ] `scripts/protein_analysis/protein_metadata_comparison.py`
- [ ] `scripts/testing/test_iterative_mapping.py`
- [ ] `scripts/testing/test_minimal_strategy.py`

### Phase 5: Remove Unused Actions ⏳
- [ ] Remove PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
- [ ] Remove PROTEIN_MULTI_BRIDGE
- [ ] Clean up empty action directories

### Phase 6: Legacy Component Analysis ⏳
- [ ] Investigate base_*.py files usage
- [ ] Determine which mapping clients are active
- [ ] Document findings
- [ ] Create removal plan for unused components

### Phase 7: Test Coverage ⏳
- [ ] Identify untested active components
- [ ] Write tests for critical paths
- [ ] Remove tests for deleted code
- [ ] Achieve 80% coverage minimum

## Validation Results

### Pre-Cleanup Baseline
```
Date: August 7, 2025 (Start of cleanup)
Total Lines of Code: 58,080 lines
Number of Python Files: 270 files
Linting Errors: 370 errors (320 remaining after auto-fix)
System Status: Some pre-existing linting issues but codebase functional
```

### Post-Phase Results
*To be filled in after each phase*

#### Phase 1 Completion
```
Date: August 7, 2025
Lines Removed: 1,933 lines (58,080 → 56,147)
Files Removed: 8 files (270 → 262)
Files Removed:
  - load_endpoint_identifiers_action_old.py
  - format_and_save_results_action_old.py
  - action_loader.py
  - config_loader.py
  - robust_execution_coordinator.py
  - strategy_coordinator_service.py
  - strategies.py (36 lines)
  - strategies_enhanced.py (822 lines)
Core Functionality: ✅ Preserved
Issues Found: Pre-existing CLI module import issues unrelated to cleanup
```

#### Phase 2 Completion
```
Date: 
Lines Removed: 
Tests Passing: ✅/❌
Model Consolidated: 
Issues Found: 
```

## Issues & Blockers

### Open Issues
*List any problems discovered during cleanup*

### Resolved Issues
*Move issues here once resolved*

## Decisions Log

### Phase 1 Decisions
*Document why specific files were kept or removed*

### Phase 2 Decisions
*Document which database model was chosen and why*

### Phase 3 Decisions
*Document whether missing actions were implemented or YAMLs updated*

## Commands for Validation

```bash
# Before starting any phase
git checkout -b cleanup-phase-X
git status

# After each removal
make check  # Or individually:
poetry run ruff check .
poetry run ruff format .
poetry run mypy biomapper biomapper-api biomapper_client
poetry run pytest

# Test strategies still work
poetry run biomapper health
poetry run biomapper metadata list

# Test API
cd biomapper-api && poetry run uvicorn app.main:app --reload
# Then test endpoints with curl or browser

# Measure metrics
find biomapper -name "*.py" | xargs wc -l  # Line count
poetry run pytest --cov=biomapper --cov=biomapper-api --cov=biomapper_client  # Coverage
```

## Notes
- Keep this document updated as cleanup progresses
- Add screenshots/outputs of successful test runs
- Document any unexpected findings
- Track time spent on each phase for future reference