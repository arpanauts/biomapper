"""Nightingale NMR platform-specific matching action."""

import logging
from typing import Dict, Any, Tuple, List
from datetime import datetime
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, Field
from thefuzz import fuzz

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class NightingaleNmrMatchParams(BaseModel):
    """Parameters for Nightingale NMR matching."""

    input_key: str = Field(description="Key for source dataset in context")
    target_dataset_key: str = Field(description="Key for target dataset in context")
    source_nightingale_column: str = Field(
        description="Column with Nightingale names in source"
    )
    target_title_column: str = Field(description="Column with titles in target dataset")
    match_strategy: str = Field(
        default="fuzzy", description="Matching strategy: 'exact' or 'fuzzy'"
    )
    confidence_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Minimum confidence score for matches"
    )
    output_key: str = Field(description="Key to store matched pairs")
    unmatched_source_key: str = Field(description="Key to store unmatched source items")
    unmatched_target_key: str = Field(description="Key to store unmatched target items")


class MatchProvenance(BaseModel):
    """Provenance information for a single match."""

    match_id: str
    source: Dict[str, Any]
    target: Dict[str, Any]
    match_details: Dict[str, Any]
    timestamp: str


@register_action("NIGHTINGALE_NMR_MATCH")
class NightingaleNmrMatchAction(
    TypedStrategyAction[NightingaleNmrMatchParams, StandardActionResult]
):
    """Match metabolites between Nightingale NMR datasets."""

    def get_params_model(self) -> type[NightingaleNmrMatchParams]:
        """Return the params model class."""
        return NightingaleNmrMatchParams

    def get_result_model(self) -> type[StandardActionResult]:
        """Return the result model class."""
        return StandardActionResult

    def _normalize_nightingale_name(self, name: Any) -> str:
        """Normalize Nightingale metabolite names for matching.

        Handles common variations:
        - Case differences
        - Underscore vs space
        - Common abbreviations
        - NaN values
        - Non-string types
        """
        # Handle non-string values
        if pd.isna(name) or name is None:
            return ""

        # Convert to string if numeric
        if isinstance(name, (int, float)) and not pd.isna(name):
            logger.warning(f"Numeric value found in name field: {name}")
            name = str(name)

        # Ensure string type
        if not isinstance(name, str):
            logger.warning(f"Non-string value found: {type(name)} - {name}")
            name = str(name)

        # Handle empty strings
        if not name or name.strip() == "":
            return ""

        normalized = name.lower().strip()
        # Replace underscores with spaces
        normalized = normalized.replace("_", " ")
        # Remove common prefixes/suffixes
        normalized = normalized.replace("total ", "")
        normalized = normalized.replace(" ratio", "")

        # Common replacements
        replacements = {
            "cholesterol": "c",
            "triglycerides": "tg",
            "lipoprotein": "l",
            "density": "d",
            "high": "h",
            "low": "l",
            "very": "v",
            "intermediate": "i",
        }

        for full, abbrev in replacements.items():
            # Try both directions
            normalized = normalized.replace(full, abbrev)

        return normalized

    def _calculate_match_score(
        self, source_name: Any, target_name: Any, strategy: str
    ) -> Tuple[float, str]:
        """Calculate match score between two names.

        Returns:
            Tuple of (score, algorithm_used)
        """
        # Ensure inputs are strings
        source_str = (
            str(source_name) if not isinstance(source_name, str) else source_name
        )
        target_str = (
            str(target_name) if not isinstance(target_name, str) else target_name
        )

        if strategy == "exact":
            # Exact match after normalization
            if self._normalize_nightingale_name(
                source_str
            ) == self._normalize_nightingale_name(target_str):
                return 1.0, "exact_normalized"
            else:
                return 0.0, "exact_normalized"

        elif strategy == "fuzzy":
            # Try different fuzzy algorithms
            scores = {
                "ratio": fuzz.ratio(source_str, target_str) / 100.0,
                "partial_ratio": fuzz.partial_ratio(source_str, target_str) / 100.0,
                "token_sort_ratio": fuzz.token_sort_ratio(source_str, target_str)
                / 100.0,
                "token_set_ratio": fuzz.token_set_ratio(source_str, target_str) / 100.0,
            }

            # Also try on normalized names
            norm_source = self._normalize_nightingale_name(source_str)
            norm_target = self._normalize_nightingale_name(target_str)

            scores["normalized_ratio"] = fuzz.ratio(norm_source, norm_target) / 100.0
            scores["normalized_token_set"] = (
                fuzz.token_set_ratio(norm_source, norm_target) / 100.0
            )

            # Return best score and algorithm
            best_algo = max(scores, key=lambda x: scores[x])
            return scores[best_algo], best_algo

        else:
            raise ValueError(f"Unknown match strategy: {strategy}")

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: NightingaleNmrMatchParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute Nightingale NMR matching."""

        # Get datasets from context
        datasets = context.get_action_data("datasets", {})
        source_data = datasets.get(params.source_dataset_key, [])
        target_data = datasets.get(params.target_dataset_key, [])

        if not source_data:
            raise ValueError(
                f"Source dataset '{params.source_dataset_key}' not found in context"
            )
        if not target_data:
            raise ValueError(
                f"Target dataset '{params.target_dataset_key}' not found in context"
            )

        logger.info(
            f"Starting Nightingale NMR matching: "
            f"{len(source_data)} source items, {len(target_data)} target items"
        )

        # Track matches and unmatched items
        matches = []
        match_provenance = []
        matched_source_indices = set()
        matched_target_indices = set()

        # Track data quality issues
        source_nan_count = 0
        target_nan_count = 0
        source_numeric_count = 0
        target_numeric_count = 0
        source_empty_count = 0
        target_empty_count = 0

        # Create index for faster lookups
        target_by_name: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
        for idx, item in enumerate(target_data):
            name = item.get(params.target_title_column, "")

            # Track data quality issues in target
            if pd.isna(name) or name is None:
                target_nan_count += 1
                continue
            elif isinstance(name, (int, float)):
                target_numeric_count += 1
            elif name == "":
                target_empty_count += 1
                continue

            normalized = self._normalize_nightingale_name(name)
            if normalized:  # Only add if normalization produced a non-empty string
                if normalized not in target_by_name:
                    target_by_name[normalized] = []
                target_by_name[normalized].append((idx, item))

        # Match each source item
        for source_idx, source_item in enumerate(source_data):
            source_name = source_item.get(params.source_nightingale_column, "")

            # Skip invalid entries and track quality issues
            if pd.isna(source_name) or source_name is None:
                source_nan_count += 1
                logger.debug(f"Skipping source item with NaN name: {source_item}")
                continue
            elif isinstance(source_name, (int, float)):
                source_numeric_count += 1
                # Continue processing after converting to string
            elif source_name == "":
                source_empty_count += 1
                logger.debug(f"Skipping source item with empty name: {source_item}")
                continue

            best_match = None
            best_score = 0.0
            best_algorithm = ""
            best_target_idx = None

            # Try exact match first (fast path)
            if params.match_strategy in ["exact", "fuzzy"]:
                normalized_source = self._normalize_nightingale_name(source_name)
                if normalized_source and normalized_source in target_by_name:
                    # Found exact normalized match
                    for target_idx, target_item in target_by_name[normalized_source]:
                        if target_idx not in matched_target_indices:
                            best_match = target_item
                            best_score = 1.0
                            best_algorithm = "exact_normalized"
                            best_target_idx = target_idx
                            break

            # If no exact match and using fuzzy, try fuzzy matching
            if not best_match and params.match_strategy == "fuzzy":
                for target_idx, target_item in enumerate(target_data):
                    if target_idx in matched_target_indices:
                        continue

                    target_name = target_item.get(params.target_title_column, "")
                    # Skip invalid target names
                    if pd.isna(target_name) or target_name is None or target_name == "":
                        continue

                    score, algorithm = self._calculate_match_score(
                        source_name, target_name, params.match_strategy
                    )

                    if score > best_score:
                        best_score = score
                        best_match = target_item
                        best_algorithm = algorithm
                        best_target_idx = target_idx

            # Record match if above threshold
            if best_match and best_score >= params.confidence_threshold:
                matched_source_indices.add(source_idx)
                matched_target_indices.add(best_target_idx)

                # Create match record
                match_record = {
                    "source": source_item,
                    "target": best_match,
                    "confidence": best_score,
                    "match_algorithm": best_algorithm,
                }
                matches.append(match_record)

                # Create provenance record
                provenance = MatchProvenance(
                    match_id=str(uuid4()),
                    source={
                        "dataset": params.source_dataset_key,
                        "identifier": source_item.get(
                            "identifier", source_item.get("tabular_field_name", "")
                        ),
                        "nightingale_name": source_name,
                    },
                    target={
                        "dataset": params.target_dataset_key,
                        "identifier": best_match.get(
                            "identifier", best_match.get("field_id", "")
                        ),
                        "title": best_match.get(params.target_title_column, ""),
                    },
                    match_details={
                        "method": best_algorithm,
                        "score": best_score,
                        "strategy": params.match_strategy,
                        "tier": "nightingale_direct",
                    },
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )
                match_provenance.append(provenance.dict())

        # Collect unmatched items
        unmatched_source = [
            item
            for idx, item in enumerate(source_data)
            if idx not in matched_source_indices
        ]
        unmatched_target = [
            item
            for idx, item in enumerate(target_data)
            if idx not in matched_target_indices
        ]

        # Store results in context
        datasets[params.output_key] = matches
        datasets[params.unmatched_source_key] = unmatched_source
        datasets[params.unmatched_target_key] = unmatched_target
        context.set_action_data("datasets", datasets)

        # Store provenance - handle both dict and list formats
        provenance_data = context.get_action_data("provenance", {})
        if isinstance(provenance_data, list):
            # If provenance is a list, append our provenance records to it
            provenance_data.extend(match_provenance)
        else:
            # If provenance is a dict, store under our key
            provenance_data["nightingale_matches"] = match_provenance
        context.set_action_data("provenance", provenance_data)

        # Calculate statistics
        total_source = len(source_data)
        total_target = len(target_data)
        total_matched = len(matches)
        match_rate = total_matched / total_source if total_source > 0 else 0.0

        # Calculate confidence distribution
        confidence_scores = [m["confidence"] for m in matches]
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )

        # Log data quality summary
        if source_nan_count > 0 or source_empty_count > 0 or source_numeric_count > 0:
            logger.warning(
                f"Source data quality issues: "
                f"{source_nan_count} NaN values, "
                f"{source_empty_count} empty values, "
                f"{source_numeric_count} numeric values"
            )

        if target_nan_count > 0 or target_empty_count > 0 or target_numeric_count > 0:
            logger.warning(
                f"Target data quality issues: "
                f"{target_nan_count} NaN values, "
                f"{target_empty_count} empty values, "
                f"{target_numeric_count} numeric values"
            )

        logger.info(
            f"Nightingale NMR matching complete: "
            f"{total_matched} matches ({match_rate:.1%} of source), "
            f"avg confidence: {avg_confidence:.3f}"
        )

        # Convert all identifiers to strings for the result
        input_ids = []
        for item in source_data:
            value = item.get(params.source_nightingale_column, "")
            if pd.isna(value) or value is None:
                input_ids.append("")
            else:
                input_ids.append(str(value))

        output_ids = []
        for match in matches:
            value = match["target"].get(params.target_title_column, "")
            if pd.isna(value) or value is None:
                output_ids.append("")
            else:
                output_ids.append(str(value))

        return StandardActionResult(
            input_identifiers=input_ids,
            output_identifiers=output_ids,
            output_ontology_type="metabolite",
            provenance=match_provenance,
            details={
                "success": True,
                "message": f"Successfully matched {total_matched} metabolites between datasets",
                "total_source": total_source,
                "total_target": total_target,
                "total_matched": total_matched,
                "match_rate": match_rate,
                "avg_confidence": avg_confidence,
                "unmatched_source": len(unmatched_source),
                "unmatched_target": len(unmatched_target),
                "data_quality": {
                    "source_nan_count": source_nan_count,
                    "source_empty_count": source_empty_count,
                    "source_numeric_count": source_numeric_count,
                    "target_nan_count": target_nan_count,
                    "target_empty_count": target_empty_count,
                    "target_numeric_count": target_numeric_count,
                },
            },
        )
