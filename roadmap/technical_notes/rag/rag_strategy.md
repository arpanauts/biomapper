# Biomapper: RAG-Based Mapping Strategy

## Introduction

This document outlines the strategy for implementing Retrieval-Augmented Generation (RAG) based mapping within the Biomapper framework. This approach is primarily intended as a fallback mechanism when traditional identifier-based or ontology-based mapping methods fail to yield results, particularly for entities like metabolites where naming conventions can be diverse and direct mappings are sparse.

The RAG strategy leverages semantic similarity search against pre-computed vector embeddings of large biomedical datasets (e.g., PubChem for compounds) and uses a Large Language Model (LLM) to interpret the retrieved candidates and determine the best match for a given query.

This strategy builds upon the existing RAG framework components found in `/home/ubuntu/biomapper/biomapper/mapping/rag/` and adapts them for specific use cases like PubChem compound mapping.

## Core Concepts

*   **Query Entity:** The input term to be mapped (e.g., a metabolite name from UKBB or Arivale).
*   **Embedding Model:** A sentence transformer model (e.g., `BAAI/bge-small-en-v1.5` via FastEmbed) used to convert text (query entities and dataset entries) into dense vector representations (embeddings).
*   **Vector Database:** A specialized database (e.g., Qdrant) optimized for storing, indexing, and querying large volumes of vector embeddings.
*   **Indexed Dataset:** A collection of pre-computed embeddings representing a large biomedical dataset (e.g., PubChem compound embeddings, where each vector is associated with a PubChem CID).
*   **Semantic Search:** The process of embedding a query entity and searching the vector database for entities with the most similar embeddings (closest vectors).
*   **Candidate Enrichment:** After retrieving top-k similar entities (e.g., PubChem CIDs) from the vector database, fetching detailed structured information for these candidates from their original source (e.g., using the PubChem PUG REST API).
*   **LLM Adjudication:** Presenting the original query entity and the enriched candidate information to an LLM, which is prompted to determine the best match and provide a confidence score and justification.
*   **`RAGMappingClient`:** A new `MappingClient` implementation that encapsulates this entire RAG workflow.

## RAG Workflow (PubChem Example)

The following steps describe the workflow for mapping an input metabolite name (query) to a PubChem CID using the RAG strategy:

1.  **Receive Query:** The `RAGMappingClient` receives a list of query entities (metabolite names) from the `FallbackOrchestrator` or `MappingExecutor`.
2.  **Embed Query:** For each query name, the client uses the `FastEmbedEmbedder` (configured with `BAAI/bge-small-en-v1.5`) to generate a query vector.
3.  **Semantic Search in Qdrant:**
    *   The query vector is used to search the pre-populated Qdrant collection containing PubChem compound embeddings.
    *   The `QdrantVectorStore` retrieves the top-k (e.g., k=3-5) most similar PubChem CIDs along with their similarity scores.
4.  **Candidate Enrichment (PubChem API):**
    *   For each candidate PubChem CID retrieved:
        *   The `PubChemAPIClient` is called to fetch detailed information (e.g., canonical name, synonyms, molecular formula, InChIKey, SMILES).
5.  **LLM Prompt Generation:**
    *   The `PubChemPromptManager` constructs a detailed prompt for the LLM.
    *   The prompt includes:
        *   The original query metabolite name.
        *   The enriched information for each of the top-k PubChem candidates.
        *   Clear instructions for the LLM to identify the best match (if any), provide a confidence level (e.g., HIGH, MEDIUM, LOW, NONE), and a justification.
        *   A request for the output to be in a structured JSON format.
6.  **LLM Adjudication:**
    *   The `LLMService` sends the prompt to the designated LLM (e.g., Claude).
    *   The LLM processes the information and returns a JSON response containing its assessment.
7.  **Parse LLM Response & Format Output:**
    *   The `RAGMappingClient` parses the LLM's JSON response.
    *   It extracts the best-matched PubChem CID, confidence, and other details.
    *   This information is formatted into the standard `MappingOutput` structure (`primary_ids`, `input_to_primary`, `errors`) expected by the `MappingExecutor`. The `confidence_score` and `mapping_path_details` (which can include LLM justification) fields in `EntityMapping` are populated.

## Key Components (Implementation Plan)

This strategy leverages and extends the existing RAG framework (`biomapper.mapping.rag`):

*   **`FastEmbedEmbedder(BaseEmbedder)`:**
    *   Implements `BaseEmbedder` using `fastembed` library.
    *   Model: `BAAI/bge-small-en-v1.5`.
    *   Responsibilities: Text embedding for queries.
*   **`QdrantVectorStore(BaseVectorStore)`:**
    *   Implements `BaseVectorStore` using the `qdrant-client` library.
    *   Configuration: Qdrant host, port, collection name (e.g., `pubchem_bge_small_v1_5`), vector parameters (size 384, distance: Cosine).
    *   Responsibilities: Storing (via separate indexing script) and retrieving PubChem CIDs based on vector similarity.
*   **`PubChemAPIClient`:**
    *   A new client for interacting with PubChem PUG REST/View APIs.
    *   Responsibilities: Fetching detailed compound information (names, formula, InChIKey, SMILES, etc.) for a given PubChem CID.
*   **`PubChemPromptManager(BasePromptManager)`:**
    *   Implements `BasePromptManager`.
    *   Responsibilities:
        *   Orchestrating calls to `PubChemAPIClient` to enrich candidate CIDs.
        *   Constructing the detailed JSON-based prompt for the LLM, including the query and enriched candidate data.
*   **`LLMService`:**
    *   Responsibilities:
        *   Sending prompts to the configured LLM (e.g., Claude via Anthropic API).
        *   Handling API key management (via `biomapper.config.settings`).
        *   Parsing the LLM's JSON response.
*   **`PubChemRAGMappingClient(BaseRAGMapper, MappingClient)`:**
    *   The concrete implementation of the RAG mapping client for PubChem.
    *   Inherits from `BaseRAGMapper` (for the core RAG workflow) and `MappingClient` (to integrate with `MappingExecutor`).
    *   `__init__`: Initializes and injects `FastEmbedEmbedder`, `QdrantVectorStore`, `PubChemPromptManager`, and `LLMService`.
    *   `_generate_matches`: Implements the abstract method from `BaseRAGMapper` by calling the `LLMService`.
    *   `map_identifiers`: Adapts `BaseRAGMapper.map_query` results to the `MappingOutput` format.
    *   `get_client_info`: Provides metadata about the client.
    *   `reverse_map_identifiers`: Raises `NotImplementedError` as this client maps *to* PubChem.

## Indexing Process (Separate Task)

*   **Dataset:** Pre-computed PubChem embeddings (`pubchem_embeddings.tar.gz`, ~894k compounds, `BAAI/bge-small-en-v1.5` model, 384 dimensions). Each embedding file contains the vector and associated PubChem CID.
*   **Indexing Script:** A dedicated Python script will be responsible for:
    1.  Decompressing the dataset.
    2.  Iterating through each embedding file.
    3.  Reading the vector and PubChem CID.
    4.  Using `QdrantVectorStore.add_documents` (or direct `qdrant-client` batch uploads) to populate the Qdrant collection.
    *   This is a one-time (or infrequent) batch operation.
*   **Qdrant Setup:** Qdrant will be run as a Docker container.

## Integration with `FallbackOrchestrator`

*   The `PubChemRAGMappingClient` will be registered in `metamapper.db` like other mapping clients.
*   Its `input_ontology_type` might be `METABOLITE_NAME` (or a generic `TEXT_QUERY`) and `output_ontology_type` would be `PUBCHEM_CID`.
*   The `FallbackOrchestrator` will invoke it when other, more direct mapping strategies for metabolites have been exhausted.

## Configuration

*   Qdrant server details (host, port).
*   PubChem RAG collection name.
*   LLM API endpoint and key.
*   Embedding model name (if configurable beyond default).
*   All managed via `biomapper.config.settings`.

## Benefits

*   **Improved Coverage for Ambiguous Entities:** Can find matches for metabolite names that lack standard identifiers or have many synonyms.
*   **Leverages Semantic Understanding:** Goes beyond exact string matching by using semantic meaning captured in embeddings.
*   **LLM for Disambiguation:** Uses the reasoning power of LLMs to interpret complex candidate information and make informed mapping decisions.
*   **Extensible Framework:** The base RAG components can be reused for other RAG-based mapping tasks (e.g., different datasets, different entity types).

## Future Considerations

*   **Multi-Collection RAG:** Supporting RAG against multiple vector collections (e.g., ChEMBL, DrugBank embeddings) within a single client or via multiple RAG clients.
*   **RAG for Reverse Mapping:** If a target entity (e.g., from Arivale) has rich descriptive text, embedding that text and searching against a UKBB RAG collection could be a reverse mapping strategy.
*   **LLM Fine-tuning/Prompt Engineering:** Iteratively improving LLM prompts and potentially exploring fine-tuned models for better domain-specific performance.
*   **Confidence Calibration:** Developing more robust methods for calibrating confidence scores from the LLM.
*   **Cost/Latency Optimization:** Monitoring and optimizing LLM token usage and overall RAG pipeline latency.