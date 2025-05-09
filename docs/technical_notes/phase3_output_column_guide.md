# Phase 3 Bidirectional Reconciliation Output Guide

This document describes the structure and interpretation of the output from the Phase 3 bidirectional reconciliation process for entity mapping.

## Overview

Phase 3 reconciles the results of forward mapping (Phase 1) and reverse mapping (Phase 2) to create a comprehensive bidirectional mapping report. The output provides rich metadata about the validation status, mapping details, and confidence levels of each entity mapping relationship.

## Column Structure

The output file contains dynamically generated column names based on the source and target endpoints being mapped. This guide uses the UKBB-to-Arivale protein mapping as an example.

### Source Entity Columns

| Column Name | Description |
|------------|-------------|
| `source_ukbb_assay_raw` | The original UKBB assay identifier |
| `source_ukbb_panel` | The panel in which the UKBB assay appears |
| `source_ukbb_uniprot_ac` | The UniProt accession for the UKBB entity |
| `source_ukbb_parsed_gene_name` | The gene name parsed from the UKBB entity |

### Target Entity Columns

| Column Name | Description |
|------------|-------------|
| `mapping_step_1_target_arivale_protein_id` | The Arivale protein identifier |
| `mapping_step_1_target_arivale_uniprot_ac` | The UniProt accession for the Arivale protein |
| `mapping_step_1_target_arivale_gene_symbol` | The gene symbol for the Arivale protein |
| `mapping_step_1_target_arivale_protein_name` | The descriptive name of the Arivale protein |

### Mapping Method and Details

| Column Name | Description |
|------------|-------------|
| `mapping_method` | The method used to establish the forward mapping |
| `mapping_path_details_json` | JSON details of the steps in the mapping path |
| `confidence_score` | Confidence score for the forward mapping (0.0-1.0) |
| `hop_count` | Number of intermediate steps in the mapping path |
| `notes` | Additional notes or context about the mapping |

### Bidirectional Validation Columns

| Column Name | Description |
|------------|-------------|
| `reverse_mapping_ukbb_assay` | The UKBB assay identified in the reverse mapping |
| `reverse_mapping_method` | The method used to establish the reverse mapping |
| `bidirectional_validation_status` | The validation status (see status values below) |
| `bidirectional_validation_details` | JSON details explaining the validation result |
| `combined_confidence_score` | Combined confidence from forward and reverse mappings |

### Historical Resolution Columns

| Column Name | Description |
|------------|-------------|
| `arivale_uniprot_historical_resolution` | Whether historical UniProt resolution was applied |
| `arivale_uniprot_resolved_ac` | The resolved UniProt accession (if applicable) |
| `arivale_uniprot_resolution_type` | The type of resolution (merged, demerged, secondary) |

### One-to-Many Relationship Flags

| Column Name | Description |
|------------|-------------|
| `is_one_to_many_source` | Flag indicating whether this source entity maps to multiple targets |
| `is_one_to_many_target` | Flag indicating whether this target entity maps to multiple sources |
| `is_canonical_mapping` | Flag indicating whether this is the preferred mapping for a source entity |

## Validation Status Values

The `bidirectional_validation_status` column contains one of the following values:

| Status | Description |
|--------|-------------|
| `Validated: Bidirectional exact match` | Entity maps to target, and target maps back to the same entity |
| `Validated: Forward mapping only` | Entity maps to target, but target doesn't map back to this entity |
| `Validated: Reverse mapping only` | No forward mapping, but target maps to this entity |
| `Conflict: Different mappings in forward and reverse directions` | Forward and reverse mappings exist but point to different entities |
| `Unmapped: No successful mapping found` | No mapping found in either direction |

## Validation Details JSON Structure

The `bidirectional_validation_details` column contains a JSON object with the following structure:

```json
{
  "reason": "Exact bidirectional match",
  "forward_mapping": "IL18 -> CVD2_Q14116",
  "reverse_mapping": "CVD2_Q14116 -> IL18",
  "alternate_forward": null,
  "historical_resolution": "Q14116 -> Q14116"
}
```

The fields in this JSON object include:

- `reason`: A human-readable explanation of the validation status
- `forward_mapping`: The forward mapping path (source → target)
- `reverse_mapping`: The reverse mapping path (target → source)
- `alternate_forward`: An alternate forward mapping in one-to-many scenarios (optional)
- `historical_resolution`: Historical UniProt resolution details (optional)

## One-to-Many Relationship Handling

When one entity maps to multiple entities sharing the same UniProt identifier, all mappings are included in the output but only one is designated as the canonical mapping per source entity.

### Canonical Mapping Selection

The `is_canonical_mapping` flag identifies the preferred mapping for each source entity. The selection process is:

1. Prioritize bidirectional exact matches over unidirectional matches
2. Among bidirectional matches, select the mapping with the highest confidence score
3. If no bidirectional matches, select the unidirectional mapping with the highest confidence

### Example: One-to-Many Source Mapping

In the case of IL18 mapping to multiple Arivale proteins (CVD2_Q14116, INF_Q14116):

- Both mappings are valid and included in the output
- Both are marked with `is_one_to_many_source = True`
- Only one mapping (typically the higher confidence one) has `is_canonical_mapping = True`

## Mapping Statistics

The metadata JSON file includes comprehensive statistics about the mapping:

- `total_mappings`: Total number of mapping entries
- `unique_source_entities`: Number of unique source entities
- `unique_target_entities`: Number of unique target entities
- `validation_status_counts`: Count of mappings by validation status
- `one_to_many_source_mappings`: Count of one-to-many source mappings
- `one_to_many_target_mappings`: Count of one-to-many target mappings
- `canonical_mappings`: Count of canonical mappings (one per source entity)
- `mapping_quality`: Percentages for each validation status

## Interpreting the Results

When analyzing the results:

1. **Canonical mappings** (`is_canonical_mapping = True`) represent the preferred mapping for each source entity
2. **Bidirectional matches** are the highest confidence mappings
3. **One-to-many source** flags indicate multiple valid target entities for one source
4. **One-to-many target** flags indicate that multiple source entities map to one target

For statistical analysis and summary counts, use the canonical mappings to avoid double-counting relationships.