# RAG-Based Mapping Feature Idea

## Core Concept
Implement a Retrieval-Augmented Generation (RAG) based mapping client as a fallback mechanism, initially targeting PubChem compound mapping for metabolites. This client will leverage semantic search over pre-computed PubChem embeddings and use an LLM for final adjudication.

## Goal/Benefit
- Improve mapping coverage for ambiguous metabolite names or entities lacking direct identifiers.
- Provide more robust mapping by considering semantic similarity and contextual information via LLM reasoning.
- Establish an extensible RAG framework for potential future use with other datasets or entity types.

## Initial Requirements/Context
- Utilize the existing RAG framework in `/home/ubuntu/biomapper/biomapper/mapping/rag/`.
- Vector Database: Qdrant.
- Embedding Model: `BAAI/bge-small-en-v1.5` via FastEmbed.
- Target Dataset for RAG: Pre-computed PubChem embeddings (approx. 894k compounds).
- LLM: Claude (or similar, configurable).
- Key components to develop/adapt:
    - `FastEmbedEmbedder`
    - `QdrantVectorStore`
    - `PubChemAPIClient` (for candidate enrichment)
    - `PubChemPromptManager`
    - `LLMService`
    - `PubChemRAGMappingClient`
- Detailed strategy outlined in `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`.
