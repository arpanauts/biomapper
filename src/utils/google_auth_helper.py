#!/usr/bin/env python3
"""
Google Authentication Helper
Handles both OAuth2 and Service Account authentication for Google Drive.

This module provides a unified interface for authentication, allowing biomapper
to work with both personal Google accounts (OAuth2) and service accounts.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any
from enum import Enum

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class AuthType(Enum):
    """Authentication type enumeration."""
    SERVICE_ACCOUNT = "service_account"
    OAUTH2 = "oauth2"
    AUTO = "auto"  # Automatically detect based on available credentials


class GoogleAuthHelper:
    """
    Unified Google authentication helper supporting both OAuth2 and Service Account.
    
    This class handles the complexity of Google authentication and provides a simple
    interface for biomapper actions to authenticate with Google Drive.
    """
    
    # Default scopes for Google Drive
    DEFAULT_SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    # OAuth2 configuration paths
    OAUTH2_CLIENT_SECRET_PATH = Path.home() / '.biomapper' / 'oauth2_client_secret.json'
    OAUTH2_TOKEN_PATH = Path.home() / '.biomapper' / 'oauth2_token.json'
    
    def __init__(
        self,
        auth_type: Union[str, AuthType] = AuthType.AUTO,
        service_account_path: Optional[str] = None,
        oauth2_token_path: Optional[str] = None,
        oauth2_client_secret_path: Optional[str] = None,
        scopes: Optional[list] = None
    ):
        """
        Initialize the authentication helper.
        
        Args:
            auth_type: Type of authentication to use (service_account, oauth2, or auto)
            service_account_path: Path to service account credentials JSON
            oauth2_token_path: Path to OAuth2 token file
            oauth2_client_secret_path: Path to OAuth2 client secret file
            scopes: Google API scopes to request
        """
        # Convert string to enum if needed
        if isinstance(auth_type, str):
            auth_type = AuthType(auth_type.lower())
        
        self.auth_type = auth_type
        self.service_account_path = service_account_path
        self.oauth2_token_path = oauth2_token_path or self.OAUTH2_TOKEN_PATH
        self.oauth2_client_secret_path = oauth2_client_secret_path or self.OAUTH2_CLIENT_SECRET_PATH
        self.scopes = scopes or self.DEFAULT_SCOPES
        self.credentials = None
        self.service = None
        
    def authenticate(self) -> Optional[Credentials]:
        """
        Authenticate with Google using the configured method.
        
        Returns:
            Google credentials object or None if authentication fails
        """
        if self.auth_type == AuthType.AUTO:
            # Try OAuth2 first (if configured), then service account
            self.credentials = self._try_oauth2()
            if not self.credentials:
                self.credentials = self._try_service_account()
        elif self.auth_type == AuthType.OAUTH2:
            self.credentials = self._try_oauth2()
        elif self.auth_type == AuthType.SERVICE_ACCOUNT:
            self.credentials = self._try_service_account()
        
        if not self.credentials:
            logger.error(f"Failed to authenticate with {self.auth_type.value}")
            return None
            
        logger.info(f"Successfully authenticated using {self._get_auth_method()}")
        return self.credentials
    
    def _try_service_account(self) -> Optional[Credentials]:
        """
        Try to authenticate using service account credentials.
        
        Returns:
            Credentials object or None if authentication fails
        """
        # Check for service account path
        creds_path = self.service_account_path
        
        if not creds_path:
            # Try environment variable
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not creds_path or not os.path.exists(creds_path):
            logger.debug(f"Service account credentials not found at: {creds_path}")
            return None
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=self.scopes
            )
            
            # Verify it's actually a service account
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
                if creds_data.get('type') != 'service_account':
                    logger.warning(f"Credentials file is not a service account: {creds_data.get('type')}")
                    return None
            
            logger.info(f"Loaded service account: {creds_data.get('client_email')}")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to load service account credentials: {e}")
            return None
    
    def _try_oauth2(self) -> Optional[Credentials]:
        """
        Try to authenticate using OAuth2 credentials.
        
        Returns:
            Credentials object or None if authentication fails
        """
        credentials = None
        
        # Check for existing token
        if os.path.exists(self.oauth2_token_path):
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(self.oauth2_token_path),
                    self.scopes
                )
                logger.debug("Loaded existing OAuth2 token")
            except Exception as e:
                logger.warning(f"Could not load OAuth2 token: {e}")
        
        # Refresh or get new credentials if needed
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    logger.info("Refreshed OAuth2 token")
                except Exception as e:
                    logger.warning(f"Could not refresh token: {e}")
                    credentials = None
            
            if not credentials:
                # Need to do OAuth2 flow
                if not os.path.exists(self.oauth2_client_secret_path):
                    logger.debug(f"OAuth2 client secret not found at: {self.oauth2_client_secret_path}")
                    return None
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.oauth2_client_secret_path),
                        self.scopes
                    )
                    
                    # Try local server first, fall back to console
                    try:
                        credentials = flow.run_local_server(port=8080)
                    except Exception:
                        logger.info("Local server failed, using console flow")
                        credentials = flow.run_console()
                    
                    # Save the token for next time
                    self.oauth2_token_path.parent.mkdir(exist_ok=True)
                    with open(self.oauth2_token_path, 'w') as token:
                        token.write(credentials.to_json())
                    
                    logger.info("OAuth2 authentication successful")
                    
                except Exception as e:
                    logger.error(f"OAuth2 flow failed: {e}")
                    return None
        
        return credentials
    
    def get_drive_service(self):
        """
        Get an authenticated Google Drive service object.
        
        Returns:
            Google Drive service object or None if not authenticated
        """
        if not self.credentials:
            self.authenticate()
        
        if not self.credentials:
            return None
        
        if not self.service:
            try:
                self.service = build('drive', 'v3', credentials=self.credentials)
                logger.debug("Built Google Drive service")
            except Exception as e:
                logger.error(f"Failed to build Drive service: {e}")
                return None
        
        return self.service
    
    def test_access(self, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Test Google Drive access and optionally test folder access.
        
        Args:
            folder_id: Optional folder ID to test access to
            
        Returns:
            Dictionary with test results
        """
        results = {
            'authenticated': False,
            'auth_method': None,
            'can_list_files': False,
            'can_access_folder': False,
            'can_upload': False,
            'email': None,
            'errors': []
        }
        
        # Get service
        service = self.get_drive_service()
        if not service:
            results['errors'].append("Failed to authenticate")
            return results
        
        results['authenticated'] = True
        results['auth_method'] = self._get_auth_method()
        
        # Test basic access
        try:
            about = service.about().get(fields="user").execute()
            user_info = about.get('user', {})
            results['email'] = user_info.get('emailAddress')
            results['can_list_files'] = True
            logger.info(f"Authenticated as: {results['email']}")
        except Exception as e:
            results['errors'].append(f"Cannot get user info: {e}")
        
        # Test folder access if provided
        if folder_id:
            try:
                folder = service.files().get(
                    fileId=folder_id,
                    fields="id,name,mimeType",
                    supportsAllDrives=True
                ).execute()
                
                results['can_access_folder'] = True
                logger.info(f"Can access folder: {folder.get('name')}")
                
                # Test upload capability
                if self._get_auth_method() == 'service_account':
                    # Service accounts need folder to be shared
                    results['can_upload'] = results['can_access_folder']
                    if not results['can_upload']:
                        results['errors'].append(
                            "Service account needs folder to be shared with Editor permission"
                        )
                else:
                    # OAuth2 can upload to user's own Drive
                    results['can_upload'] = True
                    
            except HttpError as e:
                if e.resp.status == 404:
                    results['errors'].append(f"Folder not found: {folder_id}")
                elif e.resp.status == 403:
                    results['errors'].append(f"Access denied to folder: {folder_id}")
                else:
                    results['errors'].append(f"Error accessing folder: {e}")
            except Exception as e:
                results['errors'].append(f"Error testing folder: {e}")
        
        return results
    
    def _get_auth_method(self) -> str:
        """Get the authentication method used."""
        if not self.credentials:
            return "none"
        
        # Check if it's a service account
        if hasattr(self.credentials, 'service_account_email'):
            return "service_account"
        else:
            return "oauth2"
    
    @classmethod
    def from_env(cls) -> 'GoogleAuthHelper':
        """
        Create an auth helper from environment variables.
        
        Reads configuration from:
        - GOOGLE_AUTH_TYPE (service_account, oauth2, or auto)
        - GOOGLE_APPLICATION_CREDENTIALS (for service account)
        - GOOGLE_OAUTH_TOKEN_FILE (for OAuth2)
        - GOOGLE_OAUTH_CLIENT_SECRET (for OAuth2)
        
        Returns:
            Configured GoogleAuthHelper instance
        """
        auth_type = os.getenv('GOOGLE_AUTH_TYPE', 'auto')
        
        return cls(
            auth_type=auth_type,
            service_account_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
            oauth2_token_path=os.getenv('GOOGLE_OAUTH_TOKEN_FILE'),
            oauth2_client_secret_path=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
        )
    
    @classmethod
    def get_available_auth_methods(cls) -> list:
        """
        Check which authentication methods are available.
        
        Returns:
            List of available authentication methods
        """
        available = []
        
        # Check service account
        sa_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if sa_path and os.path.exists(sa_path):
            available.append('service_account')
        
        # Check OAuth2
        oauth_token = cls.OAUTH2_TOKEN_PATH
        oauth_secret = cls.OAUTH2_CLIENT_SECRET_PATH
        
        if os.path.exists(oauth_token) or os.path.exists(oauth_secret):
            available.append('oauth2')
        
        return available


def main():
    """Test the authentication helper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Google authentication')
    parser.add_argument(
        '--auth-type',
        choices=['service_account', 'oauth2', 'auto'],
        default='auto',
        help='Authentication type to use'
    )
    parser.add_argument(
        '--folder-id',
        help='Google Drive folder ID to test access'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Create helper
    helper = GoogleAuthHelper(auth_type=args.auth_type)
    
    # Test authentication
    print("\n🔐 Testing Google Authentication")
    print("=" * 50)
    
    results = helper.test_access(folder_id=args.folder_id)
    
    # Display results
    if results['authenticated']:
        print(f"✅ Authenticated successfully")
        print(f"   Method: {results['auth_method']}")
        print(f"   Email: {results['email']}")
    else:
        print("❌ Authentication failed")
    
    if results['can_list_files']:
        print("✅ Can list files")
    
    if args.folder_id:
        if results['can_access_folder']:
            print(f"✅ Can access folder: {args.folder_id}")
        else:
            print(f"❌ Cannot access folder: {args.folder_id}")
        
        if results['can_upload']:
            print("✅ Can upload files")
        else:
            print("❌ Cannot upload files")
    
    if results['errors']:
        print("\n⚠️ Errors encountered:")
        for error in results['errors']:
            print(f"   - {error}")
    
    # Show available methods
    available = GoogleAuthHelper.get_available_auth_methods()
    print(f"\n📋 Available auth methods: {', '.join(available) if available else 'none'}")
    
    return 0 if results['authenticated'] else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())