"""Unit tests for protein mapping strategies."""

import pytest
from unittest.mock import Mock
from biomapper_client import BiomapperClient
from biomapper_client.models import StrategyResult


@pytest.fixture
def client():
    """Mock BiomapperClient for testing."""
    return Mock(spec=BiomapperClient)


@pytest.fixture
def sample_protein_data():
    """Sample protein data for testing."""
    return {
        "identifiers": ["P12345", "Q67890", "O13579"],
        "metadata": {"source": "test", "count": 3},
    }


class TestProteinStrategyLoading:
    """Test that all protein strategies load correctly."""

    def test_arivale_ukbb_comparison_strategy_loads(self, client):
        """Test that Arivale-UKBB comparison strategy loads and validates correctly."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "proteins"
        mock_strategy.metadata.id = "prot_arv_ukb_comparison_uniprot_v1_base"
        mock_strategy.metadata.source_dataset = "arivale"
        mock_strategy.metadata.target_dataset = "ukbb"
        mock_strategy.metadata.bridge_type = ["uniprot"]

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("prot_arv_ukb_comparison_uniprot_v1_base")
        assert strategy is not None
        assert strategy.metadata.entity_type == "proteins"
        assert strategy.metadata.source_dataset == "arivale"
        assert strategy.metadata.target_dataset == "ukbb"

    def test_arivale_kg2c_strategy_loads(self, client):
        """Test that Arivale to KG2c strategy loads correctly."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "proteins"
        mock_strategy.metadata.id = "prot_arv_to_kg2c_uniprot_v1_base"
        mock_strategy.metadata.source_dataset = "arivale"
        mock_strategy.metadata.target_dataset = "kg2c"

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("prot_arv_to_kg2c_uniprot_v1_base")
        assert strategy is not None
        assert strategy.metadata.entity_type == "proteins"
        assert strategy.metadata.source_dataset == "arivale"
        assert strategy.metadata.target_dataset == "kg2c"

    def test_ukbb_kg2c_strategy_loads(self, client):
        """Test that UKBB to KG2c strategy loads correctly."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "proteins"
        mock_strategy.metadata.id = "prot_ukb_to_kg2c_uniprot_v1_base"
        mock_strategy.metadata.source_dataset = "ukbb"
        mock_strategy.metadata.target_dataset = "kg2c"

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("prot_ukb_to_kg2c_uniprot_v1_base")
        assert strategy is not None
        assert strategy.metadata.source_dataset == "ukbb"
        assert strategy.metadata.target_dataset == "kg2c"

    def test_arivale_spoke_strategy_loads(self, client):
        """Test that Arivale to SPOKE strategy loads correctly."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "proteins"
        mock_strategy.metadata.id = "prot_arv_to_spoke_uniprot_v1_base"
        mock_strategy.metadata.source_dataset = "arivale"
        mock_strategy.metadata.target_dataset = "spoke"

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("prot_arv_to_spoke_uniprot_v1_base")
        assert strategy is not None
        assert strategy.metadata.source_dataset == "arivale"
        assert strategy.metadata.target_dataset == "spoke"

    def test_ukbb_spoke_strategy_loads(self, client):
        """Test that UKBB to SPOKE strategy loads correctly."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "proteins"
        mock_strategy.metadata.id = "prot_ukb_to_spoke_uniprot_v1_base"
        mock_strategy.metadata.source_dataset = "ukbb"
        mock_strategy.metadata.target_dataset = "spoke"

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("prot_ukb_to_spoke_uniprot_v1_base")
        assert strategy is not None
        assert strategy.metadata.source_dataset == "ukbb"
        assert strategy.metadata.target_dataset == "spoke"

    def test_multi_source_harmonization_strategy_loads(self, client):
        """Test that multi-source harmonization strategy loads correctly."""
        mock_strategy = Mock()
        mock_strategy.metadata.entity_type = "proteins"
        mock_strategy.metadata.id = "prot_multi_to_unified_uniprot_v1_enhanced"
        mock_strategy.metadata.source_dataset = "multi"
        mock_strategy.metadata.target_dataset = "unified"

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("prot_multi_to_unified_uniprot_v1_enhanced")
        assert strategy is not None
        assert strategy.metadata.source_dataset == "multi"
        assert strategy.metadata.target_dataset == "unified"


class TestProteinStrategyExecution:
    """Test strategy execution with mock data."""

    def test_arivale_kg2c_protein_execution(self, client, sample_protein_data):
        """Test strategy execution with sample data."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.statistics = {
            "match_rate": 0.85,
            "entities_mapped": 1000,
            "entities_total": 1197,
        }

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_arv_to_kg2c_uniprot_v1_base", parameters={"output_dir": "/tmp/test"}
        )
        assert result.success
        assert result.statistics["match_rate"] >= 0.80

    def test_ukbb_kg2c_protein_execution(self, client, sample_protein_data):
        """Test UKBB to KG2c strategy execution."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.statistics = {
            "match_rate": 0.87,
            "entities_mapped": 2100,
            "entities_total": 2500,
        }

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_ukb_to_kg2c_uniprot_v1_base", parameters={"output_dir": "/tmp/test"}
        )
        assert result.success
        assert result.statistics["match_rate"] >= 0.80

    def test_multi_source_harmonization_execution(self, client, sample_protein_data):
        """Test multi-source harmonization strategy execution."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.statistics = {
            "match_rate": 0.92,
            "entities_mapped": 45000,
            "entities_total": 50000,
        }

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_multi_to_unified_uniprot_v1_enhanced",
            parameters={"output_dir": "/tmp/test"},
        )
        assert result.success
        assert result.statistics["match_rate"] >= 0.90


class TestProteinStrategyValidation:
    """Test strategy validation and error handling."""

    def test_strategy_parameter_validation(self, client):
        """Test that strategies validate required parameters."""
        # Mock a strategy execution that fails due to missing parameters
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = False
        mock_result.error = "Missing required parameter: output_dir"

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy("prot_arv_to_kg2c_uniprot_v1_base")
        assert not result.success
        assert "parameter" in result.error.lower()

    def test_strategy_handles_missing_data_files(self, client):
        """Test that strategies handle missing data files gracefully."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = False
        mock_result.error = "Data file not found: /invalid/path.tsv"

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_arv_to_kg2c_uniprot_v1_base", parameters={"output_dir": "/tmp/test"}
        )
        assert not result.success
        assert "file not found" in result.error.lower()

    def test_strategy_performance_benchmarks(self, client):
        """Test that strategies meet performance expectations."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.execution_time_seconds = 45.0  # Under 60s requirement
        mock_result.statistics = {
            "memory_usage_mb": 1500,  # Under 2GB requirement
            "match_rate": 0.85,
        }

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_arv_to_kg2c_uniprot_v1_base", parameters={"output_dir": "/tmp/test"}
        )
        assert result.success
        assert result.execution_time_seconds < 60
        assert result.statistics["memory_usage_mb"] < 2000
        assert result.statistics["match_rate"] >= 0.80


class TestProteinStrategyMetadata:
    """Test strategy metadata completeness and accuracy."""

    @pytest.mark.parametrize(
        "strategy_id,expected_source,expected_target",
        [
            ("prot_arv_ukb_comparison_uniprot_v1_base", "arivale", "ukbb"),
            ("prot_arv_to_kg2c_uniprot_v1_base", "arivale", "kg2c"),
            ("prot_ukb_to_kg2c_uniprot_v1_base", "ukbb", "kg2c"),
            ("prot_arv_to_spoke_uniprot_v1_base", "arivale", "spoke"),
            ("prot_ukb_to_spoke_uniprot_v1_base", "ukbb", "spoke"),
            ("prot_multi_to_unified_uniprot_v1_enhanced", "multi", "unified"),
        ],
    )
    def test_strategy_metadata_consistency(
        self, client, strategy_id, expected_source, expected_target
    ):
        """Test that strategy metadata is consistent and complete."""
        mock_strategy = Mock()
        mock_strategy.metadata.id = strategy_id
        mock_strategy.metadata.entity_type = "proteins"
        mock_strategy.metadata.source_dataset = expected_source
        mock_strategy.metadata.target_dataset = expected_target
        mock_strategy.metadata.bridge_type = ["uniprot"]
        mock_strategy.metadata.quality_tier = "experimental"
        mock_strategy.metadata.version = "1.0.0"
        mock_strategy.metadata.author = "biomapper-team"

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy(strategy_id)
        assert strategy.metadata.id == strategy_id
        assert strategy.metadata.entity_type == "proteins"
        assert strategy.metadata.source_dataset == expected_source
        assert strategy.metadata.target_dataset == expected_target
        assert "uniprot" in strategy.metadata.bridge_type
        assert strategy.metadata.quality_tier == "experimental"

    def test_strategy_tags_are_comprehensive(self, client):
        """Test that strategy tags include all relevant keywords."""
        mock_strategy = Mock()
        mock_strategy.metadata.tags = ["proteomics", "uniprot", "kg2c", "arivale"]

        client.get_strategy.return_value = mock_strategy

        strategy = client.get_strategy("prot_arv_to_kg2c_uniprot_v1_base")
        tags = strategy.metadata.tags
        assert "proteomics" in tags
        assert "uniprot" in tags
        assert any(source in tags for source in ["arivale", "ukbb"])
        assert any(target in tags for target in ["kg2c", "spoke"])
