"""
Tests for the metamapper database CLI commands.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from click.testing import CliRunner

from biomapper.cli.metamapper_db_cli import metamapper_db_cli


@pytest.fixture
def cli_runner():
    """Fixture that provides a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_session():
    """Fixture that provides a mock database session."""
    session = AsyncMock()
    # Configure the async mock properly
    session.execute = AsyncMock()
    session.close = AsyncMock()
    return session


class TestResourcesCommands:
    """Test cases for resource management commands."""

    @patch('biomapper.cli.metamapper_db_cli.get_async_session')
    def test_resources_list_empty(self, mock_get_session, cli_runner, mock_session):
        """Test listing resources when none exist."""
        # Mock the async function to return the mock session
        async def return_session():
            return mock_session
        mock_get_session.side_effect = return_session
        
        # Create mock result object with proper chain
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = cli_runner.invoke(metamapper_db_cli, ['resources', 'list'])
        
        assert result.exit_code == 0
        assert "No mapping resources found" in result.output

    @patch('biomapper.cli.metamapper_db_cli.get_async_session')
    def test_resources_list_json_output(self, mock_get_session, cli_runner, mock_session):
        """Test listing resources with JSON output."""
        # Mock the async function to return the mock session
        async def return_session():
            return mock_session
        mock_get_session.side_effect = return_session
        
        # Create mock result object with proper chain
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = cli_runner.invoke(metamapper_db_cli, ['resources', 'list', '--json'])
        
        assert result.exit_code == 0
        assert result.output.strip() == "[]"

    @patch('biomapper.cli.metamapper_db_cli.get_async_session')
    def test_show_resource_not_found(self, mock_get_session, cli_runner, mock_session):
        """Test showing a resource that doesn't exist."""
        # Mock the async function to return the mock session
        async def return_session():
            return mock_session
        mock_get_session.side_effect = return_session
        
        # Create mock result object with proper chain
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = cli_runner.invoke(metamapper_db_cli, ['resources', 'show', 'nonexistent'])
        
        assert result.exit_code == 0
        assert "Resource 'nonexistent' not found" in result.output


class TestPathsCommands:
    """Test cases for mapping path commands."""

    @patch('biomapper.cli.metamapper_db_cli.get_async_session')
    def test_find_paths_no_results(self, mock_get_session, cli_runner, mock_session):
        """Test finding paths with no results."""
        # Mock the async function to return the mock session
        async def return_session():
            return mock_session
        mock_get_session.side_effect = return_session
        
        # Create mock result object with proper chain
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = cli_runner.invoke(metamapper_db_cli, ['paths', 'find', '--from', 'GENE_NAME', '--to', 'UNIPROTKB_AC'])
        
        assert result.exit_code == 0
        assert "No mapping paths found from GENE_NAME to UNIPROTKB_AC" in result.output


class TestValidationCommands:
    """Test cases for validation operations."""

    @patch('biomapper.cli.metamapper_db_cli.get_async_session')
    def test_validate_clients_empty(self, mock_get_session, cli_runner, mock_session):
        """Test client validation with no clients."""
        # Mock the async function to return the mock session
        async def return_session():
            return mock_session
        mock_get_session.side_effect = return_session
        
        # Create mock result object with proper chain
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        result = cli_runner.invoke(metamapper_db_cli, ['validate', 'clients'])
        
        assert result.exit_code == 0
        assert "Client Class Validation Results: 0/0 valid" in result.output


class TestCLIIntegration:
    """Test cases for CLI integration."""

    def test_cli_help(self, cli_runner):
        """Test that the CLI help works."""
        result = cli_runner.invoke(metamapper_db_cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Commands for managing the metamapper database configuration" in result.output

    def test_resources_help(self, cli_runner):
        """Test that the resources subcommand help works."""
        result = cli_runner.invoke(metamapper_db_cli, ['resources', '--help'])
        
        assert result.exit_code == 0
        assert "Commands for managing mapping resources" in result.output

    def test_paths_help(self, cli_runner):
        """Test that the paths subcommand help works."""
        result = cli_runner.invoke(metamapper_db_cli, ['paths', '--help'])
        
        assert result.exit_code == 0
        assert "Commands for managing mapping paths" in result.output

    def test_validate_help(self, cli_runner):
        """Test that the validate subcommand help works."""
        result = cli_runner.invoke(metamapper_db_cli, ['validate', '--help'])
        
        assert result.exit_code == 0
        assert "Validation operations for the metamapper database" in result.output