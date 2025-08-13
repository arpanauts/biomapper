"""Tests for CalculateMappingQualityAction."""

import pytest
import pandas as pd

from biomapper.core.strategy_actions.utils.data_processing.calculate_mapping_quality import (
    CalculateMappingQualityAction,
    CalculateMappingQualityParams,
)
from biomapper.core.exceptions import DatasetNotFoundError, MappingQualityError


class TestCalculateMappingQualityAction:
    """Test suite for CalculateMappingQualityAction."""

    @pytest.fixture
    def source_data(self):
        """Source dataset for testing."""
        return pd.DataFrame(
            {
                "protein_id": ["P12345", "P67890", "P11111", "P22222"],
                "name": ["Protein A", "Protein B", "Protein C", "Protein D"],
            }
        )

    @pytest.fixture
    def mapped_data(self):
        """Mapped dataset for testing."""
        return pd.DataFrame(
            {
                "protein_id": ["P12345", "P67890", "P11111", "P22222"],
                "uniprot_id": ["P12345", "P67890", None, "P22222"],
                "confidence": [0.95, 0.87, None, 0.72],
            }
        )

    @pytest.fixture
    def action(self):
        """CalculateMappingQualityAction instance."""
        return CalculateMappingQualityAction()

    @pytest.mark.asyncio
    async def test_basic_quality_calculation(self, action, source_data, mapped_data):
        """Test basic quality metrics calculation."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            confidence_column="confidence",
            metrics_to_calculate=["match_rate", "coverage", "confidence_distribution"],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert result.total_source_identifiers == 4
        assert result.successful_mappings == 3  # P11111 has None
        assert result.failed_mappings == 1

        # Check individual metrics
        assert "match_rate" in result.individual_metrics
        assert result.individual_metrics["match_rate"] == 0.75  # 3/4
        assert "coverage" in result.individual_metrics
        assert result.individual_metrics["coverage"] == 0.75  # 3/4
        assert "avg_confidence" in result.individual_metrics

        # Check quality distribution
        assert result.quality_distribution["high_quality"] == 2  # confidence >= 0.8
        assert result.quality_distribution["low_quality"] == 1  # confidence < 0.8
        assert result.quality_distribution["failed"] == 1

    @pytest.mark.asyncio
    async def test_precision_recall_with_reference(
        self, action, source_data, mapped_data
    ):
        """Test precision and recall calculation with reference dataset."""
        reference_data = pd.DataFrame(
            {
                "protein_id": ["P12345", "P67890", "P11111", "P22222"],
                "uniprot_id": [
                    "P12345",
                    "P67890",
                    "P33333",
                    "P22222",
                ],  # Different P11111 mapping
            }
        )

        context = {
            "datasets": {
                "source": source_data,
                "mapped": mapped_data,
                "reference": reference_data,
            }
        }

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            reference_dataset_key="reference",
            metrics_to_calculate=["precision", "recall", "f1_score"],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert "precision" in result.individual_metrics
        assert "recall" in result.individual_metrics
        assert "f1_score" in result.individual_metrics

        # Should have good precision/recall for matching entries (P12345, P67890, P22222 match)
        # P11111 is None in mapped but P33333 in reference
        expected_precision = 3 / 3  # 3 mapped pairs, 3 match reference
        expected_recall = 3 / 4  # 4 reference pairs, 3 found in mapped

        assert abs(result.individual_metrics["precision"] - expected_precision) < 0.01
        assert abs(result.individual_metrics["recall"] - expected_recall) < 0.01

    @pytest.mark.asyncio
    async def test_duplicate_rate_calculation(self, action, source_data):
        """Test duplicate rate calculation."""
        # Create mapped data with duplicates
        duplicate_mapped_data = pd.DataFrame(
            {
                "protein_id": ["P12345", "P67890", "P11111", "P22222"],
                "uniprot_id": [
                    "P12345",
                    "P67890",
                    "P67890",
                    "P22222",
                ],  # P67890 appears twice
            }
        )

        context = {"datasets": {"source": source_data, "mapped": duplicate_mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            metrics_to_calculate=["duplicate_rate"],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert "duplicate_rate" in result.individual_metrics
        # 4 total mapped IDs, 3 unique = 1 duplicate
        expected_duplicate_rate = 1 / 4  # 25%
        assert (
            abs(result.individual_metrics["duplicate_rate"] - expected_duplicate_rate)
            < 0.01
        )

    @pytest.mark.asyncio
    async def test_ambiguity_rate_calculation(self, action):
        """Test ambiguity rate calculation."""
        # Create data where one source ID maps to multiple targets
        source_data = pd.DataFrame(
            {
                "protein_id": [
                    "P12345",
                    "P12345",
                    "P67890",
                    "P11111",
                ],  # P12345 appears twice
                "name": ["Protein A1", "Protein A2", "Protein B", "Protein C"],
            }
        )

        mapped_data = pd.DataFrame(
            {
                "protein_id": ["P12345", "P12345", "P67890", "P11111"],
                "uniprot_id": [
                    "Q11111",
                    "Q22222",
                    "P67890",
                    "P11111",
                ],  # P12345 maps to 2 different targets
            }
        )

        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            metrics_to_calculate=["ambiguity_rate"],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert "ambiguity_rate" in result.individual_metrics
        # P12345 maps to 2 targets, others map to 1 each
        # 1 ambiguous source out of 3 unique sources
        expected_ambiguity_rate = 1 / 3
        assert (
            abs(result.individual_metrics["ambiguity_rate"] - expected_ambiguity_rate)
            < 0.01
        )

    @pytest.mark.asyncio
    async def test_identifier_quality_assessment(self, action, source_data):
        """Test identifier quality assessment."""
        # Create mapped data with various ID quality levels
        mixed_quality_data = pd.DataFrame(
            {
                "protein_id": ["P12345", "P67890", "P11111", "P22222"],
                "uniprot_id": ["P12345", "BAD ID", "Q123456", ""],  # Mixed quality
            }
        )

        context = {"datasets": {"source": source_data, "mapped": mixed_quality_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            metrics_to_calculate=["identifier_quality"],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert "id_format_consistency" in result.individual_metrics
        assert "id_completeness" in result.individual_metrics

        # Should have moderate format consistency due to mixed quality IDs
        assert 0 < result.individual_metrics["id_format_consistency"] < 1
        # Completeness should be 75% (3 out of 4 non-empty)
        assert abs(result.individual_metrics["id_completeness"] - 0.75) < 0.01

    @pytest.mark.asyncio
    async def test_recommendations_generation(self, action, source_data):
        """Test that appropriate recommendations are generated."""
        # Create low-quality mapped data
        poor_mapped_data = pd.DataFrame(
            {
                "protein_id": ["P12345", "P67890", "P11111", "P22222"],
                "uniprot_id": [None, None, "P11111", None],  # Only 1/4 successful
                "confidence": [None, None, 0.6, None],  # Low confidence
            }
        )

        context = {"datasets": {"source": source_data, "mapped": poor_mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            confidence_column="confidence",
            metrics_to_calculate=["match_rate", "confidence_distribution"],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert len(result.recommendations) > 0

        # Should recommend improvements for low match rate
        rec_text = " ".join(result.recommendations)
        assert "Low match rate" in rec_text or "match rate" in rec_text.lower()

    @pytest.mark.asyncio
    async def test_overall_quality_score_calculation(
        self, action, source_data, mapped_data
    ):
        """Test overall quality score calculation."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            confidence_column="confidence",
            metrics_to_calculate=[
                "match_rate",
                "coverage",
                "confidence_distribution",
                "identifier_quality",
            ],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert 0 <= result.overall_quality_score <= 1
        # Should be reasonably good quality (>0.5) given the test data
        assert result.overall_quality_score > 0.5

    @pytest.mark.asyncio
    async def test_detailed_report_generation(self, action, source_data, mapped_data):
        """Test detailed report generation."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            confidence_column="confidence",
            include_detailed_report=True,
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert result.detailed_report is not None
        assert "identifier_analysis" in result.detailed_report
        assert "summary_stats" in result.detailed_report
        assert "data_quality" in result.detailed_report

        # Should have analysis for each identifier
        assert len(result.detailed_report["identifier_analysis"]) == 4

        # Check data quality metrics
        dq = result.detailed_report["data_quality"]
        assert "source_completeness" in dq
        assert "mapped_completeness" in dq
        assert dq["source_completeness"] == 1.0  # All source IDs present
        assert dq["mapped_completeness"] == 0.75  # 3/4 mapped IDs present

    @pytest.mark.asyncio
    async def test_context_statistics_update(self, action, source_data, mapped_data):
        """Test that context statistics are properly updated."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            confidence_column="confidence",
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert "statistics" in context
        assert "quality_overall_quality" in context["statistics"]
        assert "quality_match_rate" in context["statistics"]
        assert "quality_successful_mappings" in context["statistics"]

        # Quality dataset should be created
        assert "quality" in context["datasets"]
        quality_df = context["datasets"]["quality"]
        assert isinstance(quality_df, pd.DataFrame)
        assert "metric" in quality_df.columns
        assert "value" in quality_df.columns
        assert "category" in quality_df.columns

    @pytest.mark.asyncio
    async def test_confidence_threshold_parameter(
        self, action, source_data, mapped_data
    ):
        """Test that confidence threshold parameter works correctly."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            confidence_column="confidence",
            confidence_threshold=0.9,  # Higher threshold
            metrics_to_calculate=["confidence_distribution"],
        )

        result = await action.execute_typed(params, context)

        assert result.success
        # With threshold 0.9, only confidence 0.95 should be high quality
        assert result.high_confidence_mappings == 1
        assert result.low_confidence_mappings == 2  # 0.87 and 0.72

    @pytest.mark.asyncio
    async def test_source_dataset_not_found(self, action):
        """Test error when source dataset doesn't exist."""
        context = {"datasets": {}}

        params = CalculateMappingQualityParams(
            source_key="nonexistent",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
        )

        with pytest.raises(DatasetNotFoundError) as exc_info:
            await action.execute_typed(params, context)

        assert "Source dataset 'nonexistent' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mapped_dataset_not_found(self, action, source_data):
        """Test error when mapped dataset doesn't exist."""
        context = {"datasets": {"source": source_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="nonexistent",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
        )

        with pytest.raises(DatasetNotFoundError) as exc_info:
            await action.execute_typed(params, context)

        assert "Mapped dataset 'nonexistent' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_source_column_not_found(self, action, source_data, mapped_data):
        """Test error when source ID column doesn't exist."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="nonexistent_column",
            mapped_id_column="uniprot_id",
        )

        with pytest.raises(MappingQualityError) as exc_info:
            await action.execute_typed(params, context)

        assert "Source ID column 'nonexistent_column' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mapped_column_not_found(self, action, source_data, mapped_data):
        """Test error when mapped ID column doesn't exist."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="nonexistent_column",
        )

        with pytest.raises(MappingQualityError) as exc_info:
            await action.execute_typed(params, context)

        assert "Mapped ID column 'nonexistent_column' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_datasets(self, action):
        """Test handling of empty datasets."""
        empty_source = pd.DataFrame(columns=["protein_id", "name"])
        empty_mapped = pd.DataFrame(columns=["protein_id", "uniprot_id"])

        context = {"datasets": {"source": empty_source, "mapped": empty_mapped}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert result.total_source_identifiers == 0
        assert result.total_mapped_identifiers == 0
        assert result.successful_mappings == 0
        assert result.overall_quality_score == 0

    @pytest.mark.asyncio
    async def test_no_detailed_report(self, action, source_data, mapped_data):
        """Test skipping detailed report generation."""
        context = {"datasets": {"source": source_data, "mapped": mapped_data}}

        params = CalculateMappingQualityParams(
            source_key="source",
            mapped_key="mapped",
            output_key="quality",
            source_id_column="protein_id",
            mapped_id_column="uniprot_id",
            include_detailed_report=False,
        )

        result = await action.execute_typed(params, context)

        assert result.success
        assert result.detailed_report is None
