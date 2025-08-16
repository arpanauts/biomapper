"""Ensembl bridge matching for proteins."""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import logging
import re
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class ProteinEnsemblBridgeParams(BaseModel):
    """Parameters for protein Ensembl bridge matching."""
    
    input_key: str = Field(..., description="Source dataset key containing proteins to match")
    reference_dataset: str = Field(..., description="Reference dataset key to match against")
    unmatched_from: List[str] = Field(default_factory=list, description="List of dataset keys containing previously matched proteins to exclude")
    
    source_ensembl_column: str = Field(default="ensembl_id", description="Column name for Ensembl IDs in source dataset")
    reference_ensembl_column: str = Field(default="ensembl_protein_id", description="Column name for Ensembl IDs in reference dataset")
    
    output_key: str = Field(..., description="Output dataset key for matched results")
    
    # Matching parameters
    strip_versions: bool = Field(default=True, description="Strip version suffixes from Ensembl IDs (e.g., .1, .2)")
    validate_format: bool = Field(default=True, description="Validate Ensembl ID format (ENSP prefix)")
    
    # Source identification columns
    source_id_column: str = Field(default="id", description="Source dataset ID column")
    reference_id_column: str = Field(default="id", description="Reference dataset ID column")

    class Config:
        extra = "allow"  # Backward compatibility


class ActionResult(BaseModel):
    """Standard action result for Ensembl bridge matching."""

    success: bool
    message: str
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


@register_action("PROTEIN_ENSEMBL_BRIDGE")
class ProteinEnsemblBridge(TypedStrategyAction[ProteinEnsemblBridgeParams, ActionResult]):
    """Bridge proteins using Ensembl protein ID matching."""

    # Ensembl protein ID pattern
    ENSEMBL_PROTEIN_PATTERN = re.compile(r'^ENSP\d{11}(\.\d+)?$')

    def get_params_model(self) -> type[ProteinEnsemblBridgeParams]:
        return ProteinEnsemblBridgeParams

    def get_result_model(self) -> type[ActionResult]:
        return ActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ProteinEnsemblBridgeParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any]
    ) -> ActionResult:
        """Execute Ensembl bridge matching."""
        try:
            # Input validation
            if "datasets" not in context:
                return ActionResult(success=False, message="No datasets in context")
            
            source_df = context["datasets"].get(params.dataset_key)
            reference_df = context["datasets"].get(params.reference_dataset)
            
            if source_df is None:
                return ActionResult(success=False, message=f"Source dataset '{params.dataset_key}' not found")
            if reference_df is None:
                return ActionResult(success=False, message=f"Reference dataset '{params.reference_dataset}' not found")
            
            logger.info(f"Starting Ensembl bridge matching: {len(source_df)} source proteins")
            
            # Get already matched protein IDs to exclude
            already_matched_ids = self._get_already_matched_ids(context, params.unmatched_from)
            
            # Filter source proteins to unmatched only
            source_unmatched = source_df[~source_df[params.source_id_column].isin(already_matched_ids)].copy()
            logger.info(f"Filtered to {len(source_unmatched)} unmatched proteins")
            
            # Perform Ensembl matching
            matches = self._perform_ensembl_matching(
                source_unmatched, reference_df, params
            )
            
            # Store results
            if matches:
                matches_df = pd.DataFrame(matches)
                context["datasets"][params.output_key] = matches_df
            else:
                # Create empty DataFrame with proper structure
                matches_df = pd.DataFrame(columns=[
                    'source_id', 'target_id', 'source_ensembl_id', 'reference_ensembl_id',
                    'match_method', 'confidence'
                ])
                context["datasets"][params.output_key] = matches_df
            
            # Track statistics
            stats = self._calculate_statistics(
                len(source_unmatched), matches, already_matched_ids
            )
            context.setdefault("statistics", {})["ensembl_bridge"] = stats
            
            match_count = len(matches)
            success_msg = f"Ensembl bridge matching completed: {match_count} matches found"
            logger.info(success_msg)
            
            return ActionResult(success=True, message=success_msg)
            
        except Exception as e:
            error_msg = f"Ensembl bridge matching failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ActionResult(success=False, message=error_msg)

    def _get_already_matched_ids(self, context: Dict, unmatched_from: List[str]) -> set:
        """Get set of already matched protein IDs to exclude."""
        already_matched = set()
        
        for dataset_key in unmatched_from:
            if dataset_key in context.get("datasets", {}):
                matched_df = context["datasets"][dataset_key]
                if not matched_df.empty and "source_id" in matched_df.columns:
                    already_matched.update(matched_df["source_id"].tolist())
        
        return already_matched

    def _normalize_ensembl_id(self, ensembl_id: str, strip_versions: bool = True) -> str:
        """Normalize Ensembl ID for matching."""
        if pd.isna(ensembl_id) or not ensembl_id:
            return ""
        
        normalized = str(ensembl_id).strip()
        
        if strip_versions and '.' in normalized:
            # Strip version suffix (e.g., ENSP00000269305.1 -> ENSP00000269305)
            normalized = normalized.split('.')[0]
        
        return normalized

    def _is_valid_ensembl_protein_id(self, ensembl_id: str) -> bool:
        """Validate Ensembl protein ID format."""
        if not ensembl_id:
            return False
        return bool(self.ENSEMBL_PROTEIN_PATTERN.match(ensembl_id))

    def _perform_ensembl_matching(
        self, source_df: pd.DataFrame, reference_df: pd.DataFrame, params: ProteinEnsemblBridgeParams
    ) -> List[Dict[str, Any]]:
        """Perform Ensembl ID matching between source and reference datasets."""
        matches = []
        
        # Filter out rows with missing Ensembl IDs
        source_valid = self._filter_valid_ensembl_ids(source_df, params.source_ensembl_column, params.validate_format)
        reference_valid = self._filter_valid_ensembl_ids(reference_df, params.reference_ensembl_column, params.validate_format)
        
        if source_valid.empty or reference_valid.empty:
            logger.info(f"No valid Ensembl IDs found. Source: {len(source_valid)}, Reference: {len(reference_valid)}")
            return matches
        
        # Create optimized lookup for reference Ensembl IDs
        reference_exact_lookup, reference_normalized_lookup = self._build_ensembl_lookup(
            reference_valid, params.reference_ensembl_column, params
        )
        logger.info(f"Built reference lookups: {len(reference_exact_lookup)} exact, {len(reference_normalized_lookup)} normalized")
        
        # Match each source protein
        for _, source_row in source_valid.iterrows():
            original_source_id = str(source_row[params.source_ensembl_column]).strip()
            if not original_source_id:
                continue
            
            best_match = self._find_best_ensembl_match(
                original_source_id, reference_exact_lookup, reference_normalized_lookup, params
            )
            
            # Add match if found
            if best_match:
                matches.append({
                    'source_id': source_row[params.source_id_column],
                    'target_id': best_match['ref_row'][params.reference_id_column],
                    'source_ensembl_id': source_row[params.source_ensembl_column],
                    'reference_ensembl_id': best_match['ref_row'][params.reference_ensembl_column],
                    'match_method': best_match['method'],
                    'confidence': best_match['confidence']
                })
        
        return matches

    def _filter_valid_ensembl_ids(self, df: pd.DataFrame, column: str, validate_format: bool) -> pd.DataFrame:
        """Filter dataframe to rows with valid Ensembl IDs."""
        valid = df.dropna(subset=[column])
        valid = valid[
            (valid[column] != "") &
            (valid[column].notna())
        ]
        
        # Apply format validation if requested
        if validate_format:
            def is_valid_id(row):
                ensembl_id = str(row[column]).strip()
                return self._is_valid_ensembl_protein_id(ensembl_id)
            
            valid = valid[valid.apply(is_valid_id, axis=1)]
        
        return valid

    def _build_ensembl_lookup(
        self, df: pd.DataFrame, column: str, params: ProteinEnsemblBridgeParams
    ) -> tuple[Dict[str, List], Dict[str, List]]:
        """Build optimized lookup dictionaries for Ensembl IDs."""
        reference_exact_lookup = {}
        reference_normalized_lookup = {}
        
        for _, ref_row in df.iterrows():
            original_id = str(ref_row[column]).strip()
            
            # Exact lookup
            if original_id not in reference_exact_lookup:
                reference_exact_lookup[original_id] = []
            reference_exact_lookup[original_id].append(ref_row)
            
            # Normalized lookup (for version matching)
            normalized_id = self._normalize_ensembl_id(original_id, params.strip_versions)
            if normalized_id and normalized_id != original_id:
                if normalized_id not in reference_normalized_lookup:
                    reference_normalized_lookup[normalized_id] = []
                reference_normalized_lookup[normalized_id].append(ref_row)
        
        return reference_exact_lookup, reference_normalized_lookup

    def _find_best_ensembl_match(
        self, source_id: str, exact_lookup: Dict[str, List], normalized_lookup: Dict[str, List], 
        params: ProteinEnsemblBridgeParams
    ) -> Optional[Dict[str, Any]]:
        """Find best match for an Ensembl ID using exact and normalized matching."""
        # Try exact match first
        if source_id in exact_lookup:
            return {
                'ref_row': exact_lookup[source_id][0],
                'confidence': 1.0,
                'method': "exact"
            }
        
        # Try normalized match (version stripping)
        if params.strip_versions:
            normalized_source = self._normalize_ensembl_id(source_id, params.strip_versions)
            
            if normalized_source in normalized_lookup:
                return {
                    'ref_row': normalized_lookup[normalized_source][0],
                    'confidence': 0.95,  # Slightly lower for version matches
                    'method': "version_stripped"
                }
        
        return None

    def _calculate_statistics(
        self, total_processed: int, matches: List[Dict], already_matched_ids: set
    ) -> Dict[str, Any]:
        """Calculate matching statistics."""
        exact_matches = sum(1 for m in matches if m['match_method'] == 'exact')
        version_matches = sum(1 for m in matches if m['match_method'] == 'version_stripped')
        
        return {
            'total_processed': total_processed,
            'exact_matches': exact_matches,
            'version_matches': version_matches,
            'total_matches': len(matches),
            'unmatched': total_processed - len(matches),
            'already_excluded': len(already_matched_ids),
            'success_rate': len(matches) / total_processed if total_processed > 0 else 0.0
        }