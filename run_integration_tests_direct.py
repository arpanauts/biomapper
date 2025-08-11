#!/usr/bin/env python3
"""
Direct integration testing without API server dependency.
Run strategies directly using MinimalStrategyService.
"""

import asyncio
import time
import json
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import traceback

# Import test data generators
import sys
sys.path.append('/home/ubuntu/biomapper/tests/integration')
from test_data_generators import generate_realistic_test_data

# Import biomapper components
from biomapper.core.minimal_strategy_service import MinimalStrategyService


@dataclass
class StrategyTestResult:
    """Test result for a strategy execution."""
    strategy_name: str
    entity_type: str
    dataset_size: int
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    output_keys: List[str] = None
    total_output_rows: int = 0


class DirectIntegrationTester:
    """Direct integration tester using MinimalStrategyService."""
    
    def __init__(self):
        self.strategies_dir = "/home/ubuntu/biomapper/configs/strategies"
        self.service = MinimalStrategyService(self.strategies_dir)
        self.results = []
    
    def get_available_strategies(self) -> Dict[str, List[str]]:
        """Get available strategies by type."""
        protein_strategies = []
        metabolite_strategies = []
        chemistry_strategies = []
        other_strategies = []
        
        # Categorize actual loaded strategies by name patterns
        for strategy_name in self.service.strategies.keys():
            strategy_lower = strategy_name.lower()
            
            if "protein" in strategy_lower or "prot" in strategy_lower:
                protein_strategies.append(strategy_name)
            elif any(term in strategy_lower for term in ["metabol", "nightingale", "nmr", "cts"]):
                metabolite_strategies.append(strategy_name)
            elif "chem" in strategy_lower:
                chemistry_strategies.append(strategy_name)
            else:
                other_strategies.append(strategy_name)
        
        return {
            "protein": sorted(protein_strategies),
            "metabolite": sorted(metabolite_strategies), 
            "chemistry": sorted(chemistry_strategies),
            "other": sorted(other_strategies)
        }
    
    def create_test_files(self, entity_type: str, size: int) -> Dict[str, str]:
        """Create test data files and return file paths."""
        output_dir = Path("/tmp/integration_test_data")
        output_dir.mkdir(exist_ok=True)
        
        if entity_type == "metabolite":
            # Create Israeli10K style data
            israeli_data = pd.DataFrame({
                'BIOCHEMICAL_NAME': [f'metabolite_{i}' for i in range(size)],
                'HMDB_ID': [f'HMDB{i:07d}' for i in range(1, size + 1)],
                'PUBCHEM_ID': [f'{i+1000}' for i in range(size)],
                'MW': [100 + i*2 for i in range(size)]
            })
            israeli_file = output_dir / f"israeli10k_test_{size}.tsv"
            israeli_data.to_csv(israeli_file, sep='\t', index=False)
            
            # Create UKBB style data
            ukbb_data = pd.DataFrame({
                'Description': [f'biomarker_{i}' for i in range(size)],
                'Biomarker': [f'BM_{i:03d}' for i in range(size)],
                'Field.ID': [f'{i+20000}' for i in range(size)],
                'Units': ['mmol/L'] * size
            })
            ukbb_file = output_dir / f"ukbb_test_{size}.tsv"
            ukbb_data.to_csv(ukbb_file, sep='\t', index=False)
            
            return {
                'israeli10k_file': str(israeli_file),
                'ukbb_file': str(ukbb_file),
                'output_dir': str(output_dir / "results")
            }
        
        elif entity_type == "protein":
            # Create protein test data
            protein_data = pd.DataFrame({
                'protein_id': [f'P{i:05d}' for i in range(1, size + 1)],
                'gene_symbol': [f'GENE_{i}' for i in range(size)],
                'uniprot_id': [f'Q{i:05d}' for i in range(1, size + 1)],
                'description': [f'Protein {i} description' for i in range(size)]
            })
            protein_file = output_dir / f"protein_test_{size}.tsv"
            protein_data.to_csv(protein_file, sep='\t', index=False)
            
            return {
                'protein_file': str(protein_file),
                'output_dir': str(output_dir / "results")
            }
        
        elif entity_type == "chemistry":
            # Create chemistry test data
            chemistry_data = pd.DataFrame({
                'test_name': [f'Test_{i}' for i in range(size)],
                'value': np.random.uniform(0, 100, size).round(2),
                'unit': ['mg/dL'] * size,
                'loinc_code': [f'{i+10000}-{i%10}' for i in range(size)]
            })
            chemistry_file = output_dir / f"chemistry_test_{size}.tsv"
            chemistry_data.to_csv(chemistry_file, sep='\t', index=False)
            
            return {
                'chemistry_file': str(chemistry_file),
                'output_dir': str(output_dir / "results")
            }
        
        return {}
    
    async def test_strategy(self, strategy_name: str, entity_type: str, 
                          dataset_size: int = 1000) -> StrategyTestResult:
        """Test a single strategy."""
        print(f"  Testing {strategy_name} ({entity_type}, {dataset_size} rows)...")
        
        start_time = time.time()
        
        try:
            # Create test parameters based on strategy
            test_files = self.create_test_files(entity_type, dataset_size)
            
            # Common parameters that many strategies might use
            parameters = {
                **test_files,
                'dataset_size': dataset_size,
                'test_mode': True
            }
            
            # Execute strategy
            result = await self.service.execute_strategy(
                strategy_name=strategy_name,
                context=parameters
            )
            
            execution_time = time.time() - start_time
            
            # Extract result info
            output_keys = list(result.get('datasets', {}).keys()) if result else []
            total_rows = 0
            if result and 'datasets' in result:
                for dataset in result['datasets'].values():
                    if isinstance(dataset, list):
                        total_rows += len(dataset)
            
            test_result = StrategyTestResult(
                strategy_name=strategy_name,
                entity_type=entity_type,
                dataset_size=dataset_size,
                execution_time=execution_time,
                success=True,
                output_keys=output_keys,
                total_output_rows=total_rows
            )
            
            print(f"    ✓ Success in {execution_time:.1f}s, {len(output_keys)} outputs, {total_rows} total rows")
            return test_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            print(f"    ✗ Failed in {execution_time:.1f}s: {error_msg}")
            
            return StrategyTestResult(
                strategy_name=strategy_name,
                entity_type=entity_type,
                dataset_size=dataset_size,
                execution_time=execution_time,
                success=False,
                error_message=error_msg
            )
    
    async def run_comprehensive_tests(self):
        """Run comprehensive integration tests."""
        print("Starting Direct Integration Tests...")
        print(f"Loaded {len(self.service.strategies)} strategies from {self.strategies_dir}")
        
        strategies = self.get_available_strategies()
        
        print(f"\nAvailable strategies:")
        for entity_type, strategy_list in strategies.items():
            print(f"  {entity_type}: {len(strategy_list)} strategies")
        
        # Test a representative sample from each category
        test_sizes = [500, 1000]  # Smaller sizes for faster testing
        
        for entity_type, strategy_list in strategies.items():
            if not strategy_list:
                continue
                
            print(f"\n=== Testing {entity_type.title()} Strategies ===")
            
            # Test first few strategies of each type
            for strategy_name in strategy_list[:3]:  # Test first 3 of each type
                for dataset_size in test_sizes:
                    result = await self.test_strategy(strategy_name, entity_type, dataset_size)
                    self.results.append(result)
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report."""
        if not self.results:
            print("No test results to report")
            return
        
        print(f"\n" + "="*80)
        print("INTEGRATION TEST REPORT")
        print("="*80)
        
        # Summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        print(f"\nSUMMARY:")
        print(f"  Total tests: {total_tests}")
        print(f"  Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"  Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        if passed_tests > 0:
            avg_time = np.mean([r.execution_time for r in self.results if r.success])
            print(f"  Average execution time: {avg_time:.1f}s")
        
        # Results by entity type
        by_entity = {}
        for result in self.results:
            entity = result.entity_type
            if entity not in by_entity:
                by_entity[entity] = {'passed': 0, 'failed': 0, 'times': []}
            
            if result.success:
                by_entity[entity]['passed'] += 1
                by_entity[entity]['times'].append(result.execution_time)
            else:
                by_entity[entity]['failed'] += 1
        
        print(f"\nRESULTS BY ENTITY TYPE:")
        for entity, stats in by_entity.items():
            total = stats['passed'] + stats['failed']
            success_rate = stats['passed'] / total * 100 if total > 0 else 0
            avg_time = np.mean(stats['times']) if stats['times'] else 0
            
            print(f"  {entity.title()}: {stats['passed']}/{total} passed ({success_rate:.1f}%), avg {avg_time:.1f}s")
        
        # Failed strategies
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            print(f"\nFAILED STRATEGIES:")
            for result in failed_results[:10]:  # Show first 10 failures
                error_short = result.error_message[:80] + "..." if len(result.error_message) > 80 else result.error_message
                print(f"  {result.strategy_name} ({result.entity_type}): {error_short}")
        
        # Save detailed results
        results_file = Path("/tmp/direct_integration_results.json")
        with open(results_file, 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        
        # Performance benchmarks for passed tests
        if passed_tests > 0:
            print(f"\nPERFORMANCE BENCHMARKS:")
            
            # Group by dataset size for performance analysis
            by_size = {}
            for result in [r for r in self.results if r.success]:
                size = result.dataset_size
                if size not in by_size:
                    by_size[size] = []
                by_size[size].append(result.execution_time)
            
            for size, times in sorted(by_size.items()):
                avg_time = np.mean(times)
                p95_time = np.percentile(times, 95)
                throughput = size / avg_time
                
                print(f"  {size} rows: avg={avg_time:.1f}s, p95={p95_time:.1f}s, throughput={throughput:.1f} rows/s")


async def main():
    """Main function to run direct integration tests."""
    tester = DirectIntegrationTester()
    await tester.run_comprehensive_tests()


if __name__ == "__main__":
    asyncio.run(main())