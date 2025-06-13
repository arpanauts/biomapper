# Task: Create RESOLVE_AND_MATCH_REVERSE Action Type

**Source Prompt Reference:** This task is defined by the prompt: /home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-13-181700-create-resolve-match-reverse-action.md

## 1. Task Objective
Create a new action type RESOLVE_AND_MATCH_REVERSE that resolves target identifiers via UniProt Historical API and matches them against remaining source identifiers. This is the reverse direction of RESOLVE_AND_MATCH_FORWARD, maximizing match coverage by checking if any unmatched target IDs can be resolved to match remaining source IDs.

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
1. **Create action implementation:** Create resolve_and_match_reverse.py from template
2. **Implement reverse resolution logic:** Resolve target IDs and match to source
3. **Create comprehensive tests:** Write test_resolve_and_match_reverse.py with full coverage
4. **Update imports:** Add to __init__.py
5. **Document usage:** Create clear documentation

## 5. Implementation Requirements

### Input files/data:
- Template: /home/ubuntu/biomapper/biomapper/core/strategy_actions/template_action.py.template
- Guidelines: /home/ubuntu/biomapper/biomapper/core/strategy_actions/CLAUDE.md
- UniProt client: /home/ubuntu/biomapper/biomapper/mapping/clients/uniprot_historical_resolver_client.py

### Expected outputs:
- Implementation: /home/ubuntu/biomapper/biomapper/core/strategy_actions/resolve_and_match_reverse.py
- Tests: /home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_resolve_and_match_reverse.py
- Updated: /home/ubuntu/biomapper/biomapper/core/strategy_actions/__init__.py

### Code standards:
- Follow biomapper conventions (see CLAUDE.md)
- Type hints required
- Comprehensive docstrings
- Handle composites and M2M by default
- Proper async/await usage for API calls

### Specific Implementation Details:

The RESOLVE_AND_MATCH_REVERSE action should:

1. **Read target identifiers from context** (default: 'unmatched_target')
2. **Read remaining source identifiers** (default: 'unmatched_source')
3. **Resolve target IDs via UniProt API**
4. **Match resolved target IDs against remaining source IDs**
5. **Handle composite identifiers** throughout
6. **Support parameters:**
   ```python
   input_from: str = 'unmatched_target'  # Target IDs to resolve
   match_against_remaining: str = 'unmatched_source'  # Remaining source IDs
   resolver: str = 'UNIPROT_HISTORICAL_API'
   source_ontology: str  # Required - ontology type in source
   append_matched_to: str = 'all_matches'
   save_final_unmatched: str = 'final_unmatched'
   composite_handling: str = 'split_and_match'
   match_mode: str = 'many_to_many'
   batch_size: int = 100
   ```

### Reverse Matching Logic:
```python
# Pseudo-code for the main logic
unmatched_target = context.get(input_from, [])
remaining_source = context.get(match_against_remaining, [])

# Expand composites
expanded_target = handle_composites(unmatched_target)
expanded_source = handle_composites(remaining_source)

# Resolve target IDs
resolver = UniProtHistoricalResolverClient(session)
resolved_target = {}
for batch in chunks(expanded_target, batch_size):
    results = await resolver.resolve_batch(batch)
    resolved_target.update(results)

# Create reverse lookup from resolved -> original
reverse_lookup = {}
for original, resolved_data in resolved_target.items():
    for current_id in resolved_data.get('current', []):
        reverse_lookup[current_id] = original

# Check if any resolved target IDs match remaining source
matches = []
still_unmatched_source = []
for source_id in expanded_source:
    if source_id in reverse_lookup:
        matches.append((source_id, reverse_lookup[source_id]))
    else:
        still_unmatched_source.append(source_id)

# Update context with final results
```

### Example usage in strategy:
```yaml
action:
  type: "RESOLVE_AND_MATCH_REVERSE"
  input_from: "context.unmatched_hpa"
  match_against_remaining: "context.unmatched_ukbb"
  source_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
  resolver: "UNIPROT_HISTORICAL_API"
  append_matched_to: "context.all_matches"
  save_final_unmatched: "context.final_unmatched"
```

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Import Errors:** Ensure proper module structure
- **Context Key Errors:** Handle missing context keys gracefully
- **API Timeout:** Implement retry logic with exponential backoff
- **Memory Issues:** Use generators for large datasets

For each error type, indicate in your feedback:
- Error classification: [RETRY_WITH_MODIFICATIONS | ESCALATE_TO_USER | REQUIRE_DIFFERENT_APPROACH]
- Specific changes needed for retry (if applicable)
- Confidence level in proposed solution

## 7. Success Criteria and Validation
Task is complete when:
- [ ] resolve_and_match_reverse.py implements reverse resolution + matching
- [ ] All tests pass: `pytest tests/unit/core/strategy_actions/test_resolve_and_match_reverse.py`
- [ ] Handles all UniProt resolution cases (merged, demerged, obsolete)
- [ ] Properly tracks final unmatched identifiers from both sides
- [ ] Maintains detailed provenance of reverse matches

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-13-181700-feedback-resolve-match-reverse-action.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Issues Encountered:** [detailed error descriptions with context]
- **Next Action Recommendation:** [specific follow-up needed]
- **Confidence Assessment:** [quality, testing coverage, risk level]
- **Environment Changes:** [files created: resolve_and_match_reverse.py, test file, __init__.py modified]
- **Lessons Learned:** [patterns that worked or should be avoided]

## Additional Context

This action completes the bidirectional mapping strategy by ensuring we check both directions:
1. Source → Resolve → Match to Target (FORWARD)
2. Target → Resolve → Match to Source (REVERSE)

This maximizes the chance of finding matches when datasets have different versions of UniProt IDs. For example:
- UKBB might have old UniProt ID "P12345"
- HPA might have the current ID "Q67890"
- UniProt API tells us P12345 was merged into Q67890
- Forward resolution would catch this, but if HPA had the old ID and UKBB had the new one, we need reverse resolution

Key difference from FORWARD: This action matches against the REMAINING source identifiers (those that didn't match in previous steps), not the full source dataset.