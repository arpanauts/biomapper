Performance Optimization Guide
===============================

Overview
--------

This guide provides comprehensive strategies for optimizing biomapper performance across different use cases, from real-time clinical applications to large-scale batch processing. Performance optimization in biomapper involves balancing accuracy, speed, memory usage, and API costs.

Performance Fundamentals
------------------------

Key Performance Metrics
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Metric
     - Target Range
     - Impact
   * - **Processing Speed**
     - <5 minutes for 10K identifiers
     - User experience, real-time feasibility
   * - **Memory Usage**
     - <1GB peak for 100K identifiers
     - Resource costs, scalability
   * - **Coverage Rate**
     - 70-80% for typical datasets
     - Scientific value, downstream analysis
   * - **API Success Rate**
     - >95% for external calls
     - Reliability, data completeness
   * - **False Positive Rate**
     - <5% for production use
     - Data quality, trust in results

Performance Bottlenecks
~~~~~~~~~~~~~~~~~~~~~~~

**Common Bottlenecks by Stage**:

1. **Stage 1 (Direct Matching)**: Usually fast, but large reference datasets can slow lookups
2. **Stage 2 (Fuzzy Matching)**: O(n²) string comparisons can be expensive
3. **Stage 3 (API Calls)**: Network latency and rate limits
4. **Stage 4 (Vector Search)**: Vector computation and database queries

Strategy-Level Optimizations
-----------------------------

Pipeline Configuration
~~~~~~~~~~~~~~~~~~~~~~

**High-Speed Configuration** (Optimize for speed):

.. code-block:: yaml

   # Optimized for <30 second processing
   speed_optimized:
     stages_enabled: [1, 2]  # Skip API and vector stages
     stage1_threshold: 0.98  # Higher threshold = fewer candidates
     stage2_threshold: 0.9   # Higher threshold = less fuzzy matching
     stage2_max_distance: 1  # Stricter edit distance
     chunk_processing: true
     chunk_size: 5000
     parallel_processing: true
     enable_caching: true

**High-Accuracy Configuration** (Optimize for coverage):

.. code-block:: yaml

   # Optimized for maximum coverage
   accuracy_optimized:
     stages_enabled: [1, 2, 3, 4]  # All stages
     stage1_threshold: 0.9          # Lower threshold = more matches
     stage2_threshold: 0.75         # More aggressive fuzzy matching  
     stage3_batch_size: 25          # Smaller batches = more reliable
     stage4_threshold: 0.7          # Lower vector similarity threshold
     use_llm_validation: true       # Additional validation
     quality_control: enhanced

**Balanced Configuration** (Production default):

.. code-block:: yaml

   # Balanced speed and accuracy
   production_optimized:
     stages_enabled: [1, 2, 3, 4]
     stage1_threshold: 0.95
     stage2_threshold: 0.8
     stage3_batch_size: 50
     stage4_threshold: 0.75
     adaptive_chunking: true
     progressive_timeouts: true

Stage-Specific Optimizations
-----------------------------

Stage 1: Direct Matching Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Reference Data Optimization**:

.. code-block:: python

   # Pre-compute lookup indices
   reference_optimization = {
       "create_hash_index": True,
       "normalize_keys": True,  # Pre-normalize for faster lookup
       "use_trie_structure": True,  # For prefix matching
       "case_insensitive_index": True
   }

**Memory-Efficient Loading**:

.. code-block:: yaml

   stage1_config:
     reference_loading:
       lazy_loading: true      # Load on demand
       memory_mapping: true    # Use mmap for large files
       compression: gzip       # Compress in memory
       cache_size: 10000       # LRU cache for frequent lookups

Stage 2: Fuzzy Matching Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Algorithm Selection**:

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - Algorithm
     - Speed
     - Accuracy
     - Best For
   * - Levenshtein
     - Fast
     - Good
     - General use
   * - Jaro-Winkler
     - Medium
     - Better
     - Transposed characters
   * - Biological
     - Slow
     - Best
     - Chemical nomenclature

**Performance Tuning**:

.. code-block:: yaml

   stage2_optimization:
     # Pre-filtering to reduce candidate set
     pre_filter:
       length_difference_max: 5  # Skip very different length strings
       first_char_match: true    # Require first character match
       common_prefix_min: 2      # Minimum common prefix
     
     # Parallel processing
     parallel_chunks: 4
     chunk_size: 2000
     
     # Early termination
     max_candidates: 5         # Stop after finding 5 good matches
     early_exit_threshold: 0.95  # Stop if perfect match found

Stage 3: API Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~

**Connection Management**:

.. code-block:: python

   # Optimize HTTP connections
   api_config = {
       "connection_pool_size": 10,
       "keep_alive": True,
       "timeout": (5, 30),  # (connect, read) timeouts
       "max_retries": 3,
       "backoff_factor": 1.0,
       "session_reuse": True
   }

**Batch Size Optimization**:

.. code-block:: yaml

   # Adaptive batch sizing based on performance
   stage3_adaptive_batching:
     initial_batch_size: 50
     min_batch_size: 10
     max_batch_size: 200
     
     # Adjust based on response time
     target_response_time: 30  # seconds
     size_increase_factor: 1.2
     size_decrease_factor: 0.8

**Caching Strategy**:

.. code-block:: python

   # Multi-level caching
   caching_config = {
       "level1_memory": {
           "size": 10000,
           "ttl": 3600  # 1 hour
       },
       "level2_redis": {
           "size": 100000,
           "ttl": 86400  # 24 hours
       },
       "level3_disk": {
           "size": 1000000,
           "ttl": 604800  # 1 week
       }
   }

Stage 4: Vector Search Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Vector Database Tuning**:

.. code-block:: yaml

   qdrant_optimization:
     # Index configuration
     index_type: hnsw
     m: 16                    # HNSW connections
     ef_construct: 200        # Build-time accuracy
     ef_search: 100           # Search-time accuracy
     
     # Memory management
     memory_threshold: 0.8    # Trigger cleanup at 80%
     batch_size: 1000         # Batch vector operations
     
     # Performance tuning
     parallel_indexing: true
     prefetch_factor: 2

**Query Optimization**:

.. code-block:: python

   # Optimize vector queries
   vector_config = {
       "max_results": 5,        # Limit candidates
       "score_threshold": 0.7,  # Early filtering
       "batch_queries": True,   # Batch multiple queries
       "use_filters": True,     # Pre-filter by metadata
       "cache_embeddings": True # Cache computed embeddings
   }

Memory Management
-----------------

Dataset Chunking
~~~~~~~~~~~~~~~~

**Adaptive Chunking Strategy**:

.. code-block:: python

   def calculate_optimal_chunk_size(dataset_size, available_memory):
       """Calculate optimal chunk size based on available memory"""
       
       # Estimate memory per record (KB)
       memory_per_record = estimate_memory_usage(sample_record)
       
       # Target 70% of available memory
       target_memory = available_memory * 0.7
       
       # Calculate chunk size
       chunk_size = int(target_memory / memory_per_record)
       
       # Apply bounds
       chunk_size = max(1000, min(chunk_size, 50000))
       
       return chunk_size

**Memory Monitoring**:

.. code-block:: yaml

   memory_management:
     monitoring:
       check_interval: 30      # seconds
       warning_threshold: 0.8  # 80% memory usage
       critical_threshold: 0.95 # 95% memory usage
       
     actions:
       on_warning: reduce_batch_size
       on_critical: trigger_garbage_collection
       on_overflow: enable_disk_swap

Garbage Collection Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import gc
   
   # Optimize garbage collection for large datasets
   def optimize_gc_for_biomapper():
       # Increase generation thresholds
       gc.set_threshold(1000, 15, 15)
       
       # Force collection between stages
       gc.collect()
       
       # Disable during intensive operations
       gc.disable()
       # ... intensive processing ...
       gc.enable()

Parallel Processing
-------------------

Thread-Level Parallelization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import concurrent.futures
   from multiprocessing import Pool
   
   def parallel_fuzzy_matching(identifiers, reference_data, num_workers=4):
       """Parallel fuzzy matching implementation"""
       
       # Split identifiers into chunks
       chunk_size = len(identifiers) // num_workers
       chunks = [identifiers[i:i+chunk_size] for i in range(0, len(identifiers), chunk_size)]
       
       # Process chunks in parallel
       with Pool(num_workers) as pool:
           results = pool.starmap(fuzzy_match_chunk, 
                                 [(chunk, reference_data) for chunk in chunks])
       
       # Combine results
       return [item for sublist in results for item in sublist]

Async Processing
~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import aiohttp
   
   async def async_api_calls(identifiers, batch_size=50):
       """Async API calls for better throughput"""
       
       semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
       
       async with aiohttp.ClientSession() as session:
           tasks = []
           
           for i in range(0, len(identifiers), batch_size):
               batch = identifiers[i:i+batch_size]
               task = limited_api_call(session, batch, semaphore)
               tasks.append(task)
           
           results = await asyncio.gather(*tasks, return_exceptions=True)
           
       return results

Caching Strategies
------------------

Multi-Level Caching Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class BiomapperCache:
       def __init__(self):
           self.l1_cache = {}  # In-memory (fast)
           self.l2_cache = redis.Redis()  # Redis (medium)  
           self.l3_cache = sqlite3.connect("cache.db")  # Disk (slow)
       
       def get(self, key):
           # L1: Memory cache
           if key in self.l1_cache:
               return self.l1_cache[key]
           
           # L2: Redis cache
           result = self.l2_cache.get(key)
           if result:
               self.l1_cache[key] = result  # Promote to L1
               return result
           
           # L3: Disk cache
           result = self.l3_cache.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
           if result:
               self.l2_cache.set(key, result[0])  # Promote to L2
               self.l1_cache[key] = result[0]    # Promote to L1
               return result[0]
           
           return None

**Cache Invalidation Strategy**:

.. code-block:: yaml

   cache_management:
     ttl_strategy:
       api_results: 86400      # 24 hours
       fuzzy_matches: 3600     # 1 hour
       vector_results: 7200    # 2 hours
       exact_matches: 604800   # 1 week (more stable)
       
     invalidation_triggers:
       - reference_data_update
       - parameter_change
       - manual_cache_clear
       - strategy_version_change
       
     cleanup_schedule:
       frequency: daily
       time: "02:00"  # 2 AM
       max_size: "10GB"

Database Optimizations
----------------------

Reference Database Tuning
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sql

   -- Optimize reference database queries
   CREATE INDEX idx_metabolite_name ON metabolites(name);
   CREATE INDEX idx_metabolite_hmdb ON metabolites(hmdb_id);
   CREATE INDEX idx_metabolite_kegg ON metabolites(kegg_id);
   
   -- Compound index for common queries
   CREATE INDEX idx_metabolite_compound ON metabolites(name, hmdb_id, kegg_id);
   
   -- Full-text search index
   CREATE VIRTUAL TABLE metabolite_fts USING fts5(name, synonyms);

Vector Database Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Qdrant collection optimization
   qdrant_config = {
       "vectors": {
           "size": 384,
           "distance": "Cosine",
           "hnsw_config": {
               "m": 16,                 # Number of connections
               "ef_construct": 200,     # Build-time accuracy
               "full_scan_threshold": 20000,  # Use full scan below this
               "max_indexing_threads": 4,     # Parallel indexing
           }
       },
       "optimizers_config": {
           "deleted_threshold": 0.2,    # Trigger cleanup at 20% deleted
           "vacuum_min_vector_number": 1000,
           "default_segment_number": 2,  # Number of segments
       }
   }

Monitoring and Profiling
------------------------

Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import time
   import psutil
   import logging
   
   class PerformanceMonitor:
       def __init__(self):
           self.metrics = {}
           
       def track_stage(self, stage_name):
           def decorator(func):
               def wrapper(*args, **kwargs):
                   start_time = time.time()
                   start_memory = psutil.virtual_memory().percent
                   
                   try:
                       result = func(*args, **kwargs)
                       
                       end_time = time.time()
                       end_memory = psutil.virtual_memory().percent
                       
                       self.metrics[stage_name] = {
                           'duration': end_time - start_time,
                           'memory_change': end_memory - start_memory,
                           'success': True
                       }
                       
                       return result
                       
                   except Exception as e:
                       self.metrics[stage_name] = {
                           'duration': time.time() - start_time,
                           'error': str(e),
                           'success': False
                       }
                       raise
                       
               return wrapper
           return decorator

Profiling Tools
~~~~~~~~~~~~~~~

**CPU Profiling**:

.. code-block:: python

   import cProfile
   import pstats
   
   # Profile biomapper execution
   profiler = cProfile.Profile()
   profiler.enable()
   
   # Run biomapper pipeline
   result = run_biomapper_pipeline(config)
   
   profiler.disable()
   
   # Analyze results
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative')
   stats.print_stats(20)  # Top 20 functions

**Memory Profiling**:

.. code-block:: python

   import tracemalloc
   
   # Built-in memory tracking (available in Python 3.4+)
   def profile_memory_usage(func, *args, **kwargs):
       tracemalloc.start()
       result = func(*args, **kwargs)
       current, peak = tracemalloc.get_traced_memory()
       tracemalloc.stop()
       
       print(f"Current memory: {current / 1024 / 1024:.2f} MB")
       print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
       return result

Troubleshooting Performance Issues
----------------------------------

Common Performance Problems
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 35 35
   :header-rows: 1

   * - Problem
     - Symptoms
     - Solutions
   * - Memory exhaustion
     - OOM errors, swapping
     - Enable chunking, reduce batch sizes
   * - Slow API calls
     - Stage 3 timeouts
     - Increase batch size, add caching
   * - Vector search slow
     - Stage 4 takes >5 minutes
     - Optimize index, reduce candidates
   * - High CPU usage
     - Stage 2 uses 100% CPU
     - Enable parallel processing
   * - Poor cache hit rate
     - Repeated slow operations
     - Review cache TTL, increase sizes

Diagnostic Commands
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Monitor system resources during execution
   top -p $(pgrep -f biomapper)
   
   # Track memory usage
   pmap -x $(pgrep -f biomapper)
   
   # Monitor disk I/O
   iotop -p $(pgrep -f biomapper)
   
   # Network monitoring for API calls
   netstat -i 1  # Interface stats
   
   # Check biomapper-specific performance
   poetry run pytest tests/performance/test_algorithm_complexity.py -v
   
   # Monitor Python memory usage
   python -c "import tracemalloc; tracemalloc.start(); # your code here"

Performance Testing Framework
-----------------------------

Benchmark Suite
~~~~~~~~~~~~~~~

.. code-block:: python

   class BiomapperBenchmark:
       def __init__(self):
           self.test_datasets = {
               'small': 100,     # 100 metabolites
               'medium': 1000,   # 1K metabolites  
               'large': 10000,   # 10K metabolites
               'xlarge': 100000  # 100K metabolites
           }
           
       def run_performance_suite(self):
           results = {}
           
           for size_name, size in self.test_datasets.items():
               dataset = self.generate_test_dataset(size)
               
               start_time = time.time()
               result = run_biomapper_pipeline(dataset)
               end_time = time.time()
               
               results[size_name] = {
                   'processing_time': end_time - start_time,
                   'coverage': result.coverage_percentage,
                   'memory_peak': result.peak_memory_usage
               }
               
           return results

Continuous Performance Monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Performance CI pipeline
   performance_tests:
     schedule: daily
     
     benchmarks:
       - name: small_dataset_speed
         dataset_size: 1000
         max_time: 30  # seconds
         min_coverage: 70  # percent
         
       - name: large_dataset_memory
         dataset_size: 50000
         max_memory: 4  # GB
         min_coverage: 65
         
     alerts:
       - condition: performance_degradation > 20%
         action: slack_notification
         recipients: [dev-team]

Production Optimization Checklist
----------------------------------

Pre-Deployment Checklist
~~~~~~~~~~~~~~~~~~~~~~~~~

- [ ] **Profiling Complete**: CPU and memory profiling completed
- [ ] **Caching Enabled**: Multi-level caching configured and tested
- [ ] **Resource Limits**: Memory and CPU limits set appropriately  
- [ ] **Monitoring Configured**: Performance metrics collection enabled
- [ ] **Error Handling**: Graceful degradation and recovery tested
- [ ] **Load Testing**: Performance under expected load verified
- [ ] **Documentation**: Performance characteristics documented

Deployment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # Production-optimized configuration
   production_config:
     # Resource allocation
     memory_limit: "8GB"
     cpu_cores: 4
     
     # Performance tuning
     enable_chunking: true
     chunk_size: 5000
     parallel_workers: 4
     cache_enabled: true
     
     # Monitoring
     metrics_enabled: true
     performance_logging: true
     alert_thresholds:
       memory_usage: 80%
       processing_time: 300  # seconds
       error_rate: 5%

Algorithm Complexity Resources
------------------------------

BioMapper includes comprehensive algorithm complexity monitoring and optimization tools:

**Core Efficiency Classes**:

.. code-block:: python

   from core.algorithms.efficient_matching import EfficientMatcher
   
   # Replace O(n*m) nested loops with O(n+m) indexed matching
   target_index = EfficientMatcher.build_index(target_data, key_func)
   matches = EfficientMatcher.match_with_index(source_data, target_index, key_func)
   
   # Multi-key indexing for biological identifiers
   protein_index = EfficientMatcher.multi_key_index(
       proteins,
       key_funcs=[
           lambda p: p.get('uniprot_id'),
           lambda p: p.get('gene_symbol'),
           lambda p: p.get('ensembl_id')
       ]
   )

**Performance Testing**:

.. code-block:: bash

   # Run algorithm complexity tests
   poetry run pytest tests/performance/test_algorithm_complexity.py -v
   
   # Performance scaling verification
   poetry run python tests/performance/test_algorithm_complexity.py

**Algorithm Performance Estimator**:

.. code-block:: python

   from core.algorithms.efficient_matching import EfficientMatcher
   
   # Estimate performance before implementation
   estimates = EfficientMatcher.estimate_performance(
       n_source=10000,
       n_target=100000,
       algorithm="hash_index"
   )
   print(f"Estimated time: {estimates['estimated_time']}")
   print(f"Complexity: {estimates['complexity']}")

See Also
--------

- ``/biomapper/dev/standards/ALGORITHM_COMPLEXITY_GUIDE.md`` - Detailed algorithm best practices
- ``/biomapper/src/core/algorithms/efficient_matching.py`` - Efficient matching implementations
- ``/biomapper/tests/performance/test_algorithm_complexity.py`` - Performance benchmarks and tests

---

## Verification Sources
*Last verified: 2025-08-22*

This documentation was verified against the following project resources:

- `/biomapper/src/core/algorithms/efficient_matching.py` (verified all performance optimization utilities and methods)
- `/biomapper/tests/performance/test_algorithm_complexity.py` (confirmed benchmarking framework and test implementation)
- `/biomapper/dev/standards/ALGORITHM_COMPLEXITY_GUIDE.md` (cross-referenced algorithm best practices and anti-patterns)
- `/biomapper/README.md` (verified architectural components and performance features)
- `/biomapper/CLAUDE.md` (confirmed standardizations and testing framework integration)
- `/biomapper/pyproject.toml` (verified dependencies and testing configuration)