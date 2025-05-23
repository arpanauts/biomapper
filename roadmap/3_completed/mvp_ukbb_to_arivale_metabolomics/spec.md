# Specification: UKBB NMR to Arivale Metabolomics Mapping

## 1. Input Data

### 1.1. UKBB NMR Metadata
*   **File:** `/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_NMR_Meta.tsv`
*   **Format:** Tab-Separated Values (TSV)
*   **Relevant Columns:**
    *   `field_id`: Unique identifier for the UKBB entry.
    *   `title`: Human-readable name of the metabolite/biomarker (primary input for RAG mapping).

### 1.2. Arivale Metabolomics Metadata
*   **File:** `/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv`
*   **Format:** Tab-Separated Values (TSV)
*   **Preprocessing:** Skip initial comment lines (typically starting with `#`).
*   **Relevant Columns:**
    *   `CHEMICAL_ID`: Internal Arivale identifier for the metabolite.
    *   `BIOCHEMICAL_NAME`: Human-readable name of the metabolite.
    *   `PUBCHEM`: PubChem CID. This is the target for matching PubChem CIDs derived from UKBB titles.
    *   `KEGG`: KEGG ID (for context in output).
    *   `HMDB`: HMDB ID (for context in output).

## 2. Core Logic & Components

### 2.1. `PubChemRAGMappingClient` Test
*   **Goal:** Validate the client's ability to map known biochemical names to their correct PubChem CIDs.
*   **Input:** A sample (10-20 entries) of `BIOCHEMICAL_NAME` and their corresponding `PUBCHEM` IDs from `metabolomics_metadata.tsv`.
*   **Process:**
    1.  For each sample `BIOCHEMICAL_NAME`, call `pubChemRAGClient.map_identifiers()`.
    2.  Compare the RAG-derived PubChem CID(s) and confidence score(s) against the known `PUBCHEM` ID.
*   **Output:** A report/log detailing:
    *   Input `BIOCHEMICAL_NAME`.
    *   Ground truth `PUBCHEM` ID.
    *   RAG-derived PubChem CID(s).
    *   RAG confidence score(s).
    *   Match status (Correct, Incorrect, No Match).

### 2.2. Main Mapping Process
1.  **Load Data:**
    *   Load UKBB `title` and `field_id` into a suitable data structure (e.g., list of dicts, Pandas DataFrame).
    *   Load Arivale metabolomics data, creating an efficient lookup dictionary mapping `PUBCHEM` ID to the corresponding row data (including `CHEMICAL_ID`, `BIOCHEMICAL_NAME`, `KEGG`, `HMDB`). Handle potential missing or multiple PubChem IDs per Arivale entry if necessary.
2.  **Iterate and Map:**
    *   For each unique `title` in the UKBB data:
        *   Invoke `pubChemRAGClient.map_identifiers([ukbb_title])`.
        *   Receive derived PubChem CID(s) and confidence score(s).
        *   **Decision Logic:**
            *   If a single, high-confidence PubChem CID is returned (threshold to be determined, e.g., >0.8):
                *   Attempt to find this PubChem CID in the Arivale `PUBCHEM` lookup.
                *   If found, record as a successful match.
                *   If not found, record as "Mapped to PubChem, Not in Arivale."
            *   If multiple PubChem CIDs are returned or confidence is moderate:
                *   For MVP, prioritize the highest confidence match. If it meets a threshold, attempt Arivale lookup.
                *   Log other candidates if necessary.
            *   If RAG mapping fails or confidence is very low:
                *   Record as "RAG Mapping Failed."
3.  **Store Results:** Accumulate mapping results in a list or DataFrame.

## 3. Output File

*   **Format:** Tab-Separated Values (TSV)
*   **Name:** `ukbb_to_arivale_metabolomics_mapping.tsv` (or similar)
*   **Columns:**
    *   `ukbb_field_id`
    *   `ukbb_title`
    *   `derived_pubchem_cid` (from RAG)
    *   `rag_confidence_score`
    *   `mapping_status` (e.g., "Successfully Mapped to Arivale", "Mapped to PubChem - Not in Arivale", "RAG Mapping Failed", "Multiple RAG Candidates")
    *   `arivale_chemical_id` (if successfully mapped)
    *   `arivale_biochemical_name` (if successfully mapped)
    *   `arivale_pubchem_id` (the matching PubChem ID from Arivale, for verification)
    *   `arivale_kegg_id` (if successfully mapped)
    *   `arivale_hmdb_id` (if successfully mapped)

## 4. Success Criteria

*   The RAG client test script runs and produces interpretable results.
*   The main mapping script processes all UKBB titles.
*   The output TSV is generated in the specified format.
*   A significant portion of UKBB titles (where applicable) are successfully mapped to Arivale entries with reasonable confidence scores.
*   Mapping statistics (counts for each `mapping_status`) are reported.
