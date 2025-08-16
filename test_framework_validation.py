#!/usr/bin/env python3
"""Simple validation script to test the new testing framework."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from biomapper.testing.base import ThreeLevelTestBase, ActionTestBase
from biomapper.testing.data_generator import BiologicalDataGenerator
from biomapper.testing.performance import PerformanceProfiler
import pandas as pd


def test_data_generator():
    """Test the biological data generator."""
    print("Testing BiologicalDataGenerator...")
    
    generator = BiologicalDataGenerator()
    
    # Test UniProt ID generation
    uniprot_ids = generator.generate_uniprot_ids(10, include_isoforms=True)
    print(f"  Generated {len(uniprot_ids)} UniProt IDs: {uniprot_ids[:3]}...")
    assert len(uniprot_ids) == 10
    
    # Test gene symbol generation
    gene_symbols = generator.generate_gene_symbols(5)
    print(f"  Generated gene symbols: {gene_symbols}")
    assert len(gene_symbols) == 5
    
    # Test dataset generation
    source_df = generator.generate_test_dataset(100, 'source')
    print(f"  Generated source dataset: {source_df.shape} with columns {list(source_df.columns)}")
    assert len(source_df) == 100
    
    target_df = generator.generate_test_dataset(150, 'target')
    print(f"  Generated target dataset: {target_df.shape} with columns {list(target_df.columns)}")
    assert len(target_df) == 150
    
    # Test edge cases
    edge_cases = generator.generate_edge_cases()
    print(f"  Generated {len(edge_cases)} edge case datasets")
    assert 'empty' in edge_cases
    assert 'duplicates' in edge_cases
    
    print("✅ Data generator tests passed!\n")


def test_performance_profiler():
    """Test the performance profiler."""
    print("Testing PerformanceProfiler...")
    
    profiler = PerformanceProfiler()
    
    # Test basic profiling
    import time
    with profiler.profile("test_operation"):
        time.sleep(0.1)
        df = pd.DataFrame({'a': range(1000)})
    
    metrics = profiler.results["test_operation"]
    print(f"  Duration: {metrics.duration:.3f}s")
    print(f"  Memory delta: {metrics.memory_delta_mb:.2f} MB")
    assert metrics.duration >= 0.1
    
    # Test complexity detection
    def linear_func(data):
        return sum(data)
    
    def quadratic_func(data):
        result = 0
        for i in data:
            for j in data:
                result += 1
        return result
    
    # Generate test data
    sizes = [10, 20, 40, 80]
    
    # Test linear complexity
    results_linear = profiler.benchmark_scaling(
        lambda n: linear_func(range(n)),
        sizes,
        data_generator=lambda n: n
    )
    
    analysis = profiler.detect_complexity(results_linear)
    print(f"  Linear function detected as: {analysis.estimated_complexity} (confidence: {analysis.confidence:.2f})")
    
    print("✅ Performance profiler tests passed!\n")


def test_framework_integration():
    """Test that all components work together."""
    print("Testing framework integration...")
    
    # Create test data
    generator = BiologicalDataGenerator()
    test_data = {
        'proteins': generator.generate_test_dataset(50, 'source'),
        'entities': generator.generate_test_dataset(100, 'target')
    }
    
    # Profile an operation
    profiler = PerformanceProfiler()
    
    with profiler.profile("data_processing"):
        # Simulate data processing
        merged = pd.merge(
            test_data['proteins'],
            test_data['entities'],
            left_on='uniprot',
            right_on='id',
            how='left'
        )
    
    print(f"  Processed {len(merged)} rows")
    print(f"  Performance: {profiler.results['data_processing'].duration:.3f}s")
    
    print("✅ Framework integration test passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Three-Level Testing Framework")
    print("=" * 60 + "\n")
    
    try:
        test_data_generator()
        test_performance_profiler()
        test_framework_integration()
        
        print("=" * 60)
        print("✅ ALL FRAMEWORK TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)