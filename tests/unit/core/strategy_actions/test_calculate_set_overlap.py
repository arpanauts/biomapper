"""Tests for CALCULATE_SET_OVERLAP action."""

import pytest
import tempfile
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from pathlib import Path
import pandas as pd

from biomapper.core.strategy_actions.typed_base import StandardActionResult
from biomapper.core.models.execution_context import StrategyExecutionContext
from biomapper.core.strategy_actions.calculate_set_overlap import (
    CalculateSetOverlapParams,
    CalculateSetOverlapAction,
)


class TestCalculateSetOverlapParams:
    """Test parameter validation for CALCULATE_SET_OVERLAP."""

    def test_valid_params(self):
        """Test that valid parameters are accepted."""
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats"
        )
        assert params.input_key == "merged_data"
        assert params.source_name == "UKBB"
        assert params.target_name == "HPA"
        assert params.mapping_combo_id == "UKBB_HPA"
        assert params.output_key == "overlap_stats"
        assert params.confidence_threshold == 0.8  # default
        assert params.output_dir == "results"  # default

    def test_missing_required_params(self):
        """Test that missing required parameters raise ValidationError."""
        # Missing input_key
        with pytest.raises(ValidationError) as exc_info:
            CalculateSetOverlapParams(
                source_name="UKBB",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats"
            )
        assert "input_key" in str(exc_info.value)

        # Missing source_name
        with pytest.raises(ValidationError) as exc_info:
            CalculateSetOverlapParams(
                input_key="merged_data",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats"
            )
        assert "source_name" in str(exc_info.value)

        # Missing target_name
        with pytest.raises(ValidationError) as exc_info:
            CalculateSetOverlapParams(
                input_key="merged_data",
                source_name="UKBB",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats"
            )
        assert "target_name" in str(exc_info.value)

        # Missing mapping_combo_id
        with pytest.raises(ValidationError) as exc_info:
            CalculateSetOverlapParams(
                input_key="merged_data",
                source_name="UKBB",
                target_name="HPA",
                output_key="overlap_stats"
            )
        assert "mapping_combo_id" in str(exc_info.value)

        # Missing output_key
        with pytest.raises(ValidationError) as exc_info:
            CalculateSetOverlapParams(
                input_key="merged_data",
                source_name="UKBB",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA"
            )
        assert "output_key" in str(exc_info.value)

    def test_optional_params(self):
        """Test optional parameters."""
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            confidence_threshold=0.9,
            output_dir="custom_results"
        )
        assert params.confidence_threshold == 0.9
        assert params.output_dir == "custom_results"

    def test_confidence_threshold_validation(self):
        """Test confidence threshold validation."""
        # Valid threshold (0.0 - 1.0)
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            confidence_threshold=0.5
        )
        assert params.confidence_threshold == 0.5

        # Invalid threshold (negative)
        with pytest.raises(ValidationError):
            CalculateSetOverlapParams(
                input_key="merged_data",
                source_name="UKBB",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats",
                confidence_threshold=-0.1
            )

        # Invalid threshold (> 1.0)
        with pytest.raises(ValidationError):
            CalculateSetOverlapParams(
                input_key="merged_data",
                source_name="UKBB",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats",
                confidence_threshold=1.1
            )


class TestCalculateSetOverlapAction:
    """Test CALCULATE_SET_OVERLAP action implementation."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return CalculateSetOverlapAction()

    def _create_context(self, datasets=None):
        """Create a test StrategyExecutionContext."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="protein",
            step_results={},
            provenance=[],
            custom_action_data={},
        )
        # Initialize datasets and metadata
        if datasets:
            context.set_action_data("datasets", datasets)
        else:
            context.set_action_data("datasets", {})
        context.set_action_data("metadata", {})
        context.set_action_data("statistics", {})
        context.set_action_data("output_files", {})
        return context

    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoints."""
        source = MagicMock()
        target = MagicMock()
        return source, target

    @pytest.fixture
    def sample_merged_data(self):
        """Create sample merged dataset from MERGE_WITH_UNIPROT_RESOLUTION."""
        return [
            # Matched rows
            {
                "UniProt": "P12345", "Assay": "Test1", "Panel": "Panel1",
                "uniprot": "P12345", "gene": "GENE1", "organ": "liver",
                "match_value": "P12345", "match_type": "direct", "match_confidence": 1.0,
                "match_status": "matched", "api_resolved": False
            },
            {
                "UniProt": "Q14213_Q8NEV9", "Assay": "Test2", "Panel": "Panel1",
                "uniprot": "Q14213", "gene": "GENE2", "organ": "brain",
                "match_value": "Q14213", "match_type": "composite", "match_confidence": 1.0,
                "match_status": "matched", "api_resolved": False
            },
            {
                "UniProt": "OLD123", "Assay": "Test3", "Panel": "Panel2",
                "uniprot": "NEW123", "gene": "GENE3", "organ": "heart",
                "match_value": "OLD123->NEW123", "match_type": "historical", "match_confidence": 0.9,
                "match_status": "matched", "api_resolved": True
            },
            # Source only rows
            {
                "UniProt": "P99999", "Assay": "Test4", "Panel": "Panel2",
                "uniprot": None, "gene": None, "organ": None,
                "match_value": None, "match_type": None, "match_confidence": 0.0,
                "match_status": "source_only", "api_resolved": False
            },
            # Target only rows
            {
                "UniProt": None, "Assay": None, "Panel": None,
                "uniprot": "P88888", "gene": "GENE4", "organ": "kidney",
                "match_value": None, "match_type": None, "match_confidence": 0.0,
                "match_status": "target_only", "api_resolved": False
            }
        ]

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield tmp_dir

    # Parameter validation tests
    @pytest.mark.asyncio
    async def test_params_validation(self, action, mock_endpoints):
        """Test parameter validation."""
        # Valid parameters
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats"
        )
        assert params.input_key == "merged_data"
        assert params.source_name == "UKBB"
        assert params.target_name == "HPA"
        assert params.mapping_combo_id == "UKBB_HPA"
        assert params.output_key == "overlap_stats"

        # Missing required parameters
        with pytest.raises(ValidationError):
            CalculateSetOverlapParams()

    # Basic statistics calculation tests
    @pytest.mark.asyncio
    async def test_basic_statistics(self, action, mock_endpoints, sample_merged_data, temp_output_dir):
        """Test basic overlap statistics calculation."""
        datasets = {"merged_data": sample_merged_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        result = await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        assert isinstance(result, StandardActionResult)
        
        # Check statistics were calculated correctly
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        assert stats["total_rows"] == 5
        assert stats["matched_rows"] == 3
        assert stats["source_only_rows"] == 1
        assert stats["target_only_rows"] == 1
        assert stats["direct_matches"] == 1
        assert stats["composite_matches"] == 1
        assert stats["historical_matches"] == 1
        
        # Check calculated rates and indices
        assert stats["source_match_rate"] == 3/4  # 3 matches out of 4 source rows
        assert stats["target_match_rate"] == 3/4  # 3 matches out of 4 target rows  
        assert stats["jaccard_index"] == 3/5  # 3 matches out of 5 total unique
        assert stats["dice_coefficient"] == (2 * 3) / (4 + 4)  # 2*matches / (source+target)

    @pytest.mark.asyncio
    async def test_match_type_breakdown(self, action, mock_endpoints, sample_merged_data, temp_output_dir):
        """Test match type statistics."""
        datasets = {"merged_data": sample_merged_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        
        # Verify match type breakdown
        assert stats["direct_matches"] == 1
        assert stats["composite_matches"] == 1
        assert stats["historical_matches"] == 1

    @pytest.mark.asyncio
    async def test_confidence_thresholds(self, action, mock_endpoints, sample_merged_data, temp_output_dir):
        """Test high confidence filtering."""
        datasets = {"merged_data": sample_merged_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            confidence_threshold=0.95,  # High threshold
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        
        # Only direct and composite matches should be high confidence (1.0)
        # Historical match has 0.9 confidence, below threshold
        assert stats["high_confidence_matches"] == 2
        assert stats["confidence_threshold"] == 0.95

    # Output file generation tests
    @pytest.mark.asyncio
    async def test_output_files_created(self, action, mock_endpoints, sample_merged_data, temp_output_dir):
        """Test that all 5 output files are created."""
        datasets = {"merged_data": sample_merged_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        # Check that output directory was created
        output_path = Path(temp_output_dir) / "UKBB_HPA"
        assert output_path.exists()
        assert output_path.is_dir()
        
        # Check that all 5 files were created
        expected_files = [
            "overlap_statistics.csv",
            "match_type_breakdown.csv",
            "venn_diagram.svg",
            "venn_diagram.png",
            "merged_dataset.csv"
        ]
        
        for filename in expected_files:
            file_path = output_path / filename
            assert file_path.exists(), f"File {filename} was not created"
            assert file_path.stat().st_size > 0, f"File {filename} is empty"

    @pytest.mark.asyncio
    async def test_statistics_csv_format(self, action, mock_endpoints, sample_merged_data, temp_output_dir):
        """Test statistics CSV has correct columns."""
        datasets = {"merged_data": sample_merged_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        # Read the statistics CSV file
        stats_file = Path(temp_output_dir) / "UKBB_HPA" / "overlap_statistics.csv"
        assert stats_file.exists()
        
        with open(stats_file, 'r') as f:
            header = f.readline().strip()
        
        # Check exact column names as specified in the prompt
        expected_columns = [
            "mapping_combo_id", "source_name", "target_name", "analysis_timestamp",
            "total_rows", "matched_rows", "source_only_rows", "target_only_rows",
            "direct_matches", "composite_matches", "historical_matches",
            "source_match_rate", "target_match_rate", "jaccard_index", "dice_coefficient",
            "avg_match_confidence", "high_confidence_matches", "confidence_threshold"
        ]
        
        assert header == ",".join(expected_columns)

    @pytest.mark.asyncio
    async def test_venn_diagram_generation(self, action, mock_endpoints, sample_merged_data, temp_output_dir):
        """Test Venn diagram creation."""
        datasets = {"merged_data": sample_merged_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        # Mock matplotlib to avoid actual plot generation in tests
        with patch('biomapper.core.strategy_actions.calculate_set_overlap.plt.savefig') as mock_savefig, \
             patch('biomapper.core.strategy_actions.calculate_set_overlap.plt.close'), \
             patch('biomapper.core.strategy_actions.calculate_set_overlap.venn2') as mock_venn2:
            
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )
            
            # Check that savefig was called twice (SVG and PNG)
            assert mock_savefig.call_count == 2
            
            # Check that venn2 was called with correct parameters
            mock_venn2.assert_called_once()
            call_args = mock_venn2.call_args[1]
            assert call_args['subsets'] == (1, 1, 3)  # source_only, target_only, matched
            assert call_args['set_labels'] == ("UKBB", "HPA")

    # Edge case tests
    @pytest.mark.asyncio
    async def test_empty_merged_dataset(self, action, mock_endpoints, temp_output_dir):
        """Test with empty input dataset."""
        datasets = {"merged_data": []}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        assert stats["total_rows"] == 0
        assert stats["matched_rows"] == 0
        assert stats["source_only_rows"] == 0
        assert stats["target_only_rows"] == 0
        assert stats["jaccard_index"] == 0.0
        assert stats["dice_coefficient"] == 0.0

    @pytest.mark.asyncio
    async def test_no_matches(self, action, mock_endpoints, temp_output_dir):
        """Test when no matches exist."""
        # All rows are source_only or target_only
        no_match_data = [
            {
                "UniProt": "P99999", "Assay": "Test1", "Panel": "Panel1",
                "uniprot": None, "gene": None, "organ": None,
                "match_value": None, "match_type": None, "match_confidence": 0.0,
                "match_status": "source_only", "api_resolved": False
            },
            {
                "UniProt": None, "Assay": None, "Panel": None,
                "uniprot": "P88888", "gene": "GENE1", "organ": "liver",
                "match_value": None, "match_type": None, "match_confidence": 0.0,
                "match_status": "target_only", "api_resolved": False
            }
        ]
        
        datasets = {"merged_data": no_match_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        assert stats["total_rows"] == 2
        assert stats["matched_rows"] == 0
        assert stats["source_only_rows"] == 1
        assert stats["target_only_rows"] == 1
        assert stats["jaccard_index"] == 0.0
        assert stats["source_match_rate"] == 0.0
        assert stats["target_match_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_perfect_overlap(self, action, mock_endpoints, temp_output_dir):
        """Test when all rows match."""
        # All rows have match_status='matched'
        perfect_match_data = [
            {
                "UniProt": "P12345", "Assay": "Test1", "Panel": "Panel1",
                "uniprot": "P12345", "gene": "GENE1", "organ": "liver",
                "match_value": "P12345", "match_type": "direct", "match_confidence": 1.0,
                "match_status": "matched", "api_resolved": False
            },
            {
                "UniProt": "Q67890", "Assay": "Test2", "Panel": "Panel1",
                "uniprot": "Q67890", "gene": "GENE2", "organ": "brain",
                "match_value": "Q67890", "match_type": "direct", "match_confidence": 1.0,
                "match_status": "matched", "api_resolved": False
            }
        ]
        
        datasets = {"merged_data": perfect_match_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        assert stats["total_rows"] == 2
        assert stats["matched_rows"] == 2
        assert stats["source_only_rows"] == 0
        assert stats["target_only_rows"] == 0
        assert stats["jaccard_index"] == 1.0
        assert stats["source_match_rate"] == 1.0
        assert stats["target_match_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_missing_match_columns(self, action, mock_endpoints, temp_output_dir):
        """Test error handling when required columns missing."""
        # Dataset missing match metadata columns
        invalid_data = [
            {"UniProt": "P12345", "Assay": "Test1", "Panel": "Panel1"}
        ]
        
        datasets = {"merged_data": invalid_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        # Should raise clear error about missing match columns
        with pytest.raises(ValueError) as exc_info:
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )
        
        error_msg = str(exc_info.value)
        assert "match_status" in error_msg or "match_type" in error_msg or "match_confidence" in error_msg

    @pytest.mark.asyncio
    async def test_missing_input_dataset(self, action, mock_endpoints, temp_output_dir):
        """Test error when input dataset doesn't exist in context."""
        context = self._create_context({})
        
        params = CalculateSetOverlapParams(
            input_key="missing_dataset",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        with pytest.raises(ValueError) as exc_info:
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )
        
        assert "missing_dataset" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_output_structure(self, action, mock_endpoints, sample_merged_data, temp_output_dir):
        """Test that context outputs have correct structure."""
        datasets = {"merged_data": sample_merged_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        # Check statistics structure
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        required_stats_keys = [
            "mapping_combo_id", "source_name", "target_name", "analysis_timestamp",
            "total_rows", "matched_rows", "source_only_rows", "target_only_rows",
            "direct_matches", "composite_matches", "historical_matches",
            "source_match_rate", "target_match_rate", "jaccard_index", "dice_coefficient",
            "avg_match_confidence", "high_confidence_matches", "confidence_threshold"
        ]
        
        for key in required_stats_keys:
            assert key in stats, f"Missing required statistics key: {key}"
        
        # Check output files structure
        output_files = context.get_action_data("output_files", {})
        expected_file_keys = [
            "overlap_stats_statistics", "overlap_stats_breakdown", 
            "overlap_stats_venn_svg", "overlap_stats_venn_png", 
            "overlap_stats_merged_data"
        ]
        
        for key in expected_file_keys:
            assert key in output_files, f"Missing output file key: {key}"
            assert output_files[key].endswith((".csv", ".svg", ".png"))

    @pytest.mark.asyncio
    async def test_with_real_merged_data(self, action, mock_endpoints, temp_output_dir):
        """Test with realistic merged dataset."""
        # Create more realistic merged data resembling MERGE_WITH_UNIPROT_RESOLUTION output
        realistic_data = [
            # Direct matches
            {
                "UniProt": "P04217", "Assay": "A2M", "Panel": "Inflammation",
                "uniprot": "P04217", "gene": "A2M", "organ": "liver",
                "match_value": "P04217", "match_type": "direct", "match_confidence": 1.0,
                "match_status": "matched", "api_resolved": False
            },
            # Composite matches
            {
                "UniProt": "P14735_P78563", "Assay": "IDE", "Panel": "Metabolism",
                "uniprot": "P14735", "gene": "IDE", "organ": "brain",
                "match_value": "P14735", "match_type": "composite", "match_confidence": 1.0,
                "match_status": "matched", "api_resolved": False
            },
            # Historical matches
            {
                "UniProt": "P01023", "Assay": "A2M", "Panel": "Inflammation",
                "uniprot": "P04217", "gene": "A2M", "organ": "liver",
                "match_value": "P01023->P04217", "match_type": "historical", "match_confidence": 0.85,
                "match_status": "matched", "api_resolved": True
            },
            # Source only
            {
                "UniProt": "P99999", "Assay": "UNKNOWN", "Panel": "Test",
                "uniprot": None, "gene": None, "organ": None,
                "match_value": None, "match_type": None, "match_confidence": 0.0,
                "match_status": "source_only", "api_resolved": False
            },
            # Target only
            {
                "UniProt": None, "Assay": None, "Panel": None,
                "uniprot": "Q8WZ42", "gene": "TITIN", "organ": "muscle",
                "match_value": None, "match_type": None, "match_confidence": 0.0,
                "match_status": "target_only", "api_resolved": False
            }
        ]
        
        datasets = {"merged_data": realistic_data}
        context = self._create_context(datasets)
        
        params = CalculateSetOverlapParams(
            input_key="merged_data",
            source_name="UKBB",
            target_name="HPA",
            mapping_combo_id="UKBB_HPA",
            output_key="overlap_stats",
            output_dir=temp_output_dir
        )
        
        await action.execute_typed(
            [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
        )
        
        # Verify the analysis worked correctly
        stats = context.get_action_data("statistics", {})["overlap_stats"]
        assert stats["total_rows"] == 5
        assert stats["matched_rows"] == 3
        assert stats["direct_matches"] == 1
        assert stats["composite_matches"] == 1
        assert stats["historical_matches"] == 1
        assert stats["source_only_rows"] == 1
        assert stats["target_only_rows"] == 1
        
        # Check that all files were created
        output_path = Path(temp_output_dir) / "UKBB_HPA"
        assert output_path.exists()
        
        for filename in ["overlap_statistics.csv", "match_type_breakdown.csv", 
                        "venn_diagram.svg", "venn_diagram.png", "merged_dataset.csv"]:
            assert (output_path / filename).exists()


class TestRealData:
    """Test with real biological data patterns."""

    @pytest.fixture
    def action(self):
        """Create action instance."""
        return CalculateSetOverlapAction()

    def _create_context(self, datasets=None):
        """Create a test StrategyExecutionContext."""
        context = StrategyExecutionContext(
            initial_identifier="test",
            current_identifier="test",
            ontology_type="protein",
            step_results={},
            provenance=[],
            custom_action_data={},
        )
        if datasets:
            context.set_action_data("datasets", datasets)
        else:
            context.set_action_data("datasets", {})
        context.set_action_data("metadata", {})
        context.set_action_data("statistics", {})
        context.set_action_data("output_files", {})
        return context

    @pytest.fixture
    def mock_endpoints(self):
        """Create mock endpoints."""
        source = MagicMock()
        target = MagicMock()
        return source, target

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, action, mock_endpoints):
        """Test performance with larger dataset."""
        # Create a larger dataset to test performance
        large_data = []
        for i in range(1000):
            if i % 3 == 0:  # matched
                large_data.append({
                    "UniProt": f"P{i:05d}", "Assay": f"ASSAY_{i}", "Panel": "Panel1",
                    "uniprot": f"P{i:05d}", "gene": f"GENE_{i}", "organ": "liver",
                    "match_value": f"P{i:05d}", "match_type": "direct", "match_confidence": 1.0,
                    "match_status": "matched", "api_resolved": False
                })
            elif i % 3 == 1:  # source_only
                large_data.append({
                    "UniProt": f"P{i:05d}", "Assay": f"ASSAY_{i}", "Panel": "Panel1",
                    "uniprot": None, "gene": None, "organ": None,
                    "match_value": None, "match_type": None, "match_confidence": 0.0,
                    "match_status": "source_only", "api_resolved": False
                })
            else:  # target_only
                large_data.append({
                    "UniProt": None, "Assay": None, "Panel": None,
                    "uniprot": f"P{i:05d}", "gene": f"GENE_{i}", "organ": "liver",
                    "match_value": None, "match_type": None, "match_confidence": 0.0,
                    "match_status": "target_only", "api_resolved": False
                })
        
        datasets = {"merged_data": large_data}
        context = self._create_context(datasets)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            params = CalculateSetOverlapParams(
                input_key="merged_data",
                source_name="UKBB",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats",
                output_dir=temp_dir
            )
            
            # This should complete in reasonable time
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )
            
            # Verify statistics are correct
            stats = context.get_action_data("statistics", {})["overlap_stats"]
            assert stats["total_rows"] == 1000
            assert stats["matched_rows"] == 334  # ~1/3 of 1000
            assert stats["source_only_rows"] == 333  # ~1/3 of 1000
            assert stats["target_only_rows"] == 333  # ~1/3 of 1000

    @pytest.mark.asyncio
    async def test_match_type_breakdown_csv_content(self, action, mock_endpoints):
        """Test match type breakdown CSV has correct content and percentages."""
        # Create data with known match type distribution
        test_data = []
        
        # 2 direct matches
        for i in range(2):
            test_data.append({
                "match_status": "matched", "match_type": "direct", "match_confidence": 1.0,
                "UniProt": f"P{i:05d}", "uniprot": f"P{i:05d}"
            })
        
        # 3 composite matches  
        for i in range(3):
            test_data.append({
                "match_status": "matched", "match_type": "composite", "match_confidence": 1.0,
                "UniProt": f"Q{i:05d}", "uniprot": f"Q{i:05d}"
            })
        
        # 1 historical match
        test_data.append({
            "match_status": "matched", "match_type": "historical", "match_confidence": 0.9,
            "UniProt": "OLD123", "uniprot": "NEW123"
        })
        
        datasets = {"test_data": test_data}
        context = self._create_context(datasets)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            params = CalculateSetOverlapParams(
                input_key="test_data",
                source_name="UKBB",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats",
                output_dir=temp_dir
            )
            
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )
            
            # Check that breakdown CSV was created and has correct content
            breakdown_file = Path(temp_dir) / "UKBB_HPA" / "match_type_breakdown.csv"
            assert breakdown_file.exists()
            
            # Read and verify content
            breakdown_df = pd.read_csv(breakdown_file)
            assert len(breakdown_df) == 5  # direct, composite, historical, source_only, target_only
            
            # Check specific counts
            direct_row = breakdown_df[breakdown_df["match_type"] == "direct"]
            assert len(direct_row) == 1
            assert direct_row.iloc[0]["count"] == 2
            
            composite_row = breakdown_df[breakdown_df["match_type"] == "composite"]
            assert len(composite_row) == 1
            assert composite_row.iloc[0]["count"] == 3
            
            historical_row = breakdown_df[breakdown_df["match_type"] == "historical"]
            assert len(historical_row) == 1
            assert historical_row.iloc[0]["count"] == 1

    @pytest.mark.asyncio
    async def test_exact_csv_column_format(self, action, mock_endpoints):
        """Test exact CSV column format matches specification."""
        test_data = [{
            "match_status": "matched", "match_type": "direct", "match_confidence": 1.0
        }]
        
        datasets = {"test_data": test_data}
        context = self._create_context(datasets)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            params = CalculateSetOverlapParams(
                input_key="test_data",
                source_name="UKBB",
                target_name="HPA",
                mapping_combo_id="UKBB_HPA",
                output_key="overlap_stats",
                output_dir=temp_dir
            )
            
            await action.execute_typed(
                [], "unknown", params, mock_endpoints[0], mock_endpoints[1], context
            )
            
            # Read the CSV and verify exact column format
            stats_file = Path(temp_dir) / "UKBB_HPA" / "overlap_statistics.csv"
            stats_df = pd.read_csv(stats_file)
            
            # Check exact column names as specified in the prompt
            expected_columns = [
                "mapping_combo_id", "source_name", "target_name", "analysis_timestamp",
                "total_rows", "matched_rows", "source_only_rows", "target_only_rows",
                "direct_matches", "composite_matches", "historical_matches",
                "source_match_rate", "target_match_rate", "jaccard_index", "dice_coefficient",
                "avg_match_confidence", "high_confidence_matches", "confidence_threshold"
            ]
            
            assert list(stats_df.columns) == expected_columns, f"Expected columns: {expected_columns}, got: {list(stats_df.columns)}"
            
            # Check data types
            import numpy as np
            row = stats_df.iloc[0]
            assert isinstance(row["mapping_combo_id"], str)
            assert isinstance(row["source_name"], str)
            assert isinstance(row["target_name"], str)
            assert isinstance(row["total_rows"], (int, float, np.integer))
            assert isinstance(row["matched_rows"], (int, float, np.integer))
            assert isinstance(row["source_match_rate"], (int, float, np.floating))
            assert isinstance(row["jaccard_index"], (int, float, np.floating))