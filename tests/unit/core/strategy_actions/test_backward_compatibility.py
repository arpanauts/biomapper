"""Tests for backward compatibility between dict-based and typed action interfaces."""

import pytest
from typing import Dict, Any, Optional, List, Type
from unittest.mock import MagicMock
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime

from biomapper.core.models import (
    ActionResult,
    Status,
    ProvenanceRecord,
)
from biomapper.core.models.execution_context import (
    StrategyExecutionContext,
)
from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.db.models import Endpoint


# Parameter models for typed actions
class MappingParams(BaseModel):
    """Typed parameters for mapping action."""

    entity_id: str
    source: str = "default_source"
    validate_strict: bool = False


class ValidationParams(BaseModel):
    """Typed parameters for validation action."""

    entity_ids: List[str]
    threshold: float = Field(0.8, ge=0.0, le=1.0)


# Mock legacy action using dict interface
class LegacyDictAction(BaseStrategyAction):
    """Legacy action that uses dict parameters."""

    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute with dict parameters."""
        # Simulate legacy behavior
        entity_id = action_params.get("entity_id") or (
            current_identifiers[0] if current_identifiers else None
        )
        source = action_params.get("source", "default_source")

        if not entity_id:
            raise ValueError("entity_id is required")

        return {
            "input_identifiers": current_identifiers,
            "output_identifiers": [f"{source}:{entity_id}"],
            "output_ontology_type": target_endpoint.entity_ontology_id
            if target_endpoint
            else current_ontology_type,
            "provenance": [
                {
                    "source": source,
                    "original_id": entity_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
            "details": {
                "confidence": 0.95,
                "metadata": {"source": source, "original_id": entity_id},
            },
        }


# Mock new typed action with wrapper
class TypedAction(BaseStrategyAction):
    """New action using typed interfaces with backward compatibility."""

    params_model: Type[BaseModel] = MappingParams

    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute with automatic parameter conversion."""
        # Convert dict params to typed if model is defined
        if hasattr(self, "params_model"):
            try:
                typed_params = self.params_model(**action_params)
            except ValidationError as e:
                raise ValueError(f"Invalid parameters: {e}")
        else:
            typed_params = action_params

        # Convert context to typed if needed
        if isinstance(context, dict) and not isinstance(
            context, StrategyExecutionContext
        ):
            typed_context = StrategyExecutionContext(
                initial_identifier=current_identifiers[0]
                if current_identifiers
                else "unknown",
                current_identifier=current_identifiers[0]
                if current_identifiers
                else "unknown",
                ontology_type=current_ontology_type or "protein",
            )
        else:
            typed_context = context

        # Execute with typed parameters
        result = await self.execute_typed(
            typed_params,
            typed_context,
            current_identifiers,
            current_ontology_type,
            source_endpoint,
            target_endpoint,
        )

        # Convert result back to dict if needed
        if isinstance(result, ActionResult):
            return {
                "input_identifiers": current_identifiers,
                "output_identifiers": result.metadata.get(
                    "output_identifiers",
                    [result.mapped_identifier] if result.mapped_identifier else [],
                ),
                "output_ontology_type": result.metadata.get(
                    "output_ontology_type", result.target_type
                ),
                "provenance": [result.provenance.model_dump()]
                if result.provenance
                else [],
                "details": {
                    **result.metadata,
                    "status": result.status.value,
                    "mapped_identifier": result.mapped_identifier,
                },
            }
        return result

    async def execute_typed(
        self,
        parameters: MappingParams,
        context: StrategyExecutionContext,
        current_identifiers: List[str],
        current_ontology_type: str,
        source_endpoint: Optional[Endpoint],
        target_endpoint: Optional[Endpoint],
    ) -> ActionResult:
        """Execute with typed parameters."""
        entity_id = parameters.entity_id or (
            current_identifiers[0] if current_identifiers else ""
        )

        return ActionResult(
            action_type="mapping",
            identifier=entity_id,
            source_type=current_ontology_type,
            target_type=target_endpoint.entity_ontology_id
            if target_endpoint
            else current_ontology_type,
            mapped_identifier=f"{parameters.source}:{entity_id}",
            status=Status.SUCCESS,
            provenance=ProvenanceRecord(
                source=parameters.source,
                timestamp=datetime.utcnow(),
                confidence_score=0.95,
                method="direct_mapping",
            ),
            metadata={
                "output_identifiers": [f"{parameters.source}:{entity_id}"],
                "output_ontology_type": target_endpoint.entity_ontology_id
                if target_endpoint
                else current_ontology_type,
                "confidence": 0.95,
                "source": parameters.source,
                "original_id": entity_id,
                "initial_id": context.initial_identifier,
            },
        )


# Mock hybrid action that can handle both
class HybridAction(BaseStrategyAction):
    """Action that accepts both dict and typed parameters."""

    params_model: Type[BaseModel] = ValidationParams

    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute with either interface."""
        # Try to convert to typed params
        try:
            if hasattr(self, "params_model"):
                typed_params = self.params_model(**action_params)
                entity_ids = typed_params.entity_ids
                threshold = typed_params.threshold
            else:
                entity_ids = action_params.get("entity_ids", current_identifiers)
                threshold = action_params.get("threshold", 0.8)
        except Exception:
            entity_ids = action_params.get("entity_ids", current_identifiers)
            threshold = action_params.get("threshold", 0.8)

        # Handle context
        if isinstance(context, dict):
            session_id = context.get("session_id", "unknown")
        else:
            session_id = (
                context.initial_identifier
            )  # Use initial_identifier as session proxy

        # Process and return result
        validated_ids = [id for id in entity_ids if len(id) > 3]  # Simple validation

        return {
            "input_identifiers": current_identifiers,
            "output_identifiers": validated_ids,
            "output_ontology_type": current_ontology_type,
            "provenance": [],
            "details": {
                "validated": len(validated_ids),
                "threshold": threshold,
                "session_id": session_id,
                "total_input": len(entity_ids),
            },
        }


class TestBackwardCompatibility:
    """Test backward compatibility wrapper functionality."""

    @pytest.fixture
    def mock_endpoint(self):
        """Create mock endpoint."""
        endpoint = MagicMock(spec=Endpoint)
        endpoint.entity_ontology_id = "protein"
        endpoint.base_url = "http://test.com"
        return endpoint

    @pytest.fixture
    def legacy_action(self):
        """Create legacy action instance."""
        return LegacyDictAction()

    @pytest.fixture
    def typed_action(self):
        """Create typed action instance."""
        return TypedAction()

    @pytest.fixture
    def hybrid_action(self):
        """Create hybrid action instance."""
        return HybridAction()

    @pytest.fixture
    def dict_context(self):
        """Create dict-based context."""
        return {
            "session_id": "test-session-123",
            "strategy_id": "test-strategy",
            "metadata": {"key": "value"},
        }

    @pytest.fixture
    def typed_context(self):
        """Create typed context."""
        return StrategyExecutionContext(
            initial_identifier="TEST123",
            current_identifier="TEST123",
            ontology_type="protein",
        )

    @pytest.mark.asyncio
    async def test_legacy_action_with_dict_params(
        self, legacy_action, dict_context, mock_endpoint
    ):
        """Test legacy action continues to work with dict parameters."""
        identifiers = ["P12345"]
        params = {"entity_id": "P12345", "source": "uniprot"}

        result = await legacy_action.execute(
            identifiers, "protein", params, mock_endpoint, mock_endpoint, dict_context
        )

        assert isinstance(result, dict)
        assert result["output_identifiers"] == ["uniprot:P12345"]
        assert result["details"]["confidence"] == 0.95
        assert result["details"]["metadata"]["source"] == "uniprot"

    @pytest.mark.asyncio
    async def test_typed_action_with_dict_params(
        self, typed_action, dict_context, mock_endpoint
    ):
        """Test typed action accepts dict parameters through wrapper."""
        identifiers = ["P12345"]
        params = {"entity_id": "P12345", "source": "uniprot", "validate_strict": True}

        result = await typed_action.execute(
            identifiers, "protein", params, mock_endpoint, mock_endpoint, dict_context
        )

        assert isinstance(result, dict)
        assert result["output_identifiers"] == ["uniprot:P12345"]
        assert "provenance" in result
        assert len(result["provenance"]) > 0

    @pytest.mark.asyncio
    async def test_context_dict_to_typed_conversion(self, typed_action):
        """Test context dict converts correctly to typed context."""
        dict_ctx = {
            "initial_identifier": "ID456",
            "current_identifier": "ID456",
            "ontology_type": "gene",
            "extra_field": "ignored",  # Should be ignored
        }

        # Test conversion in typed action
        typed_ctx = StrategyExecutionContext(
            initial_identifier=dict_ctx["initial_identifier"],
            current_identifier=dict_ctx["current_identifier"],
            ontology_type=dict_ctx["ontology_type"],
        )

        assert typed_ctx.initial_identifier == "ID456"
        assert typed_ctx.current_identifier == "ID456"
        assert typed_ctx.ontology_type == "gene"

    @pytest.mark.asyncio
    async def test_typed_result_to_dict_conversion(
        self, typed_action, typed_context, mock_endpoint
    ):
        """Test typed ActionResult converts back to dict for legacy compatibility."""
        identifiers = ["Q99999"]
        params = {"entity_id": "Q99999", "source": "custom"}

        result = await typed_action.execute(
            identifiers,
            "protein",
            params,
            mock_endpoint,
            mock_endpoint,
            typed_context.model_dump(),
        )

        assert isinstance(result, dict)
        assert "output_identifiers" in result
        assert result["output_identifiers"] == ["custom:Q99999"]
        assert "details" in result

    @pytest.mark.asyncio
    async def test_mixed_action_chain(
        self, legacy_action, typed_action, dict_context, mock_endpoint
    ):
        """Test mixed usage of legacy and typed actions in a chain."""
        # First action: legacy with dict
        identifiers1 = ["A12345"]
        params1 = {"entity_id": "A12345", "source": "source1"}
        result1 = await legacy_action.execute(
            identifiers1, "protein", params1, mock_endpoint, mock_endpoint, dict_context
        )

        # Pass result to typed action
        identifiers2 = result1["output_identifiers"]
        params2 = {
            "entity_id": result1["details"]["metadata"]["original_id"],
            "source": "source2",
        }

        result2 = await typed_action.execute(
            identifiers2,
            result1["output_ontology_type"],
            params2,
            mock_endpoint,
            mock_endpoint,
            dict_context,
        )

        assert result1["output_identifiers"] == ["source1:A12345"]
        assert result2["output_identifiers"] == ["source2:A12345"]

    @pytest.mark.asyncio
    async def test_hybrid_action_both_interfaces(self, hybrid_action, mock_endpoint):
        """Test hybrid action handles both dict and typed interfaces."""
        # Test with dict interface
        identifiers = ["P12345", "P23456", "P34567", "P45678", "P56789"]
        dict_params = {"entity_ids": identifiers, "threshold": 0.9}
        dict_ctx = {"session_id": "dict-session"}

        dict_result = await hybrid_action.execute(
            identifiers, "protein", dict_params, mock_endpoint, mock_endpoint, dict_ctx
        )

        assert isinstance(dict_result, dict)
        assert dict_result["details"]["validated"] == 5  # All IDs > 3 chars
        assert dict_result["details"]["threshold"] == 0.9

        # Test with invalid IDs
        short_ids = ["P1", "Q2", "R3"]  # Too short
        params2 = {"entity_ids": short_ids, "threshold": 0.7}

        result2 = await hybrid_action.execute(
            short_ids, "protein", params2, mock_endpoint, mock_endpoint, dict_ctx
        )

        assert result2["details"]["validated"] == 0
        assert result2["details"]["total_input"] == 3

    @pytest.mark.asyncio
    async def test_error_handling_invalid_dict_params(
        self, typed_action, dict_context, mock_endpoint
    ):
        """Test error handling when dict params don't match schema."""
        # Missing required field
        invalid_params = {"source": "uniprot"}  # Missing entity_id

        with pytest.raises(ValueError) as exc_info:
            await typed_action.execute(
                [],
                "protein",
                invalid_params,
                mock_endpoint,
                mock_endpoint,
                dict_context,
            )

        assert "entity_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_optional_fields_with_defaults(
        self, typed_action, typed_context, mock_endpoint
    ):
        """Test optional fields use defaults correctly."""
        # Only required field provided
        identifiers = ["MIN123"]
        minimal_params = {"entity_id": "MIN123"}

        result = await typed_action.execute(
            identifiers,
            "protein",
            minimal_params,
            mock_endpoint,
            mock_endpoint,
            typed_context.model_dump(),
        )

        assert result["output_identifiers"] == ["default_source:MIN123"]
        assert result["details"]["source"] == "default_source"

    @pytest.mark.asyncio
    async def test_complex_nested_params(self, mock_endpoint):
        """Test handling of complex nested parameters."""

        class ComplexParams(BaseModel):
            entity: Dict[str, Any]
            options: Dict[str, Any] = {}
            filters: List[Dict[str, Any]] = []

        class ComplexAction(BaseStrategyAction):
            params_model = ComplexParams

            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Endpoint,
                target_endpoint: Endpoint,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                # Convert params
                typed_params = self.params_model(**action_params)

                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": [typed_params.entity.get("id", "unknown")],
                    "output_ontology_type": typed_params.entity.get(
                        "type", current_ontology_type
                    ),
                    "provenance": [],
                    "details": {
                        "entity_type": typed_params.entity.get("type"),
                        "filter_count": len(typed_params.filters),
                        "has_options": bool(typed_params.options),
                    },
                }

        action = ComplexAction()

        # Complex dict params
        dict_params = {
            "entity": {"id": "E123", "type": "protein"},
            "options": {"include_metadata": True},
            "filters": [{"field": "score", "value": 0.8}],
        }

        result = await action.execute(
            ["E123"], "entity", dict_params, mock_endpoint, mock_endpoint, {}
        )

        assert result["details"]["entity_type"] == "protein"
        assert result["details"]["filter_count"] == 1
        assert result["details"]["has_options"] is True

    @pytest.mark.asyncio
    async def test_backward_compatible_wrapper(self, mock_endpoint):
        """Test a backward compatibility wrapper implementation."""

        class BackwardCompatibleAction(BaseStrategyAction):
            """Action with backward compatibility wrapper."""

            class Params(BaseModel):
                entity_id: str
                database: str = "uniprot"

            params_model = Params

            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Endpoint,
                target_endpoint: Endpoint,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                """Execute with automatic conversion."""
                # Convert dict to typed if needed
                if isinstance(action_params, dict):
                    parameters = self.params_model(**action_params)
                else:
                    parameters = action_params

                # Execute logic
                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": [
                        f"{parameters.database}:{parameters.entity_id}"
                    ],
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {"id": f"{parameters.database}:{parameters.entity_id}"},
                }

        action = BackwardCompatibleAction()

        # Test with dict
        result = await action.execute(
            ["P123"],
            "protein",
            {"entity_id": "P123", "database": "pdb"},
            mock_endpoint,
            mock_endpoint,
            {"session_id": "test"},
        )
        assert result["details"]["id"] == "pdb:P123"

        # Test with defaults
        result2 = await action.execute(
            ["P456"], "protein", {"entity_id": "P456"}, mock_endpoint, mock_endpoint, {}
        )
        assert result2["details"]["id"] == "uniprot:P456"

    @pytest.mark.asyncio
    async def test_type_coercion_in_params(self, mock_endpoint):
        """Test that parameter types are properly coerced during conversion."""

        class StrictParams(BaseModel):
            max_results: int = 10
            confidence_threshold: float = 0.8
            include_metadata: bool = True
            tags: List[str] = Field(default_factory=list)

        class StrictTypedAction(BaseStrategyAction):
            params_model = StrictParams

            async def execute(
                self,
                current_identifiers: List[str],
                current_ontology_type: str,
                action_params: Dict[str, Any],
                source_endpoint: Endpoint,
                target_endpoint: Endpoint,
                context: Dict[str, Any],
            ) -> Dict[str, Any]:
                params = self.params_model(**action_params)

                return {
                    "input_identifiers": current_identifiers,
                    "output_identifiers": current_identifiers[: params.max_results],
                    "output_ontology_type": current_ontology_type,
                    "provenance": [],
                    "details": {
                        "type_checks": {
                            "max_results_type": type(params.max_results).__name__,
                            "threshold_type": type(
                                params.confidence_threshold
                            ).__name__,
                            "include_type": type(params.include_metadata).__name__,
                            "tags_type": type(params.tags).__name__,
                        }
                    },
                }

        action = StrictTypedAction()

        # Dict with string values that should be converted
        dict_params = {
            "max_results": "20",  # Should convert to int
            "confidence_threshold": "0.95",  # Should convert to float
            "include_metadata": "true",  # Should convert to bool
            "tags": ["tag1", "tag2"],
        }

        result = await action.execute(
            ["ID1", "ID2", "ID3"],
            "entity",
            dict_params,
            mock_endpoint,
            mock_endpoint,
            {},
        )

        type_checks = result["details"]["type_checks"]
        assert type_checks["max_results_type"] == "int"
        assert type_checks["threshold_type"] == "float"
        assert type_checks["include_type"] == "bool"
        assert type_checks["tags_type"] == "list"


class TestActionRegistryCompatibility:
    """Test action registry with backward compatibility."""

    @pytest.mark.asyncio
    async def test_registry_with_mixed_actions(self):
        """Test action registry handles both legacy and typed actions."""
        # Create a mock registry
        mock_registry = {
            "legacy_map": LegacyDictAction,
            "typed_map": TypedAction,
            "hybrid_validate": HybridAction,
        }

        # Test instantiation of each action type
        for name, action_class in mock_registry.items():
            action = action_class()
            assert isinstance(action, BaseStrategyAction)
            assert hasattr(action, "execute")

            # Check if action has params_model for typed actions
            if name != "legacy_map":
                assert hasattr(action, "params_model")

    def test_action_discovery_backward_compat(self):
        """Test action discovery identifies both legacy and typed actions."""
        import inspect

        # Check legacy action
        assert inspect.iscoroutinefunction(LegacyDictAction.execute)
        params = inspect.signature(LegacyDictAction.execute).parameters
        assert "action_params" in params
        assert params["action_params"].annotation == Dict[str, Any]

        # Check typed action
        assert hasattr(TypedAction, "params_model")
        assert TypedAction.params_model == MappingParams

        # Check hybrid action
        assert hasattr(HybridAction, "params_model")
        assert HybridAction.params_model == ValidationParams

        # All should inherit from BaseStrategyAction
        assert issubclass(LegacyDictAction, BaseStrategyAction)
        assert issubclass(TypedAction, BaseStrategyAction)
        assert issubclass(HybridAction, BaseStrategyAction)

    def test_param_model_schema_generation(self):
        """Test that param models can generate JSON schema for documentation."""
        # Get schema from typed action param model
        schema = MappingParams.model_json_schema()

        assert "properties" in schema
        assert "entity_id" in schema["properties"]
        assert "source" in schema["properties"]
        assert schema["properties"]["source"]["default"] == "default_source"

        # Check validation params schema
        val_schema = ValidationParams.model_json_schema()
        assert "threshold" in val_schema["properties"]
        assert val_schema["properties"]["threshold"]["default"] == 0.8
        assert val_schema["properties"]["threshold"]["minimum"] == 0.0
        assert val_schema["properties"]["threshold"]["maximum"] == 1.0

