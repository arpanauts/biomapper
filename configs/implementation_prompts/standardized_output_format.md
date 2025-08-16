# Standardized Output Format Implementation Prompt

## Objective
Create a universal standardized output format for all mapping actions to enable consistent progressive analysis and visualization.

## Current Context
- Working in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/`
- Existing actions need retrofitting: `MERGE_DATASETS`, `PROTEIN_HISTORICAL_RESOLUTION`, etc.
- Current output varies by action (some use pandas DataFrames, others use custom formats)

## Requirements

### 1. Standard Output Schema
All mapping actions must output this exact format:
```python
class StandardMappingResult(BaseModel):
    source_id: str = Field(..., description="Original source identifier")
    target_id: Optional[str] = Field(None, description="Matched target identifier") 
    match_method: str = Field(..., description="Method used for matching")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence score")
    stage: int = Field(..., description="Progressive stage number")
    details: Optional[str] = Field(None, description="Additional match details")
    is_composite: bool = Field(False, description="Whether source was composite identifier")
    parsed_value: Optional[str] = Field(None, description="Individual parsed value used for matching")
```

### 2. Confidence Score Framework
Implement consistent confidence scoring:
- **Direct exact matches**: 1.0
- **Composite-derived matches**: 0.95 (required parsing)
- **Historical API resolution**: 0.90 (deprecated ID lookup)
- **Gene symbol bridging**: 0.85 (indirect mapping)
- **Similarity matching**: 0.70-0.80 (threshold-dependent)

Document rationale for each score assignment.

### 3. Actions to Standardize
Update these existing actions:
1. `MERGE_DATASETS` - Currently outputs DataFrames
2. `PROTEIN_HISTORICAL_RESOLUTION` - Add standard columns
3. `PROTEIN_ENSEMBL_BRIDGE` - Ensure consistency
4. `PROTEIN_GENE_SYMBOL_BRIDGE` - Ensure consistency

### 4. Backward Compatibility
- Maintain existing DataFrame outputs for legacy support
- Add new `standardized_output` field to action results
- Allow YAML strategies to specify output format preference

### 5. Integration with Context
Standardized results should integrate with:
- `progressive_stats` tracking
- Visualization input requirements
- Export capabilities

## Implementation Steps
1. Create `StandardMappingResult` model in `core/models/`
2. Create `MappingResultStandardizer` utility class
3. Update each mapping action to output standard format
4. Modify action registry to validate standard outputs
5. Test with existing strategies
6. Update YAML strategy examples

## Success Criteria
- ✅ All mapping actions output identical schema
- ✅ Confidence scores are documented and consistent
- ✅ Backward compatibility maintained
- ✅ Progressive wrapper can consume standardized outputs
- ✅ Visualization actions can process any mapping result

## Specific Implementation Notes

### For MERGE_DATASETS Action:
```python
# Current: Returns DataFrame with mixed columns
# New: Also return standardized format
results = []
for match in merged_df.iterrows():
    results.append(StandardMappingResult(
        source_id=match['source_id'],
        target_id=match['target_id'],
        match_method="direct_merge",
        confidence=1.0,  # Exact match
        stage=1,  # Set by progressive wrapper
        details=f"Merged on {join_columns}",
        is_composite=match.get('is_composite_uniprot', False),
        parsed_value=match.get('parsed_uniprot')
    ))
```

### For PROTEIN_HISTORICAL_RESOLUTION:
```python
# Add to existing historical resolution logic
StandardMappingResult(
    source_id=original_id,
    target_id=resolved_id,
    match_method="historical_api",
    confidence=0.90,
    stage=3,  # Set by progressive wrapper
    details=f"Resolved via UniProt API: {resolution_type}",
    is_composite=False,
    parsed_value=original_id
)
```

## Testing Requirements
- Unit tests for each standardized action
- Integration tests with progressive wrapper
- Performance benchmarks vs. current implementation
- Validation of confidence score accuracy

## Notes
- Use Pydantic for schema validation
- Follow 2025 standardization patterns
- Consider memory efficiency for large datasets
- Design for scientific reproducibility