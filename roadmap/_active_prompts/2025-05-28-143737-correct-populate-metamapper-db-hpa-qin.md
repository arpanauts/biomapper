# Claude Code Prompt: Correct and Complete populate_metamapper_db.py for HPA and Qin Protein Resources

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-28-143737-correct-populate-metamapper-db-hpa-qin.md`

## 1. Task Overview

The primary task is to correct and complete the Python script `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`. This script populates the `metamapper.db` SQLite database with necessary configurations for the Biomapper project. The goal is to accurately define new protein resources (HPA and Qin) and enable UniProtKB AC to UniProtKB AC identity mappings between these new resources and the existing UKBB protein resource.

A previous attempt to modify this script (reflected in the current state of the file) introduced some correct elements but also contained significant errors and omissions, particularly in the `OntologyCoverage` and `MappingPath` definitions.

## 2. Background Context

The Biomapper project requires mapping protein identifiers from two new CSV files:
*   HPA proteins: `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv` (columns: `gene,uniprot,organ`)
*   Qin proteins: `/home/ubuntu/biomapper/data/isb_osp/qin_osps.csv` (columns: `gene,uniprot,organ`)

These need to be mapped against each other and against the existing UKBB protein resource:
*   UKBB proteins: `/home/ubuntu/biomapper/data/UKBB_Protein_Meta_full.tsv` (UniProt IDs in `UniProt` column, tab-separated)

The mapping strategy involves using the `MappingExecutor`, which relies on `metamapper.db`. Therefore, `populate_metamapper_db.py` must correctly define:
*   `Endpoint`s for HPA and Qin proteins.
*   `MappingResource`s (using `GenericFileLookupClient`) to perform identity lookups within these files based on their UniProt ID columns.
*   `OntologyCoverage` for these new resources.
*   `MappingPath`s to define the six directional identity mappings:
    1.  HPA UniProtKB AC -> Qin UniProtKB AC
    2.  Qin UniProtKB AC -> HPA UniProtKB AC
    3.  HPA UniProtKB AC -> UKBB UniProtKB AC
    4.  UKBB UniProtKB AC -> HPA UniProtKB AC
    5.  Qin UniProtKB AC -> UKBB UniProtKB AC
    6.  UKBB UniProtKB AC -> Qin UniProtKB AC

**Errors from Previous Attempt to Note and Correct:**
*   **`OntologyCoverage`:** This section was entirely missing for the new HPA and Qin lookup resources.
*   **`MappingPath` Attributes:**
    *   Used `source_type` and `target_type` string literals instead of the correct `source_property_id` and `target_property_id` (which should reference the ID of the `UNIPROTKB_AC` `Property` object).
    *   Missed `source_endpoint_id` and `target_endpoint_id` attributes.
    *   Missed `path_type` (should be "DIRECT") and `is_primary_path` (should be `True`) attributes.
    *   Incorrectly included a `priority` attribute directly on `MappingPath` objects.

## 3. Input File to Modify

*   `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`

## 4. Detailed Instructions for Correction and Completion

Please modify `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` within the `populate_data` async function. Ensure all objects are correctly instantiated using models from `biomapper.db.models` and added to the session.

**Reference Variables (ensure these are correctly defined and used):**
*   `ontologies['uniprotkb_ac']`: For `Ontology` object related to UniProtKB AC.
*   `property_uniprotkb_ac`: For the `Property` object representing `UNIPROTKB_AC`. This should be fetched from the `properties` list after they are created.
*   `endpoints['hpa_protein']`, `endpoints['qin_protein']`, `endpoints['ukbb_protein']`: For `Endpoint` objects.
*   `resources['hpa_protein_lookup']`, `resources['qin_protein_lookup']`, `resources['ukbb_protein_lookup']`: For `MappingResource` objects.

**Specific Sections to Add/Correct:**

### 4.1. Endpoints
*   Verify that `Endpoint` objects for "HPA_Protein" and "Qin_Protein" are correctly defined in the `endpoints` dictionary:
    ```python
    # Example structure (already likely present from previous attempt)
    endpoints = {
        # ... other endpoints ...
        "hpa_protein": Endpoint(
            name="HPA_Protein",
            description="HPA Protein Resource (hpa_osps.csv)"
        ),
        "qin_protein": Endpoint(
            name="Qin_Protein",
            description="Qin Protein Resource (qin_osps.csv)"
        ),
        # ... ukbb_protein should also be present ...
    }
    ```

### 4.2. Properties
*   Ensure the `Property` object for `UNIPROTKB_AC` is defined and its ID is accessible (e.g., via `property_uniprotkb_ac.id`). This is likely already correct.

### 4.3. EndpointPropertyConfig
*   Verify that `EndpointPropertyConfig` entries correctly link the `UNIPROTKB_AC` property to the `HPA_Protein` and `Qin_Protein` endpoints. These should be added to the `endpoint_prop_configs` list.
    ```python
    # Example structure (already likely present from previous attempt)
    # Ensure property_uniprotkb_ac is correctly defined and its .id is used
    EndpointPropertyConfig(
        endpoint_id=endpoints["hpa_protein"].id,
        property_id=property_uniprotkb_ac.id, # Use the ID of the UNIPROTKB_AC Property object
        is_primary_identifier=True,
        available_for_mapping=True
    ),
    EndpointPropertyConfig(
        endpoint_id=endpoints["qin_protein"].id,
        property_id=property_uniprotkb_ac.id, # Use the ID of the UNIPROTKB_AC Property object
        is_primary_identifier=True,
        available_for_mapping=True
    ),
    ```

### 4.4. MappingResources
*   Verify `MappingResource` definitions for HPA and Qin protein lookups in the `resources` dictionary. Ensure `client_class_path` is `biomapper.mapping.clients.generic_file_client.GenericFileLookupClient` and `config_template` is accurate:
    ```python
    # Example structure for HPA (Qin similar, UKBB should also exist)
    # (already likely present from previous attempt)
    "hpa_protein_lookup": MappingResource(
        name="HPA_Protein_UniProt_Lookup",
        description="Lookup UniProtKB ACs within HPA Protein CSV",
        client_class_path="biomapper.mapping.clients.generic_file_client.GenericFileLookupClient",
        config_template={
            "file_path": "/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv",
            "key_column": "uniprot",
            "value_column": "uniprot", # For identity lookup
            "delimiter": ","
        },
        resource_type="LOOKUP"
    ),
    "qin_protein_lookup": MappingResource(
        name="Qin_Protein_UniProt_Lookup",
        description="Lookup UniProtKB ACs within Qin Protein CSV",
        client_class_path="biomapper.mapping.clients.generic_file_client.GenericFileLookupClient",
        config_template={
            "file_path": "/home/ubuntu/biomapper/data/isb_osp/qin_osps.csv",
            "key_column": "uniprot",
            "value_column": "uniprot", # For identity lookup
            "delimiter": ","
        },
        resource_type="LOOKUP"
    ),
    ```

### 4.5. OntologyCoverage (CRITICAL ADDITION)
*   **This section was missing.** Add `OntologyCoverage` entries to the `ontology_coverage_configs` list for the new HPA and Qin lookup resources. The existing `UKBB_Protein_UniProt_Lookup` should already have its coverage defined.
    ```python
    # Add to ontology_coverage_configs list:
    OntologyCoverage(
        resource_id=resources["hpa_protein_lookup"].id, # Use ID of the HPA MappingResource
        source_type="UNIPROTKB_AC", # String name of the property/ontology
        target_type="UNIPROTKB_AC", # String name of the property/ontology
        support_level="client_lookup", # Or an appropriate term like "identity_lookup" if preferred, check existing patterns
        # If your model uses source_ontology_id and target_ontology_id, use those:
        # source_ontology_id=ontologies["uniprotkb_ac"].id,
        # target_ontology_id=ontologies["uniprotkb_ac"].id,
        # relationship_type="identity" # If this field exists and is appropriate
    ),
    OntologyCoverage(
        resource_id=resources["qin_protein_lookup"].id, # Use ID of the Qin MappingResource
        source_type="UNIPROTKB_AC",
        target_type="UNIPROTKB_AC",
        support_level="client_lookup",
        # If your model uses source_ontology_id and target_ontology_id, use those:
        # source_ontology_id=ontologies["uniprotkb_ac"].id,
        # target_ontology_id=ontologies["uniprotkb_ac"].id,
        # relationship_type="identity" # If this field exists and is appropriate
    ),
    ```
    *Note: Please check the exact field names (`resource_id` vs `mapping_resource_id`, `source_type` vs `source_ontology_id`, etc.) against the `OntologyCoverage` model definition in `biomapper.db.models` and match existing entries in the script.* The existing entries use `resource_id`, `source_type`, `target_type`, `support_level`.

### 4.6. MappingPaths (CRITICAL CORRECTION)
*   Locate the `MappingPath` definitions in the `paths` dictionary. Correct the six identity mapping paths. Each `MappingPath` object must have:
    *   `name`: A descriptive unique name.
    *   `source_property_id`: The ID of the `UNIPROTKB_AC` `Property` object.
    *   `target_property_id`: The ID of the `UNIPROTKB_AC` `Property` object.
    *   `source_endpoint_id`: The ID of the source `Endpoint` object.
    *   `target_endpoint_id`: The ID of the target `Endpoint` object.
    *   `path_type`: Set to `"DIRECT"`.
    *   `is_primary_path`: Set to `True`.
    *   `description`: A brief description.
    *   `steps`: A list containing a single `MappingPathStep` object. This step object must have:
        *   `mapping_resource_id`: The ID of the relevant `MappingResource` (e.g., for HPA -> Qin, use `qin_protein_lookup.id`).
        *   `step_order`: Set to `1`.
        *   `description`: A brief description of the step.
*   Remove any incorrect attributes like `priority`, `source_type` (as string literal), `target_type` (as string literal) from the `MappingPath` objects themselves.

    ```python
    # Example for one path (HPA_Protein_to_Qin_Protein_UniProt_Identity)
    # Ensure property_uniprotkb_ac, endpoints, and resources variables are correctly referenced for their .id
    "HPA_Protein_to_Qin_Protein_UniProt_Identity": MappingPath(
        name="HPA_Protein_to_Qin_Protein_UniProt_Identity",
        source_property_id=property_uniprotkb_ac.id,
        target_property_id=property_uniprotkb_ac.id,
        source_endpoint_id=endpoints["hpa_protein"].id,
        target_endpoint_id=endpoints["qin_protein"].id,
        path_type="DIRECT",
        is_primary_path=True,
        description="Maps HPA UniProtKB AC to Qin UniProtKB AC if present in Qin data.",
        steps=[
            MappingPathStep(
                mapping_resource_id=resources["qin_protein_lookup"].id, # Use Qin's lookup resource
                step_order=1,
                description="Identity lookup of HPA UniProtKB AC in Qin protein data."
            )
        ]
    ),
    # ... (Define all 6 paths similarly) ...
    # Qin_Protein_to_HPA_Protein_UniProt_Identity (uses hpa_protein_lookup.id)
    # HPA_Protein_to_UKBB_Protein_UniProt_Identity (uses ukbb_protein_lookup.id)
    # UKBB_Protein_to_HPA_Protein_UniProt_Identity (uses hpa_protein_lookup.id)
    # Qin_Protein_to_UKBB_Protein_UniProt_Identity (uses ukbb_protein_lookup.id)
    # UKBB_Protein_to_Qin_Protein_UniProt_Identity (uses qin_protein_lookup.id)
    ```

### 4.7. OntologyPreferences
*   Verify `OntologyPreference` entries for HPA and Qin are present in the `preferences` list, prioritizing `UNIPROTKB_AC`.
    ```python
    # Example structure (already likely present from previous attempt)
    OntologyPreference(
        endpoint_id=endpoints["hpa_protein"].id,
        ontology_name="UNIPROTKB_AC", # String name of the ontology/property
        priority=1,
    ),
    OntologyPreference(
        endpoint_id=endpoints["qin_protein"].id,
        ontology_name="UNIPROTKB_AC",
        priority=1,
    ),
    ```

## 5. Expected Outcome

A corrected `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py` script that, when run, successfully populates `metamapper.db` with all necessary configurations for the HPA and Qin protein resources and their identity mappings with each other and the UKBB resource. The script should run without errors.

## 6. Important Considerations

*   **Adherence to Existing Patterns:** Ensure new definitions follow the structural and naming conventions already present in the script.
*   **Model Accuracy:** Double-check all attribute names against the actual SQLAlchemy model definitions in `biomapper.db.models`.
*   **Variable Scope:** Ensure all IDs (e.g., `property_uniprotkb_ac.id`, `endpoints["hpa_protein"].id`, `resources["hpa_protein_lookup"].id`) are correctly referenced after the respective objects have been flushed to the session (if IDs are auto-generated). The current script structure typically adds all objects of a type and then flushes.
*   **Idempotency:** The script already includes a `delete_existing_db()` function, so it's designed to be re-runnable.

## 7. Reference Project Memories / Context

*   The overall goal is to enable protein-to-protein mapping using new resources (`hpa_osps.csv`, `qin_osps.csv`) and the existing UKBB resource.
*   Relevant Memory: MEMORY[140ad7b0-e133-4771-a738-07e4b4926be6] (Enhance `populate_metamapper_db.py`), MEMORY[87598b65-0bf2-40c3-be97-ad15baf90c5f] (UKBB file details).
*   This task directly follows a previous, partially successful attempt to modify the script, and aims to fix the identified errors.

## 8. Feedback File Generation

Upon completion of the task (successful or otherwise), you **must** create a feedback Markdown file in the following directory:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/`

**Naming Convention:** Use the format `YYYY-MM-DD-HHMMSS-feedback-populate-metamapper-db-hpa-qin.md` (using the UTC timestamp of when you complete the task).

**Content of the Feedback File:**
*   **Source Prompt:** Reference the full path to this prompt file: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-28-143737-correct-populate-metamapper-db-hpa-qin.md`
*   **Summary of Actions:** Briefly describe the changes made to `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`.
*   **Outcome:** State whether the script was successfully corrected and completed according to the instructions.
*   **Verification:** Confirm if the script is expected to run without errors after your changes.
*   **Errors Encountered (if any):** Detail any errors or issues encountered during the modification process.
*   **Path to Modified File:** `/home/ubuntu/biomapper/scripts/populate_metamapper_db.py`
*   **Open Questions/Notes (if any):** Any clarifications needed or important observations.

This feedback file is crucial for the project management workflow.

