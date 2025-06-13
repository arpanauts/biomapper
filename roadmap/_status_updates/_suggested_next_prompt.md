# Suggested Next Prompt for Biomapper Development

## Context Brief
The biomapper configuration system has been successfully refactored to separate mapping strategies from entity configurations, improving maintainability and reusability. The UKBB-HPA pipeline is fully functional with the new configuration-driven approach, and comprehensive documentation has been created for the new architecture.

## Initial Steps
1. Begin by reviewing `/home/ubuntu/biomapper/CLAUDE.md` for overall project context and guidelines
2. Check `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-13-configuration-separation-implementation.md` for details about the configuration separation
3. Review `/home/ubuntu/biomapper/docs/CONFIGURATION_MIGRATION_GUIDE.md` to understand the new structure
4. Check `/home/ubuntu/biomapper/configs/CONFIGURATION_QUICK_REFERENCE.md` for a quick overview

## Work Priorities

### Priority 1: Update UKBB-HPA Jupyter Notebook
The notebook at `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` needs updating to:
- Handle async MappingExecutor functions properly in Jupyter
- Use configuration from metamapper.db instead of hardcoded paths
- Demonstrate the new result structure with provenance tracking
- Add visualization of mapping results

### Priority 2: Test and Fix Other Protein Pipelines
Apply configuration-driven approach to:
- QIN OSP protein mapping pipeline
- Arivale protein mapping pipeline
- Verify they work with the separated configuration structure
- Fix any issues similar to those found in UKBB-HPA pipeline

### Priority 3: Create Strategy Development Guide
Document how to:
- Design new mapping strategies (generic vs entity-specific)
- Use action types effectively
- Test strategies in isolation
- Debug strategy execution

## References
- Configuration files: `/home/ubuntu/biomapper/configs/` (protein_config.yaml, mapping_strategies_config.yaml)
- Database population script: `/home/ubuntu/biomapper/scripts/setup_and_configuration/populate_metamapper_db.py`
- Validation script: `/home/ubuntu/biomapper/scripts/setup_and_configuration/validate_config_separation.py`
- Action types reference: `/home/ubuntu/biomapper/docs/ACTION_TYPES_REFERENCE.md`
- Working pipeline example: `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`

## Workflow Integration

Consider using Claude to:

1. **Design Strategy Test Framework** - Ask Claude to design a testing framework for mapping strategies that allows testing individual strategies without full pipeline execution

2. **Optimize Jupyter Async Handling** - Provide Claude with the current notebook code and ask for the best approach to handle async functions in Jupyter

3. **Create Strategy Templates** - Ask Claude to create template strategies for common mapping patterns

Example Claude prompt for Jupyter updates:
```
I have a Jupyter notebook at /home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb that needs to work with async functions from the MappingExecutor class. The notebook should:
1. Load configuration from metamapper.db instead of hardcoded paths
2. Handle async operations properly in Jupyter cells
3. Display progress during long-running operations
4. Visualize the mapping results

Please suggest the best approach for handling async operations in Jupyter and provide code examples for updating the notebook.
```

Example Claude prompt for strategy design:
```
Based on the biomapper's action types (CONVERT_IDENTIFIERS_LOCAL, EXECUTE_MAPPING_PATH, FILTER_IDENTIFIERS_BY_TARGET_PRESENCE), please design a generic mapping strategy template that could work for any two datasets that share a common identifier type. The strategy should:
1. Be parameterizable for different ontology types
2. Handle optional filtering steps
3. Include proper error handling
4. Follow the structure used in mapping_strategies_config.yaml

Explain when this generic strategy would be preferred over entity-specific strategies.
```