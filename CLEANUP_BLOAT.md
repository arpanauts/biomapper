# Biomapper Bloat Cleanup Plan

## Files to Archive/Remove

### 1. Investigation/Test Scripts in Root (Move to archive/)
```bash
# Create archive directory
mkdir -p archive/investigation_scripts
mkdir -p archive/old_reports
mkdir -p archive/old_tests

# Move investigation scripts
mv test_*.py archive/investigation_scripts/
mv manual_pattern_analysis.py archive/investigation_scripts/
mv pattern_analysis_pipeline.py archive/investigation_scripts/
mv run_integration_tests_direct.py archive/investigation_scripts/

# Move old reports
mv *_REPORT.md archive/old_reports/
mv *_report.md archive/old_reports/
mv *_summary.md archive/old_reports/
mv CRITICAL_FIX_REQUIRED.md archive/old_reports/

# Keep only essential docs in root
# KEEP: README.md, CLAUDE.md, BIOMAPPER_ARCHITECTURE_ROADMAP.md, GOOGLE_DRIVE_SETUP.md
```

### 2. Deprecated Code to Remove
- `biomapper/core/deprecated/` - Old implementations
- `biomapper/core/base_*.py` - Old base classes not used by current architecture
- `biomapper/mapping/` - Old mapping system (replaced by strategy actions)
- `biomapper/ontology/` - Not used in current YAML/action architecture
- `biomapper/rag/` - RAG system not part of core
- `biomapper/workflows/` - Old workflow system

### 3. Unused Config Directories
- `configs/prompts/` - Old prompt files for development
- `configs/schemas/` - If not used by current system
- Any test/example configs not in active use

### 4. Test Files to Clean
- Old test versions (v1, v2, v3 variants)
- Tests for deprecated modules
- Integration tests for removed features

### 5. Data Files to Manage
- Move large data files to data/ directory
- Set up .gitignore for data files
- Document required data in README

## Core Architecture to KEEP

### Essential Components
```
biomapper/
├── core/
│   ├── strategy_actions/     # KEEP - Core action system
│   │   ├── registry.py       # KEEP - Action registry
│   │   ├── typed_base.py     # KEEP - Base classes
│   │   └── [action files]    # KEEP - All registered actions
│   ├── minimal_strategy_service.py  # KEEP - Core executor
│   ├── infrastructure/       # KEEP - Parameter resolution, etc
│   ├── models/               # KEEP - Pydantic models
│   └── exceptions.py         # KEEP - Error handling

biomapper-api/
├── app/                      # KEEP - All API code
│   ├── main.py
│   ├── services/
│   └── api/routes/

biomapper_client/             # KEEP - Client library

configs/
├── strategies/               # KEEP - YAML strategies
│   └── experimental/

tests/
├── unit/                     # KEEP - Active unit tests
└── integration/              # KEEP - Active integration tests
```

## Commands to Execute

```bash
# 1. Create archive structure
mkdir -p archive/{investigation_scripts,old_reports,old_tests,deprecated_code}

# 2. Move investigation files
mv test_*.py archive/investigation_scripts/ 2>/dev/null
mv *_pattern_*.py archive/investigation_scripts/ 2>/dev/null
mv run_integration_tests_direct.py archive/investigation_scripts/ 2>/dev/null

# 3. Move reports (keep roadmap and setup guides)
mv *_REPORT.md archive/old_reports/ 2>/dev/null
mv *_report.md archive/old_reports/ 2>/dev/null
mv *_summary.md archive/old_reports/ 2>/dev/null
mv CRITICAL_FIX_REQUIRED.md archive/old_reports/ 2>/dev/null

# 4. Move deprecated code
mv biomapper/core/deprecated archive/deprecated_code/ 2>/dev/null
mv biomapper/mapping archive/deprecated_code/ 2>/dev/null
mv biomapper/ontology archive/deprecated_code/ 2>/dev/null
mv biomapper/rag archive/deprecated_code/ 2>/dev/null
mv biomapper/workflows archive/deprecated_code/ 2>/dev/null

# 5. Clean up prompts
mv configs/prompts archive/ 2>/dev/null

# 6. Remove old base classes if not used
# Check first: grep -r "BaseMapper\|BaseLLM\|BaseRAG" biomapper/ --include="*.py"
```

## Verification After Cleanup

```bash
# Verify core system still works
poetry run pytest tests/unit/core/strategy_actions/ -q
poetry run biomapper health
curl http://localhost:8001/api/health

# Check action registration
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; print(f'Actions: {len(ACTION_REGISTRY)}')"
```