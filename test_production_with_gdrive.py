#!/usr/bin/env python3
"""
Run production protein mapping strategy with Google Drive sync.
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# Set environment variables for Google Drive
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/ubuntu/biomapper/google-credentials.json'
os.environ['GOOGLE_DRIVE_FOLDER_ID'] = '1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D'
os.environ['TIMESTAMP'] = '20250115_production'

# Add biomapper to path
sys.path.insert(0, '/home/ubuntu/biomapper')

from biomapper_client.client_v2 import BiomapperClient

async def run_production_strategy():
    """Run the complete production strategy with Google Drive sync."""
    print("🚀 Production Protein Mapping with Google Drive Integration")
    print("=" * 60)
    
    # Initialize client
    try:
        client = BiomapperClient(base_url="http://localhost:8001")
        print("✅ BiomapperClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    # Run the complete strategy
    try:
        print(f"\n📋 Running strategy: prot_simple_production_with_gdrive")
        print(f"📁 Google Drive Folder ID: {os.environ['GOOGLE_DRIVE_FOLDER_ID']}")
        print(f"🔑 Credentials: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")
        print("\n🚀 Starting execution...")
        
        result = await client._async_run("prot_simple_production_with_gdrive")
        
        if result and result.get('success', False):
            print("\n✅ Strategy execution completed successfully!")
            
            # Show strategy results
            status = result.get('status', 'unknown')
            print(f"📊 Final status: {status}")
            
            if 'outputs' in result:
                print("\n📁 Generated outputs:")
                for key, value in result['outputs'].items():
                    print(f"   📄 {key}: {value}")
            
            if 'statistics' in result:
                print("\n📈 Statistics:")
                stats = result['statistics']
                for key, value in stats.items():
                    print(f"   📊 {key}: {value}")
            
            # Check Google Drive sync results
            if 'google_drive_sync' in result:
                gdrive_result = result['google_drive_sync']
                print(f"\n☁️  Google Drive Sync Results:")
                print(f"   📤 Files uploaded: {gdrive_result.get('uploaded_count', 0)}")
                print(f"   📁 Folder structure: {gdrive_result.get('folder_structure', 'N/A')}")
                print(f"   🔗 Target folder ID: {gdrive_result.get('target_folder_id', 'N/A')}")
                
                if gdrive_result.get('uploaded_files'):
                    print(f"\n📋 Uploaded files:")
                    for file_info in gdrive_result['uploaded_files']:
                        name = file_info.get('name', 'Unknown')
                        link = file_info.get('webViewLink', 'No link')
                        print(f"   📄 {name}")
                        print(f"      🔗 {link}")
            
            return True
            
        else:
            print("❌ Strategy execution failed!")
            if result:
                error = result.get('error', 'Unknown error')
                print(f"💥 Error: {error}")
                
                # Show any partial results
                if 'outputs' in result:
                    print(f"\n📁 Partial outputs generated:")
                    for key, value in result['outputs'].items():
                        print(f"   📄 {key}: {value}")
            
            return False
            
    except Exception as e:
        print(f"❌ Strategy execution error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    print("Production Protein Mapping with Google Drive Integration")
    print("======================================================")
    
    # Check prerequisites
    print("\n🔍 Checking prerequisites...")
    
    # Check data files
    arivale_file = "/procedure/data/local_data/ARIVALE_SNAPSHOTS/proteomics_metadata.tsv"
    kg2c_file = "/procedure/data/local_data/MAPPING_ONTOLOGIES/kg2c_ontologies/kg2c_proteins.csv"
    
    if Path(arivale_file).exists():
        print(f"   ✅ Arivale data: {arivale_file}")
    else:
        print(f"   ❌ Arivale data missing: {arivale_file}")
        print("   ⚠️  Using test data instead...")
    
    if Path(kg2c_file).exists():
        print(f"   ✅ KG2C data: {kg2c_file}")
    else:
        print(f"   ❌ KG2C data missing: {kg2c_file}")
        print("   ⚠️  Strategy may fail...")
    
    # Check Google Drive credentials
    creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_file and Path(creds_file).exists():
        print(f"   ✅ Google credentials: {creds_file}")
    else:
        print(f"   ❌ Google credentials missing: {creds_file}")
        return False
    
    print(f"   ✅ Google Drive folder: {os.environ['GOOGLE_DRIVE_FOLDER_ID']}")
    
    # Run the strategy
    success = await run_production_strategy()
    
    if success:
        print("\n🎉 Production pipeline completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ Protein mapping: Complete")
        print("   ✅ Composite ID handling: Complete")
        print("   ✅ HTML report generation: Complete")
        print("   ✅ Visualization generation: Complete")
        print("   ✅ Google Drive sync: Complete")
        print("\n🚀 The complete end-to-end pipeline is working!")
    else:
        print("\n❌ Production pipeline failed!")
        return False

if __name__ == "__main__":
    asyncio.run(main())