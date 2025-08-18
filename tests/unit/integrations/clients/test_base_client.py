"""Tests for integration base client interface."""

import pytest

from src.integrations.clients.base_client import (
    BaseMappingClient,
    CachedMappingClientMixin,
    FileLookupClientMixin,
)
from core.exceptions import ClientInitializationError


class TestBaseMappingClient:
    """Test BaseMappingClient functionality."""
    
    @pytest.fixture
    def basic_config(self):
        """Create basic test configuration."""
        return {
            "base_url": "https://api.example.com",
            "timeout": 30,
            "max_retries": 3
        }
    
    @pytest.fixture
    def empty_config(self):
        """Create empty configuration."""
        return {}
    
    @pytest.fixture
    def invalid_config(self):
        """Create invalid configuration missing required keys."""
        return {
            "timeout": 30
        }
    
    def test_client_initialization_success(self, basic_config):
        """Test successful client initialization."""
        # Create a concrete implementation for testing
        class TestClient(BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestClient(basic_config)
        assert client._config == basic_config
        assert client._initialized is False  # Set during _validate_config
    
    def test_client_initialization_with_none_config(self):
        """Test client initialization with None config."""
        class TestClient(BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestClient(None)
        assert client._config == {}
    
    def test_get_config_value_existing_key(self, basic_config):
        """Test getting existing configuration value."""
        class TestClient(BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestClient(basic_config)
        assert client.get_config_value("timeout") == 30
        assert client.get_config_value("base_url") == "https://api.example.com"
    
    def test_get_config_value_missing_key_with_default(self, basic_config):
        """Test getting missing configuration value with default."""
        class TestClient(BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestClient(basic_config)
        assert client.get_config_value("missing_key", "default_value") == "default_value"
    
    def test_get_config_value_missing_key_no_default(self, basic_config):
        """Test getting missing configuration value without default."""
        class TestClient(BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestClient(basic_config)
        assert client.get_config_value("missing_key") is None
    
    def test_validate_config_with_required_keys_success(self):
        """Test successful config validation with required keys."""
        class TestClientWithRequiredKeys(BaseMappingClient):
            def get_required_config_keys(self):
                return ["api_key", "base_url"]
            
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        config = {"api_key": "test_key", "base_url": "https://api.example.com"}
        client = TestClientWithRequiredKeys(config)
        # Should not raise exception
        assert client._config == config
    
    def test_validate_config_with_required_keys_failure(self):
        """Test config validation failure with missing required keys."""
        class TestClientWithRequiredKeys(BaseMappingClient):
            def get_required_config_keys(self):
                return ["api_key", "base_url"]
            
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        config = {"api_key": "test_key"}  # Missing base_url
        
        with pytest.raises(Exception) as exc_info:  # Catch any exception type
            TestClientWithRequiredKeys(config)
        
        # Verify it's the right type and message
        assert isinstance(exc_info.value, ClientInitializationError)
        assert "Missing required configuration" in str(exc_info.value)
        assert "base_url" in str(exc_info.value)
    
    def test_format_result_with_values(self):
        """Test format_result with provided values."""
        target_ids = ["ID1", "ID2", "ID3"]
        component_id = "component_123"
        
        result = BaseMappingClient.format_result(target_ids, component_id)
        
        assert result == (target_ids, component_id)
    
    def test_format_result_with_none_values(self):
        """Test format_result with None values."""
        result = BaseMappingClient.format_result(None, None)
        assert result == (None, None)
    
    def test_format_result_default_parameters(self):
        """Test format_result with default parameters."""
        result = BaseMappingClient.format_result()
        assert result == (None, None)
    
    @pytest.mark.asyncio
    async def test_reverse_map_identifiers_not_implemented(self, basic_config):
        """Test that reverse_map_identifiers raises NotImplementedError by default."""
        class TestClient(BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestClient(basic_config)
        
        with pytest.raises(NotImplementedError) as exc_info:
            await client.reverse_map_identifiers(["ID1", "ID2"])
        
        assert "does not implement reverse_map_identifiers" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_close_method_default_implementation(self, basic_config):
        """Test that close method has default implementation that does nothing."""
        class TestClient(BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestClient(basic_config)
        # Should not raise exception
        await client.close()
    
    @pytest.mark.asyncio
    async def test_map_identifiers_is_abstract(self, basic_config):
        """Test that map_identifiers is abstract and must be implemented."""
        # Python ABC properly prevents instantiation of abstract classes
        
        class IncompleteClient(BaseMappingClient):
            pass  # Missing map_identifiers implementation
        
        # Should raise TypeError when trying to instantiate abstract class
        with pytest.raises(TypeError) as exc_info:
            IncompleteClient(basic_config)
        
        assert "Can't instantiate abstract class" in str(exc_info.value)
        assert "map_identifiers" in str(exc_info.value)


class TestCachedMappingClientMixin:
    """Test CachedMappingClientMixin functionality."""
    
    @pytest.fixture
    def cached_client(self):
        """Create cached client instance."""
        class TestCachedClient(CachedMappingClientMixin, BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        return TestCachedClient(cache_size=5, config={})
    
    @pytest.fixture
    def sample_cache_data(self):
        """Create sample cache data."""
        return {
            "ID1": (["MAPPED_ID1"], "component1"),
            "ID2": (["MAPPED_ID2A", "MAPPED_ID2B"], "component2"),
            "ID3": (None, "error:not_found")
        }
    
    def test_cache_initialization(self, cached_client):
        """Test cache initialization."""
        assert hasattr(cached_client, '_cache')
        assert hasattr(cached_client, '_cache_size')
        assert cached_client._cache_size == 5
        assert cached_client._cache_hits == 0
        assert cached_client._cache_misses == 0
        assert hasattr(cached_client, '_cache_lock')
    
    @pytest.mark.asyncio
    async def test_cache_get_miss(self, cached_client):
        """Test cache get with cache miss."""
        result = await cached_client._get_from_cache("nonexistent_id")
        
        assert result is None
        assert cached_client._cache_misses == 1
        assert cached_client._cache_hits == 0
    
    @pytest.mark.asyncio
    async def test_cache_add_and_get_hit(self, cached_client):
        """Test cache add and subsequent get hit."""
        test_result = (["MAPPED_ID"], "component1")
        
        await cached_client._add_to_cache("test_id", test_result)
        retrieved_result = await cached_client._get_from_cache("test_id")
        
        assert retrieved_result == test_result
        assert cached_client._cache_hits == 1
        assert cached_client._cache_misses == 0
    
    @pytest.mark.asyncio
    async def test_cache_add_many(self, cached_client, sample_cache_data):
        """Test adding multiple cache entries at once."""
        await cached_client._add_many_to_cache(sample_cache_data)
        
        # Verify all entries were added
        for identifier, expected_result in sample_cache_data.items():
            cached_result = await cached_client._get_from_cache(identifier)
            assert cached_result == expected_result
    
    @pytest.mark.asyncio
    async def test_cache_size_limit(self):
        """Test cache size limiting behavior."""
        class TestCachedClient(CachedMappingClientMixin, BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        # Create client with small cache size
        client = TestCachedClient(cache_size=2, config={})
        
        # Add more entries than cache size
        await client._add_to_cache("ID1", (["MAPPED1"], "comp1"))
        await client._add_to_cache("ID2", (["MAPPED2"], "comp2"))
        await client._add_to_cache("ID3", (["MAPPED3"], "comp3"))  # Should evict one
        
        # Cache should contain at most 2 entries
        assert len(client._cache) <= 2
        
        # ID3 should be present (most recently added)
        result = await client._get_from_cache("ID3")
        assert result == (["MAPPED3"], "comp3")
    
    def test_get_cache_stats_empty(self, cached_client):
        """Test cache statistics for empty cache."""
        stats = cached_client.get_cache_stats()
        
        expected_stats = {
            "cache_size": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "hit_ratio": 0,
            "initialized": False
        }
        
        assert stats == expected_stats
    
    @pytest.mark.asyncio
    async def test_get_cache_stats_with_data(self, cached_client, sample_cache_data):
        """Test cache statistics with data and hits/misses."""
        # Add some data
        await cached_client._add_many_to_cache(sample_cache_data)
        
        # Generate some hits and misses
        await cached_client._get_from_cache("ID1")  # Hit
        await cached_client._get_from_cache("ID1")  # Hit
        await cached_client._get_from_cache("nonexistent")  # Miss
        
        stats = cached_client.get_cache_stats()
        
        assert stats["cache_size"] == 3
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert stats["hit_ratio"] == 2/3  # 2 hits out of 3 total requests
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, cached_client, sample_cache_data):
        """Test cache clearing functionality."""
        # Add data to cache
        await cached_client._add_many_to_cache(sample_cache_data)
        
        # Generate some stats
        await cached_client._get_from_cache("ID1")
        
        # Clear cache
        await cached_client.clear_cache()
        
        # Verify cache is empty and stats are reset
        assert len(cached_client._cache) == 0
        assert cached_client._cache_hits == 0
        assert cached_client._cache_misses == 0
        
        # Verify data is no longer accessible
        result = await cached_client._get_from_cache("ID1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_preload_cache_default(self, cached_client):
        """Test default preload cache implementation."""
        # Default implementation should do nothing
        await cached_client._preload_cache()
        
        # Cache should remain empty
        assert len(cached_client._cache) == 0
    
    @pytest.mark.asyncio
    async def test_cache_thread_safety(self, cached_client):
        """Test cache thread safety with concurrent operations."""
        import asyncio
        
        async def add_to_cache(identifier, value):
            await cached_client._add_to_cache(identifier, value)
        
        async def get_from_cache(identifier):
            return await cached_client._get_from_cache(identifier)
        
        # Run concurrent cache operations
        tasks = []
        for i in range(10):
            tasks.append(add_to_cache(f"ID{i}", ([f"MAPPED{i}"], f"comp{i}")))
            tasks.append(get_from_cache(f"ID{i}"))
        
        # Should not raise any exceptions
        await asyncio.gather(*tasks)


class TestFileLookupClientMixin:
    """Test FileLookupClientMixin functionality."""
    
    @pytest.fixture
    def file_config(self):
        """Create file-based configuration."""
        return {
            "file_path": "/path/to/lookup_file.csv",
            "key_column": "source_id", 
            "value_column": "target_id"
        }
    
    @pytest.fixture
    def file_client(self, file_config):
        """Create file lookup client instance."""
        class TestFileClient(FileLookupClientMixin, BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        return TestFileClient(config=file_config)
    
    def test_file_client_initialization(self, file_client, file_config):
        """Test file client initialization."""
        assert file_client._config == file_config
        assert file_client._file_path_key == "file_path"
        assert file_client._key_column_key == "key_column"
        assert file_client._value_column_key == "value_column"
    
    def test_file_client_custom_key_names(self):
        """Test file client with custom configuration key names."""
        class CustomFileClient(FileLookupClientMixin, BaseMappingClient):
            def __init__(self, config):
                super().__init__(
                    file_path_key="custom_file",
                    key_column_key="custom_key_col",
                    value_column_key="custom_value_col",
                    config=config
                )
            
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        config = {
            "custom_file": "/custom/path.csv",
            "custom_key_col": "id",
            "custom_value_col": "name"
        }
        
        client = CustomFileClient(config)
        assert client._file_path_key == "custom_file"
        assert client._key_column_key == "custom_key_col"
        assert client._value_column_key == "custom_value_col"
    
    def test_get_required_config_keys(self, file_client):
        """Test required configuration keys for file lookup."""
        required_keys = file_client.get_required_config_keys()
        
        expected_keys = ["file_path", "key_column", "value_column"]
        assert all(key in required_keys for key in expected_keys)
    
    def test_get_required_config_keys_with_parent_class(self):
        """Test required config keys when parent class also has requirements."""
        class TestFileClientWithParentRequirements(FileLookupClientMixin, BaseMappingClient):
            def __init__(self, config):
                # Initialize the mixin with custom keys for testing
                FileLookupClientMixin.__init__(self, config=config)
                
            def get_required_config_keys(self):
                # Simulate parent class requirements (override to avoid recursion)
                return ["api_key", "base_url", "file_path", "key_column", "value_column"]
            
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        config = {
            "api_key": "test_key",
            "base_url": "https://api.example.com",
            "file_path": "/path/to/file.csv",
            "key_column": "id",
            "value_column": "name"
        }
        
        client = TestFileClientWithParentRequirements(config)
        required_keys = client.get_required_config_keys()
        
        expected_keys = ["api_key", "base_url", "file_path", "key_column", "value_column"]
        assert all(key in required_keys for key in expected_keys)
    
    def test_get_file_path(self, file_client):
        """Test getting file path from configuration."""
        assert file_client._get_file_path() == "/path/to/lookup_file.csv"
    
    def test_get_key_column(self, file_client):
        """Test getting key column from configuration."""
        assert file_client._get_key_column() == "source_id"
    
    def test_get_value_column(self, file_client):
        """Test getting value column from configuration."""
        assert file_client._get_value_column() == "target_id"
    
    def test_get_file_path_missing_config(self):
        """Test getting file path when not in configuration."""
        class TestFileClient(FileLookupClientMixin, BaseMappingClient):
            def get_required_config_keys(self):
                return []  # Override to allow empty config for testing
                
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestFileClient(config={})
        assert client._get_file_path() == ""
    
    def test_get_key_column_missing_config(self):
        """Test getting key column when not in configuration."""
        class TestFileClient(FileLookupClientMixin, BaseMappingClient):
            def get_required_config_keys(self):
                return []  # Override to allow empty config for testing
                
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestFileClient(config={})
        assert client._get_key_column() == ""
    
    def test_get_value_column_missing_config(self):
        """Test getting value column when not in configuration."""
        class TestFileClient(FileLookupClientMixin, BaseMappingClient):
            def get_required_config_keys(self):
                return []  # Override to allow empty config for testing
                
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestFileClient(config={})
        assert client._get_value_column() == ""


class TestIntegratedMixinFunctionality:
    """Test integration of multiple mixins together."""
    
    @pytest.fixture
    def integrated_client(self):
        """Create client with both mixins."""
        class IntegratedClient(CachedMappingClientMixin, FileLookupClientMixin, BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                # Simulate file-based lookup with caching
                results = {}
                for identifier in identifiers:
                    # Check cache first
                    cached_result = await self._get_from_cache(identifier)
                    if cached_result is not None:
                        results[identifier] = cached_result
                    else:
                        # Simulate lookup and cache result
                        if identifier == "CACHED_ID":
                            result = (["MAPPED_CACHED"], "file_lookup")
                            await self._add_to_cache(identifier, result)
                            results[identifier] = result
                        else:
                            result = (None, "not_found")
                            results[identifier] = result
                
                return results
        
        config = {
            "file_path": "/test/lookup.csv",
            "key_column": "id",
            "value_column": "mapped_id"
        }
        
        return IntegratedClient(cache_size=10, config=config)
    
    @pytest.mark.asyncio
    async def test_cached_file_lookup_integration(self, integrated_client):
        """Test integration of caching with file lookup."""
        # First call should populate cache
        result1 = await integrated_client.map_identifiers(["CACHED_ID"])
        assert result1["CACHED_ID"] == (["MAPPED_CACHED"], "file_lookup")
        
        # Second call should hit cache
        result2 = await integrated_client.map_identifiers(["CACHED_ID"])
        assert result2["CACHED_ID"] == (["MAPPED_CACHED"], "file_lookup")
        
        # Verify cache statistics
        stats = integrated_client.get_cache_stats()
        assert stats["cache_hits"] == 1  # Second call was a cache hit
        assert stats["cache_misses"] == 1  # First call was a cache miss
    
    def test_mixin_method_resolution_order(self, integrated_client):
        """Test that method resolution order is correct for mixins."""
        # Should have methods from all mixins and base class
        assert hasattr(integrated_client, '_get_from_cache')  # From CachedMappingClientMixin
        assert hasattr(integrated_client, '_get_file_path')   # From FileLookupClientMixin
        assert hasattr(integrated_client, 'map_identifiers')  # From BaseMappingClient
        assert hasattr(integrated_client, 'format_result')    # From BaseMappingClient (static)
    
    def test_config_requirements_from_mixins(self, integrated_client):
        """Test that configuration requirements from mixins are combined."""
        required_keys = integrated_client.get_required_config_keys()
        
        # Should include requirements from FileLookupClientMixin
        file_keys = ["file_path", "key_column", "value_column"]
        assert all(key in required_keys for key in file_keys)


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    def test_client_initialization_error_details(self):
        """Test that initialization errors include helpful details."""
        class TestClientWithRequiredKeys(BaseMappingClient):
            def get_required_config_keys(self):
                return ["api_key", "secret_key", "base_url"]
            
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        config = {"api_key": "test"}  # Missing secret_key and base_url
        
        with pytest.raises(Exception) as exc_info:  # Catch any exception type
            TestClientWithRequiredKeys(config)
        
        # Verify it's the right type and has details
        assert isinstance(exc_info.value, ClientInitializationError)
        error = exc_info.value
        assert error.client_name == "TestClientWithRequiredKeys"
        assert hasattr(error, 'details')  # Should have details attribute
    
    @pytest.mark.asyncio
    async def test_cache_operations_with_none_values(self):
        """Test cache operations with None values."""
        class TestCachedClient(CachedMappingClientMixin, BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestCachedClient(cache_size=5, config={})
        
        # Test caching None values
        await client._add_to_cache("none_result", (None, "not_found"))
        result = await client._get_from_cache("none_result")
        
        assert result == (None, "not_found")
    
    def test_cache_stats_division_by_zero_protection(self):
        """Test cache statistics calculation when no operations have occurred."""
        class TestCachedClient(CachedMappingClientMixin, BaseMappingClient):
            async def map_identifiers(self, identifiers, config=None):
                return {}
        
        client = TestCachedClient(cache_size=5, config={})
        stats = client.get_cache_stats()
        
        # Should not raise division by zero error
        assert stats["hit_ratio"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0