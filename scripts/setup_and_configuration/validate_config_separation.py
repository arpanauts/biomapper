#!/usr/bin/env python
"""Utility to validate configuration separation and check for issues."""

import yaml
from pathlib import Path
from typing import Dict, List, Set
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigSeparationValidator:
    """Validates the separation of strategies from entity configs."""
    
    def __init__(self, configs_dir: Path):
        self.configs_dir = configs_dir
        self.issues: List[str] = []
        self.warnings: List[str] = []
        
    def validate(self) -> bool:
        """Run all validation checks."""
        entity_configs = list(self.configs_dir.glob('*_config.yaml'))
        entity_configs = [f for f in entity_configs if f.stem != 'mapping_strategies_config']
        
        strategies_config = self.configs_dir / 'mapping_strategies_config.yaml'
        
        # Load all configs
        all_strategies = {}
        all_mapping_paths = {}
        
        # Check strategies config exists
        if not strategies_config.exists():
            self.issues.append("mapping_strategies_config.yaml not found")
            return False
            
        # Load strategies
        with open(strategies_config) as f:
            strategies_data = yaml.safe_load(f)
            
        # Collect all strategy names
        strategy_names = set()
        
        # Generic strategies
        for name in strategies_data.get('generic_strategies', {}).keys():
            if name in strategy_names:
                self.issues.append(f"Duplicate strategy name: {name}")
            strategy_names.add(name)
            
        # Entity strategies
        for entity_type, strategies in strategies_data.get('entity_strategies', {}).items():
            for name in strategies.keys():
                if name in strategy_names:
                    self.issues.append(f"Duplicate strategy name: {name}")
                strategy_names.add(name)
                
        # Check entity configs
        for config_file in entity_configs:
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
                
            # Warn if strategies still in entity config
            if 'mapping_strategies' in config_data:
                self.warnings.append(
                    f"{config_file.name} still contains mapping_strategies section"
                )
                
            # Collect mapping paths
            entity_type = config_data.get('entity_type', config_file.stem.replace('_config', ''))
            mapping_paths = config_data.get('mapping_paths', [])
            
            for path in mapping_paths:
                path_name = path.get('name')
                if path_name:
                    all_mapping_paths[path_name] = entity_type
                    
        # Validate strategy references to mapping paths
        self._validate_path_references(strategies_data, all_mapping_paths)
        
        return len(self.issues) == 0
    
    def _validate_path_references(self, strategies_data: Dict, mapping_paths: Dict):
        """Check that EXECUTE_MAPPING_PATH actions reference valid paths."""
        all_strategies = {}
        all_strategies.update(strategies_data.get('generic_strategies', {}))
        
        for entity_type, strategies in strategies_data.get('entity_strategies', {}).items():
            all_strategies.update(strategies)
            
        for strategy_name, strategy_data in all_strategies.items():
            for step in strategy_data.get('steps', []):
                action = step.get('action', {})
                if action.get('type') == 'EXECUTE_MAPPING_PATH':
                    path_name = action.get('path_name')
                    if path_name and path_name not in mapping_paths:
                        self.issues.append(
                            f"Strategy '{strategy_name}' references unknown mapping path: {path_name}"
                        )
                        
    def report(self):
        """Print validation report."""
        if self.issues:
            logger.error("Validation issues found:")
            for issue in self.issues:
                logger.error(f"  ❌ {issue}")
                
        if self.warnings:
            logger.warning("Warnings:")
            for warning in self.warnings:
                logger.warning(f"  ⚠️  {warning}")
                
        if not self.issues and not self.warnings:
            logger.info("✅ Configuration separation looks good!")
            

if __name__ == "__main__":
    import sys
    
    configs_dir = Path(__file__).parent.parent.parent / "configs"
    validator = ConfigSeparationValidator(configs_dir)
    
    if validator.validate():
        validator.report()
        sys.exit(0)
    else:
        validator.report()
        sys.exit(1)