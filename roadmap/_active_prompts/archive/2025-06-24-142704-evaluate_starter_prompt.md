# Task: Evaluate and Adapt Starter Prompt for Service-Oriented Architecture

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-24-142704-evaluate_starter_prompt.md`

## 1. Task Objective

The primary objective is to analyze the existing meta-prompt at `/home/ubuntu/biomapper/roadmap/_active_prompts/_starter_prompt.md` and create a new, updated version that aligns with the project's new service-oriented architecture (SOA). The new prompt will guide development efforts towards building and consuming mapping services rather than monolithic scripts. A secondary objective is to outline a plan for converting the existing Jupyter notebook PoC (`/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb`) into a workflow that uses this new SOA.

## 2. Prerequisites

- [X] Required files exist:
    - `/home/ubuntu/biomapper/roadmap/_active_prompts/_starter_prompt.md`
    - `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb`
- [X] Project structure has been explored and the following key directories are confirmed: `biomapper/`, `biomapper-api/`, `biomapper-ui/`.

## 3. Context from Previous Attempts (if applicable)

N/A. This is the initial attempt to formally adapt the project's guiding principles to the new architecture.

## 4. Task Decomposition

1.  **Analyze `_starter_prompt.md`:** Read the existing prompt and identify all sections that are now outdated or incomplete due to the shift to a service-oriented architecture. Pay close attention to instructions regarding code creation, execution, and the `StrategyAction` developer guide.
2.  **Draft New `_soa_starter_prompt.md`:** Create a new markdown file named `_soa_starter_prompt.md` in the same directory. This new file will be a revised version of the original. The new prompt must:
    *   Introduce the `biomapper-api` as the primary entry point for executing mapping logic.
    *   Reframe the `StrategyAction` guide to emphasize that these actions are components within a larger mapping service, executed via API calls.
    *   Add a new section detailing how to interact with the API (e.g., endpoints for starting a mapping, checking status, retrieving results).
    *   Mention the `biomapper-ui` as the tool for visualizing results from the mapping services.
    *   Update the `Enhanced Interaction Flow with USER` and `Claude Code Instance Prompt Generation` sections to reflect a workflow where the agent might define a strategy in YAML, deploy it to the API, and then trigger it.
3.  **Plan Notebook-to-Service Conversion:** Create a separate markdown document named `notebook_to_service_plan.md` in `/home/ubuntu/biomapper/roadmap/`. This document will outline the steps to convert the logic from `ukbb_to_hpa_protein.ipynb` into a service-based workflow. The plan should include:
    *   Identifying the discrete steps in the notebook (data loading, ID resolution, overlap analysis).
    *   Mapping each step to a potential `StrategyAction`.
    *   Defining the YAML configuration for a new `ukbb_to_hpa_protein` mapping strategy.
    *   Specifying the API calls needed to execute this strategy and retrieve the results.

## 5. Implementation Requirements

- **Input files/data:**
    - `/home/ubuntu/biomapper/roadmap/_active_prompts/_starter_prompt.md`
    - `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb`
- **Expected outputs:**
    1.  `/home/ubuntu/biomapper/roadmap/_active_prompts/_soa_starter_prompt.md`: The new, comprehensive meta-prompt for the service-oriented architecture.
    2.  `/home/ubuntu/biomapper/roadmap/notebook_to_service_plan.md`: A detailed plan for converting the example notebook into a service.

## 6. Error Recovery Instructions

- If any of the source files are not found, report the missing file and stop.
- If the project structure appears different than described, report the discrepancies and ask for clarification before proceeding.

## 7. Success Criteria and Validation

Task is complete when:
- [ ] The `_soa_starter_prompt.md` file is created and contains clear, actionable guidance for developing within the new service-oriented architecture.
- [ ] The new prompt correctly references the `biomapper-api` and `biomapper-ui` components.
- [ ] The `notebook_to_service_plan.md` file is created and provides a logical, step-by-step plan for the notebook-to-service conversion.

## 8. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-evaluate_starter_prompt.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Issues Encountered:** [detailed error descriptions with context]
- **Next Action Recommendation:** [specific follow-up needed]
- **Links to Artifacts:** Provide direct links to the two created markdown files.
