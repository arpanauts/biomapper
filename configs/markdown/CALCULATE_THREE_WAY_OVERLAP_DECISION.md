# Decision: CALCULATE_THREE_WAY_OVERLAP Implementation

## Status: NOT IMPLEMENTED

## Decision Date: 2025-08-05

## Rationale

After analyzing the metabolomics pipeline requirements, I've decided not to implement the `CALCULATE_THREE_WAY_OVERLAP` action for the following reasons:

1. **Existing Alternative**: The existing `CALCULATE_SET_OVERLAP` action can be used multiple times to achieve the same result with pairwise comparisons.

2. **Limited Use Case**: Three-way overlap calculation is a specialized need that may not justify a dedicated action.

3. **Workaround Available**: The YAML strategy can use multiple `CALCULATE_SET_OVERLAP` actions:
   - Israeli10K vs UKBB
   - Israeli10K vs Arivale  
   - UKBB vs Arivale

4. **Following Biomapper Principles**: Per the biomapper-strategy-developer agent guidance:
   - "Build strategies incrementally, measuring improvement at each stage"
   - Focus on getting core functionality working first
   - Add convenience actions later if needed

## Recommended Approach

For three-way metabolomics mapping, use the existing actions in combination:

```yaml
# Calculate pairwise overlaps
- name: overlap_israeli_ukbb
  action:
    type: CALCULATE_SET_OVERLAP
    params:
      source_dataset_key: "israeli10k_data"
      target_dataset_key: "ukbb_data"
      output_key: "overlap_israeli_ukbb"

- name: overlap_israeli_arivale
  action:
    type: CALCULATE_SET_OVERLAP
    params:
      source_dataset_key: "israeli10k_data"
      target_dataset_key: "arivale_data"
      output_key: "overlap_israeli_arivale"

- name: overlap_ukbb_arivale
  action:
    type: CALCULATE_SET_OVERLAP
    params:
      source_dataset_key: "ukbb_data"
      target_dataset_key: "arivale_data"
      output_key: "overlap_ukbb_arivale"
```

## Future Consideration

If three-way overlap calculations become a common pattern across multiple strategies, then implementing a dedicated `CALCULATE_THREE_WAY_OVERLAP` action would be justified. The implementation would follow the same TypedStrategyAction pattern used for MERGE_DATASETS.