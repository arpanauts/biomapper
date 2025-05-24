"""
Unit tests for the MVP0 Pipeline Orchestrator.

This module contains comprehensive unit tests for the PipelineOrchestrator class,
testing configuration validation, component integration, error handling, and
the complete pipeline execution flow.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict

from biomapper.mvp0_pipeline.pipeline_orchestrator import PipelineOrchestrator, create_orchestrator
from biomapper.mvp0_pipeline.pipeline_config import PipelineConfig
from biomapper.schemas.pipeline_schema import (
    PipelineMappingResult, 
    BatchMappingResult, 
    PipelineStatus
)
from biomapper.schemas.mvp0_schema import QdrantSearchResultItem, PubChemAnnotation
from biomapper.mvp0_pipeline.llm_mapper import LLMChoice


class TestPipelineOrchestrator:
    """Test suite for PipelineOrchestrator class."""
    
    @pytest.fixture
    def valid_config(self):
        """Create a valid PipelineConfig for testing."""
        return PipelineConfig(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test_collection",
            qdrant_api_key=None,
            anthropic_api_key="test-api-key",
            llm_model_name="claude-3-sonnet-20240229",
            pubchem_max_concurrent_requests=5,
            pipeline_batch_size=10,
            pipeline_timeout_seconds=300
        )
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock QdrantClient."""
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.QdrantClient') as mock:
            client_instance = Mock()
            client_instance.get_collection.return_value = Mock()
            mock.return_value = client_instance
            yield mock
    
    def test_init_successful(self, valid_config, mock_qdrant_client):
        """Test successful orchestrator initialization."""
        orchestrator = PipelineOrchestrator(valid_config)
        assert orchestrator.config == valid_config
        mock_qdrant_client.assert_called_once()
    
    def test_init_missing_api_key(self, mock_qdrant_client):
        """Test initialization fails with missing API key."""
        config = PipelineConfig(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test_collection",
            anthropic_api_key=""  # Empty API key
        )
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            PipelineOrchestrator(config)
    
    def test_init_missing_qdrant_url(self, mock_qdrant_client):
        """Test initialization fails with missing Qdrant URL."""
        config = PipelineConfig(
            qdrant_url="",  # Empty URL
            qdrant_collection_name="test_collection",
            anthropic_api_key="test-key"
        )
        
        with pytest.raises(ValueError, match="Qdrant URL is required"):
            PipelineOrchestrator(config)
    
    def test_init_qdrant_connection_error(self, valid_config):
        """Test initialization fails when Qdrant is not reachable."""
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.QdrantClient') as mock:
            mock.side_effect = Exception("Connection refused")
            
            with pytest.raises(ConnectionError, match="Failed to connect to Qdrant"):
                PipelineOrchestrator(valid_config)
    
    @pytest.mark.asyncio
    async def test_run_single_mapping_success(self, valid_config, mock_qdrant_client):
        """Test successful single mapping execution."""
        # Mock Qdrant search results
        mock_qdrant_results = [
            QdrantSearchResultItem(cid=5793, score=0.95),
            QdrantSearchResultItem(cid=107526, score=0.88)
        ]
        
        # Mock PubChem annotations
        mock_annotations = {
            5793: PubChemAnnotation(
                cid=5793,
                title="Glucose",
                iupac_name="(2R,3S,4R,5R)-2,3,4,5,6-Pentahydroxyhexanal",
                molecular_formula="C6H12O6",
                synonyms=["D-Glucose", "Dextrose"]
            ),
            107526: PubChemAnnotation(
                cid=107526,
                title="beta-D-Glucopyranose",
                molecular_formula="C6H12O6"
            )
        }
        
        # Mock LLM choice
        mock_llm_choice = LLMChoice(
            selected_cid=5793,
            llm_confidence=0.95,
            llm_rationale="Direct title match with common synonym 'glucose'"
        )
        
        # Patch component functions
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name', 
                   new_callable=AsyncMock) as mock_qdrant_search, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.fetch_pubchem_annotations',
                   new_callable=AsyncMock) as mock_pubchem, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.select_best_cid_with_llm',
                   new_callable=AsyncMock) as mock_llm:
            
            mock_qdrant_search.return_value = mock_qdrant_results
            mock_pubchem.return_value = mock_annotations
            mock_llm.return_value = mock_llm_choice
            
            orchestrator = PipelineOrchestrator(valid_config)
            result = await orchestrator.run_single_mapping("glucose")
            
            # Verify result
            assert result.status == PipelineStatus.SUCCESS
            assert result.selected_cid == 5793
            assert result.confidence == "High"
            assert result.rationale == "Direct title match with common synonym 'glucose'"
            assert result.qdrant_results == mock_qdrant_results
            assert result.pubchem_annotations == mock_annotations
            assert result.llm_choice == mock_llm_choice
            
            # Verify component calls
            mock_qdrant_search.assert_called_once_with(
                biochemical_name="glucose",
                top_k=10  # pipeline_batch_size
            )
            mock_pubchem.assert_called_once_with([5793, 107526])
            mock_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_single_mapping_no_qdrant_hits(self, valid_config, mock_qdrant_client):
        """Test mapping with no Qdrant hits."""
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant_search:
            
            mock_qdrant_search.return_value = []  # No results
            
            orchestrator = PipelineOrchestrator(valid_config)
            result = await orchestrator.run_single_mapping("unknown_compound")
            
            assert result.status == PipelineStatus.NO_QDRANT_HITS
            assert result.selected_cid is None
            assert result.error_message == "No similar compounds found in Qdrant vector database"
            assert result.qdrant_results == []
    
    @pytest.mark.asyncio
    async def test_run_single_mapping_insufficient_annotations(self, valid_config, mock_qdrant_client):
        """Test mapping with Qdrant hits but no PubChem annotations."""
        mock_qdrant_results = [
            QdrantSearchResultItem(cid=12345, score=0.85)
        ]
        
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant_search, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.fetch_pubchem_annotations',
                   new_callable=AsyncMock) as mock_pubchem:
            
            mock_qdrant_search.return_value = mock_qdrant_results
            mock_pubchem.return_value = {}  # No annotations
            
            orchestrator = PipelineOrchestrator(valid_config)
            result = await orchestrator.run_single_mapping("test_compound")
            
            assert result.status == PipelineStatus.INSUFFICIENT_ANNOTATIONS
            assert result.selected_cid is None
            assert "Failed to retrieve annotations" in result.error_message
    
    @pytest.mark.asyncio
    async def test_run_single_mapping_llm_no_match(self, valid_config, mock_qdrant_client):
        """Test mapping where LLM finds no suitable match."""
        mock_qdrant_results = [QdrantSearchResultItem(cid=12345, score=0.75)]
        mock_annotations = {
            12345: PubChemAnnotation(cid=12345, title="Some compound")
        }
        mock_llm_choice = LLMChoice(
            selected_cid=None,
            llm_confidence=0.2,
            llm_rationale="No suitable match found among candidates"
        )
        
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant_search, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.fetch_pubchem_annotations',
                   new_callable=AsyncMock) as mock_pubchem, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.select_best_cid_with_llm',
                   new_callable=AsyncMock) as mock_llm:
            
            mock_qdrant_search.return_value = mock_qdrant_results
            mock_pubchem.return_value = mock_annotations
            mock_llm.return_value = mock_llm_choice
            
            orchestrator = PipelineOrchestrator(valid_config)
            result = await orchestrator.run_single_mapping("test_compound")
            
            assert result.status == PipelineStatus.LLM_NO_MATCH
            assert result.selected_cid is None
            assert result.rationale == "No suitable match found among candidates"
    
    @pytest.mark.asyncio
    async def test_run_single_mapping_qdrant_error(self, valid_config, mock_qdrant_client):
        """Test handling of Qdrant component error."""
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant_search:
            
            mock_qdrant_search.side_effect = Exception("Qdrant connection timeout")
            
            orchestrator = PipelineOrchestrator(valid_config)
            result = await orchestrator.run_single_mapping("test_compound")
            
            assert result.status == PipelineStatus.COMPONENT_ERROR_QDRANT
            assert "Qdrant search error" in result.error_message
            assert "Qdrant connection timeout" in result.error_message
    
    @pytest.mark.asyncio
    async def test_run_single_mapping_pubchem_error(self, valid_config, mock_qdrant_client):
        """Test handling of PubChem component error."""
        mock_qdrant_results = [QdrantSearchResultItem(cid=12345, score=0.85)]
        
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant_search, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.fetch_pubchem_annotations',
                   new_callable=AsyncMock) as mock_pubchem:
            
            mock_qdrant_search.return_value = mock_qdrant_results
            mock_pubchem.side_effect = Exception("PubChem API rate limit exceeded")
            
            orchestrator = PipelineOrchestrator(valid_config)
            result = await orchestrator.run_single_mapping("test_compound")
            
            assert result.status == PipelineStatus.COMPONENT_ERROR_PUBCHEM
            assert "PubChem annotation error" in result.error_message
            assert "rate limit exceeded" in result.error_message
    
    @pytest.mark.asyncio
    async def test_run_single_mapping_llm_error(self, valid_config, mock_qdrant_client):
        """Test handling of LLM component error."""
        mock_qdrant_results = [QdrantSearchResultItem(cid=12345, score=0.85)]
        mock_annotations = {12345: PubChemAnnotation(cid=12345, title="Test")}
        
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant_search, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.fetch_pubchem_annotations',
                   new_callable=AsyncMock) as mock_pubchem, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.select_best_cid_with_llm',
                   new_callable=AsyncMock) as mock_llm:
            
            mock_qdrant_search.return_value = mock_qdrant_results
            mock_pubchem.return_value = mock_annotations
            mock_llm.side_effect = Exception("LLM API error")
            
            orchestrator = PipelineOrchestrator(valid_config)
            result = await orchestrator.run_single_mapping("test_compound")
            
            assert result.status == PipelineStatus.COMPONENT_ERROR_LLM
            assert "LLM mapping error" in result.error_message
    
    @pytest.mark.asyncio
    async def test_run_pipeline_batch(self, valid_config, mock_qdrant_client):
        """Test batch pipeline processing."""
        # Create different results for different inputs
        test_names = ["glucose", "unknown_compound", "caffeine"]
        
        with patch.object(PipelineOrchestrator, 'run_single_mapping', 
                         new_callable=AsyncMock) as mock_single:
            
            # Mock different results
            mock_results = [
                PipelineMappingResult(
                    input_biochemical_name="glucose",
                    status=PipelineStatus.SUCCESS,
                    selected_cid=5793,
                    confidence="High"
                ),
                PipelineMappingResult(
                    input_biochemical_name="unknown_compound",
                    status=PipelineStatus.NO_QDRANT_HITS,
                    error_message="No similar compounds found"
                ),
                PipelineMappingResult(
                    input_biochemical_name="caffeine",
                    status=PipelineStatus.SUCCESS,
                    selected_cid=2519,
                    confidence="Medium"
                )
            ]
            
            mock_single.side_effect = mock_results
            
            orchestrator = PipelineOrchestrator(valid_config)
            batch_result = await orchestrator.run_pipeline(test_names)
            
            # Verify batch result
            assert batch_result.total_processed == 3
            assert batch_result.successful_mappings == 2
            assert batch_result.failed_mappings == 0  # NO_QDRANT_HITS is not a failure
            assert len(batch_result.results) == 3
            assert batch_result.get_success_rate() == pytest.approx(66.67, rel=0.01)
            
            # Verify sequential processing
            assert mock_single.call_count == 3
            mock_single.assert_any_call("glucose")
            mock_single.assert_any_call("unknown_compound")
            mock_single.assert_any_call("caffeine")
    
    @pytest.mark.asyncio
    async def test_run_pipeline_empty_list(self, valid_config, mock_qdrant_client):
        """Test batch pipeline with empty input list."""
        orchestrator = PipelineOrchestrator(valid_config)
        batch_result = await orchestrator.run_pipeline([])
        
        assert batch_result.total_processed == 0
        assert batch_result.successful_mappings == 0
        assert batch_result.failed_mappings == 0
        assert len(batch_result.results) == 0
        assert batch_result.get_success_rate() == 0.0
    
    def test_create_orchestrator_factory(self, valid_config, mock_qdrant_client):
        """Test the create_orchestrator factory function."""
        orchestrator = create_orchestrator(valid_config)
        assert isinstance(orchestrator, PipelineOrchestrator)
        assert orchestrator.config == valid_config
    
    def test_create_orchestrator_from_env(self, mock_qdrant_client):
        """Test factory function creating config from environment."""
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.create_pipeline_config') as mock_create_config:
            mock_config = Mock(spec=PipelineConfig)
            mock_config.anthropic_api_key = "test-key"
            mock_config.qdrant_url = "http://localhost:6333"
            mock_config.qdrant_collection_name = "test"
            mock_create_config.return_value = mock_config
            
            orchestrator = create_orchestrator()
            assert isinstance(orchestrator, PipelineOrchestrator)
            mock_create_config.assert_called_once()


class TestPipelineIntegration:
    """Integration tests for component interactions."""
    
    @pytest.mark.asyncio
    async def test_data_flow_between_components(self):
        """Test that data flows correctly between components."""
        # This test verifies the data contracts between components
        config = PipelineConfig(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test",
            anthropic_api_key="test-key"
        )
        
        # Mock the component functions to verify data flow
        mock_qdrant_results = [
            QdrantSearchResultItem(cid=5793, score=0.95),
            QdrantSearchResultItem(cid=107526, score=0.88)
        ]
        
        mock_annotations = {
            5793: PubChemAnnotation(cid=5793, title="Glucose"),
            107526: PubChemAnnotation(cid=107526, title="beta-D-Glucopyranose")
        }
        
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.QdrantClient'), \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.fetch_pubchem_annotations',
                   new_callable=AsyncMock) as mock_pubchem, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.select_best_cid_with_llm',
                   new_callable=AsyncMock) as mock_llm:
            
            mock_qdrant.return_value = mock_qdrant_results
            mock_pubchem.return_value = mock_annotations
            
            # Verify that LLM receives correctly formatted data
            def verify_llm_input(name, candidates, api_key):
                assert name == "glucose"
                assert len(candidates) == 2
                assert all(hasattr(c, 'cid') and hasattr(c, 'qdrant_score') 
                          and hasattr(c, 'annotations') for c in candidates)
                assert api_key == "test-key"
                return LLMChoice(selected_cid=5793, llm_confidence=0.95)
            
            mock_llm.side_effect = verify_llm_input
            
            orchestrator = PipelineOrchestrator(config)
            result = await orchestrator.run_single_mapping("glucose")
            
            # Verify the complete data flow
            assert result.status == PipelineStatus.SUCCESS
            assert result.selected_cid == 5793
            
            # Verify component calls with correct data
            mock_qdrant.assert_called_once()
            mock_pubchem.assert_called_once_with([5793, 107526])
            mock_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_processing_time_tracking(self):
        """Test that processing times are correctly tracked."""
        config = PipelineConfig(
            qdrant_url="http://localhost:6333",
            qdrant_collection_name="test",
            anthropic_api_key="test-key"
        )
        
        with patch('biomapper.mvp0_pipeline.pipeline_orchestrator.QdrantClient'), \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.search_qdrant_for_biochemical_name',
                   new_callable=AsyncMock) as mock_qdrant, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.fetch_pubchem_annotations',
                   new_callable=AsyncMock) as mock_pubchem, \
             patch('biomapper.mvp0_pipeline.pipeline_orchestrator.select_best_cid_with_llm',
                   new_callable=AsyncMock) as mock_llm:
            
            # Add delays to simulate processing time
            async def delayed_qdrant_search(*args, **kwargs):
                await asyncio.sleep(0.1)
                return [QdrantSearchResultItem(cid=123, score=0.9)]
            
            async def delayed_pubchem_fetch(*args, **kwargs):
                await asyncio.sleep(0.2)
                return {123: PubChemAnnotation(cid=123, title="Test")}
            
            async def delayed_llm_call(*args, **kwargs):
                await asyncio.sleep(0.15)
                return LLMChoice(selected_cid=123, llm_confidence=0.9)
            
            mock_qdrant.side_effect = delayed_qdrant_search
            mock_pubchem.side_effect = delayed_pubchem_fetch
            mock_llm.side_effect = delayed_llm_call
            
            orchestrator = PipelineOrchestrator(config)
            result = await orchestrator.run_single_mapping("test")
            
            # Verify timing information is present
            assert "qdrant_search_time" in result.processing_details
            assert "pubchem_annotation_time" in result.processing_details
            assert "llm_decision_time" in result.processing_details
            assert "total_time" in result.processing_details
            
            # Verify times are reasonable
            assert result.processing_details["qdrant_search_time"] >= 0.1
            assert result.processing_details["pubchem_annotation_time"] >= 0.2
            assert result.processing_details["llm_decision_time"] >= 0.15
            assert result.processing_details["total_time"] >= 0.45


if __name__ == "__main__":
    pytest.main([__file__, "-v"])