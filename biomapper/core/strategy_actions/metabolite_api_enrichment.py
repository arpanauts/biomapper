"""Multi-API enriched matching action for metabolites."""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field, validator

from biomapper.core.strategy_actions.typed_base import (
    TypedStrategyAction,
    StandardActionResult,
)
from biomapper.core.strategy_actions.registry import register_action
from biomapper.mapping.clients.cts_client import CTSClient
from biomapper.mapping.clients.metabolite_apis import (
    HMDBClient,
    PubChemEnhancedClient,
    PubChemIdType,
)
from thefuzz import fuzz  # type: ignore

logger = logging.getLogger(__name__)


class ApiService(str, Enum):
    """Supported API services."""

    CTS = "cts"
    HMDB = "hmdb"
    PUBCHEM = "pubchem"
    CHEMSPIDER = "chemspider"  # Placeholder for future implementation


class ApiServiceConfig(BaseModel):
    """Configuration for a single API service."""

    service: ApiService = Field(
        ..., description="Service name: cts, hmdb, pubchem, chemspider"
    )
    input_column: str = Field(
        ..., description="Column containing identifiers for this service"
    )
    output_fields: List[str] = Field(
        default_factory=lambda: ["name", "synonyms", "inchikey"],
        description="Fields to retrieve from this service",
    )
    timeout: int = Field(30, description="API timeout in seconds")
    base_url: Optional[str] = Field(None, description="Override base URL for service")
    id_type: Optional[str] = Field(
        None, description="Identifier type for services that need it (e.g., pubchem)"
    )

    @validator("service", pre=True)
    def lowercase_service(cls, v):
        """Ensure service name is lowercase."""
        return v.lower() if isinstance(v, str) else v


class MetaboliteApiEnrichmentParams(BaseModel):
    """Extended parameters for multi-API enrichment."""

    # Keep existing fields for backward compatibility
    unmatched_dataset_key: str = Field(..., description="Key for unmatched metabolites")
    target_dataset_key: str = Field(..., description="Target dataset to match against")
    target_column: str = Field(
        default="unified_name", description="Target column for matching"
    )

    # New multi-API support
    api_services: Optional[List[ApiServiceConfig]] = Field(
        None, description="List of API services to use for enrichment"
    )

    # Backward compatibility - if api_services not provided, use these
    identifier_columns: Optional[List[str]] = Field(
        None, description="Legacy: columns for CTS-only mode"
    )
    cts_timeout: Optional[int] = Field(None, description="Legacy: CTS timeout")

    # Common parameters
    match_threshold: float = Field(
        0.8, ge=0.0, le=1.0, description="Threshold for name matching"
    )
    batch_size: int = Field(50, description="Batch size for API calls")
    cache_results: bool = Field(True, description="Cache API responses")
    output_key: str = Field(..., description="Key for matched results")
    unmatched_key: Optional[str] = Field(
        None, description="Key for remaining unmatched"
    )
    track_metrics: bool = Field(True, description="Track enrichment metrics")

    @validator("api_services", always=True)
    def handle_legacy_mode(cls, v, values):
        """Convert legacy parameters to new format if needed."""
        if v is None and values.get("identifier_columns"):
            # Legacy mode - create CTS-only configuration
            logger.info("Converting legacy CTS-only configuration to multi-API format")
            return [
                ApiServiceConfig(
                    service=ApiService.CTS,
                    input_column="multiple",  # Special marker for legacy mode
                    output_fields=["chemical_name", "synonyms"],
                    timeout=values.get("cts_timeout", 30),
                )
            ]
        return v


class EnrichmentMetrics(BaseModel):
    """Metrics for multi-API enrichment and matching."""

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
    api_breakdown: Dict[str, Dict[str, int]]


@register_action("METABOLITE_API_ENRICHMENT")
class MetaboliteApiEnrichmentAction(
    TypedStrategyAction[MetaboliteApiEnrichmentParams, StandardActionResult]
):
    """Match metabolites using multi-API enrichment.

    This action extends the original CTS_ENRICHED_MATCH to support multiple
    chemical databases including HMDB, PubChem, and ChemSpider.
    """

    def get_params_model(self) -> type[MetaboliteApiEnrichmentParams]:
        """Return the params model class."""
        return MetaboliteApiEnrichmentParams

    def get_result_model(self) -> type[StandardActionResult]:
        """Return the result model class."""
        return StandardActionResult

    def __init__(self) -> None:
        """Initialize with API clients."""
        super().__init__()
        self.api_clients: Dict[str, Any] = {}

    async def _initialize_api_clients(
        self, params: MetaboliteApiEnrichmentParams
    ) -> None:
        """Initialize API clients based on configuration."""
        if not params.api_services:
            return

        for service_config in params.api_services:
            if service_config.service == ApiService.CTS:
                if ApiService.CTS not in self.api_clients:
                    client_config = {
                        "rate_limit_per_second": 10,
                        "timeout_seconds": service_config.timeout,
                        "retry_attempts": 3,
                    }
                    self.api_clients[ApiService.CTS] = CTSClient(client_config)
                    await self.api_clients[ApiService.CTS].initialize()

            elif service_config.service == ApiService.HMDB:
                if ApiService.HMDB not in self.api_clients:
                    self.api_clients[ApiService.HMDB] = HMDBClient(
                        timeout=service_config.timeout
                    )
                    await self.api_clients[ApiService.HMDB].initialize()

            elif service_config.service == ApiService.PUBCHEM:
                if ApiService.PUBCHEM not in self.api_clients:
                    self.api_clients[ApiService.PUBCHEM] = PubChemEnhancedClient(
                        timeout=service_config.timeout
                    )
                    await self.api_clients[ApiService.PUBCHEM].initialize()

    async def _close_api_clients(self) -> None:
        """Close all API clients."""
        for client in self.api_clients.values():
            if hasattr(client, "close"):
                await client.close()
        self.api_clients.clear()

    async def _enrich_with_cts(
        self,
        metabolites: List[Dict[str, Any]],
        service_config: ApiServiceConfig,
        legacy_columns: Optional[List[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Enrich metabolites using CTS API."""
        client = self.api_clients[ApiService.CTS]
        enriched = []
        metrics = {"total": 0, "enriched": 0, "api_calls": 0}

        # Handle legacy mode where multiple columns are used
        if service_config.input_column == "multiple" and legacy_columns:
            identifier_columns = legacy_columns
        else:
            identifier_columns = [service_config.input_column]

        for metabolite in metabolites:
            cts_names = set()
            successful_ids = []

            for id_col in identifier_columns:
                if id_value := metabolite.get(id_col):
                    if id_value and str(id_value).strip():
                        try:
                            results = await client.convert(
                                str(id_value).strip(), id_col, "Chemical Name"
                            )
                            metrics["api_calls"] += 1

                            if results:
                                cts_names.update(results)
                                successful_ids.append(id_col)
                        except Exception as e:
                            logger.debug(f"CTS error for {id_value}: {e}")

            enriched_metabolite = {
                **metabolite,
                "cts_enriched_names": list(cts_names),
                "cts_successful_ids": successful_ids,
                "enrichment_source": "cts" if cts_names else "none",
            }
            enriched.append(enriched_metabolite)

            metrics["total"] += 1
            if cts_names:
                metrics["enriched"] += 1

        return enriched, metrics

    async def _enrich_with_hmdb(
        self, metabolites: List[Dict[str, Any]], service_config: ApiServiceConfig
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Enrich metabolites using HMDB API."""
        client = self.api_clients[ApiService.HMDB]
        enriched = []
        metrics = {"total": 0, "enriched": 0, "api_calls": 0}

        for metabolite in metabolites:
            hmdb_id = metabolite.get(service_config.input_column)
            if not hmdb_id:
                enriched.append(metabolite)
                continue

            # Get HMDB data
            hmdb_info = await client.get_metabolite_info(str(hmdb_id))
            metrics["api_calls"] += 1

            # Extract requested fields
            enriched_names = set()
            additional_data = {}

            if not hmdb_info.error:
                if "name" in service_config.output_fields and hmdb_info.common_name:
                    enriched_names.add(hmdb_info.common_name)

                if (
                    "iupac_name" in service_config.output_fields
                    and hmdb_info.iupac_name
                ):
                    enriched_names.add(hmdb_info.iupac_name)

                if "synonyms" in service_config.output_fields:
                    enriched_names.update(hmdb_info.synonyms)

                if "inchikey" in service_config.output_fields and hmdb_info.inchikey:
                    additional_data["hmdb_inchikey"] = hmdb_info.inchikey

                # Add cross-references
                if hmdb_info.kegg_id:
                    additional_data["hmdb_kegg_id"] = hmdb_info.kegg_id
                if hmdb_info.pubchem_cid:
                    additional_data["hmdb_pubchem_cid"] = hmdb_info.pubchem_cid

            enriched_metabolite = {
                **metabolite,
                **additional_data,
                "hmdb_enriched_names": list(enriched_names),
                "hmdb_enrichment_success": not bool(hmdb_info.error),
            }
            enriched.append(enriched_metabolite)

            metrics["total"] += 1
            if enriched_names:
                metrics["enriched"] += 1

        return enriched, metrics

    async def _enrich_with_pubchem(
        self, metabolites: List[Dict[str, Any]], service_config: ApiServiceConfig
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Enrich metabolites using PubChem API."""
        client = self.api_clients[ApiService.PUBCHEM]
        enriched = []
        metrics = {"total": 0, "enriched": 0, "api_calls": 0}

        # Determine ID type
        id_type_str = service_config.id_type or "cid"
        try:
            id_type = PubChemIdType(id_type_str.lower())
        except ValueError:
            id_type = PubChemIdType.CID

        for metabolite in metabolites:
            identifier = metabolite.get(service_config.input_column)
            if not identifier:
                enriched.append(metabolite)
                continue

            # Get PubChem data
            pubchem_info = await client.get_compound_info(str(identifier), id_type)
            metrics["api_calls"] += 1

            # Extract requested fields
            enriched_names = set()
            additional_data = {}

            if not pubchem_info.error:
                if "name" in service_config.output_fields and pubchem_info.iupac_name:
                    enriched_names.add(pubchem_info.iupac_name)

                if "synonyms" in service_config.output_fields:
                    enriched_names.update(pubchem_info.synonyms)

                if "inchikey" in service_config.output_fields and pubchem_info.inchikey:
                    additional_data["pubchem_inchikey"] = pubchem_info.inchikey

                if (
                    "formula" in service_config.output_fields
                    and pubchem_info.molecular_formula
                ):
                    additional_data["pubchem_formula"] = pubchem_info.molecular_formula

                if pubchem_info.cid:
                    additional_data["pubchem_cid"] = pubchem_info.cid

            enriched_metabolite = {
                **metabolite,
                **additional_data,
                "pubchem_enriched_names": list(enriched_names),
                "pubchem_enrichment_success": not bool(pubchem_info.error),
            }
            enriched.append(enriched_metabolite)

            metrics["total"] += 1
            if enriched_names:
                metrics["enriched"] += 1

        return enriched, metrics

    async def _process_api_enrichment(
        self, metabolites: List[Dict[str, Any]], params: MetaboliteApiEnrichmentParams
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, int]]]:
        """Process enrichment for all configured APIs."""
        enriched_data = metabolites
        api_metrics = {}

        if not params.api_services:
            return enriched_data, api_metrics

        for service_config in params.api_services:
            # Filter metabolites that have the required identifier
            if (
                service_config.input_column != "multiple"
            ):  # Skip filtering for legacy CTS mode
                relevant_metabolites = [
                    m for m in enriched_data if m.get(service_config.input_column)
                ]
            else:
                relevant_metabolites = enriched_data

            if not relevant_metabolites:
                continue

            # Process based on service type
            if service_config.service == ApiService.CTS:
                service_results, metrics = await self._enrich_with_cts(
                    relevant_metabolites, service_config, params.identifier_columns
                )
            elif service_config.service == ApiService.HMDB:
                service_results, metrics = await self._enrich_with_hmdb(
                    relevant_metabolites, service_config
                )
            elif service_config.service == ApiService.PUBCHEM:
                service_results, metrics = await self._enrich_with_pubchem(
                    relevant_metabolites, service_config
                )
            else:
                logger.warning(f"Unsupported API service: {service_config.service}")
                continue

            # Update the enriched data with results from this service
            # Create a mapping for efficient updates
            result_map = {
                m.get("BIOCHEMICAL_NAME", m.get("name", str(i))): m
                for i, m in enumerate(service_results)
            }

            # Update enriched_data with new information
            for i, metabolite in enumerate(enriched_data):
                key = metabolite.get("BIOCHEMICAL_NAME", metabolite.get("name", str(i)))
                if key in result_map:
                    enriched_data[i] = result_map[key]

            api_metrics[service_config.service] = metrics

        return enriched_data, api_metrics

    def _collect_all_enriched_names(self, metabolite: Dict[str, Any]) -> List[str]:
        """Collect all enriched names from different APIs."""
        all_names = []

        # Original name
        if original_name := metabolite.get("BIOCHEMICAL_NAME"):
            all_names.append(original_name)

        # CTS names
        all_names.extend(metabolite.get("cts_enriched_names", []))

        # HMDB names
        all_names.extend(metabolite.get("hmdb_enriched_names", []))

        # PubChem names
        all_names.extend(metabolite.get("pubchem_enriched_names", []))

        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in all_names:
            if name and name not in seen:
                seen.add(name)
                unique_names.append(name)

        return unique_names

    def _fuzzy_match_enriched(
        self,
        enriched_metabolite: Dict[str, Any],
        target_data: List[Dict[str, Any]],
        target_column: str,
        threshold: float,
    ) -> Optional[Dict[str, Any]]:
        """Attempt fuzzy matching with enriched names from all APIs."""
        names_to_try = self._collect_all_enriched_names(enriched_metabolite)

        if not names_to_try:
            return None

        best_match = None
        best_score = 0.0
        best_source_name = ""
        best_matching_method = ""
        best_api_source = ""

        for source_name in names_to_try:
            for target_item in target_data:
                target_name = target_item.get(target_column, "")
                if not target_name:
                    continue

                # Try multiple algorithms
                scores = {
                    "token_set_ratio": fuzz.token_set_ratio(source_name, target_name)
                    / 100.0,
                    "token_sort_ratio": fuzz.token_sort_ratio(source_name, target_name)
                    / 100.0,
                    "partial_ratio": fuzz.partial_ratio(source_name, target_name)
                    / 100.0,
                }

                for method, score in scores.items():
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = target_item
                        best_source_name = source_name
                        best_matching_method = f"multi_api_{method}"

                        # Determine which API provided the matching name
                        if source_name in enriched_metabolite.get(
                            "cts_enriched_names", []
                        ):
                            best_api_source = "cts"
                        elif source_name in enriched_metabolite.get(
                            "hmdb_enriched_names", []
                        ):
                            best_api_source = "hmdb"
                        elif source_name in enriched_metabolite.get(
                            "pubchem_enriched_names", []
                        ):
                            best_api_source = "pubchem"
                        else:
                            best_api_source = "original"

        if best_match:
            return {
                "target": best_match,
                "score": best_score,
                "matched_name": best_source_name,
                "method": best_matching_method,
                "api_source": best_api_source,
                "enrichment_used": best_api_source != "original",
            }

        return None

    async def execute_typed(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        params: MetaboliteApiEnrichmentParams,
        source_endpoint: Any,
        target_endpoint: Any,
        context: Any,
    ) -> StandardActionResult:
        """Execute multi-API enriched matching."""

        start_time = time.time()

        # Initialize API clients
        await self._initialize_api_clients(params)

        try:
            # Get datasets - handle both dict and typed context
            if hasattr(context, "get_action_data"):
                datasets = context.get_action_data("datasets", {})
            else:
                datasets = context.get("datasets", {})

            unmatched_data = datasets.get(params.unmatched_dataset_key, [])
            target_data = datasets.get(params.target_dataset_key, [])

            if not unmatched_data:
                logger.warning(
                    f"No unmatched data found in '{params.unmatched_dataset_key}'"
                )
                return StandardActionResult(
                    input_identifiers=[],
                    output_identifiers=[],
                    output_ontology_type="",
                    provenance=[],
                    details={"matched": 0, "enriched": 0},
                )

            logger.info(
                f"Starting multi-API enrichment for {len(unmatched_data)} unmatched metabolites"
            )

            # Enrich metabolites with configured APIs
            enriched_metabolites, api_metrics = await self._process_api_enrichment(
                unmatched_data, params
            )

            # Count overall enrichment success
            enriched_count = sum(
                1
                for m in enriched_metabolites
                if (
                    m.get("cts_enriched_names")
                    or m.get("hmdb_enriched_names")
                    or m.get("pubchem_enriched_names")
                )
            )

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
                    params.match_threshold,
                )

                if match_result:
                    match_record = {
                        "source": metabolite,
                        "target": match_result["target"],
                        "score": match_result["score"],
                        "method": match_result["method"],
                        "stage": "multi_api_enriched",
                        "matched_name": match_result["matched_name"],
                        "enrichment_used": match_result["enrichment_used"],
                        "api_source": match_result["api_source"],
                        "total_enriched_names": len(
                            self._collect_all_enriched_names(metabolite)
                        ),
                    }
                    matches.append(match_record)
                    total_confidence += match_result["score"]
                else:
                    still_unmatched.append(metabolite)

                total_names_collected += len(
                    self._collect_all_enriched_names(metabolite)
                )

            # Calculate metrics
            execution_time = time.time() - start_time
            avg_confidence = total_confidence / len(matches) if matches else 0.0
            avg_names = (
                total_names_collected / len(enriched_metabolites)
                if enriched_metabolites
                else 0.0
            )

            # Calculate total API calls
            total_api_calls = sum(
                metrics.get("api_calls", 0) for metrics in api_metrics.values()
            )

            metrics = EnrichmentMetrics(
                stage="multi_api_enriched",
                total_unmatched_input=len(unmatched_data),
                total_enriched=enriched_count,
                total_matched=len(matches),
                enrichment_rate=enriched_count / len(unmatched_data)
                if unmatched_data
                else 0.0,
                match_rate=len(matches) / len(unmatched_data)
                if unmatched_data
                else 0.0,
                avg_names_per_metabolite=avg_names,
                api_calls_made=total_api_calls,
                cache_hits=0,  # TODO: Implement caching
                execution_time=execution_time,
                avg_confidence=avg_confidence,
                api_breakdown=api_metrics,
            )

            # Store results - handle both dict and typed context
            if hasattr(context, "set_action_data"):
                # Typed context
                datasets[params.output_key] = matches
                if params.unmatched_key:
                    datasets[params.unmatched_key] = still_unmatched
                else:
                    unmatched_key = f"unmatched.multi_api.{params.unmatched_dataset_key.split('.')[-1]}"
                    datasets[unmatched_key] = still_unmatched
                context.set_action_data("datasets", datasets)

                if params.track_metrics:
                    context.set_action_data(
                        "metrics", {"multi_api_enriched": metrics.dict()}
                    )
            else:
                # Dict context
                if "datasets" not in context:
                    context["datasets"] = {}
                context["datasets"][params.output_key] = matches

                if params.unmatched_key:
                    context["datasets"][params.unmatched_key] = still_unmatched
                else:
                    unmatched_key = f"unmatched.multi_api.{params.unmatched_dataset_key.split('.')[-1]}"
                    context["datasets"][unmatched_key] = still_unmatched

                if params.track_metrics:
                    if "metrics" not in context:
                        context["metrics"] = {}
                    context["metrics"]["multi_api_enriched"] = metrics.dict()

            logger.info(
                f"Multi-API enrichment complete: {enriched_count} enriched, "
                f"{len(matches)} matched ({metrics.match_rate:.1%}), "
                f"APIs used: {list(api_metrics.keys())}, "
                f"time: {execution_time:.2f}s"
            )

            return StandardActionResult(
                input_identifiers=[],
                output_identifiers=[],
                output_ontology_type="",
                provenance=[],
                details={
                    "metrics": metrics.dict(),
                    "matched_count": len(matches),
                    "enriched_count": enriched_count,
                    "still_unmatched": len(still_unmatched),
                    "api_calls": total_api_calls,
                    "apis_used": list(api_metrics.keys()),
                },
            )

        finally:
            # Always close API clients
            await self._close_api_clients()


# Also register under the original name for backward compatibility
register_action("CTS_ENRICHED_MATCH")(MetaboliteApiEnrichmentAction)
