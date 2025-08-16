"""Base classes for three-level testing approach."""

import pytest
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class ThreeLevelTestBase(ABC):
    """Base class for three-level testing approach.
    
    Implements a standardized testing strategy:
    - Level 1: Unit tests with minimal synthetic data (fast, isolated)
    - Level 2: Integration tests with sample data (moderate size, realistic)
    - Level 3: Smoke tests with production data subset (real data, performance validation)
    """
    
    @abstractmethod
    def test_level1_minimal(self):
        """Level 1: Unit test with minimal synthetic data.
        
        - Tests basic functionality
        - Uses 2-10 rows of synthetic data
        - Should complete in < 1 second
        - Focus on core logic validation
        """
        pass
    
    @abstractmethod
    def test_level2_sample(self):
        """Level 2: Integration test with sample data.
        
        - Tests realistic scenarios
        - Uses 100-1000 rows of representative data
        - Should complete in < 10 seconds
        - Validates edge cases and data variations
        """
        pass
    
    @abstractmethod
    def test_level3_production_subset(self):
        """Level 3: Smoke test with production data subset.
        
        - Tests with actual production data
        - Uses first 1000-5000 rows of real datasets
        - Should complete in < 60 seconds
        - Validates performance and scalability
        """
        pass


class ActionTestBase(ThreeLevelTestBase):
    """Base class for testing biomapper actions with three-level approach."""
    
    ACTION_CLASS = None  # Override in subclass
    
    def get_minimal_data(self) -> Dict[str, pd.DataFrame]:
        """Create minimal synthetic test data for unit tests.
        
        Returns:
            Dictionary with source and target DataFrames containing 2-3 rows
        """
        return {
            'source': pd.DataFrame({
                'id': ['P12345', 'Q67890', 'O11111'],
                'uniprot': ['P12345', 'Q67890', 'O11111'],
                'name': ['Protein 1', 'Protein 2', 'Protein 3'],
                'gene_name': ['GENE1', 'GENE2', 'GENE3']
            }),
            'target': pd.DataFrame({
                'id': ['UniProtKB:P12345', 'NCBIGene:123', 'PR:000001'],
                'name': ['Entity 1', 'Entity 2', 'Entity 3'],
                'xrefs': ['', 'UniProtKB:Q67890||PR:Q67890', 'UniProtKB:O11111'],
                'synonyms': ['P12345', 'Q67890;GENE2', 'O11111;GENE3']
            })
        }
    
    def get_sample_data(self) -> Dict[str, pd.DataFrame]:
        """Load or generate sample data for integration tests.
        
        Returns:
            Dictionary with source and target DataFrames containing 100-1000 rows
        """
        sample_dir = Path('tests/data/samples')
        
        if sample_dir.exists():
            source_file = sample_dir / 'sample_source.csv'
            target_file = sample_dir / 'sample_target.csv'
            
            if source_file.exists() and target_file.exists():
                return {
                    'source': pd.read_csv(source_file),
                    'target': pd.read_csv(target_file)
                }
        
        # Generate sample data if files don't exist
        from .data_generator import BiologicalDataGenerator
        generator = BiologicalDataGenerator()
        
        return {
            'source': generator.generate_test_dataset(500, 'source'),
            'target': generator.generate_test_dataset(800, 'target')
        }
    
    def get_production_subset(self) -> Dict[str, pd.DataFrame]:
        """Load subset of production data for smoke tests.
        
        Returns:
            Dictionary with source and target DataFrames from production data
        """
        production_paths = {
            'source': Path('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv'),
            'target': Path('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv')
        }
        
        # Check if production data exists
        if not all(p.exists() for p in production_paths.values()):
            pytest.skip("Production data not available")
        
        try:
            return {
                'source': pd.read_csv(
                    production_paths['source'],
                    sep='\t',
                    comment='#',
                    nrows=1000
                ),
                'target': pd.read_csv(
                    production_paths['target'],
                    nrows=1000
                )
            }
        except Exception as e:
            pytest.skip(f"Could not load production data: {e}")
    
    def run_action(self, params: Dict[str, Any], context_data: Dict[str, pd.DataFrame]) -> Any:
        """Helper to run action with given params and context.
        
        Args:
            params: Action parameters
            context_data: Dictionary of DataFrames to use as context
            
        Returns:
            Action execution result
        """
        if self.ACTION_CLASS is None:
            raise NotImplementedError("ACTION_CLASS must be set in subclass")
        
        # Create context
        context = {
            'datasets': context_data,
            'statistics': {},
            'output_files': [],
            'current_identifiers': set()
        }
        
        # Initialize action
        action = self.ACTION_CLASS()
        
        # Execute action
        return action.execute(params, context)
    
    def assert_performance(self, duration: float, max_duration: float, level: str):
        """Assert that performance meets expectations.
        
        Args:
            duration: Actual execution time in seconds
            max_duration: Maximum allowed execution time
            level: Test level for context in error message
        """
        assert duration <= max_duration, (
            f"Performance regression in {level}: "
            f"took {duration:.2f}s, expected < {max_duration}s"
        )
    
    def assert_output_valid(self, result: Any, min_matches: int = 0):
        """Common assertions for action output validation.
        
        Args:
            result: Action execution result
            min_matches: Minimum expected number of matches/results
        """
        assert result is not None, "Action returned None"
        assert hasattr(result, 'success'), "Result missing 'success' attribute"
        assert result.success, f"Action failed: {getattr(result, 'message', 'No message')}"
        
        if hasattr(result, 'output_identifiers'):
            assert len(result.output_identifiers) >= min_matches, (
                f"Too few results: {len(result.output_identifiers)} < {min_matches}"
            )