# Task: Create BIDIRECTIONAL_MATCH Action Type

**Source Prompt Reference:** This task is defined by the prompt: /home/ubuntu/biomapper/roadmap/_active_prompts/2025-06-13-181500-create-bidirectional-match-action.md

## 1. Task Objective
Create a new action type BIDIRECTIONAL_MATCH that performs intelligent bidirectional matching between source and target endpoints with composite identifier handling, many-to-many mapping support, and tracking of matched/unmatched identifiers in the execution context.

## 2. Prerequisites
- [ ] Required files exist: /home/ubuntu/biomapper/biomapper/core/strategy_actions/base.py
- [ ] Required files exist: /home/ubuntu/biomapper/biomapper/core/strategy_actions/template_action.py.template
- [ ] Required files exist: /home/ubuntu/biomapper/biomapper/core/strategy_actions/CLAUDE.md
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
1. **Create action implementation:** Create bidirectional_match.py from template
2. **Implement matching logic:** Build bidirectional matching with composite/M2M support
3. **Create comprehensive tests:** Write test_bidirectional_match.py with full coverage
4. **Update imports:** Add to __init__.py
5. **Document usage:** Create clear documentation

## 5. Implementation Requirements

### Input files/data:
- Template: /home/ubuntu/biomapper/biomapper/core/strategy_actions/template_action.py.template
- Guidelines: /home/ubuntu/biomapper/biomapper/core/strategy_actions/CLAUDE.md
- Base class: /home/ubuntu/biomapper/biomapper/core/strategy_actions/base.py

### Expected outputs:
- Implementation: /home/ubuntu/biomapper/biomapper/core/strategy_actions/bidirectional_match.py
- Tests: /home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_bidirectional_match.py
- Updated: /home/ubuntu/biomapper/biomapper/core/strategy_actions/__init__.py

### Code standards:
- Follow biomapper conventions (see CLAUDE.md)
- Type hints required
- Comprehensive docstrings
- Handle composites and M2M by default

### Specific Implementation Details:

The BIDIRECTIONAL_MATCH action should:

1. **Load data from both endpoints** for the specified ontology types
2. **Handle composite identifiers** (e.g., Q14213_Q8NEV9) by default
3. **Perform matching** based on match_mode parameter
4. **Track results** in context:
   - Matched pairs
   - Unmatched from source
   - Unmatched from target
5. **Support parameters:**
   ```python
   source_ontology: str  # Required - ontology type in source
   target_ontology: str  # Required - ontology type in target
   match_mode: str = 'many_to_many'  # or 'one_to_one'
   composite_handling: str = 'split_and_match'  # or 'match_whole', 'both'
   track_unmatched: bool = True
   save_matched_to: str = 'matched_identifiers'
   save_unmatched_source_to: str = 'unmatched_source'
   save_unmatched_target_to: str = 'unmatched_target'
   ```

### Example usage in strategy:
```yaml
action:
  type: "BIDIRECTIONAL_MATCH"
  source_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
  target_ontology: "PROTEIN_UNIPROTKB_AC_ONTOLOGY"
  match_mode: "many_to_many"
  composite_handling: "split_and_match"
  save_matched_to: "context.direct_matches"
  save_unmatched_source_to: "context.unmatched_ukbb"
  save_unmatched_target_to: "context.unmatched_hpa"
```

## 6. Error Recovery Instructions
If you encounter errors during execution:
- **Import Errors:** Ensure you're in the Poetry shell: `poetry shell`
- **Permission Errors:** Check file permissions with `ls -la`
- **Test Failures:** Run individual tests with `pytest -xvs tests/unit/core/strategy_actions/test_bidirectional_match.py`
- **Logic Errors:** Review the matching algorithm - ensure it handles empty sets, duplicates, and edge cases

For each error type, indicate in your feedback:
- Error classification: [RETRY_WITH_MODIFICATIONS | ESCALATE_TO_USER | REQUIRE_DIFFERENT_APPROACH]
- Specific changes needed for retry (if applicable)
- Confidence level in proposed solution

## 7. Success Criteria and Validation
Task is complete when:
- [ ] bidirectional_match.py implements the full matching logic with composite/M2M support
- [ ] All tests pass: `pytest tests/unit/core/strategy_actions/test_bidirectional_match.py`
- [ ] Action is importable: `from biomapper.core.strategy_actions.bidirectional_match import BidirectionalMatchAction`
- [ ] Code follows all guidelines in CLAUDE.md
- [ ] Context tracking works correctly (matched/unmatched saved to specified keys)

## 8. Feedback Requirements
Create a detailed Markdown feedback file at:
`/home/ubuntu/biomapper/roadmap/_active_prompts/feedback/2025-06-13-181500-feedback-bidirectional-match-action.md`

**Mandatory Feedback Sections:**
- **Execution Status:** [COMPLETE_SUCCESS | PARTIAL_SUCCESS | FAILED_WITH_RECOVERY_OPTIONS | FAILED_NEEDS_ESCALATION]
- **Completed Subtasks:** [checklist of what was accomplished]
- **Issues Encountered:** [detailed error descriptions with context]
- **Next Action Recommendation:** [specific follow-up needed]
- **Confidence Assessment:** [quality, testing coverage, risk level]
- **Environment Changes:** [files created: bidirectional_match.py, test_bidirectional_match.py, __init__.py modified]
- **Lessons Learned:** [patterns that worked or should be avoided]

## Additional Context

This action is part of a broader strategy for protein mapping between UKBB and HPA datasets. It will be used in conjunction with RESOLVE_AND_MATCH_FORWARD and RESOLVE_AND_MATCH_REVERSE actions to create a comprehensive bidirectional mapping pipeline.

Remember: Bioinformatics data is messy. Always assume:
- Identifiers can be composite (Q14213_Q8NEV9)
- Mappings are many-to-many
- Empty inputs are possible
- Case sensitivity matters

Follow the template structure but implement the specific matching logic required. The template provides the framework; you provide the intelligence.