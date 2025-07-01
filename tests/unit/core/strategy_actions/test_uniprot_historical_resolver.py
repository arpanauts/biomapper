"""
Tests for UniProtHistoricalResolver action.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from biomapper.core.strategy_actions.uniprot_historical_resolver import UniProtHistoricalResolver
from biomapper.db.models import Endpoint


class TestUniProtHistoricalResolver:
    """Test cases for UniProtHistoricalResolver action."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def action(self, mock_session):
        """Create a UniProtHistoricalResolver instance."""
        return UniProtHistoricalResolver(session=mock_session)
    
    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoint objects."""
        source = MagicMock(spec=Endpoint)
        source.name = "SOURCE_ENDPOINT"
        
        target = MagicMock(spec=Endpoint)
        target.name = "TARGET_ENDPOINT"
        
        return source, target
    
    @pytest.fixture
    def mock_resolver_client(self):
        """Create a mock UniProt resolver client."""
        client = AsyncMock()
        return client
    
    async def test_basic_resolution(self, action, mock_endpoints, mock_resolver_client):
        """Test basic identifier resolution."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Mock the resolver client
        mock_resolver_client.map_identifiers.return_value = {
            'P12345': (['P67890'], 'secondary:P67890'),
            'Q99999': (['Q11111', 'Q22222'], 'demerged'),
            'P00000': ([], 'obsolete')
        }
        
        with patch.object(action, '_get_resolver_client', return_value=mock_resolver_client):
            result = await action.execute(
                current_identifiers=['P12345', 'Q99999', 'P00000'],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'output_ontology_type': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'include_obsolete': False
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        assert result['output_identifiers'] == ['P67890', 'Q11111', 'Q22222']
        assert len(result['provenance']) == 3  # One for P67890, two for Q11111/Q22222
        assert result['details']['total_resolved'] == 2  # P12345 and Q99999 resolved
        assert result['details']['resolution_statistics']['obsolete'] == 0  # Not included
    
    async def test_context_input_output(self, action, mock_endpoints, mock_resolver_client):
        """Test reading from and writing to context."""
        source_endpoint, target_endpoint = mock_endpoints
        context = {
            'old_ids': ['P12345', 'Q99999']
        }
        
        mock_resolver_client.map_identifiers.return_value = {
            'P12345': (['P67890'], 'primary'),
            'Q99999': (['Q11111'], 'secondary:Q11111')
        }
        
        with patch.object(action, '_get_resolver_client', return_value=mock_resolver_client):
            result = await action.execute(
                current_identifiers=[],  # Should be ignored
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'input_context_key': 'old_ids',
                    'output_context_key': 'resolved_ids',
                    'output_ontology_type': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context=context
            )
        
        assert context['resolved_ids'] == ['P67890', 'Q11111']
        assert result['input_identifiers'] == ['P12345', 'Q99999']
        assert result['output_identifiers'] == ['P67890', 'Q11111']
    
    async def test_composite_id_handling(self, action, mock_endpoints, mock_resolver_client):
        """Test handling of composite identifiers."""
        source_endpoint, target_endpoint = mock_endpoints
        
        mock_resolver_client.map_identifiers.return_value = {
            'P12345': (['P67890'], 'primary'),
            'Q99999': (['Q11111'], 'secondary:Q11111')
        }
        
        with patch.object(action, '_get_resolver_client', return_value=mock_resolver_client):
            result = await action.execute(
                current_identifiers=['P12345_Q99999'],  # Composite ID
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'output_ontology_type': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'expand_composites': True,
                    'composite_delimiter': '_'
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        assert set(result['output_identifiers']) == {'P67890', 'Q11111'}
        assert result['details']['total_input'] == 1
        assert result['details']['total_expanded'] == 2
    
    async def test_include_obsolete(self, action, mock_endpoints, mock_resolver_client):
        """Test including obsolete identifiers in output."""
        source_endpoint, target_endpoint = mock_endpoints
        
        mock_resolver_client.map_identifiers.return_value = {
            'P12345': (['P67890'], 'primary'),
            'P00000': ([], 'obsolete')
        }
        
        with patch.object(action, '_get_resolver_client', return_value=mock_resolver_client):
            result = await action.execute(
                current_identifiers=['P12345', 'P00000'],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'output_ontology_type': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'include_obsolete': True
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        assert result['output_identifiers'] == ['P67890']  # Obsolete IDs not in output
        assert len(result['provenance']) == 2  # But included in provenance
        assert result['details']['resolution_statistics']['obsolete'] == 1
    
    async def test_batch_processing(self, action, mock_endpoints, mock_resolver_client):
        """Test batch processing of large identifier lists."""
        source_endpoint, target_endpoint = mock_endpoints
        
        # Create 250 test IDs
        test_ids = [f'P{i:05d}' for i in range(250)]
        
        # Mock responses for all batches
        async def mock_map_identifiers(batch):
            return {id: ([f'Q{id[1:]}'], 'primary') for id in batch}
        
        mock_resolver_client.map_identifiers.side_effect = mock_map_identifiers
        
        with patch.object(action, '_get_resolver_client', return_value=mock_resolver_client):
            result = await action.execute(
                current_identifiers=test_ids,
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'output_ontology_type': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'batch_size': 100  # Should result in 3 batches
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        assert len(result['output_identifiers']) == 250
        assert mock_resolver_client.map_identifiers.call_count == 3  # 3 batches
    
    async def test_empty_input(self, action, mock_endpoints):
        """Test handling of empty input."""
        source_endpoint, target_endpoint = mock_endpoints
        
        result = await action.execute(
            current_identifiers=[],
            current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
            action_params={
                'output_ontology_type': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY'
            },
            source_endpoint=source_endpoint,
            target_endpoint=target_endpoint,
            context={}
        )
        
        assert result['output_identifiers'] == []
        assert result['details']['status'] == 'skipped'
        assert result['details']['reason'] == 'empty_input'
    
    async def test_confidence_scores(self, action, mock_endpoints, mock_resolver_client):
        """Test confidence score assignment based on resolution type."""
        source_endpoint, target_endpoint = mock_endpoints
        
        mock_resolver_client.map_identifiers.return_value = {
            'P11111': (['P11111'], 'primary'),
            'P22222': (['P33333'], 'secondary:P33333'),
            'P44444': (['P55555', 'P66666'], 'demerged'),
            'P77777': ([], 'obsolete')
        }
        
        with patch.object(action, '_get_resolver_client', return_value=mock_resolver_client):
            result = await action.execute(
                current_identifiers=['P11111', 'P22222', 'P44444', 'P77777'],
                current_ontology_type='PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                action_params={
                    'output_ontology_type': 'PROTEIN_UNIPROTKB_AC_ONTOLOGY',
                    'include_obsolete': True
                },
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                context={}
            )
        
        # Check confidence scores in provenance
        confidence_map = {p['source_id']: p['confidence'] for p in result['provenance']}
        
        assert confidence_map['P11111'] == 1.0  # Primary
        assert confidence_map['P22222'] == 0.9  # Secondary
        assert confidence_map['P77777'] == 0.0  # Obsolete
        
        # Demerged should have two entries, both with 0.8
        demerged_confidences = [p['confidence'] for p in result['provenance'] if p['source_id'] == 'P44444']
        assert all(c == 0.8 for c in demerged_confidences)
        assert len(demerged_confidences) == 2