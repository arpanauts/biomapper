# Task: Implement Strategy Execution Endpoint

**Source Prompt Reference:** Orchestrator-generated task to build the primary API endpoint.

## 1. Task Objective

To provide a primary API endpoint for executing mapping strategies by name. This involves creating a new API route, new data models, and updating the dependency injection mechanism to use the singleton `MapperService`.

## 2. Service Architecture Context

- **Primary Service:** `biomapper-api`
- **Files to Create:**
    - `/home/ubuntu/biomapper/biomapper-api/app/api/routes/strategies.py`
    - `/home/ubuntu/biomapper/biomapper-api/app/models/strategy.py`
- **Files to Modify:**
    - `/home/ubuntu/biomapper/biomapper-api/app/main.py` (to include the new router)
    - `/home/ubuntu/biomapper/biomapper-api/app/api/deps.py` (to refactor dependency injection)

## 3. Task Decomposition

1.  **Create Pydantic Models:**
    *   In the new `strategy.py` file, create two Pydantic models:
    *   `StrategyExecutionRequest`: Should contain a single field, `context`, which is a `dict`.
    *   `StrategyExecutionResponse`: Should contain a single field, `results`, which is a `dict`.
2.  **Refactor Dependency Injection:**
    *   In `deps.py`, modify `get_mapper_service`.
    *   It should no longer be a generator that creates a new service. Instead, it should take a `Request` object as an argument and return the singleton instance: `return request.app.state.mapper_service`.
3.  **Create New API Route:**
    *   In the new `strategies.py` file, create a new `APIRouter`.
    *   Define a new endpoint: `POST /api/strategies/{strategy_name}/execute`.
    *   This endpoint should take `strategy_name` from the path and the request body should be a `StrategyExecutionRequest` model.
    *   It should depend on the `get_mapper_service`.
    *   The endpoint will call `mapper_service.execute_strategy()` with the strategy name and the context from the request body.
    *   It should return a `StrategyExecutionResponse` containing the results.
4.  **Register Router:**
    *   In `main.py`, import and include the new router from `app.api.routes.strategies`.

## 4. Implementation Requirements

- The new endpoint must have a comprehensive docstring explaining its function, arguments, and what it returns.
- Use the `async/await` pattern correctly for the endpoint and service call.
- Ensure the Pydantic models are well-defined and imported correctly.

## 5. Success Criteria and Validation

- The four specified files are created/modified correctly.
- The API starts without errors.
- The new endpoint `POST /api/strategies/{strategy_name}/execute` appears correctly in the OpenAPI documentation at `/api/docs`.
- The endpoint correctly depends on the singleton `MapperService` instance.

## 6. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-02-implement-strategy-endpoint.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** Links to the four files that were created or modified.
-   **Summary of Changes:** A description of the new endpoint and how the dependency injection was updated.
