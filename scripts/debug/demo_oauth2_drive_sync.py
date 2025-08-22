#!/usr/bin/env python3
"""
Demo: Google Drive sync with OAuth2 authentication
Shows how to use the new OAuth2 support for Google Drive uploads.
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# Add biomapper to path
sys.path.insert(0, '/home/ubuntu/biomapper')
sys.path.insert(0, '/home/ubuntu/biomapper/src')

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/biomapper/.env')


async def demo_oauth2_sync():
    """Demonstrate OAuth2-based Google Drive sync."""
    
    print("=" * 70)
    print("🚀 GOOGLE DRIVE OAUTH2 SYNC DEMO")
    print("=" * 70)
    
    # Step 1: Check OAuth2 setup
    print("\n📋 Step 1: Checking OAuth2 Configuration")
    print("-" * 40)
    
    from utils.google_auth_helper import GoogleAuthHelper
    
    # Check available auth methods
    available_methods = GoogleAuthHelper.get_available_auth_methods()
    print(f"Available authentication methods: {', '.join(available_methods) if available_methods else 'none'}")
    
    if 'oauth2' not in available_methods:
        print("\n⚠️ OAuth2 not configured!")
        print("Please run: python scripts/setup_oauth2_drive.py")
        return
    
    print("✅ OAuth2 is configured")
    
    # Step 2: Create test data
    print("\n📝 Step 2: Creating Test Data")
    print("-" * 40)
    
    # Create temporary directory for test files
    test_dir = Path(tempfile.mkdtemp(prefix="biomapper_oauth2_test_"))
    print(f"Test directory: {test_dir}")
    
    # Create some test files
    test_files = {
        "metabolites_matched.csv": """metabolite_id,name,hmdb_id,confidence
M001,Glucose,HMDB0000122,0.95
M002,Lactate,HMDB0000190,0.92
M003,Pyruvate,HMDB0000243,0.88""",
        
        "proteins_resolved.tsv": """protein_id\tuniprot_id\tgene_symbol\tcoverage
P001\tP04406\tGAPDH\t0.99
P002\tP00338\tLDHA\t0.97
P003\tP14618\tPKM\t0.94""",
        
        "analysis_summary.json": """{
    "strategy": "metabolomics_progressive_v3",
    "timestamp": "%s",
    "total_metabolites": 150,
    "matched": 142,
    "coverage": 0.947,
    "stages": {
        "stage1_nmr": 95,
        "stage2_cts": 30,
        "stage3_semantic": 12,
        "stage4_vector": 5
    }
}""" % datetime.now().isoformat()
    }
    
    created_files = []
    for filename, content in test_files.items():
        file_path = test_dir / filename
        file_path.write_text(content)
        created_files.append(str(file_path))
        print(f"  Created: {filename}")
    
    # Step 3: Test OAuth2 authentication
    print("\n🔐 Step 3: Testing OAuth2 Authentication")
    print("-" * 40)
    
    helper = GoogleAuthHelper(auth_type="oauth2")
    service = helper.get_drive_service()
    
    if not service:
        print("❌ OAuth2 authentication failed")
        return
    
    print("✅ OAuth2 authentication successful")
    
    # Get user info
    test_results = helper.test_access()
    if test_results['email']:
        print(f"   Authenticated as: {test_results['email']}")
    
    # Step 4: Use the sync action with OAuth2
    print("\n📤 Step 4: Syncing Files with OAuth2")
    print("-" * 40)
    
    try:
        from actions.io.sync_to_google_drive_v3 import (
            SyncToGoogleDriveV3Action, 
            SyncToGoogleDriveV3Params
        )
        
        # Create sync parameters
        params = SyncToGoogleDriveV3Params(
            drive_folder_id='root',  # Upload to root for OAuth2
            auth_type='oauth2',  # Explicitly use OAuth2
            auto_organize=True,
            strategy_name='oauth2_demo',
            strategy_version='1.0.0',
            local_directory=str(test_dir),
            include_patterns=['*.csv', '*.tsv', '*.json'],
            create_summary=True,
            description='OAuth2 demo upload from biomapper'
        )
        
        # Create action instance
        action = SyncToGoogleDriveV3Action()
        
        # Create minimal context
        context = {
            'output_files': {
                'metabolites': created_files[0],
                'proteins': created_files[1],
                'summary': created_files[2]
            },
            'strategy_name': 'oauth2_demo',
            'strategy_metadata': {'version': '1.0.0'}
        }
        
        # Execute sync
        print("Uploading files to Google Drive...")
        result = await action.execute_typed(
            current_identifiers=[],
            current_ontology_type='',
            params=params,
            source_endpoint=None,
            target_endpoint=None,
            context=context
        )
        
        if result.success:
            print("✅ Upload successful!")
            print(f"   Files uploaded: {result.data.get('uploaded_count', 0)}")
            print(f"   Folder structure: {result.data.get('folder_structure', 'N/A')}")
            print(f"   Auth method: {result.data.get('auth_method', 'N/A')}")
            
            # Show links to uploaded files
            if result.data.get('uploaded_files'):
                print("\n📎 Uploaded Files:")
                for file_info in result.data['uploaded_files']:
                    print(f"   - {file_info.get('name')}")
                    if file_info.get('webViewLink'):
                        print(f"     View: {file_info['webViewLink']}")
        else:
            print(f"❌ Upload failed: {result.error}")
            
    except ImportError as e:
        print(f"❌ Could not import sync action: {e}")
        print("Using fallback method...")
        
        # Fallback: Direct upload using helper
        from googleapiclient.http import MediaFileUpload
        
        for file_path in created_files:
            try:
                file_name = os.path.basename(file_path)
                
                file_metadata = {
                    'name': f'oauth2_demo_{file_name}',
                    'description': 'OAuth2 demo upload'
                }
                
                media = MediaFileUpload(file_path, resumable=True)
                
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,webViewLink'
                ).execute()
                
                print(f"✅ Uploaded: {file_name}")
                if file.get('webViewLink'):
                    print(f"   View: {file['webViewLink']}")
                    
            except Exception as e:
                print(f"❌ Failed to upload {file_name}: {e}")
    
    # Step 5: Comparison with Service Account
    print("\n📊 Step 5: OAuth2 vs Service Account Comparison")
    print("-" * 40)
    
    print("OAuth2 Advantages:")
    print("  ✅ Uploads to personal Google Drive")
    print("  ✅ No storage quota limitations")
    print("  ✅ Files owned by user account")
    print("  ✅ Easy sharing with others")
    
    print("\nService Account Advantages:")
    print("  ✅ No interactive authentication required")
    print("  ✅ Better for automated pipelines")
    print("  ✅ Consistent service identity")
    
    print("\nRecommendation:")
    print("  • Use OAuth2 for: Interactive sessions, personal uploads")
    print("  • Use Service Account for: CI/CD, automated pipelines")
    
    # Cleanup
    print("\n🧹 Cleaning up test files...")
    for file_path in created_files:
        try:
            os.remove(file_path)
        except:
            pass
    try:
        os.rmdir(test_dir)
    except:
        pass
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE!")
    print("=" * 70)
    print("\nTo use OAuth2 in your pipeline:")
    print("1. Run: python scripts/setup_oauth2_drive.py")
    print("2. Add to .env:")
    print("   GOOGLE_AUTH_TYPE=oauth2")
    print("3. Run pipeline with --auth-type oauth2")
    

async def demo_auto_auth():
    """Demonstrate automatic auth selection."""
    
    print("\n" + "=" * 70)
    print("🔄 AUTOMATIC AUTHENTICATION DEMO")
    print("=" * 70)
    
    from utils.google_auth_helper import GoogleAuthHelper
    
    print("\nTesting automatic authentication selection...")
    print("-" * 40)
    
    # Create helper with auto mode
    helper = GoogleAuthHelper(auth_type="auto")
    
    # It will try OAuth2 first, then service account
    service = helper.get_drive_service()
    
    if service:
        auth_method = helper._get_auth_method()
        print(f"✅ Authenticated using: {auth_method}")
        
        # Test capabilities
        test_results = helper.test_access()
        print(f"   Email: {test_results.get('email', 'N/A')}")
        print(f"   Can list files: {test_results.get('can_list_files', False)}")
    else:
        print("❌ No authentication method available")
        print("\nTo set up authentication:")
        print("  • For OAuth2: python scripts/setup_oauth2_drive.py")
        print("  • For Service Account: Follow Google Cloud Console instructions")


if __name__ == "__main__":
    print("\n🎯 Google Drive OAuth2 Integration Demo\n")
    print("This demo shows how to use OAuth2 authentication for Google Drive uploads.")
    print("OAuth2 allows uploading to your personal Google Drive without quota limits.\n")
    
    # Run the main demo
    asyncio.run(demo_oauth2_sync())
    
    # Show auto-auth capability
    asyncio.run(demo_auto_auth())
    
    print("\n✨ Demo complete! OAuth2 support is now available for biomapper.")
    print("See the documentation for more details on configuring authentication.")