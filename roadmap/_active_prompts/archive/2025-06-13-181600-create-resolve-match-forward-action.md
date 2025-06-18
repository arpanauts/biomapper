# Task: Create RESOLVE_AND_MATCH_FORWARD Action Type

**Source Prompt Reference:** This task is defined by the prompt: /home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-13-181600-create-resolve-match-forward-action.md

## 1. Task Objective
Create a new action type RESOLVE_AND_MATCH_FORWARD that resolves source identifiers via UniProt Historical API and then matches them against the target endpoint. This action reads unmatched identifiers from context, resolves them to current IDs, and performs matching with composite/M2M support.

## 2. Prerequisites
- [ ] Required files exist: /home/ubuntu/biomapper/biomapper/core/strategy_actions/base.py
- [ ] Required files exist: /home/ubuntu/biomapper/biomapper/core/strategy_actions/template_action.py.template
- [ ] Required files exist: /home/ubuntu/biomapper/biomapper/core/strategy_actions/CLAUDE.md
- [ ] Required files exist: /home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py
- [ ] Required permissions: Write access to biomapper directory
- [ ] Required dependencies: Python 3.8+, pytest installed via Poetry
- [ ] Environment state: Poetry shell activated

## 3. Context from Previous Attempts
- **Previous attempt timestamp:** N/A - First attempt
- **Issues encountered:** N/A
- **Partial successes:** N/A
- **Recommended modifications:** N/A

## 4. Task Decomposition
Break this task into the following verifiable subtasks:
1. **Create action implementation:** Create resolve_and_match_forward.py from template
2. **Implement resolution logic:** Integrate UniProt resolver and matching
3. **Create comprehensive tests:** Write test_resolve_and_match_forward.py with full coverage
4. **Update imports:** Add to __init__.py
5. **Document usage:** Create clear documentation

## 5. Implementation Requirements

### Input files/data:
- Template: /home/ubuntu/biomapper/biomapper/core/strategy_actions/template_action.py.template
- Guidelines: /home/ubuntu/biomapper/biomapper/core/strategy_actions/CLAUDE.md
- UniProt client: /home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py

### Expected outputs:
- Implementation: /home/ubuntu/biomapper/biomapper/core/strategy_actions/resolve_and_match_forward.py
- Tests: /home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_resolve_and_match_forward.py
- Updated: /home/ubuntu/biomapper/biomapper/core/strategy_actions/__init__.py

### Code standards:
- Follow biomapper conventions (see CLAUDE.md)
- Type hints required
- Comprehensive docstrings
- Handle composites and M2M by default
- Proper async/await usage for API calls

### Specific Implementation Details:

The RESOLVE_AND_MATCH_FORWARD action should:

1. **Read identifiers from context** (default: 'unmatched_source')
2. **Resolve via UniProt API** to get current/primary accessions
3. **Handle composite identifiers** in both input and resolved results
4. **Match resolved IDs** against target endpoint
5. **Update context** with results
6. **Support parameters:**
   ```python
   input_from: str = 'unmatched_source'  # Context key to read from
   match_against: str = 'TARGET'  # Which endpoint to match against
   resolver: str = 'UNIPROT_HISTORICAL_API'  # Which resolver to use
   target_ontology: str  # Required - ontology type to match in target
   append_matched_to: str = 'all_matches'  # Where to append matches
   update_unmatched: str = 'unmatched_source'  # Update unmatched list
   composite_handling: str = 'split_and_match'
   match_mode: str = 'many_to_many'
   batch_size: int = 100  # For API calls
   ```

### Resolution Logic:
```python
# Pseudo-code for the main logic
unmatched_ids = context.get(input_from, [])
expanded_ids = handle_composites(unmatched_ids)

# Resolve via UniProt
resolver = UniProtHistoricalResolverClient(session)
resolved_mappings = {}
for batch in chunks(expanded_ids, batch_size):
    results = await resolver.resolve_batch(batch)
    # results format: {old_id: {'current': [current_ids], 'status': 'primary'}}
    resolved_mappings.update(results)

# Match against target
target_data = load_target_endpoint_data(target_ontology)
matches = perform_matching(resolved_mappings, target_data, match_mode)

# Update context
existing_matches = context.get(append_matched_to, [])
context[append_matched_to] = existing_matches + matches
```

### Example usage in strategy:
```yaml
action:
  type: "RESOLVE_AND_MATCH_FORWARD"
  input_from: "context.unmatched_ukbb"
  match_against: "TARGET"
  target_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
  resolver: "UNIPROT_HISTORICAL_API"
  append_matched_to: "context.all_matches"
  update_unmatched: "context.unmatched_ukbb"
```

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Import Errors:** Check UniProt client import path
- **API Errors:** Handle rate limiting, timeouts gracefully
- **Memory Errors:** Process in smaller batches
- **Test Failures:** Mock the UniProt client properly in tests

For each error type, indicate in your feedback:
- Error classification: [RETRY_WITH_MODIFICATIONS | ESCALATE_TO_USER | REQUIRE_DIFFERENT_APPROACH]
- Specific changes needed for retry (if applicable)
- Confidence level in proposed solution

## 7. Success Criteria and Validation
Task is complete when:
- [ ] resolve_and_match_forward.py implements full resolution + matching logic
- [ ] All tests pass: `pytest tests/unit/core/strategy_actions/test_resolve_and_match_forward.py`
- [ ] Action handles UniProt API responses correctly (primary, secondary, obsolete)
- [ ] Composite identifiers handled throughout the pipeline
- [ ] Context updates work correctly

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-13-181600-feedback-resolve-match-forward-action.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Issues Encountered:** [detailed error descriptions with context]
- **Next Action Recommendation:** [specific follow-up needed]
- **Confidence Assessment:** [quality, testing coverage, risk level]
- **Environment Changes:** [files created: resolve_and_match_forward.py, test file, __init__.py modified]
- **Lessons Learned:** [patterns that worked or should be avoided]

## Additional Context

This action is critical for handling historical UniProt IDs that may exist in older datasets. The UniProt API can resolve:
- Demerged accessions (one old ID -> multiple current IDs)
- Merged accessions (multiple old IDs -> one current ID)
- Secondary accessions -> Primary accessions
- Obsolete entries

The action must handle all these cases gracefully and maintain provenance of how IDs were resolved.

Integration note: This action works on identifiers that didn't match in the initial BIDIRECTIONAL_MATCH step, giving them a second chance to find matches after resolution.