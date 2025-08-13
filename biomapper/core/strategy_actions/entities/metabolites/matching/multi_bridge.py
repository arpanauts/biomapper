"""
METABOLITE_MULTI_BRIDGE Action.

Multi-bridge identifier resolution with fallback mechanisms for metabolite mapping.
Tries multiple bridge types in priority order with confidence scoring and fallback options.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Literal
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, validator

from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult as ActionResult,
)
from biomapper.core.exceptions import BiomapperError

logger = logging.getLogger(__name__)


class MetaboliteMultiBridgeParams(BaseModel):
    """Parameters for multi-bridge metabolite matching."""

    # Input/Output
    source_key: str = Field(..., description="Source dataset key")
    target_key: str = Field(..., description="Target dataset key")
    output_key: str = Field(..., description="Output dataset key")

    # Bridge configuration
    bridge_types: List[Literal["hmdb", "inchikey", "chebi", "kegg", "pubchem"]] = Field(
        ..., description="List of bridge types to attempt"
    )
    bridge_priority: Optional[List[str]] = Field(
        None, description="Priority order for bridges (defaults to bridge_types order)"
    )
    confidence_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "hmdb": 0.95,
            "inchikey": 0.90,
            "chebi": 0.85,
            "kegg": 0.80,
            "pubchem": 0.75,
        },
        description="Confidence weights per bridge type",
    )

    # Matching configuration
    min_confidence_threshold: float = Field(
        0.8, description="Minimum confidence for matches"
    )
    combine_strategy: Literal["highest_confidence", "consensus", "union"] = Field(
        "highest_confidence", description="How to combine matches from multiple bridges"
    )
    max_attempts_per_bridge: int = Field(
        3, description="Maximum retry attempts per bridge"
    )

    # Fallback options
    use_cts_fallback: bool = Field(
        True, description="Use CTS API for translation fallback"
    )
    use_semantic_fallback: bool = Field(
        False, description="Use semantic matching as fallback"
    )
    semantic_threshold: float = Field(
        0.8, description="Minimum confidence for semantic matches"
    )

    # Performance options
    batch_size: int = Field(1000, description="Batch size for processing")
    parallel_bridges: bool = Field(True, description="Process bridges in parallel")
    cache_results: bool = Field(True, description="Cache intermediate results")

    @validator("bridge_priority", always=True)
    def set_default_priority(cls, v, values):
        """Set default bridge priority to match bridge_types order."""
        if v is None and "bridge_types" in values:
            return values["bridge_types"][:]
        return v

    @validator("confidence_weights")
    def validate_confidence_weights(cls, v, values):
        """Ensure confidence weights exist for all bridge types."""
        if "bridge_types" in values:
            for bridge_type in values["bridge_types"]:
                if bridge_type not in v:
                    # Provide default weights
                    defaults = {
                        "hmdb": 0.95,
                        "inchikey": 0.90,
                        "chebi": 0.85,
                        "kegg": 0.80,
                        "pubchem": 0.75,
                    }
                    v[bridge_type] = defaults.get(bridge_type, 0.75)
        return v


class MetaboliteMultiBridgeResult(BaseModel):
    """Result data for multi-bridge matching."""

    total_source_compounds: int
    total_target_compounds: int
    total_matches: int
    matches_by_bridge: Dict[str, int]
    confidence_distribution: Dict[str, int] = Field(default_factory=dict)
    fallback_usage: Dict[str, int] = Field(default_factory=dict)
    execution_time_seconds: float
    bridge_performance: Dict[str, float] = Field(default_factory=dict)


class CTSTranslator:
    """Mock CTS translator for fallback - would integrate with real CTS API."""

    async def translate_batch(
        self, identifiers: List[str], from_type: str, to_type: str
    ) -> Dict[str, List[str]]:
        """Translate a batch of identifiers via CTS."""
        # Mock implementation - real version would call CTS API
        logger.info(
            f"CTS fallback: translating {len(identifiers)} {from_type} to {to_type}"
        )

        # Simulate some successful translations
        results = {}
        for identifier in identifiers[
            : min(5, len(identifiers))
        ]:  # Mock: translate first 5
            if from_type == "hmdb" and to_type == "inchikey":
                results[identifier] = [f"SIMULATED-INCHIKEY-{identifier[-7:]}-ABC-D"]
            elif from_type == "inchikey" and to_type == "hmdb":
                results[identifier] = [f"HMDB{np.random.randint(1000000, 9999999):07d}"]

        return results


class SemanticMatcher:
    """Mock semantic matcher for fallback - would integrate with real semantic matching."""

    async def find_matches(
        self, source_names: List[str], target_names: List[str], threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Find semantic matches between compound names."""
        logger.info(
            f"Semantic fallback: matching {len(source_names)} to {len(target_names)} names"
        )

        # Mock implementation - real version would use NLP/ML models
        matches = []
        for i, source_name in enumerate(
            source_names[: min(3, len(source_names))]
        ):  # Mock: match first 3
            if i < len(target_names):
                matches.append(
                    {
                        "source_id": f"semantic_source_{i}",
                        "target_id": f"semantic_target_{i}",
                        "confidence": threshold + 0.05,  # Just above threshold
                    }
                )

        return matches


@register_action("METABOLITE_MULTI_BRIDGE")
class MetaboliteMultiBridgeAction(
    TypedStrategyAction[MetaboliteMultiBridgeParams, ActionResult]
):
    """Multi-bridge identifier resolution for metabolites."""

    def __init__(self):
        super().__init__()
        self.cts_translator = CTSTranslator()
        self.semantic_matcher = SemanticMatcher()

    def get_params_model(self) -> type[MetaboliteMultiBridgeParams]:
        """Get the parameter model class."""
        return MetaboliteMultiBridgeParams

    def get_result_model(self) -> type[ActionResult]:
        """Get the result model class."""
        return ActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: MetaboliteMultiBridgeParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> ActionResult:
        """Execute multi-bridge metabolite matching."""

        start_time = time.time()
        logger.info(
            f"Starting multi-bridge matching with {len(params.bridge_types)} bridge types"
        )

        try:
            # Get datasets from context
            context_dict = (
                context if isinstance(context, dict) else context.custom_action_data
            )
            if "datasets" not in context_dict:
                context_dict = {"datasets": context_dict}

            source_df = context_dict["datasets"][params.source_key].copy()
            target_df = context_dict["datasets"][params.target_key].copy()

            logger.info(
                f"Processing {len(source_df)} source compounds against {len(target_df)} target compounds"
            )

            # Initialize results
            all_matches = []
            bridge_stats = {}
            fallback_stats = {"cts": 0, "semantic": 0}

            # Track unmatched compounds for fallback
            unmatched_source_ids = set(source_df.index)

            # Try each bridge in priority order
            for bridge_type in params.bridge_priority:
                if bridge_type not in params.bridge_types:
                    continue

                logger.info(f"Attempting bridge: {bridge_type}")

                # Attempt bridge with retries
                bridge_matches = []
                for attempt in range(params.max_attempts_per_bridge):
                    try:
                        bridge_matches = await self._match_via_bridge(
                            source_df,
                            target_df,
                            bridge_type,
                            params.confidence_weights.get(bridge_type, 0.75),
                        )
                        break  # Success
                    except Exception as e:
                        logger.warning(
                            f"Bridge {bridge_type} attempt {attempt + 1} failed: {e}"
                        )
                        if attempt == params.max_attempts_per_bridge - 1:
                            logger.error(f"Bridge {bridge_type} failed all attempts")

                # Filter by confidence and process matches
                valid_matches = [
                    match
                    for match in bridge_matches
                    if match["confidence"] >= params.min_confidence_threshold
                ]

                all_matches.extend(valid_matches)
                bridge_stats[bridge_type] = len(valid_matches)

                # Update unmatched set
                matched_source_ids = set(match["source_id"] for match in valid_matches)
                unmatched_source_ids -= matched_source_ids

                logger.info(
                    f"Bridge {bridge_type}: {len(valid_matches)} matches, {len(unmatched_source_ids)} remaining unmatched"
                )

            # CTS fallback for unmatched compounds
            if params.use_cts_fallback and unmatched_source_ids:
                logger.info(
                    f"Attempting CTS fallback for {len(unmatched_source_ids)} unmatched compounds"
                )
                cts_matches = await self._cts_fallback(
                    source_df.loc[list(unmatched_source_ids)], target_df, params
                )
                all_matches.extend(cts_matches)
                fallback_stats["cts"] = len(cts_matches)

                # Update unmatched set
                cts_matched_ids = set(match["source_id"] for match in cts_matches)
                unmatched_source_ids -= cts_matched_ids

            # Semantic fallback for remaining unmatched
            if params.use_semantic_fallback and unmatched_source_ids:
                logger.info(
                    f"Attempting semantic fallback for {len(unmatched_source_ids)} unmatched compounds"
                )
                semantic_matches = await self._semantic_fallback(
                    source_df.loc[list(unmatched_source_ids)], target_df, params
                )
                all_matches.extend(semantic_matches)
                fallback_stats["semantic"] = len(semantic_matches)

            # Combine matches based on strategy
            combined_matches = self._combine_matches(
                all_matches, params.combine_strategy
            )

            # Create output dataframe
            if combined_matches:
                matches_df = pd.DataFrame(combined_matches)
            else:
                matches_df = pd.DataFrame(
                    columns=[
                        "source_id",
                        "target_id",
                        "bridge_type",
                        "confidence",
                        "match_type",
                    ]
                )

            # Store results
            context_dict["datasets"][params.output_key] = matches_df

            # Calculate execution time and statistics
            execution_time = time.time() - start_time

            # Calculate confidence distribution
            confidence_dist = {"high": 0, "medium": 0, "low": 0}
            if len(matches_df) > 0:
                high_conf = matches_df["confidence"] >= 0.9
                med_conf = (matches_df["confidence"] >= 0.8) & (
                    matches_df["confidence"] < 0.9
                )
                low_conf = matches_df["confidence"] < 0.8

                confidence_dist = {
                    "high": int(high_conf.sum()),
                    "medium": int(med_conf.sum()),
                    "low": int(low_conf.sum()),
                }

            # Calculate bridge performance
            bridge_performance = {}
            for bridge_type in params.bridge_types:
                bridge_matches_count = bridge_stats.get(bridge_type, 0)
                # Performance as success rate (matches / attempts)
                bridge_performance[bridge_type] = min(
                    bridge_matches_count / max(len(source_df), 1), 1.0
                )

            # Build result data
            result_data = MetaboliteMultiBridgeResult(
                total_source_compounds=len(source_df),
                total_target_compounds=len(target_df),
                total_matches=len(matches_df),
                matches_by_bridge=bridge_stats,
                confidence_distribution=confidence_dist,
                fallback_usage=fallback_stats,
                execution_time_seconds=execution_time,
                bridge_performance=bridge_performance,
            )

            # Update context statistics
            if "statistics" not in context_dict:
                context_dict["statistics"] = {}
            context_dict["statistics"]["multi_bridge"] = result_data.dict()

            logger.info(
                f"Multi-bridge matching complete: {len(matches_df)} total matches in {execution_time:.2f}s"
            )

            # Get source identifiers as strings
            source_ids = []
            if "metabolite_id" in source_df.columns:
                source_ids = source_df["metabolite_id"].astype(str).tolist()[:100]
            else:
                source_ids = [str(idx) for idx in source_df.index.tolist()[:100]]

            # Get target identifiers as strings
            target_ids = []
            if len(matches_df) > 0:
                target_ids = matches_df["target_id"].astype(str).unique().tolist()[:100]

            return ActionResult(
                input_identifiers=source_ids,
                output_identifiers=target_ids,
                output_ontology_type=current_ontology_type,
                provenance=[
                    {
                        "action": "METABOLITE_MULTI_BRIDGE",
                        "bridge_types": params.bridge_types,
                        "total_matches": len(matches_df),
                        "execution_time": execution_time,
                    }
                ],
                details={"multi_bridge_result": result_data.dict()},
            )

        except Exception as e:
            logger.error(f"Multi-bridge matching failed: {e}")
            raise BiomapperError(f"Multi-bridge matching failed: {str(e)}")

    async def _match_via_bridge(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        bridge_type: str,
        confidence_weight: float,
    ) -> List[Dict[str, Any]]:
        """Match compounds via specific bridge type."""

        matches = []

        # Determine column names for this bridge type
        source_col = (
            f"{bridge_type}_id"
            if f"{bridge_type}_id" in source_df.columns
            else bridge_type
        )
        target_col = (
            f"{bridge_type}_id"
            if f"{bridge_type}_id" in target_df.columns
            else bridge_type
        )

        if source_col not in source_df.columns or target_col not in target_df.columns:
            logger.warning(
                f"Bridge {bridge_type}: missing columns {source_col} or {target_col}"
            )
            return matches

        # Extract non-null identifiers
        source_ids = source_df[source_col].dropna()
        target_ids = target_df[target_col].dropna()

        if len(source_ids) == 0 or len(target_ids) == 0:
            logger.warning(f"Bridge {bridge_type}: no valid identifiers found")
            return matches

        # Create mapping from target IDs to target records
        target_mapping = {}
        for idx, target_id in target_ids.items():
            if pd.notna(target_id):
                target_id_str = str(target_id).strip()
                if target_id_str not in target_mapping:
                    target_mapping[target_id_str] = []
                target_mapping[target_id_str].append(idx)

        # Find matches
        for source_idx, source_id in source_ids.items():
            if pd.isna(source_id):
                continue

            source_id_str = str(source_id).strip()
            if source_id_str in target_mapping:
                # Calculate confidence based on bridge type and match quality
                confidence = self._calculate_confidence(
                    source_id_str, bridge_type, confidence_weight
                )

                # Add matches for all targets with this ID
                for target_idx in target_mapping[source_id_str]:
                    matches.append(
                        {
                            "source_id": source_df.loc[source_idx, "metabolite_id"]
                            if "metabolite_id" in source_df.columns
                            else str(source_idx),
                            "target_id": target_df.loc[target_idx, "target_id"]
                            if "target_id" in target_df.columns
                            else str(target_idx),
                            "bridge_type": bridge_type,
                            "confidence": confidence,
                            "match_type": "direct_bridge",
                            "source_value": source_id_str,
                            "target_value": source_id_str,
                        }
                    )

        return matches

    def _calculate_confidence(
        self, identifier: str, bridge_type: str, base_confidence: float
    ) -> float:
        """Calculate confidence score for a match."""

        confidence = base_confidence

        # Adjust based on identifier format quality
        if bridge_type == "hmdb":
            # Higher confidence for properly formatted HMDB IDs
            if identifier.startswith("HMDB") and len(identifier) == 11:
                confidence *= 1.0
            else:
                confidence *= 0.95
        elif bridge_type == "inchikey":
            # InChIKey should have specific format
            if len(identifier.split("-")) == 3:
                parts = identifier.split("-")
                if len(parts[0]) == 14 and len(parts[1]) == 10 and len(parts[2]) == 1:
                    confidence *= 1.0
                else:
                    confidence *= 0.9
            else:
                confidence *= 0.8
        elif bridge_type == "chebi":
            # CHEBI IDs should be numeric
            clean_id = identifier.replace("CHEBI:", "")
            if clean_id.isdigit():
                confidence *= 1.0
            else:
                confidence *= 0.9
        elif bridge_type == "kegg":
            # KEGG compounds should start with C
            if identifier.startswith("C") and identifier[1:].isdigit():
                confidence *= 1.0
            else:
                confidence *= 0.95

        return min(confidence, 1.0)

    async def _cts_fallback(
        self,
        unmatched_df: pd.DataFrame,
        target_df: pd.DataFrame,
        params: MetaboliteMultiBridgeParams,
    ) -> List[Dict[str, Any]]:
        """Use CTS translation as fallback for unmatched compounds."""

        matches = []

        # Try to translate using available identifiers
        for bridge_type in params.bridge_types:
            source_col = (
                f"{bridge_type}_id"
                if f"{bridge_type}_id" in unmatched_df.columns
                else bridge_type
            )
            if source_col not in unmatched_df.columns:
                continue

            source_ids = unmatched_df[source_col].dropna().tolist()
            if not source_ids:
                continue

            # Try translating to other bridge types
            for target_bridge in params.bridge_types:
                if target_bridge == bridge_type:
                    continue

                try:
                    translations = await self.cts_translator.translate_batch(
                        source_ids, bridge_type, target_bridge
                    )

                    # Check if translated IDs match targets
                    target_col = (
                        f"{target_bridge}_id"
                        if f"{target_bridge}_id" in target_df.columns
                        else target_bridge
                    )
                    if target_col not in target_df.columns:
                        continue

                    target_ids = set(target_df[target_col].dropna().astype(str))

                    for source_id, translated_ids in translations.items():
                        for translated_id in translated_ids:
                            if translated_id in target_ids:
                                # Find matching target records
                                target_matches = target_df[
                                    target_df[target_col] == translated_id
                                ]
                                for _, target_row in target_matches.iterrows():
                                    # Find original source record
                                    source_matches = unmatched_df[
                                        unmatched_df[source_col] == source_id
                                    ]
                                    for _, source_row in source_matches.iterrows():
                                        matches.append(
                                            {
                                                "source_id": source_row.get(
                                                    "metabolite_id",
                                                    str(source_row.name),
                                                ),
                                                "target_id": target_row.get(
                                                    "target_id", str(target_row.name)
                                                ),
                                                "bridge_type": f"{bridge_type}_to_{target_bridge}",
                                                "confidence": params.confidence_weights.get(
                                                    target_bridge, 0.75
                                                )
                                                * 0.9,  # Reduced for translation
                                                "match_type": "cts_fallback",
                                                "source_value": source_id,
                                                "target_value": translated_id,
                                            }
                                        )
                except Exception as e:
                    logger.warning(
                        f"CTS translation failed for {bridge_type} to {target_bridge}: {e}"
                    )

        return matches

    async def _semantic_fallback(
        self,
        unmatched_df: pd.DataFrame,
        target_df: pd.DataFrame,
        params: MetaboliteMultiBridgeParams,
    ) -> List[Dict[str, Any]]:
        """Use semantic matching as fallback."""

        matches = []

        # Extract compound names for semantic matching
        source_names = []
        source_name_col = None
        for col in ["name", "compound_name", "metabolite_name"]:
            if col in unmatched_df.columns:
                source_name_col = col
                source_names = unmatched_df[col].dropna().tolist()
                break

        target_names = []
        target_name_col = None
        for col in ["name", "description", "compound_name"]:
            if col in target_df.columns:
                target_name_col = col
                target_names = target_df[col].dropna().tolist()
                break

        if not source_names or not target_names:
            logger.warning("Semantic fallback: no name columns found")
            return matches

        try:
            semantic_matches = await self.semantic_matcher.find_matches(
                source_names, target_names, params.semantic_threshold
            )

            # Convert semantic matches to standard format
            for semantic_match in semantic_matches:
                matches.append(
                    {
                        "source_id": semantic_match["source_id"],
                        "target_id": semantic_match["target_id"],
                        "bridge_type": "semantic",
                        "confidence": semantic_match["confidence"],
                        "match_type": "semantic_fallback",
                    }
                )

        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")

        return matches

    def _combine_matches(
        self, all_matches: List[Dict[str, Any]], strategy: str
    ) -> List[Dict[str, Any]]:
        """Combine matches from multiple bridges based on strategy."""

        if not all_matches:
            return []

        if strategy == "union":
            # Return all matches (may have duplicates)
            return all_matches

        elif strategy == "highest_confidence":
            # Group by source-target pair and keep highest confidence
            match_groups = {}
            for match in all_matches:
                key = (match["source_id"], match["target_id"])
                if (
                    key not in match_groups
                    or match["confidence"] > match_groups[key]["confidence"]
                ):
                    match_groups[key] = match
            return list(match_groups.values())

        elif strategy == "consensus":
            # Only keep matches that appear from multiple bridges
            match_counts = {}
            match_details = {}

            for match in all_matches:
                key = (match["source_id"], match["target_id"])
                if key not in match_counts:
                    match_counts[key] = 0
                    match_details[key] = match
                match_counts[key] += 1

                # Update with highest confidence version
                if match["confidence"] > match_details[key]["confidence"]:
                    match_details[key] = match

            # Only return matches that appear multiple times
            consensus_matches = []
            for key, count in match_counts.items():
                if count > 1:  # Appeared from multiple bridges
                    match = match_details[key].copy()
                    match["match_type"] = "consensus"
                    match["consensus_count"] = count
                    consensus_matches.append(match)

            return consensus_matches

        else:
            logger.warning(
                f"Unknown combine strategy: {strategy}, using highest_confidence"
            )
            return self._combine_matches(all_matches, "highest_confidence")
