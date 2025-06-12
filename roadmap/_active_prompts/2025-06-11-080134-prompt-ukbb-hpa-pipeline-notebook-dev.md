# Task: Implement and Test UKBB_TO_HPA_PROTEIN_PIPELINE in Notebook

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-11-080134-prompt-ukbb-hpa-pipeline-notebook-dev.md`

## 1. Task Objective
The primary objective is to implement and test the `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy (defined in `configs/protein_config.yaml`) within the existing Jupyter notebook `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb`. This involves using the `MappingExecutor` to run the full pipeline, analyzing its outputs, and comparing its behavior to the simpler, direct client usage previously implemented in the notebook. This serves as an interactive development and verification step for the logic intended for `scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`.

## 2. Prerequisites
- [x] The project environment is set up with all dependencies installed via Poetry.
- [x] The Jupyter notebook `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` exists and contains the initial data loading and UniProt resolution steps (as per feedback file `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-10-180426-feedback-ukbb-hpa-protein-mapping-setup.md`).
- [x] `configs/protein_config.yaml` contains the definition for the `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy.
- [x] `metamapper.db` has been populated with the configurations from `protein_config.yaml`.

## 3. Context from Previous Work
- The notebook currently uses `UniProtHistoricalResolverClient` directly to resolve UniProt IDs from UKBB and HPA datasets and find overlaps.
- The `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy in `protein_config.yaml` defines a more comprehensive, multi-step mapping process:
    1.  `S1_UKBB_NATIVE_TO_UNIPROT`: UKBB Assay ID -> UniProt AC (local)
    2.  `S2_RESOLVE_UNIPROT_HISTORY`: UniProt AC -> Resolved UniProt AC (API)
    3.  `S3_FILTER_BY_HPA_PRESENCE`: Filter by UniProt ACs present in HPA data
    4.  `S4_HPA_UNIPROT_TO_NATIVE`: Resolved UniProt AC -> HPA OSP Native ID (local)
- The goal is to transition from direct client usage to using `MappingExecutor` with this defined pipeline.

## 4. Task Decomposition
Add new cells to the existing notebook `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` to perform the following subtasks. Ensure all new code and markdown cells are added sequentially after the existing content.

1.  **[Subtask 1]: Prepare Input Data for the Pipeline**
    *   Add a markdown cell explaining that this section will run the full `UKBB_TO_HPA_PROTEIN_PIPELINE`.
    *   Load the UKBB data (`/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`) into a pandas DataFrame if not already loaded and available from previous cells.
    *   Extract the list of unique UKBB Assay IDs. The `UKBB_TO_HPA_PROTEIN_PIPELINE` strategy expects `UKBB_PROTEIN_ASSAY_ID_ONTOLOGY` as its default input.
    *   Store this list in a variable (e.g., `ukbb_assay_ids`).
    *   Print the count of unique UKBB Assay IDs.

2.  **[Subtask 2]: Initialize Biomapper Components**
    *   Add a code cell to import necessary Biomapper modules if not already imported: `MappingExecutor`, `DatabaseManager`, `BiomapperConfig`.
    *   Initialize `BiomapperConfig`.
    *   Initialize `DatabaseManager` using the config.
    *   Initialize `MappingExecutor` using the database manager and config.

3.  **[Subtask 3]: Execute the `UKBB_TO_HPA_PROTEIN_PIPELINE` Strategy**
    *   Add a code cell to execute the pipeline:
        ```python
        pipeline_name = "UKBB_TO_HPA_PROTEIN_PIPELINE"
        source_endpoint_name = "UKBB_PROTEIN" # As defined in protein_config.yaml
        target_endpoint_name = "HPA_OSP_PROTEIN" # As defined in protein_config.yaml

        # The pipeline's default_source_ontology_type is UKBB_PROTEIN_ASSAY_ID_ONTOLOGY
        # The MappingExecutor will handle loading data from the source_endpoint if inputs are not directly provided
        # However, for clarity and control, we can provide the input list directly.
        # The input key for the execute_pipeline_strategy should match an expected input name
        # or be a generic list if the strategy can pick it up.
        # For this pipeline, the first step S1_UKBB_NATIVE_TO_UNIPROT uses endpoint_context: "SOURCE"
        # so it will attempt to get data from the source endpoint based on default_source_ontology_type.

        print(f"Executing pipeline: {pipeline_name}...")
        # Option 1: Let executor handle input loading based on endpoint and default ontology
        # pipeline_results = mapping_executor.execute_pipeline_strategy(
        #     strategy_name=pipeline_name,
        #     source_endpoint_name=source_endpoint_name,
        #     target_endpoint_name=target_endpoint_name
        # )

        # Option 2: Provide input data directly (more explicit for notebook)
        # The input_data dictionary keys should correspond to what the strategy/first step expects.
        # Since S1 uses CONVERT_IDENTIFIERS_LOCAL with endpoint_context: "SOURCE",
        # providing a list of source identifiers should work if the executor is adapted for it.
        # Let's try providing the input data with a generic key that the executor might pick up, or a specific one if known.
        # For now, we'll assume the executor can take a primary list of identifiers for the source_endpoint.
        pipeline_results = mapping_executor.execute_pipeline_strategy(
            strategy_name=pipeline_name,
            source_endpoint_name=source_endpoint_name,
            target_endpoint_name=target_endpoint_name,
            input_data={'source_identifiers': ukbb_assay_ids} # Or just input_data=ukbb_assay_ids
        )

        print("Pipeline execution complete.")
        # Display the structure of pipeline_results
        # For example, if it's a dictionary of step outputs:
        # for step_id, result in pipeline_results.items():
        #     print(f"\n--- Results for Step: {step_id} ---")
        #     if hasattr(result, 'shape'): # pandas DataFrame
        #         print(f"Shape: {result.shape}")
        #         display(result.head())
        #     elif isinstance(result, (list, set)):
        #         print(f"Count: {len(result)}")
        #         print(f"Sample: {list(result)[:5]}")
        #     else:
        #         print(result)
        ```
    *   **Note:** The exact way to pass `input_data` to `execute_pipeline_strategy` might need adjustment based on `MappingExecutor`'s implementation. The prompt assumes it can take a dictionary where keys are logical input names or a direct list for the primary source identifiers. If `MappingExecutor` is designed to always fetch from the `source_endpoint` based on `default_source_ontology_type` when `input_data` is not perfectly matched, then providing `ukbb_assay_ids` might be optional or require a specific input name. The user (Claude instance) should try with `input_data={'source_identifiers': ukbb_assay_ids}` first. If that fails, try with `input_data=ukbb_assay_ids`. If that also fails, try running it without `input_data` and let the executor load from the endpoint.

4.  **[Subtask 4]: Analyze Pipeline Results**
    *   Add markdown and code cells to analyze the output of `pipeline_results`.
    *   For each step in the pipeline (`S1` to `S4`), print:
        *   The number of identifiers output by that step.
        *   A small sample of the output identifiers.
        *   A sample of any provenance data generated by that step (if available in `pipeline_results`).
    *   Specifically, report:
        *   Number of UniProt ACs after S1 (UKBB native to UniProt).
        *   Number of UniProt ACs after S2 (UniProt historical resolution).
        *   Number of UniProt ACs after S3 (Filtered by HPA presence).
        *   Number of HPA OSP native IDs after S4 (Final mapped IDs).
    *   Compare the final count of mapped HPA OSP native IDs with the overlap count obtained from the simpler `UKBB_HPA_PROTEIN_RECONCILIATION` strategy (from previous notebook cells).

5.  **[Subtask 5]: Document Findings and Next Steps**
    *   Add a markdown cell summarizing the findings from running the full pipeline.
    *   Discuss any discrepancies or confirmations compared to the previous simpler mapping.
    *   Reflect on the behavior of each step in the `UKBB_TO_HPA_PROTEIN_PIPELINE`.
    *   Suggest any refinements to the pipeline definition in `protein_config.yaml` or to the `MappingExecutor` based on this interactive testing.

## 5. Implementation Requirements
- All new code and markdown cells must be added to the end of the existing notebook: `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb`.
- Use markdown cells extensively to explain each step, your assumptions, and the results.
- Ensure Python code is clean, well-commented, and follows project conventions.

## 6. Error Recovery Instructions
- **ImportError:** Ensure all necessary Biomapper components are correctly installed and importable.
- **`MappingExecutor` Initialization Error:** Check `DatabaseManager` and `BiomapperConfig` initialization. Ensure `metamapper.db` is accessible and correctly populated.
- **Pipeline Execution Error:**
    *   Verify `strategy_name`, `source_endpoint_name`, and `target_endpoint_name` exactly match the definitions in `protein_config.yaml` and `metamapper.db`.
    *   Carefully check the structure and content of `input_data` if providing it directly. The error messages might indicate issues with how input is handled by the `MappingExecutor` or the first step of the pipeline.
    *   Examine logs from `MappingExecutor` if it produces any, or add temporary print statements within the executor's methods if direct debugging is needed (though this is less ideal for a Claude instance).
    *   Ensure all clients referenced in the pipeline steps (e.g., `GenericFileLookupClient`, `UniProtHistoricalResolverClient`) are correctly configured in `protein_config.yaml` and their dependencies are met.
- **KeyError in `pipeline_results`:** The structure of `pipeline_results` might differ from the example. Inspect its actual structure (`print(pipeline_results)`) before trying to access specific step outputs.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] New cells are added to `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` that successfully execute the `UKBB_TO_HPA_PROTEIN_PIPELINE` using `MappingExecutor`.
- [ ] The notebook clearly documents the input preparation, pipeline execution, and step-by-step analysis of results (counts and sample data).
- [ ] The output of each of the four pipeline steps (`S1` to `S4`) is displayed and analyzed.
- [ ] A comparison is made with the results from the previous, simpler mapping approach in the notebook.
- [ ] The notebook includes a summary of findings and reflections on the pipeline's performance and behavior.
- [ ] The notebook runs from top to bottom without errors.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-ukbb-hpa-pipeline-notebook-run.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Link to Updated Notebook:** Provide the absolute path to the notebook.
- **Key Quantitative Results:** (e.g., # UKBB Assay IDs input, # UniProt ACs after S1, S2, S3, # HPA OSP IDs after S4).
- **Comparison with Simpler Mapping:** Brief summary of how results compare.
- **Issues Encountered & Solutions Applied:** [detailed error descriptions, how `input_data` was handled, etc.]
- **Observations on Pipeline Behavior:** Insights into how each step performed.
- **Next Action Recommendation:** Based on the outcome, suggest next steps (e.g., "Proceed to implement `run_full_ukbb_hpa_mapping.py` script", "Refine step X in `protein_config.yaml`", "Investigate discrepancies in step Y").
