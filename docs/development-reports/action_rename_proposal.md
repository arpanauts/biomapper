# Action Registration Name Proposal

## Current State
- **Current Name**: `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`
- **Suggested Name**: `DATASET_FILTER`

## Analysis

### Pros of Current Name (`FILTER_IDENTIFIERS_BY_TARGET_PRESENCE`)
1. **Explicit**: Clearly describes what the action does
2. **Self-documenting**: No ambiguity about the filtering criteria
3. **Consistent**: Follows the pattern of other detailed action names

### Pros of Suggested Name (`DATASET_FILTER`)
1. **Concise**: Shorter and easier to type in YAML
2. **Flexible**: Could encompass future filtering variations
3. **Clean**: Simpler name for common operation

### Cons of Renaming
1. **Breaking Change**: Existing pipelines using the current name would break
2. **Less Specific**: "DATASET_FILTER" doesn't indicate it filters by target presence
3. **Ambiguity**: Could be confused with other types of filtering (by date, by quality, etc.)

## Recommendation

**Keep the current name** `FILTER_IDENTIFIERS_BY_TARGET_PRESENCE` for the following reasons:

1. **Clarity over Brevity**: In bioinformatics pipelines, explicit naming prevents errors
2. **No Breaking Changes**: Maintains compatibility with existing configurations
3. **Future-proof**: Allows for other filter types like:
   - `FILTER_IDENTIFIERS_BY_SOURCE_PRESENCE`
   - `FILTER_IDENTIFIERS_BY_QUALITY_SCORE`
   - `FILTER_IDENTIFIERS_BY_DATE_RANGE`

## Alternative Approach

If brevity is desired, consider adding an alias system:
```python
@register_action("FILTER_IDENTIFIERS_BY_TARGET_PRESENCE")
@register_action_alias("DATASET_FILTER")  # Future enhancement
class FilterByTargetPresenceAction(StrategyAction):
    ...
```

This would allow both names to work without breaking existing pipelines.