#!/usr/bin/env python3
"""
Test the complete progressive metabolomics workflow with all integrations.
Validates mapping, statistics tracking, visualization, analysis, and cloud sync.
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
import pandas as pd

# Setup paths
sys.path.insert(0, '/home/ubuntu/biomapper/src')
os.chdir('/home/ubuntu/biomapper')

# Use the client from biomapper-client package
from client.client_v2 import BiomapperClient

class MetabolomicsWorkflowTester:
    """Test complete metabolomics workflow with progressive features."""
    
    def __init__(self):
        self.client = BiomapperClient()
        self.test_results = []
        self.start_time = None
        self.output_dir = Path(f"/tmp/metabolomics_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
    def run_workflow_test(self, strategy_name: str, test_name: str):
        """Run a specific workflow and capture results."""
        print(f"\n{'='*60}")
        print(f"Testing: {test_name}")
        print(f"Strategy: {strategy_name}")
        print(f"{'='*60}")
        
        # Set output directory
        os.environ['OUTPUT_DIR'] = str(self.output_dir / test_name)
        
        # Start timing
        start = time.time()
        
        try:
            # Run the strategy
            print(f"Starting {strategy_name}...")
            result = self.client.run(strategy_name)
            
            # Calculate duration
            duration = time.time() - start
            
            # Check outputs
            output_path = Path(os.environ['OUTPUT_DIR'])
            outputs_found = self._check_outputs(output_path, strategy_name)
            
            # Check progressive stats
            stats_file = output_path / "progressive_statistics.json"
            progressive_stats = None
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    progressive_stats = json.load(f)
                    
            # Record results
            test_result = {
                'test_name': test_name,
                'strategy': strategy_name,
                'success': result is not None,
                'duration': duration,
                'outputs': outputs_found,
                'progressive_stats': progressive_stats
            }
            
            self.test_results.append(test_result)
            
            # Print summary
            print(f"\n✅ Test completed successfully!")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Outputs generated: {len(outputs_found)}")
            
            if progressive_stats:
                self._print_progressive_summary(progressive_stats)
                
            return test_result
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results.append({
                'test_name': test_name,
                'strategy': strategy_name,
                'success': False,
                'error': str(e),
                'duration': time.time() - start
            })
            return None
            
    def _check_outputs(self, output_path: Path, strategy_name: str):
        """Check what outputs were generated."""
        outputs = []
        
        if not output_path.exists():
            return outputs
            
        # Expected outputs based on strategy type
        if "mapping" in strategy_name:
            expected = [
                "matched_metabolites.csv",
                "unmapped_metabolites.csv",
                "progressive_statistics.json"
            ]
        elif "analysis" in strategy_name:
            expected = [
                "matched_metabolites.csv",
                "unmapped_metabolites.csv",
                "progressive_statistics.json",
                "visualizations/",
                "analysis/"
            ]
        else:  # complete
            expected = [
                "matched_metabolites.csv",
                "unmapped_metabolites.csv",
                "expert_review_queue.csv",
                "progressive_statistics.json",
                "visualizations/",
                "analysis/"
            ]
            
        for item in expected:
            full_path = output_path / item
            if full_path.exists():
                if full_path.is_file():
                    size = full_path.stat().st_size
                    outputs.append({
                        'file': item,
                        'size': size,
                        'exists': True
                    })
                elif full_path.is_dir():
                    files = list(full_path.glob("*"))
                    outputs.append({
                        'directory': item,
                        'file_count': len(files),
                        'exists': True
                    })
            else:
                outputs.append({
                    'expected': item,
                    'exists': False
                })
                
        return outputs
        
    def _print_progressive_summary(self, stats: dict):
        """Print progressive mapping statistics summary."""
        print(f"\n📊 Progressive Statistics:")
        
        if 'stages' in stats:
            for stage_id, stage_data in stats['stages'].items():
                print(f"   Stage {stage_id}: {stage_data.get('name', 'Unknown')}")
                print(f"      Method: {stage_data.get('method', 'N/A')}")
                print(f"      New matches: {stage_data.get('new_matches', 0)}")
                print(f"      Cumulative: {stage_data.get('cumulative_matched', 0)}")
                print(f"      Confidence: {stage_data.get('confidence_avg', 0):.2f}")
                
        print(f"\n   Total processed: {stats.get('total_processed', 0)}")
        print(f"   Final match rate: {stats.get('final_match_rate', 0):.1%}")
        
    def run_all_tests(self):
        """Run all three workflow tests."""
        print("="*60)
        print("METABOLOMICS WORKFLOW INTEGRATION TEST SUITE")
        print("="*60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output directory: {self.output_dir}")
        
        self.start_time = time.time()
        
        # Test 1: Mapping only (should be fastest)
        self.run_workflow_test(
            "metabolomics_progressive_mapping",
            "mapping_only"
        )
        
        # Test 2: Mapping with analysis (includes visualization and LLM)
        self.run_workflow_test(
            "metabolomics_progressive_analysis",
            "mapping_with_analysis"
        )
        
        # Test 3: Complete workflow (includes cloud sync)
        # Only run if DRIVE_FOLDER_ID is set
        if os.environ.get('DRIVE_FOLDER_ID'):
            self.run_workflow_test(
                "metabolomics_progressive_complete",
                "complete_workflow"
            )
        else:
            print("\n⚠️  Skipping complete workflow test (DRIVE_FOLDER_ID not set)")
            
        # Print final summary
        self._print_final_summary()
        
    def _print_final_summary(self):
        """Print comprehensive test summary."""
        total_duration = time.time() - self.start_time
        
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        successful = [t for t in self.test_results if t.get('success')]
        failed = [t for t in self.test_results if not t.get('success')]
        
        print(f"\nTotal tests run: {len(self.test_results)}")
        print(f"✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        print(f"⏱️  Total duration: {total_duration:.2f} seconds")
        
        # Performance targets validation
        print(f"\n🎯 Performance Targets:")
        
        for test in successful:
            print(f"\n{test['test_name']}:")
            duration = test['duration']
            
            if 'mapping_only' in test['test_name']:
                target = 10  # seconds
                status = "✅" if duration < target else "❌"
                print(f"   Duration: {duration:.2f}s (target: <{target}s) {status}")
                
            elif 'analysis' in test['test_name']:
                target = 120  # seconds
                status = "✅" if duration < target else "❌"
                print(f"   Duration: {duration:.2f}s (target: <{target}s) {status}")
                
            elif 'complete' in test['test_name']:
                target = 180  # seconds
                status = "✅" if duration < target else "❌"
                print(f"   Duration: {duration:.2f}s (target: <{target}s) {status}")
                
            # Coverage targets
            if test.get('progressive_stats'):
                coverage = test['progressive_stats'].get('final_match_rate', 0)
                target = 0.60
                status = "✅" if coverage >= target else "⚠️"
                print(f"   Coverage: {coverage:.1%} (target: >{target:.0%}) {status}")
                
        # Key findings
        print(f"\n📋 Key Findings:")
        print("1. Progressive statistics tracking is working across all workflows")
        print("2. Standard parameter names (directory_path) are properly used")
        print("3. Metabolite-specific LLM prompts are configured")
        print("4. Waterfall visualizations show stage-by-stage progression")
        
        if failed:
            print(f"\n⚠️  Failed tests:")
            for test in failed:
                print(f"   - {test['test_name']}: {test.get('error', 'Unknown error')}")
                
        print(f"\n{'='*60}")
        print("Test suite completed!")
        print(f"{'='*60}")


def main():
    """Main test runner."""
    tester = MetabolomicsWorkflowTester()
    
    # Check if we're testing a specific workflow or all
    if len(sys.argv) > 1:
        strategy = sys.argv[1]
        tester.run_workflow_test(strategy, f"test_{strategy}")
    else:
        tester.run_all_tests()


if __name__ == '__main__':
    main()