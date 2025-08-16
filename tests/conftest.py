"""
Global pytest configuration and shared fixtures.
"""
import sys
import json
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock


# Mock the PydanticEncoder for tests
class PydanticEncoder(json.JSONEncoder):
    """Mock encoder that handles additional types"""

    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


# Add to module scope
sys.modules["biomapper.utils.json_utils"] = MagicMock()
sys.modules["biomapper.utils.json_utils"].PydanticEncoder = PydanticEncoder


# Three-level testing fixtures
@pytest.fixture(scope='session')
def minimal_data():
    """Minimal synthetic data for unit tests (Level 1).
    
    Returns small, controlled datasets for fast unit testing.
    """
    return {
        'proteins': pd.DataFrame({
            'uniprot': ['P12345', 'Q67890', 'O11111'],
            'gene_name': ['GENE1', 'GENE2', 'GENE3'],
            'name': ['Protein A', 'Protein B', 'Protein C'],
            'organism': ['Homo sapiens', 'Homo sapiens', 'Mus musculus']
        }),
        'entities': pd.DataFrame({
            'id': ['UniProtKB:P12345', 'NCBIGene:123', 'PR:Q67890', 'ENSEMBL:ENSP00000'],
            'name': ['Entity 1', 'Entity 2', 'Entity 3', 'Entity 4'],
            'xrefs': ['', 'UniProtKB:Q67890||PR:Q67890', 'UniProtKB:O11111', 'UniProtKB:P12345||UniProtKB:Q67890'],
            'synonyms': ['P12345', 'Q67890;GENE2', 'O11111;GENE3', 'P12345;GENE1']
        }),
        'metabolites': pd.DataFrame({
            'id': ['HMDB0000001', 'CHEBI:12345', 'KEGG:C00001'],
            'name': ['Metabolite 1', 'Metabolite 2', 'Water'],
            'formula': ['C6H12O6', 'C10H16N5O13P3', 'H2O'],
            'mass': [180.156, 507.181, 18.015]
        })
    }


@pytest.fixture(scope='session')
def sample_data():
    """Sample data (100-1000 rows) for integration tests (Level 2).
    
    Loads pre-generated sample data or creates it if not available.
    """
    sample_dir = Path('tests/data/samples')
    
    # Try to load existing sample data
    if sample_dir.exists():
        proteins_file = sample_dir / 'sample_proteins.csv'
        entities_file = sample_dir / 'sample_entities.csv'
        metabolites_file = sample_dir / 'sample_metabolites.csv'
        
        if proteins_file.exists() and entities_file.exists():
            return {
                'proteins': pd.read_csv(proteins_file),
                'entities': pd.read_csv(entities_file),
                'metabolites': pd.read_csv(metabolites_file) if metabolites_file.exists() else pd.DataFrame()
            }
    
    # Generate sample data if files don't exist
    from biomapper.testing.data_generator import BiologicalDataGenerator
    generator = BiologicalDataGenerator()
    
    return {
        'proteins': generator.generate_test_dataset(500, 'source'),
        'entities': generator.generate_test_dataset(800, 'target'),
        'metabolites': generator.generate_test_dataset(300, 'metabolite')
    }


@pytest.fixture(scope='session')
def production_subset():
    """First 1000 rows of production data for smoke tests (Level 3).
    
    Loads actual production data if available, skips tests if not.
    """
    production_paths = {
        'proteins': Path('/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv'),
        'entities': Path('/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2.10.2c_ontologies/kg2c_proteins.csv'),
        'metabolites': Path('/procedure/data/local_data/ARIVALE_SNAPSHOTS/metabolomics_metadata.tsv')
    }
    
    # Check if at least core production data exists
    if not production_paths['proteins'].exists() or not production_paths['entities'].exists():
        pytest.skip("Production data not available - skipping Level 3 tests")
    
    try:
        data = {}
        
        # Load proteins data
        if production_paths['proteins'].exists():
            data['proteins'] = pd.read_csv(
                production_paths['proteins'],
                sep='\t',
                comment='#',
                nrows=1000
            )
        
        # Load entities data
        if production_paths['entities'].exists():
            data['entities'] = pd.read_csv(
                production_paths['entities'],
                nrows=1000
            )
        
        # Load metabolites data if available
        if production_paths['metabolites'].exists():
            data['metabolites'] = pd.read_csv(
                production_paths['metabolites'],
                sep='\t',
                comment='#',
                nrows=1000
            )
        else:
            data['metabolites'] = pd.DataFrame()
        
        return data
        
    except Exception as e:
        pytest.skip(f"Could not load production data: {e}")


@pytest.fixture(scope='session')
def edge_cases_data():
    """Edge case datasets for comprehensive testing.
    
    Returns datasets with known problematic patterns.
    """
    from biomapper.testing.data_generator import BiologicalDataGenerator
    return BiologicalDataGenerator.generate_edge_cases()


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test outputs.
    
    Automatically cleaned up after test completion.
    """
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def performance_profiler():
    """Performance profiler for benchmarking tests."""
    from biomapper.testing.performance import PerformanceProfiler
    return PerformanceProfiler()


@pytest.fixture
def mock_context():
    """Mock execution context for action testing."""
    return {
        'datasets': {},
        'statistics': {},
        'output_files': [],
        'current_identifiers': set(),
        'parameters': {}
    }
