"""
Unit tests for ApiResolver strategy action.

Tests cover all functionality including batching, rate limiting,
retries, and error handling using mocked API responses.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.api_resolver import ApiResolver
from biomapper.db.models import Endpoint


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def mock_endpoints():
    """Create mock source and target endpoints."""
    source = MagicMock(spec=Endpoint)
    source.ontology_type = "UNIPROT"
    
    target = MagicMock(spec=Endpoint)
    target.ontology_type = "HPA"
    
    return source, target


@pytest.fixture
def api_resolver(mock_session):
    """Create an ApiResolver instance."""
    return ApiResolver(mock_session)


def create_mock_response(status=200, json_data=None, text=""):
    """Create a mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.text = AsyncMock(return_value=text)
    
    if json_data is not None:
        mock_resp.json = AsyncMock(return_value=json_data)
    else:
        mock_resp.json = AsyncMock(side_effect=json.JSONDecodeError("No JSON", "", 0))
    
    # Context manager support
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)
    
    return mock_resp


class TestApiResolver:
    """Test cases for ApiResolver strategy action."""
    
    @pytest.mark.asyncio
    async def test_execute_successful_resolution(self, api_resolver, mock_endpoints):
        """Test successful resolution of identifiers."""
        source, target = mock_endpoints
        
        # Set up parameters
        action_params = {
            'input_context_key': 'unresolved_ids',
            'output_context_key': 'resolved_ids',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve/{id}',
            'batch_size': 2,
            'rate_limit_delay': 0.01,
            'response_id_field': 'current_id'
        }
        
        # Set up context
        context = {
            'unresolved_ids': ['OLD001', 'OLD002', 'OLD003']
        }
        
        # Mock session and responses
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        
        # Create mock responses for each ID
        mock_session.get.side_effect = [
            create_mock_response(200, {'current_id': 'NEW001'}),
            create_mock_response(200, {'current_id': 'NEW002'}),
            create_mock_response(200, {'current_id': 'NEW003'})
        ]
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            # Execute action
            result = await api_resolver.execute(
                current_identifiers=['OLD001', 'OLD002', 'OLD003'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        # Verify results
        assert result['input_identifiers'] == ['OLD001', 'OLD002', 'OLD003']
        assert set(result['output_identifiers']) == {'NEW001', 'NEW002', 'NEW003'}
        assert result['output_ontology_type'] == 'UNIPROT'
        assert len(result['provenance']) == 3
        assert all(p['status'] == 'resolved' for p in result['provenance'])
        assert result['details']['total_queried'] == 3
        assert result['details']['total_resolved'] == 3
        assert result['details']['resolution_rate'] == 1.0
        
        # Verify context was updated
        assert set(context['resolved_ids']) == {'NEW001', 'NEW002', 'NEW003'}
    
    @pytest.mark.asyncio
    async def test_execute_with_nested_response_fields(self, api_resolver, mock_endpoints):
        """Test resolution with nested response fields."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/lookup/{id}',
            'response_id_field': 'result.current.accession',
            'response_mapping_field': 'result.history'
        }
        
        context = {'ids': ['Q12345']}
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.return_value = create_mock_response(200, {
            'result': {
                'current': {'accession': 'P67890'},
                'history': {'replaced_by': 'P67890', 'date': '2023-01-01'}
            }
        })
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            result = await api_resolver.execute(
                current_identifiers=['Q12345'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert result['output_identifiers'] == ['P67890']
        assert result['provenance'][0]['resolved_id'] == 'P67890'
        assert result['provenance'][0]['mapping_info'] == {
            'replaced_by': 'P67890',
            'date': '2023-01-01'
        }
    
    @pytest.mark.asyncio
    async def test_execute_with_404_responses(self, api_resolver, mock_endpoints):
        """Test handling of 404 not found responses."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve/{id}'
        }
        
        context = {'ids': ['NOTFOUND1', 'EXISTS1', 'NOTFOUND2']}
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.side_effect = [
            create_mock_response(404),
            create_mock_response(200, {'id': 'RESOLVED1'}),
            create_mock_response(404)
        ]
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            result = await api_resolver.execute(
                current_identifiers=['NOTFOUND1', 'EXISTS1', 'NOTFOUND2'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert result['output_identifiers'] == ['RESOLVED1']
        assert result['details']['total_queried'] == 3
        assert result['details']['total_resolved'] == 1
        
        # Check provenance for different statuses
        provenance_by_id = {p['original_id']: p for p in result['provenance']}
        assert provenance_by_id['NOTFOUND1']['status'] == 'not_found'
        assert provenance_by_id['EXISTS1']['status'] == 'resolved'
        assert provenance_by_id['NOTFOUND2']['status'] == 'not_found'
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_on_errors(self, api_resolver, mock_endpoints):
        """Test retry logic on transient errors."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve/{id}',
            'max_retries': 3,
            'timeout': 1
        }
        
        context = {'ids': ['RETRY1']}
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        
        # Track get calls
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return create_mock_response(500)
            return create_mock_response(200, {'id': 'SUCCESS1'})
        
        mock_session.get.side_effect = side_effect
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            result = await api_resolver.execute(
                current_identifiers=['RETRY1'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert result['output_identifiers'] == ['SUCCESS1']
        assert result['provenance'][0]['status'] == 'resolved'
        assert call_count == 3  # Verify retries were attempted
    
    @pytest.mark.asyncio
    async def test_execute_with_max_retries_exceeded(self, api_resolver, mock_endpoints):
        """Test behavior when max retries are exceeded."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve/{id}',
            'max_retries': 2
        }
        
        context = {'ids': ['ALWAYSFAILS']}
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.return_value = create_mock_response(500)
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            result = await api_resolver.execute(
                current_identifiers=['ALWAYSFAILS'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert result['output_identifiers'] == []
        assert result['provenance'][0]['status'] == 'error'
        assert 'HTTP 500' in result['provenance'][0]['error']
    
    @pytest.mark.asyncio
    async def test_execute_with_rate_limiting(self, api_resolver, mock_endpoints):
        """Test rate limiting between batches."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve/{id}',
            'batch_size': 2,
            'rate_limit_delay': 0.1  # 100ms delay
        }
        
        # Create 5 IDs to ensure multiple batches
        context = {'ids': [f'ID{i}' for i in range(5)]}
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.side_effect = [
            create_mock_response(200, {'id': f'NEW{i}'}) for i in range(5)
        ]
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            import time
            start_time = time.time()
            
            result = await api_resolver.execute(
                current_identifiers=context['ids'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
            
            elapsed_time = time.time() - start_time
        
        # Should have 3 batches: [0,1], [2,3], [4]
        # Rate limit delays: 0 (first batch), 0.1, 0.1 = 0.2 seconds minimum
        assert elapsed_time >= 0.2
        assert len(result['output_identifiers']) == 5
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_input(self, api_resolver, mock_endpoints):
        """Test handling of empty input."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com'
        }
        
        context = {'ids': []}  # Empty list
        
        result = await api_resolver.execute(
            current_identifiers=[],
            current_ontology_type='UNIPROT',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['input_identifiers'] == []
        assert result['output_identifiers'] == []
        assert result['provenance'] == []
        assert result['details']['total_queried'] == 0
        assert result['details']['total_resolved'] == 0
    
    @pytest.mark.asyncio
    async def test_execute_missing_input_key(self, api_resolver, mock_endpoints):
        """Test handling when input key is missing from context."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'missing_key',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com'
        }
        
        context = {'other_key': ['ID1']}
        
        result = await api_resolver.execute(
            current_identifiers=['ID1'],
            current_ontology_type='UNIPROT',
            action_params=action_params,
            source_endpoint=source,
            target_endpoint=target,
            context=context
        )
        
        assert result['input_identifiers'] == ['ID1']
        assert result['output_identifiers'] == ['ID1']
        assert result['details']['total_queried'] == 0
    
    @pytest.mark.asyncio
    async def test_execute_validation_errors(self, api_resolver, mock_endpoints):
        """Test parameter validation errors."""
        source, target = mock_endpoints
        
        # Missing input_context_key
        with pytest.raises(ValueError, match="input_context_key is required"):
            await api_resolver.execute(
                current_identifiers=[],
                current_ontology_type='UNIPROT',
                action_params={'output_context_key': 'out'},
                source_endpoint=source,
                target_endpoint=target,
                context={}
            )
        
        # Missing output_context_key
        with pytest.raises(ValueError, match="output_context_key is required"):
            await api_resolver.execute(
                current_identifiers=[],
                current_ontology_type='UNIPROT',
                action_params={'input_context_key': 'in'},
                source_endpoint=source,
                target_endpoint=target,
                context={}
            )
        
        # Missing api_base_url
        with pytest.raises(ValueError, match="api_base_url is required"):
            await api_resolver.execute(
                current_identifiers=[],
                current_ontology_type='UNIPROT',
                action_params={
                    'input_context_key': 'in',
                    'output_context_key': 'out'
                },
                source_endpoint=source,
                target_endpoint=target,
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_request_params(self, api_resolver, mock_endpoints):
        """Test passing additional request parameters."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve',
            'request_params': {
                'format': 'json',
                'include_history': 'true'
            }
        }
        
        context = {'ids': ['TEST1']}
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.return_value = create_mock_response(200, {'id': 'RESOLVED1'})
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            result = await api_resolver.execute(
                current_identifiers=['TEST1'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert result['output_identifiers'] == ['RESOLVED1']
        # Verify request params were passed
        mock_session.get.assert_called_with(
            'https://api.example.com/resolve',
            params={'format': 'json', 'include_history': 'true'},
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_connection_error(self, api_resolver, mock_endpoints):
        """Test handling of connection errors."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve/{id}',
            'max_retries': 2
        }
        
        context = {'ids': ['CONN_ERROR']}
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.side_effect = ConnectionError("Connection refused")
        
        with patch.object(api_resolver, '_get_session', return_value=mock_session):
            result = await api_resolver.execute(
                current_identifiers=['CONN_ERROR'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        assert result['output_identifiers'] == []
        assert result['provenance'][0]['status'] == 'error'
        assert 'Connection refused' in result['provenance'][0]['error']
    
    @pytest.mark.asyncio
    async def test_extract_field_method(self, api_resolver):
        """Test the _extract_field helper method."""
        # Test simple field
        data = {'id': 'TEST123'}
        assert api_resolver._extract_field(data, 'id') == 'TEST123'
        
        # Test nested field
        data = {'result': {'current': {'id': 'NESTED123'}}}
        assert api_resolver._extract_field(data, 'result.current.id') == 'NESTED123'
        
        # Test array index
        data = {'results': [{'id': 'FIRST'}, {'id': 'SECOND'}]}
        assert api_resolver._extract_field(data, 'results.0.id') == 'FIRST'
        assert api_resolver._extract_field(data, 'results.1.id') == 'SECOND'
        
        # Test missing field
        data = {'id': 'TEST'}
        assert api_resolver._extract_field(data, 'missing.field') is None
        
        # Test invalid array index
        data = {'results': [{'id': 'ONLY_ONE'}]}
        assert api_resolver._extract_field(data, 'results.5.id') is None
        
        # Test empty path
        data = {'id': 'TEST'}
        assert api_resolver._extract_field(data, '') == data
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, api_resolver, mock_endpoints):
        """Test that HTTP session is properly created and closed."""
        source, target = mock_endpoints
        
        action_params = {
            'input_context_key': 'ids',
            'output_context_key': 'resolved',
            'api_base_url': 'https://api.example.com',
            'endpoint_path': '/resolve/{id}'
        }
        
        context = {'ids': ['TEST1']}
        
        # Verify session starts as None
        assert api_resolver._session is None
        
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.return_value = create_mock_response(200, {'id': 'RESOLVED1'})
        mock_session.close = AsyncMock()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            await api_resolver.execute(
                current_identifiers=['TEST1'],
                current_ontology_type='UNIPROT',
                action_params=action_params,
                source_endpoint=source,
                target_endpoint=target,
                context=context
            )
        
        # Verify session is closed after execution
        assert api_resolver._session is None
        mock_session.close.assert_called_once()