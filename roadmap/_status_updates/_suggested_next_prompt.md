# Suggested Next Prompt for Biomapper Development

## Context Brief
The `PubChemRAGMappingClient` feature is now complete, providing semantic search capabilities for metabolite mapping. The project workflow, including prompt generation and file naming, has also been refined. The immediate next step is to decide on reviewing suggested architecture documents or selecting a new feature for development.

## Initial Steps
1.  Review `/home/ubuntu/biomapper/CLAUDE.md` for overall project context and development approach.
2.  Review the latest status update which summarizes our recent session: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-23-210820-session-summary.md`.
3.  Review the completion feedback for `PubChemRAGMappingClient`, particularly the "Architecture Review Suggestions" and "Future Considerations" sections: `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-23-feedback-complete-pubchem-rag-client.md`.

## Work Priorities

1.  **Decision Point: Next Focus Area**
    *   **Option A: Architecture Document Review:**
        *   Decide whether to review and potentially update the architecture documents suggested after the `PubChemRAGMappingClient` completion:
            *   `rag_performance_evaluation_plan.md` (Path likely under `/home/ubuntu/biomapper/docs/architecture/` - to be confirmed or created).
            *   `resource_metadata_system.md` (Path likely under `/home/ubuntu/biomapper/docs/architecture/` - to be confirmed or created).
        *   If proceeding, locate/create these documents, assess necessary updates based on the RAG client, and plan/execute changes.
    *   **Option B: New Feature Development:**
        *   Identify the next high-priority feature or task from the project backlog or roadmap.
        *   Initiate the planning stage for this new feature (e.g., creating `README.md`, `spec.md`, `design.md` in a new folder under `/home/ubuntu/biomapper/roadmap/1_planning/`).

2.  **Action Based on Decision:**
    *   If Option A, begin the document review and update process.
    *   If Option B, begin the planning process for the new feature.

## Key Files and References

*   **Latest Status Update:** `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-23-210820-session-summary.md`
*   **`PubChemRAGMappingClient` Completion Feedback:** `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-05-23-feedback-complete-pubchem-rag-client.md`
*   **`PubChemRAGMappingClient` Summary:** `/home/ubuntu/biomapper/roadmap/3_completed/pubchem_rag_mapping_client/summary.md`
*   **Starter Prompt (Process Guide):** `/home/ubuntu/biomapper/roadmap/_active_prompts/_starter_prompt.md`
*   **Completed Features Log:** `/home/ubuntu/biomapper/roadmap/_reference/completed_features_log.md`

## Workflow Integration (General for Next Task)

*   Continue to leverage Cascade (as Project Manager) to define tasks and generate detailed prompts for Claude code instances, following the established stage-gate process (Planning -> In Progress -> Completed).
*   Ensure any new prompts created adhere to the updated naming convention (`YYYY-MM-DD-HHMMSS-[description].md`) and include the source prompt reference as outlined in `_starter_prompt.md`.
*   If a new feature is started, Cascade will create the initial planning documents and the first handoff prompt for the Claude instance.

This prompt aims to guide the USER in deciding the next steps and initiating the relevant workflow.