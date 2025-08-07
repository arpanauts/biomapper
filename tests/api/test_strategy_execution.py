"""Unit tests for enhanced strategy execution."""

import sys
from pathlib import Path

# Add biomapper-api to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "biomapper-api"))

import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.action_registry import ActionRegistryService


class TestActionRegistry:
    """Test action registry functionality."""
    
    def test_list_actions(self):
        """Test listing all registered actions."""
        registry = ActionRegistryService()
        
        actions = registry.list_actions()
        assert isinstance(actions, list)
        
        # Should have loaded built-in actions
        assert len(actions) > 0
    
    def test_search_actions(self):
        """Test searching actions."""
        registry = ActionRegistryService()
        
        # Search for load actions
        results = registry.search_actions("load")
        assert isinstance(results, list)
        
        # Check if LOAD_DATASET_IDENTIFIERS is in results
        action_names = [r.name for r in results]
        assert any("LOAD" in name for name in action_names)
    
    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        registry = ActionRegistryService()
        
        stats = registry.get_registry_stats()
        assert "total_actions" in stats
        assert "categories" in stats
        assert stats["total_actions"] > 0