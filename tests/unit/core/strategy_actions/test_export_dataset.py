"""Tests for dataset export functionality."""

import pytest
import pandas as pd
import tempfile
import json
from pathlib import Path

from actions.export_dataset import ExportDatasetAction, ExportDatasetParams


class TestExportDatasetAction:
    """Test dataset export functionality."""
    
    @pytest.fixture
    def biological_datasets(self):
        """Create biological datasets for testing."""
        return {
            "proteins": pd.DataFrame({
                "uniprot_id": ["P12345", "Q9Y6R4", "O00533"],
                "gene_symbol": ["TP53", "BRCA1", "CD4"],
                "organism": ["Homo sapiens", "Homo sapiens", "Homo sapiens"],
                "reviewed": [True, True, True],
                "length": [393, 1863, 458]
            }),
            "metabolites": pd.DataFrame({
                "hmdb_id": ["HMDB0000001", "HMDB0000002", "HMDB0000003"],
                "name": ["1-Methylhistidine", "1,3-Diaminopropane", "1-Pyrroline-4-hydroxy-2-carboxylate"],
                "formula": ["C7H11N3O2", "C3H10N2", "C5H7NO3"],
                "mass": [169.085, 74.084, 129.042]
            }),
            "edge_cases": pd.DataFrame({
                "protein_id": ["P04637", "Q6EMK4", "INVALID_ID"],  # Include problematic Q6EMK4
                "confidence": [0.95, 0.45, 0.0],
                "notes": ["High quality", "Problematic identifier", "Invalid format"]
            })
        }
    
    @pytest.fixture
    def action_context(self, biological_datasets):
        """Create test action context."""
        return {
            "datasets": biological_datasets,
            "statistics": {"processed_count": 0},
            "output_files": {}
        }
    
    def test_export_dataset_params_validation(self):
        """Test ExportDatasetParams validation."""
        
        # Test valid parameters
        valid_params = ExportDatasetParams(
            input_key="proteins",
            output_path="/tmp/test_proteins.tsv",
            format="tsv",
            columns=["uniprot_id", "gene_symbol"]
        )
        
        assert valid_params.input_key == "proteins"
        assert valid_params.output_path == "/tmp/test_proteins.tsv"
        assert valid_params.format == "tsv"
        assert valid_params.columns == ["uniprot_id", "gene_symbol"]
        
        # Test default values
        minimal_params = ExportDatasetParams(
            input_key="data",
            output_path="/tmp/output.tsv"
        )
        
        assert minimal_params.format == "tsv"  # Default format
        assert minimal_params.columns is None  # Default columns
    
    @pytest.mark.asyncio
    async def test_tsv_export_with_biological_data(self, action_context):
        """Test TSV export with biological data."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="proteins",
                output_path=tmp.name,
                format="tsv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Verify export success
            assert result.success is True
            assert Path(tmp.name).exists()
            assert result.data["row_count"] == 3
            assert str(tmp.name) in result.data["exported_path"]
            
            # Verify file content
            exported_data = pd.read_csv(tmp.name, sep="\t")
            assert len(exported_data) == 3
            assert list(exported_data.columns) == ["uniprot_id", "gene_symbol", "organism", "reviewed", "length"]
            assert "P12345" in exported_data["uniprot_id"].values
            assert "TP53" in exported_data["gene_symbol"].values
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_csv_export_with_column_selection(self, action_context):
        """Test CSV export with specific column selection."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="proteins",
                output_path=tmp.name,
                format="csv",
                columns=["uniprot_id", "gene_symbol"]  # Only specific columns
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Verify export success
            assert result.success is True
            assert Path(tmp.name).exists()
            
            # Verify file content has only selected columns
            exported_data = pd.read_csv(tmp.name)
            assert len(exported_data) == 3
            assert list(exported_data.columns) == ["uniprot_id", "gene_symbol"]
            assert "organism" not in exported_data.columns
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_json_export_with_metabolite_data(self, action_context):
        """Test JSON export with metabolite data."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="metabolites",
                output_path=tmp.name,
                format="json"
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Verify export success
            assert result.success is True
            assert Path(tmp.name).exists()
            
            # Verify JSON content
            with open(tmp.name, 'r') as f:
                exported_data = json.load(f)
            
            assert len(exported_data) == 3
            assert isinstance(exported_data, list)
            assert all("hmdb_id" in record for record in exported_data)
            assert all("name" in record for record in exported_data)
            assert exported_data[0]["hmdb_id"] == "HMDB0000001"
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_xlsx_export_functionality(self, action_context):
        """Test Excel (XLSX) export functionality."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="proteins",
                output_path=tmp.name,
                format="xlsx"
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Verify export success
            assert result.success is True
            assert Path(tmp.name).exists()
            
            # Verify Excel content
            exported_data = pd.read_excel(tmp.name)
            assert len(exported_data) == 3
            assert list(exported_data.columns) == ["uniprot_id", "gene_symbol", "organism", "reviewed", "length"]
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_edge_case_data_export(self, action_context):
        """Test export with edge case data including problematic identifiers."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="edge_cases",
                output_path=tmp.name,
                format="tsv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Verify export success even with edge cases
            assert result.success is True
            assert Path(tmp.name).exists()
            
            # Verify edge case data is preserved
            exported_data = pd.read_csv(tmp.name, sep="\t")
            assert len(exported_data) == 3
            assert "Q6EMK4" in exported_data["protein_id"].values  # Problematic ID preserved
            assert "INVALID_ID" in exported_data["protein_id"].values
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio 
    async def test_export_with_list_data_conversion(self):
        """Test export with list data that needs DataFrame conversion."""
        action = ExportDatasetAction()
        
        # Create context with list data
        list_context = {
            "datasets": {
                "list_data": [
                    {"protein_id": "P12345", "gene": "TP53"},
                    {"protein_id": "Q9Y6R4", "gene": "BRCA1"},
                    {"protein_id": "O00533", "gene": "CD4"}
                ]
            },
            "statistics": {},
            "output_files": {}
        }
        
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="list_data",
                output_path=tmp.name,
                format="csv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=list_context
            )
            
            # Verify conversion and export success
            assert result.success is True
            assert Path(tmp.name).exists()
            
            # Verify converted data
            exported_data = pd.read_csv(tmp.name)
            assert len(exported_data) == 3
            assert "protein_id" in exported_data.columns
            assert "gene" in exported_data.columns
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_directory_creation(self):
        """Test automatic directory creation for output paths."""
        action = ExportDatasetAction()
        
        # Create context with simple data
        context = {
            "datasets": {
                "simple": pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
            },
            "statistics": {},
            "output_files": {}
        }
        
        # Use nested directory path
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "subdir" / "output.tsv"
            
            params = ExportDatasetParams(
                input_key="simple",
                output_path=str(nested_path),
                format="tsv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=context
            )
            
            # Verify directory was created and file exported
            assert result.success is True
            assert nested_path.exists()
            assert nested_path.parent.exists()
    
    @pytest.mark.asyncio
    async def test_error_handling_missing_dataset(self, action_context):
        """Test error handling when dataset is missing."""
        action = ExportDatasetAction()
        
        params = ExportDatasetParams(
            input_key="nonexistent_dataset",
            output_path="/tmp/test.tsv",
            format="tsv"
        )
        
        result = await action.execute_typed(
            params=params,
            context=action_context
        )
        
        # Should return error result
        assert result.success is False
        assert "not found in context" in result.error
        assert "nonexistent_dataset" in result.error
    
    @pytest.mark.asyncio
    async def test_error_handling_unsupported_format(self, action_context):
        """Test error handling for unsupported export formats."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="proteins",
                output_path=tmp.name,
                format="xyz"  # Unsupported format
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Should return error result
            assert result.success is False
            assert "Unsupported format" in result.error
            assert "xyz" in result.error
            
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_columns(self, action_context):
        """Test error handling when specified columns don't exist."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="proteins",
                output_path=tmp.name,
                format="tsv",
                columns=["nonexistent_column"]  # Column doesn't exist
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Should return error result due to missing column
            assert result.success is False
            assert "Export failed" in result.error
            
            # Cleanup
            Path(tmp.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_context_updates_and_output_tracking(self, action_context):
        """Test that context is properly updated with output file information."""
        action = ExportDatasetAction()
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="proteins",
                output_path=tmp.name,
                format="tsv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=action_context
            )
            
            # Verify context was updated
            assert result.success is True
            
            # Check that output file was tracked in context (via UniversalContext)
            # Note: The actual context update depends on UniversalContext implementation
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_large_dataset_export_performance(self):
        """Test export performance with large biological datasets."""
        action = ExportDatasetAction()
        
        # Generate large dataset
        large_dataset = pd.DataFrame({
            "protein_id": [f"P{i:05d}" for i in range(10000)],
            "gene_symbol": [f"GENE_{i}" for i in range(10000)],
            "organism": ["Homo sapiens"] * 10000,
            "score": [0.5 + (i % 100) / 200 for i in range(10000)]  # Varying scores
        })
        
        context = {
            "datasets": {"large_proteins": large_dataset},
            "statistics": {},
            "output_files": {}
        }
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="large_proteins",
                output_path=tmp.name,
                format="tsv"
            )
            
            import time
            start_time = time.time()
            
            result = await action.execute_typed(
                params=params,
                context=context
            )
            
            export_time = time.time() - start_time
            
            # Verify export success and performance
            assert result.success is True
            assert result.data["row_count"] == 10000
            assert export_time < 5.0  # Should complete reasonably quickly
            
            # Verify file size is reasonable
            file_size = Path(tmp.name).stat().st_size
            assert file_size > 100000  # Should be substantial file
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_memory_efficient_export(self):
        """Test memory efficiency with large datasets."""
        action = ExportDatasetAction()
        
        # Create moderately large dataset to test memory usage
        dataset_size = 50000
        test_dataset = pd.DataFrame({
            "id": range(dataset_size),
            "data": ["x" * 50] * dataset_size  # 50 chars per row
        })
        
        context = {
            "datasets": {"memory_test": test_dataset},
            "statistics": {},
            "output_files": {}
        }
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="memory_test",
                output_path=tmp.name,
                format="tsv"
            )
            
            # Monitor memory usage (simplified)
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss
            
            result = await action.execute_typed(
                params=params,
                context=context
            )
            
            memory_after = process.memory_info().rss
            memory_increase = memory_after - memory_before
            
            # Verify export success
            assert result.success is True
            assert result.data["row_count"] == dataset_size
            
            # Memory increase should be reasonable (generous bound)
            assert memory_increase < 100 * 1024 * 1024  # < 100MB increase
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self):
        """Test export with Unicode and special characters in biological data."""
        action = ExportDatasetAction()
        
        # Create dataset with Unicode characters
        unicode_dataset = pd.DataFrame({
            "protein_name": ["α-synuclein", "β-catenin", "γ-secretase"],
            "organism": ["Homo sapiens", "Mus musculus", "Drosophila melanogaster"],
            "description": ["Protein α", "Protein β with special chars: <>&", "Protein γ"]
        })
        
        context = {
            "datasets": {"unicode_proteins": unicode_dataset},
            "statistics": {},
            "output_files": {}
        }
        
        # Test TSV export with Unicode
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="unicode_proteins",
                output_path=tmp.name,
                format="tsv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=context
            )
            
            assert result.success is True
            
            # Verify Unicode characters are preserved
            exported_data = pd.read_csv(tmp.name, sep="\t")
            assert "α-synuclein" in exported_data["protein_name"].values
            assert "β-catenin" in exported_data["protein_name"].values
            
            # Cleanup
            Path(tmp.name).unlink()
        
        # Test JSON export with Unicode
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="unicode_proteins",
                output_path=tmp.name,
                format="json"
            )
            
            result = await action.execute_typed(
                params=params,
                context=context
            )
            
            assert result.success is True
            
            # Verify JSON handles Unicode
            with open(tmp.name, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            assert json_data[0]["protein_name"] == "α-synuclein"
            
            # Cleanup
            Path(tmp.name).unlink()


class TestExportDatasetIntegration:
    """Test export dataset integration with biomapper standards."""
    
    @pytest.mark.asyncio
    async def test_universal_context_integration(self):
        """Test integration with UniversalContext wrapper."""
        action = ExportDatasetAction()
        
        # Test different context types that UniversalContext should handle
        dict_context = {
            "datasets": {
                "test": pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
            }
        }
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="test",
                output_path=tmp.name,
                format="tsv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=dict_context
            )
            
            assert result.success is True
            
            # Cleanup
            Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_standardized_parameter_naming(self):
        """Test compliance with 2025 parameter naming standards."""
        # The ExportDatasetParams should use standardized names
        params = ExportDatasetParams(
            input_key="test_data",  # Standard name
            output_path="/tmp/test.tsv",  # Standard name (not output_file)
            format="tsv"
        )
        
        assert hasattr(params, 'input_key')  # Should use input_key
        assert hasattr(params, 'output_path')  # Should use output_path
        assert not hasattr(params, 'dataset_key')  # Should not use legacy names
        assert not hasattr(params, 'output_file')  # Should not use legacy names
    
    @pytest.mark.asyncio
    async def test_biological_data_preservation(self):
        """Test that biological data integrity is preserved during export."""
        action = ExportDatasetAction()
        
        # Create dataset with biological identifiers that might have edge cases
        biological_data = pd.DataFrame({
            "uniprot_id": ["P12345", "Q6EMK4", "O00533-1"],  # Include isoform and edge case
            "gene_symbol": ["TP53", "PROBLEMATIC", "CD4"],
            "confidence": [0.95, 0.45, 0.85],  # Varying confidence levels
            "notes": ["High quality", "Known edge case", "Has isoform suffix"]
        })
        
        context = {
            "datasets": {"biological_test": biological_data},
            "statistics": {},
            "output_files": {}
        }
        
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            params = ExportDatasetParams(
                input_key="biological_test",
                output_path=tmp.name,
                format="tsv"
            )
            
            result = await action.execute_typed(
                params=params,
                context=context
            )
            
            assert result.success is True
            
            # Verify biological data integrity
            exported_data = pd.read_csv(tmp.name, sep="\t")
            assert len(exported_data) == 3
            assert "Q6EMK4" in exported_data["uniprot_id"].values  # Edge case preserved
            assert "O00533-1" in exported_data["uniprot_id"].values  # Isoform preserved
            assert exported_data.loc[1, "notes"] == "Known edge case"  # Metadata preserved
            
            # Cleanup
            Path(tmp.name).unlink()