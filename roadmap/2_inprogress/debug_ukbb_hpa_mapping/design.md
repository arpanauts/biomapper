# Design: Debug UKBB to HPA Protein Mapping Failures

## 1. Approach
The debugging process will be iterative, focusing on verifying each component of the mapping pipeline:

1.  **Configuration Validation (`populate_metamapper_db.py`):**
    *   Verify `Endpoint` definitions for UKBB and HPA:
        *   Correct `name`, `description`.
        *   Accurate `connection_details` (file paths, API endpoints).
        *   Correct `primary_property_name`.
    *   Verify `MappingResource` definitions (especially `hpa_protein_lookup`):
        *   Correct `client_class_path`.
        *   Accurate `config_template` (file path, key/value columns, delimiter).
    *   Verify `PropertyExtractionConfig` for UKBB `UNIPROTKB_AC`:
        *   Correct `ontology_type`, `property_name`.
        *   Correct `extraction_method` and `extraction_pattern` (e.g., column name "UniProt").
    *   Verify `MappingPath` ("UKBB_Protein_to_HPA_Protein_UniProt_Identity"):
        *   Correct `source_type`, `target_type`.
        *   Correct `mapping_resource_id` in steps.

2.  **Data Validation:**
    *   Inspect the UKBB input file (`UKBB_Protein_Meta_head.tsv`):
        *   Confirm presence and format of the "UniProt" column.
        *   Check a few sample UniProt IDs.
    *   Inspect the HPA lookup file (`hpa_osps.csv`):
        *   Confirm presence and format of the "uniprot" column.
        *   Check if sample UniProt IDs from UKBB data exist in this file.

3.  **Script Logic (`map_ukbb_to_hpa.py`):**
    *   Review how `MappingExecutor` is initialized and called.
    *   Add verbose logging around the mapping execution call to trace input IDs and results.
    *   Potentially step through the `MappingExecutor.execute_mappings_for_ids` method if direct logging is insufficient.

4.  **Claude Code Instance:**
    *   The currently running Claude Code instance was tasked with performing some of these steps. Its feedback will be crucial.

## 2. Tools & Techniques
-   Manual inspection of configuration files and data files.
-   Python `print()` statements or `logging` module for verbose output in scripts.
-   Claude Code instance for automated analysis and potential code modification.
-   Comparison of UniProt IDs between datasets.

## 3. Expected Outcome
A clear understanding of why mappings are failing, and implemented changes that lead to successful mappings for the test dataset.
