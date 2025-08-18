import pytest
from pathlib import Path
import yaml
from unittest.mock import patch
import sys


pytestmark = pytest.mark.requires_external_services

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Skip this test file until the pipeline classes are implemented
pytest.skip("Pipeline classes not yet implemented", allow_module_level=True)

# These imports will be used once the classes are implemented
# from scripts.main_pipelines.run_metabolomics_harmonization import (
#     MetabolomicsHarmonizationPipeline,
#     DockerManager
# )


class TestMetabolomicsPipeline:
    """Test suite for metabolomics pipeline - WRITE FIRST!"""

    @pytest.fixture
    def sample_config(self, tmp_path):
        """Create sample configuration."""
        config = {
            "name": "TEST_PIPELINE",
            "description": "Test pipeline",
            "parameters": {
                "israeli10k_file": str(tmp_path / "israeli10k.csv"),
                "ukbb_file": str(tmp_path / "ukbb.tsv"),
                "arivale_file": str(tmp_path / "arivale.tsv"),
                "nightingale_reference_csv": str(tmp_path / "nightingale_ref.csv"),
                "final_report_path": str(tmp_path / "report.md"),
                "qdrant_config": {
                    "url": "localhost:6333",
                    "collection": "hmdb_metabolites",
                },
            },
            "steps": [
                {
                    "name": "test_step",
                    "action": {
                        "type": "LOAD_DATASET_IDENTIFIERS",
                        "params": {"file_path": "${parameters.israeli10k_file}"},
                    },
                }
            ],
        }

        config_path = tmp_path / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return config_path

    def test_config_loading(self, sample_config):
        """Test configuration loading and validation."""
        pipeline = MetabolomicsHarmonizationPipeline(
            config_path=sample_config, skip_setup=True, skip_qdrant=True
        )

        assert pipeline.config["name"] == "TEST_PIPELINE"
        assert "parameters" in pipeline.config
        assert len(pipeline.config["steps"]) == 1

    def test_parameter_interpolation(self, sample_config):
        """Test ${parameters.x} interpolation."""
        pipeline = MetabolomicsHarmonizationPipeline(
            config_path=sample_config, skip_setup=True, skip_qdrant=True
        )

        # Test string interpolation
        test_str = "${parameters.israeli10k_file}"
        result = pipeline._interpolate_parameters(test_str)
        assert result.endswith("israeli10k.csv")

        # Test nested interpolation
        test_dict = {
            "path": "${parameters.ukbb_file}",
            "nested": {"value": "${parameters.arivale_file}"},
        }
        result = pipeline._interpolate_parameters(test_dict)
        assert result["path"].endswith("ukbb.tsv")
        assert result["nested"]["value"].endswith("arivale.tsv")

    @pytest.mark.asyncio
    async def test_prerequisite_checks(self, sample_config, tmp_path):
        """Test prerequisite checking."""
        # Create dummy files
        (tmp_path / "israeli10k.csv").write_text("col1,col2\n1,2\n")
        (tmp_path / "ukbb.tsv").write_text("col1\tcol2\n1\t2\n")
        (tmp_path / "arivale.tsv").write_text("col1\tcol2\n1\t2\n")

        pipeline = MetabolomicsHarmonizationPipeline(
            config_path=sample_config, skip_setup=True, skip_qdrant=True
        )

        # Mock API checks
        with patch.object(pipeline, "_check_cts_api", return_value=True):
            result = await pipeline.check_prerequisites()
            assert result is True

    def test_stage_filtering(self, sample_config):
        """Test filtering steps by stage."""
        pipeline = MetabolomicsHarmonizationPipeline(
            config_path=sample_config, skip_setup=True, skip_qdrant=True
        )

        # Create test steps
        all_steps = [
            {"name": "load_israeli10k"},
            {"name": "baseline_arivale_match"},
            {"name": "cts_enrichment"},
            {"name": "vector_enhancement"},
        ]

        # Test baseline filter
        baseline_steps = pipeline._filter_steps_by_stage(all_steps, "baseline")
        assert any(s["name"] == "baseline_arivale_match" for s in baseline_steps)
        assert not any(s["name"] == "cts_enrichment" for s in baseline_steps)

    def test_docker_manager(self):
        """Test Docker container management."""
        from biomapper.utils.docker_utils import DockerManager

        manager = DockerManager()

        # Mock subprocess calls
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            result = manager.start_qdrant()
            assert result is True

            # Verify docker command was called
            calls = mock_run.call_args_list
            assert any("docker" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_progress_logging(self, sample_config, caplog):
        """Test progress metrics logging."""
        pipeline = MetabolomicsHarmonizationPipeline(
            config_path=sample_config, skip_setup=True, skip_qdrant=True
        )

        # Create test context with metrics
        context = {
            "metrics": {
                "baseline": {"match_rate": 0.45, "matched": 450},
                "api_enriched": {"match_rate": 0.60, "total_matched": 600},
            }
        }

        pipeline._log_progress(context)

        # Check log output
        assert "baseline: 450 matches (45.0%)" in caplog.text
        assert "api_enriched: 600 matches (60.0%)" in caplog.text
