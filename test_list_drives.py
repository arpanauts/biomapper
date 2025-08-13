#!/usr/bin/env python3
"""List all drives and folders the service account can access."""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

def list_accessible_drives():
    """List all drives and folders accessible to the service account."""
    
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    print(f"Using credentials: {credentials_path}")
    print(f"Service account: biomapper@secret-lambda-468421-g6.iam.gserviceaccount.com\n")
    
    # Authenticate with full drive scope
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    service = build('drive', 'v3', credentials=credentials)
    
    # List all Shared Drives
    print("=== SHARED DRIVES ===")
    try:
        drives = service.drives().list(pageSize=100).execute()
        drive_list = drives.get('items', []) or drives.get('drives', [])
        
        if drive_list:
            print(f"Found {len(drive_list)} Shared Drive(s):")
            for drive in drive_list:
                print(f"  - Name: {drive.get('name')}")
                print(f"    ID: {drive.get('id')}")
                
                # Try to list folders in this drive
                try:
                    query = f"'{drive.get('id')}' in parents and mimeType='application/vnd.google-apps.folder'"
                    folders = service.files().list(
                        q=query,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        fields="files(id, name)"
                    ).execute()
                    
                    folder_list = folders.get('files', [])
                    if folder_list:
                        print(f"    Folders:")
                        for folder in folder_list:
                            print(f"      - {folder.get('name')} (ID: {folder.get('id')})")
                except Exception as e:
                    print(f"    Could not list folders: {e}")
                print()
        else:
            print("No Shared Drives found")
    except Exception as e:
        print(f"Error listing Shared Drives: {e}")
    
    # List all files/folders the service account can see
    print("\n=== ALL ACCESSIBLE FILES/FOLDERS ===")
    try:
        # List all files without parent filter
        results = service.files().list(
            pageSize=20,
            fields="files(id, name, mimeType, parents)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        items = results.get('files', [])
        
        if items:
            print(f"Found {len(items)} accessible items:")
            for item in items:
                mime = item.get('mimeType', '')
                if 'folder' in mime:
                    print(f"  📁 {item.get('name')} (ID: {item.get('id')})")
                else:
                    print(f"  📄 {item.get('name')} (ID: {item.get('id')})")
                if item.get('parents'):
                    print(f"     Parent: {item.get('parents')[0]}")
        else:
            print("No accessible items found")
            
    except Exception as e:
        print(f"Error listing files: {e}")
    
    # Try to access the specific folder
    print(f"\n=== TESTING SPECIFIC FOLDER ===")
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    print(f"Trying to access folder ID: {folder_id}")
    
    try:
        # Try with supportsAllDrives flag
        folder = service.files().get(
            fileId=folder_id,
            supportsAllDrives=True
        ).execute()
        print(f"✅ Folder found: {folder.get('name')}")
        print(f"   Mime type: {folder.get('mimeType')}")
        print(f"   Parents: {folder.get('parents', [])}")
    except Exception as e:
        print(f"❌ Cannot access folder: {e}")

if __name__ == "__main__":
    list_accessible_drives()