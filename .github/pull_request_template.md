## Description
<!-- Provide a clear and concise description of your changes -->

## Type of Change
<!-- Check the relevant option -->
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🧬 New strategy (biological workflow configuration)
- [ ] 🔧 New action (strategy building block)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] ⚡ Performance improvement
- [ ] 🔒 Security fix

## Related Issues
<!-- Link to related issues -->
Fixes #(issue number)
Related to #(issue number)

## Biological Context (for strategies/actions)
<!-- If adding biological functionality, explain the scientific context -->
- **Biological problem addressed:**
- **Expected accuracy/performance:**
- **Validated against:** <!-- e.g., DESeq2, manual curation -->
- **Organism specificity:** <!-- e.g., human-only, cross-species -->

## Validation Results
<!-- For strategies and actions, include validation metrics -->
```
Correlation with gold standard: 
Sensitivity: 
Specificity: 
Performance impact: 
```

## Testing
<!-- Describe the tests you ran and their results -->
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Coverage threshold met (≥80%)
- [ ] Performance benchmarks pass
- [ ] Manual testing completed

### Test Coverage
<!-- Paste coverage report summary -->
```
Current coverage: XX%
Files changed coverage: XX%
```

## Checklist
<!-- Ensure all requirements are met -->

### Code Quality
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have added comments for complex logic
- [ ] My changes generate no new warnings
- [ ] Type hints are complete and accurate

### Testing
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing unit tests pass locally
- [ ] I have tested edge cases (empty input, composites, many-to-many)
- [ ] Integration tests pass

### Documentation
- [ ] I have updated relevant documentation
- [ ] I have added/updated docstrings
- [ ] I have updated the CHANGELOG (if applicable)
- [ ] I have added usage examples (for new features)

### Biological Validation (if applicable)
- [ ] Handles composite identifiers (e.g., Q14213_Q8NEV9)
- [ ] Supports many-to-many relationships
- [ ] Maintains biological consistency
- [ ] Validated against benchmark data
- [ ] Provenance tracking implemented

## Screenshots/Examples
<!-- If applicable, add screenshots or examples showing your changes -->

## Breaking Changes
<!-- List any breaking changes and migration instructions -->

## Additional Notes
<!-- Any additional information that reviewers should know -->

---

## Review Requirements
<!-- Do not modify - for reviewers -->
- [ ] Code review by 2 maintainers
- [ ] Scientific review (for biological changes)
- [ ] Performance review (for core changes)
- [ ] Documentation review
- [ ] All CI checks passing