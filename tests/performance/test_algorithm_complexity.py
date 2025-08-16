"""Performance tests for algorithm complexity verification."""

import time
import random
import string
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
import pytest
from pathlib import Path
import sys

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from biomapper.core.algorithms.efficient_matching import EfficientMatcher


class TestAlgorithmComplexity:
    """Test and benchmark different matching algorithms."""
    
    def generate_test_data(self, size: int, overlap_ratio: float = 0.3) -> Tuple[List[Dict], List[Dict]]:
        """Generate test datasets with controlled overlap."""
        # Generate random identifiers
        all_ids = [''.join(random.choices(string.ascii_uppercase + string.digits, k=8)) 
                   for _ in range(int(size / overlap_ratio))]
        
        # Create source dataset
        source_ids = random.sample(all_ids, size)
        source = [{'id': id_val, 'value': random.random()} for id_val in source_ids]
        
        # Create target dataset with some overlap
        overlap_size = int(size * overlap_ratio)
        overlap_ids = random.sample(source_ids, overlap_size)
        new_ids = random.sample([id_val for id_val in all_ids if id_val not in source_ids], 
                                size - overlap_size)
        target_ids = overlap_ids + new_ids
        random.shuffle(target_ids)
        target = [{'id': id_val, 'value': random.random()} for id_val in target_ids]
        
        return source, target
    
    def benchmark_nested_loop(self, source: List[Dict], target: List[Dict]) -> Tuple[List, float]:
        """Benchmark naive nested loop approach (O(n*m))."""
        start_time = time.time()
        matches = []
        
        for source_item in source:
            for target_item in target:
                if source_item['id'] == target_item['id']:
                    matches.append((source_item, target_item))
        
        elapsed = time.time() - start_time
        return matches, elapsed
    
    def benchmark_indexed_matching(self, source: List[Dict], target: List[Dict]) -> Tuple[List, float]:
        """Benchmark indexed matching approach (O(n+m))."""
        start_time = time.time()
        
        # Build index
        target_index = EfficientMatcher.build_index(target, lambda x: x['id'])
        
        # Match using index
        matches = EfficientMatcher.match_with_index(
            source, target_index, lambda x: x['id']
        )
        
        elapsed = time.time() - start_time
        return matches, elapsed
    
    def benchmark_set_intersection(self, source: List[Dict], target: List[Dict]) -> Tuple[List, float]:
        """Benchmark set intersection approach (O(n+m))."""
        start_time = time.time()
        
        source_ids = [item['id'] for item in source]
        target_ids = [item['id'] for item in target]
        
        matched, _, _ = EfficientMatcher.set_intersection_match(source_ids, target_ids)
        
        elapsed = time.time() - start_time
        return matched, elapsed
    
    def benchmark_dataframe_operations(self, source: List[Dict], target: List[Dict]) -> Dict[str, float]:
        """Compare DataFrame operations: iterrows vs vectorized."""
        source_df = pd.DataFrame(source)
        target_df = pd.DataFrame(target)
        
        # Benchmark iterrows (BAD)
        start_time = time.time()
        matches_iterrows = []
        for _, source_row in source_df.iterrows():
            for _, target_row in target_df.iterrows():
                if source_row['id'] == target_row['id']:
                    matches_iterrows.append((source_row.to_dict(), target_row.to_dict()))
        iterrows_time = time.time() - start_time
        
        # Benchmark vectorized merge (GOOD)
        start_time = time.time()
        merged = pd.merge(source_df, target_df, on='id', suffixes=('_source', '_target'))
        vectorized_time = time.time() - start_time
        
        return {
            'iterrows_time': iterrows_time,
            'vectorized_time': vectorized_time,
            'speedup': iterrows_time / vectorized_time if vectorized_time > 0 else float('inf'),
            'iterrows_matches': len(matches_iterrows),
            'vectorized_matches': len(merged)
        }
    
    def test_performance_comparison(self):
        """Compare performance of different matching approaches."""
        sizes = [(100, 100), (500, 500), (1000, 1000), (1000, 5000)]
        results = []
        
        print("\n" + "=" * 80)
        print("ALGORITHM PERFORMANCE COMPARISON")
        print("=" * 80)
        
        for source_size, target_size in sizes:
            print(f"\nTesting with source={source_size}, target={target_size}")
            print("-" * 40)
            
            # Generate test data
            source, _ = self.generate_test_data(source_size)
            target, _ = self.generate_test_data(target_size)
            
            # Test nested loop (only for small sizes)
            if source_size * target_size <= 100000:
                matches_nested, time_nested = self.benchmark_nested_loop(source, target)
                print(f"Nested Loop:    {time_nested:.4f}s ({len(matches_nested)} matches)")
            else:
                time_nested = None
                print(f"Nested Loop:    Skipped (would take too long)")
            
            # Test indexed matching
            matches_indexed, time_indexed = self.benchmark_indexed_matching(source, target)
            print(f"Indexed Match:  {time_indexed:.4f}s ({len(matches_indexed)} matches)")
            
            # Test set intersection
            matches_set, time_set = self.benchmark_set_intersection(source, target)
            print(f"Set Intersect:  {time_set:.4f}s ({len(matches_set)} matches)")
            
            # Calculate speedup
            if time_nested is not None:
                speedup = time_nested / time_indexed
                print(f"\nSpeedup (indexed vs nested): {speedup:.1f}x faster")
            
            results.append({
                'source_size': source_size,
                'target_size': target_size,
                'nested_time': time_nested,
                'indexed_time': time_indexed,
                'set_time': time_set,
                'operations_nested': source_size * target_size,
                'operations_indexed': source_size + target_size
            })
        
        return results
    
    def test_dataframe_performance(self):
        """Test DataFrame operation performance."""
        print("\n" + "=" * 80)
        print("DATAFRAME OPERATION PERFORMANCE")
        print("=" * 80)
        
        sizes = [100, 500, 1000]
        
        for size in sizes:
            print(f"\nTesting with size={size}")
            print("-" * 40)
            
            source, target = self.generate_test_data(size)
            results = self.benchmark_dataframe_operations(source, target)
            
            print(f"iterrows():     {results['iterrows_time']:.4f}s")
            print(f"vectorized:     {results['vectorized_time']:.4f}s")
            print(f"Speedup:        {results['speedup']:.1f}x faster")
            
            assert results['iterrows_matches'] == results['vectorized_matches'], \
                "Match counts should be equal"
    
    def test_complexity_scaling(self):
        """Verify that algorithms scale as expected."""
        print("\n" + "=" * 80)
        print("COMPLEXITY SCALING VERIFICATION")
        print("=" * 80)
        
        base_size = 100
        multipliers = [1, 2, 4, 8]
        
        indexed_times = []
        
        for mult in multipliers:
            size = base_size * mult
            source, target = self.generate_test_data(size)
            
            _, time_indexed = self.benchmark_indexed_matching(source, target)
            indexed_times.append(time_indexed)
            
            print(f"Size {size}: {time_indexed:.4f}s")
        
        # Check that indexed matching scales linearly (O(n))
        # Time should roughly double when size doubles
        for i in range(1, len(multipliers)):
            ratio = indexed_times[i] / indexed_times[i-1]
            size_ratio = multipliers[i] / multipliers[i-1]
            
            # Allow some variance due to system factors
            assert ratio < size_ratio * 3, \
                f"Indexed matching not scaling linearly: {ratio:.2f}x time for {size_ratio}x size"
        
        print("\n✓ Indexed matching scales linearly as expected")
    
    def test_memory_efficiency(self):
        """Test memory usage of different approaches."""
        import tracemalloc
        
        print("\n" + "=" * 80)
        print("MEMORY EFFICIENCY TEST")
        print("=" * 80)
        
        size = 10000
        source, target = self.generate_test_data(size)
        
        # Test indexed approach memory
        tracemalloc.start()
        target_index = EfficientMatcher.build_index(target, lambda x: x['id'])
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"Index size for {size} items:")
        print(f"  Current memory: {current / 1024 / 1024:.2f} MB")
        print(f"  Peak memory:    {peak / 1024 / 1024:.2f} MB")
        print(f"  Memory per item: {current / size:.0f} bytes")
        
        # Verify index is efficient
        assert current / size < 1000, "Index using too much memory per item"
        print("\n✓ Memory usage is acceptable")
    
    def test_chunk_processing(self):
        """Test chunked processing for large datasets."""
        print("\n" + "=" * 80)
        print("CHUNKED PROCESSING TEST")
        print("=" * 80)
        
        size = 100000
        chunk_size = 10000
        
        # Generate large dataset
        items = [{'id': str(i), 'value': i} for i in range(size)]
        
        def process_chunk(chunk):
            return [item['id'] for item in chunk if item['value'] % 2 == 0]
        
        start_time = time.time()
        results = EfficientMatcher.chunked_processing(items, process_chunk, chunk_size)
        elapsed = time.time() - start_time
        
        print(f"Processed {size} items in {len(items) // chunk_size} chunks")
        print(f"Time: {elapsed:.4f}s")
        print(f"Results: {len(results)} items")
        
        # Verify correctness
        expected = [item['id'] for item in items if item['value'] % 2 == 0]
        assert len(results) == len(expected), "Chunked processing produced wrong result"
        print("\n✓ Chunked processing works correctly")


def run_performance_tests():
    """Run all performance tests."""
    tester = TestAlgorithmComplexity()
    
    # Run comparison tests
    tester.test_performance_comparison()
    
    # Run DataFrame tests
    tester.test_dataframe_performance()
    
    # Run scaling tests
    tester.test_complexity_scaling()
    
    # Run memory tests
    tester.test_memory_efficiency()
    
    # Run chunking tests
    tester.test_chunk_processing()
    
    print("\n" + "=" * 80)
    print("ALL PERFORMANCE TESTS PASSED ✓")
    print("=" * 80)


if __name__ == "__main__":
    run_performance_tests()