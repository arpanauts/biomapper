# RAG Performance Evaluation Plan

## Executive Summary

This document outlines a comprehensive plan for evaluating and optimizing the performance of the `PubChemRAGMappingClient` in the Biomapper project. The plan encompasses metrics definition, benchmarking strategies, threshold optimization, and a framework for comparing different configurations to ensure the RAG-based mapping system meets performance and accuracy requirements.

## 1. Introduction

### 1.1 Background

The `PubChemRAGMappingClient` has been successfully implemented as a semantic search-based metabolite mapping solution, leveraging a Qdrant vector database containing 2.3 million biologically relevant PubChem compound embeddings. While initial testing shows promising results (70-90 queries per second, successful mapping of common metabolites), a systematic evaluation framework is needed to:

- Quantify mapping accuracy and performance
- Optimize configuration parameters
- Compare different implementation strategies
- Prepare for future enhancements (LLM adjudication, statistical significance testing)

### 1.2 Scope

This evaluation plan covers:
- The currently implemented `PubChemRAGMappingClient`
- Potential future enhancements from the advanced RAG planning documents
- Performance metrics, benchmarking, and optimization strategies
- Tools and infrastructure needed for comprehensive evaluation

## 2. Key Performance Indicators (KPIs)

### 2.1 Accuracy Metrics

#### 2.1.1 Precision
- **Definition**: Proportion of returned mappings that are correct
- **Calculation**: `True Positives / (True Positives + False Positives)`
- **Target**: ≥ 0.85 for high-confidence matches

#### 2.1.2 Recall
- **Definition**: Proportion of correct mappings that are found
- **Calculation**: `True Positives / (True Positives + False Negatives)`
- **Target**: ≥ 0.70 for common metabolites

#### 2.1.3 F1-Score
- **Definition**: Harmonic mean of precision and recall
- **Calculation**: `2 * (Precision * Recall) / (Precision + Recall)`
- **Target**: ≥ 0.75

#### 2.1.4 Mean Reciprocal Rank (MRR)
- **Definition**: Average of reciprocal ranks of correct results
- **Calculation**: `(1/n) * Σ(1/rank_i)` where rank_i is the position of the correct result
- **Target**: ≥ 0.80

### 2.2 Performance Metrics

#### 2.2.1 Latency
- **Query Latency**: Time from query submission to result return
  - P50: < 100ms
  - P95: < 500ms
  - P99: < 1000ms

#### 2.2.2 Throughput
- **Queries Per Second (QPS)**: Number of queries processed per second
  - Single-threaded: 70-90 QPS (current baseline)
  - Multi-threaded target: 200+ QPS

#### 2.2.3 Resource Utilization
- **Memory Usage**: Peak memory consumption during operation
  - Baseline: < 2GB
  - With caching: < 4GB
- **CPU Usage**: Average CPU utilization
  - Target: < 50% per core during steady state

### 2.3 Operational Metrics

#### 2.3.1 Cache Hit Rate
- **Definition**: Proportion of queries served from cache
- **Target**: > 40% after warm-up period

#### 2.3.2 Error Rate
- **Definition**: Proportion of queries resulting in errors
- **Target**: < 0.1%

#### 2.3.3 Timeout Rate
- **Definition**: Proportion of queries exceeding timeout threshold
- **Target**: < 0.01%

## 3. Benchmarking Strategy

### 3.1 Dataset Creation

#### 3.1.1 Gold Standard Dataset
Create a curated dataset of metabolite name to PubChem CID mappings:

```yaml
dataset_structure:
  - categories:
      - common_metabolites: 500 entries (glucose, caffeine, aspirin, etc.)
      - drug_compounds: 300 entries (pharmaceutical compounds)
      - natural_products: 200 entries (plant metabolites, vitamins)
      - edge_cases: 100 entries (ambiguous names, synonyms, misspellings)
      - known_non_matches: 50 entries (queries that should not return a PubChem CID)
  - format:
      - input: metabolite name/synonym
      - expected_cid: correct PubChem CID
      - alternative_cids: acceptable alternatives
      - confidence_level: HIGH/MEDIUM/LOW
```

#### 3.1.2 Data Sources
- HMDB metabolite mappings
- DrugBank compound mappings
- KEGG compound database
- Manual curation for edge cases

### 3.2 Benchmarking Methodology

#### 3.2.1 Baseline Establishment
1. Run current implementation against gold standard dataset
2. Record all metrics for each query
3. Establish baseline performance profile

#### 3.2.2 Comparative Benchmarking
Compare performance across:
- Different similarity thresholds (0.5 to 0.9)
- Various top-k values (3, 5, 10)
- With and without caching
- Different batch sizes

#### 3.2.3 Stress Testing
- Concurrent query load testing
- Large batch processing
- Memory pressure scenarios
- Network latency simulation
- Cold start performance (time to readiness and accuracy after restart)

### 3.3 Benchmarking Tools

```python
# Proposed benchmarking framework structure
class RAGBenchmark:
    def __init__(self, client, dataset):
        self.client = client
        self.dataset = dataset
        self.metrics = MetricsCollector()
    
    def run_benchmark(self):
        for query in self.dataset:
            start_time = time.time()
            result = self.client.map_identifiers([query.input])
            latency = time.time() - start_time
            
            self.metrics.record_latency(latency)
            self.metrics.evaluate_accuracy(result, query.expected_cid)
            
        return self.metrics.generate_report()
```

## 4. Threshold Optimization

### 4.1 Similarity Score Threshold Tuning

#### 4.1.1 Grid Search Approach
```python
thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
results = {}

for threshold in thresholds:
    client.set_threshold(threshold)
    metrics = run_benchmark(client, test_dataset)
    results[threshold] = {
        'precision': metrics.precision,
        'recall': metrics.recall,
        'f1_score': metrics.f1_score
    }
```

#### 4.1.2 Adaptive Threshold Strategy
- Analyze score distributions for different query types
- Implement query-type-specific thresholds
- Consider confidence-based threshold adjustment

### 4.2 Statistical Significance Implementation

Based on the advanced planning documents, implement statistical significance testing:

```python
def calculate_min_similarity(alpha: float, dim: int = 384) -> float:
    """Calculate minimum cosine similarity for statistical significance"""
    from scipy.special import betaincinv
    return np.sqrt(betaincinv(1/2, (dim-1)/2, 1-alpha))

def calculate_p_value(similarity: float, dim: int = 384) -> float:
    """Calculate p-value for given cosine similarity"""
    from scipy.special import betainc
    return 1 - betainc(1/2, (dim-1)/2, similarity**2)
```

#### 4.2.1 Alpha Level Optimization
- Test alpha levels: [0.01, 0.05, 0.1, 0.15, 0.2]
- Evaluate impact on precision/recall trade-off
- Compare with fixed threshold approach

## 5. Caching Strategy Evaluation

### 5.1 Cache Implementation Options

#### 5.1.1 Query-Level Caching
```python
class QueryCache:
    def __init__(self, max_size=10000, ttl=3600):
        self.cache = LRUCache(max_size)
        self.ttl = ttl
    
    def get_or_compute(self, query, compute_func):
        cache_key = self._generate_key(query)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = compute_func(query)
        self.cache[cache_key] = result
        return result
```

#### 5.1.2 Embedding-Level Caching
- Cache computed query embeddings
- Estimated memory: ~1.5KB per embedding
- Target cache size: 50,000 embeddings (~75MB)

### 5.2 Cache Performance Metrics

- Cache hit rate over time
- Memory usage vs. hit rate trade-off
- Impact on average query latency
- Cache warm-up time

## 6. LLM Adjudication Impact (Future Enhancement)

### 6.1 LLM Integration Evaluation

When LLM adjudication is implemented:

#### 6.1.1 Accuracy Impact
- Compare mappings with and without LLM adjudication
- Measure confidence score calibration
- Analyze LLM justification quality (e.g., via human review against criteria like factual correctness, relevance, clarity, conciseness)

#### 6.1.2 Performance Impact
- Additional latency from LLM calls
- Cost per query with LLM usage
- Strategies for selective LLM usage

### 6.2 LLM Optimization Strategies

```python
class SelectiveLLMAdjudicator:
    def should_use_llm(self, top_results):
        # Use LLM only when:
        # 1. Multiple high-scoring candidates
        # 2. Low confidence in top result
        # 3. Specific query patterns
        
        if len([r for r in top_results if r.score > 0.7]) > 1:
            return True
        if top_results[0].score < 0.75:
            return True
        return False
```

## 7. Comparative Analysis Framework

### 7.1 Configuration Matrix

| Configuration | Threshold | Top-K | Statistical Filter | Cache | LLM |
|--------------|-----------|-------|-------------------|--------|-----|
| Baseline | 0.7 | 5 | No | No | No |
| Optimized-Precision | 0.8 | 3 | Yes (α=0.05) | Yes | No |
| Optimized-Recall | 0.6 | 10 | No | Yes | No |
| Full-Featured | Dynamic | 5 | Yes (α=0.1) | Yes | Yes |

### 7.2 A/B Testing Framework

```python
class ABTestRunner:
    def __init__(self, config_a, config_b):
        self.client_a = create_client(config_a)
        self.client_b = create_client(config_b)
    
    def run_comparison(self, queries):
        results_a = []
        results_b = []
        
        for query in queries:
            # Randomly assign to configuration
            if random.random() < 0.5:
                result = self.client_a.map(query)
                results_a.append(result)
            else:
                result = self.client_b.map(query)
                results_b.append(result)
        
        return self.analyze_results(results_a, results_b)
```

## 8. Implementation Tools and Infrastructure

### 8.1 Monitoring and Logging

#### 8.1.1 Metrics Collection
```python
class MetricsCollector:
    def __init__(self):
        self.prometheus_client = PrometheusClient()
        self.langfuse_tracker = LangfuseTracker()
    
    def record_query(self, query, result, latency):
        # Prometheus metrics
        self.prometheus_client.histogram(
            'rag_query_latency_seconds',
            latency,
            labels={'status': result.status}
        )
        
        # Langfuse tracking
        self.langfuse_tracker.track(
            name="rag_query",
            input=query,
            output=result,
            metadata={'latency': latency, 'config_id': self.config_id if hasattr(self, 'config_id') else 'default'},
            tags=['benchmark', 'rag_query']
        )
```

#### 8.1.2 Dashboard Requirements
- Real-time query performance metrics
- Accuracy metrics over time
- Resource utilization graphs
- Error rate monitoring

### 8.2 Testing Infrastructure

#### 8.2.1 Unit Tests
```python
def test_threshold_impact():
    client = PubChemRAGMappingClient(threshold=0.8)
    result = client.map_identifiers(["aspirin"])
    assert result.mappings[0].confidence_score >= 0.8

def test_statistical_filtering():
    store = QdrantVectorStore()
    min_sim = store.calculate_min_similarity(alpha=0.05)
    assert 0.6 < min_sim < 0.7  # Expected range for 384 dims
```

#### 8.2.2 Integration Tests
- End-to-end mapping workflows
- Qdrant connectivity and performance
- Batch processing capabilities

### 8.3 Evaluation Scripts

```bash
# scripts/evaluation/run_rag_benchmark.py
#!/usr/bin/env python3

import argparse
from biomapper.evaluation import RAGBenchmark

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--threshold', type=float, help="Similarity threshold, overrides config if provided")
    parser.add_argument('--config-file', help="Path to a JSON/YAML client configuration file")
    parser.add_argument('--output', default='benchmark_results.json')
    
    args = parser.parse_args()
    
    benchmark = RAGBenchmark(
        dataset_path=args.dataset,
        config_file=args.config_file,
        default_threshold=args.threshold
    )
    
    results = benchmark.run()
    results.save(args.output)
```

## 9. Implementation Roadmap

### Phase 1: Baseline Evaluation (Week 1-2)
1. Create gold standard dataset
2. Implement metrics collection framework
3. Run baseline benchmarks
4. Generate initial performance report

### Phase 2: Optimization (Week 3-4)
1. Implement threshold optimization
2. Add caching layer
3. Test statistical significance filtering
4. Compare configurations

### Phase 3: Advanced Features (Week 5-6)
1. Prepare for LLM integration testing
2. Implement selective adjudication logic
3. Create A/B testing framework
4. Deploy monitoring infrastructure

### Phase 4: Production Readiness (Week 7-8)
1. Finalize optimal configuration
2. Create performance documentation
3. Set up continuous monitoring
4. Establish performance regression tests

## 10. Success Criteria

The RAG performance evaluation will be considered successful when:

1. **Accuracy Goals**:
   - Precision ≥ 0.85 for high-confidence matches
   - Recall ≥ 0.70 for common metabolites
   - F1-score ≥ 0.75 overall

2. **Performance Goals**:
   - P95 latency < 500ms
   - Throughput ≥ 200 QPS (multi-threaded)
   - Cache hit rate > 40%

3. **Operational Goals**:
   - Error rate < 0.1%
   - Clear optimization strategy documented
   - Monitoring and alerting in place

## 11. Risk Mitigation

### 11.1 Performance Risks
- **Risk**: Qdrant query latency increases with scale
- **Mitigation**: Implement caching, optimize HNSW parameters

### 11.2 Accuracy Risks
- **Risk**: Low precision with relaxed thresholds
- **Mitigation**: Statistical significance testing, selective LLM usage, robust gold standard with diverse negative examples, cross-referencing with other metadata (future `resource_metadata_system`)

### 11.3 Resource Risks
- **Risk**: Plausible but incorrect mappings due to over-reliance on semantic similarity
- **Mitigation**: Emphasize LLM adjudication for nuanced cases, robust gold standard

### 11.4 LLM & API Risks
- **Risk**: LLM API cost overruns if adjudication is too frequent
- **Mitigation**: Implement and tune selective LLM adjudication logic, monitor API costs

### 11.5 General Resource Risks
- **Risk**: Memory exhaustion with large caches
- **Mitigation**: Bounded cache sizes, memory monitoring

## 12. Conclusion

This comprehensive evaluation plan provides a structured approach to optimizing the `PubChemRAGMappingClient` performance. By systematically measuring accuracy and performance metrics, optimizing configuration parameters, and preparing for future enhancements, we can ensure the RAG-based mapping system meets the high standards required for production use in the Biomapper project.

The plan emphasizes data-driven decision making, continuous monitoring, and iterative improvement to achieve optimal balance between accuracy, performance, and resource utilization.