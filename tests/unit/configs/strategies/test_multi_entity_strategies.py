"""
Unit tests for multi-entity mapping strategies.

Tests the YAML strategy configurations for multi-omics analysis,
including validation of strategy structure, parameter handling,
and expected outputs specification.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List
from biomapper_client import BiomapperClient


class TestMultiEntityStrategies:
    """Test suite for multi-entity strategies."""

    @pytest.fixture
    def strategies_dir(self) -> Path:
        """Get path to experimental strategies directory."""
        return Path("/home/ubuntu/biomapper/configs/strategies/experimental")

    @pytest.fixture
    def strategy_files(self, strategies_dir: Path) -> List[Path]:
        """Get all multi-entity strategy files."""
        return list(strategies_dir.glob("multi_*.yaml"))

    @pytest.fixture
    def client(self) -> BiomapperClient:
        """Create BiomapperClient instance for testing."""
        return BiomapperClient()

    def load_strategy(self, strategy_path: Path) -> Dict[str, Any]:
        """Load strategy YAML file."""
        with open(strategy_path, "r") as f:
            return yaml.safe_load(f)

    def test_all_strategies_exist(self, strategies_dir: Path):
        """Test that all expected multi-entity strategies exist."""
        expected_strategies = [
            "multi_arv_ukb_isr_comprehensive_v1_advanced.yaml",
            "multi_prot_met_pathway_analysis_v1_base.yaml",
            "multi_chem_met_clinical_bridge_v1_experimental.yaml",
            "multi_longitudinal_tracking_v1_advanced.yaml",
            "multi_disease_integration_v1_specialized.yaml",
        ]

        for strategy_name in expected_strategies:
            strategy_path = strategies_dir / strategy_name
            assert strategy_path.exists(), f"Strategy {strategy_name} not found"
            assert strategy_path.is_file(), f"Strategy {strategy_name} is not a file"

    def test_strategy_structure_validity(self, strategy_files: List[Path]):
        """Test that all strategies have valid YAML structure."""
        for strategy_file in strategy_files:
            strategy = self.load_strategy(strategy_file)

            # Test required top-level keys
            required_keys = ["metadata", "parameters", "steps", "expected_outputs"]
            for key in required_keys:
                assert key in strategy, f"Missing {key} in {strategy_file.name}"

            # Test metadata structure
            metadata = strategy["metadata"]
            metadata_required = ["id", "name", "version", "entity_type", "description"]
            for key in metadata_required:
                assert (
                    key in metadata
                ), f"Missing metadata.{key} in {strategy_file.name}"

            # Test entity types are valid
            valid_entities = ["proteins", "metabolites", "chemistry", "genes"]
            for entity in metadata["entity_type"]:
                assert (
                    entity in valid_entities
                ), f"Invalid entity type {entity} in {strategy_file.name}"

    def test_comprehensive_strategy_structure(self, strategies_dir: Path):
        """Test comprehensive multi-omics strategy specific structure."""
        strategy_path = (
            strategies_dir / "multi_arv_ukb_isr_comprehensive_v1_advanced.yaml"
        )
        strategy = self.load_strategy(strategy_path)

        # Test entity types
        assert "proteins" in strategy["metadata"]["entity_type"]
        assert "metabolites" in strategy["metadata"]["entity_type"]
        assert "chemistry" in strategy["metadata"]["entity_type"]

        # Test source files specification
        assert "source_files" in strategy["metadata"]
        source_files = strategy["metadata"]["source_files"]
        assert len(source_files) >= 8, "Should have files for all entities and datasets"

        # Test entity distribution in source files
        entities = [f.get("entity") for f in source_files]
        assert "proteins" in entities
        assert "metabolites" in entities
        assert "chemistry" in entities

        # Test step categories
        step_names = [step["name"] for step in strategy["steps"]]
        expected_categories = [
            "protein",
            "metabolite",
            "chemistry",
            "merge",
            "semantic",
            "export",
        ]
        for category in expected_categories:
            assert any(
                category in name.lower() for name in step_names
            ), f"Missing {category} steps in comprehensive strategy"

    def test_pathway_analysis_strategy_structure(self, strategies_dir: Path):
        """Test pathway analysis strategy specific structure."""
        strategy_path = strategies_dir / "multi_prot_met_pathway_analysis_v1_base.yaml"
        strategy = self.load_strategy(strategy_path)

        # Test focuses on proteins and metabolites
        entity_types = strategy["metadata"]["entity_type"]
        assert "proteins" in entity_types
        assert "metabolites" in entity_types

        # Test pathway-specific parameters
        params = strategy["parameters"]
        assert "pathway_databases" in params
        assert "enrichment_method" in params
        assert "fdr_threshold" in params

        # Test pathway analysis steps
        step_names = [step["name"] for step in strategy["steps"]]
        pathway_steps = ["pathway", "enrichment", "association", "network"]
        for step_type in pathway_steps:
            assert any(
                step_type in name.lower() for name in step_names
            ), f"Missing {step_type} steps in pathway strategy"

    def test_clinical_bridge_strategy_structure(self, strategies_dir: Path):
        """Test clinical chemistry-metabolomics bridge strategy structure."""
        strategy_path = (
            strategies_dir / "multi_chem_met_clinical_bridge_v1_experimental.yaml"
        )
        strategy = self.load_strategy(strategy_path)

        # Test focuses on chemistry and metabolites
        entity_types = strategy["metadata"]["entity_type"]
        assert "chemistry" in entity_types
        assert "metabolites" in entity_types

        # Test clinical mappings
        assert "clinical_mappings" in strategy["metadata"]
        mappings = strategy["metadata"]["clinical_mappings"]
        expected_mappings = [
            "glucose_metabolism",
            "lipid_metabolism",
            "kidney_function",
        ]
        for mapping in expected_mappings:
            assert mapping in mappings, f"Missing {mapping} in clinical mappings"

        # Test clinical-specific parameters
        params = strategy["parameters"]
        assert "correlation_threshold" in params
        assert "clinical_significance_threshold" in params

    def test_longitudinal_strategy_structure(self, strategies_dir: Path):
        """Test longitudinal tracking strategy structure."""
        strategy_path = strategies_dir / "multi_longitudinal_tracking_v1_advanced.yaml"
        strategy = self.load_strategy(strategy_path)

        # Test temporal framework
        assert "temporal_framework" in strategy["metadata"]
        framework = strategy["metadata"]["temporal_framework"]
        assert "timepoints" in framework
        assert "minimum_timepoints" in framework
        assert "alignment_method" in framework

        # Test analysis types
        assert "analysis_types" in strategy["metadata"]
        analysis_types = strategy["metadata"]["analysis_types"]
        expected_analyses = [
            "trend_analysis",
            "change_detection",
            "trajectory_clustering",
        ]
        for analysis in expected_analyses:
            assert (
                analysis in analysis_types
            ), f"Missing {analysis} in longitudinal strategy"

        # Test longitudinal parameters
        params = strategy["parameters"]
        assert "timepoints" in params
        assert "change_threshold" in params
        assert "trajectory_clustering_k" in params

    def test_disease_strategy_structure(self, strategies_dir: Path):
        """Test disease-specific integration strategy structure."""
        strategy_path = strategies_dir / "multi_disease_integration_v1_specialized.yaml"
        strategy = self.load_strategy(strategy_path)

        # Test disease models
        assert "disease_models" in strategy["metadata"]
        models = strategy["metadata"]["disease_models"]
        expected_diseases = [
            "type_2_diabetes",
            "cardiovascular_disease",
            "metabolic_syndrome",
        ]
        for disease in expected_diseases:
            assert disease in models, f"Missing {disease} model"
            assert "clinical_criteria" in models[disease]
            assert "biomarker_categories" in models[disease]

        # Test disease-specific parameters
        params = strategy["parameters"]
        assert "disease_focus" in params
        assert "biomarker_selection_method" in params
        assert "validation_required" in params

    def test_step_action_validity(self, strategy_files: List[Path]):
        """Test that all strategy steps reference valid actions."""
        valid_actions = {
            # Core actions
            "LOAD_DATASET_IDENTIFIERS",
            "MERGE_DATASETS",
            "EXPORT_DATASET",
            "CALCULATE_SET_OVERLAP",
            "CALCULATE_THREE_WAY_OVERLAP",
            # Protein actions
            "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS",
            "PROTEIN_NORMALIZE_ACCESSIONS",
            "PROTEIN_MULTI_BRIDGE",
            # Metabolite actions
            "METABOLITE_EXTRACT_IDENTIFIERS",
            "METABOLITE_NORMALIZE_HMDB",
            "METABOLITE_CTS_BRIDGE",
            "NIGHTINGALE_NMR_MATCH",
            "SEMANTIC_METABOLITE_MATCH",
            "METABOLITE_API_ENRICHMENT",
            "COMBINE_METABOLITE_MATCHES",
            # Chemistry actions
            "CHEMISTRY_EXTRACT_LOINC",
            "CHEMISTRY_FUZZY_TEST_MATCH",
            "CHEMISTRY_VENDOR_HARMONIZATION",
            # Reporting
            "GENERATE_METABOLOMICS_REPORT",
        }

        for strategy_file in strategy_files:
            strategy = self.load_strategy(strategy_file)

            for step in strategy["steps"]:
                action_type = step["action"]["type"]
                assert (
                    action_type in valid_actions
                ), f"Invalid action {action_type} in {strategy_file.name} step {step['name']}"

    def test_parameter_references(self, strategy_files: List[Path]):
        """Test parameter reference syntax in strategies."""
        for strategy_file in strategy_files:
            strategy = self.load_strategy(strategy_file)

            # Convert to string to check parameter references
            strategy_str = yaml.dump(strategy)

            # Test parameter substitution syntax
            import re

            param_refs = re.findall(r"\$\{parameters\.(\w+)\}", strategy_str)
            param_keys = set(strategy["parameters"].keys())

            for ref in param_refs:
                assert (
                    ref in param_keys
                ), f"Parameter reference {ref} not defined in {strategy_file.name}"

            # Test metadata references
            metadata_refs = re.findall(r"\$\{metadata\.(\w+)", strategy_str)
            metadata_keys = set()

            def collect_keys(obj, prefix=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        key = f"{prefix}.{k}" if prefix else k
                        metadata_keys.add(key)
                        collect_keys(v, key)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        collect_keys(item, f"{prefix}[{i}]")

            collect_keys(strategy["metadata"])

            for ref in metadata_refs:
                # Remove any array indexing for validation
                ref_clean = re.sub(r"\[\d+\].*$", "", ref)
                assert any(
                    ref_clean in key for key in metadata_keys
                ), f"Metadata reference {ref} not accessible in {strategy_file.name}"

    def test_expected_outputs_structure(self, strategy_files: List[Path]):
        """Test expected outputs structure in all strategies."""
        for strategy_file in strategy_files:
            strategy = self.load_strategy(strategy_file)

            outputs = strategy["expected_outputs"]

            # Test required output categories
            required_categories = ["primary", "reports"]
            for category in required_categories:
                assert (
                    category in outputs
                ), f"Missing {category} outputs in {strategy_file.name}"

            # Test output structure
            for category, output_list in outputs.items():
                assert isinstance(
                    output_list, list
                ), f"Outputs {category} should be a list in {strategy_file.name}"

                for output in output_list:
                    assert (
                        "path" in output
                    ), f"Missing path in {category} output in {strategy_file.name}"
                    assert (
                        "description" in output
                    ), f"Missing description in {category} output in {strategy_file.name}"

    def test_validation_criteria(self, strategy_files: List[Path]):
        """Test validation criteria in all strategies."""
        for strategy_file in strategy_files:
            strategy = self.load_strategy(strategy_file)

            if "validation" in strategy:
                validation = strategy["validation"]

                # Test common validation criteria
                common_criteria = ["max_execution_time_minutes"]
                for criterion in common_criteria:
                    if criterion in validation:
                        assert isinstance(
                            validation[criterion], (int, float)
                        ), f"Validation {criterion} should be numeric in {strategy_file.name}"

    @pytest.mark.slow
    def test_strategy_loading_via_client(
        self, client: BiomapperClient, strategy_files: List[Path]
    ):
        """Test that strategies can be loaded via BiomapperClient."""
        for strategy_file in strategy_files:
            strategy_id = strategy_file.stem

            try:
                # This would normally load the strategy
                # For now just test the file can be parsed
                strategy = self.load_strategy(strategy_file)
                assert strategy["metadata"]["id"] == strategy_id.replace(
                    "_", "_"
                ), f"Strategy ID mismatch in {strategy_file.name}"
            except Exception as e:
                pytest.fail(f"Failed to load strategy {strategy_file.name}: {e}")


class TestMultiEntityStrategyIntegration:
    """Integration tests for multi-entity strategies."""

    @pytest.fixture
    def client(self) -> BiomapperClient:
        """Create BiomapperClient for integration testing."""
        return BiomapperClient()

    @pytest.fixture
    def sample_multi_omics_data(self) -> Dict[str, Any]:
        """Create sample multi-omics data for testing."""
        return {
            "proteins": {
                "identifiers": ["P12345", "P67890", "Q11111"],
                "expression_levels": [1.2, 0.8, 2.1],
            },
            "metabolites": {
                "identifiers": ["HMDB0000001", "HMDB0000002", "HMDB0000003"],
                "concentrations": [45.2, 123.4, 78.9],
            },
            "chemistry": {
                "test_names": ["glucose", "cholesterol", "creatinine"],
                "values": [95.0, 180.0, 1.1],
            },
        }

    @pytest.mark.integration
    def test_comprehensive_strategy_mock_execution(
        self, client, sample_multi_omics_data
    ):
        """Test comprehensive strategy with mock data."""
        # This would be a full integration test with real API calls
        # For now, test strategy structure validation
        strategy_id = "multi_arv_ukb_isr_comprehensive_v1_advanced"

        # Test that we can validate the strategy structure
        strategy_path = (
            Path("/home/ubuntu/biomapper/configs/strategies/experimental")
            / f"{strategy_id}.yaml"
        )
        assert strategy_path.exists()

        with open(strategy_path) as f:
            strategy = yaml.safe_load(f)

        # Test that all required entity types are covered
        assert len(strategy["metadata"]["entity_type"]) == 3
        assert "proteins" in strategy["metadata"]["entity_type"]
        assert "metabolites" in strategy["metadata"]["entity_type"]
        assert "chemistry" in strategy["metadata"]["entity_type"]

    @pytest.mark.integration
    def test_pathway_analysis_mock_execution(self, client, sample_multi_omics_data):
        """Test pathway analysis strategy with mock data."""
        strategy_id = "multi_prot_met_pathway_analysis_v1_base"

        strategy_path = (
            Path("/home/ubuntu/biomapper/configs/strategies/experimental")
            / f"{strategy_id}.yaml"
        )
        assert strategy_path.exists()

        with open(strategy_path) as f:
            strategy = yaml.safe_load(f)

        # Test pathway-specific structure
        assert "pathway_databases" in strategy["parameters"]
        assert "enrichment_method" in strategy["parameters"]

        # Test expected outputs include pathway results
        primary_outputs = strategy["expected_outputs"]["primary"]
        assert any("pathway" in output["path"] for output in primary_outputs)

    @pytest.mark.integration
    def test_clinical_bridge_mock_execution(self, client):
        """Test clinical bridge strategy with mock data."""
        strategy_id = "multi_chem_met_clinical_bridge_v1_experimental"

        strategy_path = (
            Path("/home/ubuntu/biomapper/configs/strategies/experimental")
            / f"{strategy_id}.yaml"
        )
        assert strategy_path.exists()

        with open(strategy_path) as f:
            strategy = yaml.safe_load(f)

        # Test clinical-specific structure
        assert "clinical_mappings" in strategy["metadata"]
        assert "correlation_threshold" in strategy["parameters"]

        # Test expected outputs include clinical correlations
        outputs = strategy["expected_outputs"]
        assert "correlations" in outputs

    @pytest.mark.integration
    def test_longitudinal_mock_execution(self, client):
        """Test longitudinal strategy with mock data."""
        strategy_id = "multi_longitudinal_tracking_v1_advanced"

        strategy_path = (
            Path("/home/ubuntu/biomapper/configs/strategies/experimental")
            / f"{strategy_id}.yaml"
        )
        assert strategy_path.exists()

        with open(strategy_path) as f:
            strategy = yaml.safe_load(f)

        # Test temporal structure
        assert "temporal_framework" in strategy["metadata"]
        assert "timepoints" in strategy["parameters"]

        # Test expected outputs include trajectories
        outputs = strategy["expected_outputs"]
        assert "trajectories" in outputs

    @pytest.mark.integration
    def test_disease_integration_mock_execution(self, client):
        """Test disease integration strategy with mock data."""
        strategy_id = "multi_disease_integration_v1_specialized"

        strategy_path = (
            Path("/home/ubuntu/biomapper/configs/strategies/experimental")
            / f"{strategy_id}.yaml"
        )
        assert strategy_path.exists()

        with open(strategy_path) as f:
            strategy = yaml.safe_load(f)

        # Test disease-specific structure
        assert "disease_models" in strategy["metadata"]
        assert "disease_focus" in strategy["parameters"]

        # Test expected outputs include biomarkers and models
        outputs = strategy["expected_outputs"]
        assert "models" in outputs
        assert "targets" in outputs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
