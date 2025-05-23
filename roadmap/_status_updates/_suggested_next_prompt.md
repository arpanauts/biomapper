# Suggested Next Prompt for Biomapper Development

## Context Brief
The PubChem embedding filtering is complete with 2.3M biologically relevant embeddings extracted from 89.4M total. Qdrant is deployed and indexing is in progress. The next critical step is implementing the PubChemRAGMappingClient to leverage these indexed embeddings for improved metabolite mapping.

## Initial Steps
1. First, review `/home/ubuntu/biomapper/CLAUDE.md` for overall project context and development approach
2. Check the status of Qdrant indexing by running:
   ```bash
   docker ps | grep qdrant
   curl -X GET "http://localhost:6333/collections/pubchem_bge_small_v1_5"
   ```
3. Review the recent status update at `/home/ubuntu/biomapper/roadmap/_status_updates/2025-05-23-pubchem-filtering-qdrant-indexing-complete.md`

## Work Priorities

### Priority 1: Implement PubChemRAGMappingClient
- Review the design document at `/home/ubuntu/biomapper/roadmap/2_inprogress/qdrant_pubchem_indexing/design.md`
- Implement the core RAG components:
  - FastEmbedEmbedder for generating query embeddings
  - QdrantVectorStore for semantic search
  - PubChemPromptManager for LLM prompting
  - LLMService for Claude integration
- Create the main PubChemRAGMappingClient class

### Priority 2: Integration and Testing
- Integrate PubChemRAGMappingClient into the FallbackOrchestrator pipeline
- Test with challenging metabolite names that fail with current methods
- Measure and document improvement in mapping success rates

## Key Files and References

### Implementation Files
- `/home/ubuntu/biomapper/scripts/rag/index_filtered_embeddings_to_qdrant.py` - Indexing script
- `/home/ubuntu/biomapper/roadmap/technical_notes/rag/rag_strategy.md` - RAG strategy document
- `/home/ubuntu/biomapper/roadmap/2_inprogress/qdrant_pubchem_indexing/` - Feature folder with all planning docs

### Data Files
- `/home/ubuntu/biomapper/data/bio_relevant_cids_expanded.txt` - 2.7M CID allowlist
- `/home/ubuntu/biomapper/data/filtered_embeddings/` - Filtered embeddings directory
- `/home/ubuntu/biomapper/data/pubchem_bio_embeddings_qdrant.pkl.gz` - Qdrant-ready embeddings

### Docker/Infrastructure
- `/home/ubuntu/biomapper/docker/qdrant/docker-compose.yml` - Qdrant configuration
- Qdrant API: http://localhost:6333
- Qdrant dashboard: http://localhost:6333/dashboard

## Workflow Integration

### Claude Integration Points
1. **Testing RAG Performance**: Create a detailed prompt for Claude to evaluate mapping results:
   ```
   "Analyze these metabolite mapping results from our RAG system:
   - Input metabolite names: [list]
   - RAG candidates with scores: [results]
   - Traditional method results: [baseline]
   Please evaluate the quality of matches and suggest threshold adjustments."
   ```

2. **Implementation Review**: Have Claude review the PubChemRAGMappingClient implementation for:
   - Proper integration with existing interfaces
   - Error handling completeness
   - Performance optimization opportunities

3. **Documentation Generation**: Use Claude to help create comprehensive documentation for the new RAG pipeline

### Suggested Development Flow
1. Start by checking Qdrant status and running test queries
2. Implement core components incrementally, testing each
3. Use Claude for code review and optimization suggestions
4. Document progress in implementation notes
5. Update task list as components are completed

## Success Metrics
- Qdrant contains all 2.3M filtered embeddings
- Query latency < 100ms for vector search
- Mapping success rate improvement from 0.2-0.5% to >10%
- Integration with FallbackOrchestrator working smoothly
- Comprehensive documentation and tests in place