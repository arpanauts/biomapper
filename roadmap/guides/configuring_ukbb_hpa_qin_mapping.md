# Guide: Configuring Protein Mapping for UKBB, HPA, and QIN Datasets

## 1. Introduction

This document provides guidance on configuring Biomapper for protein mapping between the UK Biobank (UKBB), Human Protein Atlas (HPA), and QIN Proteomics (QIN) datasets. These datasets share common characteristics that influence the optimal mapping strategy, primarily their comprehensive coverage of UniProt Accession numbers (UniProt ACs) and the necessity of resolving historical UniProt IDs.

This guide is intended for developers and data curators responsible for setting up or augmenting the `protein_config.yaml` (or a similar entity-specific configuration file) to enable robust mapping for these sources.

It assumes familiarity with the core Biomapper configuration concepts outlined in `configs/README.md` and the YAML-Defined Mapping Strategies detailed in `roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`.

## 2. Core Characteristics of UKBB, HPA, and QIN Protein Datasets

Understanding these characteristics is key to effective configuration:

*   **"UniProt-Complete":** These datasets have near-complete annotation with UniProt ACs for their protein entities. This makes UniProt AC the natural Primary Shared Ontology (PSO) for mapping between them.
*   **Mandatory UniProt Historical ID Resolution:** A critical step in maximizing mapping recall is the resolution of UniProt ACs through the UniProt API (or a similar service). This handles cases where UniProt IDs have become secondary, merged, demerged, or obsolete. This is not an optional enhancement but a core requirement for these datasets (see MEMORY[f09ede1e-390a-49dc-b881-513aebc117b5]).
*   **Native Identifiers:** While UniProt AC is the bridge, each dataset has its own native primary identifiers (e.g., Ensembl Gene IDs for HPA, Assay IDs for UKBB) which are the typical starting and ending points for mapping queries.
*   **Provenance:** Capturing detailed provenance from each mapping step, especially the UniProt resolution metadata (e.g., 'primary', 'secondary:P12345', 'demerged', 'obsolete'), is essential.

## 3. Key Sections in `protein_config.yaml`

When configuring for UKBB, HPA, and QIN, pay close attention to these sections in your `protein_config.yaml`:

### 3.1. `entity_type` and `version`
   - Ensure these are appropriately set (e.g., `entity_type: protein`).

### 3.2. `ontologies`
   - Define all relevant ontology types:
     *   The primary native identifier ontology for HPA (e.g., `HPA_PROTEIN_NATIVE_ID_ONTOLOGY`).
     *   The primary native identifier ontology for QIN (e.g., `QIN_PROTEIN_NATIVE_ID_ONTOLOGY`).
     *   The primary native identifier ontology for UKBB (e.g., `UKBB_PROTEIN_NATIVE_ID_ONTOLOGY`).
     *   The shared UniProt AC ontology (e.g., `PROTEIN_UNIPROTKB_AC_ONTOLOGY`).
     *   Any other relevant secondary identifiers if used in advanced strategies.

### 3.3. `databases` (Endpoints)
   - Define an endpoint for HPA, QIN, and UKBB protein data.
   - For each endpoint:
     *   `endpoint_name`: A unique name (e.g., `HPA_PROTEIN_ENDPOINT`).
     *   `description`.
     *   `data_file_path`: Path to the dataset file (resolvable with `${DATA_DIR}`).
     *   `properties`: Map column names in the data file to the `ontology_type`s defined above. Ensure correct mapping for native IDs and UniProt AC columns.
     *   `mapping_clients`:
       *   **Crucially, configure the `UniProtHistoricalResolverClient`**. This client will be invoked via a `mapping_path`.
         ```yaml
         # Example client configuration within an endpoint (or globally if shared)
         mapping_clients:
           UNIPROT_HISTORY_RESOLVER:
             class_path: "biomapper.mapping.clients.uniprot_historical_resolver_client.UniProtHistoricalResolverClient"
             description: "Resolves historical UniProt IDs via UniProt API."
             config: # Optional: if defaults for cache_size, base_url, timeout are not sufficient
               cache_size: 20000
               # base_url: ...
               # timeout: ...
             input_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
             output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
         ```

### 3.4. `mapping_paths`
   - Define an atomic `mapping_path` specifically for invoking the UniProt historical resolution client.
     ```yaml
     mapping_paths:
       - name: "RESOLVE_UNIPROT_HISTORY_VIA_API"
         description: "Takes UniProt ACs and returns current primary UniProt ACs after resolving history."
         source_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
         target_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
         steps:
           - resource: "UNIPROT_HISTORY_RESOLVER" # Matches client name above
             # No specific method needed if client's default 'map_identifiers' is used
     ```

### 3.5. `mapping_strategies`
   - This is where you will define the explicit multi-step pipelines for mapping between these datasets.

## 4. Defining Mapping Strategies for UKBB-HPA-QIN

Mapping between any pair of these datasets (e.g., HPA to UKBB) will typically follow this sequence, orchestrated by a YAML-defined strategy:

1.  **Source Native ID to Source UniProt AC:** Convert the input native identifiers of the source dataset to their corresponding UniProt ACs using local data within the source endpoint.
    *   `action.type: CONVERT_IDENTIFIERS_LOCAL`
2.  **Resolve UniProt History:** Take the UniProt ACs from step 1 and resolve them using the UniProt API (via the `RESOLVE_UNIPROT_HISTORY_VIA_API` mapping path defined earlier).
    *   `action.type: EXECUTE_MAPPING_PATH`
3.  **Match Resolved UniProt ACs in Target:** Filter the resolved UniProt ACs from step 2, keeping only those present in the target dataset's UniProt AC column.
    *   `action.type: FILTER_IDENTIFIERS_BY_TARGET_PRESENCE` (or a similar custom action if more complex matching logic is needed).
4.  **Target UniProt AC to Target Native ID:** Convert the matching UniProt ACs (now known to be current and present in the target) to the target dataset's native identifiers using local data within the target endpoint.
    *   `action.type: CONVERT_IDENTIFIERS_LOCAL`

**Example Strategy (Conceptual HPA to UKBB):**

```yaml
# In protein_config.yaml
mapping_strategies:
  HPA_TO_UKBB_PROTEIN_PIPELINE:
    description: "Maps HPA native protein IDs to UKBB native protein IDs, including UniProt historical resolution."
    default_source_ontology_type: "HPA_PROTEIN_NATIVE_ID_ONTOLOGY" # Example name
    default_target_ontology_type: "UKBB_PROTEIN_NATIVE_ID_ONTOLOGY" # Example name
    steps:
      - step_id: "S1_HPA_NATIVE_TO_UNIPROT"
        description: "Convert HPA native IDs to HPA UniProt ACs."
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "SOURCE"
          output_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"

      - step_id: "S2_RESOLVE_UNIPROT_HISTORY"
        description: "Resolve UniProt ACs via UniProt API for currency."
        action:
          type: "EXECUTE_MAPPING_PATH"
          path_name: "RESOLVE_UNIPROT_HISTORY_VIA_API"

      - step_id: "S3_MATCH_RESOLVED_UNIPROT_IN_UKBB"
        description: "Filter resolved UniProt ACs by presence in UKBB UniProt data."
        action:
          type: "FILTER_IDENTIFIERS_BY_TARGET_PRESENCE"
          endpoint_context: "TARGET"
          ontology_type_to_match: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"

      - step_id: "S4_UKBB_UNIPROT_TO_NATIVE"
        description: "Convert matching UKBB UniProt ACs to UKBB native IDs."
        action:
          type: "CONVERT_IDENTIFIERS_LOCAL"
          endpoint_context: "TARGET"
          input_ontology_type: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
          output_ontology_type: "{{STRATEGY_TARGET_ONTOLOGY_TYPE}}"
```

## 5. Developing New `action.type` Methods (If Needed)

While the initial set of `action.type`s (`CONVERT_IDENTIFIERS_LOCAL`, `EXECUTE_MAPPING_PATH`, `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`) should cover many scenarios, you might encounter a need for a new, reusable primitive operation.

If so, follow the process outlined in `roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`:
1.  **Identify Need:** Determine if the operation is truly a new primitive and likely reusable.
2.  **Define `action.type`:** Choose a clear, descriptive string for the new action.
3.  **Implement Handler:** Create a Python handler module for this action (e.g., in `biomapper/core/strategy_actions/`). This module will contain the logic to perform the action, taking necessary parameters from the YAML step definition.
4.  **Document:** Thoroughly document the new `action.type`, its parameters, and its behavior.

## 6. Provenance and Bidirectional Mapping

*   **Provenance:** Ensure that the `MappingExecutor` and individual action handlers are designed to propagate provenance information. The output of a mapping strategy should ideally include not just the final mapped ID, but also how it was derived (e.g., "Resolved from P12345 (secondary) via UniProt API").
*   **Bidirectional Context:** The strategies defined here represent unidirectional mapping (e.g., HPA -> UKBB). For robust results, these will form one leg of a bidirectional mapping process. A separate reconciliation phase will compare the HPA->UKBB and UKBB->HPA results.

## 7. Key Files for Reference

*   `/home/ubuntu/biomapper/configs/README.md` (General configuration structure)
*   `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md` (Detailed explanation of YAML strategies and `action.type`s)
*   `/home/ubuntu/biomapper/configs/protein_config.yaml` (The actual configuration file to be augmented)

This guide provides a targeted approach for these specific datasets. Always refer to the core documentation for foundational concepts and adapt as needed for new requirements or datasets.
