# Task: UI Rebuild - Integrate All Components

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Integrate all the newly created UI components (`FileUpload`, `ColumnSelection`, `MappingConfig`, `Results`) into the main `App.tsx` layout. The application should now function as a cohesive, multi-step workflow.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** All endpoints used by the child components.
- **Service Dependencies:** This task depends on the completion of all other component and service prompts (01-07).

## 3. Prerequisites
- [ ] All other UI rebuild prompts have been completed.
- [ ] The `biomapper-api` service is running.

## 4. Task Decomposition
1.  **Import Components:** Import all the created components into `src/App.tsx`.
2.  **Import Store:** Import the `useAppStore` hook.
3.  **Conditional Rendering:** Use the `activeStep` from the `appStore` to conditionally render the correct component in the main content area of the `AppShell`.
4.  **Update Navigation:** Wire up the `NavLink` components in the sidebar to use the `appStore.setActiveStep` action, ensuring users can only navigate to valid steps.
5.  **End-to-End Testing:** Manually test the entire workflow from file upload to viewing results.

## 5. Implementation Requirements
- **File to modify:** `src/App.tsx`.
- **Logic:** Use a `switch` statement or similar conditional logic based on `activeStep` to render the active component.
- **Navbar Logic:** The `disabled` state of the `NavLink`s should be driven by the global state (e.g., `sessionId` and `jobId`).

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `App.tsx` file correctly renders the appropriate component for each step of the workflow.
- [ ] The application state is correctly managed throughout the entire user journey.
- [ ] A user can successfully upload a file, configure a mapping, and view the results in a single, seamless session.
- [ ] The application handles errors gracefully at each step.
