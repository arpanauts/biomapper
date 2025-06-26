# Task: UI Rebuild - Implement State Management

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Implement a global state management solution using Zustand to manage the application's shared state. This will provide a single source of truth for the UI and simplify state sharing between components.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:** None.
- **Service Dependencies:** None.

## 3. Prerequisites
- [ ] `zustand` is added as a dependency in the project.

## 4. Task Decomposition
1.  **Create Store File:** Create a new file at `src/store/appStore.ts`.
2.  **Define State Interface:** Define a TypeScript interface for the store's state.
3.  **Create Store:** Use Zustand's `create` function to build the store.
4.  **Implement Actions:** Define actions (functions) to modify the state.

## 5. Implementation Requirements
- **File:** `src/store/appStore.ts`
- **State to manage:**
    - `activeStep: 'upload' | 'columns' | 'mapping' | 'results'`
    - `sessionId: string | null`
    - `filename: string | null`
    - `jobId: string | null`
    - `isLoading: boolean`
    - `error: string | null`
- **Actions to implement:**
    - `setSession(sessionId: string, filename: string)`
    - `setJobId(jobId: string)`
    - `setActiveStep(step: ...)`
    - `reset()`: to clear the state for a new workflow.
    - `setLoading(isLoading: boolean)`
    - `setError(error: string | null)`

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `src/store/appStore.ts` file is created.
- [ ] The Zustand store is implemented with the specified state and actions.
- [ ] The store is exported as a hook that can be used in React components.
- [ ] Unit tests are created to verify the initial state and the behavior of each action.
