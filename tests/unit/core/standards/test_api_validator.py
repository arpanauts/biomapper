"""Tests for API method validator standards component."""

import pytest
import threading
import time
from typing import Any, Dict, List

from src.core.standards.api_validator import APIMethodValidator


class TestAPIMethodValidator:
    """Test APIMethodValidator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create test validator instance."""
        return APIMethodValidator()
    
    @pytest.fixture
    def sample_biological_data(self):
        """Create sample biological data for testing."""
        return {
            "uniprot_ids": ["P12345", "Q9Y6R4", "O00533"],
            "hmdb_ids": ["HMDB0000001", "HMDB0123456"],
            "gene_symbols": ["TP53", "BRCA1", "CD4"],
            "invalid_ids": ["", None, "INVALID_FORMAT"]
        }
    
    @pytest.fixture
    def valid_api_client(self):
        """Create a valid API client mock."""
        class ValidAPIClient:
            def get_protein_data(self, ids: List[str]) -> Dict[str, Any]:
                """Get protein data for given IDs."""
                return {"data": ids}
            
            def batch_query(self, queries: List[str]) -> List[Dict]:
                """Execute batch queries."""
                return [{"query": q, "result": "data"} for q in queries]
            
            def get_metadata(self) -> Dict[str, Any]:
                """Get API metadata."""
                return {"version": "1.0", "status": "active"}
            
            def search_identifiers(self, term: str) -> List[str]:
                """Search for identifiers."""
                return [f"result_{i}" for i in range(3)]
        
        return ValidAPIClient()
    
    @pytest.fixture
    def invalid_api_client(self):
        """Create an invalid API client mock."""
        class InvalidAPIClient:
            def get_protein_info(self, ids: List[str]) -> Dict:
                """Similar to get_protein_data but wrong name."""
                return {"data": ids}
            
            def batch_search(self) -> str:
                """Similar to batch_query but wrong name."""
                return "wrong"
        
        return InvalidAPIClient()

    def test_validate_method_exists_basic_functionality(self, validator, valid_api_client):
        """Test basic method existence validation."""
        # Test valid method
        result = validator.validate_method_exists(valid_api_client, "get_protein_data")
        assert result is True
        
        # Test another valid method
        result = validator.validate_method_exists(valid_api_client, "batch_query")
        assert result is True

    def test_validate_method_exists_edge_cases(self, validator, valid_api_client):
        """Test method validation with edge cases."""
        # Test nonexistent method
        with pytest.raises(AttributeError) as exc_info:
            validator.validate_method_exists(valid_api_client, "nonexistent_method")
        
        assert "Method 'nonexistent_method' not found" in str(exc_info.value)
        assert "Available methods:" in str(exc_info.value)
        
        # Test empty method name
        with pytest.raises(AttributeError):
            validator.validate_method_exists(valid_api_client, "")
        
        # Test None method name
        with pytest.raises(AttributeError):
            validator.validate_method_exists(valid_api_client, None)

    def test_find_similar_methods_functionality(self, validator):
        """Test similar method finding."""
        available_methods = [
            "get_protein_data", "get_protein_info", "fetch_protein_details",
            "batch_query", "search_identifiers", "get_metadata"
        ]
        
        # Test exact partial match
        similar = validator.find_similar_methods("protein", available_methods)
        assert len(similar) > 0
        assert any("protein" in method.lower() for method in similar)
        
        # Test fuzzy matching
        similar = validator.find_similar_methods("get_protien_data", available_methods)  # typo
        assert "get_protein_data" in similar
        
        # Test no matches
        similar = validator.find_similar_methods("totally_unrelated", available_methods)
        assert len(similar) <= 3  # Should return at most 3 suggestions

    def test_validate_signature_basic_functionality(self, validator, valid_api_client):
        """Test method signature validation."""
        # Test without expected params (should pass)
        result = validator.validate_signature(valid_api_client, "get_protein_data")
        assert result is True
        
        # Test with expected params
        expected_params = {"ids": List[str]}
        result = validator.validate_signature(
            valid_api_client, "get_protein_data", expected_params
        )
        assert result is True

    def test_validate_signature_edge_cases(self, validator, valid_api_client):
        """Test signature validation with edge cases."""
        # Test nonexistent method
        with pytest.raises(AttributeError):
            validator.validate_signature(valid_api_client, "nonexistent_method")
        
        # Test non-callable attribute
        valid_api_client.not_a_method = "string_value"
        with pytest.raises(ValueError):
            validator.validate_signature(valid_api_client, "not_a_method")

    def test_create_method_wrapper_functionality(self, validator, valid_api_client):
        """Test method wrapper creation."""
        # Create wrapper
        wrapped_method = validator.create_method_wrapper(
            valid_api_client, "get_protein_data"
        )
        
        # Test wrapper functionality
        result = wrapped_method(["P12345", "Q9Y6R4"])
        assert result is not None
        assert "data" in result
        assert result["data"] == ["P12345", "Q9Y6R4"]
        
        # Test wrapper preserves metadata
        assert wrapped_method.__name__ == "get_protein_data"
        assert wrapped_method.__doc__ is not None

    def test_create_method_wrapper_edge_cases(self, validator, valid_api_client):
        """Test method wrapper with edge cases."""
        # Test with nonexistent method
        with pytest.raises(AttributeError):
            validator.create_method_wrapper(valid_api_client, "nonexistent_method")
        
        # Test wrapper with invalid arguments
        wrapped_method = validator.create_method_wrapper(
            valid_api_client, "get_protein_data"
        )
        
        # This should raise TypeError due to wrong arguments
        with pytest.raises(TypeError):
            wrapped_method()  # Missing required argument

    def test_validate_client_interface_functionality(self, validator, valid_api_client):
        """Test client interface validation."""
        required_methods = ["get_protein_data", "batch_query"]
        optional_methods = ["get_metadata", "search_identifiers"]
        
        result = validator.validate_client_interface(
            valid_api_client, required_methods, optional_methods
        )
        
        # All methods should be available
        for method in required_methods + optional_methods:
            assert result[method] is True

    def test_validate_client_interface_edge_cases(self, validator, invalid_api_client):
        """Test client interface validation with edge cases."""
        required_methods = ["get_protein_data", "batch_query"]
        
        # Should raise ValueError for missing required methods
        with pytest.raises(ValueError) as exc_info:
            validator.validate_client_interface(invalid_api_client, required_methods)
        
        error_msg = str(exc_info.value)
        assert "missing required methods" in error_msg
        assert "get_protein_data" in error_msg
        assert "batch_query" in error_msg
        assert "Did you mean:" in error_msg  # Should suggest alternatives

    def test_api_validator_performance(self, validator, valid_api_client):
        """Test API validator performance with large method lists."""
        # Create large list of methods to check
        large_method_list = [f"method_{i}" for i in range(1000)]
        
        start_time = time.time()
        
        # Test method existence checking (should be fast)
        for method in ["get_protein_data", "batch_query", "get_metadata"]:
            validator.validate_method_exists(valid_api_client, method)
        
        execution_time = time.time() - start_time
        
        # Performance assertion
        assert execution_time < 0.1  # Should complete very quickly

    def test_api_validator_thread_safety(self, validator, valid_api_client):
        """Test API validator thread safety."""
        results = []
        errors = []
        
        def worker():
            try:
                # Each thread validates methods
                for method in ["get_protein_data", "batch_query", "get_metadata"]:
                    result = validator.validate_method_exists(valid_api_client, method)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 30  # 10 threads * 3 methods each
        assert all(r is True for r in results)


class TestPerformanceAPIValidator:
    """Performance tests for APIMethodValidator."""
    
    @pytest.mark.performance
    def test_large_api_validation_performance(self):
        """Test performance with large API interfaces."""
        # Create a large API client
        class LargeAPIClient:
            pass
        
        # Add many methods dynamically
        large_client = LargeAPIClient()
        for i in range(1000):
            setattr(large_client, f"method_{i}", lambda x: x)
        
        validator = APIMethodValidator()
        
        # Measure performance
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        # Validate many methods
        for i in range(100):
            validator.validate_method_exists(large_client, f"method_{i}")
        
        memory_after = self._get_memory_usage()
        execution_time = time.time() - start_time
        
        # Performance assertions
        assert execution_time < 1.0  # Should complete in reasonable time
        assert (memory_after - memory_before) < 50 * 1024 * 1024  # < 50MB memory increase

    def _get_memory_usage(self):
        """Get current memory usage."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return 0  # Skip memory check if psutil not available


class TestBiologicalAPIPatterns:
    """Test with realistic biological API patterns."""
    
    @pytest.fixture
    def uniprot_api_client(self):
        """Mock UniProt API client."""
        class UniProtAPIClient:
            def get_protein_data(self, accessions: List[str]) -> Dict[str, Any]:
                """Get protein data for UniProt accessions."""
                return {
                    "entries": [
                        {"accession": acc, "gene_name": f"GENE_{acc}"}
                        for acc in accessions
                    ]
                }
            
            def search_proteins(self, query: str) -> List[Dict]:
                """Search proteins by query."""
                return [{"accession": f"P{i:05d}", "score": 0.9} for i in range(5)]
            
            def get_xrefs(self, accession: str) -> Dict[str, List[str]]:
                """Get cross-references for a protein."""
                return {
                    "Ensembl": [f"ENSP{accession[1:]}"],
                    "GeneID": [f"{hash(accession) % 100000}"]
                }
        
        return UniProtAPIClient()
    
    @pytest.fixture
    def hmdb_api_client(self):
        """Mock HMDB API client."""
        class HMDBAPIClient:
            def get_metabolite_data(self, hmdb_ids: List[str]) -> Dict[str, Any]:
                """Get metabolite data for HMDB IDs."""
                return {
                    "metabolites": [
                        {"hmdb_id": hmdb_id, "name": f"Metabolite_{hmdb_id}"}
                        for hmdb_id in hmdb_ids
                    ]
                }
            
            def search_by_name(self, name: str) -> List[Dict]:
                """Search metabolites by name."""
                return [{"hmdb_id": f"HMDB{i:07d}", "name": name} for i in range(3)]
        
        return HMDBAPIClient()
    
    @pytest.fixture
    def real_world_api_specs(self):
        """Real-world API method specifications."""
        return {
            "uniprot": {
                "required": ["get_protein_data", "search_proteins"],
                "optional": ["get_xrefs", "get_protein_features"]
            },
            "hmdb": {
                "required": ["get_metabolite_data", "search_by_name"],
                "optional": ["get_pathways", "get_concentrations"]
            },
            "chembl": {
                "required": ["get_compound_data", "search_compounds"],
                "optional": ["get_activities", "get_targets"]
            }
        }

    def test_uniprot_api_validation(self, uniprot_api_client, real_world_api_specs):
        """Test UniProt API client validation."""
        validator = APIMethodValidator()
        specs = real_world_api_specs["uniprot"]
        
        result = validator.validate_client_interface(
            uniprot_api_client, specs["required"], specs["optional"]
        )
        
        # Verify required methods are available
        for method in specs["required"]:
            assert result[method] is True
        
        # Test actual method calls
        protein_data = uniprot_api_client.get_protein_data(["P12345", "Q9Y6R4"])
        assert "entries" in protein_data
        assert len(protein_data["entries"]) == 2

    def test_hmdb_api_validation(self, hmdb_api_client, real_world_api_specs):
        """Test HMDB API client validation."""
        validator = APIMethodValidator()
        specs = real_world_api_specs["hmdb"]
        
        result = validator.validate_client_interface(
            hmdb_api_client, specs["required"]
        )
        
        # Verify required methods are available
        for method in specs["required"]:
            assert result[method] is True
        
        # Test actual method calls
        metabolite_data = hmdb_api_client.get_metabolite_data(["HMDB0000001", "HMDB0000002"])
        assert "metabolites" in metabolite_data
        assert len(metabolite_data["metabolites"]) == 2

    def test_api_client_discovery(self, uniprot_api_client, hmdb_api_client):
        """Test automatic API client discovery and validation."""
        validator = APIMethodValidator()
        
        clients = {
            "uniprot": uniprot_api_client,
            "hmdb": hmdb_api_client
        }
        
        # Discover methods for each client
        for name, client in clients.items():
            available_methods = [
                m for m in dir(client) 
                if not m.startswith('_') and callable(getattr(client, m, None))
            ]
            
            assert len(available_methods) >= 2  # Should have at least 2 methods
            
            # Validate each discovered method exists
            for method in available_methods:
                result = validator.validate_method_exists(client, method)
                assert result is True

    def test_edge_case_api_patterns(self):
        """Test edge case API patterns that commonly cause issues."""
        validator = APIMethodValidator()
        
        # API client with property that looks like method
        class EdgeCaseClient:
            @property
            def not_a_method(self):
                return "property_value"
            
            def actual_method(self):
                return "method_value"
            
            # Method with complex signature
            def complex_method(self, required: str, optional: str = None, *args, **kwargs):
                return {"required": required, "optional": optional}
        
        client = EdgeCaseClient()
        
        # Should correctly identify actual methods vs properties
        result = validator.validate_method_exists(client, "actual_method")
        assert result is True
        
        with pytest.raises(ValueError):
            # Property should not validate as callable method
            validator.validate_signature(client, "not_a_method")
        
        # Complex method should validate
        result = validator.validate_method_exists(client, "complex_method")
        assert result is True


class TestAPIValidatorIntegration:
    """Integration tests for API validator with real biological patterns."""
    
    @pytest.fixture
    def mock_external_apis(self):
        """Mock external API responses for integration testing."""
        class MockAPIManager:
            def __init__(self):
                self.clients = {}
            
            def register_client(self, name: str, client: Any):
                self.clients[name] = client
            
            def validate_all_clients(self) -> Dict[str, bool]:
                validator = APIMethodValidator()
                results = {}
                
                for name, client in self.clients.items():
                    try:
                        # Basic validation - check if client has get method
                        methods = [m for m in dir(client) if not m.startswith('_')]
                        has_get_method = any('get' in m.lower() for m in methods)
                        results[name] = has_get_method
                    except Exception:
                        results[name] = False
                
                return results
        
        return MockAPIManager()

    @pytest.fixture
    def uniprot_api_client(self):
        """Mock UniProt API client."""
        class UniProtAPIClient:
            def get_protein_data(self, accessions: List[str]) -> Dict[str, Any]:
                """Get protein data for UniProt accessions."""
                return {
                    "entries": [
                        {"accession": acc, "gene_name": f"GENE_{acc}"}
                        for acc in accessions
                    ]
                }
            
            def search_proteins(self, query: str) -> List[Dict]:
                """Search proteins by query."""
                return [{"accession": f"P{i:05d}", "score": 0.9} for i in range(5)]
            
            def get_xrefs(self, accession: str) -> Dict[str, List[str]]:
                """Get cross-references for a protein."""
                return {
                    "Ensembl": [f"ENSP{accession[1:]}"],
                    "GeneID": [f"{hash(accession) % 100000}"]
                }
        
        return UniProtAPIClient()
    
    @pytest.fixture
    def hmdb_api_client(self):
        """Mock HMDB API client."""
        class HMDBAPIClient:
            def get_metabolite_data(self, hmdb_ids: List[str]) -> Dict[str, Any]:
                """Get metabolite data for HMDB IDs."""
                return {
                    "metabolites": [
                        {"hmdb_id": hmdb_id, "name": f"Metabolite_{hmdb_id}"}
                        for hmdb_id in hmdb_ids
                    ]
                }
            
            def search_by_name(self, name: str) -> List[Dict]:
                """Search metabolites by name."""
                return [{"hmdb_id": f"HMDB{i:07d}", "name": name} for i in range(3)]
        
        return HMDBAPIClient()

    def test_multi_api_validation_workflow(self, mock_external_apis, uniprot_api_client, hmdb_api_client):
        """Test validation workflow with multiple API clients."""
        # Register multiple clients
        mock_external_apis.register_client("uniprot", uniprot_api_client)
        mock_external_apis.register_client("hmdb", hmdb_api_client)
        
        # Validate all clients
        results = mock_external_apis.validate_all_clients()
        
        # All clients should pass basic validation
        assert all(results.values())
        assert "uniprot" in results
        assert "hmdb" in results

    def test_api_validation_error_recovery(self):
        """Test error recovery in API validation scenarios."""
        validator = APIMethodValidator()
        
        # Client that raises errors
        class ProblematicClient:
            def working_method(self):
                return "success"
            
            def error_method(self):
                raise ConnectionError("API temporarily unavailable")
            
            @property
            def property_that_looks_like_method(self):
                return "not callable"
        
        client = ProblematicClient()
        
        # Working method should validate
        assert validator.validate_method_exists(client, "working_method")
        
        # Error method should still validate as existing (validation != execution)
        assert validator.validate_method_exists(client, "error_method")
        
        # Property should not validate as callable
        with pytest.raises(ValueError):
            validator.validate_signature(client, "property_that_looks_like_method")

    def test_real_world_identifier_patterns(self):
        """Test API validation with real biological identifier patterns."""
        validator = APIMethodValidator()
        
        class BiologicalAPIClient:
            def get_uniprot_data(self, accessions: List[str]) -> Dict:
                """Standard UniProt accession format: P12345, Q9Y6R4, etc."""
                return {"data": [acc for acc in accessions if self._is_valid_uniprot(acc)]}
            
            def get_hmdb_data(self, hmdb_ids: List[str]) -> Dict:
                """HMDB ID format: HMDB0000001, HMDB0123456, etc."""
                return {"data": [hid for hid in hmdb_ids if hid.startswith("HMDB")]}
            
            def get_gene_data(self, symbols: List[str]) -> Dict:
                """Gene symbols: TP53, BRCA1, CD4, etc."""
                return {"data": symbols}
            
            def _is_valid_uniprot(self, acc: str) -> bool:
                """Basic UniProt accession validation."""
                return len(acc) == 6 and acc[0] in "PQOA" and acc[1:].isalnum()
        
        client = BiologicalAPIClient()
        
        # Validate biological data handling methods
        required_methods = ["get_uniprot_data", "get_hmdb_data", "get_gene_data"]
        
        result = validator.validate_client_interface(client, required_methods)
        
        for method in required_methods:
            assert result[method] is True
        
        # Test with actual biological identifiers
        uniprot_data = client.get_uniprot_data(["P12345", "Q9Y6R4", "INVALID"])
        assert len(uniprot_data["data"]) == 2  # Only valid UniProt IDs
        
        hmdb_data = client.get_hmdb_data(["HMDB0000001", "HMDB0123456", "INVALID"])
        assert len(hmdb_data["data"]) == 2  # Only valid HMDB IDs