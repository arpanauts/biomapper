"""Configuration management for the mapping cache system."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CacheConfig:
    """Configuration for the mapping cache system."""

    # Database settings
    data_dir: str = field(
        default_factory=lambda: os.path.join(Path.home(), ".biomapper", "data")
    )
    db_name: str = "biomapper.db"

    # Cache behavior settings
    default_ttl_days: int = 30  # Default time-to-live for cached mappings
    confidence_threshold: float = 0.7  # Minimum confidence for mappings
    enable_stats: bool = True  # Whether to track cache statistics

    # Transitivity settings
    enable_transitivity: bool = True  # Whether to enable transitive mapping discovery
    min_transitive_confidence: float = 0.5  # Minimum confidence for transitive mappings
    max_chain_length: int = 3  # Maximum length of transitive chains
    confidence_decay: float = 0.9  # Factor by which confidence decreases with each hop

    # Batch processing settings
    batch_size: int = 100  # Size of batches for database operations

    # Entity type prioritization (order determines preference)
    entity_type_priority: List[str] = field(
        default_factory=lambda: [
            "chebi",
            "hmdb",
            "pubchem.compound",
            "kegg",
            "inchikey",
            "smiles",
            "cas",
        ]
    )

    # Expiration time overrides by entity type (in days)
    entity_ttl_overrides: Dict[str, int] = field(
        default_factory=lambda: {
            "inchikey": 365,  # Chemical identifiers are highly stable
            "smiles": 365,
            "cas": 365,
        }
    )

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of config
        """
        return {
            "data_dir": self.data_dir,
            "db_name": self.db_name,
            "default_ttl_days": self.default_ttl_days,
            "confidence_threshold": self.confidence_threshold,
            "enable_stats": self.enable_stats,
            "enable_transitivity": self.enable_transitivity,
            "min_transitive_confidence": self.min_transitive_confidence,
            "max_chain_length": self.max_chain_length,
            "confidence_decay": self.confidence_decay,
            "batch_size": self.batch_size,
            "entity_type_priority": self.entity_type_priority,
            "entity_ttl_overrides": self.entity_ttl_overrides,
        }

    def save(self, file_path: Optional[str] = None) -> str:
        """Save configuration to a file.

        Args:
            file_path: Path to save config file, defaults to ~/.biomapper/config/cache_config.json

        Returns:
            Path to saved config file
        """
        if not file_path:
            config_dir = os.path.join(Path.home(), ".biomapper", "config")
            os.makedirs(config_dir, exist_ok=True)
            file_path = os.path.join(config_dir, "cache_config.json")

        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return file_path

    @classmethod
    def load(cls, file_path: Optional[str] = None) -> "CacheConfig":
        """Load configuration from a file.

        Args:
            file_path: Path to config file, defaults to ~/.biomapper/config/cache_config.json

        Returns:
            Configuration object
        """
        if not file_path:
            default_path = os.path.join(
                Path.home(), ".biomapper", "config", "cache_config.json"
            )
            if os.path.exists(default_path):
                file_path = default_path
            else:
                return cls()  # Return default config if no file exists

        if not os.path.exists(file_path):
            return cls()  # Return default config if specified file doesn't exist

        with open(file_path, "r") as f:
            config_dict = json.load(f)

        # Create config object with defaults
        config = cls()

        # Update with values from file
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config


def get_default_config() -> CacheConfig:
    """Get default cache configuration, checking environment variables.

    Returns:
        Cache configuration
    """
    config = CacheConfig()

    # Override with environment variables if present
    if "BIOMAPPER_DATA_DIR" in os.environ:
        config.data_dir = os.environ["BIOMAPPER_DATA_DIR"]

    if "BIOMAPPER_CACHE_TTL_DAYS" in os.environ:
        try:
            config.default_ttl_days = int(os.environ["BIOMAPPER_CACHE_TTL_DAYS"])
        except ValueError:
            pass

    if "BIOMAPPER_CACHE_CONFIDENCE" in os.environ:
        try:
            config.confidence_threshold = float(
                os.environ["BIOMAPPER_CACHE_CONFIDENCE"]
            )
        except ValueError:
            pass

    if "BIOMAPPER_ENABLE_TRANSITIVITY" in os.environ:
        value = os.environ["BIOMAPPER_ENABLE_TRANSITIVITY"].lower()
        config.enable_transitivity = value in ("true", "1", "yes")

    # Create data directory if it doesn't exist
    os.makedirs(config.data_dir, exist_ok=True)

    return config
