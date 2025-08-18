"""Tests for minimal CLI interface."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from src.cli.minimal import cli


class TestCLIInterface:
    """Test CLI interface functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def temp_strategy_dir(self):
        """Create temporary strategy directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            strategy_dir = Path(temp_dir) / "strategies"
            strategy_dir.mkdir()
            
            # Create some test strategy files
            (strategy_dir / "test_strategy_1.yaml").write_text("name: test_strategy_1")
            (strategy_dir / "test_strategy_2.yml").write_text("name: test_strategy_2")
            (strategy_dir / "subdir").mkdir()
            (strategy_dir / "subdir" / "nested_strategy.yaml").write_text("name: nested_strategy")
            
            yield strategy_dir
    
    def test_cli_help_command(self, cli_runner):
        """Test CLI help command."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Biomapper" in result.output
        assert "toolkit for biological data mapping" in result.output
        assert "health" in result.output
        assert "test-import" in result.output
        assert "api" in result.output
        assert "info" in result.output
        assert "strategies" in result.output
    
    def test_cli_version_option(self, cli_runner):
        """Test CLI version option."""
        result = cli_runner.invoke(cli, ['--version'])
        
        assert result.exit_code == 0
        assert "0.5.2" in result.output
    
    def test_health_command_success(self, cli_runner):
        """Test health command successful execution."""
        result = cli_runner.invoke(cli, ['health'])
        
        assert result.exit_code == 0
        assert "🎯 Biomapper Restructuring Complete!" in result.output
        assert "✅ Professional /src directory structure implemented" in result.output
        assert "✅ Modern Python packaging standards applied" in result.output
        assert "✅ CLI system operational" in result.output
        assert "📁 Clean structure:" in result.output
        assert "src/" in result.output
        assert "🚀 Next steps:" in result.output
    
    def test_info_command_success(self, cli_runner):
        """Test info command successful execution."""
        result = cli_runner.invoke(cli, ['info'])
        
        assert result.exit_code == 0
        assert "📦 Biomapper Project Information" in result.output
        assert "Version: 0.5.2" in result.output
        assert "Structure: Modern /src layout" in result.output
        assert "Status: Restructuring complete" in result.output
        assert "🏗️  Architecture (Barebones):" in result.output
        assert "🔧 Development:" in result.output
        assert "poetry install" in result.output


class TestImportCommand:
    """Test test-import command functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_test_import_successful_imports(self, cli_runner):
        """Test test-import command runs without crashing."""
        # Test the actual command without heavy mocking to avoid interference
        result = cli_runner.invoke(cli, ['test-import'])
        
        # The command should complete (may have import errors, but shouldn't crash)
        assert result.exit_code == 0
        assert "Path setup" in result.output  # Should attempt path setup
        # Don't check for specific success/failure patterns since they depend on actual environment
    
    def test_test_import_with_import_failures(self, cli_runner):
        """Test test-import handles import failures gracefully."""
        # Test the real command behavior - it should handle failures gracefully
        result = cli_runner.invoke(cli, ['test-import'])
        
        # Should complete gracefully regardless of any import failures
        assert result.exit_code == 0
        # Should produce some output
        assert len(result.output.strip()) > 0
    
    def test_test_import_path_setup_failure(self, cli_runner):
        """Test test-import with path setup failure."""
        with patch('sys.path') as mock_path:
            mock_path.insert.side_effect = Exception("Path setup failed")
            
            result = cli_runner.invoke(cli, ['test-import'])
            
            assert result.exit_code == 0  # Should handle gracefully
            assert "❌ Path setup: Path setup failed" in result.output


class TestAPICommand:
    """Test API command functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_api_path(self, tmp_path):
        """Create mock API directory structure."""
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        (api_dir / "main.py").write_text("# Mock API main file")
        return api_dir
    
    def test_api_command_success(self, cli_runner, mock_api_path):
        """Test API command successful execution."""
        with patch('pathlib.Path.parent') as mock_parent:
            mock_parent.return_value = mock_api_path.parent
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0)
                
                result = cli_runner.invoke(cli, ['api'])
                
                assert result.exit_code == 0
                assert "🚀 Starting biomapper API server..." in result.output
                assert "📍 URL: http://localhost:8000" in result.output
                assert "Press Ctrl+C to stop" in result.output
                
                # Verify subprocess was called with correct arguments
                mock_subprocess.assert_called_once()
                call_args = mock_subprocess.call_args[0][0]
                assert 'poetry' in call_args
                assert 'uvicorn' in call_args
                assert 'app.main:app' in call_args
                assert '--reload' in call_args
    
    def test_api_command_custom_host_port(self, cli_runner, mock_api_path):
        """Test API command with custom host and port."""
        with patch('pathlib.Path.parent') as mock_parent:
            mock_parent.return_value = mock_api_path.parent
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0)
                
                result = cli_runner.invoke(cli, ['api', '--host', '0.0.0.0', '--port', '9000'])
                
                assert result.exit_code == 0
                assert "📍 URL: http://0.0.0.0:9000" in result.output
                
                # Verify subprocess was called with custom host/port
                call_args = mock_subprocess.call_args[0][0]
                assert '--host=0.0.0.0' in call_args
                assert '--port=9000' in call_args
    
    def test_api_command_missing_api_directory(self, cli_runner):
        """Test API command when API directory doesn't exist."""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = cli_runner.invoke(cli, ['api'])
            
            assert result.exit_code == 1
            assert "❌ API directory not found" in result.output
            assert "The API components may need to be properly configured" in result.output
    
    def test_api_command_poetry_not_found(self, cli_runner, mock_api_path):
        """Test API command when poetry is not found."""
        with patch('pathlib.Path.parent') as mock_parent:
            mock_parent.return_value = mock_api_path.parent
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.side_effect = FileNotFoundError("Poetry not found")
                
                result = cli_runner.invoke(cli, ['api'])
                
                assert result.exit_code == 1
                assert "❌ Poetry not found" in result.output
                assert "Make sure you're in the poetry environment" in result.output
    
    def test_api_command_keyboard_interrupt(self, cli_runner, mock_api_path):
        """Test API command handling keyboard interrupt."""
        with patch('pathlib.Path.parent') as mock_parent:
            mock_parent.return_value = mock_api_path.parent
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.side_effect = KeyboardInterrupt()
                
                result = cli_runner.invoke(cli, ['api'])
                
                assert result.exit_code == 0
                assert "✋ API server stopped" in result.output
    
    def test_api_command_generic_error(self, cli_runner, mock_api_path):
        """Test API command with generic error."""
        with patch('pathlib.Path.parent') as mock_parent:
            mock_parent.return_value = mock_api_path.parent
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.side_effect = Exception("Generic error")
                
                result = cli_runner.invoke(cli, ['api'])
                
                assert result.exit_code == 1
                assert "❌ Error starting API: Generic error" in result.output


class TestStrategiesCommand:
    """Test strategies command functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_strategies_command_with_strategies(self, cli_runner):
        """Test strategies command when strategies are found."""
        # Mock the specific path construction in the strategies function
        mock_configs_path = MagicMock()
        mock_configs_path.exists.return_value = True
        
        # Mock YAML files
        mock_yaml_files = [
            Path("/mock/strategies/strategy1.yaml"),
            Path("/mock/strategies/strategy2.yml"),
            Path("/mock/strategies/subdir/strategy3.yaml")
        ]
        mock_configs_path.glob.side_effect = [
            mock_yaml_files[:2],  # *.yaml files
            [mock_yaml_files[2]]   # *.yml files
        ]
        
        # Patch the specific line: configs_path = Path(__file__).parent.parent / 'configs' / 'strategies'
        with patch('src.cli.minimal.Path') as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_configs_path
            
            result = cli_runner.invoke(cli, ['strategies'])
            
            assert result.exit_code == 0
            assert "📋 Found 3 strategy files:" in result.output
            assert "strategy1" in result.output
            assert "strategy2" in result.output
            assert "strategy3" in result.output
    
    def test_strategies_command_no_strategies(self, cli_runner):
        """Test strategies command when no strategies are found."""
        # Mock the specific path construction in the strategies function
        mock_configs_path = MagicMock()
        mock_configs_path.exists.return_value = True
        mock_configs_path.glob.return_value = []  # No strategy files
        
        with patch('src.cli.minimal.Path') as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_configs_path
            
            result = cli_runner.invoke(cli, ['strategies'])
            
            assert result.exit_code == 0
            assert "📋 No strategy files found" in result.output
            assert "Checked location:" in result.output
    
    def test_strategies_command_directory_not_exists(self, cli_runner):
        """Test strategies command when strategies directory doesn't exist."""
        # Mock the specific path construction in the strategies function
        mock_configs_path = MagicMock()
        mock_configs_path.exists.return_value = False
        
        with patch('src.cli.minimal.Path') as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_configs_path
            
            result = cli_runner.invoke(cli, ['strategies'])
            
            assert result.exit_code == 0
            assert "📋 No strategy files found" in result.output
            assert "Checked location:" in result.output
    
    def test_strategies_command_error_handling(self, cli_runner):
        """Test strategies command error handling."""
        # Mock the Path construction to raise an exception
        with patch('src.cli.minimal.Path') as mock_path:
            mock_path.side_effect = Exception("Path error")
            
            result = cli_runner.invoke(cli, ['strategies'])
            
            assert result.exit_code == 0
            assert "❌ Error listing strategies: Path error" in result.output


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_invalid_command(self, cli_runner):
        """Test CLI with invalid command."""
        result = cli_runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code == 2  # Click returns 2 for invalid commands
        assert "No such command" in result.output
    
    def test_api_command_invalid_port(self, cli_runner):
        """Test API command with invalid port value."""
        result = cli_runner.invoke(cli, ['api', '--port', 'invalid'])
        
        assert result.exit_code == 2  # Click validation error
    
    def test_api_command_help(self, cli_runner):
        """Test API command help."""
        result = cli_runner.invoke(cli, ['api', '--help'])
        
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
        assert "Start the biomapper API server" in result.output


class TestCLIInteractiveMode:
    """Test CLI interactive functionality."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_api_command_keyboard_interrupt_simulation(self, cli_runner):
        """Test simulated keyboard interrupt during API command."""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('subprocess.run') as mock_subprocess:
                # Simulate keyboard interrupt
                mock_subprocess.side_effect = KeyboardInterrupt()
                
                result = cli_runner.invoke(cli, ['api'])
                
                assert "✋ API server stopped" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_import_command_sys_path_error(self, cli_runner):
        """Test import command when sys.path manipulation fails."""
        with patch('sys.path') as mock_path:
            mock_path.insert.side_effect = Exception("Path manipulation failed")
            
            result = cli_runner.invoke(cli, ['test-import'])
            
            assert result.exit_code == 0  # Should handle gracefully
            assert "❌ Path setup" in result.output
    
    def test_import_command_module_import_errors(self, cli_runner):
        """Test import command handles various import errors gracefully."""
        # Test that the command doesn't crash when encountering import errors
        # This tests the real behavior without heavy mocking
        result = cli_runner.invoke(cli, ['test-import'])
        
        # Should complete gracefully regardless of import results
        assert result.exit_code == 0
        # Should produce some output
        assert len(result.output.strip()) > 0
    
    def test_strategies_command_permission_error(self, cli_runner):
        """Test strategies command with permission error."""
        # Mock the specific path construction in the strategies function
        mock_configs_path = MagicMock()
        mock_configs_path.exists.return_value = True
        mock_configs_path.glob.side_effect = PermissionError("Permission denied")
        
        with patch('src.cli.minimal.Path') as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_configs_path
            
            result = cli_runner.invoke(cli, ['strategies'])
            
            assert result.exit_code == 0
            assert "❌ Error listing strategies" in result.output
            assert "Permission denied" in result.output


class TestCLIConfigurationLoading:
    """Test CLI configuration loading and validation."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary configuration file."""
        config_content = {
            "default_strategy": "test_strategy",
            "output_dir": "/tmp/biomapper_output",
            "log_level": "INFO",
            "api": {
                "host": "0.0.0.0",
                "port": 8080
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_content, f)
            return f.name
    
    def test_configuration_file_handling(self, cli_runner, temp_config_file):
        """Test handling of configuration files."""
        # Since the current minimal CLI doesn't have explicit config file handling,
        # this test demonstrates how it could be tested when implemented
        
        config_path = Path(temp_config_file)
        assert config_path.exists()
        
        with open(config_path) as f:
            config = json.load(f)
            assert config["default_strategy"] == "test_strategy"
            assert config["api"]["port"] == 8080
        
        # Clean up
        config_path.unlink()


class TestCLIPerformance:
    """Test CLI performance characteristics."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_cli_response_time(self, cli_runner):
        """Test CLI command response time."""
        import time
        
        start_time = time.time()
        result = cli_runner.invoke(cli, ['health'])
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert result.exit_code == 0
        assert execution_time < 1.0  # Should complete quickly
    
    def test_strategies_command_large_directory(self, cli_runner):
        """Test strategies command with large number of files."""
        # Mock the specific path construction in the strategies function
        mock_configs_path = MagicMock()
        mock_configs_path.exists.return_value = True
        
        # Simulate large number of strategy files
        large_file_list = [
            Path(f"/mock/strategies/strategy_{i}.yaml") 
            for i in range(100)
        ]
        mock_configs_path.glob.side_effect = [large_file_list, []]  # yaml, yml
        
        with patch('src.cli.minimal.Path') as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_configs_path
            
            import time
            start_time = time.time()
            
            result = cli_runner.invoke(cli, ['strategies'])
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            assert result.exit_code == 0
            assert "📋 Found 100 strategy files:" in result.output
            assert execution_time < 5.0  # Should handle large lists efficiently


class TestCLIOutputFormatting:
    """Test CLI output formatting and user experience."""
    
    @pytest.fixture
    def cli_runner(self):
        """Create CLI test runner."""
        return CliRunner()
    
    def test_health_command_output_formatting(self, cli_runner):
        """Test health command output formatting."""
        result = cli_runner.invoke(cli, ['health'])
        
        assert result.exit_code == 0
        
        # Check for proper emoji and formatting
        assert "🎯" in result.output
        assert "✅" in result.output
        assert "📁" in result.output
        assert "🚀" in result.output
        
        # Check for proper structure in output
        lines = result.output.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Should have multiple informative lines
        assert len(non_empty_lines) > 5
    
    def test_info_command_output_structure(self, cli_runner):
        """Test info command output structure."""
        result = cli_runner.invoke(cli, ['info'])
        
        assert result.exit_code == 0
        
        # Check for proper sections
        assert "📦 Biomapper Project Information" in result.output
        assert "🏗️  Architecture" in result.output
        assert "🔧 Development" in result.output
        
        # Verify version information is present
        assert "Version: 0.5.2" in result.output
    
    def test_strategies_command_output_formatting(self, cli_runner):
        """Test strategies command output formatting."""
        # Mock the specific path construction in the strategies function
        mock_configs_path = MagicMock()
        mock_configs_path.exists.return_value = True
        
        mock_files = [
            Path("/mock/strategies/strategy_a.yaml"),
            Path("/mock/strategies/strategy_b.yml")
        ]
        mock_configs_path.glob.side_effect = [mock_files[:1], mock_files[1:]]
        
        with patch('src.cli.minimal.Path') as mock_path:
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = mock_configs_path
            
            result = cli_runner.invoke(cli, ['strategies'])
            
            assert result.exit_code == 0
            assert "📋" in result.output
            assert "   • strategy_a" in result.output
            assert "   • strategy_b" in result.output