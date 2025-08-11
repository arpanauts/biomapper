"""
Environment Configuration Management for Biomapper

Provides comprehensive environment configuration with:
- Environment variable management and defaults
- Configuration file loading (YAML/.env)
- Directory creation and validation
- Service configuration and validation
- Fallback and resilience settings
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from dataclasses import dataclass, field
import logging

@dataclass
class EnvironmentConfig:
    """Environment configuration for biomapper."""
    
    # Core directories
    data_dir: str = "/procedure/data/local_data"
    cache_dir: str = "/tmp/biomapper/cache"
    output_dir: str = "/tmp/biomapper/output"
    config_dir: str = "configs"
    log_dir: str = "/tmp/biomapper/logs"
    
    # External services
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    cts_api_base: str = "https://cts.fiehnlab.ucdavis.edu/rest"
    uniprot_api_base: str = "https://rest.uniprot.org"
    
    # Performance settings
    max_concurrent_requests: int = 10
    request_timeout: int = 30
    cache_ttl_hours: int = 24
    
    # Fallback modes
    enable_vector_fallback: bool = True
    enable_api_fallbacks: bool = True
    enable_file_path_fallbacks: bool = True
    
    # Validation settings
    validate_file_paths: bool = True
    validate_parameters: bool = True
    strict_validation: bool = False
    
    # Additional environment variables
    custom_vars: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_environment(cls) -> 'EnvironmentConfig':
        """Create configuration from environment variables."""
        return cls(
            data_dir=os.getenv('BIOMAPPER_DATA_DIR', cls.data_dir),
            cache_dir=os.getenv('BIOMAPPER_CACHE_DIR', cls.cache_dir),
            output_dir=os.getenv('BIOMAPPER_OUTPUT_DIR', cls.output_dir),
            config_dir=os.getenv('BIOMAPPER_CONFIG_DIR', cls.config_dir),
            log_dir=os.getenv('BIOMAPPER_LOG_DIR', cls.log_dir),
            
            qdrant_host=os.getenv('QDRANT_HOST', cls.qdrant_host),
            qdrant_port=int(os.getenv('QDRANT_PORT', str(cls.qdrant_port))),
            cts_api_base=os.getenv('CTS_API_BASE', cls.cts_api_base),
            uniprot_api_base=os.getenv('UNIPROT_API_BASE', cls.uniprot_api_base),
            
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', str(cls.max_concurrent_requests))),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', str(cls.request_timeout))),
            cache_ttl_hours=int(os.getenv('CACHE_TTL_HOURS', str(cls.cache_ttl_hours))),
            
            enable_vector_fallback=os.getenv('ENABLE_VECTOR_FALLBACK', 'true').lower() == 'true',
            enable_api_fallbacks=os.getenv('ENABLE_API_FALLBACKS', 'true').lower() == 'true',
            enable_file_path_fallbacks=os.getenv('ENABLE_FILE_PATH_FALLBACKS', 'true').lower() == 'true',
            
            validate_file_paths=os.getenv('VALIDATE_FILE_PATHS', 'true').lower() == 'true',
            validate_parameters=os.getenv('VALIDATE_PARAMETERS', 'true').lower() == 'true',
            strict_validation=os.getenv('STRICT_VALIDATION', 'false').lower() == 'true',
        )
    
    @classmethod
    def from_file(cls, config_file: Path) -> 'EnvironmentConfig':
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert to environment variables dictionary."""
        return {
            'BIOMAPPER_DATA_DIR': self.data_dir,
            'BIOMAPPER_CACHE_DIR': self.cache_dir,
            'BIOMAPPER_OUTPUT_DIR': self.output_dir,
            'BIOMAPPER_CONFIG_DIR': self.config_dir,
            'BIOMAPPER_LOG_DIR': self.log_dir,
            
            'QDRANT_HOST': self.qdrant_host,
            'QDRANT_PORT': str(self.qdrant_port),
            'CTS_API_BASE': self.cts_api_base,
            'UNIPROT_API_BASE': self.uniprot_api_base,
            
            'MAX_CONCURRENT_REQUESTS': str(self.max_concurrent_requests),
            'REQUEST_TIMEOUT': str(self.request_timeout),
            'CACHE_TTL_HOURS': str(self.cache_ttl_hours),
            
            'ENABLE_VECTOR_FALLBACK': str(self.enable_vector_fallback).lower(),
            'ENABLE_API_FALLBACKS': str(self.enable_api_fallbacks).lower(),
            'ENABLE_FILE_PATH_FALLBACKS': str(self.enable_file_path_fallbacks).lower(),
            
            'VALIDATE_FILE_PATHS': str(self.validate_file_paths).lower(),
            'VALIDATE_PARAMETERS': str(self.validate_parameters).lower(),
            'STRICT_VALIDATION': str(self.strict_validation).lower(),
            
            **self.custom_vars
        }
    
    def create_directories(self) -> None:
        """Create required directories if they don't exist."""
        directories = [
            self.data_dir,
            self.cache_dir,
            self.output_dir,
            self.log_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check directory accessibility
        for dir_name, dir_path in [
            ('data_dir', self.data_dir),
            ('cache_dir', self.cache_dir),
            ('output_dir', self.output_dir),
            ('config_dir', self.config_dir)
        ]:
            path = Path(dir_path)
            if not path.exists():
                if dir_name in ['cache_dir', 'output_dir', 'log_dir']:
                    # These can be created
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        issues.append(f"Cannot create {dir_name} at {dir_path}: {e}")
                else:
                    issues.append(f"{dir_name} does not exist: {dir_path}")
            elif not os.access(path, os.R_OK):
                issues.append(f"{dir_name} is not readable: {dir_path}")
        
        # Validate numeric values
        if self.max_concurrent_requests < 1:
            issues.append("max_concurrent_requests must be >= 1")
        
        if self.request_timeout < 1:
            issues.append("request_timeout must be >= 1")
        
        if self.cache_ttl_hours < 0:
            issues.append("cache_ttl_hours must be >= 0")
        
        return issues


def get_environment_config() -> EnvironmentConfig:
    """Get environment configuration with fallback logic."""
    
    # Try to load from file first
    config_files = [
        Path('.env.yaml'),
        Path('configs/environment.yaml'),
        Path('/etc/biomapper/environment.yaml')
    ]
    
    for config_file in config_files:
        if config_file.exists():
            try:
                return EnvironmentConfig.from_file(config_file)
            except Exception as e:
                logging.warning(f"Could not load config from {config_file}: {e}")
    
    # Fallback to environment variables
    return EnvironmentConfig.from_environment()


class EnvironmentManager:
    """Manages environment configuration and setup."""
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        self.config = config or get_environment_config()
        self.logger = logging.getLogger(__name__)
    
    def setup_environment(self) -> None:
        """Setup environment based on configuration."""
        
        # Validate configuration
        issues = self.config.validate()
        if issues:
            for issue in issues:
                self.logger.warning(f"Configuration issue: {issue}")
        
        # Create directories
        try:
            self.config.create_directories()
            self.logger.info("Created required directories")
        except Exception as e:
            self.logger.error(f"Failed to create directories: {e}")
        
        # Set environment variables
        env_vars = self.config.to_env_dict()
        for key, value in env_vars.items():
            if key not in os.environ:  # Don't override existing values
                os.environ[key] = value
        
        self.logger.info("Environment setup complete")
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service."""
        
        service_configs = {
            'qdrant': {
                'host': self.config.qdrant_host,
                'port': self.config.qdrant_port,
                'timeout': self.config.request_timeout
            },
            'cts': {
                'base_url': self.config.cts_api_base,
                'timeout': self.config.request_timeout,
                'max_concurrent': self.config.max_concurrent_requests
            },
            'uniprot': {
                'base_url': self.config.uniprot_api_base,
                'timeout': self.config.request_timeout,
                'max_concurrent': self.config.max_concurrent_requests
            },
            'cache': {
                'directory': self.config.cache_dir,
                'ttl_hours': self.config.cache_ttl_hours
            },
            'logging': {
                'directory': self.config.log_dir,
                'level': 'INFO'
            }
        }
        
        return service_configs.get(service_name, {})
    
    def check_service_availability(self, service_name: str) -> bool:
        """Check if a service is available and configured correctly."""
        
        if service_name == 'qdrant':
            # Check if Qdrant is accessible
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((self.config.qdrant_host, self.config.qdrant_port))
                sock.close()
                return result == 0
            except Exception:
                return False
        
        elif service_name in ['cts', 'uniprot']:
            # Check if API endpoints are accessible
            try:
                import requests
                config = self.get_service_config(service_name)
                response = requests.head(config['base_url'], timeout=5)
                return response.status_code < 500
            except Exception:
                return False
        
        elif service_name == 'cache':
            # Check if cache directory is writable
            cache_dir = Path(self.config.cache_dir)
            return cache_dir.exists() and os.access(cache_dir, os.W_OK)
        
        return False


def create_environment_templates():
    """Create template environment configuration files."""
    
    # .env template
    env_template = """# Biomapper Environment Configuration

# Core directories
BIOMAPPER_DATA_DIR=/procedure/data/local_data
BIOMAPPER_CACHE_DIR=/tmp/biomapper/cache
BIOMAPPER_OUTPUT_DIR=/tmp/biomapper/output
BIOMAPPER_CONFIG_DIR=configs
BIOMAPPER_LOG_DIR=/tmp/biomapper/logs

# External services
QDRANT_HOST=localhost
QDRANT_PORT=6333
CTS_API_BASE=https://cts.fiehnlab.ucdavis.edu/rest
UNIPROT_API_BASE=https://rest.uniprot.org

# Performance settings
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
CACHE_TTL_HOURS=24

# Fallback modes
ENABLE_VECTOR_FALLBACK=true
ENABLE_API_FALLBACKS=true
ENABLE_FILE_PATH_FALLBACKS=true

# Validation settings
VALIDATE_FILE_PATHS=true
VALIDATE_PARAMETERS=true
STRICT_VALIDATION=false
"""
    
    # YAML template
    yaml_template = {
        'data_dir': '/procedure/data/local_data',
        'cache_dir': '/tmp/biomapper/cache',
        'output_dir': '/tmp/biomapper/output',
        'config_dir': 'configs',
        'log_dir': '/tmp/biomapper/logs',
        
        'qdrant_host': 'localhost',
        'qdrant_port': 6333,
        'cts_api_base': 'https://cts.fiehnlab.ucdavis.edu/rest',
        'uniprot_api_base': 'https://rest.uniprot.org',
        
        'max_concurrent_requests': 10,
        'request_timeout': 30,
        'cache_ttl_hours': 24,
        
        'enable_vector_fallback': True,
        'enable_api_fallbacks': True,
        'enable_file_path_fallbacks': True,
        
        'validate_file_paths': True,
        'validate_parameters': True,
        'strict_validation': False,
        
        'custom_vars': {}
    }
    
    # Write templates
    with open('.env.template', 'w') as f:
        f.write(env_template)
    
    with open('environment.yaml.template', 'w') as f:
        yaml.dump(yaml_template, f, default_flow_style=False)
    
    print("Created environment configuration templates:")
    print("  - .env.template")
    print("  - environment.yaml.template")


# Global environment manager
_environment_manager = None

def get_environment_manager() -> EnvironmentManager:
    """Get global environment manager instance."""
    global _environment_manager
    if _environment_manager is None:
        _environment_manager = EnvironmentManager()
    return _environment_manager


if __name__ == "__main__":
    create_environment_templates()