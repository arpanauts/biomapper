import tempfile
from biomapper.core.minimal_strategy_service import MinimalStrategyService


class TestVariableSubstitution:
    def setup_method(self):
        """Setup test environment with a temporary strategies directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.service = MinimalStrategyService(strategies_dir=self.temp_dir)

    def test_resolves_parameter_references(self):
        """Test that ${parameters.key} references are resolved"""
        input_str = "File path: ${parameters.data_file}"
        parameters = {"data_file": "/tmp/test.csv"}
        result = self.service._substitute_parameters(input_str, parameters)
        assert result == "File path: /tmp/test.csv"

    def test_resolves_metadata_references(self):
        """Test that ${metadata.source_files[0].path} references are resolved"""
        input_str = "Source: ${metadata.source_files[0].path}"
        parameters = {}
        metadata = {"source_files": [{"path": "/data/real_file.tsv"}]}
        # This test should FAIL initially, then pass after fix
        result = self.service._substitute_parameters(input_str, parameters, metadata)
        assert result == "Source: /data/real_file.tsv"

    def test_resolves_nested_metadata(self):
        """Test nested metadata access like ${metadata.source_files[1].last_updated}"""
        input_str = "Updated: ${metadata.source_files[1].last_updated}"
        parameters = {}
        metadata = {
            "source_files": [
                {"path": "/file1.csv", "last_updated": "2024-01-01"},
                {"path": "/file2.csv", "last_updated": "2024-06-15"},
            ]
        }
        result = self.service._substitute_parameters(input_str, parameters, metadata)
        assert result == "Updated: 2024-06-15"

    def test_handles_missing_metadata_gracefully(self):
        """Test that missing metadata doesn't crash"""
        input_str = "Path: ${metadata.nonexistent.path}"
        parameters = {}
        metadata = {}
        result = self.service._substitute_parameters(input_str, parameters, metadata)
        # Should either return original or empty string, not crash
        assert "${metadata.nonexistent.path}" in result or result == "Path: "

    def test_mixed_parameter_and_metadata_references(self):
        """Test templates with both parameter and metadata references"""
        input_str = "Load ${parameters.dataset} from ${metadata.source_files[0].path}"
        parameters = {"dataset": "proteins"}
        metadata = {"source_files": [{"path": "/data/proteins.csv"}]}
        result = self.service._substitute_parameters(input_str, parameters, metadata)
        assert result == "Load proteins from /data/proteins.csv"
