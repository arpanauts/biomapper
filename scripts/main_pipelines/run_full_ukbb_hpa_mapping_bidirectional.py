#!/usr/bin/env python
"""
Full UKBB to HPA Protein Mapping Script - Bidirectional Strategy

This script processes a full UKBB protein dataset through the optimized
UKBB_TO_HPA_BIDIRECTIONAL_OPTIMIZED strategy using the MappingExecutor.

Key improvements over the original strategy:
- Direct UniProt matching (no initial conversion needed)
- Bidirectional resolution for maximum coverage
- Context-based tracking of matched/unmatched identifiers
- Composite identifier handling built-in

Usage:
    1. Ensure metamapper.db is populated: python scripts/populate_metamapper_db.py
    2. Ensure the biomapper Poetry environment is active
    3. Run: python scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py
    
The script will automatically:
- Load UKBB protein data (UniProt IDs) from the configured endpoint
- Execute the bidirectional mapping strategy
- Save comprehensive results to /home/ubuntu/biomapper/data/results/
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

# Add project root to sys.path for module resolution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from biomapper.core.mapping_executor import MappingExecutor
from biomapper.config import settings
from biomapper.db.models import PropertyExtractionConfig
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from biomapper.db.models import MappingStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION VARIABLES
# ============================================================================

# Output configuration
OUTPUT_RESULTS_DIR = "/home/ubuntu/biomapper/data/results/"
OUTPUT_RESULTS_FILENAME = "full_ukbb_to_hpa_mapping_bidirectional_results.csv"
OUTPUT_RESULTS_FILE_PATH = os.path.join(OUTPUT_RESULTS_DIR, OUTPUT_RESULTS_FILENAME)

# Summary file for tracking strategy performance
SUMMARY_FILENAME = "full_ukbb_to_hpa_mapping_bidirectional_summary.json"
SUMMARY_FILE_PATH = os.path.join(OUTPUT_RESULTS_DIR, SUMMARY_FILENAME)

# Default data directory (set as environment variable if not already set)
DEFAULT_DATA_DIR = "/home/ubuntu/biomapper/data"

# Strategy name to execute - using the new bidirectional strategy
STRATEGY_NAME = "UKBB_TO_HPA_BIDIRECTIONAL_OPTIMIZED"

# Endpoint names as defined in metamapper.db (from protein_config.yaml)
SOURCE_ENDPOINT_NAME = "UKBB_PROTEIN"
TARGET_ENDPOINT_NAME = "HPA_OSP_PROTEIN"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def check_strategy_exists(executor: MappingExecutor, strategy_name: str) -> bool:
    """
    Check if a strategy exists in the metamapper database.
    
    Args:
        executor: MappingExecutor instance
        strategy_name: Name of the strategy to check
        
    Returns:
        True if strategy exists, False otherwise
    """
    try:
        async with executor.async_metamapper_session() as session:
            stmt = select(MappingStrategy).where(MappingStrategy.name == strategy_name)
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            return strategy is not None
    except Exception as e:
        logger.error(f"Error checking for strategy {strategy_name}: {e}")
        return False


# ============================================================================
# MAIN MAPPING FUNCTION
# ============================================================================

async def get_column_for_ontology_type(executor: MappingExecutor, endpoint_name: str, ontology_type: str) -> str:
    """
    Get the column name for a given ontology type from an endpoint's property configuration.
    
    Args:
        executor: MappingExecutor instance
        endpoint_name: Name of the endpoint
        ontology_type: Ontology type to look up
        
    Returns:
        Column name for the ontology type
    """
    async with executor.async_metamapper_session() as session:
        from biomapper.db.models import Endpoint, EndpointPropertyConfig
        
        # Get the endpoint
        stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
        result = await session.execute(stmt)
        endpoint = result.scalar_one_or_none()
        
        if not endpoint:
            raise ValueError(f"Endpoint '{endpoint_name}' not found in database")
        
        # Get the property config for the ontology type
        stmt = select(EndpointPropertyConfig).where(
            EndpointPropertyConfig.endpoint_id == endpoint.id,
            EndpointPropertyConfig.ontology_type == ontology_type
        )
        result = await session.execute(stmt)
        property_config = result.scalar_one_or_none()
        
        if not property_config:
            raise ValueError(f"No property configuration found for ontology type '{ontology_type}' in endpoint '{endpoint_name}'")
        
        # Get the extraction config to find the column name
        stmt = select(PropertyExtractionConfig).where(
            PropertyExtractionConfig.id == property_config.property_extraction_config_id
        )
        result = await session.execute(stmt)
        extraction_config = result.scalar_one_or_none()
        
        if not extraction_config:
            raise ValueError(f"No extraction configuration found for property config ID {property_config.property_extraction_config_id}")
        
        # Parse the extraction pattern to get the column name
        pattern_data = json.loads(extraction_config.extraction_pattern)
        column_name = pattern_data.get('column')
        if not column_name:
            raise ValueError(f"No 'column' field found in extraction pattern: {extraction_config.extraction_pattern}")
        return column_name


async def load_identifiers_from_endpoint(executor: MappingExecutor, endpoint_name: str, ontology_type: str) -> List[str]:
    """
    Load identifiers from an endpoint using its configuration in metamapper.db.
    
    For the bidirectional strategy, we load UniProt IDs directly.
    
    Args:
        executor: MappingExecutor instance
        endpoint_name: Name of the endpoint to load from
        ontology_type: Ontology type of the identifiers to load
        
    Returns:
        List of unique identifiers
    """
    try:
        # First get the column name for the ontology type
        column_name = await get_column_for_ontology_type(executor, endpoint_name, ontology_type)
        logger.info(f"Ontology type '{ontology_type}' maps to column '{column_name}'")
        
        # Get endpoint configuration from metamapper.db
        async with executor.async_metamapper_session() as session:
            from biomapper.db.models import Endpoint
            
            stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
            result = await session.execute(stmt)
            endpoint = result.scalar_one_or_none()
            
            if not endpoint:
                raise ValueError(f"Endpoint '{endpoint_name}' not found in database")
            
            # Parse connection details (it's a JSON string)
            connection_details = json.loads(endpoint.connection_details)
            file_path = connection_details.get('file_path', '')
            delimiter = connection_details.get('delimiter', ',')
            
            # Handle environment variable substitution
            if '${DATA_DIR}' in file_path:
                data_dir = os.environ.get('DATA_DIR', DEFAULT_DATA_DIR)
                file_path = file_path.replace('${DATA_DIR}', data_dir)
            
            logger.info(f"Loading identifiers from endpoint '{endpoint_name}'")
            logger.info(f"File path: {file_path}")
            
            # Load the file
            if endpoint.type == 'file_tsv':
                df = pd.read_csv(file_path, sep=delimiter)
            elif endpoint.type == 'file_csv':
                df = pd.read_csv(file_path, sep=delimiter)
            else:
                raise ValueError(f"Unsupported endpoint type: {endpoint.type}")
            
            logger.info(f"Loaded dataframe with shape: {df.shape}")
            
            # Extract unique identifiers
            if column_name not in df.columns:
                raise KeyError(
                    f"Column '{column_name}' not found in {endpoint_name} data.\n"
                    f"Available columns: {list(df.columns)}"
                )
            
            identifiers = df[column_name].dropna().unique().tolist()
            logger.info(f"Found {len(identifiers)} unique identifiers in column '{column_name}'")
            
            # Log sample of identifiers including any composites
            sample_ids = identifiers[:10]
            composite_count = sum(1 for id in identifiers if '_' in str(id))
            logger.info(f"Sample identifiers: {sample_ids}")
            logger.info(f"Composite identifiers found: {composite_count} (with '_' delimiter)")
            
            return identifiers
            
    except Exception as e:
        logger.error(f"Error loading identifiers from endpoint {endpoint_name}: {e}")
        raise


async def run_full_mapping():
    """
    Main function to execute the full UKBB to HPA protein mapping using the bidirectional strategy.
    """
    start_time = datetime.now()
    logger.info(f"Starting BIDIRECTIONAL UKBB to HPA protein mapping at {start_time}")
    logger.info("=" * 80)
    logger.info("Using optimized bidirectional strategy with:")
    logger.info("- Direct UniProt matching (no conversion needed)")
    logger.info("- Composite identifier handling")
    logger.info("- Bidirectional resolution for maximum coverage")
    logger.info("- Context-based tracking throughout")
    logger.info("=" * 80)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)
    logger.info(f"Output results will be saved to: {OUTPUT_RESULTS_FILE_PATH}")
    
    # Set DATA_DIR environment variable if not already set
    if 'DATA_DIR' not in os.environ:
        os.environ['DATA_DIR'] = DEFAULT_DATA_DIR
        logger.info(f"Set DATA_DIR environment variable to: {DEFAULT_DATA_DIR}")
    
    # Initialize variables
    executor = None
    input_identifiers = []
    
    try:
        # Initialize MappingExecutor
        logger.info("Initializing MappingExecutor...")
        executor = await MappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True
        )
        logger.info("MappingExecutor created successfully")
        
        # Check if strategy exists
        logger.info(f"Checking if strategy '{STRATEGY_NAME}' exists in database...")
        strategy_exists = await check_strategy_exists(executor, STRATEGY_NAME)
        
        if not strategy_exists:
            raise ValueError(
                f"Strategy '{STRATEGY_NAME}' not found in database.\n"
                f"Please run: python scripts/populate_metamapper_db.py"
            )
        
        logger.info(f"Strategy '{STRATEGY_NAME}' found in database")
        
        # Get the source ontology type from the strategy configuration
        async with executor.async_metamapper_session() as session:
            stmt = select(MappingStrategy).where(MappingStrategy.name == STRATEGY_NAME)
            result = await session.execute(stmt)
            strategy = result.scalar_one_or_none()
            
            source_ontology_type = strategy.default_source_ontology_type
            logger.info(f"Strategy uses source ontology type: {source_ontology_type}")
            logger.info(f"Note: This is UniProt directly - no conversion needed!")
        
        # Load input identifiers from the source endpoint
        logger.info(f"Loading UniProt identifiers from source endpoint '{SOURCE_ENDPOINT_NAME}'...")
        input_identifiers = await load_identifiers_from_endpoint(
            executor=executor,
            endpoint_name=SOURCE_ENDPOINT_NAME,
            ontology_type=source_ontology_type
        )
        
        if not input_identifiers:
            logger.warning("No identifiers found in the source endpoint. Exiting.")
            return
        
        # Execute mapping strategy
        logger.info(f"Executing bidirectional mapping strategy on {len(input_identifiers)} identifiers...")
        logger.info("This may take some time for large datasets...")
        
        result = await executor.execute_yaml_strategy(
            strategy_name=STRATEGY_NAME,
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
            input_identifiers=input_identifiers,
            use_cache=True,  # Enable caching for full runs
            progress_callback=lambda curr, total, status: logger.info(
                f"Progress: {curr}/{total} - {status}"
            )
        )
        
        logger.info("Mapping execution completed")
        
        # Process and save results
        logger.info("Processing mapping results...")
        
        # Extract context information for bidirectional tracking
        context = result.get('context', {})
        direct_matches = context.get('direct_matches', [])
        all_matches = context.get('all_matches', [])
        unmatched_ukbb = context.get('unmatched_ukbb', [])
        unmatched_hpa = context.get('unmatched_hpa', [])
        final_unmatched = context.get('final_unmatched', {})
        
        # Log context-based results
        logger.info(f"\nContext-based tracking results:")
        logger.info(f"- Direct UniProt matches: {len(direct_matches)}")
        logger.info(f"- Total matches after resolution: {len(all_matches)}")
        logger.info(f"- Unmatched UKBB after all steps: {len(unmatched_ukbb) if isinstance(unmatched_ukbb, list) else 'N/A'}")
        logger.info(f"- Unmatched HPA: {len(unmatched_hpa) if isinstance(unmatched_hpa, list) else 'N/A'}")
        
        # The execute_yaml_strategy returns results in 'results' key
        results_dict = result.get('results', {})
        final_identifiers = set(result.get('final_identifiers', []))
        output_rows = []
        
        # Get step results for parsing
        step_results = result.get('summary', {}).get('step_results', [])
        
        # Process each input identifier
        for input_id in input_identifiers:
            # Default values
            final_mapped_id = None
            mapping_status = 'UNMAPPED'
            mapping_method = 'Unknown'
            confidence = 0.0
            
            # Check if this ID has results
            if input_id in results_dict:
                mapping_result = results_dict[input_id]
                all_mapped_values = mapping_result.get('all_mapped_values', [])
                
                # Check if this identifier made it to the final set
                if all_mapped_values and any(val in final_identifiers for val in all_mapped_values):
                    # Successfully mapped
                    final_mapped_id = all_mapped_values[-1]  # Last value is the HPA gene
                    mapping_status = 'MAPPED'
                    
                    # Determine mapping method from context
                    if input_id in [m[0] for m in direct_matches if isinstance(m, tuple)]:
                        mapping_method = 'DIRECT_MATCH'
                        confidence = 1.0
                    elif input_id in all_matches:
                        mapping_method = 'RESOLVED_MATCH'
                        confidence = 0.9
                    else:
                        mapping_method = 'INDIRECT_MATCH'
                        confidence = 0.8
                else:
                    # Not mapped
                    mapping_status = 'UNMAPPED'
                    mapping_method = 'NO_MATCH_FOUND'
            
            output_rows.append({
                'Input_UKBB_UniProt_ID': input_id,
                'Final_Mapped_HPA_Gene': final_mapped_id,
                'Mapping_Status': mapping_status,
                'Mapping_Method': mapping_method,
                'Confidence': confidence,
                'Is_Composite': '_' in str(input_id)
            })
        
        # Create DataFrame and save to CSV
        output_df = pd.DataFrame(output_rows)
        output_df.to_csv(OUTPUT_RESULTS_FILE_PATH, index=False)
        logger.info(f"Results saved to: {OUTPUT_RESULTS_FILE_PATH}")
        
        # Create comprehensive summary
        summary = result.get('summary', {})
        
        # Enhanced summary with bidirectional tracking
        enhanced_summary = {
            'execution_info': {
                'strategy': STRATEGY_NAME,
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            },
            'input_analysis': {
                'total_input': len(input_identifiers),
                'composite_identifiers': sum(1 for id in input_identifiers if '_' in str(id)),
                'unique_identifiers': len(set(input_identifiers))
            },
            'mapping_results': {
                'direct_matches': len(direct_matches),
                'resolved_matches': len(all_matches) - len(direct_matches) if len(all_matches) > len(direct_matches) else 0,
                'total_mapped': len([r for r in output_rows if r['Mapping_Status'] == 'MAPPED']),
                'total_unmapped': len([r for r in output_rows if r['Mapping_Status'] == 'UNMAPPED'])
            },
            'step_performance': [],
            'mapping_methods': output_df['Mapping_Method'].value_counts().to_dict() if 'Mapping_Method' in output_df.columns else {},
            'original_summary': summary
        }
        
        # Add step performance details
        for step in step_results:
            enhanced_summary['step_performance'].append({
                'step_id': step.get('step_id'),
                'action_type': step.get('action_type'),
                'success': step.get('success', False),
                'input_count': step.get('input_count', 0),
                'output_count': step.get('output_count', 0),
                'duration': step.get('duration', 0)
            })
        
        # Save enhanced summary
        with open(SUMMARY_FILE_PATH, 'w') as f:
            json.dump(enhanced_summary, f, indent=2)
        logger.info(f"Enhanced summary saved to: {SUMMARY_FILE_PATH}")
        
        # Log summary statistics
        logger.info("=" * 80)
        logger.info("MAPPING SUMMARY:")
        logger.info(f"Total input identifiers: {enhanced_summary['input_analysis']['total_input']}")
        logger.info(f"Composite identifiers: {enhanced_summary['input_analysis']['composite_identifiers']}")
        logger.info(f"Direct matches: {enhanced_summary['mapping_results']['direct_matches']}")
        logger.info(f"Resolved matches: {enhanced_summary['mapping_results']['resolved_matches']}")
        logger.info(f"Total successfully mapped: {enhanced_summary['mapping_results']['total_mapped']}")
        logger.info(f"Total unmapped: {enhanced_summary['mapping_results']['total_unmapped']}")
        
        # Mapping method breakdown
        if enhanced_summary['mapping_methods']:
            logger.info("\nMapping method breakdown:")
            for method, count in enhanced_summary['mapping_methods'].items():
                logger.info(f"  {method}: {count}")
        
        # Calculate execution time
        logger.info(f"\nTotal execution time: {enhanced_summary['execution_info']['duration_seconds']:.2f} seconds")
        logger.info("=" * 80)
        
        # Compare with original strategy (if we have previous results)
        logger.info("\nStrategy comparison notes:")
        logger.info("- Original: Convert → Resolve → Filter → Convert (4 conversions)")
        logger.info("- Bidirectional: Match → Resolve Forward → Resolve Reverse → Convert (1 conversion)")
        logger.info("- Expected benefits: Faster execution, better coverage, clearer tracking")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except KeyError as e:
        logger.error(f"Column not found error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during mapping: {e}", exc_info=True)
        raise
    finally:
        # Clean up resources
        if executor:
            logger.info("Disposing MappingExecutor...")
            await executor.async_dispose()
            logger.info("MappingExecutor disposed")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        # Run the main async function
        asyncio.run(run_full_mapping())
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)