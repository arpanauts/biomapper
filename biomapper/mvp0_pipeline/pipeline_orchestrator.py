"""
MVP0 Pipeline Orchestrator for Arivale BIOCHEMICAL_NAME RAG Mapping.

This module orchestrates the three-stage RAG approach:
1. Qdrant search for candidate CIDs
2. PubChem annotation of candidates
3. LLM selection of best match

The orchestrator manages configuration, execution flow, error handling,
and result aggregation across all pipeline components.
"""

import logging
from typing import List, Optional
import asyncio
import time
from urllib.parse import urlparse
from qdrant_client import QdrantClient

from biomapper.mvp0_pipeline.pipeline_config import PipelineConfig
from biomapper.schemas.pipeline_schema import (
    PipelineMappingResult, 
    BatchMappingResult, 
    PipelineStatus
)
from biomapper.schemas.mvp0_schema import LLMCandidateInfo
from biomapper.mvp0_pipeline.qdrant_search import search_qdrant_for_biochemical_name
from biomapper.mvp0_pipeline.pubchem_annotator import fetch_pubchem_annotations
from biomapper.mvp0_pipeline.llm_mapper import select_best_cid_with_llm

# Configure module logger
logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Main orchestrator class for the MVP0 mapping pipeline.
    
    This class coordinates the execution of the three pipeline stages
    and handles configuration, error management, and result aggregation.
    
    The pipeline follows a three-stage RAG (Retrieval-Augmented Generation) approach:
    1. Vector similarity search in Qdrant to find candidate PubChem CIDs
    2. Enrichment of candidates with detailed annotations from PubChem API
    3. LLM-based selection of the best matching CID using contextual information
    
    Attributes:
        config (PipelineConfig): Configuration object containing all pipeline settings
    
    Example:
        >>> config = PipelineConfig(anthropic_api_key="your-key")
        >>> orchestrator = PipelineOrchestrator(config)
        >>> result = await orchestrator.run_single_mapping("glucose")
        >>> print(f"Mapped to CID: {result.selected_cid}")
    """
    
    def __init__(self, config: PipelineConfig):
        """
        Initialize the pipeline orchestrator with configuration.
        
        Args:
            config: PipelineConfig instance containing all necessary settings
            
        Raises:
            ValueError: If configuration validation fails
            ConnectionError: If Qdrant connectivity check fails
        """
        self.config = config
        
        # Validate configuration
        self._validate_configuration()
        
        # Check Qdrant connectivity
        self._check_qdrant_connectivity()
        
        logger.info("Pipeline orchestrator initialized successfully")
    
    def _validate_configuration(self) -> None:
        """
        Validate that all required configuration is present.
        
        This method checks for:
        - Required API keys (Anthropic)
        - Qdrant connection settings
        - Other critical configuration parameters
        
        Raises:
            ValueError: If required configuration is missing or invalid
        
        Note:
            This is called automatically during initialization to fail fast
            if the orchestrator is misconfigured.
        """
        # Check for required API key
        if not self.config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required but not set in configuration")
        
        # Validate Qdrant settings
        if not self.config.qdrant_url:
            raise ValueError("Qdrant URL is required but not set in configuration")
        
        if not self.config.qdrant_collection_name:
            raise ValueError("Qdrant collection name is required but not set in configuration")
        
        logger.info("Configuration validation passed")
    
    def _check_qdrant_connectivity(self) -> None:
        """
        Check basic connectivity to Qdrant vector database.
        
        This method attempts to connect to Qdrant and verify that the
        configured collection exists or that the service is at least reachable.
        
        Raises:
            ConnectionError: If Qdrant is not reachable or connection fails
        
        Note:
            A warning is logged if the collection doesn't exist yet, but
            this is not considered a fatal error as the collection might
            be created later.
        """
        try:
            # Parse Qdrant URL using proper URL parsing
            parsed_url = urlparse(self.config.qdrant_url)
            host = parsed_url.hostname or "localhost"
            port = parsed_url.port or 6333
            
            # Create a temporary client to test connectivity
            client = QdrantClient(
                host=host,
                port=port,
                api_key=self.config.qdrant_api_key,
                timeout=5.0
            )
            
            # Try to get collection info as a health check
            try:
                client.get_collection(self.config.qdrant_collection_name)
                logger.info(f"Successfully connected to Qdrant at {self.config.qdrant_url}")
            except Exception as e:
                # Collection might not exist, but we should be able to connect
                logger.warning(f"Qdrant collection '{self.config.qdrant_collection_name}' check failed: {e}")
                logger.info("Qdrant is reachable but collection may not exist yet")
                
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Qdrant at {self.config.qdrant_url}: {e}")
    
    async def run_pipeline(self, biochemical_names: List[str]) -> BatchMappingResult:
        """
        Execute the full pipeline for a list of biochemical names.
        
        This method processes multiple biochemical names sequentially,
        collecting individual results and aggregating them into a batch result.
        
        Args:
            biochemical_names: List of biochemical names to map to PubChem CIDs
            
        Returns:
            BatchMappingResult: Aggregated results containing:
                - Individual mapping results for each input name
                - Summary statistics (total processed, successes, failures)
                - Total processing time
        
        Example:
            >>> names = ["glucose", "caffeine", "aspirin"]
            >>> batch_result = await orchestrator.run_pipeline(names)
            >>> print(f"Success rate: {batch_result.get_success_rate()}%")
        
        Note:
            Processing is currently sequential. Future versions may support
            concurrent processing based on the pipeline_batch_size config.
        """
        start_time = time.time()
        logger.info(f"Starting batch pipeline for {len(biochemical_names)} biochemical names")
        
        # Handle empty input gracefully
        if not biochemical_names:
            logger.warning("Empty list provided to batch pipeline")
        
        # Process names sequentially (as per Phase 1 decision)
        results = []
        for name in biochemical_names:
            result = await self.run_single_mapping(name)
            results.append(result)
        
        # Calculate summary statistics
        successful_mappings = sum(1 for r in results if r.has_mapping())
        failed_mappings = sum(1 for r in results if not r.is_successful())
        
        # Create batch result
        batch_result = BatchMappingResult(
            total_processed=len(biochemical_names),
            successful_mappings=successful_mappings,
            failed_mappings=failed_mappings,
            results=results,
            processing_time_seconds=time.time() - start_time
        )
        
        logger.info(f"Batch pipeline completed: {batch_result.summary()}")
        return batch_result
    
    async def run_single_mapping(self, biochemical_name: str) -> PipelineMappingResult:
        """
        Execute the pipeline for a single biochemical name.
        
        This method implements the core three-stage pipeline logic:
        1. Search Qdrant for similar compound embeddings
        2. Fetch detailed annotations from PubChem for candidates
        3. Use LLM to select the best matching CID
        
        Args:
            biochemical_name: The biochemical name to map (e.g., "glucose", "vitamin C")
            
        Returns:
            PipelineMappingResult: Complete result including:
                - Final selected CID (if found)
                - Confidence level and rationale
                - Intermediate results from each stage
                - Error information (if any stage failed)
                - Processing time metrics
        
        Note:
            The method implements a "fail-fast" strategy where processing stops
            at the first error, but the result object always contains detailed
            status information about what occurred.
        """
        logger.info(f"Starting pipeline for: '{biochemical_name}'")
        start_time = time.time()
        
        # Initialize result object
        result = PipelineMappingResult(
            input_biochemical_name=biochemical_name,
            status=PipelineStatus.UNKNOWN_ERROR,  # Will be updated
            processing_details={}
        )
        
        try:
            # Stage 1: Qdrant Search
            logger.info(f"Stage 1: Searching Qdrant for '{biochemical_name}'")
            qdrant_start = time.time()
            
            try:
                # Note: The qdrant_search module handles its own client initialization
                # Using pipeline_batch_size as top_k for now (could be a separate config in future)
                qdrant_results = await search_qdrant_for_biochemical_name(
                    biochemical_name=biochemical_name,
                    top_k=self.config.pipeline_batch_size
                )
                result.processing_details["qdrant_search_time"] = time.time() - qdrant_start
                
                if not qdrant_results:
                    logger.info(f"No Qdrant hits for '{biochemical_name}'")
                    result.status = PipelineStatus.NO_QDRANT_HITS
                    result.error_message = "No similar compounds found in Qdrant vector database"
                    return result
                
                result.qdrant_results = qdrant_results
                logger.info(f"Found {len(qdrant_results)} Qdrant candidates for '{biochemical_name}'")
                
            except Exception as e:
                logger.error(f"Qdrant search failed for '{biochemical_name}': {e}")
                result.status = PipelineStatus.COMPONENT_ERROR_QDRANT
                result.error_message = f"Qdrant search error: {str(e)}"
                return result
            
            # Stage 2: PubChem Annotation
            logger.info(f"Stage 2: Fetching PubChem annotations for {len(qdrant_results)} candidates")
            pubchem_start = time.time()
            
            try:
                # Extract CIDs from Qdrant results
                cids = [item.cid for item in qdrant_results]
                
                # Fetch annotations
                annotations = await fetch_pubchem_annotations(cids)
                result.processing_details["pubchem_annotation_time"] = time.time() - pubchem_start
                
                if not annotations:
                    logger.warning(f"No PubChem annotations retrieved for '{biochemical_name}'")
                    result.status = PipelineStatus.INSUFFICIENT_ANNOTATIONS
                    result.error_message = "Failed to retrieve annotations from PubChem for any candidates"
                    return result
                
                result.pubchem_annotations = annotations
                logger.info(f"Retrieved annotations for {len(annotations)} CIDs")
                
            except Exception as e:
                logger.error(f"PubChem annotation failed for '{biochemical_name}': {e}")
                result.status = PipelineStatus.COMPONENT_ERROR_PUBCHEM
                result.error_message = f"PubChem annotation error: {str(e)}"
                return result
            
            # Stage 3: LLM Mapping
            logger.info(f"Stage 3: LLM evaluation of {len(annotations)} annotated candidates")
            llm_start = time.time()
            
            try:
                # Prepare candidates for LLM
                llm_candidates = []
                for qdrant_item in qdrant_results:
                    if qdrant_item.cid in annotations:
                        llm_candidates.append(
                            LLMCandidateInfo(
                                cid=qdrant_item.cid,
                                qdrant_score=qdrant_item.score,
                                annotations=annotations[qdrant_item.cid]
                            )
                        )
                
                if not llm_candidates:
                    logger.warning("No annotated candidates available for LLM evaluation")
                    result.status = PipelineStatus.INSUFFICIENT_ANNOTATIONS
                    result.error_message = "No candidates with annotations available for LLM evaluation"
                    return result
                
                # Call LLM mapper
                llm_choice = await select_best_cid_with_llm(
                    original_biochemical_name=biochemical_name,
                    candidates_info=llm_candidates,
                    anthropic_api_key=self.config.anthropic_api_key
                )
                result.processing_details["llm_decision_time"] = time.time() - llm_start
                
                # Handle LLM errors
                if llm_choice.error_message:
                    logger.error(f"LLM mapping failed: {llm_choice.error_message}")
                    result.status = PipelineStatus.COMPONENT_ERROR_LLM
                    result.error_message = llm_choice.error_message
                    return result
                
                # Store LLM choice
                result.llm_choice = llm_choice
                
                # Update result based on LLM decision
                if llm_choice.selected_cid is None:
                    logger.info(f"LLM found no suitable match for '{biochemical_name}'")
                    result.status = PipelineStatus.LLM_NO_MATCH
                    result.rationale = llm_choice.llm_rationale
                else:
                    # Success!
                    result.selected_cid = llm_choice.selected_cid
                    result.rationale = llm_choice.llm_rationale
                    
                    # Convert confidence score to string level
                    result.confidence = self._get_confidence_level(llm_choice.llm_confidence)
                    
                    result.status = PipelineStatus.SUCCESS
                    logger.info(f"Successfully mapped '{biochemical_name}' to CID {result.selected_cid}")
                
            except Exception as e:
                logger.error(f"LLM mapping failed for '{biochemical_name}': {e}")
                result.status = PipelineStatus.COMPONENT_ERROR_LLM
                result.error_message = f"LLM mapping error: {str(e)}"
                return result
            
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error in pipeline for '{biochemical_name}': {e}")
            result.status = PipelineStatus.UNKNOWN_ERROR
            result.error_message = f"Unexpected error: {str(e)}"
        
        finally:
            # Record total processing time
            result.processing_details["total_time"] = time.time() - start_time
            logger.info(f"Pipeline completed for '{biochemical_name}' with status: {result.status}")
        
        return result
    
    def _get_confidence_level(self, confidence_score: Optional[float]) -> Optional[str]:
        """
        Convert numerical confidence score to string level.
        
        Args:
            confidence_score: Float between 0.0 and 1.0
            
        Returns:
            String confidence level: "High", "Medium", "Low", or None
        """
        if confidence_score is None:
            return None
        
        if confidence_score >= 0.8:
            return "High"
        elif confidence_score >= 0.5:
            return "Medium"
        else:
            return "Low"


def create_orchestrator(config: Optional[PipelineConfig] = None) -> PipelineOrchestrator:
    """
    Factory function to create a PipelineOrchestrator instance.
    
    This convenience function handles configuration creation and orchestrator
    initialization, making it easy to get started with the pipeline.
    
    Args:
        config: Optional PipelineConfig. If not provided, will create from 
                environment variables using default settings.
        
    Returns:
        PipelineOrchestrator: Fully initialized and ready-to-use orchestrator
        
    Raises:
        ValueError: If configuration is invalid or required settings are missing
        ConnectionError: If required services (e.g., Qdrant) are not available
    
    Example:
        >>> # Using environment variables
        >>> orchestrator = create_orchestrator()
        >>> 
        >>> # Using custom config
        >>> config = PipelineConfig(anthropic_api_key=\"key\", qdrant_url=\"http://localhost:6333\")
        >>> orchestrator = create_orchestrator(config)
    """
    if config is None:
        from biomapper.mvp0_pipeline.pipeline_config import create_pipeline_config
        config = create_pipeline_config()
    
    return PipelineOrchestrator(config)


async def main():
    """
    Example usage of the pipeline orchestrator.
    
    This demonstrates how to use the orchestrator for both single
    and batch biochemical name mapping.
    """
    import os
    from biomapper.mvp0_pipeline.pipeline_config import create_pipeline_config
    
    # Ensure we have required environment variables for the example
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is required")
        print("Please set it before running the orchestrator:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    try:
        # Create configuration from environment
        config = create_pipeline_config()
        
        # Initialize orchestrator
        orchestrator = PipelineOrchestrator(config)
        
        # Example 1: Single biochemical name mapping
        print("\n" + "="*60)
        print("Example 1: Single Biochemical Name Mapping")
        print("="*60)
        
        test_name = "glucose"
        result = await orchestrator.run_single_mapping(test_name)
        
        print(f"\nResult for '{test_name}':")
        print(f"  Status: {result.status}")
        print(f"  Selected CID: {result.selected_cid}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Summary: {result.summary()}")
        
        if result.processing_details:
            print("\n  Processing times:")
            for key, value in result.processing_details.items():
                if key.endswith("_time"):
                    print(f"    {key}: {value:.2f}s")
        
        # Example 2: Batch mapping
        print("\n" + "="*60)
        print("Example 2: Batch Biochemical Name Mapping")
        print("="*60)
        
        test_names = ["caffeine", "aspirin", "vitamin C", "unknown_compound_xyz"]
        batch_result = await orchestrator.run_pipeline(test_names)
        
        print(f"\n{batch_result.summary()}")
        print(f"Total processing time: {batch_result.processing_time_seconds:.2f}s")
        
        # Show individual results
        print("\nIndividual results:")
        for result in batch_result.results:
            status_symbol = "✓" if result.has_mapping() else "✗"
            print(f"  {status_symbol} {result.input_biochemical_name}: {result.status}")
            if result.selected_cid:
                print(f"    → CID {result.selected_cid} ({result.confidence} confidence)")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
    except ConnectionError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Set up basic logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the example
    asyncio.run(main())