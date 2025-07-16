# GENERATE_MAPPING_REPORT Action Type

## Overview

`GENERATE_MAPPING_REPORT` creates standardized output reports showing the complete mapping between source and target datasets. It produces a comprehensive "outer join" view that includes all entities from both datasets, clearly showing what mapped, what didn't, and why.

### Purpose
- Generate standardized CSV/TSV reports of mapping results
- Show full outer join of source and target metadata
- Include mapping confidence and methods used
- Provide summary statistics
- Support multiple output formats

### Use Cases
- Final output for UKBB to HPA protein mapping
- Metabolite mapping reports with cross-references
- Gene mapping results with multiple ID types
- Clinical lab test harmonization reports
- Any entity mapping requiring detailed documentation

## Design Decisions

### Report Structure
1. **Outer Join Format**: Include all rows from both source and target
2. **Metadata Preservation**: Keep all original columns from both datasets
3. **Mapping Details**: Add columns for confidence, method, timestamp
4. **Cross-Reference Paths**: Show path discovered via graph resolver (see [05_GRAPH_CROSS_REFERENCE_RESOLVER.md](./05_GRAPH_CROSS_REFERENCE_RESOLVER.md))
5. **Streaming Output**: Use streaming infrastructure for large reports (see [06_STREAMING_INFRASTRUCTURE.md](./06_STREAMING_INFRASTRUCTURE.md))
6. **Multiple Formats**: Support CSV, TSV, Excel, JSON outputs

## Implementation Details

### Parameter Model
```python
class ColumnSelection(BaseModel):
    """Columns to include from a dataset."""
    include_all: bool = Field(default=False)
    columns: Optional[List[str]] = Field(None)
    exclude: Optional[List[str]] = Field(None)
    rename: Optional[Dict[str, str]] = Field(None)

class ReportSection(str, Enum):
    """Sections to include in report."""
    SUMMARY = "summary"
    MAPPED_PAIRS = "mapped_pairs"
    SOURCE_ONLY = "source_only"
    TARGET_ONLY = "target_only"
    FAILED_MAPPINGS = "failed_mappings"
    CONFIDENCE_DISTRIBUTION = "confidence_distribution"

class GenerateMappingReportParams(BaseModel):
    """Parameters for generating mapping reports."""
    
    # Input data sources
    source_data_key: str = Field(..., description="Context key for source dataset")
    target_data_key: str = Field(..., description="Context key for target dataset")
    mapping_results_key: str = Field(..., description="Context key for mapping results")
    
    # Column configuration
    source_columns: ColumnSelection = Field(default_factory=lambda: ColumnSelection(include_all=True))
    target_columns: ColumnSelection = Field(default_factory=lambda: ColumnSelection(include_all=True))
    
    # Report configuration
    report_name: str = Field(..., description="Base name for report files")
    sections: List[ReportSection] = Field(
        default=[ReportSection.SUMMARY, ReportSection.MAPPED_PAIRS, 
                 ReportSection.SOURCE_ONLY, ReportSection.TARGET_ONLY]
    )
    
    # Mapping details to include
    include_confidence: bool = Field(default=True)
    include_mapping_method: bool = Field(default=True)
    include_timestamp: bool = Field(default=True)
    include_provenance: bool = Field(default=False)
    
    # Output configuration
    output_format: Literal['csv', 'tsv', 'excel', 'json'] = Field(default='csv')
    output_dir: str = Field(default="${OUTPUT_DIR}")
    create_separate_files: bool = Field(default=False, description="One file per section")
    
    # Formatting options
    delimiter: Optional[str] = Field(None, description="Override default delimiter")
    include_header: bool = Field(default=True)
    sort_by: Optional[List[str]] = Field(None, description="Columns to sort by")
    
    # Summary configuration
    include_summary_stats: bool = Field(default=True)
    summary_format: Literal['inline', 'separate', 'both'] = Field(default='inline')
    
    # Error handling
    include_error_details: bool = Field(default=True)
    max_error_examples: int = Field(default=100)
```

### Result Model
```python
class MappingSummaryStats(BaseModel):
    """Summary statistics for the mapping."""
    source_total: int
    target_total: int
    mapped_count: int
    source_coverage: float  # Percentage of source that mapped
    target_coverage: float  # Percentage of target that mapped
    one_to_one_count: int
    one_to_many_count: int
    many_to_one_count: int
    confidence_distribution: Dict[str, int]
    mapping_methods_used: Dict[str, int]

class GenerateMappingReportResult(ActionResult):
    """Result from generating mapping report."""
    
    # File information
    report_files: List[str]  # Paths to generated files
    primary_report_path: str
    
    # Summary statistics
    summary_stats: MappingSummaryStats
    
    # Section row counts
    section_counts: Dict[str, int]
    
    # Output details
    total_rows_written: int
    file_size_bytes: int
    generation_time_ms: float
```

### Core Implementation
```python
class GenerateMappingReport(TypedStrategyAction[GenerateMappingReportParams, GenerateMappingReportResult]):
    """Generate comprehensive mapping reports."""
    
    def get_params_model(self) -> type[GenerateMappingReportParams]:
        return GenerateMappingReportParams
    
    async def execute_typed(
        self,
        params: GenerateMappingReportParams,
        context: ExecutionContext,
        executor: MappingExecutor
    ) -> GenerateMappingReportResult:
        """Generate mapping report."""
        
        # Load input data
        source_data = self._load_as_dataframe(context.get(params.source_data_key))
        target_data = self._load_as_dataframe(context.get(params.target_data_key))
        mapping_results = context.get(params.mapping_results_key)
        
        # Process column selections
        source_cols = self._select_columns(source_data, params.source_columns, prefix='source_')
        target_cols = self._select_columns(target_data, params.target_columns, prefix='target_')
        
        # Create mapping dataframe
        mapping_df = self._create_mapping_dataframe(mapping_results)
        
        # Perform outer join
        report_df = self._create_outer_join_report(
            source_data[source_cols],
            target_data[target_cols],
            mapping_df,
            params
        )
        
        # Add mapping details columns
        if params.include_confidence:
            report_df['mapping_confidence'] = report_df['mapping_id'].map(
                lambda x: mapping_results.get(x, {}).get('confidence', None)
            )
        
        if params.include_mapping_method:
            report_df['mapping_method'] = report_df['mapping_id'].map(
                lambda x: mapping_results.get(x, {}).get('method', None)
            )
        
        if params.include_timestamp:
            report_df['mapping_timestamp'] = datetime.utcnow().isoformat()
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(
            source_data, target_data, mapping_df, report_df
        )
        
        # Generate report sections
        report_files = []
        section_counts = {}
        
        # Resolve output directory
        output_dir = os.path.expandvars(params.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate each section
        for section in params.sections:
            section_df = self._filter_section(report_df, section)
            section_counts[section.value] = len(section_df)
            
            if params.create_separate_files:
                file_path = self._write_section(
                    section_df, section, params, output_dir, summary_stats
                )
                report_files.append(file_path)
            else:
                # Will be included in main file
                pass
        
        # Write main report
        if not params.create_separate_files:
            main_path = self._write_complete_report(
                report_df, params, output_dir, summary_stats
            )
            report_files.append(main_path)
        else:
            main_path = report_files[0]  # First section file
        
        # Store report path in context
        context[f"{params.mapping_results_key}_report"] = main_path
        
        return GenerateMappingReportResult(
            status='success',
            processed_count=len(report_df),
            error_count=0,
            report_files=report_files,
            primary_report_path=main_path,
            summary_stats=summary_stats,
            section_counts=section_counts,
            total_rows_written=len(report_df),
            file_size_bytes=os.path.getsize(main_path),
            generation_time_ms=0  # TODO: Implement timing
        )
    
    def _create_outer_join_report(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        mapping_df: pd.DataFrame,
        params: GenerateMappingReportParams
    ) -> pd.DataFrame:
        """Create outer join report with all mapping information."""
        
        # Add temporary join keys
        source_df = source_df.copy()
        target_df = target_df.copy()
        
        # Perform outer joins
        # First: source LEFT JOIN mappings
        source_with_mappings = source_df.merge(
            mapping_df,
            left_on='source_id',  # Adjust based on actual ID column
            right_on='source_id',
            how='left',
            suffixes=('', '_mapping')
        )
        
        # Second: above FULL OUTER JOIN target
        full_report = source_with_mappings.merge(
            target_df,
            left_on='target_id',  # From mapping
            right_on='target_id',  # Adjust based on actual ID column
            how='outer',
            suffixes=('_source', '_target'),
            indicator=True
        )
        
        # Add mapping status column
        full_report['mapping_status'] = full_report['_merge'].map({
            'left_only': 'source_only',
            'right_only': 'target_only',
            'both': 'mapped'
        })
        
        # Clean up temporary columns
        full_report = full_report.drop(columns=['_merge'])
        
        # Sort if requested
        if params.sort_by:
            full_report = full_report.sort_values(params.sort_by)
        
        return full_report
    
    def _write_complete_report(
        self,
        report_df: pd.DataFrame,
        params: GenerateMappingReportParams,
        output_dir: str,
        summary_stats: MappingSummaryStats
    ) -> str:
        """Write complete report to file."""
        
        file_name = f"{params.report_name}.{params.output_format}"
        file_path = os.path.join(output_dir, file_name)
        
        if params.output_format == 'csv':
            # Add summary as comments if inline
            if params.include_summary_stats and params.summary_format in ['inline', 'both']:
                with open(file_path, 'w') as f:
                    # Write summary as comments
                    f.write(f"# Mapping Report: {params.report_name}\n")
                    f.write(f"# Generated: {datetime.utcnow().isoformat()}\n")
                    f.write(f"# Source Total: {summary_stats.source_total}\n")
                    f.write(f"# Target Total: {summary_stats.target_total}\n")
                    f.write(f"# Mapped: {summary_stats.mapped_count}\n")
                    f.write(f"# Source Coverage: {summary_stats.source_coverage:.1f}%\n")
                    f.write(f"# Target Coverage: {summary_stats.target_coverage:.1f}%\n")
                    f.write("#\n")
                    
                    # Write data
                    report_df.to_csv(f, index=False)
            else:
                report_df.to_csv(file_path, index=False)
        
        elif params.output_format == 'tsv':
            report_df.to_csv(file_path, sep='\t', index=False)
        
        elif params.output_format == 'excel':
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                report_df.to_excel(writer, sheet_name='Mapping Results', index=False)
                if params.include_summary_stats:
                    summary_df = pd.DataFrame([summary_stats.dict()])
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        elif params.output_format == 'json':
            report_dict = {
                'summary': summary_stats.dict() if params.include_summary_stats else None,
                'mappings': report_df.to_dict(orient='records')
            }
            with open(file_path, 'w') as f:
                json.dump(report_dict, f, indent=2, default=str)
        
        return file_path
```

## Testing Strategy

```python
@pytest.mark.asyncio
async def test_basic_mapping_report():
    """Test basic report generation."""
    action = GenerateMappingReport()
    
    context = {
        'source_data': [
            {'id': 'S1', 'name': 'Source 1', 'value': 100},
            {'id': 'S2', 'name': 'Source 2', 'value': 200},
            {'id': 'S3', 'name': 'Source 3', 'value': 300}
        ],
        'target_data': [
            {'id': 'T1', 'desc': 'Target 1'},
            {'id': 'T2', 'desc': 'Target 2'},
            {'id': 'T4', 'desc': 'Target 4'}
        ],
        'mapping_results': {
            'S1': {'target': 'T1', 'confidence': 0.95, 'method': 'exact'},
            'S2': {'target': 'T2', 'confidence': 0.80, 'method': 'fuzzy'}
            # S3 unmapped, T4 unmapped
        }
    }
    
    with TemporaryDirectory() as tmpdir:
        result = await action.execute_typed(
            params=GenerateMappingReportParams(
                source_data_key='source_data',
                target_data_key='target_data',
                mapping_results_key='mapping_results',
                report_name='test_mapping',
                output_dir=tmpdir
            ),
            context=context,
            executor=mock_executor
        )
        
        assert result.summary_stats.source_total == 3
        assert result.summary_stats.target_total == 3
        assert result.summary_stats.mapped_count == 2
        assert result.summary_stats.source_coverage == pytest.approx(66.7, 0.1)
        
        # Check file was created
        assert os.path.exists(result.primary_report_path)
```

## Examples

### Basic Protein Mapping Report
```yaml
- action:
    type: GENERATE_MAPPING_REPORT
    params:
      source_data_key: "ukbb_proteins"
      target_data_key: "hpa_proteins"
      mapping_results_key: "ukbb_hpa_mappings"
      report_name: "ukbb_to_hpa_protein_mapping"
      output_format: "csv"
      include_confidence: true
      include_mapping_method: true
```

### Detailed Metabolite Report with Sections
```yaml
- action:
    type: GENERATE_MAPPING_REPORT
    params:
      source_data_key: "arivale_metabolites"
      target_data_key: "hmdb_metabolites"
      mapping_results_key: "metabolite_mappings"
      report_name: "arivale_hmdb_mapping"
      sections:
        - "summary"
        - "mapped_pairs"
        - "source_only"
        - "target_only"
        - "confidence_distribution"
      create_separate_files: true
      output_format: "excel"
      source_columns:
        columns: ["name", "hmdb_id", "kegg_id", "pubchem_id"]
      target_columns:
        columns: ["accession", "name", "chemical_formula", "monoisotopic_mass"]
```

### Clinical Lab Test Harmonization Report
```yaml
- action:
    type: GENERATE_MAPPING_REPORT
    params:
      source_data_key: "local_lab_tests"
      target_data_key: "loinc_codes"
      mapping_results_key: "lab_harmonization"
      report_name: "lab_test_loinc_mapping"
      output_format: "tsv"
      sort_by: ["source_test_name", "mapping_confidence"]
      include_error_details: true
      summary_format: "both"  # Inline and separate file
```

## Integration Notes

### Typically Follows
- All mapping actions that produce results
- `CALCULATE_MAPPING_METRICS` - Include metrics in report
- `RANK_MAPPING_CANDIDATES` - Report best matches

### Output Usage
- Final deliverable for mapping pipelines
- Input for downstream analysis
- Documentation for mapping decisions
- Quality assurance reviews

## Performance Considerations

1. **Memory Usage**: Use chunking for very large reports
2. **File Format**: CSV fastest, Excel slowest
3. **Column Selection**: Only include needed columns
4. **Sorting**: Can be expensive for large datasets
5. **Summary Calculation**: Consider pre-computing for large data