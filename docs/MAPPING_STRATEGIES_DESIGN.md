# Mapping Strategies Design Document

## Overview

This document explains the design philosophy behind separating mapping strategies from entity-specific configurations, enabling reusable mapping logic across different biological entity types.

## Motivation

The current approach embeds mapping strategies within entity-specific config files (e.g., `protein_config.yaml`). This leads to:
- Duplication of similar strategies across entity types
- Difficulty in maintaining consistent mapping logic
- Limited reusability of proven mapping patterns

## Proposed Architecture

### 1. Separation of Concerns

**Entity Config Files** (`protein_config.yaml`, `metabolite_config.yaml`, etc.):
- Define data sources (endpoints)
- Define ontology types
- Define mapping paths (simple conversions)
- Focus on "what data exists"

**Strategy Config File** (`mapping_strategies_config.yaml`):
- Define reusable mapping strategies
- Define action sequences
- Focus on "how to map"

### 2. Strategy Categories

#### Generic Strategies
Work across any entity type with appropriate parameters:
- `DIRECT_SHARED_ONTOLOGY_MATCH` - Simple matching via shared ID
- `BRIDGE_VIA_COMMON_ID` - Use intermediate identifier
- `RESOLVE_AND_MATCH` - Handle deprecated IDs

#### Entity-Specific Strategies
Tailored to specific entity types but still reusable:
- Protein: `HANDLE_COMPOSITE_UNIPROT`
- Metabolite: `PUBCHEM_TO_HMDB_VIA_INCHIKEY`
- Clinical Lab: `NORMALIZE_LAB_UNITS`

### 3. Parameter System

Strategies can define parameters that are filled at runtime:
```yaml
parameters:
  - name: "bridge_ontology_type"
    description: "The ontology type to use as bridge"
    required: true
```

Usage in steps:
```yaml
action:
  type: "CONVERT_IDENTIFIERS_LOCAL"
  output_ontology_type: "${bridge_ontology_type}"
```

### 4. Benefits

1. **Reusability**: Same strategy works for proteins, metabolites, genes
2. **Maintainability**: Fix a strategy once, benefit everywhere
3. **Testability**: Test strategies independently
4. **Discoverability**: Clear catalog of available strategies
5. **Composability**: Combine strategies for complex workflows

## Implementation Plan

### Phase 1: Proof of Concept
1. Create `mapping_strategies_config.yaml` with core strategies
2. Update `populate_metamapper_db.py` to load from both sources
3. Modify `MappingExecutor` to resolve strategy references

### Phase 2: Migration
1. Extract strategies from existing entity configs
2. Parameterize entity-specific values
3. Update existing pipelines to use new structure

### Phase 3: Enhancement
1. Add strategy composition support
2. Implement strategy validation
3. Create strategy testing framework

## Example Usage

### Current Approach
In `protein_config.yaml`:
```yaml
mapping_strategies:
  UKBB_TO_HPA_PROTEIN_PIPELINE:
    # Full strategy definition embedded here
```

### New Approach
In `protein_config.yaml`:
```yaml
strategy_references:
  UKBB_TO_HPA: 
    strategy: "BRIDGE_VIA_COMMON_ID"
    parameters:
      bridge_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
      target_native_ontology_type: "HPA_OSP_PROTEIN_ID_ONTOLOGY"
```

In `mapping_strategies_config.yaml`:
```yaml
generic_strategies:
  BRIDGE_VIA_COMMON_ID:
    # Reusable strategy definition
```

## Considerations

### Backward Compatibility
- Support both embedded and referenced strategies initially
- Provide migration tools for existing configs
- Clear deprecation timeline

### Performance
- Strategy resolution happens at config load time
- No runtime performance impact
- Potential for strategy caching

### Flexibility vs. Complexity
- Balance reusability with readability
- Avoid over-abstraction
- Keep simple cases simple

## Future Extensions

1. **Strategy Versioning**: Track strategy versions for reproducibility
2. **Strategy Library**: Share strategies across organizations
3. **Visual Strategy Builder**: GUI for creating strategies
4. **Strategy Analytics**: Track which strategies are most effective

## Conclusion

Separating mapping strategies from entity configurations provides a cleaner, more maintainable architecture that scales better as the Biomapper system grows to handle more entity types and mapping scenarios.