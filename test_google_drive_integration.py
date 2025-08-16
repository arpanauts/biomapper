#!/usr/bin/env python3
"""
Test script for Google Drive integration.

This script tests the Google Drive sync functionality with the biomapper pipeline.
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path

# Add biomapper to path
sys.path.insert(0, '/home/ubuntu/biomapper')

from biomapper_client.client_v2 import BiomapperClient


async def test_google_drive_integration():
    """Test Google Drive integration without real credentials."""
    print("🧪 Testing Google Drive Integration Pipeline")
    print("=" * 50)
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")
        
        # Set environment variables for the test
        os.environ['OUTPUT_DIR'] = temp_dir
        os.environ['BIOMAPPER_ROOT'] = '/home/ubuntu/biomapper'
        os.environ['TIMESTAMP'] = '20240115_120000'
        
        # Initialize client with correct port
        try:
            client = BiomapperClient(base_url="http://localhost:8001")
            print("✅ BiomapperClient initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            return False
        
        # Run the integration test strategy
        try:
            print("\n🚀 Running Google Drive integration test strategy...")
            result = await client._async_run("google_drive_integration_test")
            
            if result and result.get('success', False):
                print("✅ Strategy execution completed successfully!")
                
                # Check outputs
                output_dir = Path(temp_dir)
                print(f"\n📋 Generated files in {output_dir}:")
                
                for file_path in output_dir.rglob('*'):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        print(f"  📄 {file_path.name} ({size:,} bytes)")
                
                # Check specific expected files
                expected_files = [
                    'gdrive_test_report.html',
                    'mapping_results.csv',
                    'statistics.json'
                ]
                
                print(f"\n🔍 Checking for expected files:")
                all_found = True
                for expected_file in expected_files:
                    found_files = list(output_dir.rglob(expected_file))
                    if found_files:
                        print(f"  ✅ {expected_file} - Found")
                    else:
                        print(f"  ❌ {expected_file} - Missing")
                        all_found = False
                
                # Check for visualizations
                viz_dir = output_dir / 'visualizations'
                if viz_dir.exists():
                    viz_files = list(viz_dir.glob('*.html'))
                    print(f"\n📊 Found {len(viz_files)} visualization files:")
                    for viz_file in viz_files:
                        print(f"  📈 {viz_file.name}")
                else:
                    print("\n⚠️  Visualizations directory not found")
                    all_found = False
                
                # Check Google Drive sync status
                print(f"\n☁️  Google Drive sync status:")
                if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                    print("  ✅ Credentials available - sync should have been attempted")
                else:
                    print("  ⚠️  No credentials - sync was skipped (expected for test)")
                
                return all_found
                
            else:
                print("❌ Strategy execution failed!")
                if result:
                    print(f"Error: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Strategy execution error: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_strategy_loading():
    """Test that the strategy can be loaded."""
    print("\n🔍 Testing strategy loading...")
    
    try:
        # Check if strategy file exists
        strategy_path = Path("/home/ubuntu/biomapper/configs/strategies/experimental/google_drive_integration_test.yaml")
        
        if strategy_path.exists():
            print("✅ Google Drive integration test strategy file found")
            
            # Check if sample data exists
            sample_data_path = Path("/home/ubuntu/biomapper/data/test_data/sample_proteins.tsv")
            if sample_data_path.exists():
                print("✅ Sample test data file found")
                return True
            else:
                print("❌ Sample test data file missing")
                return False
        else:
            print("❌ Google Drive integration test strategy file not found")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check strategy files: {e}")
        return False


async def main():
    """Main test function."""
    print("Google Drive Integration Test")
    print("============================")
    
    # Test 1: Strategy loading
    strategy_ok = test_strategy_loading()
    
    if strategy_ok:
        # Test 2: Full pipeline execution
        pipeline_ok = await test_google_drive_integration()
        
        if pipeline_ok:
            print("\n🎉 All tests passed! Google Drive integration is working correctly.")
            print("\n📝 To test with real Google Drive:")
            print("   1. Set GOOGLE_APPLICATION_CREDENTIALS to your service account JSON")
            print("   2. Set GOOGLE_DRIVE_TEST_FOLDER_ID to your test folder ID")
            print("   3. Run this script again")
        else:
            print("\n❌ Pipeline test failed!")
            sys.exit(1)
    else:
        print("\n❌ Strategy loading failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())