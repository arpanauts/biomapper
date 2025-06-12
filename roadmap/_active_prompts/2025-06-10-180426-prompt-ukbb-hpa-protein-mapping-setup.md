# Task: Initial Setup for UKBB-to-HPA Protein Mapping in a Notebook

**Source Prompt Reference:** This task is defined by the prompt: `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-10-180426-prompt-ukbb-hpa-protein-mapping-setup.md`

## 1. Task Objective
The primary objective is to perform the initial setup and investigation for mapping proteins between the UKBB and HPA datasets using the Biomapper framework. All work will be conducted within a new, dedicated Jupyter notebook. The focus is on configuring the necessary data sources, performing an initial ID resolution and overlap analysis, and establishing a foundation for more complex bidirectional mapping and reconciliation later.

## 2. Prerequisites
- [x] The project environment is set up with all dependencies installed via Poetry.
- [x] A blank Jupyter notebook exists at: `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb`.
- [x] The source data files exist at:
    - `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv`
    - `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv`

## 3. Context from Previous Attempts (if applicable)
This is the first attempt at this specific mapping task. However, leverage existing knowledge from memories:
- **UniProt Resolution is Mandatory:** For protein datasets like these, resolving historical UniProt IDs via `UniProtHistoricalResolverClient` is a required first step (MEMORY[f09ede1e-390a-49dc-b881-513aebc117b5]).
- **YAML Configuration:** All new data sources and mapping clients must be defined in `configs/protein_config.yaml` and then synchronized to `metamapper.db` using `scripts/populate_metamapper_db.py` (MEMORY[9de2a760-6829-452b-b2c2-bba9c90cf953]).
- **Previous UKBB Config:** The `UKBB_Protein_Meta.tsv` file has been configured before. Review existing entries in `protein_config.yaml` to see how it was handled (MEMORY[c3f81352-4385-4f0e-b00f-c46577cbec43], MEMORY[b6812ec3-907e-4aea-8aa4-ed198c4ce442]).

## 4. Task Decomposition
Break this task into the following verifiable subtasks. Perform all steps within the notebook `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` unless specified otherwise.

1.  **[Subtask 1]: Data Investigation & Exploration**
    *   In the notebook, import `pandas`.
    *   Load `/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv` into a DataFrame.
    *   Load `/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv` into a DataFrame.
    *   For each DataFrame, display the first few rows (`.head()`) and the column names (`.columns`).
    *   Identify the column(s) in each file that contain UniProt identifiers.
    *   Add markdown cells to the notebook summarizing your findings: the relevant column names for each dataset and the total number of entries in each.

2.  **[Subtask 2]: Update YAML Configuration**
    *   Edit the `/home/ubuntu/biomapper/configs/protein_config.yaml` file.
    *   **For HPA:** Add a new entry under `databases` for the HPA dataset. This will include an `endpoint` definition (for the CSV file itself) and a `mapping_clients` definition for a file-based lookup client.
    *   **For UKBB:** Verify if a suitable `endpoint` and `mapping_client` already exist for `UKBB_Protein_Meta.tsv`. If not, add or update them.
    *   **Add a Mapping Strategy:** In `protein_config.yaml`, add a new entry under `mapping_strategies` for this task.
        ```yaml
        UKBB_HPA_PROTEIN_RECONCILIATION:
          description: "Resolves UniProt IDs from UKBB and HPA and finds the overlap."
          target_ontology: "UNIPROTKB_AC"
          steps:
            - name: "Resolve UKBB UniProt IDs"
              action:
                type: "RESOLVE_UNIPROT_HISTORY"
              inputs:
                - "UKBB_PROTEIN_LIST" # This is a placeholder name for the input data
              outputs:
                - "UKBB_RESOLVED_UNIPROTS"
            - name: "Resolve HPA UniProt IDs"
              action:
                type: "RESOLVE_UNIPROT_HISTORY"
              inputs:
                - "HPA_PROTEIN_LIST" # Placeholder
              outputs:
                - "HPA_RESOLVED_UNIPROTS"
        ```

3.  **[Subtask 3]: Synchronize Configuration Database**
    *   In a notebook cell using the `!` prefix for shell commands, run the `populate_metamapper_db.py` script to load your YAML changes into the `metamapper.db`.
    *   Command: `!python scripts/populate_metamapper_db.py --config_path configs/protein_config.yaml`
    *   Ensure the command executes successfully and capture its output in the notebook.

4.  **[Subtask 4]: Initial Mapping in Notebook**
    *   Add new Python cells to the notebook.
    *   Import necessary Biomapper modules (`MappingExecutor`, `DatabaseManager`).
    *   Extract the lists of UniProt IDs from the two DataFrames you loaded in Subtask 1.
    *   Initialize the `DatabaseManager` and `MappingExecutor`.
    *   Invoke the `MappingExecutor` to run the `UKBB_HPA_PROTEIN_RECONCILIATION` strategy you defined. You will need to pass the two lists of protein IDs as inputs, using the placeholder names from your strategy definition (e.g., `UKBB_PROTEIN_LIST`).
    *   Retrieve the results from the executor.
    *   Perform a simple set intersection on the two resolved lists of UniProt IDs.
    *   Print the number of IDs in each original list, the number in each resolved list, and the final number of overlapping IDs.
    *   Display a sample of the provenance data for a few of the resolved IDs.

## 5. Implementation Requirements
- All investigative code, configuration commands, and mapping logic must be performed and documented within the `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` notebook.
- Use markdown cells extensively to explain each step, your assumptions, and the results.
- Ensure YAML edits are clean and correctly formatted.

## 6. Error Recovery Instructions
- **FileNotFoundError:** Double-check the absolute paths to the data files.
- **YAML Parse Error:** Carefully check your YAML syntax (indentation, colons, etc.) in `protein_config.yaml`.
- **Database Population Error:** Read the output from `populate_metamapper_db.py` carefully. It may indicate missing keys in your YAML or other inconsistencies.
- **`MappingExecutor` Error:** Check that the strategy name and input/output names match exactly between your Python code and the YAML file. Ensure the required clients (like `UniProtHistoricalResolverClient`) are available.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] The notebook `/home/ubuntu/biomapper/notebooks/2_use_cases/ukbb_to_hpa_protein.ipynb` is fully populated and executes from top to bottom without errors.
- [ ] The notebook contains markdown cells explaining the data investigation and the mapping process.
- [ ] `configs/protein_config.yaml` has been updated with new `Endpoint`, `MappingClient`, and `MappingStrategy` definitions for the UKBB-HPA mapping.
- [ ] The `populate_metamapper_db.py` script has been run successfully, syncing the new configurations.
- [ ] The notebook successfully uses `MappingExecutor` to run the strategy and prints the final count of overlapping, resolved UniProt IDs.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-ukbb-hpa-protein-mapping-setup.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Link to Notebook:** Provide the absolute path to the completed notebook.
- **Issues Encountered:** [detailed error descriptions with context]
- **Next Action Recommendation:** Suggest next steps, e.g., "Implement bidirectional mapping logic" or "Refine provenance handling."
