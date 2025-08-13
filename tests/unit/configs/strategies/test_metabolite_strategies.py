"""
Unit tests for metabolite mapping strategies.

Tests strategy loading, validation, and configuration correctness.
"""

import pytest
import yaml
from pathlib import Path
from biomapper_client import BiomapperClient
from unittest.mock import Mock


class TestMetaboliteStrategies:
    """Test suite for metabolite mapping strategies."""

    @pytest.fixture
    def client(self):
        """Mock BiomapperClient for testing."""
        return Mock(spec=BiomapperClient)

    @pytest.fixture
    def strategy_files(self):
        """List of all metabolite strategy files."""
        strategies_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")
        return list(strategies_dir.glob("met_*.yaml"))

    def test_all_strategy_files_exist(self, strategy_files):
        """Test that all 10 metabolite strategy files exist."""
        expected_strategies = [
            "met_isr_metab_to_kg2c_hmdb_v1_base.yaml",
            "met_isr_lipid_to_kg2c_hmdb_v1_base.yaml",
            "met_arv_to_kg2c_multi_v1_base.yaml",
            "met_ukb_nmr_to_kg2c_nightingale_v1_base.yaml",
            "met_isr_metab_to_spoke_inchikey_v1_base.yaml",
            "met_isr_lipid_to_spoke_inchikey_v1_base.yaml",
            "met_arv_to_spoke_multi_v1_base.yaml",
            "met_ukb_nmr_to_spoke_nightingale_v1_enhanced.yaml",
            "met_multi_to_unified_semantic_v1_enhanced.yaml",
            "met_multi_semantic_enrichment_v1_advanced.yaml",
        ]

        strategy_names = [f.name for f in strategy_files]
        for expected in expected_strategies:
            assert expected in strategy_names, f"Missing strategy file: {expected}"

    def test_strategy_yaml_structure(self, strategy_files):
        """Test that all strategy files have valid YAML structure."""
        for strategy_file in strategy_files:
            with open(strategy_file, "r") as f:
                try:
                    strategy = yaml.safe_load(f)
                    assert strategy is not None, f"Empty strategy file: {strategy_file}"
                    assert isinstance(
                        strategy, dict
                    ), f"Invalid YAML structure in {strategy_file}"
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {strategy_file}: {e}")

    def test_required_metadata_fields(self, strategy_files):
        """Test that all strategies have required metadata fields."""
        required_fields = [
            "id",
            "name",
            "version",
            "created",
            "author",
            "entity_type",
            "source_dataset",
            "target_dataset",
            "bridge_type",
        ]

        for strategy_file in strategy_files:
            with open(strategy_file, "r") as f:
                strategy = yaml.safe_load(f)
                metadata = strategy.get("metadata", {})

                for field in required_fields:
                    assert (
                        field in metadata
                    ), f"Missing {field} in {strategy_file} metadata"

                # Test entity_type is metabolites
                assert (
                    metadata["entity_type"] == "metabolites"
                ), f"Wrong entity_type in {strategy_file}"

    def test_strategy_steps_structure(self, strategy_files):
        """Test that all strategies have valid steps structure."""
        for strategy_file in strategy_files:
            with open(strategy_file, "r") as f:
                strategy = yaml.safe_load(f)

                assert "steps" in strategy, f"Missing steps in {strategy_file}"
                steps = strategy["steps"]
                assert isinstance(steps, list), f"Steps not a list in {strategy_file}"
                assert len(steps) > 0, f"Empty steps in {strategy_file}"

                for i, step in enumerate(steps):
                    assert "name" in step, f"Step {i} missing name in {strategy_file}"
                    assert (
                        "action" in step
                    ), f"Step {i} missing action in {strategy_file}"

                    action = step["action"]
                    assert (
                        "type" in action
                    ), f"Step {i} action missing type in {strategy_file}"
                    assert (
                        "params" in action
                    ), f"Step {i} action missing params in {strategy_file}"

    def test_metabolite_specific_actions(self, strategy_files):
        """Test that metabolite-specific actions are used correctly."""
        metabolite_actions = [
            "METABOLITE_EXTRACT_IDENTIFIERS",
            "METABOLITE_NORMALIZE_HMDB",
            "METABOLITE_CTS_BRIDGE",
            "METABOLITE_MULTI_BRIDGE",
            "NIGHTINGALE_NMR_MATCH",
            "SEMANTIC_METABOLITE_MATCH",
            "VECTOR_ENHANCED_MATCH",
            "COMBINE_METABOLITE_MATCHES",
            "GENERATE_METABOLOMICS_REPORT",
        ]

        for strategy_file in strategy_files:
            with open(strategy_file, "r") as f:
                strategy = yaml.safe_load(f)
                steps = strategy.get("steps", [])

                # Check that at least one metabolite-specific action is used
                action_types = [step["action"]["type"] for step in steps]
                has_metabolite_action = any(
                    action in metabolite_actions for action in action_types
                )
                assert (
                    has_metabolite_action
                ), f"No metabolite-specific actions in {strategy_file}"

    def test_nightingale_strategies_have_reference_file(self, strategy_files):
        """Test that Nightingale-based strategies specify reference file."""
        for strategy_file in strategy_files:
            if "nightingale" in strategy_file.name:
                with open(strategy_file, "r") as f:
                    strategy = yaml.safe_load(f)

                    # Check for Nightingale reference in parameters
                    parameters = strategy.get("parameters", {})
                    assert (
                        "nightingale_reference_file" in parameters
                    ), f"Missing nightingale_reference_file parameter in {strategy_file}"

                    # Check for NIGHTINGALE_NMR_MATCH action
                    steps = strategy.get("steps", [])
                    action_types = [step["action"]["type"] for step in steps]
                    assert (
                        "NIGHTINGALE_NMR_MATCH" in action_types
                    ), f"Missing NIGHTINGALE_NMR_MATCH action in {strategy_file}"

    def test_multi_bridge_strategies_configuration(self, strategy_files):
        """Test multi-bridge strategies have correct configuration."""
        for strategy_file in strategy_files:
            if "multi" in strategy_file.name:
                with open(strategy_file, "r") as f:
                    strategy = yaml.safe_load(f)
                    steps = strategy.get("steps", [])

                    # Find METABOLITE_MULTI_BRIDGE step
                    multi_bridge_steps = [
                        step
                        for step in steps
                        if step["action"]["type"] == "METABOLITE_MULTI_BRIDGE"
                    ]

                    if multi_bridge_steps:
                        step = multi_bridge_steps[0]
                        params = step["action"]["params"]

                        assert (
                            "bridge_types" in params
                        ), f"Missing bridge_types in {strategy_file}"
                        assert isinstance(
                            params["bridge_types"], list
                        ), f"bridge_types not a list in {strategy_file}"
                        assert (
                            len(params["bridge_types"]) > 1
                        ), f"Single bridge type in multi-bridge strategy {strategy_file}"

    def test_lipid_strategies_have_lipid_handling(self, strategy_files):
        """Test lipidomics strategies have specialized lipid handling."""
        for strategy_file in strategy_files:
            if "lipid" in strategy_file.name:
                with open(strategy_file, "r") as f:
                    strategy = yaml.safe_load(f)
                    steps = strategy.get("steps", [])

                    # Check for lipid-specific parameters
                    extract_steps = [
                        step
                        for step in steps
                        if step["action"]["type"] == "METABOLITE_EXTRACT_IDENTIFIERS"
                    ]

                    # At least one extract step should have lipid_specific_parsing
                    has_lipid_parsing = any(
                        step["action"]["params"].get("lipid_specific_parsing", False)
                        for step in extract_steps
                    )
                    assert (
                        has_lipid_parsing
                    ), f"No lipid-specific parsing in {strategy_file}"

    def test_cache_configuration(self, strategy_files):
        """Test that strategies have proper cache configuration."""
        for strategy_file in strategy_files:
            with open(strategy_file, "r") as f:
                strategy = yaml.safe_load(f)
                parameters = strategy.get("parameters", {})

                # Check cache parameters
                assert (
                    "use_cache" in parameters
                ), f"Missing use_cache parameter in {strategy_file}"
                assert (
                    parameters["use_cache"] is True
                ), f"Caching disabled in {strategy_file}"

                if "cache_dir" in parameters:
                    cache_dir = parameters["cache_dir"]
                    assert isinstance(
                        cache_dir, str
                    ), f"Invalid cache_dir type in {strategy_file}"

    def test_output_configuration(self, strategy_files):
        """Test that strategies have proper output configuration."""
        for strategy_file in strategy_files:
            with open(strategy_file, "r") as f:
                strategy = yaml.safe_load(f)
                parameters = strategy.get("parameters", {})

                # Should have output_dir parameter
                assert (
                    "output_dir" in parameters
                ), f"Missing output_dir parameter in {strategy_file}"

                # Should have at least one EXPORT_DATASET step
                steps = strategy.get("steps", [])
                export_steps = [
                    step for step in steps if step["action"]["type"] == "EXPORT_DATASET"
                ]
                assert len(export_steps) > 0, f"No export steps in {strategy_file}"

    def test_strategy_naming_convention(self, strategy_files):
        """Test that strategies follow naming convention."""
        for strategy_file in strategy_files:
            name = strategy_file.name

            # Should start with 'met_'
            assert name.startswith("met_"), f"Strategy {name} doesn't start with 'met_'"

            # Should end with '.yaml'
            assert name.endswith(".yaml"), f"Strategy {name} doesn't end with '.yaml'"

            # Should contain version info
            assert "_v1_" in name, f"Strategy {name} missing version info"

    @pytest.mark.parametrize(
        "strategy_name",
        [
            "met_isr_metab_to_kg2c_hmdb_v1_base",
            "met_arv_to_kg2c_multi_v1_base",
            "met_ukb_nmr_to_kg2c_nightingale_v1_base",
        ],
    )
    def test_specific_strategy_validation(self, strategy_name):
        """Test validation of specific strategies."""
        strategy_file = Path(
            f"/home/ubuntu/biomapper/configs/strategies/experimental/{strategy_name}.yaml"
        )
        assert strategy_file.exists(), f"Strategy file {strategy_name}.yaml not found"

        with open(strategy_file, "r") as f:
            strategy = yaml.safe_load(f)

        # Test basic structure
        assert "name" in strategy
        assert "metadata" in strategy
        assert "steps" in strategy

        # Test metadata ID matches filename
        metadata_id = strategy["metadata"]["id"]
        assert metadata_id == strategy_name, f"Metadata ID mismatch in {strategy_name}"


class TestMetaboliteStrategyContent:
    """Test content and logic of metabolite strategies."""

    def test_hmdb_normalization_steps(self):
        """Test that HMDB normalization steps are properly configured."""
        strategy_file = Path(
            "/home/ubuntu/biomapper/configs/strategies/experimental/met_isr_metab_to_kg2c_hmdb_v1_base.yaml"
        )

        with open(strategy_file, "r") as f:
            strategy = yaml.safe_load(f)

        steps = strategy.get("steps", [])
        normalize_steps = [
            step
            for step in steps
            if step["action"]["type"] == "METABOLITE_NORMALIZE_HMDB"
        ]

        assert len(normalize_steps) > 0, "No HMDB normalization steps found"

        for step in normalize_steps:
            params = step["action"]["params"]
            assert (
                "target_format" in params
            ), "Missing target_format in HMDB normalization"
            assert params["target_format"] in [
                "HMDB0001234",
                "HMDB00001234",
            ], "Invalid HMDB target format"

    def test_cts_bridge_configuration(self):
        """Test CTS bridge configurations are appropriate."""
        strategy_files = [
            "met_isr_metab_to_kg2c_hmdb_v1_base.yaml",
            "met_ukb_nmr_to_kg2c_nightingale_v1_base.yaml",
        ]

        for strategy_name in strategy_files:
            strategy_file = Path(
                f"/home/ubuntu/biomapper/configs/strategies/experimental/{strategy_name}"
            )

            with open(strategy_file, "r") as f:
                strategy = yaml.safe_load(f)

            steps = strategy.get("steps", [])
            cts_steps = [
                step
                for step in steps
                if step["action"]["type"] == "METABOLITE_CTS_BRIDGE"
            ]

            for step in cts_steps:
                params = step["action"]["params"]

                # Check required parameters
                assert "source_key" in params
                assert "target_key" in params
                assert "source_id_type" in params
                assert "target_id_type" in params

                # Check performance parameters
                if "chunk_size" in params:
                    assert params["chunk_size"] > 0, "Invalid chunk_size"
                    assert params["chunk_size"] <= 2000, "Chunk size too large"

                if "parallel_requests" in params:
                    assert params["parallel_requests"] > 0, "Invalid parallel_requests"
                    assert (
                        params["parallel_requests"] <= 10
                    ), "Too many parallel requests"

    def test_semantic_strategies_model_configuration(self):
        """Test semantic strategies have proper model configuration."""
        semantic_files = [
            "met_multi_to_unified_semantic_v1_enhanced.yaml",
            "met_multi_semantic_enrichment_v1_advanced.yaml",
        ]

        for strategy_name in semantic_files:
            strategy_file = Path(
                f"/home/ubuntu/biomapper/configs/strategies/experimental/{strategy_name}"
            )

            with open(strategy_file, "r") as f:
                strategy = yaml.safe_load(f)

            steps = strategy.get("steps", [])
            semantic_steps = [
                step
                for step in steps
                if step["action"]["type"] == "SEMANTIC_METABOLITE_MATCH"
            ]

            for step in semantic_steps:
                params = step["action"]["params"]

                if "model" in params:
                    model = params["model"]
                    # Handle parameter substitution
                    if model.startswith("${"):
                        # Check if parameter is defined
                        strategy_params = strategy.get("parameters", {})
                        param_name = model.strip("${}").split(".")[
                            -1
                        ]  # Get parameter name
                        if param_name in strategy_params:
                            actual_model = strategy_params[param_name]
                            assert (
                                actual_model in ["biobert", "chembert", "mol-bert"]
                            ), f"Unsupported semantic model in parameters: {actual_model}"
                    else:
                        assert model in [
                            "biobert",
                            "chembert",
                            "mol-bert",
                        ], f"Unsupported semantic model: {model}"

                if "threshold" in params:
                    threshold = params["threshold"]
                    assert 0.0 <= threshold <= 1.0, "Invalid threshold range"
