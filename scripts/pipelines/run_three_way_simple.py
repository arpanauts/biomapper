#!/usr/bin/env python3
"""
Run simplified three-way metabolomics analysis via Biomapper API.

This client replaces the 365-line direct execution script with 5 phases.
All pipeline orchestration is now handled by the API server.
"""
import asyncio
import argparse
from pathlib import Path
from biomapper_client import run_with_progress, parse_parameters


async def main():
    parser = argparse.ArgumentParser(
        description="Run simplified three-way metabolomics pipeline"
    )
    parser.add_argument(
        '--strategy',
        default='three_way_metabolomics_simple',
        help='Strategy name (default: three_way_metabolomics_simple)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path.cwd() / "data" / "results" / "three_way_simple",
        help='Output directory for results'
    )
    parser.add_argument(
        '--parameters',
        type=str,
        help='JSON string or file path with parameter overrides'
    )
    parser.add_argument(
        '--phase',
        choices=['data_loading', 'nightingale', 'progressive', 'integration', 'analysis', 'all'],
        default='all',
        help='Run specific phase or all phases'
    )
    
    args = parser.parse_args()
    
    # Parse parameters
    parameters = parse_parameters(args.parameters)
    
    # Add configuration
    parameters.update({
        'output_dir': str(args.output_dir),
        'phase': args.phase,
        # Default dataset paths (these can be overridden via --parameters)
        'datasets': parameters.get('datasets', {
            'arivale': 'data/metabolomics/arivale_metabolomics_with_metadata.tsv',
            'ukbb': 'data/metabolomics/ukbb_nmr_metabolomics_metadata_clean.tsv',
            'qin': 'data/metabolomics/qin_metabolomics_metadata.tsv'
        })
    })
    
    # Execute with progress tracking
    result = run_with_progress(
        strategy_name=args.strategy,
        parameters=parameters
    )
    
    # Report results
    if result.get('success'):
        print("\n✓ Three-way metabolomics pipeline completed successfully")
        print(f"Results saved to: {args.output_dir}")
    else:
        print(f"\n✗ Pipeline failed: {result.get('error', 'Unknown error')}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())