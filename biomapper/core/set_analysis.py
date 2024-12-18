"""Module for performing set analysis on omic datasets."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
import matplotlib.pyplot as plt
import pandas as pd
import venn  # type: ignore
from upsetplot import plot as upsetplot  # type: ignore

logger = logging.getLogger(__name__)


class DatasetInfo(TypedDict):
    """Type definition for dataset information."""

    size: int
    sample_ids: List[str]


class IntersectionInfo(TypedDict):
    """Type definition for intersection information."""

    sets: List[str]
    size: int
    sample_ids: List[str]


class AnalysisResults(TypedDict):
    """Type definition for analysis results."""

    datasets: Dict[str, DatasetInfo]
    intersections: List[IntersectionInfo]
    unique: Dict[str, DatasetInfo]


class SetAnalyzer:
    """Analyzer for performing set comparisons across omic datasets."""

    def __init__(self, id_columns: dict[str, str]) -> None:
        """Initialize the analyzer.

        Args:
            id_columns: Mapping of dataset names to their ID column names

        Raises:
            ValueError: If id_columns is empty
        """
        if not id_columns:
            raise ValueError("id_columns mapping cannot be empty")

        self.id_columns = {}  # Initialize empty dict
        self.datasets: dict[str, pd.DataFrame] = {}
        self.id_delimiters: dict[str, list[str]] = {}  # Change type to list[str]
        # Use property setter for validation
        for name, col in id_columns.items():
            self.set_id_column(name, col)

    def set_id_column(self, dataset: str, column: str) -> None:
        """Set ID column for a dataset with validation."""
        if dataset in self.datasets:
            if column not in self.datasets[dataset].columns:
                raise ValueError(
                    f"Column '{column}' not found in dataset '{dataset}'. "
                    f"Available columns: {', '.join(self.datasets[dataset].columns)}"
                )
        self.id_columns[dataset] = column

    @property
    def id_columns(self) -> dict[str, str]:
        return self._id_columns

    @id_columns.setter
    def id_columns(self, value: dict[str, str]) -> None:
        self._id_columns = value

    def __setitem__(self, key: str, value: str) -> None:
        """Set ID column for a dataset."""
        if key not in self.datasets:
            raise ValueError(f"Dataset '{key}' not found")

        if value not in self.datasets[key].columns:
            raise ValueError(f"Column '{value}' not found in dataset '{key}'")

        self._id_columns[key] = value

    def load_dataset(
        self, name: str, path: Path | str, id_delimiters: list[str] | None = None
    ) -> None:
        """Load a dataset from file.

        Args:
            name: Name identifier for the dataset
            path: Path to the data file (CSV/TSV)
            id_delimiters: Optional list of delimiters to split IDs

        Raises:
            ValueError: If dataset name not found in id_columns mapping
            ValueError: If specified ID column not found in dataset
            ValueError: If file format not supported
        """
        name = str(name)
        if name not in self.id_columns:
            raise ValueError(
                f"No ID column mapping provided for dataset '{name}'. "
                f"Available mappings: {', '.join(self.id_columns.keys())}"
            )

        path_str = str(path)
        if not (path_str.endswith(".csv") or path_str.endswith(".tsv")):
            raise ValueError("File must be .csv or .tsv format")

        sep = "\t" if path_str.endswith(".tsv") else ","

        try:
            df = pd.read_csv(path, sep=sep)
        except Exception as e:
            raise ValueError(f"Failed to load dataset: {str(e)}")

        df.columns = df.columns.astype(str)

        id_col = self.id_columns[name]
        if id_col not in df.columns:
            raise ValueError(
                f"ID column '{id_col}' not found in dataset '{name}'. "
                f"Available columns: {', '.join(df.columns)}"
            )

        self.datasets[name] = df

        if id_delimiters:
            self.id_delimiters[name] = id_delimiters

    def _split_identifier(self, identifier: str, delimiters: list[str]) -> set[str]:
        """Split an identifier using multiple delimiters.

        Args:
            identifier: String to split
            delimiters: List of delimiter strings

        Returns:
            Set of split values
        """
        if not delimiters:
            return {identifier.strip()}

        # Start with initial split on first delimiter
        result = {v.strip() for v in identifier.split(delimiters[0])}

        # Apply remaining delimiters
        for delimiter in delimiters[1:]:
            new_values: set[str] = set()
            for value in result:
                new_values.update(v.strip() for v in value.split(delimiter))
            result.update(new_values)

        # Remove any empty strings that might have been created
        result.discard("")

        return result

    def get_sets(self) -> dict[str, set[str]]:
        """Get sets of IDs from each dataset.

        Returns:
            Dictionary mapping dataset names to their sets of unique IDs

        Raises:
            ValueError: If no datasets have been loaded
        """
        if not self.datasets:
            raise ValueError("No datasets have been loaded")

        sets: dict[str, set[str]] = {}

        for name, df in self.datasets.items():
            id_col = self.id_columns[name]
            # Convert to strings and handle NaN values
            valid_ids = df[id_col].dropna().astype(str).unique()

            # Apply splitting if delimiters specified
            if name in self.id_delimiters:
                split_values = set()
                for value in valid_ids:
                    split_values.update(
                        self._split_identifier(value, self.id_delimiters[name])
                    )
                sets[name] = split_values
            else:
                sets[name] = set(valid_ids)

        return sets

    def analyze(self) -> Dict[str, Any]:
        """Perform set analysis across all datasets."""
        sets = self.get_sets()

        if not sets:
            return {}

        set_names = list(sets.keys())
        n_sets = len(set_names)

        results: Dict[str, Any] = {
            "datasets": {
                name: {"size": len(s), "sample_ids": list(sorted(s))[:5]}
                for name, s in sets.items()
            },
            "intersections": [],
            "unique": {},
        }

        # Calculate unique elements and intersections
        for i in range(n_sets):
            set_i = sets[set_names[i]]

            others = set().union(*[s for n, s in sets.items() if n != set_names[i]])
            unique = set_i - others
            results["unique"][set_names[i]] = {
                "size": len(unique),
                "sample_ids": list(sorted(unique))[:5],
            }

            for j in range(i + 1, n_sets):
                set_j = sets[set_names[j]]
                intersection = set_i & set_j

                if intersection:
                    results["intersections"].append(
                        {
                            "sets": [set_names[i], set_names[j]],
                            "size": len(intersection),
                            "sample_ids": list(sorted(intersection))[:5],
                        }
                    )

        if n_sets > 2:
            total_intersection = set.intersection(*sets.values())
            if total_intersection:
                results["intersections"].append(
                    {
                        "sets": list(sets.keys()),
                        "size": len(total_intersection),
                        "sample_ids": list(sorted(total_intersection))[:5],
                    }
                )

        return results

    def plot_venn(self, output_path: str | None = None) -> None:
        """Generate a Venn diagram visualization.

        Args:
            output_path: Optional path to save the plot. If None, displays plot.

        Raises:
            ValueError: If number of datasets is not 2 or 3.
        """
        if len(self.datasets) not in {2, 3}:
            raise ValueError("Venn diagrams are only supported for 2 or 3 sets")

        # Get sets and labels
        sets = self.get_sets()
        non_empty_sets = {k: v for k, v in sets.items() if v}

        # Convert to list of sets for venn
        data = non_empty_sets

        plt.figure(figsize=(10, 10))
        venn.venn(data)

        if output_path:
            plt.savefig(output_path)
            plt.close()

    def plot_upset(self, output_path: Optional[str] = None) -> None:
        """Generate UpSet plot visualization."""
        from upsetplot import from_contents

        sets = self.get_sets()
        data = from_contents(sets)

        plt.figure(figsize=(12, 6))
        upsetplot(data)

        if output_path:
            plt.savefig(output_path)
        else:
            plt.show()

    def generate_text_report(self, output_path: str | None = None) -> str:
        """Generate detailed text report of set analysis results.

        Args:
            output_path: Optional path to save report to file

        Returns:
            Formatted text report
        """
        results = self.analyze()
        sets = self.get_sets()

        # Build report sections
        lines = ["Set Analysis Report", "=" * 50, ""]

        # Dataset sizes
        lines.extend(["Dataset Sizes:", "-" * 15])
        for name, items in sets.items():
            lines.append(f"{name}: {len(items):,} unique identifiers")
        lines.append("")

        # Pairwise overlaps
        lines.extend(["Pairwise Overlaps:", "-" * 20])
        for i, (name1, set1) in enumerate(sets.items()):
            for name2, set2 in list(sets.items())[i + 1 :]:
                overlap = len(set1 & set2)
                pct1 = (overlap / len(set1)) * 100
                pct2 = (overlap / len(set2)) * 100
                lines.append(f"{name1} ∩ {name2}:")
                lines.append(f"  {overlap:,} identifiers")
                lines.append(f"  {pct1:.1f}% of {name1}")
                lines.append(f"  {pct2:.1f}% of {name2}")
                lines.append("")

        # Unique elements
        lines.extend(["Unique Elements:", "-" * 20])
        for name, result in results["unique"].items():
            lines.append(f"{name}: {result['size']:,} unique identifiers")
            if result["sample_ids"]:
                lines.append("Examples:")
                for id in result["sample_ids"][:5]:
                    lines.append(f"  - {id}")
            lines.append("")

        # Total intersection if more than 2 sets
        if len(sets) > 2:
            common = set.intersection(*sets.values())
            lines.extend(["Common to All Sets:", "-" * 20])
            lines.append(f"Total: {len(common):,} identifiers")
            if common:
                lines.append("Examples:")
                for id in sorted(common)[:5]:
                    lines.append(f"  - {id}")

        report = "\n".join(lines)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        return report

    def get_merged_dataframe(self, delimiter: str = "|") -> pd.DataFrame:
        """Create DataFrame of merged set data.

        Args:
            delimiter: Delimiter for source dataset names

        Returns:
            DataFrame with identifier and sources columns
        """
        sets = self.get_sets()

        # Create merged data structure
        merged_data: list[dict[str, str]] = []

        # Process each unique identifier
        all_ids = set().union(*sets.values())
        for identifier in sorted(all_ids):
            # Find which sets contain this identifier
            sources = [name for name, items in sets.items() if identifier in items]
            merged_data.append(
                {"identifier": identifier, "sources": delimiter.join(sorted(sources))}
            )

        return pd.DataFrame(merged_data)

    def export_merged_sets(
        self, output_path: str, delimiter: str = "|"
    ) -> pd.DataFrame:
        """Export merged set data to CSV file and return as DataFrame.

        Args:
            output_path: Path to save merged CSV
            delimiter: Delimiter for source dataset names

        Returns:
            DataFrame containing the merged data
        """
        df = self.get_merged_dataframe(delimiter)
        df.to_csv(output_path, index=False)
        return df

    def generate_report(self, output_prefix: str) -> None:
        """Generate a comprehensive analysis report.

        Args:
            output_prefix: Prefix for output files
        """
        # Generate plots
        self.plot_venn(f"{output_prefix}_venn.png")
        self.plot_upset(f"{output_prefix}_upset.png")

        # Generate text report
        self.generate_text_report(f"{output_prefix}_report.txt")

        # Export merged sets
        self.export_merged_sets(f"{output_prefix}_merged.csv")

    def _clean_identifier(self, identifier: Any) -> set[str]:
        """Clean and validate an identifier."""
        if pd.isna(identifier):
            return set()
        # Convert to string and strip whitespace
        return {str(identifier).strip()}
