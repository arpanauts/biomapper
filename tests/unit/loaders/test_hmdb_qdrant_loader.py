"""Unit tests for HMDB Qdrant loader - Written FIRST for TDD."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import time
from typing import List, Dict, Any


class TestHMDBQdrantLoader:
    """Test suite for HMDB Qdrant loader - WRITE THESE TESTS FIRST!"""
    
    @pytest.fixture
    def mock_processor(self):
        """Mock HMDBProcessor for testing."""
        processor = Mock()
        processor.process_batch = AsyncMock()
        processor.process_metabolite_batch = AsyncMock()
        return processor
    
    @pytest.fixture
    def loader(self, mock_processor):
        """Create loader instance with mocked dependencies."""
        with patch('biomapper.loaders.hmdb_qdrant_loader.QdrantClient') as mock_qdrant:
            with patch('biomapper.loaders.hmdb_qdrant_loader.TextEmbedding') as mock_embedding:
                from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader
                
                # Mock the embedding client
                mock_embedding_instance = Mock()
                mock_embedding_instance.embed = Mock(return_value=[[0.1] * 384 for _ in range(100)])
                mock_embedding.return_value = mock_embedding_instance
                
                loader = HMDBQdrantLoader(
                    processor=mock_processor,
                    qdrant_url="localhost:6333"
                )
                return loader
    
    def test_loader_initialization(self, loader):
        """Test loader initializes with correct parameters."""
        assert loader.collection_name == "hmdb_metabolites"
        assert loader.batch_size == 100
        assert loader.embedding_model == "BAAI/bge-small-en-v1.5"
        # This test should FAIL initially
    
    def test_create_search_text_basic(self, loader):
        """Test search text creation from metabolite data."""
        metabolite = {
            'hmdb_id': 'HMDB0000001',
            'name': 'L-Methionine',
            'synonyms': ['Methionine', 'Met'],
            'chemical_formula': 'C5H11NO2S'
        }
        
        search_text = loader._create_search_text(metabolite)
        
        assert 'L-Methionine' in search_text
        assert 'Methionine' in search_text
        assert 'C5H11NO2S' in search_text
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_load_metabolites_processes_batches(self, loader, mock_processor):
        """Test that metabolites are processed in batches."""
        # Setup mock data
        mock_metabolites = [
            {'hmdb_id': f'HMDB{i:07d}', 'name': f'Metabolite {i}'}
            for i in range(250)  # More than 2 batches
        ]
        
        # Configure mock processor to yield batches
        async def mock_batch_generator(batch_size):
            for i in range(0, len(mock_metabolites), batch_size):
                yield mock_metabolites[i:i+batch_size]
        
        mock_processor.process_metabolite_batch = mock_batch_generator
        
        # Run the loader
        await loader.load_metabolites()
        
        # Verify batches were processed
        assert loader.client.upsert.call_count >= 3  # At least 3 batches
        # This test should FAIL initially
    
    def test_create_embedding_text_weights_primary_name(self, loader):
        """Test that primary name is weighted in embedding text."""
        metabolite = {
            'name': 'Cholesterol',
            'synonyms': ['Cholesterin'],
            'iupac_name': '(3β)-cholest-5-en-3-ol'
        }
        
        embedding_text = loader._create_embedding_text(metabolite)
        
        # Primary name should appear multiple times for weighting
        assert embedding_text.count('Cholesterol') >= 2
        # This test should FAIL initially
    
    def test_create_embedding_text_handles_missing_fields(self, loader):
        """Test embedding text creation with missing fields."""
        metabolite = {
            'name': 'Test Compound'
            # No other fields
        }
        
        embedding_text = loader._create_embedding_text(metabolite)
        
        assert 'Test Compound' in embedding_text
        assert len(embedding_text) > 0
        # This test should FAIL initially
    
    def test_create_embedding_text_includes_all_synonyms(self, loader):
        """Test that all synonyms are included in embedding text."""
        metabolite = {
            'name': 'Glucose',
            'synonyms': ['D-Glucose', 'Dextrose', 'Grape sugar', 'Blood sugar'],
            'iupac_name': '(2R,3S,4R,5R)-2,3,4,5,6-Pentahydroxyhexanal',
            'traditional_iupac': 'glucose'
        }
        
        embedding_text = loader._create_embedding_text(metabolite)
        
        # All synonyms should be present
        for synonym in metabolite['synonyms']:
            assert synonym in embedding_text
        
        # IUPAC names should be included
        assert metabolite['iupac_name'] in embedding_text
        assert metabolite['traditional_iupac'] in embedding_text
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_setup_collection_creates_with_correct_config(self, loader):
        """Test collection setup with correct vector configuration."""
        await loader.setup_collection()
        
        # Should delete existing collection
        loader.client.delete_collection.assert_called_once_with("hmdb_metabolites")
        
        # Should create collection with correct params
        create_call = loader.client.create_collection.call_args
        assert create_call[1]['collection_name'] == "hmdb_metabolites"
        
        # Vector config should match BGE model dimensions
        vectors_config = create_call[1]['vectors_config']
        assert vectors_config.size == 384  # BGE-small dimension
        assert vectors_config.distance.name == "COSINE"
        
        # Should create payload index for hmdb_id
        loader.client.create_payload_index.assert_called_once()
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_load_metabolites_handles_errors_gracefully(self, loader, mock_processor):
        """Test error handling during metabolite loading."""
        # Setup processor to yield one good batch and one that causes error
        async def mock_batch_with_error(batch_size):
            yield [{'hmdb_id': 'HMDB0000001', 'name': 'Good Metabolite'}]
            yield [{'hmdb_id': None, 'name': None}]  # Bad data
        
        mock_processor.process_metabolite_batch = mock_batch_with_error
        
        # Should not raise exception
        stats = await loader.load_metabolites()
        
        # Should track errors
        assert stats['total_processed'] == 1
        assert stats['total_errors'] == 1
        # This test should FAIL initially
    
    def test_prepare_qdrant_payload_formats_correctly(self, loader):
        """Test Qdrant payload preparation."""
        metabolite = {
            'hmdb_id': 'HMDB0000122',
            'name': 'D-Glucose',
            'synonyms': ['Glucose', 'Dextrose'],
            'description': 'A simple sugar',
            'chemical_formula': 'C6H12O6',
            'cas_registry_number': '50-99-7'
        }
        
        payload = loader._prepare_qdrant_payload(metabolite)
        
        # Required fields
        assert payload['hmdb_id'] == 'HMDB0000122'
        assert payload['name'] == 'D-Glucose'
        assert payload['synonyms'] == ['Glucose', 'Dextrose']
        
        # Optional fields
        assert payload['description'] == 'A simple sugar'
        assert payload['chemical_formula'] == 'C6H12O6'
        assert payload['cas_registry_number'] == '50-99-7'
        
        # Should not include None values
        assert None not in payload.values()
        # This test should FAIL initially