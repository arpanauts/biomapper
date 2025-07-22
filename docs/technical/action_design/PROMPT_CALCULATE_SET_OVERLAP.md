# Development Prompt: CALCULATE_SET_OVERLAP Action

## Overview
Please implement the CALCULATE_SET_OVERLAP action for the Biomapper project following Test-Driven Development (TDD) practices.

**Reference the general guidelines in**: `/home/ubuntu/biomapper/MVP_DEVELOPER_REFERENCE.md`

## Action Purpose
Analyze overlap statistics from merged datasets with match metadata and create comprehensive output packages including:
1. Standardized statistics CSV with mapping_combo_id
2. Match type breakdown analysis
3. SVG and PNG Venn diagrams
4. Complete merged dataset export

This action creates publication-ready outputs and enables cross-mapping analysis.

## Specifications

### Parameters (Pydantic Model)
```python
class CalculateSetOverlapParams(BaseModel):
    # Input
    input_key: str = Field(..., description="Merged dataset with match metadata")
    
    # Dataset identification
    source_name: str = Field(..., description="Source dataset name (e.g., 'UKBB')")
    target_name: str = Field(..., description="Target dataset name (e.g., 'HPA')")
    mapping_combo_id: str = Field(..., description="Unique mapping identifier (e.g., 'UKBB_HPA')")
    
    # Analysis configuration
    confidence_threshold: float = Field(0.8, description="Minimum confidence for 'high quality' stats")
    
    # Output
    output_dir: str = Field("results", description="Base output directory")
    output_key: str = Field(..., description="Context key for statistics")
```

### Expected Input Data Structure
The input dataset should come from MERGE_WITH_UNIPROT_RESOLUTION with these columns:
- `match_value`: The actual ID that matched
- `match_type`: 'direct', 'composite', 'historical', or None
- `match_confidence`: Confidence score (0.0 to 1.0)
- `match_status`: 'matched', 'source_only', 'target_only'
- `api_resolved`: Boolean indicating if API was used
- All original columns from both datasets

### Processing Logic

#### 1. Analyze Match Metadata
```python
# Get merged dataset
merged_df = context['datasets'][input_key].to_dataframe()

# Core statistics
total_rows = len(merged_df)
matched_rows = len(merged_df[merged_df['match_status'] == 'matched'])
source_only_rows = len(merged_df[merged_df['match_status'] == 'source_only'])
target_only_rows = len(merged_df[merged_df['match_status'] == 'target_only'])

# Match type breakdown
direct_matches = len(merged_df[merged_df['match_type'] == 'direct'])
composite_matches = len(merged_df[merged_df['match_type'] == 'composite'])
historical_matches = len(merged_df[merged_df['match_type'] == 'historical'])

# Quality metrics
high_conf_matches = len(merged_df[
    (merged_df['match_confidence'] >= confidence_threshold) & 
    (merged_df['match_status'] == 'matched')
])
```

#### 2. Calculate Statistics
```python
# Perspective-based statistics
source_total = source_only_rows + matched_rows
source_match_rate = matched_rows / source_total if source_total > 0 else 0

target_total = target_only_rows + matched_rows
target_match_rate = matched_rows / target_total if target_total > 0 else 0

# Set theory statistics
union_total = source_only_rows + target_only_rows + matched_rows
jaccard_index = matched_rows / union_total if union_total > 0 else 0
dice_coefficient = (2 * matched_rows) / (source_total + target_total) if (source_total + target_total) > 0 else 0
```

#### 3. Generate 5 Output Files
```python
# Create output directory
output_path = f"{output_dir}/{mapping_combo_id}"
os.makedirs(output_path, exist_ok=True)

# 1. Main statistics CSV
# 2. Match type breakdown CSV
# 3. Venn diagram SVG
# 4. Venn diagram PNG
# 5. Complete merged dataset CSV
```

### Critical Output Requirements

#### 1. Statistics CSV Structure
Must include these exact columns for cross-mapping analysis:
```csv
mapping_combo_id,source_name,target_name,analysis_timestamp,total_rows,matched_rows,source_only_rows,target_only_rows,direct_matches,composite_matches,historical_matches,source_match_rate,target_match_rate,jaccard_index,dice_coefficient,avg_match_confidence,high_confidence_matches,confidence_threshold
```

#### 2. Venn Diagram Requirements
```python
from matplotlib_venn import venn2
import matplotlib.pyplot as plt

# Create professional-looking Venn diagram
fig, ax = plt.subplots(figsize=(10, 8))
venn = venn2(
    subsets=(source_only_rows, target_only_rows, matched_rows),
    set_labels=(source_name, target_name),
    ax=ax
)

# Add title with key statistics
plt.title(f'{mapping_combo_id} Protein Mapping Overlap\n'
          f'Jaccard Index: {jaccard_index:.3f} | '
          f'Total Matches: {matched_rows:,}')

# Save both formats
plt.savefig(f'{output_path}/venn_diagram.svg', format='svg', dpi=300, bbox_inches='tight')
plt.savefig(f'{output_path}/venn_diagram.png', format='png', dpi=300, bbox_inches='tight')
plt.close()
```

#### 3. Directory Structure
Each mapping creates:
```
results/
└── [mapping_combo_id]/
    ├── overlap_statistics.csv
    ├── match_type_breakdown.csv
    ├── venn_diagram.svg
    ├── venn_diagram.png
    └── merged_dataset.csv
```

## Test Cases to Implement

### 1. Parameter Validation Tests
```python
def test_params_validation():
    """Test parameter validation."""
    # Valid parameters
    params = CalculateSetOverlapParams(
        input_key="merged_data",
        source_name="UKBB",
        target_name="HPA",
        mapping_combo_id="UKBB_HPA",
        output_key="overlap_stats"
    )
    
    # Missing required parameters
    with pytest.raises(ValidationError):
        CalculateSetOverlapParams()
```

### 2. Statistics Calculation Tests
```python
def test_basic_statistics():
    """Test basic overlap statistics calculation."""
    # Mock merged dataset with match metadata
    merged_data = TableData(rows=[
        {'match_status': 'matched', 'match_type': 'direct', 'match_confidence': 1.0},
        {'match_status': 'matched', 'match_type': 'composite', 'match_confidence': 1.0},
        {'match_status': 'source_only', 'match_type': None, 'match_confidence': None},
        {'match_status': 'target_only', 'match_type': None, 'match_confidence': None}
    ])
    
    # Verify statistics calculations
    assert context['statistics']['test']['matched_rows'] == 2
    assert context['statistics']['test']['source_only_rows'] == 1
    assert context['statistics']['test']['jaccard_index'] == 0.5  # 2/(2+1+1)

def test_match_type_breakdown():
    """Test match type statistics."""
    # Verify direct, composite, historical counts
    
def test_confidence_thresholds():
    """Test high confidence filtering."""
    # Test with various confidence thresholds
```

### 3. Output Generation Tests
```python
def test_output_files_created():
    """Test that all 5 output files are created."""
    # After execution, verify files exist:
    # - overlap_statistics.csv
    # - match_type_breakdown.csv
    # - venn_diagram.svg
    # - venn_diagram.png
    # - merged_dataset.csv
    
def test_statistics_csv_format():
    """Test statistics CSV has correct columns."""
    # Verify exact column names and data types
    
def test_venn_diagram_generation():
    """Test Venn diagram creation."""
    # Verify SVG and PNG files are created
    # Check file sizes > 0
```

### 4. Real Data Integration Tests
```python
def test_with_real_merged_data():
    """Test with realistic merged dataset."""
    # Create mock data that resembles MERGE_WITH_UNIPROT_RESOLUTION output
    # Test with various match types and confidence scores
```

### 5. Edge Cases
```python
def test_empty_merged_dataset():
    """Test with empty input dataset."""
    
def test_no_matches():
    """Test when no matches exist."""
    # All rows are source_only or target_only
    
def test_perfect_overlap():
    """Test when all rows match."""
    # All rows have match_status='matched'
    
def test_missing_match_columns():
    """Test error handling when required columns missing."""
    # Should raise clear error about missing match_type, match_status, etc.
```

## Context Output

### Statistics Storage
```python
context['statistics'][output_key] = {
    'mapping_combo_id': mapping_combo_id,
    'source_name': source_name,
    'target_name': target_name,
    'analysis_timestamp': datetime.now().isoformat(),
    'total_rows': int,
    'matched_rows': int,
    'source_only_rows': int,
    'target_only_rows': int,
    'direct_matches': int,
    'composite_matches': int,
    'historical_matches': int,
    'source_match_rate': float,
    'target_match_rate': float,
    'jaccard_index': float,
    'dice_coefficient': float,
    'avg_match_confidence': float,
    'high_confidence_matches': int,
    'confidence_threshold': float
}
```

### File Paths Storage
```python
context['output_files'][f"{output_key}_statistics"] = f"{output_path}/overlap_statistics.csv"
context['output_files'][f"{output_key}_breakdown"] = f"{output_path}/match_type_breakdown.csv"
context['output_files'][f"{output_key}_venn_svg"] = f"{output_path}/venn_diagram.svg"
context['output_files'][f"{output_key}_venn_png"] = f"{output_path}/venn_diagram.png"
context['output_files'][f"{output_key}_merged_data"] = f"{output_path}/merged_dataset.csv"
```

## Dependencies

Add these to your test requirements:
```python
# For Venn diagrams
matplotlib>=3.7.0
matplotlib-venn>=0.11.9

# For data processing
pandas>=2.0.0
numpy>=1.24.0
```

## Example Usage in YAML

```yaml
- name: analyze_overlap
  action:
    type: CALCULATE_SET_OVERLAP
    params:
      input_key: "ukbb_hpa_merged"
      source_name: "UKBB"
      target_name: "HPA"
      mapping_combo_id: "UKBB_HPA"
      confidence_threshold: 0.8
      output_dir: "results"
      output_key: "overlap_analysis"
```

## Success Criteria

1. **All tests pass** with >80% coverage
2. **All 5 output files generated** consistently
3. **Professional Venn diagrams** with proper labels and statistics
4. **Standardized CSV format** for cross-mapping analysis
5. **Complete data preservation** in merged dataset export
6. **Memory efficient** - handles large merged datasets
7. **Error handling** for missing columns or invalid data

## Implementation Notes

1. **Matplotlib configuration**: Use `plt.style.use('seaborn-v0_8')` for professional plots
2. **File permissions**: Ensure output directory is writable
3. **Memory management**: Process large datasets in chunks if needed
4. **Error messages**: Include mapping_combo_id in error messages for debugging
5. **Progress logging**: Log file creation and statistics calculation

## Key Design Decisions

1. **Output standardization**: All mappings produce identical file structure
2. **Visual quality**: High-DPI outputs for publication use
3. **Cross-mapping ready**: mapping_combo_id enables aggregation
4. **Complete preservation**: Full merged dataset always exported
5. **Quality tracking**: Confidence thresholds and metrics included

Start with the failing tests focusing on the 5 output files and statistics calculations!