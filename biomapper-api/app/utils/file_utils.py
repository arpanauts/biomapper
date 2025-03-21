"""
Utilities for file operations.
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile

from app.core.config import settings


async def save_upload_file(upload_file: UploadFile, destination: Path) -> Path:
    """
    Save an uploaded file to the specified destination.
    
    Args:
        upload_file: The uploaded file
        destination: Destination path
        
    Returns:
        Path to the saved file
    """
    # Ensure parent directory exists
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the file
    with open(destination, "wb") as buffer:
        # Read in chunks to handle large files
        chunk_size = 1024 * 1024  # 1MB chunks
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            buffer.write(chunk)
    
    return destination


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def delete_file(file_path: Path) -> bool:
    """
    Delete a file if it exists.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file was deleted, False otherwise
    """
    if file_path.exists():
        os.remove(file_path)
        return True
    return False


def clean_directory(directory: Path, exclude: Optional[List[str]] = None) -> int:
    """
    Clean a directory by removing all files except those in the exclude list.
    
    Args:
        directory: Directory to clean
        exclude: List of filenames to exclude
        
    Returns:
        Number of files deleted
    """
    if not directory.exists() or not directory.is_dir():
        return 0
    
    exclude = exclude or []
    count = 0
    
    for item in directory.iterdir():
        if item.is_file() and item.name not in exclude:
            item.unlink()
            count += 1
    
    return count
