# Specification: Qdrant Setup and PubChem Embedding Indexing

## 1. Introduction

This document details the requirements for setting up Qdrant and implementing the PubChem embedding indexing script, including a critical preprocessing step to filter for biologically relevant compounds. This is a foundational step for the RAG mapping capabilities and directly supports the goal of improving mapping success rates as outlined in the project's priorities.

## 2. Functional Requirements

### FR1: PubChem Embeddings Filtering
-   Two preprocessing scripts MUST be developed:
    1. `scripts/rag/create_bio_relevant_cid_allowlist.py`: Creates an allowlist of biologically relevant PubChem CIDs
    2. `scripts/rag/filter_pubchem_embeddings.py`: Filters the compressed embeddings using the allowlist

-   The allowlist creation script MUST:
    -   Download and process data from multiple biological databases (HMDB, ChEBI, DrugBank)
    -   Extract and consolidate PubChem CIDs from these sources
    -   Generate a simple text file of unique, biologically relevant CIDs
    -   Handle large database files memory-efficiently
    -   Generate a report on the CID sources and distribution

-   The filtering script MUST accept parameters for:
    -   Path to the compressed chunks in `/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks/`
    -   Path to the CID allowlist file
    -   Output directory for filtered embeddings
    -   Decompression options as required by the DECOMPRESSION_GUIDE.md

-   The filtering script SHALL:
    -   Process compressed chunks according to the decompression guide
    -   Only extract embeddings for CIDs present in the allowlist
    -   Avoid decompressing the entire dataset (700GB) to conserve disk space
    -   Generate a report showing:
        -   Number of embeddings retained vs. filtered out
        -   Estimated size reduction
        -   Processing statistics

-   Both scripts MUST be optimized for memory efficiency to handle large datasets without excessive RAM requirements.

### FR2: Qdrant Instance Setup
-   A Qdrant instance MUST be configurable and runnable, preferably via Docker/docker-compose.
-   The setup MUST allow for persistent storage of Qdrant data.
-   Configuration for Qdrant (host, port, API key if used) SHALL be manageable.

### FR3: Indexing Script (`scripts/rag/index_pubchem_embeddings.py`)
-   The script MUST be runnable from the command line.
-   It MUST accept parameters for:
    -   Path to the filtered PubChem embeddings archive produced by the filtering script.
    -   Qdrant host and port.
    -   Qdrant collection name (default: `pubchem_bge_small_v1_5`).
    -   Batch size for uploads.
-   The script SHALL decompress the input archive.
-   It SHALL iterate through individual embedding files within the archive.
    -   Each file is assumed to contain a vector and its associated PubChem CID.
-   It SHALL parse these files to extract the vector (384 dimensions, float) and PubChem CID (string).
-   It SHALL connect to the Qdrant instance and create the specified collection if it doesn't exist.
    -   The collection MUST be configured for vectors of size 384 and Cosine distance metric.
    -   Payload indexing for PubChem CID should be enabled for filtering/retrieval.
-   It SHALL upload the vectors and their PubChem CIDs (as payload) to Qdrant in batches.

### FR4: Data Handling
-   The script MUST correctly handle the format of the provided filtered PubChem embeddings.
-   It MUST log progress, including the number of embeddings processed and any errors encountered.
-   It SHOULD be resumable or able to skip already indexed CIDs if run multiple times (e.g., by checking if a CID already exists before attempting to add, though Qdrant handles duplicate point IDs by overwriting).

### FR5: Configuration
-   Qdrant connection details (host, port, collection name) used by the indexing script should be configurable, potentially via CLI arguments or environment variables, aligning with `biomapper.config.settings` where applicable for client-side interactions.
-   Filter criteria for the preprocessing script should be configurable via command-line arguments or a separate configuration file.

## 3. Non-Functional Requirements

### NFR1: Performance
-   The indexing script should be reasonably performant, capable of indexing ~894k embeddings within a few hours.
-   Batch uploading to Qdrant MUST be used for efficiency.

### NFR2: Reliability
-   The script must handle potential errors during file processing or Qdrant communication gracefully (e.g., network issues, malformed files).

### NFR3: Usability
-   Clear instructions on how to set up Qdrant and run the indexing script MUST be provided.

## 4. Input Data
-   **Initial Input:** `pubchem_embeddings.tar.gz`: Archive containing individual files for all PubChem compounds. Each file represents one compound, storing its embedding vector and PubChem CID.
    -   Full size: ~50GB compressed, ~700GB decompressed
    -   Compound count: ~894k compounds
    -   Vector dimensions: 384 (float)
    -   Model: `BAAI/bge-small-en-v1.5`

-   **Filtered Input:** Output from the filtering process targeting biologically relevant compounds.
    -   Expected size: ~5-8GB compressed, ~70-100GB decompressed
    -   Expected compound count: ~100k-150k compounds
    -   Primarily compounds with HMDB/ChEBI cross-references, bioassay activity, or pharmacological relevance

## 5. Out of Scope
-   Automatic download of the `pubchem_embeddings.tar.gz` file (assumed to be manually acquired).
-   Real-time or incremental indexing beyond the initial batch load.
-   Exhaustive cross-referencing with all possible biological databases (focus will be on the most relevant ones).
-   Custom embedding generation for compounds not in the original PubChem embeddings dataset.
