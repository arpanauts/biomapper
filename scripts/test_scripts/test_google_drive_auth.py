#!/usr/bin/env python3
"""
Comprehensive Google Drive Authentication and Upload Test
Tests all aspects of the Google Drive sync functionality
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add biomapper to path
sys.path.insert(0, '/home/ubuntu/biomapper')
sys.path.insert(0, '/home/ubuntu/biomapper/src')

async def test_google_drive_auth():
    """Test Google Drive authentication and basic operations."""
    
    print("=" * 70)
    print("GOOGLE DRIVE AUTHENTICATION AND UPLOAD TEST")
    print("=" * 70)
    
    # Step 1: Check environment variables
    print("\n1. CHECKING ENVIRONMENT VARIABLES:")
    print("-" * 40)
    
    creds_env = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_env:
        print(f"✓ GOOGLE_APPLICATION_CREDENTIALS is set: {creds_env}")
        if os.path.exists(creds_env):
            print(f"✓ Credentials file exists at: {creds_env}")
        else:
            print(f"✗ Credentials file NOT FOUND at: {creds_env}")
    else:
        print("✗ GOOGLE_APPLICATION_CREDENTIALS not set in environment")
    
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    if folder_id:
        print(f"✓ GOOGLE_DRIVE_FOLDER_ID is set: {folder_id}")
    else:
        print("✗ GOOGLE_DRIVE_FOLDER_ID not set in environment")
    
    # Step 2: Check credentials file directly
    print("\n2. CHECKING CREDENTIALS FILE:")
    print("-" * 40)
    
    creds_path = '/home/ubuntu/biomapper/google-credentials.json'
    if os.path.exists(creds_path):
        print(f"✓ Credentials file found at: {creds_path}")
        
        try:
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            
            print(f"✓ Credentials file is valid JSON")
            print(f"  - Type: {creds_data.get('type', 'unknown')}")
            print(f"  - Project ID: {creds_data.get('project_id', 'unknown')}")
            print(f"  - Client Email: {creds_data.get('client_email', 'unknown')}")
            
            # Check for required fields
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [f for f in required_fields if f not in creds_data]
            
            if missing_fields:
                print(f"✗ Missing required fields: {missing_fields}")
            else:
                print("✓ All required fields present in credentials")
                
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON in credentials file: {e}")
        except Exception as e:
            print(f"✗ Error reading credentials: {e}")
    else:
        print(f"✗ Credentials file not found at: {creds_path}")
    
    # Step 3: Test Google API library installation
    print("\n3. CHECKING GOOGLE API LIBRARIES:")
    print("-" * 40)
    
    try:
        from google.oauth2 import service_account
        print("✓ google.oauth2.service_account imported successfully")
    except ImportError as e:
        print(f"✗ Cannot import google.oauth2.service_account: {e}")
        print("  Run: pip install google-auth")
    
    try:
        from googleapiclient.discovery import build
        print("✓ googleapiclient.discovery imported successfully")
    except ImportError as e:
        print(f"✗ Cannot import googleapiclient.discovery: {e}")
        print("  Run: pip install google-api-python-client")
    
    try:
        from googleapiclient.http import MediaFileUpload
        print("✓ googleapiclient.http.MediaFileUpload imported successfully")
    except ImportError as e:
        print(f"✗ Cannot import MediaFileUpload: {e}")
    
    # Step 4: Test authentication
    print("\n4. TESTING AUTHENTICATION:")
    print("-" * 40)
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Try environment variable first
        test_creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', creds_path)
        
        print(f"Attempting authentication with: {test_creds_path}")
        
        credentials = service_account.Credentials.from_service_account_file(
            test_creds_path,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        
        print("✓ Credentials loaded successfully")
        
        # Build the service
        service = build("drive", "v3", credentials=credentials)
        print("✓ Google Drive service built successfully")
        
        # Step 5: Test basic API call
        print("\n5. TESTING API ACCESS:")
        print("-" * 40)
        
        # Try to get information about the user
        try:
            about = service.about().get(fields="user").execute()
            user_info = about.get('user', {})
            print(f"✓ API call successful!")
            print(f"  - Service account email: {user_info.get('emailAddress', 'unknown')}")
        except Exception as e:
            print(f"✗ API test call failed: {e}")
        
        # Step 6: Test folder access
        print("\n6. TESTING FOLDER ACCESS:")
        print("-" * 40)
        
        test_folder_id = folder_id or '1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D'
        print(f"Testing access to folder: {test_folder_id}")
        
        try:
            # Try to get folder metadata
            folder = service.files().get(
                fileId=test_folder_id,
                fields="id, name, mimeType, owners, permissions",
                supportsAllDrives=True
            ).execute()
            
            print(f"✓ Folder accessible!")
            print(f"  - Name: {folder.get('name', 'unknown')}")
            print(f"  - Type: {folder.get('mimeType', 'unknown')}")
            
            # Check permissions
            permissions = folder.get('permissions', [])
            if permissions:
                print(f"  - Permissions count: {len(permissions)}")
                for perm in permissions:
                    if perm.get('emailAddress') == creds_data.get('client_email'):
                        print(f"  - Service account has {perm.get('role', 'unknown')} role")
            
        except Exception as e:
            error_str = str(e)
            if '404' in error_str:
                print(f"✗ Folder not found or not accessible: {test_folder_id}")
                print("  Possible issues:")
                print("  1. Folder ID is incorrect")
                print("  2. Folder has not been shared with service account")
                print(f"  3. Share the folder with: {creds_data.get('client_email', 'unknown')}")
            elif '403' in error_str:
                print(f"✗ Access denied to folder: {test_folder_id}")
                print("  The service account needs permission to access this folder")
                print(f"  Share the folder with: {creds_data.get('client_email', 'unknown')}")
            else:
                print(f"✗ Error accessing folder: {e}")
        
        # Step 7: Test file upload
        print("\n7. TESTING FILE UPLOAD:")
        print("-" * 40)
        
        # Create a test file
        test_file_path = '/tmp/biomapper_test_upload.txt'
        test_content = f"BiOMapper Google Drive Test Upload\nTimestamp: {datetime.now().isoformat()}\n"
        
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        print(f"Created test file: {test_file_path}")
        
        try:
            from googleapiclient.http import MediaFileUpload
            
            file_metadata = {
                'name': f'biomapper_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                'parents': [test_folder_id]
            }
            
            media = MediaFileUpload(
                test_file_path,
                mimetype='text/plain',
                resumable=True
            )
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            print(f"✓ File uploaded successfully!")
            print(f"  - File ID: {file.get('id')}")
            print(f"  - File name: {file.get('name')}")
            print(f"  - View link: {file.get('webViewLink', 'N/A')}")
            
            # Clean up - delete the test file from Drive
            try:
                service.files().delete(fileId=file.get('id')).execute()
                print("✓ Test file deleted from Drive")
            except:
                pass
                
        except Exception as e:
            error_str = str(e)
            if 'storageQuotaExceeded' in error_str:
                print("✗ Cannot upload: Service account storage quota exceeded")
                print("  Service accounts cannot store files in their own Drive")
                print("  Files must be uploaded to a shared folder")
            else:
                print(f"✗ Upload failed: {e}")
        
        # Clean up local test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 8: Test the actual sync action
    print("\n8. TESTING SYNC ACTION:")
    print("-" * 40)
    
    try:
        from actions.io.sync_to_google_drive_v2 import SyncToGoogleDriveV2Action, SyncToGoogleDriveV2Params
        print("✓ SyncToGoogleDriveV2Action imported successfully")
        
        # Create test parameters
        params = SyncToGoogleDriveV2Params(
            drive_folder_id=test_folder_id,
            credentials_path=creds_path,
            auto_organize=True,
            strategy_name='test_strategy',
            strategy_version='1.0',
            sync_context_outputs=False
        )
        
        print("✓ Parameters created successfully")
        
        # Create action instance
        action = SyncToGoogleDriveV2Action()
        print("✓ Action instance created")
        
        # Test authentication method
        auth_service = await action._authenticate(params)
        if auth_service:
            print("✓ Action authentication successful")
        else:
            print("✗ Action authentication failed")
            
    except ImportError as e:
        print(f"✗ Cannot import sync action: {e}")
    except Exception as e:
        print(f"✗ Error testing sync action: {e}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_google_drive_auth())