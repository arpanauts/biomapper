# PubChemRAGMappingClient - Planning Document

## Goal

The goal of this feature is to implement a RAG (Retrieval-Augmented Generation) based mapping client that leverages semantic search capabilities to significantly improve metabolite identifier mapping success rates. By utilizing pre-computed embeddings from PubChem stored in a Qdrant vector database, this client will enable semantic similarity search for metabolite names and synonyms, addressing the current low success rates (0.2-0.5%) of traditional exact-match based mapping approaches.

## Requirements

### Functional Requirements

1. **Vector Search Integration**
   - Query the Qdrant vector database containing 2.3 million biologically relevant PubChem embeddings
   - Use semantic similarity search to find PubChem CIDs for input metabolite names/synonyms
   - Support configurable similarity thresholds and result limits

2. **MappingClient Interface Compliance**
   - Implement the `biomapper.mapping.base_client.MappingClient` interface
   - Provide standard mapping methods compatible with the existing ecosystem
   - Support batch processing of multiple metabolite queries

3. **Embedding Generation**
   - Generate embeddings for input metabolite names using the same model (BAAI/bge-small-en-v1.5)
   - Ensure consistency with the pre-computed PubChem embeddings (384 dimensions)

4. **Result Processing**
   - Return PubChem CIDs with confidence scores based on similarity
   - Support metadata retrieval from Qdrant payloads
   - Implement result ranking and filtering mechanisms

### Technical Requirements

1. **Qdrant Integration**
   - Connect to Qdrant instance (Docker deployment on ports 6333/6334)
   - Access the `pubchem_bge_small_v1_5` collection
   - Handle connection failures gracefully with appropriate retry logic

2. **Performance**
   - Optimize for batch query processing
   - Implement caching mechanisms for frequently queried metabolites
   - Target sub-second response times for individual queries

3. **Integration Points**
   - Seamless integration with `FallbackOrchestrator`
   - Compatibility with existing mapping pipeline infrastructure
   - Support for configuration through standard Biomapper config system

### Non-Functional Requirements

1. **Reliability**
   - Graceful degradation when Qdrant is unavailable
   - Comprehensive error handling and logging
   - Unit test coverage > 80%

2. **Maintainability**
   - Clear separation of concerns (embedding generation, vector search, result processing)
   - Well-documented code with type hints
   - Follow existing Biomapper coding standards

3. **Observability**
   - Integration with existing monitoring/metrics infrastructure
   - Detailed logging for debugging and performance analysis
   - Support for tracing through the mapping pipeline

## Audience

This feature is intended for:

1. **Biomapper Users**: Researchers and bioinformaticians who need to map metabolite identifiers with higher success rates
2. **Biomapper Developers**: Team members who will maintain and extend the RAG-based mapping capabilities
3. **System Integrators**: Those who need to deploy and configure the Qdrant infrastructure alongside Biomapper

## Questions for Requirements Clarification

1. **Similarity Threshold Strategy**
   - Should the similarity threshold be configurable per query or globally?
   i think per query (or per qdrant collection, if that makes sense). i don't think it should be global
   - What should be the default threshold value based on initial testing?
   for this pubchem rag client, i think it should be 0.01
   - Should we implement adaptive thresholding based on result quality?
   not at this time

2. **Result Ranking and Selection**
   - When multiple PubChem CIDs have similar scores, what additional criteria should be used for ranking?
   we want to keep all those under the threshold, as those will be handed off to the llm for final selection
   - Should we limit results to top-N candidates or use a threshold-based cutoff?
   in this case, we want to use a threshold-based cutoff, but the underlying module should have a method for top-N candidates in addition to threshold-based cutoff
   - How should we handle cases where no results meet the minimum similarity threshold?
   we should return an empty list, but provide logging to explain why, including the top N results and their scores.

3. **Base RAG Interface Design**
   - Should we create a generic `BaseRAGMapper` class that this client extends?
   i think we should
   - What common functionality should be abstracted to the base class?
   i think we should abstract the embedding generation and vector search functionality to the base class, and leave the result processing to the specific client (in this case pubchem rag client)
   - How should we structure the interface to support future RAG-based mapping clients?
   i think we should have a base class that defines the interface for the mapping client, and then have specific clients that implement this interface

4. **Caching Strategy**
   - Should we implement in-memory caching, persistent caching, or both?
   i think we should implement in-memory caching for now, and we will defer persistent caching to a future iteration
   - What should be the cache invalidation strategy?
   i think we should invalidate the cache when the model is reloaded, and when the qdrant collection is reloaded
   - Should cache be shared across multiple client instances?
   i think we should share the cache across multiple client instances

5. **Fallback Behavior**
   - When integrated with FallbackOrchestrator, what should be the client's priority order?
   for testing, i think we should try this client first, and then try the exact match clients. in production however, i think we should try the exact match clients first, and then try this client
   - Should this client be tried before or after traditional exact-match clients?
   i think we should try this client after the exact match clients
   - How should partial matches be handled in the fallback chain?
   i think we should handle partial matches in the fallback chain the same way we handle partial matches in the exact match clients

6. **Metadata Enhancement**
   - Should the client fetch additional metadata from PubChem API for returned CIDs?
   in the qdrant collection, the only metadata is the pubchem id itself. additional metadata will need to be fetched from the pubchem api. this is to support the llm in making the final selection, and more broadly, provides annotation functionality to the project as a whole. in fact, annotation is the primary reason for this feature in the first place. it will need to be as customizable as possible, and will need to be extensible to other sources of metadata in the future
   - What metadata fields are most valuable to include in the mapping results?
   we'll need to see what's available in the pubchem api, but i think we should include the following: anything that would provide semantic value to biological function, including kegg pathways and descriptions
   - How should we handle cases where vector search succeeds but metadata fetch fails?
   i think we should return the pubchem id and the metadata that we were able to fetch, and log the error

7. **Performance Benchmarks**
   - What are the acceptable latency targets for different batch sizes?
   i think we should target sub-second response times for individual queries
   - Should we implement query batching strategies for optimal Qdrant utilization?
   i think we should implement query batching strategies for optimal Qdrant utilization
   - What monitoring metrics are most critical for production deployment?
   i think we should monitor the following: query latency, number of queries per second, number of queries in the queue, number of queries in the cache, number of queries that failed, number of queries that were retried, number of queries that were cached, number of queries that were batched, number of queries that were parallelized, number of queries that were serialized, number of queries that were cached, number of queries that were batched, number of queries that were parallelized, number of queries that were serialized