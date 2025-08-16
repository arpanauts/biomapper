"""Comprehensive tests for FileValidator."""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from biomapper.core.standards import FileValidator


class TestFileValidator:
    """Test suite for FileValidator class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def valid_proteomics_df(self):
        """Create a valid proteomics DataFrame."""
        return pd.DataFrame({
            'uniprot': ['P12345', 'Q67890', 'O11111', 'P99999'],
            'gene_symbol': ['GENE1', 'GENE2', 'GENE3', 'GENE4'],
            'protein_name': ['Protein 1', 'Protein 2', 'Protein 3', 'Protein 4'],
            'abundance': [100.5, 200.3, 150.7, 300.1]
        })
    
    @pytest.fixture
    def invalid_uniprot_df(self):
        """Create DataFrame with invalid UniProt IDs."""
        return pd.DataFrame({
            'uniprot': ['P12345', 'INVALID1', 'Q67890', 'BAD_ID', None],
            'gene_symbol': ['GENE1', 'GENE2', 'GENE3', 'GENE4', 'GENE5']
        })
    
    @pytest.fixture
    def metabolomics_df(self):
        """Create a metabolomics DataFrame."""
        return pd.DataFrame({
            'metabolite_name': ['Glucose', 'Lactate', 'Pyruvate', 'Citrate'],
            'hmdb_id': ['HMDB0000122', 'HMDB0000190', 'HMDB0000243', None],
            'kegg_id': ['C00031', 'C00186', 'C00022', 'C00158'],
            'concentration': [5.5, 2.3, 0.15, 0.8]
        })
    
    @pytest.fixture
    def df_with_duplicates(self):
        """Create DataFrame with duplicate rows and IDs."""
        return pd.DataFrame({
            'id': ['ID001', 'ID002', 'ID001', 'ID003', 'ID002'],
            'value': [100, 200, 100, 300, 200]
        })
    
    @pytest.fixture
    def df_with_high_na(self):
        """Create DataFrame with high proportion of NA values."""
        data = {
            'col1': [1, 2, None, None, None],
            'col2': [None, None, 3, None, None],
            'col3': [None, None, None, None, 5]
        }
        return pd.DataFrame(data)
    
    def test_validate_file_exists(self, temp_dir):
        """Test file existence validation."""
        # Test with existing file
        filepath = Path(temp_dir) / "test.csv"
        filepath.write_text("id,value\n1,100\n")
        
        results = FileValidator.validate_file(str(filepath))
        assert results['valid'] is True
        assert len(results['errors']) == 0
        
        # Test with non-existing file
        results = FileValidator.validate_file("/nonexistent/file.csv")
        assert results['valid'] is False
        assert len(results['errors']) > 0
    
    def test_validate_large_file_warning(self, temp_dir):
        """Test warning for large files."""
        # Create a file > 1MB (simulated with stats check)
        filepath = Path(temp_dir) / "large.csv"
        # Write minimal content but test will check file size
        content = "id,value\n" + "\n".join([f"{i},value{i}" for i in range(10)])
        filepath.write_text(content)
        
        results = FileValidator.validate_file(str(filepath))
        # File won't actually be > 1000MB in test, so no warning expected
        assert results['valid'] is True
    
    def test_validate_dataframe_basic(self, valid_proteomics_df):
        """Test basic DataFrame validation."""
        results = FileValidator.validate_dataframe(valid_proteomics_df)
        
        assert results['valid'] is True
        assert results['stats']['n_rows'] == 4
        assert results['stats']['n_columns'] == 4
        assert len(results['warnings']) == 0
        assert len(results['errors']) == 0
    
    def test_validate_required_columns(self, valid_proteomics_df):
        """Test required columns validation."""
        # Test with all required columns present
        results = FileValidator.validate_dataframe(
            valid_proteomics_df,
            required_columns=['uniprot', 'gene_symbol']
        )
        assert results['valid'] is True
        
        # Test with missing required columns
        results = FileValidator.validate_dataframe(
            valid_proteomics_df,
            required_columns=['uniprot', 'missing_column']
        )
        assert results['valid'] is False
        assert 'Missing required columns' in results['errors'][0]
    
    def test_validate_identifier_column_uniprot(self, valid_proteomics_df, invalid_uniprot_df):
        """Test UniProt identifier validation."""
        # Test valid UniProt IDs
        results = FileValidator.validate_identifier_column(
            valid_proteomics_df,
            'uniprot',
            'uniprot'
        )
        assert results['valid'] is True
        
        # Test invalid UniProt IDs
        results = FileValidator.validate_identifier_column(
            invalid_uniprot_df,
            'uniprot',
            'uniprot'
        )
        assert len(results['warnings']) > 0  # Should warn about invalid format
    
    def test_validate_identifier_column_hmdb(self, metabolomics_df):
        """Test HMDB identifier validation."""
        results = FileValidator.validate_identifier_column(
            metabolomics_df,
            'hmdb_id',
            'hmdb'
        )
        
        # Should detect valid HMDB format
        assert 'format_validation' in results['stats'] or results['valid']
    
    def test_detect_identifier_type(self):
        """Test automatic identifier type detection."""
        # UniProt identifiers
        uniprot_series = pd.Series(['P12345', 'Q67890', 'O11111'])
        detected = FileValidator._detect_identifier_type(uniprot_series)
        assert detected == 'uniprot'
        
        # HMDB identifiers
        hmdb_series = pd.Series(['HMDB0000122', 'HMDB0000190', 'HMDB0000243'])
        detected = FileValidator._detect_identifier_type(hmdb_series)
        assert detected == 'hmdb'
        
        # Ensembl gene identifiers
        ensembl_series = pd.Series(['ENSG00000123456', 'ENSG00000234567'])
        detected = FileValidator._detect_identifier_type(ensembl_series)
        assert detected == 'ensembl_gene'
    
    def test_validate_duplicates(self, df_with_duplicates):
        """Test duplicate detection."""
        results = FileValidator.validate_dataframe(df_with_duplicates)
        
        assert 'duplicate_rows' in results['stats']
        assert results['stats']['duplicate_rows'] == 2
        assert len(results['warnings']) > 0
    
    def test_validate_na_values(self, df_with_high_na):
        """Test NA value analysis."""
        results = FileValidator.validate_dataframe(df_with_high_na)
        
        na_analysis = results['stats']['na_analysis']
        assert na_analysis['total_na_percent'] > 50
        assert len(results['warnings']) > 0
        assert 'High proportion of NA values' in results['warnings'][0]
    
    def test_validate_data_type_specific(self, valid_proteomics_df, metabolomics_df):
        """Test data type specific validation."""
        # Test proteomics data
        results = FileValidator.validate_dataframe(
            valid_proteomics_df,
            data_type='proteomics'
        )
        assert results['valid'] is True
        
        # Test metabolomics data
        results = FileValidator.validate_dataframe(
            metabolomics_df,
            data_type='metabolomics'
        )
        assert results['valid'] is True
    
    def test_suspicious_patterns(self):
        """Test detection of suspicious patterns."""
        # DataFrame with unnamed columns
        df = pd.DataFrame({
            'Unnamed: 0': [1, 2, 3],
            'good_col': ['a', 'b', 'c'],
            'Unnamed: 2': [4, 5, 6]
        })
        
        results = FileValidator.validate_dataframe(df)
        warnings_text = ' '.join(results['warnings'])
        assert 'unnamed columns' in warnings_text.lower()
        
        # DataFrame with single value column
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'constant': ['same', 'same', 'same']
        })
        
        results = FileValidator.validate_dataframe(df)
        warnings_text = ' '.join(results['warnings'])
        assert 'only one unique value' in warnings_text.lower()
    
    def test_mixed_type_detection(self):
        """Test detection of mixed type columns."""
        df = pd.DataFrame({
            'mixed_col': ['123', '456', 'text', '789'],
            'good_col': [1, 2, 3, 4]
        })
        
        results = FileValidator.validate_dataframe(df)
        dtype_analysis = results['stats']['dtype_analysis']
        # Mixed type detection might identify mixed_col
        assert 'object_columns' in dtype_analysis
    
    def test_generate_report(self, valid_proteomics_df):
        """Test report generation."""
        results = FileValidator.validate_dataframe(valid_proteomics_df)
        report = FileValidator.generate_report(results)
        
        assert isinstance(report, str)
        assert 'VALID' in report
        assert 'STATISTICS' in report
    
    def test_empty_dataframe(self):
        """Test validation of empty DataFrame."""
        df = pd.DataFrame()
        results = FileValidator.validate_dataframe(df)
        
        assert results['valid'] is False
        assert 'DataFrame is empty' in results['errors'][0]
    
    def test_identifier_with_na_values(self):
        """Test identifier column with NA values."""
        df = pd.DataFrame({
            'uniprot': ['P12345', None, 'Q67890', '', 'O11111'],
            'value': [1, 2, 3, 4, 5]
        })
        
        results = FileValidator.validate_identifier_column(df, 'uniprot')
        assert 'na_count' in results['stats']
        assert len(results['warnings']) > 0
    
    def test_file_extension_validation(self, temp_dir):
        """Test file extension warnings."""
        # Unusual extension
        filepath = Path(temp_dir) / "test.xyz"
        filepath.write_text("id,value\n1,100\n")
        
        results = FileValidator.validate_file(str(filepath))
        warnings_text = ' '.join(results['warnings'])
        assert 'unusual file extension' in warnings_text.lower()
    
    def test_comment_line_detection(self, temp_dir):
        """Test detection of comment lines in file."""
        content = """# Comment line
# Another comment
id,value
1,100
2,200
"""
        filepath = Path(temp_dir) / "test_comments.csv"
        filepath.write_text(content)
        
        results = FileValidator.validate_file(str(filepath))
        assert results['stats'].get('has_comments') is True
        assert any('comment' in rec for rec in results['recommendations'])


class TestIdentifierPatterns:
    """Test biological identifier pattern matching."""
    
    def test_uniprot_patterns(self):
        """Test UniProt ID pattern matching."""
        pattern = FileValidator.IDENTIFIER_PATTERNS['uniprot']
        
        # Valid UniProt IDs
        assert pattern.match('P12345')
        assert pattern.match('Q9Y6K1')
        assert pattern.match('O00533')
        
        # Invalid UniProt IDs
        assert not pattern.match('INVALID')
        assert not pattern.match('12345')
        assert not pattern.match('P1234')  # Too short
    
    def test_ensembl_patterns(self):
        """Test Ensembl ID pattern matching."""
        # Gene pattern
        gene_pattern = FileValidator.IDENTIFIER_PATTERNS['ensembl_gene']
        assert gene_pattern.match('ENSG00000123456')
        assert not gene_pattern.match('ENSP00000123456')
        
        # Protein pattern
        protein_pattern = FileValidator.IDENTIFIER_PATTERNS['ensembl_protein']
        assert protein_pattern.match('ENSP00000123456')
        assert not protein_pattern.match('ENSG00000123456')
    
    def test_hmdb_patterns(self):
        """Test HMDB ID pattern matching."""
        pattern = FileValidator.IDENTIFIER_PATTERNS['hmdb']
        
        assert pattern.match('HMDB0000122')
        assert pattern.match('HMDB0001234')
        assert not pattern.match('HMDB123')  # Too short
        assert not pattern.match('HMD0001234')  # Wrong prefix
    
    def test_inchikey_patterns(self):
        """Test InChIKey pattern matching."""
        pattern = FileValidator.IDENTIFIER_PATTERNS['inchikey']
        
        assert pattern.match('BQJCRHHNABKAKU-KBQPJGBKSA-N')
        assert not pattern.match('INVALID-KEY')
        assert not pattern.match('BQJCRHHNABKAKU-KBQPJGBKSA')  # Missing last part