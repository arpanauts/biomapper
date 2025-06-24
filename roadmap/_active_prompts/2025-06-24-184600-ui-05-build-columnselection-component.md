# Task: UI Rebuild - Build ColumnSelection Component

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Create a component that fetches and displays the columns from the uploaded file and allows the user to select the relevant columns for mapping.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** `GET /api/sessions/{sessionId}/columns` (via `apiService`).
- **Service Dependencies:** `apiService` and `appStore`.

## 3. Prerequisites
- [ ] The `apiService` module (Prompt 02) and `appStore` (Prompt 03) are available (or can be mocked).

## 4. Task Decomposition
1.  **Create Component File:** `src/components/ColumnSelection/ColumnSelection.tsx`.
2.  **Fetch Columns:** Use the `sessionId` from the `appStore` to call `apiService.getColumns` when the component mounts.
3.  **Display Columns:** Render the fetched column names using Mantine's `Checkbox` or `MultiSelect` components.
4.  **Handle Selection:** Store the user's selection in local state.
5.  **Handle Submission:** On submission, update the global state (if necessary) and call `appStore.setActiveStep('mapping')` to proceed to the next step.

## 5. Implementation Requirements
- **File:** `src/components/ColumnSelection/ColumnSelection.tsx`.
- **Props:** None required.
- **UI:** Should show a loading state while fetching columns and an error state if the fetch fails. A "Next" button should be disabled until the user has made a valid selection.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `ColumnSelection` component is created.
- [ ] The component fetches and displays column data from the API.
- [ ] The user can select columns.
- [ ] The component navigates to the next step on submission.
- [ ] The component is tested in isolation.
