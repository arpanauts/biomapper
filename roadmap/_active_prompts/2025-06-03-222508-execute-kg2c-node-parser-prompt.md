# Biomapper Project - Prompt for Claude Code Instance

**Project:** Biomapper
**Date:** {{YYYY-MM-DD}} (Claude: Please fill with current UTC date)
**Prompt ID:** {{YYYY-MM-DD-HHMMSS}}-execute-kg2c-node-parser (Claude: Please fill with current UTC timestamp)
**Author:** Cascade (via USER Request)
**Target Claude Instance Type:** Code-focused, capable of executing shell commands and writing files.

## 1. Overview & Goal:
This task is to execute an existing Python script (`parse_kg2c_nodes.py`) that performs a full parsing of the RTX KG2c nodes data file. The script will extract ontological information for various entity types and save them into separate CSV files. The goal is to run the script, monitor its execution, and generate a feedback report summarizing the process and its outputs.

## 2. Context:
- A Python script, `/home/ubuntu/biomapper/scripts/utils/parse_kg2c_nodes.py`, has already been developed and tested with an `--explore` flag.
- The script is designed to stream the large KG2c nodes JSONL file (`/procedure/data/local_data/RTX_KG2_10_1C/kg2c-2.10.1-v1.0-nodes.jsonl`).
- It extracts specified Biolink categories and outputs them as CSV files into `/home/ubuntu/biomapper/data/kg2c_ontologies/`.
- The script prints progress updates to standard output.

## 3. Task Details & Instructions for Claude Code Instance:

### 3.1. Execute the Python Script:
1.  **Command:** Execute the following Python script:
    ```bash
    python /home/ubuntu/biomapper/scripts/utils/parse_kg2c_nodes.py
    ```
2.  **Working Directory:** Ensure the command is run from a context where the script can resolve its paths correctly, ideally from `/home/ubuntu/biomapper/` or using absolute paths for all file references within the script if necessary (the script is expected to use absolute paths for input/output).
3.  **Expected Duration:** This script will process a very large file (approx. 30GB JSONL) and is expected to run for a **significant amount of time** (potentially hours). Please ensure the execution environment can support such long-running processes.
4.  **Capture Output:** Capture all standard output (stdout) and standard error (stderr) from the script execution. This output contains vital progress information and a final summary.

### 3.2. Monitor and Report:
Upon completion of the script, gather the following information for the feedback report:
1.  **Start and End Timestamps:** Record the wall-clock start and end times of the script's execution.
2.  **Exit Status:** Note the exit code of the script (0 for success).
3.  **Generated Files:**
    *   Verify that CSV files have been created in the output directory: `/home/ubuntu/biomapper/data/kg2c_ontologies/`.
    *   List all files present in this directory after the script completes.
4.  **Script Output:** Include the complete captured stdout and stderr from the script. This should include:
    *   Initial startup messages.
    *   Periodic progress updates (e.g., "Processed X nodes...").
    *   Final summary statistics (e.g., total nodes processed, counts per category).
5.  **Errors:** Document any errors or non-zero exit codes encountered during execution.

## 4. Deliverables:

1.  **Feedback Markdown File:**
    *   Create a Markdown file named `{{YYYY-MM-DD-HHMMSS}}-feedback-execute-kg2c-nodes.md` (using the current UTC timestamp for the `{{...}}` part) in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory.
    *   The content of this file should be a report detailing all the items listed in section "3.2. Monitor and Report".

## 5. Environment & Execution:
- The script requires a Python 3 environment.
- The input KG2c nodes file is located at `/procedure/data/local_data/RTX_KG2_10_1C/kg2c-2.10.1-v1.0-nodes.jsonl`.
- The output directory for CSVs is `/home/ubuntu/biomapper/data/kg2c_ontologies/`.

## 6. Format of Output from Claude Code Instance:
- The sole output should be the content for the Markdown feedback file described above.

## 7. Questions for USER:
- (None for this execution task, as the script and its configurations are presumed final for this run.)
