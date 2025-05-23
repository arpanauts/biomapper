# Biomapper Status Update: RAG Strategy and PubChem Filtering Implementation

## 1. Recent Accomplishments

- Created a comprehensive RAG (Retrieval-Augmented Generation) strategy document in `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md` outlining the approach for RAG-based mapping, particularly for metabolites using PubChem.
- Designed a robust implementation plan for the `PubChemRAGMappingClient` and its dependencies, including `FastEmbedEmbedder`, `QdrantVectorStore`, and associated components.
- Developed a practical and efficient approach for filtering PubChem embeddings to focus on biologically relevant compounds (primarily from HMDB, ChEBI, and DrugBank).
- Updated roadmap stages in accordance with `/home/ubuntu/biomapper/roadmap/HOW_TO_UPDATE_ROADMAP_STAGES.md`, creating detailed planning documents in:
  - `/home/ubuntu/biomapper/roadmap/1_planning/rag_mapping_feature/`
  - `/home/ubuntu/biomapper/roadmap/1_planning/qdrant_pubchem_indexing/`
- Incorporated Claude's updates on `TranslatorNameResolverClient`, `UMLSClient`, and new metabolite mapping scripts into the roadmap's completed features.

## 2. Current Project State

- The core RAG strategy is now well-defined and documented, providing a clear path for implementation.
- The approach for handling the large PubChem embeddings dataset (~50GB compressed, ~700GB decompressed) has been refined to use a biologically-focused subset, improving both performance and relevance.
- Metabolite mapping capabilities are advancing, with both direct mapping scripts and plans for a RAG-based fallback mechanism.
- Current mapping success rates remain low (~0.2-0.5%), which the RAG strategy directly aims to improve.
- The development is proceeding according to the iterative mapping strategy outlined in `/home/ubuntu/biomapper/docs/draft/iterative_mapping_strategy.md` and following the dual-agent development approach.

## 3. Technical Context

- **Embedding Model Decision:** Selected `BAAI/bge-small-en-v1.5` via FastEmbed for generating embeddings, balancing performance and quality with a 384-dimension vector space.
- **Vector Database Selection:** Chosen Qdrant over alternatives due to its performance with large vector collections and support for cosine similarity search.
- **Statistical Significance for Similarity:** Incorporated statistical significance testing for cosine similarities based on vector dimensionality (n=384), using:
  ```python
  from scipy.special import betaincinv, betainc
  p_val = lambda n, x : 1 - betainc(1/2, (n-1)/2, x)
  min_effect_size = lambda n, alpha : betaincinv(1/2, (n-1)/2, 1-alpha)
  ```
- **Efficient PubChem Filtering:** Developed an approach using pre-existing biological databases to create an allowlist of relevant PubChem CIDs, avoiding the need for extensive API calls.
- **LLM Integration Pattern:** Designed a JSON-structured prompting approach for LLM (Claude) to adjudicate and provide confidence scores for candidate matches.

## 4. Next Steps

- Implement the `create_bio_relevant_cid_allowlist.py` script to generate the list of biologically relevant PubChem CIDs from HMDB, ChEBI, and DrugBank.
- Create the `filter_pubchem_embeddings.py` script to process the compressed chunks in `/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks/` according to the decompression guide.
- Develop the core RAG components: `FastEmbedEmbedder`, `QdrantVectorStore`, `PubChemPromptManager`, and `LLMService`.
- Integrate these components into the `PubChemRAGMappingClient` that implements both the `BaseRAGMapper` and `MappingClient` interfaces.
- Set up a Qdrant instance via Docker and populate it with the filtered PubChem embeddings.
- Test the RAG-based mapping approach with challenging metabolite mappings to validate improvement over the current success rates.

## 5. Open Questions & Considerations

- **Exact Format of PubChem Embeddings:** Need to review the decompression guide at `/procedure/data/local_data/PUBCHEM_FASTEMBED/DECOMPRESSION_GUIDE.md` to understand the specific structure and format of the compressed chunks.
- **Resource Requirements:** Need to determine exact disk space and memory requirements for processing the embeddings and running Qdrant.
- **Statistical Threshold Tuning:** Further investigation needed to determine optimal significance levels (alpha) for cosine similarity filtering in the vector search.
- **Integration with `FallbackOrchestrator`:** Need to define the exact conditions when the RAG-based approach should be invoked in the fallback chain.
- **Evaluation Metrics:** Need to establish concrete metrics beyond simple success rate to measure the quality of RAG-based mappings (e.g., confidence distribution, precision/recall).
