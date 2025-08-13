# TDD Improvements for Google Drive Sync Implementation

## Critical Issue: Test-Driven Development Not Properly Followed

The current `GOOGLE_DRIVE_SYNC_IMPLEMENTATION_PROMPT.md` has testing in Phase 3, which violates TDD principles. Tests must be written FIRST, before any implementation.

## Recommended Phase Restructuring

### ❌ Current Structure (WRONG)
```
Phase 1: Core Implementation
Phase 2: Upload Implementation  
Phase 3: Integration & Testing ← Tests come too late!
Phase 4: Documentation
```

### ✅ TDD Structure (CORRECT)
```
Phase 1: Write Failing Tests (RED)
Phase 2: Minimal Implementation to Pass (GREEN)
Phase 3: Refactor & Improve (REFACTOR)
Phase 4: Repeat Cycle for New Features
```

## Phase 1: Write Comprehensive Failing Tests FIRST

### Test File Structure
Create this BEFORE any implementation:
```
tests/unit/core/strategy_actions/io/test_sync_to_google_drive.py
```

### Complete Test Suite to Write First

```python
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import tempfile
from datetime import datetime

# These imports will fail initially - that's expected in TDD!
from biomapper.core.strategy_actions.io.sync_to_google_drive import (
    SyncToGoogleDriveAction,
    SyncToGoogleDriveParams
)
from biomapper.core.models.action_results import ActionResult


class TestSyncToGoogleDriveParams:
    """Test the parameter model."""
    
    def test_minimal_params(self):
        """Test creation with minimal required parameters."""
        params = SyncToGoogleDriveParams(
            drive_folder_id="1A2B3C4D5E6F"
        )
        assert params.drive_folder_id == "1A2B3C4D5E6F"
        assert params.sync_context_outputs is True  # default
        assert params.create_subfolder is True  # default
    
    def test_all_params(self):
        """Test all parameter options."""
        params = SyncToGoogleDriveParams(
            drive_folder_id="folder123",
            sync_context_outputs=False,
            input_files=["/tmp/file1.csv", "/tmp/file2.json"],
            create_subfolder=False,
            subfolder_name="custom_name",
            description="Test upload",
            file_patterns=["*.csv"],
            exclude_patterns=["*temp*"],
            conflict_resolution="overwrite",
            chunk_size=5242880,
            max_retries=5,
            hard_failure=True,
            verbose=True,
            credentials_path="/path/to/creds.json",
            use_user_auth=False
        )
        assert params.conflict_resolution == "overwrite"
        assert params.chunk_size == 5242880
        assert params.max_retries == 5


class TestSyncToGoogleDriveAction:
    """Test the main action class."""
    
    @pytest.fixture
    def mock_drive_service(self):
        """Create a mock Google Drive service."""
        service = Mock()
        
        # Mock file creation
        service.files().create().execute.return_value = {
            'id': 'file_123',
            'name': 'test_file.csv',
            'webViewLink': 'https://drive.google.com/file/123'
        }
        
        # Mock folder creation
        service.files().list().execute.return_value = {
            'files': []  # No existing folders
        }
        
        return service
    
    @pytest.fixture
    def sample_context(self):
        """Create sample execution context."""
        return {
            'output_files': {
                'results': '/tmp/results.csv',
                'report': '/tmp/summary.md',
                'data': '/tmp/processed_data.json'
            },
            'datasets': {
                'proteins': {'row_count': 100}
            },
            'statistics': {
                'total_processed': 100,
                'success_rate': 0.95
            }
        }
    
    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary test files."""
        files = {}
        
        # Create test files
        for name, content in [
            ('results.csv', 'id,name,value\n1,test,100\n'),
            ('report.md', '# Test Report\nResults summary'),
            ('data.json', '{"test": "data"}'),
            ('large_file.bin', 'x' * (20 * 1024 * 1024))  # 20MB
        ]:
            file_path = tmp_path / name
            file_path.write_text(content)
            files[name] = str(file_path)
        
        return files
    
    # === CORE FUNCTIONALITY TESTS ===
    
    @pytest.mark.asyncio
    async def test_action_registers_correctly(self):
        """Test that action self-registers with correct name."""
        from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
        
        # This will fail until implementation exists
        assert 'SYNC_TO_GOOGLE_DRIVE' in ACTION_REGISTRY
        assert ACTION_REGISTRY['SYNC_TO_GOOGLE_DRIVE'] == SyncToGoogleDriveAction
    
    @pytest.mark.asyncio
    async def test_execute_with_context_files(self, mock_drive_service, sample_context):
        """Test syncing files from context['output_files']."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='parent_folder_id',
            sync_context_outputs=True
        )
        
        with patch.object(action, '_authenticate', return_value=mock_drive_service):
            with patch.object(action, '_file_exists', return_value=True):
                result = await action.execute_typed(params, sample_context)
        
        assert result.success
        assert result.data['uploaded_count'] == 3  # All context files
        assert 'folder_id' in result.data
    
    @pytest.mark.asyncio
    async def test_execute_with_custom_files(self, mock_drive_service, temp_files):
        """Test syncing specific input files."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            sync_context_outputs=False,
            input_files=[temp_files['results.csv'], temp_files['report.md']]
        )
        
        with patch.object(action, '_authenticate', return_value=mock_drive_service):
            result = await action.execute_typed(params, {})
        
        assert result.success
        assert result.data['uploaded_count'] == 2
    
    # === FOLDER MANAGEMENT TESTS ===
    
    @pytest.mark.asyncio
    async def test_creates_timestamped_subfolder(self, mock_drive_service):
        """Test automatic timestamped subfolder creation."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='parent_id',
            create_subfolder=True
        )
        
        with patch.object(action, '_authenticate', return_value=mock_drive_service):
            with patch('biomapper.core.strategy_actions.io.sync_to_google_drive.datetime') as mock_dt:
                mock_dt.now.return_value.strftime.return_value = '2024_01_15_143022'
                
                folder_id = await action._create_target_folder(mock_drive_service, params)
        
        # Verify folder creation call
        create_call = mock_drive_service.files().create
        create_call.assert_called_once()
        
        # Check folder metadata
        call_kwargs = create_call.call_args[1]
        assert call_kwargs['body']['mimeType'] == 'application/vnd.google-apps.folder'
        assert '2024_01_15_143022' in call_kwargs['body']['name']
    
    @pytest.mark.asyncio
    async def test_uses_custom_subfolder_name(self, mock_drive_service):
        """Test custom subfolder name overrides timestamp."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='parent_id',
            create_subfolder=True,
            subfolder_name='my_custom_results'
        )
        
        with patch.object(action, '_authenticate', return_value=mock_drive_service):
            folder_id = await action._create_target_folder(mock_drive_service, params)
        
        call_kwargs = mock_drive_service.files().create.call_args[1]
        assert call_kwargs['body']['name'] == 'my_custom_results'
    
    # === FILE FILTERING TESTS ===
    
    @pytest.mark.asyncio
    async def test_file_pattern_filtering(self, temp_files):
        """Test include/exclude pattern filtering."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            sync_context_outputs=False,
            input_files=list(temp_files.values()),
            file_patterns=['*.csv', '*.json'],
            exclude_patterns=['*large*']
        )
        
        files = await action._collect_files(params, {})
        
        # Should include .csv and .json but not .md or large files
        assert len(files) == 2
        assert any('results.csv' in f for f in files)
        assert any('data.json' in f for f in files)
        assert not any('report.md' in f for f in files)
        assert not any('large' in f for f in files)
    
    # === AUTHENTICATION TESTS ===
    
    @pytest.mark.asyncio
    async def test_service_account_authentication(self):
        """Test authentication with service account."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            credentials_path='/path/to/service_account.json',
            use_user_auth=False
        )
        
        with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_creds.return_value = Mock()
                mock_build.return_value = Mock()
                
                service = await action._authenticate(params)
                
                mock_creds.assert_called_once_with(
                    '/path/to/service_account.json',
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
                assert service is not None
    
    @pytest.mark.asyncio
    async def test_authentication_failure_handling(self):
        """Test graceful handling of authentication failures."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            credentials_path='/invalid/path.json',
            hard_failure=False
        )
        
        with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
            mock_creds.side_effect = FileNotFoundError("Credentials not found")
            
            result = await action.execute_typed(params, {})
            
            assert result.success  # Should not fail pipeline
            assert result.data.get('sync_skipped') is True
            assert 'Credentials not found' in result.data.get('reason', '')
    
    # === UPLOAD BEHAVIOR TESTS ===
    
    @pytest.mark.asyncio
    async def test_chunked_upload_for_large_files(self, mock_drive_service):
        """Test chunked upload is used for files > chunk_size."""
        action = SyncToGoogleDriveAction()
        large_file = '/tmp/large_data.csv'
        
        with patch('os.path.getsize', return_value=50 * 1024 * 1024):  # 50MB
            with patch('googleapiclient.http.MediaFileUpload') as mock_media:
                mock_media.return_value = Mock()
                
                await action._upload_single_file(
                    mock_drive_service,
                    large_file,
                    'folder_id',
                    chunk_size=10 * 1024 * 1024  # 10MB chunks
                )
                
                # Verify resumable upload was used
                mock_media.assert_called_with(
                    large_file,
                    resumable=True,
                    chunksize=10 * 1024 * 1024
                )
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_rename(self, mock_drive_service):
        """Test file conflict resolution with rename strategy."""
        action = SyncToGoogleDriveAction()
        
        # Mock existing file with same name
        mock_drive_service.files().list().execute.return_value = {
            'files': [{'id': 'existing_id', 'name': 'results.csv'}]
        }
        
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            conflict_resolution='rename'
        )
        
        uploaded_name = await action._resolve_conflict(
            mock_drive_service,
            'results.csv',
            'folder_id',
            params
        )
        
        # Should rename to avoid conflict
        assert uploaded_name != 'results.csv'
        assert 'results' in uploaded_name
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, mock_drive_service):
        """Test retry logic with exponential backoff."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            max_retries=3
        )
        
        # Fail twice, then succeed
        mock_drive_service.files().create().execute.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            {'id': 'success_id', 'name': 'file.csv'}
        ]
        
        with patch('asyncio.sleep') as mock_sleep:  # Don't actually sleep in tests
            result = await action._upload_with_retry(
                mock_drive_service,
                '/tmp/file.csv',
                'folder_id',
                params
            )
        
        assert result['id'] == 'success_id'
        assert mock_drive_service.files().create().execute.call_count == 3
        
        # Verify exponential backoff
        sleep_calls = mock_sleep.call_args_list
        assert len(sleep_calls) == 2
        assert sleep_calls[0][0][0] < sleep_calls[1][0][0]  # Increasing delay
    
    # === ERROR HANDLING TESTS ===
    
    @pytest.mark.asyncio
    async def test_hard_failure_mode(self, mock_drive_service):
        """Test hard failure stops pipeline on error."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            hard_failure=True
        )
        
        with patch.object(action, '_authenticate', side_effect=Exception("Critical error")):
            result = await action.execute_typed(params, {})
        
        assert not result.success
        assert 'Critical error' in result.error
    
    @pytest.mark.asyncio
    async def test_soft_failure_mode(self, mock_drive_service):
        """Test soft failure continues pipeline on error."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            hard_failure=False
        )
        
        with patch.object(action, '_authenticate', side_effect=Exception("Non-critical error")):
            result = await action.execute_typed(params, {})
        
        assert result.success  # Pipeline continues
        assert result.data.get('sync_skipped') is True
    
    @pytest.mark.asyncio
    async def test_quota_exceeded_handling(self, mock_drive_service):
        """Test handling of Google Drive API quota errors."""
        from googleapiclient.errors import HttpError
        
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(drive_folder_id='folder_id')
        
        # Mock quota exceeded error
        error_resp = Mock()
        error_resp.status = 429
        error_resp.reason = "User Rate Limit Exceeded"
        
        mock_drive_service.files().create().execute.side_effect = HttpError(
            error_resp, b'{"error": {"message": "Quota exceeded"}}'
        )
        
        with patch.object(action, '_authenticate', return_value=mock_drive_service):
            result = await action.execute_typed(params, {'output_files': {}})
        
        # Should handle gracefully
        assert result.data.get('quota_exceeded') is True
    
    # === SECURITY TESTS ===
    
    @pytest.mark.asyncio
    async def test_credentials_never_logged(self, caplog):
        """Test that sensitive credentials are never logged."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            credentials_path='/path/to/secret_key.json'
        )
        
        # Set logging to DEBUG to catch all logs
        caplog.set_level(logging.DEBUG)
        
        with patch.object(action, '_authenticate', side_effect=Exception("Auth error")):
            try:
                await action.execute_typed(params, {})
            except:
                pass
        
        # Check no sensitive data in logs
        for record in caplog.records:
            assert 'private_key' not in record.message.lower()
            assert 'secret_key' not in record.message.lower()
            assert 'password' not in record.message.lower()
            # Path is OK, but not the contents
            assert '"type": "service_account"' not in record.message
    
    @pytest.mark.asyncio
    async def test_minimal_permissions_scope(self):
        """Test that only minimal permissions are requested."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            credentials_path='/path/to/creds.json'
        )
        
        with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds:
            with patch('googleapiclient.discovery.build'):
                await action._authenticate(params)
                
                # Verify only drive.file scope (not full drive access)
                call_args = mock_creds.call_args
                assert 'https://www.googleapis.com/auth/drive.file' in call_args[1]['scopes']
                assert 'https://www.googleapis.com/auth/drive' not in call_args[1]['scopes']
    
    # === PROGRESS TRACKING TESTS ===
    
    @pytest.mark.asyncio
    async def test_verbose_progress_logging(self, mock_drive_service, temp_files, caplog):
        """Test verbose mode provides progress updates."""
        action = SyncToGoogleDriveAction()
        params = SyncToGoogleDriveParams(
            drive_folder_id='folder_id',
            verbose=True,
            input_files=[temp_files['results.csv']]
        )
        
        caplog.set_level(logging.INFO)
        
        with patch.object(action, '_authenticate', return_value=mock_drive_service):
            await action.execute_typed(params, {})
        
        # Should have progress messages
        assert any('Uploading' in record.message for record in caplog.records)
        assert any('results.csv' in record.message for record in caplog.records)
    
    # === INTEGRATION TESTS ===
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, mock_drive_service, sample_context, temp_files):
        """Test complete workflow from context to Drive."""
        action = SyncToGoogleDriveAction()
        
        # Update context with real temp files
        sample_context['output_files'] = {
            'results': temp_files['results.csv'],
            'report': temp_files['report.md']
        }
        
        params = SyncToGoogleDriveParams(
            drive_folder_id='parent_folder',
            create_subfolder=True,
            description='Test upload batch',
            verbose=True
        )
        
        with patch.object(action, '_authenticate', return_value=mock_drive_service):
            result = await action.execute_typed(params, sample_context)
        
        assert result.success
        assert result.data['uploaded_count'] == 2
        assert 'folder_id' in result.data
        assert 'uploaded_files' in result.data
        
        # Verify context was updated
        assert 'sync_results' in sample_context
        assert sample_context['sync_results']['parent_folder']['uploaded_files']
```

## Phase 2: Minimal Implementation to Pass Tests

Only after ALL tests are written and failing, implement the minimal code:

```python
# biomapper/core/strategy_actions/io/sync_to_google_drive.py

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.models.action_results import ActionResult

class SyncToGoogleDriveParams(BaseModel):
    """Minimal params to make tests pass."""
    drive_folder_id: str
    sync_context_outputs: bool = True
    # Add other fields as tests require them

@register_action("SYNC_TO_GOOGLE_DRIVE")
class SyncToGoogleDriveAction(TypedStrategyAction[SyncToGoogleDriveParams, ActionResult]):
    """Minimal implementation to pass tests."""
    
    def get_params_model(self) -> type[SyncToGoogleDriveParams]:
        return SyncToGoogleDriveParams
    
    async def execute_typed(self, params: SyncToGoogleDriveParams, context: Dict[str, Any]) -> ActionResult:
        # Minimal implementation to make tests pass
        return ActionResult(success=True, data={'uploaded_count': 0})
```

## Phase 3: Refactor and Improve

Once tests pass, refactor for:
- Better code structure
- Performance optimization
- Error handling improvements
- Code reusability

## Phase 4: Add More Features (RED-GREEN-REFACTOR Cycle)

For each new feature:
1. Write failing test
2. Implement minimal code
3. Refactor
4. Repeat

## Key TDD Principles to Follow

### 1. Test First, Code Second
- NEVER write implementation before tests
- Tests define the specification

### 2. Minimal Implementation
- Write just enough code to pass tests
- Don't add unrequested features

### 3. Refactor With Confidence
- Tests provide safety net
- Refactor fearlessly with green tests

### 4. Tests as Documentation
- Tests show how to use the code
- Tests explain the requirements

### 5. Fast Feedback Loop
- Run tests frequently
- Fix failures immediately

## Testing Best Practices

### 1. Test Isolation
```python
@pytest.fixture(autouse=True)
def reset_registry():
    """Reset action registry between tests."""
    from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
    original = ACTION_REGISTRY.copy()
    yield
    ACTION_REGISTRY.clear()
    ACTION_REGISTRY.update(original)
```

### 2. Mock External Services
```python
@pytest.fixture
def mock_google_services():
    """Mock all Google services."""
    with patch('googleapiclient.discovery.build') as mock_build:
        with patch('google.oauth2.service_account.Credentials') as mock_creds:
            yield mock_build, mock_creds
```

### 3. Test Data Builders
```python
class TestDataBuilder:
    @staticmethod
    def context_with_files(file_count=3):
        """Build context with specified number of files."""
        return {
            'output_files': {
                f'file_{i}': f'/tmp/file_{i}.csv'
                for i in range(file_count)
            }
        }
```

### 4. Parameterized Tests
```python
@pytest.mark.parametrize("conflict_resolution,expected_behavior", [
    ("rename", "adds_timestamp"),
    ("overwrite", "replaces_existing"),
    ("skip", "keeps_original")
])
async def test_conflict_resolution_strategies(conflict_resolution, expected_behavior):
    # Test each strategy
    pass
```

## Running Tests During Development

```bash
# Run tests continuously during development
poetry run pytest tests/unit/core/strategy_actions/io/test_sync_to_google_drive.py -xvs --watch

# Run with coverage
poetry run pytest tests/unit/core/strategy_actions/io/test_sync_to_google_drive.py --cov=biomapper.core.strategy_actions.io --cov-report=term-missing

# Run specific test
poetry run pytest -k "test_authentication" -xvs
```

## Success Criteria for TDD Implementation

1. ✅ All tests written BEFORE implementation
2. ✅ Tests initially fail (RED)
3. ✅ Minimal code makes tests pass (GREEN)
4. ✅ Code refactored with passing tests (REFACTOR)
5. ✅ >90% code coverage
6. ✅ Tests serve as documentation
7. ✅ Each feature has corresponding tests
8. ✅ Security tests included
9. ✅ Performance tests included
10. ✅ Error handling tests included

## Common TDD Mistakes to Avoid

1. ❌ Writing implementation first
2. ❌ Writing tests after code
3. ❌ Testing implementation details instead of behavior
4. ❌ Not running tests frequently
5. ❌ Skipping the refactor step
6. ❌ Writing too much code to pass tests
7. ❌ Not testing edge cases
8. ❌ Ignoring failing tests
9. ❌ Testing multiple behaviors in one test
10. ❌ Not using mocks for external dependencies