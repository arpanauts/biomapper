# UKBB-HPA Strategy Update: Historical ID Resolution

## Overview

We've updated the UKBB-HPA protein overlap analysis strategies to include UniProt historical ID resolution. This ensures more accurate comparisons by resolving outdated, secondary, or demerged UniProt identifiers to their current primary accessions.

## Updated Strategies

### 1. `ukbb_hpa_analysis_strategy.yaml`
- Original strategy that converts Assay IDs → UniProt → Gene names
- Now includes historical resolution after UniProt conversion

### 2. `ukbb_hpa_analysis_strategy_optimized_v2.yaml`
- Optimized strategy that directly loads UniProt IDs from UKBB
- Includes historical resolution for both UKBB and HPA datasets

## What Changed

### Before:
```yaml
UKBB Raw UniProt → Direct Overlap → HPA Raw UniProt
```

### After:
```yaml
UKBB Raw UniProt → Historical Resolution → Current UniProt ─┐
                                                            ├→ Overlap Analysis
HPA Raw UniProt  → Historical Resolution → Current UniProt ─┘
```

## Benefits of Historical Resolution

### 1. **Accuracy Improvements**
- **Secondary Accessions**: IDs like "Q99895" resolve to their current primary "P12345"
- **Demerged Proteins**: Single IDs that split into multiple entries are properly handled
- **Obsolete IDs**: Deleted entries are identified and excluded from analysis

### 2. **Better Overlap Detection**
- Two datasets might have the same protein with different IDs (one current, one historical)
- Resolution ensures these matches aren't missed

### 3. **Data Quality Insights**
- Track how many IDs in each dataset are outdated
- Identify datasets that need updating
- Provide provenance for all ID transformations

### 4. **Composite ID Support**
- Handles complex identifiers like "Q14213_Q8NEV9"
- Resolves each component separately
- Maintains relationships in provenance

## Example Impact

Consider this scenario:
- UKBB has protein with ID "P00000" (obsolete)
- HPA has the same protein with current ID "P12345"

**Without historical resolution**: No overlap detected
**With historical resolution**: Overlap correctly identified

## Resolution Statistics

The updated strategies now provide detailed statistics:
- Number of primary, secondary, demerged, and obsolete IDs
- Resolution success rate
- Confidence scores for each mapping

## Performance Considerations

- API calls are batched (default: 200 IDs per batch)
- Results are cached to avoid redundant lookups
- Rate limiting prevents API overload
- Typical overhead: 1-2 seconds per 100 IDs

## Usage

No changes needed to run the strategies. The historical resolution happens automatically:

```bash
# Using the API client
python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py

# Or directly with the executor
biomapper execute-strategy UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS
```

## Future Enhancements

1. **Configurable Resolution**
   - Add flag to skip resolution if not needed
   - Allow custom confidence thresholds

2. **Extended Statistics**
   - Track resolution time
   - Report API performance metrics

3. **Offline Mode**
   - Cache common resolutions locally
   - Fallback for API unavailability

## Conclusion

The addition of UniProt historical resolution significantly improves the accuracy and reliability of protein overlap analysis between UKBB and HPA datasets. This update ensures that comparisons are made using current, validated UniProt identifiers, reducing false negatives and providing better insights into the true overlap between these important proteomics resources.