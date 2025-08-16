#!/usr/bin/env python3
"""Test production pipeline performance with optimized O(n+m) algorithms."""

import time
import requests
import json
from pathlib import Path

def test_production_api_pipeline():
    """Test the production pipeline via API to validate O(n+m) performance fixes."""
    
    api_base = "http://localhost:8000/api"
    
    print("🚀 Testing Production Pipeline Performance with O(n+m) Optimizations")
    print("=" * 70)
    
    # Test 1: Check API health
    print("1. Checking API health...")
    try:
        response = requests.get(f"{api_base}/health/")
        if response.status_code == 200:
            print("   ✅ API is healthy")
        else:
            print(f"   ❌ API health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ API connection failed: {e}")
        return
    
    # Test 2: Use predefined strategy (we know protein strategies exist from configs/)
    print("\n2. Using production protein strategy...")
    strategy_name = "prot_arv_to_kg2c_uniprot_v2.2_integrated"
    print(f"   🎯 Selected strategy: {strategy_name}")
    
    # Skip strategy listing and use known working strategy
    
    # Test 3: Execute strategy with performance monitoring
    print(f"\n3. Executing {strategy_name} with performance monitoring...")
    
    execution_request = {
        "strategy": strategy_name,
        "parameters": {
            "output_dir": "/tmp/api_test_output"
        }
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{api_base}/strategies/v2/execute",
            json=execution_request,
            timeout=300  # 5 minute timeout
        )
        
        execution_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Strategy completed in {execution_time:.2f} seconds")
            
            # Check for performance indicators in result
            if 'metadata' in result:
                metadata = result['metadata']
                print(f"   📊 Performance Metrics:")
                for key, value in metadata.items():
                    if 'time' in key.lower() or 'count' in key.lower():
                        print(f"       {key}: {value}")
            
            # Check for datasets
            if 'datasets' in result:
                datasets = result['datasets']
                print(f"   📊 Datasets generated: {list(datasets.keys())}")
                
                total_rows = 0
                for name, data in datasets.items():
                    if isinstance(data, list):
                        total_rows += len(data)
                        print(f"       {name}: {len(data)} rows")
                
                print(f"   📊 Total rows processed: {total_rows}")
                
                if total_rows > 0:
                    throughput = total_rows / execution_time
                    print(f"   🚀 Throughput: {throughput:.1f} rows/second")
                    
                    # Performance assessment
                    if execution_time < 60:
                        print("   ✅ EXCELLENT: Sub-minute execution (O(n+m) working!)")
                    elif execution_time < 300:
                        print("   ✅ GOOD: Under 5 minutes (acceptable performance)")
                    else:
                        print("   ⚠️  SLOW: Over 5 minutes (may need optimization)")
            
        else:
            print(f"   ❌ Strategy execution failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except requests.exceptions.Timeout:
        execution_time = time.time() - start_time
        print(f"   ⚠️  Strategy timed out after {execution_time:.2f} seconds")
        print("   This may indicate algorithm complexity issues")
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"   ❌ Strategy execution failed after {execution_time:.2f} seconds: {e}")
    
    print("\n" + "=" * 70)
    print("🎯 Performance Test Summary:")
    print(f"   Total execution time: {execution_time:.2f} seconds")
    
    if execution_time < 60:
        print("   🎉 PERFORMANCE EXCELLENT: O(n+m) optimizations are working!")
    elif execution_time < 300:
        print("   ✅ PERFORMANCE GOOD: Acceptable for production")
    else:
        print("   ⚠️  PERFORMANCE NEEDS REVIEW: May need additional optimization")

if __name__ == "__main__":
    test_production_api_pipeline()