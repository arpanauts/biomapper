# Prompt for Claude Code Instance: Implement MVP UKBB NMR to Arivale Chemistries Mapping

**Date:** 2025-05-23
**Time (UTC):** 22:38:06
**Feature:** MVP - UKBB NMR to Arivale Chemistries Mapping

## 1. Objective

Implement the mapping functionality to link UKBB NMR metabolite data (`title` field) to Arivale Chemistries data (`TestDisplayName` or `TestName` fields) using direct name matching, as detailed in the provided project documents. This involves creating one Python script for the mapping process.

## 2. Key Documents (Primary Source of Truth)

Your implementation **must** strictly adhere to the specifications, design, tasks, and notes outlined in these documents. Please review them thoroughly before starting:

*   **README:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_chemistries/README.md`
*   **Specification:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_chemistries/spec.md`
*   **Design:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_chemistries/design.md`
*   **Task List:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_chemistries/task_list.md` (Follow this for implementation steps)
*   **Implementation Notes:** `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_chemistries/implementation_notes.md`

## 3. Input Data Files

*   **UKBB NMR Metadata:** `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv`
*   **Arivale Chemistries Metadata:** `/procedure/data/local_data/ARIVALE_SNAPSHOTS/chemistries_metadata.tsv`

## 4. Deliverables

### 4.1. Python Script
Create the following Python script in the `/home/ubuntu/biomapper/scripts/mvp_ukbb_arivale_chemistries/` directory. Ensure this script is well-commented, follows PEP 8 guidelines, and includes necessary error handling and logging.

1.  **`map_ukbb_to_arivale_chemistries.py`:**
    *   Purpose: Perform the mapping of UKBB NMR titles to Arivale Chemistries entries using direct name matching.
    *   Functionality: As per `spec.md` and `design.md`.
    *   Output:
        *   A TSV file named `ukbb_to_arivale_chemistries_mapping.tsv` saved to `/home/ubuntu/biomapper/output/`. The directory `/home/ubuntu/biomapper/output/` should be created if it doesn't exist.
        *   The TSV columns and format must match `spec.md` (Section 3).
        *   Console output summarizing mapping statistics (e.g., count of each `mapping_status`).

### 4.2. Dependencies
*   If new dependencies are required (e.g., `pandas` if not already present and part of the project's `pyproject.toml`), list them in your feedback. Assume standard libraries like `csv`, `logging`, `argparse` are available. The project uses Poetry for dependency management.

## 5. Key Components & Technologies
*   **Direct Name Matching:** The core logic involves normalizing names (lowercase, trim whitespace) from UKBB `title` and Arivale `TestDisplayName`/`TestName` and comparing them.
*   **Python 3:** All code should be Python 3 compatible.
*   **Logging:** Implement appropriate logging (e.g., using the `logging` module) for diagnostics, especially for errors, warnings, and key processing steps (like verified Arivale column names).
*   **Pandas (Recommended):** For data handling.

## 6. Adherence to Project Standards
*   **Iterative Mapping Strategy:** While this MVP uses direct matching, be mindful of the broader context in `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md`.
*   **MVP Priorities:** Align with `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-08-mvp-refinement-and-dual-agent-plan.md`.
*   **Error Handling:** Implement robust error handling (e.g., for file I/O).
*   **Code Comments:** Ensure code is well-commented.
*   **CRITICAL:** Verify and log the exact Arivale Chemistries column names used from `chemistries_metadata.tsv` as per `implementation_notes.md`.

## 7. Success Criteria
*   All tasks in `/home/ubuntu/biomapper/roadmap/2_inprogress/mvp_ukbb_to_arivale_chemistries/task_list.md` are completed.
*   The Python script `map_ukbb_to_arivale_chemistries.py` is created, is executable, and functions as specified.
*   The script generates the output TSV file `ukbb_to_arivale_chemistries_mapping.tsv` in the correct format and location, and prints summary statistics.
*   The implementation adheres to the design and specifications.

## 8. Feedback File

Upon completion of all tasks, or if you encounter critical blockers or require clarification, create a feedback file named `YYYY-MM-DD-HHMMSS-feedback-implement-ukbb-arivale-chemistries-mvp.md` in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory.

The feedback file should include:
*   A summary of the work completed.
*   Confirmation of deliverables (script created, output file generated).
*   The actual Arivale Chemistries column names identified and used.
*   Any issues encountered and how they were resolved.
*   Any assumptions made.
*   Any questions or points for clarification.
*   A list of any new dependencies added.
*   Summary statistics from `map_ukbb_to_arivale_chemistries.py` (e.g., counts for each mapping status).

---
Please proceed with the implementation.
