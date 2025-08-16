"""Combine metabolite matches from multiple sources with provenance tracking."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4
from collections import defaultdict

from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class MappingTier(BaseModel):
    """Configuration for a single mapping tier."""

    key: str = Field(..., description="Dataset key for this tier")
    tier: str = Field(..., description="Tier name: direct, api_enriched, semantic")
    method: str = Field(
        ...,
        description="Method used: baseline_fuzzy, multi_api, llm_validated",
    )
    confidence_weight: float = Field(
        1.0, ge=0.0, le=1.0, description="Weight for confidence scoring"
    )


class CombineMetaboliteMatchesParams(BaseModel):
    """Parameters for combining metabolite matches."""

    nightingale_pairs: str = Field(
        ..., description="Key for Israeli10K-UKBB Nightingale matches"
    )
    arivale_mappings: List[MappingTier] = Field(
        ..., description="List of Arivale match tiers"
    )
    output_key: str = Field(..., description="Key for storing combined results")
    track_provenance: bool = Field(True, description="Track detailed match provenance")
    min_confidence: float = Field(0.0, description="Minimum confidence to include")


class MatchProvenance(BaseModel):
    """Provenance information for a single match."""

    match_id: str
    source_key: str
    target_key: str
    source_id: str
    target_id: str
    match_method: str
    match_tier: str
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


@register_action("COMBINE_METABOLITE_MATCHES")
class CombineMetaboliteMatchesAction(
    TypedStrategyAction[CombineMetaboliteMatchesParams, StandardActionResult]
):
    """Combine metabolite matches from multiple sources with provenance tracking."""

    def get_params_model(self) -> type[CombineMetaboliteMatchesParams]:
        """Return the params model class."""
        return CombineMetaboliteMatchesParams

    def get_result_model(self) -> type[StandardActionResult]:
        """Return the result model class."""
        return StandardActionResult

    def _extract_nightingale_name(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract Nightingale name from various data structures."""
        # Try different possible field names
        for field in ["nightingale_name", "identifier", "field_name", "display_name"]:
            if field in item and item[field]:
                return str(item[field])
        return None

    def _extract_identifier(
        self, item: Dict[str, Any], dataset_type: str
    ) -> Optional[str]:
        """Extract identifier based on dataset type."""
        if dataset_type == "israeli10k":
            return item.get("identifier") or item.get("field_name")
        elif dataset_type == "ukbb":
            return item.get("field_id") or item.get("identifier")
        elif dataset_type == "arivale":
            return item.get("biochemical_name") or item.get("identifier")
        return None

    def _build_metabolite_graph(
        self,
        nightingale_matches: List[Dict[str, Any]],
        arivale_tiers: List[Tuple[MappingTier, List[Dict[str, Any]]]],
    ) -> Dict[str, Dict[str, Any]]:
        """Build a graph of metabolite relationships.

        Returns a dict where keys are unified metabolite IDs and values contain
        all the information about matches across datasets.
        """
        metabolite_graph: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "israeli10k": None,
                "ukbb": None,
                "arivale": None,
                "nightingale_ref": None,
                "matches": [],
                "confidence_scores": [],
            }
        )

        # Process Nightingale matches (Israeli10K ↔ UKBB)
        for match in nightingale_matches:
            source = match.get("source", {})
            target = match.get("target", {})

            # Extract Nightingale name as the linking key
            nightingale_name = self._extract_nightingale_name(source)
            if not nightingale_name:
                continue

            metabolite_id = f"metabolite_{nightingale_name.lower().replace(' ', '_')}"

            # Store Israeli10K and UKBB data
            metabolite_graph[metabolite_id]["israeli10k"] = source
            metabolite_graph[metabolite_id]["ukbb"] = target
            metabolite_graph[metabolite_id]["nightingale_ref"] = nightingale_name

            # Add match info
            metabolite_graph[metabolite_id]["matches"].append(
                {
                    "method": match.get("match_algorithm", "nightingale_direct"),
                    "confidence": match.get("confidence", 1.0),
                    "tier": "nightingale_direct",
                    "source": "israeli10k",
                    "target": "ukbb",
                }
            )
            metabolite_graph[metabolite_id]["confidence_scores"].append(
                match.get("confidence", 1.0)
            )

        # Process Arivale matches through different tiers
        for tier_config, tier_matches in arivale_tiers:
            for match in tier_matches:
                source = match.get("source", {})
                target = match.get("target", {})

                # Extract Nightingale reference name from target
                nightingale_name = target.get("nightingale_name")
                if not nightingale_name:
                    continue

                metabolite_id = (
                    f"metabolite_{nightingale_name.lower().replace(' ', '_')}"
                )

                # Store or update Arivale data
                if metabolite_graph[metabolite_id]["arivale"] is None:
                    metabolite_graph[metabolite_id]["arivale"] = source
                else:
                    # Merge additional identifiers
                    for key, value in source.items():
                        if (
                            value
                            and key not in metabolite_graph[metabolite_id]["arivale"]
                        ):
                            metabolite_graph[metabolite_id]["arivale"][key] = value

                # Store Nightingale reference if not already set
                if metabolite_graph[metabolite_id]["nightingale_ref"] is None:
                    metabolite_graph[metabolite_id][
                        "nightingale_ref"
                    ] = nightingale_name

                # Calculate weighted confidence
                base_confidence = match.get("confidence", 1.0)
                weighted_confidence = base_confidence * tier_config.confidence_weight

                # Add match info
                metabolite_graph[metabolite_id]["matches"].append(
                    {
                        "method": tier_config.method,
                        "confidence": weighted_confidence,
                        "tier": tier_config.tier,
                        "source": "arivale",
                        "target": "nightingale_ref",
                    }
                )
                metabolite_graph[metabolite_id]["confidence_scores"].append(
                    weighted_confidence
                )

        return dict(metabolite_graph)

    def _calculate_combined_confidence(self, confidence_scores: List[float]) -> float:
        """Calculate combined confidence when multiple methods agree.

        Uses the formula: combined = 1 - ∏(1 - ci) for all confidence scores ci
        This gives higher confidence when multiple methods agree.
        """
        if not confidence_scores:
            return 0.0

        if len(confidence_scores) == 1:
            return confidence_scores[0]

        # Calculate combined confidence
        combined = 1.0
        for conf in confidence_scores:
            combined *= 1.0 - conf

        return 1.0 - combined

    def _create_three_way_match(
        self,
        metabolite_id: str,
        metabolite_data: Dict[str, Any],
        min_confidence: float,
    ) -> Optional[Dict[str, Any]]:
        """Create a three-way match entry if criteria are met."""
        # Count how many datasets have data
        dataset_count = sum(
            1
            for ds in ["israeli10k", "ukbb", "arivale"]
            if metabolite_data.get(ds) is not None
        )

        # For Arivale-only matches, we still want to include them if they have a Nightingale reference
        # This represents a potential match that could be linked to Israeli10K/UKBB in the future
        has_nightingale_ref = metabolite_data.get("nightingale_ref") is not None

        # Need at least 2 datasets OR Arivale with Nightingale reference for a meaningful match
        if dataset_count < 2 and not (
            dataset_count == 1
            and metabolite_data.get("arivale")
            and has_nightingale_ref
        ):
            return None

        # Calculate combined confidence
        combined_confidence = self._calculate_combined_confidence(
            metabolite_data["confidence_scores"]
        )

        # Apply confidence threshold
        if combined_confidence < min_confidence:
            return None

        # Extract unique match methods
        match_methods = list(
            set(match["method"] for match in metabolite_data["matches"])
        )

        # Build the three-way match entry
        match_entry = {
            "metabolite_id": metabolite_id,
            "match_confidence": combined_confidence,
            "match_methods": match_methods,
            "dataset_count": dataset_count,
            "is_complete": dataset_count == 3,
        }

        # Add dataset-specific data
        if metabolite_data["israeli10k"]:
            match_entry["israeli10k"] = {
                "field_name": self._extract_identifier(
                    metabolite_data["israeli10k"], "israeli10k"
                ),
                "display_name": metabolite_data["israeli10k"].get("display_name", ""),
                "nightingale_name": metabolite_data["nightingale_ref"],
            }

        if metabolite_data["ukbb"]:
            match_entry["ukbb"] = {
                "field_id": self._extract_identifier(metabolite_data["ukbb"], "ukbb"),
                "title": metabolite_data["ukbb"].get("title", ""),
            }

        if metabolite_data["arivale"]:
            match_entry["arivale"] = {
                "biochemical_name": metabolite_data["arivale"].get(
                    "biochemical_name", ""
                ),
                "hmdb": metabolite_data["arivale"].get("hmdb", ""),
                "kegg": metabolite_data["arivale"].get("kegg", ""),
            }

        return match_entry

    def _create_provenance_entries(
        self,
        metabolite_graph: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Create detailed provenance entries for all matches."""
        provenance_entries = []

        for metabolite_id, metabolite_data in metabolite_graph.items():
            for match in metabolite_data["matches"]:
                # Determine source and target datasets
                if match["source"] == "israeli10k" and match["target"] == "ukbb":
                    source_data = metabolite_data.get("israeli10k", {})
                    target_data = metabolite_data.get("ukbb", {})
                    source_dataset = "israeli10k"
                    target_dataset = "ukbb"
                elif match["source"] == "arivale":
                    source_data = metabolite_data.get("arivale", {})
                    target_data = {
                        "nightingale_name": metabolite_data.get("nightingale_ref")
                    }
                    source_dataset = "arivale"
                    target_dataset = "nightingale_reference"
                else:
                    continue

                if not source_data or not target_data:
                    continue

                # Create provenance entry
                provenance = MatchProvenance(
                    match_id=str(uuid4()),
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    source_id=self._extract_identifier(source_data, source_dataset)
                    or "",
                    target_id=self._extract_identifier(target_data, target_dataset)
                    or "",
                    match_method=match["method"],
                    match_tier=match["tier"],
                    confidence=match["confidence"],
                    metadata={
                        "metabolite_id": metabolite_id,
                    },
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

                provenance_entries.append(provenance.dict())

        return provenance_entries

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: CombineMetaboliteMatchesParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute the combine metabolite matches action."""
        logger.info("Starting COMBINE_METABOLITE_MATCHES action")

        # Get datasets from context
        datasets = context.get_action_data("datasets", {})

        # Load Nightingale matches
        nightingale_matches = datasets.get(params.nightingale_pairs, [])
        logger.info(f"Loaded {len(nightingale_matches)} Nightingale pair matches")

        # Load Arivale matches from different tiers
        arivale_tiers = []
        for tier_config in params.arivale_mappings:
            tier_data = datasets.get(tier_config.key, [])
            logger.info(
                f"Loaded {len(tier_data)} matches from Arivale tier '{tier_config.tier}'"
            )
            arivale_tiers.append((tier_config, tier_data))

        # Build metabolite graph
        metabolite_graph = self._build_metabolite_graph(
            nightingale_matches, arivale_tiers
        )
        logger.info(
            f"Built metabolite graph with {len(metabolite_graph)} unique metabolites"
        )

        # Generate three-way matches
        three_way_matches = []
        two_way_matches = []

        for metabolite_id, metabolite_data in metabolite_graph.items():
            match_entry = self._create_three_way_match(
                metabolite_id, metabolite_data, params.min_confidence
            )

            if match_entry:
                if match_entry["is_complete"]:
                    three_way_matches.append(match_entry)
                else:
                    two_way_matches.append(match_entry)

        # Create provenance entries if requested
        provenance_entries = []
        if params.track_provenance:
            provenance_entries = self._create_provenance_entries(metabolite_graph)

        # Calculate summary statistics
        matches_by_method: Dict[str, int] = defaultdict(int)
        confidence_distribution = {
            "high": 0,  # >= 0.9
            "medium": 0,  # >= 0.7
            "low": 0,  # < 0.7
        }

        all_matches = three_way_matches + two_way_matches
        for match in all_matches:
            for method in match["match_methods"]:
                matches_by_method[method] += 1

            confidence = match["match_confidence"]
            if confidence >= 0.9:
                confidence_distribution["high"] += 1
            elif confidence >= 0.7:
                confidence_distribution["medium"] += 1
            else:
                confidence_distribution["low"] += 1

        # Store results in context
        combined_results = {
            "three_way_matches": three_way_matches,
            "two_way_matches": two_way_matches,
            "summary_statistics": {
                "total_three_way_matches": len(three_way_matches),
                "total_two_way_matches": len(two_way_matches),
                "matches_by_method": dict(matches_by_method),
                "confidence_distribution": confidence_distribution,
                "total_unique_metabolites": len(metabolite_graph),
            },
            "provenance": provenance_entries if params.track_provenance else [],
        }

        datasets[params.output_key] = combined_results
        context.set_action_data("datasets", datasets)

        # Store provenance separately for easier access
        if params.track_provenance:
            provenance_data = context.get_action_data("provenance", {})
            provenance_data["combined_matches"] = provenance_entries
            context.set_action_data("provenance", provenance_data)

        logger.info(
            f"Combined metabolite matches complete: "
            f"{len(three_way_matches)} three-way matches, "
            f"{len(two_way_matches)} two-way matches"
        )

        # Create output identifiers list (metabolite IDs)
        output_identifiers = [m["metabolite_id"] for m in all_matches]

        return StandardActionResult(
            input_identifiers=current_identifiers,
            output_identifiers=output_identifiers,
            output_ontology_type="metabolite",
            provenance=provenance_entries,
            details={
                "success": True,
                "message": f"Successfully combined metabolite matches from {len(params.arivale_mappings) + 1} sources",
                "total_three_way_matches": len(three_way_matches),
                "total_two_way_matches": len(two_way_matches),
                "total_unique_metabolites": len(metabolite_graph),
                "matches_by_method": dict(matches_by_method),
                "confidence_distribution": confidence_distribution,
            },
        )
