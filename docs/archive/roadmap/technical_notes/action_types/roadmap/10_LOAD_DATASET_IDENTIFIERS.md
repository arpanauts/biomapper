# LOAD_DATASET_IDENTIFIERS Action Type

## Overview

`LOAD_DATASET_IDENTIFIERS` is a generic data loader that works across all entity types and file formats. It builds on the STREAMING_DATA_PROCESSOR foundation to provide entity-agnostic identifier loading with intelligent column mapping and data transformation.

### Purpose
- Load identifiers from CSV/TSV files for any entity type
- Support flexible column mapping configurations
- Handle composite identifiers and cross-references
- Provide data validation and cleaning
- Enable streaming for large datasets

### Use Cases
- Load protein IDs from UKBB or HPA datasets
- Extract metabolite identifiers with cross-references
- Load clinical lab test codes
- Parse gene lists with multiple ID types
- Process any tabular biological data

## Design Decisions

### True Generalization Approach
Instead of hardcoding entity-specific logic, this action leverages the foundation architecture:
1. **Parser Plugin Architecture**: Uses configurable parsers for identifier types (see [03_PARSER_PLUGIN_ARCHITECTURE.md](./03_PARSER_PLUGIN_ARCHITECTURE.md))
2. **Configuration-Driven Normalization**: Applies YAML-based transformation rules (see [04_CONFIGURATION_DRIVEN_NORMALIZATION.md](./04_CONFIGURATION_DRIVEN_NORMALIZATION.md))
3. **Streaming Infrastructure**: Memory-efficient processing for large files (see [06_STREAMING_INFRASTRUCTURE.md](./06_STREAMING_INFRASTRUCTURE.md))
4. **Flexible Column Mapping**: Users specify which columns contain what type of identifiers
5. **Metadata Preservation**: Keep all columns for downstream use

## Implementation Details

### Parameter Model
```python
class ColumnMapping(BaseModel):
    """Maps columns to identifier types."""
    column_name: str
    identifier_type: str  # e.g., "uniprot_ac", "hmdb_id", "gene_symbol"
    is_primary: bool = False
    is_composite: bool = False  # If values like "P12345,P67890"
    composite_separator: str = ","
    
class LoadDatasetIdentifiersParams(BaseModel):
    """Parameters for loading dataset identifiers."""
    
    # Input configuration
    file_path: Path = Field(..., description="Path to dataset file")
    file_format: Literal['csv', 'tsv', 'auto'] = Field(default='auto')
    encoding: str = Field(default='utf-8')
    
    # Column configuration
    column_mappings: List[ColumnMapping] = Field(
        ...,
        description="How to interpret each column"
    )
    metadata_columns: Optional[List[str]] = Field(
        default=None,
        description="Additional columns to preserve as metadata"
    )
    
    # Data handling
    skip_header_rows: int = Field(default=0)
    skip_empty_primary: bool = Field(default=True)
    unique_only: bool = Field(default=False)
    lowercase_ids: bool = Field(default=False)
    strip_whitespace: bool = Field(default=True)
    
    # Streaming configuration (inherited from STREAMING_DATA_PROCESSOR)
    use_streaming: bool = Field(default=True)
    chunk_size: int = Field(default=5000)
    memory_limit_mb: int = Field(default=500)
    
    # Validation
    validate_format: bool = Field(default=True)
    entity_type: Optional[str] = Field(
        default=None,
        description="Entity type for validation (if None, skip validation)"
    )
    
    # Output configuration
    output_context_key: str = Field(..., description="Where to store results")
    output_format: Literal['list', 'dict', 'dataframe'] = Field(default='dict')
```

### Result Model
```python
class LoadDatasetIdentifiersResult(ActionResult):
    """Result from loading dataset identifiers."""
    
    # Summary statistics
    total_rows_processed: int
    unique_primary_ids: int
    total_identifiers_extracted: int
    identifier_type_counts: Dict[str, int]
    
    # Data quality
    rows_skipped_empty: int
    rows_with_composite_ids: int
    validation_failures: int
    
    # Metadata
    detected_columns: List[str]
    detected_delimiter: str
    file_encoding: str
    
    # Streaming info
    chunks_processed: int
    peak_memory_mb: float
    processing_time_s: float
```

### Core Implementation
```python
class LoadDatasetIdentifiers(GeneralizedAction[LoadDatasetIdentifiersParams, LoadDatasetIdentifiersResult]):
    """Generic dataset identifier loader."""
    
    async def execute_typed(
        self,
        params: LoadDatasetIdentifiersParams,
        context: ExecutionContext
    ) -> LoadDatasetIdentifiersResult:
        """Load identifiers from dataset file."""
        
        # Initialize components
        validator = self._get_validator(params.entity_type) if params.validate_format else None
        results = IdentifierCollection()
        
        # Use streaming for large files
        if params.use_streaming:
            processor = StreamingDataProcessor()
            stream_params = StreamingDataProcessorParams(
                file_path=params.file_path,
                file_format=params.file_format,
                chunk_size=params.chunk_size,
                memory_limit_mb=params.memory_limit_mb,
                skip_rows=params.skip_header_rows,
                columns=self._get_required_columns(params)
            )
            
            async for chunk in processor.stream_execute(stream_params, context):
                await self._process_chunk(chunk.data, params, results, validator)
        else:
            # Load entire file for small datasets
            data = await self._load_file(params)
            await self._process_chunk(data, params, results, validator)
        
        # Store results in context
        context[params.output_context_key] = self._format_output(
            results, params.output_format
        )
        
        return LoadDatasetIdentifiersResult(
            status='success',
            total_rows_processed=results.total_rows,
            unique_primary_ids=len(results.primary_ids),
            total_identifiers_extracted=results.total_identifiers,
            identifier_type_counts=results.type_counts,
            rows_skipped_empty=results.skipped_empty,
            rows_with_composite_ids=results.composite_count,
            validation_failures=results.validation_failures,
            processed_count=results.total_rows,
            error_count=results.validation_failures
        )
    
    async def _process_chunk(
        self,
        data: List[Dict],
        params: LoadDatasetIdentifiersParams,
        results: IdentifierCollection,
        validator: Optional[EntityValidator]
    ):
        """Process a chunk of data."""
        
        for row in data:
            # Clean data
            if params.strip_whitespace:
                row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
            
            # Extract identifiers based on column mappings
            row_identifiers = {}
            primary_id = None
            
            for mapping in params.column_mappings:
                value = row.get(mapping.column_name)
                if not value:
                    continue
                
                # Handle composite identifiers
                if mapping.is_composite and mapping.composite_separator in str(value):
                    ids = [id.strip() for id in str(value).split(mapping.composite_separator)]
                    results.composite_count += 1
                else:
                    ids = [str(value)]
                
                # Process each identifier
                processed_ids = []
                for id_value in ids:
                    # Transform
                    if params.lowercase_ids:
                        id_value = id_value.lower()
                    
                    # Validate
                    if validator and params.validate_format:
                        if not validator.validate(id_value, mapping.identifier_type):
                            results.validation_failures += 1
                            continue
                    
                    processed_ids.append(id_value)
                
                # Store
                row_identifiers[mapping.identifier_type] = processed_ids
                if mapping.is_primary and processed_ids:
                    primary_id = processed_ids[0]
            
            # Skip if no primary ID
            if params.skip_empty_primary and not primary_id:
                results.skipped_empty += 1
                continue
            
            # Store results
            results.add_row(
                primary_id=primary_id,
                identifiers=row_identifiers,
                metadata={k: v for k, v in row.items() 
                         if k in (params.metadata_columns or [])}
            )
```

## Error Scenarios

### Common Issues
1. **Missing Columns**: Clear error with available columns
2. **Format Mismatch**: Auto-detection with fallback
3. **Invalid Identifiers**: Validation errors with context
4. **Encoding Problems**: Try multiple encodings
5. **Memory Limits**: Automatic streaming activation

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_load_protein_identifiers():
    """Test loading protein identifiers from UKBB-style data."""
    # Create test data
    test_data = """Assay,UniProt,Panel,Description
    AARSD1,Q9BTE6,Oncology,Some description
    ABL1,P00519,Oncology,Another description
    INVALID,,Neurology,Missing UniProt
    MULTI,"P12345,P67890",Cardio,Composite ID
    """
    
    loader = LoadDatasetIdentifiers()
    result = await loader.execute_typed(
        params=LoadDatasetIdentifiersParams(
            file_path="test.csv",
            column_mappings=[
                ColumnMapping(
                    column_name="UniProt",
                    identifier_type="uniprot_ac",
                    is_primary=True,
                    is_composite=True
                ),
                ColumnMapping(
                    column_name="Assay",
                    identifier_type="assay_name"
                )
            ],
            metadata_columns=["Panel", "Description"],
            entity_type="protein",
            output_context_key="ukbb_proteins"
        ),
        context={}
    )
    
    assert result.total_rows_processed == 4
    assert result.unique_primary_ids == 3  # One skipped
    assert result.rows_with_composite_ids == 1
    assert result.identifier_type_counts["uniprot_ac"] == 4  # Including split composite

@pytest.mark.asyncio
async def test_load_metabolite_cross_references():
    """Test loading metabolites with complex cross-references."""
    # Test with metabolite data containing xrefs
    # Verify cross-reference parsing
    pass
```

## Examples

### Basic Protein Loading
```yaml
- action:
    type: LOAD_DATASET_IDENTIFIERS
    params:
      file_path: "${DATA_DIR}/ukbb_proteins.csv"
      column_mappings:
        - column_name: "UniProt"
          identifier_type: "uniprot_ac"
          is_primary: true
        - column_name: "Assay"
          identifier_type: "assay_name"
      metadata_columns: ["Panel"]
      entity_type: "protein"
      output_context_key: "ukbb_proteins"
```

### Complex Metabolite Loading
```yaml
- action:
    type: LOAD_DATASET_IDENTIFIERS
    params:
      file_path: "${DATA_DIR}/metabolomics_metadata.tsv"
      file_format: "tsv"
      skip_header_rows: 13  # Arivale headers
      column_mappings:
        - column_name: "name"
          identifier_type: "metabolite_name"
          is_primary: true
        - column_name: "hmdb_id"
          identifier_type: "hmdb"
        - column_name: "kegg_id"
          identifier_type: "kegg_compound"
          is_composite: true
          composite_separator: ";"
      validate_format: true
      entity_type: "metabolite"
      use_streaming: true
      chunk_size: 10000
      output_context_key: "arivale_metabolites"
```

### Gene List with Multiple ID Types
```yaml
- action:
    type: LOAD_DATASET_IDENTIFIERS
    params:
      file_path: "${DATA_DIR}/gene_list.csv"
      column_mappings:
        - column_name: "ensembl_gene_id"
          identifier_type: "ensembl_gene"
          is_primary: true
        - column_name: "gene_symbol"
          identifier_type: "gene_symbol"
        - column_name: "entrez_gene_id"
          identifier_type: "entrez_gene"
      unique_only: true
      output_format: "dict"
      output_context_key: "gene_identifiers"
```

## Integration Notes

### Combines With
- **PARSE_COMPOSITE_IDENTIFIERS**: Further process composite IDs
- **VALIDATE_IDENTIFIER_FORMAT**: Additional validation
- **CALCULATE_SET_OVERLAP**: Compare loaded datasets
- **EXTRACT_CROSS_REFERENCES**: Parse xref columns

### Output Formats
```python
# List format (simple)
["P12345", "Q67890", "P11111"]

# Dict format (with metadata)
{
    "P12345": {
        "identifiers": {"uniprot_ac": "P12345", "assay_name": "AARSD1"},
        "metadata": {"panel": "Oncology", "description": "..."}
    }
}

# DataFrame format (for analysis)
# Returns pandas DataFrame with all data
```

## Performance Considerations

1. **Streaming Threshold**: Use streaming for files >100MB
2. **Chunk Size**: 5000-10000 rows optimal for most cases
3. **Column Selection**: Only load needed columns
4. **Validation Cost**: Disable validation for trusted sources
5. **Memory Usage**: ~50 bytes per identifier + metadata