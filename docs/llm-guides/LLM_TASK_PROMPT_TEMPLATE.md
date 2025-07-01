# Biomapper LLM Task Prompt Template

Use this template when requesting LLM assistance with biomapper development tasks.

---

## Task Context

**System**: You are working with Biomapper, a service-oriented biological data harmonization toolkit. The system uses:
- YAML-based strategy configurations for defining mapping workflows
- Reusable action classes that process data in steps
- Database-backed endpoint configurations
- A RESTful API service layer

**Architecture Guide**: Refer to `/home/ubuntu/biomapper/BIOMAPPER_ARCHITECTURE_GUIDE.md` for detailed information.

## Current Task

**Objective**: [Describe what needs to be accomplished]

**Type of Work**:
- [ ] Creating a new strategy action
- [ ] Modifying an existing action
- [ ] Creating/updating a YAML strategy
- [ ] Debugging a mapping pipeline
- [ ] Adding new endpoints
- [ ] Other: ___________

**Specific Requirements**:
1. [Requirement 1]
2. [Requirement 2]
3. [etc.]

## Current State

**Working Strategy/Action**: [Name if applicable]
**File Location**: [Path to relevant files]
**Error/Issue**: [Describe any errors or unexpected behavior]

**Example Input/Output**:
```
Input: [Sample input data]
Expected Output: [What should happen]
Actual Output: [What currently happens]
```

## Constraints

1. **DO NOT** modify the core architecture patterns
2. **DO NOT** hardcode file paths - use endpoints
3. **MUST** maintain backward compatibility with existing strategies
4. **MUST** follow the existing action registration pattern
5. **MUST** ensure all actions return required fields: `output_identifiers` and `output_ontology_type`

## Context Information

**Available Actions**:
- `LOCAL_ID_CONVERTER`: Maps using local CSV/TSV files
- `LOAD_ENDPOINT_IDENTIFIERS`: Loads all IDs from an endpoint
- `DATASET_OVERLAP_ANALYZER`: Analyzes overlap between datasets
- `API_RESOLVER`: Resolves IDs using external APIs
- [List other relevant actions]

**Available Endpoints**:
- `UKBB_PROTEIN_ASSAY_ID`: UK Biobank protein assays
- `HPA_PROTEIN_DATA`: Human Protein Atlas proteins
- [List other relevant endpoints]

**Strategy Context Flow**:
- Previous step outputs: [What's available in context]
- Required outputs: [What needs to be in context for next steps]

## Success Criteria

The task is complete when:
1. [ ] The strategy/action executes without errors
2. [ ] All test cases pass
3. [ ] The output matches expected format
4. [ ] Documentation is updated if needed
5. [ ] Database is updated if strategies were modified

## Additional Notes

[Any other relevant information, constraints, or considerations]

---

**Remember**: Focus on configuration-driven solutions. Create new strategies by combining existing actions when possible, rather than writing new code.