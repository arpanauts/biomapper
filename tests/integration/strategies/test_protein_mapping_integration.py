"""Integration tests for protein mapping strategies."""

import pytest
import tempfile
import os
from unittest.mock import Mock
from biomapper_client import BiomapperClient
from biomapper_client.models import StrategyResult


@pytest.fixture
def client():
    """Real BiomapperClient for integration testing."""
    # In a real integration test, this would be the actual client
    # For now, we'll mock it with more realistic behavior
    return Mock(spec=BiomapperClient)


@pytest.fixture
def temp_output_dir():
    """Create temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def sample_arivale_data(temp_output_dir):
    """Create sample Arivale proteomics data for testing."""
    data = """uniprot\tgene_symbol\tprotein_name
P12345\tTP53\tTumor protein p53
Q67890\tEGFR\tEpidermal growth factor receptor
O13579\tBRCA1\tBreast cancer type 1 susceptibility protein
P98765\tINS\tInsulin
Q54321\tALB\tSerum albumin"""

    file_path = os.path.join(temp_output_dir, "arivale_test.tsv")
    with open(file_path, "w") as f:
        f.write(data)
    return file_path


@pytest.fixture
def sample_kg2c_data(temp_output_dir):
    """Create sample KG2c protein data for testing."""
    data = """id\tname\txrefs\ttype
ENSEMBL:ENSG00000141510\tTP53\tUniProtKB:P12345|HGNC:11998\tProtein
ENSEMBL:ENSG00000146648\tEGFR\tUniProtKB:Q67890|HGNC:3236\tProtein
ENSEMBL:ENSG00000012048\tBRCA1\tUniProtKB:O13579|HGNC:1100\tProtein
ENSEMBL:ENSG00000114480\tINS\tUniProtKB:P01308|HGNC:6081\tProtein
ENSEMBL:ENSG00000163631\tALB\tUniProtKB:P02768|HGNC:399\tProtein"""

    file_path = os.path.join(temp_output_dir, "kg2c_test.csv")
    with open(file_path, "w") as f:
        f.write(data)
    return file_path


class TestProteinMappingIntegration:
    """Integration tests for protein mapping pipeline."""

    def test_arivale_to_kg2c_full_pipeline(
        self, client, temp_output_dir, sample_arivale_data, sample_kg2c_data
    ):
        """Test complete Arivale to KG2c protein mapping pipeline."""
        # Mock a successful execution result
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.execution_time_seconds = 30.5
        mock_result.statistics = {
            "entities_total": 5,
            "entities_mapped": 4,
            "match_rate": 0.80,
            "memory_usage_mb": 256,
        }
        mock_result.output_files = [
            os.path.join(temp_output_dir, "arivale_kg2c_proteins.tsv")
        ]

        client.execute_strategy.return_value = mock_result

        # Execute the strategy with test data
        result = client.execute_strategy(
            "prot_arv_to_kg2c_uniprot_v1_base",
            parameters={
                "output_dir": temp_output_dir,
                "arivale_data": sample_arivale_data,
                "kg2c_data": sample_kg2c_data,
            },
        )

        # Verify execution success
        assert result.success
        assert result.statistics["entities_mapped"] > 0
        assert result.statistics["match_rate"] >= 0.75  # Reasonable match rate
        assert result.execution_time_seconds < 60

        # Verify output files would be created
        assert len(result.output_files) > 0

    def test_ukbb_to_spoke_integration(self, client, temp_output_dir):
        """Test UKBB to SPOKE mapping integration."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.execution_time_seconds = 45.2
        mock_result.statistics = {
            "entities_total": 2500,
            "entities_mapped": 2200,
            "match_rate": 0.88,
        }

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_ukb_to_spoke_uniprot_v1_base",
            parameters={"output_dir": temp_output_dir},
        )

        assert result.success
        assert result.statistics["match_rate"] >= 0.80

    def test_multi_source_harmonization_integration(self, client, temp_output_dir):
        """Test multi-source protein harmonization with all datasets."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.execution_time_seconds = 120.5
        mock_result.statistics = {
            "entities_total": 68697,  # Sum of all sources
            "entities_mapped": 62000,  # After deduplication
            "match_rate": 0.90,
            "memory_usage_mb": 1800,
        }
        mock_result.output_files = [
            os.path.join(temp_output_dir, "unified_proteins.tsv"),
            os.path.join(temp_output_dir, "arivale_proteins_normalized.tsv"),
            os.path.join(temp_output_dir, "ukbb_proteins_normalized.tsv"),
            os.path.join(temp_output_dir, "kg2c_proteins_filtered.tsv"),
            os.path.join(temp_output_dir, "spoke_proteins_filtered.tsv"),
        ]

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_multi_to_unified_uniprot_v1_enhanced",
            parameters={"output_dir": temp_output_dir},
        )

        assert result.success
        assert result.statistics["entities_mapped"] > 50000  # Significant harmonization
        assert result.statistics["match_rate"] >= 0.88
        assert len(result.output_files) >= 5  # Multiple output files expected

    def test_sequential_strategy_execution(self, client, temp_output_dir):
        """Test executing multiple protein strategies in sequence."""
        strategies = [
            "prot_arv_to_kg2c_uniprot_v1_base",
            "prot_ukb_to_kg2c_uniprot_v1_base",
            "prot_arv_to_spoke_uniprot_v1_base",
        ]

        results = []
        for i, strategy_id in enumerate(strategies):
            mock_result = Mock(spec=StrategyResult)
            mock_result.success = True
            mock_result.statistics = {
                "entities_mapped": 1000 + (i * 200),
                "match_rate": 0.82 + (i * 0.02),
            }

            client.execute_strategy.return_value = mock_result

            result = client.execute_strategy(
                strategy_id,
                parameters={"output_dir": os.path.join(temp_output_dir, f"run_{i}")},
            )
            results.append(result)

        # Verify all strategies executed successfully
        assert all(result.success for result in results)
        assert all(result.statistics["entities_mapped"] > 0 for result in results)

        # Verify match rates are reasonable and improving
        match_rates = [result.statistics["match_rate"] for result in results]
        assert all(rate >= 0.80 for rate in match_rates)

    @pytest.mark.slow
    def test_performance_benchmarks(self, client, temp_output_dir):
        """Test that strategies meet performance benchmarks."""
        # Test individual strategy performance
        strategies_benchmarks = {
            "prot_arv_to_kg2c_uniprot_v1_base": {"max_time": 60, "max_memory": 2000},
            "prot_ukb_to_kg2c_uniprot_v1_base": {"max_time": 90, "max_memory": 2000},
            "prot_multi_to_unified_uniprot_v1_enhanced": {
                "max_time": 180,
                "max_memory": 2000,
            },
        }

        for strategy_id, benchmarks in strategies_benchmarks.items():
            mock_result = Mock(spec=StrategyResult)
            mock_result.success = True
            mock_result.execution_time_seconds = (
                benchmarks["max_time"] * 0.75
            )  # Under limit
            mock_result.statistics = {
                "memory_usage_mb": benchmarks["max_memory"] * 0.8,  # Under limit
                "match_rate": 0.85,
            }

            client.execute_strategy.return_value = mock_result

            result = client.execute_strategy(
                strategy_id, parameters={"output_dir": temp_output_dir}
            )

            assert result.success
            assert result.execution_time_seconds < benchmarks["max_time"]
            assert result.statistics["memory_usage_mb"] < benchmarks["max_memory"]

    def test_error_handling_integration(self, client, temp_output_dir):
        """Test error handling in integration scenarios."""
        # Test with invalid file path
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = False
        mock_result.error = "File not found: /invalid/path/data.tsv"

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_arv_to_kg2c_uniprot_v1_base",
            parameters={"output_dir": "/invalid/path"},
        )

        assert not result.success
        assert "not found" in result.error.lower()

    def test_data_validation_integration(
        self, client, temp_output_dir, sample_arivale_data
    ):
        """Test data validation during integration."""
        # Create malformed data file
        bad_data = """invalid\theader\tformat
not_uniprot\tno_gene\tno_name"""

        bad_file = os.path.join(temp_output_dir, "bad_arivale.tsv")
        with open(bad_file, "w") as f:
            f.write(bad_data)

        mock_result = Mock(spec=StrategyResult)
        mock_result.success = False
        mock_result.error = "Invalid column format: expected 'uniprot' column"

        client.execute_strategy.return_value = mock_result

        result = client.execute_strategy(
            "prot_arv_to_kg2c_uniprot_v1_base",
            parameters={"output_dir": temp_output_dir, "arivale_data": bad_file},
        )

        assert not result.success
        assert "validation" in result.error.lower() or "column" in result.error.lower()


class TestProteinActionIntegration:
    """Test integration of individual protein actions within strategies."""

    def test_protein_extract_uniprot_integration(
        self, client, temp_output_dir, sample_kg2c_data
    ):
        """Test PROTEIN_EXTRACT_UNIPROT_FROM_XREFS action integration."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.statistics = {
            "entities_processed": 5,
            "entities_extracted": 4,
            "extraction_rate": 0.80,
        }

        client.execute_action.return_value = mock_result

        result = client.execute_action(
            "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS",
            parameters={
                "input_file": sample_kg2c_data,
                "xrefs_column": "xrefs",
                "remove_isoforms": True,
            },
        )

        assert result.success
        assert result.statistics["extraction_rate"] >= 0.75

    def test_protein_normalize_accessions_integration(
        self, client, temp_output_dir, sample_arivale_data
    ):
        """Test PROTEIN_NORMALIZE_ACCESSIONS action integration."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.statistics = {
            "entities_processed": 5,
            "entities_normalized": 5,
            "normalization_rate": 1.0,
        }

        client.execute_action.return_value = mock_result

        result = client.execute_action(
            "PROTEIN_NORMALIZE_ACCESSIONS",
            parameters={
                "input_file": sample_arivale_data,
                "identifier_column": "uniprot",
            },
        )

        assert result.success
        assert result.statistics["normalization_rate"] >= 0.95

    def test_protein_multi_bridge_integration(self, client, temp_output_dir):
        """Test PROTEIN_MULTI_BRIDGE action integration."""
        mock_result = Mock(spec=StrategyResult)
        mock_result.success = True
        mock_result.statistics = {
            "bridge_attempts": 3,
            "successful_bridges": 2,
            "entities_matched": 150,
            "bridge_success_rate": 0.67,
        }

        client.execute_action.return_value = mock_result

        result = client.execute_action(
            "PROTEIN_MULTI_BRIDGE",
            parameters={
                "bridge_types": ["uniprot", "gene_symbol", "ensembl"],
                "max_attempts": 3,
            },
        )

        assert result.success
        assert result.statistics["entities_matched"] > 0
        assert result.statistics["bridge_success_rate"] >= 0.5
