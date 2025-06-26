"""Unit tests for LocalIdConverter action."""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from biomapper.core.strategy_actions.local_id_converter import LocalIdConverter
from biomapper.db.models import Endpoint


class TestLocalIdConverter:
    """Test suite for LocalIdConverter action."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock source and target endpoints."""
        source_endpoint = Mock(spec=Endpoint)
        source_endpoint.name = "source_endpoint"
        
        target_endpoint = Mock(spec=Endpoint)
        target_endpoint.name = "target_endpoint"
        
        return source_endpoint, target_endpoint
    
    @pytest.fixture
    def temp_mapping_file(self):
        """Create a temporary mapping file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as f:
            f.write("uniprot_id\tensembl_id\n")
            f.write("P12345\tENSP001\n")
            f.write("Q67890\tENSP002\n")
            f.write("P12345\tENSP003\n")  # One-to-many mapping
            f.write("R11111\tENSP004\n")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)
    
    @pytest.fixture
    def temp_csv_mapping_file(self):
        """Create a temporary CSV mapping file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("gene_symbol,protein_id\n")
            f.write("TP53,P04637\n")
            f.write("BRCA1,P38398\n")
            f.write("EGFR,P00533\n")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_successful_conversion(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test successful identifier conversion with valid mapping file."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['P12345', 'Q67890', 'X99999'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': temp_mapping_file,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        # Verify results
        assert result['input_identifiers'] == ['P12345', 'Q67890', 'X99999']
        assert set(result['output_identifiers']) == {'ENSP001', 'ENSP002', 'ENSP003'}
        assert result['output_ontology_type'] == 'PROTEIN_ENSEMBL'
        assert len(result['provenance']) == 3  # 2 for P12345, 1 for Q67890
        
        # Check details
        details = result['details']
        assert details['action'] == 'LOCAL_ID_CONVERTER'
        assert details['total_input'] == 3
        assert details['total_mapped'] == 2
        assert details['total_unmapped'] == 1
        assert details['total_output'] == 3
        assert 'X99999' in details['unmapped_identifiers']
    
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, mock_session, mock_endpoints):
        """Test validation of required parameters."""
        source_endpoint, target_endpoint = mock_endpoints
        action = LocalIdConverter(mock_session)
        
        # Test missing mapping_file
        with pytest.raises(ValueError, match="mapping_file parameter is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'source_column': 'uniprot_id',
                    'target_column': 'ensembl_id',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        # Test missing source_column
        with pytest.raises(ValueError, match="source_column parameter is required"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'mapping_file': 'test.csv',
                    'target_column': 'ensembl_id',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_composite_identifier_expansion(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test handling of composite identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Add composite mapping to file
        with open(temp_mapping_file, 'a') as f:
            f.write("Q14213\tENSP005\n")
            f.write("Q8NEV9\tENSP006\n")
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['Q14213_Q8NEV9', 'P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': temp_mapping_file,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL',
                'expand_composites': True
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        # Should map both components of the composite ID
        assert 'ENSP005' in result['output_identifiers']  # From Q14213
        assert 'ENSP006' in result['output_identifiers']  # From Q8NEV9
        assert 'ENSP001' in result['output_identifiers']  # From P12345
        assert result['details']['total_expanded'] > result['details']['total_input']
    
    @pytest.mark.asyncio
    async def test_no_composite_expansion(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test disabling composite identifier expansion."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['Q14213_Q8NEV9', 'P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': temp_mapping_file,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL',
                'expand_composites': False
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        # Composite ID should not be mapped (not in file as-is)
        assert result['details']['total_unmapped'] == 1
        assert result['details']['total_mapped'] == 1  # Only P12345
    
    @pytest.mark.asyncio
    async def test_context_key_usage(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test reading from and writing to context keys."""
        source_endpoint, target_endpoint = mock_endpoints
        
        context = {
            'my_identifiers': ['P12345', 'Q67890']
        }
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['IGNORED'],  # Should be ignored
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': temp_mapping_file,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL',
                'input_context_key': 'my_identifiers',
                'output_context_key': 'converted_ids'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context=context
        )
        
        # Should use identifiers from context
        assert result['input_identifiers'] == ['P12345', 'Q67890']
        assert 'converted_ids' in context
        assert set(context['converted_ids']) == set(result['output_identifiers'])
    
    @pytest.mark.asyncio
    async def test_empty_input_identifiers(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test behavior with empty input identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': temp_mapping_file,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
        assert result['provenance'] == []
        assert result['details']['skipped'] == 'empty_input'
    
    @pytest.mark.asyncio
    async def test_nonexistent_mapping_file(self, mock_session, mock_endpoints):
        """Test error handling for nonexistent mapping file."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = LocalIdConverter(mock_session)
        
        with pytest.raises(ValueError, match="Mapping file not found"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'mapping_file': '/nonexistent/path/mapping.csv',
                    'source_column': 'uniprot_id',
                    'target_column': 'ensembl_id',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_invalid_column_names(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test error handling for invalid column names."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = LocalIdConverter(mock_session)
        
        with pytest.raises(ValueError, match="Source column 'invalid_column' not found"):
            await action.execute(
                current_identifiers=['P12345'],
                current_ontology_type='PROTEIN_UNIPROT',
                action_params={
                    'mapping_file': temp_mapping_file,
                    'source_column': 'invalid_column',
                    'target_column': 'ensembl_id',
                    'output_ontology_type': 'PROTEIN_ENSEMBL'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_csv_delimiter_autodetection(self, mock_session, mock_endpoints, temp_csv_mapping_file):
        """Test automatic delimiter detection for CSV files."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['TP53', 'BRCA1'],
            current_ontology_type='GENE_SYMBOL',
            action_params={
                'mapping_file': temp_csv_mapping_file,
                'source_column': 'gene_symbol',
                'target_column': 'protein_id',
                'output_ontology_type': 'PROTEIN_UNIPROT'
                # No delimiter specified - should auto-detect comma
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        assert set(result['output_identifiers']) == {'P04637', 'P38398'}
        assert result['details']['total_mapped'] == 2
    
    @pytest.mark.asyncio
    async def test_custom_composite_delimiter(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test using a custom composite delimiter."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Add mappings for components
        with open(temp_mapping_file, 'a') as f:
            f.write("ABC\tENSP007\n")
            f.write("DEF\tENSP008\n")
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['ABC|DEF', 'P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': temp_mapping_file,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL',
                'composite_delimiter': '|'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        # Should expand ABC|DEF and map both components
        assert 'ENSP007' in result['output_identifiers']
        assert 'ENSP008' in result['output_identifiers']
    
    @pytest.mark.asyncio
    async def test_environment_variable_expansion(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test expansion of environment variables in file paths."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Set an environment variable
        os.environ['TEST_MAPPING_DIR'] = os.path.dirname(temp_mapping_file)
        mapping_file_with_var = f"${{TEST_MAPPING_DIR}}/{os.path.basename(temp_mapping_file)}"
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['P12345'],
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': mapping_file_with_var,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        # Should successfully resolve the path and perform mapping
        assert result['details']['total_mapped'] == 1
        
        # Cleanup
        del os.environ['TEST_MAPPING_DIR']
    
    @pytest.mark.asyncio
    async def test_provenance_tracking(self, mock_session, mock_endpoints, temp_mapping_file):
        """Test detailed provenance tracking."""
        source_endpoint, target_endpoint = mock_endpoints
        
        action = LocalIdConverter(mock_session)
        
        result = await action.execute(
            current_identifiers=['P12345'],  # Has two mappings
            current_ontology_type='PROTEIN_UNIPROT',
            action_params={
                'mapping_file': temp_mapping_file,
                'source_column': 'uniprot_id',
                'target_column': 'ensembl_id',
                'output_ontology_type': 'PROTEIN_ENSEMBL'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        # Check provenance entries
        assert len(result['provenance']) == 2  # P12345 maps to ENSP001 and ENSP003
        
        for prov in result['provenance']:
            assert prov['action'] == 'LOCAL_ID_CONVERTER'
            assert prov['source_id'] == 'P12345'
            assert prov['source_ontology'] == 'PROTEIN_UNIPROT'
            assert prov['target_ontology'] == 'PROTEIN_ENSEMBL'
            assert prov['method'] == 'local_file_mapping'
            assert prov['confidence'] == 1.0
            assert prov['target_id'] in ['ENSP001', 'ENSP003']