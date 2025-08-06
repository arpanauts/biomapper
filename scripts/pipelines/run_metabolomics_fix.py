#!/usr/bin/env python3
"""
Execute metabolomics fix pipeline via Biomapper API.

This simplified client replaces the 239-line direct execution script.
"""
import asyncio
import argparse
import sys
from pathlib import Path
from biomapper_client import run_strategy, parse_parameters, print_result


async def main():
    parser = argparse.ArgumentParser(
        description="Run metabolomics pipeline with fixes"
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent.parent.parent / "configs" / "three_way_metabolomics_mapping_strategy.yaml",
        help='Path to strategy configuration YAML file'
    )
    parser.add_argument(
        '--parameters',
        type=str,
        help='JSON string or file path with parameter overrides'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent.parent / "data" / "results",
        help='Directory for output files'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed output'
    )
    
    args = parser.parse_args()
    
    # Parse parameters
    parameters = parse_parameters(args.parameters)
    parameters['output_dir'] = str(args.output_dir)
    
    # Execute strategy
    try:
        # Use the config file path as the strategy
        result = run_strategy(
            strategy_name=str(args.config),
            parameters=parameters
        )
        
        # Print results
        print_result(result, verbose=args.verbose)
        
        if not result.get('success'):
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())