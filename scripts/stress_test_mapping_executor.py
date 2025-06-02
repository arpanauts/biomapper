#!/usr/bin/env python3
"""
Performance stress testing script for MappingExecutor.

This script is designed to validate that the recently implemented client caching mechanism
provides sustained performance benefits when using larger, production-representative datasets.
It measures execution time, memory usage, and mapping success rates across different input sizes.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import traceback
import gc
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import pandas as pd
import psutil

# Import biomapper components
from biomapper.core.mapping_executor import MappingExecutor, PathExecutionStatus
from biomapper.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Class to track performance metrics during test execution."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.peak_memory_mb: float = 0.0
        self.initial_memory_mb: float = 0.0
        self.process = psutil.Process()
        
    def start_measurement(self):
        """Start measuring performance metrics."""
        self.start_time = time.time()
        gc.collect()  # Clean up before measurement
        self.initial_memory_mb = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory_mb = self.initial_memory_mb
        logger.info(f"Starting measurement - Initial memory: {self.initial_memory_mb:.2f} MB")
        
    def update_peak_memory(self):
        """Update peak memory usage if current usage is higher."""
        current_memory_mb = self.process.memory_info().rss / 1024 / 1024
        if current_memory_mb > self.peak_memory_mb:
            self.peak_memory_mb = current_memory_mb
            
    def end_measurement(self):
        """End measuring and return final metrics."""
        self.end_time = time.time()
        self.update_peak_memory()
        final_memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        return {
            "execution_time_seconds": self.end_time - self.start_time if self.start_time else 0,
            "initial_memory_mb": self.initial_memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "final_memory_mb": final_memory_mb,
            "memory_growth_mb": final_memory_mb - self.initial_memory_mb
        }

class MappingExecutorStressTester:
    """Main class for stress testing MappingExecutor performance."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.test_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
    async def load_test_data(self, dataset_path: str, id_column: str, limit: Optional[int] = None) -> List[str]:
        """Load unique identifiers from a test dataset."""
        logger.info(f"Loading test data from: {dataset_path}")
        
        try:
            # Handle TSV files with potential comment lines
            if dataset_path.endswith('.tsv'):
                df = pd.read_csv(dataset_path, sep='\t', dtype=str, comment='#')
            else:
                df = pd.read_csv(dataset_path, dtype=str)
                
            if id_column not in df.columns:
                raise ValueError(f"Column '{id_column}' not found in dataset. Available columns: {list(df.columns)}")
                
            # Extract unique non-null identifiers
            identifiers = df[id_column].dropna().unique().tolist()
            
            if limit and len(identifiers) > limit:
                identifiers = identifiers[:limit]
                logger.info(f"Limited dataset to {limit} identifiers")
                
            logger.info(f"Loaded {len(identifiers)} unique identifiers from column '{id_column}'")
            return identifiers
            
        except Exception as e:
            logger.error(f"Error loading test data: {e}")
            return []
    
    async def run_mapping_test(
        self,
        executor: MappingExecutor,
        identifiers: List[str],
        source_endpoint: str,
        target_endpoint: str,
        source_property: str = "PrimaryIdentifier",
        target_property: str = "PrimaryIdentifier",
        test_name: str = "unnamed_test"
    ) -> Dict[str, Any]:
        """Run a single mapping test and collect performance metrics."""
        
        logger.info(f"Starting test '{test_name}' with {len(identifiers)} identifiers")
        logger.info(f"Mapping from {source_endpoint} to {target_endpoint}")
        
        # Initialize performance tracking
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # Track memory periodically during execution
        async def memory_monitor():
            while metrics.start_time and not metrics.end_time:
                metrics.update_peak_memory()
                await asyncio.sleep(0.5)  # Check every 500ms
        
        # Start memory monitoring task
        monitor_task = asyncio.create_task(memory_monitor())
        
        try:
            # Execute the mapping
            logger.info(f"Beginning mapping execution...")
            mapping_results = await executor.execute_mapping(
                source_endpoint_name=source_endpoint,
                target_endpoint_name=target_endpoint,
                input_identifiers=identifiers,
                source_property_name=source_property,
                target_property_name=target_property,
                try_reverse_mapping=True,  # Enable reverse mapping for better success rates
                validate_bidirectional=False,  # Disable for performance testing
            )
            
            # End performance measurement
            perf_metrics = metrics.end_measurement()
            
            # Cancel memory monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            
            # Analyze mapping results
            success_count = 0
            failure_count = 0
            error_count = 0
            
            for result in mapping_results.values():
                if result and isinstance(result, dict):
                    status = result.get("status", "unknown")
                    if status == "success" and result.get("target_identifiers"):
                        success_count += 1
                    elif status == "error":
                        error_count += 1
                    else:
                        failure_count += 1
                else:
                    failure_count += 1
            
            success_rate = (success_count / len(identifiers)) * 100 if identifiers else 0
            
            logger.info(f"Test '{test_name}' completed:")
            logger.info(f"  - Execution time: {perf_metrics['execution_time_seconds']:.2f}s")
            logger.info(f"  - Peak memory: {perf_metrics['peak_memory_mb']:.2f} MB")
            logger.info(f"  - Memory growth: {perf_metrics['memory_growth_mb']:.2f} MB")
            logger.info(f"  - Success rate: {success_rate:.1f}% ({success_count}/{len(identifiers)})")
            
            return {
                "test_name": test_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_count": len(identifiers),
                "source_endpoint": source_endpoint,
                "target_endpoint": target_endpoint,
                "performance_metrics": perf_metrics,
                "mapping_results": {
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "error_count": error_count,
                    "success_rate_percent": success_rate
                },
                "configuration": {
                    "source_property": source_property,
                    "target_property": target_property,
                    "try_reverse_mapping": True,
                    "validate_bidirectional": False
                }
            }
            
        except Exception as e:
            logger.error(f"Error during mapping test '{test_name}': {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # End measurement even on error
            perf_metrics = metrics.end_measurement()
            
            # Cancel memory monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
                
            return {
                "test_name": test_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_count": len(identifiers),
                "source_endpoint": source_endpoint,
                "target_endpoint": target_endpoint,
                "performance_metrics": perf_metrics,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
    
    async def run_stress_tests(
        self,
        dataset_path: str,
        id_column: str,
        source_endpoint: str,
        target_endpoint: str,
        test_sizes: List[int],
        source_property: str = "PrimaryIdentifier",
        target_property: str = "PrimaryIdentifier"
    ) -> List[Dict[str, Any]]:
        """Run a series of stress tests with increasing input sizes."""
        
        logger.info("="*60)
        logger.info("STARTING MAPPING EXECUTOR STRESS TESTS")
        logger.info("="*60)
        
        # Load the full dataset once
        all_identifiers = await self.load_test_data(dataset_path, id_column)
        
        if not all_identifiers:
            logger.error("No identifiers loaded from dataset. Cannot proceed with tests.")
            return []
        
        # Initialize MappingExecutor once and reuse to test client caching
        logger.info("Initializing MappingExecutor...")
        init_start_time = time.time()
        
        # Use the correct database paths
        metamapper_db_url = "sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db"
        cache_db_url = "sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db"
        
        executor = MappingExecutor(
            metamapper_db_url=metamapper_db_url,
            mapping_cache_db_url=cache_db_url,
            echo_sql=False,  # Disable SQL logging for performance
            enable_metrics=False,  # Disable additional metrics for performance
        )
        
        init_time = time.time() - init_start_time
        logger.info(f"MappingExecutor initialized in {init_time:.2f} seconds")
        
        results = []
        
        # Run tests with increasing sizes
        for size in test_sizes:
            if size > len(all_identifiers):
                logger.warning(f"Requested size {size} exceeds available data ({len(all_identifiers)}). Using full dataset.")
                test_identifiers = all_identifiers
            else:
                test_identifiers = all_identifiers[:size]
            
            test_name = f"stress_test_{size}_identifiers"
            
            # Run the test
            test_result = await self.run_mapping_test(
                executor=executor,
                identifiers=test_identifiers,
                source_endpoint=source_endpoint,
                target_endpoint=target_endpoint,
                source_property=source_property,
                target_property=target_property,
                test_name=test_name
            )
            
            results.append(test_result)
            
            # Force garbage collection between tests
            gc.collect()
            
            # Add a brief pause between tests
            await asyncio.sleep(1)
            
            logger.info(f"Completed test {test_name}")
            logger.info("-" * 50)
        
        logger.info("="*60)
        logger.info("ALL STRESS TESTS COMPLETED")
        logger.info("="*60)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_dir: str):
        """Save test results to JSON and markdown files."""
        
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # JSON results file
        json_file = output_path / f"mapping_executor_perf_test_results_{self.test_timestamp}.json"
        
        with open(json_file, 'w') as f:
            json.dump({
                "test_run_metadata": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "script_version": "1.0",
                    "total_tests": len(results)
                },
                "results": results
            }, f, indent=2)
        
        logger.info(f"Results saved to: {json_file}")
        
        # Markdown summary file
        md_file = output_path / f"mapping_executor_perf_test_results_{self.test_timestamp}.md"
        
        with open(md_file, 'w') as f:
            f.write("# MappingExecutor Performance Test Results\\n\\n")
            f.write(f"**Test Run:** {self.test_timestamp}\\n")
            f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\\n")
            f.write(f"**Total Tests:** {len(results)}\\n\\n")
            
            # Summary table
            f.write("## Performance Summary\\n\\n")
            f.write("| Test Size | Execution Time (s) | Peak Memory (MB) | Memory Growth (MB) | Success Rate (%) |\\n")
            f.write("|-----------|-------------------|------------------|--------------------|------------------|\\n")
            
            for result in results:
                if "error" not in result:
                    size = result["input_count"]
                    exec_time = result["performance_metrics"]["execution_time_seconds"]
                    peak_mem = result["performance_metrics"]["peak_memory_mb"]
                    mem_growth = result["performance_metrics"]["memory_growth_mb"]
                    success_rate = result["mapping_results"]["success_rate_percent"]
                    
                    f.write(f"| {size:,} | {exec_time:.2f} | {peak_mem:.1f} | {mem_growth:.1f} | {success_rate:.1f}% |\\n")
                else:
                    size = result["input_count"]
                    f.write(f"| {size:,} | ERROR | ERROR | ERROR | ERROR |\\n")
            
            f.write("\\n")
            
            # Detailed results
            f.write("## Detailed Results\\n\\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"### Test {i}: {result['test_name']}\\n\\n")
                
                if "error" not in result:
                    f.write(f"- **Input Size:** {result['input_count']:,} identifiers\\n")
                    f.write(f"- **Source Endpoint:** {result['source_endpoint']}\\n")
                    f.write(f"- **Target Endpoint:** {result['target_endpoint']}\\n")
                    f.write(f"- **Execution Time:** {result['performance_metrics']['execution_time_seconds']:.2f} seconds\\n")
                    f.write(f"- **Peak Memory:** {result['performance_metrics']['peak_memory_mb']:.1f} MB\\n")
                    f.write(f"- **Memory Growth:** {result['performance_metrics']['memory_growth_mb']:.1f} MB\\n")
                    f.write(f"- **Success Rate:** {result['mapping_results']['success_rate_percent']:.1f}% ({result['mapping_results']['success_count']:,} successful)\\n")
                    f.write(f"- **Failures:** {result['mapping_results']['failure_count']:,}\\n")
                    f.write(f"- **Errors:** {result['mapping_results']['error_count']:,}\\n")
                else:
                    f.write(f"- **Input Size:** {result['input_count']:,} identifiers\\n")
                    f.write(f"- **ERROR:** {result['error']}\\n")
                    f.write(f"- **Error Type:** {result['error_type']}\\n")
                
                f.write("\\n")
        
        logger.info(f"Summary saved to: {md_file}")
        
        return str(json_file), str(md_file)

async def main():
    """Main function to run the stress tests."""
    
    parser = argparse.ArgumentParser(description="Stress test MappingExecutor performance")
    
    parser.add_argument(
        "--dataset", 
        required=True,
        help="Path to the dataset file (TSV/CSV format)"
    )
    parser.add_argument(
        "--id-column",
        required=True,
        help="Name of the column containing identifiers to map"
    )
    parser.add_argument(
        "--source-endpoint",
        required=True,
        help="Name of the source endpoint"
    )
    parser.add_argument(
        "--target-endpoint", 
        required=True,
        help="Name of the target endpoint"
    )
    parser.add_argument(
        "--test-sizes",
        default="100,500,1000,5000,10000",
        help="Comma-separated list of test sizes (default: 100,500,1000,5000,10000)"
    )
    parser.add_argument(
        "--source-property",
        default="PrimaryIdentifier",
        help="Source property name (default: PrimaryIdentifier)"
    )
    parser.add_argument(
        "--target-property",
        default="PrimaryIdentifier", 
        help="Target property name (default: PrimaryIdentifier)"
    )
    parser.add_argument(
        "--output-dir",
        default="/home/ubuntu/biomapper/data/testing_results",
        help="Output directory for results (default: /home/ubuntu/biomapper/data/testing_results)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Parse test sizes
    try:
        test_sizes = [int(x.strip()) for x in args.test_sizes.split(",")]
        test_sizes.sort()  # Ensure ascending order
    except ValueError as e:
        logger.error(f"Invalid test sizes format: {e}")
        return 1
    
    # Validate dataset exists
    if not Path(args.dataset).exists():
        logger.error(f"Dataset file not found: {args.dataset}")
        return 1
    
    logger.info(f"Configuration:")
    logger.info(f"  Dataset: {args.dataset}")
    logger.info(f"  ID Column: {args.id_column}")
    logger.info(f"  Source Endpoint: {args.source_endpoint}")
    logger.info(f"  Target Endpoint: {args.target_endpoint}")
    logger.info(f"  Test Sizes: {test_sizes}")
    logger.info(f"  Output Directory: {args.output_dir}")
    logger.info(f"  Database URLs:")
    logger.info(f"    Metamapper: sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    logger.info(f"    Cache: sqlite+aiosqlite:////home/ubuntu/biomapper/data/mapping_cache.db")
    
    # Initialize tester
    tester = MappingExecutorStressTester()
    
    try:
        # Run stress tests
        results = await tester.run_stress_tests(
            dataset_path=args.dataset,
            id_column=args.id_column,
            source_endpoint=args.source_endpoint,
            target_endpoint=args.target_endpoint,
            test_sizes=test_sizes,
            source_property=args.source_property,
            target_property=args.target_property
        )
        
        if not results:
            logger.error("No test results generated")
            return 1
        
        # Save results
        json_file, md_file = tester.save_results(results, args.output_dir)
        
        # Print summary
        logger.info("\\n" + "="*60)
        logger.info("PERFORMANCE TEST SUMMARY")
        logger.info("="*60)
        
        successful_tests = [r for r in results if "error" not in r]
        
        if successful_tests:
            logger.info(f"Successful tests: {len(successful_tests)}/{len(results)}")
            
            # Calculate performance trends
            if len(successful_tests) > 1:
                first_test = successful_tests[0]
                last_test = successful_tests[-1]
                
                size_ratio = last_test["input_count"] / first_test["input_count"]
                time_ratio = last_test["performance_metrics"]["execution_time_seconds"] / first_test["performance_metrics"]["execution_time_seconds"]
                
                logger.info(f"Scale factor: {size_ratio:.1f}x input size")
                logger.info(f"Time scaling: {time_ratio:.1f}x execution time")
                logger.info(f"Scaling efficiency: {size_ratio/time_ratio:.2f} (1.0 = linear scaling)")
                
                # Memory analysis
                max_memory_growth = max(r["performance_metrics"]["memory_growth_mb"] for r in successful_tests)
                logger.info(f"Maximum memory growth: {max_memory_growth:.1f} MB")
        
        logger.info(f"\\nDetailed results saved to:")
        logger.info(f"  JSON: {json_file}")
        logger.info(f"  Markdown: {md_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during stress testing: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)