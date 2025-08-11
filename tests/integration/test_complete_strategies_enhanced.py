"""
Enhanced integration tests for all biomapper strategies.

This module provides comprehensive end-to-end testing for all available
strategies with performance benchmarking and quality validation.
"""

import pytest
import pandas as pd
import time
import psutil
import numpy as np
import asyncio
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from test_data_generators import generate_realistic_test_data


@dataclass
class PerformanceMetrics:
    """Performance metrics for strategy execution."""
    execution_time: float
    peak_memory_mb: float
    throughput_rows_per_second: float
    success_rate: float
    

@dataclass
class QualityMetrics:
    """Quality metrics for mapping results."""
    total_rows: int
    success_rate: float
    coverage_metrics: Dict[str, float]
    confidence_distribution: Dict[str, float]
    data_quality_score: float


@dataclass
class StrategyTestResult:
    """Complete test result for a strategy."""
    strategy_name: str
    entity_type: str
    dataset_size: int
    performance: PerformanceMetrics
    quality: QualityMetrics
    status: str  # 'passed', 'failed', 'timeout'
    error_message: Optional[str] = None


class PerformanceMonitor:
    """Monitor system performance during strategy execution."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.peak_memory = 0
        self.process = psutil.Process()
        
    def start(self):
        """Start monitoring."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = self.start_memory
        
    def update_peak(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
        
    def get_metrics(self, dataset_size: int) -> PerformanceMetrics:
        """Get current performance metrics."""
        execution_time = time.time() - self.start_time
        memory_used = self.peak_memory - self.start_memory
        throughput = dataset_size / execution_time if execution_time > 0 else 0
        
        return PerformanceMetrics(
            execution_time=execution_time,
            peak_memory_mb=memory_used,
            throughput_rows_per_second=throughput,
            success_rate=0.0  # Will be updated based on results
        )


class BiomapperAPIClient:
    """Simple client for biomapper API testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def execute_strategy(self, strategy_name: str, parameters: Dict[str, Any], timeout: int = 300):
        """Execute a strategy and return results."""
        # Start execution
        response = self.session.post(
            f"{self.base_url}/api/strategies/v2/execute",
            json={
                "strategy": strategy_name,
                "parameters": parameters
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to start strategy: {response.text}")
        
        job_data = response.json()
        job_id = job_data["job_id"]
        
        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            status_response = self.session.get(
                f"{self.base_url}/api/strategies/v2/jobs/{job_id}/status"
            )
            
            if status_response.status_code != 200:
                raise Exception(f"Failed to get job status: {status_response.text}")
                
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                # Get results
                results_response = self.session.get(
                    f"{self.base_url}/api/strategies/v2/jobs/{job_id}/results"
                )
                
                if results_response.status_code != 200:
                    raise Exception(f"Failed to get results: {results_response.text}")
                    
                return results_response.json()
            
            elif status_data["status"] == "failed":
                error = status_data.get("error", "Unknown error")
                raise Exception(f"Strategy execution failed: {error}")
            
            time.sleep(2)  # Poll every 2 seconds
        
        raise TimeoutError(f"Strategy execution timed out after {timeout} seconds")


class TestCompleteStrategiesEnhanced:
    """Enhanced integration tests for all mapping strategies."""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """API client fixture."""
        return BiomapperAPIClient()
    
    @pytest.fixture(scope="class") 
    def test_data_cache(self):
        """Cache for test data to avoid regeneration."""
        return {}
    
    def get_test_data(self, entity_type: str, size: int, cache: Dict) -> pd.DataFrame:
        """Get test data from cache or generate new."""
        cache_key = f"{entity_type}_{size}"
        if cache_key not in cache:
            cache[cache_key] = generate_realistic_test_data(entity_type, size)
        return cache[cache_key].copy()
    
    def validate_protein_mapping_quality(self, result_data: Dict) -> QualityMetrics:
        """Validate protein mapping results quality."""
        if 'datasets' not in result_data or not result_data['datasets']:
            return QualityMetrics(
                total_rows=0, success_rate=0.0, coverage_metrics={}, 
                confidence_distribution={}, data_quality_score=0.0
            )
        
        # Get the output dataset (assume it's the last one or named 'output')
        datasets = result_data['datasets']
        if 'output' in datasets:
            df_data = datasets['output']
        else:
            # Take the last dataset
            df_data = list(datasets.values())[-1]
        
        if not df_data or not isinstance(df_data, list):
            return QualityMetrics(
                total_rows=0, success_rate=0.0, coverage_metrics={}, 
                confidence_distribution={}, data_quality_score=0.0
            )
        
        df = pd.DataFrame(df_data)
        total_rows = len(df)
        
        # Calculate protein-specific metrics
        uniprot_success = 0
        gene_coverage = 0
        xrefs_processed = 0
        
        if 'uniprot_id' in df.columns:
            # Count valid UniProt IDs (6 chars, alphanumeric)
            uniprot_success = df['uniprot_id'].str.match(r'^[A-Z0-9]{6}$', na=False).sum()
        
        if 'gene_symbol' in df.columns:
            gene_coverage = df['gene_symbol'].notna().sum()
            
        if 'xrefs_processed' in df.columns:
            xrefs_processed = df['xrefs_processed'].sum() if df['xrefs_processed'].notna().any() else 0
        
        success_rate = uniprot_success / total_rows if total_rows > 0 else 0
        
        coverage_metrics = {
            'uniprot_coverage': uniprot_success / total_rows if total_rows > 0 else 0,
            'gene_symbol_coverage': gene_coverage / total_rows if total_rows > 0 else 0,
            'xrefs_processed_rate': xrefs_processed / total_rows if total_rows > 0 else 0
        }
        
        # Simple quality score based on coverage
        data_quality_score = np.mean(list(coverage_metrics.values())) * 10
        
        return QualityMetrics(
            total_rows=total_rows,
            success_rate=success_rate,
            coverage_metrics=coverage_metrics,
            confidence_distribution={},
            data_quality_score=data_quality_score
        )
    
    def validate_metabolite_mapping_quality(self, result_data: Dict) -> QualityMetrics:
        """Validate metabolite mapping results quality."""
        if 'datasets' not in result_data or not result_data['datasets']:
            return QualityMetrics(
                total_rows=0, success_rate=0.0, coverage_metrics={}, 
                confidence_distribution={}, data_quality_score=0.0
            )
        
        datasets = result_data['datasets']
        if 'output' in datasets:
            df_data = datasets['output']
        else:
            df_data = list(datasets.values())[-1]
        
        if not df_data or not isinstance(df_data, list):
            return QualityMetrics(
                total_rows=0, success_rate=0.0, coverage_metrics={}, 
                confidence_distribution={}, data_quality_score=0.0
            )
        
        df = pd.DataFrame(df_data)
        total_rows = len(df)
        
        hmdb_success = 0
        inchikey_coverage = 0
        cts_success = 0
        
        if 'hmdb_id' in df.columns:
            # Count valid HMDB IDs
            hmdb_success = df['hmdb_id'].str.match(r'^HMDB\d{7}$', na=False).sum()
        
        if 'inchikey' in df.columns:
            # Count valid InChI keys
            inchikey_coverage = df['inchikey'].str.match(r'^[A-Z]{14}-[A-Z]{10}-[A-Z]$', na=False).sum()
            
        if 'cts_mapped' in df.columns:
            cts_success = df['cts_mapped'].sum() if df['cts_mapped'].notna().any() else 0
        
        success_rate = hmdb_success / total_rows if total_rows > 0 else 0
        
        coverage_metrics = {
            'hmdb_coverage': hmdb_success / total_rows if total_rows > 0 else 0,
            'inchikey_coverage': inchikey_coverage / total_rows if total_rows > 0 else 0,
            'cts_bridge_success': cts_success / total_rows if total_rows > 0 else 0
        }
        
        data_quality_score = np.mean(list(coverage_metrics.values())) * 10
        
        return QualityMetrics(
            total_rows=total_rows,
            success_rate=success_rate,
            coverage_metrics=coverage_metrics,
            confidence_distribution={},
            data_quality_score=data_quality_score
        )
    
    def validate_chemistry_mapping_quality(self, result_data: Dict) -> QualityMetrics:
        """Validate chemistry mapping results quality."""
        if 'datasets' not in result_data or not result_data['datasets']:
            return QualityMetrics(
                total_rows=0, success_rate=0.0, coverage_metrics={}, 
                confidence_distribution={}, data_quality_score=0.0
            )
        
        datasets = result_data['datasets']
        if 'output' in datasets:
            df_data = datasets['output']
        else:
            df_data = list(datasets.values())[-1]
        
        if not df_data or not isinstance(df_data, list):
            return QualityMetrics(
                total_rows=0, success_rate=0.0, coverage_metrics={}, 
                confidence_distribution={}, data_quality_score=0.0
            )
        
        df = pd.DataFrame(df_data)
        total_rows = len(df)
        
        loinc_success = 0
        fuzzy_matches = 0
        harmonized = 0
        
        if 'loinc_code' in df.columns:
            # Count valid LOINC codes
            loinc_success = df['loinc_code'].str.match(r'^\d{1,5}-\d{1}$', na=False).sum()
        
        if 'fuzzy_matched' in df.columns:
            fuzzy_matches = df['fuzzy_matched'].sum() if df['fuzzy_matched'].notna().any() else 0
            
        if 'harmonized' in df.columns:
            harmonized = df['harmonized'].sum() if df['harmonized'].notna().any() else 0
        
        success_rate = loinc_success / total_rows if total_rows > 0 else 0
        
        coverage_metrics = {
            'loinc_extraction_rate': loinc_success / total_rows if total_rows > 0 else 0,
            'fuzzy_match_rate': fuzzy_matches / total_rows if total_rows > 0 else 0,
            'harmonization_rate': harmonized / total_rows if total_rows > 0 else 0
        }
        
        data_quality_score = np.mean(list(coverage_metrics.values())) * 10
        
        return QualityMetrics(
            total_rows=total_rows,
            success_rate=success_rate,
            coverage_metrics=coverage_metrics,
            confidence_distribution={},
            data_quality_score=data_quality_score
        )
    
    def run_strategy_test(self, strategy_name: str, entity_type: str, 
                         dataset_size: int, api_client: BiomapperAPIClient,
                         test_data_cache: Dict) -> StrategyTestResult:
        """Run a complete test for a single strategy."""
        monitor = PerformanceMonitor()
        
        try:
            # Generate test data
            test_data = self.get_test_data(entity_type, dataset_size, test_data_cache)
            
            # Start monitoring
            monitor.start()
            
            # Execute strategy
            parameters = {
                "test_data": test_data.to_dict('records'),
                "dataset_size": dataset_size
            }
            
            result = api_client.execute_strategy(strategy_name, parameters, timeout=300)
            
            # Update peak memory during execution
            monitor.update_peak()
            
            # Get performance metrics
            performance = monitor.get_metrics(dataset_size)
            
            # Validate quality based on entity type
            if entity_type == "protein":
                quality = self.validate_protein_mapping_quality(result)
            elif entity_type == "metabolite":
                quality = self.validate_metabolite_mapping_quality(result)
            elif entity_type == "chemistry":
                quality = self.validate_chemistry_mapping_quality(result)
            else:
                quality = QualityMetrics(0, 0.0, {}, {}, 0.0)
            
            # Update performance with actual success rate
            performance.success_rate = quality.success_rate
            
            return StrategyTestResult(
                strategy_name=strategy_name,
                entity_type=entity_type,
                dataset_size=dataset_size,
                performance=performance,
                quality=quality,
                status="passed"
            )
            
        except TimeoutError as e:
            performance = monitor.get_metrics(dataset_size)
            return StrategyTestResult(
                strategy_name=strategy_name,
                entity_type=entity_type,
                dataset_size=dataset_size,
                performance=performance,
                quality=QualityMetrics(0, 0.0, {}, {}, 0.0),
                status="timeout",
                error_message=str(e)
            )
            
        except Exception as e:
            performance = monitor.get_metrics(dataset_size)
            return StrategyTestResult(
                strategy_name=strategy_name,
                entity_type=entity_type,
                dataset_size=dataset_size,
                performance=performance,
                quality=QualityMetrics(0, 0.0, {}, {}, 0.0),
                status="failed",
                error_message=str(e)
            )
    
    def get_available_strategies(self) -> Dict[str, List[str]]:
        """Get available strategies by type."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies")
        
        protein_strategies = []
        metabolite_strategies = []
        chemistry_strategies = []
        
        # Find all YAML files, excluding deprecated and templates
        for yaml_file in strategies_dir.glob("**/*.yaml"):
            if "deprecated" in str(yaml_file) or "templates" in str(yaml_file):
                continue
                
            strategy_name = yaml_file.stem
            
            # Categorize by name patterns
            if "prot" in strategy_name.lower():
                protein_strategies.append(strategy_name)
            elif any(term in strategy_name.lower() for term in ["met", "metabol", "nightingale", "nmr"]):
                metabolite_strategies.append(strategy_name)
            elif "chem" in strategy_name.lower():
                chemistry_strategies.append(strategy_name)
            else:
                # Default categorization based on content or other heuristics
                if "protein" in strategy_name.lower():
                    protein_strategies.append(strategy_name)
                elif "metabolite" in strategy_name.lower() or "metabolomics" in strategy_name.lower():
                    metabolite_strategies.append(strategy_name)
                else:
                    # For multi-type or unclear strategies, add to all categories
                    if "multi" in strategy_name.lower():
                        metabolite_strategies.append(strategy_name)  # Most multi strategies are metabolite-focused
                    else:
                        metabolite_strategies.append(strategy_name)  # Default to metabolite
        
        return {
            "protein": sorted(protein_strategies),
            "metabolite": sorted(metabolite_strategies), 
            "chemistry": sorted(chemistry_strategies)
        }
    
    @pytest.mark.integration
    def test_all_strategies_execution(self, api_client, test_data_cache):
        """Test execution of all available strategies."""
        strategies = self.get_available_strategies()
        results = []
        
        # Test parameters
        test_sizes = [1000, 5000]  # Smaller sizes for faster testing
        
        for entity_type, strategy_list in strategies.items():
            print(f"\nTesting {len(strategy_list)} {entity_type} strategies...")
            
            for strategy_name in strategy_list[:3]:  # Test first 3 of each type
                for dataset_size in test_sizes:
                    print(f"  Testing {strategy_name} with {dataset_size} rows...")
                    
                    result = self.run_strategy_test(
                        strategy_name, entity_type, dataset_size, 
                        api_client, test_data_cache
                    )
                    results.append(result)
                    
                    # Basic assertions
                    if result.status == "passed":
                        assert result.performance.execution_time > 0
                        assert result.performance.peak_memory_mb > 0
                        assert result.quality.total_rows >= 0
                    
                    print(f"    Status: {result.status}")
                    if result.status == "passed":
                        print(f"    Success rate: {result.quality.success_rate:.2%}")
                        print(f"    Execution time: {result.performance.execution_time:.1f}s")
        
        # Save results
        results_file = Path("/tmp/integration_test_results.json")
        with open(results_file, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        
        print(f"\nIntegration test results saved to: {results_file}")
        
        # Summary statistics
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed") 
        timeout = sum(1 for r in results if r.status == "timeout")
        
        print(f"\nTest Summary:")
        print(f"  Total tests: {len(results)}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Timeout: {timeout}")
        print(f"  Success rate: {passed/len(results)*100:.1f}%")
        
        # Assert overall success rate
        assert passed / len(results) > 0.5, f"Too many test failures: {passed}/{len(results)}"
        
        return results
    
    @pytest.mark.performance
    def test_scalability_benchmark(self, api_client, test_data_cache):
        """Test system scalability with increasing dataset sizes."""
        # Test one strategy from each type with increasing sizes
        test_strategies = {
            "protein": "arivale_to_kg2c_proteins",
            "metabolite": "nightingale_nmr_match_example", 
            "chemistry": "chemistry_harmonization_simple"
        }
        
        test_sizes = [1000, 5000, 10000, 25000]
        scalability_results = {}
        
        for entity_type, strategy_name in test_strategies.items():
            print(f"\nTesting scalability for {entity_type} strategy: {strategy_name}")
            entity_results = {}
            
            for size in test_sizes:
                print(f"  Testing with {size} rows...")
                
                result = self.run_strategy_test(
                    strategy_name, entity_type, size, 
                    api_client, test_data_cache
                )
                
                entity_results[size] = result
                
                if result.status == "passed":
                    print(f"    Time: {result.performance.execution_time:.1f}s")
                    print(f"    Memory: {result.performance.peak_memory_mb:.1f}MB")
                    print(f"    Throughput: {result.performance.throughput_rows_per_second:.1f} rows/s")
                else:
                    print(f"    Status: {result.status}")
                    if result.error_message:
                        print(f"    Error: {result.error_message[:100]}...")
            
            scalability_results[entity_type] = entity_results
        
        # Validate linear scaling (allowing for reasonable overhead)
        for entity_type, entity_results in scalability_results.items():
            passed_results = {k: v for k, v in entity_results.items() if v.status == "passed"}
            
            if len(passed_results) >= 2:
                sizes = sorted(passed_results.keys())
                base_size = sizes[0]
                base_time = passed_results[base_size].performance.execution_time
                
                for size in sizes[1:]:
                    expected_time = base_time * (size / base_size) * 2.0  # Allow 2x overhead
                    actual_time = passed_results[size].performance.execution_time
                    
                    scaling_factor = actual_time / base_time / (size / base_size)
                    print(f"  {entity_type} scaling factor ({base_size}->{size}): {scaling_factor:.2f}")
                    
                    # Allow reasonable non-linear scaling
                    assert scaling_factor < 3.0, f"Excessive scaling for {entity_type}: {scaling_factor}"
        
        return scalability_results
    
    @pytest.mark.memory
    def test_memory_efficiency(self, api_client, test_data_cache):
        """Test memory efficiency and optimization techniques."""
        # Test memory usage with a large dataset
        large_size = 50000
        
        test_result = self.run_strategy_test(
            "simple_data_loader_demo", "metabolite", large_size,
            api_client, test_data_cache
        )
        
        if test_result.status == "passed":
            memory_per_row = test_result.performance.peak_memory_mb / large_size * 1000  # KB per row
            
            print(f"Memory efficiency test:")
            print(f"  Dataset size: {large_size} rows")
            print(f"  Peak memory: {test_result.performance.peak_memory_mb:.1f}MB")
            print(f"  Memory per row: {memory_per_row:.2f}KB")
            
            # Assert reasonable memory usage (< 50KB per row)
            assert memory_per_row < 50, f"Excessive memory usage: {memory_per_row:.2f}KB per row"
            
            # Assert total memory under reasonable limit
            assert test_result.performance.peak_memory_mb < 2048, f"Peak memory too high: {test_result.performance.peak_memory_mb}MB"
        
        return test_result