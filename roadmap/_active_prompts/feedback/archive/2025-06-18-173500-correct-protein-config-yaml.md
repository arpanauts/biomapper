# Task: Correct and Complete protein_config.yaml

**Source Prompt Reference:** This task is defined by the prompt: /home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/2025-06-18-173500-correct-protein-config-yaml.md

## 1. Task Objective
Modify the existing `configs/protein_config.yaml` to fully meet the original requirements. This involves adding two missing database configurations (HPP and Function Health) and replacing all hardcoded file paths with a `${DATA_DIR}` placeholder.

## 2. Prerequisites
- [ ] Required files exist: `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml`
- [ ] Required permissions: Write access to the file specified above.

## 3. Context from Previous Attempts (if applicable)
- **Previous attempt timestamp:** A previous agent successfully generated `protein_config.yaml` but missed two database sections and used hardcoded file paths instead of the required `${DATA_DIR}` placeholder.
- **Issues encountered:** Omission of HPP and Function Health configurations; failure to use `${DATA_DIR}`.
- **Partial successes:** The overall structure of the YAML is correct and provides a good foundation.

## 4. Task Decomposition
1. **Add HPP Configuration:** In the `databases` section, add a new entry for `hpp`. Assume a plausible file path like `${DATA_DIR}/HPP/protein_data.tsv` and define its properties and a simple mapping client, similar to the other entries.
2. **Add Function Health Configuration:** In the `databases` section, add a new entry for `function_health`. Assume a plausible path like `${DATA_DIR}/FunctionHealth/protein_data.csv` and define its properties and a mapping client.
3. **Replace Hardcoded Paths:** Perform a search-and-replace across the entire file. Replace all instances of hardcoded paths like `/procedure/data/local_data/` and `/home/ubuntu/biomapper/data/` within `file_path` keys with `${DATA_DIR}/`. For example, `/home/ubuntu/biomapper/data/UKBB_Protein_Meta.tsv` should become `${DATA_DIR}/UKBB_Protein_Meta.tsv`.
4. **Create Feedback File:** Generate a feedback file confirming the changes.

## 5. Implementation Requirements
- **Input files/data:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml`
- **Expected outputs:**
    - An updated `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml` with the corrections.
    - A new feedback file at `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-correct-protein-config-yaml.md`.
- **Validation requirements:** The final YAML must be valid and include all 8 database configurations (Arivale, UKBB, SPOKE, KG2, HPA, QIN, HPP, Function Health) with `${DATA_DIR}` paths.

## 6. Error Recovery Instructions
- **File Not Found:** If `protein_config.yaml` does not exist, report a `FAILED_NEEDS_ESCALATION` error.
- **YAML Parsing Error:** If the file is malformed and cannot be parsed, report a `FAILED_NEEDS_ESCALATION` error.

## 7. Success Criteria and Validation
Task is complete when:
- [ ] `configs/protein_config.yaml` contains database configurations for HPP and Function Health.
- [ ] All `file_path` values in `configs/protein_config.yaml` start with `${DATA_DIR}/`.
- [ ] The feedback file is created, confirming the modifications.

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/roadmap/_active_prompts/feedback/YYYY-MM-DD-HHMMSS-feedback-correct-protein-config-yaml.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [Checklist of what was accomplished]
- **Issues Encountered:** [Report any difficulties]
- **Next Action Recommendation:** [e.g., "The protein_config.yaml is now complete. Ready to proceed with database population."]
- **Confidence Assessment:** [High]
- **Environment Changes:** [e.g., "Modified file: /home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/configs/protein_config.yaml"]
