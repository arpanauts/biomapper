"""Template for testing biomapper actions with three-level approach.

This template demonstrates best practices for comprehensive action testing.
Copy and modify for new actions.
"""

import pytest
import time
import pandas as pd
from typing import Dict, Any
from biomapper.testing.base import ActionTestBase
from biomapper.testing.performance import PerformanceProfiler

# Import the action to test
# from biomapper.core.strategy_actions.my_category.my_action import MyAction


class TestMyAction(ActionTestBase):
    """Three-level test suite for MyAction.
    
    Tests follow the standardized three-level approach:
    1. Unit tests with minimal synthetic data
    2. Integration tests with sample data
    3. Smoke tests with production subset
    """
    
    # Set the action class to test
    # ACTION_CLASS = MyAction
    
    # Level 1: Unit Tests (Minimal Data)
    def test_level1_minimal(self, minimal_data):
        """Unit test with minimal synthetic data.
        
        Goals:
        - Verify basic functionality
        - Test core logic with controlled inputs
        - Complete in < 1 second
        """
        # Setup test data
        context_data = {
            'source': minimal_data['proteins'],
            'target': minimal_data['entities']
        }
        
        params = {
            'source_key': 'source',
            'target_key': 'target',
            'output_key': 'result',
            # Add action-specific parameters
        }
        
        # Execute action
        start_time = time.time()
        result = self.run_action(params, context_data)
        duration = time.time() - start_time
        
        # Assertions
        self.assert_output_valid(result, min_matches=1)
        self.assert_performance(duration, max_duration=1.0, level="Level 1")
        
        # Verify specific outputs
        assert 'result' in context_data, "Output key not created"
        output_df = context_data['result']
        assert len(output_df) > 0, "No output generated"
        
        # Test specific business logic
        # assert 'expected_column' in output_df.columns
        # assert output_df['score'].min() >= 0.0
        
    def test_level1_edge_cases(self, edge_cases_data):
        """Test edge cases with minimal data."""
        
        # Test empty input
        result = self.run_action(
            {'source_key': 'empty', 'output_key': 'result'},
            {'empty': edge_cases_data['empty']}
        )
        assert result.success, "Should handle empty input gracefully"
        
        # Test single row
        result = self.run_action(
            {'source_key': 'single', 'output_key': 'result'},
            {'single': edge_cases_data['single_row']}
        )
        assert result.success, "Should handle single row"
        
        # Test duplicates
        result = self.run_action(
            {'source_key': 'dups', 'output_key': 'result'},
            {'dups': edge_cases_data['duplicates']}
        )
        assert result.success, "Should handle duplicates"
        
        # Test special characters
        result = self.run_action(
            {'source_key': 'special', 'output_key': 'result'},
            {'special': edge_cases_data['special_chars']}
        )
        assert result.success, "Should handle special characters"
        
        # Test missing values
        result = self.run_action(
            {'source_key': 'missing', 'output_key': 'result'},
            {'missing': edge_cases_data['missing_values']}
        )
        assert result.success, "Should handle missing values"
    
    # Level 2: Integration Tests (Sample Data)
    def test_level2_sample(self, sample_data):
        """Integration test with sample data.
        
        Goals:
        - Test realistic scenarios
        - Validate edge cases with larger data
        - Complete in < 10 seconds
        """
        context_data = {
            'source': sample_data['proteins'],
            'target': sample_data['entities']
        }
        
        params = {
            'source_key': 'source',
            'target_key': 'target',
            'output_key': 'result',
            # Add realistic parameters
        }
        
        # Execute action
        start_time = time.time()
        result = self.run_action(params, context_data)
        duration = time.time() - start_time
        
        # Assertions
        self.assert_output_valid(result, min_matches=50)
        self.assert_performance(duration, max_duration=10.0, level="Level 2")
        
        # Validate output quality
        output_df = context_data['result']
        
        # Check data integrity
        assert not output_df.empty, "Output should not be empty"
        assert len(output_df) >= 50, f"Expected at least 50 matches, got {len(output_df)}"
        
        # Validate output structure
        expected_columns = ['source_id', 'target_id', 'match_score']
        # for col in expected_columns:
        #     assert col in output_df.columns, f"Missing column: {col}"
        
        # Check for data quality issues
        null_ratio = output_df.isnull().sum().sum() / (len(output_df) * len(output_df.columns))
        assert null_ratio < 0.1, f"Too many null values: {null_ratio:.2%}"
        
    def test_level2_performance_characteristics(self, sample_data, performance_profiler):
        """Test performance characteristics with varying data sizes."""
        
        # Test with increasing data sizes
        sizes = [10, 50, 100, 500]
        
        def run_with_size(n):
            data = {
                'source': sample_data['proteins'].head(n),
                'target': sample_data['entities'].head(n * 2)
            }
            return self.run_action(
                {'source_key': 'source', 'target_key': 'target', 'output_key': 'result'},
                data
            )
        
        # Benchmark scaling behavior
        results = performance_profiler.benchmark_scaling(
            run_with_size,
            sizes,
            data_generator=lambda n: n  # Size is passed directly
        )
        
        # Assert complexity is acceptable (should be O(n) or O(n log n))
        performance_profiler.assert_complexity(
            results,
            max_complexity='O(n log n)',
            min_confidence=0.7
        )
    
    # Level 3: Production Subset Tests
    def test_level3_production_subset(self, production_subset):
        """Smoke test with production data subset.
        
        Goals:
        - Validate with real production data
        - Check performance with realistic data
        - Complete in < 60 seconds
        """
        if not production_subset:
            pytest.skip("Production data not available")
        
        context_data = {
            'source': production_subset['proteins'],
            'target': production_subset['entities']
        }
        
        params = {
            'source_key': 'source',
            'target_key': 'target',
            'output_key': 'result',
            # Production-ready parameters
        }
        
        # Execute action
        start_time = time.time()
        result = self.run_action(params, context_data)
        duration = time.time() - start_time
        
        # Assertions
        self.assert_output_valid(result)
        self.assert_performance(duration, max_duration=60.0, level="Level 3")
        
        # Validate against known production characteristics
        output_df = context_data['result']
        
        # Check output is reasonable for production data
        assert len(output_df) > 0, "Should produce output with production data"
        
        # Validate known production data patterns
        # For example, check for expected ID formats
        if 'uniprot_id' in output_df.columns:
            # Check UniProt ID format
            sample_ids = output_df['uniprot_id'].dropna().head(10)
            for id_val in sample_ids:
                assert isinstance(id_val, str), f"Invalid ID type: {type(id_val)}"
                # Add more specific validation as needed
        
        # Log performance metrics for monitoring
        print(f"\nProduction subset performance:")
        print(f"  - Processed {len(production_subset['proteins'])} source records")
        print(f"  - Processed {len(production_subset['entities'])} target records")
        print(f"  - Generated {len(output_df)} matches")
        print(f"  - Duration: {duration:.2f} seconds")
        print(f"  - Rate: {len(output_df) / duration:.0f} matches/second")
    
    def test_level3_known_issues(self, production_subset):
        """Test known production issues are resolved.
        
        Tests for specific issues found in production like Q6EMK4.
        """
        if not production_subset:
            pytest.skip("Production data not available")
        
        # Test Q6EMK4 case if present
        if 'proteins' in production_subset:
            proteins_df = production_subset['proteins']
            
            # Check if problematic ID exists
            if 'uniprot' in proteins_df.columns:
                q6emk4_rows = proteins_df[proteins_df['uniprot'].str.contains('Q6EMK4', na=False)]
                
                if not q6emk4_rows.empty:
                    # Test this specific case
                    context_data = {
                        'source': q6emk4_rows,
                        'target': production_subset['entities']
                    }
                    
                    result = self.run_action(
                        {'source_key': 'source', 'target_key': 'target', 'output_key': 'result'},
                        context_data
                    )
                    
                    assert result.success, "Q6EMK4 case should be handled correctly"
    
    # Performance Comparison Tests
    def test_compare_implementations(self, sample_data, performance_profiler):
        """Compare different implementation approaches."""
        
        test_data = {
            'source': sample_data['proteins'].head(100),
            'target': sample_data['entities'].head(200)
        }
        
        # Define different implementation strategies
        implementations = {
            'baseline': lambda data: self.run_action(
                {'source_key': 'source', 'target_key': 'target', 'output_key': 'result'},
                data
            ),
            # Add alternative implementations to compare
            # 'optimized': lambda data: self.run_optimized_action(data),
        }
        
        # Compare performance
        comparison = performance_profiler.compare_implementations(
            implementations,
            test_data
        )
        
        print("\nImplementation comparison:")
        print(comparison.to_string())
        
        # Assert optimized version is better (when applicable)
        # if 'optimized' in comparison['implementation'].values:
        #     baseline_time = comparison[comparison['implementation'] == 'baseline']['time_ms'].iloc[0]
        #     optimized_time = comparison[comparison['implementation'] == 'optimized']['time_ms'].iloc[0]
        #     assert optimized_time < baseline_time, "Optimized should be faster"
    
    # Regression Tests
    def test_no_performance_regression(self, sample_data, performance_profiler):
        """Ensure no performance regression from baseline."""
        
        # Define baseline performance (in seconds)
        BASELINE_PERFORMANCE = {
            'small': 0.1,   # 100ms for 10 rows
            'medium': 1.0,  # 1s for 100 rows
            'large': 10.0   # 10s for 1000 rows
        }
        
        test_cases = [
            ('small', 10),
            ('medium', 100),
            ('large', 500)
        ]
        
        for name, size in test_cases:
            data = {
                'source': sample_data['proteins'].head(size),
                'target': sample_data['entities'].head(size * 2)
            }
            
            with performance_profiler.profile(name):
                self.run_action(
                    {'source_key': 'source', 'target_key': 'target', 'output_key': 'result'},
                    data
                )
            
            actual_time = performance_profiler.results[name].duration
            max_time = BASELINE_PERFORMANCE[name]
            
            assert actual_time <= max_time * 1.2, (  # Allow 20% variance
                f"Performance regression for {name}: "
                f"{actual_time:.3f}s > {max_time}s baseline"
            )