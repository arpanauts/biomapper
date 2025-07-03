# Code Examples Verification Report

This report documents all code examples found in the Biomapper documentation and identifies issues with imports, function signatures, and usage patterns.

## Summary of Findings

1. **Import Path Issues**: Several examples use incorrect or outdated import paths
2. **Missing Code Examples**: Many tutorial files are empty or contain only placeholders
3. **Inconsistent API Usage**: Some examples show outdated function signatures
4. **Configuration Format Issues**: Some YAML examples may not match current schema

## Detailed Findings by File

### 1. `/docs/source/tutorials/csv_adapter_usage.md`

**Issues Found:**
- Import path appears correct: `from biomapper.mapping.adapters.csv_adapter import CSVAdapter`
- All code examples appear syntactically correct
- No major issues found

### 2. `/docs/source/tutorials/name_resolution_clients.md`

**Issues Found:**
- Import paths appear correct:
  - `from biomapper.mapping.clients.translator_name_resolver_client import TranslatorNameResolverClient`
  - `from biomapper.mapping.clients.umls_client import UMLSClient`
  - `from biomapper.core.mapping_executor import MappingExecutor`
- All code examples appear syntactically correct

### 3. `/docs/source/tutorials/translator_name_resolver_usage.md`

**Potential Issues:**
- Line 129: References `UniChemClient` without import statement
- The import should be: `from biomapper.mapping.clients.unichem_client import UniChemClient`

### 4. `/docs/source/tutorials/umls_client_usage.md`

**Issues Found:**
- References `UMLSClientSimplified` but the actual import path needs verification
- Import path shown: `from biomapper.mapping.clients.umls_client_simplified import UMLSClientSimplified`
- Need to verify if this client exists in the codebase

### 5. `/docs/source/guides/getting_started.md`

**Critical Issues:**
- Line 14: `from biomapper.mapping import MetaboliteNameMapper` - This import is likely incorrect
- The class `MetaboliteNameMapper` doesn't appear to exist at this import path
- The example code is incomplete (cuts off at line 21)

### 6. `/docs/tutorials/yaml_mapping_strategies.md`

**Issues Found:**
- Import path appears correct: `from biomapper.core.mapping_executor import MappingExecutor`
- YAML configuration examples appear valid
- Code examples appear syntactically correct

### 7. `README.md` (Main Project README)

**Potential Issues:**
- Line 179: Shows a simplified import example that may not reflect actual usage:
  ```python
  from biomapper.core import MappingExecutor
  ```
  Should likely be:
  ```python
  from biomapper.core.mapping_executor import MappingExecutor
  ```

### 8. Empty/Placeholder Tutorial Files

The following tutorial files are empty or contain only headers:
- `/docs/source/tutorials/protein.md`
- `/docs/source/tutorials/llm_mapper.md`
- `/docs/source/tutorials/multi_provider.md`
- `/docs/source/tutorials/examples.md` (only contains descriptions, no actual code)

## Recommended Fixes

### High Priority

1. **Fix `/docs/source/guides/getting_started.md`**:
   - Update the import statement to use the correct class
   - Complete the code example
   - Verify the actual API for metabolite mapping

2. **Add import statement in `/docs/source/tutorials/translator_name_resolver_usage.md`**:
   ```python
   from biomapper.mapping.clients.unichem_client import UniChemClient
   ```

3. **Verify UMLSClientSimplified exists**:
   - Check if `biomapper.mapping.clients.umls_client_simplified` exists
   - If not, update documentation to reflect correct client name

4. **Update README.md import example**:
   - Change simplified import to full path import

### Medium Priority

1. **Complete empty tutorial files**:
   - Add actual code examples to protein.md, llm_mapper.md, multi_provider.md
   - Ensure examples match current API

2. **Add missing script references**:
   - Several documentation files reference scripts in `scripts/` directory
   - Verify these scripts exist: `test_translator_name_resolver.py`, `test_umls_client.py`, etc.

### Low Priority

1. **Standardize code example format**:
   - Ensure all examples include necessary imports
   - Add error handling examples where appropriate
   - Include expected output comments

## Example Scripts Verification

### `/examples/tutorials/tutorial_basic_llm_mapping.py`

**Critical Issue:**
- Line 5: `from biomapper.mapping.llm_mapper import LLMMapper`
- The actual path should be: `from biomapper.mvp0_pipeline.llm_mapper import LLMMapper`
- This import error would prevent the script from running

### `/examples/tutorials/tutorial_protein.py`

**Issues Found:**
- Import paths appear correct and match the codebase structure
- However, the script expects CSV files that may not be present

### `/examples/tutorials/tutorial_metabolite_mapping_workflow.py`

**Critical Issues:**
- Lines 27-30: Invalid imports from biomapper package
  ```python
  from biomapper import (
      MetaboliteNameMapper,
      MultiProviderMapper,
      ChromaCompoundStore,
  ```
- These classes are not exposed in `biomapper/__init__.py`
- The biomapper package only exports: `load_tabular_file`, `get_max_file_size`, `RaMPClient`, `SetAnalyzer`

### `/examples/tutorials/tutorial_chromadb_hmdb_openai.py`

**Issues Found:**
- Line 11: `from phenome_arivale.data_loaders import load_arivale_metabolomics_metadata` - External dependency not part of biomapper
- Other imports appear to have correct paths within biomapper

### Missing Referenced Scripts

The following scripts are referenced in documentation but don't exist:
- `scripts/test_translator_name_resolver.py`
- `scripts/test_translator_name_resolver_comprehensive.py`
- `scripts/test_umls_client.py`
- `scripts/test_protein_yaml_strategy.py`

## Configuration Examples

All YAML configuration examples appear to follow a consistent format and should be valid, but should be tested against the actual schema validation.

## Overall Assessment

- Most code examples in the comprehensive tutorials (csv_adapter, name_resolution_clients) are correct
- The main issues are:
  1. Incorrect import paths in getting_started.md and example scripts
  2. Missing test scripts referenced in documentation
  3. Several empty tutorial files
  4. Some imports reference classes that may not exist (MetaboliteNameMapper, UMLSClientSimplified)
- The project appears to be well-structured but documentation is in various stages of completion

## Critical Actions Required

1. Fix the import path in `tutorial_basic_llm_mapping.py`
2. Either create the missing test scripts or remove references to them
3. Verify and fix the MetaboliteNameMapper import in getting_started.md
4. Complete the empty tutorial files or remove them
5. Verify all client classes referenced in documentation actually exist

## YAML Configuration Examples

### Verified Configuration Examples

The YAML configuration examples in the following files appear to be correct and follow the proper schema:

1. **`/configs/README.md`** - Comprehensive configuration guide with valid YAML examples
2. **`/configs/CONFIGURATION_QUICK_REFERENCE.md`** - Quick reference with correct YAML structure
3. **`/docs/tutorials/yaml_mapping_strategies.md`** - Strategy configuration examples are valid

### Configuration Best Practices Observed

1. **Separation of Concerns**: Entity configs and strategy configs are properly separated
2. **Environment Variables**: Proper use of `${DATA_DIR}` for file paths
3. **Type Safety**: Consistent use of ontology type references
4. **Version Control**: Configuration files include version numbers

## Summary of Code Example Issues by Severity

### Critical (Prevents Code from Running)
1. `tutorial_basic_llm_mapping.py` - Wrong import path for LLMMapper
2. `tutorial_metabolite_mapping_workflow.py` - Invalid imports from biomapper package
3. `getting_started.md` - MetaboliteNameMapper class doesn't exist

### High (Missing Content)
1. Multiple empty tutorial files (protein.md, llm_mapper.md, multi_provider.md)
2. Referenced test scripts don't exist (test_translator_name_resolver.py, etc.)

### Medium (May Cause Confusion)
1. README.md shows simplified import that doesn't match actual usage
2. Some examples reference external dependencies (phenome_arivale)

### Low (Documentation Improvements)
1. Missing import statements in some examples
2. Incomplete code examples that cut off mid-function