import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import sys
import json
import subprocess

# Add the script directory to path for importing
scripts_dir = Path(__file__).parent.parent.parent / "scripts" / "main_pipelines"
sys.path.insert(0, str(scripts_dir))

@pytest.fixture
def mock_client():
    """Mock BiomapperClient for testing."""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock

@pytest.mark.asyncio
async def test_successful_execution(mock_client, tmp_path):
    """Test successful pipeline execution."""
    
    # Mock successful API response
    mock_client.execute_strategy.return_value = {
        'success': True,
        'execution_time': '5m 32s',
        'step_results': [
            {'step_id': 'load_data', 'status': 'success', 'input_count': 1000, 'output_count': 950}
        ],
        'summary': {
            'total_metabolites_processed': 1000,
            'final_match_rate': 0.75,
            'improvement_over_baseline': 0.30
        },
        'output_files': [str(tmp_path / 'results.csv')]
    }
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        # Import and run the main function
        from run_metabolomics_harmonization import main
        
        # Mock sys.argv
        with patch('sys.argv', ['run_metabolomics_harmonization.py']):
            result = await main()
            
            assert result == 0
            mock_client.execute_strategy.assert_called_once()
            call_args = mock_client.execute_strategy.call_args
            assert call_args.kwargs['strategy_name'] == 'METABOLOMICS_PROGRESSIVE_ENHANCEMENT'

@pytest.mark.asyncio
async def test_three_way_flag(mock_client):
    """Test that --three-way flag selects correct strategy."""
    
    mock_client.execute_strategy.return_value = {'success': True}
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py', '--three-way']):
            result = await main()
            
            assert result == 0
            call_args = mock_client.execute_strategy.call_args
            assert call_args.kwargs['strategy_name'] == 'THREE_WAY_METABOLOMICS_COMPLETE'

@pytest.mark.asyncio
async def test_custom_parameters(mock_client, tmp_path):
    """Test loading custom parameters from JSON file."""
    
    # Create test parameters file
    params_file = tmp_path / "params.json"
    params_data = {"threshold": 0.9, "output_format": "tsv"}
    params_file.write_text(json.dumps(params_data))
    
    mock_client.execute_strategy.return_value = {'success': True}
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py', '--parameters', str(params_file)]):
            result = await main()
            
            assert result == 0
            call_args = mock_client.execute_strategy.call_args
            context = call_args.kwargs['context']
            assert context['parameters'] == params_data

@pytest.mark.asyncio
async def test_execution_failure(mock_client):
    """Test handling of execution failure."""
    
    mock_client.execute_strategy.return_value = {
        'success': False,
        'message': 'Pipeline failed at step X',
        'details': {
            'failed_step': 'load_data',
            'error_details': 'File not found'
        }
    }
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py']):
            result = await main()
            
            assert result == 1

@pytest.mark.asyncio
async def test_dry_run_mode(mock_client):
    """Test dry run validation mode."""
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py', '--dry-run']):
            result = await main()
            
            assert result == 0
            # Should not call execute_strategy in dry run
            mock_client.execute_strategy.assert_not_called()

@pytest.mark.asyncio
async def test_custom_strategy(mock_client):
    """Test using custom strategy name."""
    
    mock_client.execute_strategy.return_value = {'success': True}
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py', '--strategy', 'CUSTOM_STRATEGY']):
            result = await main()
            
            assert result == 0
            call_args = mock_client.execute_strategy.call_args
            assert call_args.kwargs['strategy_name'] == 'CUSTOM_STRATEGY'

@pytest.mark.asyncio
async def test_output_directory_override(mock_client, tmp_path):
    """Test overriding output directory."""
    
    mock_client.execute_strategy.return_value = {'success': True}
    output_dir = tmp_path / "custom_output"
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py', '--output-dir', str(output_dir)]):
            result = await main()
            
            assert result == 0
            call_args = mock_client.execute_strategy.call_args
            context = call_args.kwargs['context']
            assert context['parameters']['output_dir'] == str(output_dir)

@pytest.mark.asyncio
async def test_keyboard_interrupt(mock_client):
    """Test handling of keyboard interrupt."""
    
    mock_client.execute_strategy.side_effect = KeyboardInterrupt()
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py']):
            result = await main()
            
            assert result == 130

@pytest.mark.asyncio
async def test_unexpected_exception(mock_client):
    """Test handling of unexpected exceptions."""
    
    mock_client.execute_strategy.side_effect = Exception("Unexpected error")
    
    with patch('biomapper_client.BiomapperClient', return_value=mock_client):
        from run_metabolomics_harmonization import main
        
        with patch('sys.argv', ['run_metabolomics_harmonization.py']):
            result = await main()
            
            assert result == 1

@pytest.mark.asyncio
async def test_debug_mode_logging():
    """Test that debug mode enables debug logging."""
    
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        with patch('biomapper_client.BiomapperClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.execute_strategy.return_value = {'success': True}
            mock_client_class.return_value = mock_client
            
            from run_metabolomics_harmonization import main
            
            with patch('sys.argv', ['run_metabolomics_harmonization.py', '--debug']):
                await main()
                
                # Verify setLevel was called with DEBUG
                mock_logger.setLevel.assert_called()

def test_no_forbidden_imports():
    """Verify script doesn't import forbidden modules."""
    
    # Read the script content
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
        
    content = script_path.read_text()
    
    # Check for forbidden imports
    forbidden_imports = [
        'from biomapper.core.strategy_actions',
        'from biomapper.core.executor',  
        'from biomapper.core.models.execution_context',
        'import biomapper.core.strategy_actions',
        'class.*Pipeline',  # No orchestration classes
    ]
    
    for forbidden in forbidden_imports:
        assert forbidden not in content, f"Found forbidden import/pattern: {forbidden}"
    
    # Check for required imports
    assert 'from biomapper_client import BiomapperClient' in content
    assert 'BiomapperClient' in content

def test_script_size():
    """Verify script is appropriately sized (not the old 691-line version)."""
    
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
    
    lines = script_path.read_text().split('\n')
    # Filter out empty lines and comments for actual code count
    code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
    
    # Should be significantly smaller than the original 691 lines
    assert len(code_lines) < 200, f"Script still too large: {len(code_lines)} lines of code"
    assert len(lines) < 400, f"Script still too large: {len(lines)} total lines"

def test_api_client_usage():
    """Test that script uses BiomapperClient correctly."""
    
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
        
    content = script_path.read_text()
    
    # Check for correct async context manager usage
    assert 'async with BiomapperClient(' in content
    assert 'execute_strategy(' in content
    assert 'strategy_name=' in content
    assert 'context=' in content

def test_parameter_handling():
    """Test that script handles parameters correctly."""
    
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
        
    content = script_path.read_text()
    
    # Check for parameter loading
    assert '--parameters' in content
    assert 'json.load(' in content
    assert 'parameters =' in content

def test_strategy_selection():
    """Test that script supports strategy selection."""
    
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
        
    content = script_path.read_text()
    
    # Check for strategy selection logic
    assert '--three-way' in content
    assert 'METABOLOMICS_PROGRESSIVE_ENHANCEMENT' in content
    assert 'THREE_WAY_METABOLOMICS_COMPLETE' in content
    assert 'strategy_name' in content

def test_error_handling():
    """Test that script has proper error handling."""
    
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
        
    content = script_path.read_text()
    
    # Check for error handling patterns
    assert 'try:' in content
    assert 'except Exception' in content
    assert 'KeyboardInterrupt' in content
    assert 'return 1' in content  # Error exit code
    assert 'return 0' in content  # Success exit code

def test_logging_configuration():
    """Test that script has proper logging setup."""
    
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
        
    content = script_path.read_text()
    
    # Check for logging setup
    assert 'import logging' in content
    assert 'logging.basicConfig(' in content
    assert 'logger = logging.getLogger(' in content
    assert '--debug' in content

def test_script_runs_and_shows_help():
    """Integration test - verify script runs and shows help."""
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
    
    # Test help flag
    result = subprocess.run([
        sys.executable, str(script_path), '--help'
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    assert 'metabolomics harmonization pipeline' in result.stdout
    assert '--three-way' in result.stdout
    assert '--parameters' in result.stdout

def test_script_dry_run_works():
    """Integration test - verify dry run mode works."""
    script_path = scripts_dir / "run_metabolomics_harmonization.py"
    if not script_path.exists():
        pytest.skip("Script not found - may not be migrated yet")
    
    # Test dry run (should work even without API running)  
    result = subprocess.run([
        sys.executable, str(script_path), '--dry-run'
    ], capture_output=True, text=True, timeout=30)
    
    assert result.returncode == 0
    assert 'Validating strategy configuration' in result.stderr or 'Validating strategy configuration' in result.stdout