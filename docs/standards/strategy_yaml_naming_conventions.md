# Strategy YAML Naming Conventions

## Overview

This document establishes naming conventions for strategy YAML files to ensure consistency, clarity, and maintainability across the biomapper project.

## Naming Structure

### Basic Format
```
{source}_{target}_{purpose}_{variant}.yaml
```

Where:
- `{source}`: Source dataset/database (lowercase)
- `{target}`: Target dataset/database (lowercase)
- `{purpose}`: Primary purpose of the strategy
- `{variant}`: Optional variant identifier

### Examples
```
ukbb_hpa_overlap.yaml                    # Basic overlap analysis
ukbb_hpa_overlap_with_resolution.yaml    # Variant with historical resolution
ukbb_arivale_bidirectional.yaml          # Bidirectional mapping
uniprot_ensemble_historical.yaml         # Historical resolution focus
```

## When to Create New Files vs. Modify Existing

### Create a NEW file when:

1. **Different Algorithm/Approach**
   - Adding historical resolution
   - Changing from unidirectional to bidirectional
   - Using different intermediate steps

2. **Different Use Case**
   - Research vs. production
   - Full analysis vs. quick check
   - Different output requirements

3. **Experimental Features**
   - Testing new actions
   - Trying alternative approaches
   - Performance optimization attempts

### MODIFY existing file when:

1. **Bug Fixes**
   - Fixing incorrect parameters
   - Correcting file paths
   - Updating endpoint names

2. **Minor Improvements**
   - Adjusting batch sizes
   - Changing log levels
   - Updating descriptions

3. **Maintaining Compatibility**
   - When downstream processes depend on it
   - When it's the "canonical" version

## Variant Naming Conventions

### Purpose-Based Variants

| Variant Suffix | Purpose | Example |
|----------------|---------|---------|
| `_basic` | Minimal implementation | `ukbb_hpa_overlap_basic.yaml` |
| `_full` | Complete analysis | `ukbb_hpa_overlap_full.yaml` |
| `_fast` | Performance optimized | `ukbb_hpa_overlap_fast.yaml` |
| `_validated` | With validation steps | `ukbb_hpa_overlap_validated.yaml` |
| `_historical` | With historical resolution | `ukbb_hpa_overlap_historical.yaml` |

### Environment-Based Variants

| Variant Suffix | Purpose | Example |
|----------------|---------|---------|
| `_dev` | Development testing | `ukbb_hpa_overlap_dev.yaml` |
| `_staging` | Staging environment | `ukbb_hpa_overlap_staging.yaml` |
| `_prod` | Production ready | `ukbb_hpa_overlap_prod.yaml` |

### Feature-Based Variants

| Variant Suffix | Purpose | Example |
|----------------|---------|---------|
| `_with_cache` | Includes caching | `ukbb_hpa_overlap_with_cache.yaml` |
| `_no_resolution` | Skips ID resolution | `ukbb_hpa_overlap_no_resolution.yaml` |
| `_composite` | Handles composite IDs | `ukbb_hpa_overlap_composite.yaml` |

## File Organization

### Directory Structure
```
configs/
├── strategies/
│   ├── production/        # Production-ready strategies
│   ├── experimental/      # Experimental/testing strategies
│   ├── deprecated/        # Old strategies kept for reference
│   └── examples/          # Example strategies for documentation
├── endpoints/             # Endpoint configurations
└── clients/              # Client configurations
```

### Migration Examples

#### Current → Recommended
```
# Current (unclear versioning)
ukbb_hpa_analysis_strategy.yaml
ukbb_hpa_analysis_strategy_optimized.yaml
ukbb_hpa_analysis_strategy_optimized_v2.yaml
ukbb_hpa_with_historical_resolution.yaml

# Recommended (clear purpose)
ukbb_hpa_overlap_basic.yaml              # Original basic version
ukbb_hpa_overlap_direct.yaml             # Direct UniProt comparison
ukbb_hpa_overlap_historical.yaml         # With historical resolution
ukbb_hpa_overlap_examples.yaml           # Example/documentation version
```

## Metadata in YAML Files

Each strategy YAML should include metadata:

```yaml
name: UKBB_HPA_OVERLAP_HISTORICAL
version: "1.0.0"
description: |
  UKBB-HPA protein overlap analysis with UniProt historical ID resolution.
  
metadata:
  created_date: "2024-01-15"
  modified_date: "2024-01-20"
  author: "biomapper-team"
  variant: "historical"
  replaces: "ukbb_hpa_overlap_basic.yaml"
  tags:
    - production
    - historical-resolution
    - protein-mapping
```

## Deprecation Process

When replacing a strategy:

1. **Mark as Deprecated**
   ```yaml
   # At the top of the old file
   # DEPRECATED: Use ukbb_hpa_overlap_historical.yaml instead
   # This file will be removed in version 2.0.0
   ```

2. **Move to Deprecated Folder**
   ```bash
   mv configs/strategies/old_strategy.yaml configs/strategies/deprecated/
   ```

3. **Update Documentation**
   - Update README files
   - Update example scripts
   - Add migration notes

## Best Practices

1. **Be Descriptive, Not Clever**
   - ❌ `ukbb_hpa_v2_final_final_really.yaml`
   - ✅ `ukbb_hpa_overlap_historical_validated.yaml`

2. **Avoid Version Numbers**
   - ❌ `strategy_v1.yaml`, `strategy_v2.yaml`
   - ✅ `strategy_basic.yaml`, `strategy_enhanced.yaml`

3. **Use Consistent Abbreviations**
   - `ukbb` not `uk_biobank` or `ukb`
   - `hpa` not `human_protein_atlas`
   - Document all abbreviations in a glossary

4. **Keep Names Reasonable Length**
   - ❌ `ukbb_to_hpa_protein_mapping_with_historical_resolution_and_validation_production.yaml`
   - ✅ `ukbb_hpa_protein_validated.yaml`

## Examples of Good Naming

```
# Clear purpose and variant
uniprot_ensemble_mapping_basic.yaml
uniprot_ensemble_mapping_historical.yaml
uniprot_ensemble_mapping_batch_optimized.yaml

# Different algorithms for same goal
protein_resolution_api_based.yaml
protein_resolution_local_cache.yaml
protein_resolution_hybrid.yaml

# Environment specific
gene_mapping_dev.yaml
gene_mapping_prod.yaml

# Feature specific
metabolite_mapping_with_synonyms.yaml
metabolite_mapping_exact_only.yaml
```

## Implementation Checklist

When creating a new strategy YAML:

- [ ] Follow naming convention
- [ ] Include metadata section
- [ ] Add descriptive comments
- [ ] Document parameters
- [ ] Specify which endpoints it uses
- [ ] Note any prerequisites
- [ ] Add example usage
- [ ] Update relevant documentation
- [ ] Consider if it replaces an existing strategy
- [ ] Place in appropriate directory

## Conclusion

Consistent naming helps:
- Developers find the right strategy quickly
- Understand the purpose without opening the file
- Track evolution of strategies over time
- Maintain clear documentation
- Avoid confusion between variants

When in doubt, err on the side of clarity over brevity.