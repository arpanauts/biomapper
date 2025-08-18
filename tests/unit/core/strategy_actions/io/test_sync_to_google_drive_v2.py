"""Tests for Google Drive sync action."""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.actions.io.sync_to_google_drive_v2 import (
    SyncToGoogleDriveV2Action,
    SyncToGoogleDriveV2Params,
    SyncActionResult,
)


class TestSyncToGoogleDriveV2Action:
    """Test Google Drive sync action functionality."""
    
    @pytest.fixture
    def action_params(self):
        """Create test action parameters."""
        return SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder_id_123",
            auto_organize=True,
            strategy_name="test_protein_strategy",
            strategy_version="1.0.0",
            sync_context_outputs=True,
            create_subfolder=False,
            credentials_path="/test/credentials.json"
        )
    
    @pytest.fixture
    def google_drive_action(self):
        """Create Google Drive action instance."""
        return SyncToGoogleDriveV2Action()
    
    @pytest.fixture
    def mock_google_service(self):
        """Create mock Google Drive service."""
        service = MagicMock()
        
        # Mock files API
        service.files.return_value.create.return_value.execute.return_value = {
            "id": "test-file-id-123",
            "name": "test-file.csv",
            "webViewLink": "https://drive.google.com/file/d/test-file-id-123/view"
        }
        
        # Mock folder listing
        service.files.return_value.list.return_value.execute.return_value = {
            "files": []  # Empty by default, can be overridden in specific tests
        }
        
        return service
    
    @pytest.fixture
    def test_context(self):
        """Create test execution context."""
        return {
            "strategy_name": "test_protein_strategy",
            "strategy_metadata": {"version": "1.0.0"},
            "output_files": {
                "mapped_proteins": "/tmp/mapped_proteins.csv",
                "statistics": "/tmp/stats.json",
                "report": "/tmp/report.html"
            },
            "datasets": {
                "input_data": "mock_input_dataframe",
                "results": "mock_results_dataframe"
            }
        }
    
    @pytest.fixture
    def test_file_data(self):
        """Create test file data."""
        return {
            "mapped_proteins.csv": "protein_id,gene_symbol\nP04637,TP53\nP38398,BRCA1",
            "stats.json": '{"mapped_count": 2, "unmapped_count": 0}',
            "report.html": "<html><body>Test Report</body></html>"
        }
    
    def test_action_params_model(self):
        """Test action parameters model validation."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="folder_123",
            strategy_name="test_strategy",
            auto_organize=True
        )
        
        assert params.drive_folder_id == "folder_123"
        assert params.strategy_name == "test_strategy"
        assert params.auto_organize is True
        assert params.sync_context_outputs is True  # Default value
        assert params.create_subfolder is False  # Default value
    
    def test_action_result_model(self):
        """Test action result model."""
        result = SyncActionResult(
            success=True,
            data={
                "uploaded_count": 3,
                "folder_structure": "test_strategy/v1_0_0",
                "uploaded_files": ["file1.csv", "file2.json"]
            }
        )
        
        assert result.success is True
        assert result.data["uploaded_count"] == 3
        assert result.error is None
    
    @pytest.mark.asyncio
    @patch('google.oauth2.service_account')
    @patch('googleapiclient.discovery.build')
    async def test_authenticate_success(self, mock_build, mock_service_account, google_drive_action, action_params):
        """Test successful Google Drive authentication."""
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        result = await google_drive_action._authenticate(action_params)
        
        assert result == mock_service
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with(
            action_params.credentials_path,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_credentials)
    
    @pytest.mark.asyncio
    async def test_authenticate_import_error(self, google_drive_action, action_params):
        """Test authentication with missing Google API dependencies."""
        # Mock ImportError by temporarily replacing the imports
        import sys
        
        # Store original modules if they exist
        original_service_account = sys.modules.get('google.oauth2.service_account')
        original_build = sys.modules.get('googleapiclient.discovery')
        
        # Remove modules to simulate ImportError
        if 'google.oauth2.service_account' in sys.modules:
            del sys.modules['google.oauth2.service_account']
        if 'googleapiclient.discovery' in sys.modules:
            del sys.modules['googleapiclient.discovery']
        
        try:
            result = await google_drive_action._authenticate(action_params)
            assert result is None
        finally:
            # Restore original modules
            if original_service_account:
                sys.modules['google.oauth2.service_account'] = original_service_account
            if original_build:
                sys.modules['googleapiclient.discovery'] = original_build
    
    @pytest.mark.asyncio
    async def test_authenticate_no_credentials_path(self, google_drive_action):
        """Test authentication without credentials path."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            credentials_path=None
        )
        
        with patch.dict(os.environ, {}, clear=True):  # Clear GOOGLE_APPLICATION_CREDENTIALS
            result = await google_drive_action._authenticate(params)
            
            assert result is None
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': '/env/credentials.json'})
    @patch('google.oauth2.service_account')
    @patch('googleapiclient.discovery.build')
    @pytest.mark.asyncio 
    async def test_authenticate_from_environment(self, mock_build, mock_service_account, google_drive_action):
        """Test authentication using environment variable."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            credentials_path=None
        )
        
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        result = await google_drive_action._authenticate(params)
        
        assert result == mock_service
        mock_service_account.Credentials.from_service_account_file.assert_called_once_with(
            '/env/credentials.json',
            scopes=["https://www.googleapis.com/auth/drive"]
        )
    
    def test_extract_strategy_base(self, google_drive_action):
        """Test strategy name base extraction."""
        # Test version pattern removal
        assert google_drive_action._extract_strategy_base("prot_arv_to_kg2c_uniprot_v1_base") == "prot_arv_to_kg2c_uniprot"
        assert google_drive_action._extract_strategy_base("strategy_v2_enhanced") == "strategy"
        assert google_drive_action._extract_strategy_base("test_v2.2_integrated") == "test"
        assert google_drive_action._extract_strategy_base("simple_v3") == "simple"
        
        # Test names without version patterns
        assert google_drive_action._extract_strategy_base("simple_strategy") == "simple_strategy"
        assert google_drive_action._extract_strategy_base("test") == "test"
    
    def test_format_version_folder(self, google_drive_action):
        """Test version folder name formatting."""
        assert google_drive_action._format_version_folder("1.0.0") == "v1_0_0"
        assert google_drive_action._format_version_folder("2.1") == "v2_1"
        assert google_drive_action._format_version_folder("3") == "v3"
    
    @pytest.mark.asyncio
    async def test_find_or_create_folder_existing(self, google_drive_action, mock_google_service):
        """Test finding existing folder."""
        # Mock existing folder found
        mock_google_service.files.return_value.list.return_value.execute.return_value = {
            "files": [{"id": "existing_folder_id", "name": "test_folder"}]
        }
        
        result = await google_drive_action._find_or_create_folder(
            mock_google_service, "test_folder", "parent_id"
        )
        
        assert result == "existing_folder_id"
        
        # Verify search query was called
        mock_google_service.files.return_value.list.assert_called_once()
        call_args = mock_google_service.files.return_value.list.call_args
        assert "q" in call_args.kwargs
        assert "test_folder" in call_args.kwargs["q"]
    
    @pytest.mark.asyncio 
    async def test_find_or_create_folder_create_new(self, google_drive_action, mock_google_service):
        """Test creating new folder when not found."""
        # Mock no existing folder found
        mock_google_service.files.return_value.list.return_value.execute.return_value = {
            "files": []
        }
        
        # Mock folder creation
        mock_google_service.files.return_value.create.return_value.execute.return_value = {
            "id": "new_folder_id"
        }
        
        result = await google_drive_action._find_or_create_folder(
            mock_google_service, "new_folder", "parent_id"
        )
        
        assert result == "new_folder_id"
        
        # Verify folder creation was called
        mock_google_service.files.return_value.create.assert_called_once()
        create_call_args = mock_google_service.files.return_value.create.call_args
        assert create_call_args.kwargs["body"]["name"] == "new_folder"
        assert create_call_args.kwargs["body"]["parents"] == ["parent_id"]
    
    @pytest.mark.asyncio 
    async def test_create_organized_folders(self, google_drive_action, mock_google_service, action_params):
        """Test organized folder structure creation."""
        # Mock folder creation responses
        mock_google_service.files.return_value.list.return_value.execute.return_value = {
            "files": []  # No existing folders
        }
        
        mock_google_service.files.return_value.create.return_value.execute.side_effect = [
            {"id": "strategy_folder_id"},
            {"id": "version_folder_id"}
        ]
        
        result = await google_drive_action._create_organized_folders(
            mock_google_service, action_params
        )
        
        assert result == "version_folder_id"
        
        # Verify two folders were created (strategy base + version)
        assert mock_google_service.files.return_value.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_collect_files_from_context(self, google_drive_action, action_params, test_context):
        """Test file collection from context outputs."""
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_files = []
            for filename, content in [
                ("mapped_proteins.csv", "id,name\n1,test"),
                ("stats.json", '{"count": 1}'),
                ("report.html", "<html></html>")
            ]:
                file_path = Path(temp_dir) / filename
                file_path.write_text(content)
                test_files.append(str(file_path))
            
            # Update context with actual file paths
            updated_context = test_context.copy()
            updated_context["output_files"] = {
                "proteins": str(test_files[0]),
                "stats": str(test_files[1]),
                "report": str(test_files[2])
            }
            
            files = await google_drive_action._collect_files(action_params, updated_context)
            
            assert len(files) == 3
            assert all(Path(f).exists() for f in files)
    
    @pytest.mark.asyncio
    async def test_collect_files_from_local_directory(self, google_drive_action):
        """Test file collection from local directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            (Path(temp_dir) / "test1.csv").write_text("data1")
            (Path(temp_dir) / "test2.json").write_text("data2")
            (Path(temp_dir) / "ignore.bak").write_text("backup")
            
            params = SyncToGoogleDriveV2Params(
                drive_folder_id="test_folder",
                local_directory=temp_dir,
                include_patterns=["*.csv", "*.json"],
                sync_context_outputs=False
            )
            
            files = await google_drive_action._collect_files(params, {})
            
            assert len(files) == 2
            assert any("test1.csv" in f for f in files)
            assert any("test2.json" in f for f in files)
            assert not any("ignore.bak" in f for f in files)
    
    def test_filter_files_include_patterns(self, google_drive_action):
        """Test file filtering with include patterns."""
        files = [
            "/path/to/data.csv",
            "/path/to/report.html",
            "/path/to/backup.bak",
            "/path/to/config.json"
        ]
        
        filtered = google_drive_action._filter_files(
            files, 
            include_patterns=["*.csv", "*.json"],
            exclude_patterns=None
        )
        
        assert len(filtered) == 2
        assert "/path/to/data.csv" in filtered
        assert "/path/to/config.json" in filtered
    
    def test_filter_files_exclude_patterns(self, google_drive_action):
        """Test file filtering with exclude patterns."""
        files = [
            "/path/to/data.csv",
            "/path/to/backup.bak",
            "/path/to/temp.tmp",
            "/path/to/report.html"
        ]
        
        filtered = google_drive_action._filter_files(
            files,
            include_patterns=None,
            exclude_patterns=["*.bak", "*.tmp"]
        )
        
        assert len(filtered) == 2
        assert "/path/to/data.csv" in filtered
        assert "/path/to/report.html" in filtered
    
    def test_filter_files_combined_patterns(self, google_drive_action):
        """Test file filtering with both include and exclude patterns."""
        files = [
            "/path/to/data.csv",
            "/path/to/backup.csv",
            "/path/to/report.html",
            "/path/to/config.json"
        ]
        
        filtered = google_drive_action._filter_files(
            files,
            include_patterns=["*.csv", "*.json"],
            exclude_patterns=["*backup*"]
        )
        
        assert len(filtered) == 2
        assert "/path/to/data.csv" in filtered
        assert "/path/to/config.json" in filtered
        assert "/path/to/backup.csv" not in filtered
    
    @patch('googleapiclient.http.MediaFileUpload')
    @pytest.mark.asyncio 
    async def test_upload_file_success(self, mock_media_upload, google_drive_action, mock_google_service, action_params):
        """Test successful file upload."""
        mock_media = MagicMock()
        mock_media_upload.return_value = mock_media
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write("test,data\n1,value")
            temp_file_path = temp_file.name
        
        try:
            result = await google_drive_action._upload_file(
                mock_google_service, temp_file_path, "folder_id", action_params
            )
            
            assert result["id"] == "test-file-id-123"
            assert "webViewLink" in result
            
            # Verify MediaFileUpload was called correctly
            mock_media_upload.assert_called_once()
            upload_args = mock_media_upload.call_args
            assert upload_args[0][0] == temp_file_path
            assert upload_args.kwargs["resumable"] is True
            
            # Verify Drive API was called
            mock_google_service.files.return_value.create.assert_called_once()
            
        finally:
            os.unlink(temp_file_path)
    
    def test_guess_mime_type(self, google_drive_action):
        """Test MIME type guessing from file extensions."""
        assert google_drive_action._guess_mime_type("data.csv") == "text/csv"
        assert google_drive_action._guess_mime_type("report.html") == "text/html"
        assert google_drive_action._guess_mime_type("config.json") == "application/json"
        assert google_drive_action._guess_mime_type("document.pdf") == "application/pdf"
        assert google_drive_action._guess_mime_type("archive.zip") == "application/zip"
        assert google_drive_action._guess_mime_type("unknown.xyz") == "application/octet-stream"
    
    def test_describe_folder_structure(self, google_drive_action):
        """Test folder structure description."""
        params_auto = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            auto_organize=True,
            strategy_name="prot_arv_to_kg2c_uniprot_v1_base",
            strategy_version="1.0.0",
            create_subfolder=False
        )
        
        description = google_drive_action._describe_folder_structure(params_auto)
        assert description == "prot_arv_to_kg2c_uniprot/v1_0_0"
        
        params_no_auto = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            auto_organize=False
        )
        
        description = google_drive_action._describe_folder_structure(params_no_auto)
        assert description == "Direct upload to specified folder"
        
        params_with_subfolder = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            auto_organize=True,
            strategy_name="test_strategy",
            strategy_version="2.0",
            create_subfolder=True,
            subfolder_name="custom_run"
        )
        
        description = google_drive_action._describe_folder_structure(params_with_subfolder)
        assert description == "test_strategy/v2_0/custom_run"


class TestGoogleDriveIntegrationScenarios:
    """Test complete integration scenarios."""
    
    @pytest.fixture
    def google_drive_action(self):
        """Create Google Drive action instance."""
        return SyncToGoogleDriveV2Action()
    
    @pytest.mark.asyncio
    @patch('google.oauth2.service_account')
    @patch('googleapiclient.discovery.build')
    @patch('googleapiclient.http.MediaFileUpload')
    @pytest.mark.asyncio 
    async def test_execute_typed_full_workflow(self, mock_media_upload, mock_build, mock_service_account, google_drive_action):
        """Test complete execution workflow."""
        # Setup mocks
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock folder operations
        mock_service.files.return_value.list.return_value.execute.return_value = {"files": []}
        
        # Mock folder creation and file upload - need to handle all .create() calls
        mock_service.files.return_value.create.return_value.execute.side_effect = [
            {"id": "strategy_folder_id"},      # First folder creation
            {"id": "version_folder_id"},       # Second folder creation  
            {                                  # File upload
                "id": "uploaded_file_id",
                "name": "test_file.csv",
                "webViewLink": "https://drive.google.com/file/d/uploaded_file_id/view"
            }
        ]
        
        mock_media = MagicMock()
        mock_media_upload.return_value = mock_media
        
        # Create test context and files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_data.csv"
            test_file.write_text("protein_id,gene_symbol\nP04637,TP53")
            
            context = {
                "strategy_name": "test_protein_strategy",
                "strategy_metadata": {"version": "1.0.0"},
                "output_files": {
                    "results": str(test_file)
                }
            }
            
            params = SyncToGoogleDriveV2Params(
                drive_folder_id="root_folder_id",
                auto_organize=True,
                credentials_path="/test/credentials.json"
            )
            
            result = await google_drive_action.execute_typed(
                current_identifiers=[],
                current_ontology_type="protein",
                params=params,
                source_endpoint=None,
                target_endpoint=None,
                context=context
            )
            
            assert result.success is True
            assert result.data["uploaded_count"] == 1
            assert result.data["target_folder_id"] == "version_folder_id"
            assert len(result.data["uploaded_files"]) == 1
            assert len(result.data["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_execute_typed_authentication_failure(self, google_drive_action):
        """Test execution with authentication failure."""
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="test_folder",
            credentials_path="/nonexistent/credentials.json"
        )
        
        context = {}
        
        result = await google_drive_action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        assert result.success is True  # Graceful handling
        assert result.data["sync_skipped"] is True
        assert result.data["reason"] == "Authentication failed"
    
    @pytest.mark.asyncio
    @patch('google.oauth2.service_account')
    @patch('googleapiclient.discovery.build')
    @pytest.mark.asyncio 
    async def test_execute_typed_api_error_handling(self, mock_build, mock_service_account, google_drive_action):
        """Test execution with Google Drive API errors."""
        from googleapiclient.errors import HttpError
        
        # Setup authentication mocks
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_file.return_value = mock_credentials
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock API error
        error_response = MagicMock()
        error_response.status = 404
        mock_service.files.return_value.list.side_effect = HttpError(
            resp=error_response,
            content=b'{"error": {"message": "Folder not found"}}'
        )
        
        params = SyncToGoogleDriveV2Params(
            drive_folder_id="nonexistent_folder",
            credentials_path="/test/credentials.json"
        )
        
        context = {}
        
        result = await google_drive_action.execute_typed(
            current_identifiers=[],
            current_ontology_type="protein",
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        assert result.success is False
        assert "Google Drive sync failed" in result.error


class TestGoogleDrivePerformance:
    """Test Google Drive performance characteristics."""
    
    @pytest.fixture
    def google_drive_action(self):
        """Create Google Drive action instance."""
        return SyncToGoogleDriveV2Action()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_file_upload_performance(self, google_drive_action):
        """Test upload performance with large files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as large_file:
            # Create large test file (simulate 10MB)
            large_content = "protein_id,gene_symbol,description\n" * 100000  # ~3MB of text
            large_file.write(large_content)
            large_file_path = large_file.name
        
        try:
            with patch('googleapiclient.http.MediaFileUpload') as mock_media_upload:
                with patch('googleapiclient.discovery.build') as mock_build:
                    mock_service = MagicMock()
                    mock_build.return_value = mock_service
                    mock_service.files.return_value.create.return_value.execute.return_value = {
                        "id": "large_file_id", "name": "large_file.csv", "webViewLink": "test_link"
                    }
                    
                    mock_media = MagicMock()
                    mock_media_upload.return_value = mock_media
                    
                    params = SyncToGoogleDriveV2Params(drive_folder_id="test_folder")
                    
                    import time
                    start_time = time.time()
                    
                    result = await google_drive_action._upload_file(
                        mock_service, large_file_path, "folder_id", params
                    )
                    
                    execution_time = time.time() - start_time
                    
                    # Should complete upload simulation quickly
                    assert execution_time < 5.0
                    assert result["id"] == "large_file_id"
                    
                    # Verify chunked upload was used
                    mock_media_upload.assert_called_once()
                    upload_kwargs = mock_media_upload.call_args.kwargs
                    assert upload_kwargs["resumable"] is True
        
        finally:
            os.unlink(large_file_path)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_batch_upload_performance(self, google_drive_action):
        """Test performance with multiple file uploads."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple test files
            test_files = []
            for i in range(10):
                file_path = Path(temp_dir) / f"test_file_{i}.csv"
                file_path.write_text(f"data_{i},value_{i}\n")
                test_files.append(str(file_path))
            
            with patch('google.oauth2.service_account'):
                with patch('googleapiclient.discovery.build') as mock_build:
                    with patch('googleapiclient.http.MediaFileUpload'):
                        mock_service = MagicMock()
                        mock_build.return_value = mock_service
                        
                        # Mock successful folder creation
                        mock_service.files.return_value.list.return_value.execute.return_value = {"files": []}
                        mock_service.files.return_value.create.return_value.execute.return_value = {
                            "id": "test_folder_id"
                        }
                        
                        context = {
                            "output_files": {f"file_{i}": path for i, path in enumerate(test_files)}
                        }
                        
                        params = SyncToGoogleDriveV2Params(
                            drive_folder_id="test_folder",
                            credentials_path="/test/credentials.json"
                        )
                        
                        import time
                        start_time = time.time()
                        
                        result = await google_drive_action.execute_typed(
                            current_identifiers=[],
                            current_ontology_type="test",
                            params=params,
                            source_endpoint=None,
                            target_endpoint=None,
                            context=context
                        )
                        
                        execution_time = time.time() - start_time
                        
                        # Should handle multiple files efficiently
                        assert execution_time < 10.0
                        assert result.success is True


class TestBiologicalDataIntegration:
    """Test integration with realistic biological data scenarios."""
    
    @pytest.fixture
    def google_drive_action(self):
        """Create Google Drive action instance."""
        return SyncToGoogleDriveV2Action()
    
    @pytest.fixture
    def realistic_protein_data(self):
        """Create realistic protein mapping data."""
        return {
            "arivale_proteins.csv": (
                "identifier,protein_name,gene_symbol,organism\n"
                "P04637,Tumor protein p53,TP53,Homo sapiens\n"
                "P38398,BRCA1 protein,BRCA1,Homo sapiens\n"
                "Q6EMK4,Zinc finger protein,ZNF123,Homo sapiens\n"
            ),
            "mapping_statistics.json": json.dumps({
                "total_proteins": 3,
                "mapped_proteins": 3,
                "unmapped_proteins": 0,
                "mapping_rate": 1.0,
                "problematic_ids": ["Q6EMK4"]
            }),
            "mapping_report.html": (
                "<html><body>"
                "<h1>Protein Mapping Report</h1>"
                "<p>Successfully mapped 3 proteins from Arivale dataset</p>"
                "<p>Known problematic identifier Q6EMK4 was handled correctly</p>"
                "</body></html>"
            )
        }
    
    @pytest.mark.asyncio
    async def test_realistic_protein_mapping_sync(self, google_drive_action, realistic_protein_data):
        """Test sync with realistic protein mapping results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic protein mapping files
            file_paths = {}
            for filename, content in realistic_protein_data.items():
                file_path = Path(temp_dir) / filename
                file_path.write_text(content)
                file_paths[filename.split('.')[0]] = str(file_path)
            
            context = {
                "strategy_name": "prot_arv_to_kg2c_uniprot_v1_base",
                "strategy_metadata": {"version": "1.0.0"},
                "output_files": file_paths,
                "datasets": {
                    "arivale_proteins": "mock_dataframe_3_rows",
                    "mapped_results": "mock_dataframe_3_mapped"
                }
            }
            
            params = SyncToGoogleDriveV2Params(
                drive_folder_id="biomapper_results_folder",
                auto_organize=True,
                strategy_name="prot_arv_to_kg2c_uniprot_v1_base",
                strategy_version="1.0.0"
            )
            
            with patch.object(google_drive_action, '_authenticate') as mock_auth:
                with patch.object(google_drive_action, '_create_organized_folders') as mock_folders:
                    with patch.object(google_drive_action, '_upload_file') as mock_upload:
                        # Mock successful authentication and folder creation
                        mock_auth.return_value = MagicMock()
                        mock_folders.return_value = "prot_arv_to_kg2c_uniprot/v1_0_0/folder_id"
                        
                        # Mock successful file uploads
                        mock_upload.side_effect = [
                            {"id": f"file_{i}_id", "name": f"file_{i}"} 
                            for i in range(len(file_paths))
                        ]
                        
                        result = await google_drive_action.execute_typed(
                            current_identifiers=["P04637", "P38398", "Q6EMK4"],
                            current_ontology_type="protein",
                            params=params,
                            source_endpoint=None,
                            target_endpoint=None,
                            context=context
                        )
                        
                        assert result.success is True
                        assert result.data["uploaded_count"] == 3
                        assert "prot_arv_to_kg2c_uniprot/v1_0_0" in result.data["folder_structure"]
                        
                        # Verify all biological data files were uploaded
                        assert len(result.data["uploaded_files"]) == 3
                        assert result.data["errors"] == []
    
    @pytest.mark.asyncio
    async def test_edge_case_file_handling(self, google_drive_action):
        """Test handling of edge cases in biological data files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create edge case files
            edge_case_files = {
                "empty_results.csv": "",  # Empty file
                "large_protein_list.csv": "id,name\n" + "\n".join([f"P{i:05d},protein_{i}" for i in range(1000)]),  # Large file
                "special_chars.csv": "id,name\nP04637,TP53_αβγ\nP38398,BRCA1_特殊字符",  # Special characters
            }
            
            file_paths = {}
            for filename, content in edge_case_files.items():
                file_path = Path(temp_dir) / filename
                file_path.write_text(content, encoding='utf-8')
                file_paths[filename.split('.')[0]] = str(file_path)
            
            context = {"output_files": file_paths}
            params = SyncToGoogleDriveV2Params(drive_folder_id="test_folder")
            
            # Test file collection handles edge cases
            files = await google_drive_action._collect_files(params, context)
            
            assert len(files) == 3
            assert all(Path(f).exists() for f in files)
            
            # Verify files can be processed
            for file_path in files:
                assert Path(file_path).stat().st_size >= 0  # All files have valid size
                assert google_drive_action._guess_mime_type(file_path) == "text/csv"