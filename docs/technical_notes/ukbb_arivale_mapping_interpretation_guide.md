# UKBB-Arivale Mapping Interpretation Guide

This document provides guidance on interpreting the `phase3_bidirectional_reconciliation_results.tsv` file, which contains the reconciled mapping between UKBB and Arivale protein identifiers. It explains how to analyze different mapping scenarios, understand validation statuses, and interpret complex cases involving historical identifier resolution.

## Understanding Mapping Scenarios

The output file contains several types of mapping scenarios, each with different implications for data integration between UKBB and Arivale datasets.

### 1. Bidirectional Exact Matches

**How to identify**: 
- `bidirectional_validation_status` = "Validated: Bidirectional exact match"
- Both `source_ukbb_assay_raw` and `reverse_mapping_ukbb_assay` are populated and identical
- `mapping_step_1_target_arivale_protein_id` is populated

**Interpretation**:
- Highest confidence mappings where UKBB maps to Arivale and Arivale maps back to the same UKBB entity
- Ideal for data integration as these represent unambiguous 1:1 relationships
- Typically have the highest `combined_confidence_score` values
- Should be prioritized for cross-study analyses

**Example Query**:
```sql
SELECT * FROM mapping_results 
WHERE bidirectional_validation_status = 'Validated: Bidirectional exact match'
ORDER BY combined_confidence_score DESC;
```

### 2. Forward-Only Mappings (UKBB → Arivale)

**How to identify**:
- `bidirectional_validation_status` = "Validated: Forward mapping only"
- `source_ukbb_assay_raw` is populated
- `mapping_step_1_target_arivale_protein_id` is populated
- `reverse_mapping_ukbb_assay` is NULL

**Interpretation**:
- UKBB successfully maps to Arivale, but Arivale maps back to a different UKBB entity or fails to map back
- Represents a less certain relationship than bidirectional matches
- May indicate:
  - Multiple UKBB proteins mapping to the same Arivale protein
  - Issues with the reverse mapping process
  - Differences in identifier resolution between directions

**Example Query**:
```sql
SELECT * FROM mapping_results 
WHERE bidirectional_validation_status = 'Validated: Forward mapping only'
ORDER BY combined_confidence_score DESC;
```

### 3. Reverse-Only Mappings (Arivale → UKBB)

**How to identify**:
- `bidirectional_validation_status` = "Validated: Reverse mapping only"
- `source_ukbb_assay_raw` is NULL or populated only via reverse mapping
- `mapping_step_1_target_arivale_protein_id` is populated
- `reverse_mapping_ukbb_assay` is populated

**Interpretation**:
- Arivale successfully maps to UKBB, but this UKBB entity wasn't mapped to in the forward direction
- Often involves historical UniProt ID resolution (check `arivale_uniprot_historical_resolution`)
- Useful for filling gaps in the forward mapping
- May represent UKBB entities that were missed in the forward process

**Example Query**:
```sql
SELECT * FROM mapping_results 
WHERE bidirectional_validation_status = 'Validated: Reverse mapping only'
ORDER BY combined_confidence_score DESC;
```

### 4. Conflicting Mappings

**How to identify**:
- `bidirectional_validation_status` = "Conflict: Different mappings in forward and reverse directions"
- Both `source_ukbb_assay_raw` and `reverse_mapping_ukbb_assay` are populated but different

**Interpretation**:
- The forward and reverse mappings lead to different conclusions
- Indicates potential ambiguity that requires closer examination
- May be due to:
  - Many-to-many relationships between platforms
  - Identifier resolution inconsistencies
  - Differences in mapping methods between directions
- Examine `bidirectional_validation_details` JSON for specific reasons

**Example Query**:
```sql
SELECT 
  source_ukbb_assay_raw, reverse_mapping_ukbb_assay, 
  mapping_step_1_target_arivale_protein_id,
  bidirectional_validation_details
FROM mapping_results 
WHERE bidirectional_validation_status = 'Conflict: Different mappings in forward and reverse directions';
```

### 5. Unmapped Entities

**How to identify**:
- `bidirectional_validation_status` = "Unmapped: No successful mapping found"
- For unmapped UKBB: `mapping_step_1_target_arivale_protein_id` is NULL
- For unmapped Arivale: `source_ukbb_assay_raw` is NULL but `mapping_step_1_target_arivale_protein_id` is populated

**Interpretation**:
- Represents entities from either platform that could not be mapped to the other
- Unmapped Arivale entities are included due to the "outer merge" logic
- Important for understanding dataset coverage and limitations
- For unmapped Arivale entities with `arivale_uniprot_historical_resolution = true`, historical resolution was attempted but still failed to find a match

**Example Query for Unmapped Arivale Entities**:
```sql
SELECT * FROM mapping_results 
WHERE bidirectional_validation_status = 'Unmapped: No successful mapping found'
AND mapping_step_1_target_arivale_protein_id IS NOT NULL;
```

## Interpreting Confidence Scores

The `combined_confidence_score` provides an overall assessment of mapping reliability and can be interpreted as follows:

### Confidence Score Ranges

- **0.9-1.0**: Highest confidence mappings, typically direct UniProt matches with bidirectional validation
- **0.7-0.9**: High confidence mappings, may involve secondary identifiers or unidirectional validation
- **0.5-0.7**: Medium confidence mappings, often involving multiple hops or gene-symbol-based matching
- **0.3-0.5**: Lower confidence mappings that may require additional validation
- **0.0-0.3**: Very low confidence or conflicting mappings, use with caution

### Factors Affecting Confidence

- **Bidirectional validation**: Scores are boosted for bidirectional matches
- **Mapping method**: Direct UniProt mappings receive higher confidence than gene symbol or other methods
- **Hop count**: More intermediary steps reduce confidence
- **Historical resolution**: Mappings involving historical ID resolution may have slightly reduced confidence
- **Conflicts**: Conflicting bidirectional mappings have reduced confidence

## Understanding Historical UniProt Resolution

The historical UniProt resolution columns provide crucial information about cases where Arivale's UniProt identifiers needed to be updated before mapping.

### Identifying Historical Resolution Cases

**How to identify**:
- `arivale_uniprot_historical_resolution` = true
- `arivale_uniprot_resolved_ac` is populated
- `arivale_uniprot_resolution_type` indicates the type of change

### Types of Historical Resolutions

#### 1. Demerged Identifiers

- **Resolution Type**: "demerged"
- **Example**: P0CG05 → P0DOY2
- **Interpretation**: The original UniProt entry was split into multiple new entries, and the mapping used one of these split entries
- **Significance**: The mapping may be to only one aspect of the original protein's function

#### 2. Secondary Identifiers

- **Resolution Type**: "secondary"
- **Example**: Q8NF90 → P12034
- **Interpretation**: The original ID is now a secondary identifier pointing to a different primary accession
- **Significance**: The mapping is highly reliable as this is a direct replacement

#### 3. Merged Identifiers

- **Resolution Type**: "merged"
- **Interpretation**: The original entry was merged with another entry into a new or existing accession
- **Significance**: The mapping is to a protein that may have a broader function than the original

### Interpreting Successful vs. Failed Historical Resolutions

- **Successful Resolution**: `bidirectional_validation_status` indicates a successful mapping (bidirectional, forward-only, or reverse-only)
- **Failed Resolution**: `bidirectional_validation_status` = "Unmapped: No successful mapping found" despite `arivale_uniprot_historical_resolution` = true
- **Partially Successful**: `bidirectional_validation_status` = "Conflict" with `arivale_uniprot_historical_resolution` = true indicates the resolution found a match but created a conflict

## Example: Tracing the Mapping Path for CAM_P0CG05

Let's walk through the mapping process for a specific complex case:

1. Arivale entity **CAM_P0CG05** has UniProt ID **P0CG05**
2. Historical resolution reveals P0CG05 was demerged into multiple entries, including **P0DOY2**
3. The resolved UniProt ID P0DOY2 is found in the UKBB dataset as **IGLC2**
4. The reverse mapping is successful (Arivale → UKBB), but there is no corresponding forward mapping
5. The final status is "Validated: Reverse mapping only"

This entity would have:
- `mapping_step_1_target_arivale_protein_id` = "CAM_P0CG05"
- `mapping_step_1_target_arivale_uniprot_ac` = "P0CG05" (original)
- `arivale_uniprot_historical_resolution` = true
- `arivale_uniprot_resolved_ac` = "P0DOY2"
- `arivale_uniprot_resolution_type` = "demerged"
- `reverse_mapping_ukbb_assay` = "IGLC2"
- `bidirectional_validation_status` = "Validated: Reverse mapping only"

## Using the Results for Data Integration

### Best Practices for UKBB-Arivale Data Integration

1. **Prioritization Strategy**:
   - First use bidirectional exact matches
   - Then consider forward-only and reverse-only mappings with high confidence
   - Use conflicting mappings only after manual review
   - Avoid unmapped entities unless necessary

2. **Confidence Thresholds**:
   - For high-stakes analyses, use only mappings with combined_confidence_score > 0.8
   - For exploratory analyses, mappings with score > 0.5 may be acceptable
   - Consider using confidence scores as weights in statistical analyses

3. **Handling Historical ID Cases**:
   - Always check if the mapping involved historical resolution
   - For demerged proteins, be aware the biological interpretation may have changed
   - Check UniProt documentation for details on specific ID changes

4. **Documentation and Reproducibility**:
   - Always document which validation categories were included in analyses
   - Note any confidence thresholds applied
   - Include counts of each mapping category used

### Potential Pitfalls and How to Avoid Them

1. **False Positives**: 
   - Particularly with gene symbol mapping which can be ambiguous
   - Mitigate by using higher confidence thresholds and checking bidirectional status

2. **Missing Mappings**:
   - Some proteins may truly lack equivalents between platforms
   - Check if unmapped entities were due to failed historical resolution attempts
   - Consider using additional mapping resources for important unmapped proteins

3. **Many-to-Many Relationships**:
   - Some proteins have legitimate many-to-many mappings between platforms
   - Check for clusters of conflicts that might indicate protein families
   - Use network visualization to identify complex relationship patterns

## Contribution to Biomapper Project Goals

This comprehensive UKBB-Arivale mapping output supports the Biomapper project goals by:

1. **Establishing Cross-Platform Concordance**: Enabling researchers to relate protein measurements between these two important biobanks

2. **Addressing Historical ID Challenges**: Systematically resolving outdated identifiers that would otherwise block successful mapping

3. **Providing Mapping Quality Metrics**: Helping researchers assess the reliability of each mapping with detailed status information and confidence scores

4. **Enabling Transparent "Outer Merge" Logic**: Ensuring complete representation of all entities from both platforms, facilitating comprehensive data integration and analysis

5. **Supporting Reproducible Research**: Providing detailed mapping path information that allows others to validate and reproduce the mapping process