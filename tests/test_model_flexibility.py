"""Tests for Pydantic model flexibility and backward compatibility."""

import pytest
from typing import Dict, Any
import yaml
from pathlib import Path

# Import base models
from biomapper.core.standards import (
    FlexibleBaseModel,
    StrictBaseModel,
    ActionParamsBase,
    DatasetOperationParams,
    FileOperationParams,
    APIOperationParams,
)

# Import migrated models
from biomapper.core.strategy_actions.merge_with_uniprot_resolution import (
    MergeWithUniprotResolutionParams,
)
from biomapper.core.strategy_actions.export_dataset import ExportDatasetParams
from biomapper.core.strategy_actions.utils.data_processing.custom_transform import (
    CustomTransformParams,
    TransformOperation,
)


class TestFlexibleBaseModel:
    """Test the FlexibleBaseModel allows extra fields."""

    def test_accepts_extra_fields(self):
        """Test that FlexibleBaseModel accepts extra fields without error."""
        
        class TestModel(FlexibleBaseModel):
            required_field: str
            optional_field: int = 10
        
        # Should not raise validation error
        model = TestModel(
            required_field="test",
            extra_field="should not fail",
            another_extra=123
        )
        
        assert model.required_field == "test"
        assert model.optional_field == 10
        
        # Check extra fields are accessible
        extra = model.get_extra_fields()
        assert "extra_field" in extra
        assert extra["extra_field"] == "should not fail"
        assert "another_extra" in extra
        assert extra["another_extra"] == 123

    def test_has_extra_fields_method(self):
        """Test the has_extra_fields method."""
        
        class TestModel(FlexibleBaseModel):
            field1: str
        
        model_without_extra = TestModel(field1="value")
        assert not model_without_extra.has_extra_fields()
        
        model_with_extra = TestModel(field1="value", extra="data")
        assert model_with_extra.has_extra_fields()

    def test_to_dict_with_extras(self):
        """Test exporting model with extra fields."""
        
        class TestModel(FlexibleBaseModel):
            normal_field: str
        
        model = TestModel(normal_field="value", extra_field="extra")
        full_dict = model.to_dict_with_extras()
        
        assert "normal_field" in full_dict
        assert "extra_field" in full_dict
        assert full_dict["extra_field"] == "extra"


class TestStrictBaseModel:
    """Test that StrictBaseModel rejects extra fields."""

    def test_rejects_extra_fields(self):
        """Test that StrictBaseModel forbids extra fields."""
        
        class TestModel(StrictBaseModel):
            required_field: str
        
        # Should work without extra fields
        model = TestModel(required_field="test")
        assert model.required_field == "test"
        
        # Should raise validation error with extra fields
        with pytest.raises(ValueError) as exc_info:
            TestModel(required_field="test", extra_field="should fail")
        assert "extra" in str(exc_info.value).lower()


class TestActionParamsBase:
    """Test the ActionParamsBase with common action fields."""

    def test_includes_common_fields(self):
        """Test that ActionParamsBase includes debug, trace, timeout, etc."""
        
        class TestAction(ActionParamsBase):
            my_field: str
        
        # Should have default values for common fields
        action = TestAction(my_field="test")
        assert action.my_field == "test"
        assert action.debug is False
        assert action.trace is False
        assert action.timeout is None
        assert action.continue_on_error is False
        assert action.retry_count == 0
        assert action.retry_delay == 1

    def test_accepts_common_fields(self):
        """Test that common fields can be set."""
        
        class TestAction(ActionParamsBase):
            my_field: str
        
        action = TestAction(
            my_field="test",
            debug=True,
            trace=True,
            timeout=30,
            continue_on_error=True,
            retry_count=3,
            retry_delay=2
        )
        
        assert action.debug is True
        assert action.trace is True
        assert action.timeout == 30
        assert action.continue_on_error is True
        assert action.retry_count == 3
        assert action.retry_delay == 2

    def test_accepts_extra_fields(self):
        """Test that ActionParamsBase accepts extra fields."""
        
        class TestAction(ActionParamsBase):
            my_field: str
        
        action = TestAction(
            my_field="test",
            legacy_param="old_value",
            future_param="new_feature"
        )
        
        extra = action.get_extra_fields()
        assert "legacy_param" in extra
        assert "future_param" in extra


class TestMigratedModels:
    """Test that migrated models work correctly with extra fields."""

    def test_merge_with_uniprot_params(self):
        """Test MergeWithUniprotResolutionParams accepts extra fields."""
        params = MergeWithUniprotResolutionParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_id_column="id",
            target_id_column="id",
            output_key="output",
            # Extra fields that might come from YAML
            extra_debug_flag=True,
            legacy_parameter="old_value",
            future_feature="not_yet_implemented"
        )
        
        assert params.source_dataset_key == "source"
        assert params.has_extra_fields()
        
        extra = params.get_extra_fields()
        assert "extra_debug_flag" in extra
        assert "legacy_parameter" in extra
        assert "future_feature" in extra

    def test_export_dataset_params(self):
        """Test ExportDatasetParams accepts extra fields."""
        params = ExportDatasetParams(
            input_key="data",
            output_path="/tmp/output.tsv",
            format="tsv",
            # Common fields from ActionParamsBase
            debug=True,
            # Extra fields
            compression="gzip",
            encoding="utf-8-sig"
        )
        
        assert params.input_key == "data"
        assert params.debug is True
        
        extra = params.get_extra_fields()
        assert "compression" in extra
        assert "encoding" in extra

    def test_custom_transform_params(self):
        """Test CustomTransformParams with complex nested structures."""
        transform_op = TransformOperation(
            type="column_rename",
            params={"old_name": "col1", "new_name": "col2"},
            # Extra field in nested model
            priority="high"
        )
        
        params = CustomTransformParams(
            input_key="input",
            output_key="output",
            transformations=[transform_op],
            # Extra fields
            parallel_processing=True,
            cache_results=False
        )
        
        assert params.input_key == "input"
        assert len(params.transformations) == 1
        
        # Check that nested model also accepts extra fields
        assert transform_op.get_extra_fields().get("priority") == "high"
        
        # Check parent model extra fields
        extra = params.get_extra_fields()
        assert "parallel_processing" in extra
        assert "cache_results" in extra


class TestBackwardCompatibility:
    """Test backward compatibility with existing YAML strategies."""

    def test_yaml_with_extra_parameters(self):
        """Test that models can be created from YAML with extra parameters."""
        yaml_config = """
        source_dataset_key: proteins_v1
        target_dataset_key: proteins_v2
        source_id_column: uniprot_id
        target_id_column: accession
        output_key: merged_proteins
        # These extra fields should not cause failure
        debug: true
        verbose: true
        legacy_mode: false
        experimental_feature: enabled
        api_retry_attempts: 5
        """
        
        config_dict = yaml.safe_load(yaml_config)
        
        # Should not raise validation error
        params = MergeWithUniprotResolutionParams(**config_dict)
        
        assert params.source_dataset_key == "proteins_v1"
        assert params.debug is True  # From ActionParamsBase
        
        extra = params.get_extra_fields()
        assert "verbose" in extra
        assert "legacy_mode" in extra
        assert "experimental_feature" in extra
        assert "api_retry_attempts" in extra

    def test_parameter_evolution(self):
        """Test that models can handle parameter name changes over time."""
        
        class EvolvingParams(ActionParamsBase):
            current_name: str
            
            def migrate_legacy_params(self):
                """Handle old parameter names."""
                extra = self.get_extra_fields()
                if "old_name" in extra and not hasattr(self, "current_name"):
                    self.current_name = extra["old_name"]
                return self.model_dump()
        
        # Old YAML might have old_name instead of current_name
        old_config = {"old_name": "value", "debug": True}
        params = EvolvingParams(current_name="default", **old_config)
        
        # Should handle the old parameter
        migrated = params.migrate_legacy_params()
        assert params.current_name == "default"  # Uses provided value
        assert params.get_extra_fields()["old_name"] == "value"


class TestDatasetOperationParams:
    """Test the DatasetOperationParams base class."""

    def test_includes_input_output_keys(self):
        """Test that DatasetOperationParams includes input/output keys."""
        
        class TestOperation(DatasetOperationParams):
            additional_field: str = "default"
        
        op = TestOperation(
            input_key="input",
            output_key="output"
        )
        
        assert op.input_key == "input"
        assert op.output_key == "output"
        assert op.additional_field == "default"
        
        # Should also have ActionParamsBase fields
        assert op.debug is False
        assert op.trace is False


class TestFileOperationParams:
    """Test the FileOperationParams base class."""

    def test_includes_file_path(self):
        """Test that FileOperationParams includes file_path and create_dirs."""
        
        class TestFileOp(FileOperationParams):
            encoding: str = "utf-8"
        
        op = TestFileOp(
            file_path="/tmp/test.txt",
            encoding="latin-1"
        )
        
        assert op.file_path == "/tmp/test.txt"
        assert op.create_dirs is True  # Default value
        assert op.encoding == "latin-1"


class TestAPIOperationParams:
    """Test the APIOperationParams base class."""

    def test_includes_api_fields(self):
        """Test that APIOperationParams includes API-related fields."""
        
        class TestAPICall(APIOperationParams):
            endpoint: str
        
        api_call = TestAPICall(
            endpoint="/api/v1/data",
            api_url="https://api.example.com",
            api_key="secret",
            max_retries=5,
            request_timeout=60
        )
        
        assert api_call.endpoint == "/api/v1/data"
        assert api_call.api_url == "https://api.example.com"
        assert api_call.api_key == "secret"
        assert api_call.max_retries == 5
        assert api_call.request_timeout == 60
        assert api_call.rate_limit_delay == 0.1  # Default


class TestRealWorldScenarios:
    """Test real-world scenarios that have caused issues."""

    def test_strategy_with_mixed_parameters(self):
        """Test a strategy configuration with mixed known and unknown parameters."""
        strategy_params = {
            # Known parameters
            "input_key": "metabolites",
            "output_path": "/data/output.tsv",
            "format": "csv",
            # Common parameters
            "debug": True,
            "timeout": 120,
            # Unknown/future parameters
            "experimental_mode": True,
            "performance_profile": "high",
            "custom_validator": "strict",
            "metadata": {
                "author": "test",
                "version": "1.0"
            }
        }
        
        # Should not fail with mixed parameters
        params = ExportDatasetParams(**strategy_params)
        
        assert params.input_key == "metabolites"
        assert params.debug is True
        assert params.timeout == 120
        
        extra = params.get_extra_fields()
        assert "experimental_mode" in extra
        assert "performance_profile" in extra
        assert "metadata" in extra

    def test_nested_model_flexibility(self):
        """Test that nested models also handle extra fields correctly."""
        transform_config = {
            "type": "column_transform",
            "params": {"expression": "x * 2"},
            # Extra fields in nested model
            "description": "Double the values",
            "author": "data_team",
            "validated": True
        }
        
        # Nested model should accept extra fields
        transform = TransformOperation(**transform_config)
        extra = transform.get_extra_fields()
        assert "description" in extra
        assert "author" in extra
        assert "validated" in extra
        
        # Parent model with nested flexible model
        params = CustomTransformParams(
            input_key="data",
            output_key="transformed",
            transformations=[transform],
            # Extra fields at parent level
            job_id="job_123",
            priority="high"
        )
        
        assert len(params.transformations) == 1
        parent_extra = params.get_extra_fields()
        assert "job_id" in parent_extra
        assert "priority" in parent_extra


if __name__ == "__main__":
    pytest.main([__file__, "-v"])