# README: RAG-Based Mapping Feature

## 1. Feature Overview

This feature introduces a Retrieval-Augmented Generation (RAG) based mapping client to the Biomapper project. It is designed as a fallback mechanism, primarily for metabolite mapping (initially targeting PubChem), when traditional methods are insufficient. The client will use semantic search over pre-computed PubChem embeddings stored in Qdrant and leverage an LLM (e.g., Claude) for final candidate adjudication.

This work is based on the idea outlined in `/home/ubuntu/biomapper/roadmap/0_backlog/rag_mapping_feature_idea.md` and the detailed strategy in `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`.

## 2. Goals

-   Implement the `PubChemRAGMappingClient` and its core dependencies:
    -   `FastEmbedEmbedder`
    -   `QdrantVectorStore`
    -   `PubChemAPIClient`
    -   `PubChemPromptManager`
    -   `LLMService`
-   Integrate this client into the Biomapper `FallbackOrchestrator`.
-   Improve mapping success rates for ambiguous metabolite names.
-   Establish an extensible RAG framework.

## 3. Key Documents

-   **Specification:** `rag_mapping_feature_spec.md` (sibling file) - Detailed functional and non-functional requirements.
-   **Design:** `rag_mapping_feature_design.md` (sibling file) - Technical architecture and component design.
-   **Overall RAG Strategy:** [`/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`](../technical_notes/rag/rag_strategy.md)

## 4. Prerequisites

-   Completion of the "Qdrant Setup and PubChem Embedding Indexing" feature (see `/home/ubuntu/biomapper/roadmap/1_planning/qdrant_pubchem_indexing_README.md` or its folder).
-   Access to a running Qdrant instance populated with PubChem embeddings.
-   LLM API (e.g., Anthropic Claude) key and configuration.
