"""
Biomapper Strategy Definitions.

This module contains YAML strategy configurations for biological data
harmonization workflows, organized by entity type and complexity.
"""

from pathlib import Path

def get_strategy_path(strategy_name: str) -> Path:
    """Get the full path to a strategy file."""
    strategies_dir = Path(__file__).parent
    
    # Look for strategy in experimental first, then templates
    for subdir in ['experimental', 'templates']:
        strategy_path = strategies_dir / subdir / f"{strategy_name}.yaml"
        if strategy_path.exists():
            return strategy_path
    
    # Look in root strategies directory
    strategy_path = strategies_dir / f"{strategy_name}.yaml"
    if strategy_path.exists():
        return strategy_path
    
    raise FileNotFoundError(f"Strategy '{strategy_name}' not found")

def list_available_strategies() -> dict:
    """List all available strategy files organized by category."""
    strategies_dir = Path(__file__).parent
    strategies = {}
    
    for subdir in ['experimental', 'templates']:
        subdir_path = strategies_dir / subdir
        if subdir_path.exists():
            strategies[subdir] = [
                f.stem for f in subdir_path.glob("*.yaml")
            ]
    
    return strategies

__all__ = ['get_strategy_path', 'list_available_strategies']