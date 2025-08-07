# Biomapper Cleanup Plan
*Based on Investigation Results from August 7, 2025*

## Overview
This plan addresses the ~30-40% dead code identified in the architecture investigation, prioritized by risk and impact.

## Phase 1: Safe Immediate Removals (Low Risk)
**Timeline: Can be done immediately**
**Risk: Low - No active dependencies**

### 1.1 Remove Old Action Files
```bash
# Remove deprecated action files
rm biomapper/core/strategy_actions/load_endpoint_identifiers_action_old.py
rm biomapper/core/strategy_actions/format_and_save_results_action_old.py
```

### 1.2 Clean Engine Components Directory
```bash
# Remove unused engine components (keep only CheckpointManager and ProgressReporter)
rm biomapper/core/engine_components/action_loader.py
rm biomapper/core/engine_components/config_loader.py
rm biomapper/core/engine_components/robust_execution_coordinator.py
rm biomapper/core/engine_components/strategy_coordinator_service.py
# Update __init__.py to only export CheckpointManager and ProgressReporter
```

### 1.3 Remove Duplicate/Unused API Routes
```bash
# After confirming which routes are active, remove duplicates
# Candidates: strategies_enhanced.py or strategies_v2_simple.py (keep one)
# Remove unused: files.py, mapping.py (if confirmed unused)
```

## Phase 2: Database Model Consolidation (Medium Risk)
**Timeline: 1-2 days**
**Risk: Medium - Requires migration and testing**

### 2.1 Analyze Model Usage
- Compare `app/models/job.py` vs `app/models/persistence.py`
- Identify which is actually used by PersistenceService
- Check Alembic migrations to understand history

### 2.2 Consolidate Models
```python
# Decision tree:
# If job.py is primary → migrate persistence.py features to job.py
# If persistence.py is primary → migrate job.py features to persistence.py
# Create single source of truth for database models
```

### 2.3 Update Dependencies
- Update all imports to use consolidated model
- Run tests to verify persistence still works
- Create Alembic migration if schema changes

## Phase 3: Fix Missing Actions (High Priority)
**Timeline: 2-3 days**
**Risk: Medium - Features may be broken without these**

### 3.1 Critical Missing Actions
These are referenced in YAMLs but not implemented:
1. **EXPORT_DATASET** - Used in 6 strategies
2. **CUSTOM_TRANSFORM** - Used in 1 strategy
3. **EXECUTE_MAPPING_PATH** - Used in multiple strategies

### 3.2 Implementation Options
```python
# Option A: Implement missing actions
# Create new action classes with @register_action decorator

# Option B: Update YAMLs to remove references
# Only if features are not needed

# Option C: Find if they exist under different names
# Check if functionality exists with different action type
```

### 3.3 Lower Priority Missing Actions
- AGGREGATE_RESULTS
- CONDITIONAL_EXECUTE
- VALIDATE_IDENTIFIERS
- PARAMETER_SWEEP

## Phase 4: Script Modernization (Medium Risk)
**Timeline: 3-4 days**
**Risk: Medium - Scripts need testing after conversion**

### 4.1 Convert Direct Imports to BiomapperClient
Scripts requiring conversion (11 files):
```python
# Old pattern (remove):
from biomapper.core.minimal_strategy_service import MinimalStrategyService
service = MinimalStrategyService()

# New pattern (use):
from biomapper_client import BiomapperClient
client = BiomapperClient()
client.execute_strategy("STRATEGY_NAME")
```

### 4.2 Priority Order
1. Most frequently used scripts first
2. Scripts used in documentation/tutorials
3. Utility/helper scripts
4. Experimental/research scripts

## Phase 5: Remove Unused Actions (Low Risk)
**Timeline: 1 day**
**Risk: Low - Already confirmed unused**

### 5.1 Remove Unused Registered Actions
- PROTEIN_EXTRACT_UNIPROT_FROM_XREFS
- PROTEIN_MULTI_BRIDGE
- Any others confirmed unused after Phase 3

### 5.2 Clean Up Action Directories
- Remove empty directories under strategy_actions/
- Consolidate related actions into logical groups

## Phase 6: Legacy Component Analysis (Investigation Needed)
**Timeline: 2-3 days investigation**
**Risk: Variable - Needs deeper analysis**

### 6.1 Investigate Base Classes
```python
# Check usage of:
biomapper/core/base_client.py
biomapper/core/base_llm.py
biomapper/core/base_mapper.py
biomapper/core/base_pipeline.py
biomapper/core/base_rag.py
biomapper/core/base_spoke.py
biomapper/core/base_store.py
```

### 6.2 Analyze Mapping Clients
Determine which are actively used:
- arivale_lookup_client.py
- translator_name_resolver_client.py
- umls_client.py
- unichem_client.py
- uniprot_name_client.py

## Phase 7: Test Coverage Improvement
**Timeline: Ongoing**
**Risk: None - Only adds safety**

### 7.1 Add Tests for Untested Components
- Priority: Active components with no tests
- Create tests before any refactoring
- Ensure 80% coverage minimum

### 7.2 Remove Tests for Deleted Components
- Clean up test files for removed code
- Update test documentation

## Validation Checklist

Before removing any component:
- [ ] Run full test suite: `poetry run pytest`
- [ ] Check linting: `poetry run ruff check .`
- [ ] Verify type checking: `poetry run mypy biomapper biomapper-api biomapper_client`
- [ ] Test all example scripts still work
- [ ] Verify all YAML strategies execute successfully
- [ ] Check API endpoints still respond correctly
- [ ] Review import dependencies one more time

## Success Metrics

### Quantitative
- Lines of code reduced by 30-40%
- Test coverage maintained or improved
- API response time maintained or improved
- All existing functionality preserved

### Qualitative
- Clearer architecture boundaries
- Easier onboarding for new developers
- Reduced cognitive load
- Better maintainability

## Risk Mitigation

1. **Create backup branch before each phase**
   ```bash
   git checkout -b cleanup-phase-X-backup
   ```

2. **Test after each removal**
   ```bash
   make check  # Run all checks
   ```

3. **Document decisions**
   - Why each component was removed
   - What it was replaced with (if anything)
   - Any behavioral changes

4. **Incremental commits**
   - One logical change per commit
   - Clear commit messages
   - Easy to revert if needed

## Communication Plan

1. Create GitHub issue for tracking: "Architecture Cleanup - Remove 30-40% Dead Code"
2. Create PR for each phase
3. Update CLAUDE.md after major changes
4. Update README if user-facing changes
5. Notify team of any breaking changes (there shouldn't be any)

## Post-Cleanup Tasks

1. Update architecture documentation
2. Update developer onboarding guides
3. Create new architecture diagram
4. Performance benchmarking
5. Celebrate the cleaner codebase! 🎉