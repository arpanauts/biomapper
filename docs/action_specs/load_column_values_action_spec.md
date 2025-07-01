# LOAD_COLUMN_VALUES Action Specification

## Overview

A flexible action type for loading values from any column of an endpoint's data source, not limited to the primary identifier column.

## Motivation

Current limitation: `LOAD_ENDPOINT_IDENTIFIERS` only loads the primary identifier column. Many use cases require loading non-primary columns:
- Loading UniProt IDs when gene names are primary (HPA case)
- Loading metadata columns for filtering
- Loading alternate identifiers for cross-referencing

## Interface

```python
@register_action("LOAD_COLUMN_VALUES")
class LoadColumnValuesAction(BaseStrategyAction):
    """
    Load values from any column of an endpoint's data source.
    
    Required parameters:
    - endpoint_name: Name of the endpoint to load from
    - column_name: Name of the column to extract values from
    - output_context_key: Where to store the values in context
    
    Optional parameters:
    - output_ontology_type: Ontology type of the extracted values
    - filter_column: Column to filter on (if filtering needed)
    - filter_values: Values to filter by
    - unique_only: Whether to return only unique values (default: True)
    - skip_empty: Whether to skip empty/null values (default: True)
    """
```

## Usage Examples

### Example 1: Load UniProt from HPA
```yaml
- name: LOAD_HPA_UNIPROT_VALUES
  action:
    type: LOAD_COLUMN_VALUES
    params:
      endpoint_name: "HPA_OSP_PROTEIN"
      column_name: "uniprot"
      output_context_key: "hpa_uniprot_ids"
      output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

### Example 2: Load Panel Information
```yaml
- name: LOAD_UKBB_ONCOLOGY_PROTEINS
  action:
    type: LOAD_COLUMN_VALUES
    params:
      endpoint_name: "UKBB_PROTEIN"
      column_name: "UniProt"
      output_context_key: "oncology_proteins"
      filter_column: "Panel"
      filter_values: ["Oncology"]
      output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
```

### Example 3: Load All Metadata
```yaml
- name: LOAD_PROTEIN_DESCRIPTIONS
  action:
    type: LOAD_COLUMN_VALUES
    params:
      endpoint_name: "UNIPROT_METADATA"
      column_name: "description"
      output_context_key: "protein_descriptions"
      unique_only: false  # Keep duplicates for mapping
```

## Implementation Considerations

1. **Reuse existing components**:
   - Use CSVAdapter for file loading
   - Leverage endpoint configuration from database
   - Follow patterns from LOAD_ENDPOINT_IDENTIFIERS

2. **Performance optimizations**:
   - Load only requested column(s)
   - Stream large files if possible
   - Cache results in context

3. **Error handling**:
   - Validate column exists before loading
   - Handle missing/malformed data gracefully
   - Provide clear error messages

4. **Provenance tracking**:
   - Record which column was loaded
   - Track filtering criteria if used
   - Note unique vs all values

## Benefits

1. **Flexibility**: Load any column, not just primary identifiers
2. **Efficiency**: Avoid workarounds with LOCAL_ID_CONVERTER
3. **Clarity**: Intent is clear in strategy YAML
4. **Reusability**: Common pattern across many use cases

## Migration Path

Existing strategies using workarounds can be updated:

### Before (workaround):
```yaml
- name: LOAD_HPA_DATA
  action:
    type: LOCAL_ID_CONVERTER
    params:
      mapping_file: "/path/to/hpa.csv"
      source_column: "gene"
      target_column: "uniprot"
      # Hacky way to just load UniProt values
```

### After (clean):
```yaml
- name: LOAD_HPA_DATA
  action:
    type: LOAD_COLUMN_VALUES
    params:
      endpoint_name: "HPA_OSP_PROTEIN"
      column_name: "uniprot"
      output_context_key: "hpa_uniprot_ids"
```

## Priority

Medium - Would clean up several existing strategies and enable new use cases without major architectural changes.