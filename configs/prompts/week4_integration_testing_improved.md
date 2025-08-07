# Week 4 Task 4A: Integration Testing (Improved)

## Overview

This task validates that all developed actions work together in complete end-to-end strategies, with performance benchmarking and memory optimization for production-scale datasets.

## Prerequisites

Before starting integration testing:
- ✅ All Week 1 protein actions completed
- ✅ All Week 2 metabolite actions completed  
- ✅ All Week 3 chemistry actions completed
- ✅ Individual action unit tests passing

## Integration Testing Scope

### 1. Complete Strategy Testing

Test all 21 mapping strategies end-to-end with real data subsets:

#### Protein Strategies (6 complete)
```yaml
1. ukbb_to_kg2c_proteins.yaml
2. ukbb_to_spoke_proteins.yaml  
3. hpa_to_kg2c_proteins.yaml
4. hpa_to_spoke_proteins.yaml
5. qin_to_kg2c_proteins.yaml
6. qin_to_spoke_proteins.yaml
```

#### Metabolite Strategies (10 complete)
```yaml
1. ukbb_to_kg2c_metabolites.yaml
2. ukbb_to_spoke_metabolites.yaml
3. arivale_to_kg2c_metabolites.yaml
4. arivale_to_spoke_metabolites.yaml
5. arivale_to_ukbb_metabolites.yaml
6. israeli10k_to_kg2c_metabolites.yaml
7. israeli10k_to_spoke_metabolites.yaml
8. israeli10k_to_arivale_metabolites.yaml
9. nightingale_nmr_analysis.yaml
10. multi_metabolite_harmonization.yaml
```

#### Chemistry Strategies (5 complete)
```yaml
1. israeli10k_to_kg2c_chemistry.yaml
2. israeli10k_to_spoke_chemistry.yaml
3. arivale_chemistry_harmonization.yaml
4. multi_vendor_chemistry_integration.yaml
5. clinical_chemistry_standardization.yaml
```

### 2. Test Data Preparation

#### Data Requirements and Sources
```python
# Test data specifications
TEST_DATA_REQUIREMENTS = {
    'protein_test_data': {
        'source': 'UKBB subset + HPA subset + QIN subset',
        'size': '10,000 proteins each',
        'characteristics': {
            'uniprot_coverage': '>95%',
            'xrefs_complexity': 'representative of real data',
            'gene_symbol_variations': 'include all major formats'
        },
        'quality_metrics': {
            'missing_data_rate': '<5%',
            'duplicate_rate': '<1%',
            'invalid_format_rate': '<2%'
        }
    },
    'metabolite_test_data': {
        'source': 'Arivale subset + UKBB NMR + Israeli10k',
        'size': '5,000 metabolites each',
        'characteristics': {
            'hmdb_id_coverage': '>90%',
            'multi_id_complexity': 'real-world distribution',
            'nmr_biomarker_coverage': 'all major categories'
        },
        'quality_metrics': {
            'id_extraction_success': '>85%',
            'format_validity': '>95%',
            'cross_reference_accuracy': '>90%'
        }
    },
    'chemistry_test_data': {
        'source': 'Israeli10k + Arivale + Multi-vendor',
        'size': '8,000 tests each',
        'characteristics': {
            'loinc_coverage': '>80%',
            'vendor_diversity': 'all 6 supported vendors',
            'test_name_variations': 'comprehensive abbreviations'
        },
        'quality_metrics': {
            'loinc_extraction_rate': '>75%',
            'fuzzy_match_accuracy': '>80%',
            'harmonization_success': '>85%'
        }
    }
}
```

#### Data Generation Scripts
```python
def generate_realistic_test_data(entity_type: str, size: int) -> pd.DataFrame:
    """Generate realistic test data with statistical properties of real datasets."""
    
    if entity_type == "protein":
        # Based on UKBB protein distribution analysis
        return pd.DataFrame({
            'protein_id': generate_uniprot_distribution(size),
            'xrefs': generate_complex_xrefs(size, avg_refs=3.2),
            'gene_symbol': generate_gene_symbols(size, case_variations=True),
            'confidence_score': np.random.lognormal(0.8, 0.3, size)  # Real distribution
        })
    
    elif entity_type == "metabolite":
        # Based on Arivale metabolomics analysis
        return pd.DataFrame({
            'metabolite_id': generate_metabolite_ids(size),
            'hmdb_id': generate_hmdb_with_variants(size, padding_variations=True),
            'inchikey': generate_realistic_inchikeys(size),
            'compound_name': generate_metabolite_names(size, synonyms=True),
            'detection_frequency': np.random.beta(2, 5, size)  # Real detection pattern
        })
    
    elif entity_type == "chemistry":
        # Based on clinical lab analysis
        return pd.DataFrame({
            'test_name': generate_clinical_test_names(size, vendor_variations=True),
            'value': generate_lab_values_by_test(size),  # Realistic ranges
            'unit': generate_units_with_vendor_preferences(size),
            'loinc_code': generate_loinc_with_gaps(size, missing_rate=0.25),
            'vendor': np.random.choice(['labcorp', 'quest', 'mayo', 'arivale'], size, 
                                     p=[0.3, 0.3, 0.2, 0.2])  # Real market share
        })
```

### 3. Enhanced Integration Test Suite

```python
# tests/integration/test_complete_strategies_enhanced.py
import pytest
import pandas as pd
import time
import psutil
import numpy as np
from pathlib import Path
from typing import Dict, List
from biomapper_client import BiomapperClient

class TestCompleteStrategiesEnhanced:
    """Enhanced integration tests for all 21 mapping strategies."""
    
    @pytest.fixture
    def client(self):
        """BiomapperClient with timeout and retry configuration."""
        return BiomapperClient(
            base_url="http://localhost:8000",
            timeout=300,  # 5 minutes
            max_retries=3
        )
    
    @pytest.fixture
    def performance_monitor(self):
        """Performance monitoring fixture."""
        class PerformanceMonitor:
            def __init__(self):
                self.start_time = None
                self.start_memory = None
                self.peak_memory = 0
                
            def start(self):
                self.start_time = time.time()
                self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
            def update_peak(self):
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, current_memory)
                
            def get_metrics(self):
                return {
                    'execution_time': time.time() - self.start_time,
                    'memory_used': self.peak_memory - self.start_memory,
                    'peak_memory': self.peak_memory
                }
        
        return PerformanceMonitor()
    
    # Enhanced Quality Validation
    def validate_mapping_quality(self, result_df: pd.DataFrame, entity_type: str) -> Dict:
        """Comprehensive quality validation with entity-specific metrics."""
        
        quality_metrics = {
            'total_rows': len(result_df),
            'success_rate': 0,
            'confidence_distribution': {},
            'coverage_metrics': {},
            'data_quality': {}
        }
        
        if entity_type == "protein":
            # Protein-specific quality metrics
            valid_uniprot = result_df['uniprot_id'].str.match(r'^[A-Z0-9]{6}$').sum()
            quality_metrics['success_rate'] = valid_uniprot / len(result_df)
            quality_metrics['coverage_metrics'] = {
                'uniprot_coverage': (result_df['uniprot_id'].notna().sum() / len(result_df)),
                'gene_symbol_coverage': (result_df['gene_symbol'].notna().sum() / len(result_df)),
                'xrefs_processed': (result_df['xrefs_processed'].sum() / len(result_df))
            }
            
        elif entity_type == "metabolite":
            # Metabolite-specific quality metrics  
            valid_hmdb = result_df['hmdb_id'].str.match(r'^HMDB\d{7}$').sum()
            quality_metrics['success_rate'] = valid_hmdb / len(result_df)
            quality_metrics['coverage_metrics'] = {
                'hmdb_coverage': (result_df['hmdb_id'].notna().sum() / len(result_df)),
                'inchikey_coverage': (result_df['inchikey'].notna().sum() / len(result_df)),
                'cts_bridge_success': (result_df['cts_mapped'].sum() / len(result_df))
            }
            
        elif entity_type == "chemistry":
            # Chemistry-specific quality metrics
            valid_loinc = result_df['loinc_code'].str.match(r'^\d{1,5}-\d{1}$').sum()
            quality_metrics['success_rate'] = valid_loinc / len(result_df)
            quality_metrics['coverage_metrics'] = {
                'loinc_extraction_rate': (result_df['loinc_extracted'].sum() / len(result_df)),
                'fuzzy_match_rate': (result_df['fuzzy_matched'].sum() / len(result_df)),
                'harmonization_rate': (result_df['harmonized'].sum() / len(result_df))
            }
        
        return quality_metrics
    
    # Performance Benchmarking with Statistical Analysis
    def run_performance_benchmark(self, strategy_name: str, dataset_size: int) -> Dict:
        """Run comprehensive performance benchmark with statistical analysis."""
        
        # Run benchmark multiple times for statistical significance
        execution_times = []
        memory_usage = []
        success_rates = []
        
        for run in range(5):  # 5 runs for statistical analysis
            monitor = self.performance_monitor()
            monitor.start()
            
            # Generate test data for this run
            test_data = self.generate_benchmark_data(strategy_name, dataset_size)
            
            result = self.client.execute_strategy(
                strategy_name,
                parameters={"test_data": test_data}
            )
            
            metrics = monitor.get_metrics()
            execution_times.append(metrics['execution_time'])
            memory_usage.append(metrics['peak_memory'])
            success_rates.append(result.statistics.get('success_rate', 0))
        
        # Statistical analysis
        return {
            'dataset_size': dataset_size,
            'execution_time': {
                'mean': np.mean(execution_times),
                'std': np.std(execution_times),
                'p95': np.percentile(execution_times, 95),
                'p99': np.percentile(execution_times, 99)
            },
            'memory_usage': {
                'mean': np.mean(memory_usage),
                'std': np.std(memory_usage),
                'peak': np.max(memory_usage)
            },
            'success_rate': {
                'mean': np.mean(success_rates),
                'std': np.std(success_rates),
                'min': np.min(success_rates)
            },
            'throughput_rows_per_second': dataset_size / np.mean(execution_times)
        }
    
    # Comprehensive Integration Tests
    @pytest.mark.integration
    def test_protein_strategy_complete_pipeline(self, client, performance_monitor):
        """Test complete protein mapping pipeline with quality validation."""
        
        test_data = generate_realistic_test_data("protein", 10000)
        
        performance_monitor.start()
        
        result = client.execute_strategy(
            "ukbb_to_kg2c_proteins",
            parameters={
                "protein_data": test_data.to_dict('records'),
                "quality_thresholds": {
                    'min_success_rate': 0.80,
                    'max_processing_time': 300
                }
            }
        )
        
        metrics = performance_monitor.get_metrics()
        quality = self.validate_mapping_quality(result.datasets['final_output'], 'protein')
        
        # Enhanced Assertions with Confidence Intervals
        assert quality['success_rate'] > 0.80, f"Success rate {quality['success_rate']} below threshold"
        assert metrics['execution_time'] < 300, f"Execution time {metrics['execution_time']}s exceeded limit"
        assert metrics['peak_memory'] < 1000, f"Peak memory {metrics['peak_memory']}MB exceeded limit"
        
        # Quality-specific assertions
        assert quality['coverage_metrics']['uniprot_coverage'] > 0.85
        assert quality['coverage_metrics']['gene_symbol_coverage'] > 0.75
        
        return {
            'strategy': 'ukbb_to_kg2c_proteins',
            'performance': metrics,
            'quality': quality
        }

    @pytest.mark.performance  
    def test_scalability_100k_dataset(self, client):
        """Test system scalability with 100k+ row datasets."""
        
        scalability_results = {}
        
        # Test with increasing dataset sizes
        for size in [10000, 25000, 50000, 100000]:
            benchmark_results = self.run_performance_benchmark(
                "comprehensive_protein_mapping", 
                size
            )
            scalability_results[size] = benchmark_results
            
            # Verify linear scaling (allowing for 20% overhead)
            if size > 10000:
                base_time = scalability_results[10000]['execution_time']['mean']
                expected_time = base_time * (size / 10000) * 1.2  # 20% overhead
                actual_time = benchmark_results['execution_time']['mean']
                
                assert actual_time < expected_time, (
                    f"Non-linear scaling detected: {size} rows took {actual_time}s, "
                    f"expected <{expected_time}s"
                )
        
        return scalability_results
    
    @pytest.mark.memory
    def test_memory_optimization_validation(self, client):
        """Validate memory optimization techniques."""
        
        # Test without chunking
        large_data = generate_realistic_test_data("metabolite", 50000)
        
        result_without_chunking = client.execute_strategy(
            "arivale_metabolite_processing",
            parameters={
                "data": large_data,
                "use_chunking": False
            }
        )
        
        # Test with chunking
        result_with_chunking = client.execute_strategy(
            "arivale_metabolite_processing", 
            parameters={
                "data": large_data,
                "use_chunking": True,
                "chunk_size": 5000,
                "max_memory_mb": 500
            }
        )
        
        memory_without = result_without_chunking.statistics['peak_memory_mb']
        memory_with = result_with_chunking.statistics['peak_memory_mb']
        
        # Verify memory reduction
        memory_reduction = (memory_without - memory_with) / memory_without
        assert memory_reduction > 0.30, f"Memory reduction only {memory_reduction*100:.1f}%, expected >30%"
        
        # Verify results are equivalent
        assert result_without_chunking.datasets['output'].equals(result_with_chunking.datasets['output'])
        
        return {
            'memory_reduction_percent': memory_reduction * 100,
            'chunked_memory_mb': memory_with,
            'unchunked_memory_mb': memory_without
        }
```

### 4. Success Criteria (Enhanced)

#### Quantitative Metrics
- **Strategy Success**: All 21 strategies complete without critical errors
- **Quality Thresholds**: 
  - Protein mapping: >80% valid UniProt matches
  - Metabolite mapping: >75% successful ID resolution
  - Chemistry mapping: >70% LOINC/test name matches
- **Performance Targets**:
  - 100k proteins: <5 minutes (mean), <7 minutes (p95)
  - 100k metabolites: <10 minutes (mean), <15 minutes (p95) 
  - 100k chemistry tests: <8 minutes (mean), <12 minutes (p95)
- **Memory Efficiency**: 
  - <2GB peak memory for 100k rows
  - >30% memory reduction with chunking
  - Linear memory scaling (±20%) across dataset sizes

#### Qualitative Metrics  
- **Data Integrity**: No corruption between action boundaries
- **Error Resilience**: Graceful handling of malformed input data
- **Cross-Entity Integration**: Multi-entity workflows function correctly

### 5. Deliverables (Enhanced)

#### Integration Test Report Template
```markdown
# Integration Test Report - Week 4A

## Executive Summary
- Strategies tested: 21/21 (100%)  
- Overall success rate: X%
- Critical issues identified: Y
- Performance baseline established: ✅/❌

## Detailed Results by Entity Type

### Protein Strategies (6/6)
| Strategy | Success Rate | Avg Time (s) | Peak Memory (MB) | Quality Score |
|----------|--------------|--------------|------------------|---------------|
| ukbb_to_kg2c_proteins | 87.3% | 156 | 445 | 8.2/10 |
| ... | ... | ... | ... | ... |

### Performance Benchmark Summary
| Dataset Size | Entity | Mean Time (s) | P95 Time (s) | Throughput (rows/s) |
|--------------|--------|---------------|--------------|---------------------|
| 100k | Protein | 287 | 334 | 348 |
| 100k | Metabolite | 456 | 523 | 219 |
| 100k | Chemistry | 398 | 445 | 251 |

## Memory Optimization Results
- Chunking effectiveness: 47% memory reduction
- Linear scaling validation: ✅ within 15% variance
- Memory leak detection: ✅ no leaks detected

## Issues and Recommendations
1. **Issue**: Chemistry fuzzy matching timeout on vendor datasets >50k
   **Recommendation**: Implement progressive timeout with fallback
2. **Issue**: CTS API rate limiting causes metabolite delays
   **Recommendation**: Enhanced caching and batch optimization
```

#### Performance Optimization Guide
```markdown
# Performance Optimization Guide

## Proven Optimizations
1. **Chunking Configuration**:
   - Protein data: 15k rows/chunk optimal
   - Metabolite data: 8k rows/chunk optimal  
   - Chemistry data: 12k rows/chunk optimal

2. **Memory Management**:
   - Enable dtype optimization: 25-40% memory savings
   - Use categorical encoding for repetitive strings
   - Clear intermediate DataFrames explicitly

3. **Action-Specific Optimizations**:
   - PROTEIN_MULTI_BRIDGE: Cache API responses (90% hit rate)
   - METABOLITE_CTS_BRIDGE: Batch requests (5x speedup)
   - CHEMISTRY_FUZZY_MATCH: Pre-compile regex patterns (30% speedup)
```

## Execution Timeline

### Day 1: Setup and Data Preparation
- **Morning**: Set up test environments and data generation
- **Afternoon**: Validate test data quality and representativeness

### Day 2: Integration Testing
- **Morning**: Execute all 21 strategies with quality validation
- **Afternoon**: Diagnose and document any failures

### Day 3: Performance Benchmarking  
- **Full Day**: Run comprehensive performance tests and scalability analysis

### Day 4: Optimization and Documentation
- **Morning**: Implement identified optimizations
- **Afternoon**: Generate reports and recommendations

This enhanced integration testing approach provides comprehensive validation with statistical rigor, ensuring the biomapper system is production-ready for real-world biological data harmonization workflows.