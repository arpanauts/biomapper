"""
Mock settings module for testing without dependencies on pydantic_settings.
This replaces the real biomapper.config.settings in tests.
"""

class Settings:
    """Mock Settings class."""
    
    def __init__(self):
        # Set default values for required settings
        self.metamapper_db_url = "sqlite+aiosqlite:///:memory:"
        self.cache_db_url = "sqlite+aiosqlite:///:memory:"
        self.log_level = "INFO"
        self.debug = False
        
    def __getattr__(self, name):
        # Return None for any other settings not explicitly defined
        return None

# Create a singleton instance of Settings
settings = Settings()