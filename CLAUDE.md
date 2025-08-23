# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 MANDATORY VALIDATION RULES (v3.1)

### Before ANY "SUCCESS!" Declaration:
1. **Run `/diagnose`** - 30-second comprehensive validation
2. **Run `python scripts/prevent_partial_victory.py`** - Blocks premature success
3. **All checks must pass** - No exceptions

### Quality Gates (Team-Wide Enforcement):
- **TDD Required**: Tests must exist before implementation
- **Parameter Validation**: All `${parameters.x}` must resolve
- **Import Verification**: All modules must load cleanly
- **Coverage Authentic**: No entity duplication allowed

### Quick Validation Commands:
```bash
# 30-second full diagnostic
/diagnose [strategy_name]

# Check specific issues
python scripts/check_yaml_params.py          # Parameter substitution
python scripts/check_import_paths.py         # Import paths
python scripts/check_authentic_coverage.py   # Biological coverage
python scripts/prevent_partial_victory.py    # Block false success

# TDD enforcement
python .claude/hooks/tdd_enforcer.py src/actions/my_action.py

# Emergency override (max 4 hours)
export BIOMAPPER_HOOKS_MODE="disabled"  # Temporary bypass
```

### Complete Command Reference:
- `/diagnose [strategy]` - 30-second comprehensive health check
- `/tdd-strategy <entity> <source> <target>` - Generate TDD-enforced strategy
- `/fix-imports [module]` - Resolve import path issues
- `/validate-end-to-end [strategy]` - Full pipeline validation
- `/biomapper-strategy` - Existing strategy development (enhanced with hooks)

### Automatic Hook System:
**Hooks run automatically - no manual commands needed:**
- **Edit Python file** → TDD check → Blocks if no test exists
- **Edit YAML strategy** → Parameter check → Blocks if invalid
- **Save Python file** → Import check → Warns on failures
- **Type "SUCCESS!"** → Victory check → Requires full validation

### Hook Status & Control:
```bash
# Check hook status
cat .claude/config/hooks-config.yaml | grep mode

# Temporary disable (emergency only)
export BIOMAPPER_HOOKS_MODE="disabled"  # Disables all hooks
export BIOMAPPER_HOOKS_MODE="warn"      # Warnings only
export BIOMAPPER_HOOKS_MODE="enforce_all"  # Full enforcement

# View hook configuration
ls -la .claude/hooks/*.toml
```

### Anti-Patterns BLOCKED:
❌ **"SUCCESS!" without validation** - Run `/diagnose` first
❌ **Parameter hardcoding** - Use `${parameters.x}` not `/home/user/`
❌ **Implementation before tests** - TDD enforced
❌ **Coverage inflation** - Unique entities only

## Essential Commands

```bash
# Setup and environment
poetry install --with dev,docs,api
poetry shell

# Environment configuration (NEW - 2025 standards)
python scripts/setup_environment.py        # Interactive environment setup wizard
poetry run python -c "from biomapper.core.standards.env_manager import EnvironmentManager; EnvironmentManager().validate_requirements(['google_drive'])"

# Run tests (Enhanced with three-level framework)
poetry run pytest                           # All tests with coverage
poetry run pytest tests/unit/               # Unit tests only (Level 1 - fast)
poetry run pytest tests/integration/        # Integration tests only (Level 2 - medium)
poetry run pytest -k "test_name"            # Run specific test by name
poetry run pytest -xvs tests/path/test.py   # Debug single test with output
python scripts/run_three_level_tests.py all # Run standardized three-level tests

# Code quality (run before committing)
poetry run ruff format .                    # Format code
poetry run ruff check . --fix               # Fix auto-fixable linting issues
poetry run mypy biomapper biomapper-api biomapper_client  # Type checking

# Performance and complexity analysis (NEW)
python audits/complexity_audit.py           # Detect O(n^2)+ performance issues
python scripts/investigate_identifier.py Q6EMK4  # Debug edge cases

# Development server
cd biomapper-api && poetry run uvicorn app.main:app --reload --port 8000

# Database operations
poetry run alembic upgrade head             # Apply migrations
poetry run alembic revision -m "description"  # Create new migration

# Makefile shortcuts
make test                                   # Run tests with coverage
make format                                 # Format code with ruff
make lint-fix                              # Auto-fix linting issues
make typecheck                             # Run mypy type checking
make check                                 # Run all checks (format, lint, typecheck, test, docs)
make docs                                  # Build documentation
make clean                                 # Clean cache files

# CLI usage
poetry run biomapper --help
poetry run biomapper health
poetry run biomapper metadata list

# CI diagnostics
python scripts/ci_diagnostics.py           # Check for common CI issues
make ci-test-local                         # Test in Docker CI environment
```

## Architecture Overview

```
Client Request → BiomapperClient → FastAPI Server → MapperService → MinimalStrategyService
                                                                     ↓
                                                    ACTION_REGISTRY (Global Dict)
                                                                     ↓
                                              Self-Registering Action Classes
                                                                     ↓
                                                 Execution Context (shared state)
```

### Core Components

**src/actions/** - Action implementations with entity-based organization
- Actions self-register via `@register_action("ACTION_NAME")` decorator
- Organized by biological entity: proteins/, metabolites/, chemistry/
- TypedStrategyAction pattern for type safety

**src/api/** - FastAPI service exposing REST endpoints
- Direct YAML loading from `src/configs/strategies/` directory at runtime
- SQLite job persistence (`biomapper.db`) with checkpointing
- Background job execution with real-time SSE progress updates

**src/client/** - Python client for the API
- Primary interface via `BiomapperClient` in `client_v2.py`
- Synchronous wrapper: `client.run("strategy_name")`
- No direct imports from core library

**src/core/** - Core business logic and infrastructure
- `MinimalStrategyService` provides lightweight strategy execution
- Execution context flows as `Dict[str, Any]` with keys: `current_identifiers`, `datasets`, `statistics`, `output_files`
- Standards modules for 2025 standardizations

## 🎉 BIOMAPPER 2025 STANDARDIZATIONS

This codebase has undergone comprehensive standardization (January 2025) with **1,297 tests** and production-ready architecture. **ALWAYS** follow these standards:

## ✅ Test Suite Status (2025)

**COMPREHENSIVE TEST RESTORATION COMPLETED**
- **1,297 tests collected** with comprehensive coverage
- **Unit Tests**: 99.3% success rate (1,209 passed, 86 skipped)  
- **Integration Tests**: 100% success rate (8 passed, 7 skipped)
- **Test Coverage**: 79.69% approaching 80% target
- **Architecture**: Barebones client → API → MinimalStrategyService → Actions achieved

**Key Test Categories Restored:**
- ✅ API Components, Core Infrastructure, Client Libraries
- ✅ Standards Modules, Strategy Actions, Integration Clients
- ✅ Async HTTP mocking (migrated responses→respx), Pydantic v2 compatibility
- ✅ Biological data patterns, error handling, edge cases

### 1. Parameter Naming Standard ✅
- **376 parameters standardized** across 72 files
- Use `input_key`, `output_key`, `file_path` (not `dataset_key`, `filepath`, etc.)
- Validator: `from src.core.standards.parameter_validator import ParameterValidator` (if available)
- Standard: `/home/ubuntu/biomapper/dev/standards/PARAMETER_NAMING_STANDARD.md`

### 2. Context Type Handling ✅  
- **Universal context wrapper** handles dict/object/ContextAdapter patterns
- Use: `from biomapper.core.standards.context_handler import UniversalContext`
- Pattern: `ctx = UniversalContext.wrap(context); datasets = ctx.get_datasets()`
- Eliminates defensive programming (`if hasattr(context, 'get')...`)

### 3. Algorithm Complexity Standards ✅
- **O(n^5) bottlenecks identified** and optimization tools created
- Use: `from biomapper.core.algorithms.efficient_matching import EfficientMatcher`
- Audit: `python audits/complexity_audit.py` (18 critical issues found)
- Guide: `/home/ubuntu/biomapper/dev/standards/ALGORITHM_COMPLEXITY_GUIDE.md`

### 4. Identifier Normalization ✅
- **Handles format variations** causing 99%+ match failures  
- Use: `from biomapper.core.standards.identifier_registry import normalize_identifier`
- Supports: UniProt (`UniProtKB:P12345` → `P12345`), HMDB, Ensembl, etc.
- Performance: >100k identifiers/second

### 5. File Loading Robustness ✅
- **Auto-detection** of encoding, delimiters, comments, NA values
- Use: `from biomapper.core.standards.file_loader import BiologicalFileLoader`
- Features: Chunked loading, 25+ NA variants, biological data optimized
- Eliminates 5+ production file loading failures

### 6. API Method Alignment ✅
- **Zero silent API failures** through comprehensive validation
- Use: `from biomapper.core.standards.api_validator import APIMethodValidator`
- Registry: Pre-defined specs for UniProt, ChEMBL, PubChem, HMDB
- Prevents `get_uniprot_data` vs `get_protein_data` confusion

### 7. Environment Configuration ✅
- **Centralized env management** with validation and auto-discovery
- Use: `from biomapper.core.standards.env_manager import EnvironmentManager`
- Setup: `python scripts/setup_environment.py` (interactive wizard)
- Prevents 5+ credential/path failures

### 8. Pydantic Model Flexibility ✅
- **Backward compatible** models accept extra fields gracefully
- Use: `from biomapper.core.standards.base_models import ActionParamsBase`
- Features: Universal debug/trace flags, parameter migration
- Prevents 6+ validation failures

### 9. Edge Case Debugging ✅
- **Systematic investigation** framework for complex issues (Q6EMK4)
- Use: `from biomapper.core.standards.debug_tracer import DebugTracer`
- Tools: `python scripts/investigate_identifier.py Q6EMK4`
- Registry: Documents known issues with workarounds

### 10. Testing Strategy Standardization ✅
- **Three-level testing** framework with realistic biological data
- Levels: Unit (<1s), Integration (<10s), Production subset (<60s)
- Use: `python scripts/run_three_level_tests.py proteins --performance`
- Framework: Detects performance issues before production

## Creating New Strategy Actions

**CRITICAL**: Follow all 10 standardizations above. Use the new enhanced workflow:

### Step 1: Use Standardized Base Classes

```python
# Use standardized imports and base classes
from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.standards.base_models import ActionParamsBase  # NEW: Flexible base
from biomapper.core.standards.context_handler import UniversalContext  # NEW: Context handling
from biomapper.core.standards.identifier_registry import normalize_identifier  # NEW: ID normalization
from pydantic import Field

# 1. PARAMETER NAMING: Use standardized names
class MyActionParams(ActionParamsBase):  # NEW: Inherits debug/trace/timeout
    input_key: str = Field(..., description="Input dataset key")  # STANDARD NAME
    threshold: float = Field(0.8, description="Processing threshold")
    output_key: str = Field(..., description="Output dataset key")  # STANDARD NAME
    
    # NEW: Parameter validation using standards
    def validate_params(self) -> bool:
        from src.core.standards.parameter_validator import ParameterValidator
        return ParameterValidator.validate_action_params(self.dict())

@register_action("MY_ACTION")
class MyAction(TypedStrategyAction[MyActionParams, ActionResult]):
    def get_params_model(self) -> type[MyActionParams]:
        return MyActionParams
    
    async def execute_typed(self, params: MyActionParams, context: Dict) -> ActionResult:
        # 2. CONTEXT HANDLING: Use universal wrapper
        ctx = UniversalContext.wrap(context)
        input_data = ctx.get_dataset(params.input_key)
        
        # 3. IDENTIFIER NORMALIZATION: Standardize biological IDs
        if 'uniprot_ids' in input_data.columns:
            input_data['normalized_ids'] = input_data['uniprot_ids'].apply(
                lambda x: normalize_identifier(x).base_id if normalize_identifier(x) else x
            )
        
        # 4. ALGORITHM COMPLEXITY: Use efficient patterns
        from biomapper.core.algorithms.efficient_matching import EfficientMatcher
        if len(input_data) > 1000:  # Large dataset
            matcher = EfficientMatcher()
            results = matcher.match_with_index(source_data, target_index, key_func)
        
        # 5. FILE LOADING: Use robust loader if needed
        if hasattr(params, 'file_path'):
            from biomapper.core.standards.file_loader import BiologicalFileLoader
            loader = BiologicalFileLoader()
            loaded_data = loader.load_file(params.file_path)
        
        # 6. API VALIDATION: Validate API clients
        if hasattr(self, '_api_client'):
            from biomapper.core.standards.api_validator import APIMethodValidator
            APIMethodValidator.validate_client_interface(self._api_client, ['required_method'])
        
        # Store results using standardized context
        ctx.set_dataset(params.output_key, processed_data)
        
        return ActionResult(success=True, message=f"Processed {len(processed_data)} items")
```

### Step 2: Write Three-Level Tests (NEW Standard)

```python
# tests/unit/core/strategy_actions/test_my_action.py
from biomapper.testing.base import ActionTestBase
from biomapper.testing.data_generator import BiologicalDataGenerator

class TestMyAction(ActionTestBase):
    def test_level_1_minimal_data(self):
        """Level 1: Fast unit test with minimal data (<1s)"""
        minimal_data = BiologicalDataGenerator.generate_uniprot_dataset(5)
        result = await self.execute_action_with_data("MY_ACTION", minimal_data)
        assert result.success
    
    def test_level_2_sample_data(self):
        """Level 2: Integration test with sample data (<10s)"""
        sample_data = BiologicalDataGenerator.generate_uniprot_dataset(1000)
        result = await self.execute_action_with_data("MY_ACTION", sample_data)
        assert result.success
        # Performance assertions
        self.assert_complexity_linear(result.execution_time, len(sample_data))
    
    def test_level_3_production_subset(self):
        """Level 3: Production subset with real data patterns (<60s)"""
        prod_data = self.load_production_subset("arivale_proteins", 5000)
        result = await self.execute_action_with_data("MY_ACTION", prod_data)
        assert result.success
        # Real-world edge case validation
        assert result.data['edge_cases_handled'] > 0
```

Action will auto-register - no executor modifications needed.

## Enhanced Action Organization

Actions are organized by biological entity and function:

```
strategy_actions/
├── entities/                    # Entity-specific actions
│   ├── proteins/                # UniProt, Ensembl, gene symbols
│   │   ├── annotation/          # ID extraction & normalization
│   │   └── matching/            # Cross-dataset resolution
│   ├── metabolites/             # HMDB, InChIKey, CHEBI, KEGG
│   │   ├── identification/      # ID extraction & normalization
│   │   ├── matching/            # CTS, semantic, vector matching
│   │   └── enrichment/          # External API integration
│   └── chemistry/               # LOINC, clinical tests
│       ├── identification/      # LOINC extraction
│       └── matching/            # Fuzzy test matching
├── algorithms/                  # Reusable algorithms
├── utils/                       # General utilities
├── workflows/                   # High-level orchestration
├── io/                         # Data input/output
└── reports/                    # Analysis & reporting
```

## Creating YAML Strategies

Place strategies in `src/configs/strategies/` following the naming convention:
- **Strategy files**: `entity_source_to_target_method_vX.Y.yaml`
- **Client scripts**: `scripts/pipelines/entity_source_to_target_method_vX.Y.py`  
- Example: `prot_arv_to_kg2c_uniprot_v3.0.yaml` with client `prot_arv_to_kg2c_uniprot_v3.0.py`
- Do NOT use suffixes like `_progressive` - the strategy type is defined in the YAML content

```yaml
name: prot_arv_to_kg2c_uniprot_v3.0
description: Clear description of purpose
parameters:
  data_file: "/path/to/data.tsv"
  output_dir: "${OUTPUT_DIR:-/tmp/results}"
  
steps:
  - name: load_data
    action:
      type: LOAD_DATASET_IDENTIFIERS
      params:
        file_path: "${parameters.data_file}"
        identifier_column: id
        output_key: loaded_data
        
  - name: process
    action:
      type: MY_ACTION
      params:
        input_key: loaded_data
        threshold: 0.85
        output_key: processed_data
```

Variable substitution supports:
- `${parameters.key}` - Strategy parameters
- `${metadata.field}` - Metadata fields
- `${env.VAR}` or `${VAR}` - Environment variables

## Available Actions

**Data Operations:**
- `LOAD_DATASET_IDENTIFIERS` - Load biological identifiers from TSV/CSV
- `MERGE_DATASETS` - Combine datasets with deduplication
- `FILTER_DATASET` - Apply filtering criteria
- `EXPORT_DATASET` - Export to various formats
- `CUSTOM_TRANSFORM` - Apply Python expressions to columns

**Mapping Operations:**
- `MERGE_WITH_UNIPROT_RESOLUTION` - Map to UniProt accessions
- `CALCULATE_SET_OVERLAP` - Jaccard similarity analysis
- `CALCULATE_THREE_WAY_OVERLAP` - Three-dataset comparison

**Metabolomics:**
- `NIGHTINGALE_NMR_MATCH` - Nightingale NMR reference matching
- `CTS_ENRICHED_MATCH` - Chemical Translation Service matching
- `METABOLITE_API_ENRICHMENT` - External API enrichment
- `SEMANTIC_METABOLITE_MATCH` - AI-powered semantic matching
- `VECTOR_ENHANCED_MATCH` - Vector similarity matching
- `COMBINE_METABOLITE_MATCHES` - Merge multiple approaches
- `GENERATE_METABOLOMICS_REPORT` - Comprehensive reports

**IO Operations:**
- `SYNC_TO_GOOGLE_DRIVE` - Upload results to Google Drive with chunked transfer

**Protein Operations:**
- `PROTEIN_EXTRACT_UNIPROT_FROM_XREFS` - Extract UniProt IDs from compound fields
- `PROTEIN_NORMALIZE_ACCESSIONS` - Standardize protein identifiers

**Chemistry Operations:**
- `CHEMISTRY_EXTRACT_LOINC` - Extract LOINC codes from clinical data

## Testing Strategy

Follow Test-Driven Development (TDD):

1. Write failing tests first
2. Implement minimal code to pass
3. Refactor while keeping tests green

```bash
# Test specific action
poetry run pytest -xvs tests/unit/core/strategy_actions/test_my_action.py

# Test with coverage
poetry run pytest --cov=biomapper --cov-report=html

# Debug test failures
poetry run pytest -xvs --pdb tests/unit/
```

## Type Safety Migration

Project is migrating to full type safety using TypedStrategyAction pattern:
- Business logic actions use TypedStrategyAction with Pydantic models
- Infrastructure actions (like chunk_processor) remain flexible
- Backward compatibility maintained with `extra="allow"` in Pydantic models
- All new actions must use typed pattern

## Key Implementation Patterns

### Context Flow
Actions receive and modify shared `context` dictionary:
- `context["datasets"][key]` - Access datasets from previous actions
- `context["statistics"]` - Accumulate statistics
- `context["output_files"]` - Track generated files
- `context["current_identifiers"]` - Active identifier set

### Error Handling
```python
from biomapper.core.exceptions import ValidationError, ProcessingError

try:
    result = process_data(input_data)
except ValidationError as e:
    return ActionResult(success=False, message=str(e))
```

### Parameter Validation
```python
from pydantic import BaseModel, Field, validator

class MyParams(BaseModel):
    file_path: str = Field(..., description="Input file path")
    threshold: float = Field(0.8, ge=0.0, le=1.0)
    
    @validator("file_path")
    def validate_path(cls, v):
        if not Path(v).exists():
            raise ValueError(f"File not found: {v}")
        return v
```

## API Development

When working on biomapper-api:
- Use dependency injection for database sessions
- Implement proper error handling with HTTPException
- Add OpenAPI documentation to endpoints
- Follow RESTful conventions
- Use Pydantic models for request/response validation

## Important Notes

- **ALWAYS USE POETRY** - Never use pip directly
- **🎯 FOLLOW ALL 10 STANDARDIZATIONS** - This is critical for biomapper reliability
- **Type Safety** - Resolve all mypy errors before committing
- **Action Registration** - Actions self-register via decorator
- **Direct YAML Loading** - No database intermediary for strategies
- **Test Coverage** - Minimum 80% required, use three-level framework
- **ChromaDB** - May require specific system dependencies
- **Environment Variables** - Use EnvironmentManager and setup wizard
- **Backward Compatibility** - Maintained through flexible base models
- **Performance First** - Use complexity checker to prevent O(n^2)+ algorithms
- **Edge Case Debugging** - Document known issues in registry
- **Identifier Normalization** - Always normalize biological IDs for matching

## Standards Compliance Checklist

Before submitting any new action or strategy:

- [ ] **Parameter Naming**: Uses standard names (`input_key`, `output_key`, `file_path`)
- [ ] **Context Handling**: Uses `UniversalContext.wrap(context)`
- [ ] **Algorithm Complexity**: Audited with `python audits/complexity_audit.py`
- [ ] **Identifier Normalization**: Biological IDs normalized with registry
- [ ] **File Loading**: Uses `BiologicalFileLoader` for data ingestion
- [ ] **API Validation**: API clients validated with `APIMethodValidator`
- [ ] **Environment Config**: Uses `EnvironmentManager` for settings
- [ ] **Pydantic Models**: Inherits from `ActionParamsBase` for flexibility
- [ ] **Edge Case Handling**: Known issues documented in registry
- [ ] **Three-Level Testing**: Level 1 (unit), Level 2 (integration), Level 3 (production subset)

## Scripts Directory Organization

The `/scripts/` directory contains essential development and operational tools:

```
scripts/
├── setup/                          # Environment & infrastructure setup
│   ├── setup_environment.py        # Interactive environment configuration
│   ├── setup_metabolomics_pipeline.sh      # Basic pipeline setup
│   ├── setup_metabolomics_pipeline_smart.sh # Smart setup (checks existing state)
│   └── setup_hmdb_qdrant.py        # Vector database setup
├── pipelines/                      # Simplified pipeline clients
│   ├── run_metabolomics_harmonization.py   # Modern API client (256 lines)
│   ├── run_metabolomics_fix.py     # Simple API client (61 lines)
│   └── run_three_way_metabolomics.py       # Ultra-simple client (16 lines)
├── audit_parameters.py             # Parameter standardization audit
├── investigate_identifier.py       # Debug tool for edge cases (Q6EMK4)
├── ci_diagnostics.py              # CI issue detection
├── create_minimal_test_data.py     # Test data generator
└── run_ci_tests.py                # CI test runner
```

### Key Script Usage:

**Environment Setup:**
```bash
python scripts/setup_environment.py    # Interactive setup wizard
bash scripts/setup/setup_metabolomics_pipeline_smart.sh  # Pipeline setup
```

**Pipeline Execution (Strategy-First Approach):**
```bash
# Modern approach - direct strategy execution
poetry run biomapper run STRATEGY_NAME

# Alternative - via pipeline clients  
python scripts/pipelines/run_metabolomics_harmonization.py
python scripts/pipelines/run_three_way_metabolomics.py
```

**Development Tools:**
```bash
python scripts/audit_parameters.py          # Check parameter naming compliance
python scripts/investigate_identifier.py Q6EMK4  # Debug problematic identifiers
python scripts/ci_diagnostics.py           # Pre-commit CI checks
python scripts/create_minimal_test_data.py # Generate test datasets
```

### Migration from Legacy Scripts:

**DEPRECATED** (removed in 2025 cleanup):
- `main_pipelines/run_all_protein_mappings.py` - Meta-orchestrator (238 lines)
- `main_pipelines/run_*_mapping.py` - 9x auto-generated protein scripts (~90 lines each)
- `utilities/create_client_scripts.py` - Script generator (194 lines)

These were replaced by the **strategy-first approach**: Use `poetry run biomapper run STRATEGY_NAME` instead of wrapper scripts. The YAML strategy files in `src/biomapper/configs/strategies/` now contain all mapping logic.

## Biological Data Investigation Patterns

### Systematic Coverage Debugging Workflow

When biological coverage doesn't match expectations, follow this systematic investigation sequence:

1. **Verify Extraction Completeness**
   ```python
   # Check if all identifiers are being extracted
   import re
   pattern = re.compile(r'UniProtKB:([A-Z0-9]+)')
   matches = pattern.findall(xrefs_string)
   print(f'Extracted {len(matches)} IDs')  # Should use findall() for all matches
   ```

2. **Validate Reference Data Quality**
   ```bash
   # Check if target proteins exist in reference
   grep "P29459\|P21217" /path/to/kg2c_proteins.csv
   ```

3. **Debug Join/Matching Logic**
   ```yaml
   # Use LEFT join to see unmatched records
   join_type: left  # Instead of inner - reveals what's not matching
   join_columns:
     source: uniprot
     target: extracted_uniprot_normalized  # Ensure column names align
   ```

4. **Track Data Through Pipeline**
   ```python
   # Add debug columns at each stage
   df['debug_stage'] = 'stage_name'
   df['debug_original'] = df['_original_uniprot']  # Preserve original IDs
   ```

### Case Study: Composite ID Matching Investigation (2025)

**Initial Hypothesis**: PROTEIN_EXTRACT_UNIPROT_FROM_XREFS only extracting first UniProt ID
**Investigation Result**: Extraction works correctly (37,094 multi-ID entries); issue in join column alignment

**Key Lessons Learned**:
- ✅ Always verify assumptions with data (extraction was working fine)
- ✅ Systematic investigation beats hypothesis-driven debugging
- ✅ LEFT joins reveal matching failures that INNER joins hide
- ✅ Join column alignment critical (extracted_uniprot vs extracted_uniprot_normalized)
- ✅ Preserve original IDs through all transformations (_original_uniprot)

**The Fix**: Changed join from `extracted_uniprot` to `extracted_uniprot_normalized`

### Reusable Debug Transforms

```yaml
# Debug checkpoint to inspect data at any stage
- name: debug_checkpoint
  action:
    type: CUSTOM_TRANSFORM
    params:
      transformations:
        - column: debug_unique_count
          expression: 'df["target_column"].nunique()'
        - column: debug_sample
          expression: 'df["target_column"].head(10).tolist()'
        - column: debug_unmatched
          expression: 'df[df["match_column"].isna()]["id_column"].tolist()'
```

### Standard Composite Handling Pattern

For any biological entity with composite identifiers (e.g., "P29460,P29459"):

1. **Parse** - Split composites while preserving original in `_original_{field}`
2. **Normalize** - Standardize individual components
3. **Match** - Join with reference data on normalized columns
4. **Filter** - Keep only successfully matched records
5. **Restore** - Bring back original composite ID for final output
6. **Validate** - Ensure one-to-many relationships created

### Investigation Checklist for Coverage Issues

When coverage is lower than expected:

- [ ] Are all identifiers being extracted? (Check with regex.findall())
- [ ] Do all components exist in reference? (Direct grep/search)
- [ ] Is parsing preserving original IDs? (Check _original_* columns)
- [ ] Are join columns properly aligned? (source vs target column names)
- [ ] Is normalization consistent? (Both sides normalized same way)
- [ ] Are you using LEFT join for debugging? (See unmatched records)
- [ ] Is data being filtered unexpectedly? (Check row counts at each stage)

## 🎯 99.9% Coverage Achievement Case Study (August 2025)

### Investigation: 4 Composite IDs Preventing 99.9% Coverage

**Problem**: Progressive protein mapping strategy achieved 99.7% coverage but 4 composite IDs remained unmapped despite individual components existing in KG2c reference dataset.

**Root Cause**: Column alignment mismatch in join operations. Strategy was joining on `extracted_uniprot` but normalization creates `extracted_uniprot_normalized`.

**Solution Applied**:
```yaml
# BEFORE (WRONG)
join_columns:
  composite_parsed_normalized: uniprot
  kg2c_normalized: extracted_uniprot  # Missing _normalized suffix

# AFTER (FIXED) 
join_columns:
  composite_parsed_normalized: uniprot
  kg2c_normalized: extracted_uniprot_normalized  # Correct column name
```

**Investigation Methodology**:
1. **Component Verification**: Confirmed all 8 components (P29460, P29459, Q11128, P21217, Q29983, Q29980, Q8NEV9, Q14213) exist in KG2c xrefs
2. **Isolated Testing**: Verified PARSE_COMPOSITE_IDENTIFIERS works correctly (4 composites → 8 components)  
3. **Column Analysis**: Discovered normalization adds `_normalized` suffix not used in joins
4. **Systematic Fix**: Applied column name corrections to both direct and composite matching

**Files Modified**:
- Strategy: `/src/configs/strategies/experimental/prot_arv_to_kg2c_uniprot_v3.0.yaml`
- Client: `/scripts/pipelines/prot_arv_to_kg2c_uniprot_v3.0.py`

**Expected Outcome**: 99.9%+ coverage (1,161+ of 1,165 total proteins) through proper composite matching.

**Key Lesson**: Always verify column names after transformation steps, especially normalization that adds suffixes.

## Current Focus Areas

1. **Type Safety Migration** - Converting final 2-3 actions to TypedStrategyAction
2. **Enhanced Organization** - Entity-based action structure
3. **Performance Optimization** - Chunking for large datasets
4. **External Integrations** - Google Drive sync, API enrichments
5. **Strategy-First Architecture** - Direct YAML strategy execution without wrapper scripts
6. **Coverage Excellence** - Achieving 99.9% through systematic debugging