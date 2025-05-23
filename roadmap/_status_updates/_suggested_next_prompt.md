# Suggested Next Work Session: Implementing the RAG-Based Mapping Solution

## Context Brief
We've developed a comprehensive RAG strategy document and detailed design for filtering PubChem embeddings to create a biologically relevant subset. We've also completed the implementation of `TranslatorNameResolverClient`, `UMLSClient`, and metabolite mapping scripts. Now we need to implement the RAG-based mapping components and the PubChem filtering to improve the current low mapping success rates (0.2-0.5%).

## Initial Steps
First, review `/home/ubuntu/biomapper/CLAUDE.md` to get up to speed on the overall project context, roadmap structure, and workflow procedures. Then review our recent progress in the latest status update to understand what has been accomplished and what remains to be done.

## Key References
- Latest status update: `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-23-rag-strategy-pubchem-filtering.md`
- RAG strategy document: `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md`
- RAG mapping feature design: `/home/ubuntu/biomapper/roadmap/1_planning/rag_mapping_feature/design.md`
- PubChem indexing design: `/home/ubuntu/biomapper/roadmap/1_planning/qdrant_pubchem_indexing/design.md`
- Existing RAG framework: `/home/ubuntu/biomapper/biomapper/mapping/rag/base_rag.py`
- Base mapping client interface: `/home/ubuntu/biomapper/biomapper/mapping/base.py`

## Work Priorities
1. Implement the PubChem embedding filtering solution
   - Create the `create_bio_relevant_cid_allowlist.py` script to extract relevant PubChem CIDs from HMDB, ChEBI, and DrugBank
   - Review the decompression guide at `/procedure/data/local_data/PUBCHEM_FASTEMBED/DECOMPRESSION_GUIDE.md`
   - Implement `filter_pubchem_embeddings.py` to extract only biologically relevant embeddings from the compressed chunks
   - Test with a small subset before scaling to the full dataset

2. Set up and configure the Qdrant vector database
   - Create a Docker setup for Qdrant
   - Implement the indexing script to populate Qdrant with the filtered embeddings
   - Ensure proper configuration for vector dimensionality (384) and cosine similarity

3. Implement the core RAG components
   - Develop `FastEmbedEmbedder` to generate embeddings using the BAAI/bge-small-en-v1.5 model
   - Create `QdrantVectorStore` with support for cosine similarity thresholds and statistical significance testing
   - Implement `PubChemAPIClient` for fetching detailed compound information
   - Develop `PubChemPromptManager` to format LLM prompts with relevant context
   - Create `LLMService` for interactions with Claude or other LLMs

4. Integrate components into the `PubChemRAGMappingClient`
   - Implement the client following both `BaseRAGMapper` and `MappingClient` interfaces
   - Develop the mapping logic and confidence scoring
   - Create comprehensive unit tests
   - Integrate with the `FallbackOrchestrator`

5. Validate and measure improvement
   - Test with challenging metabolite mappings
   - Compare success rates to the current baseline (0.2-0.5%)
   - Analyze and document findings

## Workflow Integration
After reviewing the RAG strategy and implementation plans, incorporate this approach into your workflow step-by-step. First, focus on creating the biological relevance allowlist and filtering the embeddings, as this is a prerequisite for the rest of the implementation. You can have Claude assist with developing the database parsing logic for extracting PubChem CIDs from HMDB, ChEBI, and DrugBank.

Once the filtered embeddings are available, work on setting up Qdrant and implementing the core RAG components. Claude can help with implementing the individual components like `FastEmbedEmbedder` and `QdrantVectorStore` while you focus on integration and testing. This modular approach allows for parallel development and iterative testing.

For validating the improvement in mapping success rates, create a test set of challenging metabolite names that currently fail to map correctly. This will provide concrete evidence of the RAG approach's effectiveness in addressing the critical low mapping success rate issue.
