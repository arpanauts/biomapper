# Biomapper Mapping Concepts: Paths, Strategies, and Actions

This document explains the key differences between **Mapping Paths**, **Mapping Strategies**, and **Action Types** in the Biomapper codebase. These three concepts work together to enable flexible, powerful biological entity mapping.

## Overview

The Biomapper system uses a layered approach to mapping:

1. **Mapping Paths** - Low-level atomic conversions between ontology types
2. **Action Types** - Mid-level operations that orchestrate paths and transformations
3. **Mapping Strategies** - High-level workflows composed of multiple actions

## 1. Mapping Paths

### Definition
A **Mapping Path** is the most fundamental unit of identifier conversion in Biomapper. It represents a single, atomic transformation from one ontology type to another using a specific resource (API, database, or file).

### Characteristics
- **Atomic**: Each path performs exactly one conversion
- **Resource-bound**: Each path is tied to a specific MappingResource (e.g., UniProt API, local TSV file)
- **Direct**: No intermediate steps or logic - just input → resource → output
- **Reusable**: Can be used by multiple strategies or the iterative mapper

### Example
```yaml
mapping_paths:
  GENE_NAME_TO_UNIPROT_VIA_API:
    description: "Convert gene names to UniProt ACs using UniProt API"
    path_steps:
      - step_number: 1
        mapping_resource: "uniprot_gene_name_api"
        input_ontology_type: "GENE_NAME"
        output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

### Storage
Defined in entity-specific config files (e.g., `protein_config.yaml`) and stored in the `mapping_paths` table in `metamapper.db`.

## 2. Action Types

### Definition
An **Action Type** represents a specific operation that can be performed on a set of identifiers during a mapping workflow. Actions are the building blocks of strategies and can execute mapping paths, perform filtering, or transform data.

### Characteristics
- **Modular**: Each action has a single, well-defined purpose
- **Parameterized**: Accept configuration parameters to customize behavior
- **Chainable**: Output from one action becomes input to the next
- **Implementation**: Each action type corresponds to a Python class in `biomapper/core/strategy_actions/`

### Currently Implemented Action Types

1. **CONVERT_IDENTIFIERS_LOCAL**
   - Converts identifiers using local data files from an endpoint
   - Parameters: `endpoint_context`, `output_ontology_type`

2. **EXECUTE_MAPPING_PATH**
   - Executes a predefined mapping path by name
   - Parameters: `path_name`

3. **FILTER_IDENTIFIERS_BY_TARGET_PRESENCE**
   - Filters to keep only identifiers present in the target endpoint
   - Parameters: `endpoint_context`, `ontology_type_to_match`

### Example
```yaml
action:
  type: "EXECUTE_MAPPING_PATH"
  path_name: "GENE_NAME_TO_UNIPROT_VIA_API"
```

### Future Action Types (Planned)
- `TRANSFORM_IDENTIFIERS` - Apply text transformations
- `MERGE_IDENTIFIER_SETS` - Combine results from parallel paths
- `VALIDATE_IDENTIFIERS` - Check format validity
- `SPLIT_COMPOSITE_IDENTIFIERS` - Handle composite IDs
- `DEDUPLICATE_IDENTIFIERS` - Remove duplicates

## 3. Mapping Strategies

### Definition
A **Mapping Strategy** is a high-level, multi-step workflow that orchestrates a sequence of actions to achieve complex mapping goals. Strategies provide explicit control over the mapping pipeline.

### Characteristics
- **Sequential**: Actions execute in a defined order
- **Conditional**: Steps can be marked as required or optional
- **Stateful**: Data flows from one step to the next
- **Explicit**: Every step is clearly defined (vs. automatic discovery)
- **Reproducible**: Same inputs always produce same outputs

### Example
```yaml
mapping_strategies:
  UKBB_TO_HPA_PROTEIN_RESOLVED:
    description: "Map UKBB proteins to HPA with UniProt history resolution"
    mapping_strategy_steps:
      - step_name: "Convert UKBB to UniProt"
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "SOURCE"
          output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        is_required: true
        
      - step_name: "Resolve UniProt history"
        action:
          type: "EXECUTE_MAPPING_PATH"
          path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"
        is_required: false  # Continue if API fails
        
      - step_name: "Filter by HPA presence"
        action:
          type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
          endpoint_context: "TARGET"
          ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
        is_required: false
```

### Storage
Defined in entity-specific config files and stored in the `mapping_strategies` table in `metamapper.db`.

## Key Differences

### 1. Level of Abstraction
- **Mapping Paths**: Lowest level - direct resource calls
- **Action Types**: Mid level - orchestrate paths and add logic
- **Mapping Strategies**: Highest level - complete workflows

### 2. Flexibility
- **Mapping Paths**: Fixed - always do the same conversion
- **Action Types**: Configurable - behavior changes based on parameters
- **Mapping Strategies**: Compositional - combine actions in different ways

### 3. Use Cases

**Use Mapping Paths when:**
- You need a simple, direct conversion
- A single resource can provide the mapping
- No intermediate processing is required

**Use Action Types when:**
- You need to add logic around path execution
- You want to filter, transform, or validate data
- You're building reusable operations

**Use Mapping Strategies when:**
- Multiple steps are required
- You need explicit control over the workflow
- Complex pipelines with conditional logic
- Reproducibility is critical

## Relationship to Iterative Mapping

The **Iterative Mapping Strategy** (default behavior of `MappingExecutor`) is an alternative to explicit YAML-defined strategies:

- **Iterative**: Automatically discovers and tries different paths
- **Priority-based**: Uses `OntologyPreference` rankings
- **Flexible**: Adapts to available identifiers
- **Best for**: Simple cases or discovery-oriented mapping

In contrast, YAML-defined strategies provide:
- **Explicit control**: Every step is defined
- **Predictability**: No automatic discovery
- **Best for**: Complex, well-understood pipelines

## Architecture Flow

```
User Request
    ↓
MappingExecutor
    ↓
┌─────────────────────────────┐
│ Strategy Selection          │
│ - Explicit strategy name?   │
│ - Use iterative default?    │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Strategy Execution          │
│ For each step:              │
│ - Load action type          │
│ - Execute action            │
│ - Pass results to next step │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Action Execution            │
│ - May execute mapping paths │
│ - May filter/transform data │
│ - Returns modified dataset  │
└─────────────────────────────┘
    ↓
Final Results

```

## Best Practices

1. **Keep paths atomic**: One path = one conversion via one resource
2. **Make actions reusable**: Design actions to work across entity types
3. **Document strategies**: Explain why each step is needed
4. **Use `is_required` wisely**: Mark critical steps as required, nice-to-haves as optional
5. **Test incrementally**: Test paths → actions → strategies

## Summary

- **Mapping Paths** are the atoms - simple, direct conversions
- **Action Types** are the molecules - combine paths with logic
- **Mapping Strategies** are the reactions - orchestrate complex workflows

This layered approach provides both the flexibility for simple mappings and the control needed for complex, multi-step transformations while maintaining modularity and reusability throughout the system.