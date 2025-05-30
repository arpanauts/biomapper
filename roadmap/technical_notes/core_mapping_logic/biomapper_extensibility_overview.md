# Biomapper Extensibility Overview

## 1. Introduction

Biomapper is designed to be a flexible and adaptable platform for mapping and integrating diverse biological datasets. A core tenet of its design is **extensibility**, which allows the system to grow and accommodate new data sources, new types of biological entities, and new mapping methodologies over time. This document outlines Biomapper's approach to extensibility, covering two primary dimensions:

*   **Horizontal Extensibility:** Integrating new datasets for *existing* entity types (e.g., mapping proteins from a new experimental dataset to an existing protein knowledgebase).
*   **Vertical Extensibility:** Incorporating entirely *new* biological entity types into the mapping framework (e.g., adding support for mapping metabolites or lipids, in addition to proteins).

Achieving robust extensibility is critical for Biomapper's long-term success and its ability to serve as a central hub for biological data integration.

## 2. Core Components Enabling Extensibility

Biomapper's extensibility is primarily facilitated by its modular architecture and configuration-driven approach. The key components are:

*   **`metamapper.db` (SQLite Database):**
    *   **Purpose:** Acts as the central configuration repository for the entire mapping system. It stores metadata about available data sources (Endpoints), types of identifiers (Ontology Types), mapping tools/APIs (Mapping Resources), and the relationships between them (Mapping Paths, Endpoint Relationships).
    *   **Extensibility Role:** New data sources, entity types, and mapping strategies are primarily added by defining new entries in this database.

*   **`populate_metamapper_db.py`:**
    *   **Purpose:** A Python script responsible for defining and populating `metamapper.db` with all necessary configurations (Endpoints, Resources, Paths, etc.).
    *   **Extensibility Role:** This script is the primary interface for developers to declare new mapping capabilities.

*   **`MappingClient` Interface (Abstract Base Class or Protocol):**
    *   **Purpose:** Defines a standardized contract for all mapping tools. Each `MappingClient` implementation encapsulates the logic for interacting with a specific data source, API, or local file to perform identifier lookups or translations.
    *   **Extensibility Role:** New mapping capabilities (e.g., querying a new online database, parsing a novel file format) are added by creating new classes that adhere to the `MappingClient` interface. Examples include `UniProtNameClient`, `ArivaleLookupClient`, `GenericFileLookupClient`.

*   **`MappingExecutor`:**
    *   **Purpose:** The core orchestration engine that takes source identifiers, desired target ontology types, and optional endpoint context, then dynamically discovers and executes the most appropriate mapping paths defined in `metamapper.db`.
    *   **Extensibility Role:** It is designed to be data-driven by `metamapper.db`. As new paths and resources are added to the database, the `MappingExecutor` can automatically utilize them without requiring changes to its own code (assuming the new capabilities fit within its existing iterative mapping logic).

*   **Key Data Models in `metamapper.db`:**
    *   **`Endpoint`:** Represents a specific data source or dataset (e.g., "UKBB_Protein_Data", "Arivale_Metabolomics_Snapshot").
    *   **`OntologyType`:** Defines a type of biological identifier or concept (e.g., "UNIPROTKB_AC", "CHEBI_ID", "GENE_NAME"). Consistent casing (typically uppercase) is crucial (MEMORY[72d47f11-0d66-4412-89ee-361faee929ce]).
    *   **`MappingResource`:** Represents a tool, API, or dataset that can perform a mapping between ontology types. It links to a specific `MappingClient` implementation and its configuration.
    *   **`MappingPath`:** Defines a sequence of `MappingResource` steps to translate identifiers from a source ontology type to a target ontology type.
    *   **`EndpointRelationship`:** Specifies preferred `MappingPath`(s) and their priorities when mapping between two specific `Endpoint`s.

## 3. Horizontal Extensibility: New Datasets for Existing Entity Types

Horizontal extensibility involves adding new data sources or datasets that deal with entity types already understood by Biomapper (e.g., adding a new source of protein identifiers).

**Example:** Mapping protein identifiers from a new "HPA_Protein" dataset to the existing "UKBB_Protein" dataset.

**Steps Involved:**

1.  **Define New `Endpoint`(s):**
    *   In `populate_metamapper_db.py`, add entries for any new datasets. For instance, an `Endpoint` named `HPA_PROTEIN_ENDPOINT`.
    *   Specify relevant `PropertyExtractionConfig` if the endpoint provides multiple identifier types.

2.  **Define New `MappingResource`(s) (if needed):**
    *   If the new dataset is accessed via a new API or a file format not yet supported, a new `MappingClient` implementation might be required.
    *   Once the client exists, define a new `MappingResource` in `populate_metamapper_db.py` that uses this client and provides its specific configuration (e.g., API URL, file path, key/value columns for a TSV).
    *   If the new dataset is a simple file (e.g., TSV, CSV) that can be handled by `GenericFileLookupClient`, you might only need to define a new `MappingResource` with the appropriate file path and column configurations (see MEMORY[c3f81352-4385-4f0e-b00f-c46577cbec43]).

3.  **Define New `MappingPath`(s):**
    *   In `populate_metamapper_db.py`, define one or more `MappingPath` entries that utilize the new (or existing) `MappingResource`(s) to connect the new `Endpoint`'s ontology types to other existing ontology types.
    *   Example: A path from `HPA_PROTEIN_ENDPOINT`'s primary ID (e.g., "ENSG_ID") to "UNIPROTKB_AC", and then potentially another path from "UNIPROTKB_AC" to the target endpoint's primary ID.

4.  **Define `EndpointRelationship`(s) (Recommended):**
    *   To guide the `MappingExecutor`, define `EndpointRelationship` entries in `populate_metamapper_db.py`. This allows specifying which `MappingPath`(s) are preferred (and their priority) when mapping directly between the new `Endpoint` and an existing one (e.g., `HPA_PROTEIN_ENDPOINT` to `UKBB_PROTEIN_ENDPOINT`).

5.  **Update Mapping Scripts:**
    *   Modify or create high-level mapping scripts (e.g., `map_hpa_to_ukbb.py`) to specify the new source and target `Endpoint` names when calling `MappingExecutor.execute_mapping`.

## 4. Vertical Extensibility: New Entity Types

Vertical extensibility involves introducing support for entirely new categories of biological entities that Biomapper hasn't handled before (e.g., adding metabolites, lipids, or genetic variants).

**Example:** Adding the capability to map "Arivale_Metabolites" (identified by, say, "ARIVALE_CHEM_ID") to "KEGG_Compound_IDs".

**Steps Involved (Potentially More Complex):**

1.  **Define New `OntologyType`(s):**
    *   In `populate_metamapper_db.py`, define new `OntologyType` entries for all new identifiers associated with the new entity type (e.g., "ARIVALE_CHEM_ID", "PUBCHEM_CID", "HMDB_ID"). Remember consistent casing.

2.  **Define New `Endpoint`(s):**
    *   Add `Endpoint` entries for data sources providing these new entity types (e.g., `ARIVALE_METABOLOMICS_ENDPOINT`, `PUBCHEM_ENDPOINT` if not already broadly defined).

3.  **Develop New `MappingClient`(s) (Often Required):**
    *   New entity types often come with specialized databases, APIs, or file formats. This usually necessitates creating new `MappingClient` implementations.
    *   Example: A `PubChemAPIClient` to query PubChem for CIDs based on names, or a `HMDBFileClient` to parse HMDB data.

4.  **Define New `MappingResource`(s):**
    *   In `populate_metamapper_db.py`, define `MappingResource` entries that use these new `MappingClient`(s) and their configurations. Declare their `input_ontology_term` and `output_ontology_term`.

5.  **Define New `MappingPath`(s):**
    *   Create `MappingPath` entries to connect the new `OntologyType`(s) via the new `MappingResource`(s).
    *   Example: A path from "ARIVALE_CHEM_ID" to "PUBCHEM_CID" using a resource based on an Arivale-to-PubChem mapping file, and another path from "PUBCHEM_CID" to "KEGG_ID" using a resource that queries UniChem or another cross-reference service.

6.  **Define `EndpointRelationship`(s):**
    *   As with horizontal extensibility, define relationships between endpoints providing these new entity types to guide path selection.

7.  **Potential `MappingExecutor` Considerations:**
    *   The goal is for `MappingExecutor` to be generic. However, new entity types might introduce complexities (e.g., highly composite identifiers, novel ambiguity resolution needs) that could, in rare cases, suggest refinements to the executor's core iterative logic or pre/post-processing steps. The preference is to handle such complexities within specialized `MappingClient`s or configurable pre-processing steps (MEMORY[5e6be590-afbc-4008-9edd-106becd63356]).

8.  **Data Schemas and Validation:**
    *   If new entity types involve complex data structures beyond simple identifiers, Pydantic models (or similar) might be needed for data validation and structured representation within clients.

## 5. Best Practices for Extensibility

*   **Consult `CONTRIBUTING_NEW_MAPPING_PATH.md`:** This document (MEMORY[6765e2d1-fa75-486f-bf63-53308d95341c]) provides a detailed guide for adding new mapping paths and should be the first point of reference.
*   **Consistent Ontology Term Casing:** Strictly adhere to uppercase for `OntologyType` names in `populate_metamapper_db.py` and client configurations to avoid pathfinding issues (MEMORY[72d47f11-0d66-4412-89ee-361faee929ce]).
*   **Modular `MappingClient` Design:** Keep clients focused on a single responsibility (e.g., interacting with one specific API or file type).
*   **Configuration-Driven Clients:** Design clients to be configurable through the `config_template` in their `MappingResource` definition, rather than hardcoding parameters.
*   **Thorough Testing:**
    *   Unit test new `MappingClient` implementations.
    *   Integration test new mapping paths using small, well-characterized datasets.
    *   Validate the `MappingExecutor`'s behavior with the new additions.
*   **Documentation:** Document new `OntologyType`s, `MappingResource`s, and `MappingClient`s.

## 6. Conclusion

Biomapper's architecture, centered around a configurable `metamapper.db` and a generic `MappingExecutor`, provides a strong foundation for both horizontal and vertical extensibility. By following the outlined procedures and best practices, developers can systematically expand Biomapper's capabilities to integrate an ever-wider range of biological data, fulfilling its core mission. Addressing any performance bottlenecks in the `MappingExecutor` is crucial to ensure that this extensibility can be practically realized.
