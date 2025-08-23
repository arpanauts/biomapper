"""
Enhanced Google Drive Sync Action with automatic folder organization
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.standards.context_handler import UniversalContext
import os
import logging
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

logger = logging.getLogger(__name__)


class SyncActionResult(BaseModel):
    """Result of Google Drive sync action."""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class SyncToGoogleDriveV2Params(BaseModel):
    """Enhanced parameters for Google Drive sync with auto-organization."""
    
    drive_folder_id: str = Field(
        description="Google Drive folder ID where files will be uploaded"
    )
    
    # Auto-organization settings
    auto_organize: bool = Field(
        default=True,
        description="Automatically organize by strategy/version folders"
    )
    strategy_name: Optional[str] = Field(
        default=None,
        description="Strategy name for folder organization (auto-detected if not provided)"
    )
    strategy_version: Optional[str] = Field(
        default=None,
        description="Strategy version for subfolder (auto-detected if not provided)"
    )
    
    # Original parameters
    sync_context_outputs: bool = Field(
        default=True, description="Whether to sync files from context['output_files']"
    )
    create_subfolder: bool = Field(
        default=False,  # Changed default since auto_organize handles this
        description="Create a timestamped subfolder (in addition to auto-organization)"
    )
    subfolder_name: Optional[str] = Field(
        default=None, description="Custom subfolder name"
    )
    credentials_path: Optional[str] = Field(
        default=None, description="Path to Google service account credentials JSON"
    )
    file_patterns: Optional[List[str]] = Field(
        default=None, description="Include only files matching these patterns"
    )
    exclude_patterns: Optional[List[str]] = Field(
        default=None, description="Exclude files matching these patterns"
    )
    description: Optional[str] = Field(
        default=None, description="Description for the upload batch"
    )
    
    # Additional parameters from YAML
    local_directory: Optional[str] = Field(
        default=None, description="Local directory to sync files from"
    )
    include_patterns: Optional[List[str]] = Field(
        default=None, description="Patterns for files to include (alias for file_patterns)"
    )
    timestamp: Optional[str] = Field(
        default=None, description="Timestamp for organizing uploads"
    )
    create_summary: bool = Field(
        default=False, description="Create a summary file of uploaded items"
    )
    
    # Duplicate handling parameters
    check_duplicates: bool = Field(
        default=True,
        description="Check for existing files before uploading to prevent duplicates"
    )
    update_existing: bool = Field(
        default=False,
        description="Update existing files instead of skipping when duplicates found"
    )


@register_action("SYNC_TO_GOOGLE_DRIVE_V2")
class SyncToGoogleDriveV2Action(TypedStrategyAction[SyncToGoogleDriveV2Params, SyncActionResult]):
    """Enhanced Google Drive sync with automatic folder organization."""
    
    def get_params_model(self) -> type[SyncToGoogleDriveV2Params]:
        return SyncToGoogleDriveV2Params
    
    def get_result_model(self) -> type[SyncActionResult]:
        return SyncActionResult
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: SyncToGoogleDriveV2Params,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any]
    ) -> SyncActionResult:
        """Execute the sync with auto-organization."""
        try:
            # Wrap context for uniform access
            ctx = UniversalContext.wrap(context)
            
            # Get strategy info from context if not provided
            if params.auto_organize:
                if not params.strategy_name:
                    # Try to get from context (set by the strategy runner)
                    params.strategy_name = ctx.get('strategy_name', 'unknown_strategy')
                
                if not params.strategy_version:
                    # Try to get from context metadata
                    metadata = ctx.get('strategy_metadata', {})
                    if isinstance(metadata, dict):
                        params.strategy_version = metadata.get('version', '1.0.0')
                    else:
                        params.strategy_version = '1.0.0'
            
            # Authenticate
            service = await self._authenticate(params)
            if not service:
                return SyncActionResult(
                    success=True,
                    data={"sync_skipped": True, "reason": "Authentication failed"}
                )
            
            # Create folder hierarchy
            target_folder_id = await self._create_organized_folders(
                service, params
            )
            
            # Collect files to upload
            files_to_upload = await self._collect_files(params, context)
            
            # Upload files
            uploaded_files = []
            errors = []
            
            for file_path in files_to_upload:
                try:
                    file_result = await self._upload_file(
                        service, file_path, target_folder_id, params
                    )
                    uploaded_files.append(file_result)
                except Exception as e:
                    errors.append({"file": file_path, "error": str(e)})
            
            return SyncActionResult(
                success=True,
                data={
                    "uploaded_count": len(uploaded_files),
                    "folder_structure": self._describe_folder_structure(params),
                    "target_folder_id": target_folder_id,
                    "uploaded_files": uploaded_files,
                    "errors": errors
                }
            )
            
        except Exception as e:
            # Import the Google API error types for better error handling
            try:
                from googleapiclient.errors import HttpError
                is_http_error = isinstance(e, HttpError)
            except ImportError:
                is_http_error = False
            
            error_msg = str(e)
            
            # Handle specific Google Drive API errors
            if is_http_error and hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                status_code = e.resp.status
                if status_code == 404:
                    logger.error(f"Google Drive folder not found: {params.drive_folder_id}")
                    logger.error("Please ensure the folder exists and service account has access")
                elif status_code == 403:
                    logger.error("Google Drive access denied")
                    logger.error("Please ensure the service account has been granted access to this folder")
                else:
                    logger.error(f"Google Drive API error {status_code}: {e}")
            elif "404" in error_msg and "notFound" in error_msg:
                logger.error(f"Google Drive folder not accessible: {params.drive_folder_id}")
                logger.error("Please ensure the service account has been granted access to this folder")
                logger.error("Share the folder with the service account email from the credentials file")
            elif "403" in error_msg and "storageQuotaExceeded" in error_msg:
                logger.error("Service account cannot create files in its own storage")
                logger.error("Please share a folder with the service account email")
            else:
                logger.error(f"Sync failed: {e}")
            
            return SyncActionResult(
                success=False,
                error=f"Google Drive sync failed: {error_msg[:200]}"
            )
    
    async def _create_organized_folders(
        self, service, params: SyncToGoogleDriveV2Params
    ) -> str:
        """Create organized folder structure: strategy_name/version/[timestamp]."""
        
        current_parent_id = params.drive_folder_id
        
        if params.auto_organize:
            # Extract base strategy name (without version suffix)
            strategy_base = self._extract_strategy_base(params.strategy_name)
            
            # Create or find strategy folder
            strategy_folder_id = await self._find_or_create_folder(
                service, strategy_base, current_parent_id
            )
            current_parent_id = strategy_folder_id
            
            # Create or find version folder
            version_folder_name = self._format_version_folder(params.strategy_version)
            version_folder_id = await self._find_or_create_folder(
                service, version_folder_name, current_parent_id
            )
            current_parent_id = version_folder_id
        
        # Optional: Add timestamp subfolder
        if params.create_subfolder:
            if params.subfolder_name:
                folder_name = params.subfolder_name
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name = f"run_{timestamp}"
            
            # CRITICAL FIX: Use find_or_create to prevent duplicate folders
            timestamp_folder_id = await self._find_or_create_folder(
                service, folder_name, current_parent_id
            )
            current_parent_id = timestamp_folder_id
        
        return current_parent_id
    
    def _extract_strategy_base(self, strategy_name: str) -> str:
        """Extract base strategy name without version suffix."""
        # Remove common version patterns: _v1_base, _v2_enhanced, _v2.2_integrated, etc.
        import re
        
        # Pattern matches various version patterns at the end:
        # _v{number}.{number}_{descriptor} (e.g., _v2.2_integrated)
        # _v{number}_{descriptor} (e.g., _v1_base)
        # _v{number} (e.g., _v2)
        patterns = [
            r'_v\d+\.\d+_\w+$',  # _v2.2_integrated
            r'_v\d+_\w+$',       # _v1_base, _v2_enhanced
            r'_v\d+$'            # _v2
        ]
        
        base_name = strategy_name
        for pattern in patterns:
            new_name = re.sub(pattern, '', base_name)
            if new_name != base_name:
                base_name = new_name
                break
        
        return base_name if base_name else strategy_name
    
    def _format_version_folder(self, version: str) -> str:
        """Format version string for folder name."""
        # Convert 1.0.0 to v1_0_0 or similar
        version_clean = version.replace('.', '_')
        return f"v{version_clean}"
    
    async def _find_or_create_folder(
        self, service, folder_name: str, parent_id: str
    ) -> str:
        """Find existing folder or create new one."""
        # First, try to find existing folder
        query = (
            f"'{parent_id}' in parents and "
            f"name = '{folder_name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        
        try:
            results = service.files().list(
                q=query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name)"
            ).execute()
            
            items = results.get('files', [])
            if items:
                logger.info(f"Found existing folder: {folder_name}")
                return items[0]['id']
        except Exception as e:
            logger.warning(f"Error searching for folder: {e}")
            # Don't continue if the parent folder doesn't exist or we can't access it
            # This should raise an exception to be caught in the main execute_typed method
            from googleapiclient.errors import HttpError
            if isinstance(e, HttpError):
                raise e  # Re-raise HttpError to be handled at higher level
        
        # Folder doesn't exist, create it
        return await self._create_folder(service, folder_name, parent_id)
    
    async def _create_folder(
        self, service, folder_name: str, parent_id: str, description: str = None
    ) -> str:
        """Create a new folder."""
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]
        }
        
        if description:
            folder_metadata["description"] = description
        
        folder = service.files().create(
            body=folder_metadata,
            fields="id",
            supportsAllDrives=True
        ).execute()
        
        logger.info(f"Created folder: {folder_name}")
        return folder["id"]
    
    def _describe_folder_structure(self, params: SyncToGoogleDriveV2Params) -> str:
        """Describe the folder structure that was created."""
        if not params.auto_organize:
            return "Direct upload to specified folder"
        
        strategy_base = self._extract_strategy_base(params.strategy_name)
        version_folder = self._format_version_folder(params.strategy_version)
        
        structure = f"{strategy_base}/{version_folder}"
        
        if params.create_subfolder:
            if params.subfolder_name:
                structure += f"/{params.subfolder_name}"
            else:
                structure += "/run_[timestamp]"
        
        return structure
    
    async def _authenticate(self, params: SyncToGoogleDriveV2Params):
        """Authenticate with Google Drive API."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            # Get credentials path
            if params.credentials_path:
                creds_path = params.credentials_path
            else:
                creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            
            if not creds_path:
                logger.error("No credentials path provided and GOOGLE_APPLICATION_CREDENTIALS not set")
                return None
            
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            
            return build("drive", "v3", credentials=credentials)
            
        except ImportError as e:
            logger.error(f"Google API dependencies not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    async def _collect_files(
        self, params: SyncToGoogleDriveV2Params, context: Dict[str, Any]
    ) -> List[str]:
        """Collect files to upload based on parameters."""
        files = []
        
        # Wrap context for uniform access
        ctx = UniversalContext.wrap(context)
        
        # Collect from context outputs
        if params.sync_context_outputs:
            output_files = ctx.get('output_files', {})
            
            # Debug logging to understand format
            logger.info(f"Context output_files type: {type(output_files)}")
            
            # Handle both dict and list formats
            if isinstance(output_files, dict):
                dict_count = 0
                for key, path in output_files.items():
                    if path and os.path.exists(path):
                        files.append(path)
                        dict_count += 1
                logger.info(f"Added {dict_count} files from dict format")
                
            elif isinstance(output_files, list):
                list_count = 0
                for path in output_files:
                    # Ensure path is valid and not already added
                    if path and os.path.exists(path) and path not in files:
                        files.append(path)
                        list_count += 1
                logger.info(f"Added {list_count} files from list format")
            
            logger.info(f"Total files collected from context: {len(files)}")
        
        # Collect from local directory if specified
        if params.local_directory and os.path.exists(params.local_directory):
            import glob
            for pattern in params.include_patterns or ['*']:
                pattern_path = os.path.join(params.local_directory, pattern)
                for file_path in glob.glob(pattern_path, recursive=True):
                    if os.path.isfile(file_path) and file_path not in files:
                        files.append(file_path)
        
        # Apply filters
        if params.file_patterns or params.exclude_patterns:
            files = self._filter_files(files, params.file_patterns, params.exclude_patterns)
        
        return files
    
    def _filter_files(
        self, files: List[str], 
        include_patterns: Optional[List[str]], 
        exclude_patterns: Optional[List[str]]
    ) -> List[str]:
        """Filter files based on patterns."""
        filtered = []
        
        for file_path in files:
            filename = os.path.basename(file_path)
            
            # Check exclude patterns first
            if exclude_patterns:
                if any(fnmatch(filename, pattern) for pattern in exclude_patterns):
                    continue
            
            # Check include patterns
            if include_patterns:
                if any(fnmatch(filename, pattern) for pattern in include_patterns):
                    filtered.append(file_path)
            else:
                filtered.append(file_path)
        
        return filtered
    
    async def _file_exists(
        self, service, folder_id: str, file_name: str
    ) -> Optional[str]:
        """Check if file already exists in folder. Returns file ID if exists."""
        query = (
            f"'{folder_id}' in parents and "
            f"name = '{file_name}' and "
            f"mimeType != 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        
        try:
            results = service.files().list(
                q=query,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name, modifiedTime)"
            ).execute()
            
            items = results.get('files', [])
            if items:
                # File exists, return its ID
                logger.info(f"File already exists: {file_name} (ID: {items[0]['id']})")
                return items[0]['id']
        except Exception as e:
            logger.warning(f"Error checking file existence: {e}")
        
        return None
    
    async def _upload_file(
        self, service, file_path: str, folder_id: str, params: SyncToGoogleDriveV2Params
    ) -> Dict[str, Any]:
        """Upload a single file to Google Drive, checking for duplicates."""
        from googleapiclient.http import MediaFileUpload
        
        file_name = os.path.basename(file_path)
        mime_type = self._guess_mime_type(file_name)
        
        # Check if file already exists (only if duplicate checking is enabled)
        check_duplicates = getattr(params, 'check_duplicates', True)  # Default to True
        update_existing = getattr(params, 'update_existing', False)  # Default to False
        
        if check_duplicates:
            existing_file_id = await self._file_exists(service, folder_id, file_name)
            
            if existing_file_id:
                if update_existing:
                    # Update existing file
                    logger.info(f"Updating existing file: {file_name}")
                    media = MediaFileUpload(
                        file_path,
                        mimetype=mime_type,
                        resumable=True,
                        chunksize=params.chunk_size if hasattr(params, 'chunk_size') else 10*1024*1024
                    )
                    
                    file = service.files().update(
                        fileId=existing_file_id,
                        media_body=media,
                        fields="id,name,webViewLink,modifiedTime",
                        supportsAllDrives=True
                    ).execute()
                    
                    logger.info(f"Updated: {file_name}")
                    return file
                else:
                    # Skip upload if file exists
                    logger.info(f"Skipping duplicate upload: {file_name}")
                    return {
                        "id": existing_file_id,
                        "name": file_name,
                        "skipped": True,
                        "reason": "File already exists"
                    }
        
        # File doesn't exist or duplicate checking disabled, create new
        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }
        
        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=params.chunk_size if hasattr(params, 'chunk_size') else 10*1024*1024
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True
        ).execute()
        
        logger.info(f"Uploaded: {file_name}")
        return file
    
    def _guess_mime_type(self, filename: str) -> str:
        """Guess MIME type from filename."""
        ext = Path(filename).suffix.lower()
        mime_types = {
            '.csv': 'text/csv',
            '.tsv': 'text/tab-separated-values',
            '.json': 'application/json',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.pdf': 'application/pdf',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.zip': 'application/zip'
        }
        return mime_types.get(ext, 'application/octet-stream')