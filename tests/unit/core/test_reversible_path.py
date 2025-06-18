"""Unit tests for the ReversiblePath class."""

import pytest
from unittest.mock import Mock

from biomapper.core.engine_components.reversible_path import ReversiblePath
from biomapper.db.models import MappingPath, MappingPathStep


class TestReversiblePath:
    """Test cases for ReversiblePath class."""
    
    @pytest.fixture
    def mock_path(self):
        """Create a mock MappingPath."""
        path = Mock(spec=MappingPath)
        path.id = 123
        path.name = "Test Path"
        path.priority = 10
        
        # Create mock steps
        step1 = Mock(spec=MappingPathStep)
        step1.step_order = 1
        
        step2 = Mock(spec=MappingPathStep)
        step2.step_order = 2
        
        step3 = Mock(spec=MappingPathStep)
        step3.step_order = 3
        
        path.steps = [step1, step2, step3]
        path.source_type = "SOURCE_TYPE"
        path.target_type = "TARGET_TYPE"
        
        return path
    
    def test_init_forward(self, mock_path):
        """Test initialization of forward path."""
        rev_path = ReversiblePath(mock_path, is_reverse=False)
        
        assert rev_path.original_path == mock_path
        assert rev_path.is_reverse is False
    
    def test_init_reverse(self, mock_path):
        """Test initialization of reverse path."""
        rev_path = ReversiblePath(mock_path, is_reverse=True)
        
        assert rev_path.original_path == mock_path
        assert rev_path.is_reverse is True
    
    def test_id_property(self, mock_path):
        """Test id property delegation."""
        rev_path = ReversiblePath(mock_path)
        assert rev_path.id == 123
    
    def test_name_forward(self, mock_path):
        """Test name property for forward path."""
        rev_path = ReversiblePath(mock_path, is_reverse=False)
        assert rev_path.name == "Test Path"
    
    def test_name_reverse(self, mock_path):
        """Test name property for reverse path."""
        rev_path = ReversiblePath(mock_path, is_reverse=True)
        assert rev_path.name == "Test Path (Reverse)"
    
    def test_priority_forward(self, mock_path):
        """Test priority for forward path."""
        rev_path = ReversiblePath(mock_path, is_reverse=False)
        assert rev_path.priority == 10
    
    def test_priority_reverse(self, mock_path):
        """Test priority for reverse path (lower priority)."""
        rev_path = ReversiblePath(mock_path, is_reverse=True)
        assert rev_path.priority == 15  # 10 + 5
    
    def test_priority_none_handling(self, mock_path):
        """Test priority when original path has None priority."""
        mock_path.priority = None
        
        # Forward path
        rev_path_forward = ReversiblePath(mock_path, is_reverse=False)
        assert rev_path_forward.priority == 100  # Default
        
        # Reverse path
        rev_path_reverse = ReversiblePath(mock_path, is_reverse=True)
        assert rev_path_reverse.priority == 105  # 100 + 5
    
    def test_steps_forward(self, mock_path):
        """Test steps property for forward path."""
        rev_path = ReversiblePath(mock_path, is_reverse=False)
        steps = rev_path.steps
        
        assert len(steps) == 3
        assert steps[0].step_order == 1
        assert steps[1].step_order == 2
        assert steps[2].step_order == 3
    
    def test_steps_reverse(self, mock_path):
        """Test steps property for reverse path."""
        rev_path = ReversiblePath(mock_path, is_reverse=True)
        steps = rev_path.steps
        
        assert len(steps) == 3
        # Steps should be in reverse order
        assert steps[0].step_order == 3
        assert steps[1].step_order == 2
        assert steps[2].step_order == 1
    
    def test_steps_reverse_with_none_order(self, mock_path):
        """Test reverse steps handling when step_order is None."""
        # Create step with None order
        step_none = Mock(spec=MappingPathStep)
        step_none.step_order = None
        
        mock_path.steps.append(step_none)
        
        rev_path = ReversiblePath(mock_path, is_reverse=True)
        steps = rev_path.steps
        
        # Should handle None gracefully
        assert len(steps) == 4
    
    def test_getattr_delegation(self, mock_path):
        """Test that unknown attributes are delegated to original path."""
        rev_path = ReversiblePath(mock_path)
        
        # Access attributes that should be delegated
        assert rev_path.source_type == "SOURCE_TYPE"
        assert rev_path.target_type == "TARGET_TYPE"
    
    def test_getattr_missing_attribute(self, mock_path):
        """Test that missing attributes raise AttributeError."""
        rev_path = ReversiblePath(mock_path)
        
        with pytest.raises(AttributeError):
            _ = rev_path.nonexistent_attribute