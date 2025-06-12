# Prompt: Verify Database Population

## 1. Task Objective
Execute the `populate_metamapper_db.py` script and inspect the resulting `metamapper.db` to verify that it is correctly populated from the project's YAML configuration files.

## 2. Expected Outputs
1.  **Feedback File:** A single markdown file created at `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-11-214645-feedback-verify-db-population.md`.

## 3. Task Decomposition
1.  **Execute Population Script:** Run the command `python /home/ubuntu/biomapper/scripts/setup_and_configuration/populate_metamapper_db.py --drop-all`.
2.  **Inspect Database:** Run the following `sqlite3` commands:
    - `sqlite3 /home/ubuntu/biomapper/data/metamapper.db "SELECT name FROM mapping_strategy;"`
    - `sqlite3 /home/ubuntu/biomapper/data/metamapper.db "SELECT name FROM endpoint;"`
3.  **Generate Feedback:** Create the feedback file specified above and populate it with the full, unedited console output from the commands in steps 1 and 2, placed within appropriate markdown code blocks. Conclude the file with a structured outcome report as shown in the template below.

## 4. Feedback File Template
Please use the following template for the feedback file.

````markdown
# Feedback: Database Population Verification

## Execution Logs

### `populate_metamapper_db.py` Output
```bash
<PASTE FULL OUTPUT HERE>
```

### `sqlite3` Inspection Output
```bash
<PASTE FULL OUTPUT HERE>
```

## Outcome Analysis

**Status:** (Choose one: `COMPLETE_SUCCESS`, `PARTIAL_SUCCESS`, `FAILED_NEEDS_ESCALATION`)

**Summary:**
<Provide a brief summary of the outcome. If successful, state that the database appears to be populated correctly. If failed, describe the error.>
````

## 5. Source Prompt Reference
*   `/home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-11-214645-prompt-verify-db-population.md`
