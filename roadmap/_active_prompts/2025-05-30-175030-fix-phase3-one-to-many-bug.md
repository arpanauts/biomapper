# Prompt for Claude Code Instance: Fix One-To-Many Bug in Phase 3 Reconciliation

**Source Prompt:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-05-30-175030-fix-phase3-one-to-many-bug.md`

## 1. Task Overview

This task requires you to debug and fix a known bug in the `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py` script. The bug relates to the `is_one_to_many_target` flag, which is reportedly being incorrectly set to TRUE for all records in the output, compromising canonical mapping selection. This issue was previously documented in project memory (MEMORY[4112ab74-f8f2-4251-bb2c-e0c0f3d233a5]).

Your goal is to correct the logic within the `perform_bidirectional_validation` function (or related functions) to ensure `is_one_to_many_target` is set accurately based on whether a target ID is mapped by multiple distinct source IDs after validation.

## 2. Project Context & Guidelines

*   Familiarize yourself with the Biomapper project structure by reviewing `/home/ubuntu/biomapper/CLAUDE.md`.
*   The script to be modified is: `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`.
*   The bug specifically impacts the reliability of one-to-many relationship handling during bidirectional validation.
*   All Python package management for this project should be done using Poetry.

## 3. Input Files & Setup

*   **Core Script:** `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`.
*   **Test Data:** You may need sample input files for Phase 1 and Phase 2 mappings that would feed into Phase 3. A previous test script `/home/ubuntu/biomapper/scripts/test_one_to_many_in_real_world.sh` (MEMORY[4ba6593d-d7d3-43e5-aa23-4c515c37b3ac]) used:
    *   Phase 1 Input: `/home/ubuntu/biomapper/data/UKBB_Protein_Meta.tsv`
    *   Phase 2 Input: `/home/ubuntu/biomapper/data/arivale_proteomics_metadata.tsv`
    You might need to generate intermediate output files from `map_ukbb_to_arivale.py` (which is used for both Phase 1 and Phase 2 in the test script, see MEMORY[80f78cfe-d820-47aa-af0a-c83de067d440]) to serve as input for `phase3_bidirectional_reconciliation.py`. Focus on creating a scenario where one-to-many mappings exist and can be tested.
*   **Environment:** Biomapper project environment, managed with Poetry.

## 4. Detailed Steps & Requirements

1.  **Understand the Bug:** Review the description in MEMORY[4112ab74-f8f2-4251-bb2c-e0c0f3d233a5]. The core issue is that `is_one_to_many_target` is always TRUE.
2.  **Locate the Logic:** Identify where `is_one_to_many_target` is determined and set within `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`, likely in `perform_bidirectional_validation` or a closely related function.
3.  **Debug:** Analyze the current logic to understand why it's failing. Add logging if necessary to trace data flow and variable states.
4.  **Implement Fix:** Correct the logic to accurately identify and flag one-to-many target relationships. A target ID should be marked as part of a one-to-many relationship if, *after bidirectional validation*, multiple distinct source IDs map to it.
5.  **Test:**
    *   Prepare or use existing test data that includes clear one-to-many and one-to-one scenarios.
    *   Run the modified `phase3_bidirectional_reconciliation.py` script.
    *   Verify that the `is_one_to_many_target` column in the output is correctly populated (i.e., TRUE only for actual one-to-many target cases, FALSE otherwise).

## 5. Deliverables

Create a single Markdown feedback file named `YYYY-MM-DD-HHMMSS-feedback-fix-phase3-one-to-many-bug.md` (use UTC timestamp of task completion) in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory. This file must include:

1.  **Summary of Actions:** Briefly describe your debugging process and the fix implemented.
2.  **Code Changes:** A `diff` of the changes made to `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`.
3.  **Explanation of the Fix:** Clearly explain how your changes correct the bug.
4.  **Testing Done:** Describe the test data or scenarios you used and how you verified the fix. Include snippets of output if illustrative.
5.  **Any Challenges Encountered or Open Questions.**

## 6. Tool Permissions
You will need `Edit` permissions for `/home/ubuntu/biomapper/scripts/phase3_bidirectional_reconciliation.py`.
