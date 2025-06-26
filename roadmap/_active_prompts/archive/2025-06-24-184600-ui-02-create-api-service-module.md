# Task: UI Rebuild - Create API Service Module

**Source Prompt Reference:** This task is part of the UI rebuild effort defined in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-06-24-184500-ui-investigation-report.md`.

## 1. Task Objective
Create a dedicated TypeScript module to handle all HTTP requests to the `biomapper-api`. This service will centralize API logic, making components cleaner and API calls easier to manage and mock for testing.

## 2. Service Architecture Context
- **Primary Service:** `biomapper-ui`
- **API Endpoints Required:**
    - `GET /api/health`
    - `POST /api/sessions/upload` (or similar endpoint for file upload)
    - `GET /api/sessions/{sessionId}/columns`
    - `POST /api/strategies/execute`
    - `GET /api/mappings/{jobId}`
- **Service Dependencies:** `biomapper-api` must be running for integration testing.

## 3. Prerequisites
- [ ] `axios` is added as a dependency in the project.

## 4. Task Decomposition
1.  **Create File:** Create a new file at `src/services/apiService.ts`.
2.  **Setup Axios:** Create an `axios` instance with a base URL pointing to the API (e.g., `http://localhost:8000`).
3.  **Implement API Functions:** Create and export async functions for each required API interaction. Each function should handle the request and return the data from the response. Implement robust error handling.

## 5. Implementation Requirements
- **File:** `src/services/apiService.ts`
- **Functions to implement:**
    - `healthCheck(): Promise<any>`
    - `uploadFile(file: File): Promise<{ session_id: string, filename: string }>`
    - `getColumns(sessionId: string): Promise<string[]>`
    - `startMapping(sessionId: string, config: any): Promise<{ job_id: string }>`
    - `getMappingStatus(jobId: string): Promise<{ status: string, results?: any, error?: string }>`
- **Error Handling:** Functions should throw or handle errors from the API gracefully.

## 6. Success Criteria and Validation
Task is complete when:
- [ ] The `src/services/apiService.ts` file is created.
- [ ] The file exports all the specified functions with correct signatures.
- [ ] The functions correctly use `axios` to make API calls.
- [ ] Unit tests are created to mock `axios` and verify the behavior of each service function.
