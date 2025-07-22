# Action 1: LOAD_DATASET_IDENTIFIERS - Design Decision

## The Sequential Flow

In the YAML strategy, we call the SAME action type twice with different parameters:

```yaml
steps:
  # First call to LOAD_DATASET_IDENTIFIERS
  - name: load_ukbb
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/ukbb/UKBB_Protein_Meta.tsv"
        file_type: "tsv"  # or auto-detect from extension
        identifier_column: "UniProt"  # which column has the IDs
        strip_prefix: null  # no prefix to strip
        composite_separator: "_"  # for Q14213_Q8NEV9
        filter_column: null  # no filtering needed
        filter_values: null
        output_key: "ukbb_raw"  # where to store in context

  # Second call to LOAD_DATASET_IDENTIFIERS  
  - name: load_hpa
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/hpa/hpa_osps.csv"
        file_type: "csv"
        identifier_column: "uniprot"  # different column name!
        strip_prefix: null
        composite_separator: "_"
        filter_column: null
        filter_values: null
        output_key: "hpa_raw"  # different location in context

  # For KG2C with prefixes and filtering
  - name: load_kg2c
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "/data/kg2c/kg2c_proteins.csv"
        file_type: "csv"
        identifier_column: "id"
        strip_prefix: "UniProtKB:"  # Remove this prefix
        composite_separator: null  # no composites in KG2C
        filter_column: "id"  # filter on same column
        filter_values: ["^UniProtKB:"]  # regex: starts with UniProtKB:
        output_key: "kg2c_raw"
```

## Simplified Parameters

```python
class LoadDatasetIdentifiersParams(BaseModel):
    # File access
    file_path: str
    file_type: Optional[Literal["csv", "tsv", "auto"]] = "auto"
    
    # Column identification
    identifier_column: str  # Which column has the main IDs
    
    # Data cleaning
    strip_prefix: Optional[str] = None  # e.g., "UniProtKB:"
    composite_separator: Optional[str] = None  # e.g., "_"
    
    # Filtering (e.g., for KG2C)
    filter_column: Optional[str] = None
    filter_values: Optional[List[str]] = None  # Can be regex patterns
    filter_mode: Literal["include", "exclude"] = "include"
    
    # Output
    output_key: str  # Where to store in context
    
    # Options
    drop_empty_ids: bool = True
    preserve_all_columns: bool = True  # Keep all columns, not just ID
```

## What This Action Does

1. **Read file** based on file_type
2. **Find identifier column** by name
3. **If strip_prefix**: Remove prefix from IDs
4. **If filter_column**: Keep only rows matching filter
5. **If composite_separator**: Expand composite IDs
6. **Drop empty IDs** if requested
7. **Store in context** at output_key

## Benefits of This Design

1. **Same action, different params** - reusable for all datasets
2. **Flexible** - handles all our cases (UKBB, HPA, SPOKE, KG2C)
3. **Simple** - each parameter has one clear purpose
4. **Sequential** - each load stores to different context key

## Data Flow

```
Step 1: LOAD UKBB → context['datasets']['ukbb_raw']
Step 2: LOAD HPA → context['datasets']['hpa_raw']
Step 3: MERGE using both datasets from context
```

Does this design make sense? We're using the same action TYPE multiple times with different parameters, not trying to load both files in one action call.