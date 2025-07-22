# Action 1: LOAD_DATASET_IDENTIFIERS - Final Design

## Purpose
Load tabular data from files with intelligent handling of biological identifiers.

## Key Design Decisions
1. **NO composite splitting** - Keep composite IDs intact (e.g., "Q14213_Q8NEV9")
2. **Preserve original data** - Never modify, only add new columns
3. **Standard naming convention** - Original data saved as "{column}_original"

## Parameters

```python
class LoadDatasetIdentifiersParams(BaseModel):
    # File access
    file_path: str = Field(..., description="Path to CSV/TSV file")
    file_type: Optional[Literal["csv", "tsv", "auto"]] = Field("auto", description="File format")
    
    # Column identification  
    identifier_column: str = Field(..., description="Column containing primary identifiers")
    
    # Data cleaning (optional)
    strip_prefix: Optional[str] = Field(None, description="Prefix to remove (e.g., 'UniProtKB:')")
    
    # Filtering (optional)
    filter_column: Optional[str] = Field(None, description="Column to filter on")
    filter_values: Optional[List[str]] = Field(None, description="Values to match (can be regex)")
    filter_mode: Literal["include", "exclude"] = Field("include", description="Include or exclude matches")
    
    # Output
    output_key: str = Field(..., description="Key for storing in context['datasets']")
    
    # Options
    drop_empty_ids: bool = Field(True, description="Remove rows where identifier column is empty")
```

## Processing Logic

```python
def execute(params, context):
    # 1. Read file
    df = read_file(params.file_path, params.file_type)
    
    # 2. Apply filter if specified
    if params.filter_column and params.filter_values:
        mask = create_filter_mask(df, params.filter_column, params.filter_values, params.filter_mode)
        df = df[mask]
        log.info(f"Filtered to {len(df)} rows")
    
    # 3. Strip prefix if specified
    if params.strip_prefix:
        # Preserve original
        df[f"{params.identifier_column}_original"] = df[params.identifier_column]
        # Clean the main column
        df[params.identifier_column] = df[params.identifier_column].str.replace(
            params.strip_prefix, '', regex=False
        )
        log.info(f"Stripped prefix '{params.strip_prefix}' from {params.identifier_column}")
    
    # 4. Drop empty identifiers if requested
    if params.drop_empty_ids:
        before = len(df)
        df = df[df[params.identifier_column].notna()]
        log.info(f"Dropped {before - len(df)} rows with empty identifiers")
    
    # 5. Add metadata
    df['_source_file'] = params.file_path
    df['_row_number'] = range(1, len(df) + 1)
    
    # 6. Store in context
    context['datasets'][params.output_key] = TableData.from_dataframe(df)
    context['metadata'][params.output_key] = {
        'source_file': params.file_path,
        'row_count': len(df),
        'identifier_column': params.identifier_column,
        'columns': list(df.columns),
        'filtered': params.filter_column is not None,
        'prefix_stripped': params.strip_prefix is not None
    }
```

## Examples

### 1. UKBB (Simple case)
```yaml
params:
  file_path: "/data/ukbb/UKBB_Protein_Meta.tsv"
  identifier_column: "UniProt"
  output_key: "ukbb_raw"
```

Result:
- Loads TSV file
- No changes to data
- Ready for downstream use

### 2. HPA (Different column name)
```yaml
params:
  file_path: "/data/hpa/hpa_osps.csv"
  identifier_column: "uniprot"  # lowercase!
  output_key: "hpa_raw"
```

### 3. KG2C (Complex case)
```yaml
params:
  file_path: "/data/kg2c/kg2c_proteins.csv"
  identifier_column: "id"
  strip_prefix: "UniProtKB:"
  filter_column: "id"
  filter_values: ["^UniProtKB:"]
  output_key: "kg2c_raw"
```

Result:
- Filters to ~85K UniProtKB entries
- Creates "id" with clean values: "P12345"
- Creates "id_original" with original: "UniProtKB:P12345"
- Other rows (UMLS:, PR:, etc.) excluded

### 4. SPOKE (No changes needed)
```yaml
params:
  file_path: "/data/spoke/spoke_proteins.csv"
  identifier_column: "identifier"
  output_key: "spoke_raw"
```

## Output Structure

```python
context['datasets'][output_key] = TableData with columns:
  - All original columns
  - "{identifier_column}_original" (if prefix stripped)
  - "_source_file"
  - "_row_number"

context['metadata'][output_key] = {
    'source_file': str,
    'row_count': int,
    'identifier_column': str,
    'columns': List[str],
    'filtered': bool,
    'prefix_stripped': bool
}
```

## Key Benefits

1. **Predictable** - Users know exactly what columns exist
2. **Traceable** - Can always see original vs cleaned data
3. **Simple** - No complex composite handling
4. **Flexible** - Handles all our protein data sources
5. **Downstream-friendly** - Clean identifiers in expected column names