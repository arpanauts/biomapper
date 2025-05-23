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
    *   It's important to note that a single source entity (e.g., one UKBB protein identified by a unique UniProt AC) can map to *multiple distinct target entities* if those target entities share the same primary identifier (e.g., Arivale proteins derived from different panels or assays but having the same UniProt AC). Each such link (Source Entity -> Specific Target Entity Instance) is considered an individual mapping to be recorded.
    *   Successful mappings (Source Entity -> Target Entity/Entities) are recorded.

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

6.  **Bidirectional Validation (Optional):** If enabled via the `validate_bidirectional` parameter, the executor performs an additional validation step:
    *   All target IDs discovered in successful mappings are collected.
    *   A reverse mapping (target → source) is executed for these IDs.
    *   Each original mapping is enriched with a `validation_status` field:
        *   **"Validated"**: When a target ID maps back to its original source ID (bidirectional success).
        *   **"UnidirectionalSuccess"**: When forward mapping succeeded but the target doesn't map back to the source.
    *   All forward mappings are preserved in the result, just enriched with validation status.
    *   This provides a three-tiered status system: "Validated" (bidirectional success), "UnidirectionalSuccess" (forward only), and "Failed" (not in successful mappings).
    *   When a single source entity maps to multiple target entities (as noted in Step 2), each of these individual forward links is independently validated. The final reconciled output (e.g., from Phase 3) will therefore present each such validated link as a distinct entry. This ensures comprehensive reporting of all identified one-to-many or many-to-many relationships, detailing the validation status for each specific source-target_instance pair.

7.  **Phase 3: Bidirectional Reconciliation:** For comprehensive mapping analysis, a dedicated reconciliation script provides the following enhancements:
    *   **Advanced Validation Status:** Expands the validation status system to five tiers:
        *   **"Validated: Bidirectional exact match":** The source entity maps to the target entity, and the target maps back to exactly the same source entity.
        *   **"Validated: Forward mapping only":** The source entity maps to the target entity, but the target entity does not map back to this source entity.
        *   **"Validated: Reverse mapping only":** No direct mapping exists from source to target, but the target entity maps back to this source entity.
        *   **"Conflict":** The source entity maps to the target entity, but the target entity maps back to a different source entity.
        *   **"Unmapped":** No mapping exists in either direction.
    *   **One-to-Many Relationship Support:** Explicitly handles and flags one-to-many relationships in both directions:
        *   **`is_one_to_many_source`:** Flag indicating whether this source entity maps to multiple target entities.
        *   **`is_one_to_many_target`:** Flag indicating whether this target entity maps to multiple source entities.
        *   **`is_canonical_mapping`:** Flag indicating the preferred mapping for each source entity (based on validation status and confidence).
    *   **Dynamic Column Naming:** Generates column names based on the source and target endpoints, allowing for flexible reconciliation between different entity types.
    *   **Comprehensive Statistics:** Provides detailed mapping statistics, including counts of unique source and target entities, validation status distribution, and one-to-many relationship metrics.
    *   **Complete Entity Coverage:** Incorporates all entities from both forward and reverse mapping phases, ensuring no entities are omitted from the final analysis.
    *   **Historical Resolution Tracking:** For UniProtKB mappings, tracks historical identifier resolution information, including original and resolved accessions and resolution type.

    The Phase 3 reconciliation process produces a comprehensive TSV output file and a JSON metadata file, providing complete information about the bidirectional mapping relationships between source and target endpoints. See `phase3_output_column_guide.md` for detailed documentation of the output format.

**Note on Backward Mapping:** The same logic applies when mapping in the reverse direction (e.g., Arivale -> UKBB). The roles of source/target are swapped, and the secondary types considered in Step 3/4 would be those available in the *Arivale* endpoint (like `ENSEMBL_PROTEIN`, `GENE_NAME`, or `ENSEMBL_GENE`). The goal remains converting these back to the primary shared type (`UNIPROTKB_AC`).

The `MappingExecutor` supports two distinct bidirectional features:

1. **Bidirectional Path Finding** (`try_reverse_mapping` parameter): When enabled, if no forward mapping path is found, the executor will automatically try to find and execute a path in the reverse direction. This feature is particularly useful for handling cases where one direction has better coverage or more reliable resources.

2. **Bidirectional Validation** (`validate_bidirectional` parameter): When enabled, performs the validation step described above to verify the quality of mappings by checking if target IDs map back to their source IDs.

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

def execute_iterative_mapping(source_entities, source_endpoint, target_endpoint, relationship, validate_bidirectional=False):
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

    # --- Step 6: Bidirectional Validation (Optional) ---
    if validate_bidirectional:
        # Extract all target IDs from successful mappings
        target_ids_to_validate = set()
        for result in successful_mappings.values():
            if result and result.get("target_identifiers"):
                target_ids_to_validate.update(result["target_identifiers"])
        
        # Find a reverse mapping path from target back to source
        reverse_path = find_best_path(
            primary_target_ontology,  # Using target as source
            primary_source_ontology,  # Using source as target
            preferred_direction="forward"
        )
        
        if reverse_path:
            # Execute reverse mapping
            reverse_results = execute_path(
                reverse_path,
                list(target_ids_to_validate),
                primary_target_ontology,
                primary_source_ontology
            )
            
            # Reconcile bidirectional mappings
            successful_mappings = reconcile_bidirectional_mappings(
                successful_mappings,
                reverse_results
            )

    # --- Step 7: Aggregate Results ---
    return successful_mappings

# Helper function for bidirectional validation
def reconcile_bidirectional_mappings(forward_mappings, reverse_results):
    # Create a target-to-source lookup from reverse_results
    target_to_sources = {}
    for target_id, result in reverse_results.items():
        if result and result.get("target_identifiers"):
            target_to_sources[target_id] = set(result["target_identifiers"])
    
    # Check each forward mapping and enrich with validation status
    enriched_mappings = {}
    for source_id, result in forward_mappings.items():
        enriched_result = result.copy()
        
        if not result or not result.get("target_identifiers"):
            enriched_result["validation_status"] = "UnidirectionalSuccess"
        else:
            target_ids = result["target_identifiers"]
            source_validated = False
            
            # Check if any of these targets map back to this source
            for target_id in target_ids:
                if target_id in target_to_sources:
                    if source_id in target_to_sources[target_id]:
                        source_validated = True
                        break
            
            if source_validated:
                enriched_result["validation_status"] = "Validated"
            else:
                enriched_result["validation_status"] = "UnidirectionalSuccess"
        
        enriched_mappings[source_id] = enriched_result
    
    return enriched_mappings

# Other helper functions (get_primary_shared_ontology, get_ontology_preferences, etc.) omitted for brevity
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
*   **Advanced Bidirectional Validation:** Building on the current bidirectional validation implementation to provide more sophisticated validation metrics and confidence adjustments based on validation status.
