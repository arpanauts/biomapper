# Task List: Debug UKBB to HPA Protein Mapping Failures

## Phase 1: Configuration and Data Validation (as per design.md)

-   [ ] **Task 1.1: Validate `populate_metamapper_db.py` - UKBB Endpoint**
    -   [ ] Verify `name`, `description`.
    -   [ ] Verify `connection_details` (path to `UKBB_Protein_Meta.tsv` or `UKBB_Protein_Meta_head.tsv`).
    -   [ ] Verify `primary_property_name` ("UNIPROTKB_AC").
-   [ ] **Task 1.2: Validate `populate_metamapper_db.py` - HPA Endpoint (`hpa_protein`)**
    -   [ ] Verify `name`, `description`.
    -   [ ] Verify `connection_details` (path to `hpa_osps.csv`).
    -   [ ] Verify `primary_property_name` ("UNIPROTKB_AC").
-   [ ] **Task 1.3: Validate `populate_metamapper_db.py` - HPA Protein Lookup Resource (`hpa_protein_lookup`)**
    -   [ ] Verify `client_class_path` (`biomapper.mapping.clients.generic_file_client.GenericFileLookupClient`).
    -   [ ] Verify `config_template`:
        -   [ ] `file_path` (to `hpa_osps.csv`).
        -   [ ] `key_column` ("uniprot").
        -   [ ] `value_column` ("uniprot").
        -   [ ] `delimiter` (",").
-   [ ] **Task 1.4: Validate `populate_metamapper_db.py` - UKBB PropertyExtractionConfig**
    -   [ ] Verify `ontology_type` ("UNIPROTKB_AC"), `property_name` ("PrimaryIdentifier").
    -   [ ] Verify `extraction_method` ("column").
    -   [ ] Verify `extraction_pattern` (json for `{"column_name": "UniProt"}`).
-   [ ] **Task 1.5: Validate `populate_metamapper_db.py` - MappingPath (`UKBB_Protein_to_HPA_Protein_UniProt_Identity`)**
    -   [ ] Verify `source_type`, `target_type` (both "UNIPROTKB_AC").
    -   [ ] Verify `mapping_resource_id` in steps points to `hpa_protein_lookup`.
-   [ ] **Task 1.6: Validate UKBB Input Data (`UKBB_Protein_Meta_head.tsv`)**
    -   [ ] Confirm presence and correct naming of "UniProt" column.
    -   [ ] Extract a few sample UniProt IDs.
-   [ ] **Task 1.7: Validate HPA Lookup Data (`hpa_osps.csv`)**
    -   [ ] Confirm presence and correct naming of "uniprot" column.
    -   [ ] Check if sample UniProt IDs from UKBB (Task 1.6) exist in this file.

## Phase 2: Script Logic and Execution (`map_ukbb_to_hpa.py`)

-   [ ] **Task 2.1: Review `MappingExecutor` Invocation**
    -   [ ] Check how `MappingExecutor` is initialized.
    -   [ ] Check how `execute_mappings_for_ids` is called (input IDs, source/target endpoint names).
-   [ ] **Task 2.2: Add/Enhance Logging**
    -   [ ] Log input IDs passed to `execute_mappings_for_ids`.
    -   [ ] Log the raw results from `execute_mappings_for_ids`.
    -   [ ] Log any exceptions or errors encountered during mapping.
-   [ ] **Task 2.3: Analyze Claude Code Instance Feedback**
    -   [ ] Once the feedback file is available, review its findings and incorporate them.

## Phase 3: Resolution and Verification

-   [ ] **Task 3.1: Implement Fixes**
    -   [ ] Based on findings from Phase 1 & 2, modify code or configurations.
-   [ ] **Task 3.2: Re-run `map_ukbb_to_hpa.py` with Test Data**
    -   [ ] Verify if mappings are now successful (Acceptance Criterion AC1).
-   [ ] **Task 3.3: Document Root Cause and Changes**
    -   [ ] Update `implementation_notes.md` with findings (Acceptance Criterion AC2).
    -   [ ] Ensure changes are committed (Acceptance Criterion AC3).
