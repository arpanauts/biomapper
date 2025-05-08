# UKBB-Arivale Protein Mapping Summary

Generated: 2025-05-08 15:49:46

This document provides a summary of the mapping results between UK Biobank (UKBB) and Arivale protein identifiers, produced by the three-phase mapping pipeline.

## Overall Mapping Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Total entries in final output | 2984 | 100% |
| Unique UKBB proteins | 2923 | 97.96% |
| Unique Arivale proteins | 1197 | 40.11% |
| Successfully mapped (any direction) | 1173 | 39.31% |
| Unmapped entities | 1809 | 60.62% |

## Validation Status Distribution

| Validation Status | Count | Percentage of Total | Percentage of Mapped |
|-------------------|-------|---------------------|---------------------|
| Validated: Bidirectional exact match | 1132 | 37.94% | 96.50% |
| Validated: Forward mapping only | 4 | 0.13% | 0.34% |
| Validated: Reverse mapping only | 37 | 1.24% | 3.15% |
| Conflict: Different mappings | 2 | 0.07% | 0.17% |
| Unmapped: No successful mapping found | 1809 | 60.62% | - |

## Mapping Methods Distribution

| Mapping Method | Count | Percentage of Mapped |
|----------------|-------|---------------------|
| No mapping found | 1785 | 152.17% |
| Direct Primary: UKBB UniProt -> Arivale Protein ID via Arivale Metadata | 1136 | 96.85% |
| Indirect: UKBB Gene Name -> UniProt AC -> Arivale Protein ID | 2 | 0.17% |

## Historical UniProt Resolution Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Total historical resolutions attempted | 3 | 100% |
| Successful historical resolutions | 3 | 100.00% |
| Failed historical resolutions | 0 | 0.00% |

### Resolution Types

| Resolution Type | Count | Percentage of Resolutions |
|-----------------|-------|---------------------------|
| Secondary identifiers | 2 | 66.67% |
| Demerged identifiers | 1 | 33.33% |

## Confidence Score Distribution

| Confidence Range | Count | Percentage of Mapped |
|------------------|-------|---------------------|
| 0.9-1.0 (Highest) | 1172 | 99.91% |
| 0.7-0.9 (High) | 1 | 0.09% |
| 0.5-0.7 (Medium) | 0 | 0.00% |
| 0.3-0.5 (Low) | 0 | 0.00% |
| 0.0-0.3 (Very Low) | 0 | 0.00% |

## Hop Count Distribution

| Hop Count | Count | Percentage of Mapped |
|-----------|-------|---------------------|
| 0 hops  | 37 | 3.15% |
| 1 hop (direct) | 1135 | 96.76% |
| 2 hops  | 1 | 0.09% |

## Key Findings

1. **Mapping Success Rate**: The overall mapping success rate is 39.31%, meaning that nearly 39% of proteins could be mapped between the two platforms.

2. **Bidirectional Validation**: Of the successfully mapped entities, 96.50% were validated bidirectionally (exact matches in both directions), providing the highest confidence mappings.

3. **Importance of Historical Resolution**: Historical UniProt ID resolution contributed to 0.26% of successful mappings, demonstrating the importance of handling identifier evolution.

4. **High Confidence Mappings**: The vast majority (99.91%) of successful mappings have the highest confidence range (0.9-1.0), indicating predominantly direct, reliable connections between the platforms.

5. **Low Mapping Complexity**: Most mappings were established with just 1 hop (direct matches), with only 3.24% requiring multiple hops. This suggests relatively straightforward mappings between the platforms.

## Notable Case Study: P0CG05 → P0DOY2

A highlight of the mapping process was the successful resolution of P0CG05 (Arivale ID: CAM_P0CG05) to P0DOY2, which then mapped to IGLC2. This case demonstrates the pipeline's ability to handle complex historical UniProt identifier changes (specifically a demerged protein) and establish valid cross-platform mappings that would otherwise be missed.

## Next Steps and Recommendations

1. For analyses requiring high confidence, focus on the bidirectional exact matches.

2. For broader coverage, include the forward-only and reverse-only validated mappings, which together account for a significant portion of successful mappings.

3. For unmapped proteins of particular scientific interest, consider:
   - Manual review of near-miss cases
   - Exploration of additional mapping resources or methods
   - Direct sequence-based comparison where feasible

4. The mapping results should be periodically updated as UniProt identifiers continue to evolve.

