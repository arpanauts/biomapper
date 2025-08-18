"""Tests for action registry functionality."""

import threading
import time
from unittest.mock import patch
from typing import Dict, Any, List

from actions.registry import ACTION_REGISTRY, register_action, get_action_class
from actions.base import BaseStrategyAction


class TestActionRegistry:
    """Test action registry functionality."""
    
    def setup_method(self):
        """Set up test environment by clearing registry."""
        # Store original registry state
        self.original_registry = ACTION_REGISTRY.copy()
        
    def teardown_method(self):
        """Clean up test environment by restoring original registry."""
        # Restore original registry state
        ACTION_REGISTRY.clear()
        ACTION_REGISTRY.update(self.original_registry)
    
    def test_action_registration_via_decorator(self):
        """Test action registration via decorator."""
        initial_count = len(ACTION_REGISTRY)
        
        @register_action("TEST_ACTION")
        class TestAction(BaseStrategyAction):
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {"success": True}
                }
        
        # Verify registration
        assert len(ACTION_REGISTRY) == initial_count + 1
        assert "TEST_ACTION" in ACTION_REGISTRY
        assert ACTION_REGISTRY["TEST_ACTION"] == TestAction
        
        # Verify action name attribute is set
        assert hasattr(TestAction, '_action_name')
        assert TestAction._action_name == "TEST_ACTION"
    
    def test_action_discovery_and_lookup(self):
        """Test action discovery and lookup functionality."""
        
        @register_action("DISCOVERABLE_ACTION")
        class DiscoverableAction(BaseStrategyAction):
            async def execute(self, *args, **kwargs):
                return {"success": True}
        
        # Test get_action_class function
        retrieved_class = get_action_class("DISCOVERABLE_ACTION")
        assert retrieved_class == DiscoverableAction
        
        # Test direct registry access
        assert ACTION_REGISTRY["DISCOVERABLE_ACTION"] == DiscoverableAction
        
        # Test non-existent action
        non_existent = get_action_class("NON_EXISTENT_ACTION")
        assert non_existent is None
    
    def test_registry_initialization_and_state(self):
        """Test registry initialization and state management."""
        # Registry should be a dictionary
        assert isinstance(ACTION_REGISTRY, dict)
        
        # Registry should maintain state across operations
        initial_keys = set(ACTION_REGISTRY.keys())
        
        @register_action("STATE_TEST_ACTION")
        class StateTestAction(BaseStrategyAction):
            async def execute(self, *args, **kwargs):
                return {}
        
        # State should have changed
        new_keys = set(ACTION_REGISTRY.keys())
        assert len(new_keys) == len(initial_keys) + 1
        assert "STATE_TEST_ACTION" in new_keys
        assert "STATE_TEST_ACTION" not in initial_keys
    
    def test_duplicate_action_handling(self):
        """Test handling of duplicate action registration."""
        
        @register_action("DUPLICATE_ACTION")
        class FirstAction(BaseStrategyAction):
            async def execute(self, *args, **kwargs):
                return {"version": "first"}
        
        # Store reference to first action
        first_action_class = ACTION_REGISTRY["DUPLICATE_ACTION"]
        
        # Capture print output for warning
        with patch('builtins.print') as mock_print:
            @register_action("DUPLICATE_ACTION")
            class SecondAction(BaseStrategyAction):
                async def execute(self, *args, **kwargs):
                    return {"version": "second"}
            
            # Should print warning
            mock_print.assert_called_once()
            warning_message = mock_print.call_args[0][0]
            assert "Warning" in warning_message
            assert "DUPLICATE_ACTION" in warning_message
            assert "already registered" in warning_message
        
        # Second registration should override first
        assert ACTION_REGISTRY["DUPLICATE_ACTION"] == SecondAction
        assert ACTION_REGISTRY["DUPLICATE_ACTION"] != first_action_class
    
    def test_action_name_validation(self):
        """Test action name validation and conventions."""
        
        # Test valid action names
        valid_names = [
            "SIMPLE_ACTION",
            "COMPLEX_ACTION_NAME", 
            "ACTION_WITH_NUMBERS_123",
            "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS"
        ]
        
        for name in valid_names:
            @register_action(name)
            class ValidAction(BaseStrategyAction):
                async def execute(self, *args, **kwargs):
                    return {}
            
            assert name in ACTION_REGISTRY
            assert ACTION_REGISTRY[name]._action_name == name
    
    def test_action_metadata_management(self):
        """Test action metadata management."""
        
        @register_action("METADATA_ACTION")
        class MetadataAction(BaseStrategyAction):
            """Action with metadata for testing."""
            
            async def execute(self, *args, **kwargs):
                return {"metadata": "test"}
        
        action_class = ACTION_REGISTRY["METADATA_ACTION"]
        
        # Verify metadata attributes
        assert hasattr(action_class, '_action_name')
        assert action_class._action_name == "METADATA_ACTION"
        assert action_class.__doc__ is not None
        assert "metadata" in action_class.__doc__.lower()
        
        # Verify class inheritance
        assert issubclass(action_class, BaseStrategyAction)
    
    def test_registry_thread_safety(self):
        """Test registry thread safety during concurrent registration."""
        results = []
        errors = []
        
        def register_worker(action_id):
            """Worker function to register actions concurrently."""
            try:
                @register_action(f"THREAD_ACTION_{action_id}")
                class ThreadAction(BaseStrategyAction):
                    async def execute(self, *args, **kwargs):
                        return {"thread_id": action_id}
                
                results.append(action_id)
                
                # Verify action was registered
                if f"THREAD_ACTION_{action_id}" in ACTION_REGISTRY:
                    results.append(f"verified_{action_id}")
                    
            except Exception as e:
                errors.append(e)
        
        # Create and start multiple threads
        threads = [threading.Thread(target=register_worker, args=(i,)) for i in range(10)]
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) >= 10  # At least registration calls succeeded
        
        # Verify all actions were registered
        for i in range(10):
            action_name = f"THREAD_ACTION_{i}"
            assert action_name in ACTION_REGISTRY
    
    def test_dynamic_action_loading(self):
        """Test dynamic action registration and loading."""
        
        def create_dynamic_action(action_name: str, action_data: dict):
            """Create an action class dynamically."""
            
            class DynamicAction(BaseStrategyAction):
                def __init__(self):
                    self.action_data = action_data
                
                async def execute(self, *args, **kwargs):
                    return {"dynamic": True, "data": self.action_data}
            
            return DynamicAction
        
        # Create and register actions dynamically
        test_actions = [
            ("DYNAMIC_TEST_1", {"type": "test1"}),
            ("DYNAMIC_TEST_2", {"type": "test2"}),
            ("DYNAMIC_TEST_3", {"type": "test3"})
        ]
        
        for action_name, action_data in test_actions:
            action_class = create_dynamic_action(action_name, action_data)
            registered_class = register_action(action_name)(action_class)
            
            # Verify registration
            assert action_name in ACTION_REGISTRY
            assert ACTION_REGISTRY[action_name] == registered_class
            
            # Verify functionality
            action_instance = registered_class()
            assert action_instance.action_data == action_data
    
    def test_registry_cleanup_operations(self):
        """Test registry cleanup and maintenance operations."""
        
        # Add some test actions
        test_actions = []
        for i in range(5):
            @register_action(f"CLEANUP_ACTION_{i}")
            class CleanupAction(BaseStrategyAction):
                async def execute(self, *args, **kwargs):
                    return {"cleanup": True}
            
            test_actions.append(f"CLEANUP_ACTION_{i}")
        
        # Verify actions were added
        for action_name in test_actions:
            assert action_name in ACTION_REGISTRY
        
        # Test selective removal (simulating cleanup)
        for action_name in test_actions:
            if action_name in ACTION_REGISTRY:
                del ACTION_REGISTRY[action_name]
        
        # Verify actions were removed
        for action_name in test_actions:
            assert action_name not in ACTION_REGISTRY
    
    def test_registry_serialization_compatibility(self):
        """Test registry state for serialization compatibility."""
        
        @register_action("SERIALIZABLE_ACTION")
        class SerializableAction(BaseStrategyAction):
            async def execute(self, *args, **kwargs):
                return {"serializable": True}
        
        # Test that registry state can be serialized
        registry_keys = list(ACTION_REGISTRY.keys())
        registry_values = list(ACTION_REGISTRY.values())
        
        # Keys should be strings
        assert all(isinstance(key, str) for key in registry_keys)
        
        # Values should be classes
        assert all(callable(value) for value in registry_values)
        assert all(issubclass(value, BaseStrategyAction) for value in registry_values)
        
        # Test registry reconstruction
        reconstructed_registry = {}
        for key, value in ACTION_REGISTRY.items():
            reconstructed_registry[key] = value
        
        assert len(reconstructed_registry) == len(ACTION_REGISTRY)
        assert "SERIALIZABLE_ACTION" in reconstructed_registry


class TestActionRegistrationPatterns:
    """Test various action registration patterns and edge cases."""
    
    def setup_method(self):
        """Set up test environment."""
        self.original_registry = ACTION_REGISTRY.copy()
    
    def teardown_method(self):
        """Clean up test environment."""
        ACTION_REGISTRY.clear()
        ACTION_REGISTRY.update(self.original_registry)
    
    def test_biological_action_registration(self):
        """Test registration of biological data processing actions."""
        
        @register_action("PROTEIN_NORMALIZE_ACCESSIONS")
        class ProteinNormalizeAccessionsAction(BaseStrategyAction):
            """Normalize protein accession identifiers."""
            
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                # Simulate protein ID normalization
                normalized_ids = []
                for protein_id in current_identifiers:
                    # Remove version numbers and prefixes
                    clean_id = protein_id.replace("UniProtKB:", "").split(".")[0]
                    if clean_id.startswith(('P', 'Q', 'O')) and len(clean_id) >= 6:
                        normalized_ids.append(clean_id)
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": normalized_ids,
                    "output_ontology_type": "normalized_protein",
                    "provenance": [{"action": "protein_normalization"}],
                    "details": {"normalization_method": "accession_cleanup"}
                }
        
        # Verify biological action registration
        assert "PROTEIN_NORMALIZE_ACCESSIONS" in ACTION_REGISTRY
        action_class = ACTION_REGISTRY["PROTEIN_NORMALIZE_ACCESSIONS"]
        assert "protein" in action_class.__doc__.lower()
        
        @register_action("METABOLITE_EXTRACT_IDENTIFIERS") 
        class MetaboliteExtractIdentifiersAction(BaseStrategyAction):
            """Extract metabolite identifiers from composite fields."""
            
            async def execute(self, *args, **kwargs):
                return {"entity_type": "metabolite"}
        
        # Verify metabolite action registration
        assert "METABOLITE_EXTRACT_IDENTIFIERS" in ACTION_REGISTRY
        assert "metabolite" in ACTION_REGISTRY["METABOLITE_EXTRACT_IDENTIFIERS"].__doc__.lower()
    
    def test_action_overriding_policies(self):
        """Test action overriding policies and behaviors."""
        
        @register_action("OVERRIDE_TEST_ACTION")
        class OriginalAction(BaseStrategyAction):
            async def execute(self, *args, **kwargs):
                return {"version": "original"}
        
        original_class = ACTION_REGISTRY["OVERRIDE_TEST_ACTION"]
        
        # Test overriding with warning
        with patch('builtins.print') as mock_print:
            @register_action("OVERRIDE_TEST_ACTION")
            class OverrideAction(BaseStrategyAction):
                async def execute(self, *args, **kwargs):
                    return {"version": "override"}
            
            # Should issue warning
            mock_print.assert_called_once()
        
        # New action should have replaced original
        new_class = ACTION_REGISTRY["OVERRIDE_TEST_ACTION"]
        assert new_class != original_class
        assert new_class == OverrideAction
    
    def test_circular_dependency_detection(self):
        """Test detection of potential circular dependencies in action registration."""
        
        # This test verifies that the registry doesn't create circular references
        @register_action("DEPENDENCY_ACTION_A")
        class DependencyActionA(BaseStrategyAction):
            async def execute(self, *args, **kwargs):
                # Could potentially reference another action
                return {"depends_on": "DEPENDENCY_ACTION_B"}
        
        @register_action("DEPENDENCY_ACTION_B") 
        class DependencyActionB(BaseStrategyAction):
            async def execute(self, *args, **kwargs):
                # Could potentially reference the first action
                return {"depends_on": "DEPENDENCY_ACTION_A"}
        
        # Both should be registered without issues
        assert "DEPENDENCY_ACTION_A" in ACTION_REGISTRY
        assert "DEPENDENCY_ACTION_B" in ACTION_REGISTRY
        
        # Registry should not contain circular references at the class level
        action_a = ACTION_REGISTRY["DEPENDENCY_ACTION_A"]
        action_b = ACTION_REGISTRY["DEPENDENCY_ACTION_B"]
        
        assert action_a != action_b
        assert action_a is not action_b
    
    def test_action_inheritance_registration(self):
        """Test registration of actions with complex inheritance hierarchies."""
        
        class BiologicalActionBase(BaseStrategyAction):
            """Base class for biological data actions."""
            
            def validate_biological_ids(self, identifiers: List[str]) -> List[str]:
                """Common validation for biological identifiers."""
                return [id for id in identifiers if isinstance(id, str) and len(id) > 0]
        
        @register_action("PROTEIN_ACTION_CHILD")
        class ProteinActionChild(BiologicalActionBase):
            """Child action for protein processing."""
            
            async def execute(self, *args, **kwargs):
                return {"type": "protein_child"}
        
        @register_action("METABOLITE_ACTION_CHILD")
        class MetaboliteActionChild(BiologicalActionBase):
            """Child action for metabolite processing."""
            
            async def execute(self, *args, **kwargs):
                return {"type": "metabolite_child"}
        
        # Verify inheritance is preserved
        protein_action = ACTION_REGISTRY["PROTEIN_ACTION_CHILD"]
        metabolite_action = ACTION_REGISTRY["METABOLITE_ACTION_CHILD"]
        
        assert issubclass(protein_action, BiologicalActionBase)
        assert issubclass(metabolite_action, BiologicalActionBase)
        assert issubclass(protein_action, BaseStrategyAction)
        assert issubclass(metabolite_action, BaseStrategyAction)
        
        # Verify inherited methods are available
        protein_instance = protein_action()
        metabolite_instance = metabolite_action()
        
        assert hasattr(protein_instance, 'validate_biological_ids')
        assert hasattr(metabolite_instance, 'validate_biological_ids')
    
    def test_action_naming_conventions(self):
        """Test action naming conventions and best practices."""
        
        # Test recommended naming patterns
        recommended_names = [
            "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS",   # entity_verb_object_from_source
            "METABOLITE_NORMALIZE_HMDB",            # entity_verb_object
            "CHEMISTRY_FUZZY_TEST_MATCH",           # entity_method_action
            "LOAD_DATASET_IDENTIFIERS",             # verb_object_type
            "EXPORT_DATASET"                        # verb_object
        ]
        
        for name in recommended_names:
            @register_action(name)
            class RecommendedAction(BaseStrategyAction):
                async def execute(self, *args, **kwargs):
                    return {"name": name}
            
            assert name in ACTION_REGISTRY
            
            # Verify name follows conventions
            assert name.isupper()  # Should be uppercase
            assert "_" in name     # Should use underscores
            assert name.isascii()  # Should be ASCII only
    
    def test_registry_performance_characteristics(self):
        """Test registry performance with large numbers of actions."""
        
        # Register many actions to test performance
        action_count = 100
        start_time = time.time()
        
        for i in range(action_count):
            @register_action(f"PERFORMANCE_ACTION_{i:03d}")
            class PerformanceAction(BaseStrategyAction):
                async def execute(self, *args, **kwargs):
                    return {"index": i}
        
        registration_time = time.time() - start_time
        
        # Verify all actions were registered
        assert len([k for k in ACTION_REGISTRY.keys() if k.startswith("PERFORMANCE_ACTION_")]) == action_count
        
        # Test lookup performance
        start_time = time.time()
        for i in range(action_count):
            action_name = f"PERFORMANCE_ACTION_{i:03d}"
            action_class = get_action_class(action_name)
            assert action_class is not None
        
        lookup_time = time.time() - start_time
        
        # Performance should be reasonable (these are generous bounds)
        assert registration_time < 1.0  # Should register 100 actions in < 1 second
        assert lookup_time < 0.1        # Should lookup 100 actions in < 0.1 seconds