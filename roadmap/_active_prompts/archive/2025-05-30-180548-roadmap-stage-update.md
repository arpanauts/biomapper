# Task: Update Roadmap Stages for Recently Completed Features

**Date:** 2025-05-30
**Objective:** Move completed features to the `3_completed` stage and generate completion artifacts using `roadmap/3_completed/STAGE_GATE_PROMPT_COMPL.md`.

**Context:**
Three features/tasks have been recently completed and their feedback reports are available. We need to update the roadmap to reflect this.

**Feature 1: MappingExecutor Performance Optimization**
-   **Current Location (if any):** `/home/ubuntu/biomapper/roadmap/2_inprogress/mapping_executor_performance_optimization/`
-   **Original Prompt:** `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-30-174500-diagnose-mapping-executor-performance.md`
-   **Feedback Report:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-30-180129-feedback-diagnose-mapping-executor-performance.md`

**Feature 2: Update `populate_metamapper_db.py` for UKBB/Arivale File Resources**
-   **Current Location (if any):** None (managed via `_active_prompts`)
-   **Original Prompt:** `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-30-175035-update-populate-db-ukbb-arivale-files.md`
-   **Feedback Report:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-30-175527-feedback-update-populate-db-ukbb-arivale-files.md`

**Feature 3: Fix Phase 3 One-To-Many Bug in `phase3_bidirectional_reconciliation.py`**
-   **Current Location (if any):** None (managed via `_active_prompts`)
-   **Original Prompt:** `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-30-175030-fix-phase3-one-to-many-bug.md`
-   **Feedback Report:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-30-175806-feedback-fix-phase3-one-to-many-bug.md`

**Instructions:**

**Part 1: Process `MappingExecutor Performance Optimization`**

1.  **Move Feature Folder:**
    *   Move the directory `/home/ubuntu/biomapper/roadmap/2_inprogress/mapping_executor_performance_optimization/` to `/home/ubuntu/biomapper/roadmap/3_completed/mapping_executor_performance_optimization/`.
2.  **Populate Missing Files (if necessary):**
    *   The folder `/home/ubuntu/biomapper/roadmap/3_completed/mapping_executor_performance_optimization/` might be missing standard planning documents (`README.md`, `spec.md`, `design.md`) or `implementation_notes.md`.
    *   Create a simple `README.md` in this folder. Content: "This feature focused on diagnosing and optimizing the MappingExecutor's performance."
    *   Create an `implementation_notes.md` in this folder. Synthesize its content primarily from the "Summary of Steps Taken", "Performance Bottleneck Analysis", "Optimization Implementation", and "Performance Improvement Evidence" sections of its feedback report (`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-30-180129-feedback-diagnose-mapping-executor-performance.md`).
3.  **Execute Completion Stage Gate:**
    *   Run the instructions in `/home/ubuntu/biomapper/roadmap/3_completed/STAGE_GATE_PROMPT_COMPL.md` for the feature folder `/home/ubuntu/biomapper/roadmap/3_completed/mapping_executor_performance_optimization/`.
    *   This involves:
        *   Generating `summary.md` (use content from the feedback report, especially the "Conclusion" section).
        *   Generating a log entry for `../../_reference/completed_features_log.md`.
        *   Suggesting architecture review points if applicable.

**Part 2: Process `Update populate_metamapper_db.py`**

1.  **Create Feature Folder:**
    *   Create a new directory: `/home/ubuntu/biomapper/roadmap/3_completed/update_populate_metamapper_db_ukbb_arivale/`
2.  **Create Supporting Documents:**
    *   Inside this new folder, create `README.md`. Content: "This feature updated `populate_metamapper_db.py` to include new file-based lookup resources for UKBB protein metadata and enhanced Arivale protein metadata lookups."
    *   Inside this new folder, create `implementation_notes.md`. Synthesize its content from the "Summary of Actions" and "Code Changes" (if applicable, or refer to the feedback diff) sections of its feedback report (`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-30-175527-feedback-update-populate-db-ukbb-arivale-files.md`).
3.  **Execute Completion Stage Gate:**
    *   Run the instructions in `/home/ubuntu/biomapper/roadmap/3_completed/STAGE_GATE_PROMPT_COMPL.md` for the feature folder `/home/ubuntu/biomapper/roadmap/3_completed/update_populate_metamapper_db_ukbb_arivale/`.
    *   Generate `summary.md` (use content from the feedback report).
    *   Generate a log entry for `../../_reference/completed_features_log.md`.

**Part 3: Process `Fix Phase 3 One-To-Many Bug`**

1.  **Create Feature Folder:**
    *   Create a new directory: `/home/ubuntu/biomapper/roadmap/3_completed/fix_phase3_one_to_many_bug/`
2.  **Create Supporting Documents:**
    *   Inside this new folder, create `README.md`. Content: "This feature fixed a bug in `phase3_bidirectional_reconciliation.py` where the `is_one_to_many_target` flag was incorrectly set."
    *   Inside this new folder, create `implementation_notes.md`. Synthesize its content from the "Summary of Actions", "Code Changes" (diff), and "Explanation of the Fix" sections of its feedback report (`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-30-175806-feedback-fix-phase3-one-to-many-bug.md`).
3.  **Execute Completion Stage Gate:**
    *   Run the instructions in `/home/ubuntu/biomapper/roadmap/3_completed/STAGE_GATE_PROMPT_COMPL.md` for the feature folder `/home/ubuntu/biomapper/roadmap/3_completed/fix_phase3_one_to_many_bug/`.
    *   Generate `summary.md` (use content from the feedback report).
    *   Generate a log entry for `../../_reference/completed_features_log.md`.

**Deliverables:**
-   The three feature folders correctly placed or created in `/home/ubuntu/biomapper/roadmap/3_completed/`.
-   Each feature folder containing `README.md`, `implementation_notes.md`, and a generated `summary.md`.
-   Three new log entries appended to `/home/ubuntu/biomapper/roadmap/_reference/completed_features_log.md`.
-   A feedback report detailing the actions taken to fulfill this prompt.
