#!/usr/bin/env python3
"""
Google Drive Setup Verification Script
Checks that Google Drive integration is properly configured for biomapper.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_file = '/home/ubuntu/biomapper/.env'
print(f"Loading environment from: {env_file}")
load_dotenv(env_file)

def check_environment():
    """Check environment variables."""
    print("\n📋 Environment Variables Check:")
    print("-" * 40)
    
    checks = {
        'GOOGLE_APPLICATION_CREDENTIALS': os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'),
        'GOOGLE_DRIVE_FOLDER_ID': os.environ.get('GOOGLE_DRIVE_FOLDER_ID'),
        'ENABLE_GOOGLE_DRIVE_SYNC': os.environ.get('ENABLE_GOOGLE_DRIVE_SYNC')
    }
    
    all_good = True
    for key, value in checks.items():
        if value:
            print(f"✅ {key}: {value[:50]}..." if len(str(value)) > 50 else f"✅ {key}: {value}")
        else:
            print(f"❌ {key}: NOT SET")
            all_good = False
    
    return all_good, checks

def check_credentials_file(creds_path):
    """Check Google credentials file."""
    print("\n🔑 Credentials File Check:")
    print("-" * 40)
    
    if not creds_path:
        print("❌ No credentials path specified")
        return False, None
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return False, None
    
    try:
        with open(creds_path, 'r') as f:
            cred_data = json.load(f)
        
        service_account = cred_data.get('client_email', 'NOT FOUND')
        project_id = cred_data.get('project_id', 'NOT FOUND')
        cred_type = cred_data.get('type', 'NOT FOUND')
        
        print(f"✅ Credentials file exists: {creds_path}")
        print(f"   Service Account: {service_account}")
        print(f"   Project ID: {project_id}")
        print(f"   Type: {cred_type}")
        
        return True, service_account
        
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False, None

def test_google_auth(creds_path):
    """Test Google Drive authentication."""
    print("\n🔐 Authentication Test:")
    print("-" * 40)
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # Try a simple API call
        results = service.files().list(pageSize=1).execute()
        
        print("✅ Authentication successful!")
        print("✅ Google Drive API is working")
        
        return True, service
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Run: poetry install")
        return False, None
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False, None

def test_folder_access(service, folder_id, service_account):
    """Test access to the specified Drive folder."""
    print("\n📁 Folder Access Test:")
    print("-" * 40)
    
    if not service or not folder_id:
        print("⚠️ Skipping folder test (no service or folder ID)")
        return False
    
    try:
        # Try to access the folder
        folder = service.files().get(fileId=folder_id).execute()
        
        print(f"✅ Can access folder: {folder.get('name', 'Unnamed')}")
        print(f"   Folder ID: {folder_id}")
        
        # Try to list files in the folder
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            pageSize=5,
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        if files:
            print(f"   Found {len(files)} file(s) in folder:")
            for file in files[:3]:
                print(f"     - {file['name']}")
        else:
            print("   Folder is empty")
        
        return True
        
    except Exception as e:
        if '404' in str(e) or 'notFound' in str(e):
            print(f"❌ Cannot access folder: {folder_id}")
            print("\n📝 TO FIX THIS:")
            print("   1. Go to your Google Drive")
            print(f"   2. Find or create the folder with ID: {folder_id}")
            print("   3. Right-click → Share")
            print(f"   4. Add email: {service_account}")
            print("   5. Set permission: Editor")
            print("   6. Click 'Send'")
        else:
            print(f"❌ Folder access error: {e}")
        
        return False

def test_upload_capability(service, folder_id):
    """Test if we can upload to the folder."""
    print("\n📤 Upload Capability Test:")
    print("-" * 40)
    
    if not service or not folder_id:
        print("⚠️ Skipping upload test")
        return False
    
    try:
        from googleapiclient.http import MediaInMemoryUpload
        
        # Create a test file in memory
        test_content = b"Biomapper Google Drive Integration Test"
        media = MediaInMemoryUpload(test_content, mimetype='text/plain')
        
        file_metadata = {
            'name': 'biomapper_test.txt',
            'parents': [folder_id]
        }
        
        # Try to upload
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()
        
        print(f"✅ Successfully uploaded test file: {file.get('name')}")
        print(f"   File ID: {file.get('id')}")
        
        if file.get('webViewLink'):
            print(f"   View link: {file.get('webViewLink')}")
        
        # Clean up - delete test file
        try:
            service.files().delete(fileId=file.get('id')).execute()
            print("   (Test file deleted)")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

def main():
    """Run all verification checks."""
    print("="*60)
    print("🔍 GOOGLE DRIVE SETUP VERIFICATION")
    print("="*60)
    
    results = {
        'environment': False,
        'credentials': False,
        'authentication': False,
        'folder_access': False,
        'upload': False
    }
    
    # Check environment
    env_ok, env_vars = check_environment()
    results['environment'] = env_ok
    
    # Check credentials file
    creds_path = env_vars.get('GOOGLE_APPLICATION_CREDENTIALS')
    creds_ok, service_account = check_credentials_file(creds_path)
    results['credentials'] = creds_ok
    
    # Test authentication
    if creds_ok:
        auth_ok, service = test_google_auth(creds_path)
        results['authentication'] = auth_ok
        
        # Test folder access
        if auth_ok:
            folder_id = env_vars.get('GOOGLE_DRIVE_FOLDER_ID')
            folder_ok = test_folder_access(service, folder_id, service_account)
            results['folder_access'] = folder_ok
            
            # Test upload
            if folder_ok:
                upload_ok = test_upload_capability(service, folder_id)
                results['upload'] = upload_ok
    
    # Summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check.replace('_', ' ').title()}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 GOOGLE DRIVE IS FULLY CONFIGURED!")
        print("You can now run the pipeline with --enable-drive-sync")
    else:
        print("⚠️ GOOGLE DRIVE SETUP INCOMPLETE")
        print("Please fix the issues above before using Drive sync")
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())