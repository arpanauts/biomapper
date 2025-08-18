**STRICT SCOPE ENFORCEMENT:** Analyze ONLY the current working directory and its immediate subdirectories. Do NOT analyze parent directories, sibling directories, or the entire project root.

**PYTHON MODULE TRACING ANALYSIS:**

Please perform a comprehensive dead code analysis of this core folder using the following systematic approach:

**1. IMPORT DEPENDENCY MAPPING:**
- Scan ALL Python files in current directory and subdirectories ONLY
- Build complete import graph showing which modules import which others
- Identify modules that are imported by other modules vs. orphaned modules
- Look for circular imports and dependency cycles
- Map external imports vs. internal cross-references

**2. FUNCTION/CLASS USAGE TRACING:**
- Within each Python file, identify all functions and classes defined
- Trace which functions/classes are actually called or referenced by other modules
- Find unused functions, unused classes, and unused methods
- Look for dead code branches and unreachable code sections

**3. REGISTRY AND DYNAMIC LOADING ANALYSIS:**
- Look for action registry patterns (@register_action decorators)
- Check if registered actions are actually referenced in configs or other code
- Identify dynamically imported modules that may not show up in static analysis
- Find modules loaded via importlib, __import__, or string-based imports

**4. CONFIGURATION CROSS-REFERENCE:**
- Look for YAML/JSON config files that reference module names or action types
- Cross-reference these configs against actual module definitions
- Identify config references to non-existent modules
- Find modules that exist but aren't referenced in any configs

**5. DEPRECATION AND VERSION ANALYSIS:**
- Look for deprecated decorators, TODO comments, or version-specific code
- Identify multiple versions of the same functionality (v1, v2, etc.)
- Find files with deprecation markers or "old" naming patterns
- Check file modification dates to identify stale code

**6. DEAD CODE CONFIDENCE SCORING:**
For each potentially dead module/function, provide:
- Confidence level (0-100%) that it's truly unused
- Specific evidence (no imports found, no config references, etc.)
- Risk assessment if removed (low/medium/high risk)
- Suggested action (delete, archive, investigate further)

**ANALYSIS CONSTRAINTS:**
- Work directory path: [show the exact path you're analyzing]
- File count limit: Report if more than 50 Python files to avoid overwhelming analysis
- Focus on .py files primarily, but also check related .yaml, .json config files
- Create dependency graph visualization if possible

**OUTPUT REQUIREMENTS:**
1. Summary of directory structure and file count
2. Import dependency graph (who imports whom)
3. Orphaned modules (no incoming imports)
4. Unused functions/classes within modules
5. Registry analysis (registered vs. actually used actions)
6. Configuration mismatches
7. High-confidence dead code candidates with detailed reasoning
8. Risk assessment and recommended cleanup actions

**SAFETY REQUIREMENTS:**
- Show exact file paths that would be affected
- Never recommend deletion of core infrastructure files
- Always provide "investigate further" option for uncertain cases
- Ask for explicit confirmation before suggesting any removals

Please start by confirming the exact directory path you're analyzing and the number of Python files found before proceeding with the full analysis.