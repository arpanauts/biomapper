#!/usr/bin/env python3
"""
Test each action type in the v3.0 strategy independently.

This script tests each action in isolation with minimal sample data to ensure
they work before running the full pipeline.
"""

import os
import sys
import asyncio
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import json

# Add biomapper to path
sys.path.insert(0, "/home/ubuntu/biomapper")

from biomapper.core.strategy_actions.registry import ACTION_REGISTRY


class ActionTester:
    """Test individual actions with sample data."""
    
    def __init__(self):
        self.results = {}
        self.context = self._create_test_context()
        
    def _create_test_context(self) -> Dict[str, Any]:
        """Create a test context with sample data."""
        # Create sample DataFrames
        sample_proteins = pd.DataFrame({
            'uniprot': ['P12345', 'Q67890,R11111', 'S22222', 'T33333', 'U44444'],
            'protein_name': ['Protein A', 'Protein B/C', 'Protein D', 'Protein E', 'Protein F'],
            'gene_symbol': ['GENA', 'GENB', 'GEND', 'GENE', 'GENF']
        })
        
        kg2c_sample = pd.DataFrame({
            'id': ['KG2C:001', 'KG2C:002', 'KG2C:003'],
            'name': ['Entity 1', 'Entity 2', 'Entity 3'],
            'category': ['protein', 'protein', 'protein'],
            'xrefs': ['UniProtKB:P12345|RefSeq:NP_001', 'UniProtKB:Q67890', 'UniProtKB:T99999']
        })
        
        return {
            'datasets': {
                'arivale_raw': sample_proteins.copy(),
                'kg2c_raw': kg2c_sample.copy(),
                'arivale_normalized': sample_proteins.copy(),
                'kg2c_normalized': kg2c_sample.copy()
            },
            'statistics': {},
            'output_files': [],
            'progressive_stats': {
                'total_processed': 5,
                'stages': {}
            }
        }
    
    async def test_action(self, action_name: str, params: Dict[str, Any]) -> bool:
        """Test a single action."""
        try:
            print(f"\nTesting {action_name}...")
            
            # Check if action exists
            if action_name not in ACTION_REGISTRY:
                print(f"  ❌ Action not found in registry")
                self.results[action_name] = False
                return False
            
            # Get action class
            action_class = ACTION_REGISTRY[action_name]
            action = action_class()
            
            # Create a copy of context for this test
            test_context = self.context.copy()
            test_context['datasets'] = self.context['datasets'].copy()
            
            # Execute action
            result = await action.execute(params, test_context)
            
            if result.success:
                print(f"  ✅ {action_name} - SUCCESS")
                self.results[action_name] = True
                return True
            else:
                print(f"  ❌ {action_name} - FAILED: {result.message}")
                self.results[action_name] = False
                return False
                
        except Exception as e:
            print(f"  ❌ {action_name} - ERROR: {str(e)}")
            self.results[action_name] = False
            return False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("ACTION TEST SUMMARY")
        print("=" * 80)
        
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        
        for action, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {action}")
        
        print(f"\nTotal: {passed}/{total} actions passed")
        return passed == total


async def test_all_v3_actions():
    """Test all actions used in v3.0 strategy."""
    
    print("=" * 80)
    print("Testing V3.0 Strategy Actions Independently")
    print("=" * 80)
    
    tester = ActionTester()
    output_dir = "/tmp/biomapper/action_tests"
    os.makedirs(output_dir, exist_ok=True)
    
    # Define test cases for each action in v3.0 strategy
    test_cases = [
        # Data loading actions
        ("LOAD_DATASET_IDENTIFIERS", {
            "file_path": "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv",
            "identifier_column": "uniprot",
            "output_key": "test_load"
        }),
        
        # Protein processing actions
        ("PROTEIN_EXTRACT_UNIPROT_FROM_XREFS", {
            "input_key": "kg2c_raw",
            "xrefs_column": "xrefs",
            "output_key": "test_extract"
        }),
        
        ("PROTEIN_NORMALIZE_ACCESSIONS", {
            "input_key": "arivale_raw",
            "id_columns": ["uniprot"],
            "output_key": "test_normalize"
        }),
        
        # Merging and filtering
        ("MERGE_DATASETS", {
            "input_key": "arivale_normalized",
            "dataset2_key": "kg2c_normalized",
            "join_columns": {"uniprot": "id"},
            "join_type": "inner",
            "output_key": "test_merge"
        }),
        
        ("FILTER_DATASET", {
            "input_key": "arivale_raw",
            "filter_type": "not_in",
            "reference_key": "kg2c_raw",
            "reference_column": "id",
            "output_key": "test_filter"
        }),
        
        # Composite identifier parsing
        ("PARSE_COMPOSITE_IDENTIFIERS", {
            "input_key": "arivale_raw",
            "identifier_column": "uniprot",
            "separators": [",", ";", "|"],
            "output_key": "test_composite",
            "track_expansion": True,
            "preserve_original": True
        }),
        
        # Historical resolution (may need API)
        ("PROTEIN_HISTORICAL_RESOLUTION", {
            "input_key": "arivale_raw",
            "reference_dataset": "kg2c_normalized",
            "output_key": "test_historical"
        }),
        
        # Custom transformations
        ("CUSTOM_TRANSFORM", {
            "input_key": "arivale_raw",
            "output_key": "test_transform",
            "transformations": [
                {"column": "confidence_score", "expression": "1.0"},
                {"column": "match_type", "expression": "'direct'"}
            ]
        }),
        
        # Export actions
        ("EXPORT_DATASET", {
            "input_key": "arivale_raw",
            "output_path": f"{output_dir}/test_export.tsv",
            "format": "tsv"
        }),
        
        # Visualization (V2)
        ("GENERATE_MAPPING_VISUALIZATIONS_V2", {
            "charts": [],
            "output_directory": f"{output_dir}/visualizations",
            "export_static": True,
            "static_formats": ["png"],
            "progressive_params": {
                "progressive_mode": True,
                "export_statistics_tsv": True
            }
        }),
        
        # Google Drive sync (will skip if no credentials)
        ("SYNC_TO_GOOGLE_DRIVE_V2", {
            "drive_folder_id": "test_folder",
            "credentials_path": "/path/to/nonexistent/creds.json",
            "auto_organize": True,
            "strategy_name": "test_strategy",
            "strategy_version": "test",
            "create_subfolder": False,
            "sync_context_outputs": False
        })
    ]
    
    # Run tests
    for action_name, params in test_cases:
        await tester.test_action(action_name, params)
    
    # Special test for LLM analysis (if available)
    print("\nTesting LLM Analysis (optional)...")
    try:
        if "GENERATE_LLM_ANALYSIS" in ACTION_REGISTRY:
            await tester.test_action("GENERATE_LLM_ANALYSIS", {
                "provider": "anthropic",
                "model": "claude-3-opus-20240229",
                "output_directory": f"{output_dir}/analysis",
                "include_recommendations": True
            })
        else:
            print("  ⚠️  GENERATE_LLM_ANALYSIS not registered yet")
    except Exception as e:
        print(f"  ⚠️  LLM Analysis test skipped: {e}")
    
    # Print summary
    success = tester.print_summary()
    
    # Identify critical vs optional failures
    critical_actions = [
        "LOAD_DATASET_IDENTIFIERS",
        "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS", 
        "PROTEIN_NORMALIZE_ACCESSIONS",
        "MERGE_DATASETS",
        "FILTER_DATASET",
        "PARSE_COMPOSITE_IDENTIFIERS",
        "CUSTOM_TRANSFORM",
        "EXPORT_DATASET"
    ]
    
    optional_actions = [
        "PROTEIN_HISTORICAL_RESOLUTION",  # Needs API
        "GENERATE_LLM_ANALYSIS",  # Optional enhancement
        "SYNC_TO_GOOGLE_DRIVE_V2"  # Needs credentials
    ]
    
    print("\n" + "=" * 80)
    print("CRITICAL ACTION STATUS")
    print("=" * 80)
    
    critical_pass = True
    for action in critical_actions:
        if action in tester.results:
            status = "✅" if tester.results[action] else "❌"
            print(f"{status} {action}")
            if not tester.results[action]:
                critical_pass = False
    
    print("\n" + "=" * 80)
    print("OPTIONAL ACTION STATUS")
    print("=" * 80)
    
    for action in optional_actions:
        if action in tester.results:
            status = "✅" if tester.results[action] else "⚠️"
            print(f"{status} {action}")
    
    return critical_pass


def main():
    """Main entry point."""
    critical_pass = asyncio.run(test_all_v3_actions())
    
    if critical_pass:
        print("\n" + "=" * 80)
        print("✅ CRITICAL ACTIONS PASSED - READY FOR PIPELINE")
        print("=" * 80)
        print("\nAll critical actions for v3.0 strategy are working!")
        print("The pipeline can be run, though some optional features may be disabled.")
        print("\nNext step: Run the full pipeline with:")
        print("  python scripts/run_v3_pipeline.py")
    else:
        print("\n" + "=" * 80)
        print("❌ CRITICAL ACTIONS FAILED - PIPELINE NOT READY")
        print("=" * 80)
        print("\nSome critical actions are failing. These must be fixed before")
        print("running the full pipeline.")
        sys.exit(1)


if __name__ == "__main__":
    main()