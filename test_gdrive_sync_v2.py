#!/usr/bin/env python3
"""
Test script for enhanced Google Drive sync with auto-organization
"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add biomapper to path
sys.path.insert(0, '/home/ubuntu/biomapper')

# Load environment variables
load_dotenv('/home/ubuntu/biomapper/.env')

from biomapper.core.strategy_actions.io.sync_to_google_drive_v2 import (
    SyncToGoogleDriveV2Action,
    SyncToGoogleDriveV2Params
)


async def test_v2_sync():
    """Test the enhanced V2 sync with auto-organization."""
    
    # Get config from environment
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not folder_id or not credentials_path:
        print("❌ Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_APPLICATION_CREDENTIALS in .env")
        return False
    
    print(f"📁 Using Drive folder: {folder_id}")
    print(f"🔑 Using credentials: {credentials_path}")
    
    # Create test data
    test_dir = Path("/tmp/biomapper/gdrive_v2_test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create multiple test files
    test_files = {
        "metabolite_results.tsv": f"id\tname\thmdb_id\nM001\tGlucose\tHMDB0000122\nM002\tLactate\tHMDB0000190\n# Generated at {timestamp}",
        "protein_results.csv": f"uniprot_id,gene_name,organism\nP12345,GENE1,Human\nP67890,GENE2,Mouse\n# Generated at {timestamp}",
        "analysis_report.md": f"# Analysis Report\n\nGenerated: {timestamp}\n\n## Summary\n- Total metabolites: 2\n- Total proteins: 2\n\n## Details\nTest run successful!"
    }
    
    for filename, content in test_files.items():
        file_path = test_dir / filename
        file_path.write_text(content)
        print(f"✅ Created test file: {filename}")
    
    # Test 1: Auto-organization with strategy info
    print("\n🧪 Test 1: Auto-organization with strategy name/version")
    print("-" * 50)
    
    context = {
        'strategy_name': 'metabolite_protein_integration_v2_enhanced',
        'strategy_metadata': {'version': '2.1.0'},
        'output_files': {
            'metabolites': str(test_dir / "metabolite_results.tsv"),
            'proteins': str(test_dir / "protein_results.csv"),
            'report': str(test_dir / "analysis_report.md")
        }
    }
    
    params = SyncToGoogleDriveV2Params(
        drive_folder_id=folder_id,
        credentials_path=credentials_path,
        auto_organize=True,  # Enable auto-organization
        sync_context_outputs=True,
        create_subfolder=True,  # Add timestamp subfolder
        description="Test run with auto-organization"
    )
    
    action = SyncToGoogleDriveV2Action()
    result = await action.execute_typed(params, context)
    
    if result.success:
        print(f"✅ Upload successful!")
        print(f"📂 Folder structure: {result.data.get('folder_structure')}")
        print(f"📊 Files uploaded: {result.data.get('uploaded_count')}")
        for file_info in result.data.get('uploaded_files', []):
            print(f"  - {file_info.get('name')}: {file_info.get('webViewLink')}")
    else:
        print(f"❌ Upload failed: {result.error}")
        return False
    
    # Test 2: Custom strategy names
    print("\n🧪 Test 2: Custom strategy/version parameters")
    print("-" * 50)
    
    context2 = {
        'output_files': {
            'test_output': str(test_dir / "analysis_report.md")
        }
    }
    
    params2 = SyncToGoogleDriveV2Params(
        drive_folder_id=folder_id,
        credentials_path=credentials_path,
        auto_organize=True,
        strategy_name="custom_test_strategy",
        strategy_version="3.0.0-beta",
        sync_context_outputs=True,
        create_subfolder=False,  # No additional timestamp folder
        file_patterns=["*.md"]  # Only markdown files
    )
    
    result2 = await action.execute_typed(params2, context2)
    
    if result2.success:
        print(f"✅ Custom upload successful!")
        print(f"📂 Folder structure: {result2.data.get('folder_structure')}")
        print(f"📊 Files uploaded: {result2.data.get('uploaded_count')}")
    else:
        print(f"❌ Custom upload failed: {result2.error}")
        return False
    
    # Test 3: Without auto-organization (classic mode)
    print("\n🧪 Test 3: Classic mode (no auto-organization)")
    print("-" * 50)
    
    params3 = SyncToGoogleDriveV2Params(
        drive_folder_id=folder_id,
        credentials_path=credentials_path,
        auto_organize=False,  # Disable auto-organization
        sync_context_outputs=True,
        create_subfolder=True,
        subfolder_name=f"classic_upload_{timestamp}"
    )
    
    result3 = await action.execute_typed(params3, context)
    
    if result3.success:
        print(f"✅ Classic upload successful!")
        print(f"📂 Folder structure: {result3.data.get('folder_structure')}")
        print(f"📊 Files uploaded: {result3.data.get('uploaded_count')}")
    else:
        print(f"❌ Classic upload failed: {result3.error}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed successfully!")
    print("\nCheck your Google Drive folder to see the organized structure:")
    print(f"📁 https://drive.google.com/drive/folders/{folder_id}")
    print("\nExpected folder structure:")
    print("├── metabolite_protein_integration/")
    print("│   └── v2_1_0/")
    print("│       └── run_[timestamp]/")
    print("│           ├── metabolite_results.tsv")
    print("│           ├── protein_results.csv")
    print("│           └── analysis_report.md")
    print("├── custom_test_strategy/")
    print("│   └── v3_0_0-beta/")
    print("│       └── analysis_report.md")
    print("└── classic_upload_[timestamp]/")
    print("    ├── metabolite_results.tsv")
    print("    ├── protein_results.csv")
    print("    └── analysis_report.md")
    
    return True


if __name__ == "__main__":
    print("🚀 Testing Enhanced Google Drive Sync V2")
    print("=" * 50)
    
    # Run async test
    success = asyncio.run(test_v2_sync())
    
    if success:
        print("\n✅ V2 sync action is working correctly!")
    else:
        print("\n❌ V2 sync action test failed")
        sys.exit(1)