#!/usr/bin/env python
"""
Full UKBB to HPA Protein Mapping Script - Enhanced Bidirectional Strategy

This script processes a full UKBB protein dataset through the optimized
UKBB_TO_HPA_BIDIRECTIONAL_OPTIMIZED strategy using the EnhancedMappingExecutor
with robust execution features.

Key improvements over the original strategy:
- Direct UniProt matching (no initial conversion needed)
- Bidirectional resolution for maximum coverage
- Context-based tracking of matched/unmatched identifiers
- Composite identifier handling built-in

Enhanced features:
- Checkpointing for resumable execution
- Retry logic for external API calls
- Progress tracking and reporting
- Batch processing with configurable sizes

Usage:
    1. Ensure metamapper.db is populated: python scripts/populate_metamapper_db.py
    2. Ensure the biomapper Poetry environment is active
    3. Run: python scripts/main_pipelines/run_full_ukbb_hpa_mapping_bidirectional.py [options]
    
Options:
    --checkpoint: Enable checkpoint saving (default: True)
    --batch-size N: Number of identifiers per batch (default: 250)
    --max-retries N: Maximum retries per operation (default: 3)
    --no-progress: Disable progress reporting
    
The script will automatically:
- Load UKBB protein data (UniProt IDs) from the configured endpoint
- Execute the bidirectional mapping strategy with robust features
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
from biomapper.core.mapping_executor_enhanced import EnhancedMappingExecutor
from biomapper.config import settings

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

# Checkpoint directory for robust execution
CHECKPOINT_DIR = "/home/ubuntu/biomapper/data/checkpoints"

# Strategy name to execute - using the EFFICIENT bidirectional strategy
# Note: The OPTIMIZED strategy has a design flaw where it processes ALL unmatched HPA proteins,
# causing timeouts even with small datasets. Use EFFICIENT instead.
STRATEGY_NAME = "UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT"

# Endpoint names as defined in metamapper.db (from protein_config.yaml)
SOURCE_ENDPOINT_NAME = "UKBB_PROTEIN"
TARGET_ENDPOINT_NAME = "HPA_OSP_PROTEIN"

# ============================================================================
# MAIN MAPPING FUNCTION
# ============================================================================


async def run_full_mapping(checkpoint_enabled: bool = True, batch_size: int = 250, 
                          max_retries: int = 3, enable_progress: bool = True):
    """
    Main function to execute the full UKBB to HPA protein mapping using the enhanced bidirectional strategy.
    
    Args:
        checkpoint_enabled: Enable checkpoint saving for resumable execution
        batch_size: Number of identifiers per batch for processing
        max_retries: Maximum retry attempts for failed operations
        enable_progress: Enable progress reporting callbacks
    """
    start_time = datetime.now()
    execution_id = f"ukbb_hpa_bidirectional_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Starting ENHANCED BIDIRECTIONAL UKBB to HPA protein mapping at {start_time}")
    logger.info("=" * 80)
    logger.info("Using enhanced bidirectional strategy with:")
    logger.info("- Direct UniProt matching (no conversion needed)")
    logger.info("- Composite identifier handling")
    logger.info("- Bidirectional resolution for maximum coverage")
    logger.info("- Context-based tracking throughout")
    logger.info("")
    logger.info("Enhanced features:")
    logger.info(f"- Checkpointing: {'Enabled' if checkpoint_enabled else 'Disabled'}")
    logger.info(f"- Batch size: {batch_size}")
    logger.info(f"- Max retries: {max_retries}")
    logger.info(f"- Progress tracking: {'Enabled' if enable_progress else 'Disabled'}")
    logger.info(f"- Execution ID: {execution_id}")
    logger.info("=" * 80)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_RESULTS_DIR, exist_ok=True)
    logger.info(f"Output results will be saved to: {OUTPUT_RESULTS_FILE_PATH}")
    
    # Set DATA_DIR environment variable if not already set
    if 'DATA_DIR' not in os.environ:
        os.environ['DATA_DIR'] = DEFAULT_DATA_DIR
        logger.info(f"Set DATA_DIR environment variable to: {DEFAULT_DATA_DIR}")
    
    # Set OUTPUT_DIR environment variable for the strategy
    if 'OUTPUT_DIR' not in os.environ:
        os.environ['OUTPUT_DIR'] = OUTPUT_RESULTS_DIR
        logger.info(f"Set OUTPUT_DIR environment variable to: {OUTPUT_RESULTS_DIR}")
    
    # Initialize variables
    executor = None
    input_identifiers = []
    
    try:
        # Initialize EnhancedMappingExecutor with robust features
        logger.info("Initializing EnhancedMappingExecutor with robust features...")
        executor = await EnhancedMappingExecutor.create(
            metamapper_db_url=settings.metamapper_db_url,
            mapping_cache_db_url=settings.cache_db_url,
            echo_sql=False,
            enable_metrics=True,
            # Enhanced features
            checkpoint_enabled=checkpoint_enabled,
            checkpoint_dir=CHECKPOINT_DIR,
            batch_size=batch_size,
            max_retries=max_retries,
            retry_delay=2  # 2 second delay between retries
        )
        logger.info("EnhancedMappingExecutor created successfully with robust features")
        
        # Add progress tracking if enabled
        if enable_progress:
            def progress_callback(progress_data: Dict[str, Any]):
                """Handle progress updates from the executor."""
                if progress_data['type'] == 'batch_complete':
                    logger.info(
                        f"Progress: {progress_data['total_processed']}/{progress_data['total_count']} "
                        f"({progress_data['progress_percent']:.1f}%) - "
                        f"{progress_data['processor']}"
                    )
                elif progress_data['type'] == 'checkpoint_saved':
                    logger.info(f"Checkpoint saved: {progress_data['state_summary']}")
                elif progress_data['type'] == 'retry_attempt':
                    logger.warning(
                        f"Retry {progress_data['attempt']}/{progress_data['max_attempts']} "
                        f"for {progress_data['operation']}"
                    )
            
            executor.add_progress_callback(progress_callback)
            logger.info("Progress tracking enabled")
        
        # Check if strategy exists using new API
        logger.info(f"Checking if strategy '{STRATEGY_NAME}' exists in database...")
        strategy = await executor.get_strategy(STRATEGY_NAME)
        
        if not strategy:
            raise ValueError(
                f"Strategy '{STRATEGY_NAME}' not found in database.\n"
                f"Please run: python scripts/populate_metamapper_db.py"
            )
        
        logger.info(f"Strategy '{STRATEGY_NAME}' found in database")
        
        # Get the source ontology type from the strategy
        source_ontology_type = strategy.default_source_ontology_type
        logger.info(f"Strategy uses source ontology type: {source_ontology_type}")
        logger.info(f"Note: This is UniProt directly - no conversion needed!")
        
        # Load input identifiers from the source endpoint using new API
        logger.info(f"Loading UniProt identifiers from source endpoint '{SOURCE_ENDPOINT_NAME}'...")
        input_identifiers = await executor.load_endpoint_identifiers(
            endpoint_name=SOURCE_ENDPOINT_NAME,
            ontology_type=source_ontology_type
        )
        
        if not input_identifiers:
            logger.warning("No identifiers found in the source endpoint. Exiting.")
            return
        
        # Check for existing checkpoint
        checkpoint_state = await executor.load_checkpoint(execution_id)
        if checkpoint_state:
            logger.info("Found existing checkpoint - attempting to resume execution...")
        
        # Execute mapping strategy with robust features
        logger.info(f"Executing enhanced bidirectional mapping strategy on {len(input_identifiers)} identifiers...")
        logger.info("Using robust execution with checkpointing and retry logic...")
        logger.info("This may take some time for large datasets...")
        
        result = await executor.execute_yaml_strategy_robust(
            strategy_name=STRATEGY_NAME,
            input_identifiers=input_identifiers,
            source_endpoint_name=SOURCE_ENDPOINT_NAME,
            target_endpoint_name=TARGET_ENDPOINT_NAME,
            execution_id=execution_id,
            resume_from_checkpoint=checkpoint_enabled,
            use_cache=True  # Enable caching for full runs
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
        
        # Enhanced summary with bidirectional tracking and robust execution info
        enhanced_summary = {
            'execution_info': {
                'strategy': STRATEGY_NAME,
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - start_time).total_seconds(),
                'execution_id': execution_id,
                'robust_features': {
                    'checkpoint_enabled': checkpoint_enabled,
                    'checkpoint_used': checkpoint_state is not None,
                    'batch_size': batch_size,
                    'max_retries': max_retries,
                    'progress_tracking': enable_progress
                }
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
            'robust_execution_metadata': result.get('robust_execution', {}),
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
        
        # Log robust execution information
        robust_info = enhanced_summary['execution_info']['robust_features']
        logger.info(f"\nRobust execution features:")
        logger.info(f"  Checkpointing: {'Used' if robust_info['checkpoint_used'] else 'Available' if robust_info['checkpoint_enabled'] else 'Disabled'}")
        logger.info(f"  Batch processing: {robust_info['batch_size']} identifiers per batch")
        logger.info(f"  Retry logic: {robust_info['max_retries']} max attempts")
        logger.info(f"  Progress tracking: {'Enabled' if robust_info['progress_tracking'] else 'Disabled'}")
        
        # Log robust execution metadata from the strategy result
        if result.get('robust_execution'):
            robust_meta = result['robust_execution']
            logger.info(f"  Actual execution time: {robust_meta.get('execution_time', 'N/A')} seconds")
            logger.info(f"  Retries configured: {robust_meta.get('retries_configured', 'N/A')}")
        
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
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Enhanced UKBB to HPA bidirectional mapping with robust execution"
    )
    parser.add_argument(
        "--no-checkpoint", 
        action="store_true", 
        help="Disable checkpoint saving"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=250, 
        help="Number of identifiers per batch (default: 250)"
    )
    parser.add_argument(
        "--max-retries", 
        type=int, 
        default=3, 
        help="Maximum retry attempts for failed operations (default: 3)"
    )
    parser.add_argument(
        "--no-progress", 
        action="store_true", 
        help="Disable progress reporting"
    )
    
    args = parser.parse_args()
    
    try:
        # Run the main async function with parsed arguments
        asyncio.run(run_full_mapping(
            checkpoint_enabled=not args.no_checkpoint,
            batch_size=args.batch_size,
            max_retries=args.max_retries,
            enable_progress=not args.no_progress
        ))
        logger.info("Script completed successfully")
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)