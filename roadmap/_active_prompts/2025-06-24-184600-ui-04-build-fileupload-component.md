# Task: UI Rebuild - Build FileUpload Component

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Create a reusable React component for uploading a file. This component will handle the UI for file selection and will use the API service to upload the file to the backend.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** `POST /api/sessions/upload` (via `apiService`).
- **Service Dependencies:** This component will depend on `apiService` and the `appStore`.

## 3. Prerequisites
- [ ] The `apiService` module (Prompt 02) and `appStore` (Prompt 03) are available (or can be mocked).

## 4. Task Decomposition
1.  **Create Component File:** Create `src/components/FileUpload/FileUpload.tsx`.
2.  **Build UI:** Use Mantine's `FileButton` or a custom dropzone to create the file selection UI.
3.  **Handle Upload:** On file selection, call the `apiService.uploadFile` function.
4.  **Update State:** On successful upload, use the `appStore` hook to call the `setSession` action with the new session ID and filename, and then advance the `activeStep`.
5.  **Handle Errors:** Display an error message if the upload fails.

## 5. Implementation Requirements
- **File:** `src/components/FileUpload/FileUpload.tsx`
- **Props:** The component should not require any props, as it will get its functionality from the global store and API service.
- **UI:** Should clearly indicate the state (waiting for file, uploading, success, error).

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `FileUpload` component is created.
- [ ] The component allows a user to select a file.
- [ ] The component successfully calls the (mocked or real) `apiService.uploadFile` function.
- [ ] The component correctly updates the global state via the `appStore` on success or failure.
- [ ] The component can be rendered in isolation and tested using Storybook or a similar tool.
