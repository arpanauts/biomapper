# Biomapper Status Update: MVP Refinement & Dual-Agent Strategy (May 8, 2025)

This document provides a comprehensive status update for the Biomapper project, reflecting recent discussions on refining the Minimum Viable Product (MVP) for UKBB-Arivale protein mapping, the current project state, technical context, and the planned next steps, particularly considering a dual-agent development approach.

## 1. Recent Accomplishments (In Recent Memory)

*   **Clarification of True MVP Requirements:** Through detailed discussion, we've reached a clear understanding that the existing `direct_mapper_run.py` is insufficient. The **true MVP** must implement the full `iterative_mapping_strategy.md`, including robust, independent forward and reverse mappings, and generate rich, detailed CSV outputs.
*   **Defined 3-Phase MVP Development Plan:** A structured, three-phase plan has been outlined to achieve the true MVP (detailed in Next Steps).
*   **Understanding of Current Validation Logic:** Clarified that the "UnidirectionalSuccess" in `direct_mapper_run.py` is a simple reverse lookup within Arivale metadata, not the comprehensive bidirectional validation envisioned by `iterative_mapping_strategy.md` (which involves independent reverse mapping).
*   **Bidirectional Validation Feature Implementation (from 2025-05-07):**
    *   A three-tiered validation status system (Validated, UnidirectionalSuccess, Failed) was added to the `MappingExecutor`.
    *   `validate_bidirectional` parameter added to `MappingExecutor.execute_mapping`.
    *   `_reconcile_bidirectional_mappings` method developed.
    *   This existing feature in `MappingExecutor` provides a foundation for the final reconciliation phase of the new 3-phase MVP plan, though the inputs to it will be more robust.
*   **Consolidated Progress (from 2025-05-05):** Continued stability and enhancements in core components like error handling, composite identifier handling, centralized configuration, and iterative mapping foundations within `MappingExecutor`.

## 2. Current Project State

*   **Overall:** The project is at a pivotal point. We've identified the limitations of the current `direct_mapper_run.py` script for achieving the desired comprehensive protein mapping. The focus has shifted to implementing the sophisticated, iterative mapping strategy documented in `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md` as the true MVP.
*   **Component Status:**
    *   `direct_mapper_run.py`: Recognized as a preliminary script. While it processes the full dataset, it lacks the iterative logic and rich output needed for the MVP.
    *   `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md`: Confirmed as the **authoritative blueprint** for the mapping process (both forward and reverse).
    *   `biomapper/core/mapping_executor.py`: Has seen significant enhancements (error handling, composite IDs, initial bidirectional validation logic). However, the *full iterative mapping logic* (secondary ID conversions, multi-step paths) as defined in the strategy document needs to be robustly implemented or orchestrated by it.
    *   `mapping/clients/`: Existing clients like `ArivaleMetadataLookupClient` are functional. **New client functionality (or a dedicated UniProt client) will be required** for secondary ID conversions (e.g., Gene Name to UniProtKB AC, ENSEMBL to UniProtKB AC).
    *   Reporting/Output: Current output from `direct_mapper_run.py` is too simplistic. The MVP requires a rich, multi-column CSV/TSV that merges source, target, and mapping path details.
*   **Outstanding Critical Issues/Blockers:**
    1.  **Implementation of the 3-Phase MVP Plan:** This is the primary focus.
    2.  **Development/Integration of UniProt Client(s):** Essential for secondary-to-primary ID conversions in both forward (UKBB Gene Name -> UniProt) and reverse (Arivale ENSEMBL/Gene Name -> UniProt) mapping iterations.
    3.  **Rich Output Generation:** Designing and implementing the logic to produce the comprehensive CSV/TSV files.

## 3. Technical Context

*   **Architectural Decisions:**
    *   **Adherence to `iterative_mapping_strategy.md`:** This document is the definitive guide for both forward and reverse mapping logic.
    *   **Shift from `direct_mapper_run.py`:** Moving towards new, dedicated scripts/modules for the iterative forward and reverse mapping processes, likely orchestrated by or using an enhanced `MappingExecutor`.
    *   **3-Phase Development Approach:** Adopted for building the MVP: (1) Iterative Forward Mapping & Rich Output, (2) Iterative Reverse Mapping & Rich Output, (3) Bidirectional Reconciliation.
*   **Key Data Structures, Algorithms, or Patterns:**
    *   The iterative mapping steps: Direct Primary Mapping, Secondary-to-Primary Conversion (prioritized), Indirect Primary Mapping.
    *   Requirement for merged DataFrames to produce rich outputs (combining original source data, mapping results, and target entity metadata).
    *   Use of UniProt APIs/services for ID conversions.
*   **Learnings:**
    *   The distinction between simple reverse lookups and comprehensive, independent iterative reverse mapping is crucial for true bidirectional validation.
    *   The need for precise definition of all `source_`, `target_`, and `mapping_path_` columns in the output.
*   **Dual-Agent Context (`2025-04-30-dual-agent-status.md` influences):**
    *   The 3-phase plan lends itself well to a dual-agent approach. Tasks can be parallelized (e.g., one agent on forward mapping, another on reverse) or specialized (e.g., one on client/API integration, another on data processing and output generation).
    *   Clear interfaces and data formats between phases/components will be critical for smooth collaboration.

## 4. Next Steps (MVP Implementation Plan)

The following 3-phase plan will guide the development of the true UKBB-Arivale protein mapping MVP.

**Phase 1: Robust Iterative FORWARD Mapping (UKBB -> Arivale) with Rich Output**

*   **Goal:** Implement the full iterative strategy for UKBB to Arivale and generate a detailed CSV output.
*   **Tasks:**
    1.  **Develop/Enhance Forward Mapping Script (e.g., `iterative_forward_mapper.py` or significantly refactor `direct_mapper_run.py`):**
        *   **a. Load UKBB Data:** From `/home/ubuntu/biomapper/data/UKBB_Protein_Meta_full.tsv`.
        *   **b. Direct Primary Mapping (UKBB UniProt -> Arivale ID):** Map existing `UNIPROTKB_AC` to `ARIVALE_PROTEIN_ID`. Record provenance.
        *   **c. Secondary to Primary Conversion (UKBB `GENE_NAME` -> `UNIPROTKB_AC`):**
            *   For unmapped UKBB entries, extract `GENE_NAME` (from "Assay" column).
            *   **Implement/Utilize UniProt Client:** Convert `GENE_NAME` to `UNIPROTKB_AC` (e.g., via UniProt ID mapping API). Record provenance.
            *   **(Immediate Sub-Task): Investigate and select the best UniProt API/Python library for this.**
        *   **d. Indirect Primary Mapping (Derived UKBB UniProt -> Arivale ID):** Use `UNIPROTKB_AC`s from (1c) to map to `ARIVALE_PROTEIN_ID`. Record provenance.
    2.  **Generate Rich Forward Output CSV:**
        *   **a. Load Arivale Metadata:** From `/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv`.
        *   **b. Merge Data:** Combine original UKBB data, mapping results (1b, 1d), and Arivale metadata.
        *   **c. Structure Output:** Create all `source_*`, `target_*` columns, `mapping_path_details`, `confidence_score`, `hop_count`, etc.

**Phase 2: Robust Iterative REVERSE Mapping (Arivale -> UKBB) with Rich Output**

*   **Goal:** Implement an independent iterative strategy for Arivale to UKBB and generate its detailed CSV output.
*   **Tasks:**
    1.  **Develop Reverse Mapping Script (e.g., `iterative_reverse_mapper.py`):**
        *   **a. Define Input:** List of unique Arivale Protein IDs.
        *   **b. Direct Primary Reverse Mapping (Arivale ID -> Arivale UniProt):** Find associated `UNIPROTKB_AC` from Arivale metadata. Record provenance.
        *   **c. Secondary to Primary Conversion (Arivale Secondary IDs -> Arivale UniProt):**
            *   For unmapped Arivale entries, extract secondary IDs (`ENSEMBL_PROTEIN`, `GENE_NAME`, `ENSEMBL_GENE` from Arivale metadata).
            *   **Implement/Utilize UniProt Client(s):** Convert these to `UNIPROTKB_AC`. Record provenance.
        *   **d. Target:** The `UNIPROTKB_AC`s from (2b, 2c) are the targets (UKBB UniProt IDs).
    2.  **Generate Rich Reverse Output CSV:**
        *   **a. Load UKBB Metadata.**
        *   **b. Merge Data:** Combine original Arivale data (if starting with more than just IDs), mapping results, and UKBB metadata.
        *   **c. Structure Output:** Create `source_*` (Arivale), `target_*` (UKBB) columns, `mapping_path_details`, etc.

**Phase 3: Bidirectional Reconciliation and Final Combined Output**

*   **Goal:** Combine Phase 1 & 2 results for a final, comprehensive mapping with robust bidirectional validation status.
*   **Tasks:**
    1.  **Develop Reconciliation Script (e.g., `reconcile_mappings.py`):**
        *   **a. Input:** Rich CSV from Phase 1 (UKBB->Arivale) and Phase 2 (Arivale->UKBB).
        *   **b. Logic:** Compare results. For each `UKBB_UniProt_A` -> `Arivale_ID_X` (from Phase 1), check if `Arivale_ID_X` mapped back to `UKBB_UniProt_A` (in Phase 2).
        *   **c. Assign Final `bidirectional_validation_status`:** (e.g., "Validated_Bidirectional_Exact", "Validated_Forward_Unidirectional", "Validated_Reverse_Unidirectional", "Conflict/Mismatch").
    2.  **Output:** A single, comprehensive CSV presenting the reconciled UKBB <-> Arivale mappings.

**Dual-Agent Task Distribution Considerations for Next Steps:**

*   **Parallel Development:** Agent A could take Phase 1, Agent B takes Phase 2. Both collaborate on Phase 3.
*   **Specialized Roles:**
    *   *Agent Core/API:* Focus on implementing/integrating the UniProt client(s) (used in P1 & P2), and potentially the core iterative logic within `MappingExecutor` if these new scripts are to become methods of it.
    *   *Agent Data/Scripting:* Focus on the data loading, DataFrame manipulation, merging, and CSV generation aspects of the P1, P2, and P3 scripts.
*   **Initial Focus:** One agent could start the UniProt client investigation/implementation (P1.1.c) while the other starts structuring the data loading and direct primary mapping for Phase 1 (P1.1.a, P1.1.b).

## 5. Open Questions & Considerations

*   **UniProt Client:** Which specific UniProt API endpoints or Python libraries are best suited for the required ID conversions (Gene Name -> UniProt, ENSEMBL -> UniProt)? Are there existing robust clients in the `biomapper` project or organization that can be leveraged/adapted?
*   **Rich Output Columns:** Need to finalize the *exact* list of all `source_*`, `target_*`, `mapping_path_details` (and its sub-fields like `derivation_method`, `intermediate_ids`), and other metadata columns for the outputs of Phase 1, Phase 2, and Phase 3.
*   **Script Orchestration:** Will the new scripts (`iterative_forward_mapper.py`, etc.) be standalone, or will they become methods/workflows orchestrated by the main `MappingExecutor`? The `iterative_mapping_strategy.md` implies `MappingExecutor` handles this.
*   **Error Handling:** Define error handling and logging strategies within these new iterative mapping scripts.
*   **Configuration:** How will parameters specific to these new scripts (e.g., input file paths if not hardcoded, API keys for UniProt) be managed? (Leverage existing `Config` system?)
*   **Dual-Agent Coordination:**
    *   If a shared UniProt client module is developed, how to manage its development and integration by both agents?
    *   What are the precise data handoff formats (e.g., DataFrame schemas) between Phase 1, Phase 2, and Phase 3, especially if handled by different agents?
*   **Relevance of `direct_mapper_run.py`:** Should this script be deprecated/archived once Phase 1 is functional, or evolved?
*   **Confidence Scoring:** How will confidence scores be determined in the iterative process, especially for multi-hop paths or those involving secondary ID conversions?
*   **Testing:** What is the testing strategy for these new, more complex mapping scripts?

This status update should provide a clear path forward. The immediate priority is to begin Phase 1, starting with the UniProt client investigation and the initial steps of the forward mapping script.
