# UniProt REST API

## Overview

UniProt provides a comprehensive, high-quality, and freely accessible resource of protein sequence and functional information. Biomapper utilizes UniProt's REST API for two primary mapping functions: mapping between different identifier types for a known UniProt entry and searching for UniProt entries based on gene or protein names.

**Base URL:** `https://rest.uniprot.org`

**Official Documentation:** [https://www.uniprot.org/help/programmatic_access](https://www.uniprot.org/help/programmatic_access)

## Endpoints Used by Biomapper

### 1. ID Mapping (`/idmapping`)

*   **Biomapper Client:** `biomapper.mapping.clients.uniprot_focused_mapper.UniprotFocusedMapper`
*   **Resource Name:** `UniProt_IDMapper` (Example, confirm actual name in `metamapper.db`)
*   **Purpose:** Maps known UniProtKB accession IDs to equivalent IDs in other databases (e.g., PDB, RefSeq, KEGG).
*   **Method:** Submits asynchronous batch jobs (`/idmapping/run`) and polls for results (`/idmapping/status/{jobId}`, `/idmapping/results/{jobId}`).
*   **Key Parameters:**
    *   `ids`: Comma-separated list of UniProtKB accessions.
    *   `from`: Source database (typically `UniProtKB_AC-ID`).
    *   `to`: Target database name (e.g., `KEGG`, `PDB`).
*   **Reference:** [https://www.uniprot.org/help/id_mapping](https://www.uniprot.org/help/id_mapping)

### 2. UniProtKB Search (`/uniprotkb/search`)

*   **Biomapper Client:** `biomapper.mapping.clients.uniprot_name_client.UniProtNameClient`
*   **Resource Name:** `UniProt_NameSearch` (Example, confirm actual name in `metamapper.db`)
*   **Purpose:** Searches for UniProtKB entries based on protein names, gene names, or other criteria to retrieve UniProtKB accession IDs.
*   **Method:** Synchronous GET requests.
*   **Key Parameters:**
    *   `query`: Search query string using UniProt query syntax (e.g., `(gene:APP OR protein_name:APP) AND (organism_id:9606) AND (reviewed:true)`). Common fields include `gene`, `protein_name`, `organism_id`, `reviewed`.
    *   `fields`: Comma-separated list of fields to return (e.g., `accession,gene_primary`).
    *   `format`: Response format (typically `json`).
    *   `size`: Number of results to return.
*   **Reference:** [https://www.uniprot.org/help/api_queries](https://www.uniprot.org/help/api_queries)

## Authentication

The UniProt REST API endpoints used by Biomapper are generally public and do not require specific authentication keys. However, rate limits may apply.
