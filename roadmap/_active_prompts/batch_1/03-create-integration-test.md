# Task: Create Integration Test for UKBB-HPA Strategy

**Source Prompt Reference:** Orchestrator-generated task to validate the end-to-end mapping workflow.

## 1. Task Objective

To create a new integration test that validates the entire mapping pipeline for the `UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS` strategy. This test will call the live API endpoint, execute the strategy with sample data, and verify the correctness of the results.

## 2. Service Architecture Context

- **Primary Service:** `biomapper-api`
- **Files to Create:** `/home/ubuntu/biomapper/tests/integration/test_strategy_execution.py`
- **Dependencies:** `pytest`, `httpx` (for making async requests to the API).

## 3. Task Decomposition

1.  **Create Test File:** Create the new test file in the `tests/integration/` directory.
2.  **Define Sample Data:**
    *   Inside the test file, create sample input data that mimics the expected context for the `UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS` strategy.
    *   This should be a Python dictionary with two keys: `ukbb_protein_ids` and `hpa_protein_ids`. The lists should contain some overlapping and some unique protein identifiers.
3.  **Write Test Case:**
    *   Create a `pytest` test function (e.g., `test_ukbb_hpa_overlap_strategy`).
    *   Use an `httpx.AsyncClient` to make a `POST` request to the `http://localhost:8000/api/strategies/UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS/execute` endpoint.
    *   The body of the request should be the JSON representation of a `StrategyExecutionRequest` containing your sample data in the `context` field.
4.  **Assert Results:**
    *   Check that the API returns a `200 OK` status code.
    *   Parse the JSON response.
    *   Assert that the `results` dictionary contains the `overlap_results` key.
    *   Assert that the overlap statistics (e.g., counts of overlapping IDs) are correct based on your sample data.

## 4. Implementation Requirements

- The test must be completely self-contained.
- The test should target a running instance of the `biomapper-api` service.
- Use `pytest.mark.asyncio` to mark the test as asynchronous.
- Do not hardcode the base URL; use a constant or fixture if possible.

## 5. Success Criteria and Validation

- The new test file is created.
- Running `pytest tests/integration/test_strategy_execution.py` passes successfully *when the API service is running and the work from prompts 01 and 02 is complete*.

## 6. Feedback Requirements

Create a detailed Markdown feedback file at:
`[PROJECT_ROOT]/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-03-create-integration-test.md`

Include:
-   **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED]
-   **Links to Artifacts:** A link to the new test file.
-   **Test Output:** A copy of the `pytest` output showing the new test passing.
