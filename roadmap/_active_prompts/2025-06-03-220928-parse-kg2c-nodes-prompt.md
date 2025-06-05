# Meta-Prompt: Analyze KG2c Node Data and Extract Ontological Datasets

## 1. Project & Task Overview:
*   **Project:** Biomapper
*   **Current Goal:** To process the RTX KG2c (Knowledge Graph 2, canonicalized) node data to extract structured ontological information for various entity types (e.g., proteins, metabolites, genes, diseases). This data will be used for downstream mapping and integration tasks within Biomapper.
*   **Task:** Develop a Python script that can:
    1.  Analyze the schema of the `kg2c-2.10.1-v1.0-nodes.jsonl` file.
    2.  Stream-process this large JSON Lines file.
    3.  Extract relevant information (ID, name, category, description, synonyms, cross-references) for predefined Biolink entity categories.
    4.  Output this information into separate CSV files, one for each targeted entity type.

## 2. Context & Background:
*   The primary data source is `/procedure/data/local_data/RTX_KG2_10_1C/kg2c-2.10.1-v1.0-nodes.jsonl`. This file contains nodes from the KG2c knowledge graph, with each line being a JSON object representing a node.
*   KG2c is built from KG2pre and utilizes Biolink Model categories. Node synonymization is a key feature of its build process.
*   The file `/procedure/data/local_data/RTX_KG2_10_1C/README_kg2c.md` provides general context about KG2c but may not detail the `nodes.jsonl` schema.
*   The output CSVs are intended to serve as readily usable ontological datasets for Biomapper.

## 3. Specific Instructions for Claude Code Instance:

### 3.1. Deliverables:
1.  **Python Script (`parse_kg2c_nodes.py`):**
    *   Place this script in `/home/ubuntu/biomapper/scripts/utils/` (create `utils` if it doesn't exist).
    *   The script must perform two main functions as detailed below: schema discovery (Part A) and full data extraction (Part B).
2.  **Markdown Feedback File:**
    *   Generate a feedback file named `YYYY-MM-DD-HHMMSS-feedback-parse-kg2c-nodes.md` (using the current UTC timestamp) in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/`.
    *   This file must document:
        *   **Schema Discovery Results:** Clearly list the identified JSON keys for `id`, `name`, `category`, `description`, `synonyms`, and `xrefs`. Include examples of values for each.
        *   **Script Design Decisions:** Explain choices made, e.g., how missing fields are handled, how lists are formatted in CSV.
        *   **Execution Summary (if script is run by Claude):** If you are able to run the script, include counts of nodes processed and entities extracted per category.
        *   **Potential Issues/Limitations:** Note any ambiguities in the data or limitations of the script.
        *   **Suggestions for Improvement:** If any.
        *   **Confirmation of Task Completion:** State whether the script is ready for testing by the USER.

### 3.2. Python Script Detailed Requirements (`parse_kg2c_nodes.py`):

#### Part A: Initial Exploration and Schema Discovery (for internal use by the script or for reporting in feedback)
*   **Functionality:** Implement a function or section that can:
    *   Open `/procedure/data/local_data/RTX_KG2_10_1C/kg2c-2.10.1-v1.0-nodes.jsonl`.
    *   Read and parse the first ~10-20 lines (JSON objects).
    *   Log or prepare for reporting (in the Markdown feedback) the common keys and example values, specifically trying to identify the fields corresponding to:
        *   Node ID (CURIE)
        *   Preferred/Canonical Name
        *   Node Category (Biolink CURIE, e.g., `biolink:Protein`)
        *   Textual Description
        *   Synonyms (and their format, e.g., list of strings)
        *   Cross-references/Equivalent Identifiers (and their format)
    *   This part helps confirm the field names before full processing.

#### Part B: Full Data Extraction and CSV Generation
*   **Configuration:**
    *   Define a dictionary mapping target Biolink categories to output CSV filenames and human-readable entity type names. This should be easily modifiable at the top of the script.
        ```python
        TARGET_ENTITY_CATEGORIES = {
            "biolink:Protein": {"file": "kg2c_proteins.csv", "name": "Protein"},
            "biolink:SmallMolecule": {"file": "kg2c_metabolites.csv", "name": "Metabolite"},
            "biolink:Gene": {"file": "kg2c_genes.csv", "name": "Gene"},
            "biolink:Disease": {"file": "kg2c_diseases.csv", "name": "Disease"},
            "biolink:PhenotypicFeature": {"file": "kg2c_phenotypes.csv", "name": "Phenotype"},
            "biolink:Pathway": {"file": "kg2c_pathways.csv", "name": "Pathway"},
            # User can add more categories as needed
        }
        # Absolute path for output
        OUTPUT_DIR = "/home/ubuntu/biomapper/data/kg2c_ontologies/"
        ```
    *   Use the field names identified in Part A (or assume common ones if Part A is for reporting only, but make this clear).

*   **Core Logic:**
    *   Ensure `OUTPUT_DIR` exists; create it if it doesn't using `os.makedirs(exist_ok=True)`.
    *   Implement streaming processing for `/procedure/data/local_data/RTX_KG2_10_1C/kg2c-2.10.1-v1.0-nodes.jsonl` to handle its large size.
    *   For each node (JSON object):
        1.  Safely extract its category.
        2.  If the category matches one in `TARGET_ENTITY_CATEGORIES`:
            a.  Extract `id`, `name`, `category_val` (the actual category string), `description`. Use `.get()` with defaults (e.g., empty string) for robustness.
            b.  Extract `synonyms` and `xrefs`. These might be lists. If so, convert them to pipe-separated strings for the CSV (e.g., `"syn1|syn2"`). If a field is missing or null, use an empty string in the CSV.
            c.  Write the extracted data as a new row to the corresponding entity-specific CSV file (located in `OUTPUT_DIR`).
    *   Initialize each CSV file with headers: `id,name,category,description,synonyms,xrefs`.
    *   Include basic error handling (e.g., for JSON parsing errors, log and skip problematic lines).
    *   Provide progress updates to `stdout` (e.g., every 100,000 nodes processed, indicate counts per category found so far).

*   **Libraries:** Use standard Python libraries (`json`, `csv`, `os`). No external packages requiring `poetry add` are anticipated unless absolutely necessary (explain in feedback if so).

### 3.3. Environment & Execution:
*   The script will be executed in an environment where Python 3 is available.
*   Assume the input `nodes.jsonl` file exists at the specified absolute path.

## 4. Definition of Done:
*   The Python script `parse_kg2c_nodes.py` is created at `/home/ubuntu/biomapper/scripts/utils/parse_kg2c_nodes.py` and implements all specified functionalities.
*   The Markdown feedback file is generated in `/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/` and contains all requested information.
*   The script is robust enough to handle potential variations in the JSON structure (e.g., missing fields) and can process the large input file without excessive memory usage.
*   The generated CSV files have the correct headers and data format.

## 5. Format of Output from Claude Code Instance:
*   The primary output should be the Python script content.
*   The secondary output should be the content for the Markdown feedback file.
*   Clearly delineate these two outputs.

## 6. Questions for USER (to be answered by USER before Claude Code instance proceeds, if necessary):
*   Are there any other specific Biolink categories to target initially beyond Protein, SmallMolecule, Gene, Disease, PhenotypicFeature, Pathway?
*   Is the output directory `/home/ubuntu/biomapper/data/kg2c_ontologies/` acceptable, or should another be used?

