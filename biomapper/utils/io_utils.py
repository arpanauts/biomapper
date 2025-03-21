"""Utilities for file input/output operations."""

import os
import sys
import pandas as pd
import psutil


def get_max_file_size():
    """
    Dynamically calculate maximum file size based on available system memory.
    
    Returns:
        int: Maximum file size in bytes (50% of available system memory or 1GB fallback)
    """
    try:
        # Use 50% of available memory as maximum file size
        available_memory = psutil.virtual_memory().available
        max_size = int(available_memory / 2)
        return max_size
    except Exception:
        # Fallback to 1GB if system memory information can't be determined
        return 1_000_000_000  # 1GB


def load_tabular_file(
    file_path, 
    sep=None, 
    comment='#', 
    low_memory=False, 
    nrows=None, 
    **kwargs
):
    """
    Load data from a CSV/TSV file with intelligent handling of comments and separators.
    
    This function is a centralized way to load tabular data files with consistent
    handling of comments and other parameters. It automatically detects the separator
    if not specified, and supports skipping comment lines.
    
    Args:
        file_path (str): Path to the file to load
        sep (str, optional): Separator used in the file. If None, it will be detected 
                             based on file extension (.tsv = tab, .csv = comma)
        comment (str, optional): Character that indicates comment lines to skip. Default '#'
        low_memory (bool, optional): Allows pandas to use less memory at the cost of performance. Default False
        nrows (int, optional): Number of rows to read. If None, reads all rows
        **kwargs: Additional arguments to pass to pd.read_csv
        
    Returns:
        pd.DataFrame: The loaded data as a pandas DataFrame
        
    Raises:
        FileNotFoundError: If the specified file does not exist
        ValueError: If the file size exceeds the system's available memory limit
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Check file size against available memory
    file_size = os.path.getsize(file_path)
    max_size = get_max_file_size()
    
    if file_size > max_size and nrows is None:
        mb_size = file_size / 1_000_000
        mb_max = max_size / 1_000_000
        raise ValueError(
            f"File size ({mb_size:.2f} MB) exceeds the recommended limit "
            f"of {mb_max:.2f} MB (50% of available memory). "
            f"Please use 'nrows' parameter to load a subset of the data."
        )
    
    # Auto-detect separator if not specified
    if sep is None:
        # Convert Path objects to string first
        file_path_str = str(file_path)
        if file_path_str.lower().endswith('.tsv'):
            sep = '\t'
        elif file_path_str.lower().endswith('.csv'):
            sep = ','
        else:
            # Default to comma for unknown extensions
            sep = ','
    
    # Load the data with comments handled
    return pd.read_csv(
        file_path, 
        sep=sep, 
        comment=comment, 
        low_memory=low_memory,
        nrows=nrows,
        **kwargs
    )
