# README: Qdrant Setup and PubChem Embedding Indexing

## 1. Feature Overview

This feature covers the setup of a Qdrant vector database instance and the development of a Python script to populate it with pre-computed PubChem compound embeddings. This is a critical prerequisite for the `PubChemRAGMappingClient` and the broader RAG-based mapping strategy.

This work is based on the idea outlined in `/home/ubuntu/biomapper/roadmap/0_backlog/qdrant_pubchem_indexing_idea.md` and supports the strategy in `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`.

## 2. Goals

-   Set up and configure a Qdrant instance (e.g., via Docker).
-   Develop a robust Python script to:
    -   Decompress the PubChem embeddings dataset (`pubchem_embeddings.tar.gz`).
    -   Parse individual embedding files (vector and PubChem CID).
    -   Batch load these embeddings into a specified Qdrant collection (e.g., `pubchem_bge_small_v1_5`).
-   Ensure the Qdrant collection is correctly configured for vector size (384 dimensions) and distance metric (Cosine).
-   Provide clear instructions on running the indexing script and managing the Qdrant instance.

## 3. Key Documents

-   **Specification:** [`spec.md`](./spec.md) - Detailed functional and non-functional requirements.
-   **Design:** [`design.md`](./design.md) - Technical architecture and script design.
-   **Overall RAG Strategy:** [`/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`](../../technical_notes/rag/rag_strategy.md)

## 4. Deliverables

-   Working Qdrant Docker setup (e.g., `docker-compose.yml`).
-   Python indexing script (`scripts/rag/index_pubchem_embeddings.py`).
-   Documentation on setup and usage.
