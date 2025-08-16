"""Integration tests for progressive wrapper with existing actions.

Tests the progressive wrapper system working with real biomapper actions
to ensure proper integration with the existing action framework.
"""

import pytest
import asyncio
import pandas as pd
from typing import Dict, Any
from unittest.mock import patch, MagicMock

from biomapper.core.strategy_actions.utils.progressive_wrapper import (
    ProgressiveWrapper,
    ProgressiveOrchestrator
)
from biomapper.core.strategy_actions.load_dataset_identifiers import LoadDatasetIdentifiersAction
from biomapper.core.strategy_actions.entities.proteins.annotation.extract_uniprot_from_xrefs import (
    ProteinExtractUniProtFromXrefsAction
)
from biomapper.core.standards.context_handler import UniversalContext


class TestProgressiveWrapperIntegration:
    """Integration tests for progressive wrapper with real actions."""
    
    @pytest.fixture
    def sample_protein_dataset(self, tmp_path):
        """Create a sample protein dataset file for testing."""
        data = {
            "protein_id": ["PROT_001", "PROT_002", "PROT_003", "PROT_004", "PROT_005"],
            "xrefs": [
                "UniProtKB:P12345|RefSeq:NP_001234",
                "UniProtKB:Q67890|KEGG:K12345",
                "RefSeq:NP_567890",  # No UniProt
                "UniProtKB:O00123|UniProtKB:P99999",  # Multiple UniProt
                "KEGG:K67890"  # No UniProt
            ],
            "gene_symbol": ["GEN1", "GEN2", "GEN3", "GEN4", "GEN5"]
        }
        
        df = pd.DataFrame(data)
        file_path = tmp_path / "sample_proteins.tsv"
        df.to_csv(file_path, sep="\t", index=False)
        
        return str(file_path)
    
    @pytest.fixture
    def integration_context(self):
        """Create integration test context."""
        return {
            "datasets": {},
            "statistics": {},
            "output_files": [],
            "current_identifiers": []
        }
    
    @pytest.mark.asyncio
    async def test_level_2_load_and_extract_progressive(
        self, 
        sample_protein_dataset, 
        integration_context
    ):
        """Test level 2: Progressive wrapper with load and extract actions."""
        
        # Stage 1: Load dataset
        load_action = LoadDatasetIdentifiersAction()
        load_params = {
            "file_path": sample_protein_dataset,
            "identifier_column": "protein_id",
            "output_key": "loaded_proteins"
        }
        
        wrapper1 = ProgressiveWrapper(1, "load_dataset", "File Loading")
        
        # Execute load stage
        load_result = await wrapper1.execute_stage(
            load_action, 
            load_params, 
            integration_context
        )
        
        # Verify load worked
        assert load_result["details"]["success"] is True
        assert "loaded_proteins" in integration_context["datasets"]
        loaded_df = integration_context["datasets"]["loaded_proteins"]
        assert len(loaded_df) == 5
        
        # Stage 2: Extract UniProt IDs
        extract_action = ProteinExtractUniProtFromXrefsAction()
        extract_params = {
            "input_key": "loaded_proteins",
            "xrefs_column": "xrefs",
            "output_key": "extracted_uniprot",
            "remove_isoforms": True
        }
        
        wrapper2 = ProgressiveWrapper(2, "extract_uniprot", "UniProt Extraction")
        
        # Use the same matched identifier tracking
        wrapper2._matched_identifiers = wrapper1._matched_identifiers.copy()
        
        # Execute extract stage
        extract_result = await wrapper2.execute_stage(
            extract_action,
            extract_params,
            integration_context
        )
        
        # Verify extraction worked
        assert extract_result["details"]["success"] is True
        assert "extracted_uniprot" in integration_context["datasets"]
        
        extracted_df = integration_context["datasets"]["extracted_uniprot"]
        assert len(extracted_df) > 0
        
        # Should have extracted UniProt IDs from xrefs
        assert "extracted_uniprot" in extracted_df.columns
        uniprot_ids = extracted_df["extracted_uniprot"].dropna()
        assert len(uniprot_ids) > 0
        
        # Verify progressive statistics
        assert "progressive_stats" in integration_context
        stats = integration_context["progressive_stats"]
        assert len(stats["stages"]) == 2
        
        # Stage 1 (load) stats
        stage1_stats = stats["stages"][1]
        assert stage1_stats["name"] == "load_dataset"
        assert stage1_stats["method"] == "File Loading"
        
        # Stage 2 (extract) stats
        stage2_stats = stats["stages"][2]
        assert stage2_stats["name"] == "extract_uniprot"
        assert stage2_stats["method"] == "UniProt Extraction"
    
    @pytest.mark.asyncio
    async def test_level_2_orchestrator_with_real_actions(
        self, 
        sample_protein_dataset, 
        integration_context
    ):
        """Test level 2: Progressive orchestrator with real actions."""
        
        orchestrator = ProgressiveOrchestrator()
        
        # Add load stage
        load_action = LoadDatasetIdentifiersAction()
        load_params = {
            "file_path": sample_protein_dataset,
            "identifier_column": "protein_id",
            "output_key": "loaded_proteins"
        }
        orchestrator.add_stage(1, "load_dataset", load_action, load_params, "File Loading")
        
        # Add extract stage
        extract_action = ProteinExtractUniProtFromXrefsAction()
        extract_params = {
            "input_key": "loaded_proteins",
            "xrefs_column": "xrefs",
            "output_key": "extracted_uniprot",
            "remove_isoforms": True
        }
        orchestrator.add_stage(2, "extract_uniprot", extract_action, extract_params, "UniProt Extraction")
        
        # Execute all stages
        result = await orchestrator.execute_all(integration_context)
        
        # Verify orchestrator results
        assert "stages" in result
        assert "final_context" in result
        assert len(result["stages"]) == 2
        
        # Both stages should have succeeded
        for stage_result in result["stages"]:
            assert "result" in stage_result
            assert "error" not in stage_result
        
        # Verify final context has progressive stats
        final_context = result["final_context"]
        assert "progressive_stats" in final_context
        
        stats = final_context["progressive_stats"]
        assert len(stats["stages"]) == 2
        assert "total_processed" in stats
        assert "final_match_rate" in stats
        assert "total_time" in stats
    
    @pytest.mark.asyncio
    async def test_level_3_progressive_filtering_with_real_data(
        self, 
        sample_protein_dataset, 
        integration_context
    ):
        """Test level 3: Progressive filtering with realistic protein data."""
        
        # First, load the dataset
        load_action = LoadDatasetIdentifiersAction()
        load_params = {
            "file_path": sample_protein_dataset,
            "identifier_column": "protein_id",
            "output_key": "loaded_proteins"
        }
        
        wrapper1 = ProgressiveWrapper(1, "load_dataset", "File Loading")
        await wrapper1.execute_stage(load_action, load_params, integration_context)
        
        # Get the loaded dataset to understand what we're working with
        loaded_df = integration_context["datasets"]["loaded_proteins"]
        original_identifiers = loaded_df["protein_id"].tolist()
        
        # Stage 2: Extract UniProt (this will "match" some identifiers)
        extract_action = ProteinExtractUniProtFromXrefsAction()
        extract_params = {
            "input_key": "loaded_proteins",
            "xrefs_column": "xrefs",
            "output_key": "extracted_uniprot",
            "identifiers": original_identifiers,  # Add for progressive tracking
            "remove_isoforms": True
        }
        
        wrapper2 = ProgressiveWrapper(2, "extract_uniprot", "UniProt Extraction")
        wrapper2._matched_identifiers = wrapper1._matched_identifiers.copy()
        
        extract_result = await wrapper2.execute_stage(
            extract_action,
            extract_params,
            integration_context
        )
        
        # Stage 3: Simulate another action that would work on remaining unmatched
        # This would be filtered to only unmatched identifiers
        from biomapper.core.strategy_actions.utils.data_processing.filter_dataset import FilterDatasetAction
        
        # Mock filter parameters that include all original identifiers
        filter_params = {
            "input_key": "loaded_proteins",
            "output_key": "filtered_proteins",
            "identifiers": original_identifiers,  # Original list
            "filter_column": "protein_id",
            "filter_operation": "isin",
            "filter_values": original_identifiers
        }
        
        filter_action = FilterDatasetAction()
        wrapper3 = ProgressiveWrapper(3, "filter_remaining", "Filtering")
        wrapper3._matched_identifiers = wrapper2._matched_identifiers.copy()
        
        # This should be filtered to only unmatched identifiers
        filter_result = await wrapper3.execute_stage(
            filter_action,
            filter_params,
            integration_context
        )
        
        # Verify progressive filtering worked
        assert "progressive_stats" in integration_context
        stats = integration_context["progressive_stats"]
        assert len(stats["stages"]) == 3
        
        # Each stage should have processed a subset of the original data
        for stage_num in [1, 2, 3]:
            stage_stats = stats["stages"][stage_num]
            assert "new_matches" in stage_stats
            assert "cumulative_matched" in stage_stats
            assert "time" in stage_stats
        
        # Final match rate should be between 0 and 1
        assert 0 <= stats["final_match_rate"] <= 1
    
    @pytest.mark.asyncio
    async def test_level_2_error_recovery_in_progression(
        self, 
        sample_protein_dataset, 
        integration_context
    ):
        """Test level 2: Error recovery and continuation in progressive stages."""
        
        orchestrator = ProgressiveOrchestrator()
        
        # Stage 1: Successful load
        load_action = LoadDatasetIdentifiersAction()
        load_params = {
            "file_path": sample_protein_dataset,
            "identifier_column": "protein_id",
            "output_key": "loaded_proteins"
        }
        orchestrator.add_stage(1, "load_dataset", load_action, load_params, "File Loading")
        
        # Stage 2: Failing action (invalid parameters)
        extract_action = ProteinExtractUniProtFromXrefsAction()
        bad_extract_params = {
            "input_key": "nonexistent_dataset",  # This will cause failure
            "xrefs_column": "xrefs",
            "output_key": "extracted_uniprot"
        }
        orchestrator.add_stage(2, "extract_uniprot_fail", extract_action, bad_extract_params, "Failing Extraction")
        
        # Stage 3: Should still execute despite stage 2 failure
        # Use a different action that can work with the loaded data
        from biomapper.core.strategy_actions.utils.data_processing.filter_dataset import FilterDatasetAction
        filter_action = FilterDatasetAction()
        filter_params = {
            "input_key": "loaded_proteins",
            "output_key": "filtered_proteins",
            "filter_column": "protein_id",
            "filter_operation": "isin",
            "filter_values": ["PROT_001", "PROT_002"]
        }
        orchestrator.add_stage(3, "filter_subset", filter_action, filter_params, "Subset Filtering")
        
        # Execute all stages
        result = await orchestrator.execute_all(integration_context)
        
        # Verify results
        assert len(result["stages"]) == 3
        
        # Stage 1: Success
        assert "result" in result["stages"][0]
        assert result["stages"][0]["stage_name"] == "load_dataset"
        
        # Stage 2: Failure
        assert "error" in result["stages"][1]
        assert result["stages"][1]["stage_name"] == "extract_uniprot_fail"
        
        # Stage 3: Success (despite stage 2 failure)
        assert "result" in result["stages"][2]
        assert result["stages"][2]["stage_name"] == "filter_subset"
        
        # Verify progressive stats still tracked what succeeded
        final_context = result["final_context"]
        assert "progressive_stats" in final_context
        
        stats = final_context["progressive_stats"]
        # Should have stats for at least the successful stages
        assert len(stats["stages"]) >= 2
    
    def test_level_1_context_compatibility(self):
        """Test level 1: Context compatibility with different context types."""
        wrapper = ProgressiveWrapper(1, "compatibility_test")
        
        # Test with standard dict context
        dict_context = {"test": "value"}
        ctx1 = UniversalContext.wrap(dict_context)
        wrapper._initialize_progressive_stats(ctx1)
        assert ctx1.has_key("progressive_stats")
        
        # Test with context that has datasets structure
        datasets_context = {
            "datasets": {"test_data": pd.DataFrame({"id": [1, 2, 3]})},
            "statistics": {},
            "output_files": []
        }
        ctx2 = UniversalContext.wrap(datasets_context)
        wrapper._initialize_progressive_stats(ctx2)
        assert ctx2.has_key("progressive_stats")
        assert ctx2.get_datasets() == datasets_context["datasets"]
    
    @pytest.mark.asyncio
    async def test_level_2_parameter_standardization(
        self, 
        sample_protein_dataset, 
        integration_context
    ):
        """Test level 2: Parameter name standardization compliance."""
        
        # Test that wrapper works with 2025 standardized parameter names
        load_action = LoadDatasetIdentifiersAction()
        
        # Use standardized parameter names
        standardized_params = {
            "file_path": sample_protein_dataset,  # Standard: file_path (not filepath)
            "identifier_column": "protein_id",    # Standard: identifier_column (not id_column)
            "output_key": "loaded_proteins"        # Standard: output_key (not output_dataset)
        }
        
        wrapper = ProgressiveWrapper(1, "standardized_test", "Standard Loading")
        
        result = await wrapper.execute_stage(
            load_action,
            standardized_params,
            integration_context
        )
        
        # Should work with standardized parameters
        assert result["details"]["success"] is True
        assert "loaded_proteins" in integration_context["datasets"]
        
        # Verify progressive stats use standard structure
        stats = integration_context["progressive_stats"]
        assert "stages" in stats
        assert "total_processed" in stats
        assert "final_match_rate" in stats
        assert "total_time" in stats
        
        stage_stats = stats["stages"][1]
        assert "name" in stage_stats
        assert "method" in stage_stats
        assert "new_matches" in stage_stats
        assert "cumulative_matched" in stage_stats
        assert "time" in stage_stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])