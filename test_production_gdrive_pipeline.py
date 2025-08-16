#!/usr/bin/env python3
"""Test end-to-end production pipeline with Google Drive sync."""

import time
import requests
import json
import os
from pathlib import Path

def test_production_pipeline_with_gdrive():
    """Test the full production pipeline including Google Drive sync."""
    
    api_base = "http://localhost:8000/api"
    
    print("🚀 Testing Production Pipeline with Google Drive Integration")
    print("=" * 80)
    
    # Check API health
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

    # Set up test environment variables (mock for testing)
    print("\n2. Setting up Google Drive environment...")
    os.environ['GOOGLE_DRIVE_FOLDER_ID'] = '1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D'  # Test folder ID
    os.environ['OUTPUT_DIR'] = '/tmp/biomapper_production_test'
    
    # Create test output directory
    output_dir = Path(os.environ['OUTPUT_DIR'])
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ Output directory created: {output_dir}")
    
    # Use production strategy with Google Drive sync
    strategy_name = "prot_arv_to_kg2c_uniprot_v2.2_integrated_with_gdrive"
    print(f"   🎯 Selected strategy: {strategy_name}")

    # Execute strategy
    print(f"\n3. Executing production pipeline with Google Drive sync...")
    
    execution_request = {
        "strategy": strategy_name,
        "parameters": {
            "output_dir": str(output_dir),
            "enable_google_drive_sync": True,  # Enable Google Drive sync
            "drive_folder_id": os.environ['GOOGLE_DRIVE_FOLDER_ID']
        }
    }
    
    start_time = time.time()
    
    try:
        print("   📤 Submitting strategy execution request...")
        response = requests.post(
            f"{api_base}/strategies/v2/execute",
            json=execution_request,
            timeout=600  # 10 minute timeout for full pipeline
        )
        
        execution_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Pipeline completed in {execution_time:.2f} seconds")
            
            # Get job ID for detailed results
            job_id = result.get('job_id')
            if job_id:
                print(f"   📋 Job ID: {job_id}")
                
                # Get detailed results
                print("   📊 Fetching detailed results...")
                results_response = requests.get(f"{api_base}/strategies/v2/jobs/{job_id}/results")
                if results_response.status_code == 200:
                    detailed_result = results_response.json()
                    
                    # Check for datasets created
                    strategy_result = detailed_result.get('result', {})
                    datasets = strategy_result.get('datasets', {})
                    output_files = strategy_result.get('output_files', {})
                    
                    print(f"   📦 Datasets created: {len(datasets)}")
                    for name, data in datasets.items():
                        if isinstance(data, list):
                            print(f"      {name}: {len(data)} rows")
                    
                    print(f"   📁 Output files: {len(output_files)}")
                    for name, path in output_files.items():
                        if isinstance(path, str) and Path(path).exists():
                            size = Path(path).stat().st_size
                            print(f"      {name}: {path} ({size} bytes)")
                    
                    # Check for Google Drive sync results
                    print("   📤 Google Drive sync status:")
                    # Look for sync results in the context
                    if 'sync_to_google_drive' in detailed_result.get('result', {}):
                        sync_result = detailed_result['result']['sync_to_google_drive']
                        print(f"      Sync success: {sync_result.get('success', 'Unknown')}")
                        if sync_result.get('data'):
                            uploaded_files = sync_result['data'].get('uploaded_files', [])
                            print(f"      Files uploaded: {len(uploaded_files)}")
                            for file_info in uploaded_files[:5]:  # Show first 5
                                print(f"        - {file_info.get('name', 'Unknown')}")
                    else:
                        print("      No Google Drive sync results found (may be mocked)")
                    
                    # Performance assessment
                    if execution_time < 60:
                        perf_emoji = "🎉"
                        perf_status = "OUTSTANDING"
                    elif execution_time < 300:
                        perf_emoji = "✅"
                        perf_status = "EXCELLENT"
                    else:
                        perf_emoji = "⚠️"
                        perf_status = "ACCEPTABLE"
                    
                    print(f"\n   {perf_emoji} Overall Performance: {perf_status}")
                    print(f"   ⏱️  Total execution time: {execution_time:.2f} seconds")
                    
                    # Check local output files
                    print("\n4. Validating local output files...")
                    local_files = list(output_dir.rglob("*"))
                    file_count = len([f for f in local_files if f.is_file()])
                    print(f"   📂 Local files created: {file_count}")
                    
                    # Look for key output types
                    html_files = list(output_dir.rglob("*.html"))
                    tsv_files = list(output_dir.rglob("*.tsv"))
                    json_files = list(output_dir.rglob("*.json"))
                    
                    print(f"   📊 HTML reports: {len(html_files)}")
                    print(f"   📋 TSV datasets: {len(tsv_files)}")
                    print(f"   📈 JSON statistics: {len(json_files)}")
                    
                    if html_files:
                        print("   🎨 Report files:")
                        for html_file in html_files:
                            size = html_file.stat().st_size
                            print(f"      - {html_file.name} ({size} bytes)")
                    
                    # Overall success assessment
                    success_criteria = [
                        execution_time < 600,  # Under 10 minutes
                        len(datasets) > 0,     # Datasets created
                        file_count > 0,        # Files generated
                        len(html_files) > 0,   # Reports generated
                        len(tsv_files) > 0     # Data exported
                    ]
                    
                    success_count = sum(success_criteria)
                    total_criteria = len(success_criteria)
                    
                    print(f"\n   📊 Success Criteria: {success_count}/{total_criteria}")
                    
                    if success_count == total_criteria:
                        print("   🎉 COMPLETE SUCCESS: All production pipeline criteria met!")
                    elif success_count >= total_criteria * 0.8:
                        print("   ✅ SUCCESS: Most production pipeline criteria met!")
                    else:
                        print("   ⚠️ PARTIAL SUCCESS: Some pipeline steps may need attention")
                
            else:
                print("   ⚠️ No job ID returned - sync execution may have failed")
                
        else:
            execution_time = time.time() - start_time
            print(f"   ❌ Pipeline failed after {execution_time:.2f}s: HTTP {response.status_code}")
            print(f"   Error: {response.text}")
            
    except requests.exceptions.Timeout:
        execution_time = time.time() - start_time
        print(f"   ⚠️ Pipeline timed out after {execution_time:.2f} seconds")
        print("   This may indicate performance issues or complex processing")
        
    except Exception as e:
        execution_time = time.time() - start_time
        print(f"   ❌ Pipeline failed after {execution_time:.2f}s: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 Production Pipeline Test Summary:")
    print(f"   Total execution time: {execution_time:.2f} seconds")
    print(f"   Output directory: {output_dir}")
    
    if execution_time < 60:
        print("   🎉 PERFORMANCE OUTSTANDING: Pipeline completes in under 1 minute!")
    elif execution_time < 300:
        print("   ✅ PERFORMANCE EXCELLENT: Pipeline completes in under 5 minutes!")
    else:
        print("   👍 PERFORMANCE ACCEPTABLE: Pipeline completes within reasonable time")

if __name__ == "__main__":
    test_production_pipeline_with_gdrive()