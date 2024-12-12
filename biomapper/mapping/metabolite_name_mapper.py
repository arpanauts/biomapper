"""Module for mapping metabolite names to standard identifiers across databases."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Callable

import pandas as pd

from .chebi_client import ChEBIClient
from .refmet_client import RefMetClient
from .unichem_client import UniChemClient


@dataclass
class MetaboliteMapping:
    """Result of mapping a metabolite name to standard identifiers."""

    input_name: str
    refmet_id: Optional[str] = None
    refmet_name: Optional[str] = None
    chebi_id: Optional[str] = None
    chebi_name: Optional[str] = None
    pubchem_id: Optional[str] = None
    inchikey: Optional[str] = None
    mapping_source: Optional[str] = None
    confidence_score: Optional[float] = None


class MetaboliteNameMapper:
    """Maps metabolite names to standard identifiers using multiple services."""

    def __init__(self) -> None:
        """Initialize mapping clients."""
        self.refmet_client = RefMetClient()
        self.chebi_client = ChEBIClient()
        self.unichem_client = UniChemClient()

    def map_single_name(self, name: str) -> MetaboliteMapping:
        """Map a single metabolite name to standard identifiers.

        Args:
            name: Metabolite name to map

        Returns:
            MetaboliteMapping object containing mapping results
        """
        mapping = MetaboliteMapping(input_name=name)

        # Try RefMet mapping first
        try:
            refmet_result = self.refmet_client.search_by_name(name)
            if refmet_result and refmet_result.get("refmet_id"):
                mapping.refmet_id = refmet_result["refmet_id"]
                mapping.refmet_name = refmet_result.get("name")
                mapping.inchikey = refmet_result.get("inchikey")
                mapping.mapping_source = "RefMet"

                # Try UniChem if we have InChIKey
                if mapping.inchikey:
                    try:
                        unichem_result = (
                            self.unichem_client.get_compound_info_by_inchikey(
                                mapping.inchikey
                            )
                        )
                        if unichem_result:
                            if unichem_result.get("chebi_ids"):
                                mapping.chebi_id = unichem_result["chebi_ids"][0]
                            if unichem_result.get("pubchem_ids"):
                                mapping.pubchem_id = unichem_result["pubchem_ids"][0]
                        # Keep RefMet as source since UniChem just enriched the data
                    except Exception:
                        pass
        except Exception:
            pass

        # Try ChEBI if no ChEBI ID yet
        if not mapping.chebi_id:
            try:
                chebi_results = self.chebi_client.search_by_name(name)
                if chebi_results:
                    chebi_result = chebi_results[0]
                    mapping.chebi_id = chebi_result.chebi_id
                    mapping.chebi_name = chebi_result.name
                    mapping.inchikey = chebi_result.inchikey
                    if not mapping.mapping_source:  # Only set if no RefMet match
                        mapping.mapping_source = "ChEBI"
            except Exception:
                pass

        return mapping

    def map_from_file(
        self,
        input_path: str | Path,
        name_column: str,
        output_path: Optional[str | Path] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> pd.DataFrame:
        """Map metabolite names from a file to standard identifiers.

        Args:
            input_path: Path to input file (CSV/TSV)
            name_column: Name of column containing metabolite names
            output_path: Optional path to save results
            progress_callback: Optional callback function to report progress

        Returns:
            DataFrame containing original data with mapping results

        Raises:
            ValueError: If name_column is not found in input file
        """
        # Detect file type from extension
        file_ext = str(input_path).lower()
        sep = "\t" if file_ext.endswith(".tsv") else ","

        df = pd.read_csv(input_path, sep=sep)
        if name_column not in df.columns:
            raise ValueError(f"Column '{name_column}' not found in input file")

        # Map metabolite names
        mappings = self.map_from_names(
            df[name_column].tolist(), progress_callback=progress_callback
        )

        # Convert mappings to DataFrame and merge with input
        mapping_records = [
            {
                "input_name": m.input_name,
                "refmet_id": m.refmet_id,
                "refmet_name": m.refmet_name,
                "chebi_id": m.chebi_id,
                "pubchem_id": m.pubchem_id,
                "inchikey": m.inchikey,
                "mapping_source": m.mapping_source,
            }
            for m in mappings
        ]
        mapping_df = pd.DataFrame.from_records(mapping_records)

        # Merge with original data
        result_df = pd.merge(
            df, mapping_df, left_on=name_column, right_on="input_name", how="left"
        )

        # Save results if output path provided
        if output_path:
            out_ext = str(output_path).lower()
            out_sep = "\t" if out_ext.endswith(".tsv") else ","
            result_df.to_csv(output_path, sep=out_sep, index=False)

        return result_df

    def map_from_names(
        self,
        names: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[MetaboliteMapping]:
        """Map a list of metabolite names to their standardized identifiers.

        Args:
            names: List of metabolite names to map
            progress_callback: Optional callback function to report progress

        Returns:
            List of MetaboliteMapping objects containing results for all input names
        """
        results = []
        total = len(names)

        for idx, name in enumerate(names):
            mapping = self.map_single_name(name)
            results.append(mapping)

            if progress_callback:
                progress_callback(idx + 1, total)

        return results
