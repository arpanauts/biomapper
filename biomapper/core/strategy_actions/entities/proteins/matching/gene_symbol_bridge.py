"""Gene symbol bridge matching for proteins."""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import logging
from fuzzywuzzy import fuzz
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

logger = logging.getLogger(__name__)


class ProteinGeneSymbolBridgeParams(BaseModel):
    """Parameters for protein gene symbol bridge matching."""
    
    input_key: str = Field(..., description="Source dataset key containing proteins to match")
    reference_dataset: str = Field(..., description="Reference dataset key to match against")
    unmatched_from: List[str] = Field(default_factory=list, description="List of dataset keys containing previously matched proteins to exclude")
    
    source_gene_column: str = Field(default="gene_symbol", description="Column name for gene symbols in source dataset")
    reference_gene_column: str = Field(default="gene_symbol", description="Column name for gene symbols in reference dataset")
    
    output_key: str = Field(..., description="Output dataset key for matched results")
    
    # Matching parameters
    min_confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum confidence score for matches")
    use_fuzzy: bool = Field(default=True, description="Enable fuzzy string matching")
    fuzzy_threshold: int = Field(default=85, ge=0, le=100, description="Minimum fuzzy match score (0-100)")
    
    # Source identification columns
    source_id_column: str = Field(default="id", description="Source dataset ID column")
    reference_id_column: str = Field(default="id", description="Reference dataset ID column")

    class Config:
        extra = "allow"  # Backward compatibility


class ActionResult(BaseModel):
    """Standard action result for gene symbol bridge matching."""

    success: bool
    message: str
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


@register_action("PROTEIN_GENE_SYMBOL_BRIDGE")
class ProteinGeneSymbolBridge(TypedStrategyAction[ProteinGeneSymbolBridgeParams, ActionResult]):
    """Bridge proteins using gene symbol matching with fuzzy matching support."""

    def get_params_model(self) -> type[ProteinGeneSymbolBridgeParams]:
        return ProteinGeneSymbolBridgeParams

    def get_result_model(self) -> type[ActionResult]:
        return ActionResult

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: ProteinGeneSymbolBridgeParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Dict[str, Any]
    ) -> ActionResult:
        """Execute gene symbol bridge matching."""
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
            
            logger.info(f"Starting gene symbol bridge matching: {len(source_df)} source proteins")
            
            # Get already matched protein IDs to exclude
            already_matched_ids = self._get_already_matched_ids(context, params.unmatched_from)
            
            # Filter source proteins to unmatched only
            source_unmatched = source_df[~source_df[params.source_id_column].isin(already_matched_ids)].copy()
            logger.info(f"Filtered to {len(source_unmatched)} unmatched proteins")
            
            # Perform gene symbol matching
            matches = self._perform_gene_symbol_matching(
                source_unmatched, reference_df, params
            )
            
            # Store results
            if matches:
                matches_df = pd.DataFrame(matches)
                context["datasets"][params.output_key] = matches_df
            else:
                # Create empty DataFrame with proper structure
                matches_df = pd.DataFrame(columns=[
                    'source_id', 'target_id', 'source_gene_symbol', 'reference_gene_symbol',
                    'match_method', 'confidence'
                ])
                context["datasets"][params.output_key] = matches_df
            
            # Track statistics
            stats = self._calculate_statistics(
                len(source_unmatched), matches, already_matched_ids
            )
            context.setdefault("statistics", {})["gene_symbol_bridge"] = stats
            
            match_count = len(matches)
            success_msg = f"Gene symbol bridge matching completed: {match_count} matches found"
            logger.info(success_msg)
            
            return ActionResult(success=True, message=success_msg)
            
        except Exception as e:
            error_msg = f"Gene symbol bridge matching failed: {str(e)}"
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

    def _perform_gene_symbol_matching(
        self, source_df: pd.DataFrame, reference_df: pd.DataFrame, params: ProteinGeneSymbolBridgeParams
    ) -> List[Dict[str, Any]]:
        """Perform gene symbol matching between source and reference datasets."""
        matches = []
        
        # Filter out rows with missing gene symbols
        source_valid = self._filter_valid_gene_symbols(source_df, params.source_gene_column)
        reference_valid = self._filter_valid_gene_symbols(reference_df, params.reference_gene_column)
        
        if source_valid.empty or reference_valid.empty:
            logger.info(f"No valid gene symbols found. Source: {len(source_valid)}, Reference: {len(reference_valid)}")
            return matches
        
        # Create optimized lookup for reference gene symbols
        reference_lookup = self._build_gene_symbol_lookup(reference_valid, params.reference_gene_column)
        logger.info(f"Built reference lookup with {len(reference_lookup)} unique gene symbols")
        
        # Match each source protein
        for _, source_row in source_valid.iterrows():
            source_gene = self._normalize_gene_symbol(source_row[params.source_gene_column])
            if not source_gene:
                continue
            
            best_match = self._find_best_gene_symbol_match(
                source_gene, reference_lookup, params
            )
            
            # Add match if meets confidence threshold
            if best_match and best_match['confidence'] >= params.min_confidence:
                matches.append({
                    'source_id': source_row[params.source_id_column],
                    'target_id': best_match['ref_row'][params.reference_id_column],
                    'source_gene_symbol': source_row[params.source_gene_column],
                    'reference_gene_symbol': best_match['ref_row'][params.reference_gene_column],
                    'match_method': best_match['method'],
                    'confidence': best_match['confidence']
                })
        
        return matches

    def _filter_valid_gene_symbols(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Filter dataframe to rows with valid gene symbols."""
        valid = df.dropna(subset=[column])
        valid = valid[
            (valid[column] != "") &
            (valid[column].notna())
        ]
        return valid

    def _normalize_gene_symbol(self, gene_symbol: Any) -> str:
        """Normalize gene symbol for matching."""
        if pd.isna(gene_symbol):
            return ""
        return str(gene_symbol).strip().upper()

    def _build_gene_symbol_lookup(self, df: pd.DataFrame, column: str) -> Dict[str, List]:
        """Build optimized lookup dictionary for gene symbols."""
        reference_lookup = {}
        for _, ref_row in df.iterrows():
            gene_symbol = self._normalize_gene_symbol(ref_row[column])
            if gene_symbol:
                if gene_symbol not in reference_lookup:
                    reference_lookup[gene_symbol] = []
                reference_lookup[gene_symbol].append(ref_row)
        return reference_lookup

    def _find_best_gene_symbol_match(
        self, source_gene: str, reference_lookup: Dict[str, List], params: ProteinGeneSymbolBridgeParams
    ) -> Optional[Dict[str, Any]]:
        """Find best match for a gene symbol using exact and fuzzy matching."""
        # Try exact match first
        if source_gene in reference_lookup:
            return {
                'ref_row': reference_lookup[source_gene][0],  # Take first exact match
                'confidence': 1.0,
                'method': "exact"
            }
        
        # Try fuzzy matching if enabled
        if params.use_fuzzy:
            best_match = None
            best_confidence = 0.0
            
            for ref_gene, ref_rows in reference_lookup.items():
                fuzzy_score = fuzz.ratio(source_gene, ref_gene)
                
                if fuzzy_score >= params.fuzzy_threshold:
                    confidence = fuzzy_score / 100.0
                    
                    if confidence > best_confidence:
                        best_match = {
                            'ref_row': ref_rows[0],  # Take first match
                            'confidence': confidence,
                            'method': "fuzzy"
                        }
                        best_confidence = confidence
            
            return best_match
        
        return None

    def _calculate_statistics(
        self, total_processed: int, matches: List[Dict], already_matched_ids: set
    ) -> Dict[str, Any]:
        """Calculate matching statistics."""
        exact_matches = sum(1 for m in matches if m['match_method'] == 'exact')
        fuzzy_matches = sum(1 for m in matches if m['match_method'] == 'fuzzy')
        
        return {
            'total_processed': total_processed,
            'exact_matches': exact_matches,
            'fuzzy_matches': fuzzy_matches,
            'total_matches': len(matches),
            'unmatched': total_processed - len(matches),
            'already_excluded': len(already_matched_ids),
            'success_rate': len(matches) / total_processed if total_processed > 0 else 0.0
        }