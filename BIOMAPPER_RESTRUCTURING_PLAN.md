# BiomMapper Project Restructuring Plan

## Executive Summary

The biomapper project has grown to 586 Python files with 154,360 lines of code, containing significant technical debt including 15+ duplicate implementations, scattered tests, and complex dependencies. This restructuring plan provides a phased approach to reduce complexity by 60% while maintaining full functionality.

## Current State Analysis

### Critical Metrics
- **586 Python files** across multiple package hierarchies
- **283 external dependencies** with heavy concentration on pandas/typing
- **51 action implementations** with registry bottleneck (71 file dependencies)
- **187 test files** with 20+ scattered outside proper test directories
- **15+ major duplicate implementations** including multiple versions of visualization, parsing, and sync systems

### Top Issues Requiring Immediate Attention

1. **Duplicate Implementation Crisis**
   - 2 visualization systems (76K lines combined)
   - 2 data parsing systems (25K lines combined)
   - 2 Google Drive sync implementations (31K lines combined)
   - 3 CLI implementations
   - Multiple client versions

2. **Test Architecture Chaos**
   - Root-level test pollution (20+ files)
   - No consistent test organization
   - Mixed unit/integration tests
   - Duplicate test implementations

3. **Configuration Sprawl**
   - 74 YAML strategy files
   - 47 experimental strategies
   - Multiple config directories
   - Versioned strategies without deprecation

## Proposed Target Architecture

### Clean Package Structure
```
biomapper/
├── core/
│   ├── actions/          # Consolidated action system
│   │   ├── base/        # Registry and base classes
│   │   ├── entities/    # Biological entity actions
│   │   ├── io/          # Single I/O implementation
│   │   ├── reports/     # Unified reporting
│   │   └── utils/       # Shared utilities
│   ├── standards/       # Keep existing (working well)
│   └── services/        # Core services
├── api/                 # FastAPI service (renamed)
├── client/              # Python client (renamed)
└── tests/               # All tests consolidated here
    ├── unit/           # Fast tests (<1s)
    ├── integration/    # Medium tests (<10s)
    └── performance/    # Performance tests
```

### Configuration Consolidation
```
configs/
├── strategies/
│   ├── production/      # Stable, tested strategies
│   ├── templates/       # Starting points for new work
│   └── experimental/    # Max 10 active experiments
└── environments/        # Environment-specific settings
```

## Implementation Phases

### Phase 1: Foundation Cleanup (Week 1)
**Risk: LOW | Impact: HIGH**

#### Actions:
1. **Test Consolidation**
   ```bash
   # Move scattered tests to proper locations
   mkdir -p tests/{unit,integration,performance}
   find . -name "test_*.py" -not -path "*/tests/*" -exec mv {} tests/unit/ \;
   ```

2. **Remove Obvious Duplicates**
   - Delete duplicate conftest.py files
   - Remove empty __init__.py files
   - Clean up archive directory completely

3. **Archive Old Experiments**
   ```bash
   mkdir -p configs/strategies/archive
   # Move strategies older than 6 months
   find configs/strategies/experimental -mtime +180 -exec mv {} configs/strategies/archive/ \;
   ```

#### Success Criteria:
- All tests in `/tests/` hierarchy
- No duplicate conftest.py files
- <20 experimental strategies remaining

### Phase 2: Code Deduplication (Week 2-3)
**Risk: MEDIUM | Impact: VERY HIGH**

#### Priority Order:
1. **Visualization Consolidation**
   - Keep `generate_visualizations_v2.py`
   - Archive original version
   - Update all references

2. **Data Parsing Unification**
   - Keep `parse_composite_identifiers_v2.py`
   - Migrate all consumers to v2
   - Remove v1

3. **Google Drive Sync Standardization**
   - Keep `sync_to_google_drive_v2.py`
   - Update action registry
   - Remove v1

#### Migration Script:
```python
# Update imports programmatically
import os
import re

def update_imports(old_module, new_module):
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                updated = re.sub(
                    f'from {old_module} import',
                    f'from {new_module} import',
                    content
                )
                if updated != content:
                    with open(filepath, 'w') as f:
                        f.write(updated)
```

### Phase 3: Package Restructuring (Week 4-5)
**Risk: MEDIUM-HIGH | Impact: HIGH**

#### Steps:
1. **Rename Major Packages**
   ```bash
   # Create new structure
   mv biomapper-api biomapper/api
   mv biomapper_client biomapper/client
   mv biomapper/core/strategy_actions biomapper/core/actions
   ```

2. **Create Compatibility Layer**
   ```python
   # biomapper-api/__init__.py (temporary)
   import sys
   import warnings
   warnings.warn("biomapper-api is deprecated, use biomapper.api", DeprecationWarning)
   sys.modules['biomapper-api'] = sys.modules['biomapper.api']
   ```

3. **Update Entry Points**
   ```toml
   # pyproject.toml
   [tool.poetry.scripts]
   biomapper = "biomapper.cli.main:app"
   ```

### Phase 4: Registry Optimization (Week 6)
**Risk: HIGH | Impact: MEDIUM**

#### Implementation:
1. **Lazy Loading Registry**
   ```python
   # biomapper/core/actions/registry.py
   class LazyActionRegistry:
       def __init__(self):
           self._actions = {}
           self._loaded = set()
       
       def get_action(self, name):
           if name not in self._loaded:
               self._load_action(name)
           return self._actions[name]
   ```

2. **Plugin Discovery System**
   ```python
   # biomapper/core/actions/discovery.py
   def discover_actions():
       action_modules = []
       for path in Path('biomapper/core/actions').rglob('*.py'):
           if '@register_action' in path.read_text():
               action_modules.append(path)
       return action_modules
   ```

## Risk Mitigation Strategy

### Pre-Migration Checklist
- [ ] Full backup of current state
- [ ] Document all current import paths
- [ ] Create test baseline metrics
- [ ] Notify team of changes
- [ ] Prepare rollback plan

### Testing Protocol
```bash
# Before each phase
poetry run pytest --co -q | wc -l  # Count tests
poetry run pytest                  # Ensure all pass

# After each change
poetry run pytest tests/integration/  # Quick validation
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; print(len(ACTION_REGISTRY))"

# Final validation
python scripts/run_three_level_tests.py all
```

### Rollback Procedures
1. Git tags before each phase: `git tag pre-phase-1`
2. Compatibility layers for 30 days minimum
3. Dual import paths during transition
4. Monitoring of CI/CD pipelines

## Success Metrics

### Quantitative Goals
| Metric | Current | Target | Reduction |
|--------|---------|--------|-----------|
| Duplicate Implementations | 15+ | 3 | 80% |
| Scattered Test Files | 20+ | 0 | 100% |
| Registry Dependencies | 71 | 20 | 72% |
| Files >800 lines | 8 | 2 | 75% |
| Experimental Strategies | 47 | 10 | 79% |

### Qualitative Goals
- **Developer Experience**: 50% faster to locate and modify functionality
- **Onboarding Time**: New developers productive in 2 days (vs current 5 days)
- **CI/CD Performance**: 30% faster test execution
- **Maintenance Burden**: 60% reduction in duplicate bug fixes

## Timeline Summary

| Week | Phase | Risk | Key Deliverables |
|------|-------|------|------------------|
| 1 | Foundation Cleanup | LOW | Tests consolidated, duplicates removed |
| 2-3 | Code Deduplication | MEDIUM | Major duplicates eliminated |
| 4-5 | Package Restructuring | MEDIUM-HIGH | Clean package hierarchy |
| 6 | Registry Optimization | HIGH | Lazy loading implemented |
| 7-8 | Stabilization | LOW | Documentation, testing, monitoring |

## Next Steps

1. **Immediate Action**: Run Phase 1 cleanup (low risk, high impact)
2. **Team Alignment**: Review plan with stakeholders
3. **Create Tracking**: Set up project board for migration tasks
4. **Begin Documentation**: Update CLAUDE.md with new structure

## Appendix: Quick Reference Commands

```bash
# Count current state
find . -name "*.py" | wc -l
find . -name "test_*.py" | wc -l
grep -r "@register_action" --include="*.py" . | wc -l

# Identify duplicates
find . -name "*_v2.py" -o -name "*_v3.py" -o -name "*_old.py"

# Test coverage baseline
poetry run pytest --cov=biomapper --cov-report=term-missing

# Validate strategies still load
python -c "from biomapper.core.minimal_strategy_service import MinimalStrategyService; print('Strategy loading OK')"
```

This plan provides a systematic approach to transform biomapper from a complex, duplicative codebase into a clean, maintainable system while preserving functionality and minimizing disruption.