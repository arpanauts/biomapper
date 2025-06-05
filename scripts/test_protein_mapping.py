import asyncio
import logging
import os
from pathlib import Path

from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings # To get the DB path consistently

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main function to test protein mapping."""
    logger.info("Starting protein mapping test...")

    # Construct the path to metamapper.db relative to the project root
    # This ensures it uses the same DB as populate_metamapper_db.py
    # settings.metamapper_db_url is already in the format sqlite+aiosqlite:///...
    metamapper_db_path = settings.metamapper_db_url
    logger.info(f"Using Metamapper DB: {metamapper_db_path}")

    # Ensure the database file exists (it should after populate_metamapper_db.py)
    # Extracting file path from URL like 'sqlite+aiosqlite:///path/to/db.sqlite'
    db_file_path_str = metamapper_db_path.split('///', 1)[-1]
    if not Path(db_file_path_str).exists():
        logger.error(f"Database file not found at {db_file_path_str}. Please run populate_metamapper_db.py first.")
        return

    # Initialize MappingExecutor directly. The create method was for an older version or a specific setup.
    # The __init__ method handles DB setup now.
    try:
        mapping_executor = MappingExecutor(
            metamapper_db_url=metamapper_db_path,
            mapping_cache_db_url=settings.cache_db_url # Ensure cache DB is also passed
        )
        # The new __init__ might not be async, and table creation is handled internally or separately.
        # We might need to call an explicit init_db method if it exists, or ensure populate_metamapper_db did it.
        # For now, assume __init__ is sufficient for setup based on recent changes.
        logger.info("MappingExecutor initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize MappingExecutor: {e}", exc_info=True)
        return

    # --- Test Case: HPA OSP Protein ID to UKBB Protein Assay ID ---
    # !!! IMPORTANT: Replace these with actual HPA OSP Protein IDs from your hpa_osps.csv file !!!
    # These IDs should be from the 'gene' column of hpa_osps.csv
    hpa_protein_ids_to_map = ["ENSG00000121410", "ENSG00000171720"] # Example: HGNC:OAS1, HGNC:ACE2 (using Ensembl IDs as placeholders)
    
    source_ontology = "HPA_OSP_PROTEIN_ID_ONTOLOGY"
    target_ontology = "UKBB_PROTEIN_ASSAY_ID_ONTOLOGY"

    logger.info(f"Attempting to map {len(hpa_protein_ids_to_map)} IDs from {source_ontology} to {target_ontology}")
    logger.info(f"Input IDs: {hpa_protein_ids_to_map}")

    try:
        # The primary method to call for mapping
        mapping_results = await mapping_executor.execute_mapping(
            input_identifiers=hpa_protein_ids_to_map,
            source_ontology_type=source_ontology,
            target_ontology_type=target_ontology,
            source_endpoint_name="HPA_OSP_PROTEIN",
            target_endpoint_name="UKBB_PROTEIN",
            # These are often defaults or controlled by the executor's init, but can be specified:
            # enable_iterative_mapping=True, 
            # enable_secondary_lookup=True,
            # max_hop_count=None, # Default is usually no limit or a high limit
            # min_confidence=0.0 # Default
        )

        logger.info("Mapping process completed.")
        logger.info("--- Mapping Results ---")
        if mapping_results:
            for source_id, result_data in mapping_results.items():
                logger.info(f"  Source ID: {source_id}")
                if result_data:
                    logger.info(f"    Mapped To: {result_data.get('target_identifiers')}")
                    logger.info(f"    Status: {result_data.get('status')}")
                    logger.info(f"    Confidence: {result_data.get('confidence_score')}")
                    logger.info(f"    Hops: {result_data.get('hop_count')}")
                    # logger.info(f"    Provenance: {result_data.get('mapping_path_details')}") # Can be verbose
                else:
                    logger.info("    No mapping found or error during mapping for this ID.")
        else:
            logger.info("No results returned from mapping_executor.execute_mapping.")

    except Exception as e:
        logger.error(f"An error occurred during mapping: {e}", exc_info=True)
    finally:
        # Clean up Langfuse resources if any were created by the executor
        if hasattr(mapping_executor, '_langfuse_tracker') and mapping_executor._langfuse_tracker:
            try:
                await asyncio.to_thread(mapping_executor._langfuse_tracker.flush)
                await asyncio.to_thread(mapping_executor._langfuse_tracker.shutdown, timeout_seconds=5)
                logger.info("Langfuse tracker flushed and shut down.")
            except Exception as e:
                logger.error(f"Error shutting down Langfuse tracker: {e}")
        
        # Properly close database connections
        if hasattr(mapping_executor, 'async_metamapper_engine'):
            await mapping_executor.async_metamapper_engine.dispose()
            logger.info("Metamapper engine disposed.")
        if hasattr(mapping_executor, 'async_cache_engine'): # if cache was initialized
            await mapping_executor.async_cache_engine.dispose()
            logger.info("Cache engine disposed.")

if __name__ == "__main__":
    asyncio.run(main())
