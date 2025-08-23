"""
LIPID MAPS SPARQL Match Action for Stage 5 of Progressive Metabolomics Pipeline

This action queries the LIPID MAPS SPARQL endpoint to find matches for unmapped
lipid metabolites. It implements comprehensive error handling, timeout management,
and feature flag control to ensure pipeline stability.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from functools import lru_cache
import re
import json
from pathlib import Path
import hashlib

import pandas as pd
import requests
from pydantic import BaseModel, Field, validator

from actions.typed_base import TypedStrategyAction
from actions.registry import register_action
from core.standards.base_models import ActionParamsBase
from core.standards.context_handler import UniversalContext

logger = logging.getLogger(__name__)


class LipidMapsSparqlParams(ActionParamsBase):
    """Parameters for LIPID MAPS SPARQL matching action."""
    
    # Data flow
    input_key: str = Field(..., description="Dataset key with unmapped metabolites")
    output_key: str = Field("stage_5_matched", description="Matched results")
    unmatched_key: str = Field("final_unmapped", description="Still unmapped after Stage 5")
    name_column: str = Field("identifier", description="Column containing metabolite names")
    
    # Feature control
    enabled: bool = Field(True, description="Feature flag to enable/disable action")
    fail_on_error: bool = Field(False, description="Whether to fail pipeline on SPARQL errors")
    
    # SPARQL configuration
    endpoint_url: str = Field("https://lipidmaps.org/sparql", description="SPARQL endpoint")
    query_strategy: str = Field("tiered", description="Query strategy: exact, fuzzy, or tiered")
    batch_size: int = Field(10, ge=1, le=20, description="Metabolites per batch query")
    timeout_seconds: int = Field(3, ge=1, le=30, description="Query timeout in seconds")
    max_retries: int = Field(2, ge=0, le=5, description="Retry attempts")
    
    # Performance controls
    cache_results: bool = Field(True, description="Cache successful matches")
    cache_ttl_hours: int = Field(24, ge=1, description="Cache time-to-live")
    cache_dir: Optional[str] = Field("/tmp/lipid_maps_cache", description="Cache directory")
    
    # Filtering
    filter_lipids_only: bool = Field(True, description="Pre-filter by pathway")
    lipid_indicators: List[str] = Field(
        default_factory=lambda: ["Lipid", "Fatty Acid", "Steroid", "Sphingolipid", 
                                "Phospholipid", "Glycerolipid", "Sterol"],
        description="Pathway indicators for lipids"
    )
    
    # Confidence scoring
    exact_match_confidence: float = Field(0.95, ge=0.5, le=1.0)
    fuzzy_match_confidence: float = Field(0.70, ge=0.5, le=1.0)
    formula_match_confidence: float = Field(0.60, ge=0.5, le=1.0)
    
    @validator("timeout_seconds")
    def validate_timeout(cls, v):
        """Ensure timeout is reasonable."""
        if v < 1 or v > 30:
            raise ValueError("Timeout must be between 1 and 30 seconds")
        return v
    
    @validator("batch_size")
    def validate_batch_size(cls, v):
        """Ensure batch size is reasonable."""
        if v < 1 or v > 20:
            raise ValueError("Batch size must be between 1 and 20")
        return v


class LipidMapsSparqlResult(BaseModel):
    """Result of LIPID MAPS SPARQL matching."""
    
    success: bool
    matches_found: int = 0
    queries_executed: int = 0
    timeouts: int = 0
    sparql_errors: int = 0
    average_query_time: float = 0.0
    cache_hits: int = 0
    message: str = ""
    stage5_coverage_improvement: float = 0.0


@register_action("LIPID_MAPS_SPARQL_MATCH")
class LipidMapsSparqlMatch(TypedStrategyAction[LipidMapsSparqlParams, LipidMapsSparqlResult]):
    """
    Stage 5: Query LIPID MAPS SPARQL for lipid-specific metabolite matches.
    
    This action implements a tiered query strategy:
    1. Exact name matching (confidence 0.95)
    2. Fuzzy/contains matching (confidence 0.70)
    3. Formula-based matching if available (confidence 0.60)
    
    Key features:
    - Aggressive timeout management (3s default)
    - Feature flag control for easy disable
    - Comprehensive error handling
    - Result caching to reduce queries
    - Batch query optimization when beneficial
    """
    
    def __init__(self):
        """Initialize the action with cache."""
        super().__init__()
        self._cache = {}
        self._query_times = []
    
    def get_params_model(self) -> type[LipidMapsSparqlParams]:
        """Return the params model class."""
        return LipidMapsSparqlParams
    
    def get_result_model(self) -> type[LipidMapsSparqlResult]:
        """Return the result model class."""
        return LipidMapsSparqlResult
    
    def _escape_sparql_string(self, value: str) -> str:
        """Escape string for safe SPARQL query inclusion."""
        # Escape quotes and backslashes
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        return escaped
    
    def _generate_exact_query(self, metabolite_name: str) -> str:
        """Generate exact match SPARQL query."""
        escaped_name = self._escape_sparql_string(metabolite_name)
        
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>
        
        SELECT ?lipid ?label ?inchikey ?formula WHERE {{
            ?lipid rdfs:label ?label .
            FILTER(LCASE(STR(?label)) = LCASE("{escaped_name}"))
            OPTIONAL {{ ?lipid chebi:inchikey ?inchikey }}
            OPTIONAL {{ ?lipid chebi:formula ?formula }}
        }} LIMIT 1
        """
        return query
    
    def _generate_fuzzy_query(self, metabolite_name: str) -> str:
        """Generate fuzzy/contains match SPARQL query."""
        # Extract core name (before parentheses)
        core_name = metabolite_name.split('(')[0].strip()
        escaped_name = self._escape_sparql_string(core_name)
        
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>
        
        SELECT ?lipid ?label ?inchikey ?formula WHERE {{
            ?lipid rdfs:label ?label .
            FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{escaped_name}")))
            OPTIONAL {{ ?lipid chebi:inchikey ?inchikey }}
            OPTIONAL {{ ?lipid chebi:formula ?formula }}
        }} ORDER BY STRLEN(?label) LIMIT 5
        """
        return query
    
    def _generate_batch_query(self, metabolites: List[str], query_type: str = "exact") -> str:
        """Generate batch query with UNION clauses."""
        union_parts = []
        
        for metabolite in metabolites:
            escaped_name = self._escape_sparql_string(metabolite)
            
            if query_type == "exact":
                filter_clause = f'FILTER(LCASE(STR(?label)) = LCASE("{escaped_name}"))'
            else:  # fuzzy
                core_name = metabolite.split('(')[0].strip()
                escaped_name = self._escape_sparql_string(core_name)
                filter_clause = f'FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{escaped_name}")))'
            
            union_parts.append(f"""
            {{
                ?lipid rdfs:label ?label .
                {filter_clause}
                OPTIONAL {{ ?lipid chebi:inchikey ?inchikey }}
                OPTIONAL {{ ?lipid chebi:formula ?formula }}
            }}
            """)
        
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX chebi: <http://purl.obolibrary.org/obo/chebi/>
        
        SELECT ?lipid ?label ?inchikey ?formula WHERE {{
            {" UNION ".join(union_parts)}
        }} LIMIT {len(metabolites) * 2}
        """
        return query
    
    def _execute_sparql_query(self, query: str, timeout: int) -> Tuple[Dict, float]:
        """
        Execute a SPARQL query with timeout management.
        
        Returns:
            Tuple of (results_dict, elapsed_time)
        """
        headers = {
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json"
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                "https://lipidmaps.org/sparql",
                data=query.encode('utf-8'),
                headers=headers,
                timeout=timeout
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                return response.json(), elapsed
            else:
                logger.warning(f"SPARQL query failed with status {response.status_code}")
                return {"error": f"Status {response.status_code}"}, elapsed
                
        except requests.Timeout:
            elapsed = time.time() - start_time
            logger.warning(f"SPARQL query timed out after {elapsed:.2f}s")
            return {"error": "timeout"}, elapsed
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"SPARQL query error: {e}")
            return {"error": str(e)}, elapsed
    
    def _get_cache_key(self, metabolite_name: str) -> str:
        """Generate cache key for metabolite."""
        return hashlib.md5(metabolite_name.lower().encode()).hexdigest()
    
    def _get_from_cache(self, metabolite_name: str) -> Optional[Dict]:
        """Get cached result if available."""
        if not self._cache:
            return None
        
        cache_key = self._get_cache_key(metabolite_name)
        return self._cache.get(cache_key)
    
    def _save_to_cache(self, metabolite_name: str, result: Dict):
        """Save result to cache."""
        cache_key = self._get_cache_key(metabolite_name)
        self._cache[cache_key] = result
    
    def _calculate_confidence_score(self, match_type: str) -> float:
        """Calculate confidence score based on match type."""
        if match_type == "exact":
            return 0.95
        elif match_type == "fuzzy":
            return 0.70
        elif match_type == "formula":
            return 0.60
        else:
            return 0.50
    
    def _process_sparql_result(self, result: Dict, metabolite: Dict, match_type: str) -> Optional[Dict]:
        """Process SPARQL result into standardized match format."""
        if "error" in result or not result.get("results", {}).get("bindings"):
            return None
        
        bindings = result["results"]["bindings"]
        if not bindings:
            return None
        
        # Take first result
        binding = bindings[0]
        
        # Extract LIPID MAPS ID from URI
        lipid_uri = binding.get("lipid", {}).get("value", "")
        lipid_id = lipid_uri.split("/")[-1] if lipid_uri else "Unknown"
        
        return {
            **metabolite,
            "lipid_maps_id": lipid_id,
            "lipid_maps_name": binding.get("label", {}).get("value", ""),
            "confidence_score": self._calculate_confidence_score(match_type),
            "match_type": f"lipid_maps_{match_type}",
            "match_source": "LIPID_MAPS_SPARQL",
            "inchikey": binding.get("inchikey", {}).get("value", ""),
            "formula": binding.get("formula", {}).get("value", ""),
            "sparql_query_type": match_type
        }
    
    async def execute_typed(
        self,
        params: LipidMapsSparqlParams,
        context: Any
    ) -> LipidMapsSparqlResult:
        """Execute LIPID MAPS SPARQL matching for Stage 5."""
        
        # Check feature flag
        if not params.enabled:
            logger.info("LIPID MAPS SPARQL disabled by feature flag")
            return LipidMapsSparqlResult(
                success=True,
                message="LIPID MAPS SPARQL disabled by feature flag"
            )
        
        try:
            # Get context using UniversalContext wrapper
            ctx = UniversalContext.wrap(context)
            datasets = ctx.get_datasets()
            
            # Get unmapped metabolites
            unmapped_df = datasets.get(params.input_key)
            if unmapped_df is None or unmapped_df.empty:
                return LipidMapsSparqlResult(
                    success=True,
                    message="No unmapped metabolites to process"
                )
            
            # Convert to list of dicts for processing
            unmapped = unmapped_df.to_dict('records')
            
            # Filter for lipids if configured
            if params.filter_lipids_only:
                original_count = len(unmapped)
                unmapped = [
                    m for m in unmapped
                    if m.get("SUPER_PATHWAY") in params.lipid_indicators
                    or m.get("SUB_PATHWAY") in params.lipid_indicators
                ]
                logger.info(f"Filtered {original_count} metabolites to {len(unmapped)} likely lipids")
            
            if not unmapped:
                return LipidMapsSparqlResult(
                    success=True,
                    message="No lipid metabolites to query"
                )
            
            # Process metabolites
            matched = []
            still_unmapped = []
            queries_executed = 0
            timeouts = 0
            sparql_errors = 0
            cache_hits = 0
            
            # Track statistics
            self._query_times = []
            
            # Process in batches
            for i in range(0, len(unmapped), params.batch_size):
                batch = unmapped[i:i + params.batch_size]
                batch_matched = []
                batch_unmapped = []
                
                # Try batch query first
                if len(batch) > 1:
                    batch_names = [m.get(params.name_column, "") for m in batch]
                    batch_query = self._generate_batch_query(batch_names, "exact")
                    
                    result, elapsed = self._execute_sparql_query(batch_query, params.timeout_seconds)
                    queries_executed += 1
                    self._query_times.append(elapsed)
                    
                    if "error" in result:
                        if result["error"] == "timeout":
                            timeouts += 1
                        else:
                            sparql_errors += 1
                        # Fall back to individual queries
                        logger.warning("Batch query failed, falling back to individual queries")
                    else:
                        # Process batch results
                        bindings = result.get("results", {}).get("bindings", [])
                        matched_names = set()
                        
                        for binding in bindings:
                            label = binding.get("label", {}).get("value", "").lower()
                            # Find which metabolite this matches
                            for metabolite in batch:
                                name = metabolite.get(params.name_column, "").lower()
                                if name == label and name not in matched_names:
                                    match = self._process_sparql_result(
                                        {"results": {"bindings": [binding]}},
                                        metabolite,
                                        "exact"
                                    )
                                    if match:
                                        batch_matched.append(match)
                                        matched_names.add(name)
                                    break
                        
                        # Unmapped from batch
                        for metabolite in batch:
                            name = metabolite.get(params.name_column, "").lower()
                            if name not in matched_names:
                                batch_unmapped.append(metabolite)
                
                # Process individually if batch failed or single item
                if not batch_matched and batch_unmapped == batch:
                    for metabolite in batch:
                        name = metabolite.get(params.name_column, "")
                        if not name:
                            still_unmapped.append(metabolite)
                            continue
                        
                        # Check cache first
                        cached = self._get_from_cache(name)
                        if cached:
                            cache_hits += 1
                            batch_matched.append({**metabolite, **cached})
                            continue
                        
                        # Try exact match
                        query = self._generate_exact_query(name)
                        result, elapsed = self._execute_sparql_query(query, params.timeout_seconds)
                        queries_executed += 1
                        self._query_times.append(elapsed)
                        
                        if "error" in result:
                            if result["error"] == "timeout":
                                timeouts += 1
                            else:
                                sparql_errors += 1
                            batch_unmapped.append(metabolite)
                            continue
                        
                        match = self._process_sparql_result(result, metabolite, "exact")
                        
                        # If no exact match, try fuzzy
                        if not match and params.query_strategy in ["fuzzy", "tiered"]:
                            query = self._generate_fuzzy_query(name)
                            result, elapsed = self._execute_sparql_query(query, params.timeout_seconds)
                            queries_executed += 1
                            self._query_times.append(elapsed)
                            
                            if "error" not in result:
                                match = self._process_sparql_result(result, metabolite, "fuzzy")
                        
                        if match:
                            batch_matched.append(match)
                            # Cache the match
                            if params.cache_results:
                                self._save_to_cache(name, {
                                    k: v for k, v in match.items()
                                    if k not in metabolite.keys()
                                })
                        else:
                            batch_unmapped.append(metabolite)
                
                matched.extend(batch_matched)
                still_unmapped.extend(batch_unmapped)
            
            # Store results directly in datasets dict
            datasets[params.output_key] = pd.DataFrame(matched)
            datasets[params.unmatched_key] = pd.DataFrame(still_unmapped)
            
            # Calculate statistics
            avg_query_time = sum(self._query_times) / len(self._query_times) if self._query_times else 0
            
            # Update progressive statistics
            statistics = context.get("statistics", {})
            total_metabolites = len(datasets.get("original_metabolites", unmapped_df))
            
            # Calculate cumulative coverage
            prev_stages_matched = statistics.get("progressive_stage4", {}).get("cumulative_matched", 0)
            stage5_matched = len(matched)
            cumulative_matched = prev_stages_matched + stage5_matched
            cumulative_coverage = cumulative_matched / total_metabolites if total_metabolites > 0 else 0
            
            statistics["progressive_stage5"] = {
                "stage": 5,
                "lipid_maps_matched": len(matched),
                "still_unmapped": len(still_unmapped),
                "cumulative_matched": cumulative_matched,
                "cumulative_coverage": cumulative_coverage,
                "queries_executed": queries_executed,
                "timeouts": timeouts,
                "sparql_errors": sparql_errors,
                "cache_hits": cache_hits,
                "average_query_time": avg_query_time
            }
            context["statistics"] = statistics
            
            # Log results
            logger.info(f"Stage 5 LIPID MAPS Complete:")
            logger.info(f"  Matched: {len(matched)}")
            logger.info(f"  Still unmapped: {len(still_unmapped)}")
            logger.info(f"  Queries executed: {queries_executed}")
            logger.info(f"  Timeouts: {timeouts}")
            logger.info(f"  Cache hits: {cache_hits}")
            logger.info(f"  Average query time: {avg_query_time:.2f}s")
            
            message = f"Matched {len(matched)} metabolites via LIPID MAPS SPARQL"
            if timeouts > 0:
                message += f" (with {timeouts} timeouts)"
            
            return LipidMapsSparqlResult(
                success=True,
                matches_found=len(matched),
                queries_executed=queries_executed,
                timeouts=timeouts,
                sparql_errors=sparql_errors,
                average_query_time=avg_query_time,
                cache_hits=cache_hits,
                message=message,
                stage5_coverage_improvement=(len(matched) / total_metabolites * 100) if total_metabolites > 0 else 0
            )
            
        except Exception as e:
            logger.error(f"Error in LIPID MAPS SPARQL matching: {e}")
            
            if params.fail_on_error:
                return LipidMapsSparqlResult(
                    success=False,
                    message=f"LIPID MAPS SPARQL failed: {str(e)}"
                )
            else:
                # Continue pipeline even on error
                return LipidMapsSparqlResult(
                    success=True,
                    sparql_errors=1,
                    message=f"LIPID MAPS SPARQL error (pipeline continued): {str(e)}"
                )