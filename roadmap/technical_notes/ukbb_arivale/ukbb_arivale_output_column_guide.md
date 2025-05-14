# Phase 3 Output Column Guide

This document provides a comprehensive guide to understanding the columns in the `phase3_bidirectional_reconciliation_results.tsv` output file, which represents the final reconciled mapping between UKBB and Arivale protein identifiers.

## Source UKBB Columns

These columns contain information from the original UKBB input dataset:

### source_ukbb_assay_raw
- **Data Type**: String
- **Source**: Directly from UKBB input
- **Description**: The raw assay identifier from the UKBB dataset, represents a unique protein measurement in the UK Biobank
- **Significance**: Primary identifier for UKBB proteins, used as the starting point for forward mapping

### source_ukbb_uniprot_ac
- **Data Type**: String
- **Source**: Directly from UKBB input
- **Description**: The UniProt accession number associated with the UKBB assay
- **Significance**: Used for direct UniProt-based mapping to Arivale identifiers

### source_ukbb_panel
- **Data Type**: String
- **Source**: Directly from UKBB input
- **Description**: The panel or category of the protein in the UKBB dataset (e.g., "Inflammation", "Cardiometabolic")
- **Significance**: Provides context for the protein's biological function or measurement group

### source_ukbb_parsed_gene_name
- **Data Type**: String
- **Source**: Directly from UKBB input or derived by parsing
- **Description**: The gene name associated with the protein, extracted or parsed from UKBB data
- **Significance**: Used for gene name-based mapping and verification

## Forward Mapping Columns (Phase 1)

These columns contain information about the forward mapping from UKBB to Arivale:

### mapping_method
- **Data Type**: String
- **Source**: Generated during Phase 1 forward mapping
- **Description**: The method used to map from UKBB to Arivale (e.g., "Direct Primary: UniProt to Arivale", "Secondary: Gene Symbol")
- **Possible Values**: "Direct Primary", "Secondary", "Via Historical", etc.
- **Significance**: Indicates the strategy and path used for mapping, affects confidence and interpretation

### mapping_path_details_json
- **Data Type**: JSON String
- **Source**: Generated during Phase 1 forward mapping
- **Description**: Detailed information about the mapping path, including specific steps and intermediate IDs
- **Significance**: Provides a trace of exactly how the mapping was performed and what resources were consulted

### confidence_score
- **Data Type**: Float (0.0-1.0)
- **Source**: Generated during Phase 1 forward mapping
- **Description**: A score indicating the confidence in the forward mapping, with 1.0 representing highest confidence
- **Significance**: Used to assess reliability of mappings and prioritize results

### hop_count
- **Data Type**: Integer
- **Source**: Generated during Phase 1 forward mapping
- **Description**: The number of intermediary steps or "hops" required to establish the mapping
- **Significance**: Generally, fewer hops indicate a more direct and potentially more reliable mapping

## Target Arivale Columns

These columns contain information about the mapped Arivale entities:

### mapping_step_1_target_arivale_protein_id
- **Data Type**: String
- **Source**: Result of Phase 1 mapping or directly from Arivale input in Phase 2
- **Description**: The Arivale protein identifier that was mapped to from UKBB, or the source Arivale ID in reverse mapping
- **Significance**: Primary identifier for Arivale proteins, central to establishing cross-platform mapping

### mapping_step_1_target_arivale_uniprot_ac
- **Data Type**: String
- **Source**: Arivale metadata from Phase 2
- **Description**: The UniProt accession number associated with the Arivale protein ID in the original Arivale metadata
- **Significance**: Used for direct UniProt-based mapping and historical ID resolution

### mapping_step_1_target_arivale_gene_symbol
- **Data Type**: String
- **Source**: Arivale metadata from Phase 2
- **Description**: The gene symbol associated with the Arivale protein
- **Significance**: Used for gene symbol-based mapping and validation

### mapping_step_1_target_arivale_protein_name
- **Data Type**: String
- **Source**: Arivale metadata from Phase 2
- **Description**: The descriptive name of the protein in the Arivale dataset
- **Significance**: Provides biological context and helps with manual verification of mapping accuracy

## Reverse Mapping Columns (Phase 2)

These columns contain information about the reverse mapping from Arivale back to UKBB:

### reverse_mapping_ukbb_assay
- **Data Type**: String
- **Source**: Result of Phase 2 reverse mapping
- **Description**: The UKBB assay ID that was mapped to from Arivale during reverse mapping
- **Significance**: Used to verify bidirectionality of the mapping

### reverse_mapping_method
- **Data Type**: String
- **Source**: Generated during Phase 2 reverse mapping
- **Description**: The method used to map from Arivale back to UKBB
- **Significance**: Indicates the strategy used for reverse mapping, which may differ from forward mapping

## Historical UniProt Resolution Columns

These columns provide information about any historical UniProt ID resolution performed during mapping:

### arivale_uniprot_historical_resolution
- **Data Type**: Boolean
- **Source**: Derived during Phase 2 or Phase 3 from mapping details
- **Description**: Indicates whether the Arivale UniProt ID needed historical resolution (was outdated/obsolete)
- **Possible Values**: true, false, NULL
- **Significance**: Flags cases where additional resolution steps were needed due to outdated identifiers

### arivale_uniprot_resolved_ac
- **Data Type**: String
- **Source**: Result of UniProt historical ID resolution in Phase 2
- **Description**: The current/active UniProt accession that the historical Arivale UniProt ID resolves to
- **Significance**: The actual up-to-date UniProt ID used for successful mapping after resolution

### arivale_uniprot_resolution_type
- **Data Type**: String
- **Source**: Derived from UniProt API responses during historical resolution
- **Description**: Indicates the type of identifier change that occurred
- **Possible Values**: "demerged", "secondary", "merged", "other"
- **Significance**: Helps understand the nature of the identifier change:
  - **demerged**: Original entry was split into multiple entries
  - **secondary**: Original ID is now a secondary identifier pointing to another primary AC
  - **merged**: Original entry was merged with another entry
  - **other**: Other types of changes or unclassified changes

## Bidirectional Validation Columns (Phase 3)

These columns contain the results of bidirectional validation:

### bidirectional_validation_status
- **Data Type**: String
- **Source**: Generated during Phase 3 reconciliation
- **Description**: The overall validation status of the mapping after considering both directions
- **Possible Values**:
  - "Validated: Bidirectional exact match"
  - "Validated: Forward mapping only"
  - "Validated: Reverse mapping only"
  - "Conflict: Different mappings in forward and reverse directions"
  - "Unmapped: No successful mapping found"
- **Significance**: Primary indicator of mapping quality and bidirectional consistency

### bidirectional_validation_details
- **Data Type**: JSON String
- **Source**: Generated during Phase 3 reconciliation
- **Description**: Detailed information about the validation process and results, including reasons for specific validation statuses
- **Significance**: Provides explanatory context for the validation status, especially useful for debugging conflicts

### combined_confidence_score
- **Data Type**: Float (0.0-1.0)
- **Source**: Generated during Phase 3 reconciliation
- **Description**: A confidence score that takes into account both forward and reverse mapping confidence
- **Significance**: Provides an overall assessment of mapping quality after bidirectional validation:
  - Increased for bidirectional matches
  - Same as forward confidence for forward-only mappings
  - Decreased for conflicts
  - Zero for unmapped entries