"""
Service for handling CSV file operations.
"""
import os
import logging
from pathlib import Path
import glob
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings
from app.core.session import session_manager, Session

# Set up logger
logger = logging.getLogger(__name__)


class CSVService:
    """Service for CSV file operations."""

    async def save_file(self, file: UploadFile) -> Tuple[Session, Path]:
        """
        Save uploaded file to temporary storage and create a session.
        
        Logs file upload details and provides error messages for debugging.
        
        Args:
            file: The uploaded CSV file
            
        Returns:
            Tuple of (session, file_path)
            
        Raises:
            HTTPException: If file is invalid or too large
        """
        # Validate file
        if not file.filename or not file.filename.lower().endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are supported",
            )
            
        # Check file size (FastAPI stream doesn't expose size directly, so we'll read in chunks)
        file_size = 0
        file_content = b''
        
        chunk_size = 1024 * 1024  # 1MB chunks
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            file_content += chunk
            
            if file_size > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB",
                )
                
        # Create session and save file
        session = session_manager.create_session()
        session_dir = session.session_dir
        file_path = session_dir / file.filename
        
        logger.info(f"Created session {session.session_id} with directory {session_dir}")
        
        try:
            # Write file to disk
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            logger.info(f"Saved file {file.filename} ({file_size} bytes) to {file_path}")
                
            # Update session with file info
            session.file_path = file_path
            session.metadata = {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": file_size,
            }
            logger.info(f"Updated session {session.session_id} with file metadata")
        except Exception as e:
            logger.exception(f"Error saving file for session {session.session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
        
        return session, file_path
        
    async def get_columns(self, session: Session) -> List[str]:
        """
        Get column names from the CSV file associated with the session.
        
        Args:
            session: The user session
            
        Returns:
            List of column names
            
        Raises:
            HTTPException: If file not found or invalid
        """
        logger.info(f"Getting columns for session {session.session_id}")
        
        if not session.file_path:
            logger.error(f"No file path in session {session.session_id}. Session metadata: {session.metadata}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No file path found for session {session.session_id}",
            )
            
        logger.info(f"File path for session {session.session_id}: {session.file_path}")
        
        if not session.file_path.exists():
            logger.error(f"File does not exist: {session.file_path} for session {session.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found on disk: {session.file_path}",
            )
            
        try:
            logger.info(f"Attempting to read CSV file: {session.file_path}")
            df = pd.read_csv(session.file_path, nrows=0)
            columns = df.columns.tolist()
            logger.info(f"Successfully read {len(columns)} columns from {session.file_path}")
            return columns
        except Exception as e:
            logger.exception(f"Error reading CSV file: {session.file_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading CSV file: {str(e)}",
            )
            
    async def get_column_types(self, session: Session) -> Dict[str, str]:
        """
        Get inferred column types from the CSV file.
        
        Args:
            session: The user session
            
        Returns:
            Dict mapping column names to inferred types
            
        Raises:
            HTTPException: If file not found or invalid
        """
        logger.info(f"Getting column types for session {session.session_id}")
        
        if not session.file_path:
            logger.error(f"No file path in session {session.session_id}. Session metadata: {session.metadata}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No file path found for session {session.session_id}",
            )
            
        if not session.file_path.exists():
            logger.error(f"File does not exist: {session.file_path} for session {session.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found on disk: {session.file_path}",
            )
            
        try:
            df = pd.read_csv(session.file_path, nrows=100)
            column_types = {}
            
            for column in df.columns:
                if pd.api.types.is_numeric_dtype(df[column]):
                    column_types[column] = "numeric"
                else:
                    # Simple heuristic to detect ID-like columns
                    unique_ratio = df[column].nunique() / len(df[column].dropna())
                    if unique_ratio > 0.9:
                        column_types[column] = "identifier"
                    else:
                        column_types[column] = "text"
                        
            return column_types
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error analyzing CSV file: {str(e)}",
            )
    
    async def preview_data(self, session: Session, limit: int = 10) -> Dict[str, Any]:
        """
        Get a preview of the CSV data.
        
        Args:
            session: The user session
            limit: Maximum number of rows to return
            
        Returns:
            Dict with columns, rows, and total row count
            
        Raises:
            HTTPException: If file not found or invalid
        """
        logger.info(f"Generating data preview for session {session.session_id}, limit={limit}")
        
        if not session.file_path:
            logger.error(f"No file path in session {session.session_id}. Session metadata: {session.metadata}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No file path found for session {session.session_id}",
            )
            
        if not session.file_path.exists():
            logger.error(f"File does not exist: {session.file_path} for session {session.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found on disk: {session.file_path}",
            )
            
        try:
            # Get total row count (fast method)
            logger.info(f"Counting rows in {session.file_path}")
            total_rows = sum(1 for _ in open(session.file_path)) - 1
            logger.info(f"File has {total_rows} data rows")
            
            # Read preview rows
            logger.info(f"Reading preview data ({limit} rows) for session {session.session_id}")
            df = pd.read_csv(session.file_path, nrows=limit)
            
            # Convert to list of dicts
            rows = df.replace({pd.NA: None}).to_dict(orient="records")
            
            result = {
                "columns": df.columns.tolist(),
                "rows": rows,
                "total_rows": total_rows,
                "preview_rows": len(rows),
            }
            
            logger.info(f"Successfully generated preview for session {session.session_id}: {len(result['columns'])} columns, {len(rows)} preview rows")
            return result
            
        except pd.errors.EmptyDataError:
            logger.warning(f"Empty CSV file detected for session {session.session_id}")
            return {
                "columns": [],
                "rows": [],
                "total_rows": 0,
                "preview_rows": 0,
            }
        except Exception as e:
            logger.exception(f"Error generating preview for session {session.session_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading CSV file: {str(e)}",
            )
    
    async def list_server_files(self, directory_path: str, extensions: List[str] = None) -> List[Dict[str, Any]]:
        """
        List files in the specified server directory with optional extension filtering.
        
        Args:
            directory_path: Path to the directory to search
            extensions: List of file extensions to include (e.g., ['.csv', '.tsv'])
            
        Returns:
            List of file information dictionaries with name, path, size, and last modified date
            
        Raises:
            HTTPException: If directory does not exist or is not accessible
        """
        try:
            logger.info(f"Checking directory: {directory_path}")
            
            # Check if the directory path is empty
            if not directory_path or directory_path.isspace():
                logger.error("Empty directory path provided")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Directory path cannot be empty"
                )
                
            # Check if directory exists and has correct permissions
            if not os.path.exists(directory_path):
                logger.error(f"Directory does not exist: {directory_path}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Directory does not exist: {directory_path}"
                )
                
            if not os.path.isdir(directory_path):
                logger.error(f"Path is not a directory: {directory_path}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Path is not a directory: {directory_path}"
                )
                
            # Check if directory is readable
            if not os.access(directory_path, os.R_OK):
                logger.error(f"Directory is not readable: {directory_path}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Directory is not readable: {directory_path}"
                )
                
            if extensions is None:
                extensions = ['.csv', '.tsv']
                
            # Convert extensions to lowercase for case-insensitive matching
            extensions = [ext.lower() if not ext.startswith('.') else ext.lower() for ext in extensions]
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
            
            logger.info(f"Listing files in {directory_path} with extensions {extensions}")
            file_list = []
            for ext in extensions:
                pattern = os.path.join(directory_path, f'*{ext}')
                logger.debug(f"Searching with pattern: {pattern}")
                files = glob.glob(pattern)
                
                for file_path in files:
                    # Skip directories with matching extensions
                    if os.path.isdir(file_path):
                        continue
                        
                    file_stat = os.stat(file_path)
                    file_list.append({
                        'name': os.path.basename(file_path),
                        'path': file_path,
                        'size': file_stat.st_size,
                        'modified': file_stat.st_mtime,
                        'extension': os.path.splitext(file_path)[1].lower()
                    })
            
            # Sort by name
            file_list.sort(key=lambda x: x['name'])
            logger.info(f"Found {len(file_list)} files in {directory_path}")
            return file_list
        
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error listing server files from {directory_path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list server files: {str(e)}"
            )
    
    async def load_server_file(self, file_path: str) -> Tuple[Session, Path]:
        """
        Load a file from the server filesystem into the session.
        
        Args:
            file_path: Path to the file on the server
            
        Returns:
            Tuple of (session, file_path)
            
        Raises:
            HTTPException: If file does not exist, is not accessible, or is invalid
        """
        try:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File does not exist or is not accessible: {file_path}"
                )
            
            # Check file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in ['.csv', '.tsv']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_ext}. Only .csv and .tsv files are supported."
                )
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB"
                )
            
            # Create session
            session = session_manager.create_session()
            filename = os.path.basename(file_path)
            
            # We'll create a symlink to the actual file in the session directory
            # This avoids copying large files unnecessarily
            session_dir = session.session_dir
            target_path = session_dir / filename
            
            # Create a symbolic link to the original file
            # This way we don't need to copy large files
            os.symlink(file_path, target_path)
            
            logger.info(f"Created session {session.session_id} with symlink to file {file_path}")
            
            # Update session with file info
            session.file_path = target_path
            session.metadata = {
                "filename": filename,
                "content_type": "text/csv" if file_ext == ".csv" else "text/tab-separated-values",
                "file_size": file_size,
                "source_path": file_path,
                "is_server_file": True
            }
            
            return session, target_path
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error loading server file {file_path}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load server file: {str(e)}"
            )
