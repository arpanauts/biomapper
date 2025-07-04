"""Tests for StrategyExecutionContext model."""

import pytest
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import ValidationError

from biomapper.core.models.execution_context import (
    StrategyExecutionContext,
    StepResult,
    ProvenanceRecord,
    ExecutionConfig,
    CacheConfig,
    BatchConfig
)


class TestStrategyExecutionContext:
    """Test StrategyExecutionContext model creation and validation."""
    
    def test_minimal_context_creation(self):
        """Test creating context with minimum required fields."""
        context = StrategyExecutionContext(
            initial_identifier="BRCA1",
            current_identifier="BRCA1",
            ontology_type="gene"
        )
        
        assert context.initial_identifier == "BRCA1"
        assert context.current_identifier == "BRCA1"
        assert context.ontology_type == "gene"
        assert context.step_results == {}
        assert context.provenance == []
        assert context.custom_action_data == {}
        assert context.config is not None
    
    def test_full_context_creation(self):
        """Test creating context with all fields specified."""
        step_results = {
            "normalize": StepResult(
                action="NormalizeAction",
                timestamp=datetime.now(),
                success=True,
                data={"normalized_id": "brca1"}
            ),
            "map": StepResult(
                action="MapAction",
                timestamp=datetime.now(),
                success=True,
                data={"mapped_id": "P38398"}
            )
        }
        
        provenance = [
            ProvenanceRecord(
                source="UniProt",
                timestamp=datetime.now(),
                action="protein_mapping",
                details={"version": "2024.01", "confidence": 0.99}
            )
        ]
        
        custom_data = {
            "user_metadata": {"project": "cancer_research"},
            "intermediate_results": {"species": "human"}
        }
        
        config = ExecutionConfig(
            cache=CacheConfig(enabled=True, ttl_seconds=3600),
            batch=BatchConfig(size=100, parallel=True),
            timeout_seconds=300,
            retry_attempts=3
        )
        
        context = StrategyExecutionContext(
            initial_identifier="BRCA1",
            current_identifier="P38398",
            ontology_type="protein",
            step_results=step_results,
            provenance=provenance,
            custom_action_data=custom_data,
            config=config
        )
        
        assert context.initial_identifier == "BRCA1"
        assert context.current_identifier == "P38398"
        assert context.ontology_type == "protein"
        assert len(context.step_results) == 2
        assert "normalize" in context.step_results
        assert "map" in context.step_results
        assert len(context.provenance) == 1
        assert context.provenance[0].source == "UniProt"
        assert context.custom_action_data["user_metadata"]["project"] == "cancer_research"
        assert context.config.cache.enabled is True
        assert context.config.batch.size == 100
    
    def test_invalid_ontology_type(self):
        """Test that invalid ontology type raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            StrategyExecutionContext(
                initial_identifier="test",
                current_identifier="test",
                ontology_type="invalid_type"  # Should be one of: gene, protein, metabolite, etc.
            )
        
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ontology_type",) for e in errors)
    
    def test_identifier_tracking(self):
        """Test identifier tracking through execution."""
        context = StrategyExecutionContext(
            initial_identifier="RS123456",
            current_identifier="RS123456",
            ontology_type="variant"
        )
        
        # Initial state
        assert context.initial_identifier == "RS123456"
        assert context.current_identifier == "RS123456"
        assert context.identifier_history == ["RS123456"]
        
        # Update current identifier
        context.current_identifier = "chr1:12345:A:G"
        assert context.current_identifier == "chr1:12345:A:G"
        assert context.initial_identifier == "RS123456"  # Should not change
        assert context.identifier_history == ["RS123456", "chr1:12345:A:G"]
        
        # Update again
        context.current_identifier = "ENSG00000139618"
        assert context.identifier_history == ["RS123456", "chr1:12345:A:G", "ENSG00000139618"]
    
    def test_step_results_accumulation(self):
        """Test accumulating step results during execution."""
        context = StrategyExecutionContext(
            initial_identifier="test-id",
            current_identifier="test-id",
            ontology_type="gene"
        )
        
        # Add first step result
        context.add_step_result("validation", {
            "valid": True,
            "format": "ensembl"
        })
        
        assert "validation" in context.step_results
        assert isinstance(context.step_results["validation"], StepResult)
        assert context.step_results["validation"].success is True
        assert context.step_results["validation"].data["valid"] is True
        
        # Add second step result with failure
        context.add_step_result("mapping", {
            "error": "Database timeout"
        }, success=False)
        
        assert "mapping" in context.step_results
        assert context.step_results["mapping"].success is False
        assert context.step_results["mapping"].data["error"] == "Database timeout"
        
        # Override existing step result
        context.add_step_result("validation", {
            "valid": False,
            "reason": "Invalid checksum"
        }, success=False)
        
        assert context.step_results["validation"].success is False
        assert context.step_results["validation"].data["reason"] == "Invalid checksum"
    
    def test_provenance_tracking(self):
        """Test provenance tracking throughout execution."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="metabolite"
        )
        
        # Add provenance records
        context.add_provenance({
            "source": "ChEBI",
            "action": "synonym_lookup",
            "details": {"matched_synonym": "aspirin"}
        })
        
        assert len(context.provenance) == 1
        assert isinstance(context.provenance[0], ProvenanceRecord)
        assert context.provenance[0].source == "ChEBI"
        assert context.provenance[0].action == "synonym_lookup"
        
        # Add another provenance record
        context.add_provenance({
            "source": "PubChem",
            "action": "structure_match",
            "details": {"similarity_score": 0.98}
        })
        
        assert len(context.provenance) == 2
        assert context.provenance[1].source == "PubChem"
        assert context.provenance[1].details["similarity_score"] == 0.98
        
        # Verify timestamps are set
        for record in context.provenance:
            assert isinstance(record.timestamp, datetime)
    
    def test_custom_action_data_storage(self):
        """Test storing and retrieving custom action data."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="gene"
        )
        
        # Store custom data
        context.set_action_data("species_filter", {"species": ["human", "mouse"]})
        context.set_action_data("confidence_threshold", 0.85)
        context.set_action_data("intermediate_mappings", {
            "uniprot": ["P12345", "Q67890"],
            "ensembl": ["ENSG00000001", "ENSG00000002"]
        })
        
        # Retrieve custom data
        assert context.get_action_data("species_filter") == {"species": ["human", "mouse"]}
        assert context.get_action_data("confidence_threshold") == 0.85
        assert len(context.get_action_data("intermediate_mappings")["uniprot"]) == 2
        
        # Get non-existent data with default
        assert context.get_action_data("missing_key", default="default_value") == "default_value"
        
        # Get non-existent data without default
        assert context.get_action_data("missing_key") is None
        
        # Update existing data
        context.set_action_data("confidence_threshold", 0.95)
        assert context.get_action_data("confidence_threshold") == 0.95
    
    def test_configuration_settings(self):
        """Test configuration settings in context."""
        # Test default configuration
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="protein"
        )
        
        assert context.config.cache.enabled is True  # Default
        assert context.config.cache.ttl_seconds == 86400  # Default 24 hours
        assert context.config.batch.size == 50  # Default
        assert context.config.batch.parallel is False  # Default
        assert context.config.timeout_seconds == 600  # Default 10 minutes
        assert context.config.retry_attempts == 3  # Default
        
        # Test custom configuration
        custom_config = ExecutionConfig(
            cache=CacheConfig(enabled=False),
            batch=BatchConfig(size=200, parallel=True),
            timeout_seconds=60,
            retry_attempts=5
        )
        
        context2 = StrategyExecutionContext(
            initial_identifier="test2",
            current_identifier="test2",
            ontology_type="metabolite",
            config=custom_config
        )
        
        assert context2.config.cache.enabled is False
        assert context2.config.batch.size == 200
        assert context2.config.batch.parallel is True
        assert context2.config.timeout_seconds == 60
        assert context2.config.retry_attempts == 5
    
    def test_context_copy_and_modification(self):
        """Test creating copies of context for parallel execution."""
        original = StrategyExecutionContext(
            initial_identifier="original",
            current_identifier="current",
            ontology_type="gene"
        )
        
        # Add some data
        original.add_step_result("step1", {"result": "value1"})
        original.add_provenance({"source": "test", "action": "copy_test"})
        original.set_action_data("key1", "value1")
        
        # Create a copy
        copy = original.model_copy(deep=True)
        
        # Verify copy has same data
        assert copy.initial_identifier == original.initial_identifier
        assert copy.current_identifier == original.current_identifier
        assert len(copy.step_results) == len(original.step_results)
        assert len(copy.provenance) == len(original.provenance)
        assert copy.get_action_data("key1") == "value1"
        
        # Modify copy
        copy.current_identifier = "modified"
        copy.add_step_result("step2", {"result": "value2"})
        copy.set_action_data("key2", "value2")
        
        # Verify original is unchanged
        assert original.current_identifier == "current"
        assert "step2" not in original.step_results
        assert original.get_action_data("key2") is None
    
    def test_context_serialization(self):
        """Test context serialization to/from dict."""
        context = StrategyExecutionContext(
            initial_identifier="test-serialize",
            current_identifier="test-current",
            ontology_type="protein"
        )
        
        # Add data
        context.add_step_result("action1", {"data": "test"})
        context.add_provenance({"source": "UniProt", "action": "lookup"})
        context.set_action_data("custom", {"nested": {"data": "value"}})
        
        # Serialize to dict
        context_dict = context.model_dump()
        
        assert isinstance(context_dict, dict)
        assert context_dict["initial_identifier"] == "test-serialize"
        assert context_dict["current_identifier"] == "test-current"
        assert "step_results" in context_dict
        assert "provenance" in context_dict
        assert "custom_action_data" in context_dict
        
        # Deserialize from dict
        restored = StrategyExecutionContext.model_validate(context_dict)
        
        assert restored.initial_identifier == context.initial_identifier
        assert restored.current_identifier == context.current_identifier
        assert len(restored.step_results) == len(context.step_results)
        assert len(restored.provenance) == len(context.provenance)
        assert restored.get_action_data("custom") == {"nested": {"data": "value"}}
    
    def test_execution_state_helpers(self):
        """Test helper methods for execution state."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="gene"
        )
        
        # Test execution success tracking
        assert context.is_successful() is True  # No failed steps
        
        context.add_step_result("step1", {"result": "ok"}, success=True)
        assert context.is_successful() is True
        
        context.add_step_result("step2", {"error": "failed"}, success=False)
        assert context.is_successful() is False
        
        # Test getting last step result
        last_step = context.get_last_step_result()
        assert last_step is not None
        assert last_step.action == "step2"
        assert last_step.success is False
        
        # Test getting step result by name
        step1_result = context.get_step_result("step1")
        assert step1_result is not None
        assert step1_result.success is True
        assert step1_result.data["result"] == "ok"
        
        # Test getting non-existent step
        assert context.get_step_result("non_existent") is None
        
        # Test execution summary
        summary = context.get_execution_summary()
        assert summary["initial_identifier"] == "test"
        assert summary["current_identifier"] == "test"
        assert summary["total_steps"] == 2
        assert summary["successful_steps"] == 1
        assert summary["failed_steps"] == 1
        assert summary["success_rate"] == 0.5


class TestStepResult:
    """Test StepResult model."""
    
    def test_step_result_creation(self):
        """Test creating StepResult instances."""
        result = StepResult(
            action="TestAction",
            timestamp=datetime.now(),
            success=True,
            data={"key": "value"},
            error=None
        )
        
        assert result.action == "TestAction"
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
    
    def test_step_result_with_error(self):
        """Test StepResult with error information."""
        error_time = datetime.now()
        result = StepResult(
            action="FailedAction",
            timestamp=error_time,
            success=False,
            data={},
            error="Connection timeout to database"
        )
        
        assert result.success is False
        assert result.error == "Connection timeout to database"
        assert result.timestamp == error_time
    
    def test_step_result_validation(self):
        """Test StepResult validation rules."""
        # Success with error should be invalid
        with pytest.raises(ValidationError):
            StepResult(
                action="InvalidAction",
                timestamp=datetime.now(),
                success=True,
                data={},
                error="This shouldn't be here"
            )
        
        # Missing action should be invalid
        with pytest.raises(ValidationError):
            StepResult(
                action="",  # Empty action
                timestamp=datetime.now(),
                success=True,
                data={}
            )


class TestProvenanceRecord:
    """Test ProvenanceRecord model."""
    
    def test_provenance_record_creation(self):
        """Test creating ProvenanceRecord instances."""
        record = ProvenanceRecord(
            source="UniProt",
            timestamp=datetime.now(),
            action="protein_mapping",
            details={
                "method": "exact_match",
                "confidence": 1.0,
                "version": "2024.01"
            }
        )
        
        assert record.source == "UniProt"
        assert record.action == "protein_mapping"
        assert record.details["confidence"] == 1.0
        assert isinstance(record.timestamp, datetime)
    
    def test_provenance_record_minimal(self):
        """Test ProvenanceRecord with minimal fields."""
        record = ProvenanceRecord(
            source="Manual",
            timestamp=datetime.now(),
            action="user_input"
        )
        
        assert record.source == "Manual"
        assert record.action == "user_input"
        assert record.details == {}  # Default empty dict
    
    def test_provenance_record_validation(self):
        """Test ProvenanceRecord validation."""
        # Empty source should be invalid
        with pytest.raises(ValidationError):
            ProvenanceRecord(
                source="",
                timestamp=datetime.now(),
                action="test"
            )
        
        # Empty action should be invalid
        with pytest.raises(ValidationError):
            ProvenanceRecord(
                source="Test",
                timestamp=datetime.now(),
                action=""
            )


class TestExecutionConfig:
    """Test ExecutionConfig and related models."""
    
    def test_cache_config(self):
        """Test CacheConfig model."""
        # Default cache config
        cache = CacheConfig()
        assert cache.enabled is True
        assert cache.ttl_seconds == 86400  # 24 hours
        
        # Custom cache config
        cache2 = CacheConfig(enabled=False, ttl_seconds=3600)
        assert cache2.enabled is False
        assert cache2.ttl_seconds == 3600
        
        # Invalid TTL should fail
        with pytest.raises(ValidationError):
            CacheConfig(ttl_seconds=-1)
    
    def test_batch_config(self):
        """Test BatchConfig model."""
        # Default batch config
        batch = BatchConfig()
        assert batch.size == 50
        assert batch.parallel is False
        
        # Custom batch config
        batch2 = BatchConfig(size=1000, parallel=True)
        assert batch2.size == 1000
        assert batch2.parallel is True
        
        # Invalid size should fail
        with pytest.raises(ValidationError):
            BatchConfig(size=0)
    
    def test_execution_config(self):
        """Test ExecutionConfig model."""
        # Default config
        config = ExecutionConfig()
        assert config.cache.enabled is True
        assert config.batch.size == 50
        assert config.timeout_seconds == 600
        assert config.retry_attempts == 3
        
        # Custom config
        config2 = ExecutionConfig(
            cache=CacheConfig(enabled=False),
            batch=BatchConfig(size=200, parallel=True),
            timeout_seconds=30,
            retry_attempts=5
        )
        
        assert config2.cache.enabled is False
        assert config2.batch.size == 200
        assert config2.timeout_seconds == 30
        assert config2.retry_attempts == 5
        
        # Invalid timeout should fail
        with pytest.raises(ValidationError):
            ExecutionConfig(timeout_seconds=0)
        
        # Invalid retry attempts should fail
        with pytest.raises(ValidationError):
            ExecutionConfig(retry_attempts=-1)