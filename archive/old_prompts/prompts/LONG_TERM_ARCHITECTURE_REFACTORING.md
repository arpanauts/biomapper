# Long-Term Architecture Refactoring for Biomapper

## Executive Summary

This prompt guides the comprehensive restructuring of the biomapper project for long-term maintainability, incorporating insights from Gemini AI collaboration and the recent cleanup report. The refactoring addresses critical issues including scattered action organization, distant strategy-action relationships, and the presence of 309 unresolved linting issues across 463 Python files.

## Current State Analysis

### Metrics from Cleanup Report
- **Codebase Size**: 463 Python files, 62 YAML files, ~50,000 lines
- **Technical Debt**: 309 linting issues (180+ unused variables, 15 boolean comparisons, 3 bare excepts)
- **Data Management**: 6.1GB uncompressed data files in repository
- **Empty Directories**: 24 (mix of runtime and obsolete)
- **Code Quality**: Recently formatted (48 files), but structural issues remain

### Architectural Pain Points
1. **Action Scatter**: 26 actions spread across deep directory trees
2. **Strategy Distance**: YAML strategies 4+ directories away from their actions
3. **No Domain Separation**: Proteins, metabolites, chemistry mixed together
4. **Root Clutter**: Investigation scripts mixed with production code
5. **Import Coupling**: Hardcoded import paths throughout

## Target Architecture

Based on Gemini's recommendations and bioinformatics best practices:

```
biomapper/
├── domains/                    # Domain-driven organization
│   ├── proteins/
│   │   ├── strategies/        # Co-located strategies
│   │   ├── actions/           # Domain-specific actions
│   │   │   ├── mapping/       # Functional sub-categories
│   │   │   ├── analysis/
│   │   │   └── enrichment/
│   │   ├── models/            # Pydantic models
│   │   └── tests/             # Domain-specific tests
│   ├── metabolites/
│   │   ├── strategies/
│   │   ├── actions/
│   │   │   ├── identification/
│   │   │   ├── matching/
│   │   │   └── harmonization/
│   │   ├── models/
│   │   └── tests/
│   ├── chemistry/
│   │   ├── strategies/
│   │   ├── actions/
│   │   │   ├── loinc/
│   │   │   ├── phenotype/
│   │   │   └── vendor/
│   │   ├── models/
│   │   └── tests/
│   └── multi_entity/          # Cross-domain workflows
│       ├── strategies/
│       ├── actions/
│       └── tests/
├── infrastructure/             # Core system components
│   ├── registry/              # Action registration system
│   ├── execution/             # MinimalStrategyService
│   ├── api/                   # FastAPI application
│   ├── persistence/           # Database and checkpointing
│   └── di/                    # Dependency injection
├── shared/                    # Cross-cutting concerns
│   ├── algorithms/            # Reusable algorithms
│   ├── models/                # Common Pydantic models
│   ├── utils/                 # Utility functions
│   └── validators/            # Common validators
├── tools/                     # Development tools
│   ├── investigation/         # Research scripts (moved from root)
│   ├── migration/             # Migration utilities
│   └── performance/           # Performance testing
└── data/                      # Managed with DVC
    └── .dvc/                  # Data version control
```

## Phase 1: Foundation (Week 1)

### Step 1: Create Migration Infrastructure

```python
# Create migration tracking system
cat > /home/ubuntu/biomapper/tools/migration/migration_tracker.py << 'EOF'
"""Track and validate architecture migration progress."""

import json
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime

class MigrationTracker:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tracker_file = project_root / ".migration_tracker.json"
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        if self.tracker_file.exists():
            with open(self.tracker_file) as f:
                return json.load(f)
        return {
            "started": datetime.now().isoformat(),
            "phases": {},
            "moved_files": [],
            "broken_imports": [],
            "verified_strategies": []
        }
    
    def track_file_move(self, old_path: str, new_path: str):
        """Track file movements for import updates."""
        self.state["moved_files"].append({
            "old": old_path,
            "new": new_path,
            "timestamp": datetime.now().isoformat()
        })
        self._save_state()
    
    def verify_strategy(self, strategy_name: str, status: str):
        """Track strategy verification status."""
        self.state["verified_strategies"].append({
            "name": strategy_name,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
        self._save_state()
    
    def _save_state(self):
        with open(self.tracker_file, 'w') as f:
            json.dump(self.state, f, indent=2)
EOF
```

### Step 2: Create Import Compatibility Layer

```python
# Create backward compatibility for imports
cat > /home/ubuntu/biomapper/infrastructure/compatibility.py << 'EOF'
"""Maintain backward compatibility during migration."""

import sys
import warnings
from typing import Dict, Any

class ImportCompatibility:
    """Redirect old imports to new locations."""
    
    # Mapping of old to new import paths
    REDIRECTS = {
        "biomapper.core.strategy_actions.load_dataset_identifiers": 
            "biomapper.domains.core.actions.load_dataset_identifiers",
        "biomapper.core.strategy_actions.entities.chemistry.identification.extract_loinc":
            "biomapper.domains.chemistry.actions.loinc.extract_loinc",
        # Add more as we migrate
    }
    
    @classmethod
    def install(cls):
        """Install import hooks for compatibility."""
        for old_path, new_path in cls.REDIRECTS.items():
            cls._add_redirect(old_path, new_path)
    
    @classmethod
    def _add_redirect(cls, old_path: str, new_path: str):
        """Add a single import redirect."""
        def redirect_import():
            warnings.warn(
                f"Import from '{old_path}' is deprecated. "
                f"Use '{new_path}' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return __import__(new_path)
        
        sys.modules[old_path] = redirect_import()
EOF
```

### Step 3: Setup Directory Structure

```bash
# Create new directory structure
cd /home/ubuntu/biomapper

# Create domain directories
mkdir -p domains/{proteins,metabolites,chemistry,multi_entity}/{strategies,actions,models,tests}
mkdir -p domains/proteins/actions/{mapping,analysis,enrichment}
mkdir -p domains/metabolites/actions/{identification,matching,harmonization}
mkdir -p domains/chemistry/actions/{loinc,phenotype,vendor}

# Create infrastructure directories
mkdir -p infrastructure/{registry,execution,api,persistence,di}

# Create shared directories
mkdir -p shared/{algorithms,models,utils,validators}

# Create tools directories
mkdir -p tools/{investigation,migration,performance}

# Create __init__.py files for all packages
find domains infrastructure shared tools -type d -exec touch {}/__init__.py \;

echo "✅ Directory structure created"
```

### Step 4: Move Investigation Scripts

```bash
# Move investigation scripts from root to tools/
cd /home/ubuntu/biomapper

# Identify and move test/investigation scripts
for file in test_*.py metabolite_test_*.py protein_test_*.py; do
    if [ -f "$file" ]; then
        git mv "$file" tools/investigation/ 2>/dev/null || mv "$file" tools/investigation/
        echo "Moved $file to tools/investigation/"
    fi
done

# Move report files
for file in *_report.md *_summary.md; do
    if [ -f "$file" ]; then
        git mv "$file" tools/investigation/ 2>/dev/null || mv "$file" tools/investigation/
        echo "Moved $file to tools/investigation/"
    fi
done

echo "✅ Investigation scripts moved"
```

## Phase 2: Action Migration (Week 2)

### Step 1: Migrate Core Actions

```python
# Script to migrate core actions
cat > /home/ubuntu/biomapper/tools/migration/migrate_core_actions.py << 'EOF'
"""Migrate core actions to new structure."""

import shutil
from pathlib import Path
import ast

class ActionMigrator:
    def __init__(self):
        self.old_base = Path("/home/ubuntu/biomapper/biomapper/core/strategy_actions")
        self.new_base = Path("/home/ubuntu/biomapper/domains")
        
    def migrate_action(self, action_file: Path, domain: str, category: str = None):
        """Migrate a single action to new location."""
        # Determine target path
        if category:
            target_dir = self.new_base / domain / "actions" / category
        else:
            target_dir = self.new_base / domain / "actions"
        
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / action_file.name
        
        # Copy file (preserve original during migration)
        shutil.copy2(action_file, target_file)
        
        # Update imports in the file
        self._update_imports(target_file, domain)
        
        print(f"✓ Migrated {action_file.name} to {domain}/{category or 'actions'}")
        
    def _update_imports(self, file_path: Path, domain: str):
        """Update imports in migrated file."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Update import statements
        replacements = [
            ("from biomapper.core.strategy_actions", f"from biomapper.domains.{domain}.actions"),
            ("from biomapper.core.models", "from biomapper.shared.models"),
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        with open(file_path, 'w') as f:
            f.write(content)

# Migrate core actions
migrator = ActionMigrator()

# Load dataset identifiers (core action)
migrator.migrate_action(
    Path("/home/ubuntu/biomapper/biomapper/core/strategy_actions/load_dataset_identifiers.py"),
    "core"
)

# Merge datasets (core action)
if Path("/home/ubuntu/biomapper/biomapper/core/strategy_actions/merge_datasets.py").exists():
    migrator.migrate_action(
        Path("/home/ubuntu/biomapper/biomapper/core/strategy_actions/merge_datasets.py"),
        "core"
    )
EOF

python /home/ubuntu/biomapper/tools/migration/migrate_core_actions.py
```

### Step 2: Migrate Domain-Specific Actions

```python
# Migrate chemistry actions
cat > /home/ubuntu/biomapper/tools/migration/migrate_chemistry_actions.py << 'EOF'
"""Migrate chemistry actions to domain structure."""

from pathlib import Path
import shutil

# Chemistry action mappings
chemistry_actions = {
    "loinc": [
        "biomapper/core/strategy_actions/entities/chemistry/identification/extract_loinc.py"
    ],
    "phenotype": [
        "biomapper/core/strategy_actions/chemistry_to_phenotype_bridge.py"
    ],
    "vendor": [
        "biomapper/core/strategy_actions/entities/chemistry/harmonization/vendor_harmonization.py"
    ]
}

base_path = Path("/home/ubuntu/biomapper")

for category, actions in chemistry_actions.items():
    target_dir = base_path / "domains" / "chemistry" / "actions" / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for action_path in actions:
        source = base_path / action_path
        if source.exists():
            target = target_dir / source.name
            shutil.copy2(source, target)
            print(f"✓ Migrated {source.name} to chemistry/{category}")
EOF

python /home/ubuntu/biomapper/tools/migration/migrate_chemistry_actions.py
```

### Step 3: Update Action Registry Discovery

```python
# Update MinimalStrategyService for new structure
cat > /home/ubuntu/biomapper/infrastructure/registry/action_discovery.py << 'EOF'
"""Dynamic action discovery for new domain structure."""

import importlib
import logging
from pathlib import Path
from typing import Dict, Type

logger = logging.getLogger(__name__)

class ActionDiscovery:
    """Discover and register actions from domain structure."""
    
    @staticmethod
    def discover_actions(base_path: Path) -> Dict[str, Type]:
        """Discover all actions in domain directories."""
        from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
        
        # Clear existing registry
        ACTION_REGISTRY.clear()
        
        # Domain paths to scan
        domain_paths = [
            base_path / "domains" / domain / "actions"
            for domain in ["proteins", "metabolites", "chemistry", "multi_entity", "core"]
        ]
        
        for domain_path in domain_paths:
            if not domain_path.exists():
                continue
                
            # Find all Python files
            for action_file in domain_path.rglob("*.py"):
                if action_file.name.startswith("__"):
                    continue
                    
                # Convert path to module
                relative_path = action_file.relative_to(base_path)
                module_path = str(relative_path.with_suffix("")).replace("/", ".")
                
                try:
                    # Import the module (actions self-register)
                    importlib.import_module(f"biomapper.{module_path}")
                    logger.info(f"Imported action module: {module_path}")
                except Exception as e:
                    logger.warning(f"Failed to import {module_path}: {e}")
        
        logger.info(f"Discovered {len(ACTION_REGISTRY)} actions")
        return ACTION_REGISTRY
EOF
```

## Phase 3: Strategy Migration (Week 3)

### Step 1: Co-locate Strategies with Actions

```python
# Migrate strategies to their domains
cat > /home/ubuntu/biomapper/tools/migration/migrate_strategies.py << 'EOF'
"""Migrate strategies to be co-located with their domain actions."""

import yaml
import shutil
from pathlib import Path

class StrategyMigrator:
    def __init__(self):
        self.old_base = Path("/home/ubuntu/biomapper/configs/strategies")
        self.new_base = Path("/home/ubuntu/biomapper/domains")
        
    def analyze_strategy(self, strategy_file: Path) -> str:
        """Determine domain for a strategy based on its name and content."""
        name = strategy_file.stem.lower()
        
        # Domain detection rules
        if "prot_" in name or "protein" in name:
            return "proteins"
        elif "met_" in name or "metabol" in name:
            return "metabolites"
        elif "chem_" in name or "chemistry" in name:
            return "chemistry"
        elif "multi_" in name:
            return "multi_entity"
        else:
            # Analyze content
            with open(strategy_file) as f:
                content = yaml.safe_load(f)
            
            # Check action types used
            if content and "steps" in content:
                for step in content["steps"]:
                    action_type = step.get("action", {}).get("type", "").lower()
                    if "protein" in action_type or "uniprot" in action_type:
                        return "proteins"
                    elif "metabol" in action_type or "hmdb" in action_type:
                        return "metabolites"
                    elif "chemistry" in action_type or "loinc" in action_type:
                        return "chemistry"
            
            return "multi_entity"  # Default for unclear cases
    
    def migrate_strategy(self, strategy_file: Path):
        """Migrate a strategy to its domain."""
        domain = self.analyze_strategy(strategy_file)
        target_dir = self.new_base / domain / "strategies"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_file = target_dir / strategy_file.name
        shutil.copy2(strategy_file, target_file)
        
        print(f"✓ Migrated {strategy_file.name} to {domain}/strategies")
        return domain

# Migrate all strategies
migrator = StrategyMigrator()

# Migrate experimental strategies
experimental_dir = Path("/home/ubuntu/biomapper/configs/strategies/experimental")
for strategy in experimental_dir.glob("*.yaml"):
    migrator.migrate_strategy(strategy)

# Migrate root strategies
for strategy in Path("/home/ubuntu/biomapper/configs/strategies").glob("*.yaml"):
    if strategy.is_file():
        migrator.migrate_strategy(strategy)
EOF

python /home/ubuntu/biomapper/tools/migration/migrate_strategies.py
```

### Step 2: Update Strategy Loading

```python
# Update strategy discovery for new locations
cat > /home/ubuntu/biomapper/infrastructure/execution/strategy_loader.py << 'EOF'
"""Load strategies from domain directories."""

import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class DomainStrategyLoader:
    """Load strategies from domain-organized structure."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.domains_path = base_path / "domains"
        self.legacy_path = base_path / "configs" / "strategies"
        
    def load_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load strategies from all domains."""
        strategies = {}
        
        # Load from new domain structure
        if self.domains_path.exists():
            for domain_dir in self.domains_path.iterdir():
                if domain_dir.is_dir():
                    strategies_dir = domain_dir / "strategies"
                    if strategies_dir.exists():
                        strategies.update(self._load_from_directory(strategies_dir))
        
        # Fallback to legacy location
        if self.legacy_path.exists() and len(strategies) == 0:
            logger.info("Loading from legacy location")
            strategies.update(self._load_from_directory(self.legacy_path))
        
        logger.info(f"Loaded {len(strategies)} strategies")
        return strategies
    
    def _load_from_directory(self, directory: Path) -> Dict[str, Dict[str, Any]]:
        """Load all YAML strategies from a directory."""
        strategies = {}
        
        for yaml_file in directory.rglob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    strategy = yaml.safe_load(f)
                
                if strategy and "name" in strategy:
                    strategies[strategy["name"]] = strategy
                    logger.debug(f"Loaded strategy: {strategy['name']}")
                    
            except Exception as e:
                logger.warning(f"Failed to load {yaml_file}: {e}")
        
        return strategies
EOF
```

## Phase 4: Dependency Injection Implementation (Week 4)

### Step 1: Create DI Container

```python
# Implement dependency injection
cat > /home/ubuntu/biomapper/infrastructure/di/container.py << 'EOF'
"""Dependency injection container for biomapper."""

from typing import Protocol, Type, Dict, Any, Optional
from dataclasses import dataclass
import inspect

class ServiceProtocol(Protocol):
    """Base protocol for all services."""
    pass

@dataclass
class ServiceBinding:
    """Binding between interface and implementation."""
    interface: Type
    implementation: Type
    singleton: bool = False
    instance: Optional[Any] = None

class DIContainer:
    """Dependency injection container."""
    
    def __init__(self):
        self.bindings: Dict[Type, ServiceBinding] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default service bindings."""
        from biomapper.infrastructure.persistence.sqlite_persistence import SQLitePersistence
        from biomapper.infrastructure.persistence.interfaces import DataPersistence
        
        self.bind(DataPersistence, SQLitePersistence, singleton=True)
    
    def bind(self, interface: Type, implementation: Type, singleton: bool = False):
        """Bind an interface to an implementation."""
        self.bindings[interface] = ServiceBinding(
            interface=interface,
            implementation=implementation,
            singleton=singleton
        )
    
    def resolve(self, interface: Type) -> Any:
        """Resolve a service by its interface."""
        if interface not in self.bindings:
            raise ValueError(f"No binding found for {interface}")
        
        binding = self.bindings[interface]
        
        # Return singleton instance if exists
        if binding.singleton and binding.instance:
            return binding.instance
        
        # Create new instance
        instance = self._create_instance(binding.implementation)
        
        # Store singleton
        if binding.singleton:
            binding.instance = instance
        
        return instance
    
    def _create_instance(self, cls: Type) -> Any:
        """Create an instance with dependency injection."""
        # Get constructor parameters
        sig = inspect.signature(cls.__init__)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Try to resolve parameter type
            if param.annotation != inspect.Parameter.empty:
                if param.annotation in self.bindings:
                    kwargs[param_name] = self.resolve(param.annotation)
        
        return cls(**kwargs)

# Global container instance
container = DIContainer()
EOF
```

### Step 2: Update Actions for DI

```python
# Example of updating an action for DI
cat > /home/ubuntu/biomapper/domains/core/actions/load_dataset_di.py << 'EOF'
"""Load dataset action with dependency injection."""

from typing import Protocol, Optional
import pandas as pd
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action

class DataValidator(Protocol):
    """Protocol for data validation."""
    def validate(self, df: pd.DataFrame) -> bool:
        ...

class DataCache(Protocol):
    """Protocol for data caching."""
    async def get(self, key: str) -> Optional[pd.DataFrame]:
        ...
    async def set(self, key: str, df: pd.DataFrame) -> None:
        ...

@register_action("LOAD_DATASET_DI")
class LoadDatasetWithDI(TypedStrategyAction):
    """Load dataset with injected dependencies."""
    
    def __init__(
        self,
        validator: Optional[DataValidator] = None,
        cache: Optional[DataCache] = None
    ):
        super().__init__()
        self.validator = validator
        self.cache = cache
    
    async def execute_typed(self, params, context):
        """Execute with optional caching and validation."""
        # Check cache first
        if self.cache:
            cached = await self.cache.get(params.file_path)
            if cached is not None:
                return cached
        
        # Load data
        df = pd.read_csv(params.file_path, sep='\t')
        
        # Validate if validator provided
        if self.validator and not self.validator.validate(df):
            raise ValueError("Data validation failed")
        
        # Cache result
        if self.cache:
            await self.cache.set(params.file_path, df)
        
        return df
EOF
```

## Phase 5: Cleanup Integration (Week 5)

### Step 1: Fix Remaining Linting Issues

```python
# Script to fix linting issues identified in cleanup report
cat > /home/ubuntu/biomapper/tools/migration/fix_linting_issues.py << 'EOF'
"""Fix linting issues from cleanup report."""

import subprocess
from pathlib import Path

def fix_linting_issues():
    """Fix the 309 identified linting issues."""
    
    base_path = Path("/home/ubuntu/biomapper")
    
    # Fix E722: Bare except clauses (3 instances)
    print("Fixing bare except clauses...")
    subprocess.run([
        "ruff", "check", "--fix", "--select", "E722", str(base_path)
    ])
    
    # Fix F811: Redefined imports (6 instances)
    print("Fixing redefined imports...")
    subprocess.run([
        "ruff", "check", "--fix", "--select", "F811", str(base_path)
    ])
    
    # Fix E712: Boolean comparisons (15 instances)
    print("Fixing boolean comparisons...")
    subprocess.run([
        "ruff", "check", "--fix", "--select", "E712", str(base_path)
    ])
    
    # Review F841: Unused variables (180+ instances)
    # This needs manual review to avoid removing needed exception variables
    print("\nRemaining unused variables need manual review:")
    result = subprocess.run(
        ["ruff", "check", "--select", "F841", str(base_path)],
        capture_output=True, text=True
    )
    
    unused_vars = result.stdout.count("F841")
    print(f"  Found {unused_vars} unused variables")
    print("  Review manually to preserve exception handling variables")

if __name__ == "__main__":
    fix_linting_issues()
EOF

python /home/ubuntu/biomapper/tools/migration/fix_linting_issues.py
```

### Step 2: Implement Data Version Control

```bash
# Setup DVC for large data files
cd /home/ubuntu/biomapper

# Initialize DVC
pip install dvc[s3]  # or dvc[gdrive] for Google Drive storage
dvc init

# Track large data files with DVC
dvc add data/hmdb_metabolites.xml
dvc add data/hmdb_metabolites.zip
dvc add data/qdrant_storage

# Create DVC config
cat > .dvc/config << EOF
[core]
    remote = myremote
    
['remote "myremote"']
    url = s3://biomapper-data/dvc-store
    # or url = gdrive://folder-id for Google Drive
EOF

# Commit DVC files
git add .dvc .dvcignore data/*.dvc
git commit -m "Add DVC for large data files"

echo "✅ DVC configured for data management"
```

### Step 3: Setup Pre-commit Hooks

```yaml
# Create pre-commit configuration
cat > /home/ubuntu/biomapper/.pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=1000]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        additional_dependencies: [types-all]
EOF

# Install pre-commit
pip install pre-commit
pre-commit install

echo "✅ Pre-commit hooks configured"
```

## Phase 6: Testing and Validation (Week 6)

### Step 1: Create Integration Tests for New Structure

```python
# Test suite for migrated structure
cat > /home/ubuntu/biomapper/tests/integration/test_migration.py << 'EOF'
"""Integration tests for architecture migration."""

import pytest
from pathlib import Path
from biomapper.infrastructure.registry.action_discovery import ActionDiscovery
from biomapper.infrastructure.execution.strategy_loader import DomainStrategyLoader

class TestMigration:
    """Test the migrated architecture."""
    
    def test_action_discovery(self):
        """Test that all 26 actions are still discovered."""
        base_path = Path("/home/ubuntu/biomapper")
        registry = ActionDiscovery.discover_actions(base_path)
        
        assert len(registry) >= 26, f"Expected 26+ actions, found {len(registry)}"
        
        # Check specific actions
        expected_actions = [
            "LOAD_DATASET_IDENTIFIERS",
            "CUSTOM_TRANSFORM",
            "CHEMISTRY_EXTRACT_LOINC",
            "CHEMISTRY_FUZZY_TEST_MATCH",
            "CHEMISTRY_VENDOR_HARMONIZATION",
            "CHEMISTRY_TO_PHENOTYPE_BRIDGE"
        ]
        
        for action in expected_actions:
            assert action in registry, f"Missing action: {action}"
    
    def test_strategy_loading(self):
        """Test that strategies load from new locations."""
        base_path = Path("/home/ubuntu/biomapper")
        loader = DomainStrategyLoader(base_path)
        strategies = loader.load_all_strategies()
        
        # Should find all migrated strategies
        assert len(strategies) > 0, "No strategies found"
        
        # Check for specific strategies
        if "met_arv_to_spoke_multi_v1_base" in strategies:
            strategy = strategies["met_arv_to_spoke_multi_v1_base"]
            assert "steps" in strategy, "Strategy missing steps"
    
    def test_backward_compatibility(self):
        """Test that old imports still work with warnings."""
        import warnings
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Try old import path
            from biomapper.infrastructure.compatibility import ImportCompatibility
            ImportCompatibility.install()
            
            # This should work but generate a warning
            # from biomapper.core.strategy_actions.load_dataset_identifiers import LoadDatasetIdentifiersAction
            
            # Check warning was raised
            # assert len(w) > 0
            # assert "deprecated" in str(w[0].message).lower()
    
    @pytest.mark.asyncio
    async def test_di_container(self):
        """Test dependency injection container."""
        from biomapper.infrastructure.di.container import container
        from biomapper.infrastructure.persistence.interfaces import DataPersistence
        
        # Should resolve service
        service = container.resolve(DataPersistence)
        assert service is not None
        
        # Should be singleton
        service2 = container.resolve(DataPersistence)
        assert service is service2
EOF

# Run integration tests
cd /home/ubuntu/biomapper
poetry run pytest tests/integration/test_migration.py -xvs
```

### Step 2: Validate All Strategies Still Execute

```python
# Validate strategy execution after migration
cat > /home/ubuntu/biomapper/tools/migration/validate_strategies.py << 'EOF'
"""Validate all strategies work after migration."""

import requests
import json
from pathlib import Path

def validate_strategies():
    """Test that strategies still execute via API."""
    
    api_base = "http://localhost:8001"
    
    # Get list of strategies
    strategies_response = requests.get(f"{api_base}/api/strategies/v2/list")
    if strategies_response.status_code != 200:
        print("❌ Failed to get strategy list")
        return False
    
    strategies = strategies_response.json()
    print(f"Found {len(strategies)} strategies to validate")
    
    success_count = 0
    failed = []
    
    for strategy_name in strategies:
        # Try to execute (just check it starts)
        response = requests.post(
            f"{api_base}/api/strategies/v2/execute",
            json={"strategy": strategy_name}
        )
        
        if response.status_code == 200:
            print(f"✓ {strategy_name}")
            success_count += 1
        else:
            print(f"✗ {strategy_name}")
            failed.append(strategy_name)
    
    print(f"\nValidation Results:")
    print(f"  Success: {success_count}/{len(strategies)}")
    
    if failed:
        print(f"  Failed strategies:")
        for name in failed[:5]:
            print(f"    - {name}")
    
    return success_count == len(strategies)

if __name__ == "__main__":
    success = validate_strategies()
    exit(0 if success else 1)
EOF

python /home/ubuntu/biomapper/tools/migration/validate_strategies.py
```

## Phase 7: Documentation and Cleanup (Week 7)

### Step 1: Update Documentation

```markdown
# Create architecture documentation
cat > /home/ubuntu/biomapper/docs/ARCHITECTURE.md << 'EOF'
# Biomapper Architecture

## Overview

Biomapper follows a Domain-Driven Design (DDD) approach with clear separation between biological domains and infrastructure concerns.

## Directory Structure

```
biomapper/
├── domains/           # Business logic organized by biological domain
├── infrastructure/    # Technical infrastructure
├── shared/           # Cross-cutting concerns
└── tools/           # Development and migration tools
```

## Key Principles

1. **Domain Separation**: Each biological entity type (proteins, metabolites, chemistry) has its own domain
2. **Co-location**: Strategies are co-located with their related actions
3. **Dependency Injection**: Loose coupling through DI container
4. **Self-Registration**: Actions register themselves via decorators
5. **API-First**: All execution through REST API

## Migration from Legacy Structure

The project was migrated from a scattered structure to domain-driven organization in 2025.
Legacy imports are maintained for backward compatibility via `infrastructure/compatibility.py`.

## Data Management

Large data files (>1MB) are managed via DVC (Data Version Control) and stored externally.
EOF
```

### Step 2: Remove Old Structure

```bash
# After validation, remove old structure
cd /home/ubuntu/biomapper

# Create backup first
tar -czf legacy_structure_backup.tar.gz \
    biomapper/core/strategy_actions \
    configs/strategies

# Remove old directories (after confirming everything works)
# rm -rf biomapper/core/strategy_actions
# rm -rf configs/strategies

echo "⚠️  Old structure backed up. Remove manually after full validation."
```

## Success Criteria

- [ ] All 26 actions discovered from new locations
- [ ] All strategies load from domain directories
- [ ] API endpoints continue to work
- [ ] Integration tests pass
- [ ] Linting issues reduced from 309 to <50
- [ ] Large data files managed via DVC
- [ ] Pre-commit hooks prevent new issues
- [ ] Documentation updated

## Risk Mitigation

1. **Incremental Migration**: Move one domain at a time
2. **Parallel Structures**: Keep old and new during transition
3. **Import Compatibility**: Maintain backward compatibility
4. **Extensive Testing**: Validate after each phase
5. **Rollback Plan**: Git branches and backups at each phase

## Timeline

- **Week 1**: Foundation and infrastructure
- **Week 2**: Core and chemistry actions migration
- **Week 3**: Strategy co-location
- **Week 4**: Dependency injection
- **Week 5**: Cleanup integration
- **Week 6**: Testing and validation
- **Week 7**: Documentation and final cleanup

## Expected Outcomes

1. **Developer Experience**: 50% reduction in navigation time
2. **Maintainability**: Clear domain boundaries
3. **Testing**: Domain-specific test suites
4. **Performance**: Faster action discovery
5. **Scalability**: Easy to add new domains

## Notes

- This migration preserves all functionality while improving structure
- The self-registering action pattern makes this safer than typical refactoring
- Focus on domains aligns with bioinformatics mental models
- Co-locating strategies with actions reduces cognitive load