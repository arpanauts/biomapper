"""
Enhanced Google Drive Sync Action with OAuth2 and Service Account support
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

# Import the new auth helper
from utils.google_auth_helper import GoogleAuthHelper, AuthType

logger = logging.getLogger(__name__)


class SyncActionResult(BaseModel):
    """Result of Google Drive sync action."""
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class SyncToGoogleDriveV3Params(BaseModel):
    """Parameters for Google Drive sync with OAuth2 support."""
    
    drive_folder_id: str = Field(
        description="Google Drive folder ID where files will be uploaded"
    )
    
    # Authentication settings (NEW)
    auth_type: str = Field(
        default="auto",
        description="Authentication type: 'oauth2', 'service_account', or 'auto'"
    )
    oauth_token_path: Optional[str] = Field(
        default=None,
        description="Path to OAuth2 token file (for OAuth2 auth)"
    )
    oauth_client_secret_path: Optional[str] = Field(
        default=None,
        description="Path to OAuth2 client secret file (for OAuth2 auth)"
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
        default=False,
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
    
    # Additional parameters
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
    chunk_size: int = Field(
        default=10*1024*1024, description="Upload chunk size in bytes"
    )


@register_action("SYNC_TO_GOOGLE_DRIVE_V3")
class SyncToGoogleDriveV3Action(TypedStrategyAction[SyncToGoogleDriveV3Params, SyncActionResult]):
    """Enhanced Google Drive sync with OAuth2 and Service Account support."""
    
    def get_params_model(self) -> type[SyncToGoogleDriveV3Params]:
        return SyncToGoogleDriveV3Params
    
    def get_result_model(self) -> type[SyncActionResult]:
        return SyncActionResult
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: SyncToGoogleDriveV3Params,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any]
    ) -> SyncActionResult:
        """Execute the sync with OAuth2 or Service Account authentication."""
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
            
            # Authenticate using the new auth helper
            service = await self._authenticate_with_helper(params)
            if not service:
                return SyncActionResult(
                    success=True,
                    data={
                        "sync_skipped": True, 
                        "reason": "Authentication failed - check credentials configuration"
                    }
                )
            
            # Test folder access before proceeding
            auth_method = self._get_auth_method_used()
            logger.info(f"Authenticated with Google Drive using {auth_method}")
            
            # Create folder hierarchy
            target_folder_id = await self._create_organized_folders(
                service, params
            )
            
            # Collect files to upload
            files_to_upload = await self._collect_files(params, context)
            
            if not files_to_upload:
                logger.info("No files to upload")
                return SyncActionResult(
                    success=True,
                    data={
                        "uploaded_count": 0,
                        "message": "No files found to upload"
                    }
                )
            
            # Upload files
            uploaded_files = []
            errors = []
            
            for file_path in files_to_upload:
                try:
                    file_result = await self._upload_file(
                        service, file_path, target_folder_id, params
                    )
                    uploaded_files.append(file_result)
                    logger.info(f"Uploaded: {os.path.basename(file_path)}")
                except Exception as e:
                    error_msg = str(e)
                    if "storageQuotaExceeded" in error_msg:
                        error_msg = "Service account storage quota exceeded - ensure folder is shared"
                    errors.append({"file": file_path, "error": error_msg})
                    logger.error(f"Failed to upload {file_path}: {error_msg}")
            
            # Create summary if requested
            if params.create_summary and uploaded_files:
                summary_result = await self._create_summary_file(
                    service, target_folder_id, uploaded_files, params
                )
                if summary_result:
                    uploaded_files.append(summary_result)
            
            return SyncActionResult(
                success=True,
                data={
                    "uploaded_count": len(uploaded_files),
                    "folder_structure": self._describe_folder_structure(params),
                    "target_folder_id": target_folder_id,
                    "auth_method": auth_method,
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
                    logger.error("Please ensure the folder exists and you have access")
                elif status_code == 403:
                    logger.error("Google Drive access denied")
                    logger.error("Please ensure you have been granted access to this folder")
                else:
                    logger.error(f"Google Drive API error {status_code}: {e}")
            elif "404" in error_msg and "notFound" in error_msg:
                logger.error(f"Google Drive folder not accessible: {params.drive_folder_id}")
                logger.error("Please ensure you have been granted access to this folder")
                if self._auth_helper and self._auth_helper._get_auth_method() == "service_account":
                    logger.error("For service accounts: Share the folder with the service account email")
            elif "403" in error_msg and "storageQuotaExceeded" in error_msg:
                logger.error("Service account cannot create files in its own storage")
                logger.error("Please share a folder with the service account email")
                logger.error("Or use OAuth2 authentication to upload to your personal Drive")
            else:
                logger.error(f"Sync failed: {e}")
            
            return SyncActionResult(
                success=False,
                error=f"Google Drive sync failed: {error_msg[:200]}"
            )
    
    async def _authenticate_with_helper(self, params: SyncToGoogleDriveV3Params):
        """Authenticate using the GoogleAuthHelper for flexible auth support."""
        try:
            # Create auth helper with specified parameters
            self._auth_helper = GoogleAuthHelper(
                auth_type=params.auth_type,
                service_account_path=params.credentials_path,
                oauth2_token_path=params.oauth_token_path,
                oauth2_client_secret_path=params.oauth_client_secret_path
            )
            
            # Authenticate and get service
            service = self._auth_helper.get_drive_service()
            
            if service:
                # Test access to the folder
                test_results = self._auth_helper.test_access(folder_id=params.drive_folder_id)
                
                if not test_results['authenticated']:
                    logger.error("Authentication failed")
                    return None
                
                if params.drive_folder_id and not test_results['can_access_folder']:
                    logger.warning(f"Cannot access folder {params.drive_folder_id}")
                    if test_results['errors']:
                        for error in test_results['errors']:
                            logger.error(f"  - {error}")
                    
                    # For OAuth2, we can still try to upload to the user's Drive
                    if test_results['auth_method'] == 'oauth2':
                        logger.info("OAuth2 authenticated - will create folder if needed")
                    else:
                        logger.error("Service account needs folder to be shared with Editor permission")
                        return None
                
                logger.info(f"Authenticated as: {test_results['email']}")
                return service
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication setup failed: {e}")
            return None
    
    def _get_auth_method_used(self) -> str:
        """Get the authentication method that was used."""
        if hasattr(self, '_auth_helper') and self._auth_helper:
            return self._auth_helper._get_auth_method()
        return "unknown"
    
    async def _create_organized_folders(
        self, service, params: SyncToGoogleDriveV3Params
    ) -> str:
        """Create organized folder structure: strategy_name/version/[timestamp]."""
        
        current_parent_id = params.drive_folder_id
        
        # For OAuth2 with no folder specified, use root
        if not current_parent_id and self._get_auth_method_used() == "oauth2":
            current_parent_id = 'root'
            logger.info("Using root folder for OAuth2 upload")
        
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
            
            timestamp_folder_id = await self._find_or_create_folder(
                service, folder_name, current_parent_id
            )
            current_parent_id = timestamp_folder_id
        
        return current_parent_id
    
    def _extract_strategy_base(self, strategy_name: str) -> str:
        """Extract base strategy name without version suffix."""
        import re
        
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
        version_clean = version.replace('.', '_')
        return f"v{version_clean}"
    
    async def _find_or_create_folder(
        self, service, folder_name: str, parent_id: str
    ) -> str:
        """Find existing folder or create new one."""
        # Handle root folder for OAuth2
        if parent_id == 'root':
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        else:
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
            # For OAuth2, we can create the folder even if search fails
            if self._get_auth_method_used() != "oauth2":
                from googleapiclient.errors import HttpError
                if isinstance(e, HttpError):
                    raise e
        
        # Folder doesn't exist, create it
        return await self._create_folder(service, folder_name, parent_id)
    
    async def _create_folder(
        self, service, folder_name: str, parent_id: str, description: str = None
    ) -> str:
        """Create a new folder."""
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        
        # Only add parents if not root
        if parent_id != 'root':
            folder_metadata["parents"] = [parent_id]
        
        if description:
            folder_metadata["description"] = description
        
        folder = service.files().create(
            body=folder_metadata,
            fields="id",
            supportsAllDrives=True
        ).execute()
        
        logger.info(f"Created folder: {folder_name}")
        return folder["id"]
    
    def _describe_folder_structure(self, params: SyncToGoogleDriveV3Params) -> str:
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
    
    async def _collect_files(
        self, params: SyncToGoogleDriveV3Params, context: Dict[str, Any]
    ) -> List[str]:
        """Collect files to upload based on parameters."""
        files = []
        
        # Wrap context for uniform access
        ctx = UniversalContext.wrap(context)
        
        # Collect from context outputs
        if params.sync_context_outputs:
            output_files = ctx.get('output_files', {})
            if isinstance(output_files, dict):
                for key, path in output_files.items():
                    if path and os.path.exists(path):
                        files.append(path)
        
        # Collect from local directory if specified
        if params.local_directory and os.path.exists(params.local_directory):
            import glob
            patterns = params.include_patterns or params.file_patterns or ['*']
            for pattern in patterns:
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
    
    async def _upload_file(
        self, service, file_path: str, folder_id: str, params: SyncToGoogleDriveV3Params
    ) -> Dict[str, Any]:
        """Upload a single file to Google Drive."""
        from googleapiclient.http import MediaFileUpload
        
        file_name = os.path.basename(file_path)
        mime_type = self._guess_mime_type(file_name)
        
        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }
        
        # Add description if provided
        if params.description:
            file_metadata["description"] = params.description
        
        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=params.chunk_size
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name,webViewLink,webContentLink",
            supportsAllDrives=True
        ).execute()
        
        result = {
            "id": file.get("id"),
            "name": file.get("name"),
            "webViewLink": file.get("webViewLink"),
            "size": os.path.getsize(file_path)
        }
        
        # For OAuth2, try to make file publicly accessible
        if self._get_auth_method_used() == "oauth2" and file.get("webContentLink"):
            result["webContentLink"] = file.get("webContentLink")
        
        return result
    
    async def _create_summary_file(
        self, service, folder_id: str, uploaded_files: List[Dict], params: SyncToGoogleDriveV3Params
    ) -> Optional[Dict[str, Any]]:
        """Create a summary file of all uploaded items."""
        try:
            from googleapiclient.http import MediaInMemoryUpload
            import json
            
            summary = {
                "upload_timestamp": datetime.now().isoformat(),
                "strategy_name": params.strategy_name,
                "strategy_version": params.strategy_version,
                "auth_method": self._get_auth_method_used(),
                "total_files": len(uploaded_files),
                "files": uploaded_files
            }
            
            summary_content = json.dumps(summary, indent=2)
            
            file_metadata = {
                "name": f"upload_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "parents": [folder_id],
                "description": "Upload summary generated by biomapper"
            }
            
            media = MediaInMemoryUpload(
                summary_content.encode(),
                mimetype='application/json'
            )
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id,name,webViewLink",
                supportsAllDrives=True
            ).execute()
            
            logger.info("Created upload summary file")
            return file
            
        except Exception as e:
            logger.warning(f"Could not create summary file: {e}")
            return None
    
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