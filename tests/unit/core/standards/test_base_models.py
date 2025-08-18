"""Tests for base models standards component."""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch, Mock

from pydantic import Field, ValidationError
from src.core.standards.base_models import (
    FlexibleBaseModel,
    StrictBaseModel,
    ActionParamsBase,
    DatasetOperationParams,
    FileOperationParams,
    APIOperationParams
)


class TestFlexibleBaseModel:
    """Test FlexibleBaseModel functionality."""
    
    @pytest.fixture
    def sample_model_class(self):
        """Create a sample model class for testing."""
        class SampleModel(FlexibleBaseModel):
            required_field: str = Field(..., description="A required field")
            optional_field: Optional[str] = Field(None, description="An optional field")
            default_field: int = Field(42, description="A field with default value")
        
        return SampleModel
    
    @pytest.fixture
    def sample_biological_data(self):
        """Create sample biological data for testing."""
        return {
            "uniprot_ids": ["P12345", "Q9Y6R4", "O00533"],
            "hmdb_ids": ["HMDB0000001", "HMDB0123456"],
            "gene_symbols": ["TP53", "BRCA1", "CD4"],
            "invalid_ids": ["", None, "INVALID_FORMAT"]
        }

    def test_flexible_model_basic_functionality(self, sample_model_class):
        """Test basic FlexibleBaseModel functionality."""
        # Test with only required fields
        model = sample_model_class(required_field="test")
        assert model.required_field == "test"
        assert model.optional_field is None
        assert model.default_field == 42
        
        # Test with all fields
        model = sample_model_class(
            required_field="test",
            optional_field="optional",
            default_field=100
        )
        assert model.required_field == "test"
        assert model.optional_field == "optional"
        assert model.default_field == 100

    def test_flexible_model_extra_fields(self, sample_model_class):
        """Test FlexibleBaseModel handling of extra fields."""
        # Create model with extra fields
        model = sample_model_class(
            required_field="test",
            extra_field="extra_value",
            biological_ids=["P12345", "Q9Y6R4"],
            metadata={"source": "test", "version": "1.0"}
        )
        
        # Basic fields should work
        assert model.required_field == "test"
        
        # Extra fields should be accessible
        extra_fields = model.get_extra_fields()
        assert "extra_field" in extra_fields
        assert "biological_ids" in extra_fields
        assert "metadata" in extra_fields
        assert extra_fields["extra_field"] == "extra_value"
        assert extra_fields["biological_ids"] == ["P12345", "Q9Y6R4"]
        
        # Should detect extra fields exist
        assert model.has_extra_fields() is True

    def test_flexible_model_edge_cases(self, sample_model_class):
        """Test FlexibleBaseModel with edge cases."""
        # Test with empty extra fields
        model = sample_model_class(required_field="test")
        assert model.has_extra_fields() is False
        assert model.get_extra_fields() == {}
        
        # Test missing required field
        with pytest.raises(ValidationError):
            sample_model_class()
        
        # Test invalid field types
        with pytest.raises(ValidationError):
            sample_model_class(required_field=123)  # Should be string

    def test_to_dict_with_extras(self, sample_model_class):
        """Test exporting model data including extra fields."""
        model = sample_model_class(
            required_field="test",
            optional_field="optional",
            extra_field="extra",
            biological_data={"uniprot": ["P12345"]}
        )
        
        data_dict = model.to_dict_with_extras()
        
        # Should include all fields
        assert data_dict["required_field"] == "test"
        assert data_dict["optional_field"] == "optional"
        assert data_dict["extra_field"] == "extra"
        assert data_dict["biological_data"] == {"uniprot": ["P12345"]}

    def test_get_defined_fields(self, sample_model_class):
        """Test getting defined model fields."""
        model = sample_model_class(required_field="test")
        defined_fields = model.get_defined_fields()
        
        expected_fields = {"required_field", "optional_field", "default_field"}
        assert defined_fields == expected_fields

    def test_flexible_model_performance(self, sample_model_class):
        """Test FlexibleBaseModel performance with large datasets."""
        # Create large extra data
        large_extra_data = {f"field_{i}": f"value_{i}" for i in range(1000)}
        
        start_time = time.time()
        model = sample_model_class(
            required_field="test",
            **large_extra_data
        )
        creation_time = time.time() - start_time
        
        # Test accessing extra fields
        start_time = time.time()
        extra_fields = model.get_extra_fields()
        access_time = time.time() - start_time
        
        # Performance assertions
        assert creation_time < 0.1  # Model creation should be fast
        assert access_time < 0.05   # Field access should be fast
        assert len(extra_fields) == 1000

    def test_flexible_model_thread_safety(self, sample_model_class):
        """Test FlexibleBaseModel thread safety."""
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                model = sample_model_class(
                    required_field=f"test_{thread_id}",
                    thread_specific_field=f"thread_{thread_id}"
                )
                results.append({
                    "required": model.required_field,
                    "extra": model.get_extra_fields()
                })
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        
        # Verify each thread's data is separate
        for i, result in enumerate(results):
            assert f"test_{i}" in result["required"]
            assert f"thread_{i}" in result["extra"]["thread_specific_field"]


class TestStrictBaseModel:
    """Test StrictBaseModel functionality."""
    
    @pytest.fixture
    def strict_model_class(self):
        """Create a strict model class for testing."""
        class StrictModel(StrictBaseModel):
            required_field: str = Field(..., description="A required field")
            optional_field: Optional[int] = Field(None, description="An optional field")
        
        return StrictModel

    def test_strict_model_basic_functionality(self, strict_model_class):
        """Test basic StrictBaseModel functionality."""
        # Test with valid data
        model = strict_model_class(required_field="test", optional_field=42)
        assert model.required_field == "test"
        assert model.optional_field == 42

    def test_strict_model_forbids_extra_fields(self, strict_model_class):
        """Test that StrictBaseModel forbids extra fields."""
        # Should raise ValidationError for extra fields
        with pytest.raises(ValidationError) as exc_info:
            strict_model_class(
                required_field="test",
                extra_field="should_fail"
            )
        
        assert "extra_field" in str(exc_info.value)

    def test_strict_model_immutability(self, strict_model_class):
        """Test that StrictBaseModel is immutable after creation."""
        model = strict_model_class(required_field="test")
        
        # Should not be able to modify fields after creation
        with pytest.raises(ValidationError):
            model.required_field = "new_value"


class TestActionParamsBase:
    """Test ActionParamsBase functionality."""
    
    @pytest.fixture
    def action_params_class(self):
        """Create an action parameters class for testing."""
        class TestActionParams(ActionParamsBase):
            input_data: List[str] = Field(..., description="Input biological identifiers")
            threshold: float = Field(0.8, description="Matching threshold")
            
            def validate_params(self) -> bool:
                """Custom validation logic."""
                return 0.0 <= self.threshold <= 1.0
        
        return TestActionParams

    def test_action_params_basic_functionality(self, action_params_class):
        """Test basic ActionParamsBase functionality."""
        params = action_params_class(
            input_data=["P12345", "Q9Y6R4"],
            threshold=0.9
        )
        
        # Basic fields should work
        assert params.input_data == ["P12345", "Q9Y6R4"]
        assert params.threshold == 0.9
        
        # Default common fields should be set
        assert params.debug is False
        assert params.trace is False
        assert params.timeout is None
        assert params.continue_on_error is False
        assert params.retry_count == 0
        assert params.retry_delay == 1

    def test_action_params_common_fields(self, action_params_class):
        """Test ActionParamsBase common fields."""
        params = action_params_class(
            input_data=["P12345"],
            debug=True,
            trace=True,
            timeout=300,
            continue_on_error=True,
            retry_count=3,
            retry_delay=5
        )
        
        assert params.debug is True
        assert params.trace is True
        assert params.timeout == 300
        assert params.continue_on_error is True
        assert params.retry_count == 3
        assert params.retry_delay == 5

    def test_action_params_validation(self, action_params_class):
        """Test ActionParamsBase custom validation."""
        # Valid params
        params = action_params_class(input_data=["P12345"], threshold=0.8)
        assert params.validate_params() is True
        
        # Invalid params (threshold out of range)
        params = action_params_class(input_data=["P12345"], threshold=1.5)
        assert params.validate_params() is False

    def test_action_params_extra_fields_logging(self, action_params_class):
        """Test ActionParamsBase extra fields logging."""
        with patch('logging.getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            params = action_params_class(
                input_data=["P12345"],
                extra_biological_field="extra_value"
            )
            
            params.log_extra_fields()
            
            # Should log extra fields
            mock_log.debug.assert_called_once()
            call_args = mock_log.debug.call_args[0][0]
            assert "Extra fields provided" in call_args
            assert "extra_biological_field" in call_args

    def test_action_params_legacy_migration(self, action_params_class):
        """Test ActionParamsBase legacy parameter migration."""
        class MigratingActionParams(ActionParamsBase):
            new_field: str = Field(..., description="New field name")
            
            def migrate_legacy_params(self) -> Dict[str, Any]:
                """Handle legacy parameter names."""
                data = self.model_dump()
                # Example migration: old_field -> new_field
                extra = self.get_extra_fields()
                if "old_field" in extra:
                    data["new_field"] = extra["old_field"]
                return data
        
        params = MigratingActionParams(
            new_field="test",
            old_field="legacy_value"  # Extra field
        )
        
        migrated = params.migrate_legacy_params()
        assert migrated["new_field"] == "legacy_value"
        assert "old_field" in params.get_extra_fields()


class TestDatasetOperationParams:
    """Test DatasetOperationParams functionality."""
    
    def test_dataset_operation_basic_functionality(self):
        """Test basic DatasetOperationParams functionality."""
        params = DatasetOperationParams(
            input_key="source_proteins",
            output_key="processed_proteins"
        )
        
        assert params.input_key == "source_proteins"
        assert params.output_key == "processed_proteins"
        # Should inherit from ActionParamsBase
        assert hasattr(params, "debug")
        assert hasattr(params, "trace")

    def test_dataset_operation_validation(self):
        """Test DatasetOperationParams validation."""
        # Test with different keys (should pass validation)
        params = DatasetOperationParams(
            input_key="input",
            output_key="output"
        )
        assert params.validate_params() is True
        
        # Test with same keys (should warn but still pass)
        with patch('logging.getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            params = DatasetOperationParams(
                input_key="same_key",
                output_key="same_key"
            )
            result = params.validate_params()
            
            assert result is True  # Still passes validation
            # Should log warning
            mock_log.warning.assert_called_once()

    def test_dataset_operation_biological_patterns(self):
        """Test DatasetOperationParams with biological data patterns."""
        # Test with realistic biological dataset keys
        params = DatasetOperationParams(
            input_key="arivale_proteins",
            output_key="kg2c_mapped_proteins",
            debug=True,
            biological_context="protein_mapping"  # Extra field
        )
        
        assert params.input_key == "arivale_proteins"
        assert params.output_key == "kg2c_mapped_proteins"
        assert params.debug is True
        
        # Extra biological context should be preserved
        extra = params.get_extra_fields()
        assert extra["biological_context"] == "protein_mapping"


class TestFileOperationParams:
    """Test FileOperationParams functionality."""
    
    def test_file_operation_basic_functionality(self):
        """Test basic FileOperationParams functionality."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        params = FileOperationParams(
            file_path=tmp_path,
            create_dirs=True
        )
        
        assert params.file_path == tmp_path
        assert params.create_dirs is True
        
        # Clean up
        Path(tmp_path).unlink(missing_ok=True)

    def test_file_operation_path_validation(self):
        """Test FileOperationParams path validation."""
        # Test with valid existing file
        with tempfile.NamedTemporaryFile() as tmp_file:
            params = FileOperationParams(file_path=tmp_file.name)
            assert params.validate_file_path() is True
        
        # Test with non-existent path (should create parent dirs)
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "subdir" / "test_file.txt"
            params = FileOperationParams(
                file_path=str(test_path),
                create_dirs=True
            )
            
            assert params.validate_file_path() is True
            assert test_path.parent.exists()

    def test_file_operation_invalid_path(self):
        """Test FileOperationParams with invalid paths."""
        # Test with invalid path
        params = FileOperationParams(
            file_path="/invalid/\x00/path",  # Invalid characters
            create_dirs=False
        )
        
        with patch('logging.getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            result = params.validate_file_path()
            assert result is False
            mock_log.error.assert_called_once()

    def test_file_operation_biological_files(self):
        """Test FileOperationParams with biological file patterns."""
        # Test with typical biological data file paths
        biological_files = [
            "/data/proteins/arivale_proteomics.tsv",
            "/data/metabolites/hmdb_compounds.csv",
            "/results/mapping/protein_matches.xlsx"
        ]
        
        for file_path in biological_files:
            params = FileOperationParams(
                file_path=file_path,
                file_format="biological_data",  # Extra field
                compression="gzip"  # Extra field
            )
            
            assert params.file_path == file_path
            extra = params.get_extra_fields()
            assert extra["file_format"] == "biological_data"
            assert extra["compression"] == "gzip"


class TestAPIOperationParams:
    """Test APIOperationParams functionality."""
    
    def test_api_operation_basic_functionality(self):
        """Test basic APIOperationParams functionality."""
        params = APIOperationParams(
            api_url="https://api.uniprot.org/uniprot",
            api_key="test_key",
            max_retries=5,
            request_timeout=60
        )
        
        assert params.api_url == "https://api.uniprot.org/uniprot"
        assert params.api_key == "test_key"
        assert params.max_retries == 5
        assert params.request_timeout == 60
        assert params.rate_limit_delay == 0.1  # Default value

    def test_api_operation_validation(self):
        """Test APIOperationParams validation."""
        # Test with valid HTTPS URL
        params = APIOperationParams(api_url="https://api.example.com")
        assert params.validate_api_config() is True
        
        # Test with valid HTTP URL
        params = APIOperationParams(api_url="http://localhost:8000")
        assert params.validate_api_config() is True
        
        # Test with invalid URL
        params = APIOperationParams(api_url="ftp://invalid.com")
        
        with patch('logging.getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            result = params.validate_api_config()
            assert result is False
            mock_log.error.assert_called_once()

    def test_api_operation_biological_apis(self):
        """Test APIOperationParams with biological API patterns."""
        # Test with real biological API configurations
        biological_apis = [
            {
                "name": "uniprot",
                "url": "https://rest.uniprot.org/uniprotkb",
                "rate_limit": 0.1
            },
            {
                "name": "hmdb",
                "url": "https://hmdb.ca/metabolites",
                "rate_limit": 0.5
            },
            {
                "name": "chembl",
                "url": "https://www.ebi.ac.uk/chembl/api/data",
                "rate_limit": 0.2
            }
        ]
        
        for api_config in biological_apis:
            params = APIOperationParams(
                api_url=api_config["url"],
                rate_limit_delay=api_config["rate_limit"],
                api_name=api_config["name"],  # Extra field
                biological_domain="protein" if "uniprot" in api_config["name"] else "metabolite"  # Extra field
            )
            
            assert params.api_url == api_config["url"]
            assert params.rate_limit_delay == api_config["rate_limit"]
            assert params.validate_api_config() is True
            
            extra = params.get_extra_fields()
            assert extra["api_name"] == api_config["name"]
            assert extra["biological_domain"] in ["protein", "metabolite"]


class TestPerformanceBaseModels:
    """Performance tests for base models."""
    
    @pytest.mark.performance
    def test_large_model_creation_performance(self):
        """Test performance with large model creation."""
        class LargeModel(FlexibleBaseModel):
            required_field: str = Field(..., description="Required field")
        
        # Create model with many extra fields
        large_extra_data = {f"field_{i}": f"value_{i}" for i in range(10000)}
        
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        model = LargeModel(required_field="test", **large_extra_data)
        
        memory_after = self._get_memory_usage()
        execution_time = time.time() - start_time
        
        # Performance assertions
        assert execution_time < 1.0  # Should complete in reasonable time
        assert (memory_after - memory_before) < 100 * 1024 * 1024  # < 100MB memory increase
        assert len(model.get_extra_fields()) == 10000

    def test_model_serialization_performance(self):
        """Test model serialization performance."""
        class SerializationModel(FlexibleBaseModel):
            biological_data: List[str] = Field(..., description="Biological identifiers")
        
        # Create model with large biological dataset
        large_biological_data = [f"P{i:05d}" for i in range(50000)]  # 50k UniProt-like IDs
        
        model = SerializationModel(
            biological_data=large_biological_data,
            metadata={"source": "test", "count": len(large_biological_data)}
        )
        
        start_time = time.time()
        serialized = model.to_dict_with_extras()
        serialization_time = time.time() - start_time
        
        # Performance assertions
        assert serialization_time < 1.0  # Should serialize quickly
        assert len(serialized["biological_data"]) == 50000
        assert serialized["metadata"]["count"] == 50000

    def _get_memory_usage(self):
        """Get current memory usage."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return 0  # Skip memory check if psutil not available


class TestBiologicalDataPatterns:
    """Test with realistic biological data patterns."""
    
    @pytest.fixture
    def protein_analysis_params(self):
        """Protein analysis parameter model."""
        class ProteinAnalysisParams(ActionParamsBase):
            uniprot_ids: List[str] = Field(..., description="UniProt accession numbers")
            confidence_threshold: float = Field(0.8, description="Confidence threshold")
            include_isoforms: bool = Field(False, description="Include protein isoforms")
            
            def validate_params(self) -> bool:
                """Validate protein-specific parameters."""
                # Check UniProt ID format
                for uid in self.uniprot_ids:
                    if not self._is_valid_uniprot_id(uid):
                        return False
                return 0.0 <= self.confidence_threshold <= 1.0
            
            def _is_valid_uniprot_id(self, uid: str) -> bool:
                """Basic UniProt ID validation."""
                import re
                if not uid:
                    return False
                # More robust regex allowing alphanumeric characters after the initial letter
                return re.fullmatch(r"^[PQOA][A-Za-z0-9]{5,}$", uid) is not None
        
        return ProteinAnalysisParams

    @pytest.fixture
    def metabolite_analysis_params(self):
        """Metabolite analysis parameter model."""
        class MetaboliteAnalysisParams(ActionParamsBase):
            hmdb_ids: List[str] = Field(..., description="HMDB identifiers")
            search_tolerance: float = Field(0.01, description="Mass tolerance for search")
            include_pathways: bool = Field(True, description="Include pathway information")
            
            def validate_params(self) -> bool:
                """Validate metabolite-specific parameters."""
                # Check HMDB ID format
                for hid in self.hmdb_ids:
                    if not hid.startswith("HMDB"):
                        return False
                return self.search_tolerance > 0.0
        
        return MetaboliteAnalysisParams

    def test_protein_data_patterns(self, protein_analysis_params):
        """Test protein data handling patterns."""
        # Valid protein data
        params = protein_analysis_params(
            uniprot_ids=["P12345", "Q9Y6R4", "O00533"],
            confidence_threshold=0.9,
            include_isoforms=True,
            analysis_type="expression",  # Extra field
            organism="human"  # Extra field
        )
        
        assert params.validate_params() is True
        assert len(params.uniprot_ids) == 3
        assert params.confidence_threshold == 0.9
        assert params.include_isoforms is True
        
        # Check extra biological context
        extra = params.get_extra_fields()
        assert extra["analysis_type"] == "expression"
        assert extra["organism"] == "human"

    def test_metabolite_data_patterns(self, metabolite_analysis_params):
        """Test metabolite data handling patterns."""
        # Valid metabolite data
        params = metabolite_analysis_params(
            hmdb_ids=["HMDB0000001", "HMDB0000002", "HMDB0123456"],
            search_tolerance=0.005,
            include_pathways=True,
            mass_spectrometry_mode="positive",  # Extra field
            sample_type="plasma"  # Extra field
        )
        
        assert params.validate_params() is True
        assert len(params.hmdb_ids) == 3
        assert params.search_tolerance == 0.005
        assert params.include_pathways is True
        
        # Check extra biological context
        extra = params.get_extra_fields()
        assert extra["mass_spectrometry_mode"] == "positive"
        assert extra["sample_type"] == "plasma"

    def test_edge_case_biological_identifiers(self, protein_analysis_params):
        """Test handling of edge case biological identifiers."""
        # Test with problematic identifiers (Q6EMK4 case)
        edge_case_ids = ["Q6EMK4", "P12345", "INVALID", ""]
        
        params = protein_analysis_params(
            uniprot_ids=edge_case_ids,
            edge_case_handling="permissive"  # Extra field
        )
        
        # Should handle edge cases gracefully
        validation_result = params.validate_params()
        # Some IDs are invalid, so validation should fail
        assert validation_result is False
        
        # But model should still be created with extra context
        extra = params.get_extra_fields()
        assert extra["edge_case_handling"] == "permissive"

    def test_multi_omics_data_integration(self):
        """Test integration of multiple omics data types."""
        class MultiOmicsParams(FlexibleBaseModel):
            protein_ids: List[str] = Field(..., description="Protein identifiers")
            metabolite_ids: List[str] = Field(..., description="Metabolite identifiers")
            
        # Real-world multi-omics scenario
        params = MultiOmicsParams(
            protein_ids=["P53_HUMAN", "BRCA1_HUMAN"],
            metabolite_ids=["HMDB0000001", "HMDB0000002"],
            gene_expression_data={"TP53": 2.5, "BRCA1": 1.8},  # Extra field
            clinical_metadata={  # Extra field
                "patient_id": "PT001",
                "tissue_type": "breast",
                "disease_stage": "II"
            },
            analysis_pipeline="integrated_pathway_analysis"  # Extra field
        )
        
        assert len(params.protein_ids) == 2
        assert len(params.metabolite_ids) == 2
        
        # Multi-omics context should be preserved
        extra = params.get_extra_fields()
        assert "gene_expression_data" in extra
        assert "clinical_metadata" in extra
        assert extra["clinical_metadata"]["patient_id"] == "PT001"
        assert extra["analysis_pipeline"] == "integrated_pathway_analysis"