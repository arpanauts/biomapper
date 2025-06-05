# Feature: Core Metamapper Configuration for Protein Datasets

## Goal
To establish a robust and comprehensive configuration within `metamapper.db` that accurately describes protein datasets (initially UKBB, HPA, Qin), their identifiers, and how they can be mapped or looked up. This forms the foundation for reliable protein data integration and mapping within the Biomapper project.

## Key Requirements
-   **Centralized Configuration:** `metamapper.db` becomes the single source of truth for how protein datasets are structured and interconnected.
-   **Enable `MappingExecutor`:** Provide the necessary metadata for the `MappingExecutor` to perform lookups and (eventually) complex mapping paths involving these protein datasets.
-   **Standardization:** Define standard ontologies (e.g., `UNIPROTKB_AC`) and properties for consistent data handling.
-   **Extensibility:** Create a framework that can be easily extended to include additional protein datasets or other related data types.
-   **Improved Mapping Reliability:** Lay the groundwork for improving mapping success rates by ensuring accurate metadata.
-   **Define Ontologies & Properties:** Ensure `UNIPROTKB_AC` and other relevant protein/gene identifiers are well-defined.
-   **Define Endpoints:** For UKBB, HPA, and Qin protein datasets.
-   **Configure Property Extraction:** Specify how to extract UniProt ACs from source files.
-   **Configure Endpoint Properties:** Link extracted properties to endpoints, designating primary identifiers.
-   **Define Mapping Resources:** For each dataset, using `GenericFileLookupClient`, with correct `config_template`.
-   **Define Ontology Coverage:** Specify that resources perform identity lookups for `UNIPROTKB_AC`.
-   **Validate `populate_metamapper_db.py`:** Ensure the script correctly implements and validates these configurations.

## Target Audience
-   The `MappingExecutor` component of the Biomapper system.
-   Developers working on data integration and mapping tasks within Biomapper.
-   Future processes that need to understand the structure and relationships of protein datasets.

## Open Questions
-   Are there other key identifiers, beyond UniProt AC, that should be prioritized for extraction from these initial protein datasets?
-   What level of detail is required for `config_template` in `MappingResource` for potential future, more complex clients (beyond `GenericFileLookupClient`)?
-   How will versioning of these datasets and their schemas be handled in `metamapper.db` in the long term?
