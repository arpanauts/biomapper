# Specification: RAG-Based Mapping Feature

## 1. Introduction

This document details the functional and non-functional requirements for the RAG-Based Mapping Feature, focusing on the `PubChemRAGMappingClient`. Refer to the main RAG strategy document (`/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`) for overarching concepts.

## 2. Functional Requirements

### FR1: `PubChemRAGMappingClient` Implementation
-   The client MUST implement the `biomapper.mapping.base.MappingClient` interface.
-   The client MUST inherit from `biomapper.mapping.rag.base_rag.BaseRAGMapper`.
-   The client SHALL accept a list of metabolite names as input.
-   The client SHALL return `MappingOutput` containing mappings to PubChem CIDs.

### FR2: Embedding Generation
-   The `FastEmbedEmbedder` SHALL use the `fastembed` library with the `BAAI/bge-small-en-v1.5` model to generate query embeddings.

### FR3: Vector Search
-   The `QdrantVectorStore` SHALL connect to a configured Qdrant instance.
-   It SHALL search a specified collection (e.g., `pubchem_bge_small_v1_5`) using query embeddings.
-   It SHALL retrieve the top-k most similar PubChem CIDs and their similarity scores. (k is configurable, default 3-5).
-   It SHALL support filtering results by a minimum cosine similarity threshold.
-   It SHALL implement statistical significance testing for cosine similarities based on embedding dimensionality (n=384 for BAAI/bge-small-en-v1.5).
-   It SHALL provide options to use either a fixed threshold or a statistically derived threshold based on a specified alpha level.

### FR4: Candidate Enrichment
-   The `PubChemAPIClient` SHALL fetch detailed information for candidate PubChem CIDs from the PubChem PUG REST/View APIs.
-   Information to fetch SHALL include: canonical name, synonyms, molecular formula, InChIKey, SMILES.

### FR5: LLM Prompting and Adjudication
-   The `PubChemPromptManager` SHALL construct a JSON-based prompt for the LLM.
-   The prompt MUST include the original query and enriched information for all top-k candidates.
-   The `LLMService` SHALL send the prompt to the configured LLM (e.g., Claude).
-   The LLM's response (expected in structured JSON) SHALL be parsed to identify the best match, confidence (HIGH, MEDIUM, LOW, NONE), and justification.

### FR6: Configuration
-   All external service details (Qdrant, LLM API key, embedding model name if varied) MUST be configurable via `biomapper.config.settings`.

### FR7: Error Handling
-   The client and its sub-components MUST implement robust error handling for API failures, network issues, and unexpected responses.
-   Errors should be logged appropriately and propagated as `MappingError` objects within the `MappingOutput`.

### FR8: Integration
-   The `PubChemRAGMappingClient` SHALL be registrable and usable within the `FallbackOrchestrator`.

## 3. Non-Functional Requirements

### NFR1: Performance
-   The RAG mapping process for a single query should ideally complete within a reasonable timeframe (e.g., target < 10-15 seconds, subject to LLM and API latencies). Batch processing performance should be considered.

### NFR2: Accuracy
-   The system should aim for high precision in its mappings, with LLM confidence scores reflecting the likelihood of a correct match. The definition of "high precision" will be refined during testing.

### NFR3: Scalability
-   The Qdrant setup should be capable of handling the full PubChem embedding dataset (approx. 894k vectors).
-   The client should handle batch inputs efficiently.

### NFR4: Maintainability
-   Code MUST follow Biomapper project coding standards.
-   Components should be modular and well-documented.
-   Unit tests MUST be provided for all new components.

## 4. Out of Scope for this Feature (Initial MVP)

-   Real-time indexing of new data into Qdrant (indexing is a separate batch process).
-   RAG mapping for entity types other than PubChem compounds.
-   Advanced LLM fine-tuning beyond prompt engineering.
-   User interface for RAG configuration or result review (client is for programmatic use).
