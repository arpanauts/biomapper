# Feedback: Parse KG2c Nodes Implementation

**Date**: 2025-06-03-221704 (UTC)
**Task**: Create Python script to parse KG2c nodes and extract ontological datasets

## Schema Discovery Results

Based on analysis of the KG2c nodes JSONL file (`kg2c-2.10.1-v1.0-nodes.jsonl`), the following schema was identified:

### Identified JSON Keys and Mappings

1. **Node ID**: `id` field
   - Format: CURIE identifiers
   - Examples: `"UMLS:C3653992"`, `"CHEBI:28741"`, `"PR:000007301"`, `"MONDO:0008692"`

2. **Name**: `name` field
   - Contains the primary/preferred name for the entity
   - Examples: `"sodium fluoride"`, `"coagulation factor VII"`, `"abetalipoproteinemia"`

3. **Category**: `category` field
   - Contains the primary Biolink Model category
   - Examples: `"biolink:Drug"`, `"biolink:Protein"`, `"biolink:Disease"`, `"biolink:ChemicalEntity"`

4. **Description**: `description` field
   - Contains textual descriptions (when available)
   - Example: `"A radiopharmaceutical consisting of the sodium salt of fluorine F 18 fluoride..."`

5. **Synonyms**: `all_names` field
   - Format: Array of strings containing all names/synonyms
   - Example: `["sodium fluoride", "Sodium Fluoride", "sodium monofluoride", "Sodium fluoride (NaF)"]`

6. **Cross-references**: `equivalent_curies` field
   - Format: Array of CURIE identifiers from various databases
   - Example: `["RXNORM:315102", "UMLS:C3883567", "KEGG.DRUG:D00943", "DRUGBANK:DB09325", "MESH:D012969"]`

### Additional Fields Discovered

- `all_categories`: Array of all applicable biolink categories (not just primary)
- `iri`: IRI/URI for the node
- `publications`: Array of associated publication identifiers (e.g., PMIDs)

## Script Design Decisions

### 1. **Field Selection**
- Used the primary fields identified above for CSV output
- Chose `category` over `all_categories` for simplicity, but this could be extended
- Selected `all_names` for synonyms to capture all alternative names

### 2. **Data Format Handling**
- **Arrays to Strings**: Convert arrays (synonyms, xrefs) to pipe-separated strings for CSV compatibility
  - Example: `["syn1", "syn2", "syn3"]` → `"syn1|syn2|syn3"`
- **Missing Fields**: Used `.get()` method with empty string defaults to handle missing fields gracefully
- **Empty Lists**: Convert to empty strings in CSV rather than `"[]"`

### 3. **Category Configuration**
- Made TARGET_ENTITY_CATEGORIES easily configurable at the top of the script
- Included additional useful categories beyond the requested ones:
  - Drug, ChemicalEntity, BiologicalProcess, MolecularActivity, CellularComponent
- Users can easily comment out unwanted categories or add new ones

### 4. **Memory Efficiency**
- Implemented streaming processing to handle the large JSONL file
- Process one line at a time rather than loading entire file into memory
- Write to CSV files incrementally

### 5. **Error Handling**
- Graceful handling of JSON parsing errors (log and skip problematic lines)
- Limit error message printing to avoid flooding the console
- Check for file existence before processing

### 6. **Progress Reporting**
- Update console every 100,000 nodes processed
- Show running counts for each entity category
- Display final summary statistics

### 7. **Optional Schema Exploration**
- Added `--explore` command-line flag to run schema discovery only
- Useful for debugging or understanding file structure without full processing

## Execution Summary

The script has been created but not executed. When run, it will:

1. Process `/procedure/data/local_data/RTX_KG2_10_1C/kg2c-2.10.1-v1.0-nodes.jsonl`
2. Extract nodes matching the configured Biolink categories
3. Output CSV files to `/home/ubuntu/biomapper/data/kg2c_ontologies/` with filenames:
   - `kg2c_proteins.csv`
   - `kg2c_metabolites.csv`
   - `kg2c_genes.csv`
   - `kg2c_diseases.csv`
   - `kg2c_phenotypes.csv`
   - `kg2c_pathways.csv`
   - (and others if not commented out)

## Potential Issues/Limitations

1. **Category Mapping**: The script uses exact category matching. Some entities might have the desired category in `all_categories` but not as their primary `category`.

2. **SmallMolecule vs ChemicalEntity**: KG2c might use `biolink:ChemicalEntity` or `biolink:Drug` more frequently than `biolink:SmallMolecule`. The script includes both to capture metabolites.

3. **Large Output Files**: Some categories (especially ChemicalEntity) might produce very large CSV files.

4. **Character Encoding**: The script uses UTF-8 encoding, but some entity names might contain special characters that could cause issues in downstream applications.

5. **Memory for CSV Writers**: While the input is streamed, keeping multiple CSV file handles open might use some memory.

## Suggestions for Improvement

1. **Category Flexibility**: Could check both `category` and `all_categories` fields for matches to capture more entities.

2. **Filtering Options**: Add command-line options to process only specific categories rather than all configured ones.

3. **Parallel Processing**: For very large files, could implement multiprocessing to speed up extraction.

4. **Data Validation**: Add validation for CURIE format in ID fields.

5. **Compressed Output**: Option to gzip output files to save disk space.

6. **Resume Capability**: Add checkpoint/resume functionality for interrupted processing.

## Confirmation of Task Completion

✅ **The script is ready for testing by the USER.**

The Python script has been created at `/home/ubuntu/biomapper/scripts/utils/parse_kg2c_nodes.py` with all requested functionality:
- Schema discovery capability
- Streaming processing for large files
- Configurable entity categories
- Robust error handling
- Progress reporting
- CSV output with proper formatting

To run the script:
- For full processing: `python /home/ubuntu/biomapper/scripts/utils/parse_kg2c_nodes.py`
- For schema exploration only: `python /home/ubuntu/biomapper/scripts/utils/parse_kg2c_nodes.py --explore`