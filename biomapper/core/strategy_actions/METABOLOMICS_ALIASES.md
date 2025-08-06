# Metabolomics Action Aliases

This document describes the action aliases created for metabolomics workflows.

## Overview

To make metabolomics strategies more intuitive and domain-specific, we've created aliases that map to existing general-purpose actions. These aliases provide clearer naming conventions for metabolomics-specific use cases while leveraging the same underlying functionality.

## Aliases

### METABOLITE_NAME_MATCH
- **Maps to**: BASELINE_FUZZY_MATCH
- **Purpose**: Direct metabolite name matching using fuzzy string comparison
- **Use Cases**:
  - Matching metabolite names between datasets
  - Finding compounds with similar names
  - Initial pass matching before enrichment
- **Parameters**: Exactly the same as BASELINE_FUZZY_MATCH

### ENRICHED_METABOLITE_MATCH  
- **Maps to**: VECTOR_ENHANCED_MATCH
- **Purpose**: Match metabolites using enriched data (synonyms, IUPAC names, InChI keys)
- **Use Cases**:
  - Matching after API enrichment
  - Semantic similarity matching
  - Cross-database harmonization
- **Parameters**: Same as VECTOR_ENHANCED_MATCH

### METABOLITE_API_ENRICHMENT
- **Maps to**: CTS_ENRICHED_MATCH (extended version)
- **Purpose**: Enrich metabolite data using multiple chemical databases
- **New Features**: 
  - Support for HMDB, PubChem, ChemSpider in addition to CTS
  - Configurable API selection per dataset
  - Parallel API processing
  - Comprehensive error handling
- **Parameters**: Extended version of CTS_ENRICHED_MATCH params

## Example Usage

### Basic Metabolite Name Matching
```yaml
- name: direct_metabolite_match
  action:
    type: METABOLITE_NAME_MATCH  # Alias for BASELINE_FUZZY_MATCH
    params:
      source_dataset_key: "metabolites"
      target_dataset_key: "reference"
      source_column: "name"
      target_column: "compound_name"
      threshold: 0.85
      output_key: "name_matches"
      unmatched_key: "unmatched.baseline"
```

### Multi-API Enrichment
```yaml
- name: multi_api_metabolite_enrichment
  action:
    type: METABOLITE_API_ENRICHMENT
    params:
      unmatched_dataset_key: "unmatched_metabolites"
      target_dataset_key: "reference_metabolites"
      target_column: "unified_name"
      api_services:
        - service: "hmdb"
          input_column: "HMDB_ID"
          output_fields: ["name", "synonyms", "iupac_name", "inchikey"]
          timeout: 30
        - service: "pubchem"
          input_column: "PUBCHEM_CID"
          output_fields: ["name", "synonyms", "inchikey"]
          timeout: 30
          id_type: "cid"
        - service: "cts"
          input_column: "KEGG_ID"
          output_fields: ["chemical_name", "synonyms"]
          timeout: 20
      match_threshold: 0.8
      batch_size: 50
      cache_results: true
      output_key: "api_enriched_matches"
```

### Enriched Metabolite Matching
```yaml
- name: semantic_metabolite_match
  action:
    type: ENRICHED_METABOLITE_MATCH  # Alias for VECTOR_ENHANCED_MATCH
    params:
      unmatched_dataset_key: "unmatched.api"
      target_dataset_key: "reference"
      source_text_columns: ["name", "synonyms", "iupac_name"]
      target_text_columns: ["unified_name", "alternative_names"]
      similarity_threshold: 0.85
      output_key: "semantic_matches"
```

## Complete Example Strategy

Here's a complete metabolomics harmonization strategy using the aliases:

```yaml
name: metabolomics_harmonization_with_aliases
description: "Harmonize metabolomics data using metabolite-specific action aliases"
steps:
  # Step 1: Load datasets
  - name: load_source_metabolites
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${DATA_DIR}/source_metabolites.csv"
        dataset_key: "source"
        
  - name: load_reference_metabolites
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${DATA_DIR}/reference_metabolites.csv"
        dataset_key: "reference"
  
  # Step 2: Direct name matching
  - name: baseline_match
    action:
      type: METABOLITE_NAME_MATCH
      params:
        source_dataset_key: "source"
        target_dataset_key: "reference"
        source_column: "compound_name"
        target_column: "name"
        threshold: 0.9
        output_key: "baseline_matches"
        unmatched_key: "unmatched.baseline"
  
  # Step 3: API enrichment for unmatched
  - name: enrich_unmatched
    action:
      type: METABOLITE_API_ENRICHMENT
      params:
        unmatched_dataset_key: "unmatched.baseline"
        target_dataset_key: "reference"
        target_column: "name"
        api_services:
          - service: "hmdb"
            input_column: "hmdb_id"
            output_fields: ["name", "synonyms", "iupac_name"]
          - service: "pubchem"
            input_column: "pubchem_cid"
            output_fields: ["name", "synonyms"]
            id_type: "cid"
        output_key: "api_matches"
        unmatched_key: "unmatched.api"
  
  # Step 4: Semantic matching for remaining unmatched
  - name: semantic_match
    action:
      type: ENRICHED_METABOLITE_MATCH
      params:
        unmatched_dataset_key: "unmatched.api"
        target_dataset_key: "reference"
        source_text_columns: ["compound_name", "hmdb_enriched_names", "pubchem_enriched_names"]
        target_text_columns: ["name", "synonyms"]
        similarity_threshold: 0.8
        output_key: "semantic_matches"
  
  # Step 5: Merge all matches
  - name: merge_results
    action:
      type: MERGE_DATASETS
      params:
        dataset_keys: ["baseline_matches", "api_matches", "semantic_matches"]
        output_key: "final_harmonized"
```

## Benefits of Using Aliases

1. **Clarity**: Action names clearly indicate their metabolomics-specific purpose
2. **Consistency**: Standardized naming across metabolomics workflows
3. **Maintainability**: Changes to underlying actions automatically apply to aliases
4. **Discoverability**: Easier for metabolomics researchers to find relevant actions
5. **Backward Compatibility**: Original action names still work

## Implementation Notes

- Aliases are created in `biomapper/core/strategy_actions/__init__.py`
- They share the exact same implementation as their target actions
- No code duplication - aliases simply point to existing action classes
- All parameters and functionality remain identical
- Documentation and examples can use either name interchangeably

## Future Aliases

Potential future metabolomics-specific aliases:
- `METABOLITE_STRUCTURE_MATCH`: For InChI/SMILES-based matching
- `METABOLITE_MASS_MATCH`: For mass spectrometry data matching
- `METABOLITE_PATHWAY_ENRICH`: For pathway-based enrichment
- `METABOLITE_CROSS_REFERENCE`: For cross-database ID mapping