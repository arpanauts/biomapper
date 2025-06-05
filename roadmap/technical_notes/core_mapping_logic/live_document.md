# Live Document: Core Mapping Logic Discussion (Iterative Strategy & Configuration)

This document captures ongoing discussion points, clarifications, and decisions related to Biomapper's core iterative mapping strategy and its configuration, particularly concerning protein mapping and the `MappingExecutor`.

## Key Discussion Areas (June 4, 2025)

### 1. Primary Shared Ontology (PSO) Strategy

*   **Confirmation of PSO:**
    *   Is `PROTEIN_UNIPROTKB_AC_ONTOLOGY` the designated PSO for all HPA-QIN-UKBB protein mapping scenarios (HPA<->QIN, QIN<->UKBB, HPA<->UKBB)? For these "UniProt-complete" datasets, this PSO is central.
*   **PSO Determination by `MappingExecutor`:**
    *   How does the `MappingExecutor` determine or utilize the PSO when executing a mapping?
    *   What is the role of `EndpointRelationship` definitions (e.g., `HPA_OSP_PROTEIN_TO_UKBB_PROTEIN`) and their associated `primary_shared_ontology` fields in `protein_config.yaml`?
    *   How does `OntologyPreference` (defined under `ontology_preferences` in `protein_config.yaml`) influence this?
    *   Is this information automatically used by the executor, or does it need to be implicitly managed through `execute_mapping` parameters?
*   **Initial PSO-Based Mapping (e.g., UniProt to UniProt):**
    *   When mapping based on a PSO (e.g., UniProt ACs from a source context to UniProt ACs in a target context), is the initial conceptual step a direct identifier match (akin to a set intersection)?
    *   How does the `MappingExecutor` implement this "direct match" to link a source entity to a target entity via the PSO, before attempting to retrieve the *final desired target ontology type*?
    *   For UniProt-complete datasets, this involves converting the source's native ID to its UniProt AC (if different), then matching this UniProt AC to those in the target's context.

### 2. `MappingExecutor.execute_mapping` Parameters Deep Dive

*   **Clarification of Parameter Roles and Interactions:**
    *   `source_endpoint_name`, `target_endpoint_name`: Define the specific endpoint configurations (from `protein_config.yaml` via `metamapper.db`) to use.
    *   `source_ontology_type`: Specifies the ontology type of the `input_identifiers`.
    *   `target_ontology_type`: Specifies the desired final ontology type of the mapped identifiers from the target endpoint.
    *   `source_property_name`, `target_property_name`:
        *   How do these parameters precisely link to the structure of `protein_config.yaml`, specifically the keys within an endpoint's `properties.mappings` section or the `column` names defined there?
        *   What is their behavior if `source_ontology_type` and `target_ontology_type` are already explicitly provided? Do they override, supplement, or are they ignored?
        *   What happens if these are left to their default (`"PrimaryIdentifier"`)? How does the executor attempt to find a property named "PrimaryIdentifier"?
*   **Linking Parameters to Data Columns:**
    *   How does the `MappingExecutor` use the combination of these parameters to ultimately identify the correct data columns (e.g., "gene", "UniProt", "Assay_ID") from the source/target data files (as configured in `connection_details` and `properties.mappings`)?

### 3. Iterative Mapping Steps in HPA-QIN-UKBB Context

*   **Step 2 (Direct Primary Mapping using PSO):**
    *   If HPA OSP's native primary ID is Ensembl Gene (`HPA_OSP_ proteína_ID_ONTOLOGY`) but the agreed PSO for HPA-UKBB mapping is UniProt AC (`PROTEIN_UNIPROTKB_AC_ONTOLOGY`), how does this step behave when mapping from HPA OSP?
    *   Is this step effectively skipped if the `source_ontology_type` (e.g., HPA's Ensembl Gene ID) is different from the PSO?
*   **Step 4 (Source ID -> PSO Conversion):**
    *   How does the executor select and prioritize `MappingPath`s for converting a source's native/input ID (e.g., HPA's Ensembl Gene ID) to the PSO (e.g., UniProt AC)?
    *   Does this rely purely on `mapping_paths` defined in `protein_config.yaml`, or can it also use `mapping_clients` directly if a relevant client is configured for the source endpoint's property?
    *   Example path needed: `HPA_OSP_PROTEIN_ID_ONTOLOGY` -> `PROTEIN_UNIPROTKB_AC_ONTOLOGY`.
*   **Step 5 (Derived PSO ID -> Target's Desired Ontology Type):**
    *   Once a PSO ID is derived (e.g., UniProt AC derived from HPA's Ensembl Gene ID), how does the executor use this to map to the *target's final desired ontology type* (e.g., `UKBB_PROTEIN_ASSAY_ID_ONTOLOGY`)?
    *   Example path needed: `PROTEIN_UNIPROTKB_AC_ONTOLOGY` (derived from HPA) -> `UKBB_PROTEIN_ASSAY_ID_ONTOLOGY`.

### 4. `protein_config.yaml` Structure and `MappingExecutor` Interaction

*   **`endpoint.properties.primary`:**
    *   What is the precise role of this field if `MappingExecutor.execute_mapping` parameters (like `source_ontology_type` or `source_property_name`) seem to specify the operative identifier type for a given mapping task?
    *   Is it mainly for defining the "default" or "most canonical" ID *within that dataset itself*?
*   **`endpoint.properties.mappings`:**
    *   How are the keys (which are ontology type strings, e.g., `"HPA_OSP_PROTEIN_ID_ONTOLOGY"`) in this section used by the executor?
    *   How do they relate to the `source_property_name` / `target_property_name` parameters if these parameters are also ontology type strings?
    *   For UniProt-complete datasets, `mappings` must at least define the native primary ID and `PROTEIN_UNIPROTKB_AC_ONTOLOGY` for each relevant endpoint.
*   **`endpoint_relationships` Section:**
    *   How is the information in this section (e.g., `HPA_OSP_PROTEIN_TO_UKBB_PROTEIN` and its `primary_shared_ontology` and `source_conversion_preference`) intended to be used by the `MappingExecutor`?
    *   Is it automatically consulted if only `source_endpoint_name` and `target_endpoint_name` are provided, or do these relationships primarily inform how `mapping_paths` should be constructed?
*   **`ontology_preferences` Section:**
    *   How does this section, which defines preferences for ontology types *within a specific endpoint*, influence the `MappingExecutor`'s choices, particularly in Step 4 (Secondary -> PSO conversion)?
*   **`mapping_paths` Section:**
    *   How critical are explicit definitions for all *atomic steps* in a potential multi-hop mapping (e.g., Ensembl Gene -> UniProt, and then UniProt -> UKBB Assay ID)?
    *   Can the `MappingExecutor` chain multiple atomic paths if a direct end-to-end path isn't defined?
    *   For UniProt-complete datasets, paths might be defined to utilize a `UniProtMappingClient` for a secondary step involving historical/alternative UniProt IDs, enhancing recall after initial direct UniProt AC comparison.

### 5. Resolving the Current `ConfigurationError` in `test_protein_mapping.py`

*   **Root Cause Analysis:**
    *   Is the error `Could not determine endpoints or primary ontologies` definitively due to the default `source_property_name="PrimaryIdentifier"` and `target_property_name="PrimaryIdentifier"` lookups failing because no such literal property name exists in the HPA/UKBB endpoint configurations?
    *   Is there a misconfiguration in how `source_ontology_type` and `target_ontology_type` are being linked to the actual data properties defined in `metamapper.db` (from `protein_config.yaml`)?
*   **Confirming Correct Parameter Usage:**
    *   What is the validated, correct usage of `source_property_name` and `target_property_name` in the `test_protein_mapping.py` script for the HPA->UKBB case? Should they be the ontology type strings themselves (e.g., `"HPA_OSP_PROTEIN_ID_ONTOLOGY"`)?

### 6. Data Representation and Consistency in `protein_config.yaml`

*   **UniProt Columns:** Verify that the columns named "uniprot" in HPA OSP and QIN OSP data, and "UniProt" in UKBB data, are all correctly and consistently associated with the `PROTEIN_UNIPROTKB_AC_ONTOLOGY` type in their respective `endpoint.properties.mappings`.
*   **Other Key Columns:** Double-check that `HPA_OSP_PROTEIN_ID_ONTOLOGY` maps to column "gene" in HPA, and `UKBB_PROTEIN_ASSAY_ID_ONTOLOGY` maps to column "Assay_ID" in UKBB.

### 7. Adopted Approach: YAML-Defined Mapping Strategies

*   **Decision:** To handle complex, multi-step mapping pipelines with explicit control (such as the HPA-QIN-UKBB protein mapping requiring UniProt API resolution), Biomapper will support YAML-defined mapping strategies.
*   **Mechanism:** A `mapping_strategies` section in the `*_config.yaml` files will allow defining named strategies with an ordered list of steps. Each step specifies an `action.type` (a predefined operation) and its parameters.
*   **`MappingExecutor` Role:** The `MappingExecutor` will be enhanced to accept a `strategy_name` and execute the defined steps sequentially.
*   **Benefits:** Provides explicit control, reproducibility, and better extensibility for unique dataset needs without over-complicating the default iterative logic for every scenario.
*   **Detailed Documentation:** [YAML-Defined Mapping Strategies in Biomapper](./yaml_defined_mapping_strategies.md)

*(Previous points regarding implicit `MappingExecutor` behavior for complex sequences may be superseded or re-evaluated in light of this explicit strategy definition method.)*

*   **Overall Mapping Architecture:** Biomapper employs a layered approach:
    *   **Unidirectional Mapping Engines:** Both YAML-Defined Strategies (for explicit control) and the Default Iterative Strategy (for automated discovery) serve as engines to produce unidirectional mappings (Source -> Target or Target -> Source).
    *   **Bidirectional Reconciliation:** A separate reconciliation phase takes the outputs of two unidirectional mapping runs (one forward, one reverse) to compare, validate, and produce a final, high-confidence set of bidirectional mappings. This phase is agnostic to how the initial unidirectional mappings were generated.

---
