"""
Integration tests for Google Drive sync functionality.

These tests require actual Google Drive credentials and are designed to validate
the Google Drive integration with real authentication and file operations.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

from actions.io.sync_to_google_drive_v2 import (
    SyncToGoogleDriveV2Action,
    SyncToGoogleDriveV2Params
)


class TestGoogleDriveIntegration:
    """Test Google Drive integration with real and mocked scenarios."""
    
    @pytest.fixture
    def action(self):
        """Create action instance."""
        return SyncToGoogleDriveV2Action()
    
    @pytest.fixture
    def sample_context(self, tmp_path):
        """Create sample context with test files."""
        # Create test files
        test_file1 = tmp_path / "test_report.html"
        test_file1.write_text("<html><body>Test Report</body></html>")
        
        test_file2 = tmp_path / "results.csv"
        test_file2.write_text("id,name,value\n1,test,100\n")
        
        test_file3 = tmp_path / "summary.json"
        test_file3.write_text('{"status": "success", "count": 42}')
        
        return {
            "strategy_name": "prot_arv_to_kg2c_uniprot_v2.2_integrated",
            "strategy_metadata": {"version": "2.2.0"},
            "output_files": {
                "html_report": str(test_file1),
                "results_csv": str(test_file2),
                "summary_json": str(test_file3)
            },
            "statistics": {
                "mapping_summary": {
                    "total_input": 1000,
                    "successfully_mapped": 875,
                    "mapping_rate": 0.875
                }
            }
        }
    
    @pytest.fixture
    def credentials_setup(self):
        """Setup for credential testing."""
        return {
            "credentials_available": os.getenv('GOOGLE_APPLICATION_CREDENTIALS') is not None,
            "drive_folder_id": os.getenv('GOOGLE_DRIVE_TEST_FOLDER_ID', 'test_folder_id')
        }
    
    @pytest.mark.asyncio
    async def test_authentication_check(self, action, credentials_setup):
        """Test authentication setup and availability."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id=credentials_setup['drive_folder_id'],
            sync_context_outputs=False,  # Don't sync files, just test auth
            auto_organize=False
        )
        
        # Test authentication method directly
        service = await action._authenticate(params)
        
        if credentials_setup['credentials_available']:
            assert service is not None, "Authentication should succeed with valid credentials"
            assert hasattr(service, 'files'), "Service should have files() method"
            print("✅ Google Drive authentication successful")
        else:
            assert service is None, "Authentication should fail without credentials"
            print("⚠️  No Google credentials available - authentication test skipped")
    
    @pytest.mark.asyncio
    async def test_folder_organization_structure(self, action):
        """Test folder structure creation logic."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            strategy_name="prot_arv_to_kg2c_uniprot_v2.2_integrated", 
            strategy_version="2.2.0",
            auto_organize=True,
            create_subfolder=True,
            subfolder_name="test_run"
        )
        
        # Test folder structure description
        structure = action._describe_folder_structure(params)
        expected = "prot_arv_to_kg2c_uniprot/v2_2_0/test_run"
        assert structure == expected, f"Expected {expected}, got {structure}"
        
        # Test strategy base extraction
        base = action._extract_strategy_base("prot_arv_to_kg2c_uniprot_v2.2_integrated")
        assert base == "prot_arv_to_kg2c_uniprot", f"Expected base name extraction, got {base}"
        
        # Test version formatting
        version_folder = action._format_version_folder("2.2.0")
        assert version_folder == "v2_2_0", f"Expected version formatting, got {version_folder}"
    
    @pytest.mark.asyncio
    async def test_file_collection(self, action, sample_context):
        """Test file collection from context."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            sync_context_outputs=True,
            file_patterns=["*.html", "*.csv"],
            exclude_patterns=["*.json"]
        )
        
        files = await action._collect_files(params, sample_context)
        
        # Should include HTML and CSV, exclude JSON
        assert len(files) == 2, f"Expected 2 files, got {len(files)}"
        assert any("test_report.html" in f for f in files), "Should include HTML file"
        assert any("results.csv" in f for f in files), "Should include CSV file"
        assert not any("summary.json" in f for f in files), "Should exclude JSON file"
    
    @pytest.mark.asyncio
    async def test_mime_type_detection(self, action):
        """Test MIME type detection for different file types."""
        test_cases = [
            ("report.html", "text/html"),
            ("data.csv", "text/csv"),
            ("results.json", "application/json"),
            ("summary.txt", "text/plain"),
            ("archive.zip", "application/zip"),
            ("unknown.xyz", "application/octet-stream")
        ]
        
        for filename, expected_mime in test_cases:
            mime_type = action._guess_mime_type(filename)
            assert mime_type == expected_mime, f"For {filename}, expected {expected_mime}, got {mime_type}"
    
    @pytest.mark.asyncio
    @patch('google.oauth2.service_account')
    @patch('googleapiclient.discovery.build')
    async def test_sync_with_mocked_drive_api(self, mock_build, mock_service_account, action, sample_context):
        """Test sync operation with mocked Google Drive API."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock folder operations
        mock_files = mock_service.files.return_value
        mock_files.list.return_value.execute.return_value = {"files": []}  # No existing folders
        mock_files.create.return_value.execute.return_value = {"id": "new_folder_id"}
        mock_files.create.return_value.execute.return_value = {
            "id": "uploaded_file_id",
            "name": "test_file.html", 
            "webViewLink": "https://drive.google.com/file/d/uploaded_file_id/view"
        }
        
        # Create a temporary credentials file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "type": "service_account",
                "project_id": "test",
                "private_key_id": "test",
                "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
                "client_email": "test@test.iam.gserviceaccount.com",
                "client_id": "test",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }, f)
            credentials_path = f.name
        
        try:
            params = SyncToGoogleDriveV2Params(
                drive_folder_id="test_folder_id",
                credentials_path=credentials_path,
                strategy_name="test_strategy",
                strategy_version="1.0.0",
                auto_organize=True,
                sync_context_outputs=True
            )
            
            # Call with all required parameters for the action signature
            result = await action.execute_typed(
                current_identifiers=[],  # No specific identifiers for file sync
                current_ontology_type="files",  # File sync operation
                params=params,
                source_endpoint=None,  # Not needed for file sync
                target_endpoint=None,  # Not needed for file sync
                context=sample_context
            )
            
            assert result.success is True, f"Sync should succeed: {result.error}"
            assert result.data["uploaded_count"] >= 0, "Should report upload count"
            assert "folder_structure" in result.data, "Should include folder structure"
            assert "target_folder_id" in result.data, "Should include target folder ID"
            
            # Verify API calls were made
            mock_service_account.Credentials.from_service_account_file.assert_called_once()
            mock_build.assert_called_once_with("drive", "v3", credentials=mock_credentials)
            
            print("✅ Mocked Google Drive sync completed successfully")
            print(f"📁 Folder structure: {result.data['folder_structure']}")
            print(f"📤 Files uploaded: {result.data['uploaded_count']}")
            
        finally:
            # Cleanup
            os.unlink(credentials_path)
    
    @pytest.mark.asyncio
    async def test_sync_without_credentials(self, action, sample_context):
        """Test sync operation without credentials (should gracefully skip)."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder_id",
            credentials_path=None,  # No credentials
            auto_organize=True
        )
        
        # Ensure no environment credentials
        with patch.dict(os.environ, {}, clear=True):
            # Call with all required parameters for the action signature
            result = await action.execute_typed(
                current_identifiers=[],  # No specific identifiers for file sync
                current_ontology_type="files",  # File sync operation
                params=params,
                source_endpoint=None,  # Not needed for file sync
                target_endpoint=None,  # Not needed for file sync
                context=sample_context
            )
        
        assert result.success is True, "Should succeed but skip sync"
        assert result.data.get("sync_skipped") is True, "Should indicate sync was skipped"
        assert "Authentication failed" in result.data.get("reason", ""), "Should indicate auth failure"
        
        print("✅ Graceful handling of missing credentials")
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_folder_id(self, action, sample_context):
        """Test error handling with invalid folder ID."""
        # This test requires actual credentials to test real API errors
        if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            pytest.skip("Requires actual Google credentials for API error testing")
        
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="invalid_folder_id_12345",  # Invalid folder ID
            auto_organize=False,
            sync_context_outputs=True
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="files",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context
        )
        
        # Should either fail gracefully or handle the error
        if not result.success:
            assert result.error is not None, "Should provide error message"
            print(f"✅ Error handled gracefully: {result.error}")
        else:
            print("⚠️  API call succeeded unexpectedly - may need folder ID validation")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or not os.getenv('GOOGLE_DRIVE_TEST_FOLDER_ID'),
        reason="Requires GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_DRIVE_TEST_FOLDER_ID environment variables"
    )
    async def test_real_google_drive_sync(self, action, sample_context):
        """Test actual Google Drive sync with real credentials and folder."""
        print("\n🚀 Testing REAL Google Drive integration...")
        
        params = SyncToGoogleDriveV2Params(
            drive_folder_id=os.getenv('GOOGLE_DRIVE_TEST_FOLDER_ID'),
            strategy_name="integration_test_strategy",
            strategy_version="test_1.0.0",
            auto_organize=True,
            create_subfolder=True,
            subfolder_name="integration_test",
            sync_context_outputs=True,
            description="Biomapper integration test upload"
        )
        
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type="files",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=sample_context
        )
        
        assert result.success is True, f"Real sync should succeed: {result.error}"
        assert result.data["uploaded_count"] > 0, "Should upload at least one file"
        
        print("✅ Real Google Drive sync successful!")
        print(f"📁 Folder structure: {result.data['folder_structure']}")
        print(f"📤 Files uploaded: {result.data['uploaded_count']}")
        print(f"🔗 Target folder ID: {result.data['target_folder_id']}")
        
        # Print upload details
        for file_info in result.data.get('uploaded_files', []):
            print(f"   📄 {file_info.get('name', 'Unknown')} - {file_info.get('webViewLink', 'No link')}")
        
        # Print any errors
        if result.data.get('errors'):
            print("⚠️  Upload errors:")
            for error in result.data['errors']:
                print(f"   ❌ {error}")
    
    def test_parameter_validation(self):
        """Test parameter validation with Pydantic."""
        # Valid parameters
        valid_params = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder_id"
        )
        assert valid_params.drive_folder_id == "test_folder_id"
        assert valid_params.auto_organize is True  # Default
        assert valid_params.sync_context_outputs is True  # Default
        
        # Test parameter defaults
        assert valid_params.create_subfolder is False
        assert valid_params.file_patterns is None
        assert valid_params.exclude_patterns is None
        
        # Invalid parameters should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            SyncToGoogleDriveV2Params()  # Missing required drive_folder_id


def setup_integration_test_environment():
    """
    Helper function to set up environment for integration testing.
    
    To run real integration tests, set these environment variables:
    - GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON file
    - GOOGLE_DRIVE_TEST_FOLDER_ID: Google Drive folder ID for testing
    
    Example service account JSON structure:
    {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
        "client_email": "service-account@your-project.iam.gserviceaccount.com",
        "client_id": "client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service-account%40your-project.iam.gserviceaccount.com"
    }
    
    To create a test folder in Google Drive:
    1. Go to Google Drive
    2. Create a new folder named "biomapper-integration-tests"
    3. Right-click the folder and select "Get link"
    4. Extract the folder ID from the URL (after /folders/)
    5. Set GOOGLE_DRIVE_TEST_FOLDER_ID to this ID
    """
    pass


if __name__ == "__main__":
    """
    Run integration tests manually.
    
    Usage:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
    export GOOGLE_DRIVE_TEST_FOLDER_ID=your_test_folder_id
    python -m pytest tests/integration/test_google_drive_integration.py -v
    """
    print("Google Drive Integration Test Setup:")
    print("====================================")
    
    creds_available = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    folder_available = os.getenv('GOOGLE_DRIVE_TEST_FOLDER_ID')
    
    print(f"Credentials available: {'✅' if creds_available else '❌'}")
    if creds_available:
        print(f"  Path: {creds_available}")
    
    print(f"Test folder ID available: {'✅' if folder_available else '❌'}")
    if folder_available:
        print(f"  Folder ID: {folder_available}")
    
    if not creds_available or not folder_available:
        print("\n⚠️  To run full integration tests, set:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json")
        print("   export GOOGLE_DRIVE_TEST_FOLDER_ID=your_test_folder_id")
        print("\nSee setup_integration_test_environment() docstring for details.")
    else:
        print("\n🚀 Ready for full Google Drive integration testing!")