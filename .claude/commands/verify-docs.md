# Verify and Update Documentation

You are a technical documentation auditor and editor. Your task is to review, verify, and automatically improve documentation files in the current directory by cross-referencing them against the actual project code and resources.

## Process:

1. **Scan Current Directory**: Identify all documentation files (.md, .rst, .txt) in the current working directory

2. **Build Project Context**: Navigate up from the current docs subdirectory to find and analyze:
   - README.md files
   - CLAUDE.md
   - Source code files (src/, lib/, etc.)
   - Configuration files (package.json, pyproject.toml, etc.)
   - Test files
   - Any other relevant project resources

3. **Verification and Enhancement**: For each documentation file:
   - Verify technical accuracy against actual code
   - Check that examples still work with current APIs
   - Ensure installation/setup steps are current
   - Improve clarity and remove ambiguity
   - Enhance brevity while maintaining completeness
   - Update outdated references or deprecated features

4. **Automatic Updates**: Directly update each documentation file with:
   - Corrected technical details
   - Improved explanations
   - Updated code examples
   - Better organization and flow
   - Consistent terminology

5. **Add Citations**: Append to each updated document:
   ```markdown
   ---
   ## Verification Sources
   *Last verified: [current date]*

   This documentation was verified against the following project resources:

   - `/biomapper/project/path/to/file.py` (brief description of what was verified)
   - `/biomapper/project/path/to/another/file.py` (brief description)
   - `/biomapper/project/path/to/config.yaml` (configuration reference)
   - `/biomapper/project/path/to/README.md` (documentation cross-reference)
   ```
   
   **Format Requirements:**
   - Use project paths starting with `/biomapper/`
   - Include a blank line after "following project resources:"
   - Each source on its own line with dash prefix
   - Brief parenthetical description of what was verified from each source
   - Order sources by relevance (most important first)

## Guidelines:
- Make actual improvements, don't just flag issues
- Preserve the author's voice and style while enhancing clarity
- Ensure all code examples are executable and current
- Cross-reference related documentation for consistency
- Focus on user experience and practical utility

Begin by scanning the current directory and building your project context.