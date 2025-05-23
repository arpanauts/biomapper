# Specification: Qdrant Setup and PubChem Embedding Indexing

## 1. Introduction

This document details the requirements for setting up Qdrant and implementing the PubChem embedding indexing script. This is a foundational step for the RAG mapping capabilities.

## 2. Functional Requirements

### FR1: Qdrant Instance Setup
-   A Qdrant instance MUST be configurable and runnable, preferably via Docker/docker-compose.
-   The setup MUST allow for persistent storage of Qdrant data.
-   Configuration for Qdrant (host, port, API key if used) SHALL be manageable.

### FR2: Indexing Script (`scripts/rag/index_pubchem_embeddings.py`)
-   The script MUST be runnable from the command line.
-   It MUST accept parameters for:
    -   Path to the `pubchem_embeddings.tar.gz` archive.
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

### FR3: Data Handling
-   The script MUST correctly handle the format of the provided PubChem embeddings.
-   It MUST log progress, including the number of embeddings processed and any errors encountered.
-   It SHOULD be resumable or able to skip already indexed CIDs if run multiple times (e.g., by checking if a CID already exists before attempting to add, though Qdrant handles duplicate point IDs by overwriting).

### FR4: Configuration
-   Qdrant connection details (host, port, collection name) used by the indexing script should be configurable, potentially via CLI arguments or environment variables, aligning with `biomapper.config.settings` where applicable for client-side interactions.

## 3. Non-Functional Requirements

### NFR1: Performance
-   The indexing script should be reasonably performant, capable of indexing ~894k embeddings within a few hours.
-   Batch uploading to Qdrant MUST be used for efficiency.

### NFR2: Reliability
-   The script must handle potential errors during file processing or Qdrant communication gracefully (e.g., network issues, malformed files).

### NFR3: Usability
-   Clear instructions on how to set up Qdrant and run the indexing script MUST be provided.

## 4. Input Data
-   `pubchem_embeddings.tar.gz`: Archive containing individual files. Each file represents one compound, storing its embedding vector and PubChem CID.
    -   Vector dimensions: 384 (float)
    -   Model: `BAAI/bge-small-en-v1.5`

## 5. Out of Scope
-   Automatic download of the `pubchem_embeddings.tar.gz` file (assumed to be manually acquired).
-   Real-time or incremental indexing beyond the initial batch load.
