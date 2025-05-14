# Technical Note: Composite Identifier Handling in Biomapper

**Date:** 2025-05-01

## 1. Introduction

During the development of the Biomapper project, particularly the UKBB <=> Arivale protein mapping, the need arose to handle 'composite' identifiers. These are identifiers that represent multiple distinct entities within a single string, often delimited by characters like commas (`,`) or underscores (`_`).

Examples encountered:

*   UniProt identifiers in the Arivale proteomics metadata acting as keys: `"P29460,P29459"`
*   Gene symbols/names representing multiple genes: `"GENE1_GENE2"` (handled by `UniProtNameClient`)

This document outlines the current implementation strategies for handling these composite identifiers and the planned future direction for generalization.

## 2. Current Implementation

Composite identifier handling is currently implemented within specific mapping clients on a case-by-case basis.

### 2.1. `ArivaleMetadataLookupClient`

*   **File:** `biomapper/mapping/clients/arivale_lookup_client.py`
*   **Context:** Used in the forward mapping path `UKBB_Protein` -> `Arivale_Protein`.
*   **Challenge:** The source Arivale metadata file (`proteomics_metadata.tsv`) uses composite UniProt strings (e.g., `"P29460,P29459"`) as keys in the `uniprot` column, mapping to a single Arivale Protein ID.
*   **Input:** The client receives single UniProt IDs from the UKBB source data.
*   **Implementation (`__init__` - Pre-processing):**
    *   The client reads the Arivale TSV and builds its primary `_lookup_map` (potentially with composite keys).
    *   It simultaneously builds a secondary `_component_lookup_map`.
    *   To build the component map, it iterates through the keys of the primary map.
    *   Each key (UniProt string) is split by comma (`,`).
    *   Each resulting non-empty component (e.g., `"P29460"`, `"P29459"`) is added as a key to `_component_lookup_map`, mapping to the corresponding Arivale Protein ID.
    *   Warnings are logged if a single component appears to map to multiple different Arivale IDs (the first encountered mapping is kept).
*   **Implementation (`map_identifiers` - Lookup):**
    *   The method uses the `_component_lookup_map` for lookups.
    *   When an input UniProt ID (e.g., `"P29460"`) is received, it performs a direct lookup in `_component_lookup_map`.
    *   If the input ID exists as a key (meaning it was a component of an original composite key, or was a standalone key), the corresponding Arivale ID is returned.
*   **Outcome:** Allows successful forward mapping even when the UKBB input ID is only *part* of a composite key in the Arivale data.

### 2.2. `UniProtNameClient`

*   **File:** `biomapper/mapping/clients/uniprot_name_client.py`
*   **Context:** Used for mapping Gene Symbols/Names to UniProtKB ACs (e.g., as part of a multi-hop path).
*   **Challenge:** Input gene symbols might represent multiple genes joined by delimiters (e.g., `"GENE1_GENE2"`).
*   **Implementation (`_handle_composite_gene_symbol`, `_process_composite_gene`):
    *   The client checks if the input gene symbol contains predefined delimiters (`_`, `;`, `|`, `/`).
    *   If composite, it splits the input symbol into individual parts (e.g., `["GENE1", "GENE2"]`).
    *   It then attempts to search UniProt for each part individually using `_search_single_gene`.
    *   It typically returns the result from the *first* part that yields a successful UniProt mapping.
    *   A fallback using `OR` logic across all parts exists if individual searches fail.
*   **Outcome:** Handles composite *input* identifiers by attempting to resolve individual components.

### 2.3. Backward Mapping (Arivale -> UKBB)

*   **Strategy:** The current approach for backward mapping relies on multi-hop paths defined in `metamapper.db` rather than attempting a direct reverse lookup and parsing of the Arivale TSV data within a single client.
*   **Implication:** If a reverse lookup client (like one potentially reading the Arivale TSV) retrieves a composite UniProt string (e.g., `"P29460,P29459"`) associated with an Arivale ID, the responsibility for handling or splitting that composite string falls to subsequent steps or clients in the defined multi-hop path, or potentially requires a dedicated 'resolver' resource step.
*   **Status:** No specific client-level composite parsing is currently implemented *for the backward path's initial lookup step* based on this strategy.

## 3. Deferred Goals & Future Roadmap

The current client-specific implementations address immediate needs. However, relying on hardcoded logic within each client is not scalable or easily maintainable, especially as new entity types and mapping resources are added.

As noted in Memory `5e6be590-afbc-4008-9edd-106becd63356`, the long-term goal is to **generalize the handling of composite identifiers** (and potentially other variations like outdated/secondary IDs).

Potential approaches include:

1.  **Configurable Pre-processing:** Implement steps within the `MappingExecutor` itself to pre-process input identifiers based on patterns or rules defined in `metamapper.db` before they reach the client.
2.  **Dedicated Resolver Resources:** Create specialized 'mapping resources' in `metamapper.db` whose sole purpose is to split composite IDs or resolve outdated IDs. These would act as intermediate steps in a multi-hop path.
3.  **Middleware/Decorators:** Apply middleware or decorator patterns to client calls within the `MappingExecutor` to handle splitting/resolution transparently.

**Roadmap:**

*   **Short-Term:** Maintain the current client-specific implementations (`ArivaleMetadataLookupClient`, `UniProtNameClient`).
*   **Medium-Term (Post-Executor Refactor):** Revisit the need for generalization based on new mapping requirements (e.g., for metabolites, different data sources).
*   **Long-Term:** Select and implement one of the generalized approaches above to reduce code duplication and improve maintainability.

This generalization effort is currently **deferred** and lower priority than the core `MappingExecutor` refactoring.

## 4. Conclusion

Biomapper currently handles composite identifiers through targeted logic within the `ArivaleMetadataLookupClient` (for composite keys in source data) and `UniProtNameClient` (for composite input identifiers). The backward mapping strategy avoids immediate parsing needs. Future work aims to generalize this handling for better scalability and maintainability, but this is deferred pending the completion of higher-priority framework enhancements.
