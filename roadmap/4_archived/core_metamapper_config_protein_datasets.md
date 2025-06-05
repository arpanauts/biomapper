# Core Metamapper Configuration for Protein Datasets

## Core Concept / Problem
To establish a robust and comprehensive configuration within `metamapper.db` that accurately describes protein datasets (initially UKBB, HPA, Qin), their identifiers, and how they can be mapped or looked up. This forms the foundation for reliable protein data integration and mapping within the Biomapper project.

## Intended Goal / Benefit
-   **Centralized Configuration:** `metamapper.db` becomes the single source of truth for how protein datasets are structured and interconnected.
-   **Enable `MappingExecutor`:** Provide the necessary metadata for the `MappingExecutor` to perform lookups and (eventually) complex mapping paths involving these protein datasets.
-   **Standardization:** Define standard ontologies (e.g., `UNIPROTKB_AC`) and properties for consistent data handling.
-   **Extensibility:** Create a framework that can be easily extended to include additional protein datasets or other related data types.
-   **Improved Mapping Reliability:** Lay the groundwork for improving mapping success rates by ensuring accurate metadata.

## Initial Thoughts / Requirements / Context
This initiative encompasses the following key aspects, building upon recent work with `populate_metamapper_db.py`:

1.  **Ontologies & Properties:**
    *   Ensure `UNIPROTKB_AC` and other relevant protein/gene identifiers are well-defined as `Ontology` and `Property` entries.
2.  **Endpoints:**
    *   Define `Endpoint` entries for UKBB, HPA, and Qin protein datasets.
3.  **Property Extraction:**
    *   Create `PropertyExtractionConfig` entries to specify how to extract UniProt ACs (and potentially other key fields) from the source files (`/home/ubuntu/biomapper/data/UKBB_Protein_Meta_full.tsv`, `/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv`, `/home/ubuntu/biomapper/data/isb_osp/qin_osps.csv`).
4.  **Endpoint Property Configuration:**
    *   Link extracted properties to their endpoints via `EndpointPropertyConfig`, designating primary identifiers.
5.  **Mapping Resources:**
    *   Define `MappingResource` entries for each dataset, primarily utilizing `GenericFileLookupClient` for direct lookups within the files.
    *   Ensure `config_template` for these resources correctly specifies file paths, delimiters, and key/value columns (using `json.dumps` for the template).
6.  **Ontology Coverage:**
    *   Define `OntologyCoverage` to state that these resources can perform identity lookups for `UNIPROTKB_AC`.
7.  **Validation:**
    *   Ensure `populate_metamapper_db.py` correctly implements these configurations and runs successfully.

This work is crucial for the UKBB-Arivale MVP and aligns with the iterative mapping strategy documented in `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md`.
