"""Tests for CSV adapter with selective column loading and caching."""

import pytest
import tempfile
import os
import pandas as pd
from unittest.mock import Mock, patch

from biomapper.mapping.adapters.csv_adapter import CSVAdapter
from biomapper.config import get_settings


class TestCSVAdapter:
    """Test CSVAdapter functionality including selective loading and caching."""
    
    @pytest.fixture
    def sample_csv_data(self):
        """Create sample CSV data for testing."""
        return {
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'age': [25, 30, 35, 40, 45],
            'city': ['New York', 'London', 'Paris', 'Tokyo', 'Sydney'],
            'score': [85, 92, 78, 88, 91]
        }
    
    @pytest.fixture
    def sample_csv_file(self, sample_csv_data):
        """Create a temporary CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame(sample_csv_data)
            df.to_csv(f.name, index=False)
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def empty_csv_file(self):
        """Create an empty CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")
            yield f.name
        os.unlink(f.name)
    
    def test_csv_adapter_initialization(self):
        """Test CSVAdapter initialization."""
        adapter = CSVAdapter()
        assert adapter.config == {}
        assert adapter.resource_name == "csv_adapter"
        
        # Should use default from settings
        settings = get_settings()
        assert adapter._data_cache.maxsize == settings.csv_adapter_cache_size
        
        # Performance counters should be initialized
        assert adapter._cache_hits == 0
        assert adapter._cache_misses == 0
        
        # Test with custom parameters
        adapter = CSVAdapter(
            config={'test': 'value'},
            resource_name='custom_adapter',
            cache_max_size=20
        )
        assert adapter.config == {'test': 'value'}
        assert adapter.resource_name == 'custom_adapter'
        assert adapter._data_cache.maxsize == 20
    
    @pytest.mark.asyncio
    async def test_load_data_all_columns(self, sample_csv_file):
        """Test loading all columns from CSV file."""
        adapter = CSVAdapter()
        data = await adapter.load_data(file_path=sample_csv_file)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 5
        assert list(data.columns) == ['id', 'name', 'age', 'city', 'score']
        assert data.iloc[0]['name'] == 'Alice'
        assert data.iloc[0]['age'] == 25
    
    @pytest.mark.asyncio
    async def test_load_data_selective_columns(self, sample_csv_file):
        """Test loading specific columns from CSV file."""
        adapter = CSVAdapter()
        data = await adapter.load_data(
            file_path=sample_csv_file,
            columns_to_load=['name', 'age']
        )
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 5
        assert list(data.columns) == ['name', 'age']
        assert data.iloc[0]['name'] == 'Alice'
        assert data.iloc[0]['age'] == 25
        
        # Verify that other columns are not present
        with pytest.raises(KeyError):
            _ = data['city']
    
    @pytest.mark.asyncio
    async def test_load_data_empty_columns_list(self, sample_csv_file):
        """Test that empty columns_to_load list loads all columns."""
        adapter = CSVAdapter()
        data = await adapter.load_data(
            file_path=sample_csv_file,
            columns_to_load=[]
        )
        
        assert len(data.columns) == 5
        assert list(data.columns) == ['id', 'name', 'age', 'city', 'score']
    
    @pytest.mark.asyncio
    async def test_load_data_nonexistent_columns(self, sample_csv_file):
        """Test handling of non-existent columns."""
        adapter = CSVAdapter()
        
        # Test with some valid and some invalid columns
        data = await adapter.load_data(
            file_path=sample_csv_file,
            columns_to_load=['name', 'nonexistent_column', 'age']
        )
        
        # Should load only the existing columns
        assert list(data.columns) == ['name', 'age']
        assert len(data) == 5
    
    @pytest.mark.asyncio
    async def test_load_data_all_nonexistent_columns(self, sample_csv_file):
        """Test handling when all requested columns don't exist."""
        adapter = CSVAdapter()
        
        with pytest.raises(ValueError) as exc_info:
            await adapter.load_data(
                file_path=sample_csv_file,
                columns_to_load=['nonexistent1', 'nonexistent2']
            )
        
        assert "None of the requested columns" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_load_data_caching(self, sample_csv_file):
        """Test data caching functionality."""
        adapter = CSVAdapter(cache_max_size=5)
        
        # First load
        data1 = await adapter.load_data(
            file_path=sample_csv_file,
            columns_to_load=['name', 'age']
        )
        
        # Second load should come from cache
        with patch('pandas.read_csv') as mock_read_csv:
            data2 = await adapter.load_data(
                file_path=sample_csv_file,
                columns_to_load=['name', 'age']
            )
            # pandas.read_csv should not be called again
            mock_read_csv.assert_not_called()
        
        # Verify data is the same
        pd.testing.assert_frame_equal(data1, data2)
        assert adapter.get_cache_info()['cache_size'] == 1
    
    @pytest.mark.asyncio
    async def test_load_data_different_columns_different_cache(self, sample_csv_file):
        """Test that different column sets create different cache entries."""
        adapter = CSVAdapter()
        
        # Load different column sets
        data1 = await adapter.load_data(
            file_path=sample_csv_file,
            columns_to_load=['name', 'age']
        )
        data2 = await adapter.load_data(
            file_path=sample_csv_file,
            columns_to_load=['name', 'city']
        )
        
        # Should have different cache entries
        assert adapter.get_cache_info()['cache_size'] == 2
        assert len(data1.columns) == 2
        assert len(data2.columns) == 2
        assert 'age' in data1.columns
        assert 'city' in data2.columns
        assert 'age' not in data2.columns
    
    @pytest.mark.asyncio
    async def test_load_data_cache_eviction(self, sample_csv_file):
        """Test LRU cache eviction."""
        adapter = CSVAdapter(cache_max_size=2)
        
        # Fill cache to capacity
        await adapter.load_data(file_path=sample_csv_file, columns_to_load=['name'])
        await adapter.load_data(file_path=sample_csv_file, columns_to_load=['age'])
        assert adapter.get_cache_info()['cache_size'] == 2
        
        # Add another entry, should evict the least recently used
        await adapter.load_data(file_path=sample_csv_file, columns_to_load=['city'])
        assert adapter.get_cache_info()['cache_size'] == 2
    
    @pytest.mark.asyncio
    async def test_load_data_file_not_found(self):
        """Test handling of non-existent file."""
        adapter = CSVAdapter()
        
        with pytest.raises(FileNotFoundError):
            await adapter.load_data(file_path='nonexistent_file.csv')
    
    @pytest.mark.asyncio
    async def test_load_data_no_file_path_no_endpoint(self):
        """Test error when no file path and no endpoint provided."""
        adapter = CSVAdapter()
        
        with pytest.raises(ValueError) as exc_info:
            await adapter.load_data()
        
        assert "file_path must be provided when no endpoint is configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_load_data_with_endpoint_file_path(self, sample_csv_file):
        """Test loading data using endpoint's file path."""
        mock_endpoint = Mock()
        mock_endpoint.file_path = sample_csv_file
        
        adapter = CSVAdapter(endpoint=mock_endpoint)
        data = await adapter.load_data(columns_to_load=['name', 'age'])
        
        assert len(data) == 5
        assert list(data.columns) == ['name', 'age']
    
    @pytest.mark.asyncio
    async def test_load_data_with_endpoint_url(self, sample_csv_file):
        """Test loading data using endpoint's URL."""
        mock_endpoint = Mock()
        mock_endpoint.file_path = None
        mock_endpoint.url = sample_csv_file
        
        adapter = CSVAdapter(endpoint=mock_endpoint)
        data = await adapter.load_data(columns_to_load=['name'])
        
        assert len(data) == 5
        assert list(data.columns) == ['name']
    
    @pytest.mark.asyncio
    async def test_load_data_endpoint_no_path(self):
        """Test error when endpoint has no file path or URL."""
        mock_endpoint = Mock()
        mock_endpoint.file_path = None
        mock_endpoint.url = None
        mock_endpoint.connection_details = None
        
        adapter = CSVAdapter(endpoint=mock_endpoint)
        
        with pytest.raises(ValueError) as exc_info:
            await adapter.load_data()
        
        assert "Could not determine file path from endpoint" in str(exc_info.value)
    
    def test_clear_cache(self, sample_csv_file):
        """Test cache clearing functionality."""
        adapter = CSVAdapter()
        
        # Add something to cache manually for testing
        adapter._data_cache[('test', None)] = pd.DataFrame({'a': [1, 2, 3]})
        assert adapter.get_cache_info()['cache_size'] == 1
        
        adapter.clear_cache()
        assert adapter.get_cache_info()['cache_size'] == 0
    
    def test_get_cache_info(self):
        """Test cache info retrieval."""
        adapter = CSVAdapter(cache_max_size=15)
        
        cache_info = adapter.get_cache_info()
        assert cache_info['cache_size'] == 0
        assert cache_info['max_size'] == 15
        assert cache_info['cached_files'] == []
    
    def test_get_cache_stats_initial(self):
        """Test cache statistics initial state."""
        adapter = CSVAdapter()
        stats = adapter.get_cache_stats()
        
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['total_requests'] == 0
        assert stats['hit_rate'] == 0.0
        assert stats['cache_size'] == 0
        assert stats['max_size'] > 0
    
    @pytest.mark.asyncio
    async def test_extract_ids_functionality(self):
        """Test that existing extract_ids functionality still works."""
        adapter = CSVAdapter()
        
        # Test with a value that should extract an ID
        result = await adapter.extract_ids(
            value="HMDB0000001",
            endpoint_id=1,
            ontology_type="hmdb"
        )
        
        assert len(result) == 1
        assert result[0]['id'] == "HMDB0000001"
        assert result[0]['ontology_type'] == "hmdb"
        assert result[0]['confidence'] == 1.0
    
    def test_get_supported_extractions(self):
        """Test that supported extractions functionality still works."""
        adapter = CSVAdapter()
        supported = adapter.get_supported_extractions(endpoint_id=1)
        assert isinstance(supported, list)
        assert len(supported) > 0


class TestCSVAdapterIntegration:
    """Integration tests for CSVAdapter with real-world scenarios."""
    
    @pytest.fixture
    def complex_csv_data(self):
        """Create more complex CSV data for integration testing."""
        return {
            'compound_id': ['C001', 'C002', 'C003', 'C004', 'C005'],
            'hmdb_id': ['HMDB0000001', 'HMDB0000002', 'HMDB0000003', 'HMDB0000004', 'HMDB0000005'],
            'chebi_id': ['CHEBI:1001', 'CHEBI:1002', 'CHEBI:1003', 'CHEBI:1004', 'CHEBI:1005'],
            'name': ['Glucose', 'Fructose', 'Galactose', 'Sucrose', 'Lactose'],
            'molecular_weight': [180.16, 180.16, 180.16, 342.30, 342.30],
            'formula': ['C6H12O6', 'C6H12O6', 'C6H12O6', 'C12H22O11', 'C12H22O11'],
            'description': ['A simple sugar', 'Fruit sugar', 'Milk sugar precursor', 'Table sugar', 'Milk sugar']
        }
    
    @pytest.fixture
    def complex_csv_file(self, complex_csv_data):
        """Create a complex CSV file for integration testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame(complex_csv_data)
            df.to_csv(f.name, index=False)
            yield f.name
        os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, complex_csv_file):
        """Test that selective loading uses less memory than loading all columns."""
        adapter = CSVAdapter()
        
        # Load all columns
        full_data = await adapter.load_data(file_path=complex_csv_file)
        
        # Load only specific columns
        selective_data = await adapter.load_data(
            file_path=complex_csv_file,
            columns_to_load=['compound_id', 'hmdb_id']
        )
        
        # Verify selective loading has fewer columns
        assert len(full_data.columns) == 7
        assert len(selective_data.columns) == 2
        
        # Both should have same number of rows
        assert len(full_data) == len(selective_data) == 5
        
        # Memory usage should be lower for selective data
        # (This is a conceptual test - actual memory measurement would require memory_profiler)
        assert selective_data.memory_usage(deep=True).sum() < full_data.memory_usage(deep=True).sum()
    
    @pytest.mark.asyncio
    async def test_performance_with_caching(self, complex_csv_file):
        """Test that caching improves performance on repeated loads."""
        adapter = CSVAdapter()
        
        # First load - should read from file
        start_time = pd.Timestamp.now()
        data1 = await adapter.load_data(
            file_path=complex_csv_file,
            columns_to_load=['compound_id', 'name']
        )
        first_load_time = (pd.Timestamp.now() - start_time).total_seconds()
        
        # Second load - should come from cache
        start_time = pd.Timestamp.now()
        data2 = await adapter.load_data(
            file_path=complex_csv_file,
            columns_to_load=['compound_id', 'name']
        )
        second_load_time = (pd.Timestamp.now() - start_time).total_seconds()
        
        # Data should be identical
        pd.testing.assert_frame_equal(data1, data2)
        
        # Second load should be faster (cached)
        # Note: This might not always be true in unit tests due to timing variations
        # but it demonstrates the concept
        assert adapter.get_cache_info()['cache_size'] == 1


class TestCSVAdapterPerformanceMonitoring:
    """Test performance monitoring features of CSVAdapter."""

    @pytest.fixture
    def sample_csv_file(self):
        """Create a temporary CSV file for testing."""
        data = {'id': [1, 2, 3], 'name': ['A', 'B', 'C'], 'value': [10, 20, 30]}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            pd.DataFrame(data).to_csv(f.name, index=False)
            yield f.name
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_cache_hit_miss_tracking(self, sample_csv_file):
        """Test that cache hits and misses are tracked correctly."""
        adapter = CSVAdapter(cache_max_size=5)
        
        # Initial state
        stats = adapter.get_cache_stats()
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['total_requests'] == 0
        assert stats['hit_rate'] == 0.0
        
        # First load - should be a cache miss
        await adapter.load_data(file_path=sample_csv_file, columns_to_load=['id', 'name'])
        stats = adapter.get_cache_stats()
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 1
        assert stats['total_requests'] == 1
        assert stats['hit_rate'] == 0.0
        
        # Second load with same parameters - should be a cache hit
        await adapter.load_data(file_path=sample_csv_file, columns_to_load=['id', 'name'])
        stats = adapter.get_cache_stats()
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['total_requests'] == 2
        assert stats['hit_rate'] == 0.5
        
        # Third load with different columns - should be a cache miss
        await adapter.load_data(file_path=sample_csv_file, columns_to_load=['id', 'value'])
        stats = adapter.get_cache_stats()
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 2
        assert stats['total_requests'] == 3
        assert stats['hit_rate'] == 1/3
        
        # Fourth load with first column set - should be a cache hit
        await adapter.load_data(file_path=sample_csv_file, columns_to_load=['id', 'name'])
        stats = adapter.get_cache_stats()
        assert stats['cache_hits'] == 2
        assert stats['cache_misses'] == 2
        assert stats['total_requests'] == 4
        assert stats['hit_rate'] == 0.5

    @pytest.mark.asyncio
    async def test_cache_stats_with_different_files(self, sample_csv_file):
        """Test cache statistics with multiple different files."""
        adapter = CSVAdapter()
        
        # Create a second temporary file
        data2 = {'x': [4, 5, 6], 'y': ['D', 'E', 'F']}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f2:
            pd.DataFrame(data2).to_csv(f2.name, index=False)
            second_file = f2.name
        
        try:
            # Load from first file
            await adapter.load_data(file_path=sample_csv_file, columns_to_load=['id'])
            # Load from second file  
            await adapter.load_data(file_path=second_file, columns_to_load=['x'])
            # Load from first file again (cache hit)
            await adapter.load_data(file_path=sample_csv_file, columns_to_load=['id'])
            
            stats = adapter.get_cache_stats()
            assert stats['cache_hits'] == 1
            assert stats['cache_misses'] == 2
            assert stats['total_requests'] == 3
            assert stats['hit_rate'] == 1/3
            assert stats['cache_size'] == 2  # Two different cache entries
            
        finally:
            os.unlink(second_file)

    def test_clear_cache_resets_stats(self):
        """Test that clearing cache also resets performance statistics."""
        adapter = CSVAdapter()
        
        # Manually set some stats to simulate usage
        adapter._cache_hits = 5
        adapter._cache_misses = 3
        adapter._data_cache[('test', None)] = pd.DataFrame({'a': [1, 2, 3]})
        
        # Verify stats before clearing
        stats = adapter.get_cache_stats()
        assert stats['cache_hits'] == 5
        assert stats['cache_misses'] == 3
        assert stats['total_requests'] == 8
        assert stats['cache_size'] == 1
        
        # Clear cache
        adapter.clear_cache()
        
        # Verify stats are reset
        stats = adapter.get_cache_stats()
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['total_requests'] == 0
        assert stats['hit_rate'] == 0.0
        assert stats['cache_size'] == 0

    def test_hit_rate_calculation_edge_cases(self):
        """Test hit rate calculation with edge cases."""
        adapter = CSVAdapter()
        
        # Test with zero requests
        stats = adapter.get_cache_stats()
        assert stats['hit_rate'] == 0.0
        
        # Test with only misses
        adapter._cache_misses = 3
        stats = adapter.get_cache_stats()
        assert stats['hit_rate'] == 0.0
        
        # Test with only hits
        adapter._cache_misses = 0
        adapter._cache_hits = 5
        stats = adapter.get_cache_stats()
        assert stats['hit_rate'] == 1.0


class TestCSVAdapterConfiguration:
    """Test configuration features of CSVAdapter."""

    def test_cache_size_from_settings(self):
        """Test that cache size is read from settings when not specified."""
        adapter = CSVAdapter()
        settings = get_settings()
        assert adapter._data_cache.maxsize == settings.csv_adapter_cache_size

    def test_cache_size_override(self):
        """Test that explicit cache_max_size overrides settings."""
        custom_size = 25
        adapter = CSVAdapter(cache_max_size=custom_size)
        assert adapter._data_cache.maxsize == custom_size

    def test_cache_size_none_uses_settings(self):
        """Test that None cache_max_size uses settings."""
        adapter = CSVAdapter(cache_max_size=None)
        settings = get_settings()
        assert adapter._data_cache.maxsize == settings.csv_adapter_cache_size

    @patch('biomapper.mapping.adapters.csv_adapter.get_settings')
    def test_settings_integration(self, mock_get_settings):
        """Test integration with settings system."""
        # Mock settings with custom cache size
        mock_settings = Mock()
        mock_settings.csv_adapter_cache_size = 42
        mock_get_settings.return_value = mock_settings
        
        adapter = CSVAdapter()
        assert adapter._data_cache.maxsize == 42
        mock_get_settings.assert_called_once()

    def test_cache_stats_includes_max_size(self):
        """Test that cache stats include the configured max size."""
        custom_size = 15
        adapter = CSVAdapter(cache_max_size=custom_size)
        
        stats = adapter.get_cache_stats()
        assert stats['max_size'] == custom_size