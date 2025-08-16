"""Validation utilities for biological data files."""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FileValidator:
    """Validator for biological data files and DataFrames."""
    
    # Common biological identifier patterns
    IDENTIFIER_PATTERNS = {
        'uniprot': re.compile(r'^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$'),
        'ensembl_gene': re.compile(r'^ENS[A-Z]+G[0-9]{11}$'),
        'ensembl_protein': re.compile(r'^ENS[A-Z]+P[0-9]{11}$'),
        'ensembl_transcript': re.compile(r'^ENS[A-Z]+T[0-9]{11}$'),
        'refseq': re.compile(r'^(NM_|NP_|XM_|XP_)[0-9]+(\.[0-9]+)?$'),
        'hgnc': re.compile(r'^HGNC:[0-9]+$'),
        'entrez': re.compile(r'^[0-9]+$'),
        'hmdb': re.compile(r'^HMDB[0-9]{7}$'),
        'chebi': re.compile(r'^CHEBI:[0-9]+$'),
        'kegg': re.compile(r'^C[0-9]{5}$'),
        'pubchem': re.compile(r'^[0-9]+$'),
        'inchikey': re.compile(r'^[A-Z]{14}-[A-Z]{10}-[A-Z]$'),
        'loinc': re.compile(r'^[0-9]+-[0-9]$'),
    }
    
    # Expected columns for common biological data types
    EXPECTED_COLUMNS = {
        'proteomics': ['uniprot', 'gene_symbol', 'protein_name'],
        'metabolomics': ['metabolite_name', 'hmdb_id', 'kegg_id', 'inchikey'],
        'genomics': ['gene_id', 'chromosome', 'start', 'end', 'strand'],
        'clinical': ['sample_id', 'patient_id', 'test_name', 'value', 'unit'],
    }
    
    @classmethod
    def validate_file(
        cls,
        filepath: str,
        data_type: Optional[str] = None,
        required_columns: Optional[List[str]] = None,
        identifier_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a biological data file before loading.
        
        Args:
            filepath: Path to file
            data_type: Type of biological data (proteomics, metabolomics, etc.)
            required_columns: List of required column names
            identifier_column: Main identifier column to validate
            
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'stats': {},
            'recommendations': []
        }
        
        filepath = Path(filepath)
        
        # Check file exists
        if not filepath.exists():
            results['valid'] = False
            results['errors'].append(f"File not found: {filepath}")
            return results
        
        # Check file size
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        results['stats']['file_size_mb'] = round(file_size_mb, 2)
        
        if file_size_mb > 1000:
            results['warnings'].append(
                f"Large file ({file_size_mb:.1f} MB). Consider using chunked loading."
            )
            results['recommendations'].append("Use BiologicalFileLoader.load_chunked() for memory efficiency")
        
        # Check file extension
        extension = filepath.suffix.lower()
        if extension not in ['.csv', '.tsv', '.txt']:
            results['warnings'].append(
                f"Unusual file extension '{extension}'. Expected .csv, .tsv, or .txt"
            )
        
        # Try to peek at the file structure
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                first_lines = [f.readline() for _ in range(10)]
            
            # Check for common issues
            if any(line.startswith('#') for line in first_lines):
                results['stats']['has_comments'] = True
                results['recommendations'].append("File contains comment lines. Use comment='#' parameter")
            
            # Check for empty lines
            if any(not line.strip() for line in first_lines):
                results['warnings'].append("File contains empty lines")
            
        except Exception as e:
            results['warnings'].append(f"Could not peek at file content: {e}")
        
        return results
    
    @classmethod
    def validate_dataframe(
        cls,
        df: pd.DataFrame,
        data_type: Optional[str] = None,
        required_columns: Optional[List[str]] = None,
        identifier_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a loaded biological DataFrame.
        
        Args:
            df: DataFrame to validate
            data_type: Type of biological data
            required_columns: Required column names
            identifier_column: Main identifier column
            
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'stats': {},
            'recommendations': []
        }
        
        # Basic statistics
        results['stats']['n_rows'] = len(df)
        results['stats']['n_columns'] = len(df.columns)
        results['stats']['memory_usage_mb'] = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
        
        # Check if empty
        if df.empty:
            results['valid'] = False
            results['errors'].append("DataFrame is empty")
            return results
        
        # Check for required columns
        if required_columns:
            missing_cols = set(required_columns) - set(df.columns)
            if missing_cols:
                results['valid'] = False
                results['errors'].append(f"Missing required columns: {missing_cols}")
        
        # Check expected columns for data type
        if data_type and data_type in cls.EXPECTED_COLUMNS:
            expected = cls.EXPECTED_COLUMNS[data_type]
            missing_expected = set(expected) - set(df.columns)
            if missing_expected:
                results['warnings'].append(
                    f"Missing expected columns for {data_type} data: {missing_expected}"
                )
        
        # Validate identifier column
        if identifier_column:
            validation = cls.validate_identifier_column(df, identifier_column)
            results['stats']['identifier_validation'] = validation
            
            if not validation['valid']:
                results['warnings'].extend(validation['warnings'])
                if validation.get('errors'):
                    results['errors'].extend(validation['errors'])
                    results['valid'] = False
        
        # Check for duplicate rows
        n_duplicates = df.duplicated().sum()
        if n_duplicates > 0:
            results['warnings'].append(f"Found {n_duplicates} duplicate rows")
            results['stats']['duplicate_rows'] = n_duplicates
        
        # Check NA values
        na_stats = cls._analyze_na_values(df)
        results['stats']['na_analysis'] = na_stats
        
        if na_stats['total_na_percent'] > 50:
            results['warnings'].append(
                f"High proportion of NA values ({na_stats['total_na_percent']:.1f}%)"
            )
        
        # Check for suspicious patterns
        suspicious = cls._check_suspicious_patterns(df)
        if suspicious:
            results['warnings'].extend(suspicious)
        
        # Data type analysis
        dtype_stats = cls._analyze_dtypes(df)
        results['stats']['dtype_analysis'] = dtype_stats
        
        if dtype_stats.get('mixed_type_columns'):
            results['warnings'].append(
                f"Columns with mixed types detected: {dtype_stats['mixed_type_columns']}"
            )
        
        return results
    
    @classmethod
    def validate_identifier_column(
        cls,
        df: pd.DataFrame,
        column: str,
        identifier_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate an identifier column specifically.
        
        Args:
            df: DataFrame containing the column
            column: Column name to validate
            identifier_type: Expected identifier type (uniprot, ensembl, etc.)
            
        Returns:
            Validation results
        """
        results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'stats': {}
        }
        
        # Check column exists
        if column not in df.columns:
            results['valid'] = False
            results['errors'].append(f"Column '{column}' not found")
            return results
        
        col_data = df[column]
        
        # Check for NA values
        na_count = col_data.isna().sum()
        if na_count > 0:
            na_percent = (na_count / len(col_data)) * 100
            results['warnings'].append(
                f"Identifier column contains {na_count} NA values ({na_percent:.1f}%)"
            )
            results['stats']['na_count'] = na_count
        
        # Check for duplicates
        duplicate_count = col_data.duplicated().sum()
        if duplicate_count > 0:
            results['warnings'].append(
                f"Identifier column contains {duplicate_count} duplicate values"
            )
            results['stats']['duplicate_count'] = duplicate_count
        
        # Check for empty strings
        if col_data.dtype == 'object':
            empty_count = (col_data == '').sum()
            if empty_count > 0:
                results['warnings'].append(
                    f"Identifier column contains {empty_count} empty strings"
                )
        
        # Validate format if type specified
        if identifier_type and identifier_type in cls.IDENTIFIER_PATTERNS:
            pattern = cls.IDENTIFIER_PATTERNS[identifier_type]
            valid_data = col_data.dropna()
            
            if len(valid_data) > 0:
                # Sample validation (check first 100 non-NA values)
                sample = valid_data.head(100)
                invalid = []
                
                for val in sample:
                    if not pattern.match(str(val)):
                        invalid.append(str(val))
                
                if invalid:
                    results['warnings'].append(
                        f"Some identifiers don't match expected {identifier_type} format. "
                        f"Examples: {invalid[:5]}"
                    )
                    results['stats']['format_validation'] = {
                        'checked': len(sample),
                        'invalid': len(invalid),
                        'examples': invalid[:5]
                    }
        
        # Auto-detect identifier type if not specified
        if not identifier_type:
            detected_type = cls._detect_identifier_type(col_data)
            if detected_type:
                results['stats']['detected_type'] = detected_type
                logger.info(f"Detected identifier type: {detected_type}")
        
        return results
    
    @classmethod
    def _detect_identifier_type(cls, series: pd.Series) -> Optional[str]:
        """
        Auto-detect the type of biological identifier.
        
        Args:
            series: Column data
            
        Returns:
            Detected type or None
        """
        # Sample non-NA values
        sample = series.dropna().head(100)
        if len(sample) == 0:
            return None
        
        # Count matches for each pattern
        matches = {}
        for id_type, pattern in cls.IDENTIFIER_PATTERNS.items():
            match_count = sum(1 for val in sample if pattern.match(str(val)))
            if match_count > 0:
                matches[id_type] = match_count / len(sample)
        
        # Return type with highest match rate (if > 50%)
        if matches:
            best_match = max(matches.items(), key=lambda x: x[1])
            if best_match[1] > 0.5:
                return best_match[0]
        
        return None
    
    @staticmethod
    def _analyze_na_values(df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze NA value patterns in DataFrame."""
        total_cells = df.shape[0] * df.shape[1]
        total_na = df.isna().sum().sum()
        
        column_na = {}
        for col in df.columns:
            na_count = df[col].isna().sum()
            if na_count > 0:
                column_na[col] = {
                    'count': na_count,
                    'percent': round((na_count / len(df)) * 100, 2)
                }
        
        return {
            'total_na': total_na,
            'total_na_percent': round((total_na / total_cells) * 100, 2),
            'columns_with_na': column_na,
            'columns_all_na': [col for col in df.columns if df[col].isna().all()]
        }
    
    @staticmethod
    def _analyze_dtypes(df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data types in DataFrame."""
        dtype_counts = df.dtypes.value_counts().to_dict()
        dtype_counts = {str(k): v for k, v in dtype_counts.items()}
        
        # Check for object columns that might be numeric
        mixed_type_columns = []
        for col in df.select_dtypes(include=['object']).columns:
            sample = df[col].dropna().head(100)
            if len(sample) > 0:
                # Try to convert to numeric
                try:
                    pd.to_numeric(sample, errors='raise')
                    mixed_type_columns.append(col)
                except (ValueError, TypeError):
                    pass
        
        return {
            'dtype_counts': dtype_counts,
            'object_columns': df.select_dtypes(include=['object']).columns.tolist(),
            'numeric_columns': df.select_dtypes(include=['number']).columns.tolist(),
            'mixed_type_columns': mixed_type_columns
        }
    
    @staticmethod
    def _check_suspicious_patterns(df: pd.DataFrame) -> List[str]:
        """Check for suspicious patterns that might indicate parsing issues."""
        warnings = []
        
        # Check for unnamed columns
        unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed')]
        if unnamed_cols:
            warnings.append(f"Found {len(unnamed_cols)} unnamed columns (possible header issue)")
        
        # Check for columns that are all the same value
        for col in df.columns:
            if df[col].nunique() == 1:
                warnings.append(f"Column '{col}' has only one unique value")
        
        # Check for very long string values (might indicate concatenated fields)
        for col in df.select_dtypes(include=['object']).columns:
            sample = df[col].dropna().head(100)
            if len(sample) > 0:
                max_len = sample.astype(str).str.len().max()
                if max_len > 500:
                    warnings.append(
                        f"Column '{col}' contains very long strings (max {max_len} chars)"
                    )
        
        return warnings
    
    @classmethod
    def generate_report(cls, validation_results: Dict[str, Any]) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            validation_results: Results from validate_file or validate_dataframe
            
        Returns:
            Formatted report string
        """
        lines = ["=" * 60, "BIOLOGICAL DATA VALIDATION REPORT", "=" * 60]
        
        # Overall status
        status = "✓ VALID" if validation_results['valid'] else "✗ INVALID"
        lines.append(f"\nStatus: {status}")
        
        # Errors
        if validation_results['errors']:
            lines.append("\n### ERRORS ###")
            for error in validation_results['errors']:
                lines.append(f"  ✗ {error}")
        
        # Warnings
        if validation_results['warnings']:
            lines.append("\n### WARNINGS ###")
            for warning in validation_results['warnings']:
                lines.append(f"  ⚠ {warning}")
        
        # Statistics
        if validation_results['stats']:
            lines.append("\n### STATISTICS ###")
            for key, value in validation_results['stats'].items():
                if isinstance(value, dict):
                    lines.append(f"  {key}:")
                    for k, v in value.items():
                        lines.append(f"    - {k}: {v}")
                else:
                    lines.append(f"  {key}: {value}")
        
        # Recommendations
        if validation_results.get('recommendations'):
            lines.append("\n### RECOMMENDATIONS ###")
            for rec in validation_results['recommendations']:
                lines.append(f"  → {rec}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)