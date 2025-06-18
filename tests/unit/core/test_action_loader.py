"""Unit tests for the ActionLoader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

from biomapper.core.engine_components.action_loader import ActionLoader
from biomapper.core.strategy_actions.base import StrategyAction
from biomapper.core.exceptions import ConfigurationError


class MockAction(StrategyAction):
    """Mock action class for testing."""
    
    async def execute(self, **kwargs):
        return {"output_identifiers": [], "output_ontology_type": "test"}


class TestActionLoader:
    """Test cases for ActionLoader class."""
    
    @pytest.fixture
    def action_loader(self):
        """Create an ActionLoader instance for testing."""
        return ActionLoader()
    
    def test_init(self, action_loader):
        """Test ActionLoader initialization."""
        assert action_loader._registry is None
        assert action_loader._loaded_modules == set()
    
    def test_action_registry_lazy_loading(self, action_loader):
        """Test that action registry is lazily loaded."""
        with patch('biomapper.core.engine_components.action_loader.ACTION_REGISTRY', {'TEST_ACTION': MockAction}):
            # Registry should not be loaded yet
            assert action_loader._registry is None
            
            # Access registry property
            registry = action_loader.action_registry
            
            # Registry should now be loaded
            assert action_loader._registry is not None
            assert 'TEST_ACTION' in registry
    
    def test_load_action_class_from_registry(self, action_loader):
        """Test loading action class from registry."""
        with patch.object(action_loader, 'action_registry', {'TEST_ACTION': MockAction}):
            action_class = action_loader.load_action_class('TEST_ACTION')
            assert action_class == MockAction
    
    def test_load_action_class_from_path(self, action_loader):
        """Test loading action class from full class path."""
        # Mock the module and class
        mock_module = MagicMock()
        mock_module.TestAction = MockAction
        
        with patch('importlib.import_module', return_value=mock_module):
            action_class = action_loader.load_action_class('test.module.TestAction')
            assert action_class == MockAction
            assert 'test.module' in action_loader._loaded_modules
    
    def test_load_action_class_invalid_type(self, action_loader):
        """Test loading action with unknown type."""
        with patch.object(action_loader, 'action_registry', {}):
            with pytest.raises(ConfigurationError) as exc_info:
                action_loader.load_action_class('UNKNOWN_ACTION')
            
            assert "Unknown action type" in str(exc_info.value)
    
    def test_load_action_class_import_error(self, action_loader):
        """Test handling import error when loading class path."""
        with patch('importlib.import_module', side_effect=ImportError("Module not found")):
            with pytest.raises(ConfigurationError) as exc_info:
                action_loader.load_action_class('nonexistent.module.Action')
            
            assert "Failed to import module" in str(exc_info.value)
    
    def test_load_action_class_attribute_error(self, action_loader):
        """Test handling missing class in module."""
        mock_module = MagicMock()
        # Don't add the expected class attribute
        
        with patch('importlib.import_module', return_value=mock_module):
            with pytest.raises(ConfigurationError) as exc_info:
                action_loader.load_action_class('test.module.MissingAction')
            
            assert "does not have class" in str(exc_info.value)
    
    def test_load_action_class_not_strategy_action(self, action_loader):
        """Test loading class that's not a StrategyAction subclass."""
        # Create a non-StrategyAction class
        class NotAnAction:
            pass
        
        mock_module = MagicMock()
        mock_module.NotAnAction = NotAnAction
        
        with patch('importlib.import_module', return_value=mock_module):
            with pytest.raises(ConfigurationError) as exc_info:
                action_loader.load_action_class('test.module.NotAnAction')
            
            assert "not a subclass of StrategyAction" in str(exc_info.value)
    
    def test_instantiate_action(self, action_loader):
        """Test instantiating an action."""
        mock_session = Mock()
        
        with patch.object(action_loader, 'load_action_class', return_value=MockAction):
            action_instance = action_loader.instantiate_action('TEST_ACTION', mock_session)
            
            assert isinstance(action_instance, MockAction)
            assert action_instance.db_session == mock_session
    
    def test_instantiate_action_failure(self, action_loader):
        """Test handling instantiation failure."""
        mock_session = Mock()
        
        # Create action class that fails to instantiate
        class FailingAction(StrategyAction):
            def __init__(self, db_session):
                raise ValueError("Instantiation failed")
        
        with patch.object(action_loader, 'load_action_class', return_value=FailingAction):
            with pytest.raises(ConfigurationError) as exc_info:
                action_loader.instantiate_action('FAILING_ACTION', mock_session)
            
            assert "Failed to instantiate action" in str(exc_info.value)
    
    def test_module_caching(self, action_loader):
        """Test that modules are cached after first load."""
        mock_module = MagicMock()
        mock_module.TestAction = MockAction
        
        with patch('importlib.import_module', return_value=mock_module) as mock_import:
            # First load
            action_loader.load_action_class('test.module.TestAction')
            assert mock_import.call_count == 1
            
            # Mock sys.modules for cached access
            with patch.dict('sys.modules', {'test.module': mock_module}):
                # Second load should use cache
                action_loader.load_action_class('test.module.TestAction')
                # Import should not be called again
                assert mock_import.call_count == 1