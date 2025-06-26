# Task: Investigate and Plan biomapper-ui Modernization

**Source Prompt Reference:** This task is defined by the prompt: /home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-24-183900-investigate-biomapper-ui-status.md

## 1. Task Objective

The primary objective is to assess the current state of the `biomapper-ui` and determine the most effective path forward for integrating it with the new `biomapper-api` service. The final deliverable should be a markdown document containing a detailed analysis and a clear recommendation on whether to refactor the existing UI or to rebuild it from scratch.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** The UI will need to interact with most of the `biomapper-api` endpoints, including:
    - `POST /api/strategies/execute`
    - `GET /api/mappings/{mapping_id}`
    - `GET /api/strategies/{strategy_name}`
    - `GET /api/endpoints`
    - `GET /api/health`
- **Service Dependencies:** The `biomapper-ui` is entirely dependent on the `biomapper-api` for all data and functionality.
- **Configuration Files:** None directly, but the UI will need to be configured with the base URL of the `biomapper-api`.

## 3. Prerequisites
- [ ] The `biomapper-api` service is running and accessible. Verification can be done by hitting the `GET /api/health` endpoint.

## 4. Task Decomposition
Break this investigation into the following subtasks:

1.  **Codebase Review:** Analyze the existing codebase of the `biomapper-ui` located at `/home/ubuntu/biomapper/biomapper-ui`.
    - Identify the framework/libraries used (e.g., React, Vue, Angular, etc.).
    - Understand the current data fetching and state management mechanisms.
    - Assess the overall code quality, structure, and documentation.
2.  **API Integration Analysis:** Map out the necessary changes to replace any direct data access or mock data with calls to the `biomapper-api`.
    - Detail the required modifications for executing strategies and polling for results.
    - Plan how to display mapping results and provenance information fetched from the API.
3.  **Effort Estimation:** Estimate the development effort (e.g., in person-days or story points) for both refactoring the existing UI and rebuilding it from scratch with a modern framework.
4.  **Recommendation:** Based on the analysis, provide a clear recommendation with justifications. The recommendation should consider factors like time-to-delivery, long-term maintainability, and performance.

## 5. Implementation Requirements
- The investigation should result in a detailed markdown report.
- The report should include code snippets or diagrams where necessary to illustrate the proposed changes.

## 6. Error Recovery Instructions
- **SERVICE_UNAVAILABLE:** If the `biomapper-api` is not running, start it before proceeding with the investigation.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] A markdown report is delivered containing the full analysis and recommendation.
- [ ] The report clearly outlines the pros and cons of refactoring versus rebuilding.
- [ ] The recommendation is well-supported by the findings in the report.

## 8. Deployment Considerations
- The report should briefly touch upon potential deployment strategies for the modernized UI (e.g., serving it from the API, using a separate web server, etc.).

## 9. Feedback Requirements
Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-investigate-biomapper-ui-status.md`

The feedback should summarize the findings and the final recommendation.
