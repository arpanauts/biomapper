"""CTS API-enriched matching action for metabolites."""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction, StandardActionResult
from biomapper.core.strategy_actions.registry import register_action
from biomapper.mapping.clients.cts_client import CTSClient
from thefuzz import fuzz  # type: ignore

logger = logging.getLogger(__name__)


class CtsEnrichedMatchParams(BaseModel):
    """Parameters for CTS-enriched matching."""
    unmatched_dataset_key: str = Field(
        description="Key for unmatched items from baseline"
    )
    target_dataset_key: str = Field(
        description="Key for target dataset (e.g., Nightingale reference)"
    )
    identifier_columns: List[str] = Field(
        description="Columns with identifiers to convert (e.g., ['HMDB', 'KEGG', 'PUBCHEM'])"
    )
    target_column: str = Field(
        default="unified_name",
        description="Column in target dataset to match against"
    )
    cts_timeout: int = Field(
        default=30,
        description="Timeout for CTS API calls in seconds"
    )
    batch_size: int = Field(
        default=50,
        description="Batch size for CTS API calls"
    )
    output_key: str = Field(
        description="Key to store enriched matches"
    )
    track_metrics: bool = Field(
        default=True,
        description="Track detailed metrics"
    )
    match_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Minimum score for matches"
    )
    cts_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for CTS client"
    )


class EnrichmentMetrics(BaseModel):
    """Metrics for CTS enrichment and matching."""
    stage: str = "api_enriched"
    total_unmatched_input: int
    total_enriched: int
    total_matched: int
    enrichment_rate: float
    match_rate: float
    avg_names_per_metabolite: float
    api_calls_made: int
    cache_hits: int
    execution_time: float
    avg_confidence: float
    identifier_coverage: Dict[str, int]


@register_action("CTS_ENRICHED_MATCH")
class CtsEnrichedMatchAction(TypedStrategyAction[CtsEnrichedMatchParams, StandardActionResult]):
    """Match metabolites using CTS API enrichment."""
    
    def get_params_model(self) -> type[CtsEnrichedMatchParams]:
        """Return the params model class."""
        return CtsEnrichedMatchParams
    
    def get_result_model(self) -> type[StandardActionResult]:
        """Return the result model class."""
        return StandardActionResult
    
    def __init__(self) -> None:
        """Initialize with CTS client."""
        super().__init__()
        self.cts_client: Optional[CTSClient] = None
    
    async def _initialize_cts_client(self, config: Optional[Dict[str, Any]]) -> None:
        """Initialize CTS client if not already done."""
        if not self.cts_client:
            client_config = config or {
                'rate_limit_per_second': 10,
                'timeout_seconds': 30,
                'retry_attempts': 3
            }
            self.cts_client = CTSClient(client_config)
            await self.cts_client.initialize()
    
    async def _enrich_metabolites(
        self,
        metabolites: List[Dict[str, Any]],
        identifier_columns: List[str],
        batch_size: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Enrich metabolites with CTS API data.
        
        Returns list of enriched metabolites with additional names.
        """
        enriched = []
        api_calls = 0
        
        # Process in batches
        for i in range(0, len(metabolites), batch_size):
            batch = metabolites[i:i+batch_size]
            
            # Collect all identifiers to convert
            conversion_tasks = []
            metabolite_indices = []
            
            for idx, metabolite in enumerate(batch):
                for id_col in identifier_columns:
                    if id_value := metabolite.get(id_col):
                        # Only process non-empty identifiers
                        if id_value and str(id_value).strip():
                            assert self.cts_client is not None
                            conversion_tasks.append(
                                self.cts_client.convert(
                                    str(id_value).strip(),
                                    id_col,
                                    "Chemical Name"
                                )
                            )
                            metabolite_indices.append((idx, id_col, id_value))
            
            # Execute conversions in parallel
            if conversion_tasks:
                results = await asyncio.gather(*conversion_tasks, return_exceptions=True)
                api_calls += len(conversion_tasks)
                
                # Map results back to metabolites
                names_by_metabolite: Dict[int, Dict[str, Any]] = {}
                for (idx, id_col, id_value), result in zip(metabolite_indices, results):
                    if idx not in names_by_metabolite:
                        names_by_metabolite[idx] = {
                            'original': batch[idx],
                            'cts_names': set(),
                            'successful_ids': []
                        }
                    
                    if isinstance(result, list) and result:
                        names_by_metabolite[idx]['cts_names'].update(result)
                        names_by_metabolite[idx]['successful_ids'].append(id_col)
                
                # Create enriched records
                for idx, metabolite in enumerate(batch):
                    if idx in names_by_metabolite:
                        enriched_data = names_by_metabolite[idx]
                        enriched.append({
                            **enriched_data['original'],
                            'cts_enriched_names': list(enriched_data['cts_names']),
                            'cts_successful_ids': enriched_data['successful_ids'],
                            'enrichment_source': 'cts_api'
                        })
                    else:
                        # No enrichment possible
                        enriched.append({
                            **metabolite,
                            'cts_enriched_names': [],
                            'cts_successful_ids': [],
                            'enrichment_source': 'none'
                        })
            else:
                # No identifiers to convert in this batch
                for metabolite in batch:
                    enriched.append({
                        **metabolite,
                        'cts_enriched_names': [],
                        'cts_successful_ids': [],
                        'enrichment_source': 'none'
                    })
        
        return enriched, api_calls
    
    def _fuzzy_match_enriched(
        self,
        enriched_metabolite: Dict[str, Any],
        target_data: List[Dict[str, Any]],
        target_column: str,
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Attempt fuzzy matching with enriched names.
        
        Returns best match if found above threshold.
        """
        # Collect all names to try
        names_to_try = []
        
        # Original name
        if original_name := enriched_metabolite.get('BIOCHEMICAL_NAME'):
            names_to_try.append(original_name)
        
        # CTS enriched names
        names_to_try.extend(enriched_metabolite.get('cts_enriched_names', []))
        
        if not names_to_try:
            return None
        
        best_match = None
        best_score = 0.0
        best_source_name = ""
        best_matching_method = ""
        
        for source_name in names_to_try:
            for target_item in target_data:
                target_name = target_item.get(target_column, "")
                if not target_name:
                    continue
                
                # Try multiple algorithms
                scores = {
                    'token_set_ratio': fuzz.token_set_ratio(source_name, target_name) / 100.0,
                    'token_sort_ratio': fuzz.token_sort_ratio(source_name, target_name) / 100.0,
                    'partial_ratio': fuzz.partial_ratio(source_name, target_name) / 100.0
                }
                
                for method, score in scores.items():
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = target_item
                        best_source_name = source_name
                        best_matching_method = f"cts_enriched_{method}"
        
        if best_match:
            return {
                'target': best_match,
                'score': best_score,
                'matched_name': best_source_name,
                'method': best_matching_method,
                'enrichment_used': best_source_name in enriched_metabolite.get('cts_enriched_names', [])
            }
        
        return None
    
    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: CtsEnrichedMatchParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any
    ) -> StandardActionResult:
        """Execute CTS-enriched matching."""
        
        start_time = time.time()
        
        # Initialize CTS client
        await self._initialize_cts_client(params.cts_config)
        
        # Get datasets - handle both dict and typed context
        if hasattr(context, 'get_action_data'):
            datasets = context.get_action_data('datasets', {})
        else:
            datasets = context.get('datasets', {})
        
        unmatched_data = datasets.get(params.unmatched_dataset_key, [])
        target_data = datasets.get(params.target_dataset_key, [])
        
        if not unmatched_data:
            logger.warning(f"No unmatched data found in '{params.unmatched_dataset_key}'")
            return StandardActionResult(
                input_identifiers=[],
                output_identifiers=[],
                output_ontology_type="",
                provenance=[],
                details={'matched': 0, 'enriched': 0}
            )
        
        logger.info(
            f"Starting CTS enrichment for {len(unmatched_data)} unmatched metabolites"
        )
        
        # Enrich metabolites with CTS
        enriched_metabolites, api_calls = await self._enrich_metabolites(
            unmatched_data,
            params.identifier_columns,
            params.batch_size
        )
        
        # Count enrichment success
        enriched_count = sum(
            1 for m in enriched_metabolites 
            if m.get('cts_enriched_names')
        )
        
        # Calculate identifier coverage
        id_coverage = {}
        for id_col in params.identifier_columns:
            count = sum(
                1 for m in enriched_metabolites
                if id_col in m.get('cts_successful_ids', [])
            )
            id_coverage[id_col] = count
        
        # Attempt matching with enriched names
        matches = []
        still_unmatched = []
        total_confidence = 0.0
        total_names_collected = 0
        
        for metabolite in enriched_metabolites:
            match_result = self._fuzzy_match_enriched(
                metabolite,
                target_data,
                params.target_column,
                params.match_threshold
            )
            
            if match_result:
                match_record = {
                    'source': metabolite,
                    'target': match_result['target'],
                    'score': match_result['score'],
                    'method': match_result['method'],
                    'stage': 'api_enriched',
                    'matched_name': match_result['matched_name'],
                    'enrichment_used': match_result['enrichment_used'],
                    'cts_names_count': len(metabolite.get('cts_enriched_names', []))
                }
                matches.append(match_record)
                total_confidence += match_result['score']
            else:
                still_unmatched.append(metabolite)
            
            total_names_collected += len(metabolite.get('cts_enriched_names', []))
        
        # Calculate metrics
        execution_time = time.time() - start_time
        avg_confidence = total_confidence / len(matches) if matches else 0.0
        avg_names = total_names_collected / len(enriched_metabolites) if enriched_metabolites else 0.0
        
        metrics = EnrichmentMetrics(
            stage='api_enriched',
            total_unmatched_input=len(unmatched_data),
            total_enriched=enriched_count,
            total_matched=len(matches),
            enrichment_rate=enriched_count / len(unmatched_data) if unmatched_data else 0.0,
            match_rate=len(matches) / len(unmatched_data) if unmatched_data else 0.0,
            avg_names_per_metabolite=avg_names,
            api_calls_made=api_calls,
            cache_hits=0,  # TODO: Get from CTS client
            execution_time=execution_time,
            avg_confidence=avg_confidence,
            identifier_coverage=id_coverage
        )
        
        # Store results - handle both dict and typed context
        if hasattr(context, 'set_action_data'):
            # Typed context
            datasets[params.output_key] = matches
            unmatched_key = f"unmatched.api.{params.unmatched_dataset_key.split('.')[-1]}"
            datasets[unmatched_key] = still_unmatched
            context.set_action_data('datasets', datasets)
            
            if params.track_metrics:
                context.set_action_data('metrics', {'api_enriched': metrics.dict()})
        else:
            # Dict context
            if 'datasets' not in context:
                context['datasets'] = {}
            context['datasets'][params.output_key] = matches
            
            unmatched_key = f"unmatched.api.{params.unmatched_dataset_key.split('.')[-1]}"
            context['datasets'][unmatched_key] = still_unmatched
            
            if params.track_metrics:
                if 'metrics' not in context:
                    context['metrics'] = {}
                context['metrics']['api_enriched'] = metrics.dict()
        
        # Close CTS client
        if self.cts_client:
            await self.cts_client.close()
        
        logger.info(
            f"CTS enrichment complete: {enriched_count} enriched, "
            f"{len(matches)} matched ({metrics.match_rate:.1%}), "
            f"time: {execution_time:.2f}s"
        )
        
        return StandardActionResult(
            input_identifiers=[],
            output_identifiers=[],
            output_ontology_type="",
            provenance=[],
            details={
                'metrics': metrics.dict(),
                'matched_count': len(matches),
                'enriched_count': enriched_count,
                'still_unmatched': len(still_unmatched),
                'api_calls': api_calls
            }
        )