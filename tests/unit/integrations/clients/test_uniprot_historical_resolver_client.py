"""Tests for UniProt historical resolver client."""

import pytest
import asyncio
import aiohttp
import responses
from unittest.mock import patch, AsyncMock

from src.integrations.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient
from src.core.exceptions import ClientExecutionError


def mock_aiohttp_session(mock_response_data, status=200, error_text=None):
    """Helper function to mock aiohttp session responses."""
    def mock_aiohttp(*args, **kwargs):  # Accept any arguments like the real session.get
        mock_context_manager = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = status
        if error_text:
            mock_response_obj.text.return_value = error_text
        else:
            mock_response_obj.json.return_value = mock_response_data
        mock_context_manager.__aenter__.return_value = mock_response_obj
        return mock_context_manager
    return mock_aiohttp


class TestUniProtHistoricalResolverClient:
    """Test UniProtHistoricalResolverClient functionality."""
    
    @pytest.fixture
    def client_config(self):
        """Create test client configuration."""
        return {
            "base_url": "https://rest.uniprot.org/uniprotkb/search",
            "timeout": 30,
            "cache_size": 1000
        }
    
    @pytest.fixture
    def client(self, client_config):
        """Create test client instance."""
        return UniProtHistoricalResolverClient(
            config=client_config,
            cache_size=100,
            timeout=10
        )
    
    @pytest.fixture
    def sample_uniprot_ids(self):
        """Create sample UniProt identifiers."""
        return [
            "P04637",      # TP53_HUMAN (valid current ID)
            "P38398",      # BRCA1_HUMAN (valid current ID)
            "Q99895",      # Historical ID that maps to P01308 (insulin)
            "P0CG05",      # Demerged ID (should map to multiple entries)
            "OBSOLETE123", # Obsolete ID that no longer exists
            "INVALID_ID"   # Invalid format
        ]
    
    @pytest.fixture
    def real_world_uniprot_ids(self):
        """Real-world UniProt identifiers for testing."""
        return [
            "P04637",  # TP53_HUMAN (Tumor protein p53)
            "P38398",  # BRCA1_HUMAN (BRCA1 protein)
            "P01730",  # CD4_HUMAN (CD4 antigen)
            "Q6EMK4",  # Problematic identifier from biomapper context
            "P12345",  # Potentially obsolete test ID
            "INVALID_ID"  # Invalid format
        ]
    
    def test_client_initialization(self, client_config):
        """Test successful client initialization."""
        client = UniProtHistoricalResolverClient(
            config=client_config,
            cache_size=500,
            timeout=15
        )
        
        assert client._config == client_config
        assert client._cache_size == 500
        assert client.timeout == 15
        assert client._initialized is True
        assert hasattr(client, 'semaphore')
        assert client.semaphore._value == 5  # Default concurrent requests limit
    
    def test_client_initialization_with_defaults(self):
        """Test client initialization with default values."""
        client = UniProtHistoricalResolverClient()
        
        assert client._config == {}
        assert client._cache_size == 10000  # Default cache size
        assert client.timeout == 30  # Default timeout
        assert client.base_url == "https://rest.uniprot.org/uniprotkb/search"
    
    @pytest.mark.asyncio
    async def test_fetch_uniprot_search_results_successful(self, client):
        """Test successful UniProt API request."""
        # Mock successful API response
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P04637",
                    "secondaryAccessions": ["Q99895"],
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "TP53"}}]
                }
            ]
        }
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession.get', mock_aiohttp_session(mock_response)):
            result = await client._fetch_uniprot_search_results("accession:P04637")
            
            assert result == mock_response
            assert len(result["results"]) == 1
            assert result["results"][0]["primaryAccession"] == "P04637"
    
    @pytest.mark.asyncio
    async def test_fetch_uniprot_search_results_api_error(self, client):
        """Test UniProt API error handling."""
        # Mock aiohttp session for error response
        with patch('aiohttp.ClientSession.get', mock_aiohttp_session(None, status=400, error_text="Invalid request")):
            with pytest.raises(ClientExecutionError) as exc_info:
                await client._fetch_uniprot_search_results("invalid_query")
            
            assert "UniProt API error" in str(exc_info.value)
            assert "Status 400" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fetch_uniprot_search_results_timeout(self, client):
        """Test UniProt API timeout handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(ClientExecutionError) as exc_info:
                await client._fetch_uniprot_search_results("test_query")
            
            assert "Timeout" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fetch_uniprot_search_results_http_error(self, client):
        """Test UniProt API HTTP error handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Connection failed")
            
            with pytest.raises(ClientExecutionError) as exc_info:
                await client._fetch_uniprot_search_results("test_query")
            
            assert "HTTP Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_check_as_secondary_accessions(self, client):
        """Test checking IDs as secondary accessions."""
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P01308",
                    "secondaryAccessions": ["Q99895", "P12345"]
                },
                {
                    "primaryAccession": "P04637", 
                    "secondaryAccessions": ["Q12345"]
                }
            ]
        }
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_context_manager = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json.return_value = mock_response
            mock_context_manager.__aenter__.return_value = mock_response_obj
            mock_get.return_value = mock_context_manager
            
            test_ids = ["Q99895", "P12345", "Q12345", "NOT_FOUND"]
            result = await client._check_as_secondary_accessions(test_ids)
            
            expected_result = {
                "Q99895": ["P01308"],
                "P12345": ["P01308"],
                "Q12345": ["P04637"],
                "NOT_FOUND": []
            }
            
            assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_check_as_primary_accessions(self, client):
        """Test checking IDs as primary accessions."""
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P04637"
                },
                {
                    "primaryAccession": "P38398"
                }
            ]
        }
        
        # Mock aiohttp session
        with patch('aiohttp.ClientSession.get', mock_aiohttp_session(mock_response)):
            test_ids = ["P04637", "P38398", "NOT_PRIMARY"]
            result = await client._check_as_primary_accessions(test_ids)
            
            expected_result = {
                "P04637": True,
                "P38398": True,
                "NOT_PRIMARY": False
            }
            
            assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_resolve_batch_with_mixed_ids(self, client):
        """Test resolving a batch with mixed ID types."""
        with patch.object(client, '_check_as_secondary_accessions') as mock_secondary:
            with patch.object(client, '_check_as_primary_accessions') as mock_primary:
                # Mock secondary check results
                mock_secondary.return_value = {
                    "Q99895": ["P01308"],  # Secondary ID
                    "P04637": [],          # Not secondary
                    "INVALID": []          # Not secondary
                }
                
                # Mock primary check results  
                mock_primary.return_value = {
                    "P04637": True,    # Is primary
                    "INVALID": False   # Not primary
                }
                
                test_ids = ["Q99895", "P04637", "INVALID"]
                result = await client._resolve_batch(test_ids)
                
                # Verify Q99895 is resolved as secondary
                assert result["Q99895"]["is_secondary"] is True
                assert result["Q99895"]["primary_ids"] == ["P01308"]
                assert result["Q99895"]["found"] is True
                
                # Verify P04637 is resolved as primary
                assert result["P04637"]["is_primary"] is True
                assert result["P04637"]["primary_ids"] == ["P04637"]
                assert result["P04637"]["found"] is True
                
                # Verify INVALID is marked as obsolete
                assert result["INVALID"]["is_obsolete"] is True
                assert result["INVALID"]["primary_ids"] == []
                assert result["INVALID"]["found"] is False
    
    def test_preprocess_ids_composite_splitting(self, client):
        """Test preprocessing of composite identifiers."""
        # Test comma-separated IDs
        result = client._preprocess_ids(["P04637,P38398,Q6EMK4"])
        assert set(result) == {"P04637", "P38398", "Q6EMK4"}
        
        # Test underscore-separated IDs
        result = client._preprocess_ids(["P04637_P38398"])
        assert set(result) == {"P04637", "P38398"}
        
        # Test mixed separators
        result = client._preprocess_ids(["P04637,P38398_Q6EMK4"])
        assert set(result) == {"P04637", "P38398", "Q6EMK4"}
        
        # Test single ID (no splitting)
        result = client._preprocess_ids(["P04637"])
        assert result == ["P04637"]
        
        # Test empty and whitespace handling
        result = client._preprocess_ids(["P04637, , P38398"])
        assert set(result) == {"P04637", "P38398"}
    
    @pytest.mark.asyncio
    async def test_map_identifiers_successful_request(self, client, sample_uniprot_ids):
        """Test successful identifier mapping."""
        # Mock the entire resolution process using patch
        with patch.object(client, '_resolve_batch') as mock_resolve:
            mock_resolve.return_value = {
                "P04637": {
                    "found": True, "is_primary": True, "is_secondary": False, "is_obsolete": False,
                    "primary_ids": ["P04637"], "organism": None, "gene_names": []
                },
                "P38398": {
                    "found": True, "is_primary": True, "is_secondary": False, "is_obsolete": False,
                    "primary_ids": ["P38398"], "organism": None, "gene_names": []
                },
                "Q99895": {
                    "found": True, "is_primary": False, "is_secondary": True, "is_obsolete": False,
                    "primary_ids": ["P01308"], "organism": None, "gene_names": []
                }
            }
            
            test_ids = ["P04637", "P38398", "Q99895"]
            result = await client.map_identifiers(test_ids)
            
            # Verify successful mapping
            assert result["P04637"][0] == ["P04637"]  # Primary ID maps to itself
            assert result["P04637"][1] == "primary"
            
            assert result["P38398"][0] == ["P38398"]  # Primary ID maps to itself  
            assert result["P38398"][1] == "primary"
            
            assert result["Q99895"][0] == ["P01308"]  # Secondary maps to primary
            assert result["Q99895"][1] == "secondary:P01308"
    
    @pytest.mark.asyncio
    async def test_map_identifiers_api_error_handling(self, client, sample_uniprot_ids):
        """Test mapping with API error handling."""
        # Mock API error response
        with patch('aiohttp.ClientSession.get', mock_aiohttp_session(None, status=503, error_text="Service unavailable")):
            test_ids = ["P04637"]
            result = await client.map_identifiers(test_ids)
            
            # Should handle error gracefully and return error status
            assert result["P04637"][0] is None
            assert "error:batch_processing_failed" in result["P04637"][1]
    
    @pytest.mark.asyncio
    async def test_map_identifiers_caching_behavior(self, client):
        """Test caching behavior during identifier mapping."""
        with patch.object(client, '_resolve_batch') as mock_resolve:
            mock_resolve.return_value = {
                "P04637": {
                    "found": True,
                    "is_primary": True,
                    "is_secondary": False,
                    "is_obsolete": False,
                    "primary_ids": ["P04637"],
                    "organism": None,
                    "gene_names": []
                }
            }
            
            # First call should hit the API
            result1 = await client.map_identifiers(["P04637"])
            assert mock_resolve.call_count == 1
            assert result1["P04637"][0] == ["P04637"]
            
            # Second call should use cache
            result2 = await client.map_identifiers(["P04637"])
            assert mock_resolve.call_count == 1  # No additional API call
            assert result2["P04637"][0] == ["P04637"]
    
    @pytest.mark.asyncio
    async def test_map_identifiers_bypass_cache(self, client):
        """Test bypassing cache during identifier mapping."""
        with patch.object(client, '_resolve_batch') as mock_resolve:
            mock_resolve.return_value = {
                "P04637": {
                    "found": True,
                    "is_primary": True,
                    "is_secondary": False,
                    "is_obsolete": False,
                    "primary_ids": ["P04637"],
                    "organism": None,
                    "gene_names": []
                }
            }
            
            # First call
            await client.map_identifiers(["P04637"])
            assert mock_resolve.call_count == 1
            
            # Second call with bypass_cache should hit API again
            config = {"bypass_cache": True}
            await client.map_identifiers(["P04637"], config=config)
            assert mock_resolve.call_count == 2  # Additional API call made
    
    @pytest.mark.asyncio
    async def test_map_identifiers_batch_processing(self, client):
        """Test batch processing optimization."""
        # Create large ID list to trigger batching
        large_id_list = [f"P{i:05d}" for i in range(150)]  # 150 IDs, should create 3 batches
        
        with patch.object(client, '_resolve_batch') as mock_batch:
            mock_batch.return_value = {}  # Empty result for simplicity
            
            await client.map_identifiers(large_id_list)
            
            # Should split into 3 batches (50 IDs each by default)
            assert mock_batch.call_count == 3
            
            # Verify batch sizes
            call_args_list = mock_batch.call_args_list
            assert len(call_args_list[0][0][0]) == 50  # First batch
            assert len(call_args_list[1][0][0]) == 50  # Second batch
            assert len(call_args_list[2][0][0]) == 50  # Third batch
    
    @pytest.mark.asyncio
    async def test_map_identifiers_composite_id_handling(self, client):
        """Test handling of composite identifiers."""
        with patch.object(client, '_resolve_batch') as mock_resolve:
            # Mock results for individual components
            mock_resolve.return_value = {
                "P04637": {
                    "found": True,
                    "is_primary": True,
                    "is_secondary": False,
                    "is_obsolete": False,
                    "primary_ids": ["P04637"],
                    "organism": None,
                    "gene_names": []
                },
                "P38398": {
                    "found": True,
                    "is_primary": True,
                    "is_secondary": False,
                    "is_obsolete": False,
                    "primary_ids": ["P38398"],
                    "organism": None,
                    "gene_names": []
                }
            }
            
            # Test composite ID
            composite_id = "P04637,P38398"
            result = await client.map_identifiers([composite_id])
            
            # Should aggregate results from both components
            assert composite_id in result
            mapped_ids = result[composite_id][0]
            assert set(mapped_ids) == {"P04637", "P38398"}
            assert "composite:resolved" in result[composite_id][1]
    
    @pytest.mark.asyncio
    async def test_reverse_map_identifiers_not_supported(self, client):
        """Test that reverse mapping is not supported."""
        with pytest.raises(NotImplementedError) as exc_info:
            await client.reverse_map_identifiers(["P04637"])
        
        assert "does not support reverse_map_identifiers" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @responses.activate
    async def test_real_world_uniprot_resolution(self, client, real_world_uniprot_ids):
        """Test UniProt resolution with real-world identifiers."""
        # Mock realistic UniProt response
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P04637",
                    "secondaryAccessions": []
                },
                {
                    "primaryAccession": "P38398", 
                    "secondaryAccessions": []
                },
                {
                    "primaryAccession": "P01730",
                    "secondaryAccessions": []
                },
                {
                    "primaryAccession": "Q6EMK4",
                    "secondaryAccessions": []
                }
            ]
        }
        
        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_response,
            status=200
        )
        
        # Add second response for secondary accession check (empty results)
        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json={"results": []},
            status=200
        )
        
        valid_ids = ["P04637", "P38398", "P01730", "Q6EMK4"]
        result = await client.map_identifiers(valid_ids)
        
        # Verify real-world IDs are handled correctly
        assert result["P04637"][0] == ["P04637"]  # TP53 mapped
        assert result["P38398"][0] == ["P38398"]  # BRCA1 mapped
        assert result["P01730"][0] == ["P01730"]  # CD4 mapped
        assert result["Q6EMK4"][0] == ["Q6EMK4"]  # Problematic ID handled
    
    @pytest.mark.asyncio
    async def test_invalid_id_format_handling(self, client):
        """Test handling of invalid UniProt ID formats."""
        invalid_ids = [
            "INVALID_FORMAT",
            "123456",  # Numbers only
            "",        # Empty string
            None,      # None value
            "P",       # Too short
            "P123456789012345"  # Too long
        ]
        
        # Filter out None for the actual call
        filtered_ids = [id for id in invalid_ids if id is not None]
        
        with patch.object(client, '_resolve_batch') as mock_resolve:
            # Mock should receive only valid format IDs after validation
            mock_resolve.return_value = {}
            
            result = await client.map_identifiers(filtered_ids)
            
            # All invalid IDs should be marked as obsolete or error
            for id in filtered_ids:
                if id:  # Skip empty strings
                    assert result[id][0] is None  # No mapping found
                    assert "obsolete" in result[id][1] or "error" in result[id][1]


class TestUniProtClientPerformance:
    """Test UniProt client performance characteristics."""
    
    @pytest.fixture
    def performance_client(self):
        """Create client configured for performance testing."""
        return UniProtHistoricalResolverClient(
            cache_size=10000,
            timeout=60  # Longer timeout for large requests
        )
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_batch_performance(self, performance_client):
        """Test performance with large batches of identifiers."""
        large_id_list = [f"P{i:05d}" for i in range(1000)]
        
        with patch.object(performance_client, '_resolve_batch') as mock_batch:
            mock_batch.return_value = {
                id: {
                    "found": True,
                    "is_primary": True,
                    "is_secondary": False,
                    "is_obsolete": False,
                    "primary_ids": [id],
                    "organism": None,
                    "gene_names": []
                } for id in large_id_list[:50]  # Mock first batch only
            }
            
            import time
            start_time = time.time()
            
            result = await performance_client.map_identifiers(large_id_list)
            
            execution_time = time.time() - start_time
            
            # Performance assertions
            assert execution_time < 30.0  # Should complete efficiently
            assert len(result) == 1000  # All IDs processed
            
            # Verify batching occurred
            assert mock_batch.call_count > 1  # Multiple batches processed
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self, performance_client):
        """Test that caching provides performance improvement."""
        test_ids = ["P04637", "P38398", "Q6EMK4"]
        
        with patch.object(performance_client, '_resolve_batch') as mock_batch:
            mock_batch.return_value = {
                id: {
                    "found": True,
                    "is_primary": True,
                    "is_secondary": False,
                    "is_obsolete": False,
                    "primary_ids": [id],
                    "organism": None,
                    "gene_names": []
                } for id in test_ids
            }
            
            import time
            
            # First call (cache miss)
            start_time = time.time()
            await performance_client.map_identifiers(test_ids)
            first_call_time = time.time() - start_time
            
            # Second call (cache hit)
            start_time = time.time()
            await performance_client.map_identifiers(test_ids)
            second_call_time = time.time() - start_time
            
            # Cache should provide speedup (more reasonable expectation)
            assert second_call_time < first_call_time  # Cache should be faster
            assert mock_batch.call_count == 1  # Only one actual API call
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, performance_client):
        """Test that concurrent requests are properly limited."""
        # Test that semaphore limits concurrent requests
        assert performance_client.semaphore._value == 5  # Default limit
        
        # Verify semaphore is used in API calls
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value={"results": []})
            
            # Should not exceed semaphore limit
            await performance_client._fetch_uniprot_search_results("test_query")
            
            # Verify semaphore is acquired/released properly
            assert performance_client.semaphore._value == 5  # Back to original value


class TestBiologicalDataIntegration:
    """Test integration with realistic biological data patterns."""
    
    @pytest.fixture
    def client_config(self):
        """Create test client configuration."""
        return {
            "base_url": "https://rest.uniprot.org/uniprotkb/search",
            "timeout": 30,
            "cache_size": 1000
        }
    
    @pytest.fixture
    def client(self, client_config):
        """Create test client instance."""
        return UniProtHistoricalResolverClient(
            config=client_config,
            cache_size=100,
            timeout=10
        )
    
    @pytest.fixture
    def biological_test_data(self):
        """Create realistic biological test data."""
        return {
            "primary_accessions": [
                "P04637",  # TP53_HUMAN (Tumor protein p53)
                "P38398",  # BRCA1_HUMAN (BRCA1 protein)
                "P01730",  # CD4_HUMAN (CD4 antigen)
                "P68871",  # HBB_HUMAN (Hemoglobin beta)
            ],
            "secondary_accessions": [
                "Q99895",  # Maps to P01308 (insulin)
                "P12345",  # Example secondary accession
            ],
            "demerged_accessions": [
                "P0CG05",  # Example demerged ID
            ],
            "obsolete_accessions": [
                "OBSOLETE123",
                "DEPRECATED456"
            ],
            "problematic_cases": [
                "Q6EMK4",  # Known problematic case from biomapper
                "",        # Empty string
                "INVALID_FORMAT"
            ]
        }
    
    @pytest.mark.asyncio
    async def test_biological_data_patterns(self, client, biological_test_data):
        """Test handling of realistic biological data patterns."""
        # Use mocking similar to other successful tests
        with patch.object(client, '_resolve_batch') as mock_resolve:
            # Mock results for biological data testing
            mock_results = {}
            
            # Mock primary accessions
            for primary_id in biological_test_data["primary_accessions"]:
                mock_results[primary_id] = {
                    "found": True,
                    "is_primary": True,
                    "is_secondary": False,
                    "is_obsolete": False,
                    "primary_ids": [primary_id],
                    "organism": None,
                    "gene_names": []
                }
            
            # Mock secondary accession (Q99895 maps to P01308)
            mock_results["Q99895"] = {
                "found": True,
                "is_primary": False,
                "is_secondary": True,
                "is_obsolete": False,
                "primary_ids": ["P01308"],
                "organism": None,
                "gene_names": []
            }
            
            mock_resolve.return_value = mock_results
            
            # Test with mixed biological data
            all_test_ids = (
                biological_test_data["primary_accessions"] +
                biological_test_data["secondary_accessions"][:1]  # Just one secondary for simplicity
            )
            
            result = await client.map_identifiers(all_test_ids)
            
            # Verify biological data handling
            for primary_id in biological_test_data["primary_accessions"]:
                assert result[primary_id][0] == [primary_id]
                assert result[primary_id][1] == "primary"
            
            # Verify secondary mapping
            assert result["Q99895"][0] == ["P01308"]
            assert result["Q99895"][1] == "secondary:P01308"
    
    @pytest.mark.asyncio
    async def test_protein_family_mapping_patterns(self, client):
        """Test mapping patterns common in protein families."""
        # Simulate protein family members with various ID types
        protein_family_ids = [
            "P68871",  # HBB_HUMAN (beta globin)
            "P69905",  # HBA_HUMAN (alpha globin)
            "Q87654",  # Hypothetical family member (secondary)
            "P12345,P67890"  # Composite ID from database export
        ]
        
        with patch.object(client, '_resolve_batch') as mock_resolve:
            mock_resolve.return_value = {
                "P68871": {
                    "found": True, "is_primary": True, "is_secondary": False, "is_obsolete": False,
                    "primary_ids": ["P68871"], "organism": None, "gene_names": []
                },
                "P69905": {
                    "found": True, "is_primary": True, "is_secondary": False, "is_obsolete": False,
                    "primary_ids": ["P69905"], "organism": None, "gene_names": []
                },
                "Q87654": {
                    "found": True, "is_primary": False, "is_secondary": True, "is_obsolete": False,
                    "primary_ids": ["P68871"], "organism": None, "gene_names": []
                },
                "P12345": {
                    "found": True, "is_primary": True, "is_secondary": False, "is_obsolete": False,
                    "primary_ids": ["P12345"], "organism": None, "gene_names": []
                },
                "P67890": {
                    "found": True, "is_primary": True, "is_secondary": False, "is_obsolete": False,
                    "primary_ids": ["P67890"], "organism": None, "gene_names": []
                }
            }
            
            result = await client.map_identifiers(protein_family_ids)
            
            # Verify protein family mapping results
            assert result["P68871"][1] == "primary"
            assert result["P69905"][1] == "primary"
            assert result["Q87654"][1] == "secondary:P68871"
            
            # Verify composite ID handling
            composite_result = result["P12345,P67890"]
            assert set(composite_result[0]) == {"P12345", "P67890"}
            assert "composite:resolved" in composite_result[1]