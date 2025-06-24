# Task: UI Rebuild - Build Results Component

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Create a component to display the results of a mapping job. This component will poll the API for the job status and display the results once they are ready.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** `GET /api/mappings/{jobId}` (via `apiService`).
- **Service Dependencies:** `apiService` and `appStore`.

## 3. Prerequisites
- [ ] The `apiService` module (Prompt 02) and `appStore` (Prompt 03) are available (or can be mocked).

## 4. Task Decomposition
1.  **Create Component File:** `src/components/Results/Results.tsx`.
2.  **Implement Polling:** Use the `jobId` from the `appStore`. Implement a polling mechanism (e.g., using `setInterval` inside a `useEffect` hook) to call `apiService.getMappingStatus` periodically.
3.  **Display Status:** While polling, display the current job status (e.g., "Running", "In Progress").
4.  **Display Results:** Once the status is "completed", display the results in a Mantine `Table`.
5.  **Handle Errors:** If the status is "failed", display the error message.
6.  **Reset Workflow:** Include a "Start New Mapping" button that calls `appStore.reset()`.

## 5. Implementation Requirements
- **File:** `src/components/Results/Results.tsx`.
- **Props:** None required.
- **UI:** Should clearly show the job's progress. The final results should be presented in a clear, readable table. The reset button should be prominent.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `Results` component is created.
- [ ] The component correctly polls for status updates.
- [ ] The component displays the final results or an error message.
- [ ] The reset button correctly resets the application state.
- [ ] The component is tested in isolation.
