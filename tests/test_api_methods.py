"""Tests for API method validation and registry."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from typing import Dict, Any, List

from biomapper.core.standards.api_validator import APIMethodValidator
from biomapper.core.standards.api_registry import (
    APIClientRegistry,
    ClientSpec,
    MethodSpec
)


class TestAPIMethodValidator:
    """Test suite for APIMethodValidator."""
    
    def test_validate_method_exists_success(self):
        """Test validation passes when method exists."""
        # Create mock client with a method
        client = Mock()
        client.get_data = Mock(return_value={"test": "data"})
        
        # Should not raise
        assert APIMethodValidator.validate_method_exists(client, "get_data")
    
    def test_validate_method_exists_failure(self):
        """Test validation fails with helpful error when method doesn't exist."""
        # Create mock client without the method
        client = Mock()
        client.fetch_data = Mock()
        client.post_data = Mock()
        
        # Remove the method we're testing for
        if hasattr(client, "get_data"):
            delattr(client, "get_data")
        
        # Should raise with suggestions
        with pytest.raises(AttributeError) as exc_info:
            APIMethodValidator.validate_method_exists(client, "get_data")
        
        error_msg = str(exc_info.value)
        assert "Method 'get_data' not found" in error_msg
        assert "fetch_data" in error_msg or "post_data" in error_msg
    
    def test_find_similar_methods(self):
        """Test finding similar method names."""
        available = [
            "get_protein_data",
            "get_metabolite_data", 
            "fetch_compound_info",
            "search_proteins"
        ]
        
        # Should find methods with "protein" in them
        similar = APIMethodValidator.find_similar_methods(
            "get_uniprot_data", available
        )
        assert "get_protein_data" in similar
        
        # Should find partial matches
        similar = APIMethodValidator.find_similar_methods(
            "protein", available
        )
        assert "get_protein_data" in similar
        assert "search_proteins" in similar
    
    def test_validate_signature(self):
        """Test signature validation."""
        # Create real object with typed method
        class TestClient:
            def get_data(self, protein_ids: List[str], fields: List[str] = None) -> Dict:
                return {}
        
        client = TestClient()
        
        # Should pass for correct signature (without type checking for simplicity)
        assert APIMethodValidator.validate_signature(
            client, "get_data"
        )
        
        # Should fail for non-existent method
        with pytest.raises(AttributeError):
            APIMethodValidator.validate_signature(
                client, "this_method_definitely_does_not_exist"
            )
    
    def test_create_method_wrapper(self):
        """Test creating wrapped method with validation."""
        # Create real client class
        class TestClient:
            def __init__(self):
                self.__class__.__name__ = "TestClient"
            
            def get_data(self, arg):
                return {"result": "success", "arg": arg}
        
        client = TestClient()
        
        # Create wrapper
        wrapped = APIMethodValidator.create_method_wrapper(
            client, "get_data"
        )
        
        # Should work normally
        result = wrapped("test_arg")
        assert result == {"result": "success", "arg": "test_arg"}
        
        # Test wrapper with non-existent method  
        with pytest.raises(AttributeError) as exc_info:
            APIMethodValidator.create_method_wrapper(
                client, "some_nonexistent_method_name"
            )
        assert "Method 'some_nonexistent_method_name' not found" in str(exc_info.value)
    
    def test_validate_client_interface(self):
        """Test validating entire client interface."""
        # Create real test client with specific methods
        class TestClient:
            def map_identifiers(self):
                pass
            
            def resolve_batch(self):
                pass
            
            def search(self):
                pass
        
        client = TestClient()
        
        # Should pass with all required methods
        results = APIMethodValidator.validate_client_interface(
            client,
            required_methods=["map_identifiers", "resolve_batch"],
            optional_methods=["search", "nonexistent"]
        )
        
        assert results["map_identifiers"] is True
        assert results["resolve_batch"] is True
        assert results["search"] is True
        assert results["nonexistent"] is False
        
        # Should fail with missing required method
        with pytest.raises(ValueError) as exc_info:
            APIMethodValidator.validate_client_interface(
                client,
                required_methods=["map_identifiers", "get_uniprot_data"]
            )
        
        error_msg = str(exc_info.value)
        assert "missing required methods" in error_msg.lower()
        assert "get_uniprot_data" in error_msg


class TestAPIClientRegistry:
    """Test suite for APIClientRegistry."""
    
    def test_get_client_spec(self):
        """Test getting client specifications."""
        # Should return spec for known client
        spec = APIClientRegistry.get_client_spec("uniprot")
        assert spec is not None
        assert spec.name == "uniprot"
        assert "map_identifiers" in spec.methods
        
        # Should return None for unknown client
        spec = APIClientRegistry.get_client_spec("unknown_client")
        assert spec is None
    
    def test_register_client(self):
        """Test registering new client specification."""
        # Create new client spec
        new_spec = ClientSpec(
            name="test_client",
            class_name="TestClient",
            module_path="tests.mocks.test_client",
            description="Test client for unit tests",
            methods={
                "test_method": MethodSpec(
                    name="test_method",
                    params=["param1"],
                    returns="str",
                    description="Test method"
                )
            }
        )
        
        # Register it
        APIClientRegistry.register_client(new_spec)
        
        # Should be retrievable
        spec = APIClientRegistry.get_client_spec("test_client")
        assert spec is not None
        assert spec.name == "test_client"
    
    def test_validate_client(self):
        """Test validating client against registry."""
        # Create real client matching UniProt spec
        class GoodUniProtClient:
            async def map_identifiers(self):
                pass
            
            async def resolve_batch(self):
                pass
            
            async def _fetch_uniprot_search_results(self):
                pass
        
        client = GoodUniProtClient()
        
        # Should pass validation
        results = APIClientRegistry.validate_client("uniprot", client)
        assert results["map_identifiers"] is True
        assert results["resolve_batch"] is True
        
        # Create client missing methods
        class IncompleteClient:
            async def map_identifiers(self):
                pass
            # Missing resolve_batch and _fetch_uniprot_search_results
        
        incomplete_client = IncompleteClient()
        
        # Should fail validation
        with pytest.raises(ValueError) as exc_info:
            APIClientRegistry.validate_client("uniprot", incomplete_client)
        
        error_msg = str(exc_info.value)
        assert "validation failed" in error_msg.lower()
        assert "resolve_batch" in error_msg
    
    def test_get_method_signature(self):
        """Test getting method signature from registry."""
        # Should return spec for known method
        method_spec = APIClientRegistry.get_method_signature(
            "uniprot", "map_identifiers"
        )
        assert method_spec is not None
        assert method_spec.name == "map_identifiers"
        assert "source_identifiers" in method_spec.params
        
        # Should return None for unknown method
        method_spec = APIClientRegistry.get_method_signature(
            "uniprot", "unknown_method"
        )
        assert method_spec is None
    
    def test_list_clients(self):
        """Test listing all known clients."""
        clients = APIClientRegistry.list_clients()
        assert "uniprot" in clients
        assert "chembl" in clients
        assert "pubchem" in clients
        assert "hmdb" in clients
    
    def test_get_client_methods(self):
        """Test getting methods for a client."""
        methods = APIClientRegistry.get_client_methods("uniprot")
        assert methods is not None
        assert "map_identifiers" in methods
        assert "resolve_batch" in methods
        
        # Should return None for unknown client
        methods = APIClientRegistry.get_client_methods("unknown")
        assert methods is None
    
    def test_generate_documentation(self):
        """Test documentation generation."""
        doc = APIClientRegistry.generate_documentation()
        
        # Should contain all clients
        assert "UniProtHistoricalResolverClient" in doc
        assert "ChemblAPIClient" in doc
        assert "PubChemAPIClient" in doc
        assert "HMDBAPIClient" in doc
        
        # Should contain method signatures
        assert "map_identifiers" in doc
        assert "search_compounds" in doc
        assert "get_metabolite" in doc
        
        # Should contain parameter information
        assert "source_identifiers" in doc
        assert "Required parameters" in doc
        assert "Optional parameters" in doc


class TestErrorMessages:
    """Test that error messages are helpful and actionable."""
    
    def test_method_not_found_with_suggestions(self):
        """Test error message includes helpful suggestions."""
        class TestClient:
            def __init__(self):
                self.__class__.__name__ = "TestClient"
            
            def get_protein_data(self):
                pass
            
            def fetch_protein_info(self):
                pass
        
        client = TestClient()
        
        with pytest.raises(AttributeError) as exc_info:
            APIMethodValidator.validate_method_exists(
                client, "get_uniprot_data"
            )
        
        error_msg = str(exc_info.value)
        
        # Should mention the incorrect method name
        assert "get_uniprot_data" in error_msg
        
        # Should mention the client class
        assert "TestClient" in error_msg
        
        # Should suggest similar methods
        assert "get_protein_data" in error_msg
        
        # Should list available methods
        assert "Available methods" in error_msg
    
    def test_signature_mismatch_error(self):
        """Test error message for signature mismatches."""
        client = Mock()
        
        def method_with_wrong_params(wrong_param: str) -> None:
            pass
        
        client.test_method = method_with_wrong_params
        
        with pytest.raises(ValueError) as exc_info:
            APIMethodValidator.validate_signature(
                client, "test_method",
                expected_params={"correct_param": str, "another_param": int}
            )
        
        error_msg = str(exc_info.value)
        
        # Should mention missing parameters
        assert "correct_param" in error_msg or "Missing parameters" in error_msg
        assert "another_param" in error_msg or "Missing parameters" in error_msg


class TestMethodSuggestions:
    """Test method name suggestion algorithm."""
    
    def test_exact_substring_match(self):
        """Test finding methods with exact substrings."""
        available = ["get_protein_data", "get_metabolite_data", "post_protein"]
        
        similar = APIMethodValidator.find_similar_methods(
            "protein", available
        )
        
        assert "get_protein_data" in similar
        assert "post_protein" in similar
        assert "get_metabolite_data" not in similar
    
    def test_close_match_suggestions(self):
        """Test finding close matches using string similarity."""
        available = ["map_identifiers", "resolve_batch", "search_proteins"]
        
        # Should find close matches
        similar = APIMethodValidator.find_similar_methods(
            "map_identifier", available  # Missing 's'
        )
        assert "map_identifiers" in similar
        
        # Should handle typos
        similar = APIMethodValidator.find_similar_methods(
            "serach_proteins", available  # Typo in 'search'
        )
        # May or may not find depending on similarity threshold
        # but should not crash
        assert isinstance(similar, list)