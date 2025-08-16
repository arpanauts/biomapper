"""Build unified Nightingale reference from matched pairs."""

import logging
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class BuildNightingaleReferenceResult(BaseModel):
    """Result model for BUILD_NIGHTINGALE_REFERENCE action."""

    success: bool = Field(description="Whether the action succeeded")
    message: str = Field(description="Status message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Action result data")


class BuildNightingaleReferenceParams(BaseModel):
    """Parameters for building Nightingale reference."""

    israeli10k_data: str = Field(description="Key for Israeli10K dataset")
    ukbb_data: str = Field(description="Key for UKBB dataset")
    matched_pairs: str = Field(
        description="Key for matched pairs from NIGHTINGALE_NMR_MATCH"
    )
    output_key: str = Field(description="Key to store reference mapping")
    export_csv: bool = Field(default=True, description="Export reference to CSV file")
    file_path: Optional[str] = Field(
        default=None, description="Path for CSV export (auto-generated if not provided)"
    )
    include_metadata: bool = Field(
        default=True, description="Include additional metadata in reference"
    )


class NightingaleReferenceEntry(BaseModel):
    """Single entry in the Nightingale reference."""

    nightingale_id: str = Field(description="Unique ID for this metabolite")
    unified_name: str = Field(description="Standardized name for the metabolite")
    israeli10k_field: str = Field(description="Israeli10K field name")
    israeli10k_display: str = Field(description="Israeli10K display name")
    ukbb_field_id: Union[str, int] = Field(description="UKBB field ID")
    ukbb_title: str = Field(description="UKBB title")
    category: Optional[str] = Field(default=None, description="Metabolite category")
    confidence: float = Field(description="Match confidence score")
    alternative_names: List[str] = Field(
        default_factory=list, description="Alternative names for this metabolite"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


@register_action("BUILD_NIGHTINGALE_REFERENCE")
class BuildNightingaleReferenceAction(
    TypedStrategyAction[
        BuildNightingaleReferenceParams, BuildNightingaleReferenceResult
    ]
):
    """Build unified Nightingale reference from matched datasets."""

    def get_params_model(self) -> type[BuildNightingaleReferenceParams]:
        """Return the params model class."""
        return BuildNightingaleReferenceParams

    def get_result_model(self) -> type[BuildNightingaleReferenceResult]:
        """Return the result model class."""
        return BuildNightingaleReferenceResult

    def _generate_unified_name(
        self, israeli10k_name: str, ukbb_title: str, confidence: float
    ) -> str:
        """Generate a unified name for the metabolite.

        Strategy:
        1. If high confidence (>0.95), prefer UKBB title (more descriptive)
        2. Otherwise, find common tokens
        3. Clean up and standardize
        """
        if confidence >= 0.95:
            # High confidence - use UKBB title as it's usually more descriptive
            return self._clean_metabolite_name(ukbb_title)

        # Find common elements
        israeli_tokens = set(israeli10k_name.lower().replace("_", " ").split())
        ukbb_tokens = set(ukbb_title.lower().split())

        common_tokens = israeli_tokens & ukbb_tokens

        if common_tokens:
            # Reconstruct from UKBB title preserving order
            unified_parts = []
            for token in ukbb_title.split():
                if token.lower() in common_tokens:
                    unified_parts.append(token)
            if unified_parts:
                return " ".join(unified_parts)

        # Fallback to UKBB title
        return self._clean_metabolite_name(ukbb_title)

    def _clean_metabolite_name(self, name: str) -> str:
        """Clean and standardize metabolite name."""
        # Remove extra whitespace
        cleaned = " ".join(name.split())

        # Convert to lowercase first, then apply standardization
        cleaned_lower = cleaned.lower()

        # Standardize common terms (case-insensitive)
        replacements = {
            "cholesterol": "cholesterol",
            "triglycerides": "triglycerides",
            "glucose": "glucose",
            "lipoprotein": "lipoprotein",
            "apolipoprotein": "apolipoprotein",
        }

        # Handle abbreviations separately (preserve case)
        abbreviations = ["HDL", "LDL", "VLDL", "IDL"]

        # Split into words and process each
        words = cleaned_lower.split()
        processed_words = []

        for word in words:
            # Check if it's an abbreviation
            upper_word = word.upper()
            if upper_word in abbreviations:
                processed_words.append(upper_word)
            else:
                # Apply replacements
                processed_word = word
                for old, new in replacements.items():
                    if old in processed_word:
                        processed_word = processed_word.replace(old, new)
                processed_words.append(processed_word)

        result = " ".join(processed_words)

        # Capitalize first letter
        if result:
            result = result[0].upper() + result[1:]

        return result

    def _extract_category(
        self, israeli10k_item: Dict[str, Any], ukbb_item: Dict[str, Any]
    ) -> Optional[str]:
        """Extract category information from items."""
        # Try UKBB category first
        if "category" in ukbb_item:
            return str(ukbb_item["category"])

        # Try to infer from Israeli10K description
        if "description" in israeli10k_item:
            desc_lower = israeli10k_item["description"].lower()
            if "cholesterol" in desc_lower:
                return "Cholesterol"
            elif "triglyceride" in desc_lower:
                return "Triglycerides"
            elif "glucose" in desc_lower or "glyc" in desc_lower:
                return "Glycolysis"
            elif "lipoprotein" in desc_lower:
                return "Lipoproteins"
            elif "amino" in desc_lower:
                return "Amino acids"
            elif "fatty" in desc_lower:
                return "Fatty acids"

        return None

    def _collect_alternative_names(
        self,
        israeli10k_item: Dict[str, Any],
        ukbb_item: Dict[str, Any],
        unified_name: str,
    ) -> List[str]:
        """Collect all alternative names for the metabolite."""
        names = set()

        # Add original names if different from unified
        israeli_name = israeli10k_item.get("nightingale_metabolomics_original_name", "")
        if israeli_name and israeli_name != unified_name:
            names.add(israeli_name)
            names.add(israeli_name.replace("_", " "))  # Add space variant

        ukbb_title = ukbb_item.get("title", "")
        if ukbb_title and ukbb_title != unified_name:
            names.add(ukbb_title)

        # Add description if available
        if "description" in israeli10k_item:
            desc = israeli10k_item["description"]
            if desc and desc != unified_name:
                names.add(desc)

        # Remove the unified name if it somehow got in
        names.discard(unified_name)

        return sorted(list(names))

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: BuildNightingaleReferenceParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> BuildNightingaleReferenceResult:
        """Build the Nightingale reference."""

        # Get required data from context
        datasets = context.get_action_data("datasets", {})
        matched_pairs = datasets.get(params.matched_pairs, [])

        if not matched_pairs:
            raise ValueError(f"No matched pairs found in '{params.matched_pairs}'")

        logger.info(
            f"Building Nightingale reference from {len(matched_pairs)} matched pairs"
        )

        # Build reference entries
        reference_entries = []
        seen_metabolites = set()  # Track to avoid duplicates

        for match in matched_pairs:
            source_item = match["source"]
            target_item = match["target"]
            confidence = match["confidence"]

            # Generate unified name
            unified_name = self._generate_unified_name(
                source_item.get("nightingale_metabolomics_original_name", ""),
                target_item.get("title", ""),
                confidence,
            )

            # Skip if we've seen this metabolite (shouldn't happen with good matching)
            if unified_name in seen_metabolites:
                logger.warning(f"Duplicate metabolite found: {unified_name}")
                continue

            seen_metabolites.add(unified_name)

            # Extract category
            category = self._extract_category(source_item, target_item)

            # Collect alternative names
            alt_names = self._collect_alternative_names(
                source_item, target_item, unified_name
            )

            # Build metadata if requested
            metadata = {}
            if params.include_metadata:
                metadata = {
                    "match_algorithm": match.get("match_algorithm", ""),
                    "match_date": datetime.utcnow().isoformat(),
                    "israeli10k_description": source_item.get("description", ""),
                    "ukbb_category": target_item.get("category", ""),
                    "platform": "Nightingale NMR",
                }

            # Create reference entry
            entry = NightingaleReferenceEntry(
                nightingale_id=str(uuid4()),
                unified_name=unified_name,
                israeli10k_field=source_item.get("tabular_field_name", ""),
                israeli10k_display=source_item.get(
                    "nightingale_metabolomics_original_name", ""
                ),
                ukbb_field_id=target_item.get("field_id", ""),
                ukbb_title=target_item.get("title", ""),
                category=category,
                confidence=confidence,
                alternative_names=alt_names,
                metadata=metadata,
            )

            reference_entries.append(entry)

        # Sort by unified name for consistency
        reference_entries.sort(key=lambda x: x.unified_name)

        # Convert to dict format for context storage
        reference_dict = [entry.dict() for entry in reference_entries]

        # Store in context
        datasets[params.output_key] = reference_dict
        context.set_action_data("datasets", datasets)

        # Export to CSV if requested
        csv_path = None
        if params.export_csv:
            csv_path = await self._export_to_csv(reference_entries, params.csv_path)
            logger.info(f"Exported reference to {csv_path}")

        # Generate summary statistics
        categories: Dict[str, int] = {}
        for entry in reference_entries:
            if entry.category:
                categories[entry.category] = categories.get(entry.category, 0) + 1

        avg_confidence = sum(e.confidence for e in reference_entries) / len(
            reference_entries
        )

        return BuildNightingaleReferenceResult(
            success=True,
            message=f"Successfully built Nightingale reference with {len(reference_entries)} metabolites",
            data={
                "total_metabolites": len(reference_entries),
                "average_confidence": avg_confidence,
                "categories": categories,
                "csv_path": str(csv_path) if csv_path else None,
                "unique_israeli10k_fields": len(
                    set(e.israeli10k_field for e in reference_entries)
                ),
                "unique_ukbb_fields": len(
                    set(e.ukbb_field_id for e in reference_entries)
                ),
            },
        )

    async def _export_to_csv(
        self, entries: List[NightingaleReferenceEntry], csv_path: Optional[str]
    ) -> Path:
        """Export reference to CSV file."""
        if not csv_path:
            # Auto-generate path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            csv_path = f"/home/ubuntu/biomapper/data/results/nightingale_reference_{timestamp}.csv"

        output_path = Path(csv_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            # Define CSV columns
            fieldnames = [
                "nightingale_id",
                "unified_name",
                "israeli10k_field",
                "israeli10k_display",
                "ukbb_field_id",
                "ukbb_title",
                "category",
                "confidence",
                "alternative_names",
                "platform",
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for entry in entries:
                row = {
                    "nightingale_id": entry.nightingale_id,
                    "unified_name": entry.unified_name,
                    "israeli10k_field": entry.israeli10k_field,
                    "israeli10k_display": entry.israeli10k_display,
                    "ukbb_field_id": entry.ukbb_field_id,
                    "ukbb_title": entry.ukbb_title,
                    "category": entry.category or "",
                    "confidence": f"{entry.confidence:.3f}",
                    "alternative_names": "|".join(entry.alternative_names),
                    "platform": entry.metadata.get("platform", "Nightingale NMR"),
                }
                writer.writerow(row)

        return output_path
