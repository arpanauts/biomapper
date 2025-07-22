# Action 4: CALCULATE_SET_OVERLAP - Design

## Purpose
Analyze overlap statistics from merged dataset with match metadata, creating standardized outputs for cross-mapping analysis.

## Key Design Decisions
1. **Input**: Merged dataset from MERGE_WITH_UNIPROT_RESOLUTION (with match metadata)
2. **Output**: Standardized statistics CSV with mapping_combo_id for aggregation
3. **Location**: `results/[mapping_combo_id]/` for consistent organization
4. **Focus**: Venn diagram data and match type breakdowns

## Parameters

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

## Processing Logic

### 1. Analyze Match Metadata
```python
# Get merged dataset
merged_df = context['datasets'][input_key].to_dataframe()

# Calculate core statistics
total_rows = len(merged_df)
matched_rows = len(merged_df[merged_df['match_status'] == 'matched'])
source_only_rows = len(merged_df[merged_df['match_status'] == 'source_only'])
target_only_rows = len(merged_df[merged_df['match_status'] == 'target_only'])

# Match type breakdown
direct_matches = len(merged_df[merged_df['match_type'] == 'direct'])
composite_matches = len(merged_df[merged_df['match_type'] == 'composite'])
historical_matches = len(merged_df[merged_df['match_type'] == 'historical'])

# High confidence subset
high_conf_matches = len(merged_df[
    (merged_df['match_confidence'] >= confidence_threshold) & 
    (merged_df['match_status'] == 'matched')
])
```

### 2. Calculate Perspective-Based Statistics
```python
# From source dataset perspective
source_total = source_only_rows + matched_rows
source_match_rate = matched_rows / source_total if source_total > 0 else 0

# From target dataset perspective  
target_total = target_only_rows + matched_rows
target_match_rate = matched_rows / target_total if target_total > 0 else 0

# Overall union
union_total = source_only_rows + target_only_rows + matched_rows
jaccard_index = matched_rows / union_total if union_total > 0 else 0
```

### 3. Create Standardized Statistics
```python
statistics = {
    'mapping_combo_id': mapping_combo_id,
    'source_name': source_name,
    'target_name': target_name,
    'analysis_timestamp': datetime.now().isoformat(),
    
    # Core counts
    'total_rows': total_rows,
    'matched_rows': matched_rows,
    'source_only_rows': source_only_rows,
    'target_only_rows': target_only_rows,
    
    # Match type breakdown
    'direct_matches': direct_matches,
    'composite_matches': composite_matches,
    'historical_matches': historical_matches,
    'high_confidence_matches': high_conf_matches,
    
    # Perspective-based rates
    'source_total': source_total,
    'source_match_rate': source_match_rate,
    'target_total': target_total,
    'target_match_rate': target_match_rate,
    
    # Set theory statistics
    'union_total': union_total,
    'jaccard_index': jaccard_index,
    'dice_coefficient': (2 * matched_rows) / (source_total + target_total) if (source_total + target_total) > 0 else 0,
    
    # Venn diagram data
    'venn_source_only': source_only_rows,
    'venn_target_only': target_only_rows,
    'venn_intersection': matched_rows,
    
    # Quality metrics
    'avg_match_confidence': merged_df[merged_df['match_status'] == 'matched']['match_confidence'].mean(),
    'confidence_threshold': confidence_threshold,
    'high_conf_rate': high_conf_matches / matched_rows if matched_rows > 0 else 0
}
```

## Output Structure

### 1. Statistics CSV
**Location**: `results/[mapping_combo_id]/overlap_statistics.csv`
```csv
mapping_combo_id,source_name,target_name,analysis_timestamp,total_rows,matched_rows,source_only_rows,target_only_rows,direct_matches,composite_matches,historical_matches,source_match_rate,target_match_rate,jaccard_index,dice_coefficient,avg_match_confidence
UKBB_HPA,UKBB,HPA,2024-01-15T10:30:00,1245,485,760,0,445,35,5,0.389,0.485,0.389,0.556,0.94
```

### 2. Detailed Breakdown CSV
**Location**: `results/[mapping_combo_id]/match_type_breakdown.csv`
```csv
mapping_combo_id,match_type,count,percentage,avg_confidence
UKBB_HPA,direct,445,91.8,1.0
UKBB_HPA,composite,35,7.2,1.0
UKBB_HPA,historical,5,1.0,0.87
```

### 3. Venn Diagram Visualizations
**Location**: `results/[mapping_combo_id]/venn_diagram.svg` and `venn_diagram.png`

```python
# Create Venn diagram using matplotlib-venn
from matplotlib_venn import venn2
import matplotlib.pyplot as plt

# Create SVG version
fig, ax = plt.subplots(figsize=(10, 8))
venn = venn2(
    subsets=(source_only_rows, target_only_rows, matched_rows),
    set_labels=(source_name, target_name),
    ax=ax
)
plt.title(f'{mapping_combo_id} Protein Mapping Overlap')
plt.savefig(f'{output_dir}/{mapping_combo_id}/venn_diagram.svg', format='svg', dpi=300)
plt.savefig(f'{output_dir}/{mapping_combo_id}/venn_diagram.png', format='png', dpi=300)
plt.close()
```

### 4. Merged Dataset Output
**Location**: `results/[mapping_combo_id]/merged_dataset.csv`
- Complete merged dataset with all match metadata
- All original columns from both datasets
- Ready for further analysis or manual inspection

## Processing Logic (Updated)

### 4. Generate Outputs
```python
# Create output directory
output_path = f"{output_dir}/{mapping_combo_id}"
os.makedirs(output_path, exist_ok=True)

# 1. Statistics CSV
stats_df = pd.DataFrame([statistics])
stats_df.to_csv(f"{output_path}/overlap_statistics.csv", index=False)

# 2. Match type breakdown CSV
breakdown_data = [
    {'mapping_combo_id': mapping_combo_id, 'match_type': 'direct', 'count': direct_matches, 'percentage': direct_matches/matched_rows*100 if matched_rows > 0 else 0, 'avg_confidence': 1.0},
    {'mapping_combo_id': mapping_combo_id, 'match_type': 'composite', 'count': composite_matches, 'percentage': composite_matches/matched_rows*100 if matched_rows > 0 else 0, 'avg_confidence': 1.0},
    {'mapping_combo_id': mapping_combo_id, 'match_type': 'historical', 'count': historical_matches, 'percentage': historical_matches/matched_rows*100 if matched_rows > 0 else 0, 'avg_confidence': merged_df[merged_df['match_type'] == 'historical']['match_confidence'].mean()}
]
breakdown_df = pd.DataFrame(breakdown_data)
breakdown_df.to_csv(f"{output_path}/match_type_breakdown.csv", index=False)

# 3. Venn diagrams (SVG and PNG)
from matplotlib_venn import venn2
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 8))
venn = venn2(
    subsets=(source_only_rows, target_only_rows, matched_rows),
    set_labels=(source_name, target_name),
    ax=ax
)
plt.title(f'{mapping_combo_id} Protein Mapping Overlap\n'
          f'Jaccard Index: {jaccard_index:.3f}')
plt.savefig(f'{output_path}/venn_diagram.svg', format='svg', dpi=300, bbox_inches='tight')
plt.savefig(f'{output_path}/venn_diagram.png', format='png', dpi=300, bbox_inches='tight')
plt.close()

# 4. Full merged dataset
merged_df.to_csv(f"{output_path}/merged_dataset.csv", index=False)
```

## Context Updates

```python
# Store statistics in context for other actions
context['statistics'][output_key] = statistics

# Store file paths for downstream actions
context['output_files'][f"{output_key}_statistics"] = f"{output_path}/overlap_statistics.csv"
context['output_files'][f"{output_key}_breakdown"] = f"{output_path}/match_type_breakdown.csv"
context['output_files'][f"{output_key}_venn_svg"] = f"{output_path}/venn_diagram.svg"
context['output_files'][f"{output_key}_venn_png"] = f"{output_path}/venn_diagram.png"
context['output_files'][f"{output_key}_merged_data"] = f"{output_path}/merged_dataset.csv"

# Update metadata
context['metadata'][output_key] = {
    'mapping_combo_id': mapping_combo_id,
    'analysis_type': 'set_overlap',
    'input_rows': total_rows,
    'output_files': 5,  # Updated count
    'confidence_threshold': confidence_threshold
}
```

## Example Usage

```yaml
- name: calculate_overlap
  action:
    type: CALCULATE_SET_OVERLAP
    params:
      input_key: "ukbb_hpa_merged"
      source_name: "UKBB"
      target_name: "HPA"
      mapping_combo_id: "UKBB_HPA"
      confidence_threshold: 0.8
      output_dir: "results"
      output_key: "overlap_stats"
```

## Benefits for Cross-Mapping Analysis

1. **Standardized format**: All 9 protein mappings produce identical CSV structure
2. **Aggregation ready**: `mapping_combo_id` column enables easy combining
3. **Venn diagram ready**: Data formatted for visualization
4. **Quality tracking**: Confidence thresholds and metrics included
5. **Reproducible**: Timestamps and parameters recorded

## Combined Analysis Example

After running all 9 mappings, you can:
```python
# Combine all statistics
all_stats = pd.concat([
    pd.read_csv("results/UKBB_HPA/overlap_statistics.csv"),
    pd.read_csv("results/UKBB_QIN/overlap_statistics.csv"),
    pd.read_csv("results/HPA_QIN/overlap_statistics.csv"),
    # ... all 9 mappings
])

# Analyze patterns
all_stats.groupby('source_name')['source_match_rate'].mean()
all_stats.groupby('target_name')['target_match_rate'].mean()
```

## Key Features

1. **Works with match metadata**: Leverages MERGE_WITH_UNIPROT_RESOLUTION output
2. **Standardized output**: Consistent format across all mappings
3. **Multiple perspectives**: Source and target dataset viewpoints
4. **Quality metrics**: Confidence-based analysis
5. **Visualization ready**: Venn diagram and breakdown data
6. **Aggregation friendly**: mapping_combo_id for combining results