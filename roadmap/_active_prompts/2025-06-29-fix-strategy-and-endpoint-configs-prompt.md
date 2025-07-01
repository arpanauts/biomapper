# Prompt: Fix Strategy and Endpoint Configurations

**Objective:**

Your task is to resolve two critical configuration issues that are preventing the biomapper pipelines from running. This involves ensuring the database is correctly populated with required endpoints and fixing validation errors in a secondary strategy file.

**Context:**

The `biomapper-api` server is now stable and running. However, application-level configuration errors are blocking pipeline execution. You must fix these to achieve a fully working end-to-end mapping process.

--- 

### **Part 1: Fix Critical Endpoint Configuration Error**

**Problem:**

The primary mapping pipeline (`UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS`) is failing during execution because the `HPA_PROTEIN_DATA` endpoint is not found in the database. The script to create this endpoint exists but was not successfully run in the previous steps.

**Implementation Steps:**

1.  **Run the Endpoint Population Script:** The script at `/home/ubuntu/biomapper/scripts/populate_endpoints.py` is responsible for creating all necessary endpoints. Execute it using `poetry` to ensure the database is correctly populated.

    ```bash
    # From the /home/ubuntu/biomapper/ directory
    poetry run python3 scripts/populate_endpoints.py
    ```

2.  **Run the Strategy Population Script:** For good measure, also run the script to populate the YAML strategy into the database.

    ```bash
    # From the /home/ubuntu/biomapper/ directory
    poetry run python3 scripts/populate_yaml_strategy.py
    ```

**Verification for Part 1:**

After running the scripts, you must verify that the endpoint was created. Restart the API server and use `curl` to query the `/api/endpoints` endpoint. 

```bash
# Restart the server in the background from the biomapper-api directory
# (You may need to stop the existing one first: pkill uvicorn)
cd /home/ubuntu/biomapper/biomapper-api/
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Wait for it to start
sleep 5

# Query the endpoints
curl http://localhost:8000/api/endpoints
```

The JSON output from `curl` **must** contain an entry for `HPA_PROTEIN_DATA`.

--- 

### **Part 2: Fix Strategy Validation Errors**

**Problem:**

The `full_featured_ukbb_hpa_strategy.yaml` strategy file is failing validation and is not being loaded by the server. The server logs indicate that some steps are using an invalid `action_class_path` field instead of the required `type` field to define the action.

**File to Modify:**

*   `/home/ubuntu/biomapper/configs/full_featured_ukbb_hpa_strategy.yaml`

**Implementation Steps:**

1.  **Identify and Replace Invalid Fields:** Search through the strategy file for any step definitions that use `action_class_path`. 
2.  **Replace `action_class_path` with `type`:** For each occurrence, replace the `action_class_path` key with `type`. The value (the action name) should remain the same.

    **Example of what to fix:**
    ```yaml
    # Hypothetical incorrect step
    - name: "SOME_ACTION_STEP"
      action:
        action_class_path: "SOME_ACTION_NAME" # <<< THIS IS WRONG
        params: { ... }
    ```

    **Corrected version:**
    ```yaml
    - name: "SOME_ACTION_STEP"
      action:
        type: "SOME_ACTION_NAME" # <<< THIS IS CORRECT
        params: { ... }
    ```

**Verification for Part 2:**

After modifying the YAML file, restart the `biomapper-api` server. Carefully inspect the server's startup logs. The logs should now show that the `UKBB_HPA_FULL_PIPELINE` strategy is loaded successfully, and there should be no validation errors related to it.

--- 

### **Final End-to-End Verification**

Once both parts are complete and verified, perform a final end-to-end test to confirm the entire system is working.

1.  Ensure the `biomapper-api` server is running.
2.  Execute the main client script from the project root (`/home/ubuntu/biomapper/`):

    ```bash
    poetry run python3 scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
    ```

**Expected Outcome:**

The script should now execute without errors and print a JSON dictionary to the console containing the final mapping results. This will confirm that the endpoints are configured, the strategies are valid, and the full pipeline is operational.
