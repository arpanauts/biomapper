# Biomapper Action Types Reference

This document describes the available action types that can be used in mapping strategies.

## Overview

Action types are the building blocks of mapping strategies. Each action type corresponds to a method in the MappingExecutor that performs a specific transformation or filtering operation on identifiers.

## Configuration Context

Action types are used within mapping strategies, which are now centrally defined in `mapping_strategies_config.yaml`. This separation allows:
- **Generic strategies** to use action types that work across all entity types
- **Entity-specific strategies** to use specialized action types as needed
- **Reusable components** through the EXECUTE_MAPPING_PATH action type

See the [Configuration Migration Guide](/home/ubuntu/biomapper/docs/CONFIGURATION_MIGRATION_GUIDE.md) for details on the new structure.

## Available Action Types

### CONVERT_IDENTIFIERS_LOCAL
**Purpose**: Convert identifiers using local data files defined in the endpoint configuration.

**Parameters**:
- `endpoint_context`: "SOURCE" or "TARGET" - which endpoint's data to use
- `output_ontology_type`: The target ontology type for conversion
- `input_ontology_type` (optional): Override the input ontology type

**Example**:
```yaml
action:
  type: "CONVERT_IDENTIFIERS_LOCAL"
  endpoint_context: "SOURCE"
  output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

**Use Case**: Converting UKBB Assay IDs to UniProt ACs using the UKBB's local mapping file.

---

### EXECUTE_MAPPING_PATH
**Purpose**: Execute a predefined mapping path from the `mapping_paths` section.

**Parameters**:
- `path_name`: Name of the mapping path to execute

**Example**:
```yaml
action:
  type: "EXECUTE_MAPPING_PATH"
  path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"
```

**Use Case**: Running complex multi-step conversions that are reused across strategies.

---

### FILTER_IDENTIFIERS_BY_TARGET_PRESENCE
**Purpose**: Keep only identifiers that exist in the target endpoint's data.

**Parameters**:
- `endpoint_context`: "TARGET" - uses the target endpoint
- `ontology_type_to_match`: Which ontology type to check for presence

**Example**:
```yaml
action:
  type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
  endpoint_context: "TARGET"
  ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

**Use Case**: Filtering proteins to keep only those present in HPA dataset.

---

### FILTER_BY_TARGET_PRESENCE
**Purpose**: Alias for FILTER_IDENTIFIERS_BY_TARGET_PRESENCE (backward compatibility).

**Parameters**: Same as FILTER_IDENTIFIERS_BY_TARGET_PRESENCE

---

### MATCH_SHARED_ONTOLOGY
**Purpose**: Find matching identifiers between source and target using a shared ontology type.

**Parameters**:
- `shared_ontology_type`: The ontology type that both endpoints have

**Example**:
```yaml
action:
  type: "MATCH_SHARED_ONTOLOGY"
  shared_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

**Use Case**: Direct matching when both datasets have the same identifier type.

---

## Currently Implemented Action Types (from code inspection)

The following action types are actually implemented in the system:

1. **CONVERT_IDENTIFIERS_LOCAL** - ✅ Implemented in `ConvertIdentifiersLocalAction`
2. **EXECUTE_MAPPING_PATH** - ✅ Implemented in `ExecuteMappingPathAction`
3. **FILTER_IDENTIFIERS_BY_TARGET_PRESENCE** - ✅ Implemented in `FilterByTargetPresenceAction`
4. **FILTER_BY_TARGET_PRESENCE** - ⚠️ Alias accepted but routes to above
5. **MATCH_SHARED_ONTOLOGY** - ❌ In schema but not implemented

## Planned Action Types

As the system evolves, we anticipate adding:

### TRANSFORM_IDENTIFIERS
**Purpose**: Apply transformations like uppercase, lowercase, prefix/suffix operations, regex replacements.

**Parameters**:
- `transformation_type`: "uppercase", "lowercase", "prefix", "suffix", "regex"
- `transformation_value`: Value to add/remove/replace (for prefix/suffix/regex)

**Example**:
```yaml
action:
  type: "TRANSFORM_IDENTIFIERS"
  transformation_type: "prefix"
  transformation_value: "CHEMBL"
```

### MERGE_IDENTIFIER_SETS
**Purpose**: Combine results from multiple parallel paths or previous steps.

**Parameters**:
- `merge_strategy`: "union", "intersection", "difference"
- `source_sets`: List of previous step IDs to merge

**Example**:
```yaml
action:
  type: "MERGE_IDENTIFIER_SETS"
  merge_strategy: "union"
  source_sets: ["S2_PATH_A", "S2_PATH_B"]
```

### VALIDATE_IDENTIFIERS
**Purpose**: Check identifier format and validity, filtering out invalid ones.

**Parameters**:
- `validation_type`: "regex", "checksum", "api_verify"
- `validation_pattern`: Pattern or rules for validation
- `on_invalid`: "remove", "flag", "fail"

**Example**:
```yaml
action:
  type: "VALIDATE_IDENTIFIERS"
  validation_type: "regex"
  validation_pattern: "^[A-Z][0-9]{5}$"
  on_invalid: "remove"
```

### ENRICH_WITH_METADATA
**Purpose**: Add metadata from external sources without changing identifiers.

**Parameters**:
- `metadata_source`: Source of metadata (endpoint name or API)
- `metadata_fields`: List of fields to retrieve
- `join_on`: Ontology type to use for joining

**Example**:
```yaml
action:
  type: "ENRICH_WITH_METADATA"
  metadata_source: "uniprot_api"
  metadata_fields: ["protein_name", "organism", "length"]
  join_on: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

### SPLIT_COMPOSITE_IDENTIFIERS
**Purpose**: Handle composite identifiers like "Q14213_Q8NEV9" by splitting them.

**Parameters**:
- `delimiter`: Character(s) that separate the parts
- `keep_original`: Whether to keep the composite ID alongside split ones

**Example**:
```yaml
action:
  type: "SPLIT_COMPOSITE_IDENTIFIERS"
  delimiter: "_"
  keep_original: false
```

### RESOLVE_DEPRECATED_IDENTIFIERS
**Purpose**: Update obsolete/deprecated identifiers to current versions.

**Parameters**:
- `resolver_service`: Which service to use (e.g., "uniprot_history", "ncbi_gene_history")
- `include_secondary`: Whether to include secondary/alternative IDs

**Example**:
```yaml
action:
  type: "RESOLVE_DEPRECATED_IDENTIFIERS"
  resolver_service: "uniprot_history"
  include_secondary: true
```

### DEDUPLICATE_IDENTIFIERS
**Purpose**: Remove duplicate identifiers, with options for handling associated data.

**Parameters**:
- `dedup_strategy`: "keep_first", "keep_last", "merge_metadata"
- `case_sensitive`: Whether to consider case in deduplication

**Example**:
```yaml
action:
  type: "DEDUPLICATE_IDENTIFIERS"
  dedup_strategy: "keep_first"
  case_sensitive: false
```

### BATCH_API_LOOKUP
**Purpose**: Efficiently query external APIs with batching and rate limiting.

**Parameters**:
- `api_endpoint`: API service to query
- `batch_size`: Number of identifiers per request
- `rate_limit`: Requests per second
- `retry_strategy`: How to handle failures

**Example**:
```yaml
action:
  type: "BATCH_API_LOOKUP"
  api_endpoint: "pubchem_compound_lookup"
  batch_size: 100
  rate_limit: 5
  retry_strategy: "exponential_backoff"
```

---

## Creating New Action Types

To add a new action type:

1. Define the action in this document
2. Implement the handler method in `MappingExecutor`
3. Add the action type to the JSON schema enum
4. Create unit tests for the new action
5. Update example strategies to demonstrate usage

---

## Best Practices

1. **Keep actions atomic** - Each action should do one thing well
2. **Use descriptive names** - Action types should clearly indicate their purpose
3. **Document parameters** - All parameters should be clearly documented
4. **Provide examples** - Include real-world usage examples
5. **Consider reusability** - Design actions to work across different entity types

---

## Cross-Entity Considerations

Some action types are generic enough to work across entity types:
- CONVERT_IDENTIFIERS_LOCAL
- EXECUTE_MAPPING_PATH
- FILTER_IDENTIFIERS_BY_TARGET_PRESENCE

Others might be entity-specific:
- RESOLVE_CHEMICAL_STRUCTURE (for metabolites)
- NORMALIZE_CLINICAL_UNITS (for clinical labs)

This suggests that core action types should remain entity-agnostic where possible.