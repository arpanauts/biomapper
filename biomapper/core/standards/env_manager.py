"""Centralized environment configuration management for Biomapper."""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv


class EnvironmentManager:
    """Centralized environment configuration management."""
    
    # Required environment variables by feature
    REQUIREMENTS = {
        'google_drive': [
            'GOOGLE_APPLICATION_CREDENTIALS',
            'GOOGLE_DRIVE_FOLDER_ID'
        ],
        'uniprot_api': [],  # No API key required for basic use
        'database': [
            'DATABASE_URL'
        ],
        'data_paths': [
            'BIOMAPPER_DATA_DIR',
            'BIOMAPPER_OUTPUT_DIR'
        ]
    }
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize and load environment."""
        self.env_file = env_file or self._find_env_file()
        self.load_environment()
        self._validated_features: Dict[str, bool] = {}
        
    def _find_env_file(self) -> Optional[Path]:
        """Search for .env file in standard locations."""
        search_paths = [
            Path.cwd() / '.env',
            Path('/home/ubuntu/biomapper/.env'),
            Path.home() / 'biomapper' / '.env',
            Path(__file__).parent.parent.parent.parent / '.env',  # Project root
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        return None
    
    def load_environment(self):
        """Load environment variables from file."""
        if self.env_file and Path(self.env_file).exists():
            load_dotenv(self.env_file, override=True)
            print(f"✅ Loaded environment from: {self.env_file}")
        else:
            print("⚠️ No .env file found, using system environment")
    
    def validate_requirements(self, features: List[str]) -> Dict[str, bool]:
        """Validate required environment variables for features."""
        results = {}
        missing = []
        
        for feature in features:
            if feature in self.REQUIREMENTS:
                feature_valid = True
                for var in self.REQUIREMENTS[feature]:
                    value = os.getenv(var)
                    if not value:
                        missing.append(f"{var} (required for {feature})")
                        feature_valid = False
                    elif var.endswith('_CREDENTIALS'):
                        # Special validation for credential files
                        if not Path(value).exists():
                            missing.append(f"{var} points to non-existent file: {value}")
                            feature_valid = False
                results[feature] = feature_valid
                self._validated_features[feature] = feature_valid
            else:
                print(f"⚠️ Unknown feature: {feature}")
                results[feature] = False
        
        if missing:
            error_msg = (
                f"Missing or invalid environment variables:\n"
                f"  • " + "\n  • ".join(missing) + "\n"
                f"Please check your .env file at: {self.env_file or 'not found'}"
            )
            raise EnvironmentError(error_msg)
        
        return results
    
    def get_with_fallback(self, 
                         key: str, 
                         fallback: Optional[str] = None) -> Optional[str]:
        """Get env var with fallback value."""
        value = os.getenv(key)
        if value is None and fallback is not None:
            print(f"ℹ️ Using fallback for {key}: {fallback}")
            return fallback
        return value
    
    def get_path(self, key: str, create_if_missing: bool = False) -> Optional[Path]:
        """Get environment variable as Path object."""
        value = os.getenv(key)
        if value:
            path = Path(value).expanduser().resolve()
            if not path.exists():
                if create_if_missing and key.endswith('_DIR'):
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"✅ Created directory from {key}: {path}")
                else:
                    print(f"⚠️ Path from {key} does not exist: {path}")
            return path
        return None
    
    def get_google_credentials_path(self) -> Optional[Path]:
        """Get and validate Google credentials path."""
        creds_path = self.get_path('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and creds_path.exists():
            try:
                with open(creds_path) as f:
                    creds = json.load(f)
                    required_fields = ['type', 'project_id', 'private_key', 'client_email']
                    missing_fields = [f for f in required_fields if f not in creds]
                    if missing_fields:
                        print(f"❌ Invalid Google credentials - missing fields: {missing_fields}")
                        return None
                    return creds_path
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in credentials file: {e}")
                return None
            except Exception as e:
                print(f"❌ Error reading credentials: {e}")
                return None
        return None
    
    def get_google_drive_folder_id(self) -> Optional[str]:
        """Get Google Drive folder ID with validation."""
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        if folder_id:
            # Basic validation - should be alphanumeric with underscores/hyphens
            if len(folder_id) > 10 and folder_id.replace('_', '').replace('-', '').isalnum():
                return folder_id
            else:
                print(f"⚠️ Invalid Google Drive folder ID format: {folder_id}")
        return None
    
    def get_data_directories(self) -> Dict[str, Path]:
        """Get all data-related directories."""
        dirs = {}
        
        # Get data directory
        data_dir = self.get_path('BIOMAPPER_DATA_DIR', create_if_missing=True)
        if not data_dir:
            # Use default
            data_dir = Path('/procedure/data/local_data')
            data_dir.mkdir(parents=True, exist_ok=True)
        dirs['data'] = data_dir
        
        # Get output directory
        output_dir = self.get_path('BIOMAPPER_OUTPUT_DIR', create_if_missing=True)
        if not output_dir:
            # Use default
            output_dir = Path('/tmp/biomapper_results')
            output_dir.mkdir(parents=True, exist_ok=True)
        dirs['output'] = output_dir
        
        return dirs
    
    def summary(self) -> str:
        """Get summary of environment configuration."""
        lines = ["Environment Configuration Summary", "=" * 50]
        
        # Environment file
        lines.append(f"Config file: {self.env_file or 'None found'}")
        lines.append("")
        
        # Check each feature
        for feature, vars in self.REQUIREMENTS.items():
            status = "✅" if self._validated_features.get(feature, False) else "❌"
            lines.append(f"{status} {feature}:")
            for var in vars:
                value = os.getenv(var)
                if value:
                    # Mask sensitive values
                    if 'KEY' in var or 'TOKEN' in var or 'SECRET' in var:
                        display_value = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
                    elif 'CREDENTIALS' in var:
                        display_value = f".../{Path(value).name}" if value else "Not set"
                    else:
                        display_value = value
                    lines.append(f"    {var}: {display_value}")
                else:
                    lines.append(f"    {var}: Not set")
        
        return "\n".join(lines)
    
    @staticmethod
    def create_template_env(output_path: str = '.env.template'):
        """Create template .env file with all variables."""
        template = '''# Biomapper Environment Configuration
# Copy to .env and fill in your values

# Google Drive Integration
# Get credentials from Google Cloud Console -> Service Accounts
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
# Get folder ID from Google Drive URL or sharing dialog
GOOGLE_DRIVE_FOLDER_ID=1oQ7CczccH2a6oYYFMo_sf8fXtxF8au_D

# API Keys (optional)
# UNIPROT_API_KEY=your_key_here  # Not required for basic use

# Database
DATABASE_URL=sqlite:///biomapper.db

# File Paths
BIOMAPPER_DATA_DIR=/procedure/data/local_data
BIOMAPPER_OUTPUT_DIR=/tmp/biomapper_results

# Optional: Logging
BIOMAPPER_LOG_LEVEL=INFO
BIOMAPPER_LOG_FILE=/tmp/biomapper.log
'''
        Path(output_path).write_text(template)
        print(f"✅ Created template: {output_path}")
        return output_path
    
    @staticmethod
    def setup_from_template(template_path: str = '.env.template', 
                           output_path: str = '.env') -> bool:
        """Interactive setup from template."""
        import sys
        
        if Path(output_path).exists():
            response = input(f"⚠️ {output_path} already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Setup cancelled.")
                return False
        
        # Create template if it doesn't exist
        if not Path(template_path).exists():
            EnvironmentManager.create_template_env(template_path)
        
        # Read template
        template = Path(template_path).read_text()
        
        print("\n🚀 Biomapper Environment Setup")
        print("=" * 60)
        print("Please provide values for the following variables:")
        print("(Press Enter to keep default values)\n")
        
        # Parse and prompt for each variable
        lines = []
        for line in template.split('\n'):
            if line.startswith('#') or not line.strip():
                lines.append(line)
            elif '=' in line:
                var_name, default_value = line.split('=', 1)
                prompt = f"{var_name} [{default_value}]: "
                value = input(prompt).strip()
                if value:
                    lines.append(f"{var_name}={value}")
                else:
                    lines.append(line)
            else:
                lines.append(line)
        
        # Write the configured .env file
        Path(output_path).write_text('\n'.join(lines))
        print(f"\n✅ Created {output_path}")
        
        # Validate the new configuration
        env = EnvironmentManager(output_path)
        print(f"\n{env.summary()}")
        
        return True