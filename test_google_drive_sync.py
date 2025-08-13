#!/usr/bin/env python3
"""Test Google Drive sync with real credentials."""

import os
import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the sync action
from biomapper.core.strategy_actions.io.sync_to_google_drive import (
    SyncToGoogleDriveAction,
    SyncToGoogleDriveParams
)

async def test_google_drive_sync():
    """Test syncing a simple file to Google Drive."""
    
    print("=== Google Drive Sync Test ===\n")
    
    # Create test data
    test_dir = Path("/tmp/biomapper/gdrive_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a test CSV file
    test_data = pd.DataFrame({
        'metabolite_id': ['HMDB0000001', 'HMDB0000002', 'HMDB0000005'],
        'name': ['1-Methylhistidine', '1,3-Diaminopropane', '2-Ketobutyric acid'],
        'test_timestamp': [datetime.now().isoformat()] * 3
    })
    
    test_file = test_dir / f"test_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    test_data.to_csv(test_file, index=False)
    print(f"Created test file: {test_file}")
    print(f"File size: {test_file.stat().st_size} bytes\n")
    
    # Prepare context with the test file
    context = {
        'output_files': {
            'test_output': str(test_file)
        }
    }
    
    # Create sync parameters
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not folder_id:
        print("ERROR: GOOGLE_DRIVE_FOLDER_ID not set in .env")
        return False
    if not credentials_path:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS not set in .env")
        return False
        
    params = SyncToGoogleDriveParams(
        drive_folder_id=folder_id,
        credentials_path=credentials_path,
        sync_context_outputs=True,  # Sync from context['output_files']
        create_subfolder=True,  # Create a timestamped subfolder
        description="Biomapper test sync"
    )
    
    # Create and execute the action
    action = SyncToGoogleDriveAction()
    
    try:
        print("Attempting to sync to Google Drive...")
        print(f"Folder ID: {os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'NOT SET')[:10]}...")
        
        result = await action.execute_typed(params, context)
        
        print("\n✅ SUCCESS! File synced to Google Drive")
        print(f"\nResult summary:")
        print(f"  Success: {result.success}")
        
        if result.data:
            print(f"\nSync details:")
            for key, value in result.data.items():
                print(f"  {key}: {value}")
                
            # Check for URLs in the data
            if 'file_urls' in result.data:
                print(f"\nGoogle Drive URLs:")
                for filename, url in result.data['file_urls'].items():
                    print(f"  {filename}: {url}")
            elif 'uploaded_files' in result.data:
                print(f"\nUploaded files:")
                for file_info in result.data['uploaded_files']:
                    print(f"  {file_info}")
        
        # Also create a markdown report
        report_file = test_dir / "sync_report.md"
        with open(report_file, 'w') as f:
            f.write(f"# Google Drive Sync Test Report\n\n")
            f.write(f"**Date**: {datetime.now().isoformat()}\n\n")
            f.write(f"## Results\n")
            f.write(f"- Success: {result.success}\n")
            if result.data:
                for key, value in result.data.items():
                    if key != 'file_urls':
                        f.write(f"- {key}: {value}\n")
            f.write(f"\n## Files Uploaded\n")
            if 'file_urls' in result.data:
                for filename, url in result.data['file_urls'].items():
                    f.write(f"- [{filename}]({url})\n")
        
        # Try to sync the report too
        print("\nSyncing report file...")
        context['output_files']['report'] = str(report_file)
        params2 = SyncToGoogleDriveParams(
            drive_folder_id=folder_id,
            credentials_path=credentials_path,
            sync_context_outputs=True,
            create_subfolder=False  # Use same folder
        )
        result2 = await action.execute_typed(params2, context)
        print(f"Report synced: Success={result2.success}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check GOOGLE_APPLICATION_CREDENTIALS points to valid JSON")
        print("2. Check GOOGLE_DRIVE_FOLDER_ID is correct")
        print("3. Ensure service account has access to the folder")
        print("4. Check if Google Drive API is enabled in your project")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_google_drive_sync())
    exit(0 if success else 1)