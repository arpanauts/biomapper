# Biomapper Architecture Cleanup Plan

## Executive Summary

The MVP successfully demonstrates that biomapper can work with a much simpler architecture:
- **YAML strategies** load data directly from files
- **Three simple actions** handle all protein mapping needs  
- **No database required** for the core mapping functionality
- **Direct API calls** to UniProt for resolution

**UPDATE**: Analysis reveals valuable mapping logic in legacy clients that should be preserved as new action types, particularly for chemical/metabolite mapping.

## Current Working Architecture (Minimal)

```
Client → API → YAML Strategy → Actions → Results
```

That's it. Everything else is legacy complexity.

## Components to REMOVE

### 1. Database-Related (metamapper.db)
- [ ] `/biomapper/db/models.py` - All SQLAlchemy models except cache
- [ ] `/biomapper/cli/metamapper_db_cli.py` - Database CLI
- [ ] `/biomapper/cli/metamapper_commands.py` - Database commands
- [ ] `/scripts/setup_and_configuration/populate_metamapper_db.py`
- [ ] `/metamapper_db_migrations/` - Entire directory
- [ ] All references to metamapper.db in SessionManager

### 2. Path-Based Mapping System
- [ ] `/biomapper/core/engine_components/path_finder.py`
- [ ] `/biomapper/core/engine_components/path_execution_manager.py`
- [ ] `/biomapper/core/engine_components/reversible_path.py`
- [ ] `/biomapper/core/engine_components/mapping_coordinator_service.py`
- [ ] `/biomapper/core/strategy_actions/execute_mapping_path.py`
- [ ] All path-related tests

### 3. Legacy Mapping Clients
- [ ] `/biomapper/mapping/` - MOST of directory tree (old client implementations)
- [ ] **PRESERVE for conversion to actions**:
  - [ ] `clients/pubchem_client.py` → CROSS_REFERENCE_COMPOUNDS action
  - [ ] `clients/chebi_client.py` → CROSS_REFERENCE_COMPOUNDS action
  - [ ] `clients/kegg_client.py` → MAP_TO_PATHWAYS action
  - [ ] `clients/refmet_client.py` → STANDARDIZE_METABOLITE_NAMES action
  - [ ] `clients/umls_client.py` → MAP_CLINICAL_TERMS action
  - [ ] `clients/unichem_client.py` → UNIFY_CHEMICAL_IDENTIFIERS action
  - [ ] `clients/uniprot_historical_resolver_client.py` → Keep as-is (used by MVP)
- [ ] Remove all other mapping components

### 4. Unused Features
- [ ] `/biomapper/rag/` - Entire RAG system
- [ ] `/biomapper/llm/` - Entire LLM integration
- [ ] `/biomapper/core/composite_handler.py` - Composite ID handling (MVP handles this)
- [ ] `/biomapper/core/mapping_executor_composite.py`

### 5. Over-Engineered Components
- [ ] Simplify MappingExecutor - remove all coordinators except Strategy
- [ ] Remove LifecycleCoordinator - not needed for stateless execution
- [ ] Remove checkpointing for now - can add back if needed
- [ ] Remove session management - stateless is simpler

## Components to KEEP & REFACTOR

### 1. Core Strategy System
```
/biomapper/core/
├── engine_components/
│   ├── strategy_orchestrator.py      # Keep - core of YAML execution
│   ├── strategy_handler.py           # Refactor - remove DB dependency
│   ├── action_executor.py            # Keep - executes actions
│   └── action_loader.py              # Keep - loads action classes
└── strategy_actions/
    ├── typed_base.py                 # Keep - base for new actions
    ├── load_dataset_identifiers.py   # Keep - MVP action
    ├── merge_with_uniprot_resolution.py  # Keep - MVP action
    ├── calculate_set_overlap.py      # Keep - MVP action
    # Future actions to implement:
    ├── cross_reference_compounds.py  # NEW - Chemical ID mapping
    ├── map_to_pathways.py            # NEW - KEGG pathway mapping
    └── standardize_metabolite_names.py # NEW - RefMet standardization
```

### 2. API Layer
```
/biomapper-api/
├── app/
│   ├── main.py                      # Keep
│   ├── services/
│   │   └── mapper_service.py         # Simplify - remove MappingExecutor
│   └── models/
│       └── strategy.py               # Keep - YAML validation
```

### 3. Client
```
/biomapper_client/
└── biomapper_client/
    └── client.py                     # Keep - works great
```

## Proposed Final Architecture

### Option 1: Ultra-Minimal (Recommended)
```python
# mapper_service.py
class YamlStrategyService:
    def __init__(self):
        self.strategies = self._load_yaml_strategies()
        self.action_registry = self._load_actions()
    
    async def execute_strategy(self, strategy_name: str, context: dict):
        strategy = self.strategies[strategy_name]
        for step in strategy.steps:
            action = self.action_registry[step.action.type]
            context = await action.execute(step.action.params, context)
        return context
```

### Option 2: Keep Some Structure
- Keep StrategyOrchestrator for complex workflows
- Keep ActionExecutor for standardized execution
- Remove all database and path-based code

## Migration Steps

### Phase 1: Create New Minimal Implementation
1. Create `/biomapper/core/minimal/` directory
2. Implement `YamlStrategyService` with just YAML loading and action execution
3. Update API to use new service
4. Test all 9 protein mappings

### Phase 1.5: Extract Valuable Clients as Actions
1. Create new action: CROSS_REFERENCE_COMPOUNDS (from PubChem/ChEBI clients)
2. Create new action: MAP_TO_PATHWAYS (from KEGG client)
3. Create new action: STANDARDIZE_METABOLITE_NAMES (from RefMet client)
4. Test with metabolomics datasets

### Phase 2: Remove Database Dependencies  
1. Remove metamapper.db references from all components
2. Update tests to not expect database
3. Remove database initialization code

### Phase 3: Delete Legacy Code
1. Delete directories listed above
2. Update imports
3. Run tests
4. Update documentation

### Phase 4: Simplify Remaining Code
1. Flatten directory structure
2. Merge similar components
3. Remove abstraction layers

## Benefits of Cleanup

1. **Simplicity**: From ~50 components to ~10
2. **Performance**: No database overhead
3. **Maintainability**: Clear, direct code path
4. **Flexibility**: Easy to add new actions
5. **Deployment**: No database setup required

## Risks & Mitigation

1. **Risk**: Losing functionality needed later
   - **Mitigation**: Tag current version, can cherry-pick if needed

2. **Risk**: Breaking existing integrations
   - **Mitigation**: Keep API contract identical

3. **Risk**: Removing useful abstractions
   - **Mitigation**: Start minimal, add abstractions as needed

## Success Criteria

After cleanup:
- [ ] All 9 protein mappings still work
- [ ] Code is <25% of current size
- [ ] No database required
- [ ] Clear documentation
- [ ] Fast execution (<30s for small datasets)
- [ ] New chemical/metabolite mapping actions implemented
- [ ] Valuable domain logic preserved from legacy clients

## Next Steps

1. Review and approve this plan
2. Create feature branch for cleanup
3. Implement Phase 1 (minimal service)
4. Test thoroughly
5. Proceed with phases 2-4