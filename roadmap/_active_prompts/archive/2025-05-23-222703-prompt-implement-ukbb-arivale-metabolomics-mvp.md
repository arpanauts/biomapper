# Prompt for Claude Code Instance: Implement MVP UKBB NMR to Arivale Metabolomics Mapping

**Date:** 2025-05-23
**Time (UTC):** 22:27:03
**Feature:** MVP - UKBB NMR to Arivale Metabolomics Mapping

## 1. Objective

Implement the mapping functionality to link UKBB NMR metabolite data to Arivale metabolomics data using the `PubChemRAGMappingClient`, as detailed in the provided project documents. This involves creating two Python scripts: one for testing the RAG client and one for the main mapping process.

## 2. Key Documents (Primary Source of Truth)

Your implementation **must** strictly adhere to the specifications, design, tasks, and notes outlined in these documents. Please review them thoroughly before starting:

*   **Specification:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_metabolomics/spec.md`
*   **Design:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_metabolomics/design.md`
*   **Task List:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_metabolomics/task_list.md` (Follow this for implementation steps)
*   **Implementation Notes:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_metabolomics/implementation_notes.md`

## 3. Input Data Files

*   **UKBB NMR Metadata:** `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv`
*   **Arivale Metabolomics Metadata:** `/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv`

## 4. Deliverables

### 4.1. Python Scripts
Create the following Python scripts in the `/home/ubuntu/biomapper/scripts/mvp_ukbb_arivale_metabolomics/` directory. Ensure these scripts are well-commented, follow PEP 8 guidelines, and include necessary error handling and logging.

1.  **`test_rag_client_arivale.py`:**
    *   Purpose: Validate the `PubChemRAGMappingClient` on a sample of Arivale metabolomics data.
    *   Functionality: As per `spec.md` (Section 2.1) and `design.md` (Section 2.1).
    *   Output: Console output detailing test results (input name, ground truth CID, RAG CID(s), confidence, match status) and overall accuracy.

2.  **`map_ukbb_to_arivale_metabolomics.py`:**
    *   Purpose: Perform the main mapping of UKBB NMR titles to Arivale metabolomics entries.
    *   Functionality: As per `spec.md` (Section 2.2) and `design.md` (Section 2.2).
    *   Output:
        *   A TSV file named `ukbb_to_arivale_metabolomics_mapping.tsv` saved to `/home/ubuntu/biomapper/output/`. The directory `/home/ubuntu/biomapper/output/` should be created if it doesn't exist.
        *   The TSV columns and format must match `spec.md` (Section 3).
        *   Console output summarizing mapping statistics (e.g., count of each `mapping_status`).

### 4.2. Dependencies
*   If new dependencies are required (e.g., `pandas` if not already present), list them in your feedback. Assume standard libraries like `csv` are available. The project uses Poetry for dependency management (`pyproject.toml`).

## 5. Key Components & Technologies
*   **`PubChemRAGMappingClient`:** This is a core component. Assume it's available within the `biomapper` project structure and can be imported. You will need to instantiate and use its `map_identifiers` method. Refer to `implementation_notes.md` for assumptions about its interface.
*   **Python 3:** All code should be Python 3 compatible.
*   **Logging:** Implement appropriate logging (e.g., using the `logging` module) for diagnostics, especially for errors, warnings, and key processing steps.

## 6. Adherence to Project Standards
*   **Iterative Mapping Strategy:** While this MVP focuses on a specific RAG-based step, be mindful of the broader context in `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md`.
*   **MVP Priorities:** Align with `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-08-mvp-refinement-and-dual-agent-plan.md`.
*   **Error Handling:** Implement robust error handling (e.g., for file I/O, API calls if `PubChemRAGMappingClient` makes them).
*   **Code Comments:** Ensure code is well-commented.

## 7. Success Criteria
*   All tasks in `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_metabolomics/task_list.md` are completed.
*   Both Python scripts are created, are executable, and function as specified.
*   The `test_rag_client_arivale.py` script produces clear, interpretable output.
*   The `map_ukbb_to_arivale_metabolomics.py` script generates the output TSV file in the correct format and location, and prints summary statistics.
*   The implementation adheres to the design and specifications.

## 8. Feedback File

Upon completion of all tasks, or if you encounter critical blockers or require clarification, create a feedback file named `YYYY-MM-DD-HHMMSS-feedback-implement-ukbb-arivale-metabolomics-mvp.md` in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory.

The feedback file should include:
*   A summary of the work completed.
*   Confirmation of deliverables (scripts created, output file generated).
*   Any issues encountered and how they were resolved.
*   Any assumptions made.
*   Any questions or points for clarification.
*   A list of any new dependencies added.
*   Brief results from `test_rag_client_arivale.py` (e.g., accuracy on sample).
*   Summary statistics from `map_ukbb_to_arivale_metabolomics.py` (e.g., counts for each mapping status).

---
Please proceed with the implementation.
