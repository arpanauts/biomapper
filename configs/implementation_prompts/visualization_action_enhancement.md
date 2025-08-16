# Visualization Action Enhancement Prompt

## Objective
Enhance `GENERATE_MAPPING_VISUALIZATIONS_V2` to create progressive mapping visualizations with direct SVG/PNG output and TSV statistics export.

## Current Context
- Existing action: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/reports/generate_visualizations_v2.py`
- Has `export_static` and `static_formats` parameters for PNG/SVG export
- Needs enhancement for progressive mapping visualization

## Requirements

### 1. Progressive Waterfall Chart
Create visualization showing cumulative mapping improvement:
```
100% |
     |
 90% |                                    ┌─────── 89% FINAL
     |                              ┌─────┤ (+2%)
 80% |                    ┌─────────┤     └─ Historical
     |          ┌─────────┤ (+15%)  
 70% |          │ (+0%)   └─ Historical Resolution
     | ┌────────┤
 60% | │  65%   └─ Composite Parsing
     | │ Direct
 50% | │ Match
     | │
 40% | │
     |─┴────────┬─────────┬─────────┬─────────
       Stage 1   Stage 2   Stage 3   Stage 4
```

### 2. Progressive Statistics Export
Generate comprehensive TSV file with:
```
stage_number,stage_name,method,new_matches,cumulative_matched,cumulative_rate,improvement,computation_time,confidence_avg
1,direct_match,Direct UniProt,650,650,65.0%,65.0%,0.5s,1.00
2,composite_expansion,Composite parsing,0,650,65.0%,0.0%,0.2s,0.95
3,historical_resolution,Historical API,150,800,80.0%,15.0%,12.3s,0.90
```

### 3. Enhanced Parameters
Extend existing `GenerateMappingVisualizationsParams`:
```python
# Add to existing parameters
progressive_mode: bool = Field(False, description="Generate progressive mapping visualizations")
export_statistics_tsv: bool = Field(False, description="Export progressive statistics as TSV")
waterfall_chart: bool = Field(False, description="Generate waterfall progression chart")
stage_comparison: bool = Field(False, description="Generate stage-by-stage comparison charts")
```

### 4. New Chart Types
Add these chart configurations:
- **`waterfall`**: Progressive improvement waterfall
- **`stage_bars`**: Bar chart comparing stage contributions
- **`confidence_distribution`**: Confidence scores by stage
- **`method_breakdown`**: Pie chart of mapping methods

### 5. Input Data Processing
Must handle:
- `context["progressive_stats"]` for stage information
- Standardized mapping results for detailed analysis
- Both single-stage and multi-stage strategies

### 6. File Outputs
Generate these files in output directory:
- **`progressive_waterfall.png/svg`** - Main waterfall chart
- **`stage_comparison.png/svg`** - Stage contribution bars
- **`method_breakdown.png/svg`** - Mapping method distribution
- **`progressive_statistics.tsv`** - Detailed statistics table
- **`progressive_summary.json`** - Machine-readable summary

## Implementation Steps
1. Examine existing `generate_visualizations_v2.py` structure
2. Add progressive-specific parameters to existing model
3. Implement waterfall chart generation using Plotly
4. Add TSV statistics export functionality
5. Integrate with existing chart generation framework
6. Test with sample progressive data
7. Ensure SVG/PNG export works correctly

## Success Criteria
- ✅ Generates accurate waterfall charts
- ✅ Exports comprehensive TSV statistics
- ✅ Produces publication-quality SVG/PNG files
- ✅ Handles both progressive and single-stage data
- ✅ Maintains backward compatibility with existing functionality
- ✅ Follows existing action patterns and 2025 standards

## Technical Implementation Notes

### Waterfall Chart Logic:
```python
def create_waterfall_chart(progressive_stats: dict) -> go.Figure:
    stages = progressive_stats["stages"]
    
    # Calculate cumulative rates and improvements
    cumulative_rates = []
    improvements = []
    stage_names = []
    
    for stage_num in sorted(stages.keys()):
        stage = stages[stage_num]
        cumulative_rate = stage["cumulative_matched"] / progressive_stats["total_processed"]
        cumulative_rates.append(cumulative_rate * 100)
        
        if stage_num == 1:
            improvement = cumulative_rate * 100
        else:
            prev_rate = cumulative_rates[-2]
            improvement = cumulative_rate * 100 - prev_rate
        
        improvements.append(improvement)
        stage_names.append(stage["name"])
    
    # Create waterfall using Plotly
    fig = go.Figure(go.Waterfall(
        name="Progressive Mapping",
        orientation="v",
        measure=["relative"] * len(stages),
        x=stage_names,
        y=improvements,
        text=[f"+{imp:.1f}%" for imp in improvements],
        # Styling for publication quality
    ))
    
    return fig
```

### TSV Export Structure:
```python
def export_progressive_tsv(progressive_stats: dict, output_path: str):
    stages_data = []
    for stage_num in sorted(progressive_stats["stages"].keys()):
        stage = progressive_stats["stages"][stage_num]
        stages_data.append({
            "stage_number": stage_num,
            "stage_name": stage["name"],
            "method": stage["method"],
            "new_matches": stage.get("new_matches", stage.get("matched", 0)),
            "cumulative_matched": stage["cumulative_matched"],
            "cumulative_rate": f"{stage['cumulative_matched'] / progressive_stats['total_processed'] * 100:.1f}%",
            # ... additional fields
        })
    
    df = pd.DataFrame(stages_data)
    df.to_csv(output_path, sep='\t', index=False)
```

### Integration Points:
- Must work with existing `ChartConfig` system
- Should leverage existing Plotly export functionality
- Integrate with `export_static` and `static_formats` parameters
- Use existing error handling and logging patterns

## Notes
- Maintain scientific accuracy in all visualizations
- Ensure charts are colorblind-friendly
- Follow publication standards for figure quality
- Consider performance for large datasets
- Design for both interactive and static use cases