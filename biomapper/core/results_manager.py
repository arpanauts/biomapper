"""
Unified results path management for local and cloud storage.
Ensures consistent folder organization across all outputs.
"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class ResultsPathManager:
    """Manages consistent path structure for biomapper results."""
    
    # Default base paths
    LOCAL_RESULTS_BASE = "/home/ubuntu/biomapper/results/Data_Harmonization"
    
    @staticmethod
    def extract_strategy_base(strategy_name: str) -> str:
        """
        Extract base strategy name without version suffix.
        
        Examples:
            metabolite_protein_integration_v2_enhanced -> metabolite_protein_integration
            custom_strategy_v1_base -> custom_strategy
            simple_strategy -> simple_strategy
        """
        # Pattern matches _v{number}_{descriptor} at the end
        pattern = r'_v\d+_\w+$'
        base_name = re.sub(pattern, '', strategy_name)
        
        # If no pattern matched, try simpler version pattern
        if base_name == strategy_name:
            pattern = r'_v\d+$'
            base_name = re.sub(pattern, '', strategy_name)
        
        return base_name if base_name else strategy_name
    
    @staticmethod
    def format_version_folder(version: str) -> str:
        """
        Format version string for folder name.
        
        Examples:
            1.0.0 -> v1_0_0
            2.1.0-beta -> v2_1_0-beta
        """
        # Replace dots with underscores
        version_clean = version.replace('.', '_')
        # Ensure it starts with 'v'
        if not version_clean.startswith('v'):
            version_clean = f"v{version_clean}"
        return version_clean
    
    @staticmethod
    def get_organized_path(
        strategy_name: str,
        version: str = "1.0.0",
        base_dir: Optional[str] = None,
        include_timestamp: bool = False,
        timestamp_format: str = "%Y%m%d_%H%M%S"
    ) -> Path:
        """
        Generate organized path structure for results.
        
        Structure: base_dir/strategy_base/version/[timestamp]/
        
        Args:
            strategy_name: Full strategy name (may include version suffix)
            version: Strategy version (e.g., "1.0.0")
            base_dir: Base directory (defaults to LOCAL_RESULTS_BASE)
            include_timestamp: Whether to add timestamp subfolder
            timestamp_format: Format for timestamp folder
            
        Returns:
            Path object for the organized directory
        """
        if base_dir is None:
            base_dir = ResultsPathManager.LOCAL_RESULTS_BASE
        
        # Extract base strategy name
        strategy_base = ResultsPathManager.extract_strategy_base(strategy_name)
        
        # Format version folder
        version_folder = ResultsPathManager.format_version_folder(version)
        
        # Build path
        path = Path(base_dir) / strategy_base / version_folder
        
        # Add timestamp if requested
        if include_timestamp:
            timestamp = datetime.now().strftime(timestamp_format)
            path = path / f"run_{timestamp}"
        
        return path
    
    @staticmethod
    def ensure_directory(path: Path) -> Path:
        """Create directory if it doesn't exist."""
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_output_filepath(
        organized_path: Path,
        filename: str,
        preserve_extension: bool = True
    ) -> Path:
        """
        Get full filepath within organized structure.
        
        Args:
            organized_path: Base organized path from get_organized_path()
            filename: Output filename
            preserve_extension: Keep original extension
            
        Returns:
            Full path to output file
        """
        return organized_path / filename
    
    @staticmethod
    def describe_structure(
        strategy_name: str,
        version: str,
        include_timestamp: bool = False
    ) -> str:
        """
        Describe the folder structure that will be created.
        
        Returns:
            Human-readable description of folder structure
        """
        strategy_base = ResultsPathManager.extract_strategy_base(strategy_name)
        version_folder = ResultsPathManager.format_version_folder(version)
        
        structure = f"{strategy_base}/{version_folder}"
        
        if include_timestamp:
            structure += "/run_[timestamp]"
        
        return structure
    
    @staticmethod
    def get_context_with_paths(
        context: Dict[str, Any],
        organized_path: Path
    ) -> Dict[str, Any]:
        """
        Update context with organized output paths.
        
        Args:
            context: Execution context
            organized_path: Organized base path
            
        Returns:
            Updated context with organized_output_path
        """
        context['organized_output_path'] = str(organized_path)
        context['organized_structure'] = {
            'base': str(organized_path.parent.parent),
            'strategy': organized_path.parent.parent.name,
            'version': organized_path.parent.name,
            'run': organized_path.name if organized_path.name.startswith('run_') else None
        }
        return context


class LocalResultsOrganizer:
    """Helper class for organizing local biomapper results."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize with base directory."""
        self.base_dir = base_dir or ResultsPathManager.LOCAL_RESULTS_BASE
        self.path_manager = ResultsPathManager()
    
    def prepare_strategy_output(
        self,
        strategy_name: str,
        version: str = "1.0.0",
        include_timestamp: bool = True
    ) -> Path:
        """
        Prepare organized output directory for a strategy.
        
        Args:
            strategy_name: Strategy name
            version: Strategy version
            include_timestamp: Include timestamp subfolder
            
        Returns:
            Path to organized output directory (created)
        """
        organized_path = self.path_manager.get_organized_path(
            strategy_name=strategy_name,
            version=version,
            base_dir=self.base_dir,
            include_timestamp=include_timestamp
        )
        
        # Ensure directory exists
        self.path_manager.ensure_directory(organized_path)
        
        return organized_path
    
    def get_latest_run(self, strategy_name: str, version: str = "1.0.0") -> Optional[Path]:
        """
        Get the most recent run directory for a strategy/version.
        
        Args:
            strategy_name: Strategy name
            version: Strategy version
            
        Returns:
            Path to latest run directory, or None if no runs exist
        """
        base_path = self.path_manager.get_organized_path(
            strategy_name=strategy_name,
            version=version,
            base_dir=self.base_dir,
            include_timestamp=False
        )
        
        if not base_path.exists():
            return None
        
        # Find all run directories
        run_dirs = sorted([
            d for d in base_path.iterdir() 
            if d.is_dir() and d.name.startswith('run_')
        ], reverse=True)
        
        return run_dirs[0] if run_dirs else None
    
    def list_strategy_runs(self, strategy_name: str) -> Dict[str, list]:
        """
        List all runs for a strategy across all versions.
        
        Args:
            strategy_name: Strategy name
            
        Returns:
            Dictionary mapping version to list of run directories
        """
        strategy_base = self.path_manager.extract_strategy_base(strategy_name)
        strategy_path = Path(self.base_dir) / strategy_base
        
        if not strategy_path.exists():
            return {}
        
        runs_by_version = {}
        
        for version_dir in strategy_path.iterdir():
            if version_dir.is_dir():
                runs = sorted([
                    d.name for d in version_dir.iterdir()
                    if d.is_dir() and d.name.startswith('run_')
                ], reverse=True)
                
                if runs:
                    runs_by_version[version_dir.name] = runs
        
        return runs_by_version
    
    def clean_old_runs(
        self, 
        strategy_name: str, 
        version: str = "1.0.0",
        keep_latest: int = 5
    ) -> int:
        """
        Clean up old run directories, keeping only the latest N.
        
        Args:
            strategy_name: Strategy name
            version: Strategy version
            keep_latest: Number of latest runs to keep
            
        Returns:
            Number of directories deleted
        """
        base_path = self.path_manager.get_organized_path(
            strategy_name=strategy_name,
            version=version,
            base_dir=self.base_dir,
            include_timestamp=False
        )
        
        if not base_path.exists():
            return 0
        
        # Find all run directories
        run_dirs = sorted([
            d for d in base_path.iterdir() 
            if d.is_dir() and d.name.startswith('run_')
        ], reverse=True)
        
        # Delete old ones
        deleted = 0
        for run_dir in run_dirs[keep_latest:]:
            import shutil
            shutil.rmtree(run_dir)
            deleted += 1
        
        return deleted


# Convenience functions for use in actions
def get_organized_output_path(
    context: Dict[str, Any],
    filename: str,
    use_organized: bool = True
) -> str:
    """
    Get output path using organized structure if available.
    
    Args:
        context: Execution context
        filename: Output filename
        use_organized: Use organized structure if available
        
    Returns:
        Full path to output file
    """
    if use_organized and 'organized_output_path' in context:
        return str(Path(context['organized_output_path']) / filename)
    
    # Fallback to traditional approach
    if 'output_dir' in context.get('parameters', {}):
        return str(Path(context['parameters']['output_dir']) / filename)
    
    # Default fallback
    return str(Path('/tmp/biomapper/output') / filename)


def setup_strategy_output_paths(
    context: Dict[str, Any],
    include_timestamp: bool = True
) -> Dict[str, Any]:
    """
    Setup organized output paths in context.
    
    Args:
        context: Execution context (will be modified)
        include_timestamp: Include timestamp in path
        
    Returns:
        Updated context with organized paths
    """
    # Get strategy info from context
    strategy_name = context.get('strategy_name', 'unknown_strategy')
    strategy_metadata = context.get('strategy_metadata', {})
    version = strategy_metadata.get('version', '1.0.0')
    
    # Check if custom output dir is specified
    custom_output = context.get('parameters', {}).get('output_dir')
    base_dir = custom_output if custom_output else ResultsPathManager.LOCAL_RESULTS_BASE
    
    # Get organized path
    organized_path = ResultsPathManager.get_organized_path(
        strategy_name=strategy_name,
        version=version,
        base_dir=base_dir,
        include_timestamp=include_timestamp
    )
    
    # Ensure directory exists
    ResultsPathManager.ensure_directory(organized_path)
    
    # Update context
    context = ResultsPathManager.get_context_with_paths(context, organized_path)
    
    return context