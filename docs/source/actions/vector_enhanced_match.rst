vector_enhanced_match
=====================

The ``VECTOR_ENHANCED_MATCH`` action performs high-performance metabolite matching using vector database search with FastEmbed and Qdrant.

Overview
--------

This action provides scalable vector similarity search for metabolite identification using:

- **FastEmbed models** for efficient local embedding generation
- **Qdrant vector database** for high-performance similarity search
- **Multi-text strategies** using original names, CTS-enriched names, and pathway context
- **Batch processing** for large-scale metabolomics datasets

The action is optimized for scenarios where thousands of metabolites need to be matched against comprehensive reference databases.

Parameters
----------

.. code-block:: yaml

   action:
     type: VECTOR_ENHANCED_MATCH
     params:
       unmatched_dataset_key: "unmatched.api.metabolomics"
       qdrant_url: "localhost:6333"
       qdrant_collection: "hmdb_metabolites"
       embedding_model: "BAAI/bge-small-en-v1.5"
       similarity_threshold: 0.75
       top_k: 5
       output_key: "vector_matches"

Required Parameters
~~~~~~~~~~~~~~~~~~~

**unmatched_dataset_key** : str
    Key for unmatched metabolites from previous matching steps

**output_key** : str
    Key to store vector-based matches

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**target_dataset_key** : str, default=None
    Optional target dataset for additional matching

**qdrant_url** : str, default="localhost:6333"
    Qdrant vector database server URL

**qdrant_collection** : str, default="hmdb_metabolites"
    Qdrant collection name containing reference metabolites

**embedding_model** : str, default="BAAI/bge-small-en-v1.5"
    FastEmbed model for embedding generation

**similarity_threshold** : float, default=0.75
    Minimum cosine similarity score for matches

**top_k** : int, default=5
    Number of candidate matches to retrieve per query

**batch_size** : int, default=50
    Batch size for embedding generation

**track_metrics** : bool, default=True
    Enable detailed performance metrics tracking

Vector Database Setup
--------------------

Before using this action, you need a populated Qdrant collection:

**HMDB Collection Structure**:
```json
{
  "vectors": {
    "size": 384,  // BGE-small embedding dimension
    "distance": "Cosine"
  },
  "payload": {
    "hmdb_id": "HMDB0000122",
    "name": "Glucose", 
    "synonyms": ["D-Glucose", "Dextrose", "Blood sugar"],
    "inchikey": "WQZGKKKJIJFFOK-GASJEMHNSA-N",
    "molecular_formula": "C6H12O6",
    "pathways": ["Glycolysis", "Gluconeogenesis"]
  }
}
```

Multi-Text Search Strategy
--------------------------

The action uses multiple text representations for each metabolite:

**Primary Search Texts**:
1. **Original name**: Direct biochemical name from dataset
2. **CTS enriched**: Names from Chemical Translation Service
3. **Pathway context**: Name combined with pathway information
4. **Super pathway context**: Name with broader pathway category

**Search Priority**:
- Tries each text representation in order
- Returns first match above similarity threshold
- Deduplicates results to best match per metabolite

Example Usage
-------------

Basic Vector Matching
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: vector_search
       action:
         type: VECTOR_ENHANCED_MATCH
         params:
           unmatched_dataset_key: "unmatched_metabolites"
           qdrant_collection: "hmdb_reference"
           similarity_threshold: 0.80
           output_key: "vector_matches"

High-Throughput Processing
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: large_scale_vector_match
       action:
         type: VECTOR_ENHANCED_MATCH
         params:
           unmatched_dataset_key: "large_metabolomics_dataset"
           qdrant_url: "production-qdrant:6333"
           qdrant_collection: "comprehensive_metabolites"
           embedding_model: "BAAI/bge-base-en-v1.5"  # Higher accuracy
           similarity_threshold: 0.75
           top_k: 10                    # More candidates
           batch_size: 100              # Larger batches
           track_metrics: true
           output_key: "scaled_vector_matches"

Multi-Stage Matching Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: exact_matching
       action:
         type: NIGHTINGALE_NMR_MATCH
         params:
           dataset_key: "metabolomics_data"
           output_key: "exact_matches"
           unmatched_key: "unmatched.exact"

     - name: api_enrichment
       action:
         type: METABOLITE_API_ENRICHMENT
         params:
           unmatched_dataset_key: "unmatched.exact"
           output_key: "api_matches"
           unmatched_key: "unmatched.api"

     - name: vector_enhanced
       action:
         type: VECTOR_ENHANCED_MATCH
         params:
           unmatched_dataset_key: "unmatched.api"
           output_key: "vector_matches"
           unmatched_key: "final_unmatched"

FastEmbed Models
---------------

Supported embedding models with different trade-offs:

**Small Models (Fast)**
- `BAAI/bge-small-en-v1.5`: 384 dimensions, fastest
- `sentence-transformers/all-MiniLM-L6-v2`: 384 dimensions, good balance

**Base Models (Balanced)**  
- `BAAI/bge-base-en-v1.5`: 768 dimensions, better accuracy
- `sentence-transformers/all-mpnet-base-v2`: 768 dimensions, robust

**Large Models (Accurate)**
- `BAAI/bge-large-en-v1.5`: 1024 dimensions, highest accuracy
- Custom domain-specific models for specialized metabolomics

Output Format
-------------

The action outputs detailed match results with metadata:

.. code-block::

   Metabolite Info + HMDB Match + Similarity Metrics + Method Info

Example output:

.. code-block::

   BIOCHEMICAL_NAME     | hmdb_id      | hmdb_name    | similarity_score | rank | matched_on
   1-methylhistidine    | HMDB0000001  | Histidine    | 0.876           | 1    | cts_enriched
   Glucose-6-phosphate  | HMDB0000122  | Glucose      | 0.834           | 1    | name_with_pathway
   Unknown metabolite   | HMDB0001234  | L-Alanine    | 0.789           | 2    | original_name

Performance Metrics
-------------------

Comprehensive performance tracking:

.. code-block:: python

   {
       "stage": "vector_enhanced",
       "total_unmatched_input": 500,
       "total_matched": 387,
       "match_rate": 0.774,
       "avg_similarity_score": 0.831,
       "avg_candidates_per_query": 4.2,
       "execution_time": 45.2,
       "embedding_time": 12.3,
       "search_time": 28.1,
       "similarity_distribution": {
           "very_high": 156,  # ≥0.90
           "high": 98,        # 0.85-0.90
           "medium": 87,      # 0.80-0.85
           "low": 46,         # 0.75-0.80
           "very_low": 0      # <0.75
       }
   }

Optimization Features
--------------------

**Embedding Optimization**
- Local model loading for no API dependency
- Batch embedding generation for efficiency
- Memory-efficient processing for large datasets

**Search Optimization**
- Qdrant's HNSW indexing for fast similarity search
- Configurable similarity thresholds
- Early termination on high-confidence matches

**Result Optimization**
- Deduplication across multiple search texts
- Best-match selection per metabolite
- Comprehensive match provenance tracking

Error Handling
--------------

Robust error handling for production use:

**Database Connectivity**
- Automatic connection retry logic
- Graceful fallback if Qdrant unavailable
- Collection validation and error reporting

**Embedding Generation**
- Model loading error handling
- Batch processing failure recovery
- Memory management for large inputs

**Search Failures**
- Individual query error isolation
- Partial result preservation
- Detailed error logging and reporting

Best Practices
--------------

1. **Choose appropriate models**: Balance speed vs accuracy for your use case
2. **Tune similarity thresholds**: Higher thresholds for clinical data, lower for discovery
3. **Monitor performance**: Track metrics to optimize batch sizes and thresholds
4. **Prepare vector databases**: Ensure reference collections are comprehensive and current
5. **Use in pipelines**: Combine with exact matching and API enrichment for best coverage

Integration Examples
--------------------

With Quality Assessment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: vector_matching
       action:
         type: VECTOR_ENHANCED_MATCH
         # ... parameters

     - name: quality_assessment
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "unmatched_metabolites"
           mapped_key: "vector_matches"
           confidence_column: "similarity_score"
           confidence_threshold: 0.80
           output_key: "vector_quality_metrics"

With Comprehensive Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: normalize_data
       action:
         type: METABOLITE_NORMALIZE_HMDB
         params:
           input_key: "raw_metabolomics"
           output_key: "normalized_metabolomics"

     - name: exact_match
       action:
         type: NIGHTINGALE_NMR_MATCH
         params:
           dataset_key: "normalized_metabolomics"
           unmatched_key: "unmatched.exact"

     - name: cts_enrichment
       action:
         type: METABOLITE_CTS_BRIDGE
         params:
           source_key: "unmatched.exact"
           unmatched_key: "unmatched.cts"

     - name: vector_search
       action:
         type: VECTOR_ENHANCED_MATCH
         params:
           unmatched_dataset_key: "unmatched.cts"
           output_key: "vector_matches"

     - name: combine_results
       action:
         type: COMBINE_METABOLITE_MATCHES
         params:
           exact_matches: "exact_matches"
           cts_matches: "cts_matches"
           vector_matches: "vector_matches"
           output_key: "comprehensive_matches"

Requirements
------------

**System Dependencies**
- Qdrant server running and accessible
- Sufficient RAM for embedding models (2-4GB recommended)
- FastEmbed compatible environment

**Python Dependencies**
- `fastembed` for embedding generation
- `qdrant-client` for vector database access
- `numpy` for similarity calculations

**Database Setup**
- Pre-populated Qdrant collection with reference metabolites
- Appropriate vector dimensions for chosen embedding model
- Proper indexing configuration for performance

The vector enhanced matching provides state-of-the-art metabolite identification with high performance and scalability for large metabolomics datasets.