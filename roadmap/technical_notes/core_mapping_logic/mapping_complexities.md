# Mapping Complexities and Edge Cases

This document outlines known complexities, edge cases, and ontological challenges encountered during the entity mapping process within the `biomapper` project, particularly focusing on identifier changes (merges, splits, deprecations).

## UniProt Identifier Demergers

### Example: P0CG05 (Arivale) -> P0DOY2 (UKBB)

*   **Context:** The UniProt identifier `P0CG05` (present in the Arivale dataset) is documented by UniProt as having been demerged into two separate entries: `P0DOY2` and `P0DOY3`.
*   **Observation:**
    *   `P0DOY2` exists in both the Arivale and UKBB datasets.
    *   `P0DOY3` exists in neither dataset (based on current analysis).
*   **Biomapper Behavior (Forward: UKBB -> Arivale):** If `P0DOY2` from UKBB is mapped forward, it might potentially map to `P0CG05` in Arivale if the mapping resources treat `P0CG05` as a secondary/alternative identifier for `P0DOY2`.
*   **Biomapper Behavior (Backward: Arivale -> UKBB):** When mapping backward from `P0CG05` in Arivale, the ideal outcome is to identify its relationship to `P0DOY2` and successfully map it to the `P0DOY2` present in UKBB.
*   **Current Handling (Investigation Needed):** We need to verify if the underlying mapping resources (e.g., UniProt ID mapping files) and the `biomapper` logic correctly handle this demerger information. Ideally, the mapping path or output metadata should indicate that `P0CG05` is a historical/secondary ID related to the mapped target `P0DOY2`.
*   **Future Enhancements (Phase 2):** Multi-strategy mapping could offer explicit options for handling such cases, like choosing to map to all valid demerged targets found in the destination dataset or flagging them for review.

---

## Composite UniProt Identifiers in Arivale Metadata

*   **Issue:** The `uniprot` column in the Arivale metadata file (`proteomics_metadata.tsv`) sometimes contains multiple UniProt IDs concatenated into a single string, typically separated by a comma (e.g., `"P29460,P29459"`).
*   **Examples:**
    *   `P29460,P29459`
    *   `Q11128,P21217`
    *   `Q29983,Q29980`
    *   `Q8NEV9,Q14213`
*   **Impact (Backward Mapping: Arivale -> UKBB):** The `ArivaleReverseLookupClient` currently reads this composite string as a single value. Subsequent mapping steps expecting a valid UniProt ID will fail.
*   **Impact (Forward Mapping: UKBB -> Arivale):** The handling by the `ArivaleMetadataLookupClient` (which maps UniProt -> Arivale ID) needs investigation. It's unclear if it splits these IDs or how it associates them with Arivale IDs.
*   **Current Handling (Investigation Needed):** We need to verify the behavior of `ArivaleMetadataLookupClient` and confirm the behavior of `ArivaleReverseLookupClient` (likely takes the full string).
*   **Resolution Strategy (Phase 2 Recommended):** Both clients need modification. A clear strategy is required (e.g., split and take first, split and map all, exclude, configurable behavior). Splitting and deciding how to handle the resulting multiple mappings is complex and best suited for multi-strategy implementation.

---


---

## Dataset-Specific Parameters and Configurations

Each meta-dataset (e.g., UKBB, HPA, QIN, Arivale) brings its own unique set of identifiers, data formats, update frequencies, and inherent data quality characteristics. Addressing these requires careful configuration and sometimes custom logic:

*   **Identifier Nuances:** Datasets may use different versions of standard identifiers (e.g., Ensembl versions) or have proprietary ID systems. The `protein_config.yaml` (and similar files for other entities) must accurately define these native identifiers and their relationship to shared ontologies like UniProt AC.
*   **Data Structure and Format:** Source data can range from simple TSV/CSV files to complex relational databases or APIs. Clients (e.g., `ArivaleMetadataLookupClient`, `UniProtHistoricalResolverClient`) must be designed to handle these specific formats, including delimiters, column names, and data types.
*   **"UniProt-Completeness":** As noted in `/home/ubuntu/biomapper/roadmap/guides/configuring_ukbb_hpa_qin_mapping.md`, datasets like HPA, QIN, and UKBB proteins are considered "UniProt-complete." This simplifies mapping by making UniProt AC a reliable primary shared ontology (PSO). However, it also makes accurate UniProt historical resolution (via `UniProtHistoricalResolverClient`) mandatory to handle IDs that have been merged, split, or deprecated over time.
*   **Data Quality and Preprocessing:** Some datasets may require preprocessing steps not explicitly handled by Biomapper's core mapping logic (e.g., cleaning malformed gene names in UKBB data, as mentioned in MEMORY[37e78782-dd9b-4c37-b305-9c17a323373c]). While Biomapper aims to be robust, awareness of upstream data quality is crucial.
*   **Update Cadence and Versioning:** Datasets are updated at different intervals. Mappings generated at one point in time might become stale. While Biomapper doesn't currently implement automated data updates, the provenance of mappings (which data versions were used) is important context.

## Entity-Type Specific Complexities (Vertical and Horizontal Extensibility)

Biomapper aims for both vertical (deepening capabilities for one entity type) and horizontal (adding new entity types) extensibility. Each entity type (proteins, metabolites, genes, etc.) presents unique mapping challenges:

*   **Proteins:**
    *   Complex lifecycle (isoforms, PTMs, cleavage products).
    *   UniProt is a central hub, but mapping to gene identifiers (Ensembl, NCBI Gene) or specific assay IDs (UKBB) is common.
    *   Historical ID changes in UniProt are a major complexity driver.
*   **Metabolites:**
    *   More fragmented identifier landscape (ChEBI, PubChem, HMDB, KEGG, CAS, InChIKeys).
    *   Stereoisomers and chemical similarity add layers of complexity beyond simple ID matching.
    *   Mapping often involves chemical structure comparisons or ontology-based reasoning, which may require specialized clients or action types.
*   **Genes:**
    *   Mapping between different gene nomenclatures (HGNC, Ensembl, NCBI Gene) and to protein products.
    *   Ortholog mapping across species (not currently a primary focus but a common bioinformatics task).
*   **Clinical/Phenotypic Data:**
    *   Mapping to standardized terminologies (SNOMED, ICD, HPO, LOINC).
    *   Often involves natural language processing or expert curation, which is beyond simple ID-to-ID mapping.

**Extensibility Implications:**
*   **Vertical (e.g., better protein mapping):** Requires more sophisticated `action.type`s for YAML strategies, more specialized clients (e.g., for PTM-aware mapping), and potentially deeper integration with resources like UniProt.
*   **Horizontal (e.g., adding metabolite mapping):** Requires new `*_config.yaml` files, new sets of ontology definitions, new client implementations for metabolite-specific databases/APIs, and potentially new `action.type`s tailored to chemical mapping challenges.

## Developing Action Types for YAML Mapping Strategies

The YAML-defined mapping strategy framework (see `/home/ubuntu/biomapper/roadmap/technical_notes/core_mapping_logic/yaml_defined_mapping_strategies.md`) relies on modular `action.type` handlers. Developing these presents its own set of considerations:

*   **Granularity:** Action types should be granular enough to be reusable building blocks but not so fine-grained that strategies become overly verbose. For example, `CONVERT_IDENTIFIERS_LOCAL` is a good level of abstraction.
*   **Interface Definition:** Each action type needs a clear contract: what parameters it expects from the YAML, what data it operates on (typically a list of identifiers from the previous step), and what data it outputs.
*   **State Management:** The `MappingExecutor` will need to manage the flow of data (the list of identifiers) between steps. Action handlers should be largely stateless or rely on the `MappingExecutor` for necessary context (like access to client instances or database sessions).
*   **Parameterization:** Action types should be configurable through parameters in the YAML (e.g., `endpoint_context`, `output_ontology_type` for `CONVERT_IDENTIFIERS_LOCAL`). This allows the same action logic to be used in different contexts.
*   **Error Handling:** Each action handler must define how it handles errors (e.g., an ID not found, an API call failing). It might return partial results, log errors, or raise exceptions that the `MappingExecutor` must catch and handle.
*   **Testing:** Action handlers must be unit-testable in isolation to ensure their logic is correct before being integrated into larger strategies.
*   **Discovery/Registration:** The `MappingExecutor` needs a mechanism to discover and dispatch to the correct Python handler module based on the `action.type` string in the YAML.

## One-to-Many Mappings and Bidirectional Reconciliation

One-to-many mappings (where a single source identifier maps to multiple target identifiers) are a common occurrence and introduce significant complexity, especially for bidirectional reconciliation:

*   **Sources of One-to-Many Mappings:**
    *   **Biological Reality:** Gene duplication, protein families, isoforms, demerged UniProt entries.
    *   **Data Aggregation:** A single concept in one dataset might correspond to multiple, more granular concepts in another.
    *   **Ambiguity/Non-Specificity:** An identifier might be inherently ambiguous.
    *   **Composite Identifiers:** As seen with Arivale UniProt IDs, if a composite ID is split, it creates a one-to-many situation from the original composite string.
*   **Challenges in Unidirectional Mapping:**
    *   YAML strategies need to decide how to handle multiple results from an action step. Does the list of identifiers grow? Are multiple results passed as tuples? This affects subsequent steps.
    *   Provenance becomes critical: if one ID maps to three, each of those three mappings needs to be traceable.
*   **Challenges in Bidirectional Reconciliation (`phase3_bidirectional_reconciliation.py`):
    *   **Symmetry Breaking:** If A maps to B1, B2 and B1 maps back to A, but B2 maps to A and C, how is the A-B1 vs A-B2 relationship prioritized or chosen as canonical?
    *   **Defining a "True" Match:** When one side is one-to-many, and the other is one-to-one (or also one-to-many), defining what constitutes a confirmed bidirectional match becomes complex. The `is_one_to_many_target` flag (fixed in MEMORY[a2b09543-7994-4538-8fcf-1078d5516123]) is a step towards managing this, but downstream logic must interpret these flags correctly.
    *   **Canonical Representative Selection:** Often, a single "best" mapping is desired. This requires scoring mechanisms or rule-sets (e.g., prefer direct matches, prefer matches with more evidence, use ontology hierarchy) which can be complex to generalize.

## Complexities in the Generalized Iterative Approach

The default iterative mapping strategy, while powerful, also has inherent complexities:

*   **Path Explosion:** Without careful pruning or prioritization of mapping paths (`priority` in `mapping_paths` config), the number of potential mapping routes can become very large, leading to performance issues or spurious mappings.
*   **Cycle Detection:** Iterative mapping can potentially lead to cycles (A -> B -> C -> A). Logic must be in place to detect and break such cycles or limit iteration depth.
*   **Optimal Path Selection:** When multiple paths exist between two identifiers, the iterative approach might find several. Determining the "best" or most reliable path often relies on the `priority` settings of individual paths and resources, which can be hard to tune globally.
*   **Provenance Tracking:** Tracing the exact sequence of client calls and intermediate identifiers that led to a final mapping can be complex in a deeply iterative process. The `MappingResult.mapping_path_details` aims to capture this but needs to be robust.
*   **Error Propagation:** An error or a low-confidence mapping from an early iteration can propagate and affect subsequent mappings.
*   **Scalability:** For very large sets of input identifiers or a very densely connected `metamapper.db`, the iterative approach can be computationally intensive, despite optimizations like client caching.

*(More examples and explanations will be added as identified)*
