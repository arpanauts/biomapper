from datetime import datetime, timezone
from unittest.mock import patch

from biomapper.core.models.result_bundle import MappingResultBundle


class TestMappingResultBundle:
    """Test suite for MappingResultBundle class."""

    def test_initialization(self):
        """Test that MappingResultBundle initializes correctly with all properties."""
        strategy_name = "test_strategy"
        initial_identifiers = ["id1", "id2", "id3"]
        source_ontology = "ENSEMBL"
        target_ontology = "UNIPROT"
        
        # Mock the current time
        mock_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        with patch('biomapper.core.models.result_bundle.get_current_utc_time', return_value=mock_time):
            bundle = MappingResultBundle(
                strategy_name=strategy_name,
                initial_identifiers=initial_identifiers,
                source_ontology_type=source_ontology,
                target_ontology_type=target_ontology
            )
        
        # Assert all initial properties
        assert bundle.strategy_name == strategy_name
        assert bundle.initial_identifiers == initial_identifiers
        assert bundle.initial_identifiers is not initial_identifiers  # Ensure it's a copy
        assert bundle.source_ontology_type == source_ontology
        assert bundle.target_ontology_type == target_ontology
        
        # Current state
        assert bundle.current_identifiers == initial_identifiers
        assert bundle.current_identifiers is not initial_identifiers  # Ensure it's a copy
        assert bundle.current_ontology_type == source_ontology
        
        # Execution tracking
        assert bundle.start_time == mock_time
        assert bundle.end_time is None
        assert bundle.execution_status == "in_progress"
        assert bundle.error is None
        
        # Step tracking
        assert bundle.step_results == []
        assert bundle.provenance == []
        
        # Statistics
        assert bundle.total_steps == 0
        assert bundle.completed_steps == 0
        assert bundle.failed_steps == 0
    
    def test_add_step_result_success(self):
        """Test adding a successful step result updates all relevant properties."""
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=["id1", "id2"],
            source_ontology_type="ENSEMBL"
        )
        
        # Add a successful step
        step_id = "step_1"
        step_description = "Convert to UniProt"
        action_type = "convert"
        input_ids = ["id1", "id2"]
        output_ids = ["P12345", "Q67890"]
        output_ontology = "UNIPROT"
        details = {"converter": "ensembl_uniprot", "success_rate": 1.0}
        
        mock_time = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
        with patch('biomapper.core.models.result_bundle.get_current_utc_time', return_value=mock_time):
            bundle.add_step_result(
                step_id=step_id,
                step_description=step_description,
                action_type=action_type,
                input_identifiers=input_ids,
                output_identifiers=output_ids,
                status="success",
                details=details,
                output_ontology_type=output_ontology
            )
        
        # Assert step_results updated
        assert len(bundle.step_results) == 1
        step_result = bundle.step_results[0]
        assert step_result["step_id"] == step_id
        assert step_result["description"] == step_description
        assert step_result["action_type"] == action_type
        assert step_result["input_count"] == 2
        assert step_result["output_count"] == 2
        assert step_result["status"] == "success"
        assert step_result["details"] == details
        assert step_result["timestamp"] == mock_time
        assert step_result["error"] is None
        
        # Assert provenance updated
        assert len(bundle.provenance) == 1
        prov = bundle.provenance[0]
        assert prov["step_id"] == step_id
        assert prov["action_type"] == action_type
        assert prov["input_identifiers"] == input_ids
        assert prov["output_identifiers"] == output_ids
        assert prov["input_ontology_type"] == "ENSEMBL"
        assert prov["output_ontology_type"] == "UNIPROT"
        assert prov["resources_used"] == []
        assert prov["timestamp"] == mock_time
        
        # Assert current state updated
        assert bundle.current_identifiers == output_ids
        assert bundle.current_ontology_type == output_ontology
        
        # Assert statistics updated
        assert bundle.completed_steps == 1
        assert bundle.failed_steps == 0
    
    def test_add_step_result_failure(self):
        """Test adding a failed step result increments failed_steps."""
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=["id1", "id2"]
        )
        
        input_ids = ["id1", "id2"]
        error_msg = "Connection timeout"
        
        bundle.add_step_result(
            step_id="step_1",
            step_description="Failed conversion",
            action_type="convert",
            input_identifiers=input_ids,
            output_identifiers=[],  # No output on failure
            status="failed",
            details={"attempt": 1},
            error=error_msg
        )
        
        # Assert step recorded
        assert len(bundle.step_results) == 1
        assert bundle.step_results[0]["status"] == "failed"
        assert bundle.step_results[0]["error"] == error_msg
        
        # Assert current state unchanged on failure
        assert bundle.current_identifiers == []  # Updated to empty output
        assert bundle.current_ontology_type is None  # Unchanged
        
        # Assert statistics
        assert bundle.completed_steps == 0
        assert bundle.failed_steps == 1
    
    def test_add_step_result_with_sampling(self):
        """Test that large identifier lists are sampled in provenance."""
        # Create bundle with many identifiers
        large_id_list = [f"id_{i}" for i in range(100)]
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=large_id_list
        )
        
        # Add step with many output identifiers
        output_ids = [f"output_{i}" for i in range(50)]
        bundle.add_step_result(
            step_id="step_1",
            step_description="Large conversion",
            action_type="convert",
            input_identifiers=large_id_list,
            output_identifiers=output_ids,
            status="success",
            details={}
        )
        
        # Assert provenance only stores samples
        prov = bundle.provenance[0]
        assert len(prov["input_identifiers"]) == 10  # Only first 10
        assert len(prov["output_identifiers"]) == 10  # Only first 10
        assert prov["input_identifiers"] == [f"id_{i}" for i in range(10)]
        assert prov["output_identifiers"] == [f"output_{i}" for i in range(10)]
    
    def test_finalize_success(self):
        """Test finalizing with completed status sets properties correctly."""
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=["id1"]
        )
        
        mock_end_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        with patch('biomapper.core.models.result_bundle.get_current_utc_time', return_value=mock_end_time):
            bundle.finalize(status="completed")
        
        assert bundle.execution_status == "completed"
        assert bundle.end_time == mock_end_time
        assert bundle.error is None
    
    def test_finalize_failure(self):
        """Test finalizing with failed status and error message."""
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=["id1"]
        )
        
        error_msg = "Critical error occurred"
        mock_end_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        with patch('biomapper.core.models.result_bundle.get_current_utc_time', return_value=mock_end_time):
            bundle.finalize(status="failed", error=error_msg)
        
        assert bundle.execution_status == "failed"
        assert bundle.end_time == mock_end_time
        assert bundle.error == error_msg
    
    def test_to_dict_finalized(self):
        """Test to_dict method on a finalized result bundle with calculated duration."""
        # Set up times
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 12, 30, 45, tzinfo=timezone.utc)
        
        # Create and populate bundle
        with patch('biomapper.core.models.result_bundle.get_current_utc_time', return_value=start_time):
            bundle = MappingResultBundle(
                strategy_name="complex_strategy",
                initial_identifiers=["id1", "id2", "id3"],
                source_ontology_type="ENSEMBL",
                target_ontology_type="UNIPROT"
            )
        
        # Add some steps
        bundle.add_step_result(
            step_id="step_1",
            step_description="First step",
            action_type="convert",
            input_identifiers=["id1", "id2", "id3"],
            output_identifiers=["P1", "P2"],
            status="success",
            details={"method": "direct"},
            output_ontology_type="UNIPROT"
        )
        
        bundle.add_step_result(
            step_id="step_2",
            step_description="Second step",
            action_type="filter",
            input_identifiers=["P1", "P2"],
            output_identifiers=["P1"],
            status="success",
            details={"filter": "active_only"}
        )
        
        bundle.total_steps = 2
        
        # Finalize
        with patch('biomapper.core.models.result_bundle.get_current_utc_time', return_value=end_time):
            bundle.finalize(status="completed")
        
        # Convert to dict
        result_dict = bundle.to_dict()
        
        # Assert all expected keys and values
        assert result_dict["strategy_name"] == "complex_strategy"
        assert result_dict["execution_status"] == "completed"
        assert result_dict["error"] is None
        assert result_dict["initial_identifiers_count"] == 3
        assert result_dict["final_identifiers_count"] == 1
        assert result_dict["source_ontology_type"] == "ENSEMBL"
        assert result_dict["target_ontology_type"] == "UNIPROT"
        assert result_dict["current_ontology_type"] == "UNIPROT"
        assert result_dict["start_time"] == start_time.isoformat()
        assert result_dict["end_time"] == end_time.isoformat()
        assert result_dict["duration_seconds"] == 1845.0  # 30 minutes 45 seconds
        assert result_dict["total_steps"] == 2
        assert result_dict["completed_steps"] == 2
        assert result_dict["failed_steps"] == 0
        assert len(result_dict["step_results"]) == 2
        assert len(result_dict["provenance"]) == 2
        assert result_dict["final_identifiers"] == ["P1"]
    
    def test_to_dict_not_finalized(self):
        """Test to_dict when bundle is not finalized (no end_time or duration)."""
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=["id1"]
        )
        
        result_dict = bundle.to_dict()
        
        assert result_dict["execution_status"] == "in_progress"
        assert result_dict["end_time"] is None
        assert result_dict["duration_seconds"] is None
    
    def test_to_dict_with_many_final_identifiers(self):
        """Test that to_dict only includes first 100 final identifiers."""
        # Create bundle with many identifiers
        many_ids = [f"id_{i}" for i in range(200)]
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=["start"]
        )
        
        # Update current identifiers
        bundle.current_identifiers = many_ids
        
        result_dict = bundle.to_dict()
        
        # Should only include first 100
        assert len(result_dict["final_identifiers"]) == 100
        assert result_dict["final_identifiers"] == [f"id_{i}" for i in range(100)]
        assert result_dict["final_identifiers_count"] == 200  # But count is accurate
    
    def test_resources_used_in_provenance(self):
        """Test that resources_used from details is included in provenance."""
        bundle = MappingResultBundle(
            strategy_name="test",
            initial_identifiers=["id1"]
        )
        
        resources = ["database_1", "api_endpoint_2"]
        bundle.add_step_result(
            step_id="step_1",
            step_description="Step with resources",
            action_type="lookup",
            input_identifiers=["id1"],
            output_identifiers=["result1"],
            status="success",
            details={"resources_used": resources, "other_info": "value"}
        )
        
        prov = bundle.provenance[0]
        assert prov["resources_used"] == resources
    
    def test_multiple_step_tracking(self):
        """Test tracking multiple steps with mixed success/failure."""
        bundle = MappingResultBundle(
            strategy_name="multi_step",
            initial_identifiers=["id1", "id2"]
        )
        
        # Step 1: Success
        bundle.add_step_result(
            step_id="step_1",
            step_description="First conversion",
            action_type="convert",
            input_identifiers=["id1", "id2"],
            output_identifiers=["out1", "out2"],
            status="success",
            details={}
        )
        
        # Step 2: Error status (counts as failed)
        bundle.add_step_result(
            step_id="step_2",
            step_description="Failed lookup",
            action_type="lookup",
            input_identifiers=["out1", "out2"],
            output_identifiers=["out1"],  # Partial output
            status="error",
            details={},
            error="Service unavailable"
        )
        
        # Step 3: Not implemented (doesn't count as failed)
        bundle.add_step_result(
            step_id="step_3",
            step_description="Optional step",
            action_type="enrich",
            input_identifiers=["out1"],
            output_identifiers=["out1"],
            status="not_implemented",
            details={}
        )
        
        # Assert statistics
        assert bundle.completed_steps == 1
        assert bundle.failed_steps == 1  # Only error/failed status counts
        assert len(bundle.step_results) == 3
        assert len(bundle.provenance) == 3