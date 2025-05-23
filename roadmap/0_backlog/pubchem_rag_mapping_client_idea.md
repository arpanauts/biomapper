# Feature Idea: PubChemRAGMappingClient Implementation

**1. Core Concept / Problem to Solve:**

The current traditional mapping methods for metabolites in Biomapper show low success rates (0.2-0.5%). To address this, a Retrieval Augmented Generation (RAG)-based mapping client is needed. This client will leverage the recently created Qdrant vector database of 2.3 million biologically relevant PubChem embeddings to find semantically similar PubChem CIDs for given metabolite names or synonyms.

**2. Intended Goal / Benefit:**

*   Significantly improve the success rate of metabolite mapping.
*   Provide more robust mapping for ambiguous or non-standard metabolite names.
*   Enable semantic similarity searches as a fallback or complementary mapping strategy.
*   Integrate seamlessly into the existing `FallbackOrchestrator` pipeline.

**3. Initial Requirements / Context:**

*   The client should be named `PubChemRAGMappingClient`.
*   It must implement the `biomapper.mapping.base_client.MappingClient` interface.
*   It should likely also implement or utilize a base RAG mapping interface (e.g., `biomapper.mapping.rag.BaseRAGMapper` if such an interface exists or needs to be defined).
*   It will query the Qdrant collection named `pubchem_bge_small_v1_5` (384-dimensional vectors, Cosine distance).
*   The Qdrant instance is accessible via Docker (ports 6333/6334).
*   Input to the client will be metabolite names/strings.
*   Output should be mapped PubChem CIDs (or a structure compatible with the `MappingClient` interface).
*   The client needs to be added to the `FallbackOrchestrator`'s sequence of mapping strategies.
*   Consider how similarity thresholds will be configured and applied.
*   Refer to the Qdrant setup and indexing details in `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-23-pubchem-filtering-qdrant-indexing-complete.md` and the indexing script `/home/ubuntu/biomapper/scripts/rag/index_filtered_embeddings_to_qdrant.py`.

**4. Success Criteria (High-Level):**

*   The `PubChemRAGMappingClient` is implemented and passes unit tests.
*   The client successfully retrieves relevant PubChem CIDs from Qdrant for test metabolite names.
*   The client is integrated into the `FallbackOrchestrator`.
*   Initial tests show an improvement in metabolite mapping coverage compared to existing methods alone.
