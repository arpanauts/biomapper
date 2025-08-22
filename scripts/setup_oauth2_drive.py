#!/usr/bin/env python3
"""
Google Drive OAuth2 Setup Script
Sets up OAuth2 authentication for Google Drive to enable file uploads.

This solves the service account storage quota limitation by using user authentication.
"""

import os
import sys
import json
import pickle
from pathlib import Path
from datetime import datetime

# Google OAuth2 imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


# If modifying these scopes, delete the token file
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def setup_oauth2_credentials():
    """Interactive OAuth2 setup for Google Drive."""
    
    print("="*70)
    print("🔐 GOOGLE DRIVE OAUTH2 SETUP")
    print("="*70)
    print("\nThis script will set up OAuth2 authentication for Google Drive.")
    print("This allows biomapper to upload files to your personal Google Drive.\n")
    
    # Check for OAuth2 client credentials
    oauth_creds_path = Path.home() / '.biomapper' / 'oauth2_client_secret.json'
    token_path = Path.home() / '.biomapper' / 'oauth2_token.json'
    
    # Create .biomapper directory if it doesn't exist
    oauth_creds_path.parent.mkdir(exist_ok=True)
    
    print("📋 Prerequisites:")
    print("-" * 40)
    print("1. Go to: https://console.cloud.google.com/apis/credentials")
    print("2. Create an OAuth 2.0 Client ID (Desktop application)")
    print("3. Download the client secret JSON file")
    print(f"4. Save it as: {oauth_creds_path}")
    print()
    
    if not oauth_creds_path.exists():
        print(f"❌ OAuth2 client secret not found at: {oauth_creds_path}")
        print("\nTo create OAuth2 credentials:")
        print("1. Go to Google Cloud Console")
        print("2. Enable Google Drive API")
        print("3. Create OAuth 2.0 Client ID (Desktop type)")
        print("4. Download and save the JSON file to the path above")
        print("\nAlternatively, paste the JSON content here (end with empty line):")
        
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        
        if lines:
            try:
                json_content = '\n'.join(lines)
                client_config = json.loads(json_content)
                with open(oauth_creds_path, 'w') as f:
                    json.dump(client_config, f, indent=2)
                print(f"✅ Saved OAuth2 client secret to: {oauth_creds_path}")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                return None
        else:
            return None
    
    print(f"✅ OAuth2 client secret found: {oauth_creds_path}")
    
    # OAuth2 flow
    creds = None
    
    # Check for existing token
    if token_path.exists():
        print(f"\n📝 Existing token found: {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            print("✅ Loaded existing credentials")
        except Exception as e:
            print(f"⚠️ Could not load existing token: {e}")
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("\n🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"⚠️ Could not refresh token: {e}")
                creds = None
        
        if not creds:
            print("\n🌐 Starting OAuth2 authentication flow...")
            print("A browser window will open for authorization.")
            print("If it doesn't open automatically, copy the URL and open it manually.\n")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(oauth_creds_path), SCOPES)
                
                # Try to use local server first
                try:
                    creds = flow.run_local_server(port=8080)
                except Exception:
                    # Fallback to console flow
                    print("Local server failed, using console flow...")
                    creds = flow.run_console()
                
                print("\n✅ Authentication successful!")
                
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return None
        
        # Save the credentials for the next run
        if creds:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            print(f"✅ Saved credentials to: {token_path}")
    
    return creds


def test_drive_access(creds):
    """Test Google Drive access with OAuth2 credentials."""
    
    print("\n🔍 Testing Google Drive Access...")
    print("-" * 40)
    
    try:
        service = build('drive', 'v3', credentials=creds)
        
        # List some files to verify access
        results = service.files().list(
            pageSize=5,
            fields="files(id, name, mimeType)"
        ).execute()
        
        files = results.get('files', [])
        
        print(f"✅ Successfully connected to Google Drive")
        print(f"   Found {len(files)} recent files/folders:")
        
        for file in files:
            file_type = 'Folder' if file['mimeType'] == 'application/vnd.google-apps.folder' else 'File'
            print(f"   - {file['name']} ({file_type})")
        
        return service
        
    except Exception as e:
        print(f"❌ Drive access failed: {e}")
        return None


def test_upload(service):
    """Test file upload capability."""
    
    print("\n📤 Testing File Upload...")
    print("-" * 40)
    
    try:
        # Create a test file
        test_content = f"Biomapper OAuth2 test upload\nTimestamp: {datetime.now()}"
        
        file_metadata = {
            'name': f'biomapper_oauth2_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
            'description': 'Biomapper OAuth2 authentication test'
        }
        
        media = MediaInMemoryUpload(
            test_content.encode(),
            mimetype='text/plain'
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink,webContentLink'
        ).execute()
        
        print(f"✅ Successfully uploaded test file!")
        print(f"   File name: {file.get('name')}")
        print(f"   File ID: {file.get('id')}")
        
        if file.get('webViewLink'):
            print(f"   View link: {file.get('webViewLink')}")
        if file.get('webContentLink'):
            print(f"   Download link: {file.get('webContentLink')}")
        
        # Make it publicly accessible
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            service.permissions().create(
                fileId=file.get('id'),
                body=permission
            ).execute()
            
            print(f"\n🔗 Public link: https://drive.google.com/file/d/{file.get('id')}/view")
            
        except Exception as e:
            print(f"   Note: Could not make file public: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False


def save_configuration(creds):
    """Save configuration for biomapper."""
    
    print("\n💾 Saving Configuration...")
    print("-" * 40)
    
    config = {
        'auth_type': 'oauth2',
        'token_file': str(Path.home() / '.biomapper' / 'oauth2_token.json'),
        'setup_date': datetime.now().isoformat(),
        'scopes': SCOPES
    }
    
    config_path = Path.home() / '.biomapper' / 'drive_config.json'
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to: {config_path}")
    
    # Update .env file instructions
    print("\n📝 To use OAuth2 in biomapper, add to your .env file:")
    print("-" * 40)
    print("GOOGLE_AUTH_TYPE=oauth2")
    print(f"GOOGLE_OAUTH_TOKEN_FILE={config['token_file']}")
    print("# GOOGLE_APPLICATION_CREDENTIALS can be removed or commented out")
    

def main():
    """Main setup flow."""
    
    # Setup OAuth2
    creds = setup_oauth2_credentials()
    
    if not creds:
        print("\n❌ OAuth2 setup failed")
        return 1
    
    # Test Drive access
    service = test_drive_access(creds)
    
    if not service:
        print("\n❌ Could not access Google Drive")
        return 1
    
    # Test upload
    upload_ok = test_upload(service)
    
    if not upload_ok:
        print("\n⚠️ Upload test failed, but authentication is set up")
    
    # Save configuration
    save_configuration(creds)
    
    print("\n" + "="*70)
    print("✅ OAUTH2 SETUP COMPLETE!")
    print("="*70)
    print("\nYou can now use Google Drive sync with biomapper.")
    print("Files will be uploaded to your personal Google Drive.")
    print("\nTo use in pipeline:")
    print("  poetry run python scripts/pipelines/metabolomics_progressive_production.py \\")
    print("    --dataset arivale \\")
    print("    --enable-drive-sync \\")
    print("    --auth-type oauth2")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())