"""Tests for the IO utility functions."""

import os
import tempfile
from biomapper.utils.io_utils import load_tabular_file, get_max_file_size


def test_load_tabular_file_with_comments():
    """Test loading a file with comment lines."""
    # Create a temporary CSV file with comment lines
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+", delete=False) as f:
        f.write("# This is a comment line\n")
        f.write("# This is another comment line\n")
        f.write("col1,col2,col3\n")
        f.write("a,b,c\n")
        f.write("# Comment in the middle\n")
        f.write("d,e,f\n")
        f.write("g,h,i\n")
        temp_path = f.name

    try:
        # Load the file with our utility
        df = load_tabular_file(temp_path)

        # Check that comments were properly excluded
        assert len(df) == 3
        assert list(df.columns) == ["col1", "col2", "col3"]
        assert df.iloc[0]["col1"] == "a"
        assert df.iloc[1]["col1"] == "d"
        assert df.iloc[2]["col1"] == "g"
    finally:
        # Clean up
        os.unlink(temp_path)


def test_load_tabular_file_auto_separator():
    """Test automatic separator detection based on file extension."""
    # Create a temporary TSV file
    with tempfile.NamedTemporaryFile(suffix=".tsv", mode="w+", delete=False) as f:
        f.write("col1\tcol2\tcol3\n")
        f.write("a\tb\tc\n")
        f.write("d\te\tf\n")
        tsv_path = f.name

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+", delete=False) as f:
        f.write("col1,col2,col3\n")
        f.write("a,b,c\n")
        f.write("d,e,f\n")
        csv_path = f.name

    try:
        # Test TSV loading (should auto-detect tab separator)
        tsv_df = load_tabular_file(tsv_path)
        assert list(tsv_df.columns) == ["col1", "col2", "col3"]
        assert tsv_df.iloc[0]["col2"] == "b"

        # Test CSV loading (should auto-detect comma separator)
        csv_df = load_tabular_file(csv_path)
        assert list(csv_df.columns) == ["col1", "col2", "col3"]
        assert csv_df.iloc[0]["col2"] == "b"
    finally:
        # Clean up
        os.unlink(tsv_path)
        os.unlink(csv_path)


def test_get_max_file_size():
    """Test the dynamic file size calculation."""
    max_size = get_max_file_size()

    # Should return a reasonable size (at least 100MB)
    assert max_size > 100_000_000

    # Should be no more than total system memory
    import psutil

    total_memory = psutil.virtual_memory().total
    assert max_size <= total_memory
