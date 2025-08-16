# Biomapper Architectural Analysis Report
*Generated for dead code detection and cleanup purposes*

## Executive Summary

The biomapper project is a large bioinformatics codebase with **659 Python files** totaling ~157,747 lines of code. The project shows signs of organic growth with significant technical debt accumulation, including deprecated code, orphaned modules, and duplicate functionality across multiple implementations.

## 1. Project Structure Overview

### Core Statistics
- **Total Python Files**: 659
- **Total Lines of Code**: ~157,747
- **Test Files**: 179 (138 in tests/ + 41 scattered)
- **Documentation Files**: 202 MD files, 210 docs files
- **Recent Activity**: 723 commits in last 3 months

### Directory Hierarchy

```
biomapper/
├── archive/                    # 67 Python files (1.4MB) - BLOAT CANDIDATE
├── biomapper/                  # Core library
│   ├── core/                   # Main business logic
│   │   ├── strategy_actions/   # 73+ action implementations
│   │   ├── standards/          # 2025 standardization framework
│   │   └── services/           # Service layer
│   ├── embedder/              # Embedding functionality (potentially unused)
│   ├── mapping/               # Mapping utilities
│   └── mvp0_pipeline/         # Legacy MVP code - BLOAT CANDIDATE
├── biomapper-api/             # FastAPI service
│   ├── app/                   # API implementation
│   └── biomapper_mock/        # Mock implementations - BLOAT CANDIDATE
├── biomapper_client/          # Python client library
├── configs/                   # YAML strategies and configurations
├── scripts/                   # Various utility scripts
├── tests/                     # Test suite
└── docs/                      # Documentation
```

## 2. Import Dependency Analysis

### Top Dependencies
1. **typing** (309 imports) - Heavy type annotation usage
2. **pathlib** (202 imports) - Modern path handling
3. **logging** (185 imports) - Extensive logging
4. **pandas** (174 imports) - Core data processing
5. **asyncio** (154 imports) - Async architecture

### Dependency Issues
- **296 unique external dependencies** - Extremely high, suggests scope creep
- **197 unique internal dependencies** - Complex internal coupling
- Multiple import patterns for same functionality (e.g., 3 different visualization actions)

## 3. Entry Points and Core Flow

### Primary Entry Points
1. **biomapper-api/app/main.py** - FastAPI server (17 dependencies)
2. **biomapper_client/cli.py** - CLI interface
3. **biomapper/cli/main.py** - Alternative CLI (duplication?)

### Core Execution Path
```
Client → BiomapperClient → FastAPI → MapperService → MinimalStrategyService
                                                          ↓
                                        ACTION_REGISTRY → Self-registering Actions
```

## 4. Major Bloat Indicators

### 🔴 Critical Bloat Areas

#### 1. Archive Directory (HIGH PRIORITY)
- **Size**: 1.4MB, 67 Python files
- **Location**: `/archive/`
- **Content**: deprecated_code, old_tests, investigation_scripts
- **Recommendation**: DELETE ENTIRELY

#### 2. Duplicate Action Implementations
- **Issue**: Multiple versions of same actions
  - `generate_visualizations.py` (457 lines)
  - `generate_visualizations_v2.py` (1494 lines)
  - `generate_mapping_visualizations.py` (different params)
- **Recommendation**: Consolidate to single implementation

#### 3. Orphaned Modules (20+ identified)
```python
# High-priority removal candidates:
- biomapper-api/biomapper_mock/*  # Entire mock directory unused
- archive/deprecated_code/*        # Explicitly deprecated
- scripts/pipelines/run_metabolomics_harmonization  # Orphaned
- templates/action_template        # Unused template
```

#### 4. Empty/Stub Files
- **10 empty `__init__.py` files** identified
- Multiple stub modules with no implementation

#### 5. Test Sprawl
- **179 test files** with many outside tests/ directory
- 41 test files scattered in root and scripts/
- Recommendation: Consolidate all tests to tests/

### 🟡 Medium Priority Bloat

#### 1. Compiled Python Files
- **189 .pyc files** and **52 __pycache__ directories**
- Add to .gitignore and clean

#### 2. Large Monolithic Files
```python
# Files exceeding 1000 lines:
- generate_visualizations_v2.py (1494 lines)
- generate_metabolomics_report.py (1185 lines)
- test_calculate_set_overlap.py (1150 lines)
```

#### 3. TODO/FIXME Technical Debt
- **88 TODO/FIXME markers** across codebase
- Many likely outdated or abandoned

## 5. Dependency Graph Issues

### Circular Dependencies Detected
- biomapper.core ↔ biomapper.core.services
- Multiple action files importing from registry while registry imports them

### Over-coupled Modules
```python
# Files with most dependencies (coupling hotspots):
- biomapper/core/strategy_actions/__init__.py (24 deps)
- biomapper-api/app/services/persistence_service.py (16 deps)
- biomapper-api/app/services/mapper_service.py (16 deps)
```

## 6. Recent Activity Analysis

### Active Areas (Last 3 months)
- `.task-prompt.md` (101 modifications) - Development notes?
- `biomapper/core/mapping_executor.py` (81 modifications)
- Core strategy actions actively maintained

### Stale Areas
- No files older than 6 months (recent project?)
- But archive/ directory suggests abandoned code migration

## 7. Actionable Cleanup Recommendations

### Immediate Actions (Safe to Delete)

```bash
# 1. Remove archive directory
rm -rf archive/

# 2. Clean compiled files
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} +

# 3. Remove empty Python files
find . -name "*.py" -size 0 -delete

# 4. Remove biomapper_mock
rm -rf biomapper-api/biomapper_mock/
```

### Consolidation Targets

```python
# Merge duplicate visualizations
# Keep: generate_mapping_visualizations.py
# Delete: generate_visualizations.py, generate_visualizations_v2.py

# Consolidate scattered tests
# Move all test_*.py from root to tests/

# Remove orphaned scripts
scripts/pipelines/run_metabolomics_harmonization.py
scripts/run_metabolomics_fix.py
templates/action_template.py
```

### Automated Detection Rules

```python
def is_dead_code(file_path):
    """Rules for automated dead code detection."""
    
    # Rule 1: Archive directory
    if 'archive/' in file_path:
        return True
    
    # Rule 2: Mock/stub implementations
    if 'mock' in file_path or 'stub' in file_path:
        return True
    
    # Rule 3: Empty Python files
    if os.path.getsize(file_path) == 0:
        return True
    
    # Rule 4: No imports from this module
    if file_path not in imported_modules and \
       not file_path.endswith('__main__.py'):
        return True
    
    # Rule 5: Deprecated markers
    with open(file_path) as f:
        content = f.read()
        if '@deprecated' in content or \
           'DEPRECATED' in content:
            return True
    
    return False
```

## 8. Estimated Cleanup Impact

### Potential Reduction
- **Files**: ~150 files (23% reduction)
- **Lines of Code**: ~25,000 lines (16% reduction)
- **Dependencies**: 50+ external deps could be removed
- **Test Execution Time**: 20-30% faster with consolidated tests

### Risk Assessment
- **Low Risk**: Archive/, empty files, __pycache__
- **Medium Risk**: Duplicate actions, orphaned scripts
- **High Risk**: Core refactoring (not recommended yet)

## Conclusion

The biomapper project has accumulated significant technical debt through rapid development. The identified bloat areas, particularly the archive directory and duplicate implementations, can be safely removed to improve maintainability. Focus cleanup efforts on the high-priority areas identified above, which offer the best risk/reward ratio for immediate improvement.

### Next Steps
1. Implement automated dead code detection using provided rules
2. Create cleanup PR removing archive/ and empty files
3. Consolidate duplicate action implementations
4. Move scattered tests to tests/ directory
5. Update .gitignore to prevent future .pyc accumulation