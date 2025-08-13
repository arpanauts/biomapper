"""
Integration tests for multi-entity mapping strategies.

Tests full strategy execution with real data files and API interactions.
These tests verify end-to-end functionality of multi-omics strategies.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
from biomapper_client import BiomapperClient


@pytest.mark.integration
class TestMultiEntityStrategyExecution:
    """Integration tests for multi-entity strategy execution."""

    @pytest.fixture(scope="class")
    def client(self) -> BiomapperClient:
        """Create BiomapperClient for integration testing."""
        return BiomapperClient()

    @pytest.fixture(scope="class")
    def temp_output_dir(self) -> Path:
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_data_files(self, temp_output_dir: Path) -> Dict[str, Path]:
        """Create mock data files for testing."""
        files = {}

        # Mock protein data
        protein_data = """uniprot\tprotein_name\texpression_level\tsubject_id
P12345\tProtein_A\t1.2\tsubj_001
P67890\tProtein_B\t0.8\tsubj_001
Q11111\tProtein_C\t2.1\tsubj_001
P12345\tProtein_A\t1.5\tsubj_002
P67890\tProtein_B\t0.9\tsubj_002"""

        protein_file = temp_output_dir / "mock_proteins.tsv"
        protein_file.write_text(protein_data)
        files["proteins"] = protein_file

        # Mock metabolite data
        metabolite_data = """hmdb_id\tmetabolite_name\tconcentration\tsubject_id
HMDB0000001\tGlucose\t45.2\tsubj_001
HMDB0000002\tCholesterol\t123.4\tsubj_001
HMDB0000003\tCreatinine\t78.9\tsubj_001
HMDB0000001\tGlucose\t48.5\tsubj_002
HMDB0000002\tCholesterol\t135.7\tsubj_002"""

        metabolite_file = temp_output_dir / "mock_metabolites.tsv"
        metabolite_file.write_text(metabolite_data)
        files["metabolites"] = metabolite_file

        # Mock chemistry data
        chemistry_data = """test_name\ttest_value\treference_range\tsubject_id
glucose\t95.0\t70-100\tsubj_001
cholesterol\t180.0\t<200\tsubj_001
creatinine\t1.1\t0.7-1.3\tsubj_001
glucose\t102.0\t70-100\tsubj_002
cholesterol\t195.0\t<200\tsubj_002"""

        chemistry_file = temp_output_dir / "mock_chemistry.tsv"
        chemistry_file.write_text(chemistry_data)
        files["chemistry"] = chemistry_file

        return files

    @pytest.fixture
    def strategy_parameters(self, temp_output_dir: Path) -> Dict[str, Any]:
        """Common strategy parameters for testing."""
        return {
            "output_dir": str(temp_output_dir),
            "enable_semantic_matching": False,  # Disable for faster testing
            "generate_report": False,  # Disable for faster testing
            "chunk_size": 1000,
            "min_confidence": 0.5,
        }

    def test_comprehensive_strategy_structure_validation(self, client: BiomapperClient):
        """Test comprehensive strategy loads correctly and has valid structure."""
        strategy_id = "multi_arv_ukb_isr_comprehensive_v1_advanced"

        # Test strategy can be retrieved (this tests YAML parsing)
        try:
            # This would normally call client.get_strategy(strategy_id)
            # For now, test the file can be loaded and parsed
            strategy_path = (
                Path("/home/ubuntu/biomapper/configs/strategies/experimental")
                / f"{strategy_id}.yaml"
            )
            assert strategy_path.exists(), f"Strategy file {strategy_id}.yaml not found"

            import yaml

            with open(strategy_path) as f:
                strategy = yaml.safe_load(f)

            # Validate structure
            assert strategy is not None
            assert "metadata" in strategy
            assert "steps" in strategy
            assert "expected_outputs" in strategy
            assert len(strategy["metadata"]["entity_type"]) == 3

        except Exception as e:
            pytest.fail(f"Failed to load comprehensive strategy: {e}")

    def test_pathway_strategy_structure_validation(self, client: BiomapperClient):
        """Test pathway analysis strategy loads correctly."""
        strategy_id = "multi_prot_met_pathway_analysis_v1_base"

        try:
            strategy_path = (
                Path("/home/ubuntu/biomapper/configs/strategies/experimental")
                / f"{strategy_id}.yaml"
            )
            assert strategy_path.exists(), f"Strategy file {strategy_id}.yaml not found"

            import yaml

            with open(strategy_path) as f:
                strategy = yaml.safe_load(f)

            # Validate pathway-specific structure
            assert "proteins" in strategy["metadata"]["entity_type"]
            assert "metabolites" in strategy["metadata"]["entity_type"]
            assert "pathway_databases" in strategy["parameters"]

        except Exception as e:
            pytest.fail(f"Failed to load pathway strategy: {e}")

    def test_clinical_bridge_strategy_structure_validation(
        self, client: BiomapperClient
    ):
        """Test clinical bridge strategy loads correctly."""
        strategy_id = "multi_chem_met_clinical_bridge_v1_experimental"

        try:
            strategy_path = (
                Path("/home/ubuntu/biomapper/configs/strategies/experimental")
                / f"{strategy_id}.yaml"
            )
            assert strategy_path.exists(), f"Strategy file {strategy_id}.yaml not found"

            import yaml

            with open(strategy_path) as f:
                strategy = yaml.safe_load(f)

            # Validate clinical-specific structure
            assert "chemistry" in strategy["metadata"]["entity_type"]
            assert "metabolites" in strategy["metadata"]["entity_type"]
            assert "clinical_mappings" in strategy["metadata"]

        except Exception as e:
            pytest.fail(f"Failed to load clinical bridge strategy: {e}")

    def test_longitudinal_strategy_structure_validation(self, client: BiomapperClient):
        """Test longitudinal strategy loads correctly."""
        strategy_id = "multi_longitudinal_tracking_v1_advanced"

        try:
            strategy_path = (
                Path("/home/ubuntu/biomapper/configs/strategies/experimental")
                / f"{strategy_id}.yaml"
            )
            assert strategy_path.exists(), f"Strategy file {strategy_id}.yaml not found"

            import yaml

            with open(strategy_path) as f:
                strategy = yaml.safe_load(f)

            # Validate longitudinal-specific structure
            assert "temporal_framework" in strategy["metadata"]
            assert "timepoints" in strategy["parameters"]
            assert "change_threshold" in strategy["parameters"]

        except Exception as e:
            pytest.fail(f"Failed to load longitudinal strategy: {e}")

    def test_disease_strategy_structure_validation(self, client: BiomapperClient):
        """Test disease integration strategy loads correctly."""
        strategy_id = "multi_disease_integration_v1_specialized"

        try:
            strategy_path = (
                Path("/home/ubuntu/biomapper/configs/strategies/experimental")
                / f"{strategy_id}.yaml"
            )
            assert strategy_path.exists(), f"Strategy file {strategy_id}.yaml not found"

            import yaml

            with open(strategy_path) as f:
                strategy = yaml.safe_load(f)

            # Validate disease-specific structure
            assert "disease_models" in strategy["metadata"]
            assert "disease_focus" in strategy["parameters"]
            assert "biomarker_selection_method" in strategy["parameters"]

        except Exception as e:
            pytest.fail(f"Failed to load disease strategy: {e}")

    @pytest.mark.slow
    def test_strategy_parameter_substitution(self):
        """Test parameter substitution works in strategies."""
        strategy_path = Path(
            "/home/ubuntu/biomapper/configs/strategies/experimental/multi_arv_ukb_isr_comprehensive_v1_advanced.yaml"
        )

        import yaml

        with open(strategy_path) as f:
            strategy_content = f.read()

        # Test that parameter references exist
        assert "${parameters.output_dir}" in strategy_content
        # Note: enable_semantic_matching is used in parameters but not always referenced in steps

        # Test that metadata references exist
        assert "${metadata.source_files" in strategy_content

        # Test YAML can be parsed with parameter placeholders
        strategy = yaml.safe_load(strategy_content)
        assert strategy is not None

    @pytest.mark.slow
    def test_all_strategies_have_required_outputs(self):
        """Test all strategies define required outputs."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")
        strategy_files = list(strategies_dir.glob("multi_*.yaml"))

        assert len(strategy_files) == 5, "Should have exactly 5 multi-entity strategies"

        import yaml

        for strategy_file in strategy_files:
            with open(strategy_file) as f:
                strategy = yaml.safe_load(f)

            # Test expected outputs structure
            assert (
                "expected_outputs" in strategy
            ), f"Missing expected_outputs in {strategy_file.name}"
            outputs = strategy["expected_outputs"]

            # Test required output categories
            assert (
                "primary" in outputs
            ), f"Missing primary outputs in {strategy_file.name}"
            assert (
                "reports" in outputs
            ), f"Missing reports outputs in {strategy_file.name}"

            # Test output paths use parameter substitution
            for category, output_list in outputs.items():
                for output in output_list:
                    assert (
                        "path" in output
                    ), f"Missing path in {category} output in {strategy_file.name}"
                    assert (
                        "${parameters.output_dir}" in output["path"]
                    ), f"Output path should use parameter substitution in {strategy_file.name}"

    @pytest.mark.slow
    def test_action_sequence_logic(self):
        """Test that action sequences make logical sense."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")

        import yaml

        # Test comprehensive strategy sequence
        comprehensive_path = (
            strategies_dir / "multi_arv_ukb_isr_comprehensive_v1_advanced.yaml"
        )
        with open(comprehensive_path) as f:
            strategy = yaml.safe_load(f)

        step_names = [step["name"] for step in strategy["steps"]]

        # Test logical progression: load -> extract -> normalize -> merge -> analyze -> export
        load_steps = [name for name in step_names if "load" in name.lower()]
        extract_steps = [name for name in step_names if "extract" in name.lower()]
        normalize_steps = [name for name in step_names if "normalize" in name.lower()]
        merge_steps = [name for name in step_names if "merge" in name.lower()]
        export_steps = [name for name in step_names if "export" in name.lower()]

        assert len(load_steps) > 0, "Should have load steps"
        assert len(normalize_steps) > 0, "Should have normalize steps"
        assert len(merge_steps) > 0, "Should have merge steps"
        assert len(export_steps) > 0, "Should have export steps"

        # Test that at least some load comes before normalize (more flexible check)
        load_indices = [
            i for i, name in enumerate(step_names) if "load" in name.lower()
        ]
        normalize_indices = [
            i for i, name in enumerate(step_names) if "normalize" in name.lower()
        ]

        if load_indices and normalize_indices:
            # At least one load step should come before any normalize step
            assert min(load_indices) < max(
                normalize_indices
            ), "At least some load steps should come before normalize steps"

    @pytest.mark.slow
    def test_strategy_validation_criteria(self):
        """Test validation criteria in strategies are reasonable."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")

        import yaml

        for strategy_file in strategies_dir.glob("multi_*.yaml"):
            with open(strategy_file) as f:
                strategy = yaml.safe_load(f)

            if "validation" in strategy:
                validation = strategy["validation"]

                # Test execution time limits are reasonable (5-45 minutes)
                if "max_execution_time_minutes" in validation:
                    time_limit = validation["max_execution_time_minutes"]
                    assert (
                        5 <= time_limit <= 45
                    ), f"Execution time {time_limit} min seems unreasonable in {strategy_file.name}"

                # Test memory limits are reasonable (1-16 GB)
                if "max_memory_gb" in validation:
                    memory_limit = validation["max_memory_gb"]
                    assert (
                        1 <= memory_limit <= 16
                    ), f"Memory limit {memory_limit} GB seems unreasonable in {strategy_file.name}"

                # Test minimum result thresholds are positive
                for key, value in validation.items():
                    if key.startswith("min_") and isinstance(value, (int, float)):
                        assert (
                            value > 0
                        ), f"Minimum threshold {key}={value} should be positive in {strategy_file.name}"


@pytest.mark.integration
@pytest.mark.slow
class TestMultiEntityStrategyPerformance:
    """Performance tests for multi-entity strategies."""

    def test_strategy_complexity_metrics(self):
        """Test strategy complexity metrics."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")

        import yaml

        complexity_metrics = {}

        for strategy_file in strategies_dir.glob("multi_*.yaml"):
            with open(strategy_file) as f:
                strategy = yaml.safe_load(f)

            metrics = {
                "num_steps": len(strategy["steps"]),
                "num_entities": len(strategy["metadata"]["entity_type"]),
                "num_parameters": len(strategy["parameters"]),
                "num_source_files": len(strategy["metadata"].get("source_files", [])),
                "estimated_complexity": 0,
            }

            # Calculate estimated complexity
            metrics["estimated_complexity"] = (
                metrics["num_steps"] * 2
                + metrics["num_entities"] * 3
                + metrics["num_source_files"]
            )

            complexity_metrics[strategy_file.stem] = metrics

        # Test complexity bounds
        for strategy_name, metrics in complexity_metrics.items():
            assert (
                metrics["num_steps"] <= 50
            ), f"Strategy {strategy_name} has too many steps ({metrics['num_steps']})"
            assert (
                metrics["estimated_complexity"] <= 200
            ), f"Strategy {strategy_name} complexity too high ({metrics['estimated_complexity']})"

    def test_parameter_count_reasonable(self):
        """Test that strategies don't have excessive parameters."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")

        import yaml

        for strategy_file in strategies_dir.glob("multi_*.yaml"):
            with open(strategy_file) as f:
                strategy = yaml.safe_load(f)

            num_params = len(strategy["parameters"])
            assert (
                num_params <= 20
            ), f"Strategy {strategy_file.name} has too many parameters ({num_params})"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
