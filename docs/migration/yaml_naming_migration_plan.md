# YAML Naming Migration Plan

## Current State Analysis

### Existing YAML Files
```
configs/
├── ukbb_hpa_analysis_strategy.yaml
├── ukbb_hpa_analysis_strategy_optimized.yaml  
├── ukbb_hpa_analysis_strategy_optimized_v2.yaml
├── ukbb_hpa_with_historical_resolution.yaml
├── example_uniprot_historical_resolution_strategy.yaml
├── full_featured_ukbb_hpa_strategy.yaml
└── legacy/
    ├── protein_config.yaml
    └── mapping_strategies_config.yaml
```

## Proposed New Structure

### Phase 1: Reorganize Directory Structure
```
configs/
├── strategies/
│   ├── production/
│   │   ├── ukbb_hpa_overlap_historical.yaml      # Main production version
│   │   └── README.md                             # Documentation
│   ├── examples/
│   │   ├── uniprot_resolution_example.yaml       # Teaching example
│   │   └── README.md
│   ├── experimental/
│   │   └── ukbb_hpa_overlap_direct.yaml          # New optimized approach
│   └── deprecated/
│       ├── ukbb_hpa_analysis_strategy.yaml       # Original
│       └── MIGRATION.md                          # Migration guide
├── endpoints/
│   └── protein_endpoints.yaml                    # Extracted from legacy
└── legacy/                                       # Keep as-is for now
```

### Phase 2: File Renaming Map

| Current File | New Name | Location | Notes |
|--------------|----------|----------|-------|
| `ukbb_hpa_analysis_strategy.yaml` | `ukbb_hpa_overlap_basic.yaml` | `deprecated/` | Original implementation |
| `ukbb_hpa_analysis_strategy_optimized.yaml` | (delete) | - | Superseded by v2 |
| `ukbb_hpa_analysis_strategy_optimized_v2.yaml` | `ukbb_hpa_overlap_direct.yaml` | `experimental/` | Direct UniProt approach |
| `ukbb_hpa_with_historical_resolution.yaml` | `ukbb_hpa_overlap_historical.yaml` | `production/` | Full featured version |
| `example_uniprot_historical_resolution_strategy.yaml` | `uniprot_resolution_example.yaml` | `examples/` | Teaching example |
| `full_featured_ukbb_hpa_strategy.yaml` | `ukbb_hpa_overlap_full.yaml` | `experimental/` | Comprehensive version |

## Migration Steps

### Step 1: Create Directory Structure
```bash
mkdir -p configs/strategies/{production,examples,experimental,deprecated}
mkdir -p configs/endpoints
```

### Step 2: Update YAML Headers
Add metadata to each file:

```yaml
# Example for ukbb_hpa_overlap_historical.yaml
name: UKBB_HPA_OVERLAP_HISTORICAL
version: "1.0.0"
metadata:
  description: "UKBB-HPA protein overlap with historical ID resolution"
  created_date: "2024-01-15"
  variant: "historical"
  replaces: ["ukbb_hpa_analysis_strategy.yaml"]
  status: "production"
```

### Step 3: Update Code References
Files that need updating:
- `/home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`
- `/home/ubuntu/biomapper/biomapper-api/main.py` (if it loads strategies)
- Test files referencing strategy names
- Documentation mentioning file names

### Step 4: Create Symbolic Links (Temporary)
For backward compatibility during transition:
```bash
cd configs
ln -s strategies/production/ukbb_hpa_overlap_historical.yaml ukbb_hpa_analysis_strategy.yaml
```

### Step 5: Update Documentation
1. Update README files
2. Update API documentation  
3. Update example notebooks
4. Create migration guide for users

### Step 6: Deprecation Notices
Add to old files:
```yaml
# DEPRECATED: This file has been moved to strategies/deprecated/
# Please use configs/strategies/production/ukbb_hpa_overlap_historical.yaml
# This file will be removed in version 2.0.0
```

## Benefits of Migration

1. **Clarity**: Purpose is clear from filename
2. **Organization**: Related strategies grouped together
3. **Versioning**: No more v1, v2, v3 confusion
4. **Discovery**: Easier to find the right strategy
5. **Maintenance**: Clear which are production-ready

## Timeline

- **Week 1**: Create directory structure, update documentation
- **Week 2**: Move and rename files, add metadata
- **Week 3**: Update code references, add symlinks
- **Week 4**: Test all pipelines, remove symlinks
- **Week 5**: Clean up, remove deprecated files

## Rollback Plan

If issues arise:
1. Keep original files in `deprecated/` folder
2. Maintain symbolic links for 1-2 releases
3. Document both old and new names
4. Provide clear migration warnings

## Success Criteria

- [ ] All strategies follow naming convention
- [ ] No broken references in code
- [ ] Documentation updated
- [ ] Tests pass with new names
- [ ] Users notified of changes
- [ ] Migration guide available