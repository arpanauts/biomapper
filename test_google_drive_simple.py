#!/usr/bin/env python3
"""Simple test to verify Google Drive access."""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

def test_drive_access():
    """Test basic Google Drive access."""
    
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    print(f"Credentials: {credentials_path}")
    print(f"Folder ID: {folder_id}")
    
    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    
    service = build('drive', 'v3', credentials=credentials)
    
    # Test 1: Try to get folder metadata
    print("\n1. Testing folder access...")
    try:
        folder = service.files().get(fileId=folder_id, supportsAllDrives=True).execute()
        print(f"✅ Folder found: {folder.get('name', 'unnamed')}")
    except Exception as e:
        print(f"❌ Cannot access folder: {e}")
        
        # Try with different scope
        print("\n2. Trying with full drive scope...")
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        
        try:
            folder = service.files().get(fileId=folder_id).execute()
            print(f"✅ Folder found with full scope: {folder.get('name', 'unnamed')}")
        except Exception as e2:
            print(f"❌ Still cannot access: {e2}")
    
    # Test 2: Try to create a test file
    print("\n3. Testing file creation...")
    try:
        # Create a simple test file
        test_content = "Hello from biomapper!"
        test_file = '/tmp/biomapper_test.txt'
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        file_metadata = {
            'name': 'biomapper_test.txt',
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(test_file, mimetype='text/plain')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink',
            supportsAllDrives=True
        ).execute()
        
        print(f"✅ File uploaded successfully!")
        print(f"   File ID: {file.get('id')}")
        print(f"   Name: {file.get('name')}")
        print(f"   URL: {file.get('webViewLink')}")
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    
    # Test 3: List files in folder
    print("\n4. Testing file listing...")
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            pageSize=10,
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        print(f"✅ Found {len(files)} files in folder:")
        for file in files:
            print(f"   - {file.get('name')}")
            
    except Exception as e:
        print(f"❌ Cannot list files: {e}")

if __name__ == "__main__":
    test_drive_access()