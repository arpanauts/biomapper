# Prompt: Fix Strategy Context Initialization to Resolve "empty_input" Error

**Objective:**

Your task is to fix a critical bug in the `StrategyOrchestrator` that prevents the mapping pipeline from executing. The `LOCAL_ID_CONVERTER` action is currently failing with an "empty_input" error because the initial execution context is missing a required key.

**Root Cause:**

The first step of the `UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS` strategy is configured to read from `input_context_key: "input_identifiers"`. However, the `StrategyOrchestrator` fails to add the initial list of identifiers to the context under this specific key.

**File to Modify:**

*   `/home/ubuntu/biomapper/biomapper/core/engine_components/strategy_orchestrator.py`

**Detailed Implementation Steps:**

1.  **Locate the `execute_strategy` method** within the `StrategyOrchestrator` class.

2.  **Modify the context initialization block** to add the `input_identifiers` key. This will ensure that strategy actions looking for this key receive the correct data.

    **Target Code Block (around line 147):**
    ```python
            # Initialize strategy context
            strategy_context = initial_context or {}
            strategy_context.update({
                'initial_identifiers': input_identifiers.copy(),
                'current_identifiers': current_identifiers.copy(),
                'current_ontology_type': current_ontology_type,
                # ... other keys
            })
    ```

    **New Code:**

    Add the `'input_identifiers': input_identifiers.copy()` line to the `update` call. This provides the key that the first strategy step is looking for.

    ```python
            # Initialize strategy context
            strategy_context = initial_context or {}
            strategy_context.update({
                'input_identifiers': input_identifiers.copy(),  # <<< ADD THIS LINE
                'initial_identifiers': input_identifiers.copy(),
                'current_identifiers': current_identifiers.copy(),
                'current_ontology_type': current_ontology_type,
                'step_results': [],
                'all_provenance': [],
                'mapping_results': {},
                'progress_callback': progress_callback,
                'mapping_session_id': mapping_session_id,
                'strategy_name': strategy.name,
                'source_endpoint': source_endpoint.name if source_endpoint else None,
                'target_endpoint': target_endpoint.name if target_endpoint else None,
                'initial_count': len(input_identifiers),
                'mapping_executor': self.mapping_executor  # Add mapping executor to context
            })
    ```

**Verification:**

After applying the change, the original issue should be resolved. Run the client script to confirm:

```bash
python3 /home/ubuntu/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py
```

The output should now show that the `CONVERT_UKBB_ASSAY_TO_UNIPROT` step successfully processes the input identifiers and that the pipeline proceeds to the subsequent steps, producing actual mapping results.
