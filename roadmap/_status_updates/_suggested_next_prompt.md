# Suggested Next Work Session Prompt

## Context Brief

Biomapper has completed a major architecture simplification, removing ~75% of the codebase and streamlining to 3 MVP actions with YAML-based strategies. Documentation has been completely overhauled for ReadTheDocs, and the project structure cleaned from 28 to 13 essential files. The system is now much simpler while retaining all core biological mapping functionality.

## Initial Steps

1. **Review Project Context:** Begin by reviewing `/home/ubuntu/biomapper/CLAUDE.md` for current development guidelines and the new MVP architecture overview.

2. **Review Recent Status:** Examine the status update at `/home/ubuntu/biomapper/roadmap/_status_updates/2025-07-22-mvp-architecture-documentation-cleanup.md` to understand the major cleanup work just completed.

3. **Understand Current State:** The project is in a "ready to commit" state with extensive changes staged for git commits.

## Work Priorities

### Priority 1: Complete Git Commit Organization
The project has extensive unstaged changes that need to be organized into logical commits:

- **Legacy Code Removal**: ~200+ deleted files from removed components (UI, database, cache, etc.)
- **Documentation Updates**: Complete ReadTheDocs restructure and content updates
- **Project Cleanup**: Root directory organization and configuration updates
- **Core Code Updates**: MVP action refinements and MinimalStrategyService

### Priority 2: Test Suite Validation
Address remaining test issues and validate system functionality:

- **Fix Test Failures**: 2 failing tests related to CSV column format expectations (timing metrics)
- **Integration Testing**: Run full end-to-end mapping scenarios with real biological data
- **Performance Validation**: Ensure simplified architecture meets performance requirements

### Priority 3: Documentation Deployment
Ensure the new documentation structure works properly:

- **ReadTheDocs Build**: Verify documentation builds without errors
- **Cross-Reference Cleanup**: Address remaining warnings about legacy references
- **User Experience Testing**: Validate that new user guides work for onboarding

### Priority 4: Production Readiness
Prepare the simplified architecture for production use:

- **API Validation**: Ensure REST API works correctly with MinimalStrategyService
- **Client Testing**: Validate biomapper_client works with simplified backend
- **Strategy Examples**: Test all example strategies in `/home/ubuntu/biomapper/configs/`

## References

- **MVP Actions**: `/home/ubuntu/biomapper/biomapper/core/strategy_actions/` (3 core actions)
- **Strategy Service**: `/home/ubuntu/biomapper/biomapper/core/minimal_strategy_service.py`
- **Documentation**: `/home/ubuntu/biomapper/docs/source/` (complete restructure)
- **Configuration**: `/home/ubuntu/biomapper/configs/` (YAML strategy examples)
- **Tests**: `/home/ubuntu/biomapper/tests/unit/core/strategy_actions/` (restored MVP tests)

## Workflow Integration

### Recommended Claude Prompts

**For Git Commit Organization:**
```
I have extensive changes ready to commit after a major architecture cleanup. Please:

1. Analyze all git diffs (staged and unstaged)
2. Group related changes into logical commits
3. Suggest appropriate commit messages for each group
4. Help organize the commits in proper sequence
5. Execute the commits and push to remote

The changes include legacy code removal, documentation updates, and project cleanup.
```

**For Test Suite Fixes:**
```
I need to address test failures and validate the simplified system. Please:

1. Run pytest and analyze the 2 failing tests
2. Update test expectations to match new CSV timing metrics columns
3. Verify all MVP actions work correctly
4. Run integration tests with real biological data
5. Document any performance considerations discovered

Focus on ensuring the simplified architecture maintains functionality.
```

**For Documentation Validation:**
```
I need to validate the new ReadTheDocs documentation structure. Please:

1. Build the documentation and check for errors
2. Address any remaining legacy cross-reference warnings
3. Test user workflows from quickstart through advanced usage
4. Verify all code examples work with current architecture
5. Check that MVP action documentation is comprehensive

Ensure documentation accurately reflects the simplified MVP architecture.
```

**For Production Readiness:**
```
I need to prepare the simplified biomapper for production use. Please:

1. Test the REST API with MinimalStrategyService backend
2. Validate biomapper_client works with all MVP actions
3. Run all example strategies from configs/ directory
4. Test with large datasets to validate performance
5. Document any limitations or considerations for production use

Focus on ensuring reliability and performance of the streamlined system.
```

## Success Criteria

- All changes committed in logical, well-organized commits
- Test suite passes with 100% success rate
- Documentation builds and deploys without errors
- All example strategies execute successfully
- API and client work seamlessly with simplified backend
- Performance is acceptable for production biological data sets
- Clear migration path documented for users of previous complex version