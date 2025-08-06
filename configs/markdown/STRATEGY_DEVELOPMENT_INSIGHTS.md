# Biomapper Strategy Development: Key Insights

## What We've Learned

### 1. Progressive Enhancement is Powerful
- Start with baseline (45% matches)
- Add API enrichment (+15%)
- Add vector search (+10%)
- Each stage builds on unmatched items from previous
- Measurable improvement at each step

### 2. Architecture Reality vs Documentation
- Documentation said "metamapper.db" but reality is direct YAML loading
- Context handling varies between action types
- TypedStrategyAction vs legacy actions have different signatures
- Always verify actual implementation

### 3. Data Quality is Critical
- NaN values break string operations
- Empty identifiers need filtering
- Different datasets have different column structures
- Robust error handling is essential

### 4. Context Management Complexity
- Actions store data in custom_action_data['datasets']
- Context wrapper needs careful design
- State must persist across actions
- Different actions expect different context structures

### 5. External Service Integration
- CTS API needs rate limiting and caching
- Qdrant needs Docker and proper setup
- Services may fail - need graceful degradation
- Connection pooling and cleanup important

### 6. Action Type Design Principles
- Small, focused actions are better
- TypedStrategyAction provides type safety
- Backward compatibility is challenging
- Clear parameter models essential
- Comprehensive error messages help debugging

### 7. Testing Strategy Importance
- TDD catches issues early
- Unit tests for each action
- Integration tests for workflows
- Mock external services
- Test data quality edge cases

### 8. Debugging Approach
- Start with simple test runner
- Add logging at key points
- Check data at each stage
- Isolate issues to specific actions
- Fix one thing at a time