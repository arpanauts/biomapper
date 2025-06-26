# Task: UI Rebuild - Build MappingConfig Component

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Create a component that allows the user to configure the mapping strategy and initiate the mapping process.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** `POST /api/strategies/execute` (via `apiService`).
- **Service Dependencies:** `apiService` and `appStore`.

## 3. Prerequisites
- [ ] The `apiService` module (Prompt 02) and `appStore` (Prompt 03) are available (or can be mocked).

## 4. Task Decomposition
1.  **Create Component File:** `src/components/MappingConfig/MappingConfig.tsx`.
2.  **Build UI:** Create a form using Mantine components (`Select`, `TextInput`, etc.) to collect mapping parameters (e.g., target data source, mapping strategy name).
3.  **Handle Submission:** On form submission, construct the configuration object and call `apiService.startMapping`.
4.  **Update State:** On success, update the global state with the returned `jobId` by calling `appStore.setJobId` and navigate to the results step.

## 5. Implementation Requirements
- **File:** `src/components/MappingConfig/MappingConfig.tsx`.
- **Props:** None required.
- **UI:** A form with fields for all necessary mapping configuration options. A "Start Mapping" button should trigger the process.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `MappingConfig` component is created.
- [ ] The component's form can be filled out by the user.
- [ ] On submission, the component calls the `apiService.startMapping` function with the correct parameters.
- [ ] The global state is updated correctly on success.
- [ ] The component is tested in isolation.
