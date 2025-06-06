# Task: Debug UniProtHistoricalResolverClient API Interaction and Resolution Logic

## 1. Task Objective

To diagnose and fix the `UniProtHistoricalResolverClient` in `/home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py` such that it correctly resolves primary UniProt accession numbers by:
1.  Successfully querying the UniProt REST API.
2.  Accurately interpreting the API's responses.
3.  Returning the correct primary ID and "primary" metadata for known primary accessions.

## 2. Background & Current Hypothesis

The `UniProtHistoricalResolverClient.map_identifiers` method is currently returning `(None, "obsolete")` for known valid primary UniProt IDs (e.g., 'P69905', 'P02768'). This occurs even when the cache is bypassed (`BYPASS_UNIPROT_CACHE=true`).

The debug logs from `MappingExecutor` show that `_execute_mapping_step` receives `(None, None)` as the result from `client_instance.map_identifiers(...)` for these primary IDs.

**Current Hypothesis:** The issue lies within `UniProtHistoricalResolverClient._resolve_batch` or the methods it calls, specifically `_check_as_primary_accessions`, `_check_as_secondary_accessions`, and the underlying `_fetch_uniprot_search_results`. It's suspected that:
    a.  The API queries constructed are incorrect.
    b.  The UniProt API is not returning the expected data for these valid IDs.
    c.  The client is misinterpreting the API's JSON response.
    d.  An error during the API call is causing `resolution_info["found"]` to remain `False`.

An attempt was made to add logging to `_fetch_uniprot_search_results` to inspect the API queries and response counts, but the edits were not applied cleanly. This logging is crucial.

## 3. Prerequisites

*   Access to the codebase at `/home/ubuntu/biomapper/`.
*   Ability to run Python scripts and set environment variables.
*   Understanding of async Python and `aiohttp`.

## 4. Input Context

*   **Primary Code File for Debugging:** `/home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py`
*   **Key Methods to Inspect/Modify:**
    *   `UniProtHistoricalResolverClient._fetch_uniprot_search_results` (target for initial logging)
    *   `UniProtHistoricalResolverClient._check_as_primary_accessions`
    *   `UniProtHistoricalResolverClient._check_as_secondary_accessions`
    *   `UniProtHistoricalResolverClient._resolve_batch`
    *   `UniProtHistoricalResolverClient.map_identifiers`
*   **Test Script:** `/home/ubuntu/biomapper/scripts/test_ukbb_hpa_pipeline.py`
*   **Relevant Input IDs (from test script):** 'P69905', 'P02768', 'Q15823', 'O00159' (all are valid primary UniProt IDs). 'P12345_UNKNOWN' is expected to fail.
*   **Previous Checkpoint Summary (for broader context if needed):** Provided by Cascade (contains details of earlier debugging steps).

## 5. Expected Outputs

*   Modified `uniprot_historical_resolver_client.py` with effective diagnostic logging and fixes.
*   Successful execution of `test_ukbb_hpa_pipeline.py` where step `S2_RESOLVE_UNIPROT_HISTORY` correctly maps the known primary UniProt IDs.
*   Log output clearly showing the UniProt API queries for the test IDs and the number of results returned by the API.

## 6. Success Criteria

1.  When `test_ukbb_hpa_pipeline.py` is run with `BYPASS_UNIPROT_CACHE=true`, the `S2_RESOLVE_UNIPROT_HISTORY` step reports at least 4 out of 5 identifiers mapped (the 4 known primary IDs).
2.  The `EXEC_PATH_DEBUG` logs for `RESOLVE_UNIPROT_HISTORY_VIA_API` show `step_results` like `{'P69905': (['P69905'], 'primary'), ...}` for the valid primary IDs.
3.  New debug logs within `UniProtHistoricalResolverClient` (specifically from `_fetch_uniprot_search_results`) confirm:
    *   The correct query strings are being sent to the UniProt API for IDs like 'P69905'.
    *   The API is returning at least one result for these queries.

## 7. Detailed Troubleshooting Steps for Claude Code

1.  **Add/Verify Logging in `_fetch_uniprot_search_results`:**
    *   Carefully review `/home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py`.
    *   Ensure that inside `_fetch_uniprot_search_results`, **before** the `session.get` call, the exact `query` string being sent to UniProt is logged (e.g., `logger.info(f"UniProtClient DEBUG: Querying UniProt with: {query}")`).
    *   Ensure that **after** receiving the response and parsing JSON (if successful), the number of results found is logged (e.g., `logger.info(f"UniProtClient DEBUG: Response for query [{query}]: {len(data.get('results', []))} results")`).
    *   *Self-correction note:* The previous attempt to add this logging was not perfect. Please ensure the new logging is correctly placed and uses accurate variable names from the method's scope.

2.  **Run the Test Pipeline:**
    *   Execute the test script with cache bypass enabled:
      ```bash
      export DATA_DIR=/home/ubuntu/biomapper/data && export BYPASS_UNIPROT_CACHE=true && python /home/ubuntu/biomapper/scripts/test_ukbb_hpa_pipeline.py
      ```

3.  **Analyze Log Output:**
    *   Examine the console output for the new `UniProtClient DEBUG` log lines.
    *   For an ID like 'P69905', verify:
        *   What was the exact query string logged (e.g., `(accession:P69905)`)?
        *   How many results did the API return for that query?
    *   Also, check the `EXEC_PATH_DEBUG` logs from `MappingExecutor` to see the `step_results` for the `UNIPROT_HISTORICAL_RESOLVER_SINGLE_STEP`.

4.  **Diagnose Based on Logs:**
    *   **If API queries are malformed:** Correct the query construction logic in `_check_as_primary_accessions` or `_check_as_secondary_accessions`.
    *   **If API returns 0 results for valid primary IDs:**
        *   Double-check the query logic. The current logic in `_check_as_primary_accessions` is to search for `accession:ID`. This should work.
        *   Consider if there's an issue with the `self.base_url` or other fixed parameters.
        *   Manually test the logged query directly against the UniProt website's search to see if it yields results.
    *   **If API returns results, but client still fails:** Investigate the JSON parsing and logic within `_check_as_primary_accessions` (e.g., how `entry.get("primaryAccession")` is used) and how `_resolve_batch` processes the `primary_map`.
    *   **If `_fetch_uniprot_search_results` itself logs errors (HTTP errors, timeouts):** Address these network-level issues. The default timeout is 30s.

5.  **Implement Fixes:**
    *   Modify the Python code in `/home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py` based on your diagnosis.
    *   Focus on ensuring that for a primary ID like 'P69905', `_resolve_batch` ultimately sets `results['P69905']` to something like `{"found": True, "is_primary": True, "primary_ids": ["P69905"], ...}`.

6.  **Iterate and Test:**
    *   After each modification, re-run the test script (Step 2).
    *   Re-analyze logs (Step 3) until the Success Criteria (Section 6) are met.

## 8. Validation Requirements

*   The primary validation is running the `test_ukbb_hpa_pipeline.py` script and observing its summary output for the `S2_RESOLVE_UNIPROT_HISTORY` step.
*   Cross-reference with the detailed `UniProtClient DEBUG` and `EXEC_PATH_DEBUG` logs.

## 9. Error Handling / Debugging Guidance

*   If the UniProt API seems to be the culprit (e.g., consistently returning no data for valid queries), consider if there's a broader network issue or if the API endpoint/behavior has changed.
*   Pay close attention to how `_resolve_batch` initializes `results[acc_id]` (with `found: False`, `is_obsolete: True`) and ensure that the logic correctly updates these fields when an ID is successfully identified as primary.
*   The client uses `aiohttp.ClientSession`. Ensure any changes are compatible with async operations.

## 10. References & Contextual Files

*   Main client file: `/home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py`
*   Test script: `/home/ubuntu/biomapper/scripts/test_ukbb_hpa_pipeline.py`
*   Downstream executor: `/home/ubuntu/biomapper/biomapper/core/mapping_executor.py`
*   UniProt REST API documentation (external reference if needed for query syntax).

Good luck!
