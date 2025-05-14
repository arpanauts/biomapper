# How to Update Roadmap Stages from a Status Update

## 1. Introduction

This document provides a step-by-step guide on how to use a project status update (typically found in `roadmap/_status_updates/`) to populate and manage the staged feature development workflow within the `/home/ubuntu/biomapper/roadmap/` directory. This system helps track features from raw ideas through planning, implementation, completion, and archiving, leveraging AI assistance via predefined stage gate prompts.

## 2. Prerequisites

Before starting, ensure the following are in place:

- The core roadmap directories: `0_backlog/`, `1_planning/`, `2_inprogress/`, `3_completed/`, `4_archived/`, `_reference/`, `_templates/`.
- Stage Gate Prompt files exist:
    - `roadmap/1_planning/STAGE_GATE_PROMPT_PLAN.md`
    - `roadmap/2_inprogress/STAGE_GATE_PROMPT_PROG.md`
    - `roadmap/3_completed/STAGE_GATE_PROMPT_COMPL.md`
- Template files (optional but recommended) exist in `roadmap/_templates/`.

## 3. General Workflow Overview

1.  **Start with the Latest Status Update:** Read the most recent `.md` file in `roadmap/_status_updates/`.
2.  **Identify & Categorize:** Extract key accomplishments, ongoing work, new ideas, blockers, and next steps. Determine the current lifecycle phase for each.
3.  **Process Through Stages:** Use the steps below to create or move items into the appropriate stage folders (`0_backlog` to `4_archived`).
4.  **Leverage AI & Stage Gates:** For transitions between planning, in-progress, and completed, instruct your AI assistant (e.g., Cascade) to execute the relevant `STAGE_GATE_PROMPT_*.md` file.

## 4. Detailed Step-by-Step Instructions

### Step 1: Review the Status Update

Thoroughly read the latest status update document. Actively look for information that maps to roadmap items, such as:

-   **New Feature Ideas:** Concepts or requirements mentioned for the first time or as future considerations.
-   **Planned Work:** Items explicitly stated as "next steps," "priorities," or "to be planned."
-   **Work In Progress:** Tasks or features currently under active development.
-   **Completed Tasks:** Features, bug fixes, or milestones recently finished and verified.
-   **Blocked or Deferred Items:** Work that is stalled or postponed.

### Step 2: Create/Update `0_backlog/` Items

For any new, raw ideas, or tasks identified from the status update that are not yet formally planned:

1.  **Create a Markdown File:** In `roadmap/0_backlog/`, create a new `.md` file for each distinct idea (e.g., `roadmap/0_backlog/new_reporting_module_idea.md`).
2.  **Document the Idea:** Briefly describe:
    *   The core concept or problem to solve.
    *   The intended goal or benefit.
    *   Any initial thoughts, requirements, or context from the status update.

### Step 3: Process Items into `1_planning/`

When an item from the status update (or an existing file in `0_backlog/`) is ready for detailed planning:

1.  **Identify the Source Idea File:** Note the path to the markdown file containing the feature idea (e.g., `roadmap/0_backlog/new_reporting_module_idea.md`). You might conceptually (or physically) move this file to `roadmap/1_planning/` first, but the key is having its content ready.
2.  **Instruct AI for Planning:** Tell your AI assistant:
    ```
    Execute `roadmap/1_planning/STAGE_GATE_PROMPT_PLAN.md` for the feature described in `[path_to_idea_file.md]`. 
    Example: Execute `roadmap/1_planning/STAGE_GATE_PROMPT_PLAN.md` for the feature described in `roadmap/0_backlog/new_reporting_module_idea.md`.
    ```
3.  **AI Action:** The AI will:
    *   Read the idea file and the planning prompt.
    *   Create a new subfolder for the feature within `roadmap/1_planning/` (e.g., `roadmap/1_planning/new_reporting_module/`).
    *   Generate standard planning documents (`README.md`, `spec.md`, `design.md`) inside this new folder, populating them based on the idea file and templates.
4.  **Review & Refine:** Review the AI-generated planning documents. Add details, answer open questions, and refine the plan.

### Step 4: Process Items into `2_inprogress/`

When a feature from `1_planning/` is approved and ready for implementation, or the status update indicates active development:

1.  **Identify the Feature Folder:** Note the path to the planned feature's folder (e.g., `roadmap/1_planning/new_reporting_module/`).
2.  **Manual Action (Conceptual or Physical):** Move the entire feature folder from `roadmap/1_planning/` to `roadmap/2_inprogress/`.
    *(Example: `mv roadmap/1_planning/new_reporting_module/ roadmap/2_inprogress/`)*
3.  **Instruct AI for Implementation Kick-off:** Tell your AI assistant:
    ```
    Execute `roadmap/2_inprogress/STAGE_GATE_PROMPT_PROG.md` for the feature in folder `roadmap/2_inprogress/new_reporting_module/`.
    ```
4.  **AI Action:** The AI will:
    *   Analyze the planning documents within the feature folder.
    *   Generate a `task_list.md`.
    *   Suggest creating `implementation_notes.md` for tracking progress.
5.  **Begin Implementation:** Use the generated task list and `implementation_notes.md` to guide development.

### Step 5: Process Items into `3_completed/`

When a feature from `2_inprogress/` is fully implemented, tested, and verified (as indicated by a status update or your own assessment):

1.  **Identify the Feature Folder:** Note the path to the in-progress feature's folder (e.g., `roadmap/2_inprogress/new_reporting_module/`).
2.  **Manual Action (Conceptual or Physical):** Move the entire feature folder from `roadmap/2_inprogress/` to `roadmap/3_completed/`.
    *(Example: `mv roadmap/2_inprogress/new_reporting_module/ roadmap/3_completed/`)*
3.  **Instruct AI for Completion Summary:** Tell your AI assistant:
    ```
    Execute `roadmap/3_completed/STAGE_GATE_PROMPT_COMPL.md` for the feature in folder `roadmap/3_completed/new_reporting_module/`.
    ```
4.  **AI Action:** The AI will:
    *   Review all documents in the feature folder.
    *   Generate a `summary.md` file.
    *   Provide a log entry for `roadmap/_reference/completed_features_log.md`.
    *   Suggest sections of `roadmap/_reference/architecture_notes.md` that might need review.
5.  **Finalize:** Add the log entry to `completed_features_log.md`. Review architecture if needed.

### Step 6: Process Items into `4_archived/`

For features or ideas that become obsolete, are indefinitely deferred, or superseded:

1.  **Identify the Item:** This could be a file from `0_backlog/` or an entire feature folder from `1_planning/`, `2_inprogress/`, or `3_completed/`.
2.  **Manual Action:** Move the file or folder into `roadmap/4_archived/`.
3.  **(Optional) Add a Note:** You might add a small note inside the archived item explaining why it was archived.

## 5. Tips for Effective Use

-   **Be Explicit with AI:** When instructing your AI assistant, provide clear, full paths to the relevant prompt files and feature files/folders.
-   **Iterate and Refine:** The AI-generated content is a starting point. Review, edit, and add your expertise to all documents.
-   **Keep Status Updates Detailed:** The more detail in your `roadmap/_status_updates/` files, the easier it will be to identify and process items for the roadmap stages.
-   **Adapt the Process:** This is a template. Feel free to adapt the stage gate prompts, templates, and workflow to best suit the Biomapper project's evolving needs.
-   **Consider Updating `roadmap/README.md`:** Once this system is established, you might want to update the main `roadmap/README.md` to describe this new workflow and point to this `HOW_TO_UPDATE_ROADMAP_STAGES.md` guide.
