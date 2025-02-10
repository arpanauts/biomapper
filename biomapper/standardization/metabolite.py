"""Module for mapping metabolite names to standard identifiers across databases."""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Callable, Any, Tuple
import re
from collections import defaultdict

import pandas as pd

from ..mapping.clients.chebi_client import ChEBIClient
from ..mapping.clients.refmet_client import RefMetClient
from ..mapping.clients.unichem_client import UniChemClient

logger = logging.getLogger(__name__)


class MetaboliteClass(Enum):
    """Enum for different types of metabolite measurements."""
    SIMPLE = "simple"  # Direct metabolite measurement
    RATIO = "ratio"  # Ratio between two metabolites
    CONCENTRATION = "concentration"  # Concentration in specific matrix/tissue
    COMPOSITE = "composite"  # Composite measurement of multiple metabolites
    LIPOPROTEIN = "lipoprotein"  # Lipoprotein particle measurements


@dataclass
class Classification:
    """Result of classifying a metabolite name."""
    raw_name: str
    measurement_class: MetaboliteClass
    primary_compound: str
    secondary_compound: Optional[str] = None
    had_total_prefix: bool = False


@dataclass
class MetaboliteMapping:
    """Result of mapping a metabolite name."""
    input_name: str
    compound_class: MetaboliteClass
    primary_compound: Optional[str] = None
    secondary_compound: Optional[str] = None
    refmet_id: Optional[str] = None
    refmet_name: Optional[str] = None
    chebi_id: Optional[str] = None
    chebi_name: Optional[str] = None
    hmdb_id: Optional[str] = None
    pubchem_id: Optional[str] = None
    inchikey: Optional[str] = None
    smiles: Optional[str] = None
    confidence: float = 0.0
    mapping_source: Optional[str] = None


class MetaboliteClassifier:
    """Classifier for metabolite names."""

    def _check_ratio_patterns(self, name: str) -> tuple[str | None, str | None]:
        """Check for ratio patterns in metabolite name."""
        ratio_patterns = [
            r"ratio\s+of\s+(.+?)\s+to\s+(.+)",
            r"(.+?)\s*[/]\s*(.+?)\s+ratio",
            r"(.+?)\s+to\s+(.+?)\s+ratio",
        ]
        
        for pattern in ratio_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1).strip(), match.group(2).strip()
        
        return None, None

    def _check_concentration_patterns(self, name: str) -> tuple[str | None, str | None]:
        """Check for concentration patterns in metabolite name."""
        concentration_patterns = [
            r"concentration\s+of\s+(.+?)\s+in\s+(.+)",
            r"(.+?)\s+concentration\s+in\s+(.+)",
            r"(.+?)\s+in\s+(.+)",
        ]
        
        for pattern in concentration_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                primary = match.group(1).strip()
                secondary = match.group(2).strip()
                
                # Check if secondary part contains lipoprotein
                lipo_class, size, leftover = self._extract_lipoprotein_info(secondary)
                if lipo_class:
                    return None, None  # Let lipoprotein handler take care of it
                    
                return primary, secondary
        
        return None, None

    def _check_composite_patterns(self, name: str) -> tuple[str | None, str | None]:
        """Check for composite patterns in metabolite name."""
        composite_patterns = [
            r"(.+?)\s+(?:plus|minus|and)\s+(.+)",
            r"(.+?)\s+(?:\+|\-|\&)\s+(.+)",
        ]
        
        for pattern in composite_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                # Keep the entire expression as primary compound
                return name, None
        
        return None, None

    def _extract_lipoprotein_info(
        self, text: str
    ) -> Tuple[str | None, str | None, str]:
        """
        Extract lipoprotein info, returning (lipo_class, size_descriptor, leftover).
        E.g. "HDL cholesterol" => ("HDL", None, "cholesterol")
             "extremely large VLDL" => ("VLDL", "extremely large", "")
             "small LDL particles" => ("LDL", "small", "particles")
             "IDL concentration" => ("IDL", None, "concentration")

        If we can't find a lipoprotein, return (None, None, text) so the caller
        knows there's no lipoprotein here.
        """
        # Normalize to lower case
        text = text.strip().lower()

        # If the text is empty or too short, skip
        if not text or text in ["/", "-", "–"]:
            return (None, None, text)

        # If there's a trailing slash (like "HDL/"), treat it as incomplete => no lipoprotein
        if text.endswith("/"):
            return (None, None, text)

        # Patterns for "size"
        size_patterns = [
            r"extremely\s+(?:large|small)",
            r"very\s+(?:large|small)",
            r"(?:small|medium|large)",
        ]

        # Map of lipoprotein tokens
        lipo_map = {
            r"\bhdl\b": "HDL",
            r"\bldl\b": "LDL",
            r"\bvldl\b": "VLDL",
            r"\bidl\b": "IDL",
        }

        # 1) Extract size descriptor if present
        size = None
        for pat in size_patterns:
            match_size = re.search(pat, text)
            if match_size:
                size = match_size.group()
                # remove it from text
                text = re.sub(pat, "", text, count=1).strip()
                break

        # 2) Find which lipoprotein we have, if any
        lipo_class = None
        for pat, label in lipo_map.items():
            match_lipo = re.search(pat, text)
            if match_lipo:
                lipo_class = label
                # remove that token from text
                text = re.sub(pat, "", text, count=1).strip()
                break

        if not lipo_class:
            # No lipoprotein found
            return (None, None, text)

        # Clean up remaining text
        leftover = text.strip()

        return (lipo_class, size, leftover)

    def classify(self, name: str) -> Classification:
        """Classify a metabolite name and extract its components."""
        original_name = name
        name = re.sub(r"\s+", " ", name).strip()
        name_lower = name.lower()

        # Edge-case: blank name
        if not name_lower or name_lower.isspace():
            return Classification(
                raw_name=original_name,
                measurement_class=MetaboliteClass.SIMPLE,
                primary_compound=name_lower,
                secondary_compound=None,
                had_total_prefix=False
            )

        # First check if this might be a composite pattern
        composite_pattern = re.compile(r"\b(?:plus|minus|and|\+|\-|\&)\b", re.IGNORECASE)
        is_composite_candidate = bool(composite_pattern.search(name_lower))

        # Only remove "total" prefix if it's NOT a composite pattern
        had_total_prefix = name_lower.startswith("total ")
        if had_total_prefix and not is_composite_candidate:
            # Remove "total " from the start of the name
            name = name[6:].strip()  # remove 6 chars ("total ")
            name_lower = name.lower()

        # 1. Check ratio patterns first
        primary, secondary = self._check_ratio_patterns(name_lower)
        if primary and secondary:
            return Classification(
                raw_name=original_name,
                measurement_class=MetaboliteClass.RATIO,
                primary_compound=primary,
                secondary_compound=secondary,
                had_total_prefix=had_total_prefix
            )

        # 2. Check concentration patterns
        primary, secondary = self._check_concentration_patterns(name_lower)
        if primary and secondary:
            return Classification(
                raw_name=original_name,
                measurement_class=MetaboliteClass.CONCENTRATION,
                primary_compound=primary,
                secondary_compound=secondary,
                had_total_prefix=had_total_prefix
            )

        # 3. Check composite patterns
        primary, secondary = self._check_composite_patterns(name_lower)
        if primary:
            return Classification(
                raw_name=original_name,
                measurement_class=MetaboliteClass.COMPOSITE,
                primary_compound=primary,
                secondary_compound=secondary,
                had_total_prefix=had_total_prefix
            )

        # 4. Check lipoprotein patterns last
        lipo_class, size, leftover = self._extract_lipoprotein_info(name_lower)
        if lipo_class:
            # Clean up the leftover text:
            # 1. If there's an "in" phrase, extract the part before it
            if " in " in leftover:
                leftover = leftover.split(" in ")[0]
            
            # 2. Remove any standalone "in" words
            leftover = re.sub(r"\bin\b", "", leftover)
            
            # 3. Clean up any extra whitespace
            leftover = " ".join(leftover.split())
            
            # Combine lipoprotein class with cleaned leftover
            primary = f"{lipo_class.lower()} {leftover}".strip()
            
            return Classification(
                raw_name=original_name,
                measurement_class=MetaboliteClass.LIPOPROTEIN,
                primary_compound=primary,
                secondary_compound=None,
                had_total_prefix=had_total_prefix
            )

        # 5. If no patterns match, treat as simple metabolite
        return Classification(
            raw_name=original_name,
            measurement_class=MetaboliteClass.SIMPLE,
            primary_compound=name_lower,
            secondary_compound=None,
            had_total_prefix=had_total_prefix
        )


class MetaboliteNameMapper:
    """Maps metabolite names to standard identifiers."""

    def __init__(self) -> None:
        """Initialize the mapper."""
        self.classifier = MetaboliteClassifier()
        self.refmet_client = RefMetClient()
        self.unichem_client = UniChemClient()
        self.chebi_client = ChEBIClient()

    def map_single_name(self, name: str) -> MetaboliteMapping:
        """Map a single metabolite name to standardized identifiers."""
        classification = self.classifier.classify(name)
        primary_compound = classification.primary_compound

        # Try RefMet first
        try:
            refmet_result = self.refmet_client.search_by_name(primary_compound)
            if refmet_result:
                # Extract and format RefMet ID
                refmet_id = refmet_result.get("refmet_id")
                if refmet_id and not refmet_id.startswith("REFMET:"):
                    refmet_id = f"REFMET:{refmet_id}"

                refmet_name = refmet_result.get("name")
                inchikey = refmet_result.get("inchikey")
                pubchem_id = refmet_result.get("pubchem_id")  # Extract PubChem ID from RefMet
                chebi_id = refmet_result.get("chebi_id")
                
                if chebi_id and not chebi_id.startswith("CHEBI:"):
                    chebi_id = f"CHEBI:{chebi_id}"

                # Get additional IDs from UniChem if we have an InChIKey
                if inchikey:
                    try:
                        unichem_result = self.unichem_client.get_compound_info_by_src_id(
                            inchikey, "inchikey"
                        )
                        if unichem_result:
                            chebi_ids = unichem_result.get("chebi_ids", [])
                            if chebi_ids and not chebi_id:  # Only use if we don't have one from RefMet
                                chebi_id = f"CHEBI:{chebi_ids[0]}"

                            pubchem_ids = unichem_result.get("pubchem_ids", [])
                            if pubchem_ids and not pubchem_id:  # Only use if we don't have one from RefMet
                                pubchem_id = pubchem_ids[0]
                    except Exception as e:
                        logger.warning(f"UniChem mapping failed for '{name}': {str(e)}")

                return MetaboliteMapping(
                    input_name=name,
                    compound_class=classification.measurement_class,
                    primary_compound=primary_compound,
                    secondary_compound=classification.secondary_compound,
                    refmet_id=refmet_id,
                    refmet_name=refmet_name,
                    chebi_id=chebi_id,
                    pubchem_id=pubchem_id,
                    inchikey=inchikey,
                    mapping_source="RefMet"
                )

        except Exception as e:
            logger.warning(f"RefMet mapping failed for '{name}': {str(e)}")

        # Try ChEBI if RefMet fails
        try:
            chebi_results = self.chebi_client.search_by_name(primary_compound)
            if chebi_results:
                result = chebi_results[0]  # Take best match
                return MetaboliteMapping(
                    input_name=name,
                    compound_class=classification.measurement_class,
                    primary_compound=primary_compound,
                    secondary_compound=classification.secondary_compound,
                    chebi_id=result.chebi_id,
                    chebi_name=result.name,
                    inchikey=result.inchikey,
                    mapping_source="ChEBI"
                )
        except Exception as e:
            logger.warning(f"ChEBI mapping failed for '{name}': {str(e)}")

        # Return unmapped result if all else fails
        return MetaboliteMapping(
            input_name=name,
            compound_class=classification.measurement_class,
            primary_compound=primary_compound,
            secondary_compound=classification.secondary_compound,
        )

    def map_from_names(
        self, names: List[str], progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[MetaboliteMapping]:
        """Map a list of metabolite names to standardized identifiers.

        Args:
            names: List of metabolite names to map.
            progress_callback: Optional callback function to report progress.

        Returns:
            List of MetaboliteMapping objects.
        """
        results = []
        total = len(names)
        for i, name in enumerate(names):
            result = self.map_single_name(name)
            results.append(result)
            if progress_callback:
                progress_callback(i + 1, total)
        return results

    def map_from_file(
        self, input_file: Path, name_column: str, output_file: Path | None = None
    ) -> pd.DataFrame:
        """Map metabolite names from a file.

        Args:
            input_file: Path to input file (CSV or TSV).
            name_column: Name of column containing metabolite names.
            output_file: Optional path to save results.

        Returns:
            DataFrame with mapping results.
        """
        # Read input file
        if input_file.suffix.lower() == ".tsv":
            df = pd.read_csv(input_file, sep="\t")
        else:
            df = pd.read_csv(input_file)

        if name_column not in df.columns:
            raise ValueError(f"Column '{name_column}' not found in input file")

        # Map names
        mappings = self.map_from_names(df[name_column].tolist())

        # Convert mappings to DataFrame
        output_df = pd.DataFrame([vars(m) for m in mappings])

        # Save results if output file specified
        if output_file:
            output_df.to_csv(output_file, sep="\t", index=False)

        return output_df

    def get_mapping_summary(self, mappings: List[MetaboliteMapping]) -> dict[str, Any]:
        """Get a summary of mapping results."""
        total = len(mappings)
        mapped_any = sum(1 for m in mappings if m.refmet_id or m.chebi_id)
        mapped_refmet = sum(1 for m in mappings if m.refmet_id)
        mapped_chebi = sum(1 for m in mappings if m.chebi_id)

        by_source = defaultdict(int)
        for m in mappings:
            if m.mapping_source:
                by_source[m.mapping_source] += 1

        by_class = defaultdict(int)
        for m in mappings:
            by_class[m.compound_class.value] += 1

        return {
            "total_terms": total,
            "mapped_any": mapped_any,
            "mapped_refmet": mapped_refmet,
            "mapped_chebi": mapped_chebi,
            "by_source": dict(by_source),
            "by_class": dict(by_class),
        }

    def print_mapping_report(self, mappings: List[MetaboliteMapping]) -> None:
        """Print a report of mapping results."""
        summary = self.get_mapping_summary(mappings)
        total = summary["total_terms"]

        print("\nMapping Summary")
        print("=" * 50)
        print("\nOverall Statistics:")
        print(f"Total terms processed: {total}")
        print(f"Successfully mapped: {summary['mapped_any']} ({summary['mapped_any']/total*100:.1f}%)")
        print(f"Mapped to RefMet: {summary['mapped_refmet']} ({summary['mapped_refmet']/total*100:.1f}%)")
        print(f"Mapped to ChEBI: {summary['mapped_chebi']} ({summary['mapped_chebi']/total*100:.1f}%)")

        print("\nBy Mapping Source:")
        for source, count in summary["by_source"].items():
            print(f"  {source}: {count} ({count/total*100:.1f}%)")

        print("\nBy Compound Class:")
        for class_name, count in summary["by_class"].items():
            print(f"  {class_name}: {count} ({count/total*100:.1f}%)")
