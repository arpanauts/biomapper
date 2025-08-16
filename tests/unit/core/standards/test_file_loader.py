"""Comprehensive tests for BiologicalFileLoader."""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path
from biomapper.core.standards import BiologicalFileLoader


class TestBiologicalFileLoader:
    """Test suite for BiologicalFileLoader class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def tsv_with_comments(self, temp_dir):
        """Create a TSV file with comment lines."""
        content = """# This is a comment line
# Another comment
uniprot\tgene_symbol\tprotein_name
P12345\tGENE1\tProtein 1
Q67890\tGENE2\tProtein 2
# Mid-file comment (should be ignored)
O11111\tGENE3\tProtein 3
"""
        filepath = Path(temp_dir) / "test_comments.tsv"
        filepath.write_text(content)
        return str(filepath)
    
    @pytest.fixture
    def csv_with_mixed_types(self, temp_dir):
        """Create a CSV file with mixed data types."""
        content = """id,value,description
1,123.45,Normal value
2,NA,Missing value
3,456.78,Another value
4,,Empty value
5,789.01,Last value
"""
        filepath = Path(temp_dir) / "test_mixed.csv"
        filepath.write_text(content)
        return str(filepath)
    
    @pytest.fixture
    def tsv_with_na_values(self, temp_dir):
        """Create a TSV file with various NA representations."""
        content = """sample_id\thmdb_id\tvalue\tstatus
S001\tHMDB0001234\t123.4\tComplete
S002\tNA\t456.7\tComplete
S003\tn/a\t.\tMissing
S004\tHMDB0005678\tnull\tPartial
S005\t-\t789.0\tComplete
S006\tNone\tNaN\tMissing
"""
        filepath = Path(temp_dir) / "test_na_values.tsv"
        filepath.write_text(content)
        return str(filepath)
    
    @pytest.fixture
    def malformed_csv(self, temp_dir):
        """Create a CSV with inconsistent columns."""
        content = """col1,col2,col3
val1,val2,val3
val4,val5
val6,val7,val8,val9
val10,val11,val12
"""
        filepath = Path(temp_dir) / "test_malformed.csv"
        filepath.write_text(content)
        return str(filepath)
    
    @pytest.fixture
    def biological_identifiers_tsv(self, temp_dir):
        """Create a TSV with biological identifiers."""
        content = """uniprot\tensembl_protein\tgene_symbol\trefseq
P12345\tENSP00000123456\tGENE1\tNP_001234.1
Q67890-1\tENSP00000234567\tGENE2\tNP_002345.2
O11111\tENSP00000345678\tGENE3\tXP_003456.1
P12345.2\tENSP00000456789\tGENE1\tNP_001234.2
"""
        filepath = Path(temp_dir) / "test_identifiers.tsv"
        filepath.write_text(content)
        return str(filepath)
    
    def test_load_tsv_with_comments(self, tsv_with_comments):
        """Test loading TSV file with comment lines."""
        df = BiologicalFileLoader.load_tsv(tsv_with_comments)
        
        # Should skip comment lines
        assert len(df) == 3
        assert list(df.columns) == ['uniprot', 'gene_symbol', 'protein_name']
        assert df.iloc[0]['uniprot'] == 'P12345'
        assert df.iloc[2]['uniprot'] == 'O11111'
    
    def test_load_csv_with_mixed_types(self, csv_with_mixed_types):
        """Test loading CSV with mixed data types."""
        df = BiologicalFileLoader.load_csv(csv_with_mixed_types)
        
        assert len(df) == 5
        # NA values should be recognized
        assert pd.isna(df.iloc[1]['value'])
        assert pd.isna(df.iloc[3]['value'])
        # Numeric values should be preserved
        assert df.iloc[0]['value'] == 123.45
    
    def test_na_value_handling(self, tsv_with_na_values):
        """Test comprehensive NA value recognition."""
        df = BiologicalFileLoader.load_tsv(tsv_with_na_values)
        
        # Check various NA representations are recognized
        assert pd.isna(df.iloc[1]['hmdb_id'])  # NA
        assert pd.isna(df.iloc[2]['hmdb_id'])  # n/a
        assert pd.isna(df.iloc[2]['value'])     # .
        assert pd.isna(df.iloc[3]['value'])     # null
        assert pd.isna(df.iloc[4]['hmdb_id'])   # -
        assert pd.isna(df.iloc[5]['hmdb_id'])   # None
        assert pd.isna(df.iloc[5]['value'])     # NaN
    
    def test_auto_detect_encoding(self, temp_dir):
        """Test encoding auto-detection."""
        # Create file with UTF-8 encoding
        content = "id,name\n1,Café\n2,Résumé\n"
        filepath = Path(temp_dir) / "test_utf8.csv"
        filepath.write_text(content, encoding='utf-8')
        
        encoding = BiologicalFileLoader.detect_encoding(str(filepath))
        assert encoding in ['utf-8', 'UTF-8', 'ascii']
    
    def test_auto_detect_delimiter(self, temp_dir):
        """Test delimiter auto-detection."""
        # Test TSV detection
        tsv_content = "col1\tcol2\tcol3\nval1\tval2\tval3\n"
        tsv_path = Path(temp_dir) / "test.tsv"
        tsv_path.write_text(tsv_content)
        
        delimiter = BiologicalFileLoader.detect_delimiter(str(tsv_path))
        assert delimiter == '\t'
        
        # Test CSV detection
        csv_content = "col1,col2,col3\nval1,val2,val3\n"
        csv_path = Path(temp_dir) / "test.csv"
        csv_path.write_text(csv_content)
        
        delimiter = BiologicalFileLoader.detect_delimiter(str(csv_path))
        assert delimiter == ','
    
    def test_detect_comment_char(self, tsv_with_comments):
        """Test comment character detection."""
        comment_char = BiologicalFileLoader.detect_comment_char(tsv_with_comments)
        assert comment_char == '#'
    
    def test_identifier_column_setting(self, biological_identifiers_tsv):
        """Test setting identifier column as index."""
        df = BiologicalFileLoader.load_tsv(
            biological_identifiers_tsv,
            identifier_column='uniprot'
        )
        
        # Index should be set to uniprot column
        assert df.index.name == 'uniprot'
        assert 'P12345' in df.index
        assert 'Q67890-1' in df.index
    
    def test_malformed_file_handling(self, malformed_csv):
        """Test handling of malformed files."""
        # Should handle with warning, not error
        df = BiologicalFileLoader.load_csv(malformed_csv)
        assert len(df) > 0  # Should load something
    
    def test_chunked_loading(self, temp_dir):
        """Test chunked loading for large files."""
        # Create a larger file
        rows = []
        for i in range(100):
            rows.append(f"ID{i:04d},Value{i},Desc{i}")
        
        content = "id,value,description\n" + "\n".join(rows)
        filepath = Path(temp_dir) / "test_large.csv"
        filepath.write_text(content)
        
        # Load in chunks
        chunks = list(BiologicalFileLoader.load_chunked(
            str(filepath),
            chunk_size=20
        ))
        
        assert len(chunks) == 5  # 100 rows / 20 per chunk
        assert len(chunks[0]) == 20
        assert len(chunks[-1]) == 20
    
    def test_auto_load_format_detection(self, tsv_with_comments, csv_with_mixed_types):
        """Test automatic format detection based on extension."""
        # Test TSV
        df_tsv = BiologicalFileLoader.auto_load(tsv_with_comments)
        assert len(df_tsv) == 3
        
        # Test CSV
        df_csv = BiologicalFileLoader.auto_load(csv_with_mixed_types)
        assert len(df_csv) == 5
    
    def test_validation_flag(self, biological_identifiers_tsv):
        """Test that validation can be enabled/disabled."""
        # With validation (default)
        df_validated = BiologicalFileLoader.load_tsv(
            biological_identifiers_tsv,
            validate=True
        )
        assert len(df_validated) == 4
        
        # Without validation
        df_no_validation = BiologicalFileLoader.load_tsv(
            biological_identifiers_tsv,
            validate=False
        )
        assert len(df_no_validation) == 4
    
    def test_file_not_found_error(self):
        """Test appropriate error on missing file."""
        with pytest.raises(Exception):
            BiologicalFileLoader.load_tsv("/nonexistent/file.tsv")
    
    def test_empty_file_handling(self, temp_dir):
        """Test handling of empty files."""
        filepath = Path(temp_dir) / "empty.csv"
        filepath.write_text("")
        
        with pytest.raises(pd.errors.EmptyDataError):
            BiologicalFileLoader.load_csv(str(filepath))
    
    def test_unicode_handling(self, temp_dir):
        """Test handling of Unicode characters."""
        content = """id,name,description
1,αβγ,Greek letters
2,你好,Chinese
3,🧬,Emoji DNA
4,Müller,German umlaut
"""
        filepath = Path(temp_dir) / "test_unicode.csv"
        filepath.write_text(content, encoding='utf-8')
        
        # Force UTF-8 encoding to ensure consistent test results
        df = BiologicalFileLoader.load_csv(str(filepath), encoding='utf-8')
        assert len(df) == 4
        assert df.iloc[0]['name'] == 'αβγ'
        assert df.iloc[1]['name'] == '你好'
        assert df.iloc[3]['name'] == 'Müller'
    
    def test_skip_blank_lines(self, temp_dir):
        """Test that blank lines are skipped."""
        content = """id,value

1,100

2,200

3,300
"""
        filepath = Path(temp_dir) / "test_blanks.csv"
        filepath.write_text(content)
        
        df = BiologicalFileLoader.load_csv(str(filepath))
        assert len(df) == 3  # Should skip blank lines
    
    def test_custom_na_values(self, temp_dir):
        """Test that all custom NA values are recognized."""
        na_values = BiologicalFileLoader.NA_VALUES
        
        # Create file with all NA value variants
        rows = ["id,value"]
        for i, na_val in enumerate(na_values):
            rows.append(f"{i},{na_val}")
        
        content = "\n".join(rows)
        filepath = Path(temp_dir) / "test_all_na.csv"
        filepath.write_text(content)
        
        df = BiologicalFileLoader.load_csv(str(filepath))
        
        # All values should be recognized as NA
        assert df['value'].isna().all()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_very_long_lines(self, temp_dir):
        """Test handling of files with very long lines."""
        # Create file with a very long line
        long_value = "A" * 10000
        content = f"id,long_value\n1,{long_value}\n2,short\n"
        filepath = Path(temp_dir) / "test_long.csv"
        filepath.write_text(content)
        
        df = BiologicalFileLoader.load_csv(str(filepath))
        assert len(df) == 2
        assert len(df.iloc[0]['long_value']) == 10000
    
    def test_special_delimiter_detection(self, temp_dir):
        """Test detection of less common delimiters."""
        # Semicolon delimiter
        content = "col1;col2;col3\nval1;val2;val3\n"
        filepath = Path(temp_dir) / "test_semicolon.csv"
        filepath.write_text(content)
        
        delimiter = BiologicalFileLoader.detect_delimiter(str(filepath))
        assert delimiter == ';'
    
    def test_quoted_fields_with_delimiters(self, temp_dir):
        """Test handling of quoted fields containing delimiters."""
        content = '''id,description,value
1,"Contains, comma",100
2,"Contains\ttab",200
3,"Contains""quote",300
'''
        filepath = Path(temp_dir) / "test_quoted.csv"
        filepath.write_text(content)
        
        df = BiologicalFileLoader.load_csv(str(filepath))
        assert len(df) == 3
        assert df.iloc[0]['description'] == "Contains, comma"
        assert df.iloc[1]['description'] == "Contains\ttab"
        assert df.iloc[2]['description'] == 'Contains"quote'