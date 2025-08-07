# Week 4 Task 4A: Integration Testing

## Overview

This task focuses on validating that all developed actions work together in complete end-to-end strategies, with performance benchmarking and memory optimization for production-scale datasets.

## Prerequisites

Before starting integration testing:
- ✅ All Week 1 protein actions completed
- ✅ Week 2 metabolite actions completed (3/4 done)
- ✅ Week 3 chemistry actions ready
- ✅ Individual action unit tests passing

## Integration Testing Scope

### 1. Complete Strategy Testing

Test all 21 mapping strategies end-to-end:

#### Protein Strategies (6)
```yaml
# Test each strategy with real data
- ukbb_to_kg2c_proteins.yaml
- ukbb_to_spoke_proteins.yaml
- hpa_to_kg2c_proteins.yaml
- hpa_to_spoke_proteins.yaml
- qin_to_kg2c_proteins.yaml
- qin_to_spoke_proteins.yaml
```

#### Metabolite Strategies (10)
```yaml
# Test with real metabolomics data
- ukbb_to_kg2c_metabolites.yaml
- ukbb_to_spoke_metabolites.yaml
- arivale_to_kg2c_metabolites.yaml
- arivale_to_spoke_metabolites.yaml
- arivale_to_ukbb_metabolites.yaml
# ... and 5 more
```

#### Chemistry Strategies (5)
```yaml
# Test with clinical chemistry data
- israeli10k_to_kg2c_chemistry.yaml
- israeli10k_to_spoke_chemistry.yaml
- arivale_chemistry_harmonization.yaml
# ... and 2 more
```

### 2. Integration Test Suite Structure

Create comprehensive integration test file:
```
tests/integration/test_complete_strategies.py
```

```python
import pytest
import pandas as pd
import time
import psutil
from biomapper_client import BiomapperClient
from pathlib import Path

class TestCompleteStrategies:
    """Integration tests for all 21 mapping strategies."""
    
    @pytest.fixture
    def client(self):
        return BiomapperClient(base_url="http://localhost:8000")
    
    @pytest.fixture
    def test_data_dir(self):
        return Path("/procedure/data/test_data/integration")
    
    # Protein Strategy Tests
    def test_ukbb_to_kg2c_proteins_integration(self, client, test_data_dir):
        """Test complete UKBB to KG2c protein mapping."""
        
        # Load test data (subset of real UKBB data)
        test_file = test_data_dir / "ukbb_proteins_subset.tsv"
        
        # Execute strategy
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        result = client.execute_strategy(
            "ukbb_to_kg2c_proteins",
            parameters={
                "ukbb_proteins_file": str(test_file),
                "output_dir": "/tmp/integration_test"
            }
        )
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Validate results
        assert result.status == "completed"
        assert result.datasets["final_mapped_proteins"] is not None
        
        # Performance assertions
        execution_time = end_time - start_time
        memory_used = end_memory - start_memory
        
        assert execution_time < 30  # Should complete in 30 seconds
        assert memory_used < 500  # Should use less than 500MB
        
        # Data quality assertions
        output_df = result.datasets["final_mapped_proteins"]
        assert len(output_df) > 0
        assert "uniprot_id" in output_df.columns
        assert "kg2c_id" in output_df.columns
        assert output_df["uniprot_id"].notna().sum() > 0.8 * len(output_df)  # 80% success rate
    
    # Metabolite Strategy Tests
    def test_arivale_metabolite_full_pipeline(self, client, test_data_dir):
        """Test Arivale metabolite mapping with all actions."""
        
        test_file = test_data_dir / "arivale_metabolites_subset.tsv"
        
        result = client.execute_strategy(
            "arivale_to_kg2c_metabolites",
            parameters={
                "metabolite_file": str(test_file),
                "use_cts_bridge": True,
                "use_nightingale_match": False  # Arivale doesn't have NMR
            }
        )
        
        # Validate action sequence
        assert "METABOLITE_EXTRACT_IDENTIFIERS" in result.actions_executed
        assert "METABOLITE_NORMALIZE_HMDB" in result.actions_executed
        assert "METABOLITE_CTS_BRIDGE" in result.actions_executed
        
        # Validate data flow
        assert result.datasets["extracted_ids"] is not None
        assert result.datasets["normalized_hmdb"] is not None
        assert result.datasets["cts_bridged"] is not None
        
    # Chemistry Strategy Tests
    def test_chemistry_vendor_harmonization(self, client, test_data_dir):
        """Test multi-vendor chemistry harmonization."""
        
        # Test files from different vendors
        labcorp_file = test_data_dir / "labcorp_chemistry.tsv"
        quest_file = test_data_dir / "quest_chemistry.tsv"
        
        # Execute harmonization strategy
        result = client.execute_strategy(
            "multi_vendor_chemistry_harmonization",
            parameters={
                "vendor_files": {
                    "labcorp": str(labcorp_file),
                    "quest": str(quest_file)
                },
                "target_unit_system": "SI",
                "use_fuzzy_matching": True
            }
        )
        
        # Validate harmonization
        harmonized_df = result.datasets["harmonized_chemistry"]
        
        # Check that units are standardized
        assert harmonized_df["unit_standardized"].nunique() < harmonized_df["unit_original"].nunique()
        
        # Check that test names are harmonized
        assert "Glucose" in harmonized_df["test_name_harmonized"].values
        assert harmonized_df["vendor_detected"].isin(["labcorp", "quest"]).all()
```

### 3. Performance Benchmarking

Create performance benchmark suite:
```
tests/performance/benchmark_strategies.py
```

```python
import pytest
import pandas as pd
import numpy as np
import time
import memory_profiler
from biomapper_client import BiomapperClient

class BenchmarkStrategies:
    """Performance benchmarks for production-scale datasets."""
    
    def generate_large_dataset(self, rows: int, entity_type: str) -> pd.DataFrame:
        """Generate synthetic large dataset for testing."""
        
        if entity_type == "protein":
            return pd.DataFrame({
                'protein_id': [f'P{i:05d}' for i in range(rows)],
                'xrefs': [f'UniProtKB:P{i:05d}|RefSeq:NP_{i:06d}' for i in range(rows)],
                'gene_symbol': [f'GENE{i}' for i in range(rows)]
            })
        elif entity_type == "metabolite":
            return pd.DataFrame({
                'metabolite_id': [f'M{i:05d}' for i in range(rows)],
                'hmdb_id': [f'HMDB{i:07d}' for i in range(rows)],
                'inchikey': [f'AAAA{i:020d}-SA-N' for i in range(rows)]
            })
        elif entity_type == "chemistry":
            return pd.DataFrame({
                'test_name': [f'Test_{i}' for i in range(rows)],
                'value': np.random.rand(rows) * 100,
                'unit': np.random.choice(['mg/dL', 'mmol/L', 'U/L'], rows),
                'loinc_code': [f'{i:05d}-{i%10}' for i in range(rows)]
            })
    
    @memory_profiler.profile
    def benchmark_100k_proteins(self):
        """Benchmark protein processing with 100k rows."""
        
        # Generate 100k protein dataset
        df = self.generate_large_dataset(100000, "protein")
        df.to_csv("/tmp/benchmark_proteins.tsv", sep='\t', index=False)
        
        client = BiomapperClient()
        
        start_time = time.time()
        
        result = client.execute_strategy(
            "benchmark_protein_strategy",
            parameters={
                "input_file": "/tmp/benchmark_proteins.tsv",
                "use_chunking": True,
                "chunk_size": 10000
            }
        )
        
        end_time = time.time()
        
        metrics = {
            'total_rows': 100000,
            'execution_time': end_time - start_time,
            'rows_per_second': 100000 / (end_time - start_time),
            'success_rate': result.statistics['success_rate'],
            'peak_memory_mb': result.statistics['peak_memory_mb']
        }
        
        # Performance targets
        assert metrics['execution_time'] < 300  # < 5 minutes
        assert metrics['rows_per_second'] > 333  # > 333 rows/second
        assert metrics['peak_memory_mb'] < 2000  # < 2GB RAM
        
        return metrics
    
    def benchmark_cross_entity_workflow(self):
        """Benchmark a workflow that uses all entity types."""
        
        # This tests the full system under load
        protein_df = self.generate_large_dataset(50000, "protein")
        metabolite_df = self.generate_large_dataset(30000, "metabolite")
        chemistry_df = self.generate_large_dataset(20000, "chemistry")
        
        # Execute complex multi-entity strategy
        # ... benchmark implementation
```

### 4. Memory Usage Optimization

Create memory optimization tests:
```python
class TestMemoryOptimization:
    """Test memory efficiency of actions and strategies."""
    
    def test_chunk_processor_memory_limits(self):
        """Verify CHUNK_PROCESSOR respects memory limits."""
        
        # Create dataset that would use 1GB in memory
        large_df = pd.DataFrame(
            np.random.rand(1000000, 100),  # 1M rows, 100 columns
            columns=[f'col_{i}' for i in range(100)]
        )
        
        # Process with 100MB memory limit
        result = client.execute_action(
            "CHUNK_PROCESSOR",
            params={
                "target_action": "SOME_MEMORY_INTENSIVE_ACTION",
                "target_params": {},
                "input_key": "large_data",
                "output_key": "processed_data",
                "chunk_by_memory": True,
                "max_memory_mb": 100
            },
            context={"datasets": {"large_data": large_df}}
        )
        
        # Verify memory was respected
        assert result.peak_memory_mb < 150  # Allow some overhead
        assert result.chunks_processed > 10  # Should have chunked
    
    def test_dtype_optimization(self):
        """Test automatic dtype optimization."""
        
        df = pd.DataFrame({
            'int64_col': np.array([1, 2, 3] * 1000, dtype='int64'),
            'float64_col': np.array([1.1, 2.2, 3.3] * 1000, dtype='float64'),
            'object_col': ['A', 'B', 'C'] * 1000
        })
        
        original_memory = df.memory_usage(deep=True).sum()
        
        # Process with optimization
        optimized_df = optimize_dataframe_dtypes(df)
        
        optimized_memory = optimized_df.memory_usage(deep=True).sum()
        
        assert optimized_memory < original_memory * 0.5  # 50% reduction
```

### 5. Cross-Action Integration Tests

```python
class TestCrossActionIntegration:
    """Test interactions between different actions."""
    
    def test_protein_to_metabolite_bridge(self):
        """Test protein-metabolite relationship mapping."""
        
        # Some strategies need to map proteins to their metabolite products
        # This tests that bridge between entity types
        
        protein_data = pd.DataFrame({
            'uniprot_id': ['P00439', 'P04406'],  # PAH, GAPDH
            'gene_symbol': ['PAH', 'GAPDH']
        })
        
        # Execute protein to metabolite mapping
        result = execute_protein_metabolite_bridge(protein_data)
        
        # PAH should map to phenylalanine/tyrosine metabolism
        assert 'HMDB0000159' in result['metabolite_hmdb'].values  # Phenylalanine
        
    def test_chemistry_to_metabolite_correlation(self):
        """Test chemistry tests correlation with metabolites."""
        
        chemistry_data = pd.DataFrame({
            'test_name': ['Glucose', 'Cholesterol', 'Triglycerides'],
            'loinc_code': ['2345-7', '2093-3', '2571-8']
        })
        
        # Map chemistry tests to related metabolites
        result = map_chemistry_to_metabolites(chemistry_data)
        
        assert 'HMDB0000122' in result['metabolite_hmdb'].values  # Glucose
```

## Success Criteria

### Integration Testing
- [ ] All 21 strategies execute successfully
- [ ] Data flows correctly between actions
- [ ] Output quality meets requirements (>80% mapping success)
- [ ] No data corruption between actions
- [ ] Error handling works across action boundaries

### Performance Benchmarks
- [ ] 100k proteins processed in < 5 minutes
- [ ] 100k metabolites processed in < 10 minutes  
- [ ] 100k chemistry tests processed in < 8 minutes
- [ ] Memory usage < 2GB for 100k rows
- [ ] Linear scaling with dataset size

### Memory Optimization
- [ ] CHUNK_PROCESSOR reduces memory by >50%
- [ ] Dtype optimization reduces memory by >30%
- [ ] No memory leaks in long-running processes
- [ ] Garbage collection works properly

## Execution Plan

### Phase 1: Setup (Day 1 Morning)
1. Create integration test directories
2. Generate synthetic test datasets
3. Set up performance monitoring

### Phase 2: Strategy Testing (Day 1 Afternoon - Day 2)
1. Test each protein strategy (6 total)
2. Test each metabolite strategy (10 total)
3. Test each chemistry strategy (5 total)
4. Document failures and bottlenecks

### Phase 3: Performance Benchmarking (Day 2 - Day 3)
1. Run 100k row benchmarks
2. Profile memory usage
3. Identify optimization opportunities
4. Implement optimizations

### Phase 4: Cross-Entity Testing (Day 3)
1. Test multi-entity workflows
2. Test action interactions
3. Validate data consistency

### Phase 5: Documentation (Day 3 Afternoon)
1. Document performance characteristics
2. Create optimization guide
3. Write troubleshooting guide

## Output Deliverables

1. **Integration Test Report**
   - Pass/fail status for all 21 strategies
   - Performance metrics for each strategy
   - Memory usage profiles

2. **Performance Benchmark Report**
   - Rows per second for each entity type
   - Memory usage patterns
   - Scaling characteristics

3. **Optimization Recommendations**
   - Identified bottlenecks
   - Suggested improvements
   - Priority ranking

4. **Production Readiness Checklist**
   - [ ] All strategies tested
   - [ ] Performance targets met
   - [ ] Memory limits enforced
   - [ ] Error handling validated
   - [ ] Documentation complete