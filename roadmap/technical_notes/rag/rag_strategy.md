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

## Indexing Process (Completed May 23, 2025)

### Dataset Statistics
*   **Original Dataset:** Pre-computed PubChem embeddings located at `/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks/`
    - 346 tar.gz files containing JSON files
    - Each JSON file contains 100 embeddings (CID -> 384-dimensional vector)
    - Model: `BAAI/bge-small-en-v1.5`
    - **Total embeddings: 89,366,728** (~89.4 million, not 894k as originally estimated)
    - Coverage: 51.68% of PubChem's 173M CID range

### Filtering Process Results
*   **Filtering Script:** `filter_pubchem_embeddings.py` completed successfully
*   **Processing Statistics:**
    - Total embeddings scanned: 89,366,728
    - Total embeddings retained: **2,295,544**
    - Retention rate: **2.57%**
    - Chunks processed: 346 (100% completion)
    - JSON files processed: 893,983
    - Output: 337 filtered pickle files in `/home/ubuntu/biomapper/data/filtered_embeddings/`

### Qdrant Indexing
*   **Qdrant Setup:** Running as Docker container on ports 6333 (HTTP) and 6334 (gRPC)
*   **Collection Configuration:**
    - Name: `pubchem_bge_small_v1_5`
    - Vector size: 384 dimensions
    - Distance metric: Cosine similarity
    - Optimized settings: HNSW indexing, 1000-5000 batch size
*   **Indexing Status:** In progress as of May 23, 2025
    - Script: `index_filtered_embeddings_to_qdrant.py`
    - Processing 2.3M embeddings in batches
    - Estimated completion: Several hours

## PubChem Filtering Strategy

### Rationale
The complete PubChem embeddings dataset contains ~50GB compressed (~700GB decompressed) data representing millions of compounds, many of which are not biologically relevant (e.g., industrial chemicals, theoretical compounds). To improve both performance and relevance, we will filter the embeddings to focus only on biologically relevant compounds using established biomedical databases.

### Data Sources (as of May 23, 2025)

1. **HMDB (Human Metabolome Database)**
   - **Source**: https://hmdb.ca/downloads
   - **File**: "All Metabolites" (XML or SDF format)
   - **Content**: Comprehensive human metabolome data including endogenous metabolites, drugs, food compounds
   - **PubChem CIDs Found**: 103,682
   - **Access**: Free for academic use, registration required for commercial use

2. **ChEBI (Chemical Entities of Biological Interest)**
   - **Source**: https://www.ebi.ac.uk/chebi/downloadsForward.do
   - **FTP**: https://ftp.ebi.ac.uk/pub/databases/chebi/
   - **File**: `ChEBI_complete_3star.sdf.gz`
   - **Content**: Comprehensive chemical entities with biological relevance
   - **PubChem CIDs Found**: 97,163
   - **Access**: Freely available

3. **UniChem Cross-References**
   - **Source**: https://www.ebi.ac.uk/unichem/
   - **Download**: https://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/table_dumps/
   - **File**: `reference.tsv.gz` (downloaded May 23, 2025)
   - **Content**: Cross-references between chemical databases
   - **Processing Results** (completed May 23, 2025):
     - Total lines processed: 292,870,858
     - Unique biological UCIs identified: 3,201,422
     - PubChem CIDs extracted: 2,639,838
     - New CIDs added to allowlist: 2,511,498
   - **Key Contributors**:
     - ChEMBL (95,917,166 lines) - 2,378,537 unique PubChem CIDs
     - HMDB (217,480 lines) - 103,714 PubChem CIDs
     - SwissLipids (503,080 lines) - 97,282 PubChem CIDs
     - EPA CompTox (293,766 lines) - 69,716 PubChem CIDs
     - DrugBank (9,238 lines) - 4,949 PubChem CIDs
     - KEGG Ligand (17,080 lines) - 7,595 PubChem CIDs
     - Recon (3,221 lines) - 2,217 PubChem CIDs
     - FDA/USP SRS (86,608 lines) - 8,238 PubChem CIDs
     - Rhea (8,964 lines) - 7,270 PubChem CIDs
     - Guide to Pharmacology (8,152 lines) - 5,636 PubChem CIDs
     - PharmGKB (3,257 lines) - 2,650 PubChem CIDs
   - **Access**: Freely available, bulk download supported

4. **Coverage Analysis**
   - HMDB-ChEBI overlap: 7,277 CIDs (3.6% of combined total)
   - Combined HMDB+ChEBI: 193,568 unique CIDs
   - With UniChem additions: **2,705,066 unique biologically relevant CIDs (actual)**
   - This represents comprehensive coverage of metabolites, drugs, lipids, and biochemically relevant compounds

### Filtering Implementation

1. **Create Allowlist Script** (`create_bio_relevant_cid_allowlist_chunked.py`):
   - Uses SAX parser for memory-efficient processing of large XML files (HMDB is 6GB+)
   - Extracts PubChem CIDs from:
     - HMDB: `<pubchem_compound_id>` tags
     - ChEBI: "Pubchem Database Links" properties in SDF format
   - Batch writes to disk to manage memory usage
   - Output: `bio_relevant_cids.txt` containing 193,568 unique CIDs from HMDB+ChEBI

2. **Process UniChem Mappings** (`process_unichem_mappings.py`):
   - Implemented memory-efficient two-pass streaming approach:
     - First pass: Identify biological UCIs (3.2M found)
     - Second pass: Extract PubChem CIDs for biological UCIs (2.64M found)
   - Uses temporary files for intermediate storage to handle 293M line file
   - Batch writing of results (50,000 CIDs per batch)
   - Successfully merged with existing HMDB+ChEBI allowlist
   - Final deduplicated output: `bio_relevant_cids_expanded.txt` with 2,705,066 unique CIDs

3. **Filter Embeddings Script** (`filter_pubchem_embeddings.py`):
   - Read the comprehensive allowlist of biologically relevant CIDs
   - Process compressed chunks from `/procedure/data/local_data/PUBCHEM_FASTEMBED/compressed_chunks/`
   - Extract only embeddings for CIDs in the allowlist
   - Output: Filtered embedding files ready for Qdrant indexing

4. **Index to Qdrant** (`index_filtered_embeddings_to_qdrant.py`):
   - Create Qdrant collection with appropriate vector dimensions
   - Batch index filtered embeddings with metadata
   - Verify indexing success and collection statistics

### Actual Outcomes (May 23, 2025)
- **Dataset reduction**: From 89.4 million embeddings to **2.3 million biologically relevant ones**
  - Original expectation: 1.4 million based on 51.68% coverage
  - Actual result: 2.3 million (64% more than expected)
  - This indicates our allowlist covers a higher percentage of available embeddings
- **Storage savings**: **~97.4% reduction** in dataset size
  - Only 2.57% of embeddings retained after filtering
- **Processing efficiency**: 
  - Filtering completed in ~7.5 hours for 89.4M embeddings
  - Average processing rate: ~42 JSON files per second
- **Improved relevance**: Dataset now exclusively contains:
  - Human metabolites (HMDB)
  - Biologically relevant chemical entities (ChEBI)
  - Drugs, lipids, and biochemically active compounds (UniChem sources)
- **Better performance expectations**: 
  - Qdrant queries will search only 2.3M relevant compounds vs 89.4M total
  - Expected query latency: <100ms per search
  - Higher precision in RAG results due to focused dataset

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

## Implementation Status (May 23, 2025)

### Completed Components
1. **Bio-relevant CID Allowlist Creation** ✅
   - HMDB processing: 103,682 CIDs extracted
   - ChEBI processing: 97,163 CIDs extracted  
   - UniChem processing: 2,511,498 additional CIDs
   - Final allowlist: 2,705,066 unique biologically relevant CIDs

2. **PubChem Embeddings Filtering** ✅
   - Script: `filter_pubchem_embeddings.py`
   - Processed: 89.4M embeddings across 346 chunks
   - Retained: 2.3M biologically relevant embeddings
   - Processing time: ~7.5 hours

3. **Qdrant Infrastructure** ✅
   - Docker container deployed and running
   - Collection created with optimal settings
   - Indexing script implemented with batch processing

### In Progress
1. **Qdrant Indexing** 🔄
   - Currently indexing 2.3M filtered embeddings
   - Estimated completion: Several hours from start
   - Progress monitoring available via logs

### Pending Implementation
1. **PubChemRAGMappingClient**
   - Needs to be implemented following the architecture outlined above
   - Will integrate with existing RAG framework components

2. **Integration Testing**
   - Validate search performance with known metabolite queries
   - Measure improvement in mapping success rate
   - Benchmark query latency

## Deployment and Transfer

### Database Portability

The Qdrant vector database is fully portable and can be transferred between systems. This enables:
- Sharing pre-indexed databases between team members
- Deploying to production servers without re-indexing
- Creating backups for disaster recovery

### Transfer Requirements

**Essential Components:**
1. **Qdrant Storage** (`docker/qdrant/qdrant_storage/`): ~4GB
   - Contains all indexed vectors and metadata
   - Must be transferred with Qdrant stopped for consistency
2. **Docker Configuration** (`docker-compose.yml`): <1KB
   - Defines container settings and port mappings

**Optional Components:**
1. **Filtered Embeddings** (`data/filtered_embeddings/`): ~750MB
   - Only needed if re-indexing from scratch is required
   - 337 pickle files containing 2.3M embeddings

### Transfer Methods

#### Method 1: Direct Storage Transfer (Recommended)
```bash
# On source system:
cd /home/ubuntu/biomapper/docker/qdrant
docker compose down
tar -czf qdrant_backup.tar.gz qdrant_storage/

# Transfer the ~3.5GB file to target system

# On target system:
mkdir -p /path/to/biomapper/docker/qdrant
cd /path/to/biomapper/docker/qdrant
tar -xzf qdrant_backup.tar.gz
# Copy docker-compose.yml
docker compose up -d
```

#### Method 2: Qdrant Snapshots
```bash
# Create snapshot via API
curl -X POST 'http://localhost:6333/collections/pubchem_bge_small_v1_5/snapshots'

# Download and transfer snapshot
# Restore on target system via upload API
```

#### Method 3: Re-index from Embeddings
```bash
# Transfer filtered_embeddings/ directory
# Run indexing script (takes ~30 minutes)
poetry run python scripts/index_filtered_embeddings_to_qdrant.py \
  --input-path data/filtered_embeddings \
  --collection-name pubchem_bge_small_v1_5
```

### Storage Best Practices

1. **Git Repository**: Exclude large binary data
   ```gitignore
   docker/qdrant/qdrant_storage/
   data/filtered_embeddings/
   *.qdrant.tar.gz
   ```

2. **External Storage**: Consider storing Qdrant data outside the project
   ```yaml
   volumes:
     - ${QDRANT_STORAGE_PATH:-./qdrant_storage}:/qdrant/storage
   ```

3. **Verification**: Always verify after transfer
   ```python
   client = QdrantClient(host="localhost", port=6333)
   info = client.get_collection("pubchem_bge_small_v1_5")
   assert info.points_count == 2217373
   ```

## Future Considerations

*   **Multi-Collection RAG:** Supporting RAG against multiple vector collections (e.g., ChEMBL, DrugBank embeddings) within a single client or via multiple RAG clients.
*   **RAG for Reverse Mapping:** If a target entity (e.g., from Arivale) has rich descriptive text, embedding that text and searching against a UKBB RAG collection could be a reverse mapping strategy.
*   **LLM Fine-tuning/Prompt Engineering:** Iteratively improving LLM prompts and potentially exploring fine-tuned models for better domain-specific performance.
*   **Confidence Calibration:** Developing more robust methods for calibrating confidence scores from the LLM.
*   **Cost/Latency Optimization:** Monitoring and optimizing LLM token usage and overall RAG pipeline latency.
*   **Incremental Updates:** Strategy for updating the Qdrant index as new biologically relevant compounds are discovered or added to source databases.
*   **Distributed Deployment:** Scaling Qdrant across multiple nodes for larger datasets or higher throughput requirements.