"""Tests for base action classes and interfaces."""

import pytest
import pandas as pd
from typing import Dict, Any, List
from unittest.mock import Mock

from actions.base import BaseStrategyAction, StrategyAction, ActionContext


class TestBaseStrategyAction:
    """Test BaseStrategyAction interface and contracts."""
    
    @pytest.fixture
    def action_context(self):
        """Create test action context with biological data."""
        return {
            "datasets": {
                "test_proteins": pd.DataFrame({
                    "uniprot_id": ["P12345", "Q9Y6R4", "O00533"],
                    "gene_symbol": ["TP53", "BRCA1", "CD4"],
                    "description": ["Tumor protein p53", "BRCA1 protein", "CD4 antigen"]
                }),
                "test_metabolites": pd.DataFrame({
                    "hmdb_id": ["HMDB0000001", "HMDB0000002"],
                    "name": ["1-Methylhistidine", "1,3-Diaminopropane"],
                    "formula": ["C7H11N3O2", "C3H10N2"]
                })
            },
            "current_identifiers": ["P12345", "Q9Y6R4"],
            "statistics": {"processed_count": 0},
            "output_files": []
        }
    
    @pytest.fixture
    def sample_biological_data(self):
        """Create sample biological dataset with edge cases."""
        return pd.DataFrame({
            "protein_id": ["P04637", "P38398", "P01730", "Q6EMK4"],  # Include problematic Q6EMK4
            "gene_symbol": ["TP53", "BRCA1", "CD4", "PROBLEMATIC"],
            "organism": ["Homo sapiens"] * 4,
            "reviewed": [True, True, True, False],
            "length": [393, 1863, 458, 234]
        })
    
    def test_base_action_is_abstract(self):
        """Test that BaseStrategyAction is abstract and cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseStrategyAction()
    
    def test_base_action_interface_requirements(self):
        """Test that subclasses must implement the execute method."""
        
        class IncompleteAction(BaseStrategyAction):
            pass  # Missing execute method
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteAction()
    
    def test_base_action_inheritance_pattern(self):
        """Test proper implementation of BaseStrategyAction interface."""
        
        class ValidAction(BaseStrategyAction):
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
                    "details": {"action_type": "test"}
                }
        
        # Should be able to instantiate
        action = ValidAction()
        assert isinstance(action, BaseStrategyAction)
        assert hasattr(action, 'execute')
    
    @pytest.mark.asyncio
    async def test_execute_method_signature(self, action_context):
        """Test execute method signature compliance."""
        
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
                # Verify all required parameters are present
                assert isinstance(current_identifiers, list)
                assert isinstance(current_ontology_type, str)
                assert isinstance(action_params, dict)
                assert isinstance(context, dict)
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {}
                }
        
        action = TestAction()
        result = await action.execute(
            current_identifiers=["P12345", "Q9Y6R4"],
            current_ontology_type="protein",
            action_params={"test_param": "value"},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        # Verify standard result format
        assert "input_identifiers" in result
        assert "output_identifiers" in result
        assert "output_ontology_type" in result
        assert "provenance" in result
        assert "details" in result
    
    @pytest.mark.asyncio
    async def test_action_context_handling(self, action_context):
        """Test action context handling and validation."""
        
        class ContextTestAction(BaseStrategyAction):
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                # Test context access patterns
                datasets = context.get("datasets", {})
                assert "test_proteins" in datasets
                assert isinstance(datasets["test_proteins"], pd.DataFrame)
                
                # Test context modification
                context["statistics"]["processed_count"] += len(current_identifiers)
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {"context_modified": True}
                }
        
        action = ContextTestAction()
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        # Verify context was modified
        assert action_context["statistics"]["processed_count"] == 1
        assert result["details"]["context_modified"] is True
    
    @pytest.mark.asyncio
    async def test_biological_data_processing(self, sample_biological_data, action_context):
        """Test action with realistic biological data."""
        
        class BiologicalDataAction(BaseStrategyAction):
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                # Process biological data
                processed_ids = []
                for protein_id in current_identifiers:
                    # Validate UniProt ID format
                    if protein_id.startswith(('P', 'Q', 'O')) and len(protein_id) == 6:
                        processed_ids.append(protein_id)
                    else:
                        # Handle edge cases like Q6EMK4
                        if protein_id == "Q6EMK4":
                            # Known problematic identifier - handle specially
                            processed_ids.append(protein_id)  # Include with note
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": processed_ids,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [{"action": "biological_validation", "timestamp": "2025-01-01"}],
                    "details": {
                        "validated_ids": len(processed_ids),
                        "edge_cases_handled": 1 if "Q6EMK4" in current_identifiers else 0
                    }
                }
        
        action_context["datasets"]["input_data"] = sample_biological_data
        action = BiologicalDataAction()
        
        # Test with biological identifiers including edge case
        result = await action.execute(
            current_identifiers=["P04637", "P38398", "Q6EMK4"],
            current_ontology_type="protein",
            action_params={},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        # Validate biological data handling
        assert len(result["output_identifiers"]) == 3
        assert all(pid.startswith(('P', 'Q', 'O')) for pid in result["output_identifiers"])
        assert "Q6EMK4" in result["output_identifiers"]  # Edge case handled
        assert result["details"]["edge_cases_handled"] == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_and_propagation(self):
        """Test error handling and propagation in actions."""
        
        class ErrorProneAction(BaseStrategyAction):
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                if action_params.get("force_error"):
                    raise ValueError("Simulated action error")
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": [],
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {}
                }
        
        action = ErrorProneAction()
        
        # Test error propagation
        with pytest.raises(ValueError, match="Simulated action error"):
            await action.execute(
                current_identifiers=["P12345"],
                current_ontology_type="protein",
                action_params={"force_error": True},
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context={}
            )
        
        # Test successful execution
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={"force_error": False},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        assert result is not None
    
    def test_strategy_action_alias(self):
        """Test that StrategyAction is correctly aliased to BaseStrategyAction."""
        assert StrategyAction is BaseStrategyAction
        assert issubclass(StrategyAction, BaseStrategyAction)
    
    def test_action_context_type_alias(self):
        """Test ActionContext type alias."""
        assert ActionContext == Dict[str, Any]
        
        # Test that it can be used for type hints
        def test_function(context: ActionContext) -> None:
            assert isinstance(context, dict)
        
        test_function({"test": "value"})
    
    @pytest.mark.asyncio
    async def test_action_lifecycle_management(self, action_context):
        """Test action lifecycle and state management."""
        
        class StatefulAction(BaseStrategyAction):
            def __init__(self):
                self.execution_count = 0
                self.state = "initialized"
            
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                self.execution_count += 1
                self.state = "executed"
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {
                        "execution_count": self.execution_count,
                        "state": self.state
                    }
                }
        
        action = StatefulAction()
        assert action.execution_count == 0
        assert action.state == "initialized"
        
        # First execution
        result1 = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert action.execution_count == 1
        assert action.state == "executed"
        assert result1["details"]["execution_count"] == 1
        
        # Second execution
        result2 = await action.execute(
            current_identifiers=["Q9Y6R4"],
            current_ontology_type="protein",
            action_params={},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        assert action.execution_count == 2
        assert result2["details"]["execution_count"] == 2
    
    @pytest.mark.asyncio
    async def test_parameter_validation_mechanisms(self):
        """Test parameter validation in actions."""
        
        class ValidatingAction(BaseStrategyAction):
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                # Parameter validation
                required_params = ["threshold", "method"]
                for param in required_params:
                    if param not in action_params:
                        raise ValueError(f"Missing required parameter: {param}")
                
                if not 0.0 <= action_params["threshold"] <= 1.0:
                    raise ValueError("Threshold must be between 0.0 and 1.0")
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {"validated": True}
                }
        
        action = ValidatingAction()
        
        # Test missing parameters
        with pytest.raises(ValueError, match="Missing required parameter: threshold"):
            await action.execute(
                current_identifiers=["P12345"],
                current_ontology_type="protein",
                action_params={"method": "test"},
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context={}
            )
        
        # Test invalid parameter values
        with pytest.raises(ValueError, match="Threshold must be between"):
            await action.execute(
                current_identifiers=["P12345"],
                current_ontology_type="protein",
                action_params={"threshold": 1.5, "method": "test"},
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context={}
            )
        
        # Test valid parameters
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={"threshold": 0.8, "method": "test"},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        assert result["details"]["validated"] is True
    
    @pytest.mark.asyncio
    async def test_result_formatting_compliance(self, action_context):
        """Test result formatting and standard field compliance."""
        
        class FormattingAction(BaseStrategyAction):
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
                    "output_identifiers": ["mapped_" + id for id in current_identifiers],
                    "output_ontology_type": "mapped_protein",
                    "provenance": [
                        {"action": "format_test", "timestamp": "2025-01-01", "source": "test"}
                    ],
                    "details": {
                        "mapping_method": "test_mapping",
                        "confidence": 0.95,
                        "additional_info": "test_data"
                    }
                }
        
        action = FormattingAction()
        result = await action.execute(
            current_identifiers=["P12345", "Q9Y6R4"],
            current_ontology_type="protein",
            action_params={},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=action_context
        )
        
        # Verify all required fields are present
        required_fields = ["input_identifiers", "output_identifiers", "output_ontology_type", "provenance", "details"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Verify field types and content
        assert isinstance(result["input_identifiers"], list)
        assert isinstance(result["output_identifiers"], list)
        assert isinstance(result["output_ontology_type"], str)
        assert isinstance(result["provenance"], list)
        assert isinstance(result["details"], dict)
        
        # Verify content correctness
        assert result["input_identifiers"] == ["P12345", "Q9Y6R4"]
        assert result["output_identifiers"] == ["mapped_P12345", "mapped_Q9Y6R4"]
        assert result["output_ontology_type"] == "mapped_protein"
        assert len(result["provenance"]) == 1
        assert "mapping_method" in result["details"]


class TestActionDocumentationRequirements:
    """Test documentation and interface requirements for actions."""
    
    def test_action_docstring_requirements(self):
        """Test that actions have proper documentation."""
        
        class DocumentedAction(BaseStrategyAction):
            """
            Well-documented action for testing purposes.
            
            This action demonstrates proper documentation patterns for biological
            data processing actions.
            
            Args:
                current_identifiers: List of biological identifiers to process
                current_ontology_type: Type of biological entity (protein, metabolite, etc.)
                action_params: Configuration parameters for the action
                source_endpoint: Source data endpoint
                target_endpoint: Target data endpoint  
                context: Execution context with datasets and metadata
                
            Returns:
                Dictionary with standard action result format including:
                - input_identifiers: Original identifiers
                - output_identifiers: Processed identifiers
                - output_ontology_type: Type of output entities
                - provenance: Processing history
                - details: Additional processing information
            """
            
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
                    "details": {}
                }
        
        action = DocumentedAction()
        assert action.__doc__ is not None
        assert "biological" in action.__doc__.lower()
        assert "identifiers" in action.__doc__.lower()
        assert "returns" in action.__doc__.lower()


class TestActionSecurityAndSafety:
    """Test security and safety aspects of action execution."""
    
    @pytest.mark.asyncio
    async def test_safe_context_access(self):
        """Test safe access to context data."""
        
        class SafeContextAction(BaseStrategyAction):
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                # Safe context access patterns
                datasets = context.get("datasets", {})
                statistics = context.get("statistics", {})
                
                # Don't assume key existence
                safe_data = datasets.get("safe_key", pd.DataFrame())
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": current_identifiers,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {"safe_access": True}
                }
        
        action = SafeContextAction()
        
        # Test with minimal context
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}  # Empty context should not cause errors
        )
        
        assert result["details"]["safe_access"] is True
    
    @pytest.mark.asyncio 
    async def test_input_sanitization(self):
        """Test input sanitization and validation."""
        
        class SanitizingAction(BaseStrategyAction):
            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Any,
                target_endpoint: Any,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                # Sanitize identifiers
                sanitized_ids = []
                # SQL injection patterns to block
                dangerous_patterns = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'EXEC', '--', ';']
                
                for id_str in current_identifiers:
                    if isinstance(id_str, str):
                        # First check for dangerous SQL patterns (case insensitive)
                        contains_dangerous = any(pattern.upper() in id_str.upper() for pattern in dangerous_patterns)
                        
                        if not contains_dangerous:
                            # Remove potentially harmful characters but allow biological ID formats
                            clean_id = ''.join(c for c in id_str if c.isalnum() or c in '-_.')
                            if clean_id:  # Only add non-empty results
                                sanitized_ids.append(clean_id)
                
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": sanitized_ids,
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {"sanitized_count": len(sanitized_ids)}
                }
        
        action = SanitizingAction()
        
        # Test with potentially harmful input
        result = await action.execute(
            current_identifiers=["P12345", "'; DROP TABLE proteins; --", "Q9Y6R4"],
            current_ontology_type="protein",
            action_params={},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        
        # Verify sanitization occurred
        assert "DROP" not in ' '.join(result["output_identifiers"])
        assert "--" not in ' '.join(result["output_identifiers"])
        assert result["details"]["sanitized_count"] == 2  # Only valid IDs kept