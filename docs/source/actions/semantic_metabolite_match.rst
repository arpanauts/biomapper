semantic_metabolite_match
========================

The ``SEMANTIC_METABOLITE_MATCH`` action uses AI-powered semantic matching with embeddings and LLM validation to identify metabolite correspondences.

Overview
--------

This advanced action combines embedding-based similarity search with Large Language Model (LLM) validation to match metabolites across datasets. It's particularly useful for:

- **Complex metabolite names** that don't match exactly
- **Cross-platform metabolomics** data integration  
- **Pathway-aware matching** using biological context
- **Quality validation** of potential matches

The action uses OpenAI's embedding models for similarity calculation and GPT models for biological validation.

Parameters
----------

.. code-block:: yaml

   action:
     type: SEMANTIC_METABOLITE_MATCH
     params:
       unmatched_dataset: "unmatched_metabolites"
       reference_map: "nightingale_reference"
       context_fields:
         unmatched: ["BIOCHEMICAL_NAME", "SUPER_PATHWAY", "SUB_PATHWAY"]
         reference: ["unified_name", "description", "category"]
       embedding_model: "text-embedding-ada-002"
       llm_model: "gpt-4"
       confidence_threshold: 0.75
       output_key: "semantic_matches"

Required Parameters
~~~~~~~~~~~~~~~~~~~

**unmatched_dataset** : str
    Key for dataset containing unmatched metabolites

**reference_map** : str
    Key for reference dataset to match against

**context_fields** : dict
    Fields to use for context per dataset

**output_key** : str
    Where to store semantic matches

Optional Parameters
~~~~~~~~~~~~~~~~~~~

**embedding_model** : str, default="text-embedding-ada-002"
    OpenAI embedding model for similarity calculation

**llm_model** : str, default="gpt-4"
    LLM model for biological validation

**confidence_threshold** : float, default=0.75
    Minimum confidence for accepting matches

**include_reasoning** : bool, default=True
    Include LLM reasoning in match results

**max_llm_calls** : int, default=100
    Maximum LLM API calls to prevent runaway costs

**embedding_similarity_threshold** : float, default=0.85
    Minimum embedding similarity for LLM validation

**batch_size** : int, default=10
    Batch size for embedding generation

**unmatched_key** : str, default=None
    Key to store final unmatched metabolites

Semantic Matching Process
-------------------------

1. **Context Creation**
   - Combines metabolite name, pathway, and description
   - Creates rich context strings for embedding

2. **Embedding Generation**
   - Uses OpenAI embeddings API
   - Caches embeddings to reduce API calls
   - Processes in batches for efficiency

3. **Similarity Search**
   - Calculates cosine similarity between embeddings
   - Identifies top candidates above threshold

4. **LLM Validation**
   - Submits candidates to GPT for biological validation
   - Gets confidence scores and reasoning
   - Filters based on confidence threshold

Context String Examples
-----------------------

The action creates rich context strings for semantic matching:

**Unmatched Metabolite Context**:
```
"Metabolite: 1-methylhistidine | SUPER_PATHWAY: Amino Acid | SUB_PATHWAY: Histidine Metabolism"
```

**Reference Metabolite Context**:
```
"Metabolite: Histidine | Description: Essential amino acid | Category: Amino acids | Platform: Nightingale NMR"
```

Example Usage
-------------

Basic Semantic Matching
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: semantic_match
       action:
         type: SEMANTIC_METABOLITE_MATCH
         params:
           unmatched_dataset: "unmatched_metabolomics"
           reference_map: "nightingale_nmr_map"
           context_fields:
             unmatched_metabolomics: ["BIOCHEMICAL_NAME", "SUPER_PATHWAY"]
             nightingale_nmr: ["unified_name", "description"]
           confidence_threshold: 0.80
           embedding_similarity_threshold: 0.85
           output_key: "semantic_matches"

Advanced Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: comprehensive_semantic_match
       action:
         type: SEMANTIC_METABOLITE_MATCH
         params:
           unmatched_dataset: "complex_metabolites"
           reference_map: "comprehensive_reference"
           context_fields:
             complex_metabolites: 
               - "BIOCHEMICAL_NAME"
               - "SUPER_PATHWAY" 
               - "SUB_PATHWAY"
               - "PLATFORM"
             comprehensive_reference:
               - "unified_name"
               - "description"
               - "category"
               - "synonyms"
           embedding_model: "text-embedding-ada-002"
           llm_model: "gpt-4"
           confidence_threshold: 0.75
           include_reasoning: true
           max_llm_calls: 200
           embedding_similarity_threshold: 0.80
           batch_size: 20
           output_key: "validated_semantic_matches"
           unmatched_key: "still_unmatched"

Cost-Controlled Matching
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: budget_semantic_match
       action:
         type: SEMANTIC_METABOLITE_MATCH
         params:
           unmatched_dataset: "priority_metabolites"
           reference_map: "core_reference"
           context_fields:
             priority_metabolites: ["BIOCHEMICAL_NAME"]
             core_reference: ["unified_name"]
           embedding_model: "text-embedding-ada-002"
           llm_model: "gpt-3.5-turbo"  # Lower cost model
           confidence_threshold: 0.85   # Higher threshold
           max_llm_calls: 50            # Strict limit
           embedding_similarity_threshold: 0.90  # Pre-filter more strictly
           output_key: "budget_matches"

LLM Validation Process
---------------------

The LLM receives structured prompts for biological validation:

**Prompt Template**:
```
I need to determine if these two metabolites are the same compound:

Metabolite A:
- Name: 1-methylhistidine
- Pathway: Amino Acid
- Sub-pathway: Histidine Metabolism
- Additional info: HMDB_ID: HMDB0000001

Metabolite B:  
- Name: Histidine
- Description: Essential amino acid
- Category: Amino acids
- Platform: Nightingale NMR

Embedding similarity: 0.887

Are these the same metabolite? Respond with:
1. YES/NO/UNCERTAIN
2. Confidence (0-1)  
3. Brief reasoning (1-2 sentences)

Format: YES|0.95|These are both referring to histidine-related compounds.
```

**LLM Response Processing**:
- Parses structured responses: Decision|Confidence|Reasoning
- Validates biological correctness
- Provides confidence scores for downstream filtering

Output Format
-------------

The action outputs enriched matches with validation metadata:

.. code-block::

   Original Metabolite + Match Info + Validation Data

Example output:

.. code-block::

   BIOCHEMICAL_NAME     | matched_name        | match_confidence | embedding_similarity | match_reasoning
   1-methylhistidine    | Histidine          | 0.85            | 0.887               | Related histidine compounds
   Glucose-6-phosphate  | Glucose            | 0.92            | 0.901               | Same base metabolite 
   Unknown compound     |                    |                 |                     |

Embedding Cache System
----------------------

Intelligent caching reduces API costs and improves performance:

**Memory Cache**
- In-memory storage for session reuse
- MD5 hashing for efficient lookups
- LRU eviction for memory management

**Disk Cache**  
- Persistent storage across sessions
- JSON serialization for portability
- TTL-based cache invalidation

**Cache Statistics**
- Hit/miss ratios tracked
- Performance metrics reported
- Cache efficiency monitoring

Error Handling and Resilience
-----------------------------

The action includes comprehensive error handling:

**API Failures**
- Graceful fallback when OpenAI APIs fail
- Retry logic with exponential backoff
- Partial results preservation

**Rate Limiting**
- Automatic rate limit detection
- Adaptive throttling
- Cost monitoring and alerting

**Data Quality Issues**
- Empty context field handling
- Invalid response parsing
- Confidence threshold validation

Statistics and Monitoring
-------------------------

Detailed statistics are provided for analysis optimization:

.. code-block:: python

   {
       "matched_count": 45,
       "unmatched_count": 15,
       "llm_calls": 87,
       "cache_hits": 32,
       "confidence_distribution": {
           "high": 35,    # ≥0.9
           "medium": 10,  # 0.75-0.9
           "low": 0       # <0.75
       },
       "embedding_similarity_avg": 0.876,
       "llm_validation_rate": 0.52,
       "api_costs_estimated": 2.34
   }

Best Practices
--------------

1. **Optimize context fields**: Include pathway and description information for better embeddings
2. **Set appropriate thresholds**: Balance recall vs precision with confidence thresholds
3. **Monitor costs**: Use `max_llm_calls` to control OpenAI API expenses
4. **Cache embeddings**: Enable caching for repeated analyses
5. **Validate results**: Review LLM reasoning for biological accuracy
6. **Batch efficiently**: Use appropriate batch sizes for your API limits

Performance Optimization
------------------------

**Embedding Efficiency**
- Batch processing for reduced API calls
- Intelligent caching strategy
- Deduplication of similar contexts

**LLM Cost Management**
- Pre-filtering with embedding similarity
- Configurable call limits
- Cost estimation and tracking

**Memory Management**
- Streaming processing for large datasets
- Cache size limitations
- Garbage collection optimization

Integration Examples
--------------------

With Traditional Matching
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: exact_match
       action:
         type: NIGHTINGALE_NMR_MATCH
         params:
           dataset_key: "metabolomics_data"
           output_key: "exact_matches"
           unmatched_key: "unmatched_after_exact"

     - name: semantic_match
       action:
         type: SEMANTIC_METABOLITE_MATCH
         params:
           unmatched_dataset: "unmatched_after_exact"
           reference_map: "nightingale_reference"
           output_key: "semantic_matches"

With Quality Assessment
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   steps:
     - name: semantic_matching
       action:
         type: SEMANTIC_METABOLITE_MATCH
         # ... parameters

     - name: validate_semantic_quality
       action:
         type: CALCULATE_MAPPING_QUALITY
         params:
           source_key: "unmatched_metabolites"
           mapped_key: "semantic_matches"
           confidence_column: "match_confidence"
           output_key: "semantic_quality_metrics"

Requirements
------------

**API Access**
- OpenAI API key required
- Sufficient API credits for embeddings and LLM calls
- Network access to OpenAI endpoints

**Dependencies**
- `openai` Python package
- `numpy` for similarity calculations
- `scikit-learn` for cosine similarity

**Environment Variables**
- `OPENAI_API_KEY`: Your OpenAI API key
- `SEMANTIC_MATCH_CACHE_DIR`: Optional cache directory

The semantic matching action provides state-of-the-art metabolite identification using AI while maintaining cost control and biological validation.