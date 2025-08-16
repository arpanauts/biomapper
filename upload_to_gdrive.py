#!/usr/bin/env python3
"""
Upload production results to Google Drive
"""
import asyncio
from biomapper.core.strategy_actions.io.sync_to_google_drive_v2 import (
    SyncToGoogleDriveV2Action, 
    SyncToGoogleDriveV2Params
)
from datetime import datetime

async def upload_results():
    print("Uploading production results to Google Drive...")
    
    # Create action
    action = SyncToGoogleDriveV2Action()
    
    # Create params - use the production strategy name for organization
    params = SyncToGoogleDriveV2Params(
        drive_folder_id="1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D",
        local_directory="/tmp/biomapper_results",
        include_patterns=["*.tsv", "*.json", "*.html", "*.txt"],
        strategy_name="production_simple_working",
        strategy_version="1.0.0",
        auto_organize=True,
        create_summary=True
    )
    
    # Create context
    context = {}
    
    # Execute
    result = await action.execute_typed(
        current_identifiers=[],
        current_ontology_type="protein",
        params=params,
        source_endpoint=None,
        target_endpoint=None,
        context=context
    )
    
    print(f"\n{'='*60}")
    if result.success:
        print("✅ UPLOAD SUCCESSFUL!")
        data = result.data
        print(f"\nUploaded {data.get('uploaded_count', 0)} files")
        print(f"Folder structure: {data.get('folder_structure', '')}")
        
        uploaded_files = data.get('uploaded_files', [])
        if uploaded_files:
            print("\nUploaded files:")
            for f in uploaded_files:
                print(f"  - {f['name']}")
                if 'webViewLink' in f:
                    print(f"    View: {f['webViewLink']}")
        
        errors = data.get('errors', [])
        if errors:
            print("\nErrors encountered:")
            for e in errors:
                print(f"  - {e}")
    else:
        print(f"❌ UPLOAD FAILED: {result.error}")
    
    print("="*60)
    return result

if __name__ == "__main__":
    print("="*60)
    print("GOOGLE DRIVE UPLOAD - PRODUCTION RESULTS")
    print("="*60)
    print(f"Timestamp: {datetime.now()}")
    print("Source: /tmp/biomapper_results/")
    print("Target: Data Harmonization folder in Google Drive")
    print("="*60)
    print()
    
    result = asyncio.run(upload_results())
    
    if result.success:
        print("\n✅ Files are now available in Google Drive!")
        print("   Location: Data Harmonization/production_simple_working/v1_0_0/")
    else:
        print("\n❌ Upload failed. Check the error message above.")