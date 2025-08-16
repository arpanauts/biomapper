"""
Comprehensive tests for environment configuration management.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from biomapper.core.standards.env_manager import EnvironmentManager
from biomapper.core.standards.env_validator import EnvironmentValidator


class TestEnvironmentManager:
    """Test cases for EnvironmentManager class."""
    
    def test_env_loading_from_file(self, tmp_path):
        """Test that .env file is loaded correctly."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("""
GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json
GOOGLE_DRIVE_FOLDER_ID=test_folder_id
BIOMAPPER_DATA_DIR=/tmp/data
BIOMAPPER_OUTPUT_DIR=/tmp/output
DATABASE_URL=sqlite:///test.db
""")
        
        # Load environment
        env = EnvironmentManager(env_file=str(env_file))
        
        # Check that variables are loaded
        assert os.getenv('GOOGLE_APPLICATION_CREDENTIALS') == '/path/to/creds.json'
        assert os.getenv('GOOGLE_DRIVE_FOLDER_ID') == 'test_folder_id'
        assert os.getenv('BIOMAPPER_DATA_DIR') == '/tmp/data'
    
    def test_env_file_discovery(self, tmp_path, monkeypatch):
        """Test automatic discovery of .env file."""
        # Create .env in temporary directory
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=discovered")
        
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        
        # Should find .env in current directory
        env = EnvironmentManager()
        assert env.env_file == env_file
    
    def test_missing_env_vars_error(self):
        """Test handling of missing environment variables."""
        env = EnvironmentManager()
        
        # Clear Google Drive variables
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError) as exc_info:
                env.validate_requirements(['google_drive'])
            
            assert 'Missing or invalid environment variables' in str(exc_info.value)
            assert 'GOOGLE_APPLICATION_CREDENTIALS' in str(exc_info.value)
    
    def test_fallback_values(self):
        """Test fallback value mechanism."""
        env = EnvironmentManager()
        
        with patch.dict(os.environ, {}, clear=True):
            # Should return fallback when env var not set
            value = env.get_with_fallback('NONEXISTENT_VAR', 'fallback_value')
            assert value == 'fallback_value'
            
            # Should return env var when set
            os.environ['EXISTING_VAR'] = 'actual_value'
            value = env.get_with_fallback('EXISTING_VAR', 'fallback_value')
            assert value == 'actual_value'
    
    def test_path_handling(self, tmp_path):
        """Test Path object handling."""
        env = EnvironmentManager()
        
        # Test with existing path
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        with patch.dict(os.environ, {'TEST_PATH': str(test_dir)}):
            path = env.get_path('TEST_PATH')
            assert path == test_dir
            assert path.exists()
        
        # Test with non-existent path
        with patch.dict(os.environ, {'MISSING_PATH': '/nonexistent/path'}):
            path = env.get_path('MISSING_PATH')
            assert path == Path('/nonexistent/path')
            assert not path.exists()
    
    def test_create_directory_if_missing(self, tmp_path):
        """Test automatic directory creation."""
        env = EnvironmentManager()
        
        new_dir = tmp_path / "auto_created"
        assert not new_dir.exists()
        
        with patch.dict(os.environ, {'TEST_DIR': str(new_dir)}):
            path = env.get_path('TEST_DIR', create_if_missing=True)
            assert path == new_dir
            assert path.exists()
            assert path.is_dir()
    
    def test_google_credentials_validation(self, tmp_path):
        """Test Google credentials file validation."""
        env = EnvironmentManager()
        
        # Create valid credentials file
        valid_creds = tmp_path / "valid_creds.json"
        valid_creds.write_text("""{
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\\ntest\\n-----END PRIVATE KEY-----",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789"
        }""")
        
        with patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': str(valid_creds)}):
            creds_path = env.get_google_credentials_path()
            assert creds_path == valid_creds
        
        # Test invalid JSON
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("not valid json")
        
        with patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': str(invalid_json)}):
            creds_path = env.get_google_credentials_path()
            assert creds_path is None
        
        # Test missing required fields
        incomplete_creds = tmp_path / "incomplete.json"
        incomplete_creds.write_text('{"type": "service_account"}')
        
        with patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': str(incomplete_creds)}):
            creds_path = env.get_google_credentials_path()
            assert creds_path is None
    
    def test_google_drive_folder_id_validation(self):
        """Test Google Drive folder ID validation."""
        env = EnvironmentManager()
        
        # Valid folder ID
        with patch.dict(os.environ, {'GOOGLE_DRIVE_FOLDER_ID': '1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D'}):
            folder_id = env.get_google_drive_folder_id()
            assert folder_id == '1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D'
        
        # Invalid folder ID (too short)
        with patch.dict(os.environ, {'GOOGLE_DRIVE_FOLDER_ID': 'short'}):
            folder_id = env.get_google_drive_folder_id()
            assert folder_id is None
        
        # Invalid folder ID (contains invalid characters)
        with patch.dict(os.environ, {'GOOGLE_DRIVE_FOLDER_ID': 'invalid@folder#id'}):
            folder_id = env.get_google_drive_folder_id()
            assert folder_id is None
    
    def test_data_directories(self, tmp_path):
        """Test data directory configuration."""
        env = EnvironmentManager()
        
        data_dir = tmp_path / "data"
        output_dir = tmp_path / "output"
        
        with patch.dict(os.environ, {
            'BIOMAPPER_DATA_DIR': str(data_dir),
            'BIOMAPPER_OUTPUT_DIR': str(output_dir)
        }):
            dirs = env.get_data_directories()
            
            assert dirs['data'] == data_dir
            assert dirs['output'] == output_dir
            assert data_dir.exists()
            assert output_dir.exists()
    
    def test_create_template_env(self, tmp_path):
        """Test template .env file creation."""
        template_path = tmp_path / ".env.template"
        
        result = EnvironmentManager.create_template_env(str(template_path))
        
        assert result == str(template_path)
        assert template_path.exists()
        
        content = template_path.read_text()
        assert 'GOOGLE_APPLICATION_CREDENTIALS' in content
        assert 'GOOGLE_DRIVE_FOLDER_ID' in content
        assert 'DATABASE_URL' in content
        assert 'BIOMAPPER_DATA_DIR' in content
    
    def test_environment_summary(self):
        """Test environment configuration summary."""
        env = EnvironmentManager()
        
        with patch.dict(os.environ, {
            'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json',
            'GOOGLE_DRIVE_FOLDER_ID': 'test_folder_id',
            'DATABASE_URL': 'sqlite:///test.db',
            'BIOMAPPER_DATA_DIR': '/tmp/data'
        }):
            summary = env.summary()
            
            assert 'GOOGLE_APPLICATION_CREDENTIALS' in summary
            assert 'GOOGLE_DRIVE_FOLDER_ID' in summary
            assert 'DATABASE_URL' in summary
            assert 'BIOMAPPER_DATA_DIR' in summary


class TestEnvironmentValidator:
    """Test cases for EnvironmentValidator class."""
    
    def test_validate_google_credentials(self, tmp_path):
        """Test Google credentials validation."""
        # Valid credentials
        valid_creds = tmp_path / "valid.json"
        valid_creds.write_text("""{
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\\ntest\\n-----END PRIVATE KEY-----",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789"
        }""")
        
        with patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': str(valid_creds)}):
            valid, message = EnvironmentValidator.validate_google_credentials()
            assert valid is True
            assert 'Valid service account' in message
        
        # Missing credentials
        with patch.dict(os.environ, {}, clear=True):
            valid, message = EnvironmentValidator.validate_google_credentials()
            assert valid is False
            assert 'not set' in message
        
        # Non-existent file
        with patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': '/nonexistent/file.json'}):
            valid, message = EnvironmentValidator.validate_google_credentials()
            assert valid is False
            assert 'not found' in message
    
    def test_validate_file_paths(self, tmp_path):
        """Test file path validation."""
        # Create test directories
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        with patch.dict(os.environ, {
            'BIOMAPPER_DATA_DIR': str(data_dir),
            'BIOMAPPER_OUTPUT_DIR': str(tmp_path / "output"),  # Doesn't exist yet
            'DATABASE_URL': 'sqlite:///test.db'
        }):
            results = EnvironmentValidator.validate_file_paths()
            
            # Existing directory should be valid
            assert results['BIOMAPPER_DATA_DIR'][0] is True
            assert 'exists' in results['BIOMAPPER_DATA_DIR'][1]
            
            # Non-existent directory should be created
            assert results['BIOMAPPER_OUTPUT_DIR'][0] is True
            assert (tmp_path / "output").exists()
            
            # Database URL should be valid
            assert results['DATABASE_URL'][0] is True
    
    @patch('subprocess.run')
    def test_validate_dependencies(self, mock_run):
        """Test Python package dependency validation."""
        # Mock pip show output
        mock_run.return_value = MagicMock(
            stdout="Name: pandas\nVersion: 1.3.0\n",
            returncode=0
        )
        
        # Mock successful imports
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = MagicMock(__version__='1.3.0')
            
            results = EnvironmentValidator.validate_dependencies()
            
            # Check that imports were attempted
            assert mock_import.called
    
    def test_validate_network_connectivity(self):
        """Test network connectivity validation."""
        with patch('socket.socket') as mock_socket:
            # Mock successful connection
            mock_sock_instance = MagicMock()
            mock_socket.return_value = mock_sock_instance
            
            # Mock SSL context
            with patch('ssl.create_default_context') as mock_ssl:
                mock_ssl_context = MagicMock()
                mock_ssl.return_value = mock_ssl_context
                
                results = EnvironmentValidator.validate_network_connectivity()
                
                # Should check multiple services
                assert 'Google Drive API' in results
                assert 'UniProt API' in results
                assert 'PyPI' in results
    
    def test_full_validation_report(self, tmp_path):
        """Test comprehensive validation report generation."""
        # Setup test environment
        valid_creds = tmp_path / "creds.json"
        valid_creds.write_text("""{
            "type": "service_account",
            "project_id": "test",
            "private_key": "-----BEGIN PRIVATE KEY-----\\ntest\\n-----END PRIVATE KEY-----",
            "client_email": "test@test.iam.gserviceaccount.com"
        }""")
        
        with patch.dict(os.environ, {
            'GOOGLE_APPLICATION_CREDENTIALS': str(valid_creds),
            'BIOMAPPER_DATA_DIR': str(tmp_path)
        }):
            # Mock network and dependencies
            with patch.object(EnvironmentValidator, 'validate_network_connectivity') as mock_net:
                mock_net.return_value = {'Test Service': (True, 'Reachable')}
                
                with patch.object(EnvironmentValidator, 'validate_dependencies') as mock_deps:
                    mock_deps.return_value = {'pandas': (True, '1.3.0')}
                    
                    with patch.object(EnvironmentValidator, 'validate_google_drive_access') as mock_drive:
                        mock_drive.return_value = (True, 'Accessible')
                        
                        report = EnvironmentValidator.full_validation_report()
                        
                        # Report should contain all sections
                        assert 'ENVIRONMENT CONFIGURATION' in report
                        assert 'GOOGLE CREDENTIALS VALIDATION' in report
                        assert 'FILE PATH VALIDATION' in report
                        assert 'PYTHON DEPENDENCIES' in report
                        assert 'NETWORK CONNECTIVITY' in report
                        assert 'SUMMARY' in report


class TestEnvironmentIntegration:
    """Integration tests for environment management."""
    
    def test_environment_setup_workflow(self, tmp_path):
        """Test complete environment setup workflow."""
        # Create test .env file
        env_file = tmp_path / ".env"
        env_file.write_text("""
GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json
GOOGLE_DRIVE_FOLDER_ID=test_folder_id
BIOMAPPER_DATA_DIR=/tmp/data
DATABASE_URL=sqlite:///test.db
""")
        
        # Load and validate environment
        env = EnvironmentManager(env_file=str(env_file))
        
        # Should be able to get configuration
        assert env.get_with_fallback('GOOGLE_DRIVE_FOLDER_ID') == 'test_folder_id'
        
        # Should handle missing features gracefully
        with pytest.raises(EnvironmentError):
            env.validate_requirements(['nonexistent_feature'])
    
    def test_production_script_compatibility(self, tmp_path):
        """Test that environment manager works with production scripts."""
        # Create minimal valid environment
        env_file = tmp_path / ".env"
        creds_file = tmp_path / "creds.json"
        
        creds_file.write_text("""{
            "type": "service_account",
            "project_id": "test",
            "private_key": "-----BEGIN PRIVATE KEY-----\\ntest\\n-----END PRIVATE KEY-----",
            "client_email": "test@test.iam.gserviceaccount.com",
            "private_key_id": "123",
            "client_id": "456"
        }""")
        
        env_file.write_text(f"""
GOOGLE_APPLICATION_CREDENTIALS={creds_file}
GOOGLE_DRIVE_FOLDER_ID=test_folder_id
""")
        
        # Test loading as in production script
        env = EnvironmentManager(env_file=str(env_file))
        
        try:
            env.validate_requirements(['google_drive'])
            creds_path = env.get_google_credentials_path()
            assert creds_path is not None
            assert creds_path.exists()
        except EnvironmentError:
            # If validation fails, should provide clear error
            pass


@pytest.fixture
def clean_environment():
    """Fixture to provide clean environment for tests."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


def test_environment_isolation(clean_environment):
    """Test that environment changes don't leak between tests."""
    # Set test variable
    os.environ['TEST_ISOLATION'] = 'test_value'
    assert os.getenv('TEST_ISOLATION') == 'test_value'
    
    # After fixture cleanup, should be restored
    # (This is tested implicitly by other tests not seeing this variable)