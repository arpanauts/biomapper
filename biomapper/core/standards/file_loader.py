"""Robust file loader for biological data formats."""

import logging
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator, Union
import csv

# Optional dependency for encoding detection
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False
    logging.warning("chardet not installed. Encoding detection will use fallback method.")

logger = logging.getLogger(__name__)


class BiologicalFileLoader:
    """Standardized loader for biological data files with robust defaults."""
    
    # Standard NA values in biological data
    NA_VALUES = [
        '', 'NA', 'na', 'N/A', 'n/a', 'nan', 'NaN',
        'null', 'NULL', 'None', 'none', '.', '-', '--',
        'undefined', 'UNDEFINED', 'missing', 'Missing',
        'Not Available', 'not available', 'N.A.', 'n.a.',
        'nil', 'NIL', 'Nil'
    ]
    
    # Common comment characters in biological files
    COMMENT_CHARS = ['#', '!', '//', '/*', '--']
    
    @classmethod
    def detect_encoding(cls, filepath: str, sample_size: int = 10000) -> str:
        """
        Detect file encoding automatically.
        
        Args:
            filepath: Path to file
            sample_size: Bytes to sample for detection
            
        Returns:
            Detected encoding string
        """
        if HAS_CHARDET:
            try:
                with open(filepath, 'rb') as f:
                    raw_data = f.read(sample_size)
                    result = chardet.detect(raw_data)
                    encoding = result.get('encoding', 'utf-8')
                    confidence = result.get('confidence', 0)
                    
                    if confidence < 0.7:
                        logger.warning(
                            f"Low confidence ({confidence:.2f}) in encoding detection for {filepath}. "
                            f"Using {encoding} but consider manual verification."
                        )
                    
                    return encoding if encoding else 'utf-8'
            except Exception as e:
                logger.warning(f"Failed to detect encoding for {filepath}: {e}. Using utf-8.")
                return 'utf-8'
        else:
            # Fallback: try common encodings
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings_to_try:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        f.read(sample_size)
                    return encoding
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            logger.warning(f"Could not detect encoding for {filepath}. Using utf-8 with error handling.")
            return 'utf-8'
    
    @classmethod
    def detect_delimiter(cls, filepath: str, encoding: Optional[str] = None) -> str:
        """
        Auto-detect delimiter from file.
        
        Args:
            filepath: Path to file
            encoding: File encoding (auto-detected if not provided)
            
        Returns:
            Detected delimiter
        """
        if encoding is None:
            encoding = cls.detect_encoding(filepath)
        
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                # Skip comment lines
                sample_lines = []
                for line in f:
                    if not any(line.strip().startswith(c) for c in cls.COMMENT_CHARS):
                        sample_lines.append(line)
                        if len(sample_lines) >= 5:
                            break
                
                # Use CSV sniffer
                sample = '\n'.join(sample_lines)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters='\t,;|')
                return dialect.delimiter
        except Exception as e:
            logger.warning(f"Failed to detect delimiter for {filepath}: {e}. Using tab.")
            return '\t'
    
    @classmethod
    def detect_comment_char(cls, filepath: str, encoding: Optional[str] = None) -> Optional[str]:
        """
        Detect comment character from file.
        
        Args:
            filepath: Path to file
            encoding: File encoding
            
        Returns:
            Detected comment character or None
        """
        if encoding is None:
            encoding = cls.detect_encoding(filepath)
        
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                first_line = f.readline().strip()
                
                for char in cls.COMMENT_CHARS:
                    if first_line.startswith(char):
                        return char
                
                return None
        except Exception:
            return None
    
    @classmethod
    def load_tsv(
        cls,
        filepath: str,
        comment: Optional[str] = None,
        identifier_column: Optional[str] = None,
        auto_detect: bool = True,
        validate: bool = True,
        **kwargs
    ) -> pd.DataFrame:
        """
        Load TSV with biological data defaults.
        
        Args:
            filepath: Path to TSV file
            comment: Comment line prefix (auto-detected if None)
            identifier_column: Column to use as index
            auto_detect: Whether to auto-detect file parameters
            validate: Whether to validate loaded data
            **kwargs: Additional pandas read_csv arguments
            
        Returns:
            Loaded DataFrame
        """
        filepath = str(Path(filepath).resolve())
        
        # Auto-detect parameters if requested
        if auto_detect:
            encoding = cls.detect_encoding(filepath)
            if comment is None:
                comment = cls.detect_comment_char(filepath, encoding)
        else:
            encoding = kwargs.pop('encoding', 'utf-8')
        
        # Set robust defaults
        defaults = {
            'sep': '\t',
            'na_values': cls.NA_VALUES,
            'low_memory': False,  # Prevent mixed type inference
            'encoding': encoding,
            'encoding_errors': 'replace',  # Handle bad characters
            'skip_blank_lines': True,
            'on_bad_lines': 'warn',  # Don't fail on malformed lines
        }
        
        # Add comment parameter if detected or provided
        if comment:
            defaults['comment'] = comment
        
        # Update with user-provided kwargs
        defaults.update(kwargs)
        
        try:
            logger.info(f"Loading TSV file: {filepath}")
            df = pd.read_csv(filepath, **defaults)
            
            # Set identifier column as index if specified
            if identifier_column and identifier_column in df.columns:
                df = df.set_index(identifier_column)
                logger.info(f"Set '{identifier_column}' as index")
            
            # Basic validation
            if validate:
                cls._validate_dataframe(df, filepath)
            
            logger.info(f"Successfully loaded {len(df)} rows from {filepath}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load TSV file {filepath}: {e}")
            raise
    
    @classmethod
    def load_csv(
        cls,
        filepath: str,
        comment: Optional[str] = None,
        identifier_column: Optional[str] = None,
        auto_detect: bool = True,
        validate: bool = True,
        **kwargs
    ) -> pd.DataFrame:
        """
        Load CSV with biological data defaults.
        
        Args:
            filepath: Path to CSV file
            comment: Comment line prefix
            identifier_column: Column to use as index
            auto_detect: Whether to auto-detect file parameters
            validate: Whether to validate loaded data
            **kwargs: Additional pandas arguments
            
        Returns:
            Loaded DataFrame
        """
        filepath = str(Path(filepath).resolve())
        
        # Auto-detect parameters if requested
        if auto_detect:
            encoding = cls.detect_encoding(filepath)
            delimiter = cls.detect_delimiter(filepath, encoding)
            if comment is None:
                comment = cls.detect_comment_char(filepath, encoding)
        else:
            encoding = kwargs.pop('encoding', 'utf-8')
            delimiter = kwargs.pop('sep', ',')
        
        # Set robust defaults
        defaults = {
            'sep': delimiter,
            'na_values': cls.NA_VALUES,
            'low_memory': False,
            'encoding': encoding,
            'encoding_errors': 'replace',
            'skip_blank_lines': True,
            'on_bad_lines': 'warn',
        }
        
        if comment:
            defaults['comment'] = comment
        
        defaults.update(kwargs)
        
        try:
            logger.info(f"Loading CSV file: {filepath}")
            df = pd.read_csv(filepath, **defaults)
            
            if identifier_column and identifier_column in df.columns:
                df = df.set_index(identifier_column)
                logger.info(f"Set '{identifier_column}' as index")
            
            if validate:
                cls._validate_dataframe(df, filepath)
            
            logger.info(f"Successfully loaded {len(df)} rows from {filepath}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load CSV file {filepath}: {e}")
            raise
    
    @classmethod
    def load_chunked(
        cls,
        filepath: str,
        chunk_size: int = 10000,
        file_type: str = 'auto',
        **kwargs
    ) -> Iterator[pd.DataFrame]:
        """
        Load large file in chunks to manage memory.
        
        Args:
            filepath: Path to file
            chunk_size: Number of rows per chunk
            file_type: 'tsv', 'csv', or 'auto'
            **kwargs: Additional arguments for pandas
            
        Yields:
            DataFrame chunks
        """
        filepath = str(Path(filepath).resolve())
        
        # Determine file type
        if file_type == 'auto':
            file_type = 'tsv' if filepath.endswith('.tsv') else 'csv'
        
        # Auto-detect parameters
        encoding = cls.detect_encoding(filepath)
        delimiter = '\t' if file_type == 'tsv' else cls.detect_delimiter(filepath, encoding)
        comment = cls.detect_comment_char(filepath, encoding)
        
        defaults = {
            'sep': delimiter,
            'na_values': cls.NA_VALUES,
            'low_memory': False,
            'encoding': encoding,
            'encoding_errors': 'replace',
            'chunksize': chunk_size,
            'skip_blank_lines': True,
            'on_bad_lines': 'warn',
        }
        
        if comment:
            defaults['comment'] = comment
        
        defaults.update(kwargs)
        
        try:
            logger.info(f"Loading file in chunks: {filepath} (chunk_size={chunk_size})")
            
            with pd.read_csv(filepath, **defaults) as reader:
                for i, chunk in enumerate(reader):
                    logger.debug(f"Processing chunk {i+1} with {len(chunk)} rows")
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Failed to load file in chunks {filepath}: {e}")
            raise
    
    @classmethod
    def auto_load(
        cls,
        filepath: str,
        identifier_column: Optional[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Automatically detect format and load file.
        
        Args:
            filepath: Path to file
            identifier_column: Column to use as index
            **kwargs: Additional arguments
            
        Returns:
            Loaded DataFrame
        """
        filepath = str(Path(filepath).resolve())
        
        # Determine file type from extension
        if filepath.endswith('.tsv') or filepath.endswith('.txt'):
            return cls.load_tsv(filepath, identifier_column=identifier_column, **kwargs)
        elif filepath.endswith('.csv'):
            return cls.load_csv(filepath, identifier_column=identifier_column, **kwargs)
        else:
            # Try to detect from content
            delimiter = cls.detect_delimiter(filepath)
            if delimiter == '\t':
                return cls.load_tsv(filepath, identifier_column=identifier_column, **kwargs)
            else:
                return cls.load_csv(filepath, identifier_column=identifier_column, **kwargs)
    
    @staticmethod
    def _validate_dataframe(df: pd.DataFrame, filepath: str) -> None:
        """
        Basic validation of loaded DataFrame.
        
        Args:
            df: DataFrame to validate
            filepath: Source file path for logging
        """
        # Check if DataFrame is empty
        if df.empty:
            logger.warning(f"Loaded empty DataFrame from {filepath}")
        
        # Check for high proportion of NA values
        na_proportion = df.isna().sum().sum() / (df.shape[0] * df.shape[1])
        if na_proportion > 0.5:
            logger.warning(
                f"High proportion of NA values ({na_proportion:.1%}) in {filepath}. "
                "Consider checking data integrity."
            )
        
        # Check for duplicate indices if index is set
        if df.index.name and df.index.duplicated().any():
            n_duplicates = df.index.duplicated().sum()
            logger.warning(
                f"Found {n_duplicates} duplicate index values in {filepath}. "
                "This may cause issues in downstream processing."
            )
        
        # Check for suspicious column names (often indicates parsing issues)
        unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed')]
        if unnamed_cols:
            logger.warning(
                f"Found {len(unnamed_cols)} unnamed columns in {filepath}. "
                "This might indicate header parsing issues."
            )