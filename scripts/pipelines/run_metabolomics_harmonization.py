#!/usr/bin/env python3
"""
Execute metabolomics harmonization pipeline via Biomapper API.

This is a simplified API client that replaces the 676-line direct execution script.
All orchestration logic is now handled by the API server.
"""
import asyncio
import argparse
import sys
from pathlib import Path
from biomapper_client import (
    BiomapperClient,
    parse_parameters,
    print_result,
    ExecutionOptions
)


async def main():
    parser = argparse.ArgumentParser(
        description="Run metabolomics harmonization pipeline"
    )
    parser.add_argument(
        '--strategy',
        default='metabolomics_progressive_enhancement',
        help='Strategy name or path to YAML file'
    )
    parser.add_argument(
        '--parameters',
        type=str,
        help='JSON string or file path with parameter overrides'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch execution progress in real-time'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Directory for output files'
    )
    parser.add_argument(
        '--skip-setup',
        action='store_true',
        help='Skip Qdrant setup (passed as parameter to strategy)'
    )
    parser.add_argument(
        '--skip-qdrant',
        action='store_true',
        help='Skip all Qdrant-related actions'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    parser.add_argument(
        '--stage',
        choices=['baseline', 'enrichment', 'vector', 'semantic', 'all'],
        default='all',
        help='Run specific stage or all stages'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed output'
    )
    
    args = parser.parse_args()
    
    # Initialize client
    async with BiomapperClient() as client:
        # Parse parameters if provided
        parameters = parse_parameters(args.parameters)
        
        # Add CLI flags to parameters
        if args.output_dir:
            parameters['output_dir'] = str(args.output_dir)
        if args.skip_setup:
            parameters['skip_setup'] = True
        if args.skip_qdrant:
            parameters['skip_qdrant'] = True
        if args.stage != 'all':
            parameters['stage'] = args.stage
        
        # Set execution options
        options = ExecutionOptions(
            checkpoint_enabled=True,
            retry_failed_steps=True,
            debug=args.debug
        )
        
        # Execute strategy
        try:
            if args.watch:
                print(f"Executing strategy: {args.strategy}")
                print("Note: Real-time progress tracking will be available in a future update")
            
            # Add options to context
            context = parameters.copy()
            context['options'] = options.to_dict()
            
            # Execute the strategy
            result = await client.execute_strategy(args.strategy, context)
            
            # Print results
            print_result(result, verbose=args.verbose)
            
            if not result.get('success'):
                sys.exit(1)
                
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if args.debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())