"""Module for mapping metabolite names to standard identifiers across databases."""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Callable, Any
import re
from collections import defaultdict

import pandas as pd

from .clients.chebi_client import ChEBIClient
from .clients.refmet_client import RefMetClient
from .clients.unichem_client import UniChemClient

logger = logging.getLogger(__name__)


class MetaboliteClass(Enum):
    """Classification of metabolite measurements."""

    SIMPLE = "simple"  # e.g., "glucose"
    RATIO = "ratio"  # e.g., "X to Y ratio"
    CONCENTRATION = "concentration"  # e.g., "X in Y"
    COMPOSITE = "composite"  # e.g., "X minus Y"
    LIPOPROTEIN = "lipoprotein"  # e.g., "VLDL cholesterol"


@dataclass
class CompositeMetabolite:
    """Represents complex metabolite measurements."""

    raw_name: str
    primary_compound: str
    measurement_class: MetaboliteClass
    secondary_compound: Optional[str] = None
    particle_class: Optional[str] = None  # VLDL, LDL, HDL
    particle_size: Optional[str] = None  # large, medium, small


@dataclass
class MetaboliteMapping:
    """Result of mapping a metabolite name to standard identifiers."""

    input_name: str
    compound_class: MetaboliteClass
    primary_compound: Optional[str] = None
    secondary_compound: Optional[str] = None
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
        self.classifier = MetaboliteClassifier()

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

                # Extract other RefMet metadata
                refmet_name = refmet_result.get("name")
                inchikey = refmet_result.get("inchikey")
                pubchem_id = refmet_result.get("pubchem_id")

                # Handle ChEBI ID from RefMet
                chebi_id = refmet_result.get("chebi_id")
                if chebi_id and not chebi_id.startswith("CHEBI:"):
                    chebi_id = f"CHEBI:{chebi_id}"

                # Try UniChem for additional mappings if we have an InChIKey
                if inchikey:
                    try:
                        unichem_result = (
                            self.unichem_client.get_compound_info_by_src_id(
                                inchikey, "inchikey"
                            )
                        )
                        if unichem_result:
                            # Get ChEBI ID if not already found
                            if not chebi_id and unichem_result.get("chebi_ids"):
                                chebi = unichem_result["chebi_ids"][0]
                                chebi_id = (
                                    f"CHEBI:{chebi}"
                                    if not chebi.startswith("CHEBI:")
                                    else chebi
                                )

                            # Get PubChem ID if not already found
                            if not pubchem_id and unichem_result.get("pubchem_ids"):
                                pubchem_id = unichem_result["pubchem_ids"][0]
                    except Exception as e:
                        logger.warning(
                            f"UniChem lookup failed for {inchikey}: {str(e)}"
                        )

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
                    mapping_source="RefMet",
                )

        except Exception as e:
            logger.warning(f"RefMet mapping failed for '{name}': {str(e)}")

        # Try ChEBI as fallback
        try:
            chebi_results = self.chebi_client.search_by_name(primary_compound)
            if chebi_results and len(chebi_results) > 0:  # Check for non-empty list
                result = chebi_results[0]  # Take best match
                return MetaboliteMapping(
                    input_name=name,
                    compound_class=classification.measurement_class,
                    primary_compound=primary_compound,
                    secondary_compound=classification.secondary_compound,
                    chebi_id=result.chebi_id,
                    chebi_name=result.name,
                    inchikey=result.inchikey,
                    mapping_source="ChEBI",
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

    def get_mapping_summary(self, mappings: list[MetaboliteMapping]) -> dict[str, Any]:
        """Generate summary statistics for mapping results."""
        by_class: defaultdict[str, int] = defaultdict(int)
        by_source: defaultdict[str, int] = defaultdict(int)
        unmapped: list[str] = []
        complex_terms: list[dict[str, str]] = []

        stats: dict[str, Any] = {
            "total": len(mappings),
            "mapped_any": 0,
            "mapped_refmet": 0,
            "mapped_chebi": 0,
            "mapped_pubchem": 0,
            "mapped_inchikey": 0,
            "mapped_multiple": 0,
            "by_class": by_class,
            "by_source": by_source,
            "unmapped": unmapped,
            "complex_terms": complex_terms,
        }

        for m in mappings:
            # Count by class
            by_class_key = m.compound_class.value
            stats["by_class"][by_class_key] += 1

            # Count successful mappings
            mappings_count = sum(
                1 for x in [m.refmet_id, m.chebi_id, m.pubchem_id] if x
            )
            if mappings_count > 0:
                stats["mapped_any"] += 1
            if mappings_count > 1:
                stats["mapped_multiple"] += 1

            if m.refmet_id:
                stats["mapped_refmet"] += 1
                stats["by_source"]["RefMet"] += 1

            if m.chebi_id:
                stats["mapped_chebi"] += 1
                if not m.refmet_id:  # Only count ChEBI as source if not from RefMet
                    stats["by_source"]["ChEBI"] += 1

            if m.pubchem_id:
                stats["mapped_pubchem"] += 1

            if m.inchikey:
                stats["mapped_inchikey"] += 1

            # Track unmapped terms
            if mappings_count == 0:
                stats["unmapped"].append(m.input_name)

            # Track complex terms
            if m.compound_class != MetaboliteClass.SIMPLE:
                stats["complex_terms"].append(
                    {
                        "input": m.input_name,
                        "class": m.compound_class.value,
                        "primary": m.primary_compound if m.primary_compound else "",
                        "secondary": m.secondary_compound
                        if m.secondary_compound
                        else "",
                    }
                )

        # Calculate percentages
        total = float(stats["total"])
        if total > 0:
            stats["percent_mapped"] = round(100 * float(stats["mapped_any"]) / total, 1)
            stats["percent_refmet"] = round(
                100 * float(stats["mapped_refmet"]) / total, 1
            )
            stats["percent_chebi"] = round(
                100 * float(stats["mapped_chebi"]) / total, 1
            )
            stats["percent_pubchem"] = round(
                100 * float(stats["mapped_pubchem"]) / total, 1
            )
            stats["percent_multiple"] = round(
                100 * float(stats["mapped_multiple"]) / total, 1
            )
        else:
            stats["percent_mapped"] = 0.0
            stats["percent_refmet"] = 0.0
            stats["percent_chebi"] = 0.0
            stats["percent_pubchem"] = 0.0
            stats["percent_multiple"] = 0.0

        return stats

    def print_mapping_report(self, mappings: list[MetaboliteMapping]) -> None:
        """Print a summary report of mapping results."""
        stats = self.get_mapping_summary(mappings)

        print("\nMetabolite Mapping Report")
        print("=" * 50 + "\n")

        print("Overall Statistics:")
        print(f"Total metabolites processed: {stats['total']}")
        print(
            f"Successfully mapped: {stats['mapped_any']} ({stats['percent_mapped']}%)"
        )
        print(
            f"Mapped to RefMet: {stats['mapped_refmet']} ({stats['percent_refmet']}%)"
        )
        if stats["mapped_chebi"] > 0:
            print(
                f"Mapped to ChEBI: {stats['mapped_chebi']} ({stats['percent_chebi']}%)"
            )
        if stats["mapped_pubchem"] > 0:
            print(
                f"Mapped to PubChem: {stats['mapped_pubchem']} ({stats['percent_pubchem']}%)"
            )
        if stats["mapped_multiple"] > 0:
            print(
                f"Mapped to multiple databases: {stats['mapped_multiple']} ({stats['percent_multiple']}%)"
            )

        print("\nBy Mapping Source:")
        for source, count in stats["by_source"].items():
            percent = round(100 * count / stats["total"], 1)
            print(f"  {source}: {count} ({percent}%)")


class MetaboliteClassifier:
    """Classifier for metabolite names."""

    LIPOPROTEINS = ["HDL", "LDL", "VLDL", "IDL"]
    PARTICLE_SIZES = [
        "extremely small",
        "very small",
        "small",
        "medium",
        "large",
        "very large",
        "extremely large",
    ]

    def _check_ratio_patterns(self, name: str) -> tuple[str | None, str | None]:
        """Check for ratio patterns in metabolite name."""
        ratio_patterns = [
            re.compile(r"ratio\s+of\s+(.+?)\s+to\s+(.+)", re.IGNORECASE),
            re.compile(r"(.+?)/(.+?)\s+ratio", re.IGNORECASE),
            re.compile(r"(.+?)\s+to\s+(.+?)\s+ratio", re.IGNORECASE),
        ]
        return self._try_match_patterns(name, ratio_patterns)

    def _check_concentration_patterns(self, name: str) -> tuple[str | None, str | None]:
        """Check for concentration patterns in metabolite name."""
        concentration_patterns = [
            re.compile(r"concentration\s+of\s+(.+?)\s+in\s+(.+)", re.IGNORECASE),
            re.compile(r"(.+?)\s+in\s+(.+)", re.IGNORECASE),
        ]
        return self._try_match_patterns(name, concentration_patterns)

    def _check_composite_patterns(self, name: str) -> tuple[str | None, str | None]:
        """Check for composite patterns."""
        name_lower = name.lower()
        operators = [" plus ", " minus ", " and "]

        # Check each operator
        for op in operators:
            if op in name_lower:
                # For composite, keep the entire name as primary
                return name_lower, None

        return None, None

    def _extract_lipoprotein_info(
        self, name: str
    ) -> tuple[str | None, str | None, str]:
        """Extract lipoprotein class, size and remaining text."""
        # Convert to lowercase for processing
        lower_name = name.lower()

        # Find lipoprotein class
        lipo_class = None
        for lipo in self.LIPOPROTEINS:
            if lipo.lower() in lower_name.split():
                lipo_class = lipo
                break

        if not lipo_class:
            return None, None, name

        # Find size phrase if present
        found_size = None
        for s in sorted(self.PARTICLE_SIZES, key=len, reverse=True):
            if s in lower_name:
                found_size = s
                break

        # Build patterns to remove, starting with most specific
        patterns_to_remove = []
        if found_size:
            # Pattern for "in <size> <lipo>"
            patterns_to_remove.append(
                r"\bin\s+" + re.escape(found_size) + r"\s+" + lipo_class.lower()
            )
            # Pattern for just "<size> <lipo>"
            patterns_to_remove.append(
                re.escape(found_size) + r"\s+" + lipo_class.lower()
            )

        # Add pattern for just "in <lipo>"
        patterns_to_remove.append(r"\bin\s+" + lipo_class.lower())
        # Add pattern for just "<lipo>"
        patterns_to_remove.append(r"\b" + lipo_class.lower() + r"\b")

        # Try patterns in order (most specific to least)
        remaining = lower_name
        for pattern in patterns_to_remove:
            new_remaining = re.sub(pattern, "", remaining, flags=re.IGNORECASE)
            if new_remaining != remaining:
                remaining = new_remaining
                break

        # Clean up extra spaces
        remaining = re.sub(r"\s+", " ", remaining).strip()
        return lipo_class, found_size, remaining

    def _try_match_patterns(
        self, text: str, patterns: list[re.Pattern[str]]
    ) -> tuple[str | None, str | None]:
        """Try to match text against a list of patterns."""
        text = text.lower().strip()
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    return (groups[0].strip(), groups[1].strip() if groups[1] else None)
                elif len(groups) == 1:
                    return (groups[0].strip(), None)
        return (None, None)

    def classify(self, name: str) -> CompositeMetabolite:
        """Classify a metabolite name and extract its components."""
        original_name = name
        name = re.sub(r"\s+", " ", name).strip()
        name_lower = name.lower()

        # Check if starts with "total "
        had_total_prefix = False
        if name_lower.startswith("total "):
            had_total_prefix = True
            name_lower = name_lower[6:].strip()

        # 1. Check ratio patterns first
        ratio_match = self._check_ratio_patterns(name_lower)
        if ratio_match[0]:
            return CompositeMetabolite(
                raw_name=original_name,
                measurement_class=MetaboliteClass.RATIO,
                primary_compound=ratio_match[0],
                secondary_compound=ratio_match[1],
            )

        # 2. Check composite patterns
        composite_match = self._check_composite_patterns(name_lower)
        if composite_match[0]:
            primary_compound = composite_match[0]
            if had_total_prefix:
                primary_compound = "total " + primary_compound
            return CompositeMetabolite(
                raw_name=original_name,
                measurement_class=MetaboliteClass.COMPOSITE,
                primary_compound=primary_compound,
                secondary_compound=None,
            )

        # 3. Check concentration patterns
        conc_match = self._check_concentration_patterns(name_lower)
        if conc_match[0]:
            # Check if secondary part contains lipoprotein
            if conc_match[1]:
                lipo_class, size, _ = self._extract_lipoprotein_info(conc_match[1])
                if lipo_class is not None:  # Explicit None check
                    # If secondary contains lipoprotein, treat whole thing as lipoprotein
                    lipo_class, size, remaining = self._extract_lipoprotein_info(
                        name_lower
                    )
                    if lipo_class is not None:  # Add explicit None check
                        lipo_class_lower = lipo_class.lower()
                        primary_compound = f"{lipo_class_lower} {remaining}".strip()
                        return CompositeMetabolite(
                            raw_name=original_name,
                            measurement_class=MetaboliteClass.LIPOPROTEIN,
                            primary_compound=primary_compound,
                            particle_class=lipo_class,
                            particle_size=size,
                        )

            # Regular concentration
            return CompositeMetabolite(
                raw_name=original_name,
                measurement_class=MetaboliteClass.CONCENTRATION,
                primary_compound=conc_match[0],
                secondary_compound=conc_match[1],
            )

        # 4. Check lipoprotein patterns
        lipo_class, size, remaining = self._extract_lipoprotein_info(name_lower)
        if lipo_class is not None:  # Explicit None check
            lipo_class_lower = lipo_class.lower()
            primary_compound = f"{lipo_class_lower} {remaining}".strip()
            return CompositeMetabolite(
                raw_name=original_name,
                measurement_class=MetaboliteClass.LIPOPROTEIN,
                primary_compound=primary_compound,
                particle_class=lipo_class,
                particle_size=size,
            )

        # 5. Default to simple (don't re-add total prefix)
        return CompositeMetabolite(
            raw_name=original_name,
            measurement_class=MetaboliteClass.SIMPLE,
            primary_compound=name_lower,
        )
