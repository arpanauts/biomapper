"""Multi-bridge protein matching with configurable bridge attempts.

This action implements configurable protein identifier matching using multiple 
bridge strategies in priority order, as designed from the Gemini collaboration 
investigation.

Bridge Priority Strategy:
1. UniProt exact match (90% success rate)  
2. Gene symbol fuzzy match (adds 8% more matches)
3. Ensembl ID exact match (adds 2% more matches)
"""

import logging
import re
from typing import Dict, Any, List, Optional, Literal
import pandas as pd
from pydantic import BaseModel, Field
from thefuzz import fuzz

from biomapper.core.strategy_actions.registry import register_action


# Simple ActionResult for compatibility
class ActionResult(BaseModel):
    """Simple action result for compatibility."""

    success: bool
    message: str


logger = logging.getLogger(__name__)


class BridgeAttempt(BaseModel):
    """Configuration for a single bridge attempt."""

    type: str = Field(..., description="Bridge type: uniprot, gene_symbol, ensembl")
    source_column: str = Field(..., description="Column in source dataset")
    target_column: str = Field(..., description="Column in target dataset")
    method: Literal["exact", "fuzzy"] = Field(..., description="Matching method")
    confidence_threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Minimum confidence for this bridge"
    )
    enabled: bool = Field(default=True, description="Whether to use this bridge")
    fuzzy_threshold: Optional[float] = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Fuzzy matching threshold if applicable",
    )


class ProteinMultiBridgeParams(BaseModel):
    """Parameters for PROTEIN_MULTI_BRIDGE action."""

    input_key: str = Field(..., description="Source dataset key")
    target_dataset_key: str = Field(..., description="Target dataset key")
    bridge_attempts: List[BridgeAttempt] = Field(
        ..., description="Bridge configurations in priority order"
    )
    partial_match_handling: Literal["best_match", "reject", "warn"] = Field(
        default="best_match", description="How to handle sub-threshold matches"
    )
    logging_verbosity: Literal["minimal", "normal", "detailed"] = Field(
        default="detailed", description="Logging level for scientific reproducibility"
    )
    output_key: str = Field(..., description="Where to store matched results")
    min_overall_confidence: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum confidence for any match"
    )


@register_action("PROTEIN_MULTI_BRIDGE")
class ProteinMultiBridge:
    """Multi-bridge protein matching with configurable bridge attempts.

    This action attempts multiple identifier matching strategies in priority order
    for protein datasets, implementing the enhanced bridge resolution design.
    """

    def __init__(self) -> None:
        """Initialize the action."""
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute_typed(
        self, params: ProteinMultiBridgeParams, context: Dict[str, Any]
    ) -> ActionResult:
        """Execute multi-bridge protein matching with type safety."""
        try:
            # Input validation
            if "datasets" not in context:
                return ActionResult(
                    success=False, message="No datasets found in context"
                )

            if params.source_dataset_key not in context["datasets"]:
                return ActionResult(
                    success=False,
                    message=f"Source dataset '{params.source_dataset_key}' not found in context",
                )

            if params.target_dataset_key not in context["datasets"]:
                return ActionResult(
                    success=False,
                    message=f"Target dataset '{params.target_dataset_key}' not found in context",
                )

            source_df = context["datasets"][params.source_dataset_key]
            target_df = context["datasets"][params.target_dataset_key]

            if source_df.empty:
                # Handle empty source gracefully
                empty_result = pd.DataFrame()
                context["datasets"][params.output_key] = empty_result
                return ActionResult(
                    success=True, message="Empty source dataset - no matches possible"
                )

            if target_df.empty:
                # Handle empty target gracefully
                empty_result = pd.DataFrame()
                context["datasets"][params.output_key] = empty_result
                return ActionResult(
                    success=True, message="Empty target dataset - no matches possible"
                )

            # Initialize enhanced logging and statistics
            enabled_bridges = [
                bridge for bridge in params.bridge_attempts if bridge.enabled
            ]
            disabled_bridges = [
                bridge for bridge in params.bridge_attempts if not bridge.enabled
            ]

            if params.logging_verbosity == "detailed":
                self.logger.info("=== PROTEIN MULTI-BRIDGE MATCHING INITIATED ===")
                self.logger.info(
                    f"Source dataset: {params.source_dataset_key} ({len(source_df)} proteins)"
                )
                self.logger.info(
                    f"Target dataset: {params.target_dataset_key} ({len(target_df)} proteins)"
                )
                self.logger.info(
                    f"Enabled bridges ({len(enabled_bridges)}): {[f'{b.type}({b.method}, {b.confidence_threshold:.2f})' for b in enabled_bridges]}"
                )
                if disabled_bridges:
                    self.logger.info(
                        f"Disabled bridges ({len(disabled_bridges)}): {[b.type for b in disabled_bridges]}"
                    )
                self.logger.info(
                    f"Partial match handling: {params.partial_match_handling}"
                )
                self.logger.info(
                    f"Minimum overall confidence: {params.min_overall_confidence}"
                )
            elif params.logging_verbosity == "normal":
                self.logger.info(
                    f"Multi-bridge protein matching: {len(source_df)} source × {len(target_df)} target proteins"
                )

            # Enhanced statistics tracking
            matches: List[Dict[str, Any]] = []
            match_statistics: Dict[str, Any] = {
                "total_source_proteins": len(source_df),
                "total_target_proteins": len(target_df),
                "total_matches": 0,
                "matches_by_bridge": {},
                "bridge_attempts": {},
                "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
                "processing_time_seconds": 0,
            }

            # Track bridge attempt statistics
            for bridge in enabled_bridges:
                match_statistics["bridge_attempts"][bridge.type] = {
                    "attempted": 0,
                    "successful": 0,
                    "avg_confidence": 0.0,
                }

            # Convert DataFrames to list of dicts for easier processing
            source_data = source_df.to_dict("records")
            target_data = target_df.to_dict("records")

            # Process each source protein with enhanced tracking
            import time

            start_time = time.time()

            for source_idx, source_row in enumerate(source_data):
                best_match = None
                best_confidence = 0.0
                best_bridge = None
                best_target_idx = None
                bridges_tried = []

                # Log progress for large datasets
                if (
                    params.logging_verbosity == "detailed"
                    and len(source_data) > 100
                    and source_idx % max(1, len(source_data) // 10) == 0
                ):
                    self.logger.info(
                        f"Processing protein {source_idx+1}/{len(source_data)} ({(source_idx+1)/len(source_data)*100:.1f}%)"
                    )

                # Try each bridge in priority order
                for bridge in params.bridge_attempts:
                    if not bridge.enabled:
                        continue

                    # Track attempt
                    match_statistics["bridge_attempts"][bridge.type]["attempted"] += 1

                    # Check if required columns exist
                    if bridge.source_column not in source_row:
                        if params.logging_verbosity == "detailed":
                            self.logger.warning(
                                f"Source column '{bridge.source_column}' not found, skipping bridge {bridge.type}"
                            )
                        continue

                    # Try this bridge
                    match_result = await self._try_bridge(
                        source_row,
                        target_data,
                        bridge,
                        source_idx,
                        params.logging_verbosity,
                    )

                    bridges_tried.append(
                        {
                            "type": bridge.type,
                            "confidence": match_result["confidence"]
                            if match_result
                            else 0.0,
                            "success": match_result is not None
                            and match_result["confidence"]
                            >= bridge.confidence_threshold,
                        }
                    )

                    if (
                        match_result
                        and match_result["confidence"] >= bridge.confidence_threshold
                    ):
                        # Track successful attempt
                        match_statistics["bridge_attempts"][bridge.type][
                            "successful"
                        ] += 1

                        if match_result["confidence"] > best_confidence:
                            best_match = match_result
                            best_confidence = match_result["confidence"]
                            best_bridge = bridge.type
                            best_target_idx = match_result["target_idx"]

                        # If exact match found, stop trying other bridges (priority order)
                        if match_result["confidence"] >= 0.99:
                            if params.logging_verbosity == "detailed":
                                protein_id = source_row.get(
                                    "id", f"protein_{source_idx}"
                                )
                                self.logger.debug(
                                    f"Exact match found for {protein_id} via {bridge.type}, confidence={match_result['confidence']:.3f}"
                                )
                            break

                # Enhanced logging for failed matches
                if (
                    not best_match
                    and params.logging_verbosity == "detailed"
                    and bridges_tried
                ):
                    protein_id = source_row.get("id", f"protein_{source_idx}")
                    tried_summary = ", ".join(
                        [f"{b['type']}({b['confidence']:.2f})" for b in bridges_tried]
                    )
                    self.logger.debug(
                        f"No match found for {protein_id} after trying: {tried_summary}"
                    )

                # Record match if meets overall confidence threshold
                if best_match and best_confidence >= params.min_overall_confidence:
                    # Find the bridge that was used for threshold checking
                    used_bridge = None
                    for bridge in params.bridge_attempts:
                        if bridge.enabled and bridge.type == best_bridge:
                            used_bridge = bridge
                            break

                    # Handle partial match strategies
                    include_match = True
                    warning_message = None

                    if (
                        used_bridge
                        and best_confidence < used_bridge.confidence_threshold
                    ):
                        if params.partial_match_handling == "reject":
                            include_match = False
                        elif params.partial_match_handling == "warn":
                            warning_message = (
                                f"Low confidence match: {best_confidence:.3f}"
                            )

                    if include_match:
                        match_record = {
                            "source_id": source_row.get("id", source_idx),
                            "target_id": best_match["target"]["id"]
                            if "id" in best_match["target"]
                            else best_target_idx,
                            "confidence": best_confidence,
                            "successful_bridge": best_bridge,
                            "bridge_method": best_match.get("method", "unknown"),
                        }

                        if warning_message and params.partial_match_handling == "warn":
                            match_record["warning"] = warning_message

                        matches.append(match_record)
                        match_statistics["matches_by_bridge"][best_bridge] = (
                            match_statistics["matches_by_bridge"].get(best_bridge, 0)
                            + 1
                        )

            # Create result DataFrame
            if matches:
                result_df = pd.DataFrame(matches)
            else:
                # Empty result with proper columns
                result_df = pd.DataFrame(
                    columns=[
                        "source_id",
                        "target_id",
                        "confidence",
                        "successful_bridge",
                        "bridge_method",
                    ]
                )

            # Calculate final statistics
            end_time = time.time()
            match_statistics["processing_time_seconds"] = round(
                end_time - start_time, 2
            )
            match_statistics["total_matches"] = len(matches)
            match_statistics["match_rate"] = (
                len(matches) / len(source_df)
                if source_df is not None and len(source_df) > 0
                else 0.0
            )

            # Calculate confidence distribution
            if matches:
                for match in matches:
                    conf = match["confidence"]
                    if conf >= 0.9:
                        match_statistics["confidence_distribution"]["high"] += 1
                    elif conf >= 0.7:
                        match_statistics["confidence_distribution"]["medium"] += 1
                    else:
                        match_statistics["confidence_distribution"]["low"] += 1

            # Calculate average confidence per bridge
            for bridge_type, stats in match_statistics["bridge_attempts"].items():
                if stats["successful"] > 0:
                    confidences = [
                        m["confidence"]
                        for m in matches
                        if m["successful_bridge"] == bridge_type
                    ]
                    if confidences:
                        stats["avg_confidence"] = sum(confidences) / len(confidences)

            # Store results
            context["datasets"][params.output_key] = result_df

            # Update context statistics
            if "statistics" not in context:
                context["statistics"] = {}
            context["statistics"].update(match_statistics)

            # Enhanced final logging
            if params.logging_verbosity == "detailed":
                self.logger.info("=== PROTEIN MULTI-BRIDGE MATCHING COMPLETE ===")
                self.logger.info(
                    f"Total matches: {len(matches)}/{len(source_df)} ({match_statistics['match_rate']:.1%})"
                )
                self.logger.info(
                    f"Processing time: {match_statistics['processing_time_seconds']}s"
                )

                # Bridge-specific statistics
                for bridge_type, count in match_statistics["matches_by_bridge"].items():
                    bridge_stats = match_statistics["bridge_attempts"].get(
                        bridge_type, {}
                    )
                    success_rate = bridge_stats.get("successful", 0) / max(
                        1, bridge_stats.get("attempted", 1)
                    )
                    avg_conf = bridge_stats.get("avg_confidence", 0.0)
                    self.logger.info(
                        f"{bridge_type} bridge: {count} matches, {success_rate:.1%} success rate, avg confidence {avg_conf:.3f}"
                    )

                # Confidence distribution
                conf_dist = match_statistics["confidence_distribution"]
                self.logger.info(
                    f"Confidence distribution: High(≥0.9)={conf_dist['high']}, Medium(0.7-0.9)={conf_dist['medium']}, Low(<0.7)={conf_dist['low']}"
                )

                unmatched = len(source_df) - len(matches)
                if unmatched > 0:
                    self.logger.info(
                        f"Unmatched proteins: {unmatched} ({unmatched/len(source_df):.1%})"
                    )

            elif params.logging_verbosity == "normal":
                self.logger.info(
                    f"Multi-bridge matching complete: {len(matches)}/{len(source_df)} matches ({match_statistics['match_rate']:.1%}) in {match_statistics['processing_time_seconds']}s"
                )

            success_message = f"Multi-bridge matching completed: {len(matches)} matches ({match_statistics['match_rate']:.1%}) in {match_statistics['processing_time_seconds']}s"
            return ActionResult(success=True, message=success_message)

        except Exception as e:
            error_msg = f"Multi-bridge protein matching failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ActionResult(success=False, message=error_msg)

    async def _try_bridge(
        self,
        source_row: Dict[str, Any],
        target_data: List[Dict[str, Any]],
        bridge: BridgeAttempt,
        source_idx: int,
        logging_verbosity: str = "normal",
    ) -> Optional[Dict[str, Any]]:
        """Try a single bridge attempt."""
        source_value = source_row.get(bridge.source_column)

        if pd.isna(source_value) or source_value == "" or source_value == "MISSING":
            return None

        best_match = None
        best_confidence = 0.0
        best_target_idx = None

        for target_idx, target_row in enumerate(target_data):
            target_value = target_row.get(bridge.target_column)

            if pd.isna(target_value) or target_value == "":
                continue

            confidence = self._calculate_match_confidence(
                source_value, target_value, bridge.method, bridge.fuzzy_threshold or 0.8
            )

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = target_row
                best_target_idx = target_idx

        if best_match and best_confidence > 0:
            return {
                "target": best_match,
                "target_idx": best_target_idx,
                "confidence": best_confidence,
                "method": bridge.method,
            }

        return None

    def _calculate_match_confidence(
        self,
        source_value: str,
        target_value: str,
        method: str,
        fuzzy_threshold: float = 0.8,
    ) -> float:
        """Calculate match confidence between two values using enhanced algorithms."""
        if method == "exact":
            # Enhanced exact matching with normalization
            source_norm = self._normalize_uniprot_id(str(source_value))
            target_norm = self._normalize_uniprot_id(str(target_value))

            if source_norm == target_norm:
                return 1.0
            else:
                return 0.0

        elif method == "fuzzy":
            # Enhanced fuzzy matching for gene symbols and protein names
            source_str = str(source_value).strip().upper()
            target_str = str(target_value).strip().upper()

            # Exact match gets perfect score
            if source_str == target_str:
                return 1.0

            # Handle empty strings
            if not source_str or not target_str:
                return 0.0

            # Performance-optimized fuzzy matching
            algorithms_scores = []

            # Quick check: if strings are very different in length, use faster algorithms only
            length_diff = abs(len(source_str) - len(target_str))
            use_fast_mode = length_diff > min(len(source_str), len(target_str)) * 0.5

            if use_fast_mode:
                # Fast mode: use only the most efficient algorithms
                simple_score = fuzz.ratio(source_str, target_str) / 100.0
                algorithms_scores.append(("simple", simple_score))

                partial_score = fuzz.partial_ratio(source_str, target_str) / 100.0
                algorithms_scores.append(("partial", partial_score))
            else:
                # Full mode: use all algorithms for better accuracy
                # 1. Token sort ratio - handles word order differences (e.g., "NRP1" vs "Neuropilin 1")
                token_sort_score = fuzz.token_sort_ratio(source_str, target_str) / 100.0
                algorithms_scores.append(("token_sort", token_sort_score))

                # 2. Partial ratio - handles partial matches (e.g., "TP53" in "TP53_VARIANT")
                partial_score = fuzz.partial_ratio(source_str, target_str) / 100.0
                algorithms_scores.append(("partial", partial_score))

                # 3. Token set ratio - handles common gene name variations
                token_set_score = fuzz.token_set_ratio(source_str, target_str) / 100.0
                algorithms_scores.append(("token_set", token_set_score))

                # 4. Simple ratio - basic Levenshtein distance
                simple_score = fuzz.ratio(source_str, target_str) / 100.0
                algorithms_scores.append(("simple", simple_score))

            # Always check protein-specific matching (it's fast and important)
            protein_specific_score = self._protein_specific_similarity(
                source_str, target_str
            )
            if protein_specific_score > 0:
                algorithms_scores.append(("protein_specific", protein_specific_score))

            # Return the best score from all algorithms
            best_score = (
                max(score for _, score in algorithms_scores)
                if algorithms_scores
                else 0.0
            )
            return best_score

        return 0.0

    def _protein_specific_similarity(self, source: str, target: str) -> float:
        """Calculate protein-specific similarity for gene names and symbols."""
        # Common gene name transformations and aliases
        transformations = [
            # Remove common suffixes/prefixes
            (r"_HUMAN$", ""),
            (r"^HUMAN_", ""),
            (r"_MOUSE$", ""),
            (r"^MOUSE_", ""),
            (r"_RAT$", ""),
            (r"^RAT_", ""),
            # Handle common gene variants
            (r"_VARIANT$", ""),
            (r"_ALT$", ""),
            (r"_V\d+$", ""),  # Version numbers
            (r"-\d+$", ""),  # Isoform numbers
            # Handle protein family naming
            (r"PROTEIN$", ""),
            (r"^PROTEIN_", ""),
        ]

        # Apply transformations to both strings
        source_clean = source
        target_clean = target

        for pattern, replacement in transformations:
            source_clean = re.sub(pattern, replacement, source_clean)
            target_clean = re.sub(pattern, replacement, target_clean)

        # If transformations made them identical, high confidence
        if source_clean == target_clean and source_clean:
            return 0.95

        # Check for common gene symbol patterns
        # E.g., "BRCA1" vs "Breast cancer gene 1"
        if len(source_clean) <= 6 and len(target_clean) > 10:
            # Source might be an abbreviation of target
            if source_clean in target_clean:
                return 0.85

        if len(target_clean) <= 6 and len(source_clean) > 10:
            # Target might be an abbreviation of source
            if target_clean in source_clean:
                return 0.85

        return 0.0

    def _normalize_uniprot_id(self, uniprot_str: str) -> str:
        """Normalize UniProt ID by removing common prefixes and isoform suffixes."""
        if pd.isna(uniprot_str) or uniprot_str == "":
            return ""

        # Remove common prefixes
        normalized = str(uniprot_str).strip()
        normalized = re.sub(r"^(UniProtKB:|sp\||tr\|)", "", normalized)

        # Remove isoform suffixes (-1, -2, etc)
        normalized = re.sub(r"-\d+$", "", normalized)

        # Extract just the accession part if pipe-separated format
        if "|" in normalized:
            parts = normalized.split("|")
            # Usually accession is the second part in sp|P12345|GENE_NAME format
            if len(parts) >= 2:
                normalized = parts[1]
            else:
                normalized = parts[0]

        return normalized.strip().upper()
