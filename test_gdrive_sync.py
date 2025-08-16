#!/usr/bin/env python3
"""
Test Google Drive sync directly
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Environment variables loaded:")
print(f"  GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
print(f"  GOOGLE_DRIVE_FOLDER_ID: {os.getenv('GOOGLE_DRIVE_FOLDER_ID')}")
print(f"  ENABLE_GOOGLE_DRIVE_SYNC: {os.getenv('ENABLE_GOOGLE_DRIVE_SYNC')}")

# Check if credentials file exists
creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if creds_path and os.path.exists(creds_path):
    print(f"\n✅ Credentials file exists: {creds_path}")
    print(f"  Size: {os.path.getsize(creds_path)} bytes")
else:
    print(f"\n❌ Credentials file not found: {creds_path}")

# Try to authenticate with Google Drive
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    print("\n🔐 Attempting Google Drive authentication...")
    
    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    
    service = build("drive", "v3", credentials=credentials)
    
    # Test by listing files in the target folder
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    print(f"\n📁 Checking folder: {folder_id}")
    
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        pageSize=5,
        fields="files(id, name, mimeType)"
    ).execute()
    
    items = results.get('files', [])
    
    print(f"\n✅ Authentication successful! Found {len(items)} items in folder:")
    for item in items:
        print(f"  - {item['name']} ({item['mimeType']})")
    
    # Try to upload a test file
    print("\n📤 Testing file upload...")
    from googleapiclient.http import MediaFileUpload
    
    # Create a test file
    test_file = "/tmp/test_biomapper_sync.txt"
    with open(test_file, 'w') as f:
        f.write("Test upload from biomapper pipeline\n")
    
    file_metadata = {
        'name': 'test_biomapper_sync.txt',
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(test_file, mimetype='text/plain')
    
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,name'
    ).execute()
    
    print(f"✅ Test file uploaded successfully!")
    print(f"  File ID: {uploaded_file.get('id')}")
    print(f"  File name: {uploaded_file.get('name')}")
    
    # Clean up test file
    os.remove(test_file)
    
except ImportError as e:
    print(f"\n❌ Missing Google Drive dependencies: {e}")
    print("Install with: poetry add google-api-python-client google-auth")
    
except Exception as e:
    print(f"\n❌ Google Drive sync failed: {e}")
    import traceback
    traceback.print_exc()