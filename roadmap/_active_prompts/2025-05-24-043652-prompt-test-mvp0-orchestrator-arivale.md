# Prompt: Integration Test MVP0 Pipeline Orchestrator with Arivale Data

**Date:** 2025-05-24
**Project:** Biomapper
**Task:** Perform an initial integration test of the MVP0 Pipeline Orchestrator using Arivale metabolomics data.
**Orchestrator Code:** `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/pipeline_orchestrator.py`
**Orchestrator README:** `/home/ubuntu/biomapper/biomapper/mvp0_pipeline/README.md`

## 1. Objective

Execute the `PipelineOrchestrator` on a subset of real biochemical names from the Arivale dataset to:
1.  Verify its functionality with live Qdrant, PubChem, and LLM services.
2.  Assess the quality of mappings on real-world data.
3.  Identify any runtime issues, unexpected behaviors, or performance characteristics.
4.  Collect results and basic statistics from the test run.

## 2. Background

The `PipelineOrchestrator` has been developed and unit/integration tested with mocked components. It is now ready for a test run using actual data and live external services. The orchestrator is configured via environment variables (see its README for details, especially `ANTHROPIC_API_KEY`, Qdrant URL/collection).

## 3. Test Data & Scope

*   **Data Source File:** `/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv`
*   **File Format:** TSV (Tab Separated Values).
*   **Important Note:** The file contains 10-15 commented lines at the beginning (starting with '#'). These lines must be skipped/ignored when reading the data.
*   **Target Column:** `BIOCHEMICAL_NAME`
*   **Test Subset:** Process the biochemical names from the **first 50 data rows** (after skipping the initial commented header lines). Ensure you extract unique names if there are duplicates within these first 50, to avoid redundant processing for this initial test.

## 4. Tasks to Perform

1.  **Environment Setup:**
    *   Ensure all necessary environment variables for the `PipelineOrchestrator` are correctly set in your execution environment (refer to the orchestrator's README, especially `ANTHROPIC_API_KEY`, Qdrant URL, collection name, etc.).
    *   Verify that you have network access to Qdrant, PubChem, and the Anthropic API.

2.  **Create a Test Script:**
    *   Develop a Python script (e.g., `/home/ubuntu/biomapper/scripts/testing/run_arivale_orchestrator_test.py`).
    *   This script should:
        *   Read the `/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv` file.
        *   Correctly handle and skip the initial commented lines.
        *   Extract the `BIOCHEMICAL_NAME` values from the first 50 data rows.
        *   Obtain a list of unique biochemical names from this subset.
        *   Instantiate the `PipelineOrchestrator` using `create_orchestrator()` (which loads config from env vars).
        *   Execute the `orchestrator.run_pipeline()` method with the list of unique biochemical names.
        *   Capture the `BatchMappingResult` returned by the orchestrator.

3.  **Execute the Test:**
    *   Run your test script.
    *   Monitor the execution for any errors or unexpected console output.

4.  **Collect and Format Results:**
    *   From the `BatchMappingResult`:
        *   Save all individual `PipelineMappingResult` objects to a structured file (e.g., JSON lines or CSV). Recommended path: `/home/ubuntu/biomapper/data/testing_results/arivale_mvp0_test_run_YYYYMMDD_HHMMSS_results.jsonl` (use actual timestamp).
        *   Extract and present the summary statistics provided in `BatchMappingResult` (total processed, successful, failed, total time, time per item).

5.  **Report Findings:**
    *   Provide a summary of the test run, including:
        *   The number of unique biochemical names processed.
        *   The summary statistics from `BatchMappingResult`.
        *   A few examples of successful mappings (original name, CID, rationale, confidence).
        *   A few examples of failed mappings or problematic cases (e.g., `NO_QDRANT_HITS`, `LLM_NO_MATCH`, component errors), including the original name and the reported status/error.
        *   Any errors or exceptions encountered during the script execution or orchestrator run.
        *   Observations on processing time or any other notable behaviors.
        *   Confirmation that the output results file was saved.

## 5. Deliverables

1.  The Python test script (`/home/ubuntu/biomapper/scripts/testing/run_arivale_orchestrator_test.py`).
2.  The path to the saved results file (e.g., `/home/ubuntu/biomapper/data/testing_results/arivale_mvp0_test_run_YYYYMMDD_HHMMSS_results.jsonl`).
3.  A feedback report (markdown format) containing the "Report Findings" detailed above.

## 6. Important Considerations

*   **API Keys & Costs:** Be mindful that this test will make live calls to PubChem and Anthropic APIs, which may incur costs or be rate-limited. The small subset (first 50 unique names) is intended to manage this.
*   **Error Handling in Script:** Your test script should also have basic error handling (e.g., for file reading).
*   **Existing `main()`:** The `main()` function in `pipeline_orchestrator.py` can serve as a reference for how to run the orchestrator.
*   **Qdrant Collection:** Ensure the Qdrant collection specified in your environment variables is the correct one populated with PubChem embeddings.

Please proceed with these tasks and provide the deliverables upon completion.
