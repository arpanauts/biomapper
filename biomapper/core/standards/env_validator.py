"""Environment configuration validation utilities."""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class EnvironmentValidator:
    """Validate environment configuration for Biomapper."""
    
    @staticmethod
    def validate_google_credentials() -> Tuple[bool, str]:
        """
        Validate Google service account credentials.
        
        Returns:
            Tuple of (is_valid, message)
        """
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not creds_path:
            return False, "GOOGLE_APPLICATION_CREDENTIALS not set"
            
        creds_file = Path(creds_path)
        if not creds_file.exists():
            return False, f"Credentials file not found: {creds_path}"
            
        try:
            # Load and validate JSON structure
            with open(creds_file) as f:
                creds = json.load(f)
                
            # Check required fields for service account
            required_fields = [
                'type', 'project_id', 'private_key_id', 
                'private_key', 'client_email', 'client_id'
            ]
            missing_fields = [f for f in required_fields if f not in creds]
            
            if missing_fields:
                return False, f"Missing fields in credentials: {', '.join(missing_fields)}"
            
            # Validate credential type
            if creds.get('type') != 'service_account':
                return False, f"Invalid credential type: {creds.get('type')} (expected: service_account)"
            
            # Check private key format
            if not creds.get('private_key', '').startswith('-----BEGIN'):
                return False, "Invalid private key format"
            
            # Check email format
            client_email = creds.get('client_email', '')
            if not client_email or '@' not in client_email:
                return False, f"Invalid client email: {client_email}"
            
            return True, f"Valid service account: {client_email}"
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in credentials file: {e}"
        except Exception as e:
            return False, f"Error reading credentials: {e}"
    
    @staticmethod
    def validate_google_drive_access() -> Tuple[bool, str]:
        """
        Test actual Google Drive API access.
        
        Returns:
            Tuple of (is_accessible, message)
        """
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
            
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            
            if not creds_path or not folder_id:
                return False, "Missing credentials or folder ID"
            
            # Create credentials
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            
            # Build service
            service = build('drive', 'v3', credentials=credentials)
            
            # Try to get folder metadata
            folder = service.files().get(
                fileId=folder_id,
                fields='id,name,mimeType'
            ).execute()
            
            if folder.get('mimeType') != 'application/vnd.google-apps.folder':
                return False, f"ID points to a file, not a folder: {folder.get('name')}"
            
            return True, f"Successfully accessed folder: {folder.get('name')}"
            
        except HttpError as e:
            if e.resp.status == 404:
                return False, f"Folder not found or not accessible: {folder_id}"
            elif e.resp.status == 403:
                return False, f"Permission denied for folder: {folder_id}"
            else:
                return False, f"Google Drive API error: {e}"
        except ImportError:
            return False, "Google API libraries not installed (pip install google-api-python-client)"
        except Exception as e:
            return False, f"Error accessing Google Drive: {e}"
    
    @staticmethod
    def validate_file_paths() -> Dict[str, Tuple[bool, str]]:
        """
        Validate all file path environment variables.
        
        Returns:
            Dict mapping variable name to (is_valid, message) tuple
        """
        results = {}
        
        # Check data directories
        path_vars = {
            'BIOMAPPER_DATA_DIR': ('directory', True),  # (type, create_if_missing)
            'BIOMAPPER_OUTPUT_DIR': ('directory', True),
            'BIOMAPPER_LOG_FILE': ('file', False),
            'DATABASE_URL': ('database', False),
        }
        
        for var_name, (path_type, create) in path_vars.items():
            value = os.getenv(var_name)
            
            if not value:
                results[var_name] = (False, "Not set")
                continue
            
            if path_type == 'database':
                # Special handling for database URLs
                if value.startswith('sqlite:///'):
                    db_path = value.replace('sqlite:///', '')
                    db_file = Path(db_path)
                    if db_file.exists():
                        results[var_name] = (True, f"SQLite database exists: {db_file}")
                    else:
                        results[var_name] = (True, f"SQLite database will be created: {db_file}")
                else:
                    results[var_name] = (True, f"Database URL configured: {value.split('@')[0]}")
                continue
            
            path = Path(value).expanduser().resolve()
            
            if path_type == 'directory':
                if path.exists():
                    if path.is_dir():
                        results[var_name] = (True, f"Directory exists: {path}")
                    else:
                        results[var_name] = (False, f"Path exists but is not a directory: {path}")
                elif create:
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        results[var_name] = (True, f"Directory created: {path}")
                    except Exception as e:
                        results[var_name] = (False, f"Cannot create directory: {e}")
                else:
                    results[var_name] = (False, f"Directory does not exist: {path}")
            
            elif path_type == 'file':
                if path.exists():
                    if path.is_file():
                        results[var_name] = (True, f"File exists: {path}")
                    else:
                        results[var_name] = (False, f"Path exists but is not a file: {path}")
                else:
                    # For log files, check if parent directory exists
                    if path.parent.exists():
                        results[var_name] = (True, f"File will be created: {path}")
                    else:
                        results[var_name] = (False, f"Parent directory does not exist: {path.parent}")
        
        return results
    
    @staticmethod
    def validate_dependencies() -> Dict[str, Tuple[bool, str]]:
        """
        Check that required Python packages are installed.
        
        Returns:
            Dict mapping package name to (is_installed, version) tuple
        """
        results = {}
        
        required_packages = {
            'dotenv': 'python-dotenv',
            'google.oauth2': 'google-auth',
            'googleapiclient': 'google-api-python-client',
            'pandas': 'pandas',
            'pydantic': 'pydantic',
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
        }
        
        for import_name, package_name in required_packages.items():
            try:
                if '.' in import_name:
                    # Handle submodule imports
                    parts = import_name.split('.')
                    module = __import__(parts[0])
                    for part in parts[1:]:
                        module = getattr(module, part)
                else:
                    module = __import__(import_name)
                
                # Try to get version
                version = "unknown"
                if hasattr(module, '__version__'):
                    version = module.__version__
                else:
                    # Try pip show as fallback
                    try:
                        result = subprocess.run(
                            ['pip', 'show', package_name],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        for line in result.stdout.split('\n'):
                            if line.startswith('Version:'):
                                version = line.split(':', 1)[1].strip()
                                break
                    except:
                        pass
                
                results[package_name] = (True, version)
                
            except ImportError:
                results[package_name] = (False, "Not installed")
            except Exception as e:
                results[package_name] = (False, f"Error: {e}")
        
        return results
    
    @staticmethod
    def validate_network_connectivity() -> Dict[str, Tuple[bool, str]]:
        """
        Check network connectivity to required services.
        
        Returns:
            Dict mapping service name to (is_reachable, message) tuple
        """
        import socket
        import ssl
        
        results = {}
        
        services = {
            'Google Drive API': ('www.googleapis.com', 443),
            'UniProt API': ('rest.uniprot.org', 443),
            'PyPI': ('pypi.org', 443),
        }
        
        for service_name, (host, port) in services.items():
            try:
                # Create socket with timeout
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                
                # Wrap with SSL
                context = ssl.create_default_context()
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    ssock.connect((host, port))
                    results[service_name] = (True, f"Reachable at {host}:{port}")
                    
            except socket.timeout:
                results[service_name] = (False, "Connection timeout")
            except socket.gaierror:
                results[service_name] = (False, f"Cannot resolve {host}")
            except ConnectionRefusedError:
                results[service_name] = (False, f"Connection refused on port {port}")
            except ssl.SSLError as e:
                results[service_name] = (False, f"SSL error: {e}")
            except Exception as e:
                results[service_name] = (False, f"Error: {e}")
        
        return results
    
    @staticmethod
    def full_validation_report() -> str:
        """
        Run all validations and generate a comprehensive report.
        
        Returns:
            Formatted report string
        """
        from .env_manager import EnvironmentManager
        
        lines = [
            "=" * 70,
            "BIOMAPPER ENVIRONMENT VALIDATION REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            ""
        ]
        
        # Load environment
        env = EnvironmentManager()
        lines.append("ENVIRONMENT CONFIGURATION")
        lines.append("-" * 40)
        lines.append(env.summary())
        lines.append("")
        
        # Google credentials
        lines.append("GOOGLE CREDENTIALS VALIDATION")
        lines.append("-" * 40)
        valid, msg = EnvironmentValidator.validate_google_credentials()
        status = "✅ PASS" if valid else "❌ FAIL"
        lines.append(f"{status}: {msg}")
        lines.append("")
        
        # Google Drive access (only if credentials valid)
        if valid:
            lines.append("GOOGLE DRIVE ACCESS TEST")
            lines.append("-" * 40)
            valid, msg = EnvironmentValidator.validate_google_drive_access()
            status = "✅ PASS" if valid else "❌ FAIL"
            lines.append(f"{status}: {msg}")
            lines.append("")
        
        # File paths
        lines.append("FILE PATH VALIDATION")
        lines.append("-" * 40)
        path_results = EnvironmentValidator.validate_file_paths()
        for var_name, (valid, msg) in path_results.items():
            status = "✅" if valid else "❌"
            lines.append(f"{status} {var_name}: {msg}")
        lines.append("")
        
        # Dependencies
        lines.append("PYTHON DEPENDENCIES")
        lines.append("-" * 40)
        dep_results = EnvironmentValidator.validate_dependencies()
        for package, (installed, version) in dep_results.items():
            status = "✅" if installed else "❌"
            lines.append(f"{status} {package}: {version}")
        lines.append("")
        
        # Network connectivity
        lines.append("NETWORK CONNECTIVITY")
        lines.append("-" * 40)
        net_results = EnvironmentValidator.validate_network_connectivity()
        for service, (reachable, msg) in net_results.items():
            status = "✅" if reachable else "❌"
            lines.append(f"{status} {service}: {msg}")
        lines.append("")
        
        # Summary
        lines.append("=" * 70)
        lines.append("SUMMARY")
        lines.append("-" * 40)
        
        all_valid = True
        issues = []
        
        # Check critical issues
        if not path_results.get('BIOMAPPER_DATA_DIR', (False, ''))[0]:
            issues.append("Data directory not configured")
            all_valid = False
        
        if not dep_results.get('pandas', (False, ''))[0]:
            issues.append("Critical dependency 'pandas' not installed")
            all_valid = False
        
        # Check for Google Drive if configured
        gdrive_configured = bool(os.getenv('GOOGLE_DRIVE_FOLDER_ID'))
        if gdrive_configured:
            gdrive_valid, _ = EnvironmentValidator.validate_google_credentials()
            if not gdrive_valid:
                issues.append("Google Drive configured but credentials invalid")
                all_valid = False
        
        if all_valid:
            lines.append("✅ All validations passed! Environment is properly configured.")
        else:
            lines.append("❌ Environment configuration has issues:")
            for issue in issues:
                lines.append(f"  • {issue}")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)