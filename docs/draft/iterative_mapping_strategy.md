# Biomapper: Iterative Mapping Strategy

## Introduction

This document outlines a refined, iterative strategy for mapping entities between two endpoints within the Biomapper framework. The primary goal is to maximize the number of successful mappings by systematically leveraging both the primary shared ontology type and available secondary ontology types present in the source endpoint data.

This strategy moves beyond simply finding the first available `MappingPath` and instead implements a more robust, multi-step process orchestrated by the `MappingExecutor`.

## Core Concepts

*   **Endpoints:** Data sources or targets (e.g., `ukbb_protein`, `arivale_protein`).
*   **EndpointRelationship:** Defines the connection between a source and target endpoint and specifies the **Primary Shared Ontology Type** preferred for mapping between them (via `OntologyPreference`). Example: For `ukbb_protein` -> `arivale_protein`, the preferred shared type is `UNIPROTKB_AC`.
*   **Primary Ontology Type:** The identifier type designated as the preferred one for an endpoint (via `OntologyPreference`, often related to the `EndpointRelationship` preference).
*   **Secondary Ontology Types:** Other identifier types available for entities within an endpoint (e.g., `GENE_NAME`, `ENSEMBL_PROTEIN`, `ENSEMBL_GENE`) as defined in `EndpointPropertyConfig`.
*   **Atomic Mapping Paths:** Individual `MappingPath` definitions in `populate_metamapper_db.py` that represent a single conversion step (e.g., `UNIPROTKB_AC` -> `ARIVALE_PROTEIN_ID`, `GENE_NAME` -> `UNIPROTKB_AC`, `ENSEMBL_PROTEIN` -> `UNIPROTKB_AC`).

## The Iterative Mapping Strategy

The strategy is executed by the `MappingExecutor` when tasked with mapping entities from a source endpoint to a target endpoint, based on their defined `EndpointRelationship`.

**Example:** Mapping Source `UKBB_Protein` to Target `Arivale_Protein`.

1.  **Identify Primary Shared Ontology:** The `MappingExecutor` checks the `EndpointRelationship` and associated `OntologyPreference` to determine the preferred shared ontology type. (e.g., `UNIPROTKB_AC`).

2.  **Attempt Primary Mapping (Direct):**
    *   The executor gathers source entities (UKBB) that *already possess* the primary shared identifier (`UNIPROTKB_AC`).
    *   It searches for and executes relevant `MappingPath`s that start with this primary shared type and end with a target endpoint identifier type (e.g., `UNIPROTKB_AC` -> `ARIVALE_PROTEIN_ID`).
    *   Successful mappings (Source Entity -> Target Entity) are recorded.

3.  **Identify Unmapped Entities & Secondary Types:**
    *   The executor identifies source entities (UKBB) that were *not* successfully mapped in Step 2 (often because they lacked the primary identifier `UNIPROTKB_AC` initially).
    *   For these unmapped entities, it checks the `EndpointPropertyConfig` to find available *secondary* ontology types (e.g., `GENE_NAME`, `ENSEMBL_PROTEIN`, `ENSEMBL_GENE`).

4.  **Attempt Secondary -> Primary Conversion (Prioritized Iteration):**
    *   For each unmapped source entity identified in Step 3:
        *   Retrieve all available *secondary* ontology types for this entity based on `EndpointPropertyConfig` (e.g., for a UKBB entity, this might be `GENE_NAME`; for an Arivale entity, this might include `GENE_NAME`, `ENSEMBL_PROTEIN`, and `ENSEMBL_GENE`).
        *   Retrieve the `OntologyPreference` rankings for these secondary types specifically for the *source* endpoint.
        *   Sort the available secondary types according to their priority (lower number = higher priority).
        *   **Iterate through the sorted secondary types:**
            *   For the current secondary type (e.g., `GENE_NAME`), search for and attempt to execute relevant `MappingPath`s that convert this secondary type to the *primary shared type* (e.g., `GENE_NAME` -> `UNIPROTKB_AC`).
            *   For Arivale proteins, alternatives include `ENSEMBL_PROTEIN` -> `UNIPROTKB_AC` and `ENSEMBL_GENE` -> `UNIPROTKB_AC`.
            *   **First Success Wins:** If a path successfully derives the primary shared identifier (`UNIPROTKB_AC`):
                *   Record the derived identifier for the entity.
                *   Record the provenance (e.g., "Derived UNIPROTKB_AC from GENE_NAME via path X").
                *   **Stop** processing further secondary types for *this specific entity* and move to the next unmapped entity.
            *   If the path fails or no path exists for this secondary type, continue to the next secondary type in the priority list for the current entity.

5.  **Re-attempt Primary Mapping (Indirect):**
    *   The executor takes the source entities for which a primary shared identifier was successfully *derived* in Step 4.
    *   It re-runs the primary mapping logic from Step 2 for these entities (e.g., using the derived `UNIPROTKB_AC` to find an `ARIVALE_PROTEIN_ID`).
    *   Successful mappings are recorded.

6.  **Aggregate Results:** The executor combines the successful mappings from Step 2 (Direct Primary) and Step 5 (Indirect via Secondary Conversion) to produce the final mapping result set.

**Note on Backward Mapping:** The same logic applies when mapping in the reverse direction (e.g., Arivale -> UKBB). The roles of source/target are swapped, and the secondary types considered in Step 3/4 would be those available in the *Arivale* endpoint (like `ENSEMBL_PROTEIN`, `GENE_NAME`, or `ENSEMBL_GENE`). The goal remains converting these back to the primary shared type (`UNIPROTKB_AC`).

Additionally, the `MappingExecutor` supports bidirectional mapping through the `try_reverse_mapping` parameter. When enabled, if no forward mapping path is found, the executor will automatically try to find and execute a path in the reverse direction. This feature is particularly useful for handling cases where one direction has better coverage or more reliable resources.

## Implementation Notes

*   **`populate_metamapper_db.py`:** Must define all the necessary *atomic* `MappingPath`s that the executor might need (Primary -> Target, Secondary -> Primary, etc.). The paths themselves don't contain the iterative logic.
*   **`MappingExecutor`:** This component implements the orchestration logic described in steps 1-6, including support for bidirectional mapping through the `ReversiblePath` class.
*   **Configuration:** `EndpointPropertyConfig` needs to accurately reflect all available identifier columns (and their ontology types) for each endpoint. `OntologyPreference` should be defined for source endpoints to guide the secondary type conversion order.

### Current Implementation for Protein Mapping

The current implementation supports mapping between UKBB Protein and Arivale Protein endpoints with the following identifiers:

**UKBB Protein Endpoint:**
- Primary: `UNIPROTKB_AC` (extracted from "UniProt" column)
- Secondary: `GENE_NAME` (extracted from "Assay" column)

**Arivale Protein Endpoint:**
- Primary: `UNIPROTKB_AC` (extracted from "uniprot" column)
- Secondary: 
  - `ENSEMBL_PROTEIN` (extracted from "protein_id" column)
  - `GENE_NAME` (extracted from "gene_name" column)
  - `ENSEMBL_GENE` (extracted from "ensembl_gene_id" column)
  - `ARIVALE_PROTEIN_ID` (extracted from "name" column, used primarily for reverse lookups)

**Mapping Paths:**
- Direct Path: `UNIPROTKB_AC` -> `ARIVALE_PROTEIN_ID` (via `arivale_lookup` resource)
- Secondary Conversion Paths:
  - `GENE_NAME` -> `UNIPROTKB_AC` (via `uniprot_name` resource using UniProt Name Search API)
  - `ENSEMBL_PROTEIN` -> `UNIPROTKB_AC` (via `uniprot_ensembl_protein_mapping` resource)
  - `ENSEMBL_GENE` -> `UNIPROTKB_AC` (via `uniprot_idmapping` resource)

**Ontology Preferences:**
- UKBB Protein priorities: (1) `UNIPROTKB_AC`, (2) `GENE_NAME`
- Arivale Protein priorities: (1) `UNIPROTKB_AC`, (2) `ENSEMBL_PROTEIN`, (3) `GENE_NAME`, (4) `ENSEMBL_GENE`, (5) `ARIVALE_PROTEIN_ID`

These configurations enable the `MappingExecutor` to attempt mappings using the preferred ontology first, followed by secondary ontologies in order of priority if the primary mapping fails.

## Pseudo-code Illustration (`MappingExecutor` Logic Snippet)

```python
# Conceptual pseudo-code within MappingExecutor.map(source_endpoint, target_endpoint, relationship)

def execute_iterative_mapping(source_entities, source_endpoint, target_endpoint, relationship):
    primary_shared_ontology = get_primary_shared_ontology(relationship)
    source_preferences = get_ontology_preferences(source_endpoint)

    successful_mappings = {}
    mapped_source_ids = set()
    derived_primary_ids = {}

    # --- Step 2: Attempt Primary Mapping (Direct) ---
    entities_with_primary = {eid: entity for eid, entity in source_entities.items() if primary_shared_ontology in entity.identifiers}
    direct_results = find_and_execute_paths(
        entities_with_primary,
        start_ontology=primary_shared_ontology,
        # end_ontology implicitly determined by target endpoint preferences/available paths
    )
    successful_mappings.update(direct_results)
    mapped_source_ids.update(direct_results.keys())

    # --- Step 3: Identify Unmapped Entities & Secondary Types ---
    unmapped_entities = {eid: entity for eid, entity in source_entities.items() if eid not in mapped_source_ids}

    # --- Step 4: Attempt Secondary -> Primary Conversion (Prioritized Iteration) ---
    for entity_id, entity in unmapped_entities.items():
        available_secondary_types = get_available_secondary_types(entity, source_endpoint)
        sorted_secondary_types = sort_by_preference(available_secondary_types, source_preferences)

        for secondary_type in sorted_secondary_types:
            conversion_results = find_and_execute_paths(
                {entity_id: entity}, # Process one entity at a time for conversion
                start_ontology=secondary_type,
                end_ontology=primary_shared_ontology
            )

            if entity_id in conversion_results: # Check if conversion was successful
                derived_id = conversion_results[entity_id] # Assuming path returns the target ID
                derived_primary_ids[entity_id] = {
                    "id": derived_id,
                    "provenance": f"Derived from {secondary_type}"
                }
                break # First success wins for this entity

    # --- Step 5: Re-attempt Primary Mapping (Indirect) ---
    entities_with_derived_primary = { 
        eid: entity # Need to effectively 'add' derived_primary_ids[eid]['id'] to entity.identifiers
        for eid, entity in unmapped_entities.items() 
        if eid in derived_primary_ids
    }
    # Update entities_with_derived_primary to use the derived ID for mapping
    update_entities_with_derived_ids(entities_with_derived_primary, derived_primary_ids)
    
    indirect_results = find_and_execute_paths(
        entities_with_derived_primary,
        start_ontology=primary_shared_ontology,
        # end_ontology implicitly determined by target endpoint preferences/available paths
    )
    # Add provenance from derived_primary_ids to these results
    add_provenance_to_mappings(indirect_results, derived_primary_ids)
    successful_mappings.update(indirect_results)

    # --- Step 6: Aggregate Results ---
    return successful_mappings

# Helper functions (get_primary_shared_ontology, get_ontology_preferences, etc.) omitted for brevity
```

## Benefits

*   **Increased Mapping Coverage:** Leverages multiple identifiers, increasing the likelihood of finding a match.
*   **Robustness:** Less reliant on every entity having the primary identifier initially.
*   **Systematic & Extensible:** Provides a clear, repeatable logic that can be applied to different endpoint relationships without requiring fundamentally new path definitions for every combination.
*   **Efficiency:** Prioritizes direct mapping first and avoids overly complex, multi-hop secondary-to-secondary mappings initially.

## Future Considerations

*   **Endpoints without a Shared Primary Ontology:** Developing strategies for mapping between endpoints where the `EndpointRelationship` does not identify a single, direct primary ontology type shared between them. This might involve multi-hop paths or leveraging intermediate ontologies, likely still guided by `OntologyPreference`.
*   **Advanced Fallback Strategies:** Implementing more sophisticated fallback mechanisms (e.g., RAG-based approaches for certain data types like metabolites or clinical labs) when both direct and secondary-conversion mapping attempts fail.
*   **Performance Optimization:** Refining the execution logic for large datasets, potentially including batching API calls or optimizing database lookups for path execution.
*   **Enhanced Metadata Tracking:** Further developing the metadata tracking capabilities implemented in `EntityMapping` (`confidence_score`, `hop_count`, `mapping_direction`, `mapping_path_details`) to provide more detailed provenance information for complex mappings.
*   **Client-Specific Reverse Mappings:** Implementing specialized `reverse_map_identifiers` methods in mapping clients where the current generic approach of inverting forward mappings may not be optimal.
*   **Compound/Metabolite Support:** Extending the current protein mapping framework to support compound and metabolite identifiers with additional resources like UMLS for text-based entity mapping.
