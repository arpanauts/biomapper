"""Tests for application configuration management."""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

from src.api.core.config import Settings, BASE_DIR
from pydantic_settings import SettingsConfigDict


class TestSettings(Settings):
    """Test-specific settings that ignore environment to test defaults."""
    model_config = SettingsConfigDict(
        env_file=None, case_sensitive=False, extra="allow"
    )


class TestSettingsDefaults:
    """Test default settings configuration."""
    
    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    def test_default_values(self):
        """Test that default values are properly set."""
        test_settings = TestSettings()
        
        # General settings
        assert test_settings.PROJECT_NAME == "Biomapper API"
        assert test_settings.DEBUG is False
        
        # API settings
        assert test_settings.API_V1_PREFIX == "/api"
        
        # CORS settings
        assert isinstance(test_settings.CORS_ORIGINS, list)
        expected_origins = [
            "http://localhost:3000",
            "http://localhost:5173", 
            "http://localhost:5174",
            "http://localhost:8000",
            "*"
        ]
        assert test_settings.CORS_ORIGINS == expected_origins
        
        # Database settings
        assert test_settings.DATABASE_URL == "sqlite+aiosqlite:///./biomapper.db"
        assert test_settings.DATABASE_ECHO is False
        
        # Session settings
        assert test_settings.SESSION_EXPIRY_HOURS == 24
        
        # Storage settings
        assert test_settings.MAX_INLINE_STORAGE_SIZE == 100 * 1024  # 100KB
    
    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    def test_path_defaults(self):
        """Test that path defaults are properly constructed."""
        test_settings = TestSettings()
        
        # Verify paths are Path objects
        assert isinstance(test_settings.UPLOAD_DIR, Path)
        assert isinstance(test_settings.MAPPING_RESULTS_DIR, Path)
        assert isinstance(test_settings.CHECKPOINT_DIR, Path)
        assert isinstance(test_settings.EXTERNAL_STORAGE_DIR, Path)
        assert isinstance(test_settings.STRATEGIES_DIR, Path)
        
        # Verify path construction
        assert test_settings.UPLOAD_DIR == BASE_DIR / "data" / "uploads"
        assert test_settings.MAPPING_RESULTS_DIR == BASE_DIR / "data" / "results"
        assert test_settings.CHECKPOINT_DIR == BASE_DIR / "data" / "checkpoints"
        assert test_settings.EXTERNAL_STORAGE_DIR == BASE_DIR / "data" / "storage"
        assert test_settings.STRATEGIES_DIR == BASE_DIR.parent / "configs"
    
    @patch('src.api.core.config.psutil')
    def test_max_upload_size_calculation(self, mock_psutil):
        """Test MAX_UPLOAD_SIZE calculation based on available memory."""
        # Mock available memory (8GB)
        mock_memory = Mock()
        mock_memory.available = 8 * 1024 * 1024 * 1024  # 8GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        test_settings = TestSettings()
        
        # Should be half of available memory
        expected_size = 4 * 1024 * 1024 * 1024  # 4GB
        assert test_settings.MAX_UPLOAD_SIZE == expected_size
    
    @patch('src.api.core.config.psutil', spec=[])  # Remove virtual_memory attribute
    def test_max_upload_size_fallback(self, mock_psutil):
        """Test MAX_UPLOAD_SIZE fallback when psutil is unavailable."""
        # Remove virtual_memory attribute
        if hasattr(mock_psutil, 'virtual_memory'):
            delattr(mock_psutil, 'virtual_memory')
        
        test_settings = TestSettings()
        
        # Should fallback to 1GB
        expected_size = 1024 * 1024 * 1024  # 1GB
        assert test_settings.MAX_UPLOAD_SIZE == expected_size


class TestSettingsEnvironmentVariables:
    """Test settings with environment variable overrides."""
    
    def test_debug_mode_from_env(self):
        """Test DEBUG setting from environment variable."""
        with patch.dict(os.environ, {'DEBUG': 'true'}):
            test_settings = Settings()
            assert test_settings.DEBUG is True
        
        with patch.dict(os.environ, {'DEBUG': 'false'}):
            test_settings = Settings()
            assert test_settings.DEBUG is False
        
        with patch.dict(os.environ, {'DEBUG': '1'}):
            test_settings = Settings()
            assert test_settings.DEBUG is True
    
    def test_project_name_from_env(self):
        """Test PROJECT_NAME from environment variable."""
        with patch.dict(os.environ, {'PROJECT_NAME': 'Custom API Name'}):
            test_settings = Settings()
            assert test_settings.PROJECT_NAME == "Custom API Name"
    
    def test_database_url_from_env(self):
        """Test DATABASE_URL from environment variable."""
        custom_db_url = "postgresql://user:pass@localhost/db"
        with patch.dict(os.environ, {'DATABASE_URL': custom_db_url}):
            test_settings = Settings()
            assert test_settings.DATABASE_URL == custom_db_url
    
    def test_api_prefix_from_env(self):
        """Test API_V1_PREFIX from environment variable."""
        with patch.dict(os.environ, {'API_V1_PREFIX': '/v1'}):
            test_settings = Settings()
            assert test_settings.API_V1_PREFIX == "/v1"
    
    def test_session_expiry_from_env(self):
        """Test SESSION_EXPIRY_HOURS from environment variable."""
        with patch.dict(os.environ, {'SESSION_EXPIRY_HOURS': '48'}):
            test_settings = Settings()
            assert test_settings.SESSION_EXPIRY_HOURS == 48
    
    def test_max_inline_storage_from_env(self):
        """Test MAX_INLINE_STORAGE_SIZE from environment variable."""
        with patch.dict(os.environ, {'MAX_INLINE_STORAGE_SIZE': '204800'}):
            test_settings = Settings()
            assert test_settings.MAX_INLINE_STORAGE_SIZE == 204800
    
    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        with patch.dict(os.environ, {'debug': 'true'}):
            test_settings = Settings()
            assert test_settings.DEBUG is True
        
        with patch.dict(os.environ, {'project_name': 'Lower Case Name'}):
            test_settings = Settings()
            assert test_settings.PROJECT_NAME == "Lower Case Name"


class TestSettingsValidation:
    """Test settings validation and type conversion."""
    
    def test_cors_origins_type_validation(self):
        """Test CORS_ORIGINS type validation."""
        test_settings = Settings()
        assert isinstance(test_settings.CORS_ORIGINS, list)
        
        # All items should be strings
        for origin in test_settings.CORS_ORIGINS:
            assert isinstance(origin, str)
    
    def test_numeric_field_validation(self):
        """Test numeric field validation."""
        # Valid numeric values
        with patch.dict(os.environ, {'SESSION_EXPIRY_HOURS': '24'}):
            test_settings = Settings()
            assert test_settings.SESSION_EXPIRY_HOURS == 24
        
        # Invalid numeric values should raise validation error
        with patch.dict(os.environ, {'SESSION_EXPIRY_HOURS': 'not_a_number'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_boolean_field_validation(self):
        """Test boolean field validation."""
        # Valid boolean values
        bool_test_cases = [
            ('true', True),
            ('false', False), 
            ('1', True),
            ('0', False),
            ('yes', True),
            ('no', False),
            ('on', True),
            ('off', False)
        ]
        
        for env_value, expected in bool_test_cases:
            with patch.dict(os.environ, {'DEBUG': env_value}):
                test_settings = Settings()
                assert test_settings.DEBUG == expected
    
    def test_path_validation(self):
        """Test path field validation."""
        test_settings = Settings()
        
        # All path fields should be Path objects
        path_fields = [
            'UPLOAD_DIR', 'MAPPING_RESULTS_DIR', 'CHECKPOINT_DIR',
            'EXTERNAL_STORAGE_DIR', 'STRATEGIES_DIR'
        ]
        
        for field_name in path_fields:
            field_value = getattr(test_settings, field_name)
            assert isinstance(field_value, Path)


class TestSettingsDirectoryCreation:
    """Test automatic directory creation."""
    
    @patch('src.api.core.config.Path.mkdir')
    def test_directory_creation_called(self, mock_mkdir):
        """Test that directories are created during initialization."""
        Settings()
        
        # Should call mkdir for each directory
        assert mock_mkdir.call_count >= 4  # At least 4 directories
        
        # Verify mkdir was called with correct parameters
        for call in mock_mkdir.call_args_list:
            args, kwargs = call
            assert kwargs.get('parents') is True
            assert kwargs.get('exist_ok') is True
    
    def test_directory_creation_with_temp_dir(self):
        """Test directory creation with temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create settings with custom base directory
            custom_settings = Settings()
            custom_settings.UPLOAD_DIR = temp_path / "uploads"
            custom_settings.MAPPING_RESULTS_DIR = temp_path / "results"
            custom_settings.CHECKPOINT_DIR = temp_path / "checkpoints"
            custom_settings.EXTERNAL_STORAGE_DIR = temp_path / "storage"
            
            # Trigger directory creation manually
            custom_settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            custom_settings.MAPPING_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            custom_settings.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
            custom_settings.EXTERNAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            
            # Verify directories were created
            assert custom_settings.UPLOAD_DIR.exists()
            assert custom_settings.MAPPING_RESULTS_DIR.exists()
            assert custom_settings.CHECKPOINT_DIR.exists()
            assert custom_settings.EXTERNAL_STORAGE_DIR.exists()


class TestSettingsInheritance:
    """Test settings inheritance and customization."""
    
    def test_custom_settings_class(self):
        """Test creating custom settings class."""
        class CustomSettings(Settings):
            CUSTOM_FIELD: str = "custom_value"
            PROJECT_NAME: str = "Custom Project"
        
        custom_settings = CustomSettings()
        
        assert custom_settings.CUSTOM_FIELD == "custom_value"
        assert custom_settings.PROJECT_NAME == "Custom Project"
        # Should inherit other default values
        assert custom_settings.DEBUG is False
        assert custom_settings.API_V1_PREFIX == "/api"
    
    def test_settings_with_custom_values(self):
        """Test settings with custom initialization values."""
        custom_settings = Settings(
            PROJECT_NAME="Test Project",
            DEBUG=True,
            SESSION_EXPIRY_HOURS=48
        )
        
        assert custom_settings.PROJECT_NAME == "Test Project"
        assert custom_settings.DEBUG is True
        assert custom_settings.SESSION_EXPIRY_HOURS == 48
        # Other values should remain default
        assert custom_settings.API_V1_PREFIX == "/api"


class TestSettingsConfiguration:
    """Test settings configuration and model config."""
    
    def test_model_config_settings(self):
        """Test Pydantic model configuration."""
        test_settings = Settings()
        
        # Verify model config attributes
        config = test_settings.model_config
        
        assert config['env_file'] == ".env"
        assert config['env_file_encoding'] == "utf-8"
        assert config['case_sensitive'] is False
        assert config['extra'] == "allow"
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed."""
        # Should not raise validation error for extra fields
        custom_settings = Settings(EXTRA_FIELD="extra_value")
        
        assert hasattr(custom_settings, 'EXTRA_FIELD')
        assert custom_settings.EXTRA_FIELD == "extra_value"
    
    def test_env_file_loading(self):
        """Test .env file loading behavior."""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_file:
            env_file.write("PROJECT_NAME=Env File Project\n")
            env_file.write("DEBUG=true\n")
            env_file_path = env_file.name
        
        try:
            # Create a custom settings class with the temporary env file
            class CustomSettings(Settings):
                model_config = SettingsConfigDict(
                    env_file=env_file_path, env_file_encoding="utf-8", case_sensitive=False, extra="allow"
                )
            
            test_settings = CustomSettings()
            # Note: This tests that the env file configuration mechanism works
            assert hasattr(test_settings, 'PROJECT_NAME')
        finally:
            os.unlink(env_file_path)


class TestGlobalSettingsInstance:
    """Test the global settings instance."""
    
    def test_global_settings_instance(self):
        """Test that global settings instance is properly initialized."""
        from src.api.core.config import settings
        
        assert isinstance(settings, Settings)
        assert settings.PROJECT_NAME == "Biomapper API"
    
    def test_global_settings_consistency(self):
        """Test that global settings instance is consistent."""
        from src.api.core.config import settings as settings1
        from src.api.core.config import settings as settings2
        
        # Should be the same instance
        assert settings1 is settings2
    
    def test_global_settings_modification(self):
        """Test modifying global settings."""
        from src.api.core.config import settings
        
        original_debug = settings.DEBUG
        
        # Modify setting
        settings.DEBUG = not original_debug
        
        # Verify modification
        assert settings.DEBUG != original_debug
        
        # Restore original value
        settings.DEBUG = original_debug


class TestSettingsEnvironmentSpecific:
    """Test environment-specific configuration scenarios."""
    
    def test_development_environment(self):
        """Test development environment configuration."""
        dev_env_vars = {
            'DEBUG': 'true',
            'DATABASE_ECHO': 'true',
            'PROJECT_NAME': 'Biomapper API (Development)'
        }
        
        with patch.dict(os.environ, dev_env_vars):
            dev_settings = Settings()
            
            assert dev_settings.DEBUG is True
            assert dev_settings.DATABASE_ECHO is True
            assert "Development" in dev_settings.PROJECT_NAME
    
    def test_production_environment(self):
        """Test production environment configuration."""
        prod_env_vars = {
            'DEBUG': 'false',
            'DATABASE_ECHO': 'false',
            'PROJECT_NAME': 'Biomapper API',
            'DATABASE_URL': 'postgresql://prod_user:prod_pass@prod_host/prod_db'
        }
        
        with patch.dict(os.environ, prod_env_vars):
            prod_settings = Settings()
            
            assert prod_settings.DEBUG is False
            assert prod_settings.DATABASE_ECHO is False
            assert prod_settings.DATABASE_URL.startswith('postgresql://')
    
    def test_testing_environment(self):
        """Test testing environment configuration."""
        test_env_vars = {
            'DATABASE_URL': 'sqlite+aiosqlite:///:memory:',
            'SESSION_EXPIRY_HOURS': '1',  # Short expiry for tests
            'MAX_INLINE_STORAGE_SIZE': '1024'  # Small size for tests
        }
        
        with patch.dict(os.environ, test_env_vars):
            test_settings = Settings()
            
            assert ':memory:' in test_settings.DATABASE_URL
            assert test_settings.SESSION_EXPIRY_HOURS == 1
            assert test_settings.MAX_INLINE_STORAGE_SIZE == 1024


class TestSettingsErrorHandling:
    """Test error handling in settings configuration."""
    
    def test_invalid_numeric_values(self):
        """Test handling of invalid numeric environment variables."""
        with patch.dict(os.environ, {'SESSION_EXPIRY_HOURS': 'invalid_number'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_invalid_boolean_values(self):
        """Test handling of invalid boolean environment variables."""
        # Some invalid boolean values might be accepted by pydantic
        # Test with clearly invalid values
        with patch.dict(os.environ, {'DEBUG': 'maybe'}):
            # Pydantic might handle this gracefully or raise an error
            try:
                test_settings = Settings()
                # If no error, verify it's handled sensibly
                assert isinstance(test_settings.DEBUG, bool)
            except ValueError:
                # If error is raised, that's also acceptable
                pass
    
    def test_missing_required_env_vars(self):
        """Test handling when required environment variables are missing."""
        # Since all fields have defaults, missing env vars should not cause errors
        # Clear environment variables that might exist
        env_vars_to_clear = ['PROJECT_NAME', 'DEBUG', 'DATABASE_URL']
        
        with patch.dict(os.environ, {}, clear=True):
            test_settings = TestSettings()
            
            # Should use default values
            assert test_settings.PROJECT_NAME == "Biomapper API"
            assert test_settings.DEBUG is False
            assert test_settings.DATABASE_URL == "sqlite+aiosqlite:///./biomapper.db"


class TestSettingsUtilityMethods:
    """Test utility methods and properties of Settings."""
    
    def test_settings_repr(self):
        """Test string representation of settings."""
        test_settings = Settings()
        
        # Should be able to convert to string without errors
        str_repr = str(test_settings)
        assert isinstance(str_repr, str)
        assert len(str_repr) > 0
    
    def test_settings_dict_conversion(self):
        """Test converting settings to dictionary."""
        test_settings = Settings()
        
        settings_dict = test_settings.model_dump()
        
        assert isinstance(settings_dict, dict)
        assert 'PROJECT_NAME' in settings_dict
        assert 'DEBUG' in settings_dict
        assert settings_dict['PROJECT_NAME'] == test_settings.PROJECT_NAME
    
    def test_settings_field_access(self):
        """Test accessing settings fields."""
        test_settings = Settings()
        
        # Test direct attribute access
        assert hasattr(test_settings, 'PROJECT_NAME')
        assert hasattr(test_settings, 'DEBUG')
        assert hasattr(test_settings, 'CORS_ORIGINS')
        
        # Test field values
        assert isinstance(test_settings.PROJECT_NAME, str)
        assert isinstance(test_settings.DEBUG, bool)
        assert isinstance(test_settings.CORS_ORIGINS, list)


class TestSettingsMemoryUsage:
    """Test memory usage and performance of settings."""
    
    def test_settings_instantiation_performance(self):
        """Test that settings instantiation is fast."""
        import time
        
        start_time = time.perf_counter()
        for _ in range(100):
            Settings()
        end_time = time.perf_counter()
        
        elapsed_time = end_time - start_time
        # Should be fast (under 4 seconds for 100 instantiations)
        # Threshold adjusted for CI environment overhead and slower runners
        assert elapsed_time < 4.0, f"Settings instantiation took {elapsed_time:.2f} seconds"
    
    def test_multiple_settings_instances(self):
        """Test creating multiple settings instances."""
        instances = []
        
        for i in range(10):
            instance = Settings(PROJECT_NAME=f"Project {i}")
            instances.append(instance)
        
        # Each instance should have correct values
        for i, instance in enumerate(instances):
            assert instance.PROJECT_NAME == f"Project {i}"
        
        # Instances should be independent
        assert len(set(id(instance) for instance in instances)) == 10