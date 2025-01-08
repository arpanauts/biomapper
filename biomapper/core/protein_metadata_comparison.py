"""Module for comparing protein metadata datasets."""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, TypedDict, TYPE_CHECKING

import pandas as pd
from tqdm import tqdm
import concurrent.futures

from ..mapping.clients.uniprot_focused_mapper import UniprotFocusedMapper


class ProteinMapping(TypedDict):
    """Type definition for protein mapping results."""

    from_id: str
    to_ids: list[str]


class MappingResult(TypedDict):
    """Type definition for individual mapping results."""

    results: list[dict[str, Any]]


@dataclass
class ComparisonResult:
    """Results from comparing two protein metadata datasets."""

    shared_proteins: set[str]  # UniProt IDs present in both sets
    unique_to_first: set[str]  # UniProt IDs only in first set
    unique_to_second: set[str]  # UniProt IDs only in second set
    mappings_first: dict[str, dict[str, list[str]]]  # Mappings for first set
    mappings_second: dict[str, dict[str, list[str]]]  # Mappings for second set


@dataclass
class ValidationResult:
    """Results from validating protein IDs."""

    valid_ids: set[str]
    invalid_records: dict[str, list[Any]]


def clean_uniprot_id(protein_id: str) -> tuple[str, bool]:
    """Clean and validate UniProt ID format.

    Handles various formats including:
    - Basic accession (P12345)
    - Accession with isoform (P12345-1)
    - Multiple IDs with delimiters (P12345_Q67890 or P12345,Q67890)
    - Entry name format (P12345|SSDH_RAT)

    Args:
        protein_id: Raw protein ID

    Returns:
        Tuple of (cleaned_id, is_valid)
    """
    # Handle empty or null values
    if pd.isna(protein_id) or not protein_id:
        return str(protein_id), False

    # Clean and standardize basic ID
    cleaned_id = str(protein_id).strip().upper()

    # Check for common delimiters and split if found
    if any(delim in cleaned_id for delim in ["_", ",", ";", "|"]):
        # Take first ID from delimited string
        cleaned_id = re.split(r"[_,;|]", cleaned_id)[0].strip()

    # Remove any isoform suffix (e.g., -1, -2)
    base_id = re.sub(r"-\d+$", "", cleaned_id)

    # Updated regex for UniProt accession format:
    # - Starts with [OPQ] followed by 5 alphanumeric characters, or
    # - Starts with [A-N,R-Z] followed by 5 numbers, or
    # - Starts with [A-Z] followed by 5 alphanumeric characters
    uniprot_pattern = r"^([OPQ][0-9A-Z]{5}|[A-N,R-Z][0-9]{5}|[A-Z][0-9A-Z]{5})$"

    is_valid = bool(re.match(uniprot_pattern, base_id))

    return base_id, is_valid


class ProteinMetadataComparison:
    """Class for comparing protein metadata datasets."""

    def __init__(self, mapper: Optional[UniprotFocusedMapper] = None) -> None:
        """Initialize the comparer with an optional mapper instance.

        Args:
            mapper: UniprotFocusedMapper instance for ID mapping. If None, creates new instance.
        """
        self.mapper = mapper or UniprotFocusedMapper()

    if TYPE_CHECKING:  # pragma: no cover
        from pandas import Series

        SeriesType = Series[Any]
    else:
        SeriesType = pd.Series

    def validate_protein_ids(
        self, protein_ids: SeriesType, source_name: str
    ) -> ValidationResult:
        """Validate a series of protein IDs.

        Args:
            protein_ids: Series containing protein IDs to validate
            source_name: Name of the data source for tracking

        Returns:
            ValidationResult containing valid and invalid IDs
        """
        valid_ids: set[str] = set()
        invalid_records: dict[str, list[Any]] = {
            "id": [],
            "reason": [],
            "original_value": [],
            "source": [],
        }

        for pid in protein_ids.dropna():
            # Handle potential multiple IDs in one field
            original_value = str(pid)
            potential_ids = re.split(r"[_,;|]", original_value)

            for single_id in potential_ids:
                cleaned_id, is_valid = clean_uniprot_id(single_id)
                if is_valid:
                    valid_ids.add(cleaned_id)
                else:
                    invalid_records["id"].append(single_id.strip())
                    invalid_records["reason"].append("Invalid UniProt format")
                    invalid_records["original_value"].append(original_value)
                    invalid_records["source"].append(source_name)

        return ValidationResult(valid_ids=valid_ids, invalid_records=invalid_records)

    def compare_datasets(
        self,
        first_proteins: set[str],
        second_proteins: set[str],
        map_categories: Optional[list[str]] = None,
    ) -> ComparisonResult:
        """Compare two sets of protein UniProt IDs and generate mappings.

        Args:
            first_proteins: Set of UniProt IDs from first dataset
            second_proteins: Set of UniProt IDs from second dataset
            map_categories: Optional list of mapping categories to include.
                          If None, maps all categories.

        Returns:
            ComparisonResult containing shared and unique proteins plus mappings

        Raises:
            ValueError: If invalid UniProt IDs or mapping categories are provided
        """
        # Validate inputs
        if not all(
            clean_uniprot_id(pid)[1] for pid in first_proteins | second_proteins
        ):
            raise ValueError("Invalid UniProt ID format detected")

        # Find overlapping and unique proteins
        shared = first_proteins & second_proteins
        unique_first = first_proteins - second_proteins
        unique_second = second_proteins - first_proteins

        # Generate mappings for both datasets
        mappings_first = self._generate_mappings(first_proteins, map_categories)
        mappings_second = self._generate_mappings(second_proteins, map_categories)

        return ComparisonResult(
            shared_proteins=shared,
            unique_to_first=unique_first,
            unique_to_second=unique_second,
            mappings_first=mappings_first,
            mappings_second=mappings_second,
        )

    def _generate_mappings(
        self, proteins: set[str], categories: Optional[list[str]] = None
    ) -> dict[str, dict[str, list[str]]]:
        """Generate mappings for a set of proteins using optimized parallel processing.

        Args:
            proteins: Set of UniProt IDs to map
            categories: Optional list of categories to map. If None, maps all.

        Returns:
            Dict mapping protein IDs to their database mappings.
        """
        # Get target databases once instead of per protein
        target_dbs: list[str] = []
        for category in categories or self.mapper.CORE_MAPPINGS.keys():
            if category in self.mapper.CORE_MAPPINGS:
                target_dbs.extend(
                    [
                        db
                        for db in self.mapper.CORE_MAPPINGS[category]
                        if db != "UniProtKB_AC-ID"
                    ]
                )
        target_dbs = list(set(target_dbs))  # Remove duplicates

        def process_protein(protein: str) -> tuple[str, dict[str, list[str]]]:
            """Process a single protein's mappings."""
            protein_mappings: dict[str, list[str]] = {}

            for target_db in target_dbs:
                try:
                    result = self.mapper.map_id(protein, target_db)
                    if result.get("results"):
                        mapped_ids: list[str] = []
                        for mapping in result["results"]:
                            to_id = mapping.get("to")
                            if isinstance(to_id, dict):
                                to_id = to_id.get("id")
                            if isinstance(to_id, str):
                                mapped_ids.append(to_id)
                        if mapped_ids:
                            protein_mappings[target_db] = mapped_ids
                except Exception as e:
                    print(
                        f"\nWarning: Failed mapping {protein} to {target_db}: {str(e)}"
                    )
                    continue

            return protein, protein_mappings

        def process_chunk(chunk: list[str]) -> dict[str, dict[str, list[str]]]:
            """Process a chunk of proteins."""
            chunk_mappings: dict[str, dict[str, list[str]]] = {}

            for protein in chunk:
                try:
                    protein_id, mappings = process_protein(protein)
                    if mappings:
                        chunk_mappings[protein_id] = mappings
                except Exception as e:
                    print(f"\nWarning: Failed processing protein {protein}: {str(e)}")
                    continue

            return chunk_mappings

        # Optimize chunk size based on total proteins
        protein_list = list(proteins)
        total_proteins = len(protein_list)
        # Smaller chunks for better reliability, adjusted based on total size
        chunk_size = min(25, max(5, total_proteins // 100))

        # Use fewer workers for smaller datasets
        max_workers = min(6, max(2, total_proteins // chunk_size // 2))

        mappings: dict[str, dict[str, list[str]]] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(0, len(protein_list), chunk_size):
                chunk = protein_list[i : i + chunk_size]
                futures.append(executor.submit(process_chunk, chunk))

            # Process results with progress bar
            with tqdm(total=len(futures), desc="Processing protein chunks") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    try:
                        chunk_result = future.result()
                        mappings.update(chunk_result)
                        pbar.update(1)
                    except Exception as e:
                        print(f"\nWarning: Chunk processing failed: {str(e)}")
                        pbar.update(1)

        return mappings

    def create_comparison_dataframe(
        self,
        comparison_result: ComparisonResult,
        invalid_first: dict[str, list[Any]],
        invalid_second: dict[str, list[Any]],
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Create detailed comparison DataFrames with mappings.

        Args:
            comparison_result: Result from protein comparison
            invalid_first: Invalid IDs from first dataset
            invalid_second: Invalid IDs from second dataset

        Returns:
            Tuple of (results_df, invalid_df)
        """
        results = []

        # Add shared proteins
        for protein in comparison_result.shared_proteins:
            mappings = comparison_result.mappings_first.get(protein, {})
            results.append(
                {
                    "uniprot_id": protein,
                    "status": "shared",
                    "source": "both",
                    "genecards": ",".join(mappings.get("GeneCards", [])),
                    "refseq": ",".join(mappings.get("RefSeq_Protein", [])),
                    "ensembl": ",".join(mappings.get("Ensembl", [])),
                    "omim": ",".join(mappings.get("MIM", [])),
                    "kegg": ",".join(mappings.get("KEGG", [])),
                    "reactome": ",".join(mappings.get("Reactome", [])),
                }
            )

        # Add unique proteins from first dataset
        for protein in comparison_result.unique_to_first:
            mappings = comparison_result.mappings_first.get(protein, {})
            results.append(
                {
                    "uniprot_id": protein,
                    "status": "unique",
                    "source": "first",
                    "genecards": ",".join(mappings.get("GeneCards", [])),
                    "refseq": ",".join(mappings.get("RefSeq_Protein", [])),
                    "ensembl": ",".join(mappings.get("Ensembl", [])),
                    "omim": ",".join(mappings.get("MIM", [])),
                    "kegg": ",".join(mappings.get("KEGG", [])),
                    "reactome": ",".join(mappings.get("Reactome", [])),
                }
            )

        # Add unique proteins from second dataset
        for protein in comparison_result.unique_to_second:
            mappings = comparison_result.mappings_second.get(protein, {})
            results.append(
                {
                    "uniprot_id": protein,
                    "status": "unique",
                    "source": "second",
                    "genecards": ",".join(mappings.get("GeneCards", [])),
                    "refseq": ",".join(mappings.get("RefSeq_Protein", [])),
                    "ensembl": ",".join(mappings.get("Ensembl", [])),
                    "omim": ",".join(mappings.get("MIM", [])),
                    "kegg": ",".join(mappings.get("KEGG", [])),
                    "reactome": ",".join(mappings.get("Reactome", [])),
                }
            )

        # Combine invalid records
        invalid_records = pd.DataFrame(
            {
                "uniprot_id": invalid_first["id"] + invalid_second["id"],
                "source": invalid_first["source"] + invalid_second["source"],
                "reason": invalid_first["reason"] + invalid_second["reason"],
                "original_value": invalid_first["original_value"]
                + invalid_second["original_value"],
            }
        )

        return pd.DataFrame(results), invalid_records

    def generate_report(
        self,
        comparison_result: ComparisonResult,
        results_df: pd.DataFrame,
        invalid_df: pd.DataFrame,
        output_dir: str,
    ) -> None:
        """Generate a text report summarizing the comparison.

        Args:
            comparison_result: Result from protein comparison
            results_df: DataFrame with valid results
            invalid_df: DataFrame with invalid IDs
            output_dir: Directory to save report
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(
            output_dir, f"protein_comparison_report_{timestamp}.txt"
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Protein Dataset Comparison Report\n")
            f.write("===============================\n\n")

            # Data validation summary
            f.write("Data Validation Summary\n")
            f.write("---------------------\n")
            first_invalid = invalid_df[invalid_df["source"] == "first"]
            second_invalid = invalid_df[invalid_df["source"] == "second"]
            f.write(f"Invalid proteins in first dataset: {len(first_invalid)}\n")
            f.write(f"Invalid proteins in second dataset: {len(second_invalid)}\n\n")

            if not first_invalid.empty:
                f.write("Example invalid IDs from first dataset (first 5):\n")
                for _, row in first_invalid.head().iterrows():
                    f.write(f"  ID: {row['uniprot_id']}\n")
                    f.write(f"  Original Value: {row['original_value']}\n")
                    f.write(f"  Reason: {row['reason']}\n")
                    f.write("\n")

            if not second_invalid.empty:
                f.write("Example invalid IDs from second dataset (first 5):\n")
                for _, row in second_invalid.head().iterrows():
                    f.write(f"  ID: {row['uniprot_id']}\n")
                    f.write(f"  Original Value: {row['original_value']}\n")
                    f.write(f"  Reason: {row['reason']}\n")
                    f.write("\n")

            # Comparison statistics
            f.write("Comparison Statistics\n")
            f.write("--------------------\n")
            f.write(
                f"Total shared proteins: {len(comparison_result.shared_proteins)}\n"
            )
            f.write(
                f"Unique to first dataset: {len(comparison_result.unique_to_first)}\n"
            )
            f.write(
                f"Unique to second dataset: {len(comparison_result.unique_to_second)}\n\n"
            )

            # Examples of shared proteins
            if comparison_result.shared_proteins:
                f.write("Example Shared Proteins (first 5)\n")
                f.write("-------------------------------\n")
                for protein in list(comparison_result.shared_proteins)[:5]:
                    f.write(f"  {protein}\n")

            f.write("\nDetailed results saved to CSV files.")

    def save_results(
        self,
        results_df: pd.DataFrame,
        invalid_df: pd.DataFrame,
        output_dir: str,
    ) -> tuple[str, str]:
        """Save comparison results to CSV files.

        Args:
            results_df: DataFrame with valid results
            invalid_df: DataFrame with invalid IDs
            output_dir: Directory to save files

        Returns:
            Tuple of (results_path, invalid_path) with paths to saved files
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        results_path = os.path.join(
            output_dir, f"protein_comparison_results_{timestamp}.csv"
        )
        invalid_path = os.path.join(output_dir, f"invalid_protein_ids_{timestamp}.csv")

        results_df.to_csv(results_path, index=False)
        invalid_df.to_csv(invalid_path, index=False)

        return results_path, invalid_path
