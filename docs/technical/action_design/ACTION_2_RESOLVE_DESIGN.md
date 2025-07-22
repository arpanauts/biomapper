# Action 2: MERGE_WITH_UNIPROT_RESOLUTION - Design

## Purpose
Smart merge of two datasets with integrated identifier resolution:
1. First attempts direct matching (including composite ID logic)
2. Uses UniProt API only for unresolved identifiers
3. Preserves ALL rows (matched and unmatched)
4. Tracks detailed match metadata

## Key Innovation
This replaces separate MERGE and RESOLVE actions with one intelligent operation.

## Parameters

```python
class MergeWithUniprotResolutionParams(BaseModel):
    # Input datasets
    source_dataset_key: str = Field(..., description="First dataset from context")
    target_dataset_key: str = Field(..., description="Second dataset from context")
    
    # Column specifications
    source_id_column: str = Field(..., description="ID column in source dataset")
    target_id_column: str = Field(..., description="ID column in target dataset")
    
    # Composite handling
    composite_separator: str = Field("_", description="Separator for composite IDs")
    
    # API configuration
    use_api: bool = Field(True, description="Whether to use API for unresolved")
    api_batch_size: int = Field(100, description="IDs per API call")
    api_cache_results: bool = Field(True, description="Cache API responses")
    
    # Output
    output_key: str = Field(..., description="Key for resolved mapping table")
    
    # Options
    confidence_threshold: float = Field(0.0, description="Minimum confidence to keep")
```

## Processing Logic

### Phase 1: Direct Matching

```python
# 1. Get both datasets
source_df = context['datasets'][source_dataset_key].to_dataframe()
target_df = context['datasets'][target_dataset_key].to_dataframe()

# 2. Extract unique IDs
source_ids = set(source_df[source_id_column].dropna())
target_ids = set(target_df[target_id_column].dropna())

# 3. Find direct matches (including composite logic)
direct_matches = []

for source_id in source_ids:
    for target_id in target_ids:
        matches = find_matches(source_id, target_id, composite_separator)
        for match_value, match_type in matches:
            direct_matches.append({
                'source_id': source_id,
                'target_id': target_id,
                'match_value': match_value,
                'match_type': match_type,
                'confidence': 1.0
            })

def find_matches(source_id, target_id, separator):
    """Find all matches between IDs, including composite logic.
    Returns list of (match_value, match_type) tuples."""
    matches = []
    
    # Exact match
    if source_id == target_id:
        matches.append((source_id, 'direct'))
        return matches
    
    # Source composite, target single
    if separator in source_id:
        parts = source_id.split(separator)
        if target_id in parts:
            matches.append((target_id, 'composite'))
    
    # Target composite, source single  
    elif separator in target_id:
        parts = target_id.split(separator)
        if source_id in parts:
            matches.append((source_id, 'composite'))
    
    # Both composite - find all overlapping parts
    elif separator in source_id and separator in target_id:
        parts1 = set(source_id.split(separator))
        parts2 = set(target_id.split(separator))
        for common in parts1 & parts2:
            matches.append((common, 'composite'))
    
    return matches
```

### Phase 2: API Resolution for Unmatched

```python
# 4. Identify unresolved IDs
matched_source_ids = {m['source_id'] for m in direct_matches}
matched_target_ids = {m['target_id'] for m in direct_matches}

unresolved_source = source_ids - matched_source_ids
unresolved_target = target_ids - matched_target_ids

# 5. Resolve via API (if enabled)
if use_api and (unresolved_source or unresolved_target):
    # Combine and deduplicate
    all_unresolved = list(unresolved_source | unresolved_target)
    
    # Call API in batches
    api_resolutions = {}
    for batch in chunks(all_unresolved, api_batch_size):
        results = await resolve_batch_via_api(batch)
        api_resolutions.update(results)
    
    # 6. Try matching with resolved IDs
    for source_id in unresolved_source:
        resolved_source = api_resolutions.get(source_id, source_id)
        for target_id in unresolved_target:
            resolved_target = api_resolutions.get(target_id, target_id)
            
            matches = find_matches(resolved_source, resolved_target, separator)
            for match_value, _ in matches:  # Ignore match_type from find_matches
                direct_matches.append({
                    'source_id': source_id,
                    'target_id': target_id,
                    'match_value': match_value,
                    'match_type': 'historical',  # Override since this is API-resolved
                    'resolved_source': resolved_source,
                    'resolved_target': resolved_target,
                    'confidence': min(
                        api_resolutions.get(source_id, {}).get('confidence', 1.0),
                        api_resolutions.get(target_id, {}).get('confidence', 1.0)
                    ),
                    'api_resolved': True
                })
```

### Phase 3: Create Full Merged Dataset

```python
# 7. Build match records with metadata
all_matches = []

# Example of composite match creating multiple rows:
# If UKBB has "Q14213_Q8NEV9" and HPA has both "Q14213" and "Q8NEV9"
# We create TWO match records:
# Row 1: Q14213_Q8NEV9 → Q14213 (match_type='composite')
# Row 2: Q14213_Q8NEV9 → Q8NEV9 (match_type='composite')

for match in direct_matches:
    all_matches.append({
        'source_id': match['source_id'],
        'target_id': match['target_id'],
        'match_value': match['match_value'],  # The actual value that matched
        'match_type': match['match_type'],    # 'direct', 'composite', 'historical'
        'match_confidence': match['confidence'],
        'api_resolved': match.get('api_resolved', False)
    })

# 8. Create full outer merge to preserve ALL rows
# First, create mapping lookup
mapping_df = pd.DataFrame(all_matches)

# Merge source data with mappings
source_with_matches = source_df.merge(
    mapping_df,
    left_on=source_id_column,
    right_on='source_id',
    how='left'
)

# Then merge with target data
final_merged = source_with_matches.merge(
    target_df,
    left_on='target_id',
    right_on=target_id_column,
    how='outer',
    suffixes=('_source', '_target'),
    indicator=True
)

# Add rows from target that didn't match anything
unmatched_target = target_df[~target_df[target_id_column].isin(mapping_df['target_id'])]
for _, row in unmatched_target.iterrows():
    final_merged = pd.concat([final_merged, pd.DataFrame([{
        **{f"{col}_target": val for col, val in row.items()},
        'match_type': None,
        'match_value': None,
        'match_confidence': None
    }])])

# 9. Clean up merge indicator
final_merged['match_status'] = final_merged['_merge'].map({
    'left_only': 'source_only',
    'right_only': 'target_only', 
    'both': 'matched'
})
final_merged.drop('_merge', axis=1, inplace=True)

# 10. Store results
context['datasets'][output_key] = TableData.from_dataframe(final_merged)
```

## Output Structure

The output is a complete merged dataset with:

### Match Metadata Columns
- `match_value`: The actual ID value that created the match
- `match_type`: Type of match
  - `'direct'`: Exact ID match
  - `'composite'`: Composite ID matched to component
  - `'historical'`: Match via API resolution
  - `None`: No match found
- `match_confidence`: Confidence score (1.0 for direct/composite, varies for API)
- `match_status`: Row status
  - `'matched'`: Row has a match
  - `'source_only'`: Row from source with no match
  - `'target_only'`: Row from target with no match
- `api_resolved`: Boolean indicating if API was used

### Data Columns
- All columns from source dataset (with `_source` suffix if conflicts)
- All columns from target dataset (with `_target` suffix if conflicts)
- ID columns preserved without suffix

### Example Output Rows

```
| UniProt_source | match_value | match_type | match_status | uniprot_target | gene_target |
|----------------|-------------|------------|--------------|----------------|-------------|
| Q14213_Q8NEV9  | Q14213      | composite  | matched      | Q14213         | IL27        |
| Q14213_Q8NEV9  | Q8NEV9      | composite  | matched      | Q8NEV9         | EBI3        |
| P12345         | P12345      | direct     | matched      | P12345         | GENE1       |
| Q99999         | P88888      | historical | matched      | P88888         | GENE2       |
| A11111         | None        | None       | source_only  | None           | None        |
| None           | None        | None       | target_only  | B22222         | GENE3       |
```

## Example Usage

```yaml
- name: merge_proteins
  action:
    type: MERGE_WITH_UNIPROT_RESOLUTION
    params:
      source_dataset_key: "ukbb_raw"
      target_dataset_key: "hpa_raw"
      source_id_column: "UniProt"
      target_id_column: "uniprot"
      composite_separator: "_"
      use_api: true
      api_batch_size: 100
      output_key: "protein_mappings"
```

## Key Benefits

1. **Efficient**: Only calls API for truly unresolved IDs
2. **Smart composite handling**: Matches Q14213_Q8NEV9 to Q14213
3. **Preserves all metadata**: Full row information maintained
4. **Confidence tracking**: Know which matches are direct vs API-resolved
5. **Flexible**: Can disable API for direct-only matching

## Statistics to Track

```python
context['metadata'][output_key] = {
    'total_source_rows': len(source_df),
    'total_target_rows': len(target_df),
    'total_output_rows': len(final_merged),
    'matches_by_type': {
        'direct': sum(1 for _, row in final_merged.iterrows() if row['match_type'] == 'direct'),
        'composite': sum(1 for _, row in final_merged.iterrows() if row['match_type'] == 'composite'),
        'historical': sum(1 for _, row in final_merged.iterrows() if row['match_type'] == 'historical'),
    },
    'unmatched_source': sum(1 for _, row in final_merged.iterrows() if row['match_status'] == 'source_only'),
    'unmatched_target': sum(1 for _, row in final_merged.iterrows() if row['match_status'] == 'target_only'),
    'api_calls_made': api_call_count,
    'unique_source_ids': len(source_ids),
    'unique_target_ids': len(target_ids)
}
```

## Summary of Key Decisions

1. **This action replaces MERGE_DATASETS** - It's a smart merge with resolution built in
2. **Composite matches create multiple rows** - If Q14213_Q8NEV9 matches both Q14213 and Q8NEV9, we get two rows
3. **All rows preserved** - Unmatched rows kept with null match metadata
4. **Match metadata tracked** in new columns:
   - `match_value`: The actual ID that matched
   - `match_type`: 'direct', 'composite', or 'historical'
   - `match_confidence`: Confidence score
   - `match_status`: 'matched', 'source_only', or 'target_only'
5. **API only for unresolved** - Efficient use of external resources