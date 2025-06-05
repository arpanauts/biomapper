# Biomapper Project - Prompt for Claude Code Instance

**Project:** Biomapper
**Date:** {{YYYY-MM-DD}} (Claude: Please fill with current UTC date)
**Prompt ID:** {{YYYY-MM-DD-HHMMSS}}-parse-spoke-nodes (Claude: Please fill with current UTC timestamp)
**Author:** Cascade (via USER Request)
**Target Claude Instance Type:** Code-focused, capable of executing shell commands, writing files, and analyzing data structures.

## 1. Overview & Goal:
The primary goal is to analyze the structure of the SPOKE v6 nodes data file (`/home/ubuntu/data/spokeV6.jsonl`) and then generate a Python script to extract detailed ontological information for various entity types. This script should be similar in functionality to one previously created for KG2c data, outputting structured data into CSV format.

## 2. Context:
- The USER is working on the Biomapper project, which involves processing and integrating biomedical ontological data.
- A similar task was recently completed for the RTX KG2c nodes file. This task should leverage similar logic and output formats.
- The input file for this task is `/home/ubuntu/data/spokeV6.jsonl`.
- The output CSV files should be placed in a new directory: `/home/ubuntu/biomapper/data/spoke_ontologies/`.

## 3. Task Details & Instructions for Claude Code Instance:

### 3.1. Python Script Requirements (`parse_spoke_nodes.py`):

#### Part A: Schema Discovery (to be integrated into the script)
*   The script should include a function or mode (e.g., triggered by an `--explore` command-line flag) to analyze and report on the schema of the `spokeV6.jsonl` file.
*   This discovery should:
    *   Identify common top-level JSON keys in the nodes.
    *   For each key, determine its data type (string, number, list, object).
    *   Provide examples of values for key fields, especially for `id`, `name` (or equivalent), `category` (or equivalent), `description`, `synonyms` (or equivalent), and `cross-references`/`xrefs` (or equivalent).
    *   Pay attention to how entity categories are represented (e.g., Biolink CURIEs, simple strings).
    *   This part helps confirm the field names before full processing and should be part of the feedback report.

#### Part B: Full Data Extraction and CSV Generation
*   **Configuration:**
    *   Define a dictionary mapping target Biolink categories (or SPOKE-specific categories if Biolink is not used directly) to output CSV filenames and human-readable entity type names. This should be easily modifiable at the top of the script.
        ```python
        # Example, adjust based on SPOKE's actual category representation
        TARGET_ENTITY_CATEGORIES = {
            "biolink:Protein": {"file": "spoke_proteins.csv", "name": "Protein"},
            "biolink:SmallMolecule": {"file": "spoke_metabolites.csv", "name": "Metabolite"}, # Or e.g., "ChemicalSubstance"
            "biolink:Gene": {"file": "spoke_genes.csv", "name": "Gene"},
            "biolink:Disease": {"file": "spoke_diseases.csv", "name": "Disease"},
            "biolink:PhenotypicFeature": {"file": "spoke_phenotypes.csv", "name": "Phenotype"},
            "biolink:Pathway": {"file": "spoke_pathways.csv", "name": "Pathway"},
            "biolink:Drug": {"file": "spoke_drugs.csv", "name": "Drug"},
            # Add other relevant categories based on SPOKE data, e.g., Anatomy, BiologicalProcess
        }
        # Absolute path for output
        OUTPUT_DIR = "/home/ubuntu/biomapper/data/spoke_ontologies/"
        ```
    *   Use the field names identified in Part A. Make it clear in the feedback if assumptions are made.

*   **Core Logic:**
    *   Ensure `OUTPUT_DIR` exists; create it if it doesn't using `os.makedirs(exist_ok=True)`.
    *   Implement streaming processing for `/home/ubuntu/data/spokeV6.jsonl` to handle its potentially large size.
    *   The script should focus only on processing node objects; any lines representing edges or relationships should be ignored if encountered.
    *   For each node (JSON object):
        1.  Safely extract its category (or type).
        2.  If the category matches one in `TARGET_ENTITY_CATEGORIES`:
            a.  Extract `id`, `name`, `category_val` (the actual category string), `description`. Use `.get()` with defaults (e.g., empty string) for robustness.
            b.  Extract `synonyms` and `xrefs` (or their equivalents). These might be lists or nested structures. If so, convert them to pipe-separated strings for the CSV (e.g., `"syn1|syn2"`). If a field is missing or null, use an empty string in the CSV.
            c.  Write the extracted data as a new row to the corresponding entity-specific CSV file (located in `OUTPUT_DIR`).
    *   Initialize each CSV file with headers: `id,name,category,description,synonyms,xrefs`. (Adjust headers if SPOKE uses different primary fields).
    *   Include basic error handling (e.g., for JSON parsing errors, log and skip problematic lines).
    *   Provide progress updates to `stdout` (e.g., every 100,000 nodes processed, indicate counts per category found so far).

*   **Libraries:** Use standard Python libraries (`json`, `csv`, `os`). No external packages requiring `poetry add` are anticipated unless absolutely necessary (explain in feedback if so).

### 3.2. Environment & Execution:
*   The script will be executed in an environment where Python 3 is available.
*   Assume the input `spokeV6.jsonl` file exists at the specified absolute path.

## 4. Deliverables:

1.  **Python Script (`parse_spoke_nodes.py`):**
    *   To be saved at `/home/ubuntu/biomapper/scripts/utils/parse_spoke_nodes.py`.
    *   Must implement all functionalities specified in section 3.1.

2.  **Feedback Markdown File:**
    *   Create a Markdown file named `{{YYYY-MM-DD-HHMMSS}}-feedback-parse-spoke-nodes.md` (using the current UTC timestamp for the `{{...}}` part) in the `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` directory.
    *   This file should document:
        *   **Schema Discovery Results:** Detailed findings from analyzing `spokeV6.jsonl` (keys, data types, examples, how categories are represented).
        *   **Script Design Decisions:** Key choices made during script development (e.g., field mappings, handling of complex data, error strategy).
        *   **Assumptions Made:** Any assumptions about the SPOKE data structure.
        *   **Potential Issues/Limitations:** Any foreseen challenges or limitations with the script or data.
        *   **Execution Summary (Anticipated):** A brief note on how to run the script (e.g., `python ... --explore` and `python ...` for full run).
        *   Confirmation that the script is ready for USER testing.

## 5. Format of Output from Claude Code Instance:
*   The primary output should be the Python script content for `parse_spoke_nodes.py`.
*   The secondary output should be the content for the Markdown feedback file.
*   Clearly delineate these two outputs.

## 6. Questions for USER (to be answered by USER before Claude Code instance proceeds, if necessary):
*   Are there any specific fields from SPOKE nodes (beyond id, name, category, description, synonyms, xrefs) that are critical to extract?
*   Is the proposed output directory `/home/ubuntu/biomapper/data/spoke_ontologies/` acceptable?
*   Should the script attempt to map SPOKE-specific categories to Biolink terms if they differ significantly, or just use SPOKE's native categories? (For now, assume using SPOKE's native categories and reporting them is fine, but note if a mapping seems feasible/desirable).
