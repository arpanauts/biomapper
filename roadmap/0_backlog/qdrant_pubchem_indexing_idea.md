# Qdrant Setup and PubChem Embedding Indexing Idea

## Core Concept
Set up a Qdrant vector database instance and develop a script to populate it with the pre-computed PubChem compound embeddings. This is a prerequisite for the RAG-Based Mapping Feature.

## Goal/Benefit
- Provide the necessary vector search backend for the `PubChemRAGMappingClient`.
- Enable efficient semantic similarity searches over the entire PubChem embedding dataset.

## Initial Requirements/Context
- Qdrant to be run as a Docker container.
- PubChem Embeddings Dataset: `pubchem_embeddings.tar.gz` (approx. 894k compounds, `BAAI/bge-small-en-v1.5` model, 384 dimensions). Each file in the archive contains a vector and its PubChem CID.
- Indexing Script:
    - Python script to decompress the dataset.
    - Iterate through embedding files.
    - Read vectors and PubChem CIDs.
    - Use `QdrantVectorStore.add_documents` (or direct `qdrant-client` batch uploads) to load data into the designated Qdrant collection (e.g., `pubchem_bge_small_v1_5`).
- This is a one-time or infrequent batch operation.
- Related to the strategy in `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`.
