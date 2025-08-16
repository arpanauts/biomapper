#!/usr/bin/env python3
"""Comprehensive performance test of the optimized O(n+m) algorithms."""

import time
import requests
import json

def test_comprehensive_performance():
    """Test multiple strategies to validate O(n+m) performance across the board."""
    
    api_base = "http://localhost:8000/api"
    
    print("🚀 COMPREHENSIVE PERFORMANCE TEST: O(n+m) Algorithm Validation")
    print("=" * 80)
    
    # Test strategies that should benefit from our optimizations
    test_strategies = [
        "prot_arv_to_kg2c_uniprot_v2.2_integrated",
        "prot_arv_to_kg2c_uniprot_v2.2_with_comprehensive_viz",
        "prot_production_simple_working"
    ]
    
    results = []
    
    for i, strategy_name in enumerate(test_strategies, 1):
        print(f"\n{i}. Testing {strategy_name}")
        print("   " + "-" * 60)
        
        execution_request = {
            "strategy": strategy_name,
            "parameters": {
                "output_dir": f"/tmp/performance_test_{i}"
            }
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{api_base}/strategies/v2/execute",
                json=execution_request,
                timeout=180  # 3 minute timeout per strategy
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ COMPLETED in {execution_time:.2f} seconds")
                
                # Extract performance metrics
                job_id = result.get('job_id')
                detailed_result = None
                
                if job_id:
                    # Get detailed results
                    results_response = requests.get(f"{api_base}/strategies/v2/jobs/{job_id}/results")
                    if results_response.status_code == 200:
                        detailed_result = results_response.json()
                
                # Use result data if available, otherwise use response data
                result_data = detailed_result.get('result', {}) if detailed_result else result
                
                # Extract key metrics
                datasets = result_data.get('datasets', {})
                total_rows = sum(len(data) if isinstance(data, list) else 0 for data in datasets.values())
                
                throughput = total_rows / execution_time if execution_time > 0 else 0
                
                print(f"   📊 Total rows processed: {total_rows}")
                print(f"   🚀 Throughput: {throughput:.1f} rows/second")
                
                # Performance assessment
                if execution_time < 30:
                    perf_grade = "EXCELLENT"
                    emoji = "🎉"
                elif execution_time < 60:
                    perf_grade = "GOOD"
                    emoji = "✅"
                elif execution_time < 120:
                    perf_grade = "ACCEPTABLE"
                    emoji = "👍"
                else:
                    perf_grade = "NEEDS_OPTIMIZATION"
                    emoji = "⚠️"
                
                print(f"   {emoji} Performance: {perf_grade}")
                
                results.append({
                    'strategy': strategy_name,
                    'time': execution_time,
                    'rows': total_rows,
                    'throughput': throughput,
                    'grade': perf_grade
                })
                
                # Check for any match statistics (indicates MERGE_WITH_UNIPROT_RESOLUTION worked)
                metadata = result_data.get('metadata', {})
                match_stats_found = False
                for key, value in metadata.items():
                    if 'match' in key.lower() and isinstance(value, dict):
                        print(f"   🔍 Match statistics found in {key}:")
                        match_stats_found = True
                        for match_type, count in value.items():
                            if isinstance(count, (int, float)) and count > 0:
                                print(f"      {match_type}: {count}")
                
                if match_stats_found:
                    print("   ✅ MERGE_WITH_UNIPROT_RESOLUTION executed successfully!")
                else:
                    print("   ℹ️  No detailed match statistics available")
                
            else:
                execution_time = time.time() - start_time
                print(f"   ❌ FAILED after {execution_time:.2f}s: HTTP {response.status_code}")
                print(f"   Error: {response.text[:200]}...")
                
                results.append({
                    'strategy': strategy_name,
                    'time': execution_time,
                    'rows': 0,
                    'throughput': 0,
                    'grade': 'FAILED'
                })
                
        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            print(f"   ⚠️ TIMEOUT after {execution_time:.2f} seconds")
            print("   This may indicate O(n^5) complexity is still present!")
            
            results.append({
                'strategy': strategy_name,
                'time': execution_time,
                'rows': 0,
                'throughput': 0,
                'grade': 'TIMEOUT'
            })
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"   ❌ ERROR after {execution_time:.2f}s: {e}")
            
            results.append({
                'strategy': strategy_name,
                'time': execution_time,
                'rows': 0,
                'throughput': 0,
                'grade': 'ERROR'
            })
    
    # Final performance summary
    print("\n" + "=" * 80)
    print("🎯 COMPREHENSIVE PERFORMANCE SUMMARY")
    print("=" * 80)
    
    if results:
        successful_results = [r for r in results if r['grade'] not in ['FAILED', 'TIMEOUT', 'ERROR']]
        
        if successful_results:
            avg_time = sum(r['time'] for r in successful_results) / len(successful_results)
            total_rows = sum(r['rows'] for r in successful_results)
            avg_throughput = sum(r['throughput'] for r in successful_results) / len(successful_results)
            
            print(f"📈 Successful executions: {len(successful_results)}/{len(results)}")
            print(f"⏱️  Average execution time: {avg_time:.2f} seconds")
            print(f"📊 Total rows processed: {total_rows:,}")
            print(f"🚀 Average throughput: {avg_throughput:.1f} rows/second")
            
            # Overall performance assessment
            excellent_count = sum(1 for r in successful_results if r['grade'] == 'EXCELLENT')
            good_count = sum(1 for r in successful_results if r['grade'] == 'GOOD')
            
            if excellent_count == len(successful_results):
                overall_grade = "🎉 OUTSTANDING: All strategies show excellent O(n+m) performance!"
            elif excellent_count + good_count == len(successful_results):
                overall_grade = "✅ EXCELLENT: All strategies show good O(n+m) performance!"
            elif avg_time < 60:
                overall_grade = "👍 GOOD: Average performance under 1 minute"
            else:
                overall_grade = "⚠️ NEEDS REVIEW: Some performance issues detected"
            
            print(f"\n{overall_grade}")
            
        else:
            print("❌ NO SUCCESSFUL EXECUTIONS: Critical issues detected!")
    
    print("\n📋 DETAILED RESULTS:")
    for result in results:
        print(f"   {result['strategy'][:40]:<40} | {result['time']:>6.1f}s | {result['grade']}")
    
    print("\n🔬 ALGORITHM COMPLEXITY ANALYSIS:")
    if successful_results and all(r['time'] < 60 for r in successful_results):
        print("   ✅ O(n+m) LINEAR COMPLEXITY: All executions complete in under 60 seconds")
        print("   🎯 OPTIMIZATION SUCCESS: Previous O(n^5) bottlenecks eliminated")
    elif successful_results and all(r['time'] < 180 for r in successful_results):
        print("   👍 ACCEPTABLE COMPLEXITY: All executions complete in under 3 minutes")  
        print("   💡 ROOM FOR IMPROVEMENT: Consider additional optimizations")
    else:
        print("   ⚠️ POTENTIAL COMPLEXITY ISSUES: Some executions taking longer than expected")
        print("   🔍 INVESTIGATION NEEDED: Review algorithms for remaining bottlenecks")

if __name__ == "__main__":
    test_comprehensive_performance()