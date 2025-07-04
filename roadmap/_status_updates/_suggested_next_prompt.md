# Suggested Next Work Session Prompt

## Context Brief

Biomapper has just completed a major type safety enhancement using Test-Driven Development (TDD), implementing comprehensive Pydantic models for strategy actions while maintaining 100% backward compatibility. The core library now features typed interfaces (`TypedStrategyAction[TParams, TResult]`) alongside legacy dictionary-based interfaces, with YAML strategy validation and a proven migration pattern.

## Initial Steps

1. **Review Project Context:** Begin by reviewing `/home/ubuntu/biomapper/CLAUDE.md` for overall project architecture and the newly added TDD workflows and type safety guidelines.

2. **Review Recent Implementation:** Examine the recent status update at `/home/ubuntu/biomapper/roadmap/_status_updates/2025-07-04-pydantic-type-safety-implementation.md` to understand the comprehensive type safety work that was just completed.

3. **Understand Current State:** Review the TDD implementation summary at `/home/ubuntu/biomapper/TDD_IMPLEMENTATION_SUMMARY.md` for technical details of what was accomplished.

## Work Priorities

### Priority 1: Migrate Core Actions to Typed Interface
Based on usage frequency and importance, migrate high-priority strategy actions to the new `TypedStrategyAction` pattern:

- **Target Actions:** Identify actions used in production YAML strategies (check `/home/ubuntu/biomapper/configs/strategies/`)
- **Migration Pattern:** Follow the example in `/home/ubuntu/biomapper/biomapper/core/strategy_actions/execute_mapping_path_typed.py`
- **Testing:** Ensure comprehensive test coverage for both typed and legacy interfaces

### Priority 2: API Integration Enhancement
Integrate the type safety improvements with the biomapper-api service:

- **Verify API Status:** Confirm the API server is still functional (last known working on June 25, 2025)
- **Schema Generation:** Leverage Pydantic models for automatic OpenAPI schema generation
- **Endpoint Updates:** Ensure API endpoints properly handle both legacy and typed action parameters

### Priority 3: Production Validation
Validate the type safety implementation in production-like scenarios:

- **Strategy Validation:** Test YAML strategy loading with the new `StrategyValidator`
- **Performance Testing:** Benchmark Pydantic validation overhead vs. dictionary access
- **Integration Testing:** Run full end-to-end pipelines using typed actions

## References

- **Type Safety Models:** `/home/ubuntu/biomapper/biomapper/core/models/`
- **TypedStrategyAction Base:** `/home/ubuntu/biomapper/biomapper/core/strategy_actions/typed_base.py`
- **Migration Example:** `/home/ubuntu/biomapper/biomapper/core/strategy_actions/execute_mapping_path_typed.py`
- **YAML Validator:** `/home/ubuntu/biomapper/biomapper/core/validators/strategy_validator.py`
- **Test Examples:** `/home/ubuntu/biomapper/tests/unit/core/models/` and `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_execute_mapping_path_typed.py`

## Workflow Integration

### Recommended Claude Prompts

**For Action Migration:**
```
I need to migrate strategy actions to the new TypedStrategyAction pattern. Please:

1. Examine the existing action at biomapper/core/strategy_actions/[action_name].py
2. Follow the pattern in execute_mapping_path_typed.py to create typed version
3. Define Pydantic models for parameters and results
4. Implement backward compatibility
5. Create comprehensive tests following TDD approach
6. Ensure all existing YAML strategies continue to work

Focus on maintaining 100% backward compatibility while adding type safety benefits.
```

**For API Integration:**
```
I need to integrate the new Pydantic type safety with the biomapper-api. Please:

1. Review the current API implementation in biomapper-api/
2. Ensure strategy execution endpoints work with both typed and legacy actions
3. Implement automatic OpenAPI schema generation from Pydantic models
4. Add validation endpoints for YAML strategies
5. Test integration with the biomapper_client

Maintain backward compatibility while exposing type safety benefits through the API.
```

**For Production Validation:**
```
I need to validate the type safety implementation in production scenarios. Please:

1. Run comprehensive tests using poetry run pytest
2. Test YAML strategy validation with various configurations
3. Benchmark performance impact of Pydantic vs dictionary access
4. Execute full end-to-end pipelines with mixed typed/legacy actions
5. Verify no regressions in existing functionality

Document any performance considerations or integration issues discovered.
```

## Success Criteria

- All existing YAML strategies continue to work without modification
- New typed actions provide better IDE support and validation
- API endpoints support both legacy and typed interfaces seamlessly  
- Performance impact of type safety is acceptable for production use
- Clear migration documentation exists for future action development