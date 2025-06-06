# Scripts Directory - AI Assistant Instructions

## Overview

This directory contains standalone executable scripts for the biomapper project, organized into functional categories. When working with scripts, follow these guidelines to maintain consistency and functionality.

## Directory Navigation

When asked to work with scripts, first identify the category:

1. **For mapping operations** → Check `main_pipelines/`
2. **For database setup** → Check `setup_and_configuration/`
3. **For data preparation** → Check `data_preprocessing/`
4. **For testing/debugging** → Check `testing_and_validation/`
5. **For analysis tasks** → Check `analysis_and_reporting/`

## Important Considerations

### Path Handling

Scripts were recently reorganized from a flat structure. When working with scripts:

1. **Check imports**: Scripts may have broken imports after reorganization
2. **Relative paths**: Update relative paths that may point to old locations
3. **Script calls**: Shell scripts calling Python scripts need path updates

### Common Issues After Reorganization

1. **Import errors**: 
   ```python
   # Old: from test_utils import helper
   # New: from ..testing_and_validation.test_utils import helper
   ```

2. **File path references**:
   ```python
   # Old: "../data/input.csv"
   # New: "../../data/input.csv"  # Account for new subdirectory
   ```

3. **Script execution paths**:
   ```bash
   # Old: python test_mapping.py
   # New: python testing_and_validation/test_mapping.py
   ```

## Working with Scripts

### When Creating New Scripts

1. **Determine correct category** - Place in appropriate subdirectory
2. **Follow naming conventions**:
   - Mapping scripts: `map_[source]_to_[target].py`
   - Test scripts: `test_[functionality].py`
   - Debug scripts: `debug_[issue].py`
   - Analysis scripts: `analyze_[data].py`

3. **Include standard headers**:
   ```python
   #!/usr/bin/env python3
   """
   Script: [name]
   Purpose: [brief description]
   Usage: python [script_name].py [arguments]
   """
   ```

### When Modifying Scripts

1. **Preserve functionality** - Don't break existing behavior
2. **Update documentation** - Modify docstrings if behavior changes
3. **Test after changes** - Run the script to verify it still works
4. **Check dependencies** - Ensure imports and file paths are correct

### When Moving Scripts

1. **Use git mv** - Preserve version history
2. **Update imports** - Fix any broken import statements
3. **Update references** - Find and update any scripts that call the moved script
4. **Test thoroughly** - Ensure the script works from its new location

## Maintaining This CLAUDE.md File

### When to Update This File

This CLAUDE.md must be kept current with the actual state of the scripts directory. Update it when:

1. **Adding new scripts**:
   - Add the script to the appropriate category section
   - Update "Key scripts" lists if it's a significant addition
   - Add any special usage notes or dependencies

2. **Creating new subdirectories**:
   - Add a new category section with purpose and usage guidelines
   - Update the directory navigation section at the top

3. **Moving or reorganizing scripts**:
   - Update all path references
   - Revise the category descriptions if purposes change
   - Note any new patterns or conventions

4. **Discovering common issues**:
   - Add to "Common Issues After Reorganization" if path-related
   - Create new sections for recurring problems
   - Document solutions that work

5. **Changing conventions**:
   - Update naming conventions if they evolve
   - Revise best practices based on lessons learned
   - Add new common tasks as they emerge

### How to Update

When making updates:

```markdown
## Example Update Pattern

### [Category Name]/
- **Purpose**: [Clear purpose statement]
- **Key scripts**: [List 3-5 most important scripts]
- **When to use**: [Specific use cases]
- **Dependencies**: [Required setup or prerequisites]
- **Recent changes**: [Note any recent additions/changes]
```

### Self-Correcting Mechanism

If you notice this file is out of sync with reality:

1. **Check actual directory structure**: `ls -la scripts/*/`
2. **Identify discrepancies**: What's missing or incorrect?
3. **Update immediately**: Don't wait for a "documentation sprint"
4. **Add a note**: Include date and what changed

Example:
```markdown
# Update Note [2025-06-06]: Added new 'model_evaluation/' subdirectory 
# for ML model performance testing scripts
```

### Version Tracking

Consider adding a change log at the bottom:

```markdown
## CLAUDE.md Change Log
- 2025-06-06: Initial creation after scripts reorganization
- [Date]: [What changed]
```

This helps AI assistants understand the evolution of the directory structure.

## Script Categories Guide

### main_pipelines/
- **Purpose**: Production-ready mapping pipelines
- **Key scripts**: UKBB mappers, phase3 reconciliation
- **When to use**: Running actual mapping operations
- **Dependencies**: Requires populated metamapper DB

### setup_and_configuration/
- **Purpose**: System initialization and configuration
- **Key scripts**: populate_metamapper_db.py, resource setup scripts
- **When to use**: Initial setup or configuration changes
- **Note**: Run these before main pipelines

### data_preprocessing/
- **Purpose**: Prepare data for mapping or analysis
- **Key scripts**: CID allowlist creation, embedding filters
- **When to use**: Before running pipelines on new data
- **Output**: Usually creates filtered/processed data files

### testing_and_validation/
- **Purpose**: Test functionality and debug issues
- **Key scripts**: All test_*.py and debug_*.py scripts
- **When to use**: Verifying functionality or troubleshooting
- **Note**: Some are integration tests requiring full setup

### analysis_and_reporting/
- **Purpose**: Analyze results and generate reports
- **Key scripts**: Result analyzers, overlap checkers
- **When to use**: After pipeline runs to understand results
- **Output**: Reports, statistics, visualizations

## Special Cases

### needs_categorization/metamapping/
- Contains `__init__.py` - likely a Python package
- May belong in main biomapper package, not scripts
- Review before modifying

### MVP Directories
- `mvp_ukbb_arivale_chemistries/`
- `mvp_ukbb_arivale_metabolomics/`
- These are self-contained pipeline implementations
- Treat as mini-projects within main_pipelines

### Archived Scripts
- Located in `archived_or_experimental/`
- May be outdated or non-functional
- Useful for historical reference
- Don't modify unless specifically requested

## Best Practices

1. **Always check existing patterns** before creating new scripts
2. **Maintain consistent style** with surrounding code
3. **Document assumptions** about environment and dependencies
4. **Use logging** instead of print statements
5. **Handle errors gracefully** with try/except blocks
6. **Make scripts configurable** via command-line arguments

## Common Tasks

### Finding a specific mapper
```bash
find main_pipelines -name "*map*" -type f
```

### Checking which tests exist for a feature
```bash
grep -r "feature_name" testing_and_validation/
```

### Understanding script dependencies
```bash
grep -h "^import\|^from" script_name.py | sort -u
```

## Maintenance Notes

- Scripts in this directory are meant to be run independently
- They should not be imported as modules by other parts of biomapper
- If a script becomes a reusable module, move it to the main biomapper package
- Keep this directory focused on executable scripts only

## CLAUDE.md Change Log

- **2025-06-06**: Initial creation after scripts reorganization
  - Documented 8 main categories plus needs_categorization
  - Added maintenance guidelines for keeping this file updated
  - Included common issues and solutions from reorganization