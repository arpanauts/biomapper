"""Tests for set analysis functionality."""

import pytest
from pathlib import Path
import pandas as pd
from biomapper.core.set_analysis import SetAnalyzer


@pytest.fixture
def sample_data(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create sample datasets for testing."""
    # Create sample CSV files
    data1 = pd.DataFrame({"uniprot": ["P1", "P2", "P3"], "value": [1, 2, 3]})
    data2 = pd.DataFrame({"identifier": ["P2", "P3", "P4"], "other": ["a", "b", "c"]})
    data3 = pd.DataFrame({"UniProt": ["P3", "P4", "P5"], "type": ["x", "y", "z"]})

    path1 = tmp_path / "data1.csv"
    path2 = tmp_path / "data2.csv"
    path3 = tmp_path / "data3.tsv"

    data1.to_csv(path1, index=False)
    data2.to_csv(path2, index=False)
    data3.to_csv(path3, sep="\t", index=False)

    return path1, path2, path3


@pytest.fixture
def analyzer() -> SetAnalyzer:
    """Create a SetAnalyzer instance for testing."""
    return SetAnalyzer(
        {
            "data1": "uniprot",
            "data2": "identifier",
            "data3": "UniProt",
            "data4": "uniprot",
        }
    )


def test_load_dataset(
    sample_data: tuple[Path, Path, Path], analyzer: SetAnalyzer
) -> None:
    """Test loading datasets."""
    path1, path2, path3 = sample_data

    analyzer.load_dataset("data1", path1)
    assert len(analyzer.datasets) == 1
    assert "data1" in analyzer.datasets
    assert analyzer.id_columns["data1"] == "uniprot"


def test_detect_id_column(
    sample_data: tuple[Path, Path, Path], analyzer: SetAnalyzer
) -> None:
    """Test ID column detection."""
    path1, path2, path3 = sample_data

    assert analyzer.id_columns["data1"] == "uniprot"
    assert analyzer.id_columns["data2"] == "identifier"
    assert analyzer.id_columns["data3"] == "UniProt"


def test_analyze(sample_data: tuple[Path, Path, Path], analyzer: SetAnalyzer) -> None:
    """Test set analysis functionality."""
    path1, path2, path3 = sample_data

    # Load all datasets before analysis
    analyzer.load_dataset("data1", path1)
    analyzer.load_dataset("data2", path2)
    analyzer.load_dataset("data3", path3)

    results = analyzer.analyze()

    assert "datasets" in results
    assert "intersections" in results
    assert "unique" in results

    # Check dataset sizes
    assert results["datasets"]["data1"]["size"] == 3
    assert results["datasets"]["data2"]["size"] == 3
    assert results["datasets"]["data3"]["size"] == 3

    # Check intersections
    intersection_sizes = {
        tuple(sorted(i["sets"])): i["size"] for i in results["intersections"]
    }
    assert intersection_sizes[("data1", "data2")] == 2  # P2, P3
    assert intersection_sizes[("data2", "data3")] == 2  # P3, P4
    assert intersection_sizes[("data1", "data3")] == 1  # P3

    # Check unique elements
    assert results["unique"]["data1"]["size"] == 1  # P1
    assert results["unique"]["data2"]["size"] == 0
    assert results["unique"]["data3"]["size"] == 1  # P5


def test_id_column_update(
    sample_data: tuple[Path, Path, Path], analyzer: SetAnalyzer
) -> None:
    """Test updating ID column."""
    path1, _, _ = sample_data

    # Load dataset before testing column update
    analyzer.load_dataset("data1", path1)

    # Test valid column update
    analyzer["data1"] = "value"
    assert analyzer.id_columns["data1"] == "value"

    # Test invalid dataset
    with pytest.raises(ValueError, match="Dataset 'invalid' not found"):
        analyzer["invalid"] = "col"

    # Test invalid column
    with pytest.raises(ValueError, match="Column 'invalid' not found"):
        analyzer["data1"] = "invalid"


def test_plot_venn(
    sample_data: tuple[Path, Path, Path], tmp_path: Path, analyzer: SetAnalyzer
) -> None:
    """Test Venn diagram generation."""
    path1, path2, path3 = sample_data

    # Test with 2 sets (should work)
    analyzer.load_dataset("data1", path1)
    analyzer.load_dataset("data2", path2)

    output_path = tmp_path / "venn.png"
    analyzer.plot_venn(str(output_path))
    assert output_path.exists()

    # Test with 3 sets (should work)
    analyzer.load_dataset("data3", path3)
    output_path_3 = tmp_path / "venn_3.png"
    analyzer.plot_venn(str(output_path_3))
    assert output_path_3.exists()

    # Test with 4 sets by adding another dataset (should raise error)
    analyzer.load_dataset("data4", path1)  # Using path1 again just for testing
    with pytest.raises(
        ValueError, match="Venn diagrams are only supported for 2 or 3 sets"
    ):
        analyzer.plot_venn()


def test_plot_upset(
    sample_data: tuple[Path, Path, Path], tmp_path: Path, analyzer: SetAnalyzer
) -> None:
    """Test UpSet plot generation."""
    path1, path2, path3 = sample_data

    # Load datasets before plotting
    analyzer.load_dataset("data1", path1)
    analyzer.load_dataset("data2", path2)
    analyzer.load_dataset("data3", path3)

    output_path = tmp_path / "upset.png"
    analyzer.plot_upset(str(output_path))

    assert output_path.exists()


def test_generate_report(
    sample_data: tuple[Path, Path, Path], tmp_path: Path, analyzer: SetAnalyzer
) -> None:
    """Test report generation."""
    path1, path2, path3 = sample_data

    # Load datasets before generating report
    analyzer.load_dataset("data1", path1)
    analyzer.load_dataset("data2", path2)
    analyzer.load_dataset("data3", path3)

    output_prefix = str(tmp_path / "report")
    analyzer.generate_report(output_prefix)

    assert Path(f"{output_prefix}_venn.png").exists()
    assert Path(f"{output_prefix}_upset.png").exists()


def test_error_cases() -> None:
    """Test error handling cases."""
    analyzer = SetAnalyzer({"dataset1": "column1"})

    # Test setting ID column for non-existent dataset
    with pytest.raises(ValueError, match="Dataset 'invalid' not found"):
        analyzer["invalid"] = "col"
