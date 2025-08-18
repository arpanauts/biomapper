"""Tests for typed base action classes and Pydantic integration."""

import pytest
from typing import Dict, Any, List, Type, Optional
from unittest.mock import Mock
from pydantic import BaseModel, Field, ValidationError

from actions.typed_base import TypedStrategyAction, StandardActionResult
from actions.base import BaseStrategyAction


class TestTypedStrategyAction:
    """Test TypedStrategyAction functionality and type safety."""
    
    def test_typed_action_inheritance(self):
        """Test that TypedStrategyAction properly inherits from BaseStrategyAction."""
        
        class TestParams(BaseModel):
            threshold: float = Field(0.8, ge=0.0, le=1.0)
            
        class TestResult(BaseModel):
            processed_count: int
            success: bool = True
        
        class TestTypedAction(TypedStrategyAction[TestParams, TestResult]):
            def get_params_model(self) -> Type[TestParams]:
                return TestParams
            
            def get_result_model(self) -> Type[TestResult]:
                return TestResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: TestParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> TestResult:
                return TestResult(processed_count=len(current_identifiers))
        
        action = TestTypedAction()
        assert isinstance(action, BaseStrategyAction)
        assert isinstance(action, TypedStrategyAction)
        assert hasattr(action, 'execute')
        assert hasattr(action, 'execute_typed')
    
    def test_pydantic_model_integration(self):
        """Test Pydantic model integration for parameters and results."""
        
        class BiologicalParams(BaseModel):
            """Parameters for biological data processing."""
            input_key: str = Field(..., description="Input dataset key")
            entity_type: str = Field("protein", description="Biological entity type")
            validation_threshold: float = Field(0.9, ge=0.0, le=1.0)
            normalize_ids: bool = Field(True, description="Whether to normalize identifiers")
            
        class BiologicalResult(BaseModel):
            """Results from biological data processing."""
            input_identifiers: List[str]
            output_identifiers: List[str] 
            output_ontology_type: str
            validation_stats: Dict[str, int] = Field(default_factory=dict)
            normalized_count: int = 0
        
        class BiologicalAction(TypedStrategyAction[BiologicalParams, BiologicalResult]):
            def get_params_model(self) -> Type[BiologicalParams]:
                return BiologicalParams
            
            def get_result_model(self) -> Type[BiologicalResult]:
                return BiologicalResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: BiologicalParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> BiologicalResult:
                # Simulate biological ID processing
                processed_ids = []
                normalized_count = 0
                
                for bio_id in current_identifiers:
                    if params.normalize_ids and bio_id.startswith("UniProtKB:"):
                        processed_ids.append(bio_id.replace("UniProtKB:", ""))
                        normalized_count += 1
                    else:
                        processed_ids.append(bio_id)
                
                return BiologicalResult(
                    input_identifiers=current_identifiers,
                    output_identifiers=processed_ids,
                    output_ontology_type=current_ontology_type,
                    validation_stats={"total": len(current_identifiers), "valid": len(processed_ids)},
                    normalized_count=normalized_count
                )
        
        action = BiologicalAction()
        
        # Test parameter model access
        params_model = action.get_params_model()
        assert params_model == BiologicalParams
        
        # Test result model access
        result_model = action.get_result_model()
        assert result_model == BiologicalResult
        
        # Test model instantiation
        params = BiologicalParams(input_key="test_data", entity_type="protein")
        assert params.input_key == "test_data"
        assert params.entity_type == "protein"
        assert params.validation_threshold == 0.9  # Default value
        assert params.normalize_ids is True  # Default value
    
    def test_type_validation_and_coercion(self):
        """Test type validation and coercion with Pydantic models."""
        
        class StrictParams(BaseModel):
            protein_count: int = Field(..., ge=1)
            confidence_score: float = Field(..., ge=0.0, le=1.0)
            protein_ids: List[str] = Field(..., min_items=1)
            metadata: Dict[str, Any] = Field(default_factory=dict)
            
        class StrictResult(BaseModel):
            success: bool
            processed_proteins: int
            error_message: Optional[str] = None
        
        class StrictTypedAction(TypedStrategyAction[StrictParams, StrictResult]):
            def get_params_model(self) -> Type[StrictParams]:
                return StrictParams
            
            def get_result_model(self) -> Type[StrictResult]:
                return StrictResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: StrictParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> StrictResult:
                return StrictResult(
                    success=True,
                    processed_proteins=params.protein_count
                )
        
        action = StrictTypedAction()
        
        # Test valid parameters
        valid_params = StrictParams(
            protein_count=5,
            confidence_score=0.85,
            protein_ids=["P12345", "Q9Y6R4"],
            metadata={"source": "test"}
        )
        assert valid_params.protein_count == 5
        assert valid_params.confidence_score == 0.85
        
        # Test type coercion
        coerced_params = StrictParams(
            protein_count="10",  # String should be coerced to int
            confidence_score="0.9",  # String should be coerced to float
            protein_ids=["P12345"],
            metadata={}
        )
        assert coerced_params.protein_count == 10
        assert coerced_params.confidence_score == 0.9
        
        # Test validation errors
        with pytest.raises(ValidationError) as exc_info:
            StrictParams(
                protein_count=-1,  # Invalid: less than 1
                confidence_score=1.5,  # Invalid: greater than 1.0
                protein_ids=[],  # Invalid: empty list
                metadata={}
            )
        
        errors = exc_info.value.errors()
        assert len(errors) >= 3  # Should have multiple validation errors
    
    @pytest.mark.asyncio
    async def test_parameter_model_validation_in_execute(self):
        """Test parameter validation during action execution."""
        
        class ValidationParams(BaseModel):
            required_field: str = Field(..., description="Required string field")
            numeric_field: int = Field(..., ge=0, le=100)
            
        class ValidationResult(BaseModel):
            validation_passed: bool
            
        class ValidationAction(TypedStrategyAction[ValidationParams, ValidationResult]):
            def get_params_model(self) -> Type[ValidationParams]:
                return ValidationParams
            
            def get_result_model(self) -> Type[ValidationResult]:
                return ValidationResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: ValidationParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> ValidationResult:
                return ValidationResult(validation_passed=True)
        
        action = ValidationAction()
        
        # Test with valid parameters (via execute method for backward compatibility)
        valid_result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={"required_field": "test", "numeric_field": 50},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        
        assert valid_result["details"]["validation_passed"] is True
        
        # Test with invalid parameters
        invalid_result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={"numeric_field": 150},  # Missing required_field, invalid numeric_field
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        
        # Should return error result due to validation failure
        assert "error" in invalid_result["details"]
        assert "validation_errors" in invalid_result["details"]
    
    def test_generic_type_handling(self):
        """Test generic type handling and constraints."""
        
        # Test that TypedStrategyAction can work with different parameter/result combinations
        
        class MinimalParams(BaseModel):
            name: str
            
        class MinimalResult(BaseModel):
            result: str
            
        class ComplexParams(BaseModel):
            identifiers: List[str]
            metadata: Dict[str, Any]
            scores: List[float]
            
        class ComplexResult(BaseModel):
            processed_data: Dict[str, List[str]]
            statistics: Dict[str, int]
            warnings: List[str] = Field(default_factory=list)
        
        # Both should be valid typed action configurations
        class MinimalAction(TypedStrategyAction[MinimalParams, MinimalResult]):
            def get_params_model(self) -> Type[MinimalParams]:
                return MinimalParams
            
            def get_result_model(self) -> Type[MinimalResult]:
                return MinimalResult
            
            async def execute_typed(self, *args, **kwargs) -> MinimalResult:
                return MinimalResult(result="minimal")
        
        class ComplexAction(TypedStrategyAction[ComplexParams, ComplexResult]):
            def get_params_model(self) -> Type[ComplexParams]:
                return ComplexParams
            
            def get_result_model(self) -> Type[ComplexResult]:
                return ComplexResult
            
            async def execute_typed(self, *args, **kwargs) -> ComplexResult:
                return ComplexResult(
                    processed_data={"proteins": ["P12345"]},
                    statistics={"count": 1}
                )
        
        minimal_action = MinimalAction()
        complex_action = ComplexAction()
        
        assert minimal_action.get_params_model() == MinimalParams
        assert minimal_action.get_result_model() == MinimalResult
        assert complex_action.get_params_model() == ComplexParams
        assert complex_action.get_result_model() == ComplexResult
    
    @pytest.mark.asyncio
    async def test_model_serialization_deserialization(self):
        """Test model serialization and deserialization."""
        
        class SerializableParams(BaseModel):
            protein_ids: List[str]
            thresholds: Dict[str, float] 
            metadata: Dict[str, Any]
            
        class SerializableResult(BaseModel):
            mapped_proteins: List[str]
            statistics: Dict[str, int]
            
        class SerializableAction(TypedStrategyAction[SerializableParams, SerializableResult]):
            def get_params_model(self) -> Type[SerializableParams]:
                return SerializableParams
            
            def get_result_model(self) -> Type[SerializableResult]:
                return SerializableResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: SerializableParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> SerializableResult:
                return SerializableResult(
                    mapped_proteins=params.protein_ids,
                    statistics={"processed": len(params.protein_ids)}
                )
        
        action = SerializableAction()
        
        # Create parameters
        params_dict = {
            "protein_ids": ["P12345", "Q9Y6R4"],
            "thresholds": {"confidence": 0.8, "coverage": 0.9},
            "metadata": {"source": "test", "version": 1.0}
        }
        
        # Test via execute method (which handles serialization/deserialization)
        result = await action.execute(
            current_identifiers=["P12345", "Q9Y6R4"],
            current_ontology_type="protein",
            action_params=params_dict,
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        
        # Verify result structure
        assert "details" in result
        assert "mapped_proteins" in result["details"]
        assert "statistics" in result["details"]
        assert result["details"]["mapped_proteins"] == ["P12345", "Q9Y6R4"]
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """Test validation error handling and reporting."""
        
        class ValidationTestParams(BaseModel):
            required_string: str = Field(..., min_length=1)
            positive_number: int = Field(..., gt=0)
            valid_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
            
        class ValidationTestResult(BaseModel):
            success: bool
            
        class ValidationTestAction(TypedStrategyAction[ValidationTestParams, ValidationTestResult]):
            def get_params_model(self) -> Type[ValidationTestParams]:
                return ValidationTestParams
            
            def get_result_model(self) -> Type[ValidationTestResult]:
                return ValidationTestResult
            
            async def execute_typed(self, *args, **kwargs) -> ValidationTestResult:
                return ValidationTestResult(success=True)
        
        action = ValidationTestAction()
        
        # Test multiple validation errors
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein", 
            action_params={
                "required_string": "",  # Too short
                "positive_number": -5,  # Not positive
                "valid_email": "invalid-email"  # Invalid format
            },
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        
        # Should return error result with validation details
        assert "error" in result["details"]
        assert "validation_errors" in result["details"]
        
        validation_errors = result["details"]["validation_errors"]
        assert len(validation_errors) == 3  # One error per field
        
        # Check that error details are informative
        error_fields = [error["loc"][0] for error in validation_errors]
        assert "required_string" in error_fields
        assert "positive_number" in error_fields
        assert "valid_email" in error_fields
    
    def test_runtime_type_checking(self):
        """Test runtime type checking and enforcement."""
        
        class TypeCheckParams(BaseModel):
            strings: List[str]
            numbers: List[int]
            mapping: Dict[str, str]
            
        class TypeCheckResult(BaseModel):
            type_check_passed: bool
            
        class TypeCheckAction(TypedStrategyAction[TypeCheckParams, TypeCheckResult]):
            def get_params_model(self) -> Type[TypeCheckParams]:
                return TypeCheckParams
            
            def get_result_model(self) -> Type[TypeCheckResult]:
                return TypeCheckResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: TypeCheckParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> TypeCheckResult:
                # Runtime type checking
                assert isinstance(params.strings, list)
                assert all(isinstance(s, str) for s in params.strings)
                assert isinstance(params.numbers, list)
                assert all(isinstance(n, int) for n in params.numbers)
                assert isinstance(params.mapping, dict)
                assert all(isinstance(k, str) and isinstance(v, str) 
                          for k, v in params.mapping.items())
                
                return TypeCheckResult(type_check_passed=True)
        
        # Test valid types
        params = TypeCheckParams(
            strings=["a", "b", "c"],
            numbers=[1, 2, 3],
            mapping={"key1": "value1", "key2": "value2"}
        )
        
        assert params.strings == ["a", "b", "c"]
        assert params.numbers == [1, 2, 3]
        assert params.mapping == {"key1": "value1", "key2": "value2"}
        
        # Test type coercion where possible
        coerced_params = TypeCheckParams(
            strings=["a", "b"],
            numbers=["1", "2"],  # String numbers should be coerced
            mapping={"key": "value"}
        )
        
        assert coerced_params.numbers == [1, 2]  # Should be converted to ints
    
    def test_type_conversion_handling(self):
        """Test type conversion and transformation handling."""
        
        class ConversionParams(BaseModel):
            # Test various conversion scenarios
            numeric_string: int  # String to int conversion
            string_list: List[str]  # Ensure list elements are strings
            optional_field: Optional[str] = None
            
            class Config:
                # Allow conversion from compatible types
                validate_assignment = True
        
        class ConversionResult(BaseModel):
            converted_successfully: bool
            converted_values: Dict[str, Any]
        
        class ConversionAction(TypedStrategyAction[ConversionParams, ConversionResult]):
            def get_params_model(self) -> Type[ConversionParams]:
                return ConversionParams
            
            def get_result_model(self) -> Type[ConversionResult]:
                return ConversionResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: ConversionParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> ConversionResult:
                return ConversionResult(
                    converted_successfully=True,
                    converted_values={
                        "numeric_string": params.numeric_string,
                        "string_list": params.string_list,
                        "optional_field": params.optional_field
                    }
                )
        
        # Test successful conversions
        params = ConversionParams(
            numeric_string="123",  # Should convert to int
            string_list=["a", "b", "c"],
            optional_field="present"
        )
        
        assert params.numeric_string == 123
        assert isinstance(params.numeric_string, int)
        assert params.string_list == ["a", "b", "c"]
        assert params.optional_field == "present"
        
        # Test optional field handling
        params_optional = ConversionParams(
            numeric_string="456",
            string_list=["x", "y"]
            # optional_field not provided - should use default None
        )
        
        assert params_optional.numeric_string == 456
        assert params_optional.optional_field is None


class TestTypedActionBackwardCompatibility:
    """Test backward compatibility with existing action infrastructure."""
    
    @pytest.mark.asyncio
    async def test_backward_compatible_execute_method(self):
        """Test that typed actions work with legacy execute() calls."""
        
        class BackwardCompatParams(BaseModel):
            input_data: str
            
        class BackwardCompatResult(BaseModel):
            output_data: str
            success: bool = True
        
        class BackwardCompatAction(TypedStrategyAction[BackwardCompatParams, BackwardCompatResult]):
            def get_params_model(self) -> Type[BackwardCompatParams]:
                return BackwardCompatParams
            
            def get_result_model(self) -> Type[BackwardCompatResult]:
                return BackwardCompatResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: BackwardCompatParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> BackwardCompatResult:
                return BackwardCompatResult(
                    output_data=f"processed_{params.input_data}",
                    success=True
                )
        
        action = BackwardCompatAction()
        
        # Test legacy execute() method interface
        result = await action.execute(
            current_identifiers=["P12345", "Q9Y6R4"],
            current_ontology_type="protein",
            action_params={"input_data": "test_data"},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={}
        )
        
        # Verify standard result format
        assert "input_identifiers" in result
        assert "output_identifiers" in result
        assert "output_ontology_type" in result
        assert "provenance" in result
        assert "details" in result
        
        # Verify our custom data is in details
        assert "output_data" in result["details"]
        assert "success" in result["details"]
        assert result["details"]["output_data"] == "processed_test_data"
    
    @pytest.mark.asyncio
    async def test_context_conversion_dict_to_typed(self):
        """Test context conversion from dict to StrategyExecutionContext."""
        
        class ContextParams(BaseModel):
            use_context: bool = True
            
        class ContextResult(BaseModel):
            context_type: str
            context_data: Dict[str, Any]
        
        class ContextAction(TypedStrategyAction[ContextParams, ContextResult]):
            def get_params_model(self) -> Type[ContextParams]:
                return ContextParams
            
            def get_result_model(self) -> Type[ContextResult]:
                return ContextResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: ContextParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> ContextResult:
                context_type = type(context).__name__
                
                # Extract some context data based on type
                if hasattr(context, '_dict'):  # MockContext
                    context_data = {"source": "mock", "keys": list(context._dict.keys())}
                elif isinstance(context, dict):
                    context_data = {"source": "dict", "keys": list(context.keys())}
                else:
                    context_data = {"source": "typed", "type": str(type(context))}
                
                return ContextResult(
                    context_type=context_type,
                    context_data=context_data
                )
        
        action = ContextAction()
        
        # Test with dictionary context
        dict_context = {
            "datasets": {"test": [{"id": "P12345"}]},
            "statistics": {"count": 1},
            "custom_data": "test_value"
        }
        
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={"use_context": True},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=dict_context
        )
        
        # Verify context was handled appropriately
        assert "context_type" in result["details"]
        assert "context_data" in result["details"]
    
    @pytest.mark.asyncio
    async def test_mvp_action_compatibility(self):
        """Test compatibility with MVP actions that use dict context."""
        
        class MVPParams(BaseModel):
            data_key: str
            
        class MVPResult(BaseModel):
            mvp_success: bool
            
        class MVPCompatibleAction(TypedStrategyAction[MVPParams, MVPResult]):
            def get_params_model(self) -> Type[MVPParams]:
                return MVPParams
            
            def get_result_model(self) -> Type[MVPResult]:
                return MVPResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: MVPParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> MVPResult:
                # MVP actions should receive MockContext that behaves like a dict
                assert hasattr(context, 'get')  # Dict-like behavior
                assert hasattr(context, '__getitem__')  # Dict-like access
                
                return MVPResult(mvp_success=True)
        
        # Simulate MVP action registration pattern
        MVPCompatibleAction.__name__ = "LoadDatasetIdentifiersAction"  # MVP action name
        
        action = MVPCompatibleAction()
        
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={"data_key": "test"},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context={"datasets": {}, "statistics": {}}
        )
        
        assert result["details"]["mvp_success"] is True
    
    def test_standard_action_result_model(self):
        """Test the StandardActionResult model for common use cases."""
        
        # Test StandardActionResult model
        result = StandardActionResult(
            input_identifiers=["P12345", "Q9Y6R4"],
            output_identifiers=["mapped_P12345", "mapped_Q9Y6R4"],
            output_ontology_type="mapped_protein",
            provenance=[{"action": "test_mapping", "timestamp": "2025-01-01"}],
            details={"mapping_method": "test", "confidence": 0.95}
        )
        
        # Verify all fields are accessible
        assert result.input_identifiers == ["P12345", "Q9Y6R4"]
        assert result.output_identifiers == ["mapped_P12345", "mapped_Q9Y6R4"]
        assert result.output_ontology_type == "mapped_protein"
        assert len(result.provenance) == 1
        assert result.details["mapping_method"] == "test"
        
        # Test serialization
        result_dict = result.model_dump()
        assert "input_identifiers" in result_dict
        assert "output_identifiers" in result_dict
        assert "output_ontology_type" in result_dict
        assert "provenance" in result_dict
        assert "details" in result_dict
        
        # Test default values
        minimal_result = StandardActionResult(
            input_identifiers=["P12345"],
            output_identifiers=["P12345"],
            output_ontology_type="protein"
        )
        assert minimal_result.provenance == []
        assert minimal_result.details == {}


class TestTypedActionErrorHandling:
    """Test error handling in typed actions."""
    
    @pytest.mark.asyncio
    async def test_typed_execution_error_handling(self):
        """Test error handling during typed execution."""
        
        class ErrorParams(BaseModel):
            force_error: bool = False
            error_type: str = "runtime"
            
        class ErrorResult(BaseModel):
            success: bool
            
        class ErrorAction(TypedStrategyAction[ErrorParams, ErrorResult]):
            def get_params_model(self) -> Type[ErrorParams]:
                return ErrorParams
            
            def get_result_model(self) -> Type[ErrorResult]:
                return ErrorResult
            
            async def execute_typed(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                params: ErrorParams,
                source_endpoint: Any,
                target_endpoint: Any,
                context: Any,
            ) -> ErrorResult:
                if params.force_error:
                    if params.error_type == "runtime":
                        raise RuntimeError("Forced runtime error")
                    elif params.error_type == "value":
                        raise ValueError("Forced value error")
                    elif params.error_type == "type":
                        raise TypeError("Forced type error")
                
                return ErrorResult(success=True)
        
        action = ErrorAction()
        
        # Test different error types get propagated
        with pytest.raises(RuntimeError, match="Forced runtime error"):
            await action.execute(
                current_identifiers=["P12345"],
                current_ontology_type="protein",
                action_params={"force_error": True, "error_type": "runtime"},
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context={}
            )
        
        with pytest.raises(ValueError, match="Forced value error"):
            await action.execute(
                current_identifiers=["P12345"],
                current_ontology_type="protein",
                action_params={"force_error": True, "error_type": "value"},
                source_endpoint=Mock(),
                target_endpoint=Mock(),
                context={}
            )
    
    @pytest.mark.asyncio
    async def test_context_conversion_error_handling(self):
        """Test error handling during context conversion."""
        
        class ContextErrorParams(BaseModel):
            test_param: str
            
        class ContextErrorResult(BaseModel):
            result: str
        
        class ContextErrorAction(TypedStrategyAction[ContextErrorParams, ContextErrorResult]):
            def get_params_model(self) -> Type[ContextErrorParams]:
                return ContextErrorParams
            
            def get_result_model(self) -> Type[ContextErrorResult]:
                return ContextErrorResult
            
            async def execute_typed(self, *args, **kwargs) -> ContextErrorResult:
                return ContextErrorResult(result="success")
        
        action = ContextErrorAction()
        
        # Test with malformed context that might cause conversion errors
        # The action should handle this gracefully
        malformed_context = {
            "provenance": [
                {"invalid": "structure"},  # Invalid provenance format
                None,  # Invalid provenance entry
            ],
            "step_results": "not_a_dict_or_list",  # Invalid step_results format
        }
        
        # Should not raise exception due to error handling in context conversion
        result = await action.execute(
            current_identifiers=["P12345"],
            current_ontology_type="protein",
            action_params={"test_param": "test"},
            source_endpoint=Mock(),
            target_endpoint=Mock(),
            context=malformed_context
        )
        
        # Should get a successful result despite malformed context
        assert result is not None
        assert "result" in result["details"]