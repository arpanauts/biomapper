"""Tests for results_manager.py."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from core.results_manager import (
    ResultsPathManager,
    LocalResultsOrganizer,
    get_organized_output_path,
    setup_strategy_output_paths
)


class TestResultsPathManager:
    """Test ResultsPathManager functionality."""
    
    def test_extract_strategy_base_with_version_suffix(self):
        """Test extracting base strategy name with version suffix."""
        test_cases = [
            ("metabolite_protein_integration_v2_enhanced", "metabolite_protein_integration"),
            ("custom_strategy_v1_base", "custom_strategy"),
            ("complex_mapping_v3_advanced", "complex_mapping"),
            ("simple_test_v10_experimental", "simple_test")
        ]
        
        for input_name, expected_base in test_cases:
            result = ResultsPathManager.extract_strategy_base(input_name)
            assert result == expected_base
    
    def test_extract_strategy_base_simple_version(self):
        """Test extracting base with simple version pattern."""
        test_cases = [
            ("strategy_v1", "strategy"),
            ("mapping_v2", "mapping"),
            ("analysis_v10", "analysis")
        ]
        
        for input_name, expected_base in test_cases:
            result = ResultsPathManager.extract_strategy_base(input_name)
            assert result == expected_base
    
    def test_extract_strategy_base_no_version(self):
        """Test extracting base without version suffix."""
        test_cases = [
            ("simple_strategy", "simple_strategy"),
            ("protein_mapping", "protein_mapping"),
            ("metabolomics_analysis", "metabolomics_analysis")
        ]
        
        for input_name, expected_base in test_cases:
            result = ResultsPathManager.extract_strategy_base(input_name)
            assert result == expected_base
    
    def test_extract_strategy_base_edge_cases(self):
        """Test edge cases for strategy base extraction."""
        # Empty string
        assert ResultsPathManager.extract_strategy_base("") == ""
        
        # Version-like patterns that shouldn't match
        assert ResultsPathManager.extract_strategy_base("strategy_version_1") == "strategy_version_1"
        assert ResultsPathManager.extract_strategy_base("test_v") == "test_v"
        assert ResultsPathManager.extract_strategy_base("test_v_base") == "test_v_base"
    
    def test_format_version_folder(self):
        """Test version folder formatting."""
        test_cases = [
            ("1.0.0", "v1_0_0"),
            ("2.1.0", "v2_1_0"),
            ("2.1.0-beta", "v2_1_0-beta"),
            ("v3.0.0", "v3_0_0"),  # Already has 'v' prefix
            ("1.5.2-alpha.1", "v1_5_2-alpha.1")
        ]
        
        for input_version, expected_folder in test_cases:
            result = ResultsPathManager.format_version_folder(input_version)
            assert result == expected_folder
    
    def test_get_organized_path_basic(self):
        """Test basic organized path generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = ResultsPathManager.get_organized_path(
                strategy_name="protein_mapping_v1_base",
                version="1.0.0",
                base_dir=temp_dir,
                include_timestamp=False
            )
            
            expected = Path(temp_dir) / "protein_mapping" / "v1_0_0"
            assert path == expected
    
    def test_get_organized_path_with_timestamp(self):
        """Test organized path generation with timestamp."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('core.results_manager.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20250118_143000"
                
                path = ResultsPathManager.get_organized_path(
                    strategy_name="metabolite_analysis",
                    version="2.1.0",
                    base_dir=temp_dir,
                    include_timestamp=True
                )
                
                expected = Path(temp_dir) / "metabolite_analysis" / "v2_1_0" / "run_20250118_143000"
                assert path == expected
    
    def test_get_organized_path_default_base_dir(self):
        """Test organized path with default base directory."""
        path = ResultsPathManager.get_organized_path(
            strategy_name="test_strategy",
            version="1.0.0"
        )
        
        expected_base = Path(ResultsPathManager.LOCAL_RESULTS_BASE)
        assert path.parent.parent == expected_base
        assert path.name == "v1_0_0"
    
    def test_get_organized_path_custom_timestamp_format(self):
        """Test organized path with custom timestamp format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('core.results_manager.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "2025-01-18"
                
                path = ResultsPathManager.get_organized_path(
                    strategy_name="test_strategy",
                    version="1.0.0",
                    base_dir=temp_dir,
                    include_timestamp=True,
                    timestamp_format="%Y-%m-%d"
                )
                
                expected = Path(temp_dir) / "test_strategy" / "v1_0_0" / "run_2025-01-18"
                assert path == expected
    
    def test_ensure_directory(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "nested" / "directory" / "structure"
            
            result = ResultsPathManager.ensure_directory(test_path)
            
            assert result == test_path
            assert test_path.exists()
            assert test_path.is_dir()
    
    def test_ensure_directory_existing(self):
        """Test ensure_directory with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_path = Path(temp_dir) / "existing"
            existing_path.mkdir()
            
            result = ResultsPathManager.ensure_directory(existing_path)
            
            assert result == existing_path
            assert existing_path.exists()
    
    def test_get_output_filepath(self):
        """Test output filepath generation."""
        base_path = Path("/tmp/results/strategy/v1_0_0")
        filename = "mapping_results.tsv"
        
        result = ResultsPathManager.get_output_filepath(base_path, filename)
        
        expected = base_path / filename
        assert result == expected
    
    def test_describe_structure(self):
        """Test structure description."""
        result = ResultsPathManager.describe_structure(
            strategy_name="protein_analysis_v2_enhanced",
            version="1.5.0",
            include_timestamp=False
        )
        
        assert result == "protein_analysis/v1_5_0"
    
    def test_describe_structure_with_timestamp(self):
        """Test structure description with timestamp."""
        result = ResultsPathManager.describe_structure(
            strategy_name="metabolite_mapping",
            version="2.0.0",
            include_timestamp=True
        )
        
        assert result == "metabolite_mapping/v2_0_0/run_[timestamp]"
    
    def test_get_context_with_paths(self):
        """Test context update with organized paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            organized_path = Path(temp_dir) / "strategy_base" / "v1_0_0" / "run_20250118"
            organized_path.mkdir(parents=True)
            
            context = {"existing_key": "existing_value"}
            
            result = ResultsPathManager.get_context_with_paths(context, organized_path)
            
            assert result["organized_output_path"] == str(organized_path)
            assert result["existing_key"] == "existing_value"
            
            structure = result["organized_structure"]
            assert structure["strategy"] == "strategy_base"
            assert structure["version"] == "v1_0_0"
            assert structure["run"] == "run_20250118"
    
    def test_get_context_with_paths_no_run_folder(self):
        """Test context update without run folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            organized_path = Path(temp_dir) / "strategy_base" / "v1_0_0"
            organized_path.mkdir(parents=True)
            
            context = {}
            
            result = ResultsPathManager.get_context_with_paths(context, organized_path)
            
            structure = result["organized_structure"]
            assert structure["run"] is None


@pytest.fixture
def temp_organizer():
    """Create organizer with temporary directory."""
    temp_dir = tempfile.mkdtemp()
    organizer = LocalResultsOrganizer(base_dir=temp_dir)
    yield organizer, temp_dir
    shutil.rmtree(temp_dir)


class TestLocalResultsOrganizer:
    """Test LocalResultsOrganizer functionality."""
    
    def test_initialization_default_base_dir(self):
        """Test initialization with default base directory."""
        organizer = LocalResultsOrganizer()
        
        assert organizer.base_dir == ResultsPathManager.LOCAL_RESULTS_BASE
        assert isinstance(organizer.path_manager, ResultsPathManager)
    
    def test_initialization_custom_base_dir(self):
        """Test initialization with custom base directory."""
        custom_dir = "/tmp/custom_biomapper"
        organizer = LocalResultsOrganizer(base_dir=custom_dir)
        
        assert organizer.base_dir == custom_dir
    
    def test_prepare_strategy_output(self, temp_organizer):
        """Test preparing strategy output directory."""
        organizer, temp_dir = temp_organizer
        
        with patch('core.results_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20250118_143000"
            
            result_path = organizer.prepare_strategy_output(
                strategy_name="protein_mapping_v1_base",
                version="1.0.0",
                include_timestamp=True
            )
            
            expected_path = Path(temp_dir) / "protein_mapping" / "v1_0_0" / "run_20250118_143000"
            assert result_path == expected_path
            assert result_path.exists()
            assert result_path.is_dir()
    
    def test_prepare_strategy_output_no_timestamp(self, temp_organizer):
        """Test preparing strategy output without timestamp."""
        organizer, temp_dir = temp_organizer
        
        result_path = organizer.prepare_strategy_output(
            strategy_name="metabolite_analysis",
            version="2.0.0",
            include_timestamp=False
        )
        
        expected_path = Path(temp_dir) / "metabolite_analysis" / "v2_0_0"
        assert result_path == expected_path
        assert result_path.exists()
    
    def test_get_latest_run_no_runs(self, temp_organizer):
        """Test get_latest_run with no existing runs."""
        organizer, temp_dir = temp_organizer
        
        result = organizer.get_latest_run("nonexistent_strategy", "1.0.0")
        
        assert result is None
    
    def test_get_latest_run_with_runs(self, temp_organizer):
        """Test get_latest_run with existing runs."""
        organizer, temp_dir = temp_organizer
        
        # Create strategy directory structure
        strategy_path = Path(temp_dir) / "test_strategy" / "v1_0_0"
        strategy_path.mkdir(parents=True)
        
        # Create multiple run directories
        runs = ["run_20250118_120000", "run_20250118_130000", "run_20250118_140000"]
        for run in runs:
            (strategy_path / run).mkdir()
        
        result = organizer.get_latest_run("test_strategy", "1.0.0")
        
        # Should return the latest (last alphabetically)
        expected = strategy_path / "run_20250118_140000"
        assert result == expected
    
    def test_get_latest_run_mixed_directories(self, temp_organizer):
        """Test get_latest_run ignores non-run directories."""
        organizer, temp_dir = temp_organizer
        
        strategy_path = Path(temp_dir) / "test_strategy" / "v1_0_0"
        strategy_path.mkdir(parents=True)
        
        # Create mix of run and non-run directories
        (strategy_path / "run_20250118_120000").mkdir()
        (strategy_path / "run_20250118_140000").mkdir()
        (strategy_path / "other_directory").mkdir()
        (strategy_path / "run_20250118_130000").mkdir()
        
        result = organizer.get_latest_run("test_strategy", "1.0.0")
        
        expected = strategy_path / "run_20250118_140000"
        assert result == expected
    
    def test_list_strategy_runs_no_strategy(self, temp_organizer):
        """Test list_strategy_runs with nonexistent strategy."""
        organizer, temp_dir = temp_organizer
        
        result = organizer.list_strategy_runs("nonexistent_strategy")
        
        assert result == {}
    
    def test_list_strategy_runs_with_versions(self, temp_organizer):
        """Test list_strategy_runs with multiple versions."""
        organizer, temp_dir = temp_organizer
        
        # Create multi-version strategy structure
        strategy_base = Path(temp_dir) / "multi_version_strategy"
        
        # Version 1.0.0
        v1_path = strategy_base / "v1_0_0"
        v1_path.mkdir(parents=True)
        (v1_path / "run_20250118_120000").mkdir()
        (v1_path / "run_20250118_130000").mkdir()
        
        # Version 2.0.0
        v2_path = strategy_base / "v2_0_0"
        v2_path.mkdir(parents=True)
        (v2_path / "run_20250118_140000").mkdir()
        
        result = organizer.list_strategy_runs("multi_version_strategy")
        
        assert "v1_0_0" in result
        assert "v2_0_0" in result
        assert len(result["v1_0_0"]) == 2
        assert len(result["v2_0_0"]) == 1
        assert "run_20250118_140000" in result["v2_0_0"]
    
    def test_clean_old_runs(self, temp_organizer):
        """Test cleaning old run directories."""
        organizer, temp_dir = temp_organizer
        
        # Create strategy with multiple runs
        strategy_path = Path(temp_dir) / "cleanup_test" / "v1_0_0"
        strategy_path.mkdir(parents=True)
        
        runs = [
            "run_20250118_100000",
            "run_20250118_110000", 
            "run_20250118_120000",
            "run_20250118_130000",
            "run_20250118_140000"
        ]
        
        for run in runs:
            run_path = strategy_path / run
            run_path.mkdir()
            # Create a file to make deletion meaningful
            (run_path / "test_file.txt").write_text("test content")
        
        # Clean, keeping only latest 3
        deleted_count = organizer.clean_old_runs("cleanup_test", "1.0.0", keep_latest=3)
        
        assert deleted_count == 2
        
        # Check which runs remain
        remaining_runs = [d.name for d in strategy_path.iterdir() if d.is_dir()]
        remaining_runs.sort()
        
        expected_remaining = ["run_20250118_120000", "run_20250118_130000", "run_20250118_140000"]
        assert remaining_runs == expected_remaining
    
    def test_clean_old_runs_no_strategy(self, temp_organizer):
        """Test clean_old_runs with nonexistent strategy."""
        organizer, temp_dir = temp_organizer
        
        deleted_count = organizer.clean_old_runs("nonexistent", "1.0.0")
        
        assert deleted_count == 0
    
    def test_clean_old_runs_fewer_than_keep_latest(self, temp_organizer):
        """Test clean_old_runs with fewer runs than keep_latest."""
        organizer, temp_dir = temp_organizer
        
        # Create strategy with only 2 runs
        strategy_path = Path(temp_dir) / "few_runs" / "v1_0_0"
        strategy_path.mkdir(parents=True)
        
        (strategy_path / "run_20250118_120000").mkdir()
        (strategy_path / "run_20250118_130000").mkdir()
        
        # Try to keep 5, but only have 2
        deleted_count = organizer.clean_old_runs("few_runs", "1.0.0", keep_latest=5)
        
        assert deleted_count == 0
        assert len([d for d in strategy_path.iterdir() if d.is_dir()]) == 2


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_organized_output_path_with_organized(self):
        """Test get_organized_output_path with organized structure."""
        context = {
            "organized_output_path": "/results/strategy/v1_0_0/run_123"
        }
        
        result = get_organized_output_path(context, "output.tsv", use_organized=True)
        
        assert result == "/results/strategy/v1_0_0/run_123/output.tsv"
    
    def test_get_organized_output_path_fallback_to_output_dir(self):
        """Test fallback to parameters.output_dir."""
        context = {
            "parameters": {
                "output_dir": "/custom/output"
            }
        }
        
        result = get_organized_output_path(context, "results.csv", use_organized=True)
        
        assert result == "/custom/output/results.csv"
    
    def test_get_organized_output_path_default_fallback(self):
        """Test default fallback path."""
        context = {}
        
        result = get_organized_output_path(context, "data.txt", use_organized=True)
        
        assert result == "/tmp/biomapper/output/data.txt"
    
    def test_get_organized_output_path_disable_organized(self):
        """Test with organized structure disabled."""
        context = {
            "organized_output_path": "/organized/path",
            "parameters": {
                "output_dir": "/custom/output"
            }
        }
        
        result = get_organized_output_path(context, "file.txt", use_organized=False)
        
        assert result == "/custom/output/file.txt"
    
    def test_setup_strategy_output_paths(self):
        """Test setup_strategy_output_paths function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            context = {
                "strategy_name": "test_strategy_v1_base",
                "strategy_metadata": {"version": "1.2.0"},
                "parameters": {"output_dir": temp_dir}
            }
            
            with patch('core.results_manager.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20250118_143000"
                
                result_context = setup_strategy_output_paths(context, include_timestamp=True)
            
            assert "organized_output_path" in result_context
            assert "organized_structure" in result_context
            
            expected_path = Path(temp_dir) / "test_strategy" / "v1_2_0" / "run_20250118_143000"
            assert result_context["organized_output_path"] == str(expected_path)
            assert expected_path.exists()
    
    def test_setup_strategy_output_paths_defaults(self):
        """Test setup_strategy_output_paths with defaults."""
        context = {}
        
        with patch.object(ResultsPathManager, 'ensure_directory') as mock_ensure:
            mock_ensure.return_value = Path("/mocked/path")
            
            result_context = setup_strategy_output_paths(context)
        
        assert result_context["strategy_name"] == "unknown_strategy"
        assert "organized_output_path" in result_context
        assert "organized_structure" in result_context
    
    def test_setup_strategy_output_paths_no_timestamp(self):
        """Test setup without timestamp."""
        with tempfile.TemporaryDirectory() as temp_dir:
            context = {
                "strategy_name": "no_timestamp_test",
                "strategy_metadata": {"version": "1.0.0"},
                "parameters": {"output_dir": temp_dir}
            }
            
            result_context = setup_strategy_output_paths(context, include_timestamp=False)
            
            expected_path = Path(temp_dir) / "no_timestamp_test" / "v1_0_0"
            assert result_context["organized_output_path"] == str(expected_path)
            assert expected_path.exists()


class TestBiologicalDataIntegration:
    """Test integration with biological data patterns."""
    
    def test_protein_mapping_strategy_organization(self, temp_organizer):
        """Test organization for protein mapping strategies."""
        organizer, temp_dir = temp_organizer
        
        # Simulate protein mapping strategy
        strategy_name = "uniprot_to_ensembl_mapping_v2_enhanced"
        version = "2.1.0"
        
        output_path = organizer.prepare_strategy_output(
            strategy_name=strategy_name,
            version=version,
            include_timestamp=True
        )
        
        # Verify path structure
        assert "uniprot_to_ensembl_mapping" in str(output_path)
        assert "v2_1_0" in str(output_path)
        assert output_path.exists()
        
        # Test context integration
        context = {
            "strategy_name": strategy_name,
            "strategy_metadata": {"version": version},
            "datasets": {
                "uniprot_proteins": ["P12345", "Q9Y6R4", "O15552"],
                "ensembl_genes": ["ENSG00000141510", "ENSG00000139618"]
            }
        }
        
        updated_context = ResultsPathManager.get_context_with_paths(context, output_path)
        
        assert updated_context["organized_output_path"] == str(output_path)
        assert updated_context["datasets"]["uniprot_proteins"] == ["P12345", "Q9Y6R4", "O15552"]
    
    def test_metabolomics_workflow_organization(self, temp_organizer):
        """Test organization for metabolomics workflows."""
        organizer, temp_dir = temp_organizer
        
        strategy_name = "hmdb_to_kegg_metabolite_mapping_v1_base"
        version = "1.0.0"
        
        # Create organized structure
        output_path = organizer.prepare_strategy_output(
            strategy_name=strategy_name,
            version=version,
            include_timestamp=False
        )
        
        # Simulate metabolomics data context
        context = {
            "strategy_name": strategy_name,
            "current_identifiers": ["HMDB0000001", "HMDB0000123", "HMDB0006456"],
            "statistics": {
                "total_metabolites": 3,
                "successful_mappings": 2,
                "mapping_rate": 0.67
            }
        }
        
        # Test file path generation
        results_file = get_organized_output_path(
            {**context, "organized_output_path": str(output_path)},
            "metabolite_mapping_results.tsv"
        )
        
        expected_file = output_path / "metabolite_mapping_results.tsv"
        assert results_file == str(expected_file)
    
    def test_multi_omics_integration_organization(self, temp_organizer):
        """Test organization for multi-omics integration."""
        organizer, temp_dir = temp_organizer
        
        strategy_name = "multi_omics_protein_metabolite_integration_v3_advanced"
        version = "3.0.0-beta"
        
        output_path = organizer.prepare_strategy_output(
            strategy_name=strategy_name,
            version=version,
            include_timestamp=True
        )
        
        # Test complex biological context
        context = {
            "strategy_name": strategy_name,
            "strategy_metadata": {
                "version": version,
                "data_types": ["proteins", "metabolites", "pathways"]
            },
            "datasets": {
                "proteins": {
                    "uniprot_ids": ["P12345", "Q9Y6R4"],
                    "gene_symbols": ["TP53", "BRCA1"]
                },
                "metabolites": {
                    "hmdb_ids": ["HMDB0000001", "HMDB0000123"],
                    "compound_names": ["1-Methylhistidine", "Acetylcarnitine"]
                },
                "pathways": {
                    "kegg_pathways": ["hsa04110", "hsa04151"],
                    "reactome_pathways": ["R-HSA-1428517", "R-HSA-73857"]
                }
            },
            "statistics": {
                "total_entities": 8,
                "cross_references_found": 12,
                "integration_score": 0.85
            }
        }
        
        updated_context = ResultsPathManager.get_context_with_paths(context, output_path)
        
        # Verify all context is preserved
        assert updated_context["datasets"]["proteins"]["uniprot_ids"] == ["P12345", "Q9Y6R4"]
        assert updated_context["datasets"]["metabolites"]["hmdb_ids"] == ["HMDB0000001", "HMDB0000123"]
        assert updated_context["statistics"]["integration_score"] == 0.85
        assert "organized_output_path" in updated_context
    
    def test_version_management_across_data_types(self, temp_organizer):
        """Test version management across different biological data types."""
        organizer, temp_dir = temp_organizer
        
        # Create multiple strategies with different data types
        strategies = [
            ("protein_uniprot_normalization_v1_base", "1.0.0"),
            ("protein_uniprot_normalization_v1_enhanced", "1.1.0"),
            ("protein_uniprot_normalization_v2_base", "2.0.0"),
            ("metabolite_hmdb_enrichment_v1_base", "1.0.0")
        ]
        
        created_paths = []
        for strategy_name, version in strategies:
            path = organizer.prepare_strategy_output(
                strategy_name=strategy_name,
                version=version,
                include_timestamp=False
            )
            created_paths.append(path)
        
        # Test version listing for protein normalization
        runs = organizer.list_strategy_runs("protein_uniprot_normalization_v1_base")
        
        # Should find different versions
        protein_base = Path(temp_dir) / "protein_uniprot_normalization"
        assert protein_base.exists()
        
        version_dirs = [d.name for d in protein_base.iterdir() if d.is_dir()]
        expected_versions = ["v1_0_0", "v1_1_0", "v2_0_0"]
        
        for expected_version in expected_versions:
            assert expected_version in version_dirs
    
    def test_large_scale_biological_data_paths(self, temp_organizer):
        """Test path management for large-scale biological datasets."""
        organizer, temp_dir = temp_organizer
        
        # Simulate large-scale genomics study
        strategy_name = "large_scale_proteogenomics_analysis_v1_production"
        version = "1.0.0"
        
        output_path = organizer.prepare_strategy_output(
            strategy_name=strategy_name,
            version=version,
            include_timestamp=True
        )
        
        # Simulate large dataset context
        large_context = {
            "strategy_name": strategy_name,
            "strategy_metadata": {
                "version": version,
                "study_type": "proteogenomics",
                "sample_count": 10000,
                "data_size_gb": 500
            },
            "datasets": {
                "proteins": {f"protein_{i}": f"P{str(i).zfill(5)}" for i in range(1000)},
                "genes": {f"gene_{i}": f"ENSG{str(i).zfill(11)}" for i in range(1000)},
                "metabolites": {f"metabolite_{i}": f"HMDB{str(i).zfill(7)}" for i in range(500)}
            },
            "statistics": {
                "total_identifiers": 2500,
                "processing_time_hours": 24,
                "memory_usage_gb": 64
            }
        }
        
        # Test path generation for multiple output files
        output_files = [
            "protein_gene_mappings.tsv",
            "metabolite_pathway_associations.csv",
            "integration_statistics.json",
            "quality_control_report.html"
        ]
        
        for filename in output_files:
            file_path = get_organized_output_path(
                {**large_context, "organized_output_path": str(output_path)},
                filename
            )
            expected_path = output_path / filename
            assert file_path == str(expected_path)
        
        # Verify directory structure can handle large datasets
        updated_context = ResultsPathManager.get_context_with_paths(large_context, output_path)
        
        assert len(updated_context["datasets"]["proteins"]) == 1000
        assert len(updated_context["datasets"]["genes"]) == 1000
        assert len(updated_context["datasets"]["metabolites"]) == 500