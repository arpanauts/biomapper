#!/usr/bin/env python3
"""
Client script for consolidated metabolomics progressive pipeline v4.0.

This script supports incremental testing with systematic stage enabling:
- Stage 1 only: Basic Nightingale Bridge matching
- Stages 1-2: Add Fuzzy String Matching
- Stages 1-3: Add RampDB API (requires API access)
- Stages 1-4: Add HMDB VectorRAG (requires Qdrant)

Usage:
    # Test Stage 1 only
    python met_arv_to_ukbb_progressive_v4.0.py --stages 1
    
    # Test Stages 1-2
    python met_arv_to_ukbb_progressive_v4.0.py --stages 1,2
    
    # Test full pipeline
    python met_arv_to_ukbb_progressive_v4.0.py --stages 1,2,3,4
    
    # Enable debug mode
    python met_arv_to_ukbb_progressive_v4.0.py --stages 1 --debug
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List

# Setup paths
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

# Import the client
from client.client_v2 import BiomapperClient


def parse_stages(stages_str: str) -> List[int]:
    """Parse stage string like '1,2,3' into list [1,2,3]."""
    try:
        return [int(s.strip()) for s in stages_str.split(',')]
    except ValueError:
        print(f"❌ Invalid stages format: {stages_str}")
        print("   Use format like: 1 or 1,2 or 1,2,3,4")
        sys.exit(1)


def main():
    """Run the consolidated metabolomics pipeline with incremental testing."""
    parser = argparse.ArgumentParser(
        description="Run consolidated metabolomics pipeline v4.0 with incremental testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Test Stage 1 only:
    %(prog)s --stages 1
    
  Test Stages 1-2:
    %(prog)s --stages 1,2
    
  Test full pipeline:
    %(prog)s --stages 1,2,3,4
    
  Custom output directory:
    %(prog)s --stages 1 --output-dir /tmp/my_test
        """
    )
    
    parser.add_argument(
        '--stages',
        type=str,
        default='1',
        help='Comma-separated list of stages to run (e.g., "1,2" or "1,2,3,4")'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (default: /tmp/biomapper/met_arv_to_ukbb_v4.0_TIMESTAMP)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable verbose debug output'
    )
    
    parser.add_argument(
        '--dataset',
        choices=['arivale', 'ukbb'],
        default='arivale',
        help='Dataset to process (default: arivale)'
    )
    
    parser.add_argument(
        '--no-validation',
        action='store_true',
        help='Skip pre-flight validation checks (not recommended)'
    )
    
    parser.add_argument(
        '--enable-visualization',
        action='store_true',
        help='Enable visualization generation (adds processing time)'
    )
    
    parser.add_argument(
        '--enable-llm',
        action='store_true',
        help='Enable LLM analysis (requires API key, adds cost)'
    )
    
    args = parser.parse_args()
    
    # Parse stages
    stages = parse_stages(args.stages)
    
    # Set up output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        stages_str = '_'.join(map(str, stages))
        output_dir = f"/tmp/biomapper/met_arv_to_ukbb_v4.0_stages{stages_str}_{timestamp}"
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Set environment variables to override YAML parameters
    os.environ['OUTPUT_DIR'] = output_dir
    os.environ['STAGES_TO_RUN'] = json.dumps(stages)  # Pass as JSON array
    os.environ['DEBUG_MODE'] = str(args.debug).lower()
    os.environ['VERBOSE_LOGGING'] = str(args.debug).lower()
    os.environ['VALIDATE_PARAMETERS'] = str(not args.no_validation).lower()
    os.environ['ENABLE_VISUALIZATIONS'] = str(args.enable_visualization).lower()
    os.environ['ENABLE_LLM_ANALYSIS'] = str(args.enable_llm).lower()
    
    # Set dataset paths
    if args.dataset == 'ukbb':
        os.environ['INPUT_FILE'] = "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_NMR_Meta.tsv"
        os.environ['IDENTIFIER_COLUMN'] = "name"
        expected_total = 251
    else:  # arivale
        os.environ['INPUT_FILE'] = "/procedure/data/local_data/MAPPING_ONTOLOGIES/arivale/metabolomics_metadata.tsv"
        os.environ['IDENTIFIER_COLUMN'] = "BIOCHEMICAL_NAME"
        expected_total = 1351
    
    # Print configuration
    print("="*60)
    print("METABOLOMICS PROGRESSIVE PIPELINE v4.0")
    print("="*60)
    print(f"Dataset: {args.dataset.upper()} ({expected_total} metabolites)")
    print(f"Stages to run: {stages}")
    print(f"Output: {output_dir}")
    print(f"Debug mode: {args.debug}")
    print(f"Validation: {not args.no_validation}")
    print(f"Visualization: {args.enable_visualization}")
    print(f"LLM Analysis: {args.enable_llm}")
    print("="*60)
    
    # Stage descriptions
    stage_descriptions = {
        1: "Nightingale Bridge (direct ID matching)",
        2: "Fuzzy String Matching (algorithmic)",
        3: "RampDB Bridge (API cross-reference)",
        4: "HMDB VectorRAG (semantic similarity)"
    }
    
    print("\nStages to execute:")
    for stage in stages:
        desc = stage_descriptions.get(stage, "Unknown")
        warning = ""
        if stage == 3:
            warning = " ⚠️ Requires RampDB API"
        elif stage == 4:
            warning = " ⚠️ Requires Qdrant + HMDB data"
        print(f"  Stage {stage}: {desc}{warning}")
    
    print("\n" + "-"*60)
    
    # Initialize client and run strategy
    try:
        print("\nInitializing BiomapperClient...")
        client = BiomapperClient()
        print("✅ Client initialized")
        
        print(f"\nRunning strategy: met_arv_to_ukbb_progressive_v4.0")
        print(f"Stages: {stages}")
        print("-"*60 + "\n")
        
        result = client.run("met_arv_to_ukbb_progressive_v4.0")
        
        print("\n" + "-"*60)
        
        if result:
            print("\n✅ Pipeline execution completed!")
            
            # Check for output files
            output_path = Path(output_dir)
            if output_path.exists():
                # Look for key files
                summary_file = output_path / "execution_summary.txt"
                final_file = output_path / "met_arv_to_ukbb_v4.0_final.tsv"
                
                if summary_file.exists():
                    print("\n📊 Execution Summary:")
                    with open(summary_file) as f:
                        for line in f:
                            print(f"   {line.strip()}")
                
                # Count files by stage
                print("\n📁 Generated files by stage:")
                for stage in stages:
                    stage_files = list(output_path.glob(f"stage_{stage}_*.tsv"))
                    if stage_files:
                        for f in stage_files:
                            size = f.stat().st_size / 1024
                            # Count lines
                            with open(f) as file:
                                lines = len(file.readlines()) - 1  # Subtract header
                            print(f"   Stage {stage}: {f.name} ({lines} records, {size:.1f} KB)")
                
                # Final results
                if final_file.exists():
                    with open(final_file) as f:
                        final_count = len(f.readlines()) - 1
                    coverage = (final_count / expected_total) * 100
                    print(f"\n🎯 Final Results:")
                    print(f"   Total matched: {final_count}/{expected_total}")
                    print(f"   Coverage achieved: {coverage:.1f}%")
                    
                    # Coverage assessment
                    if coverage < 50:
                        print("   ⚠️ Low coverage - consider enabling more stages")
                    elif coverage < 70:
                        print("   ⚠️ Moderate coverage - Stage 3-4 may improve results")
                    else:
                        print("   ✅ Good coverage achieved!")
                else:
                    print("\n⚠️ No final results file found")
                    print("   Pipeline may not have completed all stages")
                
                print(f"\n📂 All outputs in: {output_dir}")
            else:
                print(f"\n❌ Output directory not found: {output_dir}")
        else:
            print("\n❌ Pipeline failed!")
            print("Check the debug output above for error details")
            
            # Suggest troubleshooting
            print("\nTroubleshooting tips:")
            print("1. Start with --stages 1 to test basic functionality")
            print("2. Use --debug for verbose output")
            print("3. Check that input files exist")
            print("4. Ensure required actions are registered")
            
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()