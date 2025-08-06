import pytest
from unittest.mock import Mock, AsyncMock, patch
from biomapper.core.strategy_actions.cts_enriched_match import (
    CtsEnrichedMatchAction,
    CtsEnrichedMatchParams,
    EnrichmentMetrics
)


class TestCtsEnrichedMatch:
    """Test suite for CTS-enriched matching - WRITE FIRST!"""
    
    @pytest.fixture
    def action(self):
        """Create action instance."""
        return CtsEnrichedMatchAction()
    
    @pytest.fixture
    def mock_cts_client(self):
        """Mock CTS client."""
        client = Mock()
        client.initialize = AsyncMock()
        client.close = AsyncMock()
        client.convert = AsyncMock()
        return client
    
    @pytest.fixture
    def unmatched_arivale_data(self):
        """Unmatched metabolites from baseline."""
        return [
            {
                'BIOCHEMICAL_NAME': '12,13-DiHOME',
                'HMDB': 'HMDB04705',
                'KEGG': '',
                'PUBCHEM': '9966640'
            },
            {
                'BIOCHEMICAL_NAME': 'S-1-pyrroline-5-carboxylate',
                'HMDB': '',
                'KEGG': 'C03564',
                'PUBCHEM': ''
            },
            {
                'BIOCHEMICAL_NAME': '1-methylnicotinamide',
                'HMDB': 'HMDB0000699',
                'KEGG': 'C02918',
                'PUBCHEM': '457'
            }
        ]
    
    @pytest.fixture
    def nightingale_reference(self):
        """Target Nightingale reference."""
        return [
            {'unified_name': '12,13-dihydroxy-9Z-octadecenoic acid', 'nightingale_id': 'ng-100'},
            {'unified_name': 'Pyrroline carboxylate', 'nightingale_id': 'ng-101'},
            {'unified_name': 'N-Methylnicotinamide', 'nightingale_id': 'ng-102'},
            {'unified_name': 'Glucose', 'nightingale_id': 'ng-003'}
        ]
    
    @pytest.mark.asyncio
    async def test_cts_client_initialization(self, action):
        """Test CTS client is properly initialized."""
        config = {'rate_limit_per_second': 5}
        
        with patch('biomapper.core.strategy_actions.cts_enriched_match.CTSClient') as mock_cts:
            mock_instance = Mock()
            mock_instance.initialize = AsyncMock()
            mock_cts.return_value = mock_instance
            
            await action._initialize_cts_client(config)
            
            mock_cts.assert_called_once_with(config)
            mock_instance.initialize.assert_called_once()
            assert action.cts_client is not None
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_metabolite_enrichment(self, action, mock_cts_client, unmatched_arivale_data):
        """Test metabolite enrichment with CTS API."""
        action.cts_client = mock_cts_client
        
        # Mock CTS responses
        async def mock_convert(identifier, from_type, to_type):
            responses = {
                ('HMDB04705', 'HMDB'): ['12,13-dihydroxy-9Z-octadecenoic acid', '12,13-DiHOME'],
                ('9966640', 'PUBCHEM'): ['12,13-dihydroxy-9Z-octadecenoic acid'],
                ('C03564', 'KEGG'): ['1-pyrroline-5-carboxylate', 'pyrroline carboxylate'],
                ('HMDB0000699', 'HMDB'): ['N-methylnicotinamide', '1-methylnicotinamide'],
                ('C02918', 'KEGG'): ['N-methylnicotinamide'],
                ('457', 'PUBCHEM'): ['1-methylnicotinamide']
            }
            return responses.get((identifier, from_type), [])
        
        mock_cts_client.convert.side_effect = mock_convert
        
        enriched, api_calls = await action._enrich_metabolites(
            unmatched_arivale_data,
            ['HMDB', 'KEGG', 'PUBCHEM'],
            batch_size=10
        )
        
        assert len(enriched) == 3
        assert api_calls > 0
        
        # Check first metabolite enrichment
        first = enriched[0]
        assert 'cts_enriched_names' in first
        assert '12,13-dihydroxy-9Z-octadecenoic acid' in first['cts_enriched_names']
        assert 'HMDB' in first['cts_successful_ids']
        # This test should FAIL initially
    
    def test_fuzzy_match_with_enriched_names(self, action, nightingale_reference):
        """Test fuzzy matching using enriched names."""
        enriched_metabolite = {
            'BIOCHEMICAL_NAME': '12,13-DiHOME',
            'cts_enriched_names': [
                '12,13-dihydroxy-9Z-octadecenoic acid',
                '12,13-DiHOME'
            ],
            'cts_successful_ids': ['HMDB', 'PUBCHEM']
        }
        
        match = action._fuzzy_match_enriched(
            enriched_metabolite,
            nightingale_reference,
            'unified_name',
            0.80
        )
        
        assert match is not None
        assert match['score'] >= 0.80
        assert match['enrichment_used'] is True
        assert '12,13-dihydroxy' in match['matched_name']
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_full_enrichment_workflow(
        self,
        action,
        mock_cts_client,
        unmatched_arivale_data,
        nightingale_reference
    ):
        """Test complete enrichment and matching workflow."""
        action.cts_client = mock_cts_client
        
        # Mock CTS to return useful names
        async def mock_convert(identifier, from_type, to_type):
            if identifier == 'HMDB0000699':
                return ['N-methylnicotinamide', 'methylnicotinamide']
            elif identifier == 'C02918':
                return ['N-methylnicotinamide']
            return []
        
        mock_cts_client.convert.side_effect = mock_convert
        
        params = CtsEnrichedMatchParams(
            unmatched_dataset_key="unmatched",
            target_dataset_key="reference",
            identifier_columns=['HMDB', 'KEGG', 'PUBCHEM'],
            output_key="api_matches",
            track_metrics=True
        )
        
        context = {
            'datasets': {
                'unmatched': unmatched_arivale_data,
                'reference': nightingale_reference
            }
        }
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        # Check that the result was successful by examining details
        assert result.details['matched_count'] > 0
        assert 'metrics' in result.details
        matches = context['datasets']['api_matches']
        
        # Should match at least methylnicotinamide
        assert len(matches) >= 1
        matched_sources = {m['source']['BIOCHEMICAL_NAME'] for m in matches}
        assert '1-methylnicotinamide' in matched_sources
        
        # Check metrics
        assert 'metrics' in context
        metrics = context['metrics']['api_enriched']
        assert metrics['total_enriched'] > 0
        assert metrics['api_calls_made'] > 0
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_no_enrichment_possible(self, action, mock_cts_client):
        """Test handling when no enrichment is possible."""
        action.cts_client = mock_cts_client
        mock_cts_client.convert.return_value = []  # No results
        
        metabolites = [
            {'BIOCHEMICAL_NAME': 'unknown-x', 'HMDB': '', 'KEGG': '', 'PUBCHEM': ''}
        ]
        
        enriched, api_calls = await action._enrich_metabolites(
            metabolites,
            ['HMDB', 'KEGG'],
            batch_size=10
        )
        
        assert len(enriched) == 1
        assert enriched[0]['cts_enriched_names'] == []
        assert enriched[0]['enrichment_source'] == 'none'
        assert api_calls == 0  # No valid identifiers to convert
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, action, mock_cts_client):
        """Test comprehensive metrics are tracked."""
        action.cts_client = mock_cts_client
        mock_cts_client.convert.return_value = ['test-name']
        
        params = CtsEnrichedMatchParams(
            unmatched_dataset_key="unmatched",
            target_dataset_key="reference",
            identifier_columns=['HMDB'],
            output_key="matches",
            track_metrics=True
        )
        
        context = {
            'datasets': {
                'unmatched': [
                    {'BIOCHEMICAL_NAME': 'test', 'HMDB': 'HMDB0001'}
                ],
                'reference': [
                    {'unified_name': 'test-name'}
                ]
            }
        }
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="metabolite",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        metrics = context['metrics']['api_enriched']
        assert metrics['stage'] == 'api_enriched'
        assert metrics['total_unmatched_input'] == 1
        assert metrics['total_enriched'] == 1
        assert metrics['enrichment_rate'] == 1.0
        assert 'identifier_coverage' in metrics
        assert 'HMDB' in metrics['identifier_coverage']
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_partial_identifier_coverage(self, action, mock_cts_client):
        """Test tracking which identifiers successfully convert."""
        action.cts_client = mock_cts_client
        
        # Only HMDB returns results
        async def mock_convert(identifier, from_type, to_type):
            if from_type == 'HMDB':
                return ['metabolite-name']
            return []
        
        mock_cts_client.convert.side_effect = mock_convert
        
        metabolites = [
            {'HMDB': 'HMDB001', 'KEGG': 'C001', 'PUBCHEM': '123'},
            {'HMDB': 'HMDB002', 'KEGG': '', 'PUBCHEM': '456'},
            {'HMDB': '', 'KEGG': 'C003', 'PUBCHEM': ''}
        ]
        
        enriched, _ = await action._enrich_metabolites(
            metabolites,
            ['HMDB', 'KEGG', 'PUBCHEM'],
            batch_size=10
        )
        
        # Check successful IDs tracked
        assert enriched[0]['cts_successful_ids'] == ['HMDB']
        assert enriched[1]['cts_successful_ids'] == ['HMDB']
        assert enriched[2]['cts_successful_ids'] == []
        # This test should FAIL initially